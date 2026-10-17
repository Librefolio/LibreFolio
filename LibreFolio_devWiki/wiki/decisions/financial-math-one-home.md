---
title: "One home for financial math: every calculation in financial_math/, moved by renames first and a cut second, guarded by an AST test"
category: decision
status: resolved
date: 2026-10-12
tags: [backend, architecture, financial-math, refactor, layering, git-history, tests, guard, imports, workstream-t]
related:
  - decisions/financial-math-single-average-cost
  - decisions/utils-leaf-functions-only
  - decisions/native-cash-daily-revaluation
  - concepts/backend-only-calculations
  - entities/native-cash
  - entities/portfolio-engine
  - entities/fifo-lot-engine
  - entities/lots-analysis-service
  - entities/portfolio-service
  - sources/phase00-financial-math-home-2026-10
---

# Decision: one home for financial math

## Context

Workstream P created `backend/app/services/financial_math/` on 2026-10-07 for one function, the single average cost
([[decisions/financial-math-single-average-cost]]); the rest of the math stayed where it was. On 2026-10-11 the
developer asked to bring it all home:

- «Anzi, i vari motori matematici che abbiamo fatto, abbiamo già fatto dei lavori di fattorizzazione, quanto sarebbe
  pesante spostarli in questo modulo, aggiungere alle info salvate in .github di guardare prima e nel caso aggiungere
  lì quando serve fare le operazioni matematiche finanziarie e in generale di riguardare in tutto il progetto se sono
  comparse altre implementazioni copie parziali di quelle fattorizzate?» ("how heavy would it be to move the math
  engines we built into this module, tell the `.github` rules to look there first and add there, and search the
  whole project for partial copies?");
- «a suo tempo ricordo avevamo fatto anche backend/app/utils/financial, magari anche loro ha senso migrarle a questo
  service layer» ("we also made `backend/app/utils/financial` back then; it may make sense to move them too");
- on risk, signals and PAC: «la matematica comune deve essere ripresa dal modulo, ma per il resto vive bene dovè»
  ("the common math must come from the module, but otherwise they live well where they are").

Workstream T's inventory (plan 43 §1, at `b20eac99`) counted about 6 600 lines to move — the portfolio engine (2 837),
the FIFO engine (1 604), Yield on Cost (856), `roi_utils` (437, plus a lazy barrel of 75), `price_resolver` (298),
`valuation_utils` (26) — plus about 800 lines of pure math inside `lots_analysis_service.py`. The import surface was
small: about 27 lines in the app, 50 references in 35 test files, 5 in the test runner. One fact decided the
strategy: **the tests patch module globals** — `convert_bulk`, `scipy_newton`, `PortfolioCalculationEngine` — on the
module object they import.

## Options Considered

1. **Shims at the old paths** — rejected, for three concrete reasons: a shim that re-exports the new module makes every
   patch on a module global **mute** (the test patches the shim, the code reads the real module, and the test can pass
   on nothing); it keeps the old path alive for an old branch to re-attach code to; and two names for one module are a
   second home.
2. **Rename only, or cut the engines into sub-packages (D-2)** — cut, in two commits, the cut only while no active
   branch touches the engine, the FIFO or the lots.
3. **Test paths (D-3)** — unchanged; only their imports move. The runner encodes 163 test paths; mirroring the code
   tree is a later lot (T-TS1).
4. **The layer rule (D-4)** — amended now: the engine and Yield on Cost already read the database. Separating the
   loaders is a later lot.
5. **Guards (D-10)** — boundaries and old paths only. Pattern detectors of copies (`quote_base`, `365` outside the
   home) were rejected for their false positives.
6. **The price resolver (D-1)** — into the home, as `price_marks.py`: it is the mark rule, half of valuation.
7. **An instructions file (D-11)** — yes, `.github/instructions/financial-math.instructions.md`, auto-loaded for the
   layer.

D-1 … D-11 were approved by the developer as recommended on 2026-10-11 (plan 43 §8).

## Decision

### The home

| Module | Calculation | Came from |
|---|---|---|
| `average_cost.py` | average purchase cost (P, 2026-10-07) | — |
| `native_cash.py` | cash per broker and currency, its daily value, FX results (lot 41 F) | — |
| `returns.py` | simple ROI, TWRR, MWRR, annualization | `utils/financial/roi_utils.py` |
| `valuation.py` | value of a holding from quantity, price, quote base quantity | `utils/financial/valuation_utils.py` |
| `price_marks.py` | daily mark of an asset for valuation | `services/price_resolver.py` |
| `yield_on_cost.py` | Yield on Cost | `services/yield_on_cost.py` |
| `fifo/` — `models`, `eligibility`, `engine` | FIFO lots | `services/fifo_lot_engine.py` |
| `portfolio/` — `models`, `classifier`, `daily_state`, `derived_views`, `data_quality`, `engine` | daily portfolio state and its views | `services/portfolio_engine.py` |
| `lots/` — `prices`, `conversions`, `economic_events`, `histories`, `average_cost_lines` | lots analysis math | the pure methods of `LotsAnalysisService` |

`utils/financial/` is gone. `lots_analysis_service.py` stays as orchestration (loading, DTOs, data quality),
`fx.py` stays as FX infrastructure (`convert_bulk` is the primitive). Risk, signals and PAC ([[features/F-107]]) stay where they are and
take the common math from the layer.

### The rule (amended)

1. A calculation owns its whole problem and calls the infrastructure it needs (`fx.convert_bulk`, the base currency,
   the data-quality thresholds, the cache); it reads its own data from the database only at named points — the
   portfolio engine (with the configured FX pairs of `portfolio/data_quality.py`) and the Yield on Cost loaders.
2. Callers call the layer, never the reverse: no orchestration service, API, AI Export, risk, PAC or signals import.
3. No silent fallback: a missing rate, price or cost is reported, never a number, never the unconverted amount.
4. No re-exports: every `__init__.py` holds only its docstring; import a name from the module that defines it.
5. One implementation: search the layer first, never keep a local or partial copy, report any copy found.
6. The frontend computes none of these quantities; interactive measures are the declared exception.

### The method — renames first, the cut second

- **Commit A, `1cc9cd8f5`** ("refactor(math): move engines into financial_math"): whole files moved, imports
  rewritten in 43 files, nothing else. Git sees renames: the portfolio engine changed 12 lines in the move,
  `roi_utils` lost 9 (`ROIResult`, alive only through the deleted barrel's `__all__`).
- **Commit B, `a57a43fbd`** ("refactor(math): split engines and lots math"): the sub-modules of `fifo/`,
  `portfolio/` and `lots/`, 53 files.
- **Why the order matters**: `git log --follow backend/app/services/financial_math/portfolio/engine.py` still reaches
  the engine's first commit (`77b976ebc`, 2026-06-19, 39 commits), and a branch that touched a moved file re-applies
  on the rename. Git does not follow a file split into many: a module carved out by B, such as
  `portfolio/daily_state.py`, starts at B, and its lines are found with `git blame -C -C`. A was committed alone on
  T's branch; A and B reached `dev_release2` together in train 45 (merge `76a7b099b`).

### The guard

`test_financial_math/test_layer_boundaries.py` (270 lines, `ast` only, no app import), run by
`services financial-math`:

- **(a)** forbidden imports, one test for each of the layer's 24 files — lazy imports and `TYPE_CHECKING` imports
  count, relative imports are resolved;
- **(b)** the four `__init__.py` hold only their docstring;
- **(c)** the five old homes do not exist (a leftover `utils/financial/` holding only `__pycache__` does not count:
  git leaves that cache behind on checkouts that ran the old code);
- four control tests prove the checks can fail.

## Consequences

- **Same behaviour, proven**: `all-backend` 12 390 passed, 28 skipped, 0 failed — the base's 12 353 plus the 37 guard
  tests; the generated API client identical; ruff, black and dead code as the base, minus the barrel's two findings.
- **Cleaned on the way**: one public `normalize_fx_pair_slug` in `portfolio/data_quality.py` (two copies before, the
  service's own removed); `build_data_quality_report` a function, so the lots and the risk tests no longer build an
  empty `DerivedViewsBuilder` to call it; the PAC reads the public `QUANTITY_DUST_THRESHOLD` instead of a private
  name of `portfolio_service`; `lots_analysis_service.py` fell from 2 274 to 1 172 lines.
- **Rules and docs**: D-11 (`.github/instructions/financial-math.instructions.md`), the «Financial Math — One Home»
  table in `backend.instructions.md`, one line in `frontend.instructions.md`, the new developer page
  `developer/backend/financial_math.md` (nav between Scheduler and Risk Engine) and 13 developer pages realigned.
  The devWiki's 58 «Source files» rows were repointed in `09c089147`; the old paths left in the prose (T-W1) were
  realigned on 2026-10-12 by the step-3 ingest.
- **Left untouched on purpose**: contract identifiers that contain an old module name —
  `source_ref="portfolio_engine.PortfolioCalculationEngine"`, `Literal["portfolio_engine_market_value"]`,
  `"valuation_source": "portfolio_engine"`, `requires_lots_analysis_service` — and the historical test file names.
- **After release 1.2**: T-R1, private names across the boundary (`risk/service.py` calls
  `PortfolioService._get_configured_fx_pair_sets()`; `portfolio_service` imports `_compute_tx_fingerprint` from the
  engine; *2026-10-16, CP-9a:* the risk half is closed, `risk/data_quality.py` reads the routes with
  `load_configured_fx_pair_sets(db)` from the home); a further cut of `DailyStateBuilder` (`daily_state.py`, about 1 250 lines); the test tree mirror (T-TS1).
- *2026-10-17, CP-14a (U10, D-8):* the day count conventions and simple interest of the Scheduled Investment provider
  moved into the home, `financial_math/interest.py`; guard rule (e) of `test_layer_boundaries.py` keeps them defined
  there once. P-10 (decision 27) added `costless_incoming_split_adjustments` to `splits.py`: the event store asks it
  before letting a SPLIT change type, and never names the SPLIT type itself (guard (d)).
- The same layering question for `utils/` was answered the next day: [[decisions/utils-leaf-functions-only]].

## Links

- [[decisions/financial-math-single-average-cost]] — the layer's first function and first rule
- [[decisions/utils-leaf-functions-only]] — D-P7: what stays in `utils/`
- [[concepts/backend-only-calculations]] — the frontend side of the same rule
- [[entities/portfolio-engine]], [[entities/fifo-lot-engine]], [[entities/lots-analysis-service]],
  [[entities/native-cash]] — the moved and the new modules
- Source: [[sources/phase00-financial-math-home-2026-10]]

## Source files

| Role | Path |
|------|------|
| Layer docstring (rule and module map) | `backend/app/services/financial_math/__init__.py` |
| Portfolio engine package | `backend/app/services/financial_math/portfolio/engine.py`, `backend/app/services/financial_math/portfolio/daily_state.py` |
| FIFO package | `backend/app/services/financial_math/fifo/engine.py` |
| Lots math package | `backend/app/services/financial_math/lots/histories.py` |
| Returns, valuation, price marks | `backend/app/services/financial_math/returns.py`, `backend/app/services/financial_math/valuation.py`, `backend/app/services/financial_math/price_marks.py` |
| Day count and simple interest (U10) | `backend/app/services/financial_math/interest.py` |
| The guard | `backend/test_scripts/test_services/test_financial_math/test_layer_boundaries.py` |
| Rules of the layer (D-11) | `.github/instructions/financial-math.instructions.md` |
| Map of where each calculation lives | `.github/instructions/backend.instructions.md` |
| Developer guide | `mkdocs_src/docs/developer/backend/financial_math.md` |
| Runner entry `services financial-math` | `scripts/test_runner/_backend_services.py` |
| Plan (§1, §3, §4, §8, §10 T-1) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
