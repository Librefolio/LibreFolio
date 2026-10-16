---
title: "The decisions that bind Risk work — the folder-02 list, in English, with where each one lives"
category: concept
date: 2026-10-12
tags: [risk, decisions, levels, lab, benchmark, histogram, simulation, paused, release-1.2]
related:
  - decisions/risk-answers-four-questions
  - features/F-110
  - features/F-111
  - features/F-112
  - features/F-113
  - sources/phase00-risk-integration-2026-09
---

# Concept: the decisions that bind Risk work

## Definition

Folder 02 numbers its decisions D1…D384 in `04-decisioni-e-questioni-aperte.md`. Its README picks out the ones that
**bind** any further work (section «Decisioni che vincolano il lavoro», 2026-10-10). This page is that list in English,
the entry point for whoever resumes Risk after release 1.2 (D382). The full records stay in the journal.

| Decisions | In short |
|-----------|----------|
| The thesis (`01`) | Four questions, one per level; a tool sits where it answers a question — [[decisions/risk-answers-four-questions]] |
| D8, D47 | Asset Detail is reopened last, inheriting the direction already decided (A2, [[features/F-113]]) |
| D46 | Overtaken in fact: the family entered `dev_release2` in trains |
| D54 | The risk columns of Asset Global, hidden by default (B2, not built) |
| D58, D59 | The portfolio sliced by asset, weights renormalised to 100 % of the slice (B3, backend only) |
| D71 | Allocation colours by rank (R12f, undecided whether the families match across charts) |
| D87, D209, D277, D287 | M2 figures are relative variations per confidence level, never a single figure; VaR moves only at the tail's edge |
| D144 | `min_coverage` governs nothing — an open defect |
| D151, D376 | A neutral value is a claim: what the replay excludes is not an impact, and sits above the bars as a badge |
| D370, D371, D378 | One shared benchmark, an owned asset included; in the Lab a selected asset may be the reference, and the reference is never a subject; a benchmark the period cannot measure stays chosen but is not tried |
| D372, D376, D377 | The replay and L4: the common period in one click, no substitutes in L4; a picker that adds instruments; none open on the first visit; the × removes an instrument with its answer |
| D373 | The data-quality banner, with «Sync», in the Lab too; Asset Detail stays as it is |
| D374 | A discarded answer is asked again up to 3 times in all (`RISK_DISCARD_ATTEMPTS`) — [[problems/discarded-risk-answer-read-as-empty]] |
| D375 | Allocation history by type: one area per family, subtypes only in the tooltip |
| D379 | A simulation that is too large says so, with a cure that really works |
| D380, D381 | The histogram: Sturges when the IQR is 0; the Freedman–Diaconis width computed, not built; never «−0.0%» nor «−0,00 €» |
| D382 | The pause until after 1.2 |
| D383 | The box of a level's notices is the same everywhere (Dashboard, broker, Lab) |
| D384 | The broker preset in the Lab asks once |
| 1.2 CHANGELOG | In the Lab only percentages, and no verdict on the selection as a whole; what cannot be measured shows a dash that says why, never a zero |

Checked on the code at `e3a55b85f`: D374 (`RISK_DISCARD_ATTEMPTS = 3` in `riskStore.svelte.ts`), D380–D381
(`metrics.py`, `3ceac8f83`, `f22141e63`). The open items these decisions leave are on the feature pages, «Still open
(paused, after 1.2 — D382)».

## Source files

| Role | Path |
|------|------|
| The list (README, «Decisioni che vincolano il lavoro») | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/README.md` |
| The full decision records | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/04-decisioni-e-questioni-aperte.md` |
| D374 | `frontend/src/lib/features/risk/riskStore.svelte.ts` |
| D380, D381 | `backend/app/services/risk/metrics.py` |
