# 📊 Lots Analysis Service

`backend/app/services/lots_analysis_service.py` is the orchestration layer behind `POST /portfolio/lots/analysis`.

It runs `FifoLotEngine` once, then converts engine output into `LotsAnalysisResponse`: FX-normalized values, qbq-aware valuations from the unified price resolver, lot/event histories, WAC series, income allocation, and fallback valuation for assets without usable marks. Frontend consumer: `LotsAnalysisPanel.svelte`.

---

## 🔌 API Contract

### 🛣️ Endpoint

```text
POST /portfolio/lots/analysis
```

Router entrypoint:

```python
@portfolio_router.post("/lots/analysis", response_model=LotsAnalysisResponse)
async def get_lots_analysis(body: LotsAnalysisQuery, ...):
    ...
    return await service.get_lots_analysis(
        user_id=current_user.id,
        asset_id=body.asset_id,
        broker_ids=body.broker_ids,
        date_from=date_from,
        date_to=date_to,
        target_currency=body.target_currency,
        selected_lot_ids=body.selected_lot_ids,
        requested_analyses=body.requested_analyses,
    )
```

If `date_range` contains min/max sentinels, router resolves them before calling service.

### 🧾 Request Body — `LotsAnalysisQuery`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `asset_id` | `int` | Yes | Asset to analyze |
| `broker_ids` | `list[int] \| None` | No | `None` = all accessible brokers |
| `date_range` | `OpenDateRangeModel \| None` | No | Limits emitted histories/visible intervals, not engine starting state |
| `target_currency` | `str \| None` | No | Defaults to global base currency |
| `selected_lot_ids` | `list[int] \| None` | No | Lot subset for lot-scoped analyses |
| `requested_analyses` | `list[LotAnalysisType]` | Yes | Non-empty, duplicates rejected |

### 🧩 `LotAnalysisType`

| Enum member | Response field | Meaning |
|-------------|----------------|---------|
| `LOT_SUMMARY` | `lots` | One row per lot with scalar metrics, states, custody, current valuation |
| `GANTT_TOPOLOGY` | `gantt_segments` | Custody fragments for Gantt lanes |
| `CUSTODY_HISTORY` | `custody_history` | Custody-only event subset |
| `EVENT_HISTORY` | `lot_events` | Full lot chronology: openings, splits, transfers, closures |
| `VALUE_HISTORY` | `value_history` | Per-lot `open_value`, `proceeds`, `total_value`, `pnl`, `income` |
| `RETURN_HISTORY` | `return_history` | Per-lot `total_return`, `relative_return`, `income` |
| `PRICE_HISTORY` | `price_history` | Per-lot market-price series |
| `BROKER_WAC_HISTORY` | `broker_wac_history` | Broker-scoped WAC time series |
| `CUMULATIVE_WAC_HISTORY` | `cumulative_wac_history` | Combined WAC time series |
| `PERFORMANCE_HISTORY` | `performance_history` | Asset-wide ROI/TWRR, ignores lot selection |
| `INCOME_EVENTS` | `income_events` | Dividend/interest markers allocated to open LONG lots |

### 📦 Response Shape — `LotsAnalysisResponse`

Top-level fields always present:

| Field | Meaning |
|-------|---------|
| `asset_id` | Requested asset |
| `target_currency` | Final response currency |
| `quote_base_quantity` | Asset qbq, needed by frontend price/WAC axis |
| `calculation_status` | `COMPLETE`, `DEGRADED`, or `FAILED` (public global status; an empty-but-valid analysis is `COMPLETE`) |
| `calculation_metadata` | Broker scope, selection, requested/computed date bounds, generation date |
| `data_quality` | FIFO/data-quality issues mapped to UI-friendly DTOs |
| `economic_allocation_groups` | 3-level economic audit (income + FEE/TAX) mapped from the engine, `None` unless `LOT_SUMMARY` requested |
| `asset_orphan_income` / `asset_orphan_fees` / `asset_orphan_taxes` | Amounts that belonged to no eligible lot, kept at asset level (never dropped, never double-counted) |

