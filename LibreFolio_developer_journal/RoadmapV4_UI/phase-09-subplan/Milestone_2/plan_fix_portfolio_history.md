# Fix Portfolio History Growth & Dashboard UI

The goal of this plan is to correct the mathematical bugs causing flat TWRR/ROI and spiking MWRR in the portfolio growth charts, and to update the frontend UI based on the latest requirements.

## User Review Required

- **Performance impact of historical NAV**: To calculate accurate historical NAVs, the backend must iterate over daily quantities of held assets, fetch their historical prices, and run FX conversions. For large portfolios with years of data, this could slow down the `/api/v1/portfolio/history` endpoint. We will optimize this by loading prices and FX rates in bulk, but please review if this is acceptable.
- **Currency Query Parameter**: To support the UI currency selector, we will add an optional `target_currency` query parameter to the `summary` and `history` API endpoints.

## Open Questions

- In `GrowthChart.svelte`, changing the currency will require a refetch of the `/history` (and likely `/summary`) API endpoints with the new currency. Is the state for this managed globally (e.g. in `portfolioStore.ts`) so both summary and history update together?

## Proposed Changes

---

### Backend Mathematics & Algorithms

#### [MODIFY] [roi_utils.py](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/utils/financial/roi_utils.py)
- **Fix MWRR edge-case bug**: In `calculate_mwrr` and `calculate_mwrr_series`, cash flows occurring exactly on the `end_date` (or the date of the current snapshot in the series) are skipped because of the `0 < days < total_days` condition.
- We will update the logic to aggregate any cash flows that land on `total_days` and apply them to the final cash flow tuple alongside `final_nav`. E.g., `(float(total_days), float(final_nav) + float(cf_on_end_date))`. This prevents the solver from treating a deposit as magical market growth.

#### [MODIFY] [portfolio_service.py](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/services/portfolio_service.py)
- **Compute True Historical Market Value**: Instead of `nav = cash + invested_capital`, we will rebuild `get_history` (or `_build_history_series` if moved to async).
- The new logic will track a running total of asset quantities (from BUY/SELL transactions).
- It will query `PriceHistory` to get the closest available closing price for each asset on every active date.
- It will apply FX conversion using `convert_bulk` for any asset priced in a different currency.
- `NAV = cumulative_cash + cumulative_market_value`. This allows TWRR and ROI to naturally float with market movements rather than sticking to 0.00%.

#### [MODIFY] API Router (Portfolio)
- Modify `GET /api/v1/portfolio/history` and `GET /api/v1/portfolio/summary` to accept an optional `target_currency: str | None = None` query parameter.
- Pass this to `PortfolioService` to override the default user `base_currency`.

---

### Frontend Dashboard UI

#### [MODIFY] [GrowthChart.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/dashboard/GrowthChart.svelte)
- Update the UI selector that currently says `EUR | %` to say `Abs | %`.
- Add a new `<select>` or dropdown component nearby for the Target Currency.
- Default the Currency selector to the user's base setting (from auth/settings store).
- On change of the currency selector, trigger a refetch of the portfolio history and summary passing `?target_currency={selected}`.

## Verification Plan

### Automated Tests
- Run backend unit tests, specifically `pytest backend/test_scripts/test_services/test_financial/test_roi_utils.py` to ensure MWRR edge cases with end-date cashflows do not cause infinite loops or weird spikes.

### Manual Verification
- Load the LibreFolio dashboard.
- Verify the Growth Chart now shows a dynamic line that follows asset price appreciations (TWRR and ROI != 0).
- Verify MWRR no longer spikes to huge percentages immediately after a deposit.
- Test the `Abs / %` toggle to ensure formatting works.
- Test changing the target currency selector and confirm the API refetches and chart values adapt accordingly.
