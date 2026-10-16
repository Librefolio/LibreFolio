---
title: "Phase 0 / 02 — Risk Analysis replanned and rebuilt (the riskfolio integration), paused until after 1.2"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/
tags: [phase0, release2, risk, riskfolio, quantlib, levels, lab, dashboard, paused, release-1.2]
related:
  - features/F-110
  - features/F-111
  - features/F-112
  - features/F-113
  - sources/phase00-risk-analysis-backend
---

# Source: Phase 0 / 02 — Risk Analysis

## Summary

The largest folder of Phase 0: 110 files, about 63,000 lines, opened on 2026-09-16 to replan Risk Analysis, which had
shipped in 1.1.0 as a beta with a notice on every view. This page covers the folder's README (step R0 of its ingest);
the other parts are ingested in steps R1–R6.

| Part | Files | What it holds |
|------|-------|---------------|
| `00`–`08` and README | 10 | The analysis (state, thesis and four questions, verdicts per tool, levels × pages, visual grammar, math and libraries), the decisions and open questions (`04`), the executive plan, the post-integration review |
| `implementation/` | 34 | The first round (2026-09-18): streams A–N, contracts K1–K9, progress logs |
| `implementation_2/` | 34 | The second round and the UI round (2026-09-18 → 10-08): the asset-set contract, levels S1–S5, the post-merge review R5, the register, progress logs |
| `_archive-backendFirst-G0G6/` | 30 | The backend-first plan G0–G6 of the summer, superseded; its backend part is [[sources/phase00-risk-analysis-backend]] |

## Key Takeaways

- **Delivered in `dev_release2`**: the engine with fifteen analytic plugins ([[features/F-110]]), the four-level Risk
  tab of the Dashboard and broker pages ([[features/F-111]]), the Lab of Asset Global ([[features/F-112]]); the Risk tab
  of Asset Detail stays on the legacy panel ([[features/F-113]]).
- **1.2 maturity**: «Risk Analysis leaves beta, except the simulation» (CHANGELOG); Asset Detail keeps its notice.
- **Paused** (D382, 2026-10-09), the developer: «risk facciamo bene ad aggiornarlo, ma non lo archivamo perchè ancora
  non va bene, lo so già guardandolo, solo mi sono fermato dal lavorarlo per concludere questa release». The folder stays
  in `Phase_0/`; on 2026-10-10 the open items of Risk, A and F were gathered in its README, with a guide to restart —
  planned work not done (A1–A6), real gaps, known defects, test gaps, undecided questions, backlog-38 items. They are
  recorded in the wiki as «paused, after 1.2» (step R1).

## Pages created from this source

- [[features/F-110]], [[features/F-111]], [[features/F-112]], [[features/F-113]] (step R0).
- [[decisions/risk-answers-four-questions]], [[concepts/risk-binding-decisions]] (step R2).
- From `implementation_2/` (step R3): [[decisions/asset-set-one-preparation-not-fan-out]],
  [[decisions/l3-reads-current-composition]], [[problems/runner-catalog-merge-not-line-union]].
- From the post-merge review R5 (step R3b): [[problems/risk-stress-buckets-hand-listed]],
  [[problems/replay-baseline-shortened-by-late-starter]], [[problems/echarts-stacked-band-null-base]].
- From the first round, `implementation/` (step R4): [[concepts/risk-contracts-k1-k9]],
  [[decisions/histogram-grid-pinned-to-var-cut]], [[problems/annualization-factor-not-coverage]].
- From the analysis documents (step R5): [[decisions/risk-tool-verdicts]], [[decisions/risk-library-versus-own-maths]].
- The archive G0–G6 (step R6): drift only, recorded on [[sources/phase00-risk-analysis-backend]]. With R6 the folder is
  covered; the big progress logs stay in the journal, their outcomes being in the code and in the pages above.

## Source files

| Role | Path |
|------|------|
| Folder README (open items, restart guide, code map) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/README.md` |
| Decisions and open questions | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/04-decisioni-e-questioni-aperte.md` |
| Engine | `backend/app/services/risk/service.py` |
| Levels panel | `frontend/src/lib/features/risk/levels/RiskLevelsPanel.svelte` |
