# LibreFolio - Project Welcome Prompt

## 🎯 Obiettivo del Progetto

LibreFolio è un'alternativa self-hosted e open-source ad altri software di analisi finanziaria come Ghostfolio, pensata per:

- **Privacy**: I tuoi dati finanziari restano sul tuo server
- **Flessibilità**: Supporto per asset tradizionali, crypto, prestiti P2P, scheduled-yield
- **Controllo**: Import da qualsiasi broker tramite plugin estensibili
- **Multi-utenza**: Più utenti con preferenze personalizzate

**Repository**: https://github.com/Alfystar/LibreFolio

## 🏗️ Architettura del Progetto

```
LibreFolio/
├── backend/                    # Python FastAPI
│   ├── app/
│   │   ├── api/v1/            # REST API endpoints
│   │   ├── db/models.py       # SQLModel ORM models
│   │   ├── schemas/           # Pydantic schemas (validazione I/O)
│   │   ├── services/          # Business logic
│   │   │   ├── asset_source_providers/   # yfinance, JustETF, etc.
│   │   │   ├── fx_providers/             # ECB, FED, BOE, SNB
│   │   │   └── brim_providers/           # Import broker reports
│   │   └── utils/             # Utilities condivise
│   ├── alembic/               # Migrazioni database
│   ├── test_scripts/          # Test suite completa
│   └── data/                  # Dati runtime (separati prod/test)
│       ├── prod/              # Dati produzione
│       │   ├── sqlite/app.db
│       │   ├── broker_reports/{uploaded,parsed,failed}/
│       │   ├── custom-uploads/
│       │   └── logs/
│       └── test/              # Dati test (isolati)
│           └── (stessa struttura)
│
├── frontend/                   # SvelteKit SPA
│   ├── src/
│   │   ├── routes/            # Pagine e routing
│   │   ├── lib/components/    # Componenti riutilizzabili
│   │   │   ├── ui/            # Componenti base (select/, input/, media/)
│   │   │   ├── layout/        # Header, Sidebar, Footer
│   │   │   ├── settings/      # Settings tabs e componenti
│   │   │   └── brokers/       # Broker-specific components
│   │   ├── lib/api/           # Zodios client + OpenAPI types
│   │   └── lib/i18n/          # Traduzioni (EN, IT, FR, ES)
│   ├── e2e/                   # Playwright E2E tests (67+ test)
│   └── build/                 # Build statica (servita da FastAPI)
│
├── scripts/                    # CLI tools
│   ├── cli_base.py            # Utilities condivise CLI
│   ├── cli_tree_parser.py     # TreeParser per help ad albero
│   ├── test_runner.py         # Orchestratore test suite
│   ├── user_cli.py            # User management CLI
│   └── list_api_endpoints.py  # Lista endpoint API
│
├── mkdocs_src/                 # Documentazione MkDocs
│   └── docs/gallery/          # Screenshot UI (224 immagini light/dark)
│
├── dev.py                      # Entry point CLI principale (Python)
├── dev.sh                      # Wrapper bash per backward compatibility
└── LibreFolio_developer_journal/  # Documentazione e roadmap
    └── RoadmapV4_UI/          # Piano frontend attivo
        ├── plan-*.md          # Plan attivi
        └── phases/            # Sotto-plan per fase
            └── phase-04-subplan/  # 13+ sub-plan completati Phase 4
```

## 🔧 Stack Tecnologico

### Backend (Python)

- **FastAPI**: Framework web async
- **SQLModel + SQLite**: ORM + database embedded
- **Alembic**: Migrazioni schema
- **Pipenv**: Gestione dipendenze
- **Pytest**: Test suite completa

### Frontend (TypeScript/Svelte)

- **SvelteKit 2.48+**: Framework UI reattivo
- **Tailwind CSS 4.1+**: Styling utility-first (config via `@theme` in CSS)
- **Zodios**: Client API type-safe con validazione Zod
- **lucide-svelte**: Icone
- **Playwright**: E2E testing
- **Apache ECharts**: Grafici finanziari (da implementare)

### Deploy

