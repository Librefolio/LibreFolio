# Plan — Phase 07 · Part 4 · Round 6 — Context Menu, Delete Riepilogo, Bug Fix & Polish

**Date**: 2026-05-05
**Status**: ⏳ PLANNED
**Priority**: P1 (UX + bug fix)
**Estimated effort**: ~16–20 h

**Parent**: [`plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md`](./plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md)
**Predecessors (all ✅)**:
- Round 5 base: Server-Driven Type Rules + Dual Form
- Bugfix 1: Dual Form & Unified BulkModal Fixes (CASH_TRANSFER, split/promote architecture)
- Bugfix 2: Post-TestWalk Overhaul (BulkModal readonly, FormModal "✓ Applica", dual dates)
- Bugfix 3: TestWalk Fixes (PATCHABLE_FIELDS, type swap backend, TagInput, SafeDecimal, test split)

---

## 📜 Recap Round Precedenti (Round 5 Bugfix 1–3)

### Bugfix 1 — Dual Form & Unified BulkModal Fixes (2026-04-30) ✅

**File**: `plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md`
**Obiettivo**: Fix blocking bugs dual-form + unified BulkModal, add `CASH_TRANSFER` backend type, split/promote architecture.
**Decisioni chiave**:
- **Opzione C approvata**: `TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER` come first-class backend enum values
- **Split/Promote immediati**: dedicated endpoints `POST /tx/split` e `POST /tx/promote`, non deferred nel batch
- **PromotePairWizardModal → rimosso**: sostituito da selezione-based promote flow
**15 step completati** (⚠️ correction: B1-16 "Bulk Split/Promote endpoints" was erroneously marked ✅ — the `SplitMeta`/`PromoteRule` schemas exist but `POST /split` and `POST /promote` API endpoints + service layer were **never implemented**. B1-17 "Remove PromotePairWizardModal" was done (old component deleted) but the replacement selection-based flow depends on B1-16. Both moved to Round 6 Steps 10–12): CASH_TRANSFER enum+metadata, VALID_MIXED_PAIRS rimosso, split/promote type maps metadata, paired row rendering in BulkModal (Da:/A: labels), split/promote metadata schemas in TXTypeMetadata, migration + api sync.

### Bugfix 2 — Post-TestWalk Overhaul (2026-05-02) ✅

**File**: `plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md`
**Obiettivo**: BulkModal fully readonly grid, FormModal unico editing point, edit/clone singoli da main table via BulkModal→FormModal.
**14 step completati**:
1. BulkModal completamente readonly + doppio-click → FormModal
2. Fix `openEditRowForm`: status `new` → mode `create` pre-populated
3. FormModal: pulsante "✓ Applica" quando embeddato
4. FormModal dual: emette coppia completa nel pushDraft
5. Date duali nel form paired
6. Edit/Clone singoli da main table → BulkModal + FormModal
7. Fix BulkDeleteLinkedPairModal i18n + UX singola
8. Fix i18n mancanti (assets.create, form.apply, assetOptional)
9. Fix `↔` prefix non visibile al primo render
10. Fix FX dual form layout overflow desktop
11. Banner validazione verde → inline footer
12. Fix BrokerSearchSelect errori IDE
13. Fix cash-transfer.png non mostrata
14. Documentazione mkdocs (solo EN) + doc_slug backend + api sync

### Bugfix 3 — TestWalk Fixes (2026-05-03, aggiornato 2026-05-04) ✅ (22/25 step, 3 bug → Round 6)

**File**: `plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md`
**Obiettivo**: Fix tutti i bug emersi dal test walk manuale del 2026-05-02.

**Step completati (22/25)**:
| # | Ref | Descrizione | Stato |
|---|-----|-------------|-------|
| 1 | C1 | Fix doppio-click pre-popola FormModal | ✅ |
| 2 | C2 | Fix edit coppia da main table | ✅ |
| 3 | C3 | Fix delete paired new row (entrambe le metà) | ✅ |
| 4 | H1/H2 | Icone asset/broker + rendering duale qty in bulk | ✅ |
| 5 | H3 | Fallback icona broker | ✅ |
| 6 | H4 | Disabilitare auto-validate finché campi incompleti | ✅ |
| 7 | H5 | Label "(opzionale)" su campo asset | ✅ |
| 8 | M1/M2 | Banner validazione dismissable | ✅ |
| 9 | M3 | Allineamento date Da/A | ✅ |
| 10 | M4/M5 | Colonne nascoste di default + ordine cost_basis | ✅ |
| 11 | — | Quick fixes (zod import, as cast, createLabel) | ✅ |
| 14 | C4 | **PATCHABLE_FIELDS allowlist** — strip campi immutabili | ✅ |
| 15 | C5 | **Type swap nel backend** — swap_group + sign-flip | ✅ |
| 16 | M9 | Banner EN "Save cancelled" (non "Commit rolled back") | ✅ |
| 18 | H7 | Colonna Tags nella BulkModal con badge colorati | ✅ |
| 19 | H8 | **TagInput.svelte** — chip input + autocomplete | ✅ |
| 20 | H9 | Titolo FormModal paired: `#ID_A ↔ #ID_B` | ✅ |
| 21 | M8 | Colonna ID `#N` nella tabella principale | ✅ |
| — | — | **SafeDecimal** — systemic fix notazione scientifica Decimal | ✅ |
| — | — | **Test split brokers** + front-broker runner | ✅ |
| — | — | **asset-event-delete.spec.ts** (4 scenari) | ✅ |
| — | — | Fix i18n Save/Import button (`{n}` vs `{count}`) | ✅ |

