---
title: "Finished backups stay on the server, in `backups/`, with a clean-up by size and age"
category: decision
status: resolved
date: 2026-11-05
tags: [backup, storage, files, settings, cli]
related: [entities/backup-router, decisions/api-routes-removed-without-deprecation]
---

# Decision: backups stay in `backups/`

## Context
A backup used to be a file the user downloaded and the server forgot. Backups made from the command line, from the
app and by the nightly job lived in different places, nobody could see them together, and old ones were never
removed.

## Decision
- **One place.** Every finished backup, whatever made it (app, `dev.py backup create`, the nightly job), is kept in its
  own folder inside `backups/`. In Docker the folder, like `secrets/`, is readable only by LibreFolio's user.
- **One list.** The backups are shown in a `DataTable` (Settings › Backup and the Files › Backups tab) with origin,
  type, size and SHA-256, ready to download or delete. `dev.py backup create` without `--output` prints the SHA-256.
- **Clean-up by size and by age.** An administrator can set a maximum total size and a maximum age; the latest backup
  is always kept.
- **A storage bar (FB-29).** The Files page shows administrators the space taken by the database, the uploaded files,
  the broker reports and the backups, against the disk or against a limit they can set
  (`LIBREFOLIO_STORAGE_LIMIT_MB` sets it from the environment).

## Lessons
- **`core.ignorecase` hid a test file.** The repository had `core.ignorecase=true` (inherited from a Mac checkout).
  A test file `backupList.test.ts` and a different file `BackupList.test.ts` were confused by Git, and `git status`
  did not show the difference: the file was registered in the runner but never committed, and one frontend category
  went red only in the consolidated run. See [[problems/core-ignorecase-hides-a-test-file]].

## Source files
| Role | Path |
|------|------|
| Backup API | `backend/app/api/v1/backup/` |
| Backup command line | `scripts/backup_cli.py` |
