# ➗ Gains Against Losses (Omega)

The Omega ratio sets everything a series gained above a threshold against everything it lost below it. It answers a question an investor asks without any statistics: *for every euro lost on the bad days, how many were gained on the good ones?*

Unlike the [Sharpe](sharpe-ratio.md) and [Sortino](sortino-ratio.md) ratios it divides no average by a dispersion. It compares two sums of the same returns, cut at one threshold, and so it reads the **whole** distribution — the size of every gain and of every loss — rather than its first two moments.

---

## 🔢 Formula {: #formula }

For $N$ period returns $r_1, \dots, r_N$ and a per-period threshold $\tau$:

$$
\Omega(\tau) = \frac{\sum_{i=1}^{N} \max(r_i - \tau,\ 0)}{\sum_{i=1}^{N} \max(\tau - r_i,\ 0)}
$$

The numerator adds up how far each observation rose **above** the threshold; the denominator adds up how far each one fell **below** it. An observation exactly on the threshold adds nothing to either side. This is what `omega_ratio()` computes, in `backend/app/services/risk/metrics.py`.

### 🎯 The Threshold {: #threshold }

The threshold is not chosen per analysis. It is the reader's **risk-free rate**, the one fixed annual rate set under the period line of every risk page — 0% until it is set — and the same value the [Sortino ratio](sortino-ratio.md) and the semi-deviation use (see *The Risk-Free Rate* on the [Sharpe Ratio](sharpe-ratio.md) page). The engine receives it as the parameter `target_annual_return`, an **effective annual** rate $R_f$, and converts it into an effective per-period rate through the observed annualization factor $f$ of the series:

$$
\tau = (1 + R_f)^{1/f} - 1
$$

This is the same conversion as the Sharpe's and the Sortino's, through the same function (`daily_risk_free_rate`), so the three measures charge one rate on one period — see [Observed Annualization](observed-annualization.md) for $f$.

!!! info "The ratio itself is not annualized"

    The factor $f$ enters **only** through $\tau$. Both sums are taken over the same observations, so their ratio is a pure number with no time unit: there is nothing to scale by $\sqrt{f}$ or by $f$. Two Omegas measured over windows of different lengths are therefore directly comparable as ratios — though, as with every estimate, the shorter window is the less reliable one.

At the default rate of 0%, $\tau = 0$, and the formula simply divides the sum of the gains by the sum of the losses.

!!! example "Numerical example"

    Five daily returns: $+2\%$, $-1\%$, $+1\%$, $-0.5\%$, $+0.5\%$, at a risk-free rate of 0%.

    $$
    \Omega = \frac{2 + 1 + 0.5}{1 + 0.5} = \frac{3.5}{1.5} \approx 2.33
    $$

    For every 1 lost on the two bad days, about 2.33 were gained on the three good ones.

---

## 💡 How to Read It {: #interpretation }

The reference value is **1×**: gains above the threshold equal losses below it.

| Omega | What the value means |
|---|---|
| $< 1$ | The losses below the threshold outweighed the gains above it: on balance the series did worse than the risk-free rate |
| $= 1$ | Gains and losses balanced exactly: the average return equals the threshold |
| $> 1$ | The gains outweighed the losses: *1.25×* means 1.25 gained above the threshold for every 1 lost below it |

The app writes the figure as a multiple with two decimals — *1.25×* — and the block's sentence reads it as *for every 1 lost on the bad days, 1.25 were gained on the good ones*. With a non-zero risk-free rate the sentence says so and names the rate the answer used: a "bad day" is then any day below that rate, not only a day that lost money.

The ratio is never negative (both sums are non-negative), and it has no upper bound: a series whose few shortfalls are tiny can print a very large Omega. That is a true reading of the period, not a malfunction — but it is a reading of a small denominator, and it is the case to look at twice.

---

## 🔗 Relation to Sortino and to the Semi-deviation {: #relation-to-sortino }

Omega and the Sortino ratio share their threshold, and through it their sign. Dividing the numerator and the denominator of $\Omega$ by $N$ and rearranging gives:

$$
\Omega - 1 = \frac{\sum_i (r_i - \tau)}{\sum_i \max(\tau - r_i,\ 0)} = \frac{\bar r - \tau}{LPM_1(\tau)}
\qquad\text{where}\qquad
LPM_1(\tau) = \frac{1}{N}\sum_{i=1}^{N} \max(\tau - r_i,\ 0)
$$

The Sortino ratio has the **same numerator** over a different measure of the shortfalls:

$$
So = \frac{\bar r - \tau}{\sqrt{LPM_2(\tau)}}\cdot\sqrt{f}
\qquad\text{where}\qquad
LPM_2(\tau) = \frac{1}{N}\sum_{i=1}^{N} \min(r_i - \tau,\ 0)^2
$$

