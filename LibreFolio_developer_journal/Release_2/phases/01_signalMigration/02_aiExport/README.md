# Phase 0 — AI Export

**Stato**: 🟢 AI EXPORT PUBLIC V1 PRONTO AL RILASCIO — 5 agosto 2026

Questa cartella costituisce il secondo sottopiano della migrazione segnali di Phase 0.
I file sono raccolti in `Release_2/Phase_0/01_signalMigration/02_aiExport`; non è
necessario spostarli nel diverso archivio `RoadmapV4_UI/phases/`.

| File | Ruolo | Stato |
|---|---|---|
| [Piano implementativo](plan-phase00AiExportBackendSnapshotImplementation.prompt.md) | Backend snapshot, frontend cutover, cleanup e verifica | ✅ |
| [Refinement consensus](gpt5.6_refinementPlan.md) | Requisiti concordati per fotografie, analisi, periodo e sampling | ✅ |
| [Piano refinement](plan-phase00AiExportRefinementImplementation.prompt.md) | 18 fotografie, 17 analisi, bucket adattivi e hard replacement v1 | 🟡 |
| [Checkpoint aggregazione Signal](plan-phase00AiExportCheckpointSignalAggregation.prompt.md) | Stato corrente, enum aggregation, Drawdown AREA e ordine di ripresa | ⏸️ |
| [Piano Signal/UI cutover](plan-phase00AiExportSignalAggregationUiCutover.prompt.md) | Backend enum/stats → API → chart/UI/clipboard → stop review | 🟡 |
| [Contratto task/profile](contract-phase00AiExportTaskProfiles.md) | Vecchio modello 19 task/57 profili, superato dal refinement | ⛔ |
| [Migration Equivalence Report](report-phase00AiExportMigrationEquivalence.md) | Parità legacy, differenze deliberate e greenfield | ✅ |
| [Riferimento funzionale compatto](report-phase00AiExportFunctionalReference.md) | Baseline pre-refinement; da aggiornare dopo il cutover | ⛔ |
| [Contenuti selezionabili e composizione](report-phase00AiExportSelectableContentComposition.md) | Per ogni pagina: 18 export dati, 17 analisi, prompt, dataset e componenti espansi | ✅ |
| [Guida ragionata al catalogo UI](report-phase00AiExportUiPromptCatalogExplainedV1.md) | Fotografia storica del catalogo V2 32 dataset/17 analisi | ✅ storico |
| [Piano Public Catalog V3](plan-phase00AiExportPublicCatalogReduction.prompt.md) | Riduzione 8 Export Data + 13 Analysis, componenti, probe e review | ✅ |
| [Public Catalog Reduction V1](report-phase00AiExportPublicCatalogReductionV1.md) | Architettura V3, composizione, misure, confronto e decisione | ✅ |
| [Task Adequacy Review V2](report-phase00AiExportTaskAdequacyReviewV2.md) | Review 126 varianti sul run autorevole V3 | ✅ |
| [Piano final audit e legacy removal](plan-phase00AiExportFinalAuditAndLegacyRemoval.prompt.md) | Rimozione runtime storico, audit test, ottimizzazioni exact-output e gate finale | ✅ |
| [Final Audit and Closure V1](report-phase00AiExportFinalAuditAndClosureV1.md) | Runtime unico, benchmark, matrice test/coverage, 114/114 equivalenti e run autorevole | ✅ |

## Stato corrente

- primo contratto pubblico: snapshot, catalogo, selezioni e prompt contract V1;
- 67 componenti, 40 Dataset e 11 Analysis nel registry interno;
- catalogo pubblico: 8 Export Data + 11 Analysis;
- run autorevole pre-release: `real_prompt_probe/20260804T224056.073291Z`;
- 114/114 prompt, 0 failure/skip, 36 retained, secret scan passato;
- 66/66 varianti Analysis `OPTIMAL`;
- probe reale e Task Adequacy separati dal test runner funzionale;
- traduzioni UI EN/IT/FR/ES complete; traduzioni MkDocs da rigenerare dalla
  sorgente inglese aggiornata.

## Stato al checkpoint storico

- fondazioni backend, temporal engine, cataloghi e componenti dominio implementati;
- 18 dataset e 17 analisi congelati ma non ancora esposti dal contratto pubblico;
- Portfolio/Broker e Asset/FX registry fragment presenti; central registry non cablato;
- frontend ancora sul contratto AI Export precedente;
- nuova decisione bloccante: aggregazione per-output dichiarata dal Signal Plugin;
- Drawdown richiede `AREA` + `MIN_LAST`;
- nessun frontend test, wiki ingest/lint o cleanup finale da eseguire prima della ripresa.

Dettaglio e ordine di ripresa:
[Checkpoint aggregazione Signal](plan-phase00AiExportCheckpointSignalAggregation.prompt.md).
