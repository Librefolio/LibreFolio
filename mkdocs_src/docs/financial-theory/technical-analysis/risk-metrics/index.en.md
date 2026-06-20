# 📊 Risk Metrics

Risk metrics provide **quantitative measures** of portfolio risk. Each metric captures a different aspect of uncertainty, and no single metric tells the whole story. Using multiple metrics together gives a comprehensive view of portfolio risk.

---

## 📋 Comparative Overview

| Metric | What It Measures | Formula | Range | Details |
|--------|-----------------|---------|-------|---------|
| **[Sharpe Ratio](sharpe-ratio.md)** | Risk-adjusted return (total vol) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Sortino Ratio](sortino-ratio.md)** | Risk-adjusted return (downside only) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Max Drawdown](max-drawdown.md)** | Worst peak-to-trough decline | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatility](volatility.md)** | Dispersion of returns | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 When to Use Each Metric

| Scenario | Best Metric | Why |
|----------|-------------|-----|
| Comparing two funds | **Sharpe Ratio** | Normalizes return by total risk |
| Asymmetric return distributions | **Sortino Ratio** | Only penalizes downside volatility |
| Worst-case scenario planning | **Max Drawdown** | Shows the maximum pain point |
| General risk assessment | **Volatility** | Foundation for all other metrics |
| Portfolio optimization | **All four** | Each captures a different dimension |

---

## ⚠️ Common Pitfalls

!!! warning "Limitations"

    - **Historical metrics ≠ future risk**: Past volatility may not predict future volatility
    - **Normal distribution assumption**: Sharpe and Sortino assume returns are roughly normal; financial returns have fat tails
    - **Lookback sensitivity**: Metrics change significantly depending on the time window
    - **Benchmark dependency**: Sharpe and Sortino depend on the risk-free rate, which changes over time

---

## 🔗 Related

- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — How risk reduction works mathematically
- ⚖️ **[Asset Allocation](../../portfolio-theory/asset-allocation.md)** — Using risk metrics to guide allocation
- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — The "return" side of risk-return


