---
title: "FX sync_pairs_bulk used only primary route — no fallback on failure"
category: problem
status: resolved
date: 2026-05-10
tags: [backend, fx, providers, sync, fallback, resilience]
related:
  - features/F-015
  - features/F-016
  - decisions/provider-registry-decision
---

# Problem: FX sync_pairs_bulk Had No Multi-Route Fallback

## Symptom

When the primary FX provider for a pair (e.g., BOE) failed (bot protection returning HTML instead of CSV), the entire pair sync failed. Alternative routes (ECB, FED, SNB) configured with lower priority were completely ignored.

## Root Cause

Phase 1 of `sync_pairs_bulk` collected legs only from `routes[0]` (primary route). Phase 3 raised `FXServiceError` at the first failed leg without attempting alternative routes. The multi-route architecture existed in the database (multiple `FxConversionRoute` per pair with different priorities) but was never utilized at runtime.

## Solution

Three-phase fix in `backend/app/services/fx.py`:

1. **Phase 1 (collect legs)**: Changed from `pair_route_map[slug] = route` (single) to `pair_routes_map[slug] = [route1, route2, ...]` (all routes). Legs collected from ALL routes for parallel pre-fetch.
2. **Phase 2 (fetch)**: Unchanged — now fetches data for all referenced providers.
3. **Phase 3 (process)**: Monolithic `_process_route()` replaced by loop over routes in priority order. If legs of a route fail → `continue` to next route. Log fallback for diagnostics. Extracted `_compute_single_step()` and `_compute_multi_step()` for reuse.

## Prevention

- 3 backend tests with MockFX providers (`test_fx_fallback_primary_fails`, `test_fx_fallback_all_fail`, `test_fx_direct_mockfx`) verify the fallback behavior
- Original error from failed primary route preserved in `errors[]` response field for diagnostics

## Impact

Before fix: any primary provider hiccup (BOE bot protection, network timeout) caused complete sync failure for affected pairs. After fix: transparent fallback to alternative providers — user may not even notice the primary failed.

## Source files

| Role | Path |
|------|------|
| FX service (fallback logic) | `backend/app/services/fx.py` |
| MockFX providers (test infra) | `backend/app/services/fx_providers/mockfx.py` |
| FX fallback tests | `backend/test_scripts/test_api/test_fx_sync.py` |

