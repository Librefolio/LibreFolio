# 🧠 Broker AI Export

Broker AI Export prepares a clipboard snapshot or analysis prompt limited to one
accessible broker. LibreFolio never sends it to an AI service.

## 📍 Location

Open a Broker detail page and select **AI Export** in the top toolbar. Your draft
is remembered separately for this user and broker.

## 🎯 Broker Tasks

| Task | Focus |
|---|---|
| **Broker Review** | Holdings, cash, activity, performance, and data coverage. |
| **Broker Cost Efficiency** | Fees, taxes, turnover, and cost patterns. |
| **Broker Concentration Context** | Asset, currency, and portfolio-share concentration. |
| **FIFO Lot Review** | Open lots and lots closed during the previous three months, with one summary row per eligible lot. |

## 🗂️ Scope and Data

The export is limited to the selected broker and current date range and target
currency. Depending on the task, it can include cash balances, positions,
transactions, performance, costs, allocation, concentration, income, and FIFO
lot summaries. Server-side access checks prevent exporting a broker the
current user cannot read.

!!! important "FIFO rows are summaries, not histories"

    FIFO Lot Review includes every open or partially closed lot plus fully closed
    lots whose closing date falls within the previous three calendar months. Each
    row identifies the asset and opening date and summarizes quantities, residual
    cost, value, results, income, fees, and taxes. It does not export custody,
    event, value, return, or price timelines.

## 📸 Snapshot and Analyses

- **Data Snapshot** copies factual structured broker data only.
- An **analysis task** adds task-specific instructions and a response contract.
  The requested response language follows the current LibreFolio interface
  language.
- Optional notes are included only when supported by the selected task.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Latest values and aggregates only; no time series. FIFO review selects up to 7 largest open/partial lots by residual cost plus 3 most recently closed lots, then fills unused quota up to 10. |
| **Standard** | All applicable entities; up to **7 recent daily points** plus **8 preceding weekly points**. |
| **Full** | All applicable entities; **7 recent daily points** plus weekly points across the **full technical window**. |

A task/profile may omit sections whose data is unavailable or not applicable.
The separate **Technical window** selector uses **3M** by default and can be set
to **6M**, **1Y**, or a custom duration. It always ends on the snapshot date and
does not change the Broker page's selected financial range.

## 🔒 Applicability, Errors, and Privacy

Tasks can be unavailable when required facts do not exist—for example, FIFO Lot
Review without eligible open or recently closed lots. Choices also fail closed on catalog or contract
mismatch. Typed errors report access, applicability, source, or contract
problems.

The clipboard can contain sensitive account and transaction data. Review it
before sharing. See the [AI Export overview](index.md) for the
cross-domain workflow and safety model.
