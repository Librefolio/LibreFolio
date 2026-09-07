# Coda beta testing — provider parametrici, FM3, orfani forkserver

Racconto durevole dei quattro punti aperti dopo la campagna sulle sleep. Tre delle quattro
diagnosi scritte nel piano si sono rivelate **sbagliate**: quello che segue è ciò che è
risultato vero sul campo, non ciò che era stato ipotizzato.

---

## 1 · FM3 — chiuso

**Diagnosi del piano:** «la seconda gamba del form doppio non risulta compilata». **Falsa.**

**Vero:** `captureValidatePayload` registra `page.waitForRequest` e restituisce **la prossima**
POST a `/transactions/validate`, chiunque l'abbia causata. FM3 fa due `applyFormModal` e
**nessuno aspetta il primo validate**: sotto carico il listener cattura il payload del BUY, che
non contiene il TRANSFER. Fallimento in 3,5 s contro i 6-8,5 s delle corse verdi — il test non
falliva *tardi*, falliva *presto*.

**Rimedio:** la barriera esiste già nel prodotto. `TransactionBulkModal` pubblica il contatore
monotono `data-validate-runs`; `waitForValidateRun(scope, since)` lo aspetta. Una riga dopo
l'apply del BUY.

**Verifica:** `front-transaction all --workers 4` → **219/219**, FM3 a 7,8 s (dentro la banda
verde).

---

## 2 · Orfani forkserver — diagnosi ribaltata

**Ipotesi del piano:** `shutdown_pool()` chiama `shutdown(wait=False)`, quindi non fa il join
dei worker. **Falsa** come causa isolata.

**Vero, dimostrato con una sonda a sette forme di uscita** (`/tmp/libreFolio_fork_probe2.py`):

| shutdown | uscita del genitore | pipe |
|---|---|---|
| `wait=False` | SIGKILL dopo 0,2 s | chiude ✅ |
| `wait=True` | SIGKILL dopo 0,2 s | chiude ✅ |
| **mai** | SIGKILL | **appesa** ❌ |
| mai | return normale (atexit gira) | chiude ✅ |
| **mai** | `os._exit(0)` | **appesa** ❌ |
| `wait=False` **subito prima** di `os._exit` | — | **appesa** ❌ |
| `wait=True` subito prima di `os._exit` | — | chiude ✅ |

La variabile che decide non è `wait`: è **se `atexit` gira**. `concurrent.futures.process._python_exit`
è il gestore che normalmente fa il join dei figli. Chi esce per SIGKILL o `os._exit` lo salta, i
figli vengono riadottati da init **con lo stdout ereditato**, e chi legge la pipe non vede mai EOF.

`wait=False` non è un difetto in sé — è una **scommessa sul tempo**: con 0,2 s di sonno il thread
di gestione fa in tempo a mandare le sentinelle, subito prima di `os._exit` no. Ecco perché la
prima tornata di sonda sembrava assolvere `wait=False`: assolveva il sonno.

**Due produttori distinti, non uno:**

1. **pytest** — `backend/test_scripts/conftest.py::pytest_unconfigure` chiama `os._exit()`
   **di proposito**, per non farsi bloccare da `threading._shutdown()` sul thread pool di
   uvicorn. È la popolazione storica: le 28 coppie orfane trovate sulla macchina portavano
   argv di pytest (`test_brokers_api.py`, `test_brim_api.py`, `test_brim_e2e.py`).
2. **uvicorn** — `scripts/test_runner/_server.py:162` passa
   `stdout=None if self.verbose else subprocess.DEVNULL`: **solo nelle corse verbose** il server
   eredita lo stdout del runner. Orfano PID 83692 confermato di questa famiglia.

**Rimedio applicato:** `_release_process_pools()` in `pytest_unconfigure`, chiamato
immediatamente prima di `os._exit`, che smonta il pool con `wait=True`; stessa cosa nel lifespan
di `main.py`. `shutdown_pool()` guadagna il parametro `wait` con la docstring che spiega perché
il default resta non bloccante.

**Effetto collaterale utile:** la regola «mai far passare una corsa attraverso `tee`» era una
**convenzione mia di sessione**, non una regola di progetto — `.github/copilot-instructions.md:62`
il `tee` lo *raccomanda*. Una categoria E2E vera (`front-utility files`, 20/20) attraverso `tee`
chiude in 77 s senza lasciare orfani. Niente da ritirare dal repo, ma la convenzione è morta.

**Non chiuso:** il produttore uvicorn resta diagnosticato e non corretto — le corse verbose
continuano a ereditare lo stdout.

---

## 3 · Il difetto che stava sotto la modale

Cercando dove mettere l'avviso è emerso che la conferma per il **cambio parametri** esisteva già
(`showScheduledRegenConfirm`). Il buco era un altro, e più grave.

`asset_source.py` cancellava la serie solo quando `params_changed AND provider_code_unchanged`.
**Cambiare provider** da `scheduled_investment` a un provider di mercato non cancellava nulla:
la serie inventata sopravviveva sotto il nuovo provider, e siccome il sync post-salvataggio usa
`start: 'resume'`, il nuovo provider ripartiva **dal giorno dopo l'ultimo prezzo inventato** e
non recuperava mai il passato reale. Il commento nel codice dichiarava la conseguenza ad alta
voce senza trarne la conclusione.

**Rimedio:** il cancello diventa un `wipe_reason` calcolato:

- `"params changed"` — codice invariato e provider (nuovo) parametrico;
- `"provider changed"` — codice cambiato e provider **esistente** parametrico.

Dopo il wipe, `resume` si risolve da solo in `min`: era già quello che il commento prevedeva.

---

## 4 · L'avviso che sapeva contare, ma contava la cosa sbagliata

L'avviso frontend doveva dire **quanto** sta per distruggere. Due tentativi sbagliati prima di
quello giusto, ed entrambi hanno insegnato qualcosa.

