---
title: "3-Phase Pipeline for Bulk Operations"
category: decision
status: resolved
date: 2026-03-31
tags: [backend, architecture, async, database, bulk-operations]
related_features: [F-017, F-027]
related_problems: [asset-sync-transaction-closed]
---

# Decision: 3-Phase Pipeline for Bulk Operations

## Context

LibreFolio has two major bulk operations: FX rate sync and Asset price refresh. Both involve:
1. Querying database for configuration (routes, assignments)
2. Fetching data from external providers (network I/O)
3. Persisting results back to database (upserts, commits)

**Original Asset Implementation** (Phase 6 pre-Step2c):
```python
async def bulk_refresh_prices(asset_ids, session):
    tasks = [_refresh_single_asset(id, session) for id in asset_ids]
    return await asyncio.gather(*tasks)

async def _refresh_single_asset(id, session):
    assignment = await session.execute(select(Assignment).where(...))  # ← concurrent read
    asset = await session.execute(select(Asset).where(...))            # ← concurrent read
    prices = await provider.get_history_value(...)                      # network OK
    await bulk_upsert_prices(prices, session)                           # ← concurrent write
    session.add(assignment); await session.commit()                     # ← 💥 concurrent commit
```

**Problem**: N tasks sharing 1 session → concurrent commits → "This transaction is closed" SQLAlchemy error.

**FX Implementation** (Phase 5, already correct):
```python
async def sync_pairs_bulk(pairs, session):
    # Phase 1: batch query (shared session)
    routes = await session.execute(select(FxRoute).where(...))
    
    # Phase 2: fetch (no DB, parallel)
    leg_rates = await gather(*[provider.fetch_rates(...) for ...])
    
    # Phase 3: persist (per-route session, parallel)
    async def _process_route(slug):
        async with AsyncSession(engine) as s:
            await upsert_rates(..., s)
            await s.commit()
    results = await gather(*[_process_route(slug) for slug in pairs])
```

The FX code worked because Phase 1 and 2 were already separated, and Phase 3 created **per-task sessions**.

## Options Considered

### Option A: Serialize Everything

**Approach**: Process assets sequentially, one at a time.

**Pros**:
- No concurrency issues
- Simple to reason about

**Cons**:
- **Slow**: N assets × (query + network + DB write) done serially
- Phase 1: N queries instead of 1 batch query
- Phase 2: No parallelization of network I/O (slowest part)
- Unacceptable for bulk operations (7 assets would take 7× longer)

### Option B: Session-per-Task (naive)

**Approach**: Each task creates its own session at the start.

**Pros**:
- No shared session → no concurrent commit issue

**Cons**:
- **Phase 1 waste**: N separate queries `SELECT * FROM assignment WHERE id = ?` instead of 1 batch `WHERE id IN (...)`
- **Phase 2 mixing**: Network I/O interleaved with DB queries → slower
- Doesn't leverage batch query optimization

### Option C: 3-Phase Pipeline (chosen)

**Approach**: Separate into 3 sequential phases, each optimized for its access pattern:

```
Phase 1 — PREPARE (shared session, 2 batch queries)
├── SELECT * FROM asset_provider_assignment WHERE asset_id IN (1,2,3,...)
├── SELECT id, display_name, currency FROM asset WHERE id IN (1,2,3,...)
├── Build prepared_items: {id → {assignment, asset, provider_instance, params}}
└── Filter: assets without provider → SKIPPED (no Phase 2/3 for them)

Phase 2 — FETCH (no DB, parallel with semaphore)
├── For each asset:
│   ├── async with semaphore(10):  # limit concurrent network calls
│   │   └── prices = await provider.get_history_value(...)
│   └── Store: fetch_results[id] = {prices: [...], source: "yfinance"}
└── Network errors → fetch_errors[id] = str(e)

Phase 3 — PERSIST (per-task session, parallel)
├── For each asset with fetched data:
│   └── async with AsyncSession(engine) as session:  # ← isolated session
│       ├── await bulk_upsert_prices(prices, session)
│       ├── assignment.last_fetch_at = now(); session.add(assignment)
│       ├── await session.commit()
│       └── return FARefreshResult(status="OK", elapsed_ms=...)
└── DB errors isolated, don't corrupt other tasks
```

