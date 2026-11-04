---
applyTo: "backend/app/services/risk/**,backend/app/services/risk_plugins/**,backend/app/services/market_series.py"
---

# Risk Engine (backend)

## Architecture

- **Analytics**: one folder per analytic, `services/risk_plugins/<code>/` (`__init__.py` with the docstring only,
  `plugin.py` with the code, `i18n/` with its `risk.analytics.<id>.*` texts), extending `RiskAnalytic`
  (`services/risk/base.py`) and registered with `@register_plugin(RiskAnalyticRegistry)` (`services/risk/registry.py`; the decorator is in
  `services/provider_registry.py`).
  Import and patch from `….risk_plugins.<code>.plugin`. The `risk.warnings.*` vocabulary stays in the `risk` subsystem of
  the catalogue (`frontend/src/lib/i18n/risk/`), shared by every analytic.
- **Runtime**: `risk/service.py` (`RiskService`) orchestrates a request. `risk/scope.py` resolves the scope and prepares
  the series, `risk/replay.py` prepares a historical replay, `risk/results.py` applies the observation gate and builds
  the results, and `risk/data_quality.py` builds their data quality; `risk/plan.py` holds the plan and its predicates.
  `risk/eligibility.py` reads each asset's quotes; `risk/analytic_helpers.py` reads the prepared context; `risk/metrics.py`
  holds the series statistics; `risk/quant/` holds the simulation and optimization workers.
- **API**: `api/v1/risk.py` (`GET /catalog` and the bulk query). The frontend asks for analytics through
  `buildBaseAnalytics()` and on-demand runs (`frontend/src/lib/features/risk/`).

## Rules

- An analytic receives validated parameters and a DB-free `RiskExecutionContext`: it never opens a session or fetches
  prices.
- The declaration is validated at import: canonical lowercase `analytic_code`, `algorithm_version`, i18n keys, output
  kind, scopes and modes, `params_model` with `extra="forbid"`, `min_observations`, `series_inputs`.
- Refuse with `RiskUnavailableError` and a `RiskErrorCode`; an undefined value is `None` plus a warning, never a zero.
- Statistical analytics use `min_observations = RISK_MIN_OBSERVATIONS`, never a literal.
- QuantLib, Riskfolio-Lib and long CPU work run in the spawn worker pools through an overridden `execute()`; never
  import those libraries in the web process.
- Names, descriptions and warnings are i18n keys in the four frontend catalogues, with an English `message` for logs.
- Bump `algorithm_version` whenever the values change: results and worker caches key on it.
- The risk service still keys a few decisions on `analytic_code` (`available_observations()` and
  `requires_valid_composition()` in `risk/results.py`, the `stress` branches): review them for a new analytic.
- Series statistics stay in `risk/metrics.py`. Returns, annualization, FX conversion, average cost and valuation come
  from their one home, `services/financial_math/` and the map in `backend.instructions.md`, never from a local copy.

## Adding an Analytic

Read the skill `risk-plugin` and `mkdocs_src/docs/developer/backend/risk/architecture.md`, sections "The Plugin Contract"
and "Adding a Risk Analytic", with its test map.

## Testing

`./dev.py test services risk-all`, `./dev.py test schemas risk`, `./dev.py test api risk`; the simulation, optimization
and worker suites are separate actions (`services risk-simulation`, `risk-optimization`, `risk-workers`).
