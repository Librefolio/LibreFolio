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

    $f$ has a literal reading: **observations per year, counted**. A series with $N$ returns spread over $D$ calendar days was observed at a rate of $N/D$ per day, hence $365N/D$ per year. No assumption is made about the instrument, its market calendar or its asset class — the rate is whatever the data turns out to be.

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

!!! warning "A portfolio series is not a trading-day series"

    That row describes an instrument's own quoted prices. A **portfolio** return series is built differently: the engine walks the requested period one calendar day at a time and emits a point for every day, weekends and holidays included, carrying the last known price forward where nothing was quoted. A portfolio held without interruption therefore contributes roughly one return per calendar day — landing near the second row, not the first — even when every position inside it is a stock quoted on trading days only. The factor follows the series the metric is computed on, which is exactly why it is measured rather than assumed.

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

Alongside the factor, a second quantity is derived from the same two inputs:

$$
c = \min\left(1, \frac{N}{D}\right)
$$

Coverage says how **densely** the span was sampled, as a fraction between 0 and 1 — the ratio is capped, so a series observed more than once per calendar day still reads as fully covered. It is not a second annualization factor: $f$ says at what rate the series was observed, $c$ says how much of the calendar those observations account for.

What coverage does **not** say is whether the prices behind those observations were real, and the two kinds of series behave very differently on that point:

- A **portfolio** series is built on a calendar grid — one point per calendar day — so for a portfolio held without interruption $N$ and $D$ move together and coverage sits at the top of its range by construction. A day on which nothing was quoted still produces a point, carrying the last known value forward, and therefore a return near zero.
- An **instrument** series is built only from the dates that carry a genuinely fresh quote, intersected across the assets in scope. For an instrument quoted only while its market is open, that grid is the market's own calendar, and its density is naturally lower than the calendar span it covers.

So a high coverage is not a certificate and a low one is not a defect: both describe *how much of the span carries an observation*, not the quality of what is inside it. That second question — were these prices quoted, or carried forward? — is the job of [Data Quality](data-quality.md).

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
