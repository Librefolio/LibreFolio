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

- **One frozen version** (`47c505081`): right after the checkout the workflow writes `LF_APP_VERSION` from `VERSION`,
  and Vite shows it when it is set, asking git only otherwise.
- **The tree checked**: four «[CHECK] Checkout after …» steps run `scripts/ci/warn_if_tree_changed.sh`, which warns
  when a step has changed tracked files.
- **No needless rewrite**: the icons are redrawn only when the logo's hash changes (`c7c372fd3`,
  `frontend/generated-icons.json`).
- The image does not build the frontend: it copies `frontend/build/`, so it shows the version frozen at the build.
- Tests: `test_release_image_contract.py` pins the version and a clean tree (`8752c3fab`).

*Resolved in the code; to verify on the first nightly after the push.* Left in the backlog: M-25 (low) — a local
`dev.py docker build` can reuse a frontend built for another version.

*Verified on 2026-10-13* (the coordinator): the first pipeline after the push, run 77 on the merge of PR #42 into
`main` (commit 6fd90d7ee), reports `v1.1.0-1648-g1ee978788` — `git describe` of that merge — without `-dirty`.
The developer's question 11 is closed.

*2026-11-07 lint*: M-25 is closed too — CP7a of workstream H (`bf6fd84ae`, in `dev_release2` with `934f09dba`, 19/10):
`_docker_ensure_assets_built()` freezes the version once, writes it to `frontend/build/.build-version`
(`FRONTEND_BUILD_VERSION_MARKER` in `dev.py`), and rebuilds a frontend of another version. The backend side of the
same family, a leftover `VERSION` in a checkout, was fixed by `50f9faaa6`
([[problems/stale-version-file-shadows-git-describe]]).

## Source files

| Role | Path |
|------|------|
| The frontend's version (`git describe --tags --always --dirty`) | `frontend/vite.config.ts` |
| The workflow, and the frozen `VERSION` for the image | `.github/workflows/release.yml` |
| The backend's version | `backend/app/utils/runtime/version.py` |
| The tree check | `scripts/ci/warn_if_tree_changed.sh` |
| The icons' record | `frontend/generated-icons.json` |
| The release image's contract tests | `backend/test_scripts/test_utilities/test_release_image_contract.py` |
