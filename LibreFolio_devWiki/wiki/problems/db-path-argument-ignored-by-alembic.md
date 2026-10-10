---
title: "`dev.py db <command> <file>` acted on the configured database, not on the file"
category: problem
status: resolved
date: 2026-10-09
tags: [cli, devpy, database, alembic, migrations, silent-failure, env-vars]
related: [entities/devpy-cli, features/F-063, problems/env-var-injection-point-duplicated, concepts/silent-no-op-option, sources/phase00-fx-dashboard-sync-2026-10]
---

# Problem: the database path given to `dev.py db` never reached Alembic

## Symptom

`./dev.py db current|migrate|upgrade|downgrade` (and `db check`) accept an optional database file (`path`). Named
on the command line, the file was ignored: Alembic ran on the **configured** database. A `db downgrade` aimed at a
scratch copy would roll back the real one; a `db current` on a copy reported the real one's revision — with no
error, so the command looked as if it had done what was asked.

## Root cause

The launcher handed the file to Alembic as the `DATABASE_URL` environment variable. `backend/alembic/env.py` reads
the URL from `get_settings()`, and `get_settings()` (`backend/app/config.py`) **recomputes** `DATABASE_URL` from the
data directory and overwrites whatever the environment said. The variable was set, and never read.

Same family as [[problems/env-var-injection-point-duplicated]]: a value injected at a point the consumer does not
read from is a silent no-op ([[concepts/silent-no-op-option]]).

## Solution (2026-10-09, `964f3427d`)

`_alembic()` in `dev.py` passes the file as an Alembic `-x` argument, `-x sqlalchemy.url=sqlite:///<file>`, which
`env.py` reads before falling back to the settings. The path is resolved to an absolute file (a relative one starts
at the project root, like `--data-dir`); paths containing `%`, `?` or `#` are refused (they break Alembic's config
interpolation or the SQLite URL); a missing file is refused except by `db upgrade`, which creates it.

## Prevention

- To point a tool at a different resource, use the tool's own argument, not an environment variable that a settings
  layer may recompute.
- A test of such an option must check the effect on the *named* target — the configured one would pass too.

## Related residuals

Backlog 38: **N-7** (the `cli_tools` page said the database commands "work with `exec`" — closed 2026-10-09: `db
current`/`db check` work in the container, `db upgrade`/`downgrade` need the server stopped) and **N-8** (a `PORT`
in `.env` reaches the container through `env_file` while the server always listens on 6040 — read in the code, not
proven).

## Impact

A maintenance command could silently act on the configured database (the production one, on a host install) while
the operator believed it was working on a copy; the command even printed "Upgrading database: <path>". The only
clue was Alembic's own line "Using DATABASE_URL from config", easy to miss. Found by analysis — a read-only probe
showed `Settings().DATABASE_URL` honouring the variable and `get_settings().DATABASE_URL` replacing it. The project
already knew the cure: the migration tests had always passed `-x sqlalchemy.url=` for exactly this reason.

## Source files

| Role | Path |
|------|------|
| `_named_db_file`, `_alembic` (`-x sqlalchemy.url`) | `dev.py` |
| Alembic environment, `-x` before settings | `backend/alembic/env.py` |
| `get_settings()` recomputes `DATABASE_URL` | `backend/app/config.py` |
| CLI reference | `mkdocs_src/docs/admin/cli_tools.en.md` |
| Migration tests (always `-x sqlalchemy.url=`) | `backend/test_scripts/test_db/test_post_migration.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00DbPathArgument.prompt.md` |
