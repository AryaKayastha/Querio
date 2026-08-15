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
uvicorn querio_chatbot.app:app --reload --port 8000
```

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
  "sources": [{"source_name": "...", "source_section": "..."}],
  "guidance_only": false
}
```

`backend/` (Nancy) calls this endpoint and is responsible for persisting `{question, matched_domain, resolved, top_sources}` into the query log — this service does not write to Postgres itself, it only answers.

## Layout

```
src/querio_chatbot/
├── config.py           domains, paths, model names (env-driven)
├── ingestion/ingest.py  chunk + embed documents per domain into Chroma
├── retrieval/retriever.py  per-domain Chroma retriever
├── llm/gemini_client.py   thin Gemini chat + embeddings wrapper
├── router/router.py       LangGraph graph: classify -> retrieve -> generate
└── app.py                 FastAPI service exposing POST /chat
```
