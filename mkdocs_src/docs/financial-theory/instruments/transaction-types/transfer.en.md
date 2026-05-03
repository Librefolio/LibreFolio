# ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Asset Transfer

**Asset transfers** move securities between broker accounts **without a sale**. In LibreFolio, this is a **paired transaction** — each transfer creates two linked rows: a "from" side (negative quantity) and a "to" side (positive quantity).

---

## 🔑 Key Properties

| Property | From (source) | To (destination) |
|----------|---------------|-------------------|
| **Code** | `TRANSFER` | `TRANSFER` |
| **Cash effect** | — | — |
| **Asset effect** | ⬇️ Decreases | ⬆️ Increases |
| **Broker** | Source broker | Destination broker |
| **Paired** | ✅ Yes (linked via `link_uuid`) | ✅ Yes |
| **Tax event** | Varies by jurisdiction | Varies |

---

## 📊 How It Works

Both halves reference the **same asset** and share a `link_uuid`. The quantity is mirrored: one side is negative (outgoing), the other is positive (incoming).

Common scenarios:

- Moving shares from one broker to another
- Inheriting assets
- In-kind contributions to a different account type (e.g., ISA, 401k)

!!! info "Cost Basis Preservation"

    When transferring assets, the **original cost basis** should be preserved. The transfer itself is not a taxable event in most jurisdictions (though rules vary). LibreFolio allows an optional **cost basis override** on the receiving side.

---

## 🔀 Split & Promote

| Operation | Result |
|-----------|--------|
| **Split** (unlink pair) | Both halves become `ADJUSTMENT` |
| **Promote** (link 2 adjustments) | Two `ADJUSTMENT` rows → `TRANSFER` pair |

**Promote constraints**: same asset, different brokers, opposite quantities.

---

## 🔗 Related

- 🏦 **[Cash Transfer](cash-transfer.md)** — Wire transfers (cash, not assets)
- 💱 **[FX Conversion](fx-conversion.md)** — Currency exchange
- 📊 **[Adjustment](adjustment.md)** — Manual corrections
- 🛒 **[Buy & Sell](buy-sell.md)** — Standard asset transactions
