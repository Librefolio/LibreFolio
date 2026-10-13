# Piano — fase 00, 53: i test del PAC (T-PAC)

> **Stato**: 🗂️ analisi chiusa. **Il developer ha deciso: «Tutto dopo la 1.2»** (13/10, §10). Tutti i lotti restano aperti per dopo la 1.2; per ora nessun codice.
>
> - **La cartella**: nata come `52_pacTests`, rinominata `53_pacTests` il 13/10, perché il 52 è di I (`52_timeAxisLastLabel`).
> - **Workstream T** · worktree `LibreFolio-worktrees/e-alfy-silver-barnacle` · ramo `e-alfy-t-matematica-finanziaria-unica`.
> - **Base**: `6a12f9a06` (treno 95) = target `dev_release2`, worktree pulita all'avvio.
> - **Corsia**: `--test-port 6164 --data-dir /tmp/librefolio-r2-t`, usata dopo l'UNFREEZE-VENV per due misure (§1). Porta libera alla fine.
> - **Coordinatore**: `c8328a01-f208-4ade-a352-0486d1f14de2`.
> - **Fonti**:
>   - 4 sottoagenti in sola lettura: la logica pura del planner, i suoi componenti, i test del frontend, i test del backend;
>   - le mie verifiche: **✔** = riverificato a mano su `6a12f9a06`; le righe senza ✔ vengono dagli inventari e si riverificano quando un lotto le tocca;
>   - skill `testing-frontend`, `testing-backend`;
>   - devWiki letta direttamente, perché graphify manca nella worktree: `decisions/pac-rounding-against-the-plan`, `decisions/pac-draft-copies-from-owned-data`, `decisions/e2e-gaps-of-1-2-before-release`;
>   - [README della 13](../13_pacAllocator/implementation/README.md), backlog e difetti 1, 2, 5;
>   - [rapporto R](../38_postReleaseBacklog/report-R-full-run-coverage-20261012.md), §4.2; C-69.
> - **Percorsi**: `planner/` sta per `frontend/src/lib/features/tools/pac-allocator/planner/`.

## 0. Mandato

- **Il developer, testuale**: «riguardo i test, se hai visto aree come il pac che vanno potenziate o hai visto test che non testano quello che dicono, è corretto lavorare per correggere e sviluppare i test di quelle aree».
- **Il coordinatore**: la mappa del planner; cosa coprono i test oggi; i test che dichiarano senza verificare; una proposta in ordine di rischio (pesi, importi e arrotondamenti, la prova, i numeri sul filo, il perimetro dei broker), con stima, registrazione nel runner e parte E2E minima, valutando `galleryPac.ts`; i rischi.
- **Niente implementazione prima del via del developer.**

## 1. I numeri di oggi (misurati ✔)

- **Copertura unit del planner**: **17,40 %**, 788 statement su 4 528.
  - Logica TS: 34,0 % (679/1 995). Componenti Svelte: 4,3 % (109/2 533).
  - 61 file su 84 allo 0 %.
  - Misura: istanbul in Vitest sui 13 file di test di `features/tools` (439 test, 34 s, 1 worker).
  - Coerente col 16,97 % del 12/10. Quella run contava su una build strumentata: il denominatore cambia (7 008).
- **L'E2E `pac-allocator-real`** (`--coverage js front-utility pac-allocator-real`, azione da 394 s con la build strumentata): verde, 1 test in 7 s. **Ha raccolto zero copertura JS**: «No JS coverage data collected».
  - **Causa ✔**:
    - la fixture `owned` dello spec smonta il planner portando la pagina su `about:blank` (`e2e/pac-allocator-real.spec.ts:283`);
    - solo dopo il teardown di `jsCoverage` legge `window.__coverage__` dalle pagine del contesto (`e2e/fixtures/playwright.ts:311-360`), e trova una pagina vuota.
  - **Il buco è strutturale (I1)**: i contatori vivono nel documento, ogni `page.goto` ne apre uno nuovo, e la fixture non li conserva fra una navigazione e l'altra. 47 punti degli E2E finiscono su `about:blank`.
  - **Conseguenze**:
    - le cifre E2E del JS (63,10 % nel rapporto R) sono limiti inferiori;
    - C-69, «da rimisurare nella run finale», non vedrà lo spec di V.
- **Backend del PAC**: fra l'84 e il 94 % (run del 12–13/10), con circa 31 700 righe di test.

## 2. Mappa del planner

84 file di prodotto: 27 moduli TS per 4 923 righe e 57 componenti Svelte per 7 768. In più 9 file di test, per 3 346 righe.

### 2.1 Logica pura e stato

