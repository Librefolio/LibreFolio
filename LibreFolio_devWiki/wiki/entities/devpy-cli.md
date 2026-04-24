---
title: "dev.py CLI"
category: entity
type: module
tags: [infrastructure, cli, devops, workflow, testing]
related: [entities/api-router]
---

# dev.py CLI

## Role
`dev.py` is the single entry point for all developer operations in LibreFolio. It replaces ad-hoc shell scripts and manual commands with a unified, self-documenting CLI. Every project task — from running tests to translating docs — goes through `./dev.py`.

## Location
`dev.py` (project root, ~1050 lines)

## Key Interfaces

### Command groups
| Group | Sub-module | Key commands |
|-------|------------|-------------|
| `server` | inline | `./dev.py server` (start dev server), `./dev.py server --test` |
| `db` | inline | `./dev.py db create-clean`, `./dev.py db upgrade`, `./dev.py db check` |
| `front` | inline | `./dev.py front build`, `./dev.py front dev` |
| `api` | inline | `./dev.py api sync` (regenerate Zodios TS client from OpenAPI) |
| `test` | `scripts/test_runner.py` | `./dev.py test api all`, `./dev.py test all`, `./dev.py test --coverage api all` |
| `user` | `scripts/user_cli.py` | user CRUD for CLI use |
| `mkdocs` | `mkdocs_src/aphra-pipeline/translate_docs.py` | `./dev.py mkdocs build`, `./dev.py mkdocs gallery`, `./dev.py mkdocs translate` |
| `i18n` | `frontend/scripts/i18n-audit.py` | `./dev.py i18n audit`, `./dev.py i18n add`, `./dev.py i18n remove` |
| `docker` | inline | `./dev.py docker build`, `./dev.py docker up` |
| `cache` | inline | invalidate server-side caches |
| `format` / `lint` | inline | `./dev.py format`, `./dev.py lint` (ruff + black) |
| `shell` | inline | Django-style shell with app context |
| `install` | inline | `./dev.py install` (pip + npm) |
| `info` | inline | environment info |

### Ports
| Port | Use |
|------|-----|
| 8000 | Production API + static |
| 8001 | Test server |
| 8002 | MkDocs dev server |
| 5173 | SvelteKit HMR (dev) |

### Architecture
Sub-commands imported from external modules via `register_subparser()`:
- `scripts/test_runner.py` → `test *`
- `scripts/user_cli.py` → `user *`
- `scripts/coverage_analysis.py` → `test coverage-report`
- `mkdocs_src/aphra-pipeline/translate_docs.py` → `mkdocs translate*`
- `frontend/scripts/i18n-audit.py` → `i18n *`

## Key Workflows

| Trigger | Command |
|---------|---------|
| After DB model change | `./dev.py db create-clean` |
| After API change | `./dev.py api sync` |
| Run all tests | `./dev.py test all` |
| Run with coverage | `./dev.py test --coverage api all` |
| Gallery screenshots | `./dev.py mkdocs gallery` |
| Translate docs | `./dev.py mkdocs translate` |
| Docker build (pre-build first!) | `./dev.py front build && ./dev.py mkdocs build && ./dev.py docker build` |

## Design Notes
- `./dev.py` is the ONLY supported way to run complex operations — never bypass it with manual commands
- All subcommands handle environment setup (data dirs, ports, env vars) consistently
- `--test` flag switches to test DB and test server port throughout

## History
- Introduced in V4 rewrite to replace scattered shell scripts
- Sub-module architecture allows skills and agents to extend it without touching the core

## Source files

| Role | Path |
|------|------|
| Main CLI | `dev.py` |
| Test runner | `scripts/test_runner.py` |
| User CLI | `scripts/user_cli.py` |
| Coverage analysis | `scripts/coverage_analysis.py` |
| i18n audit | `frontend/scripts/i18n-audit.py` |
| devpy reference | `LibreFolio_developer_journal/knowledge_base/04_devpy_reference.md` |
