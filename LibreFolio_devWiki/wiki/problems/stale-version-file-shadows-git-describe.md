---
title: "A leftover VERSION file freezes the version a development host reports: it is read before git describe and nothing removes it"
category: problem
status: resolved
date: 2026-09-22
tags: [backend, version, docker, update-check, git, design, release]
related:
  - features/F-062
  - problems/release-shots-show-dirty-version
  - concepts/ci-release-pipeline
  - sources/phase00-feedback-jobs-2026-09
---

# Problem: the version that stopped moving

## Symptom

During the developer's visual review on the production server (2026-09-22, item R2 of folder 09), the app reported
`v1.0.1-97-g98efa725-dirty` while git said `v1.1.0-224-…`, and the update check compared that stale value with
`1.1.0`. The review notes that the update modal's own items R3 and R4 had to be fixed after R2, since the wrong version
changes their flow.

## Root Cause

`get_git_version()` (`utils/runtime/version.py`) returns the content of the root `VERSION` file, when it exists,
before trying `git describe` — on purpose, because the Docker image has no `.git/`. The file is written only by
`dev.py docker build`, which first deletes any stale copy, so the image is right. But `VERSION` is git-ignored and
nothing else removes it: a copy left on a development or self-built host freezes the reported version there.

## Solution

At filing, not fixed: the README of folder 09 (2026-10-09) keeps R2 open as a design defect, and the code still prefers the file.
Possible directions — trusting `VERSION` only inside the container, or comparing it with `git describe` when `.git/`
exists — are not decided.

2026-11-07 lint: fixed on 15/10 by `50f9faaa6` («fix(version): git describe wins in a checkout»). When `.git` exists in
the project root (a folder, or a file in a worktree or submodule), `get_git_version()` runs `git describe` first; the
`VERSION` file counts only without `.git`, or when `git describe` fails. `LF_APP_VERSION`, frozen by the release
workflow, comes before both ([[problems/release-shots-show-dirty-version]]). Tests: `test_version.py`.

## Prevention

Before `50f9faaa6`: after a local `dev.py docker build`, delete `VERSION` from the checkout before running the server
from source. Since then no clean-up is needed in a checkout; a source tree without `.git` still trusts `VERSION`.

## Source files

| Role | Path |
|------|------|
| `get_git_version()` | `backend/app/utils/runtime/version.py` |
| Writes and refreshes `VERSION` before a Docker build | `dev.py` |
| `frozen_app_version()` (`LF_APP_VERSION`) | `backend/app/config/platform.py` |
| Tests of the order (frozen, git describe, VERSION) | `backend/test_scripts/test_utilities/test_version.py` |
| Journal (the visual review, R2) | `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/08_review_visiva_20260922.md` |