**Tentativo 1 — `end: oggi`.** Sotto-dichiarava: una serie parametrica è uno *scadenzario*,
quindi si estende legittimamente nel futuro, e il wipe cancella anche quei punti.

**Tentativo 2 — `end: 2999-12-31`.** Peggio: l'endpoint `assets/prices/query` **riempie ogni
giorno di calendario** dell'intervallo richiesto. Con 25 righe vere in archivio rispondeva 944
su una finestra di tre anni, e su una finestra di mille anni sarebbe andato in timeout. Un
numero plausibile e falso è peggio di nessun numero.

**Giusto:** `GET /assets/{id}/market-data/summary` — la stessa fonte su cui si appoggia il
cambio valuta — che restituisce `{prices, events_manual, events_provider, …}` contando le
**righe archiviate**. 25 è 25.

> Regola generale che ne esce: *un endpoint che riempie risponde con la larghezza della domanda,
> non con la dimensione del dato.* Se serve una cardinalità, va chiesta a chi conta le righe.

**`ConfirmModal` non aveva identità.** Esponeva solo testid generici (`confirm-modal-confirm`,
`…-cancel`), quindi due conferme diverse erano distinguibili solo dal **testo localizzato**, che
le regole di progetto vietano come selettore. Aggiunta la prop `testId` (più
`confirm-modal-message` sul corpo): è lo stesso rimedio già applicato a `sync-modal-start` e a
`data-validate-runs` — *il prodotto deve dire quale domanda sta facendo*.

---

## 5 · I test di regressione

**Backend** — `test_parametric_provider_semantics.py`, due regole che vivono in clausole di
schema e che una migrazione futura romperebbe in silenzio:

1. la **rimozione** del provider conserva prezzi ed eventi manuali e cancella i generati — non
   c'è codice applicativo che lo imponga: è `ON DELETE CASCADE` su
   `AssetEvent.provider_assignment_id` più `PRAGMA foreign_keys=ON`;
2. il **cambio** di provider scarta la serie inventata.

Prova che il test prova qualcosa: contro `asset_source.py` **di HEAD** → 1 rosso (il cambio) e
1 verde (la rimozione). Esattamente la divisione attesa.

**Frontend** — un E2E che guida entrambi i rami: annullare non distrugge, confermare sì.

Tre trappole incontrate scrivendo i test, tutte utili:

- `identifier=None` non passa: vuole `""`.
- Gli eventi si scrivono come `{asset_id, events:[{date,type,value,notes}]}`, non piatti.
- **`'min'` è una parola chiave di *sync*, non di query.** `SyncStartDate = date | Literal["min"]`
  vale per `assets/prices/sync`; gli endpoint di *query* la rifiutano con 422. Lo stesso errore
  era finito anche nel mio helper frontend.
- Il conteggio prezzi cresce di 1 fra il seeding e il salvataggio, perché aprire la pagina di
  dettaglio **persiste il prezzo corrente**. Non è distruzione: l'asserzione giusta dopo
  l'annullamento è «non è sceso», non «è identico».

---

## Stato

| punto | esito |
|---|---|
| FM3 | ✅ chiuso e verificato (219/219) |
| orfani forkserver | ✅ causa trovata e corretta lato pytest; lato uvicorn diagnosticato, non corretto |
| wipe al cambio provider | ✅ backend + avviso frontend, provati |
| test di regressione | ✅ backend (A/B contro HEAD) + E2E (14/14) |

**Todo lasciato aperto:** `risk-catalog-error-state` — `data-catalog` vale `pending` sia per
«lento» sia per «fallito», e `loadError` non viene pubblicato. Da chiudere quando si rimetterà
mano ai test di risk.

---

# Seguito — i tre rossi che solo il carico sapeva produrre

I due rossi rimasti dopo la chiusura dei quattro punti (`asset-event-delete`, `risk`) non erano
test fragili: erano **tre difetti di prodotto distinti**, tutti della stessa famiglia — *un
parametro che arriva tardi butta via un lavoro che l'utente ha già chiesto, senza dirlo*.
Correggendoli ne è emerso un quarto, identico nella forma.

## 1 · Il catalogo di rischio che non arriva mai

`clientSession.ts:44-49` — la **prima** risoluzione d'identità incrementa la generazione di
sessione e **ritorna senza eseguire i resetter**. Tutte le transizioni successive li eseguono.

Una richiesta partita prima che l'app sapesse chi è l'utente viene quindi scartata all'arrivo
*e* il suo slot in-flight non viene mai liberato — perché l'unica cosa che lo libera è proprio
il resetter saltato. Il catalogo ha **un solo slot**: da lì in poi ogni chiamata si aggancia a
quella promessa e riceve `null`. Il pannello resta a `data-catalog="pending"` per tutta la vita
della pagina, senza eccezioni e senza nulla a schermo.

Le *query* sopravvivono perché la loro chiave di cache contiene l'id utente: dopo la
transizione cadono su un'altra voce. Il catalogo no.

**Correzione:** `releaseWhenSettled(promise, release)` in `riskStore.svelte.ts` — lo slot si
libera quando la promessa si conclude, non quando la generazione coincide. Più
`data-catalog="error"` e `loadError` su catalogo nullo, così «lento» e «fallito» smettono di
essere lo stesso attributo.

> **Ipotesi scartata per prima.** Avevo attribuito il blocco ai `finally` condizionali in
> generale. Falso: `invalidateRisk()` pulisce tutti e tre gli slot ed è registrato sia sul
> reset di sessione sia sulle mutazioni di portafoglio. Il test unitario scritto su
> quell'ipotesi **passava anche contro HEAD**, che è il modo in cui l'ipotesi è caduta.
> Riprodurre il buco vero richiede `vi.resetModules()` più un re-import di *entrambi* i moduli,
> perché serve `hasResolvedIdentity === false`, cioè uno stato di modulo vergine.
> Il test riscritto **fallisce contro HEAD** (`expected null to deeply equal {items}`).

