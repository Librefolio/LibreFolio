# 📄 Frontend Pages

*Status: Implemented (Feb 2026)*

## 📖 Overview

Application pages and routing structure. All authenticated routes are under `(app)/`. The build is
a static SPA: SSR is off in the root `+layout.ts` (FastAPI serves the static files), and only the
login page is prerendered.

## 🗺️ Page Structure

```
frontend/src/routes/
├── +layout.svelte            # Root layout (i18n init, splash removal, <html lang>)
├── +layout.ts                # ssr = false
├── +page.svelte              # Login page (public)
├── +page.ts                  # prerender = true
├── +error.svelte             # Error page
├── (app)/                    # Authenticated routes
│   ├── +layout.svelte        # App shell: auth check, bootstrap/onboarding gate, sidebar, header, guide host
│   ├── +layout.ts            # ssr = false, prerender = false
│   ├── welcome/
│   │   └── +page.svelte      # Welcome setup (onboarding), shown without the app shell
│   ├── dashboard/
│   │   └── +page.svelte      # Main dashboard
│   ├── brokers/
│   │   ├── +page.svelte      # Broker list
│   │   └── [id]/
│   │       ├── +page.svelte  # Broker detail
│   │       └── +page.ts      # Load function (brokerId)
│   ├── transactions/
│   │   ├── +page.svelte      # Transactions list and management
│   │   └── filterState.ts    # URL ⇄ filter state
│   ├── assets/
│   │   ├── +page.svelte      # Assets list and management
│   │   └── [id]/
│   │       ├── +page.svelte  # Asset detail
│   │       └── +page.ts      # Load function (assetId; invalid id → /assets)
│   ├── fx/
│   │   ├── +page.svelte      # FX pairs list and management
│   │   └── [pair]/
│   │       ├── +page.svelte  # FX pair detail
│   │       └── +page.ts      # Load function (pair slug; invalid slug → /fx)
│   ├── tools/
│   │   ├── +page.svelte      # Tools hub (ToolsHub)
│   │   └── [tool_code]/
│   │       └── +page.svelte  # One tool (ToolHost)
│   ├── files/
│   │   └── +page.svelte      # Files management (static + BRIM tabs)
│   └── settings/
│       └── +page.svelte      # Settings (4 tabs)
```

## 📋 Pages

### 🔐 Login Page (`/`)

- Public access
- **LoginCard** / **RegisterCard** / **ForgotPasswordCard** (card-style, not modals)
- Animated background with waves and chart lines
- Redirect to dashboard after login
- User preferences (language, theme) applied on login

### 👋 Welcome (`/welcome`)

- First-run setup of the onboarding: language, base currency and avatar
- Rendered by the `(app)` layout without the app shell (no sidebar or header)
- The layout's gate sends the user here (`/welcome?returnTo=<requested path>`) while the Welcome
  flow is due or a Welcome replay is armed (`appBootstrap.resolveDestination`); afterwards the
  page continues to `returnTo`, or to `/dashboard` when the intro tour starts
- Architecture: [Onboarding Guides](../onboarding.md)

### 📊 Dashboard (`/dashboard`) {: #dashboard }

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard" style="width: 100%; display: block;">
</div>

- Portfolio view in four tabs: Overview (`KpiSection`, `GrowthChart`, `AllocationPanel`),
  Positions (`PositionsPanel`, with the FIFO `LotsAnalysisPanel`), Risk (`RiskLevelsPanel`) and
  Transactions (`TransactionsTable`)
- Toolbar with the date range (`DateRangePicker`) and the display currency
  (`CurrencySearchSelect`)
- [DataQualityBanner](../data-quality-banner.md) above the tabs; its actions can open
  `FxPairAddModal` to add a missing FX pair
