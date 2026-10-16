---
title: "A late `error` event from a replaced `<img>` marked the visible broker icon as failed: the briefcase stayed until F5"
category: problem
status: resolved
date: 2026-10-12
tags: [frontend, broker-icon, svelte5, img, events, race-condition, cache, workstream-i, release-1.2]
related:
  - problems/broker-icon-race-condition
  - features/F-012
  - sources/phase00-ui-polish-2026-10
---

# Problem: an event that belonged to another image

## Symptom

The developer, 2026-10-12, verbatim: «l'icona del broker, anche se impostata, la prima volta che la pagina lo apre
mostra la valigetta, poi si fa f5 e l'icona compare, ma solo per l'icona grande… stesso difetto in broker global»
("the broker's icon, even when set, shows the briefcase the first time the page opens it; after F5 it appears, but
only for the large icon… the same defect in the brokers list"). The Dashboard's broker selector did the same on its
first load. Release 1.1.0 did not have it.

## Root Cause

Workstream I's hypothesis H1, confirmed (plan 48):

- the plugin state `pluginIconUrl` started at `null` even when the plugin-icon cache was already warm, so the first
  render tried the broker's favicon;
- when the plugin icon arrived, the `{#key}` block created a second `<img>`, but the detached favicon `<img>` kept its
  listener (Svelte 5's `$.event`), so its `error` could arrive afterwards;
- `handleError()` marked the **current** candidate as failed — the plugin icon, not the URL that had failed — and the
  chain fell to the briefcase;
- `failedUrls` was reset only when the props changed: nothing changed until F5.

With a working favicon the same race was only cosmetic. The diagnosis written when the symptom was first reported
(the chain reads only its props — [[problems/broker-icon-race-condition]]) was not the cause.

## Solution

`2412c3fe4` («fix(brokers): plugin icon first, late img events», train 72), in
`frontend/src/lib/utils/broker/brokerIconChain.svelte.ts`:

- **each event belongs to its own image**: `eventUrl(event)` reads `currentTarget.getAttribute('src')`; `handleError`
  marks the URL that failed and resets `imageLoaded` only if that URL is the one on screen, and `handleLoad` counts
  only for it;
- **the plugin state starts from the cache**, synchronously (`getPluginIconUrl`, `isFallbackPluginCode`), so a warm
  cache draws the plugin icon at once.

`BrokerIcon.test.ts` (3 cases) and one more case in `brokerIconChain.test.ts`: 4 red before the fix, 9 green after;
`front-broker broker-unit` 57 passed.

## Prevention

- A handler bound to a DOM element must ask which element fired: when an element is replaced, its late events still
  arrive, and «the current candidate» is no longer the one they are about.
- Start a state from what is already known (a warm cache) rather than from `null`: the empty first render is what
  opened the window for the race.
- Still open, outside this fix (backlog, after 1.2): C-56 (the chain does not read the store when its props are
  empty) and C-57 (the plugin-icon list is never requested again after a failed first request).

## Source files

| Role | Path |
|------|------|
| The icon chain (`eventUrl`, `handleError`, `handleLoad`) | `frontend/src/lib/utils/broker/brokerIconChain.svelte.ts` |
| The component | `frontend/src/lib/components/ui/display/BrokerIcon.svelte` |
| Component tests | `frontend/src/lib/components/ui/display/BrokerIcon.test.ts` |
| Chain tests | `frontend/src/lib/utils/broker/__tests__/brokerIconChain.test.ts` |
| Plan 48 (H1, the fix) | `LibreFolio_developer_journal/Release_2/Phase_0/48_uiPolish/plan-phase00UiPolish.prompt.md` |
| Backlog (C-56, C-57) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