**Step deferred**:
- 12 (M6): Fix icone documentazione mkdocs → Part 5
- 13 (L4): TODO gallery screenshots TX × lingua → Part 5
- 17 (M10): Nascondere errori `extra_forbidden` → superfluo dopo Step 14

**Bug aperti passati a Round 6**: R7-C1, R7-H1, R7-H2 (vedi sotto).

---

## 🎯 Obiettivo Round 6

1. **ContextMenu riusabile** nella DataTable — right-click desktop, long-press mobile, attivo di default su tutte le tabelle
2. **Fix 3 bug aperti** da Round 7 test walk (R7-C1, R7-H1, R7-H2)
3. **TagInput polish** — keyboard navigation, chip colorati, anti-bounce
4. **Delete riepilogo** — TransactionDeleteModal con layout ricco per singola/paired
5. **Asset cliccabile** — navigazione dal nome asset nella tabella transazioni
6. **Colonna ID filtro range** — NumberFilter min/max sulla colonna #N
7. **TransactionPickerModal** (R6-B.5) — cerca e aggiungi transazioni DB esistenti alla BulkModal
8. **Promote & Split** (R6-B.6/B.7) — backend endpoints + UI in BulkModal e Main Table
9. **Entry point wiring** (R6-B.8) — flusso completo integrato

---

## 📋 Steps

### Step 1 — ContextMenu riusabile nella DataTable (~2h)

**New file**: `frontend/src/lib/components/ui/ContextMenu.svelte`
**Modified**: `frontend/src/lib/components/table/DataTable.svelte`, `frontend/src/lib/components/table/types.ts`

**ContextMenu.svelte** — floating panel:
- Positioned absolutely at `{x, y}` pixel coordinates (passed as props)
- `z-index: 50` (above modals)
- List of actions: each with icon (16px) + label text + optional `variant: 'danger'` (red)
- Click on action → `onaction(actionId)` callback → closes
- Click outside (window `pointerdown`) → closes
- `Escape` key → closes
- Accessibility: `role="menu"` on container, `role="menuitem"` on items
- `data-testid="context-menu"` + `data-testid="context-menu-action-{id}"`
- Styling: white card (dark: slate-800), shadow-lg, rounded-lg, border subtle, min-width 180px
- Separator support: `{ type: 'separator' }` item for visual grouping (hr line)

**DataTable.svelte changes**:
- New prop: `enableContextMenu: boolean = true` (**default ON**)
- State: `contextMenuRow: T | null`, `contextMenuPos: {x: number, y: number} | null`
- On `<tr>` (line 1121): add `oncontextmenu` handler:
  ```ts
  oncontextmenu={(e) => {
      if (!enableContextMenu || rowActions.length === 0) return;
      e.preventDefault();
      contextMenuRow = row;
      contextMenuPos = { x: e.clientX, y: e.clientY };
  }}
  ```
- The `contextmenu` event fires natively on both:
  - **Desktop**: right-click
  - **Mobile**: long-press (~400–500ms, browser-native — no custom `touchstart`/`touchend` timers needed)
- Render `<ContextMenu>` when `contextMenuRow != null`:
  - Actions = `rowActions.filter(a => !a.visible || a.visible(contextMenuRow))` (same filtering as action column)
  - Disabled actions shown greyed out (same `disabled?.(row)` predicate)
  - On action click → call `handleRowAction(action, contextMenuRow)` (reuse existing handler) → close menu
  - On close → `contextMenuRow = null`
- **Active by default on ALL tables** — no changes needed in TransactionsTable, FX, Assets, Brokers consumers. The DataTable enables it automatically when `rowActions.length > 0`.

**Viewport boundary**: ContextMenu auto-adjusts position if it would overflow viewport bottom or right edge. Simple logic: measure menu dimensions after mount, flip to `x - width` / `y - height` if needed.

**Stima**: 2h

---

### Step 2 — R7-C1: Fix edit paired creates → updates (~1h)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Root cause**: When `patchDualRowFromForm()` or `mergePairIntoFromTo()` applies the dual form results to the hidden partner row, the code reconstructs the partner as a fresh draft with `status='new'` and `broker_id=0`. For DB rows (existing transactions), this means `collectUpdate()` skips them (they're `new`, not `edited`) and `collectCreate()` picks them up instead.

**Fix**: In the function that applies dual form edits to the partner draft:
1. Before applying changes, save reference to the original partner draft
2. If original partner has `id > 0` (DB row):
   - Preserve `id`, `status: 'edited'`, and `original` snapshot
   - Apply only the changed fields (broker_id, cash, date, etc.) from the form output
3. If partner is `new` (draft): reconstruct as today (no change)

**Verification**: After fix, edit a TRANSFER pair from the main table → Save → verify payload contains `updates` (not `creates`) for the partner row, with correct `id`.

**Test**: Existing E2E `transactions-modals.spec.ts` should pass. Add assertion: after edit TRANSFER → partner row retains its original ID in the table.

**Stima**: 1h

---

### Step 3 — R7-H1: Type swap qty doesn't update in table (~45min)

