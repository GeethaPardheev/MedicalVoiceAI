# Voice Agent Frontend

React + Vite dashboard for the LiveKit-powered medical scheduling agent. It issues LiveKit session
tokens, connects to the realtime room, and visualizes transcript, tool timeline, and Supabase
summaries.

## Features

- Session form that requests `/api/session` tokens and connects to LiveKit.
- Live call stage showing room identity plus a one-click disconnect.
- DataChannel bridge that streams transcript lines and tool events from the backend into Zustand.
- Panels for transcripts, tool calls, and latest Supabase summary records.
- Minimal Tailwind-free styling with CSS variables for dark, neon look.

## Getting Started

```bash
cd voice-agent-frontend
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL` to wherever the FastAPI service is reachable (defaults to
`http://localhost:8000`). The dev server proxies requests directly via fetch, so no Vite proxy is
required.

## Building for production

```bash
npm run build
npm run preview
```

Deploy the generated `dist/` folder behind any static host (Netlify, Vercel, S3). Ensure the
backend is reachable over HTTPS and that `BACKEND_CORS_ORIGINS` allows the frontend origin.

## Testing checklist

- `npm run build` succeeds without TypeScript errors.
- Connect flow: fill the session form, click "Connect & Join", confirm status pill switches to
  "Agent is live in the room".
- Speak through a phone bridge (or mock agent) to verify transcript entries stream in.
- Trigger tool calls (book/cancel/modify) and watch the Tool Timeline populate.
- Confirm Supabase `call_summaries` has records and the Latest Summary panel refreshes via the
  button.

## Troubleshooting

- **No audio:** ensure the browser allows autoplay or user gesture precedes connection.
- **Timeline empty:** verify the backend sends DataChannel messages with topics `app.transcript` and
  `app.timeline` as implemented in `agent.py`.
- **Summary missing:** confirm Supabase credentials in the backend `.env` and verify
  `/api/summaries` returns data for the caller phone number.
