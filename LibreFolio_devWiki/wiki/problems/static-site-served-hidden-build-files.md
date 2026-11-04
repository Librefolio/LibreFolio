---
title: "The static site served the build's hidden files: `/.build-debug`, `/.build-version`, `/.tool-contract-inputs`"
category: problem
status: resolved
date: 2026-10-17
tags: [security, static-site, frontend-build, information-disclosure, starlette, workstream-h, release-1.3]
related:
  - problems/frontend-build-looked-stale-for-files-it-never-bundles
  - decisions/single-docker-image
---

# Problem: every route that serves files by path served dotfiles too

## Summary

The SPA catch-all (`frontend_catchall()`, `backend/app/services/platform/static_site.py`) served any file of
`frontend/build/` that the request path named, once confined inside the build: hidden files included. `GET /.build-debug`
told whether the build was a debug one, `GET /.build-version` gave the version (already public), the new
`/.tool-contract-inputs` would have answered too, and so did `/fonts/noto-color-emoji/.cache_manifest.json`, which the
app never requests. The `/_app` mount and `/mkdocs` had the same gap. There were no hidden files there, but on a
developer's Mac the Finder can add a `.DS_Store` at any moment. Found while designing the record of
[[problems/frontend-build-looked-stale-for-files-it-never-bundles]] (H-28, 17/10), finished as H-29.

## Details

- **H-28, the catch-all.** `_hidden_in_build(target)`: a path whose resolved location below the resolved build has a
  name starting with `.` gets the SPA fallback (`200.html`, else `index.html`), like a path leaving the build. Dot
  segments are resolved first: `/assets/../favicon.png` is still served, `/assets/../.build-debug` is refused. A build
  folder swapped since `confined_path()` resolved the path counts as hidden: the fallback, never a 500.
- **H-29, the other two routes.**
  - The check became `_hidden_below(root, target)`, shared.
  - `ImmutableStaticFiles.get_response()` (the `/_app` mount) answers a hidden name with Starlette's
    `HTTPException(404)`, exactly what a missing file gets. The path is already normalised by `get_path`, so no `..` is
    left to read as a hidden name.
  - `mkdocs_static()` answers with the documentation's 404.
- **Why each route answers differently**: each answers a hidden file the way it answers a file it does not have.
  For the catch-all that is the SPA fallback.
- **A test that assumed the opposite.** `utils nosniff-content-types` samples one file per extension of the real build;
  for «(no extension)» it had picked `.build-debug` and expected it served. Triage verdict: *assumption*, not defect.
  Its sampler now skips hidden files.

## Solution

Real check on a lane server (17/10): `/.build-debug`, `/.tool-contract-inputs`,
`/fonts/noto-color-emoji/.cache_manifest.json` and `/assets/../.build-debug` (`curl --path-as-is`) answer
`200 text/html` with `200.html`; `/robots.txt` and `/manifest.json` are still served with their own types. The H-29
routes are proved in process on a fresh app built with `install_static_site()`, with raw ASGI requests through the real
Starlette mount.

## Prevention

- A route that serves files by path checks the hidden names below its root, as it checks confinement.
- A bookkeeping file kept in a served folder starts with `.`, so that rule covers it.
- A test that samples a real build skips what no route serves.

## Impact

Information only (debug or production build, version, the listing of the Tool codegen inputs); no user data. A line
in the 1.3 CHANGELOG under «Fixed».

## Source files

| Role | Path |
|------|------|
| `_hidden_below()`, `_hidden_in_build()`, the catch-all, the `/_app` mount, `mkdocs_static()` | `backend/app/services/platform/static_site.py` |
| Confinement and hidden-file tests (raw ASGI, fresh app for `/_app`) | `backend/test_scripts/test_utilities/test_static_route_confinement.py` |
| The sampler that no longer takes a hidden file | `backend/test_scripts/test_utilities/test_nosniff_content_types.py` |
| What each route serves («Server Startup») | `mkdocs_src/docs/developer/architecture/overview.md` |
| The lots (H-28, «H-29 e H-30») and the real check | `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md` |
