---
title: "The return histogram's grid is shifted so one edge falls exactly on the VaR cut, and the risk maths are pinned by an oracle before being vectorised"
category: decision
status: resolved
date: 2026-09-18
tags: [risk, var, histogram, metrics, oracle, numpy, testing, release-1.2]
related:
  - features/F-110
  - features/F-111
  - concepts/risk-contracts-k1-k9
  - concepts/risk-binding-decisions
  - sources/phase00-risk-integration-2026-09
---

# Decision: the red area is exactly the declared percentage

## Context

L1 draws the distribution of returns with the tail beyond the VaR coloured red. With a grid that ignores the cut, a
bin straddles it, and the red area no longer matches the percentage written beside it. Stream A of the first round
noticed it while migrating the maths: «invisibile a occhio, e quindi permanente» (`implementation/progress/A-esecuzione.md`).

## Decision

- **The grid is pinned on the cut.** `return_distribution_histogram` shifts its Freedman–Diaconis grid onto
  `pinned_edge`, which is guaranteed to appear among the edges exactly; every bin keeps the same width, and the grid is
  extended to include the cut when it falls outside the data. The bin cap is checked as an actual count (a first cap of
  200 produced 201 bins).
- **An oracle before the migration** (`f5fe80d44`, «test(risk): pin the hand-written risk maths against an oracle»):
  the same mandate wrote the numerical oracle and migrated the maths under it; any correction meant to move the numbers
  came later and alone, so every shifted number had one possible cause.

## Consequences

- The histogram rules that followed — Sturges for a zero IQR, a capped Freedman–Diaconis count — are D380–D381
  ([[concepts/risk-binding-decisions]]); C-22, the near-flat case, is still a decision for after 1.2 ([[features/F-110]]).

## Source files

| Role | Path |
|------|------|
| `return_distribution_histogram` | `backend/app/services/risk/metrics.py` |
| Journal (stream A) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/progress/A-esecuzione.md` |
