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

    Returns enter the calculation already converted into the portfolio's target currency. The figure therefore describes what the holder actually experienced, exchange-rate movements included — not what the instrument did in its home currency. Two assets quoted in different currencies are compared on the same converted basis.

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

Read it for structure rather than for individual values — the clusters of positions that move together, the pairs that genuinely do not, and whether a supposed diversifier actually behaves like one. The diagonal is always $+1$ by construction and carries no information.

Correlation answers *how* the positions move together. It says nothing about **how much** of the portfolio each one represents, which is why it is read alongside [Concentration](concentration.md) and [Risk Contribution](risk-contribution.md): a strong correlation between two marginal positions matters far less than a moderate one between the two largest.

---

## 🧮 How Each Cell Is Computed {: #how-each-cell-is-computed }

Every cell of the matrix carries its own evidence, and each one can come back in one of three states.

| Cell status | When | What is published |
|---|---|---|
| `ok` | The pair had enough common observations and neither series is flat | The coefficient, clamped to $[-1, +1]$ |
| `insufficient` | The pair has fewer common observations than the required minimum | No value — the count is published without a coefficient |
| `undefined` | At least one of the two series has (numerically) zero variance | No value — a series that never moves has no direction to share |

The minimum is applied **per pair**, not to the matrix as a whole: one pair with too short a shared history is reported as insufficient while every other cell is still computed. The default floor is 20 common observations, and it is an adjustable parameter of the analysis rather than a hard-coded rule.

Each state that occurs at least once also raises a warning on the result, so a matrix that is partly unusable says so explicitly instead of leaving blank cells to be interpreted.

!!! info "All series share one calendar"

    Before any correlation is computed, every series in scope is aligned onto a single shared calendar: a date enters the analysis only if **every** holding could be valued on it. Pairs are therefore never computed on mismatched or interpolated dates — but the cost is collective, because a date missing for one holding is dropped for all of them. A position with a short or gappy history shortens the window for the whole matrix, and the discarded dates are reported. See [Data Quality](data-quality.md).

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
