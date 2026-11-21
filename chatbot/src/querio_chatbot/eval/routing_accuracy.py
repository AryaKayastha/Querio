"""Measures routing accuracy against ROUTING_TEST_SET. Calls the real classifier (needs a chat API key).

Reports overall accuracy, accuracy per kind of case (basic, overlap, typo, ...) and a confusion
matrix. With --repeat N each question is classified N times and only counts as correct if every
run is right, which exposes answers that flip between runs (QRO-05).

Usage: python -m querio_chatbot.eval.routing_accuracy [--repeat 3]
"""

import argparse
from collections import Counter, defaultdict
from collections.abc import Callable

from querio_chatbot.config import DOMAINS
from querio_chatbot.eval.routing_test_set import ROUTING_TEST_SET

LABELS = [*sorted(DOMAINS), "UNROUTED"]


def _default_classify(query: str) -> dict:
    from querio_chatbot.router.router import classify_node  # imported here so tests need no model setup

    return classify_node({"query": query})


def confusion_table(confusion: Counter) -> str:
    """Expected domain down the side, predicted across the top; "." for zero."""
    labels = sorted(set(LABELS) | {label for pair in confusion for label in pair}, key=_label_order)
    width = max(len(label) for label in labels) + 2
    lines = ["expected \\ predicted".ljust(22) + "".join(label.rjust(width) for label in labels)]
    for expected in labels:
        cells = (confusion[(expected, predicted)] for predicted in labels)
        lines.append(expected.ljust(22) + "".join((str(count) if count else ".").rjust(width) for count in cells))
    return "\n".join(lines)


def _label_order(label: str) -> tuple[int, str]:
    return (LABELS.index(label), label) if label in LABELS else (len(LABELS), label)


def run(repeat: int = 1, classify: Callable[[str], dict] = _default_classify, cases: list[dict] | None = None) -> float:
    cases = ROUTING_TEST_SET if cases is None else cases
    confusion: Counter = Counter()
    by_kind: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # kind -> [correct, total]
    mismatches = []

    for case in cases:
        expected = case["expected_domain"]
        results = [classify(case["query"]) for _ in range(repeat)]
        predicted = [result["domain"] for result in results]
        confusion.update((expected, domain) for domain in predicted)
        tally = by_kind[case.get("kind", "basic")]
        tally[1] += 1
        if all(domain == expected for domain in predicted):
            tally[0] += 1
        else:
            confidences = ", ".join(f"{r['domain']}@{r['confidence']:.2f}" for r in results)
            mismatches.append(f"  [{expected} -> {confidences}] {case['query']}")

    correct = sum(c for c, _ in by_kind.values())
    total = len(cases)
    accuracy = correct / total if total else 0.0
    runs = f", {repeat} runs each, all must match" if repeat > 1 else ""
    print(f"Routing accuracy: {correct}/{total} = {accuracy:.1%} (target >= 90%{runs})\n")
    print("By kind:")
    for kind, (kind_correct, kind_total) in sorted(by_kind.items()):
        print(f"  {kind:<14} {kind_correct}/{kind_total}")
    print(f"\nConfusion matrix (all runs):\n{confusion_table(confusion)}")
    if mismatches:
        print("\nMismatches (expected -> predicted@confidence per run):")
        print("\n".join(mismatches))
    return accuracy


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Routing accuracy on ROUTING_TEST_SET")
    parser.add_argument("--repeat", type=int, default=1, help="classify each question N times")
    run(repeat=parser.parse_args(argv).repeat)


if __name__ == "__main__":
    main()
