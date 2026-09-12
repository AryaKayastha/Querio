import httpx
import pytest

from querio_backend import bridge as app_module
from querio_backend.session_store import InMemorySessionStore


@pytest.fixture(autouse=True)
def fresh_session_store(monkeypatch):
    store = InMemorySessionStore()
    monkeypatch.setattr(app_module, "session_store", store)
    return store


def _fake_chatbot_response(url, answer="Grounded answer", domain="D5"):
    return httpx.Response(
        200,
        request=httpx.Request("POST", url),
        json={
            "answer": answer,
            "domain": domain,
            "confidence": 0.91,
            "sources": [
                {
                    "source_name": "Fees",
                    "source_section": "Page 1",
                    "source_url": None,
                }
            ],
            "guidance_only": False,
        },
    )


def test_chat_forwards_query_to_chatbot_with_no_prior_history(monkeypatch):
    captured = {}

    def fake_post(url, *, json, timeout):
        captured.update(url=url, json=json, timeout=timeout)
        return _fake_chatbot_response(url)

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    result = app_module.chat(app_module.ChatRequest(query="How much are the fees?", session_id="s1"))

    assert result.answer == "Grounded answer"
    assert result.domain == "D5"
    assert captured == {
        "url": "http://localhost:8001/chat",
        "json": {"query": "How much are the fees?"},
        "timeout": 14.0,
    }


def test_chat_forwards_prior_history_and_records_new_turns(monkeypatch, fresh_session_store):
    fresh_session_store.append("s1", "user", "How much are the fees?")
    fresh_session_store.append("s1", "assistant", "Grounded answer")

    captured = {}

    def fake_post(url, *, json, timeout):
        captured.update(json=json)
        return _fake_chatbot_response(url, answer="Follow-up answer")

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    app_module.chat(app_module.ChatRequest(query="What about next semester?", session_id="s1"))

    assert captured["json"]["history"] == [
        {"role": "user", "content": "How much are the fees?"},
        {"role": "assistant", "content": "Grounded answer"},
    ]
    assert fresh_session_store.get_recent("s1") == [
        {"role": "user", "content": "How much are the fees?"},
        {"role": "assistant", "content": "Grounded answer"},
        {"role": "user", "content": "What about next semester?"},
        {"role": "assistant", "content": "Follow-up answer"},
    ]


def test_chat_keeps_different_sessions_isolated(monkeypatch, fresh_session_store):
    fresh_session_store.append("s1", "user", "How much are the fees?")
    fresh_session_store.append("s1", "assistant", "Grounded answer")

    captured = {}

    def fake_post(url, *, json, timeout):
        captured.update(json=json)
        return _fake_chatbot_response(url)

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    app_module.chat(app_module.ChatRequest(query="Unrelated question", session_id="s2"))

    assert "history" not in captured["json"]


@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), ValueError("invalid response")])
def test_chat_returns_bad_gateway_when_chatbot_fails(monkeypatch, error):
    def fake_post(*args, **kwargs):
        raise error

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    with pytest.raises(app_module.HTTPException) as raised:
        app_module.chat(app_module.ChatRequest(query="hello", session_id="s1"))

    assert raised.value.status_code == 502


def test_health_ok_when_chatbot_healthy(monkeypatch):
    def fake_get(url, *, timeout):
        assert url.endswith("/health")
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={"status": "ok"},
        )

    monkeypatch.setattr(app_module.httpx, "get", fake_get)
    assert app_module.health() == {"status": "ok", "chatbot": "ok"}


def test_health_degraded_when_chatbot_unavailable(monkeypatch):
    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(app_module.httpx, "get", fake_get)
    assert app_module.health() == {"status": "degraded", "chatbot": "unavailable"}
