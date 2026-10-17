---
title: "E2E tests left their writes in shared state: a saved language, the scheduler's global keys, exchange rates fetched from the network"
category: problem
status: open
date: 2026-10-12
tags: [testing, e2e, playwright, isolation, parallelism, test-user, mockfx, scheduler, settings, workstream-v, release-1.2]
related:
  - concepts/test-isolation-classes
  - decisions/data-quality-proved-on-real-data
  - decisions/e2e-gaps-of-1-2-before-release
  - problems/bcrypt-blocks-the-event-loop
  - sources/phase00-data-quality-e2e-2026-10
  - problems/test-passed-only-on-leftovers-of-other-tests
---

# Problem: tests that changed the world for their neighbours

## Symptom

After V-7 — a broker created and deleted on the shared `TEST_USER` that turned a neighbouring spec red — the developer
asked for more work for workstream V, and the coordinator gave it an audit of the E2E suite's writes (plan 46, work 3,
step 2; 2026-10-12). Five read-only audits of `frontend/e2e/**` (the gallery excluded) found tests that wrote shared
state and never put it back. The damage was then proved before any cure, on the lane's database read in read-only
mode:

- **A2** — «language change persists» saved Italian for `TEST_USER`, and every later session of that user saw the app
  in Italian (the English check of `connection-security.spec.ts`, for one). The sibling «theme preference persists»
  saved nothing at all: its selector `[class*="dark"]` matched a row container through Tailwind's `dark:` classes.
- **A3** — FSCH-006 and FSCH-006b left the global current-price frequency at 20 instead of the seed's 10. Saving the
  scheduler modal rewrites **five** global keys at once (the frequency, the history sync times, days and horizon, the
  timezone), and the two tests, running in parallel, overwrote each other: the last writer won.
