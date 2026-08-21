"""Golden question/answer cases for retrieval and answer-quality evaluation.

Keep cases grounded in the active D5 and D6 corpora. Add cases for a domain as its
source corpus becomes available; the evaluator reports scores per domain.
"""

GOLDEN_QA_SET = [
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
        if case["domain"] not in {"D5", "D6"}:
            raise ValueError(f"Unsupported golden case domain: {case['domain']}")
        ids.add(case["id"])
