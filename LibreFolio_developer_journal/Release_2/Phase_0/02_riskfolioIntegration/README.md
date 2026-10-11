# Risk Analysis — ripianificazione

**Data apertura**: 16 Settembre 2026
**Stato**: ⏸️ **in pausa fino a dopo la 1.2**, per decisione del developer (D382, 09/10/2026): la cartella resta in
`Phase_0/` e non si archivia. Il 10/10 le voci aperte di Risk, A e F sono state raccolte qui dalla memoria delle tre
sessioni: una chat nuova riparte da questo file
**Premessa (16/09)**: il sottosistema Risk era **rilasciato in beta** con un banner su ogni vista. Dalla 1.2.0 il banner
resta solo sul gradino «simulazione» di L4 e sulla scheda Rischio di Asset Detail (CHANGELOG 1.2.0).

## ⏸️ In pausa fino a dopo la 1.2 — cosa resta aperto

Il developer, il 09/10/2026: *«risk facciamo bene ad aggiornarlo, ma non lo archivamo perchè ancora non va bene, lo so
già guardandolo, solo mi sono fermato dal lavorarlo per concludere questa release»* (D382). La cartella resta intera in
`Phase_0/`, e le voci aperte della famiglia Risk (Risk, A, F) stanno **qui, e solo qui**.

Il 09/10 i piani sono stati allineati al codice di `3cceb4f90`. Il 10/10 questo elenco è stato riverificato su
`d59762e0a` e completato con quello che stava solo nella memoria delle sessioni Risk, A e F, che si chiudono: una chat
nuova riparte da qui e dalla guida più sotto, «🧭 Ripartire da qui». Le righe di codice citate sono quelle di
`d59762e0a`: prima di lavorare una voce, si riverifica.

### Lavoro pianificato e non fatto

| # | cosa | da dove viene |
|---|---|---|
| A1 | **Fase 3**: il pannello «+» degli asset anche nel segnale «Confronto Asset» e negli altri usi di `SignalAssetParamControl`. Le fasi 1 e 2, il selettore del benchmark, sono fatte (D370, D371, D378) | richiesta del developer del 02/10, in [`implementation_2/progress/F-L3-rischio-rendimento.md`](./implementation_2/progress/F-L3-rischio-rendimento.md) |
| A2 | **Asset Detail**: la scheda Rischio va riprogettata. Oggi `AssetRiskScenariosView.svelte` monta ancora il pannello monolitico `RiskAnalysisPanel.svelte`, con TE, IR e `sobol_start_index`, e tiene il banner beta. Non riceve `data_quality.issues`, quindi non ha il banner «Sincronizza» (D373). Con lei tornano D54 e le colonne di B2 | D8, D47, D373 |
| A3 | **Simulazione**: resta in beta finché non c'è una guardia sul rapporto fra storia e orizzonte | `TODO_FUTURI.md` § «La simulazione risponde alla finestra, non al portafoglio» |
| A4 | **Percorsi adattivi** della simulazione per i portafogli grandi: oggi, ai valori di default, da 67 posizioni la risposta è «troppo grande», con la cura. È anche C-21 del backlog 38 | D379; il developer l'ha messa dopo la 1.2 (07/10) |
| A5 | **Rendimento totale** con cedole e dividendi: oggi i rendimenti vengono dai soli prezzi | `TODO_FUTURI.md` § «Rischio — rendimento totale con cedole e dividendi» |
| A6 | **Ottimizzazione oltre 100 titoli utilizzabili**: risponde `invalid_parameters` invece di `resource_limit`. Il tetto sta in `OptimizationEngineRequest` (`backend/app/services/risk/quant/optimization_models.py:21`, `max_length=100`): Pydantic solleva una `ValidationError`, che è un `ValueError`, e la prende il ramo `except ValueError` (`risk_plugins/portfolio_optimization.py:221`), non quello di `OptimizationResourceLimitError` (`:189`). Riprovato il 10/10 con 101 id. Nessun pannello chiede l'ottimizzazione | [`implementation_2/R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md), D381 |
| ~~A7~~ | ✅ **Traduzioni** delle pagine di teoria del rischio: 22 su 22 in it, fr ed es, dal giro di traduzione della 1.2 (`647475999`). Il debito di traduzione che resta lo conta `./dev.py mkdocs translate-validate` (backlog 38) | [`implementation/I-documentazione.md`](./implementation/I-documentazione.md), «terza metà» |

### Buchi veri

Promessi da un piano o da una decisione, mai fatti, e senza una decisione che li abbia cambiati.

