---
title: "A stamp can hide a translation that never received the English change"
category: problem
status: resolved
date: 2026-10-10
tags: [docs, i18n, translation, aphra, mkdocs, cache, stamp, translate-stamp, translate-validate]
related:
  - concepts/mkdocs-suffix-i18n
  - decisions/docs-anchors-from-the-render
  - problems/raw-html-paths-in-translations
  - decisions/fr-typography-at-build-time
  - sources/phase00-translation-round12-2026-10
---

# Problem: stamps hide stale translations

> Written by workstream M (translations and gallery) as a note for the devWiki on 2026-10-11, filed by the historian
> on 2026-10-12 with its paths and commits checked at `5d0585595`.

## Symptom

During the 1.2 translation round (batch 11, 2026-10-10), translations that the cache declared up to date did not say
what the English said. `fifo-engine/fifo-lot-analysis.it` lacked a whole paragraph (`LotsAnalysisService` and the
unified price resolver). `transaction-types/adjustment` (it/fr/es) still described a cash effect «Optional (± any
amount)» that the English had dropped in August, and missed the succession holdings, the imported examples and the
in-kind capital. `portfolio-engine/deposited-capital` (it/fr/es) still used the old `DepCap` formula instead of
`CapitalBaseline`. Neither `translate --dry-run` nor `translate-validate` reported any of them.

## Root Cause

`translate-stamp` records the English page's current MD5 as translated for the stamped languages. It is the right tool
after a small English change has been ported **by hand** into all three translations. Stamped without the port — or
with a port into one language only, or after a larger change was judged «small» — it tells the pipeline that a stale
translation is current, and the page is never offered again.

The validators cannot see it either: the old translation is structurally fine. Only identifiers, links and numbers
that the English added can betray it.

## Detection (batch 11)

1. **Stamp audit:** for every page/language whose last cache event is a stamp (`stamped_at` > `translated_at`), diff
   the English at `translated_at` with the current English. Result: 160 pairs on 54 pages had an English change
   between their last translation and a stamp.
2. **Port check:** the tokens a translation keeps verbatim — inline code spans, link URLs, numbers — that the English
   added since `translated_at` must be in the translation. A missing token flags the pair; the larger English diffs
   were then read by hand.
3. Result: 4 pages had not been ported — `adjustment` and `deposited-capital` (it/fr/es), `fifo-engine/index`
   (it/fr/es, a stale enum value `none` instead of `unavailable`), `fifo-lot-analysis` (it). They were ported by
   hand. Every other stamp was verified ported.

The two scripts live outside the repository, in M's release-pipeline notes (`b11_stamp_audit.py`,
`b11_stamp_port_check.py`).

**Batch 13 (2026-10-11):** re-run after the second round. The port check compared numbers verbatim, so a localized
digit grouping looked like a missing number: `directa` (it/fr/es, EN `3,000` vs «3.000», «3 000») and
`fifo-lot-analysis` (it, `1000` vs «1.000») were flagged although ported. It now compares numbers without grouping,
as `inline-code-missing` does (a number really missing, e.g. 300 for 3,000, is still flagged): 0 pairs, and the
round's only stamp (`user/brokers/index`) had ported everything.

## Solution and Prevention

- A stamp is a promise that all three translations already say what the English says. Port first, in every
  language, then stamp; send anything beyond a few lines to the pipeline instead.
- `translate-validate` now has `inline-code-missing` (every inline code span of the English must be in the
  translation; commit `23f915f71`): it catches identifier-level drift — it found the stale `none`/`unavailable` and
  several identifiers the model had translated — but not prose.
- Run the stamp audit after each translation round. Making it a `translate-validate` option is backlog item M-3.

## Related: the cache bug fixed in the same round

Before batch 11, an analysis moved an entry's MD5 to the new English but kept `langs_done`. A language that then
failed, was interrupted or was left out by `--lang` stayed «done», with its old translation, exactly like an unported
stamp. Now an entry's MD5 is the English version its `langs_done` were translated or stamped from: a changed MD5
empties `langs_done`, a failure never marks a language done, and a stamp keeps the other languages only for an
unchanged MD5 (`_cache_*` helpers of `translate_docs.py`, commit `a516e4e73`; tests `./dev.py test utils
translation-cache`).

## Impact

Four pages served stale translations — `adjustment` since an English change of August — while every check was green.
The correction of two wrong lines of [[concepts/mkdocs-suffix-i18n]] («never modify `.it.md` by hand»; the cache
stores the MD5 of every language) came out of the same investigation.

## Links

- [[concepts/mkdocs-suffix-i18n]] — the conventions this corrected
- [[decisions/docs-anchors-from-the-render]] — the same round's other blind spot of the checks
- Source: [[sources/phase00-translation-round12-2026-10]]

## Source files

| Role | Path |
|------|------|
| Cache helpers (`_cache_mark_analyzed`, `_cache_mark_translated`, `_cache_mark_failed`, `_cache_stamp`) and `translate-stamp` | `mkdocs_src/aphra-pipeline/translate_docs.py` |
| `inline-code-missing` | `mkdocs_src/aphra-pipeline/validate_translations.py` |
| Cache tests (`utils translation-cache`) | `backend/test_scripts/test_utilities/test_translation_cache.py` |
| Validator tests (`utils translation-validator`) | `backend/test_scripts/test_utilities/test_translation_validator.py` |
| «Manual Edits → Stamp» | `.github/skills/devpy-tools/devpy-mkdocs/SKILL.md` |
| Journal (batches 11 and 13) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
