# 🩹 Ulcer Index

The Ulcer Index combines how deep a portfolio falls with how long it stays down, so a shallow decline that persists can score worse than a sharp one that recovers quickly.

Every other drawdown figure on this page's neighbours reports a **moment** — the worst one, or the current one. This one reports a **stretch of time**: it looks at the drawdown on every single observation and asks how much of the history was spent below a peak, and by how much.

---

## 🔢 Formula {: #formula }

The drawdown at observation $t$ is the distance from the highest value reached so far:

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

The Ulcer Index is the **root mean square** of that series over the $T$ observations:

$$
UI = \sqrt{\frac{1}{T} \sum_{t=1}^{T} DD_t^{2}}
$$

Three properties follow directly from that expression, before any interpretation is layered on top:

- It is **positive**. It is a dispersion built from a square root, and a square root cannot return a negative number. It is the one member of the drawdown family that is not reported as a fall.
- **Every observation counts**, including the ones sitting exactly at a peak. Those contribute $0$ to the sum but still occupy a slot in the divisor, which is what makes a long calm stretch pull the figure down.
- **Squaring is not neutral.** A drawdown twice as deep contributes four times as much, so the measure is dominated by the deep stretches rather than by the merely-below-peak ones.

---

## 📐 The Divisor That Looks Like Bessel's Correction {: #the-divisor }

This is the detail that trips up anyone recomputing the figure by hand, and it is worth stating precisely because the error it produces is small enough to survive a casual check.

!!! info "The series carries one more point than the history does"

    A drawdown series is derived from a wealth index that starts at a unit baseline, so it holds $T + 1$ points: the $T$ observed ones, plus that baseline. The baseline's drawdown is **always exactly zero** — a starting point cannot be below a peak it has not yet left.

    The standard reference implementation divides the sum of squares by $n - 1$, where the counter $n$ runs over the whole series and therefore **includes** that baseline. Since $n = T + 1$:

    $$
    \frac{1}{n - 1} = \frac{1}{(T + 1) - 1} = \frac{1}{T}
    $$

    The $-1$ is cancelling the phantom point, not applying a sample correction.

!!! warning "Reading it as a sample standard deviation overstates the result"

    The baseline contributes $0$ to the sum of squares and $+1$ to the count, and those two cancel exactly — which is why the expression collapses to a genuine mean over the $T$ real observations. Mistaking the $n - 1$ for Bessel's correction and dividing by $T - 1$ instead inflates the figure by

    $$
    \sqrt{\frac{T}{T - 1}}
    $$

    At $T = 750$ that is **+0.0667%**: far too small to look wrong, and still wrong. The Ulcer Index is a root-mean-square, not a sample standard deviation, and it has no mean to estimate.

---

## 🆚 Against the Maximum Drawdown {: #against-the-maximum-drawdown }

[Max Drawdown](max-drawdown.md) reports the worst moment. The Ulcer Index reports how much of the time was spent underwater, and how deep. They are built from the same series and they rank portfolios differently, which is the entire reason for publishing both.

| Two histories with the **same** Max Drawdown | Ulcer Index |
|---|---|
| One sharp fall, recovered within days | **small** — the deep observations are few, and the rest sit at a peak |
| A slow erosion that stays below the peak for months | **large** — most observations are underwater, and each one counts |

The relationship between the two is not merely qualitative. Since $DD_t^{2} \leq MDD^{2}$ for every $t$, the mean of the squares cannot exceed the largest of them:

$$
UI \leq |MDD|
$$

Equality would require the portfolio to sit at its deepest point for the entire window. The ratio $UI / |MDD|$ therefore reads as **how much of the history resembled the worst of it** — near $0$ for a single spike in an otherwise untroubled record, approaching $1$ for a portfolio that went down and stayed there.

---

## 💡 Interpretation {: #interpretation }

Read the figure as a *typical* depth rather than a worst one — duration-weighted, and expressed in the same units as the drawdowns it is built from.

- **Zero means never below a peak.** A portfolio that only ever made new highs has no drawdown series to speak of, and the index collapses to $0$. Any history containing a decline produces a strictly positive figure.
- **Lower is better**, which inverts the reading habit of the rest of the drawdown family. Here a bigger number is a worse experience, with no minus sign to signal it.
- **It reads the sequence, not the distribution.** Reshuffling the observed returns leaves [Value at Risk](value-at-risk.md) and [Conditional Value at Risk](conditional-value-at-risk.md) untouched, but it rebuilds the drawdown series from scratch and can move this figure a long way. It belongs to the path-dependent half of the section, alongside [Max Drawdown](max-drawdown.md) and [Current Drawdown](current-drawdown.md).

---

## ⚠️ Limitations {: #limitations }

!!! warning "A longer calm window lowers it"

    The divisor is the observation count, so extending a history with periods spent at a peak adds zeros to the numerator and slots to the denominator. The figure falls without anything about the portfolio's bad episodes having changed. Two Ulcer Indices are only comparable when they were computed over windows of comparable length and observation frequency.

!!! warning "It is not the fraction of time spent underwater"

    Squaring gives the deep stretches disproportionate weight, so the index is not a duration statistic wearing a percentage sign. A portfolio that spent half the window $2\%$ below its peak and one that spent an eighth of it $4\%$ below score identically, and neither figure tells you which shape produced it.

!!! warning "It carries no dates"

    The measure summarises the whole window into one number and says nothing about **when** the underwater periods occurred, or whether the portfolio is underwater now. [Current Drawdown](current-drawdown.md) answers the second question and [Max Drawdown](max-drawdown.md) dates the first.

---

## 🔗 Related {: #related }

- 📉 **[Max Drawdown](max-drawdown.md)** — the worst moment, against which this measures the whole stretch
- 📍 **[Current Drawdown](current-drawdown.md)** — where the portfolio stands against its peak today
- 📉 **[Drawdown at Risk](drawdown-at-risk.md)** — a quantile of the same drawdown series, rather than its root mean square
- 🌊 **[Conditional Drawdown at Risk](conditional-drawdown-at-risk.md)** — the severity of the drawdown tail beyond that quantile
- 📊 **[Volatility](volatility.md)** — dispersion of returns, which has no memory of the peak
- 🧪 **[Data Quality](data-quality.md)** — the window and observation count the series was built over
