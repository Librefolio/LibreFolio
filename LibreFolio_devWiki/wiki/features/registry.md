# Feature Registry

> Authoritative list of all LibreFolio features with permanent codes.
> Codes are assigned at first mention and **never change** even if the feature is renamed/split/superseded.
> Updated: 2026-04-24 (bootstrap from codebase analysis, phases 0–7 in progress)
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
| [[F-002]] | User Management (admin CRUD) | fullstack | `implemented` | [`dev/arch/database/users_access.md`](developer/architecture/database/users_access.md) |
| [[F-003]] | Multi-User Role System (admin/user) | fullstack | `implemented` | [`dev/arch/access_control.md`](developer/architecture/access_control.md) |

---

## Domain: LAYOUT & SETTINGS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-004]] | App Shell & Navigation (sidebar, header) | frontend | `implemented` | [`dev/fe/styling.md`](developer/frontend/styling.md) |
| [[F-005]] | User Settings (language, theme) | fullstack | `implemented` | [`dev/fe/components/settings.md`](developer/frontend/components/settings.md) |
| [[F-006]] | Global Settings (admin-managed app config) | fullstack | `implemented` | [`dev/arch/settings.md`](developer/architecture/settings.md) |
| [[F-007]] | Theme System (dark/light/auto) | frontend | `implemented` | — |
| [[F-008]] | i18n System (EN/IT/FR/ES, 840+ keys) | frontend | `implemented` | [`dev/fe/i18n.md`](developer/frontend/i18n.md) |

---

## Domain: BROKERS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-009]] | Broker CRUD | fullstack | `documented` | `user/brokers/index.en.md` |
| [[F-010]] | Broker Sharing (Owner/Editor/Viewer roles) | fullstack | `documented` | `user/brokers/sharing.en.md` |
| [[F-011]] | File Management (upload/list/delete broker reports) | fullstack | `documented` | `user/files/index.en.md` |
| [[F-012]] | BRIM Framework (broker report import pipeline) | fullstack | `implemented` | [`dev/be/brim/architecture.md`](developer/backend/brim/architecture.md) |
| [[F-013]] | BRIM Plugins (11 broker parsers) | backend | `implemented` | [`dev/be/brim/providers_list.md`](developer/backend/brim/providers_list.md) |
| [[F-014]] | Image Upload & Crop (broker icon) | fullstack | `implemented` | — |

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
| [[F-021]] | FX List View (dual view: card + table) | frontend | `implemented` | `user/fx/index.en.md` |
| [[F-022]] | FX Detail Page (rate history, provider mgmt) | frontend | `implemented` | — |
| [[F-023]] | FX Chart & Signal Overlay | frontend | `documented` | `user/fx/chart-settings.en.md` |

---

## Domain: ASSETS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-024]] | Asset CRUD | fullstack | `documented` | `user/assets/index.en.md` |
| [[F-025]] | Asset Provider Registry (yfinance, JustETF, CSS Scraper, Scheduled Investment) | backend | `documented` | `user/assets/providers/` |
| [[F-026]] | Asset Provider Assignment (dynamic params form) | fullstack | `implemented` | [`dev/be/assets/architecture.md`](developer/backend/assets/architecture.md) |
| [[F-027]] | Asset Data Sync (price fetch from providers) | fullstack | `implemented` | [`dev/be/assets/architecture.md`](developer/backend/assets/architecture.md) |
| [[F-028]] | Asset Search Autocomplete (multi-provider parallel) | frontend | `implemented` | — |
| [[F-029]] | Asset Metadata Refresh | fullstack | `implemented` | — |
| [[F-030]] | Asset Price History (OHLCV store/query) | backend | `implemented` | [`dev/arch/database/assets_pricing.md`](developer/architecture/database/assets_pricing.md) |
| [[F-031]] | Asset Events (DIVIDEND, SPLIT, INTEREST, etc.) | fullstack | `implemented` | [`dev/be/assets/events.md`](developer/backend/assets/events.md) |
| [[F-032]] | Asset List View (dual view: card + table) | frontend | `implemented` | `user/assets/index.en.md` |
| [[F-033]] | Asset Detail Page (chart, signals, editor) | frontend | `implemented` | `user/assets/detail/` |
| [[F-034]] | Scheduled Investment Provider (synthetic yield) | backend | `implemented` | `user/assets/providers/` |
| [[F-035]] | CSS Scraper Provider (arbitrary web scraping) | backend | `implemented` | `user/assets/providers/` |
| [[F-036]] | Provider Comparison Modal (diff provider vs DB) | frontend | `implemented` | — |

