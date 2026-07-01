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
```

All allocation sections are computed on a NAV-including-cash basis so they sum to
~100% (small residual gaps are captured explicitly, never silently dropped):

| Section | Cash included | Source |
|---|---|---|
| `by_asset_type` | ✅ (backend emits `Liquidity` bucket) | `summary.allocation_by_type` |
| `by_sector` | ✅ (backend emits `Liquidity` bucket) | `summary.allocation_by_sector` |
| `by_geography` | ❌ (cash has no geography) | `summary.allocation_by_geography` + `Other / Unallocated` fallback |
| `by_currency` | ✅ — added from `summary.cash_balances` | frontend-computed |
| `by_broker` | ✅ — added from `summary.by_broker[].cash_total` | frontend-computed |
| `by_asset` | ✅ — single `Cash / Liquidity` line added | frontend-computed |

`ensureAllocSums100()` adds an `Other / Unallocated` entry whenever a section's total
percent deviates from 100% by more than 0.5 points (covers geography, and any residual
rounding elsewhere).

## 4. Section order (final)

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

## 5. Fields deliberately NOT included

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

## 6. Technical context policy

Declared explicitly in `methodology.technical_context_policy` so the AI does not
conflate the portfolio's selected date range (which can be YTD/1Y/custom) with the
technical indicators' window (always a fixed 3M, independent of the portfolio range):

```yaml
technical_context_policy:
  technical_window: 3M
  technical_window_is_independent_from_selected_portfolio_range: true
  technical_indicators_are_context_only: true
```

## 7. Technical events — noise reduction (carried over + verified)

- Epsilon tolerance on price/EMA crosses (~0.1% of last close) and on MACD histogram (0.05)
- `minGapDays` between same-type events (3-5 days depending on indicator)
- Max 4 events per asset, max 30 events total (most recent kept)
- snake_case YAML keys throughout (`ema20`, `macd_histogram`, `rsi14`, `threshold`) —
  no more `{0: 0}`-style ambiguous detail keys

## 8. Kept as-is per product decision

- `period_pnl` and `period_pnl_percent` on `AiPosition` — retained, considered reliable
  (sourced from `positions_contribution`).
- No new backend DTOs, no MCP/AI provider integration.

## 9. Validations executed

```text
svelte-check:  0 errors, 0 warnings
./dev.py i18n audit:  1503 keys, 0 incomplete
```

No `api sync` was run — this round only touched frontend TypeScript/Svelte files.

## 10. Known limitations

- `by_geography` cannot reach 100% including cash by construction (cash has no
  geography); the `Other / Unallocated` fallback communicates the gap explicitly
  rather than silently under-reporting.
- Technical signals require ~13 months of price history for EMA200 warm-up; assets
  with shorter history get `technical_window_complete: false` and a comparability note.
- Prompt size is not capped by asset count in this MVP; a >50K character warning toast
  is shown but truncation is deferred to a future iteration if it proves necessary in practice.