- **KPI row** — `KpiSection`, also mounted on the broker detail Overview:
    - it reads `PortfolioSummary`: `period_pnl` and its rows `period_unrealized_gain_loss_delta`
      (tooltip rows `period_unrealized_breakdown`, in backend order), `period_realized_gain_loss`,
      `period_income` and `period_fees_taxes` (a positive magnitude, shown negated; the tooltip
      splits `period_fees` / `period_taxes`); `simple_roi_percent`, `twrr_percent`,
      `mwrr_cumulative_percent`, `mwrr_annualized_percent`; `net_worth`, `total_gain_loss` with
      `total_gain_loss_percent` (since inception), `market_value`, `open_cost_basis`, `cash_total`
      and `net_deposited_capital` (`total_deposited` / `total_withdrawn`, period only)
    - the start-of-period carets come from `period_market_value_start`, `period_book_value_start`
      and the first history point's `cash_value`; the Cash tooltip from the last history point's
      `cash_from_contributed_capital` / `cash_from_generated_returns`
    - the day-change lines are computed in the browser from the last two history points: Δ of
      `total_pnl`, divided by the previous `|total_pnl|` (Card 1) or `|nav_value|` (Card 2); a zero
      base drops the percentage, and fewer than two points drops the line
    - the timing effect is `mwrr_cumulative_percent − twrr_percent` in pp, labelled neutral below
      0.05 pp; its colour intensity saturates at 3 pp
    - each card's help icon is a `DocsLink` to `user/dashboard/kpi-cards/#card-1-period-pl`,
      `#card-2-returns` and `#card-3-net-worth`: keep these explicit anchors in every language
- **Positions tab** — `PositionsPanel`, also mounted on the broker detail Positions tab:
    - Holdings / Performance (labelled **Portfolio** / **Period**) × Table / Map: `ExposureTable`,
      `ExposureTreemap`, `ContributionTable` with `OtherPeriodEffectsTable`, `PerformanceChart`;
      both toggles persist per user in `localStorage` (`dashboard-positions-semantic`,
      `dashboard-positions-visual`)
    - the table layouts (`dashboard-holdings-v5`, `dashboard-performance-v2`) are shared with the
      broker detail page; the Performance Status filter is a hidden-by-default enum column of
      `ContributionTable`, not a panel toggle, and `PerformanceChart` shows an Open / Closed badge
    - `positions_contribution` is fetched apart, on demand: `PositionsPanel` asks for it the first
      time the Performance view is shown; a cached copy shows at once and is refreshed when stale
    - the lots panel opens from the **Analyze Lots** row action (⋮) or the right-click menu of
      every view — there is no plain-click trigger — and is mirrored in `?asset=<id>`;
      `LotsAnalysisPanel` renders inline below, with a slide transition, and scrolls itself into
      view. Its `broker_ids` are the broker filter, or every owned broker with a share above 0%
    - architecture: [Lots Analysis](../components/features/lots-analysis.md) and the
      [Lots Analysis Service](../../backend/transactions/lots_analysis_service.md)

### 🏦 Brokers (`/brokers`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; display: block;">
</div>

