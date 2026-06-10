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
