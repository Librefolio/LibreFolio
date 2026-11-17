---
title: "The return histogram's grid is pinned on the VaR cut — and, since RN-14, on the green tail's threshold too — and the risk maths are pinned by an oracle before being vectorised"
category: decision
status: resolved
date: 2026-09-18
updated: 2026-11-16
tags: [risk, var, histogram, metrics, oracle, numpy, testing, release-1.2, release-1.4]
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
- **An oracle before the migration** (`d15917eeb`, «test(risk): pin the hand-written risk maths against an oracle»):
  the same mandate wrote the numerical oracle and migrated the maths under it; any correction meant to move the numbers
  came later and alone, so every shifted number had one possible cause.
- **Two cuts since RN-14** (1.4, consultant's option A, 16/11/2026). The distribution also colours its right tail
  green, from a threshold that is the mirror of the VaR: the same estimator read on the gains, same level and horizon
  (`gain_threshold`), never a second formula. The green tail must be whole bars too, or the two tails would be drawn by
  two rules and a bar straddling the threshold would have no colour. So when `gain_edge` is given, the bar width becomes
  the distance between the two cuts over the whole number of bars nearest to the Freedman–Diaconis width, never fewer
  than one: both cuts are edges, the threshold set exactly.
- **The fall-back is the old grid, never an invented width.** No Freedman–Diaconis width (zero IQR, Sturges or the
  fixed fallback), a threshold not above the VaR cut (a near-flat series), or a fit that would pass the bar ceiling
  even at one bar between the cuts: the grid stays pinned on the VaR alone, and `gain_edge` names the first edge at or
  past the threshold, so the green tail is still whole bars. Each of the three has its test.

## Consequences

- The histogram rules that followed — Sturges for a zero IQR, a capped Freedman–Diaconis count — are D380–D381
  ([[concepts/risk-binding-decisions]]); C-22, the near-flat case, is still a decision for after 1.2 ([[features/F-110]]).
- The payload of `historical_var` carries both cuts: `var_bin_edge` and, since 3.3.0, `gain_threshold` and
  `gain_bin_edge` (the edge the green bars start on). Only `historical_var` draws a distribution; the lab's
  `asset_set_var` publishes no bins.

## Source files

| Role | Path |
|------|------|
| `return_distribution_histogram`, `gain_threshold`, `_bars_between_the_cuts` | `backend/app/services/risk/metrics.py` |
| The two cuts on the wire | `backend/app/services/risk_plugins/historical_var/plugin.py` |
| The grid's tests (both cuts, the three fall-backs) | `backend/test_scripts/test_services/test_risk_metrics.py` |
| Journal (stream A) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/progress/A-esecuzione.md` |
