import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_ROOT / ".env", override=True)

CHATBOT_API_URL = os.environ.get("CHATBOT_API_URL", "http://localhost:8001").rstrip("/")
CHATBOT_TIMEOUT_SECONDS = float(os.environ.get("CHATBOT_TIMEOUT_SECONDS", "14"))
