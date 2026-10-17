---
title: "In a legacy Svelte component, a language read inside a helper called from the template is untracked"
category: problem
status: resolved
date: 2026-10-11
tags: [frontend, svelte5, legacy-mode, i18n, reactivity, locale, workstream-p]
related:
  - concepts/svelte5-runes
  - concepts/marker-locale-for-catalogue-labels
  - sources/phase00-promote-pair-checks-2026-10
  - problems/legacy-layout-gate-missed-runes-state
  - features/F-101
---

# Problem: the language read inside a helper does not follow a language change

## Symptom

While localising the percentages of the broker card and of the broker page (plan 42, §8.1) with
`formatPercent(…, {locale: …})`, P's test author found the trap: read inside a helper, the language store would leave
the numbers in the language of the mount when the user switched language. The red tests switch the language in place for
this reason.

## Root Cause

`BrokerCard.svelte` and the sharing panel are legacy components (`export let`, not runes). There, a read of
`$currentLanguage` inside a helper function called from the template compiles into `$.untrack`, so the template's
expression does not depend on the store and is not recomputed.

## Solution

Commit `0de730f3b` (train 38): the store is read in the template expression itself —
`formatPercent(value, {…, locale: $currentLanguage})` — and a helper that needs the language receives it as a parameter.
Digits and rounding do not change, and English text is identical.

## Prevention

Red tests by P's test author check the switch in place: `BrokerCard.test.ts` (French at mount, then en → fr → en),
`BrokerSharingPanel.test.ts`, and `brokers-detail.spec.ts` (the page opened in French, then switched). The expected
value is computed with `Intl` in the same environment, so the U+00A0 before «%» needs no hand-written literal.

## Impact

None shipped: the trap was avoided before the fix. Elsewhere it would leave a legacy component's text in the previous
language until a reload.

## Earlier instances (added 2026-10-12, step B5)

The trap had already bitten twice, three weeks before plan 42:

- **The privacy switch (R20)** — in the usage review of 2026-09-22 the broker list and the broker page did not follow
  the privacy toggle: in these two legacy components the formatter call inside a template expression compiled into
  `$.untrack()`. `64d78e244` (2026-09-24) moved their five amounts to `CurrencyAmount.svelte`, a runes component
  ([[features/F-101]]).
- **The layout gate** — the same family, in a `$:` statement rather than a template: the `(app)` layout's gate
  missed the runes field `appBootstrap.ready`, and the requested page flashed before the Welcome redirect
  (`cc20b8288`, read through `toStore()`) — [[problems/legacy-layout-gate-missed-runes-state]].

## Source files

| Role | Path |
|------|------|
| The card | `frontend/src/lib/features/brokers/BrokerCard.svelte` |
| The sharing panel | `frontend/src/lib/features/brokers/BrokerSharingPanel.svelte` |
| `formatPercent` and its `locale` option | `frontend/src/lib/utils/core/formatPercent.ts` |
| E2E | `frontend/e2e/brokers/brokers-detail.spec.ts` |
