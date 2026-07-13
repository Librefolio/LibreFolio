# Changelog

All notable changes to LibreFolio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-13

### Added

#### 📊 Core & Dashboard Engine
- **3-Pool Cash Model Engine**: Accurate event-driven balance tracking (Known/Resolved/Working cash pools) with precise separation of transactions.
- **Advanced ROI Solvers**: High-performance implementations for Time-Weighted Rate of Return (TWRR) and Money-Weighted Rate of Return (MWRR/XIRR) with Newton-Raphson boundary caps.
- **Cost Basis Calculations**: Real-time Weighted Average Cost (WAC) calculations and First-In, First-Out (FIFO) cost basis tracking computed at runtime.
- **ECharts Dashboard**: Interactive widgets including growth chart, asset allocation pie, geography distribution map, sector weightings, and portfolio exposure treemap.
- **Responsive Layout**: Collapsible sidebar, touch-friendly UI design, and complete theme toggle (Light / Dark modes).

#### 📥 Broker Report Import Module (BRIM)
- **Import Wizard v5**: Stepper-based import flow for broker statements (Upload, Configure Parser, Analyse, Reconcile Assets & Duplicates, Bulk Review, Commit).
- **11 Supported Brokers**: Native parsers for Interactive Brokers (IBKR), Degiro, eToro, Directa SIM, Charles Schwab, Revolut, Coinbase, Freetrade, Finpension, Trading212, and a Generic CSV mapping tool.
- **On-the-fly Creation**: Prompt to create missing brokers or assets directly during the import flow without aborting.
- **Duplicate Detection**: 4-level duplicate confidence scoring (Likely/Possible with matching rules) to prevent double entry.

#### 💱 Forex & Currency Routing
- **Triangulation Graph**: Arbitrary multi-currency exchange rate conversions via direct or multi-hop path routing.
- **Official Providers**: Auto-sync from European Central Bank (ECB), Federal Reserve (FED), Bank of England (BOE), and Swiss National Bank (SNB).
- **MANUAL Override Sentinel**: Ability to manually input specific exchange rates or edit sync buffers via data grid editor.

#### 📈 Asset Providers & Scheduler
- **Price Synchronization**: Multi-source price updates from Yahoo Finance (async offload), justETF, Borsa Italiana, and custom CSS scrapers.
- **Scheduled Investments**: Automated creation of periodic purchasing/accumulation plans.
- **Scheduler Daemon**: Leader-election backend daemon (psutil/lock-file based) that synchronizes historical and current market data on a cron schedule.

#### 🧠 Technical Analysis (Signals)
- **Indicator Overlays**: Automated charts showing EMA, MACD, RSI, and Bollinger Bands.
- **FX Pair & Benchmark Comparison**: Overlap benchmark lines on any price graph to compare performance.

#### 🔒 Security, Admin & Localisation
- **Role-Based Sharing**: Multi-user permissions on broker accounts (Owner, Editor, Viewer).
- **Static Assets Uploader**: Secure management and crop tool (Cropper.js) for upload of custom broker/user icons and files.
- **PWA Support**: Installable Progressive Web App (PWA) with offline capabilities.
- **Multi-language Support**: Complete localization in English, Italian, French, and Spanish.
