---
title: "Phase 0 / 32 — the English documentation aligned with 1.2 (workstream Q)"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md
tags: [phase0, release2, workstream-q, docs, mkdocs, user-docs, developer-docs, docs-writer, drift, release-1.2]
related:
  - decisions/user-docs-plain-dev-manual-technical
  - problems/docs-claimed-what-the-code-did-not-do
  - decisions/docs-anchors-from-the-render
  - features/F-069
  - features/F-102
---

# Source: Phase 0 / 32 — the English docs for 1.2

## Summary

One plan of about 1,800 lines, mostly in Italian, by workstream Q, from 2026-10-07 to 10-10. Q compared the
documentation with the code from v1.1.0 (commit `785d78a4e`): 809 commits, 205 files under `mkdocs_src/docs`. The work ran
in two parts — Q1, the user, admin and theory pages; Q2, the developer manual, kept separable — and then in 23 steps
(S1–S23) that followed the developer's reviews and the trains of the other workstreams. Only English pages were
written; the translations came afterwards, in workstream M's round.

| Part | Dates | What it did |
|------|-------|-------------|
| Q1 (`e26732eeb`) | 2026-10-07 | User and admin pages, theory, the screenshot inventory with named placeholders |
| Q2 (`bf30d01a2`) | 2026-10-07 | The developer manual: the 1.2 drift, two errors older than 1.1, the onboarding and risk pages |
| S12–S13 (`ddd342546`, `ba372e117`) | 2026-10-07/08 | The broker Risk tab anchor; simulation limits that name their remedy (`resource_limit`) |
| S16–S18, three waves (`6220dfb2f`, `c3b8a4290`, `a93c8227a`) | 2026-10-08 | The developer's review: plain user pages, technical detail moved to the developer manual, every page re-checked on the code |
| S19 (`3a9a1738e`) | 2026-10-08 | What train 19 changed: `dev.py` in the image, FX and i18n, events |
| S20 (`022f0054b`) | 2026-10-09 | The connection security page, with masked Tailscale addresses |
| S22–S23 | 2026-10-09 | The Sharpe and Sortino pages convert the risk-free rate with the series' frequency (`7a3a38e85`); the last English pages before the translation round (`151446d83`) |

## Key Takeaways

- **The rules**: pages by the `docs-writer` agent, English only, no translation stamped; a strict build and
  `check-links` at every batch, with no new broken link against the baseline; a named placeholder wherever a
  screenshot does not exist yet, and no invented data
  ([[decisions/user-docs-plain-dev-manual-technical]]).
- **The review that reshaped the work** (2026-10-08, 13:08): «è un muro di testo, troppi dettagli tecnici, e te lo
  dico, vale per tutto» — user pages simplified, internals moved to the developer manual.
- **The code contradicted the pages** in several places — the Generic CSV mapping, the IBKR export, the SNB provider,
  the scheduler's leader, sessions, migrations in Docker, the ECB currency count, the Sharpe and Sortino risk-free
  rate ([[problems/docs-claimed-what-the-code-did-not-do]]).
- **English-only pages link translated pages without anchors**: a strict translated build checks the anchor in the
  translated page, whose slug differs ([[decisions/docs-anchors-from-the-render]]).
- **`mkdocs serve` lost the gallery images**: MkDocs rewrites `site_url` to the local address, so the fallback to the
  online screenshots asked the local server; fixed in `01ed5bd04` by reading the canonical URL.
- **The translation debt was reported, not hidden**: 58 stale English pages and 22 never translated at the start. The
  translations came in M's batch 11 (train 29, `90997fa46`, [[sources/phase00-translation-round12-2026-10]]).
- **Closed at the end** (2026-10-10): the eight broker-portal screenshots stay hidden placeholders, a post-1.2 backlog
  item, by the developer's decision; the `security/connection-indicator` placeholder was shot by M (`207656c04`); the
  page of [[features/F-102]] exists since S20.

## Pages created from this source

- [[decisions/user-docs-plain-dev-manual-technical]]
- [[problems/docs-claimed-what-the-code-did-not-do]]

Pages updated: [[features/F-069]], [[decisions/docs-anchors-from-the-render]].

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/Phase_0/32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md` |
| Writer agent | `.github/agents/docs-writer.agent.md` |
| Connection security page | `mkdocs_src/docs/user/connection-security.en.md` |
| Risk dashboard page (user) | `mkdocs_src/docs/user/dashboard/risk.en.md` |
| Risk subsystem (developer) | `mkdocs_src/docs/developer/backend/risk/architecture.md` |
| Gallery fallback base | `mkdocs_src/overrides/main.html` |
