# Backend (Nancy)

<<<<<<< Updated upstream
API, query logging pipeline, admin document-management panel, database schema (PostgreSQL). See [`Project_Details/03_data_requirements.md`](../Project_Details/03_data_requirements.md) §5 for the suggested `query_log` and `document` table schemas.
=======
Querio's backend is the public FastAPI API boundary for the frontend. It forwards
chat requests to the standalone `chatbot/` service, which owns classification,
retrieval, ingestion, and answer generation.
>>>>>>> Stashed changes

Calls `chatbot/`'s `POST /chat` endpoint for answers — see the root [`README.md`](../README.md) for the integration contract.

<<<<<<< Updated upstream
Not yet scaffolded — set up your stack of choice here.
=======
```text
backend/
├── README.md
├── .env
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

The backend does not run the router, retrieval, ingestion, or Gemini calls. Those
responsibilities belong to `chatbot/`.

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Set `CHATBOT_API_URL=http://localhost:8001` in `backend/.env` when using the local
chatbot service. Gemini configuration and document ingestion belong to `chatbot/`.

## Run the service

```powershell
uvicorn querio_backend.bridge:app --reload --port 8000
```

Start the chatbot separately on port `8001` before starting the backend:

```powershell
cd ..\chatbot
uvicorn querio_chatbot.app:app --reload --port 8001
```

The local request flow is:

`frontend:5173` → `backend:8000` → `chatbot:8001`

Test it with:

```powershell
curl -Method Post http://localhost:8000/chat -Headers @{"Content-Type"="application/json"} -Body '{"query":"How many electives can I choose this semester?"}'
```

## API contract

`POST /chat`

Request body:

```json
{ "query": "string" }
```

Response body:

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

`GET /health` checks the chatbot dependency and returns `status: "ok"` only when
the chatbot is healthy. If the backend is running but the chatbot is unavailable,
it returns `status: "degraded"`.

```json
{ "status": "ok" }
```

## Tests

```powershell
pytest
```
>>>>>>> Stashed changes
