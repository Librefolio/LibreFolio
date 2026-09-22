# 📐 Beta & Active Return

Beta measures how strongly a portfolio tends to follow its benchmark, while active return isolates the part of the result the benchmark does not explain. Both are **relative** figures: they describe a portfolio only in the company of the series it was compared against, and they change when that series changes.

---

## 🔢 Formula {: #formula }

Four quantities are computed from the two aligned return series — the portfolio, $p$, and the comparison series, $b$.

**Beta** is the sample covariance of the two series divided by the variance of the comparison:

$$
\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}
$$

Both moments use the unbiased $(N-1)$ estimators, so at least two common observations are required.

**Active return** is the difference between the two compounded returns over the whole window:

$$
AR = \left[\prod_{t=1}^{N} (1 + r_{p,t}) - 1\right] - \left[\prod_{t=1}^{N} (1 + r_{b,t}) - 1\right]
$$

**Tracking error** is the dispersion of the per-period difference $a_t = r_{p,t} - r_{b,t}$, annualized with the measured factor:

$$
TE = \sigma_a \times \sqrt{f}
$$

**Information ratio** relates the average of that difference to its dispersion, annualized on the same basis:

$$
IR = \frac{\bar{a}}{\sigma_a} \times \sqrt{f}
$$

The factor $f$ is the same observed annualization factor used everywhere else in the analysis — counted from the data rather than assumed. See [Observed Annualization](observed-annualization.md).

!!! info "The two series must be aligned"

    Both series are compared point by point, so they must cover the same observations: a comparison is computed only when the two series have the same length and at least two observations. The alignment is performed before the metrics are reached, which is why a result that used a shortened window says so through its observation count rather than through a silently shifted comparison.

---

## 🚫 When Beta Has No Value {: #when-beta-has-no-value }

Beta is not always defined, and when it is not, no number is published.

**A comparison series with zero variance yields no beta.** Beta expresses how the portfolio responds to movements of the comparison series; a series that does not move offers nothing to respond to. Mathematically the denominator vanishes, and any value returned in its place would be an artefact of the arithmetic rather than a measurement. The result reports the absence instead.

The same discipline applies to the information ratio: if the per-period difference between the two series never varies, its dispersion is zero, and the ratio is left unpublished rather than forced.

!!! info "An absent value is a result"

    A missing beta is not a failure of the calculation — it is what the data supports. Reading it as "no relationship" would be the wrong conclusion: it means the comparison series provided no variation against which a relationship could be measured at all.

---

## ➗ Active Return Is a Difference of Compounded Returns {: #active-return-is-a-difference-of-compounded-returns }

The order of operations matters, and it is the source of the most common misreading of this number. Active return compounds each series over the window **first** and subtracts **afterwards**. It is not the compounding of the per-period differences.

Three consequences follow.

**It does not add up across time.** The active return of a year is not the sum — nor the compounding — of the active returns of its months. Each figure belongs to the window it was computed on, and windows cannot be chained.

**It is not the return of a strategy.** It is not what an investor would have earned holding the portfolio and shorting the benchmark: that position would compound the difference, and would also carry financing and rebalancing effects that no subtraction of two compounded returns can represent.

**It does not decompose into skill.** Active return states that the portfolio ended the window ahead of or behind its comparison, by that amount. It attributes nothing: the gap may come from different exposures, different timing, or from a comparison that was never an appropriate yardstick to begin with.

---

## 💡 Interpretation {: #interpretation }

**Beta** describes sensitivity, not quality. A beta of $1$ means the portfolio has tended to move one-for-one with the comparison series; below $1$ it has moved less than the series, above $1$ more. The sign matters more than any threshold: a negative beta means the portfolio has tended to move in the opposite direction.

It is worth separating beta from correlation, because they are easily conflated. From the definitions above, $\beta = \rho_{p,b} \times \dfrac{\sigma_p}{\sigma_b}$: correlation captures only the *direction* of the relationship, while beta also carries the ratio of the two volatilities. A portfolio can track its comparison closely and still have a beta far from $1$ simply because it fluctuates more, or less, than the series it follows. See [Correlation](correlation.md).

**Active return** is the distance between the two finish lines, measured over the window.

**Tracking error** is how consistently that distance was travelled. It is the volatility of the difference, so a large value says the portfolio departed from its comparison frequently or violently — in either direction, since it is a dispersion and carries no sign.

**Information ratio** puts the two together: it expresses the average per-period difference in units of its own dispersion, annualized. A higher ratio means the difference was more regular relative to how much it varied; a ratio near zero means the difference, whatever its sign, is small compared with the variation around it. No value is good or bad in itself — the figure depends on the length of the window and on the comparison chosen, and the same number measured over a different window is not the same statement.

---

## ⚠️ Limitations {: #limitations }

!!! warning "Every figure here inherits its benchmark"

    Beta, active return, tracking error and information ratio are all measured *against* a comparison series. Change the series and every one of them changes, without anything about the portfolio having changed. A relative figure quoted without naming what it was measured against is incomplete. See [Benchmark Selection](benchmark-selection.md).

!!! warning "Beta sees a straight line, over one window"

    Beta is the slope of a linear relationship estimated over the observed period. A portfolio whose behaviour differs between calm and stressed conditions is summarised by a single slope that describes neither. And because it is estimated, a short window produces a figure that reflects the particular sequence it happened to contain.

!!! warning "Sensitivity is not explanation"

    A beta near $1$ says the portfolio moved with the comparison series; it does not say the series drives the portfolio, nor that the remainder is skill. Two series can move together through a common cause with no relationship to one another — the same caution that applies to correlation applies here, with the ratio of volatilities added on top.

---

## 🔗 Related {: #related }

- 🎯 **[Benchmark Selection](benchmark-selection.md)** — the choice that every figure on this page inherits
- 🔗 **[Correlation](correlation.md)** — direction of the relationship, with the volatility ratio removed
- 📊 **[Volatility](volatility.md)** — the dispersion that turns a correlation into a beta
- 📏 **[Observed Annualization](observed-annualization.md)** — the measured factor used to annualize tracking error and information ratio