All analysis payload sections are `None` unless explicitly requested.

---

## ⚙️ Processing Pipeline

Service entrypoint:

```python
async def get_lots_analysis(
    self,
    user_id: int,
    asset_id: int,
    broker_ids: list[int] | None,
    date_from: date_type | None,
    date_to: date_type | None,
    target_currency: str | None,
    selected_lot_ids: list[int] | None,
    requested_analyses: list[str | LotAnalysisType],
) -> LotsAnalysisResponse:
```

High-level flow:

1. Load accessible brokers, asset transactions, split ratios, broker shorting flags, `price_history`, asset income transactions.
2. Build `reference_price_lookup()` and run `run_fifo_lot_engine(...)`.
3. Resolve selected lots.
4. Collect needed FX pairs with `_collect_fx_needs()` / `_collect_performance_fx_needs()`, then batch-load rates through `_FxRateResolver`.
5. Extract the engine's **economic stage** outputs — income, FEE/TAX and net metrics — with `_extract_income_outputs()` and `_extract_cost_outputs()` (allocation itself happens inside the engine, not here).
6. Build one qbq-aware resolver series with `build_asset_price_series()`; feed both valuation maps and price-history lines from it.
7. Emit only requested DTO sections.

### 💱 FX Conversion

`_FxRateResolver` is thin prefetch + conversion helper:

- `need(currency, as_of_date)` registers required pairs
- `load(session)` calls `convert_bulk(...)` once
- `convert(amount, currency, as_of_date)` applies date-specific conversion into `target_currency`

Service converts:

- lot opening cost and opening unit price
- closure proceeds / realized P&L
- native resolver marks from `build_asset_price_series()`
- dividend / interest cash flows
- WAC inputs
- performance-history external flows

### ⚠️ qbq Scaling Gotcha

!!! warning "Two price scales coexist"

    `price_history.close` is quoted **per `quote_base_quantity`**.

    `opening_unit_price`, closure unit prices, and WAC values are **per single unit**.

    For bonds this mismatch is dangerous: comparing raw `opening_unit_price` with raw market price mixes
    two scales and historically caused huge fake returns/P&L. Example: a bond can trade near `100`, while
    `opening_unit_price` is near `1` because cost was divided by nominal quantity.

    Service fixes this in two places:

    - **Valuation path**: `_build_lot_summaries()`, `_build_value_history()`, `_build_return_history()`,
      `_build_performance_history()` call `compute_holding_value(..., quote_base_quantity)` so
      `open_value = (qty / qbq) * price`.
    - **Reference-price fallback path**: `_opening_reference_price()` multiplies fallback
      `lot.opening_unit_price * quote_base_quantity` when no market quote exists on opening date.

Exact fallback scaling code:

```python
scale = quote_base_quantity if quote_base_quantity > 0 else 1
return lot.opening_unit_price * scale, lot.currency, lot.opening_date, "exact"
```

That multiplication is **only** for fallback Scenario B. Real market quotes already arrive in per-qbq scale and must **not** be multiplied again.

---

## 🧭 Unified Price Resolver

`LotsAnalysisService` uses `backend/app/services/price_resolver.py` as the single daily mark path:

```python
price_series = build_asset_price_series(
    price_rows=[(row.date, row.close, row.currency) for row in prices],
    transactions=transactions,
    split_linked_tx_ids=set(split_ratios_by_tx_id),
    asset_currency=asset.currency,
    quote_base_quantity=quote_base_quantity,
)
mark = price_series.resolve(current_date)
```

Resolution tiers are owned by `AssetPriceSeries.resolve()`:

| Tier | `MarkSource` | Meaning |
|------|--------------|---------|
| 1 | `MARKET` | Same-day asset-system `price_history.close`. |
| 2 | `TRADE_AVG` | Same-day BUY/SELL or priced ADJUSTMENT-derived average. |
| 3 | `CARRIED` | Last observation carried forward (LOCF), market- or trade-origin. |
| 4 | `MISSING` | No observation on/before the day. |

