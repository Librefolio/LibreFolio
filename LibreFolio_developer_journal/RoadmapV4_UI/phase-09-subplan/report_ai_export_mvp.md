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
  by_geography: "market_value_excluding_cash — backend does not classify cash geographically; percentages are not rescaled to NAV and do not sum to 100%"
```

Most allocation sections are computed on a NAV-including-cash basis so they sum to
~100% (small residual gaps are captured explicitly, never silently dropped):

| Section | Cash included | Source |
|---|---|---|
| `by_asset_type` | ✅ (backend emits `Liquidity` bucket) | `summary.allocation_by_type` |
| `by_sector` | ✅ (backend emits `Liquidity` bucket) | `summary.allocation_by_sector` |
| `by_geography` | ❌ **exception** — backend has no cash geography; NOT rescaled to NAV, sums to ~100% of market_value only | `summary.allocation_by_geography` |
| `by_currency` | ✅ — added from `summary.cash_balances` | frontend-computed |
| `by_broker` | ✅ — added from `summary.by_broker[].cash_total` | frontend-computed |
| `by_asset` | ✅ — single `Cash / Liquidity` line added | frontend-computed |

**Root cause fixed**: an earlier iteration added a `Liquidity` line to `by_geography`
using the NAV-based cash percentage, while the country percentages underneath were
already summing to ~100% of *market_value only* (backend `by_geo` denominator excludes
cash, unlike `by_type`/`by_sector` which already fold cash into their own `Liquidity`
bucket). Adding NAV-based cash on top of a market-value-based 100% pushed the section
to ~101%, and `ensureAllocSums100()` then emitted a negative `Other / Unallocated`
residual to force the sum back to 100 — an invalid, confusing value.

**Fix**: `by_geography` is no longer rescaled and no `Liquidity` line is added to it.
Country percentages are exported exactly as returned by the backend (their own
100%-of-market-value basis), and the basis exception is declared explicitly in
`methodology.allocation_basis_exceptions` so the AI does not assume `by_geography`
sums to 100% of NAV like the other sections.

`ensureAllocSums100()` now also guards against emitting negative residuals: if a
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

## 9. Kept as-is per product decision + new definition added

- `period_pnl` and `period_pnl_percent` on `AiPosition` — retained, considered reliable
  (sourced from `positions_contribution`).
- **New**: `metric_definitions.position_period_pnl_percent` added to clarify that
  this is `period_pnl / |start_value|` at the position level, distinct from the
  technical `return_3m_percent` (price-only return) shown in Technical Summary/Series —
  prevents the AI from conflating a P&L metric with a price return metric.
- No new backend DTOs, no MCP/AI provider integration.

## 10. Validations executed

```text
svelte-check:  0 errors, 0 warnings
./dev.py i18n audit:  1503 keys, 0 incomplete
```

No `api sync` was run — this round only touched frontend TypeScript/Svelte files.

## 11. Known limitations

- **`by_geography` uses a different basis than the rest** (`market_value_excluding_cash`
  vs `nav_including_cash`) — this is a real, permanent asymmetry in the backend data
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
