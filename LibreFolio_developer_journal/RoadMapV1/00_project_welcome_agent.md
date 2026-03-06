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
│   │   │   ├── fx_providers/             # ECB, FED, BOE, SNB, MANUAL
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
│   │   ├── routes/(app)/      # Pagine protette da auth
│   │   │   ├── dashboard/     # Dashboard (placeholder)
│   │   │   ├── brokers/       # Lista broker + [id] dettaglio
│   │   │   ├── fx/            # Lista FX + [pair] dettaglio ← PHASE 5
│   │   │   ├── assets/        # Placeholder (Phase 6)
│   │   │   ├── transactions/  # Placeholder (Phase 7)
│   │   │   ├── files/         # File management
│   │   │   └── settings/      # User & global settings
│   │   ├── lib/components/    # Componenti riutilizzabili
│   │   │   ├── ui/            # Componenti base
│   │   │   │   ├── select/    # BaseDropdown, SimpleSelect, SearchSelect,
│   │   │   │   │              # CurrencySearchSelect, BrokerSearchSelect,
│   │   │   │   │              # FxProviderSelect, ImportPluginSelect
│   │   │   │   ├── input/     # Input components
│   │   │   │   ├── media/     # ImagePicker, ImageEdit
│   │   │   │   ├── DateRangePicker.svelte  # Calendario dual-column custom
│   │   │   │   ├── OrderableList.svelte    # Drag & drop + frecce riordinamento
│   │   │   │   ├── ModalBase.svelte        # Base modale riusabile
│   │   │   │   ├── ConfirmModal.svelte     # Modale di conferma
│   │   │   │   ├── Tooltip.svelte          # Tooltip hover
│   │   │   │   └── ErrorBanner.svelte      # Banner errore
│   │   │   ├── charts/        # Libreria grafici ECharts ← NUOVA Phase 5
│   │   │   │   ├── LineChart.svelte        # Grafico linee con visualMap colori
│   │   │   │   ├── CandlestickChart.svelte # Grafico candele
│   │   │   │   ├── DataZoomBar.svelte      # Barra zoom temporale
│   │   │   │   ├── VolumeBar.svelte        # Barra variazione %
│   │   │   │   ├── MeasureOverlay.svelte   # Overlay misura click-to-click
│   │   │   │   ├── ChartToolbar.svelte     # Toolbar Line/Candle, Abs/%
│   │   │   │   ├── PriceChartFull.svelte   # Chart completo (detail page)
│   │   │   │   ├── PriceChartCompact.svelte# Chart compatto (card)
│   │   │   │   ├── SemiDonutChart.svelte   # Semicerchio (broker sharing)
│   │   │   │   └── EditPopup.svelte        # Popup edit valore
│   │   │   ├── fx/            # FX-specific components ← NUOVA Phase 5
│   │   │   │   ├── FxCard.svelte           # Card coppia FX con mini-chart
│   │   │   │   ├── FxPairAddModal.svelte   # Modale aggiunta coppia
│   │   │   │   ├── FxProviderConfig.svelte # Config provider con OrderableList
│   │   │   │   ├── FxEditSection.svelte    # Edit bulk rates (CSV + manual)
│   │   │   │   ├── FxSyncModal.svelte      # Modale sync
│   │   │   │   └── CsvEditor.svelte        # Editor CSV inline
│   │   │   ├── layout/        # Header, Sidebar, Footer
│   │   │   ├── settings/      # Settings tabs e componenti
│   │   │   ├── brokers/       # Broker-specific components
│   │   │   ├── auth/          # Login, Register, ForgotPassword modals
│   │   │   ├── files/         # FilesTable
│   │   │   └── table/         # DataTable generico
│   │   ├── lib/stores/        # Svelte stores
│   │   │   ├── TimeSeriesStore.ts    # Cache client-side generica ← Phase 5
│   │   │   ├── fxStoreRegistry.ts    # Registry cache per coppie FX
│   │   │   ├── EditBuffer.ts         # Buffer edit con dirty tracking
│   │   │   ├── auth.ts, settings.ts, language.ts, globalSettings.ts
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
            ├── phase-04-subplan/  # 13+ sub-plan completati Phase 4
            └── phase-05-subplan/  # Sub-plan completati Phase 5
