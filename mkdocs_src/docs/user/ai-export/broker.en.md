# 🧠 Broker AI Export

Broker AI Export prepares a clipboard snapshot or analysis prompt limited to one
accessible broker. LibreFolio never sends it to an AI service.

## 📍 Location

Open a Broker detail page and select **AI Export** in the top toolbar. Your draft
is remembered separately for this user and broker.

## 🎯 Broker Analyses

| Task | Focus |
|---|---|
| **Broker Review** | Holdings, cash, activity, performance, and data coverage. |
| **Broker Cost Efficiency** | Fees, taxes, turnover, and cost patterns. |
| **Broker Concentration Context** | Asset, currency, and portfolio-share concentration. |
| **FIFO Lot Review** | Open lots and lots closed during the previous three months, with one summary row per eligible lot. |

## 🗂️ Scope and Data

The export is limited to the selected broker and current date range and target
currency. Depending on the selection, it can include cash balances, positions,
transactions, performance, costs, allocation, concentration, income, and FIFO
lot summaries. Server-side access checks prevent exporting a broker the
current user cannot read.

!!! important "FIFO rows are summaries, not histories"

    FIFO Lot Review includes every open or partially closed lot plus fully closed
    lots whose closing date falls within the previous three calendar months. Each
    row identifies the asset and opening date and summarizes quantities, residual
    cost, value, results, income, fees, and taxes. It does not export custody,
    event, value, return, or price timelines.

## 📤 Export Data and Request Analysis

- **Export Data** copies one factual Broker dataset only.
- **Request Analysis** adds task-specific instructions, a response contract, and
  the datasets declared for the Analysis.
  The requested response language follows the current LibreFolio interface
  language.
- Optional notes are included only when supported by the selected Analysis.

Available exports include Broker Overview, Performance & Flows, Technical Summary,
Asset Comparison, Drawdown Context, Concentration Evidence, Cost Efficiency
Evidence, complete Technical Data, FIFO Lots, and All Broker Data.

## 🧾 Broker Cost Efficiency

Cost Efficiency keeps these values separate:

- recorded fees;
- taxes;
- total recorded costs;
- trading activity and deterministic denominators;
- valid cost ratios.

`recorded` with amount 0 means the source contains a real zero. `unavailable`
means the source does not support the value and does not mean zero.
`not applicable` means the inputs exist but the denominator makes the ratio
meaningless. Ratios appear only with valid inputs and include their formula,
numerator, denominator, unit, period, and coverage.

Trading, FX, or other cost subcategories remain unavailable when the Broker data
does not classify them separately.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Same data universe with the sparsest supported temporal buckets (up to 30 days). |
| **Standard** | Same data universe with temporal buckets up to 14 days. |
| **Full** | Same data universe with temporal buckets up to 7 days. |

A dataset or Analysis can omit unavailable or non-applicable optional sections.
The **AI period** ends on the snapshot date. Partial history and coverage remain
explicit.

## 🔒 Applicability, Errors, and Privacy

Analyses can be unavailable when required facts do not exist—for example, FIFO Lot
Review without eligible open or recently closed lots. Choices also fail closed on catalog or contract
mismatch. Typed errors report access, applicability, source, or contract
problems.

The clipboard can contain sensitive account and transaction data. Review it
before sharing. See the [AI Export overview](index.md) for the
cross-domain workflow and safety model.
