# Piano — Riscrivere la semantica dei test: da «assumere» a «verificare»

> Il piano P8 concluso è conservato qui accanto come `files/plan-p8-runner-migration.md`.
> Ad approvazione, questo va depositato nel journal come
> `plan-phase00TestSemanticsRewrite.prompt.md`, con collegamento incrociato da/verso
> `plan-phase00TestRunnerMigration.prompt.md`.

---

## 0. Le tue tre domande, con la risposta verificata

### «L'OOM è solo un problema di test, o ha evidenziato un problema di caching del prodotto?»

**È strumentazione di test, non prodotto.** La memoria che è esplosa è quella del **processo Node di
Playwright**, non del browser e non del backend. Il meccanismo:
`startJSCoverage({ resetOnNavigation: false })` fa sì che ogni test restituisca la copertura V8 di
*ogni script caricato dall'inizio*, e ogni voce porta con sé **il sorgente completo** dello script.
Finché ogni file di spec aveva il suo processo, quella roba veniva liberata dalla morte del processo;
consolidando, no. Il prodotto non ha un equivalente: nessun componente accumula i propri sorgenti.

**Però un difetto di caching di prodotto è saltato fuori davvero**, per un'altra strada, ed è già
corretto in questo albero: `NamedCache.clear()` svuotava la mappa delle voci ma lasciava il filtro di
ammissione W-TinyLFU di theine carico delle frequenze delle chiavi appena buttate. Una volta che la
cache aveva toccato `maxsize` **anche una sola volta**, ogni `set()` successivo veniva rifiutato
contro quei fantasmi e **la cache smetteva di memorizzare qualunque cosa, per sempre e in silenzio**.
Misurato su theine 2.0.0: 19 voci prima di un `clear()` si riprendono, 20 no. *Quello* sì è un difetto
di prodotto sotto uso intensivo, ed è esattamente la classe di problemi che avevi in mente.

### «W9 l'hai risolto o è ancora rotto? 10,6 s mi sa tanto di timeout»

**Ancora rotto, e non è un timeout.** L'errore è `expect(received).toContain(expected)` —
un'asserzione sincrona, che fallisce all'istante. I 10,6 s sono il corpo del test, non l'attesa di una
scadenza.

E il corpo del test è la causa: `setupSameCurrencyTransfer()` è costruito su **attese a orologio** —
`waitForTimeout(500)`, poi `waitForTimeout(2000)` — e il test aggiunge `200` + `500`. Il commento dice
*«Wait for WAC value to populate»* ma la riga sotto aspetta solo che l'input sia **visibile**, non che
abbia un **valore**.

La guardia nel prodotto **c'è ed è giusta**:

```js
const currentDisplay = formatDecimalForDisplay(value?.amount ?? '');
const nextDisplay    = formatDecimalForDisplay(next.amount ?? '');
if (currentDisplay === nextDisplay) return;   // blur senza modifica → non cambia modo
```

Se il blur arriva **prima** che il WAC sia popolato, il confronto è `'' ≠ '170,32…'`, la guardia non
scatta e il modo passa a manual. Il test non sta trovando un difetto: **sta generando** la condizione
che poi denuncia.

W9 non è quindi un caso isolato da sistemare di corsa: è **il piano intero in miniatura**. Assume
invece di verificare — lì il tempo, altrove la posizione. Per questo la sua correzione apre il piano
(tappa 0.1) invece di essere una nota a margine.

### «I test non devono avviare altri server» — i numeri ti danno ragione

Ricostruite 90 delle 93 invocazioni pytest dal log della corsa di chiusura:

| | Invocazioni | Tempo | Test | s/test |
|---|---:|---:|---:|---:|
| `test_api/` | 47 | **15,0 min** | 564 | **1,59** |
| resto seriale | 43 | 8,7 min | 1315 | 0,40 |
| passata parallela (PURE) | — | 0,6 min | 1494 | **0,022** |

`test_api` è **il 62 % del tempo seriale per il 30 % dei test**, e ogni invocazione avvia il proprio
uvicorn reimportando tutta l'app FastAPI per eseguire una dozzina di test.

> **Correzione, a misura fatta.** Qui avevo scritto «circa 11 dei 15 minuti sono avvio di server».
> **È falso, e la stima era mia**: misurato sul campo, l'avvio pesa **~1,3 s per modulo, ~68 s in
> totale (13 %)**, e la categoria passa da **8m43 a 7m40**. Il tempo `user` che sembrava crollare
> (7m03 → 1m36) non è confrontabile: la CPU del server condiviso sta *fuori* dall'albero di processi
> misurato.
>
> Il guadagno vero è un altro, ed è più grande di quello che avevo previsto: **i moduli non
> pretendono più la proprietà esclusiva della porta 6041**. Con 4 worker pytest su un solo backend:
> **283,9 s contro 460 s seriali (1,6×)**, senza aver ancora riscritto un solo test. La tappa 2 si
> giustifica per la concorrenza che abilita, non per i secondi di avvio che risparmia.

E la mina è già armata: `_force_kill_port()` **non esclude `os.getpid()`**. Oggi è innocuo perché ogni
invocazione ha il suo processo; nel momento in cui due moduli `test_api` condividessero un processo, il
secondo troverebbe la porta tenuta dal thread del primo, `lsof` restituirebbe il PID di pytest e **il
processo si manderebbe un SIGKILL da solo**.

---

## 1. Diagnosi: il runner non è più il collo di bottiglia, lo sono i test

Il piano precedente ha costruito inventario, scheduler, esecutore e broker di risorse. Funzionano. Ma
delle 294 unità **164 restano seriali per costruzione** (101 pytest + 63 Playwright), e il motivo non è
più il runner: è che **i test assumono invece di verificare**.

Tre forme dello stesso difetto, tutte misurate su questo albero:

| Assunzione | Dove | Quanto |
|---|---|---|
| **Posizione** — `[0]`, `.first()`, indici fissi | backend `test_api` | **562** occorrenze di `[0]`, in 44 file su 47 |
| | frontend `e2e` | **430** `.first()` "nudi" (non filtrati), in 49 spec su 60 |
| **Conteggio** — `len(x) == N`, `toHaveCount(N)` | backend | 159 in 36 file |
| | frontend | 35 in 13 spec |
| **Tempo** — attesa a orologio invece che a condizione | frontend | **921** `waitForTimeout` in 56 file, **452,9 s** di sonno dichiarato |
| | backend | 8 `time.sleep` in 5 file |

452,9 secondi sono **7,5 minuti per corsa** spesi ad aspettare a vuoto — e ogni singola occorrenza è
una scommessa che sotto carico si perde. È il motivo per cui parallelizzare oggi produce rossi
intermittenti: non perché il parallelismo sia difficile, ma perché **un test che assume il tempo o la
posizione è già rotto, e la serializzazione lo stava soltanto nascondendo**.

Da cui la conseguenza operativa che hai enunciato tu, e che il piano adotta come regola: un test di
lettura che si **cerca** il proprio dato è write-safe *per costruzione*, non per fortuna.

---

## 2. L'architettura di arrivo (la tua, formalizzata)

