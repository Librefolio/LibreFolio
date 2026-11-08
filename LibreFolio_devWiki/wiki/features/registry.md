# Feature Registry

> Authoritative list of all LibreFolio features with permanent codes.
> Codes are assigned at first mention and **never change** even if the feature is renamed/split/superseded.
> Updated: 2026-04-24 (bootstrap from codebase analysis, phases 0–7 in progress); 2026-10-09 (Release 2 archive: F-100–F-104 added, F-052/F-053/F-055/F-088/F-095 statuses corrected against the code); 2026-10-12 (lint: F-050/F-089/F-092 documented, F-075 superseded, verified on the code and in git); 2026-10-12 (step B5: F-105 guided onboarding; step B6a: F-106 Tool platform; step B6b: F-107 PAC allocator, F-108 Rebalancer planned; step C: F-078 implemented); 2026-10-12 (step B8: F-109 in-app changelog, localized by chapter); 2026-10-12 (folder 02, step R0: F-110–F-113 Risk); 2026-10-12 (C-64, status check: F-048 documented; the planned and idea rows checked against the code, unchanged); 2026-10-13 (the pages checked against the 1.2.0 CHANGELOG: F-114 Benchmark assets added); 2026-11-07 (1.3 closing ingest: F-073 documented, the restore and the space limit); 2026-11-07 (lint against the code: 29 `implemented` rows with a current user, admin or theory page → `documented`; F-087 and F-094 shipped; F-037–F-041 `fullstack` since the backend signal plugins; F-046 `backend`; mkdocs paths of F-005, F-056, F-071 fixed)
>
> **Macro-level navigation**: for product-level domain narratives (what each domain does, how features cluster, data-flow diagrams), see [`wiki/domains/`](../domains/) — 11 domain pages covering all features.

## Status Key

| Status | Meaning |
|--------|---------|
| `idea` | Mentioned, not yet planned |
| `planned` | In a roadmap, not started |
| `in-progress` | Actively being built |
| `implemented` | Code complete, no mkdocs yet |
| `documented` | mkdocs page exists and current |
| `superseded` | Replaced by another feature |

---

## Domain: AUTH

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-001]] | User Authentication & Sessions | fullstack | `implemented` | [`dev/arch/access_control.md`](developer/architecture/access_control.md) |
| [[F-002]] | User Management (Users tab and CLI for administrators; self-service account deletion) | fullstack | `documented` | `admin/users.en.md` |
| [[F-003]] | Multi-User Role System (admin/user; last-active-admin guard) | fullstack | `implemented` | [`dev/arch/access_control.md`](developer/architecture/access_control.md) |
| [[F-102]] | Connection Security Indicator (+ login without account enumeration) | fullstack | `documented` | `user/connection-security.en.md` |

---

## Domain: LAYOUT & SETTINGS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-004]] | App Shell & Navigation (sidebar, header) | frontend | `implemented` | [`dev/fe/styling.md`](developer/frontend/styling.md) |
| [[F-005]] | User Settings (language, theme) | fullstack | `documented` | `user/settings/preferences.en.md` |
| [[F-006]] | Global Settings (admin-managed app config) | fullstack | `documented` | `admin/settings.en.md` |
| [[F-007]] | Theme System (dark/light/auto) | frontend | `implemented` | — |
| [[F-008]] | i18n System (EN/IT/FR/ES, 4 215 keys) | frontend | `implemented` | [`dev/fe/i18n.md`](developer/frontend/i18n.md) |
| [[F-101]] | Global Privacy Mode (hide values) | frontend | `documented` | `user/settings/preferences.en.md` |
| [[F-104]] | Recommend LibreFolio (social share, copy and go) | frontend | `documented` | `user/settings/about.en.md` |
| [[F-105]] | Guided onboarding (Welcome, intro tour, contextual guides) | fullstack | `documented` | [`dev/fe/onboarding.md`](developer/frontend/onboarding.md) |
| [[F-109]] | In-app changelog (sidebar version → modal; each release in the UI language when translated) | frontend | `documented` | `user/settings/about.en.md` |

---

