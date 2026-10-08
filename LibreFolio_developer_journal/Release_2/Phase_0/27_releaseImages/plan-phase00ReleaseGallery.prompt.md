# Plan Phase 00 — Release pipeline: gallery repairs, release gate, Docker `latest`, translation alignment plan

**Creato**: 2026-10-07
**Baseline/target**: `d07412899` (`dev_release2`, train 8), fast-forward at 13:25, HEAD verified clean
**Workstream**: M — branch `e-alfy-cloud-resource-sizing`, worktree `LibreFolio-worktrees/e-alfy-upgraded-telegram`
**Coordinator**: session `c8328a01-f208-4ade-a352-0486d1f14de2`
**Runtime lane**: ports `6158`/`6168`, data dir `/tmp/librefolio-r2-m`. Evidence outside the repo in `LibreFolio-cloud-sizing/release-pipeline/` (`r12_analysis.md`, `r12_translation_debt.{py,json}`, gallery log of run `37533864185`).
**Previous plans**: [plan-phase00ReleaseImages.prompt.md](plan-phase00ReleaseImages.prompt.md) (images, gzip, Tailscale, startup timeout) · [plan-phase00TranslatedCodeIndent.prompt.md](plan-phase00TranslatedCodeIndent.prompt.md) (step 8, closed)
**Origin**: nightly `37533864185` (`v1.1.0-789-g24d26ea27`): 13 gallery failures in 7 scenarios; `translate-diff`, `translate-validate` and `check-links` red; the `ubuntu-latest` → 26.04 annotation.
**Autorizzazione developer**: plan approved in M's session on 2026-10-07 (exit from plan mode, interactive). Decisions relayed by the coordinator the same day.

## 0. Decisions (developer verbatim where quoted)

| # | Decision |
|---|---|
| D1 fixture | «se il dashboard-report.json è diventato obsoleto perché abbiamo aggiunto campi, non fargli inventare nulla, dimmelo e ne fornisco uno nuovo da una build recente». **M does not touch the fixture.** M sends the exact capture procedure. Once the capture arrives: `mkdocs normalize-dashboard-fixture`, the vitest guard, and dashboard scenarios that verify the report loaded before taking any shot. |
| D2 gallery gate | Yes: the gallery blocks releases and stays tolerant on `dev`. |
| D3 retries | No change: «i retry servono, e se tutto gira non si perde tempo, mentre se fallisce ci dà, attraverso i log, la sicurezza che non è stato momentaneo». |
| D4 runner | No pin: «non è un problema, le emoji già ora cambiano nei vari OS. Lasciamo com'è». `ubuntu-latest` stays, `manual-test-run.yml` included. **Only `ImageOS` is added to the cache keys**, so that from 19/10 no 24.04 cache is restored on 26.04. |
| D5 lane | `db populate --force --clean` only on `/tmp/librefolio-r2-m`, with `LIBREFOLIO_TEST_DATA_DIR` and `--test-port 6158`. |
| D6 anchors | The `scheduled-investment` EN anchors are Q's (page owner). |
| D7 probes | Only on the paths touched now; the full sweep of the 91 probes goes with Q's inventory. |
| Docker tags | «Correggere il workflow: latest = light».<ul><li>In `release.yml`, `latest` moves from the full-variant metadata to the light-variant metadata, and `latest-light` disappears.</li><li>The nightlies stay as they are: `nightly` = full, `nightly-light` = light.</li><li>The guide and the CHANGELOG are already right and are not touched.</li></ul> |
| Docs | `mkdocs_src/docs/developer/docs/release-pipeline.md` goes to M, via docs-writer, EN only. It has three errors found by Q: <ul><li>`vX.Y.Z` tags;</li><li>a gallery cache that does not exist;</li><li>a `file:///Users/…` link published on the site.</li></ul> It is also aligned with the correct tags. |
| Translations | Plan only. The developer decides when to run it, after Q, P, L and N close their EN pages. |
| Constraints | <ul><li>The full gallery runs only after the coverage run ends, and with the coordinator's OK; until then, single scenarios with 1 worker.</li><li>Image names for Q's inventory go through the coordinator. Q uses placeholders `<!-- [Screenshot Placeholder: <name> — <what>] -->`.</li><li>FROZEN and a handoff before any commit.</li></ul> |

## Sintesi (italiano)

- **Gallery.** Le 7 cause, in breve:
  - la modale di aggiornamento interroga ora il backend;
  - tre scenari della dashboard usano una fixture reale non più valida per lo schema (`yield_on_cost`): la ricattura il developer;
  - la dashboard vuota su mobile è una sonda `isVisible` troppo presto;
  - nel wizard «Continua» è disabilitato finché ci sono proposte aperte, e il click aspetta 10 minuti;
  - il popover degli eventi è da confermare con un'esecuzione locale.
  - Le riparazioni le scrive il test-author in `gallery.spec.ts`, più un `actionTimeout` che fa fallire in fretta.
- **Rilascio.** La gallery ora blocca i rilasci e resta tollerante su `dev`. `latest` passa alla light. `ImageOS` entra nelle chiavi di cache.
- **Traduzioni.** Da allineare: 80 pagine, 240 coppie. Tutti gli errori dei gate stanno lì; le coppie aggiornate sono pulite. Il piano a lotti è al §4; la decisione è del developer.

## 1. Findings (detail: `LibreFolio-cloud-sizing/release-pipeline/r12_analysis.md`)

- **History.** Gallery runs:
  - v1.1.0 (09-07): 180 passed, 1 flaky;
  - nightlies of 09-22 and 09-29, and 10-05: 12 failed, always the same 6 scenarios × 2 devices;
  - 10-06: 13 failed (+ mobile empty state).
  - The failures are deterministic and cost ~37 % of the gallery's worker time.

| Line | Scenario | Cause | Since |
|---|---|---|---|
| `:237` | update-available modal | The image gate now goes through the same-origin `GET /api/v1/system/container-image-status`. The spec still mocks the browser's `ghcr.io` manifest request, which is never made. | `ef722b552` 09-09 |
| `:526` `:678` `:812` | main dashboard, positions, data-quality banner | The captured `frontend/e2e/dashboard-report.json` (09-04) fails the current schema: `summary.holdings[*].yield_on_cost` is required. Zodios rejects the mocked report, so the dashboard shows no history: `%` is disabled, and there is no exposure table and no banner. | `74afcebce` 09-11 |
| `:792` | empty state (mobile) | `openMobileMenu()` probes `isVisible()` the instant `login()` returns. The drawer stays closed, so the logout button stays off-canvas. | 10-06 |
| `:2222` | import wizard conditional steps | Since 09-14 the assets-step Continue is disabled while proposals are open. The click waits out the 10-minute test, and the `finally` masks the error. | `580bd504f` 09-14 |
| `:3325` | asset event popover | Not proven statically. The first combo passes, every later one fails, and the fallback returns silently. Prime suspect: the date-range probe (`isVisible({timeout})` does not wait). To be confirmed by a local run. | 09-07 → 09-22 |

