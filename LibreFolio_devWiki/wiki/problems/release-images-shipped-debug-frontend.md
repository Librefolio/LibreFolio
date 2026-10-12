---
title: "The release images shipped a debug frontend, and the full image was the light one: the gallery rebuilt the frontend in debug mode, and the docs site was built before the screenshots existed"
category: problem
status: resolved
date: 2026-10-06
tags: [ci, release, docker, frontend, build, sourcemaps, gallery, mkdocs, light-image, workstream-m, release-1.2]
related:
  - concepts/ci-release-pipeline
  - decisions/release-image-tags-latest-light
  - decisions/http-gzip-in-the-app
  - decisions/single-docker-image
  - features/F-062
  - features/F-074
  - sources/phase00-release-images-and-gallery-2026-10
---

# Problem: the published images were not what they claimed

## Symptom

The cloud sizing study of workstream M (its report, items 1 and 7) measured the 1.1 release images:

- the frontend inside the image weighed **58 MB instead of 21 MB**, with 103 `.map` files: a debug build, not
  minified and with sourcemaps;
- the **full** image, the one meant to carry the documentation screenshots for offline use, was **identical to the
  light one**: it had no screenshots either, and loaded them from the online site like the light variant.

## Root Cause

Two ordering faults in `.github/workflows/release.yml`, both invisible in a green run:

1. **The gallery left a debug build behind.** The release ran `dev.py front build` (production), then the gallery. The
   gallery's Playwright webServer is `dev.py server --test`, which forces debug mode and rebuilds `frontend/build/`
   without minification and with sourcemaps. Both `docker build` steps then copied that directory as it was.
2. **The docs site was built before the screenshots.** CI built the MkDocs site before the gallery and never rebuilt
   it, so the PNGs never reached `site/gallery/`. The full image shipped the site as built; the light one deleted
   screenshots that were not there.

## Solution

M's commit `dda56c9e1` (2026-10-06, «fix(docker): production frontend, real light/full»), with the journal in
`810bab323`:

- **A guard stage.** The Dockerfile's `frontend` stage runs `scripts/docker/check_frontend_build.sh` on the build it
  copies. The image fails unless `index.html` and `200.html` (the SPA fallback) exist, the `.build-debug` marker that
  `dev.py front build` writes is not `1`, there is no `.coverage-instrumented` marker and no `*.map` file. A missing
  marker with no sourcemaps only warns.
- **Two rebuilds after the gallery.** A production `front build`, then `mkdocs build` again (`id: rebuild-mkdocs`),
  so the full image carries the screenshots.
- **`.dockerignore`** stops stale nested `.pyc` files from reaching the context.

The proof, without publishing (plan, step 4):

- the full `docker build` with a debug frontend **fails in 10 s** at the frontend stage, with the guard's message;
- with the new order, both images carry a production frontend (marker 0, no maps, 21.2 MB);
- Docker's image size, full minus light = **2,961,040 bytes, exactly the bytes of the 32 test screenshots**;
- extrapolated to the whole gallery: full ≈ 1.95 GB unpacked (≈ 0.78 GB compressed), light ≈ 1.59 GB (≈ 443 MB).

## Prevention

- `./dev.py test utils release-image-contract` (`test_release_image_contract.py`) pins the order of the steps: a
  production frontend build and a docs build between the gallery and the images.
- `test_check_frontend_build.py` runs the guard script under `sh` on build trees made in the test, as the Docker stage
  does: each rejected case exits 1, a production build exits 0.
- The gallery became a release gate the next day ([[decisions/gallery-is-a-release-gate-with-real-data]]), so the
  rebuilt site can no longer ship missing screenshots.
- The same plan added HTTP compression to the app ([[decisions/http-gzip-in-the-app]]).

## Source files

| Role | Path |
|------|------|
| Guard script | `scripts/docker/check_frontend_build.sh` |
| `frontend` stage | `Dockerfile` |
| Rebuild steps after the gallery | `.github/workflows/release.yml` |
| Build context exclusions | `.dockerignore` |
| Guard tests | `backend/test_scripts/test_utilities/test_check_frontend_build.py` |
| Step-order contract | `backend/test_scripts/test_utilities/test_release_image_contract.py` |
| Build-mode marker (`FRONTEND_BUILD_MODE_MARKER`) | `dev.py` |
| Developer page («Documentation Checks, Gallery and Rebuilds») | `mkdocs_src/docs/developer/docs/release-pipeline.md` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseImages.prompt.md` |
