# Piano Phase 0 — AI Export final audit, legacy removal e chiusura

**Stato**: ✅ Completato  
**Avvio**: 2026-08-04  
**Baseline sorgenti**: commit `54a15b42`

## Obiettivo

Chiudere AI Export mantenendo invariato il contratto pubblico V3 e rimuovendo il
runtime storico profile/assembler, le Analysis interne legacy, test/fixture
obsoleti e passaggi runtime ridondanti. Il risultato finale deve avere un solo
runtime component-based, zero test orphan e prompt pubblici equivalenti.

## Vincoli

- Catalogo pubblico invariato: 8 Dataset + 11 Analysis.
- Snapshot V2, Catalog V3, P/M/K, eventi, coverage e semantica finanziaria
  invariati.
- Conservare 67 componenti e 40 dataset, inclusi i dataset interni V3.
- MkDocs: aggiornare solo inglese; non tradurre e non stampare.
- Nessun commit, push, release o wiki lint.

## Passi

1. ✅ Baseline corpus/benchmark/import/test runner. — 2026-08-04
   > **Note implementazione**: run baseline
   > `20260804T214400.268752Z` completato 114/114, 36 prompt retained,
   > 0 failure/skip, secret scan passato e DB source/production invariati.
   > Benchmark salvato nel run: import cold mediano ~1,43 s, registry chain
   > ~0,116 ms, catalogo ~0,295 ms, stats runtime 3 full JSON dump sia su
   > payload piccolo sia da 500 KB.
   > **⚠️ Fuori pista**: il precedente staging era già stato committato
   > manualmente nei commit `54a15b42` e `be0e6a0b`; la baseline sorgenti è
   > quindi il commit pulito `54a15b42`, mentre il worktree sporco appartiene
   > alla pipeline MkDocs parallela.
2. ✅ Registrazione test orphan e correzione duplicazioni test. — 2026-08-04
   > **Note implementazione**: aggiunti i tre file mancanti a
   > `AI_EXPORT_SERVICE_TEST_PATHS`; rimosso dal test Drawdown il count globale
   > duplicato e obsoleto. I tre file ora passano 63/63 e
   > `./dev.py test check-orphans` riporta zero orphan backend/frontend.
3. ✅ Spostamento helper FIFO e riduzione telemetry. — 2026-08-04
   > **Note implementazione**: completato il seam FIFO: i cinque helper live
   > sono ora in `components/payloads/portfolio_broker.py`, nessun componente
   > V3 importa più `assemblers.fifo`, e 103 test financial/integration passano.
   > **⚠️ Fuori pista**: la riduzione di `telemetry.py` viene applicata
   > atomicamente insieme alla cancellazione legacy, perché
   > `assemblers/shared.py` usa ancora `build_export_stats` fino a quel momento.
   > **Note implementazione**: `telemetry.py` ora contiene soltanto canonical
   > JSON e stima chars/4 schema-independent; entrambi i density probe importano
   > correttamente la utility ridotta.
4. ✅ Rimozione runtime/schema/test/fixture legacy e Analysis interne. — 2026-08-04
   > **Note implementazione**: eliminati service/resolver/models, sampling,
   > coverage, technical, normalization, profiles, assemblers, schema V1, 9
   > file test legacy e 4 fixture legacy. `ai_export/__init__.py` non carica più
   > il vecchio stack. Registry Analysis ridotto da 22 a 11, tutte pubbliche.
   > Gate intermedi: 822 service test, 16 schema test, 56 probe utility,
   > density probe import smoke e zero test orphan.
5. ✅ Ottimizzazioni runtime exact-output. — 2026-08-04
   > **Note implementazione**: registry/composer default condivisi e catalogo
   > cacheato; envelope API costruito dal payload già validato; stats risolti
   > con un solo full dump e fixed-point intero. 25 test runtime passano,
   > inclusi Unicode e soglie digit-count. Benchmark: catalogo ~0,295→0,0008
   > ms/call; full dump 3→1; payload 500 KB ~5,20→2,22 ms con chars/bytes
   > identici (501.065).