## Domain: BROKERS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-009]] | Broker CRUD | fullstack | `documented` | `user/brokers/index.en.md` |
| [[F-010]] | Broker Sharing (Owner/Editor/Viewer roles) | fullstack | `documented` | `user/brokers/sharing.en.md` |
| [[F-011]] | File Management (upload/list/delete broker reports) | fullstack | `documented` | `user/files/index.en.md` |
| [[F-012]] | BRIM Framework (broker report import pipeline) | fullstack | `implemented` | [`dev/be/brim/architecture.md`](developer/backend/brim/architecture.md) |
| [[F-013]] | BRIM Broker Parser Plugins | backend | `documented` | [`dev/be/brim/providers_list.md`](developer/backend/brim/providers_list.md) |
| [[F-014]] | Image Upload & Crop (broker icon) | fullstack | `documented` | `user/misc/image-crop.en.md` |
| [[F-103]] | BRIM Report Sets (one import from several exports; gap fix) | fullstack | `documented` | [`dev/be/brim/architecture.md`](developer/backend/brim/architecture.md) |

---

## Domain: FX (Foreign Exchange)

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-015]] | FX Provider Registry (ECB, FED, BOE, SNB) | backend | `documented` | [`dev/be/fx/architecture.md`](developer/backend/fx/architecture.md) |
| [[F-016]] | FX Pair CRUD | fullstack | `documented` | `user/fx/add-pair.en.md` |
| [[F-017]] | FX Rate Sync (fetch from central banks) | fullstack | `documented` | `user/fx/sync.en.md` |
| [[F-018]] | FX Multi-Provider Fallback (priority chain) | backend | `implemented` | [`dev/be/fx/architecture.md`](developer/backend/fx/architecture.md) |
| [[F-019]] | MANUAL Sentinel Provider (auto-insert/remove) | backend | `implemented` | [`dev/be/fx/configuration.md`](developer/backend/fx/configuration.md) |
| [[F-020]] | FX Currency Conversion Graph (triangulation) | fullstack | `implemented` | [`dev/fe/fx-chain-algorithm.md`](developer/frontend/fx-chain-algorithm.md) |
| [[F-021]] | FX List View (dual view: card + table) | frontend | `documented` | `user/fx/index.en.md` |
| [[F-022]] | FX Detail Page (rate history, provider mgmt) | frontend | `documented` | `user/fx/detail/index.en.md` |
| [[F-023]] | FX Chart & Signal Overlay | frontend | `documented` | `user/fx/chart-settings.en.md` |

---

## Domain: ASSETS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-024]] | Asset CRUD | fullstack | `documented` | `user/assets/index.en.md` |
| [[F-025]] | Asset Provider Registry (yfinance, JustETF, CSS Scraper, Scheduled Investment) | backend | `documented` | `user/assets/providers/` |
| [[F-026]] | Asset Provider Assignment (dynamic params form) | fullstack | `implemented` | [`dev/be/assets/architecture.md`](developer/backend/assets/architecture.md) |
| [[F-027]] | Asset Data Sync (price fetch from providers) | fullstack | `implemented` | [`dev/be/assets/architecture.md`](developer/backend/assets/architecture.md) |
| [[F-028]] | Asset Search Autocomplete (multi-provider parallel) | frontend | `documented` | `user/assets/create-edit.en.md` |
| [[F-029]] | Asset Metadata Refresh | fullstack | `documented` | `user/assets/create-edit.en.md` |
| [[F-030]] | Asset Price History (OHLCV store/query) | backend | `implemented` | [`dev/arch/database/assets_pricing.md`](developer/architecture/database/assets_pricing.md) |
| [[F-031]] | Asset Events (DIVIDEND, SPLIT, INTEREST, etc.) | fullstack | `implemented` | [`dev/be/assets/events.md`](developer/backend/assets/events.md) |
| [[F-032]] | Asset List View (dual view: card + table) | frontend | `documented` | `user/assets/index.en.md` |
| [[F-033]] | Asset Detail Page (chart, signals, editor) | frontend | `documented` | `user/assets/detail/index.en.md` |
| [[F-034]] | Scheduled Investment Provider (synthetic yield) | backend | `documented` | `user/assets/providers/scheduled-investment.en.md` |
| [[F-035]] | CSS Scraper Provider (arbitrary web scraping) | backend | `documented` | `user/assets/providers/css-scraper.en.md` |
| [[F-036]] | Provider Comparison Modal (diff provider vs DB) | frontend | `documented` | `user/assets/create-edit.en.md` |
| [[F-114]] | Benchmark assets — a switch that offers an asset as a comparison benchmark | fullstack | `implemented` | — |

---

