---
title: "SQLite reused the id of a deleted row, and whatever pointed at it outside the database followed"
category: problem
status: resolved
date: 2026-10-08
tags: [backend, database, sqlite, ids, autoincrement, data-integrity, brim, post-migration]
related: [problems/account-deletion-orphaned-brokers, problems/brim-file-store-rename-race, concepts/single-migration-strategy, sources/phase00-account-and-id-reuse-2026-10, sources/phase00-e2e-import-infra-2026-10]
---

# Problem: ids came back after a delete

## Symptom

In the import E2E runs (plan 33, [[sources/phase00-e2e-import-infra-2026-10]]), a freshly created broker showed
report files it had never received. They
belonged to an earlier broker, deleted, whose id the new one had taken — and with it the `broker_<id>` folders of
uploaded reports on disk.

## Root cause

SQLite gives a table declared `id INTEGER PRIMARY KEY` (without `AUTOINCREMENT`) the next id as `max(id) + 1`:
delete the newest row, and the next insert takes its id again. Inside the database that is harmless — foreign keys
go with the row. Outside it is not: several ids **leave the backend and stay saved** — the `broker_<id>` report
folders, BRIM sidecars, URLs the user saved, benchmarks and choices kept in `localStorage`. A reused id silently
re-points all of them at a different entity.

The E2E trigger was a test helper (`populate --force` deleted the database but not the report folders), but the
mechanism exists in production: delete the newest broker, create another.

## Solution (train 12, merge `637c5d105`)

The developer rejected a local workaround ("b2") and asked for a fix at the root:

- **The tables whose ids leave the backend never reuse one**: `users`, `brokers`, `assets`, `transactions`,
  `asset_events`, `fx_conversion_routes` declare `sqlite_autoincrement=True` in the models; new databases are created
  that way. High-volume series (prices, FX rates) are deliberately excluded.
- **A schema test** checks the keyword after `alembic upgrade head`: SQLAlchemy 2.0 does not read `AUTOINCREMENT`
  back from the database, so a future batch migration (a table rebuild) would drop it silently.
- **Existing databases** are converted by a new subsystem of *post-migration fixes*
  (`backend/app/db/post_migration/`): ordered repairs that look for the anomaly they correct and apply only if they
  find it. Two entry points — server start-up, right after the migrations (`run_post_migration_fixes_at_startup()`
  in `main.py`, never raising), and offline with the server stopped (`python -m backend.app.db.post_migration`, also
  inside the Docker image). Safety rules: `PRAGMA integrity_check` first (a damaged database is never touched); WAL
  checkpoint and a backup copy; one transaction with foreign keys off; then `foreign_key_check` empty and identical
  row counts; the backup is deleted once verified (D2) and kept on any error, with a rollback, a warning and a normal
  start — start-up is never blocked; idempotent.
- The first fix rebuilds each table from its **current** `CREATE TABLE` with exactly one change (`AUTOINCREMENT`),
  copies ids as they are (D4), and refuses any id-column shape it does not recognise. Before converting `brokers`,
  orphan `broker_reports/<status>/broker_<n>` folders are quarantined, then deleted when the fix is verified: the
  first broker created after the conversion may reuse `<n>` once and must not inherit them.

## Prevention

- An id that leaves the database (a path, a URL, a client-side key) must be one that is never reissued.
- A test helper that resets the database must reset the files keyed by its ids too — the runner's `db create`
  already did; `populate --force` did not (fixed in plan 33).

## Impact

Files and saved references attached to the wrong entity after a delete — in tests visibly, in production silently.
No field case was known when it was fixed.

## Source files

| Role | Path |
|------|------|
| Models (`sqlite_autoincrement` on six tables) | `backend/app/db/models.py` |
| Post-migration runner (integrity, backup, verify) | `backend/app/db/post_migration/__init__.py` |
| Fix contract | `backend/app/db/post_migration/base.py` |
| The AUTOINCREMENT fix, orphan-folder quarantine | `backend/app/db/post_migration/autoincrement.py` |
| Offline entry point | `backend/app/db/post_migration/__main__.py` |
| Start-up entry point | `backend/app/main.py` |
| Tests | `backend/test_scripts/test_db/test_post_migration.py` |
| E2E reset of report folders (plan 33) | `backend/test_scripts/test_db/populate_mock_data.py` |
| Plan (§0 B, §2.3, D1–D6) | `LibreFolio_developer_journal/Release_2/phases/34_accountAndIdReuse/plan-phase00AccountAndIdReuse.prompt.md` |
