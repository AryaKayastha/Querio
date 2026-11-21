"""QRO-05: a question touching both placement (D4) and attendance/leave (D6) routes the same way
every time -- D6 if it's about leave-type attendance, D4 otherwise. Model faked."""

import itertools

import pytest

from querio_chatbot.eval.routing_test_set import ROUTING_TEST_SET
from querio_chatbot.router import router
from querio_chatbot.router.router import Classification, _placement_or_leave, classify_node

QRO_05 = "What is the minimum attendance needed for placement eligibility?"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (QRO_05, "D4"),
        ("Does low attendance in placement training stop me from sitting for drives?", "D4"),
        ("Is 75% attendance required to sit for placements?", "D4"),
        ("placement ke liye kitna attendance chahiye?", "D4"),
        ("Is attendance given for days I spend at placement drives?", "D6"),
        ("Will I get attendance for a placement interview day?", "D6"),
        ("Can I miss classes to attend a placement drive?", "D6"),
        ("How many leaves can I take for internship interviews?", "D6"),
        ("Will my attendance be counted if I go for a campus drive?", "D6"),
    ],
)
def test_overlapping_questions_go_to_leave_only_when_they_are_about_leave(query, expected):
    for classified, alternative in [("D4", "D6"), ("D6", "D4"), ("D6", None), ("D4", None)]:
        assert _placement_or_leave(query, classified, alternative) == expected


@pytest.mark.parametrize(
    ("query", "classified"),
    [
        ("What happens if my attendance falls below 75%?", "D6"),  # no placement words
        ("Which company offers the highest package?", "D4"),  # no attendance words
        ("Is 75% attendance required for scholarships?", "D5"),  # classifier chose neither D4 nor D6
    ],
)
def test_questions_outside_the_overlap_keep_the_classifiers_domain(query, classified):
    assert _placement_or_leave(query, classified, None) is None


def _flipping_classifier(monkeypatch, outcomes):
    cycle = itertools.cycle(outcomes)

    def fake_invoke(build, prompt):
        domain, alternative, confidence = next(cycle)
        return Classification(domain=domain, alternative_domain=alternative, confidence=confidence)

    monkeypatch.setattr(router, "invoke_with_fallback", fake_invoke)


def test_qro_05_question_routes_to_placement_on_every_run(monkeypatch):
    # The QA saw D4, D4, D6, D6 for identical runs; the result must not depend on the classifier's pick.
    _flipping_classifier(monkeypatch, [("D4", "D6", 0.85), ("D6", "D4", 0.85), ("D6", None, 0.85)])
    results = [classify_node({"query": QRO_05}) for _ in range(10)]
    assert [r["domain"] for r in results] == ["D4"] * 10
    assert not any(r["low_confidence"] for r in results)


def test_unsure_between_placement_and_leave_is_decided_instead_of_asked(monkeypatch):
    _flipping_classifier(monkeypatch, [("D6", "D4", 0.4)])
    result = classify_node({"query": "Can I miss classes to attend a placement drive?"})
    assert result["domain"] == "D6"
    assert result["low_confidence"] is False
    assert result["alternative_domain"] is None


def test_routing_set_labels_agree_with_the_rule():
    # Every routing case that touches both domains and is labelled D4 or D6 follows the rule.
    for case in ROUTING_TEST_SET:
        if case["expected_domain"] in {"D4", "D6"}:
            decided = _placement_or_leave(case["query"], case["expected_domain"], None)
            assert decided in {None, case["expected_domain"]}, case["query"]
