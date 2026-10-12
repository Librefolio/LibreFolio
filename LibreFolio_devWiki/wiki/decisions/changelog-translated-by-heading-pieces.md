---
title: "The CHANGELOG is translated by pieces keyed by their headings: the version lines are copied, a structure change is refused, and the open chapter blocks nothing until its tag"
category: decision
status: resolved
date: 2026-10-12
tags: [docs, i18n, translation, aphra, changelog, cache, validator, release, workstream-m, release-1.2]
related:
  - decisions/changelog-translated-by-chapter
  - features/F-109
  - features/F-070
  - problems/stamps-hide-stale-translations
  - sources/phase00-translation-round12-2026-10
---

# Decision: translate the CHANGELOG the way the pages are translated, piece by piece

> Written from workstream M's note for the devWiki (batch 25, 2026-10-12), checked against the code at `b91d6d902`.

## Context

The developer approved translating the CHANGELOG, unreleased chapters included («si ma fai anche la traduzione delle
cose non ancora rilasciate, tanto stiamo rifinendo, ci fossero piccole aggiunte, andremo in append»). The app shows a
translated chapter in place of its English twin and falls back chapter by chapter
([[decisions/changelog-translated-by-chapter]]), so each translation has to copy every `## [x.y.z] - date` line byte
for byte, in order, and leave out a chapter not yet translated. The [1.2.0] chapter is about 74.5 KB and still growing:
re-translating it whole for every added line would be slow and would rewrite text already reviewed.

## Decision

The coordinator's frame, implemented by M in `2aecd5a6f` («feat(docs): translate the CHANGELOG by pieces»):

- **Units and pieces** (`mkdocs_src/aphra-pipeline/changelog.py`, pure functions). The preamble and each chapter are
  units. A chapter over 30,000 characters is cut at its `###` and `####` lines (outside fenced code); a heading alone
  and the chapter's intro join the part that follows. A piece is keyed by its headings' words —
  `CHANGELOG.md#1.2.0/fixed/documentation` — so an added section shifts no other key. The version line is never sent
  to the model: it is copied.
- **Cache.** One entry per piece in `.translate-hashes.json`, with the page transitions, plus `langs.<lang>.index`, the
  piece's position when last written: the translated parts are found by those indexes, not by position.
- **The trap, refused twice.** A model that adds or drops a heading changes how the chapter cuts; the file would no
  longer match its pieces and every later run would translate the whole chapter again. So a translation is refused per
  piece (one part, with a heading at the start exactly when the English piece has one) and per chapter before writing
  (a break at a seam, such as a fence left open).
- **The open chapter.** The newest chapter is open until its tag (`vX.Y.Z` or `X.Y.Z`, or the CI ref) exists: its
  findings in `translate-validate` are information, so a dev run never blocks on an unreleased line, and a tag run does.
- **Append.** A line added to the open chapter re-translates only its piece, in three languages; a hand port plus
  `translate-stamp --file CHANGELOG.md` does the same with no model call. Both were seen working on the real file.

The translations themselves came in `4325e03d4` (`CHANGELOG.{it,fr,es}.md`, every chapter, [1.2.0] included); tests in
`e63cfb074`; the developer manual gained a «Changelog» part in `translation-pipeline.md`.

## Options Considered

- **One hash per chapter for [1.2.0] too**: every added line would have re-translated 74.5 KB in three languages.
- **Key pieces by position**: an added section would have shifted every later key and invalidated the cache.
- **Block every run on the open chapter**: a dev run would fail on a line just added in English, before any translation
  could exist.

## Consequences

- `CHANGELOG.md` stays the coordinator's alone; its translations are generated, and the app reads them lazily.
- A structure change in a translation surfaces as a refused piece, not as a silent full re-translation.
- The release-notes discipline of «Changelog Rules» now has three translated companions to keep in step.

## Source files

| Role | Path |
|------|------|
| Units, pieces, keys | `mkdocs_src/aphra-pipeline/changelog.py` |
| Translate and stamp | `mkdocs_src/aphra-pipeline/translate_docs.py` |
| Validator (structure, the open chapter) | `mkdocs_src/aphra-pipeline/validate_translations.py` |
| Cache | `mkdocs_src/aphra-pipeline/.translate-hashes.json` |
| Translations | `CHANGELOG.it.md` |
| Cache tests | `backend/test_scripts/test_utilities/test_translation_cache.py` |
| Validator tests | `backend/test_scripts/test_utilities/test_translation_validator.py` |
| Developer manual («Changelog») | `mkdocs_src/docs/developer/docs/translation-pipeline.md` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` |
