# ⏱️ TWRR (Time-Weighted Rate of Return)

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is it?
TWRR measures the "pure" performance of your chosen assets (The Market), completely ignoring the timing and size of your deposits or withdrawals.

## 🧮 How it works
Every time you deposit or withdraw money, TWRR "breaks" the timeline into a sub-period. It calculates the return for that specific sub-period, and then links (multiplies) all sub-periods together. 

$$
R_{TWRR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

## 🎯 When to use it
- To judge if the **assets you picked** are actually good.
- To compare your portfolio against an external benchmark (like the S&P 500).
- Mutual funds and ETFs always report TWRR, because the fund manager cannot control when clients deposit or withdraw money.
