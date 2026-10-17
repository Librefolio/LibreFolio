# devWiki Log

> Append-only chronological record of all wiki operations.
> Format: `## [YYYY-MM-DD] {operation} | {title}`
> Parse: `grep "^## \[" log.md | tail -10`

## [2026-10-07] update | CI/CD Release Pipeline
Realigned the concept page with the real release.yml after R12 (workstream M): no screenshot cache,
no `force_gallery`, no test stage; the gallery is now a release gate (soft on dev) with failure
evidence kept; Docker tags follow the user guide (latest = light, X.Y.Z full, X.Y.Z-light, no v,
no latest-light) with per-variant push guards; the light image is pushed before the full one so the
update prompt's image gate (plain X.Y.Z) fires only once `latest` moved; cache keys carry the runner
image ahead of the ubuntu-latest → 26.04 move; dashboard gallery fixture + its Vitest guard.
Updated: [[concepts/ci-release-pipeline]].
Graph not updated: graphify-out/graph.json and .graphify_python are absent in this worktree (ignored
artifacts); queued for the next graphify --update on the main checkout.

## [2026-09-10] file | SQLite savepoint without an outer write transaction commits on release
Recorded the deferred-BEGIN trap found by the asset deletion commit-failure
regression and the no-op-write fix that restores real outer rollback semantics.
Filed: [[problems/sqlite-savepoint-without-write-begins-as-transaction]].

## [2026-09-09] file | Browser GHCR image probe could not complete the anonymous Bearer flow
Filed the integrated update-check lesson: stable release metadata and image
pullability are separate probes; GHCR's anonymous challenge is completed by a
fixed-target authenticated same-origin endpoint with strict trust validation,
explicit pending/error mapping, and a fail-closed frontend.
Filed: [[problems/ghcr-browser-cors-auth-flow]].
Updated: [[concepts/ci-release-pipeline]].
Graph updated with a scoped incremental pass over those two pages: +28 nodes,
+35 edges, 3 hyperedges total, and 169 recomputed communities. The manifest
was stamped only for the two target pages; unrelated dirty corpus files were
not extracted. Source-path validation remained at the same 43 missing paths /
65 occurrences present before this filing, with no new failure from this work.

## [2026-09-02] file | MWRR pole when the period starts on a data-less day
Filed the beta-reported MWRR cumulative pole (+9.94% on a −1.5% period): deposit on the first NAV day double-counted when the start date had no data. Fixed in the period re-basing (flows embedded in the first snapshot are no longer re-added).
Filed: [[problems/mwrr-pole-dataless-period-start]].

## [2026-09-02] update | CI/CD Release Pipeline
Added the release-tag convention for the F14 in-app update prompt (SemVer vX.Y.Z, stable-only via releases/latest, name free-form, GHCR tags aligned) — user asked for the rule to live in the wiki + dev guide.
Filed: [[concepts/ci-release-pipeline]].

## [2026-09-01] lint-repair | Applying the P0–P3 repair list from the 2026-08-31 lint

**The finding that framed the work.** The lint counted **144 of 1 828 paths** cited in
`## Source files` tables pointing at files that do not exist, and — decisively — **23 of
the 38 pages written in the 2026-08-31 ingest** were among them. The refactors that could
explain staleness are from **June 2026**; the ingest is from **31 August**. So this was
not ageing. **The ingest transcribed paths out of plans without checking them against the
tree.** Everything below follows from treating that as the root cause rather than the
symptom.

### P0 — where the wiki asserted things that are false

- **Three invented paths** (present in no source; constructed because they sounded
  right) replaced with verified ones: `_orphans.py` → `_cli.py` (the check is the
  `check-orphans` action, registered at `_cli.py:462`), `_schedule.py` → `_scheduler.py`,
  `actions/frontend.py` → `_frontend_common.py`. **There is no `actions/` package.**
  A **fourth** invention the lint had not caught: `_resources.py`, also in
  [[sources/p8-runner-parallel-architecture]].
- **[[entities/test-runner]] rewritten from the code.** The old page documented
  `_orchestrator.py`, `_backend_unit.py`, `_e2e.py`, a `suites/` directory, a
  `@registry.register("transactions")` decorator with auto-discovery and a
  `./dev.py test backend --suite transactions` CLI. None of it exists. The real package
  is **30 flat modules, 15 categories, 250 `add_test()` call sites**, with the registry
  built by **14 explicit `populate_registry()` calls** in `_registry.py` — no decorator,
  no discovery — and a CLI of the form `./dev.py test <category> <action>` generated
  from `TEST_REGISTRY.keys()`.
- **[[concepts/backend-test-isolation]] retired, not amended.** It claimed twice that
  `unique_id()` combines timestamp + UUID4. The code
  (`backend/test_scripts/test_utils.py:174-182`) is a millisecond timestamp plus a
  **process-global counter that restarts at 0 in every process** — two workers starting
  in the same millisecond produce the same identifier. The naming convention, which is
  sound and has nothing to do with parallelism, moved to
  [[concepts/unique-test-identifiers]]; the isolation claim is withdrawn in favour of
  [[concepts/test-isolation-classes]]. The page's own 2026-08 caveat was also wrong
  (**56/16** where the truth is **36/7**) and spoke of "**the** `session` fixture" —
  there are **ten**, redefined locally in ten files of `test_services/`, all
  function-scoped, none owned. Centralisation is work to be **built**, not an owner to
  be consulted. Verified totals: **195** test files, **645** `test_` functions in
  `test_api/`.
- **[[decisions/test-runner-package-split]]** — History corrected to 30/15/250 and the
  sentence about an `actions/` reorganisation deleted. The module table is left frozen
  on purpose: the page documents the *rationale* of 2026-06.
- **`frontend/mcr.config.js` removed from 4 pages.** It never existed — it is proposal
  B.3 of `plan-p7-js-coverage.md:227`. Monocart was **removed**
  (`frontend/e2e/fixtures/playwright.ts:297`, *"no monocart here any more"*); coverage is
  istanbul end to end. Each page now says so, because that is information and not merely
  a correction.

### P1 — mass drift

- **233 substitutions across 109 pages** from the 85-entry remap table of the June 2026
  refactors (stores, transaction components, frontend utils, backend financial utils,
  skills). Every destination `ls`-verified before writing. Basename matching alone was
  **not** safe: it proposed `api/v1/brim.py` → `schemas/brim.py`, `ai_export/service.py`
  → `risk/service.py` and three more semantically wrong hits, all rejected by a guard
  that only auto-accepts a move *deeper* into the same directory or a pure prefix
  addition.
- **A further 11 rules, 20 substitutions**, found while repairing: `test_utils/` →
  `test_utilities/`, `fx_service.py` → `fx.py`, `scripts/test_runner.py` →
  `scripts/test_runner/`, `.github/skills/test-triage/` →
  `.github/skills/devpy-tools/test-triage/`, and an **AI-export cluster where the ingest
  had again written the planned names rather than the delivered ones**:
  `AiExportMenuV2.svelte` → `AiExportMenu.svelte`, `aiExportClipboardV2.ts` →
  `aiExportClipboard.ts`, `ai-export.spec.ts` → the `frontend/e2e/ai-export/` directory
  of four specs. The `V2` suffix is a plan artefact; it never shipped.
- **The six absences the lint had already resolved**, plus **9 broken mkdocs paths**
  (`user/brokers.en.md` and `user/settings.en.md` are directories today) — 12
  substitutions.
- **[[problems/utc-today-vs-user-calendar]]** rewritten symbol by symbol. In doing so:
  `resolveDateSentinel` is at `dateRangeStore.svelte.ts:144`, **124 lines from
  `defaultRange()` at L20** — two of the three product defects live in the same file.
- **Twin pairs merged**, descriptive slugs surviving as decided:
  [[sources/phase07-part4-round3-staging-rewrite]] and
  [[sources/phase07-part4-round5-server-type-rules]] absorbed the non-redundant lines of
  the bare-slug copies (which pointed at different `related:` pages), and the copies —
  the wiki's only two orphans — were deleted.

### P2 / P3

- **[[concepts/silent-no-op-option]]** created and linked from the four problems that
  paid for it — `resume-mode-stale-import`, `coverage-mode-stale-import`,
  `coverage-report-category-dest-collision`, `env-var-injection-point-duplicated`. Four
  incidents, one shape: *an option that is accepted, does nothing, and does not say so.*
  Two mechanisms underlie it — `from x import y` freezing a value at import time, and two
  code paths where the design assumed one.
- **[[concepts/assert-on-identity-not-prose]]** created. Its frontmatter pointer had
  existed in [[problems/i18n-key-assertion-false-green]] since 2026-08-31, aimed at a page
  nobody had written.
- **[[features/F-020]]**: the dangling `decisions/fx-triangulation.md` replaced by
  [[decisions/fx-sync-pair-based]] with a line on how they differ, and an explicit note
  that no decision page for the triangulation algorithm exists — a gap, not a broken link.
- **See also added** in [[decisions/settings-write-path-contract]] →
  [[decisions/scheduler-converts-at-decision]].
- **[[sources/coverage-campaign-2026-08]]**: the Final position (78,02 / 59,45 / 90,18)
  now carries its caveat inline instead of forty lines below, plus a per-figure
  reconstruction. The frontend pair is comparable to its neighbours in the campaign.
  **`90,18 %` was initially recorded here as unexplained**; the project owner supplied
  its provenance the same day from `htmlcov-backend/index.html` — it is the **mixed
  lines + branch-arms** formula, the *same one* as 90,10 %, measured on the final
  validation run (`--workers 8`, `--fresh-run`, all three `--cov-clean-*`). So the set
  is **one pure-lines figure (92,33) against four mixed ones** (90,10 · 90,46 · 92,40 ·
  90,18), and the caveat now says which is which — because comparing across those two
  columns is exactly the error the campaign documented and then repeated in its own
  closing line. A hand-check of the five printed numbers does **not** reproduce 90,18:
  `coverage.py` uses `missing_branches` (≈1 917) where the HTML shows `partial` (1 719).
  Recorded, because a figure you cannot reproduce looks wrong when it is not.
  Same treatment applied to the triple in this log.
- **`index.md` reabsorbed**: 439 links / 381 destinations / **58 duplicate rows** →
  348 / 323 / **25**, and 514 → 414 lines. The three "Recent Additions" blocks became one
  **chronological register** under two rules — a page is listed once, on its creation
  date, never again when updated; a bulk ingest is named and counted, not expanded.
  The 60-link bare `F-NNN` dump under "Uncategorized / Auto-Recovered" was deleted (it
  duplicated `features/registry.md` without its information) and the 9 real pages stranded
  there were promoted into the Problems and Decisions tables with proper summaries.
  **"Individual Feature Pages" is now declared a selection**, with
  [[features/registry]] named as the authoritative catalogue — so a feature's absence
  from the index is no longer a defect to be re-flagged.
- **`raw/ingest-registry.md`**: the **14 sources** that lived only in
  `~/.copilot/session-state/` — outside the repository, outside git, in a directory that
  dies with the session — now point at
  `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/`
  and carry content hashes, so drift detection works for them as for everything else. The
  same re-pointing was applied to the `original_path` frontmatter and Source-files rows of
  the **8 source pages** that cited them. Its `INDEX.md` carries the warning these
  particular sources need: **a plan is not a chronicle** — several describe an
  architecture in the future tense, and reading them as a record of what shipped is
  exactly what produced the invented paths above.

### Result

**Non-existent paths: 157 unique / 328 occurrences → 33 unique / 52 occurrences**
(−79 % and −84 %; measured on the same filter before and after, counting only table rows
inside `## Source files`). The remainder are genuine unknowns, not drift: symbols whose
new home cannot be established by matching, and files that appear to have been deleted
rather than moved. They are listed in the repair report and were deliberately **not**
guessed at — guessing is what created the problem this entry describes.

**The empty AI-export packages, resolved.** `ai_export/assemblers/` and `profiles/`
contain nothing but `__pycache__` — stale bytecode, which is the only reason `ls` still
shows the directories and what makes them look like a move. They were **deleted** in
commit **`615a52eb` (2026-08-05)**, *"refactor(ai-export): remove legacy runtime"*:
**22 233 lines removed against 1 577 added**, taking `assemblers/`, `profiles/`,
`resolver.py`, `sampling.py`, `technical.py`, `normalization.py`, `service.py` and their
tests. The commit gives the reason: *"Keep one production path so catalog, prompts, and
tests cannot drift between V3 composition and **an unreachable profile/assembler
stack**."* Not tidying — **a second path that could still be reached and had started to
disagree with the first**, resolved by deleting the loser rather than reconciling them.
Same family as [[problems/registered-but-unreachable-test-actions]] and
[[concepts/silent-no-op-option]]. The two pages that pointed there now name the V3
successors — `components/payloads/portfolio_broker.py`,
`components/portfolio_financial.py`, `components/drawdown_context.py`,
`components/spec.py`, `analyses/spec.py`, `composer.py`, `runtime_service.py` — and carry
a note saying the modules were dismantled, with the commit and the rationale.

A detail worth keeping: the drawdown defect was not settled with a better fallback but by
**removing the fallback shape entirely** — `components/drawdown_context.py:31` reads
*"never fails — there is deliberately no success-shaped fallback"*, returning an explicit
`FAILED`/`UNAVAILABLE` status naming scope and period instead. The same lesson as
[[concepts/silent-no-op-option]], reached from the other side.

**Both pages were written 2026-08-31 — twenty-six days after the deletion.** They named
the deleted modules because they were written from the plan, not from the tree.

**Still open**: `backend/app/api/v1/brim.py` is cited by 5 pages and **no BRIM router
exists** — the endpoints live in `api/v1/brokers.py` and `api/v1/uploads.py`.

## [2026-08-05] update | MkDocs audit capability taxonomy

Updated [[sources/mkdocs-audit-2026-08-05]] with the second-order split:
13 existing-system extensions, 4 new system/library/integration prerequisites,
25 existing-but-undocumented capabilities, 21 editorial-only records, and 1
product ambiguity. Beta Risk Analysis is intentionally excluded. Graph semantic refresh
remains pending because the local Graphify Gemini API key was rejected.

## [2026-08-05] file | MkDocs English Source Audit

Filed [[sources/mkdocs-audit-2026-08-05]] from the completed non-developer English
MkDocs audit. Preserved 182/182 page coverage, 64 evidence-backed discrepancies,
validation results, and the explicit developer-guide deferral.

## [2026-08-05] update | AI Export first public V1 and probe/test boundary

Updated [[decisions/ai-export-versioned-snapshot-boundary]],
[[entities/ai-export-snapshot-service]],
[[concepts/ai-export-catalog-granularity-and-composition]], and
[[sources/phase00-ai-export-backend-snapshot]]. Recorded that internal V2/V3
iterations were never released: snapshot, catalog, selection, instruction and
response contracts start publicly at V1, while component/internal dataset
versions retain their technical history. Functional suites keep 57 fast probe
helper tests but never launch copied-DB prompt generation or Task Adequacy.
Cross-run prompt hashes are diagnostic; same-input UI/probe equivalence remains
byte-exact.
Graph: code-only refresh incorporated the V1 source contracts, then a scoped
semantic refresh replaced the four AI Export wiki pages and regenerated
`graph.json`, `GRAPH_REPORT.md`, and `graph.html`: 1,614 nodes, 2,274 edges,
160 communities. BFS resolves First Public AI Export V1, Functional Test
Boundary, Probe Helpers separation, and diagnostic-only cross-run SHA.

## [2026-08-05] update | AI Export single-runtime V3 final closure

Updated [[decisions/ai-export-versioned-snapshot-boundary]],
[[entities/ai-export-snapshot-service]],
[[concepts/ai-export-catalog-granularity-and-composition]], and
[[sources/phase00-ai-export-backend-snapshot]]. Recorded removal of the complete
profile/assembler/V1-schema runtime, the final 67-component/40-dataset/11-analysis
registry, the 8+11 public catalog, exact-output registry/catalog/stats/envelope
optimizations, zero orphan tests, 114/114 baseline/candidate prompt equivalence,
and 66/66 `OPTIMAL` Analysis variants. Candidate
`20260804T224056.073291Z` is the authoritative closure run.
Graph: scoped semantic refresh replaced 15 historical page nodes with 22
current nodes, pruned 11 obsolete findings, and regenerated `graph.json`,
`GRAPH_REPORT.md`, and `graph.html`: 1,533→1,540 nodes, 2,248→2,222 edges,
150 communities. BFS now resolves the single runtime, 114/114 prompt
equivalence and 66/66 `OPTIMAL` variants.

## [2026-08-04] update | AI Export short-lived session memory and fiscal catalog refinement

Updated [[decisions/ai-export-contextual-ui-memory]] after manual multi-login
testing: durable `localStorage` drafts were replaced by validated
user/context-scoped `sessionStorage` with a sliding ten-minute TTL; logout,
account changes, and every new login reset selection, detail, period, notes, and
Copy Anyway state. The public catalog was reduced from 13 to 11 Analyses by
removing Broker Cost Efficiency and FX Conversion Planning. Portfolio/Broker
fiscal-lot prompts became Capital-Loss Offset Strategies centered on official
tax-loss inventory (`cassetto fiscale`), jurisdiction/regime, category,
origin/expiry, used/remaining balances, legal eligibility, and conditional
no-action/gain-realization/staged/loss-harvesting paths. Targeted run
`20260804T190403.680108Z` rendered 2/2 prompts with source/production DB unchanged
and a passed secret scan. Final frontend cutover passed 32/32 Playwright tests
across desktop/mobile.

## [2026-08-04] file | AI Export catalog granularity and composition

Filed [[concepts/ai-export-catalog-granularity-and-composition]] from
`report-phase00AiExportUiPromptCatalogExplainedV1.md` and updated
[[decisions/ai-export-versioned-snapshot-boundary]],
[[entities/ai-export-snapshot-service]], and
[[sources/phase00-ai-export-backend-snapshot]]. Preserved the 32-dataset /
17-analysis / 65-component catalog shape; confirmed that PAC and Rebalancing
receive per-position unit price, value, WAC, P&L, and weight plus optional
per-Asset market context; distinguished position price, observed market price,
and price history; and recorded canonical `all_data` union semantics.
Documented the principal UX ambiguity (Technical Summary vs Asset Snapshot vs
Asset Comparison vs Technical, Context vs Analysis, and no granularity badges)
plus two unimplemented gaps: Broker Technical lacks a raw price-history
component, and Asset Trend promises Drawdown without composing
`asset.drawdown_context`. Verification covers 49/49 choices; real Portfolio run
`20260804T085052.052297Z` passed 5/5, UI/probe equivalence, secret scan, and
database immutability.
Graph: scoped semantic refresh replaced the four changed AI Export page
fragments, preserved external links, and regenerated `graph.json`,
`GRAPH_REPORT.md`, and `graph.html`: 1,524→1,533 nodes, 2,214→2,255 edges,
144 communities. The semantic incremental queue fell from 242 to 238
pre-existing changes, and queries now resolve the catalog taxonomy, PAC /
Rebalancing composition, three price meanings, `all_data` union, both gaps, and
run `20260804T085052.052297Z`.

## [2026-08-03] update | AI Export applied density policy and final hardening closure

Updated [[decisions/ai-export-technical-series-and-density-contract]],
[[decisions/ai-export-versioned-snapshot-boundary]], and
[[sources/phase00-ai-export-backend-snapshot]]. Recorded the approved and applied
event policy: Compact complete 7 calendar days/minimum latest 3, Standard complete
21 calendar days/minimum latest 10, and Full complete 30 calendar days/minimum
latest 20 per entity/annotation; indicator history remains 5/10/all non-empty rows.
Recorded the project owner's approval of empty-temporal-row hardening, explicit
Broker nomenclature, and `20260801T085820.657238Z` as final targeted evidence.
Applied-policy run `20260803T164514.504966Z` passed 7/7 prompts with zero
failures/public violations, UI/probe equivalence, a passed secret scan, and
unchanged source/production databases. Dense Portfolio/Broker output may exceed
60k, so the UI warning remains and no automatic cap is introduced. Closed the
Developer test-walkthrough and repository-instruction follow-ups; User Guide
IT/FR/ES translations remain explicitly deferred.
Graph: incremental detection found 240 semantic changes overall (237 pre-existing
plus these three AI Export pages). The scoped semantic refresh replaced only the
three AI Export page fragments, preserved their external links, and regenerated
`graph.json`, `GRAPH_REPORT.md`, and `graph.html`: 1,516→1,524 nodes,
2,189→2,214 edges, 144 communities. Post-refresh queries resolve the approved
21d/min10 policy and both final evidence runs.

## [2026-08-03] update | AI Export E2E and contextual-memory hardening

Updated [[decisions/ai-export-contextual-ui-memory]] with reactive async
client-session hydration, V2 per-user/context storage, separate raw Analysis-note
memory, and epoch/operation/session/context guards that make stale preparation
results inert before clipboard, persistence, or callbacks. Recorded the
panel/catalog/memory/contract Playwright split, focused runner actions plus the
cutover alias, and the final canonical gate: 214 unit tests and 32 desktop/mobile
E2E tests passed. The separate density recommendation remains awaiting user
decision and was not filed as resolved.
Graph: incrementally replaced the decision's semantic fragment, regenerated
`graph.json`, `GRAPH_REPORT.md`, and `graph.html`, and verified the four new
hardening concept nodes linked from the existing decision node.

## [2026-08-03] file | AI Export density, news causality, and Transactions NaN loop

Updated [[decisions/ai-export-technical-series-and-density-contract]] with explicit
backend-owned Compact/Standard/Full history and event density, source-row
diagnostics, lossless prompt encoding, and targeted real-prompt measurements.
Created [[decisions/ai-export-news-driver-analysis]] for cited dated web research,
source hierarchy, supported/inferred/speculative links, and unexplained movements.
Created [[problems/transactions-without-asset-filter-nan-loop]] for the
`__null__` → `NaN` reactive navigation loop and explicit `without_asset` state.

## [2026-07-30] update | AI Export Signal Density V2 contract

Updated [[decisions/ai-export-technical-series-and-density-contract]] with the
completed beta-v1 in-place temporal-class sampling and per-entity event-selection
contract, manifest propagation, 18/18 and 54/54 validation, measured Portfolio
Full 1Y reduction from 2,676,781 to 1,990,718 characters, and the known
`fx.rate_ohlc` warm-up blocker. No application, journal, or MkDocs source changed.
Graph: ran the incremental refresh, semantically replaced the updated decision
page, regenerated graph outputs, and verified the new Signal Density V2 nodes.

## [2026-07-30] file | AI Export technical series and density contract

Filed the native-market/target-valuation split, unique per-asset Portfolio/Broker
technical universe, inter-bucket return anchors, observed-only carry-forward and
epsilon semantics, measured Full 1Y density, deferred N=5 reduction candidate,
and removal of public drawdown recovery pending deterministic Risk episodes.
Filed: [[decisions/ai-export-technical-series-and-density-contract]].
Graph: incremental code refresh plus semantic page merge produced 1,461 nodes /
2,070 edges / 142 communities and regenerated `graph.html`; the new decision
node and its cross-links were verified.

## [2026-07-29] file | Risk G6 application contracts

Filed stable/pending-approval G6 decisions for historical-replay proxy audit,
lazy-panel retention/cache identity, present-bucket + Show all shock UX, and
optional inert YAML tags. Shared Foundation and G6-11 remain blocked.
Filed: [[decisions/risk-g6-application-contracts]].

## [2026-07-28] update | Risk backend audit and worker idle lifecycle

Updated the Risk quantitative decision, Sobol contract, Riskfolio dependency trap,
and Phase 0 source with canonical `random_seed`/`sobol_start_index` semantics,
generation-safe idle reap, lazy restart, and the explicit Riskfolio 7.3.0 probe.
Final focused evidence recorded: 74 service, 7 API, 21 schema, and 11 worker
lifecycle tests; frontend check/build and 5 mocked E2E; Docker arm64 build/smoke.
Created: [[problems/risk-spawn-worker-idle-residency]]. Updated:
[[decisions/risk-quant-engine-process-boundary]],
[[problems/quantlib-sobol-seed-skipto]],
[[problems/riskfolio-numpy-vectorbt-dependency-trap]], and
[[sources/phase00-risk-analysis-backend]].
Graph: incremental semantic extraction refreshed five Risk pages, removed modified-page
ghosts, preserved 11 external edges, and regenerated 1,435 nodes / 2,040 edges /
144 communities plus `graph.html`.

## [2026-07-28] file | Phase 0 Risk Analysis backend G0-G5

Filed the corrected quantitative backend: QuantLib MC/QMC and Riskfolio 7.0.1 in separate persistent spawn pools, cancellation-safe content-key deduplication, Sobol `skipTo` seed semantics, crash-safe response pipes, and the exact-version dependency resolution that preserves NumPy 2.5.1 without vectorbt/numba.
Created: [[sources/phase00-risk-analysis-backend]], [[decisions/risk-quant-engine-process-boundary]], [[concepts/cancellation-safe-inflight-deduplication]], [[problems/quantlib-sobol-seed-skipto]], [[problems/spawn-worker-response-queue-semaphore-leak]], [[problems/riskfolio-numpy-vectorbt-dependency-trap]].
Graph: semantic update merged all six pages, reclustered 1,525 nodes / 1,986 edges into 273 communities, and regenerated `graph.html`.

## [2026-07-27] update | Phase 0 AI Export final UI closure and manual approval

Source: completed `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` chain @ git:`untracked`. Recorded the custom icon/name/description analysis select; synthetic Data Snapshot → `data_only`; real analyses → `full_prompt`; locale-owned response language; hidden web/compatibility controls; body portal; domain-aware manuals; and final desktop/mobile approval.
Created: [[decisions/ai-export-contextual-ui-memory]] for client-session-user/context-keyed Portfolio, Broker, Asset, and canonical-FX draft persistence, including the invariant that Snapshot remembers hidden notes but never exports them.
Updated: [[sources/phase00-ai-export-backend-snapshot]], [[decisions/ai-export-versioned-snapshot-boundary]], [[decisions/ai-export-prompt-catalog]], [[entities/ai-export-snapshot-service]], [[problems/ai-export-cash-fx-valuation-basis-mismatch]], [[problems/ai-export-drawdown-selected-history-fallback]], [[problems/ai-export-clipboard-fallback-unreachable]].
Archive: the chain is complete in `Release_2/Phase_0/01_signalMigration/02_aiExport/`; no move to `RoadmapV4_UI/phases/` is required.
Graph: ran `./dev.py graph update`, semantically merged the eight changed AI Export wiki pages, reclustered, and regenerated `graph.html`; verified [[decisions/ai-export-contextual-ui-memory]] as a linked graph node.

## [2026-07-26] update | AI Export final-review regressions and canonical test registration

Filed the false Asset drawdown 409 caused by an empty technical window and the unreachable non-modern clipboard transport. Updated the Phase 0 source, snapshot entity, and versioned-boundary decision with the selected-history fallback, prepare-once V2 clipboard behavior, and canonical backend/service/schema/API plus frontend AI Export+signal suite registration; unrelated pre-existing orphan tests remain outside scope.
Created: [[problems/ai-export-drawdown-selected-history-fallback]], [[problems/ai-export-clipboard-fallback-unreachable]].
Updated: [[sources/phase00-ai-export-backend-snapshot]], [[entities/ai-export-snapshot-service]], [[decisions/ai-export-versioned-snapshot-boundary]].
Graph: ran `./dev.py graph update`, cached the five changed wiki pages, and reclustered with no visualization; both new problem nodes were verified linked.

## [2026-07-26] ingest | Phase 0 AI Export backend snapshot and hard cutover

Source: `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/` plan, frozen task/profile contract, and migration equivalence report @ git:`untracked`. Recorded the 18-task × 3-detail = 54 versioned profile platform, backend-owned factual snapshot boundary, frontend-owned safe prompt/clipboard boundary, fail-closed compatibility, four-surface hard cutover, and MCP-ready service seam.
Created: [[sources/phase00-ai-export-backend-snapshot]], [[decisions/ai-export-versioned-snapshot-boundary]], [[entities/ai-export-snapshot-service]].
Updated: [[decisions/ai-export-prompt-catalog]] (marked superseded by the Phase 0 architecture).

## [2026-07-26] file | AI Export cash FX valuation-basis mismatch

Live E2E showed that Portfolio Engine cash is transaction-date FX valued while native cash exposure is snapshot-date FX valued; an invalid equality invariant produced `portfolio_service.cash_balance_total_mismatch` as HTTP 503. Preserved engine summary/decomposition, kept factual snapshot-valued native cash, and gave `allocation_by_currency_pct` its declared `trading_currency_positions_plus_native_cash_snapshot_value` denominator without changing Portfolio Engine math. Filed: [[problems/ai-export-cash-fx-valuation-basis-mismatch]].

## [2026-07-26] file | Import wizard fake asset-id collision across multiple files

Root-caused marco's prod portfolio corruption (BTP PIU at -917k/-99.99%): the Step-4 merge keyed asset resolutions by bare fake ids that collide across files, binding Intesa's EURIZON seeds onto Crédit Agricole's BTPs. Fixed by namespacing fake ids per-file (unique global allocator) + cloning txs; documented the companion locale numeric-input bug. Filed: [[problems/import-wizard-fake-id-collision]].

## [2026-07-25] file | Crédit Agricole securities-only BRIM cash-neutral model

Recorded the CA BRIM decision: securities-only exports get automatic BUY/SELL cash counter-entries, and succession transfer rows are faithful BUY+DEPOSIT legs rather than ADJUSTMENTs. Filed: [[decisions/credit-agricole-securities-only-cash-neutral-brim]].

## [2026-07-23] file | Backend plugin signals and OpenAPI discriminator workaround

Recorded the Phase 0 technical-signal architecture (pure Python plugins, canonical outputs, one Asset/FX bulk request, local-only comparisons/benchmarks) and the `openapi-zod-client` discriminator type-erasure workaround. Updated the signals domain page. Filed: [[decisions/signal-backend-plugin-architecture]], [[problems/openapi-zod-discriminator-type-erasure]].

## [2026-07-01] ingest | Phase 09 — Portfolio Engine 3-Pool Refactor (commit 39106380)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/` @ HEAD:`d27902b7`.
Major engine refactor: inline WAC single-pass (eliminates N×M `compute_wac_iterative` DB calls), 3-pool K/R/W event-driven state machine with SELL fix (read WAC before reducing pool → correct K/R split on full exit), LAST_BUY_PRICE(V(u)) as price fallback, pre-frame/frame separation (no market eval before t0), range-aware blob cache with fingerprint keys. Supporting analysis docs: architectural analysis, implementation status, P&L breakdown, asset contribution gap analysis.
Created: [[sources/phase09-portfolio-engine-3pool-refactor]], [[concepts/inline-wac-computation]], [[concepts/pre-frame-frame-separation]].
Updated: [[entities/portfolio-engine]] (inline WAC, fallback chain, blob cache, 3-pool, history), [[entities/portfolio-service]] (+612 lines noted, tech debt updated), [[concepts/3-pool-cash-model]] (full K/R/W event-driven semantics, SELL fix, reconciliation invariant).

## [2026-06-30] ingest | Group 1 — Phase 07 PlanD-D1D2: Split/Promote Full Stack

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/README.md` @ git:`8f363d79`.
Batch ingest of sub-plan bundle (D1 backend batch pipeline, D2 frontend PromoteMergeModal, Centralize payload layer, 4 bugfix rounds). Key insights: `_PromoteCandidate` duck-typing, endpoint elimination (no standalone /split or /promote), centralized txPayloadHelpers.ts + txCommitApi.ts (9 callsites), PMC override UX.
Created: [[sources/phase07-pland-split-promote]], [[decisions/batch-only-split-promote]], [[concepts/centralized-tx-payload]].

## [2026-06-30] ingest | Group 2 — Phase 07 Part 5: BRIM Import Wizard v5

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-v5-ImportWizard.prompt.md` @ git:`5592f299`.
Major paradigm shift v4→v5: single-file breadcrumb → multi-file 4-step stepper (z:70 wide modal). Schwab parser added. ImportTodo signals and WorkspaceIntent pattern documented. 4-level data pipeline captured.
Created: [[sources/phase07-part5-import-wizard-v5]], [[entities/import-wizard-modal]], [[concepts/workspace-intent-pattern]], [[concepts/import-todo-signals]], [[decisions/import-wizard-v5-paradigm]].

## [2026-06-30] ingest | Group 3 — Phase 07 Standalone: PWA Mobile Optimizations

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Standalone/plan-pwa-mobile-optimizations.prompt.md` @ git:`66f56432`.
Archive re-anchor for PWA plan (already ingested as r2-parallel-features-pwa-borsa-fx). Two additional bugfixes captured: Svelte 5 runes reactivity fix for HelpMenu, and beforeinstallprompt race condition fix with early-capture in app.html.
Created: [[sources/phase07-standalone-pwa]].
Updated: [[features/F-098]] (cross-reference only, status remains implemented).

## [2026-06-30] ingest | Group 4 — Phase 08: Market Data Scheduler Backend

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/plan-phase08Step1-2-backend.prompt.md` @ git:`5592f299`.
Embedded FastAPI scheduler daemon with leader election (psutil + file-lock), 2 job types (current-price + history-sync), 5 new settings, fetch_interval column removal, atomic state persistence, JSONL log. Test checkpoint covers Phase 07 Part 5 + Phase 08.
Created: [[sources/phase08-scheduler-backend]], [[entities/market-data-scheduler]].

## [2026-06-30] ingest | Group 5 — Phase 09: Portfolio Engine + Dashboard (Milestone 2)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` @ git:`39106380`.
Major: 4-layer portfolio architecture (Engine→Service→API→Store), 4-stage engine pipeline, 3-pool cash model, MWRR double-counting bug fix (initial_nav correction), unified /portfolio/report endpoint, L2 TTL cache, P&L breakdown analysis. 6 known issues documented.
Created: [[sources/phase09-portfolio-engine-dashboard]], [[entities/portfolio-engine]], [[entities/portfolio-service]], [[concepts/3-pool-cash-model]], [[concepts/portfolio-report-unified]], [[decisions/mwrr-boundary-fix]].

## [2026-06-30] ingest | Group 6 — Wiki Audit 2026-06-18

Sources: `wiki_audit_2026_06_18/audit_transactions.md`, `audit_backend_infra.md`, `audit_assets_brokers_brim.md` @ git:`010ec3ed`.
Two critical corrections: WorkspaceIntent is frontend-only Svelte 5 pattern (not backend multi-tenancy); test_runner is now a modular package at scripts/test_runner/ (18 modules, not monolithic .py file). New mkdocs: runner_architecture.md, scheduler.md, transaction-draft.md update. lf-screenshot-carousel component created.
Created: [[sources/wiki-audit-2026-06-18]], [[entities/test-runner]].
Updated: [[concepts/workspace-intent-pattern]] (new page with correct categorization).

