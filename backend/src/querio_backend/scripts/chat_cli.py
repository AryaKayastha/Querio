"""Interactive CLI for manually testing the router/retrieval/generation graph
once GEMINI_API_KEY is set and documents have been ingested.

Usage: python -m querio_backend.scripts.chat_cli
"""

from querio_backend.router.router import answer_query


def main() -> None:
    print("Querio chatbot CLI -- type a question (D5/D6), or 'quit' to exit.")
    while True:
        query = input("\n> ").strip()
        if query.lower() in {"quit", "exit"}:
            break
        if not query:
            continue
        result = answer_query(query)
        print(f"[domain={result.get('domain')} confidence={result.get('confidence', 0):.2f}]")
        print(result.get("answer"))


if __name__ == "__main__":
    main()
