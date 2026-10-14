---
title: "Remotion Video Promo"
category: "entity"
tags: ["video", "promo", "remotion", "react", "i18n"]
related: ["source-code-v0.9.0-batch", "gallery-is-a-release-gate-with-real-data"]
---

# Remotion Video Promo

> **Moved out of the repository (2026-10-14).** The video project now lives in the project's business repository,
> folder `media/video/`, together with its render, its AI assets and the local copies of third-party pages it used.
> `./dev.py mkdocs video` is gone. The history was not rewritten: `mkdocs_src/videoClipPrject/` is still in the
> commits from `484acf88b` (June 2026) up to the removal, and in the tags v0.9.0 to v1.2.0.

## Context
A programmatic video generation project bootstrapped to create promotional material for LibreFolio.

## Details
- From June 2026 to 2026-10-14 it lived in this repository, in `mkdocs_src/videoClipPrject/video_promo`.
- Built using **Remotion** (React-based programmatic video creation).
- Supports multi-language (i18n) rendering to generate promos in EN, IT, FR, ES.
- Uses AI-generated assets (audio tracks, background images, SFX) stored in the `public/ai/` folder.
- Divided into composable scenes (Hook, Hero, MultiAsset, Import, Mobile, OpenSource, CTA).

## The link that stays with this repository
The video's `scripts/sync-assets.ts` still reads this repository's documentation: the gallery screenshots
(`mkdocs_src/docs/gallery/`, by the names in its own gallery manifest) and the static files (`mkdocs_src/docs/static/`).
It finds them through `LIBREFOLIO_MKDOCS_SRC`, the `mkdocs_src` folder of a LibreFolio checkout, with the usual local
layout as the default. Moving those folders or renaming a screenshot breaks the video's sync, and no test in this
repository sees it: the sync runs in the other one.

## Source files
| Role | Path |
|------|------|
| The screenshots the video syncs | `mkdocs_src/docs/gallery/` |
| Their producer | `frontend/e2e/gallery.spec.ts` |
| The static files it syncs | `mkdocs_src/docs/static/` |
