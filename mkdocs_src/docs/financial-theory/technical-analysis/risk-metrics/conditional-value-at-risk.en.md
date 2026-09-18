# 🌊 Conditional Value at Risk

Conditional Value at Risk takes over exactly where Value at Risk stops: it measures the average loss in the cases where the Value at Risk threshold was in fact breached.

[Value at Risk](value-at-risk.md) says **where the tail begins**. This says **how deep it goes**. That is the whole difference, and it is why this is the figure the section leads with.

---

## 🔢 Formula {: #formula }

At confidence level $c$, Conditional Value at Risk is the expected loss **given** that the loss exceeded the Value at Risk:

$$
CVaR_c = E\left[\, L \mid L \ge VaR_c \,\right]
$$

Empirically, it is the average of the losses in the tail beyond the threshold — the mean of the bad cases, rather than the boundary of the bad cases.

Because it averages a region instead of reading a point, it carries information the quantile cannot: two portfolios with the **same** Value at Risk can have very different Conditional Values at Risk, one exceeding the threshold by a little and the other by a great deal. Nothing about the first figure distinguishes them; this one does.

!!! tip "It also rewards diversification consistently"

    There is a second, more technical reason risk practice moved towards tail averages. A quantile can behave perversely when portfolios are combined: it is possible for the Value at Risk of a combined portfolio to exceed the sum of the Values at Risk of its parts, which would say that diversifying increased risk. An average over the tail does not have that defect, which makes it the better-behaved figure when risk is compared across compositions.

---

## 🔬 How the Tail Average Is Taken {: #how-the-tail-average-is-taken }

The tail rarely contains a whole number of observations. At 95% confidence over a few hundred periods, the boundary of the tail falls **between** two observed losses, and the observation sitting on that boundary belongs to the tail only in part.

The average therefore weights that boundary observation by the fraction of it that actually lies beyond the threshold, instead of counting every tail observation equally. Treating a partially-included observation as fully included pulls the average towards the boundary — that is, towards the least severe loss in the tail — and therefore reports a tail that is shallower than it is.

---

## 📐 The Correction, and What It Does to Your Number {: #the-correction }

This is a change to a number you may already have seen. The earlier estimator took a **uniform** average over the tail; the current one applies the fractional weighting described above.

!!! warning "The new figure is not merely different — it is less optimistic"

    The correction moves the Conditional Value at Risk **upward at every confidence level**, in every sample of a measurement study of 2,000 simulated series of 750 observations each: 2,000 out of 2,000, without a single exception in either direction.

    That direction is the point. The previous figure was **understating the tail**: it reported the average bad case as milder than the data said. A user who sees this number rise is not seeing a new methodology produce an arbitrary difference — they are seeing an optimistic estimate replaced by an accurate one.

| Confidence | Measured change (median) | Largest change observed | Samples that moved upward |
|---|---|---|---|
| 90% | +0.364% | +0.476% | 2,000 / 2,000 |
| 95% | +0.267% | +0.404% | 2,000 / 2,000 |
| 99% | +0.727% | +1.748% | 2,000 / 2,000 |

**The shift grows with the confidence level**, and the reason follows from the mechanism: the higher the level, the fewer observations lie in the tail, so the single partially-included one carries a larger share of the average. At 99% a handful of observations decide the figure, and mis-weighting one of them moves the result more than it would at 90%.

!!! info "The corrected figure matches the reference implementation"

    Measured against the standard reference implementation of the same estimator, the remaining difference is $-4.27 \times 10^{-18}$ — floating-point rounding noise, not a methodological gap. The two now compute the same quantity.

The threshold figure moves too, though under a far narrower condition: the [Value at Risk](value-at-risk.md) reported alongside this one changes only when the observation count is divisible in the way the confidence level requires, and where it does change it jumps by a whole observation rather than drifting slightly. The rule, and how to check a particular case, is set out under [what the correction changes](value-at-risk.md#what-the-correction-changes). The two are distinct changes that happen to arrive together: this one is to how the tail is averaged, not to where the tail starts.

---

## 💡 Interpretation {: #interpretation }

Read this figure as *how bad it gets when it goes bad* — the average outcome across the worst cases in the window, not the worst of them.

- It is always at least as severe as the Value at Risk at the same level, because it averages values that are all beyond that threshold.
- The gap between the two is itself informative: a Conditional Value at Risk far above its Value at Risk describes a portfolio whose bad cases, when they arrive, are much worse than the threshold suggests.
- Like the quantile it extends, it reads the **distribution** and not the sequence: reshuffling the order of the observed returns leaves it unchanged. The path-dependent view belongs to [Max Drawdown](max-drawdown.md) and [Current Drawdown](current-drawdown.md), and a complete picture needs both.

---

## ⚠️ Limitations {: #limitations }

!!! warning "The tail is estimated from few observations"

    By definition, only a small fraction of the window lies beyond the threshold, and at 99% that fraction is very small. The figure is therefore the least stable of the distributional measures: it can shift noticeably as new observations arrive, and two adjacent windows can disagree more than their length difference suggests.

!!! warning "It is still bounded by the history it was given"

    Averaging the tail does not conjure losses the portfolio never experienced. If the window contains no severe episode, the tail it averages is a mild one — the measure will report honestly on a history that simply has not been tested. A [Historical Replay](historical-replay.md) or a [Hypothetical Shock](hypothetical-shock.md) is how a scenario outside the window enters the analysis.

!!! warning "It describes severity, not likelihood"

    The figure is conditional on the tail being reached. It says nothing about how probable that is beyond the confidence level that defined it, and nothing about when — bad periods cluster, and no distributional summary carries that.

---

## 🔗 Related {: #related }

- 📉 **[Value at Risk](value-at-risk.md)** — the threshold this figure averages beyond
- 📉 **[Max Drawdown](max-drawdown.md)** — the worst cumulative fall along the path
- 📊 **[Volatility](volatility.md)** — dispersion in both directions, rather than the loss tail alone
- ⚡ **[Hypothetical Shock](hypothetical-shock.md)** — a scenario the observed history never contained
- 🧪 **[Data Quality](data-quality.md)** — the window the tail was drawn from
