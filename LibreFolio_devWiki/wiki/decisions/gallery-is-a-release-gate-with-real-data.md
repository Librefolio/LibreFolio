---
title: "The gallery is a release gate, shot from real data: no invented fixture, disposable accounts, no network, reduced motion, screens as tall as their subject"
category: decision
status: resolved
date: 2026-10-07
updated: 2026-10-12
tags: [ci, release, gallery, screenshots, playwright, e2e, fixtures, offline, reduced-motion, docs, workstream-m, release-1.2]
related:
  - features/F-074
  - concepts/ci-release-pipeline
  - problems/playwright-favicon-aborted-by-routes
  - problems/playwright-probes-ignore-timeout
  - problems/gallery-price-guard-expected-tofixed-text
  - problems/release-images-shipped-debug-frontend
  - decisions/pdf-preview-viewer-only-local-assets
  - sources/phase00-release-images-and-gallery-2026-10
---

# Decision: a release cannot ship a missing or invented screenshot

## Context

On 2026-10-07 the nightly run `37533864185` ended with 13 gallery failures in 7 scenarios. Earlier failures had
passed unseen: the gallery step ended in `|| echo ::warning::` on every branch, a published release included. The
day before, the release images had been fixed so that the full image really carries the screenshots
([[problems/release-images-shipped-debug-frontend]]): a broken shot would now ship inside the image and on the
documentation site. The dashboard shots also rendered an empty dashboard: the captured report the spec serves,
`frontend/e2e/dashboard-report.json` (2026-09-04), no longer passed the API schema (`yield_on_cost` had become
required), and Zodios rejected it.

## Decision

The developer's four decisions (plan R12, §0, 2026-10-07):

| # | Decision |
|---|----------|
| D1, the fixture | «se il dashboard-report.json è diventato obsoleto perché abbiamo aggiunto campi, non fargli inventare nulla, dimmelo e ne fornisco uno nuovo da una build recente». M did not touch the fixture; it sent the capture procedure, and the new capture went through `scripts/normalize_dashboard_fixture.py` (`c80508be8`) |
| D2, the gate | The gallery blocks releases and stays tolerant on `dev` |
| D3, retries | Kept: «i retry servono, e se tutto gira non si perde tempo, mentre se fallisce ci dà, attraverso i log, la sicurezza che non è stato momentaneo» |
| D4, the runner | No pin: «non è un problema, le emoji già ora cambiano nei vari OS. Lasciamo com'è». Only `ImageOS` joins the cache keys, so that no 24.04 cache is restored on 26.04 |

Then the rules for the new scenarios, approved for groups 3–7 of the repairs:

- **Disposable accounts.** One `demo_<token>` account per test, taken through the Welcome with every guide skipped and
  deleted in `afterEach` with its brokers and files; `hideGalleryTempData` hides, from each session, the marked
  brokers and files of other tests that the session cannot reach.
- **Injected responses only where real data is not enough**, and no change to `populate_mock_data.py`.
- **No network** (`73680c052`, 2026-10-08). `guardGalleryOffline`, installed before any sign-in, aborts and fails the
  test on any provider sync a scenario presses; answers the live-price poll and the exchange-rate provider catalogue
  from `galleryOfflineData.ts`; aborts the admin's check of the latest GitHub release; and aborts, and fails the test
  on, any third-party host. `expectGalleryOffline` reads the record at the end of each test. The last rule is why the
  PDF viewer had to serve its own engine and fonts ([[decisions/pdf-preview-viewer-only-local-assets]]).
  *Update (train 70)*: the cards' live prices, answered from that file, are checked as the shot's locale writes them
  — [[problems/gallery-price-guard-expected-tofixed-text]].
- **Reduced motion for every shot** (`02ae0e09d`, 2026-10-09). A name too long for its box scrolls as a marquee
  (`scrollOnOverflow.ts`) 2 s after mounting, a loop that freezing animations cannot stop, so shots caught names
  mid-scroll. The gallery's context now has `reducedMotion: 'reduce'`; a full comparison changed 659 of 2,796 PNGs.
- **Screens as tall as their subject** (`d7481a7e7`). `extendScreenToBlock` grows the window to the block to shoot.
  Playwright's `fullPage` was dropped: it keeps the 720 px screen, so the fixed sidebar stops at 720 and the page
  below is blank.
- **A hung action fails in 20 s** (`actionTimeout: 20_000`), naming the real step, instead of at the four-minute test
  timeout.

## Options Considered

- **Fake the missing fields of the old fixture.** Refused by D1: a screenshot must show what a real build returns.
- **Pin the runner image** so that screenshots never change with the OS. Refused by D4.
- **Drop the retries** to make failures cheaper. Refused by D3: a retry that passes costs nothing, one that fails
  proves the failure was not momentary.
- **`fullPage` for long lists.** Tried and dropped (above).

## Consequences

- In `release.yml` the gallery step is `continue-on-error` only on `dev`; a nightly lists it in its job summary, any
  other run fails ([[concepts/ci-release-pipeline]], «Release gates and nightly tolerance»).
- A full run during the repairs (step 18, 2026-10-08/09, two workers): 243 passed, 1 skipped, in 1.1 h, 2,796 PNGs.
- Every shot depends only on the test database and the fixtures, never on the day's network or on another test.
- Two traps of Playwright 1.61 surfaced along the way: images ending in `/favicon.ico` aborted by any route
  ([[problems/playwright-favicon-aborted-by-routes]]), and probes that ignore their timeout
  ([[problems/playwright-probes-ignore-timeout]]).
- The screenshots are generated, never committed: the PNGs under `mkdocs_src/docs/gallery/` are git-ignored.

## Source files

| Role | Path |
|------|------|
| Gallery spec (options, dashboard fixture helpers) | `frontend/e2e/gallery.spec.ts` |
| Offline guard, temporary data, favicon init script | `frontend/e2e/fixtures/galleryReportSets.ts` |
| Offline answers | `frontend/e2e/fixtures/galleryOfflineData.ts` |
| Tall screens | `frontend/e2e/fixtures/galleryTallShots.ts` |
| Dashboard fixture | `frontend/e2e/dashboard-report.json` |
| Fixture normalization | `scripts/normalize_dashboard_fixture.py` |
| Fixture schema guard (Vitest) | `frontend/src/lib/api/dashboardReportFixture.test.ts` |
| The marquee that reduced motion stops | `frontend/src/lib/actions/scrollOnOverflow.ts` |
| Release gate | `.github/workflows/release.yml` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseGallery.prompt.md` |
