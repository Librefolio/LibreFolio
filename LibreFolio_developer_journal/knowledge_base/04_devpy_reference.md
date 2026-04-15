# LibreFolio — `dev.py` Command Reference

> **Regola fondamentale**: usare SEMPRE `./dev.py` per operazioni complesse. Non comandi manuali.

## Command Tree Completo

```text
dev.py [-h]
├─── server [--test] [--rebuild] [--debug] [--force] [--workers N] [--coverage]
├─┬─ db
│ ├── check [PATH]
│ ├── current [PATH]
│ ├── migrate MESSAGE [PATH]
│ ├── upgrade [PATH]
│ ├── downgrade [PATH]
│ └── create-clean [--test]
├─┬─ front
│ ├── dev                          # HMR :5173
│ ├── build [--debug]
│ ├── check                        # svelte-check
│ └── preview
├─┬─ test [--coverage] [--cov-clean-backend] [--cov-clean-frontend] [-v]
│ ├── external ACTION
│ ├── db ACTION                    # include "populate"
│ ├── services ACTION
│ ├── utils ACTION
│ ├── schemas ACTION
│ ├── api ACTION
│ ├── e2e ACTION
│ ├── front-utility ACTION         # auth, settings, files, select, image-crop
│ ├── front-user ACTION            # brokers, multi-user, sharing
│ ├── front-fx ACTION              # unit + E2E fx tests
│ ├── front-asset ACTION           # list, detail, modal, data-editor
│ ├── all
│ ├── all-backend                  # all backend categories (external → e2e)
│ ├── all-frontend                 # all frontend categories (front-*)
│ ├── coverage-report [--priority] [--json] [--summary]  # Analisi funzioni scoperte
│ └─┬─ coverage                    # Gestione report coverage
│   ├── show [backend|frontend|combined]
│   └── combine
├─┬─ user [--test-db]
│ ├── create USERNAME EMAIL PASSWORD
│ ├── list
│ ├── reset USERNAME NEW_PASSWORD
│ ├── activate / deactivate USERNAME
│ ├── promote / demote USERNAME
│ └── init-settings
├─┬─ mkdocs
│ ├── build                        # + check admonition pre-build
│ ├── serve                        # porta 8002
│ ├── clean
│ ├── deploy                       # GitHub Pages
│ ├── gallery [-l] [-f TEXT] [--desktop-only] [--mobile-only] [--no-populate] [-w N]
│ ├── translate [--file GLOB] [--lang LANGS] [--dry-run] [--force]
│ ├── translate-check              # verifica setup Aphra
│ ├── translate-validate [--lang LANG] [--file FILE] [-v]
│ ├── translate-diff [--lang LANG] [-v]
│ └── translate-inspect [--file FILE]
├─┬─ api
│ ├── schema                       # Export OpenAPI
│ ├── client                       # Genera TypeScript client
│ └── sync                         # schema + client
├─┬─ i18n
│ ├── audit [--format xlsx|md|both] [--duplicates]
│ ├── add KEY --en --it --fr --es
│ ├── remove KEY [-f]
│ ├── update KEY [--en] [--it] [--fr] [--es]
│ ├── search QUERY [-k] [-v] [-l LANG]
│ └── tree [PREFIX] [--counts] [-d]
├─┬─ cache
│ └── js [--force]
├─┬─ info
│ ├── api                          # Lista endpoint
│ └── version
├── format                         # black
├── lint                           # ruff
├── shell                          # pipenv shell
└── install                        # pip + npm
```

---

## Scenari Comuni

| Scenario | Comando |
|----------|---------|
| Avviare per sviluppo | `./dev.py server` |
| Test mode | `./dev.py server --test` |
| Test mode con coverage | `./dev.py server --test --coverage` |
| Frontend con HMR | T1: `./dev.py server` — T2: `./dev.py front dev` |
| Tutti i test | `./dev.py test all` |
| Solo test frontend | `./dev.py test front-fx all` |
| Popola DB mock | `./dev.py test db populate --force` |
| Gallery screenshot | `./dev.py mkdocs gallery` |
| Dopo modifica modelli | `./dev.py db create-clean` |
| Dopo modifica API | `./dev.py api sync` |
| Verificare traduzioni frontend | `./dev.py i18n audit` |
| Aggiungere traduzione | `./dev.py i18n add "key" --en "..." --it "..." --fr "..." --es "..."` |
| Cercare traduzioni | `./dev.py i18n search "query"` |
| Cercare solo chiavi | `./dev.py i18n search "common" --keys` |
| Albero chiavi i18n | `./dev.py i18n tree` |
| Build docs | `./dev.py mkdocs build` |
| Tradurre docs | `./dev.py mkdocs translate` |
| Validare traduzioni docs | `./dev.py mkdocs translate-validate` |
| Build produzione | `./dev.py front build && ./dev.py server` |
| Nuovo utente | `./dev.py user create admin admin@mail.com pass` |
| Lista endpoint API | `./dev.py info api` |
| Coverage backend con test | `./dev.py test --coverage api all` |
| Coverage frontend E2E | `./dev.py test --coverage front-fx all` |
| Report coverage backend | `./dev.py test coverage show backend` |
| Report coverage frontend | `./dev.py test coverage show frontend` |
| Report coverage combinato | `./dev.py test coverage show combined` |
| Analisi funzioni scoperte | `./dev.py test coverage-report --priority high` |

---

## Architettura di dev.py

`dev.py` (~1050 righe) è organizzato in:

1. **Import e setup** — `PROJECT_ROOT`, `scripts/cli_base.py` utilities
2. **Funzioni comando** — `cmd_server()`, `cmd_db_*()`, `cmd_fe_*()`, etc.
3. **Helper** — `auto_build_frontend()`, `auto_build_mkdocs()`, `copy_docs_assets()`
4. **Main parser** — `TreeParser` (da `scripts/cli_tree_parser.py`) con `add_subparsers`

I sotto-comandi complessi sono **importati** da moduli esterni via `register_subparser()`:

| Modulo | Path | Comandi registrati |
|--------|------|--------------------|
| `test_runner` | `scripts/test_runner.py` | `test *` |
| `coverage_analysis` | `scripts/coverage_analysis.py` | `test coverage-report` |
| `user_cli` | `scripts/user_cli.py` | `user *` |
| `translate_docs` | `mkdocs_src/aphra-pipeline/translate_docs.py` | `mkdocs translate*` |
| `validate_translations` | `mkdocs_src/aphra-pipeline/validate_translations.py` | `mkdocs translate-validate` |
| `i18n-audit` | `frontend/scripts/i18n-audit.py` | `i18n *` |
| `update_js_cache` | `scripts/update_js_cache.py` | `cache js` |

---

## Porte

| Porta | Servizio |
|-------|----------|
| 8000 | Backend produzione |
| 8001 | Backend test mode |
| 8002 | MkDocs serve |
| 5173 | Frontend dev (Vite HMR) |

