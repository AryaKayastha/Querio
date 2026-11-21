"""Golden question/answer cases for retrieval and answer-quality evaluation.

Keep each case grounded in its domain's source documents. Add cases for a domain as its
source corpus becomes available; the evaluator reports scores per domain.
"""

from querio_chatbot.config import DOMAINS

GOLDEN_QA_SET = [
    {
        "id": "d4-dress-code-01",
        "domain": "D4",
        "question": "What is the dress code for placement drives?",
        "reference_answer": (
            "Students must wear formal attire and shoes during the recruitment process; a student not "
            "following the dress code is not allowed to take part in that drive (Placement Guidelines)."
        ),
    },
    # QRO-07: answers added conditions, documents and approvals the guidelines don't state.
    {
        "id": "d4-self-sourced-01",
        "domain": "D4",
        "question": "Can I take a self-sourced offer after I'm already placed through CDPC?",
        "reference_answer": (
            "A self-sourced offer for a student already placed through CDPC is considered only if its package "
            "is at least 5 LPA higher than the existing offer. The guidelines state no other conditions, "
            "documents or approvals for this."
        ),
    },
    {
        "id": "d4-one-job-01",
        "domain": "D4",
        "question": "Can I sit for more placement drives after I'm selected?",
        "reference_answer": (
            "No. The University follows a strict 'one student, one job' policy: once a student is selected, "
            "they are not allowed to participate in further placement drives."
        ),
    },
    {
        "id": "d4-noc-01",
        "domain": "D4",
        "question": "What documents do I need for an NOC?",
        "reference_answer": (
            "For the NOC process and the format of the documents required, contact your department's Training "
            "and Placement Officer (TPO)."
        ),
    },
    {
        "id": "d5-fee-blank-01",
        "domain": "D5",
        "question": "What is the fee for 3rd year mechanical NRI?",
        "reference_answer": (
            "The fee structure lists no amount ('-') for 3rd-year NRI students in ME/Civil/EE, so the fee "
            "isn't given in the document."
        ),
    },
    {
        "id": "d5-fees-01",
        "domain": "D5",
        "question": "What fees are listed for the formal education programmes?",
        "reference_answer": "The answer should report the programme fee information stated in the FeesStructure source.",
    },
    {
        "id": "d5-admission-01",
        "domain": "D5",
        "question": "What information is provided about admission counselling?",
        "reference_answer": "The answer should summarize the admission counselling information in the Admission Counselling Booklet source.",
    },
    {
        "id": "d5-syllabus-01",
        "domain": "D5",
        "question": "What subjects or electives are described for the fifth semester?",
        "reference_answer": "The answer should identify the subjects or electives stated in the fifth-semester source.",
    },
    {
        "id": "d6-attendance-01",
        "domain": "D6",
        "question": "What happens if my attendance falls below the required percentage?",
        "reference_answer": "The answer should explain the attendance-shortage consequences and process stated in the attendance policy.",
    },
    {
        "id": "d6-leave-01",
        "domain": "D6",
        "question": "What documents are required for a leave application?",
        "reference_answer": "The answer should list the documents required by the leave policy.",
    },
    {
        "id": "d6-condonation-01",
        "domain": "D6",
        "question": "How do I apply for condonation of attendance shortage?",
        "reference_answer": "The answer should explain the condonation procedure without claiming to submit or approve a request.",
    },
]


def validate_golden_qa(cases: list[dict] | None = None) -> None:
    """Validate the fields required by the evaluator before making API calls."""
    cases = GOLDEN_QA_SET if cases is None else cases
    required = {"id", "domain", "question", "reference_answer"}
    ids = set()
    for case in cases:
        missing = required - case.keys()
        if missing:
            raise ValueError(f"Golden case {case.get('id', '<unknown>')} is missing: {sorted(missing)}")
        if case["id"] in ids:
            raise ValueError(f"Duplicate golden case id: {case['id']}")
        if case["domain"] not in DOMAINS:
            raise ValueError(f"Unsupported golden case domain: {case['domain']}")
        ids.add(case["id"])
