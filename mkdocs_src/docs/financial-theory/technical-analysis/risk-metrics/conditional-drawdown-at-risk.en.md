# 🌊 Conditional Drawdown at Risk

Conditional Drawdown at Risk averages the drawdowns that did breach the Drawdown at Risk threshold, answering how deep the fall goes once it goes past that point.

[Drawdown at Risk](drawdown-at-risk.md) says **where the drawdown tail begins**. This says **how deep it goes** — the same step [Conditional Value at Risk](conditional-value-at-risk.md) takes beyond [Value at Risk](value-at-risk.md), taken on the drawdown series instead of the loss series.

The word *averages* in that opening sentence is doing more work than it looks. It is a **weighted** average, and the weight is fixed by the confidence level rather than by how many observations happen to land in the tail. That distinction is the subject of most of this page, because the shortcut it rules out is a plausible one.

---

## 🔢 Formula {: #formula }

At confidence level $c$, writing $\alpha = 1 - c$ for the tail fraction, the measure takes the **Rockafellar–Uryasev** form:

$$
CDaR_c = DaR_c - \frac{1}{\alpha T} \sum_{t=1}^{T} \left( DaR_c - DD_t \right)^{+}
$$

where $(x)^{+} = \max(x, 0)$, $DD_t$ is the drawdown at observation $t$, and $T$ is the number of observed points in the series.

The sum collects the **excess severity**: for every observation deeper than the threshold, how much deeper. Every observation shallower than the threshold contributes nothing. That total is then spread over $\alpha T$ and subtracted from the threshold, which drives the result further below zero than the Drawdown at Risk it starts from.

Like the threshold it extends, Conditional Drawdown at Risk is **non-positive** — a drawdown is a fall from a peak, and averaging falls does not produce a rise. It is always at least as severe as the Drawdown at Risk at the same confidence level, because every quantity it adds to that threshold is a fall beyond it.

---

## 🔬 It Is Not the Average of the Worst Observations {: #it-is-not-the-average-of-the-worst-observations }

The intuitive recipe — take the $k$ deepest drawdowns and average them — is not this formula, and the difference is in the denominator.

The normalisation above is $\alpha T$: a **fixed** quantity determined by the confidence level and the history length. The tail count $k$ is a different quantity — the number of observations that actually landed beyond the threshold, which can only be a whole number. When $\alpha T$ is not whole, the tail necessarily contains **more** observations than $\alpha T$, and dividing the same total severity by that larger count produces a shallower figure.

!!! warning "The shortcut understates the tail"

    Averaging over the tail count instead of over $\alpha T$ reports the average bad case as **milder** than the data says. The two forms coincide **exactly** when $\alpha T$ is a whole number, and the shortcut is too optimistic whenever it is not.

    | Observations $T$ | $\alpha T$ at 95% | Whole number? | Relative difference |
    |---|---|---|---|
    | 740 | 37.00 | yes | **0.00000%** |
    | 745 | 37.25 | no | $-0.03817\%$ |
    | 750 | 37.50 | no | $-0.02528\%$ |
    | 760 | 38.00 | yes | **0.00000%** |
    | 800 | 40.00 | yes | **0.00000%** |
    | 1000 | 50.00 | yes | **0.00000%** |

    The gaps are fractions of a percent. That is precisely what makes the shortcut durable: a figure wrong by three hundredths of a percent looks like rounding, not like a different formula.

---

## 🪤 The Same Trap, in the Opposite Sense {: #the-same-trap-in-the-opposite-sense }

