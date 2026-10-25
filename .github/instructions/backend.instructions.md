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
│   │   ├── platform/                 # app startup/shutdown steps, middleware stack, static site, DB bootstrap; scheduler, container registry, date sentinels, data-quality thresholds, per-series exports, instance backup, instance key, config checks, readiness, provider pauses
│   │   ├── files/                    # uploaded static files and their previews
│   │   ├── email/                    # optional SMTP email: config checks, transport, budget, templates
│   │   ├── asset_source_providers/   # yfinance, JustETF, CSS Scraper, Scheduled Investment
│   │   ├── fx_providers/             # ECB, FED, BOE, SNB, MANUAL
│   │   └── brim_providers/           # 11 broker import plugins
│   ├── config/                # env vars, paths, get_data_dir(): the only place that reads os.environ
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
- The first account of an instance without accounts is an administrator (registration, in any mode); with
  `LIBREFOLIO_ADMIN_EMAIL` (F02) that administrator is created at startup instead, and activates through a
  single-use `/setup` link (`services/accounts/bootstrap_admin_service.py`)
- Broker roles: Owner / Editor / Viewer

## Financial Math — One Home

Every financial calculation — purchase cost, P&L, capital, NAV, returns, FX valuation, yields — has exactly one
implementation. Its home is `backend/app/services/financial_math/` (developer decision, 2026-10-11). The rules of the
layer — its boundaries, imports and guards — are in `financial-math.instructions.md`, auto-loaded for that folder.

1. **Search before writing.** Before computing anything financial, look in `financial_math/` and in the table below. If
   the calculation exists, call it — with parameters when your case differs — instead of deriving it again.
2. **Add there.** A new calculation goes into `financial_math/`, next to the ones it relates to, with its unit tests.
3. **No local or partial copies.** A loop over transactions that recomputes cost, capital, NAV or P&L outside these
   engines is a defect, even when it serves a single card or export: read the engine's output instead.
4. **Report copies.** Report any copy you meet, old or new, to the coordinator (backlog 38 or the consolidation lot).
   Before closing work that touched financial math, search the project for copies of what you changed.