| Livello | Come gira | Cosa si prova, in più |
|---|---|---|
| **Backend atomico** (PURE) | multi-processo Python | il GIL li serializzerebbe; processi separati, nessuna risorsa condivisa |
| **Backend API** | **una sola istanza**, chiamate in **vera concorrenza** | oltre al percorso, la **capacità reale di reggere richieste concorrenti**: i rallentamenti diventano una mappa delle aree da ridisegnare |
| **Frontend lettura** | più schede Chrome in parallelo | non si danno fastidio per definizione |
| **Frontend scrittura** | più schede, **un solo backend** | è proprio lì che i colli di bottiglia devono emergere |

Tre regole che ne discendono, e che diventano vincolanti:

1. **I test non avviano server.** Il server è una risorsa dell'ambiente, avviata una volta sola.
2. **Le letture si cercano il dato.** Mai «il primo», «la prima pagina», «ce ne sono N». Si naviga
   finché non si trova ciò che serve, identificato da qualcosa di **proprio** — un id univoco creato
   dal test — non dalla sua posizione.
3. **Le attese sono su condizione.** Mai sull'orologio.

L'esclusiva su una risorsa resta possibile, ma diventa **un'eccezione da motivare per iscritto** nel
catalogo: dopo la riscrittura, un test che ancora la pretende sta dicendo qualcosa di vero sul
prodotto, e va ascoltato — non assecondato per inerzia.

---

## 3. Il metodo: non un esperimento apposta, ma un'ipotesi in più nel triage

Fra `[0]` e `.first()` ci sono **~1000 punti di chiamata**. Leggerli tutti è impraticabile e, peggio,
inaffidabile: molti sono innocui — un `.first()` su un locator già filtrato risolve a un elemento solo,
e infatti 45 dei 475 totali sono di quella forma. L'analisi statica sa **restringere**, non
**decidere**.

Avevo proposto un generatore di rumore. **Hai ragione a non esserne convinto**, e i tuoi due
argomenti reggono meglio del mio: chi lo avvia, chi lo ferma, con che ciclo di vita rispetto ai
worker — sono tre domande senza una risposta pulita, per costruire una condizione che *la corsa reale
produce già da sé*. Un backend condiviso con più worker che scrivono **è** il rumore. Un generatore in
più sarebbe una seconda sorgente di non determinismo da governare per misurare la prima.

**Quindi: li lanciamo, e basta.** Quando uno fallisce, la novità non è uno strumento ma **il
protocollo di analisi**: fra le cause da indagare entra, esplicita e prima delle altre, *«è stata la
forma della risposta?»* — il dato non era dove il test lo aspettava, la pagina conteneva altro, il
conteggio era diverso. Se l'indagine conferma, il test si rende write-safe; se no, è un difetto vero e
si tratta come tale.

Questo sposta il baricentro nel modo giusto:

| | Generatore di rumore | Protocollo di triage |
|---|---|---|
| Quando agisce | prima, in una passata apposta | **quando serve**, sul rosso vero |
| Costo | costruirlo, avviarlo, renderlo deterministico | zero: è una voce in una lista |
| Copertura | solo ciò che il generatore tocca | **tutto ciò che fallisce davvero** |
| Dopo il piano | codice da mantenere | **regola scritta**, che continua a valere |

E chiude dove dici tu: **una parte qui** (i rossi che questa corsa produce si correggono in questo
piano) e **il resto nelle skill** — perché il difetto è permanente e la contromisura deve
sopravvivere al piano che l'ha scoperto.

> **Conseguenza da mettere in conto fin d'ora**: consolidando e parallelizzando **compariranno rossi
> nuovi**, di test che oggi passano solo perché il dato capita al posto giusto. Non sono regressioni:
> sono la ragione del piano — e vanno corretti dentro la tappa che li scopre, non rimandati. Ogni
> tappa che tocca l'esecuzione si porta dietro il proprio budget di correzione.

---

## 4. Le tappe

### Tappa 0 ✅ — Rete di sicurezza (prima di toccare qualunque semantica)