| # | cosa | evidenza | peso | proposta |
|---|---|---|---|---|
| B1 | **L'icona della documentazione su tutti i pannelli di tutte le pagine**, con la sua pagina | decisione del developer del 24/09 ([`implementation_2/progress/F-laboratorio-postmerge.md`](./implementation_2/progress/F-laboratorio-postmerge.md), «Correzioni in avanti e decisione del developer sul seguito»; Doc1–Doc3 in [`implementation_2/R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md)). Sul rischio c'è; fuori no: dei componenti di `frontend/src/lib/components/dashboard/` solo `KpiSection.svelte` ha un `DocsLink` | medio | l'inventario pagina per pagina (Doc1) e un giro dedicato dopo la 1.2, oppure una decisione che ne restringa la portata |
| B2 | **Le colonne di rischio di Asset Global** (D54: nascoste per default, il max drawdown visibile) e la colonna ρ̄ (F-4) | mai costruite. Il rinvio a `TODO_FUTURI.md` annunciato da F ([`implementation/progress/F-esecuzione.md`](./implementation/progress/F-esecuzione.md), Q-F4) non è mai stato scritto. La fonte dei dati ora c'è (`asset_set_kpi`, `asset_set_drawdown`) | basso-medio | decidere: costruirle con la ripresa di Asset Detail, come dice D54, oppure ritirare D54 |
| B3 | **La fetta per asset del portafoglio** (D58, D59): il backend c'è, nessuna pagina la chiede | `PortfolioRiskScope.asset_ids` e `sliced_asset_ids` in `backend/app/schemas/risk.py` (`:665`, `:533`); il frontend costruisce lo scope `portfolio` solo con `broker_ids` (`routes/(app)/dashboard/+page.svelte:1041`, `routes/(app)/brokers/[id]/+page.svelte:682`). Così il confronto di una fetta con il suo riferimento, lo scopo di D59, non si può fare, e la rinormalizzazione non è dichiarata da nessuna parte ([`implementation/C-backend-affettamento-portafoglio.md`](./implementation/C-backend-affettamento-portafoglio.md), definizione di finito) | medio | decidere alla ripresa: un selettore della fetta in L3, oppure ritirare la parte di interfaccia di D58 |
| ~~B4~~ | ✅ **Il CHANGELOG 1.2.0 dice che due numeri della 1.1.0 cambiano**: M2 (VaR e CVaR) e A9 (il tasso privo di rischio alla frequenza della serie) | due righe in «🔄 Changed», scritte dal coordinatore (`586a4f0ea`, 09/10). Danno l'ordine di grandezza e da cosa dipende, non una cifra sola: le cifre del brief di J valgono in un caso particolare (verifica in [`implementation_2/R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md), «Allineamento del 09/10/2026») | — | — |
| ~~B5~~ | ✅ **Le pagine di Sharpe e Sortino scrivono il tasso del periodo con l'esponente `1/f`**, come il codice (A9) | corrette da Q in inglese (`1fdcaef38`, 09/10); le traduzioni non avevano la formula, e il giro di traduzione della 1.2 (`647475999`) l'ha portata già giusta | — | — |
| B6 | **V1 e V2 della lista di A**, dalla review visiva del developer: i badge degli asset e la frase breve nell'avviso unico; il tooltip vero sulle barre dell'istogramma | [`implementation_2/progress/A-dashboard-esecuzione.md`](./implementation_2/progress/A-dashboard-esecuzione.md), tabella del lavoro; `levels/l1/ReturnHistogram.svelte:67` usa ancora il `title` nativo; `AssetChip.svelte` esiste già | basso | un giro piccolo alla ripresa |
| B7 | **La matrice di correlazione di L2, su Dashboard e Broker, ordina solo per «similarità» e «nome»**: V4 di A e di F, mai fatto. L'allineamento del 09/10 l'aveva segnato ✅ per errore (corretto il 10/10) | `levels/L2Diversification.svelte:363` monta `CorrelationHeatmap` con i soli `assetLabels`. Gli ordinamenti per tipo, settore e area chiedono `assetTypes`, `assetSectors` e `assetRegions` (`CorrelationHeatmap.svelte:78-82`), che oggi passa solo il laboratorio (`AssetSetCorrelationSection.svelte:144`). È la decisione K11 del giro UI | basso-medio | F estrae in un pezzo condiviso il caricamento delle tre mappe, oggi in `AssetSetCorrelationSection.svelte`; A lo collega in L2 |
| B8 | **La paginazione della tabella di L3 oltre 5 righe**, chiesta dal developer il 05/10, tramite A: *«nella tabella metti la paginazione se ci sono più di 5 righe»* | `RiskReturnLevel.svelte:307`, `enablePagination={false}` | basso-medio | qui sotto, «La paginazione di L3 (B8)» |

#### La paginazione di L3 (B8)

- **Deciso il 06/10**, in linea di principio, col coordinatore:
  - `RiskReturnLevel.svelte` è di A: `defaultPageSize` 5 e opzioni `[5, 10, 25, 0]`, come in `DistributionEditor`;
  - prima, in un commit `feat(ui)` a parte scritto da F, un'opzione additiva:
    `DataTable.navigateToRowId(rowId, {scroll = true, highlight = true} = {})`. I rossi vengono prima, in
    `DataTable.test.ts`, con un test **obbligatorio** del percorso di default che fissi lo
    `scrollIntoView({behavior: 'smooth', block: 'center'})` di oggi (`frontend/src/lib/components/table/DataTable.svelte:898`):
    nessun test lo fissa. Le 13 chiamate esistenti, tutte fuori dalla famiglia, tengono i default;
  - `onRowOrderChange`, il prerequisito di K, è già nella base (`DataTable.svelte:94`).
- **Perché**: il clic su un punto la cui riga sta su un'altra pagina deve portare su quella pagina. Oggi
  `navigateToRowId` (`DataTable.svelte:876`) evidenzia la riga e la porta al centro con uno scroll fluido: col grafico
  sotto la tabella, la vista salta via dal punto.
- **Da decidere col developer**:
  - il punto cambia pagina senza muovere la vista?
  - anche L1° pagina? La richiesta diceva «la tabella»;
  - come contano le righe di riferimento: aprono la tabella e prendono un posto sulla prima pagina, e dopo un
    ordinamento possono finire su un'altra.
- **Trappole**:
  - le fixture del laboratorio con più di 5 righe: `SELECTION_WITH_REFERENCE` (6) e `WIDE_SELECTION` (12) in
    `AssetSetRiskReturnSection.test.ts`;
  - una decina di controlli E2E contano le righe e le celle di L3 per asset selezionato (`paidRows`,
    `toHaveCount(selected.length)`);
  - `navigateToRowId` calcola la pagina da `sortedData`, dove le righe di riferimento vengono prima.

### Difetti noti

- **L4, la tabella dello shock** (da A). Il developer non l'ha più rivista dopo la correzione del peso (07/10: «via con
  i test»), e nessuno ha deciso. I file: `levels/l4/L4Shock.svelte`, di A; `levels/l4/TornadoChart.svelte` e
  `levels/l4/scenarioHelpers.ts`, di Risk.
  - Le righe mostrano gli id grezzi dei bucket (`CROWDFUND_REAL_ESTATE`, `ETF_MONETARY`): `rowLabel`, in
    `L4Shock.svelte:99-104`, lo dice nel commento «listed as debt». Per `asset_class` le etichette ci sono già in
    quattro lingue (`assets.types.<TIPO>`); per settore e area le rende leggibili il pannello legacy, da riusare.
  - La prima colonna si chiama «Asset» anche quando le righe sono categorie (`TornadoChart.svelte:101`,
    `risk.levels.l4.table.asset`).
  - I bucket che nessuno possiede restano righe a 0,0%: 15 su 18 in «Global risk-off», sui dati di prova. Sullo scope
    pesato il loro `contribution_return` vale 0 e non `null`, quindi `tornadoRows` (`scenarioHelpers.ts:158`) non li
    scarta. Da decidere: un bucket vuoto, con uno shock scritto a mano dal lettore, resta visibile?
  - Proposta: un giro piccolo, con la review visiva del developer.
