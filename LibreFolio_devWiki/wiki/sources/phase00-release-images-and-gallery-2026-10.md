---
title: "Phase 0 / 27 — the release images, the translated code blocks and the release pipeline with its gallery (workstream M)"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/
tags: [phase0, release2, workstream-m, release, docker, gzip, gallery, playwright, translation, pdf, ci]
related:
  - decisions/release-image-tags-latest-light
  - problems/release-images-shipped-debug-frontend
  - decisions/http-gzip-in-the-app
  - decisions/gallery-is-a-release-gate-with-real-data
  - problems/playwright-favicon-aborted-by-routes
  - decisions/pdf-preview-viewer-only-local-assets
  - problems/translation-cleanup-flattened-code-indent
  - sources/phase00-translation-round12-2026-10
---

# Source: Phase 0 / 27 — release images, gallery and pipeline

## Summary

Folder 27 holds four plans of workstream M, written from 2026-10-06 to 10-12. This page covers the first three; the
fourth, the 1.2 translation round, has its own page ([[sources/phase00-translation-round12-2026-10]]). They start
from the cloud sizing study, which found two release blockers in the published images, and end with a release
pipeline whose gallery is a gate and whose screenshots come from real data, offline.

| File | Dates | What it adds |
|------|-------|--------------|
| `plan-phase00ReleaseImages.prompt.md` | 2026-10-06 → 10-07 | The images (a production frontend, a full image that really carries the screenshots), HTTP compression, the Tailscale watchdog, the test-startup timeout |
| `plan-phase00TranslatedCodeIndent.prompt.md` | 2026-10-06 | The translation clean-up that flattened code blocks: the fix, the `code-block-indent` check, the repair of the pages the next alignment would not translate |
| `plan-phase00ReleaseGallery.prompt.md` | 2026-10-07 → 10-10 | R12: the gallery repairs and gate, `latest` on the light image, the prerelease rules, then batches 5–12 — the shots of the 1.2 pages, reduced motion, tall screens, the offline guard, the PDF preview, the translation round's launch |

## Key Takeaways

- **The images were not what they claimed** (2026-10-06): a debug frontend in both, and a full image identical to
  the light one. A guard stage in the Dockerfile and two rebuilds after the gallery fixed both; the proof was a size
  difference equal to the screenshot bytes ([[problems/release-images-shipped-debug-frontend]]).
- **`latest` is the light image** — the developer's choice, then written into the workflow with three prerelease rules
  ([[decisions/release-image-tags-latest-light]]).
- **The app compresses its responses**: a first visit −63 %, a warm session −84 % ([[decisions/http-gzip-in-the-app]]).
- **The Tailscale watchdog** went into the admin guide (step 6): «Sì, M porta lo script nella guida adesso». The
  supervised `custom_startup.sh` (`194bb438a`) was tested on the developer's two containers, and the compose examples
  gained Tailscale's health check, in all four languages.
- **One startup timeout** (step 8): the Python runner and `playwright.config.ts` both read
  `LIBREFOLIO_TEST_STARTUP_TIMEOUT`, 300 s by default and no longer different on CI; a test proves the two agree.
- **The translation pipeline flattened code blocks**, a broken YAML compose included
  ([[problems/translation-cleanup-flattened-code-indent]]).
- **The gallery became a gate, with rules for its data** — no invented fixture, disposable accounts, no network,
  reduced motion, screens as tall as their subject ([[decisions/gallery-is-a-release-gate-with-real-data]]). Two
  traps of Playwright 1.61 surfaced: favicon URLs aborted by any route
  ([[problems/playwright-favicon-aborted-by-routes]]), and probes that ignore their timeout
  ([[problems/playwright-probes-ignore-timeout]], in the translation round's plan).
- **The PDF preview became a viewer**, serving its own engine and fonts, and a fallback loop as old as v1.1.0 was
  found and fixed on the way ([[decisions/pdf-preview-viewer-only-local-assets]]).
- **A red that passed on retry** (batch 12, step 25): resizing the window makes the header show itself, and the shared
  gallery helpers scrolled before the page had handled the resize. The verdict was a test assumption, not a product
  defect: `galleryRiskLab.ts` now waits for the resize and for two rendered frames, as the PAC helpers already did.
- **Defects seen in the shots** were routed rather than fixed in place, for example an untranslated column header and
  an unlocalised percentage in `DistributionEditor.svelte` (batch 12, step 26).

## Pages created from this source

- [[problems/release-images-shipped-debug-frontend]]
- [[decisions/release-image-tags-latest-light]]
- [[decisions/http-gzip-in-the-app]]
- [[problems/translation-cleanup-flattened-code-indent]]
- [[decisions/gallery-is-a-release-gate-with-real-data]]
- [[problems/playwright-favicon-aborted-by-routes]]
- [[decisions/pdf-preview-viewer-only-local-assets]]

Pages updated: [[features/F-074]], [[features/F-062]], [[features/F-050]], [[features/F-070]],
[[concepts/ci-release-pipeline]].

## Commits

| Commit | Date | What |
|--------|------|------|
| `dda56c9e1` | 2026-10-06 | Production frontend, real light and full images |
| `16238e220` | 2026-10-06 | gzip HTTP responses |
| `194bb438a` | 2026-10-06 | The supervised Tailscale startup script |
| `5fa0cf12a` | 2026-10-06 | Code indentation kept in translations |
| `ea63cd029` | 2026-10-07 | The gallery gate; the light image is `latest` |
| `073ac30b2` | 2026-10-07 | Release tags must match the release kind |
| `c80508be8` | 2026-10-07 | Six gallery scenarios repaired, the fresh dashboard fixture |
| `73680c052` | 2026-10-08 | Onboarding shots and the offline guard |
| `d7481a7e7` | 2026-10-09 | Tall screens for long subjects |
| `02ae0e09d` | 2026-10-09 | Reduced motion for every shot |
| `32d62640f` | 2026-10-09 | The PDF preview's render state |
| `1028a1978` | 2026-10-09 | The local, viewer-only PDF preview |

## Source files

| Role | Path |
|------|------|
| Plan: release images | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseImages.prompt.md` |
| Plan: translated code blocks | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslatedCodeIndent.prompt.md` |
| Plan: release pipeline (R12) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseGallery.prompt.md` |
| Release workflow | `.github/workflows/release.yml` |
| Gallery spec | `frontend/e2e/gallery.spec.ts` |
| Tailscale startup script | `mkdocs_src/docs/static/tailscale-guide/custom_startup.sh` |
| Startup timeout (Playwright side) | `frontend/playwright.config.ts` |
| Startup timeout (runner side) | `scripts/test_runner/_server.py` |
| Header-resize wait | `frontend/e2e/fixtures/galleryRiskLab.ts` |
