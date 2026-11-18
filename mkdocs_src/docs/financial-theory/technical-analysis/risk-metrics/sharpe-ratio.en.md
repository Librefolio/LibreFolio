# 📐 Sharpe Ratio

The Sharpe ratio is the most widely used **risk-adjusted return** metric. It measures how much excess return you receive per unit of total volatility.

---

## 🔢 Formula {: #formula }

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

where:

- $R_p$ = portfolio return (annualized)
- $R_f$ = risk-free rate (e.g., Treasury bill rate)
- $\sigma_p$ = portfolio standard deviation (annualized)

!!! info "How the rate enters the calculation"

    The risk-free rate is supplied as an **effective annual** rate and converted to an **effective per-period** rate before use:

    $$
    r_{period} = (1 + r_{annual})^{1/f} - 1
    $$

    where $f$ is the same annualization factor that scales the volatility, measured from the observed data — see [Annualization](#annualization). That per-period rate is subtracted from each period return, and the resulting excess returns are what the ratio is built on. Sharing $f$ with the volatility keeps the numerator and the denominator on the same period: charging a calendar-day rate against trading-day returns would understate the charge and, when the rate is positive, flatter the ratio. The conversion is compounding-aware: a plain $r_{annual}/f$ would treat the rate as if it did not compound over the year.

---

## 🏦 The Risk-Free Rate {: #risk-free-rate }

Since release 1.4 the reader sets **one fixed annual rate**, in the field under the period line of every risk page. It is 0% until it is set. The value is kept in the browser, per account, and travels with each request: the backend stores nothing.

### 🎯 One Threshold for Every Excess Measure {: #one-threshold }

The same value is used everywhere a measure asks "above what?":

| Measure | Role of the rate | Engine parameter |
|---|---|---|
| [Sharpe ratio](#formula) | $R_f$, subtracted from every return | `risk_free_annual_rate` |
| [Sortino ratio](sortino-ratio.md) | The threshold of the numerator and of the downside deviation | `target_annual_return` |
| [Gains against losses (Omega)](omega-ratio.md) | The cut between gains and shortfalls | `target_annual_return` |
| Semi-deviation ([downside deviation](sortino-ratio.md#downside-deviation)) | The level below which a return counts as a shortfall | `target_annual_return` |

The engine still declares the two parameters separately; the app fills both from the one rate, so a Sharpe and the Sortino beside it never charge two different rates. The three rolling signals of the asset chart that take a rate — **Rolling Sharpe Ratio**, **Rolling Semi-deviation** and **Rolling Gains / Losses (Omega)** — read the same value: their rate parameter is declared with `x-control: "risk_free_rate"`, so the chart shows the reader's rate in place of a field.

The analytics that take the rate — `historical_kpi`, `asset_set_kpi`, `comparison`, `asset_set_comparison` and `asset_risk_return` — echo the rate they were charged in `metadata.risk_free.annual_rate`. What a page writes as "the rate used" is read from there, not from the field: between a change and the new answer the two differ.

### 📏 Why a Short Rate, Not a Long Bond {: #why-a-short-rate }

The rate the ratio needs is the return of an investment with **no** risk over the measurement period. The closest observable is the yield of a **short** government bill — for instance the latest yield of a 12-month Treasury bill, or the equivalent bill of the currency the analysis is measured in.

A 10-year government bond yield is not a substitute:

- **It pays a term premium.** Holding a long bond exposes the investor to interest-rate risk: its price falls when yields rise. Its yield includes a compensation for that risk, so it is already a risky return, not a risk-free one.
- **For a single country it carries credit risk.** The yield of one issuer's long bond includes a premium for the chance that the issuer does not pay, which a short bill of a highly rated issuer carries far less of.
- **It usually sits above short rates.** With an upward-sloping yield curve — the usual shape, though not the only one — the long yield exceeds the bill yield, and using it raises the charge on every return.

The effect on the ratio is direct. The Sharpe ratio falls by approximately the difference of the two rates divided by the annual volatility:

$$
\Delta S \approx -\frac{\Delta R_f}{\sigma_p}
$$

!!! example "A one-point difference in the rate"

    An asset with an annual volatility of 14%, measured with a rate of 3.5% instead of 2.5%:

    $$
    \Delta S \approx -\frac{0.035 - 0.025}{0.14} \approx -0.07
    $$

    The asset did not change; its Sharpe ratio dropped by about 0.07 because the bar it is measured against was raised by a premium that is not risk-free. (The compounding-aware conversion above gives $-0.069$.)

!!! warning "One constant over the whole window"

    The rate is a single fixed annual figure applied to every day of the period, not a historical series of rates. Over a window that spans different rate regimes — years near zero followed by years of high rates — it is an approximation, and the reading of the ratio inherits it. Set it to the rate that best represents the period being measured.

---

## 💡 Interpretation {: #interpretation }

| Sharpe Ratio | What the value means |
|---|---|
| $< 0$ | The portfolio returned less than the risk-free rate over the window: the excess return in the numerator is negative, so no level of volatility can turn the ratio positive |
| $0 - 0.5$ | Less than half a unit of excess return per unit of volatility: the portfolio moved a great deal relative to what that movement earned |
| $0.5 - 1.0$ | Between half a unit and one unit of excess return per unit of volatility |
| $1.0 - 2.0$ | One to two units of excess return per unit of volatility: the excess return was larger than the volatility that produced it |
| $> 2.0$ | More than two units of excess return per unit of volatility — uncommon over long periods, much less so over short and favourable ones |

!!! warning "The same number is not the same statement"

    A ratio means nothing detached from the window and the asset class it was measured on. A short, favourable stretch produces values that a full market cycle would not sustain, and asset classes with different return rhythms occupy different parts of the scale by construction. Two ratios are comparable only when they cover the same period and were annualised on the same observed factor — see [Observed Annualization](observed-annualization.md). The table says what the number *is*, not whether the result was good: that judgement needs the objective the portfolio was built for.

!!! example "Numerical example"

    Portfolio return: 12%, Risk-free rate: 3%, Volatility: 15%

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    For every 1% of volatility, the portfolio earned 0.60% of excess return.

---

## ⚙️ Annualization {: #annualization }

A Sharpe ratio computed on per-period returns is scaled to an annual figure by the square root of the number of periods a year contains:

$$
S_{annual} = S_{period} \times \sqrt{f}
$$

The factor $f$ is **measured from the observed data** — the number of returns actually used, rescaled to a full calendar year over the span they cover:

$$
f = \frac{N \times 365}{D}
$$

where $N$ is the number of period returns and $D$ the calendar days they span. The square root comes from variance adding across independent periods, so the scaling assumes returns are IID (independent and identically distributed) — an approximation that breaks down for autocorrelated returns.

!!! info "√252 is a result, not a constant"

    A daily-priced stock contributes roughly 252 returns over a full calendar year, so $f \approx 252$ and the familiar $\sqrt{252}$ is recovered as the outcome of the measurement rather than written into it. An instrument priced every calendar day gives $f \approx 365$ instead, and a weekly-priced fund $f \approx 52$.

    → See **[Observed Annualization](observed-annualization.md)** for the derivation and worked examples.

---

## ⚠️ Limitations {: #limitations }

### 📊 Symmetric Penalty {: #symmetric-penalty }

The Sharpe ratio penalizes **upside volatility** as much as downside volatility. An asset that frequently spikes upward (highly desirable!) will have a lower Sharpe ratio than one with the same return and less upside movement.

→ For asymmetric return distributions, prefer the **[Sortino Ratio](sortino-ratio.md)**.

### 📈 Sensitivity to Outliers {: #sensitivity-to-outliers }

A few extreme returns can significantly distort the standard deviation, making the Sharpe ratio unstable for short time periods.

### 🔄 Time-Period Dependency {: #time-period-dependency }

The Sharpe ratio can vary dramatically depending on the lookback window. A strategy with an excellent 5-year Sharpe may have a poor 1-year Sharpe (or vice versa).

---

## 🔗 Related {: #related }

- 📊 **[Sortino Ratio](sortino-ratio.md)** — Downside-only variant
- ➗ **[Gains Against Losses (Omega)](omega-ratio.md)** — Gains above the same rate against shortfalls below it
- 📊 **[Volatility](volatility.md)** — The denominator of the Sharpe ratio
- 📈 **[Returns](../../fundamentals/returns.md)** — The numerator of the Sharpe ratio


