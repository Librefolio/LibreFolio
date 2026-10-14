# S4 — piano di esecuzione · L4 «Cosa succede se…?»

| | |
|---|---|
| Mandato | `../S4-livello-4.md` (sola lettura) |
| Branch | `e-alfy-h-monte-carlo` (sessione H del round 1, riusata) |
| Baseline | `7d75a9c6c283af4bccf11f6bf380ffaa701d53eb` ✅ verificata, albero pulito |
| Lane | porta `6156` · data dir `/tmp/librefolio-r2-s4` |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |
| Analisi | consegnata prima di qualunque codice; autorizzazione del developer via approvazione del piano |

> ⚠️ **Questo file è il punto di ripristino.** Il brief è in sola lettura: se deve
> cambiare, lo cambia il coordinatore.

---

## Lo scopo, in una riga

Il briefing elogia L4 per un selettore delle modalità **che non esiste**. Il frontend
cabla `process: 'gbm'`, quindi **l'intera consegna del round 1 di H — il block bootstrap
reso default a livello di contratto — è irraggiungibile dalla UI.** S4 non abbellisce L4:
gli collega il motore che già ha.

---

## Le tre misure che orientano tutto il resto

| # | misura | comando | esito |
|---|---|---|---|
| 1 | usi di `risk.simulation.mode.*` | `grep -rn` su `src/` escluso `i18n/` | **0** → 52 stringhe morte in 4 lingue |
| 2 | `process: 'gbm'` cablato | `riskRequest.ts:168` | **1**, senza alcun campo di stato che possa sostituirlo |
| 3 | `bootstrap_seed` letto da `result.output` | `simulationProvenance.ts` | sta in `RiskResultMetadata` → la riga «Seed» **non si rende mai** |

📌 Il difetto 3 è l'unico che `api sync` *sembrava* poter riparare. Non poteva: il campo
non mancava, stava a un **altro indirizzo**.

---

## Passi

- [x] **0. Piano vivo** — ✅ 2026-09-18
  > **Note implementazione**: questo file, creato prima di qualunque riga di codice,
  > secondo `_comune.md` §59. Nominato esplicitamente in ogni handoff.

- [x] **1. Selettore delle modalità** in `L4Simulation.svelte` — ✅ 2026-09-18
  > **Note implementazione**: `<fieldset data-testid="risk-simulation-modes">` con cinque
  > `<label data-testid="risk-simulation-mode">`, ciascuna con `data-mode-id`,
  > `data-selected`, badge «avanzato» e **ipotesi inline** (`risk-simulation-mode-hypothesis`).
  > Tabella in `simulationModes.ts`: **l'`id` della modalità *è* la chiave i18n**, non una
  > chiave mappata. Una mappa id→chiave sarebbe una seconda tabella che può divergere, e una
  > ricerca mancata renderebbe la chiave grezza **nel posto dove dovrebbe stare l'ipotesi**.
  > Realizza strutturalmente il `regime === 'none' ? mode[process] : mode[regime]` di K6 §8.
  >
  > **Campionamento assente, non disabilitato** (`showSampling = spec.process === 'gbm'`):
  > sotto un ricampionatore il metodo di campionamento non è «predefinito a mc», è **privo
  > di significato**. Un controllo disabilitato dice «puoi averlo, non ora»; l'assenza dice
  > la verità.
  >
  > **Combinazione invalida irrappresentabile**: la tabella a 5 righe non può esprimere
  > `gbm + regime`, e il ramo parametrico del builder emette `regime: 'none'` **letterale**
  > invece di inoltrare `state.regime` — così nemmeno uno stato malformato la mette sul filo.

- [x] **2. De-cablare `process`** in `riskRequest.ts` — ✅ 2026-09-18
  > **Note implementazione**: `buildSimulationParameters` riscritta a **due rami**, perché i
  > due motori prendono insiemi di parametri **disgiunti** (`simulation.py:149-169`), non un
  > insieme comune con qualche opzionale. `SimulationEditorState` guadagna `process` e `regime`.
  >
  > **⚠️ Fuori pista**: il file ha **8 importatori** e S3 vuole `buildBaseAnalytics` nello
  > stesso file. Il coordinatore mi ha ristretto a **due simboli soli**. Ho tipato i campi
  > nuovi con `z.infer<typeof schemas.…>` inline per non uscire dall'intervallo concesso.
  >
  > **⚠️ Fuori pista**: `RiskAnalysisPanel.svelte` (pannello legacy) non compilava più.
  > Fissato a `process:'gbm', regime:'none'` con motivazione: `_infer_process:118-138`
  > documenta che i chiamanti anteriori al ricampionatore **restano su GBM di proposito**,
  > perché rendono ancora una didascalia lognormale fissa. Verificato che `:1057-1058` rende
  > `risk.simulation.assumptions` e ha **0** `SimulationProvenance`: è letteralmente quel caso.

