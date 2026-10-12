---
title: "A fast-forward refused over a locally modified file, and how to get past it without a Git write"
category: problem
status: resolved
date: 2026-10-12
tags: [git, worktree, fast-forward, coordination, workstreams, merge-file, release-trains]
related:
  - concepts/runtime-lanes
  - sources/phase00-translation-round12-2026-10
---

# Problem: the coordinator cannot fast-forward a worktree with a dirty shared file

> Written from workstream M's note for the devWiki (batch 25, 2026-10-12).

## Symptom

During batch 25, workstream M had a local, uncommitted change to the shared backlog
(`LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md`) when the coordinator fast-forwarded M's branch
to `0afac8e14` (train 64): 103 incoming files, and one overlap — the backlog, where the target had added its own hunks
and workstream V 67 lines above and below M's section. Git refused the fast-forward, although the two sets of hunks
were disjoint.

## Root Cause

Git refuses to update a working-tree file that has local modifications when the incoming commits change it too,
whatever the hunks. Workstreams may not commit, stash, reset or rebase themselves — history-mutating commands belong to
the developer and the coordinator — so the usual ways out are closed.

## Solution

What worked, with no Git write by the workstream:

1. save the local version of the file outside the repository;
2. set the worktree file back to HEAD's content (`git show HEAD:<path> > <path>`);
3. let the coordinator fast-forward;
4. run `git merge-file -p mine base theirs` on **copies** — base being the old HEAD's version — and check that each
   side's difference survives exactly;
5. copy the result back.

## Prevention

Keep shared files — the backlog above all — out of a workstream's uncommitted changes when a train is due, or hand
the change to the coordinator first. When it happens anyway, the five steps above keep both sides without touching
history.

## Source files

| Role | Path |
|------|------|
| The shared file of the case | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Journal (batch 25) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` |
