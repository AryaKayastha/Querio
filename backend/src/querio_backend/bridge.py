import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from querio_backend.bridge_config import CHATBOT_API_URL, CHATBOT_TIMEOUT_SECONDS, CONFIDENCE_THRESHOLD, ENABLE_API_DOCS
from querio_backend.db.engine import get_db
from querio_backend.db.models import QueryLog
from querio_backend.session_store import session_store

_API_DOCS_OFF = {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="Querio Backend Bridge", **({} if ENABLE_API_DOCS else _API_DOCS_OFF))

# Vite falls back to the next free port (5174, 5175, ...) when 5173 is already taken by
# another project's dev server on the same machine -- allow a small range of dev ports
# rather than breaking whenever that happens.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{port}" for port in range(5173, 5178)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    history = session_store.get_recent(request.session_id)
    payload = {"query": request.query}
    if history:
        payload["history"] = history

    try:
        response = httpx.post(
            f"{CHATBOT_API_URL}/chat",
            json=payload,
            timeout=CHATBOT_TIMEOUT_SECONDS,
        )
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
        response = httpx.get(f"{CHATBOT_API_URL}/health", timeout=3)
        response.raise_for_status()
        chatbot_health = response.json()
    except (httpx.HTTPError, ValueError):
        return {"status": "degraded", "chatbot": "unavailable"}

    if chatbot_health.get("status") != "ok":
        return {"status": "degraded", "chatbot": "unavailable"}
    return {"status": "ok", "chatbot": "ok"}
