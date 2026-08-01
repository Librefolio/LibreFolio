# 🧠 Asset AI Export

Asset Detail AI Export prepares a clipboard snapshot or focused analysis prompt
for the asset currently open. LibreFolio never sends it to an AI service.

## 📍 Location

Open an Asset detail page. In the **Signals** header, select **AI Export**. Your
draft is remembered separately for this user and asset.

## 🎯 Asset Analyses

| Task | Focus |
|---|---|
| **Asset Trend Analysis** | Price trend, normalized returns, drawdown, and technical signals. |
| **Position Review** | Position size, cost basis, performance, income, and concentration. |

## 🗂️ Scope and Data

The export uses the current asset, selected date range, display/target currency,
and the user's accessible broker scope when portfolio context is required.
Depending on the selection, it can include identifiers, prices, returns, valuation,
position and FIFO facts, income, corporate events, and backend-computed technical
results. The browser does not recalculate indicators.

## 📤 Export Data and Request Analysis

- **Export Data** copies a selected factual Asset dataset without analysis
  instructions or interpretation.
- **Request Analysis** uses relevant facts and adds task-specific instructions
  plus a response contract so the receiving AI can interpret them. The requested
  response language follows the current LibreFolio interface language.
- Optional notes are included only when supported by the selected Analysis.

Available data exports include Asset Overview, Position Performance, Position
Context, Asset Drawdown Context, Market & Technical Data, and All Asset Data.
Drawdown Context is data/evidence; there is no separate Drawdown Recovery Analysis.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Same data universe with the sparsest supported temporal buckets (up to 30 days). Focused Position Context can include a very small recent history. |
| **Standard** | Same data universe with temporal buckets up to 14 days. |
| **Full** | Same data universe with temporal buckets up to 7 days. |

A dataset or Analysis can omit unavailable or non-applicable optional sections.
The **AI period** ends on the snapshot date. Available dates, coverage, partial
Signal, and omission reasons remain explicit.

## 🔒 Applicability, Errors, and Privacy

Position Review requires position context. Other tasks can be disabled when
required facts are absent. Catalog and response-contract mismatches fail closed.
Typed errors report applicability, missing entities, source failures, or
contract problems.

The clipboard can contain sensitive holdings and performance data. Review it
before sharing. See the [AI Export overview](index.md) for
the cross-domain workflow and safety model.
