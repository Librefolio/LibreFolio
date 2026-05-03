# ![](../../../static/icons/transactions/cash-transfer.png){: width="32" style="vertical-align: middle;" } Cash Transfer

**Cash transfers** (wire transfers / bonifici) move money between broker accounts. In LibreFolio, this is a **paired transaction** — each transfer creates two linked rows: a "from" side (negative cash) and a "to" side (positive cash).

---

## 🔑 Key Properties

| Property | From (source) | To (destination) |
|----------|---------------|-------------------|
| **Code** | `CASH_TRANSFER` | `CASH_TRANSFER` |
| **Cash effect** | ⬇️ Decreases | ⬆️ Increases |
| **Asset effect** | — | — |
| **Broker** | Source broker | Destination broker |
| **Currency** | Same on both sides | Same on both sides |
| **Paired** | ✅ Yes (linked via `link_uuid`) | ✅ Yes |
| **Tax event** | No | No |

---

## 📊 How It Works

Both halves share the same currency and `link_uuid`. The cash amount is mirrored: one side is negative (outgoing), the other is positive (incoming). The two sides may have **different dates** — e.g., a wire sent on Monday may arrive on Wednesday.

Common scenarios:

- Wiring funds from one brokerage to another
- Moving cash to a savings account
- Sending money between personal accounts

!!! note "Different dates"

    Unlike asset transfers where both sides typically settle on the same date, wire transfers may span multiple days. LibreFolio supports separate dates for each half of the pair.

---

## 🔀 Split & Promote

| Operation | Result |
|-----------|--------|
| **Split** (unlink pair) | "From" → `WITHDRAWAL`, "To" → `DEPOSIT` |
| **Promote** (link W+D) | `WITHDRAWAL` + `DEPOSIT` → `CASH_TRANSFER` pair |

**Promote constraints**: same currency, different brokers, opposite cash amounts.

---

## 🔗 Related

- 🔄 **[Asset Transfer](transfer.md)** — Moving securities (not cash)
- 💵 **[Deposit & Withdrawal](deposit-withdrawal.md)** — Single-sided cash movements
- 💱 **[FX Conversion](fx-conversion.md)** — Currency exchange

