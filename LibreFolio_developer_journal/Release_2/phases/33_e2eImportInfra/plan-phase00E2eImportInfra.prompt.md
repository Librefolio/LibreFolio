# Piano — fase 00, 33: l'infrastruttura dei test E2E dell'import

> **Stato**: ✅ chiuso e integrato nel treno 10: `860c934ac`, `abfcdf2be`, `ffdcacc2f`, `cc15441e6` (verifica del 2026-10-09 su `3cceb4f90`, §8). I difetti A e B di §1.1 li ha chiusi il piano 34; il backlog di §7 è rinviato in `Phase_0/38_postReleaseBacklog/README.md`, voce L11.
> - Al checkpoint: ✅ approvato (2026-10-07), in esecuzione.
>
> - Mandato: coordinatore («Release 2 backlog analysis», `c8328a01-…`). D3 l'ha deciso lui: prima l'infrastruttura; i difetti A e B in un checkpoint a parte, dopo la decisione del developer.
> - Workstream L. Ramo `e-alfy-l-danske-bank`, base `dfd6ed963` (DEGIRO committato, entra nel treno 9 per SHA).
> - Corsia 6156/6166, `--data-dir /tmp/librefolio-r2-l`, un comando alla volta. `--clean` concesso per tutto il lotto.
> - Fuori perimetro finché il developer non decide A e B: `auth.py`, `user_service.py`, `brokers.py`, `broker_service.py`.

## 0. Il mandato

1. **I rossi dell'import nella coverage** su `d07412899`:
   - `tx-brim-import` T1 (`:161`);
   - `tx-import-ca-contract` CAC-011 (`:438`) e CAC-012 (`:481`);
   - `tx-import-report-set` R1 (`:1229`) e A18 (`:1373`);
   - `tx-import-resolution` IWR-001 (`:258`);
   - in più, `tx-import-file-selection` rosso nella mia corsia.

   Verdetti come da `test-triage`.
2. **`populate_mock_data.py`**: concesso; in questo lotto sono l'unico a scriverlo.
   - Con `--force` svuota solo `broker_reports`, e solo sotto la stessa data-dir del DB che cancella.
   - `custom-uploads` continua a svuotarlo solo `--clean`.
3. **Spec**:
   - concessi `tx-brim-import`, `tx-import-ca-contract`, `tx-import-resolution` e i loro helper;
   - se serve, un helper comune in `frontend/e2e/`;
   - `tx-import-report-set` solo se necessario.

   I test li scrive il test-author, e sono rossi prima della correzione.
4. **La verifica in produzione** è fatta nell'analisi (§1.1). Ha trovato due difetti, A e B: mi fermo prima di correggerli.

## 1. Stato verificato (codice a `dfd6ed963`)

### 1.1 La verifica in produzione — ⛔ STOP, al developer — ✅ risolta dal piano 34 (§8)

- **Cancellare un broker dall'app ne cancella i file**, in entrambi i percorsi:
  - `DELETE /brokers` (`brokers.py:372-418`);
  - l'ultimo owner che esce (`:541-567`).

  Tutti e due chiamano `_delete_brim_files_for_brokers` (`:103`): dopo il commit, best-effort, solo i file con il `target_broker_id` uguale.
- **Difetto A — cancellare l'account non cancella i broker.**
  - `DELETE /auth/users/me` (`auth.py` ~276-305) chiama `user_service.delete_user` (`:333-357`), che cancella solo l'utente.
  - Le righe di `broker_user_access` vanno via in cascata (`001_initial.py:148-162`), ma `brokers` non ha una FK verso `users`.
  - Risultato: i broker di cui l'utente era l'unico owner restano senza proprietario, con transazioni e file BRIM, e nessuno può più vederli o cancellarli dall'app.
  - Le docstring dicono il contrario: `auth.py` «Deletes all user data (brokers, transactions, settings)»; `delete_user` «cascades to all brokers owned by the user, all transactions».
