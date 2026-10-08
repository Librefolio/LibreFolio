# 📝 Transaction Form

The transaction form adds or edits one transaction — or one linked pair — in the [bulk workspace](index.md#bulk-workspace). It also shows a transaction read-only when you double-click it in a list. Only the fields that the chosen type needs appear.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> BUY' alt="Buy">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> SELL' alt="Sell">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDEND' alt="Dividend">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DEPOSIT' alt="Deposit">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ADJUSTMENT' alt="Adjustment">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFER' alt="Asset Transfer">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> FX CONVERSION' alt="FX Conversion">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CASH TRANSFER' alt="Cash Transfer">
</div>

---

## ✍️ Fill in the form

1. Pick the **Type**, then the **Broker** if it is not set already.
2. Fill in the **Required** section: the **Date**, the **Asset** and its quantity when the type has one, and the cash amount.
3. Open **Optional** for **Tags**, a **Description** or, on dividends, interest and adjustments, a **Linked Event**.
4. Click **Apply** to place the row in the workspace; **Save All** in the workspace writes it.

A few rules keep entries quick:

- **Amounts are totals** — type the total paid or received, not the price per share (*Total amount (not per share)*).
- **Type positive numbers** — the form adds the minus sign where money or units go out: a purchase's payment, a sale's units, a withdrawal, a fee, a tax. Only an **Adjustment** quantity takes a sign: positive adds units, negative removes them.
- **Checks as you go** — once the required fields are filled, the form checks the entry against your ledger and the other workspace rows, and lists any problem at the top. **⚡ Validate now** checks at once.
- **Missing broker or asset?** — **Create new** in the broker list, or **New asset** in the asset list, creates it without leaving the form.

??? info "💰 Cost basis of incoming units — for Adjustments and Asset Transfers"

    When an **Adjustment** adds units, or on the receiving side of an **Asset Transfer**, the form asks what those units cost:

    - **Auto** — LibreFolio computes it as a [Weighted Average Cost](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md); press **⚡ Validate now** to see it.
    - **Manual** — you type it.

    An Adjustment without a cost basis creates its lot at zero cost, and the form warns you: right for a split or a gift, wrong for shares bought elsewhere. If an exchange rate is missing, the **Sync FX rates** link fetches it.

---

## 🏷️ Transaction types

The [Financial Theory guide](../../financial-theory/instruments/transaction-types/index.md) explains each type in depth.

### 🧾 Single transactions

| Type | What it records | Theory |
|------|-----------------|--------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **Buy** | Units of an asset bought, and the total paid | [📖 Read](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } **Sell** | Units of an asset sold, and the total received | [📖 Read](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **Dividend** | Cash paid by an asset you hold | [📖 Read](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } **Interest** | Interest received, with or without an asset | [📖 Read](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **Deposit** | Cash you put into the broker | [📖 Read](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } **Withdrawal** | Cash you take out of the broker | [📖 Read](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **Fee** | A commission or another cost, optionally tied to an asset | [📖 Read](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } **Tax** | A tax paid, optionally tied to an asset | [📖 Read](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **Adjustment** | Units added or removed without cash: a split, a gift, a position opened elsewhere | [📖 Read](../../financial-theory/instruments/transaction-types/adjustment.md) |

### 🔗 Paired transactions {: #composite-transactions }

A paired operation is recorded as two linked transactions, which the form shows as one, with a **From** and a **To** side. Each side has its own date, and the **Swap sides** arrow turns the direction around.

| Type | What it records | Theory |
|------|-----------------|--------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **Asset Transfer** | Units of one asset moved between two of your brokers | [📖 Read](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **Cash Transfer** | Cash moved between two of your brokers, in one currency | [📖 Read](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **Currency Exchange** | One currency converted into another, inside one broker | [📖 Read](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

A transfer needs two different brokers, an exchange two different currencies. Two single rows can also be linked into a pair later, and a pair split back — see [Link or unlink a pair](index.md#link-pairs).

---

## 🔗 Related

- 📋 **[Transactions](index.md)** — the list, the filters and the bulk workspace
- 📥 **[Import from Broker](import/index.md)** — skip manual entry with a BRIM import
