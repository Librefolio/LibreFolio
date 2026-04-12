# 📐 Sharpe Ratio

The Sharpe ratio is the most widely used **risk-adjusted return** metric. It measures how much excess return you receive per unit of total volatility.

---

## 🔢 Formula

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

where:

- $R_p$ = portfolio return (annualized)
- $R_f$ = risk-free rate (e.g., Treasury bill rate)
- $\sigma_p$ = portfolio standard deviation (annualized)

---

## 💡 Interpretation

| Sharpe Ratio | Quality |
|---|---|
| $< 0$ | Portfolio underperformed the risk-free rate |
| $0 - 0.5$ | Suboptimal risk-adjusted return |
| $0.5 - 1.0$ | Acceptable |
| $1.0 - 2.0$ | Good |
| $> 2.0$ | Excellent (rare for long periods) |

!!! example "Numerical example"

    Portfolio return: 12%, Risk-free rate: 3%, Volatility: 15%

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    For every 1% of volatility, the portfolio earned 0.60% of excess return.

---

## ⚙️ Annualization

When computed from daily returns:

$$
S_{annual} = S_{daily} \times \sqrt{252}
$$

where 252 is the typical number of trading days per year. This assumes returns are IID (independent and identically distributed) — an approximation that breaks down for autocorrelated returns.

---

## ⚠️ Limitations

### 📊 Symmetric Penalty

The Sharpe ratio penalizes **upside volatility** as much as downside volatility. An asset that frequently spikes upward (highly desirable!) will have a lower Sharpe ratio than one with the same return and less upside movement.

→ For asymmetric return distributions, prefer the **[Sortino Ratio](sortino-ratio.md)**.

### 📈 Sensitivity to Outliers

A few extreme returns can significantly distort the standard deviation, making the Sharpe ratio unstable for short time periods.

### 🔄 Time-Period Dependency

The Sharpe ratio can vary dramatically depending on the lookback window. A strategy with an excellent 5-year Sharpe may have a poor 1-year Sharpe (or vice versa).

---

## 🔗 Related

- 📊 **[Sortino Ratio](sortino-ratio.md)** — Downside-only variant
- 📊 **[Volatility](volatility.md)** — The denominator of the Sharpe ratio
- 📈 **[Returns](../../fundamentals/returns.md)** — The numerator of the Sharpe ratio


