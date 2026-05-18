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

## 📈 Implied Rate & Broker Spread

LibreFolio automatically computes the **implied exchange rate** from the two linked amounts:

$$
\text{Implied Rate} = \frac{\lvert\text{Amount}_{target}\rvert}{\lvert\text{Amount}_{source}\rvert}
$$

This is compared with the **market rate** from the FX subsystem at the transaction date. The difference is the **broker spread** — the markup applied by the broker for the conversion:

$$
\text{Spread} = \text{Implied Rate} - \text{Market Rate}
$$

$$
\text{Spread \%} = \frac{\text{Spread}}{\text{Market Rate}} \times 100
$$

!!! info "Where you'll see this"

    - **Bulk Edit banner**: when two standalone transactions are detected as a potential FX conversion, the implied rate and spread are shown inline with a tooltip for details.
    - **Transaction Form**: when creating or editing an FX conversion, an info marker between the two sides shows the implied rate vs. market rate.

!!! warning "Market Rate Availability"

    The market rate comparison requires the relevant FX pair to be configured in LibreFolio's FX system. If the pair is not configured or no rate exists for the transaction date, only the implied rate is shown (the spread cannot be computed).

    When a rate from a different date is used (backward-fill), a ⚠️ stale indicator shows how many days old the rate is.

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