This is the same shape of mistake the [Conditional Value at Risk](conditional-value-at-risk.md) page describes for the loss tail: a plausible uniform average, wrong by a fraction of a percent, in the same direction — understating the tail. And it is governed by the **same arithmetic quantity**, $(1 - c) \cdot T$, that the [Value at Risk](value-at-risk.md#what-the-correction-changes) page already sets out.

!!! warning "The same quantity, the opposite meaning — do not carry one rule over to the other"

    A whole $(1 - c) \cdot T$ means opposite things on the two pages, and the two statements are easy to blur into one.

    | Measure | When $(1 - c) \cdot T$ is a whole number |
    |---|---|
    | [Value at Risk](value-at-risk.md#what-the-correction-changes) | the two conventions **diverge** — the figure moves by a whole observation |
    | **Conditional Drawdown at Risk** | the shortcut **happens to be right** — the two forms agree exactly |

    Divisibility is the condition in both cases; it just selects disagreement in one and agreement in the other.

---

## 🔍 Checking the Figure Yourself {: #checking-the-figure-yourself }

Because a whole $\alpha T$ is exactly where the shortcut is indistinguishable from the correct form, the choice of history length decides whether a hand check can detect the difference at all.

!!! warning "A round history length cannot tell the two forms apart"

    | Observations $T$ | 90% | 95% | 99% |
    |---|---|---|---|
    | 250 | blind | sees | sees |
    | 500 | **blind** | **blind** | **blind** |
    | 750 | blind | sees | sees |
    | 1000 | **blind** | **blind** | **blind** |
    | 1003 | sees | sees | sees |
    | 2000 | **blind** | **blind** | **blind** |

    **500, 1,000 and 2,000 observations are blind at every confidence level; 1,003 detects at every level.**

    The pattern is not a rare edge case — it is the opposite. $\alpha T$ is whole when $T$ is divisible by 10 at 90% confidence, by 20 at 95%, and by 100 at 99%, and the round numbers are precisely the divisible ones. Two years, a thousand days, five hundred sessions: the window lengths anyone reaches for first are the ones where the two forms return the same number.

!!! tip "So choose an untidy window"

    If you want to verify the figure by recomputing it, pick a history length that is **not** a round multiple of 10, 20 or 100 — 1,003 observations rather than 1,000. At a divisible length the two candidate formulas agree to the last digit, so a match tells you nothing about which one produced it.

---

## 💡 Interpretation {: #interpretation }

Read it as *how far below the peak things go once they go past the threshold* — the severity of the drawdown tail, not its boundary.

- **The gap from the threshold is informative.** A Conditional Drawdown at Risk far below its Drawdown at Risk describes a portfolio whose bad stretches, once they start, run much deeper than the threshold suggests.
- **It is a depth, not a duration.** It says how deep the tail of the drawdown distribution runs, and nothing about how long the portfolio stayed there. [Ulcer Index](ulcer-index.md) is the figure that folds duration in.
- **It reads a path-dependent series.** Unlike the loss-based pair, this measure and its threshold are computed from drawdowns, which depend on the order in which returns arrived. Reshuffling the history rebuilds them both.

---

## ⚠️ Limitations {: #limitations }

!!! warning "The tail is estimated from few observations"

    Only a small fraction of the window lies beyond the threshold, and at 99% that fraction is very small. The figure is correspondingly unstable: it can shift noticeably as observations arrive, and two adjacent windows can disagree more than their length difference suggests.

!!! warning "Those few observations are not independent"

    Drawdowns inside one episode are nearly the same number day after day, so the tail is often a single prolonged decline counted many times rather than $\alpha T$ separate events. The measure averages observations, not episodes, and a history with one bad year can put that year in the tail on its own.

!!! warning "It is bounded by the history it was given"

    Averaging the drawdown tail does not conjure declines the portfolio never lived through. A window containing no severe episode yields a mild tail, honestly reported. A [Historical Replay](historical-replay.md) or a [Hypothetical Shock](hypothetical-shock.md) is how a scenario outside the window enters the analysis.

---

## 🔗 Related {: #related }

- 📉 **[Drawdown at Risk](drawdown-at-risk.md)** — the threshold this figure averages beyond
- 🌊 **[Conditional Value at Risk](conditional-value-at-risk.md)** — the same severity step, taken on the loss series
- 📉 **[Value at Risk](value-at-risk.md)** — where the divisibility rule is set out in full
- 📉 **[Max Drawdown](max-drawdown.md)** — the single deepest fall, rather than an average over the tail
- 🩹 **[Ulcer Index](ulcer-index.md)** — depth and duration together, without a confidence level
- 🧪 **[Data Quality](data-quality.md)** — the window and observation count the tail was drawn from
