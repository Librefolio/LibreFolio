---
title: "Svelte 5 Runes Convention"
category: concept
tags: [frontend, svelte, runes, state-management]
related_features: [F-004, F-037]
---

# Concept: Svelte 5 Runes Convention

## Definition
New components in LibreFolio use **Svelte 5 Runes** syntax for reactivity. The old Svelte 4 reactive syntax (`$:`, `let` + `bind:`) is deprecated and must not be used in new code.

## The convention

```svelte
<!-- ✅ Svelte 5 Runes (new components) -->
let count = $state(0);
let doubled = $derived(count * 2);
$effect(() => {
    console.log('count changed:', count);
});

<!-- ❌ Svelte 4 (do not use in new code) -->
let count = 0;
$: doubled = count * 2;
$: console.log('count changed:', count);
```

## Where runes are used
- All new components created from Phase 5 onward
- `.svelte.ts` stores use runes (e.g. `chartSettingsStore.svelte.ts`, `toastStore.svelte.ts`)
- Older components (Phase 0–4) may still use Svelte 4 syntax — acceptable, no forced migration

## Known traps (filed problems)
- An `$effect` that reads and writes the same state loops: [[problems/svelte5-effect-read-write-loop]].
- Props are getters, so an effect re-runs whenever the object it reads them from is rebuilt — with a store that
  bumps its version on every merge this became a request loop: [[problems/broker-icon-fields-request-loop]].
- A teardown reads `$state` as it was before its last write, so timer handles belong in plain variables:
  [[problems/svelte5-teardown-reads-stale-state-timers]].

## Tailwind v4 parallel convention
Tailwind CSS 4 config lives in `app.css` via `@theme {}` — **not** `tailwind.config.ts`:
```css
@theme {
    --color-libre-green: #1a4031;
    --color-libre-beige: #f5f4ef;
}
```

## Source
`LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` — "Svelte 5 Runes" section

## Source files

| Role | Path |
|------|------|
| Chart settings store (runes) | `frontend/src/lib/stores/chartSettingsStore.svelte.ts` |
| Toast store (runes) | `frontend/src/lib/stores/app/toastStore.svelte.ts` |
| App CSS | `frontend/src/app.css` |
| mkdocs | `mkdocs_src/docs/developer/frontend/state/index.md` |
