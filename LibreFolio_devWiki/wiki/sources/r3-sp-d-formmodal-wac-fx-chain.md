# Source: R3-SP-D Plan Chain — FormModal Props + Event Picker + WAC FX Feedback + Bugfixes

> **Ingested**: 2026-06-04 @ `61cc81e5`
> **Status**: ✅ ALL DONE (2026-06-01 → 2026-06-04)
> **Origin**: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/`

---

## Plan Chain Overview

6 plans forming the D2-Round3 sub-plan (SP-D) and its bugfix tail. All completed as of 2026-06-04.

| # | Plan | Date | Summary |
|---|------|------|---------|
| 1 | `plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md` | 2026-06-01 | Root plan: 3 steps (A: FormModal props unification, B: AssetEventPicker, C: WAC FX staleness feedback) |
| 2 | `Bugfix-SPD/plan-R3-SP-D-BugfixRound1.prompt.md` | 2026-06-03→04 | 12 steps: issue index fix, event picker UX, slider redesign, bulk event cell, sync FX button, WAC buttons logic, validation messages, INDEX greyed, FX badge tooltip, original unit cost propagation, mock data, E2E tests |
| 3 | `Bugfix-SPD/plan-R3-SP-D-BugfixRound2.prompt.md` | 2026-06-03 | 7 fixes: translations, delta event picker, slider-in-dropdown, DIVIDEND hint, currency format, balance issue labeling |
| 4 | `Bugfix-SPD/plan-R3-SP-D-WacCurrency.prompt.md` | 2026-06-03 | WAC target currency selector: chip valuta, sentinella override, `determine_target_currency()` |
| 5 | `Bugfix-SPD/plan-R3-SP-D-WacCurrencyFix.prompt.md` | 2026-06-03 | 6 UX polish: warning condition, blur fix, FX fallito non forza manual, toggle behavior |
| 6 | `Bugfix-SPD/plan-R3-SP-D-WacFxEnrich.prompt.md` | 2026-06-04 | 3 phases: backend date enrichment for missing pairs, FxSyncModal integration, tooltip redesign, blur fix (formatDecimalForDisplay), E2E tests |

---

## Key Features Delivered

### A — FormModal Props Unification
- `initialRow` + `injectedPartnerRow` → single `items: FormModalItems | null` prop
- Callers use `resolveFormItemsForView()` / `resolveFormItemsFromOps()` 
- Zero logic change inside FormModal — pure interface refactor

### B — AssetEventPicker
- New `AssetEventSelect.svelte` → eventually redesigned as `AssetEventPicker.svelte` (slider integrated in dropdown)
- Fetches events via `POST /assets/events/query` with date range filter
- Slider ±N days (max 30, persisted to localStorage)
- Delta indicator (Δ+/-) comparing TX cash with event amount
- Gated by `canShowAssetEvent && draft.date !== ''`

### C — WAC FX Staleness Feedback
- Backend propagates `fx_info` (FxBackwardFillInfo) in qualifying_txs
- Backend emits `WAC_FX_UNAVAILABLE` validation issue with `missing_pairs` as params
- Frontend: amber banner for stale rates, forced-manual when pairs missing
- Sync FX button in validation banner triggers `POST /fx/currencies/sync`
- WAC FX tooltip redesign (bottom position, amber/red coloring)

### D — WAC Target Currency
- Default: last acquisition's currency (deterministic, not majority vote)
- Override via `cost_basis_override: {code: "KRW", amount: "0"}` sentinel
- Chip valuta in PMC suggestion row (always visible in auto mode)
- `determine_target_currency()` backend function

### E — FxSyncModal Integration
- Single FxSyncModal instance owned by FormModal parent
- WacPreviewSection calls parent via `onOpenFxSync` prop
- z-index: parent + 10 (stacks above FormModal)
- Post-sync: auto re-validate, modal stays open for results

---

## Key Decisions Extracted

| Decision | Choice | Rationale |
|----------|--------|-----------|
| WAC target currency | Last acquisition's currency (not majority) | Deterministic, predictable, no ties |
| cost_basis_override semantics | Currency object `{code, amount}` not raw decimal | Unambiguous currency + enables currency selector |
| FxSyncModal ownership | Parent owns modal, child calls `onOpenFxSync` | Single instance, no duplicate modals |
| Blur detection | Compare `formatDecimalForDisplay()` strings | Handles backend precision (17 decimals) vs display truncation (8 decimals) |
| useValidateScheduler manual bypass | Manual triggers skip antiBounce 10s | Post-sync re-validate must happen immediately |
| FX missing → NOT force manual | Show error informatively, keep auto | User can sync FX without losing auto mode |
| Issue row index mapping | Use `buildOpsIndexMap()` for `operation:index` → tempId | Correct Na/Nb notation for paired rows |
| PromoteMergeModal WAC section | Removed (dead code) | No caller passed WAC props |

---

## Problems Discovered & Fixed

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Issue index wrong in BulkModal | `issue.index` = position in `creates[]`/`updates[]`, not in `ops[]` | Reuse `buildOpsIndexMap()` for lookup |
| Blur on WAC auto field → spurious manual switch | CompactCashCell emits on blur even without change | Compare `formatDecimalForDisplay()` strings |
| Warning "no cost basis" in auto mode | Condition checked `draft.cost_basis_override` which is empty in auto | Add `costBasisMode !== 'auto'` guard |
| forcedManual on FX missing | `$effect` called `onModeChange('manual')` | Remove $effect, show informative error only |
| Anti-bounce blocked post-sync re-validate | 10s anti-bounce prevented manual re-trigger | `useValidateScheduler` bypasses antiBounce for `trigger: 'manual'` |
| i18n JSON broken (it/fr/es) | `"promote": {` line deleted during `wac` key insertion | Restored missing line |
| Event picker illeggible | Double emoji, 6 decimals, "—" as not-set | Redesigned dropdown with formatted amounts |

---

## Test Coverage Added

| Suite | File | Tests |
|-------|------|-------|
| E2E WAC FX flow | `frontend/e2e/transactions/tx-wac-fx.spec.ts` | 9 tests (sync modal, qualifying table, tooltip) |
| E2E WAC mode switch | `frontend/e2e/transactions/tx-wac-mode.spec.ts` | 5 tests (blur, edit→manual, toggle, placeholder) |
| Backend WAC FX missing | `test_transactions_wac.py` P29 | Multi-currency missing pair scenario |

---

## Source Files

| Role | Path |
|------|------|
| Root plan (SP-D) | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md` |
| BugfixRound1 | `…/Round6/Bugfix-SPD/plan-R3-SP-D-BugfixRound1.prompt.md` |
| BugfixRound2 | `…/Round6/Bugfix-SPD/plan-R3-SP-D-BugfixRound2.prompt.md` |
| WacCurrency | `…/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrency.prompt.md` |
| WacCurrencyFix | `…/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrencyFix.prompt.md` |
| WacFxEnrich | `…/Round6/Bugfix-SPD/plan-R3-SP-D-WacFxEnrich.prompt.md` |
| WAC service | `backend/app/services/wac_service.py` |
| Financial utils | `backend/app/utils/financial_utils.py` |
| Transaction service | `backend/app/services/transaction_service.py` |
| FormModal | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| WacPreviewSection | `frontend/src/lib/components/transactions/WacPreviewSection.svelte` |
| AssetEventPicker | `frontend/src/lib/components/transactions/AssetEventPicker.svelte` |
| FxSyncModal | `frontend/src/lib/components/fx/FxSyncModal.svelte` |
| ValidateScheduler | `frontend/src/lib/components/transactions/useValidateScheduler.ts` |
| E2E WAC FX | `frontend/e2e/transactions/tx-wac-fx.spec.ts` |
| E2E WAC mode | `frontend/e2e/transactions/tx-wac-mode.spec.ts` |

