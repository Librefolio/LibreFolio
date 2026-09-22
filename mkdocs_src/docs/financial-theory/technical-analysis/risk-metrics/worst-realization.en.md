# 🔻 Worst Realization

Worst realization is simply the least favourable single-period return actually observed in the available history — an observed fact rather than an estimate.

Every other figure in this section is computed *from* the observations. This one **is** one of them.

---

## 🔢 What It Is {: #what-it-is }

Given the returns of the analysed window, the worst realization is their minimum:

$$
WR = \min_t \; r_t
$$

There is no confidence level to choose, no distribution to assume, no averaging. The figure is a return that happened, and it comes with **the date it happened on** — which is what separates it from every parameter on the surrounding pages. A date can be looked up. It anchors the number to an event the portfolio actually went through, rather than to a statistical construction.

---

## 🆚 Against Value at Risk {: #against-value-at-risk }

The natural companion is [Value at Risk](value-at-risk.md), and the pair works by **contrast** rather than repetition:

| | Says | Nature |
|---|---|---|
| Value at Risk | *One period in twenty goes worse than this* | A threshold, estimated |
| Worst realization | *And the worst one was this, on this date* | A single point, observed |

Value at Risk describes a **rate** and is silent about magnitude beyond the threshold. Worst realization describes a **magnitude** and is silent about rate — it happened once, and the figure says nothing about how likely a repeat is. [Conditional Value at Risk](conditional-value-at-risk.md) sits between them, averaging the whole tail rather than reading its boundary or its extreme.

Together they bracket the tail: where it begins, how deep it runs on average, and the deepest single step recorded.

---

## 🧭 Distribution or Path {: #distribution-or-path }

Metrics labelled *risk* fall into two families that answer different questions, and nothing in a row of eight numbers signals which is which.

!!! info "Shuffle the returns, and see what moves"

    **Shuffle the order of a portfolio's returns and the Value at Risk does not change by a comma — while the maximum drawdown can double.**

    Value at Risk, Conditional Value at Risk and worst realization read the **distribution**: which returns occurred, in any order. [Max Drawdown](max-drawdown.md), [Current Drawdown](current-drawdown.md) and the durations attached to them read the **path**: the order in which they arrived.

Worst realization belongs firmly to the distribution family, and the distinction is not academic. It answers *how bad can a single period be?* — while a portfolio is not destroyed by one bad day but by a **sequence** of them. Three consecutive losses of 5% do more damage than one isolated loss of 12%, and only the path-reading family can tell them apart.

Reading a distributional figure as if it described the worst experience available is the mistake this section is arranged to prevent.

---

## 💡 Interpretation {: #interpretation }

Use it as a reality check on the estimated figures. A Value at Risk far milder than the worst realization is not a contradiction — the quantile is meant to be exceeded sometimes, and this is what exceeding it looked like at its most extreme.

The date matters as much as the value. A worst realization from a well-known market event reads differently from one on an unremarkable day, which often points at something specific to the portfolio: a single holding, a corporate action, or a pricing artefact worth checking in [Data Quality](data-quality.md).

---

## ⚠️ Limitations {: #limitations }

!!! warning "It is an extremum, so the window can only make it worse"

    Lengthening the analysed period can never improve this figure and can only worsen it: a longer window contains every observation the shorter one did, plus more chances to find something worse. Comparing worst realizations across portfolios is therefore meaningless unless they were measured over the same window — a longer history will usually look worse for that reason alone.

!!! warning "One observation carries no frequency"

    The figure rests on a single period. It says nothing about how often such a period occurs, whether anything close to it happened more than once, or how the rest of the tail behaved. For the shape of the tail rather than its extreme, use [Conditional Value at Risk](conditional-value-at-risk.md).

!!! warning "It depends on the length of a period"

    A worst day, a worst week and a worst month are different quantities, and they do not convert into one another. The figure is tied to the observation frequency of the series it was read from — see [Observed Annualization](observed-annualization.md) for how that frequency is established.

---

## 🔗 Related {: #related }

- 📉 **[Value at Risk](value-at-risk.md)** — where the tail begins, as a rate rather than a fact
- 🌊 **[Conditional Value at Risk](conditional-value-at-risk.md)** — the average depth of the tail this figure sits at the end of
- 📉 **[Max Drawdown](max-drawdown.md)** — the worst cumulative fall, which reads the path instead of the distribution
- 📊 **[Volatility](volatility.md)** — typical dispersion, against which an extreme can be judged
- 🧪 **[Data Quality](data-quality.md)** — the window and the series the minimum was taken over
