# MindPattern

A personal mental health pattern analysis tool that helps users track moods, habits, sleep, stress, and journal entries — then surfaces behavioral patterns and insights over time.

## Run & Operate

- `cd artifacts/api-server && uvicorn main:app --host 0.0.0.0 --port 8080 --reload` — run the FastAPI server (dev)
- `pnpm --filter @workspace/mindpattern run dev` — run the frontend (port 25243)
- `pnpm run typecheck` — full typecheck across all packages
- Required env: `DATABASE_URL` — Postgres connection string
- Required env: `SECRET_KEY` — JWT signing key (optional; has a dev default)

## Stack

- Frontend: React + Vite, wouter routing, shadcn/ui, Recharts, Framer Motion
- API: Python 3.11, FastAPI, uvicorn
- DB: PostgreSQL + SQLAlchemy (ORM), tables auto-created on startup
- Auth: JWT (python-jose) + bcrypt for passwords
- NLP: Rule-based keyword detection + sentiment scoring (no LLM)
- Python deps: fastapi, uvicorn[standard], sqlalchemy, psycopg2-binary, python-jose[cryptography], bcrypt, pydantic-settings, email-validator

## Where things live

- `artifacts/api-server/main.py` — FastAPI app entrypoint + CORS + router registration
- `artifacts/api-server/app/core/` — config, database engine, security (JWT + bcrypt)
- `artifacts/api-server/app/models/` — SQLAlchemy models (User, CheckIn, JournalEntry, Insight, SafetyEvent)
- `artifacts/api-server/app/schemas/` — Pydantic request/response schemas
- `artifacts/api-server/app/repositories/` — DB query layer (scoped by user_id)
- `artifacts/api-server/app/services/` — NLP, safety detection, dashboard, pattern insights
- `artifacts/api-server/app/routes/` — FastAPI routers (auth, checkins, journals, dashboard, insights, users)
- `artifacts/mindpattern/src/` — React frontend (currently wired to old Express API; will be rebuilt)

## API Routes

All routes live under `/api`:
- `GET /api/health` — health check
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `POST /api/checkins`, `GET /api/checkins`, `GET /api/checkins/{id}`
- `POST /api/journals`, `GET /api/journals`, `GET /api/journals/{id}`
- `GET /api/dashboard/summary`, `/mood-trends`, `/stress-trends`, `/sleep-mood`
- `POST /api/insights/generate`, `GET /api/insights`
- `GET /api/users/me/settings`, `PUT /api/users/me/settings`

## Architecture decisions

- All queries are scoped by `user_id` — no cross-user data leakage.
- SQLAlchemy `create_all` on startup auto-creates tables (dev-friendly, no migration needed for fresh DB).
- Passwords hashed with bcrypt directly (not via passlib — passlib 1.7.x is incompatible with bcrypt 4.x).
- Dates stored as `text` (ISO `yyyy-MM-dd`) in Postgres to avoid timezone complications.
- Pattern detection uses correlation math on last 60 check-ins; returns "More Check-Ins Needed" if <3.
- Journal NLP uses rule-based keyword detection + pos/neg word lists — no LLM needed per MVP plan.
- Safety keyword detection logs a `SafetyEvent` but always saves the journal entry.
- Score ranges: mood/stress/workload/energy 1–5, sleep 0–24.
- DB tables use `_v2` suffix for check-ins and journals to avoid conflicts with old Express-era tables.

## Product

- **Auth**: Register, login, JWT-protected routes
- **Daily Check-In**: Log mood (1–5), stress (1–5), sleep hours, energy, exercise, socializing, workload, notes
- **Dashboard**: Mood/stress trend charts, sleep-mood scatter, summary stats with streak
- **Journal**: Write entries; NLP auto-detects keywords and sentiment; crisis terms trigger a SafetyEvent
- **Patterns/Insights**: sleep→mood, exercise→mood, workload→stress, recurring journal keywords
- **User Settings**: Toggle ai_analysis_enabled, weekly_summary_enabled

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- After editing Python routes, uvicorn `--reload` hot-reloads automatically in dev.
- `create_all` only creates missing tables — schema changes to existing tables require manual `ALTER TABLE`.
- bcrypt is used directly (not via passlib) to avoid passlib/bcrypt 4.x incompatibility.
- Anthropic env vars are no longer needed for the MVP backend (NLP is rule-based).
- Use `psql $DATABASE_URL` to inspect or alter tables in dev.
