---
title: "The local MathJax had no fonts: once nested pages used it, every formula fell back to the page's font — a vendored library must carry its companions"
category: problem
status: resolved
date: 2026-10-12
tags: [docs, mkdocs, mathjax, fonts, vendoring, offline, cache, mermaid, workstream-m, release-1.2]
related:
  - problems/docs-mathjax-looked-in-the-page-folder
  - features/F-069
  - features/F-062
  - sources/phase00-translation-round12-2026-10
---

# Problem: the script came without the fonts it loads

> Written from workstream M's note for the devWiki (batch 25, 2026-10-12), checked against the code at `b91d6d902`.

## Symptom

Writing the regression spec for M-19 ([[problems/docs-mathjax-looked-in-the-page-folder]]), the test-author found the
formulas drawn wrong: letters upright instead of italic, fractions clipped. M proved it in a browser on
`financial-theory/fundamentals/day-count/`: with the local copy the formulas drew, but the faces `MJXZERO`, `MJXTEX`
and `MJXTEX-I` ended in `error`, with 404s on `vendor/mathjax/output/chtml/fonts/woff-v2/MathJax_*.woff`; through
jsDelivr the same faces were `loaded`. The public site of 1.1.0 had the same gap: it serves the script (200) without
its fonts (404).

## Root Cause

MathJax's CHTML output loads its fonts from `[mathjax]/output/chtml/fonts/woff-v2/`, beside the script, and the docs
vendored the script alone. It stayed invisible while nested pages fell back to the CDN; fixing M-19 alone would have
shipped degraded formulas in 1.2, in the image and on the public site. A 200 on the script proved nothing: only
`document.fonts` in a browser showed the faces in `error`.

## Solution

`92fb9c83e` («fix(docs): ship MathJax fonts with the docs»):

- **Companions** in `scripts/update_js_cache.py`: a cached `js` library lists the files it loads from beside itself.
  For MathJax the names come from the cached script's own text (`MathJax_[A-Za-z0-9-]+\.woff`, 22 files, 321 KB) and the
  address from the library's URL; they are checked on **every** run, even when the script's ETag matches (the JS path
  returns early there), and downloaded again when the script changes. A failed download keeps the cached copy, and with
  none it is a hard failure; a 200 that is not a font is refused; files the script no longer names are removed.
- **`mathjax.js`** calls `MathJax.typesetPromise()` only once it exists: Material's `document$` fired before the loader
  had loaded MathJax and threw a `TypeError` on every page.
- After `dev.py mkdocs build` the site carries the 22 fonts; the faces are `loaded` and the formulas match the CDN's.
  The Dockerfile copies the built site whole, so the fonts follow the script into the image.
- `TestCompanions` in `test_update_js_cache.py` (32 cases); three edge cases of the new code fixed on the way, each with
  a test (a cleanup that could remove the script itself, an empty `dir`, a lost manifest).

## Prevention

- **A vendored library lists its companions from its own text, and they are checked on every run** — a fresh script
  with missing companions is a broken library.
- Check what a page draws, not that a file answers 200: the M-19 spec now also checks the font answers, the MJX faces
  and the absence of `typesetPromise` errors. It is **not in the repository yet**: it waits outside it until the shared
  runner file is free, since an unregistered spec turns `check-orphans` red.
- **Still open — M-22** (medium, after 1.2): Mermaid is imported only from jsDelivr (`mermaid.mjs`), with no local copy
  and no fallback, so without internet — as in the full image — 74 pages show their diagrams as code. The cure is
  MathJax's: a copy in `vendor/` and a loader with a fallback.
- M-21 now names the vendor files too: a local `dev.py docker build` over an already-built site does not take them
  without `dev.py mkdocs build`.

## Source files

| Role | Path |
|------|------|
| Companions | `scripts/update_js_cache.py` |
| Companion tests | `backend/test_scripts/test_utilities/test_update_js_cache.py` |
| `typesetPromise` guard | `mkdocs_src/docs/javascripts/mathjax.js` |
| Loader (M-19) | `mkdocs_src/docs/javascripts/lib-loader.js` |
| Mermaid from the CDN only (M-22) | `mkdocs_src/docs/javascripts/mermaid.mjs` |
| Journal (step 8) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` |
