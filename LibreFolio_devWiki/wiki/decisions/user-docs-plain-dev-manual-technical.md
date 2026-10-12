---
title: "The user pages stay plain and the technical detail moves to the developer manual; the English docs are aligned before any translation, with placeholders instead of invented screenshots"
category: decision
status: resolved
date: 2026-10-08
updated: 2026-10-10
tags: [docs, mkdocs, user-docs, developer-docs, docs-writer, screenshots, placeholders, i18n, workstream-q, release-1.2]
related:
  - features/F-069
  - problems/docs-claimed-what-the-code-did-not-do
  - decisions/docs-anchors-from-the-render
  - decisions/gallery-is-a-release-gate-with-real-data
  - sources/phase00-docs-english-12-2026-10
---

# Decision: simple for the user, exact for the developer

## Context

Between v1.1.0 (commit `837a8f2c7`, 2026-09-07) and the start of the 1.2 docs work on 2026-10-07 the repository took 809
commits, and 205 files under `mkdocs_src/docs` changed. Workstream Q received the English documentation to align:
user, admin and theory pages first (Q1), then the developer manual (Q2), the second kept separable so that it could
be cut from 1.2. 58 English pages were already stale against the translation cache, and 22 new ones had never been
translated.

## Decision

**The working rules** (coordinator, 2026-10-07, with the developer's approval):

- pages are written by the `docs-writer` agent, in English only, and **no translation is stamped**: Q reports the
  translation debt at the end instead of hiding it;
- `mkdocs build` (strict) and `mkdocs check-links` run at every batch; the criterion is no new broken link against the
  baseline;
- screenshots: «organizzati che q scrive delle note placeholder che poi quando abbiamo gli screen vengono sostituite
  dal codice giusto» (D4). A missing image is `<!-- [Screenshot Placeholder: <name> — <what it shows>] -->`, its name
  agreed with M, who shoots it. **No invented data**: the shots that need the new dashboard fixture stay placeholders
  until the developer provides it ([[decisions/gallery-is-a-release-gate-with-real-data]], D1).

**The developer's review of the user pages** (2026-10-08), verbatim:

- on the Tools page: «tools: fino a opening tool come capitolo va bene quello che viene dopo è da manuale dev se fosse,
  qui è la sezione utente, deve essere semplice»;
- on the PAC page: «non farei una tabella con gli step, ma per ogni step una sezione, così compare anche nella tabella
  dei contenuti, e per formule e numeri cercherei di usare latex», then «togli il riferimento alla versione, non serve»;
- on the Danske Bank page, and on every page: «Poi è un muro di testo, troppi dettagli tecnici, e te lo dico, vale per
  tutto, non solo per questa pagina, quindi riguarda anche le altre e cerca di semplificare e scorporare, mettere in dev
  manual le cose tecniche e qui le info utili».

## Options Considered

- **Keep the technical detail in the user pages**, where Q had first written it: refused by the 13:08 review.
- **Translate along the way.** Refused: the translations came after the English was final, in one pipeline round
  («per ora non avviare nessuna traduzione, fammi solo il resoconto», 2026-10-08).
- **Shoot the missing screenshots from made-up data.** Refused by D1 and D4.

## Consequences

- Three waves simplified the user and admin pages and moved the internals to the developer manual (`eee56b42a`,
  `1c2f88d67`, `22d80282a`, 2026-10-08). New developer pages took what left the user pages: the Risk UI and the Danske
  Bank and Crédit Agricole importers; the risk subsystem page had come with Q2 (`7b06e9f9f`).
- Writing from the code, the waves found and fixed pages that described something the code did not do
  ([[problems/docs-claimed-what-the-code-did-not-do]]).
- DEGIRO went Stable: «abbiamo avuto degli export veri, direi che è uscito dalla fase beta». The import list shows a
  badge only for Alpha and Beta.
- English-only pages link translated pages **without anchors**: a strict build of a translated site checks the anchor
  in the translated page, where a heading's slug differs ([[decisions/docs-anchors-from-the-render]]).
- The eight broker-portal screenshots stay hidden placeholders after 1.2, by the developer's decision; the translation
  round ran afterwards, in M's batch 11 (train 29, `e32f47133`).

## Source files

| Role | Path |
|------|------|
| Writer agent | `.github/agents/docs-writer.agent.md` |
| Doc rules for agents | `.github/instructions/mkdocs.instructions.md` |
| User page simplified (Tools) | `mkdocs_src/docs/user/tools/index.en.md` |
| New developer page (risk subsystem) | `mkdocs_src/docs/developer/backend/risk/architecture.md` |
| New developer page (Risk UI) | `mkdocs_src/docs/developer/frontend/components/features/risk-lab.md` |
| New developer page (Danske Bank) | `mkdocs_src/docs/developer/backend/brim/danske_bank.md` |
| New developer page (Crédit Agricole) | `mkdocs_src/docs/developer/backend/brim/credit_agricole.md` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md` |