- **Systemic:**
  - 91 `isVisible({timeout})` probes: Playwright ignores that timeout and answers at once;
  - no `actionTimeout`;
  - scenarios that use the fixture pass on an empty dashboard (allocation charts, `main`/`kpi-top`, mobile menu).
- **Translations (HEAD):**
  - 205 pages / 615 pairs: 375 fresh, 174 stale (58 pages), 66 new (22 pages);
  - **alignment set: 80 pages / 240 pairs**, ≈ 2.04 M EN characters, ≈ 6.2 M tokens by the pipeline's estimate;
  - **every gate issue is in that set**: 694 diff anomalies, 675 validate ERRORs, 66 missing files. The fresh pairs have 0.
- **Ubuntu:**
  - `actions/runner-images#14748` rolls `ubuntu-latest` to 26.04 between 10-19 and 11-19;
  - Playwright 1.61.0 and Python 3.13.16 already support 26.04;
  - the cache keys today use only `runner.os`.

## 2. Steps

1. Journal plan (this file), cross-linked.
2. D1 capture procedure → coordinator.
3. Gallery repairs, test-author, `gallery.spec.ts` only:
   - a spec-wide `actionTimeout`, and a `finally` guard;
   - `:237` mock of the backend image gate;
   - `:792` user switch without the UI logout;
   - `:2222` confirm the proposals, then Continue;
   - `:3325` diagnose first, then a deterministic fix.
4. Single-scenario verification on lane 6158, `--workers 1`, desktop and mobile (D5).
5. `release.yml`:
   - the D2 gallery gate;
   - `ImageOS` in the cache keys;
   - `latest` on the light metadata, with `latest-light` removed, and release notes aligned.
   - Then the `utils release-image-contract` gate, its tests updated by test-author if they pin the old mapping.
6. `developer/docs/release-pipeline.md` via docs-writer (EN).
7. After the D1 capture lands:
   - normalize it;
   - the vitest guard;
   - dashboard scenarios that assert the report loaded.
8. Q's inventory scenarios: names through the coordinator.
9. Handoff, then FROZEN.

## 3. Definition of done

- Every repaired scenario passes alone at `--workers 1`, on desktop and mobile, in the lane.
- The full gallery is green once the coverage run has ended and the coordinator has given the OK.
- `utils release-image-contract` is green.
- `mkdocs build` strict and `check-links` pass for the docs change.
- `git diff --check` is clean, and no ignored artifacts are staged.

## 4. Translation alignment plan (the developer runs it, on explicit request only)

0. **Preconditions.**
   - Q, P, L and N have closed their EN pages, and `dev_release2` is integrated.
   - `utils translation-code-blocks` is green.
   - Q has added the explicit `{: #how-value-is-calculated }` and `{: #interest-schedule-editor }` anchors to `user/assets/providers/scheduled-investment.en.md` (D6).
   - M recomputes the lists with `r12_translation_debt.py` (read-only).
1. **Batches**, each with `./dev.py mkdocs translate --file '<glob>' --dry-run` first:
   - A `user/**`;
   - B `admin/*`;
   - C `financial-theory/**/indicators/*` + `asset-types/*` + `performance-metrics/**`;
   - D `financial-theory/**/risk-metrics/**` (17 new);
   - E the remaining new pages (`user/tools/**`, `user/assets/correlation`, `danske-bank`).
2. **After each batch:**
   - `translate-diff --issues-only`;
   - `translate-validate --hide-localized`, which must report 0 `code-block-indent`;
   - `check-links`;
   - `mkdocs build` strict;
   - `utils translation-code-blocks`.
3. **Residuals.** The developer re-runs the file with `--force`. No hand translation.
4. **End.**
   - All three docs gates exit 0.
   - `rolling-return` resolves (the `user/assets/detail/chart` page is stale and gets re-translated).
   - Remove the closed `MKDOCS_ANCHOR_EXCEPTIONS` entries: the list only shrinks.

## Progress (after every step: ✅ with date, «Note implementazione», «Fuori pista»)

### 1. ✅ Journal plan and cross-links — 2026-10-07
> **Note implementazione**: this file. Forward links were added to `plan-phase00ReleaseImages.prompt.md` (header + Progress §10). The analysis and scripts are copied to `LibreFolio-cloud-sizing/release-pipeline/`.

### 2. ✅ D1 capture procedure; first capture normalized and installed — 2026-10-07
> **Note implementazione**:
> - The procedure went to the coordinator: build ≥ `d07412899`, 1Y, EUR, all brokers, and the main `POST /api/v1/portfolio/report` request, saved outside the repo.
> - The first capture (`include_breakdown`/`positions_contribution`/`pnl_candles` false, `broker_ids` `[2,1]`) was normalized by the repo script through a silent wrapper. The script prints the real net worth, and so would the scale ratio; the wrapper prints neither.
>   - Invariants: 0 errors.
>   - **Leaf-by-leaf proof**: 37 763 numeric leaves scaled by the same factor; 1 546 unchanged, all percent/ratio/id/count/quantity keys; 195 zero; 0 other ratios. That covers every new section: income, cost, deposit, acquisition funding, broker P&L.
> - Zod, with the client regenerated at HEAD (`api sync`, ignored files only): the new capture is **valid (0 issues)**; the old fixture fails with `invalid_union: summary`.
> - Copied to `frontend/e2e/dashboard-report.json`. The raw file and the working copy were deleted.
> - Evidence: `release-pipeline/fixture_normalize_proof.py`, `fixture_proof_dryrun.txt`.
> **⚠️ Fuori pista**: the developer is now taking a single **«all sections true»** capture (breakdown, positions contribution, P&L candles). Once validated, it replaces this one and the separate candles capture, and the spec then serves one coherent snapshot to every report request. `scripts/normalize_dashboard_fixture.py` was extended for the three plain-number money fields of `positions_contribution` (`gross_gains`, `gross_losses`, `period_unrealized_delta`); the logic is unchanged. The console capture snippet is documented in the script's docstring.

### 3. ✅ `release.yml` — 2026-10-07
> **Note implementazione**:
> - The new step «Expose the runner image for cache keys» exports `RUNNER_IMAGE_OS=${ImageOS:-unknown}` to `$GITHUB_ENV`. Pipenv, npm and Playwright cache keys and restore-keys now include it. `ImageOS` is a runner variable, not part of the expression `env` context.
> - The gallery step has `continue-on-error: ${{ github.ref_name == 'dev' }}` with no `|| echo ::warning::`, and the nightly report reads `steps.gallery.outcome` (D2).
> - Docker metadata: the full variant has `flavor: latest=false` and no raw `latest`. The light variant has `flavor: latest=auto` plus raw `latest` on `main`. `latest-light` is gone. Before, both variants pushed `latest`, and the light one won only because it was pushed second.
> - The release-notes snippet now names the variants: `latest` light, `X.Y.Z` full, `X.Y.Z-light`.
> - `utils release-image-contract`: 17/17 (the existing generic check already forced the report to read the gallery). Contract tests for the new rules are with test-author.

