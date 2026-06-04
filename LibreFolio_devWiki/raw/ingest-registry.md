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
> For untracked files (external articles, PDFs in raw/): hash = `untracked`, no drift check possible.

| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md` | `61cc81e5` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-BugfixRound1.prompt.md` | `61cc81e5` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-BugfixRound2.prompt.md` | `61cc81e5` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrency.prompt.md` | `61cc81e5` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrencyFix.prompt.md` | `61cc81e5` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacFxEnrich.prompt.md` | `61cc81e5` | 2026-06-04 | [[sources/r3-sp-d-formmodal-wac-fx-chain]] |
| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/knowledge_base/00_project_overview.md` | `f17d963` | 2026-04-24 | [[sources/knowledge-base-overview]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/00-index.md` | `f17d963` | 2026-04-24 | [[sources/roadmap-v4-index]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part1.md` | `f17d963` | 2026-04-24 | [[sources/phase07-transactions]] |
| `LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` | `957a124` | 2026-04-24 | [[concepts/async-io-rule]], [[concepts/single-migration-strategy]], [[concepts/svelte5-runes]], [[problems/flag-emoji-windows]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/changelog_2026-04-10_live-ticker-and-provider-lifecycle.md` | `2c448cd` | 2026-04-24 | [[decisions/provider-shutdown-generic]], [[problems/liveticker-header-crash]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-subplan/plan-fxSyncApiRedesign.prompt.md` | `f123d4d` | 2026-04-24 | [[decisions/fx-sync-pair-based]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-subplan/analysis-brim-multiuser.md` | `84516e3` | 2026-04-24 | [[decisions/brim-broker-scoped]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-subplan/plan-data-separation.md` | `f17d963` | 2026-04-24 | [[decisions/prod-test-data-separation]] |
| `LibreFolio_developer_journal/RoadMapV1/01-Riassunto_generale.md` | `f17d963` | 2026-04-24 | [[sources/roadmap-v1-summary]] |
| `backend/app/db/models.py` | `f17d963` | 2026-04-24 | [[entities/db-models]] |
| `backend/app/api/v1/router.py` | `f1205b7` | 2026-04-24 | [[entities/api-router]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-00-setup.md` | `e8ab12a` | 2026-05-10 | [[decisions/sveltekit-over-react]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-01-foundation.md` | `e8ab12a` | 2026-05-10 | [[decisions/sveltekit-over-react]], [[decisions/zodios-api-client]], [[features/F-059]] |
| `TODO_FUTURI.md` | `fcdd89e` | 2026-04-24 | [[sources/todos]], [[features/F-075]] through [[features/F-096]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-03-layout-settings.md` | `e8ab12a` | 2026-05-10 | [[features/F-001]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-brokers.md` | `e8ab12a` | 2026-05-10 | [[features/F-009]], [[features/F-012]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-fx.md` | `e8ab12a` | 2026-05-10 | [[features/F-019]], [[features/F-020]], [[features/F-037]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-assets.md` | `e8ab12a` | 2026-05-10 | [[features/F-034]], [[features/F-037]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12-AssetEventAndScheduleRedesign.prompt.md` | `e8ab12a` | 2026-05-10 | [[decisions/scheduled-investment-redesign]], [[features/F-034]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step3/plan-phase06Step3Round12Finale-MaturationEngine.prompt.md` | `e8ab12a` | 2026-05-10 | [[decisions/scheduled-investment-redesign]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/PlanB/plan-partBDataEditorUnificato.prompt.md` | `e8ab12a` | 2026-05-10 | [[decisions/data-editor-unification]], [[concepts/editbuffer-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-subplan/plan-fxConversionChain.prompt.md` | `e8ab12a` | 2026-05-10 | [[features/F-020]] |
| `backend/app/services/asset_source_providers/scheduled_investment.py` | `e8ab12a` | 2026-05-10 | [[decisions/scheduled-investment-redesign]], [[features/F-034]] |
| `backend/app/services/asset_source_providers/justetf.py` | `e8ab12a` | 2026-05-10 | [[problems/justetf-websocket-disconnect]] |
| `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts` | `e8ab12a` | 2026-05-10 | [[concepts/editbuffer-pattern]], [[decisions/data-editor-unification]] |
| `frontend/src/lib/stores/TimeSeriesStore.ts` | `e8ab12a` | 2026-05-10 | [[concepts/timeseries-store-pattern]] |
| `frontend/src/lib/stores/fxStoreRegistry.ts` | `e8ab12a` | 2026-05-10 | [[concepts/timeseries-store-pattern]] |
| `backend/app/db/models.py` | `e8ab12a` | 2026-05-10 | [[entities/db-models]] (updated hash; previously `f17d963`) |
| `Dockerfile` | `e8ab12a` | 2026-05-10 | [[decisions/single-docker-image]] |
| `LibreFolio_developer_journal/knowledge_base/04_devpy_reference.md` | `e8ab12a` | 2026-05-10 | [[entities/devpy-cli]] |
| `TODO_Completati.md` | (live file) | 2026-05-10 | [[features/F-008]], [[features/F-014]], [[features/F-061]], [[features/F-034]], [[features/F-022]] |
| `TODO_FUTURI.md` | (live file) | 2026-05-10 | [[features/F-075]]–[[features/F-095]] |
| `LibreFolio_developer_journal/knowledge_base/03_documentation.md` | `e8ab12a` | 2026-04-24 | [[sources/kb-03-documentation]], [[features/F-069]], [[features/F-070]], [[features/F-074]], [[concepts/mkdocs-suffix-i18n]] |
| `LibreFolio_developer_journal/knowledge_base/06_testing_backend.md` | `e8ab12a` | 2026-04-24 | [[sources/kb-06-testing-backend]], [[features/F-068]], [[concepts/backend-test-isolation]] |
| `LibreFolio_developer_journal/knowledge_base/07_testing_frontend.md` | `e8ab12a` | 2026-04-24 | [[sources/kb-07-testing-frontend]], [[features/F-067]], [[features/F-074]], [[concepts/e2e-data-testid-rule]] |
| `LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md` | `e8ab12a` | 2026-04-24 | [[sources/kb-08-i18n-duplicates]], [[features/F-008]], [[decisions/i18n-key-rationalization]] |
| `LibreFolio_developer_journal/knowledge_base/01_backend.md` | `742248e` | 2026-04-24 | [[sources/kb-01-backend]] |
| `LibreFolio_developer_journal/knowledge_base/02_frontend.md` | `742248e` | 2026-04-24 | [[sources/kb-02-frontend]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step1/plan-phase06BugfixMigration-part2.md` | `381c30e` | 2026-04-24 | [[sources/phase06-bugfix-migration]], [[concepts/responsive-4mode-layout]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step1/plan-phase06BugfixMigration-part3.md` | `381c30e` | 2026-04-24 | [[sources/phase06-bugfix-migration]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/checklist-AssetProviders-CSSandScheduled.md` | `381c30e` | 2026-04-24 | [[sources/phase06-step2-providers]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/plan-phase06Step2cSyncDeleteRefactor.prompt.md` | `381c30e` | 2026-04-24 | [[sources/phase06-step2c-sync-refactor]], [[decisions/three-phase-pipeline]], [[problems/asset-sync-transaction-closed]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/plan-phase06Step6-i18n-dedup.prompt.md` | `381c30e` | 2026-04-24 | [[sources/phase06-step6-i18n-polish]] |
| Phase06 Step3 Rounds 1–11 (14 files in `Bugfix-Step3/`) | `e8ab12a` | 2026-05-24 | [[sources/phase06-step3-rounds]], [[features/F-033]], [[features/F-034]], [[problems/asset-list-500-provider-input-type]] |
| Phase06 Step4 PlanA + Plan0 (6 files in `Bugfix-Step4/PlanA/` + `Plan0/`) | `e8ab12a` | 2026-05-24 | [[sources/phase06-step4-plana]], [[features/F-033]], [[features/F-037]], [[features/F-042]], [[features/F-043]], [[decisions/signal-label-unification]] |
| Phase06 Step4 PlanC (5 files in `Bugfix-Step4/PlanC/`) | `e8ab12a` | 2026-05-24 | [[sources/phase06-step4-planc]], [[features/F-020]], [[features/F-042]], [[features/F-060]], [[features/F-061]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part2.prompt.md` | `f17d963` | 2026-04-24 | [[sources/phase07-part2-brim-revision]], [[features/F-012]], [[decisions/brim-parser-only]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3.md` | `c9b269` | 2026-04-24 | [[sources/phase07-part3-api-consolidation]], [[features/F-046]], [[decisions/multi-broker-atomic-tx]], [[decisions/tx-link-uuid-semantics]], [[decisions/price-currency-hard-reject]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure.md` | `66ad026a` | 2026-04-24 | [[sources/phase07-part3-closure]], [[features/F-046]], [[features/F-012]], [[features/F-051]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure_2.prompt.md` (+ Batch4d parts + BlockG) | `1bff6ad1` | 2026-04-24 | [[sources/phase07-part3-closure2]], [[concepts/savewithretry-frontend-pattern]], [[features/F-049]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte1/plan-phase07-transaction-Part1.md` | `a61b0dfa` | 2026-04-25 | [[sources/phase07-transactions]] (re-anchored after archive move; status ✅ DONE) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte2/plan-phase07-transaction-Part2.prompt.md` | `a61b0dfa` | 2026-04-25 | [[sources/phase07-part2-brim-revision]] (re-anchored; status ✅ DONE) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3.md` | `a61b0dfa` | 2026-04-25 | [[sources/phase07-part3-api-consolidation]] (re-anchored; status ✅ DONE) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure.md` | `a61b0dfa` | 2026-04-25 | [[sources/phase07-part3-closure]] (re-anchored; Policy D + backup endpoints surfaced) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure_2.prompt.md` (+ Batch4dPart2 + Batch4dPart3 + BlockG) | `a61b0dfa` | 2026-04-25 | [[sources/phase07-part3-closure2]], [[problems/assets-wipe-error-attr-mismatch]], [[problems/babel-currency-symbol-echo]], [[decisions/policy-d-currency-wipe]], [[entities/backup-router]] (G-batch6 + G-batch7, 87.06% coverage, 2 prod bugs) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/plan-phase07-transaction-Part4.prompt.md` | `dcb91929` | 2026-04-28 | [[sources/phase07-part4-transactions-ui]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md` | `444b2d16` | 2026-04-28 | [[sources/phase07-part4-round1]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` | `29898623` | 2026-04-28 | [[sources/phase07-part4-round2]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md` | `133cb0d4` | 2026-05-25 | [[sources/phase07-part4-round3-staging-rewrite]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md` | `133cb0d4` | 2026-05-25 | [[sources/phase07-part4-round3-bugfix1]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md` | `133cb0d4` | 2026-05-25 | [[sources/phase07-part4-round3-bugfix2]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md` | `133cb0d4` | 2026-05-25 | [[sources/phase07-part4-round4-unified-pipeline]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` | `133cb0d4` | 2026-05-25 | [[sources/phase07-part4-round5-server-type-rules]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md` | `0351d65f` | 2026-05-28 | [[sources/phase07-part4-round5-bugfix1-dual-form]], [[decisions/cash-transfer-split-promote]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md` | `0351d65f` | 2026-05-28 | [[sources/phase07-part4-round5-bugfix2-testwalk-overhaul]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md` | `0351d65f` | 2026-05-28 | [[sources/phase07-part4-round5-bugfix3-testwalk-fixes]], [[features/F-048]], [[features/F-047]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md` | `0351d65f` | 2026-05-28 | [[sources/phase07-part4-round6-context-menu-delete]], [[decisions/context-menu-all-tables]], [[features/F-047]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanA_ContextMenuBugfix.prompt.md` | `0351d65f` | 2026-05-28 | [[sources/phase07-part4-round6-plana-context-menu-bugfix]], [[problems/dual-form-collect-duplication]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB_DeletePickerAccess.prompt.md` | `0351d65f` | 2026-05-28 | [[sources/phase07-part4-round6-planb-delete-picker-access]], [[decisions/broker-access-min-paired]], [[features/F-047]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB1_BugfixRound1.prompt.md` | `0351d65f` | 2026-05-28 | [[sources/phase07-part4-round6-planb-delete-picker-access]] (B1 folded into Plan B source page) |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB23_Appendix1_UIPolish.prompt.md` | `42a45cf5` | 2026-05-29 | [[sources/phase07-part4-round6-planb23-appendix1-ui-polish]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md` | `b77da4d7` | 2026-05-29 | [[sources/phase07-part4-round6-planc-txstore-refactor]], [[concepts/txstore-pattern]], [[decisions/txstore-single-source-of-truth]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md` | `a23ad3e5` | 2026-05-30 | [[sources/phase07-part4-round6-planc3-pendingop-refactor]], [[decisions/pendingop-tagged-union]], [[concepts/txstore-pattern]], [[concepts/e2e-data-testid-rule]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC2_BugfixAndPairValidation.prompt.md` | `6aac0dce` | 2026-05-30 | [[sources/phase07-part4-round6-planc2-bugfix-pair-validation]], [[decisions/pair-description-tags-validation]], [[problems/fx-multi-route-no-fallback]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md` | `f9f3bec2` | 2026-05-30 | [[sources/phase07-part4-round6-planc2r2-regressions-mockfx]], [[decisions/auto-populate-removal]], [[decisions/formmodal-contextual-validate]], [[decisions/end-of-day-balance-check]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB23_BulkDeleteViaBulkModal.prompt.md` | `uncommitted` | 2026-05-31 | [[sources/phase07-part4-round6-planb23-bulk-delete]] (registry backfill — source page already existed from 2026-05-27 ingest) |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md` | `b0e223c0` | 2026-05-31 | [[sources/phase07-part4-round6-pland-split-promote-master]], [[decisions/cash-transfer-split-promote]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md` | `666059b5` | 2026-05-31 | [[sources/phase07-part4-round6-pland1-backend-batch-suggest]], [[decisions/cash-transfer-split-promote]], [[features/F-046]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_FrontendSplitPromoteUI.prompt.md` | `db7264ce` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-frontend-split-promote]], [[features/F-048]], [[features/F-047]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_1_SplitPromotePolish.prompt.md` | `fdf00d4b` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix1]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_2_PayloadSplitPreviewUX.prompt.md` | `eb9b8ae2` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix2]], [[features/F-048]], [[features/F-046]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_3_UXModalPayloadSuggestE2E.prompt.md` | `78f44497` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix3]], [[features/F-048]], [[features/F-046]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_4_SplitSuggestPmcOverrideUx.prompt.md` | `ce7344a1` | 2026-05-31 | [[sources/phase07-part4-round6-pland2-bugfix4]], [[features/F-048]], [[features/F-046]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/plan-R2-WalktestFeedbackRound.prompt.md` | `84f8bd07` | 2026-06-01 | [[sources/r2-walktest-feedback-master]], [[features/F-097]], [[features/F-048]], [[decisions/cost-basis-currency-object]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-A-CostBasisWAC.prompt.md` | `84f8bd07` | 2026-06-01 | [[sources/r2-sp-a-cost-basis-wac]], [[features/F-097]], [[decisions/cost-basis-currency-object]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-B-BackendTests.prompt.md` | `84f8bd07` | 2026-06-01 | [[sources/r2-sp-b-backend-tests]], [[features/F-097]], [[features/F-068]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-C-BulkModalSuggestUX.prompt.md` | `84f8bd07` | 2026-06-01 | [[sources/r2-sp-c-bulkmodal-suggest-ux]], [[features/F-048]], [[features/F-097]] |
| (commits `b0bfde60`, `f6023a73`, `6db90b73`, `2b0142f0`) — PWA Support | `84f8bd07` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-098]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-pwa-mobile-optimizations.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-098]] |
| (commit `a7b30d52`) — Port 60/40 Scheme | `84f8bd07` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[decisions/port-6040-scheme]] |
| (commit `7fd9c6df`) — Borsa Italiana Provider | `84f8bd07` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-099]] |
| (commit `0d7607e8`) — FX Provider Removal Fix | `84f8bd07` | 2026-06-02 | [[sources/r2-parallel-features-pwa-borsa-fx]], [[features/F-019]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/plan-SP-C-BugfixRound1.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/plan-SP-C-BugfixRound2-WacPreview.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]], [[features/F-048]], [[decisions/wac-inline-validate-commit]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/plan-SP-C-FxImpliedRateSpread.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-BugfixRound3-UnifiedPartnerArch.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[concepts/paired-partner-architecture]], [[features/F-048]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-ReactiveWacBulkModal.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-FixCloneLinkUuid.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[problems/clone-link-uuid-duplication]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-FixWacFeedbackLoop.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[problems/wac-feedback-loop]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-WacInlineValidateCommit.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[decisions/wac-inline-validate-commit]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-FixWacPartnerRows.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-StatelessWacPreview.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[concepts/stateless-preview-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-WacBackendCleanup.prompt.md` | `84f8bd07` | 2026-06-02 | [[sources/r2-sp-c-bugfix-chain]], [[features/F-097]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-BackendLogAudit.prompt.md` | `b5a0bf9` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-076]], [[concepts/log-level-policy]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-CandlestickChart.prompt.md` | `92c0516` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-080]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-FxRangeHelper.prompt.md` | `f5aadec` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[concepts/fx-range-helper-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-LazyImageCache.prompt.md` | `ce2bc92` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-086]], [[concepts/image-preview-cache-pattern]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-RsiSignalBands.prompt.md` | `6f0d4c6` | 2026-06-01 | [[sources/independent-batch-2026-06-01]], [[features/F-039]] |