- **Difetto B — un buco d'isolamento latente.**
  - `brokers.id INTEGER PRIMARY KEY` non ha AUTOINCREMENT (`001_initial.py:127-141`): se si cancella il broker con l'id più alto, quell'id si riusa.
  - I file si elencano per cartella (`broker_<id>`): un orfano compare nel broker successivo con quell'id, anche se è di un altro utente. Anche `rememberedChoices` (`importReportSets.ts:463`) legge quei file.
  - In produzione un orfano nasce solo così: la pulizia best-effort fallisce, il processo cade fra il commit e la pulizia, oppure si interviene a mano sul DB. Il backup è solo un export, non ripristina.
- **Opzioni proposte**:
  - A: alla cancellazione dell'account, applicare broker per broker la regola «l'ultimo owner che esce»;
  - B: (b1) AUTOINCREMENT, con una migrazione che ricostruisce la tabella; (b2) le cartelle di un broker nuovo vengono svuotate alla creazione, con un avviso nel log; (b3) nascondere i file caricati prima del `created_at` del broker.
  - Consigliate A + b2.

### 1.2 L'infrastruttura dei test

- `populate_mock_data --force` (`:3742-3760`) cancella il file del DB, ma non `broker_reports`.
- `--clean` (`clean_data_dirs`, `:3252`) svuota `broker_reports` **e** `custom-uploads`.
- `--with-reports` (`upload_broker_reports`, `:3427`) ricarica i campioni a ogni invocazione, che quindi si accumulano: nella mia corsia il broker 1 è arrivato a 78 file.
- Ogni invocazione E2E chiama `db_populate(force=True, with_reports=True)` senza `clean` (`_frontend_common.py:163`; `_frontend_transaction.py:315/353/499`). Senza report lo fanno anche `_backend_api.py:610` e `_backend_db.py:254`.
- Quindi i broker dell'invocazione precedente spariscono dal DB, ma i loro file restano. I broker nuovi riprendono gli id 9, 10, … e li ereditano.
- `tx-import-ca-contract` crea un broker e un file a ogni test (`:48-67`, `beforeEach` `:173-177`), e non li cancella mai.

### 1.3 I rossi e i verdetti (skill `test-triage`)

| Rosso | Sintomo | Causa | Verdetto |
|---|---|---|---|
| file-selection (mia corsia) | il broker «control» ha 2 file invece di 1 | un file di CAC su un id riusato | **stato condiviso** (verde da solo sulla corsia pulita) |
| R1 `:1229`, A18 `:1373` (coverage) | «the owned broker holds … nothing else», con 1 file in più | la stessa | **stato condiviso** |
| T1 `:161` | coverage: «no importable file listed»; mia corsia: timeout sul passo 4 | `.first()` su tutti i pannelli (`:74-86`); `isVisible({timeout})`, che non aspetta (`:104-125`) | **assunzione** (posizione, orologio) |
| CAC-011/012 | timeout sul passo 4; snapshot: il wizard è fermo sulle correzioni | `walkToReview` (`:139-151`) e `confirmNotices` (`:126-132`) usano `isVisible({timeout})` | **assunzione** (orologio) |
| IWR-001 `:258` | 90 s di timeout sul click della riga `generic_simple.csv` | la riga è cercata solo nella pagina corrente, e le copie accumulate la spingono oltre | **assunzione** (posizione) |

T1 e CAC-011/012 sono rossi identici anche col wizard di HEAD, sulla corsia pulita (prova del lotto DEGIRO, piano 31, §11.6).

## 2. Il disegno

### 2.1 `populate --force`

- Con `--force`, prima di ricreare il DB, svuotare `broker_reports/{uploaded,parsed,failed}`, sottocartelle comprese.
  - Non `.locks`: un server attivo può tenerli aperti, e sono innocui.
  - Non `custom-uploads`, che resta compito di `--clean`.
- Guardia: si svuota solo se il file del DB sta sotto `get_data_dir()`; altrimenti un avviso, e nessun file toccato.
- Il lavoro sta in una funzione con un nome (`reset_broker_reports(data_dir, db_path)`), che `clean_data_dirs` può riusare per la sua parte.
- Effetto: niente orfani fra un'invocazione e l'altra, e una sola copia di ogni campione con `--with-reports`.

### 2.2 Gli spec

- **Un helper comune** in `frontend/e2e/fixtures/`: dalla verifica dell'analisi alla revisione, leggendo lo stepper (`[aria-current="step"][data-step-id]`), come fa `continueToReview` dello spec DEGIRO.
  - La conferma degli avvisi la decide la risposta del parse, mai una sonda.
  - Le correzioni si accettano in modo deterministico.