## Domain: TECHNICAL ANALYSIS (Signals)

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-037]] | Signal Library Framework (abstract base + registry) | fullstack | `implemented` | [`developer/architecture/patterns/signal_plugin_guide.md`](developer/architecture/patterns/signal_plugin_guide.md) |
| [[F-038]] | EMA Signal | fullstack | `documented` | `financial-theory/technical-analysis/indicators/ema.en.md` |
| [[F-039]] | RSI Signal | fullstack | `documented` | `financial-theory/technical-analysis/indicators/rsi.en.md` |
| [[F-040]] | MACD Signal | fullstack | `documented` | `financial-theory/technical-analysis/indicators/macd.en.md` |
| [[F-041]] | Bollinger Bands Signal | fullstack | `documented` | `financial-theory/technical-analysis/indicators/bollinger-bands.en.md` |
| [[F-042]] | FX Pair Comparison Signal | frontend | `documented` | `user/assets/detail/signals.en.md` |
| [[F-043]] | Asset Comparison Signal | frontend | `documented` | `user/assets/detail/signals.en.md` |
| [[F-044]] | Benchmark Signals (Linear, Compound, Sine) | frontend | `documented` | `financial-theory/technical-analysis/synthetic-benchmarks/index.en.md` |
| [[F-045]] | Measure Tool (2-click Δabs, Δ%, days) | frontend | `documented` | `user/assets/detail/measures.en.md` |

---

## Domain: TRANSACTIONS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-046]] | Transaction Model & Unified Batch API (validate + commit) | backend | `implemented` | [`dev/arch/database/brokers_transactions.md`](developer/architecture/database/brokers_transactions.md) |
| [[F-047]] | Transaction List Page (DataTable + filters + dual-form modals) | frontend | `documented` | `user/transactions/index.en.md` |
| [[F-048]] | Transaction Modals — Form / Bulk / Delete / Promote / Split (mode-less, Round 6 Plan D done) | fullstack | `documented` | `user/transactions/index.en.md` |
| [[F-049]] | BRIM Import UI (asset matching and review wizard) | fullstack | `documented` | [`dev/fe/import-wizard.md`](developer/frontend/components/features/import-wizard.md) |
| [[F-050]] | File Preview System (image/text/table/md/code) | fullstack | `documented` | `user/files/index.en.md` |
| [[F-051]] | Transaction ↔ AssetEvent Link | backend | `implemented` | — |

---

## Domain: SCHEDULER

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-052]] | Market Data Scheduler (embedded asyncio daemon) | backend | `documented` | [`dev/be/scheduler.md`](developer/backend/scheduler.md) |
| [[F-053]] | Scheduler Settings UI (admin Global settings) | frontend | `documented` | `admin/settings.en.md` |

---

## Domain: DASHBOARD

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-054]] | Dashboard KPI & Overview | fullstack | `documented` | `user/dashboard/kpi-cards.en.md` |
| [[F-055]] | Portfolio Charts (Holdings/Performance panel, GrowthChart with P&L modes, Allocation) | frontend | `documented` | `user/dashboard/charts.en.md` |
| [[F-100]] | Yield on Cost (YOC) per position | fullstack | `documented` | `user/dashboard/positions.en.md` |
| [[F-111]] | Risk tab of the Dashboard and broker pages (four levels L1–L4) | frontend | `documented` | `user/dashboard/risk.en.md` |
| [[F-112]] | Risk Lab of Asset Global (correlation, losses, risk–return, replay) | frontend | `documented` | `user/assets/correlation.en.md` |
| [[F-113]] | Risk tab of Asset Detail (legacy panel, beta) | frontend | `implemented` | — |

---

## Domain: CALCULATIONS (Backend-only)

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-056]] | FIFO at Runtime (on-demand cost basis) | backend | `documented` | `financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` |
| [[F-057]] | Currency Conversion (triangulation via FX graph) | backend | `implemented` | — |
| [[F-058]] | ROI Calculations (TWRR + MWRR) | backend | `documented` | `financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.en.md` |
| [[F-107]] | PAC allocator (purchase planner: SCIP search, exact replay, broker increments) | fullstack | `documented` | `user/tools/pac-allocator/index.en.md` |
| [[F-110]] | Risk engine (analytic plugins, quant libraries in spawned processes) | backend | `documented` | [`dev/be/risk/architecture.md`](developer/backend/risk/architecture.md) |

---

