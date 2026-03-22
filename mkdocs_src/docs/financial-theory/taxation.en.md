# 💰 Taxation & Tax Efficiency

Understanding taxation is essential for maximizing long-term investment returns. This page covers the theoretical foundations — **not jurisdiction-specific rules** — of how taxes interact with portfolio growth.

!!! warning "Not financial advice"
    LibreFolio does not provide tax advice. Every jurisdiction has different rules regarding tax rates, holding periods, loss carry-forward, and matching methods. Consult a qualified tax professional for your specific situation.

---

## 📊 Capital Gains & Losses

When you sell an asset, the difference between the sale price and the purchase price determines your **capital gain** or **capital loss**:

$$
\text{Capital Gain} = P_{sell} - P_{buy} - \text{Fees}
$$

- **Capital Gain** ($> 0$): You sold for more than you paid → taxable event in most jurisdictions
- **Capital Loss** ($< 0$): You sold for less than you paid → may offset future gains

### 🔄 Realized vs Unrealized

| Type | Definition | Tax Impact |
|------|-----------|------------|
| **Unrealized** (paper gain/loss) | Asset still held; gain/loss exists only on paper | Not taxed (in most jurisdictions) |
| **Realized** | Asset sold; gain/loss is locked in | Typically triggers a tax event |

This distinction is the foundation of **tax deferral** — by not selling, you defer the tax event indefinitely.

### 📋 Matching Methods

When you've bought the same asset multiple times at different prices, which purchase does a sale match against?

| Method | Rule | Effect |
|--------|------|--------|
| **FIFO** (First In, First Out) | Oldest shares sold first | Most common default |
| **LIFO** (Last In, First Out) | Newest shares sold first | May minimize/maximize gains |
| **Specific Identification** | You choose which lot to sell | Maximum tax optimization |

!!! info "LibreFolio uses FIFO"
    LibreFolio computes capital gains using **FIFO** matching at runtime. The matching is calculated on-demand, not stored in the database.

---

## 🔄 Loss Carry-Forward

Most jurisdictions allow you to **carry forward** capital losses to offset future capital gains:

$$
\text{Taxable Gain}_t = \max(0, \text{Realized Gains}_t - \text{Carried Losses}_{t-1})
$$

Key parameters that vary by jurisdiction:

- ⏳ **Duration**: How long losses can be carried (e.g., 4 years in Italy, unlimited in Germany, 7 years in the US for certain types)
- 📊 **Scope**: Whether losses from one asset class can offset gains from another
- 🚫 **Wash sale rules**: Restrictions on re-buying a sold asset within a short window to claim the loss

---

## ⏳ Tax Deferral Advantage { #tax-deferral-advantage }

One of the most powerful concepts in tax-efficient investing is **deferring** the tax event as long as possible. The mathematics strongly favor deferral:

### 📐 The Formula

Compare two scenarios over $n$ years with annual return $r$ and tax rate $\tau$:

**Scenario A — Tax annually** (e.g., distributing fund):

$$
V_A = P \cdot (1 + r \cdot (1 - \tau))^n
$$

**Scenario B — Tax at the end** (e.g., accumulating fund):

$$
V_B = P \cdot (1 + r)^n - \tau \cdot [P \cdot (1 + r)^n - P] = P \cdot [(1 + r)^n \cdot (1 - \tau) + \tau]
$$

### 📊 Numerical Example

With $P = 10{,}000$, $r = 7\%$, $\tau = 26\%$, $n = 20$ years:

| Scenario | Final Value | Effective Return |
|----------|------------|-----------------|
| Tax annually | €28,398 | 5.18% p.a. |
| Tax at end | €31,616 | 5.93% p.a. |
| **Deferral advantage** | **+€3,218** | **+0.75% p.a.** |

The advantage grows exponentially with time — over 30 years, the gap widens to over €8,000 on the same €10,000 investment.

---

## 📦 Accumulating vs Distributing Instruments

This deferral advantage manifests directly in the choice between accumulating and distributing investment vehicles:

### 📈 Accumulating (e.g., Acc ETFs)

- Dividends are **reinvested internally** by the fund
- **No taxable event** until you sell the fund shares
- Full benefit of [compound growth](synthetic-benchmarks.md#compound-growth) on the pre-tax amount
- Ideal for long-term investors seeking maximum growth

### 💵 Distributing (e.g., Dist ETFs)

- Dividends are **paid out** to you periodically
- Each distribution is a **taxable event** (taxed immediately)
- You receive cash but lose the compounding benefit on the taxed portion
- Useful if you need income from your investments

### 🔗 Connection to Growth Models

- **[Linear Growth](synthetic-benchmarks.md#linear-growth)** approximates the behavior when dividends are received but **not reinvested** — growth is additive
- **[Compound Growth](synthetic-benchmarks.md#compound-growth)** represents the ideal case with full reinvestment — growth is multiplicative and benefits most from tax deferral

---

## ⚠️ Jurisdiction-Specific Considerations

Every country has its own tax framework. Key parameters that vary:

| Parameter | Examples |
|-----------|---------|
| **Tax rate on capital gains** | 26% (Italy), 25% (Germany), 0-20% (US, depending on holding period) |
| **Holding period benefits** | Some countries reduce rates for long-term holdings |
| **Loss carry-forward duration** | 4 years (Italy), unlimited (Germany), 7 years (US for some types) |
| **Double taxation treaties** | Affect dividends from foreign stocks |
| **Tax-free allowances** | Annual thresholds below which gains are not taxed |
| **Crypto-specific rules** | Rapidly evolving; often treated differently from traditional assets |

!!! abstract "LibreFolio's role"
    LibreFolio tracks your transactions and computes realized gains/losses using FIFO matching. It provides the **data foundation** for tax reporting, but does not generate tax declarations or apply jurisdiction-specific rules. Export your transaction data and consult a tax professional.

---

## 🔗 Related

- 📈 **[Returns & Growth Rates](returns.md)** — How to measure and annualize returns
- 🎯 **[Synthetic Benchmarks](synthetic-benchmarks.md)** — Linear vs compound growth visualization
- 📅 **[Day Count Conventions](day-count.md)** — How time periods affect calculations