- **Single Docker Image**: Backend serve frontend come file statici
- **Sviluppo**: Backend :8000, Frontend dev :5173 (con HMR)
- **Produzione**: Solo :8000, frontend pre-built servito da FastAPI

## 📐 Scelte Progettuali Chiave

1. **Calcoli solo nel Backend**: Il frontend è pura presentazione, non fa calcoli
2. **FIFO a Runtime**: Matching costi calcolato on-demand, non persistito
3. **Provider Registry Pattern**: Auto-discovery per FX, Asset e BRIM providers
4. **Multi-Provider con Fallback**: FX rates da ECB→FED→BOE→SNB con backward-fill
5. **Scheduled-Yield Assets**: Valutazione prestiti P2P dalla schedule interessi
6. **Tailwind v4**: Configurazione tramite `@theme {}` in CSS, no file config TS
7. **Multi-User Broker Access**: Owner/Editor/Viewer roles per condivisione broker
8. **Zodios API Client**: Tipi derivati da OpenAPI, validazione runtime
9. **Data Separation prod/test**: Dati completamente isolati tra ambienti
10. **Svelte 5 Runes**: Componenti nuovi usano $state, $derived, $effect
11. **E2E Test Gallery**: Screenshot automatici per documentazione (light/dark)

## 📊 Stato Attuale (6 Febbraio 2026)

### ✅ Backend Completato

- **Database**: Schema con Users, Brokers, Assets, Transactions, FX Rates, Price History
- **API**: 84+ endpoints operativi per tutte le entità
- **Auth**: Registrazione, Login, Session cookie, Password change, First user = admin
- **FX Multi-Provider**: ECB, FED, BOE, SNB con fallback automatico
- **Asset Providers**: yfinance, JustETF, CSS Scraper, Scheduled Investment
- **BRIM**: 11 plugin (IBKR, Degiro, Directa, eToro, Coinbase, Revolut, Trading212, etc.)
- **Broker Access Control**: Multi-user con ruoli Owner/Editor/Viewer
- **Data Separation**: Cartelle prod/test completamente isolate (`backend/data/prod/`, `backend/data/test/`)
- **Test Suite**: 8/8 categorie passano (external, db, services, utils, schemas, api, e2e, frontend)

### ✅ Frontend Completato (Phase 0-3.5 + gran parte Phase 4)

