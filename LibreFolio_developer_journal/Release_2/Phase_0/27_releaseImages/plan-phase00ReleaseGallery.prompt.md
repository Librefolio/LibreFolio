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
