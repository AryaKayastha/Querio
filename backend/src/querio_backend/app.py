from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from querio_backend.router.router import answer_query

app = FastAPI(title="Querio Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# TODO: Add deployed frontend origin(s) here for non-local environments.


class ChatRequest(BaseModel):
    query: str


class SourceRef(BaseModel):
    source_name: str
    source_section: str


class ChatResponse(BaseModel):
    answer: str
    domain: str
    confidence: float
    sources: list[SourceRef]
    guidance_only: bool


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = answer_query(request.query)
    documents = result.get("documents", [])
    return ChatResponse(
        answer=result.get("answer", ""),
        domain=result.get("domain", "UNROUTED"),
        confidence=result.get("confidence", 0.0),
        sources=[
            SourceRef(
                source_name=doc.metadata.get("source_name", "unknown"),
                source_section=doc.metadata.get("source_section", ""),
            )
            for doc in documents
        ],
        guidance_only=result.get("guidance_only", False),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
