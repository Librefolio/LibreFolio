# 🧠 Portfolio AI Export

Portfolio AI Export prepares a Dashboard-scoped clipboard snapshot or a focused
analysis prompt. LibreFolio never sends the export to an AI service.

## 📍 Location

Open **Dashboard** and select **AI Export** in the top toolbar, beside
**Update/Sync**. Your draft is remembered for this user and Dashboard context.

## 🎯 Portfolio Tasks

| Task | Focus |
|---|---|
| **Recurring Investment Plan** | Portfolio structure, cash flows, constraints, and recurring-investment context. |
| **Portfolio Rebalancing** | Current allocation, concentration, diversification, and target-allocation context. |
| **Performance Attribution** | Main contributors and detractors over the selected period. |
| **Portfolio Income Review** | Dividends, interest, fees, taxes, and other income. |
| **Portfolio FIFO Lot Review** | Open lots and lots closed during the previous three months across the active Dashboard broker scope. |
| **Technical Breadth** | Technical states and signals across applicable assets. |
| **Portfolio Description** | Factual composition, allocation, valuation, and activity overview. |

## 🗂️ Scope and Data

The export follows the active broker filter, date range, and target currency.
Depending on the task, it can include portfolio totals, cash, positions,
allocations, performance, contributions, income, data-quality context, and
backend-computed technical results.

!!! note "FIFO rows are summaries, not histories"

    Portfolio FIFO Lot Review includes every open or partially closed lot plus
    fully closed lots whose closing date falls within the previous three calendar
    months. Each row identifies the asset, opening date, and opening broker, then
    summarizes quantities, residual cost, value, results, income, fees, and taxes.
    It does not export custody, event, value, return, or price timelines.

## 📸 Snapshot and Analyses

- **Data Snapshot** copies factual structured data only. It contains no analysis
  instructions or response contract.
- An **analysis task** adds task-specific instructions and a response contract.
  The requested response language always follows the current LibreFolio
  interface language.
- Optional notes are included only for tasks that support them.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Latest values and aggregates only; no time series. FIFO review selects up to 7 largest open/partial lots by residual cost plus 3 most recently closed lots, then fills unused quota up to 10. |
| **Standard** | All applicable entities; up to **7 recent daily points** plus **8 preceding weekly points**. |
| **Full** | All applicable entities; **7 recent daily points** plus weekly points across the **full technical window**. |

A task/profile may omit sections whose data is unavailable or not applicable.
The separate **Technical window** selector uses **3M** by default and can be set
to **6M**, **1Y**, or a custom duration. It always ends on the snapshot date and
does not change the Dashboard's selected financial range.

## 🔒 Applicability, Errors, and Privacy

Unavailable tasks or detail choices stay disabled. AI Export also fails closed
when browser and server catalogs or response contracts do not match. Typed
errors explain missing applicability, inaccessible entities, source failures,
or contract problems without exposing internal details.

The clipboard can contain sensitive financial data. Review it before pasting it
into a third-party service. See the [AI Export overview](index.md)
for the cross-domain workflow and safety model.
