# Querio

Conversational AI agent answering student questions across six mentor-approved domains of college life, with cited answers pulled from real institutional documents. See [`Project_Details/Querio_Complete_Context.md`](Project_Details/Querio_Complete_Context.md) for full project context.

## Repo layout

This is a monorepo split into three independent lanes so the team can build in parallel:

| Folder | Owner | Covers |
|---|---|---|
| [`frontend/`](frontend/) | Jahnavi | Chat UI / web widget |
| [`backend/`](backend/) | Nancy | API bridge, query logging, admin document panel, DB schema |
| [`chatbot/`](chatbot/) | Arya | Domain router, retrieval engine, LLM integration, eval harness |
| [`data/`](data/) | Nancy (gathering), Arya (ingests) | Raw per-domain source documents (D1–D6) |
| [`Project_Details/`](Project_Details/) | — | Planning docs, architecture, scope |

```text
Querio/
├── backend/          # thin FastAPI bridge → chatbot
├── chatbot/          # router, retrieval, ingestion, LLM
├── data/             # D1–D6 source corpora
├── frontend/         # React + Vite chat UI
└── Project_Details/
```

Current target: end-to-end for **D5 (Formal Education)** and **D6 (Leave Management & Attendance)**. D1–D4 follow as their data is collected.

## Integration contract

The `chatbot/` service exposes `POST /chat` (see [`chatbot/README.md`](chatbot/README.md)). The `backend/` bridge forwards frontend requests to that endpoint so each lane stays decoupled.

### Ports (do not swap these)

| Service | Port | Command entrypoint |
|---|---|---|
| Chatbot | **8001** | `uvicorn querio_chatbot.app:app --reload --port 8001` |
| Backend bridge | **8000** | `uvicorn querio_backend.bridge:app --reload --port 8000` |
| Frontend | **5173** | `npm run dev` (Vite default) |

Request flow:

`frontend:5173` → `backend:8000` → `chatbot:8001`

- Frontend `VITE_API_BASE_URL` must point at the **backend** (`http://localhost:8000`), never the chatbot.
- Backend `CHATBOT_API_URL` must point at the **chatbot** (`http://localhost:8001`).

## How to run locally

1. Start the chatbot service from `chatbot/` on port **8001**.
2. Start the backend bridge from `backend/` on port **8000**.
3. Start the frontend from `frontend/` (port **5173**).
4. Add source documents under `data/` and run ingestion from `chatbot/` whenever the corpus changes.

See the folder-specific README files for exact commands and environment variables.

## Important files

- `backend/src/querio_backend/bridge.py` — FastAPI bridge exposing `POST /chat` and `GET /health`
- `chatbot/src/querio_chatbot/app.py` — chatbot FastAPI service
- `chatbot/src/querio_chatbot/router/router.py` — routing, retrieval, and answer generation
- `frontend/src/api/backend.js` — frontend client for the backend bridge
- `data/README.md` — document format and domain folder layout
