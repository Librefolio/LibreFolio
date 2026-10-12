# Piano — fase 00, 49: la corsa dei contatori di richieste in `asset-detail.spec.ts`

> **Stato**: ✅ chiuso il 2026-10-12, checkpoint al coordinatore (§7, passo 9).
> - **La corsa del §1 è chiusa dalla cura** (§3). Con la prova K-B (§4) la base cade alla prima lettura a rischio, `:3514` (passo 3). La cura passa tutto il test: 56 attese contate su 56 hanno aspettato l'handler (passo 5).
> - **La spec intera** è verde due volte sotto carico (passo 6).
> - **La prima prova, K′**, è scartata come artefatto (§4.1).
> - La prova e la cura sono passate da `test-author`.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), lotto 49. **Origine**: il rosso di `asset-detail` nel lotto 48, [piano della 48](../48_uiPolish/plan-phase00UiPolish.prompt.md), §8, passo 5, «Fuori pista».
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base `0071b9703` (treno 72).
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta. Mai le porte 6040 e 6041, mai la galleria, mai `front build` (§8).
> - **Tocca**: solo `frontend/e2e/assets/asset-detail.spec.ts`, più il journal: questo piano, la voce 49-1 nella sezione I di `BACKLOG_POST_1.2.md` e il rimando dal piano 48.

## 0. Autorizzazione (2026-10-12)

- **Coordinatore**, sul reperto del lotto 48: «(a), ma come lotto 49 separato, subito dopo il checkpoint del lotto 48». La portata, registrata nel piano 48 (§8, passo 5):
  - «La cura, via `test-author`: gli helper `waitFor…Request…` risolvono solo dopo che l'handler ha contato la richiesta, con un registro locale; i 42 siti restano invariati.»
    - Nota del passo 3: la riscansione (§2) trova 12 siti a rischio veri, non 42. La cura non cambia, e non cambia nessuna asserzione.
  - «Le prove sulla 6157, compreso un rilancio sotto carico della spec intera.»
  - «Una scansione in sola lettura delle altre spec con lo stesso schema, cioè un contatore incrementato da `page.route` e asserito subito dopo `waitForRequest`, con file:riga e proprietario. Quelle non mie non si correggono: decide il coordinatore.»
- **Coordinatore**, alla consegna del lotto 48: «**Lotto 49**, dopo la validazione: cartella `Phase_0/49_requestCountRace/`. Le note per U e per M le giro io.»
- **Coordinatore**, stesso messaggio: «il debito di lint di `_frontend_broker.py` diventa una voce nella tua sezione del backlog, nel lotto 49». Vedi §6.

## 1. Il meccanismo

- Playwright 1.61, client nello stesso processo del test (`frontend/node_modules/playwright-core/lib/coreBundle.js`):
  - il server emette l'evento `request` e subito dopo avvia la `route` (`:22399-22401`);
  - il client consegna ogni messaggio in un suo `setImmediate`, in ordine (`:62310`); fra due messaggi si svuotano le microtask.
- `page.waitForRequest` risolve sull'evento `request`, quindi **prima** che giri l'handler di `page.route`. I contatori del test (`:913-933`) crescono negli handler: `prices/sync` (`:1781`), `fx/currencies/sync` (`:1829`), `prices/query` (`:1934`).
- **Quando il conto è vecchio.** Se il test è già fermo su `await …RequestPromise` quando arriva l'evento, riparte nelle microtask di quel messaggio, prima del messaggio della `route`: una lettura sincrona del contatore vede il valore di prima. Se invece la richiesta parte mentre il test è ancora fermo in una chiamata precedente (il `click()`), l'handler ha già contato quando il test riparte. Col carico la richiesta parte più tardi, e il conto torna di uno sotto: nel lotto 48, `:5435`, Expected 51, Received 50.
- **La stessa famiglia**, non solo le asserzioni:
  - un'istantanea sincrona subito dopo l'attesa (`const xBefore = counter`) perde la richiesta corrente, e un'asserzione successiva vede +2;
  - un cancello armato subito dopo l'attesa (`deferNext…()`) viene consumato dalla richiesta corrente invece che dalla prossima.
- **Dove il problema non c'è.** Alla prossima chiamata di protocollo del test (un'asserzione sulla UI, un click) la finestra si chiude, perché i messaggi restano in ordine: le letture dopo un'attesa sulla UI sono fresche. Le letture dopo un `waitForResponse` sono fresche perché la risposta arriva dopo il `fulfill` dell'handler.
- **Il verdetto** (skill `test-triage`): **assunzione**. Il test aspetta la condizione sbagliata: «la richiesta è partita», mentre gli serve «la richiesta è stata contata». Il prodotto non c'entra.

## 2. L'inventario

**12 siti davvero a rischio, in 9 finestre; il primo in ordine d'esecuzione è `:3514`.** Ci si arriva in tre scansioni, tutte sulla base (blob dello spec `6ac98fba`).

- **La prima scansione** (`/tmp/libreFolio_i_ui_race_scan.py`) prende ogni `expect(<x>RequestCount).toBe(… + n)` e guarda solo l'ultima attesa nelle 12 righe sopra: **151 asserzioni, 42 «a rischio», 74 sicure, 35 da classificare.** È una stima per eccesso: non guarda le attese fra l'attesa di richiesta e la lettura.
  - Le 42: l'attesa più vicina è un'attesa di richiesta. Per origine della promessa (`/tmp/libreFolio_i_l49_promise_origin.log`): `waitForPriceComparisonRequest` 17, `waitForCalendarRequest` 15, `waitForMainPriceRequest` 5, `page.waitForRequest` diretta 3 (`:4374`/`:4376` per `:4384`, `:7370` per `:7397-7398`), `waitForCalendarRequestForRange` 2.
  - Le 74: l'attesa più vicina è un `waitForResponse`.
