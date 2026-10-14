---
title: "Phase 0 / 39 — P-1, Auto cost basis without a position: analysed, closed without code"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/39_autoCostNoPosition/plan-phase00AutoCostNoPosition.prompt.md
tags: [phase0, release2, transactions, cost-basis, wac, auto-mode, product-decision, workstream-p]
related:
  - decisions/auto-cost-basis-zero-without-position
  - decisions/wac-inline-validate-commit
  - decisions/financial-math-single-average-cost
  - sources/phase00-wac-unification-2026-10
---

# Source: Phase 0 / 39 — P-1, Auto cost without a position

## Summary

One plan of workstream P (~22 KB), written and closed on 2026-10-09 and archived straight to `phases/` without
passing through `Phase_0/`. It analysed backlog item P-1 — an incoming row in Auto on an empty pool is saved at cost
0 with no warning — and designed a fix that turned the case into a missing cost basis. The developer decided not to
do it: 0 is the correct fallback for Auto when the data is missing, and correcting the cost is the user's job, on
that transaction. Nothing in the code changed; the analysis (§1–§9) stays as the motivation.

## Key takeaways

- The decision, its context checked on the code, and the options it rejected:
  [[decisions/auto-cost-basis-zero-without-position]].
- Analysis findings worth keeping even though no code followed:
  - the "enter the empty field and leave it = 0" gesture does not exist: in Manual a blur on an empty field emits
    `null` (→ `costBasisRequired`), in Auto a blur keeps the computed value (E2E W9, `tx-wac-mode.spec.ts`);
  - no test asserts the `costBasisRequired` code itself; two tests only mention it in comments;
  - three texts (a form warning key, the user form page and a developer page) still describe the pre-June behaviour
    of saving a zero-cost lot when a Manual cost basis is left empty — residual P-11.
- The plan was written for a test lane it never used: no server and no test was started.

## Residuals (backlog 38)

P-10 — `MISSING_COST_BASIS` reachable from the app by retyping a SPLIT event that has a linked Auto `ADJUSTMENT`.
P-11 — three texts promise a zero-cost lot when a Manual cost basis is left empty (in progress on 2026-10-09).

## Wiki pages updated

- [[decisions/auto-cost-basis-zero-without-position]] — new (from workstream P's draft note, verified on the code at
  `083ed26dc`).
- [[decisions/wac-inline-validate-commit]], [[decisions/financial-math-single-average-cost]] — notes.
- [[sources/phase00-wac-unification-2026-10]] — the P-1 residual line corrected (it carried the superseded first
  direction).

## Source files

| Role | Path |
|------|------|
| Plan (§1 state, §2 dropped design, §10 decision) | `LibreFolio_developer_journal/Release_2/phases/39_autoCostNoPosition/plan-phase00AutoCostNoPosition.prompt.md` |
| Backlog (P-1 closed, P-10, P-11) | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` |
| Test pinning the behaviour | `backend/test_scripts/test_api/test_wac_inline.py` |
| E2E W9 (Auto blur keeps the value) | `frontend/e2e/transactions/tx-wac-mode.spec.ts` |
