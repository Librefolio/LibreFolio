# Changelog

All notable changes to LibreFolio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-09-07

The first feature release after 1.0. It introduces the **Risk Analysis** subsystem (beta), rebuilds technical analysis as a backend plugin platform, ships the first public **AI Export V1** catalog, adds 19 new broker importers, and replaces the legacy valuation cascade with a single unified price resolver. Two beta-testing waves (early August with real Crédit Agricole reports, late August on a fresh production install) reshaped the import wizard around asset identity and added an ownership-aware dashboard, broker self-service sharing, a Docker light variant and an in-app changelog on top.

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

### ✨ Added

#### 🧠 Technical Analysis — backend Signals platform
- **Indicators are now backend Python plugins**: a single validated implementation is shared by charts, the REST API and AI consumers, replacing the previous browser-side calculations.
- **22 indicator plugins**, all available for **Asset** data and **9** also compatible with **FX** — SMA, EMA, MACD, RSI, Bollinger, ADX, Aroon, ATR/NATR, CCI, Donchian, KAMA, MFI, OBV, PPO, ROC, Stochastic RSI, plus risk-oriented overlays (Drawdown, Rolling Beta, Rolling Return, Rolling Sharpe, Rolling Volatility).
- Fail-fast plugin runtime, registry, `SignalService`, and chart annotations with independent components, zones, warnings and styles.
- **Live preview in global chart settings** via `POST /signals/preview`: indicators are computed on a caller-supplied synthetic curve with no DB or I/O, so the global "asset"/"forex" settings modal renders a real overlay instead of an "unavailable" banner.
- Grouped indicator search, KaTeX formula labels, responsive cards and per-signal diagnostics.
- Incomplete OHLCV inputs render as honest partial contiguous segments instead of interpolated fiction.

#### 🤖 AI Export — rebuilt catalog
- First public **V1** export contract: **8 autonomous public datasets** and **11 task-oriented analyses**, composed from **67 components** and 40 internal dataset blocks.
- **Task-aware prompt composition** — drawdown, income, concentration, cost and FX contexts are selected per analysis, so financial prompts stay focused without weakening full technical exports.
- Snapshots render as compact, auditable tables with local entity references; weights, HHI, FIFO, numeric and missing-price semantics are stated explicitly in the prompt.
- Adaptive temporal buckets, plugin-owned signal aggregation, sampling manifests, and coverage/broker-scope/partial-history disclosure embedded in the export.
- Focused financial context, capital-loss offset prompts, and 10-minute login-bound panel memory for draft continuity.

#### 📥 Broker imports (BRIM)
- **19 new broker plugins** (30 supported importers in total): Avanza, Bitvavo, BUX, CoinTracking, Crédit Agricole, Crypto.com, Delta, Disnat, Fineco, Intesa Sanpaolo, InvestEngine, Investimental, Parqet, Rabobank, Relai, Saxo, Swissquote, Trade Republic and XTB.
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

#### 🔁 Import flow & asset identity (post-beta)

- **Instrument unification inside the wizard** — a dedicated step proposes merges for instruments that already exist in your library (certain / proposed / lone), before duplicate checking, so re-imports no longer create parallel assets for the same security. Existing duplicates can be merged later from the asset page.
- **Crédit Agricole trades branch** — `COMPRAVENDITA TITOLI/FONDI/OPZIONI` rows are now imported as real buy/sell trades instead of falling back to generic cash movements, with a pre-alarm net validated on four real trades.
- **Wizard rework** — a 7-step conditional flow (upload → parse → corrections → unify assets → duplicates → review → done), with cross-file and database duplicate detection after your corrections, and per-row repair panels for ambiguous cash movements, bundled amounts, and instrument-less fees.

#### 🧪 Test infrastructure

- **Parallel Playwright suite** — the whole frontend E2E suite shares one backend and declares what each spec owns; waits are on published product state (`data-busy`, `data-chart-ready`), never on the clock.
- **One backend per API run**, a reachability check that keeps every registered suite inside `all`, and branch-accurate JS/Svelte coverage via a shared Istanbul instrumentation.
- **jsdom component harness** for fast unit tests of Svelte components alongside the E2E suite.

#### 📦 Beta feedback consolidation (second wave)

