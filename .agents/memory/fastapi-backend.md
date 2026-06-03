---
name: Python FastAPI backend
description: Key lessons from the FastAPI backend build for MindPattern
---

# Python FastAPI Backend

## bcrypt / passlib incompatibility
**Rule:** Use `bcrypt` directly — do NOT use `passlib[bcrypt]`.
**Why:** passlib 1.7.4 tries to access `bcrypt.__about__.__version__` (removed in bcrypt 4.x) and calls `hashpw` with a >72-byte test string to detect a wrap bug, which bcrypt 4.x now rejects with `ValueError`. This breaks any password hashing at startup.
**How to apply:** In `security.py`, import `bcrypt` and call `bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())` / `bcrypt.checkpw(...)` directly.

## create_all schema changes
**Rule:** `Base.metadata.create_all` only creates missing tables; it never alters existing columns.
**Why:** If you deploy with a wrong column type (e.g., Integer instead of Boolean), the column stays wrong even after fixing the model. You must `ALTER TABLE` manually.
**How to apply:** For fresh deploys this is a non-issue. For schema corrections on existing tables, run `ALTER TABLE <table> ALTER COLUMN <col> TYPE <new_type> USING <col>::<new_type>`.

## artifact.toml dev run command
The development `run` field in artifact.toml is a shell string executed from an unknown CWD — always use absolute paths: `cd /home/runner/workspace/artifacts/api-server && uvicorn main:app ...`.
