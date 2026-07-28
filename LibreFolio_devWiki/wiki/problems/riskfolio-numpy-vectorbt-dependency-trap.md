---
title: "Riskfolio upgrade conflicted with LibreFolio's NumPy baseline"
category: problem
status: resolved
date: 2026-07-28
tags: [backend, riskfolio, numpy, vectorbt, numba, dependencies, python313]
related:
  - decisions/risk-quant-engine-process-boundary
  - sources/phase00-risk-analysis-backend
---

# Problem: Riskfolio upgrade conflicted with LibreFolio's NumPy baseline

## Symptom

Riskfolio-Lib 7.3.0 introduced
`vectorbt → numba`, whose constraints conflicted with LibreFolio's required
NumPy 2.5.1 baseline. Treating that conflict as proof that Riskfolio itself was
unusable would have incorrectly removed P13.

## Root Cause

The rejected closure was version-specific, not a universal Riskfolio
requirement. The needed LibreFolio capabilities had not first been tested against
the exact historical Riskfolio release already compatible with the desired
Python/NumPy stack.

## Solution

Riskfolio-Lib 7.0.1 was probed and locked with Python 3.13 and NumPy 2.5.1.
Minimum variance, maximum Sharpe, equal risk contribution, covariance estimators,
bounds, frontier generation, CLARABEL, and SCS all passed. Neither `vectorbt` nor
`numba` is present in the final dependency graph. A later clean probe explicitly
retested 7.3.0 with pip, Pipenv, and Docker: all paths preserving NumPy 2.5.1 fail
because Numba 0.66 requires `numpy<2.5`. The exact 7.0.1 pin is therefore a current
compatibility decision, not merely an assumption inherited from the first probe.

## Prevention

- Diagnose dependency conflicts against exact versions and required capabilities.
- Do not infer a package-wide incompatibility from the latest release's optional
  or transitive closure.
- Probe imports, solvers, mathematical outputs, Docker architectures, and lock
  reproducibility before accepting or rejecting a quantitative library.
- Never silently downgrade NumPy or replace the requested engine.

## Impact

P13 portfolio optimization remains available without weakening LibreFolio's NumPy
baseline or adding vectorbt/Numba to production. The exact 7.0.1 pin is intentional
and must not be upgraded without repeating the capability and dependency probes.

## Source files

| Role | Path |
|------|------|
| Dependency manifests | `Pipfile`, `Pipfile.lock` |
| Riskfolio production engine | `backend/app/services/risk/quant/riskfolio_worker.py` |
| Optimization tests | `backend/test_scripts/test_services/test_risk_optimization.py` |
| Library evidence | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/spike-phase01QuantLibraries.md` |
| Docker probe | `scripts/spikes/risk/Dockerfile.riskfolio` |
