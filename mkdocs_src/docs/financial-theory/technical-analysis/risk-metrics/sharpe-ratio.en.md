# 📐 Sharpe Ratio

The Sharpe ratio is the most widely used **risk-adjusted return** metric. It measures how much excess return you receive per unit of total volatility.

---

## 🔢 Formula {: #formula }

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

where:

- $R_p$ = portfolio return (annualized)
- $R_f$ = risk-free rate (e.g., Treasury bill rate)
- $\sigma_p$ = portfolio standard deviation (annualized)

!!! info "How the rate enters the calculation"

    The risk-free rate is supplied as an **effective annual** rate and converted to an **effective daily** rate before use:

    $$
    r_{daily} = (1 + r_{annual})^{1/365} - 1
    $$

    That daily rate is subtracted from each daily return, and the resulting excess returns are what the ratio is built on. The conversion is compounding-aware: a plain $r_{annual}/365$ would treat the rate as if it did not compound over the year.

---

## 💡 Interpretation {: #interpretation }

| Sharpe Ratio | What the value means |
|---|---|
| $< 0$ | The portfolio returned less than the risk-free rate over the window: the excess return in the numerator is negative, so no level of volatility can turn the ratio positive |
| $0 - 0.5$ | Less than half a unit of excess return per unit of volatility: the portfolio moved a great deal relative to what that movement earned |
| $0.5 - 1.0$ | Between half a unit and one unit of excess return per unit of volatility |
| $1.0 - 2.0$ | One to two units of excess return per unit of volatility: the excess return was larger than the volatility that produced it |
| $> 2.0$ | More than two units of excess return per unit of volatility — uncommon over long periods, much less so over short and favourable ones |

!!! warning "The same number is not the same statement"

    A ratio means nothing detached from the window and the asset class it was measured on. A short, favourable stretch produces values that a full market cycle would not sustain, and asset classes with different return rhythms occupy different parts of the scale by construction. Two ratios are comparable only when they cover the same period and were annualised on the same observed factor — see [Observed Annualization](observed-annualization.md). The table says what the number *is*, not whether the result was good: that judgement needs the objective the portfolio was built for.

!!! example "Numerical example"

    Portfolio return: 12%, Risk-free rate: 3%, Volatility: 15%

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    For every 1% of volatility, the portfolio earned 0.60% of excess return.

---

## ⚙️ Annualization {: #annualization }

A Sharpe ratio computed on per-period returns is scaled to an annual figure by the square root of the number of periods a year contains:

$$
S_{annual} = S_{period} \times \sqrt{f}
$$

The factor $f$ is **measured from the observed data** — the number of returns actually used, rescaled to a full calendar year over the span they cover:

$$
f = \frac{N \times 365}{D}
$$

where $N$ is the number of period returns and $D$ the calendar days they span. The square root comes from variance adding across independent periods, so the scaling assumes returns are IID (independent and identically distributed) — an approximation that breaks down for autocorrelated returns.

!!! info "√252 is a result, not a constant"

    A daily-priced stock contributes roughly 252 returns over a full calendar year, so $f \approx 252$ and the familiar $\sqrt{252}$ is recovered as the outcome of the measurement rather than written into it. An instrument priced every calendar day gives $f \approx 365$ instead, and a weekly-priced fund $f \approx 52$.

    → See **[Observed Annualization](observed-annualization.md)** for the derivation and worked examples.

---

## ⚠️ Limitations {: #limitations }

### 📊 Symmetric Penalty {: #symmetric-penalty }

The Sharpe ratio penalizes **upside volatility** as much as downside volatility. An asset that frequently spikes upward (highly desirable!) will have a lower Sharpe ratio than one with the same return and less upside movement.

→ For asymmetric return distributions, prefer the **[Sortino Ratio](sortino-ratio.md)**.

### 📈 Sensitivity to Outliers {: #sensitivity-to-outliers }

A few extreme returns can significantly distort the standard deviation, making the Sharpe ratio unstable for short time periods.

### 🔄 Time-Period Dependency {: #time-period-dependency }

The Sharpe ratio can vary dramatically depending on the lookback window. A strategy with an excellent 5-year Sharpe may have a poor 1-year Sharpe (or vice versa).

---

## 🔗 Related {: #related }

- 📊 **[Sortino Ratio](sortino-ratio.md)** — Downside-only variant
- 📊 **[Volatility](volatility.md)** — The denominator of the Sharpe ratio
- 📈 **[Returns](../../fundamentals/returns.md)** — The numerator of the Sharpe ratio