## Domain: INFRASTRUCTURE

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-059]] | Provider Registry Pattern (auto-discovery via decorator) | backend | `implemented` | [`dev/arch/patterns/registry_pattern.md`](developer/architecture/patterns/registry_pattern.md) |
| [[F-060]] | Thread Isolation for Providers | backend | `implemented` | [`dev/arch/overview.md`](developer/architecture/overview.md) |
| [[F-061]] | 5-layer Provider Cache | backend | `implemented` | — |
| [[F-062]] | Docker Single-Image Deploy | infra | `documented` | `admin/docker_advanced.en.md` |
| [[F-063]] | dev.py CLI (single entry point) | infra | `documented` | `admin/cli_tools.en.md` |
| [[F-064]] | Data Separation prod/test (isolated SQLite) | backend | `implemented` | [`dev/arch/database/index.md`](developer/architecture/database/index.md) |
| [[F-065]] | JWT Cookie Auth (stateless, multi-worker) | backend | `implemented` | — |
| [[F-066]] | Zodios API Client (OpenAPI types + Zod validation) | frontend | `implemented` | — |
| [[F-067]] | Playwright E2E Tests (181+ tests) | infra | `implemented` | [`dev/tests/index.md`](developer/test-walkthrough/index.md) |
| [[F-068]] | Backend API Tests (276+ pytest tests) | infra | `implemented` | [`dev/tests/index.md`](developer/test-walkthrough/index.md) |
| [[F-069]] | MkDocs Multi-Language Documentation | infra | `documented` | `developer/` |
| [[F-070]] | Aphra LLM Translation Pipeline | infra | `implemented` | [`dev/docs/translation-pipeline.md`](developer/docs/translation-pipeline.md) |
| [[F-071]] | EditBuffer Pattern (bidirectional inline editor) | frontend | `implemented` | [`developer/frontend/components/core-ui/data-editor.md`](developer/frontend/components/core-ui/data-editor.md) |
| [[F-072]] | TimeSeriesStore Pattern (delta-fetching client cache) | frontend | `implemented` | [`dev/fe/state/index.md`](developer/frontend/state/index.md) |
| [[F-073]] | Backup & Restore | fullstack | `documented` | [`admin/backup_restore.en.md`](admin/backup_restore.en.md) |
| [[F-074]] | E2E Test Gallery (auto-screenshots for docs) | infra | `implemented` | — |
| [[F-106]] | Tool platform (atomic Tool plugins, an owned process per item, compiled renderers) | fullstack | `documented` | [`dev/arch/patterns/tool_plugins.en.md`](developer/architecture/patterns/tool_plugins.en.md) |

---

## Domain: PLANNED / IDEA (future features, not yet built)

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-075]] | TanStack Table v9 Migration | frontend | `superseded` | — |
| [[F-076]] | Log Level Policy & TRACE Level | backend | `implemented` | — |
| [[F-077]] | Mobile DataTable Touch Drag Column Reorder | frontend | `planned` | — |
| [[F-078]] | User Filter in Files Page (an uploader column filter, for every user) | fullstack | `implemented` | — |
| [[F-079]] | GDPR Broker Access Compliance | fullstack | `planned` | — |
| [[F-080]] | Candlestick Chart / Volume Bars | frontend | `documented` | `user/assets/detail/chart.en.md` |
| [[F-081]] | Fiscal Sale Method (FIFO/LIFO/PMC/SelectID) | fullstack | `planned` | — |
| [[F-082]] | Cash Split Transactions | fullstack | `planned` | — |
| [[F-083]] | Multi-File Multi-Broker Import | fullstack | `documented` | [`dev/fe/import-wizard.md`](developer/frontend/components/features/import-wizard.md) |
| [[F-084]] | Transaction Gain Chart | frontend | `planned` | — |
| [[F-085]] | QuarkAI AI Assistant | fullstack | `idea` | — |
| [[F-086]] | Client-side Image Preview Cache (LazyImage) | frontend | `implemented` | — |
| [[F-087]] | Smooth Signal Line Style | frontend | `implemented` | — |
| [[F-088]] | Rolling (Return-over-N) Return chart mode | fullstack | `documented` | `user/assets/detail/chart.en.md` |
| [[F-089]] | FX Provider Per-Plugin Documentation | infra | `documented` | `user/fx/providers/index.en.md` |
| [[F-090]] | AssetEvent → Transaction Link (Enrichment) | backend | `planned` | — |
| [[F-091]] | Multi-Worker Cache Server | backend | `planned` | — |
| [[F-092]] | Default Language/Currency for New Users | backend | `documented` | `admin/settings.en.md` |
| [[F-093]] | Coupon Policy Field | backend | `idea` | — |
| [[F-094]] | Sync Date Range Dialog | frontend | `documented` | `user/fx/sync.en.md` |
| [[F-095]] | Asset Delete — Transaction Count Link | fullstack | `documented` | `user/assets/index.en.md` |
| [[F-096]] | Scheduled Investment — Decoupled Frequencies + Anchor Day | backend | `idea` | — |
| [[F-097]] | WAC — Weighted Average Cost (cross-currency, auto-calc on TRANSFER) | fullstack | `documented` | [`dev/be/transactions/wac.md`](developer/backend/transactions/wac.md) |
| [[F-098]] | Progressive Web App (PWA) | frontend | `documented` | `user/pwa.en.md` |
| [[F-099]] | Borsa Italiana Asset Provider | fullstack | `documented` | `user/assets/providers/borsa-italiana.en.md` |
| [[F-108]] | Portfolio Rebalancer (PAC engine with existing positions, sales and taxes) | fullstack | `planned` | — |

