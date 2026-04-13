# ![](../../../static/icons/asset-types/other.png){: width="32" style="vertical-align: middle;" } Index & Benchmark

An **index** is a statistical measure of a section of the financial market. It tracks the performance of a group of assets and serves as a **benchmark** against which investors measure their own portfolio performance.

---

## 🔑 Key Characteristics

| Property | Detail |
|----------|--------|
| **Tradeable?** | Not directly — but ETFs and futures track indexes |
| **Examples** | S&P 500, MSCI World, FTSE 100, DAX, Nikkei 225 |
| **Use in LibreFolio** | Reference for [Asset Comparison](../../../user/assets/detail/signals.md) signal |
| **Pricing** | Computed from constituent weights, not traded on an exchange |

---

## 📊 How Indexes Are Constructed

### 📈 Weighting Methods

| Method | Formula | Example |
|--------|---------|---------|
| **Market-cap weighted** | Weight ∝ company market cap | S&P 500, MSCI World |
| **Price weighted** | Weight ∝ share price | Dow Jones, Nikkei 225 |
| **Equal weighted** | All constituents have same weight | S&P 500 Equal Weight |

### 🔄 Rebalancing

Indexes are periodically rebalanced — constituents are added, removed, or re-weighted. This typically happens quarterly. ETFs that track the index must adjust their holdings accordingly.

---

## 📐 Using Benchmarks in LibreFolio

LibreFolio offers two types of benchmarks:

### 📊 Real Benchmarks (Asset Comparison)

Compare your asset's chart against another real asset (e.g., compare your stock against the S&P 500 ETF). This uses the **Asset Comparison** signal overlay.

### 🎯 Synthetic Benchmarks

Mathematical reference curves that answer "what if my asset had grown at X% per year?":

- **[Linear Growth](../../technical-analysis/synthetic-benchmarks/linear.md)** — Simple interest model
- **[Compound Growth](../../technical-analysis/synthetic-benchmarks/compound.md)** — Compound interest model
- **[Sine Wave](../../technical-analysis/synthetic-benchmarks/sine-wave.md)** — Cyclic reference for seasonality

---

## 🔗 Related

- 📊 **[ETFs](etfs.md)** — Instruments that track indexes
- 🎯 **[Synthetic Benchmarks](../../technical-analysis/synthetic-benchmarks/index.md)** — Mathematical reference curves
- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — Measuring performance vs benchmark
