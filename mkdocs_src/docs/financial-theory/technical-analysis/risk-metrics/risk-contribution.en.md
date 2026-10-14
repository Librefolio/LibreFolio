# 🧩 Risk Contribution

Risk contribution attributes total portfolio risk back to the individual holdings, and what each position contributes is generally not the same as how much of the portfolio it represents.

Knowing the weights tells you nothing new — they are visible in the portfolio itself. Knowing where the **risk** comes from usually does, because a position's contribution depends on how volatile it is and on how it moves together with everything else it is held alongside.

---

## 🔢 Formula {: #formula }

The decomposition starts from the portfolio variance written through the covariance matrix $\Sigma$ of the asset returns and the vector of weights $w$:

$$
\sigma_p = \sqrt{w^{\top} \Sigma\, w}
$$

Three quantities are derived from it, in this order:

$$
MCTR_i = \frac{(\Sigma w)_i}{\sigma_p}, \qquad
CCTR_i = w_i \cdot MCTR_i, \qquad
PCTR_i = \frac{CCTR_i}{\sigma_p}
$$

| Quantity | Reads as | Answers |
|---|---|---|
| $MCTR_i$ — marginal | Sensitivity of portfolio volatility to the weight of $i$ | *If I add a little of this position, how much does total risk move?* |
| $CCTR_i$ — component | That sensitivity multiplied by the weight actually held | *How much of the total risk does this position bring, in volatility units?* |
| $PCTR_i$ — percentage | The component as a share of total volatility | *What fraction of the portfolio's risk is this position?* |

The marginal figure is the derivative $\partial \sigma_p / \partial w_i$: it describes the **next** unit of the position, not the one held. The component figure is the one that describes the holding as it stands.

!!! info "The annualization is applied to the covariance matrix"

    Every entry of $\Sigma$ is multiplied by the observed annualization factor $f$ before the decomposition runs, so the portfolio volatility and all three contribution figures come out on an annual basis. Scaling a covariance by $f$ is the matrix form of multiplying a standard deviation by $\sqrt{f}$ — the same operation, and the same measured factor, used by [Volatility](volatility.md). See [Observed Annualization](observed-annualization.md) for where $f$ comes from.

---

## ➗ Why the Parts Add Up {: #why-the-parts-add-up }

The component contributions sum to the portfolio volatility **exactly**, and the percentage contributions therefore sum to $1$:

$$
\sum_i CCTR_i = \sum_i w_i \frac{(\Sigma w)_i}{\sigma_p} = \frac{w^{\top} \Sigma\, w}{\sigma_p} = \frac{\sigma_p^{2}}{\sigma_p} = \sigma_p
\qquad\Longrightarrow\qquad
\sum_i PCTR_i = 1
$$

This is not an approximation that happens to be close, and not a normalisation applied afterwards to force the numbers to a round total. It is Euler's decomposition, and it holds because $\sigma_p$ is **homogeneous of degree 1** in the weights: doubling every weight doubles the portfolio volatility. Any such function is recovered exactly by the sum of its arguments times its own partial derivatives, which is precisely the sum above.

The practical consequence is the reason the metric is published at all: because the shares are exact and add to one, **a percentage contribution can be compared directly against a weight**. A position at 10% of the portfolio carrying 30% of the risk is a statement with no hidden scaling in it.

---

## ⚖️ Contribution Is Not Weight {: #contribution-is-not-weight }

The two numbers answer different questions, and they separate for two reasons that compound:

- **Volatility.** A position that moves twice as much as the rest brings more risk per unit of capital.
- **Correlation.** A position that moves *with* the others adds its volatility on top of theirs; one that moves against them partly cancels what the others do. The same holding, at the same weight, contributes differently depending on the company it keeps.

That second reason is why the contribution cannot be read off a single position in isolation: $(\Sigma w)_i$ contains every covariance between asset $i$ and the rest of the portfolio, so changing an *unrelated* holding changes this one's contribution.

