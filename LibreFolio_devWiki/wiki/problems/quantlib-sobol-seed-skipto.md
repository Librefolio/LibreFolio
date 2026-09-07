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
meaningfully representing the requested sequence offset. The shared field name
also conflated MC pseudo-random seeding with QMC sequence positioning.

## Root Cause

The constructor's seed argument is not a direct replacement for advancing the
generated Sobol stream. LibreFolio's API semantics require a start index, not an
opaque generator initialization parameter.

## Solution

QMC now constructs the native `SobolRsg` and calls
`skipTo(sobol_start_index)` before QuantLib Gaussianization and
`StochasticProcessArray.evolve`. The canonical contract uses `random_seed` for MC
and `sobol_start_index` for QMC; they are mutually exclusive in requests, metadata,
cache keys, and output. Legacy `seed` is accepted only by the parent plugin input
shim and normalized immediately. Tests cover repeatability, distinct streams,
direct/worker identity, powers-of-two path counts, convergence, and the QuantLib
dimension limit.

## Prevention

- Never call a Sobol start index a random seed.
- Keep MC seed, Sobol start index, and future scrambling seed as separate fields.
- Test that two start indices alter the actual generated result, not only metadata.
- Keep direct and spawned-worker output identity tests.
- Use convergence across powers of two rather than a single arbitrary
  correlation cutoff.

## Impact

MC and QMC requests now have unambiguous reproducibility semantics across API,
cache, metadata, direct execution, and spawned workers. Existing plugin callers can
still submit legacy `seed`, but it is not exposed as the canonical contract.

## Source files

| Role | Path |
|------|------|
| QuantLib QMC implementation | `backend/app/services/risk/quant/quantlib_worker.py` |
| API contracts | `backend/app/schemas/risk.py` |
| Mathematical tests | `backend/test_scripts/test_services/test_risk_simulation.py` |
| Probe | `scripts/spikes/risk/run_simulation_adapter_probe.py` |
