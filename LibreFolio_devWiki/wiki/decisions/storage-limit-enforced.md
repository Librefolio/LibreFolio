---
title: "The space limit is enforced: what it refuses and what it never stops"
category: decision
status: resolved
date: 2026-11-06
tags: [backup, storage, files, restore, limits, release-1.3]
related:
  - decisions/backups-kept-in-backups-folder
  - decisions/restore-waits-and-restores-from-kept-backup
  - entities/backup-router
  - features/F-073
  - problems/exact-key-tests-break-when-response-gains-a-field
---

# Decision: the space limit is enforced

## Context

Wave 6 (FB-29) gave the Files page a storage bar and a space limit an administrator can set, `storage_limit_mb`
(or `LIBREFOLIO_STORAGE_LIMIT_MB`, which wins). It was decided then that the limit was **shown, not applied**. During
the 1.3 test list (06/11/2026) the developer asked for the opposite: a limit that does not limit confuses. The
question was what to block without leaving the instance unusable or without a copy.

## Options considered

The proposal of 06/11 had two rows the developer changed:

| Action | Proposal | Developer's answer (wins) |
|---|---|---|
| Automatic backup | try the clean-up; if still over, skip and warn | **always made**: at worst the clean-up removes the old ones |
| Restore of a backup | never blocked, it is the emergency tool | **refused** when the result would pass the limit, with the numbers to fix it |

## Decision

The limit is the most space LibreFolio may take in its data directory, all of it (database, uploads, broker reports,
backups, the rest). 0 = no limit, and nothing changes.

| Action | Rule |
|---|---|
| An upload, a broker report (a combined report too) | refused when it would take the data past the limit |
| A backup started by hand | the backup clean-up runs first; refused if still past the limit |
| A backup of the hosting panel, or of the command line (`dev.py backup create`) | always made; the clean-up runs after it |
| A restore | refused when what it leaves would pass the limit |
| Transactions, prices, the database | never stopped: the app would stop working |

Two rows were decided by the coordinator, not asked: the command-line backup counts as an automatic one (the guide
advises running it from cron, and a silent refusal would leave the instance without a copy), and combined broker
reports follow the report rule (they write new bytes).

- **Every refusal is a 507** with the code `storage_limit_exceeded` and the numbers a message needs: the limit, the space
  used, `required_mb` (raise the limit to at least this) and `disk_missing_bytes` (free at least this on the disk; 0 when
  the disk has room). The messages say what to do: an administrator gets *Open the settings*, a member how much to free
  and to ask an administrator. A limit fixed by the hosting provider (`limit_locked`) never says «raise it here».
- **The estimate of a manual backup** is the size on disk of what the archive carries (database, uploads, broker
  reports). The archive is compressed, so it is an upper bound: a backup refused on it loses nothing.
- **A restore is judged on what it leaves**: the restored data plus the backups and the rest that stay, without the
  restore's own work folder (`.restore/`). The limit is the one in force before the restore, read from the data
  directory's database opened immutable (no `-wal` or `-shm` created); the confirmation re-checks against the limit the
  check recorded, or the provider's variable read again.
- **A limit that cannot be read is no limit**, as before: `read_limit` never raises.
- **Over the limit the bar keeps every part**, with a tick at the limit and red stripes past it (`LinkedStackedBar`,
  shared with the PAC allocator); a restore under way is a part of its own (C9-4, C9-7).

## Consequences

- `files.*.hint` and the admin guides now say the limit refuses; `.env.example` says what the variable refuses.
- A restore check refused by the limit gives its room back at once (see
  [[decisions/restore-waits-and-restores-from-kept-backup]]).
- The new report fields broke two exact-key tests in another category, twice (C8 and C9): see
  [[problems/exact-key-tests-break-when-response-gains-a-field]].
- Supersedes the «shown, not applied» line of [[decisions/backups-kept-in-backups-folder]].

## Links

- Sources: `DECISIONI-ondata8-20261106.md` (question 1 and the developer's answer), `kickoff-w8.md` (lot C8),
  `DECISIONI-giro2-backup-20261107.md` (proposals 1–7, lot C9 step A) — coordinator files kept outside the repository.
- Summary: [[sources/wave8-9-release-1.3-closing-2026-11]]

## Source files

| Role | Path |
|------|------|
| The rule, the estimate, the restore judgement | `backend/app/services/platform/storage_limit.py` |
| What the data directory takes | `backend/app/services/platform/storage_usage.py` |
| Upload refusal | `backend/app/api/v1/uploads.py` |
| Broker report refusal | `backend/app/api/v1/brokers.py`, `backend/app/services/brim/brim_report_sets.py` |
| Manual backup refusal | `backend/app/api/v1/backup/job_views.py` |
| Restore refusal | `backend/app/services/platform/instance_backup/staging.py`, `backend/app/services/platform/instance_backup/apply.py` |
| Frontend refusal message | `frontend/src/lib/components/ui/feedback/StorageLimitRefusal.svelte`, `frontend/src/lib/utils/files/storageLimit.ts` |
| The bar (tick and stripes) | `frontend/src/lib/components/ui/display/LinkedStackedBar.svelte`, `frontend/src/lib/features/files/StorageBar.svelte` |
| Tests | `backend/test_scripts/test_services/test_storage_limit.py`, `backend/test_scripts/test_api/test_storage_limit_api.py` |
| Admin guide | `mkdocs_src/docs/admin/backup_restore.en.md`, `mkdocs_src/docs/admin/configuration.en.md` |
