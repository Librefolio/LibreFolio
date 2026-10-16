---
title: "Import wizard: «Next» worked before the broker list had arrived, hiding the uploaded files in step 2"
category: problem
status: resolved
date: 2026-10-12
tags: [frontend, import-wizard, svelte5, race-condition, async, loading-state, testing, workstream-i, m-16]
related:
  - problems/playwright-probes-ignore-timeout
  - decisions/import-wizard-default-plugin-check
  - problems/svelte5-effect-read-write-loop
  - entities/import-wizard-modal
  - features/F-049
  - sources/phase00-import-wizard-broker-gate-2026-10
---

# Problem: «Next» before the broker list

## Symptom

On step 1 of the import wizard, «Next: Select Files» was enabled while the broker list was still loading. A user
faster than the list reached step 2 with every broker panel collapsed: the uploaded files were there, but hidden. M's
test author found it while fixing the gallery probes (backlog M-16, batch 19), as the product side of a gallery race —
[[problems/playwright-probes-ignore-timeout]].

## Root Cause

In `ImportWizardModal.svelte`, at the base `378338fed`:

- the opening `$effect` starts `loadBrokers()`, which waits for the brokers, the transaction types and the import
  plugins before it writes `brokers`;
- «Next» looked only at `step1CanProceed`, `uploading` and `step1Continuing`;
- `goNext()` uploads and calls `loadBrokerFiles()`, which maps `brokers` — still an empty list — so step 2's panels
  opened collapsed;
- the **second face**: the wrong-broker check reads the same list ([[decisions/import-wizard-default-plugin-check]]);
- the same gap after a broker is created from step 1: `BrokerModal`'s `oncreated` refreshed `brokers` with no signal;
- nearby: `loadBrokers` had no `finally`, so when `ensureTypesLoaded` rejected, step 1 stayed `data-busy` forever and
  the rejection went unhandled.

## Solution

The developer, 2026-10-12: «si nella 1.2 e ok I, ma fai che disabilitiamo il pulsante finchè il pacchetto non
arriva» ("yes, in 1.2, and fine for I, but disable the button until the package arrives"). Workstream I, plan 44,
commit `3cd25af4f` ("fix(import): gate wizard Next on broker load", train 48):

- `trackBrokerLoad(load)` counts the broker loads in flight — the one at opening and the refresh after `oncreated` —
  and `brokersLoading` stays true until all of them have finished. «Next» is disabled, with the upload's spinner, and
  step 1 is `data-busy`;
- `loadBrokers()` waits with `Promise.allSettled`, inside the counter's `finally`: a failed loader neither releases
  «Next» early nor locks it, and each loader still logs its own error;
- `goNext()` returns while `brokersLoading` too, because Svelte 5's event delegation can call a handler on a disabled
  button (the plan's reading of `svelte`'s `events.js`);
- no i18n key, no recomputation of the panels, no backend change.

**The counter is a plain variable, not `$state`.** The analysis first proposed a reactive counter and
`$derived(brokerLoads > 0)`. But `loadBrokers()` runs inside the opening `$effect`, where `brokerLoads += 1` reads and
writes the same signal: the effect would depend on it and start again at every load
([[problems/svelte5-effect-read-write-loop]]). The template keeps reading `brokersLoading`.

## Prevention

- Red tests first, by `test-author`, each red for the right reason before the fix:
  - Vitest V1–V4b in `ImportWizardModal.test.ts` («step 1 waits for the broker list»): «Next» disabled during the
    load; a click during the load stays on step 1; a rejected types load releases the step; the refresh after
    `oncreated`; and V4b, a refresh that ends before the opening load — both must finish;
  - E2E E1 in `tx-import-upload.spec.ts`, which holds the import-plugins request and writes nothing.
- Three older unit tests that pressed «Next» right after the mount now wait for `data-busy="false"`.
- The gallery shot of step 1 waited only 300 ms; it now waits for the step to settle
  (`waitForSettled(import-wizard-step1)`, M's batch 20, `51b581636`).

## Impact

A quick click hid the uploaded files in step 2, and the wrong-broker check read an empty broker list.

## Links

- [[problems/playwright-probes-ignore-timeout]] — the gallery side, M-13 to M-18
- [[entities/import-wizard-modal]], [[features/F-049]]
- Source: [[sources/phase00-import-wizard-broker-gate-2026-10]]

## Source files

| Role | Path |
|------|------|
| `trackBrokerLoad`, `loadBrokers`, `brokersLoading`, `goNext` | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |
| V1–V4b | `frontend/src/lib/features/transactions/import/ImportWizardModal.test.ts` |
| E1 | `frontend/e2e/transactions/tx-import-upload.spec.ts` |
| The gallery wait | `frontend/e2e/gallery.spec.ts` |
| Plan 44 | `LibreFolio_developer_journal/Release_2/Phase_0/44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md` |
