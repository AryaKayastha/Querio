# Chatbot (Arya)

Domain router + retrieval engine + LLM integration for Querio. Currently scoped to **D5 (Formal Education)** and **D6 (Leave Management & Attendance)** — the two domains with usable source data. Adding D1–D4 later means: drop their documents in `../data/<domain>/`, add the domain to `DOMAINS` in `src/querio_chatbot/config.py`, and re-ingest — no router/retrieval code changes required.

Stack: **Gemini** (LLM + embeddings) · **LangGraph** (classify → retrieve → answer graph) · **Chroma** (per-domain vector store namespaces) · **FastAPI** (service boundary for `backend/` to call).

## Setup

```bash
cd chatbot
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
pip install -e .
copy .env.example .env         # then fill in GEMINI_API_KEY
```

## Ingest documents into the vector store

Put source docs in `../data/D5_formal_education/` and `../data/D6_leave_attendance/` (see [`../data/README.md`](../data/README.md) for the expected format), then run:

```bash
python -m querio_chatbot.ingestion.ingest
```

This (re)builds the Chroma collections in `vectorstore/` (gitignored — regenerate, don't commit).

## Run the service

```bash
<<<<<<< Updated upstream
uvicorn querio_chatbot.app:app --reload --port 8000
```

=======
uvicorn querio_chatbot.app:app --reload --port 8001
```

The frontend does not call this service directly. The public request flow is:

`frontend:5173` → `backend:8000` → `chatbot:8001`

>>>>>>> Stashed changes
Then:

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"query\": \"How many electives can I choose this semester?\"}"
```

## Integration contract

`POST /chat` — request `{"query": string}`, response:

```json
{
  "answer": "string — the generated answer",
  "domain": "D5 | D6 | UNROUTED",
  "confidence": 0.92,
<<<<<<< Updated upstream
  "sources": [{"source_name": "...", "source_section": "..."}],
=======
  "sources": [{"source_name": "...", "source_section": "...", "source_url": "https://example.edu/source"}],
>>>>>>> Stashed changes
  "guidance_only": false
}
```

When `confidence` is below the router's threshold (`CONFIDENCE_THRESHOLD` in `config.py`, currently 0.6), `domain` still reflects the router's best guess but `answer` is a clarifying question instead of a grounded answer — treat this case as `resolved: false` for logging purposes.

`backend/` (Nancy) calls this endpoint and is responsible for persisting `{question, matched_domain, resolved, top_sources}` into the query log — this service does not write to Postgres itself, it only answers.

## Manual testing (CLI)

For quick interactive testing without waiting on `backend/`'s integration:

```bash
python -m querio_chatbot.scripts.chat_cli
```

## Evaluation

- **Routing accuracy** — `python -m querio_chatbot.eval.routing_accuracy` runs the labeled set in `eval/routing_test_set.py` (D5/D6 + out-of-scope queries) against the classifier and reports accuracy + mismatches. Target ≥ 90% per `Project_Details/05_evaluation_and_testing.md` §2. Requires `GEMINI_API_KEY`.
- **D6 guidance-only boundary compliance** — `tests/test_guidance_only_boundary.py` covers the four required categories from `Project_Details/04_scope_and_guardrails.md` §6 (direct action, status/tracking, leading/implicit, legitimate guidance) against fixture documents, so it doesn't need to wait on the real D6 corpus. Skipped automatically unless `GEMINI_API_KEY` is set.
- Golden Q&A / RAGAS evaluation is not yet built — it needs the real D5/D6 corpora to be meaningful, so it's the next thing to scaffold once documents land.

## Layout

```
src/querio_chatbot/
├── config.py                    domains, paths, model names, confidence threshold (env-driven)
├── ingestion/ingest.py           chunk + embed documents per domain into Chroma
├── retrieval/retriever.py        per-domain Chroma retriever
├── llm/gemini_client.py          thin Gemini chat + embeddings wrapper
├── router/router.py              LangGraph graph: classify -> retrieve -> generate, with a
│                                 confidence-based clarifying-question fallback for ambiguous queries
├── eval/routing_test_set.py      labeled {query, expected_domain} pairs
├── eval/routing_accuracy.py      routing accuracy harness
├── scripts/chat_cli.py           interactive manual-testing CLI
└── app.py                        FastAPI service exposing POST /chat
```
