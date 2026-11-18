# 🌗 The Shape of the Days

The measures of «How does it move?» are the other side of «How much can it hurt?». Where the loss measures read the left tail of a series — its worst day, its worst month, its deepest fall — these read the rest: the best moments of the period, and what an ordinary day looked like.

Each one is computed by the backend from the same return series, over the same days, as the loss measures beside it. The shared functions live in `backend/app/services/risk/metrics.py` (`return_shape()` and its helpers, `largest_rally()`, `best_horizon_window()`) and in `backend/app/services/risk/acquired.py` (`best_realization()`, `average_drawdown()`).

---

## 🧭 Where the Figures Come From {: #where-the-figures-come-from }

No analytic of its own computes them. They are fields of the answers the loss measures already need:

| Answer | One series (Risk tab) | One row per asset (Correlation tab) | Fields |
|---|---|---|---|
| Historical KPIs | `historical_kpi` | `asset_set_kpi` | `best_realization` (+ date), `positive_observation_share`, `mean_positive_return`, `mean_negative_return`, `longest_positive_run_*`, `omega_ratio`, `downside_deviation`, `extreme_day_ratio` |
| Drawdown | `drawdown_summary` | `asset_set_drawdown` | `largest_rally` (+ dates and duration), `average_drawdown` |
| 30-day Value at Risk | `historical_var` | `asset_set_var` | `best_horizon` |

On the Risk tab the series is the scope's: the time-weighted return on a portfolio or a broker, the price returns on an asset. On the Correlation tab every asset is measured on its own price returns, over the calendar the selection shares.

!!! info "Two reference points"

    The day-counting measures — the best day, the share of positive days, the average up and down day, the positive streak — count around **zero**: a gain is a return above $0$. Gains against losses (Omega) and the semi-deviation count around the reader's **risk-free rate**, the one threshold of every «excess» measure (see *The Risk-Free Rate* on the [Sharpe Ratio](sharpe-ratio.md) page). At the default rate of 0% the two reference points coincide.

Throughout the page, $r_1, \dots, r_N$ are the period returns and $W_0 = 1,\ W_t = \prod_{s \le t}(1 + r_s)$ is the compounded growth index the [Max Drawdown](max-drawdown.md) walks.

---

## ☀️ The Best Day {: #best-day }

$$
r_{best} = \max_{i} r_i
$$

The single best return of the period, with its date. On equal returns the earliest one is reported. It is the twin of the [Worst Realization](worst-realization.md): an observed fact, not an estimate.

**Blank** («—») when no observation gained: $r_{best} \le 0$ is not a "best day" in the sense the card names, and reporting it would point at a day that lost or stood still. The warning is `best_realization_undefined`, which blanks the average up day and the positive streak with it.

---

## 📆 The Best 30 Days {: #best-30-days }

$$
R^{(n)}_{best} = \max_{k} \prod_{i=k}^{k+n-1} (1 + r_i) - 1
$$

The best compounded stretch of 30 calendar days the series actually went through, with the first and the last date of it. It is read from the windows of the 30-day [Value at Risk](value-at-risk.md) (`best_horizon`, the twin of its `worst_horizon`): the 30 days are converted into $n = \max(1, \operatorname{round}(30 f / 365))$ observations at the series' [observed annualization factor](observed-annualization.md) $f$ — 21 on a series quoted on trading days, 30 on one quoted every calendar day — and every run of $n$ consecutive returns is compounded. On equal windows the earliest is reported.

It is **not floored**: in a period in which every 30-day stretch lost, the best one lost too, and the figure is negative. That is the truth of the period, not a missing value.

