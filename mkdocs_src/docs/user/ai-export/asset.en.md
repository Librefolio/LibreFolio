# 🧠 Asset AI Export

Asset Detail AI Export prepares a clipboard snapshot or focused analysis prompt
for the asset currently open. LibreFolio never sends it to an AI service.

## 📍 Location

Open an Asset detail page. In the **page toolbar**, select **AI Export**. Your
draft remains available for 10 minutes in the current login session and resets
after logout or a new login.

## 🎯 Asset Analyses

| Task                      | Focus                                                                                                 |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Position Review**       | Position size, cost basis, performance, income, and concentration.                                    |
| **Asset Market Analysis** | Observed-close history, returns, trend, momentum, volatility, Drawdown, states, events, and coverage. |

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

Two public data exports are available:

- **Asset Position & History** — positions per Broker, cost, value, P&L,
  recorded-zero period semantics, economic lots with allocated fees/taxes, compact
  market history, Drawdown, and provenance;
- **Asset Market History** — observed-close buckets, returns, indicators, states,
  events, Drawdown, and coverage.

## 📏 Detail and Sampling

| Detail       | Exact sampling                                                                                                        |
| ------------ | --------------------------------------------------------------------------------------------------------------------- |
| **Compact**  | Position export: up to 8 uniform observed history points. Market export: up to 5 non-empty indicator rows per Signal. |
| **Standard** | Position export: up to 16 points. Market export: up to 10 indicator rows.                                             |
| **Full**     | Position export: up to 30 points. Market export: every non-empty indicator bucket and can be large.                   |

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
