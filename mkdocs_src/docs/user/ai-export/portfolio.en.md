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
| **Technical Breadth** | Technical states and signals across applicable assets. |
| **Portfolio Description** | Factual composition, allocation, valuation, and activity overview. |

## 🗂️ Scope and Data

The export follows the active broker filter, date range, and target currency.
Depending on the task, it can include portfolio totals, cash, positions,
allocations, performance, contributions, income, data-quality context, and
backend-computed technical results.

!!! note "FIFO lot analysis is not a Portfolio task yet"

    The Dashboard export does not currently include the FIFO Engine's per-lot
    timelines. The Broker FIFO task is aggregate and broker-scoped. A future
    Portfolio FIFO task would need a dedicated contract for selected lots and
    their custody, event, value, return, and price histories.

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
| **Compact** | Latest values and aggregates only; no time series. Where applicable, the task profile uses an explicit compact selection of portfolio entities. |
| **Standard** | All applicable entities; up to **7 recent daily points** plus **8 preceding weekly points**. |
| **Full** | All applicable entities; **7 recent daily points** plus weekly points across the **full technical window**. |

A task/profile may omit sections whose data is unavailable or not applicable.

## 🔒 Applicability, Errors, and Privacy

Unavailable tasks or detail choices stay disabled. AI Export also fails closed
when browser and server catalogs or response contracts do not match. Typed
errors explain missing applicability, inaccessible entities, source failures,
or contract problems without exposing internal details.

The clipboard can contain sensitive financial data. Review it before pasting it
into a third-party service. See the [AI Export overview](index.md)
for the cross-domain workflow and safety model.
