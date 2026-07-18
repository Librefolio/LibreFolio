# FIFO Engine v3 — State Recap (for supervisor)

> Ultra-terse. Substance intact. Snapshot @ 2026-07-18, working tree (uncommitted).
> Scope: FIFO lots analysis backend + frontend. Sibling task in same tree: BRIM FEE/TAX asset-link.
> Companion docs: `highLevel-v3.md` (spec), `implementation-log-v3.md` (waves 0–2 + bugfix round 2).
> This doc adds: bugfix **round 3 + round 4** (undocumented in the log), full math, UI ascii, code-quality audit.

---

## 0. TL;DR

- Backend FIFO lots engine = **feature-complete for v3 scope**. Per-lot metrics (income, market/total P&L, yield, return, value_source) computed, converted to target ccy, tested (16/16 service + 37 API). No FEE/TAX in lots engine yet.
- Frontend lots panel = **4 charts + table + custody modal**, all wired, build-green (`front check` 0/0, `front build` OK). 4 bugfix rounds of manual-review polish applied.
- **Open**: BRIM FEE/TAX→asset link (plugin half done in tree; FIFO cost-basis half NOT built). Chart-code duplication ripe for factoring. Couple latent UX/dead-code items below.

---

## 1. Backend state

### 1.1 Contract (`schemas/portfolio.py:509-544`)

`LotSummarySchema` per-lot fields (all in response target ccy):

```
opening_unit_price   cost basis / share (converted)        original_cost = opening_value
original_quantity    open_quantity      realized_pnl       cumulative_proceeds
open_value           total_value        pnl (=market+realized, NO income)
relative_return (=open_return)          reference_price_source
asset_income   market_pnl   total_pnl   cash_yield   total_return   value_source
```
`value_source ∈ {MARKET_PRICE, ESTIMATED_AT_COST}` (`LotValueSource`).
Chart contracts: `LotValueHistoryPoint{...,income,pnl}`, `LotReturnHistoryPoint{...,income,total_return}`, `LotIncomeEventSchema{type,date,broker_id,transaction_id,amount,lot_ids}`, `LotsAnalysisResponse.income_events`.

### 1.2 Math (exact)

Notation: lot i, open qty `q_i`, latest market price `P`, opening unit price `u_i`, original cost `C_i = u_i·q0_i`.

```
market_pnl_i   = open_value_i − open_cost_basis_i                 (= pnl_i − realized_pnl_i)
                 = 0                              if value_source = ESTIMATED_AT_COST
open_value_i   = q_i · P                          if MARKET_PRICE
                 = q_i · u_i                       if ESTIMATED_AT_COST   (assumed-at-cost)
total_pnl_i    = market_pnl_i + realized_pnl_i + asset_income_i
cash_yield_i   = asset_income_i / C_i             (guard C_i > 0)
total_return_i = total_pnl_i / C_i                (guard C_i > 0)     [summary card]
```

Return-history last point uses a different-looking form (`_build_return_history:1435`):
```
total_return = (total_value + income) / C − 1
```
**These two are algebraically identical**: `total_value − C = market_pnl + realized`, so
`(total_value+income)/C − 1 = (market_pnl+realized+income)/C = total_pnl/C`. ✓ (summary = last history point).

### 1.3 Asset-income allocation (`_allocate_asset_income:906-974`)

DIVIDEND/INTEREST **asset-linked** (has `asset_id`), pro-rata to LONG lots open at `tx.date`:
```
w_{i,t} = q_i(t) / Σ_j q_j(t)          over LONG lots with opening_date ≤ t, q>0
income_{i} = Σ_t convert(amount_t, tx.date) · w_{i,t}
```
Conservation: **running-remainder** — lots sorted by id, last lot absorbs residual → Σ allocations = converted total exactly (no float drift). Income with **no open lot** at t → skipped here → falls to Portfolio Engine as broker-level effect. Cumulative-by-date prefix map feeds value/return histories. One `LotIncomeEventSchema` per tx (for chart markers).

### 1.4 Estimated-at-cost (`_build_lot_summaries:1011-1027`)

`has_market = price_lookup.latest() is not None`. No price → `open_value = q·u`, `market_pnl = 0`, `value_source = ESTIMATED_AT_COST`, DQ issue `CURRENT_PRICE_ASSUMED_AT_COST`. Value/return histories **emit estimated points** instead of skipping (was the old "empty chart" bug). Enables price-less assets (crowdfunding, "Lonate Pozzolo") to render.

### 1.5 What backend does NOT do (open)

- **FEE/TAX never allocated to lots** (`fifo_utils.py` ignores them even when asset known). Cost basis / WAC untouched by fees. This is the FIFO half of the BRIM task — **not built**.
- Unallocated income/costs (no `asset_id`) handled only by **Portfolio Engine** → "Altri effetti del periodo" table (`positions_contribution.{unallocated,other_effects}`), NOT by lots engine. (Interest w/o asset → yes, lands here.)

---

## 2. Frontend state

### 2.1 Component map (`brokers/lots/`)

```
LotsAnalysisPanel.svelte      orchestrator: fetch, selection state, visibleLots, modal wiring
├─ LotWacPriceChart.svelte    "PMC / Prezzo di mercato"  (WAC/market lines + perf BUBBLES + income |)
├─ LotGanttChart.svelte       "Vita e custodia dei lotti" (compact hierarchical Gantt, Aperti|Chiusi)
├─ UnifiedLotsTable.svelte    "Lotti" table (+ aggregate footer, ⋮ actions) on DataTable core
├─ LotComparisonChart.svelte  "Valore dei lotti selezionati" (modes Value/Return/Price + income |)
└─ LotCustodyModal.svelte     per-lot detail modal (all v3 metrics)
lotStateVisual.ts             shared OPEN/PARTIAL/CLOSED → colour+shape (factored helper)
```

### 2.2 Panel ascii (desktop)

```
┌─ Dettaglio Lotti FIFO — 🇪🇺 <asset> ───────────────────────── [↗asset] [✕] ┐
│ [DataQualityBanner: "prezzo stimato al costo" se estimated]                  │
│                                                                              │
│  PMC / Prezzo di mercato            legend: WAC—broker · Market · buys▲ sells▼│
│  price ┤          ╱‾‾‾●(bubble=lot opening, size∝qty, colour=broker)          │
│        │      ╱‾‾‾╱   ┆(dashed connector cost→bubble; green up / red down)    │
│        │  ╱‾‾‾╱      │(income "|" marker teal=div / purple=int @ price height) │
│        └────────────────────────────────────────── time ──                   │
│                                                                              │
│  Vita e custodia dei lotti                        [Aperti|Chiusi] (2 colours) │
│  lot1 ▐███████▓▓▓───┐  (▲buy ▼sell ◆transfer split│ ; thickness=size)         │
│  lot2      ▐████████┘  (child lane forks only at transfer/split date)         │
│  └──── sticky X axis (synced zoom/pan with chart above) ────                  │
│                                                                              │
│  Lotti                                                    4 rows              │
│  Data ap. │ P&L compl. │ Rend.tot │ Valore corr. │ Qtà │ Custodia │ ⋮        │
│  2 gen 26 │ +27,90 €   │ +10.10%  │ 304,20 €     │ 36  │ directa  │ ⋮        │
│  …                                                                 │ ⋮        │
│  Totali   │ +73,49 €   │ +6.24%   │ 1250,60 €    │ 148 │          │  (footer) │
│                                                                              │
│  Valore dei lotti selezionati              [Aggregato|Per lotto] [Val|Rend|Prz]│
│  P&L €┤   ╱‾‾ lot cumulative P&L (each starts at 0)                           │
│      0┼──╱────────── (income "|" on each lot line at div/int date)            │
│       └──────────────────────────── time ──                                  │
└──────────────────────────────────────────────────────────────────────────────┘
      (click bubble/row/table → LotCustodyModal: opening, size, current, P&L,
       market_pnl, asset_income, total_pnl, total_return, cash_yield, value_source)
```

### 2.3 Chart-specific logic (post round-4)

