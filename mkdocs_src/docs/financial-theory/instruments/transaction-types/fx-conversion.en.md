# ![](../../../static/icons/transactions/fx-conversion.png){: width="32" style="vertical-align: middle;" } FX Conversion

**FX conversions** exchange one currency for another within the **same broker account**. In LibreFolio, this is a **paired transaction** — each conversion creates two linked rows: a "from" side (source currency, negative) and a "to" side (target currency, positive).

---

## 🔑 Key Properties

| Property | From (source) | To (target) |
|----------|---------------|-------------|
| **Code** | `FX_CONVERSION` | `FX_CONVERSION` |
| **Cash effect** | ⬇️ Source currency | ⬆️ Target currency |
| **Asset effect** | — | — |
| **Broker** | Same on both sides | Same on both sides |
| **Currency** | Different on each side | Different on each side |
| **Paired** | ✅ Yes (linked via `link_uuid`) | ✅ Yes |
| **Tax event** | Varies by jurisdiction | Varies |

---

## 📊 How It Works

Both halves share the same broker and `link_uuid`, but have **different currencies**. The conversion rate is implicit from the amounts:

$$
\text{FX Rate} = \frac{\text{Amount}_{target}}{\lvert\text{Amount}_{source}\rvert}
$$

FX conversions may be:

- **Explicit**: User deliberately converts currencies (e.g., EUR → USD before buying US stocks)
- **Implicit**: Broker auto-converts when buying a foreign-denominated asset

!!! info "Implicit FX and Fees"

    When a broker auto-converts currency, the effective rate often includes a spread. The difference between the market rate and the effective rate is essentially a hidden fee:

    $$
    \text{Implicit Fee} = \lvert\text{Amount}_{source}\rvert \times (\text{Market Rate} - \text{Effective Rate})
    $$

---

## 🔀 Split & Promote

| Operation | Result |
|-----------|--------|
| **Split** (unlink pair) | "From" → `WITHDRAWAL`, "To" → `DEPOSIT` |
| **Promote** (link W+D) | `WITHDRAWAL` + `DEPOSIT` → `FX_CONVERSION` pair |

**Promote constraints**: different currencies, same broker.

---

## 🔗 Related

- 💵 **[Deposit & Withdrawal](deposit-withdrawal.md)** — Single-sided cash movements
- 🔄 **[Asset Transfer](transfer.md)** — Moving securities between brokers
- 🏦 **[Cash Transfer](cash-transfer.md)** — Wire transfers between brokers
- 💰 **[FX Rates](../../../user/fx/index.md)** — Exchange rate management

