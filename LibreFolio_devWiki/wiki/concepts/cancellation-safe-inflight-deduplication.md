---
title: "Cancellation-safe in-flight calculation deduplication"
category: concept
tags: [backend, async, cache, cancellation, concurrency, risk]
related:
  - decisions/risk-quant-engine-process-boundary
  - concepts/async-io-rule
  - concepts/portfolio-report-unified
---

# Concept: Cancellation-safe in-flight calculation deduplication

## Definition

Content-keyed quantitative caches deduplicate identical concurrent misses: one
leader submits the expensive child-process job and followers await the same
future. Follower cancellation must not cancel that shared future, while leader
cancellation must explicitly resolve or cancel it so followers never wait
forever.

The LibreFolio pattern is:

1. protect follower waits with `asyncio.shield(shared_future)`;
2. let the leader publish either the result or the exact failure;
3. if the leader is cancelled, cancel the unresolved shared future;
4. remove the in-flight entry in `finally`;
5. cache only successful immutable results.

## Where It Applies

- QuantLib simulation cache and request collapse.
- Riskfolio optimization cache and request collapse.
- Any future expensive content-keyed async calculation where callers can be
  independently cancelled.

## Why It Matters

Awaiting a bare shared future couples every caller's cancellation state: one
cancelled HTTP request can abort work needed by other callers. Conversely, a
cancelled leader that exits without resolving the future creates a permanent
wait. The shield-plus-explicit-leader-cleanup pattern prevents both failure
modes without duplicating expensive jobs.

## Source files

| Role | Path |
|------|------|
| Simulation implementation | `backend/app/services/risk/quant/engine.py` |
| Optimization implementation | `backend/app/services/risk/quant/optimization_engine.py` |
| Cancellation regression tests | `backend/test_scripts/test_services/test_risk_spawn_worker.py` |
