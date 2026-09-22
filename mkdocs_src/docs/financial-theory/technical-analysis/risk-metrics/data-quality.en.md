# 🧪 Data Quality

A risk figure is only as trustworthy as the observations behind it, so the amount and freshness of the underlying data belong to the reading of the result. LibreFolio does not keep that layer hidden: every risk result travels with a source-data report, a status derived from it, and — when something was missing — the list of what was missing.

---

## 🚦 Source-Data Status {: #source-data-status }

Source data is classified on three levels:

| Status | What it means |
|---|---|
| `ok` | Nothing missing, nothing held over. The series is what it claims to be. |
| `carried_forward` | The series is complete only because prices or exchange rates were held over from an earlier date — stale quotes, carried-forward price points, carried-forward FX points. |
| `partial` | Something is missing outright: prices, FX pairs, dates on which not every holding could be valued, unresolved currency pairs, or assets that could not participate at all. |

Two properties of this ladder matter more than the labels.

**It is derived, not declared.** The status is a computed property of the report's own contents: a producer cannot claim `ok` while reporting missing prices, because the status is recomputed from what the report holds. Anything missing outright yields `partial`; if nothing is missing but something was held over, `carried_forward`; otherwise `ok`. `partial` takes precedence over `carried_forward`.

**It is categorical, not numeric.** The status answers *what kind of imperfection is present*, never *how much is tolerable*. There is no level of completeness below which the system declares a figure untrustworthy — that judgement is left to the reader, deliberately and explicitly.

---

## 📋 What the Report Records {: #what-the-report-records }

The report is an inventory, not a score:

| Signal | What it captures |
|---|---|
| Missing price assets | Holdings for which no usable price could be obtained |
| Missing / unresolved FX pairs | Currency conversions that could not be resolved |
| Stale prices | Quotes older than the date they are being used for |
| Carried-forward price points | How many price points were held over, and for which assets |
| Carried-forward FX points | How many conversion points were held over, and for which pairs |
| Incomplete dates | Dates on which valuation, NAV, book value or allocation could not be completed for every holding |
| Unusable assets | Assets excluded before any metric was attempted, each with a reason |
| Warnings | Free-form notes attached by the producing stage |

Each entry names the object it concerns — the asset, the currency pair, the date. A reader can always ask *which* holding degraded the figure, not merely *whether* one did.

---

## 🧮 Alignment: What Missing Data Actually Costs {: #alignment-what-missing-data-actually-costs }

When an analysis spans several holdings — a correlation matrix, a risk-contribution breakdown — it is computed on a **single shared calendar**, and building that calendar is where missing data turns into a visible cost.

1. A date is a candidate if at least one holding had a fresh quote on it.
2. A candidate date enters the analysis only if **every** holding could be valued on it. Dates that fail this test are dropped for all holdings and recorded as incomplete valuation dates.
3. The baseline is the last date before the requested start on which all holdings were valuable; if there is none, the analysis starts inside the requested window instead, and the holdings responsible for the late start are named.

The consequence is worth stating plainly: **one holding with a gap shortens the window for everyone**. Nothing is silently interpolated to keep a date alive, and a holding is never partially included in a joint computation — either the date works for all of them or it is not an observation. Because those dropped dates land in the report, the result that used the shortened calendar is marked `partial`.

---

## 📏 Coverage {: #coverage }

Coverage is normally the density companion of the status: it answers *how much of what could have been observed actually was*. Several different ratios go by that name. They share no denominator, and they do not all measure the same kind of thing: two of them count observations, a third counts holdings and contains no observation at all.

**How much did the shared calendar cost?** Of the dates on which at least one holding had a fresh quote, this is the share that survived the requirement that every holding be valuable. A figure well below 1 means the intersection discarded a large part of the available dates.

**How much of the data is genuinely fresh?** Across the grid of holdings × observations, this is the share of points whose price was quoted on that date rather than held over from an earlier one. It is the numeric counterpart of the `carried_forward` status — and it counts prices only: a quote that is fresh but had to be converted with a carried-forward exchange rate still counts as fresh, because carried-forward conversions are tracked as their own separate signal.

**How much of the portfolio could be classified?** Of the holdings in scope, this is the share whose sector or geography metadata was available, rather than missing and sending the holding to the catch-all `Other` bucket at 100%. This one is a statement about metadata: no price, no date and no observation enters it. A [hypothetical shock](hypothetical-shock.md) reports this ratio.