## [2026-06-30] ingest | Group 7 — Phase Final Bug Report 2026-06-25

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-final-subplan/bug_vari_report20260625.md` @ git:`1400451d`.
Static code analysis on Docker build: 5 bug categories. Critical: broker icon race condition (3 pages), import wizard oncreated path skips identifier prompt, BulkModal toolbar clipped by overflow-y:auto after import.
Created: [[sources/phase-final-bugs-2026-06-25]], [[problems/broker-icon-race-condition]], [[problems/import-wizard-identifier-prompt]], [[problems/bulk-modal-sticky-z-index]].

## [2026-06-30] ingest | Group 8 — CI/CD Release Pipeline

Source: `.github/workflows/release.yml` @ git:`a688bcb9` (commits a688bcb9..b79735e2).
GitHub Actions full automated pipeline: Node 24, Vite 7.3.5, package-lock.json, Docker :test tag, Playwright 8 workers + networkidle, screenshot cache, crypto.randomUUID polyfill.
Created: [[sources/ci-release-pipeline-2026-06]], [[concepts/ci-release-pipeline]].



**Created** (1 source page):
- [[sources/r3-sp-d-formmodal-wac-fx-chain]]

**Created** (3 decision pages):
- [[decisions/wac-target-currency-last-acquisition]] — WAC target = last acquisition's currency (deterministic)
- [[decisions/fxsyncmodal-parent-ownership]] — Parent owns FxSyncModal, child calls onOpenFxSync
- [[decisions/blur-detection-format-string-comparison]] — Compare formatDecimalForDisplay() strings for blur detection

**Updated** (2 feature pages):
- [[features/F-097]] — status: in-progress → **implemented** (all walktests pass, E2E added)
- [[features/F-048]] — title updated to reflect SP-D completion

**Key decisions extracted**:
- WAC target currency = most recent acquisition's currency (not majority)
- cost_basis_override is Currency object {code, amount}, sentinel {code, "0"} for auto hint
- FxSyncModal reuse pattern: parent owns modal, child calls onOpenFxSync prop
- Blur detection: compare formatDecimalForDisplay() strings (not numeric tolerance)
- useValidateScheduler: manual triggers bypass antiBounce 10s
- PromoteMergeModal WAC section was dead code → removed
- FX missing does NOT force manual mode (informative error only)

## [2026-06-01] ingest | Batch 4 — Five Independent Mini-Plans

Ingested 5 independent plans (BackendLogAudit, CandlestickChart, FxRangeHelper, LazyImageCache, RsiSignalBands) — all ✅ DONE 2026-06-01.

**Created** (1 source page):
- [[sources/independent-batch-2026-06-01]]

**Created** (3 concept pages):
- [[concepts/log-level-policy]] — 6-level hierarchy, TRACE registration, structlog patch
- [[concepts/image-preview-cache-pattern]] — objectUrl cache, size-based reuse, no ref counting
- [[concepts/fx-range-helper-pattern]] — ensureFxRangeLoaded centralization (DRY 6→1)

**Updated** (4 feature pages):
- [[features/F-076]] — status: planned → implemented (log policy + TRACE)
- [[features/F-080]] — status: planned → implemented (candlestick OHLCV chart)
- [[features/F-086]] — status: planned → implemented (image preview cache)
- [[features/F-039]] — added RSI zone-driven band style details

## [2026-06-02] ingest | Batch 2 — SP-C Bugfix Chain (11 plans: BulkModal + WAC Preview)

Ingested 11 completed plans from SP-C sub-plan (Frontend BulkModal + Suggest UX + WAC bugfixes) @ anchor `84f8bd07`.

**Created** (1 source page):
- [[sources/r2-sp-c-bugfix-chain]] — Combined source covering all 11 plans in the SP-C bugfix dependency chain

**Created** (2 problem pages):
- [[problems/wac-feedback-loop]] — WAC recalc → field update → infinite loop (resolved via cost_basis_mode)
- [[problems/clone-link-uuid-duplication]] — Clone paired rows from DB didn't generate link_uuid (resolved via type-rule check)

**Created** (2 concept pages):
- [[concepts/paired-partner-architecture]] — pairedWith, getPartnerOp, visibleOps, resolveFormItems pattern
- [[concepts/stateless-preview-pattern]] — Controlled components for computed values (WacPreviewSection)

**Created** (1 decision page):
- [[decisions/wac-inline-validate-commit]] — WAC computed in validate/commit, standalone endpoint eliminated from editing flow

**Updated**:
- [[features/F-097]] — Added bugfix chain status history, dead ends, implementation notes (feedback loop, stateless preview, link_uuid)
- [[features/F-048]] — Added SP-C bugfix chain references and related problems/concepts
- `raw/ingest-registry.md` — 11 entries added
- `index.md` — 1 source, 2 problems, 2 concepts, 1 decision added

Key patterns extracted:
1. **Feedback loop prevention**: Separate "what to compute" (mode) from "computed result" (value) — never let output be input trigger
2. **Paired partner architecture**: `pairedWith` for UI, `link_uuid` for backend — two separate linkage mechanisms
3. **Stateless preview**: Components displaying computed data should be controlled (no internal state)
4. **Fingerprint invalidation**: Hash material fields only — prevents unnecessary recalculation
5. **link_uuid promotion**: Decision based on target type needs, not source op type
6. **Post-flush WAC**: Compute on actual DB state in same transaction — eliminates adapter layer

## [2026-06-02] ingest | Batch 3 — Parallel Features (PWA, Port 60/40, Borsa Italiana, FX Fix)

Ingested 4 parallel-terminal features/fixes (no formal plan chains) @ anchor `84f8bd07`.

**Created** (1 source page):
- [[sources/r2-parallel-features-pwa-borsa-fx]] — Combined source covering PWA support (4 commits), Port 60/40 migration, Borsa Italiana provider, FX provider removal fix

**Created** (2 feature pages):
- [[features/F-098]] — NEW: Progressive Web App (PWA) — offline fallback, install button, iOS safe-area, theme-color sync
- [[features/F-099]] — NEW: Borsa Italiana Asset Provider — stocks, bonds, ETFs from borsaitaliana.it

**Created** (1 decision page):
- [[decisions/port-6040-scheme]] — All ports migrated from 8000/8001/8002 to 6040/6041/6042 ("60/40 rule" mnemonic)

**Updated**:
- [[features/registry]] — F-098 + F-099 added (Infrastructure / Assets domains)
- `raw/ingest-registry.md` — 5 entries added (PWA commits + plan, port commit, Borsa commit, FX fix commit)
- `index.md` — 2 feature pages, 1 source page, 1 decision added

Key observations:
1. **Provider pattern maturity**: Borsa Italiana is the 5th provider following `@register_provider` pattern — pattern now proven robust
2. **PWA = no-cache strategy**: financial apps prioritize data freshness over offline access — intentional design choice
3. **FX sentinel edge cases**: MANUAL auto-reinstate logic now handles all deletion scenarios including bulk-remove-all

## [2026-06-01] ingest | R2 Walktest Feedback Round — Batch 1 (WAC feature, 4 plans)

Ingested 4 source files from `PlanD_SplitPromoteFullStack/` R2 WAC sub-plans @ anchor `84f8bd07`.

**Created** (4 source pages):
- [[sources/r2-walktest-feedback-master]] — Master plan: 18 steps, 5 sub-plans (SP-A✅ SP-B✅ SP-C✅ SP-D⏳ SP-E🔲); cost_basis→Currency, WAC with FX, AssetEvent picker, store-first
- [[sources/r2-sp-a-cost-basis-wac]] — Backend: cost_basis_override→Currency, WACResult/WACConversionInfo schemas, compute_weighted_avg_cost with FX, recalc-wac endpoint (commit `92f4b1ba`)
- [[sources/r2-sp-b-backend-tests]] — Tests: 13 WAC API tests (WAC-1→WAC-13) + helpers; self-contained per-test isolation (commit `473d2611`)
- [[sources/r2-sp-c-bulkmodal-suggest-ux]] — Frontend: toolbar alignment, split preview fix, suggest overhaul (subtractive filter, human-readable, lightbulb), PromoteMergeModal simplified, ActionModal enhanced

**Created** (1 feature page):
- [[features/F-097]] — NEW: WAC — Weighted Average Cost (cross-currency, auto-calc on TRANSFER)

**Created** (1 decision page):
- [[decisions/cost-basis-currency-object]] — cost_basis_override from SafeDecimal to Currency {code, amount}; breaking change, no backward compat

**Updated**:
- [[features/F-048]] — 3 new status history entries (R2 SP-A/B/C), deferred items updated
- [[features/registry]] — F-097 added (fullstack, in-progress)
- `raw/ingest-registry.md` — 4 entries added
- `index.md` — F-097 in feature list, decision + 4 source pages added

Key architectural insights:
1. **Currency object over bare decimal**: unambiguous currency association enables multi-currency WAC
2. **Fail-safe WAC**: even one failed FX conversion → wac=None, never silently wrong
3. **Transient wac_info**: computed at commit time, not persisted — changes when FX rates update
4. **Target currency heuristic**: majority among TX → asset currency on tie → alphabetical

## [2026-05-31] ingest | Phase 07 Part 4 Round 6 — Plan D chain (7 files: split/promote full stack)

Ingested 8 source files: PlanB23 (registry backfill only, source page already existed), PlanD master @ `b0e223c0`, PlanD1 @ `666059b5`, PlanD2 @ `db7264ce`, D2-bugfix1 @ `fdf00d4b`, D2-bugfix2 @ `eb9b8ae2`, D2-bugfix3 @ `78f44497`, D2-bugfix4 @ `ce7344a1`.

**Created** (7 source pages):
- [[sources/phase07-part4-round6-pland-split-promote-master]] — Master plan: split/promote full stack integration into batch pipeline; D1✅ D2✅ bf1-4✅ D2-round2⏳; D3 absorbed into D2-bf3
- [[sources/phase07-part4-round6-pland1-backend-batch-suggest]] — Backend: TXMixedBatch + splits[]/promotes[], endpoint elimination (DD2), promote-suggest, consumed_link_uuids (DD4), _PromoteCandidate, 18 tests
- [[sources/phase07-part4-round6-pland2-frontend-split-promote]] — Frontend: PromoteMergeModal 3-column diff, BulkModal split/promote actions, Main Table promote migration to batch, suggest green banner
- [[sources/phase07-part4-round6-pland2-bugfix1]] — 21 bugs: BulkModal first-open race (getTypeRule FALLBACK_RULE), promote toolbar not appearing, findPromoteMatch constraint enrichment, collapse post-promote
- [[sources/phase07-part4-round6-pland2-bugfix2]] — Split preview editability (corrects DD-BF1), pipeline reorder (splits before updates), TXBatchResultItem.id→ids[], payload fixes
- [[sources/phase07-part4-round6-pland2-bugfix3]] — Biggest round: split schema {id_a,id_b}, suggest banner redesign, E2E (absorbed D3 scope), TransactionActionModal unification, cash sign fix
- [[sources/phase07-part4-round6-pland2-bugfix4]] — PMC auto-calc (compute_weighted_avg_cost), cost_basis_override only on receiver, promote-suggest constraint fix (None amount/qty), link_uuid sync, delta-days slider

**Updated** (1 decision):
- [[decisions/cash-transfer-split-promote]] — MAJOR: standalone `/split` and `/promote` endpoints eliminated (DD2); split/promote now exclusively via batch pipeline `splits[]+promotes[]`; added promote-suggest, consumed_link_uuids, PMC auto-calc

**Updated** (3 feature/connection pages):
- [[features/F-048]] — title updated (now "Form / Bulk / Delete / Promote / Split"), layer changed to fullstack, 8 new status history entries (D1→D2→bf1→bf2→bf3→bf4), PromoteMergeModal section, Split/Promote in BulkModal section, PMC Auto-Calc section, 10 new source files
- [[features/registry]] — F-048 title + layer updated
- [[connections/transactions-connections]] — header updated with Plan D completion status

**Registry**: 8 entries added to `raw/ingest-registry.md` (PlanB23 as `uncommitted` backfill, 7 PlanD files with commit hashes)
**Index**: 7 source pages + 1 decision summary updated in `index.md`

Key architectural insights documented:
1. **Endpoint elimination** (DD2): `/split` and `/promote` never used in production → removed entirely. All mutations go through unified `execute_batch` pipeline.
2. **consumed_link_uuids** (DD4): prevents Step 6 link resolution from re-processing link_uuids already consumed by promotes in Step 5c. Critical for atomic batch promote-and-create flows.
3. **Pipeline reorder** (DD-R2.2): `deletes(3) → splits(3b) → updates(4) → creates(5) → promotes(5c) → links(6) → balance(7)` — splits before updates enables "split + edit post-split" in same batch.
4. **PMC auto-calc**: `compute_weighted_avg_cost()` auto-fills `cost_basis_override` on TRANSFER receiver when null. Weighted average of BUY prices + incoming TRANSFER cost_basis at source broker.
5. **D3 absorbed**: E2E test scope originally planned as separate D3 sub-plan was absorbed into D2-bugfix3.

## [2026-05-30] ingest | Phase 07 Part 4 Round 6 Plans C2 + C2R2 — Bugfix, Pair Validation, MockFX, Contextual Validate

Ingested 2 new plan files (C2 @ `6aac0dce`, C2R2 @ `f9f3bec2`). Verified 8 already-ingested plans from the same batch — no re-ingest needed; existing pages accurate.

**Created** (2 source pages):
- [[sources/phase07-part4-round6-planc2-bugfix-pair-validation]] — 6 bugs fixed, pair desc/tags validation, clone paired, picker hideActions, bulk toast, UC 58%→92%, Docker non-root, font self-hosted, FX fallback, classification race
- [[sources/phase07-part4-round6-planc2r2-regressions-mockfx]] — MockFX providers, auto-populate removal, DistributionEditor fix, contextual validate, end-of-day balance confirmation, 8 balance walk tests, 3 FX fallback tests, 3 asset classification E2E

**Created** (4 decisions):
- [[decisions/pair-description-tags-validation]] — linked pairs must have identical desc+tags
- [[decisions/auto-populate-removal]] — metadata flow frontend-driven (probe→diff→PATCH)
- [[decisions/formmodal-contextual-validate]] — FormModal sends entire bulk context to /validate
- [[decisions/end-of-day-balance-check]] — intra-day order irrelevant, end-of-day aggregation

**Created** (1 problem):
- [[problems/fx-multi-route-no-fallback]] — FX sync used only primary route, no fallback to ECB/FED/SNB

**Updated**:
- [[features/F-048]] — Plan C2/C2R2 entries in status history, contextual validate, clone paired, picker hideActions, bulk toast, balance walk, 4 new related_decisions
- index.md, raw/ingest-registry.md

**Verification of already-ingested plans** (8 files): All source pages for Round 6 ContextMenu, Plan A, Plan B, Plan B1, Plan B23, Plan B23 Appendix, Plan C, Plan C3 confirmed accurate with no contradictions. Plan C3 page verified — no updates needed (correctly documents PendingOp as successor to C2R2 work).

Key architectural progression documented: C2 (bugfix + pair validation + infrastructure) → C2R2 (MockFX + auto-populate removal + contextual validate + balance confirmation) → C3 (PendingOp tagged union).

## [2026-05-30] ingest | Phase 07 Part 4 Round 6 Plan C3 — PendingOp Refactor
Ingested from `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md`.
**Created**: [[sources/phase07-part4-round6-planc3-pendingop-refactor]], [[decisions/pendingop-tagged-union]].
**Updated**: [[features/F-048]] (PendingOp tagged union, factory functions, 3 new E2E tests, data-action-id), [[concepts/txstore-pattern]] (PendingOp model updated to final implementation), [[concepts/e2e-data-testid-rule]] (data-action-id pattern).
Key insight: DraftRow→PendingOp completes 80%→100% of txStore architecture. Zero-copy originals + tagged discriminator + derived status make Plan D (Split/Promote) trivial (~10 LOC per action). `data-action-id` establishes i18n-resilient E2E selectors for DataTable row actions.

## [2026-05-29] ingest | Phase 07 Part 4 Round 6 Plan C — txStore Refactor
Ingested from `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md`.
**Created**: [[sources/phase07-part4-round6-planc-txstore-refactor]], [[concepts/txstore-pattern]], [[decisions/txstore-single-source-of-truth]].
**Updated**: [[features/F-048]] (txStore as single source of truth, WorkspaceIntent pattern, PendingOp model, interface deduplication in types.ts, -30% LOC).
Key insight: 5 recurring bug categories (17+ instances) all rooted in 3-copy prop cascade; eliminated structurally by centralized store. Piano D (Split/Promote) now trivial.

## [2026-05-29] ingest | Phase 07 Part 4 Round 6 Plan B23 Appendix 1 — UI Polish
Ingested from `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB23_Appendix1_UIPolish.prompt.md`.
**Created**: [[sources/phase07-part4-round6-planb23-appendix1-ui-polish]].
**Updated**: [[features/F-048]] (structured delete toast, responsive footer buttons, row background tints, viewer-only guard on bulk actions, conditional "Reset all", "Reset selected" toolbar button).
Note: Execution order in master plan updated — old Piano C (Split/Promote) renamed Piano D; txStore refactor inserted as Piano C prerequisite.

## [2026-05-27] ingest | Phase 07 Part 4 Round 6 Plan B23 — Bulk Delete via BulkModal + Mode Removal
Ingested Plan B23 + 3 source files (TransactionBulkModal.svelte, TransactionDeleteModal.svelte, +page.svelte transactions).
**Created**: [[sources/phase07-part4-round6-planb23-bulk-delete]], [[decisions/bulkmodal-mode-removal]].
**Updated**: [[features/F-048]] (mode-less architecture, delete flow, enriched DeleteModal, PickerModal guard),
[[features/F-047]] (BulkDeleteLinkedPairModal removed, bulkMode state removed),
[[connections/transactions-connections]] (Round 6 status), [[domains/transactions]],
[[features/registry]] (F-048 title), index.md.
Key changes: (1) BulkDeleteLinkedPairModal eliminated — bulk delete now via BulkModal with `initialStatus:'delete'`;
(2) `mode` prop removed from BulkModal — now mode-less, each row infers create/edit from `tx.id > 0`;
(3) TransactionDeleteModal enriched: 3 layouts, validate-now, error banners with resolveIssueMessage, success toast with icons;
(4) PickerModal guard for non-editable rows; (5) Confirm edit on deleted row.

## [2026-05-27] query | AssetMatchingWizard / asset search / Phase 6 Step 5 status
Synthesized answer from: F-028, F-049, F-012, domains/assets, workflows/brim-import-flow, workflows/asset-onboarding-flow, connections/assets-connections, sources/phase06-step3-rounds, phase-06-assets.md plan.
**Key finding**: AssetMatchingWizard.svelte was never built — Phase 6 Step 5 is still ⏳. The component exists only in plans and wiki references but has zero source files in the codebase. AssetSearchAutocomplete.svelte (F-028) exists and works for asset creation, but the 3-step matching wizard (DB search → provider search → manual create) for BRIM import was interrupted before Phase 07 Part 4 bugfix rounds.

## [2026-05-26] file | SafeDecimal — Preventing Scientific Notation in JSON Responses
Filed [[concepts/safe-decimal-pattern]]. `SafeDecimal` is an `Annotated[Decimal, PlainSerializer]`
type that forces `format(v, 'f')` during JSON serialization, preventing Python's `str(Decimal)`
from emitting scientific notation (`"1.29E+5"`) which breaks frontend Zod validators.
3-layer approach: type definition in `common.py`, `Currency.amount` adoption, per-schema migration.
Incrementally adopted in brokers.py + transactions.py; prices.py/fx.py/brim.py still pending.
Updated: index.md.

## [2026-05-26] file | Static export of constant metadata at compile-time (deferred)
Filed [[decisions/static-metadata-export]]. Deferred to Phase 8+: extracting constant
metadata (TX_TYPE_METADATA, asset types, currency codes) as static JSON at `dev.py api sync`
time instead of serving via runtime endpoints. Current cost is 1 req/session — not worth
the sync-pipeline + store refactor effort until more constant-data endpoints accumulate.
Related: [[decisions/server-driven-type-rules]].

## [2026-04-25] lint | wiki-lint pass #5 — post Phase 7 Parts 1+2+3 ingest reconciliation

**Scope**: full health-check after Phase 7 Part 3 closure (backend coverage 87.06%,
2 production bugs filed, Policy D destructive wipe in place, new backup router,
ErasableNumberCell typing fix). Workspace HEAD = `a61b0dfa` (matches latest re-anchor
in `raw/ingest-registry.md`).

### Drift detection — ✅ clean

All 17 unique git-hashes in `raw/ingest-registry.md` resolve in current history.
Phase 7 sources (Parts 1/2/3 + Closure + Closure_2) re-anchored at `a61b0dfa` =
HEAD; `git diff a61b0dfa HEAD -- {phase07 paths} = 0 lines`. No source drift.

### Prioritized repair list

| # | Sev | Page | Problem | Action |
|---|-----|------|---------|--------|
| L5-01 | P0 | `connections/transactions-connections.md` | Header "Phase 7 — in progress (Part 1✅, Part 2✅, Part 3–5 TODO)" + 7-row gap table all stale; Parts 1–3 now ✅ DONE | rewrote header + replaced gap table with closed-gap table |
| L5-02 | P0 | `features/F-051.md` | Source files & layer breakdown referenced `Transaction.related_asset_event_id`; **code has `Transaction.asset_event_id`** (models.py L580/L659) | renamed all references to `asset_event_id`; updated status to `implemented`; added Policy D link |
| L5-03 | P0 | `domains/transactions.md` | F-051 row "planned"; "Known problems" still listed Phase 7 gaps as open (access control, multi-broker atomic, plugin_version) — all closed in Part 2/3 | updated F-051 row→`implemented`, rewrote "Known problems" to reflect closed gaps + add Policy D context |
| L5-04 | P1 | `problems/assets-wipe-error-attr-mismatch.md` | Reported 2 fixed sites; **a third sibling `e.code` reference still lives at `assets.py:976` (bulk_upsert_events)** — code wins → annotate as residual | added "Residual occurrence" section; flagged for code-side follow-up |
| L5-05 | P1 | `decisions/policy-d-currency-wipe.md` | Missing cross-ref to `features/F-073` (Backup & Restore) — backup endpoints belong to F-073 | added `F-073` to `related` + body |
| L5-06 | P1 | `entities/backup-router.md` | Missing cross-ref to `features/F-073` | added F-073 in `related` + body |
| L5-07 | P1 | `features/F-073.md` | No `related_decisions`/`related_problems`; doesn't mention Policy D or `entities/backup-router` | added related_decisions + cross-refs |
| L5-08 | P1 | `decisions/price-currency-hard-reject.md` | I.3 (409 on currency change with prices) doesn't link to its destructive successor Policy D | added "When the user accepts the 409" pointer + `related: policy-d-currency-wipe` |
| L5-09 | P1 | `problems/asset-currency-mismatch.md` | Older "per-row currency column" page — silent on the fact that I.2 hard-reject + Policy D now formalise a stricter model on top of it | added "Superseded-in-spirit" header + cross-refs to I.2/I.3/Policy D |
| L5-10 | P1 | `domains/assets.md` | No mention of Policy D destructive wipe or backup-router despite being the asset domain owner | added "Asset currency change (Policy D)" subsection + cross-refs |
| L5-11 | P2 | `wiki/features/F-049.md`, `F-047.md`, `F-046.md` | mostly current; only minor stale gap-analysis bullets — covered transitively by L5-01 / L5-03 | none (P2, deferred) |

### Index drift

`index.md` Problems/Decisions/Entities tables reflect the on-disk state correctly
post Phase 7 Part 3 ingest. F-051 status row was the only case where index
implicitly inherited the page's stale `in-progress` — now reconciled via L5-02.

### Orphan detection — ✅ none

Every wiki/* page is reachable from `index.md` directly or transitively
(domains → features → connections → decisions/concepts/problems). The 4 new
Phase-7 pages (`problems/assets-wipe-error-attr-mismatch`, `problems/babel-currency-symbol-echo`,
`decisions/policy-d-currency-wipe`, `entities/backup-router`) are all listed in
`index.md` and now also linked from at least 2 sibling pages each (post-L5).

### Contradiction scan — beyond fixes above

- `e.code` vs `e.error_code`: only the wiki had stale claims; current code
  uses `e.error_code` in the 2 wipe handlers. Residual `e.code` at line 976
  (bulk_upsert_events) is a **code-side latent bug** — annotated, not silently
  preserved (L5-04).
- "Soft-skip currency mismatch" appears nowhere in the wiki as the *current*
  behaviour — only as historical context inside `price-currency-hard-reject.md`
  and Part 3 source page (correctly framed as "old behaviour").

### Knowledge condensation

- Pages **rewritten in place**: 5 (transactions-connections, F-051, domains/transactions, asset-currency-mismatch, price-currency-hard-reject)
- Cross-ref additions: 6 pages received new `related:` + body links
- Sections added: 4 ("Residual occurrence", "Asset currency change (Policy D)" in domains/assets, "Superseded-in-spirit" in asset-currency-mismatch, "Closed Phase 7 gaps" in transactions-connections)
- Sections deleted: 1 (the now-misleading "Phase 7 Gap Analysis (from plan)" 7-row TODO table in transactions-connections)
- Pages deleted: 0 (all stale content was condensed/annotated, not removed — historical signal preserved with "Superseded" framing)
- Concept debt scanned: `editbuffer-pattern` (concept) + `data-editor-unification` (decision) overlap is intentional (mechanism vs rationale). FX-related concepts (`daily-point-policy`, `prices-current-side-effect`) and BRIM-related decisions (`brim-broker-scoped`, `brim-fake-asset-id`, `brim-parser-only`) cover distinct angles; no merges performed.

**Total touched**: 11 wiki pages + log.md + this entry. **0 new pages created**, **0 pages deleted**.

---

## [2026-04-24] lint | Lint pass #4 — Phase 07 contradictions + API URL audit

**Issues found**: 7 (4 high, 3 medium)
**Issues repaired**: 7

### 🔴 High — Repaired

1. **Contradiction**: `wiki/domains/transactions.md` said `POST /brokers/:id/transactions/bulk` and "atomic per broker / per-broker scoped" on 4 different lines. Real code (`tx_router = APIRouter(prefix="/transactions")`) has `POST /transactions/bulk` (multi-broker atomic). Fixed all 4 occurrences: prose, Mermaid node, Mermaid node label ("per-broker scoped"), key-decisions bullet. Also removed the ⚠️ "under active development" warning banner (F-046 is now implemented) and updated F-046 row status to `implemented`.

2. **Wrong API URLs**: `wiki/workflows/brim-import-flow.md` upload, list-files, and parse endpoints still referenced the old `/files/` router prefix. Real code: `brim_router = APIRouter(prefix="/import")` mounted under `broker_router(prefix="/brokers")`. Fixed: `POST /api/v1/brokers/import/upload?broker_id={id}`, `GET /api/v1/brokers/import/files?broker_ids={id}`, `POST /api/v1/brokers/import/files/{id}/parse`. Also corrected source-files reference from non-existent `files.py` to `brokers.py (brim_router)`.

3. **Missing file**: `wiki/sources/phase07-transactions.md` was indexed in `index.md` and `raw/ingest-registry.md` (hash `f17d963`) but the file did not exist (zombie entry from previous session). Created the source page from `plan-phase07-transaction-Part1.md`.

4. **Wrong enables**: `wiki/features/F-046.md` incorrectly listed `F-037` (Signal Library Framework) in `enables`. Signal Library depends on the asset detail chart area (F-033), not on the TX Bulk API. Removed F-037 from F-046 enables.

### 🟡 Medium — Repaired

5. **Malformed YAML + wrong cross-ref**: `wiki/features/F-037.md` had `depends_on: [F-046-area: PriceChartFull]` — invalid YAML (colon in value) and wrong F-code (F-046 is TX API, not a chart). Fixed to `depends_on: [F-033]` (Asset Detail Page chart/signals/editor is the actual dependency).

6. **Missing cross-ref**: `wiki/decisions/brim-parser-only.md` had no link to `[[decisions/brim-fake-asset-id]]`. Added a "Related decisions" section explaining that fake IDs are the mechanism that makes parser-only viable.

**Deferred (no action needed)**:
- `problems/asset-currency-mismatch.md` — already status `resolved`, no further action.
- F-047/F-048/F-049/F-050/F-051 status in transactions domain — Phase 7 is still in-progress for these features; left as-is.

## [2026-04-24] ingest | Created 11 domain cluster pages

**Pages created** (`wiki/domains/`):
- `auth.md` — Domain: AUTH (F-001–F-003)
- `layout-settings.md` — Domain: LAYOUT & SETTINGS (F-004–F-008)
- `brokers.md` — Domain: BROKERS (F-009–F-014)
- `fx.md` — Domain: FX Foreign Exchange (F-015–F-023)
- `assets.md` — Domain: ASSETS (F-024–F-036)
- `signals.md` — Domain: TECHNICAL ANALYSIS Signals (F-037–F-045)
- `transactions.md` — Domain: TRANSACTIONS (F-046–F-051) — status: in-progress
- `scheduler.md` — Domain: SCHEDULER (F-052–F-053) — status: planned
- `dashboard.md` — Domain: DASHBOARD (F-054–F-055) — status: planned
- `calculations.md` — Domain: CALCULATIONS (F-056–F-058)
- `infrastructure.md` — Domain: INFRASTRUCTURE (F-059–F-074)

**Updated**:
- `index.md` — added `## Domains` section with links to all 11 pages
- `wiki/features/registry.md` — added navigation note pointing to `wiki/domains/` for macro-level context

---

## [2026-04-24] ingest | Project bootstrap — codebase analysis

Sources analyzed: `knowledge_base/00_project_overview.md` @ git:`f17d963`, `RoadmapV4_UI/phases/00-index.md` @ git:`f17d963`, `plan-phase07-transaction-Part1.md` @ git:`f17d963`, `phase-08-scheduler.md` @ git:`66ad026`, `RoadMapV1/01-Riassunto_generale.md` @ git:`f17d963`, `backend/app/db/models.py` @ git:`f17d963`, `backend/app/api/v1/router.py` @ git:`f1205b7`.

Full codebase survey: backend API routes, services, providers (FX/Asset/BRIM), frontend routes, stores, components, mkdocs coverage.

**Created**:
- [[features/registry]] — 74 features across 11 domains with codes, status, mkdocs links
- [[features/F-012]] BRIM Framework
- [[features/F-019]] MANUAL Sentinel FX Provider
- [[features/F-020]] FX Currency Conversion Graph
- [[features/F-034]] Scheduled Investment Provider
- [[features/F-037]] Signal Library Framework
- [[features/F-056]] FIFO at Runtime
- [[features/F-059]] Provider Registry Pattern
- [[connections/dependency-graph]] — full project dependency graph
- [[connections/fx-connections]] — FX domain dependency map
- [[connections/assets-connections]] — Asset domain dependency map
- [[connections/transactions-connections]] — Transaction domain (Phase 7 gap analysis)

**Current project state**: Phases 0–6 complete, Phase 7 (Transactions) in progress (Part 1+2 done, Part 3–5 TODO), Phases 8–10 planned.


## [2026-04-24] init | devWiki initialized

Wiki structure created. SCHEMA.md, index.md, log.md bootstrapped.
wiki/ subdirectories: decisions/, entities/, concepts/, problems/, sources/.
Skills created: wiki-ingest, wiki-query, wiki-lint (historian agent); wiki-search, wiki-file (main agent).

## [2026-04-24] ingest | Conventions, changelogs, decisions — Phase 4–6

Sources: `knowledge_base/05_project_conventions.md` @ git:`957a124`, `changelog_2026-04-10_live-ticker-and-provider-lifecycle.md` @ git:`2c448cd`, `plan-fxSyncApiRedesign.prompt.md` @ git:`f123d4d`, `analysis-brim-multiuser.md` @ git:`84516e3`, `plan-data-separation.md` @ git:`f17d963`.

Created:
- Concepts: [[concepts/async-io-rule]], [[concepts/daily-point-policy]], [[concepts/single-migration-strategy]], [[concepts/backend-only-calculations]], [[concepts/dual-view-pattern]], [[concepts/svelte5-runes]]
- Decisions: [[decisions/fx-sync-pair-based]], [[decisions/brim-broker-scoped]], [[decisions/provider-shutdown-generic]], [[decisions/prod-test-data-separation]]
- Problems: [[problems/event-loop-blocking]], [[problems/liveticker-header-crash]], [[problems/flag-emoji-windows]]

## [2026-04-24] lint | First full lint pass

Issues found: 75 (62 systemic enables omission, 7 missing decision pages, 4 broken links, 2 misplaced files).
Fixes applied: moved 2 misplaced files, fixed 3 broken wikilinks, created 4 missing decision pages, populated `enables` field on all 74 feature pages, updated index.md.

## [2026-04-24] ingest | mkdocs developer docs + source file links

Read all English mkdocs developer pages (`mkdocs_src/docs/developer/`) to map features to actual source files.
Added `## Source files` tables to all 98 wiki pages (74 features, 6 concepts, 8 decisions, 3 problems, 4 connections, 1 entity, 1 source, 1 registry).
Updated historian agent and wiki-search skill with "source file linking" as a core rule.

## [2026-05-10] ingest | Phases 0–6 source files — bulk wiki creation

Sources ingested: phase-00-setup.md, phase-01-foundation.md, phase-02-backend-auth.md, phase-03-layout-settings.md, phase-04-brokers.md, phase-05-fx.md, phase-06-assets.md, phase-06-subplan Round12 (AssetEvent + ScheduleRedesign + MaturationEngine), phase-06-subplan Step4 PlanB (DataEditorUnification), plan-fxConversionChain.prompt.md, scheduled_investment.py, justetf.py, DataEditorTypes.ts, TimeSeriesStore.ts, fxStoreRegistry.ts, models.py (updated hash), Dockerfile, 04_devpy_reference.md.

Created decisions:
- [[decisions/sveltekit-over-react]] — V4 frontend stack choice
- [[decisions/zodios-api-client]] — type-safe API client
- [[decisions/single-docker-image]] — deployment architecture
- [[decisions/scheduled-investment-redesign]] — pure deterministic engine, AssetEvent table
- [[decisions/data-editor-unification]] — generic DataEditor component set

Created concepts:
- [[concepts/timeseries-store-pattern]] — gap-aware client-side time series cache
- [[concepts/editbuffer-pattern]] — DataRow status tracking in DataEditor

Created problems:
- [[problems/justetf-websocket-disconnect]] — silent WebSocket freeze, backoff workaround
- [[problems/asset-currency-mismatch]] — per-row PriceHistory.currency design rationale

Created entities:
- [[entities/db-models]] — full model table, enums, design notes (replaces old stub)
- [[entities/devpy-cli]] — CLI architecture, command groups, workflow commands

Created workflows (new wiki/ subdirectory):
- [[workflows/asset-onboarding-flow]] — create → provider → sync → view
- [[workflows/brim-import-flow]] — upload → detect → parse → match → commit

Updated feature status histories:
- [[features/F-001]] — Phase 0/1/2 details
- [[features/F-009]] — Phase 4 (45-day Broker CRUD phase)
- [[features/F-012]] — Phase 4 BRIM framework
- [[features/F-019]] — Phase 5 MANUAL sentinel
- [[features/F-020]] — Phase 5 FX Conversion Chain
- [[features/F-034]] — Phase 6 Round 12 redesign (added redesign entry + link to decision)
- [[features/F-037]] — Phase 5 initial + Phase 6 expansion
- [[features/F-059]] — Phase 1/4/5/6 registry extension history

Updated index.md: new decisions, concepts, problems, entities, workflows sections.

---

## 2026-05-10 — TODO Files Ingest & Feature Registry Expansion (F-075–F-095)

**Source**: `TODO_Completati.md` and `TODO_FUTURI.md` (project root)

### Task 1: Verified F-073 and F-050
- [[features/F-073]] (Backup & Restore): Status confirmed as `implemented` (partial). Per-series exports implemented; full portfolio export/restore are HTTP 501 placeholders. Wiki was already accurate.
- [[features/F-050]] (File Preview): Confirmed not started. Image preview via PreviewCache works; text/CSV/markdown not implemented. Status history updated.

### Task 2: Enriched existing feature pages
- [[features/F-008]] (i18n): Added 2-pass cleanup details (Phase 5: 724→590, Phase 6: 875→825 keys, 50 duplicates consolidated to `common.*`)
- [[features/F-014]] (Image Upload & Crop): Added cropperjs v2 rationale, key new files (ImageCropper, ImageEditModal, FileEditModal)
- [[features/F-061]] (5-layer Cache): Added FX Rate Cache (TTL 5min in `fx.py`) and Upload Metadata Cache (TTL 1h in `static_uploads.py`)

### Task 3: Registry expanded to F-095
Added Domain: PLANNED / IDEA FEATURES section with F-075–F-095 (21 new entries).

### Task 4: Created 21 feature pages
- [[features/F-075]] TanStack Table v9 Migration
- [[features/F-076]] Log Level Policy & TRACE Level
- [[features/F-077]] Mobile DataTable Touch Drag
- [[features/F-078]] User Filter in Files Page
- [[features/F-079]] GDPR Broker Access Compliance
- [[features/F-080]] Candlestick Chart / Volume Bars
- [[features/F-081]] Fiscal Sale Method (FIFO/LIFO/PMC/SelectID)
- [[features/F-082]] Cash Split Transactions
- [[features/F-083]] Multi-File Multi-Broker Import
- [[features/F-084]] Transaction Gain Chart
- [[features/F-085]] QuarkAI AI Assistant
- [[features/F-086]] Client-side Image Preview Cache (LazyImage)
- [[features/F-087]] Smooth Signal Line Style
- [[features/F-088]] Return-over-N Chart
- [[features/F-089]] FX Provider Per-Plugin Documentation
- [[features/F-090]] AssetEvent → Transaction Link (Enrichment)
- [[features/F-091]] Multi-Worker Cache Server
- [[features/F-092]] Default Language/Currency for New Users
- [[features/F-093]] Coupon Policy Field
- [[features/F-094]] Sync Date Range Dialog
- [[features/F-095]] Asset Delete Transaction Count Link

### Task 5: Created 2 problem pages
- [[problems/tanstack-svelte5-incompatibility]] — v8 adapter incompatible with Svelte 5 runes, custom adapter workaround
- [[problems/sync-functions-dead-code]] — sync wrappers removed as dead code; lesson: don't create unless immediate consumer

### Task 6: Created sources page
- [[sources/todos]] — documents both TODO files as continuous sources

### Task 7: Updated index.md, ingest-registry, log.md

---

## [2026-04-24] ingest | knowledge_base 03, 06, 07, 08

**Sources**: `knowledge_base/03_documentation.md`, `knowledge_base/06_testing_backend.md`, `knowledge_base/07_testing_frontend.md`, `knowledge_base/08_i18n_duplicates.md` — all @ git:`e8ab12a`.

### Created source pages
- [[sources/kb-03-documentation]] — MkDocs setup, Aphra v2 pipeline, gallery, documentation conventions
- [[sources/kb-06-testing-backend]] — Backend pytest architecture, _TestingServerManager, coverage, provider filtering
- [[sources/kb-07-testing-frontend]] — Playwright E2E patterns, fixtures, backend coverage SIGTERM architecture
- [[sources/kb-08-i18n-duplicates]] — i18n key rationalization principle, 42 duplicate groups

### Created concept pages
- [[concepts/mkdocs-suffix-i18n]] — Suffix strategy (`.en.md`, `.it.md`) for multilingual docs, ~36 source → 108 translated files
- [[concepts/backend-test-isolation]] — Each test creates own user via `unique_id()`, zero cross-test state
- [[concepts/e2e-data-testid-rule]] — ALWAYS use `data-testid`, NEVER CSS classes or text (i18n-safe, refactor-safe)

### Created decision page
- [[decisions/i18n-key-rationalization]] — Consolidate only when meaning+context+value match in all 4 languages; 42 groups (18 consolidated, ~30 accepted)

### Enriched feature pages
- [[features/F-067]] Playwright E2E Tests — added 2-project config, fixtures, backend coverage SIGTERM architecture, conventions, Linux deps
- [[features/F-068]] Backend API Tests — added _TestingServerManager details, mock data, coverage analysis, provider filtering, retry logic
- [[features/F-069]] MkDocs Multi-Language — added suffix i18n strategy, scope table, admonition blank line rule, gallery loader, style conventions, commands
- [[features/F-070]] Aphra LLM Translation Pipeline — added Aphra v2 architecture (shared analysis), 10-step cleaning, 13-dimension structural diff, cache, commands
- [[features/F-074]] E2E Test Gallery — added prerequisites (deterministic DB, Linux deps), output structure, viewport/theme/language loops, troubleshooting
- [[features/F-008]] i18n System — added two-pass cleanup stats, 42 duplicate groups, key namespaces table, CLI commands, reference docs

