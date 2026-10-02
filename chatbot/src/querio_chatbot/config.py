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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_CHAT_MODEL = os.environ.get("GROQ_CHAT_MODEL", "openai/gpt-oss-120b")

# Chat providers for routing and answering, tried in this order until one succeeds. Providers
# without an API key are skipped. Embeddings and OCR always use Gemini.
CHAT_PROVIDERS = tuple(
    name.strip().lower() for name in os.environ.get("CHAT_PROVIDERS", "gemini,groq").split(",") if name.strip()
)


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
        description=(
            "Attendance requirements and penalties for low attendance, leave policy (including medical "
            "leave) and how the leave process works, attendance/leave for taking part in external or "
            "university-level events, parent meetings and attendance reports, detention, and the "
            "attendance undertaking."
        ),
        data_dir=DATA_ROOT / "D6_leave_attendance",
        guidance_only=True,
    ),
    "D4": Domain(
        code="D4",
        name="Career, NOC & Placement",
        description=(
            "Campus placements: eligibility, placement rules and penalties (one student-one job, dress "
            "code, conduct, refusing or not joining an offer), the ₹25,000 placement security-deposit "
            "cheque and parent undertaking, drive types (CDPC, self-sourced, pool campus), participating "
            "companies and packages, job descriptions/roles, and the no-objection certificate (NOC) "
            "process for internships and placements."
        ),
        data_dir=DATA_ROOT / "D4_career_noc",
        guidance_only=True,
    ),
}

# Real topics that exist at the college but aren't wired up as active domains yet (D1-D3).
# The classifier is told about these explicitly so it routes them to UNROUTED instead of
# force-fitting them into an active domain just because it's the closest available option.
INACTIVE_DOMAIN_TOPICS = "co-curricular activities/clubs, certifications, and extra-curricular activities/sports"

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
