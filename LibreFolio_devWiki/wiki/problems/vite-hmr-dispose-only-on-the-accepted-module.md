---
title: "Vite HMR: dispose() runs only on the module an update is accepted through"
category: problem
status: resolved
date: 2026-10-17
tags: [frontend, vite, hmr, vitest, svelte5, dev-only]
related: [concepts/svelte5-runes]
---

# Problem: Vite HMR: `dispose()` runs only on the module an update is accepted through

## Symptom
Lot Z-20 (workstream Z, release 1.3) split the instance block into two modules:
- `instanceBlockState.ts`, a plain module;
- `instanceBlock.svelte.ts`, the layout's reactive face, which subscribes to the plain module when it is imported. H's
  condition: a block marked before the layout loads must be visible.

H's review (17/10) found that a hot update of the face leaves the old copy subscribed, and proposed
`import.meta.hot?.dispose(stop)`. That line would never have run here: an experiment with the repo's Vite showed the
same leak with it and without it.

## Root Cause
- **Vite calls `dispose` on one module only.** In Vite 7.3.5 the client calls the disposer of the module the update is
  accepted through (`dist/client/client.mjs`, `HMRClient.fetchUpdate`: `disposeMap.get(acceptedPath)`), not that of
  every module evaluated again.
- **Here that module is the layout.** The face does not accept its own updates, so `propagateUpdate`
  (`dist/node/chunks/config.js`) walks up to its importers. The boundary is the `(app)` layout, a Svelte component that
  accepts itself. `acceptedPath` is the layout, and the face's `dispose` is registered but never called.
- **The face runs again anyway, and the plain module keeps every old listener.** The layout's new copy imports a new
  copy of the face, which subscribes again. The plain module did not change, so the old listeners stay: they write a
  `$state` that nobody reads any more.
- **Measured with Vite's module runner**, which uses the same `HMRClient` as the browser: a plain module, a face that
  subscribes at import, an importer that accepts itself, three edits of the face. Listeners: 1→2→3→4 with no fix,
  1→2→3→4 with `dispose`, always 1 with the handover below.

A second trap waited in the tests. Vitest 4.1.11 defines `import.meta.hot`, but as a stand-in without `data`:
`createHotContext` in `dist/module-evaluator.js` gives only `accept`, `dispose`, `prune`, `decline`, `invalidate`, `on`
and `send`. So a guard `if (import.meta.hot)` followed by `import.meta.hot.data.x` throws at import time. All 24 cases
of `instanceBlock.test.ts` fell with `TypeError: Cannot read properties of undefined (reading 'stopFollowing')`.

## Solution
Each copy of the module stops the one before it through `import.meta.hot.data`. Vite keys that object by the module's
path, so it survives from one copy to the next (`d49263b0e`, Z-22):

```ts
const stopFollowing = instanceBlockState.subscribe(() => {
    blocked = instanceBlockState.blocked;
});

if (import.meta.hot?.data) {
    import.meta.hot.data.stopFollowing?.();
    import.meta.hot.data.stopFollowing = stopFollowing;
}
```

A build drops the block: Vite defines `import.meta.hot` as `undefined` when it builds.

## Prevention
- **A module that is not an HMR boundary** and that registers, at import, with something that outlives it (a plain
  module's listener set, a bus, `window`): hand the unsubscribe over through `import.meta.hot.data`. Alternatively,
  register under a key, so that the new copy replaces the old one. `registerPortfolioMutationListener(key, …)` works
  that way, which is why the price and FX registries never had this leak.
- **`dispose()` belongs in a boundary**: a module that accepts its own updates (`import.meta.hot.accept()`).
- **Guard on `import.meta.hot?.data`**, not on `import.meta.hot`: Vitest's stand-in has no `data`.

## Impact
Development only. Each hot update of the face added one listener: harmless writes to an orphaned `$state`, and a slow
leak in a long `front dev` session. Nothing reached users, since a production build evaluates the module once. The
experiment and its numbers are in plan 06 of workstream Z, section «Z-22»
(`LibreFolio_developer_journal/Release_2/Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md`).

## Source files
| Role | Path |
|------|------|
| The face, with the handover | `frontend/src/lib/features/instance/instanceBlock.svelte.ts` |
| The plain state and its listener set | `frontend/src/lib/features/instance/instanceBlockState.ts` |
| A keyed registration, with no leak | `frontend/src/lib/stores/portfolio/portfolioMutation.ts` |
| The tests that met Vitest's stand-in | `frontend/src/lib/features/instance/instanceBlock.test.ts` |