- [x] **3. Indirizzo del seme** in `simulationProvenance.ts` — ✅ 2026-09-18
  > **Note implementazione**: nuova `simulationSeed()` che legge da **`metadata`**, con
  > ripiego `bootstrap_seed` → `random_seed`. `sobol_start_index` **deliberatamente non
  > letto**: è un punto d'ingresso in una successione a bassa discrepanza, non un seme.
  > Il test unitario passava perché iniettava il campo dove il codice **già guardava**.

- [x] **4. Catalogo provenance ×4 lingue** — ✅ 2026-09-18
  > **Note implementazione**: differenza insiemistica ricalcolata sul codice: **6 mancanti,
  > 0 morti** (l'analisi ne aveva stimati 7). `none` è **escluso di proposito**: la voce
  > regime richiede `regime_declared_days`, che il backend rifiuta su `none` → non potrebbe
  > mai rendersi. Aggiungerlo creerebbe la **prima voce morta** e distruggerebbe l'invariante
  > asseribile «0 mancanti / 0 morti».
  >
  > **⚠️ Fuori pista**: `valueLabel` ha un ripiego deliberato sul valore grezzo
  > (`SimulationProvenance.svelte:33`), quindi **nessun test «si rende?» poteva fallire**.
  > Il catalogo era fermo al mondo pre-H e nulla lo segnalava.

- [x] **5. Test di provenance + nuovi test** — ✅ 2026-09-18 (delegato a `test-author`)
  > **Note implementazione**: `'crisis'` → `'prolonged_crisis'` ×5, fixture del seme spostato
  > da `output` a `metadata`, titolo `describe` obsoleto corretto. Due file nuovi:
  > `simulationModes.test.ts` (13) e `simulationParameters.test.ts` (21).
  > **56 test passati** su 3 file; `front check` 0 errori; file di produzione invariati per SHA-256.
  >
  > 🔑 **Fixture derivate dagli schemi Zod generati**, `schemas.RiskAnalyticResult.parse(...)`,
  > **senza cast**. Era la richiesta che contava: ogni difetto trovato in questo mandato era
  > passato sotto test verdi che costruivano l'output a mano — e un fixture a mano **non può
  > falsificare un'assunzione su dove vive un campo**, può solo confermarla.
  >
  > ✅ **Mutation testing eseguito, non dichiarato**: rimettendo il seme su `output`, il file
  > **vecchio** resta `12 passed` (verde contro codice rotto), il **nuovo** va `4 failed | 18 passed`.
  >
  > **⚠️ Fuori pista**: `dev.py test check-orphans` → **2 orfani**. La registrazione sta in
  > `scripts/test_runner/_frontend_portfolio.py:117` e `:212`, **del mandato A**. Finché non
  > atterra, **34 test nuovi non girano in CI**.

- [x] **6. `SingleDatePicker` ×2** in `L4Replay.svelte` — ✅ 2026-09-18
  > **Note implementazione**: `type="date"` → **0**. Stile **misurato, non scelto**:
  > `TransactionFormModal:1561` è il caso della riga densa (didascalia esterna + `label=""`),
  > `BrokerForm:270` quello del campo isolato (etichetta interna). Il mio è il primo, accanto
  > a un `SimpleSelect compact` → `compact`. `<label>` → `<div>`: un `<label>` deve puntare a
  > **un** controllo, e il picker è bottone + input.
  >
  > **⚠️ `testid` esplicito obbligatorio**: `SingleDatePicker:359` scrive `data-testid={testid}`,
  > **non** `{tid}`. Il ripiego interno (`:81`) alimenta trigger e popover, **non l'input**.
  > Senza `testid` esplicito l'attributo sparisce e le due E2E di S1 morirebbero in silenzio.
  >
  > **⚠️ Fuori pista — cambiamento di comportamento dichiarato**: `allowFuture` default `false`,
  > mentre il vecchio `<input type="date">` non aveva `max`. Prima si poteva digitare una data
  > futura in un replay storico. È una correzione, ma è **osservabile** → materia da `CHANGELOG.md`.
- [x] **6b. Riparazione del validatore dei metadati** — ✅ 2026-09-18 (assegnata dal coordinatore)
  > **Note implementazione**: `schemas/risk.py`, **solo il blocco `sampling_method`**. Il ramo
  > MC copriva **un** motore e ne esistono **due**: il parametrico estrae le normali da
  > `random_seed`; il bootstrap ricampiona la storia sotto `bootstrap_seed` e ha `random_seed`
  > **vietato** da `SimulationParams` stesso. Il validatore lo **pretendeva** → il default del
  > prodotto non era descrivibile dal proprio modello di metadati.
  >
  > 🔑 **Discriminante scelto e motivato**: i metadati **non portano `process`** (i campi a
  > `:498-502` sono solo i cinque di simulazione; il `process` a `:987` è di un altro modello).
  > Ma non serve: il validatore dei params rende i tre semi **mutuamente esclusivi**, quindi
  > *quale seme è presente* **è** il processo, codificato. Non è una deduzione: è una biiezione
  > che un altro validatore già impone.
  >
  > **Secondo buco, simmetrico, trovato dal quarto caso della sonda**: la guardia
  > `sampling_method is None` elencava `path_count`, `random_seed`, `sobol_start_index` e
  > **non `bootstrap_seed`** → un seme orfano passava senza metodo dichiarato, cioè un campo
  > di disclosure **non falsificabile**. Aggiunto.
  > ⚠️ **Irraggiungibile dalla produzione oggi** (sotto bootstrap `sampling_method` è forzato a
  > `mc`): è difesa in profondità, **non un guadagno da CHANGELOG**. Lo dichiaro per non
  > ripetere il caso `INVALID_COVARIANCE` del round 1, dove un ramo irraggiungibile stava per
  > essere scritto come beneficio.
  >
  > **⚠️ Fuori pista — il DB della corsia non era popolato**: `api risk` è caduto **nella
  > fixture**, non in un test (3 failed / 8 passed, e due dei tre erano preesistenti).
  > Rosso d'infrastruttura. Risolto con `db populate --force` sulla **mia** data dir.
  >
  > **⚠️ Fuori pista — la mia prima asserzione era inventata**: avevo scritto
  > `status == "ok"` e il prodotto risponde `partial`. `partial` nasce da warning, esclusioni
  > e qualità dei dati (`service.py:770`): è una proprietà del **portafoglio di fixture**, non
  > della mia modifica. **Sarebbe stato un rosso falso su un prodotto corretto** — lo stesso
  > errore che questa campagna insegue da due giorni, commesso da me nell'atto di chiuderlo.
  > Corretto in **uguaglianza fra i tre dialetti**, che resta onesta se le fixture cambiano.

- [x] **6c. Il caso mancante nella suite** — ✅ 2026-09-18
  > **Note implementazione**: `test_risk_query_simulates_with_canonical_names_and_no_seed` in
  > `test_api/test_risk_api.py`, autorizzato dal coordinatore. **I due controlli viaggiano
  > nella stessa query del soggetto**: un soggetto solo che risponde 200 prova solo che non
  > ha sollevato; condividere portafoglio, finestra e risposta con due dialetti noti-buoni è
  > ciò che rende il suo esito **confrontabile**.
  >
  > **Prova per mutazione, eseguita non dichiarata**:
  > · con la correzione → **11 passed in 12,14 s**
  > · rimettendo il ramo vecchio → **1 failed, 10 passed**, e il rosso è
  >   `ValidationError: MC metadata requires random_seed and forbids sobol_start_index`
  >   a `service.py:833`, attraverso il middleware d'errore di Starlette → **il 500**.
  > · **i due controlli restano verdi nella corsa mutata** → il test **discrimina**,
  >   non è verde per costruzione.
  > File di produzione ripristinato e verificato per SHA-256 (`0417503b…`), identico.
  >
  > Selettore **già in catalogo**: `api risk` (`_backend_api.py:696`) → **nessuna richiesta ad A**.

- [x] **7. Primitive — inventario** — ✅ 2026-09-18 (**raccolta**, nessuna costruzione)
  > **Note implementazione**: la domanda **D-S4-1 era la domanda sbagliata**, e la misura la
  > dissolve invece di rispondervi.
  >
  > **① Nessuna primitiva bottone/chip esiste.** `ui/` contiene `display/`, `input/`,
  > `toolbar/`, `select/`, `date/`… e **nessun `Button.svelte`, `Chip.svelte`, `NumberInput`**.
  > `PRIMITIVE.md` non ne elencava perché **non ce ne sono**. Adottarne una è impossibile.
  >
  > **② 🔴 Ma esiste un *token*, e L4 lo scavalca.** `app.css:16-25` definisce
  > `--color-primary-50…900`: è un **verde scuro** (`#1a4031`, `#173a2c`). I tre bottoni
  > d'azione di L4 sono `bg-blue-600` = **`#2563eb`**, un blu.
  >
  > **`bg-blue-600` compare in 4 file dell'intero frontend, e 3 sono di L4** — l'unico altro
  > è `ImportWizardModal.svelte`. Non è una sfumatura: **L4 rende bottoni blu in
  > un'applicazione verde.** Il reclamo del developer è **letteralmente vero e misurabile**,
  > e **non riguarda un componente mancante: riguarda un token presente e ignorato.**
  >
  > **⚠️ Fuori pista — l'ho propagato io.** Il mio selettore nuovo (`:138`) usa
  > `border-blue-500 bg-blue-50`, perché **ho copiato le chip di `L4Shock`**, cioè ho misurato
  > lo stile di casa nella stanza sbagliata.
  >
  > 🔑 **«Misura lo stile di casa» fallisce quando la stanza che misuri è la stanza sbagliata.**
  > Col `SingleDatePicker` ha funzionato perché il campione (`TransactionFormModal`) stava
  > **fuori** da L4. Qui il vicino *era* il difetto, e allinearmi al vicino l'ha **moltiplicato**.
  >
  > **Inventario grezzo**: `L4Shock` 3 bottoni + 1 `<input>` a mano (`:141`) · `L4Replay` 3 ·
  > `L4Simulation` 1 + radio + 3 `<input type="number">` · `TornadoChart` 0.
  >
  > **⚠️ Fuori pista — la mia prima raccomandazione era sbagliata, e l'ho ritirata da solo.**
  > Avevo proposto `bg-blue-600` → **`bg-primary-600`**. Falso: le uniche 2 occorrenze di
  > `bg-primary-` sono **`hover:`**, e il fondo vero è **`bg-libre-green`**.
  >
  > ```
  > bg-libre-green :  307 occorrenze  in  87 file    ← l'idioma di casa
  > bg-blue-600    :    4 occorrenze  in   4 file    ← 3 sono L4
  > ```
  >
  > `--color-libre-green` è un token **di marca**, non di ruolo: `#1a4031` in chiaro
  > (`app.css:9`), **`#00d681` in scuro** (`:132`), con regola dedicata a `:274`.
  > → **Il difetto è doppio**: tinta sbagliata, **e** nessuna seconda tinta. `bg-blue-600` è
  > statico mentre il token di casa cambia col tema.
  >
  > 🔑 **Perché il primo grep ha mancato**: ho cercato il nome del **ruolo** (`primary`) e il
  > progetto usa il nome del **marchio** (`libre-green`). Il fallimento è **silenzioso e
  > plausibile** — `--color-primary-*` esiste, è verde, ed è a due occorrenze dal sembrare «il
  > token giusto poco usato». Avevo una risposta coerente, verificabile e sbagliata.
  > **Terza volta oggi**: *trovare qualcosa fa smettere di cercare.*
  >
  > **Idioma bersaglio, misurato in tre punti fuori da L4** (per non ripetere l'errore di
  > misurare la stanza sbagliata):
  >
  > | fonte | forma |
  > |---|---|
  > | `SettingTheme.svelte:65` **← analogo più vicino** (opzione selezionabile in pannello) | sel. `border-libre-green bg-libre-green/10 dark:bg-libre-green/20 text-libre-green dark:text-green-400` · non sel. `border-gray-300 dark:border-slate-600 text-gray-600` |
  > | `FxProviderSelect.svelte:569` | `border-libre-green bg-libre-green/5 text-libre-green` |
  > | `TabBar.svelte:95` | `text-libre-green border-libre-green bg-libre-green/5 dark:…` |
  > | bottone d'azione (`AskAdminModal:73`, `UpdateAvailableModal:67`) | `bg-libre-green text-white hover:bg-primary-600` |
  >
  > 📌 L'idioma di casa usa il **modificatore alfa** (`/10`, `/20`) invece di una tinta
  > separata: funziona in entrambi i temi **perché il colore base cambia**. Il mio
  > `bg-blue-50` + `dark:bg-blue-900/30` fa a mano ciò che il token fa da sé.
  >
  > **Stato**: nessuna modifica applicata. In attesa del via del coordinatore su D-S4-1.

- [x] **8. Avanzamento — misura delle fasi** — ✅ 2026-09-18 (**misura**; la forma resta a D-S4-3)
  > **Note implementazione**: misurato **direttamente sul motore**, in processo, senza server
  > e senza consumare una corsa di corsia (`/tmp/libreFolio_s4_timings.py`).
  >
  > | caso | dentro il ciclo a chunk | fuori (campionamento) | totale |
  > |---|---:|---:|---:|
  > | 250×5, h365, 8 192 path | **97,1 %** | 2,9 % | 158 ms |
  > | 250×5, h30, 256 path | 74,1 % | 25,9 % | **0,7 ms** |
  > | 1000×20, h365, 50 000 path | **99,2 %** | 0,8 % | 3 028 ms |
  >
  > ✅ **La mia riserva del round 1 è falsificata dalla misura.** Avevo dichiarato criterio
  > d'accettazione che «un contatore di path resterebbe a 0 % durante il campionamento fuori
  > ciclo». Quella quota è **0,8-2,9 %** per lavori grandi abbastanza da volere una barra, e
  > **si restringe al crescere del lavoro** — cioè proprio quando la barra serve. L'unico caso
  > col 25,9 % fuori ciclo dura **0,7 ms**: nessuno gli guarda una barra.
  >
  > **🔴 Il pericolo vero è un altro, e il nome del campo lo invita**:
  > `generation_evolution_seconds` è **cablato a `0.0`** per il bootstrap
  > (`resampling.py:198`). È una fase QuantLib che in questo motore **non esiste**. Chi
  > costruisse il canale di avanzamento cercherebbe esattamente quel nome — «generazione dei
  > cammini» — e otterrebbe **una barra ferma a 0 % per sempre**, con un campo che *sembra*
  > una misura e invece è una **costante letterale**.
  >
  > Le due fasi reali (`process_evolution` + `path_aggregation`) sono **entrambe dentro** il
  > ciclo a `:172`, quindi un gancio al confine di chunk le copre tutte e due. Costo dominante:
  > **`path_aggregation` al 90 %** su lavori grandi, non il ricampionamento.

- [x] **9. Cancelli** e `FROZEN` — ✅ 2026-09-18

  **Colore — l'ultima modifica, autorizzata dopo il passo 7**

  > **Note implementazione**: `bg-blue-600` → `bg-libre-green` su **3 file** di `levels/l4/`
  > (`L4Simulation.svelte:193`, `L4Shock.svelte:154`, `L4Replay.svelte:165`). Dopo la
  > modifica, **zero occorrenze di `blue` in tutti e quattro** i file del livello.
  >
  > ⚠️ **Le chip `bg-blue-50` non sono state tradotte «per simmetria»**: il verde di casa è
  > **scuro** (`#1a4031`), `text-white` ci sta sopra ma un fondo pallido no. Il campione
  > canonico misurato **fuori da L4** (`SettingTheme.svelte:65`) usa
  > `bg-libre-green/10 dark:bg-libre-green/20` con testo verde — forma diversa, fuori
  > perimetro di questo reclamo.

  **Esiti dei cancelli — comandi ed esiti, non «verde»**

  | cancello | comando | esito |
  |---|---|---|
  | lint backend | `ruff check` sui 2 file backend | **All checks passed** |
  | formato backend | `black --check` sui 2 file backend | **2 files unchanged** |
  | formato frontend | `npx prettier --check` sui file toccati | **All matched files use Prettier code style** |
  | tipi frontend | `dev.py front check` | **0 errori**, 41 avvisi in 2 file **non miei** (baseline nota) |
  | unità frontend | `cd frontend && npx vitest run` | **4 998 passati, 1 fallito** — *estraneo*, diagnosticato sotto |
  | servizi | `services risk-all` (corsia 6156) | **400 passed in 33,52 s** |
  | API | `api risk` (corsia 6156) | **11 passed in 12,73 s** |
  | i18n | `dev.py i18n audit` | **2 886 chiavi, 2 886 complete, 0 incomplete, 0 backend mancanti**; 122 inutilizzate, **nessuna `risk.*`** |
  | porta | `lsof -nP -iTCP:6156 -sTCP:LISTEN` | **libera, nessun listener** |

  > **⚠️ Fuori pista — `services risk-all` spopola il DB di corsia.** `api risk` era passato
  > **11/11**; dopo `services risk-all` la stessa suite è tornata **3 failed / 8 passed in
  > 2,00 s** con la firma delle fixture assenti (`user 'e2e_test_user' is missing`). Entrambe
  > le corse dei servizi si chiudono con `Test DB snapshot → 00_archive/…`.
  >
  > **Non è un rosso di prodotto: è un rosso d'infrastruttura prima di pytest.** Due dei tre
  > falliti sono test preesistenti che pure vogliono le fixture. Risolto con
  > `db populate --force` e rieseguito → **11 passed**. **Vincolo d'ordine fra cancelli**:
  > `api risk` va eseguito **prima** di `services risk-all`, oppure **dopo un ripopolamento**.
  > Chi li eseguisse nell'ordine ovvio leggerebbe un rosso e cercherebbe il difetto nel codice.

  > **⚠️ Fuori pista — il rosso vitest è estraneo, e lo è perché il prodotto è migliorato.**
  > `riskStore.test.ts` › *«cannot yet express an asset slice in the request key — the schema
  > strips it»* pretende che `makeRiskRequestKey(scoped([2,4]))` sia **uguale** a
  > `scoped([2,5])`. Lo schema Zod generato porta ora `asset_ids?` sullo scope di portafoglio
  > (`generated.ts:8585`), quindi la chiave **li distingue**. **Il test documentava un'assenza
  > che nel frattempo è stata colmata.** Il mio diff non tocca né `asset_ids` né
  > `makeRiskRequestKey` (grep vuoto); la mia modifica a quel file è **+6/-0**, sole fixture.
  > Correzione di una riga (`.not.toBe`) di competenza del proprietario della fetta di asset.

  > **⚠️ Fuori pista — l'inciampo dell'`edit`, seconda volta.** Il `--check` di Prettier ha
  > pescato `<button type="button"             class="…">` su due file: l'`old_str` della
  > sostituzione del colore partiva a metà riga e ha lasciato in piedi l'indentazione della
  > riga originale. Difetto **mio e solo nelle mie righe** — verificato col diff di Prettier
  > **prima** di scrivere, per non riformattare regioni altrui e sporcare il delta.

---

## Decisioni aperte

| id | domanda | stato |
|---|---|---|
| **D-S4-1** | esiste una primitiva bottone/chip/input? `PRIMITIVE.md` non ne elenca — metà esatta del reclamo del developer | **dissolta, non risolta**: `PRIMITIVE.md` non ne elenca **perché non esistono**. Non manca un componente — **esiste un token (`--color-libre-green`, 307 usi in 87 file) e L4 lo scavalcava** con `bg-blue-600` (4 file in tutto il frontend, **3 sono L4**). Cercare una primitiva da adottare avrebbe portato a **costruirne una**; il difetto era una sostituzione di classe |
| **D-S4-2** | un `toFixed` di T4 su una riga che riscrivo per altri motivi: convertire o lasciare? | aperta |
| **D-S4-3** | serve un **id di lavoro** e un'API «invia → segui» per l'avanzamento? È architetturale | **aperta e fuori perimetro**: il passo 8 consegna **la misura**, non la forma. La scelta fra SSE, polling su id di lavoro e websocket resta al coordinatore |
| **D-S4-4** | i tre file fuori da `levels/l4/*` sono miei? | **sciolta da me**: la lista dei divieti del briefing è **per nome** e nessuno dei tre compare → non assegnati, non altrui. Comunicata al coordinatore con offerta esplicita di mollarli |
| **D-S4-5** | seme: leggerlo da `metadata` o spostarlo di schema? | **sciolta**: da `metadata`. Evita `schemas/risk.py` (scrittore C) e `levelHelpers.ts` (scrittore S1) |

---

## Scoperte

*(compilate passo per passo)*
