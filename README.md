# Querio

Conversational AI agent answering student questions across six mentor-approved domains of college life, with cited answers pulled from real institutional documents. See [`Project_Details/Querio_Complete_Context.md`](Project_Details/Querio_Complete_Context.md) for full project context.

## Repo layout

This is a monorepo split into three independent lanes so the team can build in parallel:

| Folder | Owner | Covers |
|---|---|---|
| [`frontend/`](frontend/) | Jahnavi | Chat UI / web widget |
| [`backend/`](backend/) | Nancy | API, query logging, admin document panel, DB schema |
| [`chatbot/`](chatbot/) | Arya | Domain router, retrieval engine, LLM integration, eval harness |
| [`data/`](data/) | Nancy (gathering), Arya (ingests) | Raw per-domain source documents (D1–D6) |
| [`Project_Details/`](Project_Details/) | — | Planning docs, architecture, scope |

Current target: get the chatbot working end-to-end for **D5 (Formal Education)** and **D6 (Leave Management & Attendance)**, since those two domains already have usable source data. D1–D4 will follow as their data is collected.

## Integration contract

The `chatbot/` service exposes a `POST /chat` HTTP endpoint (see [`chatbot/README.md`](chatbot/README.md)) so `backend/` can call it without importing its code directly — each lane only needs to agree on that HTTP contract to stay decoupled.
