# 📖 Book Value

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is Book Value?

In LibreFolio, the **Book Value** represents the historical accounting cost (cost basis) of your portfolio. It reflects the net amount of capital you have actually committed to your current open positions, plus cash.

It answers the question: _"How much did my current portfolio cost to build?"_

Unlike Net Asset Value (NAV), which fluctuates with daily market prices, Book Value only changes when you buy or sell assets, or when cash is deposited/withdrawn. It does not represent the current liquidated market value.

---

## 🧮 Formula

The Book Value is calculated using the following formula:

$$
\text{Book Value} = \text{Open Cost Basis} + \text{Cash Value} + \text{In Transit Book Value}
$$

Where:

- **$\text{Open Cost Basis}$**: The total cost basis of your open positions, calculated by multiplying each asset's pool quantity by its [Weighted Average Cost (WAC)](weighted-average-cost.md).
- **$\text{Cash Value}$**: The actual cash balance held in the broker accounts included in the scope.
- **$\text{In Transit Book Value}$**: The cost basis value of cash or assets currently in transit between accounts inside the scope. This concept is introduced to handle transfers (e.g., wire transfers or security transfers) that start on day 1 from the source account and arrive on day 5 at the destination account due to settlement delays.

---

## 📝 Practical Example

Consider a portfolio with the following figures:

- **Open Cost Basis (Acquisition Cost)**: €27,000
- **Cash**: €600
- **In Transit Assets (Book Cost)**: €0

The Book Value is calculated as:

$$
\text{Book Value} = 27,000 + 600 + 0 = \text{€}27,600
$$

### 📊 Comparison with NAV (Unrealized Performance)

If the current market value ([NAV](nav.md)) of this portfolio is **€33,000**, we can compute the **Unrealized Gain/Loss** (latent performance) by comparing it with the Book Value:

$$
\text{Unrealized Gain/Loss} = \text{NAV} - \text{Book Value}
$$

$$
\text{Unrealized Gain/Loss} = 33,000 - 27,600 = +\text{€}5,400
$$

This indicates that your portfolio has gained €5,400 in market value above what you paid to acquire it.

---

## ⚙️ Note on Cost Basis Methods

To determine the cost basis of open positions, LibreFolio utilizes the [Weighted Average Cost (WAC)](weighted-average-cost.md) method as its default inventory-tracking algorithm:

- Every time you purchase an asset, the average cost per unit is updated.
- Every time you sell an asset, the cost basis is reduced proportionally based on the WAC at the time of sale, leaving the unit cost of remaining shares unchanged.
