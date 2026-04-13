# ![](../../../static/icons/asset-types/fund.png){: width="32" style="vertical-align: middle;" } Mutual Fund

A **mutual fund** is a professionally managed investment vehicle that pools money from many investors to purchase a diversified portfolio of stocks, bonds, or other securities.

---

## 🔑 Key Characteristics

| Property | Detail |
|----------|--------|
| **Code in LibreFolio** | `FUND` |
| **Pricing** | NAV (Net Asset Value) calculated once per day, after market close |
| **Currency** | Denominated in the fund's base currency |
| **Dividends** | May distribute (income funds) or reinvest (growth funds) |
| **Fees** | Management fee (TER), entry/exit loads |
| **Typical providers** | Yahoo Finance, Manual |

---

## 📊 How Mutual Funds Work

1. **Pooling**: Investors buy shares/units of the fund
2. **Management**: A professional fund manager selects and manages the underlying securities
3. **NAV pricing**: The fund's value is calculated daily as: total assets − liabilities ÷ shares outstanding
4. **Distributions**: Income (dividends, interest) may be distributed or reinvested

---

## 📐 NAV Calculation

$$
\text{NAV} = \frac{\text{Total Assets} - \text{Total Liabilities}}{\text{Shares Outstanding}}
$$

Unlike ETFs, mutual funds trade only at end-of-day NAV — you cannot buy or sell at intraday prices.

---

## 🔗 Related

- 📊 **[ETFs](etfs.md)** — Exchange-traded alternative with intraday pricing
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Distribution vs accumulation tax implications
- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — Measuring fund performance