Marks stay in **native currency** and on the market × `quote_base_quantity` axis. The service converts `mark.unit_price` with `_FxRateResolver.convert(..., current_date)`, so carried foreign marks use FX for the **valuation date**, not the original observation date.

Both internal maps are built from this same resolver:

- `market_prices[date] = target-currency mark or None` feeds lot summaries, value/return history, performance NAV, and transfer valuation.
- `estimated_market_prices[date] = (target-currency mark, mark.estimated)` feeds `PRICE_HISTORY`.

The old duplicate map pattern (`_build_market_price_map` plus `_build_estimated_market_price_map`) is gone in shipped code. There is no separate market-only valuation path to document.

`ResolvedMark.estimated` means **TRADE-origin**, including a trade mark carried forward. A real market quote carried forward is stale (`price_backward_fill`) but not estimated.

---

## 💸 Economic Stage — Income, FEE/TAX & Net Metrics

Since FIFO v5 the **allocation** of asset-linked income (`DIVIDEND` / `INTEREST`) and asset-linked cost
(`FEE` / `TAX`) happens **inside the engine's economic stage** (see
[FIFO Lot Engine](fifo_lot_engine.md)), not in the service. The service only **extracts** the already-computed
per-lot accumulators and audit groups:

- `_extract_income_outputs(engine_result, ...)` reads `engine_result.economic_accumulators_by_lot[*].gross_income`
- `_extract_cost_outputs(engine_result, ...)` reads `.allocated_fees` / `.allocated_taxes`
- `_map_economic_groups(...)` maps the 3-level audit into `economic_allocation_groups`

!!! warning "Allocation rule moved and changed"

    The pre-v5 same-day rule `w_i(t) = OpenQty_i(t) / Σ OpenQty_j(t)` no longer applies. Income eligibility
    is now **D-1** (`OpenQty_i(D-1)`) and **broker-scoped** to the paying broker, and FEE/TAX use a
    deterministic operation-matching ladder. The math lives in the engine; see the theory page
    [FIFO Lot Analysis](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md).

### 📤 Extracted outputs

- `income_by_lot` → scalar cumulative income for `LotSummarySchema.asset_income`
- `income_prefix_by_lot` → per-date cumulative prefixes for value/return histories
- `income_events` → chart markers with source tx and affected lot ids
- `fees_by_lot` / `taxes_by_lot` → scalar `allocated_fees` / `allocated_taxes`, plus per-date prefixes for history

### 🧮 Net metrics (`LotSummarySchema`)

FEE/TAX are stored as **positive magnitudes** already converted to `target_currency`, and net metrics are
derived only when they can be meaningful:

```text
net_total_pnl    = total_pnl - allocated_fees - allocated_taxes          # total_pnl INCLUDES income
net_total_return = net_total_pnl / opening_value       (opening_value > 0)
```

History builders expose their own net lines: `_build_value_history()` emits
`net_pnl = pnl - allocated_fees - allocated_taxes` (**pnl excludes income**), while `_build_return_history()`
emits an income-inclusive `net_total_return`. The asymmetry is intentional — each net line mirrors its gross
counterpart minus costs.

!!! note "`net_metrics_status`"

    Every processed lot is emitted with `net_metrics_status = "AVAILABLE"`. Because a missing FX rate falls
    back to the native amount, the net of an existing lot is always mathematically determined, so no path
    currently emits `"UNAVAILABLE"`.

### 🧺 Orphans & conservation

When income or FEE/TAX has no eligible lot (e.g. a cost after the position is fully closed), the amount is
**not dropped**: it is returned at asset level as `asset_orphan_income` / `asset_orphan_fees` /
`asset_orphan_taxes` and surfaced as a `ASSET_INCOME_NO_ELIGIBLE_LOTS` / `ASSET_COST_NO_ELIGIBLE_LOTS`
data-quality issue. The engine guarantees, per pool, `Σ allocated + orphan == converted pool total`.