- **Laboratorio: i verdetti di ammissibilità non si richiedono dopo una sincronizzazione** (da F; letto nel codice, non
  provato a runtime).
  - La domanda, `eligibilityQuestion` (`AssetSetRiskPanel.svelte:260`), dipende da elenco, periodo e valuta.
    `handleSynced` (`:200`) e `reload()` (`:224`) alzano `syncGeneration` e chiamano `invalidateRisk()`, ma
    l'ammissibilità è una chiamata diretta (`:281`), fuori dalla cache del rischio.
  - Così, dopo **Sync selection**, gli avvisi dei chip e gli asset parcheggiati restano com'erano finché non cambia il
    periodo o non si ricarica la pagina. Da D378 resta anche un benchmark `blocked` per `stale_at_end`: l'utente
    sincronizza, e il benchmark resta bloccato.
  - Idea: `syncGeneration` nella chiave della domanda; L3° torna ad aspettare, e la domanda resta una. Trappola: L3° si
    rimonterebbe dopo ogni Reload All.
- **Laboratorio: all'apertura ogni sezione chiede due volte.** Solo L3° aspetta i verdetti di ammissibilità
  (`AssetSetRiskPanel.svelte`; reperto di F al giro 15). Chi lo cura legga prima i vincoli nelle trappole del
  laboratorio, più sotto.
- **Correlazione: l'avviso `low_pair_coverage` non scatta mai, e lo slider `min_coverage` non governa nulla** (D144,
  mai corretto). `risk_plugins/correlation.py:76` confronta la soglia con la copertura di
  `pairwise_correlation_matrix` (`risk/metrics.py:583`: osservazioni su osservazioni attese), che vale 1 per
  costruzione, perché le serie condividono il calendario preparato. Il risultato pubblica invece `calendar_coverage`
  (`correlation.py:139`). Visto il 24/09: copertura 0,577 sotto la soglia di 0,6, e nessun avviso.
- **Laboratorio, C-23 del backlog 38: «Risalita al massimo» tagliata a destra in italiano.** Una causa da provare, di
  F. Le larghezze di L1° (`headerWidth` e `measureHeaderTitle`, `riskReturnLevel.ts:106-123`) si misurano quando si
  derivano le colonne, con `getComputedStyle(document.body).fontFamily`, e si rimisurano solo al cambio di lingua: se
  il font web non è ancora caricato si misura quello di ripiego, e nulla rimisura quando i font arrivano. Cura da
  provare: ricalcolare dopo `document.fonts.ready`. Altrimenti è lo scroll orizzontale: da 13-B i nomi non sono
  fissati, e l'ultima colonna sta oltre la card.
- **Documentazione**:
  - `risk-contribution.en.md` lascia intendere che le quote negative vengano solo dalle posizioni corte (basta un
    asset di copertura);
  - `max-drawdown.en.md` parla di «portfolio value», mentre il codice usa il TWRR;
  - `value-at-risk.en.md` non dice che il VaR a un mese si calcola su finestre sovrapposte (`horizon_compounded_returns`,
    `risk/metrics.py:744`): con un anno di storia poggia su circa 12 mesi indipendenti, quindi è fragile. Va scritto
    come limite.
- **`HurtRow.secondaryLoss` è un campo morto** (`levels/levelHelpers.ts`): il VaR si legge come soglia dell'istogramma.
- **Commenti con numeri di riga superati** (da A, minimo). `schemas/risk.py:1056` è citato in `RiskLevelsPanel.svelte:199`
  e in `risk-analysis.spec.ts:54` e `:2690`, ma oggi quella riga è `RiskVarCvarBin`: il validatore inteso è
  `validate_status_payload` (`:1675`). `schemas/risk.py:1045`, citato in `scenarioHelpers.ts:198`, è un decoratore: il
  campo inteso è `error: Optional[RiskError]` (`:1672`). Meglio citarli per nome.
- **`riskStore.test.ts` con l'ordine casuale** (di Risk, basso): con alcuni semi cadono 3 test, per il
  `vi.resetModules()` del blocco «first identity resolution». Il runner non mescola, quindi oggi non si vede.
- **Il controllo dei link della documentazione legge anche i commenti** (minimo): `_DOCS_PATH_LITERAL`
  (`scripts/docs_links.py:58`) trova un `docsPath: '…'` anche in un commento, e un percorso d'esempio diventa un link
  rotto. Nei commenti, niente sintassi `docsPath:`.

### Buchi nei test

- `AssetSetRiskPanel.svelte` non ha un test di componente. La contabilità dell'ammissibilità (`eligibilityQuestion`,
  `eligibilityAnsweredFor`, un fallimento che la chiude) la copre solo l'E2E `risk-lab`, al caso (g); `labL3Waits` ha i
  suoi test di unità.
- `L4Simulation.svelte` non ha un test di componente: i due stati d'incertezza sono provati solo come funzione pura
  (`levels/l4/driftUncertainty.test.ts`).
- Un E2E non clicca un punto di un grafico, perché la suite rifiuta le posizioni in pixel
  (`frontend/e2e/fixtures/charts.ts:56-59`): la selezione di una riga dal suo punto, benchmark compreso, è fissata solo
  in `AssetSetRiskReturnSection.test.ts`.
- Il trascinamento delle colonne di L1° passa anche con `table-layout: auto` a 1280 px: a proteggere è l'asserzione su
  `fixed` (`risk-lab.spec.ts:5033`; per L3°, `:5302`).

### Domande mai decise

Dalle schede della review del 24/09 ([`implementation_2/R5-tempo2-schede.md`](./implementation_2/R5-tempo2-schede.md),
«Esito delle schede»):

- **C4**: il tasso privo di rischio è sempre 0 su Dashboard e Broker (`levels/RiskLevelsPanel.svelte:77`). Asset Detail
  ha il suo campo. Se diventa non nullo, la retta dello scatter va fatta partire da `f · r_p`, con `r_p` il tasso del
  periodo, come lo Sharpe: oggi parte dal tasso annuo (`charts/scatterChartHelpers.ts:179-186`), e i due coincidono
  solo a 0;
