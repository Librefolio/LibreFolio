# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Buy & Sell

The most fundamental transaction types: **buying** increases your holdings and decreases cash; **selling** does the reverse and realizes a profit or loss.

---

## 🔑 Key Properties

| Property | Buy | Sell |
|----------|-----|------|
| **Code** | `BUY` | `SELL` |
| **Cash effect** | ⬇️ Decreases | ⬆️ Increases |
| **Asset effect** | ⬆️ Increases holdings | ⬇️ Decreases holdings |
| **Tax event** | No | Yes (realizes gain/loss) |

---

## 📊 How It Works

### 🛒 Buy

When you buy an asset, a **lot** is created with:

- **Date**: When the purchase occurred
- **Quantity**: Number of shares/units bought
- **Unit price**: Price per share at the time of purchase
- **Fees**: Any transaction fees (commission, spread, etc.)
- **Total cost**: `quantity × unit_price + fees`

### 💰 Sell

When you sell, LibreFolio matches the sale against existing lots using **FIFO** (First In, First Out) to determine:

$$
\text{Capital Gain} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Fees}
$$

!!! info "FIFO Matching"

    LibreFolio computes lot matching at **runtime** — it's not persisted in the database. This allows for flexible what-if analysis and potential future support for other matching methods (LIFO, specific identification).

---

## 📐 Cost Basis

The cost basis of your holdings is the total amount you've paid, including fees:

$$
\text{Cost Basis} = \sum_{i} (Q_i \times P_i + F_i)
$$

This is used to compute unrealized P&L at any point:

$$
\text{Unrealized P\\&L} = \text{Current Value} - \text{Cost Basis}
$$

---

## 🔗 Related

- 💰 **[Taxation](../../fundamentals/taxation.md)** — Capital gains, matching methods, loss carry-forward
- 📈 **[Returns](../../fundamentals/returns.md)** — Measuring investment performance