- **Ownership-aware dashboard** — the dashboard aggregates only brokers you own, scaled by your ownership share (0% is a valid share and behaves like editor/viewer); broker cards scale likewise, and share/role edits invalidate cached numbers immediately.
- **Broker self-service** — editors can demote themselves to viewer, editors and viewers can leave a broker, and the last owner leaving deletes the broker with its reports and transactions (with a destructive-action warning).
- **Assets page usage panels** — your assets / other users' assets / watched (saved but unused), with a transaction-count badge per asset in both the grid and the (stacked, layout-synchronised) tables.
- **AI Export lot detail v2** — each lot now carries the market reference price and market value at its opening date, so analyses can reason about entry conditions (e.g. recovery value), not only about cost.
- **In-app changelog** — clicking the version in the sidebar opens the bundled changelog as foldable per-release panels with foldable sub-sections and a version index.
- **Update prompt for admins** — after login, admins see a one-day-throttled prompt when a newer stable release exists on GitHub, linking the updating guide (which now documents Watchtower).
- **Docker light variant** — `dev.py docker build --light` / `*-light` tags ship the documentation without its images (they load from the online docs site on demand). The diet also removed the duplicated chown layer, the build-time pip toolchain from the runtime image, and the accidental inclusion of local databases in published images. Light is ~1.5 GB vs ~2.9 GB full.
- Mobile fixes: compact date inputs keep their intended size (the iOS zoom guard no longer inflates them), and table header tooltips open upward instead of covering the rows below.

### 🔄 Changed

- **Signal cards show a spinner while their request is in flight** — no more red "cannot be calculated" flash between asking for an indicator and its answer; genuine problems still surface once the response lands.
- **Tooltips open after a short hover rest** (500ms) instead of instantly — no more tooltip flashes while crossing the page. Click, tap and keyboard still open them immediately.
- **Duplicating a transaction preserves the original date** in every clone path (list clone, in-workspace clone, paired clone) — duplication is how a misclassified historical row gets corrected, and resetting to today destroyed exactly the field being fixed.
- **Single-row delete routes through the bulk workspace** (pre-marked for deletion), consistent with single-row edit and clone; the dedicated delete modal was removed. Deleting one side of a linked pair without its partner surfaces a localized explanation.
- **Legacy valuation engine removed** — the unified resolver is the only valuation path. The `LIBREFOLIO_RESOLVER_VALUATION` transition flag, the `LAST_BUY_PRICE` / `LAST_SEED_COST` fallback tiers and the duplicate per-path price maps are gone.
- **Legacy AI Export runtime removed** — the unreachable profile/assembler stack was deleted so the catalog, prompts and tests cannot drift apart. The final V1 prompt outputs were preserved during the cleanup.
- Technical analysis moved from the frontend to the backend (see Signals platform above); frontend controls, rendering, axes and batching now consume backend results.
- Asset and FX domains were folded into the existing APIs rather than kept as parallel surfaces.
- The 500-item cap on bulk import validation was removed, so large multi-file merges import in one pass.
- Borsa Italiana search now performs a single on-site fetch and emits both language rows from it, roughly halving search latency (~2.6s → ~1.2s).
- Candidate URL resolution during asset search runs concurrently instead of sequentially, and creating an asset no longer blocks the modal on the provider history sync.
- The dashboard data-quality banner is foldable and offers one "go to asset" link per affected asset, instead of a single CTA that only opened the first one.
- Documentation: the English MkDocs set was realigned with the shipped code, adding Price Resolution and Net Annualized Return pages, a duplicate-detection developer page, and user guides for the new brokers.

### 🐛 Fixed

#### 📈 Borsa Italiana — non-XMIL markets (EuroTLX) + OHLC integrity (2026-09-04)

