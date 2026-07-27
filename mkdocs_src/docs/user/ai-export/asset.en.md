# 🧠 Asset AI Export

Asset Detail AI Export prepares a clipboard snapshot or focused analysis prompt
for the asset currently open. LibreFolio never sends it to an AI service.

## 📍 Location

Open an Asset detail page. In the **Signals** header, select **AI Export**. Your
draft is remembered separately for this user and asset.

## 🎯 Asset Tasks

| Task | Focus |
|---|---|
| **Data Snapshot** | Raw asset identity, valuation, position, performance, and available technical facts. |
| **Asset Trend Analysis** | Price trend, normalized returns, drawdown, and technical signals. |
| **Position Review** | Position size, cost basis, performance, income, and concentration. |
| **Drawdown and Recovery** | Drawdown depth, duration, recovery progress, and related context. |

## 🗂️ Scope and Data

The export uses the current asset, selected date range, display/target currency,
and the user's accessible broker scope when portfolio context is required.
Depending on the task, it can include identifiers, prices, returns, valuation,
position and FIFO facts, income, corporate events, and backend-computed technical
results. The browser does not recalculate indicators.

## 📸 Snapshot and Analyses

- **Data Snapshot** uses the backend Asset Snapshot facts, but copies them as raw
  structured data without analysis instructions or interpretation.
- An **analysis task** uses relevant facts and adds task-specific instructions
  plus a response contract so the receiving AI can interpret them. The requested
  response language follows the current LibreFolio interface language.
- Optional notes are included only when supported by the selected task.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Latest values and aggregates only; no time series. Where applicable, the task profile explicitly selects relevant position, lot, or event entities. |
| **Standard** | All applicable entities; up to **7 recent daily points** plus **8 preceding weekly points**. |
| **Full** | All applicable entities; **7 recent daily points** plus weekly points across the **full technical window**. |

A task/profile may omit sections whose data is unavailable or not applicable.

## 🔒 Applicability, Errors, and Privacy

Position Review requires position context. Other tasks can be disabled when
required facts are absent. Catalog and response-contract mismatches fail closed.
Typed errors report applicability, missing entities, source failures, or
contract problems.

The clipboard can contain sensitive holdings and performance data. Review it
before sharing. See the [AI Export overview](index.md) for
the cross-domain workflow and safety model.
