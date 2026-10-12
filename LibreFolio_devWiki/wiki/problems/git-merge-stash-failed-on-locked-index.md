---
title: "`git merge` died with «stash failed» on the main checkout: Git 2.53 runs `git stash create` before every real merge, and an IDE or a watcher held `index.lock`"
category: problem
status: resolved
date: 2026-10-12
tags: [git, merge, index-lock, stash, ide, fsmonitor, release-trains, coordination, workaround]
related:
  - problems/fast-forward-blocked-by-a-dirty-file
  - decisions/plugin-folders-and-split-i18n
---

# Problem: a merge that dies before it starts

> Filed at the train-71 ingest (2026-10-12) from the coordinator's report, with the mechanism checked in Git's own
> sources at v2.53.0, the version on the developer's machine.

## Symptom

Train 71 merged U's lot into `dev_release2` on the main checkout (U-2, about 26 thousand lines touched), then stopped:
the next `git merge` died with `fatal: stash failed`. It died before starting: no `MERGE_HEAD`, no conflict,
nothing to undo. A clean clone ran the same merge without an error.

## Root Cause

- **A real merge always stashes first.** Before trying a strategy, a merge that is not a fast-forward calls
  `save_state()` (`builtin/merge.c:1784`): «Stash away the local changes so that we can try more than one and/or
  recover from merge strategies bailing while leaving the index and working tree polluted». `save_state()` runs
  `git stash create` as a child process (l. 356) and dies with «stash failed» when the child fails (l. 366).
- **`git stash create` writes the index.** `do_create_stash()` refreshes and writes it
  (`repo_refresh_and_write_index`, `builtin/stash.c:1450`), so it needs `index.lock`. On the main checkout other
  processes take that lock too: by the coordinator's diagnosis, PyCharm and the app's fsmonitor daemons. When one of
  them holds it, the child fails, and the merge with it.
- **Nothing is written before.** The merge dies before any strategy runs, so there is no merge state to abort. A clone
  that no IDE or watcher reads has no one to race for the lock.

## Solution — a workaround

The coordinator resumed with train 71b, whose merge step retries up to 5 times when the merge dies before starting.
Train 71 then integrated (`c57acf510`, gates green). The retry lives in the coordinator's train script, outside the
repository: nothing in the code changed.

## Prevention

- **A «stash failed» that leaves no `MERGE_HEAD` is a race for the index lock, not a conflict**: retry. There is
  nothing to `--abort` or reset, and the files are as they were.
- Tell it from a real stop: a conflict leaves `MERGE_HEAD` and conflict markers; this leaves neither.
- A merge run where no IDE or watcher reads the index (a clean clone, as here) avoids the race altogether. The other
  train-time obstacle on a shared checkout is a dirty file — [[problems/fast-forward-blocked-by-a-dirty-file]].

## Source files

| Role | Path |
|------|------|
| The coordinator's merge procedure (the retry is not in it) | `.github/agents/release-coordinator.agent.md` |
| Git 2.53.0: `save_state()` and its call | [builtin/merge.c](https://github.com/git/git/blob/v2.53.0/builtin/merge.c#L341-L366), [l. 1784](https://github.com/git/git/blob/v2.53.0/builtin/merge.c#L1784) |
| Git 2.53.0: `git stash create` writes the index | [builtin/stash.c](https://github.com/git/git/blob/v2.53.0/builtin/stash.c#L1429-L1450) |
