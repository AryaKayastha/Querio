"""QRO-18: Swagger UI, ReDoc and the OpenAPI schema are off unless ENABLE_API_DOCS is set."""

import pytest
from fastapi.testclient import TestClient

from querio_backend import bridge, bridge_config

client = TestClient(bridge.app)


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_served_only_when_enabled(path):
    assert client.get(path).status_code == (200 if bridge_config.ENABLE_API_DOCS else 404)


@pytest.mark.parametrize(
    ("value", "enabled"),
    [(None, False), ("", False), ("false", False), ("0", False), ("true", True), ("1", True), (" Yes ", True)],
)
def test_api_docs_flag_is_off_unless_explicitly_enabled(monkeypatch, value, enabled):
    if value is None:
        monkeypatch.delenv("ENABLE_API_DOCS", raising=False)
    else:
        monkeypatch.setenv("ENABLE_API_DOCS", value)
    assert bridge_config.env_flag("ENABLE_API_DOCS") is enabled
