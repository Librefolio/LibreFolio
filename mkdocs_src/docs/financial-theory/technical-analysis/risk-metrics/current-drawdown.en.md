# 📍 Current Drawdown

Current drawdown measures how far below its own historical peak a portfolio stands **right now**, as opposed to the worst fall it ever suffered. [Max Drawdown](max-drawdown.md) reports a fact about the past; this figure reports a position in the present, and it is the one that changes with every new observation.

---

## 🔢 Formula {: #formula }

Both drawdown figures are read from the same underwater series. A wealth index is built from the analysed returns, a running peak is carried forward, and the drawdown at each point is the distance between the two:

$$
DD_t = \frac{W_t}{\displaystyle\max_{\tau \le t} W_\tau} - 1
$$

The current drawdown is the value of that series at the **last** observation, never above zero:

$$
DD_{current} = \min\left(0,\; DD_{last}\right)
$$

At a new high-water mark the last wealth value *is* the running peak, so the ratio is $1$ and the drawdown is exactly $0$.

!!! info "Underwater is decided with a tolerance"

    A portfolio counts as underwater only when the current drawdown is negative **beyond a numerical tolerance**, not at every fraction of a cent below the peak. The tolerance exists to absorb floating-point noise, so that a value indistinguishable from the peak is treated as being at the peak. It is a guard against arithmetic artefacts, not a user-facing threshold below which a decline stops mattering.

---

## 📅 What Is Published {: #what-is-published }

Four quantities describe the present position. Their behaviour when the portfolio is **not** underwater is part of the contract, not an accident.

| Quantity | Meaning | At a high-water mark |
|---|---|---|
| Current drawdown | Distance below the running peak, as a decimal ratio, never positive | Exactly $0$ |
| Current peak date | The date of the **running** peak the drawdown is measured from | The latest observation date |
| Current drawdown duration | Calendar days elapsed **since that peak** | Exactly $0$ |
| Remaining to peak | The gain still required, on the current value, to return to the peak | Exactly $0$ |

Two of these deserve to be read carefully.

**The duration is counted from the peak, not from the low point.** This is the same convention the maximum drawdown uses for its duration: the clock starts when the portfolio leaves its high-water mark, not when it stops falling. The decline is not a prelude to the loss — it is the loss happening — so the count covers the whole stretch spent below the peak. See [Recovery Time](max-drawdown.md#recovery-time) for the same reasoning applied to the worst episode.

**The current peak date is not the peak of the worst episode.** It is the most recent high-water mark, which the running peak moves forward every time the portfolio sets a new one. A portfolio at an all-time high therefore reports today's date and a zero-length drawdown; the peak that preceded the deepest historical fall belongs to [Max Drawdown](max-drawdown.md) and is published separately.

---

## 🧗 What It Takes to Get Back {: #what-it-takes-to-get-back }

The gain required to return to the peak is not the mirror image of the fall, because the gain applies to a smaller base. Written from the current drawdown $DD$:

$$
\text{Required gain} = \frac{1}{1 + DD} - 1 = \frac{-DD}{1 + DD}
$$

The two forms are the same expression — the second is the first with the fraction combined — and [Max Drawdown](max-drawdown.md) explains the asymmetry this creates, with the worked values.

!!! warning "The same formula, applied to a different question"

    That asymmetry is a general lesson, and it is taught on the maximum drawdown page. The quantity computed here applies it to the **current** drawdown instead, and the difference is not cosmetic:

    - applied to the **maximum**, it is a historical statement — *how much it would have taken to recover, at the worst point ever reached*;
    - applied to the **current** drawdown, it is a present one — *how much it takes to recover from where the portfolio stands today*.

    Only the second can be acted on. A portfolio that fell steeply years ago and has since recovered carries a large maximum and a near-zero current figure at the same time: these are not two numbers in disagreement, they are answers to two different questions, and both are true.

---

## 💡 Interpretation {: #interpretation }

The current drawdown answers *where am I, relative to my own best result?* — a question no return figure answers, because a return measures a journey between two chosen dates while this measures a distance from a peak the portfolio itself set.

Read together, the four quantities describe a position rather than a score: **how far** below the peak, **since when**, and **how much** is still missing. The duration is often the more revealing of the two: a modest decline that has persisted for a long time is a different experience from a deeper one that opened last week, and the depth alone cannot tell them apart. That combination of depth and persistence is what the [Ulcer Index](ulcer-index.md) sets out to summarise in a single number.

Because it is measured against the running peak, the figure has a built-in asymmetry of its own: it improves as the portfolio rises and resets to zero the moment a new peak is set, however slightly that peak is exceeded.

---

## ⚠️ Limitations {: #limitations }

!!! warning "It is a position, not a forecast"

    The current drawdown says how far below the peak the portfolio is, and nothing about what happens next. It does not indicate whether the decline is ending, continuing or about to deepen, and the remaining-to-peak figure is arithmetic — the gain required to close the gap — not an expectation that the gain will arrive.

!!! warning "A new peak erases the memory"

    The running peak only moves upward, so exceeding the previous high by any margin resets the current drawdown to zero and restarts the duration from that date. The fall that preceded it does not disappear from the analysis, but it stops being described by *this* figure: it belongs to the maximum drawdown and to the episode history.

!!! warning "It inherits the series it was computed on"

    The underwater series is built from the same returns as the rest of the analysis, over the same observation window. A shorter window can only contain the peaks it saw: a portfolio analysed over a recent window may appear near its high simply because the higher peak lies before the start date. Each result publishes the window it used, its observation count, and the basis the returns were computed on. See [Data Quality](data-quality.md).

---

## 🔗 Related {: #related }

- 📉 **[Max Drawdown](max-drawdown.md)** — the worst fall in the record, its duration and its recovery state
- 🩹 **[Ulcer Index](ulcer-index.md)** — depth and persistence combined into one figure
- 📊 **[Volatility](volatility.md)** — how much the portfolio fluctuates, independently of any peak
- 🧪 **[Data Quality](data-quality.md)** — the window and the observations the drawdown was read from
