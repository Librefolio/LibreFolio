# 🧠 Portfolio AI Export

Portfolio AI Export prepares a Dashboard-scoped clipboard snapshot or a focused
analysis prompt. LibreFolio never sends the export to an AI service.

## 📍 Location

Open **Dashboard** and select **AI Export** in the top toolbar, beside
**Update/Sync**. Your draft is remembered for this user and Dashboard context.

## 🎯 Portfolio Analyses

| Task | Focus |
|---|---|
| **Recurring Investment Plan** | Portfolio structure, cash flows, constraints, and recurring-investment context. |
| **Portfolio Rebalancing** | Current allocation, concentration, diversification, and target-allocation context. |
| **Performance Attribution** | Main contributors and detractors over the selected period. |
| **Portfolio News & Price Drivers** | Dated Asset movements matched with cited current news, qualified as supported, inferred, speculative, or unexplained. |
| **Portfolio Income Review** | Dividends, interest, fees, taxes, and other income. |
| **Portfolio FIFO Lot Review** | Open lots and lots closed during the previous three months across the active Dashboard broker scope. |
| **Technical Breadth** | Technical states and signals across applicable assets. |
| **Portfolio Description** | Factual composition, allocation, valuation, and activity overview. |

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

!!! note "FIFO rows are summaries, not histories"

    Portfolio FIFO Lot Review includes every open or partially closed lot plus
    fully closed lots whose closing date falls within the previous three calendar
    months. Each row identifies the asset, opening date, and opening broker, then
    summarizes quantities, residual cost, value, results, income, fees, and taxes.
    It does not export custody, event, value, return, or price timelines.

## 📤 Export Data and Request Analysis

- **Export Data** copies one factual Portfolio dataset without analysis
  instructions or a response contract.
- **Request Analysis** adds task-specific instructions, a response contract, and
  the datasets declared for the selected Analysis.
  The requested response language always follows the current LibreFolio
  interface language.
- Optional notes are included only for analyses that support them.

Available data exports include Portfolio Overview, Performance & Flows, Technical
Summary, Asset Snapshot, Asset Comparison, Drawdown Context, Income Evidence,
complete Technical Data, FIFO Lots, and All Portfolio Data.

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

Portfolio Drawdown and a compact per-Asset Drawdown comparison are historical
context only. They are not forecasts or standalone purchase signals, and no Asset
Drawdown history is added.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Same Asset/Signal universe; up to 5 non-empty indicator rows per Asset/Signal and a 7-day/minimum-3 event policy. |
| **Standard** | Same Asset/Signal universe; up to 10 non-empty indicator rows per Asset/Signal and a 21-day/minimum-10 event policy. |
| **Full** | Every non-empty indicator bucket and the 30-day/minimum-20 event policy. Use it only when the extra history density matters. |

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
