import base64
import json
import time

import httpx
from fastapi.testclient import TestClient

from querio_backend import bridge as app_module
from querio_backend import bridge_config
from querio_backend.db.engine import get_db
from querio_backend.rate_limit import SlidingWindowRateLimiter


def _make_jwt(exp: float) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def test_parse_allowed_origins_defaults_to_local_vite_ports():
    assert bridge_config.parse_allowed_origins(None) == [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
    ]
    assert bridge_config.parse_allowed_origins("   ") == bridge_config.parse_allowed_origins(None)


def test_parse_allowed_origins_strips_whitespace_and_trailing_slashes():
    assert bridge_config.parse_allowed_origins(" https://querio.web.app/ , https://querio.firebaseapp.com ") == [
        "https://querio.web.app",
        "https://querio.firebaseapp.com",
    ]


def test_google_id_token_is_attached_and_cached(monkeypatch):
    fetch_calls = []

    def fake_fetch(audience):
        fetch_calls.append(audience)
        return _make_jwt(time.time() + 3600)

    monkeypatch.setattr(app_module, "CHATBOT_AUTH", "google")
    monkeypatch.setattr(app_module, "_cached_id_token", None)
    monkeypatch.setattr(app_module, "_fetch_google_id_token", fake_fetch)

    captured_headers = []

    def fake_post(url, *, json, timeout, headers=None):
        captured_headers.append(headers)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "answer": "ok",
                "domain": "D5",
                "confidence": 0.9,
                "sources": [],
                "guidance_only": False,
            },
        )

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    class _NoopDB:
        def add(self, _):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

    app_module.chat(app_module.ChatRequest(query="fees?", session_id="s1"), db=_NoopDB())
    app_module.chat(app_module.ChatRequest(query="syllabus?", session_id="s1"), db=_NoopDB())

    assert len(fetch_calls) == 1
    assert captured_headers == [
        {"Authorization": f"Bearer {app_module._cached_id_token[0]}"},
        {"Authorization": f"Bearer {app_module._cached_id_token[0]}"},
    ]


def test_sliding_window_rate_limiter_enforces_limit_and_recovers():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60.0)
    assert limiter.check("1.2.3.4", now=100.0) is None
    assert limiter.check("1.2.3.4", now=110.0) is None
    retry_after = limiter.check("1.2.3.4", now=120.0)
    assert retry_after == 40
    # Different IP is unaffected.
    assert limiter.check("5.6.7.8", now=120.0) is None
    # Once the first hit ages out (> 60s), requests succeed again.
    assert limiter.check("1.2.3.4", now=161.0) is None


def test_chat_endpoint_rate_limits_by_x_forwarded_for(monkeypatch):
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60.0)
    monkeypatch.setattr(app_module, "rate_limiter", limiter)
    monkeypatch.setattr(app_module, "CHATBOT_AUTH", "")

    def fake_post(url, *, json, timeout):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "answer": "ok",
                "domain": "D5",
                "confidence": 0.9,
                "sources": [],
                "guidance_only": False,
            },
        )

    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    class _NoopDB:
        def add(self, _):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

    app_module.app.dependency_overrides[get_db] = lambda: _NoopDB()
    try:
        client = TestClient(app_module.app)
        headers_ip1 = {"X-Forwarded-For": "203.0.113.10, 10.0.0.1"}
        headers_ip2 = {"X-Forwarded-For": "203.0.113.20, 10.0.0.1"}

        assert client.post("/chat", json={"query": "q1", "session_id": "s1"}, headers=headers_ip1).status_code == 200
        assert client.post("/chat", json={"query": "q2", "session_id": "s1"}, headers=headers_ip1).status_code == 200

        blocked = client.post("/chat", json={"query": "q3", "session_id": "s1"}, headers=headers_ip1)
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) >= 1

        # Separate client IP still goes through.
        assert client.post("/chat", json={"query": "q1", "session_id": "s2"}, headers=headers_ip2).status_code == 200
    finally:
        app_module.app.dependency_overrides.clear()
