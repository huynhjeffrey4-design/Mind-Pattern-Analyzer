---
name: DB table naming
description: Convention for new Python/SQLAlchemy table names alongside old Drizzle tables
---

# DB Table Naming Convention

**Rule:** New Python/SQLAlchemy tables use a `_v2` suffix where they semantically overlap with old Drizzle-era tables.

**Why:** The Postgres database still has old tables from the Express/Drizzle era (`checkins`, `journal_entries`). The new FastAPI models use `checkins_v2` and `journal_entries_v2` to avoid schema conflicts during transition. The `users`, `insights`, and `safety_events` tables are new — no suffix needed.

**How to apply:** If a future migration consolidates tables (dropping _v2 suffix), update the `__tablename__` in the SQLAlchemy models and run a data migration.
