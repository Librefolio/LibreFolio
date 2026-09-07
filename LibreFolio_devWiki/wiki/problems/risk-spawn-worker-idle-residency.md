---
title: "Risk spawn workers stayed resident after idle"
category: problem
status: resolved
date: 2026-07-28
tags: [backend, risk, multiprocessing, spawn, lifecycle, memory]
related:
  - decisions/risk-quant-engine-process-boundary
  - sources/phase00-risk-analysis-backend
---

# Problem: Risk spawn workers stayed resident after idle

## Symptom

The QuantLib and Riskfolio pools were lazy before their first request but remained
alive until FastAPI shutdown afterward. Measured warm RSS was about 171 MB for one
simulation worker and 340 MB for one optimization worker, so occasional Risk usage
left substantial memory resident indefinitely.

## Root Cause

`SpawnWorkerPool` implemented job timeout, crash recycle, bounded queues, and
application shutdown, but no transition from an idle running pool back to the lazy
state. A naive timer would be unsafe because it could race with newly queued or
in-flight work.

## Solution

Each domain now has a configurable idle timeout, default 600 seconds. When pending
work reaches zero, the pool schedules a generation-tagged reap. Accepting another
job invalidates that generation. The reaper acquires the pool lock, checks
`_pending == 0` again, stops every lane, and clears lane state without marking the
pool permanently closed. The next request starts fresh lanes lazily.

Timeout `0` disables idle reap. Tests cover queued/in-flight safety, multi-lane
reap, repeated restart cycles, shutdown during the timer, new PIDs after restart,
and absence of orphan processes.

## Prevention

- Treat lazy start and bounded idle residency as separate lifecycle requirements.
- Never let an idle timer stop a lane without a locked pending-work recheck.
- Use generation tokens to invalidate stale timers after new work arrives.
- Test at least two lanes and repeated reap/restart cycles.

## Impact

Risk workers keep warm-start performance during normal request bursts while
releasing native-library memory after inactivity. The web process remains isolated,
and timeout/crash behavior is unchanged.

## Source files

| Role | Path |
|------|------|
| Pool lifecycle | `backend/app/services/risk/quant/spawn_worker.py` |
| Pool configuration | `backend/app/services/risk/quant/workers.py` |
| Settings | `backend/app/config.py` |
| Lifecycle tests | `backend/test_scripts/test_services/test_risk_spawn_worker.py` |
| Benchmark | `scripts/spikes/risk/run_simulation_scale_benchmark.py` |
| Audit report | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/report-phase01RiskBackendAuditAndRemediation.md` |
