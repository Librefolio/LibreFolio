# 📏 Bollinger Bands

Bollinger Bands dynamically measure **volatility** and draw an adaptive "normality fence" around the price.

---

## 💡 Financial Meaning

When the bands are wide, the market is volatile; when they squeeze together, a breakout is imminent. A price touching the upper band signals statistical exuberance; touching the lower band signals an abnormal dip.

---

## 🔢 Mathematical Formulas

1.  **Middle Band** (expected value):

    $$
    MB_t = SMA_N(C_t)
    $$

2.  **Standard deviation** of prices over the window:

    $$
    \sigma_t = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (C_{t-i} - MB_t)^2}
    $$

3.  **Upper and Lower Bands**:

    $$
    Upper_t = MB_t + k \cdot \sigma_t, \qquad
    Lower_t = MB_t - k \cdot \sigma_t
    $$

With $k = 2$, if returns were normally distributed the price would stay inside the bands ~95.4% of the time. In practice, financial returns have *fat tails* (leptokurtosis), so breaches are more frequent — but still statistically significant.

---

## ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Period ($N$) | `period` | 20 | SMA window for expected value. |
| Multiplier ($k$) | `multiplier` | 2 | Number of standard deviations. |

---

## 🎛️ Signal Processing Equivalent — Adaptive Confidence Interval Tracker

The Middle Band is a **FIR (Finite Impulse Response) moving average filter** — the simplest low-pass with a rectangular window of length $N$. The bands add a **time-varying envelope** at $\pm k\sigma$, which is essentially a running estimate of the signal's instantaneous variance.

In the language of adaptive filters, this is an **expected-value tracker with an adaptive confidence interval**. When the variance $\sigma^2$ drops (the "Bollinger Squeeze"), the system is in a low-entropy state. In chaotic systems like financial markets, low-entropy periods are reliably followed by high-entropy (high-volatility) explosions — making the squeeze one of the most watched setups in technical analysis.

!!! info "FIR vs IIR"

    Unlike the EMA (IIR, one pole), the SMA is a **FIR filter** with a perfectly flat
    group delay of $(N-1)/2$ samples. It trades off a wider transition band for
    zero-phase distortion — ideal for centring the confidence envelope.

:material-link: [Bollinger Bands on Wikipedia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }


