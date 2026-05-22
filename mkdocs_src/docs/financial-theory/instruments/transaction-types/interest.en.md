# ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" } Interest (Transaction)

An **interest transaction** records interest income received from bonds, savings accounts, P2P loans, or other fixed-income instruments. It represents the portfolio-level impact of an [interest event](../asset-events/interest.md).

---

## 🔑 Key Properties

| Property | Detail |
|----------|--------|
| **Code** | `INTEREST` |
| **Cash effect** | ⬆️ Increases balance |
| **Asset effect** | — (principal unchanged) |
| **Tax event** | Yes (taxable income) |

---

## 📊 Interest Sources

| Source | Description | Frequency |
|--------|-------------|-----------|
| **Bond coupons** | Fixed or floating rate payments | Semi-annual / Annual |
| **Savings interest** | Interest on cash deposits | Monthly / Quarterly |
| **P2P loan payments** | Interest portion of loan repayments | Monthly |
| **Crowdfunding returns** | Fixed-rate returns on projects | Varies |

---

## 💡 When to Use

Use an `INTEREST` transaction when cash arrives in your broker account as interest income. This is distinct from:

- **Dividend** — income from equity (stocks, distributing ETFs)
- **Maturity Settlement** — return of principal at bond maturity

!!! tip "Theory & formulas"

    For the mathematics of interest accrual (simple vs compound, day count conventions, yield metrics), see:

    - **[📈 Interest Events](../asset-events/interest.md)** — Accrual mechanics and price impact
    - **[📅 Day Count Conventions](../../fundamentals/day-count.md)** — How interest periods are calculated

---

## 🔗 Related

- 📈 **[Interest Events](../asset-events/interest.md)** — Accrual and coupon mechanics
- 🏛️ **[Bonds](../asset-types/bonds.md)** — The primary interest-bearing asset
- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — Measuring income return
- 📅 **[Day Count Conventions](../../fundamentals/day-count.md)** — How interest periods are calculated
