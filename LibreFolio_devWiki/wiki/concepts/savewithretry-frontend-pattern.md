---
title: "saveWithRetry — Frontend Modal Save Pattern"
tags: [frontend, pattern, error-handling, modals, ux]
related_features: [F-002, F-003, F-024]
related_sources: [sources/phase07-part3-closure2]
---

# Concept: saveWithRetry — Frontend Modal Save Pattern

## Problem

Before Phase 07 Part 3 (I-bis #22), each modal had its own try/catch pattern for
API calls. Error messages were extracted inconsistently, some modals showed toasts,
others showed inline banners, and several had no error handling at all for edge cases.

## Solution

`saveWithRetry(fn, opts)` — a unified helper in `frontend/src/lib/utils/saveWithRetry.ts`.

```typescript
type SaveResult = { status: 'success'; data: any } | { status: 'error'; message: string };

async function saveWithRetry(
  fn: () => Promise<any>,
  opts: {
    toast?: boolean;          // show success/error toast automatically
    fallback?: string;        // fallback error message if extraction fails
    onError?: (err: any) => boolean;  // true = handled inline, false = bubble to generic
  }
): Promise<SaveResult>
```

### Error extraction

The helper normalizes Zodios errors (structured `detail`, `message` fields) into a
human-readable string. This replaces the inconsistent `.detail`, `.message`, and
`toString()` calls scattered across modals.

### Return value

Always returns a `SaveResult`. The caller checks `result.status === 'error'` and sets
`formError = result.message` for inline display. No unhandled exceptions reach the UI.

### `onError` hook

Per-modal custom handling:
```typescript
onError: (err) => {
  if (err?.response?.status === 409) {
    formError = $t('assets.modal.duplicateName');
    return true;  // handled inline
  }
  return false;  // let generic message show
}
```

## Adopted Modals (Phase 07, 8+ total)

| Modal | File |
|-------|------|
| `BrokerModal` | `frontend/src/lib/components/brokers/BrokerModal.svelte` |
| `CashTransactionModal` | `frontend/src/lib/components/transactions/CashTransactionModal.svelte` |
| `AssetCurrencyChangeModal` | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` |
| `PasswordChangeModal` | `frontend/src/routes/(app)/settings/+page.svelte` or component |
| `FxPairAddModal` | `frontend/src/lib/components/fx/FxPairAddModal.svelte` |
| `BrokerImportFilesModal` | `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` |
| `BrokerSharingModal` | `frontend/src/lib/components/brokers/BrokerSharingModal.svelte` |
| `AssetModal` | `frontend/src/lib/components/assets/AssetModal.svelte` |

## `AssetModal` special case

`AssetModal` has two 409 paths:
1. **Duplicate name** → `formError = $t('assets.modal.duplicateName')` (handled in `onError`)
2. **Currency change with prices** → reconstructs `patchResp` from `detail.results[]` internally
   inside `saveEdit` — NOT surfaced as error, triggers `AssetCurrencyChangeModal` instead

The `saveWithRetry` wrapper wraps the outer `doSave()` call; the 409 currency intercept
runs inside `saveEdit` before control returns to `saveWithRetry`.

## `BrokerImportFilesModal` variants

This modal has 3 call sites, each wrapped differently:
- Upload loop: per-iteration retry, breaks on first error
- Delete single: wraps single call
- Delete multiple: collect-all, summary error `"Failed to delete {count} file(s)"`

## Design principles

- Modal stays open on error (user can fix and retry)
- Draft data is never lost (no reset on error)
- Inline `formError` for actionable errors, toast for transient failures
- Generic fallback message for unexpected errors

## Source files

| Role | Path |
|------|------|
| Helper | `frontend/src/lib/utils/saveWithRetry.ts` |
| AssetModal (complex case) | `frontend/src/lib/components/assets/AssetModal.svelte` |
| BrokerImportFilesModal (3 call sites) | `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` |