!!! tip "Where the metric earns its place"

    A small position in something volatile and closely tied to the rest of the book can carry a share of risk several times its share of capital — and the portfolio view will never show it, because the portfolio view shows weights. Conversely, a large holding that moves out of step with everything else can contribute far less risk than its size suggests. Diversification is visible here in a way it is not in [Correlation](correlation.md) alone: correlation says which pairs move together, this says what that costs once the amounts held are taken into account.

---

## 🧾 What the Inputs Must Satisfy {: #what-the-inputs-must-satisfy }

The decomposition refuses inputs it cannot honestly decompose. These are **declared boundaries of the first wave**, not gaps left by omission:

| Requirement | Behaviour when violated |
|---|---|
| Weights must be non-negative | Rejected — short positions are outside the first-wave contract |
| The composition must not be leveraged | Rejected upstream — asset weights above 100% of scope value are outside the contract |
| The covariance matrix must be symmetric | Rejected, within a numerical tolerance for floating-point noise |
| Matrix dimensions must match the weights | Rejected |
| All return series must share one common calendar | Rejected — the covariance matrix is built over a single observation calendar |

A short position would break the arithmetic above in a specific way: with negative weights, a component contribution can be negative, and a share of "total risk" that is below zero cannot be read as a share of anything. Refusing the input is the honest response until the presentation contract covers that case.

Cash is handled without appearing in the matrix at all. Asset weights sum to one minus the cash share, so the volatility computed is already that of the **whole** portfolio, cash included — and cash never shows up as a contributor, because a holding that does not move has a marginal contribution of zero. The cash share is published alongside the contributions so the reader can see what the remainder is.

---

## 💡 Interpretation {: #interpretation }

Read the percentage contribution **against the weight**, not on its own:

- contribution ≈ weight — the position carries its own share, no more
- contribution > weight — it is a concentrated source of risk relative to the capital committed to it
- contribution < weight — it is diluting portfolio risk, either because it is calm or because it moves differently from the rest

The marginal figure answers a different question and is the one to use when thinking about a change: it says what the **next** euro into that position does to total volatility. A position can carry a large component contribution simply because it is large, while its marginal contribution is unremarkable.

---

## ⚠️ Limitations {: #limitations }

!!! warning "It decomposes volatility, not loss"

    Every figure on this page is a share of **portfolio volatility**. Volatility counts moves in both directions, so a position that contributes 30% of the risk is not thereby expected to produce 30% of any loss. Contributions to a downside figure are a different decomposition, and this is not it. For what fluctuation does and does not capture, see [Volatility](volatility.md).

!!! warning "It is a snapshot of the current composition"

    The weights are the ones held now, and the covariance matrix is estimated over the analysed window. The result describes today's portfolio measured against that history — it is not a statement about how the risk was distributed in the past, when the composition was different.

!!! warning "The matrix is an estimate, and it inherits its window"

    Covariances are estimated from a finite sample over one common calendar. A short window, a turbulent stretch, or an asset with a sparse price history produces an estimate that a different window would not reproduce, and every contribution derives from that estimate. Correlations in particular are known to move when markets are stressed. Each result publishes the observation count and the window it used — see [Data Quality](data-quality.md).

!!! warning "Zero volatility returns zeros, not an absent result"

    If the portfolio volatility is indistinguishable from zero, all three contribution figures are returned as exactly zero. That is the answer, not a placeholder: with no risk to attribute, every share of it is genuinely nothing. It is worth contrasting with the [Beta and Active Return](beta-active-return.md) page, where a benchmark with no variance produces **no value at all** — there the quantity would be a division by zero, so there is nothing to report; here the quantity exists and equals zero.

---

## 🔗 Related {: #related }

- 🔗 **[Correlation](correlation.md)** — which holdings move together, before amounts are taken into account
- 📊 **[Volatility](volatility.md)** — the total being decomposed
- 🎯 **[Concentration](concentration.md)** — how much of the portfolio sits in how few positions
- 🗓️ **[Observed Annualization](observed-annualization.md)** — the factor applied to the covariance matrix
- 🧪 **[Data Quality](data-quality.md)** — the window and the observations the matrix was estimated on