**LotWacPriceChart** (PMC/Prezzo):
- Lines: per-broker WAC, combined WAC (dashed), market price, ROI/TWRR (% mode).
- **Bubbles** (perf overlay, LONG only): ABS `y = opening_unit_price·(1+total_return)`; % `y = total_return·100`. Radius ∝ open_qty (ABS) / original_cost (%). Colour = broker. Centre dot: shape+colour = lot state (sky=open / amber=partial / slate=closed). Dashed connector cost→bubble (green/red/grey by sign).
- **Income "|" markers** (rect 2×16): teal=div / purple=int, at market price (fallback mean `u_i`). ABS mode only.
- Legend: explicit allow-list excludes connectors + centre dots + income markers.

**LotComparisonChart** (Valore lotti), 3 modes:
- **Value**: aggregate stacked area (residual+proceeds) + total + original-cost; per-lot lines = **cumulative FIFO P&L** `point.pnl` (each starts ~0). Same y-scale as aggregate (deferred decision).
- **Return**: per-lot `total_return·100`.
- **Price**: opening-price refs + market + broker WAC.
- Income "|" markers on the relevant line per involved lot (value=pnl height, return=return height; aggregate line if aggregate-only).
- ECharts 6.0.0 workaround: per-lot lines use `trigger:'item'` (axis-trigger bug hides multi-start lines); hidden `axis-trigger-anchor` restores axis tooltip; manual hover-dots overlay + individual tooltip rows.

