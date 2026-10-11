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
| Technical Signals | `backend-signals.instructions.md` — plugins, runtime, status and data policy |
| Risk Engine | `backend-risk.instructions.md` — analytics, DB-free context, workers, i18n keys |
| Tool Platform | `backend-tools.instructions.md` — Pydantic contracts, isolated jobs, registry |
| Testing | `backend-testing.instructions.md` — pytest patterns, fixtures, coverage |
| Lint & Format | skill `lint-format-backend` — ruff + black, rules, workflow |
| Dead code | skill `lint-format-backend` — `./dev.py lint --dead-code` (vulture), test-only detection |

## Auth

- Cookie-based sessions (JWT in HttpOnly cookie)
- Multi-worker: JWT stateless (no session store)
- First user = automatic admin
- Broker roles: Owner / Editor / Viewer

## Financial Math — One Home

Every financial calculation — purchase cost, P&L, capital, NAV, returns, FX valuation, yields — has exactly one
implementation. Its home is `backend/app/services/financial_math/` (developer decision, 2026-10-11). Some engines still
live in their historical modules until they are moved there: the table says where each calculation is today.

1. **Search before writing.** Before computing anything financial, look in `financial_math/` and in the table below. If
   the calculation exists, call it — with parameters when your case differs — instead of deriving it again.
2. **Add there.** A new calculation goes into `financial_math/`, next to the ones it relates to, with its unit tests.
3. **No local or partial copies.** A loop over transactions that recomputes cost, capital, NAV or P&L outside these
   engines is a defect, even when it serves a single card or export: read the engine's output instead.
4. **Report copies.** Report any copy you meet, old or new, to the coordinator (backlog 38 or the consolidation lot).
   Before closing work that touched financial math, search the project for copies of what you changed.

| Calculation | Where it lives today |
|---|---|
| Average purchase cost (WAC), cost-basis steps and conversions | `services/financial_math/average_cost.py` |
| Daily portfolio state: NAV, capital baseline, P&L, per-broker contributions | `services/portfolio_engine.py` |
| FIFO lots and realized gains | `services/fifo_lot_engine.py` |
| Simple ROI, TWRR, MWRR, annualization | `utils/financial/roi_utils.py` |
| Holding value from quantity and price | `utils/financial/valuation_utils.py` |
| Yield on Cost | `services/yield_on_cost.py` |
| FX conversion | `services/fx.py` (`convert_bulk`) |
| Technical indicators | `services/signal_plugins/`, `services/signal_runtime.py` |
| Risk metrics and optimization | `services/risk/quant/` |
| PAC allocation | `services/pac_allocator/` |

The frontend computes none of these (`.github/copilot-instructions.md`, decision 1).

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
