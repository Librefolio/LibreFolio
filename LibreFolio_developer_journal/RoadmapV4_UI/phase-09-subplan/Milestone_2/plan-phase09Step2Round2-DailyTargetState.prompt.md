# Plan — Phase 09 Step 2 Round 2: Daily Target State

Sources:
- `plan_fix_portfolio_history.md`
- `analysis-portfolio-chart-bugs.prompt.md`
- User target-state prompt (2026-06-12)

Follow-up:
- Next round: `plan-phase09Step2Round3-PortfolioRenameCurrencySeed.prompt.md`

## Goal

Close the gap between the current “patched dashboard” and the final target
state:

- dense daily portfolio history
- POST-based portfolio query endpoints
- `Currency` payloads for monetary fields
- stable dashboard reactivity for period/currency/filter changes
- realistic `db_populate` seed with explicit financial sanity validation

## Gap Summary

1. `get_history()` still derives visible points from transaction dates.
2. Summary/history contracts still expose bare `SafeDecimal` amounts.
3. Frontend dashboard/store/chart still assume the old GET + primitive schema.
4. Test-seed realism still owns too much of the MWRR problem space.

## Implementation Steps

### Step 1 — Redefine portfolio query contracts

Files:
- `backend/app/schemas/analytics.py`
- `backend/app/api/v1/analytics.py`

Actions:
- Add POST query-body schemas for portfolio summary/history.
- Migrate response schemas so monetary fields use `Currency`.
- Keep return percentages as `SafeDecimal`.
- Prepare clean migration from GET to POST query endpoints.

### Step 2 — Replace sparse history with daily expansion

Files:
- `backend/app/services/portfolio_service.py`

Actions:
- Build a continuous day-by-day calendar.
- Forward cumulative cash and holdings across days.
- Price held assets each day with `PriceHistory` + FX conversion.
- Recompute NAV daily.
- Rebase TWRR/MWRR/ROI on the selected period using the `date_from` NAV as the
  synthetic starting investment.
- Ensure the first visible point has `twrr=0`, `mwrr=0`, `roi=0`.

### Step 3 — Re-audit ROI purity and move realism to seed generation

Files:
- `backend/app/utils/financial/roi_utils.py`
- `backend/test_scripts/test_db/populate_mock_data.py`

Actions:
- Keep production ROI math pure except for hard safety checks like
  `math.isfinite`.
- Remove/revisit interim defensive tweaks that are not part of the intended
  financial model.
- Make the generated seed financially plausible over time.
- Fail `db_populate` loudly if TWRR/MWRR sanity breaks.

### Step 4 — Sync API client and migrate portfolio store

Files:
- `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`
- generated client files under `frontend/src/lib/api/`

Actions:
- Move store fetches to POST bodies.
- Update cache keys for the new request shape.
- Switch all monetary reads to `Currency.amount` / `Currency.code`.

### Step 5 — Refactor dashboard UI to final layout

Files:
- `frontend/src/routes/(app)/dashboard/+page.svelte`
- `frontend/src/lib/components/dashboard/GrowthChart.svelte`
- `frontend/src/lib/components/dashboard/HoldingsPanel.svelte`
- `frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte`
- `frontend/src/lib/components/charts/GeographyMap.svelte`

Actions:
- Header: `[ Range ] [ Filtra Broker ] [ Sincronizza ]`
- Reuse custom components first (`DateRangePicker`, `CurrencySearchSelect`,
  `DataTable`, etc.)
- Make chart rerender deterministic when period/currency changes.
- Rework bottom section to explicit 2-column positions/transactions split.
- Fix mobile geography map scroll/tooltip/labels behavior.

### Step 6 — Verify end to end

Commands:
- `./dev.py api sync`
- `./dev.py front check`
- `./dev.py front format`
- targeted backend lint/tests
- `./dev.py test db populate --force`

Checks:
- history starts at selected `date_from`
- currency change visibly affects summary/chart values
- history is daily, not transaction-sparse
- POST payloads carry filters correctly
- mobile map no longer traps page scroll

## Notes

- This round is a full coordinated refactor, not a backward-compatible patch.
- If import-overlap fixtures must be broken to make seed generation realistic
  and repeatable, do it explicitly and report it in the final handoff.
- Residual cleanup after this round (backend naming cleanup, mandatory dashboard
  target currency, and market-coherent `db_populate` transactions) is tracked in
  `plan-phase09Step2Round3-PortfolioRenameCurrencySeed.prompt.md`.