- **T1**: un file noto, per nome, nel pannello del suo broker, cercato pagina per pagina (`fixtures/paging.ts`).
- **IWR-001**: `generic_simple.csv` cercato in tutte le pagine.
- **CAC**: usa l'helper comune; un `afterEach` cancella via API, con force, il broker e il file che il test ha creato.
- **R1/A18**: l'asserzione «nient'altro» resta, perché è ciò che il test verifica; li risolve §2.1.

## 3. Superfici

| File | Proprietà | Cosa |
|---|---|---|
| `backend/test_scripts/test_db/populate_mock_data.py` | L, unico scrittore nel lotto | §2.1 |
| un test backend nuovo per §2.1 | test-author | rosso prima |
| `frontend/e2e/fixtures/<helper comune>.ts` (nuovo) | test-author | §2.2 |
| `frontend/e2e/transactions/tx-brim-import.spec.ts`, `tx-import-ca-contract.spec.ts`, `tx-import-resolution.spec.ts` | test-author | §2.2 |
| `frontend/e2e/transactions/tx-import-report-set.spec.ts` | solo se serve | — |
| `LibreFolio_developer_journal/Release_2/Phase_0/31_brimDegiro/…` | L | la nota sul campione LF, in §11.6 |
| questo piano | L | — |

## 4. Passi

1. ✅ Il piano; la nota nel piano DEGIRO.
2. **Prova del rosso** sulla corsia sporca, così com'è, prima di ogni modifica: i quattro spec, uno alla volta.
3. Il test-author, in parallelo:
   - (a) il test backend di §2.1, contro uno stub con la firma definitiva;
   - (b) l'helper comune e gli spec di §2.2.
4. La cura di §2.1, dopo il rosso del test.
5. Gli spec nuovi, prima **sulla corsia sporca**, poi su una pulita dopo §2.1.
6. Gate, privacy, checkpoint.

## 5. Test e gate

- Backend: il test nuovo; `db`/populate; `check-orphans`.
- E2E:
  - i quattro spec, sulla corsia sporca e su quella pulita;
  - poi gli altri spec dell'import che usano i campioni: flow, upload, file-selection, report-set-guide, duplicate-precedence, bulk-import-handoff, degiro.
- Lint, prettier, `git diff --check`, porta libera.
- **Fatto quando**:
  - i sei rossi diventano verdi su una corsia che ha già girato più volte;
  - dopo un'invocazione non restano file di broker inesistenti;
  - ogni campione è caricato una volta sola.

## 6. Avanzamento

### 6.1 ✅ Il piano e la nota DEGIRO (2026-10-07)

> **Note implementazione**: piano creato. Nel piano 31, §11.6, ho registrato la decisione del coordinatore sui fine riga: campione LF, niente `.gitattributes`.

### 6.2 ✅ La prova del rosso sulla corsia sporca (2026-10-07)

> **Note implementazione**: corsia 6156 com'era, prima di ogni modifica.
> - DB con i broker 1–8.
> - Su disco: il broker 1 con 15 file (5 copie dei 3 campioni), i broker 2–5 con 5 ciascuno, orfani sugli id 10–67.
>
> | Spec, uno alla volta (log nella sessione, `files/infra-batch/runs/01-dirty-RED-*`) | Esito |
> |---|---|
> | `tx-brim-import` | **T1 rosso**, 7 non eseguiti (suite seriale) |
> | `tx-import-resolution` | 12 verdi: IWR-001 non si riproduce in questo stato |
> | `tx-import-report-set` | 28 verdi: R1/A18 non si riproducono |
> | `tx-ca-contract` | **CAC-011/012 rossi**, 10 verdi |
>
> IWR-001 e R1/A18 dipendono dallo stato esatto: quante copie ci sono, quali id sono orfani, l'ordine. Le loro cause restano comunque da correggere:
> - IWR-001 viola la regola 1, perché non scorre le pagine;
> - R1/A18 hanno la radice negli orfani, che ricevono un test deterministico a livello di populate (§6.3).

