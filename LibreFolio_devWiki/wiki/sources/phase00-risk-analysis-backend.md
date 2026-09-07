---
title: "Phase 0 — Risk Analysis backend G0-G5"
category: source
source_type: plan
date_ingested: 2026-07-28
original_path: LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01RiskAnalysisImplementation.prompt.md
tags: [phase0, backend, risk, quantlib, riskfolio, simulation, optimization]
related:
  - decisions/risk-quant-engine-process-boundary
  - concepts/cancellation-safe-inflight-deduplication
  - problems/quantlib-sobol-seed-skipto
  - problems/spawn-worker-response-queue-semaphore-leak
  - problems/riskfolio-numpy-vectorbt-dependency-trap
  - problems/risk-spawn-worker-idle-residency
  - decisions/signal-backend-plugin-architecture
  - concepts/backend-only-calculations
---

# Source: Phase 0 — Risk Analysis backend G0-G5

## Summary

The completed G0-G5 backend chain establishes canonical risk series and metadata,
rolling risk plugins, deterministic multi-asset analytics, QuantLib MC/QMC
simulation, and Riskfolio portfolio optimization. The final correction replaces
an in-process NumPy/SciPy design with isolated `spawn` workers and motivated
mathematical oracles. The audit then makes MC/QMC sequence controls explicit and
adds idle reap with lazy restart. Simulation and optimization expose serializable
service/API contracts, independent content caches, bounded resources, timeout
recovery, and separate failure domains. G6 is reconciled into a new plan but not
implemented.

## Key Takeaways

- Backend remains the sole owner of financial math; frontend consumes typed
  results.
- Rolling asset risk uses `SignalPlugin`; portfolio/multi-asset work uses
  `RiskAnalytic`.
- QuantLib 1.43 owns production GBM path generation/evolution for MC and QMC.
- MC uses `random_seed`; QMC uses
  `SobolRsg.skipTo(sobol_start_index)`. The controls are mutually exclusive, path
  count is a power of two, and native Sobol dimension is bounded at 21,201.
- Riskfolio-Lib 7.0.1 owns minimum-variance, maximum-Sharpe, and risk-parity
  optimization with historical/Ledoit-Wolf/OAS covariance.
- Process isolation is mandatory; P12 benchmark tunes worker count rather than
  deciding whether processes are used.
- Default is one simulation and one optimization worker; more workers trade
  repeatable speedup for approximately linear RSS.
- Pools retain warm workers during bursts, reap every lane after a configurable
  idle timeout, and restart lazily without interrupting queued/in-flight work.
- Mathematical gates use analytical GBM moments, covariance standard errors,
  Fisher-z correlation error, and QMC convergence instead of arbitrary cutoffs.
- No DB migration was required.
- Backend G0-G5 is complete and audited; G6 UI integration and final integrated
  closure remain.

## Final focused validation

| Gate | Result |
|------|--------|
| Risk service tests | 74 passed |
| Risk API tests | 7 passed |
| Risk schema tests | 21 passed |
| Spawn-worker lifecycle tests | 11 passed |
| Frontend format/check/build | Green |
| Mocked desktop Risk E2E | 5 passed |
| Docker arm64 | Build and import smoke green |

These results close the backend audit/remediation scope only. G6 was reconciled
into its frontend plan and was not implemented.

## Wiki Pages Updated

- [[decisions/risk-quant-engine-process-boundary]] — production engine and process
  architecture.
- [[concepts/cancellation-safe-inflight-deduplication]] — shared cache cancellation
  safety.
- [[problems/quantlib-sobol-seed-skipto]] — native QMC seed semantics.
- [[problems/spawn-worker-response-queue-semaphore-leak]] — crash-safe response IPC.
- [[problems/riskfolio-numpy-vectorbt-dependency-trap]] — exact-version dependency
  resolution.
- [[problems/risk-spawn-worker-idle-residency]] — safe idle reap and lazy restart.

## Source files

| Role | Path |
|------|------|
| Final recap | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/_RECAP-and-implementation-reading-guide.md` |
| Mathematical contract | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/contract-phase01RiskMetricsMathematical.md` |
| Master implementation plan | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01RiskAnalysisImplementation.prompt.md` |
| Corrected G5 plan | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01Step5SimulationScaleOptimization.prompt.md` |
| Quantitative library spike | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/spike-phase01QuantLibraries.md` |
| Simulation oracle report | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/spike-phase01SimulationAdapters.md` |
| Production benchmark | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/benchmark-phase01SimulationScale.md` |
| Audit/remediation report | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/report-phase01RiskBackendAuditAndRemediation.md` |
| Reconciled G6 plan | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01Step6RiskFrontendIntegration.prompt.md` |
| Risk service | `backend/app/services/risk/` |
| Risk plugins | `backend/app/services/risk_plugins/` |
| Risk API schemas | `backend/app/schemas/risk.py` |
| Risk tests | `backend/test_scripts/test_services/test_risk_*.py`, `backend/test_scripts/test_api/test_risk_api.py` |
