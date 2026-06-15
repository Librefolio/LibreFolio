# Plan - Phase 09 Step 2 Round 4: Cash Algebra, Missing Data Transparency, Loan Nominals

Sources:
- Gemini analysis shared on 2026-06-12
- Current code audit on `PortfolioService`, `portfolio.py`, `populate_mock_data.py`, and dashboard UI alerts

Back-link:
- Previous round: `plan-phase09Step2Round3-PortfolioRenameCurrencySeed.prompt.md`

## Goal

Resolve the next architectural gap in the dashboard portfolio engine:

- fix liquidity math so it uses the signed transaction ledger instead of
  filtered/absolute-value logic
- keep mark-to-market pure while exposing missing market data explicitly
- seed nominal valuation points for P2P loans
- show the resulting issues clearly in the dashboard UI

## Confirmed Gap

1. `get_summary()` only derives broker cash from deposits/withdrawals and ignores
   the cash effect of buys, sells, dividends, interest, fees, and taxes.
2. `get_history()` and `_build_history_series()` still apply extra logical
   filtering and sign-flipping even though DB amounts are already algebraically
   signed.
3. `PortfolioSummary` still exposes `wac_missing_pairs` and has no
   `missing_prices_assets`.
4. `populate_price_history()` still seeds only market assets, leaving P2P loans
   without a nominal valuation point.
5. The dashboard does not yet render warnings for assets excluded from NAV or
   missing FX conversions.

## Operational Plan

### Step 1 - Fix cash algebra in history and summary

Files:
- `backend/app/services/portfolio_service.py`

Actions:
- In `get_history()`, stop dropping non-deposit/non-withdrawal/non-holding cash
  events.
- In `_build_history_series()`, replace per-type sign logic with a pure
  algebraic daily sum: `cash_delta_by_date[row.date] += row.amount * row.share`.
- In `get_summary()`, compute broker cash from all signed transaction amounts,
  converted into the target currency without `abs()` distortion.
- Keep deposit/withdrawal-specific logic only for invested-capital / MWRR cash
  flow inputs.

### Step 2 - Expose missing data explicitly

Files:
- `backend/app/schemas/portfolio.py`
- `backend/app/services/portfolio_service.py`

Actions:
- Rename `wac_missing_pairs` to `missing_fx_pairs` across portfolio summary and
  WAC response payloads.
- Add `missing_prices_assets: list[str]` to `PortfolioSummary`.
- Whenever an asset is excluded from NAV because no `PriceHistory` is available,
  record its display name for the frontend.

### Step 3 - Seed nominal prices for P2P loans

Files:
- `backend/test_scripts/test_db/populate_mock_data.py`

Actions:
- Create one manual `PriceHistory` point for each `CROWDFUND_LOAN` mock asset.
- Use the nominal unit value implied by its mock purchase.
- Rely on stale/backfill behavior so the loan remains valued without requiring a
  scheduler-driven price series.

### Step 4 - Surface warnings in the dashboard

Files:
- `frontend/src/routes/(app)/dashboard/+page.svelte`
- regenerated API client files

Actions:
- Run `./dev.py api sync`.
- Reuse the amber banner pattern from asset detail.
- Show dashboard warnings for:
  - missing market prices (assets excluded from NAV)
  - missing FX pairs (aggregates may be incomplete)

### Step 5 - Validate

Commands:
- `./dev.py api sync`
- targeted backend API tests in `backend/test_scripts/test_api/`
- `./dev.py front check`
- `./dev.py front format`
- `./dev.py test db populate --force`

Expected outcomes:
- cash totals and history reflect all signed ledger events
- P2P loans no longer artificially depress NAV
- summary payload exposes `missing_fx_pairs` and `missing_prices_assets`
- dashboard warnings become user-visible and actionable

## Open Decisions

1. Should the realism gate remain **warning-only** when TWRR/MWRR exceed the
   desired tolerance, or become **fatal** now that cash algebra is being fixed?
2. Should the single nominal `PriceHistory` point for each loan be anchored at
   the **first buy date** or at the broader **seed history start date**?
