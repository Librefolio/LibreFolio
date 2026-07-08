---
title: "test_transaction_implied.py fails — DailyStateBuilder constructor mismatch"
category: problem
status: open
date: 2026-07-07
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

Not yet fixed. To resolve: update `test_transaction_implied.py::_builder()` to drop the `wac_series` kwarg and
add `asset_currencies={}` (or a populated dict matching the test's asset IDs, if any test relies on non-EUR
asset currencies for FX conversion coverage).

## Prevention

The duplicated `_builder()` helper pattern across test files in
`test_scripts/test_services/test_financial/test_portfolio_engine/` is itself the structural cause: a
constructor signature change requires updating every file's local copy instead of one shared fixture/factory.
Consider extracting a single shared `make_daily_state_builder()` test helper (e.g. in a `conftest.py` or shared
test utils module) so future constructor changes only need one update site.

## Impact

Low — this is a pure-unit test file (no DB, no async) exercising the `TRANSACTION_IMPLIED` valuation fallback
for P2P/crowdfund assets without `PriceHistory`. The feature itself (`TRANSACTION_IMPLIED` fallback) is
confirmed working in production via manual verification during the Milestone 2 closeout (holdings no longer
show `current_value=None` for P2P/crowdfund assets) — only this specific test file's scaffolding is stale, so
there is no production risk, but this test file provides zero regression coverage for the
`TRANSACTION_IMPLIED` path until fixed.

## Source files

| Role | Path |
|------|------|
| Failing test file | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_transaction_implied.py` |
| Constructor (current signature) | `backend/app/services/portfolio_engine.py` (`DailyStateBuilder.__init__`) |
| Sibling test (already updated) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_daily_state_builder.py` |
