Ciao! Sto lavorando su un portfolio tracker finanziario self-hosted chiamato **LibreFolio**.

## 🎯 Obiettivo del Progetto

LibreFolio è un'alternativa self-hosted e open-source a Ghostfolio, pensata per:

- **Privacy**: I tuoi dati finanziari restano sul tuo server
- **Flessibilità**: Supporto per asset tradizionali, crypto, prestiti P2P, scheduled-yield
- **Controllo**: Import da qualsiasi broker tramite plugin estensibili
- **Multi-utenza**: Più utenti con preferenze personalizzate

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
│   └── data/sqlite/           # Database SQLite
│
├── frontend/                   # SvelteKit SPA
│   ├── src/
│   │   ├── routes/            # Pagine e routing
│   │   ├── lib/components/    # Componenti riutilizzabili
│   │   └── lib/i18n/          # Traduzioni (EN, IT, FR, ES)
│   └── build/                 # Build statica (servita da FastAPI)
│
├── dev.sh                      # Script principale per sviluppo
├── test_runner.py              # Orchestratore test suite
└── LibreFolio_developer_journal/  # Documentazione e roadmap
    └── RoadmapV4_UI/plan-frontendDevelopment.prompt.md
```

## 🔧 Stack Tecnologico

### Backend (Python)

- **FastAPI**: Framework web async
- **SQLModel + SQLite**: ORM + database embedded
- **Alembic**: Migrazioni schema
- **Pipenv**: Gestione dipendenze

### Frontend (TypeScript/Svelte)

- **SvelteKit 2.48+**: Framework UI reattivo
- **Tailwind CSS 4.1+**: Styling utility-first (config via `@theme` in CSS)
- **lucide-svelte**: Icone
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

## 📊 Stato Attuale (Gennaio 2026)

### ✅ Backend Completato

- **Database**: Schema con Users, Brokers, Assets, Transactions, FX Rates, Price History
- **API**: 60+ endpoints operativi per tutte le entità
- **Auth**: Registrazione, Login, Session cookie, Password reset (via CLI)
- **FX Multi-Provider**: ECB, FED, BOE, SNB con fallback automatico
- **Asset Providers**: yfinance, JustETF, CSS Scraper, Scheduled Investment
- **BRIM**: Broker Report Import Manager con plugin (Generic CSV, Directa, Degiro, eToro, etc.)
- **Test Suite**: 7/7 categorie passano

### ✅ Frontend Completato (Phase 0-2.5)

- **Login Page**: Modale login con animazioni, cambio lingua
- **Register Modal**: Registrazione utente funzionante
- **Forgot Password Modal**: Istruzioni per reset via CLI
- **Dashboard Placeholder**: Struttura base con navigazione
- **AnimatedBackground**: Onde animate + linee grafici
- **Build Integration**: Auto-build in dev.sh, FastAPI serve static files
- **Design System**: Colori brand (#1a4031 verde, #f5f4ef beige)
- **i18n**: Supporto EN, IT, FR, ES

### 🔲 Da Implementare (Phase 3+)

- **Phase 3**: Layout App + Settings Page
- **Phase 4**: Broker Management Pages
- **Phase 5**: FX Management Pages
- **Phase 6**: Asset Management Pages
- **Phase 7**: Transaction Management + BRIM Import UI
- **Phase 8**: Dashboard con grafici e KPIs
- **Phase 9**: Polish & Responsive (incrementale)

## 📁 Dove Trovare Cosa

| Cosa cerchi?       | Dove guardare                                  |
|--------------------|------------------------------------------------|
| **Modelli DB**     | `backend/app/db/models.py`                     |
| **Schemi API**     | `backend/app/schemas/*.py`                     |
| **Business Logic** | `backend/app/services/*.py`                    |
| **API Endpoints**  | `backend/app/api/v1/*.py`                      |
| **Provider FX**    | `backend/app/services/fx_providers/`           |
| **Provider Asset** | `backend/app/services/asset_source_providers/` |
| **Import Broker**  | `backend/app/services/brim_providers/`         |
| **Test Suite**     | `backend/test_scripts/`                        |
| **Frontend Pages** | `frontend/src/routes/`                         |
| **Componenti UI**  | `frontend/src/lib/components/`                 |
| **Roadmap UI**     | `LibreFolio_developer_journal/RoadmapV4_UI/`   |

## 🛠️ Comandi Utili - USARE SEMPRE QUESTI SCRIPT

⚠️ **REGOLA FONDAMENTALE**: Per operazioni complesse, usa SEMPRE `dev.sh`, `test_runner.py` o `user_cli.py`.
Non eseguire comandi manuali quando esiste uno script che fa quel lavoro!

### dev.sh - Script Principale

```bash
# Visualizza tutti i comandi disponibili
./dev.sh --help

# === SERVER ===
./dev.sh server              # Avvia backend+frontend su :8000 (auto-build frontend)
./dev.sh server:test         # Avvia in test mode su :8001 (usa test_app.db)

# === FRONTEND ===
./dev.sh fe:dev              # Dev server con HMR su :5173
./dev.sh fe:build            # Build production → frontend/build/
./dev.sh fe:check            # Type-check Svelte/TypeScript

# === DATABASE ===
./dev.sh db:upgrade          # Applica migrazioni al DB
./dev.sh db:check            # Verifica CHECK constraints
./dev.sh db:current          # Mostra migrazione corrente
./dev.sh db:migrate "msg"    # Crea nuova migrazione

# === TESTING ===
./dev.sh test all            # Tutti i test
./dev.sh test api assets     # Solo test API assets
./dev.sh test external fx    # Solo test provider FX
./dev.sh test db brim        # Solo test BRIM database
./dev.sh test:coverage       # Test con coverage HTML

# === API SCHEMA (OpenAPI → TypeScript) ===
./dev.sh api:schema          # Genera openapi.json
./dev.sh api:client          # Genera client TypeScript da schema
./dev.sh api:sync            # schema + client insieme

# === USER MANAGEMENT ===
./dev.sh user:create <user> <email> <pass>   # Crea utente
./dev.sh user:list                            # Lista utenti
./dev.sh user:reset <user> <new_pass>        # Reset password
./dev.sh user:activate <user>                 # Attiva utente
./dev.sh user:deactivate <user>               # Disattiva utente

# === UTILITIES ===
./dev.sh format              # Formatta codice con black
./dev.sh lint                # Linting con ruff
./dev.sh info:api            # Lista tutti gli endpoint API
./dev.sh info:mk build       # Genera documentazione MkDocs

# === i18n TRANSLATIONS ===
./dev.sh i18n:audit          # Audit traduzioni, mostra chiavi mancanti (Markdown)
./dev.sh i18n:audit:xlsx     # Esporta audit in Excel
./dev.sh i18n:audit:both     # Esporta in Markdown + Excel
```

### test_runner.py - Orchestratore Test

```bash
# Mostra help dettagliato
./test_runner.py --help

# Categorie disponibili
./test_runner.py external fx         # Provider FX (ECB, FED, etc.)
./test_runner.py external assets     # Provider Asset (yfinance, justETF)
./test_runner.py external brim-providers  # BRIM plugins
./test_runner.py db all              # Tutti i test database
./test_runner.py api all             # Tutti i test API
./test_runner.py schemas all         # Tutti i test schema

# Opzioni utili
./test_runner.py --reset db all      # Reset DB prima dei test
./test_runner.py -v api auth         # Verbose mode
```

### user_cli.py - Gestione Utenti

```bash
# Lista utenti (usa il DB di produzione di default)
python user_cli.py list-users

# Operazioni su DB di test (--test-db)
python user_cli.py --test-db list-users

# Creazione utente
python user_cli.py create-user <username> <email> <password>

# Promuovi a superuser
python user_cli.py promote-user <username>

# Reset password
python user_cli.py reset-password <username> <new_password>

# Attiva/Disattiva utente
python user_cli.py activate-user <username>
python user_cli.py deactivate-user <username>
```

## 🖥️ Note per AI Agent - Frontend e MCP Browser

⚠️ **IMPORTANTE per operazioni UI**:

Quando devi lavorare sul frontend o verificare il comportamento dell'interfaccia:

1. **Usa il browser MCP tool** (Playwright) per interagire con la UI
2. **NON usare curl** per verificare comportamenti visivi/UI
3. **curl è solo per testare endpoint API** (risposte JSON, status code, ecc.)

```bash
# Per verificare endpoint API → usa curl o httpx
curl http://localhost:8000/api/v1/auth/me

# Per verificare UI → usa browser MCP tools:
# - mcp_microsoft_pla_browser_navigate: navigare URL
# - mcp_microsoft_pla_browser_snapshot: catturare stato accessibilità
# - mcp_microsoft_pla_browser_click: cliccare elementi
# - mcp_microsoft_pla_browser_type: digitare in form
# - mcp_microsoft_pla_browser_take_screenshot: screenshot per debug
```

### Scenari Comuni

| Scenario                           | Comando                                                       |
|------------------------------------|---------------------------------------------------------------|
| **Nuovo utente dopo deploy**       | `./dev.sh user:create admin admin@mail.com password123`       |
| **Password dimenticata**           | `./dev.sh user:reset username newpassword`                    |
| **Avviare tutto per sviluppo**     | Terminal 1: `./dev.sh server` — Terminal 2: `./dev.sh fe:dev` |
| **Verificare che tutto funzioni**  | `./dev.sh test all`                                           |
| **Dopo modifica modelli DB**       | 1. `rm backend/data/sqlite/*.db` — 2. `./dev.sh db:upgrade`   |
| **Dopo modifica API**              | `./dev.sh api:sync` (rigenera client TypeScript)              |
| **Verificare traduzioni complete** | `./dev.sh i18n:audit`                                         |
| **Build per produzione**           | `./dev.sh fe:build && ./dev.sh server`                        |
| **Debug test singolo**             | `./dev.sh test -v api <test_name>`                            |

## 🔗 Link Utili

- **Repository GitHub**: https://github.com/Alfystar/LibreFolio
- **Documentazione Locale**: http://localhost:8000/mkdocs/
- **API Swagger**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

## ⚠️ Note per lo Sviluppo

- **Progetto embrionale**: Esiste solo su questa macchina
- **No backward compatibility**: Pulisci invece di mantenere legacy
- **Codice in inglese**: Commenti, docstrings, README
- **UI multilingue**: Solo interfaccia grafica in EN/IT/FR/ES
- **Obiettivo**: Codebase pulito e mantenibile per condivisione futura
- **Migrazioni DB**: Durante lo sviluppo, modifica `001_initial.py` e ricrea DB invece di creare migrazioni

## 📝 Convenzioni DB

- **Primo utente = Superuser**: Il primo utente registrato diventa automaticamente superuser
- **BrokerUserAccess**: Ogni broker ha ownership tramite tabella `broker_user_access`
  - Ruoli: `OWNER` (tutto), `EDITOR` (modifica, no delete/share), `VIEWER` (solo lettura)
- **Creazione broker**: Automaticamente crea accesso OWNER per l'utente creatore

Prima di proseguire:

1. ✅ Rivedi stato attuale (codebase, modelli, endpoint)
2. ✅ Consulta il plan: `LibreFolio_developer_journal/RoadmapV4_UI/plan-frontendDevelopment.prompt.md`
3. ✅ Segnala inconsistenze o necessità di cleanup

Grazie!
