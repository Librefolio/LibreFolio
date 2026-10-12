---
title: "`latest` is the light image; a release is `X.Y.Z` (full) and `X.Y.Z-light`; a prerelease is `vX.Y.Z-rc.N` and never moves `latest` or the docs"
category: decision
status: resolved
date: 2026-10-07
tags: [ci, release, docker, ghcr, tags, prerelease, light-image, github-actions, workstream-m, release-1.2]
related:
  - concepts/ci-release-pipeline
  - decisions/single-docker-image
  - problems/release-images-shipped-debug-frontend
  - features/F-062
  - sources/phase00-release-images-and-gallery-2026-10
---

# Decision: `latest` points to the light image, and only a stable release moves it

## Context

The 1.1.0 pipeline built two variants of the image, a **full** one that carries the documentation screenshots and
a **light** one without them, and both pushed `latest`: the light one won only because it was pushed second
([[concepts/ci-release-pipeline]]). On 2026-10-06 the cloud sizing study of workstream M found worse: the two
variants were identical, both with a debug frontend ([[problems/release-images-shipped-debug-frontend]]). Before
fixing the images, M asked the developer which variant `latest` should be.

## Decision

The developer (plan of the release images, §0, 2026-10-06):

- «è corretto che la latest punti anche alla light, mi torna, quello che è errato è che light e full hanno la stessa
  size con il debug attivo»;
- on the docs (O3): «fare che latest sia il tag-light è stata un ottima mossa, non ha senso fare il latest-full o
  correggere, come è ora va bene, correggiamo la guida e allineamola a questa logica».

On 2026-10-07 he confirmed it for the workflow too, through the coordinator: «Correggere il workflow: latest =
light» (plan 32, D1). M wrote it in `release.yml` the same day (`ea63cd029`), together with three rules on
prereleases:

| Rule | Developer, verbatim | Where |
|------|---------------------|-------|
| A prerelease never moves `latest` and never deploys the docs | «Sì, escluderle da latest e dal deploy della doc» | the light metadata step's `flavor: latest=…` is `auto` only for a non-prerelease release; the deploy runs only on `main` or a stable release |
| A prerelease tag is `vX.Y.Z-rc.N` | «sì al suffisso rc per le pre release, però non succede che faccio una pre release e poi promuovo, al più ne creo un'altra da 0 su un tag nuovo» | first job step |
| The check works both ways | «Sì, controllo simmetrico» | the step «Release tag must match the release kind» (`073ac30b2`): a prerelease must carry `-rc.N`, a stable release a plain `vX.Y.Z` |

The resulting tags, which the user guide's «Image Variants» table states:

| Event | Full | Light |
|-------|------|-------|
| Stable release `vX.Y.Z` | `X.Y.Z` | `X.Y.Z-light`, `latest` |
| Prerelease `vX.Y.Z-rc.N` | `X.Y.Z-rc.N` | `X.Y.Z-rc.N-light` |
| Push to `dev` | `nightly` | `nightly-light` |
| Manual run from `main` | — | `latest` |

Image tags never carry the `v` of the GitHub tag (metadata-action's `{{version}}`).

## Options Considered

1. **`latest` = full.** Rejected by the developer: the light image is the recommended default (about 450 MB to
   download), and the screenshots it lacks load from the online documentation site.
2. **`flavor: latest=true`.** Rejected in the workflow: metadata-action would add `latest` to every raw tag as well,
   `nightly-light` included. The flavor is `auto` for a stable release and `false` otherwise.
3. **Promote a prerelease to stable.** Not handled on purpose: the pipeline listens only to `published`, and the
   developer never promotes («al più ne creo un'altra da 0 su un tag nuovo»). An `-rc.N` tag published as stable
   would have deployed the docs and announced `latest` in its notes while `latest` ignored it — the symmetric check
   stops that run at its first step.

## Consequences

- The in-app update prompt reads only stable `vX.Y.Z` releases and probes the plain `X.Y.Z` tag, the full image, so
  the light build runs first and the full one last ([[concepts/ci-release-pipeline]], «Push order»).
- Local `dev.py docker build` tags still come from `git describe` and keep the `v`.
- The tag guard reads `TAG_NAME` and `PRERELEASE` through `env`, never interpolated into the script; M simulated it
  on 28 cases, 14 per branch, an injection attempt and embedded newlines included.
- `./dev.py test utils release-image-contract` pins the tags, the push order and the step order.

## Source files

| Role | Path |
|------|------|
| Tag guard, metadata steps, deploy condition | `.github/workflows/release.yml` |
| Contract tests (tags, order) | `backend/test_scripts/test_utilities/test_release_image_contract.py` |
| Developer page («Release Tags and Publishing», «Docker Images and Tags») | `mkdocs_src/docs/developer/docs/release-pipeline.md` |
| User guide («Image Variants: Full and Light») | `mkdocs_src/docs/user/installation.en.md` |
| Journal (§0, steps 9–12) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseGallery.prompt.md` |
| Journal (§0, O3) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseImages.prompt.md` |
