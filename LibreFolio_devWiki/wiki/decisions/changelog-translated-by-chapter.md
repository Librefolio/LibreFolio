---
title: "The changelog is translated chapter by chapter: the English file decides which releases exist, a translated chapter replaces its twin only when it has content, and the rest stays English with a label"
category: decision
status: resolved
date: 2026-10-12
tags: [frontend, changelog, i18n, translation, lazy-loading, sanitization, dompurify, release-1.2, workstream-t, workstream-m]
related:
  - features/F-109
  - features/F-008
  - sources/phase00-financial-math-home-2026-10
  - sources/phase00-translation-round12-2026-10
---

# Decision: a localized changelog that never hides a release

## Context

The in-app changelog ([[features/F-109]]) showed only `CHANGELOG.md`, in English, whatever the interface language.
After batch 23 of the translation round, the developer approved translating it, unreleased chapters included
(«si ma fai anche la traduzione delle cose non ancora rilasciate, tanto stiamo rifinendo, ci fossero piccole aggiunte,
andremo in append»). The translations are workstream M's, in a plan of their own; the frontend went to workstream T:
«T prende la parte frontend del CHANGELOG localizzato al posto di I: I resta su asse x, rifinitura UI e M-18, e U può
dividere prima i cataloghi» (developer, 2026-10-12).

## Decision

**M's contract**: `CHANGELOG.{it,fr,es}.md` at the repository root; their `## [x.y.z] - date` lines identical to the
English ones; a chapter not yet translated is simply absent from the file.

**T's frontend** (CL of plan 43, approved by the coordinator; `8f67f89de`, with the key `a8691bd27`):

- **Loading.** English stays inline in the bundle. The translations come from a lazy
  `import.meta.glob('…/CHANGELOG.[a-z][a-z].md', {query: '?raw'})`: one chunk per language, fetched only when the modal
  opens in that language, cached per language — only successes are cached, and a failed chunk shows everything in
  English. An eager glob would have added about 330 KB to the shell.
- **Merging.** The English file gives the set and the order of the chapters; the key is the version between the
  brackets. A translated chapter with content replaces its English twin; an empty one counts as missing; one without
  an English twin is ignored. A different date in the translation is tolerated (coordinator).
- **The label.** An English chapter inside a translated UI carries a small pill, `changelog.notTranslated` («Not
  translated yet», «Non ancora tradotto», «Pas encore traduit», «Aún sin traducir»); each chapter carries its own
  `lang` and `data-version`.
- **One sanitization path.** Every rendered chapter, English included, goes through `sanitizeHtml` (DOMPurify);
  the modal's exemption in `htmlSink.gate.test.ts` was removed, so the gate now checks it like any other sink.
- **«View on GitHub»** stays on the English file.

## Options Considered

- **An eager glob** of every translation: about 330 KB more in the app shell for a modal most sessions never open.
- **Drop a release that has no translation**, or show the translated file alone: a user would miss a release; the
  English file stays the authority.
- **Discard a translated chapter whose date differs**: rejected by the coordinator — the date is presentation, the
  version is the key.

## Consequences

- Until M's files land, every chapter shows in English with the label: today the tree has no `CHANGELOG.<xx>.md`.
  The E2E test reads whatever file is on disk, so it holds before and after.
- The developer's «andremo in append»: a chapter added later in English simply shows in English until its
  translation is appended.
- `dev.py` treats `CHANGELOG*.md` as inputs of the frontend build (`ee8a19384`); deleting a translation needs an
  explicit `front build`, since modification times cannot see a deletion.
- Before the translations ship, a gallery shot must change: the `changelog-modal-search` shot searches «Added»
  (`gallery.spec.ts`), which a translated chapter no longer contains; the cure — a word that is the same in the four
  languages — is M's.
- The user guide says the modal follows the interface language and labels untranslated releases (`b02bf6c54`).

## Source files

| Role | Path |
|------|------|
| Merge and lazy loaders | `frontend/src/lib/features/changelog/changelog.ts` |
| Modal (pill, loading state, sanitization) | `frontend/src/lib/components/layout/ChangelogModal.svelte` |
| HTML sink gate | `frontend/src/htmlSink.gate.test.ts` |
| E2E | `frontend/e2e/layout/changelog-locale.spec.ts` |
| Rebuild on a changelog change | `scripts/cli_base.py` |
| The label key (English catalogue) | `frontend/src/lib/i18n/en.json` |
| Journal (CL, plan 43) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
| Journal (the developer's approval, §16) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
