# <img src="../../../static/icons/transactions/dividend.png" width="32" style="vertical-align: middle;" /> Dividend (Transaction)

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

The amount received depends on the number of shares held on the **record date**:

$$
\text{Dividend Received} = \text{Shares Held} \times \text{Dividend per Share}
$$

### 💰 Withholding Tax

Many jurisdictions apply withholding tax on dividends, especially for foreign stocks:

$$
\text{Net Dividend} = \text{Gross Dividend} \times (1 - \tau_{withholding})
$$

The withheld tax is recorded as a separate `TAX` transaction.

---

## 🔗 Related

- 💰 **[Dividend Events](../asset-events/dividend.md)** — How dividends affect asset prices
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Dividend tax treatment
- 📈 **[Stocks](../asset-types/stocks.md)** — The primary dividend-paying asset class
