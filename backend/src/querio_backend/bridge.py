import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from querio_backend.bridge_config import CHATBOT_API_URL, CHATBOT_TIMEOUT_SECONDS

app = FastAPI(title="Querio Backend Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str


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
    try:
        response = httpx.post(
            f"{CHATBOT_API_URL}/chat",
            json={"query": request.query},
            timeout=CHATBOT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return ChatResponse.model_validate(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The chatbot service is unavailable. Please try again shortly.",
        ) from exc


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
