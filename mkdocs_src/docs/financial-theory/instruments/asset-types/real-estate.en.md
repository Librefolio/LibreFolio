# <img src="../../../static/icons/asset-types/crowdfunding.png" width="32" style="vertical-align: middle;" /> P2P / Crowdfunding

**P2P / Crowdfunding** platforms allow investors to participate in real estate projects or consumer/business loans with relatively small amounts. These instruments typically offer fixed or variable interest payments and have a defined maturity date.

---

## 🔑 Key Characteristics

| Property | Detail |
|----------|--------|
| **Code in LibreFolio** | `CROWDFUNDING` |
| **Pricing** | Not exchange-traded — value is typically the invested principal |
| **Currency** | Denominated in the platform's operating currency |
| **Income** | Periodic interest payments (monthly, quarterly, or at maturity) |
| **Liquidity** | Very low — funds are locked until maturity or buyback |
| **Typical providers** | Scheduled Investment, Manual |

---

## 📊 How It Works

### 🏗️ Real Estate Crowdfunding

1. A platform lists a real estate project needing funding
2. Multiple investors contribute small amounts (€500–€10,000 typical)
3. The project pays interest on the invested capital
4. At maturity, the principal is returned (if the project succeeds)

### 💸 P2P Lending

1. Borrowers request loans through a platform
2. Investors fund portions of loans
3. Borrowers repay principal + interest over the loan term
4. The platform distributes payments to investors

---

## ⚠️ Risk Factors

| Risk | Description |
|------|-------------|
| **Default risk** | The borrower/project may fail to repay |
| **Liquidity risk** | Cannot sell before maturity (unlike stocks) |
| **Platform risk** | The platform itself may go bankrupt |
| **Concentration risk** | Each investment is a single project/borrower |

---

## 🔧 Modeling in LibreFolio

The **Scheduled Investment** provider is designed for these instruments. It generates:

- **[Interest events](../asset-events/interest.md)** — Periodic coupon payments based on configured rate and schedule
- **[Maturity Settlement events](../asset-events/maturity-settlement.md)** — Final capital return at end of term
- **[Price Adjustment events](../asset-events/price-adjustment.md)** — Write-downs if the project underperforms

---

## 🔗 Related

- 📈 **[Interest Events](../asset-events/interest.md)** — How interest accrual works
- 🏁 **[Maturity Settlement](../asset-events/maturity-settlement.md)** — End-of-life capital return
- 📅 **[Day Count Conventions](../../fundamentals/day-count.md)** — How interest periods are calculated
