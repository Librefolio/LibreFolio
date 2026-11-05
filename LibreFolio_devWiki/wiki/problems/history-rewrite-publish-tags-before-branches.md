---
title: "After a history rewrite, publish the tags first and the branches second"
category: problem
status: resolved
date: 2026-11-05
tags: [git, history-rewrite, ci, nightly, tags, backups]
related: [problems/stale-version-file-shadows-git-describe]
---

# Problem: a nightly build that ran before the rewritten tags arrived

## Context
The repository history was rewritten (`dev_release2` took new SHAs; the old ones no longer exist). Branches and tags
were force-pushed one after the other.

## Symptom
Every forced push of the development branch started the nightly build before the rewritten tags had arrived. The
build computed its version from `git describe`, found no tag it could reach, and produced a nightly with the version
`v0.0.0-g<sha>`. There was no permanent damage, but a nightly with a wrong name was published.

## Lessons
1. **Tags first, branches second.** Push the rewritten tags, check them on the remote, then push the branches.
2. **Every SHA quoted before the rewrite is invalid afterwards**; say the date of the rewrite wherever old SHAs
   remain in a document.
3. **Record HEAD and `git status --porcelain` before the operation, and verify HEAD, parents and cleanliness after
   it**; report the resulting SHAs.
4. A SHA written in a plan before the rewrite does not resolve any more; look the commit up by its message.
