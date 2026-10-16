---
title: "Broker icon race condition (ensurePluginIconsLoaded)"
category: problem
status: open
date: 2026-06-25
updated: 2026-10-12
tags: [frontend, broker-icon, race-condition, async, plugin-icons, svelte5]
related:
  - sources/phase-final-bugs-2026-06-25
  - features/F-012
  - problems/late-img-error-marked-the-visible-icon-failed
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

## Resolution where it was seen in June (verified on the code, 2026-10-12)

Both forms are closed in the places where they were seen in June:

- **Form A** — commit `7bae73b74` (2026-06-25, the QA session that found it): `files/+page.svelte` awaits
  `ensurePluginIconsLoaded()`, and `BrokerInfo` gained `default_import_plugin`, so a broker known only by its plugin
  reaches the plugin step.
- **Form B** — the transactions page awaits the cache and then sets `pluginIconsReady` (option 2 above). The other
  icons go through the shared reactive chain `brokerIconChain.svelte.ts` (`ddffb5273`, 2026-06-26), which updates its
  own state when the cache arrives, so the derived URL list is computed again. `ensureBrokersLoaded()` and
  `refreshAllBrokers()` in `brokerStore.ts` start the cache for every consumer — the app-level call that Prevention
  asks for.

## Still open (2026-10-12)

The developer saw the symptom again on 2026-10-12, on the build of train 38 (relayed by the coordinator):

- **the large icon on a broker's page** stays the briefcase until the page is reloaded (F5) — the developer's UI
  notes of the morning;
- **the Dashboard's broker selector**: the icon does not load the first time the selector opens — item 27 of the
  developer's server checklist.

It is symptom 3 above, with another cause. The coordinator's diagnosis, consistent with the code: when its props carry
no icon field, `BrokerIcon.svelte` calls `ensureBrokerIconFieldsLoaded(brokerId)` (`brokerStore.ts`), which fetches
the broker and merges it into the store; but its icon chain reads only the props (`iconUrl`, `portalUrl`,
`pluginCode`), so the store fills up and the props never change. Assigned to workstream I, in the UI polish lot.

*Update (train 72)*: both symptoms had another cause. A late `error` event from a replaced `<img>` marked the plugin
icon as failed, and the plugin state started from `null` even with a warm cache; fixed in `2412c3fe4` —
[[problems/late-img-error-marked-the-visible-icon-failed]]. The diagnosis above was not the cause; it survives as the
latent C-56 below.

Two neighbouring items from I's analysis of 2026-10-12 are in the post-1.2 backlog, section C: **C-56** (the same
chain does not read the store when its props are empty — latent, since every surface passes full props today; keep
`settledIconFieldIds`, which stops the loop) and **C-57** (`ensurePluginIconsLoaded` in `brokerHelpers.ts` never retries
after a failed first request, so plugin icons stay missing until the page reloads — to verify).

*2026-10-13*: another way to the fallback icon, from outside the app — a broker's site that answers the browser with a
bot check: [[problems/schwab-favicon-blocked-by-orb]].

## Prevention

- Any page that displays broker icons must call `ensurePluginIconsLoaded()` in `onMount` AND ensure its derived computations that use plugin icons re-run after the call resolves.
- `ensurePluginIconsLoaded` should be called once at app level (app shell / layout +page.svelte) to avoid the per-page pattern.

## Impact

Visual only — colored dots instead of brand icons. Confusing UX when users have broker-only plugin icons (no `icon_url` or `portal_url` configured).

## Source files

| Role | Path |
|------|------|
| brokerHelpers | `frontend/src/lib/utils/broker/brokerHelpers.ts` |
| FilesTable | `frontend/src/lib/features/files/FilesTable.svelte` |
| files page (missing call) | `frontend/src/routes/(app)/files/+page.svelte` |
| transactions page (race) | `frontend/src/routes/(app)/transactions/+page.svelte` |
| dashboard page (race) | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| The shared reactive icon chain (Form B fix) | `frontend/src/lib/utils/broker/brokerIconChain.svelte.ts` |
| The store that starts the plugin-icon cache; `ensureBrokerIconFieldsLoaded` | `frontend/src/lib/stores/reference/brokerStore.ts` |
| C-56, latent: the chain reads only the props | `frontend/src/lib/components/ui/display/BrokerIcon.svelte` |
