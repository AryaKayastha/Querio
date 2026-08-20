# Querio

Conversational AI agent answering student questions across six mentor-approved domains of college life, with cited answers pulled from real institutional documents. See [`Project_Details/Querio_Complete_Context.md`](Project_Details/Querio_Complete_Context.md) for full project context.

## Repo layout

This is a monorepo split into three independent lanes so the team can build in parallel:

<<<<<<< Updated upstream
| Folder | Owner | Covers |
|---|---|---|
| [`frontend/`](frontend/) | Jahnavi | Chat UI / web widget |
| [`backend/`](backend/) | Nancy | API, query logging, admin document panel, DB schema |
| [`chatbot/`](chatbot/) | Arya | Domain router, retrieval engine, LLM integration, eval harness |
| [`data/`](data/) | Nancy (gathering), Arya (ingests) | Raw per-domain source documents (D1–D6) |
| [`Project_Details/`](Project_Details/) | — | Planning docs, architecture, scope |
=======
```text
Querio/
├── backend/
│   ├── README.md
│   ├── .env.example
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/
│   │   └── querio_backend/
│   │       ├── app.py
│   │       ├── config.py
│   │       ├── eval/
│   │       ├── ingestion/
│   │       ├── llm/
│   │       ├── retrieval/
│   │       ├── router/
│   │       └── scripts/
│   └── tests/
├── chatbot/
│   ├── README.md
│   ├── .env.example
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/
│   └── tests/
├── data/
│   ├── README.md
│   ├── D1_clubs/
│   ├── D2_certifications/
│   ├── D3_eca_sports/
│   ├── D4_career_noc/
│   ├── D5_formal_education/
│   └── D6_leave_attendance/
├── frontend/
│   ├── README.md
│   ├── .env
│   ├── .env.example
│   ├── package.json
│   └── src/
│       ├── api/
│       ├── assets/
│       ├── components/
│       ├── data/
│       ├── pages/
│       └── utils/
└── Project_Details/
	├── 00_README.md
	├── 01_project_planning.md
	├── 02_architecture.md
	├── 03_data_requirements.md
	├── 04_scope_and_guardrails.md
	└── 05_evaluation_and_testing.md
```
>>>>>>> Stashed changes

Current target: get the chatbot working end-to-end for **D5 (Formal Education)** and **D6 (Leave Management & Attendance)**, since those two domains already have usable source data. D1–D4 will follow as their data is collected.

## Integration contract

<<<<<<< Updated upstream
The `chatbot/` service exposes a `POST /chat` HTTP endpoint (see [`chatbot/README.md`](chatbot/README.md)) so `backend/` can call it without importing its code directly — each lane only needs to agree on that HTTP contract to stay decoupled.
=======
- D5: Formal Education
- D6: Leave Management & Attendance

D1–D4 are preserved in the data structure for future expansion.

## How to run locally

1. Start the backend API from `backend/`.
2. Start the chatbot service from `chatbot/`.
3. Start the frontend app from `frontend/`.
4. Add source documents under `data/` and run ingestion from `chatbot/` whenever the corpus changes.

See the folder-specific README files for exact commands and environment variables.

## Important files

- `backend/src/querio_backend/bridge.py` — FastAPI bridge exposing `POST /chat` and `GET /health`
- `chatbot/src/querio_chatbot/router/router.py` — routing, retrieval, and answer generation flow
- `frontend/src/api/backend.js` — frontend API client for the backend service
- `data/README.md` — document format and domain folder layout
- `Project_Details/03_data_requirements.md` — collection requirements and source metadata guidance
>>>>>>> Stashed changes
