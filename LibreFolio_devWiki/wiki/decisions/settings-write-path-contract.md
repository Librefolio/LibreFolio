---
title: "The settings write path: confirm before applying, report per field, never stop at the first refusal"
category: decision
status: accepted
date: 2026-08-30
tags: [settings, frontend, ux, api-contract, product-decision]
related: [concepts/characterisation-test-latch, decisions/broker-last-owner-guard]
---

# Decision: what a settings save owes the user

The settings lane found five defects in the write path. The user decided each of
them, and the answers form a single coherent contract.

## C1 — apply after the server confirms, not before

The optimistic path applied the change locally and then sent the `PUT`. On
failure the UI kept a value the server had rejected.

**Decision:** apply **after** the response, and show a toast on error. The cost is
a perceptible delay on a settings screen — which is exactly the screen where
correctness beats latency, because the user is deliberately changing something
and expects an acknowledgement.

## C2 — `hasNonDefaults={false}` was a literal

The preferences tab passed the literal `false`, so the "reset to defaults"
affordance never appeared however far the user had strayed from the defaults.

**Decision:** a one-line fix.

```svelte
hasNonDefaults={languageNonDefault || currencyNonDefault || themeNonDefault}
```

## C3 / C4 — `saveAll` must not stop at the first refusal

`saveAll` aborted on the first rejected field. The user was left with a partially
applied batch and a single error message that did not say which fields had landed.

**Decision:** `saveAll` attempts **every** field, then reports what landed and
what did not — and its semantics are aligned with `saveField`, so that "save one"
and "save all" cannot diverge in behaviour.

> A batch operation that stops at the first error converts a per-field problem
> into an all-or-nothing one, and then does not even deliver "nothing".

## C5 — unclaimed keys go to «Altro»

Settings keys that no tab claims were simply not rendered: invisible, uneditable,
and impossible to discover.

**Decision:** an **«Altro»** (Other) category collects them. A key that exists
must be reachable.

## C7 — `isSaving` is missing on three controls

`SettingNumber` and `SettingToggle` expose an `isSaving` state; `SettingCurrency`,
`SettingSelect` and `SettingTheme` do not.

**Decision:** it is a **bug**, not a design choice. Three of five controls give no
feedback during the round trip, which with C1 in place — apply only after the
response — becomes a visible dead interval.

C1 and C7 have to ship together: confirming before applying *without* a pending
indicator would make the UI feel broken.

## Two neighbouring findings from the same lane

**C8 — `resolveFormItemsFromOps` is not dead code.** It is the right function,
never wired up. `TransactionBulkModal.svelte` (~2280) builds the pair by hand,
skipping `orientPair` and `validatePair`. Wiring it requires care with the
ordering against the `mainItem.type` overwrite at ~2264-2275 — which is why it
was not done inside a test lane.

**C9 — the `transactions/modals/index.ts` barrel is dead code.** Verified: no
importer. Deleted.

## Why this is one decision and not five

Each item on its own is small. Together they answer one question — *what does the
UI owe the user between the click and the acknowledgement* — and the answers only
work as a set: confirm late (C1), show the wait (C7), never lose a field (C3/C4),
never hide a key (C5), and tell the truth about defaults (C2).

The behaviours that were **not** repaired inside the lane are held by
characterisation tests ([[concepts/characterisation-test-latch]]).

## See also

- [[decisions/scheduler-converts-at-decision]] — the same question one layer down:
  *at which point does a value get converted, and who is allowed to do it*. The
  write-path contract fixes where a setting may be written; the scheduler decision
  fixes where an instant becomes a calendar day. Both answers are "at one named
  point, and nowhere else", and both exist because the alternative was a value that
  differed depending on the route it took.
- [[problems/utc-today-vs-user-calendar]] — the read-side counterpart of the
  scheduler decision.

## Source files

| Role | Path |
|------|------|
| Save orchestration | `frontend/src/lib/components/settings/SettingsLayout.svelte` — `saveField`, `saveAll` |
| Preferences tab (C2, C1) | `frontend/src/lib/components/settings/tabs/PreferencesTab.svelte` |
| Global settings tab (C5) | `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte` |
| Controls missing `isSaving` (C7) | `frontend/src/lib/components/settings/SettingCurrency.svelte`, `SettingSelect.svelte`, `SettingTheme.svelte` |
| Controls that have it | `frontend/src/lib/components/settings/SettingNumber.svelte`, `SettingToggle.svelte` |
| Unwired helper (C8) | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` (~2280), `resolveFormItemsFromOps` |
| Settings API | `backend/app/api/v1/settings.py` |
| mkdocs | `mkdocs_src/docs/user/settings/index.en.md` |
