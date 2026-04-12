# ✂️ Split

A **stock split** (or reverse split) is a corporate action that changes the number of outstanding shares while keeping the total market capitalization constant.

---

## 📖 Definition

In a stock split, a company divides its existing shares into multiple new shares. The **total value** of an investor's position remains the same — only the number of shares and the price per share change.

### Forward Split

The company increases the number of shares. Each existing share becomes multiple shares at a proportionally lower price.

| Ratio | Meaning |
|-------|---------|
| **2:1** | Each share becomes 2 shares at half the price |
| **3:1** | Each share becomes 3 shares at one-third the price |
| **4:1** | Each share becomes 4 shares at one-quarter the price |
| **10:1** | Each share becomes 10 shares at one-tenth the price |

### Reverse Split

The company reduces the number of shares. Multiple existing shares merge into fewer shares at a proportionally higher price.

| Ratio | Meaning |
|-------|---------|
| **1:2** | Every 2 shares become 1 share at double the price |
| **1:10** | Every 10 shares become 1 share at 10× the price |
| **1:20** | Every 20 shares become 1 share at 20× the price |

---

## 📉 Impact on Market Price

A split causes an **immediate, proportional price change** that is mathematically neutral:

$$
P_{\text{after}} = \frac{P_{\text{before}}}{\text{split ratio}}
$$

$$
Q_{\text{after}} = Q_{\text{before}} \times \text{split ratio}
$$

Where $P$ is price per share and $Q$ is quantity of shares.

!!! example "Example: Apple 4:1 Split (August 2020)"

    - **Before split**: 100 shares × $500 = $50,000 total value
    - **After split**: 400 shares × $125 = $50,000 total value
    - **Price change**: −75% (but position value unchanged)

!!! example "Example: Reverse Split 1:10"

    - **Before**: 1,000 shares × $0.50 = $500 total value
    - **After**: 100 shares × $5.00 = $500 total value
    - **Reason**: Company wants to raise share price above exchange minimum listing requirements

---

## 📊 Why Companies Split

### Forward splits

- **Accessibility**: Lower share price makes the stock more accessible to retail investors
- **Liquidity**: More shares outstanding can increase trading volume
- **Psychology**: A lower nominal price can attract more buyers
- **Options**: Lower share price reduces the capital needed for options contracts (100 shares per contract)

### Reverse splits

- **Listing compliance**: Exchanges require minimum share prices (e.g., $1.00 on NASDAQ)
- **Institutional perception**: Some funds have minimum price requirements
- **Often a warning sign**: Reverse splits are frequently associated with struggling companies

---

## 📈 Historical Price Adjustment

When analyzing historical prices across splits, data providers typically provide **adjusted prices** — all historical prices are divided by the cumulative split ratio so the chart shows a smooth line.

For example, if Apple was $100 before a 4:1 split, the adjusted historical price becomes $25 to match the post-split scale.

---

## 🧮 How LibreFolio Handles Splits

In LibreFolio, a `SPLIT` event is recorded with:

- **Date**: The effective date of the split
- **Amount**: The split ratio (e.g., `2` for a 2:1 split, `0.1` for a 1:10 reverse split)
- **Notes**: Optional description (e.g., "4:1 forward split")

Split events appear as **markers on the chart** and help explain sudden price discontinuities. When using **adjusted prices** from providers like Yahoo Finance, the split is already factored into the price data.

---

## 🔗 Related

- 📅 **[Asset Events Overview](index.md)** — All event types
- 💸 **[Transaction Types](../transaction-types/index.md)** — How splits affect portfolio transactions
- 📚 **[Asset Types](../asset-types/index.md)** — Types of assets that can split