- **EuroTLX instruments now resolve end-to-end** — instruments quoted on EuroTLX (e.g. a US T-Bond such as ISIN `US912810TU25`) were found by search but the generated page link landed on a dead generic URL and price/history/metadata all failed. The provider now carries the market `mic`/`platform` from the site's own search result into `provider_params` (never a hardcoded map), so the instrument page, current price, history and metadata all work for every market — present and future. History for FX-denominated bonds now reports the real currency (e.g. USD) instead of a hardcoded EUR.
- **Government bonds get the right classification** — Italian BTPs, US T-Bonds and other sovereign paper now get sector = Financials (100%) and the issuer's country in the geographic area (e.g. *United States of America* → USA).
- **Dead search results are never offered** — instruments the search can't route to a real market page (and non-purchasable indices) are filtered out instead of producing a result that fails on click; when a market page genuinely can't be read yet, the provider raises a clear `UNSUPPORTED_PAGE` error inviting you to open a GitHub issue with the ISIN.
- **Sync no longer rejected valid bond prices** — Borsa Italiana reports the official daily fixing as the close even when it falls outside the day's traded low/high range (normal for thinly-traded bonds); the upsert validator rejected those points as "impossible OHLC". A new global guard on the provider base class now widens the candle's low/high bounds to contain the open/close for **every** provider, so no real price is ever dropped — each repair is logged at debug level.
- **Provider config fields are tidier** — the per-asset provider parameters now show a short inline label with the longer explanation moved into an ⓘ tooltip, and the user manual documents how to set `mic`/`platform`/`codice_fondo` by hand (in all four languages).

#### 🧹 Clean audit re-check — P2/P3 + docs wave (2026-09-03/04)

- **New admin cache panel** — Global Settings now shows every named cache (size, TTL) to all signed-in users, with admin-only "Clear" per cache and "Clear all", each behind a confirmation that warns the next fetch will be as slow as a restart.
- **Trading212 broker icon never loaded** — the plugin pointed at a Cloudflare-blocked `favicon.ico` (403); it now uses the public PNG.
- **Settings docs area realigned** — new Profile page (it was folded into Preferences), rewritten Preferences, About page gains the changelog-modal and plugin-diagnostics guides, admin docs gain the update-notification flow and the cache panel, installation page no longer claims "Alpha".
- **Signals docs realigned** — asset/FX signal pages now link the 22/9 backend indicators documented once in Financial Theory instead of listing a stale subset, and document the spinner, per-signal diagnostics and the drawdown full-history toggle.
- **Documentation sweep** — import wizard guide rewritten for the real 7-step flow, sharing guide rewritten (multi-owner, self-leave, last-owner cascade), AI Export catalog names, SNB monthly averages, WAL-safe Docker backup, dead links/icons/backlinks fixed across the manual.
- **check-links tooling** — test fixtures no longer scanned as real links and template-literal paths are handled: the report is now all-green with zero false positives.

#### 🧹 Clean audit re-check — P1 hygiene (2026-09-03)

- **Bulk FX conversion-route operations issued one query per route** — route replacement now preloads the touched pairs in one SELECT, batches deletes, and re-reads remaining routes with a single grouped query; the WAC analytics endpoint preloads its assets the same way.
- **Error logs lost the traceback in 55 places** — `logger.error` inside `except` blocks is now `logger.exception`, so operational failures carry their stack trace in the server log.
- Internal hygiene with no behavior change: unreachable backend helpers and frontend orphans removed, 25 unused translations dropped from all four languages, dead barrel re-exports pruned, the impossible currency-graph invalidation machinery removed (the graph is built from startup-static provider capabilities), and the lint gate hardened (complexity `C901` at 10 with justified exceptions for flat data packers, `TRY400`, `S110`).

#### 🧹 Clean audit re-check — P0 fixes (2026-09-02)

- **Configured base currency was ignored everywhere** — valuation paths read a `base_currency` global key that was never registered, silently falling back to EUR, and the engine's fallback branch called the settings helper with inverted arguments (a guaranteed `TypeError` had it ever run). The effective base currency is now the per-user setting, seeded from the admin-level default at first creation, EUR as last resort.
- **Image previews blocked the API event loop** — Pillow resize in the file-serving endpoint now runs in a worker thread (`asyncio.to_thread`), so a large image no longer stalls every concurrent request.
- **Bulk asset PATCH issued N+1 queries** — assets are now preloaded in one SELECT and the currency-change guard uses per-asset `GROUP BY` aggregates: a 50-asset bulk update drops from ~50+ queries to 4.
- **Silent `except: pass` swallows** — a fixed one in the cache layer (`clear()` could not log a failed close) and a new punctual `S110` ruff gate so the class cannot return.

#### 🧪 Second beta wave — consolidation (2026-09-02)

