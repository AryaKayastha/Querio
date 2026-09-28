# Backend (Nancy)

Thin FastAPI bridge that is the public API boundary for the frontend. It forwards chat requests to the standalone `chatbot/` service, which owns classification, retrieval, ingestion, and answer generation.

Query logging now persists to PostgreSQL (see `db/schema.sql` and `Project_Details/03_data_requirements.md` §5). Future work for this lane: admin document-management panel backed by the `document` table.

## Layout

```text
backend/
├── README.md
├── .env.example
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml       # local Postgres for dev
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── querio_backend/
│       ├── __init__.py
│       ├── bridge.py
│       ├── bridge_config.py
│       ├── session_store.py
│       └── db/
│           ├── models.py    # SQLAlchemy models (query_log, document)
│           ├── engine.py    # engine/session factory
│           └── schema.sql   # reference DDL, mirrors the Alembic migration
└── tests/
    └── test_chatbot_proxy.py
```

## What it does

- Exposes `POST /chat` and `GET /health`
- Forwards chat requests to the chatbot service
- Preserves the chatbot response contract for the frontend
- Reports a degraded health status when the chatbot is unavailable
- Logs every chat query to Postgres (`query_log`) for department analytics — question, matched domain, confidence, resolved, sources. Analytics-only: no workflow/status fields (see `Project_Details/04_scope_and_guardrails.md`).

The backend does **not** run the router, retrieval, ingestion, or Gemini calls. Those belong in `chatbot/`.

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Set `CHATBOT_API_URL=http://localhost:8001` in `backend/.env`.

### Database

Start a local Postgres (Docker Desktop must be running):

```powershell
docker compose up -d
```

Apply migrations:

```powershell
alembic upgrade head
```

`DATABASE_URL` in `.env` defaults to `postgresql+psycopg://querio:querio@localhost:5432/querio`, matching `docker-compose.yml`. `CONFIDENCE_THRESHOLD` (default `0.6`) must match `chatbot/src/querio_chatbot/config.py`'s value — it's how the backend derives `resolved` for logging, since the chat response itself doesn't carry that flag.

Adding a model field later: edit `db/models.py`, then `alembic revision --autogenerate -m "..."` and review the generated migration before `alembic upgrade head`.

## Run the service

```powershell
uvicorn querio_backend.bridge:app --reload --port 8000
```

**Ports:** backend bridge **8000** · chatbot **8001** · frontend **5173**. Do not point the frontend at 8001.

Start the chatbot on port `8001` first:

```powershell
cd ..\chatbot
uvicorn querio_chatbot.app:app --reload --port 8001
```

Request flow: `frontend:5173` → `backend:8000` → `chatbot:8001`

```powershell
curl -Method Post http://localhost:8000/chat -Headers @{"Content-Type"="application/json"} -Body '{"query":"How many electives can I choose this semester?","session_id":"demo-session"}'
```

## API contract

`POST /chat`

```json
{ "query": "string", "session_id": "string" }
```

```json
{
  "answer": "string",
  "domain": "D5 | D6 | UNROUTED",
  "confidence": 0.92,
  "sources": [
    {
      "source_name": "string",
      "source_section": "string",
      "source_url": "https://example.edu/source"
    }
  ],
  "guidance_only": false
}
```

`GET /health` returns `status: "ok"` only when the chatbot is healthy; otherwise `status: "degraded"`.

## Tests

Bridge/proxy tests live only under `backend/tests/` (this package).

Chatbot/RAG tests live under `chatbot/tests/` — do not put them here.

```powershell
pytest
```
