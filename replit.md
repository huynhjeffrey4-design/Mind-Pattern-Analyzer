# MindPattern

A personal mental health pattern analysis tool that helps users track moods, habits, sleep, stress, and journal entries — then surfaces behavioral patterns and insights over time.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 8080)
- `pnpm --filter @workspace/mindpattern run dev` — run the frontend (port 25243)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string
- Required env: `AI_INTEGRATIONS_ANTHROPIC_BASE_URL`, `AI_INTEGRATIONS_ANTHROPIC_API_KEY` — auto-provisioned via Replit AI Integrations

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Frontend: React + Vite, wouter routing, shadcn/ui, Recharts, Framer Motion
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- AI: Anthropic claude-haiku-4-5 via Replit AI Integrations (journal analysis)
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `lib/api-spec/openapi.yaml` — API contract (source of truth)
- `lib/db/src/schema/checkins.ts` — daily check-in Drizzle table
- `lib/db/src/schema/journal.ts` — journal entries Drizzle table
- `artifacts/api-server/src/routes/checkins.ts` — CRUD for check-ins
- `artifacts/api-server/src/routes/journal.ts` — CRUD for journal + AI analysis endpoint
- `artifacts/api-server/src/routes/insights.ts` — dashboard, mood trend, patterns, weekly summary
- `artifacts/mindpattern/src/` — React frontend

## Architecture decisions

- Pattern detection runs server-side on each request from the last 60 check-ins — no caching needed at this scale, but can be cached later if data grows.
- Journal AI analysis uses claude-haiku-4-5 for speed; it returns themes + summary but explicitly never diagnoses conditions.
- Crisis signal detection is a keyword match in the server route; the AI response separately includes a safe resource message.
- Dates are stored as `text` (ISO format `yyyy-MM-dd`) in Postgres to avoid timezone complications with date-only values.
- The Zod `format: date` fields from OpenAPI get coerced to Date objects — routes normalize back to strings before DB insert.

## Product

- **Daily Check-In**: Log mood (1–10), stress (1–10), sleep hours, exercise, socializing, workload, and free-form notes
- **Dashboard**: Mood/stress trend chart, weekly summary, current streak, detected patterns preview
- **Journal**: Write entries with optional AI analysis that surfaces recurring themes (without diagnosing)
- **Patterns**: Detected behavioral correlations (sleep→mood, exercise→mood, social→mood, etc.) with confidence scores and personalized suggestions
- **Check-In History**: Full timeline of all check-ins

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- After editing routes, restart the `artifacts/api-server: API Server` workflow for changes to take effect.
- After any OpenAPI spec change, run codegen before editing routes or frontend.
- The `date` column in `checkins` is `text` — always insert as `yyyy-MM-dd` string, not a Date object.
- The Anthropic integration env vars are auto-set — never ask the user for them.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
