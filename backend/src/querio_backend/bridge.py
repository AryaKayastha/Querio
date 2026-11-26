import base64
import json
import threading
import time

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from querio_backend.bridge_config import (
    ALLOWED_ORIGINS,
    CHATBOT_API_URL,
    CHATBOT_AUTH,
    CHATBOT_TIMEOUT_SECONDS,
    CONFIDENCE_THRESHOLD,
    ENABLE_API_DOCS,
    RATE_LIMIT_PER_MINUTE,
)
from querio_backend.db.engine import get_db
from querio_backend.db.models import QueryLog
from querio_backend.rate_limit import SlidingWindowRateLimiter, client_ip_from_request
from querio_backend.session_store import session_store

_API_DOCS_OFF = {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="Querio Backend Bridge", **({} if ENABLE_API_DOCS else _API_DOCS_OFF))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limiter = SlidingWindowRateLimiter(max_requests=RATE_LIMIT_PER_MINUTE, window_seconds=60.0)
_token_lock = threading.Lock()
_cached_id_token: tuple[str, float] | None = None


def _jwt_expiry(token: str) -> float:
    """Extract the JWT exp claim without verifying signature; fall back to 5 minutes."""
    try:
        payload_segment = token.split(".")[1]
        padding = "=" * (-len(payload_segment) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_segment + padding))
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            return float(exp)
    except (IndexError, ValueError, TypeError):
        pass
    return time.time() + 300.0


def _fetch_google_id_token(audience: str) -> str:
    """Fetch a Cloud Run service-to-service ID token for the target audience."""
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2 import id_token

    return id_token.fetch_id_token(GoogleAuthRequest(), audience)


def _chatbot_headers() -> dict[str, str]:
    """Return auth headers for calling the chatbot when CHATBOT_AUTH=google."""
    if CHATBOT_AUTH != "google":
        return {}

    global _cached_id_token
    now = time.time()
    with _token_lock:
        if _cached_id_token and now < _cached_id_token[1] - 60.0:
            token = _cached_id_token[0]
        else:
            token = _fetch_google_id_token(CHATBOT_API_URL)
            _cached_id_token = (token, _jwt_expiry(token))
    return {"Authorization": f"Bearer {token}"}


def _enforce_rate_limit(request: Request) -> None:
    """Limit /chat requests per client IP to protect LLM quota."""
    retry_after = rate_limiter.check(client_ip_from_request(request))
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="You're sending questions too quickly. Please wait a moment and try again.",
            headers={"Retry-After": str(retry_after)},
        )


class ChatRequest(BaseModel):
    query: str
    session_id: str

    @field_validator("query")
    @classmethod
    def _strip_and_require_text(cls, query: str) -> str:
        # Rejected here (422) so a blank query is never forwarded, logged or added to the history.
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        return query


class SourceRef(BaseModel):
    source_name: str
    source_section: str
    source_url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    domain: str
    confidence: float
    sources: list[SourceRef]
    guidance_only: bool


BUSY_FALLBACK_MESSAGE = "Querio is busy right now. Please try again in a minute."


def _detail_of(response: httpx.Response) -> str | None:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        return None
    return detail if isinstance(detail, str) and detail.strip() else None


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(_enforce_rate_limit)])
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    history = session_store.get_recent(request.session_id)
    payload = {"query": request.query}
    if history:
        payload["history"] = history

    try:
        headers = _chatbot_headers()
        post_kwargs: dict = {"json": payload, "timeout": CHATBOT_TIMEOUT_SECONDS}
        if headers:
            post_kwargs["headers"] = headers
        response = httpx.post(f"{CHATBOT_API_URL}/chat", **post_kwargs)
        response.raise_for_status()
        chat_response = ChatResponse.model_validate(response.json())
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 503:
            # The chatbot is up but its models are busy or out of quota (QRO-02): pass on its
            # "try again shortly" message and Retry-After so the UI can show them.
            raise HTTPException(
                status_code=503,
                detail=_detail_of(exc.response) or BUSY_FALLBACK_MESSAGE,
                headers={"Retry-After": exc.response.headers.get("Retry-After", "30")},
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="The chatbot service is unavailable. Please try again shortly.",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The chatbot service is unavailable. Please try again shortly.",
        ) from exc

    session_store.append(request.session_id, "user", request.query)
    session_store.append(request.session_id, "assistant", chat_response.answer)

    # Analytics-only log (see Project_Details/03_data_requirements.md §5.1). A logging
    # failure must never break the chat response the student is waiting on.
    try:
        db.add(
            QueryLog(
                session_id=request.session_id,
                question=request.query,
                matched_domain=chat_response.domain,
                confidence=chat_response.confidence,
                resolved=chat_response.confidence >= CONFIDENCE_THRESHOLD,
                guidance_only=chat_response.guidance_only,
                top_sources=[source.model_dump() for source in chat_response.sources],
            )
        )
        db.commit()
    except Exception:
        db.rollback()

    return chat_response


@app.get("/health")
def health() -> dict:
    try:
        headers = _chatbot_headers()
        get_kwargs: dict = {"timeout": 3}
        if headers:
            get_kwargs["headers"] = headers
        response = httpx.get(f"{CHATBOT_API_URL}/health", **get_kwargs)
        response.raise_for_status()
        chatbot_health = response.json()
    except (httpx.HTTPError, ValueError):
        return {"status": "degraded", "chatbot": "unavailable"}

    if chatbot_health.get("status") != "ok":
        return {"status": "degraded", "chatbot": "unavailable"}
    return {"status": "ok", "chatbot": "ok"}