---

## Statistics

> Recomputed from the rows above on 2026-10-09 (the previous table still counted 96 features and listed F-052/F-053
> as planned), and again on 2026-10-12 after the lint (F-050, F-089, F-092 shipped; F-075 superseded) and after
> steps B5, B6a and B6b (F-105 to F-108 added), step B8 (F-109), and step R0 of folder 02 (F-110–F-113, Risk). "PLANNED / IDEA" is the section where a feature was first
> registered, not its status: twelve of its rows have shipped (F-078 recognised in step C) and one is superseded.
> **C-64, the status check of 2026-10-12**: F-048 had shipped in 1.0.0 and is `documented`. The ten `planned` rows and
> the three `idea` rows were checked against the code and stay as they are: none is in 1.2 (F-108 has its contract
> only; F-090 has parts built under F-051, its provider-change modal and reverse lookup are not — C-65; F-094's sync
> dialogs exist, the warning on existing data is C-66). *2026-10-15*: F-090's reverse lookup was built (C-65b,
> `021bc37cd`), and the provider-change modal (C-65a) keeps it `planned`. *2026-11-07 (lint)*: F-087 shipped as the
> line shape setting for every chart (`610c6af4d`, 2026-10-30) and F-094's warning on existing data (C-66) as
> `54996bf07` (2026-10-16): eight `planned` rows remain. The other `planned` and `idea` rows were checked against the
> code and stay (F-084 is partly covered by the Lots Analysis, F-082 by the import split; see their pages).

| Domain | Total | implemented/documented | in-progress | planned | idea | superseded |
|--------|-------|----------------------|-------------|---------|------|------------|
| AUTH | 4 | 4 | 0 | 0 | 0 | 0 |
| LAYOUT & SETTINGS | 9 | 9 | 0 | 0 | 0 | 0 |
| BROKERS | 7 | 7 | 0 | 0 | 0 | 0 |
| FX | 9 | 9 | 0 | 0 | 0 | 0 |
| ASSETS | 14 | 14 | 0 | 0 | 0 | 0 |
| SIGNALS | 9 | 9 | 0 | 0 | 0 | 0 |
| TRANSACTIONS | 6 | 6 | 0 | 0 | 0 | 0 |
| SCHEDULER | 2 | 2 | 0 | 0 | 0 | 0 |
| DASHBOARD | 6 | 6 | 0 | 0 | 0 | 0 |
| CALCULATIONS | 5 | 5 | 0 | 0 | 0 | 0 |
| INFRASTRUCTURE | 17 | 17 | 0 | 0 | 0 | 0 |
| PLANNED/IDEA (first registered) | 26 | 14 | 0 | 8 | 3 | 1 |
| **TOTAL** | **114** | **102** | **0** | **8** | **3** | **1** |

## Key source files

| Role | Path |
|------|------|
| Feature files directory | `LibreFolio_devWiki/wiki/features/` |
| All API endpoints | `backend/app/api/v1/` |
| All services | `backend/app/services/` |
| Frontend routes | `frontend/src/routes/(app)/` |
| mkdocs developer docs | `mkdocs_src/docs/developer/` |
