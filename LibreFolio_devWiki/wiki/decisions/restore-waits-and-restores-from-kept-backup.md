---
title: "A restore can wait, can start from a kept backup, and can check a password before it runs"
category: decision
status: resolved
date: 2026-11-07
tags: [backup, restore, security, storage, release-1.3]
related:
  - decisions/storage-limit-enforced
  - decisions/backups-kept-in-backups-folder
  - entities/backup-router
  - features/F-073
---

# Decision: the restore waits, starts from a kept backup, checks a password

## Context

After a restore archive is uploaded, the server checks it on a copy and keeps the check for a while (its report's
`expires_at`). In 1.3 before this lot, the check's id (`stage_id`) lived only in the browser tab that started it
(`sessionStorage`): closing the tab, opening another or changing device left no way back to it, while the copy kept
taking space until it expired. With the space limit enforced (see [[decisions/storage-limit-enforced]]) it was worse: a
check refused for space took space exactly when it was missing, and could not be restored anyway. The developer's test
list of 07/11/2026 also asked to restore a backup the server already keeps without downloading it, and to know before
a restore whether a password will open the restored instance.

## Options considered

The coordinator proposed ten changes (`DECISIONI-giro2-backup-20261107.md`), in two steps: A (screens and the space
rules, proposals 1–7) and B (the restore that changes, 8–10), so that A could ship even if B slipped. The developer
took all ten for 1.3. On the password check he asked for **no extra rule**: only an administrator can run a restore, so
only an administrator can ask; the one rule that stays is the app-wide one, a password never reaches a log or a report.

## Decision

- **A check can wait.** In the report window *Decide later* closes it and keeps the check. Settings › Backup lists the
  waiting checks, with *Resume* (the same report) and *Discard*, from any tab or device of an administrator: the server
  lists them (`GET /restore/stages`), the browser no longer has to remember. The words «checked copy» are gone: the
  interface says «uploaded archive».
- **A blocked check asks for nothing.** With a blocker, the lower part of the window (the confirmation word and
  *Restore and restart*) is not shown. A check refused by the space limit **is deleted on the server at once**; its
  report stays on screen with the message and the numbers until the user closes it.
- **Restore from a kept backup.** *Restore* on a row of the backups table: `POST /restore/upload/from-backup` copies the
  kept archive into the restore's upload slot, with no download and no upload, and the normal check runs on it
  (`POST /restore/stage`, a secure backup with its password). One path, no parallel one; a sealed backup of a hosting
  panel is refused (409 `backup_sealed_unsupported`); the kept backup stays.
- **Password check.** In the report, pick an administrator of the backup, type a password, *Verify*:
  `POST /restore/stage/{stage_id}/verify-password` compares it with that account's hash **in the opened copy**, with
  bcrypt in `asyncio.to_thread`. The answer is yes or no; the password is never stored, logged or sent back. 409
  `restore_stage_copy_gone` when the copy was dropped, expired or given back for the space limit.
- **A more graphic report.** The backup's administrators with their avatars, read from the opened copy
  (`GET /restore/stage/{stage_id}/avatar/{username}`, an admin's avatar read from `user_settings`), and a bar of what the
  backup holds (database, files, reports: the report fields `uploads_size` and `broker_reports_size`), drawn with the
  same bar component. Names stay text, for screen readers.
- Before an archive is uploaded, the window says how much space checking it takes.

## Consequences

- The restore is the riskiest path of the app (an error loses data), so step B was proved with a real restore end to
  end on test data: from a kept backup, secure and not, to the restart and the sign-in with the verified password
  (`73450351c`).
- The new report fields broke the exact-key tests again (`445ea2849`, `34746a2b5`): see
  [[problems/exact-key-tests-break-when-response-gains-a-field]].

## Links

- Sources: `DECISIONI-giro2-backup-20261107.md`, `kickoff-w9-backup.md` (lot C9) — coordinator files kept outside the
  repository. Summary: [[sources/wave8-9-release-1.3-closing-2026-11]]

## Source files

| Role | Path |
|------|------|
| Restore routes (stages list, from-backup, verify-password, avatar) | `backend/app/api/v1/backup/restore.py` |
| Waiting checks, kept backup as the archive, give room back | `backend/app/services/platform/instance_backup/restore_jobs.py` |
| Password and avatar read from the opened copy | `backend/app/services/platform/instance_backup/stage_peek.py` |
| The check and its report | `backend/app/services/platform/instance_backup/staging.py` |
| Schemas | `backend/app/schemas/backup.py` |
| Restore flow (frontend) | `frontend/src/lib/features/backup/restoreFlow.svelte.ts`, `frontend/src/lib/features/backup/restoreRequest.svelte.ts` |
| Report window, card, backups table | `frontend/src/lib/features/backup/RestoreReportModal.svelte`, `frontend/src/lib/features/backup/RestoreCard.svelte`, `frontend/src/lib/features/backup/BackupList.svelte` |
| Tests | `backend/test_scripts/test_services/test_restore_stage_peek.py`, `backend/test_scripts/test_api/test_backup_users_limit_api.py` |
| Admin guide | `mkdocs_src/docs/admin/backup_restore.en.md` |
