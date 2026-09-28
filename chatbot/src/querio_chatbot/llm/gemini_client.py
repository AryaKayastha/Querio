from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from querio_chatbot.config import GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBEDDING_MODEL

# The SDK default is no timeout at all, so a connection that stalls (seen through the corporate
# proxy) hung the request thread forever and surfaced as a backend 502. Bounded per-call
# timeouts make a stalled call fail fast and retry instead.
CHAT_TIMEOUT_SECONDS = 20
CHAT_MAX_RETRIES = 2
EMBED_TIMEOUT_SECONDS = 15


@lru_cache
def get_chat_model(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_CHAT_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=temperature,
        timeout=CHAT_TIMEOUT_SECONDS,
        max_retries=CHAT_MAX_RETRIES,
    )


@lru_cache
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
        client_args={"timeout": EMBED_TIMEOUT_SECONDS},
    )