- **La riscansione delle 42** (`/tmp/libreFolio_i_l49_window_rescan.{py,log}`) guarda tutte le attese fra l'attesa di richiesta e la lettura:
  - **12 a rischio vero.** L'attesa di richiesta è l'ultima prima della lettura: righe 3514-3515, 4384, 5067, 5435, 6179, 6856, 7278, 7397-7398, 7772, 7775. Le finestre si aprono a `:3512`, `:4381`, `:5064`, `:5432`, `:6177`, `:6852`, `:7271`, `:7392`, `:7766` (`/tmp/libreFolio_i_l49_origins.log`). Il rosso del lotto 48, `:5435`, è fra questi.
  - 24 sono chiuse da un `expect.poll` fra l'attesa e la lettura. Fra queste ci sono 3320-3322, che la prima versione del §4 dava come primo rosso.
  - 4 sono chiuse da attese sulla UI dopo l'attesa di richiesta: 4226-4229 (la richiesta a `:4219`, poi `:4221`, `:4222`, `:4225`).
  - 2 sono sicure per causalità: 4553-4554. `assetSync` e `fxSync` sono già contati quando parte la richiesta principale, attesa a `:4550`.
- **Le scritture nelle finestre** (`/tmp/libreFolio_i_l49_open_windows.{py,log}`, `…_window_writes.{py,log}`): tre rilasci di cancelli (`:3516`, `:3731`, `:3842`), un flag (`:4156`) e due cancelli del calendario armati (`:4491`, `:4666`). Tutte benigne: un rilascio risolve una promessa che l'handler aspetta dopo; il flag serve alle richieste successive; una richiesta di confronto non consuma un cancello del calendario.
- **Tutte le letture**, comprese quelle che seguono solo attese sulla UI (`/tmp/libreFolio_i_l49_ui_reads{,2,3}.{py,log}`). Nel test (righe 486-7836) ci sono 290 letture sincrone dei contatori; l'attesa più vicina è sulla UI per 137, un poll per 82, una risposta per 52, una richiesta per 19. Per le 159 della forma «istantanea + n» la scansione cerca una chiusura dopo l'ultima azione: una risposta, un poll, un'attesa causale, o un'attesa di richiesta seguita da un'altra attesa.
  - 124 sono chiuse, e nessuna lo è solo da un'attesa causale sulla UI;
  - 12 sono nella finestra di una richiesta: esattamente i 12 siti a rischio;
  - 23 non hanno una chiusura riconosciuta. Lette a mano, sono tutte sicure:
    - dopo una risposta: 3371 e 3373 (`:3360`; le azioni successive non mandano richieste nuove), 3528-3529 (`:3517`, `:3519`), 6798-6799 (`(await sevenYearsResponsePromise)` a `:6773`, una forma fra parentesi che la regex non riconosce), 7355 e 7357-7358 (`:7341`, `:7343`), 7515 (`:7490`, più `data-busy=false`; rilegge il valore di `:7506-7507`);
    - dopo un poll: 4584-4585 (`:4556`), 5915-5916 (`:5897-5904`);
    - dopo un'attesa di richiesta seguita da attese sulla UI: 4226-4229 (`:4219`), 4408-4409 (`:4380-4381`), 6196 (`:6177`);
    - 3824-3825: il +2 è la richiesta di confronto coi peer sostitutivi (`:3795`) più la principale del refresh (`:3806`), entrambe chiuse dalle attese successive. La richiesta di confronto del refresh (`:3802`) parte solo dopo la risposta principale, che il cancello trattiene fino a dopo la lettura: se partisse prima, anche la base leggerebbe +3. `priceComparisonRequestCount` resta fermo (`:3826`) perché conta solo i peer di `comparisonPeerIds` (`:1937`).
- **Le 35 da classificare** della prima scansione, lette a mano con la cura applicata (`/tmp/libreFolio_i_l49_probe_classify{,2}.log`). Tutte fresche:
  - dopo un'attesa di risposta: 3373, 3497-3499, 3501, 3664-3665, 3670, 3672, 4349-4351, 5625, 5627-5628, 6798-6799 (`sevenYearsResponsePromise`, `:6773`), 7020, 7355, 7357, 7604-7605, 7607, 7680;
  - dopo un `expect.poll`: 5915-5916;
  - dopo un'attesa che la cura conta, seguita da altre attese: 3824-3825 (gli helper di `:3795` e `:3806`), 4408-4409 (le attese dirette di `:4380-4381`, più il poll di `:4385`), 6196 (l'helper del calendario di `:6177`; stesso valore del sito a rischio `:6179`);
  - nessuna richiesta nuova da contare: 4584-4585, gli stessi valori di `:4556-4558`;
  - fuori dalla prova, perché l'handler di `fx/currencies/convert` non conta per la cura: 6405 e 7681 (`fxConvertRequestCount`).
- **La riprova sulle istantanee** (`/tmp/libreFolio_i_l49_reqnear_reads.{py,log}`): tutte le letture dei contatori, istantanee comprese, la cui attesa più vicina è un'attesa di richiesta. Sono 20:
  - i 12 siti a rischio, più i 2 sicuri per causalità (4553-4554);
  - 5 asserzioni «invariato» su un contatore che la richiesta corrente non tocca: 7399, 7400 (dopo la principale di `:7392`), 7773, 7774, 7776 (dopo il calendario di `:7766`);
  - 2531: l'attesa è `commitSyntheticRange` (`:2492`), che prima di tornare aspetta le risposte e la UI.
  - Nessuna istantanea (`const … = <contatore>`) sta in una finestra di richiesta.

