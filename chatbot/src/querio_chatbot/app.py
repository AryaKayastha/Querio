from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, field_validator

from querio_chatbot.config import ENABLE_API_DOCS
from querio_chatbot.router.router import answer_query

_API_DOCS_OFF = {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="Querio Chatbot", **({} if ENABLE_API_DOCS else _API_DOCS_OFF))


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str
    history: list[Turn] = []

    @field_validator("query")
    @classmethod
    def _strip_and_require_text(cls, query: str) -> str:
        # A blank query is a client error (422), not something to spend an LLM call on.
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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = answer_query(request.query, history=[turn.model_dump() for turn in request.history])
    # Only what the answer cites, not every retrieved chunk (QRO-12).
    documents = result.get("sources", [])
    return ChatResponse(
        answer=result.get("answer", ""),
        domain=result.get("domain", "UNROUTED"),
        confidence=result.get("confidence", 0.0),
        sources=[
            SourceRef(
                source_name=doc.metadata.get("source_name", "unknown"),
                source_section=doc.metadata.get("source_section", ""),
                source_url=doc.metadata.get("source_url"),
            )
            for doc in documents
        ],
        guidance_only=result.get("guidance_only", False),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
