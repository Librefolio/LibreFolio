---
name: devpy-cli
description: "Use this skill when the user needs to run dev.py commands, start the server, manage the database, build the frontend, generate gallery screenshots, manage i18n translations, or any CLI operation. This skill contains the complete command tree and common scenarios."
---

# `dev.py` CLI Reference

> **Fundamental rule**: ALWAYS use `./dev.py` for complex operations. Never manual commands.

## Complete Command Tree

```text
dev.py [-h]
├─── server                        → see skill: devpy-server
├─┬─ db                            → see skill: devpy-server
├─┬─ front                         → see skill: devpy-server
├─┬─ api                           → see skill: devpy-server
├─┬─ test                          → see skills: testing-backend, testing-frontend
├─┬─ user [--test-db]
│ ├── create USERNAME EMAIL PASSWORD
│ ├── list
│ ├── reset USERNAME NEW_PASSWORD
│ ├── activate / deactivate USERNAME
│ ├── promote / demote USERNAME
│ └── init-settings
├─┬─ mkdocs                        → see skill: devpy-mkdocs
├─┬─ i18n                          → see skill: devpy-i18n
├─┬─ docker                        → see skill: devpy-docker
├─┬─ cache
│ └── js [--force]
├─┬─ info
│ ├── api                          # List all API endpoints
│ └── version                      # Show git-based version
├── format                         # black
├── lint                           # ruff (--dead-code → vulture + knip)
├── shell                          # pipenv shell
└── install                        # pip + npm
```

## Common Scenarios

| Scenario | Command |
|----------|---------|
| Start for development | `./dev.py server` |
| Test mode | `./dev.py server --test` |
| Kill zombie + start | `./dev.py server --force` |
| Frontend with HMR | T1: `./dev.py server` — T2: `./dev.py front dev` |
| After modifying models | `./dev.py db migrate "…"` (incremental migration; `db create-clean` only for fresh/test DBs) |
| After modifying API | `./dev.py api sync` |
| Build frontend | `./dev.py front build` |
| All tests | `./dev.py test all` |
| Gallery screenshots | `./dev.py mkdocs gallery` |
| Check translations | `./dev.py i18n audit` |
| Docker deploy | `./dev.py docker rebuild` |
| Code formatting | `./dev.py format` |
| Linting | `./dev.py lint` |
| Dead code | `./dev.py lint --dead-code` |
| User management | `./dev.py user create admin admin@mail.com pass` |

## Dependency Management (pipenv)

⚠️ **NEVER run `pipenv update <pkg>` on a VCS (git) dependency** — pipenv 2026.x rewrites
the Pipfile during `update` and **drops the `git`/`ref` fields** (the entry becomes a plain
`"*"` PyPI requirement). The next lock then fails with `No matching distribution found`
(our git deps, e.g. `borsa-italiana-scraping`, are not on PyPI). Lost hours on 2026-09-04/05
chasing a "mysterious Pipfile edit" that was `pipenv update` itself.

Correct flow to bump a git dependency (e.g. after pushing a new commit on the lib's main):

```bash
pipenv lock --clear        # re-resolves ref = "main" to the latest commit; does NOT rewrite the Pipfile
pipenv install             # sync the venv from the updated lock
```

`requirements.txt` is gitignored — the release pipeline regenerates it (`pipenv requirements`);
never commit or hand-edit it.

Related incident notes (2026-09-05): the Borsa Italiana site-search may return HTTP 200 with
ALL sections empty — a silent WAF soft-block per IP after heavy scraping. `cerca()` (library
≥ 0.3.1) detects it via a control-query probe and raises `RicercaNonDisponibile` instead of
returning "no results". If searches suddenly return empty for everything: wait a few hours or
change IP before suspecting the code.

## Ports

| Port | Service |
|------|---------|
| 6040 | Backend production |
| 6041 | Backend test mode |
| 6042 | MkDocs serve |
| 5173 | Frontend dev (Vite HMR) |