!!! info "Costs without an asset"

    `FEE` / `TAX` with `asset_id = null` never enter the FIFO/lots analysis at all — they are handled by the
    Portfolio Engine. Only asset-linked costs can produce allocated net figures here.

---

## 🧮 Estimated-at-Cost Fallback

When no asset-system quote exists (`price_lookup.latest() is None`), service enters `estimated_mode` and emits a `CURRENT_PRICE_ASSUMED_AT_COST` data-quality warning for the analysis window.

If the unified resolver returns `MISSING` for an open LONG lot, the service values the remaining quantity at residual cost:

```python
open_value = (opening_value or Decimal("0")) * lot.open_quantity / lot.original_quantity
value_source = "ESTIMATED_AT_COST"
market_pnl = Decimal("0")
```

Implications:

- `LotSummarySchema.value_source = "ESTIMATED_AT_COST"` only on the true missing-mark fallback branch
- `open_value` still exists for crowdfunding / unquoted assets
- `total_value`, `total_pnl`, `cash_yield`, `total_return` remain usable
- `relative_return` stays `None` because no true market/reference comparison exists
- data quality report adds `CURRENT_PRICE_ASSUMED_AT_COST`

If the resolver can derive a TRADE-origin mark from transactions, `market_prices[date]` is not `None`: valuation uses that mark, while the price-history point carries `estimated=True`. For history builders, the cost fallback appears in `_build_value_history()` and `_build_return_history()` when `market_price is None` but lot is still open.

---

## 🎯 Selection Model

Backend method:

```python
def _resolve_selected_lot_ids(self, selected_lot_ids: list[int] | None, lots_by_id: dict[int, FifoLot]) -> list[int]:
    if selected_lot_ids is None:
        return list(lots_by_id)
    ...
    return list(dict.fromkeys(selected_lot_ids))
```

Meaning at raw API level:

- `selected_lot_ids = None` → all lots in backend scope
- explicit non-empty list → exactly those lots
- explicit unknown ids → `ValueError`

!!! note "Frontend empty-selection convention"

    UI state uses different semantics: empty selection means **all visible lots**, not "none".

    `LotsAnalysisPanel.svelte` implements that by expanding empty UI selection into
    `effectiveSelectionIds = visibleLots.map((lot) => lot.lot_id)` before lot-scoped requests.

    So if you call API directly, send `null`/omit field for "all lots", or send explicit visible IDs
    for "all visible lots after frontend filtering". Do **not** assume raw `[]` automatically means all.

Also note: `PERFORMANCE_HISTORY` ignores lot selection entirely by schema/implementation.

---

## 🕰️ History Builders

Key builders:

- `_build_lot_summaries()` — scalar lot rows for table/modal
- `_build_gantt_segments()` — custody fragments
- `_build_lot_event_rows()` — full lot chronology
- `_build_value_history()` — continues closed lots to `date_to` via `_lot_history_end_date(..., extend_closed=True)`
- `_build_return_history()` — same continuity rule, plus `relative_return`
- `_build_price_history()` — truncates at closure date, no post-close points
- `_build_broker_wac_history()` / `_build_cumulative_wac_history()` — WAC snapshots via `_compute_wac_series()`
- `_build_performance_history()` — asset-wide ROI/TWRR from NAV + external cash flows

Important nuance: `date_from` trims emitted rows only. Engine still starts from earliest in-scope asset transaction so FIFO state stays correct.

---

## 🔗 Related

- 🧠 **[FIFO Lot Engine](fifo_lot_engine.md)** — Pure event-sourced FIFO core
- 📖 **[FIFO Lot Analysis Theory](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)** — Financial interpretation of lot metrics
- 🖥️ **[Lots Analysis Frontend](../../frontend/components/features/lots-analysis.md)** — `LotsAnalysisPanel` and chart/table consumers
