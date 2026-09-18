import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_ROOT / ".env", override=True)

CHATBOT_API_URL = os.environ.get("CHATBOT_API_URL", "http://localhost:8001").rstrip("/")
CHATBOT_TIMEOUT_SECONDS = float(os.environ.get("CHATBOT_TIMEOUT_SECONDS", "25"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://querio:querio@localhost:5432/querio"
)

# Must match chatbot/src/querio_chatbot/config.py's CONFIDENCE_THRESHOLD. The /chat response
# doesn't carry a `resolved` flag directly, so the backend re-derives it from confidence for
# query_log purposes -- keep this in sync if the chatbot's threshold changes.
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.6"))
