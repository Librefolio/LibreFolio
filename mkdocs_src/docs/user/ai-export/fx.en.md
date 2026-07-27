# 🧠 FX AI Export

FX Detail AI Export prepares a clipboard snapshot or focused analysis prompt for
the canonical currency pair currently open. LibreFolio never sends it to an AI
service.

## 📍 Location

Open an FX detail page. In the **Signals** header, select **AI Export**. Your
draft is remembered separately for this user and canonical pair.

## 🎯 FX Tasks

| Task | Focus |
|---|---|
| **Data Snapshot** | Raw pair, rate-history, provider, and technical facts. |
| **FX Trend Review** | Pair direction, returns, volatility, and technical context. |
| **FX Conversion Timing Context** | Trend, volatility, and rate context for a possible conversion. |

## 🗂️ Scope and Data

The export uses the page's canonical pair, selected date range, target currency,
rate history, provider context, and backend-computed technical results.

## 📸 Snapshot and Analyses

- **Data Snapshot** copies factual structured FX data only.
- An **analysis task** adds task-specific instructions and a response contract.
  The requested response language follows the current LibreFolio interface
  language.
- Optional notes are included only when supported by the selected task.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Latest values and aggregates only; no time series. Where applicable, the task profile explicitly selects relevant entities. |
| **Standard** | All applicable entities; up to **7 recent daily points** plus **8 preceding weekly points**. |
| **Full** | All applicable entities; **7 recent daily points** plus weekly points across the **full technical window**. |

A task/profile may omit sections whose data is unavailable or not applicable.

## 🔒 Applicability, Errors, and Privacy

Tasks or detail choices can be disabled when required data is absent. Catalog
and response-contract mismatches fail closed. Typed errors report applicability,
source, entity, or contract problems.

The clipboard can contain sensitive currency and portfolio exposure data. Review
it before sharing. See the [AI Export overview](index.md) for
the cross-domain workflow and safety model.
