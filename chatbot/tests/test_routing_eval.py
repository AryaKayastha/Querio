"""QRO-14: the routing test set is big and varied enough to catch real misroutes, and the evaluator
reports per-kind accuracy, a confusion matrix and flips across repeated runs. No model calls."""

import itertools
from collections import Counter

from querio_chatbot.config import DOMAINS
from querio_chatbot.eval import routing_accuracy
from querio_chatbot.eval.routing_test_set import ROUTING_TEST_SET

KINDS = {"qa-regression", "overlap", "typo", "hinglish", "gujarati", "request", "out-of-scope"}


def test_set_has_at_least_80_cases_with_every_kind_of_hard_case():
    assert len(ROUTING_TEST_SET) >= 80
    assert {case.get("kind", "basic") for case in ROUTING_TEST_SET} == KINDS | {"basic"}
    assert sum(case.get("kind") == "overlap" for case in ROUTING_TEST_SET) >= 15


def test_every_case_has_a_valid_label_and_a_unique_question():
    assert all(case["expected_domain"] in {*DOMAINS, "UNROUTED"} for case in ROUTING_TEST_SET)
    queries = [case["query"].lower() for case in ROUTING_TEST_SET]
    assert len(queries) == len(set(queries))


def test_qa_misroutes_are_in_the_set():
    labels = {case["query"]: case["expected_domain"] for case in ROUTING_TEST_SET}
    assert labels["What is the penalty if my fee cheque bounces?"] == "D5"  # QRO-04
    assert labels["What is the minimum attendance needed for placement eligibility?"] == "D4"  # QRO-05


CASES = [
    {"query": "a", "expected_domain": "D4"},
    {"query": "b", "expected_domain": "D6", "kind": "overlap"},
    {"query": "c", "expected_domain": "UNROUTED", "kind": "out-of-scope"},
]


def test_run_reports_accuracy_by_kind_and_a_confusion_matrix(capsys):
    predictions = {"a": "D4", "b": "D4", "c": "UNROUTED"}  # "b" misrouted to D4
    accuracy = routing_accuracy.run(
        classify=lambda query: {"domain": predictions[query], "confidence": 0.9}, cases=CASES
    )
    out = capsys.readouterr().out

    assert accuracy == 2 / 3
    assert "overlap        0/1" in out
    assert "basic          1/1" in out
    assert "[D6 -> D4@0.90] b" in out
    assert "Confusion matrix" in out


def test_repeat_counts_a_question_wrong_if_any_run_flips(capsys):
    flips = itertools.cycle(["D4", "D6"])  # QRO-05: same question, different domain per run
    accuracy = routing_accuracy.run(
        repeat=2, classify=lambda query: {"domain": next(flips), "confidence": 0.85}, cases=CASES[:1]
    )
    assert accuracy == 0.0
    assert "[D4 -> D4@0.85, D6@0.85] a" in capsys.readouterr().out


def test_confusion_table_puts_expected_down_the_side_and_predicted_across():
    table = routing_accuracy.confusion_table(Counter({("D6", "D4"): 2, ("D4", "D4"): 3}))
    header, *rows = table.splitlines()
    assert header.split()[-7:] == [*sorted(DOMAINS), "UNROUTED"]
    d6_row = next(row for row in rows if row.startswith("D6"))
    cells = d6_row.split()[1:]
    assert cells[sorted(DOMAINS).index("D4")] == "2"
    assert cells.count(".") == len(cells) - 1
