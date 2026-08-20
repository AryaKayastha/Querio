# Backend

Querio's backend contains the FastAPI service, routing graph, retrieval pipeline, ingestion scripts, and evaluation harness.

## Folder structure

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
│       ├── app.py
│       ├── config.py
│       ├── eval/
│       │   ├── __init__.py
│       │   ├── routing_accuracy.py
│       │   └── routing_test_set.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   └── ingest.py
│       ├── llm/
│       │   ├── __init__.py
│       │   └── gemini_client.py
│       ├── retrieval/
│       │   ├── __init__.py
│       │   └── retriever.py
│       ├── router/
│       │   ├── __init__.py
│       │   └── router.py
│       └── scripts/
│           ├── __init__.py
│           └── chat_cli.py
└── tests/
		├── fixtures/
		│   └── sample_doc.md
		├── test_guidance_only_boundary.py
		├── test_ingestion.py
		└── test_router_fallback.py
```

## What it does

- Exposes `POST /chat` and `GET /health`
- Routes questions into D5 or D6 when appropriate
- Retrieves supporting passages from Chroma
- Generates grounded answers with Gemini
- Includes a guidance-only boundary for domains that must never perform transactions

## Current domain coverage

Active domains:

- D5: Formal Education
- D6: Leave Management & Attendance

Inactive but reserved for future data:

- D1: Clubs
- D2: Certifications
- D3: Extra-curricular activities and sports
- D4: Career, internship, placement, and NOC

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Set `GEMINI_API_KEY` in `backend/.env` before running the service.

## Prepare the vector store

Put source documents in:

- `../data/D5_formal_education/`
- `../data/D6_leave_attendance/`

Then ingest them:

```powershell
python -m querio_backend.ingestion.ingest
```

This rebuilds the Chroma vector store in `vectorstore/`.

## Run the service

```powershell
uvicorn querio_backend.app:app --reload --port 8000
```

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
			"source_section": "string"
		}
	],
	"guidance_only": false
}
```

`GET /health`

```json
{ "status": "ok" }
```

## Useful commands

Run the CLI:

```powershell
python -m querio_backend.scripts.chat_cli
```

Run the routing evaluation:

```powershell
python -m querio_backend.eval.routing_accuracy
```

Run tests:

```powershell
pytest
```
