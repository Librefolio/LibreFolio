---
title: "Runtime lanes: one port and one data directory per parallel server or test run"
category: concept
tags: [cli, devpy, testing, parallelism, isolation, worktrees, data-dir, ports, agents]
related: [entities/devpy-cli, features/F-063, features/F-064, decisions/port-6040-scheme, decisions/prod-test-data-separation, concepts/test-isolation-classes, concepts/silent-no-op-option, sources/phase00-parallel-runtime-isolation-2026-09]
---

# Concept: runtime lanes

## Definition

Since 2026-09-10 (`916f12bdd`) several LibreFolio servers and test runs can work side by side — one per worktree,
per agent or per test campaign — each in its own **lane**: a unique **port** and a unique **data directory**. The data
directory holds everything a run writes: the SQLite database, uploads, broker reports, logs. A lane is valid only if
**both** are unique (the default ports follow [[decisions/port-6040-scheme]]); a shared port collides at bind time, a shared data directory corrupts silently.

## The switches

| Command | Lane options |
|---|---|
| `./dev.py server` | `--port N` (default `PORT` or 6040), `--data-dir PATH`; with `--test` the data directory goes through `LIBREFOLIO_TEST_DATA_DIR` |
| `./dev.py test …` | `--test-port N` (alias `--port`), `--data-dir PATH` — exported to the runner, pytest, the shared backend, Playwright and every child process |
| `./dev.py mkdocs gallery` | `--test-port` only — **no `--data-dir`**: it always repopulates the configured test directory (`db populate --force --clean`); a known limit, accepted on 2026-09-22 |

## The guards

- `configure_test_runtime()` (`scripts/cli_base.py`) validates and exports one lane's port and data directory and
  refuses a test port equal to the production port.
- `validate_test_data_dir()` (`backend/app/config.py`) refuses the production data directory, including relative-path
  and symlink aliases, and a directory carrying the persistent production marker.
- **Readiness carries an identity**: the runner accepts a server only if its HTTP answer carries the lane's nonce, so a
  `200` from a server of another lane on a reused port is not mistaken for its own.
- `--force` kills only listeners the runner owns; database paths are resolved when used, not frozen at import.
- Fixed on the way: `pipenv run` reloaded `.env` over the parent's overrides — the lane was set and then silently lost
  (the family of [[concepts/silent-no-op-option]]).

## Gotcha: one virtualenv per worktree path

Pipenv keys its virtualenv on the project path, so each new worktree gets a new, empty venv. Point every worktree at
the locked main venv with `PIPENV_CUSTOM_VENV_NAME` (documented in the `devpy` and `testing-frontend` skills).

## Where it applies

Every parallel workstream of Release 2 ran in its own lane (e.g. "lane 6156/6166, `--data-dir /tmp/librefolio-r2-l`"
in the plans' headers). Isolation *between tests of one run* is a different layer: [[concepts/test-isolation-classes]].

## Source files

| Role | Path |
|------|------|
| `server --port --data-dir`; gallery `--test-port` | `dev.py` |
| `configure_test_runtime`, readiness identity | `scripts/cli_base.py` |
| `test --test-port --data-dir` | `scripts/test_runner/_cli.py` |
| `validate_test_data_dir` | `backend/app/config.py` |
| Tests (propagation, guards, readiness, ownership) | `backend/test_scripts/test_utilities/test_runtime_isolation.py` |
| Skill note on `PIPENV_CUSTOM_VENV_NAME` | `.github/skills/devpy-tools/devpy/SKILL.md` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/15_parallelRuntimeIsolation/plan-phase00ParallelRuntimeIsolation.prompt.md` |
