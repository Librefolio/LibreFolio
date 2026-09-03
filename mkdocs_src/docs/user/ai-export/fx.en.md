# 🧠 FX AI Export

FX Detail AI Export prepares a clipboard snapshot or focused analysis prompt for
the canonical currency pair currently open. LibreFolio never sends it to an AI
service.

## 📍 Location

Open an FX detail page. In the **page toolbar**, select **AI Export**. Your
draft remains available for 10 minutes in the current login session and resets
after logout or a new login.

## 🎯 FX Analyses

| Task                   | Focus                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------- |
| **FX Pair Analysis**   | Pair direction, returns, volatility, technical evidence, coverage, and dated macro context. |
| **FX Exposure Impact** | Direct cash, trading-currency, and valuation-currency links to the pair.                    |

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

Two public data exports are available:

- **FX Market & Exposure** — current quote-per-base rate, 8/16/30 observed path
  points, focused trend/momentum/volatility, 30-day and 91-day returns, range
  position, source coverage, missing user inputs, and direct exposure;
- **FX Market History** — denser rate buckets, returns, indicators, states, events,
  and coverage.

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

| Detail       | Exact sampling                                                                                                      |
| ------------ | ------------------------------------------------------------------------------------------------------------------- |
| **Compact**  | General export: up to 8 uniform observed rate points. Detailed export: up to 5 non-empty indicator rows per Signal. |
| **Standard** | General export: up to 16 points. Detailed export: up to 10 indicator rows.                                          |
| **Full**     | General export: up to 30 points. Detailed export: every non-empty indicator bucket and can be large.                |

A dataset or Analysis can omit unavailable or non-applicable optional sections.
The **AI period** ends on the snapshot date.

## 🔒 Applicability, Errors, and Privacy

Analyses or detail choices can be disabled when required data is absent. Catalog
and response-contract mismatches fail closed. Typed errors report applicability,
source, entity, or contract problems.

The clipboard can contain sensitive currency and portfolio exposure data. Review
it before sharing. See the [AI Export overview](index.md) for
the cross-domain workflow and safety model.
