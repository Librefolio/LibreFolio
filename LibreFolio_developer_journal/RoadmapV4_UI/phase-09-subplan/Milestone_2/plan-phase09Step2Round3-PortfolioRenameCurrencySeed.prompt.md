# Plan - Phase 09 Step 2 Round 3: Portfolio Rename, Currency Default, Seed Coherence

Sources:
- `plan-phase09Step2Round2-DailyTargetState.prompt.md`
- Gemini follow-up prompt (2026-06-12)
- Current code audit on renamed backend files, dashboard currency flow, and `populate_mock_data.py`

Back-link:
- Previous round: `plan-phase09Step2Round2-DailyTargetState.prompt.md`

Follow-up:
- Next round: `plan-phase09Step2Round4-CashMtMTransparency.prompt.md`

## Goal

Close the residual gaps left after the big Round 2 refactor:

- complete the backend rename from `analytics` terminology to `portfolio`
- clean the POST portfolio routes to `/summary` and `/history`
- force the dashboard to always operate with a concrete target currency
- make `db_populate` derive dynamic transaction amounts from simulated market
  data and keep mock returns realistic

## Audit Snapshot

Confirmed in code:

1. Files are already renamed:
   - `backend/app/api/v1/portfolio_api.py`
   - `backend/app/schemas/portfolio.py`
2. Runtime imports already use `portfolio`, but descriptions/docstrings still
   reference legacy analytics endpoints.
3. Frontend store still depends on generated aliases containing `_query_post`.
4. Dashboard still starts with `targetCurrency = ''` and uses
   `includeAll={true}` on `CurrencySearchSelect`.
5. `populate_mock_data.py` still creates transactions before price history, so
   transaction amounts cannot yet be priced off the simulated series.

## Operational Plan

### Step 1 - Finish backend portfolio contract cleanup

Files:
- `backend/app/api/v1/portfolio_api.py`
- `backend/app/schemas/portfolio.py`
- `backend/app/api/v1/router.py`
- any backend files still matching `analytics`

Actions:
- Replace stale backend references to `analytics` where they still describe the
  active portfolio contract.
- Keep `portfolio_router` as the only router entry for this domain.
- Ensure `/wac` remains under the same router.
- Rename the POST endpoints:
  - `/portfolio/summary/query` -> `/portfolio/summary`
  - `/portfolio/history/query` -> `/portfolio/history`
- Update schema/request descriptions to match the cleaned paths.

### Step 2 - Regenerate client and enforce dashboard currency default

Files:
- `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`
- `frontend/src/routes/(app)/dashboard/+page.svelte`
- generated API client files

Actions:
- Run `./dev.py api sync` immediately after backend route changes.
- Replace the old generated aliases in the portfolio store with the new ones.
- Remove `includeAll={true}` from the dashboard currency selector.
- Initialize `targetCurrency` from `$globalSettings.default_currency` instead of
  an empty string.
- Ensure summary/history requests send `target_currency` from first load, not
  only after manual interaction.

### Step 3 - Re-sequence `db_populate` around market data

Files:
- `backend/test_scripts/test_db/populate_mock_data.py`

Actions:
- Move `populate_price_history(session)` before dynamic transaction creation.
- Restrict dynamic buy/sell activity to the last 365 days.
- For each dynamic transaction, look up the simulated close price for that date
  and compute `amount` from `quantity * price` plus any explicit fee rule.
- Preserve the fixed BRIM duplicate-test dates, but add balancing sell/withdraw
  flows so those fixtures do not pollute long-range portfolio capital.

### Step 4 - Tighten mock-data realism validation

Files:
- `backend/test_scripts/test_db/populate_mock_data.py`

Actions:
- Reuse the existing final validation pass.
- Expand the realism gate to evaluate whether global TWRR/MWRR stay within the
  target range `[-20%, +20%]`.
- Recommended behavior: keep the gate fatal for out-of-range fixture data,
  because this script is deterministic test-seed generation, not production
  analytics.

### Step 5 - Verify the round

Commands:
- `./dev.py api sync`
- `./dev.py front check`
- `./dev.py front format`
- `./dev.py test db populate --force`

Functional checks:
- dashboard sends `target_currency` on first render
- summary/history use the clean POST routes without `/query`
- generated client aliases no longer use `_query_post`
- seeded data stays coherent with simulated prices
- final mock portfolio returns remain plausible

## Notes

- This round is narrower than Round 2: it is cleanup and coherence work, not a
  new architectural rewrite.
- If BRIM duplicate fixtures force a trade-off between import-test fidelity and
  portfolio realism, prefer deterministic realism and document the fixture
  adjustment in the handoff.
- The next discovered gap (cash algebra, explicit missing-price reporting, and
  nominal loan valuation) is tracked in
  `plan-phase09Step2Round4-CashMtMTransparency.prompt.md`.
