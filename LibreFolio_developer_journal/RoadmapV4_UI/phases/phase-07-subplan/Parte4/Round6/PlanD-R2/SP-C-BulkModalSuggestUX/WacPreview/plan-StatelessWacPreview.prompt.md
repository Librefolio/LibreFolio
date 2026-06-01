# Plan: Stateless WacPreviewSection + Mode Persistence Fix

> **Parent**: [plan-FixWacPartnerRows.prompt.md](./plan-FixWacPartnerRows.prompt.md) (Addendum Bug 12+13)
> **Type**: Bugfix — Phase continuation
> **Status**: ✅ COMPLETED (2026-05-30)

---

## Problem Statement

When a paired TRANSFER is set to Manual mode (e.g. "30 USD") via FormModal, Apply correctly updates the BulkModal cell. But **re-opening** the FormModal always shows Auto mode + empty value.

### Root Causes

| # | Cause | Location |
|---|-------|----------|
| A | **Value reads from wrong field**: `WacPreviewSection value={draft.cost_basis_override}` reads the SENDER (always null — `applyPartnerToDualTo` L490 nullifies it). The receiver's value lives in `dualTo.cost_basis_override`. | FormModal L1566 |
| B | **Mode never restored**: `costBasisMode` defaults to `'auto'` and is never set from the receiver's actual `fields.cost_basis_mode`. | FormModal L270 |
| C | **Timing/untrack**: WacPreviewSection uses `untrack()` at mount (L94) — reads `variant` once, ignores later changes. `$effect` at L303 runs AFTER mount. | WacPreviewSection L94 |

### Design Decision

Instead of patching timing issues, make **WacPreviewSection a fully controlled component** (mode from parent, no internal state). This eliminates the timing problem systemically and makes the visualizer stateless.

---

## Approach: Controlled Component + Receiver State Forwarding

1. WacPreviewSection receives `mode` as a prop (parent-owned)
2. FormModal reads receiver's `cost_basis_mode` on open → drives `costBasisMode` state
3. WAC result cached on PendingOp → survives re-opens without relying on the separate Map

---

## Implementation Steps

### Phase A: TXReadItem carries `cost_basis_mode`

- [ ] **A1** — Add `cost_basis_mode?: 'auto' | 'manual' | null` to `TXReadItem` interface (`types.ts`)
- [ ] **A2** — Map it in `opToTxLike` (BulkModal ~L509): `cost_basis_mode: d.fields.cost_basis_mode`

### Phase B: WacPreviewSection becomes controlled

- [ ] **B1** — Replace `variant: 'auto-new' | 'saved'` prop with `mode: 'auto' | 'manual'` prop
- [ ] **B2** — Remove internal `let mode = $state<WacMode>(untrack(...))` (line 94)
- [ ] **B3** — Update `setAutoMode()` + `switchToManual()` — only call `onModeChange()`, no local state mutation
- [x] **B4** — `isAuto` derived directly from prop: `let isAuto = $derived(mode === 'auto')`
- [x] **B5** — Remove all `untrack` patterns related to variant/mode initialization
- [x] **B6** — Verify `$effect` for externalResult sync (L113-130) still works with prop-based `mode`

### Phase C: FormModal derives mode from receiver state

- [x] **C1** — In `$effect` on open (L303), after `applyPartnerToDualTo`, set `costBasisMode` from injected partner
- [x] **C2** — Copy `dualTo.cost_basis_override` → `draft.cost_basis_override`
- [x] **C3** — Updated all WacPreviewSection invocations (3 in FormModal + 1 in PromoteMergeModal)
- [x] **C4** — `onModeChange` callbacks verified

### Phase D: WAC cache on PendingOp

- [x] **D1** — Added `_wacCache?: WacResultEntry | null` to PendingOp type
- [x] **D2** — Validate handler stores WAC cache on the op (piggybacks on existing ops.map)
- [x] **D3** — `getWacResult` callback uses fallback chain: Map → partner._wacCache → self._wacCache

### Phase E: Tests + Verification

