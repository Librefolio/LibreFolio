# 📊 Sortino Ratio

The Sortino ratio is a modification of the Sharpe ratio that only penalizes **downside volatility**. It recognizes that investors are primarily concerned with losses, not with upside surprises.

---

## 🔢 Formula {: #formula }

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

where:

- $R_p$ = portfolio return (annualized)
- $R_f$ = risk-free rate (or minimum acceptable return)
- $\sigma_d$ = **downside deviation** (annualized)

!!! info "How the threshold enters the calculation"

    The threshold — the minimum acceptable return — is supplied as an **effective annual** rate and converted to an **effective daily** rate through the same conversion the Sharpe ratio uses:

    $$
    r_{daily} = (1 + r_{annual})^{1/365} - 1
    $$

    That daily threshold is then subtracted from each daily return, both in the excess returns and inside the downside deviation below, so a single definition of "acceptable" governs the numerator and the denominator alike.

### 📐 Downside Deviation {: #downside-deviation }

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Only returns **below** the threshold contribute to downside deviation. Returns above the threshold contribute zero.

---

## ⚖️ Two Downside Conventions {: #two-downside-conventions }

Two different quantities are commonly called "downside deviation", and they differ in two ways — one negligible, one decisive.

| | Reference point | Divisor |
|---|---|---|
| **Threshold convention** (used here) | A **chosen** threshold — the minimum acceptable return | $N$, every observation |
| **Mean convention** | The **sample mean of the series itself** | $N - 1$, the observations minus one |

**The divisor is the negligible difference.** When the threshold happens to coincide with the sample mean, the two results differ only by the factor $\sqrt{N/(N-1)}$ — over a year of daily observations, roughly two parts in a thousand. It is a bookkeeping choice, not a change of meaning.

**The reference point is the decisive one**, and the gap it opens has no upper bound. The following values follow directly from the two definitions applied to constructed series — they are arithmetic a reader can reproduce, not output of a LibreFolio run:

| Series over 250 observations | Mean convention | Threshold convention (threshold $= 0$) |
|---|---|---|
| **Loses exactly 0.5% every day** | **0.000000** | **0.005000** |
| Alternates $+1\%$ and $-1\%$ around zero | 0.007085 | 0.007071 |
| Gains exactly 0.5% every day | 0.000000 | 0.000000 |

The first row is the whole argument. A portfolio that loses half a percent **every single day for a year** never deviates from its own average, because its average *is* that daily loss — so the mean convention measures its downside risk as exactly zero. The threshold convention, asked how far the series fell below zero, answers that it fell below on every one of the 250 days.

!!! warning "They are not two estimates of the same quantity"

    The two conventions answer different questions. Measuring against the series' own mean asks *how inconsistent am I relative to myself*; measuring against a chosen threshold asks *how far do I fall below what I asked for*. Only the second can report that losing steadily is a risk — the first, by construction, cannot see a loss that never varies.

    Neither is wrong in general. The mean convention belongs naturally to portfolio optimization, where the quantity being minimised is dispersion around whatever mean the allocation achieves. The question this page is about is the other one: the threshold is something the investor states in advance, and the ratio reports the result against it.

LibreFolio uses the **threshold convention with the $N$ divisor** — the formula given above. The threshold is an explicit parameter of the analysis and is zero unless it is set to something else, so by default the question asked is *how far did the portfolio fall below break-even, and was its result above it*.

---

## 💡 Interpretation {: #interpretation }

| Sortino Ratio | What the value means |
|---|---|
| $< 0$ | The return fell short of the threshold: the numerator is negative whatever the downside deviation turned out to be |
| $0 - 1.0$ | Less than one unit of excess return per unit of downside deviation |
| $1.0 - 2.0$ | One to two units of excess return per unit of downside deviation |
| $> 2.0$ | More than two units of excess return per unit of downside deviation — uncommon over long periods, much less so over short and favourable ones |

!!! warning "Read the scale before reading the number"

    These ranges are expressed in units of **downside** deviation, so a Sortino and a Sharpe with the same numeric value are not the same statement about a portfolio. And as with any ratio of this family, the value depends on the window and on the asset class it was measured on: a short favourable stretch and a full market cycle do not produce comparable figures, even for the same portfolio. The table says what the number *is*, not whether it is good.

!!! example "Numerical example"

    Portfolio return: 12%, Risk-free rate: 3%, Downside deviation: 10%

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Compare with Sharpe (if total σ = 15%): $S = 0.60$. The Sortino is higher because upside volatility is excluded.

---

## 📊 Sharpe vs Sortino {: #sharpe-vs-sortino }

| Aspect | Sharpe | Sortino |
|--------|--------|---------|
| **Risk measure** | Total standard deviation | Downside deviation only |
| **Penalizes upside?** | Yes ❌ | No ✅ |
| **Best for** | Symmetric return distributions | Asymmetric / skewed returns |
| **Example** | Broad market index | Options strategies, concentrated portfolios |

### 🔑 When to Prefer Sortino {: #when-to-prefer-sortino }

- **Skewed distributions**: Strategies that have occasional large gains but controlled losses
- **Options-based portfolios**: Inherently asymmetric payoffs
- **Growth stocks**: Tend to have positively skewed return distributions
- **Any investor** who cares about downside risk more than total risk

---

## ⚠️ Limitations {: #limitations }

!!! warning "Small sample bias"

    Downside deviation requires sufficient data points below the threshold. With few negative returns (e.g., short bull market periods), the estimate becomes unreliable and the Sortino ratio can be misleadingly high.

---

## 🔗 Related {: #related }

- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Total volatility variant
- 📊 **[Volatility](volatility.md)** — Understanding standard deviation
- 📈 **[Max Drawdown](max-drawdown.md)** — Another downside-focused metric


