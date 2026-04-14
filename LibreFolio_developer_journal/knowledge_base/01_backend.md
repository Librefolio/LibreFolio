# LibreFolio — Backend Reference

## 📁 Struttura

```text
backend/
├── app/
│   ├── api/v1/                # REST API endpoints (~82)
│   ├── db/models.py           # SQLModel ORM models
│   ├── schemas/               # Pydantic schemas (validazione I/O)
│   ├── services/              # Business logic
│   │   ├── asset_source_providers/   # yfinance, JustETF, CSS Scraper, Scheduled Investment
│   │   ├── fx_providers/             # ECB, FED, BOE, SNB, MANUAL
│   │   └── brim_providers/           # 11 plugin import broker
│   ├── config.py              # get_data_dir(), paths, env vars
│   └── utils/                 # Utilities condivise
├── alembic/                   # Migrazioni database (001_initial.py)
├── test_scripts/              # Test suite completa (850+ test, 8 categorie)
│   └── ...
└── data/
    ├── prod/                  # sqlite/app.db, broker_reports/, logs/
    └── test/                  # Stessa struttura, isolati
```

---

## 🗄️ Database

- **Engine**: SQLite via SQLModel (SQLAlchemy async)
- **Schema principale**: Users, Brokers, BrokerAccess, Assets, Transactions, FxPairConfig, FxRate, PriceHistory, GlobalSettings
- **Migrazioni**: Alembic, ma in fase embrionale si modifica `001_initial.py` e si ricrea con `./dev.py db create-clean`
- **Data separation**: `backend/data/prod/` vs `backend/data/test/` — cartelle completamente isolate

---

## 🔌 Provider Pattern

Tutti i provider usano **auto-discovery** tramite Registry Pattern.

### FX Providers (`fx_providers/`)

| Provider | Fonte | Coppie |
|----------|-------|--------|
| ECB | XML feed | EUR-based |
| FED | JSON API | USD-based |
| BOE | JSON API | GBP-based |
| SNB | JSON API | CHF-based |
| MANUAL | Sentinella | Qualsiasi (auto-insert priority=999) |

**MANUAL**: auto-insert quando nessun provider reale, auto-remove quando se ne aggiunge uno, auto-reinstate quando si rimuove l'ultimo.

### Asset Providers (`asset_source_providers/`)

| Provider | `identifier` | `provider_params` | `supports_search` |
|----------|-------------|-------------------|-------------------|
| `yfinance` | ticker (es. "AAPL") | `None` | ✅ |
| `justetf` | ISIN (es. "IE00B4L5Y983") | `None` | ✅ |
| `cssscraper` | URL pagina web | `{current_css_selector, currency, decimal_format?}` | ❌ |
| `scheduled_investment` | asset_id | `FAScheduledInvestmentSchedule` (complesso) | ❌ |

Ogni provider espone `params_schema` (proprietà sulla base class) per descrivere i campi `provider_params` necessari → il frontend genera form dinamici.

### Provider Core Cache & Thread Isolation

Tutte le chiamate ai provider asset passano per un layer centralizzato in `asset_source.py`:

1. **Thread Isolation**: `_run_provider_in_thread()` esegue ogni chiamata provider in un thread dedicato con event loop proprio. I provider non devono più usare `asyncio.to_thread()`.

2. **Cache Core** (5 cache, auto-registrate in `cache_utils` → visibili in admin):

| Cache | TTL | Scope |
|-------|-----|-------|
| `asset_history_fetch` | 15 min | Smart range per-date granularity |
| `asset_current_fetch` | 2 min | Polling frontend ogni 30s |
| `asset_metadata_fetch` | 30 min | Refresh esplicito |
| `search_queries` | 15 min | Query esatte ripetute |
| `search_results` | 24h | Item individuali |

3. **Probe bypassa la cache**: `probe_provider_config()` usa solo thread isolation, niente cache.

### BRIM Providers (`brim_providers/`)

11 plugin: IBKR, Degiro, Directa, eToro, Coinbase, Revolut, Trading212, Bitpanda, Bitvavo, Schwab, Parqet.

---

## 🔐 Auth

- Cookie-based sessions (JWT in HttpOnly cookie)
- Multi-worker: JWT stateless (no session store)
- First user = admin automatico
- Ruoli broker: Owner / Editor / Viewer

---

## 🧪 Test

8 categorie via `./dev.py test <category> <action>` — **850+ test** totali:

| Categoria | Cosa testa |
|-----------|-----------|
| `external` | Provider FX, Asset, BRIM (rete) |
| `db` | Layer database, populate |
| `services` | Business logic |
| `utils` | Utilities |
| `schemas` | Validazione Pydantic |
| `api` | Endpoint REST (276 test: 70 asset, 28 fx, 22 brokers, 21 auth, …) |
| `e2e` | End-to-end backend (search→create→assign→sync) |
| `front` | Playwright E2E frontend (181+ test, 4 categorie: utility/user/fx/asset) |

---

## 📍 Dove Trovare Cosa

| Cosa cerchi? | Dove guardare |
|--------------|---------------|
| Modelli DB | `backend/app/db/models.py` |
| Schemi API | `backend/app/schemas/*.py` |
| Business Logic | `backend/app/services/*.py` |
| API Endpoints | `backend/app/api/v1/*.py` |
| Config & Data Paths | `backend/app/config.py` |
| Provider FX | `backend/app/services/fx_providers/` |
| Provider Asset | `backend/app/services/asset_source_providers/` |
| Import Broker | `backend/app/services/brim_providers/` |
| System & Health | `backend/app/api/v1/system.py` |
| Backup & Restore | `backend/app/api/v1/backup.py` |
| Test Suite | `backend/test_scripts/` |
| Test Asset API | `backend/test_scripts/test_api/test_assets_*.py` (5 file, 70 test) |
| Coverage Analysis | `scripts/coverage_analysis.py` |
| Coverage Config | `.coveragerc` + `sitecustomize.py` |
| Dati Produzione | `backend/data/prod/` |
| Dati Test | `backend/data/test/` |

