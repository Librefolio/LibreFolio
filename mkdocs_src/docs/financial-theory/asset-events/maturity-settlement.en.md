# 🏁 Maturity Settlement

A **maturity settlement** event marks the end of a fixed-term financial instrument — the issuer returns the principal (face value) to the investor, and no further price calculations occur.

---

## 📖 Definition

Maturity is the date on which a debt instrument (bond, note, certificate of deposit, term loan) reaches its contractual end. On this date:

1. The **principal** (face value / par value) is returned to the investor
2. Any **final interest payment** is made (if applicable)
3. The instrument **ceases to exist** — no further pricing or trading

### Instruments with Maturity Dates

| Instrument | Typical Maturity | Settlement |
|------------|-----------------|------------|
| **Treasury Bills** | 4 weeks – 1 year | Par value at maturity |
| **Government Bonds** | 2 – 30 years | Par value + final coupon |
| **Corporate Bonds** | 1 – 30 years | Par value + final coupon |
| **Certificates of Deposit** | 1 month – 5 years | Principal + accrued interest |
| **Term Deposits** | 1 month – 5 years | Principal + interest |
| **P2P Loans** | 1 – 5 years | Remaining principal |

---

## 📉 Impact on Market Price

As a bond approaches maturity, its market price converges toward the **face value** (par), regardless of whether it was trading at a premium or discount:

$$
\lim_{d \to \text{maturity}} P(d) = \text{Face Value}
$$

This phenomenon is called **pull to par**:

- **Premium bonds** (price > par): Price gradually decreases toward par
- **Discount bonds** (price < par): Price gradually increases toward par

!!! example "Example: Government Bond Maturity"

    A 10-year government bond with face value €1,000 and 3% annual coupon:

    - **At issuance** (2015): Price = €1,000 (par)
    - **Mid-life** (2020): Price = €1,050 (premium, because market rates dropped)
    - **Near maturity** (2024): Price = €1,005 (converging to par)
    - **At maturity** (2025-01-15): Investor receives:
        - €1,000 (face value return)
        - €30 (final annual coupon)
        - Total: €1,030

!!! example "Example: Zero-Coupon Bond"

    A zero-coupon bond with face value $1,000 purchased at $850:

    - **At purchase**: Price = $850 (discount)
    - **At maturity**: Investor receives $1,000
    - **Implied return**: $150 ($1,000 − $850)
    - No interim interest payments — all return comes from the maturity settlement

---

## 📊 After Maturity

Once a maturity settlement event is recorded in LibreFolio:

- The asset's **price series ends** at the maturity date
- The settlement amount represents the **final data point**
- The asset can remain in the system for historical analysis but won't receive new price data

---

## 🧮 How LibreFolio Handles Maturity Settlement

In LibreFolio, a `MATURITY_SETTLEMENT` event is recorded with:

- **Date**: The maturity date
- **Amount**: The face value / principal amount returned
- **Currency**: The currency of settlement
- **Notes**: Optional description (e.g., "10Y Treasury bond matured")

For the **Scheduled Investment** provider, the maturity date is configured in the provider settings. The price calculation formula recognizes that no further accrual occurs after maturity:

$$
\text{price}(d) = \begin{cases}
\text{initial{\_}value} + \text{accrued}(d) - \Sigma\text{INT} + \Sigma\text{ADJ} & \text{if } d < \text{maturity} \\
\text{settlement{\_}amount} & \text{if } d \geq \text{maturity}
\end{cases}
$$

---

## 🔗 Related

- 📅 **[Asset Events Overview](../asset-events.md)** — All event types
- 📈 **[Interest](interest.md)** — Periodic coupon payments before maturity
- 📆 **[Day Count Conventions](../day-count.md)** — How accrual is calculated between coupon dates
- 📊 **[Price Adjustment](price-adjustment.md)** — Non-cash value changes before maturity


