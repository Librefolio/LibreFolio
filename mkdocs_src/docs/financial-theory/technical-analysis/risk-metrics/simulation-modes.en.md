# 🎲 Simulation Modes

The simulation projects a portfolio forward by generating a large number of possible futures and reading the distribution of where they arrive. It is the one place in this section where **nothing in the output happened**: every path is manufactured, and the way it is manufactured decides what the results can contain and what they cannot.

There are five ways of manufacturing them. The result names the one it used, with its settings, in a short block — *What this simulation assumed* — but not what those settings imply. This page states it.

---

## 🧭 The Five Modes {: #the-five-modes }

On the **Risk** tab of the Dashboard and of a broker's page, the simulation is the third tool of **What if…?**, after the historical replay and the hypothetical shock. It offers five modes, each with its assumption written under its name:

| Mode | How the paths are made | Assumption added to the history |
|---|---|---|
| **Reshuffled history** — *Recommended*, the default | [Joint block bootstrap](#block-bootstrap) | None: your own returns, reordered in blocks |
| **Calm market** | Joint block bootstrap with a [regime](#prescribed-regimes) | Swings reduced by 30% for the whole horizon |
| **Prolonged crisis** | Joint block bootstrap with a regime | Swings ×2.5 and a level falling 20% a year, for 14 months |
| **Shock and recovery** | Joint block bootstrap with a regime | A 35% drop over the first two months, then the history as it was |
| **Normal curve (GBM)** — *Advanced* | [Geometric Brownian motion](#the-process) | Gaussian returns with a constant drift, volatility and correlation |

The first four draw real returns from the analysed window and differ only in the regime they declare on top of them; the last one draws from a model fitted to that window. A regime cannot be combined with the normal curve, and the list offers no such pair.

Beside the mode, the step asks for a **Horizon (days)** — 365 by default, at most 3 650 — and a number of **Simulation paths** — 8 192 by default, from 256 to 100 000 — and, for the normal curve only, a **Sampling strategy**. A **Random seed** fixes the draws — quasi-Monte Carlo needs none — so that the same inputs always give the same result. **Simulate** runs it. The answer gives the **Terminal mean return**, the **Probability of loss** — the share of paths that end below where they started — and the range from the 5th to the 95th percentile on the last day, above a cone that draws the 5th, 50th and 95th percentiles day by day.

The **Risk & Scenarios** tab of an asset's detail page still runs the normal curve alone, with Monte Carlo or quasi-Monte Carlo sampling.

<!-- [Screenshot Placeholder: risk/whatif-simulation — the Dashboard's What if…? simulation step with the beta notice and the model warning above the five modes, the horizon, paths and seed fields, and a result: terminal figures, cone and "What this simulation assumed"] -->

---

## 🧪 Why the Simulation Is Still in Beta {: #why-beta }

Every other part of Risk Analysis has left beta. The simulation step alone opens with a notice: *Simulation is still in beta. Its outcome depends heavily on how much history is requested relative to the horizon: a short window with a long horizon can produce implausible figures.* Below it, a second warning stays for good, because a model stays a model: *This is the only rung that is a model rather than a measurement. Read it as a range of possibilities, not a forecast.*

The defect behind the first notice is the ratio between the horizon $H$, counted in steps, and the $n$ observations of the window. A resampled path of $H$ steps reuses each observation $H/n$ times on average: from a quarter of history, a one-year horizon is that quarter, reshuffled and repeated about four times over, and whatever the quarter did — a rally, a calm spell, a slide — becomes the year. The normal curve does not escape it, because its drift and its volatility are the window's, carried forward unchanged however long the horizon. Requesting more history does not always cure it either: a holding with a short history shortens the shared window for all of them (see [Data Quality](data-quality.md#alignment-what-missing-data-actually-costs)). No guard on that ratio is applied yet, and until one is, the step stays in beta. The [uncertainty of the drift](#the-drift-is-an-estimate), shown beside every result, is that ratio at work.

---

## 🔁 Reshuffled History: the Joint Block Bootstrap {: #block-bootstrap }

The default mode estimates nothing. It takes the simple returns of the holdings over the analysed window, aligned on one shared calendar — one row per observation date, one column per holding — turns them into log returns $x_{s,i} = \ln(1 + r_{s,i})$, and builds every future out of **blocks** of consecutive rows of that matrix.

With $n$ observations in the window and blocks of $b$ observations, a path of $H$ steps is assembled from $\lceil H/b \rceil$ blocks. Each block starts at a row drawn uniformly at random among the $n$ and takes the $b$ rows from there, wrapping round from the last row to the first; the blocks are laid end to end and cut at $H$ steps. Holding $i$ grows along the path by the compounded sum of its drawn log returns, and the portfolio is today's composition held without rebalancing, its cash share $c$ earning nothing:

$$
G_i(s) = \exp\Big(\sum_{u=1}^{s} x_{u,i}\Big), \qquad R(s) = c + \sum_i w_i \, G_i(s) - 1
$$

where $w_i$ are today's weights and $R(s)$ is the portfolio's return after $s$ steps. Three properties follow from the construction:

- **Whole rows are drawn.** Each holding's return of a date travels with every other holding's return of the same date, so their co-movement is carried by construction: no covariance is estimated, inverted or checked, and none can fail.
- **Consecutive returns stay together inside a block.** Short-range dependence — a turbulent week, a run of quiet days — survives within each block, and is broken only at the joins.
- **Without a regime, every step happened.** The tails are the window's own, not a bell curve's: a single step cannot move further than the largest move the window recorded, and a path holds nothing the window did not contain.

### 📏 Calendar Days and Steps {: #calendar-days-and-steps }

The horizon is stated in calendar days, but the history is a sequence of observations: a series quoted on trading days holds about 252 of them a year, not 365. A horizon of $D$ calendar days is therefore converted at the window's observed frequency $f$, the number of observations it holds per year (see [Observed Annualization](observed-annualization.md)):

$$
H = \max\Big(1,\ \operatorname{round}\Big(\frac{D \, f}{365}\Big)\Big)
$$

The $H$ steps are simulated and then read back one point per calendar day: day $d$ shows step $\lfloor d \, H / D \rfloor$, so a day that falls between two steps repeats the one before — no trading, no move.

### 🧱 The Block Length {: #block-length }

Unless a block length is requested, it follows the moving-block rule of thumb, proportional to the cube root of the sample:

$$
b = \min\big(n,\ \max(2,\ \operatorname{round}(n^{1/3}))\big)
$$

That gives 6 observations for a year of trading days, and 9 for three years: long enough to carry volatility clustering across a few consecutive days, short enough to leave many distinct blocks to draw from. The result reports the length it used, converted back into calendar days, as *Block length*.

The analysis also accepts a requested length, `block_length_days`, from 1 to 5 000 calendar days, converted into observations at the same frequency $f$. The **What if…?** step does not offer it and always uses the rule above, so only a request sent straight to the analysis can set it — and only such a request can meet the refusal described under [Limits](#limits).

---

## 🌦️ Prescribed Regimes {: #prescribed-regimes }

*Calm market*, *Prolonged crisis* and *Shock and recovery* resample exactly as above, then transform each drawn log return during the regime's span:

$$
\tilde{x}_{s,i} = \bar{x}_i + k_s \, (x_{s,i} - \bar{x}_i) + \delta_s
$$

where $\bar{x}_i$ is holding $i$'s mean log return over the window, $k_s$ scales the swings around it and $\delta_s$ shifts their level. Outside the span, $k_s = 1$ and $\delta_s = 0$: the history is drawn as it was.

| Mode | Span | $k_s$ | $\delta_s$, per step |
|---|---|---|---|
| Calm market | the whole horizon | $0.7$ | $0$ |
| Prolonged crisis | the first 426 calendar days (14 months) | $2.5$ | $\ln(0.8)/f$ |
| Shock and recovery | the first 61 calendar days (2 months) | $1$ | $\ln(0.65)/m$ |

with $f$ the window's observed frequency and $m$ the number of steps the shock covers. Over a year of steps, the crisis shift compounds to a factor of $0.8$ — a level 20% lower each year than the history alone would give — on top of swings two and a half times as wide. The shock compounds to $0.65$, a 35% drop on top of the history, over its span, and always in full: on a horizon shorter than two months, the whole drop falls within the horizon. The spans are converted into steps the way the horizon is.

A regime is **declared, never estimated**: these numbers are the hypothesis, written down, not something measured from your data. Each step applies the same $k_s$ and the same $\delta_s$ to every holding, which leaves the correlations between them those of the history.

When the horizon is shorter than a regime's span, the regime covers the horizon only, and the result says so — for a crisis over a one-year horizon: *Declared over 426 days, applied over 365: the cone answers the shorter question.*

---

## 📈 The Normal Curve: Geometric Brownian Motion {: #the-process }

In the *Normal curve (GBM)* mode, every path comes from a **geometric Brownian motion**. For a single asset, the value $S_t$ evolves as

$$
dS_t = \mu S_t \, dt + \sigma S_t \, dW_t
$$

where $\mu$ is the drift, $\sigma$ the volatility and $W_t$ a Brownian motion, which is where the randomness enters. Each simulated asset starts at 1.0, so its path is a growth factor rather than a price, and it is advanced one day at a time until the horizon is reached.

Assets are not simulated separately and added up afterwards. They are assembled into a single process whose shocks are tied together by **one correlation matrix**, so that a move in one asset arrives accompanied by the moves its measured co-movement implies.

Integrating the equation gives the path in closed form:

$$
S_t = S_0 \exp\left(\left(\mu - \frac{\sigma^{2}}{2}\right) t + \sigma W_t\right)
$$

Two properties of this model do most of the work, and both are restrictions:

- **$\mu$ and $\sigma$ are constants.** Each takes one value and keeps it for the whole horizon, and so does every entry of the correlation matrix. Nothing in the simulation changes its own volatility, or its own correlations, as it runs.
- **The randomness enters through $W_t$ alone**, so over any interval the log return is normally distributed. The shape of the simulated returns is settled before the first path is drawn, and that shape is the bell curve.

The second property is the one to carry into everything below: the normal distribution is **thinner in the tails** than the returns markets actually produce, and the tails are what a risk simulation is read for.

---

## 🎲 Two Ways of Drawing the Same Model {: #sampling-strategies }

The **Sampling strategy** offered with the normal curve — and only with it — is between **Monte Carlo** and **quasi-Monte Carlo**. It is a choice about how the random numbers are produced, and about nothing else. The bootstrap has no such choice: it always draws the starts of its blocks from a seeded pseudo-random generator.

!!! warning "Two entries are not two models"

    A menu with two items invites the reading that there are two models available, and that one of them might suit a portfolio better than the other. There are not two. Both entries drive the same geometric Brownian motion, with the same drift, the same volatility and the same correlation matrix, and both draw **Gaussian** numbers to do it.

    Quasi-Monte Carlo buys **convergence**, not realism. Its low-discrepancy sequence covers the sample space more evenly than pseudo-random draws, so the estimate settles down with fewer paths. It does not simulate a different market, and it repairs none of the assumptions on this page.

What does differ is what each needs in order to be reproducible, and what each demands of the path count:

| | Monte Carlo | Quasi-Monte Carlo |
|---|---|---|
| Numbers drawn from | a pseudo-random generator | a Sobol low-discrepancy sequence |
| Reproduced by | a random seed | a start index in the sequence |
| Path count | no further requirement | must be a **power of two** |
| Additional limit | — | holdings × horizon days at most 21 201 — see [Limits](#limits) |

Both are fully reproducible: the same seed, or the same start index, regenerates the same paths. Neither accepts the other's parameter — a seed and a Sobol start index are mutually exclusive. The Dashboard shows no start index: it always enters the sequence at 0. The asset page's **Risk & Scenarios** tab lets you set it.

---

## 📐 Where the Parameters Come From {: #parameters }

In the normal curve, the model is supplied by measurement rather than by choice. The returns of the analysed window are converted to log returns, and from those:

- the **covariance** is the sample covariance, symmetrised and scaled to annual terms. Every observation in the window carries the same weight — a return from the first day counts exactly as much as one from the last;
- the **volatilities** are the square roots of its diagonal, and the **correlation matrix** is what remains once that scale is divided out;
- the scaling to annual terms uses the measured observed-span factor described in [Observed Annualization](observed-annualization.md), not a fixed convention.

The drift is the one parameter that is not simply the measured average:

$$
\mu = \bar{r}_{\log} \cdot f + \frac{\sigma^{2}}{2}
$$

with $\bar{r}_{\log}$ the mean log return per observation, $f$ the annualization factor and $\sigma^{2}$ the annual variance. The half-variance term is the Itô convexity correction. The drift parameter of the process is an expected *simple* growth rate, while what was measured is an average *log* return, and the two differ by exactly half the variance; adding it back is what makes the expected log growth of the simulated paths equal the average log return of the window. Without it, the paths would grow more slowly than the data they came from.

Cash is carried differently from the holdings, in every mode. It enters the portfolio path at its weight and stays there: the cash sleeve **earns exactly zero** across the whole horizon and contributes no variation of its own.

---

## 🧮 The Drift Is an Estimate {: #the-drift-is-an-estimate }

Whatever the mode, the centre of the cone rests on the window's average growth — the bootstrap draws every row with the same probability, the normal curve sets its drift from the same mean — and that average is a sample estimate, with a standard error of its own. The cone does not contain that error: it is the spread of the paths *given* the drift. So beside the result, a line states how far that error alone moves the median.

With $\hat{\sigma}$ the standard deviation of the portfolio's log return per observation over the $n$ observations of the window — cash counted at its weight, earning nothing — and $H$ the horizon in steps, the 95% factor is

$$
\varphi = \exp\left(z_{0.975} \, \frac{H \, \hat{\sigma}}{\sqrt{n}}\right), \qquad z_{0.975} \approx 1.96
$$

and the median $M$ of the last day is given the range $\big[(1 + M)/\varphi - 1,\ (1 + M)\,\varphi - 1\big]$: *The drift comes from … observations: that alone puts this median between … and ….* When $\varphi$ exceeds the spread of the cone itself, $(1 + P_{95})/(1 + P_{5})$, the line becomes an amber warning: the uncertainty about the drift alone is then wider than the band the simulation drew.

The exponent grows with $H$ and shrinks only with $\sqrt{n}$: doubling the horizon doubles it, while halving it takes four times as much history. That is the [ratio behind the beta notice](#why-beta), written as a number.

---

## 🚧 Limits {: #limits }

A simulation is refused, rather than run badly, in the cases below. The refusal is itself the result — the simulation comes back unavailable — and the banner of **What if…?** says why:

| Refusal | When | On screen | What to change |
|---|---|---|---|
| Too little history | Fewer than 30 observations in the window | *Insufficient history for this calculation.* | A longer date range |
| Block longer than the history | A requested block length spans more observations than the window holds | *Invalid calculation parameters.* | A shorter block, or a longer window |
| Sequence too large | Normal curve with quasi-Monte Carlo, when holdings × horizon days exceeds 21 201 | *This calculation is too large to run.* | A shorter horizon, a narrower scope with fewer holdings, or Monte Carlo sampling |
| Path count | Quasi-Monte Carlo with a path count that is not a power of two | *Invalid calculation parameters.* | A power of two: 4 096, 8 192, 16 384… |
| Size | Paths × (horizon days + 1) above 20 000 000; paths × horizon days × holdings above 200 000 000; or, for the bootstrap, window observations × holdings above 250 000 | *Invalid calculation parameters.* | Fewer paths, a shorter horizon, a shorter window or a narrower scope |

The second and third are refusals of a setting, not of your data. Their codes say so — invalid parameters rather than insufficient history, too large to run rather than a failure — and the message each returns names the setting. The block-length refusal states the length requested, the observations it spans and the observations the window holds: the remedy is a shorter block, since more history is often not to be had. The quasi-random refusal states the number of sequence dimensions it needs — one per holding and per day of the horizon — and the limit. At the default horizon of 365 days, the limit admits 58 holdings; at the longest, 3 650 days, it falls between five and six: five holdings need 18 250 dimensions, six need 21 900. Monte Carlo sampling has no such limit.

The size limits bind sooner than they seem. At the default 8 192 paths, any horizon beyond 2 440 days exceeds the first; at the default 365 days and 8 192 paths, a scope of 67 holdings or more exceeds the second.

---

## 💡 Interpretation {: #interpretation }

Read the output as what the mode implies, never as what is expected to happen:

- **Nothing in it is evidence.** A resampled path rearranges what the window contained; a model path is a consequence of the drift, the volatility and the correlations fed in. Neither carries information the window did not already hold, and a regime adds only the hypothesis it declares.
- **More paths reduce sampling error, not model error.** Raising the path count makes the result converge — to the answer *this mode* gives. No number of paths adds a crash the window did not contain, thickens a Gaussian tail or makes a fixed correlation move.
- **The centre of the distribution is an extrapolation.** It is the window's average growth carried forward unchanged — shifted, under a crisis or a shock, by the amount the regime declares. A window that rose produces futures that rise, for as long as the horizon runs, and how precisely that average is known is the [drift's uncertainty](#the-drift-is-an-estimate).
- **The spread is as wide as the window was, and no wider** — save for the factor a regime declares. A calm estimation period supplies calm swings and a comfortable co-movement, and the simulation then produces a calm future in perfectly good faith.

The figures that read what actually happened — [Value at Risk](value-at-risk.md), [Worst Realization](worst-realization.md), [Max Drawdown](max-drawdown.md) — are at least bounded by a history that occurred. A simulation is bounded only by its own assumptions. The normal curve can show a loss worse than anything on record, whose shape is the model's rather than the market's; a long resampled path can string bad blocks together into a fall the market never delivered in one stretch.

---

## ⚠️ Limitations {: #limitations }

!!! warning "The window is the only source"

    Every mode reads one window: the bootstrap reuses its rows, the normal curve fits its averages, and both weigh every observation equally, with no additional weight on recent ones. A window without a crash holds none to draw, and a window that rose is projected forward rising, however long the horizon. The window each result was computed on is published with it — see [Data Quality](data-quality.md).

!!! warning "The normal curve understates the tails"

    Real market returns produce extreme moves more often, and larger, than a normal distribution allows for. The *Normal curve (GBM)* mode, built on Gaussian increments, therefore reports rare outcomes as rarer and milder than they have historically been, and it does so most confidently at the far end of the distribution — the part a risk simulation exists to describe. [Value at Risk](value-at-risk.md) covers the same failure in its parametric form. The bootstrap keeps the window's own tails: no thinner, and no thicker.

!!! warning "Volatility clusters only as far as a block"

    In the normal curve, volatility is a single number for the entire horizon, so a bad day does not make the following day any more likely to be bad. The bootstrap keeps the window's clustering inside each block, a few days long, and loses it at the joins: a resampled turbulent spell lasts about as long as a block, not as long as the one it came from, unless a *Prolonged crisis* declares one. Real markets behave otherwise: turbulent periods arrive in runs, and crises persist. A simulated worst stretch is not the same object as a historical crisis and should not be compared with one.

!!! warning "Correlations never break"

    The normal curve applies one correlation matrix to every future; the bootstrap carries the window's own co-movement, and the regimes leave it unchanged by design. Neither can produce, unless the window contains it, the event that most damages a diversified portfolio: correlations rising towards one exactly when markets fall, leaving holdings that had been offsetting each other to fall together instead. [Correlation](correlation.md) covers the measured version, and how much it depends on the window it was taken from.

!!! warning "Cash stands still, and nothing else happens"

    The cash portion of the portfolio neither grows nor varies over the horizon, whatever it might earn in reality, and the composition is held without rebalancing. Costs, cash flows and inflation are left out too: the result lists them under *Left out of the cone*. The longer the horizon, the more these simplifications matter.

---

## 🔗 Related {: #related }

- 📊 **[Volatility](volatility.md)** — the dispersion measure the normal curve takes as one of its two parameters
- 🔗 **[Correlation](correlation.md)** — the co-movement structure the simulation holds fixed across every path
- 📅 **[Observed Annualization](observed-annualization.md)** — the measured frequency that turns calendar days into steps, and the window's statistics into annual ones
- 📉 **[Value at Risk](value-at-risk.md)** — the same tail question answered from observed returns instead of generated ones
- ⏮️ **[Historical Replay](historical-replay.md)** — a real episode applied to the current portfolio, where nothing is generated
- 🧪 **[Data Quality](data-quality.md)** — the window and observation count the parameters were estimated from
