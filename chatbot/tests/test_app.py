"""API-level checks for the chatbot service (:8001), with no model or network calls."""

import pytest
from fastapi.testclient import TestClient

from querio_chatbot import app as app_module
from querio_chatbot import config

client = TestClient(app_module.app)


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
