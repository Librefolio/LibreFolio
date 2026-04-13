# ![](../../../static/icons/asset-types/etf.png){: width="32" style="vertical-align: middle;" } ETFs (Exchange Traded Funds)

An **ETF** is a basket of securities (stocks, bonds, commodities, or a mix) that trades on an exchange like a single stock. ETFs combine the diversification of mutual funds with the real-time trading flexibility of stocks.

---

## 🔑 Key Characteristics

| Property | Detail |
|----------|--------|
| **Code in LibreFolio** | `ETF` |
| **Pricing** | Real-time exchange prices, like stocks |
| **Currency** | Denominated in the listing exchange's currency |
| **Dividends** | May distribute (Dist) or reinvest internally (Acc) |
| **TER** | Total Expense Ratio — annual management fee deducted from NAV |
| **Typical providers** | Yahoo Finance, justETF, CSS Scraper |

---

## 📊 Accumulating vs Distributing

| Feature | Accumulating (Acc) | Distributing (Dist) |
|---------|-------------------|-------------------|
| **Dividends** | Reinvested internally | Paid out to holders |
| **Tax event** | Only on sale | On each distribution |
| **Compounding** | Full compound growth | Reduced by tax drag |
| **Best for** | Long-term growth | Income needs |

The [tax deferral advantage](../../fundamentals/taxation.md#tax-deferral-advantage) of accumulating ETFs can be significant over long horizons.

---

## 📈 NAV vs Market Price

- **NAV** (Net Asset Value): The true value of underlying holdings ÷ shares outstanding. Computed daily.
- **Market Price**: What the ETF actually trades for on the exchange. Can deviate slightly from NAV.
- **Premium/Discount**: When market price > NAV, the ETF trades at a premium; when < NAV, at a discount.

---

## 🔍 Index Tracking

Most ETFs track a benchmark index (e.g., S&P 500, MSCI World). The **tracking error** measures how much the ETF's return deviates from the index:

$$
TE = \sigma(R_{ETF} - R_{index})
$$

Lower tracking error = better replication of the index.

---

## 🔗 Related

- 💰 **[Dividend Events](../asset-events/dividend.md)** — Distributions from ETF holdings
- 📈 **[Index & Benchmark](index-benchmark.md)** — How benchmarks work
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Acc vs Dist tax implications
