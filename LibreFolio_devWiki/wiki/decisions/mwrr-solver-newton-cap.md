---
title: "MWRR solver: Newton-only + result cap (deliberate, not a bug)"
category: decision
status: resolved
date: 2026-07-06
tags: [backend, portfolio, mwrr, xirr, newton-raphson, numerical-stability, financial-math, design-decision]
related:
  - decisions/mwrr-boundary-fix
  - concepts/twrr-mwrr-algorithms
  - entities/portfolio-service
  - features/F-054
---

# Decision: MWRR Solver — Newton-Only + Result Cap (Deliberate Design Choice)

## Context

`mwrr-numerical-stability-analysis.md` (part of the archived Milestone 2 `portfolio_engine/` analysis batch)
explored the numerical stability of the MWRR (XIRR) solver and raised two concerns found in earlier drafts of
the analysis docs:

1. A **Newton-Raphson-only** solver can fail to converge or converge to a nonsensical root for pathological
   cash-flow sequences (e.g. many flows clustered near the same date, or extreme flow magnitudes relative to
   NAV) — a bracketing method like Brent's, or a Newton/Brent hybrid, is more robust in the general case.
2. The MWRR result was observed capped at a large multiple (referred to as "100x" in some analysis docs) in
   some pathological scenarios, which older drafts flagged as suspicious.

**This decision record exists specifically to prevent a future ingest or code review from re-flagging these two
observations as open bugs.** They are not defects in the current implementation — they were evaluated and
deliberately rejected/accepted as trade-offs during Milestone 2.

## Options Considered

1. **Newton-Raphson only** (current implementation in `roi_utils.py::calculate_mwrr()`) — fast, simple,
   sufficient for the actual shape of cash-flow sequences LibreFolio portfolios produce (personal/household
   portfolios, not high-frequency trading books). Convergence failures are handled by falling back to a capped
   result rather than raising.
2. **Brent's method / bisection** — guaranteed to converge given a valid bracket, but requires establishing a
   sign-changing bracket first (non-trivial for XIRR, where the NPV function is not guaranteed monotonic across
   the full domain) and adds implementation complexity for a case that doesn't materialize in practice.
3. **Newton/Brent hybrid** (Newton first, Brent fallback on non-convergence) — the "textbook correct" answer,
   but adds a second numerical code path to test and maintain for a failure mode that has not been observed
   with real portfolio data.

## Decision

**Keep Newton-Raphson only.** Do not implement a Brent/hybrid fallback. Accept the theoretical non-convergence
risk for the specific class of pathological inputs described in the analysis doc, because:
- Real portfolios (the target use case) don't produce cash-flow sequences pathological enough to trigger it.
- The **result cap** (a large but finite multiple applied to the computed rate) is the deliberate safety net
  for the rare case where Newton converges to an extreme root — it prevents a single reported number from being
  absurd (e.g. displaying "847,000,000%") without needing a second solver. The cap is a UX/display safety valve,
  not evidence of an unfixed bug in the root-finding.

## Consequences

- MWRR computation stays a single, simple code path (`roi_utils.py::calculate_mwrr()`), consistent with the
  rest of the engine's preference for straightforward, testable arithmetic over generalized numerical libraries
  (see [[concepts/twrr-mwrr-algorithms]]).
- If LibreFolio ever supports very high-frequency or adversarial cash-flow patterns (e.g. algorithmic trading
  import), this decision should be revisited — the Brent/hybrid option remains documented as the fallback path
  if convergence failures are ever observed with real user data.
- Future historians/ingests: do **not** record "Newton-only solver" or "MWRR result cap" as open problems in
  `wiki/problems/` — they belong here, as an accepted trade-off.

## Links

- [[decisions/mwrr-boundary-fix]] — the actual bug fix (double-counting deposits), a separate and unrelated
  issue from this solver-choice decision.
- [[concepts/twrr-mwrr-algorithms]] — algorithm documentation.
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/mwrr-numerical-stability-analysis.md`

## Source files

| Role | Path |
|------|------|
| MWRR/XIRR implementation | `backend/app/utils/roi_utils.py` |
| Numerical stability analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/mwrr-numerical-stability-analysis.md` |
| MWRR boundary anomaly report | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/mwrr_boundary_anomaly_report.md` |