6. ✅ Aggiunta test mancanti. — 2026-08-05
   > **Note implementazione**: aggiunti test per `NotAllowedError` clipboard,
   > income timeline con conversione parziale, helper FIFO, registry/catalog
   > cache, fixed-point stats, envelope bridge e contratto E2E
   > `portfolio.fiscal_lots`. Gate mirati: 34 unit frontend, 25 runtime backend,
   > 103 FIFO financial/integration e fiscal E2E 2/2 desktop/mobile.
7. ✅ Audit coverage e consolidamento finale. — 2026-08-05
   > **Note implementazione**: coverage combinata su service/schema/API/probe.
   > Moduli AI Export live tra 77,78% e 100%; core finanziari 97–99%, runtime
   > 90,88%, schema 91,71%. Il solo gap contrattuale netto era la validazione
   > input dei mini-bucket uniformi: aggiunti 3 test; suite temporal 182/182.
   > Non sono stati aggiunti test cosmetici per branch di validator già coperti
   > semanticamente da altri modelli.
8. ✅ Documentazione EN aggiornata. — 2026-08-05
   > **Note implementazione**: aggiornati esclusivamente runtime,
   > composition e test walkthrough inglesi: runtime unico, 67/40/11,
   > comandi schema/coverage/orphan. MkDocs build riuscito; nessuna
   > traduzione/stamp eseguita.
   > **⚠️ Fuori pista**: `mkdocs check-links` segnala il preesistente link
   > dinamico `${lang` in `AboutTab.svelte:145`, fuori scope AI Export; i 18
   > link statici verificabili sono validi.
9. ✅ Gate completi + probe candidate 114 + confronto baseline. — 2026-08-05
   > **Note implementazione**: gate pre-probe verdi: 835 service, 16 schema,
   > 15 API, 56 probe utility, 199 frontend unit, 34 Playwright,
   > typecheck 0/0, i18n 2332/2332, zero orphan, registry 67/40/11,
   > diff sorgenti pulito. MkDocs build verde; link-check conserva un solo
   > falso positivo/preesistente `${lang` fuori scope.
   > **Note implementazione**: candidate
   > `20260804T224056.073291Z` completato 114/114, 36 retained, 0
   > failure/skip. Il confronto con baseline `20260804T214400.268752Z`
   > classifica 114/114 chiavi `unchanged`: zero delta su caratteri, byte,
   > composizione, eventi e stato. Secret scan, equivalenza UI/probe e hash DB
   > primario/source sono verdi. Review qualitativa completata su min, median,
   > P90, max, FIFO, FX e partial-data.
   > **Note implementazione**: Task Adequacy finale sulle 66 varianti Analysis:
   > 54 review invarianti riusate dal run autorevole precedente e 12 varianti
   > fiscali rilette sul nuovo contratto; 66/66 `OPTIMAL`, 0 sufficient/
   > insufficient.
10. ✅ Staging sorgenti e handoff finale. — 2026-08-05
    > **Note implementazione**: messi in staging esclusivamente 64 file sotto
    > `backend/`, `frontend/` e `scripts/test_runner/`: 890 inserimenti,
    > 21.901 eliminazioni. MkDocs, journal, devWiki, run probe e traduzioni
    > parallele restano unstaged. `git diff --cached --check`, Ruff e Black
    > mirati sui 26 Python modificati e Prettier frontend sono verdi.
    > **⚠️ Fuori pista**: il lint Ruff globale vede 36 violazioni preesistenti
    > in file non inclusi nel change set (`settings.py`, Borsa Italiana,
    > ROI/scheduler tests); non sono state corrette né messe in staging.

## Artefatti previsti

- `real_prompt_probe/<baseline_run_id>/`
- `real_prompt_probe/<candidate_run_id>/`
- `report-phase00AiExportFinalAuditAndClosureV1.md`

## Collegamenti

- [Piano Public Catalog V3](plan-phase00AiExportPublicCatalogReduction.prompt.md)
- [Public Catalog Reduction V1](report-phase00AiExportPublicCatalogReductionV1.md)
- [Task Adequacy Review V2](report-phase00AiExportTaskAdequacyReviewV2.md)
