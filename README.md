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

Assumes each lane's one-time setup is already done (venvs created, `pip install -e .`, `npm install`, `.env` copied — see each folder's README). Run these in order, each in its own terminal, from the repo root.

**1. Database** (backend/)

```powershell
cd backend
docker compose up -d          # starts local Postgres (Docker Desktop must be running)
alembic upgrade head          # applies the query_log / document schema
cd ..
```

**2. Ingest documents** (chatbot/) — only needed the first time or when the corpus under `data/` changes:

```powershell
cd chatbot
.venv\Scripts\activate
python -m querio_chatbot.ingestion.ingest
cd ..
```

**3. Chatbot service** — port **8001**:

```powershell
cd chatbot
.venv\Scripts\activate
uvicorn querio_chatbot.app:app --reload --port 8001
```

**4. Backend bridge** — port **8000** (new terminal):

```powershell
cd backend
.venv\Scripts\activate
uvicorn querio_backend.bridge:app --reload --port 8000
```

**5. Frontend** — port **5173** (new terminal):

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173** once all three services report healthy (`GET http://localhost:8000/health` should return `{"status":"ok","chatbot":"ok"}`).

To stop: `Ctrl+C` each service, then `docker compose stop` from `backend/` (add `-v` after `down` instead of `stop` only if you want to wipe the local Postgres data).

See the folder-specific README files ([`backend/README.md`](backend/README.md), [`chatbot/README.md`](chatbot/README.md), [`frontend/README.md`](frontend/README.md)) for first-time setup, environment variables, and troubleshooting.

## Important files

- `backend/src/querio_backend/bridge.py` — FastAPI bridge exposing `POST /chat` and `GET /health`
- `chatbot/src/querio_chatbot/app.py` — chatbot FastAPI service
- `chatbot/src/querio_chatbot/router/router.py` — routing, retrieval, and answer generation
- `frontend/src/api/backend.js` — frontend client for the backend bridge
- `data/README.md` — document format and domain folder layout
