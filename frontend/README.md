# Frontend (Jahnavi)

Chat UI / web widget for Querio. Talks to the **backend bridge** at `http://localhost:8000` (not the chatbot service directly).

## Routes

| Path | Page |
|---|---|
| `/` | Landing |
| `/chat` | Full chat experience |
| `/widget` | Embeddable widget demo |

## Setup

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000`.

## Local stack

1. `chatbot` on **8001**
2. `backend` bridge on **8000**
3. `frontend` on **5173**
