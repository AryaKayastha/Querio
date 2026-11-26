import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_ROOT / ".env", override=True)

CHATBOT_API_URL = os.environ.get("CHATBOT_API_URL", "http://localhost:8001").rstrip("/")
CHATBOT_TIMEOUT_SECONDS = float(os.environ.get("CHATBOT_TIMEOUT_SECONDS", "25"))
CHATBOT_AUTH = os.environ.get("CHATBOT_AUTH", "").strip().lower()

_DEFAULT_ALLOWED_ORIGINS = [f"http://localhost:{port}" for port in range(5173, 5178)]


def parse_allowed_origins(raw: str | None) -> list[str]:
    """Parse a comma-separated list of CORS origins, falling back to local Vite ports."""
    if not raw or not raw.strip():
        return list(_DEFAULT_ALLOWED_ORIGINS)
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    return origins or list(_DEFAULT_ALLOWED_ORIGINS)


ALLOWED_ORIGINS = parse_allowed_origins(os.environ.get("ALLOWED_ORIGINS"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10"))


def env_flag(name: str) -> bool:
    """True if the environment variable is set to 1, true, yes or on (any case)."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


# Swagger UI (/docs), ReDoc (/redoc) and the OpenAPI schema (/openapi.json) map every endpoint for
# anyone who can reach the port, so they're off unless turned on for local development.
ENABLE_API_DOCS = env_flag("ENABLE_API_DOCS")

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://querio:querio@localhost:5432/querio"
)

# Must match chatbot/src/querio_chatbot/config.py's CONFIDENCE_THRESHOLD. The /chat response
# doesn't carry a `resolved` flag directly, so the backend re-derives it from confidence for
# query_log purposes -- keep this in sync if the chatbot's threshold changes.
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.6"))