## 3. La cura

- **Il registro**, accanto ai contatori (`:913-933`), con un commento breve sul perché:
  - `countedRequests = new WeakSet<Request>()`: le richieste già contate;
  - `countedRequestWaiters = new Map<Request, Array<() => void>>()`. Un array e non un solo risolutore, perché due attese contate possono prendere la stessa richiesta: con un risolutore solo, una delle due resterebbe appesa;
  - `markRequestCounted(request)`: aggiunge la richiesta al set, risolve tutte le attese, toglie la voce;
  - `untilCounted(request)`: risolve subito se la richiesta è già contata; altrimenti registra un risolutore con un timer di 10 s, che rifiuta con un messaggio chiaro (metodo, percorso, «never counted by its page.route handler») e si cancella alla risoluzione;
  - `waitForCountedRequest(predicate, options?)` = `page.waitForRequest(predicate, options).then(untilCounted)`.
- **Il tipo**: `Request` entra nell'import di tipo della riga 13; `fixtures/playwright.ts:337` lo esporta già.
- **I punti di conteggio**, `markRequestCounted(route.request())`, dopo tutti gli incrementi e dopo il consumo dei cancelli, prima del primo `await`:
  - `prices/sync`: fra `:1803` (`deferredAssetSyncResponse = null`) e `:1804` (`if (deferred)`);
  - `fx/currencies/sync`: fra `:1858` (il consumo del cancello) e `:1859` (`if (deferred)`);
  - `prices/query`: subito prima di `:2034`. Dopo resta solo `deferredCalendarResponses.delete`, sincrona, che gira prima che il test riparta.
  - **Mai in fondo all'handler**: il test apre i cancelli differiti solo dopo essere ripartito, quindi un conteggio dopo l'`await` del cancello si bloccherebbe. I percorsi che lanciano un errore non contano: l'attesa fallisce in 10 s, con un messaggio chiaro.
- **Cosa passa a `waitForCountedRequest`**: i 5 helper (`waitForCalendarRequest` `:1483`, `waitForCalendarRequestForRange` `:1491`, `waitForPriceComparisonRequest` `:1542`, `waitForMainPriceRequest` `:1563`, `waitForBackendSignalRequest` `:1584`) e le 3 attese dirette `:4374`, `:4376`, `:7370`. **Le asserzioni restano invariate**, i 12 siti a rischio come tutte le altre.
- Il `Request` dell'evento e quello di `route.request()` sono la stessa istanza, quindi il `WeakSet` li riconosce.
- La cura rende le attese solo più tarde, mai più presto: tutto quello che era vero alla risoluzione di prima resta vero.

### 3.1 Perché il registro non può bloccare

- Il test registra 8 rotte (`:1742`, `:1764`, `:1767`, `:1781`, `:1829`, `:1898`, `:1934`, `:2234`); solo tre contano richieste, e tutte e tre segnano.
- Le 50 chiamate a `page.waitForRequest` del test vanno tutte su quelle tre (`/tmp/libreFolio_i_l49_direct_targets.log`): `prices/query` 10, `prices/sync` 17, `fx/currencies/sync` 23.
- Nessun handler fa un `await` prima del suo punto di conteggio.
- **Il risolutore è registrato sempre prima del conteggio.** `.then(untilCounted)` gira nelle microtask dell'evento `request`, prima del messaggio della `route`, anche quando la richiesta parte mentre il test è ancora fermo nel click: in quel caso la promessa è già risolta quando il test ci arriva. La misura del passo 5 lo conferma: 56 attese su 56 hanno aspettato l'handler, nessuna ha trovato la richiesta già contata. Il ramo «già contata» di `untilCounted` è una cintura, per il caso in cui una versione futura di Playwright cambi l'ordine.

### 3.2 Le alternative scartate

- **Riscrivere con `expect.poll` le letture a rischio** (i 12 siti del §2): fuori dalla portata approvata, che lascia i siti invariati; e non copre le istantanee né i cancelli.
- **Aspettare la risposta invece della richiesta**: cambia il senso del test. Con un cancello differito la risposta arriva solo dopo che il test lo apre, quindi le attese sullo stato intermedio si bloccherebbero.
- **Contare in `page.on('request')`**: duplica la classificazione degli handler (calendario, principale, confronto), che dipende dallo stato del test; due copie divergono.

## 4. Le prove: la prova K-B

La prova serve a vedere il rosso in modo deterministico, senza aspettare il carico. **Non entra nel commit.** Sostituisce la prova K′, che ha dato un rosso d'artefatto (§4.1).

