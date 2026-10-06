# Changelog

All notable changes to LibreFolio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

**Preparing v1.2.0.** These features and fixes are in preparation; this version has not been released.

### ✨ Added

- Shared support actions in the donation popup and About page: coffee links and X, Reddit, Facebook, Instagram and TikTok icons, with platform-specific messages in the active interface language, each followed by the same five hashtags (#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance). **Copy and go** includes the public project link and opens a new tab, leaving the original screen open. Reddit separates title and body; platforms without text-prefill support explain how to paste the copied caption. TikTok opens its upload page rather than the feed. Clipboard and pop-up failures are reported explicitly; nothing is published automatically.
- A new authenticated **Tools** foundation provides a versioned catalogue, isolated per-item computation, read-only diagnostics and compiled custom interfaces. The hub reports missing or incompatible tools explicitly; no financial calculation or portfolio write is implied when no compatible plugin is installed.
- **PAC allocator** is the first packaged tool in that catalogue. Its planner computes purchase plans — in whole or fractional units, or in amounts, following each broker's increment — that bring an allocation as close as possible to its target weights. It works in exact arithmetic, across multiple currencies and arbitrary quote bases. Cash in another currency can pay for an order: you choose whether you convert first or the broker converts when you buy, both at the FX step's rate minus the conversion spread, and every exchange appears in the plan. Every answer says what it is worth: proven optimal, the best plan found when optimality could not be proven, proven infeasible, or no plan within the calculation limits. These are never presented as the same thing, and missing or invalid inputs are reported rather than guessed. The guided interface walks through liquidity, brokers, assets, order routes, targets and, only when needed, exchange rates. Brokers and assets can be entered by hand or copied from LibreFolio, together with cash, current prices, exchange rates and the current distribution as an editable starting target. Each copy keeps its source and capture time. **Calculate** refreshes the copied prices, rates and balances you have not changed, and leaves typed values as they are. Results show:
  - the orders by broker and route, with their fees;
  - the cash left in each currency;
  - target versus resulting weights;
  - exposure by country, type and sector;
  - the proof behind the outcome.

  Personal amounts follow Privacy mode. The calculation uses only the scenario it receives and reads nothing from the portfolio while it runs. It plans purchases only: it does not sell or rebalance current holdings, and it never places an order.
- Holdings tables on the Dashboard and Broker pages now show transaction-ledger **Yield on Cost** by asset and broker. The metric compares gross recorded dividend and interest income over the last year with the average purchase price, using prior-day held quantity, linked splits and portfolio FX rates; unavailable values explain the exact missing or inconsistent input.
- **Asset types**: the type picker is a searchable two-level menu, with ETF and Crowdfunding families. Specialized ETF and crowdfunding types show their content icon overlaid on the container icon wherever the type appears, and a new type, *Real estate crowdfunding*, is available.
- New users now get a Welcome setup, a versioned Core tour, and contextual Broker, FX, Asset and Import guides. A completed or skipped guide can be replayed from Settings, while a newer guide version becomes due automatically; Import guidance remains separate from transaction writes and Save All. Guides remember where you are in this browser — across tabs, reloads and logging out — resume at the step you left when you return to a page, and a guide finished in one tab closes in the others.
- **Privacy mode** — an eye button in the page header hides how much you own: every portfolio amount (dashboard, positions, FIFO lots, brokers, risk panels, transactions) shows `•••` with its currency and sign still visible. Held quantities are hidden in positions and lots but stay visible in the transaction list; unit prices, WAC, percentages, FX rates, asset events and edit fields stay readable. It switches instantly both ways, belongs to this browser and survives reloads; AI Export and downloads still contain the real figures.
- **P&L view in the Growth chart.** On the Dashboard and broker pages, a third view next to Abs and % plots cumulative total P&L, never rebased to the selected range. *Line* shows the accumulated P&L; *Candles* builds synthetic candles day by day from each asset's prices with that day's quantities, ownership and FX — highs and lows are hypothetical and not simultaneous, and there is no volume; *Income* stacks dividends and interest, fees and taxes, deposits, and purchases split into new and reinvested capital. A width picker from 1D to 1Y offers only the widths that can be drawn; periods count back from the last day, so the newest candle closes on it, and a shorter oldest period is faded and marked "Partial: N of M days".
- **Rolling Return in the asset chart.** A second mode next to Prices shows the price-only return against the close exactly N calendar days earlier — 1W, 1M, 3M or 1Y, or a custom number of weeks, months or years. History before the selected range is loaded, so a window longer than the range still draws; the tooltip shows the reference date and the price and FX observations used, partial data is shown apart from unavailable data, comparison assets use the same window and currency, and a **?** next to the window opens the guide.
- **The Growth and Allocation charts remember the view you chose.**
- **FX route metadata in the API** — route responses expose `is_chain` and a sorted, unique `providers_used` list of configured providers. Ordered `chain_steps` still preserves direction and repeated providers; request payloads remain unchanged, with no database migration required.
- **Danske Bank (Finland) importer, alpha: one import from two exports.** The bank splits an equity savings account (*osakesäästötili*) into a securities export (XLSX) — purchases, sales, dividends, demergers — and a cash statement (CSV); upload the two together and LibreFolio imports them as one.
  - **One card per set.** In *Select Files* the two exports form a single card: each kind of export in its own table, ordered by the period it covers, and a timeline of the files, of any days no export covers, and of the history LibreFolio already holds — point at a bar, or click it, for its dates and number of rows. The Files page shows which exports belong together and which file was combined from them.
  - **A missing export is announced at once.** Upload only one of the two and the wizard says which one is missing and for which period, already at upload and again on the card; upload it into the same set from there, or leave the set out of this import.
  - **Every trade paired with its cash.** The two files are combined into one; the analysis detail shows the outcome — trades paired with their cash movement, rows found in one file only, movements summarised or left for your next import, rows left out and why — and lets you preview or download the combined file. The importer's notes are in Finnish, like the bank's exports.
  - **Commissions you can separate.** The bank gives one total per trade, commission included: the cash is imported exactly as booked, and for a security priced in euro the fix step suggests the likely commission, so you can separate it from the price if you track fees.
  - **Align with the bank.** A first import summarises the older history in a starting point instead of replaying it, and later imports skip what LibreFolio already holds. After the review, a new step compares what LibreFolio will hold with the bank's balance and with the positions the files prove: one card per point — the starting point, and a point after each gap between exports — and one table of the proposed deposits and adjustments, selected by default and tagged `gap_fix`. An end-of-period check compares the cash with the statement's last balance and is never corrected automatically. The Import guide covers the new step.
  - **You choose how a set is read.** The card's *Read as* menu shows how the set is read — the plugin that recognised it, another set plugin that reads every file, or *Read the files one by one* — and each file's menu offers *Read alone with…* (when another plugin reads that file) and *Remove from the set*. A note says when the broker's default plugin, or another set plugin, could also read a file of the set. While the files are only uploaded your choice lasts until you close the wizard; after an analysis LibreFolio remembers how each file was read, and the Files page follows it.
  - **Alpha.** Built from the exports of a single account, shared in [issue #26](https://github.com/Librefolio/LibreFolio/issues/26): if your files look different, or a row is imported in a way that looks wrong, please tell us there.
- **Todo banners lead to their rows.** In the bulk editor, each entry of the banners that list the fields to complete or to verify pages to its row and highlights it.

### 🐛 Fixed

#### 🔒 Security

- Asset, broker and note names that contain markup are shown as plain text in tables, chart tooltips, notifications and validation messages, instead of being interpreted as HTML. This closes a stored cross-site scripting issue present since v1.1.0, where a crafted asset name could run code in another user's browser.

#### 🤖 AI Export and signal contracts

- AI Export structural validation now raises typed errors for invalid component, dataset, analysis, policy and detail-level definitions even when Python runs with optimization enabled. Public IDs, versions and catalog ordering remain unchanged.
- Technical-signal results consistently enforce the declared status matrix for precompute/runtime failures, partial undefined metrics, aligned output and paired metadata, preventing impossible API result combinations.

#### 📥 Imports and transaction editing

- Editing an asset from the import wizard now loads its complete saved metadata. Saving unrelated fields preserves descriptions and sector/geographic distributions; explicit clears remain possible.
- Currency-change confirmations and nested asset dialogs remain reachable above the wizard. Price and linked-transaction warnings now display their counts and dates correctly.
- Manual FX conversions no longer remain incomplete because of a hidden destination broker. Separate leg dates, exact decimal amounts and balance/sign validation are preserved.
- Import matching refreshes current candidates and the asset catalog together, including assets created after parsing. A single distinct match can be selected automatically; ambiguous matches still require a choice.
- A final duplicate check that changes the selected transactions returns to review instead of silently importing a smaller or empty batch.
- A movement found in two of the files being imported that already exists in the database, or in the unsaved editor, is no longer pre-selected at review; its badge opens the comparison with the existing transaction.
- Choices made in the Duplicates step are no longer reset when you create or pick an asset on the review step; Import sends you back to that step only when the final check finds new or changed duplicates between your files, and says so.
- The Transactions page no longer fires dozens of `GET /brokers/{id}` requests per second in the background when a broker has no icon, portal URL or import plugin.
- Balance diagnostics identify all contributing workspace rows and navigate to the first affected row in the current display order. Backdated FX pairs sort with their dates without changing operation identity or submission order, and new rows on the same date keep the order in which you added them.
- Non-sticky bulk-table action headers stay at the end of the table rather than covering the rightmost visible columns.
- Page-size menus remain reachable in short, scrollable modal tables instead of clipping their first options.
- The Transactions page clears its selection after a saved bulk edit, clone, deletion, addition or import, and after linking or unlinking a pair; cancelling keeps it.
- Uploading broker reports from the Files page or from a broker's import history no longer fails with a validation error. The failure dated back to v0.9.0; the import wizard was not affected.
- Every CSV importer now reads broker exports saved as Windows-1252 or Latin-1 (for example re-saved with Excel on Windows): accented characters and the euro sign no longer make the import fail, and semicolon-separated files are no longer split on commas.
- The Generic CSV is offered only for a CSV whose first row names a date and a type column (in any language it knows), instead of every CSV it then failed to read; choosing it for another file now says which required column is missing.
- A searchable list (currency, asset, type, broker…) now opens on the first click right after you choose from it: a guard against phantom taps on touch screens ignored any click within 200 ms of the list closing, mouse and keyboard included; it now applies to touch and pen only.
- In the bulk editor, applying an imported row with Auto (WAC) cost now clears its *enter the cost* todo, even when Auto was already selected — no more switching to manual and back.
- Rows handed over by an import are now validated once right away, whatever their number: above 50 rows the editor used to show no problems until *Validate now*.
- The analysis detail of an import shows each field to complete as readable facts — the file row, the amounts, the importer's suggestions and the source rows — instead of raw JSON.

#### 🧩 Asset providers and feedback

- Provider tests and metadata requests ignore stale responses after the asset or provider configuration changes. Late metadata cannot silently overwrite manual edits.
- Equivalent distributions no longer appear different merely because their entries arrived in another order.
- Duplicate broker-name errors include localized recovery guidance and reset when a new dialog is opened. Successful broker creation and deletion receive confirmation toasts.
- Manual update checks refresh release metadata and compare against the running server version. Failed or unavailable checks no longer report “up to date”; a positive success message includes the version detected online. Checking from the changelog window always shows the outcome, and a newer version appears at once instead of after the window is closed.
- The header theme button is labelled in every interface language.
- Country flags render as flags on Windows everywhere, dashboard currencies included, instead of letter pairs such as “EU”. Apple devices show their own flags without downloading a flag font.
- Docker image availability checks now complete GHCR's public authentication handshake through the LibreFolio backend, so a published release is no longer rejected because the registry first returns an authentication challenge. Invalid or untrusted challenges still fail closed.
- Social-dialog logos retain a circular, fixed-size background even beside long translated instructions.
- Global settings use the standard amber in-app confirmation before discarding an unsaved draft; cancel and Escape keep the draft unlocked.
- Search in select menus ranks name matches first: typing "CSV" puts "Generic CSV" at the top.
- Creating an asset, the provider data comparison no longer opens on top of the ISIN choice: it waits for your answer and never asks the same question twice.
- Borsa Italiana ETFs and ETCs take the currency they are quoted in (EUR), not the fund's denomination currency, whether they are found by search or added from their page address.
- The Dashboard again warns about assets whose provider has not delivered a new price for more than 7 days. The warning now has a **Sync** button that refreshes those assets; manual assets are never flagged.

#### 📈 Charts

- **Allocation history shows the right emoji for commodities, real estate and unknown types**, instead of 📊, the ETF emoji, for all three.
- The amount axes of the Growth and Performance charts no longer print the same label twice (`5.5k` shown as `6k` next to a real `6k`, `1.25M` as `1.3M`), and an axis edge placed automatically beyond the data is no longer labelled as if it were a regular step. Chart amounts take their minus sign from your browser's language; the Growth tooltip's total P&L now reads `EUR -12.00` like the other amounts, instead of `−EUR 12.00`.
- The lot comparison chart no longer leaves an empty strip left of its amounts, most visibly on phones.

#### ⚡ Faster reports

- **Reports and the Dashboard no longer stall on long currency histories.** A currency conversion now loads only the exchange rates it can use, instead of the whole history of the pair, with identical results: on a real portfolio with rates going back to 2000, a report in a currency other than the base one went from 10–27 s to under 3 s. Thanks to Martin Sova ([#30](https://github.com/Librefolio/LibreFolio/pull/30)).

#### 📱 Sign-in, app icons and small screens

- Browsers offer saved credentials on the sign-in username field too, and registration and password change are recognised by password managers, so changing a password updates the right saved account.
- The installed app no longer shows black corners on the Android splash screen or around the iPhone home-screen icon, and Android gets a proper maskable icon.
- On phones, the asset dialog keeps Save and Cancel reachable, **Sync** on an asset page no longer looks crossed out while the page loads, and the asset page tabs show an icon.
- On phones, the price chart tooltip of an asset with a long name no longer runs off the screen: the name is shortened with an ellipsis, while the value and its currency stay whole.
- The top toolbars of the Assets, asset detail, Dashboard, broker detail and FX pages no longer push buttons out of the bar at intermediate widths, in every interface language.
- With a single broker selected, a long broker name in the Dashboard's broker filter is shortened with an ellipsis instead of sticking out of the bar on narrow screens.

#### 🐳 Docker images

- **The published images ship the production interface again.** Since at least v1.1.0 they contained a debug build of the web app (not minified, with source maps), 58 MB instead of 21 MB, about 5 MB more to download on a first visit. The image build now refuses a debug build, local builds included.
- **The full image includes the documentation screenshots for offline use**, as the installation guide says; until now full and light were identical. The light image, the one `latest` points to, still loads them from the online documentation.
- The installation guide and the release notes name the image tags that exist: `latest` (light), `X.Y.Z` (full) and `X.Y.Z-light`, without a leading `v`. `latest-light` and `v1.1.0-light` never existed.

### 🔄 Changed

- **Pages download less data.** The server compresses its responses (gzip): a first visit downloads about 2.8 MB instead of 7.5 MB, and a typical session about 0.9 MB instead of 5.5 MB, which helps on slow or metered connections.
- Language and display currency for new users start from administrator defaults; existing users are not forced through onboarding.
- Import file tables paginate from five rows. After uploading, only the brokers that received those files start expanded.
- First-time asset creation is explained briefly; known ISINs or tickers can prefill a missing asset name. The currency tooltip now describes the currency used to store asset prices.
- The Generic CSV guide clarifies one file per broker—not one file per currency—and keeps its column reference in a single table.
- Files show who uploaded them in a sortable column, with an avatar/name multi-select filter. Uploader filters survive switching between list and grid.
- The header hides while scrolling down and returns while scrolling up on desktop and mobile. Focus, open menus and dialogs keep it visible.
- The browser tab title stays “LibreFolio” on every page: the Files page no longer sets its own, so it can no longer linger after you leave it.
- Preferences and broker-sharing forms retain staged Save/Undo/Reset, persisted values and role-based access after their Svelte 5 migration. Successful sharing saves close the list-page modal without another discard prompt; saving from the broker's Info tab keeps the inline editor open.
- New FX-pair configuration closes immediately while automatic synchronization continues in the background. Creation and sync results use flagged, clickable pair links; linked completion feedback keeps the pair, fetched/changed counters and provider badges on one compact detail row. Asset-library creation success links point to the new asset without changing contextual import or transaction flows.

#### 📉 Risk Analysis leaves beta, except the simulation

- **Risk Analysis is no longer marked beta.** The beta notice used to sit above every risk surface, which said the whole subsystem was provisional. It now appears on the **simulation** step alone, where it names the reason: the outcome depends heavily on how much history is requested relative to the horizon, so a short window with a long horizon can produce implausible figures. The permanent reminder that a model is a model stays where it was, below it. Asset Detail keeps its beta notice: its risk view has not been rebuilt yet.
- **Asset Global gains two comparison levels, with a user guide.** *How much did each of these hurt?* transposes the scale — the ruler becomes the columns, the assets become the rows, and the worst fall says how long it lasted — and *What did each of these pay for its risk?* plots what each instrument risked against what it returned, beside the benchmark chosen on the Dashboard. Percentages only and no verdict — no line is drawn through the points, because a selection has no whole — and an asset that could not be measured keeps its row with the reason, because a missing row reads as one that was never selected. The legacy panel is no longer mounted there. A new user page explains the Correlation tab and how its figures are measured.
- **The risk/return scatter now renders** on the Dashboard and on Broker pages. It had never appeared: the panel neither asked the backend for the figures nor passed them on.
- **A failure inside a risk calculation is now reported as ours.** Every internal error used to be answered with *«the metric is undefined for these data»* — a verdict about the portfolio — and was never logged. Undeclared failures now say the calculation failed and are recorded; an analytic that genuinely has no defined value still says so.
- **Two simulation settings now explain themselves instead of failing obscurely.** Choosing a block longer than the available history, or a quasi-random simulation too large for the number of assets and the horizon, now says which setting to change. The second is reachable by an ordinary portfolio: at the longest horizon the limit falls between five and six assets.

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
