---
title: "Forced spawn-worker crashes leaked response-queue semaphores"
category: problem
status: resolved
date: 2026-07-28
tags: [backend, multiprocessing, spawn, ipc, resource-leak, risk]
related:
  - decisions/risk-quant-engine-process-boundary
  - concepts/cancellation-safe-inflight-deduplication
---

# Problem: Forced spawn-worker crashes leaked response-queue semaphores

## Symptom

Lifecycle tests that deliberately killed a quantitative worker completed
functionally but Python's resource tracker warned about three leaked semaphore
objects at process shutdown.

## Root Cause

Each lane used a `multiprocessing.Queue` for its one-response-at-a-time return
channel. That queue owns synchronization primitives whose cleanup is unreliable
when the child is forcefully terminated during timeout/crash recovery.

## Solution

The request side remains a bounded multiprocessing queue for backpressure. The
single-consumer response side is now a one-way pipe, which fits the lane protocol
without queue semaphores. Timeout/crash recycling closes old endpoints and
creates a fresh lane. Forced-crash tests now finish without resource-tracker
warnings.

## Prevention

- Choose the smallest IPC primitive matching channel cardinality.
- Do not use a queue for a single outstanding response merely for symmetry.
- Include forced timeout/crash and interpreter-shutdown checks in worker tests.
- Recycle and close only the affected lane.

## Source files

| Role | Path |
|------|------|
| IPC and lifecycle implementation | `backend/app/services/risk/quant/spawn_worker.py` |
| Crash/recycle tests | `backend/test_scripts/test_services/test_risk_spawn_worker.py` |
| Scale/recovery benchmark | `scripts/spikes/risk/run_simulation_scale_benchmark.py` |
