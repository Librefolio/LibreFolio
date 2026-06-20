# 📚 Financial Theory

This section documents the financial models, conventions, and definitions used throughout LibreFolio.

## 📖 Overview

Accurate financial calculations are critical for a portfolio tracker. LibreFolio implements standard financial conventions to ensure consistency with broker reports and real-world data. This section is organized into four thematic areas.

## 🗺️ Conceptual Map

### 🏦 [Instruments](instruments/index.md)

The building blocks of any portfolio:

- **[Asset Types](instruments/asset-types/index.md)** — Stocks, ETFs, Bonds, Crypto, Real Estate, Indexes
- **[Transaction Types](instruments/transaction-types/index.md)** — Buy/Sell, Deposit/Withdrawal, Dividend, Fee, Interest, Transfer
- **[Asset Events](instruments/asset-events/index.md)** — Dividend, Interest, Split, Price Adjustment, Maturity Settlement

### 📊 [Technical Analysis](technical-analysis/index.md)

Data-driven chart overlays and mathematical reference curves:

- **[Indicators](technical-analysis/indicators/index.md)** — EMA, MACD, RSI, Bollinger Bands
- **[Synthetic Benchmarks](technical-analysis/synthetic-benchmarks/index.md)** — Linear Growth, Compound Growth, Sine Wave

### 📐 [Fundamentals](fundamentals/index.md)

Core financial concepts:

- **[Day Count Conventions](fundamentals/day-count.md)** — ACT/365, ACT/360, 30/360, ACT/ACT
- **[Returns & Growth Rates](fundamentals/returns.md)** — Simple vs Log returns, CAGR, annualization
- **[Taxation](fundamentals/taxation.md)** — Capital gains, tax deferral, Acc vs Dist

### 📈 [Portfolio Theory](portfolio-theory/index.md)

Modern Portfolio Theory and risk management:

- **[Diversification](portfolio-theory/diversification.md)** — Correlation, systematic vs idiosyncratic risk
- **[Asset Allocation](portfolio-theory/asset-allocation.md)** — Strategic, tactical, glide paths, rebalancing
- **[Risk Metrics](technical-analysis/risk-metrics/index.md)** — Sharpe, Sortino, Max Drawdown, Volatility