- **C5**: la soglia del Sortino è sempre 0;
- **C8**: gli euro del max drawdown dicono «la stessa caduta, oggi»: va scritto così?
- il periodo non è scritto nell'intestazione dei livelli;
- una partenza tardiva non si vede: `baseline_inside_requested_range` e `short_history` non hanno lettori nel frontend;
- la copertura dello shock sotto 1 non segnala i tipi non configurati;
- `fresh_quote_coverage` è pubblicato e nessuno lo legge (debito 6 di [`implementation/STATO.md`](./implementation/STATO.md));
- **R12f**: la stessa famiglia ha lo stesso colore nella torta dell'allocazione e nel grafico storico? Non se i ranghi
  differiscono. Entrambi danno il colore per rango (D71), ma la torta ordina per il peso di oggi
  (`charts/allocationHierarchy.ts:214`) e lo storico per il peso medio del periodo
  (`dashboard/AllocationHistoryChart.svelte:350`).

Le domande della tabella dello shock e della paginazione di L3 stanno nelle loro voci, più sopra.

### Voci della famiglia nel backlog 38

Le ha scritte il coordinatore in [`../38_postReleaseBacklog/README.md`](../38_postReleaseBacklog/README.md); qui c'è
solo il rimando:

- **C-20**: la diagnostica dei plugin non elenca `RiskAnalyticRegistry`;
- **C-21**: il numero di percorsi della simulazione è fisso (è A4);
- **C-22**: con un IQR appena sopra zero, Freedman–Diaconis arriva a 198 barre;
- **C-23**: il laboratorio (`invalidateRisk()` o `markRiskStale()`, la doppia richiesta, la colonna tagliata,
  l'ipotesi del SIGTERM dopo i feed di JustETF);
- **C-24**: `BenchmarkSelect` può tornare a togliere dalla selezione gli id spariti;
- **N-4**: il SIGTERM durante il salvataggio della coverage (`backend/app/services/risk/quant/spawn_worker.py:280-282`);
- **N-5**: commenti superati in `risk-lab.spec.ts` e in `routes/(app)/assets/+page.svelte`.

### Rinvii già registrati in [`TODO_FUTURI.md`](../../../../TODO_FUTURI.md)

Tracking Error e Information Ratio · ottimizzazione di portafoglio · Monte Carlo avanzato (GJR-GARCH, livelli 4 e 5) ·
stimatori robusti di covarianza · rivalutare le misure di N contro riskfolio-lib · catalogo scenari dinamico, sostituti
nel replay e RQMC · separatore decimale · avanzamento della simulazione · i 110 `raise ValueError` del motore.

---

## 🧭 Ripartire da qui — guida per una chat nuova

Scritta il 10/10/2026, quando le sessioni Risk, A e F si chiudono. A chi riprende servono solo questa cartella, il
codice e la documentazione developer.

### Cosa leggere, in quest'ordine

1. Questo README, fino a qui: cosa resta aperto.
2. [`01-tesi-e-quattro-domande.md`](./01-tesi-e-quattro-domande.md), la direzione. Ogni livello risponde a una domanda:
   L1 «Quanto può fare male?», L2 «Sono diversificato come credo?», L3 «Sto venendo pagato per questo rischio?», L4
   «Cosa succede se…?». Il laboratorio di Asset Global ne riprende due su una selezione di asset, L1° e L3°, accanto
   alla correlazione e al replay.
3. [`04-decisioni-e-questioni-aperte.md`](./04-decisioni-e-questioni-aperte.md), da D370 in giù: le decisioni del giro
   UI. Le più vincolanti sono nella tabella qui sotto.
4. La pagina developer [`architecture.md`](../../../../mkdocs_src/docs/developer/backend/risk/architecture.md): il
   motore, il calendario dei mercati, l'ammissibilità, i limiti di dimensione (§ Budgets), gli errori e la loro
   traduzione (§ Warnings, Errors and Localization).
5. Le pagine utente `mkdocs_src/docs/user/dashboard/risk.en.md` e `mkdocs_src/docs/user/assets/correlation.en.md`:
   cosa vede l'utente.
6. I piani per area, con le decisioni del developer parola per parola:
   - Dashboard e Broker (A): [`A-dashboard-esecuzione.md`](./implementation_2/progress/A-dashboard-esecuzione.md), poi
     [`A-postmerge-esecuzione.md`](./implementation_2/progress/A-postmerge-esecuzione.md);
   - il laboratorio di Asset Global (F): [`F-L3-rischio-rendimento.md`](./implementation_2/progress/F-L3-rischio-rendimento.md),
     giri 1–15 con i contratti di D371, 13-A, F14 e D378, poi
     [`F-laboratorio-postmerge.md`](./implementation_2/progress/F-laboratorio-postmerge.md) e
     [`F-L1-confronto-perdite.md`](./implementation_2/progress/F-L1-confronto-perdite.md);
   - il motore, le primitive condivise, L4, i limiti della simulazione e l'istogramma (Risk):
     [`R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md).

### Dove sta il codice

| area | dove | cosa |
|---|---|---|
| motore | `backend/app/services/risk/` | `service.py` (il piano delle analitiche, l'ammissibilità, i budget), `metrics.py` (le formule: VaR e CVaR `:757`, istogramma `return_distribution_histogram` `:850`, tasso privo di rischio `:208`), `base.py` (la base dei plugin), `quant/` (QuantLib e riskfolio-lib nei processi `spawn`), `scenario_catalog/` (gli scenari in YAML) |
| serie | `backend/app/services/series_preparation.py` | allineamento al calendario comune; rendimenti dai soli prezzi (A5) |
| calendario | `backend/app/services/market_calendar.py` | festivi delle borse; QuantLib solo nel processo `spawn` |
| analitiche | `backend/app/services/risk_plugins/` | un modulo per analitica, ognuna con la sua `algorithm_version` (per esempio `historical_var.py:65`, 3.1.0) |
| contratti | `backend/app/schemas/risk.py`, `backend/app/api/v1/risk.py` | scope (`PortfolioRiskScope` `:657`), parametri, risultati, errori |
| Dashboard e Broker | `frontend/src/lib/components/risk/levels/` | `RiskLevelsPanel.svelte` (montato da `routes/(app)/dashboard/+page.svelte:1041` e `routes/(app)/brokers/[id]/+page.svelte:682`), `RiskLevelSection.svelte` (la cornice di ogni livello), `l1/`, `L2Diversification.svelte`, `L3RiskAdjusted.svelte`, `L3Benchmark.svelte`, `L4WhatIf.svelte` e `l4/`, `levelHelpers.ts`, `errorDisplayCode.ts` |
| laboratorio di Asset Global | `frontend/src/lib/components/risk/` | `AssetSetRiskPanel.svelte` (la scheda Correlazione, `routes/(app)/assets/+page.svelte:52`), `AssetSetComparisonLevels.svelte` (L1° e L3°), `RiskReturnLevel.svelte` e `riskReturnLevel.ts`, `AssetSetCorrelationSection.svelte`, `AssetSetReplaySection.svelte`, `LabAssetPicker.svelte`, `assetSetSelection.ts`, `eligibility.ts` |
| condivisi | `frontend/src/lib/components/risk/`, `frontend/src/lib/components/charts/` | `BenchmarkSelect.svelte`, `AssetChip.svelte`, `CorrelationHeatmap.svelte`, `RiskControllerHost.svelte`; `ScatterChart.svelte` e `scatterChartHelpers.ts` |
| Asset Detail | `frontend/src/lib/components/risk/AssetRiskScenariosView.svelte` | monta il pannello legacy `RiskAnalysisPanel.svelte`, in beta (A2) |
| stato | `frontend/src/lib/stores/risk/` | `riskStore.svelte.ts` (la cache, `RISK_DISCARD_ATTEMPTS` `:95`, i verdetti di ammissibilità), `riskPanelController.svelte.ts`, `riskBenchmarkStore.svelte.ts` |
| documentazione | `mkdocs_src/docs/` | utente: `user/dashboard/risk`, `user/assets/correlation`; teoria: `financial-theory/technical-analysis/risk-metrics/` (22 pagine, in quattro lingue); developer: `developer/backend/risk/architecture.md` |
| test | `backend/test_scripts/test_services/test_risk_*.py`, `backend/test_scripts/test_schemas/test_risk_schemas.py`, `frontend/e2e/portfolio/risk*.spec.ts` e `risk-mocks.ts` | i test di unità e di componente del frontend stanno accanto ai sorgenti |

### Come si prova

Da una worktree, sempre col venv condiviso e con la propria corsia (mai `./dev.py` nudo, mai un venv della worktree):

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port <PORTA> --data-dir <CARTELLA ASSOLUTA> <categoria> <azione>
```

| categoria | azioni | cosa |
|---|---|---|
| `services` | `risk-oracle`, `risk-all`, `risk-asset-set`, `risk-optimization`, `risk-simulation`, `risk-workers` | backend; l'oracolo confronta le formule con riskfolio-lib |
| `schemas` | `risk` | i contratti, compreso il catalogo `risk.errors` |
| `api` | `risk` | gli endpoint; prima, `test db populate --force` (vedi le trappole) |
| `front-portfolio` | `risk-unit`, `risk-request-unit`, `risk-benchmark-unit`, `risk-controller-unit`, `risk-levels-unit`, `risk-levels-component`, `risk-frame-component` | Vitest |
| `front-portfolio` | `risk`, `risk-lab`, `risk-asset-detail`, `risk-benchmark-shared` | E2E Playwright: Dashboard e Broker, laboratorio, Asset Detail, il selettore del benchmark |

Poi `front check` e `i18n audit`; per la documentazione, `mkdocs build` e `mkdocs check-links`. I test nuovi o da
riparare li scrive l'agente `test-author`, che li registra nel catalogo del runner.

### Decisioni che vincolano il lavoro

| decisione | in breve |
|---|---|
| la tesi, [`01`](./01-tesi-e-quattro-domande.md) | quattro domande, una per livello: uno strumento sta dove risponde a una domanda |
| D8, D47 | Asset Detail si riapre per ultimo, ereditando la direzione già decisa (A2) |
| D46 | superata nei fatti: la famiglia è entrata in `dev_release2` a treni |
| D54 | le colonne di rischio di Asset Global, nascoste per default (B2) |
| D58, D59 | la fetta per asset, con i pesi rinormalizzati al 100% della fetta (B3) |
| D71 | i colori dell'allocazione per rango (R12f) |
| D87, D209, D277, D287 | le cifre di M2 sono variazioni relative, per livello di confidenza: mai una cifra sola; il VaR si sposta solo sul confine della coda |
| D144 | `min_coverage` non governa nulla (difetto aperto) |
| D151, D376 | un valore neutro è un'affermazione: gli esclusi del replay non sono impatti, e stanno sopra le barre come badge |
| D370, D371, D378 | il benchmark condiviso: anche un asset posseduto; nel laboratorio un asset selezionato può fare da riferimento, e il riferimento non è mai un soggetto; un benchmark che il periodo non può misurare resta scelto ma non si prova |
| D372, D376, D377 | il replay e L4: il periodo comune in un clic, niente sostituti in L4; un selettore che aggiunge gli strumenti; alla prima visita nessuno strumento aperto; la × toglie lo strumento con la sua risposta |
| D373 | il banner della qualità dei dati, con «Sincronizza», anche nel laboratorio; Asset Detail resta com'è |
| D374 | una risposta scartata si richiede fino a 3 volte in tutto (`RISK_DISCARD_ATTEMPTS`) |
| D375 | lo storico dell'allocazione per tipo: un'area per famiglia; i sottotipi solo nel tooltip |
| D379 | una simulazione troppo grande dice «troppo grande», con la cura che funziona davvero |
| D380, D381 | l'istogramma (Sturges con IQR 0; la larghezza Freedman–Diaconis calcolata, non costruita); mai «−0.0%» né «−0,00 €» |
| D382 | la pausa fino a dopo la 1.2 |
| D383 | il riquadro degli avvisi di livello, uguale dappertutto (Dashboard, Broker, laboratorio) |
| D384 | il preset del broker nel laboratorio richiede una volta sola |
| CHANGELOG 1.2.0 | nel laboratorio solo percentuali, e nessun giudizio sulla selezione nel suo insieme; ciò che non si misura mostra un trattino che dice perché, mai uno zero |

### Trappole note

**Numeri e formule**

- VaR: la coda nominale `(1−c)·T` si riaggancia all'intero (`risk/metrics.py:804`). `1.0 − 0.95` non è 0,05: senza
  aggancio, a T = 740 torna l'errore di una posizione che M2 ha tolto. Il CVaR somma con `math.fsum` (`:817`): passare a
  `ndarray.sum` sposta cifre pubblicate. Il pavimento a 0 delle perdite regge il contratto (`RiskVarCvarOutput`,
  `ge=0`).
- Istogramma: la larghezza Freedman–Diaconis si calcola prima di chiedere la griglia a NumPy, e con IQR = 0 si passa a
  Sturges, sotto il tetto di 200 barre (`_MAX_HISTOGRAM_BINS`, `risk/metrics.py:22`). `historical_var` è alla 3.1.0
  (`risk_plugins/historical_var.py:65`), fissata da `test_risk_analytics.py:2507`: una griglia diversa cambia la
  versione.
- Il tasso privo di rischio annuo si converte alla frequenza della serie: `daily_risk_free_rate(annual_rate,
  periods_per_year)` ha il secondo parametro obbligatorio apposta (`risk/metrics.py:208`). Lo Sharpe è la media
  aritmetica dell'eccesso sulla deviazione campionaria, per √f.
- Le cifre: «0.0%» sugli assi, precisione adattiva nelle cifre («−0.04%»), mai «−0.0%»; mai «−0,00 €» sotto una perdita
  zero. La regola si scrive sul numero, non sul testo, perché la privacy maschera gli importi (D380, D381).
- Il VaR a un mese: l'orizzonte conta giorni di calendario (30 nel frontend), e le osservazioni sono
  `round(h·f/365)` (`value-at-risk.en.md`), su finestre sovrapposte.

**Calendario e dati**

- Una riga di sabato, di domenica o di un festivo comune, con la chiusura uguale a quella prima, è un riporto e non una
  quotazione. La prima riga è sempre una quotazione, e lo sono anche un giorno feriale piatto e le mosse delle cripto
  nel fine settimana (`market_calendar.py`; `data-quality.en.md`, § Stored Carries). Il processo web non importa mai
  QuantLib: la tabella dei festivi si costruisce in un processo `spawn`.
- L'ammissibilità è necessaria, non sufficiente: conta le quotazioni di ogni asset, non il calendario comune, e guarda
  il cambio solo agli estremi del periodo (`architecture.md`, § Analysis Eligibility).
- Gli indicatori tecnici contano le sedute (una SMA 200 copre 200 sedute); la copertura resta di calendario, e
  `calendar_rolling_return` e i 4 segnali di rischio rolling restano sui giorni di calendario
  (`mkdocs_src/docs/developer/architecture/patterns/signal_plugin_guide.md`). Le bande impilate si colmano con
  `bridgeBetweenPoints` (`charts/lineChartHelpers.ts`), non con `connectNulls`, che ECharts riempie fino all'asse.
  Effetti collaterali annotati allora e mai rivisti col developer: l'istogramma del MACD lascia vuoti i fine
  settimana, il `pointCount` della pagina FX scende a circa 5/7, e i plugin che chiedono una serie contigua possono non
  essere disponibili vicino all'inizio della storia.

**Contratti del backend**

- Ogni modello di `schemas/risk.py` eredita `extra="forbid"`: un parametro nuovo passa dallo schema e da
  `./dev.py api sync`. `api sync` esce 0 anche se il client generato non compila, e i suoi file sono ignorati da git:
  la prova è `front check`.
- Le chiavi i18n degli avvisi del backend si scrivono letterali (`message_i18n_key="risk.warnings.…"`), mai
  costruite: l'audit non le troverebbe.
- Il catalogo `risk.errors` è fissato da `test_risk_error_catalogues_agree_across_languages`
  (`test_risk_schemas.py`), che legge per nome `RESOURCE_LIMIT_DISPLAY_CODES` (`levels/errorDisplayCode.ts`): ogni
  modifica a `risk.errors` passa anche da `schemas risk`.
- I limiti di dimensione si controllano in un ordine fisso, e la richiesta si ferma al primo superato (D379; la tabella
  in `architecture.md`, § Budgets). L'ottimizzazione porta in `resource_limit` solo `actual` e `limit`.
- `test_risk_service.py` costruisce `RiskService(db=object())` in 7 punti: una chiamata nuova al database nel servizio
  chiede un monkeypatch lì.

**Frontend**

- Una risposta scartata si richiede al massimo 3 volte in tutto, senza attesa, e un errore lanciato non si riprova
  (D374). Il `loadBase(force)` pubblico resta un involucro di `loadBaseAttempt`. Il preset del broker nel laboratorio
  richiede una volta sola (D384).
- `L3Benchmark` chiede la comparazione solo nello stato `set`, una volta per chiave `${baseEpoch}|${selected}`: il clic
  non chiede da sé, chiede l'effetto; se lo stato lascia `set`, la comparazione si azzera.
- Laboratorio, l'attesa dei verdetti (da F):
  - `eligibilityQuestion` è `null` finché non arriva l'elenco della pagina, apposta: la selezione si ripristina da
    `localStorage` prima dell'elenco, e senza verdetti tutto è analizzabile (`analysedIds`, `AssetSetRiskPanel.svelte:357`),
    quindi i livelli si monterebbero subito. «Niente da chiedere» non vale mai come risposta;
  - l'attesa funziona montando: il controller di L3° nasce in `RiskControllerHost` sotto `{#if !benchmarkPending}`
    (`AssetSetComparisonLevels.svelte:243`), perché `createRiskPanelController`
    (`stores/risk/riskPanelController.svelte.ts:296`) non ha un interruttore di attesa. Estendere l'attesa a ogni
    sezione le farebbe rimontare tutte a ogni cambio di periodo, con un lampo di caricamento; l'alternativa è
    un'opzione di attesa nel controller;
  - la domanda copre tutto il catalogo, a blocchi di 500 (`eligibility.ts:47`), e L3° la aspetta: la sua latenza
    cresce col catalogo;
  - `labL3Waits` (`assetSetSelection.ts:245`) aspetta per `set` e per `blocked` finché la domanda non è chiusa, perché
    un `blocked` del periodo prima non deve decidere quello nuovo.
- Le etichette degli avvisi di L4 vanno per gradino, mai per istanza: replay e shock sono la stessa analitica
  `stress`, con la stessa istanza (`L4_STEP_LABELS`, `RiskLevelsPanel.svelte:229`).
- Il replay non chiama `ensureAssetsLoaded`: i test di F non simulano lo store degli asset, e `chipAsset()` legge solo
  la cache. Il preset MAX di `DateRangePicker` emette la sentinella `('min','max')`, che risolve solo il filtro
  globale: per questo il replay passa `excludePresets={['MAX']}` (`L4Replay.svelte:231`).
- Le barre di Income (`dashboard/growthLadderBuckets.ts`, di A): `todayIso()` è la data locale, la memoria della scala
  dei periodi è chiavata sulla data di oggi, i periodi offerti dipendono dalla larghezza del grafico (misurata da 279 a
  734 px), e le chiavi i18n del grafico si chiamano con `$_()` letterali, perché un test di contratto lo controlla.

**File e testid condivisi**

- `components/risk/eligibility.ts` serve `BenchmarkSelect.svelte` (`dayFormatter`, `describeEligibility`) e
  `stores/risk/riskStore.svelte.ts` (`eligibilityBatches`, `mergeEligibilityAnswers`, `:20`): cambiarne firma o
  comportamento tocca entrambi.
- I file del selettore in `components/ui/select/` (`AssetPickerPanel.svelte`, `SelectPopover.svelte`,
  `CheckMenu.svelte`, `assetPicker.ts`) sono condivisi dal primo stadio del selettore del benchmark.
- I testid del replay (`risk-replay`, `-run`, `-preset`, `-period`, `-total`, `-tornado`, `-tornado-row`,
  `-excluded…`, `-suggested…`, `-coverage`, `-nothing`) li usano `AssetSetReplaySection.test.ts`,
  `risk-analysis.spec.ts` e `risk-lab.spec.ts`; i testid della cornice `RiskLevelSection.svelte` (`{testId}-alert`,
  `-body`, `-title`, `-toggle`, …) li usa `risk-lab.spec.ts`. Rinominarli rompe quelle suite senza toccarle.
- Ogni suite E2E di rischio simula a modo suo `POST /risk/eligibility`: `risk-analysis.spec.ts` con
  `RiskMockOptions.eligibilityVerdicts` (`:189-212`, di default tutto `eligible`, validato con
  `schemas.RiskEligibilityResponse.parse`), `risk-lab.spec.ts` con le sue route (`:1308`, `:1438`). Un test senza
  quella simulazione vede il benchmark non posseduto `blocked` per `too_few_quotes`, e aspetta una riga di L3 che non
  arriva.
- Se il lavoro torna a dividersi fra più sessioni: un solo scrittore per file, e un componente condiviso ha un solo
  proprietario, qualunque pagina lo monti ([`implementation_2/_comune.md`](./implementation_2/_comune.md)).

**Test e corsie**

- Una corsia, cioè una porta e una cartella dati assoluta, per worktree; un comando alla volta per corsia; mai
  `--force` sul server di test.
- Ogni selettore `services risk-*` svuota il database della corsia: prima di `api risk` serve `test db populate --force`
  (`_comune.md`, Ⓖ).
- Misurare i dati e guardare l'app nella stessa corsia non vanno insieme: navigare riscrive il `close` di oggi (Ⓓ).
  Nessun numero che integri sulla finestra va in un commento, in una didascalia o in un'asserzione: i dati di prova
  sono generati con un seme per asset e data, quindi un prezzo a una data è stabile, ma la finestra scorre, e un beta o
  una correlazione cambiano ogni giorno (Ⓕ).
- Gli E2E di rischio trattengono il polling dei prezzi dal vivo (`holdLivePricePoll`, in tutte e quattro le suite):
  senza, toccano i provider veri.
- Durante un E2E non si toccano i file del prodotto: il server di test ricostruisce il frontend dai sorgenti, e un
  mutante entra nella corsa.
- Vitest si lancia da `frontend/`: un test legge `src/app.css` relativo alla cartella di lavoro. Prima della prima
  suite che avvia il backend serve `front build --debug`; l'avvio del backend (120 s) può scadere con la macchina
  carica, e si rilancia.
- `svelte-check` segnala solo la prima prop mancante di ogni letterale. In Playwright `isVisible({timeout})` non
  aspetta ([devWiki](../../../../LibreFolio_devWiki/wiki/problems/compactcashcell-decimal-separator-feedback-loop.md)).
- riskfolio-lib costa secondi all'import a freddo: i test dell'oracolo stanno nel loro selettore, `risk-oracle`, e i
  test veloci importano solo `math` ([`07-piano-esecutivo.md`](./07-piano-esecutivo.md), §5). Alcune funzioni di
  riskfolio hanno lo stesso nome per grandezze diverse, come `MDD_Abs`, che somma i rendimenti invece di comporli
  ([`06-matematica-librerie-e-reimplementazioni.md`](./06-matematica-librerie-e-reimplementazioni.md), §3.1).
- Il repo è pubblico: nei file niente cifre reali. La review sui dati veri segue la procedura del piano di A (passo 14,
  «Accordi»): una copia privata dello snapshot (permessi `700`, `umask 077`), il server solo su `127.0.0.1`, il log
  dentro la copia, e alla fine la cancellazione con la prova. L'impronta dello snapshot la tiene il coordinatore, mai
  nei file.

---

## Perché questa cartella è stata svuotata

La prima campagna Risk (Luglio 2026) ha prodotto un backend completo e auditato e
**21 documenti di piano**, ma il frontend si è fermato al **26% della catena G6**
(work item 7 di 23). Il rilascio è avvenuto comunque, coprendo le viste incomplete con
un banner beta.

L'analisi del 16 Settembre 2026 ha stabilito che il problema non è la qualità del
backend né la resa grafica, ma **l'assenza di una domanda guida**: i piani rispondevano
a *«quali strumenti di rischio esistono?»* invece che a *«quale decisione deve prendere
l'utente?»*. Senza quella domanda ogni metrica pesa uguale, le implementi tutte, la UI
diventa una lista e l'utente non sa dove guardare.

Il materiale precedente **non è stato cancellato**: è in
[`_archive-backendFirst-G0G6/`](./_archive-backendFirst-G0G6/) e resta la fonte
autoritativa per il **contratto matematico**, le **evidenze di benchmark** e le
**decisioni di architettura backend**, che restano tutte valide.

Ciò che è superato è la **pianificazione frontend** (catena G6) e la **gerarchia di
priorità fra le metriche**.

---

## Ordine di lettura

| # | Documento | Contenuto |
|---|---|---|
| 0 | [`00-analisi-stato-attuale.md`](./00-analisi-stato-attuale.md) | Inventario **verificato sul codice** di cosa esiste davvero, dove, e quanto del piano è stato eseguito. |
| 1 | [`01-tesi-e-quattro-domande.md`](./01-tesi-e-quattro-domande.md) | **La direzione.** Tesi guida, i quattro livelli di domanda, la regola dei pesi. Fonte di ogni decisione successiva. |
| 2 | [`02-verdetti-per-strumento.md`](./02-verdetti-per-strumento.md) | Per ogni strumento: cosa fa, a che domanda risponde, verdetto e destinazione. |
| 3 | [`03-mappa-livelli-pagine.md`](./03-mappa-livelli-pagine.md) | Mappa livelli × pagine, conseguenze architetturali, scomposizione del monolite. |
| 4 | [`04-decisioni-e-questioni-aperte.md`](./04-decisioni-e-questioni-aperte.md) | Registro delle decisioni prese, dei rinvii, e di ciò che resta aperto. **Documento vivo.** |
| 5 | [`05-grammatica-visiva-e-rappresentazioni.md`](./05-grammatica-visiva-e-rappresentazioni.md) | Diagnosi estetica, contratto di primitive, anatomia della card, sei rappresentazioni, dossier heatmap, layout per zona. |
| 6 | [`06-matematica-librerie-e-reimplementazioni.md`](./06-matematica-librerie-e-reimplementazioni.md) | Le due sorgenti matematiche del progetto, confronto a tre vie con NumPy e Riskfolio, distorsione del CVaR, costo dei segnali rolling, setaccio delle 42 funzioni Riskfolio, piano di migrazione M1-M6. |
| 7 | [`07-piano-esecutivo.md`](./07-piano-esecutivo.md) | **L'ordine.** Dodici flussi paralleli, cinque dipendenze, tre cancelli, la taglia in superficie misurata, l'indirizzo dell'oracolo M4, la banda di porte e la voce di CHANGELOG. Non riassume i precedenti: rimanda. |
| 8 | [`implementation/`](./implementation/) | **I mandati.** Undici piani di lavoro assegnabili a sotto-agenti, uno per flusso, con lane, proprietà dei file e contratti. Il [`README`](./implementation/README.md) della cartella è la mappa di coordinamento; [`kickoff/`](./implementation/kickoff/) i prompt di avvio, [`contracts/`](./implementation/contracts/) i contratti K1-K8 e [`progress/`](./implementation/progress/) i piani vivi. |
| 9 | [`implementation_2/`](./implementation_2/) | **Il secondo giro e il giro UI.** Il [`REGISTRO`](./implementation_2/REGISTRO.md) dei mandati, i piani S1–S5, i piani di A e di F in [`progress/`](./implementation_2/progress/), e il journal di Risk, [`R5-post-merge-e-review.md`](./implementation_2/R5-post-merge-e-review.md), che arriva fino alla 1.2. |

---

## Stato dell'avanzamento

| Blocco | Stato |
|---|---|
| Analisi dello stato attuale | ✅ 16 Set 2026 |
| Tesi e quattro domande | ✅ 16 Set 2026 |
| Verdetti per strumento | ✅ 16 Set 2026 |
| Mappa livelli × pagine | ✅ 16 Set 2026 |
| **UI/UX per zona e scelta dei grafici** | ✅ 16 Set 2026 |
| **Matematica, librerie e reimplementazioni** | ✅ 16 Set 2026 |
| **Piano esecutivo** | ✅ 17 Set 2026 |
| **Mandati di implementazione** | ✅ 17 Set 2026 |
| Esecuzione — primo giro, [`implementation/`](./implementation/) | ✅ 18 Set 2026 (J mai creato: lo sostituisce il secondo giro) |
| Esecuzione — secondo giro e giro UI, [`implementation_2/`](./implementation_2/) | ✅ 18 Set – 08 Ott 2026, tutto in `dev_release2` |
| Rilascio | ✅ 1.2.0: fuori dalla beta, salvo la simulazione e la scheda di Asset Detail |
| Seguito | ⏸️ in pausa fino a dopo la 1.2 (D382) |
| Consegne alla prossima release | ✅ 10 Ott 2026: le voci aperte di Risk, A e F raccolte qui, con la guida per ripartire |

---

## Vincoli di scopo già fissati

- **Asset Detail è parcheggiato in beta.** Non rientra in questo giro: si riapre a fine
  catena (D47), quando i quattro livelli e la grammatica visiva saranno in piedi, così
  eredita una direzione già decisa. La discussione si concentra su **Dashboard**,
  **Broker Detail** e **Asset Global**.
- *(Superato nei fatti: la famiglia è entrata in `dev_release2` a treni, e la 1.2.0 toglie il banner superficie per
  superficie.)* **Si rilascia solo a catena completa** (D46). Il lavoro vive in un worktree separato
  e non tocca `dev_release2` finché non è pronto; il banner beta si toglie a quel punto,
  in un colpo solo.
- **I segnali rolling restano dove sono** (Overview di Asset Detail). Non vengono
  spostati né duplicati.
- *(Superato dal piano esecutivo del 17/09 e dai giri seguenti: il backend è stato riaperto dai mandati A, migrazione
  matematica, H, Monte Carlo, e N, acquisizioni, poi dai limiti della simulazione, D379, e dall'istogramma, D380 e
  D381.)* **Il backend non viene riaperto** su: contratto matematico, QuantLib MC/QMC, obbligo
  di processo `spawn`, serie canoniche, metadata di qualità del dato.
- **La catena G6 non viene ripresa.** 23 item a catena singola con gate umani bloccanti
  si è dimostrato un modello fragile: un solo stop congela tutto il resto.
- *(Superato come l'altro punto sul backend; le due eccezioni sono diventate i mandati B e C.)* **Il backend non viene
  riaperto**, con due eccezioni decise il 17 Set: il filtro per
  asset su `PortfolioRiskScope` (D58), che oggi sa affettare solo per broker, e
  l'estensione di `AssetType` con i sottotipi (D52). Entrambe servono il confronto con
  il riferimento giusto, che è il perno di L3.

---

## Riferimenti

- Archivio prima campagna: [`_archive-backendFirst-G0G6/`](./_archive-backendFirst-G0G6/)
- Rinvii registrati: [`../../../../TODO_FUTURI.md`](../../../../TODO_FUTURI.md)
- Backlog dopo la 1.2: [`../38_postReleaseBacklog/README.md`](../38_postReleaseBacklog/README.md)
