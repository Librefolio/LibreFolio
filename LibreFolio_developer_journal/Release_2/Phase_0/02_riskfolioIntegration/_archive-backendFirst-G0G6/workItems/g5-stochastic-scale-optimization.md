# G5 — Stochastic risk, scale, and optimization

← [Indice work item](./README.md)

**P-map**: P11-P13
**Stato gate**: ✅ completato e corretto
**Work item**: 10

## `risk-stochastic-backend`

**Titolo**: Implementing stochastic risk engines
**Stato**: `done`
**Dipende da**: `risk-multiasset-backend`
**Creato**: 2026-07-27 09:58:43
**Aggiornato**: 2026-07-28 14:08:36

Completed corrected P11-P13: QuantLib MC/QMC, persistent spawn pools,
deterministic content cache, P12 benchmark, and Riskfolio-Lib 7.0.1
optimization; RQMC removed.

## `risk5-spike`

**Titolo**: Gating quantitative dependencies
**Stato**: `done`
**Dipende da**: —
**Creato**: 2026-07-27 14:11:56
**Aggiornato**: 2026-07-28 12:00:27

Probe Riskfolio-Lib 7.0.1 on Python 3.13 with NumPy 2.5.1 on host and Docker
arm64/amd64. Verify required optimization APIs, open-source solvers, licenses,
repeatability, RSS/image cost, and absence of vectorbt. Stop without fallback
if the gate fails. Gate passed: Riskfolio-Lib 7.0.1 runs on Python 3.13 with
NumPy 2.5.1 on host/Linux arm64/amd64; CLARABEL, strategies, covariance
estimators, bounds, frontier and infeasible handling passed; vectorbt/numba
absent.

## `risk5-contracts`

**Titolo**: Defining quant worker contracts
**Stato**: `done`
**Dipende da**: `risk5-spike`
**Creato**: 2026-07-27 14:11:56
**Aggiornato**: 2026-07-28 12:19:28

Revise simulation contracts for MC/QMC only and define serializable
spawned-worker plus portfolio-optimization request/result DTOs, cache keys,
errors, timeout semantics, and strict validators.

## `risk5-workers`

**Titolo**: Building spawned worker isolation
**Stato**: `done`
**Dipende da**: `risk5-spike`
**Creato**: 2026-07-28 10:50:26
**Aggiornato**: 2026-07-28 12:19:42

Implement separate lazy persistent spawn pools for simulation and optimization
with bounded queues, configurable workers, hard timeouts, lane recycling,
explicit child errors, metrics, and clean FastAPI shutdown.

## `risk5-adapter`

**Titolo**: Implementing QuantLib simulation
**Stato**: `done`
**Dipende da**: `risk5-contracts`, `risk5-workers`
**Creato**: 2026-07-27 14:11:56
**Aggiornato**: 2026-07-28 12:33:00

Replace the production NumPy/SciPy adapter with QuantLib MC/QMC GBM running in
a lazy spawned simulation worker. Remove RQMC and keep NumPy only for
aggregation/reference tests.

## `risk5-optimization`

**Titolo**: Implementing Riskfolio optimization
**Stato**: `done`
**Dipende da**: `risk5-contracts`, `risk5-workers`
**Creato**: 2026-07-28 10:50:26
**Aggiornato**: 2026-07-28 12:33:00

Add backend-only portfolio_optimization for portfolio, broker, and asset-set
scopes using Riskfolio 7.0.1: min-risk, max-Sharpe, risk parity, covariance
estimators, bounds, optional frontier/sensitivity, and explicit infeasibility.

## `risk5-service`

**Titolo**: Integrating quant analytics
**Stato**: `done`
**Dipende da**: `risk5-adapter`, `risk5-optimization`
**Creato**: 2026-07-27 14:11:56
**Aggiornato**: 2026-07-28 12:51:06

Add the async analytic execution boundary, simulation and
portfolio_optimization catalog/API integration, error isolation, lifespan
shutdown, API tests, client regeneration, and minimal frontend compatibility
edits.

## `risk5-benchmark`

**Titolo**: Benchmarking spawned quant workers
**Stato**: `done`
**Dipende da**: `risk5-service`
**Creato**: 2026-07-27 14:11:56
**Aggiornato**: 2026-07-28 12:51:06

Measure cold/warm worker startup, queue wait, RNG, evolution, aggregation,
serialization, cache, RSS, timeout recycle, and sequential/concurrent scaling
for QuantLib and Riskfolio pools.

## `risk5-verify`

**Titolo**: Verifying corrected quant backend
**Stato**: `done`
**Dipende da**: `risk5-benchmark`, `risk5-service`
**Creato**: 2026-07-28 10:50:26
**Aggiornato**: 2026-07-28 14:08:36

Completed analytical moments/covariance/QMC convergence, optimization
invariants, failure/recycle tests, risk/API suites, lock, Docker, API sync, and
compatibility checks.

## `risk5-decision`

**Titolo**: Finalizing corrected Gate G5
**Stato**: `done`
**Dipende da**: `risk5-verify`
**Creato**: 2026-07-27 14:11:56
**Aggiornato**: 2026-07-28 14:08:36

Completed corrected G5 decisions, evidence, final recap, devWiki filing, graph
update, and backend stop gate.
