import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from querio_backend.bridge_config import CHATBOT_API_URL, CHATBOT_TIMEOUT_SECONDS, CONFIDENCE_THRESHOLD
from querio_backend.db.engine import get_db
from querio_backend.db.models import QueryLog
from querio_backend.session_store import session_store

app = FastAPI(title="Querio Backend Bridge")

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