- **0.1 ✅ — W9**: sostituire le attese a orologio con attese su condizione (il valore del WAC
  *popolato*, non l'input *visibile*). È il caso campione, e la sua correzione diventa l'esempio
  citato dalle regole scritte alla tappa 6.
- **0.2 ✅ — `_force_kill_port()` esclude `os.getpid()`** e smette di poter uccidere il processo che lo
  invoca. Difetto latente, ma sta esattamente sul percorso della tappa 2.
- **0.3 ✅ — Fotografia**: esiti e durate per unità **prima** di ogni modifica, per distinguere «rotto
  dalla riscrittura» da «già rosso». È la distinzione che nel piano precedente ha ripagato tre volte.

### Tappa 1 ✅ — `--log-dir`: rendere la corsa diagnosticabile

Richiesta tua, e prerequisito pratico di tutto il resto: senza log per unità l'esperimento della
tappa 3 non è leggibile.

- **1.1 ✅** `--log-dir PATH`: `mkdir -p`, **un file di log per unità**, con nome derivato dall'unità
  così che si trovino a colpo d'occhio.
- **1.2 ✅** **Generalizzare l'archiviazione** oggi sepolta in `_coverage.py::_archive_db()`: estrarla in
  un helper unico usato sia dalla coverage sia dai log. Se la cartella esiste già, i file precedenti
  finiscono in `00_archive/<YYYYMMDD_HHMM>/`.
- **1.3 ✅** **Compressione portabile.** Oggi giriamo su macOS, domani su Linux o Windows: quindi
  **niente binari esterni e niente probe di sistema**. La stdlib di Python li ha già tutti, e —
  misurato qui — **batte lo `zstd` esterno**:

  | | log 4,3 MB | db 1,4 MB |
  |---|---|---|
  | **`lzma` preset 1** | **0,16 MB (26,9×) in 0,04 s** | **0,25 MB (5,5×) in 0,04 s** |
  | `lzma` preset 6 | 0,15 MB (29,6×) in 0,49 s | 0,22 MB (6,4×) in 0,25 s |
  | `bz2` | 0,23 MB (19,1×) in 0,28 s | 0,33 MB (4,1×) |
  | `gzip` | 0,99 MB (4,4×) in 0,35 s | 0,34 MB (4,1×) |
  | *(`zstd -3` esterno, per confronto)* | *0,18 MB (24×) in 0,33 s* | *0,3 MB in 0,33 s* |

  **`lzma` a preset 1 è il punto ottimale**: rapporto praticamente uguale al preset 6 (26,9× contro
  29,6×) a **dodici volte la velocità**, e migliore dello `zstd` esterno su entrambe le grandezze.

  Il ripiego è quindi **interno alla stdlib**, non al sistema operativo:

  ```
  tarfile "w:xz" (lzma, preset 1)  →  "w:bz2"  →  "w:gz"  →  tar semplice
  ```

  `lzma` e `bz2` sono moduli opzionali di CPython (una build senza `liblzma` non li espone: capita su
  distribuzioni Linux minimali e in qualche container), quindi la scelta si fa con un `import`
  in `try`, non con un `which`. `gzip` e `zlib` sono sempre presenti: **l'ultimo scalino non fallisce
  mai**. Su Windows si può preferire `.zip` come contenitore, che Esplora risorse apre con un doppio
  clic — è un parametro, con un default per sistema operativo, non un ramo di codice diverso.

  > **Sul `Pipfile`: non va toccato, e non è una scelta ma un fatto.** `lzma` non è un pacchetto pip:
  > è **stdlib di CPython**, verificato — `.../Python.framework/Versions/3.13/lib/python3.13/lzma.py`
  > con l'estensione C in `lib-dynload/_lzma.cpython-313-darwin.so`, non in `site-packages`. Non
  > esiste un `pipenv install lzma` da fare, né come dipendenza di sviluppo né come runtime: se manca,
  > manca perché quel *Python* è stato compilato senza `liblzma`, e si rimedia a livello di sistema
  > (`xz-devel`, `liblzma-dev`) — mai da pip. È proprio quel caso che il ripiego qui sopra copre, ed è
  > la ragione per cui la catena esiste invece di dare `lzma` per scontato.
  >
  > Nota di contorno: `zstandard` **è** un pacchetto pip ed **è già installato** come dipendenza
  > transitiva, ma il piano **non lo usa** — non compare fra le dipendenze dirette del `Pipfile` e
  > appoggiarcisi significherebbe promuoverlo. In più, misurato, la stdlib lo batte. Se un domani lo
  > volessimo davvero, allora sì: **`[dev-packages]`**, come dici tu, perché serve solo alla
  > strumentazione di test e mai al prodotto.
- **1.4 ✅** **Anche il DB**: la tua perplessità — «i binari si comprimono male» — qui **non si verifica**.
  1,4 MB → 0,25 MB in 0,04 s, perché le pagine SQLite sono in gran parte testo e spazio vuoto.
  Archiviare il DB accanto ai log rende un rosso riproducibile **con i dati che l'hanno prodotto**, che
  è il pezzo che oggi manca di più — e con la tappa 3 che vive di rossi da capire, serve subito.

### Tappa 2 — Un solo backend, condiviso (il guadagno è la concorrenza, non i secondi di avvio)

Non è da inventare: **il pattern esiste già e funziona**. `playwright.config.ts` avvia
`./dev.py server --test --coverage` come **processo esterno sotto `coverage run`**, con `SIGTERM` e
30 s di grazia perché il flush della coverage non venga troncato.

- **2.1 ✅** Estrarre quel ciclo di vita in un servizio del runner, condiviso fra frontend e `test_api`.
  → `scripts/test_runner/_server.py`. **Fuori pista, due volte**: (a) il server sopravviveva allo
  spegnimento con PPID 1 — è `--reload` che forgia un supervisore che scavalca il segnale diretto al
  capo della catena `exec`; risolto con gruppo di processi proprio + `killpg`, e con un `--no-reload`
  su `dev.py server`. (b) `stop()` aspettava la *salute*, non la **porta**: un processo morente smette
  di rispondere mentre tiene ancora il socket, ed è proprio la finestra che fa trovare la porta
  occupata alla corsa successiva.
- **2.2 ✅** `test_api` smette di usare `_TestingServerManager`: niente uvicorn in-process, si parla con
  `API_BASE`. Dipende da 0.2. **Nessun test riscritto**: 44 su 52 moduli parlavano già HTTP.
  → **Ha confermato la premessa del piano meglio di qualunque analisi statica.** Con un uvicorn per
  modulo, chi azzerava `global_settings` veniva riparato in silenzio dallo *startup del modulo
  successivo*. Con un solo server nessuno ripara più niente, e il sintomo compare **lontano dal
  guasto** (un 404, un «setting was not initialized»). Corretto dove la garanzia stava davvero — la
  fixture di sessione ora *semina* i `GLOBAL_SETTINGS_DEFAULTS` con `INSERT OR IGNORE`, invece di
  fare `UPDATE` su una riga che non c'è.
- **2.2-bis ✅ (fuori piano)** **Dimensionare il backend sul parallelismo che lo colpisce.**
  `server_workers_for()` = metà dei client, minimo 1 garantito; la gallery resta a un quarto perché i
  suoi worker passano il tempo a disegnare. Il numero arriva fino a `dev.py` sia dal runner sia da
  `playwright.config.ts` (`E2E_WORKERS`), dove prima era un `'1'` scritto a mano.
  **Difetto trovato**: sotto coverage `--workers` veniva **scartato in silenzio** — `coverage run`
  traccia solo il processo che avvia, quindi N worker avrebbero misurato il supervisore (che non
  esegue codice d'app) buttando via tutto il resto. Risolto passando `--concurrency
  multiprocessing,…` **sulla riga di comando** e solo quando serve, per non alterare le corse pytest.
  Misurato: 3 worker, **tutti e 3 tracciati** (224 righe ciascuno), supervisore 0.
  E la domanda che contava davvero — SQLite regge? — **sì**: 8 client concorrenti, 80 scritture,
  **zero `database is locked`**, e la latenza *migliora* (mediana 22 ms → 7 ms, p95 276 → 39 ms).
- **2.2-ter ✅ (fuori piano, regressione mia)** Il server condiviso rompeva `test all --coverage`:
  `reuseExistingServer` è `false` sotto coverage, e Playwright controlla la salute **prima** di
  lanciare il suo webServer, quindi abortiva con «port already used» portandosi giù tutta la fase
  frontend. Il config ora legge `LIBREFOLIO_TEST_SHARED_SERVER`. *Avevo previsto una perdita
  silenziosa di coverage da SIGKILL: la misura ha smentito il meccanismo* — il fallimento era
  rumoroso, non silenzioso. La correzione è la stessa, ma la ragione scritta nel commento ora è
  quella vera.
- **2.3 ✅** Consolidare le 47 invocazioni in poche, come già fatto sul frontend.
  → `scripts/test_runner/_consolidate_backend.py`. Una invocazione pytest **per categoria** invece
  che per unità, con gli esiti per file ricostruiti dal junit (una unità che non produce nemmeno un
  caso è **rossa**, non silenziosamente verde). `./dev.py test api auth` resta invariato: una azione
  singola è ancora un file singolo.

  Il costo fisso di una invocazione, misurato: **2,60 s** (pipenv + interprete + import di FastAPI,
  SQLModel e di tutti i provider). Collezionare tutti e 47 i file `test_api` insieme ne costa **3,69**
  in totale.

  | categoria | invocazioni | prima | dopo | |
  |---|---:|---:|---:|---:|
  | `schemas` | 8 → 1 | 14,2 s | **4,2 s** | **−70 %** |
  | `utils` | 12 → 1 | 34,4 s | **18,3 s** | **−47 %** |
  | `services` | 61 → 1 | 5m16 | **2m42** | **−49 %** |
  | `api` | 51 → 1 | 7m38 | **6m20** | **−17 %** |
  | **totale seriale** | **132 → 4** | **13m43** | **9m25** | **−31 %** |

  Zero rossi, verdetti per unità completi (61/61 su `services`, 51/51 su `api`). Il guadagno è più
  grande dove le unità sono piccole e numerose, ed è per questo che `services` batte `api`.

  > **⚠️ Fuori pista 1 — un difetto di ordinamento che annullava in silenzio la tappa 2.**
  > `_apply_parallel` gira in `_dispatch_test_command` **prima** di `dispatch_to_category`, che è dove
  > viveva il contesto del server condiviso. Ogni passata preliminare girava quindi **fuori** da quel
  > contesto: senza `LIBREFOLIO_TEST_SHARED_SERVER` nell'ambiente, `test_server_helper.start()` prende
  > il ramo che **ammazza chi tiene la porta 6041 e avvia il proprio uvicorn**. Misurato sul log: la
  > passata consolidata di `api` ha avviato **43 server dentro un solo processo pytest**, uccidendo per
  > giunta il server condiviso del runner. La passata parallela aveva lo stesso difetto latente, ma
  > innocuo: esegue solo unità PURE, che un server non lo vogliono.
  >
  > Corretto estraendo `shared_backend_for()` e `_run_passes()` in `_cli.py`, così che «backend su →
  > passate preliminari → seriale» sia deciso **in un punto solo** e i due punti di ingresso non
  > possano divergere. Verificato: 0 avvii di server nella corsa corretta, contro 43.

  > **⚠️ Fuori pista 2 — e riscrive la lettura della tappa 2.** Con l'ordine corretto `api` fa
  > **6m03** contro i **6m09** dell'ordine sbagliato: attaccarsi al server condiviso, a valle del
  > consolidamento, vale **6 secondi**. Non è una delusione, è la spiegazione: uvicorn parte **in un
  > thread dentro il processo pytest**, quindi la spesa non è mai stata «avviare il server» ma
  > **importare l'app**, e il consolidamento la paga già una volta sola. I 78 s recuperati su `api`
  > vengono dal consolidamento, non dalla condivisione.
  >
  > Il che **conferma** quanto già scritto nella correzione in testa alla tappa 2, con un argomento
  > più forte: **il server condiviso non è un'ottimizzazione, è la precondizione della concorrenza.**
  > 43 server in-process sulla stessa porta sono mutuamente esclusivi *per costruzione*; un solo
  > server esterno è ciò che permette a più processi pytest di colpirlo insieme (misurato: 1,6× con 4
  > worker). Il suo valore si riscuote alla tappa 5, non qui.

  > **⚠️ Fuori pista 3 — la perdita silenziosa di coverage, questa volta nel mio codice.**
  > `_run_group()` copiava *dentro* il database di coverage accumulato ma non lo ricopiava **fuori**,
  > al contrario di `run_command()` che lo fa in un `finally`. Effetto: pytest-cov scrive `.coverage`,
  > il lettore successivo trova solo `.coverage_data/backend` invariato, e **la misura dell'intera
  > categoria sparisce senza un solo rosso**. È esattamente il rischio in cima alla tabella §5 —
  > «già successo due volte in P7, senza fallire» — trovato per la terza volta e nel codice nuovo.
  > Trovato **perché** la verifica 2.4 era obbligatoria, non perché l'avessi sospettato.

  > **Nota, non risolta**: dopo `api` sopravvivono processi figli `multiprocessing` forkserver, che
  > tengono aperta la pipe di stdout — una `| tee` resta appesa a corsa finita. È stato di test che
  > perde, e va guardato; qui è stato aggirato con `> file` invece della pipe.

  > **⚠️ Fuori pista 5 — `all-backend` era rotto, e nessuno l'aveva visto.**
  > La prima corsa completa di `all-backend` da quando esiste il server condiviso ha prodotto **13
  > fallimenti e 116 errori `no such table: users`**, nessuno dei quali nominava la causa. Venti righe
  > sopra il primo test, il setup aveva stampato: *«Removing existing test database» → «Test database
  > removed» → «Create database via Alembic migrations FAILED» → «Server is currently running on port
  > 6041»*.
  >
  > `db_create` **cancella il file e poi** lascia che sia la migrazione a scoprire che il server è su.
  > La migrazione rifiuta — correttamente — ma a quel punto il database non esiste più, e tutto il
  > resto della corsa gira contro uno schema vuoto. Il difetto è **pre-esistente**: c'è da quando la
  > tappa 2.1 ha introdotto il server condiviso, e non era emerso perché avevamo sempre lanciato
  > categorie singole. Tre correzioni:
  >
  > 1. **La precondizione si verifica prima di distruggere**, non dopo. Ora, se il conflitto c'è, il
  >    database resta intatto e il messaggio lo dice.
  > 2. **`database_file_owned_exclusively()`**: `db_create` mette in pausa il backend condiviso per la
  >    durata dell'operazione e lo riavvia dopo. Sotto coverage è sicuro — `stop()` aspetta che
  >    `coverage run` scriva il suo `.coverage.<pid>`, e il secondo processo scrive il proprio: li
  >    fonde `coverage combine`.
  > 3. **Un setup fallito è fatale per la sua categoria.** Prima proseguivo con un warning: sbagliato,
  >    produce 116 errori che raccontano la conseguenza e nascondono la causa.
  >
  > Il setup di `services`, che è l'unico esclusivo e gira per primo, è inoltre **anticipato a prima
  > dell'avvio del server** (`setup_exclusive=True`): non è la rete di sicurezza — quella è il punto 2
  > — ma evita un ciclo di stop/start cinque secondi dopo l'avvio.
  >
  > **Esito: `./dev.py test all-backend` → 7/7, 10m39, verde.** È la prima corsa completa verde dalla
  > tappa 2.

  **Verifica della coverage (la 2.4 applicata al consolidamento).** Il confronto è fra `--coverage`
  con le invocazioni separate e `--coverage` consolidato, riga per riga e file per file, non sul
  totale:

  | | file solo in A | file solo in B | file con delta | righe |
  |---|---:|---:|---:|---:|
  | `utils` (12 → 1) | 0 | 0 | **0** | 7 255 = 7 255 |
  | `api` (51 → 1) | 0 | 0 | **1** | 24 898 → 24 900 |

  L'unico file che si muove è `app/utils/identifier_utils.py`, **+2 righe** (30-31, il ramo
  `elif isinstance(value, (list, tuple, set))`): un guadagno, non una perdita, e su una funzione pura
  raggiunta da dati leggermente diversi in una sessione condivisa. Il livello endpoint —
  `app/api/v1/**`, l'unico che il passaggio poteva far sparire — è **1570 contro 1570, identico**.

  Verificati anche `--resume` (le nuove chiavi `consolidated:<categoria>` saltano correttamente le 8
  unità già verdi di `schemas`: 4,6 s → 1,8 s) e `check-orphans`.

  > **⚠️ Fuori pista 4 — un orfano introdotto da me alla tappa 0.1.**
  > `check-orphans` ha trovato `formatDecimal.test.ts` non registrato: l'avevo scritto correggendo W9
  > e non l'avevo aggiunto a nessuna azione, quindi **non girava mai**. Registrato in
  > `front_utility_unit`. È il secondo caso in questo piano in cui un controllo automatico trova un
  > mio errore prima che lo trovi una corsa: vale la pena notarlo, perché è l'argomento per cui la
  > tappa 6 deve renderli obbligatori e non facoltativi.
- **2.4 ✅** **Verifica non negoziabile**: la coverage backend deve restare **identica file per file**. Si
  passa da «pytest-cov vede gli endpoint in-process» a «il server esterno scrive il proprio file e
  `coverage combine` lo fonde»: è esattamente il punto in cui, in P7, la coverage si è persa **due
  volte in silenzio**.

  **Esito: non si è persa.** Su `api auth`, confronto file per file:

  | | in-process | condiviso |
  |---|---|---|
  | `app/api/v1/**` (endpoint) | 1104 | **1104**, identico per singolo file |
  | file con righe coperte | 192 | **224** |
  | righe totali | 19 655 | **20 985** |

  Il livello endpoint — l'unico che il passaggio poteva far sparire — è **identico**. Il guadagno
  netto viene dall'avvio reale del server (registry BRIM, `main.py`).

  > **⚠️ Fuori pista, e vale più della verifica stessa.** Quindici file risultavano *peggiorati*, tutti
  > provider e servizi prezzi. Stavo per attribuirlo al server condiviso. **Ho rieseguito due volte il
  > percorso vecchio, identico a sé stesso: stessa identica varianza** — `asset_source.py` 542 poi
  > 234, `yahoo_finance.py` 165 poi 77, mentre `api/v1/auth.py` restava fisso a 132.
  >
  > Causa: `populate_mock_data` scrive `last_run_at = ieri`, quindi **ogni job dello scheduler è
  > dovuto appena un server di test parte**. Il loop si sveglia dopo 5 s e comincia a rinfrescare
  > prezzi **contro provider veri**: una corsa ha registrato la Bank of England che risponde HTML.
  > Coverage che nessun test ha chiesto, che cambia a ogni corsa, e che sporca proprio l'analisi
  > «quali aree sono poco testate» che è il passo successivo.
  >
  > Il server condiviso ora parte con `--no-scheduler` (come già fa la gallery, per la stessa ragione).
  > **Misurato: due corse identiche, delta 0 righe, 0 file variabili** — prima variavano 14 file per
  > 742 righe. La logica dello scheduler resta coperta dai suoi test in `test_services`, che chiamano
  > le funzioni direttamente; `api scheduler` 8/8, `settings` 22/22, `assets-crud` 22/22, `services`
  > tutto verde.

> **Nota sul parallelismo frontend**: il meccanismo c'è, ma **resta spento** (`E2E_WORKERS=1`,
> `fullyParallel: false`). Accenderlo è lavoro delle tappe 3 e 5, non un default silenzioso: con 63
> spec che oggi condividono lo stato, alzarlo adesso produrrebbe esattamente il diluvio di rossi che
> il protocollo di triage deve saper leggere *in ordine*.

### Tappa 3 ✅ — Rendere le letture write-safe (il cuore)

Nessuno strumento nuovo: **è la corsa stessa a produrre le condizioni**, e il lavoro è tutto nel come
si legge un rosso.

> **Esito, in una riga: i test erano già write-safe. Era il catalogo a non saperlo.**
>
> L'esperimento previsto dalla tappa non ha prodotto il diluvio di rossi che il piano metteva in
> conto. Ne ha prodotti **14 in tutto, su 603 test**, e **tredici avevano una sola causa** — la
> quattordicesima non c'entrava niente con la concorrenza. Il debito non era nei test: era nella
> **classificazione conservativa**, che dichiarava `write-global` per difetto tutto ciò che non
> riusciva a dimostrare puro, e stava quindi serializzando 50 unità su 51 senza una ragione.
>
> | | prima | dopo | |
> |---|---:|---:|---:|
> | `api all` | 6m20 | **3m26** → **3m07** | **2,0×** |
> | `services all` | 2m42 | **51 s** | **3,2×** |
> | `utils all` | 18,3 s | 16,8 s | — |
> | `schemas all` | 4,2 s | 4,0 s | — |
> | **totale** | **9m25** | **4m38** | **2,0×** |
>
> Rispetto alla fotografia iniziale della tappa 0 (13m43), il seriale backend è **3,0× più veloce**.
> Coverage verificata file per file: **0 file persi, endpoint `app/api/v1/**` 1570 = 1570.**

- **3.1 ✅** **Il protocollo di triage.** Scriverlo prima di usarlo, perché è il vero prodotto della
  tappa: davanti a un rosso, l'ipotesi *«è stata la forma della risposta?»* va verificata **per
  prima**, e con criteri espliciti — il dato c'era ma altrove; la pagina conteneva altro; il conteggio
  differiva; l'elemento esisteva ma non era il primo. Se conferma → il test si rende write-safe. Se
  smentisce → è un difetto vero, e si tratta come tale.
  → `.github/skills/devpy-tools/test-triage/SKILL.md`. Otto sezioni, ciascuna un'ipotesi con il modo
  di confermarla o escluderla, e una tabella di verdetti che **non ha una sesta riga**: in
  particolare non esiste `flaky`.

- **3.2 ✅** **L'esperimento.** Perché fosse possibile, due estensioni al macchinario della tappa
  precedente: `add_test(..., isolation=…)` — il campo che `_inventory.classify()` leggeva già ma che
  **nessuno poteva scrivere**, perché il parametro non esisteva — e `plan(..., classes=…)`, che
  smette di parallelizzare solo PURE.

  In più `--assume-scoped`: un flag che **ignora il catalogo** e lancia tutto in concorrenza. Serve
  esattamente una volta per categoria, per scoprire cosa il catalogo sbagliava; è strumentazione
  d'esperimento, non un default.

  **Prima corsa, `api all --workers 4 --assume-scoped`: 51 unità in parallelo, 3m19, 13 rossi.**

- **3.3 ✅** **Il triage, applicato — e il §4 della skill si è verificato al primo colpo.**
  I 13 rossi stavano in due file, `test_assets_patch_fields.py` e `test_assets_prices.py`, e
  **nessuno dei due era la causa**. Tutti riportavano lo stesso messaggio:

  ```
  Exception: Failed to create user: {"detail":"New user registration is disabled"}
  ```

  La causa era un **terzo** file, `test_auth_api.py`, che scrive
  `global_settings.enable_registration = False` per verificare che la registrazione chiusa rifiuti —
  e nella finestra in cui quel flag è a `False`, chiunque registri un utente fallisce.

  Il punto che vale la pena notare: **quella riga l'avevo scritta un'ora prima**, come
  `exclusive_because` di `api auth`, ragionando a tavolino su cosa il file toccasse. La corsa l'ha
  confermata alla lettera. Non è fortuna: è che la domanda *«che cosa muove questa unità che non è
  suo?»* ha una risposta breve e verificabile, quando ci si costringe a scriverla.

  **Verdetto: `auth` è un'esclusiva legittima.** `enable_registration` è un flag di istanza, non una
  riga per utente: non c'è modo di scoparlo, e la finestra è irriducibile. Un test che verifica la
  registrazione chiusa *deve* avere l'istanza. Questa è la prima voce del catalogo della tappa 5.3, e
  ci arriva con la sua motivazione già scritta e già dimostrata.

  **Seconda corsa, con `auth` seriale: 50 unità in parallelo, 3m16, verde.**

- **3.4 ✅** **Il quattordicesimo rosso, che non c'entrava.** Sotto `--coverage` è comparso
  `test_fx_api::test_sync_rates` — `httpcore.ReadTimeout`. Non è concorrenza: `POST
  /fx/currencies/sync` chiama **la BCE su internet**, e la coverage (che qui costa `user 6m12` contro
  `37 s`) ha spinto il round trip oltre i 30 s di timeout del client. Verificato: **2 corse su 2
  verdi in seriale.**

  Il triage lo classifica come *difetto vero*, ma di una specie che questa tappa non deve risolvere:
  un test di API che fa I/O verso un servizio esterno è non deterministico per costruzione — è lo
  stesso difetto che alla 2.4 sporcava la coverage con i job dello scheduler, qui però **deliberato**.
  `api fx` resta quindi esclusivo con la sua motivazione, e togliere la dipendenza di rete è
  **annotato come lavoro proprio** (`t3-fx-network`), non come blocco di questa tappa.

  > **Chiuso durante la tappa 4**, e con un effetto sul catalogo: `api` passa da 49 a **50 unità in
  > parallelo e una sola seriale**, con `api all --workers 4` a **3m07** (603 test, exit 0).
  >
  > Il rimedio era già in casa e nessuno lo usava: esiste
  > `MOCKFX`, un provider registrato *apposta* per i test, che restituisce `1.2345` per ogni data.
  > I tre sync che chiamavano `ECB` ora chiamano lui. Il test non è solo diventato deterministico:
  > è diventato **più severo**, perché adesso può affermare `provider_used == "MOCKFX"` e
  > `points_fetched >= 1` invece di limitarsi a stampare quello che è arrivato.
  >
  > Le altre occorrenze di `ECB` nel file restano: sono configurazione di rotte che nessuno
  > sincronizza, quindi non toccano la rete. **`api fx` ha perso la sua esclusiva**: 21 test in
  > 15,8 s, verde.

- **3.5 ✅** **La promozione, dichiarata dove è vera.** Scrivere `isolation="write-scoped"` su
  quarantanove `add_test` avrebbe **nascosto le due eccezioni dietro le quarantotto regolarità**.
  Quindi `make_category(..., default_isolation=…)`: la proprietà appartiene alla categoria — *«ogni
  unità di `api` crea il proprio utente e indirizza le proprie righe per id»* — e le uniche due righe
  che si leggono sono quelle che dicono il contrario.

  Con un dettaglio che conta: **`exclusive_because` *è* la dichiarazione di `write-global`**, non un
  commento accanto a un flag. Sono una sola affermazione, così un default di categoria non può
  promuovere in silenzio un'unità che qualcuno ha già spiegato perché non va promossa.

  Esteso poi a `services` (85 unità, verde al primo colpo), `utils` e `schemas`. Nessuna delle tre ha
  prodotto un solo rosso: **il debito era tutto nella classificazione**.

- **3.6 ✅ (fuori piano)** **`all-backend` non ne beneficiava, e la ragione è istruttiva.** La passata
  parallela era *sollevata davanti a tutto*, con `scope=None`. Sopra PURE quella forma non può
  funzionare: la suite **oscilla il database di proposito** (`db` popola → `services` svuota → `api`
  ripopola), quindi **non esiste un istante in cui la precondizione di ogni categoria vale insieme**.

  Corretto camminando le categorie in ordine di suite, ciascuna preceduta dal proprio setup — che è
  esattamente ciò che fa la passata consolidata, e che `run_category_setup` esegue una volta sola per
  invocazione, quindi senza raddoppiarlo.

  **`./dev.py test all-backend` → 7/7, 5m57, verde**, contro i 10m39 della corsa di chiusura della
  tappa 2. **1,8×**, e questa volta senza `--assume-scoped`: è il catalogo a dirlo.

- **3.7 ✅ (fuori piano) — e vale più di tutto il resto della tappa: `PRAGMA busy_timeout`.**
  La prima corsa di `all-backend` con l'interleaving è caduta su un errore che nessuna corsa di
  categoria singola aveva mai prodotto:

  ```
  sqlite3.OperationalError: database is locked
  [SQL: INSERT INTO users (...)]
  ```

  `services` da solo era verde: il server condiviso non c'era. In `all-backend` c'è, ed è **un writer
  in più** sullo stesso file.

  La configurazione diceva già la cosa giusta a metà. `journal_mode=WAL` c'era, con un commento che
  spiegava perché serve. Ma **WAL ammette un solo scrittore alla volta**, e il comportamento di
  SQLite quando lo scrittore trova occupato è, *per difetto*, **fallire subito** — non aspettare.
  `busy_timeout` non era impostato, quindi valeva 0.

  **Non è un difetto di test.** È raggiungibile in produzione, per due strade che esistono entrambe
  oggi: lo scheduler rinfresca i prezzi in sottofondo mentre l'utente salva una transazione; e
  uvicorn gira con più worker — cosa che questo stesso piano ha introdotto alla 2.2-bis. In entrambi
  i casi l'utente vede un errore al posto di un'attesa di qualche millisecondo.

  Una riga: `PRAGMA busy_timeout=5000`. Cinque secondi sono oltre qualunque transazione che questa
  applicazione apra, quindi l'effetto pratico è convertire un errore spurio in un'attesa breve.

  È il **secondo** difetto di prodotto che questo lavoro trova per la stessa strada — dopo
  `NamedCache.clear()`, che smetteva di memorizzare per sempre e in silenzio. Entrambi invisibili ai
  test così com'erano, entrambi emersi appena la concorrenza è diventata vera. È l'argomento della
  §2 del piano, verificato: *«oltre al percorso si prova la capacità reale di reggere richieste
  concorrenti»*.

### Tappa 4 — Attese su condizione

- **4.1 ✅** Le `waitForTimeout` non sono tutte uguali: separare quelle sostituibili meccanicamente
  da quelle che nascondono **una vera assenza di segnale nel prodotto**.

  Censite **885 attese per 410,6 s dichiarati**. Ma `gallery.spec.ts` da solo ne ha **220**, ed è il
  generatore di screenshot: gira da solo, e le sue attese servono a far *finire di disegnare* una
  pagina prima di fotografarla. Non è la stessa cosa e va trattato a parte. Restano **665 attese,
  299,9 s**:

  | | attese | secondi |
  |---|---:|---:|
  | seguite da un'asserzione | 228 | 99,3 |
  | precedute da un'asserzione | 176 | 91,2 |
  | **sostituibili, totale** | **404** | **190,6** |
  | lunghe, nessun segnale vicino | 214 | 100,2 |
  | brevi, nessun segnale vicino | 47 | 9,2 |

  > **La stima del piano era ottimista, e per una ragione che vale la pena scrivere.** Applicando il
  > criterio **stretto** — l'attesa è rimovibile solo se la riga *immediatamente successiva* è
  > un'asserzione che ritenta da sola (`toBeVisible`, `toHaveValue`, …) o un'attesa esplicita
  > (`.waitFor({…})`, `waitForSelector`) — le rimovibili **senza pensarci** sono **58**, non 404.
  > Le altre 346 hanno un'asserzione *nelle vicinanze* ma non subito dopo, e in mezzo c'è un `click`,
  > un `fill`, un `if`: vanno guardate una per una.
  >
  > **58 rimosse, 26,8 s per corsa, in 22 file.** Poche, ma tolte con un argomento che non ha
  > eccezioni — non con un giudizio a occhio su 404 punti.

  > **E hanno mostrato qualcosa che non cercavo.** Diverse rimozioni lasciano un test così:
  >
  > ```ts
  > await searchInput.fill('Apple');
  > await expect(page.getByTestId('assets-page')).toBeVisible();   // era già visibile
  > ```
  >
  > L'asserzione era vera **anche prima** di digitare. Il test non verifica il filtro: verifica che
  > la pagina esista. La `waitForTimeout(500)` in mezzo gli dava l'aria di aspettare un risultato.
  > Non è una regressione della rimozione — è una **debolezza che la sleep nascondeva**, e adesso si
  > vede. Sono voci per la tappa 4.2, di natura diversa da quella prevista: non «al prodotto manca
  > uno stato», ma «al test manca un'asserzione».
- **4.2 ⏳** **Le seconde sono lavoro di progettazione, non di test.**

  Classificate per **che cosa** stanno aspettando — cioè guardando la riga *precedente*, non quella
  successiva, perché è lì che si vede quale evento il prodotto non racconta:

  | attese | s | dopo che cosa | che cosa non è osservabile |
  |---:|---:|---|---|
  | 380 | 154,4 | un `click` | l'**effetto** del click |
  | 86 | 34,0 | una digitazione | il **debounce** e l'arrivo dei risultati |
  | 66 | 46,8 | **un'attesa esplicita che non è bastata** | un secondo stadio di caricamento |
  | 67 | 32,8 | altro | — |

  **La terza riga è la più interessante, ed è quella da cui ho cominciato**: sono i punti in cui
  qualcuno *aveva già scritto* l'attesa giusta — `waitForSelector('[data-testid=…]')`,
  `expect(...).toBeVisible()` — e ha dovuto aggiungerci sopra un sonno lo stesso. Non è pigrizia: è
  che il segnale che il prodotto espone **arriva prima di quando la cosa è davvero pronta**. Il
  commento accanto lo dice quasi sempre a parole: *«Wait for loading to complete (skeleton →
  content)»*, *«wait for broker files to load»*, *«Extra settle time for init events»*.

  Tre casi affrontati, scelti perché la risposta **non era una scelta di interfaccia** — lo stato
  esisteva già dentro il componente, semplicemente non usciva nel DOM:

  1. **`ImageEditModal` — `data-edit-ready`.** `data-cropper-ready` diventa `true` appena il cropper
     sa disegnare, ma il modale continua a **scartare gli eventi di modifica per altri ~500 ms**
     mentre gira il proprio `resetAll`. In quella finestra l'utente può ruotare l'immagine e
     `hasChanges` resta `false`: preme X, il modale **si chiude senza avvisare** e la modifica è
     persa. Il test ci metteva sopra `waitForTimeout(1500)`, due volte.
     Ora lo stato esce come `data-edit-ready` e `aria-busy`. *(La conseguenza sull'interfaccia —
     disabilitare o meno i controlli in quei 500 ms invece di lasciarli rispondere a vuoto — è una
     scelta tua, ed è annotata sotto.)*
  2. **Pagine `assets` e `fx` — `data-busy`.** Entrambe caricano **in due ondate**: prima l'elenco,
     poi i prezzi/tassi riga per riga. `loading` e `row.loadingPrices` esistono già nel componente;
     nel DOM non compariva niente, quindi `goToAssetsPage()` e `goToFxPage()` — usate da **tutte** le
     spec di quelle due aree — dormivano 1 s a testa. Ora la radice espone
     `data-busy="true|false"` (e `aria-busy`), e gli helper aspettano quello.
  3. Restano da guardare con lo stesso metodo `portfolio` («Let portfolio summary load», 2 s),
     `fx-detail` e il wizard di import.

  **Quello che invece mi fermo a chiederti**, perché è interfaccia e non osservabilità:

  - Nei ~500 ms di init del ritaglio immagine, i pulsanti **devono restare attivi** (e le modifiche
    continuare a perdersi), oppure vanno **disabilitati** finché non sono efficaci? Io propendo per
    disabilitarli — un pulsante che non fa nulla è peggio di un pulsante spento — ma cambia la resa
    visiva del modale e la decisione è tua.
  - Le 380 attese «dopo un click» sono quasi tutte **conferme di un'azione andata a buon fine**
    (salva, elimina, importa). La domanda giusta non è per-test ma di prodotto: *esiste una
    convenzione unica* — un toast, un `aria-live`, uno stato sulla riga — che il test possa leggere
    sempre nello stesso modo? Se sì la si dichiara una volta e valgono tutte; se no, restano 380
    decisioni separate. **Questa è la domanda che tiene aperta la 4.2.** Se un test è costretto a dormire,
  è perché *non esiste modo di sapere che l'operazione è finita* — e quel modo non manca solo al test:
  **manca anche all'utente**, che davanti allo stesso schermo può soltanto aspettare e sperare. Il
  `waitForTimeout` è il sintomo; la diagnosi è che uno stato del sistema non è osservabile.

  Quindi il rimedio non è «trovare un selettore più furbo» ma **rendere quello stato visibile a
  entrambi, con un unico intervento**: lo stato passa da implicito a esplicito nel componente
  (`idle | pending | done | error`), l'utente lo vede come indicatore o disabilitazione, il test lo
  legge dallo stesso attributo. Un solo cambiamento, due beneficiari — ed è il motivo per cui questo
  punto sta in un piano sui test ma produce valore sul prodotto.

  **Metodo**: per ogni attesa non sostituibile, dire *quale stato* è invisibile e *a chi* serve.
  Dove la risposta è chiara la implemento; **dove non lo è, mi fermo e te lo chiedo** invece di
  inventare una convenzione — perché è una scelta di interfaccia, e le scelte di interfaccia sono
  tue. Le porto con l'elenco degli schermi coinvolti, non come domanda astratta.
- **4.3 ✅** Misurare il tempo recuperato. Il tetto teorico era 7,5 minuti a corsa; scontando
  `gallery` — che gira da solo e le sue attese le usa per far finire di disegnare le pagine da
  fotografare — il tetto vero era **299,9 s**.

  | | attese | secondi |
  |---:|---:|---:|
  | prima (escluso gallery) | 665 | 299,9 |
  | **dopo** | **572** | **258,9** |
  | recuperato | **93** | **41,0 s** |

  Di cui **88 rimosse meccanicamente** (58 con la regola stretta, 30 con quella sulle azioni, che
  attendono già da sole l'*actionability*) e **5 sostituite da uno stato nuovo** — le due
  `data-busy` negli helper condivisi e le tre `data-edit-ready` del ritaglio immagine, che da sole
  valgono 5,5 s ma li valgono **in ogni spec** delle aree `assets` e `fx`, perché stanno negli
  helper di navigazione.

  Misurato sulle categorie toccate: `front-asset` 6,0 → **5,5 min**, `front-fx` 4,4 → **3,7 min**.
  Il guadagno di orologio è più grande della somma delle sleep tolte, perché le attese negli helper
  si pagavano una volta per test, non una volta per file.

  Restano 572 attese per 258,9 s, ed è **il numero giusto da non inseguire**: sono la tappa 4.2,
  cioè lavoro di prodotto, non di test.

  > **Nota di metodo, pagata a caro prezzo.** La corsa di verifica di `api all` subito dopo 27
  > minuti di e2e ha dato **5m04**; la stessa corsa a macchina scarica, **3m07**. Un 60 % di
  > differenza senza che una riga fosse cambiata. Le misure di questo piano vanno prese **a freddo**,
  > altrimenti si scrive una regressione che non esiste — che è esattamente l'errore che stavo per
  > commettere.

### Tappa 5 — Riclassificare il catalogo

> **Il backend è fatto: l'ha assorbito la tappa 3**, perché non aveva senso scoprire una promozione
> e non scriverla. Resta il frontend, ed è **bloccato per scelta** finché la 4.2 non ha risposta.

- **5.1 ✅ (backend)** Promosse `api`, `services`, `utils`, `schemas` a `write-scoped` di categoria.
- **5.2 ✅ (backend)** Passata parallela allargata e rimisurata: `all-backend` 10m39 → **5m57**,
  coverage confrontata file per file, **0 file persi**.
- **5.3 ✅ (backend)** Restava **una** unità `WRITE-GLOBAL` con motivazione scritta (`api auth`);
  `api fx` ha perso la sua quando la dipendenza di rete è sparita. Il catalogo è in
  `runner_architecture.md` (6.4).
- **5.4 ⏳ (frontend) — da fare, e con una precondizione precisa.** Lo stesso metodo
  (`--assume-scoped` → triage → `default_isolation`) sulle 63 spec Playwright, **dopo** la 4.2.
  Alzare `E2E_WORKERS` adesso significherebbe leggere i rossi prodotti da 572 attese a orologio
  sotto concorrenza: illeggibili, e per una ragione che sappiamo già. *Risorse richieste: la
  risposta alle due domande della 4.2, in particolare quella sulla convenzione unica di conferma
  dopo un'azione.*

### Tappa 6 ✅ — Scrivere le regole (perché il debito non si riformi)

Le regole vanno dove chi scrive un test le incontra **prima** di sbagliare:

- **6.1 ✅** `.github/instructions/backend-testing.instructions.md` e
  `frontend-testing.instructions.md`: le regole in forma normativa, con l'esempio giusto e quello
  sbagliato accanto, tratti da casi **veri di questo albero**. Aggiunte in questa tappa: sul
  frontend i due esempi di stato pubblicato (`data-busy`, `data-edit-ready`) e **la spia da
  riconoscere** — *«extra settle time»*, *«let it load»*: ogni volta che si scrive un commento così
  si è appena nominato uno stato che il prodotto non espone. Sul backend, come si dichiara
  `exclusive_because` e la sesta regola: **mai raggiungere un terzo sulla rete**.
- **6.2 ✅** Skill `testing-backend` e `testing-frontend`. La prima diceva ancora *«solo le unità
  PURE girano in parallelo»*, che dalla tappa 3 è falso, e avvertiva di un difetto di `db create`
  già corretto alla 2.3: entrambe le sezioni riscritte, con `--assume-scoped` presentato per quello
  che è — strumento di un esperimento, non un default. La seconda ha ora la sezione sulle attese,
  con il ragionamento *«se non c'è niente da aspettare, manca uno stato»* e l'avvertenza che **un
  segnale può esistere e mentire**.
- **6.3 ✅** `mkdocs_src/.../test-walkthrough/`: `runner_architecture.md` con la dichiarazione delle
  classi e il perché una promozione **si guadagna con una corsa, non si afferma**; `api.md` ed
  `e2e.md` riscritti — entrambi dicevano ancora *«avvia il server in modalità test»*, che è
  esattamente la regola che il piano ha abolito.
- **6.4 ✅** Il catalogo delle eccezioni, che ora ha **una sola voce** (`api auth`) — ed è il senso
  della sezione: è corta perché un'esclusiva deve sopravvivere all'essere scritta. Accanto, le due
  motivazioni che *sembrano* buone e non lo sono: «va sulla rete» (allora togli la rete — è quello
  che ha fatto perdere l'esclusiva a `api fx`) e «falliva in parallelo» (allora **dì quale
  superficie condivisa muove**; se non sai dirlo, la causa è altrove).

---

## 5. Rischi

| Rischio | Perché è reale | Mitigazione |
|---|---|---|
| **La coverage si perde nel passaggio a server esterno** | già successo **due volte** in P7, senza fallire | 2.4 confronta **file per file**, non il totale |
| **La riscrittura introduce rossi** | è **previsto**, non un rischio: i test che assumono la posizione *devono* fallire | budget di correzione dentro ogni tappa (3.4); la fotografia 0.3 distingue nuovo da preesistente |
| **I rossi da concorrenza sono intermittenti e quindi illeggibili** | è il rischio che il generatore di rumore doveva coprire, e che senza va coperto lo stesso | `--log-dir` (tappa 1) conserva **log per unità + DB compresso del momento**: un rosso si legge senza rieseguirlo. È il motivo per cui la tappa 1 precede la 3 invece di essere una comodità |
| **Il triage si fa pigro e archivia i rossi come «flaky»** | è il modo abituale in cui questo debito si riforma | il protocollo (3.1) mette *«è la forma della risposta?»* come **prima** ipotesi, e vive nelle skill (3.5), non nella memoria di chi c'era |
| **La concorrenza vera fa emergere lentezze del backend** | è **lo scopo**, ma può bloccare il piano | separare «test rosso» da «prodotto lento»: il secondo diventa una voce di lavoro propria, non un blocco |
| **1000 punti di chiamata sono troppi** | lo sono, se letti a mano | non si leggono tutti: la statica dà l'**ordine**, il rosso dà la **lista** |
| **La compressione non è disponibile sulla macchina di turno** | `lzma`/`bz2` sono moduli **opzionali** di CPython: mancano in build minimali | ripiego interno alla stdlib fino a `gzip`, che c'è sempre; nessun binario esterno, quindi niente da installare su Linux o Windows |
| **Le regole restano lettera morta** | è il destino abituale delle regole | tappa 6 con esempi presi da questo albero, non astratti; e la 3.5 le scrive **mentre** servono, non a piano finito |

---

## 6. Cosa **non** è in questo piano — e perché non serve che ci sia

Le prime due voci non sono rinvii: sono **conseguenze**. Questo piano non le rimanda, le **rende
inutili**.

- **Un DB per worker** (`LIBREFOLIO_TEST_WORKER` → `data/test/wN/`). Serviva a dare a ogni worker dati
  che nessun altro poteva muovere — cioè a **conservare** l'assunzione di posizione invece di
  toglierla. Un test che si cerca il proprio dato non ha bisogno di un DB tutto suo. In più avrebbe
  richiesto di forare la regola `ALWAYS backend/data/test/ (no override)` di `get_data_dir()`, che è
  una protezione di produzione: la tappa 3 la lascia intatta.
- **Una porta per worker**. Serviva perché ogni test si avviava il proprio server sulla stessa porta
  fissa. Con **un solo backend** (tappa 2) la collisione non esiste: non c'è nulla da assegnare.

> Il senso è che entrambe erano rimedi al sintomo. Isolare i worker avrebbe reso i test verdi
> *nascondendo* che assumono la posizione — lo stesso meccanismo per cui «un processo per azione»
> nascondeva l'inquinamento dello stato condiviso, scoperto nel piano precedente. La stessa trappola,
> un piano dopo.

- **L'attacco alle aree poco coperte** (`JS_FEATURE`, `JS_STORE`, …): confermato **dopo**, come hai
  detto. Questo piano serve a rendere quei test scrivibili in modo sano; senza, si aggiungerebbe debito
  sopra debito — e sarebbero proprio i test nuovi, scritti sulle aree meno battute, a nascere già con
  le assunzioni che qui stiamo togliendo.