| Modulo | Righe | Cosa fa | Numeri | Ambiente | Unit % |
|---|---:|---|---|---|---:|
| `decimal.ts` | 210 | testo decimale esatto (BigInt): parse, confronto, arrotondamento, percentuali di controllo | `sumControlPercentages`, `remainingControlPercentage`, `rebalanceControlPercentages` (:151-209) decidono i target che l'utente vede | node | 59,6 |
| `format.ts` | 307 | come si scrive ogni numero: denaro, quantità, tassi, percentuali, date | denaro esatto (R14, G3) poi un double (:109); percentuali via `formatPercent(Number(…))` (:223-235) | node | 80,4 |
| `request.ts` | 498 | bozza → problemi locali → richiesta sul filo → controllo zod | `localProblems` (:145-255) è il cancello; `buildRequest` (:259); `wireFraction`, `nonZero`, priorità intere | rune (bozza) | 69,7 |
| `draft.svelte.ts` | 779 | stato della bozza, totale dei target, coppie FX | `targetTotal` (:633), `#fxClosure` (:650-685), `selectionExceedsAvailable` (:774) | rune | 55,5 |
| `copies.ts` | 714 | applica le copie (broker, cassa, prezzi, FX, distribuzione), aggiornamento, conflitti | **perimetro dei broker** (:201, :230, :527), importi di cassa (:271-277), distribuzione → target (:677-714) | rune (bozza) | 1,1 |
| `result/model.ts` | 385 | badge del risultato (prova), barre dei pesi, confronto esatto, ordini, registro | `resultBadges` (:41-135), `compareExact` (:191), `planSteps`/`ordersByBroker` (:269-334) | node | 28,9 |
| `result/text.ts` | 74 | frasi di ordini, prezzi, minimi, tetti | `ratePercentText` (:71) | node | 74,2 |
| `issues.ts` | 240 | problemi del backend → passo, etichetta, parametri | `paramValues` (:113-134) | node | 0 |
| `source.ts` | 386 | tipi della fonte, lettura, id, timestamp | `toPlannerId` (:360) va sul filo | node + API | 12,5 |
| `scope.ts` | 41 | broker da cui si può copiare | **solo OWNER** (:31) | async | 0 |
| `review.ts` | 183 | conteggi e fatti del passo Review | — | node | 0 |
| `run.svelte.ts` | 111 | esecuzione, risposte vecchie scartate | — | rune | 0 |
| `sourceLoad`, `assetRead`, `fxRead` `.svelte.ts` | 64 / 153 / 149 | stati di lettura delle copie | — | rune | 0 |
| altri 11 (`modeText`, `policies`, `fxSetup`, `labels`, `ui`, `types`, `defaults`, `copyFlow`, `categoryLabels`, `exposureTooltip`, `shared/{tipHtml,columnHelp}`) | 16–93 | testi, costanti, piccoli aiuti | — | node/rune | 0–100 |

**Nota**: il browser non calcola nessun numero del risultato. Fa conti solo sulle percentuali di controllo dei target, ammesse dalla regola del developer (Q-C0-2), e sulle larghezze delle barre.

### 2.2 Componenti

| Gruppo | File | Cosa decidono | Test oggi |
|---|---|---|---|
| Guscio | `PacPlannerTool` (435), `shell/StepNav`, `shell/SummaryPanel` | Continue bloccato da `localProblems` (:136-143); `NO_OWNER_ERROR` (:213); rilettura delle copie prima del calcolo | solo l'E2E felice |
| Passi | `TargetsStep` (246), `LiquidityStep` (258), `BrokersStep`, `BrokerEditor` (424), `AssetsStep`, `AssetEditor`, `RoutingStep`, `FxStep` (362), `StrategyStep`, `ReviewStep`, `ScenarioStep` e i dialoghi (`BrokerScopeCopyDialog`, `DistributionDialog`, `OwnedAssetsDialog`, `ManualAccountDialog`) | stato del 100 % e riequilibri (`TargetsStep:39-72`); «supera il disponibile» (`LiquidityStep:131`, `ManualAccountDialog:28`); perimetro OWNER (`DistributionDialog:205-208`, quote parziali); Calculate bloccato (`ReviewStep:293`) | E2E felice; `FxStep`, `StrategyStep`, `AssetEditor`, `ManualAccountDialog` mai raggiunti |
| Risultato | `ResultView`, `OutcomeHeader`, `KpiCards`, `AssetTable`, `OperationalPlan`, `OrderDetail`, `LedgerTable`, `ProofPanel`, `Exposure*`, `StateNotice`, `ResultCell`, pannelli d'errore | solo formato di valori del backend (b), tranne i tempi di `BackendTimingBar` (diagnostica) | `ResultCell` (3 varianti su 11), `StateNotice`; il resto dall'E2E o da niente |
| Condivisi | 17 widget (`OwnerBrokerPicker`, `ReviewCell`, `TargetInputCell`, …) | quota parziale (`OwnerBrokerPicker:25`) | no |

I `data-testid` ci sono quasi ovunque. Secondo l'inventario, 5 widget piccoli non ne hanno. Prima di un test di componente si controlla che i numeri da leggere abbiano il loro.

## 3. Cosa coprono i test oggi

### 3.1 Vitest del planner

| File | Azione | Test | Cosa copre | Note |
|---|---|---:|---|---|
| `decimal.test.ts` | `core-unit` | ~150 | `roundDecimal`, `roundRatio`, `decimalEqualsRatio` | forte, ma 3 export su 15; il riequilibrio e le somme di controllo mai |
| `format.test.ts` | `core-unit` | ~94 | denaro R14/G3, numeri del solver, L2, plurali, locale | le percentuali (`format.ts:223-246`) non sono importate |
| `modeText.test.ts`, `pluralCountSites.test.ts` | `core-unit` | 13 + 19 | testo dell'incremento; guardia statica dei plurali | docstring vecchie («red today») |
| `request.test.ts` | `component-unit` | 7 | `buildRequest`, insiemi di chiavi esatti | valori solo in parte; nessun rifiuto, niente FX, niente modo per importo |
| `result/{ResultCell,StateNotice,model,text}.test.ts` | `component-unit` | 7 + 6 + 11 + 95 | 3 varianti di cella; notifiche dei top-up; aiuti dei badge; frasi e plurali | stati usati come barriere; niente `no_op`; toni mai |
| E2E `pac-allocator-real.spec.ts` | `front-utility pac-allocator-real` | 1 | percorso felice su dati reali, solo desktop | §3.2 |
| `gallery.spec.ts` + `fixtures/galleryPac.ts` | **fuori dalla suite** (`_inventory.py:54-55`) | 3 × 4 lingue × 2 temi × 2 viste | FX, commissioni, rotte, più broker | 140 `expect`, nessuno numerico contro la risposta |

### 3.2 L'E2E di V

- **Il percorso**:
  - account usa-e-getta, onboarding saltato;
  - un broker, due ETF manuali in EUR, dieci chiusure, un deposito di 5 000, acquisti di 20 × 90 e 30 × 40;
  - il tool si apre dalla card; Liquidità copiata (budget 1 000); il broker, i due asset «Your Assets», le rotte;
  - target da «Copy current distribution» (60/40), poi Calculate.
- **Le verifiche**:
  - la richiesta: codice del tool, valuta, prezzi, cassa e pesi, tutti via `Number()`;
  - la risposta: `ready_incumbent`, `optimal_proven`, `completed`;
  - a schermo: stati e badge, e per ogni asset valore finale, valore ideale e scarto; i due piè di tabella; debito e commissione di ogni ordine; il totale investito entro il budget.
- **Mai raggiunti da nessun E2E, galleria compresa**:
  - nel wizard: l'editor delle esposizioni, la rimozione di asset e broker, Balance all, la conferma che sostituisce i target, l'allarme del passo, la conferma d'uscita, la tabella dei fatti della Review, il tasso manuale o mancante e lo spread;
  - nel risultato: KPI, obiettivi, note, esposizioni, registro, dettaglio dell'ordine, Expand all, Edit e Calculate new plan;
  - gli stati: stale, interrotto, rilettura fallita, errore di piattaforma, no-op, limite, infattibile, top-up, privacy.

### 3.3 Backend

| Area | File (azione) | Test | Forte su |
|---|---|---:|---|
| aritmetica esatta | `test_pac_planner_exact` (`services:pac-planner-core`) | 40 | floor/ceiling/half-up, commissioni con minimo e tetto, tasso FX |
| normalizzazione | `…_normalize` (core) | 47 | precedenze, 10 controlli di intervallo, unità minime CLDR, banda FX |
| replay esatto | `…_evaluator` (`pac-planner-evaluator`) | 88 | conflitti del candidato, registrazioni, identità contabile, top-up |
| oracolo e solver | `…_oracle`, `…_solver`, `…_policies` | 21 + 15 + 35 | ottimo SCIP = oracolo; confini del MIP |
| prova | `…_proof` (`pac-planner-proof`) | 13 | testimone sigillato, nessuna prova trasferita |
| numeri sul filo | `…_wire_numbers` | 17 | 6 000 andata e ritorno senza perdite, testo canonico |
| servizio e rapporto | `…_planner`, `…_report` | 42 + 29 | tutti gli stati, pareggi in JPY/BHD/EUR, ricalcolo indipendente dell'arrotondamento |
| schema | `test_pac_planner_schemas` (`schemas:pac-planner`) | 103 | radici strette, testo numerico, prova, contabilità, pesi |
| copia dei dati | `test_portfolio_allocation_source` (`services:portfolio-allocation-source`) + `test_portfolio_api.py:1437-2075` (`api:portfolio`) | 48 + 7 | forma della richiesta, cassa e posizioni esatte, FX diretti, pesi a resto più grande |
| API del tool | `test_pac_planner_tool_api` (`api:pac-planner-tool`) | 12 | piano dal vivo, needs_input, identità vecchia |

**Matrice degli invarianti**: le lacune.

- **Pesi**: `target_weight_missing` non è mai prodotto. Il rifiuto dei pesi incoerenti c'è solo per il Rebalancer, senza la ragione.
- **Arrotondamento e unità minime**:
  - `rounding_bound` è provato solo con una registrazione;
  - nessun accredito FX in valute a 0 o 3 decimali;
  - lo schema non lega il limite alle registrazioni.
