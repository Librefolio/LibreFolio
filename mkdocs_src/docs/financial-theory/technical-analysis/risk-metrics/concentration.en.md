# 🎯 Concentration

Concentration measures how far a portfolio's weight is gathered into a few positions, giving a reading that a plain count of holdings cannot provide.

It is covered here as **two** figures rather than one, and that is deliberate: the first counts how the money is spread, the second checks whether spreading it achieved anything. Read alone, the first will call a portfolio diversified when it is not.

---

## 🔢 The Count-Based Figure {: #the-count-based-figure }

The starting point is the Herfindahl index — the sum of squared weights:

$$
H = \sum_i w_i^{2}
$$

Squaring is what makes it a concentration measure: a weight of 50% contributes twenty-five times as much as a weight of 10%, so large positions dominate the total in a way a simple count never reflects.

The reciprocal turns that into something readable, the **number of effective assets**:

$$
N_{eff} = \frac{1}{H}
$$

It answers: *how many equally-sized positions would produce the concentration I actually have?* Ten positions of 10% each give $H = 10 \times 0.1^2 = 0.1$ and therefore exactly 10. One position of 50% alongside ten of 5% gives far fewer than eleven — the number falls towards the count of positions that actually matter.

The figure is intuitive precisely because it is expressed on the scale of a count while behaving nothing like one. That reading does depend on the weights summing to one: as soon as any cash is held they do not, and the result can climb past the number of holdings outright — [Where Cash Sits](#where-cash-sits) covers what happens then.

---

## 🙈 What a Count Cannot See {: #what-a-count-cannot-see }

The number of effective assets reads **only the weights**. It never looks at how the holdings behave, and this is its blind spot — a complete one.

Consider three portfolios, each holding ten equally-weighted assets, differing only in how correlated those assets are. Alongside the count-based figure, the table shows the **diversification ratio**, which compares the volatility the holdings would have had separately with the volatility of the portfolio they form:

$$
DR = \frac{\sum_i w_i \sigma_i}{\sigma_p}
$$

| Correlation between holdings | Number of effective assets | Diversification ratio |
|---|---|---|
| 0 | **10.00** | 3.15 |
| 0.5 | **10.00** | 1.35 |
| 0.95 | **10.00** | **1.02** |

The count-based figure does not move by a hundredth. The diversification ratio collapses.

!!! warning "Ten holdings that move together are not ten bets"

    At a correlation of 0.95 the portfolio behaves almost exactly like a single position: the ratio of 1.02 says that spreading the money across ten assets bought a 2% reduction in volatility over holding one of them. The count-based figure reports 10.00 in all three cases, and a reader looking only at that number would conclude all three portfolios were equally well diversified.

    This is why the two figures belong on the same page and in the same glance. One measures how the money is **spread**, the other whether the spreading **worked**.

The measured values above are consistent with the idealised case: for $n$ equally-weighted holdings of equal volatility and constant pairwise correlation $\rho$, the ratio is $\sqrt{n / (1 + (n-1)\rho)}$, which gives approximately 3.16, 1.35 and 1.02 for the three rows.

---

## 🏦 The Same Word at Two Granularities {: #two-granularities }

A portfolio can report two different concentration figures at the same moment, and neither is wrong. What changes is **what counts as one position**.

Suppose the same instrument is held at two brokers, at 6% and 4% of the portfolio.

- Counted **per position**, it contributes $0.06^2 + 0.04^2 = 0.0052$.
- Counted **per instrument**, the holdings are first added to 10%, contributing $0.10^2 = 0.0100$.

The difference is exactly $2 w_1 w_2$, which is always positive. So the per-instrument view **always** reports the higher concentration — and, since the effective-asset figure is the reciprocal, the per-position view **always** reports the more comfortable number.

!!! info "Two questions, not two answers"

    *How concentrated am I per position?* and *how concentrated am I per instrument?* are different questions, and a portfolio split across brokers answers them differently by construction. The per-instrument view is the one that matches market exposure: the same fund held in two accounts is one bet, however many rows it occupies.

    When two figures disagree, the thing to establish is which granularity each of them counted — not which one is correct.

A figure computed over positions is verifiable on this point: LibreFolio's portfolio and broker reporting builds its Herfindahl index from per-holding weights, and a holding there is identified by **both** its instrument and its broker.

---

## 🪙 Where Cash Sits {: #where-cash-sits }

Cash has to be handled somehow, and the choice changes the result. In the portfolio and broker reporting, the rule is stated in the code itself: weights are position value over **total NAV**, and cash is *included in the denominator but is not itself a term of the index*.

The consequence is worth spelling out, because it runs in a direction most readers would not guess. Cash dilutes every weight without contributing a square of its own, so holding more cash **lowers** the index and therefore **raises** the effective-asset count. A portfolio holding half its value in cash looks better diversified than the same holdings without it.

Under that rule the effect is larger than *looks better*. Write $s$ for the invested share of the portfolio, so that $s = 1 - \text{cash fraction}$ and the weights sum to $s$ instead of to one. Adding cash to a fixed set of holdings scales the index by $s^{2}$ and the effective-asset count by $1/s^{2}$; for $n$ evenly-weighted holdings that is exactly

$$
N_{eff} = \frac{n}{s^{2}}
$$

Two holdings and no cash give 2.00. The same two holdings give 8.00 with half the value in cash, roughly **11.4** with a little over half in cash, and 200 with ninety per cent in cash. A portfolio of two positions can therefore report a figure many times larger than two, and there is no upper bound at all: as cash approaches the whole portfolio, the count diverges.

Uneven weights pull the other way, so a lopsided portfolio holding little cash can still report fewer effective assets than it has holdings. The inflation itself, though, is always present — and the familiar reading, a value somewhere between one and the number of holdings, describes only the zero-cash case.

That is defensible — cash genuinely is an unconcentrated position, and it genuinely does reduce exposure to any single instrument — but it is an assumption, not a neutral fact, and reading a concentration figure without knowing it invites the wrong conclusion. Two portfolios with identical holdings and different cash balances are not equally diversified in their invested capital.

---

## 💡 Interpretation {: #interpretation }

Read the two figures as a pair, in this order:

1. **Effective assets against the actual number of holdings.** The direction of the gap selects its meaning: **below** the count, the weights are lopsided and a few positions carry the portfolio regardless of how many rows it has; **above** it, the excess is cash, and it says nothing about how the weights are spread.
2. **Diversification ratio.** A value near 1 means the holdings move as one, and the spreading bought little. The further above 1, the more the holdings offset one another.

The second figure is the one that can contradict the first, and it is the contradiction that carries the information. A portfolio can be perfectly balanced by weight and undiversified in substance — it is the ordinary outcome of holding several funds that track overlapping markets.

Neither figure says anything about **which** holdings drive the risk. That attribution is [Risk Contribution](risk-contribution.md), and the pairwise behaviour underneath both is [Correlation](correlation.md).

---

## ⚠️ Limitations {: #limitations }

!!! warning "Weights alone can be reassuring"

    The count-based figure is a function of the weights and nothing else. It cannot distinguish a genuinely varied portfolio from a set of near-identical holdings, and it is not evidence of diversification on its own.

!!! warning "Correlation-aware does not mean forward-looking"

    The diversification ratio depends on volatilities and correlations estimated over a window, and those change — typically in the least convenient direction, since correlations tend to rise in stressed markets. A comfortable ratio measured over a calm period is a measurement of that period. See [Data Quality](data-quality.md) for the window each result was computed on.

!!! warning "Concentration is not automatically a defect"

    Neither figure is a score. A deliberately concentrated portfolio is a choice, and a high effective-asset count is not an achievement in itself — as the table above shows, it can be reported by a portfolio that holds ten versions of the same bet.

---

## 🔗 Related {: #related }

- 🔗 **[Correlation](correlation.md)** — the pairwise behaviour the diversification ratio summarises
- 🧩 **[Risk Contribution](risk-contribution.md)** — which holdings carry the risk, once weights and co-movements are combined
- 📊 **[Volatility](volatility.md)** — the quantity the diversification ratio compares against
- 🧪 **[Data Quality](data-quality.md)** — the window volatilities and correlations were estimated over
