---
title: "The P&L day change is shown as a share of yesterday's portfolio value; the share of the total P&L is removed"
category: decision
status: resolved
date: 2026-11-07
tags: [dashboard, portfolio, kpi, financial-math, api, breaking-change, release-1.3]
related:
  - decisions/portfolio-pnl-series-contracts
  - decisions/api-routes-removed-without-deprecation
  - entities/portfolio-engine
  - concepts/portfolio-report-unified
---

# Decision: the day change against yesterday's NAV

## Context

The first KPI card of the Dashboard showed the day's change of the total P&L in money and, under it, a percentage:
`pnl_change_1d_vs_total_pnl_percent`, the change divided by the absolute total P&L of the day before. Near zero that
base explodes: a total P&L going from −1 to +100 reads as about +10 100 %. The developer reported a 101 % that made no
sense (October notes, D8). The backend already sent a second share, `pnl_change_1d_vs_nav_percent`, the same change
divided by yesterday's portfolio value (NAV), which the second card also showed.

## Options considered

1. **(a)** Keep a percentage on card 1, computed on yesterday's NAV: the same number as card 2.
2. **(b)** Remove the percentage from card 1, so that every number appears once (the coordinator's advice).
3. A threshold in the backend that hides the P&L share near zero (left as a 1.4 note).

The kickoff of the October lots (07/11) first said «D8 is not done», still under discussion. The developer decided the
same day, and his answer wins.

## Decision

- Beside the money delta, card 1 shows the change **as a share of yesterday's whole-portfolio value**. It is also the
  average of the positions' one-day changes weighted by yesterday's weights, so it reads as «how much the portfolio
  moved today».
- The share of the accumulated P&L is gone, and so is the duplicate on card 2.
- Nobody else used it, so `summary.pnl_change_1d_vs_total_pnl_percent` was **removed from the API and the backend**,
  with no deprecation (the rule of [[decisions/api-routes-removed-without-deprecation]]) and a «Breaking changes» line in
  the 1.3 changelog. `DayChange` in `financial_math/portfolio/period.py` keeps only `pnl_change` and `vs_nav`.

## Consequences

- A test pins that the answer has no share of the total P&L (`a9e368c63`).
- User docs (`user/dashboard/kpi-cards`) and the developer page of the KPI cards describe the new line.
- A backend threshold for a P&L share stays a 1.4 note, to be discussed again only if the topic comes back.

## Links

- Sources: `TRIAGE-feedback-ottobre-20261107.md` (D8 and decision 4), `kickoff-w9-ottobre.md` (lot R9) — coordinator
  files kept outside the repository. Summary: [[sources/wave8-9-release-1.3-closing-2026-11]]
- Commits: `1560d8267` (API), `a0aa851d5` (card), `a9e368c63` (test).

## Source files

| Role | Path |
|------|------|
| The day change (amount and share of NAV) | `backend/app/services/financial_math/portfolio/period.py` |
| Report schema (`PortfolioSummary`) | `backend/app/schemas/portfolio.py` |
| Report assembly | `backend/app/services/portfolio_service.py` |
| KPI cards | `frontend/src/lib/features/dashboard/KpiSection.svelte` |
| KPI cards test | `frontend/src/lib/features/dashboard/KpiSection.test.ts` |
| User docs | `mkdocs_src/docs/user/dashboard/kpi-cards.en.md` |
| Changelog (Breaking changes) | `CHANGELOG.md` |