### 4. ✅ Single «all sections» capture replaces the fixture — 2026-10-07
> **Note implementazione**:
> - The developer's capture had every `include_*` set to true; it replaces both the first capture and the planned separate candles capture.
> - `scripts/normalize_dashboard_fixture.py`: `SCALE_NAME_RE` now also matches `gains`, `losses` and `^period_unrealized_delta$`.
>   - A schema walk of `PositionsContribution` shows that the 11 plain money fields are now all covered: `period_unrealized_delta`, `period_realized_gain_loss`, `period_income`, `period_fees_taxes`, `period_pnl` (positions and other effects), `start_value`, `end_value`, `unallocated_income`, `unallocated_fees_taxes`, `gross_gains`, `gross_losses`.
>   - `PnlCandleSeries` uses `Currency` objects only.
>   - The logic is unchanged.
> - **Leaf-by-leaf proof**, from the silent wrapper, which now also masks non-snake_case keys:
>   - 39 290 leaves scaled by the same factor, including `pnl_candles` 1 464/0/0 and `positions_contribution` 57 scaled, 50 unchanged (ids, `period_pnl_percent`, `annualized_return`), 8 zero;
>   - 1 600 unchanged leaves in total, all percent/rate/id/count/quantity keys;
>   - **0 leaves with any other ratio**.
>   - Free text: no amounts (the only digit runs are a bond ticker).
> - Zod (client regenerated at HEAD): **valid, 0 issues**. Pydantic: only the 2 output-only `data_quality_status` echoes.
> - Installed atomically: 366 history points, 10 holdings, 14 contribution positions, 366 candles, 2 broker P&L series, net worth 50 000. `dev.py mkdocs normalize-dashboard-fixture --dry-run` on the installed file gives ratio 1, so the invariants hold.
> - **Raw capture and working copy deleted** from `/tmp`.
> - **Capture method for the future** (also in the script's docstring):
>   1. In the browser console, run the `fetch` of `POST /api/v1/portfolio/report` with every `include_*` true, ≥ 2 brokers, 1Y, EUR, storing it in `window.lfReport`.
>   2. Then, as a **separate** command, `copy(JSON.stringify(window.lfReport))`. Chrome has no `copy()` inside a block that uses `await`.
>   3. Alternatively, copy the response from the Network panel.
>   4. Save the result outside the repo, normalize it, validate it with Zod, copy it into the repo, and delete the raw file.
> - Still to do: the spec must serve this fixture to **every** report request (the live merge for the positions tab and candles goes), and the dashboard scenarios must assert that the report loaded. That is round 2 of test-author, after round 1 closes on `gallery.spec.ts`.

### 5. ✅ Contract tests for `release.yml` (test-author) + push guard — 2026-10-07
> **Note implementazione**: `backend/test_scripts/test_utilities/test_release_image_contract.py`, **55 passed** (17 existing + 38 new); ruff and black are clean.
> - `TestCacheKeys`: the `RUNNER_IMAGE_OS` export comes before the first cache, and every key and restore-key includes it.
> - `TestGalleryGate`: soft only on `dev`; the gallery is the last command of its step, with nothing that can mask its failure.
> - `TestImageTags`: models the metadata-action rules (flavor, suffix, `enable`). On a release the full variant gets exactly `{{version}}`, and the light one `{{version}}-light` + `latest`. The nightlies are `nightly` and `nightly-light`. `latest-light` is gone.
> - `TestReleaseNotes`.
> - 24 negative controls, plus a control on unmutated copies.
> **⚠️ Fuori pista**: test-author found that on a manual `workflow_dispatch` from `main` the full metadata now yields **no tag**, and the push fails ("tag is needed when pushing to registry"). The failure also blocked the light `latest` push and the gh-pages deploy. The same failure already existed for manual runs from any other branch (e.g. the 09-23 dispatch on `dev_release2`).
> - Fix: both build steps have `if: steps.<own meta>.outputs.tags != ''`.
>   - Manual run from `main`: the light variant publishes `latest`, and the full variant is skipped (the guide publishes it only as `X.Y.Z`).
>   - Manual run from another branch: nothing is pushed.
>   - Releases and nightlies: unchanged.
> - 55/55 after the change; test-author is pinning the guard.
> - Flagged to the coordinator: user-facing `latest-light`, outside M's surfaces, at `README.md:131` and `docker-compose.prod.yml:6-11`.

### 6. ✅ Tags aligned outside the workflow (granted by the coordinator) — 2026-10-07
> **Note implementazione**:
> - `README.md:131`: `latest` is the light image; each release is also `X.Y.Z` (full, offline) and `X.Y.Z-light`; no `v`; links to the guide's «Image Variants».
> - `docker-compose.prod.yml` header comments: the three GHCR tags with their variants, no `v`, and how to pin through `LIBREFOLIO_IMAGE` (the variable the file already reads). `docker compose config` exits 0.
> - `scripts/test_runner/_backend_utils.py`: only the `desc` of `release-image-contract` (line 313) now lists the R12 rules. Ruff and black are clean.
> - **Not changed:** `.github/skills/devpy-tools/devpy-docker/SKILL.md:44`. The local `dev.py docker build` tags come from `git describe` and keep the `v` (`librefolio:v1.2.3-light`), so the example is right for local builds, as the coordinator specified.

### 7. ✅ `release-pipeline.md` (docs-writer) and the workflow fixes it surfaced — 2026-10-07
> **Note implementazione**: docs-writer rewrote the page against the workflow, 161 → 249 lines:
> - the `file://` links are gone;
> - the screenshot cache and `force_gallery` are removed;
> - the F14 section is corrected;
> - §1–§6 describe the real runner, caches, docs checks, gallery, gate, images, deploy, artifact and release notes.
>
> From its «surprising» list, M fixed these in `release.yml`:
> - **Push order**: the light build now comes before the full one. The update prompt's image gate probes the plain `X.Y.Z` tag (`container_registry.py`), which is the full variant, so pushing it last means `latest` and `X.Y.Z-light` exist when admins are prompted. If the light build fails, nobody is prompted.
> - **Evidence**: `Archive Generated Screenshots` runs under `!cancelled()`. The new step `Archive Playwright report (gallery failures)` uploads `frontend/playwright-report/` and `frontend/test-results/` for 3 days whenever the gallery failed, on `dev` too.
> - **Stale comments**: «Single Image», the VERSION/gallery-PNG claim, the 120 s webServer budget.
>
> Contract test: 67/67 on the current workflow. test-author is pinning the order and the evidence step. docs-writer is updating the page for the guard, the order and the artifacts.
> **⚠️ Fuori pista** (reported, not changed):
> - prereleases deploy the docs and append a `:latest` line;
> - images are amd64 only;
> - `run-name` reads «Release » on non-release runs;
> - outside M's surfaces: `file://` links in `developer/test-walkthrough/runner_architecture.md:730-739`, the stale devWiki `concepts/ci-release-pipeline.md`, and the `+layout.svelte:108` comment (24 h vs 1 h).

### 8. ✅ Gallery repairs round 1 (test-author) — lane verification — 2026-10-07
> **Note implementazione**: `frontend/e2e/gallery.spec.ts`:
> - A: `actionTimeout` 20 s.
> - B: the backend image-gate mock; route hit counters.
> - C: logout via API + `clearCookies` + `/auth/me` identity.
> - D: confirm the asset proposals → Continue enabled; the Parse gate is named; `finally` respects `page.isClosed()`.
> - E: strict MAX preset, a route log, and a diagnostic that fails loudly.
>
> Lane 6158, 1 worker, load 17–40:
>
> | Scenario | Result |
> |---|---|
> | `:792` empty state | ✅ desktop + mobile, 16 shots, ~10 s per device (CI: 4 min timeout); image checked: empty user's dashboard |
> | `:2222` import wizard | ✅ desktop 44 s, mobile 59 s (CI: 10 min timeout); 4 steps × 8 combos each, fix/duplicates/compare included |
> | `:237` update modal | modal **now appears**; the test stops at the pre-existing `waitForSelector('html[data-i18n-ready]')`, which waits for *visible* while Playwright reports `<html>` hidden under the open modal → wait on the attribute instead (test-author, next round) |
> | `:3325` event popover | ❌ **product bug, confirmed**: the route answered 1 event for asset 1 (`start=min&end=max`), the chart drew 0 |
>
> **Product bug**: `routes/(app)/assets/[id]/+page.svelte` `loadChartData()`.
> - `:1642` captures `requestedStart`.
> - On a price-cache hit, `:1705` `resolveMaxStartFromChartData()` moves `dateStart` from the «All» sentinel to the first price date.
> - The events-only request then fails `:1654` `dataRequestIsCurrent()` and is discarded.
> - Users opening an asset from the list with «All» see no event markers. Introduced by `2d22130bd` (09-17).
> - Reported to the coordinator: product code, not M's. It blocks 1.2 now that the gallery gates releases.
>
> Evidence: `LibreFolio-cloud-sizing/release-pipeline/runs/*.log`.
> **⚠️ Fuori pista**: Q's notes for the placeholder replacement (`32_docsEnglish12/…` §S6):
> - add the `---` separators on the gallery pages;
> - update the Growth carousel sentence with the P&L shots;
> - the home Tools block returns to «deep-dive reverse» with `tools/hub`.

### 9. ✅ Prerelease rule (developer) — 2026-10-07
> **Note implementazione**: «Sì, escluderle da latest e dal deploy della doc».
> - The light flavor is `latest=${{ (release && !prerelease) && 'auto' || 'false' }}`. It is never `true`: metadata-action's `procRaw` would add `latest` to raw tags, `nightly-light` included.
> - Deploy runs only on `main` or a non-prerelease release.
> - The release notes print the `latest` line only when `PRERELEASE != true`. Simulated with bash: the stable `v1.2.0` notes pull latest + `1.2.0` + `1.2.0-light`; the prerelease `v1.2.0-rc.1` notes pull only `1.2.0-rc.1` + `1.2.0-rc.1-light`.
> - The contract-test parsers read the old literal flavor and the single printf: 12 red. test-author is updating the model and pinning the rule.
> - docs-writer documented the rule in `release-pipeline.md`.
>
> **⚠️ Fuori pista** (docs-writer): promoting a prerelease to a release sends no `published` event, so the pipeline does not run. With a plain-tag prerelease, admins would be prompted while `latest` has not moved. Proposed to the coordinator: require a semver suffix on prereleases and fail fast without one.

### 10. ✅ Gallery rounds 2–3 (test-author) + dashboard verification + checkpoint gates — 2026-10-07
> **Note implementazione**:
> - **Round 2**, the dashboard scenarios:
>   - `setupDashboardMockReport` serves the date-shifted fixture to EVERY `POST /portfolio/report`, matched by URL only. The live merge is gone, and a missing or invalid fixture now throws.
>   - The data-quality scenario uses the same helper and replaces only `summary.data_quality.issues`. It keeps the fixture's computed `data_quality_status`, which the Zod schema requires.
>   - `expectDashboardReportLoaded` (`dashboard-page[data-busy=false]`, `growth-chart`, `%` enabled, KPI values) runs before every dashboard shot.
>   - Mode switches wait on `data-chart-renders`.
>   - Local `selectOneYearPreset`.
>   - Kept: the KPI count-up wait (`TweenedValue` has no settled signal) and the transactions-tab 500 ms (`txLoading` is not published). Both are product interface decisions, reported.
> - **Round 3**: B waits on the `data-i18n-ready` attribute. `ModalBase.lockBodyScroll()` fixes `body`, `<html>` collapses to zero height, and Playwright reports it hidden.
> - **Lane 6158, 1 worker, load 26–109**: every scenario below is green on desktop and mobile.
>
>   | Scenario | Shots | Time per run |
>   |---|---|---|
>   | `main dashboard` | 48 | 53/51 s |
>   | `allocation charts` | 96 | 50/42 s |
>   | `positions tab` | 64 | 53/59 s |
>   | `transactions tab` | 16 | 38/44 s |
>   | `data-quality banner` | 16 | 22/41 s |
>   | `mobile menu open` (mobile only) | 8 | 24 s |
>   | `update available modal` | 16 | 22/21 s |
>
>   Images checked by eye: `main-pct` shows the fixture's MWRR/TWRR/ROI over 1Y; the banner shows the two injected issues; the positions period table shows real rows.
> - **Gates**: `check-orphans` clean (329 vitest + 99 e2e + 237 backend files reachable); `--workers 4 utils all` green, 1 061 passed; `front-utility core-unit` 116 files / 3 405 tests; `utils release-image-contract` 87/87; Prettier clean; `git diff --check` clean; ports free.
> - **Docs**: `mkdocs build` strict, 0 warnings; `check-links` shows 89 valid plus the pre-existing `#rolling-return`, which the alignment closes.
> **⚠️ Fuori pista**:
> - `:3325` event popover stays red until the product fix (reported).
> - The data-quality shot keeps the 3M preset (as before R12), cosmetic.
> - The positions tables resolve brokers by id from the gallery DB, so the snapshot's broker names show only in tooltips. That is fine for privacy.

## Batch 2 (after commit `742e381ec`, train 9)

### 11. ✅ Prerelease tag guard — 2026-10-07
> **Note implementazione**: developer: «sì al suffisso rc per le pre release, però non succede che faccio una pre release e poi promuovo, al più ne creo un'altra da 0 su un tag nuovo».
> - New first step of the job, «Prerelease tag must be vX.Y.Z-rc.N». It runs only for a release marked as prerelease and reads the tag through `env`. It fails with an `::error` annotation unless `[[ "$TAG_NAME" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$ ]]`.
> - The promotion event is not handled: the stable release is always published on a new `vX.Y.Z` tag.
> - Simulation (bash, 14 tags): `v1.2.0-rc.1`, `1.2.0-rc.12` and `v10.20.30-rc.0` pass. Plain, `beta`, bare `rc`, `rc.1.2`, upper-case `V`, leading space, a quote injection, `$(id)`, the empty tag and both embedded-newline forms fail.
> - `utils release-image-contract` is still 87/87. Contract pins: test-author. `release-pipeline.md`: docs-writer.
> **⚠️ Fuori pista**: the first draft matched with `grep -Eq`, which matches line by line, so `v1.2.0-rc.1\nv9` passed. Replaced with bash's whole-string `[[ =~ ]]`. Evidence: `release-pipeline/runs/prerelease_guard_sim.txt`.
> **Gates**: `utils release-image-contract` **115/115** (+28 in `TestPrereleaseTagGuard`). They pin:
> - the `if:`, which is true only for prereleases;
> - the tag passed through `env`;
> - the step comes first;
> - the 14 tag verdicts, run in bash;
> - a plain-tag prerelease fails at this guard before any other step;
> - 7 negative controls: removed, every-release `if`, dropped `if`, any suffix, `grep` restored, tag interpolated into the script, moved after checkout.
>
> ruff and black clean. `release-pipeline.md` (docs-writer): new subsection «Prereleases and Publishing» with the guard, why the rc suffix matters, why there is no promotion, and «How to publish»; the diagram check; the §3 row and the `latest` bullet. `mkdocs build` strict: 0 warnings. `check-links`: 89 valid plus the pre-existing `#rolling-return`. `git diff --check` clean.
> **⚠️ Fuori pista**:
> - `Archive Generated Screenshots` (`!cancelled()`) still runs after the guard fails, and uploads nothing (`if-no-files-found: ignore`).
> - Open question for the coordinator: a release tagged `-rc.N` but **not** marked as a prerelease passes the guard and would deploy the docs with a `:latest` line in its notes. A symmetric check would close it (stable ⇒ `^v?X.Y.Z$`).

### 12. ✅ Symmetric release tag check — 2026-10-07
> **Note implementazione**: developer: «Sì, controllo simmetrico». The first step, renamed «Release tag must match the release kind», now runs for every release (`if: github.event_name == 'release'`) and reads `TAG_NAME` and `PRERELEASE` through `env`.
> - Prerelease: the tag must be `vX.Y.Z-rc.N`, otherwise `::error title=Prerelease tag`.
> - Stable: the tag must be a plain `vX.Y.Z`, otherwise `::error title=Release tag`.
> - This closes the case of an `-rc.N` tag published as stable, which would deploy the docs and announce `:latest` while `latest` and the update prompt ignore it.
> - Bash simulation, 28 cases (14 per branch, including an injection attempt, `$(id)`, embedded newlines and the empty tag): all as expected, each failure with its own title. Evidence: `release-pipeline/runs/release_tag_guard_sim.txt`.
> - Contract tests (test-author, including the developer's 2 negatives) and `release-pipeline.md` (docs-writer) are in progress.
>
> **Coordinator constraints, inventory order approved:**
> - group 2 (P&L and privacy) waits for I: the developer decided gold for the dividend and a label on every X-axis bucket for Candles and Income;
> - `detail-chart-rolling-return` waits for I's fix (train 9);
> - sequence: train 9 (Q + I) → commit of batch 2 → merge of `dev_release2` into M → replace Q's placeholders.
> **Gates** (lane 6158, load 50):
> - `utils release-image-contract` **133/133** (was 115). test-author added:
>   - 28 bash verdicts, with titles;
>   - the run «stable release on `v1.2.0-rc.1`», which fails first at the guard;
>   - the developer's 2 negatives, `stable-branch-dropped` and `stable-regex-loosened`, plus `prerelease-in-script` and `stable-error-titled-as-prerelease`;
>   - `if-every-release` → `if-prerelease-only`.
> - Ruff and black: clean.
> - `release-pipeline.md` (docs-writer): «🔖 Release Tags and Publishing» (anchor `#prereleases` kept) with a two-branch table, the refreshed YAML, both «why» bullets, «How to publish», the diagram box «Tag matches its kind? (rc / plain)», the gate and contract sentences, and the closed gap.
> - `mkdocs build` strict: 0 warnings. `check-links`: 89 valid plus the pre-existing `#rolling-return`. `git diff --check`: clean.

## Batch 3 — Q's screenshot inventory (base `9d79c2dbe`, train 10, Q's pages included)

### 13. ✅ Inventory: start, the event popover after I's fix, and group 1 — 2026-10-07 (committed 2026-10-08: `fb40d275b`, `1ac5d0a0a`)
> **Note implementazione**:
> - Clean base `9d79c2dbe`. Q's placeholders: 125 occurrences in EN pages, 40 names.
>   - 8 are third-party broker-portal screenshots (Coinbase, Degiro, IBKR, …), which are out of scope because the gallery cannot produce them.
>   - One more is a `gallery-index` editorial note (add Tools / Risk Analysis / Onboarding bullets once those shots exist).
>   - Reference list: session file `placeholders_9d79c2dbe.txt`.
> - **`:3383` Asset detail event popover**, re-run after I's fix (train 9): ✅ desktop 43 s, mobile 45 s, 16 shots (es/dark checked: dividend tooltip on the marker). All 7 scenarios red on the 10-06 nightly are now green on the lane.
> - Order approved by the coordinator: groups 1 (single screens, plus `assets/detail-chart-rolling-return`, unblocked), 3 (Danske), 4 (risk lab, plus `whatif-simulation`, unblocked with N), 5 (onboarding), 6 (PAC), 7 (provider compare).
>   - Group 2 (P&L, privacy) waits for I's chart batch.
>   - `dashboard/data-quality-sync-rates` is pending a coordinator confirmation that N's part is complete.
> - One test-author at a time on `gallery.spec.ts` (shared file within M): group 1 is in progress.
>
> **Group 1** (test-author, `gallery.spec.ts` only):
> - 6 of 7 scenarios written, plus the shared helper `waitForMotionSettled`:
>   - `settings/about-tool-diagnostics`;
>   - `tools/hub` (new `Tools` describe);
>   - `support/donation-popup` (new `Support` describe; the login response is intercepted to set `show_donation_popup` and the language/theme for each combination, no DB writes);
>   - `support/social-share-modal` (Reddit);
>   - `assets/detail-chart-rolling-return`;
>   - `assets/type-picker-open`.
> - Lane run (6158, 1 worker, desktop + mobile): **12/12 passed**, 96 PNGs, 3.4 min. Evidence: `release-pipeline/runs/G1_run1.log`.
> - Visual check of a sample (4 languages, both themes, desktop + mobile): `hub`, type picker (on mobile it opens upward, the picker's own behaviour), rolling return, donation popup and diagnostics are correct.
> - Rolling return: page range **1W** with window **1Y** (Q's placeholder asks for the 1Y window). The seeded prices start 2025-09-23, so a 1Y page would show a mostly partial 1Y window. A wider axis needs ≥ 2 years of mock prices (`populate_mock_data.py`, not M's surface).
> - `settings/onboarding-replay` is **blocked**: the category buttons in `SettingsLayout.svelte` have neither a testid nor a selected state. Proposal: `settings-category-{id}` + `aria-pressed`, and `settings-mobile-category-trigger` / `settings-mobile-category-{id}`. Owner to be decided by the coordinator.
>
> **⚠️ Fuori pista — product bug found by the visual check (not fixed by M):**
> - `support/social-share-modal` (desktop and mobile) shows a 32 px strip at the bottom of the viewport that the backdrop does not dim. The donation popup does not.
> - DOM probe on the lane (`release-pipeline/scripts/probe_share_backdrop{,_v2,_v3}.cjs`, outputs `runs/probe_share_backdrop*.json`): the ModalBase `.modal-backdrop` (`position:fixed; inset:0`) computes **`margin-bottom: 32px`**, so its box is 688 px instead of 720. This holds at scroll 0, 100 and at the bottom; no ancestor creates a containing block.
> - Cause: `AboutTab.svelte:586` mounts `<SocialShareModal>` as a non-last child of `div.space-y-8` (`:247`). Tailwind `space-y-8` puts `margin-block-end: 2rem` on every child but the last, and that includes the in-place backdrop.
> - Effect for users: the strip is not dimmed and stays **clickable** under an `aria-modal` dialog. `elementFromPoint(100,700)` is `sidebar-version`.
> - Generic fix proposed: `margin: 0` on `.modal-backdrop`. Unlayered Svelte CSS beats Tailwind's `@layer utilities` `:where()` rules, and the fix also covers `space-x-*`.
> - Reported to the coordinator. After the fix, only this scenario is re-shot.
>
> **Group 1: placeholders in the EN docs** (`docs-writer`, EN only, no stamp: the pages were already stale because of Q's placeholders, and the debt stays real until the alignment):
> - 19 occurrences replaced:
>   - `gallery/{desktop,mobile}.en.md`: 3 Settings entries, Rolling Return, Asset Type Picker, and the new section `---` + `## 🧰 Tools` + «Tools Hub». The 9 `tools/pac-*` placeholders remain inside the section; mobile entries use `screenshot-container mobile`.
>   - `user/settings/about` (3), `user/tools/index`, `user/assets/create-edit`, `user/assets/detail/chart`.
>   - `index.en.md` DD6 «Planning Tools» back to `deep-dive reverse` with an image column, modelled on DD2.
>   - `gallery/index` gets the Tools bullet; the comment now names only Risk Analysis and Onboarding.
> - Text taken byte for byte from the placeholders. Each gallery page has 10 `##` and 10 `---`; no `###` has one.
>
> **Gates** (load ~16–20):
> - `mkdocs build` strict: exit 0, 0 WARNING/ERROR (`runs/G1_mkdocs_build.log`).
> - `check-links`: 89 valid, 3 known exceptions, plus the pre-existing `#rolling-return`, unchanged from the baseline (`runs/G1_check_links.log`).
> - Prettier on `gallery.spec.ts`: ok. `git diff --check`: clean.
> - Built site served statically on 6168 (`scripts/site_visual_check_g1.cjs`): DD6 renders `reverse` with `tools/hub`; the gallery and `user/tools` images resolve (`runs/G1_site_*.png`).
> - Ports 6158 and 6168 free after the run.

### 14. ✅ Coordinator decisions on group 1, the `onboarding-replay` hook, and feasibility of groups 3–7 — 2026-10-08

> **Note implementazione**:
>
> **Decisions** (coordinator, 2026-10-08):
> 1. ModalBase fix (`margin: 0` on `.modal-backdrop`) goes to K, in its next batch, with a red test. After integration M re-shoots only `support/social-share-modal`.
> 2. `onboarding-replay` hook granted to M, only in `SettingsLayout.svelte`, no visual change. The scenario goes through test-author.
> 3. Rolling return with a 1W page and a 1Y window: accepted.
> 4. `dashboard/data-quality-sync-rates` unblocked: the **Sync rates** button is N's, in `dev_release2` since train 8. It goes to group 4, with the fixture and injected issues.
> 5. The 8 broker-portal screenshots stay placeholders until after 1.2 (developer).
> 6. New name approved: `brokers/import-report-set-file-menu` (the ⋮ menu of a set's file), next to `brokers/import-report-set-read-as` (the Read as menu). The two popovers cannot be open together. M updates `danske-bank:69` and `how-to:94` (EN, docs-writer).
> 7. Approved for groups 3–7:
>    - disposable users, deleted at the end with their brokers and files;
>    - injected responses only where real data is not enough;
>    - no change to `populate_mock_data.py`;
>    - one checkpoint per group: G3, G4, G5 with the hook, G6+G7.
> 8. G6: ask before touching PAC files. None needed: verified below.
>
> **Hook** (`frontend/src/lib/components/settings/SettingsLayout.svelte`, uncommitted, goes with the G5 checkpoint):
> - desktop: `settings-category-all` / `settings-category-{id}`;
> - phone: `settings-mobile-category-trigger`, `settings-mobile-category-all` / `settings-mobile-category-{id}`;
> - `aria-pressed` written as the strings `'true'|'false'`, the same style as `data-busy` in that file;
> - one docblock line; no class or style changed;
> - convention copied from `GlobalSettingsTab.svelte:435-505`.
>
> Evidence: Prettier ok; `frontend/node_modules/.bin/vitest run src/lib/components/settings/SettingsLayout.test.ts` 34/34 (`release-pipeline/runs/G5_settingsLayout_vitest.log`).
>
> Follow-up for test-author in G5: the docblock of `SettingsLayout.test.ts` says «publishes no `data-testid`, anywhere». That is now stale: update it and add direct assertions on the new attributes.
>
> **Feasibility of groups 3–7** (3 read-only explorers plus M's own checks; summary in the session file `r12_feasibility_g3-7.md`): **no new product hook** beyond `SettingsLayout`.
> - Visibility: broker access is strictly per user (`broker_service.get_accessible_broker_ids` → `BrokerUserAccess`, no admin bypass). So G3 runs as a disposable user, and its Danske broker and uploads stay invisible to admin shots running in parallel. Example: `import wizard step 2` photographs every file the admin uploaded.
> - Registration: `enable_registration` = true in the test DB.
> - Charts publish `data-chart-ready` / `data-chart-renders` (`chartReady.ts`), so the simulation cone can be awaited with no new testid.
> - Danske missing-file card: it already shows the missing export, its period and «Upload the missing file» (`ReportSetCard.svelte:420-431`). One shot is enough.
> - PAC: the needed hooks exist:
>   - `pac-planner-scenario-currency`, `pac-planner-contribution-currency`, the amount through `ExactDecimalInput`;
>   - copy dialog `BrokerScopeCopyDialog` `{testid}-body/-broker/-check/-apply`;
>   - `CopyFlowView` only wraps `CopyNotice` and `ConflictDialog`, which have their own testids.
> - Lane risk data (read-only on the test DB, `runs/G4_lane_price_spans.txt`):
>   - 9 assets priced 2025-09-23 → 2026-10-07, including S&P 500 and MSCI World;
>   - 7 assets with a single quote: NVIDIA, 3 ETFs, 2 BTPs, Gold. These are the natural «cannot be analysed» cases;
>   - Test KRW Stock has no prices;
>   - no asset starts late or ends stale, so `lab-notice` and `lab-replay` will very likely need injected responses.
>
> **⚠️ Fuori pista**: the group 1 batch was committed by path while the `SettingsLayout.svelte` hook sat in the worktree. Until the SHAs arrived M did not touch the 10 batch paths, and warned the coordinator to stage them explicitly. The hook stayed out of the commits as planned.

### 15. ✅ Group 3: Danske Bank report sets — 2026-10-08 (committed: `f1bda660f`, `88b30ac1a`)

> **Note implementazione**:
> - Base `1ac5d0a0a`.
> - test-author is writing 8 shots:
>   - `brokers/import-report-set-card`, `-missing`, `-read-as`, `-file-menu`, `-pairing`;
>   - `brokers/import-wizard-gapfix-step`;
>   - `files/brim-report-sets`;
>   - `transactions/bulk-todo-banner`.
> - Every test has its own disposable user and broker, cleaned up in `finally`. No import is committed.
>
> **Tests** (test-author, `frontend/e2e/gallery.spec.ts` + new `frontend/e2e/fixtures/galleryReportSets.ts`): 6 tests in `test.describe('Import report sets (Danske Bank)')`, after `Brokers`.
> - **Setup per test:**
>   - a disposable account `demo_<token>`, taken through the Welcome with every guide skipped;
>   - one broker `Label · TOKEN`;
>   - uploads over the API, one batch per set;
>   - language and theme switched before the wizard is reopened.
> - **Cleanup** in `afterEach`: files (the combined one included), then the broker, then the account. **No import is committed**: parse, gap fix and validate write nothing, and the bulk editor is closed by discarding.
> - **8 names × 16 shots:**
>   - `brokers/import-report-set-card`, `-read-as`;
>   - `-file-menu`: an extended cash statement that Generic CSV can read too; with the bank's own statement «Read alone with…» never appears;
>   - `-missing`;
>   - `-pairing`: on the gap set, because the table of reasons only appears when rows are excluded;
>   - `brokers/import-wizard-gapfix-step`: on the gap set, cash rows only, so the end-of-period check reads «Does not match»;
>   - `files/brim-report-sets`;
>   - `transactions/bulk-todo-banner`: a generic CSV, with 2 `field_todos` injected into the parse response.
> - **Isolation:**
>   - a universal filter `hideGalleryTempData`, installed by a `beforeEach` of `Gallery Screenshots` (`gallery.spec.ts:238`), plus `unrouteAll` in `afterEach`;
>   - it removes `Label · TOKEN` brokers (U+00B7) and their files from the lists of anyone who cannot access them;
>   - with nothing marked, the response passes through unchanged.
>
> **Lane runs** (6158, 1 worker, `--no-populate`):
> - Run 1, load 34 → 20: 10/12 in 5.8 min. Desktop 6/6; mobile had 2 red, see «Fuori pista».
> - Run 2, load 24 → 11: **14/14** in 6.1 min. It covered the 3 corrected tests and 4 existing admin scenarios that go through the filter: Files broker reports tab, BRIM file preview, broker list, import wizard step 2.
> - Lane DB afterwards: 0 `demo_*` users, 0 marked brokers.
> - Logs: `release-pipeline/runs/G3_run{1,2}.log`.
> - Visual check of a sample (4 languages, both themes, desktop and mobile): all correct.
>
> **Docs** (docs-writer, EN only, no stamp):
> - 23 placeholders replaced, plus a new «🗃️ File Menu» entry in both gallery pages. The «📖 Read As» description is trimmed to the Read as menu alone.
> - User pages:
>   - `transactions/index`;
>   - `danske-bank`: card, pairing, missing, Read as only, gap fix;
>   - `how-to`: Read as plus file menu, and gap fix;
>   - `files/index`.
>
> **Gates:**
> - `mkdocs build` strict: 0 WARNING/ERROR.
> - `check-links`: identical to the baseline (89 valid, 3 known exceptions, plus the pre-existing `#rolling-return`).
> - Prettier: ok on the spec and the fixture.
> - `tsc -p tsconfig.e2e.json`: only the 2 pre-existing errors, both outside these files (`onboarding-tour.spec.ts:863`, `src/lib/types/files.ts:9`).
> - `git diff --check`: clean. Ports 6158 and 6168 free.
>
> **⚠️ Fuori pista**:
> - **Isolation premise was wrong.**
>   - What I assumed: «no admin bypass».
>   - What test-author found: the superuser lists **every** BRIM file (`brokers.py:673-675`), and every user sees other users' broker names in «Other existing brokers» (`brokerStore.ts:107`).
>   - Consequence: in the seed the admin owns all 8 brokers, so during a parallel full gallery the temporary data would have appeared in the admin shots.
>   - Fix: the universal filter above. M's decision, inside `gallery.spec.ts` only, touching neither the product nor the runner.
> - **Product bugs**, reported to the coordinator and not fixed:
>   1. `ReportSetCard` header on mobile: the toggle (`flex-1 min-w-0`) is squeezed to zero width. With «A file is missing» the card cannot be opened by tapping, and even with «Complete» the set label disappears.
>   2. The set timeline on mobile: the start and end dates overlap.
>   3. Escape on the Read as list or the ⋮ menu bubbles up to the wizard's discard prompt.
>   - On mobile the gallery opens the card from the keyboard when the toggle has no box, as the card arrives open after a real upload.
> - **Bulk banner in English:** it shows the todo's `message`, the English fallback (`TransactionBulkModal.svelte:3171`), in every language. The FR/IT/ES shots show English entries, faithful to the product: a small i18n gap.
> - **Q's text corrected:** `danske-bank.en.md:152` said only «Deposit», but the code proposes a Deposit or a Withdrawal (`brim_gap_fix.py:145`), and our gap-fix image shows a Withdrawal. Changed to «a **Deposit** or a **Withdrawal**». EN only; the page has no translations.
> - **Toasts:** they close on a JS timer that `freezeAnimations` does not pause, so a shot taken within 8 s of an action that raises one can catch it. `expectNoToast` is exported but only used in the bulk test. The risk already existed in other scenarios and was not widened.
> - **Timeouts:** test-author's 240–600 s budgets stay. Runs measured 15–28 s per test, but the 20 s `actionTimeout` already fails a stuck step quickly, and CI is slower.

### 16. ✅ Group 4: risk lab, What if simulation, missing exchange rates — 2026-10-08

> **Note implementazione**:
> - Base `88b30ac1a`.
> - test-author is writing 9 shots:
>   - `risk/lab-correlation`, `-asset-picker`, `-hurt-table`, `-risk-return`, `-benchmark-picker`, `-notice`, `-replay`;
>   - `risk/whatif-simulation`;
>   - `dashboard/data-quality-sync-rates`.
> - All of it runs as the admin, read-only: the selection and the benchmark live in localStorage. No live provider is ever called.
> - Coordinator note for G6: the PAC images in `user/tools/pac-allocator/index.en.md` go in only after Q's checkpoint (which restructures that page) is in M's base. The scenarios can be written before.
>
> **Real-data probes on the lane** (read-only; only localStorage is written). Scripts: `release-pipeline/scripts/probe_risk_lab_real_data{,_v2,_v3}.cjs`; output: `runs/G4_probe*`.
> - The Assets page opens on 3M, so the shots select 1Y with the top preset.
> - At 1Y, the 7 priced assets (AAPL, MSFT, TSLA, the two loans, BTC, ETH) give:
>   - «The most alike»: Roma↔Milano 0.94 and ETH↔BTC 0.93;
>   - «The ones that offset»: empty (no ρ ≤ −0.30 in the mock data).
> - Ineligible assets (the 7 with a single quote, and KRW) are **parked**: struck-through chips and `risk-parked-note`. They raise no `risk-partial-notice`. So `lab-notice` very likely needs an injection.
> - A 2Y replay gives the left-out box `starts_after_window_start` and the «Replay from 2025-09-24 to …» button with real data.
>
> **Tests** (test-author: `frontend/e2e/gallery.spec.ts` and the new `frontend/e2e/fixtures/galleryRiskLab.ts`):
> - A `Risk Analysis` describe after `Assets` with 5 tests, plus 1 test in `Dashboard` next to the existing data-quality test, which is unchanged.
> - **Setup:**
>   - the admin, read-only;
>   - selection in localStorage: Apple, RE Loan Milano, RE Loan Roma, Bitcoin, Ethereum;
>   - benchmark S&P 500, also in localStorage;
>   - 1Y period from the top preset;
>   - asset ids resolved through the API.
> - **Guards:** each test aborts `POST /assets/prices/current` (the page's 30 s poll, which would reach providers and store a price), `/assets/prices/sync`, `/fx/currencies/sync` and `GET /fx/providers`, and asserts at the end that no attempt was made.
> - **Real data:** correlation, hurt table, risk-return, both pickers, and the simulation (paths 2048, seed 123456).
> - **Injected:**
>   - `lab-notice`: RE Loan Roma stale by 12 days in the `/risk/query` answers, plus a `stale_at_end` warning in the eligibility answer (amber chip, still analysed), plus Correlation `unavailable` / `insufficient_history` for the section banner. The real engine has no trigger: the eligibility check filters stale assets out before the query.
>   - `lab-replay`: Roma left out as «quoted after the period start», with a suggested period. All the seeded prices start on the same day.
>   - `data-quality-sync-rates`: the dashboard fixture plus a `MISSING_FX_RATES` issue, shaped as the backend builds it (pairs sorted EUR-GBP, EUR-USD).
>
> **Lane runs** (6158, 1 worker):
> - Run 1 (load ~10): 10/12. The correlation test was red on both viewports because it required BTC↔ETH, a pair the selection's joint calendar no longer ranks.
> - Run 2 (load 7→12): 6/6 for the 3 corrected tests.
> - Run 3, final with the final code (load 10→15): **12/12 in 7.2 min**.
> - Logs: `release-pipeline/runs/G4_run{1,2,3}.log`.
> - Visual check of a sample (4 languages, both themes, desktop and mobile): correct.
>
> **Docs** (docs-writer, gallery pages only, by the coordinator's rule during Q's wave 1):
> - `gallery/{desktop,mobile}.en.md`: «💱 Missing Exchange Rates» in Dashboard, plus the new section `---` / `## 📉 Risk Analysis` with 8 entries and the following `---`.
> - `gallery/index.en.md`: a «Risk Analysis» bullet; the comment now names only Onboarding.
> - Placeholders left in place on purpose, for the batch after Q's wave 1: `user/assets/correlation.en.md` (7) and `financial-theory/.../risk-metrics/{benchmark-selection,historical-replay,simulation-modes}.en.md` (1 each).
>
> **Gates:**
> - `mkdocs build` strict: 0 WARNING/ERROR.
> - `check-links`: identical to the baseline.
> - Prettier: ok.
> - `tsc` e2e: only the 2 known errors.
> - `git diff --check`: clean. Ports 6158 and 6168 free.
>
> **⚠️ Fuori pista**:
> - **Tooling bug** in `dev.py mkdocs gallery --no-populate`. The help says «Skip DB population». But `LF_SETUP_DONE` is set only when dev.py has populated the DB itself (`dev.py:990-999`), so Playwright's `global-setup.ts:48` runs `populate_mock_data --force --with-reports` at **every** run. That is a different dataset from dev.py's own `--force --clean --with-static --with-reports`.
>   - Effects: `--no-populate` reruns are neither faster nor on the same DB.
>   - Proposed fix: one line, set `LF_SETUP_DONE=1` with `--no-populate` too. `dev.py` is shared, so it goes to the coordinator.
>   - This also explains why the lane DB changed between runs (prices regenerated up to today).
> - **Correction to my earlier facts:** NVIDIA, the ETFs, the BTPs and Gold now have **no** price rows, so the reason «No price has ever been recorded» is correct. The single row each had on 2026-10-07 is not reproduced by today's populate, and its origin is unknown.
> - **Prices are deterministic but correlations are not portable:** the mock prices are seeded per asset and date (`_stable_seed`), but the correlation of a pair depends on the selection's joint calendar. Gallery assertions use only the Roma↔Milano pair, near-identical by construction.
> - **Italian hurt table:** the last column («Risalita al massimo») is cut on the right by the longer labels. Product layout, minor.
> - **Simulation framing:** the shot starts at the top of the step. The cone is partly in frame and «What this simulation assumed» is out of frame. To revisit with the new `dashboard/risk-whatif` shots after Q's wave 1.
> - **Q's G3 finding:** `brokers/import-report-set-file-menu` used an extended test cash statement, so it showed «Read alone with Generic CSV». Danske is the only plugin with report sets (`report_roles`, `broker_danske_bank.py:1644`). Decision sent to Q: reshoot with the real Danske cash export, whose menu has Preview / Remove from the set / Delete, in the batch after Q's wave 1. Q has added the placeholder in `danske-bank` after `-read-as`.
