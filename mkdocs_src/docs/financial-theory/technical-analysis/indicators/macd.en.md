# 📊 MACD — Moving Average Convergence Divergence

The MACD answers: *"Is the trend accelerating or losing steam?"* It tells you whether the *rate of change* of the trend is positive or negative.

---

## 💡 Financial Meaning

Traders watch for the MACD line crossing the Signal line — a bullish crossover suggests increasing momentum, a bearish one suggests exhaustion. The MACD does **not** tell you the price is rising (you can see that already); it tells you whether the momentum is increasing or decreasing.

---

## 🔢 Mathematical Formulas

The MACD system produces three series:

1.  **MACD Line** (the band-pass output):

    $$
    MACD_t = EMA_{fast}(C_t) - EMA_{slow}(C_t)
    $$

2.  **Signal Line** (smoothed MACD):

    $$
    Signal_t = EMA_{signal}(MACD_t)
    $$

3.  **Histogram** (momentum delta):

    $$
    Histogram_t = MACD_t - Signal_t
    $$

---

## ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Fast Period | `fastPeriod` | 12 | Short-term EMA window (days). |
| Slow Period | `slowPeriod` | 26 | Long-term EMA window (days). |
| Signal Period | `signalPeriod` | 9 | EMA smoothing applied to the MACD line. |

---

## 🎛️ Signal Processing Equivalent — Band-Pass Filter (Smoothed Derivative)

Subtracting two low-pass filters with different cut-off frequencies produces a **band-pass filter**. $EMA_{fast} - EMA_{slow}$ cancels the DC component (the long-run trend shared by both) and suppresses high-frequency noise (already filtered by both EMAs). What remains is the *mid-frequency* band: the momentum oscillation.

In the $z$-domain:

$$
H_{MACD}(z) = H_{fast}(z) - H_{slow}(z)
    = \frac{\alpha_f}{1-(1-\alpha_f)z^{-1}}
    - \frac{\alpha_s}{1-(1-\alpha_s)z^{-1}}
$$

The Signal Line is yet another low-pass applied to this band-pass output — it acts as a **matched filter**, delaying the signal slightly to reduce false-positive crossover detections.

!!! note "Derivative interpretation"

    For small $\alpha$, $EMA_{fast} - EMA_{slow}$ behaves like a smoothed first
    derivative $\frac{d}{dt}[\text{trend}]$. When the histogram flips sign, the
    "velocity" of the trend changes direction.

:material-link: [MACD on Wikipedia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }


