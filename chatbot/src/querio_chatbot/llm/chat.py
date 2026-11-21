"""Chat calls for routing and answering, with fallback across providers (Gemini, Groq).

Each call tries the providers in config.CHAT_PROVIDERS order and moves on when one fails
(timeout, overload, exhausted free-tier quota), so a single provider's outage doesn't take
the chatbot down. Embeddings and OCR deliberately stay on Gemini: the vector store holds
Gemini embeddings, and OCR needs a vision model.
"""

import logging
import threading
import time
from collections.abc import Callable
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

# After a provider with a fallback fails (timeout, exhausted quota, outage), skip it for this long,
# so the following calls don't each pay for the same failure before reaching the fallback (QRO-13).
PROVIDER_COOLDOWN_SECONDS = 60
_cooldown_until: dict[str, float] = {}
_cooldown_lock = threading.Lock()


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


def _cooling_down(name: str) -> bool:
    with _cooldown_lock:
        return _cooldown_until.get(name, 0.0) > time.monotonic()


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
    A provider that has a fallback and just failed is skipped for PROVIDER_COOLDOWN_SECONDS; the last
    provider is always tried.
    """
    providers = chat_providers()
    last_error: Exception | None = None
    for index, (name, model) in enumerate(providers):
        has_fallback = index < len(providers) - 1
        if has_fallback and _cooling_down(name):
            continue
        try:
            result = build(model).invoke(prompt)
            if result is None:
                raise ValueError("empty structured result")
        except Exception as exc:
            last_error = exc
            # ValueError (incl. output-parser and validation errors) is one odd response, not a
            # provider problem, so it doesn't bench the provider.
            if has_fallback and not isinstance(exc, ValueError):
                _start_cooldown(name)
            if has_fallback:
                logger.warning("%s chat call failed (%s: %s); falling back to %s",
                               name, type(exc).__name__, str(exc)[:200], providers[index + 1][0])
            continue
        if index > 0:
            logger.warning("answered by fallback provider %s", name)
        return result
    raise last_error
