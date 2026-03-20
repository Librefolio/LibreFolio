# 📈 Returns & Growth Rates

This page covers the mathematical foundations of **investment returns** — how to measure, compare, and annualize growth rates. These concepts are used throughout LibreFolio's FX measurement tools and portfolio analytics.

---

## 📊 Simple (Discrete) Return

The **simple return** over a period is the percentage change:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example
    If EUR/USD moves from 1.10 to 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Properties

- **Intuitive**: directly represents "how much you gained/lost"
- **Not additive**: you cannot simply sum simple returns across periods to get total return
- **Compounding**: multi-period returns must be **multiplied**, not added

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Logarithmic (Continuous) Return

The **log return** is the natural logarithm of the price ratio:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Properties

- **Additive across time**: total log return = sum of sub-period log returns

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Symmetric**: a +5% move followed by a −5% move returns exactly to the starting point
- **Approximately equal** to simple return for small values: $r_{log} \approx R_{simple}$ when $R_{simple}$ is small

### 🔄 Conversion

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Annualized Return

To compare returns across different time periods, we **annualize** them — projecting the observed growth rate to a full year.

### 📈 Compound Annual Growth Rate (CAGR)

The most common annualization method. Given a total return over $d$ calendar days:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

This is what LibreFolio's [Measures tool](../user/fx/detail/measures.md) displays.

!!! example
    EUR/USD moves from 1.10 to 1.14 over 90 days:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Annualized Log Return

For log returns, annualization is simply scaling:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

This linearity is one of the key advantages of log returns in quantitative finance.

---

## 🔄 Relationship Between Simple and Log Returns

| Property | Simple Return $R$ | Log Return $r$ |
|----------|:---:|:---:|
| **Compounding** | Multiplicative: $(1+R_1)(1+R_2)$ | Additive: $r_1 + r_2$ |
| **Symmetry** | Asymmetric: +10% then −10% ≠ 0 | Symmetric: +10% then −10% = 0 |
| **Annualization** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Portfolio returns** | Weighted sum works ✅ | Weighted sum doesn't work ❌ |
| **Time series** | Not additive ❌ | Additive ✅ |
| **Interpretation** | "I gained 5%" | "Log growth rate was 0.0488" |

!!! tip "When to use which?"
    - **Simple returns** for reporting to users and computing portfolio-level returns
    - **Log returns** for statistical analysis, volatility estimation, and time-series models

---

## 📏 Day Count Conventions

The number of days $d$ can be computed differently depending on the convention:

- **Actual/365**: Calendar days (what LibreFolio uses)
- **Actual/360**: Calendar days over a 360-day year (common in money markets)
- **30/360**: Assumes 30-day months and 360-day year

For more details, see [Day Count Conventions](day-count.md).

---

## ⚠️ Pitfalls

1. **Very short periods**: Annualizing a 3-day return can produce misleading figures (e.g., a 0.1% 3-day move → 12.5% annualized)
2. **Negative prices**: Log returns are undefined for negative values — not an issue for FX rates
3. **Compounding frequency**: CAGR assumes continuous compounding; real-world instruments may compound daily, monthly, or quarterly

