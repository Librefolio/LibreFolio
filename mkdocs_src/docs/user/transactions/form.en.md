# 📝 Transaction Form

The Transaction Form opens whenever you **create** or **edit** a transaction. It adapts dynamically to the selected transaction type, showing only the fields relevant to that operation.

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

## 📋 The Form Interface

The form is designed to be intuitive and dynamic. When you select a **Transaction Type**, the form automatically adjusts to show only the relevant fields. 

- **Basic Details:** Date, Type, Currency, and Amount.
- **Asset Specifics:** If the transaction involves an asset (like BUY or SELL), fields for selecting the asset, entering the quantity, and setting the unit price will appear.
- **Preview Panel (WAC):** For operations that affect your portfolio, a real-time preview appears at the bottom. It shows your current cost basis, the projected new cost basis, and any realized gain/loss.

!!! note "Automatic Calculations"

    The system automatically handles standard calculations for you (such as multiplying quantity by unit price) so you don't have to do the math manually.

---

## 🏷️ Transaction Types

For an in-depth conceptual definition of each operation, please refer to the [Financial Theory guide](../../financial-theory/instruments/transaction-types/index.md).

### Single Transactions

These operate independently on a single broker account.

| Type | Description | Theory Guide |
|------|-------------|--------------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **BUY / SELL** ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } | Purchase or sale of an asset | [📖 Read](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **DEPOSIT / WITHDRAWAL** ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } | Adding or removing cash from a broker account | [📖 Read](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **DIVIDEND / INTEREST** ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } | Yield from equity or fixed-income assets | [📖 Read](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **FEE / TAX** ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } | Costs like broker fees or taxes | [📖 Read](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **ADJUSTMENT** | Manual correction to balances | [📖 Read](../../financial-theory/instruments/transaction-types/adjustment.md) |

### Composite Transactions {: #composite-transactions }

These represent movements **between** accounts or currencies. They produce two linked entries that balance each other.

| Type | Description | Theory Guide |
|------|-------------|--------------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **TRANSFER** | Asset moved between two of your brokers | [📖 Read](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **CASH_TRANSFER** | Wire transfer between brokers | [📖 Read](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **FX_CONVERSION** | Currency exchange within a broker | [📖 Read](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

To maintain data integrity and enable advanced analytics, composite transactions group multiple cash and asset legs:

* **Asset Transfer**: Specifies a **source broker** and a **destination broker**, asset, and quantity.
* **FX Conversion**: Specifies the **source currency amount** and the **destination currency amount** within the same broker.

You can create composite transactions directly from the form, or by **Promoting** single transactions (like linking a deposit and a withdrawal) from the transaction table. If needed, a composite transaction can be **split** back into individual single transactions.

---

## 🔗 Related

- 📋 **[Transaction Table](index.md)** — List view, filtering, bulk operations
- 📥 **[Import from Broker](import/index.md)** — Skip manual entry with BRIM import