### Updated registries
- `raw/ingest-registry.md`: added 4 KB files @ git:`e8ab12a`
- `index.md`: added 3 concept pages, 1 decision page, 4 source pages
- `log.md`: this entry

## [2026-04-24] ingest | KB 01/02 backend+frontend, Phase06 Bugfix Steps 1/2/6

Ingested 7 source documents from Phase 06 development:

**Knowledge Base References**:
- `knowledge_base/01_backend.md` → [[sources/kb-01-backend]] — backend architecture overview
- `knowledge_base/02_frontend.md` → [[sources/kb-02-frontend]] — frontend architecture overview

**Phase 06 Plans**:
- Phase 06 Bugfix Migration Steps 1-3 → [[sources/phase06-bugfix-migration]]
- Phase 06 Step 2 Providers → [[sources/phase06-step2-providers]]  
- Phase 06 Step 2c Sync Refactor → [[sources/phase06-step2c-sync-refactor]]
- Phase 06 Step 6 i18n Polish → [[sources/phase06-step6-i18n-polish]]

**New Decisions Created**:
- [[decisions/three-phase-pipeline]] — PREPARE→FETCH→PERSIST pattern for bulk operations (fixes concurrent session commits)

**New Concepts Created**:
- [[concepts/responsive-4mode-layout]] — 4-breakpoint system (wide/tablet/tablet-s/mobile) for filter bar pages

**New Problems Documented**:
- [[problems/asset-sync-transaction-closed]] — SQLAlchemy concurrent commit error, resolved by 3-phase pipeline

**Key Insights**:
- 3-phase pipeline pattern is a **documented convention**, not a base class abstraction (FX and Asset implementations differ significantly)
- `tablet-s` breakpoint (500-770px) provides better UX for intermediate screen widths where neither tablet nor mobile layouts work well
- i18n duplicate consolidation reduced 18 groups (conservative approach, ~30 intentional duplicates preserved per context-aware rationalization principle)
- CSS Scraper and Scheduled Investment providers use `params_schema` for dynamic form generation
- SyncModalBase pattern extracted common sync modal logic (FX + Asset wrappers)
- TypeScript fixes: `getUserStorage` return type, `EditableNumberCell` min/max, lucide-svelte icon type compatibility

**Files enriched**: No existing feature/decision pages needed updates (all major patterns already documented).

**Registry updates**: Added 1 decision, 1 concept, 1 problem, 7 source pages.

---

## [2026-05-24] ingest | Phase06 Step3-rounds, Step4-PlanA, Step4-PlanC

Sources ingested: 14 plan files from Bugfix-Step3 (Rounds 1-11), 6 plan files from Bugfix-Step4 PlanA+Plan0, 5 plan files from Bugfix-Step4 PlanC. Git hash: `e8ab12a`.

All facts verified against source code before writing.

**Source pages created**:
- [[sources/phase06-step3-rounds]] — Step3 bugfix rounds 1-11: AssetModal, AssetSearchAutocomplete, ProviderAssignmentSection, ScheduledInvestmentEditor F9
- [[sources/phase06-step4-plana]] — Step4 PlanA+Plan0: asset detail page A1-A10, chart panel redesign, event markers, signal label unification
- [[sources/phase06-step4-planc]] — Step4 PlanC: FX-aware price queries C1-C5, multi-FX comparison, provider cache architecture

**Features enriched**:
- [[features/F-033]] Asset Detail Page — AssetModal implementation details, provider assignment section, full A1-A10 detail page, event markers, panel redesign
- [[features/F-034]] Scheduled Investment Provider — F9 editor: layout β, CellDateRange, contiguity engine, CRUD (Add/Delete/Split/Merge), bulk delete multi-gap, JSON ↔ form serialization, ui_component in params_schema
- [[features/F-037]] Signal Library Framework — signalLabel.ts utility, RenderedSignal enrichment (iconUrl/assetType/currency/currencyFlag), loadComparisonData.ts, MeasurePanel refactor, signal line styles by category
- [[features/F-042]] FX Pair Comparison Signal — staircase fix via null-gap filtering, currency labels in RenderedSignal, requiredFxPairs derived, FxStatusBanner, PageSyncAllModal
- [[features/F-020]] FX Currency Conversion Graph — C1-C5 FX-aware price queries: target_currency, OHLC scaling, dual staleness tracking, live ticker conversion, comparison overlays

**New decisions**:
- [[decisions/signal-label-unification]] — `signalLabel.ts` + enriched `RenderedSignal` as single source of truth for signal visual labels

**New problems**:
- [[problems/asset-list-500-provider-input-type]] — list_assets 500 on AUTO_GENERATED identifier type; fix: apply `map_input_type_to_identifier_type()` before building FAinfoResponse

**Skipped / not enriched**:
- F-035 (CSS Scraper): no new information in these plans
- F-036 (Provider Comparison Modal): no new information in these plans
- F-038/F-039/F-040/F-041 (individual signal pages): plan-partC_5 adds line style info to F-037 (framework), not individual signals
- F-060 (Thread Isolation): already well documented; plan-partC_7 confirms but adds no corrections
- F-061 (5-layer Provider Cache): already well documented with smart history range details

**Registry updates**: Added 3 source pages, 1 decision, 1 problem; enriched 5 feature pages; updated index.md and ingest-registry.md.

---

## [2026-04-24] ingest | TODO_FUTURI re-ingest + mkdocs developer pages mapping

**Task 1 — Re-ingest TODO_FUTURI.md**

Source: `TODO_FUTURI.md` @ git:`fcdd89e` (2026-04-17)

Comparison with existing registry F-075–F-095: all 21 features already documented from previous ingest (2026-05-10). Detected 1 NEW feature not yet in registry:

- **F-096** Scheduled Investment — Decoupled Frequencies (price vs coupon) + Anchor Day

**Created**:
- [[features/F-096]] — idea status, extends [[features/F-034]]

**Updated**:
- [[features/registry]] — added F-096 row, updated statistics (96 total features, 22 planned/idea)
- [[sources/todos]] — added F-096 to table

**Task 2 — Map mkdocs developer pages to features**

Systematically read all 68 mkdocs developer pages and mapped them to 36 features. Mapping hypothesis:

- **Architecture**: patterns (registry, async, alembic, config, plugin guides) → F-006, F-012, F-015, F-025, F-059, F-064
- **Database**: schema pages → F-001, F-002, F-009, F-016, F-030, F-046, F-064
- **Backend**: FX/Assets/BRIM architecture → F-012, F-013, F-015, F-016, F-017, F-018, F-019, F-024, F-025, F-026, F-027, F-031, F-034, F-035
- **API**: overview and testing → F-068
- **Frontend**: styling, i18n, state, components → F-001, F-004, F-005, F-008, F-009, F-011, F-020, F-071, F-072
- **Testing**: walkthrough pages → F-067, F-068
- **Docs/Tools**: translation pipeline, dev setup → F-063, F-070

**Updated 36 feature pages**:
- Frontmatter `mkdocs:` field — changed from `null` to primary mkdocs path (e.g., `"developer/backend/fx/architecture.md"`)
- `## Source files` table — prepended mkdocs rows (Primary mkdocs + secondary mkdocs pages for each feature)

**Coverage**:
- F-001, F-002, F-003, F-004, F-005, F-006, F-008, F-009, F-011, F-012, F-013
- F-015, F-016, F-017, F-018, F-019, F-020
- F-024, F-025, F-026, F-027, F-030, F-031, F-034, F-035, F-046
- F-059, F-060, F-063, F-064, F-067, F-068, F-070, F-071, F-072, F-096

**Pages with no feature mapping** (general infrastructure / UI library docs):
- `developer/api/overview.md`
- `developer/frontend/index.md`, `pages/index.md`, `components/index.md`, `components/data-table.md`, `components/live-ticker.md`, `components/select.md`
- `developer/frontend/components/ui-base/{atoms,datePickers,feedback,modals}.md`

**Registry summary after update**:
- 96 total features
- 62 implemented/documented
- 3 in-progress
- 31 planned/idea
- **36 features now linked to mkdocs developer pages** (up from 0 before this session)

## [2026-04-24] lint | Full reasoned lint pass #3

**Checks run**: thin pages, missing source sections, broken wikilinks, F-096 symmetry, registry vs files, mkdocs path validity, index orphans, log format, conceptual quality, connections currency.

**Issues found and fixed**:
- ✅ F-075–F-096: added full "Domain: PLANNED/IDEA" section to `registry.md` (22 features were counted in stats but had no individual rows)
- ✅ F-034 `enables:` updated to include F-096
- ✅ `## Source files` added to `problems/sync-functions-dead-code.md`, `problems/tanstack-svelte5-incompatibility.md`, `sources/todos.md`

**No issues found**:
- No broken wikilinks
- No orphan pages (all reachable from index.md)
- All mkdocs: paths point to real files
- Log format: all entries well-formed
- Thin pages: all under-25-line pages are planned/idea features (appropriate)
- Concept pages (daily-point-policy, backend-only-calculations, fifo-runtime-decision): substantive and accurate

## [2026-04-24] file | I-bis #24 v4 — `/prices/current` has a persistence side-effect
Filed lesson learned from final iteration of I-bis #24 (Auto-refresh mirato post-sync).
Root cause: `AssetSourceManager.get_current_prices_bulk` upserts today's OHLC to
PriceHistory (F.2 + F.3), so chaining `/current` + `/sync` for the same asset always
yields empty `changed_points` — the changes already happened on `/current`.
Created: [[concepts/prices-current-side-effect]] (cross-cutting API contract),
[[problems/prices-current-sync-chain-empty-delta]] (specific anti-pattern bug).
Updated: index.md (Concepts + Problems tables).

---

## 2026-04-24 — Phase 07 Part 2–3 Ingest (Transactions system final)

Ingested all remaining Phase 07 plan files (Part 2, Part 3, Closure, Closure_2 + BlockG).
This completes the documentation of the core transaction system architecture.

**Sources ingested (4 new source pages):**
- [[sources/phase07-part2-brim-revision]] — BRIM Revision 2 (parser-only)
- [[sources/phase07-part3-api-consolidation]] — multi-broker atomic TX, transfer semantics, currency simplification
- [[sources/phase07-part3-closure]] — Blocco I decisions, I-bis queue, #R6-4 scheduled investment wipe
- [[sources/phase07-part3-closure2]] — Batch 4 (saveWithRetry adoption), BlockG test coverage (76.05%)

**Decisions created (4):**
- [[decisions/brim-parser-only]] — BRIM is a parser; no commit endpoint, no asset events
- [[decisions/multi-broker-atomic-tx]] — bulk endpoints not broker-scoped, multi-broker atomic
- [[decisions/tx-link-uuid-semantics]] — TRANSFER/DEPOSIT/WITHDRAWAL link_uuid rules + promote endpoint
- [[decisions/price-currency-hard-reject]] — hard 400 on mismatch, 409 on currency change with prices

**Concepts created (1):**
- [[concepts/savewithretry-frontend-pattern]] — unified modal save helper adopted in 8+ modals

**Features updated:**
- [[features/F-012]] — BRIM Revision 2: parser-only, plugin_version, parse_is_stale, bulk_upsert_events rename
- [[features/F-046]] — status→implemented, multi-broker bulk endpoints, validate/suggest/promote
- [[features/F-049]] — commit via /transactions/bulk (not BRIM-specific), parse_is_stale UI
- [[features/F-051]] — status→in-progress, events/suggest endpoint documented

**Registry updated:**
- F-046: `in-progress` → `implemented`
- F-051: `planned` → `in-progress`

**Wiki page count**: ~176 pages (170 + 4 sources + 4 decisions + 1 concept - 3 from prev pass)

## [2026-04-25] ingest | phase07 Parts 1/2/3 — re-anchor + G-batch6/G-batch7 closure

Re-ingested Phase 7 Parts 1, 2, 3 (incl. Closure + Closure_2 + Batch4d + BlockG)
after the plans were archived from `RoadmapV4_UI/plan-phase07-transaction-Part*.md`
into `RoadmapV4_UI/phases/phase-07-subplan/Parte{1,2,3}/`. All Phase 7 Parts 1–3
are now ✅ DONE.

**Re-anchored sources** (path + git_hash → `a61b0dfa`, status → ✅ DONE):
- [[sources/phase07-transactions]] — Parte1/Part1.md
- [[sources/phase07-part2-brim-revision]] — Parte2/Part2.prompt.md
- [[sources/phase07-part3-api-consolidation]] — Parte3/Part3.md
- [[sources/phase07-part3-closure]] — Parte3/Part3_1_Closure.md
- [[sources/phase07-part3-closure2]] — Parte3/Part3_1_Closure_2.prompt.md (+ 3 companions)

**Delta surfaced** (new content not in previous ingest):
- Backend coverage **76.05% → 85.34% → 87.06%** in 2 days (G-batch6 + G-batch7); from ~57% at start of Phase 7
- 2 production bugs discovered by the new tests:
  - [[problems/assets-wipe-error-attr-mismatch]] — `e.code` → `e.error_code` (HTTP 500 → 404)
  - [[problems/babel-currency-symbol-echo]] — `normalize_currency` echoed garbage; strict pycountry lookup
- Policy D destructive wipe semantics formalised (commit `8fc018ab`):
  - [[decisions/policy-d-currency-wipe]] — created
  - Distinguishes from `#R6-4` selective wipe (manual events preserved there)
- New backup router `/api/v1/backup`:
  - [[entities/backup-router]] — created
  - Endpoints: `/backup/asset/{id}/{prices,events}` + `/backup/fx/{base}/{quote}/rates`
  - Replaces legacy `/assets/{id}/prices/export`
- I-bis #24 `changed_points` cap-500 + live-poll merge (commit `ddb1fcfb`) — refined in [[sources/phase07-part3-closure2]]
- ErasableNumberCell `$state<number | null>` fix (commit `83328b6b`) — captured in closure_2

**Files corrected** (previous ingest had wrong info):
- [[sources/phase07-part3-closure]] — old "R3-3 Policy D" line incorrectly claimed
  `/api/v1/system/{export,import}` as the backup. Replaced with the actual `backup.py`
  router + Policy D destructive wipe description.

**Cross-links added/strengthened**: F-012 (BRIM), F-046 (TX bulk), F-051 (TX↔AssetEvent),
F-056 (FIFO runtime — transaction preservation rationale), F-019/F-020 (FX),
[[entities/db-models]], [[entities/api-router]],
[[concepts/savewithretry-frontend-pattern]], [[decisions/price-currency-hard-reject]].

**Pages created**: 2 problems + 1 decision + 1 entity = 4 new wiki pages.
**Pages updated**: 5 source pages + index.md + ingest-registry.md.

---

## [2026-04-28] ingest | Phase 07 Part 4 — /transactions UI + Round 1 + Round 2

Sources:
- `plan-phase07-transaction-Part4.prompt.md` @ git:`dcb91929`
- `plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md` @ git:`444b2d16`
- `plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` @ git:`29898623`

Phase 7 Part 4 completes the `/transactions` frontend page (F-047 → **implemented**). Round 1 fixed 82+ issues across 14 sub-rounds, establishing 100% client-side filtering (W28 decision). Round 2 introduced `createEntityStore<T>()` factory, `brokerStore`, conditional pair-grouping, per-currency sliders, and `TxTypeIconCell`. F-048 Staging Modal moved from `planned` → **in-progress** (manual `create-many`/`edit-many` done; BRIM mode deferred to Part 5). Critical deviation: original plan had server-side filters on `GET /transactions` → replaced by full client-side filtering; `highlight_id` URL param removed in favour of DOM-direct pulse animation.

**Created**:
- [[sources/phase07-part4-transactions-ui]]
- [[sources/phase07-part4-round1]]
- [[sources/phase07-part4-round2]]
- [[concepts/entity-store-pattern]]
- [[concepts/always-pair-adjacent]]
- [[concepts/opportunistic-cache-merge]]
- [[decisions/transactions-client-side-filtering]]
- [[decisions/datatable-tooltip-custom-cell]]
- [[problems/svelte5-effect-read-write-loop]]
- [[problems/babel-currency-symbol-locale]]
- [[problems/datatable-filter-options-disappear]]

**Updated**:
- [[features/F-047]] (in-progress → implemented, full component inventory)
- [[features/F-048]] (planned → in-progress, manual mode done)
- [[features/registry]] (F-047/F-048 status rows)
- [[domains/transactions]] (F-047/F-048 status, Part 4 context)
- [[connections/transactions-connections]] (header + gap table Part 4 closure)
- index.md, ingest-registry.md

**Pages created**: 3 sources + 3 concepts + 2 decisions + 3 problems = 11 new wiki pages.
**Pages updated**: 5 existing pages + index.md + ingest-registry.md.

---

## [2026-04-28] lint | Wiki lint pass #6 — post Phase 07 Part 4 ingest

**Scope**: health check after Phase 7 Part 4 ingest (11 new pages, 7 updated). Focus: stale endpoint references, F-047/F-048 status drift, orphan pages, index drift.

**Issues found**: 4 (1 high, 2 medium, 1 low)
**Issues repaired**: 3 (1 high, 2 medium)
**Deferred**: 1 (low)

### 🔴 High — Repaired

| # | Page | Problem | Fix |
|---|------|---------|-----|
| L6-01 | `domains/brokers.md` (Mermaid line 47) | `POST /brokers/:id/transactions/bulk` in Mermaid diagram — **stale broker-scoped endpoint**. Actual endpoint since Phase 7 Part 3 is `POST /transactions/bulk` (multi-broker atomic). This was fixed in `domains/transactions.md` in Lint #4 but the Brokers domain Mermaid was missed. | Replaced with `POST /transactions/bulk` |

### 🟡 Medium — Repaired

| # | Page | Problem | Fix |
|---|------|---------|-----|
| L6-02 | `domains/brokers.md` "What comes next" | Described F-048 Staging Modal as entirely future work — stale after Phase 7 Part 4 delivered manual `create-many`/`edit-many` modes | Updated to note manual modes done, BRIM `create-brim` coming in Part 5 |
| L6-03 | `raw/ingest-registry.md` Round1 entry | `plan-phase07-transaction-Part4_Round1` shows 14-line drift at git `444b2d16`. The diff is trivial: successor link updated from planned placeholder name to actual Round2 filename. Content is accurate; the drift is purely metadata. | Annotated in source page (`phase07-part4-round1.md`) — no re-ingest needed |

### 🟢 Low — Deferred

| # | Page | Problem | Recommendation |
|---|------|---------|---------------|
| L6-04 | `features/F-049.md` | F-049 describes "Review staging" in the flow; doesn't mention that F-048 manual mode is now available as an alternative entry to staging for non-BRIM use | P2 — update F-049 in Phase 7 Part 5 when BRIM→staging flow is finalized |

### Drift detection summary

| Source | Hash | Lines changed | Assessment |
|--------|------|---------------|------------|
| `plan-phase07-transaction-Part4.prompt.md` | `dcb91929` | 0 | ✅ clean |
| `plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md` | `444b2d16` | 14 | ⚠️ trivial — successor link metadata only |
| `plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` | `29898623` | 0 | ✅ clean |

### Orphan check — ✅ none

All 11 new pages have inbound `[[links]]` from at least 2 other wiki files each (F-047, source pages, index.md, log.md, domain pages). No orphans.

### Index drift — ✅ none

No wiki pages missing from index.md (except individual F-00X feature pages, which are intentionally not individually listed — only notable ones appear under "Individual Feature Pages"). No dead index references found.

### Concept debt — ✅ satisfied by new pages

Terms that appeared 7–18× across wiki pages before this ingest now have concept pages:
- `entity-store-pattern` (18 occurrences) → [[concepts/entity-store-pattern]] ✅
- `always-pair-adjacent` (16 occurrences) → [[concepts/always-pair-adjacent]] ✅
- `opportunistic-cache-merge` (7 occurrences) → [[concepts/opportunistic-cache-merge]] ✅

`TxTypeIconCell` (6 occurrences) is a component name, not a pattern — documented in F-047. No concept page needed.

**Total touched**: `domains/brokers.md` (2 fixes) + log.md. **0 new pages created**, **0 pages deleted**.

## [2026-04-28] correction | Source-verified fixes — 4 factual errors corrected

Cross-checking all Phase 7 Part 4 wiki pages against actual source files (range: `fcdd89e8` → `2989862` HEAD). 4 factual errors corrected:

1. **`TxTypeIconCell.svelte` path** (F-047.md, sources/phase07-part4-round2.md): Missing `cells/` subdirectory. Fixed to `frontend/src/lib/components/transactions/cells/TxTypeIconCell.svelte`.

2. **TxTypeIconCell desktop interaction** (sources/phase07-part4-round2.md): Claimed "single click → open doc". Actual code: **double-click** (`ondblclick`) opens doc; single click shows tooltip only.

3. **assetStore loader endpoint** (concepts/entity-store-pattern.md, concepts/opportunistic-cache-merge.md): Examples used `apiClient.get('/assets/all')`. Actual: `zodiosApi.list_assets_api_v1_assets_query_get()` → `GET /assets/query`.

4. **Babel fix code** (problems/babel-currency-symbol-locale.md): Function signature was `list_currencies(locale: str)` (wrong). Actual: `list_currencies(language: str = "en")`. Code used `locale='en'` string; actual code uses `en_locale = get_babel_locale("en")` (a `babel.Locale` object), then `get_currency_symbol(code, locale=en_locale)`.

**Verified correct**: entityStore.ts API, brokerStore.ts API, isGrouped logic (TransactionsTable), DataTable fullData/onSortChange/getEnumOptionsWithCounts, capture-phase click (use:captureClick action).

**Files corrected**: F-047.md, sources/phase07-part4-round2.md, concepts/entity-store-pattern.md, concepts/opportunistic-cache-merge.md, problems/babel-currency-symbol-locale.md.

---

## [2026-05-25] file | Dual-Transaction Form — TransactionFormModal paired mode (R6-B.1–B.3)

Filed discovery: TransactionFormModal.svelte now supports paired transactions (FX_CONVERSION, TRANSFER_ASSET, TRANSFER_CASH) via a dual-form mode driven by `pairFormLayout` from `transactionTypeStore`.

**Created**:
- [[decisions/dual-transaction-form-design]] — design choices: single modal with From/To layout, Da/A sign-based detection on edit, swap normalisation, `collectDualCreates()` / `collectDualUpdates()`, client-side same-currency/same-broker validation

**Updated**:
- [[features/F-047]] — added TransactionFormModal to modal inventory + source files table; added `dual-transaction-form-design` to `related_decisions`
- `index.md` — added decision entry

Key implementation details captured: 3 layout modes (fx, transfer_asset, transfer_cash), `DualDraftTo` state type, partner auto-fetch in edit mode, 7 new i18n keys across 4 locales, type selector readonly in dual mode, advanced section hidden, tags/description shared across pair sides.

## [2026-05-25] ingest | Phase 7 Part 4 Rounds 3–5 (5 plan files)

Batch ingest of 5 Phase 7 Part 4 plan files covering the transaction modal system rewrite, i18n validation errors, unified batch pipeline, and server-driven type rules.

**Source files ingested** (git hash `133cb0d4`):
- `plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md`
- `plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md`
- `plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md`
- `plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md`
- `plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md`

**Created**:
- [[sources/phase07-part4-round3-staging-rewrite]] — three-component split (FormModal/BulkModal/PromoteWizard)
- [[sources/phase07-part4-round4-unified-pipeline]] — 4 endpoints → 2 with lenient parse
- [[sources/phase07-part4-round5-server-type-rules]] — transactionTypeStore + auto-sign + dual-form
- [[problems/pydantic-422-preemption]] — Pydantic 422 blocks service-layer validation (resolved)

**Updated**:
- [[sources/phase07-part4-round3-bugfix1]] — 5 walkthrough rounds, A1→A3→A4 pivot, field reset, unsaved-changes
- [[sources/phase07-part4-round3-bugfix2]] — structured error codes, PydanticCustomError, resolveIssueMessage
- [[features/F-046]] → title updated (Unified Batch API), layer→fullstack
- [[features/F-047]] → confirmed implemented, dual-form modals
- [[features/F-048]] → confirmed in-progress (R6-B items pending)
- `features/registry.md` — TRANSACTIONS domain: 3 implemented, 1 in-progress, 2 planned
- `index.md` — 2 decisions, 2 concepts, 2 problems, 5 sources added
- `raw/ingest-registry.md` — 5 new entries at `133cb0d4`

**Key decisions surfaced**:
- [[decisions/unified-batch-pipeline]] — already existed
- [[decisions/server-driven-type-rules]] — already existed

**Key concepts surfaced**:
- [[concepts/validate-scheduler-pattern]] — already existed
- [[concepts/resolve-validation-message-pattern]] — already existed

**Key problems surfaced**:
- [[problems/pydantic-422-preemption]] — new (resolved by unified pipeline)
- [[problems/browser-autofill-numeric-fields]] — already existed

## [2026-05-28] ingest | Phase 07 Part 4 Rounds 5-6 (8 plan files — Bugfix 1-3 + Round 6 Plans A/B/B1)

Batch ingest of 8 Phase 7 Part 4 plan files covering Round 5 Bugfix 1-3 and Round 6 Plans A/B/B1. Git hash: `0351d65f`.

**Source files ingested**:
- `plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` (re-anchored: R6-B expansion)
- `plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md`
- `plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md`
- `plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md`
- `plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`
- `plan-phase07-transaction-Part4_Round6_PlanA_ContextMenuBugfix.prompt.md`
- `plan-phase07-transaction-Part4_Round6_PlanB_DeletePickerAccess.prompt.md`
- `plan-phase07-transaction-Part4_Round6_PlanB1_BugfixRound1.prompt.md`

**Created** (6 source pages):
- [[sources/phase07-part4-round5-bugfix1-dual-form]] — CASH_TRANSFER, split/promote architecture, paired rendering
- [[sources/phase07-part4-round5-bugfix2-testwalk-overhaul]] — BulkModal readonly, "✓ Applica", dual dates
- [[sources/phase07-part4-round5-bugfix3-testwalk-fixes]] — PATCHABLE_FIELDS, type swap, TagInput, SafeDecimal
- [[sources/phase07-part4-round6-context-menu-delete]] — Round 6 master plan: ContextMenu, delete, picker
- [[sources/phase07-part4-round6-plana-context-menu-bugfix]] — ContextMenu + R7-C1/H1 fix + txPayloadHelpers.ts
- [[sources/phase07-part4-round6-planb-delete-picker-access]] — Broker access, DeleteModal 3 layouts, PickerModal, 48+ E2E tests

**Created** (3 decisions):
- [[decisions/cash-transfer-split-promote]] — CASH_TRANSFER first-class enum + split/promote immediate endpoints
- [[decisions/context-menu-all-tables]] — ContextMenu default ON on all DataTables
- [[decisions/broker-access-min-paired]] — Paired access = min(role_A, role_B) + 3-layout delete + partner_broker_id

**Created** (1 problem):
- [[problems/dual-form-collect-duplication]] — FormModal/BulkModal duplicated collect logic → txPayloadHelpers.ts

**Updated**:
- [[sources/phase07-part4-round5-server-type-rules]] — re-anchored at `0351d65f` (R6-B expansion)
- [[features/F-047]] — ContextMenu, asset clickable, description column, URL filter sync, broker access, soft reload, flat mode adjacency
- [[features/F-048]] — CASH_TRANSFER, split/promote architecture, PATCHABLE_FIELDS, type swap, TagInput, txPayloadHelpers, broker access gating, 3-layout DeleteModal, PickerModal, 48+ E2E tests, round 5-6 status history
- [[features/registry]] — F-048 title updated
- [[connections/transactions-connections]] — header updated with Round 5-6 achievements
- [[domains/transactions]] — F-048 feature cluster row updated
- `index.md` — 6 source pages, 3 decisions, 1 problem added
- `raw/ingest-registry.md` — 8 new entries at `0351d65f`

**Key architectural decisions surfaced**:
1. **CASH_TRANSFER** first-class enum (replaces VALID_MIXED_PAIRS hack); split/promote as immediate dedicated endpoints (schemas ready, backend endpoints in Plan C)
2. **ContextMenu** default ON on all DataTables (right-click + mobile long-press, zero consumer changes)
3. **Paired access = min(role_A, role_B)** — 3-layout TransactionDeleteModal (standalone/paired-full/paired-blocked); GET /brokers LEFT JOIN returning all brokers with user_role=null; partner_broker_id in TXReadItem
4. **txPayloadHelpers.ts** — shared utility eliminating 3 cascading bugs from FormModal/BulkModal logic duplication

**Pages created**: 6 sources + 3 decisions + 1 problem = 10 new wiki pages.
**Pages updated**: 7 existing pages + index.md + ingest-registry.md.

## [2026-06-17] ingest | Phase 09 Dashboard Batch
Source: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/` @ git:`24cdc40`.
Extracted concepts regarding Dashboard KPI, TWRR, MWRR algorithms, and FIFO lot tracking implementations.
Created: [[sources/phase09-dashboard-batch]], [[concepts/twrr-mwrr-algorithms]], [[concepts/fifo-lot-tracking]].
Updated: [[features/F-054]].

## [2026-06-17] ingest | Source Code v0.9.0 Batch
Source: Source Code @ git:`6d89b44`.
Ingested new source code implementations including Remotion Video Promo, MkDocs Pros/Cons Slider, and Gallery Overhaul.
Created: [[sources/source-code-v0.9.0-batch]], [[entities/video-promo-remotion]], [[concepts/interactive-pros-cons-slider]].

## [2026-07-01] lint | Full wiki health check — post Phase 7-9 ingest

Graph: 6399 nodes, 17688 edges, 366 communities. 1080 corpus files.
God nodes: Currency (426 edges), TransactionType (199), Transaction (166), User (158), Asset (152).
Issues found: 4 (1 high, 2 medium, 1 low).

Repaired:
- [HIGH] Dead link in `index.md`: `problems/pydantic-422-pre-emption` → `problems/pydantic-422-preemption` (typo fix)

Deferred (medium):
- Index drift: 20 wiki/features/ files not listed in index.md (F-001–F-074 gaps) — acceptable: index uses domains as navigation hub, not exhaustive feature list
- Concept debt: "Phase 07 Part 4" node cluster [5x] and "Multi-Broker Atomic Transaction Batch" [4x] without new concept pages — already covered by decisions/multi-broker-atomic-tx.md and source pages

Low:
- graph.html not regenerated (6399 nodes > 5000 threshold)

Next recommended: ingest Phase 10 / next development cycle when available.

## [2026-07-01] graphify | Incremental update — portfolio engine 3-pool refactor

Graph updated: 6514 nodes (+115 vs pre-update 6399), 17914 edges (+226), 411 communities.
Changed files: portfolio_engine.py (AST) + 8 mkdocs risk-metrics/WAC docs (semantic) + 6 new wiki pages.
False-deleted manifest paths (corpus/corpus/ double-prefix) ignored — full rebuild not needed.

## [2026-07-07] ingest | Phase 09 M1/M2 archive closeout (Holdings/Performance panel, verification pass)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/` (Milestone_1/, Milestone_2/ incl. `lowDashboard/`, `portfolio_engine/`, `Ai_consultant_engine/`, + 6 root cross-cutting docs) @ git:`1be3fc9c` (staged `git mv`, uncommitted at ingest time).
Milestone_3 (Broker UI v2) intentionally NOT archived — still in progress at old `phase-09-subplan/Milestone_3/` path.

This ingest is primarily a **closeout pass**: an exhaustive (non-sampled) verification against the current codebase found that ~20 items previously logged as "open" in `implementation_status_report.md` / `STATUS_REPORT_M2.md` / `ARCHITECTURE_CURRENT_STATE.md` (dated 2026-06-19/06-30) are now resolved by the Holdings/Performance refactor (commit `78aaa0a3`, 2026-07-06) and prior engine work (commit `39106380`, 2026-06-30): `get_summary()` wired to `PortfolioCalculationEngine`, `build_data_quality_report()` implemented, `first_position_date` present, GrowthChart stacked-area + rich tooltip, AllocationPanel Now/History toggle, DataQualityBanner unified field, TRANSACTION_IMPLIED fallback, tx double-click modal. ~7 items resolved *differently* than originally designed (architecture evolved) — recorded as [[decisions/portfolio-summary-direct-wiring]]. ~7 items remain genuinely open (low priority) — recorded in the source page and cross-linked from entity/domain pages. Per explicit user instruction, the MWRR "100x" result cap and Newton-only (non-Brent) solver choice are **deliberate design decisions, not bugs** — recorded as [[decisions/mwrr-solver-newton-cap]] with an explicit "do not record as a problem" note for future historians.

Also captured two genuinely open, unrelated pre-existing problems found during verification: a `test_transaction_implied.py` constructor-signature mismatch (6 failing tests, root cause confirmed via `pytest --junitxml`) and an unresolved `DataTable.svelte` column-resize click-no-effect bug (root cause not yet determined).

Created: [[sources/phase09-m1-m2-archive-2026-07]], [[concepts/holdings-performance-panel]], [[decisions/mwrr-solver-newton-cap]], [[decisions/portfolio-summary-direct-wiring]], [[problems/test-transaction-implied-constructor-mismatch]], [[problems/datatable-column-resize-noop]].

Updated: [[entities/portfolio-service]], [[entities/portfolio-engine]], [[concepts/twrr-mwrr-algorithms]], [[concepts/portfolio-report-unified]], [[sources/phase09-portfolio-engine-dashboard]], [[sources/phase09-portfolio-engine-3pool-refactor]], [[sources/phase09-dashboard-batch]], [[features/F-054]], [[features/F-055]], [[features/F-058]], [[features/registry]], [[domains/dashboard]], [[domains/calculations]].

Path corrections: fixed 8 files with stale `phase-09-subplan/Milestone_1|2` references (missing new `phases/` prefix introduced by the 2026-07-07 `git mv`) — [[decisions/mwrr-boundary-fix]], [[concepts/3-pool-cash-model]], [[concepts/pre-frame-frame-separation]], [[concepts/inline-wac-computation]], [[sources/phase09-portfolio-engine-3pool-refactor]], [[sources/phase09-portfolio-engine-dashboard]], [[entities/portfolio-engine]], [[sources/phase09-dashboard-batch]] (3 root-doc paths).

## [2026-07-07] graphify | Incremental update — Phase 09 M1/M2 archive closeout

Graph updated: 6527 nodes (+13 vs pre-update 6514), 18024 edges (+110), 381 communities (recomputed globally via Louvain — count not directly comparable to prior 411).
Scope: single semantic-extraction subagent chunk over the 23 wiki pages created/updated this ingest (6 new + 17 updated). 8 node IDs remapped to existing canonical IDs before merge to avoid duplicating already-modeled entities (`portfolio_engine_entity`, `portfolio_service_entity`, `decision_mwrr_boundary_fix`, `twrr_mwrr_algorithms_concept`, `portfolio_report_unified_concept`, `dashboard_document`, `f055_portfolio_charts`, `f058_roi_calculations_simple_dwr`).
Deferred (out of scope for this narrow update, left for a future full/incremental pass): semantic re-extraction of the 47 archived `phases/phase-09-subplan/` plan documents whose only change is the `git mv` path (content identical — these still show as "new" in manifest terms since their new path was never previously seen, but no new graph nodes are needed since content is unchanged); AST re-extraction of ~117 unrelated code files flagged as changed by `detect_incremental` (out of this session's scope). Manifest (`graphify-out/manifest.json`) stamped only for the 23 processed wiki files; as a side effect, `save_manifest`'s existing-entry reconciliation (root-relative re-anchoring) consolidated ~800 duplicate legacy absolute/relative key pairs and dropped 36 entries for genuinely-deleted/moved files — this is manifest hygiene, not a change to `graph.json`.
Community relabeling (Step 5, LLM-based) and `graph.html` regeneration (Step 6) skipped — graph exceeds the 5000-node HTML threshold and full community relabeling is out of proportion to a 23-file incremental update, consistent with the 2026-07-01 precedent.

## [2026-07-07] lint | Health check — post Phase 09 M1/M2 archive ingest

Graph: 6527 nodes, 18024 edges, 381 communities. 1125 corpus files.
God nodes unchanged from last lint (Currency 426, TransactionType 199, Transaction 166, User 158, BaseBulkResponse 155) — none are new-wiki-relevant.
New hyperedges from this ingest: "Dashboard Unified Report Flow", "Phase 09 Archive Closeout", "Portfolio Engine Refactor Core" — all EXTRACTED confidence 1.00, confirming the new pages integrated cleanly into existing clusters.
Issues found: 4 (0 high, 2 medium, 2 low) — all pre-existing, none introduced by this ingest.

Verified clean (explicit checks requested by user):
- No stale `phase-09-subplan/Milestone_1|2` (missing `phases/` prefix) references remain in any `wiki/` page or `index.md`. Only `raw/ingest-registry.md` and historical `log.md` entries still show the pre-move path — correct, since those are point-in-time git-hash snapshots from before the 2026-07-07 `git mv`.
- All 6 new pages have valid frontmatter, a `## Source files` table, and ≥4 inbound `[[links]]` — no new orphans.
- [[F-084]] (referenced from `domains/transactions.md`, `sources/todos.md`) not orphaned by the `domains/dashboard.md` rewrite — inbound links intact elsewhere.
- All `[[...]]` links in the 19 new/updated pages resolve to real files (bare `F-NNN` codes resolve to `features/F-NNN.md`).

Deferred (medium):
- **2 pre-existing orphan pages** (unrelated to this ingest): [[sources/phase07-part4-round3]] and [[sources/phase07-part4-round5]] — near-duplicate content of already-indexed, differently-slugged pages ([[sources/phase07-part4-round3-staging-rewrite]], [[sources/phase07-part4-round5-server-type-rules]]). Not linked from any other wiki page or from index.md. Recommend a future consolidation pass (merge or delete the duplicate slug).
- **Index drift**: 17 `wiki/features/*.md` files (F-001, F-003, F-004, F-008, F-009, F-014, F-015, F-023, F-024, F-036, F-045, F-046, F-051, F-052, F-053, F-056, F-074) not individually listed in `index.md` — same accepted pattern noted in the 2026-07-01 lint (index uses domains + Feature Registry as the navigation hub, not an exhaustive per-feature list).

Low:
- `graph.html` not regenerated (6527 nodes > 5000 threshold) — unchanged from prior lint.
- Concept debt (Interest, Dividend, Risk Metrics, TimeSeriesStore Pattern, Svelte 5 Runes Convention, "Phase 07 Part 4" cluster, "Multi-Broker Atomic Transaction Batch") — all pre-existing, already deferred in the 2026-07-01 lint as acceptable (covered by existing decision/source pages).

Not repaired this pass (deferred, low priority, unrelated to the requested ingest scope): the 2 orphan sources and the 17 unlisted feature pages.

Next recommended: a dedicated dedup pass on `sources/phase07-part4-round3.md` / `sources/phase07-part4-round5.md`; ingest Milestone 3 (Broker UI v2) once it completes.

## [2026-07-13] file | Full test suite green-up session
Ran `./dev.py test --fresh-run all` / `--resume all` to green the entire suite (14/14
categories). Filed three new problem pages for the cross-cutting infra/contract bugs found
along the way, and corrected the pre-existing [[problems/test-transaction-implied-constructor-mismatch]]
page (its proposed "signature-only" fix was verified empirically to not work — the WAC-as-price
fallback was actually removed, not renamed).
Filed: [[problems/pytest-exit-swallows-failures]], [[problems/resume-mode-stale-import]],
[[problems/brlistresponse-contract-drift]].

## [2026-07-15] ingest | Phase 09 M3 archive (Broker UI v2 redesign, chart-resolution/semantic-zoom)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/` (+ root
`implementation_plan.md` and 3 superseded pre-v2 designs) @ multiple git hashes (see `raw/ingest-registry.md`
— `git mv` archive, staged/uncommitted at ingest time, same pattern as the 2026-07-07 M1/M2 closeout). This
completes Phase 9 fully: all 3 Milestones now archived under `phases/phase-09-subplan/`.

