# AI Portfolio Export — MVP Report

## 1. Overview

Frontend-only feature: two clipboard actions on the dashboard (`Copy full AI prompt`,
`Copy portfolio data only`) that build a structured Markdown+YAML export from the
existing portfolio report API and frontend-computed technical signals (EMA/RSI/MACD),
for use with an external AI advisor during the monthly PAC review.

No backend changes. No new endpoints. No API sync performed (frontend-only work).

## 2. Files

```
frontend/src/lib/features/ai-export/
├── types.ts                          # AiPortfolioExport + all sub-types
├── aiExportBuilder.ts                # Orchestrator: report API + assetStore + signals → export
├── aiPromptRenderer.ts               # Full AI Prompt → Markdown+YAML
├── aiDataRenderer.ts                 # Data Only → Markdown+YAML
├── aiExportClipboard.ts              # builder → renderer → clipboard + toast
├── allocationCompaction.ts           # Geography/sector long-tail compaction (ISO3→continent)
├── technical/
│   ├── technicalExportBuilder.ts     # EMA20/50/200, RSI14, MACD per asset
│   ├── signalCrossDetection.ts       # Generic cross detection (series vs series/threshold)
│   ├── technicalSampling.ts          # Last 7 daily + preceding weekly (3M window)
│   └── technicalEvents.ts            # Cross → semantic events, noise reduction
└── templates/
    ├── promptTemplate.ts             # English prompt sections
    └── languageMap.ts                # locale → response language name

frontend/src/routes/(app)/dashboard/+page.svelte   # Brain icon button + dropdown
frontend/src/lib/i18n/{en,it,fr,es}.json           # dashboard.aiExport* keys
```

## 3. Allocation basis (final)

```yaml
allocation_basis: nav_including_cash
allocation_basis_exceptions:
  by_geography: "invested_market_value_excluding_cash_rescaled_to_100 — backend does not classify cash geographically, so country/continent percentages are rescaled to sum to ~100% of invested market value only (excluding cash), not of NAV like the other allocation sections"
```

Most allocation sections are computed on a NAV-including-cash basis so they sum to
~100% of NAV (small residual gaps are captured explicitly, never silently dropped):

| Section | Cash included | Sums to ~100% of | Source |
|---|---|---|---|
| `by_asset_type` | ✅ (backend emits `Liquidity` bucket) | NAV | `summary.allocation_by_type` |
| `by_sector` | ✅ (backend emits `Liquidity` bucket) | NAV | `summary.allocation_by_sector` |
| `by_geography` | ❌ **exception** — backend has no cash geography | invested market value **excluding cash** | `summary.allocation_by_geography` |
| `by_currency` | ✅ — added from `summary.cash_balances` | NAV | frontend-computed |
| `by_broker` | ✅ — added from `summary.by_broker[].cash_total` | NAV | frontend-computed |
| `by_asset` | ✅ — single `Cash / Liquidity` line added | NAV | frontend-computed |

**Root cause fixed (round 5)**: an earlier iteration added a `Liquidity` line to
`by_geography` using the NAV-based cash percentage, while the country percentages
underneath were already summing to ~100% of *market value only* (backend `by_geo`
denominator excludes cash — see `portfolio_engine.py`: `"4h. Allocation: cash as
Liquidity (type + sector, not geography)"`, unlike `by_type`/`by_sector` which fold
cash into their own `Liquidity` bucket before normalizing). Adding NAV-based cash on
top of an already-complete market-value-based 100% pushed the section to ~101%, and
`ensureAllocSums100()` then emitted a negative `Other / Unallocated` residual to force
the sum back to 100 — an invalid, confusing value.

**Fix (round 5)**: `by_geography` is no longer rescaled and no `Liquidity` line is
added to it — countries are exported exactly as returned by the backend.

**Definition correction (round 7)**: the round-5 wording — *"percentages are not
rescaled to NAV and do not sum to 100%"* — was itself inaccurate and confusing.
`by_geography` percentages **do** sum to ~100%, just of a smaller base (invested
market value excluding cash) than the other sections (NAV including cash). The
corrected `allocation_basis_exceptions.by_geography` text now states this precisely:
the section is rescaled to ~100% of invested market value only, not of NAV.
Practical effect: a country line in `by_geography` reads slightly *higher* than the
same country's share of full NAV would be, proportional to the cash percentage
(e.g. if cash is ~1% of NAV, geography percentages are inflated by a factor of
roughly `1 / (1 - cash_pct)` relative to a NAV-basis figure).

`ensureAllocSums100()` still guards against emitting negative residuals: if a
section exceeds 100% by more than the 0.5pp tolerance, the excess is logged as a
console warning and silently omitted rather than exported as a negative bucket.

## 4. Geography / sector compaction (long-tail reduction)

Long lists of sub-1% countries or sectors reduce signal-to-noise for the LLM. Applied
via `allocationCompaction.ts` (frontend-only, static ISO3→continent lookup table —
no backend/API changes):

