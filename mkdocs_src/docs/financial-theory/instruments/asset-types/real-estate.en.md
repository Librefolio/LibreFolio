# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

**P2P / Crowdfunding** platforms let investors lend relatively small amounts to consumers,
businesses or real estate projects. The investor does not buy a share of anything: they hold a
**loan**, which typically pays fixed or variable interest and has a defined maturity date.

LibreFolio models these instruments as the **Crowdfunding family** of
[asset types](index.md#crowdfunding-family): the generic `CROWDFUND` and its real-estate
specialization, `CROWDFUND_REAL_ESTATE`.

---

## 🔑 Key Characteristics

| Property | Detail |
|----------|--------|
| **Codes in LibreFolio** | `CROWDFUND` — P2P and business lending, and the family's generic member · `CROWDFUND_REAL_ESTATE` — loans backed by property projects |
| **Pricing** | Not exchange-traded — value is typically the invested principal |
| **Currency** | Denominated in the platform's operating currency |
| **Income** | Periodic interest payments (monthly, quarterly, or at maturity) |
| **Liquidity** | Very low — funds are locked until maturity or buyback |
| **Typical providers** | Scheduled Investment, or prices entered by hand in the [Data Editor](../../../user/assets/detail/data-editor.md) |

---

## 🏷️ Which Code to Choose {: #which-code-to-choose }

| | Code | Choose it when the loan… |
|:---:|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | finances a property project |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | `CROWDFUND` | goes to consumers or businesses — or its purpose is not stated |

The rule is about what the loan finances, not about the platform. When in doubt, `CROWDFUND` — the
family's residual — is the safe choice; the price is that, in the
[content view](index.md#two-views-of-one-instrument), the loan no longer counts as real estate.

---

## 📊 How It Works

### 🏗️ Real Estate Crowdfunding — `CROWDFUND_REAL_ESTATE`

1. A platform lists a real estate project needing funding
2. Multiple investors contribute small amounts (€500–€10,000 typical)
3. The project pays interest on the invested capital
4. At maturity, the principal is returned (if the project succeeds)

### 💸 P2P Lending — `CROWDFUND`

1. Borrowers — consumers or businesses — request loans through a platform
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

## 🏠 Three Ways to Hold Property {: #three-ways-to-hold-property }

"Real estate" names three different instruments in LibreFolio, and what separates them is the
difference between **owning** and **lending**:

| | Code | What you hold | Nature of the claim |
|:---:|:---|:---|:---|
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | `REAL_ESTATE` | A share of a REIT or of another listed real-estate vehicle | Equity: you own part of the property's income and value |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | `ETF_REAL_ESTATE` | A share of an ETF holding such vehicles | Equity, through a basket |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | A loan to a property project, through a platform | Debt: you are owed interest and principal, repaid by the project |

All three contain real estate, so the [content view](index.md#two-views-of-one-instrument) puts them
in the same class, and their badge is teal. The claims, however, behave very differently when
markets fall — and that is where the stress scenarios part ways.

---

## 🌪️ In Stress Scenarios {: #in-stress-scenarios }

A stress scenario that shocks the portfolio by asset class gives every code its own bucket. In the
defaults of the two built-in asset-class scenarios:

| Code | Equity crash | Global risk-off |
|:---|---:|---:|
| `REAL_ESTATE` | −20 % | −15 % |
| `ETF_REAL_ESTATE` | −20 % | −15 % |
| `CROWDFUND_REAL_ESTATE` | −10 % | −10 % |
| `CROWDFUND` | −10 % | −10 % |

`CROWDFUND_REAL_ESTATE` is shocked as the **loan** it is, not as the property behind it. Listed
property is repriced every trading day, so a sell-off reaches it at once. A crowdfunding loan is
illiquid and not marked to market — nothing reprices it the next morning — and its risk is a
**default that arrives late**; in an instantaneous shock it therefore moves like the rest of
`CROWDFUND`.

!!! warning "Known limit: a prolonged property crisis"

    A hypothetical shock is a single-period statement: it has no time in it. The credit risk of
    property-backed loans is precisely the kind that builds up over time, as a property crisis
    drags on — so the −10 % **understates** that risk in a prolonged crisis. Every bucket shock is
    editable: if that is the scenario you want to test, raise the `CROWDFUND_REAL_ESTATE` bucket
    yourself.

How buckets are applied, and what happens to the ones you do not configure, is explained in
[Hypothetical Shock](../../technical-analysis/risk-metrics/hypothetical-shock.md).

---

## 🔧 Modeling in LibreFolio

The **Scheduled Investment** provider is designed for these instruments. From the schedule you
configure, it generates:

- **[Interest events](../asset-events/interest.md)** — periodic coupon payments, when the schedule is
  set to generate them
- **[Maturity Settlement events](../asset-events/maturity-settlement.md)** — the final capital return
  at the end of the term

**[Price Adjustment events](../asset-events/price-adjustment.md)** that you record yourself — a
write-down when a project underperforms — are applied to the value it computes.

---

## 🔗 Related

- 📊 **[Asset Types](index.md)** — The two-level taxonomy and how subtypes roll up
- 📈 **[Interest Events](../asset-events/interest.md)** — How interest accrual works
- 🏁 **[Maturity Settlement](../asset-events/maturity-settlement.md)** — End-of-life capital return
- 📅 **[Day Count Conventions](../../fundamentals/day-count.md)** — How interest periods are calculated
- ⚡ **[Hypothetical Shock](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — How stress scenarios shock asset-class buckets
