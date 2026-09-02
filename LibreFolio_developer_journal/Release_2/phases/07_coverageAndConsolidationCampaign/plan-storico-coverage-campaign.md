# Piano — Chiusura gap di coverage (backend + frontend)

> Il merge `origin/dev` → `dev_release2` è **chiuso** (commit `c4413528`, ancestry-only,
> zero cambi di contenuto). Questo piano riprende il lavoro sulla coverage.

## Decisioni prese con l'utente (revisione del 27/08)

- **Approccio ibrido** — E2E Playwright per i flussi, component test Vitest per gli atomi UI.
  `@testing-library/svelte` e `jsdom` sono **pacchetti npm veri** da aggiungere alle
  devDependencies, non decorator: permettono a Vitest di montare un `.svelte` in un DOM
  simulato e interagirci senza avviare Chromium.
- **BRIM fuori dal piano** — i provider di import sono in beta; senza dati reali i loro rami
  non si testano ora.
- **Solo codice realisticamente raggiungibile** — prima di scrivere un test si **ispezionano
  le righe mancanti**. I blocchi try/except puramente difensivi (condizioni impossibili da
  riprodurre) si escludono via `.coveragerc` o si documentano; **non si forzano**. Obiettivo:
  blindare il codice vero con non-regression test, non gonfiare la percentuale.
- **`generated.ts` escluso** dalla coverage JS.
- Dubbi sul comportamento UI: codice → mkdocs → skill `wiki-search` → domanda all'utente.

### Cos'è la branch coverage (risposta alla domanda)

Oggi si misurano le **righe eseguite**. Con `branch = true` coverage.py misura anche gli
**archi decisionali**: per ogni `if`/`for`/`while`, entrambe le uscite sono state percorse?

```python
if err:
    log(err)      # se nei test err capita sempre, ogni riga risulta coperta…
continue_work()   # …ma l'arco «err mai successo» non è mai stato percorso
```

La percentuale scenderà (tipicamente 2–5 punti) perché il denominatore cresce e archi mai
percorsi diventano visibili. Non è un peggioramento: è il numero vero. Serve **prima** di
scrivere i test, altrimenti si scrivono test guidati da una mappa sbagliata.

## Baseline misurata (corsa full-coverage del 27/08, **con** branch coverage e senza `generated.ts`)

| Lato | Statements | Branch |
|---|---|---|
| Backend (243 file) | **90,50%** | **78,34%** (8 668 / 11 064) |
| Frontend (377 file) | **65,83%** | **49,78%** |

> **Attenzione al numero di testa di coverage.py.** Con `branch = true`,
> `totals.percent_covered` diventa la metrica *combinata*
> `(righe coperte + archi coperti) / (stmts + archi)` — qui **87,72%**. Non è il tasso di
> statement: va calcolato a parte, altrimenti «da 90,48% a 87,72%» si legge come una
> regressione mentre gli statement non si sono mossi di un millimetro.

### La mappa dei branch riordina le priorità della Wave 1

File con ≥10 branch, ordinati per **archi mancanti**:

| miss | br% | stmt% | file |
|---|---|---|---|
| 88 | 78,9 | 89,2 | `services/lots_analysis_service.py` |
| 84 | 85,7 | 89,5 | `services/asset_source.py` |
| 79 | 84,5 | 94,1 | `services/portfolio_service.py` |
| 69 | **65,8** | 91,2 | `schemas/risk.py` |
| 66 | 86,5 | 93,0 | `services/portfolio_engine.py` |
| 54 | 89,0 | 92,3 | `services/transaction_service.py` |
| 51 | **50,0** | 72,8 | `services/asset_source_providers/justetf.py` |
| 50 | **56,1** | 85,3 | `services/ai_export/components/fx_payloads.py` |
| 48 | 68,8 | 87,7 | `services/risk/metrics.py` |
| 37 | **56,0** | 87,9 | `services/ai_export/components/technical_payloads.py` |
| 33 | **51,5** | 86,4 | `services/ai_export/components/fx_timing_context.py` |

Due letture che cambiano il piano:

- **`schemas/risk.py` sembrava sano** (91,2% di statement) ed è al **65,8% di branch**.
- Il grappolo **AI Export** (`fx_payloads`, `technical_payloads`, `fx_timing_context`,
  `aggregators`) somma ~150 archi mancanti ed è **calcolo puro** → test in isolamento
  `PURE`, i più economici che esistano.
- **`scheduler/jobs.py` non compare qui** (ha meno di 10 branch): il suo 18,2% è un puro
  gap di *statement*, i due corpi job semplicemente non girano mai. Resta target, ma per
  un motivo diverso da quello che sembrava.

## Risultati dell'analisi

### Backend — gap (in ordine di rischio)

- **B1 · `scheduler/jobs.py` 18,2%** — i due corpi job veri (`run_current_price_refresh`,
  `run_history_sync`) quasi mai eseguiti, mentre l'infrastruttura attorno (state, due-check,
  leader, loop) è già ben testata. **Gap principale e più utile da chiudere.**
- **B2 · `scheduler/joblog.py` 43,7%** — helper di build/append/rotazione delle entry.
- **B3 · Rami dei provider** — `justetf` 72,5%, `borsa_italiana` 77,6%, `yahoo_finance`
  73,1%, `snb` 69,4%, `fed` 75,2%. Da ispezionare: si copre solo ciò che un utente può
  davvero incontrare (risposta vuota, HTTP error, payload di forma diversa ma plausibile).
- **B4 · `asset_source.py`** 89,4% ma **170 stmts mancanti** (il maggior miss assoluto) e
  `lots_analysis_service.py` 98 miss — stessa regola: ispezione prima, test dopo.
- ~~BRIM providers~~ — **escluso per decisione**.

### Frontend — gap

- **F1 · `components/` 60,6%** — la massa del gap:
  - `ui/select` **16%** (FxProviderSelect), `ui/date` 0–44% (CalendarMonth **0%**,
    SingleDatePicker 20%, DateRangePicker 44%), `ui/input` (TagInput 33%)
  - `table` 43% (DataTableColumnFilter **22%**, DataTable 54%)
  - `dashboard` 44% (PerformanceChart **0%**, ExposureTreemap **0%**, AllocationHistoryChart 27%)
  - `settings` 56% (AboutTab 27%, SchedulerLogModal 23%)
  - `assets` 51% (ScheduledInvestmentEditor 26%, AssetCurrencyChangeModal 6%, AssetModal 53%)
  - `brokers/lots` (LotCustodyModal **12%**, LotComparisonChart 51%)
  - `transactions/modals` (ParseDetailModal 8%, PromoteMergeModal 10%, TransactionCompareModal 10%)
- **F2 · Routes 66,8%** — `assets/[id]` 74%, `fx` 48–65%, `files` 65%, `dashboard` 54%.
- **F3 · Zero component unit test**: la copertura componenti arriva **solo** da E2E
  (ImportWizardModal: 915 stmts coperte solo così). Nessuna infra `@testing-library`.
