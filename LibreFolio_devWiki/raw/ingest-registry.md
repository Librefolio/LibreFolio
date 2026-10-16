# Ingest Registry

> Records every source file ingested into the wiki, with its git hash at ingest time.
> Purpose: detect drift between the ingested snapshot and the current state of the source.
>
> **How to check drift for a source:**
> ```bash
> git diff {hash} HEAD -- {source-path}
> ```
> A non-empty diff means the source has changed since it was ingested.
> Significant changes → consider re-ingesting the source.
>
> **History rewrite (2026-09-04).** Hashes recorded before that day pointed to commits the rewrite replaced. On
> 2026-10-12 (C-64) every one of them was mapped to today's commit through `git filter-repo`'s commit map, so
> the drift check above works again; `log.md` keeps the old hashes as written.
>
> **Two hash kinds.** A bare hash is a **commit** hash and the command above works
> directly. A hash marked `(blob)` is a **content** hash of a file that is in the
> working tree but not yet committed — drift is checked by recomputing it:
> ```bash
> git hash-object {source-path}     # differs from the recorded blob → the source changed
> ```
> Once those files are committed, the blob hashes can be replaced with the commit
> hash and the `git diff` form applies again.
>
> For untracked files (external articles, PDFs in raw/): hash = `untracked`, no drift check possible.

## 2026-10-09 — lint: most recorded hashes are no longer in the repository, and many sources moved

**Unreachable hashes.** Of the 181 rows below dated up to 2026-08-31, **158 carry a commit hash that does not exist in
this repository's history** (`git cat-file -t {hash}` fails; only 2 commit hashes resolve). The history was rewritten
after those ingests, so `git diff {hash} HEAD -- {path}` cannot measure their drift. Until a deliberate re-baseline,
treat those rows as *date + path* records: to judge drift, read the source at HEAD against the wiki page, or compare
with `git log --follow -- {current path}` from the ingest date. The 14 `(blob)` rows still work: their content hashes
match the files today (`git hash-object`), although the files moved.

**Moved sources.** 64 rows name a path that moved since ingest, 7 name Plan D files that were renamed when archived,
and 2 carry a batch label instead of a path. Content is unchanged where it can be checked (the `(blob)` rows);
elsewhere it cannot (see above). Map:

| Path at ingest | Path at `586a4f0ea` |
|---|---|
| `Release_2/Phase_0/01_signalMigration/…`, `06_betaTestingReportAndFixing/…`, `07_coverageAndConsolidationCampaign/…` | `Release_2/phases/<same folder>/…` |
| `RoadmapV4_UI/phase-09-subplan/…` | `RoadmapV4_UI/phases/phase-09-subplan/…` |
| `RoadmapV4_UI/plan-phase07-transaction-Part{1,2,3,3_1_Closure,3_1_Closure_2}…` | `RoadmapV4_UI/phases/phase-07-subplan/Parte{1,2,3}/…` |
| `RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD…` (7 files) | `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/` (`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`, `PlanD-D1D2/…`, `PlanD-D1D2/Bugfix/plan-bugfix{1..4}_….prompt.md`) |
| `RoadmapV4_UI/PlanD_SplitPromoteFullStack/…` | `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-R2/…` |
| `RoadmapV4_UI/plan-independent-…`, `plan-pwa-mobile-optimizations…` | `RoadmapV4_UI/phases/phase-{05,06,10}-subplan/…`, `phases/phase-07-subplan/Standalone/…` |
| `RoadmapV4_UI/wiki_audit_2026_06_18/…` | `RoadmapV4_UI/phases/phase-final-subplan/wiki_audit_2026_06_18/…` |
| `frontend/src/lib/stores/TimeSeriesStore.ts` | `frontend/src/lib/stores/core/TimeSeriesStore.ts` |

All prefixes above start with `LibreFolio_developer_journal/` except the last row. The nineteen folders archived
today had **no** rows here before this date; their rows are at the end of the file, with the archive commit.

## 2026-09-01 — the 14 session-state sources were brought into the repository

The 2026-08-31 consolidation ingest read 14 plan/history files that lived only in
`~/.copilot/session-state/8e82a6ff-.../files/` — outside the repository, outside git,
and inside a directory that is deleted when the session is. Nine `sources/` pages
derive from them, and **drift detection was structurally impossible**: there was
nothing to diff against, and the sources could vanish without the wiki noticing.

They now live in
[`LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/`](../../LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/),
with an `INDEX.md` that carries the warning these sources need most: **a plan is not
a chronicle.** Several of them describe an architecture in the future tense —
proposed module names, a proposed `actions/` package — that was then read as a record
of what shipped. That misreading is precisely what put three invented paths into the
wiki (see the 2026-09-01 lint-repair entry in `log.md`). The `INDEX.md` states it at
the top so the next reader meets it before the plans.

A 15th file, `draft-runner-changes.md`, is present in that directory but **was never
ingested** and has no registry row — it is background, not a source.

Their rows below now carry repository paths and `(blob)` content hashes.

| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/README.md` | `62e1c0dd2` | 2026-06-30 | [[sources/phase07-pland-split-promote]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-PlanD1_BackendBatchSuggest.prompt.md` | `62e1c0dd2` | 2026-06-30 | [[sources/phase07-pland-split-promote]], [[decisions/batch-only-split-promote]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-PlanD2_FrontendSplitPromoteUI.prompt.md` | `62e1c0dd2` | 2026-06-30 | [[sources/phase07-pland-split-promote]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-CentralizePayloadCommit.prompt.md` | `62e1c0dd2` | 2026-06-30 | [[sources/phase07-pland-split-promote]], [[concepts/centralized-tx-payload]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-v5-ImportWizard.prompt.md` | `32fbec5bc` | 2026-06-30 | [[sources/phase07-part5-import-wizard-v5]], [[entities/import-wizard-modal]], [[decisions/import-wizard-v5-paradigm]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-BRIMImportBridge.prompt.md` | `32fbec5bc` | 2026-06-30 | [[sources/phase07-part5-import-wizard-v5]] (superseded v4) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-M1-ParseAndSee.prompt.md` | `32fbec5bc` | 2026-06-30 | [[sources/phase07-part5-import-wizard-v5]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/brim-plugin-sign-audit-2026-06-08.md` | `32fbec5bc` | 2026-06-30 | [[sources/phase07-part5-import-wizard-v5]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Standalone/plan-pwa-mobile-optimizations.prompt.md` | `c96134181` | 2026-06-30 | [[sources/phase07-standalone-pwa]], [[features/F-098]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/plan-phase08Step1-2-backend.prompt.md` | `32fbec5bc` | 2026-06-30 | [[sources/phase08-scheduler-backend]], [[entities/market-data-scheduler]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/plan-test-checkpoint-phase07-08.md` | `32fbec5bc` | 2026-06-30 | [[sources/phase08-scheduler-backend]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/README.md` | `32fbec5bc` | 2026-06-30 | [[sources/phase08-scheduler-backend]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` | `39106380` | 2026-06-30 | [[sources/phase09-portfolio-engine-dashboard]], [[entities/portfolio-engine]], [[entities/portfolio-service]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` | `39106380` | 2026-06-30 | [[sources/phase09-portfolio-engine-dashboard]], [[concepts/3-pool-cash-model]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/mwrr_analysis_report.md` | `39106380` | 2026-06-30 | [[sources/phase09-portfolio-engine-dashboard]], [[decisions/mwrr-boundary-fix]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/pnl_breakdown_analysis.md` | `39106380` | 2026-06-30 | [[sources/phase09-portfolio-engine-dashboard]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_ui_dashboard.md` | `39106380` | 2026-06-30 | [[sources/phase09-portfolio-engine-dashboard]], [[concepts/portfolio-report-unified]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/wiki_audit_2026_06_18/audit_transactions.md` | `e3c5c9608` | 2026-06-30 | [[sources/wiki-audit-2026-06-18]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/wiki_audit_2026_06_18/audit_backend_infra.md` | `e3c5c9608` | 2026-06-30 | [[sources/wiki-audit-2026-06-18]], [[entities/test-runner]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/wiki_audit_2026_06_18/audit_assets_brokers_brim.md` | `e3c5c9608` | 2026-06-30 | [[sources/wiki-audit-2026-06-18]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-final-subplan/bug_vari_report20260625.md` | `7bae73b74` | 2026-06-30 | [[sources/phase-final-bugs-2026-06-25]], [[problems/broker-icon-race-condition]], [[problems/import-wizard-identifier-prompt]], [[problems/bulk-modal-sticky-z-index]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` | `31cc36da5` | 2026-07-01 | [[sources/phase09-portfolio-engine-3pool-refactor]], [[entities/portfolio-engine]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` | `31cc36da5` | 2026-07-01 | [[sources/phase09-portfolio-engine-3pool-refactor]], [[concepts/3-pool-cash-model]], [[concepts/inline-wac-computation]], [[concepts/pre-frame-frame-separation]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCH_ANALYSIS_PORTFOLIO_ENGINE.md` | `31cc36da5` | 2026-07-01 | [[sources/phase09-portfolio-engine-3pool-refactor]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/implementation_status_report.md` | `31cc36da5` | 2026-07-01 | [[sources/phase09-portfolio-engine-3pool-refactor]], [[entities/portfolio-engine]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/mwrr_analysis_report.md` | `31cc36da5` | 2026-07-01 | [[sources/phase09-portfolio-engine-3pool-refactor]], [[decisions/mwrr-boundary-fix]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/pnl_breakdown_analysis.md` | `31cc36da5` | 2026-07-01 | [[sources/phase09-portfolio-engine-3pool-refactor]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/report_asset_level_contribution_gap_analysis.md` | `31cc36da5` | 2026-07-01 | [[sources/phase09-portfolio-engine-3pool-refactor]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md` | `4e5e500c0` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-BugfixRound1.prompt.md` | `4e5e500c0` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-BugfixRound2.prompt.md` | `4e5e500c0` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrency.prompt.md` | `4e5e500c0` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrencyFix.prompt.md` | `4e5e500c0` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacFxEnrich.prompt.md` | `4e5e500c0` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/knowledge_base/00_project_overview.md` | `8d21ced5a` | 2026-04-24 | no source page of its own; the pages that draw on it: [[concepts/backend-only-calculations]], [[concepts/dual-view-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/00-index.md` | `8d21ced5a` | 2026-04-24 | [[sources/roadmap-v4-index]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part1.md` | `8d21ced5a` | 2026-04-24 | [[sources/phase07-transactions]] |
| `LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` | `dd949cb6a` | 2026-04-24 | [[concepts/async-io-rule]], [[concepts/single-migration-strategy]], [[concepts/svelte5-runes]], [[problems/flag-emoji-windows]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/changelog_2026-04-10_live-ticker-and-provider-lifecycle.md` | `e931448f6` | 2026-04-24 | [[decisions/provider-shutdown-generic]], [[problems/liveticker-header-crash]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-subplan/plan-fxSyncApiRedesign.prompt.md` | `f123d4d` | 2026-04-24 | [[decisions/fx-sync-pair-based]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-subplan/analysis-brim-multiuser.md` | `84516e3` | 2026-04-24 | [[decisions/brim-broker-scoped]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-subplan/plan-data-separation.md` | `8d21ced5a` | 2026-04-24 | [[decisions/prod-test-data-separation]] |
| `LibreFolio_developer_journal/RoadMapV1/01-Riassunto_generale.md` | `8d21ced5a` | 2026-04-24 | [[sources/roadmap-v1-summary]] |
| `backend/app/db/models.py` | `8d21ced5a` | 2026-04-24 | [[entities/db-models]] |
| `backend/app/api/v1/router.py` | `fcf37d2d3` | 2026-04-24 | [[entities/api-router]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-00-setup.md` | `b4d32a217` | 2026-05-10 | [[decisions/sveltekit-over-react]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-01-foundation.md` | `b4d32a217` | 2026-05-10 | [[decisions/sveltekit-over-react]], [[decisions/zodios-api-client]], [[features/F-059]] |
| `TODO_FUTURI.md` | `af33ef791` | 2026-04-24 | [[sources/todos]], [[features/F-075]] through [[features/F-096]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-03-layout-settings.md` | `b4d32a217` | 2026-05-10 | [[features/F-001]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-brokers.md` | `b4d32a217` | 2026-05-10 | [[features/F-009]], [[features/F-012]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-fx.md` | `b4d32a217` | 2026-05-10 | [[features/F-019]], [[features/F-020]], [[features/F-037]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-assets.md` | `b4d32a217` | 2026-05-10 | [[features/F-034]], [[features/F-037]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12-AssetEventAndScheduleRedesign.prompt.md` | `b4d32a217` | 2026-05-10 | [[decisions/scheduled-investment-redesign]], [[features/F-034]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12Finale-MaturationEngine.prompt.md` | `b4d32a217` | 2026-05-10 | [[decisions/scheduled-investment-redesign]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/PlanB/plan-partBDataEditorUnificato.prompt.md` | `b4d32a217` | 2026-05-10 | [[decisions/data-editor-unification]], [[concepts/editbuffer-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-subplan/plan-fxConversionChain.prompt.md` | `b4d32a217` | 2026-05-10 | [[features/F-020]] |
| `backend/app/services/asset_source_providers/scheduled_investment.py` | `b4d32a217` | 2026-05-10 | [[decisions/scheduled-investment-redesign]], [[features/F-034]] |
| `backend/app/services/asset_source_providers/justetf.py` | `b4d32a217` | 2026-05-10 | [[problems/justetf-websocket-disconnect]] |
| `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts` | `b4d32a217` | 2026-05-10 | [[concepts/editbuffer-pattern]], [[decisions/data-editor-unification]] |
| `frontend/src/lib/stores/TimeSeriesStore.ts` | `b4d32a217` | 2026-05-10 | [[concepts/timeseries-store-pattern]] |
| `frontend/src/lib/stores/fxStoreRegistry.ts` | `b4d32a217` | 2026-05-10 | [[concepts/timeseries-store-pattern]] |
| `backend/app/db/models.py` | `b4d32a217` | 2026-05-10 | [[entities/db-models]] (updated hash; previously `8d21ced5a`) |
| `Dockerfile` | `b4d32a217` | 2026-05-10 | [[decisions/single-docker-image]] |
| `LibreFolio_developer_journal/knowledge_base/04_devpy_reference.md` | `b4d32a217` | 2026-05-10 | [[entities/devpy-cli]] |
| `TODO_Completati.md` | (live file) | 2026-05-10 | [[features/F-008]], [[features/F-014]], [[features/F-061]], [[features/F-034]], [[features/F-022]] |
| `TODO_FUTURI.md` | (live file) | 2026-05-10 | [[features/F-075]]–[[features/F-095]] |
| `LibreFolio_developer_journal/knowledge_base/03_documentation.md` | `b4d32a217` | 2026-04-24 | [[sources/kb-03-documentation]], [[features/F-069]], [[features/F-070]], [[features/F-074]], [[concepts/mkdocs-suffix-i18n]] |
| `LibreFolio_developer_journal/knowledge_base/06_testing_backend.md` | `b4d32a217` | 2026-04-24 | [[sources/kb-06-testing-backend]], [[features/F-068]], [[concepts/backend-test-isolation]] |
| `LibreFolio_developer_journal/knowledge_base/07_testing_frontend.md` | `b4d32a217` | 2026-04-24 | [[sources/kb-07-testing-frontend]], [[features/F-067]], [[features/F-074]], [[concepts/e2e-data-testid-rule]] |
| `LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md` | `b4d32a217` | 2026-04-24 | [[sources/kb-08-i18n-duplicates]], [[features/F-008]], [[decisions/i18n-key-rationalization]] |
| `LibreFolio_developer_journal/knowledge_base/01_backend.md` | `ca6e96497` | 2026-04-24 | [[sources/kb-01-backend]] |
| `LibreFolio_developer_journal/knowledge_base/02_frontend.md` | `ca6e96497` | 2026-04-24 | [[sources/kb-02-frontend]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step1/plan-phase06BugfixMigration-part2.md` | `6f10b8132` | 2026-04-24 | [[sources/phase06-bugfix-migration]], [[concepts/responsive-4mode-layout]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step1/plan-phase06BugfixMigration-part3.md` | `6f10b8132` | 2026-04-24 | [[sources/phase06-bugfix-migration]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/checklist-AssetProviders-CSSandScheduled.md` | `6f10b8132` | 2026-04-24 | [[sources/phase06-step2-providers]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/plan-phase06Step2cSyncDeleteRefactor.prompt.md` | `6f10b8132` | 2026-04-24 | [[sources/phase06-step2c-sync-refactor]], [[decisions/three-phase-pipeline]], [[problems/asset-sync-transaction-closed]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/plan-phase06Step6-i18n-dedup.prompt.md` | `6f10b8132` | 2026-04-24 | [[sources/phase06-step6-i18n-polish]] |
| Phase06 Step3 Rounds 1–11 (14 files in `Bugfix-Step3/`) | `b4d32a217` | 2026-05-24 | [[sources/phase06-step3-rounds]], [[features/F-033]], [[features/F-034]], [[problems/asset-list-500-provider-input-type]] |
| Phase06 Step4 PlanA + Plan0 (6 files in `Bugfix-Step4/PlanA/` + `Plan0/`) | `b4d32a217` | 2026-05-24 | [[sources/phase06-step4-plana]], [[features/F-033]], [[features/F-037]], [[features/F-042]], [[features/F-043]], [[decisions/signal-label-unification]] |
| Phase06 Step4 PlanC (5 files in `Bugfix-Step4/PlanC/`) | `b4d32a217` | 2026-05-24 | [[sources/phase06-step4-planc]], [[features/F-020]], [[features/F-042]], [[features/F-060]], [[features/F-061]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part2.prompt.md` | `8d21ced5a` | 2026-04-24 | [[sources/phase07-part2-brim-revision]], [[features/F-012]], [[decisions/brim-parser-only]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3.md` | `c9b269` | 2026-04-24 | [[sources/phase07-part3-api-consolidation]], [[features/F-046]], [[decisions/multi-broker-atomic-tx]], [[decisions/tx-link-uuid-semantics]], [[decisions/price-currency-hard-reject]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure.md` | `47bb2d8d0` | 2026-04-24 | [[sources/phase07-part3-closure]], [[features/F-046]], [[features/F-012]], [[features/F-051]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure_2.prompt.md` (+ Batch4d parts + BlockG) | `a3ee30948` | 2026-04-24 | [[sources/phase07-part3-closure2]], [[concepts/savewithretry-frontend-pattern]], [[features/F-049]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte1/plan-phase07-transaction-Part1.md` | `4ddf7797a` | 2026-04-25 | [[sources/phase07-transactions]] (re-anchored after archive move; status ✅ DONE) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte2/plan-phase07-transaction-Part2.prompt.md` | `4ddf7797a` | 2026-04-25 | [[sources/phase07-part2-brim-revision]] (re-anchored; status ✅ DONE) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3.md` | `4ddf7797a` | 2026-04-25 | [[sources/phase07-part3-api-consolidation]] (re-anchored; status ✅ DONE) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure.md` | `4ddf7797a` | 2026-04-25 | [[sources/phase07-part3-closure]] (re-anchored; Policy D + backup endpoints surfaced) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure_2.prompt.md` (+ Batch4dPart2 + Batch4dPart3 + BlockG) | `4ddf7797a` | 2026-04-25 | [[sources/phase07-part3-closure2]], [[problems/assets-wipe-error-attr-mismatch]], [[problems/babel-currency-symbol-echo]], [[decisions/policy-d-currency-wipe]], [[entities/backup-router]] (G-batch6 + G-batch7, 87.06% coverage, 2 prod bugs) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/plan-phase07-transaction-Part4.prompt.md` | `8bce1c2fc` | 2026-04-28 | [[sources/phase07-part4-transactions-ui]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md` | `9ce781e88` | 2026-04-28 | [[sources/phase07-part4-round1]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` | `29898623` | 2026-04-28 | [[sources/phase07-part4-round2]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md` | `f3ba9f2ba` | 2026-05-25 | [[sources/phase07-part4-round3-staging-rewrite]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md` | `f3ba9f2ba` | 2026-05-25 | [[sources/phase07-part4-round3-bugfix1]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md` | `f3ba9f2ba` | 2026-05-25 | [[sources/phase07-part4-round3-bugfix2]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md` | `f3ba9f2ba` | 2026-05-25 | [[sources/phase07-part4-round4-unified-pipeline]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` | `f3ba9f2ba` | 2026-05-25 | [[sources/phase07-part4-round5-server-type-rules]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md` | `90f7a12c4` | 2026-05-28 | [[sources/phase07-part4-round5-bugfix1-dual-form]], [[decisions/cash-transfer-split-promote]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md` | `90f7a12c4` | 2026-05-28 | [[sources/phase07-part4-round5-bugfix2-testwalk-overhaul]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md` | `90f7a12c4` | 2026-05-28 | [[sources/phase07-part4-round5-bugfix3-testwalk-fixes]], [[features/F-048]], [[features/F-047]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md` | `90f7a12c4` | 2026-05-28 | [[sources/phase07-part4-round6-context-menu-delete]], [[decisions/context-menu-all-tables]], [[features/F-047]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanA_ContextMenuBugfix.prompt.md` | `90f7a12c4` | 2026-05-28 | [[sources/phase07-part4-round6-plana-context-menu-bugfix]], [[problems/dual-form-collect-duplication]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB_DeletePickerAccess.prompt.md` | `90f7a12c4` | 2026-05-28 | [[sources/phase07-part4-round6-planb-delete-picker-access]], [[decisions/broker-access-min-paired]], [[features/F-047]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB1_BugfixRound1.prompt.md` | `90f7a12c4` | 2026-05-28 | [[sources/phase07-part4-round6-planb-delete-picker-access]] (B1 folded into Plan B source page) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB23_Appendix1_UIPolish.prompt.md` | `53c9314b1` | 2026-05-29 | [[sources/phase07-part4-round6-planb23-appendix1-ui-polish]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md` | `1589ecfe6` | 2026-05-29 | [[sources/phase07-part4-round6-planc-txstore-refactor]], [[concepts/txstore-pattern]], [[decisions/txstore-single-source-of-truth]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md` | `96d8d0a4d` | 2026-05-30 | [[sources/phase07-part4-round6-planc3-pendingop-refactor]], [[decisions/pendingop-tagged-union]], [[concepts/txstore-pattern]], [[concepts/e2e-data-testid-rule]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC2_BugfixAndPairValidation.prompt.md` | `f08a6e619` | 2026-05-30 | [[sources/phase07-part4-round6-planc2-bugfix-pair-validation]], [[decisions/pair-description-tags-validation]], [[problems/fx-multi-route-no-fallback]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md` | `ff5e7b36c` | 2026-05-30 | [[sources/phase07-part4-round6-planc2r2-regressions-mockfx]], [[decisions/auto-populate-removal]], [[decisions/formmodal-contextual-validate]], [[decisions/end-of-day-balance-check]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB23_BulkDeleteViaBulkModal.prompt.md` | `uncommitted` | 2026-05-31 | [[sources/phase07-part4-round6-planb23-bulk-delete]] (registry backfill — source page already existed from 2026-05-27 ingest) |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md` | `e3d8bda40` | 2026-05-31 | [[sources/phase07-part4-round6-pland-split-promote-master]], [[decisions/cash-transfer-split-promote]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md` | `11f5d81db` | 2026-05-31 | [[sources/phase07-part4-round6-pland1-backend-batch-suggest]], [[decisions/cash-transfer-split-promote]], [[features/F-046]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_FrontendSplitPromoteUI.prompt.md` | `5890cf9fe` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-frontend-split-promote]], [[features/F-048]], [[features/F-047]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_1_SplitPromotePolish.prompt.md` | `79841b567` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix1]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_2_PayloadSplitPreviewUX.prompt.md` | `588bf0c0c` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix2]], [[features/F-048]], [[features/F-046]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_3_UXModalPayloadSuggestE2E.prompt.md` | `49424b264` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix3]], [[features/F-048]], [[features/F-046]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_4_SplitSuggestPmcOverrideUx.prompt.md` | `25f31a1ca` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix4]], [[features/F-048]], [[features/F-046]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/plan-R2-WalktestFeedbackRound.prompt.md` | `ec0ac90a3` | 2026-06-01 | [[sources/r2-walktest-feedback-master]], [[features/F-097]], [[features/F-048]], [[decisions/cost-basis-currency-object]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-A-CostBasisWAC.prompt.md` | `ec0ac90a3` | 2026-06-01 | [[sources/r2-sp-a-cost-basis-wac]], [[features/F-097]], [[decisions/cost-basis-currency-object]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-B-BackendTests.prompt.md` | `ec0ac90a3` | 2026-06-01 | [[sources/r2-sp-b-backend-tests]], [[features/F-097]], [[features/F-068]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-C-BulkModalSuggestUX.prompt.md` | `ec0ac90a3` | 2026-06-01 | [[sources/r2-sp-c-bulkmodal-suggest-ux]], [[features/F-048]], [[features/F-097]] |
| (commits `daf95a904`, `75d72f601`, `6871dc38f`, `9ab32912c`) — PWA Support | `ec0ac90a3` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-098]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-pwa-mobile-optimizations.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-098]] |
| (commit `432d8642a`) — Port 60/40 Scheme | `ec0ac90a3` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[decisions/port-6040-scheme]] |
| (commit `9b9fcbb65`) — Borsa Italiana Provider | `ec0ac90a3` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-099]] |
| (commit `e82346802`) — FX Provider Removal Fix | `ec0ac90a3` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-019]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/plan-SP-C-BugfixRound1.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/plan-SP-C-BugfixRound2-WacPreview.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]], [[features/F-048]], [[decisions/wac-inline-validate-commit]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/plan-SP-C-FxImpliedRateSpread.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-BugfixRound3-UnifiedPartnerArch.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[concepts/paired-partner-architecture]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-ReactiveWacBulkModal.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-FixCloneLinkUuid.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[problems/clone-link-uuid-duplication]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-FixWacFeedbackLoop.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[problems/wac-feedback-loop]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-WacInlineValidateCommit.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[decisions/wac-inline-validate-commit]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-FixWacPartnerRows.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-StatelessWacPreview.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[concepts/stateless-preview-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-WacBackendCleanup.prompt.md` | `ec0ac90a3` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-BackendLogAudit.prompt.md` | `82c9224d5` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-076]], [[concepts/log-level-policy]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-CandlestickChart.prompt.md` | `aefb764ed` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-080]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-FxRangeHelper.prompt.md` | `5e12fef35` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[concepts/fx-range-helper-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-LazyImageCache.prompt.md` | `315d3e826` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-086]], [[concepts/image-preview-cache-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-RsiSignalBands.prompt.md` | `7a6bd67bb` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-039]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/batch` | `63ae8ccee` | 2026-06-17 | [[sources/phase09-dashboard-batch]] |
| `source-code-v0.9.0-batch` | `3622c2c03` | 2026-06-17 | [[sources/source-code-v0.9.0-batch]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/lowDashboard/` (Holdings/Performance refactor) | `13052a006` | 2026-07-06 | [[concepts/holdings-performance-panel]], [[entities/portfolio-service]], [[features/F-054]], [[features/F-055]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/mwrr-numerical-stability-analysis.md` | `39106380` | 2026-07-07 | [[decisions/mwrr-solver-newton-cap]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/` (Milestone_1/ + Milestone_2/ + root docs, `git mv` archive — staged, uncommitted at ingest) | `820d945a6` | 2026-07-07 | [[sources/phase09-m1-m2-archive-2026-07]], [[decisions/portfolio-summary-direct-wiring]], [[problems/test-transaction-implied-constructor-mismatch]], [[problems/datatable-column-resize-noop]] |
| `.../phase-09-subplan/Milestone_3/` (`README.md` + 6 chart-resolution impl plans, `git mv` archive — staged, uncommitted at ingest) | `8c25c548b` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]], [[concepts/chart-resolution-semantic-zoom]], [[entities/time-series-aggregation]] |
| `.../phase-09-subplan/implementation_plan.md` (shared M1/M2/M3 reference, `git mv` archive) | `2841640d0` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]] |
| `.../phase-09-subplan/plan_ui_broker_holdings.md` (root, superseded original) | `81fc556d7` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]] |
| `.../phase-09-subplan/{plan_ui_broker_overview.md, plan_ui_broker_transactions.md}` (root, superseded originals) | `63ae8ccee` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]] |
| `.../Milestone_3/GUIDA-TOOLBAR-RESPONSIVE-v2.md` | `16f24e410` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]] |
| `.../Milestone_3/{plan_ui_broker_overview.md, plan_ui_broker_transactions.md, chart_resolution/study_chart_dynamic_resolution.md}` | `0d29808d4` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]], [[decisions/broker-list-visibility-non-members]], [[decisions/broker-card-aggregation-no-n-plus-one]], [[problems/portfolio-asset-history-regression-restored]], [[concepts/chart-resolution-semantic-zoom]] |
| `.../Milestone_3/{plan_ui_broker_holdings.md, impl_plan_broker_holdings.md}` | `4cdd1d8fb` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]], [[concepts/fifo-lot-tracking]] |
| `.../Milestone_3/impl_plan_broker_overview.md` | `c3cf93f56` | 2026-07-15 | [[sources/phase09-m3-broker-redesign-2026-07]], [[decisions/broker-list-visibility-non-members]], [[decisions/broker-card-aggregation-no-n-plus-one]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/post-implementation-review-v5.md` | `29769258e` | 2026-07-22 | [[sources/fifo-v4-fee-tax-integration]], [[problems/datatable-net-columns-hidden-override-model]], [[problems/transaction-update-bypassed-sign-validation]], [[decisions/fifo-v4-gross-net-status-model]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-recap-v5.md` | `29769258e` | 2026-07-22 | [[sources/fifo-v4-fee-tax-integration]], [[entities/fifo-lot-engine]], [[entities/lots-analysis-service]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/review-checklist-v5.md` | `29769258e` | 2026-07-22 | [[sources/fifo-v4-fee-tax-integration]], [[decisions/fifo-v4-gross-net-status-model]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-plan-v5.md` | `29769258e` | 2026-07-22 | [[sources/fifo-v4-fee-tax-integration]], [[entities/fifo-lot-engine]], [[entities/lots-analysis-service]], [[decisions/fifo-v4-income-eligibility-d1]], [[decisions/fifo-v4-cost-allocation-ladder]], [[decisions/fifo-v4-engine-architecture]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` | `8ca7b72da` | 2026-07-21 | [[sources/fifo-v4-fee-tax-integration]], [[decisions/fifo-v4-income-eligibility-d1]], [[decisions/fifo-v4-cost-allocation-ladder]], [[decisions/fifo-v4-engine-architecture]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/feasibility-analysis-v4.1.md` | `8ca7b72da` | 2026-07-21 | [[sources/fifo-v4-fee-tax-integration]], [[decisions/fifo-v4-engine-architecture]], [[decisions/fifo-v4-validation-and-scope]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/{feasibility-analysis.md, feasibility-analysis-v2.md, feasibility-analysis-v3.md, feasibility-analysis-v4.md, feasibility-analysis-v4-review.md}` (superseded drafts) | `8ca7b72da` | 2026-07-21 | [[sources/fifo-v4-fee-tax-integration]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/{high-level-analysis.md, high-level-analysis-v2.md, hig-level-analysis-v3.md}` (superseded drafts) | `8ca7b72da` | 2026-07-21 | [[sources/fifo-v4-fee-tax-integration]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/{REPORT-fifo-lots-transfer-mismatch.md, fifo-engine-current-state.md, fifo-segment-model-analysis.md, portfolio-engine-cache-analysis.md}` (parent background, partly superseded — see source page) | `9fe20ce1d` | 2026-07-16 | [[sources/fifo-v4-fee-tax-integration]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` | `untracked` | 2026-07-27 | [[sources/phase00-ai-export-backend-snapshot]], [[decisions/ai-export-contextual-ui-memory]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md` | `untracked` | 2026-07-27 | [[sources/phase00-ai-export-backend-snapshot]], [[decisions/ai-export-versioned-snapshot-boundary]], [[decisions/ai-export-contextual-ui-memory]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/contract-phase00AiExportTaskProfiles.md` | `untracked` | 2026-07-26 | [[sources/phase00-ai-export-backend-snapshot]], [[decisions/ai-export-versioned-snapshot-boundary]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportMigrationEquivalence.md` | `untracked` | 2026-07-26 | [[sources/phase00-ai-export-backend-snapshot]], [[decisions/ai-export-versioned-snapshot-boundary]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/difetti-aperti-corsia-impostazioni.md` | `3db264af5fb0` (blob) | 2026-08-31 | [[sources/settings-lane-and-sixteen-defects]], [[decisions/settings-write-path-contract]], [[decisions/broker-last-owner-guard]], [[concepts/characterisation-test-latch]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-corsia-impostazioni-COMPLETO.md` | `b471cf160c66` (blob) | 2026-08-31 | [[sources/settings-lane-and-sixteen-defects]], [[decisions/settings-write-path-contract]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-undici-difetti-COMPLETO.md` | `8ed90ecabce3` (blob) | 2026-08-31 | [[sources/settings-lane-and-sixteen-defects]], [[concepts/characterisation-test-latch]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-scheduler-e-fx-COMPLETO.md` | `fcfdd3fad935` (blob) | 2026-08-31 | [[sources/settings-lane-and-sixteen-defects]], [[decisions/scheduler-converts-at-decision]], [[concepts/absence-sentinel-vs-nullable-type]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-p8-runner-migration.md` | `526b70d13af8` (blob) | 2026-08-31 | [[sources/p8-runner-parallel-architecture]], [[concepts/test-isolation-classes]], [[concepts/derived-test-inventory]], [[concepts/run-cache-and-campaign-semantics]], [[problems/registered-but-unreachable-test-actions]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-p7-js-coverage.md` | `9404cdddee06` (blob) | 2026-08-31 | [[sources/p7-js-coverage-instrumentation]], [[problems/svelte-template-branches-not-instrumented]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-p9-test-semantics-COMPLETO.md` | `2d60850698a9` (blob) | 2026-08-31 | [[sources/p9-test-semantics]], [[problems/namedcache-clear-leaves-admission-filter]], [[concepts/load-only-red-is-a-product-defect]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-tappe-7-11-parallelismo-COMPLETO.md` | `5b2e4dfcc4cf` (blob) | 2026-08-31 | [[sources/frontend-parallelism-tappe-7-11]], [[concepts/playwright-run-consolidation]], [[concepts/transaction-hygiene-fixture]], [[problems/env-var-injection-point-duplicated]], [[problems/commit-reported-success-on-rolled-back-batch]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/tappa9-desleep.md` | `3326f0f6b995` (blob) | 2026-08-31 | [[sources/frontend-parallelism-tappe-7-11]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-coverage-campaign.md` | `ca787f450faa` (blob) | 2026-08-31 | [[sources/coverage-campaign-2026-08]], [[concepts/coverage-rate-vs-volume]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-coverage-campaign-2.md` | `a0ac043ccd7a` (blob) | 2026-08-31 | [[sources/coverage-campaign-2026-08]], [[problems/coverage-percent-mixed-lines-and-branches]], [[problems/e2e-python-coverage-lost-above-two-workers]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-fase012.md` | `dc981afd1248` (blob) | 2026-08-31 | [[sources/coverage-fase012-and-branch-lanes]], [[problems/utc-today-vs-user-calendar]], [[concepts/coverage-rate-vs-volume]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-corsie-sync-e-logica.md` | `43391a417c8c` (blob) | 2026-08-31 | [[sources/coverage-fase012-and-branch-lanes]], [[problems/svelte-template-branches-not-instrumented]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/coda-beta-parametrici-forkserver.md` | `1365b7df88ae` (blob) | 2026-08-31 | [[sources/coda-beta-parametric-forkserver]], [[concepts/discard-the-answer-not-the-question]], [[problems/conftest-autouse-write-breaks-pure-class]], [[problems/brim-file-store-rename-race]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/06_betaTestingReportAndFixing/00_20260805_betaTester_report.md` | `0e07359b4` | 2026-08-31 | [[sources/beta-testing-2026-08-05]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/06_betaTestingReportAndFixing/01_tassonomia_findings.md` | `0e07359b4` | 2026-08-31 | [[sources/beta-testing-2026-08-05]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/06_betaTestingReportAndFixing/02_riconciliazione_credit_agricole.md` | `0e07359b4` | 2026-08-31 | [[sources/beta-testing-2026-08-05]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/06_betaTestingReportAndFixing/INDEX.md` | `ee084861d` | 2026-08-31 | [[sources/beta-testing-2026-08-05]] |
| `.github/agents/test-author.agent.md` (§ "When a test fails", ~538-552) | `2e104b919` | 2026-08-31 | [[concepts/load-only-red-is-a-product-defect]] |
| `.github/skills/devpy-tools/testing-frontend/SKILL.md` (~313) | `2e104b919` | 2026-08-31 | [[concepts/load-only-red-is-a-product-defect]] |

## 2026-10-09 — Release 2 archive: the nineteen folders moved to `Release_2/phases/` (commit `586a4f0ea`)

Ingested from their archived paths on the day they moved (train 25). The hash is the archive commit, so
`git diff 586a4f0ea HEAD -- {path}` works for all of them. Every claim taken from these plans was checked against the
code at that commit; see the six "Release 2 archive" entries of 2026-10-09 in `log.md`.

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-contracts-runes-2026-09]], [[features/F-016]] |
| `LibreFolio_developer_journal/Release_2/phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunesBugfixRound1.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-contracts-runes-2026-09]], [[features/F-016]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/checklist-review-E.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/manifest-integrazione-E.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgent.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound1-Review.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound2-Share.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound3-SocialFeedback.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound4-SocialBoundaries.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]] |
| `LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound5-GHCRAuth.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-feedback-import-urgent-2026-09]], [[problems/asset-classification-wiped-by-partial-save]], [[features/F-104]], [[problems/ghcr-browser-cors-auth-flow]] |
| `LibreFolio_developer_journal/Release_2/phases/15_parallelRuntimeIsolation/plan-phase00ParallelRuntimeIsolation.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-parallel-runtime-isolation-2026-09]], [[concepts/runtime-lanes]] |
| `LibreFolio_developer_journal/Release_2/phases/17_assetDataOperations/plan-phase00AssetDataOperations.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-asset-data-operations-2026-09]], [[features/F-095]] |
| `LibreFolio_developer_journal/Release_2/phases/18_brimTargeted/plan-phase00BrimTargeted.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-targeted-2026-09]], [[features/F-013]] |
| `LibreFolio_developer_journal/Release_2/phases/19_yieldOnCost/README.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-yield-on-cost-2026-09]], [[decisions/yield-on-cost-definition]], [[features/F-100]] |
| `LibreFolio_developer_journal/Release_2/phases/19_yieldOnCost/plan-phase00YieldOnCost.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-yield-on-cost-2026-09]], [[decisions/yield-on-cost-definition]], [[features/F-100]] |
| `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/README.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-performance-charts-2026-09]], [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]] |
| `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceCharts.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-performance-charts-2026-09]], [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]], [[features/F-088]], [[features/F-055]] |
| `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-AssetEvents.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-performance-charts-2026-09]], [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]], [[problems/asset-event-edit-delete-reinsert]] |
| `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-EventsOnCacheHit.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-performance-charts-2026-09]], [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]], [[concepts/discard-the-answer-not-the-question]] |
| `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-TooltipI18nEscape.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-performance-charts-2026-09]], [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]] |
| `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-performance-charts-2026-09]], [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]] |
| `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-performance-charts-2026-09]], [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]] |
| `LibreFolio_developer_journal/Release_2/phases/22_assetPricingRefactor/plan-phase00AssetPricingRefactor.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-asset-pricing-refactor-2026-09]], [[entities/asset-sources-package]] |
| `LibreFolio_developer_journal/Release_2/phases/23_transactionBatchRefactor/plan-phase00TransactionBatchRefactor.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-transaction-batch-refactor-2026-09]], [[entities/transaction-batch-pipeline]] |
| `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/README.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-privacy-global-2026-09]], [[decisions/privacy-mask-at-the-formatter]], [[features/F-101]] |
| `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/analysis-phase00PrivacyGlobal.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-privacy-global-2026-09]], [[decisions/privacy-mask-at-the-formatter]], [[features/F-101]], [[concepts/premise-gate-keyed-by-content]] |
| `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-privacy-global-2026-09]], [[decisions/privacy-mask-at-the-formatter]], [[features/F-101]] |
| `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound2-PostReview.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-privacy-global-2026-09]], [[decisions/privacy-mask-at-the-formatter]], [[features/F-101]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/analysis-phase00BrimDanskeBank.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/issue26-reply.en.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBank.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]], [[problems/brim-text-exports-hardcoded-utf8]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep5PluginRedetection.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]], [[problems/brim-compatible-plugins-frozen-at-upload]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep6UploadRobustness.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep7ButtonAndR6.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep8MobileCard.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]] |
| `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep9StaleFrontend.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-danske-bank-2026-10]], [[decisions/brim-report-sets]], [[features/F-103]], [[problems/stale-frontend-after-update-html-cached]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/README.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00CoverageCombineRace.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]], [[problems/coverage-combine-race-renamed-part]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00DataQualityBannersNavCount.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00DbPathArgument.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]], [[problems/db-path-argument-ignored-by-alembic]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00DefaultDisplayCurrency.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxAddPairNavigationWait.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxDashboardSync.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]], [[problems/fx-backward-fill-unbounded-stale-rates]], [[features/F-016]] |
| `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxDashboardSyncStep2PageCache.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-fx-dashboard-sync-2026-10]], [[concepts/stale-while-revalidate-page-cache]] |
| `LibreFolio_developer_journal/Release_2/phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-i18n-audit-2026-10]], [[problems/i18n-audit-false-dead-and-false-used]], [[problems/svelte-i18n-formatter-cache-ignores-locale]], [[problems/i18n-loading-gate-remounts-app]] |
| `LibreFolio_developer_journal/Release_2/phases/30_wacUnification/plan-phase00SettingsBulkValidation.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-wac-unification-2026-10]], [[problems/global-settings-bulk-saved-unvalidated-values]] |
| `LibreFolio_developer_journal/Release_2/phases/30_wacUnification/plan-phase00WacUnification.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-wac-unification-2026-10]], [[decisions/financial-math-single-average-cost]], [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]] |
| `LibreFolio_developer_journal/Release_2/phases/31_brimDegiro/plan-phase00BrimDegiro.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-brim-degiro-2026-10]], [[features/F-013]] |
| `LibreFolio_developer_journal/Release_2/phases/33_e2eImportInfra/plan-phase00E2eImportInfra.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-e2e-import-infra-2026-10]] |
| `LibreFolio_developer_journal/Release_2/phases/34_accountAndIdReuse/plan-phase00AccountAndIdReuse.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-account-and-id-reuse-2026-10]], [[problems/account-deletion-orphaned-brokers]], [[problems/reused-ids-after-delete]] |
| `LibreFolio_developer_journal/Release_2/phases/34_accountAndIdReuse/plan-phase00AccountAndIdReuseStep2LastAdmin.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-account-and-id-reuse-2026-10]], [[problems/account-deletion-orphaned-brokers]], [[problems/reused-ids-after-delete]] |
| `LibreFolio_developer_journal/Release_2/phases/35_devCliImage/plan-phase00DevCliImage.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-dev-cli-image-2026-10]], [[problems/devpy-unusable-in-docker-image]] |
| `LibreFolio_developer_journal/Release_2/phases/36_connectionSecurity/plan-phase00ConnectionSecurity.prompt.md` | `586a4f0ea` | 2026-10-09 | [[sources/phase00-connection-security-2026-10]], [[decisions/connection-security-server-never-upgrades]], [[problems/login-account-enumeration-before-password]], [[features/F-102]] |

## 2026-10-09 — second pass: folders 25 and 39, PAC rounding (commit `083ed26dc`, train 26)

Folders 25 (workstream K) and 39 (P-1) archived to `Release_2/phases/`; the PAC rounding plan of the still-active
folder 13 read for its decision only (merge `b81b92fd1`). Paths are relative to the repository root.

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/README.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/analysis-phase00TaxonomySelect.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[decisions/asset-type-two-level-taxonomy]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelect.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[decisions/asset-type-two-level-taxonomy]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep9ImportDuplicates.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[entities/import-wizard-modal]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[problems/broker-icon-fields-request-loop]], [[concepts/entity-store-pattern]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep11BulkCreationOrder.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[features/F-048]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep12ReviewFollowups.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[problems/flag-emoji-windows]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[decisions/html-escape-at-the-source]], [[problems/stale-price-banner-never-emitted]], [[concepts/responsive-4mode-layout]], [[features/F-098]], [[features/F-099]], [[features/F-032]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep14TooltipTeardownFixture.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[problems/svelte5-teardown-reads-stale-state-timers]], [[problems/fixture-skip-hid-api-test]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep15ToolbarSweepGutter.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[concepts/responsive-4mode-layout]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep16AssetDetailUx.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[features/F-033]], [[concepts/echarts-chart-gotchas]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[problems/svelte5-teardown-reads-stale-state-timers]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep17DeviceNotes.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[decisions/asset-type-two-level-taxonomy]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep18CoverageTriage.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[problems/modal-layers-escape-and-backdrop]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[features/F-001]], [[problems/modal-layers-escape-and-backdrop]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[problems/modal-layers-escape-and-backdrop]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep21PureDefects.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[features/F-008]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep22RegisterLinkProfileDate.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[features/F-001]] |
| `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep23BulkCloneAndDiscardGuard.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-taxonomy-select-2026-10]], [[features/F-048]] |
| `LibreFolio_developer_journal/Release_2/phases/39_autoCostNoPosition/plan-phase00AutoCostNoPosition.prompt.md` | `083ed26dc` | 2026-10-09 | [[sources/phase00-auto-cost-no-position-2026-10]], [[decisions/auto-cost-basis-zero-without-position]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRoundingDirectionFix.prompt.md` | `083ed26dc` | 2026-10-09 | [[decisions/pac-rounding-against-the-plan]] — partial: folder 13 is still active; re-check before archiving |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerMathematicalCore.prompt.md` | `083ed26dc` | 2026-10-09 | [[decisions/pac-rounding-against-the-plan]] — §7.3 only (the no-arbitrage principle) |

## 2026-10-12 — step 3: lot 41 F, T-1, the AI Export version rule, M's notes (base `5d0585595`, train 47)

Step 3 of the historian, decided by the developer on 2026-10-12. Folders 41, 43 and 27 are still in `Phase_0/`. Hashes
are each file's last commit at the base. Paths are relative to the repository root.

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` | `f10fcd04a` | 2026-10-12 | [[sources/phase00-broker-pnl-flows-2026-10]], [[decisions/native-cash-daily-revaluation]], [[entities/native-cash]], [[problems/foreign-cash-never-revalued]], [[problems/dirty-days-ignore-fx-only-moves]], [[decisions/portfolio-pnl-series-contracts]] (§13) |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `25e358eb0` | 2026-10-12 | [[sources/phase00-financial-math-home-2026-10]], [[decisions/financial-math-one-home]], [[decisions/utils-leaf-functions-only]], [[problems/ai-export-reconciled-false-on-rounding-dust]], [[decisions/ai-export-version-bump-once-per-release]] — partial: §10 from «T-1» on, §1, §3, §4, §8; the folder is still active |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `e25eb913d` | 2026-10-12 | sections C, I, M and T (T-W1, T-R1, T-BU1+BU2) — read for status, not summarized |
| `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` | `83c2ba377` | 2026-10-12 | [[problems/ai-export-reconciled-false-on-rounding-dust]] (C-53), [[decisions/ai-export-version-bump-once-per-release]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `62526ede4` | 2026-10-12 | [[sources/phase00-translation-round12-2026-10]], [[problems/playwright-probes-ignore-timeout]] — partial: §9.3, §10, §11; spot checks of §5.7–§6 for the notes below |
| M's note `b12_devwiki_stamps_hide_stale_translations.md` (release-pipeline working files, outside the repository) | `untracked` | 2026-10-12 | [[problems/stamps-hide-stale-translations]], [[concepts/mkdocs-suffix-i18n]] |
| M's note `b13_devwiki_anchors_from_render.md` (idem) | `untracked` | 2026-10-12 | [[decisions/docs-anchors-from-the-render]] |
| M's note `b14_devwiki_raw_html_paths_in_translations.md` (idem) | `untracked` | 2026-10-12 | [[problems/raw-html-paths-in-translations]] |
| M's note `b15_devwiki_fr_typography_hook.md` (idem) | `untracked` | 2026-10-12 | [[decisions/fr-typography-at-build-time]] |
| The developer, via the coordinator, 2026-10-12: F-AI (b) after 1.2 with a typed code; the Scalable confirmation; the version rule; `utils/runtime/` | `untracked` | 2026-10-12 | [[decisions/native-cash-daily-revaluation]], [[decisions/ai-export-version-bump-once-per-release]], [[decisions/utils-leaf-functions-only]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `390ba7d9a` | 2026-10-12 | [[decisions/utils-leaf-functions-only]] (BU1 delivered, the `version.py` root near-miss), [[problems/docker-system-info-missing-deps]] — re-read for the BU1 record only, base `bdc078efc` (train 50) |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `f038ce39a` | 2026-10-12 | [[decisions/utils-leaf-functions-only]] (BU2 delivered), [[decisions/ai-export-version-bump-once-per-release]] (the rule written in `4388db8df`) — re-read for the BU2 record only, base `f0f3de0d9` (train 53) |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `63b3e5971` | 2026-10-12 | [[problems/playwright-probes-ignore-timeout]] (M-14 closed) — re-read for §11 (batch 20) only, base `9e31ea2ba` |
| `LibreFolio_developer_journal/Release_2/Phase_0/44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md` | `8339b0a06` | 2026-10-12 | [[problems/playwright-probes-ignore-timeout]] (M-16 closed) — read for the fix only, base `9e31ea2ba` |

## 2026-10-12 — train 56: plan 46 (V), C-55, U's decisions (planned), the connection guide (base `e7d698c4d`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `b44b28f3d` | 2026-10-12 | [[sources/phase00-data-quality-e2e-2026-10]], [[decisions/data-quality-proved-on-real-data]], [[problems/open-panels-stale-after-fx-sync]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `e7d698c4d` | 2026-10-12 | section V (V-1 … V-7), read for status |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `d5497e40a` | 2026-10-12 | [[problems/ai-export-probe-rejected-unavailable-hhi]] — C-55 sections only |
| `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` | `17c50ab50` | 2026-10-12 | [[problems/ai-export-probe-rejected-unavailable-hhi]] (C-55) |
| The coordinator's diary, decisions D-1, D-4, D-A, D-B, D-C of 2026-10-12, quoted verbatim by the coordinator; the developer's server checklist, item 28 | `untracked` | 2026-10-12 | [[decisions/plugin-folders-and-split-i18n]] — planned; re-ingest from U's plan 45 when it enters the target |
| `mkdocs_src/docs/admin/connection_checks.en.md` (commit `3eee17616`) | `3eee17616` | 2026-10-12 | [[features/F-102]], [[decisions/connection-security-server-never-upgrades]] — cross-links only |

## 2026-10-12 — step B1: plan 37 (S), the exporter's recap, M's batch 21 (base `573f7c5c7`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/plan-phase00BrimScalable.prompt.md` | `4d878e545` | 2026-10-12 | [[sources/phase00-brim-scalable-2026-10]], [[decisions/scalable-two-accounts-two-plugins]], [[decisions/import-wizard-default-plugin-check]], [[decisions/broker-icon-order-dedicated-plugin-first]], [[decisions/bulk-pairs-new-with-saved]], [[problems/merged-transfer-not-seen-as-duplicate]], [[concepts/brim-texts-translated-by-code]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/recap-phase00ScalableExporter.md` | `305b80202` | 2026-10-12 | [[sources/phase00-brim-scalable-2026-10]], [[decisions/scalable-two-accounts-two-plugins]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `0ebf86178` | 2026-10-12 | §12, batch 21 → [[decisions/scalable-two-accounts-two-plugins]]; §13, batch 22, was linked in train 56 |

## 2026-10-12 — step B2: plan 44 (I, M-16) (base `d3c6e55c5`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md` | `8339b0a06` | 2026-10-12 | [[sources/phase00-import-wizard-broker-gate-2026-10]], [[problems/import-wizard-next-before-brokers-loaded]] — full ingest; the earlier row read it only for M-16's status |
| `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` | `8339b0a06` | 2026-10-12 | re-read since `f10fcd04a`: bookkeeping only (F-C3 in train 43, F-AI decided), already in [[decisions/native-cash-daily-revaluation]]; the F-AI (b) note added there |

## 2026-10-12 — step B3: plan 40 (P) (base `5350c8e24`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/40_transferCostBasis/plan-phase00TransferCostBasis.prompt.md` | `fa109eaa7` | 2026-10-12 | [[sources/phase00-transfer-cost-basis-2026-10]], [[decisions/transfer-auto-cost-from-sending-broker]], [[problems/promote-skipped-cost-basis-check]] |

## 2026-10-12 — step B4: plan 42 (P) (base `94abcf380`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md` | `6c32f4aff` | 2026-10-12 | [[sources/phase00-promote-pair-checks-2026-10]], [[decisions/transfer-pair-same-asset-opposite-quantity]], [[decisions/promote-respects-asset-event-link]], [[problems/bulk-cost-basis-compared-by-reference]], [[problems/legacy-component-language-untracked]], [[concepts/marker-locale-for-catalogue-labels]] |

## 2026-10-12 — step B5: folder 21, the onboarding (J) (base `c7261618d`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00Onboarding.prompt.md` | `020c762e0` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[features/F-105]], [[decisions/onboarding-versioned-progress-per-flow]], [[decisions/onboarding-guide-observes-never-acts]], [[decisions/automatic-popups-wait-for-guides]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound1-UXRefinement.prompt.md` | `1982c254b` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[decisions/onboarding-guide-observes-never-acts]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound2-ModularGuides.prompt.md` | `8a8e686f0` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[decisions/onboarding-versioned-progress-per-flow]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound3-TriggeredTours.prompt.md` | `1982c254b` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound4-GeometryMilestones.prompt.md` | `1982c254b` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[problems/coachmark-measured-mid-modal-transition]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound5-StepProgressPolish.prompt.md` | `1982c254b` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[decisions/onboarding-versioned-progress-per-flow]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound6-FinalUX.prompt.md` | `1982c254b` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound7-AnchorStall.prompt.md` | `176f19707` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[problems/guide-anchor-never-resolves]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/plan-phase00OnboardingRound8-PostReview.prompt.md` | `020c762e0` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[decisions/onboarding-positions-in-browser-per-account]], [[decisions/guide-text-never-announces-another-guide]], [[problems/legacy-layout-gate-missed-runes-state]], [[problems/guide-anchor-never-resolves]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/onboarding-review-dossier.md` | `d614daed9` | 2026-10-12 | [[sources/phase00-onboarding-2026-09]], [[decisions/onboarding-existing-users-seeded-skipped]] |

## 2026-10-12 — step B6a: folder 16, the Tool platform (C), and the capacity round (D) (base `8abce8e87`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/plan-phase00ToolPlatform.prompt.md` | `425cb26d5` | 2026-10-12 | [[sources/phase00-tool-platform-2026-09]], [[features/F-106]], [[decisions/tool-calculation-without-authority]], [[decisions/tool-contract-from-pydantic-compiled-renderer]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/dossier-piattaforma-tool.md` | `09c6171bc` | 2026-10-12 | [[sources/phase00-tool-platform-2026-09]], [[decisions/tool-item-runs-in-owned-process]], [[decisions/tool-contract-from-pydantic-compiled-renderer]], [[features/F-106]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/manifest-integrazione-C.md` | `d614daed9` | 2026-10-12 | [[sources/phase00-tool-platform-2026-09]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/handoff-pac-D.md` | `9e4140376` | 2026-10-12 | [[sources/phase00-tool-platform-2026-09]] — §0 is the PAC live contract, ingested again with folder 13 in step B6b |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step1Round1-ToolPlatformCapacity.prompt.md` | `4cd2cda56` | 2026-10-12 | [[sources/phase00-tool-platform-2026-09]], [[decisions/tool-item-runs-in-owned-process]] |

## 2026-10-12 — step B6b: folder 13, the PAC allocator and the Rebalancer designs (D) (base `96fd88fec`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md` | `9a6974eff` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]], [[features/F-107]], [[features/F-108]], [[decisions/pac-scip-searches-exact-replay-certifies]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerMathematicalCore.prompt.md` | `9a6974eff` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]], [[decisions/pac-lexicographic-fixed-l2-objective]], [[decisions/pac-rounding-against-the-plan]] (refreshed from `083ed26dc`) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerPolicies.prompt.md` | `30d235b4d` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]], [[decisions/pac-lexicographic-fixed-l2-objective]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerArchitecture.prompt.md` | `30d235b4d` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]], [[decisions/pac-scip-searches-exact-replay-certifies]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerUiTarget.prompt.md` | `9e4140376` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]], [[decisions/pac-fx-one-rate-map-direct-conversions]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/review/PAC_ALLOCATOR_REVIEW_DOSSIER.md` | `9a6974eff` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]], [[decisions/pac-scip-searches-exact-replay-certifies]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/review/drive_planner.py` | `09c6171bc` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-rebalancer-decision-chronicle.md` | `30d235b4d` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]], [[decisions/pac-lexicographic-fixed-l2-objective]], [[features/F-108]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/README.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-allocator-contract.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-allocator-evidence.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-allocator-ux.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-rebalancer-end-to-end-design.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-rebalancer-operational-design.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00PacAllocator.prompt.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step2Round2-PacAllocatorUiRefinement.prompt.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step2Round3-PacAllocatorUiAcceptance.prompt.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step2Round4-PacAndRebalancerUiAcceptance.prompt.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step2Round5-PacRebalancerOperationalPlanner.prompt.md` | `30d235b4d` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step2Round6-PacRebalancerUiBlueprint.prompt.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step2Round7-PacRebalancerOperationalMigration.prompt.md` | `30d235b4d` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step3-PacRebalancingSolver.prompt.md` | `b0a410b88` | 2026-10-12 | [[sources/phase00-pac-rebalancer-design-2026-09]] — characterised (archived draft) |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/README.md` | `6c56392f1` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[features/F-107]], [[problems/datatable-actions-column-on-mobile]], [[problems/svelte5-trims-leading-space-in-tag]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRebalancerImplementation.prompt.md` | `4cd2cda56` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/tool-item-runs-in-owned-process]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step1PacRebalancerContractsCapacity.prompt.md` | `8c98a03c1` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-fx-one-rate-map-direct-conversions]], [[decisions/pac-contract-compacted-before-release]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step2PacRebalancerExactCore.prompt.md` | `8c98a03c1` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step3PacRebalancerSolverPolicies.prompt.md` | `a8ad1a500` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-scip-searches-exact-replay-certifies]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step4PacRebalancerDomainCopies.prompt.md` | `8c98a03c1` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-draft-copies-from-owned-data]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step5PacRebalancerFrontendReview.prompt.md` | `8c98a03c1` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[features/F-107]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step6PacRebalancerIntegrationTestsDocs.prompt.md` | `8c98a03c1` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRebalancerRemediation.prompt.md` | `4cd2cda56` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-p1-prototype-removed]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacP1ResidueRemoval.prompt.md` | `154182295` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-p1-prototype-removed]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacSolverBudget.prompt.md` | `4cd2cda56` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[problems/pac-solver-ran-on-default-budget]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md` | `8c98a03c1` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-scip-searches-exact-replay-certifies]], [[problems/pac-fee-floor-and-cap-misread]], [[problems/pac-tool-error-instead-of-plan]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5-C0UiDelta.prompt.md` | `30d235b4d` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-draft-copies-from-owned-data]], [[decisions/pac-contract-compacted-before-release]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacContractCompaction.prompt.md` | `7038c2224` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-contract-compacted-before-release]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacSolverRobustness.prompt.md` | `838be2b6f` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[problems/pac-scip-tolerance-misreported-proof]], [[problems/pac-tool-error-instead-of-plan]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacP1FinalRemoval.prompt.md` | `f374f1e5b` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-p1-prototype-removed]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacFxConversionFix.prompt.md` | `8a79ff34d` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[problems/pac-foreign-funding-calculation-failed]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRoundingDirectionFix.prompt.md` | `aee1e3d28` | 2026-10-12 | [[sources/phase00-pac-implementation-2026-10]], [[decisions/pac-rounding-against-the-plan]] (refreshed from `083ed26dc`: the S10 closure) |

## 2026-10-12 — steps D and C: the plugin paths after U-1, F-078 (base `145502a39`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` | `170d16333` | 2026-10-12 | [[decisions/plugin-folders-and-split-i18n]], [[features/F-059]] — partial: U-1 recorded as delivered; U-2 and U-3 when they enter |

## 2026-10-12 — step B7: folder 27 (release images, gallery) and folder 32 (the English docs for 1.2) (base `3f9de8bdb`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseImages.prompt.md` | `742e381ec` | 2026-10-12 | [[sources/phase00-release-images-and-gallery-2026-10]], [[problems/release-images-shipped-debug-frontend]], [[decisions/release-image-tags-latest-light]], [[decisions/http-gzip-in-the-app]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslatedCodeIndent.prompt.md` | `5fa0cf12a` | 2026-10-12 | [[sources/phase00-release-images-and-gallery-2026-10]], [[problems/translation-cleanup-flattened-code-indent]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseGallery.prompt.md` | `5983714f5` | 2026-10-12 | [[sources/phase00-release-images-and-gallery-2026-10]], [[decisions/gallery-is-a-release-gate-with-real-data]], [[problems/playwright-favicon-aborted-by-routes]], [[decisions/pdf-preview-viewer-only-local-assets]], [[decisions/release-image-tags-latest-light]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md` | `425cb26d5` | 2026-10-12 | [[sources/phase00-docs-english-12-2026-10]], [[decisions/user-docs-plain-dev-manual-technical]], [[problems/docs-claimed-what-the-code-did-not-do]] |

## 2026-10-12 — step B8: batches 23–24 of M, the CL of T, plan 47 of I, the backlog of 12/10 (base `35c4242f3`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `dfd8284f3` | 2026-10-12 | [[sources/phase00-translation-round12-2026-10]] (§14–§16, batches 23–24), [[problems/docs-mathjax-looked-in-the-page-folder]], [[problems/copy-buttons-without-http-fallback]], [[problems/mkdocs-material-tables-resist-styling]], [[decisions/changelog-translated-by-chapter]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `fba291f53` | 2026-10-12 | [[sources/phase00-financial-math-home-2026-10]] (CL), [[decisions/changelog-translated-by-chapter]], [[features/F-109]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md` | `ace3455e2` | 2026-10-12 | [[sources/phase00-chart-axis-day-labels-2026-10]], [[problems/line-chart-axes-lost-the-day]], [[problems/pnl-lines-kept-removed-brokers]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `bf831ef10` | 2026-10-12 | sections C (C-56, C-57), D (D-T1…D-T3), T (T-DI), M (M-19…M-21), I (47-1) — read for ids and status, not summarized |

## 2026-10-12 — trains 58 and 64: V's batch 2 and work 3 (base `d04b87c0f`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `262515898` | 2026-10-12 | [[sources/phase00-data-quality-e2e-2026-10]] (§11–§12), [[problems/e2e-writes-leaked-into-shared-state]], [[decisions/e2e-gaps-of-1-2-before-release]], [[problems/bcrypt-blocks-the-event-loop]], [[problems/open-panels-stale-after-fx-sync]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `0afac8e14` | 2026-10-12 | section V (V-1…V-20), read for status |

## 2026-10-12 — train 66: V-16 and M's batch 25 (base `b91d6d902`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `3aabf0916` | 2026-10-12 | [[problems/bcrypt-blocks-the-event-loop]] (§12.7), [[problems/e2e-writes-leaked-into-shared-state]] (A7 proofs) |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` | `81e221f4e` | 2026-10-12 | [[decisions/changelog-translated-by-heading-pieces]], [[problems/mathjax-fonts-missing-from-local-copy]], [[problems/fast-forward-blocked-by-a-dirty-file]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `81e221f4e` | 2026-10-12 | §16 updated by batch 25 — read for status |
| `CHANGELOG.md` | `b91d6d902` | 2026-10-12 | [[features/F-109]], [[decisions/changelog-translated-by-chapter]] (the ✨ line) |

## 2026-10-12 — train 67: M's batch 26 (base `0c8412745`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` | `872d42107` | 2026-10-12 | [[decisions/changelog-translated-by-heading-pieces]] (step 10), [[decisions/fr-typography-at-build-time]] (M-23) |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `872d42107` | 2026-10-12 | section M (M-23), read for status |

## 2026-10-12 — folder 02 (Risk), step R0 (base `551d8cbb4`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/README.md` | `107098edf` | 2026-10-12 | [[sources/phase00-risk-integration-2026-09]], [[features/F-110]], [[features/F-111]], [[features/F-112]], [[features/F-113]] — partial: status, parts, code map; the open items come in R1 |

## 2026-10-12 — train 68: M-18 CP1 (base `8730f949c`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `d00c06685` | 2026-10-12 | [[decisions/figures-in-the-interface-language]] — partial: M-18 rule and CP1 |

## 2026-10-12 — folder 02 (Risk), step R1 (base `86de5e903`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/README.md` | `107098edf` | 2026-10-12 | [[features/F-110]], [[features/F-111]], [[features/F-112]] — the open items (the R0 row was partial; now complete) |

## 2026-10-12 — folder 02 (Risk), step R2 (base `e3a55b85f`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/01-tesi-e-quattro-domande.md` | `245aabf97` | 2026-10-12 | [[decisions/risk-answers-four-questions]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/04-decisioni-e-questioni-aperte.md` | `107098edf` | 2026-10-12 | [[concepts/risk-binding-decisions]] — partial: the binding list via the README |

## 2026-10-12 — train 69: M-23 (base `d877a4e14`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ChangelogTranslation.prompt.md` | `1ed372534` | 2026-10-12 | [[decisions/fr-typography-at-build-time]], [[features/F-109]] (M-23) |

## 2026-10-12 — folder 02 (Risk), step R3a (base `4549376b8`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/A-contratto-asset-set.md` | `daa03c0f2` | 2026-10-12 | [[decisions/asset-set-one-preparation-not-fan-out]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/S3-livello-3.md` | `ac929a78e` | 2026-10-12 | [[decisions/l3-reads-current-composition]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/REGISTRO.md` | `33d5a599b` | 2026-10-12 | [[problems/runner-catalog-merge-not-line-union]], [[decisions/l3-reads-current-composition]] |

## 2026-10-12 — folder 02 (Risk), step R3b (base `e050cc142`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/R5-post-merge-e-review.md` | `107098edf` | 2026-10-12 | [[problems/risk-stress-buckets-hand-listed]], [[problems/replay-baseline-shortened-by-late-starter]], [[problems/echarts-stacked-band-null-base]] — partial: marker sections |

## 2026-10-12 — folder 02 (Risk), step R4 (base `97eecde84`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/contracts/README.md` | `33d5a599b` | 2026-10-12 | [[concepts/risk-contracts-k1-k9]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/progress/A-esecuzione.md` | `33d5a599b` | 2026-10-12 | [[decisions/histogram-grid-pinned-to-var-cut]], [[problems/annualization-factor-not-coverage]] |

## 2026-10-12 — folder 02 (Risk), step R5 (base `b4acfb250`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/02-verdetti-per-strumento.md` | `245aabf97` | 2026-10-12 | [[decisions/risk-tool-verdicts]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/06-matematica-librerie-e-reimplementazioni.md` | `0e704af4e` | 2026-10-12 | [[decisions/risk-library-versus-own-maths]] |

## 2026-10-12 — folder 02 (Risk), step R6 (base `843c9a9d2`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/_archive-backendFirst-G0G6/README.md` | `33d5a599b` | 2026-10-12 | [[sources/phase00-risk-analysis-backend]] — drift only |

## 2026-10-12 — folder 09, step F0 (base `dc00cbe9f`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/README.md` | `d614daed9` | 2026-10-12 | [[sources/phase00-feedback-jobs-2026-09]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/06_piano_sprint.md` | `d614daed9` | 2026-10-12 | [[sources/phase00-feedback-jobs-2026-09]] |

## 2026-10-12 — folder 09, step F1 (base `7ff48ac9b`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/00_backlog_strutturale_P4.md` | `d614daed9` | 2026-10-12 | [[sources/phase00-feedback-jobs-2026-09]], [[problems/privacy-gate-blind-to-formatter-consumers]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/09_reperti_analisi_statica_20260922.md` | `d614daed9` | 2026-10-12 | [[sources/phase00-feedback-jobs-2026-09]], [[problems/missing-event-detail-read-as-consent]] |

## 2026-10-12 — folder 09, step F2 (base `5c82d9bd4`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/08_review_visiva_20260922.md` | `d614daed9` | 2026-10-12 | [[problems/stale-version-file-shadows-git-describe]], [[sources/phase00-feedback-jobs-2026-09]] |

## 2026-10-12 — historical folder H1, 01_signalMigration (base `62471add2`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/README.md` | `8da24ef22` | 2026-10-12 | re-baseline of the July row (path moved, hash was `untracked`) |
| `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md` | `8da24ef22` | 2026-10-12 | re-baseline of the July row |
| `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/contract-phase00AiExportTaskProfiles.md` | `8da24ef22` | 2026-10-12 | re-baseline of the July row |
| `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/report-phase00AiExportMigrationEquivalence.md` | `8da24ef22` | 2026-10-12 | re-baseline of the July row |
| `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/plan-phase00SignalsBackendMigrationImplementation.prompt.md` | `8da24ef22` | 2026-10-12 | [[decisions/signal-indicator-warmup-sizing]], [[problems/spa-logout-cross-user-cache-leak]] — gaps only |

## 2026-10-12 — historical folder H2, 05_cleanAudit (base `42fc4dd7f`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/README.md` | `8da24ef22` | 2026-10-12 | [[sources/phase00-clean-audit-2026-08]] |
| `LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/17_stabilizzazione_suite_completa.md` | `8da24ef22` | 2026-10-12 | [[problems/asset-events-lost-on-price-cache-hit]], [[concepts/test-isolation-classes]] |

## 2026-10-12 — historical folder H3, 08_newCleanAndDocumentation_audit (base `61f7c970b`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/08_newCleanAndDocumentation_audit/00_INDEX.md` | `a9138140a` | 2026-10-12 | [[sources/phase00-clean-audit-2026-08]] |
| `LibreFolio_developer_journal/Release_2/phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md` | `a9138140a` | 2026-10-12 | [[problems/base-currency-setting-silently-defaulted-eur]] |

## 2026-10-12 — historical folders H4, 03 and 04 (base `63121ee78`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/03_brokerImportRecovery/README.md` | `8da24ef22` | 2026-10-12 | covered by [[decisions/credit-agricole-securities-only-cash-neutral-brim]] — read for drift, no new page |
| `LibreFolio_developer_journal/Release_2/phases/04_webSearchEngine/README.md` | `8dd918a15` | 2026-10-12 | [[decisions/web-link-finder-ddgs]] |

## 2026-10-12 — historical folder H5, Ai_ideas (base `b899903db`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Ai_ideas/brainstorming_ai_features.md` | `28b8443dd` | 2026-10-12 | [[sources/release2-ai-ideas-2026-07]] |
| `LibreFolio_developer_journal/Release_2/Ai_ideas/roadmap_and_signals_brainstorm.md` | `e7c33c85a` | 2026-10-12 | [[sources/release2-ai-ideas-2026-07]] |
| `LibreFolio_developer_journal/Release_2/Ai_ideas/mcp_server_architecture_draft.md` | `07be11cbc` | 2026-10-12 | [[sources/release2-ai-ideas-2026-07]] |
| `LibreFolio_developer_journal/Release_2/Ai_ideas/phase_0_detailed_roadmap.md` | `7992471b6` | 2026-10-12 | [[sources/release2-ai-ideas-2026-07]] |

## 2026-10-12 — historical folder H6, 06_betaTestingReportAndFixing (base `6e3d1368c`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/00_20260805_betaTester_report.md` | `91e88b8d1` | 2026-10-12 | [[sources/beta-testing-2026-08-05]] — re-baseline (moved) |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/01_tassonomia_findings.md` | `91e88b8d1` | 2026-10-12 | [[sources/beta-testing-2026-08-05]] — re-baseline (moved) |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/02_riconciliazione_credit_agricole.md` | `91e88b8d1` | 2026-10-12 | [[sources/beta-testing-2026-08-05]] — re-baseline (moved) |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/INDEX.md` | `91e88b8d1` | 2026-10-12 | [[sources/beta-testing-2026-08-05]] — re-baseline (edited) |

## 2026-10-12 — train 70, M's batch 28 (base `afd7d4821`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `21c3a3adc` | 2026-10-12 | §16.7, §17 → [[sources/phase00-translation-round12-2026-10]], [[problems/gallery-price-guard-expected-tofixed-text]], [[problems/docs-mathjax-looked-in-the-page-folder]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `21c3a3adc` | 2026-10-12 | the M-19 line only (spec registered) → [[problems/docs-mathjax-looked-in-the-page-folder]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `d00c06685` | 2026-10-12 | the CP1 note on the gallery's guard (before the STOP) → [[problems/gallery-price-guard-expected-tofixed-text]] |

## 2026-10-12 — train 71, U-2 and M's batch 29 (base `c57acf510`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` | `0a5285dc0` | 2026-10-12 | §10, U-2 → [[decisions/plugin-folders-and-split-i18n]], [[features/F-008]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `78c67f1b6` | 2026-10-12 | U-B6 → [[decisions/plugin-folders-and-split-i18n]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `6180aefd0` | 2026-10-12 | §18, batch 29 → [[sources/phase00-translation-round12-2026-10]] |

## 2026-10-12 — train 72, I's plan 48 and V's step 2b (base `0071b9703`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/48_uiPolish/plan-phase00UiPolish.prompt.md` | `f1e904b83` | 2026-10-12 | [[sources/phase00-ui-polish-2026-10]] and the five pages it links |
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `3d7635efb` | 2026-10-12 | §2b → [[sources/phase00-data-quality-e2e-2026-10]], [[problems/e2e-writes-leaked-into-shared-state]], [[problems/test-passed-only-on-leftovers-of-other-tests]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `6e9f2c47a` | 2026-10-12 | V-17 … V-23, 48-1 → the pages above |

## 2026-10-12 — train 74, U-3 and M's batches 30–32 (base `bcd502912`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` | `bcd4f6fe4` | 2026-10-12 | §10, U-3 → [[decisions/plugin-folders-and-split-i18n]], [[features/F-008]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `ac3a90813` | 2026-10-12 | §19–§21, batches 30–32 → [[sources/phase00-translation-round12-2026-10]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `2166eeb90` | 2026-10-12 | C-63, M-20, V-19 closed → [[decisions/clipboard-through-one-helper-with-a-gate]], [[problems/toolbar-measurements-differed-by-the-scrollbar-gutter]] |

## 2026-10-13 — trains 75 and 76, M-18's CP2 and CP3, V's gaps of 1.2 (base `986e99bd3`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `b65c39d0e` | 2026-10-13 | M-18 CP2, CP3a, CP3b → [[decisions/figures-in-the-interface-language]], [[features/F-008]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `ec488a296` | 2026-10-13 | §12.9 → [[decisions/e2e-gaps-of-1-2-before-release]], [[problems/e2e-writes-leaked-into-shared-state]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `986e99bd3` | 2026-10-13 | T-ST … T-DEAD, V-24, V-25 → the pages above |

## 2026-10-13 — trains 77 and 78, I's lot 49, M's batch 33, U-4 (base `1c710c7a8`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/49_requestCountRace/plan-phase00RequestCountRace.prompt.md` | `d4d4b301f` | 2026-10-13 | [[problems/request-counter-read-before-the-handler-counted]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` | `873d45175` | 2026-10-13 | §10, U-4 → [[decisions/plugin-folders-and-split-i18n]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `33bf5ef1b` | 2026-10-13 | batch 33 → [[sources/phase00-translation-round12-2026-10]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `1e1708528` | 2026-10-13 | M-24, U-B5, U-B7, 49-1 → the pages above |

## 2026-10-13 — train 79, T-EN1 and T-EN2 (base `b1a17b49b`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `0e291aa4e` | 2026-10-13 | «T-EN» → [[decisions/figures-in-the-interface-language]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `581588d39` | 2026-10-13 | T-EN1, T-EN2 closed; T-ISO, T-FB → [[decisions/figures-in-the-interface-language]] |

## 2026-10-13 — train 80, U-5 and M's batch 34 (base `cea8a478d`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` | `6a3b87d1c` | 2026-10-13 | §10, U-5 and the findings → [[decisions/plugin-folders-and-split-i18n]], [[problems/shared-server-rebuilt-the-frontend-past-its-startup-timeout]], [[problems/editing-a-running-bash-script-corrupts-its-run]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `cd1643ee2` | 2026-10-13 | batch 34 → [[problems/release-shots-show-dirty-version]], [[sources/phase00-translation-round12-2026-10]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `e97584a06` | 2026-10-13 | U-B2, U-B5, M-25 → the pages above |

## 2026-10-13 — train 81 (I's lot 50) and R's full run (base `5b169189d`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` | `588223c6f` | 2026-10-13 | [[sources/r-full-run-coverage-2026-10-12]] and its two open problems |
| `LibreFolio_developer_journal/Release_2/Phase_0/50_brokerDetailBudget/plan-phase00BrokerDetailBudget.prompt.md` | `f351293c4` | 2026-10-13 | [[problems/broker-detail-tests-over-budget-under-load]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `588223c6f` | 2026-10-13 | C-58 closed; C-67, C-68, C-69 → [[sources/r-full-run-coverage-2026-10-12]] |

## 2026-10-13 — train 82, V's §12.10 (base `273b188ea`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `452978f2e` | 2026-10-13 | §12.10 → [[problems/hidden-pair-half-survived-row-removal]], [[problems/e2e-writes-leaked-into-shared-state]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `73d083e46` | 2026-10-13 | V-21, V-25, V-26, V-27, V-29 → the pages above |

## 2026-10-13 — train 83, the CHANGELOG review and M's gallery (base `9686ee1f2`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `b2a21bb4a` | 2026-10-13 | C-70, C-71 → [[decisions/changelog-entry-rules]] |

## 2026-10-13 — C-64 last part, the plans of `phases/06_betaTestingReportAndFixing` (base `fa93b1777`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00AssetIdentityAndIdentifiers.prompt.md` | `91e88b8d1` | 2026-10-13 | D1–D11 → [[decisions/asset-identity-quoted-code-leads]]; the merge traps → [[problems/asset-merge-cascade-deleted-the-migrated-events]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00AssetLifecycleAndIdentifiers.prompt.md` | `91e88b8d1` | 2026-10-13 | superseded by P3; D4 → [[decisions/asset-identity-quoted-code-leads]], [[features/F-024]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00BrimCreditAgricoleTrades.prompt.md` | `91e88b8d1` | 2026-10-13 | B5-lite → [[decisions/import-row-split-legs-sum-to-the-row]]; detours listed on [[sources/beta-testing-2026-08-05]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00EngineAccountingAndSignals.prompt.md` | `91e88b8d1` | 2026-10-13 | E1 detour → [[problems/fx-error-dedup-went-quadratic-under-full-history]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/03_feedback_utenti_F1-F17_classificazione_e_fix.md` | `91e88b8d1` | 2026-10-13 | F2 → [[problems/portfolio-cache-ignored-role-and-share]]; F13 → [[features/F-062]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00TestRunnerMigration.prompt.md` | `91e88b8d1` | 2026-10-13 | D-3.3 → [[concepts/transaction-hygiene-fixture]]; detour 15 → [[concepts/derived-test-inventory]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00ImportWizardUx.prompt.md` | `91e88b8d1` | 2026-10-13 | W9 → [[features/F-083]] (corrected) |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00TransactionsUxPolish.prompt.md` | `91e88b8d1` | 2026-10-13 | T3 → [[concepts/txstore-pattern]] (corrected) |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00ImportFlowStepRestructure.prompt.md` | `91e88b8d1` | 2026-10-13 | findings listed on [[sources/beta-testing-2026-08-05]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00I18nAndDocsAssets.prompt.md` | `91e88b8d1` | 2026-10-13 | findings listed on [[sources/beta-testing-2026-08-05]] |
| `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00FrontendCoverage.prompt.md` | `91e88b8d1` | 2026-10-13 | findings listed on [[sources/beta-testing-2026-08-05]] |

## 2026-10-13 — the release page of 1.2.0, draft (base `2b1734e76`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `CHANGELOG.md` | `60f734e08` | 2026-10-13 | [[sources/release-1.2.0]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `b2a21bb4a` | 2026-10-13 | [[sources/release-1.2.0]] |
| `backend/alembic/versions/004_release_1_2_0_schema.py` | `f1047f766` | 2026-10-13 | [[sources/release-1.2.0]] |

## 2026-10-13 — trains 84–91 (base `fa6299689`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `237160725` | 2026-10-13 | lots 35–38 → [[sources/phase00-translation-round12-2026-10]], [[problems/schwab-favicon-blocked-by-orb]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `a0f6843d8` | 2026-10-13 | T-SHK, T-CL, T-ISO, T-FB → [[sources/phase00-financial-math-home-2026-10]], [[problems/test-hooks-read-the-localized-text]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `db90ecb07` | 2026-10-13 | V-27, V-28, V-33 → [[sources/phase00-data-quality-e2e-2026-10]] and the two resolved problems |
| `LibreFolio_developer_journal/Release_2/Phase_0/51_narrowFitFixes/plan-phase00NarrowFitFixes.prompt.md` | `5717bf2a8` | 2026-10-13 | lot 51 → [[problems/event-markers-lost-in-the-last-partial-period]], [[concepts/echarts-chart-gotchas]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `0c8d47d0d` | 2026-10-13 | V-30…V-34, M-26…M-29, T-CAT, T-GRP, T-EVW → the pages above |

## 2026-10-13 — trains 92–93 and the coordinator's commits (base `9313f81ee`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `de567029c` | 2026-10-13 | V-35, V-36 → [[sources/phase00-data-quality-e2e-2026-10]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` | `fafe68863` | 2026-10-13 | the open period's tooltip → [[problems/event-markers-lost-in-the-last-partial-period]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `9313f81ee` | 2026-10-13 | C-60, V-3, V-8, V-22, C-72, T-EVW → [[decisions/python-stays-on-3-13]], [[decisions/orphan-transfer-becomes-an-adjustment]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/research-python-3.15-20261012.md` | `426d9e1b7` | 2026-10-13 | [[decisions/python-stays-on-3-13]] (the baseline) |
| `.github/agents/release-coordinator.agent.md` | `6e1a2ef3e` | 2026-10-13 | [[problems/git-merge-stash-failed-on-locked-index]] |
| `CHANGELOG.md` | `4de042cfe` | 2026-10-13 | R-5's line, the risk API → [[sources/release-1.2.0]] |

## 2026-10-14 — trains 94–99 (base `bae15c3cf`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` | `a2182a5db` | 2026-10-14 | U-6, U-6b → [[problems/schwab-favicon-blocked-by-orb]], [[decisions/scalable-two-accounts-two-plugins]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `dd4d3e830` | 2026-10-14 | batches 39–42, final gallery → [[sources/phase00-translation-round12-2026-10]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` | `0822066ab` | 2026-10-14 | T1, T4, V-37, V-38 → [[problems/transaction-form-saved-a-refused-date]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/52_timeAxisLastLabel/plan-phase00TimeAxisLastLabel.prompt.md` | `e2aac137d` | 2026-10-14 | lot 52 → [[concepts/echarts-chart-gotchas]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/53_pacTests/plan-phase00PacTests.prompt.md` | `96ae2f31a` | 2026-10-14 | T-PAC → [[features/F-107]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/54_galleryFixtureShares/plan-phase00GalleryFixtureShares.prompt.md` | `3e99e65b6` | 2026-10-14 | I-M30 → [[problems/gallery-fixture-normalizer-scaled-ratios]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `bae15c3cf` | 2026-10-14 | C-59, C-73…C-76, U-B3, U-B8, U-B9, M-30…M-32, V-37b, V-38 → the pages above |

## 2026-10-14 — release day (base `a28beed92`)

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `CHANGELOG.md` | `a28beed92` | 2026-10-14 | the introduction, the date and the counts → [[sources/release-1.2.0]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-final-run-coverage-20261013.md` | `40576bdcd` | 2026-10-14 | R's final run → [[sources/release-1.2.0]], [[sources/r-full-run-coverage-2026-10-12]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | `c44e2b0cd` | 2026-10-14 | C-79…C-84, M-30 closed, M-33 → [[sources/release-1.2.0]] |
| `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` | `7b2cb679b` | 2026-10-14 | batch 45, the allocation re-shots → [[problems/gallery-fixture-normalizer-scaled-ratios]] |
| `LibreFolio_developer_journal/Release_2/Phase_1/08_email/plan-phase01Email.prompt.md` | `0e0c14868` | 2026-10-16 | E0–E4b, E-5, E6.0–E6.7 → [[domains/email]] |