Milestone 3 redesigns the Broker pages (global list + 3-tab detail) to reuse the unified `/portfolio/report`
widgets built in M1/M2, plus a cross-cutting chart-resolution/semantic-zoom workstream (7 impl plans + 1
study, written in parallel by a fleet of agents). All sub-plans verified ✅ design · ✅ implementation plan ·
✅ implemented (no open items). Key content: `GET /portfolio/asset-history` regression found-and-restored
(commit `3184a969` → `1a734008`); `GET /brokers?include_inaccessible=true` opt-in discovery; sharing icon
read-only for EDITOR/VIEWER/non-members (was OWNER-only); `BrokerBreakdown.cash_balances` added natively for
per-card NAV/Gain/quota% without N+1 calls; inline multi-broker FIFO lots panel (UI/display layer over the
existing `GET /portfolio/lots` engine output, no engine changes); daily→weekly→monthly semantic-zoom
bucketing (`timeSeriesAggregation.ts`) now shared across price/growth/allocation charts and 9 signal
overlays, plus a static compact-card variant with no interactive resolution switching.

**Explicit exclusion honored**: `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/` (== the symlinked
`LibreFolio_devWiki/corpus/roadmap/fifo-engine/`) was deliberately NOT read, summarized, or linked from any
page in this pass, per user instruction — it is a separate, still-open FIFO/WAC/transfer engine-internals
investigation ("Analisi tecnica completa... Domande aperte e raccomandazione", 2026-07-14), unrelated to this
UI redesign and not yet ready for ingest (no decision taken yet).

Created: [[sources/phase09-m3-broker-redesign-2026-07]], [[concepts/chart-resolution-semantic-zoom]],
[[entities/time-series-aggregation]], [[decisions/broker-list-visibility-non-members]],
[[decisions/broker-card-aggregation-no-n-plus-one]], [[problems/portfolio-asset-history-regression-restored]].

Updated: [[domains/brokers]] (UI v2 redesign summary + 2 new decisions linked), [[domains/dashboard]] ("M3 in
progress, not archived" note resolved; source-file paths corrected), [[entities/portfolio-engine]] (History
row for the M3 archiving milestone).

Also refreshed, as part of the archive move itself (not a separate wiki page): two stale "codice in working
tree non ancora committato" notes in `Milestone_3/README.md` (git status confirmed both already committed),
and flagged (not fixed, out of scope) a pre-existing broken link in the same file
(`GUIDA-TOOLBAR-RESPONSIVE.md` vs. the actual `GUIDA-TOOLBAR-RESPONSIVE-v2.md` on disk) plus two unrelated
pre-existing dangling links in `phases/phase-09-dashboard.md` pointing at documents later relocated by
earlier phase-07/phase-08 archiving passes (`plan-phase05-to-08-upgrade.md`,
`plan-WacInlineValidateCommit.prompt.md`) — none caused by this session's edits, left as noise per convention.

Per plan: the skill's own final `graphify --update` step was skipped here — superseded by a full
from-scratch graphify rebuild run immediately after the post-ingest lint pass (see following log entries).

## [2026-07-15] lint | Health check — post Phase 09 M3 ingest (pre-rebuild)

Graph (pre-rebuild, unchanged from 2026-07-07): 6527 nodes, 18024 edges, 381 communities, 1125 corpus files —
run intentionally BEFORE the full graphify rebuild per plan, so cheap file-based checks fix issues before the
costly rebuild processes the final state once. Graph-based checks (god nodes, high-degree gaps) therefore
still reflect the pre-ingest graph — the 6 new M3 pages aren't graphed yet; expected, not a defect. God nodes
unchanged from the 2026-07-07 lint (`Currency` 426, `TransactionType` 199, `Transaction` 166, `User` 158,
`BaseBulkResponse` 155) — all pre-existing code entities, none newly relevant to this ingest.

File-based checks on the 6 new + 3 updated pages from this ingest: **all clean**.
- Orphans: 0 — every new page has 3-5 inbound `[[links]]` (verified programmatically).
- Index drift: 0 — all `wiki/**/*.md` files are listed in `index.md`.
- Broken `[[wikilinks]]`: 0 introduced by this ingest (checked all 1537 wikilinks across 322 wiki files).

Issues found: 2, both pre-existing and unrelated to this ingest (deferred, not auto-repaired, following the
same scoping precedent set in the 2026-07-07 lint for the 2 unrelated orphan sources found then):
- `wiki/sources/kb-01-backend.md` → `[[concepts/provider-registry-pattern]]` — target page does not exist.
- `wiki/sources/phase06-step4-planc.md` → `[[problems/sync-pairs-bulk-none]]` (×2) — target page does not
  exist.

Carried over from the 2026-07-07 lint, still not repaired (unrelated to this ingest, same as before): the 2
near-duplicate orphan sources ([[sources/phase07-part4-round3]], [[sources/phase07-part4-round5]]) and the 17
`wiki/features/*.md` pages not individually listed in `index.md`.

Next recommended: full graphify rebuild (this session, immediately following); a dedicated pass on the 2
newly-found broken links + the carried-over dedup/index-drift items above, whenever a general wiki-cleanup
session is scheduled (not part of this ingest's scope).

## [2026-07-15] file | AI export prompt catalog

Filed the AI export rework done this session: single "Full/Data-only" prompt replaced by a 6-entry
single-purpose prompt catalog (Snapshot, PAC Planning, Rebalancing, Market Trend, Income Review,
Describe Portfolio) plus a new single-asset export (Asset Detail Signals panel button). Also fixed a
real bug where several call sites used ticker/ISIN as the primary asset label instead of `name`.
Filed: [[decisions/ai-export-prompt-catalog]], [[problems/ai-export-name-not-ticker]].

## [2026-07-16] update | graphify full incremental rebuild (9 days of drift)

Ran `/graphify --update` on the devWiki corpus for the first time since 2026-07-07 — picked up 154
changed files (42 code, 109 document, 3 image) across this session's AI export work AND other
concurrent work (a "donation popup" feature: `donation_popup_service.py`, `DonationPopupModal.svelte`,
`donationPopupStore.svelte.ts`; new mkdocs financial-theory pages on risk metrics — Sharpe/Sortino/
max-drawdown/volatility/WAC; several dashboard chart component tweaks). 8 genuine deletions pruned
(stale audit/working files already archived into `phase-final-subplan/`).

**Bug found and worked around** (library issue, not a devWiki content problem): `graphify`'s
`detect_incremental()` auto-detects `follow_symlinks` based on whether the **scan root's direct
children** are symlinks. This corpus's symlinks (`corpus/backend`, `corpus/roadmap`, `corpus/wiki`,
etc.) sit one level *inside* `corpus/`, not at the devWiki root — so calling
`detect_incremental(Path('.'))` (the natural root, matching the original build) auto-detected
`follow_symlinks=False` and silently skipped ~1100 files, while the *first* attempt using
`Path('corpus')` as root (which does have direct symlinked children) tripped a separate manifest
re-anchoring bug (`_to_absolute_from_storage` double-prepends the root when manifest keys were saved
relative to a *different* root than the one passed in) that misreported **1052-1079 real files as
deleted**. Neither call was safe as-is. Fix: always call `detect_incremental(Path('.'),
follow_symlinks=True)` for this corpus, and re-saved `manifest.json` via `save_manifest(files,
root=Path('.'))` using that same combination, so future `--update` runs are self-consistent (verified:
a repeat `detect_incremental` immediately after now reports 0 deletions).

Graph: 6527→6850 nodes, 18024→20236 edges, 381→283 communities (labeled all 283 by hand from
top-degree node samples). Re-ran token benchmark (114.4x reduction) and regenerated `graph.html`/
`GRAPH_REPORT.md`/`graph.json`. HTML viz note: graph now exceeds the 5,000-node auto-viz cap, so
`graph.html` reflects the last run under that cap — regenerate manually via Obsidian export if a fresh
interactive view is needed.

Not filed as a dedicated wiki page (this is graphify tooling/process bookkeeping, not
LibreFolio-product knowledge) — recorded here in the log only.




## [2026-07-20] file | Docker System Info fix + macOS entrypoint GID collision
Fixed Settings → About "Copy for Issue" showing `App Version: unknown` and empty
Backend/Frontend Dependencies when running from the Docker image (root cause: `.git/`,
`Pipfile`, and `frontend/package.json` were never copied into the runtime-only image).
Mirrored the existing `requirements.txt` generated-artifact pattern with a new `VERSION`
file written fresh by `dev.py` before each `docker build`. Bonus fix: `parse_pipfile()`
regex couldn't match quoted Pipfile keys, so "Borsa Italiana Scraping" was invisible in
Backend Dependencies in *both* environments. Added a new `deployment_mode` field
(docker/local) plus 6 new About-tab diagnostic fields (viewport, DPR, browser UA, theme,
language) with full i18n. While verifying the Docker fix, discovered and flagged (not
fixed, per user's own-review-first workflow preference) a separate, still-open bug:
`entrypoint.sh`'s `chown` fails on macOS hosts because GID 20 (macOS default first-user
GID) collides with Debian's pre-existing `dialout` group, so `groupadd -g 20 librefolio`
silently no-ops and the literal group name never exists.
Filed: [[problems/docker-system-info-missing-deps]], [[problems/docker-entrypoint-gid20-collision]].
Graph updated (scoped, not a full rebuild): +2 nodes, +3 edges (both new problem nodes
cross-reference each other and [[decisions/single-docker-image]]); 6850 pre-existing nodes/edges/
communities left untouched. Manifest stamped only for these 2 files. Deferred: 126 unrelated
files still show as changed in `detect_incremental` (concurrent uncommitted work — mkdocs
restructuring, chart components, DataTable, etc., none of it mine) — left for a dedicated full
catch-up pass, same precedent as the 2026-07-01 entry above.

## [2026-07-22] ingest | FIFO Engine v4 — FEE/TAX Integration

Ingested the completed `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/` plan chain (6 feasibility drafts,
4 high-level-design drafts, implementation plan, recap, review checklist, post-implementation review — 14
files, ~450KB) plus the 4 parent `fifo-engine/` background docs. This is the plan behind the mkdocs
`fifo-lot-analysis.en.md`/`fee.en.md` translation-alignment work done earlier in this same session. Read via
a dedicated extraction subagent (post-implementation-review-v5/recap/checklist/hig-level-analysis-v5/
feasibility-v4.1/implementation-plan-v5 read in full; earlier drafts skimmed only for rejected pivots).

Summary: v4 moved dividend/interest/FEE/TAX allocation into the FIFO domain via one canonical
`FifoLotEngine.run()` path (the old service-level income allocator was deleted, not left coexisting). Income
eligibility tightened to D-1, broker-scoped, transfer-aware. Asset-linked FEE/TAX route through distinct
deterministic matching ladders (FEE trade-centric, TAX income-first); assetless costs never enter FIFO at all.
Net metrics are always gross minus allocated costs, gross math untouched. Portfolio-Engine-side reconciliation
was deliberately deferred as separate, higher-risk future work.

Created: [[sources/fifo-v4-fee-tax-integration]], [[decisions/fifo-v4-income-eligibility-d1]],
[[decisions/fifo-v4-cost-allocation-ladder]], [[decisions/fifo-v4-engine-architecture]],
[[decisions/fifo-v4-gross-net-status-model]], [[decisions/fifo-v4-validation-and-scope]],
[[entities/fifo-lot-engine]], [[entities/lots-analysis-service]], [[concepts/d1-income-eligibility-window]],
[[concepts/deterministic-cost-matching-ladder]], [[concepts/asset-orphan-vs-portfolio-level-cost]],
[[concepts/gross-net-dual-reporting]], [[problems/datatable-net-columns-hidden-override-model]],
[[problems/transaction-update-bypassed-sign-validation]],
[[problems/fifo-income-silently-dropped-after-full-close]].

Updated: [[entities/portfolio-engine]] (deferred-reconciliation note), [[concepts/fifo-lot-tracking]] (v4
evolution note), `wiki/features/registry.md` (F-056 mkdocs column).

**Drift found and fixed** (not part of the plan itself, discovered while cross-linking): [[decisions/fifo-runtime-decision]]
and [[features/F-056]] both referenced `backend/app/services/transaction_service.py` as "the FIFO engine" —
verified stale via `grep -c fifo` across the three candidate files (`fifo_lot_engine.py` and
`lots_analysis_service.py` are the real FIFO code now, `transaction_service.py` only has 2 incidental mentions).
Corrected both pages' source-file tables and added a dated correction note rather than silently rewriting
history.

Next recommended: full `graphify --update` (immediately following, same session) to absorb these 18 new/updated
wiki pages plus the outstanding backlog explicitly deferred in the 2026-07-20 entry above (126 files) and this
session's mkdocs translation-alignment changes (fee.en.md/fifo-lot-analysis.en.md + it/fr/es).

## [2026-07-22] update | graphify full incremental rebuild (18 devWiki pages + 214-file backlog catch-up)

Ran `/graphify --update` on the devWiki corpus, catching up the entire backlog deferred since 2026-07-20 (126
files) plus this session's own changes: `detect_incremental(Path('.'), follow_symlinks=True)` reported 214
changed paths (89 unique documents once `corpus/wiki/*` vs `wiki/*` symlink duplicates were manually deduped
to 194 real files, 125 code). Dispatched 10 parallel semantic-extraction subagents (chunked by directory,
~20 files each) alongside AST extraction on the 125 code files; merged into the existing graph via
`G_existing.update(G_new)` (no deletions this round).

Graph: 6852→8276 nodes (+1424), 20239→23731 edges (+3492), 283→325 communities (325 re-labeled: ~20 hand-crafted
for the FIFO/wiki-relevant clusters, the remaining ~225 sizable ones auto-labeled via a top-degree-node
heuristic — lower quality than a full hand pass but functional; flagged as a candidate for a future dedicated
labeling session). `graph.html` NOT regenerated — graph now exceeds the 5,000-node auto-viz cap (was already
noted as an open item from the 2026-07-16 entry; still open, use Obsidian export if a fresh interactive view is
needed). Token-reduction benchmark: 61.7x. Manifest re-saved via `save_manifest(files, root=Path('.'))` for all
1617 corpus files, matching the follow_symlinks/root fix documented in the 2026-07-16 entry (verified
self-consistent going forward).

Notable new structure confirms the ingest landed correctly: dedicated hyperedges for "FIFO v4 FEE/TAX design
decisions", "FIFO v4 economic-allocation concept cluster", "FIFO v4 post-implementation review bug fixes", and
"FIFO runtime implementation surface" (the last one linking the corrected [[decisions/fifo-runtime-decision]]/
[[features/F-056]] to the new [[entities/fifo-lot-engine]]/[[entities/lots-analysis-service]] — confirms the
drift fix is graph-visible). Also surfaced code-level structure not part of this ingest: BRIM broker-provider
family clusters (`Cashless Crypto Adjustment Importers`, `BRIM CSV Import Provider Family`, etc.) and a
`Column Visibility Override Ecosystem` hyperedge matching the DataTable bug fix pattern.

**Known limitations of this run** (methodology notes, not content problems):
- Per-agent token usage wasn't available the way native graphify tooling exposes it, so `cost.json` recorded
  0 input/0 output tokens for this run — cost tracking is under-counted from here, not accurate.
- A handful of near-duplicate node IDs exist for the same real entity across different subagent chunks (e.g.
  `F_056` vs `wiki_features_F-056`) — cosmetic, matches an existing pre-ingest pattern already flagged
  elsewhere in the report as "surprising connections", not fixed.
- `graphify`'s own `graph_diff()` helper compares the full old graph against only the incremental extraction
  (not the full merged graph), so its "nodes/edges removed" output is not a real deletion count in `--update`
  mode — only its "new_nodes"/"new_edges" figures are meaningful here (used above); this is a re-confirmation
  of a diff-methodology quirk, not a new bug.

## [2026-07-22] lint | Health check (post-ingest)

Ran the wiki-lint workflow immediately after the ingest above.

**Graph analysis**: God nodes unchanged in kind (`Currency`, `TransactionType`, `Transaction`, `User`, `Asset`
still top 5) but `BRIMParseError`/`BRIMParseOutput` newly entered the top 10 (162/137 edges) as a direct result
of this update's BRIM-provider semantic pass. Surprising connections list unchanged from before this ingest
(same 5 pre-existing INFERRED pairs) — no new surprising/dubious edges introduced by this ingest's own content.

**🔴 High priority**: none found specific to this ingest.

**🟡 Medium priority**:
1. **Orphan pages (81 total, pre-existing, not introduced by this ingest)** — corrected the orphan-check
   script's own bug first (the literal `grep "\[\[$slug\]\]"` bare-slug pattern from the skill undercounts,
   since `wiki/sources/` and `wiki/entities/` pages are conventionally linked with the qualified
   `[[category/slug]]` form). With a basename-aware check, genuine orphans are ~81, concentrated in
   `wiki/sources/*.md` (44 — mostly by design, linked only from `index.md`'s Sources table, consistent with the
   2026-07-15 lint's precedent of treating this as accepted) and `wiki/domains/*.md`/`wiki/connections/*.md` (9,
   likely the same pattern). Higher-signal subset worth a future pass: 7 orphaned `wiki/problems/*.md` pages
   (`justetf-websocket-disconnect`, `sync-functions-dead-code`, `pydantic-422-preemption`,
   `pytest-exit-swallows-failures`, `coverage-mode-stale-import`, `coverage-report-category-dest-collision`,
   `brlistresponse-contract-drift`), 3 orphaned `wiki/decisions/*.md` (`port-6040-scheme`,
   `provider-shutdown-generic`, `static-metadata-export`), plus `wiki/entities/devpy-cli.md` and
   `wiki/concepts/responsive-4mode-layout.md`. None of this ingest's 15 new pages are orphaned.
2. **Drift-registry false positives** — the standard `git diff {hash} HEAD -- {path}` drift check flagged 91
   sources as ">5 lines changed", but 82 of those are `git mv`-archived plan files (Phase 06/07 → `phases/`
   subfolders) where the recorded ingest hash predates the move, so git shows a spurious 100% "new file" diff
   at the archived path — not real content drift. Refined check (excluding new/deleted-file-mode diffs) finds
   only **9 genuine in-place stale sources**, most notably `backend/app/services/asset_source_providers/justetf.py`
   (211 lines changed since hash `e8ab12a`), `.../scheduled_investment.py` (190 lines) and
   `frontend/src/lib/stores/fxStoreRegistry.ts` (183 lines) — all three worth a dedicated re-ingest/refresh pass;
   `backend/app/db/models.py` (47 lines, 2 registry rows) is a smaller but recurring one worth checking against
   `wiki/entities/db-models.md`. `README.md`/`Dockerfile`/`TODO_FUTURI.md`/`phases/00-index.md` also flagged but
   are expected-to-churn living documents, not concerning.
3. **Concept debt (pre-existing, sampled pre-update)**: recurring un-paged concepts from `conceptually_related_to`
   edges include "Semantic Zoom Chart Resolution" (15×) and "MWRR as XIRR" (10×) as the most citable candidates
   for a dedicated `wiki/concepts/` page in a future session.

**🟢 Low priority**:
4. Index drift: none — every `wiki/**/*.md` page is already referenced in `index.md` (checked all 340 pages).
5. Near-duplicate node IDs for the same entity (`F_056` vs `wiki_features_F-056`) noted above under the
   graphify update entry — cosmetic only.

**Repairs executed as part of this pass**: none beyond what the ingest above already did (the drift/orphan
findings are reported for a future dedicated session, consistent with the deferral precedent set in the
2026-07-01/2026-07-16/2026-07-20 entries above — this pass's own scope was the FIFO v4 ingest, not a general
wiki cleanup).

Next recommended: (a) re-ingest/refresh the 3 genuinely-stale backend/frontend sources above; (b) a dedicated
orphan-linking pass for the 7 problem + 3 decision pages listed above; (c) hand-relabel the ~225 auto-labeled
communities from this update if/when the graph is used for browsing rather than query.

## [2026-08-04] update | graphify scoped semantic refresh (1 wiki decision page)

Scoped graph refresh for the three files changed by the ai-export-contextual-ui-memory wiki-file operation
(`wiki/decisions/ai-export-contextual-ui-memory.md`, `index.md`, `log.md`). Only one of the three is tracked
by graphify (`wiki/decisions/ai-export-contextual-ui-memory.md`; the wiki-root `index.md`/`log.md` are outside
`corpus/` and are not graphify-tracked files).

**Context**: `detect_incremental(Path('corpus/'))` reported 246 pending files (214 code + 32 documents) — an
accumulation of unrelated changes. Running `graphify --update` over all 246 would process unrelated pending
files; instead, this entry documents the minimum scoped patch to clear only the three task-relevant files.

**Semantic change in `wiki/decisions/ai-export-contextual-ui-memory.md`**: The decision title was updated from
"AI Export drafts persist per authenticated user and UI context" to "AI Export drafts use short-lived session
memory", reflecting the 2026-08-04 cutover from durable `localStorage` to a ten-minute sliding TTL in
tab-scoped `sessionStorage`. The four sub-decision sections (Reactive Identity-Bound Memory, Raw-Note /
Effective-Option Separation, Context-Bound In-Flight Preparation, Concern-Based E2E Cutover) retain their
headings. Source-location line ranges for all four sub-nodes were re-anchored to the new file layout
(L40-L59, L60-L65, L66-L71, L72-L76). All 7 external edges from the root node were preserved unmodified
(references to auth domain, AI Export snapshot service, AI Export versioned snapshot boundary, prompt catalog,
phase-00 source, clipboard fallback problem; INFERRED link to mkdocs Contextual AI Export Draft Memory).

