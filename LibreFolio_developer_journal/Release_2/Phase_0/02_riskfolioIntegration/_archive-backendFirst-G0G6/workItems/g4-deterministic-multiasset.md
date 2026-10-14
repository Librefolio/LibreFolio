# G4 — Deterministic multi-asset risk

← [Indice work item](./README.md)

**P-map**: P5-P10 backend/API
**Stato gate**: ✅ completato
**Work item**: 13

## `risk-multiasset-backend`

**Titolo**: Implementing deterministic multi-asset risk
**Stato**: `done`
**Dipende da**: `risk-rolling-backend`
**Creato**: 2026-07-27 09:58:43
**Aggiornato**: 2026-07-27 14:11:44

Execute P5 plus backend P6-P10: RiskAnalytic registry/service/API, portfolio
KPIs, correlation, PCTR, stress, comparison, VaR/CVaR, metadata, quality, auth,
and OpenAPI tests.

## `risk4-schemas`

**Titolo**: Defining risk API schemas
**Stato**: `done`
**Dipende da**: —
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:09:34

Implement strict DTOs/enums/discriminated scope union/catalog/query/results in
backend/app/schemas/risk.py; no persistence.

## `risk4-registry`

**Titolo**: Creating RiskAnalytic registry
**Stato**: `done`
**Dipende da**: `risk4-schemas`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:11:59

Add pure self-describing RiskAnalytic base, registry/discovery, and catalog
contracts under backend/app/services/risk_plugins/.

## `risk4-math`

**Titolo**: Implementing deterministic risk math
**Stato**: `done`
**Dipende da**: `risk4-schemas`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:16:37

Extend pure backend risk metrics for portfolio KPI, correlation/covariance,
PCTR, stress, comparison, and historical VaR/CVaR with hand-derived tests.

## `risk4-correlation`

**Titolo**: Adding correlation analytic
**Stato**: `done`
**Dipende da**: `risk4-math`, `risk4-registry`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:22:12

Pearson matrix with one joint calendar plus per-cell n_obs/coverage and
insufficient state.

## `risk4-kpi`

**Titolo**: Adding portfolio KPI analytic
**Stato**: `done`
**Dipende da**: `risk4-math`, `risk4-registry`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:22:12

Historical TWRR volatility, max drawdown/duration, Sharpe, Sortino.

## `risk4-pctr`

**Titolo**: Adding risk contribution analytic
**Stato**: `done`
**Dipende da**: `risk4-correlation`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:22:12

MCTR/CCTR/PCTR on common covariance, current target-currency weights, negative
contributions preserved, cash/zero-vol handled.

## `risk4-stress`

**Titolo**: Adding stress analytics
**Stato**: `done`
**Dipende da**: `risk4-math`, `risk4-registry`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:22:12

Hypothetical deterministic shocks and historical replay
current_buy_and_hold; factor shock excluded.

## `risk4-comparison`

**Titolo**: Adding comparison analytics
**Stato**: `done`
**Dipende da**: `risk4-correlation`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:22:12

Separate risk-free and real comparison contracts; active return, TE, IR,
correlation, beta, cumulative and drawdown comparison.

## `risk4-var`

**Titolo**: Adding historical VaR CVaR
**Stato**: `done`
**Dipende da**: `risk4-math`, `risk4-registry`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:22:12

Historical simulation with positive loss magnitudes, explicit
confidence/horizon and compounded multi-day returns.

## `risk4-service`

**Titolo**: Building bulk RiskService
**Stato**: `done`
**Dipende da**: `risk4-math`, `risk4-registry`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:32:11

Authorize scopes, load each data source once, prepare one joint calendar,
resolve historical TWRR/current weights, execute multiple analytics with
per-result error isolation.

## `risk4-api`

**Titolo**: Adding risk API
**Stato**: `done`
**Dipende da**: `risk4-service`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 13:33:44

Add GET /api/v1/risk/catalog and POST /api/v1/risk/query, router wiring, auth,
OpenAPI, and API tests.

## `risk4-verify`

**Titolo**: Verifying Gate G4
**Stato**: `done`
**Dipende da**: `risk4-api`, `risk4-comparison`, `risk4-correlation`,
`risk4-kpi`, `risk4-pctr`, `risk4-stress`, `risk4-var`
**Creato**: 2026-07-27 13:01:45
**Aggiornato**: 2026-07-27 14:11:44

Run targeted/full backend tests, lint/format, API sync stability, update
plans/recap/wiki/graph after G4.