**Files**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`, `backend/app/services/transaction_service.py`

**Investigation checklist**:
1. **Backend `_update_single`**: When `type` changes within a swap group (e.g. BUY→SELL), does the service auto-negate `quantity`? Check if the sign-flip logic (added in Bugfix 3 Step 15) fires correctly when `new_type != existing.type` and the type is in the same swap group.
2. **Frontend `buildUpdatePayload`**: When `type` changes in the BulkModal draft, does `quantity` appear in the diff? The draft may show the same absolute value (e.g. `10` for BUY → SELL), but the backend expects a sign flip. If `collectUpdate` compares `draft.quantity === original.quantity` → it won't include `quantity` in the payload → backend won't know to flip.
3. **Frontend reload**: After commit, does the page re-fetch transactions? If `quantity` was flipped server-side but the page shows stale data → refresh issue.

**Likely fix**: In `collectUpdate()`, when `type` has changed, **always include `quantity`** in the payload even if the displayed value hasn't changed — the backend needs to see it to apply the sign flip. Alternatively, the frontend should pre-flip the quantity in the draft when type changes (matching the auto-sign behavior from Step R5-5).

**Stima**: 45min

---

### Step 4 — TagInput: keyboard nav + colored chips + anti-bounce (~1h)

**File**: `frontend/src/lib/components/ui/TagInput.svelte`

**4a — Keyboard navigation**:
- Add state: `let highlightedIndex = $state(-1);`
- In `handleKeydown`:
  - `ArrowDown`: `highlightedIndex = Math.min(highlightedIndex + 1, suggestions.length - 1); dropdownOpen = true;`
  - `ArrowUp`: `highlightedIndex = Math.max(highlightedIndex - 1, -1);`
  - `Enter`: if `highlightedIndex >= 0` → `addTag(suggestions[highlightedIndex]); inputBuffer = ''; highlightedIndex = -1;` else → existing behavior (add typed text)
  - `Escape`: `highlightedIndex = -1; dropdownOpen = false;`
- Reset `highlightedIndex = -1` whenever `inputBuffer` changes (via `$effect`)
- In dropdown rendering (line 130): add class `bg-blue-100 dark:bg-blue-900/50` when `index === highlightedIndex`
- Scroll highlighted item into view: `scrollIntoView({ block: 'nearest' })` on the highlighted button

**4b — Colored chips**:
- Import `getStringColor` from `$lib/utils/colors`
- Line 92: replace static `bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200` with inline style:
  ```svelte
  {@const colors = getStringColor(tag)}
  <span style="background:{colors.bg};color:{colors.text}" ...>
  ```
- Consistent with tag rendering in TransactionsTable and TransactionBulkModal

**4c — Anti-bounce (R7-H2)**:
- Remove the fragile `setTimeout(200)` in `handleBlur` (line 80)
- Add state: `let mouseDownOnDropdown = $state(false);`
- On the dropdown container div (line 129): add `onmousedown={() => mouseDownOnDropdown = true}`
- In `handleBlur`: `if (mouseDownOnDropdown) { mouseDownOnDropdown = false; return; }`
- On `window` via `$effect`: listen for `mouseup` → `mouseDownOnDropdown = false` (cleanup on unmount)
- This ensures: when user clicks a suggestion, the `mousedown` on dropdown fires first → sets flag → `blur` fires → sees flag → skips close → `handleSuggestionClick` fires → adds tag + closes dropdown

**Stima**: 1h

---

### Step 5 — Colonna ID: filtro range min/max (~15min)

**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`

At the `id` column definition (~line 710):
```ts
{
    id: 'id',
    header: 'ID',
    type: 'number',       // was: 'text'
    filterable: true,      // was: false
    sortable: true,
    getValue: (d) => d.tx.id,
    // ...existing cell renderer...
}
```

The `NumberFilter` in `DataTableColumnFilter.svelte` already provides min/max slider UI. No additional work needed.

**TODO futuro** (annotare in codice):
```ts
// TODO: filtro composito multi-range per ID (come currency-stack con range multipli)
```

**Stima**: 15min

---

### Step 6 — Asset cliccabile nella tabella transazioni (~30min)

