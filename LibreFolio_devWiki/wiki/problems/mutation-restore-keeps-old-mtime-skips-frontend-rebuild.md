---
title: "A mutation restored with its old file time (`cp -p`) skips the frontend rebuild: the «final green» E2E runs on the mutated bundle"
category: problem
status: resolved
date: 2026-10-15
tags: [testing, test-runner, frontend-build, mutation-testing, playwright, mtime, workstream-b, release-1.3]
related:
  - problems/shared-server-rebuilt-the-frontend-past-its-startup-timeout
  - problems/front-check-does-not-check-what-you-think
---

# Problem: restoring a mutated source can leave the mutated build in place

## Summary

The E2E runner rebuilds `frontend/build/` only when a source file is **newer** than `build/index.html`. A mutation test
that edits a product file forces a rebuild, as it should; but restoring the original with its **old** modification time
(`cp -p`, `rsync -t`, `git show … > file` followed by `touch -r`, an editor that keeps times) makes every source look
older than the mutated build, so the next run skips the rebuild and tests the mutated bundle. A «final green run on the
restored code» then proves nothing: it can even pass or fail for the wrong reason.

## Details

- `check_frontend_needs_build()` (`scripts/cli_base.py`) compares `st_mtime` of the sources with
  `build/index.html`; `_ensure_frontend_build()` (`scripts/test_runner/_frontend_common.py`) builds only when it says so.
- Found by test-author while proving the mutations of the Backup tab E2E (workstream B, lot B5a, 2026-10-15): each
  mutation of `BackupDownloadCard.svelte` and `backupJob.svelte.ts` rebuilt the frontend (130–155 s); the restore was
  done with a plain `cp`, which gives the file a fresh time, so the final run rebuilt again and really tested the
  committed code. With `cp -p` it would not have.
- Byte identity (sha256) of the restored source is necessary but not sufficient for the E2E: the bundle is a second
  copy of the code, keyed on time, not on content.

## Solution

Restore a mutated frontend file **without** keeping its old time: plain `cp`, or `touch` the restored file. Then let the
final run rebuild, and check the run's log for the rebuild step (or compare the bundle's time with the restore's).

## Prevention

- In every mutation protocol that runs E2E: restore with a fresh file time, and require the final run to show a rebuild.
- When an E2E result looks impossible after a restore, check `build/index.html`'s time first: the bundle may be older
  code than the tree.

## Source files

| Role | Path |
|------|------|
| Staleness check (source times against the built index page) | `scripts/cli_base.py` |
| The runner's build step before an E2E | `scripts/test_runner/_frontend_common.py` |
| The E2E whose mutations surfaced it | `frontend/e2e/settings/backup.spec.ts` |
