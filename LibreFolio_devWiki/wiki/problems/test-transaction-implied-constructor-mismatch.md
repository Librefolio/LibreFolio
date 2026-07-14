---
title: "test_transaction_implied.py fails — DailyStateBuilder constructor mismatch"
category: problem
status: resolved
date: 2026-07-07
resolved_date: 2026-07-13
tags: [backend, testing, portfolio-engine, pre-existing, low-priority]
related:
  - entities/portfolio-engine
  - concepts/inline-wac-computation
  - sources/phase09-m1-m2-archive-2026-07
---

# Problem: `test_transaction_implied.py` Fails — `DailyStateBuilder` Constructor Mismatch

## Symptom

All 6 tests in
`backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_transaction_implied.py` fail
with:

```
TypeError: DailyStateBuilder.__init__() got an unexpected keyword argument 'wac_series'
```

Discovered during the exhaustive verification pass before archiving Phase 09 Milestone 1 & 2 (2026-07-07). Not
part of the archived work itself — a pre-existing, unrelated gap in test maintenance.

## Root Cause

The test file's local `_builder()` helper (a `DailyStateBuilder` factory used only within this test file) still
constructs the builder using the **pre-refactor** constructor signature:

```python
return DailyStateBuilder(
    classified_txs=classified_txs or [],
    in_transit_intervals=[],
    external_cash_flows=[],
    price_map=price_map or {},
    quote_base_map=quote_base_map or {},
    wac_series=wac_series or {},        # <- no longer a valid kwarg
    fx_rate_map=fx_rate_map or {},
    asset_classifications={},
    asset_types={},
    # asset_currencies=... is MISSING — now a required keyword-only arg
    target_currency=target_currency,
    date_from=date.fromisoformat(date_from),
    date_to=date.fromisoformat(date_to),
)
```

Commit `39106380` (2026-06-30, the inline-WAC / 3-pool refactor — see [[concepts/inline-wac-computation]] and
[[entities/portfolio-engine]]) removed `wac_series` from `DailyStateBuilder.__init__()` (WAC is now computed
inline from the per-transaction loop) and added a new required keyword-only parameter, `asset_currencies:
dict[int, str]`. The sibling test file `test_daily_state_builder.py` was updated for the new signature at that
time; `test_transaction_implied.py`'s local helper (which intentionally duplicates the same helper pattern
rather than importing a shared one) was missed.

## Solution

**Correction (2026-07-13): the originally proposed fix below does NOT work — verified empirically.**
Applying only the signature fix (drop `wac_series`, add `asset_currencies={}`, unwrap
`build().daily_states`) still leaves 4 of 6 tests failing. The mismatch is deeper than a
constructor signature: commit `39106380` didn't just rename `wac_series`, it **removed the
WAC-as-valuation fallback entirely**. `DailyStateBuilder._market_value_for()` now documents
explicitly: *"NO WAC→price fallback. WAC is only for cost basis, never for valuation."*
Valuation is strictly `MARKET_PRICE → LAST_BUY_PRICE(V(u)) → MISSING`, where `LAST_BUY_PRICE`
comes from an externally-supplied `last_buy_prices: dict[int, tuple[date, Decimal, str]]`
(keyed by `asset_id` only, aggregated across V(u) visible brokers) — not from inline WAC.
`transaction_implied_asset_ids` is a field name kept for schema/frontend compatibility, but
it's now populated whenever `LAST_BUY_PRICE` is used, not when WAC is used as a price proxy.

This is confirmed by `test_portfolio_engine_vnext.py::TestLastBuyPrice::test_no_wac_as_price`,
added in the same commit, which explicitly asserts the opposite of what this file expected:
*"Even with WAC available, if no market price and no last_buy → MISSING"*.

**Resolution taken**: deleted `test_transaction_implied.py`. Its MISSING-path coverage
(no price, no fallback → `missing_price_asset_ids`/`nav_complete=False`) is preserved in
`test_daily_state_builder.py::TestMissingPrices` (fixed in the same pass — see
`asset_currencies` note above, this file's `_builder()` needed the identical signature
update and passed once applied, since it doesn't touch the implied-valuation assertions).
The LAST_BUY_PRICE-fallback coverage this file used to attempt is already owned by
`test_portfolio_engine_vnext.py::TestLastBuyPrice` (4 tests, position-state level).

**Known residual gap** (not filled, flagged for a future dedicated task rather than guessed
at here): neither `TestLastBuyPrice` (position-state level) nor `test_daily_state_builder.py`
(day-aggregate level, no last_buy_price scenarios) currently test the BTP-style
`quote_base_quantity` interaction with the `LAST_BUY_PRICE` fallback, nor the day-aggregate
(`DailyPortfolioState`) view of a LAST_BUY_PRICE-valued holding. If that combination matters,
it needs a new test written against the current `last_buy_prices` mechanism — not a revival
of this file's WAC-based assertions.

## Prevention

The duplicated `_builder()` helper pattern across test files in
`test_scripts/test_services/test_financial/test_portfolio_engine/` is itself the structural cause: a
constructor signature change requires updating every file's local copy instead of one shared fixture/factory.
Consider extracting a single shared `make_daily_state_builder()` test helper (e.g. in a `conftest.py` or shared
test utils module) so future constructor changes only need one update site.

## Impact

Resolved — see Solution above. The original "Low / no production risk" assessment was correct in outcome
(P2P/crowdfund holdings do show a value in production) but for the wrong mechanism: it's `LAST_BUY_PRICE`
(V(u)-wide last BUY price), not `TRANSACTION_IMPLIED` (WAC-as-price). The `TRANSACTION_IMPLIED` mechanism
this test file exercised was intentionally removed in commit `39106380`, not merely renamed.

## Source files

| Role | Path |
|------|------|
| Deleted test file (was failing) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_transaction_implied.py` |
| Constructor (current signature) | `backend/app/services/portfolio_engine.py` (`DailyStateBuilder.__init__`, `_market_value_for`) |
| Sibling test (fixed, same signature update) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_daily_state_builder.py` |
| Replacement coverage (LAST_BUY_PRICE) | `backend/test_scripts/test_services/test_portfolio_engine_vnext.py` (`TestLastBuyPrice`) |
