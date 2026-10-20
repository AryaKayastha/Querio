# Chatbot (Arya)

Domain router + retrieval engine + LLM integration for Querio. Currently scoped to **D4 (Career, NOC & Placement)**, **D5 (Formal Education)**, and **D6 (Leave Management & Attendance)** — the domains with usable source data. Adding D1–D3 later means: drop their documents in `../data/<domain>/`, add the domain to `DOMAINS` in `src/querio_chatbot/config.py`, and ingest it — no router/retrieval code changes required.

Stack: **Gemini** (LLM + embeddings) · **Groq** (fallback LLM) · **LangGraph** (classify → retrieve → answer graph) · **Chroma** (per-domain vector store namespaces) · **FastAPI** (service boundary for `backend/` to call).

## Setup

```powershell
cd chatbot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Fill in `GEMINI_API_KEY` in `.env`. Optionally add `GROQ_API_KEY` (free at console.groq.com): routing and answers then fall back to Groq whenever a Gemini call fails (timeout, overload, quota). `CHAT_PROVIDERS` sets the order — e.g. `groq,gemini` to make Groq primary. Embeddings and OCR always use Gemini, since the vector store holds Gemini embeddings.

## Ingest documents into the vector store

Put source docs in the domain folders under `../data/` (see [`../data/README.md`](../data/README.md)), then run:

```powershell
python -m querio_chatbot.ingestion.ingest          # all domains
python -m querio_chatbot.ingestion.ingest D4 D6    # only these domains
```

Collections live in `vectorstore/` (gitignored — each teammate builds their own; don't commit it). Ingestion syncs each domain's collection with its documents, so it is safe to re-run any time:

- **Only new or changed chunks are embedded.** Chunks already stored are skipped, so after pulling new documents a re-run spends embedding quota only on what changed.
- **Stale chunks are removed** (edited or deleted documents, duplicate copies) at no embedding cost.
- **An interrupted run resumes.** Failed embedding calls are retried; if a run still stops (quota, network, Gemini overload), run the same command again.
- **A different embedding model is refused.** Each collection records the model that built it. If `GEMINI_EMBEDDING_MODEL` differs, ingestion stops instead of mixing incompatible vectors — delete `vectorstore/` and re-run to rebuild.

A full build from scratch is ~950 embeddings (D5 892, D4 47, D6 12), close to the free-tier daily embedding limit — if it stops partway, re-run it the next day and it continues where it left off.

**Semester course lists:** each semester's subject list lives in only one or two table pages of the booklets, which rarely name the semester and are outnumbered by detailed per-subject syllabus pages. `../data/D5_formal_education/Semester_N_Courses.md` hold curated transcriptions of those tables so "subjects for semester N" retrieves the right list. Update them when a new booklet is released.

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
  "domain": "D4 | D5 | D6 | UNROUTED",
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
