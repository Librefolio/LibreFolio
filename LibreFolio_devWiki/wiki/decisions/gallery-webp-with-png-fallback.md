---
title: "Documentation screenshots served as WebP, with the PNG kept as fallback on the public site"
category: decision
status: resolved
date: 2026-11-06
tags: [docs, gallery, mkdocs, docker, release, images, release-1.3]
related:
  - decisions/gallery-is-a-release-gate-with-real-data
  - concepts/ci-release-pipeline
  - problems/release-images-shipped-debug-frontend
---

# Decision: the gallery as WebP, PNG as the fallback

## Context

The full Docker image carries the documentation site with its gallery of screenshots, about 590 MB of PNG in the
documentation layer. The developer asked on 06/11/2026 to bring forward from 1.4 a lighter format. Measured on 40 random
shots: 518 MB of PNG became about 178 MB as WebP at quality 85 (0.19 s per shot), 281 MB lossless; by eye q85 cannot be
told from the PNG.

## Decision

1. **The gallery keeps writing PNG.** Playwright cannot write WebP, and `scripts/visual_review/*` read the PNGs.
2. **Conversion at the end of `dev.py mkdocs gallery`**, with Pillow, in parallel over the CPUs, at **quality 85**.
   Only a PNG without a WebP, or newer than its WebP, is converted, so a partial run (`-f`) is quick and the command can
   be run again for nothing. It runs even when the gallery fails, so the nightly goes on with the shots that succeeded.
   A WebP is written under a temporary name and renamed when complete; an unreadable PNG is reported and stops nothing.
3. **`gallery-img-loader.js` asks for `.webp`**, with the same fallback chain: this site (requested language, then
   English) as WebP, then as PNG, then the public site the same way. On one site every language is tried as WebP before
   any PNG.
4. **The public site keeps both files.** Released light images (1.2.1 for example) and the `README.md` read the `.png`
   from GitHub Pages: they must not break.
5. **The full image drops the PNGs** (`find /site/gallery -iname '*.png' -delete` in the `Dockerfile`), as the light
   image already drops every image; a release-image contract test pins it.
6. `.gitignore` ignores the WebP copies; the `playwright-screenshots` artefact stays PNG.

## Consequences

- The full image is lighter by about two thirds of the gallery's weight.
- The mkdocs instructions now give the gallery image path as `.webp`.

## Links

- Sources: `kickoff-w8.md` (lot E8) — a coordinator file kept outside the repository. Summary:
  [[sources/wave8-9-release-1.3-closing-2026-11]]
- Commits: `d710eb7e8` (conversion), `40fa6fdac` (loader), `f60c2e8fe` (Dockerfile), `0debd2c51` (developer docs).

## Source files

| Role | Path |
|------|------|
| Conversion | `scripts/gallery_webp.py` |
| Gallery command | `dev.py` |
| Loader with fallback chain | `mkdocs_src/docs/javascripts/gallery-img-loader.js` |
| Full image drops the PNGs | `Dockerfile` |
| Tests | `backend/test_scripts/test_utilities/test_gallery_webp.py`, `backend/test_scripts/test_utilities/test_release_image_contract.py` |
| Developer docs | `mkdocs_src/docs/developer/docs/release-pipeline.md` |
| mkdocs rules | `.github/instructions/mkdocs.instructions.md` |