```yaml
allocation_compaction_policy:
  geography:
    country_threshold_percent: 1
    below_threshold_grouping: continent
    keep_unknown_separate: true
    includes_liquidity: false
  sector:
    sector_threshold_percent: 1
    below_threshold_grouping: minor_sectors
    keep_unknown_separate: true
    includes_liquidity: true
```

Rules:
- **Geography**: countries ≥ 1% kept individually (ISO3 code, e.g. `ITA`, `USA`).
  Countries < 1% are grouped by continent into `Europe minor countries`,
  `Asia-Pacific minor countries`, `North America minor countries`,
  `South America minor countries`, `Africa minor countries`. Codes without a
  continent mapping fall into `Other minor countries`. `Liquidity` is not part of
  this section at all (see §3 basis exception above).
- **Sector**: sectors ≥ 1% kept individually; sectors < 1% are merged into a single
  `Minor sectors` bucket (no per-sector breakdown retained, to keep the export compact).
  `Liquidity` (from the backend) is kept as its own line, never merged.
- **`Unknown`** is never merged into a minor bucket in either dimension, regardless of
  its weight — it stays a meaningful standalone signal for the AI.
- Declared in `methodology.allocation_compaction_policy` so the AI knows small
  exposures may be aggregated (also referenced in the Requested Analysis text).

**Example output** (geography, compacted, sums to ~100% of market_value — cash excluded):
```yaml
by_geography:
  - name: ITA
    percent: 55.64
  - name: USA
    percent: 19.80
  - name: CHN
    percent: 5.54
  - name: Unknown
    percent: 3.62
  - name: Europe minor countries
    percent: 4.03
  - name: Asia-Pacific minor countries
    percent: 6.58
```

- `by_asset`, `by_asset_type`, `by_currency`, `by_broker` are **not** compacted —
  left complete for now (asset-level detail is needed for PAC decisions; type/currency/
  broker lists are already short).


## 5. Section order (final)

Both the full prompt and the data-only export follow the same order:

```text
1. Header instructions (full prompt only — role, web research note)
2. Methodology (incl. technical_context_policy, allocation_basis, metric_definitions)
3. Export Metadata
4. Portfolio Snapshot
5. Current Allocation
6. Positions
7. Broker Summary
8. PAC Context
9. Investor Assumptions
10. Technical Summary
11. Technical Series Detail
12. Technical Events
13. Technical Context Unavailable
14. Data Quality Notes (only if issues present)
15. Requested Analysis (full prompt only)
```

**Gap fixed**: the data-only export previously omitted `methodology` entirely — it now
includes it (needed to correctly interpret `wac_policy`, `valuation_policy`, and
`allocation_basis` without the accompanying prompt text).

## 6. Fields deliberately NOT included

- **`valuation_source`** — explicitly excluded per product decision. The exported
  value is already LibreFolio's best available estimate; the AI advisor is not meant
  to reason about valuation provenance, only about data-quality flags already
  surfaced separately (`missing_price_assets`, `stale_prices`).
- **`target_allocation`** — not modeled anywhere in the app; exposed only as
  `investor_assumptions.target_allocation: unavailable`.
- **Detailed investor profile** (risk tolerance, horizon, income, age) — no source of
  truth exists. Exposed as a minimal `investor_assumptions` block with `unavailable`
  values, plus an explicit prompt instruction not to assume these.
- **Closed positions** (quantity ≈ 0) — omitted entirely from `positions` and from all
  allocation sections; they add no value to forward-looking PAC allocation advice.

## 7. Technical context policy

Declared explicitly in `methodology.technical_context_policy` so the AI does not
conflate the portfolio's selected date range (which can be YTD/1Y/custom) with the
technical indicators' window (always a fixed 3M, independent of the portfolio range):

```yaml
technical_context_policy:
  technical_window: 3M
  technical_window_is_independent_from_selected_portfolio_range: true
  technical_indicators_are_context_only: true
```

## 8. Technical events — noise reduction (carried over + verified)

- Epsilon tolerance on price/EMA crosses (~0.1% of last close) and on MACD histogram (0.05)
- `minGapDays` between same-type events (3-5 days depending on indicator)
- Max 4 events per asset, max 30 events total (most recent kept)
- snake_case YAML keys throughout (`ema20`, `macd_histogram`, `rsi14`, `threshold`) —
  no more `{0: 0}`-style ambiguous detail keys

## 9. Kept as-is per product decision + definitions added/fixed

- `period_pnl` and `period_pnl_percent` on `AiPosition` — retained, considered reliable
  (sourced from `positions_contribution`).
- `metric_definitions.position_period_pnl_percent` added to clarify that this is
  `period_pnl / |start_value|` at the position level, distinct from the technical
  `return_3m_percent` (price-only return) shown in Technical Summary/Series —
  prevents the AI from conflating a P&L metric with a price return metric.
- No new backend DTOs, no MCP/AI provider integration.

## 10. HTML escaping fix

