# Dashboard Bottom Widgets — Technical Analysis Report

> Generated: 2026-06-26  
> Scope: read-only analysis, no code changes  
> Based on: codebase grep + plan_ui_dashboard.md (1534 lines) + wiki-search

---

## 1. Executive Summary

### What is already ready

| Item | Status |
|------|--------|
| `HoldingsPanel.svelte` | ✅ exists — but very basic (4 cols, no broker, no toggle, no treemap) |
| `RecentTransactionsPanel.svelte` | ✅ exists — mostly complete but Qty layout + interactions wrong |
| `portfolioStore` → `fetchReport()` | ✅ cache + deduplication, single POST /portfolio/report |
| `PortfolioHolding` DTO (partial) | ✅ has asset_id, type, qty, value, gain_loss%, allocation_percent |
| Period P&L at portfolio level | ✅ unrealized_delta, realized, income, fees_taxes all in PortfolioSummary |
| ECharts infrastructure | ✅ tooltip helpers, dark mode, responsive, palette |
| Shared formatters | ✅ `formatCurrencyAmountHtml/Plain`, `getAssetTypeIconUrl`, `getStringBadgeStyle` |
| `DataTable` + double-click | ✅ `onRowDoubleClick` prop, context-menu, long-press-for-selection |
| Treemap chart component | ❌ does NOT exist yet |

### What is missing / must be built

1. **`broker_id`/`broker_name` NOT in `PortfolioHolding` DTO** — available inside the backend loop but never included in the Pydantic model. Blocking for both Esposizione/Mappa hierarchy (Broker → AssetType → Asset) and for the Broker column in the table views.
2. **Per-asset period P&L attribution** — zero backend support. The engine accumulates `_income_accum`, `_fees_taxes_accum`, `_realized_accum` at portfolio level only. No per-(broker, asset) breakdown for the Contributo view.
3. **`allocation_percent` semantic mismatch** — current field = `current_value / sum_market_values` (excludes cash). Plan wants `current_value / NAV` (includes cash). Frontend can compute correct value from `PortfolioHolding.current_value / PortfolioSummary.net_worth.amount`.
4. **No treemap ECharts component** — must be created from scratch following existing pattern.
5. **Shared cell components not extracted** — `typeBadgeHtml`, `assetIconHtml`, broker badge are inline functions in AssetTable/TransactionsTable, not shared components.
6. **RecentTransactionsPanel: 3 gaps** — Qty sub-row (not column), Qty has colors (plan: neutral), no row interactions (double-click / long-press).
7. **i18n: ~10 keys missing** — `exposure`, `contribution`, `viewTable`, `viewMap`, `weight`, `impact`, `qty`, `periodReturn`, empty-states for contribution mode.

### Main risk

> **Backend per-asset P&L attribution is the hardest dependency.** The Contributo view (both table and treemap) requires per-asset `unrealized_delta + realized + income - fees_taxes` for the selected period. This does NOT exist in any form today. It requires a non-trivial new computation path in `portfolio_service.py` / `portfolio_engine.py`. Until this is built, the Contributo view cannot be completed.

### Implementation recommendation

Implement in two decoupled phases:

- **Phase A** — Esposizione widget (table + treemap) + RecentTransactions fix. Requires only small backend change (add `broker_id`/`broker_name` to PortfolioHolding + fix `allocation_percent` semantics).
- **Phase B** — Contributo widget. Requires new backend DTO `PositionsPeriodPnl` and per-asset attribution engine changes. Can be gated behind a feature flag.

---

## 2. Existing Frontend Resources

### 2.1 Asset table / cells / formatters

**`frontend/src/lib/components/assets/AssetTable.svelte`**

- DataTable-based, columns: Icon, Name, Type (badge), Currency (flag), Last Price, Δ-deltas per period, Provider, Active
- **Inline** (not extracted) helpers: `assetIconHtml()`, `typeBadgeHtml()`, `formatDelta()`, `deltaColorClass()`
- `typeBadgeHtml()` produces colored badge + PNG icon via `getAssetTypeIconUrl()` — pattern is solid
- `formatCurrencyAmountHtml()` is imported from `$lib/utils/currency/currencyFormat.ts` ✅ (shared)
- `getAssetTypeIconUrl()` is imported from `$lib/utils/assetTypes.ts` ✅ (shared)
- `getStringBadgeStyle()`, `getStringColor()` from `$lib/utils/colors.ts` ✅ (shared)