### 6.3 ✅ Stub, registrazione, test-author (2026-10-07)

> **Note implementazione**:
> - `reset_broker_reports(data_dir, db_path) -> int` è nel repo come **stub**, con la firma definitiva.
> - Runner: `db populate-reset` in `scripts/test_runner/_backend_db.py`, cioè funzione, registrazione e posto in `db all`, dopo `populate`. Solo la mia voce.
> - Due test-author in parallelo, su file distinti; nessuno dei due esegue test, li lancio io:
>   - (a) `test_populate_reset.py`, rosso contro lo stub;
>   - (b) l'helper comune `frontend/e2e/fixtures/import-wizard.ts` e i tre spec.
>
> **⚠️ Fuori pista — c'è già un precedente nel runner**: `db create` (`_backend_db.py:34-67`, `_reset_test_file_store`) svuota già `broker_reports` e `custom-uploads` quando ricrea il DB. La docstring descrive questo stesso problema: 308 cartelle di broker, 182 copie di `generic_simple.csv`, «a previous run's broker silently impersonating a current one».
> - `populate --force` cancella il DB dentro `populate_mock_data.py` e scavalca quella pulizia.
> - La cura va in `populate`, come ha deciso il coordinatore: solo `broker_reports`, non `custom-uploads`. Non si importa il runner da uno script del backend.
> - La guardia confronta i percorsi **risolti**: su macOS `/tmp` è un link a `/private/tmp`.

### 6.4 ✅ `populate --force`: rosso, poi verde (2026-10-07)

> **Note implementazione** — il rosso (test-author): `backend/test_scripts/test_db/test_populate_reset.py`, 21 funzioni, 25 casi.
> - Un fixture autouse sposta `get_data_dir()` in una sandbox con un canarino: un'implementazione che ignorasse il suo argomento non potrebbe mai toccare la corsia vera.
> - Una «barriera» nei test «tiene X»: lo stub, che non fa niente, non li passa per la ragione sbagliata.
> - Contro lo stub: **21 rossi, 4 guardie verdi**. I 21 rossi sono tutti `AssertionError`, 8 sulla barriera; nessuno al setup.
>
> La cura (`populate_mock_data.py`):
> - `reset_broker_reports(data_dir, db_path)`:
>   - svuota `uploaded`, `parsed` e `failed`, sottocartelle comprese;
>   - lascia stare `.locks`, `custom-uploads`, il DB e il resto;
>   - non fa niente se il DB, risolto, non sta sotto la data-dir risolta, e allo stesso modo salta una cartella di stato che porta fuori;
>   - un link si toglie come link, senza seguirlo;
>   - restituisce i file tolti.
> - In `main()`: con `--force` si chiama dopo la cancellazione del DB, che il DB esistesse o no. Il testo d'aiuto di `--force` lo dice.
> - `db populate-reset`: **25 verdi**. Ruff e black puliti (il file era pulito anche a HEAD).
>
> **⚠️ Fuori pista — l'ordine dei passi**: con la cura attiva, ogni invocazione E2E pulisce la corsia all'avvio. Per provare gli spec nuovi sulla corsia sporca (§4.5) tolgo per un momento la sola chiamata in `main()`, poi la rimetto: la stessa prova del rosso fatta per P4 nel lotto DEGIRO. La corsia adesso ha 136 file BRIM, di cui 48 orfani, e 32 sul broker 1.

### 6.5 ✅ Gli spec riscritti, prima sulla corsia sporca (2026-10-07)

