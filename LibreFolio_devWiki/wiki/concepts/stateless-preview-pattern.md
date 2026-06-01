---
title: "Stateless Preview Pattern — Controlled Components for Computed Values"
category: Concept
tags: [frontend, svelte5, reactivity, pattern, controlled-component, wac]
related_features: [F-097, F-048]
related_problems: [problems/wac-feedback-loop, problems/svelte5-effect-read-write-loop]
---

# Stateless Preview Pattern

## What it is

A component design pattern where components that display **computed/derived values** have NO internal state for those values. Instead, they receive all state as props and communicate changes via callbacks. This eliminates timing bugs caused by `$effect` initialization order and `untrack()` workarounds.

## The Problem It Solves

In Svelte 5, components with internal `$state` initialized from props face timing issues:

```svelte
<!-- BROKEN: internal state initialized at mount, ignores later prop changes -->
<script>
  let { variant } = $props();
  let mode = $state(untrack(() => variant === 'saved' ? 'manual' : 'auto'));
  // mode is now stale if parent changes variant after mount
</script>
```

Symptoms:
- State lost on re-open (component re-renders with stale initial value)
- `$effect` at mount runs AFTER initial render → flicker
- `untrack()` needed everywhere to prevent loops → fragile code

## The Pattern

```svelte
<!-- CORRECT: fully controlled component -->
<script>
  let { mode, onModeChange, result, onResultChange } = $props();
  let isAuto = $derived(mode === 'auto');
  
  function switchToManual() {
    onModeChange?.('manual');  // parent owns state, we just notify
  }
</script>
```

### Data ownership model:
```
Parent (BulkModal/FormModal)
  └── owns: costBasisMode state (per PendingOp)
  └── owns: wacResult (from validate response or _wacCache)
  └── passes: mode prop, result prop
  └── receives: onModeChange callback

Child (WacPreviewSection)
  └── owns: NOTHING related to computed values
  └── owns: UI-only state (e.g. showQualifyingTable toggle)
  └── reads: mode, result as props
  └── calls: onModeChange when user clicks toggle
```

### Cache lives on the data model, not the component:

```typescript
type PendingOp = {
    // ...
    fields: {
        cost_basis_mode?: 'auto' | 'manual';  // authoritative mode
        cost_basis_override?: Currency | null;  // user-entered or applied value
    };
    _wacCache?: WacResultEntry | null;  // persists across re-opens
};
```

## When to Apply

| Scenario | Use stateless pattern? |
|----------|----------------------|
| Component displays computed value (WAC, totals) | ✅ Yes |
| Component has pure UI state (expanded/collapsed) | ❌ No — internal state OK |
| Component state needs to survive re-mount | ✅ Yes — store on data model |
| Component state is ephemeral (search filter text) | ❌ No — internal state OK |

## Key Insight

> The component is a **visualizer**, not a **state owner**. If the value comes from a calculation or network call, the component should not "remember" it — the data model should.

## Source files

| Role | Path |
|------|------|
| WacPreviewSection (controlled) | `frontend/src/lib/components/transactions/WacPreviewSection.svelte` |
| FormModal (mode state owner) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| BulkModal (_wacCache on PendingOp) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
