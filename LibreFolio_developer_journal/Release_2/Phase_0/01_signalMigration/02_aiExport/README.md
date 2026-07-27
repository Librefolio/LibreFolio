# Phase 0 — AI Export

**Stato**: ✅ COMPLETATO — 27 luglio 2026

Questa cartella costituisce il secondo sottopiano della migrazione segnali di Phase 0.
I file sono raccolti in `Release_2/Phase_0/01_signalMigration/02_aiExport`; non è
necessario spostarli nel diverso archivio `RoadmapV4_UI/phases/`.

| File | Ruolo | Stato |
|---|---|---|
| [Piano implementativo](plan-phase00AiExportBackendSnapshotImplementation.prompt.md) | Backend snapshot, frontend cutover, cleanup e verifica | ✅ |
| [Contratto task/profile](contract-phase00AiExportTaskProfiles.md) | 18 task, 3 detail level, 54 profili versionati | ✅ |
| [Migration Equivalence Report](report-phase00AiExportMigrationEquivalence.md) | Parità legacy, differenze deliberate e greenfield | ✅ |

## Risultato

- quattro domini backend: Portfolio, Broker, Asset e FX;
- catalogo/snapshot autenticati e fail-closed;
- prompt/clipboard frontend sicuri;
- hard cutover delle quattro superfici;
- legacy AI Export e quattro engine tecnici TypeScript rimossi;
- memoria UI per utente e contesto;
- documentazione, devWiki e knowledge graph aggiornati;
- gate backend/frontend/build/i18n/docs/E2E e review manuale completati.
