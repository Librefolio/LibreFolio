---
title: "LiveTicker in Header Causes Navigation Crash"
category: problem
status: resolved
date: 2026-04-10
tags: [frontend, liveticker, navigation, crash]
related_features: [F-004]
---

# Problem: LiveTicker in Global Header Caused Navigation Crashes

## Symptom
When `<LiveTicker />` was placed in `Header.svelte` (global layout), navigating between pages caused crashes. The component's polling intervals and reactivity conflicted with SvelteKit's page lifecycle during navigation.

## Root Cause
The LiveTicker component uses `setInterval` for periodic price fetching. When placed in a layout component that persists across navigation, the interval continued running while the page context changed, causing stale state updates and reactivity errors.

## Solution
LiveTicker is placed **only in page-level components** where it mounts/unmounts with the page:
- `dashboard/+page.svelte` — full ticker for all assets
- `assets/[id]/+page.svelte` — single-asset badge
- `assets/+page.svelte` — inline price in `AssetCard` (via prop, no separate component)

`Header.svelte` was restored to its pre-LiveTicker state.

## Prevention
**Rule**: components with active polling (`setInterval`, `$effect` loops, WebSocket subscriptions) must **not** be placed in layout components (`+layout.svelte`). They should only live in page-level components where SvelteKit controls mount/unmount cleanly.

## Source
`changelog_2026-04-10_live-ticker-and-provider-lifecycle.md` — "NON nell'header globale (causava crash di navigazione)"

## Source files

| Role | Path |
|------|------|
| LiveTicker component | `frontend/src/lib/components/layout/LiveTicker.svelte` |
| Header component | `frontend/src/lib/components/layout/Header.svelte` |
| Navigation store | `frontend/src/lib/stores/navigationStore.ts` |