## 1b · …e che, una volta scartato, non riprova mai

Liberato lo slot, la corsa successiva ha mostrato `data-catalog="error"` invece di `pending` —
il nuovo stato ha ripagato immediatamente, distinguendo «lento» da «fallito». Ma restava
`error` per 44 rilevazioni su 20 s: **il catalogo non riprovava mai**.

`fetchRiskCatalog` restituisce `null` quando la generazione di sessione **o quella di cache** si
muove durante la richiesta. E su una pagina asset quella di cache si muove per un motivo
banalissimo: **aprire la pagina persiste il prezzo corrente**, che notifica i listener di
mutazione del portafoglio, che invalidano il rischio. Sotto carico quella scrittura cade
esattamente dentro la finestra della fetch del catalogo.

**Correzione:** un ciclo di al massimo 3 tentativi che ri-campiona le generazioni a ogni giro.
Uno scarto significa «la risposta descrive un mondo che non esiste più», non «la richiesta è
fallita»: la reazione giusta è richiedere, non restituire un `null` che il chiamante può solo
riportare come errore. Stessa forma applicata anche allo scenario-catalog.

> Il retry ha cambiato la semantica del test scritto al punto 1, che si aspettava `null`. È
> stato riallineato all'invariante che conta davvero — *una fetch a cavallo della prima
> risoluzione d'identità consegna comunque un catalogo* — e resta rosso contro HEAD.

## 2 · Il confronto che sparisce fra il click e la risposta

`RiskAnalysisPanel.svelte:322` — un `$effect` sorvegliava una *signature* (`scope`, date,
valuta, tasso privo di rischio) e al suo cambio azzerava generazioni, risultati e flag di
caricamento **di tutte e quattro** le analisi su richiesta.

Sulla pagina di dettaglio asset quella signature **si assesta tardi**: `dateStart` viene
riscritto da `resolveMaxStartFromChartData()` quando arrivano i prezzi
(`assets/[id]/+page.svelte:1084`) e `displayCurrency` quando arriva l'asset (`:1052`). Sotto
carico entrambi atterrano *dopo* che l'utente ha premuto Confronta.

Esito: il risultato in volo viene scartato — giusto, era calcolato su parametri superati — ma
**la richiesta viene scartata con lui**. `comparisonLoading` torna a `false`, l'intero blocco
dei risultati non si rende, e l'utente resta senza grafico, senza rotella e senza errore.
Nessuna traccia che dica «ripremi».

**Correzione:** prima dell'azzeramento si annota quali analisi erano in volo e le si **ri-lancia**
dopo. Scartare la risposta è corretto; scartare la domanda no.

## 3 · La riga di distribuzione che non c'è ancora quando salvi

`DistributionEditor.svelte:172` — `addEntry` è `async`: alla prima invocazione carica l'elenco
dei paesi. Il commento sopra documenta già una correzione precedente («cliccare prima che
arrivassero produceva una voce con chiave vuota, che il genitore scartava in silenzio»): quella
correzione ha reso la voce **giusta**, non **tempestiva**. Il gestore del click ritorna prima
che la riga esista, quindi un Salva premuto subito dopo salva **niente** — e la modale si chiude
come se fosse andato tutto bene.

**Correzione:** `addingEntry` con `data-busy` e `disabled` sul pulsante. La finestra esiste
ancora, ma ora è **visibile** — all'utente e al test. Lato test, la barriera che i due test
gemelli avevano già (attendere il totale) è stata aggiunta al terzo, e i timeout di 3 s alzati a
10: 3 s è una scommessa sulla latenza, non una barriera.

## 4 · L'editor dati che perdeva le cancellazioni in sospeso

`AssetDataEditorSection.svelte:180` ricostruiva `eventRows` da zero a ogni nuovo riferimento
dell'array `events`. Il genitore ne assegna uno nuovo a **ogni** `loadChartData()`
(`assets/[id]/+page.svelte:1165`), da ~10 punti di chiamata — compreso il caricamento iniziale
della pagina, che sotto carico è ancora in volo mentre l'utente marca le cancellazioni.

Le righe con `status !== 'original'` non esistono nei dati del server: sparivano. `dirtyCount`
tornava a 0 e Salva si disabilitava da solo, in silenzio.

L'invariante era **già dichiarata** otto righe più sotto, a `:188`: *«We don't rebuild eventRows
from scratch to preserve the user's pending edits/deletes.»* Era la riga 180 a violarla.

**Correzione:** non si ricostruisce mentre la sezione è sporca, e `prevEvents`/`prevChartData`
restano non consumati, così il primo aggiornamento successivo al salvataggio entra normalmente.
Nessuna politica di merge: chi sta scrivendo non si vede strappare il documento di mano.

---

## Regola che se ne ricava

Le quattro correzioni hanno la stessa forma. In tutte, un *ingresso* arriva più tardi del
previsto e il codice reagisce **buttando via** — un risultato, una richiesta, delle modifiche
locali — trattando l'arrivo tardivo come se annullasse anche l'intenzione che l'aveva
preceduto.

> *Scartare una risposta superata è corretto. Scartare con essa la domanda che l'ha generata è
> perdita di dati, e passa inosservata perché non fallisce niente: semplicemente non succede
> niente.*

E il corollario operativo già usato tre volte in questa campagna: **un rosso che compare solo
sotto carico è un difetto di prodotto, non un difetto di test.** Il parallelismo non li ha
creati; ha solo allargato la finestra abbastanza da renderli riproducibili.

## Numeri sul parallelismo (per non rimisurarli)

