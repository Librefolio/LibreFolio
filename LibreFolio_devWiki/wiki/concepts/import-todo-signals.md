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

`ImportTodo` signals are field-level warnings or blockers emitted by BRIM parser plugins to indicate that a `TXCreateItem` field was intentionally left incomplete (a safe placeholder value was inserted). The user reviews them in the Import Wizard (the correction step and the parse detail) and again in the transaction bulk editor.

Import Todos **travel with their rows into the bulk editor**: `onImportBatch` hands over `{tx, todos}` pairs and the editor keeps them on the op (`op.todos`). There a `blocker` disables **Save All**, a `warning` is listed in the save-gate confirmation, both banners link each todo to its row, and filling the field clears the todo (`remainingTodos`). They are never sent in the commit payload.

## The Type

```typescript
interface ImportTodo {
    field: string;                     // TXCreateItem field (e.g. 'cost_basis_override')
    severity: 'blocker' | 'warning';   // blocker = import blocked, warning = proceed with caution
    reasonCode: string;                // machine-readable (e.g. 'stock_merger', 'spin_off')
    message: string;                   // the plugin's own wording, in the language of the parsed file
    context?: Record<string, unknown>; // i18n params (e.g. {old_ticker: 'CCIV', new_ticker: 'LCID'})
}
```

This mirrors `BrimFieldTodo` from the Zodios-generated backend client schema.

## Wording and localisation

Every surface resolves the text the same way (`resolveBrimTodoMessage` in `resolveBrimNotice.ts`, the notices' contract): `importWizard.brimNotice.<reasonCode>`, with `context` as values, replaces the plugin's wording in the UI language when the key exists; otherwise the plugin's `message` is shown as written. Plugins of a single-language bank write in that language on purpose (Crédit Agricole in Italian, Danske Bank in Finnish), so a key is added only when the message has no file language to honour — the Generic CSV's `corporate_action`. Until 2026-10 the bulk editor printed `message` directly, so no key reached it.

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
5. **On import**: `onImportBatch(creates: Array<{tx, todos}>)` hands the corrected items to the bulk editor **with their remaining todos**, which keep gating and guiding there (see the Definition).

## Distinction from `WorkspaceIntent`

| | `ImportTodo` | `WorkspaceIntent` |
|-|-|-|
| Scope | Import Wizard, then the bulk editor | TransactionBulkModal |
| Origin | Backend plugin | User action |
| Lifecycle | Cleared when its field is filled, or dropped at commit | Persists until commit |
| Touches PendingOp? | Yes (`op.todos`), never the commit payload | Yes (indirectly) |

## Source files

| Role | Path |
|------|------|
| Import Wizard Modal | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| Bulk editor (banners, save gate) | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Todo wording resolver | `frontend/src/lib/utils/transactions/resolveBrimNotice.ts` |
| Parse merge (`field_todos` → `ImportTodo`) | `frontend/src/lib/utils/transactions/importMerge.ts` |
| Todo clearing | `frontend/src/lib/utils/transactions/bulkTodos.ts` |
| BRIM API schemas | `backend/app/schemas/brim.py` |
| BRIM parse API | `backend/app/api/v1/brokers.py` |
| Coinbase plugin (example) | `backend/app/services/brim_providers/broker_coinbase.py` |
| mkdocs (transaction draft) | `mkdocs_src/docs/developer/frontend/state/transaction-draft.md` |