- **Login/Register/Forgot Password**: Modali funzionanti con animazioni
- **Dashboard Placeholder**: Struttura base con navigazione
- **Settings Page**: User preferences + Global settings (admin only), layout mobile responsive
- **Broker Management**: Lista, CRUD, dettaglio con holdings/transactions
- **Files Management**: Upload, lista, BRIM import associato a broker, filtri URL-based
- **Component Library**: Famiglia Select unificata (BaseDropdown, SimpleSelect, SearchSelect)
- **Password Strength Meter**: zxcvbn-ts integration
- **AnimatedBackground**: Onde animate + linee grafici
- **Design System**: Colori brand (#1a4031 verde, #f5f4ef beige), dark mode completo
- **i18n**: Supporto EN, IT, FR, ES con CLI per gestione traduzioni
- **Mobile Responsive**: Settings e layout ottimizzati per mobile
- **E2E Tests**: 67+ test Playwright, gallery con 224 screenshot (light/dark)
- **Zodios API Client**: Type-safe con validazione Zod runtime

### 🔄 In Corso (Phase 4 finale)

- **UI Fixes**: Bug scoperti durante test (preferences al login, modal scroll, etc.)
- **Image Crop Component**: Per upload avatar/icone broker

### 🔲 Da Implementare (Phase 5+)

- **Phase 5**: FX Management Pages
- **Phase 6**: Asset Management Pages
- **Phase 7**: Transaction Management + BRIM Import UI completa
- **Phase 8**: Dashboard con grafici ECharts e KPIs
- **Phase 9**: Polish & Responsive finale

## 📁 Dove Trovare Cosa

| Cosa cerchi?            | Dove guardare                                             |
|-------------------------|-----------------------------------------------------------|
| **Modelli DB**          | `backend/app/db/models.py`                                |
| **Schemi API**          | `backend/app/schemas/*.py`                                |
| **Business Logic**      | `backend/app/services/*.py`                               |
| **API Endpoints**       | `backend/app/api/v1/*.py`                                 |
| **Config & Data Paths** | `backend/app/config.py` (get_data_dir, etc.)              |
| **Provider FX**         | `backend/app/services/fx_providers/`                      |
| **Provider Asset**      | `backend/app/services/asset_source_providers/`            |
| **Import Broker**       | `backend/app/services/brim_providers/`                    |
| **Backend Test Suite**  | `backend/test_scripts/`                                   |
| **Dati Produzione**     | `backend/data/prod/` (sqlite, uploads, logs)              |
| **Dati Test**           | `backend/data/test/` (isolati, stessa struttura)          |
| **Frontend Pages**      | `frontend/src/routes/`                                    |
| **Componenti UI Base**  | `frontend/src/lib/components/ui/`                         |
| **Componenti Select**   | `frontend/src/lib/components/ui/select/`                  |
| **Componenti Settings** | `frontend/src/lib/components/settings/`                   |
| **E2E Tests**           | `frontend/e2e/`                                           |
| **API Client (Zodios)** | `frontend/src/lib/api/`                                   |
| **Traduzioni**          | `frontend/src/lib/i18n/locales/`                          |
| **CLI Scripts**         | `scripts/`                                                |
| **Roadmap UI**          | `LibreFolio_developer_journal/RoadmapV4_UI/`              |
| **Plan attivi**         | `RoadmapV4_UI/plan-*.md` (root)                           |
| **Plan completati**     | `RoadmapV4_UI/phases/phase-04-subplan/`                   |
| **Phase 4 Summary**     | `RoadmapV4_UI/phases/phase-04-subplan/plan-phase04-summary.md` |
| **Dark Mode Guide**     | `RoadmapV4_UI/phases/phase-04-subplan/GUIDA-DARK-MODE.md` |

## 🛠️ Comandi Utili - USARE SEMPRE dev.py

⚠️ **REGOLA FONDAMENTALE**: Per operazioni complesse, usa SEMPRE `./dev.py`.
Non eseguire comandi manuali quando esiste uno script che fa quel lavoro!

### Command Tree (./dev.py --help)

```
dev.py [-h]
├──╴server [--test] [--rebuild] [-h]  # Avvia server (--test per test mode)
├─┬╴db [-h]                           # Database commands
│ ├──╴check [PATH]                    # Verifica CHECK constraints
│ ├──╴current [PATH]                  # Mostra migrazione corrente
│ ├──╴migrate MESSAGE [PATH]          # Crea nuova migrazione
│ ├──╴upgrade [PATH]                  # Applica migrazioni
│ ├──╴downgrade [PATH]                # Rollback una migrazione
│ ╰──╴create-clean [--test]           # Cancella e ricrea DB da zero
├─┬╴front [-h]                        # Frontend commands
│ ├──╴dev                             # Dev server con HMR (:5173)
│ ├──╴build                           # Build produzione
│ ├──╴check                           # Type-check Svelte/TypeScript
│ ╰──╴preview                         # Preview build locale
├─┬╴test [--coverage] [-v]            # Test suite
│ ├──╴external ACTION                 # Provider tests (FX, assets, BRIM)
│ ├──╴db ACTION                       # Database layer tests (populate)
│ ├──╴services ACTION                 # Service logic tests
│ ├──╴utils ACTION                    # Utility tests
│ ├──╴schemas ACTION                  # Schema validation tests
│ ├──╴api ACTION                      # API endpoint tests
│ ├──╴e2e ACTION                      # End-to-end tests
│ ├──╴front ACTION                    # Frontend E2E (Playwright)
│ ╰──╴all                             # Tutti i test
├─┬╴user [--test-db]                  # User management
│ ├──╴create EMAIL PASSWORD USERNAME
│ ├──╴list
│ ├──╴reset NEW_PASSWORD USERNAME
│ ├──╴activate/deactivate USERNAME
│ ├──╴promote/demote USERNAME
│ ╰──╴init-settings
├─┬╴mkdocs [-h]                       # Documentation
│ ├──╴build                           # Build sito docs
│ ├──╴serve                           # Serve localmente (:8002)
│ ├──╴clean                           # Rimuove site/
│ ├──╴gallery                         # Genera screenshot con Playwright
│ ╰──╴deploy                          # Deploy GitHub Pages
├─┬╴api [-h]                          # API schema tools
│ ├──╴schema                          # Export OpenAPI
│ ├──╴client                          # Genera client TypeScript
│ ╰──╴sync                            # schema + client
├─┬╴i18n [-h]                         # Translation management
│ ├──╴audit [--format]                # Audit traduzioni (coverage report)
│ ├──╴add KEY --en --it --fr --es     # Aggiungi chiave a tutte le lingue
│ ├──╴remove KEY [-f]                 # Rimuovi chiave da tutte le lingue
│ ├──╴update KEY [--en] [--it] [--fr] [--es]  # Modifica traduzioni
│ ╰──╴search QUERY                    # Cerca nelle chiavi e valori
├─┬╴cache [-h]
│ ╰──╴js [--force]                    # Aggiorna cache JS
├─┬╴info [-h]
│ ╰──╴api                             # Lista tutti endpoint
├──╴format                            # Format con black
├──╴lint                              # Lint con ruff
├──╴shell                             # Pipenv shell
╰──╴install                           # Installa dipendenze
```

### Scenari Comuni

| Scenario                          | Comando                                                                    |
|-----------------------------------|----------------------------------------------------------------------------|
| **Avviare per sviluppo**          | `./dev.py server`                                                          |
| **Avviare in test mode**          | `./dev.py server --test`                                                   |
| **Frontend con HMR**              | Terminal 1: `./dev.py server` — Terminal 2: `./dev.py front dev`           |
| **Verificare che tutto funzioni** | `./dev.py test all`                                                        |
| **Solo test frontend**            | `./dev.py test front all`                                                  |
| **Popola DB con dati mock**       | `./dev.py test db populate --force`                                        |
| **Genera gallery screenshot**     | `./dev.py mkdocs gallery`                                                  |
| **Dopo modifica modelli DB**      | `./dev.py db create-clean`                                                 |
| **Dopo modifica API**             | `./dev.py api sync`                                                        |
| **Verificare traduzioni**         | `./dev.py i18n audit`                                                      |
| **Aggiungere traduzione**         | `./dev.py i18n add "key.path" --en "..." --it "..." --fr "..." --es "..."` |
| **Cercare traduzioni**            | `./dev.py i18n search "query"`                                             |
| **Modificare traduzione**         | `./dev.py i18n update "key.path" --it "nuova traduzione"`                  |
| **Build per produzione**          | `./dev.py front build && ./dev.py server`                                  |
| **Nuovo utente**                  | `./dev.py user create admin admin@mail.com pass`                           |
| **Reset password**                | `./dev.py user reset username newpassword`                                 |
| **Lista endpoint API**            | `./dev.py info api`                                                        |

## ⚠️ Note per lo Sviluppo

- **Progetto embrionale**: Esiste solo su questa macchina
- **No backward compatibility**: Pulisci invece di mantenere legacy
- **Codice in inglese**: Commenti, docstrings, README
- **UI multilingue**: Solo interfaccia grafica in EN/IT/FR/ES
- **Obiettivo**: Codebase pulito e mantenibile per condivisione futura
- **No migrazioni Alembic**: Modifica `001_initial.py` e ricrea DB
- **Edit better rewrite**: Evita di riscrivere tutto un file se già esiste, preferisci modifiche puntuali per evitare perdite di funzionalità

Prima di proseguire:

1. ✅ Rivedi stato attuale (codebase, modelli, endpoint)
2. ✅ Consulta il plan corrente in `LibreFolio_developer_journal/RoadmapV4_UI/`
3. ✅ Segnala inconsistenze o necessità di cleanup

Grazie!
