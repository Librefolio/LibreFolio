---
title: "Asset Sync Transaction Closed Error"
category: problem
status: resolved
date: 2026-03-31
tags: [backend, async, database, sqlalchemy, concurrency]
related_features: [F-027]
related_decisions: [three-phase-pipeline]
---

# Problem: Asset Sync "This Transaction is Closed" Error

## Symptom

Bulk asset price sync (`POST /api/v1/assets/bulk-refresh-prices`) failed intermittently with SQLAlchemy error:

```
sqlalchemy.exc.InvalidRequestError: This transaction is closed
```

**Frequency**: Appeared on ~30% of bulk syncs with 5+ assets. Single-asset refresh worked consistently.

**User impact**: Sync modal showed all assets as FAILED even though some providers had successfully fetched data. Data loss (fetched prices not persisted).

## Root Cause

**Concurrent writes to shared session**:

```python
async def bulk_refresh_prices(asset_ids: List[int], session: AsyncSession):
    tasks = [_refresh_single_asset(id, session) for id in asset_ids]
    return await asyncio.gather(*tasks)

async def _refresh_single_asset(asset_id: int, session: AsyncSession):
    # Step 1: Read (concurrent across tasks - OK)
    assignment = await session.execute(select(Assignment).where(id=asset_id))
    asset = await session.execute(select(Asset).where(id=asset_id))
    
    # Step 2: Fetch (no DB, parallel - OK)
    prices = await provider.get_history_value(...)
    
    # Step 3: Write (concurrent across tasks - NOT OK)
    await bulk_upsert_prices(prices, session)  # ← multiple tasks writing
    session.add(assignment)
    await session.commit()  # ← 💥 multiple tasks committing same session
```

**Why it failed**:
- SQLAlchemy `AsyncSession` is **not thread-safe** for concurrent commits
- Task 1 calls `session.commit()` → session closes
- Task 2 (still running) tries `session.commit()` → "transaction is closed"

**Why FX sync worked**: FX sync already used per-task sessions in Phase 3 (see [[decisions/fx-sync-pair-based]]).

## Investigation Path

1. **Initial suspicion**: Provider timeout or network error → ruled out (some assets succeeded, but data not persisted)
2. **Logging added**: Confirmed multiple tasks calling `session.commit()` simultaneously
3. **Async inspection**: Discovered shared session passed to `asyncio.gather([...])` with N concurrent tasks
4. **Comparison to FX**: Analyzed FX sync code → noticed per-task session pattern in `_process_route()`
5. **Root cause confirmed**: Session shared across concurrent async tasks performing writes

## Solution

**Implemented**: [[decisions/three-phase-pipeline]] — separate database access into 3 phases:

```
Phase 1 — PREPARE (shared session, read-only, batch queries)
Phase 2 — FETCH (no database, parallel)
Phase 3 — PERSIST (per-task session, isolated commits)
```

**Key change**:
```python
# Phase 3 — each task gets its own session
async def _persist_asset_data(asset_id: int, prices: List[...]):
    async with AsyncSession(engine) as session:  # ← new session per task
        await bulk_upsert_prices(prices, session)
        assignment.last_fetch_at = datetime.utcnow()
        session.add(assignment)
        await session.commit()  # ← isolated commit, no conflict
        return FARefreshResult(status="OK", ...)

# Orchestrator (Phase 3)
persist_tasks = [_persist_asset_data(id, data) for id, data in fetch_results.items()]
results = await asyncio.gather(*persist_tasks, return_exceptions=True)
```

**Benefits**:
- Each task commits independently → no session conflict
- One task's DB error doesn't corrupt others
- Partial success possible (5/7 assets succeed, 2 fail independently)

## Prevention

**Pattern established**: All future bulk operations must follow 3-phase pattern with **per-task sessions in Phase 3**.

**Code review checklist**:
- [ ] Does bulk operation pass shared session to `asyncio.gather` tasks?
- [ ] Do tasks perform **writes** (insert/update/delete) on that session?
- [ ] If yes to both → **refactor to per-task sessions**

**Safe pattern**:
```python
# ✅ GOOD: per-task session
async def _process_item(item_id):
    async with AsyncSession(engine) as session:
        await write_data(session)
        await session.commit()

# ❌ BAD: shared session
async def bulk_op(items, session):
    tasks = [_process_item(id, session) for id in items]  # ← same session
    await asyncio.gather(*tasks)
```

## Impact

**Before fix**:
- 30% failure rate on bulk sync (5+ assets)
- Frustrating UX: "all failed" even though some data was fetched
- Data loss: fetched prices not persisted

**After fix**:
- 0% failure rate (100+ syncs tested)
- Granular per-asset status: "5 OK, 2 FAILED (network timeout)"
- No data loss: successful fetches always persisted

**Performance improvement**: 2-3× faster (batch queries in Phase 1 + parallel network in Phase 2).

## Timeline

- **2026-03-25**: Bug reported by user (intermittent sync failures)
- **2026-03-27**: Root cause identified (shared session + concurrent commits)
- **2026-03-29**: 3-phase pipeline implemented
- **2026-03-31**: Verified fixed (Step 2c completed, 10/10 tests passed)

## Related

- [[decisions/three-phase-pipeline]] — the architectural solution
- [[features/F-027]] — Asset Data Sync feature
- Source: [[sources/phase06-step2c-sync-refactor]]

## Source files

| Role | Path |
|------|------|
| Fixed implementation | `backend/app/services/asset_source.py` (bulk_refresh_prices) |
| Test suite | `backend/test_scripts/test_services/test_asset_source_refresh.py` (7 tests) |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/plan-phase06Step2cSyncDeleteRefactor.prompt.md` |
