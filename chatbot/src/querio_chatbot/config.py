import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CHATBOT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = CHATBOT_ROOT.parent / "data"
VECTORSTORE_DIR = CHATBOT_ROOT / "vectorstore"


def collection_name(domain_code: str) -> str:
    """Return a stable Chroma collection name for a domain."""
    return f"domain_{domain_code}"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_CHAT_MODEL = os.environ.get("GEMINI_CHAT_MODEL", "gemini-flash-lite-latest")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")


@dataclass(frozen=True)
class Domain:
    code: str
    name: str
    description: str
    data_dir: Path
    guidance_only: bool


# Only domains with usable source data are active. Add a domain here (and drop its
# documents in ../data/<dir>/) to bring it online -- no router/retrieval code changes needed.
DOMAINS: dict[str, Domain] = {
    "D5": Domain(
        code="D5",
        name="Formal Education",
        description=(
            "Subject/syllabus queries, electives, teaching-learning process, academic "
            "regulations, admissions counselling, scholarships, and semester fee payment "
            "schedules."
        ),
        data_dir=DATA_ROOT / "D5_formal_education",
        guidance_only=False,
    ),
    "D6": Domain(
        code="D6",
        name="Leave Management & Attendance",
        description="Leave policy, attendance shortage/condoning rules, how the leave process works.",
        data_dir=DATA_ROOT / "D6_leave_attendance",
        guidance_only=True,
    ),
}

# Real topics that exist at the college but aren't wired up as active domains yet (D1-D4).
# The classifier is told about these explicitly so it routes them to UNROUTED instead of
# force-fitting them into D5/D6 just because they're the closest available option.
INACTIVE_DOMAIN_TOPICS = (
    "co-curricular activities/clubs, certifications, extra-curricular activities/sports, "
    "and career/internship/placement (including NOC)"
)

# Below this, the router treats the query as ambiguous and asks the student to
# clarify instead of committing to a domain -- see 02_architecture.md §2.2.
CONFIDENCE_THRESHOLD = 0.6

# Max number of prior user+assistant turn *pairs* (i.e. up to 2x this many history
# entries) the router will use as conversational context for a follow-up question.
HISTORY_TURN_LIMIT = 3

GUIDANCE_ONLY_SYSTEM_NOTE = (
    "This domain is guidance-only. Explain the process, policy, eligibility, required "
    "documents, and timelines, and point the student to the right contact/procedure. "
    "Never claim to submit, approve, reject, route, or track a request, and never imply "
    "an action was taken on the student's behalf."
)
