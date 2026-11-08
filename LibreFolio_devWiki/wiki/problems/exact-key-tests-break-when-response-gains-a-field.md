---
title: "A test that pins the exact set of keys of a response breaks when another lot adds a field: seen twice on the restore report"
category: problem
status: recurs
date: 2026-11-07
tags: [testing, backend, api, backup, restore, parallel-work, merge]
related:
  - decisions/storage-limit-enforced
  - decisions/restore-waits-and-restores-from-kept-backup
  - concepts/test-isolation-classes
---

# Problem: exact-key tests break when a response gains a field

## Symptom

After a lot added fields to the restore report (`RestoreStageReport`), the candidate branch went red in tests the lot
had not touched: `test_backup_users_limit.py` and `test_backup_users_limit_api.py` assert the **exact** set of the
report's keys. It happened twice in two days:

- 06/11/2026, lot C8 (the space limit): four storage fields (`storage_limit_mb`, `storage_limit_locked`,
  `storage_required_bytes`, `storage_disk_missing_bytes`) — fixed by `21396f65b`;
- 07/11/2026, lot C9 (the restore report's parts bar): `uploads_size`, `broker_reports_size` — fixed by `445ea2849` and
  `34746a2b5`.

A cousin of the same day: `dc89f6879` — two frontend tests mocked `$lib/i18n` with a reduced set of exports; `trySave`
began to reach the language store through the new storage-limit message, and the mocks lacked the export it needed.

## Root cause

The exact-key assertion is deliberate: the users-limit lot (B5-1k2) wanted to prove that it added exactly three numbers
and leaked no user name. But the test belongs to another category than the lot that adds the next field, so the lot's
own category stays green; the red appears only in a full or merged run. The test pins a contract that several lots
extend.

## Solution

Each time, the expected set was extended with a named tuple per lot (`STORAGE_FIELDS`, `PARTS_FIELDS`), so the
assertion stays exact and says which lot owns which field. The mocks keep the real i18n exports
(`importOriginal`-style) instead of a hand-made subset.

## Prevention

- **Before adding a field to a public response, grep the tests for exact-key assertions on it** (`set(report) ==`,
  `keys() ==`, `additionalProperties`). The kickoff of lot C9 now says so explicitly.
- Run the categories that own those tests, not only the lot's own.
- Prefer partial mocks that spread the real module over hand-written module shapes.

## Impact

Two red gates on the 1.3 candidate, each fixed in minutes once read; no user impact.

## Source files

| Role | Path |
|------|------|
| Exact-key test (API) | `backend/test_scripts/test_api/test_backup_users_limit_api.py` |
| Exact-key test (service) | `backend/test_scripts/test_services/test_backup_users_limit.py` |
| The report schema | `backend/app/schemas/backup.py` |
| Mocks fixed by `dc89f6879` | `frontend/src/lib/features/settings/PasswordChangeModal.test.ts`, `frontend/src/lib/services/fxCreationSync.test.ts` |
