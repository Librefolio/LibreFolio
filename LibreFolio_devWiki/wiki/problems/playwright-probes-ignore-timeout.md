---
title: "Playwright probes that ignore their timeout skipped gallery shots in silence"
category: problem
status: resolved
date: 2026-10-12
updated: 2026-10-12
tags: [frontend, testing, playwright, e2e, gallery, screenshots, probes, flaky, import-wizard, i18n, locale, cdp]
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
  wait inside step 2 can fix that. (The product side of this race was M-16, fixed in train 48 — below.)

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

## M-14, closed the same day: each language is shot by a browser of that language

- **The diagnosis** (batch 18): about 36 app sites format with the browser's locale — the amounts
  (`toLocaleString(undefined, …)` in `currencyFormat.ts`), table dates, KPI and chart labels, the scheduler log — and
  the gallery ran an en-US browser, so the it, fr and es shots showed «1,188.58 €» next to labels in their language.
- **The developer's decision** (2026-10-12, verbatim): «tanto gli screen vanno fatti in ogni caso, impostiamo il locale
  in playwright sin da ora, è la scelta giusta» ("the shots have to be taken anyway: set the locale in Playwright from
  now on, it is the right choice").
- **The fix** (batch 20 of M, test-author; `51b581636`, journal `63b3e5971`, train 52 `d33fca26f`):
  - Playwright's `locale` is fixed per browser context, while the gallery loops four languages in one page. So
    `setBrowserLocale(page, lang)` (`frontend/e2e/fixtures/galleryLocale.ts`) sends Chromium's
    `Emulation.setLocaleOverride` from the page's CDP session — en-US, it-IT, fr-FR, es-ES — as the first statement of
    each of the 76 language loops, before the page is drawn: a language switch redraws nothing, so a number drawn
    before it would keep the old format.
  - **The guard**: an init script stamps each document with the locale it began under (`stampDocumentLocale`), and
    `expectDrawnUnder(page, lang)` — in `screenshot()` and `shootFiles()`, the only two screenshot calls — fails a shot
    whose page was drawn under another locale, or carries no stamp.
  - *Update (train 78)*: the override moves only `Intl`'s fallback locale and `Accept-Language`; `navigator.language`,
    which `uiLocale()` reads since M-18, stays en-US — backlog M-24 (low), written into the header of
    `galleryLocale.ts` (`1e4a3ecd5`).
  - The 13 tests that shoot a page prepared once (3 auth pages, 2 PAC, 8 Files) now redraw it in each language.
  - **The trap**: `@playwright/test` gives every context `locale: 'en-US'`, and Chromium then refuses a second override
    («Another locale override is already in effect»). `test.use({locale: undefined})` falls back to that default; the
    gallery's describe uses a fixture that yields `undefined` instead.
- **Proof**: full gallery 250 passed, 1 skipped by design, 1 failed — triaged as environment (a network change on the
  shared machine aborted the requests in flight), the same test green three times alone. The Italian dashboard reads
  «+4788,01 €» and «50.000,00 €».
- The `testing-frontend` skill gained the rule «Gallery: a language's shots are taken by a browser of that language».

## M-16, closed in train 48: the wizard's «Next» waits for the broker list

- The product side of the wizard race above: on step 1 «Next» stayed enabled while the broker list loaded, and a user
  faster than the list found step 2's broker panels collapsed, the files there but hidden.
- Fixed by workstream I (`3cd25af4f`, "fix(import): gate wizard Next on broker load"; train 48, `0e4f35b0a`; plan
  `Phase_0/44_importWizardBrokerGate/`). Every broker-list load in flight — the one at opening and the refresh after a
  broker created from step 1 — keeps step 1 busy (`data-busy`) and «Next» disabled with its spinner
  (`trackBrokerLoad()`, `brokersLoading`). `loadBrokers()` waits with `Promise.allSettled`, so a loader that fails
  neither releases «Next» early nor locks it.
- The gallery line that depends on it, `waitForSettled(import-wizard-step1)` before the step-1 shot, came with batch 20
  of M (`51b581636`).
- The defect and its fix in full: [[problems/import-wizard-next-before-brokers-loaded]].

## Still open (post-1.2 backlog, section M)

- **M-15**: `appears()` was put also where the component always renders the element on the test's path
  (`selectTransactionType`, table views, the wizard file row, the cache unlock, the broker edit, the asset search, the
  date presets): those should be `expect`. Also open there: the timed wait of the step-2 shot, the 7 class-C probes,
  and the same `isEnabled({timeout})` defect in `transactions/tx-picker-pagination.spec.ts`.

## Planned in release 1.2 (assigned to I)

- **M-17**, found by M-14 — the coordinator's decision, after M-16: two UI strings fixed in English — the date range
  picker formats with `'en'`, and «Last updated:» in the global settings. *Resolved in M-18's CP2 (`ff7c96fd0`, train 75).*
- **M-18**, found by M-14 — the developer's decision of 2026-10-12, after the UI refinement: numbers built with
  `toFixed(n)` never meet a locale and keep the dot in every language — percentages (about 50 lines in some 30 files),
  file sizes, durations — so a shot reads «+4788,01 €» next to «14.07%». *Update (train 68)*: moved to T, with the
  developer's rule «Lingua della UI per tutto» — CP1 delivered (`5b2aad5c4`); CP2 and CP3 delivered in trains 75–76, M-18 closed —
  [[decisions/figures-in-the-interface-language]]. A known limit stays after it (T's analysis,
  backlog T-DI): a native `<input type="date">` is drawn by the browser in the browser's language
  (`RiskAnalysisPanel.svelte`); only a date picker of the app's own would follow the UI.

## Links

- [[problems/compactcashcell-decimal-separator-feedback-loop]] and [[sources/phase00-e2e-import-infra-2026-10]] — the
  same trap met before, outside the gallery
- [[entities/import-wizard-modal]] — the wizard whose step 1 race is described above
- [[problems/playwright-favicon-aborted-by-routes]] — the other Playwright 1.61 trap of the gallery, and
  [[decisions/gallery-is-a-release-gate-with-real-data]] for the rules the gallery runs under
- Source: [[sources/phase00-translation-round12-2026-10]]

## Source files

| Role | Path |
|------|------|
| `appears()`, `becomesEnabled()` | `frontend/e2e/fixtures/probe.ts` |
| `setBrowserLocale()`, `stampDocumentLocale()`, `expectDrawnUnder()` (M-14) | `frontend/e2e/fixtures/galleryLocale.ts` |
| `waitForSettled()` | `frontend/e2e/fixtures/app-events.ts` |
| The gallery scenarios | `frontend/e2e/gallery.spec.ts` |
| The wizard (`loadBrokerFiles`; M-16: `trackBrokerLoad`, `loadBrokers`; each step's `data-busy` in its component under `frontend/src/lib/features/transactions/import/`) | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |
| M-16 tests (unit, E2E) | `frontend/src/lib/features/transactions/import/ImportWizardModal.test.ts`, `frontend/e2e/transactions/tx-import-upload.spec.ts` |
| M-16 plan (workstream I) | `LibreFolio_developer_journal/Release_2/Phase_0/44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md` |
| Amount formatting by the browser's locale (M-14) | `frontend/src/lib/utils/currency/currencyFormat.ts` |
| Same `isEnabled` defect outside the gallery (M-15) | `frontend/e2e/transactions/tx-picker-pagination.spec.ts` |
| The rule for test authors | `.github/agents/test-author.agent.md` |
| The gallery locale rule | `.github/skills/devpy-tools/testing-frontend/SKILL.md` |
| Journal (§9.3, §10, §11) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
| Backlog rows M-13 … M-18 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
