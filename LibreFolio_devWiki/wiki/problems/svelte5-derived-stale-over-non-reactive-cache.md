---
title: "Svelte 5: a `$derived` over a non-reactive module cache stays stale across close and reopen — the changelog stuck on «loading»"
category: problem
status: resolved
date: 2026-10-19
tags: [frontend, svelte5, runes, reactivity, cache, derived, legacy-mode, changelog, vitest, playwright, workstream-a]
related:
  - concepts/svelte5-runes
  - concepts/discard-the-answer-not-the-question
  - problems/legacy-component-language-untracked
  - problems/svelte5-teardown-reads-stale-state-timers
  - decisions/changelog-translated-by-chapter
  - features/F-109
---

# Problem: a `$derived` over a non-reactive module cache keeps its stale value across close and reopen

## Symptom

On his nightly (`v1.2.1-2591-g5e1a7c3af`, Italian UI), the developer clicked the version under the logo in
Settings › About: the changelog window opened and stayed on «loading» for good. The version under the sidebar opened the
same changelog at once (lot A-CL1, 19/10/2026).

The sequence that reproduces it, in any translated language:

1. open the changelog while its translation chunk is not loaded yet («loading»);
2. close it before the chunk arrives;
3. reopen it from the same entry point once the chunk has loaded.

It stays on «loading» until a language change or a reload. A first opening, with the chunk landing while the window is
open, always worked.

## Root Cause

Three things together.

- **The reader's state did not observe the cache.** `ChangelogModal` derived what it shows from the module's cache:
  `ready = $derived(localizedChangelog.peek(uiLanguage) ?? (loaded?.language === uiLanguage ? loaded.chapters : undefined))`.
  `peek()` read `merged`, a plain `Map` in `createLocalizedChangelog`, so the cache was not a dependency of `ready`:
  `ready` was recomputed only when `uiLanguage` or `loaded` changed.
- **The answer was dropped on close (rightly).** The load effect's teardown sets `live = false`, so a window closed
  mid-load ignores the answer ([[concepts/discard-the-answer-not-the-question]]: dropping a stale answer is right). The
  load itself still completed and filled the shared cache.
- **On reopening nobody asked again, and nothing told `ready`.** The effect saw `peek()` full and returned without
  setting `loaded`. `ready` kept its cached `undefined`: a component's `$derived` survives the destroy and re-creation of
  the `{#if open}` block, because it belongs to the component, and none of the signals it had read had changed.

The question was not lost (the cache held the answer), but the view could not see it: the data lived outside the
reactive graph. The sidebar worked because it was **another instance**. About mounted a second `ChangelogModal` of its
own, and the sidebar's `ready` was computed for the first time when it opened, after About's load had filled the cache.
The developer called the second instance «una duplicazione errata di codice».

**Hypotheses ruled out**:

- a rejected or hung promise: `load()` never rejects (`.catch(() => englishOnly)`), and a hung chunk would also have
  blocked the sidebar, which shares the pending request;
- the «What's new» window or the sidebar preloading the translation: a cache filled *before* the first opening makes
  the opening immediate, not stuck.

## Solution

Commit `5ccb495e5`, release 1.3:

- **The cache is observable.** `merged` is a `SvelteMap` (`svelte/reactivity`): every `$derived` or effect that calls
  `peek()` depends on it, and `SvelteMap.get()` of a missing key tracks the map's version, so the first `set` reaches
  readers that saw `undefined`. `WhatsNewModal`, which reads the same module the same way, is cured too.
- **One window.** The Sidebar mounts the only `ChangelogModal`, bound to `changelogModalStore.svelte.ts`
  (`changelogModal.open`, `show()`, `close()`). Both versions call `show()`, and the Sidebar closes it on unmount, so a
  new sign-in never finds it open.

Two side notes found on the way:

- **Node tests see a plain `Map`.** In Vitest's node environment `svelte/reactivity` resolves to its server build,
  which exports `SvelteMap = globalThis.Map`: the module's pure-logic tests (`changelog.test.ts`) are unaffected, and
  they cannot observe reactivity either.
- **A legacy component reading a runes store.** In the legacy `Sidebar`, Svelte 5.48 compiles
  `open={changelogModal.open}` to `($.deep_read_state(changelogModal), $.untrack(() => changelogModal.open))`. It is
  reactive only because `deep_read_state` walks the object and calls the `open` getter. `Sidebar.changelog.test.ts` case 1
  turns red if that ever stops ([[problems/legacy-component-language-untracked]] is the same family).

