---
title: "Playwright probes that ignore their timeout skipped gallery shots in silence"
category: problem
status: resolved
date: 2026-10-12
tags: [frontend, testing, playwright, e2e, gallery, screenshots, probes, flaky, import-wizard, i18n]
related:
  - problems/compactcashcell-decimal-separator-feedback-loop
  - sources/phase00-e2e-import-infra-2026-10
  - concepts/e2e-data-testid-rule
  - entities/import-wizard-modal
  - sources/phase00-translation-round12-2026-10
---

# Problem: probes that ignore their timeout skipped gallery shots in silence

## Symptom

The full gallery run of translation batch 18 (2026-10-12, lane 6158, 2 workers) ended **251 passed, 0 failed** — and
8 shots had not been retaken: `create-wizard-modal` in five language/theme pairs, `import-wizard-step3` and
`import-wizard-step4-resolution` (mobile/en/light), `import-wizard-duplicate` (mobile/fr/light) still carried their
files of 8–9 October. The release run rebuilds the gallery from scratch, so a shot skipped there is simply
missing from the release.

## Root Cause

- **In Playwright 1.61, `locator.isVisible({timeout})` ignores its timeout**: it answers about *this instant*. And
  `locator.isEnabled({timeout})` waits only for the element to exist, then looks once. The gallery scenarios used both
  as waits for optional branches — `if (await x.isVisible({timeout: N})) { …screenshot… }` — so whenever the element
  was not there at that instant the branch, and its shot, was skipped and the test stayed green.
  `gallery.spec.ts` held 76 such `isVisible` probes, plus 3 `isEnabled` probes on the import wizard's parse button,
  which stays disabled until step 2 can parse.
- **A race in the import wizard**, found once the probes really waited (under load 84, six more wizard shots were
  missed): step 2 loads its files, plugins and set previews behind its own `data-busy`, which the scenario's prelude
  guessed with `waitForTimeout(800)`; and a «Next» clicked before step 1's broker list arrives makes
  `loadBrokerFiles()` read an empty list, so every broker panel renders collapsed and the file row never exists. No
  wait inside step 2 can fix that.

The trap itself was known — `e2e/fixtures/probe.ts` has had `appears()` for it since 2026-08-15 (`e39ab4571`), and
the agent rules warn about it — but `gallery.spec.ts` used `appears()` nowhere.

## Solution

Backlog M-13, batch 19 of workstream M (2026-10-12, test-author; commit `d956853a6`, train 46, merge `378338fed`):

- The 76 probes were read one by one and classified: **A**, 19 guard a shot; **B**, 29 prepare a later shot; **C**, 7
  fail loudly when they miss; **D**, 21 are cleanups or a deliberate instant question. A and B — **48** — became
  `appears(x, N)`, each in place, every timeout as written.
- The 3 `isEnabled` probes became `becomesEnabled()`, the enabled twin of `appears()`, new in `e2e/fixtures/probe.ts`.
- The wizard prelude settles step 1 before «Next» (`waitForSettled(import-wizard-step1)`), waits for step 2's
  `data-busy` instead of the 800 ms sleep, and settles step 4 before the create-wizard's asset select.
- **Proof**: the 43 test titles per viewport that hold a converted probe, 86 passed; the 8 missed shots came out, and
  every other shot name of those scenarios exists 16 times out of 16 (2 viewports × 4 languages × 2 themes). The three
  wizard tests, rerun with 2 and with 4 workers: 6 passed each time, their 4 shot names 16/16 each time.

## Prevention

- Never use `isVisible({timeout})` or `isEnabled({timeout})` as a wait. For a branch that is legitimately optional, use
  `appears()` / `becomesEnabled()`: fast when the answer is yes, honest when it is no.
- When the element **must** be there, use `expect(x).toBeVisible()` / `toBeEnabled()`: a missing shot then becomes a
  red test instead of a gap in the release.

## Still open (post-1.2 backlog, section M)

- **M-15**: `appears()` was put also where the component always renders the element on the test's path
  (`selectTransactionType`, table views, the wizard file row, the cache unlock, the broker edit, the asset search, the
  date presets): those should be `expect`. Also open there: the timed wait of the step-2 shot, the 7 class-C probes,
  and the same `isEnabled({timeout})` defect in `transactions/tx-picker-pagination.spec.ts`.
- **M-16**: a product question — the wizard's «Next» stays enabled while the broker list loads, so a user that fast sees
  the same collapsed list.
- **M-14** (not delivered at `5d0585595`, only its diagnosis is recorded here): amounts are formatted by the browser's
  locale (`toLocaleString(undefined, …)` in `currencyFormat.ts`) and the gallery runs an en-US browser, so the it, fr
  and es shots show «1,188.58 €». A per-language locale for the gallery browser is in progress.

## Links

- [[problems/compactcashcell-decimal-separator-feedback-loop]] and [[sources/phase00-e2e-import-infra-2026-10]] — the
  same trap met before, outside the gallery
- [[entities/import-wizard-modal]] — the wizard whose step 1 race is described above
- Source: [[sources/phase00-translation-round12-2026-10]]

## Source files

| Role | Path |
|------|------|
| `appears()`, `becomesEnabled()` | `frontend/e2e/fixtures/probe.ts` |
| `waitForSettled()` | `frontend/e2e/fixtures/app-events.ts` |
| The gallery scenarios | `frontend/e2e/gallery.spec.ts` |
| The wizard (step `data-busy`, `loadBrokerFiles`) | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| Amount formatting by the browser's locale (M-14) | `frontend/src/lib/utils/currency/currencyFormat.ts` |
| Same `isEnabled` defect outside the gallery (M-15) | `frontend/e2e/transactions/tx-picker-pagination.spec.ts` |
| The rule for test authors | `.github/agents/test-author.agent.md` |
| Journal (§9.3, §10) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
| Backlog rows M-13 … M-16 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