| Calculation | Where it lives |
|---|---|
| Average purchase cost (WAC), cost-basis steps and conversions | `services/financial_math/average_cost.py` |
| Cash per broker and currency, its daily value, FX results on cash | `services/financial_math/native_cash.py` |
| Control totals of the ledger (backup manifest, restore check) | `services/financial_math/ledger_totals.py` |
| Daily portfolio state: NAV, capital baseline, P&L, per-broker contributions | `services/financial_math/portfolio/` (`daily_state.py`, run by `engine.py`) |
| A period's boundary states, P&L and identity; the day's change of the total P&L | `services/financial_math/portfolio/period.py` |
| A position's period contribution (Performance table): the transfer split between brokers, return on the start value, annualized window, closed positions | `services/financial_math/portfolio/contributions.py` |
| FIFO lots and realized gains | `services/financial_math/fifo/` |
| Lots analysis: lot summary and histories, economic events, average cost lines, transfers at the scope's edge | `services/financial_math/lots/` |
| Simple ROI, TWRR, MWRR (and the Dashboard's MWRR rule for card and line), annualization, a period's start (rebasing), net holding return, G/L ratio (of a holding or a group), a change as a fraction of its base, the timing effect, realized gain, price return (also as a float for a return series), the observed annualization factor of a return series (`DAYS_PER_YEAR`, its validator, and both conversions between calendar days and observations), the fixed-period changes of a price or rate (1D … 5Y, both orientations), the gain that recovers a drawdown | `services/financial_math/returns.py` |
| Holding value from quantity and price | `services/financial_math/valuation.py` |
| The amount of a trade from its unit price, and the unit price from its amount (the transaction form) | `services/financial_math/trade_amount.py` |
| The orientation of a stored FX rate (a pair read from source to destination, either way); the unit rates a calculation reads by day, kept as steps and answered on the asked days only (`AskedDayRates`, P3) | `services/financial_math/fx_rates.py` |
| Day count conventions (ACT/365, ACT/360, ACT/ACT, 30/360), simple interest, daily compounding over a span in closed form | `services/financial_math/interest.py` |
| Daily price mark of an asset for valuation | `services/financial_math/price_marks.py` |
| Yield on Cost | `services/financial_math/yield_on_cost.py` |
| Stock splits linked to the ledger: their rows, the usable ratio, and the incoming adjustments without a cost a SPLIT may not lose by a retype | `services/financial_math/splits.py` |
| Weights and concentration: a share of a total, allocation slices, gross weights, largest weight and Herfindahl index | `services/financial_math/weights.py` |
| Holding window of a position: oldest lot still open, a closed position's flight time | `services/financial_math/holding_window.py` |
| FX conversion | `services/fx/conversion.py` (`convert_bulk`) |
| Technical indicators | `services/signal_plugins/` (the plugins), `services/signals/` (runtime, contract, registry) |
| Risk metrics and optimization | `services/risk/quant/` |
| PAC allocation | `services/pac_allocator/` |

Risk, signals and PAC stay where they are, but take the common math — returns, annualization, conversions, average
cost, valuation — from `financial_math/`. The frontend computes none of these (`.github/copilot-instructions.md`,
decision 1).

`utils/` holds leaf functions only: they never import services; anything that needs FX, assets or other services
belongs to a service layer, such as `financial_math/` (developer decision D-P7, 2026-10-12). Its folders group them by
type: `utils/asset/` (sectors, geographic areas, identifiers, display-name locale), `utils/fx/` (currencies),
`utils/runtime/` (version, client network address, TTL caches, sliding-window rate limits in `rate_window.py`, pauses
after a remote's «too many requests» in `cooldown.py`, the causes of an exception and the «reported» mark in
`errors.py`); `datetime_utils`, `json_utils` and `decimal_utils` stay
at the root. The truncation to the database precision reads the models, so it lives in `db/precision.py`.

## Errors: never lose the cause

The developer's rule (19/10/2026): when something fails, the useful information is printed, in the server log and in
the browser console (lot H-60).

- **A broad `except` that turns a failure into a fallback, a result field or an HTTP error logs it once, where it is
  caught**: `logger.warning(...)` or `logger.error(...)` with `exc_info=exc` and the identifiers of what failed (ids,
  codes, component), never personal data, addresses or secrets. A caught exception that only becomes `str(exc)` in a
  response is lost to the log, and the text of an internal error never goes to the client.
- **Keep the chain**: `raise NewError(...) from exc`. A wrapper that stores its cause sets `__cause__`, or carries it
  in a `cause` attribute (`utils/runtime/errors.py` reads both).
- **The client gets a code, never a message or a stack.** Every response carries `X-Request-Id`, and every log line of
  the request carries `request_id` (`services/platform/request_id.py`). A 5xx body adds `request_id` and `error_type`,
  the class name of the root cause, to its `detail` (`api/server_errors.py`, `services/platform/failure_report.py`); a
  closed `reason_code` says more when the client can act on it. The message, the type and the traceback go to the log.
- **The safety net, not a second line.** A warning or a higher line written with an exception, or inside the `except`
  that handles it, marks it as reported for the request the line carries (`logging_config.LibreFolioBoundLogger`): the
  5xx handler then writes nothing more for that request. Otherwise it writes the failure once: an error line with the
  traceback of a cause nobody logged, a warning line for a 5xx raised without a cause. One exception object can reach
  several requests (a single-flight build hands its failure to every request waiting on it): a request whose failure
  another request logged already gets a short warning, «Request failed with an error already logged», with its own
  `request_id` and `logged_with_request_id`, never the traceback again (H-60r). An exception that leaves the app is
  answered by `security_headers.py` and logged there, once per request; uvicorn's own line for it is dropped.
- **A failure handed to several consumers is written with its traceback once**: a memoized failure, a single-flight
  build. Before writing `exc_info=error`, ask `traceback_reported(error)` (`utils/runtime/errors.py`); when a line
  carried it already, write the consumer's line without `exc_info`, naming `logged_with_request_id`
  (`traceback_reporting_request(error)`), as the AI Export `BuildContext._build` does.
- **`logger.exception()` writes one JSON line at `ERROR`, its traceback inside it.** The log stays JSON (developer
  decision D1): the message is the `event` key.
- **Catch what you expect.** A broad `except Exception` is an isolation boundary and says so in a comment. A parsing
  probe whose failure *is* the answer («is this a date?») may return without logging, and says so too.

## Where to Find Things

| What | Where |
|------|-------|
| DB Models | `backend/app/db/models.py` |
| API Schemas | `backend/app/schemas/*.py` |
| Business Logic | `backend/app/services/*.py` |
| App startup and shutdown: one line per step (`STARTUP_STEPS`, `SHUTDOWN_STEPS`), run by `lifecycle.py`; middleware, outermost first (`MIDDLEWARE_STACK`); MkDocs and SPA serving; DB create/migrate at startup. `main.py` only wires them | `backend/app/services/platform/app_lifespan.py`, `lifecycle.py`, `middleware.py`, `static_site.py`, `database_bootstrap.py` |
| Errors (H-60): the request id of every request, the body and the log line of a 5xx, the causes of an exception and its «reported» mark | `backend/app/services/platform/request_id.py`, `failure_report.py`, `backend/app/api/server_errors.py`, `backend/app/utils/runtime/errors.py` |
| Platform services (scheduler, data-quality thresholds, per-series exports `series_export.py`, instance backup `instance_backup/`, instance key `derive_key()`, startup config checks, readiness `/system/ready`, provider pauses after HTTP 429 `provider_cooldown.py`, shutdown budget `shutdown_budget.py`, sleep and wake `sleep_wake/`: the user's activity and the work in progress) | `backend/app/services/platform/` |
| Uploads and file previews | `backend/app/services/files/` |
| Email (optional SMTP: transport, hourly budget, templates in 4 languages, config checks) | `backend/app/services/email/` (config in `backend/app/config/email.py`; sliding-window limiter in `backend/app/utils/runtime/rate_window.py`) |
| API Endpoints | `backend/app/api/v1/*.py` |
| Config & Data Paths | `backend/app/config/` (base in `__init__.py`, one module per owner section; env vars are read only here; secrets through `env_secret()`, which also reads `NAME_FILE`; every variable documented in `.env.example`, new lines commented; a new security `Settings` field states its `managed` value in `PROFILE_DEFAULTS` in the same lot, or why `managed` keeps the code default (H-39)) |
| FX Providers | `backend/app/services/fx_providers/` |
| Asset Providers | `backend/app/services/asset_source_providers/` |
| Broker Import | `backend/app/services/brim_providers/` |
| System & Health | `backend/app/api/v1/system/` (one module per resource) |
| Test Suite | `backend/test_scripts/` |
