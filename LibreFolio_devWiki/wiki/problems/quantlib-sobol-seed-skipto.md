---
title: "QuantLib Sobol seed did not select the expected stream position"
category: problem
status: resolved
date: 2026-07-28
tags: [backend, risk, quantlib, sobol, qmc, reproducibility]
related:
  - decisions/risk-quant-engine-process-boundary
  - sources/phase00-risk-analysis-backend
---

# Problem: QuantLib Sobol seed did not select the expected stream position

## Symptom

Passing different values through the QuantLib Sobol constructor did not provide
the intended LibreFolio contract of selecting a deterministic starting point in
one native Sobol sequence. A request `seed` could therefore be repeatable without
meaningfully representing the requested sequence offset.

## Root Cause

The constructor's seed argument is not a direct replacement for advancing the
generated Sobol stream. LibreFolio's API semantics require a start index, not an
opaque generator initialization parameter.

## Solution

QMC now constructs the native `SobolRsg` and calls `skipTo(seed)` before QuantLib
Gaussianization and `StochasticProcessArray.evolve`. The API documents QMC seed
as a Sobol start index. Tests cover same-seed repeatability, different-seed
results, direct/worker identity, powers-of-two path counts, convergence, and the
QuantLib dimension limit.

## Prevention

- Define QMC seed semantics explicitly before wiring a library constructor.
- Test that two seeds alter the actual generated result, not only metadata.
- Keep direct and spawned-worker output identity tests.
- Use convergence across powers of two rather than a single arbitrary
  correlation cutoff.

## Source files

| Role | Path |
|------|------|
| QuantLib QMC implementation | `backend/app/services/risk/quant/quantlib_worker.py` |
| API contracts | `backend/app/schemas/risk.py` |
| Mathematical tests | `backend/test_scripts/test_services/test_risk_simulation.py` |
| Probe | `scripts/spikes/risk/run_simulation_adapter_probe.py` |
