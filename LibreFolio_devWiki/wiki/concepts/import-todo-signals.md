---
title: "Import Todo Signals"
category: concept
tags: [frontend, brim, import, wizard, warnings, blockers, plugin, signals]
related:
  - entities/import-wizard-modal
  - concepts/workspace-intent-pattern
  - features/F-012
  - features/F-048
---

# Concept: Import Todo Signals

## Definition

`ImportTodo` signals are field-level warnings or blockers emitted by BRIM parser plugins to indicate that a `TXCreateItem` field was intentionally left incomplete (a safe placeholder value was inserted). The user must review and optionally correct these fields in Step 4 of the Import Wizard before confirming the import.

Import Todos are **strictly wizard-local**: they exist only within `ImportWizardModal` and are never propagated into `PendingOp`, `txStore`, or the batch commit payload.

## The Type

```typescript
interface ImportTodo {
    field: string;                     // TXCreateItem field (e.g. 'cost_basis_override')
    severity: 'blocker' | 'warning';   // blocker = import blocked, warning = proceed with caution
    reasonCode: string;                // machine-readable (e.g. 'stock_merger', 'spin_off')
    message: string;                   // human-readable English fallback
    context?: Record<string, unknown>; // i18n params (e.g. {old_ticker: 'CCIV', new_ticker: 'LCID'})
}
```

This mirrors `BrimFieldTodo` from the Zodios-generated backend client schema.

## Where They Come From

Backend BRIM plugins emit `field_todos` inside `BRIMParseResponse` for each row where automated extraction was incomplete or ambiguous. Examples:
- A stock merger/spin-off where the cost basis of the new position is unknown
- A transaction with a date ambiguity
- A fee or tax that can't be attributed to a specific position

## Lifecycle in the Import Wizard

1. **Backend parse** (Step 3): `POST /brim/parse` returns `BRIMParseResponse[]` with `field_todos` per row
2. **Step 4 merge**: `ParsedFileResult.response.transactions` are merged into `MergedTransaction[]`, each with `todos: ImportTodo[]`
3. **Step 4 display**: Rows with blockers show a red badge; warnings show amber. Import button disabled if any `severity='blocker'` remains unresolved.
4. **User review**: User can edit the row's field directly in the review grid, or accept the warning.
5. **On import**: `onImportBatch(items: TXCreateItem[])` fires with the corrected items — todos are NOT included.

## Distinction from `WorkspaceIntent`

| | `ImportTodo` | `WorkspaceIntent` |
|-|-|-|
| Scope | ImportWizardModal (Step 4) | TransactionBulkModal |
| Origin | Backend plugin | User action |
| Lifecycle | Disappears on import | Persists until commit |
| Touches PendingOp? | No | Yes (indirectly) |

## Source files

| Role | Path |
|------|------|
| Import Wizard Modal | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| BRIM API schemas | `backend/app/schemas/brim.py` |
| BRIM parse API | `backend/app/api/v1/brim.py` |
| Coinbase plugin (example) | `backend/app/services/brim_providers/broker_coinbase.py` |
| mkdocs (transaction draft) | `mkdocs_src/docs/developer/frontend/state/transaction-draft.md` |
