# Chatbot (Arya)

Domain router + retrieval engine + LLM integration for Querio. Currently scoped to **D5 (Formal Education)** and **D6 (Leave Management & Attendance)** — the two domains with usable source data. Adding D1–D4 later means: drop their documents in `../data/<domain>/`, add the domain to `DOMAINS` in `src/querio_chatbot/config.py`, and re-ingest — no router/retrieval code changes required.

Stack: **Gemini** (LLM + embeddings) · **LangGraph** (classify → retrieve → answer graph) · **Chroma** (per-domain vector store namespaces) · **FastAPI** (service boundary for `backend/` to call).

## Setup

```powershell
cd chatbot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Fill in `GEMINI_API_KEY` in `.env`.

## Ingest documents into the vector store

Put source docs in `../data/D5_formal_education/` and `../data/D6_leave_attendance/` (see [`../data/README.md`](../data/README.md)), then run:

```powershell
python -m querio_chatbot.ingestion.ingest
```

This (re)builds the Chroma collections in `vectorstore/` (gitignored — regenerate, don't commit).

## Run the service

```powershell
uvicorn querio_chatbot.app:app --reload --port 8001
```

**Ports:** chatbot **8001** · backend bridge **8000** · frontend **5173**. Curl this service on **8001**; the browser should only talk to the backend on **8000**.

The frontend does not call this service directly. The public request flow is:

`frontend:5173` → `backend:8000` → `chatbot:8001`

```powershell
curl -Method Post http://localhost:8001/chat -Headers @{"Content-Type"="application/json"} -Body '{"query":"How many electives can I choose this semester?"}'
```

## Integration contract

`POST /chat` — request `{"query": string}`, response:

```json
{
  "answer": "string",
  "domain": "D5 | D6 | UNROUTED",
  "confidence": 0.92,
  "sources": [
    {
      "source_name": "...",
      "source_section": "...",
      "source_url": "https://example.edu/source"
    }
  ],
  "guidance_only": false
}
```

When `confidence` is below the router's threshold (`CONFIDENCE_THRESHOLD` in `config.py`, currently 0.6), `domain` still reflects the router's best guess but `answer` is a clarifying question instead of a grounded answer — treat this case as `resolved: false` for logging purposes.

`backend/` calls this endpoint and is responsible for persisting `{question, matched_domain, resolved, top_sources}` into the query log — this service does not write to Postgres itself.

## Manual testing (CLI)

```powershell
python -m querio_chatbot.scripts.chat_cli
```

## Evaluation

- **Routing accuracy** — `python -m querio_chatbot.eval.routing_accuracy`
- **D6 guidance-only boundary** — `tests/test_guidance_only_boundary.py` (skipped unless `GEMINI_API_KEY` is set)
- **Hybrid retrieval** — `tests/test_hybrid_retrieval.py` covers BM25/RRF weighting and re-rank helpers without needing Gemini
- **Answer quality** — `python -m querio_chatbot.eval.answer_quality` runs RAGAS faithfulness, answer relevance, context precision, and context recall against `src/querio_chatbot/eval/golden_qa.py`, reporting D5 and D6 separately

Backend bridge proxy tests live in `backend/tests/` (not here).

## Layout

```text
src/querio_chatbot/
├── config.py
├── ingestion/ingest.py
├── retrieval/retriever.py   # hybrid semantic + BM25, weighted RRF, light re-rank
├── llm/gemini_client.py
├── router/router.py
├── eval/
├── scripts/chat_cli.py
└── app.py
```