**Blank** when the 30-day Value at Risk itself is unavailable — fewer than 20 compounded windows, that is $N < n + 19$ returns. There is no warning code of its own: the answer that would carry the window is the one reporting insufficient history. The windows overlap, so the caveat on the [Value at Risk page](value-at-risk.md#limitations) applies here as well.

---

## 🚀 The Largest Rally {: #largest-rally }

$$
\text{Rally} = \max_{t} \left( \frac{W_t}{\min_{s < t} W_s} - 1 \right)
$$

The largest rise from a low to a **later** high, measured on the same compounded index as the [Max Drawdown](max-drawdown.md) — the twin of the worst fall. The result carries the date of the low, the date of the high and the calendar days between them; on equal rallies the earliest is reported. The low can be the index's starting point, the day before the first return.

Because it is measured on returns, a deposit is not a rally: on a portfolio the index is the time-weighted return, which money moving in and out does not raise.

**Never blank.** A series that never rose from any low reports a rally of exactly $0$, with no dates and a duration of zero: a measured zero, not a missing figure. A value of zero (a total loss) cannot be the low a rally starts from.

---

## ➕ Positive Days {: #positive-days }

$$
p = \frac{\#\{\, i : r_i > 0 \,\}}{N}
$$

The share of observations with a gain. A day at **exactly zero** does not count as positive — on a quiet instrument, or wherever a price is unchanged from the previous observation, such days can be numerous, and counting them would inflate the share.

**Never blank**: a series with no gaining day has a share of $0$.

---

## ⚖️ The Average Up Day and Down Day {: #average-day }

$$
\bar r_{+} = \frac{1}{N_{+}} \sum_{r_i > 0} r_i,
\qquad
\bar r_{-} = \frac{1}{N_{-}} \sum_{r_i < 0} r_i
$$

where $N_{+}$ and $N_{-}$ are the numbers of gaining and losing observations. Each is the mean of its own days only; days at exactly zero enter neither. Read together with the share of positive days, they tell a series that wins often and small from one that wins rarely and big.

**Blank** when its side is empty: no gaining day leaves $\bar r_{+}$ blank (warning `best_realization_undefined`), no losing day leaves $\bar r_{-}$ blank (warning `average_loss_undefined`).

---

## 🔁 The Longest Positive Streak {: #positive-streak }

The longest run of **consecutive** observations with a gain, with its first and last date. A day at exactly zero breaks the run; on equal runs the earliest is reported. The length is counted in observations of the series — on a series quoted on trading days, the weekend between Friday and Monday does not break a streak, because it holds no observation.

**Blank** with no gaining observation at all (warning `best_realization_undefined`).

---

## 🌊 Below the Peak, on Average {: #average-drawdown }

$$
ADD = \frac{1}{N} \sum_{t=1}^{N} DD_t,
\qquad
DD_t = \frac{W_t - \max_{\tau \le t} W_\tau}{\max_{\tau \le t} W_\tau}
$$

The average drawdown: the mean of the underwater curve, on the same compounded index as the [Max Drawdown](max-drawdown.md), the [Ulcer Index](ulcer-index.md) and the drawdown quantiles. Where the maximum reports the single deepest point, this averages **every** day — so it is the measure of a period spent under water, not of one bad fall. It is a non-positive number; the sum runs over the index's starting point too, where the drawdown is zero, but is divided by the number of returns $N$ — the same divisor the Ulcer Index uses.

**Never blank**: a series that never fell below a previous peak reports $0$.

---

## 📉 The Semi-deviation {: #semi-deviation }

The volatility of the observations **below the risk-free rate**, annualized: the denominator of the Sortino ratio, published on its own. Its formula and the choice of convention (around a threshold, over $N$) are on the Sortino page — see [Downside Deviation](sortino-ratio.md#downside-deviation).

The app writes it beside the volatility of the same series — *9.8% downward · out of a 13.9% swing* — because the comparison is the reading: when the returns are symmetric around the threshold, the semi-deviation is about $1/\sqrt{2} \approx 71\%$ of the volatility; well below that, the falls were lighter than the rises; above it, heavier.

**Never blank**: with nothing below the threshold it is $0$ — which is precisely the case that leaves the Sortino and the Omega undefined.

---

## ➗ Gains Against Losses {: #omega }

The headline of the block: the sum of the gains above the risk-free rate over the sum of the shortfalls below it, read against **1×**. It has a page of its own — see [Gains Against Losses (Omega)](omega-ratio.md).

**Blank** when no observation fell below the threshold (warning `omega_undefined`).

---

## 🎲 Extreme Days {: #extreme-days }

$$
\text{Extreme days} = \frac{K}{3},
\qquad
K = \frac{m_4}{m_2^{2}},
\qquad
m_k = \frac{1}{N} \sum_{i=1}^{N} (r_i - \bar r)^k
$$

$K$ is the **Pearson kurtosis** of the returns, from population moments — the value SciPy returns as `kurtosis(x, fisher=False)` with its default biased estimator, not the excess kurtosis $K - 3$. A normal distribution has $K = 3$, so the figure reads **1×** on a bell curve. `extreme_day_ratio()` computes it.

The app reads the figure as *how much more often very large days, up or down, came than a bell curve would give*. That is the intuition, and the direction is right, but it is not a literal ratio of counts: kurtosis is the weight of the fourth power of the deviations relative to the squared variance, so it measures how much of the dispersion sits in the **tails** rather than near the mean.

- **1×** — tails like a normal distribution of the same volatility
- **above 1×** — fatter tails: large moves, in either direction, carry more of the variance than a bell curve would allow; daily equity returns typically sit well above 1
- **below 1×** — thinner tails than a bell curve, e.g. $0.6\times$ for returns spread evenly over a range, $\approx 0.33\times$ for a series that only alternates between two values

The figure is symmetric: it does not say whether the extreme days were gains or losses. For which side they fell on, read the best day against the [Worst Realization](worst-realization.md).

**Blank** when the series does not move — fewer than two observations, or a sample standard deviation indistinguishable from zero, the same test that leaves the Sharpe ratio undefined (warning `extreme_day_ratio_undefined`).

---

## ➖ When a Figure Is Blank {: #when-blank }

A blank is never a zero. The app shows «—» with the reason, read from the warning the answer carries; none of these warnings marks the result as partial, because a series that never gained, never lost or never moved is complete — only made so.

| Warning | Blanks | Condition |
|---|---|---|
| `best_realization_undefined` | Best day, average up day, positive streak | No observation above zero |
| `average_loss_undefined` | Average down day | No observation below zero |
| `omega_undefined` | Gains against losses | No observation below the risk-free rate |
| `extreme_day_ratio_undefined` | Extreme days | The series does not move |

On the Correlation tab's table each of these is one warning naming the assets it concerns. The best 30 days has no code of its own (it is blank when the 30-day Value at Risk is unavailable); the positive share, the semi-deviation, the largest rally and the average drawdown are always defined.

---

## ⚠️ Limitations {: #limitations }

!!! warning "Facts of one period, not properties of the asset"

    The best day, the best 30 days and the largest rally are single observed episodes. A different period would show different ones, and a short period may simply not contain the kind of day it is asked about.

!!! warning "Not additive across horizons"

    A day, 30 days and the whole period are different horizons: the best day, the best 30 days and the largest rally are not meant to be added up or compared with one another, only across subjects measured over the same period.

---

## 🔗 Related {: #related }

- ➗ **[Gains Against Losses (Omega)](omega-ratio.md)** — the headline of the block
- 📊 **[Sortino Ratio](sortino-ratio.md)** — the semi-deviation and its convention
- 📉 **[Max Drawdown](max-drawdown.md)** — the curve the rally and the average drawdown walk
- 🔻 **[Worst Realization](worst-realization.md)** — the twin of the best day
- 📉 **[Value at Risk](value-at-risk.md)** — the 30-day windows the best 30 days are read from
