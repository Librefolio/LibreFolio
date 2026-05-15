---
title: "Phase 07 Part 4 Round 6 Plan C2 — Bugfix + Pair Desc/Tags Validation + Test Coverage"
category: source
source_type: plan
date_ingested: 2026-05-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC2_BugfixAndPairValidation.prompt.md
tags: [phase07, transactions, bugfix, pair-validation, clone, picker, toast, docker, fx-fallback, mock-data, e2e]
related:
  - sources/phase07-part4-round6-planc-txstore-refactor
  - sources/phase07-part4-round6-planc2r2-regressions-mockfx
  - decisions/pair-description-tags-validation
  - problems/fx-multi-route-no-fallback
  - features/F-048
  - features/F-047
---

# Source: Plan C2 — Bugfix + Pair Desc/Tags Validation + Test Coverage

## Summary

Plan C2 addresses 6 bugs found during manual testing of Plan C (txStore refactor), adds a backend validation rule enforcing identical `description` and `tags` on linked transaction pairs, adds bulk commit toast, and significantly expands E2E test coverage from 68 to 80 tests (UC coverage 58% → 92%). Additionally, it includes 4 important infrastructure fixes outside Phase 07 scope: Docker non-root container, Noto Color Emoji self-hosted fonts, FX multi-route fallback, and `classification_params` race condition.

## Key Takeaways

- **B1 (false positive "edited")**: Root cause = mock data had divergent descriptions between pair sides → `collectDualCreates()` copies "from" desc to both → `diffDualItem` detects change. Fix: (a) align mock data, (b) FormModal concatenates mismatched descs with `[auto-merged]` note for legacy data
- **B2 (clone paired only clones half)**: `resolveInitialRows()` excluded partner for clone action → fixed to auto-include partner + generate shared `link_uuid`
- **B3 (picker has ContextMenu + actions)**: Added `hideActions` prop to `TransactionsTable`, passed from PickerModal
- **B4 (no toast after bulk commit)**: `handleBulkCommitted()` now counts successes by operation type and shows summary toast
- **B6 (mock data divergent descriptions)**: All 8 linked pairs in `populate_mock_data.py` aligned with `↔` format
- **Backend pair validation** (Step 2): New `_validate_pair_description_tags()` in `TransactionService` — rejects linked pairs with mismatched description or tags (codes: `pairDescriptionMismatch`, `pairTagsMismatch`). Hooked into step 6 (creates) and step 4b (updates)
- **Test coverage jump**: 68 → 80 E2E tests, 7 → 9 spec files, UC covered 15/26 → 24/26
- **Docker non-root** (A1): Container runs as `librefolio` user with host UID/GID mapping
- **Font self-hosted** (A2): Noto Color Emoji now served from `frontend/static/fonts/` via extended `update_js_cache.py` — eliminates 23s CDN wait
- **FX multi-route fallback** (A3): `sync_pairs_bulk` now tries all routes in priority order when primary fails (Phase 1 collects all route legs, Phase 3 loops with fallback)
- **classification_params race** (A4): `session.refresh(asset)` before auto-populate prevents stale read; compare-before-write prevents false `changes_count`

## Bugs Fixed (6)

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| B1 | deriveStatus false positive "edited" on paired edit | Mock data divergent descs + FormModal only shows "from" desc | Align mock data + concatenate mismatched descs in FormModal |
| B2 | Clone paired TX only clones one half | resolveInitialRows excluded partner for clone | Auto-include partner + shared link_uuid |
| B3 | Picker shows context menu + action buttons | No mechanism to disable actions in picker context | hideActions prop on TransactionsTable |
| B4 | No toast after bulk commit | handleBulkCommitted only reloaded | Count by operation type + summary toast |
| B5 | Reset removes label but bg stays | Consequence of B1 | Resolved by fixing B1 |
| B6 | Mock data divergent descriptions | 8 pairs had different descs between out/in sides | Aligned all pairs with "↔" format |

## Infrastructure Addenda (A1–A4)

These are outside Phase 07 scope but landed in the same commit batch:

1. **A1 Docker non-root**: `ARG UID/GID=1000`, user `librefolio`, `USER librefolio`. docker-compose passes host UID/GID
2. **A2 Font self-hosted**: `update_js_cache.py` extended with `"font"` type — downloads Google Fonts CSS + woff2 subsets → local serving
3. **A3 FX multi-route fallback**: `pair_routes_map[slug] = [route1, route2, ...]` → Phase 3 loops all routes by priority. Extracted `_compute_single_step()` / `_compute_multi_step()` helpers
4. **A4 classification_params race**: `await session.refresh(asset)` before auto-populate + compare-before-write guard

## New E2E Test Specs

- `frontend/e2e/transactions/tx-clone.spec.ts` (5 tests): clone standalone, clone paired, quantityRule zero, clone paired commit, clone from view-only broker
- `frontend/e2e/transactions/tx-bulk-operations.spec.ts` (7 tests): bulk edit, no-change status, mark/unmark delete, reset, mixed commit toast, picker no actions, pair desc validation banner

## Wiki Pages Updated

- [[features/F-048]] — clone paired, picker hideActions, bulk commit toast, pair validation, UC coverage
- [[decisions/pair-description-tags-validation]] — new
- [[problems/fx-multi-route-no-fallback]] — new

## Source files

| Role | Path |
|------|------|
| Transaction service (pair validation) | `backend/app/services/transaction_service.py` |
| Mock data | `backend/test_scripts/test_db/populate_mock_data.py` |
| BulkModal (clone fix) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| FormModal (mismatched desc) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| TransactionsTable (hideActions) | `frontend/src/lib/components/transactions/TransactionsTable.svelte` |
| PickerModal | `frontend/src/lib/components/transactions/TransactionPickerModal.svelte` |
| Page (+toast) | `frontend/src/routes/(app)/transactions/+page.svelte` |
| E2E clone | `frontend/e2e/transactions/tx-clone.spec.ts` |
| E2E bulk ops | `frontend/e2e/transactions/tx-bulk-operations.spec.ts` |
| FX sync (fallback) | `backend/app/services/fx.py` |
| Dockerfile | `Dockerfile` |
| update_js_cache | `scripts/update_js_cache.py` |
| Asset source (race fix) | `backend/app/services/asset_source.py` |

