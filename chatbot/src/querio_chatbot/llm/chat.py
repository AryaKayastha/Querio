"""Chat calls for routing and answering, with fallback across providers (Gemini, Groq).

Each call tries the providers in config.CHAT_PROVIDERS order and moves on when one fails
(timeout, overload, exhausted free-tier quota), so a single provider's outage doesn't take
the chatbot down. Embeddings and OCR deliberately stay on Gemini: the vector store holds
Gemini embeddings, and OCR needs a vision model.

When every provider fails, or the question runs out of time, ProvidersUnavailable is raised so
the API can answer 503 "try again shortly" instead of a bare 500 (QRO-02).
"""

import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from querio_chatbot.config import CHAT_PROVIDERS, GEMINI_API_KEY, GEMINI_CHAT_MODEL, GROQ_API_KEY, GROQ_CHAT_MODEL

logger = logging.getLogger(__name__)

# A question makes two chat calls (classify, then answer) and the backend gives up after 45s.
# So a provider with another one behind it gets no retries and a shorter timeout -- a slow or
# overloaded provider hands over quickly instead of retrying -- and only the last provider retries.
CHAT_TIMEOUT_SECONDS = 15
# Gemini rejects any deadline under 10 s ("Minimum allowed deadline is 10s"), failing every call.
GEMINI_MIN_TIMEOUT_SECONDS = 10
FALLBACK_TIMEOUT_SECONDS = GEMINI_MIN_TIMEOUT_SECONDS
LAST_PROVIDER_MAX_RETRIES = 2

# After a provider fails (timeout, exhausted quota, outage), it goes to the back of the queue for this
# long, so the following calls don't each pay for the same failure before reaching another provider
# (QRO-13). It is still tried when the providers ahead of it fail: skipping it outright turned a
# single Gemini timeout into a minute of failed questions whenever Groq's quota was used up (QRO-02).
PROVIDER_COOLDOWN_SECONDS = 60
_cooldown_until: dict[str, float] = {}
_cooldown_lock = threading.Lock()

# Don't start a provider call with less time than this left before the question's deadline.
MIN_SECONDS_FOR_ATTEMPT = 2
_deadline: ContextVar[float | None] = ContextVar("querio_chat_deadline", default=None)


class ProvidersUnavailable(RuntimeError):
    """No model provider could answer (all failed, or the question ran out of time)."""


@contextmanager
def chat_deadline(deadline: float) -> Iterator[None]:
    """Stop starting provider calls after `deadline` (a time.monotonic() value) inside this block."""
    token = _deadline.set(deadline)
    try:
        yield
    finally:
        _deadline.reset(token)


def _seconds_left() -> float | None:
    deadline = _deadline.get()
    return None if deadline is None else deadline - time.monotonic()


def _gemini(max_retries: int, timeout: float) -> BaseChatModel:
    return ChatGoogleGenerativeAI(
        model=GEMINI_CHAT_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.0,
        timeout=timeout,
        max_retries=max_retries,
    )


def _groq(max_retries: int, timeout: float) -> BaseChatModel:
    return ChatGroq(
        model=GROQ_CHAT_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.0,
        timeout=timeout,
        max_retries=max_retries,
    )


_PROVIDERS: dict[str, tuple[str, Callable[[int, float], BaseChatModel]]] = {
    "gemini": (GEMINI_API_KEY, _gemini),
    "groq": (GROQ_API_KEY, _groq),
}


@lru_cache
def chat_providers() -> tuple[tuple[str, BaseChatModel], ...]:
    unknown = [name for name in CHAT_PROVIDERS if name not in _PROVIDERS]
    if unknown:
        raise ValueError(f"Unknown CHAT_PROVIDERS entries: {unknown} (known: {list(_PROVIDERS)})")
    available = [name for name in CHAT_PROVIDERS if _PROVIDERS[name][0]]
    if not available:
        raise RuntimeError("No chat provider has an API key -- set GEMINI_API_KEY and/or GROQ_API_KEY in chatbot/.env")

    last = len(available) - 1
    return tuple(
        (
            name,
            _PROVIDERS[name][1](
                LAST_PROVIDER_MAX_RETRIES if index == last else 0,
                CHAT_TIMEOUT_SECONDS if index == last else FALLBACK_TIMEOUT_SECONDS,
            ),
        )
        for index, name in enumerate(available)
    )


def _attempt_order(providers: tuple[tuple[str, BaseChatModel], ...]) -> list[tuple[str, BaseChatModel]]:
    """Providers in configured order, with any that are cooling down moved to the back."""
    with _cooldown_lock:
        now = time.monotonic()
        cooling = {name for name, until in _cooldown_until.items() if until > now}
    return [p for p in providers if p[0] not in cooling] + [p for p in providers if p[0] in cooling]


def _start_cooldown(name: str) -> None:
    with _cooldown_lock:
        _cooldown_until[name] = time.monotonic() + PROVIDER_COOLDOWN_SECONDS


def reset_provider_cooldowns() -> None:
    with _cooldown_lock:
        _cooldown_until.clear()


def invoke_with_fallback(build: Callable[[BaseChatModel], Runnable], prompt: Any) -> Any:
    """Run build(model).invoke(prompt) on each provider in turn and return the first result.

    `build` adapts the raw chat model, e.g. `lambda model: model.with_structured_output(Schema)`.
    A structured call that comes back empty (the model skipped the tool call) counts as a failure.
    A provider that just failed is tried after the others for PROVIDER_COOLDOWN_SECONDS. Raises
    ProvidersUnavailable when every provider fails or the chat_deadline() leaves no time to try.
    """
    providers = chat_providers()
    order = _attempt_order(providers)
    last_error: Exception | None = None
    for position, (name, model) in enumerate(order):
        seconds_left = _seconds_left()
        if seconds_left is not None and seconds_left < MIN_SECONDS_FOR_ATTEMPT:
            raise ProvidersUnavailable(f"out of time before trying {name} (last error: {last_error!r})") from last_error
        try:
            result = build(model).invoke(prompt)
            if result is None:
                raise ValueError("empty structured result")
        except Exception as exc:
            last_error = exc
            # ValueError (incl. output-parser and validation errors) is one odd response, not a
            # provider problem, so it doesn't bench the provider. A lone provider has nothing to
            # make way for, so it isn't benched either.
            if len(providers) > 1 and not isinstance(exc, ValueError):
                _start_cooldown(name)
            next_name = order[position + 1][0] if position + 1 < len(order) else None
            logger.warning("%s chat call failed (%s: %s)%s", name, type(exc).__name__, str(exc)[:200],
                           f"; falling back to {next_name}" if next_name else "")
            continue
        if name != providers[0][0]:
            logger.warning("answered by fallback provider %s", name)
        return result
    raise ProvidersUnavailable(f"every chat provider failed (last error: {last_error!r})") from last_error