151 unità backend girano in parallelo — `services` 80, `api` 51, `utils` 12, `schemas` 8.
Restano seriali **3 azioni**: `api auth` (scrive stato globale: utenti e token) e le due di
`e2e` (`brim-e2e`, `search-to-prices`). Le categorie sono seriali **fra loro** di proposito
(`_consolidate.py:307`): la suite fa oscillare il database apposta — `db` popola, `services`
svuota, `api` ripopola — quindi non esiste un istante in cui valga la precondizione di tutte.

---
---

# Corsa a 8 worker — quattro difetti, tre strati diversi

Il comando dell'utente (`--coverage --workers 8 --fresh-run all`) chiudeva con 5 worker su 8
rossi. Ogni ipotesi è stata decisa con una **misura** prima di scrivere codice.

## 1 · `database is locked` — chi *aspetta* e chi *tiene*

Il primo esperimento ha ucciso l'ipotesi sbagliata: con `busy_timeout` a 30 s la corsa
diventava verde. Se il gestore di attesa fosse stato saltato (percorso di *lock upgrade*), un
timeout più grande non avrebbe cambiato nulla. Il problema era **la durata**.

La prima sonda misurava `begin` → `commit` e dava 16,1 s: **numero inutile**, perché l'attesa
avviene *dentro* la transazione e quindi somma attesa e possesso. La separazione che funziona:

> SQLite prende il lock di scrittura alla **prima istruzione di scrittura**. Quindi
> `attesa` = durata di quella istruzione, `possesso` = commit meno la sua fine.

Solo dopo la separazione il quadro si è risolto: **un** solo scrittore teneva 10,3 s, tutti
gli altri aspettavano fino a 13,7 s e tenevano millisecondi. Fame, non deadlock.

**Causa**: `bulk_upsert_prices` scriveva un'intera storia prezzi in **una** transazione —
45 666 righe, `IN (...)` con 45 666 parametri (il limite documentato di SQLite è 32 766).
È un difetto **di produzione**: chi sincronizza una storia lunga fa fallire con 500 le
scritture dello scheduler e dell'altra scheda aperta.

**Correzione**: commit a fette da 1000 date. Possesso 10,3 s → 1,23 s, attesa 13,7 s → 0,16 s,
durata di categoria invariata. Le fette sono sicure perché nel merge F.4 ogni data consulta
solo la propria riga.

`BEGIN IMMEDIATE` generalizzato è stato **considerato e scartato**: farebbe prendere il lock
esclusivo anche alle transazioni di sola lettura, serializzando gli 8 worker e punendo le
letture analitiche lunghe (FIFO, rischio).

**Perché anche il timeout**: la durata di una fetta scala con carico e strumentazione — sotto
coverage le stesse fette costano ~4×. Le fette limitano quanto un scrittore **tiene**; il
timeout limita quanto un altro è disposto ad **aspettare**. Nessuno dei due basta da solo.

FX lo fa già meglio: `upsert_rates_bulk` usa `INSERT … ON CONFLICT` nativo invece di
DELETE + `add_all`. Portare `bulk_upsert_prices` alla stessa forma toglierebbe il bisogno
delle fette — **non fatto**, perché la semantica F.4 (`None` preserva, `-1` annulla, più la
guardia OHLC lato Python) lo rende delicato.

## 2 · Due commenti che mentivano

Entrambi portanti da anni, entrambi falsi alla misura:

| commento | realtà |
|---|---|
| «no FK check in test» (broker_id=1 preso a prestito) | `PRAGMA foreign_keys=ON` su ogni connessione |
| «Five seconds is far beyond any transaction this app opens» | misurato 10,3 s |

> Un commento che mente è peggio di nessun commento: sposta la diagnosi altrove per anni.

Nello stesso file, `_unique()` era un timestamp al millisecondo: 8 worker partono dentro lo
stesso millisecondo e `brokers.name` è UNIQUE. Stessa famiglia di `.first()` non è un'identità.

## 3 · Il frontend a 8 worker era **più lento** che a 4

Non un'ipotesi, una misura su `front-utility` (165 test):

| configurazione | esito | tempo |
|---|---|---|
| 8 worker + coverage | **20 rossi** | 5,8 min |
| 8 worker, senza coverage | **10 rossi** | 4,3 min |
| 4 worker + coverage | **165/165** | 3,3 min |
| 5 worker + coverage | **165/165** | 3,5 min |

Più lento *e* rosso è la firma del **thrash**, non del carico: 10 core logici non reggono 8
Chromium più `ceil(8/2)=4` uvicorn più il tracciamento della coverage. Tutti i rossi ai-export
erano la **stessa** riga (timeout sul login): una causa sistemica, non tanti flake.

