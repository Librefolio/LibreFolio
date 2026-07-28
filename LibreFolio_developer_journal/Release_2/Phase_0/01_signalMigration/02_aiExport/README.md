# Phase 0 — AI Export

**Stato**: ⏸️ PAUSA — CHECKPOINT SIGNAL AGGREGATION — 28 luglio 2026

Questa cartella costituisce il secondo sottopiano della migrazione segnali di Phase 0.
I file sono raccolti in `Release_2/Phase_0/01_signalMigration/02_aiExport`; non è
necessario spostarli nel diverso archivio `RoadmapV4_UI/phases/`.

| File | Ruolo | Stato |
|---|---|---|
| [Piano implementativo](plan-phase00AiExportBackendSnapshotImplementation.prompt.md) | Backend snapshot, frontend cutover, cleanup e verifica | ✅ |
| [Refinement consensus](gpt5.6_refinementPlan.md) | Requisiti concordati per fotografie, analisi, periodo e sampling | ✅ |
| [Piano refinement](plan-phase00AiExportRefinementImplementation.prompt.md) | 18 fotografie, 17 analisi, bucket adattivi e hard replacement v1 | 🟡 |
| [Checkpoint aggregazione Signal](plan-phase00AiExportCheckpointSignalAggregation.prompt.md) | Stato corrente, enum aggregation, Drawdown AREA e ordine di ripresa | ⏸️ |
| [Contratto task/profile](contract-phase00AiExportTaskProfiles.md) | Vecchio modello 19 task/57 profili, superato dal refinement | ⛔ |
| [Migration Equivalence Report](report-phase00AiExportMigrationEquivalence.md) | Parità legacy, differenze deliberate e greenfield | ✅ |
| [Riferimento funzionale compatto](report-phase00AiExportFunctionalReference.md) | Baseline pre-refinement; da aggiornare dopo il cutover | ⛔ |

## Stato al checkpoint

- fondazioni backend, temporal engine, cataloghi e componenti dominio implementati;
- 18 dataset e 17 analisi congelati ma non ancora esposti dal contratto pubblico;
- Portfolio/Broker e Asset/FX registry fragment presenti; central registry non cablato;
- frontend ancora sul contratto AI Export precedente;
- nuova decisione bloccante: aggregazione per-output dichiarata dal Signal Plugin;
- Drawdown richiede `AREA` + `MIN_LAST`;
- nessun frontend test, wiki ingest/lint o cleanup finale da eseguire prima della ripresa.

Dettaglio e ordine di ripresa:
[Checkpoint aggregazione Signal](plan-phase00AiExportCheckpointSignalAggregation.prompt.md).
