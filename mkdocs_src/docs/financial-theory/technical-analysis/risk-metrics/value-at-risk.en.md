# 📉 Value at Risk

Value at Risk answers a deliberately narrow question: over a given horizon and at a chosen confidence level, what is the loss that should not be exceeded?

The narrowness is the point, and it is also the trap. VaR marks **where the tail begins** — it is a threshold, not a maximum, and it is silent about everything past it.

---

## 🔢 Formula {: #formula }

At confidence level $c$, Value at Risk is the quantile of the loss distribution:

$$
VaR_c = \inf\left\{\, \ell : P(L \le \ell) \ge c \,\right\}
$$

In practice that is an ordering exercise: the losses observed over the analysed window are sorted, and the figure is read off at the position the confidence level points to.

The result is a **frequency statement**. At 95%, it says that in 19 periods out of 20 the loss is no worse than the figure reported — and that in the remaining one it is worse, by an amount this measure does not state.

---

## 📜 Measured, Not Modelled {: #measured-not-modelled }

LibreFolio's Value at Risk is **historical**: it is the empirical quantile of the losses the portfolio actually experienced. There is no assumed distribution anywhere in it.

That is a deliberate choice against the most common alternative, in which returns are assumed to be normally distributed and the quantile is read from that curve.

!!! warning "The Gaussian assumption fails exactly when the number matters"

    Real market returns have **fatter tails** than a normal distribution: extreme moves occur more often, and are larger, than the bell curve allows for. A parametric Gaussian VaR therefore promises that the worst days are rarer than they are — and it makes that promise most confidently at the high confidence levels, which are precisely the ones used to think about crises.

    It is a measure of risk that is reassuring in proportion to how wrong it is. The empirical approach cannot make that error, because it never claims a shape: it counts what happened.

The advantage is earned, not free, and the price is on the same page as the benefit:

!!! warning "It cannot show you a loss you have never lived"

    An empirical quantile is bounded by the sample it is drawn from. A short history, or a calm one, produces a calm Value at Risk — not because the portfolio is safe, but because nothing worse has been observed yet. The measure describes the window it was given, and a window that contains no crisis contains no crisis-sized losses.

---

## 💡 Interpretation {: #interpretation }

Read the figure as *how often*, never as *how much at worst*:

- **It is a threshold, not a bound.** Losses beyond it are not excluded — they are, by construction, expected to occur at the stated rate.
- **It says nothing about the depth beyond.** Two portfolios can report the same VaR while one exceeds it modestly and the other catastrophically. That difference is what [Conditional Value at Risk](conditional-value-at-risk.md) is for, and it is the reason this section leads with that figure rather than this one.
- **It is a rate, not a schedule.** "One period in twenty" does not mean one bad period every twenty. Bad periods arrive in clusters, and a quantile has no memory of order.

That last property is worth stating precisely, because it separates this measure from half the section: **shuffle the order of the observed returns and the Value at Risk does not move at all.** It reads the distribution, not the sequence. The figures that read the sequence — [Max Drawdown](max-drawdown.md) and [Current Drawdown](current-drawdown.md) — can change completely under the same shuffle. Neither view is complete alone, which is why both are published.

The least favourable single observation in the window is reported as its own figure, [Worst Realization](worst-realization.md): where Value at Risk says *one period in twenty goes worse than this*, that one says *and the worst was this, on this date*.

---

## 🔄 What the Tail-Estimator Correction Changes Here {: #what-the-correction-changes }

The tail average used by [Conditional Value at Risk](conditional-value-at-risk.md) has been corrected, and the natural question is whether the Value at Risk figure moves with it.

It does for some configurations and not for others, and the boundary between the two is exact. Which side a given figure falls on is decided by arithmetic, not by inspection, so it can be checked rather than assumed.

!!! info "The condition, in full"

    The reported Value at Risk changes **exactly when $(1-c) \cdot T$ is a whole number**, where $c$ is the confidence level and $T$ is the number of observations entering the tail calculation.

    When that product is not a whole number, both conventions select the same observation and the figure is not merely close but identical.

### 🎚️ Why the Change Is All or Nothing {: #why-the-change-is-all-or-nothing }

A measurement study across 24 combinations of confidence level and history length, 300 samples each — 7,200 trials — found that every combination was one in which **either every sample moved or none did**. No combination produced an intermediate proportion.

That follows from what the figure is. Value at Risk here is an **order statistic**: the calculation sorts the observed losses and reads off the one at the position the confidence level points to, so the number reported is always a loss the portfolio actually experienced. It is a step function of an index, not a continuous function of the data.

When the condition above is met, the index shifts by one position — and an index that shifts does not shift a little. It selects a **different observation**. The figure therefore jumps by one whole order statistic, and the largest such jump measured was **+4.587%**. Between whole numbers the two conventions round to the same index and the output is bit-identical.

!!! info "Where the figure moves, it moves upward"

    This figure and [Conditional Value at Risk](conditional-value-at-risk.md) both move in the same direction: up. No configuration was found in which either number moved towards a more optimistic reading. Where a Value at Risk changed, the risk previously reported was **too low**.

### 📅 Which Histories Are Affected {: #which-histories-are-affected }

$(1-c) \cdot T$ is a whole number when $T$ is divisible by 10 at 90% confidence, by 20 at 95%, and by 100 at 99%:

