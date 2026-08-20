# Frontend

Querio's frontend is a Vite + React chat UI that talks to the backend API.

## Folder structure

```text
frontend/
├── README.md
├── .env
├── .env.example
├── index.html
├── package.json
├── vite.config.js
├── public/
└── src/
	├── App.jsx
	├── api/
	│   └── backend.js
	├── assets/
	│   └── icons/
	├── components/
	│   ├── Avatar/
	│   ├── ChatHeader/
	│   ├── ChatInput/
	│   ├── ChatWindow/
	│   ├── ExamplePromptCard/
	│   ├── MessageBubble/
	│   ├── QuickReplyChips/
	│   ├── RecentChatItem/
	│   ├── Sidebar/
	│   ├── StatusPill/
	│   ├── TypingIndicator/
	│   ├── WidgetBubble/
	│   └── WidgetPanel/
	├── data/
	├── pages/
	│   ├── ChatPage/
	│   ├── LandingPage/
	│   └── WidgetDemoPage/
	└── utils/
		├── generateId.js
		└── getBotReply.js
```

## What it does

- Renders the main chat experience
- Sends messages to the backend API
- Displays chat messages, quick replies, and typing indicators
- Provides the widget demo and landing pages

## Setup

```powershell
cd frontend
npm install
copy .env.example .env
```

Edit `frontend/.env` if your backend runs on a different address.

## Run locally

```powershell
npm run dev
```

Open the printed Vite URL in your browser, usually:

```text
http://localhost:5173
```

## Build and preview

```powershell
npm run build
npm run preview
```

## Environment variables

- `VITE_API_BASE_URL` — backend base URL, defaults to `http://localhost:8000`

## Notes

- The chat input is single-line.
- Source chips currently re-submit their label as a new message when clicked.
- The frontend does not sanitize rendered message text again; React escaping is already sufficient.