and $\sqrt{LPM_2(\tau)}\cdot\sqrt{f}$ is the annualized semi-deviation, the [downside deviation](sortino-ratio.md#downside-deviation) that both the Sortino ratio and the «How does it move?» block publish.

Three consequences follow, each exact:

- **The same sign.** $\Omega > 1$ exactly when the Sortino is positive, $\Omega = 1$ exactly when it is zero, and $\Omega < 1$ exactly when it is negative.
- **The same blank.** Both are undefined in one case only: no observation below the threshold. The code tests that case once, on the semi-deviation (`_no_downside`), for both measures — so the app never prints a missing Sortino beside an enormous Omega.
- **A different weighting of the losses.** $LPM_1$ is the *average* shortfall; $LPM_2$ squares each shortfall before averaging, so it lets a few deep losses dominate. Two series with the same average excess return and the same total of shortfalls have the same Omega; the one whose shortfalls are concentrated in a few large days has the higher semi-deviation and therefore the lower Sortino. Read together, the two say whether the losses were many and small or few and large.

---

## 📍 Where It Appears {: #where-it-appears }

| Surface | What it shows | Computed by |
|---|---|---|
| Risk tab, «How does it move?» block | The card *What the days were like* (technical name *Gains against losses · Omega*), and the block's headline sentence | `historical_kpi` (`omega_ratio` field), on the scope's series |
| Correlation tab, table «How did each one move?» | The column *Gains / losses*, one value per selected asset | `asset_set_kpi`, one `omega_ratio` per item |
| Asset chart, signal **Rolling Gains / Losses (Omega)** | A line of the ratio over a sliding window, with a reference line at **1×** (*Gains = losses*) | Signal `RISK_ROLLING_OMEGA` (`rolling_omega_values`) |

On the Risk tab the series is the historical one the «How much can it hurt?» cards read: the time-weighted return on a portfolio or a broker, the price returns on an asset (a portfolio narrowed to some of its assets replays today's weights instead — see the [Max Drawdown](max-drawdown.md#formula) page). On the Correlation tab each asset is measured on its own price returns over the shared calendar of the selection.

### 📈 The Rolling Signal {: #rolling-signal }

The chart signal applies the same formula to every window of $w$ consecutive price returns — 90 by default, between 2 and 500 — and plots the result at the end of each window. Its threshold is not a field of the signal: it is the reader's risk-free rate, shared with the risk pages (the parameter is declared with `x-control: "risk_free_rate"`), so a chart and a risk page never charge two different rates.

- A window with **no return below the threshold** has no value there (`null`, never a placeholder number), and the signal carries the warning `undefined_metric_window` with the number of undefined windows. Only when **every** window is undefined is the signal unavailable as a whole.
- The axis starts at 0 and the reference level sits at **1×**: above it, the window gained more than it lost.
- With a short window over a calm stretch, the denominator can hold one or two small shortfalls, and the line spikes. The spike is real arithmetic; setting the axis scale by hand brings the region around 1 back into view.

---

## ➖ When It Is Blank {: #when-it-is-blank }

Omega is undefined — `null`, shown as «—» — when **no observation fell below the threshold**: the denominator is zero, and a ratio over nothing is not a large number but no number. The result then carries the warning `omega_undefined` — on the Correlation tab's table, one warning of that code naming the assets concerned — which does not mark the result as partial: the series is complete, it simply never fell below the rate.

At a risk-free rate of 0% this means a period without a single losing observation. With a positive rate it is rarer still, because any return below the rate — even a small gain — is a shortfall.

---

## ⚠️ Limitations {: #limitations }

!!! warning "Sensitive to a small denominator"

    The ratio is only as stable as the sum of the shortfalls. Over a short window, or a calm period with few days below the threshold, one more bad day can move it a long way. The figure describes the period; it is not a property of the asset.

!!! warning "It depends on the threshold"

    Omega is a function of $\tau$, not one number: raising the risk-free rate moves gains into the denominator and lowers the ratio. Two Omegas are comparable only when they were measured at the same rate — which is why the app shows the rate the answer used.

!!! warning "It ignores the order of the days"

    Like the Sortino ratio and the [Value at Risk](value-at-risk.md), Omega reads the distribution, not the path: shuffle the returns and it does not move. How deep and how long the falls were is the [Max Drawdown](max-drawdown.md)'s question.

---

## 🔗 Related {: #related }

- 📊 **[Sortino Ratio](sortino-ratio.md)** — the same numerator, over the semi-deviation
- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — where the risk-free rate is explained
- 🌗 **[The Shape of the Days](return-shape.md)** — the other measures of «How does it move?»
- 🗓️ **[Observed Annualization](observed-annualization.md)** — the factor that converts the annual rate into the threshold
