"""QRO-02: when the models can't answer (free-tier quota, timeouts, outages), /chat replies with a
structured 503 and Retry-After, within its deadline, instead of a bare "Internal Server Error".
Models faked, so no network is needed."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_google_genai._common import GoogleGenerativeAIError

from querio_chatbot import app as app_module
from querio_chatbot.llm import chat
from querio_chatbot.llm.chat import ProvidersUnavailable
from querio_chatbot.retrieval import retriever
from querio_chatbot.router import router
from querio_chatbot.router.router import generate_node
from tests.test_guardrails import STATE

client = TestClient(app_module.app)
QUESTION = {"query": "What is the minimum attendance required?"}


def _raise(error):
    def fail(*args, **kwargs):
        raise error

    return fail


def _assert_busy_reply(response):
    assert response.status_code == 503
    assert response.json() == {"detail": app_module.BUSY_MESSAGE}
    assert response.headers["Retry-After"] == str(app_module.RETRY_AFTER_SECONDS)


def test_every_provider_failing_gives_a_503_with_retry_after(monkeypatch):
    monkeypatch.setattr(app_module, "answer_query", _raise(ProvidersUnavailable("every chat provider failed")))
    _assert_busy_reply(client.post("/chat", json=QUESTION))


def test_provider_failure_inside_the_real_graph_gives_a_503(monkeypatch):
    # The error has to come out of LangGraph unchanged for the API to recognise it.
    monkeypatch.setattr(router, "invoke_with_fallback", _raise(ProvidersUnavailable("every chat provider failed")))
    _assert_busy_reply(client.post("/chat", json=QUESTION))


def test_the_deadline_reaches_model_calls_inside_the_graph(monkeypatch):
    seen = {}

    def record_time_left(build, prompt):
        seen["seconds_left"] = chat._seconds_left()
        raise ProvidersUnavailable("stop here")

    monkeypatch.setattr(router, "invoke_with_fallback", record_time_left)
    client.post("/chat", json=QUESTION)
    assert seen["seconds_left"] is not None
    assert 0 < seen["seconds_left"] <= app_module.CHAT_DEADLINE_SECONDS


def test_a_question_past_its_deadline_gets_a_503_without_waiting_for_it(monkeypatch):
    monkeypatch.setattr(app_module, "CHAT_DEADLINE_SECONDS", 0.3)
    release = threading.Event()
    monkeypatch.setattr(app_module, "answer_query", lambda query, history: release.wait(5))

    started = time.monotonic()
    response = client.post("/chat", json=QUESTION)
    release.set()
    _assert_busy_reply(response)
    assert time.monotonic() - started < 2


def test_a_question_still_queued_at_its_deadline_is_never_started(monkeypatch):
    monkeypatch.setattr(app_module, "CHAT_DEADLINE_SECONDS", 0.3)
    pool = ThreadPoolExecutor(max_workers=1)
    monkeypatch.setattr(app_module, "_answer_pool", pool)
    answered = []
    monkeypatch.setattr(app_module, "answer_query", lambda query, history: answered.append(query))
    release = threading.Event()
    pool.submit(release.wait, 5)  # the only worker is busy

    _assert_busy_reply(client.post("/chat", json=QUESTION))
    release.set()
    pool.shutdown(wait=True)
    assert answered == []


def test_an_unexpected_error_gives_a_json_500_not_a_bare_one(monkeypatch):
    monkeypatch.setattr(app_module, "answer_query", _raise(KeyError("bug")))
    response = client.post("/chat", json=QUESTION)
    assert response.status_code == 500
    assert response.json() == {"detail": "Something went wrong while answering. Please try again."}


def test_embedding_failure_counts_as_providers_unavailable(monkeypatch):
    class FailingCollection:
        def similarity_search(self, query, k):
            raise GoogleGenerativeAIError("Error embedding content (429): RESOURCE_EXHAUSTED")

    monkeypatch.setattr(retriever, "_get_collection", lambda code: FailingCollection())
    with pytest.raises(ProvidersUnavailable, match="RESOURCE_EXHAUSTED"):
        retriever._semantic_candidates("D6", "minimum attendance", k=4)


def test_claim_is_cut_from_the_first_answer_when_regeneration_has_no_model(monkeypatch):
    replies = iter([SimpleNamespace(content="Your leave has been approved. You need a medical certificate and HOD approval.")])

    def first_answers_then_outage(build, prompt):
        try:
            return next(replies)
        except StopIteration:
            raise ProvidersUnavailable("every chat provider failed") from None

    monkeypatch.setattr(router, "invoke_with_fallback", first_answers_then_outage)
    assert generate_node(STATE)["answer"] == "You need a medical certificate and HOD approval."
