---
title: "assets.py wipe handlers used non-existent `e.code` attribute"
category: problem
status: resolved
date: 2026-04-25
tags: [backend, assets, exceptions, error-handling, hidden-bug]
related:
  - sources/phase07-part3-closure2
  - decisions/policy-d-currency-wipe
  - entities/api-router
---

# Problem: `assets.py::market_data_{summary,wipe}` referenced `e.code` instead of `e.error_code`

## Symptom

Any error path inside `GET /assets/{id}/market_data/summary` or
`POST /assets/{id}/market_data/wipe` (Policy D) returned **HTTP 500** with a
generic `AttributeError: 'AssetSourceError' object has no attribute 'code'`,
masking the intended **404** "asset not found / no market data" response.

The bug was silent in normal use because the happy paths never raised
`AssetSourceError`. It surfaced only when G-batch6 added end-to-end tests that
exercised the destructive Policy D wipe flow.

## Root Cause

In `backend/app/api/v1/assets.py` the two handlers had:

```python
except AssetSourceError as e:
    raise HTTPException(404, detail={"error_code": e.code, ...})  # ❌
```

But `AssetSourceError` exposes the field as `error_code`, not `code`. Reading
`e.code` raised `AttributeError`, which FastAPI translated into a 500.

## Solution

`e.code` → `e.error_code` in the two occurrences (commit landed in
G-batch6, 2026-04-25, `c943f219`).

```python
except AssetSourceError as e:
    raise HTTPException(404, detail={"error_code": e.error_code, ...})  # ✅
```

## Residual occurrence (lint pass #5, 2026-04-25) — ✅ RESOLVED same day

A **third** instance of the same anti-pattern was found in the same file
at `backend/app/api/v1/assets.py:976` inside `bulk_upsert_events`:

```python
except AssetSourceError as e:
    status = 400 if e.code in ("EVENT_CURRENCY_MISMATCH",) else 500  # ❌ was here
    raise HTTPException(status_code=status, detail=str(e)) from e
```

This branch read `e.code` and would have `AttributeError` → bare-`except
Exception` → HTTP **500** on the very mismatch path it tried to handle
(Policy D `EVENT_CURRENCY_MISMATCH`), instead of the documented HTTP **400**.

**Fix applied 2026-04-25** (post-lint follow-up): identical 3-character
rename `e.code` → `e.error_code`. Regression test added:
`test_assets_events.py::test_bulk_upsert_events_currency_mismatch_returns_400`
(creates a USD asset, submits an EUR DIVIDEND event, asserts HTTP 400).
Test passes ✅. With this fix the entire `assets.py` file is `e.code`-clean.

## Prevention

- **End-to-end tests on error paths**, not only happy paths. The bug had been
  shippable for weeks because no test forced the `AssetSourceError` branch.
- Lint rule idea: a custom mypy/pylint check that flags attribute access on
  exception classes whose attribute names don't match a known set
  (low priority — coverage tests are the durable answer).

## Impact

- ~Zero user impact (Policy D wipe was new and gated by `AssetCurrencyChangeModal`
  which guards inputs, so wrong asset IDs rarely reached the endpoint in practice).
- Discovered by `test_market_data_wipe.py::test_wipe_unknown_asset_returns_404`.
- Same class of bug as why backend test coverage was raised to 87.06% — see
  [[sources/phase07-part3-closure2]] G-batch6.

## Source files

| Role | Path |
|------|------|
| Bug location & fix | `backend/app/api/v1/assets.py` (handlers `market_data_summary`, `wipe_market_data`, **and `bulk_upsert_events` — fixed 2026-04-25 post-lint**) |
| Exception definition | `backend/app/services/asset_source_errors.py` (`AssetSourceError.error_code`) |
| Tests that caught it | `backend/test_scripts/test_api/test_market_data_wipe.py` (G-batch6, original 2 sites); `backend/test_scripts/test_api/test_assets_events.py::test_bulk_upsert_events_currency_mismatch_returns_400` (post-lint, residual site) |

