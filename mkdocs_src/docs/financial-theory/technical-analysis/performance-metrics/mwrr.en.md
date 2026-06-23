# 💵 MWRR (Money-Weighted Rate of Return) / XIRR

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is it?
MWRR (also known as Internal Rate of Return) measures **your personal** performance as an investor. Unlike asset-only metrics, it accounts for both the performance of the underlying assets and the **timing and size** of your deposits and withdrawals. 

To provide complete visibility, LibreFolio distinguishes between two forms of this metric: **Annualized MWRR** and **Cumulative MWRR**.

---

## 📈 Annualized MWRR vs. Cumulative MWRR

### Annualized MWRR {: #annualized-mwrr }
Annualized MWRR is the compound annual rate of return that makes the Net Present Value (NPV) of all cash flows equal to zero. 

This compound rate is mathematically equivalent to the **CAGR** (Compound Annual Growth Rate) of your actual invested money, representing the smoothed annual growth rate required for the capital to grow to the final balance, accounting for all intermediate movements.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
$$

??? note "🧮 How the NPV Equation is Unfolded"

    #### 1. Intuitive Final Value Form
    Imagine trying to project your final Net Asset Value (NAV) by growing each cash flow by a compound rate \(r\):
    
    \[
    NAV_{final} = CF_0 \times (1 + r)^{\frac{d_0}{365}} + CF_1 \times (1 + r)^{\frac{d_1}{365}} + \dots + CF_n \times (1 + r)^{\frac{d_n}{365}}
    \]
    
    Where \(d_i\) represents the number of days each cash flow was invested during the period.
    
    #### 2. Discounting to Net Present Value (NPV = 0)
    By dividing both sides of the equation by \((1 + r)^{\frac{\text{total days}}{365}}\), we shift all cash flows back to the start of the period (\(t_0\)). This gives us the standard Net Present Value equation where the sum of discounted cash flows equals zero:
    
    \[
    0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
    \]
    
    Where \(t_i\) is the number of days from the start of the period to the date of cash flow \(i\).
    
    #### 3. Example of Unfolding Cash Flows
    Let's see how cash flows populate for a portfolio over a 31-day period:
    
    * **Day 0:** Starting value of the portfolio is €1,000 (represented as a deposit/investment).
    * **Day 15:** You deposit €100.
    * **Day 31:** Final portfolio NAV is €1,150.
    
    First, we construct the transaction table from the investor's perspective (money going into the portfolio is negative, money coming back is positive):
    
    | Step (\(i\)) | Day (\(t_i\)) | Event | Wallet Cash Flow (\(CF_i\)) |
    |------------|-------------|-------|---------------------------|
    | 0 | 0 | Initial Balance | **-€1,000** (Outflow) |
    | 1 | 15 | Deposit | **-€100** (Outflow) |
    | 2 | 31 | Hypothetical Liquidation (NAV) | **+€1,150** (Inflow) |
    
    Now, we splay/unfold these transactions into the NPV summation:
    
    \[
    0 = -1000 + \frac{-100}{(1+r)^{\frac{15}{365}}} + \frac{1150}{(1+r)^{\frac{31}{365}}}
    \]
    
    The mathematical solver iteratively searches for the value of \(r\) (Annualized MWRR) that makes the right side of this equation equal to 0. 

    #### 4. Cumulative Chart Anchor
    This sign convention ensures that on the very first day (\(t_0\)), the initial deposit (\(CF_0 = -1000\)) and the hypothetical liquidation (\(CF_1 = +1000\)) cancel each other out:
    
    \[
    0 = -1000 + 1000 = 0\%
    \]
    
    This anchors the start of the Cumulative MWRR chart at exactly **0%**.

**Variable Descriptions:**

* $r$ = Annualized MWRR (representing the CAGR of your actual money).
* $CF_i$ = Cash flow from the investor's perspective:
    * **Negative cash flows ($CF_i < 0$):** Capital committed to the portfolio (deposits, investments). This represents money leaving the investor's wallet.
    * **Positive cash flows ($CF_i > 0$):** Capital returned to the investor (withdrawals, dividends). This represents money returning to the wallet.
    * **Final valuation ($CF_n > 0$):** The final portfolio Net Asset Value (NAV) at the end of the period, treated as a positive inflow (a hypothetical liquidation where the entire portfolio is converted back to cash returning to the wallet).
