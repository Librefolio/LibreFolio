# 📊 Sortino Ratio

The Sortino ratio is a modification of the Sharpe ratio that only penalizes **downside volatility**. It recognizes that investors are primarily concerned with losses, not with upside surprises.

---

## 🔢 Formula

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

where:

- $R_p$ = portfolio return (annualized)
- $R_f$ = risk-free rate (or minimum acceptable return)
- $\sigma_d$ = **downside deviation** (annualized)

### 📐 Downside Deviation

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Only returns **below** the threshold contribute to downside deviation. Returns above the threshold contribute zero.

---

## 💡 Interpretation

| Sortino Ratio | Quality |
|---|---|
| $< 0$ | Returns below the threshold |
| $0 - 1.0$ | Moderate downside-adjusted return |
| $1.0 - 2.0$ | Good |
| $> 2.0$ | Excellent downside risk management |

!!! example "Numerical example"

    Portfolio return: 12%, Risk-free rate: 3%, Downside deviation: 10%

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Compare with Sharpe (if total σ = 15%): $S = 0.60$. The Sortino is higher because upside volatility is excluded.

---

## 📊 Sharpe vs Sortino

| Aspect | Sharpe | Sortino |
|--------|--------|---------|
| **Risk measure** | Total standard deviation | Downside deviation only |
| **Penalizes upside?** | Yes ❌ | No ✅ |
| **Best for** | Symmetric return distributions | Asymmetric / skewed returns |
| **Example** | Broad market index | Options strategies, concentrated portfolios |

### 🔑 When to Prefer Sortino

- **Skewed distributions**: Strategies that have occasional large gains but controlled losses
- **Options-based portfolios**: Inherently asymmetric payoffs
- **Growth stocks**: Tend to have positively skewed return distributions
- **Any investor** who cares about downside risk more than total risk

---

## ⚠️ Limitations

!!! warning "Small sample bias"

    Downside deviation requires sufficient data points below the threshold. With few negative returns (e.g., short bull market periods), the estimate becomes unreliable and the Sortino ratio can be misleadingly high.

---

## 🔗 Related

- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Total volatility variant
- 📊 **[Volatility](volatility.md)** — Understanding standard deviation
- 📈 **[Max Drawdown](max-drawdown.md)** — Another downside-focused metric


