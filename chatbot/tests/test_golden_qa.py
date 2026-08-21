import pytest

from querio_chatbot.eval.golden_qa import GOLDEN_QA_SET, validate_golden_qa


def test_golden_set_has_cases_for_each_active_evaluation_domain():
    assert {case["domain"] for case in GOLDEN_QA_SET} == {"D5", "D6"}
    validate_golden_qa()


def test_golden_set_ids_are_unique_and_questions_are_nonempty():
    ids = [case["id"] for case in GOLDEN_QA_SET]
    assert len(ids) == len(set(ids))
    assert all(case["question"].strip() for case in GOLDEN_QA_SET)
    assert all(case["reference_answer"].strip() for case in GOLDEN_QA_SET)


def test_validate_golden_qa_rejects_missing_fields():
    with pytest.raises(ValueError, match="missing"):
        validate_golden_qa([{"id": "bad", "domain": "D5", "question": "Question"}])


def test_validate_golden_qa_rejects_duplicate_ids():
    case = GOLDEN_QA_SET[0].copy()
    with pytest.raises(ValueError, match="Duplicate"):
        validate_golden_qa([case, case.copy()])
