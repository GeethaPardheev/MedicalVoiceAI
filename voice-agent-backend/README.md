# Voice Agent Backend

Python 3.11 backend for the Aida medical scheduling agent. It bundles two entry points:

- `agent.py`: LiveKit AgentServer worker that joins rooms, runs the realtime agent, and logs conversations.
- `api.py`: FastAPI surface for issuing LiveKit tokens, exposing availability data, and surfacing summaries to the web client.

## Features

- LiveKit Agents orchestration with Deepgram STT, OpenAI GPT-4o LLM, and Cartesia voices.
- Tool layer backed by Supabase/PostgREST for user records and appointment management.
- Automatic call transcription + tool timeline broadcast via LiveKit DataChannel.
- Post-call summarization with GPT-4o and Supabase persistence (transcript, timeline, cost usage, action items).
- FastAPI service for session tokens, slot previews, health, summaries, and appointment lookups.
- Dockerfile for reproducible builds.

## Environment Variables

Copy `.env.example` to `.env` and populate the following:

| Variable | Description |
| --- | --- |
| `LIVEKIT_URL` | `wss://` endpoint for your LiveKit deployment. |
| `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | Worker credentials with room join + publish permissions. |
| `LIVEKIT_TOKEN_TTL` | Seconds each user token remains valid (default `3600`). |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Used by the summarizer + fallback completion. |
| `LLM_FALLBACK` | `anthropic` or other fallback label. |
| `ANTHROPIC_API_KEY` | Required if `LLM_FALLBACK=anthropic`. |
| `DEEPGRAM_API_KEY`, `DEEPGRAM_STT_MODEL` | Realtime speech-to-text provider + model slug. |
| `CARTESIA_API_KEY`, `CARTESIA_TTS_MODEL`, `CARTESIA_VOICE_ID` | Cartesia speech synthesis settings. |
| `LIVEKIT_LLM_MODEL` | Model slug used by the realtime agent (e.g. `openai/gpt-4o-mini`). |
| `SUPABASE_URL`, `SUPABASE_KEY` | PostgREST base + service role key. |
| `DEFAULT_TIMEZONE` | Olson TZ identifier for slot generation. |
| `BACKEND_CORS_ORIGINS` | Comma-delimited allowed origins for the API (use `*` for dev). |
| `LOG_LEVEL` | Optional Python logging level. |

See `.env.example` for all placeholders.

## Supabase schema

Expected tables (all `jsonb` columns can be empty objects):

```sql
create table public.users (
  phone text primary key,
  name text,
  preferences jsonb default '{}'::jsonb
);

create table public.appointments (
  id uuid primary key default gen_random_uuid(),
  user_phone text references public.users(phone),
  start_time timestamptz not null,
  end_time timestamptz not null,
  status text default 'booked',
  meta jsonb default '{}'::jsonb
);

create table public.call_summaries (
  id uuid primary key default gen_random_uuid(),
  user_phone text references public.users(phone),
  summary_text text,
  preferences jsonb,
  appointments_in_call jsonb,
  cost_breakdown jsonb,
  timeline jsonb,
  transcript jsonb,
  created_at timestamptz default now()
);
```

Grant PostgREST access to these tables and ensure the service role key is used by the backend.

## Running locally

```bash
cd voice-agent-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run realtime worker (connects to LiveKit)
python agent.py dev

# run REST API for the web client
uvicorn api:app --reload --port 8000
```

### Docker

```bash
# build
docker build -t voice-agent-backend .

# run worker mode
docker run --env-file .env --network host voice-agent-backend python agent.py start
```

### Testing checklist

- `python agent.py console` for local audio loopback sanity.
- `pytest` (not included) or `python -m compileall .` for syntax validation.
- `uvicorn api:app --port 8000` and hit `/api/health`.
- Make a POST to `/api/session` to confirm token issuance.
- Dry-run tools with `python -m tools.book_appointment` style scripts if needed.

## Deployment Notes

- Worker (`agent.py start`) and API (`uvicorn api:app`) can run in separate containers; share the same `.env`.
- Scale horizontally by running multiple workers—LiveKit Agents will fan out jobs.
- Expose `/api/*` over HTTPS; lock down `LIVEKIT_API_KEY/SECRET` to server-side only.
- Configure Supabase row-level policies if exposing read endpoints publicly.

## Troubleshooting

- Verify LiveKit credentials via `python agent.py console` to ensure the worker can attach to rooms.
- Ensure Supabase REST endpoint is reachable from the container (check `/api/health`).
- For tool debugging, tail logs at `INFO` to see dispatch arguments/results; adjust via `LOG_LEVEL`.
- If summaries fail, confirm `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are set and not rate-limited.
