---
title: "An ADJUSTMENT is never a price; a holding with no price at all is valued at cost (J-17, decided 16/10)"
category: decision
status: accepted
date: 2026-10-16
tags: [backend, valuation, price-resolver, adjustment, transfer, capital, data-quality, ai-export, pac, release-1.3]
related:
  - decisions/financial-math-one-home
  - decisions/orphan-transfer-becomes-an-adjustment
  - entities/portfolio-engine
  - problems/stale-price-banner-never-emitted
  - decisions/ai-export-version-bump-once-per-release
---

# Decision: an ADJUSTMENT is never a price; no price at all → valued at cost

## Context
Until 1.2 the unified price resolver (`financial_math/price_marks.py`) took three kinds of trade observations: BUY,
SELL and an ADJUSTMENT carrying a cost basis. An opening position, a succession or a transfer from an untracked broker
therefore **marked the asset's price at its cost**. Two visible consequences:
- a day whose newest observation was such an adjustment replaced the previous quote or trade with a cost;
- a foreign asset priced only by adjustments was revalued every day at that day's rate, so a book cost produced an
  FX gain or loss that never happened.

## Options considered
1. **Valued at cost, no price** (option A): the adjustment sets the cost only; with no observation at all the holding
   counts at its book cost, declared as an estimate.
2. **MISSING**: no price → out of the NAV, with an error banner, until a quote arrives.
3. Keep the adjustment as a price (status quo).

## Decision
The developer chose **A** (P2, 16/10), and confirmed that **a SELL stays a price source**: only BUY and SELL observe.
The rule is applied day by day with no look-ahead:
- a day with no quote and no BUY or SELL on or before it, with the position's cost known in the report currency, is
  valued at that cost as `ValuationSource.ESTIMATED_AT_COST`;
- from the first observation on the price wins, an old one too (carried, `stale`);
- an unknown or incomplete cost stays `MISSING`.

The hierarchy is MARKET_PRICE > LAST_TRADE_PRICE > ESTIMATED_AT_COST > MISSING. An at-cost holding has no
`current_price`, no unit price and no unrealized P&L (neither the price nor the FX part).

## Consequences
- **Data quality:** a new warning, `VALUED_AT_COST`. It lists assets with a provider only (for a manual asset the cost
  is its intended value), after the 14-day grace, which counts from the asset's **first acquisition**: ADJUSTMENT and
  TRANSFER count, unlike `TRANSACTION_IMPLIED`'s BUY/SELL dates.
  - Pitfall found in review: fed with the BUY/SELL first-position dates, the grace never applied, because such an asset
    has neither, so it was listed at once.
- **Capital of unpriced transfers follows the pool's book cost**, as for in-kind ADJUSTMENTs:
  - an orphan TRANSFER leg moves `step.cost_report_change`;
  - an internal pair moves the cost the arrival adds to the **receiver's** pool, at the sender's share (lot 41: "what the
    arrival brings into the receiver's NAV, as the NAV values it").
  - The pool counts an unknown or unconvertible cost as zero, so this stays consistent with a pool of partly unknown cost
    too: the gap stays with the broker whose cost is unknown (P22), and nothing is left in capital once the units are gone.
  - Pitfall: a completeness check ("only when the pool is complete before and after") looked safer but left a
    permanent artifact. A priced ADJUSTMENT-in (+50) followed by an orphan transfer out of everything kept −50 forever.
- **Lots:** an asset priced only by adjustments has its lots at cost, and its histories start at the first quote, BUY or
  SELL.
  - *Update 2026-10-16 (CP-7b):* the lots now follow the Dashboard's rule **day by day** (coordinator's decision (a):
    «one rule in the whole app, and no gap the Dashboard doesn't have»). An open LONG lot is at cost on every day with
    no observation on or before it — the days before the asset's first quote, BUY or SELL — even when the asset is priced
    later (`lots/prices.py::last_day_without_observation`, the service's `at_cost_until`). A price without a rate stays
    a gap. `CURRENT_PRICE_ASSUMED_AT_COST` names exactly those days, so J-28 is closed. The lot summary is at cost only
    when the end date has no observation. The reference of a lot opened by an ADJUSTMENT is the home's mark on its
    opening day (trades included, `exact` only for that day's quote), converted at the opening date's rate (P21).
  - Left open: a costless ADJUSTMENT-in opens a zero-cost FIFO lot (shown at 0 on at-cost days), while the average cost
    counts it unknown (J-35). The lots' ROI/TWRR history still skips unpriced days (J-33).
- **AI Export:** `unit_price` is null for at-cost rows. Versions: `asset.provenance` 2, `asset.positions_by_broker` 2,
  `portfolio.provenance` and `broker.provenance` 3, `portfolio.positions` and `broker.positions` 2.
  - A component bumped without its `COMPACT_COMPONENT_VERSIONS` entry falls back to YAML (`DEFAULT_COMPACT_VERSIONS = {1}`).
- **PAC planner:** keeps the `ESTIMATED_AT_COST` code and labels the holding «valued at cost · no price».
- A position with a priced and an unpriced adjustment and no price is now `MISSING` (incomplete cost), where before it
  was valued at the adjustment's price.

## Source files
| Role | Path |
|------|------|
| Price observations (BUY/SELL only) | `backend/app/services/financial_math/price_marks.py` |
| Valuation at cost, transfer capital | `backend/app/services/financial_math/portfolio/daily_state.py` |
| Valuation sources | `backend/app/services/financial_math/portfolio/models.py` |
| `VALUED_AT_COST` issue | `backend/app/services/financial_math/portfolio/data_quality.py` |
| Grace and listing | `backend/app/services/portfolio_service.py` |
| Cost pool (zero-cost convention) | `backend/app/services/financial_math/average_cost.py` |
| Lots: reference price, days at cost (CP-7b) | `backend/app/services/financial_math/lots/prices.py` |
| Lots: at-cost warning range | `backend/app/services/lots_analysis_service.py` |
| AI Export semantics and unit price | `backend/app/services/ai_export/components/asset_core.py` |
| PAC source mapping | `frontend/src/lib/features/tools/pac-allocator/planner/source.ts` |

## Links
- [[decisions/financial-math-one-home]]
- [[entities/portfolio-engine]]
- Source: `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md`,
  §10 «J-17», «CP-7b — codice»; backlog J-17, J-28, J-29, J-33, J-35.