- **F4 · Sovra-test**: **nessuno dannoso**. I file coperti ≥80% sia da unit sia da E2E sono
  pochi e la doppia copertura è incidentale (l'E2E li attraversa, non li ri-testa). Unica
  correzione: `api/generated.ts` (478 stmts, 100%/100%, prodotto da `openapi-zod-client`)
  gonfia la percentuale.

## Vincolo architetturale: parallelismo nativo

Ogni nuovo test nasce dentro l'architettura di parallelizzazione, non vi viene adattato dopo:

- **Backend**: registrazione in catalogo con la **classe di isolamento giusta**
  (PURE/READ/WRITE_SCOPED); `exclusive_because=` solo con ragione scritta in una frase.
  Scheduler: `tmp_path` per joblog/state, provider MOCK → al massimo WRITE_SCOPED.
- **Frontend E2E**: niente `mode: 'serial'` senza motivo scritto; dati propri con
  `uniqueSuffix()`; attese su stato pubblicato, mai sleep; registrazione in `_frontend_{area}.py`.
- **Frontend Vitest**: gira nella passata unit consolidata; ogni file si registra come azione
  `*_unit` con `tests="src/lib/.../x.test.ts"`.
- **Definition of done**: verde da solo, verde nella categoria, verde a `--workers 8`, niente
  sleep, niente `.first()` non filtrati, ripulisce ciò che scrive, `check-orphans` pulito.

## Onde di lavoro

### Wave 0 — Misura e igiene *(prerequisito: cambia la mappa che guida tutto il resto)*
1. **T0.1** `branch = true` in `.coveragerc` (`[run]`), ri-baseline backend.
2. **T0.2** Escludere `src/lib/api/generated.ts` in `frontend/mcr.shared.js` → `sourceFilter`
   (punto unico condiviso unit+E2E, come dichiara la docstring del file). Annotare la nuova
   baseline.

### Wave 1 — Backend (ispezione prima, test solo del raggiungibile)
3. **T1.1** Test servizio per `scheduler/jobs.py` + `joblog.py`: manager monkeypatchato (così
   l'orchestrazione gira per intero senza la riscrittura globale dei prezzi), joblog in
   sandbox con il pattern `isolated_joblog_dir`, isolamento **READ**. Include il
   non-regression su `str(SyncStatus.ok) == "ok"`, che regge solo perché è una `StrEnum`.
4. **T1.2** Ispezione dei miss dei provider; test mock-driven solo dei rami reali. Il peggiore
   è `justetf.py` (**50,0% di branch**), poi `borsa_italiana`, `yahoo_finance`. BRIM escluso.
5. **T1.3** Rami di `lots_analysis_service.py` (88 archi), `asset_source.py` (84),
   `schemas/risk.py` (69 — il caso più sorprendente) e il grappolo **AI Export**
   (`fx_payloads`, `technical_payloads`, `fx_timing_context`, `aggregators`: ~150 archi di
   calcolo puro, isolamento `PURE`).

### Wave 2 — Infra component test + atomi UI (Vitest)
6. **T2.1** Installare `@testing-library/svelte` + `jsdom`; environment jsdom per i soli file
   component; setup con mock i18n. Spec dimostrativa su `ui/date/CalendarMonth.svelte` (0%
   oggi, auto-contenuto) per fissare il pattern; registrazione in catalogo; pattern aggiunto
   alle istruzioni test-author.
7. **T2.2** `ui/date`: SingleDatePicker, DateRangePicker.
8. **T2.3** `ui/select`: FxProviderSelect + fratelli; `ui/input/TagInput`.
9. **T2.4** `table`: DataTableColumnFilter e interazioni DataTable copribili in jsdom.

### Wave 3 — Flussi E2E (estensione spec esistenti, parallel-native)
10. **T3.1** `settings`: AboutTab, SchedulerLogModal, edge di GlobalSettingsTab.
11. **T3.2** `dashboard`: PerformanceChart, ExposureTreemap, AllocationHistoryChart.
12. **T3.3** `assets`: AssetModal (cambio provider con avviso scheduled-investment),
    ScheduledInvestmentEditor, AssetCurrencyChangeModal, pagina `assets/[id]`.
13. **T3.4** `brokers/lots`: LotCustodyModal e interazioni dei chart lots.
14. **T3.5** `transactions`: ParseDetailModal, PromoteMergeModal, TransactionCompareModal;
    pagine `fx` e `files`.

### Wave 4 — Verifica finale
15. **T4.1** `all --workers 8 --coverage` verde dall'inizio alla fine; baseline annotata;
    `check-orphans` pulito; lint backend+frontend puliti.

## Stato di avanzamento

- [x] **T0.1 — branch coverage backend.** `branch = true` in `.coveragerc`. Lungo la strada
  sono emersi tre difetti concatenati del runner, tutti corretti:
  1. `coverage combine` **rifiuta** di fondere dati ad archi con dati a righe → aggiunto
     `_archive_incompatible_coverage_dbs()` in `_suites.py`, che confronta
     `Coverage().config.branch` con `CoverageData.has_arcs()` di ogni DB salvato e archivia
     i disallineati. Candidati: `.coverage_data/backend`, `.coverage_data/frontend` **e il
     `.coverage` di root** — che sopravvive a ogni corsa backend-only ed era il vero
     portatore della modalità vecchia.
  2. coverage.py stampa quell'errore su **stdout**, e tutti e tre i punti del runner
     leggevano solo **stderr** → il messaggio usciva come `coverage combine failed:` seguito
     dal nulla. Corretti `_executor.py` e i due siti di `_coverage.py`.
  3. `_finalize_coverage` tratta un combine fallito come semplice *warning* e genera comunque
     l'HTML: una corsa «15/15 verde con coverage» poteva spedire in silenzio un report privo
     dell'intera passata parallela. Ora la riga di conseguenza lo dice a voce alta.
- [x] **T0.2 — esclusione `generated.ts`.** `GENERATED_SOURCES` + filtro in
  `frontend/mcr.shared.js` → `sourceFilter` (punto unico condiviso unit+E2E). Verificato
  senza rifare la corsa, ri-eseguendo `npx mcr merge --all src` sui raw esistenti:
  378 → **377 file**, 34 403 → **33 925** statement (−478), frontend 66,2% → **65,8%**.
- [x] **Rosso WB5 chiuso** (`tx-wac-bulk.spec.ts`). Non era né lentezza né sfortuna: WB5 era
  l'unico test del file che, dopo il clone, scommetteva 8 s sull'**esito** senza passare da
  `waitForWacResolved`, cioè senza aspettare la barriera che il prodotto pubblica
  (`data-validate-runs` che lascia lo zero, poi `data-busy`). Con il debounce di 1 s davanti
  e un backend strumentato due volte, quel budget cadeva nella coda della distribuzione.
  Inoltre il selettore composto `[data-state="ready"]` collassava «ancora in calcolo» e
  «questa riga un WAC non ce l'ha» nello stesso `element(s) not found`: presenza e stato ora
  sono asserzioni separate, in **entrambi** i file WAC, così il fallimento nomina lo stato
  ricevuto. Verificato: `tx-wac-bulk` 10/10, `tx-wac-formmodal` 10/10.
- [x] **T1.1 — scheduler.** `jobs.py` **18,18% → 100%** (statement *e* branch), `joblog.py`
  **43,69% → 96,12%**. Due unit nuove (`scheduler-jobs` isolamento **read**,
  `scheduler-joblog-builders`), 34 test, nessun accesso esclusivo richiesto: i tre entry
  point che riscrivono i prezzi sono sostituiti da doppi, il joblog è deviato in una
  sandbox per-uuid, e `jobs.py` non chiama mai `save_state()` — muta l'oggetto
  `SchedulerState` che riceve — quindi un'istanza usa-e-getta basta a isolarlo del tutto.
  Non coperte di proposito: due `except OSError` di pura difesa in `joblog.py` e il ramo
  falso di `len(pair_parts) == 2`, irraggiungibile perché `FXSyncPairResult.validate_pair`
  rifiuta a monte ogni `pair` che non sia `A-B`.
- [x] **Igiene di catalogo.** `test_brim_parse_race.py` era committato da `0c319f14` e **mai
  registrato**: un file di test che non girava. Ora è l'azione `services brim-parse-race`.
- [x] **T2.1 — infra component test.** `@testing-library/svelte` + `jsdom` +
  `@testing-library/jest-dom` installati; `vitest.config.ts` monta `svelte()` e
  `svelteTesting()`; harness condiviso in `src/__tests__/component.ts` (matcher jest-dom,
  `setupI18n()`, stub di `scrollIntoView`); alias `$test` dichiarato in `svelte.config.js`
  — non in `tsconfig.json`, che SvelteKit rigenera. Ambiente `node` di default, `jsdom`
  chiesto file per file: i ~650 unit test esistenti non pagano nulla (58 file, 655 test,
  tutti ancora verdi). Nuova azione di catalogo `front-utility component-unit`.
- [x] **T2.2a — `CalendarMonth`** (era **0%**): 9 test. Il componente non pubblicava un solo
  `data-testid`, contro la convenzione del progetto: aggiunti quelli di navigazione e un
  `data-state` per giorno (`selected|range-start|range-end|in-range|pending|today|…`), così
  lo stato visivo è interrogabile senza passare dalle classi Tailwind.
- [x] **T2.3a — `TagInput`** (era **33%**, zero E2E lo tocca): 17 test sul modello di
  tastiera. **Difetto reale trovato e corretto**: lo scroll della navigazione con le frecce
  cercava `[data-testid="tag-suggestion-idx-N"]`, un testid che il template non ha **mai**
  reso — la query tornava sempre `null` e con più di uno schermo di suggerimenti
  l'evidenziazione usciva dalla vista senza che nulla la riportasse dentro. Ora l'indice è
  un `data-idx` e c'è il test di non-regressione.
- [x] **Difetto d'ambiente chiuso: lo scheduler girava sotto gli E2E.** Il rosso
  `asset-modal › switching away from a parametric provider` (solo sotto carico, verde da
  solo) ha portato a galla due scritture di sfondo che nessun test controllava.
  1. Il `webServer` di Playwright avviava il backend **senza `--no-scheduler`**, flag che il
     path condiviso del runner passa da sempre e motiva per esteso: `populate_mock_data`
     scrive `last_run_at=yesterday`, quindi ogni job è dovuto all'avvio e cinque secondi
     dopo il boot il demone rinfresca i prezzi correnti di **ogni asset attivo** contro
     provider **live**. Una categoria frontend lanciata da sola (`./dev.py test front-asset
     all`) non si attacca al backend condiviso: se lo avvia da sé, e quindi girava contro un
     backend che muta i prezzi a timer e tira la rete dentro la suite. Allineato.
  2. **Fetchare un prezzo corrente non è una lettura**: `get_current_prices_bulk` documenta
     un write-back OHLC (F.2/F.3) che *crea la riga di oggi* a ogni fetch riuscito. La
     pagina di dettaglio quindi **aggiunge una riga di prezzo solo mostrando l'asset**, e
     una fetch ancora in volo quando il wipe committa atterra dopo di esso: resta un
     superstite che nessun poll successivo rimuoverà mai — `toBe(0)`, ricevuto `1`. Stubbato
     come già lo era `prices/sync`, con la ragione scritta: così l'asserzione resta
     **esatta** invece di diventare tollerante. Verificato: `front-asset` 87/87 a 4 worker.
- [x] **T2.2b — `SingleDatePicker`** (era **20%**): 23 test. Anche qui il componente non
  pubblicava lo stato: «calendario aperto» e «quello che hai scritto non è una data» si
  leggevano **solo** dalle classi Tailwind (`border-red-400`, `ring-libre-green`), cioè da
  niente di asseribile senza testare la palette. Ora la radice espone `data-open` e
  `data-invalid`, e trigger e popover hanno un testid derivato da quello passato dal
  chiamante (due picker sulla stessa schermata restano distinguibili). Coperti: le tre
  separazioni che la gente digita davvero, il rifiuto delle date future e di quelle che il
  calendario ingrigisce, Invio che committa e riapre, Escape che abbandona, il calendario
  che segue la data digitata, e le frecce che si fermano su oggi invece di scavalcarlo.
- [x] **Rosso `tx-delete` A2-confirm chiuso — era l'asserzione, non il prodotto.**
  `expect.poll(() => countRows(page, 'delete-safe', 'ETH')).toBe(0)` chiedeva *«nel mondo
  non esiste più nessuna riga il cui testo dica delete-safe ETH»*: un **totale globale che
  il test non ha creato**, cioè la regola 2 violata alla lettera. `tx-clone` committa
  legittimamente un clone di quella stessa coppia e lo rimuove nel proprio `afterEach` —
  e fra i due istanti la tabella condivisa contiene due righe in più. Il poll ha campionato
  lì dentro: ricevuto `2` in una corsa in cui la delete aveva funzionato perfettamente
  (nessun `Traceback`/`IntegrityError` nel log, e l'asserzione per `data-row-id` era
  passata). Il commento in testa a `e2e/fixtures/db-cleanup.ts` **descriveva già** questo
  identico scenario: la mitigazione lato `tx-clone` chiude la finestra, non la elimina.
  Ora il test chiede al **server** se i due id della coppia che ha davvero cancellato sono
  spariti — `related_transaction_id` è bidirezionale, quindi una sola GET nomina entrambe
  le metà. Esatto, immune ai vicini e alla paginazione, e non riscansiona più ogni riga.
  Lungo la strada: il `data-row-id` **non è** l'id della transazione (`TransactionsTable`
  antepone `tx-` / `ghost-` per tenere separati i due spazi di id nella selezione della
  DataTable) — la prima stesura passava `tx-123` a `?ids=` e prendeva 422. `countRows` è
  stata rimossa perché non serviva più a nessuno. Verificato: `tx-delete` 15/15 da solo,
  **categoria `front-transaction` intera 26/26 unit a 4 worker**, con `tx-clone` e
  `tx-delete` nella stessa invocazione — cioè con l'interferenza attiva.
- [ ] Wave 1 — T1.2 provider, T1.3 servizi + AI Export (**in corso**)
- [ ] Wave 2 — `table/DataTableColumnFilter`, `ui/select` (**in corso**), poi `ui/date` parent
- [ ] Wave 3 — flussi E2E
- [ ] Wave 4 — verifica finale

## Domanda aperta per l'utente (contratto, non implementazione)

`run_current_price_refresh` esce alle righe 51-53 quando non ci sono asset attivi **senza
scrivere né state né entry di joblog**. `run_history_sync`, nella stessa identica
situazione, scrive comunque state ed entry con liste vuote e status `ok`. Due job dello
stesso scheduler, stessa condizione, osservabilità opposta.

Conseguenza per l'utente: il pannello scheduler continua a mostrare l'esito della corsa
*precedente* e `last_run_at` non avanza, quindi «gira e non trova nulla» è
indistinguibile da «non gira più» — cioè un'installazione nuova, o una configurazione
rotta, sembra uno scheduler fermo.

I due comportamenti sono ora **pinnati da due test affiancati apposta**. Se si decide di
allineare `run_current_price_refresh` all'altro (state `ok` con `last_items_ok=0`), è
esattamente quel test a diventare rosso. **Non è stato cambiato nulla**: cambia ciò che
l'utente vede.

### Seconda domanda: il campo data diventa rosso mentre stai ancora scrivendo

`SingleDatePicker` calcola `typedInvalid` come «quello che c'è nel campo non è già adesso
una data valida». Scrivendo `2024-08-07` un carattere alla volta, il campo è rosso da `2`
fino a `2024-08-0` e torna normale solo sull'ultimo carattere. Vale per ogni data digitata,
sempre.

L'alternativa usuale è lamentarsi solo quando l'utente ha smesso (blur, o dopo una pausa).
Anche questo è pinnato da un test che dichiara nel titolo il comportamento reale, non quello
desiderabile — se lo si cambia, quel test lo dice.

### Terza domanda: `tx-delete` A2-confirm mangia una fixture che non è sua

Chiudendo il rosso è venuto a galla un secondo problema, **latente e non corretto** perché
la soluzione pulita tocca i dati mock — territorio in cui le istruzioni dicono di fermarsi
e chiedere.

`populate_mock_data.py` crea **una sola** coppia `delete-safe` ETH (Coinbase ↔ IB). Su
quella coppia insistono:

- `tx-delete` **A2** — apre il modale, annulla, e verifica che la riga sia *ancora lì*;
- `tx-delete` **A2-confirm** — la **cancella per sempre** e non la ripristina;
- `tx-bulk-suggest-ux` (tre volte), `tx-crud-full`, `tx-split-promote` — la cercano, e
  `tx-bulk-suggest-ux` **solleva un errore esplicito** se non la trova.

Due conseguenze. La prima: con `fullyParallel` A2 e A2-confirm possono girare **insieme**
su worker diversi, e A2 asserisce la presenza della riga che l'altro sta cancellando —
un rosso che oggi non si vede solo per fortuna di scheduling. Si noti che A1 e A1-confirm
lo evitano *per costruzione*, usando due righe diverse: l'asimmetria esiste perché il mock
offre una sola coppia. La seconda: A2-confirm lascia il database senza quella coppia, quindi
la tenuta delle altre spec dipende dall'**ordine** in cui il runner le pesca. È esattamente
la classe di dipendenza che questa campagna sta smontando ovunque.

Le tre uscite possibili, in ordine di costo:

1. **Una seconda coppia nel mock**, dedicata al consumo distruttivo (es. tag
   `delete-consume`): A2 tiene la sua, A2-confirm mangia l'altra. Una riga di fixture, zero
   complessità nel test — ma è un cambio a `populate_mock_data.py`, che altre spec leggono.
2. **A2-confirm si crea la coppia da sé** via `POST /transactions/commit` +
   `POST /transactions/transfers/promote`. Nessun cambio al mock, ma il setup diventa
   sensibile ai vincoli di saldo e di posizione che il backend applica alla promozione:
   un test sulla *cancellazione* comincerebbe a fallire per motivi di *creazione*.
3. **A2-confirm ripristina** ciò che ha cancellato, con gli stessi vincoli del punto 2.

La 1 è quella che consiglierei — ma la scelta è tua, perché muove dati che altri test
leggono.

## Baseline finale (corsa `all --coverage --workers 8`, **15/15 verde**)

| Lato | Statements | Branch |
|---|---|---|
| Backend (243 file) | 90,50% → **91,37%** | 78,34% → **80,40%** (8 668 → **8 895** / 11 064) |
| Frontend (377 file) | **66,85%** | **50,40%** (10 348 / 20 530) |

Il delta backend è confrontabile alla lettera: stesso denominatore di archi (11 064), 227
archi in più percorsi. Quello frontend **non lo è**: la cifra di partenza (65,83% su 33 925
statement) veniva da un `mcr merge` fatto sui soli raw presenti in quel momento, mentre
questa arriva dal report combinato completo (35 350 statement). Le due percentuali si
somigliano ma stanno su basi diverse: da qui in avanti la base di riferimento è questa.

Contorno verificato: `check-orphans` pulito (59 spec E2E, 63 unit frontend, 184 test
backend, tutti raggiungibili da `all`); `svelte-check` 0 errori / 0 warning; Prettier pulito
su tutto ciò che è stato toccato; `./dev.py lint` mostra **39 errori, tutti preesistenti** e
tutti in file che questa campagna non ha creato (`test_roi_utils` 21, `test_scheduler_leader`
10, più sette sparsi) — nessuno nei file nuovi.

## Decisioni prese dall'utente (27/08) ed eseguite

### Punto 4 — guardie morte: **ripulite**

Prima di cancellare le ho riverificate io, perché rimuovere una guardia viva sarebbe grave:

- `technical_payloads.py` — `observation_count == 0 and cell_counts` è irraggiungibile
  perché **ogni** elemento di `cell_counts` è ≥ 1: una cella singola conta `1`, e
  `TechnicalRangeValueCell.observation_count` è `Field(..., ge=2)`. Quindi con riga a 0 il
  `max(cell_counts) > 0` della riga precedente scatta sempre per primo.
- `aggregators.py` — `observation_count == 0 and any(component_counts)` è irraggiungibile
  perché `any()` è vero solo se un componente ha count > 0, e quel componente ha già fatto
  scattare il `component.observation_count > self.observation_count` dentro il loop.

Rimosse entrambe. I due test che le riguardavano **esistevano già e pinnavano il
comportamento, non la riga** — è precisamente ciò che rende la rimozione sicura: l'invariante
resta verificata, e se un domani qualcuno rilassa `ge=2` il test diventa rosso lì. Ho
riscritto i loro commenti, che citavano numeri di riga ormai inesistenti.

### Punto 5 — seconda coppia nel mock: **fatta**

`populate_mock_data.py` crea ora una coppia `delete-consume`, gemella della `delete-safe`
ma **monouso**, la cui descrizione **non contiene** la sottostringa `delete-safe`: i finder
delle altre spec continuano a pescare la prima e ignorano questa. `tx-delete` A2-confirm
punta alla nuova.

Verifica: `tx-delete` 15/15 → poi, **senza ripopolare**, `tx-bulk-suggest-ux` 8/8. Quel test
solleva un errore esplicito quando la coppia `delete-safe` non c'è, quindi è la prova diretta
che ora sopravvive alla cancellazione. Categoria `front-transaction` intera 26/26 a 4 worker
con il mock modificato.

Lungo la strada: `./dev.py format` ha tolto una riga vuota di troppo in
`test_server_helper.py` — un file che non avevo toccato ma che non era conforme al formatter
del progetto. Lasciata la correzione: rimetterla indietro terrebbe il repo fuori dal proprio
standard.

### Verifica dopo le due modifiche

`all --coverage --workers 8` → **15/15**. Backend 91,36% stmt / 80,37% branch
(8 889/11 060), frontend 66,60% / 50,19%. Il denominatore degli archi scende da 11 064 a
**11 060**: esattamente i 4 archi dei due `if` rimossi, nient'altro. `check-orphans` pulito,
`./dev.py lint` fermo a 39 errori preesistenti.

## Cinque correzioni approvate (27/08, secondo giro)

### 1. Scheduler unificato

`run_current_price_refresh` non esce più muto. Verificato che fra i due job non ci fosse
**nessun'altra** differenza in quel punto: `run_history_sync` salta il blocco asset ma
prosegue e scrive sempre state + joblog; il gemello faceva `return` dentro la sessione.
Ora anche lui registra la corsa vuota — `status="ok"`, `summary {ok:0, err:0}`, `items: []`
— mentre **continua a saltare** la chiamata ai provider: registrare la corsa non è la stessa
cosa che fare lavoro inutile.

Prova del rosso: rimesso il `return`, i due test cadono entrambi. Ripristinato: 90 verdi.

### 2. Date picker — il reclamo si arma quando lasci il campo

Nuovo stato `validationArmed`: `oninput` lo disarma, blur e Invio lo armano, Escape lo
azzera con il testo. `data-invalid` è ora `validationArmed && typedUnparseable`.

**Ma la richiesta non si poteva soddisfare solo così**, e vale la pena scriverlo:
`commitTyped` faceva `typed = null` *sempre*, quindi al blur il testo rifiutato spariva e
tornava il valore precedente — non restava niente da segnalare. Ora il testo che il picker
non accetta **resta sullo schermo** ed è lì che diventa rosso; Escape resta la via per
abbandonare, e un campo svuotato è letto come abbandono (rimette il valore memorizzato).
Prima, «ho sbagliato a digitare» e «ho scritto una data che questo campo rifiuta» erano
indistinguibili: in entrambi i casi il testo spariva senza dire niente.

Prova del rosso: tolto l'arming, cadono **6 test su 26**, esattamente i sei nuovi.
Ripristinato: 26/26. `front-transaction` 26/26 a 4 worker.

### 3. Il bool che diventava 1

Aggiunto un `field_validator(..., mode="before")` che rifiuta i bool sul valore grezzo —
l'unico punto in cui un bool è ancora un bool. Il controllo `< 1` resta dov'era, in
`mode="after"`, su un intero già coercito. Stesso messaggio d'errore, così nulla di ciò che
ci faceva match si rompe.

Verificate le altre nove occorrenze di `isinstance(value, bool)` nel backend: sono **helper
puri** che ricevono `object` grezzo e funzionano. Il difetto era isolato a questo.

Dettaglio emerso dalla prova del rosso: **solo `True` era il buco**. `False` diventa `0`,
che il controllo «deve essere positivo» rifiutava comunque. Entrambi i casi restano nel
test, con il motivo scritto.

### 4 e 5 — delegate all'agente `fe-filter-header-fixes`

Filtro multi-scelta che ignora la ricerca, e intestazioni di gruppo selezionabili in
`SimpleSelect`. Consegna con obbligo di dimostrare il passaggio rosso→verde su entrambi.

### 4 e 5 — rientrati dall'agente, con una mia correzione sopra

Filtro multi-scelta: la causa vera non era «l'elenco non si filtra» ma che il ramo
multi-enum filtrava **solo** su `label` mentre il gemello usava `label` **o** `searchText`
— ed è in `searchText` che vivono gli ISIN. Ora un unico predicato condiviso, così i due
rami non possono più divergere. `SimpleSelect`: allineato a `optionFilter.ts`, la
convenzione che `SearchSelect` già usava, invece di inventarne una nuova.

**Correzione mia sopra il lavoro dell'agente**: `selectAllMultiEnums` **sostituiva**
l'insieme con i visibili. Con una ricerca attiva questo toglie la spunta a tutto ciò che la
ricerca nasconde: cerca → spunta → cerca ancora → spunta, e resta solo l'ultimo gruppo.
È «seleziona solo questi» con l'etichetta «seleziona tutto». Passato all'unione, con il test
del caso che mancava (spunta preesistente fuori vista). Rosso dimostrato contro la
sostituzione.

Da segnalare all'utente: con ricerca attiva «seleziona tutto» ora agisce sui **visibili**
e non su tutto l'elenco. Nessuna spec E2E tocca quei testid.

### Corsa finale

`all --coverage --workers 8` → **15/15**. Backend 91,36% stmt / **80,40%** branch
(8 894/11 062 — i 2 archi in più sono il nuovo validatore `before`), frontend 66,72% /
50,33%. `check-orphans` pulito, lint fermo a 39 preesistenti.

## Corsia mia — `brokers-detail`: dieci test su ventidue non testavano niente

Andando a coprire `LotCustodyModal` (11,9%) ho trovato la ragione vera di quel numero, ed è
più grave della copertura.

`brokers-detail.spec.ts` conteneva **36 uscite silenziose** (`if (!ok) return`,
`if ((await x.count()) === 0) return`). Le ho armate temporaneamente — sostituendo ogni
`return` con un `throw` parlante — e ho misurato: **10 test su 22 uscivano prima di fare
alcunché**, tutti con lo stesso motivo, `row empty`. Cioè l'intero blocco «FIFO lots
analysis panel» si dichiarava verde senza aprire mai il pannello.

La causa non era un'attesa mancante: lo snapshot del fallimento dice «**No positions
available**». `goToFirstBrokerDetail` faceva `brokerCards.first().click()` — e *«il primo»
non è un'identità*: la lista è ordinata per nome, il mock ha sette broker e le altre spec ne
creano di propri, quindi si atterrava su qualunque cosa ordinasse per prima, spesso un
broker senza posizioni. In più `count()` non ritenta, quindi «lento» e «broker sbagliato»
producevano lo stesso identico esito: verde.

Correzioni:
- `goToBrokerWithHoldings` ancora a **Interactive Brokers**, l'unico che il mock riempie di
  posizioni, filtrando le card per testo (`.first()` su collezione filtrata è legittimo);
- `goToFirstBrokerDetail` non torna più un booleano: il mock i broker li ha sempre, quindi
  «nessuna card» è un fallimento, non un motivo per saltare;
- `firstHoldingRow` **asserisce** invece di sondare, con un messaggio che dice cosa
  controllare;
- tutte e 36 le uscite rimosse: le cinque che restavano sono diventate asserzioni parlanti.

Risultato: **24/24**, e stavolta facendo il lavoro. Aggiunti due test sul modale (le tre
sezioni + le figure di P&L derivate; chiusura da header e da footer).

### Un buco che non ho colmato, perché tocca i dati mock

La sezione «scomposizione del netto» del modale è dietro `{#if lotHasNetCosts}`. Ho scritto
il test che **cerca** un lotto con costi allocati invece di assumere che il primo li abbia,
e ha risposto: nessuno dei primi sei di IB. Il motivo è nel mock — entrambe le righe FEE di
`populate_mock_data.py` hanno `asset_id=None`, sono spese di conto e non vengono mai
allocate a un lotto, quindi `lotHasNetCosts` è falso per ogni lotto esistente. Ho tolto il
test e lasciato il buco **documentato nel file**, perché colmarlo richiede una fee o una
tassa legata a un asset nel mock: dati che altre spec leggono.

## Nota operativa: tre corsie, un solo database

Lanciando la categoria broker a 4 worker mentre i due agenti lavoravano, è arrivato
`no such table: users` — non un difetto dei test: un agente stava ricreando il database di
test sotto i piedi della mia corsa. Il parallelismo fra corsie vale per **scrivere**, non
per **eseguire**: backend e database di test sono uno solo. Da qui in avanti le verifiche
vanno serializzate.

## `DateRangePicker` — chiuso (agente `fe-filter-header-fixes`)

Il componente aveva **esattamente** i due difetti che l'utente aveva già approvato di
correggere sul gemello `SingleDatePicker`, quindi sono stati allineati (l'unica eccezione
autorizzata): validazione che si arma su blur/Invio invece di essere continua, e testo
rifiutato che resta a schermo invece di sparire ripristinando in silenzio il valore
precedente. Aggiunti gli attributi di stato che prima erano leggibili solo dalle classi
Tailwind: `data-open` sulla radice, `data-active` su ogni preset, `data-invalid` sui due
campi, testid sul popover.

Rosso dimostrato: **4 falliti su 17** contro il componente non allineato, e i quattro erano
esattamente i comportamenti di parità. Dopo: 17/17.

17 test nuovi: preset (finestra esatta, marcatore attivo, **nessun preset scavalca oggi**
con `allowFuture=false`, sentinelle MAX), invariante dell'intervallo, indipendenza dei due
campi, stepping con le frecce, apertura/chiusura e commit, e la cucitura della data
sbagliata. Copertura **25,9% → 52,9%** su base unit (115/444 → 248/469).

Pinnati e **non** toccati, perché non sono difetti: l'inversione inizio/fine è uno **scambio
deliberato** (commentato nel sorgente), non un intervallo invertito accettato; e nessun
preset supera oggi quando il futuro è vietato — il difetto classico della famiglia qui non
c'è. `disabledDates` non esiste su questo componente.

## Corsa finale delle tre corsie — 15/15

| | prima | dopo |
|---|---|---|
| Frontend statement | 66,72% | **69,15%** |
| Frontend branch | 50,33% | **52,62%** |
| Backend statement / branch | 91,36% / 80,40% | 91,36% / **80,41%** |

Per file, dove è stato fatto il lavoro:

| file | prima | dopo |
|---|---|---|
| `LotCustodyModal.svelte` | 11,9% | **82,9%** |
| `ExposureTreemap.svelte` | **0,0%** | **73,4%** |
| `AllocationHistoryChart.svelte` | 26,8% | **66,4%** |
| `PerformanceChart.svelte` | **0,0%** | **60,9%** |
| `DateRangePicker.svelte` | 40,3% | **55,4%** |

Il salto di `LotCustodyModal` è la conferma della diagnosi: non è stato scritto quasi nulla
su quel componente, sono semplicemente stati messi in condizione di girare i test che
c'erano già e che uscivano in silenzio. Nota a margine: `brokers/[id]/+page` risulta ora
all'85,1%, quindi lo 0% visto nella misura per singola categoria era un artefatto della
corsa parziale, non un buco di strumentazione.

## Domande aperte da questa tornata

1. **Il mock non ha lotti con costi allocati.** Entrambe le righe FEE hanno `asset_id=None`
   (spese di conto), quindi `lotHasNetCosts` è falso per ogni lotto e la «scomposizione del
   netto» del modale — commissioni allocate, tasse allocate, P&L netto — non è raggiungibile
   da nessun test. Servirebbe una fee o una tassa legata a un asset nel mock. Buco lasciato
   documentato nel file.
2. **Tre corsie, una porta.** `front-portfolio` non è una categoria server-backed, quindi è
   Playwright ad avviare il backend con `./dev.py server --test --force`, e `--force`
   uccide chi occupa la 6041. Con più agenti che lanciano E2E insieme, uno stende il server
   dell'altro (ed è anche ciò che mi ha azzerato il database a metà corsa). Si può far
   riusare a tutti un backend condiviso stabile invece di forzare la porta: è un intervento
   sul runner, non l'ho fatto.

## Verifica di raggiungibilità — e un difetto trovato facendola

La domanda era: `check-orphans` dice «registrati», ma girano davvero? Andando a verificarlo
è saltato fuori un difetto vero.

**`pytest --collect-only` rediretto su file produceva zero byte.** Non era pytest: è
`conftest.py`, che in `pytest_unconfigure` chiude il processo con `os._exit()` — e `os._exit`
**salta il flush degli stream**. Su un terminale non costa nulla (line-buffered), ma ogni
corsa che il runner registra passa per una **pipe**, dove il buffer è di pochi KB e solo i
blocchi pieni sono già stati scritti. Si perde la coda — che è esattamente la sezione
FAILURES e la riga di riepilogo, cioè le due cose per cui quell'hook era stato spostato lì.
Il commento nel sorgente diceva di volerle preservare; senza flush le buttava via lo stesso,
solo più tardi.

Sintomo già presente e visibile: **ogni log per unit del backend in `.testLog` finiva a metà
riga su `[100%]`, senza riepilogo**. Corretto con un flush esplicito prima dell'uscita:
`--collect-only` passa da **0 a 2 057 byte**.

Con il flush a posto, la verifica richiesta:

| file | eseguito in `all` | test raccolti |
|---|---|---|
| `test_ai_export_fx_payload_invariants` | worker 3 | 70 |
| `test_ai_export_fx_timing_invariants` | worker 5 | 55 |
| `test_ai_export_technical_payload_invariants` | worker 3 | 48 |
| `test_ai_export_technical_shared_pure` | worker 4 | 54 |
| `test_ai_export_temporal_aggregator_invariants` | worker 5 | 43 |
| `test_scheduler_jobs` | worker 5 | 20 |
| `test_scheduler_joblog_builders` | worker 4 | 14 |

**304 test.** Sul frontend: tutti e 8 i file component nel log vitest di `front-utility`, e
`dashboard.spec.ts` nel log e2e di `front-portfolio`.

## Backend condiviso: il runner è a posto, il problema ero io

Distinzione richiesta, verificata sui log della corsa `all`:

- **Il runner non crea doppi backend.** Un solo avvio su 6041, e viene perfino *messo in
  pausa di proposito* quando serve ricreare il database («Pausing the shared backend —
  creating a clean test database needs the database file to itself»). **Zero** righe
  `[WebServer]` in tutta la corsa: Playwright non ne ha mai avviato uno suo, ha riusato il
  condiviso. Lo conferma il global-setup: «DB and users already prepared by the runner».
  Il meccanismo è `reuseExistingServer: SHARED_SERVER ? true : …` in `playwright.config.ts`,
  pilotato da `LIBREFOLIO_TEST_SHARED_SERVER`. **La richiesta originale è implementata e
  funziona.**
- **Il `--force` scatta solo per una categoria frontend lanciata da sola**, dove non c'è
  nessun backend condiviso a cui attaccarsi. Ed è esattamente ciò che facevamo: due agenti
  che lanciavano categorie singole in parallelo. Corsa critica di sviluppo, non un difetto
  del prodotto. Nulla da correggere.

## Fee legata a un asset — fatta

`populate_mock_data.py` ha ora una FEE (-3,20 USD) e una TAX (-1,13 USD) **legate ad Apple**
su IB, datate dentro la vita dei lotti così che `_allocate_cost_pools` abbia frammenti su cui
distribuirle. Importi piccoli di proposito, per non mandare in negativo nessun saldo. Le altre
FEE/TAX restano di conto: non ne è stata cambiata nessuna.

Il test del breakdown è tornato al suo posto e **cerca** un lotto con costi invece di
assumerlo. Rosso già dimostrato prima della modifica al mock («no lot among the first 5»);
ora `front-broker detail` è **25/25**.

## Onda 3 — corsia mia: settings (scritta, non ancora verificata)

Esecuzioni serializzate: l'agente backend ha l'esclusiva sul database, quindi ho solo
**scritto**. Da verificare appena si libera.

### `SchedulerLogModal` (22,9%) — aperto e chiuso, mai guardato dentro

I tre test esistenti aprono il modale e lo chiudono. Restavano fuori i **tre filtri**, lo
**stato per voce** e il **dettaglio espandibile** — cioè quasi tutto il componente.

Due cose andavano pubblicate prima, perché leggibili solo dalle classi Tailwind (asserire su
quelle significa testare la palette):
- ogni voce ora espone `data-job`, `data-status`, `data-expanded`, `data-has-detail`;
- il contenitore espone `data-busy`, così «visibile» smette di essere confuso con «caricato»;
- il ramo «nessuna voce» ha un testid, così un elenco vuoto si distingue da uno non ancora
  caricato;
- i tre `SimpleSelect` dei filtri ricevono `optionTestId` — che il componente già supportava
  ma il modale non passava — quindi un filtro si pilota senza cliccare testo tradotto.

Cinque test nuovi (FSCH-011..015). Le asserzioni sui filtri sono **relazioni**, non numeri:
«tutto ciò che sopravvive al filtro porta lo stato richiesto», che regge qualunque cosa
faccia un vicino. Il mock semina già corse `ok`, `partial`, `error` e `history_sync`, quindi
c'è materiale vero.

### Un selettore su testo tradotto, corretto

`goToSchedulerSettings` cliccava la categoria con `getByRole('button', {name: 'Scheduler &
Upload'})`: passa solo nella lingua in cui gira la suite. I bottoni categoria non avevano
testid — aggiunto `global-settings-category-{id}`, e la spec ora usa quello.

### `AboutTab` (27,1%) — due sezioni dentro un `<details>` chiuso

I test leggevano nome e versione e si fermavano lì; il catalogo dei segnali installati e la
diagnostica plugin per sistema stavano dentro un `<details>` che nessuno apriva. Due test
nuovi, che aprono e asseriscono sull'attributo `open` (non sul chevron che ruota). Alla
diagnostica ho aggiunto `data-status`/`data-failures`, perché «tutto caricato» era leggibile
solo dal segno di spunta verde e dalla sua didascalia tradotta. L'ultimo test asserisce che
**nessun** sistema di plugin sia in stato `failed`: un plugin che esplode all'import è un
difetto vero, e questo è il punto in cui verrebbe fuori.

## Una cosa che ho trovato e NON toccato: un test che mente

`settings.spec.ts`, «theme preference persists after page reload». Non verifica la
persistenza del tema. Sceglie il bottone con `button:has-text("Dark")` — **testo tradotto** —
e se non lo trova salta il click in silenzio (`isVisible().catch(() => false)`); poi ricarica
e l'unica asserzione finale è che la scheda preferenze risulti selezionata. Il commento nel
sorgente lo ammette: «The actual persistence is verified by the page loading without errors».

Renderlo onesto è facile — i bottoni del tema hanno bisogno di un testid e di `data-selected`
— ma **il tema è una preferenza dell'utente di test condiviso**, e `broker-sharing.spec.ts` e
`image-crop.spec.ts` lo commutano dal toggle globale leggendo `documentElement.classList`.
Un round-trip vero entrerebbe in conflitto con loro, e `mode: 'serial'` non protegge fra file
diversi. Le vie d'uscita sono tre: accettare il rischio, dare al test un utente tutto suo, o
lasciarlo com'è dichiarando che non verifica la persistenza. È una decisione, non un edit.

## Tre corsie, secondo giro — risultati

| | prima | dopo |
|---|---|---|
| Backend statement | 91,36% | **91,74%** |
| Backend branch | 80,41% | **81,40%** |
| Frontend statement | 69,15% | **69,94%** |
| Frontend branch | 52,62% | **53,10%** |

Per file:

| file | prima | dopo |
|---|---|---|
| `lots_analysis_service.py` (branch) | 79,90% | **98,33%** |
| `asset_source.py` (branch) | 85,67% | **90,44%** |
| `AboutTab.svelte` | 27,1% | **87,1%** |
| `SchedulerLogModal.svelte` | 22,9% | **79,5%** |
| `ScheduledInvestmentEditor.svelte` | 25,9% | **49,9%** |
| `DataTable.svelte` | 53,9% | **56,6%** |

Corsa finale **14/15**: unico rosso `test_sync_weekend_no_rates`, diagnosi sotto.

## Il rosso: un test che dipende dalla Banca Centrale Europea

`test_fx_sync.py::test_sync_weekend_no_rates` è caduto con `httpx.ReadTimeout` a 8 worker,
e passa da solo (l'intera categoria `api fx` fa 21/21 in 12 secondi). Non è mio, ed era verde
nelle due corse precedenti: è **intermittente**.

La causa non è il carico in sé. Il test registra una route sul provider **ECB** — quello vero
— e poi sincronizza: quindi **esce sulla rete**, contro la regola «mai raggiungere un
servizio esterno». Sette punti di quel file fanno lo stesso.

E non si corregge sostituendo il provider: `MOCKFX` restituisce un tasso per **ogni** giorno,
weekend compreso, mentre questo test verifica proprio che nel weekend non arrivino punti —
cioè una proprietà del comportamento **reale** della BCE. Le vie d'uscita sono tre, e sono
una decisione: spostare questi test in `test_external/` (la categoria che la rete la ammette
per contratto), insegnare a un provider mock i giorni di chiusura, o accettare la dipendenza
e dichiararla. Alzare il timeout sarebbe solo una scommessa più lunga.

## Tre difetti di prodotto trovati dai component test — nessuno corretto

1. **`addDays`/`addMonths`/`midpointDate` sbagliano giorno fuori da UTC.** Parsano a
   mezzanotte locale e riserializzano in UTC, quindi a est di Greenwich il giorno slitta
   indietro. Misurato con `TZ=Europe/Rome`: `addDays('2024-12-31', +1)` resta
   `2024-12-31`, e `addDays('2024-03-15', -1)` torna `2024-03-13` — **due** giorni indietro.
   Conseguenze osservate: «aggiungi periodo» crea un periodo che inizia lo stesso giorno in
   cui finisce il precedente, violando l'invariante dichiarata del componente al primo
   click; e lo split fa condividere alle due metà il giorno di confine, contando un giorno
   di interessi due volte. 15 punti di chiamata. **Invisibile alla CI se gira in UTC.**
2. **`sortedData` non ha un ramo per i null**: finiscono in `String(null)` e vengono
   confrontati con `localeCompare`, quindi in ordine decrescente le celle vuote finiscono
   **sopra il valore massimo**, e la posizione dipende dalla grafia del segnaposto.
3. **`internalUpdate` ingoia il primo aggiornamento esterno dopo una modifica**: se il
   genitore rialimenta un valore diverso da quello che ha ricevuto (risposta normalizzata
   dal server, cambio di asset, reset del form) l'aggiornamento sparisce in silenzio.

Nessuno dei tre è stato cementato nei test: le spec evitano di attraversarli, così restano
verdi oggi e resteranno verdi dopo la correzione.

## I due difetti corretti, e il test FX sostituito (28/08)

### Difetto 1 — l'aritmetica delle date: peggio di quanto sembrasse

La misura sulla vecchia implementazione, sotto tre fusi:

```
TZ=Europe/Rome        addDays(2024-06-01, +1) -> 2024-06-01   *** non avanza ***
TZ=UTC                addDays(2024-06-01, +1) -> 2024-06-02   ok
TZ=Pacific/Kiritimati addDays(2024-06-01, +1) -> 2024-06-01   *** non avanza ***
```

Non era un caso limite di fine anno: **nessuna** somma di giorni funzionava a est di
Greenwich. Il difetto è invisibile solo perché la CI gira in UTC.

La cura non è aggiustare le tre funzioni dov'erano, ma smettere di uscire dal dominio:
**una data-only non ha fuso**. Nuovo modulo `src/lib/utils/dateOnly.ts` che fa tutta
l'aritmetica in UTC dall'inizio alla fine, più `todayIso()` che invece legge i campi
**locali** — perché «oggi» è una domanda sul calendario dell'utente, e
`new Date().toISOString()` alle 00:30 a Roma risponde *ieri*. Il progetto conosceva già la
forma giusta: `SingleDatePicker.todayIso()` la usava.

Lungo la strada: `Date` **normalizza in silenzio** un giorno inesistente — `2023-02-30`
diventa 2 marzo — cioè trasforma un errore di battitura in una risposta plausibile e
sbagliata. `parseUtc` fa il giro di andata e ritorno e la rifiuta.

25 test sull'helper, verdi sotto `Europe/Rome`, `UTC`, `America/Los_Angeles` e
`Pacific/Kiritimati` (UTC+14). `ScheduledInvestmentEditor` migrato (35 punti di chiamata).

E soprattutto: ora si possono scrivere i test che il difetto rendeva impossibili. Tre
aggiunti, sulle invarianti che il componente **dichiara** di rispettare — «il periodo nuovo
comincia il giorno dopo la fine del precedente», «nessun buco e nessuna sovrapposizione su
tutta la scaletta», «lo split non fa condividere il giorno di confine». Prova del rosso:
contro l'aritmetica vecchia cadono **esattamente quei tre**, gli altri 36 no.

### Difetto 2 — l'ordinamento dei vuoti

`sortedData` non aveva alcun ramo per `null`/`undefined`/`''`: finivano in `String(aRaw)` e
passavano per `localeCompare`. In ordine decrescente le celle vuote scavalcavano il valore
massimo, e la loro posizione dipendeva dalla **grafia** del segnaposto (`'null'` e
`'undefined'` dopo le cifre, `''` prima di tutto).

Ora un valore mancante va in fondo **in entrambe le direzioni** — con un `return` diretto,
perché l'inversione applicata più sotto non deve spostarlo. Due test nuovi; il primo è rosso
contro il comparatore vecchio.

### Il test FX: eliminato e sostituito, come richiesto

`test_sync_weekend_no_rates` registrava una route sul provider **ECB vero** e asseriva che
un sabato desse zero punti. Due cose non andavano: usciva sulla rete, e ciò che verificava
non era il nostro comportamento ma il **calendario di pubblicazione della BCE** — il giorno
in cui la BCE pubblicasse di sabato, o fosse irraggiungibile, il test direbbe una cosa
diversa senza che il nostro codice sia cambiato.

Sostituito da `test_convert_falls_back_to_the_last_rate_before_a_gap`, che verifica ciò che
per l'utente conta davvero: una serie ha buchi — weekend, festivi, un provider che salta un
giorno — e una conversione datata dentro un buco deve comunque risolvere, usando il tasso
più recente **a quella data o prima**. Poiché MOCKFX restituisce un tasso per ogni giorno,
il buco viene **costruito**: si sincronizza una finestra chiusa (6-8 gennaio) e si converte
il 10. Il tasso fisso rende l'asserzione **esatta** (123,45 e non «è arrivato un numero»).

In più il caso simmetrico, che è ciò che dimostra che la regola è «a quella data o prima» e
non «un tasso qualsiasi»: una conversione datata **prima** dell'inizio della serie non deve
risolvere, e infatti non risolve. `api fx` 21/21, offline.

### Il test FX: seconda stesura, dopo un rosso che era mio

La prima versione asseriva il valore assoluto (`100 × 1,2345`) e, come caso simmetrico, che
una data **prima** della serie non risolvesse. È caduta sotto carico, e la colpa era mia due
volte: quando *tutte* le conversioni falliscono l'endpoint risponde **404**, non 200 con
`to_amount` nullo; e soprattutto quel caso dipendeva dall'**assenza** di tassi EUR-GBP prima
del 2025, che il test non aveva creato e non poteva garantire — `FxRate` è globale.

Riscritto come **relazione**: il giorno dentro il buco deve dare la stessa cifra dell'ultimo
giorno che ha davvero un'osservazione. Vero chiunque abbia riempito la serie, e con qualunque
provider. Il caso «prima della serie» è stato tolto, non aggiustato: chiedeva una garanzia
sull'assenza di dati altrui.

## Un difetto del runner: lo spegnimento non liberava la porta

Due corse `all` consecutive sono cadute su `Create Database`, con
`Port 6041 still held by PID(s) … after shutdown`. Non era un test: il runner mette in pausa
il backend condiviso per ricreare il database — cosa giusta, e già deliberata — ma
`self.proc.wait()` reap solo il **padre**, mentre con quattro worker uvicorn i figli
sopravvivono e tengono il socket. Scaduta l'attesa, il codice si limitava a **segnalare** e
proseguiva; il passo successivo si rifiutava di toccare il database con qualcosa sulla porta,
e l'intera categoria falliva per un motivo che con i test non c'entrava nulla.

Ora, se allo scadere dell'attesa la porta è ancora occupata, i processi residui vengono
chiusi per PID — sono processi che il runner stesso ha avviato — e si riattende. Solo dopo
si segnala l'errore.

Con la correzione: `all --workers 8` → **15/15**.

## Difetto 3 — corretto, e il caso riproducibile non era quello che pensavo

La guardia ora **confronta** invece di contare: `emitChange` ricorda cosa ha spedito e
l'effetto salta solo ciò che coincide.

Il primo test che ho scritto — «modifica, poi il genitore rimanda un valore diverso» — è
passato **anche con la guardia vecchia**: fra la modifica e il rerender l'effetto gira e
consuma il contatore. Quindi non era una prova, era una coincidenza.

Il caso davvero riproducibile è un altro, e peggiore: **il montaggio su valore vuoto**. Il
componente in quel caso emette da solo, da un `queueMicrotask`, e arma la guardia senza che
nessuno abbia toccato niente; poiché il genitore non ha mandato nulla, niente la consuma.
Quando i dati veri arrivano — da una fetch, un attimo dopo — **vengono ingoiati**, e
l'editor resta vuoto. Test rosso dimostrato contro la guardia a conteggio.

## Analisi delle duplicazioni

### Frontend

| duplicato | copie | stato |
|---|---|---|
| `todayIso` / `todayISO` | **6** | **4 sbagliate** (usano `toISOString()`, cioè UTC) |
| `escapeHtml` | **10** + 1 variante | logica identica, funzione di **sicurezza** |
| `safeInt` / `safeStr` / `safeNum` | **7** | esiste già `safeString`/`safeNumber` in `types/common.ts`, **ignorata** |
| `setupResizeObserver` | **8** | boilerplate ECharts |
| `formatDate` | **7** | da verificare quanto divergono |

Il primo è quello con conseguenze, e non è teorico: `CalendarMonth`, `DateRangePicker`,
`TransactionFormModal` e `TransactionBulkModal` calcolano «oggi» in UTC. Misurato:

```
istante 2024-06-14T22:30Z (= 00:30 italiane del 15)
  toISOString -> 2024-06-14      calendario dell'utente -> 2024-06-15
istante 2024-12-31T23:30Z (= 00:30 italiane del 1° gennaio)
  toISOString -> 2024-12-31      calendario dell'utente -> 2025-01-01
```

Venti punti d'uso complessivi. Per chi apre l'app dopo mezzanotte: il calendario segna ieri
come oggi, una nuova transazione nasce datata ieri, e il limite «non oltre oggi» rifiuta la
data di oggi. `SingleDatePicker` è l'unico che lo fa giusto — la correzione era già stata
trovata una volta e non si è propagata, che è esattamente il costo della duplicazione.

### Backend

| duplicato | copie | note |
|---|---|---|
| `_require_positive_int` | **5** (tutto AI Export) | logica identica, cambia solo l'eccezione e il testo |
| `_is_fiat_currency` | **4** (provider BRIM crypto) | da confrontare |

Nota metodologica: i 45 `provider_code`, 31 `parse`, 31 `can_parse` eccetera **non** sono
duplicazione — sono implementazioni del pattern registry, corrette per costruzione.

### Duplicazioni con divergenza — le due che mordono davvero

`_is_fiat_currency`, quattro copie nei provider crypto BRIM, **non sono uguali**:

```python
# broker_delta.py — nessuna normalizzazione
Currency.validate_code(value)

# broker_bitvavo.py — normalizza prima
code = code.strip().upper()
if not code: return False
Currency(code=code, amount=Decimal("0"))
```

Lo stesso codice valuta, scritto con uno spazio o in minuscolo, è fiat per un broker e non
per un altro: la stessa riga importata da due file diversi viene classificata in modo
diverso. È la forma peggiore di duplicazione, perché non si vede finché qualcuno non porta
un file con un formato leggermente diverso.

`_require_positive_int`, cinque copie nell'AI Export, sono invece identiche nella logica e
cambiano solo l'eccezione sollevata e il testo del messaggio — duplicazione innocua ma
inutile, risolvibile con un helper parametrizzato sull'eccezione.

`formatDate`, sette copie nel frontend, divergono nei formati (`toLocaleDateString` con
opzioni diverse, una addirittura `toLocaleTimeString`): qui la divergenza è probabilmente
voluta, ma nessuno può dirlo guardando i nomi.

## Stato finale

`all --workers 8` → **15/15**, con il fix del runner che ha fatto il suo lavoro nella corsa
precedente («Port 6041 still held after SIGTERM — closing PID(s) 37742» seguito da un
`Create Database` riuscito).

Un rosso intermittente osservato una volta e non riprodotto: `test_lots_analysis_service.py`
`::test_buy_sell_summary_converts_to_target_currency` con
`UNIQUE constraint failed: fx_rates.date, fx_rates.base, fx_rates.quote`. Due test **dello
stesso file** inseriscono `FxRate(2025-02-01, EUR, USD)` con tassi diversi (1,3 e 1,25) su
una tabella globale. La categoria da sola passa a 8 worker, e la corsa successiva è verde:
è latente, non introdotto da questo lavoro, e va sistemato dando a ciascun test una riga
propria invece di condividere data e coppia.

# ═══════════════════════════════════════════════════════════════════
# Giro di deduplicazione + Onda 3 (28/08)
# ═══════════════════════════════════════════════════════════════════

Decisioni prese dall'utente:
1. `todayIso` — unificare. **Corsia mia.**
2. `_is_fiat_currency` — unificare **normalizzando a maiuscolo**.
3. `escapeHtml` — fattorizzare.
4. `safeString`/`safeNumber` — usare le comuni, cancellare le locali, e **cercare altri
   helper con nome diverso ma funzione identica**. Più un audit di
   `backend/app/schemas/common.py`: verificare che i molti contratti aggiunti di recente non
   abbiano **ricreato** strutture che bastava estendere.
5. Conflitto `FxRate` fra i due test lots-analysis — separare i dati.
6. Onda 3 — procedere.

**Regola operativa per questo giro**, su indicazione dell'utente: gli agenti fanno le
modifiche e al massimo un test mirato; **una sola corsa completa alla fine**. Per evitare
quel che è già successo (un `db populate` che azzera il database sotto un'altra corsa) le
corsie sono assegnate in base a *cosa toccano*:

| corsia | tocca il DB? | può girare insieme a |
|---|---|---|
| frontend puro (Vitest) | no | chiunque |
| backend (fiat, schemi, FxRate) | sì | solo la corsia frontend |
| E2E Onda 3 | sì | solo la corsia frontend — **quindi parte dopo il backend** |

## Punto 1 — `todayIso` unificato, e un test che si confermava da solo

Le **sei** definizioni locali sono sparite: tutte importano da `$lib/utils/dateOnly`. Anche
`SingleDatePicker`, che era l'unica corretta — tenerla a parte avrebbe solo lasciato in giro
una settima copia da cui ricominciare a divergere.

Ma il difetto in `DateRangePicker` era più largo di `todayISO`: **`withMinWindow`,
`computeStartDate` e `computeCustomStart`** costruivano un `Date` locale, lo spostavano e lo
rileggevano con `toISOString()` — quindi *ogni preset* (1W, 1M, 3M, 6M, 1Y…10Y e i
personalizzati) partiva un giorno prima a est di Greenwich. Curiosamente MTD, QTD e YTD lì
accanto erano già scritti bene, dai campi locali: due stili opposti nello stesso `switch`,
in disaccordo di un giorno. Tutto portato su `addDays`/`addMonths`.

### Il test dei preset esisteva e non serviva a niente

`DateRangePicker.test.ts` aveva già «a preset sets the end to today and the start a window
before it». Rimettendo il calcolo difettoso su `1W`, i **17 test restavano verdi**.

Il motivo è nel suo stesso docblock, che lo dichiarava candidamente: i valori attesi erano
«computed relative to today with **the component's own** UTC-based
`toISOString().slice(0,10)`». L'oracolo replicava l'errore dell'implementazione, così i due
sbagliavano insieme e si confermavano a vicenda. Un oracolo va derivato dalla **regola**, non
dal codice sotto test.

Corretto l'oracolo — e non bastava ancora: rimesso il difetto, restava verde lo stesso,
perché `toISOString()` e il calendario locale **coincidono per ventidue ore al giorno**. Un
test che gira alle 10:30 non può vedere un difetto che esiste fra mezzanotte e le 02:00.

Serviva congelare l'orologio: il nuovo test fissa l'istante a `2024-06-14T22:30Z`, che a Roma
è lo 00:30 del 15, e deriva l'atteso dai campi **locali** di quell'istante — così enuncia la
regola in qualunque fuso invece di fissare ciò che vede Roma. **Rosso contro il difetto,
verde dopo.**

Verifica: `DateRangePicker` 18/18 sotto Roma, UTC e Kiritimati; suite Vitest completa
**902/902** sotto Roma e UTC; `svelte-check` 0/0; Prettier pulito.

## Punti 3 e 4 — deduplicazione frontend (agente `component-tests-wave2`)

**Il mio brief era sbagliato in due punti, e l'agente non l'ha eseguito alla cieca.** Vale la
pena scriverlo, perché è il motivo per cui la fattorizzazione non ha fatto danni.

### `escapeHtml`: quattordici copie, non dieci — e due varianti

La quattordicesima si chiamava **`esc`** in `FxProviderSelect`: nessun `grep "function
escapeHtml"` poteva vederla, l'ha trovata la ricerca **per corpo**. E non erano identiche:

| variante | sostituzioni | copie |
|---|---|---|
| A — con `'` → `&#39;` | 5 | 8 |
| B — senza apostrofo | 4 | 5 |
| C — `escapeHtmlAttr`, stesso effetto della B | 4 | 1 |

La divergenza è **un buco di sicurezza latente**: le cinque copie B non chiudono un attributo
delimitato da apici singoli. Oggi tutti i call site usano apici doppi, quindi non è
sfruttabile — ma è un invariante che nessuno stava sorvegliando, ed è esattamente ciò che
dieci copie fanno sparire dalla vista.

**Non unificata**: `inlineMath.ts`. Lì l'escape avviene **prima** di KaTeX, quindi ciò che
produce è ciò che KaTeX compone: passare alla variante con l'apostrofo avrebbe rotto la
**notazione di derivata** (`f'(x)`) in ogni formula dei sottotitoli dei segnali. Verificato
eseguendo entrambe. Lasciata dov'è, con il perché scritto sopra.

### `safeNumber` non è `safeNum` — e il mio brief avrebbe azzerato la dashboard

```
safeNumber('12.34')  ->  null     // type-guard: non è un numero, e non tira a indovinare
safeNum('12.34')     ->  12.34    // parser
```

Gli importi arrivano dal backend come **stringhe**, per non perdere precisione. Eseguire
alla lettera «usa le comuni e cancella le locali» avrebbe sostituito un parser con un
type-guard e **azzerato ogni importo di ogni grafico**, in silenzio, perché `null` in quei
componenti si rende come `—` e non come errore. L'agente si è fermato e ha aggiunto
`safeDecimal`, con il nome che dice cosa fa.

`safeInt` invece **era** `safeNumber` sotto un altro nome: 13 casi limite eseguiti
affiancati, zero divergenze. Era il nome a nascondere il duplicato, non l'implementazione.

Lasciati divergenti di proposito, perché cambiano cosa vede l'utente quando un dato manca:
`firstScalar` in `UnifiedLotsTable` (salta i `null` invece di prendere il primo elemento) e
il suo `safeNum` (rifiuta `±Infinity`, le altre copie lo accettano).

**Bilancio: 36 definizioni eliminate, 3 aggiunte, 31 test nuovi** in `core-unit`. Fra questi,
quello che fissa `safeNumber('12.34') === null` con la spiegazione — la trappola è ora in un
test invece che nella memoria di qualcuno.

### Altri duplicati avvistati e non toccati

Traduci-con-fallback sotto tre nomi (`label`/`tr`/`translatedOr`), chiave di posizione sotto
due, numero-finito-o-null sotto due, data breve per asse in tre chart, snake→Title in due,
`portal`/`portalAction`, e quattro modi di annullare un long-press. Il più utile da chiudere
è `translatedOr`: è logica i18n copiata tre volte.

## Punti 2, 4-backend e 5 (agente `sched-jobs-tests`)

### `_is_fiat_currency` — il mio sospetto era sbagliato, il difetto era un altro

Le varianti erano **due** su quattro file, e **non divergevano** come temevo:
`Currency.validate_code` (`common.py:137`) **fa già** `upper().strip()` e rifiuta già la
stringa vuota, quindi lo `strip().upper()` della variante B era ridondante, non una regola
diversa. Verificato eseguendo tutte e quattro su `'eur'`, `'  EUR  '`, `''`, `'   '`,
`'BTC'`, `'XXX'`: **identiche su ogni input stringa**. Il caso che avevo descritto — la
stessa valuta con uno spazio classificata diversamente — non era riproducibile.

**Il difetto vero era dietro**: nella variante B la normalizzazione stava **fuori** dal
`try`, quindi su un input non-stringa (una cella CSV non parsata: `None`, `123`) due dei
quattro provider sollevavano un `AttributeError` **non catturato**, mentre gli altri due
restituivano `False`. Un crash latente negli importer, non una differenza di
classificazione.

Unificata in `common.py` come `is_fiat_currency` — non in `_brim_io.py`, che la sua stessa
docstring delimita all'IO dei broker italiani e tira dentro openpyxl, mentre tutti e quattro
i plugin importavano già `Currency` da `common`: zero nuovi archi di import. Quattro copie
rimosse, 16 call site ripuntati.

### Audit di `common.py` — esito controintuitivo: il livello schemi è sano

| base comune | sottoclassi | modelli che ridichiarano invece di estendere |
|---|---|---|
| `BaseBulkResponse` | 21 | **0** |
| `BaseListResponse` | 14 | **0** |
| `BaseDeleteResult` | 10 | **0** |
| `BaseBulkDeleteResponse` | 6 | **0** |

Il segnale che cercavamo — contatori bulk riscritti a mano — dà **zero** risultati fuori da
`common.py`. Le 59 `currency: str` non sono duplicazione: sono `str` sul filo più
`Currency.validate_code` come validatore, che è il pattern stabilito.

La duplicazione vera è tutta in `ai_export/`, che è un **livello diverso** (dataclass ed
eccezioni tipizzate, non modelli pydantic). Fatta la sola fattorizzazione a rischio nullo:
`_validate_finite_positive_decimal`, identica byte per byte in `fx_payloads` e
`fx_timing_context` — e l'arco di import fra i due **esisteva già**.

### `FxRate` — riprodotto prima di correggere, e il problema è più largo

L'agente ha **piantato le righe in conflitto** nel database e misurato: `IntegrityError`
riprodotto, e dopo la correzione le righe del «vicino» sopravvivono intatte. I due test ora
usano chiavi disgiunte (`2025-02-01` e `2025-03-05`) più un helper che cancella **solo** la
propria chiave prima di inserire — e funziona perché la fixture fa `flush` + rollback, quindi
anche la cancellazione viene annullata.

**Ma ha trovato di peggio**, fuori dal perimetro e non toccato:
`test_fx_core.py:44` e `test_fx_sync_service.py:36` hanno una fixture **`autouse=True`** che
fa `DELETE FROM fx_rates` **senza WHERE** e con **commit** — cancellano l'intera tabella
globale in modo non recuperabile, prima di ogni test del file. E
`test_fx_sync_service.py:107` asserisce `len(rows) == 2` su tutte le righe EUR/USD, cosa che
regge **solo** grazie a quella purga. Oggi non esplode perché il planner mette in parallelo
solo le unit `PURE`; il giorno in cui si allarga, diventa un rosso quotidiano.

## Domande aperte da questo giro

1. **Solana è classificata come valuta fiat.** `SOL` è il Nuevo Sol peruviano, `ALL` il Lek
   albanese, `XXX` il codice ISO «nessuna valuta»: tutti e tre validano come ISO 4217.
   Serve una denylist crypto — decisione di dominio, non toccata. C'è un test che documenta
   la collisione.
2. **`common.py:424` interpola `self.end` due volte**: il messaggio annuncia «start date» e
   mostra la data di **fine**. Le due copie sorelle lo fanno giusto, quindi è un refuso. È
   testo d'errore visibile (esce nella 422), quindi non corretto. Il fix è un token.
3. **`ConfigDict(extra="forbid")` ripetuto 316 volte** (216 negli schemi, 100 in AI Export).
   Fattorizzabile con uno `StrictModel` in `common.py` — meccanicamente sicuro, ma tocca
   l'intera superficie dei contratti, inclusi i payload AI Export **versionati**, e ci sono
   7 varianti da gestire una per una.
4. **`_require_positive_int` × 5**: il predicato è identico, divergono eccezione e messaggio.
   Unificare del tutto significherebbe cambiare messaggi d'errore di contratti versionati.
   Via di mezzo proposta: estrarre solo `is_positive_int(value) -> bool` — la parte sottile,
   cioè la trappola `bool ⊂ int` — lasciando a ciascuno il proprio `raise`.
5. **Le due fixture che cancellano tutta `fx_rates`** con commit.

## Due decisioni prese da me, mentre gli agenti lavorano sull'Onda 3

### Il refuso in `DateRangeModel` — corretto

`common.py:424` interpolava `self.end` due volte: chi inviava 31/12 → 01/01 si sentiva dire
«end date (2025-01-01) must be >= start date (2025-01-01)» — una frase che si contraddice e
che nasconde proprio il valore da correggere. Le due copie sorelle lo fanno giusto: è un
refuso, non una scelta, e l'ho corretto senza chiedere perché non cambia struttura né
contratto, solo il numero mostrato.

Il test che c'era asseriva **solo il prefisso** (`match="must be >= start"`), quindi il
refuso gli passava sotto. Ora ce n'è uno che pretende che **entrambe** le date compaiano nel
messaggio: rimesso il refuso, diventa rosso.

Nello stesso file ho trovato e riscritto `test_optional_end`, che era un test **incapace di
fallire**: provava la chiamata dentro un `try/except` che accettava entrambi gli esiti — «se
funziona `end` è opzionale, se fallisce è obbligatorio, e va bene lo stesso». Il campo è
dichiarato `Optional[...] = Field(None, ...)`: una risposta giusta c'è.

### `_require_positive_int` — estratto il predicato, non le funzioni

Ho seguito la via di mezzo che l'agente aveva proposto. Le cinque copie divergono su
eccezione (`TypeError`, `DatasetSpecError`, `error_cls` parametrico, `BuildScopeError`,
`AnalysisSpecError`), su tre formati di messaggio e perfino sul valore di ritorno — e quelle
differenze appartengono a **contratti versionati**, quindi unificare le funzioni avrebbe
significato o trascinarsi cinque formati o cambiare messaggi che i chiamanti vedono.

Quel che è stato estratto è la **parte sottile**, copiata cinque volte identica: che `bool`
è sottoclasse di `int`. `isinstance(True, int)` è `True`, quindi un campo `int` accetta
`True` e memorizza `1` — il refuso di un chiamante che diventa un numero di versione vero,
attaccato a dati veri. Cinque autori se lo sono ricordato; il sesto è quello che preoccupa.

`ai_export/_int_predicates.py` con `is_int_not_bool` e `is_positive_int`; ogni chiamante
tiene il proprio `raise`. 26 test nuovi, registrati in `services ai-export-pure`, che hanno
per soggetto proprio quella trappola — incluso `is_positive_int(True) is False`, che un
predicato basato sulla sola grandezza lascerebbe passare visto che `True >= 1`.

Verifica: 374 test puri verdi, `check-orphans` pulito, lint tornato a **39** (ne avevo
introdotti 5 di ordinamento import, corretti).

## Le fixture che svuotano `fx_rates` — indagate, documentate **nel codice**, non corrette

Ho provato a metterle a posto e mi sono fermato per una ragione precisa, che vale la pena
scrivere perché non è pigrizia.

La purga globale **non è solo igiene: è portante per un'asserzione.**
`test_fx_core.py::test_all_new` dice «No existing data → all rates are new → count = 2» e
conta le righe EUR/USD di oggi e ieri. Se la fixture cancellasse solo le proprie righe, i
tassi ECB del mock su quelle stesse date farebbero fallire il conteggio. Cioè il test *si
appoggia alla demolizione*.

Scoperto provandolo: avevo già scritto la versione scoped (marcatore `FXCORE_TEST` +
`DELETE ... WHERE source = ...`) prima di accorgermene.

La correzione vera è dare a questi test una **coppia di valute che nessun altro tocca**, così
«nessun dato esistente» diventa vero per costruzione invece che per demolizione. `BGN` è
libera: compare solo in una mappa di simboli e in un test di utility, mai come coppia FX.
È un ridisegno delle fixture di **due** file (`test_fx_core.py`, `test_fx_sync_service.py`)
più la riscrittura dell'`assert len(rows) == 2` che oggi regge solo grazie alla purga — e va
verificato senza contendere il database ai due agenti che stanno lavorando adesso.

Quindi per ora il difetto è **documentato dove sta**, nella docstring della fixture: cosa fa,
perché non si può semplicemente restringere, quale sarebbe la cura, e perché non è ancora
esploso (il planner mette in parallelo solo la classe `PURE`, quindi l'esposizione è
cross-categoria — ed è esattamente per questo che si è visto in una corsa `all` a 8 worker e
mai in `services` da sola).

## Onda 3 e chiusura del giro

Gli agenti E2E hanno lavorato sull'area asset (`asset-list`, `asset-detail`, `asset-modal`)
e sono usciti dalla sessione prima di consegnare un report: il lavoro l'ho validato io.
`routes/(app)/assets/+page` è passata da **57,7% a 63,7%**.

Frontend complessivo: **69,94% → 70,31%** statement, **52,62% → 53,37%** branch.

### Gli ultimi due rossi, e cosa erano

La corsa di validazione ha dato 13/15. Entrambi i rossi erano d'ambiente:

1. **`test_sync_auto_config` — `httpx.ReadTimeout`.** Ancora il provider **ECB reale**: è uno
   dei sette punti che avevo segnalato quando abbiamo sostituito il test del weekend. Ho
   esteso a questo file la decisione già presa: i tre usi in cui il provider era solo
   **impalcatura** (auto-config, conversione multi-giorno, e il commento «pairs that ECB
   supports directly») sono passati a `MOCKFX`. Ne resta **uno solo**, ed è giusto che resti:
   la route concatenata `CHF→EUR (SNB) → EUR→USD (ECB)`, dove i provider *sono* il soggetto
   della configurazione.
2. **`test_bulk_refresh_prices_with_min_start` — `database is locked`.** Contesa SQLite a 8
   worker su una scrittura bulk di `price_history`. Non riprodotto nella corsa successiva.

Corsa di conferma dopo la correzione: **15/15**.

# ═══════════════════════════════════════════════════════════════════
# Giro di fattorizzazione (28/08 pomeriggio) — `all` 15/15
# ═══════════════════════════════════════════════════════════════════

## `_require_positive_int` — avevo torto, ora è unificato davvero

La mia motivazione («sono contratti versionati») **non reggeva**, e verificarla ha richiesto
un minuto: `DatasetSpecError`, `AnalysisSpecError`, `BuildScopeError` e `ComponentSpecError`
sono tutte sottoclassi di `ValueError` che dicono *«una dichiarazione è internamente
incoerente»* — vengono sollevate quando l'autore di un plugin scrive male la propria spec,
**non raggiungono mai l'API**, e nessun test ne fissava il testo. Avevo scambiato «versione
del contratto» con «messaggio d'errore del contratto».

Le cinque copie sono quindi diventate una: `require_positive_int(value, field_name, *,
owner_id=None, error_cls=None)` in `ai_export/_int_validation.py`. L'unica varietà tenuta è
quella che un chiamante può ragionevolmente rivolere: **la propria eccezione tipizzata**.
Senza, si ottiene ciò che Python intende — `TypeError` per il tipo sbagliato, `ValueError`
per il valore inutilizzabile — che è anche più informativo di quanto facessero tre delle
cinque. Restituisce sempre il valore (prima tre sì e due no, quindi il chiamante doveva
sapere quale stava guardando).

33 test. Fra questi: che un `bool` è un errore **di tipo** e non di valore — perché `True`
è `1`, e riportarlo come «must be >= 1» manderebbe l'autore a cercare nel posto sbagliato.

## `StrictModel` — 305 classi, una riga sola

`model_config = ConfigDict(extra="forbid")` era ripetuto **316 volte**, e le varianti erano
appena 11 in tutto. Quindi: `StrictModel` in `common.py`, e **305 classi** (205 negli schemi,
100 nell'AI Export) che la estendono invece di ridichiararla. Le 11 varianti restano dove
sono; pydantic fonde `model_config` lungo la catena, quindi chi ha bisogno di `frozen` o
`from_attributes` continua a funzionare **e** resta severo.

Perché conta più di un risparmio di righe: rifiutare i campi sconosciuti è ciò che trasforma
una chiave rinominata o scritta male in un 422 rumoroso invece che in un valore che sparisce
in silenzio. Ripeterla 316 volte è il modo in cui prima o poi la si dimentica proprio sul
modello dove serviva di più. Ereditarla capovolge il default: un modello nuovo è severo, e
deve **rinunciarci** di proposito.

Cinque test la proteggono, incluso quello che nota se qualcuno riportasse `StrictModel` a
`BaseModel` — cosa che allenterebbe trecento contratti in un colpo senza far fallire nulla
altrove.

Due classi esistevano **solo** per portare quella riga (`AiExportModel`, `SignalModel`): sono
rimaste come basi nominate del loro sottosistema, con una docstring che dice perché.

## Le fixture che svuotavano `fx_rates` — risolte, con il tuo permesso sul mock

Il blocco era che la purga globale **era portante**: «no existing data → count = 2» è vero
di EUR/USD solo se qualcuno ha appena demolito la tabella. La via d'uscita è dare a quei
test una coppia loro.

Cercandola ho sbattuto contro un vincolo che non conoscevo: `ck_fx_rates_base_less_than_quote`
impone `base < quote` alfabeticamente, quindi metà delle coppie candidate non è nemmeno
inseribile. La scelta finale è **BGN/ISK** e **CHF/ISK**: nessuna delle due compare altrove
nel progetto come coppia FX, e tutto ciò che il file scrive ha `ISK` come quote, quindi una
sola `WHERE` copre la sua intera impronta. Non è servito aggiungere righe al populate: bastava
smettere di usare le coppie di tutti.

`test_fx_sync_service.py` era peggio — cancellava anche **ogni rotta FX del database**. Ora
le rate sono ripulite per `source == "MOCKFX"` (quel provider gira solo nei test, quindi una
riga ECB o SNB vera non viene mai toccata) e le rotte per le due coppie che il file usa. E
l'`assert len(rows) == 2`, che era un conteggio globale retto solo dalla purga, ora filtra
anche per source.

## Le cripto con sigla di valuta fiat — chiuso

Decisione dell'utente: si accetta la sovrapposizione (`SOL` Nuevo Sol, `ALL` Lek, `XXX`),
perché nel progetto le cripto sono trattate come **asset** e non come valute. Il test che
documenta la collisione resta come nota, non come difetto.

## Pydantic o dataclass nell'AI Export? Entrambi, e la divisione è architetturale

Misurato, non ricordato:

| | classi | dove |
|---|---|---|
| **Modelli pydantic** (ora `StrictModel`) | **101** | tutti in `components/`: `*_payloads.py`, `*_context.py`, `catalog.py` |
| **Dataclass** | **53** | `temporal/` (plan, points, policy, aggregators, uniform), `composer.py`, `datasets/spec.py`, `components/spec.py`, `components/types.py`, `technical_shared.py` |

La linea di separazione non è casuale:

- **Pydantic dove il dato esce.** I payload esportati verso l'AI devono essere validati e
  serializzati, e devono rifiutare i campi sconosciuti — sono un contratto versionato. Sono
  questi i 100 che hanno guadagnato `StrictModel`.
- **Dataclass dove il dato resta dentro.** Piani temporali, punti, policy, aggregatori e le
  *dichiarazioni* di spec sono strutture di lavoro: non vengono serializzate, e passano per
  cicli caldi dove la validazione pydantic a ogni costruzione si pagherebbe senza comprare
  nulla.

Alcuni file hanno entrambi (`portfolio_income.py`, `broker_cost_efficiency.py`): il payload
in pydantic, le strutture d'appoggio in dataclass.

Ed è esattamente per questo che `require_positive_int` serve: è chiamato dai `__post_init__`
delle **dataclass**, dove pydantic non arriva. Se quelle fossero modelli pydantic, la
validazione sarebbe dichiarativa e quella funzione non esisterebbe.

## Stato al 28/08, ore 12:40

`all --workers 8` → **15/15**. Lint **38** (uno sotto la baseline preesistente).
Da committare: **98 file** (87 modificati, 11 nuovi). Messaggio unico pronto in
`/tmp/libreFolio_commit_ALL.txt`, che copre tutto dall'ultimo commit (`603099d2`).

Coverage dall'inizio della campagna:

| | prima | ora |
|---|---|---|
| Backend statement | 87,72% | **91,36%** |
| Backend branch | — (metrica attivata da noi) | **81,40%** |
| Frontend statement | 65,83% | **70,31%** |
| Frontend branch | 49,78% | **53,37%** |

## Lavagna ripulita — cosa resta davvero

Le voci residue degli agenti terminati sono state chiuse o fuse. Restano otto voci:

**Onda 3, ciò che manca**
1. `cover-iwm` — **ImportWizardModal**, 60,1% con 613 statement scoperti, il file più
   scoperto del frontend. Il percorso felice è coperto; mancano parsing fallito, file non
   riconosciuto, righe irrisolte, annullamento a metà, ritorno fra i passi. Attenzione:
   l'import committa transazioni **vere**, quindi serve il `TransactionWriteTracker`.
2. `cover-bulk` — `TransactionBulkModal`, 75,5% / 246 scoperti.
3. `cov-t35` — rotte `fx` (48,4%) e `files` (65,1%) più `FilePreviewModal`.
4. `cov-t12` — rami negativi dei provider (justETF 67%, borsa_italiana 74,8%,
   yahoo_finance 71,4%, snb 65%). Da coprire con risposte mockate, mai con la rete.

**Deduplicazione residua**
5. `dup-translated-or` — traduci-con-fallback sotto tre nomi (`label`/`tr`/`translatedOr`):
   logica i18n copiata tre volte, il candidato più utile.
6. `dup-misc-frontend` — chiave di posizione, numero-finito-o-null, data breve per asse,
   snake→Title, `portal`/`portalAction`, quattro modi di annullare un long-press.

**Decisioni**
7. `decide-unifiedlots-divergences` — in `UnifiedLotsTable`, `firstScalar` salta i `null`
   invece di prendere il primo elemento, e il suo `safeNum` rifiuta `±Infinity` mentre le
   altre copie lo accettano. Cambiano cosa vede l'utente quando un dato manca.
8. `sqlite-lock-bulk-price` — `database is locked` su una scrittura bulk di `price_history`,
   visto una volta a 8 worker e non riprodotto.