**GRAPH_REPORT.md** updated: one label occurrence ("…persist per authenticated user…" → "…use short-lived
session memory…") in the Surprising Connections section.

**Manifest**: `wiki/decisions/ai-export-contextual-ui-memory.md` hash updated
(old semantic_hash `8061c1eb3e63976909956a705ec7d837` → new `26a4af3fc31511790a2ffdf0bd61a348`,
mtime 1785774139.88 → 1785870347.51).

Graph: **1533→1533 nodes** (±0), **2255→2255 edges** (±0), **144→144 communities** (±0).
Remaining pending after this refresh: **245** (unrelated; will be processed in a future full `--update` pass).

## [2026-08-31] file | Consolidation campaign — five discoveries

Closing a campaign that fixed sixteen pinned defects across settings, broker
sharing, the scheduler and FX. Five findings were filed because each cost real
time to reach and would cost it again:

- **A false green nobody could have seen coming.** Five tests asserted on the
  string `$_()` returns while looking like they asserted on i18n keys. They were
  green *only because the keys were untranslated* — `svelte-i18n` echoes a
  missing key — and went red in the commit that added the translations, blaming
  the translator for a defect written weeks earlier.
  Filed: [[problems/i18n-key-assertion-false-green]].

- **`page.route()` is per context, not per suite.** An E2E asserted a global
  price count reached zero, stubbing every writer in its own browser context.
  But `PriceHistory` has no `user_id`, so other workers wrote the row anyway —
  217 commits of "14 row(s) written/updated" in the backend log of the failing
  run. Passing in isolation proved nothing.
  Filed: [[problems/playwright-route-stub-is-per-context]].

- **The scheduler's defect was the conversion point, not the model.** Days and
  times stored in UTC could not be displayed in another zone without lying about
  the weekday. Storing in the configured zone and converting once, at the
  decision, removed the defect by construction *and* stopped DST from moving jobs
  by an hour twice a year. The proposed `(day, time)` redesign was unnecessary.
  Filed: [[decisions/scheduler-converts-at-decision]].

- **Zero is not an exchange rate.** An absence was travelling with the shape of a
  datum from the API boundary onward, drawing collapses to zero in charts and a
  reachable −100 % delta. Widening the type *first* let `svelte-check` enumerate
  40 sites across 7 files — more than the manual estimate, and it found two
  consumers the survey had missed.
  Filed: [[concepts/absence-sentinel-vs-nullable-type]].

- **A near-miss in a shared component.** Fixing the FX chart gap set
  `connectNulls: false` globally, which would have inverted every overlay in the
  application; overlays had been `true`. Caught by asking who else passes through
  the file, not by a test — no test would have caught it.
  Filed: [[problems/shared-component-option-changed-globally]].

Suite at filing time: 15/15 green in 46m 55s, lines 78,02 %, branch arms
59,45 %, backend 90,18 %.

> **Provenance added 2026-09-01.** `90,18 %` is **lines + branch arms — the same
> formula as the 90,10 %** quoted elsewhere in the campaign, not a third scale. It is
> the `TOTAL` row of `htmlcov-backend/index.html`
> (`37085 / 2810 / 11048 / 1719`) from the final validation run of 2026-08-31:
> `dev.py test --fresh-run --coverage all --cov-clean-js --cov-clean-backend
> --cov-clean-backend-e2e --workers 8 all`. The distance from 90,10 is two successive
> measurements with the scheduler work and its tests in between, not a change of
> definition.
>
> **`92,33 %` is the only pure-lines figure in the campaign.** Comparing it with
> 90,18 compares two formulas — the error documented in
> [[problems/coverage-percent-mixed-lines-and-branches]]. Within the mixed set
> (90,10 · 90,46 · 92,40 · 90,18) the figures are comparable to each other.
>
> The frontend pair is comparable to its neighbours (78,07/59,39 and 78,13/59,53 at
> the two recorded checkpoints). Worker counts for the **earlier** figures remain
> **not reconstructible**; for this one it is known and recorded above.
> See [[sources/coverage-campaign-2026-08]] § Caveats.

---

## [2026-08-31] ingest | Consolidation campaign — 13 session plans + the 2026-08-05 beta testing folder

**Sources**: 14 untracked plan/history files from the session state directory
(`plan-p7-js-coverage`, `plan-p8-runner-migration`,
`plan-p9-test-semantics-COMPLETO`, `plan-tappe-7-11-parallelismo-COMPLETO`,
`tappa9-desleep`, `plan-storico-coverage-campaign` and `-2`,
`plan-storico-fase012`, `plan-storico-corsie-sync-e-logica`,
`coda-beta-parametrici-forkserver`, `difetti-aperti-corsia-impostazioni`,
`plan-storico-corsia-impostazioni-COMPLETO`,
`plan-storico-undici-difetti-COMPLETO`, plus
`plan-storico-scheduler-e-fx-COMPLETO` found in the directory but absent from the
supplied inventory) — and four files from
`LibreFolio_developer_journal/Release_2/Phase_0/06_betaTestingReportAndFixing/`
(`571bcde0`, `6eac0225`), a folder never ingested before.

**Created — 31 pages.**

*Concepts (9)* — the runner's execution model and the vocabulary the campaign
needed to read its own numbers: [[concepts/test-isolation-classes]],
[[concepts/derived-test-inventory]],
[[concepts/run-cache-and-campaign-semantics]],
[[concepts/playwright-run-consolidation]],
[[concepts/transaction-hygiene-fixture]],
[[concepts/load-only-red-is-a-product-defect]],
[[concepts/coverage-rate-vs-volume]], [[concepts/characterisation-test-latch]],
[[concepts/discard-the-answer-not-the-question]].

*Problems (11)* — five of them share one property worth naming: they produce
**no signal at all**. Empty coverage files, unreachable test actions, an env var
that yields a default instead of an error, a cache that stops caching, a barrel
nobody imports. [[problems/svelte-template-branches-not-instrumented]],
[[problems/coverage-percent-mixed-lines-and-branches]],
[[problems/e2e-python-coverage-lost-above-two-workers]],
[[problems/registered-but-unreachable-test-actions]],
[[problems/conftest-autouse-write-breaks-pure-class]],
[[problems/brim-file-store-rename-race]],
[[problems/commit-reported-success-on-rolled-back-batch]],
[[problems/utc-today-vs-user-calendar]],
[[problems/namedcache-clear-leaves-admission-filter]],
[[problems/env-var-injection-point-duplicated]],
[[problems/bulk-validate-index-map-off-by-one]].

*Decisions (2)* — [[decisions/settings-write-path-contract]] (C1-C9 as one
contract: confirm late, show the wait, never lose a field) and
[[decisions/broker-last-owner-guard]] (recorded precisely because the obvious
five-minute repair is the wrong one).

*Sources (9)* — [[sources/p7-js-coverage-instrumentation]],
[[sources/p8-runner-parallel-architecture]], [[sources/p9-test-semantics]],
[[sources/frontend-parallelism-tappe-7-11]],
[[sources/coverage-campaign-2026-08]],
[[sources/coverage-fase012-and-branch-lanes]],
[[sources/settings-lane-and-sixteen-defects]],
[[sources/coda-beta-parametric-forkserver]],
[[sources/beta-testing-2026-08-05]].

**Updated — 7 pages.**
[[concepts/backend-test-isolation]] now carries a superseded-in-part warning: its
"parallel-safe, no cleanup required" claim is contradicted by a single-process
run that produced three `UNIQUE constraint failed` failures, and by the fact that
56 test files share one SQLite file against 16 using `:memory:`. Not repaired —
flagged. [[decisions/test-runner-package-split]] gained a History section: 18
modules/12 categories/~115 actions has become 31/15/219, and the decision was not
reversed but built upon. The five pages filed by hand a few hours earlier gained
`See also` blocks linking them into the new material, without rewriting them.

**Not ingested, deliberately**: the ten `plan-phase00*.prompt.md` execution plans
in the beta folder (operational, and their durable content lives in the taxonomy
or in existing `phase00-*` pages), plus the non-prose artefacts in the session
directory (`draft-*.ts`, `collect_pass.py`, `drift_check.py`, `spec_class.txt`,
screenshots, a compressed log).

**Correction, same day.** The two cases named as "four workers revealed a
user-facing bug" were not in the session plans — they are in
`.github/agents/test-author.agent.md` (~538-552) and
`.github/skills/devpy-tools/testing-frontend/SKILL.md` (~313). They have been
written into [[concepts/load-only-red-is-a-product-defect]] in their true form:
`AssetSearchAutocomplete` dropped a query typed before the provider list loaded —
at one worker the providers *always* won the race, so the defect was not rare but
**unobservable**, and the suite was green for months on a dead search box; and
`useValidateScheduler` sampled its anti-bounce key when the response *arrived*
instead of when the request *left*, so an edit made during a pending validation
was marked already-validated and never re-checked. Four tests always red under
load, always green alone, always the same four — the exact signature people
dismiss as flaky.

The `resolveOps` / `buildOpsIndexMap` off-by-one that had been placed there
provisionally was **not** a load-only red: it was found statically by the
pure-logic lane. Split out into
[[problems/bulk-validate-index-map-off-by-one]].

**index.md**: 267 → 298 unique links (273 → 304 table rows).

**Not run**: `graphify --update` — deferred to the maintainer, after the lint
pass, so the ~1 280-file queue is processed once.

---

## [2026-09-01] lint | Health check after the 2026-08-31 consolidation ingest

**Scope**: 400 wiki pages, 439 index links, 1 828 source-file paths cited in
`## Source files` tables, 454 manifest entries, graph built on 100 files.

**The finding that dominates every other**: the wiki's navigation layer is
broken against the current tree. **144 of the 1 828 cited source paths (7,9 %)
point at files that do not exist.** 85 of them are files that *moved* — the
frontend `stores/`, `utils/` and `components/transactions/` trees were regrouped
on **2026-06-05** (`99144b67`, `ee84e078`) and the backend financial utils on
**2026-06-10** (`79ea14e5`) — and 59 name files that exist nowhere under any
name. **23 of the 38 pages written or touched by the 2026-08-31 ingest** contain
at least one such path, i.e. the ingest transcribed plan-era paths that were
already three months stale when it wrote them.

**Verified against the code, contradicted**:
- `concepts/backend-test-isolation` — `unique_id()` does **not** combine
  timestamp + UUID4. `backend/test_scripts/test_utils.py:180` returns
  `f"{prefix}_{int(time.time()*1000)}_{_counter}"` with a **process-global
  counter**. The page's parallel-safety argument rests on a mechanism that is
  not in the code. The superseded-warning added by the ingest does not say this.
- `decisions/test-runner-package-split` — the History added by the ingest says
  31 modules / 15 categories / 219 actions. Code: **30 modules, 15 categories,
  250 `add_test()` call sites**. It also says the flat `_backend_*` /
  `_frontend_*` layout "was reorganised around an `actions/` package" — that
  package does not exist; the flat layout is still there.
- `entities/test-runner` — the directory tree, the `@registry.register`
  decorator and the `suites/` package it documents do not exist. Not touched by
  the ingest despite three new concept pages on the same package.
- The `:memory:` / shared-file counts in the ingest's own warning (16 / 56) are
  **7 / 36** in the tree today (195 test files total).

**Repaired (mechanical only)**: `features/registry.md` was missing **F-048**,
the most-linked feature page in the wiki (43 inbound links); 2 broken
`[[links]]`; 6 broken frontmatter refs (`phase07-part4-round4-pipeline`,
two nested-bracket typos, `responsive-layout-strategy`,
`three-phase-pipeline-pattern`, `sync-modal-base-pattern`). Broken `[[links]]`
now **0**.

**Duplicates found (pre-existing, not from this ingest)**:
`sources/phase07-part4-round3` ≡ `sources/phase07-part4-round3-staging-rewrite`
and `sources/phase07-part4-round5` ≡ `sources/phase07-part4-round5-server-type-rules`
— same `original_path`, same title modulo "Phase 07"/"Phase 7", ingested twice
(2026-05-25 and 2026-05-28). Both older copies are orphans and absent from
`index.md`. Merge deferred: it is a judgement call about which slug survives.

**Deferred, needs a decision**: the `unique_id` reconciliation (owner of the
fixture); whether `entities/test-runner` is rewritten or retired; the
`decisions/fx-triangulation` and `assert-on-identity-not-prose` references that
name pages nobody ever wrote; `index.md` carries 58 duplicate rows across its
"Recent Additions" sections.

**Also noted, not corrected on purpose**: `.github/copilot-instructions.md:155`
claims the graph has 9 259 nodes / 14 151 edges / 748 communities. The current
`GRAPH_REPORT.md` says **1 617 / 2 277 / 167**, built from 100 files. Left for
the maintainer to fix after the rebuild, so the number is written once.

**Not run**: `graphify --update` — the ~1 280-file queue stays with the
maintainer.

## [2026-09-01] tooling | check_source_paths.py

Il lint ha trovato **144 path su 1 828 (7,9 %)** citati nelle tabelle `## Source
files` puntati a file inesistenti, e la ripartizione contava più del totale: 85
erano deriva databile da tre refactor di giugno, 59 non esistevano da nessuna
parte, **4 erano inventati**. E 23 delle 38 pagine scritte il giorno prima ne
contenevano almeno uno — quindi non invecchiamento, ma trascrizione di path
presi dai piani senza confronto con l'albero.

Nessuna delle tre classi sopravvive a un controllo di esistenza su filesystem, e
**nessuna era visibile al grafo**, che copre ~4 % del codice: una query BFS
risponde parzialmente e sembra completa.

Aggiunto `check_source_paths.py`, che verifica ogni path citato. Dopo le
riparazioni: **41 rotti su 2 016 citati (2,0 %)**, da 7,9 %. Va eseguito **prima**
di scrivere una pagina, non sei mesi dopo.

Aggiornate anche le istruzioni di progetto: il numero di nodi del grafo era fermo
a 9 259 contro i ~1 617 reali, e ora rimandano a `GRAPH_REPORT.md` invece di
riportare una cifra destinata a invecchiare. Con l'avvertenza che conta: il grafo
è affidabile sulla conoscenza accumulata, **cieco sul codice**.

## [2026-09-01] lint | code-reality-check.md marcato superato

Generato il 2025-05-24, afferma *«Alembic: 1 sola migrazione — conforme alle
istruzioni "no incremental migrations"»*. Le istruzioni oggi impongono l'**opposto**:
migrazioni incrementali per non rompere le installazioni rilasciate. Una pagina
che verifica la conformità al codice e sbaglia sulla regola più delicata è essa
stessa deriva. Avviso in testa, non riscritta: serve come fotografia del maggio
2025, non come verifica.

## [2026-09-02] file | Drawdown full_history warmup (decision)

Consolidamento beta P4/E1: il drawdown ha memoria illimitata — `full_history` param
sul segnale (toggle UI, default on), AI Export sempre full; documentato perché il
seed SQL del max pre-periodo è FX-unsafe (max(convertita) ≠ convertita(max)).
Filed: [[decisions/drawdown-full-history-warmup]].

## [2026-09-02] file | CompactCashCell decimal separator feedback loop (problem)

T1: l'`$effect` di sync confrontava stringhe di display e sovrascriveva il buffer
mid-typing (`12,` → `12`); fix = confronto numerico normalizzato. Include la trappola
`isVisible({timeout})` che non attende (emersa con il tooltip delay T2).
Filed: [[problems/compactcashcell-decimal-separator-feedback-loop]].

2026-09-03 — P1 audit wave executed (all 18 tasks): C901 gate@10 (199 sites triaged: 173 flat noqa, 26 TODO-refactor), TRY400 55/55, dead code backend+frontend, i18n -25 keys, currency-graph dead machinery removed (user hypothesis confirmed), response_model ×6 + TS discriminator fix (enum extra + post-processor list), spawn-worker coverage via sitecustomize. Filed: [[problems/sitecustomize-shadows-homebrew-python]] (PYTHONPATH sitecustomize shadowing Homebrew's → pipenv broken; chain-exec fix). WS-H migration proof: published 1.0.1 image → current image on same volume, both data migrations verified correct.

## [2026-09-09] update | Group E import and bulk UX reconciliation
Reconciled the broker-scoped upload decision and import knowledge against the integrated
code after Group E. Corrected the multipart upload route, single-broker-per-file Generic
CSV boundary, positive high fake IDs, explicit asset resolution, full inspector PATCH
semantics, final duplicate recheck, guarded bulk handoff, and E7/E8 stable-row diagnostics
with display-only chronological sorting.
Updated: [[decisions/brim-broker-scoped]], [[decisions/brim-fake-asset-id]],
[[decisions/brim-parser-only]], [[entities/import-wizard-modal]],
[[workflows/brim-import-flow]], [[features/F-012]], [[features/F-049]],
[[features/F-083]], [[decisions/import-wizard-v5-paradigm]], and
[[features/F-011]], [[features/F-013]], [[concepts/import-todo-signals]],
[[domains/transactions]], and [[features/registry]].

## [2026-09-05] file | Asset Global laboratory — the no-money rule and three verified traps

Mandate F of the Risk Analysis replan rewrote the Asset Global correlation surface.
`wiki-search` found **zero** prior pages on Asset Global, correlation or the heatmap,
so the session's findings had no home to be added to.

Filed the governing invariant — no position, exposure or portfolio impact in money on
a page whose subject has no weights — together with the reason its obvious test is
worthless: the euro there is *latent, not present*, so "assert no `€` on screen" passes
because the backend sends no numbers and would keep passing with every guard deleted.
The guard is a net that stubs money **in**.

Also filed three traps verified against code, not inherited from the plan: `front check`
is blind to `e2e/**` and born red without `api sync`; the generated client's TS type for
`RiskMatrixCell.value` contradicts its own Zod validator; and the ASSET_SET scope has no
primary series, which cancelled a planned KPI-column deliverable rather than faking it.

Filed: [[decisions/asset-global-page-shows-no-money]],
[[problems/front-check-does-not-check-what-you-think]],
[[problems/generated-client-widens-nullable-scalar]],
[[problems/asset-set-scope-has-no-primary-series]].

## [2026-09-18] file | Risk request ordering and test-id grep false negatives
Mandate F's E2E round produced two failures whose causes were both *the observer*, not the code: a
correlation stub indexed by chip order while `riskRequest.ts` canonicalises `asset_ids` ascending, and a
`grep -c` on a composed test id reported a selector deleted when the primitive still emits it.
Filed: [[problems/risk-request-sorts-asset-ids]], [[problems/testid-grep-false-negative]].

## [2026-09-23] file | Workstream F — the R2-101 debt, and three pages the code had overtaken
Workstream F (Asset Global laboratory) paid the devWiki debt S5 declared in R2-101 — three pages
deferred on 18/09 rather than reopen a frozen tree — and updated three pages that the code had
overtaken. Sources: `REGISTRO.md` (R2-62, R2-66, R2-96, R2-98, R2-100, R2-101, R2-112), S5's and F's
plans, the 22/09 sheets 08 §8.8 and 09 §1.6/§3.11/§3.12/§9.1/§9.2; every claim re-checked against
`f1047f766`.
Filed: [[problems/discarded-risk-answer-read-as-empty]] (R2-101's boot identity–query race: the
three-outcome defect and its fix hold; the recorded boot trigger — "the `(app)` layout has no auth
guard" — is contradicted by the layout, so the page says so), [[concepts/span-as-a-detector]],
[[problems/tab-writes-after-the-look]].
Updated: [[decisions/asset-global-page-shows-no-money]] (frontend guards since 18–21/09; the net is
blind under global privacy and is pinned off until J repairs the risk formatter),
[[problems/asset-set-scope-has-no-primary-series]] (per-asset analytics delivered 21/09 by `d3afb92b6`
and `032b86959`; open → resolved), [[problems/testid-grep-false-negative]] (recurrence on 23/09;
resolved → recurs).
Graph: the graphify `--update` is **deferred** — `graphify-out/graph.json` and `.graphify_python` do not
exist in this worktree. `check_source_paths.py`: 0 missing paths on the six pages.

## [2026-09-25] file | Workstream F — the lab redesign (F-3b): eligibility, heatmap emphasis, three gotchas
Lessons from the four-hands redesign of the Asset Global laboratory and the Risk → F merge (`2c02ff070`).
Filed: [[decisions/lab-eligibility-from-risk-engine]] (the verdict is Risk's; parked chips; the two meanings of
"mine"), [[decisions/heatmap-emphasis-is-hue-free]], [[problems/echarts-canvas-mismeasures-emoji-labels]],
[[problems/tooltip-click-pins-over-modal]], [[problems/popover-pointerdown-swallows-click]] (red first, then fixed).
Updated: [[concepts/mkdocs-suffix-i18n]] (an app link's anchor must exist in all four languages; the risk-metrics
index anchors exist in English only), [[concepts/portfolio-report-unified]] (holdings-only callers ask for the light
report), [[concepts/test-isolation-classes]] (a single `api` action after `services` finds the lane empty),
[[decisions/asset-global-page-shows-no-money]] (the redesigned card keeps the rule).
Graph: the graphify `--update` is **deferred** — `graphify-out/graph.json` and `.graphify_python` do not exist in this
worktree. `check_source_paths.py`: 0 missing paths on these nine pages (60 pre-existing elsewhere).

## [2026-09-29] file | Flag emoji on Windows — the global flags-only face
The developer turned the per-container `.emoji-flag` rule into one global face, `'LF Flags'`, whose unicode-range
covers only the regional indicators: Apple flags on Apple devices, the self-hosted Noto flags subset elsewhere,
every other character on its usual font. The page records the new solution, why the old "not globally" rule fell,
and how to verify it without Windows.
Filed: [[problems/flag-emoji-windows]] (updated); [[domains/layout-settings]] (its known-problems line aligned).

## [2026-10-07] file | Workstream O — the i18n audit, and the svelte-i18n formatter cache
The Release 2 i18n audit found the usage audit wrong in both directions (118 live keys reported dead, the whole
`risk.*` namespace absolved by a single-literal parameter type, tests counted as evidence) and a svelte-i18n
4.0.1 cache keyed on message text only, which leaks plural rules across locales after an in-place switch. Both
fixes are filed with their gates; the catalogue went from 4 356 to 4 186 keys per language.
Filed: [[problems/i18n-audit-false-dead-and-false-used]], [[problems/svelte-i18n-formatter-cache-ignores-locale]].
Graph: the graphify `--update` is **deferred** — `graphify-out/graph.json` and `.graphify_python` do not exist in this
worktree.

## [2026-10-07] update | Workstream O — the i18n audit, second pass on the release tip
On `d07412899` (dashboard and risk work merged) the audit still read 78 live keys as «not verified» and let a
component nobody imported prove five keys. Five rules closed that: one import hop for narrow families, reachability
from the SvelteKit entries (keys only unreferenced sources keep alive are listed under 📦), generated API clients
out of the walk, backend codes in any spelling or starting with a digit, and multi-slot template shapes. Result:
0 dead and 3 not verified, all live; a fourth (`onboarding.settings.groups.contextual`) only a per-key check
proved dead, and it was removed with the batch.
Updated: [[problems/i18n-audit-false-dead-and-false-used]].
Graph: the graphify `--update` is still **deferred** — no `graphify-out/graph.json` in this worktree.

## [2026-10-07] file | Workstream P — one average-cost function in a financial_math layer (decision)
Release 2 workstream P answered issue #32 without a patch. The developer chose one generic average-cost function,
`compute_average_costs()`, in a new service layer `backend/app/services/financial_math/` whose rule is that a
calculation owns its whole problem and calls the services it needs (the FX service) instead of receiving values its
caller prepared. Historical cost in the report currency — each acquisition at its own date, the cost in the asset
currency kept alongside; a missing rate or cost always surfaces (pair + dates, `MISSING_COST_BASIS`), never a silent
zero; four implementations retired (engine pools, `wac_utils.py`, the lots WAC rows, `get_cost_basis`). The page keeps
the rejected alternatives (identity-rate patch, pool in the asset currency revalued daily, cross rates), the
behaviour changes (FX effect now inside the unrealized change, with its per-currency tooltip; oversell; in-transit
cost at arrival; AI Export provenance v2) and the known limits (FIFO lot conversions still fall back to unconverted
amounts; `oversold_movement_ids` not surfaced).
Filed: [[decisions/financial-math-single-average-cost]].

## [2026-10-07] file | Issue #32 — zero purchase cost for a foreign asset paid in the report currency (problem)
The engine kept its pools in the asset currency; with the purchase paid in the report currency, `_buy_unit_cost`
needed the identity key `(T, T, d)`, which `_preload_fx_rates` never loads, and its `None` became "add at the current
average cost" — 0 for an empty pool, with no trace. The page records the same-root twins (a cost basis in the report
currency, which also inflated total P&L; a cost basis in a third currency), the other silent fallbacks found by the
same analysis, the fix and the regression tests.
Filed: [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]].

## [2026-10-07] update | Workstream P — the average-cost pages realigned
Updated, keeping their history and marking what the change superseded:
[[concepts/inline-wac-computation]] (superseded in part: the replay now follows a precomputed `compute_average_costs()`
timeline in the report currency), [[entities/portfolio-engine]] (new "Average Cost" section, required `average_costs`,
gotcha on the test construction outside the engine selectors, history row, dead source paths remapped),
[[entities/portfolio-service]] (facade, realized P&L and boundary costs from the engine, breakdown rows; known issue 3
closed), [[entities/lots-analysis-service]] (WAC lines on the function, gaps → `DEGRADED`; FIFO lot fallback recorded as
a known limit), [[features/F-097]] (implemented → documented, mkdocs `developer/backend/transactions/wac.md`, stale
names annotated, three dead source paths remapped) and its row in [[features/registry]] (`in-progress` → `documented`),
[[decisions/wac-target-currency-last-acquisition]] (scope note: the rule now governs only the facade's callers — preview
/ automatic cost basis and `POST /portfolio/wac`; the PAC passes the report currency; Dashboard, engine and lots use the
report currency; the broker summary the asset currency), [[problems/test-transaction-implied-constructor-mismatch]]
("Recurrence 2026-10-07"; its index row said `open`, the page has said `resolved` since 2026-07-13 — aligned).
Reviewed and left unchanged: [[decisions/cost-basis-currency-object]] — nothing in it became false.
Drift flagged in passing, not realigned (valuation was not part of P): the engine page's LAST_BUY_PRICE section and the
service page's TRANSACTION_IMPLIED item describe valuation designs replaced by the unified price resolver on 2026-07-31
(`1c5082f81`).
Still contradicting P's outcome, outside this filing's page list: [[problems/wac-feedback-loop]] (presents `add_at_wac`
as the backend mechanism — it was unreachable and is deleted), [[concepts/3-pool-cash-model]] and
[[concepts/pre-frame-frame-separation]] (sold cost / cost basis "× FX" at the valuation or sale date), [[features/F-058]]
(cites the deleted `wac_utils.py` and `fifo_utils.py`), [[domains/calculations]] (FIFO presented as the core cost-basis
algorithm), [[features/F-048]] (`compute_weighted_avg_cost`).
State at filing time: the plan's step P9 was still open — `dashboard.unrealizedAssetEffect`,
`dashboard.unrealizedFxEffect`, `dashboard.unrealizedUnsplit` and `dataQuality.missingCostBasis` were in none of the
four i18n catalogues, so until they land the tooltip rows and the new banner issue show key ids; the IT/FR/ES
translations of the updated docs are translation debt (P11).
Graph: the graphify `--update` is **deferred** — `graphify-out/graph.json` and `.graphify_python` do not exist in this
worktree. `check_source_paths.py`: 0 missing paths on the ten pages created or edited; elsewhere 64 distinct missing
paths remain (90 occurrences in 53 pages, down from 99 in 59 before this filing).

## [2026-10-07] update | Workstream P — four more pages realigned with the single average cost
Follow-up to the entries above: only the statements workstream P made false, annotated or marked superseded, history
kept. [[problems/wac-feedback-loop]]: historical note on solution item 1 — `add_at_wac` was unreachable in production
and is deleted with `wac_utils.py`; the auto receiver's cost basis comes from the WAC facade at `/validate` and
`/commit`; the math-engine path now cites `financial_math/average_cost.py`. [[concepts/3-pool-cash-model]]: the sold
cost C leaves at its historical cost in the report currency, with no rate (old formula kept, marked "until
2026-10-07"); the caveat's per-SELL `get_summary()` sentence is marked superseded — the KPI realized P&L comes from the
engine's `realized_sales`. [[concepts/pre-frame-frame-separation]]: `cost_basis` is historical in T with no rate (old
line kept, marked), plus a one-line note that the pre-frame's step 3 now advances precomputed steps.
[[features/F-058]]: the WAC row points to `financial_math/average_cost.py`, with a note on `wac_utils.py`; the
`fifo_utils.py` row is left as it is — it was deleted on 2026-09-03, before P.
Older drift deliberately left for the coordinator: [[domains/calculations]], [[features/F-048]], the LAST_BUY_PRICE and
TRANSACTION_IMPLIED descriptions.
Index: no summary changed. Graph: the graphify `--update` is **deferred** (graphify unavailable in this worktree).
`check_source_paths.py`: 0 missing paths on three of the four pages; [[features/F-058]] keeps its one pre-P miss
(`fifo_utils.py`); overall 64 distinct missing paths, 88 occurrences in 52 pages.

## [2026-10-07] file | A slow language switch tore the whole app down
Triage of the auth 3a coverage red: both layouts unmounted the app on every svelte-i18n `isLoading`, so a
Welcome language preview whose catalogue took more than 200 ms was rebuilt back to the persisted language.
Fixed with a first-dictionary latch; regression E2E 3c and a layout unit case.
Filed: [[problems/i18n-loading-gate-remounts-app]].
Graph: the graphify `--update` is still **deferred** — no `graphify-out/graph.json` in this worktree.

## [2026-10-08] file | Two parallel passes lost all their coverage: a part renamed under `coverage combine`
Analysis and fix of the 2026-10-07 coverage-combine failure (backend read 36.8 % in a green run). The resource
tracker's part was renamed between the runner's listing and coverage's start, and coverage aborted the combine.
The runner now combines the directory, keeps one parts directory per run and turns the pass red on a failed
combine. The first real pass also found empty parts left by a SIGTERM during coverage's own save; these are
removed and named. The causes are in the backlog.
Filed: [[problems/coverage-combine-race-renamed-part]]. Updated: [[concepts/test-isolation-classes]] (the
`COVERAGE_FILE` row).
Graph: the graphify `--update` is **deferred** (graphify unavailable in this worktree).

## [2026-10-08] update | Import Todo Signals: todos reach the bulk editor, worded like notices
The concept page still said todos never leave the wizard and that `message` is an English fallback. Todos travel
with their rows into the bulk editor (blockers gate Save All, warnings feed the save gate); `message` is the
plugin's wording in the file's language, and `resolveBrimTodoMessage` now words them on every surface,
the bulk editor included (workstream O, S19).
Updated: [[concepts/import-todo-signals]].
Graph: the graphify `--update` is still **deferred** — no `graphify-out/graph.json` in this worktree.

## [2026-10-09] ingest | Release 2 archive, batch 1 — 28 FX in the Dashboard, 30 WAC unification, 29 i18n audit
Nineteen work-stream folders moved today from `Release_2/Phase_0/` to `Release_2/phases/` (train 25, `586a4f0ea`).
This batch covers the three whose knowledge was already partly in the wiki. `wiki-search` found the 2026-10-07/08
filings (WAC decision and #32 problem, three i18n problems, the coverage-combine race) and nothing on FX in the
Dashboard, the page cache, the display currency, `db <path>` or the settings bulk write. Every claim below was
checked against the code at `586a4f0ea`; where the plans and an explore pass disagreed with the code, the code was
written (the D6 scenario, the D7 percentage rule, the origin of `GLOBAL_SETTINGS_CONSTRAINTS`).
Created: [[problems/fx-backward-fill-unbounded-stale-rates]] (**backlog N-9**: the page D6 promised — `convert_bulk`
fills without a maximum age; Risk and Signals flag FX carried forward > 7 days, the engine's `_preload_fx_rates`
discards the flag, so the Dashboard never does), [[concepts/stale-while-revalidate-page-cache]],
[[problems/db-path-argument-ignored-by-alembic]], [[problems/global-settings-bulk-saved-unvalidated-values]],
[[sources/phase00-fx-dashboard-sync-2026-10]], [[sources/phase00-wac-unification-2026-10]],
[[sources/phase00-i18n-audit-2026-10]].
Updated: [[features/F-016]] (auto-sync on creation, full history; dead `FxProviderConfig.svelte` row removed),
[[features/F-008]] (840+ → 4 215 keys; audit tool and library traps), [[decisions/settings-write-path-contract]]
(server-side all-or-nothing bulk write).
Graph: not updated (decision of the coordinator: no graphify run in this session).

## [2026-10-09] ingest | Release 2 archive, batch 2 — 20 performance charts, 19 Yield on Cost, 24 global privacy
`wiki-search` found nothing citing these folders; F-088 still said "planned, client-side", F-055 knew nothing of
the P&L modes, and [[decisions/asset-global-page-shows-no-money]] still waited for a formatter repair that landed on
2026-09-24 (`176f19707`). The two largest plans of the archive (~5 700 and ~6 700 lines) were read through status
headers, decisions and closing checks. Code wins over plan: the rolling-return window is preset **or custom** (the
plan's "fixed windows, no custom input" is outdated); privacy has a user doc (Preferences → Privacy mode).
Created: [[decisions/portfolio-pnl-series-contracts]] (additive broker lines in one replay; candles composed per day
then bucketed; income from the ledger), [[concepts/echarts-chart-gotchas]], [[problems/asset-event-edit-delete-reinsert]],
[[decisions/yield-on-cost-definition]], [[features/F-100]] (Yield on Cost), [[decisions/privacy-mask-at-the-formatter]],
[[concepts/premise-gate-keyed-by-content]], [[features/F-101]] (global privacy mode),
[[sources/phase00-performance-charts-2026-09]], [[sources/phase00-yield-on-cost-2026-09]],
[[sources/phase00-privacy-global-2026-09]].
Updated: [[features/F-088]] (planned → documented, rewritten to the backend calendar signal), [[features/F-055]]
(P&L modes; implemented → documented), [[concepts/discard-the-answer-not-the-question]] (case 5, events on a cache
hit; dead route path remapped), [[decisions/asset-global-page-shows-no-money]] (update note).
Product defect confirmed in passing (backlog I-09, report only): `FAAssetEventPoint.type` is a free `str`, so an
unknown event type is written and every later read of the row fails.

## [2026-10-09] ingest | Release 2 archive, batch 3 — 36 connection security, 34 account deletion and id reuse
`wiki-search`: nothing on the indicator, enumeration, account deletion, id reuse or the last admin. Reading the code
to check the plans exposed three auth pages that had never matched it: [[features/F-002]] described an admin CRUD API
and a Settings tab that do not exist (administration is `dev.py user …`), [[features/F-003]] called `UserRole`
admin/user (it is the broker role; admin is `is_superuser`) and cited a `get_admin_user` that does not exist
(`require_admin`), and [[features/F-065]] said Secure=False, UUID ids and passlib. All corrected, history kept.
Created: [[problems/login-account-enumeration-before-password]] (pre-fix code read at `01da03047^1`: disabled checked
before the password, no bcrypt for unknown users), [[decisions/connection-security-server-never-upgrades]],
[[features/F-102]] (connection security indicator), [[problems/account-deletion-orphaned-brokers]],
[[problems/reused-ids-after-delete]] (post-migration fix subsystem), [[sources/phase00-connection-security-2026-10]],
[[sources/phase00-account-and-id-reuse-2026-10]].
Updated: [[features/F-001]], [[features/F-002]], [[features/F-003]], [[features/F-065]] (blank `JWT_SECRET`,
`SESSION_COOKIE_SECURE`), [[decisions/broker-last-owner-guard]] (second caller of the rule),
[[concepts/single-migration-strategy]] (marked superseded: incremental migrations since the release; rule of record
in `.github/instructions/backend-db.instructions.md`).
Deliberately not written: plan 34 §0 B1 carries an instruction of the developer that one aspect of the id fix stays
only in the plan; this wiki records the models, the schema test and the post-migration subsystem, nothing more.

## [2026-10-09] ingest | Release 2 archive, batch 4 — 26 Danske Bank / report sets, 31 DEGIRO, 18 BRIM targeted, 33 E2E import infra
`wiki-search`: only [[concepts/import-todo-signals]] mentioned Danske; nothing on report sets, the encoding chain,
plugin re-detection or the stale-frontend fix. [[features/F-013]] still described a `detected()` method (detection is
`can_parse`, plus `detect_role` for sets) and Generic CSV as "the fallback" (it is not a catch-all), and
[[decisions/brim-broker-scoped]] lacked `batch_id`. Code wins over an explore pass once more: the damaged-workbook
error family does include `IndexError` and `struct.error` (`file_preview.py`).
Created: [[decisions/brim-report-sets]], [[features/F-103]] (BRIM report sets), [[problems/brim-text-exports-hardcoded-utf8]],
[[problems/brim-compatible-plugins-frozen-at-upload]] (with the per-broker sidecar lock),
[[problems/stale-frontend-after-update-html-cached]], [[sources/phase00-brim-danske-bank-2026-10]],
[[sources/phase00-brim-degiro-2026-10]], [[sources/phase00-brim-targeted-2026-09]],
[[sources/phase00-e2e-import-infra-2026-10]].
Updated: [[features/F-013]] (31 modules, detection, encoding rule, DEGIRO/Danske/eToro/Crédit Agricole notes;
implemented → documented, matching its registry row), [[decisions/brim-broker-scoped]] (report-set upload contract).
Confirmed still present (backlog L10, report only): a stale `TODO(P2-refactor)` comment in `broker_credit_agricole.py`.

## [2026-10-09] ingest | Release 2 archive, batch 5 — 11 contracts and Runes, 14 urgent import feedback, 15 runtime lanes, 35 dev.py in the image
`wiki-search`: only [[problems/ghcr-browser-cors-auth-flow]] (14, Round 5) was filed. [[entities/devpy-cli]] said
~1 050 lines (2 714), an 18-module runner (30) and "pre-build first" (`docker build` rebuilds stale assets itself);
[[features/F-063]] said `./dev.py test gallery` (it is `mkdocs gallery`) and "no incremental migrations".
Created: [[concepts/runtime-lanes]], [[problems/devpy-unusable-in-docker-image]] (with the HEALTHCHECK on 6040),
[[problems/asset-classification-wiped-by-partial-save]] (absent vs `null` in a PATCH; `exclude_none` vs
`exclude_unset`), [[features/F-104]] (recommend LibreFolio — copy and go), [[sources/phase00-feedback-contracts-runes-2026-09]],
[[sources/phase00-feedback-import-urgent-2026-09]], [[sources/phase00-parallel-runtime-isolation-2026-09]],
[[sources/phase00-dev-cli-image-2026-10]].
Updated: [[entities/devpy-cli]] (lanes, image stubs, `db <path>`, venv gotcha, stale numbers), [[features/F-063]],
[[features/F-062]] (HEALTHCHECK, CLI in the container, HTML revalidation).
Docstring drift reported, not fixed: `AssetCRUDService` bulk patch docstring says `exclude_none` for
`classification_params`, the code uses `exclude_unset` (`backend/app/services/asset_sources/crud.py`).

## [2026-10-09] ingest | Release 2 archive, batch 6 — 17 asset data operations, 22 SP08 asset pricing, 23 SP16 transaction batch
`wiki-search`: nothing on bond categories, the distributions CSV, the `asset_sources/` package or the batch stages;
[[features/F-095]] was still `planned`, and [[concepts/prices-current-side-effect]] pointed at functions of the
monolithic `asset_source.py`, now a facade.
Created: [[entities/asset-sources-package]], [[entities/transaction-batch-pipeline]],
[[sources/phase00-asset-data-operations-2026-09]], [[sources/phase00-asset-pricing-refactor-2026-09]],
[[sources/phase00-transaction-batch-refactor-2026-09]].
Updated: [[features/F-095]] (planned → documented: global transaction count + filtered link, per-item savepoints),
[[decisions/unified-batch-pipeline]] (SP16 stages), [[concepts/prices-current-side-effect]] (moved functions).
All nineteen archived folders now have a source page.

## [2026-10-09] lint | Health check after the Release 2 archive ingest
Graph: 1 650 nodes, 2 432 edges, 169 communities — `graph.json` of 2026-09-09, `GRAPH_REPORT.md` of 2026-09-22; **stale,
not rebuilt** (no graphify run in this session, by instruction). God nodes unchanged (Feature Registry 99 edges, F-048 78,
F-046 46, F-047 32, Domain TRANSACTIONS 27); the five surprising INFERRED edges are AI Export pairs, plausible. Every
graph query was confirmed with `grep` over `wiki/`, `index.md`, `log.md` and the registry.
Issues found: 14 (7 high, 4 medium, 3 low).
- 🔴 H1 backlog N-9: the backward-fill page promised by D6 was never written → written
  ([[problems/fx-backward-fill-unbounded-stale-rates]]).
- 🔴 H2 `raw/ingest-registry.md`: 158 of the 181 rows dated up to 2026-08-31 carry commit hashes that are **not in this
  repository's history** (only 2 resolve; the 14 `(blob)` rows still match), so `git diff {hash} HEAD` cannot measure
  their drift; 64 rows name moved paths, 7 renamed Plan D files → documented with a path map at the top of the
  registry; re-baselining deferred (it would assert that the derived pages were re-read).
- 🔴 H3 `check_source_paths.py`: 59 missing paths / 80 occurrences / 47 pages on disk at session start (69 / 96 / 58 in
  a clean worktree, where git-ignored artefacts do not exist) → **1 / 1 / 1** on disk and 11 / 17 / 12 clean; 58 paths
  remapped to their successor (archived Risk plans, Plan R3 SP-D full paths, `phases/` moves, renamed modules,
  backend signal plugins, `trySave.ts`, `sw.js`, `003_scheduler_timezone.py`, `TransactionBulkModal.svelte`…) or
  turned into dated "removed" notes. Left: `backend/app/api/v1/admin.py` (F-078, a planned file "to create") and ten
  git-ignored artefacts cited on purpose (generated API client, build/coverage outputs, the prod data directory).
- 🔴 H4 feature catalogue: F-052/F-053 `planned` (the scheduler shipped in Phase 08), F-055 implemented, F-088 and F-095
  `planned` (both shipped) → corrected; five shipped features had no code → F-100…F-104; statistics recomputed
  (96 → 104).
- 🔴 H5 pages contradicting the code → corrected with history kept: [[features/F-001]], [[features/F-002]] (no admin
  CRUD API or tab), [[features/F-003]], [[features/F-065]], [[features/F-008]], [[features/F-013]],
  [[features/F-063]], [[entities/devpy-cli]], [[concepts/single-migration-strategy]] (superseded),
  [[domains/scheduler]], [[decisions/asset-global-page-shows-no-money]], [[decisions/brim-broker-scoped]],
  [[concepts/prices-current-side-effect]].
- 🔴 H6 tooling: `detect_incremental(Path('corpus/'))`, the SCHEMA's "is the graph up to date?" check, scans **0**
  files with the installed graphify (the corpus roots are symlinks resolving outside the scan root) and would report
  "up to date" → reported, not fixed (SCHEMA is outside this session's write scope). Measured instead from
  `graphify-out/manifest.json`: 177 wiki pages changed since their semantic extraction + 112 wiki pages new = 289 to
  re-extract (714 with the roadmap and mkdocs-en sub-corpora, whose manifest keys no longer match); 162 wiki pages are
  newer than `graph.json`. The Release 2 plans are not in the corpus at all (`corpus/roadmap` → `RoadmapV4_UI`).
- 🔴 H7 privacy: a page quoted a machine hostname containing a person's name → redacted to `<hostname>`.
- 🟡 M1 15 of the 19 archived folders had no wiki coverage → six ingest batches above.
- 🟡 M2 orphans: 91 → 84 (59 are source pages linked only from the index, by convention).
- 🟡 M3 concept debt → [[concepts/echarts-chart-gotchas]], [[concepts/runtime-lanes]],
  [[concepts/stale-while-revalidate-page-cache]], [[concepts/premise-gate-keyed-by-content]].
- 🟡 M4 P-6 (graph step for the #32 pages) still open: those pages, and the 47 created today, are not in the graph.
- 🟢 L1 broken wikilinks: 8 targets in historical `log.md` entries and 1 in a registry row
  (`sources/knowledge-base-overview`) — left as history; none in pages or the index.
- 🟢 L2 index: 57 feature pages are not listed one by one — by design (the registry is the catalogue); no other page
  is missing.
- 🟢 L3 code facts reported, not fixed: I-09 (free-text asset event type → 500 on read), L10 (stale TODO in the Crédit
  Agricole parser), the `patch_assets_bulk` docstring (says `exclude_none`, code uses `exclude_unset`), and the
  Dashboard path that discards FX staleness (part of N-9).
Repaired: H1, H3, H4, H5, H7, M1, M3, part of M2. Deferred: H2 (re-baseline), H6 (SCHEMA snippet), M4 (graph run).
Next recommended: a graphify semantic `--update` over `wiki/` (289 pages) once the cost is approved — it closes P-6;
then fix the corpus symlink scan so the incremental check stops reporting "up to date" on an unscanned corpus.

## [2026-10-09] file | P-1 closed without code — Auto cost basis without a position (folder 39)
Second pass, HEAD `083ed26dc` (train 26). `phases/39_autoCostNoPosition/` holds one plan of workstream P, written and
closed today. The developer's decision, verbatim: «no chat, non facciamolo e segnamo la decisione, se i dati mancano
lo 0 come fallback per auto è corretto. se bisogna cambiare sarà l'utente ad andare su quella transazione e
correggere.» P's draft note was used as input and every claim re-checked on the code (the zero WAC on an empty pool,
`ADD_ZERO_COST`, `if wac_result.wac:` in the inline WAC, the batch's Auto indices, the form default `'auto'`, the
existing test `test_wacp27_empty_pool_wac_zero`); the draft's "enter the field and leave it = 0" gesture does not exist
in the code and is recorded as the developer's first direction, superseded.
Created: [[decisions/auto-cost-basis-zero-without-position]], [[sources/phase00-auto-cost-no-position-2026-10]].
Updated: [[decisions/wac-inline-validate-commit]] (`'auto'` on an empty pool → 0 by decision),
[[decisions/financial-math-single-average-cost]] ("never a silent zero" does not cover Auto's known 0),
[[sources/phase00-wac-unification-2026-10]] (P-1 residual closed).
Graph: not updated (deferred to after 1.2 by the developer; P-6 and C-29 stay in the backlog).

## [2026-10-09] file | PAC allocator — rounding against the plan (D's notes, merge `b81b92fd1`)
No PAC page existed (folder 13 is still active, no feature code yet). Filed from
`Phase_0/13_pacAllocator/implementation/plan-phase00PacRoundingDirectionFix.prompt.md`, checked against
`services/pac_allocator/` at `083ed26dc`: rule (a) — one table `_PLAN_ROUNDING` in `ledger.py` (credits `fx_credit`,
`gross_sell_credit` floor; debits `buy_debit`, `buy_fee`, `sell_fee`, `broker_withheld_tax`, `self_reserved_tax`
ceiling) and the same direction in the SCIP rows; the band `rounding_bound` = one minor unit per rounded posting with
the strict per-posting check `_validate_posting`; C-FXPOS (row and evaluator fact) with its residual SCIP tolerance →
`execution_failed`; B1 (β = h·Σ1/Rᵢ on the three stored rates, h = half a unit of the tenth decimal of
`Numeric(24, 10)`; planning rate `min(spot·(1−s), val(origin)/val(destination))`; beyond it
`allocation.fx_rate_inconsistent`); the lesson (the principle lives in MathCore §7.3, not TargetDesign §4.4; no test
states it literally — the tests pin its halves).
Created: [[decisions/pac-rounding-against-the-plan]]. Updated: [[concepts/backend-only-calculations]] (scope link).
Graph: not updated (deferred).

## [2026-10-09] file | Backlog K-25 — the four devWiki pages of workstream K
Written from steps 13 and 14 of `phases/25_taxonomySelect/`, every claim checked on the code:
[[problems/svelte5-teardown-reads-stale-state-timers]] (Tooltip and TreeSelect; residuals K-12, C-13),
[[decisions/html-escape-at-the-source]] (escape rules and the two gates; `escapeHtml` is defined **three** times at
HEAD — the canonical helper, the KaTeX variant, a local copy in `CorrelationHeatmap.svelte` — so
[[features/F-047]]'s "× 4 copies cleanup (deferred)" was corrected to done-with-two-left),
[[problems/stale-price-banner-never-emitted]] (`valuation_stale` also flags trade-derived marks; rule D8; `/assets`
writes today's price), and [[concepts/responsive-4mode-layout]] rewritten from the code (four tiers per page,
thresholds measured in four languages, the gutter rule) — none of the four was already covered.
Cross-links: [[concepts/premise-gate-keyed-by-content]], [[concepts/echarts-chart-gotchas]] (K-15; tooltip width on
phones), [[problems/fx-backward-fill-unbounded-stale-rates]], [[features/F-054]].
Graph: not updated (deferred).

## [2026-10-09] ingest | Release 2 archive, folder 25 — workstream K, taxonomy and selects (steps 1–23)
One analysis and 18 plans; `wiki-search` found only [[problems/flag-emoji-windows]] citing the folder (step 12) and
nothing on the taxonomy, the import-duplicate keeper, the request loop, the bulk guards, app start or Escape layering.
Code over plan: D-K3 expected real-estate crowdfunding inside the Real-estate slice of the allocation pie, but the
charts now group by family (workstream I, D15); [[features/F-048]]'s "JSON snapshot comparison" is still true for the
form modal — only the bulk editor's guard became canonical (`serializeOps`); the `AssetType` docstring's "subtypes roll
up to the base type they contain" is not what the backend's `allocation_by_type` does (reported, not fixed).
Created: [[sources/phase00-taxonomy-select-2026-10]], [[decisions/asset-type-two-level-taxonomy]],
[[problems/broker-icon-fields-request-loop]], [[problems/modal-layers-escape-and-backdrop]],
[[problems/fixture-skip-hid-api-test]].
Updated: [[features/F-001]] (app start: only a 401 signs out, `?redirect=` through `safeInternalPath`, register link),
[[features/F-008]] (missing ICU argument shows raw text; the argument guard), [[features/F-024]] and
[[entities/db-models]] (the `AssetType` list was stale since July: `CROWDFUND_LOAN` → `CROWDFUND`, subtypes),
[[features/F-032]] (stored XSS fixed, type filter), [[features/F-033]] (‹ n/N › browsing, phone tooltip),
[[features/F-048]] (creation order, canonical close guard, cloning pairs, K-1 … K-4), [[features/F-098]] (opaque and
maskable PWA icons; the old Apple-first flag stack marked superseded), [[features/F-099]] (metadata currency from the
price API; K-16), [[entities/import-wizard-modal]] (C1/C2/C6), [[concepts/entity-store-pattern]] (K-11),
[[concepts/svelte5-runes]] (known traps), [[problems/testid-grep-false-negative]] (`testIdPrefix`),
[[problems/flag-emoji-windows]] (K-13/K-14).
Not filed (nothing durable beyond the source page): the app-title guard, the selection cleared after a save, the
avatar merge in `PreferencesTab`, the AssetModal footer on phones, the date and size formats of step 22 (C-10/C-11).
Registry: 22 rows at `083ed26dc` (19 for folder 25, 1 for folder 39, 2 for the PAC plans).
Graph: not updated (deferred).

## [2026-10-09] lint | Second-pass checks
- `check_source_paths.py`: 1 missing path (1 occurrence) of 2 757 cited, in 1 page — `backend/app/api/v1/admin.py`
  in [[features/F-078]], unchanged from the first pass; every path cited by the 11 new and 24 updated pages is
  tracked in git at `083ed26dc`.
- Wikilinks: 0 broken in pages and in the index; every new page has inbound links besides the index.
- Privacy: no absolute paths, e-mails, IBANs, IPs, venv names or `/tmp` logs in the added text.
- Feature registry: no new code needed — K's lots extend F-001, F-008, F-024, F-032, F-033, F-048, F-054, F-098,
  F-099, whose statuses stand; the PAC allocator still has no code (to assign when folder 13 is archived).
- Reported, not fixed: the `AssetType` docstring vs the backend allocation (above); `test_settings_api.py` skips five
  checks on a 404 from endpoints that exist (latent false green, [[problems/fixture-skip-hid-api-test]]); the mkdocs
  data-quality page still says "All 5 codes" (K-24, assigned).
- Graph debt grows by the 11 new pages; P-6 and C-29 stay in the backlog by the developer's decision.

## [2026-10-12] ingest | Lot 41 — F (native cash), the broker lines at transfers, the cards (H)
Source: `Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` @ git:`f10fcd04a` (§0–§4, §13–§17),
backlog section I, base `5d0585595`. Step 3 of the historian, decided by the developer on 2026-10-12 («Adesso, in
parallelo»). Every claim checked on the code: `native_cash.py` (`compute_native_cash`, `NativeCash`,
`exchange_results`, `CONVERSION_DUST`), `_revalue_foreign_cash` (R first, then K), step 10c, the rate-change days in
pre-frame and frame, `_internal_transfer_flows` / `_transfer_leg_capital`, the cards in `get_summary`, the «FX on
cash» row; the lot's commits placed on the history (trains 32, 35, 42). Not in the journal, recorded as «developer,
2026-10-12, via the coordinator»: F-AI (b) after 1.2 with a typed code (section I still lists it as open), and the
Scalable confirmation («come me lo aspettavo»). The plan's §13 G1a text, addressed to the historian on 2026-10-10 and
never applied, is now in [[decisions/portfolio-pnl-series-contracts]].
Drift found on the way: [[concepts/3-pool-cash-model]] described a `reconciliation_delta` flag that the code never had
— the display values rescale the summed pools since 2026-06-25 (`7aa1f7772`); also documented the per-broker pools,
the internal-leg approximation (B3) and the pre-frame SELL approximation.
Created: [[decisions/native-cash-daily-revaluation]], [[entities/native-cash]], [[problems/foreign-cash-never-revalued]],
[[problems/dirty-days-ignore-fx-only-moves]], [[sources/phase00-broker-pnl-flows-2026-10]].
Updated: [[concepts/3-pool-cash-model]], [[entities/portfolio-engine]], [[concepts/pre-frame-frame-separation]],
[[entities/portfolio-service]], [[decisions/portfolio-pnl-series-contracts]],
[[decisions/broker-card-aggregation-no-n-plus-one]] (also its first «Source files» table),
[[problems/ai-export-cash-fx-valuation-basis-mismatch]], [[features/F-054]], [[features/F-055]], [[domains/calculations]].

## [2026-10-12] ingest | T-1 — one home for financial math, D-P7 on utils/, the AI Export version rule, C-53
Source: `Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` @ git:`25e358eb0` (§1, §3, §4,
§8, §10 from «T-1» to «BU1 e BU2»), backlog sections C and T, backlog 38 C-53. T-1's two commits checked on the
history: the rename `1cc9cd8f5` keeps `git log --follow` of `financial_math/portfolio/engine.py` back to 2026-06-19
(39 commits); the modules cut by `a57a43fbd` start there. The version rule («+1 rispetto alla 1.1») checked on the
catalogue: the nine components moved in the cycle are each exactly +1 over `v1.1.0`. BU1 and BU2 written as planned,
not delivered; the BU1 folder is `utils/runtime/` (the developer's choice, via the coordinator; `platform/` in the plan
was the earlier proposal).
Drift: the «Known limits» of [[decisions/financial-math-single-average-cost]] — the lots' native fallback was closed on
2026-10-11 (`82c1d3ab9`, `59a7c3e2f`), `roi_utils`/`valuation_utils` moved by T-1.
Created: [[decisions/financial-math-one-home]], [[decisions/utils-leaf-functions-only]],
[[decisions/ai-export-version-bump-once-per-release]], [[problems/ai-export-reconciled-false-on-rounding-dust]],
[[sources/phase00-financial-math-home-2026-10]].
Updated: [[decisions/financial-math-single-average-cost]], [[entities/fifo-lot-engine]],
[[entities/lots-analysis-service]], [[entities/ai-export-snapshot-service]].

## [2026-10-12] ingest | M — notes b12–b15 (translations) and batch 19 (gallery probes, M-13)
Sources: M's four devWiki notes, kept outside the repository with M's release-pipeline files (untracked), and
`Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` @ git:`62526ede4` (§9.3, §10, §11).
The notes were filed nearly as written; every path, symbol and number was checked against the code and the journal,
and the two notes without a «Source files» table got one. Commits placed on the history rather than taken from the
journal: the French typography hook (`a965956ab`) was built on train 37 but reached `dev_release2` with train 38
(`9245ffb6f`). M-14 (the gallery's browser locale) is in progress: only its diagnosis is written.
Created: [[problems/stamps-hide-stale-translations]], [[decisions/docs-anchors-from-the-render]],
[[problems/raw-html-paths-in-translations]], [[decisions/fr-typography-at-build-time]],
[[problems/playwright-probes-ignore-timeout]], [[sources/phase00-translation-round12-2026-10]].
Updated: [[concepts/mkdocs-suffix-i18n]] — its two wrong «Conventions» lines (never edit translations by hand; the
cache stores every language's MD5) corrected as note b12 asked. Cross-links to the probes page from the two pages that
already named the trap: [[problems/compactcashcell-decimal-separator-feedback-loop]],
[[sources/phase00-e2e-import-infra-2026-10]].

## [2026-10-12] update | T-W1 — old module paths in the prose, after T-1
Backlog T-W1: T-1 repointed only the 58 «Source files» rows (`09c089147`). A scan of the prose (outside those tables)
found 57 mentions of the pre-T-1 homes in 27 files with this ingest's filter (T counted 50 in 28 with another). Rule
agreed with the coordinator: a present-tense claim moves to the new module; dated history stays as written, with a
«since 2026-10-12» pointer only where a reader would be stranded; line numbers become symbol names. About 27 mentions
in 18 pages changed — among them the «Location» of [[entities/portfolio-engine]] and [[entities/fifo-lot-engine]],
[[features/F-054]], [[features/F-056]], [[features/F-058]], [[features/F-100]], [[decisions/mwrr-solver-newton-cap]],
[[decisions/yield-on-cost-definition]], [[problems/fx-backward-fill-unbounded-stale-rates]] (line numbers → symbols)
and [[domains/calculations]], whose diagram and «Source files» placed the FIFO engine in `transaction_service.py`.
Left on purpose: dated history (status-history rows, «as it was before 2026-10-07», the `wac_utils.py` deletion,
source summaries) and contract identifiers such as `"valuation_source": "portfolio_engine"`.
Checks: `check_source_paths.py` — the same 11 missing paths before and after in the worktree (`admin.py` of
[[features/F-078]] plus 10 generated artifacts a fresh worktree does not have; on the main checkout, per the
coordinator, only `admin.py`); 2 931 paths cited, 163 more than before, all present; 0 broken wikilinks in the added
text; every new page has at least three inbound links besides the index. Graph: not updated (P-6, after release 1.2).

## [2026-10-12] update | BU1 — the utils/ paths after the typed folders
Base `bdc078efc` (train 50): BU1 (`346b7e292`, journal `390ba7d9a`) moved `sector_fin_utils`, `geo_utils`,
`identifier_utils`, `translation_utils` to `utils/asset/`, `currency_utils` to `utils/fx/currency.py`, and `version`,
`network_utils`, `cache_utils` to `utils/runtime/`; `decimal_utils` stays until BU2. `check_source_paths.py` on the
new base: 16 missing (28 occurrences), the baseline's 11 plus 5 moved modules cited by 11 «Source files» rows in 10
pages — one of them [[decisions/utils-leaf-functions-only]], written by the step-3 ingest. All 11 repointed. Prose,
with the T-W1 rule: 6 present-tense mentions in 5 pages changed ([[features/F-061]], [[features/F-102]],
[[problems/babel-currency-symbol-locale]], [[problems/docker-system-info-missing-deps]], [[domains/calculations]]);
symptoms, source summaries and the audit line of [[features/F-076]] left as written. The test files keep their names.
[[decisions/utils-leaf-functions-only]] now records BU1 as delivered and BU2 as planned, with a near-miss from the
journal: `utils/runtime/version.py` computed the project root with four `.parent` written for its old place, so the
image would have read `/app/backend/VERSION` and shown version `unknown`; fixed in the same commit with
`_project_root()` from the module's dotted name, two tests, and the lesson «in a rename, search the paths a file
computes from its own location». The same note went into [[problems/docker-system-info-missing-deps]].
Registry: plan 43 re-read at `390ba7d9a` (the BU1 record).
Checks: `check_source_paths.py` back to the baseline set — 11 missing (17 occurrences) in the worktree, the same paths
as before BU1; 0 broken wikilinks in the added text; `git diff --check` clean. Graph: not updated (P-6).

## [2026-10-12] update | BU2 — DB precision out of utils/, and the version rule written down
Base `f0f3de0d9` (train 53): BU2 (`8dae5cc6e`, journal `f038ce39a`) moved `get_model_column_precision`,
`truncate_to_db_precision`, `truncate_priceHistory` and `truncate_fx_rate`, unchanged, from `utils/decimal_utils.py`
to `backend/app/db/precision.py`; `decimal_utils.py` keeps only `parse_decimal_value`. The lazy `clear_cache` imports
of `fx.py` and the lazy `get_git_version` import of `config.py` became top-level: none broke a cycle. In the wiki only
one present-tense mention of the truncation existed, in [[features/F-017]] — repointed; no «Source files» row cited
`decimal_utils` except [[decisions/utils-leaf-functions-only]]'s own, now split into the new module and the reduced
one. That page records BU2 as delivered: every `utils` module is a leaf.
The AI Export version rule, flagged by step 3 as living only in the journal, is now written (`4388db8df`): a
«Versions» section in `.github/instructions/ai-development.instructions.md` and a paragraph in «ComponentSpec» of
`ai_export_composition.md`, both citing [[decisions/ai-export-version-bump-once-per-release]], which now lists them.
Correction carried back from the docs-writer's code check: the spec/placeholder version parity is checked at import by
`catalog.py`, not by "the registry", as the page had copied from the journal.
Registry: plan 43 re-read at `f038ce39a` (the BU2 record).
Checks: `check_source_paths.py` — the same 11 missing paths (17 occurrences) as the reference set; 0 broken wikilinks
in the added text; `git diff --check` clean. Graph: not updated (P-6).

## [2026-10-12] update | M-14 closed — the gallery shoots each language in its own browser locale
Base `9e31ea2ba`. At step 3 [[problems/playwright-probes-ignore-timeout]] recorded only M-14's diagnosis, since the fix
was in progress; batch 20 of M closed it the same day (`51b581636`, journal `63b3e5971` §11, train 52 `d33fca26f`), on
the developer's decision «impostiamo il locale in playwright sin da ora». Checked on the code:
`frontend/e2e/fixtures/galleryLocale.ts` (`setBrowserLocale` → Chromium's `Emulation.setLocaleOverride` from the page's
CDP session, `stampDocumentLocale`, `expectDrawnUnder`), 76 `setBrowserLocale(page, lang)` in `gallery.spec.ts`, the
gallery's describe yielding `undefined` for Playwright's `locale` fixture (the default `en-US` would make Chromium refuse
the override). The page now describes the fix, its guard and its proof. M-16 — the wizard's «Next» before the broker
list — moves among the closed items: fixed by I in train 48 (`3cd25af4f`, `trackBrokerLoad` and `Promise.allSettled`,
checked on the code). M-17 and M-18, found by M-14, are planned in release 1.2 and assigned to I (the coordinator's and
the developer's decisions); M-15 stays open after 1.2. The index row followed.
[[sources/phase00-translation-round12-2026-10]] stays as written: it is the snapshot of the step-3 ingest.
Registry: plan 27 round 12 re-read at `63b3e5971` (§11); plan 44 (`Phase_0/44_importWizardBrokerGate/`) read at
`8339b0a06`.
Checks: `check_source_paths.py` on the reference set; 0 broken wikilinks in the added text; `git diff --check` clean.

## [2026-10-12] ingest | Plan 46 (V) — data-quality warnings proved on real data
Source: `Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` @ git:`b44b28f3d`, backlog section V,
base `e7d698c4d` (train 56; code `15bfcf1e8`, tests `2f0b06346`). Checked on the code: the specs and their runner
actions, the helper's guards (`setup_test_database`, `verify_test_database`, exits 2 and 3), the MOCKFX provider, the
`refreshVersion += 1` in `syncMissingFxRates` and its two listeners (`LotsAnalysisPanel`, `RiskLevelsPanel`).
Created: [[decisions/data-quality-proved-on-real-data]] (items 21–23, D1 «(c) Entrambe», MOCKFX, the legacy-row helper,
V-1…V-7), [[problems/open-panels-stale-after-fx-sync]] (D2), [[sources/phase00-data-quality-e2e-2026-10]].
Updated: [[features/F-054]] (status history).

## [2026-10-12] file | C-55 — the probe rejected the unavailable HHI of an empty broker
Sources: plan 43 «C-55 — analisi» to «Checkpoint C-55» @ git:`d5497e40a`, backlog 38 C-55 @ git:`17c50ab50`, commit
`9e495c305` (train 56). The defect was the probe's, not the product's: HHI and largest weight are `null` together on an
empty set, by contract. Created: [[problems/ai-export-probe-rejected-unavailable-hhi]]. Updated:
[[decisions/ai-export-version-bump-once-per-release]] (a third no-bump case), [[entities/ai-export-snapshot-service]]
(history).

## [2026-10-12] file | U — plugins as folders, i18n catalogues split by subsystem (planned)
Not in the code at `e7d698c4d`, and U's plan 45 is not in the target: the decisions D-1, D-4, D-A, D-B and D-C of
2026-10-12 (D-1 taken by the coordinator on the developer's delegation), quoted verbatim by the coordinator from his
diary (not in the repository), and the origin, item 28 of the developer's server checklist. Recorded as planned, as
the D-P7 page was before BU1. Created:
[[decisions/plugin-folders-and-split-i18n]]. Cross-links from [[decisions/provider-registry-decision]],
[[decisions/signal-backend-plugin-architecture]], [[decisions/i18n-key-rationalization]]. When U lands, about 84
plugin-path citations in 47 pages will need realigning (to be assigned).

## [2026-10-12] update | The connection-security guide — cross-links only
M rewrote the user guide and added the admin page «Checking Connection Security» (`3eee17616`, train 56). Rows and a
status-history line in [[features/F-102]], a link and a row in [[decisions/connection-security-server-never-upgrades]].
Checks for the four entries: `check_source_paths.py` on the reference set; 0 broken wikilinks in the added text; every
new page has inbound links besides the index; `git diff --check` clean. Graph: not updated (P-6).

## [2026-10-12] lint | Health check, step A (base `37304d716`, train 57)
Graph: not consulted (P-6, after 1.2). File-based checks only; every status below was checked on the code or in git.
Issues found: 11 high (8 statuses checked — 7 corrected, 1 kept `open` — and 3 stale claims), 4 medium groups (24 pages without a link from another page,
4 dead targets, 7 missing statuses, 16 drifted table cells), 4 low groups; 8 judgments reported. The full report went to
the coordinator.
- 🔴 H1 stale statuses → corrected, history kept:
  - [[problems/import-wizard-identifier-prompt]] was fixed in `7bae73b74` on the day it was filed;
  - [[problems/broker-icon-race-condition]] stays `open`: forms A and B were fixed where they were seen in June
    (`7bae73b74`, `ddffb5273`), but the developer saw the symptom again on 2026-10-12 — the large icon on a broker's
    page, the Dashboard's selector — because `BrokerIcon`'s chain reads only its props (the coordinator's correction
    and diagnosis); assigned to I;
  - [[problems/docker-entrypoint-gid20-collision]] was fixed another way, with numeric ids, in `f32e460ca`;
  - [[problems/tanstack-svelte5-incompatibility]] was resolved by removal in `52c8d0d70`;
  - [[F-050]] (`5b887dd3a`), [[F-089]] (`d30c35966`) and [[F-092]] (`2a8e5bf1c`) → documented, and [[F-075]] →
    superseded. The registry rows and statistics were recomputed (89 / 1 / 10 / 3 / 1 of 104), and notes added to the
    domain pages that listed them as planned.
- 🔴 H2 stale prose: [[decisions/yield-on-cost-definition]] and [[F-088]] (I-08 closed on 2026-10-12),
  [[problems/stale-price-banner-never-emitted]] (K-24 closed on 2026-10-09).
- 🟡 M1 24 pages that only the index or the log linked to → one inbound link each, from the page they declared in
  `related:` or the one that cites the same code. Source pages linked only from the index stay, by convention (59).
- 🟡 M2 4 dead `related:` targets, pages never written → repointed: [[decisions/zodios-api-client]],
  [[entities/test-runner]], and [[sources/phase07-part4-round6-planc2-bugfix-pair-validation]] for the A4 race.
- 🟡 M3 7 problems without `status`, verified fixed in the code → `status: resolved`.
- 🟡 M4 table drift: [[F-055]] in the index; 15 cells of the domain tables aligned to [[features/registry]].
- 🟢 L1 `Resolved` → `resolved` (2). L2 5 plain feature codes linked. L3 5 broken links in historical rows of
  `log.md` and the registry: left as history. L4 7 pages without frontmatter: left.
Reported, not changed — left for a lint after 1.2 (coordinator, 2026-10-12):
- `domains/signals` says `in-progress`, the index `stable`;
- `domains/transactions` and [[F-048]] are `in-progress` since April; the brokers and transactions domain pages are
  stuck in the Phase 7 era;
- [[F-094]] is half delivered: the dialog exists, the overwrite warning does not;
- [[decisions/broker-last-owner-guard]] went another way in the code (`987df6805`, `3e3f9c41f`);
- [[problems/generated-client-widens-nullable-scalar]]: `open` or `workaround`?
- the `accepted`/`active`/`open` vocabulary against the SCHEMA;
- [[problems/datatable-column-resize-noop]] and [[problems/bulk-modal-sticky-z-index]] cannot be verified without the
  app;
- two dated source pages say «planned» or «in progress».

Checks after the repairs:
- `check_source_paths.py`: the reference set, 11 / 17 / 12;
- wikilinks: 0 broken in pages and in the index, 0 dead frontmatter targets, 0 non-source pages without an inbound
  link, 0 plain feature codes;
- the registry agrees with every page;
- privacy clean; `git diff --check` clean.

## [2026-10-12] ingest | Step B1 — plan 37 (S): the Scalable importers; the exporter's recap; M's batch 21
Sources: plan 37 @ git:`4d878e545`, the exporter's recap @ git:`305b80202`, M's journal §12 @ git:`0ebf86178`; base
`573f7c5c7`. First of the order proposed by the audit of step B. Checked on the code at HEAD:
- the two plugins and `_scalable.py`: four refusal codes, twelve notices, the id in the description, the tags;
- `cannot_parse_detail`, `check_file_with_plugin`, the `plugin-check` endpoint;
- `_MERGED_LEG_TYPES` and the «probable» rule;
- `defaultPluginCheck.ts`, `ImportBrokerMismatchModal`, `promoteSuggest.ts`, `PromoteAllModal`, `pluginKind.ts` (50);
- the icons, the docs and the tests.

The commits of the five checkpoints and of batch 21 are all in HEAD. `cashAmountsCancel` has been exact since P's lot 42
(`7f8233c47`, train 34), so S's reports to P are recorded as closed.
Created:
- [[sources/phase00-brim-scalable-2026-10]];
- [[decisions/scalable-two-accounts-two-plugins]], [[decisions/import-wizard-default-plugin-check]],
  [[decisions/broker-icon-order-dedicated-plugin-first]], [[decisions/bulk-pairs-new-with-saved]];
- [[problems/merged-transfer-not-seen-as-duplicate]];
- [[concepts/brim-texts-translated-by-code]].

Updated: [[features/F-012]], [[features/F-013]], [[features/F-048]], [[features/F-049]] (status history, Source files),
[[entities/import-wizard-modal]].
Not yet in the target: M's batch 23, a second rewrite of the Scalable page. Graph: not updated (P-6).

## [2026-10-12] ingest | Step B2 — plan 44 (I): the import wizard waits for the broker list (M-16)
Source: `Release_2/Phase_0/44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md` @ git:`8339b0a06`;
base `d3c6e55c5`. Checked on the code at HEAD:
- `brokerLoadsInFlight`, a plain variable, and `trackBrokerLoad`;
- `Promise.allSettled` in `loadBrokers`;
- the guard in `goNext`;
- `brokersLoading` in «Next»'s `disabled` and spinner;
- the `oncreated` refresh through the counter;
- V1–V4b and E1;
- the gallery's `waitForSettled(import-wizard-step1)`.

`3cd25af4f`, `8339b0a06`, the train-48 merge `a94de23e2` and `51b581636` are all in HEAD.
Created: [[problems/import-wizard-next-before-brokers-loaded]], [[sources/phase00-import-wizard-broker-gate-2026-10]].
Updated:
- [[problems/playwright-probes-ignore-timeout]] (M-16 links its page);
- [[problems/svelte5-effect-read-write-loop]] (the rule applied before the code);
- [[decisions/import-wizard-default-plugin-check]] (the gate also protects the check);
- [[decisions/native-cash-daily-revaluation]] (F-AI (b) is a backlog row since `8339b0a06`);
- [[features/F-049]], [[entities/import-wizard-modal]].

Plan 41's registry row refreshed to `8339b0a06`: bookkeeping only since `f10fcd04a`. Graph: not updated (P-6).

## [2026-10-12] ingest | Step B3 — plan 40 (P): the cost of transfers in Auto and of promotes
Source: `Release_2/phases/40_transferCostBasis/plan-phase00TransferCostBasis.prompt.md` @ git:`fa109eaa7`; base
`5350c8e24`. The folder was archived on 2026-10-10, after the archive ingest of 09/10, so the audit found it never
ingested. Checked on the code at HEAD:
- `_auto_cost_source()`: the partner's broker, its date, the two exclusions;
- `_resolve_source_broker_from_link`: gone;
- `_check_result_create_cost_basis` and `_check_promoted_saved_cost_basis`;
- tests P30–P35 and G1/G2 by name;
- the three developer pages, and the theory sentence in all four languages, so the plan's translation residue is
  closed.

`d7c148564`, the train-28 merge `2a5c15c3c` and `fa109eaa7` are all in HEAD.
Created: [[decisions/transfer-auto-cost-from-sending-broker]], [[problems/promote-skipped-cost-basis-check]],
[[sources/phase00-transfer-cost-basis-2026-10]].
Updated:
- [[entities/transaction-batch-pipeline]];
- [[features/F-048]] (a dated note under the Plan D auto-calc: `compute_weighted_avg_cost` no longer exists);
- [[features/F-097]];
- [[decisions/financial-math-single-average-cost]], [[decisions/bulk-pairs-new-with-saved]].

Graph: not updated (P-6).

## [2026-10-12] ingest | Step B4 — plan 42 (P): the checks of promoted pairs, C-46…C-48, the localisation mini-lot
Source: `Release_2/Phase_0/42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md` @ git:`6c32f4aff`; base
`94abcf380`. Checked on the code at HEAD:
- `pairAssetMismatch` and `pairQuantityMismatch` in `_validate_linked_pair`, and both keys in the four catalogues;
- `_promoted_state_issues`;
- `TXPromoteSuggestInput.asset_event_id`;
- `costBasisValue` in `fieldEq`;
- `findPromoteMatch`'s exact opposite and `eventA`/`eventB`;
- the selection bar's `assetQuantitiesCancel`;
- `tolerance_days` with `ge=0`, and the window in the 💡's key;
- the marker locale `qaa` in `DataEditor.test.ts`;
- `$currentLanguage` in the broker card's and sharing panel's template expressions.

The four commits and their merges (trains 32, 34, 37, 38) are in HEAD. Two paths read in the plan's notes were corrected
to the tree: `components/charts/calendarReturnWindow.ts` and `utils/__tests__/txPayloadHelpers.test.ts`.
Created:
- [[decisions/transfer-pair-same-asset-opposite-quantity]], [[decisions/promote-respects-asset-event-link]];
- [[problems/bulk-cost-basis-compared-by-reference]], [[problems/legacy-component-language-untracked]];
- [[concepts/marker-locale-for-catalogue-labels]];
- [[sources/phase00-promote-pair-checks-2026-10]].

Updated: [[decisions/bulk-pairs-new-with-saved]] (C-47), [[decisions/pair-description-tags-validation]] (C-42, the
single-leg update), [[decisions/cash-transfer-split-promote]], [[entities/transaction-batch-pipeline]],
[[problems/promote-skipped-cost-basis-check]], [[concepts/svelte5-runes]], [[concepts/assert-on-identity-not-prose]],
[[features/F-048]].
Graph: not updated (P-6).

## [2026-10-12] ingest | Step B5 — the onboarding (J, folder 21): F-105, six decisions, three problems
Source: `Release_2/Phase_0/21_onboarding/` — the main plan, Rounds 1–8 and the review dossier (ten files, ~313 KB) at
the commits of the registry section; base `c7261618d`. Checked on the code at HEAD:
- the fifteen flows and their versions (`ONBOARDING_FLOW_VERSIONS`, all 1) and the two step lists
  (`ONBOARDING_FLOW_STEPS`, nine Import steps with `import.gapFix`, four Bulk steps);
- the tables and the grandfathering in `004_release_1_2_0_schema.py` (docstring §3), and the consolidation `22fa0aed7`;
- the nine intro step ids (`CORE_TOUR_STEP_IDS`) against the eight `onboarding.tour.steps` keys;
- `GUIDE_STALL_MS` and `PANEL_FADE_MS` (3 s), `isRendered()` with `checkVisibility`, the motion root
  `.modal-content, nav`, `onstallend`;
- the key `lf_{userId}_onboarding_replay_{flow}_v{version}`, `createReplayStorageListener` → `dismissHost()`;
- `toStore(() => appBootstrap.ready)` in `(app)/+layout.svelte`, and `inert` on the shell during `intro_tour`;
- `DeferredAppPopups` (requested update first, nothing during a guide, donation before update), identical in
  `580bd504f` except the requested branch;
- `startImportAt()`/`setStep()` in the wizard, `handOffToEditor()`, `releaseCreateGuideHost()`;
- the commits `8d9761db1`, `8a8e686f0`, `580bd504f` (in `dev_release2` with the PAC merge `3913fe217`), `1982c254b`,
  `64d78e244`, `5e7ae336e`, `cc20b8288`, `f2abf9b47`, `208296923`, `8bd933834`, `93e023f2e`, `020c762e0`.

Corrections against the sources: the dossier's popup lane («suppressed entirely, not queued-and-shown-after») already
held the prompts and showed them afterwards in the code it reviewed (`580bd504f`); the it/fr/es user pages that Round 8
found without onboarding sections have them today.
Created:
- [[features/F-105]] (registry: 105 features, LAYOUT & SETTINGS 8);
- [[decisions/onboarding-versioned-progress-per-flow]], [[decisions/onboarding-existing-users-seeded-skipped]],
  [[decisions/onboarding-guide-observes-never-acts]], [[decisions/onboarding-positions-in-browser-per-account]],
  [[decisions/guide-text-never-announces-another-guide]], [[decisions/automatic-popups-wait-for-guides]];
- [[problems/guide-anchor-never-resolves]], [[problems/coachmark-measured-mid-modal-transition]],
  [[problems/legacy-layout-gate-missed-runes-state]];
- [[sources/phase00-onboarding-2026-09]].

Updated: [[features/registry]], [[domains/layout-settings]] (F-101, F-104 and F-105 in the cluster table, aligned to
the registry), [[features/F-004]], [[features/F-005]], [[features/F-008]], [[features/F-092]], [[features/F-101]]
(R20, the legacy trap of the privacy switch), [[features/F-104]], [[entities/import-wizard-modal]],
[[concepts/svelte5-runes]], [[problems/legacy-component-language-untracked]] (two earlier instances),
[[problems/i18n-loading-gate-remounts-app]].
Graph: not updated (P-6).

## [2026-10-12] ingest | Step B6a — the Tool platform (C, folder 16): F-106, three decisions
Source: `Release_2/Phase_0/16_toolPlatform/` (plan, integration manifest, review dossier, hand-off to D) and the
capacity round `13_pacAllocator/implementation/plan-phase00Step1Round1-ToolPlatformCapacity.prompt.md`, at the
commits of the registry section; base `8abce8e87`. Step B6 is split in two: the PAC (folder 13) follows as B6b.
Checked on the code at HEAD:
- `ToolPlatformPolicy` defaults (1–4 items, 2 lanes, 8 pending, 4 per user, engine 30 s, 1 GiB) and the operation
  defaults (engine 4 s); `catalog_version` "2"; `_MAX_SERVICES_PER_PLUGIN = 16`; `duplicate_code` and
  `import_failed` quarantine;
- `get_current_user` on the three routes; the `spawn` context, `setsid`, the `ready` frame and the `\x00` ACK,
  `OwnedProcessTree`, `cgroup_v2_hard` and `process_tree_observed`, `claim_engine_window()`;
- `@register_plugin(ToolPluginRegistry)` on `PacAllocatorTool`, contract and implementation `1.0.0`;
  `defineToolRenderer('pac_allocator', '1.0.0', …)` in `registry.ts`;
- the commits `1656aff69`, `bb0cdc334`, `8e7259ecc`, `570beb386`, `4a38b9061`, `3913fe217`, `b82e59ffa`,
  `0210f9848`.

The dossier's risks of 2026-09-11, re-checked: the old budgets are gone from the user page (fixed); no screen shows
the memory mode, and `contracts.ts` still waits the platform's client timeout (both still true, recorded in
[[features/F-106]]). The generated codec files are git-ignored, so no page cites them.
Created:
- [[features/F-106]] (registry: 106 features, INFRASTRUCTURE 17);
- [[decisions/tool-calculation-without-authority]], [[decisions/tool-item-runs-in-owned-process]],
  [[decisions/tool-contract-from-pydantic-compiled-renderer]];
- [[sources/phase00-tool-platform-2026-09]].

Updated: [[features/registry]], [[domains/infrastructure]], [[features/F-059]], [[features/F-105]] (the unused
`tools.hub` anchor), [[decisions/provider-registry-decision]], [[decisions/plugin-folders-and-split-i18n]],
[[concepts/backend-only-calculations]].

Also: [[decisions/onboarding-existing-users-seeded-skipped]] records the developer's decision of 2026-10-12, relayed by
the coordinator — the `import.gapFix` coachmark that older accounts meet once is accepted, not a defect («Va bene così:
lo step è una novità della 1.2 e il coachmark la presenta una volta sola»); migration 004 does not change.
Graph: not updated (P-6).

## [2026-10-12] ingest | Step B6b — the PAC allocator (D, folder 13): F-107, F-108 planned, six decisions, seven problems
Source: `Release_2/Phase_0/13_pacAllocator/` — the five designs, `review/`, the fifteen `drafts/` (characterised, not
re-told) and eighteen plans of `implementation/` (Step 1, Round 1 went with B6a), at the commits of the registry
section; base `96fd88fec`. Read through eight digests of the plans, then checked on the code at HEAD:
- `pyscipopt = "==6.2.1"` in the `Pipfile`; the seven `result_state` values; `policy: Literal["proportional"]` for
  the PAC; the Rebalancer requests in the schema with no service, `normalize_rebalancer_plan` reached only by tests;
- the plugin's `claim_engine_window(post_engine_reserve_ms=_POST_ENGINE_RESERVE_MS)` (2,000 ms) and
  `solver_time_budget_seconds=window.timeout_ms / 1000`; the 3.5 s fallback marked «Not the product budget»;
- `STAGE_PIN_RELATIVE_SLACK = 1e-12`, `_flag_contradicted_bounds`, `SolverInfeasibilityContradictedError`,
  `_published_gap`; `_fee_clamp_upper`, `_fee_cap_excess`; `_require_credit_tie_free` gone;
- `validate_fx_coherence`, `allocation.fx_rate_inconsistent`, `allocation.exposure_total_exceeds_one`; `rounding_delta`
  as `ExactNumber` (`ratio_to_exact_number`); `conversion_mode` («It changes no figure of the plan»),
  `PlannerConversion`, `NoOrderCap`; `currency_specs` gone; `json_schema_serialization_defaults_required=True`, no
  `default_factory`, the `~zero~` fee instances;
- the copies endpoint (owner-only, 403, `no-store`), `POST /portfolio/wac` behind `get_current_user`,
  `refreshCopiedFacts()`; `{' '}` at the routing intro; the `DataTable` sticky-header and actions selectors;
- the regression tests named on the pages, among them `test_exhaustive_oracle_is_test_only`; the 47 commit hashes on the
  pages touched by this step, all ancestors of HEAD.

Corrections against the sources: the README calls the Remediation's §5 «sette decisioni del developer» — they are
seven questions for the developer, one answered later (Q-C0-4); the compaction's «Il fingerprint cambia una volta,
qui» held for that slice only — the FX fix and the rounding fix moved the `1.0.0` fingerprint again; the README's note
«Il P1 rimosso il 24/09» dates a removal committed on 2026-09-21 (`b82e59ffa`).
Created:
- [[features/F-107]] (CALCULATIONS) and [[features/F-108]] (`planned`); registry at 108 features;
- [[decisions/pac-scip-searches-exact-replay-certifies]], [[decisions/pac-lexicographic-fixed-l2-objective]],
  [[decisions/pac-fx-one-rate-map-direct-conversions]], [[decisions/pac-draft-copies-from-owned-data]],
  [[decisions/pac-contract-compacted-before-release]], [[decisions/pac-p1-prototype-removed]];
- [[problems/pac-solver-ran-on-default-budget]], [[problems/pac-scip-tolerance-misreported-proof]],
  [[problems/pac-fee-floor-and-cap-misread]], [[problems/pac-foreign-funding-calculation-failed]],
  [[problems/pac-tool-error-instead-of-plan]], [[problems/svelte5-trims-leading-space-in-tag]],
  [[problems/datatable-actions-column-on-mobile]] (open, a hypothesis);
- [[sources/phase00-pac-rebalancer-design-2026-09]], [[sources/phase00-pac-implementation-2026-10]].

Updated: [[features/registry]], [[domains/calculations]], [[features/F-106]], [[features/F-097]],
[[decisions/pac-rounding-against-the-plan]], [[decisions/tool-calculation-without-authority]],
[[decisions/wac-target-currency-last-acquisition]], [[decisions/financial-math-one-home]],
[[decisions/html-escape-at-the-source]], [[concepts/backend-only-calculations]], [[concepts/svelte5-runes]],
[[problems/svelte-i18n-formatter-cache-ignores-locale]], [[problems/bulk-modal-sticky-z-index]],
[[problems/datatable-column-resize-noop]], [[sources/phase00-tool-platform-2026-09]].

Note for step D: the B6a and B6b pages cite `backend/app/services/tool_plugins/pac_allocator.py`, which U-1 moved to
`tool_plugins/pac_allocator/plugin.py` in the target (train 61); they follow the map with the other plugin paths.
Graph: not updated (P-6).

## [2026-10-12] lint | Steps D and C — the plugin paths after U-1, and F-078
Base `145502a39` (train 62). U-1 is `2eed3d26c` («one folder per plugin», train 61 `bd8ee8e4d`): the 84 first-party
plugins moved with `git mv` to `<family>/<name>/plugin.py` (82 renames at 100 %, 2 at 99 %), each beside an
`__init__.py` that is only its docstring; discovery loads `plugin.py` (`PLUGIN_MODULE_NAME` in
`provider_registry.py`), the family helpers stay at the family root, and `test_plugin_layout_gate.py` guards the
layout, the imports and the strings. `frontend/src/lib/i18n/` still holds one catalogue per language: U-2 and U-3 are
later steps of plan 45.

**Before**: `check_source_paths` gave 54 missing paths in this worktree (104 occurrences, 63 pages) — on the target 44: 42
plugin modules (BRIM 16, risk 8, signal 6, FX 6, asset 6), `tool_plugins/pac_allocator.py` cited by steps B6a and
B6b, and the old `admin.py` of F-078; the other 10 are git-ignored artifacts that a worktree does not have.

**D — the map** (delivered with the checkpoint, outside the repository): 120 citations — 99 paths, 20 bare file
names, one dotted import — in 56 pages. 112 moved to `<name>/plugin.py` in 54 pages, every new path checked with `git ls-files`; by
hand, [[features/F-013]]'s layer sentence and a note on the convention in [[features/F-059]]. 8 left as written, being
history: five in this log, the old import quoted as the problem of [[decisions/provider-shutdown-generic]], a past-tense
account in [[sources/beta-testing-2026-08-05]] and a dated residual in [[sources/phase00-brim-targeted-2026-09]].
[[decisions/plugin-folders-and-split-i18n]] now records U-1 as delivered and the translations as still planned.

**C — F-078**: [[features/F-078]] (`planned`) was delivered in another form on 2026-09-09 (`ef722b552`, U4 of the urgent
import and UX fixes, [[sources/phase00-feedback-import-urgent-2026-09]]): a sortable uploader column with an avatar and
name filter, kept in the URL, for every user rather than admins only, with names from the existing
`GET /api/v1/users/search`. `backend/app/api/v1/admin.py` never existed (`git log --all` is empty), so its row gave way
to the files that do; `get_upload_by_user()` is still called only by its tests. F-078 → `implemented`; registry: 93
implemented or documented, 10 planned.

**After**: 10 missing in this worktree, all git-ignored artifacts; on main the check should reach 0.
Graph: not updated (P-6).

## [2026-10-12] ingest | Step B7 — folder 27 (release images, gallery) and folder 32 (the English docs for 1.2)
Base `3f9de8bdb` (train 63). Sources: three plans of workstream M in `27_releaseImages/` — the release images
(`742e381ec`), the translated code blocks (`5fa0cf12a`), the release pipeline with its gallery, R12 and batches 5–12
(`5983714f5`) — and the plan of workstream Q in `32_docsEnglish12/` (`425cb26d5`). The fourth plan of folder 27, the
translation round, already has [[sources/phase00-translation-round12-2026-10]]; its batches 23–24 are left to step B8.
Every symbol, path and commit was checked on this tree; every cited commit is an ancestor of HEAD.

**Created (11)**: [[problems/release-images-shipped-debug-frontend]] (a debug frontend in both images, and full = light
because the site was built before the gallery; full − light = 2,961,040 bytes, the PNGs), [[decisions/release-image-tags-latest-light]]
(«è corretto che la latest punti anche alla light…»; `-rc.N` prereleases, the symmetric tag check),
[[decisions/http-gzip-in-the-app]] (level 6, −63 % cold, −84 % warm), [[problems/translation-cleanup-flattened-code-indent]]
(`_clean_translation` step 7 on the whole document; `code_blocks.py`, ERROR `code-block-indent`),
[[decisions/gallery-is-a-release-gate-with-real-data]] (D1–D4, disposable accounts, the offline guard, reduced motion,
tall screens), [[problems/playwright-favicon-aborted-by-routes]] (`_isFavicon` + any route; `?lf-gallery`),
[[decisions/pdf-preview-viewer-only-local-assets]] (`1028a1978`; the fallback loop from `5b887dd3a`),
[[decisions/user-docs-plain-dev-manual-technical]], [[problems/docs-claimed-what-the-code-did-not-do]] (nine drifts, each
with its fixing commit), [[sources/phase00-release-images-and-gallery-2026-10]], [[sources/phase00-docs-english-12-2026-10]].

**Updated**: [[features/F-074]] (1.2 gallery rules, fixtures, status row), [[features/F-062]] (variants, frontend guard,
gzip), [[features/F-050]] (the 1.2 PDF preview), [[features/F-070]] (code-block indentation), [[features/F-069]] (the
1.2 English alignment, anchorless links from English-only pages, the serve fallback), [[concepts/ci-release-pipeline]]
(prerelease rules, links), [[decisions/docs-anchors-from-the-render]] (English-only pages link without anchors),
[[decisions/single-docker-image]] (links), [[problems/playwright-probes-ignore-timeout]] (sibling link). No feature
changed status.

**Corrections to the plans' wording, from the code**: `dev.py` no longer imports the translation commands inside
`except ImportError` — since `5dca6e2cf` (2026-10-08) it checks `_has()` first, so the reason given for a stdlib-only
`code_blocks.py` is recorded as history; the session cookie described as never `Secure` on 2026-10-08 follows
`SESSION_COOKIE_SECURE` since `11be06988`; the Tools pages Q found English-only are translated today.
Graph: not updated (P-6).

## [2026-10-12] ingest | Step B8 — M's batches 23–24, T's CL, I's plan 47, the backlog of 12/10, V-19
Base `35c4242f3` (B7 on train 63). Sources: the translation round's journal from `0ebf86178` to `dfd8284f3` (batch 23,
two pages reviewed in a live preview; batch 24, M-19); plan 43 from `d5497e40a` to `fba291f53` (CL, the localized
changelog frontend); plan 47 of I (`ace3455e2`); the backlog at `bf831ef10` (C-56…C-58, D-T1…D-T3, T-SG, T-DI, M-19…M-21),
read for ids and status. Every cited commit is an ancestor of HEAD.

**Created (8)**: [[features/F-109]] (the in-app changelog, registered: `3e3f9c41f` on 2026-09-01, localized by
`8f67f89de`), [[decisions/changelog-translated-by-chapter]] (M's file contract, lazy chunks per language, a merge keyed
on the version, the «Not translated yet» pill, one DOMPurify path; no translated file exists yet),
[[problems/docs-mathjax-looked-in-the-page-folder]] (M-19, since 1.0; `8d47c28c0`; M-21 still open),
[[problems/copy-buttons-without-http-fallback]] (M-20, open, five call sites checked at HEAD),
[[problems/mkdocs-material-tables-resist-styling]] (three CSS traps, `11339afa6`),
[[problems/line-chart-axes-lost-the-day]] (`4c05c1d85`, `8682f0bbd`; item 47-1 open),
[[problems/pnl-lines-kept-removed-brokers]] (`e72b0b56e`), [[sources/phase00-chart-axis-day-labels-2026-10]].

**Updated**: [[features/F-102]] (the guide as pros-and-cons tables, the Tailscale-over-HTTP warning, the admin
pointers), [[features/F-069]], [[features/F-062]] (formulas offline in the full image), [[features/F-055]] (plan 47),
[[features/F-106]] («Still open» now carries D-T1…D-T3), [[concepts/echarts-chart-gotchas]] (two rows: partial updates
merge by position; default labels never meet the app's language), [[concepts/responsive-4mode-layout]] (a translation
can expire the calibration: `7c66234a7` turned the Spanish `aiExport` into «Exportación IA», the sweep went red on two
bars in `denseRow`; backlog V-19; the cure planned in I's plan 48, 950 → 990 and 850 → 890, to be linked when the plan
enters the target), [[problems/broker-icon-race-condition]] (C-56, C-57), [[problems/playwright-probes-ignore-timeout]]
(T-DI beside M-18), [[sources/phase00-translation-round12-2026-10]] (batches 23–24),
[[sources/phase00-brim-scalable-2026-10]] (batch 23 in the target, the page approved),
[[sources/phase00-financial-math-home-2026-10]] (the CL section), [[domains/layout-settings]], the registry (109
features, 94 implemented or documented).

**Not filed**: C-58 (a broker-detail test past 30 s under load: a test budget to triage, no durable knowledge yet); T-SG
(the loose modules of `services/` grouped by domain, after 1.2). V-19 is in the target's backlog since train 64, not yet on
this branch: cited by id only.
Graph: not updated (P-6).

## [2026-10-12] ingest | Trains 58 and 64 — V's batch 2 and work 3 (plan 46 §11–§12)
Base `d04b87c0f` (train 65). The coordinator asked for train 64 (V's step 2a: §12.3–§12.5, V-15…V-20, cures A1–A3).
The same plan also carried V's part of train 58 (`0596e8d08`: §11, batch 2, and §12.1–§12.2), never ingested, and the
wiki still called V-1 open: both are included, so the registry row at `262515898` is true for the whole plan.

**Created (3)**: [[problems/e2e-writes-leaked-into-shared-state]] (how a write spreads — parallel inside a category,
one populate per invocation, clean-ups at one worker only; A1–A7; damage proved on the lane's database before each cure;
2a delivered in `495fb9e86`, `6d62171e3`, `e6333930c`; 2b open), [[problems/bcrypt-blocks-the-event-loop]] (V-16,
checked in `auth.py`, `auth_service.py`, `user_service.py`), [[decisions/e2e-gaps-of-1-2-before-release]] (planned:
nothing of it is in the code).

**Updated**: [[problems/open-panels-stale-after-fx-sync]] (V-1 closed, `a0722f755`), [[decisions/data-quality-proved-on-real-data]]
(the left-after list: V-1, V-5…V-7, V-9, V-10 closed), [[sources/phase00-data-quality-e2e-2026-10]] (batch 2 and work 3;
open after train 64: V-2…V-4, V-8, V-11…V-20), [[features/F-054]] (status row), [[concepts/test-isolation-classes]]
(the E2E rule), [[concepts/async-io-rule]] (the known violation). V-19 was already filed in step B8.

**Checked against the code**: `fullyParallel: true` in `playwright.config.ts` (a comment above it still says «off»;
not ours to change); the reserved quotes TTD/JMD and GTQ/HNL; `describe('Saving')` serial; the About tab's
`data-busy`; the disposable-account helpers in `fixtures/onboarding-accounts.ts`.
Graph: not updated (P-6).

## [2026-10-12] ingest | Train 66 — V-16, M's batch 25, the ✨ changelog line
Base `b91d6d902`. Sources: plan 46 §12.7 (V-16, `3aabf0916`); M's plan of batch 25,
`27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` (`81e221f4e`), with M's note for the devWiki (outside the
repository); the ✨ line of `CHANGELOG.md` (`b91d6d902`). Every claim of the note checked on the code.

**Created (3)**: [[decisions/changelog-translated-by-heading-pieces]] (`2aecd5a6f`, `e63cfb074`, `4325e03d4`; four
chapter lines identical in the four files), [[problems/mathjax-fonts-missing-from-local-copy]] (`92fb9c83e`; 22 fonts as
companions of the cached script; the M-19 spec, extended to the font faces, still waits outside the repository; M-22
open), [[problems/fast-forward-blocked-by-a-dirty-file]] (the fast-forward to `0afac8e14` over M's backlog edit).

**Updated**: [[problems/bcrypt-blocks-the-event-loop]] → resolved (`a9e0fe4d9`; the heartbeat tests of `0d6aee67c`, red
first; `reset_password`, CLI only, unchanged), [[concepts/async-io-rule]], [[decisions/changelog-translated-by-chapter]]
(**corrected**: it said no translated file existed — true at `35c4242f3`, false since `4325e03d4`; the gallery word is
`Docker`, `416faf60d`), [[features/F-109]], [[features/F-070]], [[features/F-069]],
[[problems/docs-mathjax-looked-in-the-page-folder]] (the follow-up), [[problems/e2e-writes-leaked-into-shared-state]]
(A7's damage proved; IWR-009 passes in silence).
Graph: not updated (P-6).

## [2026-10-12] ingest | Train 67 — M's batch 26: the first append, and M-23
Base `0c8412745`. Source: step 10 of `27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` (`872d42107`) and
the backlog's M-23. The ✨ line of `b91d6d902` was ported by hand into `CHANGELOG.{it,fr,es}.md` and stamped
(`98fe9ce1d`) instead of re-translating a 16.8 KB piece three times.

**Updated**: [[decisions/changelog-translated-by-heading-pieces]] (the first append, by hand), [[decisions/fr-typography-at-build-time]]
(what the build-time hook cannot reach: M-23, open, planned in 1.2 by the coordinator), [[features/F-109]] (still open:
M-23). Checked on the code: `changelog.ts` and `ChangelogModal.svelte` apply no French spacing rule.
Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R0 — the features and the map
Base `551d8cbb4`. Plan approved by the coordinator: R0 → R6, trains first; three UI features in DASHBOARD, the engine
in CALCULATIONS, no new domain; open items as «paused, after 1.2» (D382). Source of this step: the folder's README
(`107098edf`), whose code map was checked path by path on this tree.

**Created (5)**: [[features/F-110]] (engine: `services/risk/`, fifteen plugins, four endpoints, documented),
[[features/F-111]] (four levels on the Dashboard and broker pages; only the simulation rung stays beta),
[[features/F-112]] (the Lab of Asset Global), [[features/F-113]] (the legacy Asset Detail tab, beta, implemented),
[[sources/phase00-risk-integration-2026-09]] (the folder, its parts, D382).

**Updated**: the registry (113 features, 98 implemented or documented), [[domains/calculations]], [[domains/dashboard]]
(F-100 added too: it was in the registry's DASHBOARD rows but missing from the domain page).
Next: R1, the open items. Graph: not updated (P-6).

## [2026-10-12] ingest | Train 68 — M-18 CP1 (T)
Base `8730f949c` (the target merged into this branch by the coordinator). Source: plan 43, «M-18» sections (`d00c06685`),
and the code of `5b2aad5c4`. **Created**: [[decisions/figures-in-the-interface-language]] (the developer's rule, CP1
delivered, CP2 pending). **Updated**: [[problems/playwright-probes-ignore-timeout]] (M-18 moved to T, CP1),
[[features/F-008]] (status row). Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R1 — the open items
Base `86de5e903`. Source: the README's lists «Lavoro pianificato e non fatto», «Buchi veri», «Difetti noti», «Buchi nei
test», «Domande mai decise», the backlog-38 family and the `TODO_FUTURI.md` deferrals (`107098edf`, verified by their
authors on 2026-10-10). Re-checked on the code: A6, C-22 (D381 clamp; Sturges only for a zero IQR), C4, B7, B8 and
`HurtRow.secondaryLoss`. **Updated**: [[features/F-110]], [[features/F-111]], [[features/F-112]] («Still open (paused,
after 1.2 — D382)»); F-113 already carried A2 and T-DI. No problem page: every item is paused by the developer's D382,
and the README stays its single home. The post-integration review `08` is the first round's history: steps R3/R4.
Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R2 — the decisions that bind
Base `e3a55b85f`. Sources: the README's «Decisioni che vincolano il lavoro» (`107098edf`) and the thesis
`01-tesi-e-quattro-domande.md` (`245aabf97`). **Created**: [[decisions/risk-answers-four-questions]],
[[concepts/risk-binding-decisions]] (D374 and D380–D381 checked on the code). **Updated**: F-110…F-112 (a link). The
full records of `04` (1,076 lines) stay in the journal; individual pages come only where a later step needs one.
Graph: not updated (P-6).

## [2026-10-12] ingest | Train 69 — M-23 resolved (M's batch 27)
Base `d877a4e14`. Source: step 11 of `27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` (`1ed372534`) and
the code of `99aa2f4ec`, `53673ae9f`. **Updated**: [[decisions/fr-typography-at-build-time]] and [[features/F-109]]
(M-23 open → resolved in 1.2: `typesetFrench()` in `changelog.ts`). Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R3a — implementation_2, the contract and the levels
Base `4549376b8`. Sources: `implementation_2/` top files (00, A, F1, F2, PRIMITIVE, S1–S5, `_comune`, REGISTRO,
R5-tempo2), digested by an explore agent and checked here (quotes by grep; hashes and paths verified). **Created**:
[[decisions/asset-set-one-preparation-not-fan-out]], [[decisions/l3-reads-current-composition]],
[[problems/runner-catalog-merge-not-line-union]]. **Updated**: [[features/F-111]], [[features/F-112]],
[[sources/phase00-risk-integration-2026-09]]. Overtaken in the journal, noted on the pages: the contract's table of
`ASSET_SET` plugins. Next: R3b, the post-merge review R5 and the progress logs. Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R3b — the post-merge review R5
Base `e050cc142`. Source: `implementation_2/R5-post-merge-e-review.md` (`107098edf`), digested by an explore agent
(sections around the «⚠️ Fuori pista» markers; the four big progress logs were not read — their history is covered by
the review and the code). Quotes kept only where grep found them verbatim. **Created**:
[[problems/risk-stress-buckets-hand-listed]], [[problems/replay-baseline-shortened-by-late-starter]],
[[problems/echarts-stacked-band-null-base]]. **Updated**: [[concepts/echarts-chart-gotchas]], F-110, F-113, the folder
source. Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R4 — the first round, implementation/
Base `97eecde84`. Sources: `implementation/` (README, contracts K1–K9, streams, the A progress log), digested by an
explore agent; quotes re-found by grep, hashes and paths verified. **Created**: [[concepts/risk-contracts-k1-k9]],
[[decisions/histogram-grid-pinned-to-var-cut]], [[problems/annualization-factor-not-coverage]] (no delivering commit
isolated for the observed factor: cited by its code). **Updated**: [[features/F-110]], the folder source.
Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R5 — the analysis documents
Base `b4acfb250`. Sources: `00`, `02`, `03`, `05`, `06`, `07`, digested by an explore agent; quotes re-found by grep.
**Created**: [[decisions/risk-tool-verdicts]] (with today's departures: TE and IR still in the contracts and on the
legacy panel, optimization delivered as a plugin), [[decisions/risk-library-versus-own-maths]] (coherent CVaR and
vectorised rolling checked in the code). The visual grammar of `05` and the plans `03`, `07` left in the journal: the
levels pages and the features already carry what shipped. Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 02 (Risk), step R6 — the archive G0–G6; folder 02 covered
Base `843c9a9d2`. Source: `_archive-backendFirst-G0G6/README.md` (`33d5a599b`) and the archive's history since the July
ingest: archived on 2026-09-16 (`245aabf97`), aligned once on 2026-10-09 (`33d5a599b`, 4 files). **Updated**:
[[sources/phase00-risk-analysis-backend]] (what still holds, what is superseded), [[sources/phase00-risk-integration-2026-09]].
Folder 02 is now covered by steps R0–R6: 4 features, 6 decisions, 2 concepts, 5 problems and 1 source, with the open
items as «paused, after 1.2 (D382)». Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 09, step F0 — the feedback jobs
Base `dc00cbe9f`. Plan approved by the coordinator: F0 → F2, then H1 → H5 (`Ai_ideas`: a source page only, linked to
`TODO_FUTURI.md` themes). Sources: `09_feedbackJobs/README.md` and `06_piano_sprint.md` (`d614daed9`), digested by an
explore agent; the hashes verified as ancestors, the README's open items rewritten with today's paths (BU1, U-1).
**Created**: [[sources/phase00-feedback-jobs-2026-09]]. **Updated**: [[sources/phase00-feedback-import-urgent-2026-09]]
(a link). Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 09, step F1 — the structural backlog P4 and the static analysis
Base `7ff48ac9b`. Sources: `00_backlog_strutturale_P4.md` and `09_reperti_analisi_statica_20260922.md` (`d614daed9`),
digested by an explore agent; hashes verified, the two fixes re-read in the code. **Created**:
[[problems/privacy-gate-blind-to-formatter-consumers]], [[problems/missing-event-detail-read-as-consent]]. **Updated**:
[[sources/phase00-feedback-jobs-2026-09]] (the F1 statuses). Graph: not updated (P-6).

## [2026-10-12] ingest | Folder 09, step F2 — the areas and the visual review; folder 09 covered
Base `5c82d9bd4`. Sources: `01`–`05`, `07`, `08` of `09_feedbackJobs/` (`d614daed9`), digested by an explore agent
that grepped the wiki for each topic; only R2 was missing. **Created**: [[problems/stale-version-file-shadows-git-describe]]
(open; the mechanism checked in `utils/runtime/version.py` and `dev.py`). **Updated**: [[sources/phase00-feedback-jobs-2026-09]],
[[features/F-062]]. Folder 09 covered by F0–F2. Next: the historical folders H1–H5. Graph: not updated (P-6).

## [2026-10-12] ingest | Historical folder H1 — 01_signalMigration (drift and gaps)
Base `62471add2`. The four rows ingested in July (`02_aiExport/`, hash `untracked`, old `Phase_0/` path) are re-based
on `8da24ef22` and the `phases/` path; 32 files were never ingested — mostly the AI Export reports, whose outcomes the
AI Export pages already carry. Gaps found by an explore agent and checked in the code: **Created**
[[decisions/signal-indicator-warmup-sizing]], [[problems/spa-logout-cross-user-cache-leak]]. **Updated**
[[decisions/signal-backend-plugin-architecture]], [[features/F-001]]. Graph: not updated (P-6).

## [2026-10-12] ingest | Historical folder H2 — 05_cleanAudit
Base `42fc4dd7f`. Source: `phases/05_cleanAudit/` (`8da24ef22`; never ingested), digested by an explore agent that
grepped the wiki before naming a gap. **Created**: [[sources/phase00-clean-audit-2026-08]],
[[problems/asset-events-lost-on-price-cache-hit]] (`b45f5afbb`; the journal cites, for the cause, a hash that does
not resolve in this repository — `git log -S` points to `5b9dddb45`). **Updated**: [[concepts/test-isolation-classes]] (the
first `test all` that could not pass). Graph: not updated (P-6).

## [2026-10-12] ingest | Historical folder H3 — 08_newCleanAndDocumentation_audit
Base `61f7c970b`. Source: `phases/08_newCleanAndDocumentation_audit/` (`a9138140a`; never ingested), digested by an
explore agent. **Created**: [[problems/base-currency-setting-silently-defaulted-eur]] (`08b99c3ac`; the helper and its
callers checked in the code). **Updated**: [[sources/phase00-clean-audit-2026-08]] (the second audit), [[features/F-092]].
Graph: not updated (P-6).

## [2026-10-12] ingest | Historical folders H4 — 03_brokerImportRecovery and 04_webSearchEngine
Base `63121ee78`. Sources: both folders (never ingested), digested by an explore agent. 03 (the Intesa and Crédit
Agricole recovery, `0e07359b4`) is already covered by [[decisions/credit-agricole-securities-only-cash-neutral-brim]]
and the BRIM pages; its ISIN auto-binding note was too thin for a page of its own. **Created**
[[decisions/web-link-finder-ddgs]] (`ae417b9ab`; the engine settings checked in `web_link_finder.py`). **Updated**
[[features/F-028]]. Graph: not updated (P-6).

## [2026-10-12] ingest | Historical folder H5 — Ai_ideas; the historical folders covered
Base `b899903db`. Source: `Release_2/Ai_ideas/` (four files, 2026-07-20 → 08-05; never ingested). By the coordinator's
rule a source page only, no `idea` features: **Created** [[sources/release2-ai-ideas-2026-07]] (what held — signals,
then risk, the rolling chart — and the MCP assistant deferred to `TODO_FUTURI.md`, «QuarkAI»). **Updated**
[[decisions/signal-backend-plugin-architecture]] (a link). With H5, the plan of folder 09 and the historical folders
(F0–F2, H1–H5) is complete. Graph: not updated (P-6).

## [2026-10-12] ingest | Historical folder H6 — 06_betaTestingReportAndFixing (drift)
Base `6e3d1368c`. The four July rows (hashes that no longer resolve, old `Phase_0/` path) re-based on `91e88b8d1` and
the `phases/` path; three reports moved unchanged, `INDEX.md` edited. Eleven files never ingested, listed on
[[sources/beta-testing-2026-08-05]]; their topics already have pages, so no new page — a content check of the ten plans
stays a candidate for a later lint. Graph: not updated (P-6).

## [2026-10-12] lint | Follow-up of the read-only lint — two open problems re-checked
Base `4d0cedec7`. The coordinator's decisions on the lint: re-check the two stale open problems against today's E2E;
M-20 waits for I's plan 48 (FileGrid and FilesTable will be C-63); the unchecked areas become C-64. An explore agent
read the specs. **Updated**: [[problems/bulk-modal-sticky-z-index]] (not covered → open, re-test after 1.2, C-61),
[[problems/datatable-column-resize-noop]] (resize proved on the Risk Lab L1° table, `f55b2e42a`; others untested → open,
C-62). Graph: not updated (P-6).

## [2026-10-12] ingest | Train 70 — M's batch 28: the M-19 spec registered, the gallery's price guard after M-18
Base `afd7d4821` (the target `b063b16ca` merged into W). Source: M's journal of round 12, §16.7 and §17 (batch 28),
with the code of `0fe5195e8` and `e8d5a5668`, and T's CP1 note that found the guard (`43_financialMathHome`, before the
STOP). **Created** [[problems/gallery-price-guard-expected-tofixed-text]] (resolved: red in English on prices over
1,000, unseen because the runner excludes the gallery; the first control could not fail). **Updated**
[[problems/docs-mathjax-looked-in-the-page-folder]] and [[problems/mathjax-fonts-missing-from-local-copy]] (the spec is
in the repository, `front-utility docs-offline-math`), [[decisions/figures-in-the-interface-language]] (a consequence
for tests), [[decisions/gallery-is-a-release-gate-with-real-data]], [[features/F-069]],
[[sources/phase00-translation-round12-2026-10]] (batch 28; its stale «M-14 still in progress» line corrected). Graph:
not updated (P-6).

## [2026-10-12] lint | C-64, part 1 — the unfinished features against today's code
Base `0bd1a8368`. Asked by the coordinator before the tag, so that the wiki says what 1.2 really contains. Two explore
agents read the code and the history of the 14 features not `implemented` or `documented`; F-048's findings were
re-checked by hand, on the code and on the trees of `v1.0.0` and `v1.1.0`. **Updated** [[features/F-048]]
(`in-progress` → `documented`: its four open items were delivered and shipped in 1.0.0, `dce60a5ee`; residuals K-1 …
K-4 in backlog 38), [[features/registry]] (row, note, statistics: 99 shipped, none in progress),
[[domains/transactions]], [[domains/brokers]], `index.md` (Domains row). Unchanged after the check: F-077, F-079,
F-081, F-082, F-084, F-087, F-091, F-094 and F-108 (contract only) stay `planned`; F-085, F-093 and F-096 stay `idea`.
Listed to the coordinator, not touched: F-090 (parts built under F-051, the provider-change modal and the reverse
lookup not), F-094 (borderline), page drift on F-082, F-090 and F-096. Graph: not updated (P-6).

## [2026-10-12] lint | C-64, part 1 — the coordinator's decisions on F-090, F-094 and three page defects
Base `f83a1486d` (C-65 and C-66 in the backlog). **Updated** [[features/F-090]]: stays `planned`; what was built under
[[F-051]] is listed with its paths (the `RESTRICT` FK, `delete_events_bulk` with an outcome per id, the link field and
rule 9, the event picker), the 409 it promised is gone, and the rest — the provider-change modal, the reverse lookup —
points to C-65, with the `TODO_FUTURI.md` entry on suggested links as a neighbour. [[features/F-094]]: stays
`planned`; the three sync dialogs on `SyncModalBase` sync the page's range, the warning on existing data is C-66.
Page defects fixed: [[features/F-082]] (the staging modal's path), [[features/F-096]] (its two tables separated, the
editor's path), [[domains/signals]] (`status: stable`, as in the index and the registry). [[features/registry]]: the
C-64 note cites C-65 and C-66. `index.md`: F-048's row in «Individual Feature Pages» still said `in-progress`, missed
in part 1 — now `documented`. Graph: not updated (P-6).

## [2026-10-12] ingest | Train 71 — U-2 (the catalogue built from its sources), M's batch 29, a merge that died on a lock
Base `c57acf510` (train 71, gates green). Sources: plan 45 §10 (U-2) and the code of `1b31f9057`; backlog U-B6; M's
journal of round 12, §18 (batch 29, `18e872872`); the coordinator's report on train 71, with the mechanism checked in
Git's own sources at v2.53.0. **Created** [[problems/git-merge-stash-failed-on-locked-index]] (Git 2.53 runs
`git stash create` before every real merge; an IDE or a watcher holding `index.lock` killed it before it started;
workaround: the train retries up to 5 times). **Updated** [[decisions/plugin-folders-and-split-i18n]] (U-2 delivered:
generated catalogue, sources in `base/`, read-only and stamped, hooks, gate `utils gate-i18n-catalog`; U-3 and U-B6
open), [[features/F-008]], [[sources/phase00-translation-round12-2026-10]] (batch 29),
[[problems/fast-forward-blocked-by-a-dirty-file]] (see also). **Paths**: U-2 moved the four catalogues, so 28
citations of `frontend/src/lib/i18n/<lang>.json` in 13 pages and 5 written as `{en,it,fr,es}` now point to `base/`;
`$lib/i18n/en.json` imports stay (they name the generated file). Graph: not updated (P-6).

## [2026-10-12] ingest | Train 72 — I's plan 48 (UI polish) and V's step 2b (the E2E cleanup)
Base `0071b9703` (train 72, gates green). Sources: plan 48 and plan 46 §2b, digested by two explore agents, with the
quotes, paths and figures re-checked on the files and the code. **Created** [[sources/phase00-ui-polish-2026-10]],
[[problems/late-img-error-marked-the-visible-icon-failed]] (`2412c3fe4`), [[problems/test-passed-only-on-leftovers-of-other-tests]]
(WB5, `1ea16aace`, linked to the isolation classes), [[problems/toolbar-measurements-differed-by-the-scrollbar-gutter]]
(V-19, `7f8febd9d`), [[decisions/clipboard-through-one-helper-with-a-gate]] (M-20 and C-63, `65d20910e`),
[[decisions/security-details-close-after-30-seconds]] (`5e9eff52d`). **Updated** [[problems/broker-icon-race-condition]]
(the October symptoms had another cause; C-56, C-57 open), [[problems/copy-buttons-without-http-fallback]] (resolved),
[[concepts/responsive-4mode-layout]] (the cure delivered), [[problems/e2e-writes-leaked-into-shared-state]] (checkpoint
2b; V-21, V-17, V-18 still open), [[sources/phase00-data-quality-e2e-2026-10]], [[features/F-102]],
[[decisions/plugin-folders-and-split-i18n]] (I's batch reached `base/` through the rename). Graph: not updated (P-6).

## [2026-10-12] lint | C-64, part 2 — dates and hashes in conflict between pages
Base `fef272b65`. A script compared each of the 1 567 backticked hashes with the date written beside it and with Git;
two explore agents compared trains, versions, archive dates, backlog and decision IDs, feature status events and
batches across pages. **No real conflict**: every date that differs from a commit's own belongs to another event (the
decision's date in the index's Date column, a report, an archive, a range such as `2026-06-08/09`); the two commits
with one subject, `3e3f9c41f` and `f32e460ca`, are a parent and its follow-up, each cited for its own change; every
dated train has one date. **A history rewrite**: 98 cited 7–8-character hashes resolve to nothing in today's
repository (5b1333fa6b07 is an Alembic revision, not a commit). Six were matched to today's commit by subject and
date and replaced in the pages (17 citations): 615a52eb → `c9f840680`, 78aaa0a3 → `13052a006`, ddb1fcfb →
`93a88be2c`, a688bcb9 → `dadcc4de2`, b5a0bf9 → `82c9224d5`, a7b30d52 → `432d8642a`. Left: 23 in the pages,
whose match is ambiguous (F-098's four, 3184a969/1a734008, …), and the citations in this log and in the ingest
registry, kept as written. Graph: not updated (P-6).

## [2026-10-12] lint | C-64, part 2 — the history rewrite of 2026-09-04, remapped exactly
Base `d88e10d15`. The repository's history was rewritten with `git filter-repo` on 2026-09-04: every older commit got
a new hash, so the hashes written before that day — in this log, the ingest registry and some pages — resolve to
nothing. With the rewrite's commit map (1 125 old → new pairs, a copy provided by the coordinator), 74 such hashes were
mapped to today's commits, each unique and an ancestor of HEAD: 48 citations in the pages and the index, 165 in
[raw/ingest-registry.md](raw/ingest-registry.md), whose drift check works again. The six matched earlier by subject
and date agree with the map. This log keeps its old hashes as written: look them up in the map. Not a commit, left
as is: an Alembic revision id. Graph: not updated (P-6).

## [2026-10-12] lint | C-64, part 2 — the dates the remap brought to light
Base `8ba2db509`. The coordinator's decisions: beside a hash goes its commit's date. `c7cf528c4` (Policy D, the backup
router) is dated 2026-04-24, its commit's date, in [[decisions/policy-d-currency-wipe]], [[entities/backup-router]]
(twice) and [[sources/phase07-part3-closure]] — all four sentences describe the commit itself; [[features/F-099]]'s
status row goes to 2026-05-30, the date of `9b9fcbb65`. In the ingest registry, the knowledge-base overview's row
linked a page that never existed: it now names the two concepts that draw on that source. Graph: not updated (P-6).

## [2026-10-12] ingest | Train 74 — U-3 (the catalogue split), M's batches 30–32
Base `bcd502912` (fast-forward). Sources: plan 45 §10 (U-3), checked on the code (18 folders under
`frontend/src/lib/i18n/`, 71 plugin fragments, the new gate); M's journal of round 12, §19–§21; the backlog. **Updated**
[[decisions/plugin-folders-and-split-i18n]] (U-3 delivered: `base/` 288 keys, 17 subsystems with 3 844, 71 fragments
with 219, the merged catalogue identical; the coordinator's D-U3-1 and D-U3-2; gate `utils gate-plugin-i18n-ownership`,
R1–R4; U-4 and U-5 to come), [[features/F-008]], [[sources/phase00-translation-round12-2026-10]] (batches 30–32),
[[problems/gallery-price-guard-expected-tofixed-text]] (the header of `galleryLocale.ts` rewritten, `172211a89`),
[[decisions/security-details-close-after-30-seconds]] (I5 prepared), [[decisions/figures-in-the-interface-language]]
(the CHANGELOG announces the whole rule ahead of CP2 and CP3), [[decisions/clipboard-through-one-helper-with-a-gate]]
and [[problems/toolbar-measurements-differed-by-the-scrollbar-gutter]] (C-63, M-20, V-19 closed, `2166eeb90`). No path
broke: `base/` stays. Graph: not updated (P-6).

## [2026-10-13] ingest | Trains 75 and 76 — M-18 closed (T's CP2, CP3), the seven E2E gaps of 1.2 (V)
Base `986e99bd3` (fast-forward). Sources: plan 43 (M-18 CP2, CP3a, CP3b) and plan 46 §12.9, digested by two explore
agents, with the paths, the hashes and the figures (−175 EUR, WAC 150, en-GB, `formatExactDecimal`) re-checked on the
code. **Updated** [[decisions/figures-in-the-interface-language]] (delivered: amounts, dates, axes, exact decimals;
M-17 resolved; what is left for after 1.2), [[features/F-008]] (its rows of 2026-10-12 put in order),
[[problems/playwright-probes-ignore-timeout]] (M-17, M-18), [[decisions/e2e-gaps-of-1-2-before-release]] (delivered,
the seven specs and their figures), [[problems/e2e-writes-leaked-into-shared-state]] (the files spec cleans up; V-25
open), [[sources/phase00-data-quality-e2e-2026-10]]. The M-18 lines of the CHANGELOG (`e7bfa342f`), noted in train 74
as ahead of the code, now describe it. Graph: not updated (P-6).

## [2026-10-13] ingest | Trains 77 and 78 — I's lot 49, M's batch 33, U-4; a dirty version in the release shots
Base `1c710c7a8` (fast-forward). Sources: plan 49, M's journal of round 12 (batch 33, M-24), plan 45 (U-4), the backlog,
and the coordinator's report on the release shots; every claim checked on the code. **Created**
[[problems/request-counter-read-before-the-handler-counted]] (`waitForRequest` resolves before the route handler
counts; `waitForCountedRequest`, `6a1d95d85`) and [[problems/release-shots-show-dirty-version]] (open: Vite's
`git describe --dirty` after the workflow writes tracked files; cure in M's lot 34). **Updated**
[[decisions/plugin-folders-and-split-i18n]] (U-4 delivered, U-B7, U-5 left), [[features/F-008]],
[[decisions/security-details-close-after-30-seconds]] (I5 applied, `2d0ca1660`), [[problems/playwright-probes-ignore-timeout]]
(M-24), [[sources/phase00-ui-polish-2026-10]], [[sources/phase00-translation-round12-2026-10]]. U-B5's devWiki part
was done in step D. Graph: not updated (P-6).

## [2026-10-13] ingest | Train 79 — T-EN1 and T-EN2
Base `b1a17b49b`. Sources: plan 43 («T-EN»), the backlog, the code of `f31bd6cfd` and the CHANGELOG line `4e11c2f83`.
**Updated** [[decisions/figures-in-the-interface-language]] (T-EN1, T-EN2 closed; `ChartSignal`'s tracked catalogue;
T-ISO and T-FB for after 1.2), [[decisions/plugin-folders-and-split-i18n]] (the first `i18n add` after U-3, routed to
`charts` and `assets`), [[features/F-008]]. Graph: not updated (P-6).

## [2026-10-13] ingest | Train 80 — U-5 and plan 45 closed; M's batch 34 (the dirty version)
Base `cea8a478d`. Sources: plan 45 §10 (U-5 and the detours of U-2 and U-3), M's journal of round 12 (batch 34), the
backlog, the code of `741310647`, `428bf27d1` and `b816adc6c`. **Created**
[[problems/shared-server-rebuilt-the-frontend-past-its-startup-timeout]] and
[[problems/editing-a-running-bash-script-corrupts-its-run]]. **Updated** [[decisions/plugin-folders-and-split-i18n]]
(U-1 to U-5 delivered, plan 45 closed, its four findings; U-B5 closed, U-B2 after 1.2),
[[problems/release-shots-show-dirty-version]] (resolved in the code: `LF_APP_VERSION`, the tree checks, the icons by
the logo's hash; to verify on the first nightly; M-25), [[sources/phase00-translation-round12-2026-10]]. Graph: not
updated (P-6).

## [2026-10-13] ingest | Train 81 (I's lot 50) and R's full run with coverage
Base `5b169189d` (train 81 and the coordinator's `588223c6f`). Sources: plan 50 and the code of `c58d48a6a`; R's
report, archived in the post-1.2 backlog folder (§0, §3.2, §3.3). **Created** [[sources/r-full-run-coverage-2026-10-12]],
[[problems/jscoverage-teardown-spends-the-test-budget]] (open), [[problems/login-returns-before-the-app-has-started]]
(open, V-27), [[problems/broker-detail-tests-over-budget-under-load]] (C-58, resolved). Graph: not updated (P-6).

## [2026-10-13] ingest | Train 82 — V's §12.10: V-29, V-25, V-21 in part, V-26
Base `273b188ea` (fast-forward). Sources: plan 46 §12.10, the backlog, the code of `e6019f349` and `5d5c7caed`.
**Created** [[problems/hidden-pair-half-survived-row-removal]] (V-29: `removeRow` left the hidden partner, a false
«Discard changes?» since 1.1.0). **Updated** [[problems/e2e-writes-leaked-into-shared-state]] (V-25 cured, V-21 in
part, the calendar-driven seed rates), [[concepts/test-isolation-classes]] (the owned-pair fixture),
[[problems/login-returns-before-the-app-has-started]] (V-27 now in the backlog; V-26 closed), [[features/F-048]],
[[sources/phase00-data-quality-e2e-2026-10]]. Graph: not updated (P-6).

## [2026-10-13] ingest | Train 83 — the 1.2 CHANGELOG reviewed line by line; M's full gallery
Base `9686ee1f2`. Sources: the chapter [1.2.0] after `60f734e08`, the summaries of T's and I's review reports (working
files outside the repository), the backlog (`b2a21bb4a`), M's gallery report of I5 part two (outside the repository),
V's correction on the jsCoverage teardown; the code checked for the WAC endpoint, the fixture and `data-dist-pct`.
**Created** [[decisions/changelog-entry-rules]], [[problems/portfolio-wac-endpoint-answered-anyone]] (resolved),
[[problems/schwab-favicon-blocked-by-orb]] (open). **Updated** [[problems/jscoverage-teardown-spends-the-test-budget]]
(the teardown counts against the after-hooks slot, not the body; V-28), [[decisions/figures-in-the-interface-language]]
(`data-dist-pct`). Graph: not updated (P-6).

## [2026-10-13] lint | The feature pages against the verified 1.2.0 CHANGELOG
Base `34b9593c6`. An explore agent mapped the 46 items of the chapter [1.2.0] — 43 under ✨ Added, sub-items included,
and three under 🔄 Changed (Risk out of beta, the purchase cost, the figures) — to the feature pages; every match and
every commit cited was checked. **Updated**: 23 feature pages each gained a row dated 2026-10-13 that names the
CHANGELOG line by section and beginning, with the commit or the train. No page had a lagging status. **Created**
[[features/F-114]] (Benchmark assets, `00d8c735b`), with the registry (114 features), the ASSETS domain and the index.
Left: five items whose commit is not identified (asset types, allocation families, the ‹ › arrows, the FX route
metadata, the banners that lead to their rows); the Scalable importers have no page of their own (F-013 and a
decision cover them); the plans of `phases/06_betaTestingReportAndFixing` (C-64's last part). Graph: not updated (P-6).

## [2026-10-13] lint | C-64 closed: the plans of phases/06_betaTestingReportAndFixing against the wiki
Base `fa93b1777`. Three read-only agents read the ten plans and the F1–F17 classification in full; every gap and every
commit was re-checked on the code and on git history (one claimed contradiction, the drawdown default, was false:
`DrawdownParams.full_history` is `True`). **Corrected**, pages that contradicted the code: [[features/F-083]]
(parsing is concurrent since `d1e04b2b8`), [[concepts/txstore-pattern]] (a clone keeps its date, `59087c74a`),
[[entities/portfolio-engine]] (the blob cache key has no dates and carries the access fingerprint; a hit needs the
exact end). **Created** [[decisions/asset-identity-quoted-code-leads]] (D1–D11), [[decisions/import-row-split-legs-sum-to-the-row]]
(B5-lite), [[problems/fx-error-dedup-went-quadratic-under-full-history]], [[problems/asset-merge-cascade-deleted-the-migrated-events]],
[[problems/portfolio-cache-ignored-role-and-share]]. **Updated** [[features/F-024]] (merge, inactive assets),
[[features/F-049]], [[features/F-062]] (F13, the 2 GB image), [[concepts/transaction-hygiene-fixture]] (D-3.3),
[[concepts/derived-test-inventory]] (detour 15), [[decisions/drawdown-full-history-warmup]] and
[[sources/beta-testing-2026-08-05]] (the check, and the smaller findings listed but not paged). Found on the way: the
[1.1.0] CHANGELOG line «Wizard rework» puts corrections before unification, while `v1.1.0` already had `assets`
before `fix`. With this part, C-64 is complete. Graph: not updated (P-6).

## [2026-10-13] ingest | The release page of 1.2.0, in draft
Base `2b1734e76`. **Created** [[sources/release-1.2.0]], status draft, «tag date: pending». From the verified chapter
[1.2.0] of `CHANGELOG.md` (`60f734e08`: 25 ✨ with 27 sub-items, 149 🐛 in 13 groups, 32 🔄, 7 ⚠️), the feature pages
that carry a 1.2.0 row (24, grouped by area), the 60 decision pages dated 2026-09-07 → 2026-10-13 (grouped by theme),
the problem pages still open, workaround or recurring (14) with their backlog ids, and the checks already on record:
R's full run ([[sources/r-full-run-coverage-2026-10-12]]) and M's full gallery of 2026-10-13 (242 passed, 9 failed,
1 skipped). Left to fill at the tag: the tag date, R's final run, the gates and the gallery at the tagged commit, the
first nightly after the push (M-25) and the final CHANGELOG counts. Inbound links from
[[decisions/changelog-entry-rules]] and the R source page. Graph: not updated (P-6).

## [2026-10-13] ingest | Trains 84–91 — M's lots 35–38, T's last fixes, V's budgets, I's lot 51
Base `fa6299689`; three read-only digests of the journals, every claim re-checked on the code and on git.
**M** (lots 35–38): [[sources/phase00-translation-round12-2026-10]] — the [1.2.0] chapter re-translated with 136
fixes from the catalogues, the two sync buttons, M-26 to M-29, «tipo de cambio»; [[problems/schwab-favicon-blocked-by-orb]]
corrected: the gallery's four reds were also our own favicon mark (`6bb79fecd`), and Schwab falls to the plugin's
generic icon; still open (U-B3). **T**: [[sources/phase00-financial-math-home-2026-10]], [[features/F-111]] (the shock
table), [[decisions/figures-in-the-interface-language]] (T-ISO and T-FB pulled into 1.2 and delivered); created
[[problems/test-hooks-read-the-localized-text]]. **V** (train 87): resolved [[problems/jscoverage-teardown-spends-the-test-budget]]
(V-28, title corrected) and [[problems/login-returns-before-the-app-has-started]] (V-27);
[[problems/e2e-writes-leaked-into-shared-state]] (`fx-destructive`, the asset specs); [[sources/phase00-data-quality-e2e-2026-10]].
**I** (lot 51): created [[problems/event-markers-lost-in-the-last-partial-period]] (R-5); [[concepts/echarts-chart-gotchas]]
gained the time-axis label rule. [[concepts/responsive-4mode-layout]] was updated by workstream I in `437e74066` (the
width sweep in four languages, the phone pill): recorded here, and checked against the code — `pillWidthClass`, the
pill test in `toolbar-width-sweep.spec.ts`, `3e5313d3e` after `v1.1.0`, the measures of plan 51. Also
[[sources/release-1.2.0]] (two problems resolved, R-5 among the released defects, the gallery's group A corrected).
Not filed: V-35, which has no record in the tree yet. Graph: not updated (P-6).

## [2026-10-13] ingest | Trains 92–93, the coordinator's commits, C-60 and V-3 decided
Base `9313f81ee`. **V** (train 92): V-36 closed (`fccf0bee1`, `setLanguage` waits for the dictionary) — recorded on
[[problems/login-returns-before-the-app-has-started]]; V-35 under observation, with `aria-expanded` and a panel log
(`a67f89661`, `84cdf6dbb`) — [[sources/phase00-data-quality-e2e-2026-10]]. **T** (train 93): the open period's
tooltip (`341c77811`, `bucketSpanUpTo`) and T-EVW closed — [[problems/event-markers-lost-in-the-last-partial-period]]
(its 🐛 line now in the chapter, `fcc4ac96f`, `ef666fdee`), [[sources/phase00-financial-math-home-2026-10]].
**Coordinator**: the risk API stable from 1.2 except the simulation (`4de042cfe`) — [[features/F-110]],
[[sources/release-1.2.0]]; V-8 and V-22 after 1.2; C-72, whose wiki part was this lot's to do:
[[problems/svelte-template-branches-not-instrumented]] corrected — the empty `branchMap` was V8's, and `2e104b919`
(2026-08-30, in 1.1.0) already counted the template's branches with istanbul; status accepted → resolved. The stash
rule is in `.github/agents/release-coordinator.agent.md` (`6e1a2ef3e`): [[problems/git-merge-stash-failed-on-locked-index]]
links it (ask the developer first) without copying its seven steps. **Created** [[decisions/python-stays-on-3-13]]
(C-60; the 12/10 report as the baseline of the next comparison) and [[decisions/orphan-transfer-becomes-an-adjustment]]
(V-3; not in the code, after 1.2), linked from [[decisions/single-docker-image]], [[features/F-062]] (whose
dependency line was also corrected: the toolchain lives in the builder stage), [[decisions/transfer-pair-same-asset-opposite-quantity]]
and [[decisions/data-quality-proved-on-real-data]]. Graph: not updated (P-6).

## [2026-10-14] ingest | Trains 94–99 and the coordinator's commits
Base `bae15c3cf`; four read-only digests, every claim re-checked on the code and on git. **C-59** (`ce09c6ac4`):
uvicorn's extras in the lock — [[decisions/single-docker-image]], [[decisions/python-stays-on-3-13]]. **U-6/U-6b**:
the bundled Schwab logo undone by the developer — [[problems/schwab-favicon-blocked-by-orb]] now *accepted*, with his
hypothesis (our bursts of requests); Scalable without exporter 1.0.0 and D4 «Tagesgeld» on
[[decisions/scalable-two-accounts-two-plugins]]. **V** (trains 94–96): created [[problems/transaction-form-saved-a-refused-date]]
(V-37, since v1.1.0; V-37b after 1.2); T1, T4, V-38 on [[sources/phase00-data-quality-e2e-2026-10]]. **I, lot 52**:
three rows in [[concepts/echarts-chart-gotchas]] (`containLabel` and the unrounded time extent, `outerBounds` before
`hideOverlap` — a3, not (a) — and `dataZoom` linear in time, Z2); the running period on every chart on
[[problems/event-markers-lost-in-the-last-partial-period]]. **I-M30, plan 54**: created
[[problems/gallery-fixture-normalizer-scaled-ratios]] — no numbers, no detail of the scale; linked from
[[concepts/ci-release-pipeline]] and [[decisions/gallery-is-a-release-gate-with-real-data]]. **T-PAC, plan 53**:
[[features/F-107]] and [[decisions/pac-rounding-against-the-plan]] (the margin is in the computation). **M**: batches
39–42 and the final gallery on [[sources/phase00-translation-round12-2026-10]]; [[features/F-106]] (Tools stable).
**The dirty version** verified on pipeline run 77 — [[problems/release-shots-show-dirty-version]]. And
[[sources/release-1.2.0]]. Graph: not updated (P-6).

## [2026-10-14] ingest | Release day — the release page of 1.2.0 ready for the tag
Base `a28beed92` (the chapter's introduction and date). [[sources/release-1.2.0]]: status `ready-for-tag`, the date
2026-10-14, the approved introduction quoted as it stands in the chapter (checked identical), the counts at
`a28beed92` (25 ✨ with 27 sub-items, 152 🐛 in 13 groups, 32 🔄, 7 ⚠️), R's final run on `10e646f79` (0 reds;
pytest 12 936, vitest 11 515, Playwright 1 221; backend 91.54 %, frontend 71.17 %, a lower bound for its E2E part),
the green gallery (251/0/1, then 20/0 and, after I-M30, 10/0), the gates, the developer's decision on the gallery
fixture (option (a), published as it is — no figure of the fixture anywhere), and the backlog C-79…C-84 with M-33. The
table «To fill at the tag» is filled except two rows that exist only after publication — the tagged commit and the
release pipeline's run — which the next ingest fills. Also [[problems/gallery-fixture-normalizer-scaled-ratios]] (the
decision), [[sources/r-full-run-coverage-2026-10-12]] (a pointer to the final run), and a C-82 note on
[[problems/jscoverage-teardown-spends-the-test-budget]] and [[problems/login-returns-before-the-app-has-started]].
Graph: not updated (P-6).

## [2026-10-14] file | The promotional video project leaves the repository
`mkdocs_src/videoClipPrject/` (64 tracked files, ~22 MB) is removed, with `./dev.py mkdocs video` and its skill section:
the project lives in the business repository since 2026-10-14 (`media/video/`). The history is not rewritten — the
folder stays in the tags v0.9.0 to v1.2.0. Updated [[entities/video-promo-remotion]]: moved out, and its source files
are now what the video's asset sync still reads here (the gallery screenshots and `docs/static/`, through
`LIBREFOLIO_MKDOCS_SRC`). A note on [[sources/source-code-v0.9.0-batch]]. Graph: not updated (P-6) — graphify 0.9.54 no
longer indexes the corpus's out-of-root symlinks.

## [2026-10-14] file | Repository cleanup after 1.2.0
Besides the video project: the early UI mockups (`mkdocs_src/docs/POC_UX/`, 75 images, ~158 MB, always excluded from
the docs build) leave the repository, with their `exclude_docs` entry, the `/POC_UX/` segment in the two docs scripts
and the `POC UX` entry of `EN_ONLY_SECTIONS` — updated [[concepts/mkdocs-suffix-i18n]]. Also gone: `dev.sh` (the
messages that still suggested it name `./dev.py` now), the unused `engineering-skills` pack, the stray root
`graphify-out/` and 26 leftovers of the June semantic run in `graphify-out/` (`.chunk_files_*.txt`,
`chunk15_summary.json`; `cost.json` stays, graphify protects it). The history is not rewritten: everything stays in the
tags up to v1.2.0. Graph: not updated (P-6).

## [2026-10-14] ingest | Release 1.2.0 published — the release page is `released`
The two rows that existed only after publication are filled on [[sources/release-1.2.0]]: the tag `v1.2.0` is on
`cf00fac7d`, the merge of PR #46 into `main`, with the tree of `a3fe2eb04` on `dev_release2`; the release pipeline's
run 38540086298 is green (images `1.2.0`, `1.2.0-light` and `latest`, the `docker pull` lines on the GitHub release,
the docs site deployed from `cf00fac7d`). Status `released`; index row updated. Graph: not updated (P-6).

## [2026-10-15] file | Account link tokens travel in the URL fragment
Release 1.3, workstream A, lot A5b. A review of the A5a docs found that `/invite?token=…` would put the token in
uvicorn's access log (on in the Docker image) and in any proxy log; the token now travels in the fragment, before
A5a was integrated. Filed [[decisions/link-tokens-in-the-url-fragment]]; updated [[domains/auth]] (registration
modes, invitations, admin API, limit, K-5 until A7, what comes next in workstream A) and [[features/F-001]] (the
register link reads `GET /system/instance`). Graph: not updated (P-6).

## [2026-10-15] file | Colours factored into lib/theme at pixel parity (workstream R)
Workstream R of the colour programme (`Phase_1/10_colorSystem`) closed: lots A–D entered `dev_release2` with
`8fd8e494b` after one gallery gate (2 370 identical, 454 changed, all content or the shots' own noise). The decision
page records the modules of `frontend/src/lib/theme/`, the rules (same values, divergences kept under a name), the
proofs and what phase B inherits. Two problems filed:
- esbuild rewrites colours in some declarations but never in custom properties, so tokens hold the build's emitted
  text;
- the colour ratchet's `--resolve` drops a colour accepted on one side (backlog R-8, for T).

Pages updated:
- [[features/F-007]]: a drift corrected; charts follow the theme through `onThemeClassChange()`, not store
  subscriptions;
- [[features/F-098]]: a change to `offline.html` ships with `sw.js` restamped (`23f6578f3`);
- [[problems/front-check-does-not-check-what-you-think]]: a merge can make the generated client stale.

Filed: [[decisions/colour-factorisation-at-pixel-parity]], [[problems/esbuild-colour-minify-skips-custom-properties]],
[[problems/colour-ratchet-resolve-drops-an-accept]]. Graph: not updated (P-6).

## [2026-10-15] file | Asset event saves all or nothing — workstream W, lot E1 (decisions 20–23)
Release 1.3, workstream W, lot E1, filed from plan 04 (sections «Analisi di E1», «E0», «E1»), the decisions file
(points 20–23) and the code, every claim checked on the worktree.

What the lot is:
- E1a (`a2fb6936f`) and E1c (`313dde70e`) entered `dev_release2` with `14d58cc61`;
- E1b and its docs were still uncommitted in W's worktree.

The decision page covers decisions 20–23 and the coordinator's «one request» (`delete_ids`):
- a save that is one transaction, with structured refusals;
- `mode: "create"` and the existing-events panel;
- the scoped `DELETE` and the type check;
- the post-migration fix `event_types`, with the framework's `row_count_changes()`;
- the editor's one-`POST` save, the translated refusals and the picker's re-read.

A correction landed while filing (W, 17:50, found by the docs-writer). The first E1b cure let `delete_ids` take
manual events only, so a save that deleted a provider's read-only row was refused whole. Now:
- `_delete_item_events()` (renamed from `_delete_manual_events()`) takes any event of the asset, as in 1.2;
- `EVENT_NOT_DELETABLE` covers only unknown, gone, or other-asset ids;
- `EVENT_IN_USE` covers any linked event.

The decision page records both, and S3's contract holds.

Three problems filed, from E1b's reds:
- a provider event dated today waits for a later sync (X's area, open);
- a `SimpleSelect` list under the sticky table header (W-B26, open);
- `@testing-library/svelte` reading a prop named `events` as a mount option.

The fourth discovery, pysqlite's deferred `BEGIN`, was already filed on 2026-09-10: its page gains the recurrence
W-B20 instead of a duplicate.

Pages updated:
- [[features/F-031]]: the routes, the model's real fields (`details` JSON never existed), the 1.3 notes and sources;
- [[features/F-090]]: the scoped `DELETE`, the editor's `EVENT_IN_USE`, and the reverse lookup built on 15/10
  (C-65b, `5e96df752`), noted in [[features/registry]] too;
- [[problems/asset-event-edit-delete-reinsert]]: I-09…I-12 closed, I-11b open as W-B16;
- [[domains/assets]], [[problems/datatable-actions-column-on-mobile]] and
  [[problems/sqlite-savepoint-without-write-begins-as-transaction]].

`check_source_paths.py` gives 5 missing (8 occurrences) before and after, all pre-existing. No ingest-registry row: a
file operation, like the other entries of 15/10.

Filed: [[decisions/asset-event-saves-all-or-nothing]], [[problems/provider-event-dated-today-not-synced]],
[[problems/select-list-under-the-sticky-table-header]], [[problems/testing-library-events-prop-read-as-mount-option]].
Graph: not updated (P-6); graphify is not available in this worktree.

## [2026-10-15] file | A mutation restored with its old file time skips the frontend rebuild
Found by test-author during the Backup tab E2E mutations (workstream B, lot B5a): the runner's staleness check compares
file times, so a restore with `cp -p` would leave the mutated bundle in place for the «final green» run.
Filed: [[problems/mutation-restore-keeps-old-mtime-skips-frontend-rebuild]]. Graph: not updated (no graph in this
worktree).

## [2026-10-15] file | Category axes under zoom, and the AI Export button — workstream Y, lot Y8
Y's lot Y8 closed two items the wiki still listed as open, and taught one ECharts rule.

- 47-1: on a phone, a zoomed category axis kept the compact `interval` computed for every point. The policy now takes
  the visible count (`visiblePointCountFromZoom`, read from the event), and `LineChart`, `CandlestickChart` and
  `PriceChartFull` merge `categoryAxisLabelPatch()` once the gesture settles.
- The rule: a `setOption` merge keeps every key the patch omits, so the patch always sets `interval: 'auto'`. Filed as a
  row of [[concepts/echarts-chart-gotchas]].
- 48-1: the AI Export trigger and the Dashboard's `sync-button` use `gap-1.5 px-2.5`, like the other toolbars.

Pages updated: [[problems/line-chart-axes-lost-the-day]], [[problems/toolbar-measurements-differed-by-the-scrollbar-gutter]],
[[concepts/echarts-chart-gotchas]] and their index rows. `check_source_paths.py` gives 5 missing (8 occurrences) before
and after, all pre-existing.

Filed: [[concepts/echarts-chart-gotchas]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-15] file | Correction: 47-1 was not a phone-only defect
The Y8 entry above says «on a phone». The compact axis policy also applies below 24 px per point, so a long period lost
its labels under zoom on desktop too: 33 is the step for a year of days in an 800 px chart, 90 or more on a phone.
Corrected in the row of [[concepts/echarts-chart-gotchas]]; the CHANGELOG line was already right.
Graph: not updated; graphify is not available in this worktree.

## [2026-10-15] file | DataTable on phones and column resize — workstream Y, lot Y7
Y's lot Y7 closed the two DataTable problems the wiki still held as open or as hypotheses.

- [[problems/datatable-actions-column-on-mobile]]: the hypothesis of 2026-10-10 was right, confirmed red in a browser
  (`layout/datatable-mobile.spec.ts`). At 768 px and below the selection and actions columns now scroll with the
  table, header and cells alike (D-Y17). The lesson is the specificity: a bare class cannot undo a pin that a
  `thead … th` rule carries.
- [[problems/datatable-column-resize-noop]]: the old cause («`onColumnResize` not read by the parent») was wrong.
  Measured: auto layout shares spare width in proportion to the given widths (+57 px for a +80 px drag), the drag
  started from the configured width, and the handle answered the mouse only (D-Y18). The cure follows the drawn width,
  uses Pointer Events, and pins a resized column's width as its minimum.
- The two index rows are updated. `check_source_paths.py` gives 5 missing (8 occurrences) before and after, all
  pre-existing.

Filed: [[problems/datatable-actions-column-on-mobile]], [[problems/datatable-column-resize-noop]].

## [2026-10-15] update | SQLite savepoint without an outer write transaction commits on release
W-B20 built (workstream W): `begin_writes()` in `backend/app/db/session.py` opens the transaction before the per-broker
savepoints of `BrokerService.delete_bulk`, so a broker that fails half-way leaves nothing behind and account deletion
stays all or nothing. Red first (BR-U-081…085); a mutation without the helper turns BR-U-082 and the account's
all-or-nothing tests red. The page gains the fix, a testing lesson (only a *released* outermost savepoint commits
early) and its source files.
Updated: [[problems/sqlite-savepoint-without-write-begins-as-transaction]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-16] update | A TRANSFER left without its other half becomes a plain ADJUSTMENT (V-3)
Decision 47 built (workstream W, on J's CP-16 FIFO handover at cost): the giving leg of a TRANSFER whose receiver is
deleted becomes an ADJUSTMENT-out at the Auto cost of its own broker (`_handover_cost`), without a cost it only loses its
link; the split of a TRANSFER pair prices its giving leg in the WAC stage (refused with `WAC_FX_UNAVAILABLE` on a missing
conversion), a promote back to TRANSFER drops the giving side's cost; the lone legs already in databases are converted by
the `lone-transfer-legs` startup step after the post-migration fixes (the sync fix cannot compute the async WAC), with a
dry run in the offline CLI. Entry after J-17 (price marks from adjustments). The status's stale «not in the code yet» and
«waits for point 46/47» lines are gone.
Updated: [[decisions/orphan-transfer-becomes-an-adjustment]].

## [2026-10-16] update | Days that only move an exchange rate, or a price's source or age, were skipped
J CP-6 (release 1.3, decision 28) closes B11's securities half: a frame day is dirty when a rate the day reads to value
it changes (securities, the unrealized split, cash in transit), on every market-quote day, and on the first day a
carried price turns stale; `native_cash.change_days` is the one home for «the day a rate changes». The page moves to
resolved, with the test lesson (buy in the report currency, or the cash leg hides the defect) and its source files.
Updated: [[problems/dirty-days-ignore-fx-only-moves]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-16] update | Three pages that still said B11's securities half was open
After J CP-6 the docs-writer found three statements left behind: the pre-frame/frame concept («still skipped»), the
native-cash revaluation decision («stays open») and the native-cash entity (no `change_days` in its API). Brought in
line with the resolved problem page.
Updated: [[concepts/pre-frame-frame-separation]], [[decisions/native-cash-daily-revaluation]], [[entities/native-cash]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-16] file | Tailwind 4 sorts same-property utilities by name
Workstream T, lot I1 of the colour programme (the selects, night of 15–16/10): moving `SimpleSelect`'s trigger onto the
roles kept the idle border always on and added the open one conditionally, and the open border vanished. Tailwind 4
emits two base utilities of one property sorted by name, so `border-lf-input` came after `border-lf-focus`; the legacy
pair had worked by luck. The page covers the cause (variant order and specificity in 4.1.18, the `:where()` dark
variant), the rule (one property, one ternary; a state that must beat a caller is a variant), the same logic across
class props and `<style>` (`ModalBase`, `AssetCurrencyChangeModal`), and the prevention. The rule is also rule 8 of the
`theme-roles` skill.
Filed: [[problems/tailwind4-same-property-utilities-sorted-by-name]].
Graph: not updated; no graphify run while the machine is reserved for the gallery (coordinator, 16/10).

## [2026-10-16] update | F-088 becomes the one Rolling Return (decision 29)
J CP-10a removed the observation-based `RISK_ROLLING_RETURN` and made the calendar plugin visible in the Signals panel;
the page said the old signal «stays, unchanged». Now it records the removal, the parity proof, the store's version-3
migration of saved overlays, the plugin-owned `signals.riskRollingReturn.*` keys and the `price_return` home.
Updated: [[features/F-088]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-16] file | An ADJUSTMENT is never a price; no price at all → valued at cost (J-17)
J-17 recorded the developer's decision P2 (option A, SELL stays a price source), the valued-at-cost rule and two review
pitfalls: the grace counted from BUY/SELL dates never applied, and a completeness check on unpriced transfers left a
permanent capital artifact. Two pages that stated the old rule got a dated note.
Filed: [[decisions/adjustment-is-never-a-price]]. Updated: [[entities/portfolio-engine]],
[[problems/stale-price-banner-never-emitted]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-16] update | J-24: an outgoing priced ADJUSTMENT leaves at the value it hands over
The Dashboard now follows the developer's rule P21 for outgoing adjustments with a cost: the units leave the capital at
quantity × cost basis converted at the adjustment's date, and the difference from the average cost removed is realized,
as the lots do since CP-7a. Two pages that stated the historical-cost rule got a dated note.
Updated: [[entities/portfolio-engine]], [[concepts/inline-wac-computation]].
Graph: not updated; graphify is not available in this worktree.
## [2026-10-16] file | Domain: EMAIL — optional SMTP email of release 1.3 (workstream E, F04)
Workstream E's lot E6 asked for the domain page of the optional email. Filed from plan 08
(`Release_2/Phase_1/08_email/plan-phase01Email.prompt.md`, committed at `b22747e52`, read with the uncommitted
E6.0–E6.2 notes), the backlog section «E · Email (fase 01)», developer decisions 44 and 45, `admin/email.en.md`,
`developer/backend/email.md` and the code at `b22747e52`. The page covers what the domain sends and why, the
architecture, decisions D-E1…D-E14 with 44 and 45, the security decisions of E3s, E5b and E4b, P1 and the E4c rule,
the known limits (per process, behind a proxy, no queue, E-7, E-8, F19), 16 problems solved, mostly from the plan's
«Fuori pista» notes, and what comes next (A7a, E4c, E6, the backlog). No email feature code exists: `features: []`.
Decisions and problems stay inside the page, as the coordinator asked. `build_admin_setup()` has no caller yet:
pending A7a. `check_source_paths.py`: 5 missing (8 occurrences) before and after, all pre-existing; the page cites
50 paths, all present.
Filed: [[domains/email]].
Graph not rebuilt: not available in the worktree.

## [2026-10-16] update | CP-7b: the lots follow the Dashboard's at-cost rule day by day
The lots now value an open LONG lot at cost on every day with no observation on or before it, as the Dashboard does,
and the lots warning names exactly those days, which closes J-28. A lot opened by an ADJUSTMENT takes the home's mark on
its opening day as its reference, trades included, converted at that day's rate.
Updated: [[decisions/adjustment-is-never-a-price]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-16] update | `toISOString().slice(0,10)` is not today — a comparison is one site (Z-3)
Workstream Z's lot A (`a43502298`) fixed the asset pages' `isHeadToday`, which compared the store's `dateEnd` (the
user's calendar since the audit's commit `2e104b919`, 2026-08-30) with the UTC date. Added to the page: the history
checked in git (both sides UTC until that commit, which fixed only the store), the two faces of the `>=` (west in the
evening, a range ending today looks past, since 2026-08-30; east after midnight, a range that ended yesterday polls
and writes, older), the rule that a date comparison moves as one site, the FX conversion date left UTC on purpose (a
backward-filled lookup), the guard that freezes the time zone as well as the clock, and the six product lines that
still carry the idiom, not re-audited. `check_source_paths.py`: 5 missing (8 occurrences) before and after, all
pre-existing; the five new rows exist.
Updated: [[problems/utc-today-vs-user-calendar]].
## [2026-10-16] update | CP-9a: the risk service split by theme, T-R1 risk half closed
The risk service is split into `risk/{plan,scope,replay,results,data_quality}.py`, `RiskService` keeping the
orchestration; the risk side reads the FX routes through the home's `load_configured_fx_pair_sets`. Source-file rows
that sent moved behaviour to `risk/service.py` now point to its new module.
Updated: [[decisions/financial-math-one-home]], [[entities/portfolio-service]], [[features/F-110]],
[[problems/asset-set-scope-has-no-primary-series]], [[problems/stale-price-banner-never-emitted]],
[[problems/fx-backward-fill-unbounded-stale-rates]], [[decisions/asset-global-page-shows-no-money]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-17] update | CP-10b: the signals runtime moves into services/signals/
The signals runtime (service, runtime, annotations, series), the plugin contract and the risk adapters moved into
`services/signals/`, which ends the risk-signals import cycle. Source-file rows follow the new paths; a dated note on
the plugin-folder decision says the family root no longer keeps a contract.
Updated: [[decisions/plugin-folders-and-split-i18n]], [[decisions/ai-export-technical-series-and-density-contract]],
[[decisions/drawdown-full-history-warmup]], [[decisions/risk-library-versus-own-maths]],
[[decisions/signal-backend-plugin-architecture]], [[domains/signals]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-17] update | CP-10c: the signal service is cut by theme
`signals/service.py` keeps only `SignalService`, the façade. The batch plan moves to `signals/planning.py`, its
execution to `signals/execution.py` and the output checks to `signals/validation.py`; the annotation helpers join
`signals/annotations.py`. No behaviour change. Source-file rows point at the module that now holds the behaviour.
Updated: [[domains/signals]], [[decisions/signal-backend-plugin-architecture]], [[decisions/drawdown-full-history-warmup]].
## [2026-10-17] update | Domain: EMAIL — E-14: the limiter evicts the key with the fewest hits
Workstream E's lot E-14 (release 1.3), from E's after-the-fact review of decision N70, approved by the coordinator for
the cloud. `SlidingWindowLimiter` now evicts the key with the fewest hits still in the window, the least recently used
among them, with exact expiry (a heap of each key's oldest hit) and no search; `eviction_scan` is gone. The lesson
filed on the page: any least-recently-used family, N70's «spare the full keys» included, lets an attacker who stops one
failure short of a lock reset the count with a spray of `max_keys` fresh keys (about 1,100 requests per guess,
measured); only «fewest hits go» makes every other key carry as many hits (about 10,000 per guess), and only with
exact expiry, or keys at a stale high count would shield the spray. The first design E proposed (an index of the keys
not full) protected locked keys only: corrected before any code. Sources: plan 08 «E-14», `rate_window.py`.
Updated: [[domains/email]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-17] update | Domain: EMAIL — E-13: the per-address limits skip an untrusted local proxy
Workstream E's lot E-13 (release 1.3), approved by the coordinator after H-36 and A8a+N70. The three per-address
limits of E (forgot password, «send the link again», the registration emails) take workstream H's
`rate_limit_address(request)` instead of `client_address(request)`: `None`, which each of them already read as «no
count», behind a reverse proxy LibreFolio does not trust on a local address (the usual Docker setup), where one count
would let 10 requests from anyone block the feature for everyone. The «Behind a proxy» limitation is rewritten: the
local case skips, the public case (a CDN) still shares one count, `FORWARDED_ALLOW_IPS` takes networks; the old
example «Fly's, without the variable» is dropped, since Fly's proxy may reach the app from a private address.
Sources: plan 08 «E-13», H's `client_address.py`, `security.md` «The Client's Address».
Updated: [[domains/email]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-17] update | Domain: EMAIL — E-9 done as night decision N62 (aliases folded, no stranger's text)
Workstream E's lot E-9 (release 1.3), done the night of 17/10 as the coordinator's night decision N62, to be reviewed
by the developer. Checked in the code first: the three per-mailbox limits count on `delivery.mailbox_budget_key()`
(`+tag` and Gmail's dots folded, never stored, logged or shown); reset, verification and change notice greet
anonymously, the notice shows nothing of the new address, `masked_address()` is gone, admin setup and test keep the
username. The page gains the N62 bullet with its why (the spam relay that would harm the cloud's Brevo key and
`mail.librefolio.eu`); the notice bullet, the limits paragraph, the E4c sentence on the four limiter keys, the Aliases
limit (resolved; E-12, catch-all and Fastmail, left), the developer decisions (the drained instance budget, N62), the
backlog line and the `delivery.py` row follow. Sources: plan 08 «E-9.0» and «E-9.1», backlog E-9 and E-12; R13-SEC…3
stay in the plan. `developer/backend/email.md` still shows the masked notice and E-9 open: the docs-writer's part.
`check_source_paths.py`: 5 missing (8 occurrences) of 4108, all pre-existing, none on this page.
Updated: [[domains/email]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-17] file | Page busy, the E2E budget, and a direct Playwright run in a lane
Three pages from Y's night of 16→17/10 (Y11 closing lots, Y-21, Y-22). The concept: the `pageBusy` contract of
decision 48 / P3: tokens on the trigger and never in a load function, `join` (N55), the post-sync rule, N64, the
panels' own tokens, the button contract and the hold/record/control E2E pattern; nothing in the wiki described it.
Two problems: waits chained past the 30 s test budget (a block budget, real poll deadlines, the tooltip retry's
per-attempt rest); and a direct Playwright run in a coordinated lane (`LF_SETUP_DONE=1`, the lane guard, never
edit a script bash is running). `check_source_paths.py`: 7 missing (12 occurrences) of 4127, all pre-existing,
none on these pages.
Filed: [[concepts/page-busy-refresh-button]], [[problems/e2e-chained-waits-outlast-the-test-budget]],
[[problems/direct-playwright-run-in-a-test-lane]].
## [2026-10-17] file | Workstream H: the platform's night discoveries (H-24r, H-26, H-28/29, H-32, H-33)
Filed at the coordinator's request, after lots H-24 … H-33 of release 1.3 entered `dev_release2` the night of 17/10.
Each page carries its «why», checked in the code at `5bba93280`:
- the frontend rebuilt for files it never bundles, and a folder's time cannot tell a `.DS_Store` from a removed file,
  so the last successful build records the listing of the Tool codegen inputs;
- no route serves a hidden file of the build or of the site;
- the test runner refuses names an action cannot apply, before any side effect;
- request floats refuse infinity and NaN, field by field, with a guard over every route;
- a response that breaks its model no longer leaves its content in the log.
The concept page collects five FastAPI 0.141 behaviours measured in process: included routers hidden from
`app.routes`, `scope["route"]` without the include prefix, infinity serialised as `null`, the stock 422 that echoes the
input and fails with a 500 on a non-finite value, and no handler for `ResponseValidationError`. Sources: plan
`Phase_1/01_platform` §14, with the lots, measurements and real checks; backlog section H (H-24 … H-34).
`check_source_paths.py`: 7 missing (12 occurrences) of 4149, all pre-existing, none on these pages.
Filed: [[problems/frontend-build-looked-stale-for-files-it-never-bundles]], [[problems/static-site-served-hidden-build-files]],
[[decisions/test-runner-refuses-test-names-it-cannot-apply]], [[decisions/request-floats-refuse-inf-and-nan]],
[[problems/response-validation-error-wrote-the-response-to-the-log]], [[concepts/fastapi-0141-routing-and-validation-gotchas]].
## [2026-10-17] file | Vite HMR: dispose() runs only on the module an update is accepted through
Workstream Z, Z-22 (release 1.3). H's review of Z-20 proposed `import.meta.hot?.dispose(stop)` for the listener that
`instanceBlock.svelte.ts` adds at every hot update. Measured with the repo's Vite 7.3.5 (module runner, same
`HMRClient` as the browser): `dispose` runs only on the accepted module, the `(app)` layout, so the leak stays (1→4
listeners in three edits); handing the unsubscribe over through `import.meta.hot.data` keeps one. Also filed: Vitest
4.1.11's `import.meta.hot` has no `data`, which made the first guard throw in 24 tests. Fix `d49263b0e`.
Filed: [[problems/vite-hmr-dispose-only-on-the-accepted-module]].
## [2026-10-17] update | CP-14a: day count and simple interest in the home, one accrual walk, P-10
U10 (D-8): the day count conventions and simple interest moved, unchanged, from the Scheduled Investment provider into
`financial_math/interest.py`. The provider's two duplicated day walks are one (`_accrual_days`), pinned by a golden
test. P-10 (decision 27): the event store refuses to change a SPLIT's type while a linked incoming adjustment has no
cost, asking `splits.py`.
Updated: [[decisions/financial-math-one-home]], [[decisions/scheduled-investment-redesign]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-17] file | CP-14b: ACT/ACT ISDA, the maturity settlement after the final coupon, the measure tool's floor
ACT/ACT counted one day short per year end crossed; the Scheduled Investment's maturity settlement counted the final
coupon twice (J-39, the part without late interest); the chart measure tool annualised from one day and showed 0 % on a
zero start. All three fixed red first, with the changed values declared before the code; two reds had failed on a
mistyped literal, not on the behaviour, which the page on the settlement keeps as a lesson.
Filed: [[problems/act-act-lost-a-day-per-year-end]], [[problems/maturity-settlement-counted-the-final-coupon-twice]].
Updated: [[features/F-045]].
Graph: not updated; graphify is not available in this worktree.

## [2026-10-17] file | J-43 (transfer share mismatch) and R13-SEC7-1 (unbounded date ranges)
The share-mismatch warning of the portfolio classifier skipped same-day pairs and never reached the user, so a transfer
between brokers owned at different shares made P&L with no explanation: now an INFO data-quality issue. And an
unbounded date range (`end: 9999-12-30`) froze the instance through the portfolio, lots, risk and AI Export routes:
every range now ends by tomorrow and starts at the first transaction, with a test seam for the far-future suites.
Filed: [[problems/share-mismatch-warning-never-left-the-classifier]], [[problems/unbounded-date-range-froze-the-instance]].
Graph: not updated; graphify is not available in this worktree.