`resolve_e2e_workers()` limita a `cpu_count()//2` (l'euristica di Playwright), e **lo dichiara**:
`🧵 Playwright workers: 5 (capped from 8: 10 logical cores)`. `--workers 8` resta 8 sul backend,
dove paga. Un numero non va mai disobbedito in silenzio.

## 4 · Il DB si azzerava, i file su disco no

L'ultimo rosso — `IWR-001`, il parse dell'import wizard — non si riproduceva: verde in
isolamento, verde a 5 worker, verde a 5 worker con coverage. Solo la suite **intera** lo
faceva comparire.

Ipotesi scartate con misura, non con l'intuito:

- **il mio `busy_timeout`**: l'endpoint di parse non scrive su DB, e con WAL i lettori non
  aspettano lo scrittore → scagionato;
- **parse fallito lato server**: in `failed/` solo i 20 `plugin_test.csv` voluti → mai fallito;
- **cold start del process pool** (forkserver + 4 interpreti): misurato **1,08 s** → non 30 s.

La causa era altrove, e visibile a occhio una volta guardata:

```
broker nel DB:      1 … 28
cartelle su disco:  1 … 308   (6490 file, 182 copie dello stesso generic_simple.csv)
```

I file dei broker vivono su disco indicizzati per **id** (`broker_reports/uploaded/broker_21/…`),
la riga del broker vive nel DB. Ricreare il DB **rinumera i proprietari** di file che nessuno
ha cancellato: ogni cartella 1-28 era un broker di una corsa precedente che impersonava in
silenzio uno di oggi. Un test che sceglie «il primo file di nome X» prende un file diverso a
seconda di quante corse l'hanno preceduto.

> **Sono un unico dataset.** Distruggere il database e lasciare i file è come cancellare
> l'anagrafe e tenere gli indirizzi.

`_reset_test_file_store()` azzera `broker_reports` e `custom-uploads` insieme al `.db`.
Entrambi si ricostruiscono da soli (`db populate`, e gli avatar dal marker `.avatars_seeded`
che sta *dentro* la cartella). Da 308 cartelle/6490 file a 6/16.

## 5 · Il test che falliva senza dire perché

`IWR-001` aspettava 30 s che `import-wizard-continue` si abilitasse, poi riportava soltanto
«un bottone era disabilitato». Ma il bottone è disabilitato **sia** mentre il parse gira **sia**
quando è fallito: la prima è un'attesa sensata, la seconda non si risolverà mai.

Il prodotto la diagnosi ce l'aveva già — `import-wizard-parse-errors`, con tanto di commento
«show WHY, not just Error» — ed era il test a non chiederla. Aggiunto `data-parse-state`
(`idle|parsing|ok|partial|error`) sul contenitore dello step 3, e `waitForParseVerdict()` in
`app-events.ts`: se il verdetto è `error`, il test **legge il motivo e lo rilancia**. Applicato
ai quattro spec che avevano la stessa attesa cieca.

> Stessa forma di `data-busy`, `data-validate-runs`, `sync-modal-results`: quando un test deve
> distinguere due stati, è il prodotto che deve saperli dire.

---

## Il rosso che non si lascia riprodurre — e le ipotesi che ha ucciso

Corsa dell'utente, 8 worker: **9 rossi tutti nel worker 7**, gli altri sette verdi. Codice
identico al mio verde (commit `af87ede8`, albero pulito), quindi il rosso dipende dallo
**stato**, non dal codice.

**Tre misure, non tre opinioni:**

| ipotesi | prova | esito |
|---|---|---|
| il log backend contiene la causa | finestra `2026-08-16T08:0[678]` estratta: 203 righe, 3 ERROR di cui 2 fixture volute e 1 plugin rotto per contratto | ❌ nessuna traccia |
| interferenza fra unità sullo stesso processo | **tutte le 80 unità in una sola invocazione pytest** — contaminazione massima possibile | ❌ **2682 passed** |
| il rosso è deterministico | due riproduzioni indipendenti a 8 worker, stessa pre-passata da 80 unità, stesso totale di 2682 test | ❌ verde, exit 0, due volte |

I worker eseguono **una sola pytest per più unità** (`worker 6: 14 unit(s) | 783 passed` è una
riga di riepilogo sola): condividono quindi stato di processo. Era l'ipotesi più promettente ed
è caduta nel modo più netto — messe *tutte* insieme, non si disturbano.

Resta la concorrenza reale: 8 processi più 4 worker uvicorn sullo stesso file SQLite. È l'unica
differenza fra la sonda verde e la corsa rossa.

> **La lezione operativa non è la diagnosi, è la prova.** La corsa fallita è girata senza
> `--log-dir`, quindi le uniche informazioni sopravvissute erano gli otto totali per worker.
> Per questo `--log-dir` ora vale `.testLog` **di default**: la prova non può essere opzionale,
> perché la si vuole proprio quando non ci si aspettava di averne bisogno. I log per worker
> registrano elenco unità, exit code e output — cioè esattamente ciò che mancava.

## `--fail-fast` invertito: la scelta e il perché

Prima: fermarsi al primo rosso era il default, `--no-fail-fast` lo disattivava. Ora è
l'opposto, e `--no-fail-fast` è stato **rimosso** invece che lasciato come no-op — un flag che
non fa nulla è una bugia in più nella `--help`.

La ragione è empirica e viene proprio da questa corsa: **nove rossi in un worker sono quasi
sempre nove sintomi di una causa sola**, e fermarsi al primo nasconde la forma del guasto,
costando una corsa intera per ogni rosso da riscoprire.

Aggiornati insieme al codice i **sette** punti in cui la documentazione lo descriveva
(`test-author.agent.md`, le due SKILL, `index.md`, tre punti di `runner_architecture.md`):
togliere il flag e lasciare i documenti avrebbe solo spostato la bugia.

## `ON CONFLICT` per `bulk_upsert_prices`: sì, ma non nella forma che sembrava

L'idea di partenza — esprimere la semantica F.4 in SQL con `CASE WHEN excluded…` — è
**sbagliata**, per due motivi misurati:

1. **Non toglie le fette.** SQLite ha un tetto di 32766 parametri di bind; a 10 colonne per
   riga sono ~3200 righe per istruzione, contro le ~45k di uno storico completo. Il chunking
   resta obbligatorio comunque, quindi la motivazione principale cade.
2. **La guardia OHLC non è esprimibile bene.** Il ramo di allargamento
   (`min(merged_low, close)`) dipende dai valori **fusi**, cioè dalla riga esistente: servirebbe
   partizionare le righe in due gruppi e duplicare lunghe espressioni `CASE` — spostando
   semantica portante da Python leggibile a SQL difficile da verificare.

**La forma giusta è l'altra**: Python continua a fare tutta la fusione (la SELECT serve comunque
per «preserva»), e l'`ON CONFLICT` sostituisce solo la coppia **DELETE + INSERT**. Semantica
identica al 100%, un'istruzione in meno, e l'`id` della riga non viene più riciclato a ogni
scrittura. Verificato che sia sicuro: `UniqueConstraint("asset_id", "date")` esiste e
**nessuna FK punta a `price_history.id`**.