- **L'idea**: ritardare nel browser l'invio delle richieste che contano. Il click torna prima che la richiesta parta, e il test è sempre già fermo sull'attesa di richiesta quando arriva l'evento: è il caso del §1 in cui il conto è vecchio, quello che il carico produce a caso.
- **Il client HTTP**: tutte le chiamate all'API passano da `XMLHttpRequest`. L'istanza axios di `frontend/src/lib/api/zodios-client.ts:83` non sceglie un adapter, e axios 1.13.2 prova per primo `xhr`. `fetch(` serve solo per gli asset statici e in `generated.ts`, mai per le tre rotte che contano.
- **Il codice**, subito dopo `test.setTimeout(…)` (`:487`), che nella prova passa a `600_000`:
  - `page.addInitScript(…)` avvolge `XMLHttpRequest.prototype.open`, `send` e `abort`;
  - `open` ricorda metodo e URL;
  - `send` di un POST verso `/api/v1/assets/prices/sync`, `/api/v1/fx/currencies/sync` o `/api/v1/assets/prices/query` parte dopo `setTimeout(…, 250)`; le altre richieste partono subito;
  - un `abort` prima dell'invio ritardato lo annulla. È solo una cintura: nella pagina dell'asset non ci sono `AbortController` né `.abort()`;
  - due contatori su `window`: `__l49Delayed` (gli invii ritardati) e `__l49AbortedBeforeSend`.
- **Perché copre tutto il test**: lo script si registra prima della navigazione di `:2243` e si riapplica al `reload` di `:6882`. Prima del `reload` il test aspetta le risposte e `data-busy=false`, quindi nessun invio ritardato va perso. `page.clock` compare solo da `:8068`, fuori dal test: il `setTimeout` della pagina è quello vero.
- **Perché non ha l'artefatto di K′**: il ritardo sta prima dell'evento `request`, non dopo. Il test che aspetta la richiesta aspetta anche il ritardo, e l'handler gira subito dopo l'evento, come senza la prova. Le richieste che contano aspettano tutte lo stesso tempo, e i timer con lo stesso ritardo scattano nell'ordine di creazione: arrivano agli handler nell'ordine naturale.
- **Gli esiti attesi**:
  - sulla base: il primo rosso a `:3514` (`priceQueryRequestCount`, dopo `await pageSyncPostComparisonRequestPromise` di `:3512`), con «Expected N+1, Received N». Nel file con la prova, la riga scende dello scarto della prova;
  - con la cura: verde. Per escludere un verde vuoto, la prova sulla cura aggiunge un contatore delle volte in cui `untilCounted` ha dovuto aspettare davvero, e alla fine del test stampa quel numero e `__l49Delayed`.
- **Se la cura resta rossa**, si classifica il sito:
  - dopo un'attesa diretta non coperta dalla cura, senza chiamate di protocollo prima della lettura: è una **corsa latente vera**. Si propone al coordinatore di passare a `waitForCountedRequest` tutte le 45 attese dirette (le 50 meno i 5 helper);
  - dopo una risposta o un poll su un'altra richiesta: è una **corsa latente** della stessa famiglia, con una finestra naturale piccola. Va al coordinatore col sito e una proposta: un poll sul contatore, o l'attesa contata;
  - un riordino rispetto alle richieste che non contano (i GET dei metadati, `fx/currencies/convert`): è un **artefatto della variante**. Si rilancia con la variante «tutte le XHR», che ritarda ogni richiesta e conserva l'ordine fra tutte.
- Il diff della prova e i log vanno in `/tmp/libreFolio_i_l49_probe2*`.

### 4.1 La prova K′, scartata

- **Com'era**: `page.waitForRequest`, avvolto sull'istanza, segnava in un `WeakSet` le richieste che il test aspetta esplicitamente; all'inizio dei tre handler, le richieste segnate aspettavano 250 ms.
- **Sulla base** (`/tmp/libreFolio_i_l49_probe_base.diff`, `…_probe_base_run.log`): rosso dopo 29,2 s, `page.waitForResponse: Timeout 10000ms exceeded`, a `:2968`/`:2969` della base, nella scena i60g. Nel file con la prova le righe erano 2983/2984.
- **Perché è un artefatto**: la richiesta vecchia di i60g era segnata, e il suo handler aspettava 250 ms; la successiva no, e lo ha sorpassato. Ha consumato lei il cancello della finestra 7 (`deferredCalendarResponses`), e la sua risposta è rimasta trattenuta. Il ritardo nell'handler, dopo l'evento `request`, crea un ordine fra le richieste che senza la prova non capita.
- **Cosa resta**: il sito i60g non legge contatori nella finestra; e il primo rosso atteso da K′, `:3320`, era sbagliato, perché è chiuso da un poll (§2).
- **Perché non la prova A**, un ritardo nell'handler di ogni richiesta: ha lo stesso difetto di K′, il ritardo dopo l'evento, e in più ritarda richieste che il test non aspetta.

## 5. Le altre spec (scansione in sola lettura)

- **La variante A**, un contatore letto subito dopo `waitForRequest`: c'è solo in `asset-detail.spec.ts`. Gli altri usi di `waitForRequest` sono sicuri:
  - leggono la richiesta stessa: `fx-add-pair:197`; `fx-detail:1137`, `:1786`; `stale-price-banner:339`, `:408`, `:418`; `tx-import-degiro:627`; `tx-import-duplicate-precedence:1180`; `default-currency:157-167`;
  - aspettano anche la risposta, con `Promise.all`: `ai-export-contract:106`; `ai-export/helpers.ts:137`;
  - li segue un'attesa sulla UI o un poll: `asset-mobile-layout:380`; `auth:391`; `risk-analysis:2306`; `risk-asset-detail:177`;
  - dipendono da `sync.answered`: `data-quality-banners:552`, `:600`; `stale-price-banner:346`, `:414`.
- **La variante B**, un handler che registra dopo il suo primo `await`, o un handler con un nome: 16 casi LATE e 10 NAMED, tutti sicuri (`/tmp/libreFolio_i_l49_xspec_late.log`).
- **Il test `log` di `asset-detail`** (`:8221-8227`, letto a `:8254`): è benigno. Lo documento qui e non lo tocco.
- **Nessuna nota per altri proprietari**: le note per U e per M, se servissero, le gira il coordinatore.