- Grid of broker cards with icons ([fallback chain](../components/features/brokers/forms.md#brokericon))
- Add/Edit broker via **BrokerModal** (extends ModalBase); the icon is picked in the form
  (`ImagePickerWrapper` → **AssetPickerModal**)
- Sharing via **BrokerSharingModal**; brokers the user has no access to are listed apart as
  `BrokerDiscoveryCard`s, whose sharing view is read-only
- Delete via **DeleteBrokerDialog**, with a force option when the broker still has transactions

#### 🔍 Broker Detail (`/brokers/[id]`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Detail" style="width: 100%; display: block;">
</div>

- Header with back button, icon and name; toolbar actions: edit (**BrokerModal**, owners and
  editors), share (opens the Info tab), refresh, and AI export
- Tabs: Overview (KPIs, cash balances, growth chart, allocation), Positions (**Analyze Lots**, from
  the ⋮ menu or the right-click menu, opens the FIFO lots panel, mirrored in `?asset=<id>`), Risk,
  Transactions and Info
- Transactions tab: the broker's transactions, its report files (*Uploaded Reports* →
  **BrokerImportFilesModal**), a link to the Transactions page, and — for owners and editors —
  import and new transaction through the bulk workspace, with this broker pre-selected
- Info tab: broker details and the embedded sharing panel
  ([BrokerSharingPanel](../components/features/brokers/modals.md#broker-sharing-panel))

### 📝 Transactions (`/transactions`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Transactions List" style="width: 100%; display: block;">
</div>

- Master ledger of all user transactions
- Advanced filtering and pagination; filters are mirrored in the URL (`filterState.ts`)
- A row opens read-only in the Form modal; adding, editing, cloning, deleting and importing go
  through the bulk workspace (`TransactionBulkModal`). After every saved operation the page clears
  its selection ([Selection on the Transactions page](../state/transaction-draft.md#transactions-selection))

### 💼 Assets (`/assets`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="assets" data-name="list" alt="Asset List" style="width: 100%; display: block;">
</div>

- Full list of tracked financial instruments
- Interactive data tables with sorting and filtering

#### 🔍 Asset Detail (`/assets/[id]`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Detail" style="width: 100%; display: block;">
</div>

- [Live prices](../components/features/live-ticker.md) and historical charts (ECharts)
- Technical signals and related events
- Detailed performance metrics and history

### 💱 FX Rates (`/fx`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="fx" data-name="list" alt="FX List" style="width: 100%; display: block;">
</div>

- List of configured currency pairs and conversion rates
- Direct route and chain management
- Live data sync and technical signals

#### 🔍 FX Pair Detail (`/fx/[pair]`) {: #fx-pair-detail-fxid }

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="FX Detail" style="width: 100%; display: block;">
</div>

- `[pair]` is a slug such as `EUR-USD`: its order sets the display direction, while stores and API
  calls use the alphabetical (canonical) pair; an invalid slug redirects to `/fx` (`+page.ts`)
- Rate summary (`FxPriceSummary`), full chart with signals and measurements (`PriceChartFull`,
  `ChartSignalsSection`, `MeasurePanel`), and the rate editor (`FxDataEditorSection`)

### 🧰 Tools (`/tools`, `/tools/[tool_code]`)

- `/tools` mounts `ToolsHub`: the catalogue of computation tools read from
  `GET /api/v1/tools/catalog`, one card per tool with its compatibility label
- `/tools/[tool_code]` mounts `ToolHost`, which resolves the tool's compiled renderer in
  `lib/features/tools/registry.ts` and mounts it; a tool without a compatible renderer is shown as
  unavailable. Today the registry holds one tool, the PAC allocator
- Contract and frontend binding: [Tool plugins](../../architecture/patterns/tool_plugins.md#frontend-and-documentation)

### 📁 Files (`/files`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Files Page" style="width: 100%; display: block;">
</div>

- **Two tabs**: Static Resources / Broker Reports (BRIM)
- **DataTable** with sorting, filtering, pagination, URL-synced filters
- **Grid view** toggle with image previews and search
- Upload interface with:
    - Image files → **ImageEditModal** (crop, rotate, flip)
    - Non-image files → **FileEditModal** (rename)
- Copy link, download, delete actions
- File thumbnails via `?img_preview=` API

### ⚙️ Settings (`/settings`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="Settings Page" style="width: 100%; display: block;">
</div>

- **4 tabs**: Profile, Preferences, About, Admin (global settings); `?tab=` selects one
- **ProfileTab**: Avatar editing via AssetPickerModal, username display
- **PreferencesTab**: Language, currency, theme, and the Onboarding category (guide replays —
  see [Settings Components](../components/features/settings.md))
- **GlobalSettingsTab**: visible to every user, editable only by a superuser, behind an edit lock
- **AboutTab**: Version info (from Git tag), system info
- **PasswordChangeModal** from profile
- Mobile responsive with dropdown category selector

