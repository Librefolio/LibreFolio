---
title: "SQLite savepoint without an outer write transaction commits on release"
category: problem
status: resolved
date: 2026-09-10
tags: [backend, sqlite, sqlalchemy, transactions, savepoint, rollback]
related: [decisions/three-phase-pipeline]
---

# Problem: SQLite savepoint without an outer write transaction commits on release

## Symptom

After read-only setup, `AssetCRUDService.delete_assets_bulk` deleted an asset
inside `begin_nested()`. When the simulated final `session.commit()` failed, the
asset was nevertheless absent from a fresh session instead of being restored by
the outer rollback.

## Root Cause

SQLite defers the real `BEGIN` across reads. In an `AsyncSession` that has only
executed `SELECT`, the first `begin_nested()` can therefore become the effective
outer transaction. Releasing that savepoint persists its delete, so a later
`session.rollback()` cannot undo it after a final commit failure.

## Solution

`AssetCRUDService.delete_assets_bulk` now performs a no-op `UPDATE` before its
per-item savepoints. This starts SQLite's outer write transaction without
changing rows. Each savepoint can then isolate an item, while a failed final
commit still rolls the complete tentative batch back. A regression test verifies
the asset remains persisted after commit failure.

## Prevention

When SQLite work relies on savepoints followed by an outer rollback, ensure a
write transaction has begun before opening the first savepoint; read-only setup
is not sufficient. Keep the commit-failure regression test so this transaction
boundary cannot silently regress.

## Impact

Without the fix, an asset deletion could survive an outer commit failure, while
the caller received an exception implying the batch had rolled back. The fix
restores atomic failure semantics without changing production data during the
transaction-starting statement.

## Source files

| Role | Path |
|------|------|
| Implementation | `backend/app/services/asset_source.py` |
| Regression test | `backend/test_scripts/test_services/test_asset_source.py` |
