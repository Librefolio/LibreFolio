# LibreFolio — Backend Reference

## 📁 Struttura

```text
backend/
├── app/
│   ├── api/v1/                # REST API endpoints (84+)
│   ├── db/models.py           # SQLModel ORM models
│   ├── schemas/               # Pydantic schemas (validazione I/O)
│   ├── services/              # Business logic
│   │   ├── asset_source_providers/   # yfinance, JustETF, CSS Scraper, Scheduled
│   │   ├── fx_providers/             # ECB, FED, BOE, SNB, MANUAL
│   │   └── brim_providers/           # 11 plugin import broker
│   ├── config.py              # get_data_dir(), paths, env vars
│   └── utils/                 # Utilities condivise
├── alembic/                   # Migrazioni database (001_initial.py)
├── test_scripts/              # Test suite completa (8 categorie)
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

yfinance, JustETF scraper, CSS Scraper (BeautifulSoup), Scheduled Investment.

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

8 categorie via `./dev.py test <category> <action>`:

| Categoria | Cosa testa |
|-----------|-----------|
| `external` | Provider FX, Asset, BRIM (rete) |
| `db` | Layer database, populate |
| `services` | Business logic |
| `utils` | Utilities |
| `schemas` | Validazione Pydantic |
| `api` | Endpoint REST (20+ FX tests) |
| `e2e` | End-to-end backend |
| `front` | Playwright E2E frontend (67+ test) |

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
| Test Suite | `backend/test_scripts/` |
| Dati Produzione | `backend/data/prod/` |
| Dati Test | `backend/data/test/` |

