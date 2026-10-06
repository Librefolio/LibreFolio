# 📅 Observed Annualization

Annualizing a risk figure requires knowing how many periods a year contains, and that number can be measured from the observed data instead of being assumed in advance. LibreFolio measures it: the factor used to scale a per-period figure to an annual one is **counted from the series that was actually analysed**, never taken from a market convention fixed beforehand.

---

## 🔢 Formula {: #formula }

Two quantities are read off the series before any figure is annualized — the calendar span it covers, and the number of returns observed inside that span:

$$
D = d_{last} - d_{baseline}
$$

$$
f = \frac{N \times 365}{D}
$$

where:

- $N$ = number of period returns actually used
- $d_{baseline}$ = date of the first valuation (it opens the series and therefore produces no return of its own)
- $d_{last}$ = date of the last return
- $D$ = calendar days spanned, weekends and closures included

The factor $f$ is then applied wherever a per-period figure has to be expressed on an annual basis. For volatility:

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

!!! info "It is a count, not a convention"

    $f$ has a literal reading: **observations per year, counted**. A series with $N$ returns spread over $D$ calendar days was observed at a rate of $N/D$ per day, hence $365N/D$ per year. No assumption is made about the instrument, its market calendar or its asset class — the rate is whatever the data turns out to be. The one piece of calendar knowledge involved decides what counts as an observation, never how many there should be: a stored price that only repeats the previous close on a weekend or a market holiday is a carry, not a quote (see [below](#252-is-recovered-not-imposed)).

If the span collapses — a single valuation date, so $D \leq 0$ — no factor exists and no annualized figure is produced. The alternative would be to invent one.

---

## 💡 Interpretation {: #interpretation }

The table below works the formula out for a few shapes of series. It is arithmetic, not the output of a LibreFolio run:

| Series | Returns $N$ | Calendar days $D$ | $f = 365N/D$ | $\sqrt{f}$ |
|---|---|---|---|---|
| Instrument quoted on trading days only, full year | 252 | 365 | 252.0 | 15.87 |
| Instrument trading every day (crypto), full year | 365 | 365 | 365.0 | 19.10 |
| Weekly-priced fund, full year | 52 | 365 | 52.0 | 7.21 |
| Instrument quoted on trading days, started mid-period | 126 | 183 | 251.3 | 15.85 |
| Daily series with gaps | 180 | 365 | 180.0 | 13.42 |

Four readings follow from those rows.

### 📈 √252 Is Recovered, Not Imposed {: #252-is-recovered-not-imposed }

An instrument quoted only while its market is open contributes roughly 252 returns across a full calendar year, so $f = 252 \times 365 / 365 = 252$ and the familiar $\sqrt{252}$ comes out of the measurement. The conventional number is **a result** here, not an input — which is precisely why nothing is lost by refusing to hardcode it.

It comes out even when the price source delivers a row for every calendar day. Some sources repeat the last close on the days the market is closed — justETF, for one, repeats Friday's close on Saturday and Sunday. Counted as quotes, those rows would add a zero return that no market produced for every closed day, and push $f$ towards 365. They are not counted: a stored price dated on a Saturday, a Sunday or a weekday market holiday whose close repeats **exactly** the close of the row before it is a **carry** — the last quote held over, not a new one — and its date adds no observation to the series. A price that moved on a closed day stays a quote, as a crypto-asset's weekend prices do, and so does an unchanged price on an ordinary weekday, such as a flat day of a bond. The instrument keeps its trading days, and $f$ stays near 252. The full rule, with the exchanges whose holidays count, is under [Data Quality](data-quality.md#stored-carries).

!!! info "A portfolio series is read on its holdings' quote days"

    That row describes an instrument's own quoted prices; the return series of a **portfolio** reaches it by another route. The portfolio's [time-weighted return](../performance-metrics/portfolio-engine/twrr.md) is computed one calendar day at a time, weekends and holidays included, carrying the last known price forward where nothing was quoted. The risk analysis reads it only on its **observation days** — the days on which at least one of the positions held at the end of the analysed period had a quote of its own — and chain-links the return of every other day into the next observation day, so the cumulative return is exactly what it was: only the sampling changes. A portfolio of stocks and funds quoted on trading days therefore contributes roughly 252 returns a year, like the first row, although its history has a point for every calendar day; one that holds an instrument quoted every calendar day, such as a crypto-asset, is observed every day, like the second. The factor follows the series the metric is computed on, which is exactly why it is measured rather than assumed.

### 🪙 A 24/7 Instrument Gives ≈ √365 {: #a-247-instrument-gives-365 }

An instrument that trades every calendar day is observed 365 times a year, so $f \approx 365$. A hardcoded $\sqrt{252}$ applied to it would **understate** its annualized volatility by a factor of:

$$
\frac{\sqrt{365}}{\sqrt{252}} \approx 1.20
$$

The error is not a rounding detail: it is systematic, and it always points in the reassuring direction.

### 📐 The Factor Measures a Rate, Not a Length {: #the-factor-measures-a-rate-not-a-length }

Row four is a daily-priced stock observed for roughly half a year: $f$ still lands near 252, because numerator and denominator shrink together. A shorter window does not shrink the factor — it only makes it noisier (see the limitations below).

### 🕳️ Gaps Lower It, Honestly {: #gaps-lower-it-honestly }

Holidays, missing prices, an asset that started mid-period: whatever was observed is what gets counted. A series with gaps is annualized as the sparse series it is, rather than as the dense series it was assumed to be.

---

## 📏 Coverage {: #coverage }

Alongside the factor, a second quantity is published with the result: of the days on which the series could have been observed, the share on which it was.

$$
c = \frac{N}{Q}
$$

where $Q$ is the number of those days. Coverage says how **densely** the series was sampled, as a fraction between 0 and 1. It is not a second annualization factor: $f$ says at what rate the series was observed, $c$ says how many of its possible observations it kept. Which days count in $Q$ depends on how the series is built:

- An **instrument** series — and any series built from the prices of several assets — runs on a joint calendar. Every date in the requested window on which at least one of the assets has a quote of its own is a candidate, and a candidate becomes an observation only if every asset can be valued on it, a price carried forward from an earlier date included. $Q$ counts the candidates, the baseline aside. For an instrument quoted only while its market is open, the candidates are the market's own calendar, so its closed days cost nothing: a carry is not a quote, and adds no candidate.
- A **portfolio** series is its time-weighted return read on its observation days (see [above](#252-is-recovered-not-imposed)), with its first point kept as the baseline. $Q$ counts the observation days after the baseline, up to the last return. The portfolio history has a point for every calendar day, so for a portfolio held without interruption every observation day carries one, and coverage sits at the top of its range by construction. Only if none of the holdings has a quote of its own in the window is every calendar day kept, and $Q$ is then the span $D$.

What coverage does **not** say is whether the prices behind those observations were real. On a joint calendar, a date on which only some of the assets were quoted is still an observation, the others entering with a price carried forward; on a portfolio's observation day, every holding not quoted that day enters at its last known value. So a high coverage is not a certificate and a low one is not a defect: both describe *how many of the possible observations the series kept*, not the quality of what is inside them. That second question — were these prices quoted, or carried forward? — is the job of [Data Quality](data-quality.md).

!!! info "Both figures travel with the result"

    Every risk result carries the inputs of its own annualization in its metadata — the number of observations, the calendar days spanned, the factor and the coverage. A published annual figure can therefore be recomputed by hand from the same inputs that produced it.

---

## ⚠️ Limitations {: #limitations }

!!! warning "A short span makes the factor unstable"

    The denominator is the observed calendar span. Over a few weeks $D$ is small, so one missing or one extra observation moves $f$ appreciably, and $\sqrt{f}$ with it. The annualized figure inherits that instability: it is being extrapolated from a window far shorter than the year it claims to describe.

!!! warning "Measuring the factor does not repair the assumption"

    Scaling by $\sqrt{f}$ follows from variance adding across **independent** periods (see [Volatility](volatility.md)). If returns are autocorrelated — trends, volatility clustering, mean reversion — the scaled figure is biased regardless of how accurately $f$ was counted. Measuring the factor removes a wrong constant; it does not remove the independence hypothesis underneath it.

Two figures annualized with different factors are also only comparable if the sampling behind them is comparable. A weekly-priced fund and a 24/7 instrument are both annualized correctly, and are still being observed in very different ways — which is what the observation count and the coverage are there to make visible.

---

## 🔗 Related {: #related }

- 📊 **[Volatility](volatility.md)** — the figure most often expressed on an annual basis
- 🧪 **[Data Quality](data-quality.md)** — what a low coverage means for the trustworthiness of a result
- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — a risk-adjusted ratio that also carries an annual scale
- 📊 **[Sortino Ratio](sortino-ratio.md)** — the downside-only variant, same scaling question
