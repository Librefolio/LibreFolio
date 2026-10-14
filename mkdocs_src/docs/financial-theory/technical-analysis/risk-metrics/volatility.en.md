# 📊 Volatility

Volatility measures the **dispersion of returns** — how much an asset's price fluctuates over time. It is the most fundamental risk measure in finance and the building block for nearly all other risk metrics.

---

## 🔢 Formula {: #formula }

### 📐 Standard Deviation of Returns {: #standard-deviation-of-returns }

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

where $R_i$ are individual period returns and $\bar{R}$ is the mean return.

### 📈 Annualization {: #annualization }

Per-period volatility is annualized by multiplying it by the square root of the number of periods a year contains:

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

The factor $f$ is **measured from the observed data**, not fixed in advance: it is the number of returns actually used, rescaled to a full calendar year over the span they cover.

$$
f = \frac{N \times 365}{D}
$$

where $N$ is the number of period returns and $D$ the calendar days they span.

!!! info "Why a square root?"

    Returns are assumed to be independent across periods. The variance of a sum of $f$ independent variables is $f$ times the individual variance. Therefore:

    $$\text{Var}_{annual} = f \times \text{Var}_{period}$$

    $$\sigma_{annual} = \sqrt{f} \times \sigma_{period}$$

!!! info "√252 is a result, not a constant"

    A daily-priced stock contributes roughly 252 returns over a full calendar year, so $f = 252 \times 365 / 365 = 252$ and the familiar $\sqrt{252}$ is recovered — as the outcome of the measurement, not as an assumption written into it. An instrument that trades every calendar day, such as crypto, gives $f \approx 365$ and therefore $\approx \sqrt{365}$: a hardcoded $\sqrt{252}$ would **understate** its annualized volatility. A weekly-priced fund gives $f \approx 52$.

    → See **[Observed Annualization](observed-annualization.md)** for the derivation, the worked examples and what coverage adds to them.

---

## 💡 Interpretation {: #interpretation }

| Annualized Volatility | Typical Assets |
|---|---|
| 1-5% | Money market, short-term bonds |
| 5-15% | Government bonds, investment-grade corporates |
| 15-25% | Large-cap stocks, diversified equity ETFs |
| 25-40% | Small-cap stocks, single stocks |
| 40-80%+ | Crypto, meme stocks, leveraged products |

---

## 📊 Realized vs Implied Volatility {: #realized-vs-implied-volatility }

### 📈 Realized (Historical) Volatility {: #realized-historical-volatility }

Computed from **past** price data. This is what LibreFolio computes:

$$
\sigma_{realized} = \text{StdDev}(\text{historical returns})
$$

### 🔮 Implied Volatility {: #implied-volatility }

Extracted from **options prices** using the Black-Scholes model. It represents the market's **expectation** of future volatility:

$$
C = f(S, K, T, r, \sigma_{implied})
$$

Implied volatility is forward-looking but only available for optionable assets.

---

## 🔄 Rolling Window Volatility {: #rolling-window-volatility }

Rather than computing a single volatility number for the entire period, **rolling window volatility** computes $\sigma$ over a sliding window (e.g., 30 days), producing a time series that shows how volatility evolves:

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

This is useful for:

- Identifying **volatility regimes** (calm vs turbulent periods)
- Detecting **volatility clustering** (high-volatility days tend to follow high-volatility days)
- Setting dynamic position sizes (reduce exposure during high-volatility periods)

---

## 📐 Volatility and Portfolio Theory {: #volatility-and-portfolio-theory }

Volatility plays a central role in [Modern Portfolio Theory](../index.md):

- It is the **denominator** of the [Sharpe Ratio](sharpe-ratio.md)
- It determines the **width** of [Bollinger Bands](../../technical-analysis/indicators/bollinger-bands.md)
- It is the key input for portfolio optimization (minimizing $\sigma_p$ for a target $R_p$)
- [Diversification](../../portfolio-theory/diversification.md) reduces portfolio volatility when asset correlations are less than 1

---

## ⚠️ Limitations {: #limitations }

!!! warning "Volatility ≠ Risk"

    Volatility treats upside and downside movements equally. An asset that frequently spikes upward has high volatility but may be very attractive. For a downside-focused measure, use the [Sortino Ratio](sortino-ratio.md) or [Max Drawdown](max-drawdown.md).

!!! warning "Non-normality"

    Financial returns typically have:

    - **Fat tails** (more extreme events than a normal distribution predicts)
    - **Negative skew** (large drops more common than large gains)
    - **Volatility clustering** (calm and turbulent periods)

    Standard deviation alone doesn't capture these features.

---

## 🔗 Related {: #related }

- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Uses volatility as risk denominator
- 📊 **[Sortino Ratio](sortino-ratio.md)** — Downside-only volatility variant
- 📏 **[Bollinger Bands](../../technical-analysis/indicators/bollinger-bands.md)** — Volatility envelope on charts
- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — Reducing portfolio volatility