- **A1** — T7 of `fx-sync.spec.ts` rewrote 65 EUR-USD rows with real ECB fixings fetched from the network (2026-07-14
  went from the seed's 1.11247… to 1.1405), and cleared the portfolio cache. And it proved nothing: it waited only for
  the sync summary, which also appears when the sync fails, so offline it stayed green. A twin did the same in
  `fx-detail.spec.ts` (A1b).

## Root Cause

How a write spreads, as the audit mapped it:

- **Inside a category**, tests run in parallel (`fullyParallel`): a temporary write on a shared user breaks the
  neighbours of the same category — the class of V-7.
- **Across categories**, which run one after another (ai-export, asset, broker, fx, portfolio, transaction, user,
  utility), the database is populated once per invocation: a permanent leftover reaches every later category.
- **The automatic clean-ups** — the transaction hygiene of `fixtures/playwright.ts` and the mock restore — work only
  at one worker.

The audit's list, «A», all to be cured (coordinator): A1 the real network sync; A2 the saved preferences; A3 the
scheduler keys; A4 real commits into the seed brokers of `TEST_USER`, never deleted at four workers; A5 seed pairs
split or edited; A6 a permanent DIVIDEND on a global asset; A7 brokers of `TEST_USER` that pile up (two more cases
found while counting V-15).

## Solution

**Checkpoint 2a, train 64** (the ones that dirty global state), each with its proof of damage first:

- **A1** (`495fb9e86`): each test owns a **reserved MOCKFX pair** — EUR-TTD and EUR-JMD for T7, EUR-GTQ and EUR-HNL for
  the twin, real ISO codes nothing else uses — created and removed in the spec's fixture, with the clean-up in its
  `finally`, so a timeout cannot leave it behind. The page opens on an explicit ten-day window; the test asserts the
  request, the response (validated by the generated schema: 10 fetched, 10 changed), the modal's counts read from
  `data-*`, and the rates read back through the API. After each run: nothing on the four codes, no EUR-USD row written
  after the seed.
- **A2** (`6d62171e3`, with the attributes of `e6333930c`): the two writing tests run on a **disposable account**, with
  `en`/`light` set through the API before the login and the account deleted in `finally`; options are picked by test id
  (`setting-theme-option-*`, `setting-select-option-*`) and checked through the PUT body, the
  `settings.preferences.saved` event and `GET /settings/user`. The theme test now really saves.
- **A3** (`6d62171e3`): each writing test **reads the five scheduler keys first and restores them in `finally`**
  through the admin bulk PATCH, then reads them back; FSCH-006 and 006b run in a nested serial `describe('Saving')`.
- The About tab now publishes `data-busy` and `aria-busy`, so its tests wait for a state instead of a clock.

Proved at one and four workers (`front-fx fx-sync` 3/3, `fx-detail` 17/17, `front-utility settings` 45/45,
`scheduler` 17/17), with the database clean after each run.

**Then open** (done in train 72, below): checkpoint 2b, A4–A7, with the two new A7 cases (`tx-import-resolution` IWR-009,
`tx-clone`'s «clone inside the workspace»). The damage of A7 was proved on the database in train 66's journal (§12.7):
`Test Broker`, `Private Broker`, `Unique Broker` and `T3-ws-…` left on `TEST_USER`; IWR-009 instead passes in silence —
its selector exists only with files pending, the test adds none, so it always leaves through its conditional `return`.
After A1–A7, the developer wants the seven E2E gaps of 1.2 closed on the
same rules — [[decisions/e2e-gaps-of-1-2-before-release]].

**Checkpoint 2b, train 72**, each item with its damage proved first, then green at one and at four workers:

- **A4** (`1b1e58fd0`): the four `tx-commit` specs left 26 transactions behind at every run; they now record their
  writes and delete them by id after each test, and FM6 opens its own pair by id.
- **A5, A6** (`7074fd7d1`): the seed-pair specs had altered the pairs 43↔44 and 45↔46 and added a DIVIDEND on Apple;
  C3 and TODO-B now work on a disposable account with their own pair, A6 on its own manual asset.
- **A7, A7b, A7c** (`ad16a4d3c`): the broker writes moved to disposable accounts; IWR-009 and `tx-clone` delete what
  they create, by id.
- **V-20** (`d60937c08`): the fixed 3 s waits of `auth`, `app-start-auth` and `files` became waits on the state the
  page publishes.
- **WB4, WB5** (`1ea16aace`): the cleanup unmasked a test that passed only on the leftovers of others —
  [[problems/test-passed-only-on-leftovers-of-other-tests]].
- The Playwright configuration's notes now match its parallel mode and its five serial blocks (`5139f4014`).

The category gates at four workers were green but for V-19 (the Spanish toolbar, fixed in the same train by
workstream I), one mobile case red only under load, and WB5; `front-transaction all` passed 327 of 327 on the
re-run.

**Then open** (after 2b): V-21, the probes and forbidden selectors left in the cleaned specs, and the File Preview
tests, which never delete their upload; V-17's two runner points; V-18. With A1–A7 done, the seven E2E gaps of 1.2
came next — delivered in train 76 ([[decisions/e2e-gaps-of-1-2-before-release]]).

*Train 76*: `files.spec.ts` now registers every upload and deletes it, with the BRIM broker of its import test, in
`afterEach` (`eb269ecde`) — V-21's upload item. **Still open**: V-25 (`tx-delete` uses up a seed FEE and a seed pair,
and one test leaves a broker on purpose), 12 upload files left by an earlier run that the populate step does not
clean, the rest of V-21 (probes and forbidden selectors, which leak nothing), V-17's two runner points, V-18.

*Train 82*: V-25 is cured — `tx-delete` creates and deletes only its own rows, through the new fixture
`frontend/e2e/fixtures/owned-pair.ts` (`5d5c7caed`); after a run it had left 73 transactions, 9 brokers and 18 assets
against the seed's 76, 8 and 17. V-21 in part: the transaction specs lost their probes and fragile selectors
(`e01289a65`), and files and logout wait on the page's state (`34fb7ca37`); T1, T4, T5/T8, T13, A6 and the B3 guard
wait on questions to the developer. A finding: after midnight the seed holds more exchange rates (4 140), because
the populate's ECB window follows the calendar — so the no-leak check now proves that no rate is written after the
populate, instead of counting them. **Still open**: the rest of V-21, V-17's two runner points, V-18.

*Train 87*: two more leaks of the V-25 class, cured. `fx-destructive` said it used pairs outside the seed, but EUR/PLN
and EUR/SEK have been in the seed since `a3a9ead52`, as ECB legs of other chains: its «clean slate» deleted both
pairs' 2 × 276 rates (`fx_rates` 4 140 → 3 588). It now uses currencies checked free of the seed, registers its
pairs before creating them and deletes only those (`586fd8aca`); its `beforeAll` checks, read-only, that no pair
already has routes or rates, and fails without touching anything otherwise — proved red on purpose. The asset specs take each id from the `POST` response and delete it in `afterEach` (`ba1c34d64`): after
every round the database is back at the seed's 17 assets. New in the backlog: V-31 (the mock FX sync leaves its
rates), V-32 (asset specs that pick rows by position), V-34 (a cleanup that checks only the HTTP status). **Still
open**: the rest of V-21, V-17's two runner points, V-18.

## Prevention

- A test that writes shared state owns it: its own account, its own reserved pair, or a read-and-restore in `finally`;
  writers of the same global keys run in sequence.
- Wait for the outcome, not for the summary: a test that also passes when the action fails proves nothing.
- Prove the damage before the cure, on the database itself.
- Left in the backlog: V-15 (about 27 specs that create and delete `TEST_USER` brokers by id — transient, within their
  category, no red shown), V-17 (the runner's `settings` key also picks `fx/fx-chart-settings.spec.ts`, and Playwright's
  setup repopulates after the runner did), V-18 (CSS and English selectors left in the settings tests), V-20 (3 s waits
  on the first navigation, red under load).

## Source files

| Role | Path |
|------|------|
| A1: reserved pair for T7 | `frontend/e2e/fx/fx-sync.spec.ts` |
| A1b: reserved pair for the twin | `frontend/e2e/fx/fx-detail.spec.ts` |
| A2: disposable accounts | `frontend/e2e/settings.spec.ts` |
| A3: read and restore the scheduler keys | `frontend/e2e/settings/scheduler.spec.ts` |
| Theme option test ids | `frontend/src/lib/features/settings/SettingTheme.svelte` |
| Select option test ids | `frontend/src/lib/features/settings/SettingSelect.svelte` |
| About tab busy state | `frontend/src/lib/features/settings/tabs/AboutTab.svelte` |
| Transaction hygiene (one worker only) | `frontend/e2e/fixtures/playwright.ts` |
| Disposable account helpers | `frontend/e2e/fixtures/onboarding-accounts.ts` |
| `fullyParallel: true` | `frontend/playwright.config.ts` |
| Journal (§12.3, §12.5) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