## 6. Il debito di lint di `_frontend_broker.py` (voce 49-1)

- `ruff check scripts/test_runner/_frontend_broker.py`: E701 a `:44:36`, `:45:32`, `:52:36`, `:53:32`; PLC0415 a `:96:5`.
- `black --check` lo riformatterebbe, in due pezzi: `@@ -39,20 +39,24 @@` e `@@ -92,16 +96,14 @@`.
- È preesistente (blame `1a29e0523`, `547c06cf0`, `7d3463e2f`); le righe del lotto 48 non sono nei pezzi di black (piano 48, §8, passo 7).
- **È fuori dal gate**: `dev.py:1841` e `:1848` passano ruff e black solo su `backend/`.
- **Il runner intero**: 149 errori ruff in 17 file; black riformatterebbe 15 file su 30 (`/tmp/libreFolio_i_l49_{ruff,black}_runner.log`). Se pulirlo in una volta sola lo decide il coordinatore.
- La voce va nella sezione I del backlog come **49-1**, priorità minima. Questo lotto non tocca il file.

## 7. Avanzamento

- [x] **1. Analisi** (2026-10-12): il meccanismo, l'inventario, gli handler, la scansione delle altre spec, gli statici della base, il debito di lint.
  > **Note implementazione**:
  > - Il meccanismo è letto nel sorgente di Playwright 1.61 (§1). L'evento `request` e `route.request()` danno la stessa istanza, e il predicato dell'utente gira in modo sincrono all'emissione dell'evento.
  > - L'inventario (§2): `/tmp/libreFolio_i_l49_scan_head.log` (42/74/35), `…_promise_origin.log`, `…_unknown.txt`, `…_unknown_ctx.log`, `…_ident_incr.log`.
  > - Le 50 attese del test puntano tutte ai tre handler che contano (`…_direct_targets.log`).
  > - Gli statici della base, da `frontend/`:
  >   - `node_modules/.bin/tsc -p tsconfig.e2e.json --noEmit`: rc 2, 2 righe d'errore, nessuna in `asset-detail` (`e2e/onboarding-tour.spec.ts(863,21)` TS2322 e `src/lib/types/files.ts(9,23)` TS2307; `/tmp/libreFolio_i_l49_tsc_base.log`);
  >   - `node_modules/.bin/prettier --check e2e/assets/asset-detail.spec.ts`: rc 0 (`…_prettier_base.log`).
  > - Il frontend servito è la build di debug (marcatore 1), quella che il server di test vuole (`dev.py:198`): non serve ricostruire.
  >
  > **⚠️ Fuori pista**:
  > - **La prima euristica della scansione incrociata** (`/tmp/libreFolio_i_l49_xspec_scan.py`) trovava un solo sito a rischio anche in `asset-detail`, contro i 42 della scansione dedicata: come rivelatore non era affidabile. L'ho sostituita con la lettura del contesto di ogni `waitForRequest` e di ogni lettura dei contatori (`/tmp/libreFolio_i_l49_xspec_ctx*.log`, `…_xspec_reads.log`).
  > - **La variante B è un'estensione mia**: gli handler che registrano dopo il primo `await` hanno la stessa forma di corsa. Tutti sicuri (§5).
  > - **La base è avanzata durante l'analisi**: il coordinatore ha portato il ramo in fast-forward da `0a148a109` a `0071b9703` (treno 72). Il blob dello spec non è cambiato (`6ac98fba`); i numeri di riga valgono per entrambe.
  > - **Niente `front build`**: scrive il marcatore 0, e il server di test ricostruirebbe all'avvio, col rischio di superare i 300 s di `STARTUP_TIMEOUT` (`scripts/test_runner/_server.py:43-48`). È la causa probabile del timeout d'infrastruttura del lotto 48. Se mai servisse, si usa `--debug`.
- [x] **2. Il progetto della prova** (2026-10-12): la prova K′ (oggi §4.1, scartata al passo 3) e la classificazione delle 35 (§2).
  > **Note implementazione**:
  > - Le 35 sono classificate con `/tmp/libreFolio_i_l49_probe_classify.py` (`…_probe_classify.log`, `…_probe_classify2.log`): sotto la prova e con la cura, tutte fresche.
  > - Rilette le ancore degli handler: in `prices/sync` e `fx/currencies/sync` non ci sono ritorni anticipati prima del cancello; in `prices/query` tutto il consumo dei cancelli sta prima di `:2034`.
  >
  > **⚠️ Fuori pista**:
  > - **La prima idea era la prova A**, un ritardo su ogni richiesta. L'ho scartata per i falsi rossi (§4): resta aperto solo se le istantanee dopo le attese dirette non coperte siano a rischio, ed è la prova K′ a dirlo.