**Pros**:
- **Correctness**: No concurrent commits (each task has own session in Phase 3)
- **Performance Phase 1**: 2 batch queries (IN clause) vs N queries
- **Performance Phase 2**: Network I/O fully parallelized (slowest part)
- **Error isolation**: One asset's DB error doesn't block others
- **Clarity**: Clean separation read/fetch/write

**Cons**:
- More code structure complexity (3 loops instead of 1)
- Must pass data between phases via dicts

## Decision

**Chosen: Option C — 3-Phase Pipeline.**

**Principle**: Bulk operations must separate **database reads** (Phase 1), **network I/O** (Phase 2), and **database writes** (Phase 3) into sequential phases with appropriate session management.

## Implementation Details

### Session Management Rules

| Phase | Session Strategy | Rationale |
|-------|------------------|-----------|
| Phase 1 | Single shared session (read-only) | Batch queries are efficient, no concurrent writes |
| Phase 2 | No database access | Pure network I/O, fully parallelizable |
| Phase 3 | Per-task session (`async with AsyncSession(engine)`) | Isolates commits, errors don't propagate |

### Semaphore in Phase 2

**Asset providers**: Added `asyncio.Semaphore(10)` to limit concurrent network calls. Without limit, 100 assets → 100 simultaneous HTTP requests → provider throttling or local resource exhaustion.

**FX providers**: Already grouped by provider (ECB serves 10 currencies in 1 call), so natural batching limits concurrency.

### Error Handling

| Phase | Error Type | Handling |
|-------|-----------|----------|
| Phase 1 | DB query fails | Raise immediately (fatal, operation can't proceed) |
| Phase 2 | Network error (timeout, 404, etc.) | Store in `fetch_errors` dict, continue with other assets |
| Phase 3 | DB write fails (constraint, lock) | Caught per-task, return FARefreshResult with FAILED status |

**Result**: Partial success possible — 5/7 assets succeed, 2 fail (network timeout) → user sees detailed per-asset status.

## Consequences

### Positive

1. **Bug fixed**: "This transaction is closed" error eliminated
2. **Performance**: Asset bulk sync 2-3× faster (batch queries + parallel fetch)
3. **Robustness**: One asset's failure doesn't block others
4. **Testability**: Each phase can be tested independently
5. **Pattern established**: FX and Asset bulk operations now follow same conceptual design

### Trade-offs

1. **Code structure**: More verbose (3 nested loops) than naive "gather over single function"
2. **Memory usage**: Prepared items + fetch results held in memory between phases (acceptable for reasonable batch sizes)
3. **Not a generic abstraction**: FX and Asset phases differ enough that a shared base class would add complexity without benefit

### Why Not a Generic Orchestrator?

**Analysis**: FX and Asset 3-phase patterns differ significantly:

| Phase | FX | Asset | Generalizable? |
|-------|-----|-------|----------------|
| **Phase 1** | 1 query (routes) | 2 queries (assignments + assets) | ❌ Different schemas |
| **Phase 2** | Grouped by provider (batch fetch), Event-based | Per-item with semaphore | ❌ Incompatible strategies |
| **Phase 3** | Chain computation + upsert FxRate | Upsert PriceHistory + update assignment | ❌ Different models |
| **Result** | FXSyncPairResult | FARefreshResult | ❌ Different schemas |

**Decision**: The 3-phase **pattern** is a **documented convention**, not a class hierarchy. Each domain implements phases with domain-specific logic.

## Verification

**Tests** (Step 2c):
- `test_asset_source_refresh.py`: 7 tests covering concurrent refresh, mixed success/failure, SKIPPED status
- `test_fx_sync.py`: Already passing (pattern was correct from Phase 5)

**Evidence of fix**: User report: "10/10 tests passed" after migration.

## Related

- [[problems/asset-sync-transaction-closed]] — the original bug this decision fixed
- [[features/F-017]] — FX Rate Sync (already used 3-phase)
- [[features/F-027]] — Asset Data Sync (migrated to 3-phase in Step 2c)
- Source: [[sources/phase06-step2c-sync-refactor]]

## Source files

| Role | Path |
|------|------|
| FX sync (Phase 1-3) | `backend/app/services/fx.py` (sync_pairs_bulk) |
| Asset sync (Phase 1-3) | `backend/app/services/asset_source.py` (bulk_refresh_prices) |
| Asset sync tests | `backend/test_scripts/test_services/test_asset_source_refresh.py` |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/plan-phase06Step2cSyncDeleteRefactor.prompt.md` |
