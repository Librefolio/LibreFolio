# 🎲 Simulation Modes

The simulation projects a portfolio forward by generating a large number of possible futures and reading the distribution of where they arrive. It is the one place in this section where **nothing in the output happened**: every path is manufactured by a model, and that model's assumptions decide what the results can contain and what they cannot.

Those assumptions are not visible in the output. This page states them.

---

## 🔢 The Process {: #the-process }

Every path comes from a **geometric Brownian motion**. For a single asset, the value $S_t$ evolves as

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

The choice offered alongside the simulation is between **Monte Carlo** and **quasi-Monte Carlo**. It is a choice about how the random numbers are produced, and about nothing else.

!!! warning "Two entries are not two models"

    A menu with two items invites the reading that there are two models available, and that one of them might suit a portfolio better than the other. There are not two. Both entries drive the same geometric Brownian motion, with the same drift, the same volatility and the same correlation matrix, and both draw **Gaussian** numbers to do it.

    Quasi-Monte Carlo buys **convergence**, not realism. Its low-discrepancy sequence covers the sample space more evenly than pseudo-random draws, so the estimate settles down with fewer paths. It does not simulate a different market, and it repairs none of the assumptions on this page.

What does differ is what each needs in order to be reproducible, and what each demands of the path count:

| | Monte Carlo | Quasi-Monte Carlo |
|---|---|---|
| Numbers drawn from | a pseudo-random generator | a Sobol low-discrepancy sequence |
| Reproduced by | a random seed | a start index in the sequence |
| Path count | no further requirement | must be a **power of two** |
| Additional limit | — | the asset count multiplied by the horizon length is capped |

Both are fully reproducible: the same seed, or the same start index, regenerates the same paths. Neither accepts the other's parameter — a seed and a Sobol start index are mutually exclusive.

---

## 📐 Where the Parameters Come From {: #parameters }

The model is supplied by measurement rather than by choice. The returns of the analysed window are converted to log returns, and from those:

- the **covariance** is the sample covariance, symmetrised and scaled to annual terms. Every observation in the window carries the same weight — a return from the first day counts exactly as much as one from the last;
- the **volatilities** are the square roots of its diagonal, and the **correlation matrix** is what remains once that scale is divided out;
- the scaling to annual terms uses the measured observed-span factor described in [Observed Annualization](observed-annualization.md), not a fixed convention.

The drift is the one parameter that is not simply the measured average:

$$
\mu = \bar{r}_{\log} \cdot f + \frac{\sigma^{2}}{2}
$$

with $\bar{r}_{\log}$ the mean log return per observation, $f$ the annualization factor and $\sigma^{2}$ the annual variance. The half-variance term is the Itô convexity correction. The drift parameter of the process is an expected *simple* growth rate, while what was measured is an average *log* return, and the two differ by exactly half the variance; adding it back is what makes the expected log growth of the simulated paths equal the average log return of the window. Without it, the paths would grow more slowly than the data they came from.

Cash is carried differently from the holdings. It enters the portfolio path at its weight and stays there: the cash sleeve **earns exactly zero** across the whole horizon and contributes no variation of its own.

---

## 💡 Interpretation {: #interpretation }

Read the output as what the model implies, never as what is expected to happen:

- **Nothing in it is evidence.** A simulated path is a consequence of the drift, the volatility and the correlations fed in. It carries no information those inputs did not already contain.
- **More paths reduce sampling error, not model error.** Raising the path count makes the result converge — to the answer *this model* gives. No number of paths thickens a Gaussian tail or makes a fixed correlation matrix move.
- **The centre of the distribution is an extrapolation.** The drift is the window's average growth carried forward unchanged. A window that rose produces futures that rise, for as long as the horizon runs.
- **The spread is as wide as the window was, and no wider.** A calm estimation period supplies a low volatility and a comfortable correlation matrix, and the simulation then produces a calm future in perfectly good faith.

The figures that read what actually happened — [Value at Risk](value-at-risk.md), [Worst Realization](worst-realization.md), [Max Drawdown](max-drawdown.md) — are at least bounded by a history that occurred. A simulation is bounded only by its own assumptions, which is why it can show a loss worse than anything on record, and why the shape of that loss is the model's rather than the market's.

---

## ⚠️ Limitations {: #limitations }

!!! warning "Gaussian returns understate the tails"

    Real market returns produce extreme moves more often, and larger, than a normal distribution allows for. A simulation built on Gaussian increments therefore reports rare outcomes as rarer and milder than they have historically been, and it does so most confidently at the far end of the distribution — the part a risk simulation exists to describe. [Value at Risk](value-at-risk.md) covers the same failure in its parametric form.

!!! warning "Constant volatility means no clustering"

    Volatility is a single number for the entire horizon, so in this model a bad day does not make the following day any more likely to be bad. Real markets behave in the opposite way: turbulent periods arrive in runs, and crises persist. A simulated worst stretch is a run of independent unlucky draws, which is not the same object as a historical crisis and should not be compared with one.

!!! warning "One correlation matrix for every future"

    Correlations are fixed for the whole horizon, so the model cannot produce the event that most damages a diversified portfolio: correlations rising towards one exactly when markets fall, leaving holdings that had been offsetting each other to fall together instead. [Correlation](correlation.md) covers the measured version, and how much it depends on the window it was taken from.

!!! warning "The estimation window becomes the future"

    Drift, volatilities and correlations are all equally weighted averages over the analysed window, with no additional weight on recent observations. That window is projected forward unchanged, however long the horizon. The window each result was computed on is published with it — see [Data Quality](data-quality.md).

!!! warning "Cash stands still"

    The cash portion of the portfolio neither grows nor varies over the horizon, whatever it might earn in reality. A portfolio holding a large cash balance is simulated as though that part of it were frozen for the entire period, and the longer the horizon, the more that simplification matters.

---

## 🔗 Related {: #related }

- 📊 **[Volatility](volatility.md)** — the dispersion measure the simulation takes as one of its two parameters
- 🔗 **[Correlation](correlation.md)** — the co-movement structure held fixed across every path
- 📅 **[Observed Annualization](observed-annualization.md)** — the measured factor that turns the window's statistics into annual ones
- 📉 **[Value at Risk](value-at-risk.md)** — the same tail question answered from observed returns instead of generated ones
- ⏮️ **[Historical Replay](historical-replay.md)** — a real episode applied to the current portfolio, where nothing is generated
- 🧪 **[Data Quality](data-quality.md)** — the window and observation count the parameters were estimated from