**Files**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`, `frontend/src/routes/(app)/transactions/+page.svelte`

**TransactionsTable.svelte** — colonna `asset`:
- Wrap the asset HTML with a clickable anchor when `asset_id` is not null:
  ```html
  <a href="/assets/{assetId}" data-asset-navigate="{assetId}" 
     class="hover:underline hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer">
    [icon] display_name
  </a>
  ```
- When `asset_id` is null or the cell shows `—`: no link

**TransactionsTable.svelte** — `handleTableClick` delegation:
- Add handler for `data-asset-navigate`:
  ```ts
  const assetLink = target.closest('[data-asset-navigate]') as HTMLElement | null;
  if (assetLink) {
      ev.preventDefault();
      ev.stopPropagation();
      const assetId = assetLink.getAttribute('data-asset-navigate');
      if (assetId) goto(`/assets/${assetId}`);
      return;
  }
  ```

**+page.svelte** cleanup:
- Remove `handleEventBadgeClick` function (line ~625)
- Remove `onEventBadgeClick={handleEventBadgeClick}` prop from `<TransactionsTable>` (line ~772)

**TransactionsTable.svelte** cleanup:
- Remove `onEventBadgeClick` from Props interface and destructuring
- Remove `onEventBadgeClick?.(tx)` call from `handleTableClick` event badge delegation
- The `●evt` badge remains as a **visual indicator only** with its existing tooltip (emoji + date + amount + notes + ⚙ auto). No click action.

**Stima**: 30min

---

### Step 7 — TransactionDeleteModal con riepilogo ricco (~2.5h)

**New file**: `frontend/src/lib/components/transactions/TransactionDeleteModal.svelte`
**Modified**: `frontend/src/routes/(app)/transactions/+page.svelte`, `frontend/src/lib/i18n/{en,it,fr,es}.json`

**Component design** — `TransactionDeleteModal.svelte`:

Props:
```ts
interface Props {
    open: boolean;
    transaction: TXReadItem;
    partner?: TXReadItem | null;  // if paired, the linked partner
    brokers: BrokerLike[];
    onConfirm: (deletePartner: boolean) => void;
    onCancel: () => void;
}
```

**Layout A — Standalone** (no partner):
```
┌──────────────────────────────────────────────────┐
│  🗑️  Elimina transazione                     [X] │
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Tipo      │ [icon] BUY                       ││
│  │ Data      │ 2025-03-15                       ││
│  │ Asset     │ [icon] VWCE.DE                   ││
│  │ Quantità  │ 10.000                           ││
│  │ Importo   │ 🇪🇺 -1,123.00 EUR                ││
│  │ Broker    │ [icon] Directa                   ││
│  │ Tag       │ [rebalance] [core]               ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│            [Annulla]  [🗑️ Elimina]               │
└──────────────────────────────────────────────────┘
```

**Layout B — Paired** (with partner):
```
┌────────────────────────────────────────────────────┐
│  🗑️  Elimina transazione collegata             [X] │
│                                                    │
│  Questa transazione fa parte di una coppia.        │
│                                                    │
│  ┌────────────────────────────────────────────────┐│
│  │        │ 🔴 Uscita          │ 🟢 Entrata      ││
│  │────────│────────────────────│──────────────────││
│  │ Data   │ 2025-03-15        │ 2025-03-15       ││
│  │ Broker │ [ico] Directa     │ [ico] Degiro     ││
│  │ Importo│ -1,000.00 EUR     │ +1,000.00 EUR    ││
│  └────────────────────────────────────────────────┘│
│                                                    │
│  ┌────── Cosa eliminare? ──────────────────────┐   │
│  │  [Solo questa ●━━━━━━━━━━━━○ Entrambe]      │   │
│  │                                              │   │
│  │  ⚠️ La transazione partner rimarrà orfana.    │   │
│  └──────────────────────────────────────────────┘   │
│                                                    │
│            [Annulla]  [🗑️ Elimina]                  │
└────────────────────────────────────────────────────┘
```

**Slider toggle implementation**:
- Two-option toggle (not a native range input): two buttons styled as a segmented control
- Default: "Entrambe" (safer choice)
- When "Solo questa" selected: warning `⚠️ La transazione partner rimarrà orfana.` appears
- `onConfirm(deletePartner)` receives the choice

**+page.svelte** routing:
- In `onBulkDelete` handler: if exactly 1 row selected:
  - If `related_transaction_id == null` → open `TransactionDeleteModal` (standalone layout)
  - If `related_transaction_id != null` → fetch partner if needed → open `TransactionDeleteModal` with partner (paired layout)
- If N > 1 → existing `BulkDeleteLinkedPairModal` (unchanged)

**i18n keys** (4 locales):
```
transactions.delete.title = "Delete transaction" / "Elimina transazione" / ...
transactions.delete.titlePaired = "Delete linked transaction" / "Elimina transazione collegata" / ...
transactions.delete.pairedIntro = "This transaction is part of a linked pair." / ...
transactions.delete.deleteOnlyThis = "Only this one" / "Solo questa" / ...
transactions.delete.deleteBoth = "Both" / "Entrambe" / ...
transactions.delete.orphanWarning = "The partner transaction will remain orphaned." / ...
transactions.delete.whatToDelete = "What to delete?" / "Cosa eliminare?" / ...
transactions.delete.outgoing = "Outgoing" / "Uscita" / ...
transactions.delete.incoming = "Incoming" / "Entrata" / ...
transactions.delete.fieldType = "Type" / "Tipo" / ...
transactions.delete.fieldDate = "Date" / "Data" / ...
transactions.delete.fieldAsset = "Asset" / "Asset" / ...
transactions.delete.fieldQuantity = "Quantity" / "Quantità" / ...
transactions.delete.fieldAmount = "Amount" / "Importo" / ...
transactions.delete.fieldBroker = "Broker" / "Broker" / ...
transactions.delete.fieldTags = "Tags" / "Tag" / ...
```

**Stima**: 2.5h

---

### Step 8 — Aggiornamento file plan storici (~1h)

**8a — Update `plan-phase07-transaction-Part4.prompt.md`**:
- Change header status from `🔨 IN CORSO` to `✅ COMPLETATO (Steps 1–10 + 6 rounds di bugfix)`
- Add new section after Step 10: `## 🔧 Post-Implementation Rounds` with timeline:

```markdown
## 🔧 Post-Implementation Rounds

| Round | Date | File | Focus | Status |
|-------|------|------|-------|--------|
| 1 | 2026-04-27 | `..._Round1-tableRefactorBugfix.prompt.md` | Table refactor + infinite loop fix + currency-stack filter + tags filter | ✅ |
| 2 | 2026-04-27 | `..._Round2-tableRefactorBugfix.prompt.md` | Cache entity store, currency tooltip, currency-stack per-valuta, linked-pair conditional | ✅ |
| 3 | 2026-04-28 | `..._Round3-stagingModalRewrite.prompt.md` | Staging modal greenfield rewrite → FormModal + BulkModal + PromotePairWizard | ✅ |
| 3.B1 | 2026-04-28 | `..._Round3_Bugfix1-formModalRedesign.prompt.md` | Form/Bulk modal redesign, 422 error display, type change reset | ✅ |
| 3.B2 | 2026-04-29 | `..._Round3_Bugfix2-i18nValidationErrors.prompt.md` | Structured error codes + i18n, frontend resolution via stores | ✅ |
| 4 | 2026-04-29 | `..._Round4_UnifiedBatchPipeline.prompt.md` | Merge 4 mutation endpoints → 2, TXMixedBatch, lenient parse | ✅ |
| 5 | 2026-04-30 | `..._Round5_ServerDrivenTypeRules.prompt.md` | Server-driven type rules, auto-sign, dark mode vibrancy, dual-transaction form | ✅ |
| 5.B1 | 2026-04-30 | `..._Round5_Bugfix1_DualFormAndBulkFixes.prompt.md` | CASH_TRANSFER, split/promote architecture, paired rendering, 15 steps | ✅ |
| 5.B2 | 2026-05-02 | `..._Round5_Bugfix2_PostTestWalkOverhaul.prompt.md` | BulkModal readonly, "✓ Applica", dual dates, edit/clone, i18n, 14 steps | ✅ |
| 5.B3 | 2026-05-03 | `..._Round5_Bugfix3_TestWalkFixes.prompt.md` | PATCHABLE_FIELDS, type swap, TagInput, SafeDecimal, test split, 25 steps | ✅ |
| 6 | 2026-05-05 | `..._Round6_ContextMenuDeletePolish.prompt.md` | ContextMenu, delete riepilogo, R7-C1/H1/H2 fix, TagInput polish | ⏳ |
```

- Update Open Questions: mark #1 (mixed validate) as resolved (Round 4 unified pipeline), #5 (pair-adjacent toggle) as still deferred.
- Update Follow-ups in Step 6 and Step 10: mark closed items, add forward refs to Round 6.

**8b — Update `plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md`**:
- Update R6-B checklist: mark items completed through Bugfix 1-3
- Add section `## Recap Bugfix Rounds (1–3)` with the summaries from §Recap above
- Add section `## Round 6 — Context Menu, Delete, Bug Fix & Polish` with forward link to this file
- Update items still deferred: R6-B.5 (TransactionPickerModal), R6-B.6 (Promote/Split within BulkModal), R6-B.7 (Main table promote/split quick actions), R6-B.8 (entry point wiring) → marked as Part 5

**Stima**: 1h

---

### Step 9 — TransactionPickerModal: cerca e aggiungi TX esistenti (R6-B.5) (~2h)

**Ref**: [`plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` §R6-B.5](./plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md)

**New file**: `frontend/src/lib/components/transactions/TransactionPickerModal.svelte`
**Modified**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`, `frontend/src/lib/components/transactions/TransactionsTable.svelte`

Il pulsante `[🔍 Cerca e aggiungi]` nella toolbar della BulkModal apre una **modale con la stessa `TransactionsTable`** usata nella main page. Permette di cercare transazioni DB non ancora nel batch e tirarle dentro per editarle, collegare come coppia, o marcare per eliminazione.

**TransactionPickerModal.svelte** — Props:
```ts
interface Props {
    open: boolean;
    excludeIds: Set<number>;        // IDs already in bulk grid — hidden from picker
    onAdd: (rows: TXReadItem[]) => void;  // selected rows to add
    onClose: () => void;
}
```

**Design**:
- Riusa `<TransactionsTable>` con nuova prop `pickerMode: boolean = false`
- In `pickerMode`:
  - `selectionMode = 'multi'` (always multi-select)
  - Row actions hidden (no edit/clone/delete/view buttons)
  - `onEventBadgeClick` / `onLinkedPairClick` disabled
  - Double-click = no-op (no view/edit)
  - Rows with `id ∈ excludeIds` → filtered out before rendering
- Linked pairs: selecting one side auto-selects the partner (if partner not in excludeIds)
- Footer: `[Annulla]  [✓ Aggiungi N selezionate]`
- On add: `onAdd(selectedRows)` → BulkModal receives rows → creates `edit` state drafts

**BulkModal integration**:
- Toolbar: add `[🔍 Cerca e aggiungi]` button next to `[+ Nuova riga]`
- State: `pickerOpen: $state(false)`
- `handlePickerAdd(rows)`: for each row:
  - Create draft with `status: 'edited'`, `id: row.id`, `original: {...row}`
  - If row has `related_transaction_id` and partner in `rows` → create paired draft
  - If partner NOT in `rows` but exists → auto-fetch and add as paired
- Dedup: skip if `row.id` already in drafts

**i18n keys** (4 locales):
```
transactions.picker.title = "Select transactions to add" / "Seleziona transazioni da aggiungere" / ...
transactions.picker.addSelected = "Add {n} selected" / "Aggiungi {n} selezionate" / ...
transactions.bulk.searchAndAdd = "Search & add" / "Cerca e aggiungi" / ...
```

**Stima**: 2h

---

### Step 10 — Backend: Split & Promote endpoints (R6-B.6 backend) (~2h)

**Ref**: [`plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md` §Split/Promote Architecture](./plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md)

**Files**: `backend/app/api/v1/transactions.py`, `backend/app/services/transaction_service.py`, `backend/app/schemas/transactions.py`

⚠️ **Gli endpoint split/promote NON esistono ancora nel backend** — erano stati pianificati in Bugfix 1 ma solo la metadata (swap_group, PATCHABLE_FIELDS) è stata implementata. Servono i 2 endpoint immediati.

**`POST /api/v1/transactions/split`** — Scollega una coppia:
```python
class TXSplitRequest(BaseModel):
    items: List[TXSplitItem]  # each item = { id: int } (one half of a pair)