---

## Domain: TECHNICAL ANALYSIS (Signals)

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-037]] | Signal Library Framework (abstract base + registry) | frontend | `implemented` | — |
| [[F-038]] | EMA Signal | frontend | `implemented` | — |
| [[F-039]] | RSI Signal | frontend | `implemented` | — |
| [[F-040]] | MACD Signal | frontend | `implemented` | — |
| [[F-041]] | Bollinger Bands Signal | frontend | `implemented` | — |
| [[F-042]] | FX Pair Comparison Signal | frontend | `implemented` | — |
| [[F-043]] | Asset Comparison Signal | frontend | `implemented` | — |
| [[F-044]] | Benchmark Signals (Linear, Compound, Sine) | frontend | `implemented` | — |
| [[F-045]] | Measure Tool (2-click Δabs, Δ%, days) | frontend | `implemented` | — |

---

## Domain: TRANSACTIONS

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-046]] | Transaction Model & Unified Batch API (validate + commit) | fullstack | `implemented` | [`dev/arch/database/brokers_transactions.md`](developer/architecture/database/brokers_transactions.md) |
| [[F-047]] | Transaction List Page (DataTable + filters + dual-form modals) | frontend | `implemented` | — |
| [[F-048]] | Transaction Modals (Form / Bulk / Promote Wizard + server-driven type rules) | frontend | `in-progress` | — |
| [[F-049]] | BRIM Import UI (asset matching wizard, bulk commit) | frontend | `in-progress` | — |
| [[F-050]] | File Preview System (image/text/table/md/code) | fullstack | `planned` | — |
| [[F-051]] | Transaction ↔ AssetEvent Link | backend | `implemented` | — |

---

## Domain: SCHEDULER

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-052]] | Market Data Scheduler (APScheduler daemon) | backend | `planned` | — |
| [[F-053]] | Scheduler Settings UI (admin-managed cron config) | frontend | `planned` | — |

---

## Domain: DASHBOARD

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-054]] | Dashboard KPI & Overview | fullstack | `planned` | — |
| [[F-055]] | Portfolio Charts (allocation, evolution) | frontend | `planned` | — |

---

## Domain: CALCULATIONS (Backend-only)

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-056]] | FIFO at Runtime (on-demand cost basis) | backend | `implemented` | — |
| [[F-057]] | Currency Conversion (triangulation via FX graph) | backend | `implemented` | — |
| [[F-058]] | ROI Calculations (Simple + Duration-Weighted) | backend | `planned` | — |

---

## Domain: INFRASTRUCTURE

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-059]] | Provider Registry Pattern (auto-discovery via decorator) | backend | `implemented` | [`dev/arch/patterns/registry_pattern.md`](developer/architecture/patterns/registry_pattern.md) |
| [[F-060]] | Thread Isolation for Providers | backend | `implemented` | [`dev/arch/overview.md`](developer/architecture/overview.md) |
| [[F-061]] | 5-layer Provider Cache | backend | `implemented` | — |
| [[F-062]] | Docker Single-Image Deploy | infra | `documented` | `admin/docker_advanced.en.md` |
| [[F-063]] | dev.py CLI (single entry point) | infra | `implemented` | `admin/cli_tools.en.md` |
| [[F-064]] | Data Separation prod/test (isolated SQLite) | backend | `implemented` | [`dev/arch/database/index.md`](developer/architecture/database/index.md) |
| [[F-065]] | JWT Cookie Auth (stateless, multi-worker) | backend | `implemented` | — |
| [[F-066]] | Zodios API Client (OpenAPI types + Zod validation) | frontend | `implemented` | — |
| [[F-067]] | Playwright E2E Tests (181+ tests) | infra | `implemented` | [`dev/tests/index.md`](developer/test-walkthrough/index.md) |
| [[F-068]] | Backend API Tests (276+ pytest tests) | infra | `implemented` | [`dev/tests/index.md`](developer/test-walkthrough/index.md) |
| [[F-069]] | MkDocs Multi-Language Documentation | infra | `documented` | `developer/` |
| [[F-070]] | Aphra LLM Translation Pipeline | infra | `implemented` | [`dev/docs/translation-pipeline.md`](developer/docs/translation-pipeline.md) |
| [[F-071]] | EditBuffer Pattern (bidirectional inline editor) | frontend | `implemented` | [`dev/fe/components/ui-base/data-editor.md`](developer/frontend/components/ui-base/data-editor.md) |
| [[F-072]] | TimeSeriesStore Pattern (delta-fetching client cache) | frontend | `implemented` | [`dev/fe/state/index.md`](developer/frontend/state/index.md) |
| [[F-073]] | Backup & Restore | fullstack | `implemented` | — |
| [[F-074]] | E2E Test Gallery (auto-screenshots for docs) | infra | `implemented` | — |

