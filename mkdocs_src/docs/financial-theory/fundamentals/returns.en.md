# 📈 Returns & Growth Rates

This page covers the mathematical foundations of **investment returns** — how to measure, compare, and annualize growth rates. These concepts are used throughout LibreFolio's measurement tools and portfolio analytics.

---

## 📊 Simple (Discrete) Return

The **simple return** over a period is the percentage change:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    If EUR/USD moves from 1.10 to 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Properties

- **Intuitive**: directly represents "how much you gained/lost"
- **Not additive**: you cannot simply sum simple returns across periods to get total return
- **Compounding**: multi-period returns must be **multiplied**, not added

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Logarithmic (Continuous) Return

The **log return** is the natural logarithm of the price ratio:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Properties

- **Additive across time**: total log return = sum of sub-period log returns

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Symmetric**: a +5% move followed by a −5% move returns exactly to the starting point
- **Approximately equal** to simple return for small values: $r_{log} \approx R_{simple}$ when $R_{simple}$ is small

### 🔄 Conversion

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Annualized Return

To compare returns across different time periods, we **annualize** them — projecting the observed growth rate to a full year.

### 📈 Compound Annual Growth Rate (CAGR)

The most common annualization method. Given a total return over $d$ calendar days:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

This is what LibreFolio's [Measures tool](../../user/fx/detail/measures.md) displays.

!!! example

    EUR/USD moves from 1.10 to 1.14 over 90 days:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Annualized Log Return

For log returns, annualization is simply scaling:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

This linearity is one of the key advantages of log returns in quantitative finance.

---

## 🔄 Relationship Between Simple and Log Returns

| Property | Simple Return $R$ | Log Return $r$ |
|----------|:---:|:---:|
| **Compounding** | Multiplicative: $(1+R_1)(1+R_2)$ | Additive: $r_1 + r_2$ |
| **Symmetry** | Asymmetric: +10% then −10% ≠ 0 | Symmetric: +10% then −10% = 0 |
| **Annualization** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Portfolio returns** | Weighted sum works ✅ | Weighted sum doesn't work ❌ |
| **Time series** | Not additive ❌ | Additive ✅ |
| **Interpretation** | "I gained 5%" | "Log growth rate was 0.0488" |

!!! tip "When to use which?"

    - **Simple returns** for reporting to users and computing portfolio-level returns
    - **Log returns** for statistical analysis, volatility estimation, and time-series models

---

## 🔁 Rolling Return {: #rolling-return }

A **rolling return** is the simple return of the sections above, measured over a window that slides along the series: one value per date, each looking back over the same span. Two features of an asset's page compute it, and they differ in how the span is counted — in sessions, or in calendar days. The 📖 guide button on the card of the **Rolling Return** signal opens this page.

### 📊 Over a Window of Sessions {: #rolling-return-sessions }

The **Rolling Return** signal of the Signals panel, in the risk family, reads the asset's prepared return series, in the chart's currency: one simple return per **session**, a day on which the asset has a quote of its own. A price stored on a weekend or a market holiday that only repeats the close before it is not a session. With $V_t$ the value at session $t$ and $r_t = V_t / V_{t-1} - 1$, the rolling return over a window of $w$ sessions is

$$
R_t^{(w)} = \prod_{k=0}^{w-1} \left(1 + r_{t-k}\right) - 1 = \frac{V_t}{V_{t-w}} - 1
$$

computed through logarithms, $R_t^{(w)} = \exp\left(\sum_{k=0}^{w-1} \ln(1 + r_{t-k})\right) - 1$, so that the window can slide one step at a time. The window $w$ — 30 by default, from 1 to 500 — counts return observations, not calendar days: 30 sessions of an instrument quoted on weekdays span about six weeks, 30 sessions of one quoted every day span 30 days. The first value appears once $w + 1$ valuations are available.

### 🗓️ Over a Window of Calendar Days {: #rolling-return-calendar }

The chart's **Rolling Return** mode measures each date against the close exactly $N$ calendar days earlier. With $\hat{P}(d)$ the resolved close of calendar day $d$ — the last close available on or before $d$, converted into the chart's currency, so that a weekend or a holiday reads the session before it — the return on day $d$ is

$$
R^{[N]}(d) = \frac{\hat{P}(d)}{\hat{P}(d - N)} - 1
$$

The presets **1W**, **1M**, **3M** and **1Y** set $N$ to 7, 30, 90 and 365 days; a custom window counts 7 days a week, 30 a month and 365 a year. A point is left empty, never estimated, when either end has no resolved close or a close that is not positive; when no point of the range can be computed, the result is unavailable. Each point reports the reference date it asked for and the dates of the price and exchange rate actually used — see the [Interactive Chart](../../user/assets/detail/chart.md#rolling-return).

### ⚖️ Sessions or Calendar Days {: #sessions-or-calendar-days }

Both measures are price-only simple returns: neither adds dividends, coupons or cash flows, and neither is annualised. They answer slightly different questions:

| | Window of sessions | Window of calendar days |
|---|---|---|
| Span | $w$ quotes, whatever time they cover | exactly $N$ days, whatever the quoting rhythm |
| Defined on | the asset's sessions | every date of the chart |
| Comparing two assets | equal $w$ can mean different spans | equal $N$ always means the same span |
| A closed day at either end | cannot occur: only sessions are used | resolved to the last close before it |

To compare a rolling return with one over a different span, annualise it with the CAGR formula above, $d$ being the span in calendar days — bearing in mind the pitfall on very short periods below.

---

## 📏 Day Count Conventions

The number of days $d$ can be computed differently depending on the convention:

- **Actual/365**: Calendar days (what LibreFolio uses)
- **Actual/360**: Calendar days over a 360-day year (common in money markets)
- **30/360**: Assumes 30-day months and 360-day year

For more details, see [Day Count Conventions](day-count.md).

---

## 💰 Portfolio Return Methods

When a portfolio has **cash flows** (deposits, withdrawals), a single return formula is not enough, because capital injections or withdrawals would dilute or artificially inflate the percentage return.

To solve this, advanced performance metrics are used:
- **TWRR (Time-Weighted Rate of Return):** Isolates the performance of the assets, ignoring the investor's cash flow timing.
- **MWRR (Money-Weighted Rate of Return):** Measures the investor's personal performance, taking cash flow timing into account.

For a deep dive into how these metrics work, why they differ, and how LibreFolio uses them, see the dedicated [Performance Metrics](../technical-analysis/performance-metrics/index.md) chapter.

---

## ⚠️ Pitfalls

1. **Very short periods**: Annualizing a 3-day return can produce misleading figures (e.g., a 0.1% 3-day move → 12.5% annualized)
2. **Negative prices**: Log returns are undefined for negative values — not an issue for FX rates
3. **Compounding frequency**: CAGR assumes continuous compounding; real-world instruments may compound daily, monthly, or quarterly


