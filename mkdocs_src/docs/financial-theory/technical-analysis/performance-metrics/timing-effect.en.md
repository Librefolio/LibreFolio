# ⏱️ Timing Effect

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is it?

The **Timing Effect** measures how much the timing and size of your deposits and withdrawals (cash flows) have impacted your personal return as an investor compared to the return of the underlying strategy, neutralizing the effect of external cash flows.

It is calculated as the difference between your money-weighted cumulative return and your time-weighted cumulative return:

$$
\text{Timing Effect} = \text{MWRR}_{\text{cumulative}} - \text{TWRR}_{\text{cumulative}}
$$

It is expressed in **percentage points (pp)**.

---

## 🧮 How to Interpret the Timing Effect

By comparing [Cumulative MWRR](mwrr.md#cumulative-mwrr) (which includes cash flow timing) with [Cumulative TWRR](twrr.md) (which neutralizes cash flow timing), the Timing Effect highlights the difference between the investor's personal return and the strategy's return, attributable to the timing and size of cash flows:

- **Positive Timing Effect ($> 0$ pp):** Your cash flows occurred at favorable times (e.g., buying assets at a discount during a market dip). Your personal return (MWRR) is higher than the pure strategy return (TWRR).
- **Negative Timing Effect ($< 0$ pp):** Your cash flows occurred at unfavorable times (e.g., depositing large sums at the peak of the market right before a correction). Your personal return (MWRR) is lower than the pure strategy return (TWRR).
- **Near-Zero Timing Effect ($\approx 0$ pp):** Your cash flows had little to no impact on performance (e.g., if you made very small deposits or if the market remained flat during your transactions).

---

## 🔢 Numerical Examples

### Example 1: Positive Timing Effect (Favorable Inflows)
* **Cumulative TWRR (Strategy Performance):** $+20\%$
* **Cumulative MWRR (Investor Performance):** $+28\%$

$$
\text{Timing Effect} = 28\% - 20\% = +8\text{ pp}
$$

* **Interpretation:** The underlying asset strategy generated a return of $+20\%$. However, because you added a significant amount of capital to the portfolio before the market surged, your personal money-weighted return increased to $+28\%$. The timing and size of your inflows contributed **$+8$ percentage points** of additional performance.

### Example 2: Negative Timing Effect (Unfavorable Inflows)
* **Cumulative TWRR (Strategy Performance):** $+20\%$
* **Cumulative MWRR (Investor Performance):** $+12\%$

$$
\text{Timing Effect} = 12\% - 20\% = -8\text{ pp}
$$

* **Interpretation:** The underlying asset strategy generated a return of $+20\%$. However, you added significant capital near the market peak right before a decline. This concentrated more of your money during a period of poor performance, dragging your personal money-weighted return down to $+12\%$. Your timing reduced your return by **$-8$ percentage points**.

---

## ⚖️ What it Captures vs. What it Does Not

### What it Captures
- **Impact of Deposit/Withdrawal Timing:** Whether you added cash during market troughs (buying low) or peaks (buying high).
- **Impact of Flow Sizes:** Larger cash flows have a stronger weighting and a greater impact on the MWRR, which the Timing Effect reflects.
- **The "Investor Gap":** the distance between the strategy return and the return actually achieved by the investor, due to the timing and size of the cash flows.

### What it Does Not Capture
- **Absolute Monetary Profit:** A positive Timing Effect of $+5$ pp can exist even if the portfolio is in a net loss (e.g., TWRR is $-20\%$ and MWRR is $-15\%$). Use [Period P&L](period-pnl.md) to evaluate monetary gains.
- **Risk and Volatility:** It does not indicate the risk profile or volatility of the assets.
- **Disaggregated impact of taxes and costs:** the Timing Effect does not break down taxes and costs; any costs and taxes may be shown separately in the Period P&L.
- **Pure Quality of the Assets:** A high Timing Effect can occur on a poor asset if you buy right before a temporary bounce. Always check [TWRR](twrr.md) to judge the asset quality.

---

## 🖥️ UI Integration & Dashboard Usage
LibreFolio displays the Timing Effect on the **Returns** dashboard card. This card aggregates the key indicators of your investment performance:

- **Timing Effect:** Difference between Cumulative MWRR and Cumulative TWRR, showing how your cash flows affected your returns.
- **Simple ROI:** intuitive percentage return for the period. It is useful for a quick check on performance, but does not account for the timing of cash flows with the same precision as MWRR.
- **Cumulative TWRR:** Return of the underlying strategy, neutralizing cash flow impacts.
- **Cumulative MWRR:** Return of your actual capital, accounting for cash flows.
- **Annualized MWRR:** The annualized compound rate of growth of your money.

!!! note "Tooltip Helper"

    Difference between Cumulative MWRR and Cumulative TWRR. Shows how much the timing and size of your cash flows impacted your overall return.


---

## 🔗 Related Performance Metrics

- **[Simple ROI](roi.md):** Measures the absolute percentage gain or loss relative to the capital invested.
- **[TWRR](twrr.md):** Measures the return of the underlying strategy or assets, ignoring the investor's cash flow timing.
- **[MWRR](mwrr.md):** Measures the return of the investor's capital, factoring in both asset performance and cash flow timing.
- **[Period P&L](period-pnl.md):** Measures the absolute fiat profit or loss generated by the portfolio within the selected time window.
