---
applyTo: "backend/**"
---

# Backend Reference

## Structure

```text
backend/
├── app/
│   ├── api/v1/                # REST API endpoints (~82)
│   ├── db/models.py           # SQLModel ORM models
│   ├── schemas/               # Pydantic schemas (I/O validation)
│   ├── services/              # Business logic
│   │   ├── asset_source_providers/   # yfinance, JustETF, CSS Scraper, Scheduled Investment
│   │   ├── fx_providers/             # ECB, FED, BOE, SNB, MANUAL
│   │   └── brim_providers/           # 11 broker import plugins
│   ├── config.py              # get_data_dir(), paths, env vars
│   └── utils/                 # Shared utilities
├── alembic/                   # Database migrations (001_initial.py)
├── test_scripts/              # Full test suite (850+ tests, 8 categories)
└── data/
    ├── prod/                  # sqlite/app.db, broker_reports/, logs/
    └── test/                  # Same structure, isolated
```

## Detailed Instructions (auto-loaded by path)

| Scope | Instruction file |
|-------|-----------------|
| DB & Alembic | `backend-db.instructions.md` — models, enums, migrations, session |
| Pydantic Schemas | `backend-schemas.instructions.md` — common.py, naming, design rules |
| Asset Providers | `backend-providers-asset.instructions.md` — base class, cache, thread isolation |
| FX Providers | `backend-providers-fx.instructions.md` — central banks, MANUAL sentinel |
| BRIM Plugins | `backend-providers-brim.instructions.md` — broker import, fake asset ID flow |
| Testing | `backend-testing.instructions.md` — pytest patterns, fixtures, coverage |

## Auth

- Cookie-based sessions (JWT in HttpOnly cookie)
- Multi-worker: JWT stateless (no session store)
- First user = automatic admin
- Broker roles: Owner / Editor / Viewer

## Where to Find Things

| What | Where |
|------|-------|
| DB Models | `backend/app/db/models.py` |
| API Schemas | `backend/app/schemas/*.py` |
| Business Logic | `backend/app/services/*.py` |
| API Endpoints | `backend/app/api/v1/*.py` |
| Config & Data Paths | `backend/app/config.py` |
| FX Providers | `backend/app/services/fx_providers/` |
| Asset Providers | `backend/app/services/asset_source_providers/` |
| Broker Import | `backend/app/services/brim_providers/` |
| System & Health | `backend/app/api/v1/system.py` |
| Test Suite | `backend/test_scripts/` |
