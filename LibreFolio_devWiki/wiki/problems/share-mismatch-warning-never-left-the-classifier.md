---
title: "The transfer share-mismatch warning never left the classifier"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, portfolio-engine, data-quality, transfers, ownership-share, clarity, workstream-j]
related:
  - problems/unbounded-date-range-froze-the-instance
  - features/F-054
---

# Problem: the transfer share-mismatch warning never left the classifier

## Symptom

Two brokers owned at different shares: one at 100 % and one at 50 %, or a broker owned at 30 % and one only viewed,
which counts at 100 %. A linked transfer between them creates a gain or a loss out of nothing in the user's view:
- each leg counts at its own broker's share, so what leaves one broker and what reaches the other differ;
- by design that gap is a result, never capital (D-MF4 = a).

The engine had a warning for exactly this case, but no user ever saw it. Reported by MF as MF-J4; found larger than
filed by J on 17/10/2026 (J-43).

## Root Cause

Two defects, one on top of the other:

1. **Same-day pairs never warned.** In `financial_math/portfolio/classifier.py` the check sat inside the branch that
   builds the in-transit interval, which runs only when the two legs have different dates.
2. **No warning ever left the classifier, on any date.**
   - `engine.py` read `classified`, `in_transit_intervals` and `external_cash_flows`, never `warnings`.
   - `build_data_quality_report(classifier_warnings=…)` had no caller that passed it.
   - `DataQualityReport.share_mismatch_warnings` was filled by nothing.
   - The engine's own design table in commit `77b976ebc` (June) already marked the field «schema ✅, populated ❌».

## Solution (J-43 a + b, night decision N72)

- **Classifier**: once per pair, on any dates, a `ShareMismatch`: legs ordered by transaction id, with their brokers
  and shares, dated on the later leg.
- **Engine**: carries it as `PortfolioCalculationResult.share_mismatches`. The blob-cache key already holds every
  broker's role and share, so a cached result can't be stale.
- **`build_data_quality_report(share_mismatches=…)`**:
  - an INFO issue `TRANSFER_SHARE_MISMATCH` (`dataQuality.transferShareMismatch`, `{count}`, group
    `transfer_share_mismatch`, no CTA), counting the pairs complete by `period_to`. A pair before `period_from` counts
    too, since its result is in the cumulative figures;
  - one `share_mismatch_warnings` line per pair;
  - the status doesn't change.
- **Both `PortfolioService` builders** pass them on. The Dashboard banner renders the issue by key, with no UI code.
- **AI Export**: unaffected. It carries no data-quality codes, only `data_quality_status`.

## Side effects

- The native-cash golden changed in exactly the declared 12 paths: 6 `data_quality` blocks.
- The mock data gives the demo users (IB owned at 30 % / 40 %, same-day linked transfers) the INFO line on the
  real-data dashboard. The gallery shots of that dashboard change.

## Source files

| Role | Path |
|------|------|
| Classifier | `backend/app/services/financial_math/portfolio/classifier.py` |
| Models (`ShareMismatch`) | `backend/app/services/financial_math/portfolio/models.py` |
| Report builder | `backend/app/services/financial_math/portfolio/data_quality.py` |
| Engine | `backend/app/services/financial_math/portfolio/engine.py` |
| Service | `backend/app/services/portfolio_service.py` |
| Issue code | `backend/app/schemas/portfolio.py` |
| Message (4 languages) | `frontend/src/lib/i18n/dataQuality/en.json` |
| Developer docs | `mkdocs_src/docs/developer/frontend/data-quality-banner.md` |
| Plan | `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` |
