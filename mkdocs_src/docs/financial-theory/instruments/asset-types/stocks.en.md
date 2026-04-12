# <img src="../../../static/icons/asset-types/stock.png" width="32" style="vertical-align: middle;" /> Stocks

A **stock** (or share / equity) represents partial ownership in a publicly traded company. When you buy a stock, you become a shareholder with a proportional claim on the company's assets and earnings.

---

## 🔑 Key Characteristics

| Property | Detail |
|----------|--------|
| **Code in LibreFolio** | `STOCK` |
| **Pricing** | Real-time or delayed quotes from exchanges (NYSE, NASDAQ, LSE, etc.) |
| **Currency** | Denominated in the exchange's local currency |
| **Dividends** | Many stocks pay periodic cash dividends (quarterly in the US, semi-annually in Europe) |
| **Splits** | Companies may split shares (e.g., 4:1) to lower the per-share price |
| **Typical providers** | Yahoo Finance, CSS Scraper |

---

## 📊 How Stocks Work

1. **Price discovery**: Stocks trade on public exchanges during market hours. The price reflects supply and demand.
2. **Dividends**: Companies may distribute a portion of profits to shareholders. This creates a [Dividend event](../asset-events/dividend.md) on the ex-date.
3. **Capital gains**: The difference between buy and sell price determines your profit or loss. See [Taxation](../../fundamentals/taxation.md).
4. **Splits**: A company may split its shares to improve liquidity. A 4:1 split means each share becomes 4 shares at ¼ the price. See [Split event](../asset-events/split.md).

---

## 📐 Total Return

The total return of a stock includes both price appreciation and dividends:

$$
R_{total} = \frac{P_{end} - P_{start} + \sum D_i}{P_{start}}
$$

where $D_i$ are all dividend payments received during the holding period.

---

## 🔗 Related

- 💰 **[Dividend Events](../asset-events/dividend.md)** — How dividends affect stock prices
- ✂️ **[Split Events](../asset-events/split.md)** — Forward and reverse splits
- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — Measuring stock performance
