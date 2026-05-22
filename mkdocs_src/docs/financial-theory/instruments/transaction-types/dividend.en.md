# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividend (Transaction)

A **dividend transaction** records the cash payment received from holding a dividend-paying asset (stock or distributing ETF). It represents the portfolio-level impact of a [dividend event](../asset-events/dividend.md).

---

## 🔑 Key Properties

| Property | Detail |
|----------|--------|
| **Code** | `DIVIDEND` |
| **Cash effect** | ⬆️ Increases balance |
| **Asset effect** | — (quantity unchanged) |
| **Tax event** | Yes (taxable income in most jurisdictions) |

---

## 📊 Event vs Transaction

| Concept | Dividend Event | Dividend Transaction |
|---------|---------------|---------------------|
| **Scope** | Global — affects the asset price | Personal — affects your portfolio |
| **Example** | "Apple declared $0.25/share" | "I received $12.50 from my 50 shares" |
| **Recorded by** | Provider or manual (Data Editor) | Broker report (BRIM import) |
| **Chart impact** | Diamond marker (◆) on price chart | Not visible on chart |

---

## 📐 Dividend Amount

The amount received depends on the number of shares held on the **record date** (the date the company checks who owns shares):

$$
\text{Dividend Received} = \text{Shares Held} \times \text{Dividend per Share}
$$

Where:

- **Shares Held** = number of shares you own at the record date (ex-dividend date − 1 business day)
- **Dividend per Share** = amount declared by the company (e.g., $0.25/share)

### 💰 Withholding Tax

Many jurisdictions apply **withholding tax** on dividends — especially for foreign stocks. The tax is deducted at source (by the broker or the issuer's country) before you receive the payment:

$$
\text{Net Dividend} = \text{Gross Dividend} \times (1 - \tau_{withholding})
$$

Where:

- **Gross Dividend** = full declared amount (before tax)
- $\tau_{withholding}$ = withholding tax rate (e.g., 15% for US stocks held by EU residents under most tax treaties)
- **Net Dividend** = what actually lands in your broker account

The withheld amount is typically recorded as a separate `TAX` transaction in LibreFolio, keeping the gross dividend and the tax deduction distinct for tax reporting purposes.

---

## 🔗 Related

- 💰 **[Dividend Events](../asset-events/dividend.md)** — How dividends affect asset prices
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Dividend tax treatment
- 📈 **[Stocks](../asset-types/stocks.md)** — The primary dividend-paying asset class