## Prevention

- **A module-level cache that a `$derived` or an effect reads must be reactive**: a `SvelteMap` or `SvelteSet`, or
  `$state` in a `.svelte.ts` module. The alternative is that each reader keeps the value in state it owns and sets it
  from every path, the early returns included. A plain `Map` behind a `peek()` works only for readers whose first read
  comes after the fill.
- **One instance of a stateful window**, and a shared opener for every entry point. A second instance is a second
  copy of the state, and of its bugs.
- **The test that shows it**: close during the load, let it resolve, reopen (M1 in `ChangelogModal.test.ts`). M2 is the
  failed-then-loaded variant.
  - A faithful fake of the module must mirror its reactivity: the fakes' cache is a `SvelteMap` since A-CL1. The red
    was observed with the plain-`Map` fake, today's module semantics. A fake proves the component's side only: with
    `new Map` back in the module, every test on the fake would stay green (the automatic review of `5ccb495e5`).
- **The real module, in Vitest.** Two walls stood in the way, and both are worth knowing:
  - the default `node` environment has no reactivity: `svelte/reactivity` is the server build (`SvelteMap =
    globalThis.Map`), `$derived` is computed once and `$effect` never runs (`src/__tests__/runes.svelte.ts`);
  - jsdom refuses the module's `?raw` import of the repo-root `CHANGELOG.md` («Denied ID …»,
    `isServerAccessDeniedForTransform`), even when that raw path is mocked (relative, absolute or `/@fs`).
  - The seam: the bundle imports live in `changelogSources.ts` (the `?raw` CHANGELOG.md and the `import.meta.glob` of
    its translations); a jsdom test mocks that normal module and loads the real `changelog.ts`.
    `changelog.reactivity.test.ts` reads `peek('it')` from an effect (`recordReads`) across a `load('it')`: red with
    `new Map` (4 failed, in a copy of the module that was in the tree only for that run), green with `SvelteMap`.
  - A new `.test.ts` is also registered in `scripts/test_runner/_frontend_utility.py`: `dev.py test check-orphans`
    lists the ones that are not (two were, here).
- **In the real app**, the E2E E1 in `changelog-locale.spec.ts`:
  - the translation chunk is held with `page.route`, recognised by its body through a marker read from
    `CHANGELOG.it.md`, then continued with `route.continue()`;
  - after the release, the page calls `import(url)` twice before reopening. The first import alone may resolve before
    the app's own continuation, which would hide the bug.

## Impact

- **Users**: the changelog from Settings › About could stay on «loading» in any translated language until a reload.
  No data effect.
- **Effort**: about 1 h of analysis and 1.5 h for the lot (Vitest reds and greens, an E2E slot red → green).
- **Side effects of the developer's decision**, passed on to him:
  - from About, the manual update check now reports the app's version, not the backend's (equal within one image);
  - the window opened from About now stays open on browser back, as the sidebar's always did.

## Source files

| Role | Path |
|------|------|
| The cache (`merged` as `SvelteMap`, `peek`, `load`) | `frontend/src/lib/features/changelog/changelog.ts` |
| The one window's state | `frontend/src/lib/features/changelog/changelogModalStore.svelte.ts` |
| The window (`ready`, the load effect) | `frontend/src/lib/components/layout/ChangelogModal.svelte` |
| The mount point and an entry point | `frontend/src/lib/components/layout/Sidebar.svelte` |
| The other entry point | `frontend/src/lib/features/settings/tabs/AboutTab.svelte` |
| The other reader of the cache | `frontend/src/lib/features/changelog/WhatsNewModal.svelte` |
| Vitest M1, M2 (the faithful fake) | `frontend/src/lib/components/layout/ChangelogModal.test.ts` |
| Vitest: the real module's cache tells its readers | `frontend/src/lib/features/changelog/changelog.reactivity.test.ts` |
| The bundle imports a jsdom test replaces (the seam) | `frontend/src/lib/features/changelog/changelogSources.ts` |
| Vitest: one window, bound to the shared state | `frontend/src/lib/components/layout/Sidebar.changelog.test.ts` |
| E2E E1, E2 | `frontend/e2e/layout/changelog-locale.spec.ts` |
| The plan (analysis, lot, slot) | `LibreFolio_developer_journal/Release_2/Phase_1/02_accounts/plan-phase01Accounts.prompt.md` |