### Il difetto trovato per strada: un commento che mente su `fetched_at`

```python
# Manual entries keep fetched_at=None (no "fetch" happened), matching prior behavior.
fetched_at=utcnow() if source_plugin_key != "MANUAL" else None,
```

Misura: `SELECT COUNT(*) … WHERE fetched_at IS NULL` → **zero righe**, MANUAL comprese. Il
`default_factory=utcnow` del modello scatta al flush e sovrascrive il `None`; la colonna è
`NOT NULL` nello schema, quindi non potrebbe essere altrimenti.

E per fortuna: il fingerprint della cache di portafoglio è `COUNT + MAX(fetched_at)`
(`portfolio_engine.py:2182`). Se le scritture manuali avessero davvero `fetched_at=NULL`,
**modificare a mano un prezzo già esistente non cambierebbe né il conteggio né il massimo** — la
cache resterebbe valida e la modifica dell'utente invisibile. Il commento descrive quindi non
solo qualcosa che non accade, ma qualcosa che sarebbe un difetto se accadesse.

Conseguenza pratica per la patch: con `insert().values()` di Core il default ORM **non**
scatterebbe e si otterrebbe un errore NOT NULL. Va passato `utcnow()` esplicito — che è anche
il comportamento reale di oggi.

> Nota a margine: `PriceHistory.adjusted_close` è dichiarata nel modello e **non è mai usata**
> in tutto il backend. Colonna morta.

## Orfani forkserver: era già risolto, e la regola «mai `tee`» si può ritirare

Fermando la raffica sono comparsi cinque processi superstiti. La misura:

```
PID    PPID  STAT  ETIME          COMMAND
83692     1  S     01-22:43:24    multiprocessing.forkserver.main(...)   ← orfano
83693 83692  S     01-22:43:24    (figlio)
84755 83692  S     01-22:41:28    (figlio)
84794 83692  S     01-22:41:21    (figlio)
84795 83692  S     01-22:41:20    (figlio)
```

`PPID 1` = riadottato da init; il capo è il **processo di controllo forkserver** in persona,
vivo da quasi due giorni con quattro figli appesi. Esattamente il meccanismo che il piano
ipotizzava — ma la conclusione è l'opposto di quella attesa:

`main.py:276` chiama già `shutdown_brim_parse_pool(wait=True)` nello spegnimento, e quella riga
è entrata il **2026-08-15 18:49**. L'orfano è nato intorno al **14 agosto**: lo *precede*. Non
era un difetto vivo, era un residuo di prima della correzione.

Le due verifiche che lo confermano:

1. dopo la suite completa a 8 worker, `ps` non mostra **nessun** forkserver e la 6041 è libera;
2. una corsa `api all --workers 4` **attraverso `tee`** è terminata in **3m01s con exit 0** — la
   pipe si è chiusa da sola.

Quindi la convenzione di sessione «mai far passare una corsa attraverso `tee`» **si ritira**.
Non era una regola di repo: `copilot-instructions.md:62` raccomanda `tee`, ed è di nuovo il
comportamento giusto. Nota: la regola era un aggiramento che ha funzionato per mesi mascherando
un difetto già corretto — vale la pena rimisurare gli aggiramenti, non solo tramandarli.

## Esito finale

Suite completa `--workers 8 --fresh-run all` con i flag di pulizia copertura dell'utente:
**🎉 ALL TESTS PASSED, exit 0**, copertura backend **90,53%**. Le sette occorrenze di `❌` nel
log sono messaggi *attesi* di test che verificano la gestione errori
(`MOCKFX_FAIL: simulated provider failure`), non fallimenti.

---

## La domanda «anche db populate è in parallelo?» — no, ma ha scoperto altro

**Risposta diretta**: no. `_inventory.py:60` dichiara
`SIDE_EFFECTING = {("db","create"), ("db","populate")}`, che le esclude dalla passata parallela.
E sotto `all` / `all-backend` `_parallel_classes` restituisce **solo `(PURE,)`**, perché READ e
WRITE_SCOPED richiedono che si nomini *una sola* categoria: la suite fa oscillare il file di
proposito (`db` popola → `services` svuota → `api` ripopola) e ogni categoria ripristina la propria
precondizione appena prima di girare.

### Ma la garanzia PURE aveva un'eccezione non dichiarata

`PURE` significa, testualmente, «no DB, no server: shares anything». La classificazione è provata
**staticamente**, leggendo il file di test e tre soli helper (`test_utils`, `test_db_config`,
`test_server_helper`). **I `conftest.py` non vengono letti.**

E `backend/test_scripts/conftest.py:16` ha una fixture `scope="session", autouse=True` che apre
`app.db` con `sqlite3` grezzo e ci **scrive** (`INSERT OR IGNORE` sui default + `UPDATE
enable_registration='true'`). Essendo autouse gira in *ogni* processo pytest: sotto `--workers 8`
sono otto scrittori sullo stesso file entro un secondo l'uno dall'altro, **inclusi i worker PURE**.

Tre spigoli, tutti misurati:

| difetto | prova |
|---|---|
| nessun `busy_timeout` | `PRAGMA busy_timeout` su una connessione stdlib → **5000 ms**, un sesto dei 30000 di `session.py:54` |
| connessione mai chiusa | `with sqlite3.connect(...) as c: pass` poi `c.execute('SELECT 1')` → **riesce**. Il context manager fa commit, non close. Una connessione per worker, aperta per tutta la sessione, che tiene indietro il checkpoint del WAL |
| errore inghiottito | `except sqlite3.Error: pass` — e il docstring stesso dice che un `enable_registration` non ripristinato fa fallire «~50 test non correlati» con un messaggio «che non punta neanche lontanamente alla causa vera» |

Il terzo è il più costoso, ed è **esattamente la forma dei 9 rossi in un solo worker** mai
riprodotti: molti fallimenti scorrelati, concentrati, senza traccia nel log.

### Correzione

`contextlib.closing()` attorno alla connessione; `timeout=_SEED_LOCK_TIMEOUT_S` = 30 s, allineato
all'engine con un commento che dice *perché* quel numero e non un altro; e il ramo d'errore
**diviso in due**: `no such table` resta silenzioso (è il caso benigno documentato, DB non ancora
migrato), qualunque altro `OperationalError` — il lock su tutti — alza un `warnings.warn` che si
nomina. Il silenzio era ciò che rendeva caro quel guasto.

Verificato: DB bloccato → 1 warning col messaggio giusto; tabella assente → 0 warning; dopo la
fixture **0 connessioni aperte** e `enable_registration = true`.

---

## La gara del file store BRIM — un errore di contenuto per un problema di indirizzo

Un solo rosso E2E in una corsa completa: `tx-import-resolution.spec.ts` IWR‑002, con
`Parse produced no usable file … [Errno 2] No such file or directory:
'…/broker_reports/uploaded/broker_1/76811a4e‑….csv'`. Gli IWR‑003…012 subito dopo usavano lo
**stesso** file e passavano: quindi non era stato cancellato, era stato **momentaneamente
assente**.

La prova sta nel log strutturato del backend, alla stessa millesima:

```
{"file_id": "76811a4e…", "from_status": "uploaded", "to_status": "parsed",
 "event": "Moved file", "timestamp": "2026-08-16T10:46:31.179329Z"}
```

Un parse riuscito promuove il file da `uploaded` a `parsed`, e quella promozione è una
**rinomina fisica**. Un parse concorrente aveva risolto il percorso *prima* della rinomina e
aperto il file *dopo*.

**Perché la separazione dato/sidecar conta.** L'elenco dei file è guidato interamente dal JSON
di corredo: `_find_metadata_path` scandisce ogni cartella di stato e ogni `broker_*`, quindi una
riga compare appena esiste il `.json`, qualunque cosa faccia il file dati. Ma `get_file_path`
ricavava la cartella dal **contenuto** del sidecar (`file_info.status`), e `_move_file` rinomina
il dato **prima** e riscrive il sidecar **dopo**. In quella finestra chi legge calcola la
cartella vecchia per un file che vive già in quella nuova.

Da cui la regola: **dedurre l'indirizzo dallo stato è una scorciatoia; il file stesso è il
fatto.** `get_file_path` ora, quando il percorso derivato non esiste, scandisce come già faceva
il sidecar.

Più una ritentata sola in `parse_file`, resa sicura non dal tipo d'eccezione (il plugin ha già
convertito ENOENT in `BRIMParseError`) ma da **due guardie**: si rilancia se il percorso
originale esiste ancora (il guasto era vero), e si rilancia se la ri‑risoluzione dà `None` o lo
stesso percorso. Un test dedicato fissa che un errore di lettura genuino **non** venga
riciclato.

Trovate per strada tre violazioni della regola di I/O asincrono: `move_to_parsed` e i due
`move_to_failed` in `brokers.py` facevano rinomina + lettura + scrittura + unlink **sul loop**.

> Nota di metodo: una grep precedente aveva mancato la riga decisiva perché il filtro
> `grep -v '^…brim_provider.py:8[0-9][0-9]'` escludeva per caso proprio `move_to_parsed` alla
> riga 883. Un filtro per intervallo di righe è cieco per costruzione.

---

## `default_isolation` di categoria: una promessa fatta a nome di 85 unità

A 8 worker la passata parallela di `services` è caduta con 9 rossi in un solo worker.
`test_fx_conversion` trovava un tasso EUR/USD, convertiva EUR→USD, e la **conversione inversa**
falliva: nel frattempo la tabella era stata svuotata. I test seguenti non trovavano più nulla.

Colpevoli, sullo stesso banco di prova ma su un altro worker: `test_fx_core.py:44` e
`test_fx_sync_service.py:36`, due fixture **autouse** che fanno `DELETE FROM fx_rates` — tabella
intera — **prima di ogni test**.

Tutte e tre ereditavano `default_isolation="write-scoped"` da `_backend_services.py:670`, la cui
motivazione scritta è:

> *«ognuno apre la propria sessione e crea le righe che poi rilegge»*

Quella frase è **la clausola portante**, ed è un'affermazione su *ogni* unità. Tre la
violavano. Una fixture autouse che tronca una tabella condivisa non è «le proprie righe»; e
un'unità che semina una volta per **modulo** perde tutto contro una vicina che tronca una volta
per **test**.

Uno scan mirato (`delete(Model)` senza `.where`) ha trovato anche
`test_global_settings_service.py`, che azzera `GlobalSetting` — cioè la tabella dove la fixture
di `conftest` scrive `enable_registration`, cioè il guasto che la sua stessa docstring descrive
come capace di far fallire «~50 test non correlati» con un messaggio che non punta alla causa.
È la spiegazione più probabile dei 9 rossi mai riprodotti di una corsa precedente.

Quarta esclusa: `fx-conversion` stessa. Le sue assert riguardano **la riga EUR/USD più vecchia e
più recente dell'intera tabella** (backward fill, confine del tasso mancante), e il servizio
sotto test interroga `fx_rates` **senza filtro su `source`**: filtrare le query del test non
servirebbe, perché è il prodotto a leggere la riga estranea. Un'altra unità
(`test_lots_analysis_service`) inserisce EUR/USD storici e sposta il confine misurato.

Il meccanismo per dichiararlo esisteva già e non era mai stato usato: `exclusive_because` su
`add_test` **è** la dichiarazione WRITE_GLOBAL (`_inventory.py:326‑330`), e in
`_backend_api.py:695` c'era già il precedente esatto su
`global_settings.enable_registration`. La classe di problema era nota per `api` e mancata per
`services`.

