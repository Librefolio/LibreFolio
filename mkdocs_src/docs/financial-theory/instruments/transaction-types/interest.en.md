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

## 📐 Simple vs Compound Interest

### 📏 Simple Interest

Interest calculated only on the original principal:

$$
I = P \times r \times t
$$

### 📈 Compound Interest

Interest calculated on principal + accumulated interest:

$$
A = P \times (1 + r)^t
$$

The difference between simple and compound interest is the foundation of the [Linear vs Compound Growth](../../technical-analysis/synthetic-benchmarks/index.md) benchmark comparison.

---

## 🔗 Related

- 📈 **[Interest Events](../asset-events/interest.md)** — Accrual and coupon mechanics
- 🏛️ **[Bonds](../asset-types/bonds.md)** — The primary interest-bearing asset
- 📅 **[Day Count Conventions](../../fundamentals/day-count.md)** — How interest periods are calculated
