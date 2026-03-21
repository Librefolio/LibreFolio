# 📉 Technical Indicators

This page documents the technical analysis indicators available as chart overlays in
LibreFolio's FX module. Each indicator is explained from two complementary perspectives:
the **financial** interpretation that traders use daily, and the **signal processing**
equivalent that engineers from control systems or DSP backgrounds will recognise
instantly.

!!! info "Why two perspectives?"
    Financial markets are **not** stationary LTI (Linear Time-Invariant) systems — they
    are noisy, chaotic, and their spectral content shifts over time. Yet the mathematical
    tools we apply to extract trend, momentum, or volatility are *exactly* the same
    discrete-time filters taught in any signal processing course. If you have ever
    designed a Butterworth low-pass or computed a running variance, you already understand
    these indicators — just under different names.

---

## ⚡ The "Fast" vs "Slow" Intuition

In finance, *fast* and *slow* refer to the **time constant** ($\tau$) of the underlying
filter.

| Property | Fast (small $N$) | Slow (large $N$) |
|---|---|---|
| Cut-off frequency $f_c$ | Higher | Lower |
| Noise rejection | Poor — lets HF through | Good — strong smoothing |
| Phase lag | Small — reacts quickly | Large — significant delay |
| Typical $N$ | 9, 12, 14 | 26, 50, 200 |

---

## 📉 EMA — Exponential Moving Average { #ema }

### 💡 Financial Meaning