> **Note implementazione** — test-author: un helper comune nuovo, `frontend/e2e/fixtures/import-wizard.ts`.
> - `uploadOwnedReport` / `deleteOwnedReports`: il test carica la sua copia del campione sul broker giusto, cercato per nome via API, e la cancella alla fine.
> - `selectBrokerFile`: apre il pannello se è chiuso, scorre le pagine (`findAcrossPages`), sceglie il file per id; se non lo trova, fallisce dicendo quante pagine ha visto.
> - `parseSelectedFile`: tiene la risposta del parse.
> - `continueToStep` / `continueToReview`: seguono lo stepper; gli avvisi si confermano solo se il parse ne ha.
>
> Gli spec:
> - `tx-brim-import`: copia propria di `ibkr-trades-export.csv` su «Interactive Brokers», scelta per id; via `selectFirstAvailableFile`, `continueToReview` e `passOptionalWizardSteps`.
>   - T5: i duplicati si calcolano sul broker del file, quindi la copia propria dà gli stessi verdetti.
>   - T1: l'Import passa solo le righe all'editor e non salva niente.
> - `tx-import-ca-contract`:
>   - il broker creato si cerca per nome, non con `results[0]`;
>   - un `afterEach` cancella via API, con force, i broker del test (anche il «late» di CAC-012), e controlla che ogni file caricato risponda poi **404**: l'affermazione di §1.1 diventa un'asserzione a ogni test;
>   - via le sonde di `confirmNotices`, `walkToReview` e `goToFixStep`.
> - `tx-import-resolution`: copia propria di `generic_simple.csv`, cercata per id in tutte le pagine; via i due Escape, che chiudevano il wizard; `goToStep4WithGenericSimple` usa l'helper comune.
>
> | Corsia sporca, la sola chiamata del reset tolta per la prova (log `files/infra-batch/runs/04-dirty-NEW-*`) | Esito |
> |---|---|
> | `tx-brim-import` | **8 verdi** (prima T1 rosso) |
> | `tx-import-resolution` | **12 verdi** |
> | `tx-import-report-set` (spec non toccato) | **R1 rosso**: «the owned broker holds the set of this upload and nothing else», 1 file in più sul broker 9. È l'orfano ereditato: lo stato condiviso, finalmente riprodotto. |
> | `tx-ca-contract` | **12 verdi** (prima CAC-011/012 rossi) |
>
> Dopo il giro la corsia aveva 181 file BRIM, 45 orfani e 50 sul broker 1. Il file `populate` è stato rimesso e verificato identico alla copia, con la chiamata presente.

### 6.6 ✅ Con la cura attiva, senza `--clean` (2026-10-07)

> **Note implementazione**:
> - La corsia sporca si pulisce da sola alla prima invocazione: da 181 file e 45 orfani a **8 file, 0 orfani, 3 sul broker 1**, cioè una copia di ogni campione. Resta così dopo ogni invocazione (`Broker reports reset: 16 file(s) removed`).
> - I quattro spec: report-set **28** (R1 compreso), brim-import **8**, resolution **12**, CAC **12**.
> - Gate, uno alla volta, tutti verdi:
>   - import-flow 10, import-upload 9, file-selection 2, report-set-guide 2, duplicate-precedence 6, bulk-import-handoff 2, degiro 4, import-matching 6, asset-identity 9, asset-inspector 5;
>   - `api brim` 79, `db populate-reset` 25, `check-orphans` pulito.
> - Dopo `api brim` restano 31 file, tutti su broker ancora vivi: i test API lasciano i loro broker, e il `populate --force` successivo azzera insieme DB e file. Nessun orfano vero.

### 6.7 ✅ Il rosso del treno 9: `core-unit` (2026-10-07)