- [x] **3. Il rosso della prova sulla base** (`test-author`, 2026-10-12): la prova K-B (§4) sulla base, il singolo test, il sito e i valori.
  > **Note implementazione**:
  > - **La prova K′ è girata sulla base** (2026-10-12, 22:39-22:43, `test-author`): rosso d'artefatto, §4.1. Il test-author ha tolto la prova, e il blob dello spec è tornato `6ac98fba` (verificato).
  > - **Rifatto l'inventario** (§2): da 42 siti «a rischio» a 12 veri, in 9 finestre; il primo è `:3514`, non `:3320`. Rilette anche tutte le 290 letture dei contatori: nessuna corsa fuori dai 12.
  > - **La nuova prova è K-B** (§4), lato browser. Prima di sceglierla ho verificato: che il client HTTP passa da XHR; che nel test non ci sono `abort` né `page.clock`; che `addInitScript` copre la navigazione e il `reload`.
  > - **La prova K-B sulla base** (2026-10-12, 23:24, `test-author`) dà **il rosso atteso, al sito previsto**:
  >   - lo scarto della prova è 38: la riga `:487` cambia sul posto, e il blocco occupa le righe 488–525 del file con la prova;
  >   - il rosso è alla riga 3552 del file con la prova, cioè **`:3514` della base**: `expect(priceQueryRequestCount).toBe(pageSyncPriceQueriesBeforeReturn + 1)`, con **Expected 35, Received 34**;
  >   - l'attesa di richiesta di `:3512` era già risolta, e il controllo del payload di `:3513` era passato. L'handler, però, non aveva ancora contato la richiesta: è il conto vecchio del §1;
  >   - tutte le asserzioni prima di `:3514` sono passate. Il test è durato 34,2 s e il comando 1 min 22 s. Un solo giro, senza rilancio: il rosso è un'asserzione, non un problema d'infrastruttura;
  >   - c'è un secondo errore, `page.waitForResponse: Test ended`. È una conseguenza del primo: la risposta attesa da `:3508` era trattenuta da `pageSyncPostComparisonGate`, che si rilascia a `:3516`, e il test non ci è arrivato.
  > - **I file**: `/tmp/libreFolio_i_l49_probe2_base.diff`, `…_probe2_base_run.log` e `…_probe2_base_artifacts/` (lo screenshot e `error-context.md`).
  > - **Il ripristino, riverificato da me**: blob `6ac98fba`, nessuna voce dello spec in `git status`, porta 6157 libera (`lsof` rc 1).
  > - **Il verdetto** (test-triage): **assunzione**. Il test dà per scontato che, quando l'attesa di richiesta risolve, l'handler abbia già contato. Il prodotto non c'entra.
  > - **Prima di mandare la cura** ho riletto le ancore sulla copia della base (`/tmp/libreFolio_i_l49_spec_head.ts`):
  >   - nei tre handler non c'è nessun `return` prima del punto di conteggio, solo i `throw` per i payload sbagliati, che fanno già fallire il test. Tutti gli incrementi stanno prima del punto;
  >   - il nome `Request` non compare nello spec, quindi l'import di tipo non oscura niente;
  >   - il file ha 52 `page.waitForRequest(`: 50 nel test, e 2 in altri test (`:224`, `:294`) che la cura non tocca.
  >
  > **⚠️ Fuori pista**:
  > - **K′ aveva un difetto di progetto**: il ritardo nell'handler, dopo l'evento `request`, lascia che una richiesta non segnata ne sorpassi una segnata. Il blocco di i60g (`:2968`/`:2969`) è nato lì, non dal prodotto né dalla corsa.
  > - **La prima scansione era troppo larga**: guardava solo l'attesa più vicina. Il sito che il §4 dava come primo rosso (`:3320`) è chiuso da un poll; il conto vero è 12, non 42.
  > - **Lo scarto di riga**: nel file con la prova K′ le righe dopo `:488` scendevano di 12, e di 15 dopo il terzo handler. Il log riporta i numeri del file con la prova.
  > - **3824-3825 sembrava una corsa latente** (+2 su `priceQueryRequestCount` senza un'attesa sulla seconda richiesta). Non lo è: il §2 spiega da dove viene il +2.
- [x] **4. La cura** (`test-author`, 2026-10-12): §3, senza la prova. È stata mandata dopo il rosso del passo 3, col codice esatto del registro e i conteggi di controllo.
  > **Note implementazione**:
  > - **Il diff** (`/tmp/libreFolio_i_l49_cure.diff`, riletto da me): 1 file, 36 righe aggiunte e 9 tolte, in 12 blocchi. Dentro ci sono solo:
  >   - l'import di tipo;
  >   - il registro di 24 righe dopo `:933`;
  >   - i 5 helper;
  >   - i 3 punti di conteggio, ognuno dopo l'ultimo incremento e prima del primo `await` del suo handler;
  >   - le 3 attese dirette. `:4374` e `:4376` stanno nello stesso blocco, per questo i blocchi sono 12.
  >
  >   Nessuna riga `expect(` nel diff.
  > - **I conteggi**: 45 `page.waitForRequest(`, 8 `waitForCountedRequest(`, 3 `markRequestCounted(route.request())`. Il file passa da 8.396 a 8.423 righe.
  > - **Gli statici**:
  >   - prettier: `--write` non ha cambiato niente, e `--check` dà rc 0 (rilanciato da me);
  >   - tsc e2e: rc 2, con le stesse 2 righe della base (`/tmp/libreFolio_i_l49_cure_tsc.log`);
  >   - `git diff --check`: pulito.
  > - **Il blob della cura** è `52b5f9d2e939…`, identico all'istantanea `/tmp/libreFolio_i_l49_spec_cure.ts` (`cmp` muto). Nel file non c'è nessun resto della prova: `l49`, `addInitScript`, `600_000` e `console.log` contano 0.
  > - **Il giro singolo** (`front-asset asset-detail "calendar-return primary mode"`) è **verde**, sotto carico alto:
  >   - `1 passed (1.4m)`: il test ha preso 1,3 min dei suoi 180 s, il comando 2 min 39 s;
  >   - nessun errore «was never counted»;
  >   - un solo giro, senza rilancio (`/tmp/libreFolio_i_l49_cure_single.log`).
  > - **La porta 6157** è libera (`lsof` rc 1).
  > - **Righe base → cura**: +24 da `:934`, +25 da `:1804`, +26 da `:1859`, +27 da `:2034`. Per esempio il `reload` passa da `:6881` a `:6908`, e l'ultima istruzione del test da `:7823` a `:7850`.
  > - **Il limite di questo verde**: senza la prova dice solo che la cura non si blocca e che ogni richiesta attesa viene contata. Non dice che la corsa è chiusa, perché anche la base passa quasi sempre. Questa prova la dà il passo 5.
  >
  > **⚠️ Fuori pista**: nessuno.
- [x] **5. La prova sulla cura** (`test-author`, 2026-10-12, 23:44-23:47): la prova K-B sulla cura, col contatore delle attese di `untilCounted`. **Verde.** Poi la prova è stata tolta.
  > **Note implementazione**:
  > - **La prova** (`/tmp/libreFolio_i_l49_probe3_cure.diff`, riletto da me): sul file della cura, 6 blocchi, 53 righe aggiunte e 3 tolte. Dentro ci sono:
  >   - il blocco K-B del passo 3, identico byte per byte: le 38 righe estratte dai due diff coincidono (`diff` rc 0);
  >   - l'import di `writeFileSync`;
  >   - i due contatori prima del registro;
  >   - il ramo di `untilCounted` diviso in due;
  >   - i contatori K-B letti prima del `reload`;
  >   - la riga finale, nel log e in un file.
  > - **Lo scarto di riga** nel file con la prova: +38 da `:488` della cura, +41 da `:936`, +45 da `:946`, +46 da `:6908`, +50 dopo l'ultima istruzione del test (`:7850`).
  > - **Il giro singolo è verde**:
  >   - `1 passed (2.1m)`: il test ha preso 2,0 min dei suoi 600 s, il comando 2 min 52 s;
  >   - un solo giro, senza rilancio;
  >   - nel log nessun «never counted» e nessun errore (`/tmp/libreFolio_i_l49_probe3_cure_run.log`).
  > - **La riga della prova** (anche in `/tmp/libreFolio_i_l49_probe3_cure_counters.txt`): `[l49-probe] beforeReload delayed=217 aborted=0; afterReload delayed=32 aborted=0; untilCounted immediate=0 waited=56`.
  >   - **La prova era attiva su tutte e due le pagine**: 249 POST che contano sono partiti con 250 ms di ritardo, 217 prima del `reload` e 32 dopo. Nessuno è stato annullato durante il ritardo, quindi la prova non ha perso richieste.
  >   - **Le attese contate** sono state 56, e tutte hanno aspettato il punto di conteggio del loro handler. Nessuna è scaduta ai 10 s.
  > - **Cosa dimostra**: con la stessa prova la base cade alla prima lettura a rischio (`:3514`, passo 3), mentre la cura passa tutte le 12 letture delle 9 finestre (§2). La corsa è chiusa dove il §2 la trova.
  > - **Il limite del contatore**:
  >   - `immediate=0` non dipende dalla prova. `untilCounted` è agganciato all'attesa di richiesta, quindi gira nelle microtask del messaggio `request`, sempre prima del messaggio della `route` (§1).
  >   - Il contatore dice che il registro ha lavorato 56 volte su 56, cioè che il verde non è vuoto.
  >   - Che il test fosse fermo sull'attesa, quando l'evento è arrivato, lo dice K-B, col rosso della base.
  > - **Il ripristino, riverificato da me**:
  >   - blob `52b5f9d2e939…`, `cmp` con l'istantanea muto;
  >   - i marcatori della prova (`l49`, `addInitScript`, `600_000`, `console.log`, `writeFileSync`) contano 0;
  >   - i conteggi restano 45/8/3;
  >   - la porta 6157 è libera (`lsof` rc 1).
  >
  > **⚠️ Fuori pista**: il §3.1 diceva che, se la richiesta parte mentre il test è fermo nel click, l'attesa risolve dal ramo «già contata». La misura dice di no: quel ramo non è mai scattato (`immediate=0`). Ho corretto il §3.1. La cura non cambia: in quel caso la promessa è già risolta quando il test la raggiunge.
- [x] **6. La spec intera** (2026-10-12, 23:50-23:58, lanciata da me): verde sulla 6157, e verde anche nel rilancio sotto carico.
  > **Note implementazione**:
  > - **Il primo giro** (`front-asset asset-detail`, `/tmp/libreFolio_i_l49_spec_full.log`):
  >   - `32 passed (2.9m)`, con 1 worker;
  >   - il test del lotto in 1,2 min;
  >   - il comando in 3 min 28 s.
  > - **Il rilancio** (`/tmp/libreFolio_i_l49_spec_full2.log`):
  >   - `32 passed (3.2m)`;
  >   - il test del lotto in 1,4 min;
  >   - il comando in 4 min 23 s.
  > - **Nei log** nessun «failed», «flaky», «retry», «never counted» né «Error».
  > - **Il carico**, su 10 core:
  >   - load average 22,8 sui 5 minuti del primo giro (letto alle 23:54);
  >   - 32,7 all'inizio del rilancio e 25,6 alla fine.
  > - **Dopo i due giri** la porta 6157 è libera (`lsof` rc 1), e nessun processo cita la porta o la cartella dati della corsia.
  >
  > **⚠️ Fuori pista**:
  > - **Lo spegnimento del backend.** In tutti e due i giri, dopo `✅ Playwright tests - PASSED`, il runner ha scritto «Shared backend ignored SIGTERM for 5s — killing its process group».
  >   - È lo spegnimento di `scripts/test_runner/_server.py:311-334`: SIGTERM, 5 s di attesa, poi SIGKILL del gruppo.
  >   - Non c'è nei giri singoli dei passi 4 e 5, né nei miei log del lotto 48.
  >   - Non tocca l'esito: exit code 0, porta libera, nessun orfano.
  >   - È fuori dal lotto, e il runner è del coordinatore: lo segnalo nel checkpoint e non indago.
- [x] **7. Gli statici** (2026-10-12, sul blob della cura `52b5f9d2…`, da `frontend/`):
  > **Note implementazione**:
  > - **tsc e2e** (`node_modules/.bin/tsc -p tsconfig.e2e.json --noEmit`): rc 2, con le stesse 2 righe della base (`/tmp/libreFolio_i_l49_final_tsc.log`).
  > - **prettier**: `--check e2e/assets/asset-detail.spec.ts` dà rc 0.
  > - **`git diff --check`**: pulito. Nel piano nuovo, che non è tracciato, nessuno spazio in coda né tabulazioni.
  > - **Nessun resto della prova** fra le righe aggiunte (`/tmp/libreFolio_i_l49_final.diff`): `addInitScript`, `600_000`, `l49`, `__l49`, `console.log`, `writeFileSync` e `250` contano 0.
  > - **Le asserzioni**: nessuna riga `expect(` nel diff, che sulla spec conta 36 righe aggiunte e 9 tolte.
  >
  > **⚠️ Fuori pista**: nessuno.
- [x] **8. Il journal** (2026-10-12, fatto in anticipo, mentre `test-author` gira il passo 3): la voce 49-1 nel backlog, il rimando dal piano 48.
  > **Note implementazione**:
  > - **La voce 49-1**, in fondo alla sezione I di `BACKLOG_POST_1.2.md`, dopo la 48-1; l'introduzione della sezione dice da quale base vengono i suoi numeri di riga (`0071b9703`).
  > - Prima di scriverla ho rilanciato `ruff check` su `_frontend_broker.py`: gli stessi 5 errori della misura del passo 1.
  > - **Il piano 48** rimanda qui dall'intestazione («Seguito»).
  > - L'indice per fonte del backlog è del coordinatore: la riga per i piani 48 e 49 non la scrivo io.
- [x] **9. Il checkpoint** (2026-10-12): consegnato al coordinatore con questo stato; poi FROZEN.
  > **Note implementazione**:
  > - **Due commit senza file in comune**, quindi basta un'istantanea:
  >   - C1 `test(e2e): count asset-detail requests`: la spec;
  >   - C2 `docs(journal): plan 49, lint debt in backlog`: questo piano, `BACKLOG_POST_1.2.md` e il piano 48.
  > - **Il manifest coi blob, i messaggi e le prove** sono nei file della sessione di I (`requestcount_commit_bundle/`).
  > - **La definizione di fatto** (§8): tutti e 8 i punti sono soddisfatti.
  > - **Il target**: `dev_release2` è a `986e99bd3` (treno 76), 40 commit dopo la base (`/tmp/libreFolio_i_l49_conflict.log`).
  >   - Dei file del lotto tocca solo `BACKLOG_POST_1.2.md`, con blocchi lontani dai miei: i suoi a `:124`, `:414`, `:517`, `:718`, `:772`, `:851`, i miei a `:178` e `:262`. La fusione a tre vie simulata in `/tmp` (`git merge-file`) è pulita, e la voce 49-1 resta.
  >   - Non tocca `fixtures/playwright.ts`, da cui viene il tipo `Request`, né `package.json`: Playwright resta 1.61.
  >   - Cambia però i grafici e `assets/[id]/+page.svelte` (una data nella lingua dell'interfaccia), che la spec attraversa. Dopo la fusione va rilanciata `front-asset asset-detail`.
  > - **La porta 6157** è libera.
  > - **Il CHANGELOG**: nessuna riga.
  >
  > **⚠️ Fuori pista**: nessuno.

## 8. Definizione di fatto e selettori

- **I selettori**, uno alla volta sulla 6157, col prefisso `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`:
  - il singolo test: `front-asset asset-detail "calendar-return primary mode"`;
  - la spec intera: `front-asset asset-detail` (32 test nel lotto 48).
  - Se un E2E scade sotto carico, si rilancia da solo prima di indagare.
- **Fatto quando**:
  1. il rosso della prova sulla base è registrato, col sito e coi valori;
  2. la cura è quella del §3, e le asserzioni sono invariate: il diff tocca solo l'import di tipo, il registro, i 3 punti di conteggio, i 5 helper e le 3 attese dirette;
  3. la prova sulla cura è verde, oppure ogni rosso è classificato e deciso col coordinatore;
  4. la prova è tolta: `addInitScript`, `__l49Delayed`, il ritardo di 250 ms e il timeout di `600_000` non compaiono nel diff;
  5. la spec intera è verde sulla 6157, e lo resta nel rilancio sotto carico;
  6. tsc e2e non aggiunge errori alle 2 righe della base, `prettier --check` dà rc 0, `git diff --check` è pulito;
  7. la voce 49-1 è nel backlog e il piano 48 rimanda qui;
  8. la porta 6157 è libera, e il checkpoint è consegnato con manifest e messaggi.
- **Niente `front build`**: il server di test usa la build di debug già presente (§7, passo 1).
- **Il CHANGELOG**: nessuna riga, il lotto tocca solo un test.
