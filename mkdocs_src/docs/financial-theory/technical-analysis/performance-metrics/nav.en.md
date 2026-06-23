# 💼 Net Asset Value (NAV) / Net Worth

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is NAV / Net Worth?

In the LibreFolio dashboard, **Net Asset Value (NAV)** (also referred to as **Net Worth**) represents the total market value of your portfolio at the end of the selected time window (`date_to`). 

It answers the fundamental question: _"How much is the portfolio within the selected scope worth right now?"_

Unlike period-based performance metrics (such as ROI or P&L), NAV is a **point-in-time snapshot**. While its historical trend can be plotted over time, the final NAV value shown on a dashboard card depends solely on the end date (`date_to`) and is completely independent of the starting date (`date_from`).

---

## 🧮 Formula

LibreFolio calculates the Net Asset Value using the following formula:

$$
\text{NAV} = \text{Market Value} + \text{Cash Value} + \text{In Transit Market Value}
$$

Where:

- **$\text{Market Value}$**: The current market valuation of all held assets (ETFs, stocks, bonds, cryptos, etc.) calculated using the latest available price and converted to the target currency.
- **$\text{Cash Value}$**: The actual cash balance held in the broker accounts included within the selected scope.
- **$\text{In Transit Market Value}$**: The valuation of cash or assets currently in transit between accounts inside the scope (e.g., initiated but not yet completed internal transfers). Similar to Book Value, this concept handles transactions that leave one account on day 1 and arrive at the destination on day 5 due to execution delays.

---

## 📝 Practical Example

Consider a portfolio with the following balances at the end of the selected period:

- **Market Value of Assets**: €32,759
- **Cash Balance**: €631
- **In Transit Assets**: €0

The Net Asset Value is calculated as:

$$
\text{NAV} = 32,759 + 631 + 0 = \text{€}33,390
$$


---

## ⚖️ Key Differences

To avoid confusion, it is important to distinguish NAV from other dashboard metrics:

- **vs. Book Value**: NAV represents the **current market value** of your assets. [Book Value](book-value.md) represents the **acquisition cost** (what you originally paid). The difference between the two is your unrealized gain or loss.
- **vs. Period P&L**: NAV is the absolute value of your wealth. [Period P&L](period-pnl.md) is the *change* in your wealth over a specific timeframe, adjusted for external deposits and withdrawals.

---

## ⚠️ Data Quality & Valuation

Because NAV relies on market prices and foreign exchange (FX) rates to convert all assets into your target currency:

- If price data or FX rates are missing for any asset on `date_to`, the valuation may be incomplete.
- In such cases, LibreFolio displays the **Data Quality Banner** at the top of the dashboard to alert you that some valuations are based on stale or missing pricing.
