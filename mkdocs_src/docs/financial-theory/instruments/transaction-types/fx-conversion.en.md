# ![](../../../static/icons/transactions/fx-conversion.png){: width="32" style="vertical-align: middle;" } FX Conversion

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-fxconversion" alt="Transaction Form — FX Conversion">
</div>

**FX conversions** exchange one currency for another within the **same broker account**. One currency balance decreases while another increases — no securities or brokers change.

---

## 🔑 Key Properties

| Property | From (source) | To (target) |
|----------|---------------|-------------|
| **Code** | `FX_CONVERSION` | `FX_CONVERSION` |
| **Cash effect** | ⬇️ Source currency | ⬆️ Target currency |
| **Asset effect** | — | — |
| **Broker** | Same on both sides | Same on both sides |
| **Currency** | Different on each side | Different on each side |
| **Tax event** | Varies by jurisdiction | Varies |

---

## 📊 How It Works

An FX conversion records **two entries** on the same broker with **different currencies**. The conversion rate is implicit from the amounts:

$$
FX_{rate} = \frac{\text{Amount}_{target}}{\lvert\text{Amount}_{source}\rvert}
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

LibreFolio automatically computes the **implied exchange rate** from the two amounts:

$$
\text{Implied Rate} = \frac{\lvert\text{Amount}_{target}\rvert}{\lvert\text{Amount}_{source}\rvert}
$$

This is compared with the **market rate** from the FX subsystem at the transaction date. The difference is the **broker spread**:

$$
\text{Spread} = \text{Implied Rate} - \text{Market Rate}
$$

$$
\text{%Spread} = \frac{\text{Spread}}{\text{Market Rate}} \times 100
$$

!!! warning "Market Rate Availability"

    The market rate comparison requires the relevant FX pair to be configured in LibreFolio's FX system. If the pair is not configured or no rate exists for the transaction date, only the implied rate is shown.

---

## 🔀 Relationship with Deposits/Withdrawals

Under the hood, an FX Conversion is composed of a Withdrawal (source currency) and a Deposit (target currency). LibreFolio supports:

| Operation | Result |
|-----------|--------|
| **Split** (unlink) | FX Conversion → independent Withdrawal + Deposit |
| **Promote** (link) | Withdrawal + Deposit → FX Conversion |

**Promote constraints**: different currencies, same broker.

---

## 🔗 Related

- 💵 **[Deposit & Withdrawal](deposit-withdrawal.md)** — Single-sided cash movements
- 🔄 **[Asset Transfer](transfer.md)** — Moving securities between brokers
- 🏦 **[Cash Transfer](cash-transfer.md)** — Wire transfers between brokers

---

*See also: [💱 FX Rates](../../../user/fx/index.md) — how to configure and sync exchange rates in LibreFolio.*