!!! warning "One shared name, two kinds of quantity"

    When the figure is a density measure, its denominator depends on the path: for an analysis built from instrument quotes it is the candidate quote dates, while for a portfolio series it is the calendar days actually spanned. On a portfolio series that figure is high by construction — the engine emits a point for every calendar day whether or not anything was quoted, carrying the last known value forward when nothing was — so it certifies nothing about the prices behind it, and a lower figure on an instrument grid is simply the shape of a market that is closed part of the time.

    The question *were these prices quoted, or carried forward?* does have an answer in the system, but it is the freshness measure above, not the one a result carries under the name *coverage*. Which measure reaches any given screen is outside what this page describes.

    One discriminator settles it without any knowledge of the internals. **When a result reports `n_observations = 0` and `calendar_days = 0` next to a non-zero coverage, that coverage is not a statement about data density.** It cannot be: nothing was observed. It is reporting how much of the portfolio was classified.

    The distinction changes what should be done about the number. A coverage of 80%, read with the first two meanings in mind, says *a fifth of the prices are missing*. On a classification ratio it says a fifth of the sector or geography labels are missing. One is a gap in market data, the other a gap in asset metadata, and the two call for completely different actions. See [Observed Annualization](observed-annualization.md) for how the span and the observation count also produce the annualization factor.

---

## 🚫 Exclusions {: #exclusions }

An asset can leave the analysis at two different moments, and the distinction is recorded.

**Before any metric is attempted**, when its source data cannot support one: no usable price, no usable currency conversion, an invalid currency. These are reported as unusable assets, each carrying its reason.

**When the scope is resolved**, if the asset has no usable prepared return series at all. The requested scope is then reduced to the assets that survive, each exclusion keeps its reason, and a warning lists exactly which assets were dropped.

In neither case does the analysis refuse to run: it runs on what remains and says so. An excluded asset is a change in *what was measured*, which is why it forces the result out of the clean state.

---

## 💡 Interpretation {: #interpretation }

Every analytic result carries a status of its own, distinct from the source-data one:

| Result status | Meaning |
|---|---|
| `ok` | Computed on complete source data, with nothing excluded and no degrading warning |
| `partial` | Computed, but on less than what was asked |
| `unavailable` | Not computed; a stable reason code explains why (insufficient history, data unavailable, undefined metric, incompatible scope or mode, …) |
| `failed` | The computation itself did not complete |

A result is `partial` when **any** of these holds: a warning that degrades the result is present; an asset was excluded from the scope; the analytic itself excluded something; or the source-data status is anything other than `ok`. In the last case an explicit warning is attached as well, so the degradation is never inferred from the status alone.

!!! info "How to read a partial result"

    `partial` does not mean *wrong*. It means the figure answers a slightly different question than the one asked — over a shorter window, or over fewer holdings. The figure and the reason travel together in the same payload, and they are meant to be read together: a drawdown measured with two holdings excluded is a fact about the remaining holdings, not about the portfolio.

Analytics also refuse to answer rather than answer badly. Each one declares the minimum number of observations it needs, and below that floor it is not computed at all: the result comes back `unavailable` with an `insufficient_history` reason carrying both the observations available and the number required. Risk contribution and comparison against a benchmark, for instance, both need at least 20. Correlation is the exception that proves the rule: the matrix as a whole runs on very little, but the floor is applied **cell by cell**, so a single pair with too short a shared history is marked insufficient while the rest of the matrix is still computed.

---

## ⚠️ Limitations {: #limitations }

!!! warning "A status describes the inputs, not the model"

    `ok` says the series was complete, not that the metric is appropriate, that the window is long enough, or that the past resembles the future. Every caveat on the metric pages still applies to a figure built on impeccable data.

!!! warning "Carried-forward data flatters a risk figure"

    A price held over from the previous date produces a period return of exactly zero. Those zeros enter the sample like any other observation, so a series rich in carried-forward points reports **less** movement than the instrument actually had. The `carried_forward` status is the warning that a calm-looking figure may be calm for the wrong reason.

!!! warning "No threshold is defined"

    Nothing in the system declares a coverage, an observation count or a carried-forward share beyond which a figure must be discarded. That absence is deliberate — the honest number is the one that comes with its own provenance — but it means the final judgement is yours, and it cannot be delegated to the status label.

---

## 🔗 Related {: #related }

- 📅 **[Observed Annualization](observed-annualization.md)** — the calendar-span form of coverage, and why a sparse series is not necessarily a broken one
- 🔗 **[Correlation](correlation.md)** — reports the observation count behind every single cell
- 📊 **[Volatility](volatility.md)** — the figure most directly flattened by carried-forward prices
