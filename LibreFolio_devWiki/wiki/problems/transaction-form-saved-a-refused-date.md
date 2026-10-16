---
title: "The transaction form saved a date its calendar had refused, keeping the previous one in silence, and said «valid» next to a field shown in red (V-37, since v1.1.0)"
category: problem
status: resolved
date: 2026-10-13
tags: [frontend, transactions, forms, validation, date-picker, product-defect, workstream-v, release-1.2]
related:
  - features/F-048
  - sources/phase00-data-quality-e2e-2026-10
---

# Problem: a form that trusted only the server

## Symptom

Two defects of the transaction form, found by workstream V on 2026-10-13 and present since v1.1.0:

- **A refused date was saved as the previous date.** Typing a date in the future, or text that is not a date, left
  the text on screen in red; *valid* stayed, **Apply** worked, and the transaction was saved with the date it had
  before, without a word.
- **«valid» next to a red field.** A purchase with a negative quantity showed the quantity in red, and the form's
  badge said *valid*.

## Root Cause

- **The date picker never reported its validity.** `SingleDatePicker` kept the refused text on screen with
  `data-invalid="true"`, but its bound value kept the previous date, and it had no way to tell the form. The defect
  dates from `52b48fd83` (2026-08-27), in v1.1.0.
- **The badge read only the server's verdict.** The form validates a sign-corrected draft: a quantity of −1 on a
  purchase reaches the server as 1, and the server answers *valid*. A manual validation also bypassed the scheduler's
  own gate.

## Solution

The minimum, now (`b77885f0b`, train 96; the developer: «Il minimo ora, più la data se la sonda la conferma; il
pre-step completo dopo la 1.2»):

- the picker reports its validity (`onvaliditychange`), and a refused date becomes one of the form's own errors;
- `hasLocalErrors` — a sign violation, a pair error or a refused date — gates three things: the automatic
  validation, the *valid* badge and **Apply**, which instead focuses the first wrong field; **⚡ Validate now** does
  the same, and validation starts again by itself once the errors are cleared;
- three E2E tests («A refused entry blocks the form», `transactions-modals.spec.ts`) and unit tests on the form and
  the picker; the user guide says that the form checks nothing while it shows a mistake of its own (`73a75650e`).

The [1.2.0] chapter has one 🐛 line for each defect, under «📥 Imports and transaction editing», both «Present since
v1.1.0» (`f8dbdddaf`).

## Still open

- **V-37b**, after 1.2: the full pre-step — ⚡ always clickable, checking required fields and formats first, every
  wrong cell marked, for single, pair and FX layouts.
- **V-38**, to verify on screen: the form files a balance problem under the field problems because it splits them by
  index, where the bulk editor splits them by code.

## Prevention

A form must count its own visible errors before it trusts a server verdict on a corrected copy of its data: what the
user sees in red is the state, whatever the payload says.

## Source files

| Role | Path |
|------|------|
| The date picker (`onvaliditychange`) | `frontend/src/lib/components/ui/date/SingleDatePicker.svelte` |
| The form (`hasLocalErrors`, `validateNow`) | `frontend/src/lib/features/transactions/form/TransactionFormModal.svelte` |
| E2E | `frontend/e2e/transactions/transactions-modals.spec.ts` |
| User guide | `mkdocs_src/docs/user/transactions/form.en.md` |
| V's lot (§12.15) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