> **Note implementazione**: `optionFilter.test.ts` › ranking › «on the real import-plugin list (R13)».
> - Errore: `broker_degiro.py, description: expected exactly one definition, found 2`.
> - Causa: `returnedLiteral` cerca la proprietà in tutto il file, e DEGIRO ha anche `_Row.description`.
> - Verdetto del coordinatore: assunzione del test; il plugin è giusto.
> - Rosso confermato sulla 6156 (`front-utility core-unit`: 1 file fallito su 115).
> - Correzione affidata al test-author: si legge solo il corpo della classe con `@register_provider(...)`, con uno stop esplicito se è zero o più di una; l'intento di R13 non cambia.
> - Da ora `core-unit` è fra i miei controlli.
> - La correzione (test-author): `registeredClassBody(source, file)` tiene solo il corpo della classe con `@register_provider(...)`.
>   - Stop espliciti: il decoratore manca, è ripetuto o è rientrato; dopo non c'è l'intestazione `class` su una riga.
>   - `returnedLiteral`, col suo stop, è identico byte per byte.
>   - Verificati tutti i 31 `broker_*.py`: un decoratore a colonna 0, classe su una riga, le tre proprietà dentro.
> - **`core-unit` 115/115 file, 3400 test**; `front check` 0/0; `front build --debug`.
>
> | Gate finali del lotto | Esito |
> |---|---|
> | ruff e black: `populate_mock_data.py`, `test_populate_reset.py` | puliti |
> | ruff e black: `scripts/test_runner/_backend_db.py` | stesso stato di HEAD (3 errori ruff e il formato black c'erano già) |
> | prettier: helper, tre spec, `optionFilter.test.ts` | puliti |
> | `git diff --check`; porte 6156 e 6166 | pulito; libere |

## 7. Backlog (per il coordinatore): violazioni viste e lasciate, fuori dal perimetro

Elenco del test-author, file:riga sulla versione nuova:
- **Rischi**:
  - IWR-005 `:381` / IWR-006 `:461` salvano `identifier_ticker="UNETF"` su un asset reale e non lo ripristinano (regola 8): IWR-001..004 perdono la premessa «irrisolto» nel progetto mobile;
  - IWR-010 `:634` prende la prima `row-actions` senza filtro (regola 1);
  - l'apertura del wizard (brim `:57/:68`, CAC `:136/:145`, IWR `:84/:95`): prima riga della tabella senza filtro, sonda su `formClose`.
- **`tx-brim-import`**:
  - T1 `:159`, con `isEnabled()` letto una volta sola;
  - T2 `:177`, testo tradotto;
  - T3/T4 `:199-236`, testo, classi CSS e sonde: possono passare senza fare niente;
  - T5 `:255-258` non controlla niente;
  - T8 `:308`, una sonda;
  - l'intestazione è disallineata.
- **`tx-import-ca-contract`**:
  - CAC-001 `:210`, con la sonda dell'evidenza;
  - CAC-006/007 `:313-366`;
  - CAC-009/010 `:419/:439`, `waitForTimeout` (serve un segnale «ricontrollo finito»);
  - sonde in CAC-011/012 `:457-513`.
- **`tx-import-resolution`**:
  - `skipStepIfPresent` (IWR-007/011);
  - classi CSS a `:161/:262/:355/:387/:391/:419/:514`;
  - sonde a `:166/:194-226/:340-345/:421-463`;
  - prima opzione senza filtro a `:203/:208/:332/:374/:442/:449`;
  - IWR-007 e IWR-006 non verificano niente;
  - IWR-009 non cancella il suo broker;
  - `resolveFirstAssetManually` non è usata;
  - l'intestazione è disallineata.
- `tx-brim-import` resta in `mode: 'serial'`, perché toglierlo tocca le liste d'eccezione in `playwright.config.ts` e nelle istruzioni: decide il coordinatore.

## 8. ✅ Integrazione e verifica finale (2026-10-09)

> **Note implementazione**:
> - **I commit**, integrati nel treno 10 (2026-10-07):
>   - `860c934ac` test(db): populate --force resets broker reports;
>   - `abfcdf2be` test(e2e): import specs own their files;
>   - `ffdcacc2f` test(select): scope R13 scrape to provider class;
>   - `cc15441e6` docs(journal): plan 33, e2e import infra.
> - **La verifica in produzione di §1.1** (difetti A e B) è diventata il piano 34 (`34_accountAndIdReuse/`): A con `6b66ee306`, B con gli id mai riusati e il fix all'avvio, `298ed96f3` (treno 12).
> - **Verifica** su `3cceb4f90`: `populate --force` svuota `broker_reports` della propria data-dir (`reset_broker_reports`, `populate_mock_data.py:3323`); gli spec d'import cancellano i broker che creano (`afterEach`).
> - **Il backlog di §7 è ancora aperto** sul codice. Per esempio:
>   - le sonde su `formClose` in `tx-brim-import.spec.ts:67-69` e `tx-import-ca-contract.spec.ts:144-146`;
>   - `waitForTimeout` in `tx-import-ca-contract.spec.ts:419` e `:439`;
>   - `mode: 'serial'` in `tx-brim-import.spec.ts:104`.
>   - Rinviato: `Phase_0/38_postReleaseBacklog/README.md`, voce L11.
> - **Classificazione: FINITA.** L'unico residuo è la voce L11. Archiviata in `Release_2/phases/33_e2eImportInfra/`.
