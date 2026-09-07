# 🧠 Portfolio AI Export

Portfolio AI Export prepares a Dashboard-scoped clipboard snapshot or a focused
analysis prompt. LibreFolio never sends the export to an AI service.

## 📍 Location

Open **Dashboard** and select **AI Export** in the top toolbar, beside
**Refresh**. The draft remains available for 10 minutes in the current login
session and resets after logout or a new login.

## 🎯 Portfolio Analyses

| Task                                       | Focus                                                                                                                                                                 |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Recurring Investment Plan**              | Portfolio structure, cash flows, constraints, and recurring-investment context.                                                                                       |
| **Portfolio Rebalancing**                  | Current allocation, concentration, diversification, and target-allocation context.                                                                                    |
| **Portfolio Performance & Market Drivers** | Performance reconciliation plus dated short- and long-horizon research for every held Asset.                                                                          |
| **Capital-Loss Offset Strategies**         | Conditional ways to use available or expiring tax losses against potentially eligible gains, using economic FIFO evidence and the user's official tax-loss inventory. |

## 🗂️ Scope and Data

The export follows the active broker filter, date range, and target currency.
Depending on the selection, it can include portfolio totals, cash, positions,
allocations, performance, contributions, income, data-quality context, and
backend-computed technical results.

The prompt distinguishes:

- Brokers included in the calculation scope;
- Brokers with current open positions;
- Brokers represented by performance contributors in the AI period.

A scoped Broker can have no current position. B# references remain consistent with
the Entity Directory.

!!! note "Economic FIFO is not legal tax treatment"

    The general export contains one compact economic FIFO summary per Asset.
    **Capital-Loss Offset Strategies** additionally receives every applicable lot.
    Before comparing no-action, gain-realization, staged, or loss-harvesting paths,
    the prompt asks for tax residence, regime, account type, official tax-loss
    inventory (for example the Italian `cassetto fiscale`), legal category,
    remaining and used amounts, origin/expiry dates, offset rules, and constraints.

## 📤 Export Data and Request Analysis

- **Export Data** copies one factual Portfolio dataset without analysis
  instructions or a response contract.
- **Request Analysis** adds task-specific instructions, a response contract, and
  the datasets declared for the selected Analysis.
  The requested response language always follows the current LibreFolio
  interface language.
- Optional notes are included only for analyses that support them.

Two public data exports are available:

- **Portfolio Overview & History** — positions, cash, allocations, concentration,
  performance path, flows, income, costs, reconciliation, economic FIFO summary,
  compact per-Asset history, Drawdown, coverage, and provenance;
- **Portfolio Asset History** — denser observed-close price buckets, indicators,
  states, events, coverage, and breadth for the eligible Asset universe.

## 📅 Recurring Investment Plan

The Analysis uses supplied facts first and asks only for missing preferences that
materially change the plan. Questions are grouped into:

- capital and contribution frequency;
- objectives and horizon;
- risk preferences, including acceptable volatility or temporary Drawdown;
- operational constraints such as liquidity, Brokers, minimum orders, exclusions,
  or whether sales are allowed.

The prompt distinguishes indispensable answers from optional refinements and can
still offer conditional scenarios. It never invents budget, targets, or risk
tolerance.

It compares immediate and staged deployment. Conditional waiting appears only
when broad and persistent declining evidence exists across the Portfolio, never
from one Asset or one indicator.

Portfolio Drawdown and a compact per-Asset Drawdown comparison are historical
context only. They are not forecasts or standalone purchase signals, and no Asset
Drawdown history is added.

## 📰 Performance and Market Drivers

The receiving AI is instructed to cover every held Asset, cite dated sources,
assess source quality, provide short- and long-horizon theses, distinguish
chronology/correlation from causality, and label links as supported, plausible,
inferred, speculative, or unexplained.

## 📏 Detail and Sampling

| Detail       | Exact sampling                                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Compact**  | General export: 8 Portfolio path points and up to 6 points per eligible Asset. Detailed export: up to 5 non-empty indicator rows per Asset/Signal.          |
| **Standard** | General export: 16 Portfolio path points and up to 12 points per eligible Asset. Detailed export: up to 10 indicator rows.                                  |
| **Full**     | General export: 30 Portfolio path points and up to 24 points per eligible Asset. Detailed export: every non-empty indicator bucket; this can be very large. |

A dataset or Analysis can omit unavailable or non-applicable optional sections.
The **AI period** uses 3M, 6M, 1Y, or Custom when offered and always ends on the
snapshot date. Completely empty temporal rows are omitted, while period/coverage
metadata and observed zero values remain.

## 🔒 Applicability, Errors, and Privacy

Unavailable tasks or detail choices stay disabled. AI Export also fails closed
when browser and server catalogs or response contracts do not match. Typed
errors explain missing applicability, inaccessible entities, source failures,
or contract problems without exposing internal details.

The clipboard can contain sensitive financial data. Review it before pasting it
into a third-party service. See the [AI Export overview](index.md)
for the cross-domain workflow and safety model.
