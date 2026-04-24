---
title: "Single Migration Strategy (001_initial.py)"
category: concept
tags: [backend, db, alembic, migrations, devops]
related_features: [F-064]
---

# Concept: Single Migration Strategy

## Definition
During LibreFolio's development phase, **all database schema changes are made directly in `alembic/versions/001_initial.py`** — the single migration file. No incremental migration files are created. The DB is recreated from scratch after every schema change.

## The rule
```bash
# CORRECT workflow for schema changes:
# 1. Edit backend/alembic/versions/001_initial.py
# 2. Recreate DB
./dev.py db create-clean           # prod DB
./dev.py db create-clean --test    # test DB
```

**Never** run `alembic revision --autogenerate` or create `002_xxx.py`, `003_xxx.py` files.

## Why
- LibreFolio is pre-release, single-machine, no backward compatibility required
- Incremental migrations accumulate complexity and require squashing later
- A single file is easy to audit and understand
- Retroactive edits to schema don't require migration chaining

## Consequences
- **Data loss on every schema change** — acceptable in dev, not acceptable post-release
- This strategy will change at v1.0 (public release) — incremental migrations will be introduced then
- All test data is ephemeral by design

## Source
`LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` — "No migrazioni Alembic incrementali"

## Source files

| Role | Path |
|------|------|
| Single migration file | `backend/alembic/versions/001_initial.py` |
| DB models | `backend/app/db/models.py` |
| CLI db commands | `dev.py` |
| mkdocs | `mkdocs_src/docs/developer/architecture/patterns/alembic.md` |
