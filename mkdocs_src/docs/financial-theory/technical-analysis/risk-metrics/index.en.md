# 📊 Risk Metrics

Risk metrics provide **quantitative measures** of portfolio risk. Each metric captures a different aspect of uncertainty, and no single metric tells the whole story. Using multiple metrics together gives a comprehensive view of portfolio risk.

---

## 🧭 The Four Questions {: #the-four-questions }

Every page in this section exists to answer one of four questions. A metric earns its place by answering one of them; two cross-cutting pages explain how the answers are computed and how far they can be trusted. The two tables further down compare the four best-known of these metrics side by side and suggest when to reach for each.

### 📉 How Much Can It Hurt? {: #how-much-can-it-hurt }

| Metric | What it answers |
|--------|-----------------|
| **[Max Drawdown](max-drawdown.md)** | The largest peak-to-trough decline before a new peak — the worst loss an investor would actually have lived through. |
| **[Current Drawdown](current-drawdown.md)** | How far below its own historical peak a portfolio stands right now, as opposed to the worst fall it ever suffered. |
| **[Drawdown at Risk](drawdown-at-risk.md)** | Drawdown at Risk applies the quantile idea to drawdowns rather than to returns: it is the drawdown depth that should not be exceeded at a chosen confidence level. |
| **[Conditional Drawdown at Risk](conditional-drawdown-at-risk.md)** | Conditional Drawdown at Risk averages the drawdowns that did breach the Drawdown at Risk threshold, answering how deep the fall goes once it goes past that point. |
| **[Ulcer Index](ulcer-index.md)** | The Ulcer Index combines how deep a portfolio falls with how long it stays down, so a shallow decline that persists can score worse than a sharp one that recovers quickly. |
| **[Value at Risk](value-at-risk.md)** | A deliberately narrow question: over a given horizon and at a chosen confidence level, what is the loss that should not be exceeded? |
| **[Conditional Value at Risk](conditional-value-at-risk.md)** | Takes over exactly where Value at Risk stops: the average loss in the cases where the Value at Risk threshold was in fact breached. |
| **[Worst Realization](worst-realization.md)** | The least favourable single-period return actually observed in the available history — an observed fact rather than an estimate. |

*The first five read the **path** the portfolio actually took; the last three read the **distribution** of its returns. Shuffle the order of those returns and the last three are unchanged, while the first five can change completely.*

### 🧩 Am I Diversified? {: #am-i-diversified }

| Metric | What it answers |
|--------|-----------------|
| **[Correlation](correlation.md)** | How holdings move in relation to one another, which is why diversification depends on how positions behave together rather than on how many of them there are. |
| **[Risk Contribution](risk-contribution.md)** | How total portfolio risk is attributed back to the individual holdings — what each position contributes is generally not the same as how much of the portfolio it represents. |
| **[Concentration](concentration.md)** | How far a portfolio's weight is gathered into a few positions, giving a reading that a plain count of holdings cannot provide. |

### ⚖️ Am I Paid for the Risk? {: #am-i-paid-for-the-risk }

| Metric | What it answers |
|--------|-----------------|
| **[Volatility](volatility.md)** | The dispersion of returns — how much value fluctuates, and the building block of nearly every other risk metric. |
| **[Sharpe Ratio](sharpe-ratio.md)** | How much excess return was earned per unit of total volatility. |
| **[Sortino Ratio](sortino-ratio.md)** | The same comparison, with only downside volatility in the denominator. |
| **[Beta & Active Return](beta-active-return.md)** | How strongly a portfolio tends to follow its benchmark, and which part of the result the benchmark does not explain. |
| **[Benchmark Selection](benchmark-selection.md)** | Every benchmark-relative figure inherits the benchmark it was measured against, so the choice of comparison is itself part of the verdict. |

### 🎲 What If…? {: #what-if }

| Metric | What it answers |
|--------|-----------------|
| **[Historical Replay](historical-replay.md)** | What the movements of a real past episode would do to the portfolio as it is composed today. |
| **[Hypothetical Shock](hypothetical-shock.md)** | Replaces the historical episode with a chosen one, which makes it possible to test a scenario that the available history never contained. |
| **[Simulation Modes](simulation-modes.md)** | Each mode rests on its own assumptions, and those assumptions determine as much what its results cannot say as what they can. |

### 🔧 Method {: #method }

| Page | What it answers |
|------|-----------------|
| **[Observed Annualization](observed-annualization.md)** | How a per-period figure becomes an annual one, with the number of periods in a year measured from the data instead of assumed in advance. |
| **[Data Quality](data-quality.md)** | A risk figure is only as trustworthy as the observations behind it, so the amount and freshness of the underlying data belong to the reading of the result. |

---

## 📋 Comparative Overview {: #comparative-overview }

| Metric | What It Measures | Formula | Range | Details |
|--------|-----------------|---------|-------|---------|
| **[Sharpe Ratio](sharpe-ratio.md)** | Risk-adjusted return (total vol) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Sortino Ratio](sortino-ratio.md)** | Risk-adjusted return (downside only) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Max Drawdown](max-drawdown.md)** | Worst peak-to-trough decline | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatility](volatility.md)** | Dispersion of returns | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 When to Use Each Metric {: #when-to-use-each-metric }

| Scenario | Best Metric | Why |
|----------|-------------|-----|
| Comparing two funds | **Sharpe Ratio** | Normalizes return by total risk |
| Asymmetric return distributions | **Sortino Ratio** | Only penalizes downside volatility |
| Worst-case scenario planning | **Max Drawdown** | Shows the maximum pain point |
| General risk assessment | **Volatility** | Foundation for all other metrics |
| Portfolio optimization | **All four** | Each captures a different dimension |

---

## ⚠️ Common Pitfalls {: #common-pitfalls }

!!! warning "Limitations"

    - **Historical metrics ≠ future risk**: Past volatility may not predict future volatility
    - **Normal distribution assumption**: Sharpe and Sortino assume returns are roughly normal; financial returns have fat tails
    - **Lookback sensitivity**: Metrics change significantly depending on the time window
    - **Benchmark dependency**: Sharpe and Sortino depend on the risk-free rate, which changes over time

---

## 🔗 Related {: #related }

- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — How risk reduction works mathematically
- ⚖️ **[Asset Allocation](../../portfolio-theory/asset-allocation.md)** — Using risk metrics to guide allocation
- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — The "return" side of risk-return


