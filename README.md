# MindPattern

A personal mental health pattern analysis tool. Track your daily mood, sleep, stress, and habits — then surface real behavioral patterns and insights over time.

---

## What it does

- **Daily Check-In** — log mood, stress, sleep hours, energy, exercise, socializing, and workload each day
- **Dashboard** — mood and stress trend charts, sleep-mood scatter, streak counter, and weekly averages
- **Journal** — write free-form entries; AI surfaces recurring emotional themes without diagnosing anything
- **Patterns & Insights** — detects correlations like "your mood drops after less than 6 hours of sleep" with confidence scores and personalized suggestions
- **Settings** — toggle AI analysis and weekly summary features per account

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, wouter, shadcn/ui, Recharts, Framer Motion |
| API | Python 3.11 + FastAPI + uvicorn |
| Database | PostgreSQL + SQLAlchemy (ORM) |
| Auth | JWT (python-jose) + bcrypt |
| AI | Anthropic claude-haiku-4-5 via Replit AI Integrations |
| NLP | Rule-based keyword detection + sentiment scoring |

---

## Running locally

```bash
# API server (port 8080)
cd artifacts/api-server
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Frontend (port 25243)
pnpm --filter @workspace/mindpattern run dev
```

Required environment variables:
- `DATABASE_URL` — PostgreSQL connection string (auto-set on Replit)
- `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` / `AI_INTEGRATIONS_ANTHROPIC_API_KEY` — auto-set via Replit AI Integrations

---

## Project structure

```
artifacts/
  api-server/          # Python FastAPI backend
    main.py            # App entrypoint, CORS, router registration
    app/
      core/            # Config, DB engine, security (JWT + bcrypt)
      models/          # SQLAlchemy models: User, CheckIn, JournalEntry, Insight, SafetyEvent
      schemas/         # Pydantic request/response schemas
      repositories/    # DB query layer, all scoped by user_id
      services/        # NLP, safety detection, dashboard aggregation, pattern insights
      routes/          # FastAPI routers: auth, checkins, journals, dashboard, insights, users
  mindpattern/         # React + Vite frontend
    src/
      pages/           # dashboard, checkin, journal, insights, settings, login, register
      components/      # Layout, ProtectedRoute, RiskNotice, shadcn/ui
      services/        # API service modules (auth, checkins, journals, dashboard, insights)
      store/           # Zustand auth store
      lib/             # Axios client (attaches JWT, handles 401)

lib/
  db/                  # Drizzle ORM schema + migrations (legacy, still used for schema push)
  api-spec/            # OpenAPI spec + Orval codegen config
```

---

## API routes

All routes are under `/api`:

```
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me

POST   /api/checkins
GET    /api/checkins
GET    /api/checkins/{id}

POST   /api/journals
GET    /api/journals
GET    /api/journals/{id}

GET    /api/dashboard/summary
GET    /api/dashboard/mood-trends
GET    /api/dashboard/stress-trends
GET    /api/dashboard/sleep-mood

POST   /api/insights/generate
GET    /api/insights

GET    /api/users/me/settings
PUT    /api/users/me/settings

GET    /api/health
```

---

## Key decisions

- **All queries are scoped by `user_id`** — no cross-user data leakage.
- **bcrypt is used directly** (not via passlib) — passlib 1.7.x is incompatible with bcrypt 4.x.
- **Dates stored as `text`** in ISO `yyyy-MM-dd` format — avoids timezone complications with date-only values.
- **DB tables use `_v2` suffix** (`checkins_v2`, `journal_entries_v2`) — avoids conflict with old Drizzle-era tables.
- **NLP is rule-based** — no LLM call on check-ins; AI is only used for journal analysis.
- **Safety keyword detection** logs a `SafetyEvent` but always saves the journal entry; crisis resources are shown in the UI.
- **Pattern detection** runs on the last 60 check-ins; returns "More Check-Ins Needed" if fewer than 3 exist.
- **`create_all` on startup** — auto-creates missing tables (dev-friendly); schema changes to existing tables require a manual `ALTER TABLE`.

---

## Gotchas

- After editing Python routes, restart the `artifacts/api-server: API Server` workflow — `--reload` handles hot-reload in dev.
- `create_all` only creates missing tables; it does not alter existing columns.
- After any OpenAPI spec change, run `pnpm --filter @workspace/api-spec run codegen` before editing routes or the frontend.
- The Anthropic integration env vars are auto-provisioned — never ask the user for them.
