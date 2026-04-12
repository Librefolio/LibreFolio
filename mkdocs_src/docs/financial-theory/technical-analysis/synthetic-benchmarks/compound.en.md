# 📊 Compound Growth

A compound growth benchmark represents **compound interest** — the value grows exponentially, meaning returns are reinvested.

---

## 💡 Financial Meaning

This is the natural growth model for most financial assets and the standard assumption in discounted cash flow (DCF) analysis. Compound growth produces an exponential curve that accelerates over time — the foundation of long-term wealth building.

---

## 🔢 Mathematical Formula

$$
y(t) = y_0 \cdot (1 + r)^t
$$

where:

- $y_0$ is the starting value,
- $r$ is the annual growth rate (decimal),
- $t$ is time in years from the start.

This is equivalent to the **compound interest** formula $A = P(1 + r)^t$ with annual compounding. The generalised formula with $n$ compounding periods per year is:

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

LibreFolio's backend supports the following compounding frequencies: **Annual** ($n=1$), **Semiannual** ($n=2$), **Quarterly** ($n=4$), **Monthly** ($n=12$), **Daily** ($n=365$), and **Continuous** ($n \to \infty$).

When $n \to \infty$ (continuous compounding):

$$
A = P \cdot e^{r \cdot t}
$$

---

## 🔄 Iterative Computation (Daily Stepping)

In LibreFolio the compound curve is computed **iteratively** rather than calling `pow()` for each data point. This is both more efficient and instructive:

$$
\text{dailyFactor} = (1 + r)^{1/365}
$$

Then, for each successive day:

$$
y_{i+1} = y_i \cdot \text{dailyFactor}
$$

This is mathematically equivalent to the closed-form $y_0(1+r)^t$ but replaces $N$ expensive power operations with $N$ simple multiplications — the same principle behind how banks actually accrue daily compound interest.

!!! tip "Rule of 72"

    A quick mental shortcut: an investment growing at $r$% per year will approximately
    double in $72 / r$ years. At 7% → ~10.3 years.

---

## ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Annual Rate | `annualRate` | 7 | Compound growth rate in percent per year. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

---

## 🔍 Interpretation

The curve is straight on a **logarithmic** scale — this is the telltale sign of exponential growth. Overlaying a compound benchmark on a log-scale chart is the cleanest way to judge whether an asset is growing faster or slower than a target rate.

:material-link: [Compound Interest on Wikipedia](https://en.wikipedia.org/wiki/Compound_interest){ target="_blank" }


