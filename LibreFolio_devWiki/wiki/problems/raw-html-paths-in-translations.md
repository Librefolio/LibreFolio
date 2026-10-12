---
title: "A raw-HTML image path is one folder short in every translation"
category: problem
status: resolved
date: 2026-10-11
tags: [docs, i18n, mkdocs, mkdocs-static-i18n, translation, images, raw-html, build]
related:
  - concepts/mkdocs-suffix-i18n
  - decisions/docs-anchors-from-the-render
  - decisions/fr-typography-at-build-time
  - problems/stamps-hide-stale-translations
  - sources/phase00-translation-round12-2026-10
---

# Problem: a raw-HTML image path is one folder short in every translation

> Written by workstream M as a note for the devWiki on 2026-10-11, filed by the historian on 2026-10-12 with its paths
> and commits checked at `5d0585595`.

## Symptom

21 images were broken in the Italian, French and Spanish sites while the English ones showed: the CSS Scraper
and Scheduled Investment icons since June 2026, and the Scalable Capital favicon on the import overview. The
strict build stayed green. `dev.py mkdocs build` printed «⚠️ 3 broken icon path(s)» and exited 0, and a check that
counted only WARNING/ERROR lines did not see it.

## Root Cause

- With `mkdocs-static-i18n` (suffix structure), a translated page is built under `site/<lang>/…`, one folder deeper
  than its English page, and the language folders hold only HTML: every image, icon or file is served from the
  site root.
- MkDocs rewrites the paths of Markdown images and links for each page; it does not touch raw HTML.
- So a raw-HTML relative path that works on the English page (`<img src="../../../static/icons/x.png">`) points
  under `site/<lang>/static/…` when copied unchanged into a translation. The translation pipeline copies `src`/`href`
  verbatim, as its prompts require.
- `translate-validate` accepted one more `../` in a translation but also the unchanged copy; `dev.py`'s post-build
  check looked only at `static/icons` and never failed the build.

## Fix (batch 14)

- The 21 paths got one more `../` (`720ca8008`).
- `dev.py mkdocs build` resolves every relative file URL of the built site (img/source `src`/`srcset`, video
  `src`/`poster`, audio `src`, `<a href>` to a file) from its page's folder, as a browser does, and exits 1 on a
  broken one (`d23fac443`): the release workflow's build steps now fail on it.
- `translate-validate` reports `html-asset-depth` (ERROR): a raw-HTML relative file path copied unchanged from the
  English, with the line and the path to write, computed from the page's build folder (`90d146111`).
- Tests: `./dev.py test utils gate-docs-links`, `./dev.py test utils translation-validator`.
- All three commits reached `dev_release2` with train 37 (merge `6fa720752`).

## Prevention

- In an English page, prefer Markdown image syntax (`![alt](path){: … }`): MkDocs fixes its path in every language.
  Raw HTML is needed inside HTML blocks (cards, headings with an icon): then every translation needs one more `../`
  for a path that climbs to the site root.
- Read build logs for ⚠️/❌ as well as WARNING/ERROR; with the new check, the exit code is enough.
- Still open (backlog): a deterministic pipeline step for the `../` of translations, only if the case recurs (M-2);
  the `../` of `srcset` and `poster` in `html-attr-mismatch` (M-6).

## Links

- [[concepts/mkdocs-suffix-i18n]] — the suffix structure that puts translations one folder deeper
- [[decisions/fr-typography-at-build-time]] — the other build-time rule for translated pages
- Source: [[sources/phase00-translation-round12-2026-10]]

## Source files

| Role | Path |
|------|------|
| `_relative_asset_urls`, `_check_asset_paths_in_built_site`, `cmd_mkdocs_build` | `dev.py` |
| `check_html_asset_depth`, `_translated_file_url` | `mkdocs_src/aphra-pipeline/validate_translations.py` |
| The build check's tests | `backend/test_scripts/test_utilities/test_docs_links_gate.py` |
| The validator check's tests | `backend/test_scripts/test_utilities/test_translation_validator.py` |
| Journal (step 5.9b) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
