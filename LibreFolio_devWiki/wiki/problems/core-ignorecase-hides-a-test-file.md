---
title: "`core.ignorecase=true` made Git confuse `backupList.test.ts` with `BackupList.test.ts`, and `git status` said nothing"
category: problem
status: resolved
date: 2026-11-05
tags: [git, test-runner, case-sensitivity, release-trains]
related: [decisions/backups-kept-in-backups-folder, problems/git-merge-stash-failed-on-locked-index]
---

# Problem: a registered test that was never committed

## Symptom
In the consolidated run of the release candidate one frontend category failed (`component-unit`), while the same
category was green when run alone on the branch that made the test. The test file was registered in the runner but
missing from the merged tree.

## Cause
The repository had `core.ignorecase=true`, inherited from a Mac checkout. Two files whose names differ only by case,
`backupList.test.ts` and `BackupList.test.ts`, were one path for Git, so the new file was never staged and
`git status` showed nothing wrong. On Linux (a case-sensitive file system) they are two files.

## Fix
- The test was renamed to a name that does not differ by case (`backupListSignal.test.ts`).
- `core.ignorecase` of the repository was set to `false`.

## Prevention
- On a Linux or Docker checkout keep `core.ignorecase=false`; check it with `git config core.ignorecase`.
- Never name two files in one folder with names that differ only by case.
- When a category is green alone and red in the consolidated run, compare the file list of the branch with the
  merged tree before looking for a race.
