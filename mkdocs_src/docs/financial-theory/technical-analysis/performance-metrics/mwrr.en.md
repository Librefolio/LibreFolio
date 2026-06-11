# 💵 MWRR (Money-Weighted Rate of Return) / XIRR

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is it?
MWRR (also known as Internal Rate of Return) measures *your personal* performance. It heavily weights the periods where you had the most money invested.

## 🧮 How it works
It looks at the exact dates and sizes of all your cash flows (deposits and withdrawals) and the final portfolio value, calculating the constant interest rate that a bank would have needed to offer you to reach the exact same final result.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

Where $CF_i$ is each cash flow (deposits positive, withdrawals negative, final portfolio value positive).

## 🎯 When to use it
- To judge **your personal timing**.
- To see the raw, true reality of how effectively your money grew.

## 📈 How the Cumulative Series (Chart) is Calculated
To display MWRR as a historical chart over time, the calculation is performed **cumulatively** from the start for every single day in the series. 

For each data point plotted at day $t_N$:

1. The calculation considers the entire time window from $t_0$ to $t_N$.
2. It sets up the Net Present Value equation where the initial cash flow at $t_0$ is the starting portfolio value (represented as a negative cash flow: an "investment").
3. All intermediate cash flows between $t_0$ and $t_N$ are plotted on the timeline.
4. The final cash flow at $t_N$ represents the hypothetical liquidation of the portfolio, which is the NAV at $t_N$ (represented as a positive cash flow). 

**Important Mathematical Edge Case:** 
If an external cash flow occurs exactly on the final day $t_N$ of the period being evaluated, the NAV at $t_N$ already incorporates that cash flow. In the NPV equation for that specific day, the final net cash flow must account for both the final NAV and the cash flow made on that same day. 

**Example:**
Imagine you start at $t_0$ with a portfolio of \$1,000. 
- The cash flow at $t_0$ is -\$1,000.
- On day $t_{31}$, you deposit an additional \$100.
- Your portfolio NAV immediately jumps to \$1,100 (assuming no market growth). 

If the algorithm uses the final NAV of +\$1,100 as the terminal cash flow without offsetting the deposit made on that exact same day, the math assumes a \$1,000 investment grew to \$1,100 purely through market performance (a false 10% gain). By correctly including the -\$100 deposit on $t_{31}$ alongside the terminal NAV, the final net cash flow becomes +\$1,000 (\$1,100 - \$100), correctly proving that the real return was 0%.

This logic also ensures that on the very first day ($t_0$), the starting NAV and the initial investment perfectly cancel each other out, anchoring the beginning of the chart at exactly 0%.