```

## 🔧 Stack Tecnologico

### Backend (Python)

- **FastAPI**: Framework web async
- **SQLModel + SQLite**: ORM + database embedded
- **Alembic**: Migrazioni schema
- **Pipenv**: Gestione dipendenze
- **Pytest**: Test suite completa

### Frontend (TypeScript/Svelte)

- **SvelteKit 2.48+**: Framework UI reattivo (Svelte 5 con Runes)
- **Tailwind CSS 4.1+**: Styling utility-first (config via `@theme` in CSS)
- **Zodios**: Client API type-safe con validazione Zod
- **Apache ECharts 5.6+**: Grafici finanziari (linee, candele, zoom, measure)
- **lucide-svelte**: Icone
- **Playwright**: E2E testing

### Deploy

- **Single Docker Image**: Backend serve frontend come file statici
- **Sviluppo**: Backend :8000, Frontend dev :5173 (con HMR)
- **Produzione**: Solo :8000, frontend pre-built servito da FastAPI

## 📐 Scelte Progettuali Chiave

1. **Calcoli solo nel Backend**: Il frontend è pura presentazione, non fa calcoli
2. **FIFO a Runtime**: Matching costi calcolato on-demand, non persistito
3. **Provider Registry Pattern**: Auto-discovery per FX, Asset e BRIM providers
4. **Multi-Provider con Fallback**: FX rates da ECB→FED→BOE→SNB con backward-fill
5. **MANUAL FX Provider**: Sentinella automatica per coppie senza provider (priority=999, auto-insert/remove dal backend)
6. **Scheduled-Yield Assets**: Valutazione prestiti P2P dalla schedule interessi
7. **Tailwind v4**: Configurazione tramite `@theme {}` in CSS, no file config TS
8. **Multi-User Broker Access**: Owner/Editor/Viewer roles per condivisione broker
9. **Zodios API Client**: Tipi derivati da OpenAPI, validazione runtime
10. **Data Separation prod/test**: Dati completamente isolati tra ambienti
11. **Svelte 5 Runes**: Componenti nuovi usano $state, $derived, $effect
12. **E2E Test Gallery**: Screenshot automatici per documentazione (light/dark)
13. **TimeSeriesStore<T>**: Cache client-side generica con gap-detection e merge incrementale
14. **Componenti chart modulari**: Libreria ECharts con 10+ sotto-componenti riusabili per FX e futuri Asset

## 📊 Stato Attuale (4 Marzo 2026)

### ✅ Backend Completato

- **Database**: Schema con Users, Brokers, Assets, Transactions, FX Rates, Price History
- **API**: 84+ endpoints operativi per tutte le entità
- **Auth**: Registrazione, Login, Session cookie, Password change, First user = admin
- **FX Multi-Provider**: ECB, FED, BOE, SNB + MANUAL (sentinella) con fallback automatico
- **FX Provider API potenziata**: `GET /fx/providers` restituisce `base_currencies` + `target_currencies`, con filtro opzionale per provider codes
- **Asset Providers**: yfinance, JustETF, CSS Scraper, Scheduled Investment
- **BRIM**: 11 plugin (IBKR, Degiro, Directa, eToro, Coinbase, Revolut, Trading212, etc.)
- **Broker Access Control**: Multi-user con ruoli Owner/Editor/Viewer
- **Data Separation**: Cartelle prod/test completamente isolate (`backend/data/prod/`, `backend/data/test/`)
- **Test Suite**: 8/8 categorie passano (external, db, services, utils, schemas, api, e2e, frontend)
- **FX API Tests**: 20 test incluso MANUAL lifecycle completo (auto-insert, auto-remove, sync skip, full delete)

### ✅ Frontend — Phase 4 Completata (Brokers, Files, Settings)

- **Login/Register/Forgot Password**: Modali funzionanti con animazioni
- **Dashboard Placeholder**: Struttura base con navigazione
- **Settings Page**: User preferences + Global settings (admin only), layout mobile responsive
- **Broker Management**: Lista, CRUD, dettaglio con holdings/transactions, sharing multi-user
- **Files Management**: Upload, lista, BRIM import associato a broker, filtri URL-based
- **Component Library**: Famiglia Select unificata (BaseDropdown, SimpleSelect, SearchSelect, CurrencySearchSelect, BrokerSearchSelect, FxProviderSelect, ImportPluginSelect)
- **Password Strength Meter**: zxcvbn-ts integration
- **AnimatedBackground**: Onde animate + linee grafici
- **Design System**: Colori brand (#1a4031 verde, #f5f4ef beige), dark mode completo
- **i18n**: Supporto EN, IT, FR, ES con CLI per gestione traduzioni
- **Mobile Responsive**: Settings e layout ottimizzati per mobile
- **E2E Tests**: 67+ test Playwright, gallery con 224 screenshot (light/dark)
- **Zodios API Client**: Type-safe con validazione Zod runtime

### 🔄 Frontend — Phase 5 In Corso (FX Management)

**Cosa è stato realizzato:**

- **Pagina FX List** (`/fx`): Lista card con mini-chart per ogni coppia configurata
  - **Filter bar 3 colonne responsive**: DateRangePicker + Currency filters + Actions (Abs/%, ⚙️ Settings, Sync All, Refresh All)
  - **DateRangePicker custom**: Calendario dual-column, presets (1W/1M/3M/6M/1Y/2Y), custom editabile con granularità, i18n completa, oggi evidenziato, giorni futuri grigi
  - **FxCard**: Mini-chart con inversione coppia, asse Y, variazione %, badge "Manual Only", delete, edit, navigate to detail
  - **FxPairAddModal**: CurrencySearchSelect per base/quote, FxProviderSelect con compatibilità automatica, OrderableList per priorità provider, info banners, save senza provider (MANUAL auto-insert)
  - **Filtri valuta**: CurrencySearchSelect con prop `allowedCurrencies` per filtrare solo le valute presenti nelle configurazioni
  - **Toggle globale Abs/%**: Propagato a tutte le card

- **Pagina FX Detail** (`/fx/[pair]`): Grafico avanzato per singola coppia
  - **PriceChartFull**: Line/Candlestick toggle, Abs/% toggle, zoom bidirezionale con DataZoomBar
  - **MeasureOverlay**: Click-to-click con 3-fase (start → draw → dismiss), info box con Δabs, Δ%, intervallo giorni
  - **FxProviderConfig**: Configurazione provider con OrderableList + Save/Cancel
  - **FxEditSection**: Edit bulk rates con CsvEditor + inserimento manuale singolo punto
  - **Inversione coppia**: Swap istantaneo con calcolo locale (1/rate)

- **TimeSeriesStore<T>**: Cache client-side generica con `getRange()`, `merge()`, `invalidateRange()`, `invalidateAll()`. Registry condivisa tra card e detail page.

- **Libreria Chart ECharts** (10+ componenti modulari):
  - LineChart con visualMap piecewise (rosso < 0, verde > 0 in % mode)
  - CandlestickChart per forex con apertura = chiusura giorno precedente
  - DataZoomBar collegata bidirezionalmente al chart principale
  - VolumeBar per variazione % giornaliera
  - MeasureOverlay con coordinate pixel reali
  - PriceChartCompact con mini-axis per card
  - SemiDonutChart (estratto da broker sharing per riuso)

- **Provider MANUAL** (backend + frontend):
  - Backend: auto-insert con priority=999 quando nessun provider reale, auto-remove quando si aggiunge provider reale, auto-reinstate quando si rimuove l'ultimo, filtrato da GET /fx/providers
  - Frontend: nascosto dalla UI, badge "Manual Only" sulle card, save senza provider crea automaticamente coppia MANUAL

- **Nuovi componenti UI generici** (riusabili anche in future fasi):
  - `DateRangePicker`: Calendario custom dual-column con presets e i18n
  - `OrderableList`: Drag & drop + frecce su/giù per riordinamento
  - `CurrencySearchSelect`: SearchSelect specializzato per valute con simboli/emoji, prop `allowedCurrencies`
  - `FxProviderSelect`: SearchSelect specializzato per provider FX con icone e badge compatibilità
  - `ConfirmModal`: Modale conferma azione distruttiva

**Cosa resta da rifinire (Phase 5 — Refinements):**

- **Step 8 del sub-plan**: Chart Settings ⚙️ popover (checkbox per baseline color, area fill, grid lines, stale gradient), overlay confronto tra coppie FX, linea di crescita sintetica (benchmark)
- **Stale data gradient**: Opacità ridotta per punti con backward-fill (dato vecchio)
- **Documentation**: Pagine MkDocs per FX (user guide), i18n MkDocs globale
- **Micro-fix UX**: Colori percentuale negativi segmentati per tutta la linea, tooltip con nota baseline

### 🔲 Da Implementare (Phase 6+)

- **Phase 6**: Asset Management Pages (lista, dettaglio, provider config)
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
| **Provider FX**         | `backend/app/services/fx_providers/` (ECB, FED, BOE, SNB, MANUAL) |
| **Provider Asset**      | `backend/app/services/asset_source_providers/`            |
| **Import Broker**       | `backend/app/services/brim_providers/`                    |
| **Backend Test Suite**  | `backend/test_scripts/`                                   |
| **Dati Produzione**     | `backend/data/prod/` (sqlite, uploads, logs)              |
| **Dati Test**           | `backend/data/test/` (isolati, stessa struttura)          |
| **Frontend Pages**      | `frontend/src/routes/(app)/`                              |
| **Componenti UI Base**  | `frontend/src/lib/components/ui/`                         |
| **Componenti Select**   | `frontend/src/lib/components/ui/select/`                  |
| **Componenti Chart**    | `frontend/src/lib/components/charts/`                     |
| **Componenti FX**       | `frontend/src/lib/components/fx/`                         |
| **Componenti Settings** | `frontend/src/lib/components/settings/`                   |
| **Stores (cache, auth)**| `frontend/src/lib/stores/`                                |
| **E2E Tests**           | `frontend/e2e/`                                           |
| **API Client (Zodios)** | `frontend/src/lib/api/`                                   |
| **Traduzioni**          | `frontend/src/lib/i18n/locales/`                          |
| **CLI Scripts**         | `scripts/`                                                |
| **Roadmap UI**          | `LibreFolio_developer_journal/RoadmapV4_UI/`              |
| **Plan attivi**         | `RoadmapV4_UI/plan-*.md` (root)                           |
| **Plan completati P4**  | `RoadmapV4_UI/phases/phase-04-subplan/`                   |
| **Plan completati P5**  | `RoadmapV4_UI/phases/phase-05-subplan/`                   |
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
│ ╰──╴search QUERY [-k] [-v] [-l LANG]  # Cerca in chiavi e/o valori, filtro per lingua
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
| **Cercare solo nelle chiavi**     | `./dev.py i18n search "common" --keys`                                     |
| **Cercare solo nei valori IT**    | `./dev.py i18n search "Annulla" --values --lang it`                        |
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
- **Test DB users**: `e2e_test_user` / `E2eTestPass123!` e `e2e_test_admin` / `E2eAdminPass123!`

Prima di proseguire:

1. ✅ Leggi i plan attivi in `RoadmapV4_UI/` per capire lo stato dettagliato
2. ✅ Rivedi il codice frontend FX (`routes/(app)/fx/`, `components/fx/`, `components/charts/`, `stores/`)
3. ✅ Controlla `./dev.py front check` e `./dev.py front build` per assicurarti che sia tutto green
4. ✅ Segnala inconsistenze o necessità di cleanup

Grazie!
