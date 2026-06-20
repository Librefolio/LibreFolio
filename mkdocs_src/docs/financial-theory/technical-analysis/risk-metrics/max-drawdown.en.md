# 📉 Max Drawdown

Max Drawdown (MDD) measures the **largest peak-to-trough decline** in portfolio value before a new peak is established. It answers the question: *"What was the worst loss an investor could have experienced?"*

---

## 🔢 Formula

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

where $V_t$ is the portfolio value at time $t$.

The drawdown at any point $t$ is:

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

Max drawdown is the minimum (most negative) value of $DD_t$ over the entire observation period.

---

## 💡 Interpretation

| Max Drawdown | Typical Context |
|---|---|
| $-5\%$ to $-10\%$ | Normal correction, well-diversified portfolio |
| $-10\%$ to $-20\%$ | Significant correction |
| $-20\%$ to $-30\%$ | Bear market territory |
| $-30\%$ to $-50\%$ | Severe bear market (2008, COVID-2020) |
| $> -50\%$ | Catastrophic (concentrated positions, crypto) |

!!! example "Numerical example"

    Portfolio value sequence: 100 → 120 → 90 → 110 → 130

    - Peak: 120
    - Trough: 90
    - MDD: $(90 - 120) / 120 = -25\%$
    - Recovery: reached 120 again, then new high at 130

---

## ⏱️ Recovery Time

An equally important metric is **recovery time** — how long it takes to recover from the drawdown and reach a new peak:

$$
T_{recovery} = t_{new\_peak} - t_{trough}
$$

| Asset Class | Typical Recovery Time (after major drawdown) |
|-------------|---------------------------------------------|
| US Stocks (S&P 500) | 1-5 years |
| Bonds | Months to 1-2 years |
| Crypto | Highly variable (months to years) |

!!! warning "Asymmetry of losses"

    A 50% loss requires a **100% gain** to recover:

    $$
    \text{Required gain} = \frac{1}{1 + MDD} - 1
    $$

    <div style="display: flex; justify-content: center;">

    | Loss | Required Gain |
    |:----:|:-------------:|
    | -10% | +11.1% |
    | -25% | +33.3% |
    | -50% | +100% |
    | -75% | +300% |

    </div>

---

## 📊 Drawdown Chart

A drawdown chart plots $DD_t$ over time. It's always zero or negative, touching zero at each new peak. The deepest valley is the max drawdown. This visualization makes it easy to:

- Identify the **timing** of worst-case periods
- See how frequently drawdowns occur
- Compare recovery patterns across different strategies

---

## 🔗 Related

- 📊 **[Volatility](volatility.md)** — Standard deviation doesn't capture drawdown severity
- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Risk-adjusted return (uses volatility, not drawdown)
- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — The primary tool for reducing max drawdown
