# 🎯 Synthetic Benchmarks

LibreFolio can overlay **synthetic benchmark curves** on any FX chart. Unlike technical
indicators (which are computed *from* market data), synthetic benchmarks are generated
mathematically and serve as **visual reference lines** — "what if the price had followed
this ideal trajectory?"

They are invaluable for:

- Comparing actual returns against a target growth rate.
- Visualising what a disciplined investment plan would look like.
- Adding oscillatory or cyclic references for seasonality analysis.

---

## 📈 Linear Growth { #linear-growth }

### 💡 Financial Meaning

A linear growth benchmark represents **simple interest** — the value increases by a
fixed absolute amount each period. This models the scenario where you **do not reinvest**
earnings (dividends, interest, coupons): cash payouts are received but kept aside, so
only the original principal generates returns.

If instead you **reinvest** those earnings — either manually or automatically through
accumulating instruments (e.g., accumulating ETFs, which reinvest dividends internally
and benefit from [tax deferral](taxation.md#tax-deferral-advantage)) — you should
expect **[compound growth](#compound-growth)**, where returns generate further returns.

In practice, the difference between linear and compound growth widens dramatically
over long horizons. This is why the Linear benchmark appears as a straight line while
the Compound benchmark curves upward exponentially.

!!! abstract "Capital gains & losses"
    When selling an asset above its purchase price, the difference is a **capital gain**;
    below, a **capital loss**. Each jurisdiction has its own rules regarding tax rates,
    holding period thresholds, loss carry-forward duration, and matching methods
    (FIFO, LIFO, specific identification). For a theoretical overview, see
    [Taxation & Tax Efficiency](taxation.md).

### 🔢 Mathematical Formula

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

where:

- $y_0$ is the starting value (first data point of the chart),
- $r$ is the annual growth rate (expressed as a decimal, e.g. 0.07 for 7%),
- $t$ is time in years from the start.

This is equivalent to the **simple interest** formula $A = P(1 + rt)$, where $t$ is
expressed in years using the applicable [Day Count Convention](day-count.md).

### ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Annual Rate | `annualRate` | 5 | Growth rate in percent per year. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

### 🔍 Interpretation

The line is perfectly straight on a linear scale. Any point where the actual price
is *above* the line means the asset has outperformed the target; any point *below*
means underperformance. Because the growth is additive, the line curves downward on a
logarithmic scale — making it easy to visually distinguish from compound growth.

:material-link: [Simple Interest on Wikipedia](https://en.wikipedia.org/wiki/Interest#Simple_interest){ target="_blank" }

---

## 📊 Compound Growth { #compound-growth }

### 💡 Financial Meaning

A compound growth benchmark represents **compound interest** — the value grows
exponentially, meaning returns are reinvested. This is the natural growth model for
most financial assets and the standard assumption in discounted cash flow (DCF)
analysis.

### 🔢 Mathematical Formula

$$
y(t) = y_0 \cdot (1 + r)^t
$$

where:

- $y_0$ is the starting value,
- $r$ is the annual growth rate (decimal),
- $t$ is time in years from the start.

This is equivalent to the **compound interest** formula $A = P(1 + r)^t$ with annual
compounding. The generalised formula with $n$ compounding periods per year is:

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

LibreFolio's backend supports the following compounding frequencies:
**Annual** ($n=1$), **Semiannual** ($n=2$), **Quarterly** ($n=4$),
**Monthly** ($n=12$), **Daily** ($n=365$), and **Continuous** ($n \to \infty$).

When $n \to \infty$ (continuous compounding):

$$
A = P \cdot e^{r \cdot t}
$$

### 🔄 Iterative Computation (Daily Stepping)

In LibreFolio the compound curve is computed **iteratively** rather than calling
`pow()` for each data point. This is both more efficient and instructive:

$$
\text{dailyFactor} = (1 + r)^{1/365}
$$

Then, for each successive day:

$$
y_{i+1} = y_i \cdot \text{dailyFactor}
$$

This is mathematically equivalent to the closed-form $y_0(1+r)^t$ but replaces $N$
expensive power operations with $N$ simple multiplications — the same principle behind
how banks actually accrue daily compound interest.

!!! tip "Rule of 72"
    A quick mental shortcut: an investment growing at $r$% per year will approximately
    double in $72 / r$ years. At 7% → ~10.3 years.

### ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Annual Rate | `annualRate` | 7 | Compound growth rate in percent per year. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

### 🔍 Interpretation

The curve is straight on a **logarithmic** scale — this is the telltale sign of
exponential growth. Overlaying a compound benchmark on a log-scale chart is the
cleanest way to judge whether an asset is growing faster or slower than a target rate.

:material-link: [Compound Interest on Wikipedia](https://en.wikipedia.org/wiki/Compound_interest){ target="_blank" }

---

## 🌊 Sine Wave { #sine-wave }

### 💡 Financial Meaning

A sine wave benchmark represents **periodic oscillation**. It is useful for:

- Modelling **seasonality** (e.g. agricultural commodities, tourism-linked currencies).
- Providing a visual reference for **cyclic patterns** that traders suspect in the data.
- Testing the rendering pipeline with a known analytic waveform.

### 🔢 Mathematical Formula

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{offset}
$$

where:

- $A$ is the amplitude (peak-to-peak range as % of base value),
- $T$ is the period in days,
- $y_0$ is the base value (first data point),
- $\text{offset}$ is a vertical shift.

### ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Amplitude | `amplitude` | 10 | Peak oscillation range as % of base value. |
| Period | `period` | 365 | Full cycle length in days. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

### 🔍 Interpretation

If the actual price roughly tracks the sine reference, the market exhibits a detectable
cyclic component at that frequency. Deviations from the sine suggest non-periodic shocks
or trend drift. Adjusting the period parameter lets you scan across different cycle
lengths — effectively performing a manual version of spectral analysis.

:material-link: [Sine Wave on Wikipedia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }
