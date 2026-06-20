# ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Asset Transfer

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-transfer" alt="Transaction Form — TRANSFER">
</div>

**Asset transfers** move securities between broker accounts **without a sale**. The position leaves one broker and arrives at another — no cash changes hands, and in most jurisdictions this is not a taxable event.

---

## 🔑 Key Properties

| Property | From (source) | To (destination) |
|----------|---------------|-------------------|
| **Code** | `TRANSFER` | `TRANSFER` |
| **Cash effect** | — | — |
| **Asset effect** | ⬇️ Decreases | ⬆️ Increases |
| **Broker** | Source broker | Destination broker |
| **Tax event** | Varies by jurisdiction | Varies |

---

## 📊 How It Works

An asset transfer records **two entries**: one debit at the source broker and one credit at the destination broker. Both reference the **same asset** with mirrored quantities.

Common scenarios:

- Moving shares from one broker to another
- Inheriting assets
- In-kind contributions to a different account type (e.g., ISA, 401k)

!!! info "Cost Basis Preservation"

    When transferring assets, the **original cost basis** should be preserved. The transfer itself is not a taxable event in most jurisdictions (though rules vary). LibreFolio allows an optional **cost basis override** on the receiving side.

    See **[📊 Weighted Average Cost (WAC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** for how the automatic cost basis is computed.

---

## 🔀 Relationship with Adjustments

Under the hood, a Transfer is composed of two Adjustment entries. LibreFolio supports:

| Operation | Result |
|-----------|--------|
| **Split** (unlink) | Transfer → two independent Adjustments |
| **Promote** (link) | Two Adjustments → Transfer |

**Promote constraints**: same asset, different brokers, opposite quantities.

---

## 🔗 Related

- 📊 **[Weighted Average Cost](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — How cost basis is computed on transfers
- 🏦 **[Cash Transfer](cash-transfer.md)** — Wire transfers (cash, not assets)
- 💱 **[FX Conversion](fx-conversion.md)** — Currency exchange
- 📊 **[Adjustment](adjustment.md)** — Manual corrections
