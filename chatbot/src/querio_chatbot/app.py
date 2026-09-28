from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from querio_chatbot.router.router import answer_query

app = FastAPI(title="Querio Chatbot")


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str
    history: list[Turn] = []


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
    documents = result.get("documents", [])
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