class TXSplitItem(BaseModel):
    id: int  # ID of ONE half — backend finds partner via link_uuid

class TXSplitResultItem(BaseModel):
    from_tx: TXReadItem   # the half that becomes standalone (type mutated)
    to_tx: TXReadItem     # the partner half (type mutated)

class TXSplitResponse(BaseModel):
    results: List[TXSplitResultItem]
    errors: List[str]
```

**Split type mutation map** (deterministic):
| Original type | "From" half → | "To" half → |
|---|---|---|
| `CASH_TRANSFER` | `WITHDRAWAL` | `DEPOSIT` |
| `TRANSFER` | `ADJUSTMENT` (-qty) | `ADJUSTMENT` (+qty) |
| `FX_CONVERSION` | `WITHDRAWAL` (cash neg) | `DEPOSIT` (cash pos) |

Logic: find partner via `link_uuid`, apply type mutation, set `link_uuid = None` and `related_transaction_id = None` on both.

**`POST /api/v1/transactions/promote`** — Collega 2 standalone come coppia:
```python
class TXPromoteRequest(BaseModel):
    items: List[TXPromoteItem]

class TXPromoteItem(BaseModel):
    id_a: int
    id_b: int

class TXPromoteResultItem(BaseModel):
    pair_a: TXReadItem
    pair_b: TXReadItem

class TXPromoteResponse(BaseModel):
    results: List[TXPromoteResultItem]
    errors: List[str]
```

**Promote type mutation map** (inverse of split):
| Standalone types | → Pair type | Validation |
|---|---|---|
| `WITHDRAWAL` + `DEPOSIT` (same currency, diff broker) | `CASH_TRANSFER` | ✅ |
| `ADJUSTMENT` + `ADJUSTMENT` (same asset, diff broker, opposite qty) | `TRANSFER` | ✅ |
| `WITHDRAWAL` + `DEPOSIT` (diff currency, same broker) | `FX_CONVERSION` | ✅ |

Logic: generate `link_uuid`, apply type mutation, set `related_transaction_id` on both.

**After implementation**: `./dev.py api sync` per rigenerare il client TypeScript.

**Stima**: 2h

---

### Step 11 — Promote & Split UI in BulkModal (R6-B.6 frontend) (~1.5h)

**Ref**: [`plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` §R6-B.6](./plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md)

**Modified**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Promote (🔗 Collega coppia)**:
- Condizionale: visibile nella selection toolbar quando esattamente 2 righe selezionate con `status === 'edited'` (DB rows, non new)
- Frontend compatibility check prima di mostrare il pulsante:
  - `transfer_cash`: entrambe unlinked, same currency, different broker, types DEPOSIT+WITHDRAWAL
  - `transfer_asset`: entrambe unlinked, same asset, different broker, types TRANSFER+TRANSFER (o ADJUSTMENT+ADJUSTMENT)
  - `fx`: entrambe unlinked, same broker, different currency, types FX_CONVERSION (o WITHDRAWAL+DEPOSIT)
- Click → `ConfirmModal` stacked (z-index > BulkModal) con riepilogo delle 2 righe + tipo coppia auto-detected
- Conferma → `POST /transactions/promote` → on success: replace 2 drafts with 1 paired draft, refresh

**Split (⛓💥 Scollega)**:
- Row action `⛓💥` visibile solo su righe paired (`related_transaction_id != null`, `status === 'edited'`)
- Click → `ConfirmModal` stacked con riepilogo coppia
- Conferma → `POST /transactions/split` → on success: replace paired draft with 2 standalone drafts, refresh

**i18n keys** (4 locales):
```
transactions.promote.title = "Link as pair?" / "Collegare come coppia?" / ...
transactions.promote.confirm = "Link" / "Collega" / ...
transactions.promote.immediate = "Immediate operation" / "Operazione immediata" / ...
transactions.split.title = "Unlink this pair?" / "Scollegare questa coppia?" / ...
transactions.split.confirm = "Unlink" / "Scollega" / ...
transactions.split.description = "The 2 transactions will become independent rows." / "Le 2 transazioni diventeranno righe indipendenti." / ...
```

**Stima**: 1.5h

---

### Step 12 — Promote & Split in Main Table + Entry Points (R6-B.7/B.8) (~1h)

**Ref**: [`plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` §R6-B.7/B.8](./plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md)

**Modified**: `frontend/src/routes/(app)/transactions/+page.svelte`, `frontend/src/lib/components/transactions/TransactionsTable.svelte`

**Main Table — Promote**:
- In SelectionBar (già in `+page.svelte`): quando 2 righe selezionate + compatibili → mostra `[🔗 Collega come coppia]`
- Same ConfirmModal flow as Step 11 but triggered from `+page.svelte`
- On success → refresh main table, highlight new pair

**Main Table — Split**:
- New row action `⛓💥` in `TransactionsTable.svelte` (stesso array `rowActions`):
  - `visible: (row) => row.tx.related_transaction_id != null`
  - icon: lucide `Unlink` (o `LinkOff`)
  - variant: `'warning'`
- Click → ConfirmModal con riepilogo coppia
- On success → refresh main table, 2 righe indipendenti appaiono

**Entry point summary** (R6-B.8 — tutto il cablaggio):
```
Main Table:
  [+ Aggiungi] → BulkModal (1 empty draft)
  [✎ Edit] (inline) → BulkModal (1 row) → auto-open FormModal
  [📋 Clone] → BulkModal (1 cloned row) → auto-open FormModal
  Selection [✎ Edit bulk] → BulkModal (N rows)
  Selection [🔗 Collega] → ConfirmModal → POST /promote
  Row action [⛓💥] → ConfirmModal → POST /split

