# Frontend (Jahnavi)

Chat UI / web widget for Querio. Talks only to the **backend bridge** — never call the chatbot service directly from the browser.

## Ports

| Service | Port |
|---|---|
| Frontend (this app) | **5173** |
| Backend bridge | **8000** ← `VITE_API_BASE_URL` |
| Chatbot | **8001** (backend-only; not used by the UI) |

Flow: `frontend:5173` → `backend:8000` → `chatbot:8001`

## Routes

| Path | Page |
|---|---|
| `/` | Landing |
| `/chat` | Full chat experience |
| `/widget` | Embeddable widget demo |

## Layout

```text
frontend/src/
├── api/backend.js          # POST /chat + GET /health against backend:8000
├── components/             # Chat UI building blocks (header, sidebar, bubbles, widget)
├── pages/
│   ├── LandingPage/
│   ├── ChatPage/
│   └── WidgetDemoPage/
├── utils/getBotReply.js    # Normalizes answers, sources, and chips
├── App.jsx                 # React Router routes
└── main.jsx
```

## Setup

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000`.

## Local stack order

1. Start `chatbot` on **8001**
2. Start `backend` bridge on **8000**
3. Start this app on **5173** (`npm run dev`)

The chat header status pill polls `GET /health` on the backend and shows online/offline accordingly.