- **Decimal separator erased while typing** — in the transaction form's amount field, typing `12,` was rewritten to `12` mid-keystroke (the field's own emission came back reformatted); the comparison is now numeric, so `12,` and trailing zeros survive until blur. The quantity field no longer starts pre-filled with `0`, which forced cursor gymnastics to type decimals.
- **Import wizard summary counted raw parses, not the import** — the asset/transaction totals in the analysis summary are now derived from the consolidated state (identity-grouped assets, current selection), so duplicate resolution and before-opening rows update the numbers.
- **Import wizard: transaction types in English** in the analysis summary — now translated.
- **Import wizard: rows stayed deselected** when a broker's opening date was fixed before assigning their asset — the importable-row re-selection now also runs on asset assignment.
- **Drawdown signal was window-relative** — the running peak started at the visible range. The signal now computes against the full available history by default (new `full_history` parameter, shown as a toggle in the signal settings), and AI Export drawdown sections always use the full history regardless of the export period.
- **Charts could freeze the whole API on assets with long FX-uncovered history** — the currency-conversion pass deduplicated its errors inside the per-point loop (quadratic), so a full-history load with thousands of distinct missing-rate days spun the worker at 100% CPU for minutes and every concurrent request timed out (the "technical signals could not be updated" banner). Errors are now deduplicated once per job and capped with a summary line.
- **Docker build shipped without the emoji font on download failure** — a failed Google Fonts fetch was logged and ignored, so the image went out with a broken font link (flags rendered as letters on Windows). The resource cache now fails the build when a resource is missing and not cached; partially downloaded fonts count as failures too.
- **Provider test errors always in English** — the "Test Configuration" probe results now carry a structured error code plus parameters, and the frontend renders a localized message for the common cases (no data, stale fund NAV, not found, fetch/timeout/parse errors…), falling back to the raw message otherwise.
- Documentation: the Net Worth KPI page now states explicitly that the figure includes cash and is not comparable to a bank statement's securities-only value (in all four languages), and the card carries a composition tooltip.

#### Earlier in this cycle

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

These affect newly introduced analytics or local UI persistence only — the stable REST API and the database schema are unchanged.

- **Signals**: `gain_loss_change_1d_percent` is now computed on the previous position *market value* rather than the previous unrealized P&L.
- **DataTable**: the column-visibility persistence key changed (`columnVisibility` → `columnVisibilityOverrides`). Saved show/hide preferences are not migrated and each table resets to its default once; column order and widths are preserved.

---

## [1.0.1] - 2026-07-21

First patch release after 1.0.0 — a day-one polish round from real-world use: FX selection UX, a candlestick refresh bug, a fairer current price for thinly-traded ETFs, and two CI/test-runner fixes for fresh checkouts.

### 🐛 Fixed

- **FX & positions UX** — the currency selectors only offer pairs with a configured route (with a back-to-default and a create-pair shortcut); missing-FX data-quality issues now distinguish "no route configured" (add the pair) from "provider synced but gaps" (sync it, with the date range and gap count) from "manual-only"; the displayed currency stays frozen until the backend report resolves, so labels never mismatch stale numbers; the banner's sync CTA shows progress and reports "no new data" when a sync adds nothing.
- **Candlestick charts ignored range changes** — the series was bound to a manually-cached derivation that short-circuited before reading the data, so Svelte stopped tracking it; switching the time range now redraws the candles.
- **Thinly-traded ETFs showed a stale current price** — on JustETF/Gettex these trade mostly at the opening auction, so `last` sat at the open all day; the current price now prefers the live `mid` (bid+ask)/2, with a fallback to the performance chart's latest quote for all currencies.
- **Fresh-checkout CI/test failures** — the test runner's frontend build and the CI pipeline consumed gitignored build artifacts (the generated API client) before ensuring they exist; both now generate them first.

---

## [1.0.0] - 2026-07-20

LibreFolio is a self-hosted, open-source portfolio tracker: your brokers' reports in,
a clear and honest picture of your wealth out. No cloud service in between — the whole
stack (FastAPI backend, SvelteKit frontend, SQLite database) runs in a single Docker
container on your own hardware. This first release packages the core engine, the import
wizard, and the dashboards that grew up over the project's first months.

### ✨ Added

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
