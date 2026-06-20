# 📈 Portfolio Theory

Portfolio theory provides the mathematical framework for constructing investment portfolios that maximize expected return for a given level of risk — or equivalently, minimize risk for a given expected return.

---

## 📖 Overview

### 🏛️ Modern Portfolio Theory (MPT)

Introduced by Harry Markowitz in 1952, Modern Portfolio Theory revolutionized investing by showing that **portfolio risk is not simply the sum of individual asset risks**. Through diversification, an investor can reduce portfolio volatility without sacrificing expected return.

The key insight: what matters is not just each asset's individual risk and return, but how assets move **relative to each other** (correlation).

### 📐 The Efficient Frontier

The efficient frontier is the set of portfolios that offer the **highest expected return for each level of risk**:

$$
\max_{w} \quad E[R_p] = \sum_i w_i \cdot E[R_i]
$$

subject to:

$$
\sigma_p^2 = \sum_i \sum_j w_i w_j \sigma_i \sigma_j \rho_{ij} \leq \sigma_{target}^2
$$

where $w_i$ are portfolio weights, $E[R_i]$ expected returns, $\sigma_i$ volatilities, and $\rho_{ij}$ correlations.

Any portfolio **below** the frontier is suboptimal — you could get higher return at the same risk, or lower risk at the same return.

---

## 📖 What's Inside

### 🔀 [Diversification](diversification.md)

The mathematical foundation of "don't put all your eggs in one basket." How combining assets with imperfect correlation reduces portfolio variance — and the limits of diversification against systematic risk.

### ⚖️ [Asset Allocation](asset-allocation.md)

Strategic vs tactical allocation, glide paths, target-date strategies, and the art of rebalancing. How to decide *how much* of each asset class to hold.

### 📊 [Risk Metrics](../technical-analysis/risk-metrics/index.md)

Quantitative measures of portfolio risk. From standard deviation to Sharpe ratio, each metric captures a different aspect of risk:

- **[Sharpe Ratio](../technical-analysis/risk-metrics/sharpe-ratio.md)** — Risk-adjusted return (total volatility)
- **[Sortino Ratio](../technical-analysis/risk-metrics/sortino-ratio.md)** — Risk-adjusted return (downside only)
- **[Max Drawdown](../technical-analysis/risk-metrics/max-drawdown.md)** — Worst peak-to-trough decline
- **[Volatility](../technical-analysis/risk-metrics/volatility.md)** — Standard deviation of returns

---

## 🔑 Key Assumptions & Limitations

!!! warning "MPT assumptions"

    Modern Portfolio Theory assumes:

    1. **Rational investors** who seek to maximize utility
    2. **Normal distribution** of returns (in practice, returns have fat tails)
    3. **Known** expected returns, volatilities, and correlations (in practice, these are estimated with error)
    4. **Frictionless markets** — no taxes, no transaction costs (LibreFolio helps you track these!)

Despite these limitations, MPT remains the foundation of institutional portfolio management and provides the vocabulary used by the entire investment industry.

---

## 🔗 Related Sections

- 🏦 **[Instruments](../instruments/index.md)** — The building blocks of portfolios
- 📐 **[Fundamentals](../fundamentals/index.md)** — Returns, day count conventions, taxation
- 📊 **[Technical Analysis](../technical-analysis/index.md)** — Individual asset analysis tools


