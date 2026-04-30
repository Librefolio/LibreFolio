---
title: "Validate Scheduler Pattern"
category: concept
tags: [frontend, transactions, validation, debounce, scheduling, ux]
related: [features/F-048, concepts/savewithretry-frontend-pattern]
---

# Concept: Validate Scheduler Pattern

## Definition

A reactive validation scheduling system used in transaction modals that combines three trigger modes: **debounce on change** (1s), **idle auto-fire** (60s of inactivity), and **manual button** (always available). Implemented as `useValidateScheduler.svelte.ts` factory.

## Where It Applies

- `TransactionFormModal.svelte` — single-row validation (always < 50 rows → all triggers active)
- `TransactionBulkModal.svelte` — bulk validation with auto-disable above 50 rows

## Behaviour

```
user edits ──▶ debounce 1s ─▶ POST /validate ─▶ update banner + chip
                                      │
                                      ▼
                             set lastValidatedAt
                                      ▲
[⚡ Validate now] click ──────────────┤
                                      │
idle 60s since last change ──────────┘
   (timer reset ONLY on real change, NOT on manual validate click)
   (auto-trigger globally disabled when N > 50 rows)
```

## Key Design Rules

1. **Idle timer resets only on `trigger('change')`** — manual validate does NOT reset the idle timer
2. **N > 50 auto-disable**: debounce and idle triggers are suppressed; only manual `⚡ Validate now` remains
3. **Anti-bounce (10s)**: `draftKey` tracking prevents duplicate requests when content unchanged (added in Round 4)
4. **Commit anti-bounce**: separate `lastCommitDraftKey` + `lastCommitAt` tracking prevents duplicate commits

## API

```ts
createValidateScheduler({
    enabled: () => boolean,       // () => drafts.length <= 50
    debounceMs: 1000,
    idleMs: 60000,
    validateFn: () => Promise<void>,
    draftKey?: () => string,      // JSON snapshot for anti-bounce
    antiBounceMs?: 10000,
}) → {
    trigger(reason: 'change' | 'manual' | 'idle'): void,
    state: $state({ isValidating, lastValidatedAt, issuesCount }),
    dispose(): void,
}
```

## Source files

| Role | Path |
|------|------|
| Scheduler factory | `frontend/src/lib/utils/useValidateScheduler.svelte.ts` |
| FormModal consumer | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| BulkModal consumer | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |

