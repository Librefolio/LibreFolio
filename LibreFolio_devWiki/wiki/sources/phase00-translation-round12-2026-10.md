---
title: "Phase 0 / 27 — translation round 12 (workstream M): M's four devWiki notes and batch 19, the gallery probes"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md
tags: [phase0, release2, workstream-m, docs, i18n, translation, aphra, mkdocs, gallery, playwright]
related:
  - problems/stamps-hide-stale-translations
  - decisions/docs-anchors-from-the-render
  - problems/raw-html-paths-in-translations
  - decisions/fr-typography-at-build-time
  - problems/docs-mathjax-looked-in-the-page-folder
  - problems/copy-buttons-without-http-fallback
  - problems/mkdocs-material-tables-resist-styling
  - problems/playwright-probes-ignore-timeout
  - concepts/mkdocs-suffix-i18n
---

# Source: translation round 12 — M's notes and the gallery probes

## Summary

Two kinds of source from workstream M, which owns the documentation translations, the gallery and the release
pipeline. First, four notes M wrote for the devWiki on 2026-10-10 and 2026-10-11, kept outside the repository with M's
release-pipeline working files (`b12_devwiki_stamps_hide_stale_translations.md`, `b13_devwiki_anchors_from_render.md`,
`b14_devwiki_raw_html_paths_in_translations.md`, `b15_devwiki_fr_typography_hook.md`) and handed over by the
coordinator as step 3 of the historian's work (journal §11, point 1). Second, the journal of round 12, §10: batch 19,
backlog M-13, the gallery probes that ignored their timeout. The notes were filed nearly as written, after checking
every path, symbol and commit against `5d0585595`; two notes lacked a «Source files» table, now added.

## Key takeaways

- **A stamp is a promise that every translation already says what the English says** — stamped without the port, it
  hides a stale translation from every check: [[problems/stamps-hide-stale-translations]].
- **Anchors come from the page's own MkDocs render**, not from a re-implemented slugify, which accepted 1 179 ids the
  build does not have: [[decisions/docs-anchors-from-the-render]].
- **Raw HTML is one folder deeper in every translation**; the build now fails on a broken asset URL and the validator
  reports a copied path: [[problems/raw-html-paths-in-translations]].
- **French typography is applied by a build hook**, never written into the sources that every pipeline run rewrites:
  [[decisions/fr-typography-at-build-time]].
- **A green gallery run can miss shots**: in Playwright 1.61 `isVisible({timeout})` does not wait and
  `isEnabled({timeout})` waits only for the element to exist: [[problems/playwright-probes-ignore-timeout]].
- **Placement of the commits checked on the history**, not taken from the journal: the hook was built on train 37 but
  reached `dev_release2` with train 38 (`9245ffb6f`); the raw-HTML fixes with train 37; the gallery probes with train 46.

## Wiki pages created or updated

- Created: [[problems/stamps-hide-stale-translations]], [[decisions/docs-anchors-from-the-render]],
  [[problems/raw-html-paths-in-translations]], [[decisions/fr-typography-at-build-time]],
  [[problems/playwright-probes-ignore-timeout]].
- Updated: [[concepts/mkdocs-suffix-i18n]] (two wrong «Conventions» lines corrected, as note b12 asked).

## Batches 23 and 24 (2026-10-12, added in step B8)

The plan grew after this page was first written (registered at `dfd8284f3`):

- **Batch 23 — two pages reviewed in a live preview.** `dev.py mkdocs serve` stayed up while the developer read the
  Italian pages and sent corrections, applied live in four languages (`11339afa6`). The Scalable import page lost its
  example-name column and the custom icon URL, gained larger icons, «❓ Why two brokers?» as a heading, the exporter's
  link on its name and a bold recommendation of «our extension»: «vista la pagina di scalable, approvata a pieni
  voti». The connection-security guide became three pros-and-cons tables ([[features/F-102]]). Two CSS traps of
  Material's tables surfaced: [[problems/mkdocs-material-tables-resist-styling]]. Checking one sentence of the guide
  found M-20: [[problems/copy-buttons-without-http-fallback]].
- **Batch 24 — M-19.** Seen in the preview's log: nested pages looked for the local MathJax in their own folder, so
  they used jsDelivr and showed no formula offline; fixed in `8d47c28c0`, proved on 34 pages —
  [[problems/docs-mathjax-looked-in-the-page-folder]]. M-21 (a local site not rebuilt after a JS- or CSS-only change)
  stays in the backlog.
- **The CHANGELOG's translation**, approved by the developer the same day («si ma fai anche la traduzione delle cose
  non ancora rilasciate…»), has its own plan; its frontend came from T — [[decisions/changelog-translated-by-chapter]].

## Not ingested

- The rest of round 12 (batches 11–18: the pipeline runs, the label and register reviews, the glossary) — operational,
  with no durable knowledge beyond the four notes.
- M-14 beyond its diagnosis: the per-language browser locale for the gallery is still in progress.

## Source files

| Role | Path |
|------|------|
| Journal of round 12 (§5.7–§5.9, §6, §9.3, §10, §11) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
| Backlog section M (M-2 … M-16) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Translation pipeline and its cache | `mkdocs_src/aphra-pipeline/translate_docs.py` |
| Translation validator | `mkdocs_src/aphra-pipeline/validate_translations.py` |
| Rendered anchors | `mkdocs_src/aphra-pipeline/page_anchors.py` |
| French typography hook | `mkdocs_src/hooks/fr_typography.py` |
| Gallery scenarios and probes | `frontend/e2e/gallery.spec.ts`, `frontend/e2e/fixtures/probe.ts` |
