---
title: "dev.py CLI"
category: entity
type: module
tags: [infrastructure, cli, devops, workflow, testing]
related: [entities/api-router, entities/test-runner, concepts/runtime-lanes, problems/devpy-unusable-in-docker-image, problems/db-path-argument-ignored-by-alembic]
---

# dev.py CLI

## Role
`dev.py` is the single entry point for all developer operations in LibreFolio. It replaces ad-hoc shell scripts and manual commands with a unified, self-documenting CLI. Every project task — from running tests to translating docs — goes through `./dev.py`.

## Location
`dev.py` (project root, 2 714 lines on 2026-10-09, 3 053 on 2026-11-07)

## Key Interfaces

### Command groups
| Group | Sub-module | Key commands |
|-------|------------|-------------|
| `server` | inline | `./dev.py server` (start dev server), `./dev.py server --test` |
| `db` | inline | `./dev.py db create-clean`, `./dev.py db upgrade`, `./dev.py db check` |
| `front` | inline | `./dev.py front build`, `./dev.py front dev` |
| `api` | inline | `./dev.py api sync` (regenerate Zodios TS client from OpenAPI) |
| `test` | `scripts/test_runner/` | `./dev.py test api all`, `./dev.py test all`, `./dev.py test --coverage api all` |
| `user` | `scripts/user_cli.py` | user CRUD for CLI use |
| `mkdocs` | `mkdocs_src/aphra-pipeline/translate_docs.py` | `./dev.py mkdocs build`, `./dev.py mkdocs gallery`, `./dev.py mkdocs translate` |
| `i18n` | `frontend/scripts/i18n-audit.py` | `./dev.py i18n audit`, `./dev.py i18n add`, `./dev.py i18n remove` |
| `docker` | inline | `./dev.py docker build`, `./dev.py docker up` |
| `cache` | `scripts/update_js_cache.py` | `./dev.py cache js` — the static resource cache (JS libraries, fonts) kept locally for offline use |
| `format` / `lint` | inline | `./dev.py format`, `./dev.py lint` (ruff + black) |
| `shell` | inline | opens the pipenv shell |
| `install` | inline | `./dev.py install` (pip + npm) |
| `info` | inline | environment info |
| `backup` | `scripts/backup_cli.py` | instance backup: create, inspect, restore, decrypt, pending |
| `graph` | inline | devWiki knowledge graph: `build`, `update`, `query`, `viz`, … |

### Ports
| Port | Use |
|------|-----|
| 6040 | Production API + static |
| 6041 | Test server |
| 6042 | MkDocs dev server |
| 5173 | SvelteKit HMR (dev) |

### Architecture
Sub-commands imported from external modules via `register_subparser()`:
- `scripts/test_runner/` (31 modules on 2026-11-07, see [[entities/test-runner]]) → `test *`
- `scripts/user_cli.py` → `user *`
- `scripts/backup_cli.py` → `backup *`
- `scripts/update_js_cache.py` → `cache *`
- `scripts/coverage_analysis.py` → `test coverage-report`
- `mkdocs_src/aphra-pipeline/translate_docs.py`, `validate_translations.py` → `mkdocs translate*`
- `frontend/scripts/i18n-audit.py` → `i18n *`

## Key Workflows

| Trigger | Command |
|---------|---------|
| After DB model change | edit the release's migration file and test the upgrade; `./dev.py db create-clean` only for fresh/test DBs ([[concepts/single-migration-strategy]]; 2026-11-07 lint: was `db create-clean` alone) |
| After API change | `./dev.py api sync` |
| Run all tests | `./dev.py test all` |
| Run with coverage | `./dev.py test --coverage api all` |
| Gallery screenshots | `./dev.py mkdocs gallery` |
| Translate docs | `./dev.py mkdocs translate` |
| Docker build | `./dev.py docker build` (rebuilds a missing or stale frontend and docs itself) |

## Design Notes
- `./dev.py` is the ONLY supported way to run complex operations — never bypass it with manual commands
- All subcommands handle environment setup (data dirs, ports, env vars) consistently
- `--test` flag switches to the test DB and the test server port throughout; the port and the data directory are overridable per run — a **runtime lane** (`server --port --data-dir`, `test --test-port --data-dir`; the gallery takes `--test-port` only): [[concepts/runtime-lanes]]
- **Two installation shapes**: in the Docker image the development tree is absent, so `test`, `i18n` and `mkdocs translate*` are registered as "not available in this installation" stubs that exit 2, decided by `_has(paths)` before importing — never by catching `ImportError`. `user *`, `info`, `db current|check` work through `docker compose exec`; `db upgrade` wants the server stopped: [[problems/devpy-unusable-in-docker-image]]
- `db … [path]` passes the file to Alembic as `-x sqlalchemy.url` ([[problems/db-path-argument-ignored-by-alembic]]); a blank `JWT_SECRET` counts as absent ([[features/F-065]])
- Worktrees: each worktree path gets a new empty pipenv venv unless `PIPENV_CUSTOM_VENV_NAME` points at the main one

## History
- Introduced in V4 rewrite to replace scattered shell scripts
- Sub-module architecture allows skills and agents to extend it without touching the core
- 2026-05-26: `scripts/test_runner/` (4841-line monolith) refactored into 18-module package at `scripts/test_runner/`. See [[decisions/test-runner-package-split]].
- 2026-09-10: runtime lanes (`4588506b9`) — [[sources/phase00-parallel-runtime-isolation-2026-09]].
- 2026-10-08/09: image-aware command groups (train 19), `db <path>` honoured, `user` exit status, shared JWT secret — [[sources/phase00-dev-cli-image-2026-10]].
- 2026-11-07 lint: command table completed with the `backup`, `graph` and `cache` groups as registered in `dev.py`.

## Source files

| Role | Path |
|------|------|
| Main CLI | `dev.py` |
| Shared CLI helpers (lanes, readiness) | `scripts/cli_base.py` |
| Test runner (package) | `scripts/test_runner/` |
| User CLI | `scripts/user_cli.py` |
| Coverage analysis | `scripts/coverage_analysis.py` |
| i18n audit | `frontend/scripts/i18n-audit.py` |
| devpy reference | `LibreFolio_developer_journal/knowledge_base/04_devpy_reference.md` |