---

## Domain: PLANNED / IDEA (future features, not yet built)

| Code | Title | Layer | Status | mkdocs |
|------|-------|-------|--------|--------|
| [[F-075]] | TanStack Table v9 Migration | frontend | `planned` | — |
| [[F-076]] | Log Level Policy & TRACE Level | backend | `planned` | — |
| [[F-077]] | Mobile DataTable Touch Drag Column Reorder | frontend | `planned` | — |
| [[F-078]] | User Filter in Files Page | fullstack | `planned` | — |
| [[F-079]] | GDPR Broker Access Compliance | fullstack | `planned` | — |
| [[F-080]] | Candlestick Chart / Volume Bars | frontend | `planned` | — |
| [[F-081]] | Fiscal Sale Method (FIFO/LIFO/PMC/SelectID) | fullstack | `planned` | — |
| [[F-082]] | Cash Split Transactions | fullstack | `planned` | — |
| [[F-083]] | Multi-File Multi-Broker Import | fullstack | `planned` | — |
| [[F-084]] | Transaction Gain Chart | frontend | `planned` | — |
| [[F-085]] | QuarkAI AI Assistant | fullstack | `idea` | — |
| [[F-086]] | Client-side Image Preview Cache (LazyImage) | frontend | `planned` | — |
| [[F-087]] | Smooth Signal Line Style | frontend | `planned` | — |
| [[F-088]] | Return-over-N Chart | frontend | `planned` | — |
| [[F-089]] | FX Provider Per-Plugin Documentation | infra | `planned` | — |
| [[F-090]] | AssetEvent → Transaction Link (Enrichment) | backend | `planned` | — |
| [[F-091]] | Multi-Worker Cache Server | backend | `planned` | — |
| [[F-092]] | Default Language/Currency for New Users | backend | `planned` | — |
| [[F-093]] | Coupon Policy Field | backend | `idea` | — |
| [[F-094]] | Sync Date Range Dialog | frontend | `planned` | — |
| [[F-095]] | Asset Delete — Transaction Count Link | fullstack | `planned` | — |
| [[F-096]] | Scheduled Investment — Decoupled Frequencies + Anchor Day | backend | `idea` | — |

---

## Statistics

| Domain | Total | implemented/documented | in-progress | planned |
|--------|-------|----------------------|-------------|---------|
| AUTH | 3 | 3 | 0 | 0 |
| LAYOUT | 5 | 5 | 0 | 0 |
| BROKERS | 6 | 6 | 0 | 0 |
| FX | 9 | 9 | 0 | 0 |
| ASSETS | 13 | 13 | 0 | 0 |
| SIGNALS | 9 | 9 | 0 | 0 |
| TRANSACTIONS | 6 | 3 | 1 | 2 |
| SCHEDULER | 2 | 0 | 0 | 2 |
| DASHBOARD | 2 | 0 | 0 | 2 |
| CALCULATIONS | 3 | 2 | 0 | 1 |
| INFRASTRUCTURE | 16 | 15 | 0 | 1 |
| PLANNED/IDEA | 22 | 0 | 0 | 22 |
| **TOTAL** | **96** | **62** | **3** | **31** |

## Key source files

| Role | Path |
|------|------|
| Feature files directory | `LibreFolio_devWiki/wiki/features/` |
| All API endpoints | `backend/app/api/v1/` |
| All services | `backend/app/services/` |
| Frontend routes | `frontend/src/routes/(app)/` |
| mkdocs developer docs | `mkdocs_src/docs/developer/` |