**LotGanttChart**: compact lanes 30px, segment highlight, hierarchical child lanes fork at transfer/split, sticky X axis, inferred event markers, `filterMode:'none'` (bar clips at range edge, doesn't vanish on zoom past start). `pulseLot(id)` API.

**UnifiedLotsTable** + **DataTable**: no global search; column selector; aggregate footer (sums + weighted avgs, selected-else-visible rows, visible cols only); ⋮ actions column = **DataTable default** now (round 3).

---

## 3. User requests recap (what drove each round)

| Round | User asks (essence) | Delivered |
|------|--------------------|-----------|
| v3 waves 0–2 | full lots panel rebuild per `highLevel-v3.md` §1–18 | backend metrics + 5 fleet frontend (Gantt, bubbles, table, income markers, tx nav) |
| bugfix r2 | ✓ off toggles, phantom 3rd button, return-mode infobox, gantt bar vanish, bubbles→PMC, remove "Altri effetti" from panel, verify per-lot value | 6 aesthetic + 1 math verify (per-lot value **not** a bug: differs by qty only) |
| bugfix r3 | bubble centre dot + open/closed shape, % dashed connectors, closed-lot bubbles, Gantt "Aperti\|Chiusi" 3-way→2-colour, tooltip z-index, per-lot line infobox, kebab as DataTable default | all 6 + kebab default |
| bugfix r4 | (1) open colour green→confusing (2) drop bubble-connectors from PMC legend (3) Amundi lots diff height bug (4) price-less asset (Lonate) needs bubbles (5) per-lot value line → real P&L from 0 (6) dividends purple lines → "\|" markers | **all done this session** ↓ |
| BRIM (parallel) | FEE/TAX not linked to asset in plugins; FIFO should assign costs to open lots when asset known, else Portfolio-Engine generic | plugins half-fixed (see §4); FIFO half NOT started |
| WAC modal (parallel) | responsiveness: desktop↔mobile switch doesn't recompute WAC layout | **not reproducible** via real resize (checkpoint 011) — needs exact repro (device-toolbar vs window) |

### round-4 detail (this session)
- **#1** `lotStateVisual.ts:22` OPEN emerald→sky `#38bdf8`/`#0284c7` (propagates to dot + Gantt button).
- **#2** PMC legend allow-list excludes `lot-bubble-connector-*`, `lot-performance-bubble-centers`, `lot-income-markers`.
- **#3+#6** ABS bubble base market-price→**`opening_unit_price`**. Root cause of Amundi: base was market-close-at-open but `total_return` is cost-basis-relative → mismatch. New base collapses same-asset no-distribution lots to current unit price (equal height) **and** lets price-less assets render. Verified numerically (`/tmp` check: 3 lots same price → all = P_now; old formula → differ).
- **#5** per-lot value line `point.totalValue`→`point.pnl`; tooltip/hover-dots/label updated; reuse i18n `brokers.lots.fifoPnl`.
- **#7** income markLine→"|" scatter in both charts.

---

## 4. Sibling task in tree — BRIM FEE/TAX (partial)

Plugins modified (uncommitted): `broker_directa/finpension/revolut/schwab.py` — link FEE/TAX to asset **when ISIN/ticker present on the row**, never force placeholder for account-level rows (Bollo/generic commissions). Pattern (directa):
```python
asset_optional = tx_type in [TransactionType.FEE, TransactionType.TAX]
if asset_required or (asset_optional and (isin or ticker)):
    ...
```
**Missing**: etoro/freetrade/trading212 (per prior audit, 6/11 plugins had the gap; ibkr/coinbase/degiro/generic_csv already correct). **FIFO cost-basis half unbuilt** — engine still ignores FEE/TAX for lot cost even when asset-linked.

---

## 5. Code-quality audit (for next-step decision)

### 5.1 Duplication — ripe to factor (LOW risk, HIGH value)
Chart income-marker stack is **copy-pasted** across `LotWacPriceChart` + `LotComparisonChart`:
- `incomeEventColor()`, `incomeEventTypeLabel()`, `buildIncomeEventTooltip()`, `LOT_INCOME_MARKER_SERIES_ID`, `buildIncomeMarker*()`, legend-exclusion filter.
→ Extract `lotIncomeMarkers.ts` (colour/label/tooltip/series-builder) + a `collectLegendNames(series, exclude[])` util. `lotStateVisual.ts` already proves the pattern works. Est. ~150 LOC dedup.
Also duplicated: tooltip theme/row/header/divider builders (likely already in a shared util — verify import vs re-decl), `parseNumber`, date sort helpers.

### 5.2 Dead / latent
- **Dead**: `LotWacPriceChart` `LotBubblePoint.priceAtOpening` + its `priceLookupPoints` lookup now unused for bubble base (kept only for income-marker fallback path — `priceAtOpening` field itself is write-only). Remove field, keep `priceLookupPoints`.
- **Behaviour change (flag)**: PMC income markers now **ABS-mode only** (old dashed line showed in % too). Intentional ("altezza del prezzo" undefined in %). Confirm acceptable.
- **UX latent (deferred by user)**: per-lot P&L lines (~±tens €) share y-axis with aggregate value area (~hundreds €) → squashed. User said "same scale for now, decide later". Candidate: 2nd y-axis or split Value vs P&L into its own mode.
- **Formula in 2 places**: `total_return` summary (`:1041`) vs return-history (`:1435`). Algebraically equal (proof §1.2) but **drift risk** — consider one helper.
- **i18n prettier trap**: JSON at `tabWidth:4` in repo config would rewrite the 2-space files; `.prettierignore` does NOT exclude them yet → **add them** to avoid a future accidental full-file churn.

### 5.3 Working tree hygiene
Tree is a **multi-task mix** (fifo v3 r3+r4, BRIM FEE/TAX, DataTable kebab, gallery timing, tx modals, tooltip component, i18n). Recommend **split into ≥3 commits** before merge (see commit-msg suggestion). Stray untracked: `idee_per_grafici.md`, dupe report dir `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v3/` (mirror of this corpus dir — dedup or gitignore).

---

## 6. Suggested next steps (supervisor to pick)

1. **BRIM FEE/TAX — finish**: (a) remaining plugins (etoro/freetrade/trading212); (b) **FIFO engine**: when FEE/TAX asset-linked, fold into lot cost basis on arrival; else leave to Portfolio Engine as generic. Needs product decision (does a fee raise cost basis / lower proceeds?) + tests.
2. **Factor chart income-markers** → `lotIncomeMarkers.ts` (§5.1). Cheap, reduces r5+ maintenance.
3. **Decide P&L-line scale** (§5.2) — 2nd axis vs dedicated mode.
4. **Remove dead `priceAtOpening`** + add i18n JSON to `.prettierignore`.
5. **WAC modal responsiveness** — get exact repro from user or close as non-repro.
