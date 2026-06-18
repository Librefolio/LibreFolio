# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Buy & Sell ![](../../../static/icons/transactions/sell.png){: width="32" style="vertical-align: middle;" }

<div class="lf-screenshot-carousel" data-carousel="buy-sell" data-carousel-interval="4000" data-show-titles="true">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> BUY' alt="Buy">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> SELL' alt="Sell">
</div>

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

## 🔗 Related

- 📊 **[Weighted Average Cost (WAC)](../../portfolio-theory/weighted-average-cost.md)** — Average cost per unit across multiple buys
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Capital gains, matching methods, loss carry-forward
- 📈 **[Returns](../../fundamentals/returns.md)** — Measuring investment performance

