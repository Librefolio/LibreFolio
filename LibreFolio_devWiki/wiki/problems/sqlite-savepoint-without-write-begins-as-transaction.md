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
is not sufficient. Since 2026-10-15 the helper for that is `begin_writes(session,
table)` in `backend/app/db/session.py`: call it once before the loop that opens
the per-item savepoints. Keep the commit-failure regression test so this transaction
boundary cannot silently regress.

## Impact

Without the fix, an asset deletion could survive an outer commit failure, while
the caller received an exception implying the batch had rolled back. The fix
restores atomic failure semantics without changing production data during the
transaction-starting statement.

## Seen again (2026-10-15, backlog W-B20)

Workstream W met the trap again in lot N1, on broker deletion. `DELETE /brokers` commits when `errors` is empty, and
`BrokerService.delete_bulk` catches errors broker by broker without ever filling it. Whatever a failed broker already
wrote in the session goes into the commit.

- A savepoint per broker would not be enough, for the reason above. W reproduced it on a scratch SQLite with
  `aiosqlite`: a `SELECT`, then `begin_nested()` with an `INSERT`, then an outer rollback, and the row stays. With a
  write before the savepoint, no row.
- Workstream X's finding: a general SQLAlchemy `begin` listener that emits `BEGIN` up front is ruled out. A session
  that reads, sees another writer commit, then writes, fails at once with `SQLITE_BUSY_SNAPSHOT`, which
  `busy_timeout` does not wait for.
- The cure decided by the coordinator: a helper in the database session module that opens the transaction before a
  write path's first savepoint (this page's no-op `UPDATE`, or `BEGIN IMMEDIATE`). `delete_bulk` uses it per broker,
  with a red test first; `crud.py`'s local trick could move to it later (workstream X).

### Fixed (2026-10-15, W-B20)

- `begin_writes(session, table)` in `backend/app/db/session.py` runs an `UPDATE` of `table` that matches no row
  (`WHERE false`, primary key set to itself, `synchronize_session=False`). pysqlite emits `BEGIN` before it, and with a
  transaction already open it changes nothing. It is additive in a shared module, and its docstring says why it
  exists and why the `begin` listener does not.
- `BrokerService.delete_bulk` calls `begin_writes(self.session, Broker)` before its loop, then deletes each broker in
  `session.begin_nested()` through `_delete_one()`. That helper flushes inside the savepoint, the broker delete
  included, so a write error surfaces before RELEASE.
  - A broker that fails half-way leaves every row as it was: its own, and the other halves on other brokers.
  - The brokers before and after it in the request are deleted, and its result carries the error.
  - Nothing commits before the caller does. Account deletion, which rolls back when a broker cannot be released,
    stays all or nothing.
- Tests: section 4.10 of `test_broker_service.py` (BR-U-081…085), which provokes the failure by replacing
  `make_standalone` after `delete_by_broker`'s first two writes.
- Mutation check: without the `begin_writes` call, BR-U-082 and the two account all-or-nothing tests of
  `test_user_profile.py` turn red. The first broker stays deleted after the caller's rollback, because the RELEASE of
  its savepoint, the outermost one, committed.
- **Testing lesson.** A request holding only the failing item cannot tell the two cures apart: rolling back to the
  outermost savepoint restores everything either way. Only a *released* outermost savepoint commits early, so the
  test needs an item that succeeds before the one that fails, and a caller that rolls back afterwards.

## Source files

| Role | Path |
|------|------|
| Implementation | `backend/app/services/assets/crud.py` |
| Regression test | `backend/test_scripts/test_services/test_asset_source.py` |
| W-B20: the helper `begin_writes` | `backend/app/db/session.py` |
| W-B20: the broker bulk delete, one savepoint per broker (`_delete_one`) | `backend/app/services/brokers/broker_service.py` |
| W-B20: the commit when `errors` is empty | `backend/app/api/v1/brokers.py` |
| W-B20: regression tests BR-U-081…085 | `backend/test_scripts/test_services/test_broker_service.py` |
| W-B20: account deletion all or nothing (the mutation guard) | `backend/test_scripts/test_services/test_user_profile.py` |
| Backlog W-B20 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
