# Phase 0 — Archived Sub-Plans Index

> Completed work-streams of Release 2, archived here once done. Active work stays in
> `Phase_0/` (list at the bottom; until 2026-10-09 only `02_riskfolioIntegration`, paused in beta). Archiviata il 03/09: `06_betaTestingReportAndFixing` (beta feedback consolidation, chiusa).
> `Phase_0/04_webSearchEngine/` was fully archived on 2026-09-02 (ddgs suffices; SearXNG dropped). When a phase completes entirely, its folder moves under
> `phases/Phase_N/`.

| Archive | What it was | Outcome |
|---|---|---|
| `01_signalMigration/` | Backend Signals platform migration + AI Export V1 (incl. `02_aiExport/` subdir) | ✅ Shipped in 1.1.0 |
| `03_brokerImportRecovery/` | BRIM recovery: Crédit Agricole trades, import flow restructure | ✅ Shipped (Fase A+B) |
| `04_webSearchEngine/` | Web link-finder transport: raw DDG scraper → `ddgs` metasearch (+ SearXNG plan, not needed) | ✅ ddgs Steps 1–6; SearXNG dropped |
| `05_cleanAudit/` | Systematic dead-code/optimization audit (17 reports) + stabilization | ✅ Suite stabilized |
| `07_coverageAndConsolidationCampaign/` | Test runner parallelization, JS/Svelte coverage, 16 defects closed | ✅ Suite 15/15 green, 78% lines |
| `06_betaTestingReportAndFixing/` | Beta feedback consolidation (F1–F17, piani P1–P8) | ✅ Tutti i task eseguiti — archiviata il 03/09 (07/09: i residui P8 erano una scelta deliberata — le scritture restano seriali per la validità dei test; voce TODO rimossa) |
| `08_newCleanAndDocumentation_audit/` | Riverifica integrale dell'audit di agosto + esecuzione backlog (P0→P3), ondata docs/gallery/traduzioni, report 50 (gap v1.0.1→HEAD) | ✅ P0/P1/P2/P3 tutti chiusi e validati a zero; **residuo**: 8 task strutturali P4 → `Phase_0/09_feedbackJobs/` — archiviata il 07/09 |
| `11_feedbackContractsRunes/` | Gruppo B del feedback: contratti API e componenti Runes (SP04-SP05), `fxCreationSync`, `entityLink`, la riga compatta dei toast | ✅ B00-B10 e R1-01…06 integrati (`514582a47`, `00c469c3f`); residui → 38 (O-19, O-20) — archiviata il 09/10 |
| `14_feedbackImportUrgent/` | Feedback urgenti sull'import: piano incrementale e 5 round (review, condivisione, feedback social, confini social, autenticazione GHCR) | ✅ completata il 10/09 — archiviata il 09/10 |
| `15_parallelRuntimeIsolation/` | Corsie di runtime isolate (`--test-port`, `--data-dir`) per sviluppo e test paralleli | ✅ `916f12bdd` (10/09); il limite noto della gallery è scritto nel piano — archiviata il 09/10 |
| `17_assetDataOperations/` | Dati degli asset: classificazione dei bond, CSV delle distribuzioni, link nella modale di cancellazione | ✅ `e50d66408`, `cc57b6a38` (10-11/09) — archiviata il 09/10 |
| `18_brimTargeted/` | BRIM mirato: rifiniture degli import Crédit Agricole ed eToro | ✅ `ebba209c5`, merge `5c2a711f3` (10/09); residuo → 38 (L10) — archiviata il 09/10 |
| `19_yieldOnCost/` | Yield on Cost dal ledger delle transazioni (U3, SP06) | ✅ `74afcebce` (11/09); residuo → 38 (I-08) — archiviata il 09/10 |
| `20_performanceCharts/` | Grafici di performance (SP06 G3/G1c, SP07 G1a/G1b), eventi degli asset, colori e asse dei proventi | ✅ integrata; residui → 38 (I-01…I-04, I-06…I-12) — archiviata il 09/10 |
| `22_assetPricingRefactor/` | SP08: prezzi degli asset e confini del servizio | ✅ `3c85866dd` (11/09) — archiviata il 09/10 |
| `23_transactionBatchRefactor/` | SP16: scomposizione del batch delle transazioni | ✅ `846aefb24` (11/09) — archiviata il 09/10 |
| `24_privacyGlobal/` | Privacy globale, «nascondi valori» (U2, SP15), con la correzione della review d'uso del 22/09 | ✅ integrata; residuo → 38 (I-05) — archiviata il 09/10 |
| `26_brimDanskeBank/` | BRIM Danske Bank: pilota multi-report (report set) e codifica dei CSV | ✅ passi 4–9 integrati; residui → 38 (L1–L9) — archiviata il 09/10 |
| `28_fxDashboardSync/` | Lotti di N (06–09/10): FX in Dashboard, cache fra le pagine, banner di qualità dei dati, valuta di visualizzazione, `db <path>`, combine della coverage | ✅ 7 piani integrati; residui → 38 (N-1…N-9) — archiviata il 09/10 |
| `29_i18nAudit/` | Audit i18n: chiavi inutilizzate, doppioni, plurali, strumento | ✅ S0-S22; 4215 chiavi, 0 morte; residui → 38 (O-1…O-18) — archiviata il 09/10 |
| `30_wacUnification/` | Costo medio unico (issue #32) e validazione in blocco delle impostazioni globali | ✅ P0–P12 integrati; residui → 38 (P-1…P-9) — archiviata il 09/10 |
| `31_brimDegiro/` | Plugin DEGIRO (issue #35): lettura per posizione, in ogni lingua | ✅ merge `2cecf5a00` (treno 9) — archiviata il 09/10 |
| `33_e2eImportInfra/` | Infrastruttura dei test E2E dell'import | ✅ treno 10; residuo → 38 (L11) — archiviata il 09/10 |
| `34_accountAndIdReuse/` | Cancellazione dell'account, id che si riusano, ultimo admin | ✅ treni 12 e 22; residuo → 38 (L12) — archiviata il 09/10 |
| `35_devCliImage/` | `dev.py` dentro l'immagine Docker | ✅ merge `cdde3bc4d` (treno 19) — archiviata il 09/10 |
| `36_connectionSecurity/` | Indicatore di sicurezza della connessione e login senza enumerazione degli account | ✅ merge `01da03047` (treno 24) — archiviata il 09/10 |
| `25_taxonomySelect/` | K: tassonomia degli asset, select, Esc nelle modali, Bulk e correzioni (step 1–23) | ✅ step 1–23 integrati, l'ultimo nel treno 25; residui → 38 (K-1…K-26) — archiviata il 09/10 |
| `39_autoCostNoPosition/` | P-1 (P): il costo Auto salvato a 0 quando il broker d'origine non ha quote — analisi | ✅ chiusa senza codice per decisione del developer (09/10): lo 0 è il ripiego voluto di Auto, l'utente corregge la transazione; P-10, P-11 → 38 |

**Not archived (still active / paused):**
- `../Phase_0/02_riskfolioIntegration/` — Risk Analysis: resta in `Phase_0` per decisione del developer (D382, 09/10); il suo README elenca il lavoro aperto (A1–A7, B1–B6).
- `../Phase_0/09_feedbackJobs/` — backlog strutturale P4 ereditato dall'audit 08, reperti e review visiva (attivo: si pesca da lì al prossimo round).
- `../Phase_0/13_pacAllocator/` — allocatore PAC (workstream D), in chiusura per la 1.2.
- `../Phase_0/16_toolPlatform/` — piattaforma dei Tool, insieme alla 13.
- `../Phase_0/21_onboarding/` — onboarding: aspetta la review manuale C7 del developer.
- `../Phase_0/27_releaseImages/` — immagini di rilascio, gallery e pipeline (workstream M).
- `../Phase_0/32_docsEnglish12/` — documentazione inglese della 1.2 (workstream Q).
- `../Phase_0/37_brimScalable/` — plugin BRIM Scalable Capital (workstream S): in corso, entra con il suo checkpoint.
- `../Phase_0/38_postReleaseBacklog/` — backlog dopo la 1.2: i residui delle cartelle archiviate il 09/10 e il backlog del coordinatore.