The EMA tracks the **trend** by smoothing daily price noise, giving more weight to
recent observations than older ones. Traders overlay EMAs of different periods on a
price chart: when a short-period EMA crosses *above* a long-period EMA, it signals
upward momentum (a "golden cross"); the opposite crossing signals a slowdown ("death
cross").

### 🔢 Mathematical Formula

The EMA is defined by the first-order recurrence:

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

where $P_t$ is the closing price at time $t$ and $\alpha$ is the **smoothing
coefficient**.

**Mapping $N$ → $\alpha$.**
Traders specify a "period" $N$ (in days). The coefficient is derived by matching the
*average age* of data between an EMA and a Simple Moving Average (SMA) of the same
window:

$$
\text{Age}_{SMA} = \frac{N-1}{2}, \qquad
\text{Age}_{EMA} = \frac{1-\alpha}{\alpha}
$$

Setting them equal:

$$
\alpha = \frac{2}{N+1}
$$

For example, $N = 14 \implies \alpha = 2/15 \approx 0.133$.

### ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Period ($N$) | `period` | 14 | Lookback window in days. Higher → smoother, slower. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

### 🎛️ Signal Processing Equivalent — First-Order IIR Low-Pass Filter

The recurrence $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ is precisely a **first-order
IIR (Infinite Impulse Response) low-pass filter**. Its transfer function in the
$z$-domain is:

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

The $-3\,\text{dB}$ cut-off frequency (normalised) is:

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

When $\alpha$ is small ($N$ large) the pass-band narrows dramatically, attenuating all
but the DC component (the long-run trend).

!!! tip "Pole location"
    The single pole sits at $z = 1-\alpha$. For $N = 200$, $\alpha \approx 0.01$, so
    the pole is at $z = 0.99$ — extremely close to the unit circle, which explains the
    heavy smoothing and large group delay.

:material-link: [EMA on Wikipedia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }

---

## 📊 MACD — Moving Average Convergence Divergence { #macd }

### 💡 Financial Meaning

The MACD answers: *"Is the trend accelerating or losing steam?"* It does **not** tell
you the price is rising (you can see that already); it tells you whether the *rate of
change* of the trend is positive or negative. Traders watch for the MACD line crossing
the Signal line — a bullish crossover suggests increasing momentum, a bearish one
suggests exhaustion.

### 🔢 Mathematical Formulas

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

### ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Fast Period | `fastPeriod` | 12 | Short-term EMA window (days). |
| Slow Period | `slowPeriod` | 26 | Long-term EMA window (days). |
| Signal Period | `signalPeriod` | 9 | EMA smoothing applied to the MACD line. |

### 🎛️ Signal Processing Equivalent — Band-Pass Filter (Smoothed Derivative)

Subtracting two low-pass filters with different cut-off frequencies produces a
**band-pass filter**. $EMA_{fast} - EMA_{slow}$ cancels the DC component (the
long-run trend shared by both) and suppresses high-frequency noise (already filtered
by both EMAs). What remains is the *mid-frequency* band: the momentum oscillation.

In the $z$-domain:

$$
H_{MACD}(z) = H_{fast}(z) - H_{slow}(z)
    = \frac{\alpha_f}{1-(1-\alpha_f)z^{-1}}
    - \frac{\alpha_s}{1-(1-\alpha_s)z^{-1}}
$$

The Signal Line is yet another low-pass applied to this band-pass output — it acts as
a **matched filter**, delaying the signal slightly to reduce false-positive crossover
detections.

!!! note "Derivative interpretation"
    For small $\alpha$, $EMA_{fast} - EMA_{slow}$ behaves like a smoothed first
    derivative $\frac{d}{dt}[\text{trend}]$. When the histogram flips sign, the
    "velocity" of the trend changes direction.

:material-link: [MACD on Wikipedia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }

---

## 💪 RSI — Relative Strength Index { #rsi }

### 💡 Financial Meaning

The RSI measures whether buyers or sellers have dominated *recently*. It answers:
*"Over the last $N$ days, how much of the total price movement was upward vs
downward?"* The result is squeezed into a 0–100 range:

- **RSI > 70** → Overbought — the spring is stretched, a pullback is statistically
  likely.
- **RSI < 30** → Oversold — the spring is compressed, a bounce is likely.

### 🔢 Mathematical Formulas

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

The normalisation $100 - 100/(1+RS)$ is a monotonically increasing sigmoid that maps
$RS \in [0, \infty)$ to $RSI \in [0, 100)$.

### ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Period ($N$) | `period` | 14 | Lookback window for SMMA. |
| Overbought | `overbought` | 70 | Threshold for overbought zone. |
| Oversold | `oversold` | 30 | Threshold for oversold zone. |

### 🎛️ Signal Processing Equivalent — Duty Cycle / Saturation Indicator

Imagine splitting the price delta signal $\Delta P[n]$ into its positive and negative
half-wave rectified components, then low-pass filtering each. The RSI is the **ratio
of the positive envelope to the total envelope**, rescaled to $[0, 100]$.

In control systems terms, it is a **saturation detector**: when the system output (price)
has been moving in one direction for too long, the RSI signals that the actuator (market)
is near its rail. Like any oscillator in a feedback loop, the further from equilibrium,
the stronger the restoring force — hence the mean-reverting property traders exploit.

!!! warning "Non-stationarity"
    The 70/30 thresholds assume roughly symmetric return distributions. In strong
    trending markets the RSI can stay above 70 for weeks — it is a *probabilistic*
    indicator, not a deterministic one.

:material-link: [RSI on Wikipedia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }

---

## 📏 Bollinger Bands { #bollinger-bands }

### 💡 Financial Meaning

Bollinger Bands dynamically measure **volatility** and draw an adaptive "normality
fence" around the price. When the bands are wide, the market is volatile; when they
squeeze together, a breakout is imminent. A price touching the upper band signals
statistical exuberance; touching the lower band signals an abnormal dip.

### 🔢 Mathematical Formulas

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

With $k = 2$, if returns were normally distributed the price would stay inside the bands
~95.4% of the time. In practice, financial returns have *fat tails* (leptokurtosis), so
breaches are more frequent — but still statistically significant.

### ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Period ($N$) | `period` | 20 | SMA window for expected value. |
| Multiplier ($k$) | `multiplier` | 2 | Number of standard deviations. |

### 🎛️ Signal Processing Equivalent — Adaptive Confidence Interval Tracker

The Middle Band is a **FIR (Finite Impulse Response) moving average filter** — the
simplest low-pass with a rectangular window of length $N$. The bands add a
**time-varying envelope** at $\pm k\sigma$, which is essentially a running estimate of
the signal's instantaneous variance.

In the language of adaptive filters, this is an **expected-value tracker with an
adaptive confidence interval**. When the variance $\sigma^2$ drops (the "Bollinger
Squeeze"), the system is in a low-entropy state. In chaotic systems like financial
markets, low-entropy periods are reliably followed by high-entropy (high-volatility)
explosions — making the squeeze one of the most watched setups in technical analysis.

!!! info "FIR vs IIR"
    Unlike the EMA (IIR, one pole), the SMA is a **FIR filter** with a perfectly flat
    group delay of $(N-1)/2$ samples. It trades off a wider transition band for
    zero-phase distortion — ideal for centring the confidence envelope.

:material-link: [Bollinger Bands on Wikipedia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }
