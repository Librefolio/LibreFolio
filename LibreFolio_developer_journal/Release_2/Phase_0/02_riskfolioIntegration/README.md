# Fase 0.1 — Integrazione Risk Analysis · Studio e implementazione

Questa cartella contiene lo studio di alto livello e il **piano applicativo**
della Fase 0.1 (Monte Carlo & Risk Metrics Engine). Lo scopo dello studio è
rispondere a una domanda architetturale chiave: *dove* mettere l'analisi del
rischio in LibreFolio e *quanto* di essa può essere reso modulare (stile
"segnali") invece di richiedere una UI ad-hoc ogni volta. Lo studio è **approvato**;
il piano applicativo (documento 4) formalizza gli step P0–P13; il master
implementativo (documento 6) li traduce in sei sub-plan backend-first.

## Documenti

| # | File | Contenuto |
|---|------|-----------|
| 0 | [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md) | **Contratto matematico/semantico fondativo.** Quali serie consumare (TWRR per portafoglio, close per asset), **annualizzazione osservata dal campione** (§2.1), calendario congiunto + ultimo prezzo disponibile (§2.2), modalità `historical` vs `current_composition`, `RiskResultMetadata` + qualità dati, regole di allineamento date per correlazione, schede per-metrica (MCTR/CCTR/PCTR, VaR/CVaR, Monte Carlo, stress), gap `AssetReturnSeries`, async. **Leggere per primo.** |
| 1 | [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md) | Analisi architetturale. Tassonomia degli output di rischio, la proposta `RiskAnalytic` (distinta da `SignalPlugin`) + "widget primitives", matrice di posizionamento UI per pagina, cosa implementare / rimandare / evitare, scelta libreria e async safety, roadmap R0–R9. |
| 2 | [`brainstorm-phase01RiskUiConcepts.md`](./brainstorm-phase01RiskUiConcepts.md) | Brainstorming visivo. **9 concept UI** (A–I) con **ASCII art** e, per ciascuno, "cosa fa notare all'utente" + costo/valore. Information architecture della Risk tab + banner qualità dati trasversale. |
| 3 | [`review-risk-analysis-feedback.md`](./review-risk-analysis-feedback.md) | **Revisione critica punto-per-punto.** Le 18 osservazioni valutate (ACCETTO / ACCETTO CON MODIFICHE / RESPINGO / RIMANDO) con evidenza dal codice, razionale finanziario/tecnico, conseguenze architetturali e modifiche apportate ai documenti. |
| 4 | [`plan-phase01RiskAnalysisApplication.prompt.md`](./plan-phase01RiskAnalysisApplication.prompt.md) | **Piano applicativo incrementale (P0–P13).** Decisioni consolidate, gate librerie, step verificabili, test+benchmark e tracciabilità. Aggiornato con gli esiti QuantLib/Riskfolio reali. |
| 5 | [`_RECAP-and-implementation-reading-guide.md`](./_RECAP-and-implementation-reading-guide.md) | **Punto d'ingresso / ripresa.** Mappa dei documenti, decisioni cardine consolidate, **prompt di ripresa** copiabile e **guida di lettura** per pianificare l'implementazione in fasi (A–F, raggruppamento di P0–P13, doppio percorso funzionale/librerie). |
| 6 | [`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md) | **Master implementativo backend-first.** Coordina sei sub-plan, gate G0–G6 e tracking task-per-task. G5 è stato corretto con process isolation obbligatorio. |
| 7 | [`spike-phase01QuantLibraries.md`](./spike-phase01QuantLibraries.md) | **Evidenza P0.** QuantLib 1.43 + Riskfolio-Lib 7.0.1 su host/Linux arm64/amd64, solver, lock e costo container. |
| 8 | [`spike-phase01SimulationAdapters.md`](./spike-phase01SimulationAdapters.md) | **Evidenza P11.** Oracle analitici GBM, gate MC a standard error, convergenza QMC e equivalenza direct/spawn. |
| 9 | [`benchmark-phase01SimulationScale.md`](./benchmark-phase01SimulationScale.md) | **Evidenza P12.** Cold/warm, cache, RSS, concorrenza e timeout/recycle dei pool production. |
| 10 | [`report-phase01RiskAnalysisCurrentStateAndHandoff.md`](./report-phase01RiskAnalysisCurrentStateAndHandoff.md) | **Report autosufficiente per handoff.** Richieste vs stato reale, falsa pista NumPy/thread, correzione QuantLib/Riskfolio, lavoro completato/rimandato/eliminato, problemi inattesi e decisioni ancora aperte. |
| 11 | [`workItems/`](./workItems/README.md) | **Snapshot dei 37 work item operativi.** Scomposizione P0-P13 per gate G0-G6/GF, stato, dipendenze e descrizioni originali del tracker interno. |

## TL;DR delle conclusioni (revisionate)

1. **Consumare, non reimplementare.** Il motore produce già le serie giuste:
   `PortfolioHistoryPoint.twrr` è **neutro rispetto ai flussi di cassa** e già in
   valuta target. Le metriche di rischio di portafoglio DEVONO partire dal **TWRR**,
   mai da delta di `nav_value`. (contratto §0–§1)
2. **Annualizzazione OSSERVATA, non un fattore fisso.** Il calcolo resta
   giornaliero, ma il fattore è `A = oss.incluse × 365 / giorni-di-calendario`
   (né 252 né 365 costante): per equity tende naturalmente a ~252, per crypto 24/7
   a ~365 — valori che **emergono dal campione**. La volatilità si annualizza con
   √A. (contratto §2.1)
3. **Il rischio si scompone in 6 archetipi di output** (scalare, serie, distribuzione,
   cono, matrice, scatter). Modularizzare i **widget/renderer**, non le linee.
4. **Due binari backend (review-4).** Le metriche **rolling asset-scoped** (drawdown,
   rolling vol/return/Sharpe, e il **beta** con una serie secondaria dichiarata)
   entrano nel **`SignalPlugin`** esistente con **piccole estensioni** (valore
   `SignalCategory.RISK`, param risk-free, slot serie-secondaria per il beta). Lo
   scope **portafoglio/multi-asset** (correlazione, PCTR, VaR/CVaR, stress, MC,
   frontiera) passa da un contratto separato **`RiskAnalytic`**. Renderer segnali
   riusato in entrambi i casi; preparazione serie in **un'unica utility** del service layer.
5. **Due modalità** distinte: `historical` (pesi reali nel tempo, usa il TWRR già
   esistente — **disponibile subito**) vs `current_composition` (pesi attuali su
   rendimenti passati — richiede `AssetReturnSeries`).
6. **Gap critico = `AssetReturnSeries`:** non esiste una serie canonica di rendimenti
   per-asset convertiti in valuta. Correlazione, beta e risk-contribution dipendono da
   essa → è il **collo di bottiglia** (roadmap R1), da costruire come *estensione* del
   layer prezzi/portafoglio riusando l'FX, non come pipeline parallela.
7. **Provenienza e qualità:** `RiskResultMetadata` deve **estendere** i pattern già
   presenti (`SignalStatus`, `SignalWarningCode`, `DataQualityReport`), non inventarne.
8. **Priorità rivista:** risk contribution (PCTR) e stress test **precedono** il Monte
   Carlo, che scende per il rischio di falsa precisione (review §9, §13).
9. **Gate librerie corretto.** QuantLib 1.43 e Riskfolio-Lib 7.0.1 sono adottate
   con NumPy 2.5.1; `vectorbt`/`numba` assenti. Probe host/Linux arm64/amd64 e
   immagine finale arm64 sono verdi.
10. **Esecuzione G0-G4 completata.** Serie canoniche e metadata sono condivisi;
    cinque rolling risk sono nel catalogo Asset; sei analytics deterministici
    multi-asset sono disponibili via service/API bulk con test matematici e query
    reale sul DB popolato.
11. **G5 corretto.** P11 usa QuantLib MC/QMC in worker `spawn`; P12 usa pool
    simulation/optimization separati e persistenti; P13 espone
    `portfolio_optimization` Riskfolio nei tre scope. RQMC e l'adapter
    NumPy/SciPy production sono rimossi. G6 non viene ripreso in questo round.

> **Nota:** i documenti 0–4 nascono come studio; il master e le evidenze successive
> registrano ora anche l'implementazione. Nessuna migrazione DB è stata necessaria.

### Precisazioni della 2ª revisione (review-2)

10. **Calcolo sempre giornaliero (1ª impl.).** La frequenza non è configurabile:
    tutte le metriche consumano rendimenti **giornalieri**. `frequency`/`resample_rule`/
    fattore configurabile **rimossi** dalla prima implementazione. L'aggregazione del
    frontend è **solo visuale** (downsampling per pixel) e non tocca campione, valori,
    `n_observations` né semantica rolling. (contratto §2.0/§2.2)
11. **Estrazione rendimenti dalla TWRR:** `r_t = (1+TWRR_t)/(1+TWRR_{t-1})−1`,
    `W_t = 1+TWRR_t`; verificato = `hpr_t` del motore. Derivare dall'HPR di
    sotto-periodo, non differenziando cumulative arrotondate. (contratto §1.3)
12. **`AssetValuationSeries` → `AssetReturnSeries`:** si converte il **prezzo** alla
    data, *poi* si calcola il rendimento (mai il contrario). Due concetti separati:
    valorizzazione convertita (con provenance FX) vs rendimenti derivati. (contratto §7.1)
13. **`current_composition` = `current_buy_and_hold`** nella 1ª impl. (no ribilanciamento
    sintetico/costi/tasse). Politica **obbligatoria**, non generica. (contratto §3.1)
14. **Risk contribution = grafico a barre divergente, non treemap** (il PCTR può essere
    negativo). Riusa la primitive di barra esistente (`PerformanceChart`/`buildBarSeries`).
    (contratto §6.7, brainstorm Concept F)
15. **VaR/CVaR come magnitudini positive di perdita:** `CVaR ≥ VaR ≥ 0`; il segno è
    presentazione UI, non dominio. (contratto §6.8)
16. **Stress test: tre famiglie con dipendenze distinte.** Hypothetical shock primo
    (deterministico); factor shock richiede un factor-exposure model **assente** →
    evoluzione successiva. (contratto §6.10)
17. **Confronto risk-free vs asset reale:** baseline sintetica deterministica (varianza
    **nulla**, `rf_daily=(1+rf)^(1/365)−1`) vs benchmark reale (active return, TE, IR,
    beta). Contratti backend distinti `RiskFreeReference`/`ComparisonBenchmark`; nessun
    asset reale è "risk-free". (contratto §6.11, brainstorm Concept I)
18. **`return_basis` sempre propagato** (`price_only|twrr|total_return`); i confronti
    price-only sono **parziali** finché mancano serie total-return. (contratto §1.2)
19. **Frontiera efficiente: wording condizionato** («massimo Sharpe **stimato nel
    campione**»), mai assertivo. (brainstorm Concept G)

### Precisazioni della 3ª revisione (review-3)

20. **Calendario congiunto + ultimo prezzo disponibile.** Giorno **incluso** se ≥1
    asset ha una nuova quotazione (gli altri valorizzati con l'ultimo prezzo, rendimento
    derivato → può essere zero); giorno **escluso** solo se **nessuno** ha nuova
    quotazione; asset senza alcun prezzo → escluso (risultato parziale). Mai ffill dei
    rendimenti: si mantiene il **prezzo**, poi si deriva. Supera la formulazione
    review-2 §2.2. (contratto §2.2)
21. **Annualizzazione osservata** `A = oss.incluse × 365 / giorni-calendario`, inclusa
    nei metadati e **uguale per tutte le metriche** sullo stesso calendario congiunto.
    (contratto §2.1)
22. **Qualità dati = warning, non euristiche.** `data_quality_status`
    (`ok|carried_forward|partial`) + `assets_with_missing_prices` /
    `carried_forward_price_points`; banner UI riusabile con dettaglio asset e pulsante
    **"Sincronizza prezzi"** che **riusa il refresh esistente** — il Risk Engine non
    scarica prezzi né corregge il DB. (contratto §2.3, analisi §6, brainstorm §qualità dati)
23. **Stress: nessuna dipendenza `correlazione → factor shock`.** Hypothetical shock
    prima; historical replay dipende da `AssetReturnSeries`+pesi; factor shock richiede
    un factor exposure model (assente). Diagramma dipendenze del contratto corretto.
    (contratto §6.10/§10)
24. **Tassonomia widget:** le **barre divergenti** sono una **primitive aggiuntiva**
    (`DB`) oltre ai 6 archetipi S/T/D/C/M/F, da non confondere con il *Concept B*
    (Monte Carlo); concept UI totali = **9** (A–I). (analisi §3)

### Precisazioni della 4ª revisione (review-4) — cleanup, riuso, piccole estensioni

25. **Pivot plugin (verificato sul codice):** rolling asset → `SignalPlugin` con
    estensioni minori; portafoglio/multi-asset → `RiskAnalytic`. Il beta è l'unica
    rolling che richiede una **serie secondaria dichiarata** (slot assente oggi in
    `SignalInputRequirements`/`SignalExecutionContext`). Input-prep in **un'unica
    utility del service layer** (riusa coverage segnali + `convert_bulk`); i plugin
    **non** toccano DB/prezzi/FX/sync. (analisi §4/§4.1/§4.2)
26. **Beta ≠ risk-free sintetico:** una baseline a varianza nulla dà `var=0` → beta
    indefinito; il beta ammette solo benchmark **variabili**. (contratto §6.5)
27. **Metadata = estensione, non invenzione:** `data_quality_status`/`excluded_assets`
    **non** esistono in `DataQualityReport` → vanno aggiunti. La qualità considera
    **anche l'FX** carried-forward (`missing_fx_pairs`/backward-fill), non solo i prezzi.
    (contratto §4)
28. **Correlazione = un contratto, casa primaria Asset Global** (2ª tab "Correlation",
    vista asset-centrica), riusata in Dashboard/Broker/Asset Detail. Il filtro broker
    costruisce **solo il SET** di asset (nessun peso). Tab su `PageToolbar`+`TabBar`
    esistenti → piccola estensione. (analisi §5, brainstorm D-bis/D-ter)
29. **Stress per scope, una sola definizione di scenario:** Asset Detail % singolo ·
    Asset Global % multi-asset (no pesi) · Dashboard/Broker € (con pesi). (analisi §5,
    brainstorm E/E-bis)
30. **Sync = modale comune esistente (`PageSyncModal`)** con **prezzi + FX
    preselezionati**, avvio esplicito dell'utente; invalidazione/ricalcolo a carico
    della pagina (`onsynced`). È comportamento **frontend**, fuori dal dominio.
    (contratto §2.3, brainstorm §qualità dati)
31. **Monte Carlo — decisione originaria superseded.** L'inventario iniziale
    proponeva GBM NumPy in `asyncio.to_thread`; G5 corretto usa invece QuantLib
    MC/QMC sempre in worker `spawn`. Riskfolio 7.0.1 è installata per P13.
32. **Policy di riuso:** librerie (numpy/pandas/scipy → estensione minima → nuova lib
    solo se giustificata) e componenti UI custom (custom → variante → estensione →
    primitive → lib → ad-hoc). I nomi semantici del contratto non sono nomi di classe
    obbligatori. (analisi §7.1/§7.2)

## Riferimenti

- Roadmap Fase 0/0.1: [`../../Ai_ideas/phase_0_detailed_roadmap.md`](../../Ai_ideas/phase_0_detailed_roadmap.md)
- Roadmap strategica: [`../../Ai_ideas/roadmap_and_signals_brainstorm.md`](../../Ai_ideas/roadmap_and_signals_brainstorm.md)
- Migrazione segnali (Fase 0): [`../01_signalMigration/`](../01_signalMigration/)
- Gallery UI di riferimento: `mkdocs_src/docs/gallery/desktop/en/light/`
