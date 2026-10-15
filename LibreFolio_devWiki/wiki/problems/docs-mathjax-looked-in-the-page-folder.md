---
title: "The documentation looked for its local MathJax in the page's own folder: every nested page fell back to jsDelivr, and showed no formulas offline (M-19)"
category: problem
status: resolved
date: 2026-10-12
tags: [docs, mkdocs, mathjax, offline, javascript, privacy, third-party, docker, workstream-m, release-1.2]
related:
  - features/F-069
  - features/F-062
  - decisions/gallery-is-a-release-gate-with-real-data
  - sources/phase00-translation-round12-2026-10
---

# Problem: formulas that needed the internet

## Symptom

During the live preview of batch 23 (2026-10-12), M saw in the server log that the local copy of MathJax answered
404 on nested pages: `/LibreFolio/javascripts/vendor/mathjax/tex-mml-chtml.js` 200, but
`/LibreFolio/it/user/brokers/javascripts/vendor/mathjax/tex-mml-chtml.js` 404. Online, the formulas still showed —
loaded from jsDelivr, a third party, on every page with formulas. Offline, as in the full Docker image that is meant to
carry the whole documentation, they did not show at all. The defect was already in 1.0 and 1.1: `lib-loader.js` had
not changed since `7b36569c3` (2026-02-06).

## Root Cause

`mkdocs_src/docs/javascripts/lib-loader.js` built the path of the local copy (`javascripts/vendor/mathjax/…`, at the
site's root) from the page's `<base>` element. Material for MkDocs emits none, and the backend serves the docs files as
they are, so the base fell back to the page's own folder: right on the home page, wrong one level down and below.

## Solution

`8d47c28c0` («fix(docs): load local MathJax on nested pages», batch 24): the script reads its own address once, while
it runs (`document.currentScript`, null afterwards), and `getBasePath()` returns everything before
`/javascripts/lib-loader.js` in it — the site's root, whatever the page's depth, its language folder or the path the
site is served at. `<base>` and the page's folder stay as fallbacks.

Proved offline, with every host but the site refused: 34 pages of 34 — 16 pages with formulas, one per language and
depth (2 to 6 folders), plus the root, served both under `/mkdocs/` (the backend) and under `/LibreFolio/` (GitHub Pages
and `mkdocs serve`) — load the local copy and draw every formula, with no request to jsDelivr. The CHANGELOG of 1.2
carries the fix under «Formulas show in the documentation without internet».

## Prevention

- A page-relative path in the docs' JavaScript is wrong on every nested page: derive it from the script's own
  address, which MkDocs always links from the site's root.
- **A test pins it since train 70.** When the fix landed, none did: the e2e specs that open the documentation checked
  only the address a guide link opens. M proposed `frontend/e2e/layout/docs-offline-math.spec.ts` — a nested page with
  formulas, in English and Italian, every other host refused, `mjx-container` drawn — for test-author, once the shared
  runner file was assigned.
- **Follow-up (batch 25)**: writing that spec found the local copy had no fonts, so formulas drew in the page's font —
  [[problems/mathjax-fonts-missing-from-local-copy]]. The spec, extended to the font faces, waited outside the
  repository for the runner file.
- *Update (train 70)*: the spec is registered, copied byte for byte, as `front-utility docs-offline-math`
  (`0fe5195e8`, M's batch 28), once the coordinator had assigned M the runner file after T's CP1 of M-18. M's run:
  2 passed (English and Italian), and `check-orphans` clean, 110 of 110 e2e specs registered. A red names the place:
  a 404 under the page's own folder is M-19 back, a 404 at the root is a copy the site does not have.

## Still open — M-21

A local site does not pick up a change like this one. `dev.py` rebuilds `mkdocs_src/site` only when a `.md` is newer
than `site/index.html` (`auto_build_mkdocs()` for `dev.py server`, and the same check in `_docker_ensure_assets_built()`
for `dev.py docker build`), so a change to `lib-loader.js` or `extra.css` alone leaves an existing site as it was. CI
builds the site from scratch, so published images are not affected; a local server or image needs
`dev.py mkdocs build` first. Backlog M-21 (low; `dev.py` is shared, so not M's to change).

## Source files

| Role | Path |
|------|------|
| Loader (`getBasePath`, `document.currentScript`) | `mkdocs_src/docs/javascripts/lib-loader.js` |
| Regression spec (`front-utility docs-offline-math`) | `frontend/e2e/layout/docs-offline-math.spec.ts` |
| Its registration in the runner | `scripts/test_runner/_frontend_utility.py` |
| Docs rebuild check (`auto_build_mkdocs`) | `dev.py` |
| How the backend serves the docs | `backend/app/services/platform/static_site.py` |
| Journal (§14.6, §15) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
| Backlog (M-19, M-21) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
