# 📉 Drawdown at Risk

Drawdown at Risk applies the quantile idea to drawdowns rather than to returns: it is the drawdown depth that should not be exceeded at a chosen confidence level.

Everything [Value at Risk](value-at-risk.md) is, this is — with one substitution. Where that figure sorts the **losses** the portfolio suffered, this one sorts the **distances below a peak** it lived through. The narrowness is identical, and so is the trap: it marks where the drawdown tail begins, and is silent about everything past it.

---

## 🔢 Formula {: #formula }

The drawdown at observation $t$ is the distance from the highest value reached so far:

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

At confidence level $c$, writing $\alpha = 1 - c$ for the tail fraction, Drawdown at Risk is the $\alpha$-quantile of that series:

$$
DaR_c = \inf\left\{\, d : P(DD_t \leq d) \geq \alpha \,\right\}
$$

In practice that is an ordering exercise, exactly as it is for the Value at Risk: the drawdowns observed over the analysed window are sorted from deepest to shallowest, and the figure is read off at the position $\alpha T$ points to.

!!! info "Sign and reading"

    Drawdown at Risk is **non-positive** — zero or negative. A drawdown is a fall from a peak, so it cannot come out above zero, and a *deeper* figure is a *more negative* one. At 95% confidence the statement is: in 19 observations out of 20 the portfolio stood no further below its peak than this, and in the remaining one it stood further — by an amount this measure does not state.

    The $T$ here counts the observed points only. The baseline that a wealth index starts from carries a drawdown of exactly zero by construction, and the quantile family discards it before sorting, so it neither enters the ranking nor inflates the denominator. The [Ulcer Index](ulcer-index.md) keeps it, harmlessly, for a reason set out [on its own page](ulcer-index.md#the-divisor).

---

## 🎯 It Is an Order Statistic {: #it-is-an-order-statistic }

The figure is read off a sorted list, which fixes two of its properties in advance.

- **It can only report a depth the portfolio actually visited.** There is no interpolation and no assumed distribution; the number is one of the observations, selected by position. It cannot describe a drawdown the history never contained.
- **It is a step function of an index.** Between one position and the next it does not move at all, and when the position shifts it jumps by a whole observation. This is the same mechanism that makes the Value at Risk change in an all-or-nothing way, described under [what the correction changes](value-at-risk.md#what-the-correction-changes).

---

## 🔁 The Same Step That VaR Takes to CVaR {: #the-same-step-that-var-takes-to-cvar }

A quantile stops at the boundary. Two portfolios can report the same Drawdown at Risk while one exceeds it by a whisker and the other collapses far beyond it, and nothing in this figure distinguishes them. That silence is exactly what [Conditional Drawdown at Risk](conditional-drawdown-at-risk.md) fills.

| Reads the **loss** series | Reads the **drawdown** series | What it answers |
|---|---|---|
| [Value at Risk](value-at-risk.md) | **Drawdown at Risk** | Where does the tail begin? |
| [Conditional Value at Risk](conditional-value-at-risk.md) | [Conditional Drawdown at Risk](conditional-drawdown-at-risk.md) | How deep does it go once it begins? |

Reading the columns downward gives the two threshold-and-severity pairs; reading the rows across gives the same question asked of a distribution and of a path. A complete picture needs all four, and the pair on the right is the one that knows the portfolio had a peak to fall from.

---

## 💡 Interpretation {: #interpretation }

Read it as *how far below the peak a bad day typically finds you*, never as a floor.

- **It is a threshold, not a bound.** Deeper drawdowns are not excluded — they are, by construction, expected at the stated rate.
- **The confidence level changes the question, not the precision.** Moving from 95% to 99% asks about a rarer stretch, estimated from fewer observations, not about the same stretch measured better.
- **It is not the Max Drawdown.** [Max Drawdown](max-drawdown.md) is the single deepest point in the window; this is the level that a chosen fraction of the window went past. The two coincide only in the limit where the tail contains one observation.

---

## ⚠️ Limitations {: #limitations }

!!! warning "Silent beyond the threshold"

    The measure stops at the boundary of the drawdown tail. Whether the falls past it are slightly deeper or catastrophically deeper is information it does not carry, and no confidence level recovers it. Use [Conditional Drawdown at Risk](conditional-drawdown-at-risk.md) for the depth.

!!! warning "Drawdown observations are not independent of one another"

    Consecutive observations inside the same episode are nearly the same number: a portfolio underwater on Tuesday is almost certainly underwater on Wednesday. The tail of a drawdown series is therefore rarely $\alpha T$ separate events — it is more often a handful of episodes, or one long one, counted day by day.

    This makes the figure less stable than its observation count suggests, and it means a single prolonged decline can furnish the entire tail on its own.

!!! warning "It inherits its window"

    An empirical quantile is bounded by the history it is drawn from. A window with no severe episode yields a shallow Drawdown at Risk — not because the portfolio is safe, but because nothing worse has been observed yet. A [Historical Replay](historical-replay.md) or a [Hypothetical Shock](hypothetical-shock.md) is how a scenario outside the window enters the analysis.

---

## 🔗 Related {: #related }

- 🌊 **[Conditional Drawdown at Risk](conditional-drawdown-at-risk.md)** — how deep the drawdown tail goes past this threshold
- 📉 **[Value at Risk](value-at-risk.md)** — the same quantile construction, applied to losses instead of drawdowns
- 🌊 **[Conditional Value at Risk](conditional-value-at-risk.md)** — the severity counterpart on the loss series
- 📉 **[Max Drawdown](max-drawdown.md)** — the single deepest fall, rather than a rate
- 🩹 **[Ulcer Index](ulcer-index.md)** — the whole drawdown series in one number, without a confidence level
- 🧪 **[Data Quality](data-quality.md)** — the window and observation count the quantile was read from
