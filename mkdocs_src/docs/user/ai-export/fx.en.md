# 🧠 FX AI Export

FX Detail AI Export prepares a clipboard snapshot or focused analysis prompt for
the canonical currency pair currently open. LibreFolio never sends it to an AI
service.

## 📍 Location

Open an FX detail page. In the **Signals** header, select **AI Export**. Your
draft is remembered separately for this user and canonical pair.

## 🎯 FX Analyses

| Task | Focus |
|---|---|
| **FX Trend Review** | Pair direction, returns, volatility, and technical context. |
| **FX Conversion Timing Context** | Trend, volatility, and rate context for a possible conversion. |
| **FX Exposure Impact** | Direct cash, trading-currency, and valuation-currency links to the pair. |

## 🗂️ Scope and Data

The export uses the page's canonical pair, selected date range, target currency,
rate history, provider context, and backend-computed technical results.

## 📤 Export Data and Request Analysis

- **Export Data** copies one factual FX dataset only.
- **Request Analysis** adds task-specific instructions, a response contract, and
  the datasets declared for the Analysis.
  The requested response language follows the current LibreFolio interface
  language.
- Optional notes are included only when supported by the selected Analysis.

Available exports include FX Overview, Market Context, Conversion Timing Context,
Market & Technical Data, Direct Exposure, and All FX Data.

## 📉 Partial History

When the requested AI period begins before stored rate history, LibreFolio exports
the genuine history it can use and reports:

- requested and available dates;
- coverage;
- observed and backward-filled counts;
- partial Signal;
- omitted Signal and reasons;
- insufficient-history warnings.

No future rate is used. A partial Signal is not presented as equivalent to a full
history.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Same data universe with the sparsest supported temporal buckets (up to 30 days). |
| **Standard** | Same data universe with temporal buckets up to 14 days. |
| **Full** | Same data universe with temporal buckets up to 7 days. |

A dataset or Analysis can omit unavailable or non-applicable optional sections.
The **AI period** ends on the snapshot date.

## 🔒 Applicability, Errors, and Privacy

Analyses or detail choices can be disabled when required data is absent. Catalog
and response-contract mismatches fail closed. Typed errors report applicability,
source, entity, or contract problems.

The clipboard can contain sensitive currency and portfolio exposure data. Review
it before sharing. See the [AI Export overview](index.md) for
the cross-domain workflow and safety model.
