# 📉 Max Drawdown

Max Drawdown (MDD) measures the **largest peak-to-trough decline** in portfolio value before a new peak is established. It answers the question: *"What was the worst loss an investor could have experienced?"*

---

## 🔢 Formula {: #formula }

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

where $V_t$ is the portfolio value at time $t$.

The drawdown at any point $t$ is:

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

Max drawdown is the minimum (most negative) value of $DD_t$ over the entire observation period.

---

## 💡 Interpretation {: #interpretation }

| Max Drawdown | Typical Context |
|---|---|
| $-5\%$ to $-10\%$ | Normal correction, well-diversified portfolio |
| $-10\%$ to $-20\%$ | Significant correction |
| $-20\%$ to $-30\%$ | Bear market territory |
| $-30\%$ to $-50\%$ | Severe bear market (2008, COVID-2020) |
| $> -50\%$ | Catastrophic (concentrated positions, crypto) |

!!! example "Numerical example"

    Portfolio value sequence: 100 → 120 → 90 → 110 → 130

    - Peak: 120
    - Trough: 90
    - MDD: $(90 - 120) / 120 = -25\%$
    - Recovery: reached 120 again, then new high at 130

---

## ⏱️ Recovery Time {: #recovery-time }

An equally important metric is **recovery time** — how long the portfolio stayed below a peak it had already reached. The clock starts at the **peak**, not at the trough: it begins the day the portfolio leaves its high-water mark and stops only when that mark is reached again.

$$
T_{recovery} = t_{recovery} - t_{peak}
$$

The decline is therefore part of the count, and the duration is expressed in **calendar days** between those two dates. The worst episode is always reported together with its state, and the state decides what else can be said about it:

| Recovery state | What it means | What comes with it |
|---|---|---|
| *recovered* | The previous peak was reached again | Peak, trough and recovery dates; the duration is final |
| *open* | The peak has not been reached again within the observed period | Peak and trough dates, and **no recovery date**; the duration is still running |
| *no drawdown* | The portfolio never closed below a previous peak | No dates and no recovered fraction; depth and duration are zero |

These are not presentation conventions: the combinations are enforced on the result itself, so an open episode cannot carry a recovery date, and an episode that never happened cannot carry a partial recovery.

!!! info "When the drawdown is still open"

    If the peak has not been reached again by the end of the observed period there is no recovery date, and the duration is measured up to the last observation instead:

    $$
    T_{open} = t_{last} - t_{peak}
    $$

    This figure **grows with every day that passes** while the portfolio remains below the peak: the number is not drifting, the episode simply has not ended yet.

    An open episode also carries a **recovered fraction** between $0$ and $1$: how much of the fall, measured from the trough, has already been climbed back. It is a progress reading rather than a verdict — the part of the descent that has been undone so far — and it is the figure that answers the question an investor still underwater is actually asking.

!!! warning "Why the count starts at the peak"

    Measuring only the climb back — from the trough to a new peak — always yields a **smaller** number, because it discards the decline itself. But the investor was already below the high-water mark while the portfolio was falling: that stretch is not a prelude to the loss, it is the loss happening. Starting the count at the peak reports the whole period spent underwater, which is the period the investor actually had to live through.

Historical context, by asset class:

| Asset Class | Typical Recovery Time (after major drawdown) |
|-------------|---------------------------------------------|
| US Stocks (S&P 500) | 1-5 years |
| Bonds | Months to 1-2 years |
| Crypto | Highly variable (months to years) |

These figures are general market history, not a LibreFolio measurement, and the basis on which they were counted is not stated — published recovery times are sometimes measured from the trough and sometimes from the peak. They are therefore **not directly comparable** with the duration reported above, which always counts from the peak and so covers a longer stretch than a trough-based figure for the same episode.

!!! warning "Asymmetry of losses"

    A 50% loss requires a **100% gain** to recover:

    $$
    \text{Required gain} = \frac{1}{1 + MDD} - 1
    $$

    <div style="display: flex; justify-content: center;">

    | Loss | Required Gain |
    |:----:|:-------------:|
    | -10% | +11.1% |
    | -25% | +33.3% |
    | -50% | +100% |
    | -75% | +300% |

    </div>

The table above is the general arithmetic of the asymmetry, tabulated against the depth of the **maximum** drawdown. The figure the system computes applies that same formula to the **current** drawdown instead: it answers how much gain is needed to return to the peak *from where the portfolio stands today*, which is the only version of the question that can be acted on. The two readings coincide only when the portfolio happens to be sitting at its deepest point ever — see [Current Drawdown](current-drawdown.md).

---

## 📊 Drawdown Chart {: #drawdown-chart }

A drawdown chart plots $DD_t$ over time. It's always zero or negative, touching zero at each new peak. The deepest valley is the max drawdown. This visualization makes it easy to:

- Identify the **timing** of worst-case periods
- See how frequently drawdowns occur
- Compare recovery patterns across different strategies

---

## 🔗 Related {: #related }

- 📊 **[Volatility](volatility.md)** — Standard deviation doesn't capture drawdown severity
- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Risk-adjusted return (uses volatility, not drawdown)
- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — The primary tool for reducing max drawdown
