# 💪 RSI — Relative Strength Index

The RSI measures whether buyers or sellers have dominated *recently*. It answers: *"Over the last $N$ days, how much of the total price movement was upward vs downward?"*

---

## 💡 Financial Meaning

The result is squeezed into a 0–100 range:

- **RSI > 70** → Overbought — the spring is stretched, a pullback is statistically likely.
- **RSI < 30** → Oversold — the spring is compressed, a bounce is likely.

---

## 🔢 Mathematical Formulas

1.  **Decompose** daily changes into gains and losses:

    $$
    U_t = \max(P_t - P_{t-1},\; 0), \qquad
    D_t = \max(P_{t-1} - P_t,\; 0)
    $$

2.  **Smooth** each component with an exponential moving average (SMMA variant):

    $$
    \overline{U} = SMMA_N(U), \qquad
    \overline{D} = SMMA_N(D)
    $$

3.  **Relative Strength** ratio and normalisation:

    $$
    RS = \frac{\overline{U}}{\overline{D}}, \qquad
    RSI = 100 - \frac{100}{1 + RS}
    $$

The normalisation $100 - 100/(1+RS)$ is a monotonically increasing sigmoid that maps $RS \in [0, \infty)$ to $RSI \in [0, 100)$.

---

## ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Period ($N$) | `period` | 14 | Lookback window for SMMA. |
| Overbought | `overbought` | 70 | Threshold for overbought zone. |
| Oversold | `oversold` | 30 | Threshold for oversold zone. |

---

## 🎛️ Signal Processing Equivalent — Duty Cycle / Saturation Indicator

Imagine splitting the price delta signal $\Delta P[n]$ into its positive and negative half-wave rectified components, then low-pass filtering each. The RSI is the **ratio of the positive envelope to the total envelope**, rescaled to $[0, 100]$.

In control systems terms, it is a **saturation detector**: when the system output (price) has been moving in one direction for too long, the RSI signals that the actuator (market) is near its rail. Like any oscillator in a feedback loop, the further from equilibrium, the stronger the restoring force — hence the mean-reverting property traders exploit.

!!! warning "Non-stationarity"

    The 70/30 thresholds assume roughly symmetric return distributions. In strong
    trending markets the RSI can stay above 70 for weeks — it is a *probabilistic*
    indicator, not a deterministic one.

:material-link: [RSI on Wikipedia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }


