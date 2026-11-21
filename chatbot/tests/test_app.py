"""API-level checks for the chatbot service (:8001), with no model or network calls."""

import pytest
from fastapi.testclient import TestClient

from querio_chatbot import app as app_module
from querio_chatbot import config
from querio_chatbot.router import router
from querio_chatbot.router.router import TOO_SHORT_REPLY

client = TestClient(app_module.app)


def _fail(*args, **kwargs):
    raise AssertionError("must be answered without the graph or a model call")


@pytest.fixture
def no_model(monkeypatch):
    monkeypatch.setattr(router, "invoke_with_fallback", _fail)
    monkeypatch.setattr(router, "get_graph", _fail)


# QRO-16: blank and next-to-empty queries must not spend an LLM call.


@pytest.mark.parametrize("query", ["", "   ", "\n\t "])
def test_blank_query_is_rejected_without_answering(monkeypatch, query):
    monkeypatch.setattr(app_module, "answer_query", _fail)
    response = client.post("/chat", json={"query": query})
    assert response.status_code == 422


@pytest.mark.parametrize("query", ["?", "a", " . ", "5", "??!", "🙏"])
def test_query_without_real_text_gets_an_instant_reply(no_model, query):
    response = client.post("/chat", json={"query": query})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == TOO_SHORT_REPLY
    assert body["domain"] == "UNROUTED"
    assert body["confidence"] == 0.0
    assert body["sources"] == []


def test_query_is_answered_without_surrounding_whitespace(monkeypatch):
    seen = {}

    def fake_answer_query(query, history):
        seen["query"] = query
        return {"answer": "Grounded answer", "domain": "D5", "confidence": 0.9, "documents": []}

    monkeypatch.setattr(app_module, "answer_query", fake_answer_query)
    response = client.post("/chat", json={"query": "  What is the fee?\n"})
    assert response.status_code == 200
    assert seen["query"] == "What is the fee?"


# QRO-18: Swagger UI, ReDoc and the OpenAPI schema are off unless ENABLE_API_DOCS is set.


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_served_only_when_enabled(path):
    assert client.get(path).status_code == (200 if config.ENABLE_API_DOCS else 404)


@pytest.mark.parametrize(
    ("value", "enabled"),
    [(None, False), ("", False), ("false", False), ("0", False), ("true", True), ("1", True), (" Yes ", True)],
)
def test_api_docs_flag_is_off_unless_explicitly_enabled(monkeypatch, value, enabled):
    if value is None:
        monkeypatch.delenv("ENABLE_API_DOCS", raising=False)
    else:
        monkeypatch.setenv("ENABLE_API_DOCS", value)
    assert config.env_flag("ENABLE_API_DOCS") is enabled


def test_health_is_still_served():
    assert client.get("/health").json() == {"status": "ok"}
