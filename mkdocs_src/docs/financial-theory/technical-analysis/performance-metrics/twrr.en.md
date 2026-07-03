# ⏱️ TWRR (Time-Weighted Rate of Return)

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is it?
TWRR measures the **"pure" performance** of your chosen assets and strategy (The Market), completely ignoring the timing and size of your deposits or withdrawals. 

It is the standard metric used by mutual funds and ETFs because fund managers have no control over when clients deposit or withdraw capital; they must be evaluated solely on the returns of the underlying investments.

---

## 🧩 What is a Sub-Period?
To isolate asset performance from cash flow timing, TWRR breaks the evaluation timeline into smaller intervals called **sub-periods**. 

A **sub-period** is a continuous interval of time between two consecutive external cash flows (deposits or withdrawals). 

By definition:
* A new sub-period begins immediately after any external cash flow.
* During any given sub-period, **no external capital is added or removed** from the portfolio.
* Consequently, any changes in the portfolio's value during a sub-period are driven entirely by asset performance (price fluctuations, dividends, interest).

---

## 🧮 How it works
TWRR calculates the rate of return for each sub-period individually and then links (multiplies) them together.

$$
R_{\text{TWRR}} = \prod_{i=1}^{n} (1 + r_i) - 1 = (1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1
$$

**Variable Descriptions:**

* $r_i$ = The rate of return of sub-period $i$.
* $n$ = The total number of sub-periods.

---

??? note "Example of Unfolding TWRR"

    ### 1. The Scenario

    * **Day 0:** You start your portfolio with an initial deposit of **€1,000**.
    * **Day 10:** The market goes up. Your portfolio is now worth **€1,100**. On this same day, you deposit another **€500** cash.
    * **Day 20:** The market drops. Your portfolio ends at a final value of **€1,440**.
    
    ### 2. Breaking Down the Sub-Periods
    The timeline is split into two sub-periods because of the cash flow on Day 10:
    
    **Sub-Period 1 (Day 0 to Day 10):**

    * Start Value (\(V_{\text{start}}\)): **€1,000**
    * End Value (\(V_{\text{end}}\) before cash flow): **€1,100**
    * Sub-Period Return (\(r_1\)):

    \[
    r_1 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1,100}{1,000} - 1 = +10\%
    \]
    
    **Sub-Period 2 (Day 10 to Day 20):**

    * Start Value (\(V_{\text{start}}\) after cash flow): €1,100 + €500 deposit = **€1,600**
    * End Value (\(V_{\text{end}}\)): **€1,440**
    * Sub-Period Return (\(r_2\)):

    \[
    r_2 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1,440}{1,600} - 1 = -10\%
    \]
    
    ### 3. Unfolding the TWRR Calculation
    We link the returns of the sub-periods together:
    
    \[
    \begin{aligned}
    R_{\text{TWRR}} &= (1 + r_1) \times (1 + r_2) - 1 \\
    &= (1 + 0.10) \times (1 - 0.10) - 1 \\
    &= 1.10 \times 0.90 - 1 \\
    &= 0.99 - 1 \\
    &= -1\%
    \end{aligned}
    \]
    
    The assets you picked went up 10% and then down 10%, resulting in a net asset-level return of **-1%**.
    
    ### 4. TWRR vs. Simple ROI
    Let's calculate the **Simple ROI** for the exact same scenario to see the contrast:

    * Total net cash invested = €1,000 + €500 = **€1,500**
    * Final portfolio value = **€1,440**
    * Simple ROI:

    \[
    ROI = \frac{1,440 - 1,500}{1,500} = -4\%
    \]
    
    **Why are they different?**

    * **Simple ROI (-4%)** shows your actual, raw wallet performance. It is dragged down because you deposited €500 right before a -10% drop, making your loss heavier in absolute terms.
    * **TWRR (-1%)** isolates the asset's strategy performance. It shows what would have happened if you had just invested a single sum at the beginning and never touched it again.

---

## 🎯 When to use it
* To judge the quality of the **assets and strategy you chose**, independent of your personal savings rate or timing.
* To compare your portfolio performance directly against external benchmarks (like the S&P 500 or an index ETF).

---

!!! tip "Analyzing the Performance Difference"

    To understand how your personal cash flows caused your actual returns to deviate from the pure strategy return (TWRR), refer to the [Timing Effect](timing-effect.md) page.

