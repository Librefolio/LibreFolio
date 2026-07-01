---
title: "Broker icon race condition (ensurePluginIconsLoaded)"
category: problem
status: open
date: 2026-06-25
tags: [frontend, broker-icon, race-condition, async, plugin-icons, svelte5]
related:
  - sources/phase-final-bugs-2026-06-25
  - features/F-012
---

# Problem: Broker Icon Race Condition

## Symptom

Broker icons show only a colored dot (fallback) instead of the correct icon in three locations:
1. `/files?tab=brim` — FilesTable: all broker icons are dots
2. `/transactions` sidebar filter panel: some brokers (e.g., Recrowd) show only dot
3. Dashboard home broker filter: some brokers show only dot

The issue: the 3-step icon chain `icon_url → portal_url/favicon → plugin_icon` fails at step 3.

## Root Cause

`getBrokerIconUrl()` is a **synchronous** function that reads `_pluginIconCache` (a `Map` loaded asynchronously by `ensurePluginIconsLoaded()`). The race condition has two forms:

**Form A — Missing call** (`/files`): `ensurePluginIconsLoaded()` is never called in `files/+page.svelte` or `FilesTable.svelte`. `_pluginIconCache` is `null` forever. `getPluginIconUrl()` returns `null` → colored dot.

**Form B — Read before resolve** (transactions, dashboard): `ensurePluginIconsLoaded()` IS called, but broker icon cells/filter options are computed as Svelte 5 `$derived` values that execute synchronously before the async Promise resolves. By the time the Promise settles and fills the cache, the derived has already computed with `null`.

## Solution (proposed)

**For Form A**: Add `await ensurePluginIconsLoaded()` in `onMount` of `files/+page.svelte` (or `FilesTable.svelte`).

**For Form B**: Ensure broker filter options re-derive AFTER Promise settlement. Options:
1. Move the derived that computes filter options inside an `{#await}` block / `$effect` that triggers after `ensurePluginIconsLoaded()` resolves
2. Or expose a reactive boolean `pluginIconsLoaded = $state(false)` set after `ensurePluginIconsLoaded()` resolves; derived reads this boolean to trigger re-computation

## Prevention

- Any page that displays broker icons must call `ensurePluginIconsLoaded()` in `onMount` AND ensure its derived computations that use plugin icons re-run after the call resolves.
- `ensurePluginIconsLoaded` should be called once at app level (app shell / layout +page.svelte) to avoid the per-page pattern.

## Impact

Visual only — colored dots instead of brand icons. Confusing UX when users have broker-only plugin icons (no `icon_url` or `portal_url` configured).

## Source files

| Role | Path |
|------|------|
| brokerHelpers | `frontend/src/lib/utils/brokerHelpers.ts` |
| FilesTable | `frontend/src/lib/components/files/FilesTable.svelte` |
| files page (missing call) | `frontend/src/routes/(app)/files/+page.svelte` |
| transactions page (race) | `frontend/src/routes/(app)/transactions/+page.svelte` |
| dashboard page (race) | `frontend/src/routes/(app)/dashboard/+page.svelte` |
