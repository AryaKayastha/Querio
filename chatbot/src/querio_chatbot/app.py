import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as AnswerTimeout
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from querio_chatbot.config import CHAT_DEADLINE_SECONDS, ENABLE_API_DOCS, MAX_CONCURRENT_CHATS
from querio_chatbot.llm.chat import ProvidersUnavailable, chat_deadline
from querio_chatbot.router.router import answer_query

logger = logging.getLogger(__name__)

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


# QRO-02: when the models can't answer (free-tier quota, timeouts, outages) the student gets this, as
# a 503 with Retry-After, instead of a bare "Internal Server Error".
BUSY_MESSAGE = "Querio is getting more questions than it can answer right now. Please try again in a minute."
RETRY_AFTER_SECONDS = 30

# Questions are answered on this pool so that one stuck on slow providers or retries can be given up
# on at the deadline, and so at most MAX_CONCURRENT_CHATS run at once.
_answer_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CHATS, thread_name_prefix="querio-answer")


def _answer_before(deadline: float, query: str, history: list[dict]) -> dict:
    with chat_deadline(deadline):
        return answer_query(query, history=history)


def _busy() -> HTTPException:
    return HTTPException(status_code=503, detail=BUSY_MESSAGE, headers={"Retry-After": str(RETRY_AFTER_SECONDS)})


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={503: {"description": "The models are busy or unavailable; retry after Retry-After seconds."}},
)
def chat(request: ChatRequest) -> ChatResponse:
    deadline = time.monotonic() + CHAT_DEADLINE_SECONDS
    history = [turn.model_dump() for turn in request.history]
    future = _answer_pool.submit(_answer_before, deadline, request.query, history)
    try:
        result = future.result(timeout=CHAT_DEADLINE_SECONDS)
    except AnswerTimeout:
        # Not started yet (all workers busy) -> never start it. Already running -> it stops at its next
        # model call, because the same deadline is set inside it.
        future.cancel()
        logger.warning("no answer within %.0fs; replying 503", CHAT_DEADLINE_SECONDS)
        raise _busy() from None
    except ProvidersUnavailable as exc:
        logger.warning("model providers unavailable (%s); replying 503", exc)
        raise _busy() from None
    except Exception:
        logger.exception("unexpected error while answering")
        raise HTTPException(
            status_code=500, detail="Something went wrong while answering. Please try again."
        ) from None
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
