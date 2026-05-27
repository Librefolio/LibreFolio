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
├── lint                           # ruff
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
| After modifying models | `./dev.py db create-clean` |
| After modifying API | `./dev.py api sync` |
| Build frontend | `./dev.py front build` |
| All tests | `./dev.py test all` |
| Gallery screenshots | `./dev.py mkdocs gallery` |
| Check translations | `./dev.py i18n audit` |
| Docker deploy | `./dev.py docker rebuild` |
| Code formatting | `./dev.py format` |
| Linting | `./dev.py lint` |
| User management | `./dev.py user create admin admin@mail.com pass` |

## Ports

| Port | Service |
|------|---------|
| 6040 | Backend production |
| 6041 | Backend test mode |
| 6042 | MkDocs serve |
| 5173 | Frontend dev (Vite HMR) |
