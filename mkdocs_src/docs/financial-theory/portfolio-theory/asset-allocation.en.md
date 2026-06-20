# ⚖️ Asset Allocation

Asset allocation is the process of deciding **how to distribute your portfolio** across different asset classes. Research consistently shows that asset allocation explains the majority of portfolio return variability — more than individual security selection or market timing.

---

## 📊 Strategic vs Tactical Allocation

### 🏗️ Strategic Asset Allocation (SAA)

A **long-term target** based on your risk tolerance, time horizon, and goals:

| Profile | Stocks | Bonds | Alternatives | Cash |
|---------|--------|-------|-------------|------|
| Aggressive (long horizon) | 80-90% | 5-15% | 5-10% | 0-5% |
| Balanced | 50-60% | 30-40% | 5-10% | 5% |
| Conservative (short horizon) | 20-30% | 50-60% | 5-10% | 10-20% |

SAA is reviewed infrequently (annually or upon major life changes).

### 🎯 Tactical Asset Allocation (TAA)

**Short-term deviations** from the strategic target to exploit perceived market opportunities:

- Overweighting an asset class expected to outperform
- Reducing exposure to an asset class showing weakness
- Adjusting for macroeconomic conditions

!!! warning "TAA is difficult"

    Successfully timing the market is extremely difficult. Most academic research shows that tactical adjustments hurt more than they help for average investors.

---

## 📈 Glide Path & Target-Date Strategy

A **glide path** gradually shifts allocation from aggressive (more stocks) to conservative (more bonds) as the investor approaches their goal date (typically retirement):

$$
w_{stocks}(t) = w_{max} - (w_{max} - w_{min}) \cdot \frac{t}{T}
$$

where $t$ is years elapsed and $T$ is time to target date.

### 📉 The Rationale

- **Young investors** have a long time horizon → can tolerate short-term volatility → should hold more stocks
- **Near-retirement investors** need capital preservation → should hold more bonds
- The glide path automates this transition

---

## 🔄 Rebalancing

Over time, asset price movements cause the portfolio to **drift** from its target allocation. Rebalancing restores the original weights.

### 📊 Rebalancing Methods

| Method | Trigger | Pros | Cons |
|--------|---------|------|------|
| **Calendar** | Fixed schedule (monthly, quarterly) | Simple, predictable | May trigger unnecessary trades |
| **Threshold** | When allocation drifts by X% | Only trades when needed | Requires monitoring |
| **Hybrid** | Check calendar, trade if beyond threshold | Best of both | Slightly more complex |

### 📐 Rebalancing Bonus

In a portfolio of volatile, uncorrelated assets, systematic rebalancing generates a **rebalancing bonus** — a small excess return from the discipline of "buying low, selling high" automatically:

$$
R_{rebalanced} \approx R_{buy\&hold} + \frac{1}{2} \sum_i w_i \sigma_i^2 (1 - \rho_{avg})
$$

The bonus is larger when volatilities are high and correlations are low.

---

## 🌍 Geographic Diversification

Beyond asset class allocation, geographic diversification spreads risk across economies:

| Region | Role | Currency Risk |
|--------|------|---------------|
| Domestic | Core holdings, no FX risk | None |
| Developed (US, EU, JP) | Growth + stability | Moderate |
| Emerging (CN, IN, BR) | Higher growth potential | Higher |

!!! info "Currency hedging"

    Foreign investments introduce [FX risk](../../user/fx/index.md). Some ETFs offer hedged variants that neutralize currency exposure, at the cost of the hedging premium.

---

## 🔗 Related

- 🔀 **[Diversification](diversification.md)** — The mathematics behind allocation decisions
- 📊 **[Risk Metrics](../technical-analysis/risk-metrics/index.md)** — Measuring portfolio risk
- 📊 **[Asset Types](../instruments/asset-types/index.md)** — The asset classes to allocate across
- 💰 **[Taxation](../fundamentals/taxation.md)** — Tax-efficient allocation strategies