The `position_period_pnl_percent` definition originally contained a literal `&`
character ("P&L"). Any Markdown-to-HTML rendering step downstream of the clipboard
(e.g. viewing the copied text through a Markdown-aware tool) legitimately re-encodes
raw `&` as `&amp;` per CommonMark/HTML rules — this could confuse an AI reading the
rendered version. Fixed by rewording the string to avoid the ampersand entirely
("gain/loss" instead of "P&L"); the clipboard renderer itself does no escaping of its
own (`navigator.clipboard.writeText()` writes the plain string as-is — verified no
other literal `&` remains anywhere in `frontend/src/lib/features/ai-export/`).

## 11. `simple_roi_percent` definition correction (round 7)

**Problem reported**: the round-6 definition
`"(NAV - period_net_deposits) / period_net_deposits"` did not match real exported
numbers — e.g. `nav: 51004.25`, `period_net_deposits: 6468.26`,
`simple_roi_percent: 11.63` would require `(51004.25 - 6468.26) / 6468.26 ≈ 688.55%`,
nowhere close to the actual 11.63%. The formula was wrong.

**Root cause**: traced the real backend computation in
`backend/app/services/portfolio_service.py` (`get_summary`, ~lines 936-960):

```python
period_net_invested = sum(-cf.amount for cf in period_cfs)  # includes a synthetic
                                                              # cash flow equal to
                                                              # -period_start_nav_perf,
                                                              # PLUS external CFs after
                                                              # period start
simple_roi = calculate_simple_roi(engine_nav, period_net_invested)
# calculate_simple_roi(): (current_nav - total_invested) / total_invested
```

So the true denominator is **`period_nav_start + period_net_deposits`**
(NAV at the start of the selected period, plus net deposits during the period) —
NOT `period_net_deposits` alone. `period_net_deposits` (mapped from
`summary.net_deposited_capital`) only captures the period's external cash flows; it
was missing the starting NAV term entirely.

**Fix**:
- Added `period_nav_start` to `AiPortfolioSnapshot` (pulled from the already-existing
  backend field `summary.period_nav_start` — no backend changes needed).
- Corrected `metric_definitions.simple_roi_percent` to:
  `"Simple ROI for the selected period, computed as period_pnl divided by the capital
  base for the period (approximately period_nav_start + period_net_deposits); treat
  as an approximation, not an exact reproducible formula from the other exported
  fields."`
- Deliberately **not** presented as an exact `=` formula: the backend's ROI
  calculation and the `period_pnl`/`period_nav_start` calculation use slightly
  different period-boundary conventions internally (e.g. `cf.date > period_start_date`
  without an explicit `date_to` upper bound for ROI's cash-flow sum, vs. `cf.date >
  date_from AND cf.date <= date_to` for `period_pnl`'s net flows) — the two are
  conceptually equivalent but not guaranteed to be numerically identical to the last
  decimal in every edge case. Presenting it as an approximation avoids re-introducing
  a formula the AI could mechanically verify and flag as wrong again.

## 12. Validations executed

```text
svelte-check:  0 errors, 0 warnings
./dev.py i18n audit:  1476 keys, 0 incomplete
```

No `api sync` was run — this round only touched frontend TypeScript/Svelte files.

## 13. Known limitations

- **`by_geography` uses a different basis than the rest** (invested market value
  excluding cash, rescaled to ~100% on that smaller base — vs NAV including cash for
  the other sections) — this is a real, permanent asymmetry in the backend data
  (cash has no geography), not a bug. It is declared explicitly via
  `methodology.allocation_basis_exceptions.by_geography` so the AI does not assume
  this section sums to 100% of NAV like the others.
- **Country → continent mapping** (`allocationCompaction.ts`) is a static, frontend-only
  ISO 3166-1 alpha-3 lookup table (~230 codes across 5 continents). It is not
  exhaustive of every possible territory/dependency code; unmapped codes fall into
  `Other minor countries` rather than being dropped or miscategorized.
- `by_geography` compaction groups by continent only when a country is below the 1%
  threshold — the continent grouping itself is coarse (e.g. "Asia-Pacific" merges Asia
  and Oceania) and not further subdivided (no separate Middle East bucket).
- `Minor sectors` intentionally discards the per-sector breakdown of small exposures
  (e.g. Consumer Staples, Energy, Utilities) to keep the export compact; this detail
  is not recoverable from the export alone.
- Technical signals require ~13 months of price history for EMA200 warm-up; assets
  with shorter history get `technical_window_complete: false` and a comparability note.
- Prompt size is not capped by asset count in this MVP; a >50K character warning toast
  is shown but truncation is deferred to a future iteration if it proves necessary in practice.
- **`simple_roi_percent` is not an exactly reproducible formula** from the other
  exported fields — it is closely approximated by
  `period_pnl / (period_nav_start + period_net_deposits)`, but LibreFolio's internal
  ROI calculation uses slightly different period-boundary conventions for its cash-flow
  sum than the `period_pnl`/`period_nav_start` calculation does (see §11). The export
  documents this as an approximation rather than an exact formula to avoid asserting
  false precision.