**Regola generalizzabile**: un default di isolamento a livello di categoria è una promessa fatta
a nome di unità che non l'hanno firmata. Va accompagnato dal criterio che la rende falsificabile
— qui: *nessuna fixture può troncare una tabella condivisa* — perché altrimenti la si verifica
solo per osservazione, e l'osservazione era stata fatta a 4 worker.

---

## `--quiet` e `--log-dir` sono indipendenti, ma non del tutto

- **passata parallela** (`backend-parallel__worker*.log`): l'executor cattura **sempre**
  (`_executor.py:216`) e scrive **sempre** il file (`:112`). `-q` non toglie nulla.
- **unità seriali** (`all__*.log`): con `-q` `subprocess.run` usa `capture_output=True` e
  l'output catturato viene stampato **solo in caso di fallimento** (`_common.py:516‑519`). Nel
  file di un'unità passata restano intestazione, comando e `✅ PASSED`.

Quindi con `-q` conservi il rosso ma perdi il contesto dei verdi che l'hanno preceduto — che è
esattamente ciò che serve quando il sospetto è una cascata.

## `[tx-hygiene] disabled: …` — compare *perché* si è in parallelo

`tx-hygiene` fotografa gli id delle transazioni all'apertura di uno spec e alla fine cancella
«tutto ciò che è comparso da allora». L'inferenza *nuovo = mio* vale solo se gira uno spec per
volta; in parallelo gli spec si interlacciano e «nuovo» include righe che un altro worker sta
**usando in quel momento**. Quindi il meccanismo si autodisattiva sopra 1 worker
(`playwright.ts:84`) e lo dichiara.

Il successore corretto è `db-cleanup.ts`, che definisce la proprietà come **intersezione** di due
fatti: l'id l'ha restituito un mio commit **e** non era nello snapshot iniziale.

Resta una contraddizione minore: `_consolidate.py:189` imposta `LF_TX_HYGIENE=1`
**incondizionatamente** per la passata consolidata, che gira a 5 worker — accende una funzione
che in quella modalità non può mai partire, e stampa 5 avvisi per invocazione.

---

## Il rosso AI Export: come si distingue un budget stretto da un endpoint lento

Sintomo: `ai-export-contract.spec.ts:111 › Portfolio Dataset` muore su
`page.waitForResponse: Timeout 30000ms` mentre `waitForRequest` (8 s) era passato — la
POST a `/api/v1/ai-export/snapshot` **era partita**, la risposta non è arrivata in 30 s.

La tentazione è alzare il numero e andare avanti. Il numero *va* alzato, ma solo dopo aver
escluso che l'endpoint sia lento davvero — altrimenti si sta nascondendo un difetto di
prodotto dietro un'attesa più lunga.

### Le tre ipotesi, e come sono cadute

| ipotesi | prova cercata | esito |
|---|---|---|
| listener registrato tardi (schema FM3) | ordine delle righe in `helpers.ts` | **falsa**: `waitForRequest` e `waitForResponse` sono entrambi registrati a :123-124, **prima** del click a :125 |
| endpoint lento | misura diretta con backend di test | **falsa**: 0,32 s da sola, 1,06 s a freddo, **4,0 s con 8 chiamanti concorrenti** |
| DB gonfiato dalle categorie precedenti | ordine delle categorie nel log | **falsa**: `populate_mock_data --force` gira alla riga 1444, `front-ai-export` parte alla 1448 — è la **prima** categoria frontend, su DB fresco |

Quello che resta è la misura decisiva: **la stessa spec costa 6,7 s nuda e 44,8 s sotto
coverage**. Python + JS tracing moltiplicano ~7× ogni percorso pure-Python che lo snapshot
attraversa. Con quel fattore, un'attesa da 30 s finisce **dentro la coda** della
distribuzione: nella corsa reale le due spec sorelle sono passate a 36,2 s e 37,2 s — a
pochi secondi dalla stessa fine — e la terza ha perso la gara.

### La regola

> Un timeout su un percorso che ci si aspetta riesca non è mai un'asserzione di prestazione.
> Lo si attende solo quando qualcosa è già rotto, quindi alzarlo non costa nulla quando le
> cose funzionano e limita solo quanto tempo serve a *riportare* un guasto vero.

È la stessa regola già applicata a `COLD_START_TIMEOUT_S` nei test spawn-worker. La sua
metà mancante, emersa qui: **anche il budget che lo racchiude va alzato**. Il test fa
quattro export in fila; con `test.setTimeout(120_000)` e `API_TIMEOUT` a 90 s, una singola
risposta lenta farebbe scattare *prima* il timeout di test — che dice «il test è troppo
lungo», cioè niente — invece di `waitForResponse`, che nomina l'endpoint che si è fermato.
Quale dei due budget scatta per primo **decide la qualità della diagnosi** della prossima
volta.

### Come si misura un endpoint senza infrastruttura

`/tmp/lf_snapshot_bench.py`: login (cookie di sessione, non bearer — `POST
/api/v1/auth/login` risponde con `set-cookie: session=…` e nessun `access_token`), poi
`ThreadPoolExecutor` a 1 / 3 / 8 vie sullo stesso payload. Tre righe di output hanno chiuso
un'ipotesi che sarebbe costata mezza giornata di lettura del codice.

## `LF_TX_HYGIENE`: chiedere una funzione che non può attivarsi

`_consolidate.py:189` lo impostava **incondizionatamente** per una passata che gira a 5+
worker, dove la fixture si auto-disattiva (`playwright.ts:84`) perché «creato da quando ho
aperto questo file» smette di significare «mio» appena due spec si intrecciano. Effetto:
cinque righe di warning per invocazione, che nel log sembrano un problema e non lo sono.

Ora è condizionato a `E2E_WORKERS == 1`. Il costo di una richiesta impossibile non è zero:
si paga in rumore, e il rumore si paga nella diagnosi successiva.
