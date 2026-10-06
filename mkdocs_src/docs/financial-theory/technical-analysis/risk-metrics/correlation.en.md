# 🔗 Correlation

Correlation measures **how two positions move in relation to each other**. It is the metric that decides whether a portfolio is genuinely diversified or merely long: owning many things is not diversification if those things rise and fall together.

---

## 🔢 Formula {: #formula }

For two return series $r_i$ and $r_j$ observed over the same $N$ periods, the Pearson correlation coefficient is their covariance normalised by their standard deviations:

$$\rho_{i,j} = \frac{\mathrm{Cov}(r_i, r_j)}{\sigma_i \, \sigma_j}$$

with the unbiased ($N-1$) sample estimators:

$$\mathrm{Cov}(r_i, r_j) = \frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})(r_{j,t} - \bar{r_j}) \qquad \sigma_i = \sqrt{\frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})^2}$$

Dividing by the two standard deviations is what makes the result comparable: covariance is expressed in squared return units and grows with the volatility of its inputs, while $\rho$ is a pure number bounded by $-1$ and $+1$ whatever the assets are.

!!! info "Correlation is computed after currency conversion"

    Returns enter the calculation already converted into the target currency requested for the analysis — the same rule for a portfolio and for a set of assets. The figure therefore describes what a holder measuring in that currency experienced, exchange-rate movements included — not what the instrument did in its home currency. Two assets quoted in different currencies are compared on the same converted basis.

---

## 💡 Interpretation {: #interpretation }

The coefficient has three reference points, and only three that require no convention:

| Value | Meaning |
|---|---|
| $\rho = +1$ | The two series move in perfect lockstep: one is an exact positive linear function of the other |
| $\rho = 0$ | No **linear** relationship between the two series over the observed window |
| $\rho = -1$ | Perfect opposition: one series is an exact negative linear function of the other |

Everything between those poles is a matter of degree, and LibreFolio deliberately does not slice that range into named bands: there is no level at which a pair becomes "too correlated", because the answer depends on how much of the portfolio those two positions represent — a question the correlation matrix alone cannot answer.

### 🧩 Why the Matrix Answers "Am I Diversified?" {: #why-the-matrix-answers-am-i-diversified }

The number of positions is a count; diversification is a behaviour. Ten holdings that all respond to the same driver behave, in a bad month, like one position held ten times. The correlation matrix is what makes that visible: it is the map of the relationships, not a verdict on them.

Read it for structure rather than for individual values — the clusters of positions that move together, the pairs that genuinely do not, and whether a supposed diversifier actually behaves like one. The diagonal carries no information: wherever it holds a value, that value is $+1$ by construction — but a flat series' own diagonal cell is `undefined`, and a matrix below the observation floor holds no values at all (see [How Each Cell Is Computed](#how-each-cell-is-computed)).

Correlation answers *how* the positions move together. It says nothing about **how much** of the portfolio each one represents, which is why it is read alongside [Concentration](concentration.md) and [Risk Contribution](risk-contribution.md): a strong correlation between two marginal positions matters far less than a moderate one between the two largest.

---

## 🧮 How Each Cell Is Computed {: #how-each-cell-is-computed }

Every cell of the matrix comes back in one of three states, and every cell carries the observation count it was judged on.

| Cell status | When | What is published |
|---|---|---|
| `ok` | The shared calendar holds enough observations and neither series is flat | The coefficient, clamped to $[-1, +1]$ |
| `insufficient` | The shared calendar holds fewer observations than the required minimum — every cell of the matrix is then in this state | No value — the count is published without a coefficient |
| `undefined` | At least one of the two series has (numerically) zero variance | No value — a series that never moves has no direction to share |

The minimum is applied to the **matrix as a whole**, not pair by pair. Because every series sits on the same shared calendar (see below), every pair is computed on exactly the same dates, so there is a single observation count for the whole matrix: it either clears the floor or it does not, and when it does not, every cell is reported as insufficient. A short history therefore never leaves some pairs computed and others blank — it shortens the calendar, and with it the sample, for every pair at once. The default floor is 20 observations, and it is an adjustable parameter of the analysis rather than a hard-coded rule.

Each non-`ok` state that occurs at least once also raises a warning on the result — `insufficient_pair_history` and `flat_series` respectively — so a matrix that is wholly or partly unusable says so explicitly instead of leaving blank cells to be interpreted. Despite its name, `insufficient_pair_history` always concerns the whole matrix. A flat series, by contrast, blanks only its own row and column and leaves every other correlation untouched.

!!! info "All series share one calendar"

    Before any correlation is computed, every series in scope is aligned onto a single shared calendar: a date enters the analysis only if **every** holding can be valued on it in the target currency. Pairs are therefore never computed on mismatched or interpolated dates — but the cost is collective, because a date that fails for one holding is dropped for all of them. A holding with a short history — one that cannot be valued before the requested start — shortens the window for the whole matrix: the calendar begins on the first date on which every holding can be valued, and the data-quality report names the holdings concerned rather than listing the dates skipped. A gap inside a history removes no dates: a missing price, like a missing exchange rate, is replaced by the last known one, carried forward with no age limit, and the report counts as carried-forward points only those held over beyond the [staleness threshold](data-quality.md#staleness-threshold). Once the calendar has started, a date is dropped only if some holding still has no value in the target currency on it, and such dates are listed in the report as incomplete. See [Data Quality](data-quality.md).

    When the matrix is built over a set of assets picked directly, with no portfolio behind them, an asset with **no price series at all** is not a short history but an absent one: it is excluded from the scope before the calendar is built. The result lists it as excluded — with the reason `no_price_source` when no price source is assigned to it and no price has ever been recorded for it, `missing_price` otherwise — raises an `assets_excluded` warning and is marked `partial`. The asset does not appear as a flat row, and it does not shorten the window for the other assets. See [Exclusions](data-quality.md#exclusions).

---

## ⚠️ Limitations {: #limitations }

!!! warning "Correlation only sees the linear part of a relationship"

    $\rho$ measures how well the relationship between two series is described by a straight line. A dependency that is real but curved — one asset reacting only to large moves of another, for instance — can produce a coefficient near zero. A low correlation means "no linear link was detected in this window", never "these positions are unrelated".

!!! warning "One number for the whole window"

    A correlation is an average over the requested period. A pair that was unrelated for most of the window and moved together at the worst moment produces a reassuring average. This is the well-documented asymmetry of diversification: correlations observed in calm conditions are not a promise about behaviour under stress, when positions that looked independent frequently stop being so. The matrix describes the window it was measured on, and nothing else.

!!! warning "Correlation is not causation, and not magnitude"

    Two assets can be strongly correlated through a common driver with no relationship to each other. And correlation says nothing about size: a pair correlated at $+1$ where one asset moves violently and the other barely at all shares direction, not risk. Magnitude belongs to [Volatility](volatility.md), weight belongs to [Risk Contribution](risk-contribution.md).

---

## 🔗 Related {: #related }

- 🧩 **[Concentration](concentration.md)** — how much of the portfolio each position actually represents
- ⚖️ **[Risk Contribution](risk-contribution.md)** — which positions drive portfolio risk once correlation and weight are combined
- 📊 **[Volatility](volatility.md)** — the magnitude that correlation deliberately normalises away
- 🧪 **[Data Quality](data-quality.md)** — the shared calendar, and what a missing date costs the whole matrix
