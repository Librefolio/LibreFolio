# 📉 EMA — Exponential Moving Average

The EMA tracks the **trend** by smoothing daily price noise, giving more weight to recent observations than older ones.

---

## 💡 Financial Meaning

Traders overlay EMAs of different periods on a price chart: when a short-period EMA crosses *above* a long-period EMA, it signals upward momentum (a "golden cross"); the opposite crossing signals a slowdown ("death cross").

---

## 🔢 Mathematical Formula

The EMA is defined by the first-order recurrence:

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

where $P_t$ is the closing price at time $t$ and $\alpha$ is the **smoothing coefficient**.

**Mapping $N$ → $\alpha$.**
Traders specify a "period" $N$ (in days). The coefficient is derived by matching the *average age* of data between an EMA and a Simple Moving Average (SMA) of the same window:

$$
\text{Age}_{SMA} = \frac{N-1}{2}, \qquad
\text{Age}_{EMA} = \frac{1-\alpha}{\alpha}
$$

Setting them equal:

$$
\alpha = \frac{2}{N+1}
$$

For example, $N = 14 \implies \alpha = 2/15 \approx 0.133$.

---

## ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Period ($N$) | `period` | 14 | Lookback window in days. Higher → smoother, slower. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

---

## 🎛️ Signal Processing Equivalent — First-Order IIR Low-Pass Filter

The recurrence $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ is precisely a **first-order IIR (Infinite Impulse Response) low-pass filter**. Its transfer function in the $z$-domain is:

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

The $-3\,\text{dB}$ cut-off frequency (normalised) is:

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

When $\alpha$ is small ($N$ large) the pass-band narrows dramatically, attenuating all but the DC component (the long-run trend).

!!! tip "Pole location"

    The single pole sits at $z = 1-\alpha$. For $N = 200$, $\alpha \approx 0.01$, so
    the pole is at $z = 0.99$ — extremely close to the unit circle, which explains the
    heavy smoothing and large group delay.

:material-link: [EMA on Wikipedia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }


