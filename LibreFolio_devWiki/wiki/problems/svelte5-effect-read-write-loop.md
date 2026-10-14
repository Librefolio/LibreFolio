---
title: "Svelte 5 $effect Read-Write Loop — effect_update_depth_exceeded"
category: problem
status: resolved
tags: [svelte5, frontend, runes, effect, reactivity, infinite-loop]
severity: critical
resolved: true
date: 2026-04-28
related:
  - features/F-047
  - features/F-048
  - sources/phase07-part4-round1
---

# Problem: Svelte 5 $effect Read-Write Loop

## Symptom

```
Uncaught Error: effect_update_depth_exceeded
Maximum update depth exceeded — a reactive update triggered another reactive update more than 1000 times.
```

Application freezes or crashes on open. Browser tab may become unresponsive.

## Trigger

A `$effect` that **reads from a reactive `$state` variable in a `for` loop** AND **writes to that same variable** in the same run. In Svelte 5, when the effect writes the signal it read, it immediately re-queues itself for re-execution, which re-triggers the write, and so on.

Example that caused the bug:
```ts
$effect(() => {
    for (const draft of drafts) {      // ← reads drafts
        if (draft.asset_id === someId) {
            drafts = recalculate(drafts);  // ← writes drafts → retriggers!
        }
    }
});
```

## Root Cause

Svelte 5 rune-based effects track reactive reads and re-run when any read value changes. Writing to a signal that you previously read in the same effect body creates an immediate re-trigger cycle. This is fundamentally different from Svelte 4 `$:` blocks which had explicit cycle detection.

## Fix

Compute the next value into a **local non-reactive variable first**, then assign once:

```ts
$effect(() => {
    const next: DraftRow[] = [];
    const assetIds = new Set<number>();

    for (const draft of drafts) {    // reads drafts (tracked)
        next.push(recalculate(draft));
        assetIds.add(draft.asset_id);
    }

    drafts = next;    // single write at the end, AFTER all reads are done
});
```

## Rule

> In Svelte 5 `$effect`, always collect reads first into local variables, then perform all writes at the end. Never interleave reads and writes of the same signal.

**Applied before the code (2026-10-12, plan 44).** The import wizard needed a counter of broker loads in flight,
incremented by `loadBrokers()`, which runs inside the wizard's opening `$effect`. A `$state` counter would have been
read and written there, and the effect would have started again at every load. The counter is a plain variable, and
the template reads only `brokersLoading` — [[problems/import-wizard-next-before-brokers-loaded]].

## Affected File

- `frontend/src/lib/components/transactions/TransactionStagingModal.svelte` (W1/C1, Round 1)

## Source

W1/C1 documented in:
`LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md`, sub-round 1.2.
