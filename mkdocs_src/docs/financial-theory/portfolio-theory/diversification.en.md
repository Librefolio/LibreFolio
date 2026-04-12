# 🔀 Diversification

Diversification is the most fundamental risk management strategy: by combining assets that don't move in perfect lockstep, an investor can **reduce portfolio volatility** without necessarily reducing expected return.

---

## 📐 The Mathematics

### 📊 Two-Asset Portfolio Variance

For a portfolio of two assets with weights $w_1$ and $w_2 = 1 - w_1$:

$$
\sigma_p^2 = w_1^2 \sigma_1^2 + w_2^2 \sigma_2^2 + 2 w_1 w_2 \sigma_1 \sigma_2 \rho_{12}
$$

where:

- $\sigma_1, \sigma_2$ are the individual asset volatilities
- $\rho_{12}$ is the **correlation coefficient** ($-1 \leq \rho \leq +1$)

The magic of diversification lies in the **cross-term**: when $\rho_{12} < 1$, the portfolio variance is **less** than the weighted average of individual variances.

### 🔑 Correlation Effects

| Correlation $\rho$ | Effect | Example |
|---|---|---|
| $+1$ | No diversification benefit — assets move identically | Two S&P 500 ETFs |
| $0$ | Significant variance reduction | Stocks vs Gold |
| $-1$ | Perfect hedge — variance can reach zero | Long stock + put option |

### 📈 N-Asset Generalization

For $N$ assets:

$$
\sigma_p^2 = \sum_{i=1}^{N} \sum_{j=1}^{N} w_i w_j \sigma_i \sigma_j \rho_{ij}
$$

As $N$ increases, the contribution of individual variances shrinks (proportional to $1/N$), but the contribution of covariances remains. This leads to the concept of **systematic risk**.

---

## 🎯 Systematic vs Idiosyncratic Risk

### 📊 Idiosyncratic (Diversifiable) Risk

Risk specific to a single company or asset. Examples:

- CEO departure
- Product recall
- Patent expiration

This risk **can be diversified away** by holding many assets. With ~30 uncorrelated stocks, idiosyncratic risk approaches zero.

### 🌍 Systematic (Non-Diversifiable) Risk

Risk affecting the entire market. Examples:

- Interest rate changes
- Recessions
- Pandemics
- Geopolitical events

This risk **cannot be eliminated** through diversification. It is the risk that investors are compensated for bearing — the foundation of the Capital Asset Pricing Model (CAPM).

$$
\sigma_{portfolio}^2 = \underbrace{\sigma_{systematic}^2}_{\text{cannot remove}} + \underbrace{\sigma_{idiosyncratic}^2}_{\xrightarrow{N \to \infty} 0}
$$

---

## ⚠️ Diversification Pitfalls

!!! warning "Correlation instability"

    Correlations are **not constant** — they tend to increase during market crises (exactly when diversification is most needed). This phenomenon, called **correlation breakdown**, means that diversification provides less protection during extreme events than historical data suggests.

!!! info "Over-diversification"

    Beyond a certain point, adding more assets increases complexity and cost (transaction fees, tax complexity) without meaningfully reducing risk. The sweet spot for most investors is 20-40 holdings across different asset classes and geographies.

---

## 🔗 Related

- ⚖️ **[Asset Allocation](asset-allocation.md)** — How to choose portfolio weights
- 📊 **[Volatility](risk-metrics/volatility.md)** — Measuring the risk that diversification reduces
- 📈 **[Max Drawdown](risk-metrics/max-drawdown.md)** — The worst-case scenario metric


