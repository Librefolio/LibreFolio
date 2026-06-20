# 📊 Volatility

Volatility measures the **dispersion of returns** — how much an asset's price fluctuates over time. It is the most fundamental risk measure in finance and the building block for nearly all other risk metrics.

---

## 🔢 Formula

### 📐 Standard Deviation of Returns

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

where $R_i$ are individual period returns and $\bar{R}$ is the mean return.

### 📈 Annualization

Daily volatility is annualized by multiplying by the square root of the number of trading days:

$$
\sigma_{annual} = \sigma_{daily} \times \sqrt{252}
$$

!!! info "Why √252?"

    Returns are assumed to be independent across days. The variance of a sum of $N$ independent variables is $N$ times the individual variance. Therefore:

    $$\text{Var}_{annual} = 252 \times \text{Var}_{daily}$$
    $$\sigma_{annual} = \sqrt{252} \times \sigma_{daily}$$

---

## 💡 Interpretation

| Annualized Volatility | Typical Assets |
|---|---|
| 1-5% | Money market, short-term bonds |
| 5-15% | Government bonds, investment-grade corporates |
| 15-25% | Large-cap stocks, diversified equity ETFs |
| 25-40% | Small-cap stocks, single stocks |
| 40-80%+ | Crypto, meme stocks, leveraged products |

---

## 📊 Realized vs Implied Volatility

### 📈 Realized (Historical) Volatility

Computed from **past** price data. This is what LibreFolio computes:

$$
\sigma_{realized} = \text{StdDev}(\text{historical returns})
$$

### 🔮 Implied Volatility

Extracted from **options prices** using the Black-Scholes model. It represents the market's **expectation** of future volatility:

$$
C = f(S, K, T, r, \sigma_{implied})
$$

Implied volatility is forward-looking but only available for optionable assets.

---

## 🔄 Rolling Window Volatility

Rather than computing a single volatility number for the entire period, **rolling window volatility** computes $\sigma$ over a sliding window (e.g., 30 days), producing a time series that shows how volatility evolves:

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

This is useful for:

- Identifying **volatility regimes** (calm vs turbulent periods)
- Detecting **volatility clustering** (high-volatility days tend to follow high-volatility days)
- Setting dynamic position sizes (reduce exposure during high-volatility periods)

---

## 📐 Volatility and Portfolio Theory

Volatility plays a central role in [Modern Portfolio Theory](../index.md):

- It is the **denominator** of the [Sharpe Ratio](sharpe-ratio.md)
- It determines the **width** of [Bollinger Bands](../../technical-analysis/indicators/bollinger-bands.md)
- It is the key input for portfolio optimization (minimizing $\sigma_p$ for a target $R_p$)
- [Diversification](../../portfolio-theory/diversification.md) reduces portfolio volatility when asset correlations are less than 1

---

## ⚠️ Limitations

!!! warning "Volatility ≠ Risk"

    Volatility treats upside and downside movements equally. An asset that frequently spikes upward has high volatility but may be very attractive. For a downside-focused measure, use the [Sortino Ratio](sortino-ratio.md) or [Max Drawdown](max-drawdown.md).

!!! warning "Non-normality"

    Financial returns typically have:

    - **Fat tails** (more extreme events than a normal distribution predicts)
    - **Negative skew** (large drops more common than large gains)
    - **Volatility clustering** (calm and turbulent periods)

    Standard deviation alone doesn't capture these features.

---

## 🔗 Related

- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Uses volatility as risk denominator
- 📊 **[Sortino Ratio](sortino-ratio.md)** — Downside-only volatility variant
- 📏 **[Bollinger Bands](../../technical-analysis/indicators/bollinger-bands.md)** — Volatility envelope on charts
- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — Reducing portfolio volatility


