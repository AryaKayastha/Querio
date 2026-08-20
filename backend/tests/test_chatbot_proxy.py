import httpx
import pytest

from querio_backend import bridge as app_module


def test_chat_forwards_query_to_chatbot(monkeypatch):
    captured = {}

    def fake_post(url, *, json, timeout):
        captured.update(url=url, json=json, timeout=timeout)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "answer": "Grounded answer",
                "domain": "D5",
                "confidence": 0.91,
                "sources": [{"source_name": "Fees", "source_section": "Page 1"}],
                "guidance_only": False,
            },
        )

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    result = app_module.chat(app_module.ChatRequest(query="How much are the fees?"))

    assert result.answer == "Grounded answer"
    assert captured == {
        "url": "http://localhost:8001/chat",
        "json": {"query": "How much are the fees?"},
        "timeout": 14.0,
    }


@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), ValueError("invalid response")])
def test_chat_returns_bad_gateway_when_chatbot_fails(monkeypatch, error):
    def fake_post(*args, **kwargs):
        raise error

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    with pytest.raises(app_module.HTTPException) as raised:
        app_module.chat(app_module.ChatRequest(query="hello"))

    assert raised.value.status_code == 502
