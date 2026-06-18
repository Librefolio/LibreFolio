# ![](../../../static/icons/transactions/cash-transfer.png){: width="32" style="vertical-align: middle;" } Cash Transfer

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-cash-transfer" alt="Transaction Form — Cash Transfer">
</div>

**Cash transfers** (wire transfers / bonifici) move money between broker accounts. The balance decreases at the source and increases at the destination — no assets are involved.

---

## 🔑 Key Properties

| Property | From (source) | To (destination) |
|----------|---------------|-------------------|
| **Code** | `CASH_TRANSFER` | `CASH_TRANSFER` |
| **Cash effect** | ⬇️ Decreases | ⬆️ Increases |
| **Asset effect** | — | — |
| **Broker** | Source broker | Destination broker |
| **Currency** | Same on both sides | Same on both sides |
| **Tax event** | No | No |

---

## 📊 How It Works

A cash transfer records **two entries**: one withdrawal at the source broker and one deposit at the destination. Both share the same currency with mirrored amounts. The two sides may have **different dates** — e.g., a wire sent on Monday may arrive on Wednesday.

Common scenarios:

- Wiring funds from one brokerage to another
- Moving cash to a savings account
- Sending money between personal accounts

!!! note "Different dates"

    Unlike asset transfers where both sides typically settle on the same date, wire transfers may span multiple days. LibreFolio supports separate dates for each side.

---

## 🔀 Relationship with Deposits/Withdrawals

Under the hood, a Cash Transfer is composed of a Withdrawal and a Deposit. LibreFolio supports:

| Operation | Result |
|-----------|--------|
| **Split** (unlink) | Cash Transfer → independent Withdrawal + Deposit |
| **Promote** (link) | Withdrawal + Deposit → Cash Transfer |

**Promote constraints**: same currency, different brokers, opposite cash amounts.

---

## 🔗 Related

- 🔄 **[Asset Transfer](transfer.md)** — Moving securities (not cash)
- 💵 **[Deposit & Withdrawal](deposit-withdrawal.md)** — Single-sided cash movements
- 💱 **[FX Conversion](fx-conversion.md)** — Currency exchange
