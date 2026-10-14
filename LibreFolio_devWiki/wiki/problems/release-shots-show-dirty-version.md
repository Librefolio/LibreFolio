---
title: "The release shots of 1.1 show `v1.1.0-dirty` in the sidebar: Vite stamps the version with `git describe --dirty`, after the workflow has written tracked files"
category: problem
status: resolved
date: 2026-10-13
tags: [release, ci, gallery, screenshots, version, git, vite, workstream-m, release-1.2]
related:
  - problems/stale-version-file-shadows-git-describe
  - decisions/gallery-is-a-release-gate-with-real-data
  - features/F-074
---

# Problem: a clean tag drawn as dirty

## Symptom

The screenshots of the 1.1 release show `v1.1.0-dirty` as the version in the sidebar, although the build ran on the
tag.

## Root Cause

The coordinator's diagnosis (2026-10-13), consistent with the code:

- the frontend takes its version at build time from `git describe --tags --always --dirty`
  (`frontend/vite.config.ts`), so any change to a tracked file in the working tree adds `-dirty`;
- the release workflow writes tracked files before the frontend is built. For the Docker image it already freezes the
  version first — `VERSION` is written «BEFORE any step that could write tracked files: `git describe --dirty` would
  otherwise stamp the image version with a spurious "-dirty"» (`.github/workflows/release.yml`) — but Vite asks git
  again, later.

## Solution

Workstream M's batch 34 (train 80):

- **One frozen version** (`741310647`): right after the checkout the workflow writes `LF_APP_VERSION` from `VERSION`,
  and Vite shows it when it is set, asking git only otherwise.
- **The tree checked**: four «[CHECK] Checkout after …» steps run `scripts/ci/warn_if_tree_changed.sh`, which warns
  when a step has changed tracked files.
- **No needless rewrite**: the icons are redrawn only when the logo's hash changes (`428bf27d1`,
  `frontend/generated-icons.json`).
- The image does not build the frontend: it copies `frontend/build/`, so it shows the version frozen at the build.
- Tests: `test_release_image_contract.py` pins the version and a clean tree (`b816adc6c`).

*Resolved in the code; to verify on the first nightly after the push.* Left in the backlog: M-25 (low) — a local
`dev.py docker build` can reuse a frontend built for another version.

*Verified on 2026-10-13* (the coordinator): the first pipeline after the push, run 77 on the merge of PR #42 into
`main` (commit 1ee978788), reports `v1.1.0-1648-g1ee978788` — `git describe` of that merge — without `-dirty`.
The developer's question 11 is closed.

## Source files

| Role | Path |
|------|------|
| The frontend's version (`git describe --tags --always --dirty`) | `frontend/vite.config.ts` |
| The workflow, and the frozen `VERSION` for the image | `.github/workflows/release.yml` |
| The backend's version | `backend/app/utils/runtime/version.py` |
| The tree check | `scripts/ci/warn_if_tree_changed.sh` |
| The icons' record | `frontend/generated-icons.json` |
| The release image's contract tests | `backend/test_scripts/test_utilities/test_release_image_contract.py` |