- [x] **E1** — All `variant=` usages updated to `mode=` (incl. PromoteMergeModal)
- [x] **E2** — FM E2E tests pass without changes (assertions still valid)
- [x] **E3** — `npx svelte-check`: 0 errors
- [x] **E4** — FM tests: 18/18 pass (9 × desktop+mobile)
- [ ] **E5** — Run: WB tests (7/7 pass)
- [ ] **E6** — Manual walktest:
  1. Create paired TRANSFER → FormModal shows Auto + WAC data ✓
  2. Switch to Manual → type "30" → Apply → cell shows "30 USD" ✓
  3. Re-open same row → FormModal shows **Manual** + "30" + table ✓
  4. Switch back to Auto → Apply → cell shows WAC auto value ✓

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/lib/components/transactions/types.ts` | Add `cost_basis_mode` to TXReadItem |
| `frontend/src/lib/components/transactions/WacPreviewSection.svelte` | Controlled mode: variant→mode prop, remove internal state |
| `frontend/src/lib/components/transactions/TransactionFormModal.svelte` | C1-C4: read receiver mode on open, pass mode prop |
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | A2: opToTxLike; D1-D3: _wacCache |
| `frontend/e2e/transactions/tx-wac-formmodal.spec.ts` | E1-E2: update test assertions |

## Risk Notes

- **WacPreviewSection API break** — `variant` → `mode`. Must grep ALL usages.
- **`onCostBasisChange` writes to `draft.cost_basis_override`** — correct for `buildDualCreatePayloads` (reads from there for receiver payload). C2 ensures initial value is visible.
- **`wacResults` Map kept** — `_wacCache` is fallback layer; Map is still primary for fresh validate results.
- **showQualifying** state in WacPreviewSection remains internal (not controlled) — it's a pure UI toggle.

---

## Walktest Results (2026-05-30)

- ✅ Mode persistence: Manual 30 → Apply → re-open → shows Manual + 30
- ✅ Auto recalculation: adding a BUY updates the WAC value reactively
- ⚠️ **New Bug Found**: Qualifying table shows batch-pending tx with DB ID (e.g. "75") instead of pending indicator (●). See below.

---

## Discovered Bug: Pending TX Indicator in Qualifying Table — ✅ FIXED (2026-06-01)

**Symptom**: When a BUY is added in the same batch, its qualifying_txs entry shows `tx_id: 75` (the temp DB ID) and renders as a regular row, instead of showing `●` with indigo background.

**Fix implemented (Option B — Frontend)**:

1. **BulkModal validate handler**: extracts `pendingIdOps` Map from `results[].ids[]`, annotates `qualifying_txs` with `is_pending: true` + `pending_op: 'create'|'update'`
2. **Reactive `pendingTxIds` Set**: updated after every validate, passed as prop through FormModal → WacPreviewSection for render-time annotation (eliminates timing issues)
3. **WacPreviewSection template**: `{@const isPending = qtx.is_pending || pendingTxIds?.has(qtx.tx_id)}` — dual check (annotation + prop)
4. **Tooltip on ●**: Tooltip with i18n text distinguishing create vs edit (4 languages)

---

## Additional Fixes (2026-06-01)

### Mode Persistence v2 — auto→manual over-correction

**Symptom**: After auto-validate writes WAC into `fields.cost_basis_override` (for DataTable cell display), re-opening FormModal always showed Manual mode.

**Root cause**: `costBasisMode = draft.cost_basis_override ? 'manual' : 'auto'` was truthy because auto-computed WAC was stored in `cost_basis_override`.

**Fix**: Use `row.cost_basis_mode` as authoritative source when explicitly set:
```ts
costBasisMode = (row.cost_basis_mode === 'manual' || row.cost_basis_mode === 'auto')
    ? row.cost_basis_mode : 'auto';
```
Applied in all 4 init paths (L346, L368, L394, L417, L420).

### UX: Validate hints

1. **Auto mode, no result yet**: 💡 "Complete the fields and validate to calculate WAC"
2. **Qualifying table lightbulb tooltip**: "⚡ Validate now to recalculate the table"

---

## Status: ✅ ALL BUGS FIXED — Tests pending

All walktest scenarios pass manually. E2E tests to be added below.

---

## Phase F: E2E Test Coverage

New tests to add in existing spec files. These cover the manual walktest scenarios that caught the bugs.

### `tx-wac-bulk.spec.ts` additions

| ID | Title | Steps | Assertion |
|----|-------|-------|-----------|
| WB8 | Mode persistence re-edit: manual stays manual | 1. Create TRANSFER pair (auto) → Apply 2. Re-edit receiver → toggle Manual, enter "30" → Apply 3. Re-edit receiver again | Toggle shows Manual selected, input has "30" |
| WB9 | Mode persistence re-edit: auto stays auto | 1. Create TRANSFER pair (auto) → Apply 2. Wait for auto-validate 3. Re-edit receiver | Toggle shows Auto selected (not Manual despite cost_basis_override being populated by auto-calc) |
| WB10 | Pending indicator ● in qualifying table | 1. Create BUY → Apply 2. Create TRANSFER pair (auto) → Apply 3. Wait for validate 4. Edit TRANSFER → expand qualifying table | BUY row shows `●` instead of numeric tx_id, has `bg-indigo` row class |

### `tx-wac-formmodal.spec.ts` additions

| ID | Title | Steps | Assertion |
|----|-------|-------|-----------|
| FM10 | ADJUSTMENT mode persist: manual stays manual | 1. Create ADJUSTMENT+ (auto) → Apply 2. Re-edit → toggle Manual, enter "50" → Apply 3. Re-edit again | Toggle shows Manual, input has "50" |

### Implementation notes

- All tests use `data-testid` selectors (never CSS/text)
- WB8/WB9/FM10: check toggle button state via class `font-medium` on active toggle
- WB10: locate qualifying table via `[data-testid="tx-form-cost-basis-qualifying-table"]`, check first cell text content
- Tooltip test (WB11) skipped — hover assertions are fragile in Playwright