BulkModal:
  [+ Nuova riga] → FormModal (create)
  [🔍 Cerca e aggiungi] → TransactionPickerModal → add as edit drafts
  Double-click row → FormModal (edit/create based on status)
  Selection [🔗 Collega coppia] → ConfirmModal → POST /promote
  Row action [⛓💥] → ConfirmModal → POST /split
  [💾 Salva tutto] → POST /commit (creates + updates + deletes mixed)
```

## ✅ Checklist

- [ ] Step 1: ContextMenu.svelte + DataTable integration (default ON, all tables)
- [ ] Step 2: R7-C1 fix — edit paired preserves partner id/status/original
- [ ] Step 3: R7-H1 fix — type swap qty propagation in pipeline
- [x] Step 4a: TagInput keyboard navigation (ArrowDown/Up + Enter on highlight)
- [x] Step 4b: TagInput colored chips via getStringColor()
- [x] Step 4c: TagInput anti-bounce (relatedTarget check replaces setTimeout)
- [x] Step 4d: TagInput ←→ chip navigation + Delete/Backspace on selected chip (ring-2 highlight)
- [x] Step 4e: TagInput chip colors use getStringBadgeStyle() with CSS variables (dark mode + content-based hash)
- [x] Step 5: Colonna ID filterable (NumberFilter min/max, sortable, urlKey sync)
- [x] Step 6: Asset cliccabile (↗ icon on hover, span+data-asset-navigate, goto SPA) + remove onEventBadgeClick
- [x] Step 6b: Full URL filter sync (id, qty, broker multi, asset multi) + race condition fix (skip init emissions)
- [x] Step 6c: navigationStore tracks full URL (pathname+search) — back button preserves filters
- [ ] Step 7: TransactionDeleteModal (standalone + paired layout + slider toggle)
- [x] Step 8a: Update plan-phase07-transaction-Part4.prompt.md con round timeline
- [x] Step 8b: Update plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md con recap + Round 6 link
- [ ] Step 9: TransactionPickerModal — cerca e aggiungi TX DB alla BulkModal (R6-B.5)
- [ ] Step 10: Backend Split & Promote endpoints (R6-B.6 backend)
- [ ] Step 11: Promote & Split UI in BulkModal (R6-B.6 frontend)
- [ ] Step 12: Promote & Split in Main Table + Entry Points (R6-B.7/B.8)

---

## 🔮 Deferred to Part 5

| # | Feature | Note |
|---|---------|------|
| M6 | Fix icone documentazione mkdocs | Docs polish |
| L4 | TODO gallery screenshots TX × lingua | Docs content |
| — | BulkDeleteLinkedPairModal toggle `[⇄]` per-riga | Delete multipla polish |
| — | Multi-range composite ID filter | Advanced filter UX |
| — | Import ▾ menu (BrokerImportFilesModal from /transactions) | Part 5 BRIM |
| — | AssetMatchingWizard (Phase 6 Step 5) | Fake asset ID resolution for BRIM import |

---

## 🧪 Test E2E

| Spec | Cosa copre |
|------|-----------|
| `utility/context-menu.spec.ts` (NEW) | Right-click → menu appears, click action → executes, click outside → closes, Escape → closes. Test on Asset table (most stable). |
| `transactions-modals.spec.ts` (existing) | After R7-C1 fix: verify edit paired preserves IDs. After R7-H1 fix: verify type swap updates qty. |
| `transactions-table.spec.ts` (existing) | After Step 5: verify ID column filter works. After Step 6: verify asset click navigates. |
| `transactions-promote-split.spec.ts` (NEW) | Promote: select 2 compatible → 🔗 → pair created. Split: ⛓💥 on pair → 2 standalone. Both from main table and BulkModal. |
| `transactions-picker.spec.ts` (NEW) | Open picker from BulkModal → search → select → add → rows appear in bulk grid with edit status. |

---

## 🔗 Cross-link

**Parent plan**: [`plan-phase07-transaction-Part4.prompt.md`](./plan-phase07-transaction-Part4.prompt.md)
**Round 5 base**: [`plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md`](./plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md)
**Bugfix 1**: [`plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md`](./plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md)
**Bugfix 2**: [`plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md`](./plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md)
**Bugfix 3**: [`plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md`](./plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md)

---

## 📊 Step Classification — One-Shot vs Detailed Plan

| Step | Descrizione | Tipo | Stima | Stato | Link piano dettaglio |
|------|-------------|------|-------|-------|---------------------|
| 1 | ContextMenu riusabile nella DataTable | 🗺️ Piano | ~2h | ⏳ | |
| 2 | R7-C1: Fix edit paired creates→updates | 🗺️ Piano | ~1h | ⏳ | |
| 3 | R7-H1: Type swap qty non aggiorna | 🗺️ Piano | ~45min | ⏳ | |
| 4a | TagInput keyboard navigation | 🎯 One-shot | ~20min | ✅ | — |
| 4b | TagInput colored chips | 🎯 One-shot | ~15min | ✅ | — |
| 4c | TagInput anti-bounce | 🎯 One-shot | ~10min | ✅ | — |
| 4d | TagInput ←→ chip nav + Del/Back | 🎯 One-shot | ~20min | ✅ | — |
| 4e | TagInput chip colors dark mode fix | 🎯 One-shot | ~10min | ✅ | — |
| 5 | Colonna ID filterable (NumberFilter) + URL sync | 🎯 One-shot | ~20min | ✅ | — |
| 6 | Asset cliccabile (↗ icon) + remove onEventBadgeClick | 🎯 One-shot | ~30min | ✅ | — |
| 6b | Full URL filter sync + race condition fix | 🎯 One-shot | ~30min | ✅ | — |
| 6c | navigationStore full URL → back preserves filters | 🎯 One-shot | ~15min | ✅ | — |
| 7 | TransactionDeleteModal (standalone + paired) | 🗺️ Piano | ~2.5h | ⏳ | |
| 8a | Update plan Part4 con round timeline | 📝 Doc | ~30min | ✅ | — |
| 8b | Update plan Round5 con recap + forward link | 📝 Doc | ~30min | ✅ | — |
| 9 | TransactionPickerModal (R6-B.5) | 🗺️ Piano | ~2h | ⏳ | |
| 10 | Backend Split & Promote endpoints (R6-B.6) | 🗺️ Piano | ~2h | ⏳ | |
| 11 | Promote & Split UI in BulkModal (R6-B.6 FE) | 🗺️ Piano | ~1.5h | ⏳ | |
| 12 | Main Table Promote/Split + Entry Points (R6-B.7/B.8) | 🗺️ Piano | ~1h | ⏳ | |

**Legenda**: 🎯 = implementabile direttamente senza sotto-piano · 🗺️ = richiede investigazione/piano dettagliato · 📝 = solo documentazione

**Note sui piani dettagliati**:
- **Step 1 (ContextMenu)**: nuovo componente + integrazione DataTable + viewport clamping + mobile long-press → serve piano
- **Step 2 (R7-C1)**: debug del flusso `patchDualRowFromForm` → `collectUpdate` → serve indagine del codice BulkModal
- **Step 3 (R7-H1)**: debug pipeline type-swap qty → backend sign-flip vs frontend diff → serve indagine
- **Step 7 (DeleteModal)**: nuovo componente con 2 layout (standalone/paired) + toggle + i18n 4 lingue → serve piano
- **Step 9 (PickerModal)**: nuovo componente + integrazione BulkModal + auto-fetch partner → serve piano
- **Step 10-12 (Split/Promote)**: 2 endpoint backend + 2 UI flow (BulkModal + MainTable) + entry point wiring → serve piano unico


---

Raggruppamento e ordine di dipendenza

Analizzando le dipendenze tra gli step rimanenti:

Step 1 (ContextMenu)          ← indipendente, nessuna dipendenza
Step 2 (R7-C1 fix paired)     ← indipendente
Step 3 (R7-H1 fix qty swap)   ← indipendente

Step 7 (DeleteModal)           ← indipendente (ma beneficia del ContextMenu per l'entry point)

Step 9 (PickerModal)           ← indipendente
Step 10 (Backend split/promote) ← indipendente
Step 11 (Split/Promote UI Bulk) ← DIPENDE da Step 10
Step 12 (Split/Promote Main)    ← DIPENDE da Step 10 + Step 11

Piani suggeriti (3 anziché 7)
Piano | Steps | Motivazione | Stima
Piano A — ContextMenu + bugfix | 1 + 2 + 3 | Step 1 crea il ContextMenu, Step 2-3 sono bugfix indipendenti. Raggrupparli evita 3 cicli plan/execute separati. Nessuna dipendenza incrociata.| ~3.5h |
Piano B — Delete + Picker modals | 7 + 9 | Due nuovi componenti modali, entrambi standalone. Simile pattern (nuova modale → integrazione +page.svelte). Parallelizzabili ma condividono i18n e pattern. | ~4.5h |
Piano C — Split/Promote full stack | 10 → 11 → 12 | Chain stretta: backend endpoints → UI BulkModal → UI Main Table + wiring. Un unico piano sequenziale. | ~4.5h |

Ordine di esecuzione consigliato
1. Piano A (ContextMenu + bugfix 2,3)   — sblocca UX base, fix bug critici
2. Piano B (DeleteModal + PickerModal)   — nuove modali, user-facing
3. Piano C (Split/Promote full stack)    — feature più complessa, ultima

