"""Measures /chat latency under concurrent load against a running chatbot service.

QRO-13 target: p90 under 8 s and max under 25 s with 3 concurrent users. Sends every question in
ROUTING_TEST_SET from --concurrency workers and reports median, p90, max and failed requests. Each
request is a real routed answer, so this spends LLM and embedding quota (one request per question
in the routing set).

Usage: python -m querio_chatbot.eval.latency [--url http://localhost:8001] [--concurrency 3]
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from querio_chatbot.eval.routing_test_set import ROUTING_TEST_SET

TARGET_P90_SECONDS = 8.0
TARGET_MAX_SECONDS = 25.0


def _ask(url: str, query: str, timeout: float) -> tuple[float, int | None]:
    """Seconds taken and HTTP status (None if the request itself failed)."""
    start = time.perf_counter()
    try:
        status = httpx.post(f"{url}/chat", json={"query": query}, timeout=timeout).status_code
    except httpx.HTTPError:
        status = None
    return time.perf_counter() - start, status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8001", help="chatbot service base URL")
    parser.add_argument("--concurrency", type=int, default=3, help="simultaneous users")
    parser.add_argument("--timeout", type=float, default=45.0, help="per-request timeout, like the backend's")
    args = parser.parse_args(argv)

    queries = [case["query"] for case in ROUTING_TEST_SET]
    url = args.url.rstrip("/")
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda query: _ask(url, query, args.timeout), queries))

    durations = [seconds for seconds, _ in results]
    failures = sum(1 for _, status in results if status != 200)
    p90 = statistics.quantiles(durations, n=10)[8]
    worst = max(durations)
    print(f"{len(results)} requests, {args.concurrency} concurrent, {failures} failed")
    print(f"median {statistics.median(durations):.1f} s | p90 {p90:.1f} s | max {worst:.1f} s")

    passed = p90 < TARGET_P90_SECONDS and worst < TARGET_MAX_SECONDS and failures == 0
    print(f"{'PASS' if passed else 'FAIL'} (target: p90 < {TARGET_P90_SECONDS:.0f} s, "
          f"max < {TARGET_MAX_SECONDS:.0f} s, no failures)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