**`frontend/src/lib/components/dashboard/HoldingsPanel.svelte`**

- Simple `<table>`, NO DataTable — 4 columns: Asset (icon+name), Current Price, Value, Gain%
- All formatters are local inline functions (`safeNum`, `formatPrice`, `formatValue`, `formatGainPct`, `gainClass`)
- `assetIconHtml()` duplicated here vs AssetTable — same logic, not shared
- Gets `holdings: PortfolioHolding[]` as prop (passed from dashboard page `summary.holdings`)
- No broker column, no type badge, no weight/allocation column, no toggle

**Shared utilities available for extraction**

| Utility | File | Reusable for dashboard widget |
|---------|------|-------------------------------|
| `formatCurrencyAmountHtml/Plain` | `utils/currency/currencyFormat.ts` | ✅ yes |
| `getAssetTypeIconUrl` | `utils/assetTypes.ts` | ✅ yes |
| `getStringBadgeStyle` / `getStringColor` | `utils/colors.ts` | ✅ yes (for type badge) |
| `getBrokerColor` | `utils/broker/brokerColors.ts` | ✅ yes (for broker tint) |
| `getBrokerIconUrlById` | `utils/broker/brokerHelpers.ts` | ✅ yes |
| `getAssetInfo` | `stores/reference/assetStore.ts` | ✅ yes |
| `getBrokerInfo` | `stores/reference/brokerStore.ts` | ✅ yes |

**Cells to centralize** (do NOT exist yet as standalone components):

```
AssetIdentityCell   → icon + name (duplicated in HoldingsPanel, AssetTable, RecentTransactionsPanel)
AssetTypeBadge      → colored badge + type icon (inline in AssetTable.typeBadgeHtml)
BrokerBadge         → icon + name (inline in TransactionsTable & RecentTransactionsPanel)
MoneyCell           → currency amount with optional sign + color
PercentCell         → weight %, with optional color by sign
PnlCell             → P&L amount + % with red/green
```

Extracting to `frontend/src/lib/components/dashboard/cells/` would eliminate duplication across HoldingsPanel, the new PositionsPanel, and RecentTransactionsPanel.

### 2.2 Transaction table / compact possibilities

**`frontend/src/lib/components/transactions/TransactionsTable.svelte`** (54 KB)

- Full DataTable-based, 1500+ lines
- Pair-adjacent rendering (TRANSFER/FX_CONVERSION), ghost rows, pair-never-split paginator
- Props relevant to home variant:
  - `onRowDoubleClick?: (row) => void` ✅
  - `hideActions?: boolean` ✅ (hides CRUD actions + context menu)
  - `enableTouchSelection?: boolean` (touch = selection toggle, NOT view → insufficient for plan)
  - `enableContextMenu?: boolean`
- Long-press (500ms) in DataTable → triggers **selection toggle**, NOT row view. Needs separate handler for mobile home.
- **Verdict**: TransactionsTable is too complex to reuse directly in compact/home mode. It requires `mainRows + partnerRows` (not a simple `limit` param), no built-in "compact" mode. The existing `RecentTransactionsPanel.svelte` is the correct base to evolve.

**`frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte`**

Current columns: Date | Type (icon only, no text) | Asset | Broker | Amount+Qty(sub-row)  
Target columns:  Date | Type | Asset | Broker | Qty (separate) | Amount

Gaps vs plan:
1. Qty is rendered as a sub-row below Amount in the same `<td>` — NOT a separate column
2. `quantityClass()` returns green/red — plan says neutral (no colors on Qty)
3. No `ondblclick` handler on `<tr>` elements
4. No long-press mobile → view (no touch event listener on rows)
5. Self-fetches via `zodiosApi` directly — bypasses portfolioStore cache

Column configurability: zero (hardcoded). No `variant` prop, no hidden columns, no `compact` mode.  
Mobile scroll: ✅ `overflow-x-auto` already present.

### 2.3 ECharts reusable patterns

**Existing chart components:**

| Component | Location | ECharts type |
|-----------|----------|--------------|
| `AllocationPieChart.svelte` | `lib/components/charts/` | Pie |
| `LineChart.svelte` | `lib/components/charts/` | Line + area |
| `CandlestickChart.svelte` | `lib/components/charts/` | Candlestick + 2-grid |
| `SemiDonutChart.svelte` | `lib/components/charts/` | Pie (semi) |
| `GeographyMap.svelte` | `lib/components/charts/` | Map |
| `GrowthChart.svelte` | `lib/components/dashboard/` | Line (multi-series) |
| `AllocationHistoryChart.svelte` | `lib/components/dashboard/` | Stacked area |
| `AllocationPieChart.svelte` | `lib/components/charts/` | Pie |

