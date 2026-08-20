"""Measures routing accuracy against ROUTING_TEST_SET. Requires GEMINI_API_KEY.

Usage: python -m querio_backend.eval.routing_accuracy
"""

from querio_backend.eval.routing_test_set import ROUTING_TEST_SET
from querio_backend.router.router import classify_node


def run() -> float:
    correct = 0
    mismatches = []
    for case in ROUTING_TEST_SET:
        result = classify_node({"query": case["query"]})
        predicted = result["domain"]
        if predicted == case["expected_domain"]:
            correct += 1
        else:
            mismatches.append((case["query"], case["expected_domain"], predicted, result["confidence"]))

    total = len(ROUTING_TEST_SET)
    accuracy = correct / total if total else 0.0
    print(f"Routing accuracy: {correct}/{total} = {accuracy:.1%} (target >= 90%)")
    if mismatches:
        print("\nMismatches (expected -> predicted @ confidence):")
        for query, expected, predicted, confidence in mismatches:
            print(f"  [{expected} -> {predicted} @ {confidence:.2f}] {query}")
    return accuracy


if __name__ == "__main__":
    run()