| Observations $T$ | 90% | 95% | 99% |
|---|---|---|---|
| 250 | moves | — | — |
| 500 | moves | moves | moves |
| 750 | moves | — | — |
| 1000 | moves | moves | moves |
| 1003 | — | — | — |
| 2000 | moves | moves | moves |

The pattern in that table deserves naming, because it is the opposite of a rare edge case: **the affected histories are the tidy ones**. One year, two years, three years, a thousand days — the round numbers are precisely the divisible numbers, and round numbers are what an interface invites you to type. A history of 1,003 observations, by contrast, is affected at no confidence level at all.

This is the fact that answers the question the correction usually provokes — **why one analysis changed and a colleague's did not**. Two analyses of the same portfolio at the same confidence level can disagree about whether anything happened, because one was run over a round window and the other was not. Neither is wrong, and the difference between them is not a matter of degree: it is the divisibility of a single integer.

### ⏳ The Observation Count Is Not the History Length {: #the-observation-count-is-not-the-history-length }

$T$ is not the number of days in the window. The tail is computed from **horizon-compounded** returns — every run of $n$ consecutive returns compounded into one — so the number of values entering the calculation is

$$
T = N - n + 1
$$

where $N$ is the number of returns in the window and $n$ is the horizon counted in observations. The **Horizon (days)** parameter $h$ is in **calendar days**, and it is converted into observations at the rate the series was actually observed — its [observed annualization factor](observed-annualization.md) $f$:

$$
n = \max\left(1,\ \operatorname{round}\left(\frac{h \cdot f}{365}\right)\right)
$$

A horizon therefore spans the same stretch of calendar on every series, to the nearest observation. Thirty days — the bad month the app reports beside the bad day — are $n = 21$ observations of a series quoted on trading days ($f \approx 252$) and $n = 30$ of one quoted every calendar day ($f = 365$).

The analytic computes exactly these quantities and publishes both with the result: $n$ as its horizon in observations, $T$ as its observation count. That published count, not the window length, is the $T$ the rule applies to. It is also the count the minimum of 20 observations is checked against: with fewer than 20 compounded windows the figure is not computed, and the result comes back unavailable for insufficient history. A bad month therefore needs $N \ge 40$ returns at $f \approx 252$, where $n = 21$, and $N \ge 49$ at $f = 365$.

Horizon is a form field on the analytic, defaulting to $h = 1$ and accepting values from 1 to 365. At the default $n = 1$ on every series — none is observed more than once per calendar day, so $f \le 365$ — and $T = N$, which is why round histories are the affected ones.

Raise it and the table above inverts. At $h = 10$, a series quoted on trading days compounds $n = 7$ observations, so a round $N$ yields $T = N - 6$, a number ending in 4; a series quoted every calendar day compounds $n = 10$, and $T = N - 9$ ends in 1. Neither is ever divisible by 10, 20 or 100, and the same holds on any series observed at least 54.75 times a year ($f \ge 54.75$): ten days then hold between 2 and 10 observations, so a round $N$ loses between 1 and 9 of them. Across the same history lengths, at $h = 10$ **250, 500, 750, 1000, 1250 and 2000 observations are unaffected at all three confidence levels**, on either kind of series. The default horizon of 1 is precisely the setting under which tidy histories move; a horizon of 10 leaves those same histories untouched — except on a series observed less often, such as a weekly fund ($f \approx 52$), where ten days still round to a single observation and $T = N$. This is a consequence of the arithmetic rather than a defect in it, but it does mean a comparison between two analyses has to match the horizon as well as the window and the level — and, since the same horizon holds a different $n$ at a different $f$, the observed frequency of the series too.

!!! info "How to check a particular case"

    Take the observation count the Value at Risk publishes with its figures — `observations`, already net of the horizon and published next to `horizon_observations` — and multiply it by $1 - c$. A whole number means the figure moved, by one observation; anything else means it is unchanged. The observation count in the result's metadata (`n_observations`, see [Data Quality](data-quality.md)) is $N$, counted before compounding: it equals $T$ only when $n = 1$.

---

## ⚠️ Limitations {: #limitations }

!!! warning "Silent beyond the threshold"

    The measure stops at the boundary of the tail. Whether the losses past it are slightly worse or many times worse is information it does not carry, and no confidence level recovers it. Use [Conditional Value at Risk](conditional-value-at-risk.md) for the depth.

!!! warning "The confidence level changes the question, not the precision"

    Moving from 95% to 99% does not produce a more accurate answer; it asks about a rarer event. It also asks about one estimated from fewer observations, so the higher level is read from a thinner slice of the same history.

!!! warning "It inherits its window"

    The figure is computed from the returns of the analysed period, over the observation calendar those series share. The window, the observation count and the basis used are published with the result — see [Data Quality](data-quality.md).

---

## 🔗 Related {: #related }

- 🌊 **[Conditional Value at Risk](conditional-value-at-risk.md)** — how deep the tail goes once the threshold is passed
- 📉 **[Max Drawdown](max-drawdown.md)** — the worst fall along the path, which a quantile cannot see
- 📊 **[Volatility](volatility.md)** — dispersion as a whole, rather than one point of the distribution
- ⏮️ **[Historical Replay](historical-replay.md)** — a specific episode instead of a summary statistic
- 🔻 **[Worst Realization](worst-realization.md)** — the deepest single observation, as a dated fact rather than a rate
- 🧪 **[Data Quality](data-quality.md)** — the window and observations the quantile was read from