**Standard pattern** (all charts follow this):
```ts
onMount(() => {
    chartInstance = echarts.init(container, isDark ? 'dark' : undefined);
    // MutationObserver on document.documentElement → re-render on dark mode class change
    // ResizeObserver on container → chartInstance.resize()
    return () => { cleanup(); }
});
$effect(() => { renderChart(); }); // re-renders on prop changes
```

**Shared infrastructure:**
- `echartsTooltipHelpers.ts` — `buildTooltipTheme`, `buildTooltipRow`, `buildDot`, `buildTooltipHeader`, `buildTooltipDivider`, `buildTooltipTopN`, `tooltipPositionAboveFinger`, `tooltipPositionSide`, `setupTooltipAutoHide`
- `chartCoreHelpers.ts` — additional chart helpers
- Color palettes: `PALETTE_LIGHT`, `PALETTE_DARK` defined per-component (could be centralized but aren't)

**Treemap**: NOT present. Must be built. ECharts supports `type: 'treemap'` natively with `children` array for hierarchy. Nested levels with Broker → AssetType → Asset are standard ECharts capability.

**Known ECharts issues from wiki**: candlestick payload is `[open, close, low, high]` (non-standard). No open ECharts issues.

### 2.4 Shared UI primitives

Available and reusable:
- `Tooltip.svelte` (`lib/components/ui/feedback/`)
- `ContextMenu.svelte` + `ContextMenuItem`
- `DateRangePicker.svelte` (used in dashboard header)
- `SimpleSelect.svelte`, `SearchSelect.svelte`
- `DataTable.svelte` with full feature set

---

## 3. Existing Backend/API Resources

### 3.1 Dashboard endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/portfolio/summary` | POST | KPIs + holdings + allocations |
| `POST /api/v1/portfolio/history` | POST | Daily NAV series |
| `POST /api/v1/portfolio/allocation-history` | POST | Allocation time series |
| `POST /api/v1/portfolio/report` | POST | All of the above in one engine run |
| `GET /api/v1/portfolio/lots` | GET | FIFO lots per (broker, asset) |
| `GET /api/v1/portfolio/asset-history` | GET | WAC vs market price per asset |
| `GET /api/v1/transactions` | GET | Paginated transactions (supports `limit`, `broker_id`) |

The `portfolioStore.fetchReport()` uses `POST /portfolio/report` to get summary + history + allocation_history in one call. `RecentTransactionsPanel` uses `GET /api/v1/transactions` directly.

### 3.2 Asset/position data availability

**`PortfolioHolding`** (current schema — `backend/app/schemas/portfolio.py` line 265):

```python
class PortfolioHolding(BaseModel):
    asset_id: int
    asset_name: str
    asset_ticker: Optional[str]
    asset_type: str
    quantity: SafeDecimal
    wac_per_unit: Optional[SafeDecimal]    # None if FX missing
    current_price: Optional[SafeDecimal]   # None if price missing
    current_value: Optional[SafeDecimal]
    gain_loss: Optional[SafeDecimal]       # = current_value - (wac_per_unit × qty)  ← TOTAL unrealized only
    gain_loss_percent: Optional[SafeDecimal]
    allocation_percent: Optional[SafeDecimal]  # = current_value / Σ(market values)  ← NOT NAV-based
```

**Gap inventory for Esposizione table** (view 1):

| Column | Available | Notes |
|--------|-----------|-------|
| Asset identity | ✅ asset_id, asset_name, asset_ticker | |
| Asset type | ✅ asset_type | |
| Broker | ❌ **MISSING** | `broker_id`/`broker_name` are in service loop but not in DTO |
| Valore (market value) | ✅ current_value | |
| Peso (NAV weight) | ⚠️ `allocation_percent` wrong basis | Computed as current_value / total_market, NOT / NAV. **Frontend can compute correctly**: `current_value / net_worth.amount * 100` |
| P&L totale | ✅ gain_loss | Lifetime unrealized = current_value - cost_basis |

**Gap inventory for Contributo table** (view 3):

| Column | Available | Notes |
|--------|-----------|-------|
| Asset identity | ✅ | |
| Asset type | ✅ | |
| Broker | ❌ MISSING | Same as above |
| P&L periodo | ❌ **NOT IN BACKEND** | Requires new per-asset period attribution |
| Var. % (period return) | ❌ **NOT IN BACKEND** | Asset-level TWRR for period — complex |
| Impatto | ❌ derived | Computed frontend from P&L periodo vs scale_max |

**Esposizione/Mappa** (view 2): needs `broker_id` per holding for hierarchy Broker → AssetType → Asset.

### 3.3 Transaction data availability

`GET /api/v1/transactions` supports:
- `limit` ✅
- `broker_id` ✅
- `date_from`, `date_to` (available, not used by RecentTransactionsPanel today)
- Returns: `id, date, type, asset_id, broker_id, quantity, cash` (full TXReadItem)

`RecentTransactionsPanel.svelte` already fetches the last N txns directly. Current approach:
- Fetches `limit * 3` rows to filter out partner halves
- Filters: keeps only non-partner rows (skips ghost halves of transfers)
- Sort: date desc + id desc as tiebreaker
- This logic is correct and sufficient for home view

### 3.4 Missing DTO/data

**Missing DTO #1 — broker_id in PortfolioHolding**

Change to `portfolio_service.py` (portfolio_service line ~796) + schema:
```python
class PortfolioHolding(BaseModel):
    ...
    broker_id: Optional[int] = None      # ADD
    broker_name: Optional[str] = None    # ADD
```
Backend already has these values in the loop. Small fix. Requires `./dev.py api sync` after.

**Missing DTO #2 — PositionsPeriodPnl (new, for Contributo view)**

Proposed new schema:
```python
class AssetPeriodContribution(BaseModel):
    asset_id: int
    asset_name: str
    asset_ticker: Optional[str]
    asset_type: str
    broker_id: int
    broker_name: str
    period_unrealized_delta: Optional[SafeDecimal]  # Δ(unrealized GL) start → end
    period_realized_gain_loss: Optional[SafeDecimal] # realized from SELLs in period
    period_income: Optional[SafeDecimal]             # DIVIDEND/INTEREST attributed to asset
    period_fees_taxes: Optional[SafeDecimal]         # FEE/TAX attributed to asset (positive value)
    period_pnl: Optional[SafeDecimal]                # = unrealized_delta + realized + income - fees_taxes
    period_pnl_percent: Optional[SafeDecimal]        # period return % for the asset (optional)
```

New endpoint needed:
```
POST /api/v1/portfolio/positions-contribution
body: { broker_ids, date_range, target_currency }
response: list[AssetPeriodContribution]
```

**Engineering challenge**: Fees/taxes as separate transactions are NOT linked to a specific asset (no `asset_id`). Only SELL/BUY/DIVIDEND/INTEREST have asset_id. FEE/TAX rows have `broker_id` but no `asset_id`. These must be allocated to a "Portfolio / Unallocated" bucket in the contribution view.

**No API sync needed** for the current Phase A (RecentTransactions fix only touches frontend). API sync required when adding broker_id to PortfolioHolding.

---

## 4. Data Semantics Validation

### 4.1 Exposure view

**Formula target:**
```
asset_weight = asset_market_value / NAV
```

**Current backend field:**
```python
allocation_percent = current_value / Σ(current_value for all holdings)  # excludes cash
```

**Semantic gap**: If portfolio = €30k assets + €10k cash → NAV = €40k. An asset at €6k gives:
- Correct (plan): 6k/40k = 15%
- Current `allocation_percent`: 6k/30k = 20%

**Recommendation**: DO NOT use `allocation_percent` for the Exposure weight column. Compute in frontend:
```ts
const navWeight = (holding.current_value / parseFloat(summary.net_worth.amount)) * 100;
```

`summary.net_worth.amount` = market_value + cash_total + in_transit = correct NAV denominator.

**P&L total in Exposure view:**
- `PortfolioHolding.gain_loss` = `current_value - wac_per_unit * quantity` = **total unrealized since inception at current end-date**
- This is correct for "P&L totale" semantic: how much has this position gained from its cost basis today?
- Important: it does NOT represent P&L from the selected start date — it's always relative to cost basis (WAC).
- UI label must say "P&L totale" or "Total P&L (vs cost)" to avoid confusion with period metrics.

### 4.2 Contribution view

**Formula target:**
```
asset_period_pnl = unrealized_delta + realized + income - fees_taxes
```

**Unrealized delta per asset**: `(current_price - prev_period_price) × current_qty + settlement effects`. NOT simply `current_gain_loss - start_gain_loss` because qty may have changed. Requires engine support.

**Realized gain/loss per asset**: Portfolio service already accumulates `_realized_accum` across all assets, but NOT per-asset. Would need to refactor inner loop to build `per_asset_realized: dict[(broker_id, asset_id), Decimal]`.

**Income per asset**: DIVIDEND/INTEREST transactions have `asset_id`. Can be grouped per (broker, asset) for the period. Feasible.

**Fees/taxes per asset**: FEE/TAX transactions typically have `asset_id = None`. Must be bucketed as "Portfolio-level" unallocated. This means `asset_period_pnl` for standard positions excludes portfolio fees, and a synthetic "Unallocated" row shows portfolio-level fees.

**Var. % (period return %)**: Plan says "rendimento posizione nel periodo, not semplice variazione prezzo". True asset-level TWRR is expensive (requires WAC series + price history for the period, per asset). Simplified proxy: `period_pnl / start_cost_basis` — simpler but semantically approximate.

### 4.3 P&L total vs P&L period

| Metric | Source | Meaning | When to use |
|--------|--------|---------|-------------|
| `gain_loss` (PortfolioHolding) | `current_value - wac×qty` | Total unrealized from cost basis — snapshot at end date | Esposizione view "P&L tot" |
| `period_pnl` (PortfolioSummary) | `nav_end - nav_start - net_flows` | Full period result (unrealized delta + realized + income - fees) | Portfolio-level KPI card |
| `asset_period_pnl` (NOT YET) | per-asset attribution | Which asset drove the period result | Contributo view |

**Risk**: the word "P&L" used in both total and period contexts. The UI must label explicitly:
- Esposizione: "P&L totale" or "Gain/Loss (tot.)"
- Contributo: "P&L periodo" or "Period contribution"

### 4.4 Edge cases

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Cash-only asset | `current_price = None`, `gain_loss = None` | Show "—" in P&L col; exclude from treemap (area = 0 still valid for cash weight) |
| Manual asset (no price source) | `current_price = None` → `current_value = None`, `allocation_percent = None` | Exclude from treemap; show "—" in value col; add to DataQuality banner |
| Crowdfund without live price | Same as manual — transaction-implied price used | TRANSACTION_IMPLIED flag in DataQualityReport — show warning |
| Missing broker | `broker_id = None` after DTO fix | Group in "Unknown Broker" in treemap hierarchy |
| Missing P&L attribution (fees not linked to asset) | Portfolio-level fees absent from per-asset total | Show "Portfolio" row in Contributo table for unallocated fees |
| Zero NAV | `net_worth.amount = 0` → division by zero for weight | Guard: if NAV == 0, show "—" for all weights |
| All gains / no losses | Contribution treemap: only GAINS section rendered; LOSSES section empty/hidden | Detect: if `gross_losses == 0`, hide LOSSES treemap; show "No losses" message |
| All losses / no gains | Contribution treemap: only LOSSES section; GAINS empty | Same logic: hide GAINS treemap if `gross_gains == 0` |
| No transactions in period | `period_pnl = 0`, all attribution = 0 | Show empty state: "No P&L in selected period" — already designed in plan |
| Same asset in multiple brokers | Two PortfolioHolding rows with same asset_id, different broker_id | After broker_id fix: both rows shown separately. Treemap: separate leaves under different broker nodes |

---

## 5. Treemap Feasibility

### 5.1 Exposure treemap

**Data structure needed:**
```ts
interface TreemapNode {
  name: string;
  value: number;      // market_value in base currency
  children?: TreemapNode[];
  // Extra for tooltip:
  navWeight?: number;
  pnlTotal?: number;
  pnlPercent?: number;
  brokerName?: string;
  assetType?: string;
}
// Hierarchy: Broker → AssetType → Asset
```

**Requires**: `broker_id` + `broker_name` in PortfolioHolding (backend gap).

**ECharts treemap configuration**:
```ts
{
  type: 'treemap',
  data: [/* Broker nodes with children */],
  label: { show: true },
  upperLabel: { show: true },  // Shows broker/type labels on parent nodes
  leafDepth: 1,                // Drill-down support optional
  breadcrumb: { show: false }, // Minimal UI for dashboard compact view
}
```

**Feasibility**: HIGH — standard ECharts treemap. Reuses existing tooltip/dark mode infrastructure.

### 5.2 Contribution double treemap

**Two separate chart instances** (simpler than two series in one instance):
- `ContributionGainsTreemap` — shows only assets with `period_pnl > 0`
- `ContributionLossesTreemap` — shows only assets with `period_pnl < 0`

Each has its own ECharts instance, but area sizing must reflect the shared scale:
- GAINS treemap: container height proportional to `gross_gains / scale_max`
- LOSSES treemap: container height proportional to `gross_losses / scale_max`

**Within each treemap**: hierarchy = Broker → AssetType → Asset, area = `|period_pnl|`.

**Feasibility**: MEDIUM — requires new `PositionsPeriodPnl` DTO first (high backend effort). The chart itself is feasible with ECharts treemap.

### 5.3 Scaling logic

```ts
const gross_gains = assets.filter(a => a.period_pnl > 0).reduce((s, a) => s + a.period_pnl, 0);
const gross_losses = assets.filter(a => a.period_pnl < 0).reduce((s, a) => s + Math.abs(a.period_pnl), 0);
const scale_max = Math.max(gross_gains, gross_losses);

// Container height split (e.g. total available = 400px):
const gainsHeightPct = gross_gains / scale_max;   // 0–1
const lossesHeightPct = gross_losses / scale_max; // 0–1

// UI label (required per plan): "Shared scale: 100% = max(gains, losses)"
```

**Division by zero guard**: if `scale_max === 0` → show empty state "No P&L in period".

### 5.4 Tooltip/data needs

**Exposure treemap tooltip** (per plan):
```
VWCE
Broker: Directa
Tipo: ETF
Valore: €12.450
Peso NAV: 18,2%
P&L totale: +€840
```

**Contribution treemap tooltip**:
```
VWCE
Broker: Directa
Tipo: ETF
P&L periodo: +€840
Var. %: +3,8%
Impatto: Gain #1
Scala: 66.7% of scale_max
```

Both can use `buildTooltipTheme` + `buildTooltipRow` from `echartsTooltipHelpers.ts`.

---

## 6. Recent Transactions Feasibility

### 6.1 Column filtering

`RecentTransactionsPanel.svelte` has hardcoded columns. The target column set (Date | Type | Asset | Broker | Qty | Amount) differs from current (Date | Type | Asset | Broker | Amount+Qty-sub-row). Changes needed:

1. Split the last `<td>` (which contains Amount + Qty sub-row) into two separate `<td>` columns
2. Add a `Qty` `<th>` header column
3. Move `quantityLabel` output to its own `<td>`

No column visibility toggle needed for home view — columns are fixed.

### 6.2 Qty vs Amount handling

**Current** (line 221-226 `RecentTransactionsPanel.svelte`):
```html
<td>
  <div class="text-gray-700">{formatAmount(tx)}</div>  <!-- Amount -->
  {#if qtyLabel}
    <div class="text-[10px] {quantityClass(tx)}">{qtyLabel}</div>  <!-- qty sub-row with colors -->
  {/if}
</td>
```

**Target** (per plan — Qty = separate column, neutral color):
```html
<td class="text-gray-500 whitespace-nowrap">          <!-- Qty column -->
  {quantityLabel(tx) ?? '—'}                           <!-- neutral color (remove quantityClass) -->
</td>
<td class="text-right font-medium whitespace-nowrap"> <!-- Amount column -->
  {formatAmount(tx)}
</td>
```

Also: the Type column currently shows only an icon (no text label). Plan shows "Tipo" with text. Decision: icon-only is acceptable for compact home view (saves horizontal space); text label is available as `tx.type` if needed.

### 6.3 Mobile behavior

`overflow-x-auto` is already present on the table wrapper → horizontal scroll on mobile works. Plan confirms: "no layout forzato a card, mantieni tabella scrollabile." ✅ No changes needed for mobile layout.

The 6-column layout (Date | Type | Asset | Broker | Qty | Amount) is wider than current 5-column → more horizontal scroll on mobile. Acceptable per plan.

### 6.4 Row interaction

**Double-click (desktop):**
`RecentTransactionsPanel.svelte` uses plain `<tr>` elements. Add `ondblclick`:
```svelte
<tr ondblclick={() => onViewRow?.(tx)}>
```
Add `onViewRow?: (tx: ApiTXRow) => void` prop. Parent (dashboard page) navigates to `/transactions?id={tx.id}` or opens a view modal.

**Long-press (mobile):**
DataTable implements 500ms long-press via `touchstart`/`touchend` handlers (line 231 in DataTable.svelte). This is for selection toggle, not view. Need to add separate long-press handler in `RecentTransactionsPanel.svelte` — ~20 lines of `touchstart`/`touchend` logic. Can extract a `useLongPress` action utility if pattern will be reused.

**Context menu**: Plan says "no context menu in home" for mobile. Use long-press → immediate view, skip menu. For desktop, double-click is sufficient; no right-click menu needed in home.

---

## 7. Proposed Implementation Plan

> **DO NOT IMPLEMENT** — analysis only.

### Phase A — Esposizione + Recent Transactions (no new backend endpoints)

**Step A1: Backend — add broker_id to PortfolioHolding**
- `backend/app/schemas/portfolio.py`: add `broker_id: Optional[int]`, `broker_name: Optional[str]` to `PortfolioHolding`
- `backend/app/services/portfolio_service.py`: pass `broker_id=broker_id, broker_name=broker_name` in `all_holdings.append(PortfolioHolding(...))`  
- Run `./dev.py api sync` → regenerates TypeScript client

**Step A2: Frontend — extract shared cell components**
- Create `frontend/src/lib/components/dashboard/cells/AssetIdentityCell.svelte`
- Create `frontend/src/lib/components/dashboard/cells/AssetTypeBadge.svelte`
- Create `frontend/src/lib/components/dashboard/cells/BrokerBadge.svelte`
- Create `frontend/src/lib/components/dashboard/cells/MoneyCell.svelte`
- Create `frontend/src/lib/components/dashboard/cells/PercentCell.svelte`
- Create `frontend/src/lib/components/dashboard/cells/PnlCell.svelte`

**Step A3: Frontend — create PositionsPanel.svelte (Esposizione only)**
- Replaces `HoldingsPanel.svelte` (or keeps as fallback)
- Toggle Esposizione/Contributo (Contributo disabled/coming-soon in Phase A)
- Toggle Tabella/Mappa
- Esposizione/Tabella view: Asset | Type | Broker | Value | NAV Weight | P&L total
- Esposizione/Mappa view: placeholder "Coming soon" or treemap

**Step A4: Frontend — create ExposureTreemap.svelte**
- ECharts `treemap` type
- Hierarchy: Broker → AssetType → Asset
- Area = `current_value`, weight label = NAV weight
- Color = P&L sign (green/red gradient by `gain_loss_percent`)
- Tooltip using `echartsTooltipHelpers.ts`
- Dark mode + ResizeObserver pattern

**Step A5: Frontend — fix RecentTransactionsPanel.svelte**
- Split Qty sub-row into separate column
- Remove `quantityClass` (neutral gray color for Qty)
- Add `onViewRow?: (tx) => void` prop
- Add `ondblclick` on `<tr>`
- Add long-press touch handler (~20 lines)

**Step A6: i18n — add Esposizione/Tabella/Mappa/Weight keys**
- `dashboard.positions` = "Your Positions"  
- `dashboard.exposure` = "Exposure"
- `dashboard.viewTable` = "Table"
- `dashboard.viewMap` = "Map"
- `dashboard.weight` = "Weight"
- `dashboard.qty` = "Qty"
- (in all 4 language files)

**Step A7: Wire in dashboard +page.svelte**
- Replace `<HoldingsPanel>` with `<PositionsPanel>`
- Pass `holdings={summary?.holdings ?? []}`, `nav={summary?.net_worth}`, `loading={summaryLoading}`
- Update `<RecentTransactionsPanel>` to pass `onViewRow` callback + navigate

---

### Phase B — Contributo view (requires new backend)

**Step B1: Backend — per-asset P&L attribution engine**
- New `portfolio_service.py` method: `get_positions_contribution(user_id, broker_ids, date_range, target_currency)`
- Compute per-(broker_id, asset_id): `unrealized_delta`, `realized`, `income`, `fees_taxes`, `period_pnl`
- Fees/taxes not linked to asset → bucket as `asset_id=None` "Portfolio" row
- New schema: `AssetPeriodContribution`, response `list[AssetPeriodContribution]`
- New endpoint: `POST /api/v1/portfolio/positions-contribution`
- Run `./dev.py api sync`

**Step B2: Backend — extend portfolioStore to fetch contribution data**
- Add `fetchContribution(brokerIds, dateFrom, dateTo, targetCurrency)` to portfolioStore
- Cache alongside report cache (same invalidation)

**Step B3: Frontend — Contributo/Tabella view in PositionsPanel**
- On tab switch to Contributo: fetch contribution data
- Table: Asset | Type | Broker | P&L periodo | Var. % | Impatto
- Sort by `|period_pnl|` descending
- "Impatto" = rank label: "Gain #1", "Loss #1" etc.

**Step B4: Frontend — ContributionTreemap.svelte**
- Two ECharts treemap instances (stacked vertically)
- Container heights proportional to `gross_gains / scale_max` and `gross_losses / scale_max`
- Scale label: "Shared scale: 100% = max(gains, losses)"
- Empty state when `scale_max === 0`
- Conditional rendering when only gains or only losses

**Step B5: i18n — add Contributo/PnL/Impact keys**
- `dashboard.contribution` = "Contribution"
- `dashboard.impact` = "Impact"
- `dashboard.periodReturn` = "Period return"
- `dashboard.sharedScaleLabel` = "Shared scale: 100% = {max}"
- Empty state keys

---

## 8. Open Questions for Copilot/User

1. **Broker-per-holding in Exposure table**: If an asset is held in multiple brokers (e.g., VWCE at both Directa and IBKR), should the Exposure table show **two separate rows** (one per broker) or **one merged row** (sum of values, broker column = "Multiple")? The treemap always shows separate nodes. Recommended: separate rows (more information-rich; user can "See all →" for merged view).

2. **`allocation_percent` vs computed NAV weight**: The fix (compute `current_value / NAV` in frontend) requires the frontend to know whether `current_value` is already in the display currency or in the base currency. Currently `current_value` is in `base_currency`. If user switches to a different display currency (override), the values are fetched in the override currency. Confirm: does `PortfolioHolding.current_value` always match the currency of `PortfolioSummary.net_worth`? _(Expected: yes, both use the same `base_currency`/`target_currency_override` from the same engine run.)_

3. **Var. % for Contributo**: The plan says "rendimento posizione nel periodo, not semplice variazione prezzo". Full asset-level TWRR is expensive. Acceptable simplified proxy: `period_pnl / |start_cost_basis_or_start_value|`. Confirm acceptable semantics before implementation to avoid user surprise.

4. **Phase A: PositionsPanel replaces HoldingsPanel or extends it?** The simplest approach is to extend `HoldingsPanel.svelte` in-place (add toggles, broker column). Cleaner approach is a new `PositionsPanel.svelte` that deprecates HoldingsPanel. Recommend: new component (cleaner separation), but keep HoldingsPanel as alias until full dashboard rewrite is done.

5. **Mobile treemap**: On very small screens, the Esposizione treemap with Broker → AssetType → Asset 3-level hierarchy will have many tiny nodes. Should mobile treemap show a simpler 2-level hierarchy (AssetType → Asset only), or reduce to top-N assets with "Other"? The plan does not specify.

---

## Commands Executed

```bash
# File exploration
find /path -name "portfolio*" 
find /path -name "+page.svelte"
ls frontend/src/lib/components/{assets,transactions,dashboard,charts,table}/
ls frontend/src/lib/{stores,utils,i18n}/

# Targeted reads
view plan_ui_dashboard.md (multiple view_range calls)
view HoldingsPanel.svelte        # 147 lines
view RecentTransactionsPanel.svelte  # 234 lines
view TransactionsTable.svelte    # lines 1–200 (54KB total)
view AssetTable.svelte           # lines 1–150
view DataTable.svelte            # lines 1–160
view portfolio_api.py            # 311 lines
view portfolio.py (schemas)      # 380 lines
view echartsTooltipHelpers.ts    # 285 lines
view AllocationPieChart.svelte   # lines 1–80
view LineChart.svelte            # lines 1–80
view dashboard/+page.svelte      # lines 1–300

# Grep searches
grep "PortfolioHolding|holdings|allocation_percent" portfolio_service.py
grep "HoldingsPanel|RecentTransactions" dashboard/+page.svelte
grep "long.press|contextmenu|500ms" DataTable.svelte
grep "quantityClass|quantityLabel" RecentTransactionsPanel.svelte
grep "getAssetTypeIconUrl|formatCurrencyAmount|getStringBadgeStyle" utils/*.ts

# i18n queries
python3 -c 'json.load → search dashboard.* and common.* keys' en.json

# Backend analysis
sed -n '785,830p' portfolio_service.py   # holdings loop / allocation_percent
sed -n '835,845p' portfolio_service.py   # allocation_percent calculation basis
```

---

*End of report.*
