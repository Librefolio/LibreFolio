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
| **Weighted average cost** | No lot is matched: every unit carries the average cost of the pool | Smooths the result over the purchases |
| **Specific Identification** | You choose which lot to sell | Maximum tax optimization |

A small example. Bought 10 units at 100 in January and 10 at 120 in March; 10 sold at 130 in June:

| Method | Lot closed | Realized | What stays |
|--------|-----------|----------|------------|
| FIFO | January | $10 \times (130 - 100) = 300$ | 10 at 120 |
| LIFO | March | $10 \times (130 - 120) = 100$ | 10 at 100 |
| Average cost (110) | none | $10 \times (130 - 110) = 200$ | 10 at 110 |

Over the whole life of a position the methods realize the same total; they differ in **when** the gain is realized, and
so in which tax year it falls.

!!! info "LibreFolio matches in FIFO and in LIFO"

    The lots analysis computes both matchings at runtime, in one request, and the lots panel switches between them (FIFO
    first, not saved). The matching is calculated on demand, never stored in the database. The rest of the app — the
    Dashboard, the broker pages — realizes on the **weighted average cost**, which is not a matching method: the
    [weighted average cost](../technical-analysis/performance-metrics/weighted-average-cost.md) lines exist beside the
    lots. Specific identification (choosing the lot) is not offered.

### 🇮🇹 Italy: which method the law names { #italy }

Italian law names a different method for each of its two tax regimes for individuals:

| Regime | Who computes the tax | Method | Source |
|--------|----------------------|--------|--------|
| **Dichiarativo** (self-declared) | You, in your tax return | **LIFO**: the units sold first are the ones acquired most recently | Art. 67, paragraph 1-bis, TUIR (d.P.R. 917/1986), for the income of 2026; from 1 January 2027 art. 76, paragraph 2, of the new TUIR (d.lgs. 19 June 2026, no. 117), unchanged in substance. The Agenzia delle Entrate calls it the «metodo L.I.F.O.» (Risposta no. 204/2023) |
| **Amministrato** (managed by the broker) | The intermediary, as withholding agent | **Weighted average cost** of each homogeneous category: no lot is matched | Art. 6, paragraph 4, d.lgs. 461/1997; from 2027 art. 306, paragraph 5, of the new TUIR |

FIFO is the method of neither regime. So, for someone who declares in Italy, the **LIFO view** of the lots panel is the
one close to the law; for someone in the managed regime, the closest figure is the realized gain on the average cost
that the Dashboard and the broker pages show.

!!! warning "Three limits of LibreFolio's matching"

    1. **A lot is dated with the data LibreFolio has.** With every broker of a transfer in the analysis, a transferred lot
       keeps its purchase date and the arrival broker's queue orders it by that date. Seen from one broker only, the
       units arrive with no purchase date, so the lot is born on the day it arrives. The Dashboard and a broker's page
       can therefore date a lot differently, and close a different one, in either method.
    2. **The queue is per broker.** A sale closes the lots held at the broker that sells, in FIFO as in LIFO. The rule
       on LIFO does not name the account: the sources disagree on whether it applies per account (the Agenzia, on
       foreign-currency accounts: «per ciascun conto», Risposta no. 204/2023) or across all the taxpayer's accounts (a
       commentary in Il Sole 24 Ore, 8 December 2018).
    3. **The managed regime does not match lots.** There the law uses the weighted average cost: read the realized gain
       on the average cost, not a lot view.

!!! info "Points the sources leave open"

    - **ETFs and funds**: a gain is income from capital, a loss a «reddito diverso»; the withholding rule speaks of the
      weighted average cost of subscription or purchase, while the loss follows art. 67. In the self-declared regime
      the guides disagree, and no document of the Agenzia settles it.
    - **Crypto-assets**: paragraph 1-bis does not name them; LIFO for them in the self-declared regime is practice
      reported by secondary sources, not the text of the law.

    Sources: [Agenzia delle Entrate, Risposta no. 204/2023](https://www.agenziaentrate.gov.it/portale/documents/20143/4988698/Risposta+n.+204_2023.pdf/5189c15d-4fe7-f043-606b-2843bc00df74);
    [art. 67 TUIR](https://www.brocardi.it/testo-unico-imposte-redditi/titolo-i/capo-vii/art67.html);
    [d.lgs. 117/2026, new TUIR (Gazzetta Ufficiale)](https://www.gazzettaufficiale.it/eli/id/2026/07/03/26G00131/sg);
    [art. 6 d.lgs. 461/1997 (Normattiva)](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:1997-11-21;461~art6).

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
- Full benefit of [compound growth](../technical-analysis/synthetic-benchmarks/compound.md) on the pre-tax amount
- Ideal for long-term investors seeking maximum growth

### 💵 Distributing (e.g., Dist ETFs)

- Dividends are **paid out** to you periodically
- Each distribution is a **taxable event** (taxed immediately)
- You receive cash but lose the compounding benefit on the taxed portion
- Useful if you need income from your investments

### 🔗 Connection to Growth Models

- **[Linear Growth](../technical-analysis/synthetic-benchmarks/linear.md)** approximates the behavior when dividends are received but **not reinvested** — growth is additive
- **[Compound Growth](../technical-analysis/synthetic-benchmarks/compound.md)** represents the ideal case with full reinvestment — growth is multiplicative and benefits most from tax deferral

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

    LibreFolio tracks your transactions and computes realized gains/losses on the weighted average cost, and per lot in FIFO and in LIFO. It provides the **data foundation** for tax reporting, but does not generate tax declarations or apply jurisdiction-specific rules. Export your transaction data and consult a tax professional.

---

## 🔗 Related

- 📈 **[Returns & Growth Rates](returns.md)** — How to measure and annualize returns
- 🎯 **[Synthetic Benchmarks](../technical-analysis/synthetic-benchmarks/index.md)** — Linear vs compound growth visualization
- 📅 **[Day Count Conventions](day-count.md)** — How time periods affect calculations


