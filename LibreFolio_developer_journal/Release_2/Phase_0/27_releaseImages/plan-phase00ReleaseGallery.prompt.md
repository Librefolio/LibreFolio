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

### 16. ✅ Group 4: risk lab, What if simulation, missing exchange rates — 2026-10-08 (committed: `a1f34905a`, `44ac071d2`)

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

## Batch 4 — base `57f3d96a8` (merge of `dev_release2`, train 14, into M)

### 17. ✅ Group 5 and two tooling fixes: combined revision, `--no-populate`, gallery fallback under `serve` — 2026-10-08 (committed `6a9000898…3a8e9a05d`, train 18 `70d02cd8e`)

> **Note implementazione**:
>
> **Combined revision validated** (light runs while the coverage run was on 6150):
> - `mkdocs build` strict: 0 WARNING/ERROR. `check-links`: identical to the baseline.
> - vitest `SettingsLayout` plus the fixture guard: 39/39. `tsc` e2e: only the 2 known errors. Prettier ok.
> - Gallery smoke 4/4: `tools hub` and `social share modal`, desktop and mobile.
> - `support/social-share-modal` was re-shot with K's fix (`53a6b2213`). The pixels confirm the bottom strip is now dimmed.
> - Train 14 also brings:
>   - L's fix to the card header and timeline on phones (`038109e91`), so the G3 mobile shots have to be re-shot;
>   - I's batch (`bc08101d6`, gold dividends and period labels), which unblocks group 2.
>
> **`dev.py mkdocs gallery --no-populate`** (granted by the coordinator; a separate `fix(dev)` commit):
> - New helper `_reuse_gallery_test_db()`. It resolves `get_test_data_dir()/sqlite/app.db`:
>   - DB missing: a clear error and exit 1, before Playwright starts;
>   - DB present: `_ensure_test_users()`, then «reusing <path>».
> - `LF_SETUP_DONE=1` is now set in both branches, as `manifest-integrazione-E.md:301` requires (only once DB and users are really prepared).
> - Ruff on `dev.py`: 43 errors, the same as `HEAD`. The local imports use the file's `# noqa: PLC0415 — CLI-only import` convention.
> - **Proof on the lane** (`release-pipeline/runs/DEV_proof_{1_full,2_nopopulate,3_nodb}.log`, `DEV_proof_markers.txt`):
>   1. A full run: populate and users, then global-setup «skipping to global settings».
>   2. A `--no-populate` run: «reusing /private/tmp/librefolio-r2-m/sqlite/app.db», global-setup stands down, and the admin's `created_at` is unchanged (12:44:55). No repopulation.
>   3. `--no-populate` on `/tmp/librefolio-r2-m-nodb`: exit 1 with the message; no Playwright, no directory created.
> - **Regression tests** (test-author, `backend/test_scripts/test_utilities/test_runtime_isolation.py`): 10 new tests, all pure (`tmp_path`, `subprocess` blocked).
>   - `TestGalleryReusesTheLaneDb` covers:
>     - a missing DB: refused, the path is named, no users are created, nothing is written;
>     - an existing DB: reused untouched, users ensured once, «reusing <lane>» printed;
>     - users that cannot be ensured: refused;
>     - a lane the real resolver rejects (inside `LIBREFOLIO_DATA_DIR`, or a folder marked as production): refused, with no exception.
>   - `TestGalleryHandsTheSetupToPlaywright` goes through the real `dev.main()` parser:
>     - with and without `--no-populate`, Playwright starts last, with `LF_SETUP_DONE` as `global-setup.ts` expects it and the same lane;
>     - a refused reuse exits with 1 before Playwright and never falls back to populating.
>   - Result: `utils runtime-isolation` **153/153** (143 + 10). Ruff and black clean on the test file.
> - The `--no-populate` help now reads «Reuse the existing test database as it is (faster re-runs; needs one earlier full run)». Rerun 153/153.
> - Notes from test-author, outside the scope:
>   - `mkdocs gallery` does not call `configure_test_runtime()`. If the lane is defined only in `.env` and `dev.py` runs outside `pipenv run`, the command and Playwright could resolve different lanes. This already applies to the populate branch.
>   - The reuse check only tests that the file exists: «as it is».
>
> **Gallery fallback under `mkdocs serve`** (Q's finding, assigned to M):
> - The cause: `serve` rewrites `config.site_url`, and `overrides/main.html` derived `LF_GALLERY_FALLBACK_BASE` from it, so the loader asked the local server again.
> - The fix, without touching `mkdocs.yml`:
>   - `hooks/jsonld.py` publishes `_SITE_URL` to the templates (`on_env` → `lf_canonical_site_url`);
>   - `main.html` reads it, falling back to `config.site_url`;
>   - a new `on_config` warns when `site_url` and `_SITE_URL` drift apart (so a strict build fails), and skips the check under `serve`;
>   - the comment in `gallery-img-loader.js` is updated.
> - Hook check (`runs/G5_jsonld_hook_check.txt`): canonical, no trailing slash and `serve` give 0 warnings; drift gives 1; `on_env` publishes the canonical address.
> - Strict build: 0 WARNING/ERROR, and the EN and IT pages carry `"https://librefolio.github.io/LibreFolio/"`.
> - **`serve` on 6168** (`runs/G5_serve_6168.log`, `scripts/serve_fallback_check.cjs`, `runs/G5_serve_fallback_check.json`):
>   - the injected base is the canonical one, with no drift warning;
>   - in the browser, `fx/list.png` (absent locally) is requested locally first, then from GitHub Pages, and loads at 1280×720;
>   - port freed afterwards.
> - Ruff on `jsonld.py`: 2 errors, the same as `HEAD` (including the pre-existing `I001`).
>
> **For Q:**
> - 102 PNGs (desktop/en, light and dark) copied to `/tmp/librefolio-q-gallery-drop/` for the developer's static preview. The repo is untouched.
> - `assets/distribution-editor-{sector,geographic}` regenerated with the existing scenario: they show Q's 1.2 **Import CSV**.
>
> **⚠️ Fuori pista — live providers in the gallery (pre-existing):**
> - During the `--no-populate` proof run, the Assets page's 30 s poll (`POST /assets/prices/current`) wrote 6 rows with today's live prices into the lane DB. Sources: `provider:justetf`, `provider:css_scraper` and `provider:scheduled_investment`, for the ETFs, the BTPs and Gold.
> - This explains the single quote those assets had on 2026-10-07. The gallery disables the scheduler, but this frontend poll bypasses that.
> - G4 aborts it; the older scenarios do not. To be decided by the coordinator: a gallery-wide abort (deterministic and offline, but the cards of unseeded assets would show no price), or seeding those prices in the populate.
>
> **Group 5, onboarding** (test-author: `gallery.spec.ts` and the new `fixtures/galleryOnboarding.ts`):
> - A new `Onboarding` describe after `Auth Pages`:
>   - `welcome setup` → `onboarding/welcome-setup`;
>   - `core tour step` → `onboarding/core-tour-step`, at step `intro.fx_nav`;
>   - `contextual guide on the FX page` → `onboarding/contextual-guide`, at step `fx.page.filters`, never `fx.page.sync`.
> - `onboarding replay` → `settings/onboarding-replay` goes at the end of `Settings`. It runs as the admin, read-only, and never presses Replay.
> - **Accounts:** one disposable `demo_<token>` account per test, not per combination, so the same name appears in every variant. Language and theme go through localStorage, plus a `PUT /settings/user` on the account itself for the Welcome form. The account is deleted in `afterEach`.
> - **`SettingsLayout.test.ts`:** 40 tests (34 existing + 6 for the hook's test ids and `aria-pressed`, desktop and phone). The docblock is updated.
> - **`unfoldCard` (G3):** the keyboard fallback for the zero-width toggle is gone, because L fixed the header (`038109e91`). A regression now fails loudly.
>
> **Offline gallery guard** (coordinator decision, option (a) plus a fixture; test-author):
> - `guardGalleryOffline` runs in the top-level `beforeEach`, and `expectGalleryOffline` in `afterEach`.
> - **Aborted, recorded, and the test fails:** `POST /assets/prices/sync`, `/assets/provider/refresh`, `/assets/provider/probe` and `/fx/currencies/sync`.
> - **Answered from fixtures** (`fixtures/galleryOfflineData.ts`):
>   - `POST /assets/prices/current`: the 6 prices observed live today (ETFs, BTPs, Gold), dated today, ids resolved by name;
>   - `GET /fx/providers`: BOE, ECB, FED and SNB, with metadata from the backend classes and currencies from the docs.
> - **Answered with «no results»:** `GET /assets/provider/search` and `/search/stream`.
> - **Aborted:** `api.github.com`, the admin's release check.
> - **Ownership:** group 4's `guardReadOnly` now only switches the poll to abort and reuses the global record.
> - **Fixed along the way:** «Add pair - chain» folded the group again and never selected a route. It now opens the group only if closed and checks the count goes up by one.
> - `expectOfflinePricesDrawn` waits for the fixture prices before the Assets shots.
>
> **Lane runs** (6158, 1 worker):
> - G5 run 1, fresh populate (load 27→17): 7/8. The mobile `onboarding replay` failed in ES: on phones the Core group was below the fold.
> - Fix: on phones the shot is framed from the Onboarding card header (`frameFromTop`).
> - Run 2: 2/2.
> - G3 reshoot with the global guard active: **12/12**. On phones the card header is on two rows and the timeline dates no longer overlap.
> - Lane DB afterwards: 0 `provider:*` rows, 0 disposable accounts, 0 marked brokers.
> - Logs: `runs/G5_run{1,2}.log`, `runs/G3_reshoot.log`.
>
> **Docs** (docs-writer, gallery pages only):
> - `gallery/{desktop,mobile}`: a new `## 🧭 Onboarding` section with 3 entries plus `---`, and «🔁 Guide Replay» in Settings.
> - `gallery/index`: an Onboarding bullet; the last editorial comment is removed.
> - Held: `user/getting-started` and `user/settings/preferences`. They are part of Q's wave 2.
>
> **Gates:**
> - `mkdocs build` strict: 0 WARNING/ERROR. The injected fallback is the canonical one.
> - `check-links`: identical to the baseline.
> - vitest: 45/45 (SettingsLayout 40 plus the fixture guard 5).
> - `tsc` e2e: the 2 known errors.
> - Prettier ok.
> - Ruff and black on `test_runtime_isolation.py`: ok.
> - `git diff --check`: clean.
>
> **Next:** after the coverage run on 6150, the broad verification of the offline guard (Assets, FX, Risk Analysis, Onboarding and the Settings shots), with a fresh populate.
>
> **Broad verification of the offline guard** (6158, 1 worker, fresh populate, 17:00–17:51, load 9→17): **95/96** (`runs/G5_guard.log`). The `-f` covered Assets, FX, Risk Analysis, Onboarding, About tab, plugin and tool diagnostics, onboarding replay and data-quality banner.
> - Lane DB afterwards: 0 `provider:*` price rows. The price rows and the 4,095 `fx_rates` ECB rows all date from the 15:00:27 UTC populate, none written during the run. 0 disposable accounts, 0 marked brokers.
> - **The only red:** mobile «Add pair - chain».
>   - Playwright clicks the centre of the route row. On a phone that centre is a provider badge wrapped in `Tooltip` (`FxProviderSelect.svelte:737-747`).
>   - The tooltip's mouse `onclick` calls `stopPropagation()` (`Tooltip.svelte:149, 389-390`), so `addRoute` never runs. A real tap goes through `touchstart` and works.
>   - Fix: click the row's «+» (`position`) and `parkPointer` before the shot.
> - **SNB fixture fidelity:**
>   - It listed 8 currencies, taken from the docs page. The real coverage is the 25 verified live in the audit `phases/05_cleanAudit/mkdocsAudit/03_fx-market-data.md:157-160`.
>   - The published 1.1 shot shows a direct SNB NOK→CHF route.
>   - Now: the 25 audited currencies; the chain test opens the 2-step group by the chevron and frames from «Conversion routes», with the direct route in view.
> - `-f 'Add pair'` rerun: **4/4**. Visual check (desktop EN, mobile IT dark): the added chain route, the direct SNB route and the open group are all in frame.
>
> **⚠️ Fuori pista — a gallery regression introduced by G3 (integrated since train 13):**
> - In playwright-core 1.61 (`lib/coreBundle.js`, `_isFavicon = url.endsWith("/favicon.ico")`), as soon as ANY route is registered, Playwright aborts that request **before any handler runs**.
> - Since G3, the global `beforeEach` installs routes for every test. So every broker logo (`portal_url` origin + `/favicon.ico`, `brokerIconChain.svelte.ts:85`) and the FED/SNB icons show their fallback.
> - The published 1.1 `brokers/list` shows real logos; ours shows the briefcase.
> - Probes (`scripts/probe_fx_icons{,_v2,_v3}.cjs`): ECB's `.png` loads, the `.ico` icons do not. `route.fetch()` gets a 403. Serving the bytes from Node does not help, because the abort comes first.
> - **Test-only fix** (`scripts/probe_favicon_shim.cjs`): an `addInitScript` appends `?lf-gallery` to image URLs ending in `/favicon.ico`, through the `src` setter, `setAttribute` and `innerHTML`.
>   - With it 12/12 images load; without it 0/12.
>   - Each host serves identical bytes with the query: IBKR, DEGIRO, Directa, eToro, Coinbase, Schwab, FRED, SNB (Recrowd answers 429 either way).
>   - No product code touched.
> - Assigned to test-author (task E). Reported to the coordinator.
>
> **Favicon fix** (test-author, task E; `fixtures/galleryReportSets.ts` and `gallery.spec.ts`):
> - `keepFaviconImagesLoading(page)` is an `addInitScript` in the top-level `beforeEach`, before any navigation. It appends `lf-gallery` to image URLs ending in `/favicon.ico`:
>   - through the `src` property, `setAttribute('src')`, and `src` values written via `innerHTML`;
>   - the `#fragment` is kept, and an existing query gets `&`.
> - `expectFaviconImagesLoading(page)` runs in the top-level `afterEach`. It checks, with no network, that the shim was active on the last page.
> - Cause confirmed in playwright-core 1.61.0 `coreBundle.js:12805` (`_isFavicon`) and `:22393-22396` (abort when any route is registered).
> - **Lane check** (load 47→71 from the other lanes): **14/14** — broker list, broker detail, import wizard step 2, broker reports tab, both «Add pair» and transaction list, desktop and mobile.
>   - Visual: the Coinbase, DEGIRO, Directa and IBKR logos are back in `brokers/list` and in the wizard. In «Add pair» the FED and SNB icons are back.
>   - Schwab and Recrowd keep their fallback: Recrowd answers 429, and Schwab's icon has no logo in this shot either, as in 1.1.
> - Sanity on pages with heavy DOM (core tour, Asset list, risk lab): **6/6**.
>
> **Final evidence:**
> - Lane DB: 0 `provider:*` price rows; prices and `fx_rates` only from the 15:00 UTC populate; 0 disposable accounts, 0 marked brokers. Ports 6158 and 6168 free.
> - Prettier ok on the 7 frontend files. `tsc` e2e: only the 2 known errors. `git diff --check`: clean.
> - Build strict and check-links were verified at 16:42 (0 WARNING/ERROR, baseline links). The later changes touch only e2e files.

## Batch 5 — images in the user pages (base `70d02cd8e`, train 18, branch fast-forwarded; Q's waves 1 and 2 integrated)

### 18. ✅ User-page images, risk dashboard, group 2, PAC, provider compare, Danske reshoot, reduced motion, tall shots — 2026-10-08/09

> **Note implementazione**:
>
> **Coordinator decisions:**
> - Scope:
>   - risk pages: `user/assets/correlation` (7), the three `risk-metrics` theory pages, `user/dashboard/risk` (5);
>   - group 2 (P&L and privacy);
>   - PAC and provider-compare;
>   - the `file-menu` reshoot with the real cash export, plus L's sentence (#26) on `danske-bank`;
>   - retakes of Coinbase and `/transactions` with P's seed (ETH staking as ADJUSTMENT, Coinbase cash −5 USD).
> - Out: `dashboard/data-quality-sync-rates`. No user page has its placeholder since train 15; the gallery entry is enough.
> - **Taller viewport for `risk/whatif-simulation`, desktop only:** 1280 wide, same scale, height just enough for the whole Simulation box (~1000).
>   - Why: `user/dashboard/risk` asks for the whole box in one image, and at 720 px the ~930 px box does not fit.
>   - Mobile keeps the phone viewport and the top of the step, which is what the mobile gallery entry describes.
> - `user/getting-started` (3) and `user/settings/preferences` (2) are now M's. Wave 2 is integrated, and wave 3 does not touch them. Only the placeholders are replaced; Q's text stays.
> - The four `dashboard/risk-*` also go in the gallery's «📉 Risk Analysis» section, with the terms of `user/dashboard/risk`.
> - **Organisation:** one checkpoint at the end of the batch (integration after the coverage run, ~22:00), one test-author at a time on `gallery.spec.ts`, docs-writer in parallel on the pages. Until ~22:00, gallery with 1 worker on lane 6158.
>
> **Placeholders at the base:** 71 in total.
> - Gallery: 14 per page (growth-pnl 3, privacy-masked 1, create-provider-compare 1, `tools/pac-*` 9).
> - User and theory pages: correlation 7, theory 3, dashboard/risk 5, dashboard/charts 4, preferences 2, getting-started 3, create-edit 1, pac-allocator 9, danske-bank 1.
> - The 8 broker-portal placeholders stay until after 1.2.
>
> **In progress:**
> - test-author A: the tall simulation and the four `dashboard/risk-*`.
> - docs-writer 1: correlation, theory, the `risk.en.md` simulation, Danske (`file-menu` and L's sentence), then getting-started and preferences (onboarding).
> - test-author C, preparation only: PAC (9) and provider-compare in two new modules, `galleryPac.ts` and `galleryProviderCompare.ts`. It doesn't touch `gallery.spec.ts`: the `test(...)` blocks go in when the spec is free.
> - test-author B, preparation only (read-only, code in its report): group 2, plus the `file-menu` reshoot with `[DANSKE_SAMPLES.custody, DANSKE_SAMPLES.cash]`.
>   - The new premise: Danske reads the file, the generic CSV does not.
>   - The menu must have no `read-alone`.
>   - `writeExtendedCashStatement`, used only by that scenario, gets removed.
>   - It edits the spec after A.
>
> **Group 2 checks (before the brief):**
> - I's batch is in the base: `bc08101d6 feat(charts): gold dividends, period axis labels`, integrated in train 13. Group 2 is unblocked.
> - Hide amounts lives in `localStorage` only (`privacyStore.svelte.ts`), so it does not leak between tests. The header's `privacy-toggle` is visible on mobile too (no `hidden` class).
> - The mode and the P&L submode persist in `localStorage` (`dashboard-growth-pnl-submode`). Income opens at `1M` (`INCOME_OPENING_WIDTH`).
>   - So group 2 goes in a separate test after `main dashboard`, which stays untouched, with the same framing as `main`: the three P&L shots join its carousel.
> - **The real fixture (D1: nothing invented) limits what the shots can show:**
>   - `total_pnl` is positive on all 366 days (≈1 196 → 6 268 EUR), so the P&L line is all green. The dashed grey line is at the first visible day's P&L, not at zero, so it is always visible.
>   - `income_history`: dividends are 0 in all 12 months; interest, fees (`cost_history`), deposits and the split of purchases (`acquisition_funding`) are there.
>   - `pnl_candles.hypothetical: true`, so the Synthetic caption is there.
>   - The pages' text describes the function in general and stays true. The alt texts must not promise red or dividends.
>
> **docs-writer 1, finished (2 rounds):**
> - Round 1: 11 placeholders replaced.
>   - `correlation` 7, the 3 theory pages (`benchmark-selection`, `historical-replay`, `simulation-modes`), `risk.en.md` simulation, `danske-bank` `file-menu`.
>   - L's sentence, as its own paragraph, in «🧺 Upload both files together».
>   - Markup: the instructions' template, 700px. No `.it/.fr/.es` versions on those pages, so no translation debt.
> - Round 2: `getting-started` (welcome-setup 600px, core-tour-step and contextual-guide 700px) and `preferences` `onboarding-replay` (600px, no `style` like the rest of `user/settings/`).
>   - Q's text untouched. `privacy-masked` is still a placeholder, now at about line 109.
>   - Translation debt on both pages: the sections were already ahead of the translations after Q's wave 2. Nothing stamped.
> - Review: every alt text checked against the images in the base. The `lab-correlation` alt (0.94 Roma↔Milano, The ones that offset empty) matches today's PNG.
>   - The −0.30 threshold is about 5σ from independent mock series, so the alt stays true when regenerated.
>   - The `whatif-simulation` and `file-menu` alts describe the reshoots, which are still to come.
>
> **Two decisions raised by docs-writer 1, settled by M (fix tied to L's sentence):**
> 1. **«Continue» or «Parse»:** in Select Files the disabled button is **Parse (N)** (`import-wizard-parse`, `disabled={!step2CanParse}`, `ImportWizardModal.svelte:338/5280`). No «Continue» exists in that step, and the page already says **Parse** (lines 33 and 51).
>    - So L's sentence on the page now says **Parse**.
>    - The product message `importWizard.reportSet.ungroupedBlocks` says «Continue…» in all 4 languages. Reported to the coordinator for L (#26).
> 2. **Duplicate sentence:** Q's «Exports uploaded with LibreFolio 1.1.0 or earlier cannot: upload the two again, together.» repeated L's paragraph with another version threshold, so it was removed. «before 1.2» stays, consistent with the CHANGELOG (1.1.0 → 1.2.0).
>
> **test-author B, preparation finished (code in its report, nothing written).** M's review:
> - Accepted:
>   - `switchPnlSubmode` and the render-pass helpers, via `__lfChart` as in `dashboard.spec.ts`;
>   - the Candles → Income → Line order. Candles take their opening width only on the first entry after a load, and Income always reopens on 1M. The comment at `GrowthChart.svelte:89-90` says «every entry»: a note for I, not blocking;
>   - `reducedMotion: 'reduce'` only in the growth test, so the Synthetic caption's marquee stays still on mobile.
> - Privacy:
>   - the frame has the KPI row under the header, pinned by the focused eye button: the eye, the masked KPIs, and on desktop the chart's header with its masked axis;
>   - no tooltip, because there's no deterministic room for it;
>   - the masking checks read `•••` and the absence of digits: that's data, not a translation, as in `privacy-masking.spec.ts`;
>   - no product hook.
> - File menu: a real pair; premise DANSKE ∈ and GENERIC ∉ `compatible_plugins`; the menu has `preview`, `remove-from-set` and `delete`, and no `read-alone-*` at all. `writeExtendedCashStatement` is removed (no other user).
> - Docs crop `.chart-crop-container` (Q's `extra.css`): 580×420 at (−280, −290), so image rows 290–710.
>   - B estimates the Candles caption at y≈696–712: the bottom 2 px could be cut off. Checked on the real PNG before deciding.
> - Texts tied to the reshoot, already fixed:
>   - the `how-to.en.md:80` alt: «Preview, Remove from the set and Delete», no more «Read alone with Generic CSV». The IT/FR/ES translations don't have that image, so there's no stamp;
>   - the description of the gallery entry `🗃️ File Menu`, desktop and mobile.
>   - The `danske-bank` alt already matched the new menu.
> - Order: B writes to the spec only after A's lane run, which reads the spec.
>
> **Lane run 1 — A's code (fresh populate, 1 worker, port 6158):** `-f 'Dashboard Risk|what-if simulation'`, **10/10 passed in 9.9 min**, log `release-pipeline/runs/b5_runA_risk.log`. Load 15–30 at the start, 11 at the end.
> - Simulation, desktop: box **1090 px**, so the screen is **1280×1106** in all 8 combinations (A's estimate was ~930). The whole box is in frame, with notices, modes, cone and «What this simulation assumed». Checked on `desktop/en/light`.
> - `risk-whatif`: GFC chosen and dates 2007-10-09 → 2009-03-09 shown; the request window is moved to the portfolio's deepest fall (2026-09-29…2026-10-04).
>   - The engine's real answer: total −0.46%, 7 rows, KRW left out (no KRW/EUR rate), «Historical replay: Partial» notice. Same in all combinations.
>   - **Product nit** (Risk/F backlog, not blocking): the sentence «would have ended the period at −0.46% -€273.85» mixes U+2212 (percent) and the hyphen (amount).
> - At 720 px on desktop: `risk-hurt` VaR threshold ✗; `risk-diversification` matrix and pairs ✗; `risk-paid` chart ◐; `risk-whatif` table ◐. On mobile, the top of each block, as expected.
>
> **Coordinator decision (provisional, the developer is away until ~21:00): option 1.** The 4 desktop `dashboard/risk-*` get the screen as tall as the block, 1280 wide, same scale; mobile unchanged.
> - To make it reversible: one line per test, `if (viewport === 'desktop') await fitScreenToRiskBlock(…)`, with a reference to the simulation's comment.
> - If the developer chooses 720: delete the 4 lines and retake the 4 shots.
> - The alt texts are written on the whole block either way.
> - **GO A** at 20:03; the mobile shots from run 1 are final.
> - A done at 20:06: `RISK_FRAME_MARGIN = 8`, `fitScreenToRiskBlock` (fit, then 📐 log, reframe, double settle, whole block ratio 1), one desktop line per test; `canvasStill` also compares every `[data-chart-renders]`; timeouts 360/360/420/480 s; docblocks updated (exception = simulation + 4 Dashboard Risk blocks, desktop only, provisional). Prettier/tsc ok.
> - **GO B** at 20:06, done at 20:08: two new tests after `main dashboard` (untouched), file-menu with the real pair, `writeExtendedCashStatement` removed. Prettier ok, tsc 2 known errors, `-f` verified on 111 titles: only its 3 tests.
> - **Lane run 2a** (20:09, `--no-populate` on run 1's DB, so the desktop and mobile risk shots have the same data): `-f '(desktop .*Dashboard Risk)|growth P&L submodes|privacy mode|report set file menu'`. Log `runs/b5_run2a_riskdesk_group2.log`.
>   - **10/10 passed in 7.3 min**, load ~9; ports 6158/6168 free afterwards.
>   - Desktop Risk block → screen: hurt 801 → **1280×817**, diversification 1269 → **1280×1285**, paid 1149 → **1280×1165**, what-if 892 → **1280×908**. All 🖼️ parts ✓.
>   - Candles open on **3D** in all 16 combinations; Income on 1M.
>   - Images checked:
>     - risk-diversification: the whole block, matrix and pairs included;
>     - risk-paid: the table with Portfolio and MSCI World, the chart, the notes;
>     - risk-whatif: the whole block, 7 rows;
>     - risk-hurt: the whole block, but see the bug below;
>     - growth-pnl-line: all green, grey dashed reference line, dashed directa and Recrowd lines;
>     - candles: 3D–6M picker, period labels, Synthetic caption at y≈697–709, inside the `chart-crop-container` crop (rows 290–710);
>     - income: 1M, interest, fees, deposits, purchases; no dividends, as in the data;
>     - privacy-masked: `•••` with sign and currency, percentages readable, the chart's axis masked on desktop;
>     - file-menu: Preview, Remove from the set, Delete. The cash row is `danske_bank-cash.csv`.
>   - Accepted: the eye button's **focus ring** in `privacy-masked`, blue on desktop and amber on mobile. The focus is what keeps the header on screen, it's what a keyboard user sees, and it highlights the subject.
>   - Accepted: the mobile candles caption is cut on the right, because reduced motion stops the marquee.
> - **Product bug** (reported to the coordinator for Risk/F; the test needs no change):
>   - In `risk-hurt`, «Distribution of daily returns» has only 2 bars, plus «VaR threshold at −0.0%» (negative zero).
>   - Cause: `return_histogram` (`backend/app/services/risk/metrics.py:867`) takes the FD width from `np.histogram_bin_edges(bins="fd")`. With IQR = 0 and a non-zero range, NumPy gives a single bin over the whole range. The code only handles the zero-range case.
>   - In the test DB the admin's portfolio has had positions only since late summer, so most daily returns are 0. The mock prices are dense: 273–381 days per asset, checked read-only on the lane DB.
>   - The CI regenerates the PNGs at release, so once the bug is fixed the shot is right on its own.
> - **docs-writer 1, round 3** (20:20): the 4 `dashboard/risk-*` in the page and in the gallery (Risk Analysis section opened by the Dashboard's 5 entries, «🎲 Simulation» moved after «🔮 What If…?»), and group 2.
>   - In `charts.en.md` the 3 P&L shots use the same crop as `main`, through a single-item carousel: the JS ignores carousels with ≤1 item (`gallery-img-loader.js:195`), and the crop is CSS alone (`extra.css:1043-1075`, `!important`).
>   - **Done at 20:36.** Every alt written after looking at the PNG (desktop en/light, mobile en/light for the mobile gallery). No numbers; nothing the images don't show (no red, no Dividend bars, no split of purchases, no tooltip, no «Currently down…» card, no bug histogram).
>     - `risk.en.md` 19–21/47–49/71–73/98–100, at 700px.
>     - Gallery: Risk Analysis opens with Hurt → Diversified → Paid → What If → Simulation, then the lab's 7. Mobile descriptions match the mobile PNGs (top of the block).
>     - Growth carousel: +3 items, and the sentence now covers P&L. «### 🙈 Privacy Mode» uses the placeholder's sentence.
>     - `charts.en.md`: privacy at 24–26 (700px), P&L at 73–77/85–89/113–117 (crop).
>     - `preferences.en.md` 109–111 at 600px, like the page's other images.
>   - Translation debt: `charts`, `preferences` and the gallery IT/FR/ES already lacked these sections. Nothing stamped. `risk` is English-only.
>   - M review: gallery markup (carousel `img` items, `---` rule) and single-item carousels checked; `git diff --check` clean.
> - **Lane run 2b** (20:17, fresh populate, P's seed): `-f 'Screenshots (Brokers|Transactions) '`, **58 tests**; the form variants count one per combination. Log `runs/b5_run2b_retakes.log`.
> - **test-author C, preparation finished** (20:20): `galleryPac.ts` (784 lines) and `galleryProviderCompare.ts` (335). Prettier ok, tsc 2 known errors. Not yet in the spec: it writes after run 2b.
>   - PAC: real data, read only. One draft per test, two tests (steps, result). The draft survives language and theme changes (store and `ToolHost`, checked in the code); every result shot asserts `data-stale=false`.
>   - Provider-compare: an invented fund (`IE000NWGE006`, ticker `NWGE.MI`). Search, REST fallback and probe are answered by routes registered after the guard, validated on the Zod schemas; everything else uses `route.fallback()`. Nothing is created.
>   - Scan: no `waitForTimeout`, no `isVisible({timeout})`, no text or CSS selectors, only GETs via `page.request`.
>   - **Open question to the coordinator** (20:24): extend the tall-screen rule to `tools/pac-result-proof` (~1100 px) and to `assets/create-provider-compare` (body `max-h-[60vh]`, content ~700 px, so ~1200 px of screen).
>     - **Coordinator decision (20:27, provisional):** yes, the same rule, desktop only, one line per test. The 6 shots go to the developer as a single question.
>     - C changes only its two modules during run 2b. The spec gets written on «GO C SPEC».
>     - The tall screen is restored to 1280×720 after the tall shot, within the same combination: the other shots of the same test (`pac-result`, `pac-result-plan`, the asset form) must stay at 720.
>   - Accepted: «Calculation data (N)» stays closed in Review, otherwise Calculate goes off screen.
>   - **C, update after the decision** (20:33): `fitScreenToPacProof` and `fitScreenToCompareDialog`.
>     - The compare dialog: H = max(720, ⌈(scrollHeight+1)/0.6⌉, ⌈dialog/0.9⌉), then wait until the body stops scrolling.
>     - Plus `restorePacScreen` and `restoreCompareScreen`, which put back the screen the fit found; they do nothing on mobile, because `setViewportSize` would also overwrite the emulated screen there.
>     - One `if (viewport === 'desktop')` line per test, with a comment pointing to the simulation's decision.
>     - Correction: the mobile viewport is **430×740** (the iPhone screen is 430×932).
> - **Marquee caught mid-scroll** (found in the run 2b retakes; it predates this batch):
>   - `scrollOnOverflow` (`frontend/src/lib/actions/scrollOnOverflow.ts`) starts 2 s after mount. `freezeAnimations()` doesn't stop it, because it's JS.
>   - `broker list` waits exactly 2000 ms, so the card names are always mid-scroll («harle», «oinba», «EGIR»).
>   - The same marquee is in KpiCard, AssetCard, RiskMetricCard, AssetPickerPanel, ImportWizardModal, AssetGroupStep, CorrelationPairsList, the asset detail page and the PAC.
>   - Under `prefers-reduced-motion: reduce` it doesn't start (`scrollOnOverflow.ts:49`).
>   - **Now:** one `emulateMedia({reducedMotion: 'reduce'})` line in the `broker list` test, via C together with its insertion, then reshoot in run 3.
>   - **Proposal to the coordinator** (gallery-wide reduced motion + full gallery, after integration): awaiting a decision.
>   - **Coordinator decision (20:40):**
>     1. Yes to the `broker list` line in this batch.
>     2. Yes to `reducedMotion: 'reduce'` in the gallery's top-level `beforeEach`, **after 22:00** (end of the run on 6150): first the audit, then a full gallery on the lane and a comparison of the changed shots, which must only be marquees or wanted effects. In a **separate commit** of the same checkpoint, with the list of changed shots in the body.
>   - **Audit of who reads `prefers-reduced-motion`** (code and CSS, `frontend/src`, at 20:45):
>
>     | Where | Effect under `reduce` | Photographed? | Verdict |
>     |---|---|---|---|
>     | `lib/actions/scrollOnOverflow.ts:49,121` (KpiCard, AssetCard, BrokerCard, BrokerDiscoveryCard, RiskMetricCard, AssetPickerPanel, ImportWizardModal, AssetGroupStep, TransactionCompareModal, DataTableColumnFilter, CorrelationPairsList, AboutTab, GrowthChart, asset detail, PAC) | the marquee doesn't start; the text rests at its start | yes | **the goal** |
>     | `components/onboarding/OnboardingIntroScene.svelte:54-166` | all the phrases together, dots all active, no fade | **no**: `walkCoreTourToFx` only clicks Start | no visible effect |
>     | `components/onboarding/OnboardingCoachmark.svelte:468-479,542,546` | `scrollIntoView` auto instead of smooth; pulse ring and cursor bounce stopped (`motion-reduce:animate-none`) | yes (`core-tour-step`, `contextual-guide`) | wanted: ring at opacity 1 instead of ~0.95 (frozen at 0.1 s), cursor a few px lower |
>     | `features/tools/pac-allocator/planner/result/ResultView.svelte:94` | `scrollIntoView` auto | the final state, yes | no static difference |
>     | `app.css:356` (`.lf-price-flash-*`) | no animation, peak colour while the class is on | no: the gallery is offline, prices are fixed, nothing flashes | none |
>     | `components/table/DataTable.svelte:1925` (`tr.highlighted`) | static highlight | only if a row is highlighted at the shot | wanted |
>     | Tailwind `motion-safe:animate-spin` (PAC AssetsStep, FxStep, BusyPanel), `motion-reduce:animate-none` (ToolsHub, ToolHost, ToolDiagnosticsPanel, ToolAboutPanel), `motion-reduce:transition-none` (Header, IntroScene), `motion-safe:transition-*` (PAC StepNav) | spinners and pulses stopped, no transitions | no: shots wait for idle/ready, and `freezeAnimations()` already zeroes transitions | none |
>     | `ui/TweenedValue.svelte` (`tweened` from `svelte/motion`) | **none**: `tweened` ignores the preference | — | the KPI count-ups stay, and so does the 1 s wait |
>
>     Nothing hides content that the pages describe. ECharts doesn't read the preference.
>   - **Plan after 22:00:**
>     - (a) Fresh-populate **baseline** full gallery with the batch's spec, without the global rule. Copy the PNGs to `/tmp/librefolio-r2-m-gallery-baseline/` (2148 PNGs, 354 MB; 40 GB free).
>     - (b) test-author adds the line to the top-level `beforeEach` (the per-test lines become redundant).
>     - (c) Full gallery, fresh populate, same day.
>     - (d) Pixel diff per PNG (script in `release-pipeline/scripts/`), then classify every changed shot by eye: marquee, coachmark, or noise to explain.
> - **Lane run 2b — Brokers and Transactions retakes:** **58/58 passed in 26.8 min** (20:17–20:45), 737 shots, 0 failures. Log `runs/b5_run2b_retakes.log`. Ports free afterwards.
>   - P's seed is visible: Coinbase with 4,181.08 USD + 200 EUR in the list; transactions with ETH ADJUSTMENT movements.
>   - **Observation, predates this batch** (not in scope): `brokers/fifo-lots-panel` (Bitcoin, Coinbase) shows «1 error(s)» and «Lot analysis could not be reconstructed reliably (inconsistent quantities or transfers)», with the average cost jumping to ~43K.
>     - The image published on GitHub Pages (built from v1.1.0, fetched with curl) already had the same banner.
>     - It goes in the handoff as a backlog note (seed or FIFO).
> - `gallery_diff.py` script (in `release-pipeline/scripts/`, shared venv for Pillow and NumPy): per-PNG diff with threshold 8 per channel, CSV + MD grouped by shot (changed combinations, maximum pixels, union bbox). Self-test ok.
> - **GO C SPEC** (20:46), done at 20:52:
>   - imports after `galleryOnboarding`;
>   - the 2 PAC tests in `Tools` after `tools hub`;
>   - provider compare in `Assets` between `Asset type picker open` and `Asset distribution editors`;
>   - `broker list` with `emulateMedia({reducedMotion: 'reduce'})` as its first line.
>   - Prettier ok, tsc 2 known errors. Filter `PAC allocator|provider compare|broker list - all` checked against 115 titles plus 16 describes: exactly 4.
> - **Lane run 3** (20:53, fresh populate, 1 worker): `-f 'PAC allocator|provider compare|broker list - all'`. Log `runs/b5_run3_pac_compare_brokerlist.log`.
>   - **4 passed, 4 failed** (3.1 min). Provider compare ✓ and broker list ✓, desktop and mobile. Both PAC tests ✗ in both projects, before any shot.
>   - **PAC cause:** a selector in `galleryPac.ts:265` (`copyFromBroker`). `…-copy-cash` → `[data-currency="EUR"]` matches 2 elements: the cash row «EUR custody 8,200.00» and the inner currency label. Strict mode violation.
>     - The message «Broker 2 holds no EUR cash» was misleading: the cash is there. Sent to C (fix the selector and check the other `[data-currency]`), then rerun with `--no-populate`.
>   - Provider compare, desktop: dialog 867–887 px, body 734–754 px, so the screen is **1280×1225–1259** depending on the language.
>     - Complete: TICKER with «Which TICKER is the main one…» (`NWGE.MI` from the provider vs `NWGE` already saved, alternates kept); Type ETF → Equity ETF as badges; Sector Distribution Industrials 100% vs 3 sectors; Apply Selected (3/3).
>     - The asset names behind the dialog are caught mid-marquee: the gallery-wide rule will fix it.
>   - Broker list: the names now rest at their beginning («Charl», «Coinb», «DEGII»).
>     - **Product layout note** (backlog, not in scope): at 1280 the BrokerCard header leaves ~5 characters for the name next to the crown and 4 icons.
> - **C's selector fix** (`:scope > [data-currency="EUR"]`, at least one row; other locators checked), then **rerun 3b** (`--no-populate`, `-f 'PAC allocator'`, log `runs/b5_run3b_pac.log`): 4 failed, at the next step.
>   - `galleryPac.ts:415` expected the DEGIRO→Apple route to be `data-ready=false`, because DEGIRO had no USD mode. The product has it `true`: in the draft DEGIRO converts the currency itself («the Broker converts»).
>   - So the precondition is wrong, not the product.
> - **Lane granted to C (21:02) for the PAC tests only**, so it can iterate without round trips: the exact command, 1 worker, 6158, `--no-populate`, logs in `runs/b5_run3c_pac_<n>.log`, port free after every run, budget until 21:40. M runs nothing on the lane in the meantime.
> - **docs-writer 1, round 4** (provider-compare), done:
>   - `create-edit.en.md` 87–89 at 700px, with an alt on the whole dialog (no fund, code or numbers);
>   - gallery «### 🔍 Provider Data Comparison», desktop 719–725 and mobile 723–729; the mobile description covers only TICKER and Type, which is what the phone shows.
>   - `create-edit` IT/FR/ES already lacked the section, and the gallery IT/FR/ES lack the entry. Nothing stamped.
> - **Interim gates** (21:02–21:05, outside the lane, `nice -n 10`), same as the baseline:
>   - `mkdocs build` (strict): exit 0, 38.7 s;
>   - `mkdocs check-links`: 89 valid, 3 known exceptions, 1 broken = the pre-existing `user/assets/detail/chart/#rolling-return`;
>   - Prettier on the 6 e2e files touched: clean;
>   - `tsc -p tsconfig.e2e.json`: only the 2 known errors.
>   - Logs `runs/b5_gates_docs_1.log` and `runs/b5_gates_front_1.log`. To repeat after the PAC round.
> - **Developer on the tall shots** (via the coordinator, 21:15), verbatim: «in effetti, alzare il blocco potrebbe essere una grande idea, anche per dashboard e altre pagine che proseguono più a lungo, puoi chiedere una lista ad M prima di partire, così decidiamo assieme?»
>   - Request: a list of every desktop shot (existing and from this batch) whose subject continues beyond 720 px. For each:
>     - the shot name and the app page;
>     - the measured height of its subject at 1280;
>     - what is cut off today;
>     - the doc pages that use it, and their texts;
>     - a proposal: (a) screen as tall as the block, (b) `fullPage` for continuous lists, (c) stay at 720;
>     - the resulting height in the doc at 700 px;
>     - the cost of retaking it.
>   - Grouped by gallery section. The 6 provisional shots stay as they are; the rule is not extended until a decision is made.
> - **How M measures:**
>   - A temporary hook in `screenshot()`, the only point all 136 calls pass through, as a patch outside the repo: `release-pipeline/scripts/gallery_measure.patch`.
>     - Guarded by `LF_GALLERY_MEASURE=log|only` + `LF_GALLERY_MEASURE_OUT`. It reads layout only.
>     - Per shot: tallest blocks cut at the bottom edge, blocks cut at the top, page height and scroll, scroll containers with hidden content, open dialogs.
>     - Applied only for that run, then reverted with `git apply -R`; never committed.
>   - `release-pipeline/scripts/gallery_tall_list.py` crosses the measurements with the docs (pages and alts per `data-category`/`data-name`) and with the log (test and duration of each shot).
>   - Proposed to the coordinator: the measurement rides on the **baseline** full gallery that the reduced-motion comparison needs anyway (one full gallery saved, ~45 min). If the coordinator prefers a separate run without PNGs, M does that.
>   - **Approved (21:20)**; the patch comes off before the checkpoint.
>   - **Load constraint:** from ~21:55 the train 19 gates run on 6150 (~1h15, 2 E2E workers). Until they finish, the gallery runs at **2 workers**, then 4. The red runs tonight came from the load.
>   - Q's two sentences are coming, to apply as they are (`correlation.en.md:153`, the returns' currency = Default Currency since train 18; `preferences.en.md`, the currency the pages open in).
>   - **Applied verbatim at 21:24** (Q's message, sources `stores/app/settings.ts` `defaultDisplayCurrency`, `routes/(app)/assets/+page.svelte:1618`, `restoredView.targetCurrency`):
>     - `correlation.en.md` «One currency.» now points to the Default Currency in [Preferences](../settings/preferences.md);
>     - the **Default Currency** row in `preferences.en.md` now lists the pages that open in it, and says the Dashboard keeps its choice for the session.
>     - English only, no stamp. Q won't touch `correlation`, `preferences` or `getting-started` until this batch is integrated.
> - **C, PAC iteration on the lane** (21:02–21:33, runs `b5_run3c_pac_1…8.log`): **both PAC tests green** on desktop (`_8`, 2 passed 1.3 min) and mobile (`_7`, 2 passed 1.4 min). Lane free after every run.
>   - **Routing:** a route is ready when the Broker has an order mode in the asset's price currency (`draft.modeFor`, `draft.svelte.ts:397`).
>     - The seed books the AAPL and MSFT transfers on DEGIRO in USD with amount 0 (`populate_mock_data.py` ~1593, ~1800), so the copy brings a «DEGIRO USD 0» cash row.
>     - The draft removes that row and DEGIRO's USD mode, then excludes Apple and Microsoft with the toggle.
>   - **PAC product bug** (reported to the coordinator at 21:34): with a foreign-currency source, «Calculation failed».
>     - USD: `WireNumberTooLargeError` (`wire_numbers.py:142`). The conversion uses the inverse of the stored rate (`evaluator.py:206`), giving an infinitely repeating decimal (`numeric.py:252`) that `planner_report.py:667` can't write.
>     - CHF: `ValueError` `_require_nonnegative` (`models.py:129`).
>     - Gallery workaround: the external account is in EUR; the reason and the way back are next to `PAC_SCENARIO.externalAccount`.
>   - The header reappears after a resize. The fit helper now waits for the resize event, goes to the top, waits two frames, then reframes.
>   - Phone broker editor: the conversion choice is below the fold (asserted only when the block fits, on desktop).
>   - Desktop proof 📐: en 1383 → **1280×1399**; it, fr 1399 → 1415; es 1419 → 1435.
>   - **Compromises:**
>     - Liquidity framed from the first card;
>     - Review with the step title scrolled away, so Calculate clears the footer;
>     - Result: on desktop only the title of «Allocation per Asset» fits. A candidate for the tall-screen list.
>   - M checked `pac-result-plan` (4 steps, orders by broker): ok.
> - **Measurement patch applied** (21:36): `git apply`; copy of the spec before it in `/tmp/librefolio-r2-m-measure/spec_before_measure.ts`, for a byte-for-byte check after `git apply -R`.
>   - Probe in `only` mode (`-f 'transaction list - all|dashboard allocation charts'`, desktop, 1 worker): 2 passed, 56 JSONL lines, no PNG, port free.
>   - `gallery_tall_list.py` leaves out `app-shell` and reports the top 3 blocks cut; on the probe it lists `transactions/list` (page 3095, `tx-table` 2918), with its doc pages and test.
> - **docs-writer 1, round 5 (PAC)** sent at 21:40.
>   - **Done at 21:44.** All 18 PNGs viewed before writing (desktop and mobile en/light).
>     - `pac-allocator/index.en.md`: 9 blocks in the form of `user/tools/index.en.md` (700px, no `style`), at lines 50–52, 100–102, 126–128, 159–161, 200–202, 277–279, 322–324, 393–395, 407–409.
>     - Alts with no names, amounts or counts; the only number is «100%», the rule for the targets.
>     - Nothing the images don't show: Liquidity without «its own currency», Result with only the title of «Allocation per Asset», Balance all disabled (checked in `TargetsStep.svelte`).
>   - Gallery: the Tools section is Tools Hub followed by 9 PAC entries. The placeholders' descriptions were kept when true and corrected when they promised parts that aren't visible: Result without the allocation, the mobile entries on what the phone shows.
>   - Debt: `pac-allocator` English-only; the gallery IT/FR/ES have no Tools section at all. Nothing stamped.
>   - **Census:** the only placeholders left in the EN docs are the **8 broker portals** (after 1.2, by decision).
> - **B, gallery-wide reduced motion prepared** (21:43, not written: waiting for «GO B2» after the baseline):
>   - The choice is `test.use({contextOptions: {reducedMotion: 'reduce'}})` next to `actionTimeout`.
>     - In Playwright 1.61 `reducedMotion` exists only under `contextOptions`.
>     - Set on the context, it covers every page from the first document, regardless of hook order, and future popups too.
>   - Inventory: 128 tests and hooks, all on the `page` fixture (`{page}` 117, `{page, request}` 11). No `newContext`, `newPage`, popup or `window.open` in the spec or its helpers. Second users sign in on the same page.
>   - The 2 per-test lines (growth, broker list) are removed. In growth, `toBeInViewport` reads the box, not the scroll position. In broker list the 2 s wait stays because it's for the favicons.
>   - Audit check: spinners rest at 0°; the coachmark fade is a JS timer, so `holdPanelAtFullStrength` still works; ECharts 6.0.0 and `tweened` (svelte 5.48) ignore the preference.
> - **Baseline full gallery + measurement** (21:50, fresh populate, **2 workers**, `LF_GALLERY_MEASURE=log`): log `runs/b5_baseline_full.log`, measurements `runs/b5_baseline_measure.jsonl`.
>   - Load 46–50 at the start. Mostly macOS system processes: `mediaanalysisd` ~170% and Spotlight, probably set off by the thousands of PNGs written in the gallery folders. Not the lanes.
>   - **Result: 243 passed, 1 skipped, 0 failed in 1.1 h** (21:52–22:58). 2711 measurement lines. Ports free afterwards.
> - **After the baseline** (`release-pipeline/scripts/b5_after_baseline.sh`):
>   - 2796 baseline PNGs in `/tmp/librefolio-r2-m-gallery-baseline/`;
>   - measurement hook taken off with `git apply -R`, and the spec matches the pre-hook copy byte for byte (`cmp`);
>   - the **C1 spec** saved as `release-pipeline/c1_gallery.spec.ts` (sha256 `b38973ab…`);
>   - `git diff --check` ok.
> - **New product bug seen in `brokers/import-wizard-step4-resolution`:** the badge reads «1 1 assets unresolved». `ImportWizardModal.svelte:4972` prints `{step4UnresolvedCount}` and then the string `importWizard.unresolvedCount` = "{n} assets unresolved", which already contains `{n}`. The singular is missing too. Goes in the handoff.
> - **Tall-shot list** (sent to the coordinator at 23:03): `release-pipeline/lista_scatti_alti.md`, in Italian, grouped by section.
>   - Scripts: `gallery_shot_tests.py` (static map from shot to test and helper, with durations), `gallery_tall_report.py` (facts and table), `gallery_tall_proposals.py` (rules plus per-shot judgments).
>   - **175 desktop shots, 135 continue beyond 720 px** (or are already tall). 7 are already tall; **new proposals: 36 (a), 2 (b), 90 (c)**.
>   - Retaking (a)/(b): 27 desktop tests, ~13 min. Once only: a generic helper for dialogs (11 of the (a) are dialogs whose body is in `vh`) and a `fullPage` parameter.
>   - Doc height of (a)/(b) at 700 px: median 494, maximum ~1004.
>   - Judgments checked by eye on the PNGs:
>     - `positions-performance-table`: 6 rows of ~17;
>     - `detail-signals`: chart mostly cut off;
>     - `import-wizard-step2` and `step4`: subject in view, so (c);
>     - lot detail: the doc's Asset Income row is in view, so (c);
>     - risk lab: the measured cut block is the next section, so (c), except `lab-risk-return` (a, 75 px).
>     - A false positive in the regex («per**form**ance») was fixed.
> - **GO B2** (22:59): `test.use({contextOptions: {reducedMotion: 'reduce'}})` at lines 302–310, the per-test lines in growth (≈1050) and broker list (≈2674) removed. Prettier ok, tsc 2 known errors.
>   - **C3 patch** = diff between C1 and the final spec: `release-pipeline/c3_reduced_motion.patch`, 3 hunks, 19 lines. Final spec copy: `c3_gallery.spec.ts`.
> - **Reduced-motion full gallery** (23:00, fresh populate, **2 workers like the baseline**, so the timing conditions match): log `runs/b5_reduced_motion_full.log`.
> - **Developer on the tall-shot list** (via the coordinator, 23:12), verbatim: «si si modifica il codice, tanto la pipeline poi rigira tutto a prescindere, per le prove però lancia solo quelle che modifica per ora».
>   - **All M's proposals approved:** 36 (a), 2 (b) (`brokers/list` and `settings/global-settings` as full pages), 90 (c).
>   - **The list is the reference for this step:** `/Users/ea_enel/Documents/00_My/LibreFolio-cloud-sizing/release-pipeline/lista_scatti_alti.md`, with data in `runs/b5_tall_report.json`, `b5_tall_proposals.json` and `b5_tall_worklist.json` (38 shots, ~27 tests).
>   - Code to write:
>     - a generic dialog helper;
>     - an `extendScreenToBlock` that keeps today's framing;
>     - an optional `fullPage` in `screenshot()`;
>     - one desktop line per shot.
>   - Proof: **only the modified tests** (`--desktop-only`), no full gallery for this change.
>   - **A separate commit** (C4) with the list of shots touched in its body.
>   - The reduced-motion gallery runs to the end, for the comparison.
>   - Briefed to **A** (23:15): phase 1 is the new module `galleryTallShots.ts` (safe while the run is going); phase 2, on «GO A2» after the run, writes the spec and gets the lane `--desktop-only`.
>   - **A, phase 1 done (23:50):** `galleryTallShots.ts`, Prettier ok, tsc 2 known errors.
>     - `extendScreenToBlock` keeps frame and scroll. The header hides only after 8 px of scrolling down, so the helper re-scrolls with a 16 px step and asserts it's hidden. It re-measures blocks that grow with the screen (holdings map 65vh, performance chart 70vh), never goes past the end of the page, and leaves room for the PAC sticky footer.
>     - `fitScreenToDialog` reads the cascade of caps and fails loudly on a cap in px.
>     - `restoreTallScreen` does nothing if there was no fit.
>     - `screenshot()` gets `{fullPage?}` (desktop only).
>   - **5 of M's proposals change to (c)** on technical grounds (accepted by M; goes to the coordinator):
>     - `assets/detail-editor`, `fx/detail-editor`: the box is capped at 500 px (`DataEditor.svelte:684`);
>     - `assets/type-picker-open`: the menu is capped at 420 px (`TreeSelect.svelte:398`);
>     - `fx/detail-csv-import`: the measurement was of the editor behind; the CSV dialog is already whole;
>     - `assets/detail-signals-tree`: with more height the menu would open downwards, over the chart.
>   - So **33 shots in 34 tests** (26 titles + the 8 form-variant tests). The `--desktop-only` filter was checked by A against all 115 titles.
>   - Expected H corrected upwards for the blocks and dialogs whose caps grow with the screen: holdings map ~1146 (dashboard) and ~1277 (brokers), `fx/add-pair-chain` ~1182, `assets/create-modal` ~916.
>   - Risk to check: fullPage and the fixed sidebar. The fallback is `extendScreenToBlock(body)`.
> - **Reduced-motion full gallery: 243 passed, 1 skipped, 0 failed in 1.1 h** (23:01–00:04). Copy in `/tmp/librefolio-r2-m-gallery-rm/` (2796 PNGs). Ports free afterwards.
> - **Base vs reduced motion comparison** (`gallery_diff.py`, threshold 8): **659 of 2796 PNGs changed, 124 groups**.
>   - Every group checked by eye: samples top/bottom from `gallery_diff_samples.py`, contact sheets, heat maps for the doubtful ones.
>   - Classification in `release-pipeline/runs/b5_rm_classification.md`:
>     1. **Marquee at rest (the goal):** `assets/list-filtered` (desktop and mobile), `assets/create-provider-compare` (cards behind the dialog), `tools/pac-result-proof` (solver stages), `tools/pac-result-plan` (order names), `support/social-share-modal` mobile (browser line).
>     2. **Wanted static state:** the FIFO lot tables. `DataTable.svelte:1925` stops the `tr.highlighted` animation; before, the shot froze a frame of it.
>     3. **Not caused by reduced motion:**
>        - data that changes from one populate to the next: file times, random images, `demo_*` accounts, tokens, process id, scheduler, PAC timings, KPI ±0.1%;
>        - pre-existing orderings and races: imports, «validando…», wizard panels, «1/16», favicons, About framing, `fifo-lots-panel`;
>        - AnimatedBackground frozen at a variable frame;
>        - **the midnight rollover** (115 mobile PNGs after 00:00, the mock price window moves with the date);
>        - sub-10-px noise.
>   - So the coordinator's condition holds: the look changes caused by reduced motion are only the marquee and the wanted static states.
>   - The C3 body lists the changed shots (commit proposal updated).
>   - The pre-existing gallery nondeterminism goes in the handoff as a backlog item.
> - **The coordinator's request (00:10): CI red `Files › file preview modal (image)`**, to analyse after the checkpoint without interrupting it. Read-only pre-analysis with `test-triage` while A uses the lane: `release-pipeline/runs/b5_ci_triage_file_preview.md`.
>   - **Verdict: assumption (time + position).**
>     - 32 `page.goto` + `setLanguage`/`setTheme` + `networkidle` + 2.4 s of fixed waits. Locally 3.5–3.6 min of the 240 s budget (87–90%); in CI it goes over at `es`. The failing line varies, which is the sign of a time limit.
>     - The image is whatever row comes first (`.first()`): men_12 and men_15 between two runs.
>     - **Hidden defect:** two `if (await …isVisible({timeout}))`. Playwright 1.61 ignores the timeout, so a shot can be skipped silently.
>     - The older nightly's grid red: `networkidle` 20 s on the Files page.
>   - **Fix** (spec, test-author, after the checkpoint):
>     - one test per type;
>     - one navigation per test, with language and theme switched in the app;
>     - the row by name (seeded avatar `men_01.png`);
>     - `expect().toBeVisible()`;
>     - readiness (img `complete`, rendered content, PDF state or a §6 hook);
>     - same treatment for the grid and table tests.
>   - **Release:** `continue-on-error: ${{ github.ref_name == 'dev' }}`. On a `release` event the ref is the tag, so **the 4 steps block, `-rc.N` included**.
>     - The first one stopping the job today is `translate-diff --issues-only` (translation debt), then translation links, `check-links` (`#rolling-return`), then the gallery.
> - **A, C4 done (00:35):** 33 shots, `b5_c4_5` **34/34 green in 8.6 min** (desktop only), plus `b5_c4_6` 2/2 after the framing fixes. Lane free; Prettier ok; tsc 2 known errors.
>   - Measured H, at 1280:
>     - Dashboard positions: holdings-table 929, holdings-map 1145, performance-table 1325, performance-map 1102.
>     - Brokers: holdings-map 1275, performance-table 767, detail 1253, info-tab 1026–1056, list 1101–1161.
>     - Settings: global-settings 1820–1836, profile 830, about-plugin-diagnostics 728, about-tool-diagnostics 858, onboarding-replay 854–874.
>     - PAC: liquidity 823, result 973–1021, result-plan 789.
>     - Assets: list-table 878, detail-chart 865 (and candlestick), detail-signals 1019, drawdown 1157, measures-active 804, chart-settings 1004, create-modal 916.
>     - Others: lab-risk-return 804, fx/detail-signals 903, files/static-tab 891, form-modal-transfer 884, action-modal 1163, edit-modal 1011, add-pair-chain 1162–1200, fx/chart-settings 1004.
>   - **⚠️ Fuori pista:**
>     1. **`fullPage` dropped.** Playwright's full-page capture keeps the 720 px screen, so the fixed sidebar stops at 720 and the page below is blank (seen in `b5_c4_1`). The 2 (b) shots take the body as the block, so the screen is as tall as the page: the same result the developer approved, with the sidebar whole. The `{fullPage}` option has been taken out of `screenshot()`.
>     2. **Treemap canvas** with broker logos from other origins can't be read (tainted). The stillness check uses size + `data-chart-renders` instead.
>     3. **Broker edit modal:** the sticky footer hangs 16 px below the form, so the fit uses natural height vs visible height.
>     4. Charts that grow with the screen are re-measured until they fit.
>     5. **Two pre-existing framing races fixed** (desktop only): the positions panel is framed from the top of the page (929 in all 8 combinations; one was 728 before), and About plugin diagnostics waits for the Tools panel (728 in all 8; one was 852).
>   - **Pre-existing defect found by A:** `profile tab` looked for /profile/i in the tab text. It never matched it/fr/es, nor mobile (`hideLabelOnMobile`), and the `if (isVisible())` skipped silently. **The only `settings/profile` PNG ever produced is desktop en** (it/fr/es and mobile are 404 on Pages too). Assigned to A at 00:38 (testid `settings-tab-profile` + `expect`), with a run on both viewports.
>   - **Profile fix** (`b5_c4_7`, both viewports): 2/2 in 31 s.
>     - Locator `settings-tab-profile` with `expect` and `aria-selected`; waits for `profile-tab` `data-busy=false` and the avatar loaded (no 300 ms).
>     - The desktop tall block is `settings-page` (1280×855 in all 8 combinations), so the card is whole.
>     - The 16 `settings/profile` PNGs now exist; it/fr/es and mobile for the first time.
>     - Product nit: «Account Created» is formatted in the browser's locale (`toLocaleDateString(undefined, …)`), not the app's.
>   - M checked by eye `positions-performance-table` (14 rows + Other period effects), `brokers/list` (8 cards, sidebar whole) and `pac-result` (Allocation per Asset table whole).
>   - No doc crop container uses one of the 40 tall shots.
>   - **C4 patch** = diff between C3 and the final spec: `release-pipeline/c4_tall_shots.patch`, 34 hunks, 148 lines; plus `galleryTallShots.ts`. The other fixtures haven't changed since the C1 snapshot (mtimes ≤ 21:25, C1 22:58).
>
> **Final state, 2026-10-09 00:45:**
> - Gates:
>   - Prettier clean on the 7 e2e files;
>   - `tsc -p tsconfig.e2e.json`: only the 2 known errors;
>   - strict build and check-links as in `b5_gates_docs_2` (docs unchanged since then): 89 valid, 3 known, 1 pre-existing (`#rolling-return`);
>   - `git diff --check` ok.
> - Ports 6158/6168 free.
> - Lane DB clean: 0 `provider:*` rows, 0 `demo_*` accounts, 0 brokers marked with `·`.
> - The measurement hook is not in the spec (`git apply -R` checked with `cmp`).
> - Spec versions for the commits:
>   - C1 `release-pipeline/c1_gallery.spec.ts` (sha256 `b38973ab4adc557d…`);
>   - C3 `c3_gallery.spec.ts` (`643df57ac45b9db0…`);
>   - C4 = the worktree (`89ba5fe5e12532df…`).
> - Commit proposals: `release-pipeline/commit_proposal_B5.txt` (C1 test, C2 docs, C3 reduced motion, C4 tall shots + journal).
>
> **Committed** (train 21, 2026-10-09): `ee5a2e277`, `797a629d7`, `02ae0e09d`, `d7481a7e7`, merge `e3c1aee06`; `dev_release2` = `9b2acdd5d`.

## Batch 6 — the gallery Files family and the PDF preview state (base `9b2acdd5d`, train 21, M and D integrated)

### 19. ✅ The CI red `Files › file preview modal (image)` and its family; PDF loaded state; PAC back to USD — 2026-10-09

> **Note implementazione**:
>
> **Origin:** the coordinator (2026-10-09 00:10).
> - Nightly `37843184859`: the desktop test hit 240 s on all 3 attempts; mobile went green on the second retry.
> - Nightly `37772325521`: the same, plus `static resources grid view` red.
> - Triage `release-pipeline/runs/b5_ci_triage_file_preview.md`. **Verdict: assumption (time + position).**
>
> **Coordinator decisions** (00:50, 07:52):
> 1. In the product, `data-state="loading|ready|error"` and `aria-busy` on `file-preview-pdf` (§6 of `test-triage`).
>    - M is the only writer of `FilePreviewModal.svelte` until the checkpoint.
>    - The state logic goes in a pure helper with unit tests.
>    - Also run the existing non-gallery E2E tests that open the preview.
> 2. Scope = the whole gallery `Files` family, 5 tests: static tab, broker reports tab, grid view, BRIM preview, image/PDF/markdown/text preview.
> 3. Proof: only the tests that change, plus the preview E2E tests. No CHANGELOG entry: this is test and observability work.
> 4. D (PAC, row 15, train 21) fixed the engine (`bffc634b0 fix(pac): exact FX residual, coherent cross rates`), so `PAC_SCENARIO.externalAccount` goes back to USD.
>    - Both PAC tests share the draft, so both get run: this also checks D's fix on the result path.
> 5. Load: the train-21 gates run on 6150 for about 30 min, so 2 workers.
>
> **Facts about the product (EmbedPDF `@embedpdf/snippet` 2.14.3)**
> - `EmbedPDF.init()` returns the container, whose `registry` is a `Promise<PluginRegistry>`.
> - Plugins: `document-manager` (`onDocumentOpened`, `onDocumentError`) and `tiling` (`onTileRendering`: `{documentId, tiles: Record<page, Tile[]>}`, each `Tile.status` is `queued|rendering|ready` plus `isFallback`).
> - Both are **behavior emitters** (`createBehaviorEmitter`): a late listener receives the latest value, so subscribing after `init` loses nothing.
> - A tile becomes `ready` when its render task finishes (`plugin-tiling/dist/index.js:317-328`). Once all of a page's new tiles are `ready`, the fallback ones are dropped (`:110-118`).
> - Rule chosen: **ready = document open AND at least one non-fallback tile AND every non-fallback tile visible `ready`**; **error = `onDocumentError`**; anything else is loading.
>
> **19.1 ✅ Product (M), 2026-10-09 08:15**
> - New pure helper `frontend/src/lib/utils/files/pdfPreviewState.ts`: `pdfPreviewState(reports)` → `loading|ready|error`, from `{opened, failed, tiles}`. Fallback tiles are ignored.
> - `FilePreviewModal.svelte`, PDF effect only:
>   - after `EmbedPDF.init`, `await viewer.registry`; the two plugins are `getPlugin(DocumentManagerPlugin.id / TilingPlugin.id).provides()`, with the ids and types taken from the same lazy `import('@embedpdf/snippet')`;
>   - subscribes to `onDocumentOpened`, `onDocumentError` and `onTileRendering`; unsubscribes in the cleanup;
>   - a `disposed` flag means a subscription that arrives after unmount is never made;
>   - the stage: `data-state={pdfState}` and `aria-busy={pdfState === 'loading'}`. Nothing changes on screen.
> - Checks: Prettier ok. `npm run check` (svelte-check): **0 errors, 0 warnings**, after `dev.py api sync`.
> - **⚠️ Fuori pista:** the first `svelte-check` found 2 errors in D's PAC code (`model.ts:352`, `LedgerTable.svelte:92`). The cause was the worktree's stale generated client (10-08 19:51), from before D's schema change (`rounding_delta` ExactNumber).
>   - `dev.py api sync` regenerated it (ignored files only, `git status` unchanged), and the errors went away.
>   - The gallery's test server rebuilds the frontend with `api sync` (`cmd_fe_build`), so the runs use the up-to-date client.
>
> **19.2 ⏳ Delegation (08:25)**
> - Test-author C (PAC, batch 5) no longer exists, so there are two new test-authors with separate files:
>   - **ta-pac-usd** (`448b1e80…`): `galleryPac.ts` only. External account back to USD, then the EUR-only assertions re-checked. It runs the 2 PAC tests on lane 6158 first, with 2 workers and a fresh populate.
>   - **ta-files-family** (`7e188ef4…`):
>     - the gallery `Files` describe (5 tests; the image preview test becomes 4, one per type);
>     - `pdfPreviewState.test.ts`, plus a PDF block in `FilePreviewModal.test.ts` (EmbedPDF mocked);
>     - in `files.spec.ts` the PDF test waits for `data-state=ready`;
>     - the runner catalogue if needed.
>     - It writes code and runs vitest without the lane; the lane comes on «LANE FREE» after the PAC.
>   - Preview E2E to run: `front-utility files` and `component-unit`, `front-broker detail`, `front-transaction tx-import-report-set` and `tx-import-resolution`.
>
> **19.3 ✅ PAC back to USD (ta-pac-usd, 08:47)**
> - Only `galleryPac.ts` (+27/−14):
>   - `PAC_SCENARIO.externalAccount` back to USD, same name and amounts; comment and docblock without the bug;
>   - the Liquidity frame asserts the external account in USD;
>   - `framePacPlan` asserts what the draft guarantees: ≥1 cash step, exactly one USD transfer into Interactive Brokers, ≥1 numbered exchange (all on IB, either direction), cash before exchanges, IB orders.
> - Runs: `b6_pac_1` (fresh populate) **4/4** in 3.4 min; `b6_pac_2` (`--no-populate`) **4/4** in 2.7 min, same plan. Lane free.
> - 📐: `pac-result-plan` block 773 → **1024** (screen 1040); `pac-result` screen 957–981; liquidity and proof unchanged.
> - **Engine finding** (reported to the coordinator for D, 08:50): the plan **exploits rounding**. Checked by eye on `pac-result-plan` desktop en/light:
>   - step 4 transfers 0.01 USD Northwind→DEGIRO, auto-converted to 0.01 EUR (exact 0.00893);
>   - step 6 converts 0.14 USD → «about 0.13 EUR» on IB (exact 0.12507), after step 5 EUR→USD on the same broker, to pay exactly the 20th unit of the bond;
>   - step 5 credits «about 1,233.42 USD» where the exact amount is 1,233.4109;
>   - «Not invested» shows Rounding ≈ −0.02 EUR.
>   - Probable cause: credits posted half-up at the minor unit (D's commit) + spread 0% + no cost per step.
>   - Not worked around and not asserted (it would be red today). Gallery options sent to the coordinator; M recommends (a), keep it until D fixes.
> - **Shared surface:** the Files author added a line to `scripts/test_runner/_frontend_utility.py:100` (`pdfPreviewState.test.ts` in `front_utility_unit`). Writer confirmation requested from the coordinator.
> - **LANE FREE** given to ta-files-family at 08:48.
>
> **19.4 ✅ The gallery Files family (ta-files-family, 10:15)**
> - `gallery.spec.ts`: only the `Files` describe plus one import.
>   - **8 tests**: the image preview test becomes 4, one per type.
>   - One page load per test; language and theme switched in place; files found by exact name (`men_01.png`, `ebook.pdf`, `preview_markdown_sample.md`, `preview_notes_sample.txt`, `schwab-export.csv`) through the API and opened from their row.
>   - No `networkidle`, sleep or silent skip.
>   - Names, categories and the desktop tall-screen line unchanged.
> - `fixtures/galleryFiles.ts` (new, 336 lines), readiness:
>   - tables: files loaded, uploaders resolved, images on screen loaded (a broken image fails with its URL);
>   - image preview: picture decoded;
>   - PDF: `data-state=ready`, tiles loaded and still;
>   - markdown: heading, KaTeX and fonts;
>   - text: lines shown;
>   - spreadsheet: canvas painted and still.
> - `files.spec.ts`: `pdf preview hides comment button` waits for `data-state="ready"`.
> - Unit tests: `pdfPreviewState.test.ts` (19) and 7 PDF tests with a fake EmbedPDF in `FilePreviewModal.test.ts`, 45/45.
> - Runner: one line in `scripts/test_runner/_frontend_utility.py:100` (core-unit), confirmation requested from the coordinator.
> - **Runs** (lane 6158, 2 workers):
>   - gallery `b6_files_5` **16/16 in 1.8 min** (fresh populate, both viewports). The old image preview test alone took 3.5 min. The PDF test takes ~50 s of its 180 s; the others 4–12 s of 90 s.
>   - E2E: `front-utility files` 22/22, `front-broker detail` 33/33, `tx-import-report-set` 32 passed (32 skipped by its own viewport split), `tx-import-resolution` 12/12.
>   - Units: core-unit 3471/3471, component-unit 2906/2906.
> - Images checked by M: `preview-modal-pdf` desktop (ebook.pdf rendered, no page pill), `preview-modal-image` mobile (men_01.png loaded).
> - **Findings for the coordinator:**
>   1. **Product defect:** the static grid's size units (B/KB → o/Ko) don't follow a language switch; FileGrid formats at mount. The test reopens the grid, so the shots are correct.
>   2. EmbedPDF's page pill «‹ 1 4 ›» was in every PDF shot; now the test waits for it to disappear (~4.5 s per combination, state-based).
>   3. **The PDF preview reaches the internet** (checked in the bundle): `cdn.jsdelivr.net/npm/@embedpdf/pdfium@2.14.3/dist/pdfium.wasm` (the WASM engine, yet `node_modules/@embedpdf/pdfium/dist/pdfium.wasm` is local, 4.4 MB), `fonts.googleapis.com` (Open Sans for the UI, signature fonts), `cdn.jsdelivr.net/npm/@embedpdf/default-stamps/…`. For a self-hosted app, privacy and offline. The snippet accepts a `wasmUrl` option.
>   4. The Files describe uses its own shot without the global `networkidle` + 200 ms; the other describes are unchanged.
>
> **Final gates (10:20):**
> - Prettier on the 8 files: clean;
> - `tsc -p tsconfig.e2e.json`: only the 2 known errors;
> - `svelte-check`: 0 errors and 0 warnings;
> - vitest: 45/45;
> - ruff on the runner file: ok;
> - `git diff --check` ok;
> - ports free.
>
> **Committed** (2026-10-09): `32d62640f` (feat files, PDF state), `2e8d6a551` (test gallery Files + PAC USD).
> - **Coordinator decisions on the checkpoint** (09:40):
>   - the line in `_frontend_utility.py` is confirmed, with M as its writer;
>   - PAC rounding dust: option (a), images kept, the defect passed to D, and the CI regenerates after the fix;
>   - PDF assets from third parties, FileGrid units and the global shot: to the developer.

## Batch 7 — PDF preview without third-party requests (base `2e8d6a551`)

### 20. ✅ PDF engine and assets served locally, the remote as fallback; viewer only; protected PDFs — 2026-10-09

> **Note implementazione**:
>
> **Developer** (via the coordinator, 09:53), verbatim: «si facciamolo subito, ma come fallback lasciamo lo scaricamento remoto, per resilienza».
>
> **Coordinator brief:**
> - local first: the WASM engine of `@embedpdf/pdfium` (2.14.3, locked) served by us (`?url`, then `wasmUrl`); the same for fonts and stamps if the library accepts a configurable origin;
> - the remote only as a fallback;
> - font licences written into the plan;
> - tests red first: an E2E with no request to `cdn.jsdelivr.net` / `fonts.googleapis.com` / `fonts.gstatic.com`, watched with `page.on('request')`; a test of the fallback; the gallery Files suite stays green and works offline;
> - the Docker weight written into the plan;
> - CHANGELOG by the coordinator (Fixed? check v1.1.0);
> - M is the only writer of `FilePreviewModal.svelte`;
> - proof: only the tests touched plus the preview E2E.
>
> **Facts (read-only analysis, 09:55–10:20):**
> - **v1.1.0** (`837a8f2c7`, 2026-09-07) already had the EmbedPDF PDF preview (`@embedpdf/snippet` ^2.14.3; preview since `5b887dd3a` of 2026-06-04), so the CHANGELOG entry goes under **Fixed**.
> - Options of the snippet (`snippet/dist/components/app.d.ts`):
>   - `wasmUrl`;
>   - `fonts.ui` / `fonts.signature` (`null` = no request; documented «for GDPR-sensitive, airgapped, or self-hosted deployments»);
>   - `fontFallback` (PDF content fonts, jsDelivr by default);
>   - `stamp` (`manifests`, `defaultLibrary`).
> - Third-party requests today, from the bundle and `node_modules/@embedpdf/*`:
>   1. **WASM engine** `cdn.jsdelivr.net/npm/@embedpdf/pdfium@2.14.3/dist/pdfium.wasm`, on every viewer start. A local copy is in `node_modules/@embedpdf/pdfium/dist/pdfium.wasm` (**4.42 MB**, exported as `./pdfium.wasm`). Licences MIT (EmbedPDF) + BSD-3 (PDFium, `LICENSE.pdfium`).
>   2. **UI font** Open Sans from `fonts.googleapis.com` (+ `fonts.gstatic.com`), on every start. Not in `node_modules`.
>   3. **Default stamps manifest** `cdn.jsdelivr.net/npm/@embedpdf/default-stamps/{locale}/manifest.json`, fetched by `StampPlugin.initialize()` on **every start**, even though our preview can't place stamps (the tool has category `annotation`, disabled). The package isn't installed.
>   4. **Signature fonts** (Caveat, Dancing Script, Great Vibes, Pacifico), Google Fonts, on the first open of «Create signature».
>   5. **PDF content fallback fonts**, jsDelivr, only for PDFs with non-embedded fonts of that script. Local Noto (OFL-1.1) in `node_modules/@embedpdf/fonts-*`: latin 11.0 MB (18 variants; Regular/Italic/Bold/BoldItalic ≈ 2.4 MB), arabic 0.3, hebrew 0.1, jp 30, kr 31, sc 40, tc 38 MB.
> - **UX finding:** the «Insert» mode (`mode:insert`, `insert:add-signature`, `insert:add-rubber-stamp`, categories `insert*`) isn't in `PDF_PREVIEW_DISABLED` (`annotation`, `annotation-comment`, `panel-comment`), so it can be reached in a preview that can't save. That's the same reason comments were disabled.
> - Serving: no CSP; `sw.js` handles navigations only (no asset caching); `/_app` via `ImmutableStaticFiles`, `.wasm` → `application/wasm` (Python mimetypes), with `Cache-Control: immutable`.
> - Licences: `THIRD_PARTY_LICENSES.md` exists for the attribution clause and goes into the image (`Dockerfile:127`); today it doesn't name EmbedPDF or PDFium.
>
> **Coordinator decisions** (10:07), consistent with the developer's:
> 1. WASM engine local (`?url`), CDN fallback after a failed `HEAD`. **M writes `THIRD_PARTY_LICENSES.md`** (EmbedPDF MIT, PDFium BSD-3).
> 2. `fonts.ui = {family: <app font>, stylesheetUrl: null}`.
> 3. `stamp: {manifests: []}`.
> 4. `fonts.signature: null`. The «Insert» mode goes to the developer: **don't touch it**.
> 5. Content fallback fonts **(b)**: latin with 4 variants, plus Arabic and Hebrew local; CJK remote.
> - Tests as proposed. CHANGELOG «Fixed» by the coordinator.
>
> **Docker weight** (full and light images, both copy `frontend/build`): engine 4.42 MB + latin 2.43 MB (4 × ~0.61 MB) + Arabic and Hebrew ≈ 0.39 MB (sizes in `node_modules`), so **≈ +7.2 MB**, uncompressed.
>
> **20.1 ✅ Licences (10:30):** new section `## 📄 PDF preview` in `THIRD_PARTY_LICENSES.md`, in the image via `Dockerfile:127`.
> - Table: EmbedPDF 2.14.3 MIT, PDFium BSD-3, Noto Sans OFL-1.1, Noto Naskh Arabic and Noto Sans Hebrew Apache-2.0.
> - PDFium's BSD notice in short form, as for the file's other BSD notices; the full OFL-1.1 text in `<details>`.
> - **⚠️ Fuori pista:** the **real** copyrights come from the `name` table of the shipped files (nameID 0/13/14, read with a Python parser):
>   - NotoSans-Regular: «Copyright 2022 The Noto Project Authors», OFL-1.1;
>   - NotoNaskhArabic-Regular: «Copyright 2014 Google Inc.», **Apache-2.0**;
>   - NotoSansHebrew-Regular: «Copyright 2012 Google Inc.», **Apache-2.0**.
>   - The `@embedpdf/fonts-*` packages declare OFL-1.1 and reuse the Noto Sans LICENSE: the attribution follows the files, and says so. Both licences are AGPL-3.0 compatible.
> - **Code prepared outside the repo:** `/tmp/librefolio-r2-m-b7/pdfViewerAssets.ts`, to apply after the red evidence.
>   - Engine via `@embedpdf/pdfium/pdfium.wasm?url`; fonts via relative `?url` paths into `node_modules` (the packages export only `.`).
>   - `FontCharset` from `@embedpdf/models`; the same charset map as the library's default (`engines/dist/lib/pdfium/index.js:32-45`).
>   - CJK on the CDN pinned to `@1.0.0`, guarded by a test (the library asks for `@latest`).
>   - One `HEAD` decides local vs CDN for engine and fonts together, with absolute URLs because the viewer's worker starts from a `Blob`.
>   - The packages imported (`@embedpdf/pdfium`, `models`, `fonts-*`) are transitive dependencies of the snippet, pinned by the lock. Declaring them in `package.json` would need an `npm install` (maintenance step, to propose).
>
> **Developer on «Insert»** (via the coordinator, 10:33), verbatim: «Sì, disattiva Insert (Consigliato)».
> - Add `'insert'` to `PDF_PREVIEW_DISABLED`, with a test that the preview stays read-only.
> - The viewer hides an item when **any** of its categories is disabled (`computeHiddenItems`, `plugin-ui/dist/index.js:375-383`: `categories.some(cat => disabledSet.has(cat))`). So `'insert'` alone covers `mode:insert` (`mode`, `mode-insert`, `insert`), `insert:add-signature`, `insert:add-rubber-stamp` and the Rubber Stamp / Signature tools.
> - Order: the Insert test is written and run **red** on the build with the assets already local, then `'insert'` goes in and it turns green.
>
> **20.2 ✅ RED evidence (test-author, phase 1, 10:45):**
> - `files.spec.ts` gains `pdf preview requests nothing from third-party hosts`: requests at context level, observation only, with a positive control (a `.wasm` request was seen, so the worker is being listened to). It deletes its own upload.
> - `guardGalleryOffline` aborts and records (`thirdParty` list) the exact hosts `cdn.jsdelivr.net`, `fonts.googleapis.com` and `fonts.gstatic.com`.
> - Worker requests: a module worker from a blob URL shows up in `context.on('request')`, and `page.route`/`context.route` intercept it (Playwright 1.61, checked in isolation).
> - **Red**, `b7_red_3` (front-utility files): the new test red with 5 URLs, the other 22 green.
>   1. `pdfium.wasm` (from the **engine worker**, attributed by Resource Timing);
>   2. Open Sans css (`fonts.googleapis.com`);
>   3. its woff2 (`fonts.gstatic.com`);
>   4. `default-stamps/en/manifest.json`;
>   5. `default-stamps/en/stamps.pdf`.
> - **Red**, `b7_red_4` (gallery `file preview modal (pdf)`, fresh populate): red on both viewports; the guard aborted the worker's `pdfium.wasm`, so the stage stayed at `loading`.
> - **Finding:** jsDelivr already made the PDF E2E unstable. `b7_diag_5`: `pdfium.wasm` was still pending after 20 s while the small files took 1–6 s; the viewer doesn't retry, so it sat at `loading`. The PDF tests ranged from 4.4 s to over 27 s. Locally `ERR_NETWORK_CHANGED` also appeared (environmental).
> - Grep: the hosts appear only in the two EmbedPDF chunks. Other icons use different hosts (brokers' sites, `www.google.com/s2/favicons` → `t*.gstatic.com`, not `fonts.gstatic.com`), so the guard matches exact host names.
>
> **20.3 ✅ Product: local assets (M, 10:55)**
> - `frontend/src/lib/utils/files/pdfViewerAssets.ts` (new, from `/tmp/librefolio-r2-m-b7`).
> - `FilePreviewModal.svelte`:
>   - snippet and assets module in parallel (`Promise.all` of the two lazy imports);
>   - `pdfViewerAssets(document.baseURI)` (one `HEAD`), then `if (disposed) return`;
>   - `init({...assets, ...pdfViewerOfflineOptions(getComputedStyle(host).fontFamily)})`.
> - `'insert'` **not yet**: the Insert test runs red first.
> - Checks: Prettier ok; `svelte-check` **0 errors and 0 warnings** (the `?url` imports and the FontCharset keys type-check); vitest `pdfPreviewState` + `FilePreviewModal` **45/45** (in jsdom the `HEAD` fails, so the defaults apply).
>
> **20.4 ✅ Phase 2 tests, before «Insert» (test-author, 11:30)**
> - `front-utility files` (`b7_files_1`): **24 passed, 1 failed, as intended.**
>   - `pdf preview requests nothing from third-party hosts` **green** (6.6 s): only `HEAD` and `GET` of `/_app/immutable/assets/pdfium.C65hdIN1.wasm`.
>   - `pdf preview falls back to the CDN when the local engine is unreachable` **green** (5.8 s): the local engine aborted, the CDN URL (version read from the installed package) answered with the local file plus a CORS header; asserted the `HEAD`, the CDN route hit, and no unanswered request to the three hosts.
>   - `pdf preview offers no Insert mode` **RED**: «the modes menu offers Insert». Today the menu offers Insert, Form and Redact; Annotate and Shapes are already hidden.
> - Unit tests:
>   - new `pdfViewerAssets.test.ts`, 24 tests; the expected map comes from the library's `createCdnFontConfig(CDN_FONTS_VERSION)`, with version pins and files checked on disk;
>   - `FilePreviewModal.test.ts`, +2 (assets mocked, offline options real).
>   - core-unit 3495, component-unit 2908; svelte-check 0.
> - Runner: one more line, `scripts/test_runner/_frontend_utility.py:101` (`pdfViewerAssets.test.ts`), authorised by M as writer of the file.
>
> **20.5 ✅ «Insert» disabled (M, 11:32):** `PDF_PREVIEW_DISABLED = ['annotation', 'annotation-comment', 'panel-comment', 'insert']` (`FilePreviewModal.svelte:57`), with an updated comment. «INSERT IN» sent to the test-author for the green runs.
> - **Question to the developer** (via the coordinator): disable **Form** and **Redact** too, which can't be saved from the preview either? Untouched until a yes; the viewer's «•••» menu might offer an export, to check if asked.
>
> **Developer on Form, Redact and «•••»** (via the coordinator, 11:32), verbatim: «disattivale, deve essere solo un visualizzatore, se nei 3 puntini ci fosse l'export, disattivalo o nascondilo».
> - Coordinator brief: Form and Redact off, test red first; in the menu, export, print, download or save hidden, with a test; anything else that modifies the document reported before touching it.
>
> **20.6 Analysis of the viewer's menus** (bundle `@embedpdf/snippet`, 11:40):
> - «•••» next to «View» is `tabs:overflow-menu` (the modes): `mode:insert` (already off), `mode:form` (`mode`, `mode-form`, `form`), `mode:redact` (`mode`, `mode-redact`, `redaction`).
>   - The `form` category also covers `form:add-*`, `form:toggle-fill-mode` and `form:overflow-tools`.
>   - `redaction` covers `redaction:*`, `panel:toggle-redaction` and `annotation:apply-redaction`.
> - «≡» is `document-menu-button` → `document-menu`: `document:open`, `document:close`, `document:print`, `document:protect`, `document:capture`, `document:export`, `document:fullscreen`. Each has its own `document-*` category.
> - **Decided:** `form`, `redaction`, `document-export` and `document-print` off, red first.
> - **To the developer:** Protect (modifies the document: password), Capture (exports an area as an image), Open and Close (load another PDF from disk, or empty the viewer). M recommends switching them off, keeping Fullscreen; Undo/Redo and copying text stay.
>
> **Developer on the document menu** (via the coordinator, 11:38), verbatim: «togli tutto eccetto fullscreen e copia testo, che senso ha tenere una cosa che non funziona? tienila solo se non riesci a toglierla».
>
> **20.7 Viewer-only: what goes, what stays, what is outside the menus (M, 11:50)**
> - **Off:**
>   - the modes Insert, Form and Redact;
>   - the document menu's Open, Close, Print, Protect, Capture and Export;
>   - Undo/Redo;
>   - `capture:screenshot` (keyboard-only, Ctrl/Meta+Shift+S);
>   - `redaction:redact-text` in the text-selection menu (`add-link` and the markup tools there are already `annotation`).
>   - Categories to add: `form`, `redaction`, `document-open`, `document-close`, `document-print`, `document-protect`, `document-capture`, `document-export`, `capture`, `history`.
> - **Stay:**
>   - `document:fullscreen` (in ≡ and in page settings) and the ≡ button `document:menu`;
>   - `selection:copy` and `selection:copy-to-clipboard`;
>   - zoom, search, thumbnails, outline, spread, scroll, rotate and pages: the viewer itself.
>   - There is no attachments tab in the sidebar: only thumbnails and outline.
> - **Every entry can be removed with categories, shortcuts included:**
>   - the viewer's keyboard handler sits on `document` and runs a shortcut only if `!resolve(id).disabled`;
>   - `resolve()` ORs the category block with the dynamic `disabled`;
>   - `computeHiddenItems` hides the UI items, and the menu dividers have `visibilityDependsOn`, so they disappear with their items.
> - Undo/Redo appear only in the annotate, shapes, form and insert toolbars, already hidden. Before this change they were reachable only through Ctrl/Meta+Z and Ctrl+Y.
> - **No other way to open another document:**
>   - no drag-and-drop on the viewer (only the signature upload, which is under Insert);
>   - the empty state's «Open» button appears only after Close, which is now off;
>   - the tab bar with «+» appears only with 2+ documents.
> - **For the RED test, `resolve().disabled` is dynamic** (undo/redo when there is no history; print/copy from the PDF's permissions). The test reads the category block from the registry instead: `resolve(id).categories ∩ getDisabledCategories()`.
> - **Outside the menus (reported to the coordinator before touching; decision pending):**
>   1. In View mode the viewer applies `annotations.locked` from the configuration, default `{type: none}`. So annotations already in the PDF (and form widgets) remain selectable, movable and resizable, in memory; the `annotation` category does not block this interaction (`isAnnotationInteractive` looks only at the lock).
>      - Fix: one line, `annotations: {locked: {type: 'all'}}`. But according to the library's types, «locked annotations let clicks pass through to the layer below (e.g. form-filling)»: to observe on a fixture.
>   2. `unlock-owner-overlay`: shows on encrypted PDFs with owner restrictions. It offers «View permissions» plus the owner password field (`unlockOwnerPermissions`, in memory). It has no category; it can be removed with `disableOverlay` when the document opens.
>   - Both need new PDF fixtures: annotation plus form, and encrypted. The venv has no PDF library (`pypdf`, `pikepdf`, `reportlab`, `fitz` and `pdfplumber` all absent).
>
> **20.8 ✅ RED: viewer only (test-author, 11:58)**, `runs/b7_viewer_red_2.log`, `front-utility files`: 24 green, the 3 new ones red for the expected reasons.
> - **(a) `pdf preview offers no editing mode`**, 12.9 s.
>   - What it checks: `data-epdf-hid` on the viewer's root must contain the Insert, Form and Redact tabs and menu entries, plus signature and rubber stamp. The tabs, the mode dropdown and «•••» must be hidden.
>   - Red: «the viewer still offers `form-mode`, `mode:form`, `redact-mode`, `mode:redact`».
> - **(b) `pdf preview document menu offers only fullscreen`**, 11.4 s.
>   - What it checks: after opening ≡, the visible entries must be exactly `['document:fullscreen']`, so a new entry from a future viewer version would also turn it red.
>   - Red: the visible entries are open, close, print, protect, capture, export and fullscreen.
> - **(c) `pdf preview blocks every editing and export command`**, 7.0 s.
>   - What it checks: `embedpdf-container.registry`, then `resolve(id).categories ∩ getDisabledCategories()`.
>   - Red: 12 commands «available» instead of «blocked»; `mode:insert` already blocked. The 4 kept ones are available.
>   - This test also pins the shortcuts: Ctrl/⌘+O, W, P, Shift+S, Z, Ctrl+Y and ⌘+Shift+Z.
>
> **20.9 ✅ Product: viewer only (M, 12:02)**
> - `PDF_PREVIEW_DISABLED` += `form`, `redaction`, `history`, `document-open|close|print|protect|capture|export`, `capture` (`FilePreviewModal.svelte:60`), with a docblock rewritten as «viewer only».
> - Never `document`: it would block `document:menu` and `document:fullscreen`. Never `tools`: pan and pointer carry it.
> - The schema hides on its own the View tab (`visibilityDependsOn` on the other modes), the mode dropdown (on `mode:*`) and «•••» (on its menu).
> - Prettier: `printWidth` 300, so the array stays on one line.
> - Checked: the keyboard listener on `document` goes away when the preview closes. `disconnectedCallback` of `embedpdf-container` runs `render(null, root)`, and the modal empties the host.
> - **Finding (not fixed, backlog):** while the PDF preview is open, Ctrl/⌘+C on text selected *outside* the PDF (for example the modal's title) is caught by the viewer. It calls `preventDefault` and copies its own empty selection.
> - «VIEWER IN» sent to the test-author for the green runs.
>
> **Developer on annotations and protected PDFs** (via the coordinator, 11:54), verbatim: «riguardo le annotazioni siamo al limite del caso limite, basta, tanto non si può salvare. riguardo i documenti protetti permettiamo, giusto nella sessione, di mettere la pw per visualizzarlo, se serve, dopo averlo "sbloccato" diventa un normale pdf».
> - Annotations: untouched (no `locked`, no fixture).
> - The «Document protected» overlay stays. The password applies only to the open preview: not saved, not kept after closing. After unlocking, the same reduced entries.
> - If the prompt does not appear, or the overlay does not work with the batch 7 local files, report before changing anything.
>
> **20.10 Protected PDFs: verification on the 2.14.3 bundle (M, 12:05)**
> - **Opening password:** the prompt exists.
>   - It is the viewer's own document error view (`zC`): error `PdfErrorCode.Password` → password field → `retryDocument(id, {password})`.
>   - It has no category, so our categories do not hide it.
>   - Our stage replaces the viewer (iframe fallback) only on `pdfError`, i.e. an exception in import/init; a load error leaves the viewer on screen.
>   - Same engine, local or CDN (pdfium 2.14.3).
> - **`unlock-owner-overlay`:** works in the same way. «View permissions» → `view-permissions-modal` (no category) → `unlockOwnerPermissions` (a capability, not a command). The categories are global, so after unlocking the entries stay reduced.
> - **The password never leaves and never stays:**
>   - `openDocumentUrl` re-fetches the URL with `fetcher(url, requestOptions)`; the password goes only to `FPDF_LoadMemDocument` in the worker.
>   - The bundle has no `localStorage`, `sessionStorage` or IndexedDB.
>   - The password sits in the document manager's `loadOptions` (memory).
>   - On unmount the engine hook runs `closeAllDocuments()`, then `destroy()`, then `worker.terminate()`.
>   - Our code never sees the password.
> - **A. Defect (batch 6, M):** `pdfPreviewState` treats `failed` as final («error … whatever came before»). After a successful unlock `onDocumentOpened` arrives, but `data-state` stays `error` (and `aria-busy` false) while the document is shown. Proposed fix: `onDocumentOpened` resets `failed`, with a red-first unit test and no fixture. **Asked the coordinator before changing anything.**
> - **B. Residual «Open» path:**
>   - after a non-password load error, the viewer's error card offers «Close» (`closeDocument()`, a capability rather than the command, so not blocked by `document-close`);
>   - the empty state then offers «Open file» (`openFileDialog()`), which views a PDF from the user's own disk, locally only.
>   - Categories cannot remove it. Proposal: leave it, record it in the checkpoint and in the backlog (removing it would mean our own error UI on non-password errors). **Asked the coordinator.**
> - **Runtime probe:** two encrypted PDFs, made by hand outside the repo (`release-pipeline/scripts/b7_make_encrypted_pdfs.py`, V2/R3 RC4-128, standard library only, self-checked): `pw_open.pdf` (opening password) and `pw_owner.pdf` (owner restrictions, P=-3904). They go to the test-author for a temporary probe (TEMP test, removed afterwards) once the lane is free.
>
> **Coordinator on A and B** (12:10):
> - A: **yes, in batch 7**, unit test red first.
> - B: goes to the developer, untouched until then. If the answer is «remove it», our error message needs a new i18n key, and the catalogues are L's: the coordinator and L coordinate it.
>
> **20.11 ✅ RED: defect A and the runtime probe (test-author, 12:30)**
> - **RED unit test**, `FilePreviewModal.test.ts`, `is ready once a protected PDF opens after its password was asked` (`runs/b8_unit_red_1.log`, 1 failed / 30 passed). The fake viewer sends error(Password), then opened, then ready tiles. Today:
>   - at opened: `data-state=error` (expected `loading`) and `aria-busy=false` (expected `true`);
>   - after the tiles: still `error`.
>   - Guards, green: «error alone stays error» and «error → error (a wrong password) stays error».
> - **TEMP probe** (`files.spec.ts`, a marked block of +319 lines; `runs/b8_temp_1|2.log`, `b8_temp_p1|p2|p3.json`, `b8_p*.png`; uploads deleted in `finally`):
>   - **P1 `pw_open.pdf`:**
>     - prompt visible, viewer in error with code 4 (Password);
>     - wrong password: the «incorrect» warning;
>     - right password: page drawn, registry `loaded`, but `data-state` **`error`**. Defect A confirmed at runtime.
>     - Across 216 requests no password, in the URL, body or headers. 3 plain GETs of the file. Zero third parties.
>     - Nothing in `localStorage`, `sessionStorage`, cookies or IndexedDB. Cache Storage holds only `offline-fallback`, from the app's own `sw.js`.
>     - `page.workers()` 0 → 3 → 0 on close.
>   - **P2 `pw_owner.pdf`:**
>     - opens without a prompt and reaches `ready`;
>     - overlay `[data-overlay-id="unlock-owner-overlay"]` visible (lock, ×, «View permissions»);
>     - before the unlock, `selection:copy` is disabled by the PDF's permissions;
>     - after the unlock: owner unlocked, all permissions, copy enabled, **13 commands still blocked by category**, `ready`.
>     - The owner password appears in none of the 205 requests.
>   - **P3 (test-author's addition):** «Cancel» on the prompt closes the document. The viewer shows its empty state «No Documents Open» with «Open Document», which opens the **native file chooser** (`openFileDialog()` called directly; `resolve('document:open')` throws without a document). **Same mechanism as B, but reachable with one click on any protected PDF.** Reported to the coordinator as an extension of B; no test until the decision.
>   - Minor notes (backlog):
>     1. the overlay's text points to «Security in the document menu», now off;
>     2. after the unlock, the permissions dialog says «full access» and ticks Print, Modify and Annotate, which stay off;
>     3. the dialog covers the whole page;
>     4. while the prompt is up `data-state=error`: telling «waiting for a password» from «broken PDF» would need a fourth state (an interface decision).
>
> **20.12 ✅ Fix A (M, 12:35):**
> - `FilePreviewModal.svelte`: `documents.onDocumentOpened(() => report({opened: true, failed: false}))`, plus one line of comment.
> - `pdfPreviewState.ts`: docs only (the `failed` field and the `error` bullet: «while the latest attempt to open has failed»).
> - Prettier OK.
> - «STATE IN» sent: the unit test GREEN, TEMP P1 again, TEMP removed (empty diff against the saved copy), final runs.
> - Coordinator: B updated with P3 and a question with 3 options for the developer (our message / close the preview / leave it).
>
> **20.13 ✅ Final green runs and gates (test-author + M, 12:31)**
> - Unit, after fix A: `FilePreviewModal.test.ts` 31/31; with `pdfPreviewState.test.ts`, 50/50 (`b8_unit_green_1|2.log`).
> - TEMP P1 after the fix (`b8_temp_3.log`, `b8_temp_p1.json`): `data-state=ready` and `aria-busy=false` after the right password. Privacy checks unchanged:
>   - 287 requests, no password, no request body;
>   - 3 plain GETs of the file;
>   - zero third parties;
>   - no storage;
>   - workers 0 → 3 → 0.
> - **TEMP removed:** `files.spec.ts` is byte-identical to the saved copy (sha256 `78ae7335…2501942`, 848 lines, no `TEMP`). No test for P3 (B pending).
> - Probe uploads deleted: checked in `finally` and on disk (`/tmp/librefolio-r2-m/custom-uploads`: no `temp-pw-*`, no 924/927-byte file; the only PDF is the seeded `ebook.pdf`).
> - **Final runs:**
>   - `front-utility files` 27/27 (`b8_final_files.log`);
>   - core-unit 120 files / 3495;
>   - component-unit 111 / 2911;
>   - svelte-check 0/0;
>   - Prettier clean;
>   - `tsc -p tsconfig.e2e.json`: only the 2 known errors.
> - The Files gallery is **not re-run after fix A**: on a PDF that opens, `failed` is already false, so `report({opened: true, failed: false})` is identical; last gallery 16/16 after «VIEWER IN» (`b7_viewer_gallery.log`).
> - **M's gates:** `git diff --check` clean; 6158 and 6168 free; load at 12:31 = 26.2 / 20.8 / 16.8 (train gates and other lanes at the same time).
> - **Docs:** no page describes the viewer's internal functions (the gallery captions are generic; `user/files/index.md` says only «Preview»), so no text became false. A line on «read-only viewer, protected PDFs with the password kept in the browser» is proposed to the coordinator, not written.
> - **Transitive dependencies imported directly** (declared: only `@embedpdf/snippet`):
>   - product: `@embedpdf/models` (FontCharset), `@embedpdf/pdfium` (wasm `?url`), `@embedpdf/fonts-{latin,arabic,hebrew}` (relative `?url`);
>   - tests: `@embedpdf/engines/pdfium`, `@embedpdf/models`.
>   - Versions pinned by the lock; `pdfViewerAssets.test.ts` checks pins and files on disk. Proposal: declare them in `package.json`, a maintenance step for the developer.
> - **Open after the checkpoint:** B + P3 (the viewer's empty state after a load error or «Cancel» on the password → «Open Document»), a developer decision with 3 options. If «our message», the i18n key is coordinated by the coordinator with L.
>
> **Developer on B and P3** (via the coordinator, 12:53), verbatim:
> - on B, before knowing about P3: «lasciamolo ora e per sempre, mi pare un caso troppo limite, apuntiamocelo per evitare di tornarci in futuro, direttametne nel codice»;
> - on P3: «Chiudi l'anteprima quando il visore resta vuoto».
>
> Coordinator's brief:
> - the cure closes the preview when the viewer is left without a document (after «Cancel» on the password and «Close» on the error card), closing both P3 and B;
> - red first; no new texts, and if a key is needed, stop (the catalogues are L's);
> - never close when the preview itself replaces the document (fallback, file change);
> - a note in the code, as the developer asked;
> - gates: `front-utility files`, core-unit, component-unit, the Files gallery, svelte-check, Prettier.
>
> **20.14 Analysis of the cure (M, 13:00)**
> - Both «Cancel» on the password prompt (`passwordPrompt.cancel`) and «Close» on the error card (`documentError.close`) call `closeDocument(id)`:
>   - on a non-loaded document it is `dispatchCoreAction(CLOSE_DOCUMENT)` directly;
>   - then the hook `onDocumentClosed`, then `documentClosed$.emit(id)` (`EventHook<string>`, replayed to late listeners).
> - `dispatchToCore` runs the reducer **before** the listeners (`onAction`), so on `documentClosed$` `getDocumentCount()` is already 0 for the single document.
> - How the preview closes: `onRequestClose()` (prop; the parent owns `open`).
> - When the preview drops the viewer itself:
>   - teardown (modal closed, file changed): `disposed = true` and listeners unsubscribed **before** `host.innerHTML = ''`;
>   - iframe fallback (`pdfError` in the catch): we will also set `disposed = true` there.
> - No new text.
> - RED brief sent to the test-author:
>   - unit, the cure plus 3 guards (count 1; teardown with a file change and with `open=false`; the fallback);
>   - E2E path B with a broken PDF built in the test (the viewer's «Close» → the modal closes);
>   - TEMP P3 with `pw_open.pdf`, not committed.
>
> **20.15 ✅ RED: an empty viewer (test-author, 13:40)**
> - **Unit** (`runs/b7_empty_unit_red_2.log`, 36 tests: 2 RED, 34 green).
>   - **The fake:** one viewer per `init`, with its own `onDocumentClosed` (replay, dedup, real stop) and `getDocumentCount`. The stage element closes its documents a microtask after it leaves the DOM, as the real unmount does. A breaker stops `init` after 10 starts.
>   - **RED, planned:** `closes the preview when the viewer is left without a document`: `onRequestClose` was called 0 times, expected 1.
>   - **Guards, green:** count 1; file change; `open=false`. The «stops listening» tests now require at least 3 subscriptions.
>   - **RED, unplanned:** the fallback guard (`init` throws) found the viewer **started 11 times**. In the first run the jsdom worker ran out of memory (`b7_empty_unit_red_1.log`).
> - **E2E `pdf preview closes when its viewer is left empty`** (path B; `runs/b7_empty_files_red_1.log`): **RED in 8.2 s**.
>   - Test data: a broken PDF built in the test, `%PDF-1.4` followed by text, 201 bytes, deleted in `finally`. The backend accepts it: blocklist, and libmagic recognises the signature.
>   - Steps: `data-state=error`, then the error card's Close (`div:has(> h3):has(> p) > button`), then `toBeHidden()`. The modal stays open on «No Documents Open / Open Document» (`b7_empty_e2e_red_failed.png`).
> - **TEMP P3** (`files.spec.ts:861–893`, a pure insertion; copy saved at `/tmp/lf_b7_empty_files.spec.ts.before_temp`): «Cancel» on `pw_open.pdf` → the modal stays open with «Open Document» (`b7_empty_temp_p3_before_fix.json`).
> - **Test-author's note on `open=false`:** Svelte 5.48 removes the stage before the effect's cleanup runs. What protects that path is the viewer's asynchronous unmount (`registry.destroy()` awaits `initPromise`). A close made by the user is synchronous. Suggestion: a check on the element's connection.
>
> **20.16 ✅ The cure, and the fallback loop (M, 13:50)**
> - **The cure** (`FilePreviewModal.svelte`): `documents.onDocumentClosed(() => { if (!disposed && host.isConnected && documents.getDocumentCount() === 0) onRequestClose(); })`.
>   - The developer's note sits beside it in the code: «Open Document» opens local PDFs, no category turns it off, so the preview closes; not to be revisited.
>   - `host.isConnected` replaces the planned `disposed = true` in the `catch`: it covers every removal of the stage done by us (closing, the fallback) whatever the viewer's timing.
>   - Changing file is covered by `disposed` plus the unsubscribe that comes before `innerHTML = ''`.
>   - No new text.
> - **⚠️ Off track: the fallback loop.** The `!host` branch cleared `pdfError` whenever it ran. So:
>   - the iframe takes the stage's place (`pdfHost` becomes null), the effect reruns, and `pdfError` is cleared;
>   - the stage comes back and `init` fails again, round after round, with a HEAD and a new iframe every time.
>   - It dates from `5b887dd3a` (2026-06-04, `feat(files): add inline file preview system`), so it was already in v1.1.0. It triggers only if the import or the viewer's start throws.
>   - **Fix:** `if (!sourceUrl) pdfError = null;` (the `!open` effect still clears it when the modal closes). Reported to the coordinator: it is tightly coupled to the fallback guard they asked for.
> - Prettier OK. «EMPTY IN» sent: the GREEN runs plus the gates.
>
> **20.17 ✅ GREEN: empty viewer and fallback, final gates (test-author + M, 13:36)**
> - **Unit** `FilePreviewModal.test.ts` 36/36:
>   - the close test is green;
>   - the fallback guard is green (one start, the iframe stays, 18 ms): the loop fix holds.
>   - **Check of `host.isConnected`:** with the fake set to report its unmount close *synchronously*, inside the DOM removal, all 17 PDF tests still passed (`b7_empty_unit_sync_unmount_experiment.log`). The fake was then restored byte for byte.
> - **E2E** `pdf preview closes when its viewer is left empty`: green, 5.4 s.
> - **TEMP P3:** after «Cancel» the modal and the stage are gone (`b7_empty_temp_p3.json`). TEMP removed: empty diff, sha256 `3c6ae414…593a`, 876 lines, no `TEMP` left.
> - **Gates:**
>   - `front-utility files` 28/28 (`b7_empty_final_files.log`);
>   - core-unit 120 files / 3495;
>   - component-unit 111 / 2916;
>   - the Files gallery: fresh populate, offline guard on, 16/16; the PDF shot takes 51.4 s desktop and 51.2 s mobile, against a 180 s budget (`b7_empty_final_gallery.log`);
>   - svelte-check 0/0, after a type-only cast in the test (`b7_empty_final_check_2.log`);
>   - Prettier clean;
>   - `tsc -p tsconfig.e2e.json`: only the 2 known errors.
> - **M's checks:**
>   - `git diff --check` clean;
>   - 6158 and 6168 free;
>   - `dev_release2` = `1ead733f2` (train 23): from `2e8d6a551` no overlap with the batch 7 paths, only `CHANGELOG.md`, which M does not touch;
>   - load at 13:36: 14.2 / 14.2 / 14.9.
> - **Step 20 closed.** Updated CHECKPOINT READY sent to the coordinator; M FROZEN.

## Batch 8 — English pages that can already be fixed (base `3cceb4f90`, train 24b, M integrated with L and Q)

### 21. ✅ Connection indicator shot, PDF preview line, Docker box in `cli_tools` — 2026-10-09

> **Coordinator's brief** (13:49), on the developer's wish to start the translations as late as possible:
> 1. the shot `security/connection-indicator` in the gallery, then in `user/connection-security.en.md` in place of the placeholder (line 14);
> 2. one line in `user/files/index.en.md`: the PDF preview is read-only; a protected PDF asks for the password, which stays in the browser and is gone when it closes;
> 3. `admin/cli_tools.en.md:8`: the Docker box says «User and database commands work there», but `db upgrade` and `db downgrade` with `exec` do not work (in Docker the server is always running; `:113` already says so). Fix it, with a link. `docker_advanced:207` is already right: do not touch it.
> - English only: no stamp, no translation, the PAC page untouched (it is D's).
> - Gates: `mkdocs build` strict, `check-links` (only the known `#rolling-return` may remain), the gallery only for the new shot, desktop and mobile.
>
> **21.1 ✅ Baseline and analysis (M, 14:00)**
> - HEAD `3cceb4f90` = `dev_release2` (fast-forward after train 24b: `6bd947519`, M's B7 commits `1028a1978` and `908f9bf1d`); worktree clean.
> - Placeholder `connection-security.en.md:14`: `<!-- [Screenshot Placeholder: security/connection-indicator — the sidebar's connection security indicator open on Connection: local network, with its reason and the How to connect securely link] -->`.
> - How to reproduce it (L, `frontend/e2e/layout/connection-security.spec.ts`):
>   - Chromium with `--host-resolver-rules=MAP lf-e2e.lan 127.0.0.1`;
>   - log in through the form under `http://lf-e2e.lan:<port>/`, because cookies are per host;
>   - wait for `data-server-checked`, then `data-level="local"` and `data-reason="lan"`;
>   - open `connection-security-toggle`.
>   - `launchOptions` is worker-scoped: Playwright refuses it inside a describe, so it goes in a `test.use` at the top of the file.
> - `screenshot()` in the gallery: always full screen (no crop; tall shots via galleryTallShots).
> - Gallery pages convention: every new shot gets an entry in `gallery/desktop.en.md` and `mobile.en.md` (as «🗃️ File Menu» did in batch 3). There is no Security section today.
> - `cli_tools`: the database section is `## 🗄️ Maintain the Database` → `### ⬆️ Apply Migrations` (line 93); `:113` describes `db upgrade`/`downgrade` in Docker; `docker_advanced.md#docker-exec` (line 196) and `:207` («Database migrations need no command»).
> - Assignments:
>   - test-author: the gallery test, lane 6158;
>   - docs-writer: the placeholder, the gallery pages, the PDF line and the `cli_tools` box; no lane, only `mkdocs build` and `check-links`.
>
> **21.2 ✅ English docs (docs-writer, 14:15)**
> - `user/connection-security.en.md:14`: the placeholder → the standard block (`max-width: 700px`), `data-category="security" data-name="connection-indicator"`.
>   - Alt text: «The connection security indicator at the bottom of the sidebar, open on Connection: local network: its reason, that anyone on the same network can read the traffic, and the How to connect securely link».
>   - The strings come from `en.json`; the position from `Sidebar.svelte:273`, under Logout and above the version.
> - `gallery/desktop.en.md` and `mobile.en.md`: a new `## 🔒 Security` → `### 🚦 Connection Indicator` after Authentication, with a description, the img, and `---`. Mobile uses `screenshot-container mobile`.
> - `user/files/index.en.md`: a bullet under Preview, in Static resources, the only section that takes PDFs (the BRIM uploader accepts `.csv,.xlsx,.xls`): read-only viewer (read, search, copy; no edit, annotate or print; **Download** to keep the file); a protected PDF asks for its password, which stays in the browser, is never sent or saved, and is gone when the preview closes.
> - `admin/cli_tools.en.md:8`: «User commands, `db current` and `db check` work there; `db upgrade` and `db downgrade` do not, as they need the server stopped ([Apply Migrations](#apply-migrations))…».
>   - Plus `{: #apply-migrations }` on line 93: same value as the generated slug, so it protects the link in the translations (100 of the 102 same-page links already use fixed anchors). Accepted by M.
>   - `:113` and `docker_advanced` untouched. Verified in `dev.py:490-549`: upgrade and downgrade refuse while the server runs; current and check do not.
> - Gates:
>   - `mkdocs build` strict: exit 0, 0 WARNING (`b8_docs_build.log`);
>   - `check-links`: only `#rolling-return`, plus the 3 already on the exception list (`b8_docs_links.log`);
>   - `git diff --check` clean.
> - No timestamp (not a convention); no stamp; the translation debt is left visible (IT/FR/ES gallery pages, the files bullet, cli_tools, connection-security).
> - Note for the checkpoint: if the viewer fails, the fallback iframe (the browser's own PDF viewer) may offer print and download. The line describes the normal viewer.
> - **Follow-up approved by M:** a **Security** bullet in «What You'll See» in `gallery/index.en.md`, the convention for a new section (Onboarding in `3a8e9a05d`), then build and check-links again.
>
> **21.3 ✅ Gallery index (docs-writer, 14:20)**
> - `gallery/index.en.md:25`, «What You'll See»: `- **Security**: Connection security indicator in the sidebar, open on its level and the reason for it` (after Authentication).
> - Build strict: exit 0, 0 WARNING; the bullet is in `gallery/index.html`.
> - `check-links`: only `#rolling-return`, plus the 3 known ones on the exception list.
> - `git diff --check` clean.
> - 6 EN docs files modified. The IT/FR/ES debt is left visible.
>
> **⚠️ Off track: pause and the session error (14:21 → 15:22).** The coordinator asked for a pause at 14:21; M's session went down with an error on that very message, before replying «IN PAUSA». It resumed at 15:22 on the coordinator's signal, with HEAD `3cceb4f90`, 9 files modified, ports 6158 and 6168 free.
>
> **21.4 State on resume (M, 15:25)**
> - Docs: done (21.2, 21.3).
> - The gallery shot: the first test-author (`bc4a6092`) **shows `running` but has given no sign of activity since 14:50** (last edit to `gallery.spec.ts` 14:20:58; failure evidence copied at 14:50), and no lane process is running.
> - **Its runs**, all with `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-m` and port 6158 (`runs/b8_connection_*.meta`):
>   - `red_first` (14:11, desktop only): exit 1;
>   - `b8_connection_1` (14:18): **green on desktop and mobile, 74 s**;
>   - `b8_connection_2` (14:21, load 48): **red on both**: under `http://lf-e2e.lan:6158` the page stays on the splash (snapshot: the LibreFolio logo only), and `login-page` does not appear within 30 s.
> - The spec **changed between the green run and the red one**: a `TEMP-DIAG-B8` block was added; its console output is not in the runner's log.
> - **The test's design** (from the diff):
>   - a top-level `test.use` that maps only `lf-e2e.lan`;
>   - the admin's `login()` on the baseURL, then `keepTempDataHiddenUnder` (new in `galleryReportSets.ts`: the two listings that `hideGalleryTempData` reads in Node, where `lf-e2e.lan` does not resolve, are redirected to the baseURL);
>   - the form login under the LAN name, and a positive check that the offline guard answers a catalogue read from the page;
>   - per language and theme: `/dashboard`, 1Y, `data-server-checked`, then `local`/`lan`, the drawer on mobile, the toggle, the reason, the link with `href` in the UI's language, no cookie warning;
>   - settled waits, `toBeInViewport`, `expectUncovered`, then the screenshot.
> - **Next action:**
>   - STOP sent to the first test-author;
>   - a new test-author takes over: `test-triage` on the red (what keeps the boot on the splash under the LAN name), the fix, `TEMP-DIAG` removed, 2 green runs on both viewports, `view` of the images, Prettier and tsc;
>   - then the CHECKPOINT READY.
>
> **21.5 The first test-author is alive (M, 15:30)**
> - The new test-author (`96a01a8b`) **stopped before any edit or run**, under the concurrency rule.
> - The first test-author (`bc4a6092`) resumed together with M's session:
>   - it changed `gallery.spec.ts` at 15:23:41 (sha256 `5cdfa8b2…`);
>   - it ran `b8_connection_3_diag` (15:23:47–15:25:03, load 30.8 → 18.1): **exit 0 on both viewports in 76 s**, 16 PNGs written.
> - TEMP-DIAG is still in the spec (lines 1632–1667). Its output now reaches the runner's log.
>   - `signed in under LAN` at about 5.3 s on both viewports: run 2's red (the splash, at load 48) does not reproduce at load about 31.
>   - Still pending: 1–3 chunks `http://localhost:6158/_app/immutable/chunks/*.js`, probably abandoned when the page moved to the LAN origin, and two 401s at about 0.6 s and 3.1 s (`auth/me` before each login). To be confirmed.
> - **Decision (M):** the first agent finishes; it has the context and is in the middle of the triage. The second stays idle. The «STOP» sent at 15:25 will reach it only at the end of its turn, so it does not interrupt its work.
> - On the report: check the verdict on run 2's red (not «flaky»), TEMP-DIAG removed, at least 2 clean green runs, the images, the gates.
>
> **21.6 ✅ The connection indicator shot: final report and confirmation (test-author `bc4a6092` + M, 15:35)**
> - **The test**, `gallery.spec.ts` (+154, additions only):
>   - a file-level `test.use` with `--host-resolver-rules=MAP lf-e2e.lan 127.0.0.1` (only that name; the config's `slowMo` kept; `--list` collects all 252 tests with no worker error);
>   - `test.describe('Security')` between Dashboard and Settings. The flow:
>     - the admin's `login()` on the baseURL, then `keepTempDataHiddenUnder`, then the form login under `lf-e2e.lan`;
>     - a positive check that the offline guard answers a catalogue read from the LAN page;
>     - per combination: `/dashboard` 1Y, the language and theme on `<html>`, `data-server-checked`, then `local`/`lan`, the drawer on mobile, the toggle, the reason, `href` in the UI's language, no cookie line;
>     - settled waits (`textStill`, `canvasStill`, images, motion), `toBeInViewport({ratio: 1})`, `expectUncovered`, the screenshot.
> - **The fixture**, `galleryReportSets.ts` (+29): `keepTempDataHiddenUnder`. The guard's routes match paths, not the origin, so they also hold under the LAN name. But `hideGalleryTempData` reads `/brokers` and `/brokers/import/files` in Node, where `lf-e2e.lan` does not resolve. Without the fix: `getaddrinfo ENOTFOUND` (the no-fix run, 14:11).
> - **Runs** (`dev.py mkdocs gallery … -f 'connection indicator on a local network'`, `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-m`, port 6158, 2 workers, fresh populate):
>
> | run | result | elapsed | load at start → end |
> |---|---|---|---|
> | no fix (desktop only) | ✘ ENOTFOUND | 167 s | 14.6 → 23.9 |
> | 1 | ✓ | 74 s | 15.8 → 10.7 |
> | 2 | ✘ both (splash > 30 s) | 203 s | 16.0 → **48.5** |
> | 3 (TEMP-DIAG) | ✓ | 76 s | 30.8 → 18.1 |
> | 4 (final code) | ✓ desktop 37.9 s / mobile 37.6 s | 73 s | 7.4 → 11.6 |
> | **5 (final code, M)** | ✓ desktop 34.9 s / mobile 36.2 s, 16 PNGs | 72 s | 8.7 → 10.9 |
>
> - **Triage of run 2: verdict *environment*.**
>   - Both workers sat on the splash at the same moment, before any API call (the splash waits for the app's code). Setup was about 5× slower, load reached 48.5 on 10 CPUs, swap 7.7 of 8 GB, with no backend error.
>   - The same flow is green in runs 1, 3, 4 and 5; the sign-in under the LAN name takes about 2.8–5.3 s against a 30 s budget (the same as L's).
>   - TEMP-DIAG removed (grep: none).
> - **Images** (`mkdocs_src/docs/gallery/{desktop,mobile}/{lang}/{theme}/security/connection-indicator.png`, gitignored; desktop 1280×720, mobile 1290×2220). M viewed desktop en/light and mobile en/dark; the test-author viewed six variants. They show «Connection: local network», the reason («Local network without encryption: …») and «How to connect securely», with the mocked dashboard behind; the drawer on mobile. Nothing live or private.
>   - **Framing:** on desktop the open details push the menu into its scroll («FX Rates» half cut, Files and Settings hidden). The subject is whole, so rule (c) applies: stay at 720. Option for the developer: a taller desktop screen, about 1280×900, one line.
>   - The version label reads `-dirty` (local build from the worktree); it will be clean in the release run.
> - **Gates:**
>   - Prettier clean (run from `frontend/`);
>   - `tsc -p tsconfig.e2e.json`: only the 2 known errors;
>   - `check-orphans` clean;
>   - `git diff --check` clean;
>   - 6158 and 6168 free;
>   - `dev_release2` still `3cceb4f90`: no overlap.
> - Docs gates: unchanged since 21.3 (build strict 0 WARNING, check-links only `#rolling-return`).
> - **Not run:** the other 125 gallery shots under the new launch rule (it maps only `lf-e2e.lan`). The CI runs the whole gallery.
> - Agents: `bc4a6092` stopped and idle, nothing half done; `96a01a8b` idle, no edit made.
> - **Step 21 closed.** CHECKPOINT READY sent to the coordinator; M FROZEN.
>
> **Batch 8 committed and integrated:** `dbf4263e9` (test gallery) and `4845bdefb` (docs), merge `43de22cbd`, train 25 (`dev_release2` = `586a4f0ea`).

## Batch 9 — PAC shots after D's row 16 (base `083ed26dc`, train 26)

### 22. ✅ PAC gallery shots on the integrated revision — 2026-10-09

> **Coordinator's brief** (18:09): train 26 is in (`dev_release2` = `083ed26dc`; D's row 16, «rounding against the plan», merge `b81b92fd1`).
> - Put `galleryPac.ts`'s external account back in USD (D's report);
> - re-shoot the PAC gallery shots, desktop and mobile, PAC only;
> - lane 6158/6168, data `/tmp/librefolio-r2-m`;
> - look at the images one by one: nothing live or private;
> - checkpoint with the manifest, then FROZEN.
>
> **22.1 ✅ Baseline and analysis (M, 18:15)**
> - HEAD `083ed26dc` = `dev_release2`; worktree clean; 6158 and 6168 free.
> - **The external account is already in USD:** `galleryPac.ts:86` `externalAccount: {name: 'Northwind Bank', currency: 'USD', declared: '3000', toUse: '1200'}`, since `2e8d6a551` (batch 6). D's own plan says so (`plan-phase00PacRoundingDirectionFix.prompt.md:30`). The report forwarded to M is out of date: **nothing to change**.
> - **D's row 16** (`96283eaa5 fix(pac)`, `85b2a3125 docs(pac)`):
>   - backend only (`pac_allocator/{constraints,evaluator,ledger,normalize,numeric,objectives,planner,models}.py` and the schemas), plus one comment in `StateNotice.svelte`;
>   - credits are rounded down and debits up, once, on the exact value;
>   - in D's own words, the dust it should remove from `pac-result-plan`: step 4 «0.01 USD Northwind → DEGIRO → 0.01 EUR», step 6 «0.14 USD → about 0.13 EUR», step 5 «about 1,233.42», and Not invested «Rounding ≈ −0.02 EUR».
> - **PAC page** (`user/tools/pac-allocator/index.en.md`): no placeholders left; the 9 images are already referenced (`pac-step-{liquidity,brokers,assets,routing,targets,review}`, `pac-result`, `pac-result-plan`, `pac-result-proof`). D's «`:192`» means only that its edits (`:226-249`) stay away from the zone of M's images. Nothing to replace; the alt texts are to be checked against the new shots.
> - **Tests:** `gallery.spec.ts` `Tools` → `PAC allocator steps` (6 shots × 8 combinations) and `PAC allocator result` (3 × 8). Filter `-f 'PAC allocator'`; 144 PNGs over the two projects, gitignored (`.gitignore:79`).
> - **Before-hashes:** the PAC PNGs on disk come from batch 6 (USD, before row 16). Recorded in `runs/b9_pac_before.tsv`, to show which shots change.
>
> **22.2 ✅ Runs (M, 18:12–18:32)**
> - **⚠️ Off track: run 1 red in setup** (`runs/b9_pac_1.{log,meta}`, 18:12:21–18:18:35, load 34.6 → 40.6).
>   - `Error: Timed out waiting 300000ms from config.webServer`: no test ran.
>   - The webServer is `dev.py server --test`, which first rebuilds a stale frontend and MkDocs (`playwright.config.ts:75-80`). After train 26's fast-forward the build was stale, and on a loaded machine the rebuild alone ate the 300 s.
>   - DB populated (fresh, lane); port free before and after.
>   - Verdict: **environment** (setup). No timeout raised.
> - **Fix:** rebuilt before the run, outside Playwright's timer (`runs/b9_prebuild.meta`):
>   - `dev.py front build` 222 s, exit 0;
>   - `dev.py mkdocs build` 67 s, exit 0, 0 WARNING.
>   - Together 289 s, which with the server's start confirms why 300 s was not enough.
> - Load peaked at **127** (another lane's Playwright, `e-alfy-special-fishstick`, and a svelte-check in the main checkout); waited for a 1-min load < 25 (18:24 → 18:28; nothing in M's lane).
> - **Run 2 green** (`runs/b9_pac_2.{log,meta}`, 18:28:55–18:32:25, 210 s, load 20.4 → 23.4): 4/4 in 3.1 min.
>   - Desktop: steps 43.0 s, result 40.0 s. Mobile: steps 38.4 s, result 21.3 s.
>   - 144 PNGs rewritten; port free before and after.
> - **Before/after** (`runs/b9_pac_before.tsv`, `b9_pac_after.tsv`, script `scripts/b9_pac_hashes.py`):
>   - **mobile, 6 steps: 48/48 byte-identical**: inputs, unchanged by D;
>   - **desktop, 6 steps: 48/48 changed**, only the sidebar: the «Connection: secure» line (train 24, L) and the version label `v1.1.0-1078-g083ed26dc-dirty`, both absent from batch 6's shots;
>   - **results: 48/48 changed**. `pac-result-plan` desktop goes from 1280×1040 to **1280×789** (block 773 px); `pac-result` en from 957 to 949.
> - **D's fix seen by M** (desktop en/light):
>   - «Operational plan (4)»: 2 transfers, 1 deposit and **one** exchange, «1,101.78 EUR → about 1,233.28 USD» with spot = effective 1.1193593463 and spread loss 0.00;
>   - orders 5–8;
>   - **no dust steps** (0.01 USD, 0.14 → 0.13);
>   - Not invested ≈5.03 with **Rounding ≈0.01 EUR (not negative)**.
>   - Nothing live or private: test account, mock brokers and assets, prices from the populated DB or Manual, the offline guard green.
> - **The one-by-one review of the 144 images** goes to three read-only reviewers in parallel (desktop steps, mobile steps, results), each with the expected subject, a checklist and a TSV verdict per image (`runs/b9_review_*`).
>
> **22.3 ✅ One-by-one review of desktop steps and results; two alts (reviewers + docs-writer, 18:50)**
> - **Results** (`runs/b9_review_results.{tsv,md}`): **48/48 OK**.
>   - D's fix is in every image: the 16 plans have exactly steps 1–4, with no 0.01 USD or 0.14 USD; Rounding ≈0.01 in all 16 `pac-result`.
>   - The rounding goes the right way: the exchange gives «about 1,233.28» (down from 1,233.2877); AAPL costs 1,201.28 (up from 1,201.274208).
>   - The same data in every variant; no English strings left.
>   - The only low-confidence doubt (a strip above `mobile/it/light/…/pac-result-proof`) was checked by M: it is the page background above the card, the frame's margin. No defect.
> - **Desktop steps** (`runs/b9_review_desktop_steps.{tsv,md}`): **30 OK, 18 ISSUE**. Three defects, **all pre-existing** (the main content does not depend on the sidebar, the only change since batch 6):
>   - **A** `pac-step-routing` it/light and it/dark: the second broker's row (Interactive Brokers: «Consenti tutti / Escludi tutti / 3 consentiti su 3») is cut mid-text by the sticky footer. In Italian DEGIRO's settings wrap to 3 lines (+32 px); in en/fr/es the row stays whole.
>     - The first broker, the subject by rule **(c) «il primo broker basta»** (`lista_scatti_alti.md:195`), is whole in every variant. Seen by M (it and en light).
>   - **B** `pac-step-review`, all 8: the top edge cuts about 8 px of the row above the summary table.
>   - **C** `pac-step-targets`, all 8: the Asset column truncates «MSFT Microsoft Corporation» **without an ellipsis** («…Corp» with the last letter sliced; «…Cor» in es). This is the product's own display at 1280 px, not the framing.
>   - Not counted: «ROUTING–» without a space before the dash (a product string); «Riepilogo» and «Récapitulatif» used both for the step and for the toggle; money in en format in it/fr/es (known, already in the results).
> - **Alts** (docs-writer, `user/tools/pac-allocator/index.en.md`, the two `alt` attributes only):
>   - `pac-result`: «… and the title of Allocation per Asset» → «… and the Allocation per Asset table, with each Asset's target share beside its share after the plan, its value after the plan and its ideal value, and the totals». This was M's own debt from batch 5: the (a) rule had already extended the shot to the end of the table.
>   - `pac-result-plan`: «a currency exchange» → «a currency exchange with its rate»; «and the title of the next Broker's orders» → «and the next Broker's orders». The plan got shorter with D's fix, so DEGIRO's orders now fit.
>   - User pages always load the **desktop** shots (`gallery-img-loader.js`), so the alts only need to match those. The page has no translations: no debt.
>   - `mkdocs build` strict: 0 WARNING (`b9_docs_build.log`). `check-links`: only `#rolling-return` and the 3 known ones (`b9_docs_links.log`). `git diff --check` clean.
>
> **22.4 ✅ Mobile steps, manifest, gates (reviewer + M, 19:05)**
> - **Mobile steps** (`runs/b9_review_mobile_steps.{tsv,md}`): **22 OK, 26 ISSUE**. All **pre-existing**: the 48 images are **byte-identical** to batch 6's.
>   - **D** `pac-step-targets`, all 8: the table is shifted sideways and misaligned with its header. Names are cut on the left («APL Apple Inc.»), the Target % inputs on the right with no «%», and «Actions» sits over the inputs; the bond input keeps its focus ring. Seen by M (en/light).
>     - Cause: the table **does not fit the width on a phone** (product, DataTable on mobile) plus the focus left on the input just typed (fixture).
>   - **E** `pac-step-assets`, all 8: starts at the AAPL card, without Search Asset / Your Assets / Manual Asset. This is the fixture's phone fallback; the mobile gallery caption («automatic and manual prices and their origin badges») holds.
>   - **F** `pac-step-review`, all 8: the «Actions» header with no ⋮ in the rows (the same DataTable on mobile); fr/es: the header row cut at the top edge; es: a sentence cut mid-letter.
>   - **G** `pac-step-liquidity` es, 2: «· 100» / «% tuya» break apart: an ordinary space before «%» in `es.json` (needs NBSP; L's catalogues).
> - **Manifest** (`runs/b9_pac_manifest.{md,tsv}`, script `scripts/b9_pac_manifest.py`): 144 images with path, size, sha256, change against batch 6 and verdict. **100 OK, 44 ISSUE: all in the step shots and pre-existing; none in the result shots**, the ones D's fix touches.
> - **Gates:**
>   - run `b9_pac_2` 4/4;
>   - docs build strict 0 WARNING; check-links only the known ones;
>   - `git diff --check` clean;
>   - 6158 and 6168 free;
>   - `dev_release2` still `083ed26dc`.
> - **Tracked delta:** the PAC page (2 alts) and this journal. The PNGs are gitignored.
> - **To the coordinator, for decision:**
>   - **A** desktop IT routing: accept under (c), or a taller screen up to the second broker's control row;
>   - **D** mobile targets: blur plus horizontal reset in the fixture, and the product item for DataTable on mobile;
>   - accept B and E;
>   - backlog **C** (truncation without an ellipsis), **F** (Actions without ⋮ on mobile), **G** (NBSP in `es.json`), «ROUTING–» without a space, «Riepilogo/Récapitulatif» used twice.
> - **Step 22 closed.** CHECKPOINT READY sent; M FROZEN.
>
> **Batch 9 committed and integrated:** `29103f95b` (docs pac), merge `83cb002a2`, train 27 (`dev_release2` = `9f060ef6e`).
>
> **Coordinator's decisions on batch 9** (20:01):
> - A (desktop IT Routing): accepted under rule (c);
> - B (Review desktop, 8 px) and E (Assets mobile, the fallback): accepted;
> - **D** (Targets mobile): batch 10 approved, fixture only;
> - product defects:
>   - to D (backlog of row 13): C (truncation without an ellipsis), F («Actions» without ⋮ on mobile), «ROUTING–», «Riepilogo/Récapitulatif», the Targets table layout on mobile;
>   - to S (catalogues): G (NBSP before «%» in `es.json`).

## Batch 10 — Targets shots: the fixture leaves no focus and no horizontal scroll (base `9f060ef6e`, train 27)

### 23. ✅ `framePacTargets`: blur and horizontal scroll reset before the shot — 2026-10-09

> **Coordinator's brief** (20:03):
> - only the fixture of the Targets shots on mobile: remove the focus from the input and reset the scroll before the shot;
> - re-shoot only the shots touched;
> - lane 6158/6168;
> - review the images as usual;
> - checkpoint, then FROZEN.
>
> **23.1 ✅ Baseline and analysis (M, 20:10)**
> - HEAD `9f060ef6e` = `dev_release2` (fast-forward; M's B9 commit `29103f95b` inside); worktree clean; 6158 and 6168 free.
> - Train 27 touched no file under `frontend/e2e`, `components/ui` or `features/tools`: the fixture is the same as in batch 9.
> - **Cause**, `galleryPac.ts`:
>   - `framePacTargets` types the bond's target (`typeValue` → `input.fill`). `fill` focuses the input and scrolls it into view, inside the DataTable's horizontal scroller too: `.table-wrapper`, `overflow-x: auto` (`DataTable.svelte:1559-1561`).
>   - On a phone the table is wider than the screen, so the wrapper stays scrolled. The selection column is sticky on the left (`.td-select`) and the Actions column sticky on the right (`.td-fixed`), so the names end up cut under the checkboxes and «Actions» over the inputs.
>   - Header and body share the same scroller, so they are not really misaligned: it is the stickies that overlap.
> - **On desktop too** the bond input keeps the **focus ring** in all 8 `pac-step-targets` (seen by M in en/light: a dark, thicker border), but the table fits, so there is no scroll.
>   - The blur goes in the shared fixture: the desktop Targets shot changes too, only in its focus ring. A viewport-only blur would be artificial; to report in the checkpoint.
> - **What changes on disk in a re-run:**
>   - desktop: every shot, because of the version label in the sidebar (`v1.1.0-1089-g9f060ef6e-dirty` instead of `…1078-g083ed26dc…`);
>   - mobile: the sidebar is not visible, so the other step shots should come out **byte-identical**.
>   - Pixel diffs with PIL and numpy (present in the venv) delimit each change.
> - Before-hashes `runs/b10_pac_before.tsv`, the same as batch 9's after.
> - Test-author: red first (assertions in the fixture: input not focused, scroller at `scrollLeft` 0), then the fix, then green, diffs and review.
>
> **23.2 ✅ RED → fix → GREEN, diffs, review (test-author, 20:15–20:28)**
> - **RED** (`runs/b10_targets_red.{log,meta}`, 20:15:05–20:17:54, load 10.8 → 36.0): the new guard `expectPacTargetsAtRest` fails at the first combination on both viewports, «the Targets shot is not at rest…»:
>   - desktop `focused: input[data-testid="pac-planner-target-input"]`, `scroller: 0`;
>   - mobile the same focus plus `scroller: 53`.
> - **Fix** (`galleryPac.ts`, +51/−2, the only file):
>   - in `framePacTargets`, after `typeValue`: `bond.blur()`, then `scrollBackToFirstColumn(bond)` (every box from the field up to the page back to `scrollLeft` 0, `behavior: 'instant'`), then a check that the value stays 40 and the control `balanced`;
>   - after the framing, the guard `expectPacTargetsAtRest`, an `expect.poll` on `{focused: null, scroller: 0, scrolledBoxes: []}`. The scroller is found structurally (the nearest ancestor with `overflow-x` auto/scroll); not found → `null` → red.
>   - The guard also covers boxes scrolled sideways other than the wrapper (cells with `overflow: hidden`): in practice `scrolledBoxes: []`. `settlePacShot` still runs after the reset.
> - **GREEN:**
>   - `b10_targets_green` (20:19:03–20:20:21, 78 s, 2/2: mobile 40.8 s, desktop 42.6 s);
>   - control `b10_targets_green2_desktop` (`--desktop-only --no-populate`, 65 s, 1/1).
>   - No webServer timeout (rebuild within 300 s). Port free before and after every run.
> - **Pixel diffs** (`runs/b10_pixel_diff.tsv`, `_summary.txt`; scripts `b10_pixel_diff.py`, `b10_regions.py`; the before copies in `/tmp/libreFolio_b10_before_png`, 0 mismatches against `b10_pac_before.tsv`):
>
> | viewport | shots | byte-identical | change |
> |---|---|---|---|
> | mobile | 5 non-Targets × 8 | **40/40** | none |
> | mobile | Targets × 8 | 0/8 | table header and 3 rows only (box (294,1126)–(1188,1734)); selection column and Total untouched |
> | desktop | all 48 | 0/48 | the sidebar's version label (box (41,688)–(215,701); 1,342–1,376 px) |
> | desktop | Targets × 8 | — | plus the bond field's box (1044,531)–(1158,571): the focus ring is gone |
>
> - **⚠️ Off track:**
>   - Desktop has anti-aliasing noise on rounded edges (asset icons, field corners), at most 9/255 on one channel. It changes between two desktop runs with the same code, build and DB (12/48 shots; `b10_green1_vs_green2_desktop.txt`). Verdict: **environment** (the renderer), not the fix; mobile shows none. The desktop shots on disk come from the second run (`b10_pac_after.tsv`); the first one's are kept in `*_green1*`.
> - **Review of the 16 Targets** (`runs/b10_review_targets.tsv`; M saw mobile en/light and desktop it/dark):
>   - **desktop 8/8 OK:** the table whole, 30/30/40 with «%», no focus ring, Total 100.00%, Balance all disabled, ⋮ in every row;
>   - **mobile 8/8 OK, with the layout caveat:** the table from its first column, names whole («AAPL Apple Inc.», «Global Bond ETF»), no focus. But the **Target % inputs are off the right edge** (their values are not visible) and «Distributio» is cut by the sticky Actions column. This is the mobile layout issue already routed to D: before the batch the values could be seen and the names were cut; now the reverse.
>   - «MSFT Microsoft C…» is cut on both viewports, as before (C, routed to D).
> - **Gates:**
>   - Prettier clean;
>   - `tsc -p tsconfig.e2e.json`: only the 2 known errors;
>   - `git diff --check` clean;
>   - 6158 and 6168 free;
>   - `dev_release2` still `9f060ef6e`.
> - Triage: the original defect is an **assumption** (the fixture took for granted that `fill` leaves the table at rest), fixed in the fixture.
> - **Step 23 closed.** CHECKPOINT READY sent; M FROZEN.
>
> **Batch 10 committed and integrated:** `0771eaaaf` (test gallery), merge `49212b6df`, train 28 (`dev_release2` = `fbb57eb41`, tree `eb2090da4488`).
>
> **Coordinator's decisions on batch 10** (21:59):
> - the mobile compromise (the Target % inputs past the right edge, «Distributio» cut) is **accepted**: it is the table layout, in row 13's backlog and in 38 as **C-38**;
> - removing the focus ring on desktop (shared fixture) is accepted too.

## Batch 11 — the 1.2 translation round

### 24. ⏳ Triage, small fixes, glossary and pipeline launch — 2026-10-10

> Tracked in its own plan: [plan-phase00TranslationRound12.prompt.md](plan-phase00TranslationRound12.prompt.md).
