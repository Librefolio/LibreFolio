# Changelog

All notable changes to LibreFolio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-08-07

The first feature release after 1.0. It introduces the **Risk Analysis** subsystem (beta), rebuilds technical analysis as a backend plugin platform, ships the **V3 AI Export** catalog, adds 18 new broker importers, and replaces the legacy valuation cascade with a single unified price resolver.

### 🧪 Beta

#### 📉 Risk Analysis — new subsystem

Quantitative risk and allocation analytics, powered by [QuantLib](https://www.quantlib.org/) and [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib).

> **This subsystem is beta.** Analytic parameters, result shapes and the `/api/v1/risk` contract may still change in a future release without a major version bump. Results are intended as decision support, not as authoritative financial figures — always read the reported data-quality status alongside the numbers.

- **9 risk analytics**, registered through a plugin registry with schema-driven parameter forms (the same pattern already used by Asset, FX and BRIM providers):
    - **Historical risk metrics** — historical volatility, drawdown, Sharpe and Sortino from the selected scope's canonical returns.
    - **Historical VaR / CVaR** — historical-simulation loss estimates at a configurable confidence level and horizon.
    - **Drawdown summary** — dated current and maximum peak-relative drawdown episodes with recovery status (`no_drawdown` / `recovered` / `open`).
    - **Correlation** — Pearson correlation matrix computed on target-currency returns over a joint calendar.
    - **Risk contribution** — current-composition volatility contributions broken down by asset.
    - **Stress test** — apply hypothetical shocks or replay a real historical period, from a typed and audited scenario catalog.
    - **Comparison** — performance and risk measured against a real comparison asset or benchmark.
    - **Simulation** — conditional GBM return percentiles from historical drift and covariance estimates (QuantLib).
    - **Portfolio allocation** — builds a hypothetical composition from the selected sample, strategy, estimators and constraints (Riskfolio-Lib).
- **Scope-neutral analytics** — each analytic declares the scopes it supports (`asset`, `asset_set`, `portfolio`) and the return mode it consumes (`price_only` or `twrr`), so the same engine serves an asset detail page and a whole portfolio.
- **Process isolation** — QuantLib and Riskfolio-Lib run inside dedicated `spawn` workers. A heavy, hanging or failing optimisation can never block the async event loop or take down the API. Idle workers are reaped without interrupting jobs that are still running.
- **Honest failure reporting** — a dedicated error taxonomy (`insufficient_history`, `undefined_metric`, `invalid_covariance`, `optimization_infeasible`, `resource_limit`, `worker_busy`, `execution_timeout`, …) plus a per-result status (`ok` / `partial` / `unavailable` / `failed`). An analysis reports *why* it could not compute instead of silently returning a misleading number.
- **Cached Risk UI** with shared Asset/FX detail controls and content-keyed result caching.
- Monte Carlo random seeds are kept separate from QMC Sobol start indexes, so runs stay reproducible and low-discrepancy sequences are not accidentally correlated.

### Added

#### 🧠 Technical Analysis — backend Signals platform
- **Indicators are now backend Python plugins**: a single validated implementation is shared by charts, the REST API and AI consumers, replacing the previous browser-side calculations.
- **22 indicator plugins** exposing **17 Asset** and **9 FX** schema-driven indicators — SMA, EMA, MACD, RSI, Bollinger, ADX, Aroon, ATR/NATR, CCI, Donchian, KAMA, MFI, OBV, PPO, ROC, Stochastic RSI, plus risk-oriented overlays (Drawdown, Rolling Beta, Rolling Return, Rolling Sharpe, Rolling Volatility).
- Fail-fast plugin runtime, registry, `SignalService`, and chart annotations with independent components, zones, warnings and styles.
- **Live preview in global chart settings** via `POST /signals/preview`: indicators are computed on a caller-supplied synthetic curve with no DB or I/O, so the global "asset"/"forex" settings modal renders a real overlay instead of an "unavailable" banner.
- Grouped indicator search, KaTeX formula labels, responsive cards and per-signal diagnostics.
- Incomplete OHLCV inputs render as honest partial contiguous segments instead of interpolated fiction.

#### 🤖 AI Export — rebuilt catalog
- Reworked, versioned export catalog: **8 autonomous public datasets** and **11 task-oriented analyses**, composed from 40 internal dataset blocks.
- **Task-aware prompt composition** — drawdown, income, concentration, cost and FX contexts are selected per analysis, so financial prompts stay focused without weakening full technical exports.
- Snapshots render as compact, auditable tables with local entity references; weights, HHI, FIFO, numeric and missing-price semantics are stated explicitly in the prompt.
- Adaptive temporal buckets, plugin-owned signal aggregation, sampling manifests, and coverage/broker-scope/partial-history disclosure embedded in the export.
- Focused financial context, capital-loss offset prompts, and 10-minute login-bound panel memory for draft continuity.

#### 📥 Broker imports (BRIM)
- **18 new broker plugins** (29 supported importers in total): Avanza, Bitvavo, BUX, CoinTracking, Crédit Agricole, Crypto.com, Delta, Disnat, Fineco, Intesa Sanpaolo, InvestEngine, Investimental, Parqet, Rabobank, Relai, Saxo, Swissquote, Trade Republic and XTB.
- **Crédit Agricole** reads both the account-movements and the securities-dossier exports, in CSV or XLSX, auto-detecting which one was loaded — including bond maturities, automatic cash counter-entries and succession transfers as cashless in-kind adjustments.
- **Directa** exports are now accepted as XLSX as well as CSV.
- **Duplicate resolver (wizard step 3)** — a reorderable file-priority list plus one collapsible group per duplicate cluster, letting you choose exactly which leg to keep across a multi-file import.
- **N-way compare modal** — compare any number of candidate transactions side by side (previously limited to 2), with provenance-aware titles.
- **Maturity / redemption notices** — descriptions are scanned for maturity cues and the affected assets are flagged with an advisory banner, so delisted securities are not silently mispriced.
- **"Reuse existing asset" prompt** — when an imported instrument matches an asset you already have, choose to reuse it (optionally merging the import's search keys) instead of creating a duplicate.
- **Plugin diagnostics** — `GET /api/v1/system/plugin-diagnostics` and a new panel in *Settings → Info* report, per registry, which plugin files failed to load and why. A missing runtime dependency is now diagnosable instead of a silent skip.

#### 📊 Portfolio, valuation & FIFO
- **Unified daily price resolver** — one pure, deterministic calculator (`MARKET` → `TRADE_AVG` → `CARRIED`/LOCF → `MISSING`) is now the single source of valuation marks, so NAV, MWRR, TWRR and ROI all read from the same numbers. Staleness is reported with the project-wide backward-fill contract.
- **FIFO Engine v4** — FEE/TAX and asset income are allocated into the lot engine (deterministic pooling, D-1 eligibility, broker scope, LONG/SHORT crossing), producing **gross *and* net** P&L and returns plus a 3-level economic audit (groups → operations → lots).
- **Net annualized return (CAGR)** column across FIFO lots, holdings and period contribution — net of income and costs, with a 30-day minimum window guard so a one-week hold no longer reports an absurd annualised figure.
- **Estimated market line** on the FIFO lot chart, drawn dashed on estimated points, for positions with no recent quote.
- **Oldest open lot** column (hidden by default) on the exposure and contribution tables.
- In-kind `ADJUSTMENT` transfers carrying a per-unit cost basis now open real-cost FIFO lots and move the capital baseline symmetrically, so inherited or transferred-in positions are valued and annualised correctly.

#### 🔍 Asset search & providers
- **`ddgs` metasearch link-finder** replaces the previous DuckDuckGo HTML scraper, which had begun returning rate-limited empty results.
- **Borsa Italiana mutual funds** priced by internal fund code, with a URL→asset resolver and an opt-in provider `resolve_url` capability.
- **`identifier_other` is now a JSON list** of soft identifiers, additive across imports (Alembic migration `002`, data-only and idempotent).
- Search accepts ISIN and candidate-name `hints` to disambiguate the provider fallback, and returns structured `error_code` values so an expected-empty result is shown as a warning, not a hard failure.

#### 🏦 Brokers
- **User picker in the sharing panel** — a real select listing all users on open and narrowing as you type, replacing the free-text field that needed ≥2 characters and showed nothing on click.
- **"View in Transactions" deep-link** from a broker's Transactions tab, carrying the broker and the active column filters through to the full Transactions page (and registering on the navigation stack, so Back works).
- **Delete guard** — deleting a broker that still holds transactions now returns the transaction count and opens a guard dialog linking to the filtered view, instead of failing silently.
- All broker pickers list only brokers you can actually access, with sharing-level icons.

### Changed

- **Legacy valuation engine removed** — the unified resolver is the only valuation path. The `LIBREFOLIO_RESOLVER_VALUATION` transition flag, the `LAST_BUY_PRICE` / `LAST_SEED_COST` fallback tiers and the duplicate per-path price maps are gone.
- **Legacy AI Export runtime removed** — the unreachable profile/assembler stack was deleted so the catalog, prompts and tests cannot drift apart. All public prompt variants are preserved.
- Technical analysis moved from the frontend to the backend (see Signals platform above); frontend controls, rendering, axes and batching now consume backend results.
- Asset and FX domains were folded into the existing APIs rather than kept as parallel surfaces.
- The 500-item cap on bulk import validation was removed, so large multi-file merges import in one pass.
- Borsa Italiana search now performs a single on-site fetch and emits both language rows from it, roughly halving search latency (~2.6s → ~1.2s).
- Candidate URL resolution during asset search runs concurrently instead of sequentially, and creating an asset no longer blocks the modal on the provider history sync.
- The dashboard data-quality banner is foldable and offers one "go to asset" link per affected asset, instead of a single CTA that only opened the first one.
- Documentation: the English MkDocs set was realigned with the shipped code, adding Price Resolution and Net Annualized Return pages, a duplicate-detection developer page, and user guides for the new brokers.

### Fixed

- **Inflated ROI on portfolios seeded in kind** — in-kind adjustments contributed to the capital baseline but not to the cash-only flow used as the ROI denominator, so transferred-in capital appeared as pure gain. ROI, TWRR, MWRR and the headline figures now all derive from the same flows.
- **Fully-closed positions showed "—" for annualized return** — realized net return is now annualised over the position's real flight time, dust-aware for partial redemptions.
- **False "valued at cost" warnings** — the data-quality flag was computed over the whole history, so an asset kept the flag forever once it had ever been price-less. It is now evaluated as of the valuation date.
- **Runaway asset search loop** — a zero-result query re-satisfied the auto-search condition and re-fired indefinitely, flooding the backend. Fixed with a per-query guard plus request cancellation.
- **Cost basis flat after a bond maturity** — an unidentifiable Crédit Agricole redemption was booked as a plain cash deposit, inflating paid-in capital. It is now booked as a sale at par.
- **XLSX broker plugins missing in Docker** — `openpyxl` was declared as a dev dependency, so the published image shipped without it and the Crédit Agricole, Intesa and Fineco plugins were silently skipped.
- **Import wizard flagged duplicates against rows marked for deletion** — pending deletions are now excluded from duplicate matching.
- **Broker detail page-size selector did nothing** — the grouped transactions table never received the page-size callback.
- **KPI card percentages moved with the selected period** — net worth now shows total P&L over invested capital, and the period card shows the last-day delta.
- **Empty error tooltips in the sync modals** — an empty error array is no longer treated as a present-but-blank message.
- Transactions "without asset" filter, dynamic default column visibility in `DataTable`, right-aligned Asset/FX table toolbars, cross-account cache leakage on auth changes, and a number of translation inconsistencies across EN/IT/FR/ES.

### ⚠️ Breaking changes

These affect beta and internal surfaces only — the stable REST API and the database schema are unchanged.

- **AI Export**: the granular public dataset IDs, `broker.cost_efficiency`, `fx.conversion_planning` and `asset.drawdown_recovery` are no longer part of the public catalog. Use the new datasets and analyses instead.
- **Signals**: `gain_loss_change_1d_percent` is now computed on the previous position *market value* rather than the previous unrealized P&L.
- **DataTable**: the column-visibility persistence key changed (`columnVisibility` → `columnVisibilityOverrides`). Saved show/hide preferences are not migrated and each table resets to its default once; column order and widths are preserved.

---

## [1.0.0] - 2026-07-20

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
