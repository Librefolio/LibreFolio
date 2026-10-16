---
title: "@testing-library/svelte reads a prop named `events` as a mount option: props go under `{props: …}`"
category: problem
status: resolved
date: 2026-10-15
tags: [frontend, testing, vitest, svelte5, testing-library, jsdom]
related:
  - decisions/asset-event-saves-all-or-nothing
  - problems/svelte5-teardown-reads-stale-state-timers
---

# Problem: a prop named like a mount option

## Symptom

Release 1.3, workstream W, lot E1b, 15/10. `EventExistsPanel.test.ts` (Vitest, jsdom) went red in every test right
after the cure, which cannot be a red written first. The component was never mounted.

## Root Cause

`render(Component, options)` in `@testing-library/svelte` (5.4.2, through `@testing-library/svelte-core`) takes its
second argument as either props or Svelte mount options:

- `validateOptions()` in the core's `setup.js` reads the object as mount options as soon as one key is a mount option
  name. On Svelte 5 those are `target`, `anchor`, `props`, `events`, `context` and `intro`;
- any other key is then an error: `UnknownSvelteOptionsError`, whose message says to put the props under `props`.

`EventExistsPanel`'s props are `events`, `onuse`, `onedit` and `oncancel`. The `events` key turned the object into
mount options, and the three callbacks were refused as unknown options.

## Solution

The test-author passes the props explicitly, then the file is green:
`render(EventExistsPanel, {props: {events, onuse, onedit, oncancel}})`. A comment above the call says why.

## Prevention

- A component prop called `events`, `context`, `target`, `anchor`, `intro` or `props` must go under `{props: …}`.
- Writing `{props: …}` every time costs nothing and removes the guess.
- A whole test file red after a cure, at render, points at the test before the product.

## Impact

Minutes. No product defect.

## Source files

| Role | Path |
|------|------|
| The test, with the `props` key and its comment | `frontend/src/lib/features/transactions/events/EventExistsPanel.test.ts` |
| The component and its `events` prop | `frontend/src/lib/features/transactions/events/EventExistsPanel.svelte` |
| The library's version (`@testing-library/svelte`) | `frontend/package.json` |
