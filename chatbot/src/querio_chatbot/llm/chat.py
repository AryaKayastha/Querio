"""Chat calls for routing and answering, with fallback across providers (Gemini, Groq).

Each call tries the providers in config.CHAT_PROVIDERS order and moves on when one fails
(timeout, overload, exhausted free-tier quota), so a single provider's outage doesn't take
the chatbot down. Embeddings and OCR deliberately stay on Gemini: the vector store holds
Gemini embeddings, and OCR needs a vision model.
"""

import logging
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
# So a provider with another one behind it gets no retries -- a slow or overloaded provider
# hands over after one timeout instead of retrying -- and only the last provider retries.
CHAT_TIMEOUT_SECONDS = 15
LAST_PROVIDER_MAX_RETRIES = 2


def _gemini(max_retries: int) -> BaseChatModel:
    return ChatGoogleGenerativeAI(
        model=GEMINI_CHAT_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.0,
        timeout=CHAT_TIMEOUT_SECONDS,
        max_retries=max_retries,
    )


def _groq(max_retries: int) -> BaseChatModel:
    return ChatGroq(
        model=GROQ_CHAT_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.0,
        timeout=CHAT_TIMEOUT_SECONDS,
        max_retries=max_retries,
    )


_PROVIDERS: dict[str, tuple[str, Callable[[int], BaseChatModel]]] = {
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
        (name, _PROVIDERS[name][1](LAST_PROVIDER_MAX_RETRIES if index == last else 0))
        for index, name in enumerate(available)
    )


def invoke_with_fallback(build: Callable[[BaseChatModel], Runnable], prompt: Any) -> Any:
    """Run build(model).invoke(prompt) on each provider in turn and return the first result.

    `build` adapts the raw chat model, e.g. `lambda model: model.with_structured_output(Schema)`.
    A structured call that comes back empty (the model skipped the tool call) counts as a failure.
    """
    providers = chat_providers()
    last_error: Exception | None = None
    for index, (name, model) in enumerate(providers):
        try:
            result = build(model).invoke(prompt)
            if result is None:
                raise ValueError("empty structured result")
        except Exception as exc:
            last_error = exc
            if index < len(providers) - 1:
                logger.warning("%s chat call failed (%s: %s); falling back to %s",
                               name, type(exc).__name__, str(exc)[:200], providers[index + 1][0])
            continue
        if index > 0:
            logger.warning("answered by fallback provider %s", name)
        return result
    raise last_error