* $t_i$ = Days elapsed since the start of the period ($t_0 = 0$).

**Key Concepts:**

* It represents an **annual velocity/rate** of growth.
* It is ideal for long-term comparisons (e.g., comparing your performance with an annual bank interest rate or CAGR).
* **Volatility Warning:** On short periods (e.g., a few days or weeks), the annualized return can be highly volatile and display extreme percentages because the math extrapolates a small-window return to a full 365-day year.

### Cumulative MWRR {: #cumulative-mwrr }
Cumulative MWRR represents the total equivalent return over the selected period, obtained by compounding the annualized rate for the actual duration of that window.

**Direct Formula (without roots, uses $r$ directly):**

$$
\text{MWRR}_{\text{cumulative}} = (1 + r)^{\frac{\text{days}}{365}} - 1
$$

**Daily Rate Formula (with root):**

$$
\text{MWRR}_{\text{cumulative}} = (1 + r_d)^{\text{days}} - 1 \quad \text{where} \quad r_d = \sqrt[365]{1 + r} - 1
$$

Both formulas are mathematically equivalent. However, computationally, the direct formula using $r$ (without roots) is preferred once the annualized rate $r$ is found, as direct exponentiation is simpler and more efficient for the software to calculate.

**Variable Descriptions:**

* $\text{days}$ = The actual number of calendar days in the selected time window.

**Key Concepts:**

* It represents the **total distance covered** over the period.
* It starts at 0% and grows along the timeline, making it the correct metric for serial chart visualization.
* **Not a simple HPR:** While it represents cumulative return, it is a money-weighted cumulative return. It should not be confused with the simple Holding Period Return (ROI), which ignores cash flow timing.

---

## 🔢 10-Year Numerical Example

Let's look at a 10-year scenario to see how timing impacts performance and how these metrics convert:

* **Year 0:** You deposit **€10,000**.
* **Year 5:** You deposit another **€90,000**.
* **Year 10:** Your final Net Asset Value (NAV) is **€200,000**.

### Simple ROI Comparison
The simple ROI is calculated purely on total net contributions:

$$
ROI = \frac{200,000 - 100,000}{100,000} = +100\%
$$

### MWRR Timing Effect
If the bulk of your capital (€90,000) was deposited in Year 5, right before a massive multi-year market recovery, your money worked very efficiently. Because the larger sum was exposed to the high-growth years, your **Annualized MWRR** would be much higher than the market's TWRR.

Using a mathematical NPV solver for this specific scenario:
* **Annualized MWRR ($r$)** is exactly **13.02%**.

### Converting to Cumulative MWRR
By compounding this 13.02% annualized return over the 10-year period:

$$
\text{MWRR}_{\text{cumulative}} = (1 + 0.130227)^{10} - 1 \approx +240.14\%
$$

### What does +240.14% mean?
* It does **not** mean that your total €100,000 contributions grew to €340,140.
* It means that a **theoretical euro**, invested at the very beginning of the 10-year period and left untouched, would have grown to €3.40, achieving a total return of 240.14% by growing at the same average compound speed as your actual cash flows.

---

## 🖥️ UI Integration & Dashboard Usage

LibreFolio displays these performance metrics across the dashboard:

### Percent Chart (`%`)
Plotted series use **Cumulative MWRR**, **Cumulative TWRR**, and **Simple ROI**. This allows direct, side-by-side visual comparison as all three series start at 0% and represent total progress over the selected timeframe.

### KPI Cards
* **Simple ROI** (Primary metric for absolute return).
* **Cumulative TWRR** (Strategy/allocation performance indicator).
* **Cumulative MWRR** (Primary personal timing indicator).
* **Annualized MWRR** (Shown as a secondary/comparative metric to understand the compound yearly rate).

!!! tip "Analyzing the Performance Difference"

    To interpret the difference between Cumulative MWRR and Cumulative TWRR, refer to the [Timing Effect](timing-effect.md) page.

