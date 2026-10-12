---
title: "The release shots of 1.1 show `v1.1.0-dirty` in the sidebar: Vite stamps the version with `git describe --dirty`, after the workflow has written tracked files"
category: problem
status: open
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

## Status

Open: workstream M is curing it in its lot 34. This page will be updated when the cure enters `dev_release2`.

## Source files

| Role | Path |
|------|------|
| The frontend's version (`git describe --tags --always --dirty`) | `frontend/vite.config.ts` |
| The workflow, and the frozen `VERSION` for the image | `.github/workflows/release.yml` |
| The backend's version | `backend/app/utils/runtime/version.py` |