- **Prova**: nessun confronto campo per campo fra risultato pubblicato e replay (per esempio `rounding_delta` ← `rounding_adjustment`, `planner_report.py:722`).
- **Filo**: il validatore delle chiavi FX (`schemas/pac_allocator.py:619-631`) non è provato.
- **Perimetro**: nessun test dal vivo con EDITOR, con una selezione mista o col superuser sul servizio vero. Nessun test SQL che escluda i broker non scelti.
- **FX**: la coppia mancante della valuta di valutazione (`normalize.py:657-658`), lo spread fuori intervallo e il tasso «0» non sono provati.

## 4. Test che dichiarano più di quanto verificano

### 4.1 Frontend

| # | Dove | Promette | Verifica davvero | Cura |
|---|---|---|---|---|
| F1 | E2E, titolo `:362` e testata `:16-20` | «printed as the engine answered» | solo le celle di denaro, i piè e gli stati. Mai l'**istruzione** (quante unità comprare, `OperationalPlan.svelte:80`), i pesi, i KPI, gli obiettivi | confrontare istruzione e pesi con `instruction.quantity`, `target_weight` e `final_weight` |
| F2 ✔ | E2E `:17-19`, `:150-155`, `:528-537` | importi «at the currency's minor unit» | `printed()` scarta «≈» e separatori; il filo passa da `Number()`; i dati sono euro interi, quindi niente arrotondamento | tenere `≈` e separatori; filo come stringhe; un prezzo non intero e una commissione |
| F3 | `request.test.ts:30` | «a local problem is reported by its id» | solo la lista vuota (`:92-98`); `localProblems`, `stepOfWirePath` e `issues.ts` mai | tabella bozza → `{step, id}` |
| F4 | galleria (`galleryPac.ts:721-887`) | l'ordine trasferimento → conversione, i toni, il cancello della Review | non girano: la galleria è fuori dalla suite | portarle in uno spec (TP-19) |
| F5 | `request.test.ts:17-18`, `:107-108` | oggetti del filo confrontati come insiemi esatti | i valori di cassa, quota e capability no; `resolvedOf` è tautologico (`request.ts:465`) | `toStrictEqual` con letterali |
| F6 | `ResultCell.test.ts:3` | «the R14 number cells» | 3 varianti su 11; percentuali mai, a nessun livello | casi di `formatExactPercent` e delle celle `weight` |
| F7 | `StateNotice.test.ts:60`, `:12-13` | l'infattibile elenca il funding raggiungibile; la notifica del replay sparita | stati usati come barriere | asserire `data-kind` e callback |
| F8 | E2E `:540-541`, `:567-568` | il piano è «Verified in Decimal» | `proof.kind` e due toni; mai `primary_solution.validation` né il badge | aggiungerli |
| F9 | `model.test.ts:3` | «the catalogue behind every badge» | niente `no_op`, toni mai | caso `no_op` e tabella dei toni |
| F10 | `modeText.test.ts:180` | il ramo monetario | atteso = implementazione | ancore letterali |
| F11 | E2E `:36-38` | «offline: no sync, no live price» | nessuna richiesta registrata | fallire su sync e provider |
| F12 | E2E `:575-596` | ogni riga della risposta a schermo | le righe in più non si contano | `toHaveCount(n)` |
| F13 | `document-title`, `registry.test.ts:135-150` | il tool si monta | accetta `unavailable`; il binding vero non è mai caricato | un `load()` vero |
| F14 | E2E (I1) | coverage del planner | zero, per lo smontaggio prima della raccolta | §6 TP-18, D-4 |

### 4.2 Backend

| # | Dove | Promette | Verifica davvero | Cura |
|---|---|---|---|---|
| B1 ✔ | `test_portfolio_allocation_source.py:398-444` | «requires owner» | con EDITOR e VIEWER la sessione finta non restituisce righe, a prescindere dal codice; della produzione controlla solo che `OWNER` sia fra i parametri (`:404`), quindi un `role.in_([OWNER, EDITOR])` passerebbe | test dal vivo (TP-17) |
| B2 | `test_portfolio_api.py:1565-1596` | «superuser has no implicit bypass» | il builder è mockato per sollevare sempre | sul servizio vero |
| B3 | `test_pac_planner_schemas.py:1631-1724` | la mappa delle precedenze dei codici è congelata | non chiama mai il normalizzatore né `issues.py` | confronto con `issues.py:54-105` |
| B4 | schema, 42 `_reject` contro 14 `_reject_because` | regole specifiche | la ragione no: la mutazione del «rounding-bound» rompe anche lo shortfall (`:2870-2905`); circa 110 messaggi su 163 in nessun test | `_reject_because` |
| B5 | oracolo (`_pac_exhaustive_oracle.py:36-39`, `:191`) | indipendente | da SCIP sì, dall'evaluator no | il test derivato a mano (`:710`) e la verifica in Fraction (`:796`) restano l'àncora: va scritto nel docstring |
| B6 | `_QueuedReadSession` (`:62-95`) | perimetro dei broker | i filtri `broker_id IN` (`portfolio_allocation_source.py:61-66`, `:127-131`) non girano mai | TP-17 |
| B7 | `…_evaluator:4919-5221`, `:2310-2396` | rifiuti precisi | solo la classe dell'eccezione; sei rami di `ExactReplayRejectedError` senza messaggio | messaggi |
| B8 | `…_normalize:544-552`, `…_wire_numbers:10-15` | commenti | non più veri (tasso «0» ora `None`; confronti in Fraction) | aggiornare |
| B9 | `…_planner:301-316`, `:337-345`, `:359`, `:2030-2059` | nomi più forti dei controlli | una riga sola, il tipo e non il codice, atteso = implementazione, «eccezione o risultato qualsiasi» | rinforzare |

**Nessun reperto** in queste categorie: confronti float dove si dichiara l'esattezza, skip silenziosi (c'è solo lo `skipif` POSIX), test senza asserzioni.

## 5. Difetti di prodotto (trovati o sospettati)

| # | Difetto | Prova | Gravità | Un test lo trova? |
|---|---|---|---|---|
| D1 ✔ | **Le percentuali arrotondano male i pareggi.** `formatPlannerPercent` e `formatPlannerPercentUnits` (`format.ts:223-235`) passano da `formatPercent(Number(…))` (`utils/core/formatPercent.ts:82-90`: `value * scale`, poi `toFixed`). Il planner dichiara «half away from zero, exactly» (`decimal.ts:106`, R14). Una quota esatta di 0,30595 appare «30,59 %» invece di «30,60 %». Prova su tutte le frazioni a 5 decimali: sbaglia 3 864 pareggi su 8 000 fra 0,1 e 0,9, e 4 800 su 10 000 in unità percentuali | node, `/tmp` | bassa (l'ultima cifra ai pareggi), ma tocca pesi, quote, esposizioni, spread, margini | **sì, rosso oggi** (TP-2) |
| D2 ✔ | **L'aiuto di «Value after the plan» è sbagliato per il PAC**: «the units you had plus the ones bought» (`result/AssetTable.svelte:79-83`, chiave `…finalValueHelp`). Nel PAC `final_value = buy_mid_value` e `current_invested = 0` (`schemas/pac_allocator.py:1976-1981`, `:2026-2027`). La stessa tabella lo dice in `buyMidHelp`. Anche «Ideal value» parla di «already invested», che nel PAC vale sempre 0 | lettura | media (testo che informa male) | no: è testo; cura nel catalogo |
| D3 ✔ | **Un limite di SCIP a -0.0 diventa «-0»** (`planner_report.py:1055`, `:1086-1091`). La regex `PlannerFixedDecimal` lo rifiuta (`schemas/pac_allocator.py:47`), e il risultato fallisce la validazione | lettura | rara; media se capita | sì, con un valore -0.0 (TP-11) |
| D4 ✔ | **Il cancello locale non guarda segno e zero.** `localProblems` controlla solo vuoto e numero per importo da usare, contributo e passo (`request.ts:154-175`). Un negativo arriva al codec o al backend, e l'utente legge «A field does not match the planner contract: {path}». Inoltre un selezionato negativo è riportato sul percorso di `available` (`normalize.py:449-450`) | lettura | bassa (UX) | sì (TP-12); la cura vuole chiavi nuove: D-3 |
| D5 | Denaro e prezzi passano da un double (`format.ts:109`, `currencyFormat.ts:46`): oltre circa 15 cifre significative le ultime cifre sono inventate, senza «≈» | lettura | latente (grandezze irreali) | sì, come confine documentato (TP-6) |
| D6 | `AssetEditor` riscrive i pesi delle esposizioni passando dalle frazioni float del `DistributionEditor` condiviso (`steps/AssetEditor.svelte:82-104`, `toFixed(6)`). Tiene 4 decimali di percentuale; le esposizioni non cambiano il piano | lettura ✔ | bassa | sì (TP-4 o TP-13) |
| D7 | Backend, minori: i limiti del plugin (256/512 KiB) abbassati in silenzio ai default della piattaforma, 128/256 KiB (risultati reali da 21 a 38 KB); `rounding_delta` pubblicato da `rounding_adjustment`, col segno degli accrediti invertito rispetto al testo del contratto (`schemas/pac_allocator.py:1553` contro `planner_report.py:703-722`); `request_fingerprint = snapshot_id` nei fallimenti (`planner.py:167`); «-0» negli importi economici della copia (`portfolio_allocation_source.py:598`) | inventario | bassa | in parte (TP-11, TP-15) |
| I1 ✔ | **Infrastruttura**: la copertura JS degli E2E perde i contatori a ogni navigazione e a ogni `about:blank` (§1) | run + lettura | misura falsata per tutto il frontend | — (D-4, proprietario V) |

**Nessun difetto di denaro nel backend**: nessun caso in cui l'arrotondamento crei valore o un numero pubblicato sfugga al replay.

## 6. Proposta, in ordine di rischio

Ogni test ha prima il rosso, se il difetto c'è. Li scrive test-author; io vedo ogni rosso.

**Gli oracoli**: letterali o calcoli esatti indipendenti (`roundDecimal`, Fraction), mai la funzione sotto test.

**Le azioni**:
- `core-unit`: test node;
- `component-unit`: jsdom, oppure moduli che chiedono la bozza a rune (come `request.test.ts`);
- backend: le azioni esistenti.

### P1 — I pesi

| # | Test | Livello / azione | Rosso | Stima |
|---|---|---|---|---|
| TP-1 | `decimal.ts`, i controlli dei target: somma e resto, riequilibrio (somma esatta 100, rapporti nell'ordine, nessun negativo, resto più grande a pari merito per riga, tutti zero → parti uguali, `null` sui rifiuti), `percentToFraction`/`fractionToPercent`, `canonicalInput` coi separatori della lingua | node, `core-unit` (`decimal.test.ts`) | non atteso | 0,5 g |
| TP-2 | percentuali esatte: `formatPlannerPercent`, `formatPlannerPercentUnits`, `formatExactPercent`, `ratePercentText`, confrontate con `roundDecimal` in en, it, fr, con i pareggi | node, `core-unit` (`format.test.ts`) | **sì (D1)** | 0,25 g + cura 0,25 g (D-1) |
| TP-3 | `distributionProposal`/`applyDistribution` (`copies.ts:677-714`): al centesimo di punto la somma resta esattamente 100 (promessa della doc utente), asset manuali a 0, `changes` della conferma, stato `incomplete` | `component-unit` | non atteso | 0,5 g |
| TP-4 | `TargetsStep` montato: stati balanced, excess, missing; Balance all; Balance to 100 % di una riga; righe selezionate; limite fra 0 e 100 | jsdom, `component-unit` | non atteso | 0,5 g |
| TP-5 | celle dei pesi del risultato (`ResultCell` `weight`, `bars`, `unavailable`; colonne di `AssetTable`) | jsdom, `component-unit` | sì, se ereditano D1 | 0,25 g |

### P2 — Importi e arrotondamenti

| # | Test | Livello / azione | Rosso | Stima |
|---|---|---|---|---|
| TP-6 | denaro all'unità minima: JPY a 0, BHD e KWD a 3 decimali (`catalogCurrencyDigits`), «≈» solo se cambia la cifra, G3, il confine del double (D5) | node, `core-unit` | forse (D5, se si decide di curarlo) | 0,25 g |
| TP-7 | cassa copiata: saldo negativo → vuoto → `selectedMissing`; `usesAllAvailable` sul testo grezzo («1000.00» contro «1000»); `refreshCopiedFacts` scrive solo le copie non toccate; `resolveConflicts`; «supera il disponibile» al centesimo | `component-unit` | da vedere | 0,75 g |
| TP-8 | il risultato montato da una risposta vera (il fixture del backend `pac_plan_result.min.v2.json`, o uno nuovo): `KpiCards`, `AssetTable`, `OperationalPlan` con l'istruzione, `OrderDetail`, `LedgerTable`. Ogni cifra va contro l'esatto arrotondato in modo indipendente | jsdom, `component-unit` | da vedere | 1 g |

### P3 — La prova

| # | Test | Livello / azione | Rosso | Stima |
|---|---|---|---|---|
| TP-9 | `resultBadges` per esito × prova × arresto × validazione (`no_op`, `infeasibility_proven`, `not_proven` con `completed` e con `time_limit`, validazione diversa da `decimal_verified`) → badge e toni | node, `component-unit` (`model.test.ts`) | da vedere | 0,5 g |
| TP-10 | `ProofPanel`, `OutcomeHeader`, `StateNotice` (il funding raggiungibile nell'infattibile, l'importo del no-op, gli stadi, le callback) | jsdom, `component-unit` | da vedere | 0,5 g |
| TP-11 | backend: `_reject_because` sulle regole di prova e del testimone ottimo (`schemas/pac_allocator.py:2216`); la ragione dei rifiuti di prova sul filo; un limite -0.0 (D3) | `schemas:pac-planner`, `services:pac-planner-report` | **sì (D3)** | 0,5 g |

### P4 — I numeri sul filo

| # | Test | Livello / azione | Rosso | Stima |
|---|---|---|---|---|
| TP-12 | `localProblems` a tabella (~30 id, bozza → `{step, id}`), `stepOfWirePath`, `structureInvalid` col tetto di 20, segno e zero degli importi (D4) | `component-unit` (`request.test.ts`) | **sì, se D-3 = curare** | 1 g |
| TP-13 | `buildRequest` coi valori esatti (`toStrictEqual` su stringhe: cassa, quote, capability, `wireFraction`, omissioni `nonZero`, target vuoti a «0», priorità intere, solo le coppie richieste in `fx_rates`); `#fxClosure`, `requiredPairs`, `fxPurpose` (broker solo funding, rotta spenta, contributo in una terza valuta) | `component-unit` | da vedere | 0,75 g |
| TP-14 | `issues.ts` (`presentIssues`, `issueStep`, `entityLabel`, `paramValues`); `source.ts` (`toPlannerId` iniettivo, `toPlannerTimestamp`, `canonicalPair`) | node, `core-unit` | non atteso | 0,5 g |
| TP-15 | backend: i codici del normalizzatore che nessun test produce (commissioni `normalize.py:366-382`, rotte `:518-592`, funding `:455-500`, `reference_not_found` `:155-161`, timestamp `:209-212`, spread `:605-608`, tasso «0»); il validatore delle chiavi FX; il risultato campo per campo contro il replay; `rounding_bound` con più registrazioni e più valute | `services:pac-planner-core`, `schemas:pac-planner`, `services:pac-planner-report`, `…-evaluator` | forse (D7) | 1 g |

### P5 — Il perimetro dei broker

| # | Test | Livello / azione | Rosso | Stima |
|---|---|---|---|---|
| TP-16 | frontend: `scope.ts` (`selectableIds` solo OWNER); `applyBrokerCopy` e `applyLiquidityCopy` filtrano i broker scelti; `refreshQuery` = proprietari ∪ broker di cassa; `NO_OWNER_ERROR` | `component-unit` | non atteso | 0,5 g |
| TP-17 | backend dal vivo, `/portfolio/allocation-source`: EDITOR → 403; selezione mista → 403; i broker non scelti esclusi da posizioni e cassa, con l'SQL vero; superuser senza accesso → 403 sul servizio non mockato. Cura B1, B2, B6 | `api:portfolio` | da vedere | 0,75 g |

### P6 — E2E

| # | Test | Azione | Stima |
|---|---|---|---|
| TP-18 | rinforzo di `pac-allocator-real`, stesso test e quasi stesso tempo: F1, F2, F8, F11, F12. Istruzione e pesi contro la risposta; «Verified in Decimal»; filo come stringhe; righe contate; un prezzo non intero e una commissione, perché compaiano arrotondamento e «≈». In più la copertura raccolta prima dello smontaggio (I1) | `front-utility pac-allocator-real` | 0,5 g |
| TP-19 | un secondo spec reale, «FX e commissioni». Gli aiuti di `galleryPac.ts` si estraggono in `fixtures/pacPlanner.ts` (`openPacPlanner`, `goToPacStep`, `buildPacDraft`, `calculatePacPlan`): account usa-e-getta, broker EUR e USD, asset manuali, tasso manuale, commissione, contributo. Si confrontano filo e schermo: ordini con istruzione, trasferimenti, conversioni, KPI, obiettivi | nuova azione `front-utility pac-allocator-fx` | 1,5–2 g |
| TP-20 | percorsi non felici: «Continue» su un passo incompleto → `pac-planner-step-alert`; uno scenario infattibile (acquisto richiesto oltre la cassa) → la notifica coi vincoli e il link al passo | `front-utility pac-allocator-real` (secondo test) | 0,5 g |

**`galleryPac.ts`**:
- si riusano senza cambi gli aiuti di flusso: circa 40 interazioni e 42 `expect` diretti, senza scatti né cambi di lingua;
- da cambiare:
  - l'import dalla macchina della galleria (`:62-63`);
  - i dati del seed condiviso (TEST_ADMIN, DEGIRO, Interactive Brokers, Apple, Microsoft, il tasso EUR/USD salvato) vanno sostituiti con un account usa-e-getta;
  - i timeout di default.

Il file è di M: l'estrazione si concorda (D-5).

## 7. Quanto si allunga la suite

| Dove | Oggi (misurato nella corsia) | In più, stima |
|---|---|---|
| `core-unit` | 27 s, 4 140 test | +150–250 test node: +2–4 s |
| `component-unit` | 104 s, 117 file | +8–12 file jsdom: +20–40 s |
| E2E del PAC | 7 s di test, solo desktop | TP-18 ≈ 0; TP-20 +10–20 s; TP-19 +20–60 s |
| backend | — | `services` puri +5–10 s; `api:portfolio` dal vivo +10–20 s |

Totale: circa 1–2 minuti su una run completa.

## 8. Rischi e conflitti

- **Rossi di prodotto attesi**:
  - D1, sicuro;
  - D3, se lo si provoca;
  - D4, se si decide di curarlo;
  - D2 è testo, quindi una cura nel catalogo in 4 lingue con `dev.py i18n update`, senza chiavi nuove.
- **Superfici condivise**:
  - il runner `_frontend_utility.py`, cioè le righe di registrazione;
  - `fixtures/galleryPac.ts`, di M;
  - `e2e/fixtures/playwright.ts`, di V, se la cura di I1 è generale;
  - il catalogo i18n (D2, D4).
  - I file del planner sono del PAC (workstream D, chiuso per la 1.2): solo test aggiunti, e le cure di D1, D2, D4.
- **Stabilità degli E2E**: il motore vero ha i suoi limiti di tempo. Con dati piccoli SCIP chiude in pochi secondi, come nello spec di V. Account usa-e-getta, verdi a 1 e a 4 worker.
- **Oracoli**: i test esistenti hanno già casi di «atteso = implementazione» (F10, B9). I nuovi usano letterali o un calcolo esatto indipendente.
- **Copertura**: finché I1 resta, la run finale non mostrerà gli E2E del planner. La misura vera sarà l'unit più TP-18.

## 9. Lotti e stima

| Lotto | Contenuto | Stima | Quando |
|---|---|---|---|
| **A**: i numeri che arrivano all'utente e i test che mentono | TP-2 (+ cura D1), TP-1, TP-9, TP-12, TP-18, TP-17 | ~3,5 g | dopo la 1.2 (decisione del developer, §10) |
| **B**: i componenti | TP-3, TP-4, TP-5, TP-7, TP-8, TP-10, TP-13, TP-14, TP-16 | ~5 g | dopo la 1.2 |
| **C**: E2E e backend fine | TP-19, TP-20, TP-6, TP-11, TP-15 | ~4 g | dopo la 1.2 |

Totale: ~12–13 giorni. La copertura unit del planner dovrebbe passare dal 17 % a circa il 60–70 %, perché i componenti più grossi entrano con B.

## 10. Decisioni per il developer

**La decisione del developer (13/10, attraverso il coordinatore), testuale: «Tutto dopo la 1.2».**

- **Il chiarimento su D1**: il developer aveva chiesto se D1 non fosse l'arrotondamento prudente voluto. Il coordinatore ha spiegato che quello sta nel calcolo del piano, non nella visualizzazione:
  - le registrazioni arrotondate contro il piano, cioè accrediti per difetto e addebiti per eccesso (`backend/app/services/pac_allocator/constraints.py:417-418`, `ledger._PLAN_ROUNDING`);
  - il margine d'esecuzione.

  D1 invece è il modo in cui il planner scrive una percentuale già calcolata: arrotonda male i pareggi, contro la sua stessa regola R14.
- **Cosa vuol dire per la tabella sotto**:
  - D-6 è decisa: nessun lotto prima della 1.2;
  - le altre restano aperte, e si riprendono quando parte il primo lotto.
- **Nel backlog** (sezione C): C-69 aggiornata; una voce per ciascuno di D1–D4 (C-73…C-76), una per i test che mentono (C-77) e una per i minori (C-78). Tutte «dopo la 1.2».

| # | Domanda | Consiglio | Stato |
|---|---|---|---|
| D-1 | D1 (i pareggi delle percentuali): si cura nel lotto A, col rosso prima? | **Sì**: due funzioni, arrotondare in esatto con `roundDecimal` e poi formattare | aperta, dopo la 1.2 |
| D-2 | D2 (l'aiuto di «Value after the plan» e di «Ideal value»): si corregge per il PAC? | **Sì**, nei 4 cataloghi, senza chiavi nuove | aperta, dopo la 1.2 |
| D-3 | D4: il cancello locale controlla segno e zero, con un messaggio per passo (chiavi nuove), o si lascia al codec? | **Controllarli**: l'errore generico non dice dove | aperta, dopo la 1.2 |
| D-4 | I1: la copertura degli E2E si cura nella fixture per tutti (proprietario V), o solo per lo spec del PAC? | **Per tutti, a V**. Intanto per il PAC una raccolta prima dello smontaggio (TP-18) | aperta, dopo la 1.2 |
| D-5 | TP-19 riusa gli aiuti di `galleryPac.ts` estraendoli (file di M), o ne scrive di nuovi? | **Estrarli**, d'accordo con M | aperta, dopo la 1.2 |
| D-6 | Quali lotti prima della 1.2? | ~~**A** prima; B e C dopo~~ | **decisa: tutti dopo la 1.2** |
| D-7 | I minori del backend (D7) e i commenti vecchi (B8, F13): voci T-* nel backlog, o dentro C? | **Dentro C**; il resto nel backlog | aperta; intanto C-78 nel backlog |

## 11. Lotto T-PAC-J, solo journal (2026-10-13)

> **Note implementazione**:
> - **Mandato** (coordinatore, 13/10 sera): base `6a12f9a06`.
>   1. Rinominare la cartella in `53_pacTests`.
>   2. Scrivere nel piano la decisione e il chiarimento su D1.
>   3. Nel backlog, sezione C: aggiornare C-69; una voce per ciascuno di D1–D4, una per i test che mentono, una per i minori. Tutto «dopo la 1.2», senza toccare le voci degli altri.
>   4. Checkpoint col manifest e un commit ASCII. Niente codice, e la build strumentata in `frontend/build` resta fuori (è ignorata, `frontend/.gitignore:9`).
> - **Fatto**:
>   - la cartella, mai committata, è spostata con `mv`;
>   - il piano: titolo, stato, §9 e §10;
>   - il backlog: C-69 riscritta con le misure, I1 e i lotti; C-73…C-78 in coda alla sezione C, prima della voce senza numero «Devwiki e grafo».
>   - Il target (`dev_release2` = `ce09c6ac4`, letto come ref, senza aprire il checkout) arriva ancora a C-72: i numeri da C-73 a C-78 erano liberi.
> - **Verifica**: `constraints.py:417-418` è proprio l'arrotondamento contro il piano (accrediti `floor`, addebiti `ceil`).
