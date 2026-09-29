# 🧪 Data Quality

A risk figure is only as trustworthy as the observations behind it, so the amount and freshness of the underlying data belong to the reading of the result. LibreFolio does not keep that layer hidden: every risk result travels with a source-data report, a status derived from it, and — when something was missing — the list of what was missing.

---

## 🚦 Source-Data Status {: #source-data-status }

Source data is classified on three levels:

| Status | What it means |
|---|---|
| `ok` | Nothing missing, and nothing held over for longer than the [staleness threshold](#staleness-threshold). The series is what it claims to be. |
| `carried_forward` | Nothing is missing outright, but some prices or exchange rates were held over from an earlier date for longer than the staleness threshold — stale quotes, carried-forward price points, carried-forward FX points. |
| `partial` | Something is missing outright: prices, FX pairs, dates inside the analysed window on which not every holding could be valued, unresolved currency pairs, or assets that could not participate at all. |

Two properties of this ladder matter more than the labels.

**It is derived, not declared.** The status is a computed property of the report's own contents: a producer cannot claim `ok` while reporting missing prices, because the status is recomputed from what the report holds. Anything missing outright yields `partial`; if nothing is missing but something was held over past the staleness threshold, `carried_forward`; otherwise `ok`. `partial` takes precedence over `carried_forward`.

**It is categorical, not numeric.** The status answers *what kind of imperfection is present*, never *how much is tolerable*. There is no level of completeness below which the system declares a figure untrustworthy — that judgement is left to the reader, deliberately and explicitly.

### ⏳ The Staleness Threshold {: #staleness-threshold }

A price or an exchange rate held over from an earlier date is ordinary in itself: weekends, holidays and instruments quoted on their own market calendars leave gaps all the time. A held-over value becomes **stale** only once it is more than **seven calendar days** older than the date it stands in for, and only a stale one counts against the per-asset series of an analysis: it is recorded as a carried-forward price or FX point, and a single one is enough for `carried_forward`. A younger one degrades nothing, but it is not invisible: a held-over price still gives a period return of zero, and that return enters the sample (see [Limitations](#limitations)). The threshold decides what counts as an imperfection, not how many imperfections are tolerable.

Seven calendar days is the project's single staleness threshold, not a convention of this page: the [correlation laboratory](../../../user/assets/correlation.md) of the Assets page and the historical replay judge the age of a price by the same seven days, and the warnings that report stale prices or exchange rates quote it.

---

## 📋 What the Report Records {: #what-the-report-records }

The report is an inventory, not a score:

| Signal | What it captures |
|---|---|
| Missing price assets | Holdings for which no usable price could be obtained |
| Missing / unresolved FX pairs | Currency conversions that could not be resolved |
| Stale prices | Holdings whose latest price is older than the [staleness threshold](#staleness-threshold) |
| Carried-forward price points | How many price points were held over past the staleness threshold, and for which assets |
| Carried-forward FX points | How many conversion points were held over past the staleness threshold, and for which pairs |
| Incomplete dates | Dates on which valuation, NAV, book value or allocation could not be completed for every holding |
| Unusable assets | Assets excluded before any metric was attempted, each with a reason |
| Warnings | Free-form notes attached by the producing stage |

Each entry names the object it concerns — the asset, the currency pair, the date. A reader can ask *which* asset, currency pair or date degraded the figure, not merely *whether* something did.

---

## 🧮 Alignment: What Missing Data Actually Costs {: #alignment-what-missing-data-actually-costs }

When an analysis spans several holdings — a correlation matrix, a risk-contribution breakdown — it is computed on a **single shared calendar**, and building that calendar is where missing data turns into a visible cost.

1. A date is a candidate if at least one holding had a fresh quote on it: the candidates are the union of the holdings' quote calendars over the requested window.
2. A candidate date enters the analysis only if **every** holding could be valued on it. Here *valued* includes a price or an exchange rate carried forward from an earlier date, with no age limit, so in practice the test fails only before a holding's first usable price, or where its conversion into the target currency could not be resolved. Dates that fail this test are dropped for all holdings, but they are recorded as incomplete valuation dates only once the calendar has started — that is, after the baseline.
3. The baseline is the last date before the requested start on which all holdings were valuable; if there is none, the analysis starts inside the requested window instead, on the first date on which every holding can be valued, and the holdings responsible for the late start are named.

The consequence is worth stating plainly: **one holding that starts late shortens the window for everyone**. A gap inside a history shortens nothing, because the missing price or exchange rate is held over. Nothing is interpolated: a held-over price or rate is the last one known. Once it has been held over past the [staleness threshold](#staleness-threshold) it is counted as a carried-forward point — a matter for the `carried_forward` status, not for the length of the window. A younger one does not degrade the status, although a held-over price, whatever its age, still counts against the freshness measure described under [Coverage](#coverage). A holding is never partially included in a joint computation — either the date works for all of them or it is not an observation. A late start alone does not make the result `partial`: the dates it costs are not listed as incomplete, the report names the holdings responsible in its `short_history` entries, and the loss shows in the observation count and in the shared calendar's coverage below. A date lost after the calendar has started is different: it is listed as incomplete, and it makes the result `partial`.

---

## 📏 Coverage {: #coverage }

Coverage is normally the density companion of the status: it answers *how much of what could have been observed actually was*. Several different ratios go by that name. They share no denominator, and they do not all measure the same kind of thing: two of them count observations, a third counts holdings and contains no observation at all.

**How much did the shared calendar cost?** Of the dates on which at least one holding had a fresh quote, this is the share that survived the requirement that every holding be valuable. A figure well below 1 means that on many of the dates on which some holding was quoted, another could not be valued — and since gaps are carried forward, that usually points to a holding whose history begins well after the requested start, or to conversions that could not be resolved, rather than to gaps.

**How much of the data is genuinely fresh?** Across the grid of holdings × observations, this is the share of points whose price was quoted on that date rather than held over from an earlier one. It measures the same kind of imperfection as the `carried_forward` status, but over the observations only and with a stricter bar: every held-over price counts against it, however young, where the status counts only those held over past the staleness threshold. It also counts prices only: a quote that is fresh but had to be converted with a carried-forward exchange rate still counts as fresh, because carried-forward conversions are tracked as their own separate signal. So a share below 100% does not by itself mean `carried_forward`, and a share of 100% does not by itself rule it out — nor, therefore, a `partial` result.

**How much of the portfolio could be classified?** Of the holdings in scope, this is the share whose sector or geography metadata was available, rather than missing and sending the holding to the catch-all `Other` bucket at 100%. This one is a statement about metadata: no price, no date and no observation enters it. A [hypothetical shock](hypothetical-shock.md) reports this ratio.

!!! warning "One shared name, two kinds of quantity"

    When the figure is a density measure, its denominator depends on the path: for an analysis built from instrument quotes it is the candidate quote dates, while for a portfolio series it is the calendar days actually spanned. On a portfolio series that figure is high by construction — the engine emits a point for every calendar day whether or not anything was quoted, carrying the last known value forward when nothing was — so it certifies nothing about the prices behind it. On an instrument grid a lower figure points to dates the shared calendar actually lost — a late start, or a conversion that could not be resolved — never to a closed market: a date on which nothing was quoted is not a candidate, and on a date on which only some holdings were quoted the others are carried forward and still valued, so the closure shows in the freshness measure instead.

    The question *were these prices quoted, or carried forward?* does have an answer in the system, but it is the freshness measure above, not the one a result carries under the name *coverage*. Which measure reaches any given screen is outside what this page describes.

    One discriminator settles it without any knowledge of the internals. **When a result reports `n_observations = 0` and `calendar_days = 0` next to a non-zero coverage, that coverage is not a statement about data density.** It cannot be: nothing was observed. It is reporting how much of the portfolio was classified.

    The distinction changes what should be done about the number. A coverage of 80%, read with the first two meanings in mind, says *a fifth of the prices are missing*. On a classification ratio it says a fifth of the sector or geography labels are missing. One is a gap in market data, the other a gap in asset metadata, and the two call for completely different actions. See [Observed Annualization](observed-annualization.md) for how the span and the observation count also produce the annualization factor.

---

## 🚫 Exclusions {: #exclusions }

An asset can leave the analysis at two different moments, and the distinction is recorded.

**Before any metric is attempted**, when its source data cannot support one: no usable price, no usable currency conversion, an invalid currency. These are reported as unusable assets, each carrying its reason.

**When the scope is resolved**, if the asset has no usable prepared return series at all. The requested scope is then reduced to the assets that survive, each exclusion keeps its reason, and a warning for each reason names exactly which assets were dropped.

In neither case does the analysis refuse to run: it runs on what remains and says so. An excluded asset is a change in *what was measured*, which is why it forces out of the clean state every result whose measurement it changed — and only those.

### 🎯 Which Results Carry an Exclusion {: #which-results-carry-an-exclusion }

An exclusion is a hole in the per-asset series of the scope: the return series of each holding, aligned on the [shared calendar](#alignment-what-missing-data-actually-costs). Every result built from those series inherits it — the asset is listed as excluded, the warning naming it travels with the result, and the result is `partial`. That covers correlation, risk contribution, risk/return and the simulation; the KPIs, the Value at Risk and the comparison replayed on the current composition, which is today's weights run over those series; the analyses of a set of assets picked directly; and the analyses of a *slice* of a portfolio, a selection of its holdings. A slice cannot be cut out of the portfolio's own history, so even in the historical mode it is replayed from the series of the holdings selected.

The exception is the historical mode of a portfolio as a whole — all of its brokers or a selection of them, but not a slice of its holdings. There, four analytics read the portfolio's own return history, its [time-weighted return](../performance-metrics/portfolio-engine/twrr.md) (TWRR), instead of the per-asset series: the KPIs (volatility, Sharpe, Sortino, …), the historical [Value at Risk](value-at-risk.md) and [Conditional Value at Risk](conditional-value-at-risk.md), the drawdown, and the comparison against a benchmark, which adds only the benchmark's own series. That history already values every holding — one without market quotes at the price of its last transaction — so an asset missing from the per-asset series costs these four nothing. They inherit neither the exclusion nor the warning that names it, nor the warning that the part of today's composition counted at zero return includes value in transit, a statement about a composition they never use. The same request still reports the exclusion on every result that reads the per-asset series. What can still make these four `partial` is the data behind the portfolio history itself, and for the comparison the preparation of its benchmark — see [Interpretation](#interpretation).

The stress tests apply rules of their own. A [historical replay](historical-replay.md) prepares its own series over the window of its episode, and leaves out — for reasons of its own, named in its own warnings — the assets it cannot price at both ends of that window. A [hypothetical shock](hypothetical-shock.md) reads no return series at all: it applies its shocks to every holding through the holding's classification, so an exclusion from the per-asset series costs it nothing, and it inherits neither the exclusion nor its warning.

### 🏷️ Exclusion Reasons {: #exclusion-reasons }

Every excluded asset carries one reason, and each reason has a sentence of its own in the warning:

| Reason | Why the asset was left out |
|---|---|
| `no_price_source` | No price source is assigned to it and no price has ever been recorded for it. Nothing is set up to price it, so this is a permanent state rather than a gap in the data — typically a private investment, such as a crowdfunding loan, that no market quotes. |
| `missing_price` | It has a price source, or prices on record, but no usable price for the period: the source returned nothing for it, or every recorded price falls after the period. |
| `missing_fx` | Its prices could not be converted into the target currency. |
| `invalid_currency` | Its prices carry no valid currency. |
| `insufficient_history` | There is not enough history in the period to give it a usable return series. |

Prices recorded only *before* the period never cause an exclusion: the last of them is carried into the period, as described under [Alignment](#alignment-what-missing-data-actually-costs). Only the result tells the first two reasons apart: in its source-data report, an asset that nothing prices is still listed among the unusable assets as `missing_price`.

### ⚖️ The Excluded Weight {: #excluded-weight }

The analyses of the current composition that state weights — risk contribution and risk/return — keep an excluded holding at its weight and count it at zero return: the figures they compute are exactly those the same money held in cash would give. The result names that part separately. `excluded_weight` is the sum of the weights of the scope's holdings left without a series, and it is stated next to `cash_weight`, the zero-return residual: the share of the scope's value held outside the holdings that have a series — cash, any value in transit and the excluded holdings. In every result these two analyses produce, the excluded weight is part of that residual. The two could fail to nest only if the holdings were worth more than the net worth — a negative cash balance not offset by value in transit — and in that case neither analysis produces a result: it comes back `unavailable`. Selections without weights, such as a set of assets picked directly, carry neither.

---

## 💡 Interpretation {: #interpretation }

Every analytic result carries a status of its own, distinct from the source-data one:

| Result status | Meaning |
|---|---|
| `ok` | Computed with nothing missing or stale in its source data, nothing excluded from what it reads and no degrading warning |
| `partial` | Computed, but with source data missing or stale, something excluded from what it reads, or a degrading warning |
| `unavailable` | Not computed; a stable reason code explains why (insufficient history, data unavailable, undefined metric, incompatible scope or mode, …) |
| `failed` | The computation itself did not complete |

A result is `partial` when **any** of these holds: a warning that degrades the result is present; an asset of the scope that the result reads was [excluded](#which-results-carry-an-exclusion); the analytic itself excluded something; or the status of the source-data report the result is judged on is anything other than `ok`. In the last case an explicit warning is attached as well, so the degradation is never inferred from the status alone.

That report is the one of the series the result consumed:

- a result built from the per-asset series of the scope — including the KPIs, the Value at Risk figures, the drawdown and the comparison when they are replayed from those series, on the current composition or on a slice — is judged on the report of their preparation, merged, when the scope is a portfolio, with the portfolio's own report;
- on a portfolio's TWRR, the KPIs, the Value at Risk figures and the drawdown are judged on the portfolio's own source-data report: if the portfolio history itself is incomplete — a holding that could not be valued, a missing exchange rate, a day on which the net worth could not be valued in full — they are still `partial`, with the warning. That report tracks what could not be valued, not how old a valuation is, so a price held over past the staleness threshold inside the portfolio history does not degrade them;
- the comparison against a benchmark on the TWRR is judged on the portfolio's report plus the preparation of its benchmark, which is aligned on the shared calendar of the scope: a price or an exchange rate on that calendar held over past the [staleness threshold](#staleness-threshold) — the benchmark's or a holding's — or a date lost from it, still makes it `partial`; the holdings excluded from the scope never entered that calendar, so their exclusion does not.

!!! info "How to read a partial result"

    `partial` does not mean *wrong*. It means the figure carries a known imperfection: it may rest on prices or exchange rates held over past the staleness threshold — same window, same holdings — or answer a slightly different question than the one asked, over a calendar with incomplete dates or over fewer holdings. The figure and the reason travel together in the same payload, and they are meant to be read together: a risk contribution computed with two holdings excluded describes a portfolio in which those two stood still, like cash — not the portfolio as it is.

Analytics also refuse to answer rather than answer badly. Each one declares the minimum number of observations it needs, and below that floor it is not computed at all: the result comes back `unavailable` with an `insufficient_history` reason carrying both the observations available and the number required. Risk contribution and comparison against a benchmark, for instance, both need at least 20. [Correlation](correlation.md#how-each-cell-is-computed) is an exception: it is never refused for short history. Its floor — an adjustable parameter of the analysis, 20 observations by default — applies to the matrix as a whole: every series shares one calendar, so every pair has the same number of observations, and below the floor every cell comes back `insufficient` with no coefficient, in a result marked `partial` rather than `unavailable`.

---

## ⚠️ Limitations {: #limitations }

!!! warning "A status describes the inputs, not the model"

    `ok` says the series was complete, not that the metric is appropriate, that the window is long enough, or that the past resembles the future. Every caveat on the metric pages still applies to a figure built on impeccable data.

!!! warning "Carried-forward data flatters a risk figure"

    A price held over from an earlier date produces a period return of exactly zero in the instrument's own currency; after conversion into the target currency, only the exchange rate moves it. Every held-over price does this, however young, and those returns enter the sample like any other observation. Within the [staleness threshold](#staleness-threshold) that is ordinary: over a weekend, a holiday or a day on which only another market traded, the instrument had no new quote, and its next quote catches up. A price held over for longer stands in for days on which the instrument may well have moved, so a series rich in such points reports **less** movement than the instrument actually had. Those are the points the `carried_forward` status counts, and the status is the warning that a calm-looking figure may be calm for the wrong reason.

!!! warning "A holding valued from its trades stands still"

    On a portfolio's TWRR, a holding that no market prices is valued at [the price of its last transaction](../performance-metrics/portfolio-engine/price-resolution.md), so in its own currency it stands still from one transaction to the next. For a loan held at its nominal value — a typical crowdfunding investment — that is the truth. For a holding whose value really moves, it flattens every figure read on the TWRR, just as a held-over price does. No status flags it: the portfolio's report does not count a valuation from trades against its status, and for a holding with no price source it treats that valuation as the intended, permanent state.

!!! warning "No quality threshold discards a figure"

    Apart from the minimum observation counts described above, below which an analytic is not computed at all or every correlation cell comes back `insufficient`, nothing in the system declares a coverage or a carried-forward share beyond which a figure must be discarded. That absence is deliberate — the honest number is the one that comes with its own provenance — but it means the final judgement is yours, and it cannot be delegated to the status label.

---

## 🔗 Related {: #related }

- 📅 **[Observed Annualization](observed-annualization.md)** — the calendar-span form of coverage, and why a sparse series is not necessarily a broken one
- 🔗 **[Correlation](correlation.md)** — reports the observation count behind every single cell
- 📊 **[Volatility](volatility.md)** — the figure most directly flattened by carried-forward prices
