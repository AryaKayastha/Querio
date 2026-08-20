# Querio

Querio is a conversational AI assistant for student questions across six mentor-approved domains of college life, with answers grounded in real institutional documents.

See [`Project_Details/Querio_Complete_Context.md`](Project_Details/Querio_Complete_Context.md) for the full project context.

## Repository structure

```text
Querio/
├── backend/
│   ├── README.md
│   ├── .env
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

## Current scope

The backend service is currently wired for:

- D5: Formal Education
- D6: Leave Management & Attendance

D1–D4 are preserved in the data structure for future expansion.

## How to run locally

1. Start the backend API from `backend/`.
2. Start the frontend app from `frontend/`.
3. Add source documents under `data/` and run ingestion from `backend/` whenever the corpus changes.

See the folder-specific README files for exact commands and environment variables.

## Important files

- `backend/src/querio_backend/app.py` — FastAPI app exposing `POST /chat` and `GET /health`
- `backend/src/querio_backend/router/router.py` — routing, retrieval, and answer generation flow
- `frontend/src/api/backend.js` — frontend API client for the backend service
- `data/README.md` — document format and domain folder layout
- `Project_Details/03_data_requirements.md` — collection requirements and source metadata guidance
