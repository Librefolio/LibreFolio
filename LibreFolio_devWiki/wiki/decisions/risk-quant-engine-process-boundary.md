---
title: "Risk quantitative engines use isolated idle-reaped spawn workers"
category: decision
status: resolved
date: 2026-07-28
tags: [backend, risk, quantlib, riskfolio, multiprocessing, performance, architecture]
related:
  - concepts/backend-only-calculations
  - concepts/cancellation-safe-inflight-deduplication
  - problems/quantlib-sobol-seed-skipto
  - problems/spawn-worker-response-queue-semaphore-leak
  - problems/riskfolio-numpy-vectorbt-dependency-trap
  - problems/risk-spawn-worker-idle-residency
  - sources/phase00-risk-analysis-backend
---

# Decision: Risk quantitative engines use isolated idle-reaped spawn workers

## Context

Risk simulation and portfolio optimization call heavy native libraries. Running
them in the FastAPI process, even behind `asyncio.to_thread`, isolates the event
loop wait but not CPU, memory, native-library faults, or the GIL/native runtime
failure domain. Reimplementing established simulation and optimization engines
with NumPy would also increase LibreFolio's mathematical and maintenance burden.

## Options Considered

1. **In-process thread offload** — low IPC cost, but native computation and memory
   remain in the web process.
2. **Fresh child process for each request** — strong isolation, but repeats costly
   QuantLib/Riskfolio imports and solver startup.
3. **Separate lazy `spawn` pools with warm reuse and idle reap** — process isolation,
   bounded concurrency, targeted recycle, independent failure domains, and bounded
   idle memory residency.

## Decision

LibreFolio runs stochastic simulation with QuantLib 1.43 and portfolio
optimization with Riskfolio-Lib 7.0.1 in two independent lazy `spawn` pools. The
production web process never imports or executes those engines. Each pool has its
own worker count, bounded capacity, job timeout, idle timeout, cache, and failure
domain. A timeout, crash, or invalid response terminates and recreates only the
affected lane. After the pool is idle for 600 seconds, all lanes are stopped; the
next request starts them lazily with new PIDs.

NumPy remains available for linear algebra, aggregation, and independent test
oracles; it is not a fallback production simulation engine. There is no silent
fallback if QuantLib or Riskfolio fails. Default pool size is one worker per
domain, while larger counts remain configurable because the production benchmark
measured repeatable concurrent speedups at an approximately linear memory cost.

## Consequences

- Native CPU/memory work cannot block or destabilize the FastAPI process.
- Warm workers amortize QuantLib/Riskfolio import and solver startup.
- Idle reap releases roughly 171 MB per simulation worker and 340 MB per
  optimization worker when Risk is unused.
- Simulation and optimization cannot exhaust each other's queue or worker.
- Timeout and crash recovery are observable and testable.
- Deployment must budget roughly 175 MB per warm simulation worker and 341 MB per
  warm optimization worker for the measured fixtures.
- `asyncio.to_thread` is allowed only around blocking IPC/join or lightweight
  analytics, never as the quantitative execution boundary.
- API contracts contain serializable DTOs only; no QuantLib, pandas, CVXPY, or
  Riskfolio object crosses the process boundary.

## Source files

| Role | Path |
|------|------|
| Generic spawn pool | `backend/app/services/risk/quant/spawn_worker.py` |
| Pool configuration | `backend/app/services/risk/quant/workers.py` |
| Idle timeout settings | `backend/app/config.py` |
| QuantLib child engine | `backend/app/services/risk/quant/quantlib_worker.py` |
| Riskfolio child engine | `backend/app/services/risk/quant/riskfolio_worker.py` |
| Simulation parent boundary | `backend/app/services/risk/quant/engine.py` |
| Optimization parent boundary | `backend/app/services/risk/quant/optimization_engine.py` |
| FastAPI lifecycle | `backend/app/main.py` |
| Implementation plan | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01Step5SimulationScaleOptimization.prompt.md` |
| Benchmark | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/benchmark-phase01SimulationScale.md` |
| Lifecycle tests | `backend/test_scripts/test_services/test_risk_spawn_worker.py` |
