---
title: "Phase 0 / 43 — one home for financial math (T-1), D-P7 on utils/, C-53 and the AI Export version rule"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md
tags: [phase0, release2, workstream-t, financial-math, refactor, layering, utils, ai-export, versioning, devwiki]
related:
  - decisions/financial-math-one-home
  - decisions/utils-leaf-functions-only
  - decisions/ai-export-version-bump-once-per-release
  - problems/ai-export-reconciled-false-on-rounding-dust
  - decisions/financial-math-single-average-cost
  - entities/portfolio-engine
  - entities/fifo-lot-engine
  - entities/lots-analysis-service
  - sources/phase00-wac-unification-2026-10
---

# Source: Phase 0 / 43 — one home for financial math

## Summary

The plan of workstream T (1 592 lines, from 2026-10-11, still active in `Phase_0/` at `5d0585595`). Part 1 brings
every financial calculation into `backend/app/services/financial_math/`; part 2 (§P2) is the wider «Code reordering»
of backend and frontend, executed one approved lot at a time. This ingest covers §10 — step T-1 (commit A, the
renames; commit B, the cut; the guard; the docs; the devWiki rows) — with decisions D-1…D-11 (§8), then C-53 and the
developer's decision D-P7 on `utils/`, and the planned BU1/BU2. The earlier steps of §10 (B1–B3b, PL3, FE1, C-50) are
not ingested here, except where a wiki page was stale because of them (the lots' «no unconverted fallback», B3a).

## Key takeaways

- **T-1** ([[decisions/financial-math-one-home]]): renames first (`1cc9cd8f5`), the cut second (`a57a43fbd`), so
  `git log --follow` stays continuous on the renamed files; no shims and no re-exports, because the tests patch module
  globals; an AST guard (`test_layer_boundaries.py`) for the boundaries, the docstring-only `__init__.py` files and
  the old homes; D-11, the `financial-math.instructions.md` rules file; `developer/backend/financial_math.md`.
  Merged in train 45 (`76a7b099b`); `all-backend` 12 390 passed, the base plus the 37 guard tests.
- **devWiki**: the historian, in T's worktree, repointed the 58 «Source files» rows that cited moved modules
  (`09c089147`); the 50 old paths left in the prose became backlog T-W1, realigned by this ingest on 2026-10-12.
- **D-P7** ([[decisions/utils-leaf-functions-only]]): `utils/` keeps the leaf functions, which never import services;
  BU1 groups them into subfolders and BU2 moves the decimal truncation out — both planned for 1.2, not in the code at
  `5d0585595`.
- **C-53** ([[problems/ai-export-reconciled-false-on-rounding-dust]], `876d2b430`, train 47): `reconciled` true below
  `CONVERSION_DUST`, both reconciliation components to v2.
- **The version rule** ([[decisions/ai-export-version-bump-once-per-release]]): «+1 rispetto alla 1.1» — one step over
  the last released version until the release ships; the compact renderer's map in the same change (the lesson of B3b).
- **Left after 1.2** (backlog section T): T-R1 (private names across the layer boundary), T-U1…T-U10 (the
  unifications), T-TS1 (the test tree mirror), and the part-2 lots.

## Wiki pages created or updated

- Created: [[decisions/financial-math-one-home]], [[decisions/utils-leaf-functions-only]],
  [[decisions/ai-export-version-bump-once-per-release]], [[problems/ai-export-reconciled-false-on-rounding-dust]].
- Updated: [[decisions/financial-math-single-average-cost]] (its «Known limits» were overtaken: the lots' fallback is
  gone since `82c1d3ab9`, `roi_utils` and `valuation_utils` moved), [[entities/portfolio-engine]],
  [[entities/fifo-lot-engine]], [[entities/lots-analysis-service]], [[entities/portfolio-service]],
  [[entities/ai-export-snapshot-service]], and the 18 pages realigned by T-W1 (see `log.md`, 2026-10-12).

## Not in the plan, recorded from the coordinator

- The version rule as the developer stated it on 2026-10-12: one +1 over the last released version, until the release
  ships. The plan records its application to C-53 («regola del developer: +1 rispetto alla 1.1»).
- The BU1 folder name: `utils/runtime/`, the developer's choice; `utils/platform/` in the plan was the earlier proposal.

## CL — the localized changelog frontend (added in step B8)

After C-55 the plan records one more job of T's, not about financial math (registered at `fba291f53`): the frontend
of the localized CHANGELOG, which the developer moved from I to T on 2026-10-12. T analysed the bundle (the English
changelog is inline in the shell; jsdom cannot import `?raw` files), proposed lazy per-language chunks and a merge
keyed on the version, and delivered it in steps — the key `changelog.notTranslated` (`a8691bd27`, train 57), the
red tests, the cure (`8f67f89de`), the runner's rebuild on a changelog change (`ee8a19384`), the user guide
(`b02bf6c54`). A synthetic `CHANGELOG.it.md`, never tracked, proved the translated branch in the build and the E2E, then
was deleted. Pages: [[features/F-109]] (registered in step B8) and [[decisions/changelog-translated-by-chapter]].

## T-SHK, T-CL, T-ISO and T-FB (trains 85, 88 and 90, added 2026-10-13)

- **T-SHK** (`97810317a`): the hypothetical shock's table names its buckets — a translated class, a sector with its
  emoji, a country with its flag, a translated «Other» — under a header that names the dimension, and, when the
  weights are known, a bucket at weight 0 is no longer a row ([[features/F-111]]). The replay keeps «Asset»; the API does not change.
- **T-CL** (`dfc4f9ccc`, `08c0a7a85`): `data-dist-pct` back to a machine form —
  [[problems/test-hooks-read-the-localized-text]]; one term for the maximum drawdown per language, taken from the
  documentation glossary (Italian «Drawdown massimo», French «Perte maximale»), guarded by `riskGlossary.test.ts`.
- **T-ISO** (`2a17ae3af`) and **T-FB** (`03dba53f8`, `d017492d8`): the charts' tooltip dates and the comparison
  signals' fallbacks follow the language — [[decisions/figures-in-the-interface-language]]. The probe test they broke
  was repaired with `data-operation` (`8684d29fe`, train 90).
- Left in the backlog: T-CAT (two renderings of the same categories), T-GRP (geography groups that stay raw ids) and
  T-EVW, which is the defect workstream I cured as R-5 — [[problems/event-markers-lost-in-the-last-partial-period]].
- **The open period's tooltip** (`341c77811`, train 93): the tooltip of an aggregated point names its period up to the
  point's own day (`bucketSpanUpTo`), no longer the Sunday or the month's end still to come; T-EVW closed with a
  pointer to R-5 — [[problems/event-markers-lost-in-the-last-partial-period]].

## Source files

| Role | Path |
|------|------|
| The plan (§0, §1, §3, §4, §8, §10, D-P7) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
| Backlog section T (T-W1, T-R1, T-BU1+BU2) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Backlog C-53 | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` |
| The layer | `backend/app/services/financial_math/__init__.py` |
| The guard | `backend/test_scripts/test_services/test_financial_math/test_layer_boundaries.py` |
| Rules (D-11) and the map | `.github/instructions/financial-math.instructions.md`, `.github/instructions/backend.instructions.md` |
| Developer guide | `mkdocs_src/docs/developer/backend/financial_math.md` |
