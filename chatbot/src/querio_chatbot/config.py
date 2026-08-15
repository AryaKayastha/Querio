import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CHATBOT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = CHATBOT_ROOT.parent / "data"
VECTORSTORE_DIR = CHATBOT_ROOT / "vectorstore"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_CHAT_MODEL = os.environ.get("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")


@dataclass(frozen=True)
class Domain:
    code: str
    name: str
    data_dir: Path
    guidance_only: bool


# Only domains with usable source data are active. Add a domain here (and drop its
# documents in ../data/<dir>/) to bring it online -- no router/retrieval code changes needed.
DOMAINS: dict[str, Domain] = {
    "D5": Domain(
        code="D5",
        name="Formal Education",
        data_dir=DATA_ROOT / "D5_formal_education",
        guidance_only=False,
    ),
    "D6": Domain(
        code="D6",
        name="Leave Management & Attendance",
        data_dir=DATA_ROOT / "D6_leave_attendance",
        guidance_only=True,
    ),
}

GUIDANCE_ONLY_SYSTEM_NOTE = (
    "This domain is guidance-only. Explain the process, policy, eligibility, required "
    "documents, and timelines, and point the student to the right contact/procedure. "
    "Never claim to submit, approve, reject, route, or track a request, and never imply "
    "an action was taken on the student's behalf."
)
