---
title: "TransactionBulkModal mode removal — unified mode-less batch editor"
category: decision
status: resolved
date: 2026-05-07
tags: [frontend, transactions, bulkModal, architecture, simplification]
related:
  - features/F-048
  - features/F-047
  - decisions/unified-batch-pipeline
  - decisions/dual-transaction-form-design
  - sources/phase07-part4-round6-planb23-bulk-delete
---

# Decision: TransactionBulkModal Mode Removal

## Context
`TransactionBulkModal` had a `mode: 'create-many' | 'edit-many'` prop that determined its behavior. The prop impacted 6 code points (primarily `fromTx()`, `$effect` init, `mergePairedRows` condition, `resetRow/resetAll`, dead code `editMode`, and Picker visibility). The parent `+page.svelte` managed a `bulkMode` state with 8 assignments across different handlers.

With the introduction of bulk delete via `initialStatus: 'delete'` (Plan B23), the modal now handles create + edit + delete rows in a single batch. The global `mode` flag became a conceptual contradiction: a batch could contain new drafts, edited DB rows, and rows marked for deletion simultaneously, yet the mode said "you're in create mode" or "you're in edit mode."

## Options Considered
1. **Keep mode** — Continue branching on mode in 6 places. Low effort, but perpetuates a misleading abstraction that doesn't match the modal's actual behavior.
2. **Remove mode, infer per-row** — Each row's role is determined by its data: `tx.id > 0` = DB row (edit/delete), `tx.id ≤ 0` = new draft (create). The commit pipeline already ignores mode — it dispatches by row `status` (new→CREATE, edited→UPDATE, delete→DELETE).

## Decision
Option 2: remove `mode` entirely. The inference pattern `tx.id > 0` is more precise than a global flag because it's per-row. Mixed batches (new + edit + delete rows) are the natural state.

### Specific changes
| Before | After |
|--------|-------|
| `fromTx(tx, mode, overrideStatus?)` branches on mode | `fromTx(tx, overrideStatus?)` branches on `tx.id > 0` |
| `mergePairedRows` gated by `mode === 'edit-many'` | Gated by `rows.some(r => r.id > 0 && r.related_transaction_id != null)` |
| Auto-open FormModal gated by `mode === 'create-many' && rows.length === 0` | Gated by `rows.length === 0` |
| `resetRow`/`resetAll` pass mode to `fromTx` | Call `fromTx(d.original)` — original always has `id > 0` |
| `editMode` derived computed | Removed (was never used in template — dead code) |
| Picker visible only in `edit-many` | Visible when `allMainRows.length > 0` |
| Parent has `bulkMode` state + 8 assignments | No `bulkMode` — `bulkInitial` rows carry all information |

### Total impact
~25 lines removed, 1 prop eliminated, 8 state assignments in parent eliminated. No E2E test changes needed (tests don't interact with the mode prop directly).

## Consequences
- **Simpler mental model**: the modal is a "batch editor" — any row can be any status regardless of how the batch was opened
- **Future-proof**: adding more row states or batch entry points doesn't require a mode enum extension
- **Slightly less explicit intent in parent code**: `bulkMode = 'edit-many'` was self-documenting, now intent is implicit in the shape of `bulkInitial` rows. Acceptable trade-off: the code is more honest about what actually determines behavior.

## Source files

| Role | Path |
|------|------|
| BulkModal | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| Transactions page | `frontend/src/routes/(app)/transactions/+page.svelte` |
| Plan | `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanB23_BulkDeleteViaBulkModal.prompt.md` |

