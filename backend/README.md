# Backend (Nancy)

Thin FastAPI bridge that is the public API boundary for the frontend. It forwards chat requests to the standalone `chatbot/` service, which owns classification, retrieval, ingestion, and answer generation.

Future work for this lane: query logging pipeline, admin document-management panel, and PostgreSQL schema. See [`Project_Details/03_data_requirements.md`](../Project_Details/03_data_requirements.md) §5 for the suggested `query_log` and `document` table schemas.

## Layout

```text
backend/
├── README.md
├── .env.example
├── pyproject.toml
├── requirements.txt
├── src/
│   └── querio_backend/
│       ├── __init__.py
│       ├── bridge.py
│       └── bridge_config.py
└── tests/
    └── test_chatbot_proxy.py
```

## What it does

- Exposes `POST /chat` and `GET /health`
- Forwards chat requests to the chatbot service
- Preserves the chatbot response contract for the frontend
- Reports a degraded health status when the chatbot is unavailable

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

## Run the service

```powershell
uvicorn querio_backend.bridge:app --reload --port 8000
```

Start the chatbot on port `8001` first:

```powershell
cd ..\chatbot
uvicorn querio_chatbot.app:app --reload --port 8001
```

Request flow: `frontend:5173` → `backend:8000` → `chatbot:8001`

```powershell
curl -Method Post http://localhost:8000/chat -Headers @{"Content-Type"="application/json"} -Body '{"query":"How many electives can I choose this semester?"}'
```

## API contract

`POST /chat`

```json
{ "query": "string" }
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

```powershell
pytest
```
