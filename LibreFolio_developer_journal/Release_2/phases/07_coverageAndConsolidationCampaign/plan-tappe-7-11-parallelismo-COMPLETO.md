# Piano — Ridurre il tempo dei test frontend

> Il piano precedente (*«Riscrivere la semantica dei test: da assumere a verificare»*, tappe 0‑6)
> è archiviato in `files/plan-p9-test-semantics-COMPLETO.md`. Ha chiuso il backend:
> `all-backend` 10m39 → 5m57, `services` 5m16 → 51 s, `api` 7m38 → 3m07.
> Il frontend è rimasto quasi intatto: **−1,2 min in tutto**. Questo piano lo affronta.

---

## La tesi

Il frontend è lento **per dichiarazione, non per necessità**. In `playwright.config.ts`:

```ts
fullyParallel: false,   // Test sequenziali (stato condiviso)
workers: E2E_WORKERS,   // default 1
```

Non è una svista: è onesta. La suite *condivide davvero* un backend e un database, e nessuno ha
mai potuto dimostrare che due test sopportino di stare accanto. È esattamente la situazione del
backend prima della tappa 3 — dove il debito non era nei test, era **nel catalogo che non sapeva
dire nulla**.

### Il malinteso da sfatare subito

Le 572 `waitForTimeout` residue valgono **258,9 s ≈ 4,3 min** su un frontend che ne dura ~40.
Convertirle tutte, una per una, comprerebbe il 10 %. **Non è lì il tempo.**

Le attese contano per un altro motivo: **sono l'ostacolo al parallelismo**. Una sleep da 500 ms
tarata su una macchina scarica diventa insufficiente quando quattro worker si contendono un
backend, e si trasforma in un rosso. Le attese non sono il costo — sono il **pedaggio** da pagare
per incassare il 3×.

Quindi l'ordine è: **si misura, si costruisce lo strumento, e sono i rossi a dire quali attese
meritano lavoro.** È il protocollo che ha funzionato sul backend, applicato tale e quale.

---

## Il modello: la gallery lo fa già

`gallery.spec.ts`, riga 134:

```ts
test.describe.configure({mode: 'parallel'});
```

Opt‑in **per blocco**, con `fullyParallel: false` globale. È il gemello esatto del catalogo
backend: il default resta prudente, e ogni blocco che vuole correre in parallelo deve
**dichiararlo** — e guadagnarselo con una corsa verde.

| backend | frontend |
|---|---|
| `add_test(isolation=…)` | `test.describe.configure({mode: 'parallel'})` |
| `make_category(default_isolation=…)` | opt‑in per file |
| `exclusive_because="…"` | `mode: 'serial'` **con motivazione scritta** |
| `--assume-scoped` | `E2E_FORCE_PARALLEL=1` (sonda) |

La gallery resta **fuori dal perimetro** (confermato): le sue 221 attese servono davvero, aspettano
che l'animazione si fermi prima dello scatto.

---

## Domanda: «si potrebbe mandare un print nella console? il test riesce a intercettarlo?»

Tecnicamente **sì** — `page.on('console')` e `page.waitForEvent('console')` esistono. Ma due fatti
verificati nel repo bocciano la versione ingenua:

**Fatto A — il `debug` attuale non esiste nel binario sotto test.**
`lib/debug.ts` è compilato via `DEBUG_ENABLED = VITE_DEBUG === 'true' || import.meta.env.DEV`, e
gli e2e girano contro `npm run build` servito dal backend su 6041 (`auto_build_frontend`, che non
imposta `VITE_DEBUG`). In quel build **l'intero oggetto `debug` è eliminato come dead code**. Un
`debug.log` sarebbe invisibile ai test — oppure andrebbe costruito un e2e su un build diverso da
quello che spediamo, che è peggio del problema.

**Fatto B — un messaggio di console è un *fronte*, non uno *stato*.**
Il listener va armato **prima** dell'azione. Chi scrive `await click()` e poi `waitForEvent` perde
il messaggio se è già passato. Cioè: un test che passa a 1 worker e fallisce a 4 — **la stessa
identica classe di bug che stiamo rimuovendo**, solo travestita.

### La proposta: tieni l'idea, cambia il supporto

Un segnale che non è un toast, ma **uno stato invece di un print**. Una sola funzione, tre
consumatori, ognuno col suo interruttore:

```ts
notify({
    name: 'tx.import.committed',        // stabile, mai tradotto → contratto macchina
    detail: {imported: 47, skipped: 3}, // strutturato
    toast: {variant: 'success', message: t('...')},  // opzionale → contratto umano
});
```

| consumatore | quando | perché |
|---|---|---|
| ring buffer `window.__lf.events` (ultimi 100) | **sempre** | è uno *stato*: leggibile in ritardo, nessuna gara. ~30 righe spedite, e in più è una traccia diagnostica utile al supporto |
| `debug.log` | solo build debug | comodità umana, sparisce in produzione com'è giusto |
| toast | quando l'utente deve saperlo | contratto umano, tradotto |

Il test legge lo **stato**, non aspetta il fronte:

```ts
const since = await eventSeq(page);
await saveButton.click();
const ev = await waitForEvent(page, 'asset.saved', {since});
expect(ev.detail.id).toBe(assetId);
```

Arrivare tardi non è un problema: il buffer se lo ricorda.

### Il punto che scioglie la domanda

Toast ed evento **non sono due canali alternativi**. Sono le due metà della stessa notifica:
l'evento è la metà macchina, il toast è la metà umana. `toast:` è un **campo dell'evento**, non
un'altra strada. Due conseguenze:

- Il requisito «il toast può contenere altri dati» è soddisfatto per costruzione: il messaggio
  resta HTML libero (l'AI Export continua a metterci le dimensioni del prompt), mentre il
  **payload strutturato** vive in `detail`.
- **Il test non deve mai asserire sul testo del toast** — è tradotto in 4 lingue. Asserisce sulla
  variante (`data-testid="toast-success"`, già esistente) o sull'evento. È questo il motivo per cui
  l'evento serve *anche quando il toast c'è*.

---

## La classificazione richiesta

Principio: **un toast è dovuto quando l'esito non è già visibile, oppure è irreversibile, oppure
è parziale.** Tutto il resto è evento silenzioso.

| # | caso | toast | esempio |
|---|---|---|---|
| 1 | esito **già visibile** nella vista corrente | ✗ | salvi una cella inline e il valore cambia sotto gli occhi; cancelli una riga e sparisce |
| 2 | esito **invisibile** | ✓ | copia negli appunti (AI Export), download file, sync avviato in background, salvataggio che non cambia la vista corrente |
| 3 | **irreversibile o costoso** | ✓ col conteggio | delete massiva, merge di asset, import committato — «47 importate, 3 saltate» |
| 4 | **parziale / degradato** | ✓ sempre | sync di 10 asset, 2 falliti. Il silenzio qui sarebbe una bugia |
| 5 | **errore** | ✓ sempre | già la prassi: 45 dei 98 call site attuali |
| 6 | **transizione interna** | ✗ | cache invalidata, store ricaricato, step del wizard, debounce scattato |

Stato attuale: 98 call site — 45 `error`, 36 `success`, 11 `info`, 6 `warning`, su 28 file. Le
righe 5 e 1 sono già rispettate quasi ovunque; il lavoro vero è **2, 3 e 4**, dove oggi il prodotto
tace e il test dorme.

**Nessun big‑bang**: `notify()` è additivo, i 98 `toasts.*` esistenti continuano a funzionare, e si
migra area per area guidati dai rossi.

---

## La regola che rende possibile il parallelismo

Le attese sono il pedaggio, ma il vero ostacolo è un altro: **i test si contendono un database**.
Due test che creano una transazione e poi contano le transazioni si rovinano a vicenda.

> **Un test possiede i dati che crea, li riconosce da un marcatore unico, e non asserisce mai su
> conteggi globali né su posizioni fisse.**

È il `WRITE_SCOPED` del backend tradotto al frontend, ed è già la regola enunciata a voce
(«i test devono cercarsi il dato giusto navigando le risposte/pagine»). Qui diventa la
precondizione tecnica del parallelismo, non solo buon gusto.

---

## Tappe

### Tappa 7 — Misurare prima di costruire

Nessuna riga di prodotto. Si compra **informazione**: 572 attese sconosciute diventano una lista
ordinata di rossi veri.

- **7.1 ✅ Sonda su `front-fx`.** 63 test, stessa invocazione, unica variabile la concorrenza:
  **3,2 min → 1,7 min (1,9×), zero rossi**. Ripetuta: **1,6 min, verde di nuovo**. Due corse
  parallele verdi ⇒ `front-fx` si è **guadagnata** la promozione.
- **7.2 ✅ Sonda su `front-transaction`.** 215 test: **17,8 min → 6,1 min (2,9×)**.

  > **Il numero che decide il piano.** Se le altre categorie si comportano come queste due, il
  > frontend passa da ~40 min a **~14**.

- **7.3 ✅ Triage.** Cinque rossi nella parallela, ma **tre erano già rossi in seriale** — quindi
  non è la concorrenza ad averli causati. Sono affiorati per un motivo diverso e istruttivo:
  il runner esegue ogni spec in una **invocazione separata**, io le ho eseguite tutte in una sola,
  e tre test dipendono dall'ordine.

  | # | test | causa | classe |
  |---|---|---|---|
  | 1 | `tx-tooltips` › tooltip broker nascosto | cerca una transazione con «Hidden Admin Broker» che le spec precedenti hanno consumato | **possesso dei dati** |
  | 2‑3 | `tx-split-promote` › ×2 | l'azione «split» non è più disponibile sulla riga pescata: qualcuno l'ha già divisa | **possesso dei dati** |
  | 4 | `tx-commit-all-types:455` | `isVisible({timeout: 1000}).catch(() => false)`: sotto carico il campo descrizione risulta «assente», il test **salta la modifica in silenzio** e poi pretende che Salva sia abilitato | **il test assume invece di verificare** |
  | 5 | `tx-import-asset-identity:293` | clicca `continue` e subito `back`: Playwright aspetta che *il pulsante* sia cliccabile, non che il wizard abbia finito di cambiare passo | **verifica intermedia mancante** |

  **Nessun conflitto di scrittura reale.** A quattro worker su un backend condiviso, 215 test
  hanno prodotto due soli rossi da concorrenza, ed entrambi sono difetti del test, non del
  prodotto. Il #4 è la tesi del piano allo stato puro: una sonda condizionale con timeout corto
  trasforma «lento» in «assente» e prosegue come se nulla fosse.

- **7.4 ✅ Riparazione dei cinque rossi.** Tutti difetti dei test, nessuno del prodotto.
  Corsa di verifica dell'area intera a 4 worker: **215/215 verdi in 5,9 min** (17,8 in seriale,
  **3,0×**). Le correzioni, tutte della stessa forma — *sostituire un'assunzione con una verifica*:

  | test | prima | dopo |
  |---|---|---|
  | `tx-commit-all-types` | `isVisible({timeout:1000}).catch(()=>false)` su una sezione che c'è **sempre** su una TX modificabile (verificato in `TransactionFormModal.svelte:2010`) | `expect(...).toBeVisible()` incondizionata: se manca è un rosso, non un salto silenzioso |
  | `tx-import-asset-identity` | `continue` poi subito `back` | attende che lo step precedente sia `hidden` prima di tornare indietro |
  | `tx-tooltips` | scandiva le prime 20 righe cercandone una taggata | filtra per marcatore e le scandisce **tutte**, e asserisce che almeno una esista |
  | `tx-split-promote` ×2 | pescava una riga *appaiata* e dava per scontato fosse divisibile | `findSplittableRowId()`: apre il menù e **guarda** se «split» c'è; essere appaiata è condizione necessaria, non sufficiente |

  > Il caso `tx-split-promote` è il possesso dei dati in forma pura: la riga che cercava era stata
  > divisa da una spec vicina. Non serviva isolarla — serviva che si cercasse una riga adatta
  > invece di sceglierne una e sperare.

- **7.5 ✅** Misura di riferimento di tutte e 8 le categorie a macchina fredda — consegnata dalla
  tabella della 11.5, che le misura tutte dopo il ribaltamento anziché prima.

> **Reperto che cambia la tappa 11.** Consolidare le ~20 invocazioni in una sola **non fa
> risparmiare tempo** (17,8 min in una sola invocazione contro i 17,6 del runner che ne fa venti):
> a differenza del backend, dove 47→1 fu metà del guadagno, qui l'overhead di avvio è trascurabile.
> Ma il consolidamento resta **necessario lo stesso**, per un altro motivo: con una spec per
> invocazione il parallelismo ha un solo file da distribuire, e i worker non servono a niente.
> Il 2,9× si incassa solo eseguendo la categoria intera in un colpo — il che rende obbligatorio
> sistemare le tre dipendenze dall'ordine, che oggi l'isolamento per unità nasconde.

### Tappa 8 — I difetti di prodotto ✅

Indipendenti dal resto, valore visibile all'utente, piccoli. **Tutti e tre fatti.**

- **8.1 ✅ Rendering progressivo di assets e fx.** L'onda 2 (prezzi/tassi) è uscita dalla finestra
  `loading`. Le righe nascono con `loadingPrices: true` / `loading: true` e si disegnano lo
  scheletro da sole; `data-busy` resta l'unico segnale di «entrambe le onde finite».

  > Delle due complicazioni che il piano temeva, **una non esisteva**: `fetchAllPriceData()` e
  > `fetchAllPairData()` hanno già il proprio `try/catch` e azzerano il flag su ogni percorso, quindi
  > l'errore dell'onda 2 non è mai uscito da nessuna parte. L'unica cosa vera da sistemare era il
  > percorso «tutto in cache» di fx (riga 403), che aggiornava i dati **senza spegnere** il flag:
  > invisibile finché nasceva `false`, un caricamento eterno appena nasce `true`.
  > La risoluzione di «All» non è toccata: vive dentro l'onda 2 e lì è rimasta.

- **8.2 ✅ ImageEditModal.** `disabled={!editReady}` su tutti i comandi che modificano l'immagine,
  più un overlay `image-edit-init-guard` sopra il cropper — che non è un controllo di form e
  quindi `disabled` non lo raggiunge. Chiudi e Annulla restano attivi: l'utente deve sempre poter
  uscire.

- **8.3 ✅ La ricerca asset moriva in silenzio** — *difetto trovato dalla concorrenza, non dal
  censimento*. `executeSearch()` usciva senza dire niente se `selectedProviders` era vuoto, cioè
  **finché la lista dei provider non era arrivata**. Chi digitava prima di quel momento perdeva la
  ricerca: il debounce era già scattato, nessuno ritentava, e il campo restava morto. A 1 worker i
  provider arrivavano sempre in tempo; a 4 no.

  Il componente sapeva già aspettarli — ma solo per `initialQuery` (l'effect che rilancia la
  ricerca a `providersLoaded`). Il percorso digitato non aveva lo stesso riguardo. Ora la query
  viene **trattenuta** (`pendingQuery`) e rilanciata all'arrivo dei provider, con il dropdown già
  aperto in stato «sto cercando». `loadProviders()` segna `providersLoaded` **anche quando
  fallisce**: una query in attesa non deve girare per sempre su una lista che non arriverà mai.

  Aggiunto `data-testid="asset-search-results"` + `data-state` (`searching|results|empty|error`).
  Il test chiedeva «sei in uno di questi due stati *adesso*?» campionando due classi CSS 1,5 s dopo
  aver digitato; ora chiede «hai reagito?», che è la domanda vera e ha un timeout.

  > Vale la pena notare cosa è successo: nessuno cercava questo bug. È emerso perché il
  > parallelismo ha reso *normale* una condizione che prima era rara. È il rendimento vero della
  > tappa 7, oltre ai minuti.

**Verifica.** `assets/ fx/` — 148 test — **verdi in seriale (9,2 min) e verdi a 4 worker
(4,9 min, 1,9×)**. `front-asset` si è guadagnata la promozione insieme a `front-fx`.

<details><summary>dettaglio 8.1</summary>

Oggi `loadAssets()` faceva `await fetchAllPriceData()`
  *dentro* la finestra `loading = true`, e il template (riga 1407) sostituisce l'intera pagina con
  uno spinner. La macchina che serve **esiste già**: ogni riga ha `loadingPrices` e il componente
  riga riceve già `loading={asset.loadingPrices}` (riga 1462) — sa disegnarsi lo scheletro da sola.
  È solo irraggiungibile perché lo spinner di pagina le sta davanti. Idem in `fx/+page.svelte`
  (`pairs[i].loading`, riga 1097).
  Due complicazioni da gestire, non scoprire dopo: l'errore dell'onda 2 esce dal `try` di
  `loadAssets`, e la risoluzione di «All» (data minima globale) oggi legge i prezzi, quindi arriva
  dopo. `data-busy` resta corretto e diventa l'unico segnale di «entrambe le onde finite».
- **8.2 ImageEditModal**: comandi disattivati durante l'init (~500 ms), come concordato. Oggi sono
  attivi e scartano in silenzio: l'utente ruota, chiude, e perde la modifica senza un avviso.

</details>

### Tappa 9 — Il segnale ✅

- **9.1 ✅** `notify()` in `$lib/stores/app/notify.svelte.ts`: ring buffer da 100 sempre,
  toast se dovuto. `toasts.show()` rispecchia già il messaggio in `debug` con l'HTML rimosso,
  quindi la metà umana non ha avuto bisogno di niente in più.
- **9.2 ✅** `eventSeq` / `waitForEvent` / `waitForSettled` in `e2e/fixtures/app-events.ts`
  (accanto agli altri helper, non in una cartella nuova).
  `waitForSettled` rilegge l'attributo **sullo stesso elemento** invece di aspettare che compaia un
  qualsiasi `[data-busy="false"]`: su una pagina con contenitori annidati il secondo avrebbe
  accettato un vicino che non era mai stato occupato.
- **9.3 ✅** `data-busy` esteso da 2 a 5 pagine: `assets`, `fx`, `transactions`, `brokers`, `files`.
  La dashboard non ha uno stato di caricamento proprio — i suoi widget se lo gestiscono da soli.
- **9.4 ✅** Regole scritte in quattro posti, non due: `frontend.instructions.md` (quando si deve un
  toast, tabella a 6 righe, `notify()`, «pubblica lo stato, non stamparlo»),
  `frontend-testing.instructions.md` (regole 5, 6, 7 + sezione parallelismo),
  `testing-frontend/SKILL.md` (parallelismo per blocco, segnali, e i tre divieti nuovi).

### Tappa 10 — Adozione guidata dai rossi

Non «convertire 572 attese». Convertire **quelle che la sonda ha dimostrato bloccanti**, più gli
helper condivisi ad alta leva (che si pagano per test, non per file — è così che `front-asset` e
`front-fx` hanno reso).

- **10.1** `front-transaction` per prima: 406 attese su 572, 17,6 min su ~40.
- **10.2** Le altre 7 categorie, in ordine di rossi trovati.
- **10.3** Riscrittura dei test a conteggio globale / posizione fissa emersi dal triage, secondo la
  regola del possesso dei dati.
- **10.4** Promozione `mode:'parallel'` blocco per blocco, ognuna **guadagnata** da una corsa
  parallela verde. Chi resta seriale scrive il perché, come `exclusive_because` sul backend.

#### 10.2/10.3/10.4 — `ai-export + brokers + portfolio + settings` ✅ (2026-08-14)

**Risultato**: 4,9 min seriali → **3,4 min** con le dichiarazioni (1,4×), **2,5 min** col flag (1,9×).
98/98 verdi, **stesso conteggio del seriale**: prima uno si auto-escludeva.

Sei rossi, e **nessuno era un conflitto di scrittura**. Uno per uno:

| # | test | causa | correzione |
|---|---|---|---|
| 1 | `brokers/multi-user.spec.ts:52` | blocco che condivide due contesti browser fra i test | `mode:'serial'` **con motivazione scritta**; secondo test fa login esplicito |
| 2 | `risk-analysis.spec.ts:599` | l'oracolo era uno **snapshot server** di un broker condiviso; la UI congela il *suo* al caricamento pagina, e un vicino le fa divergere per sempre | oracolo spostato sul client: la richiesta deve combaciare con i chip che il pannello mostra |
| 3 | `settings/scheduler.spec.ts` FSCH‑010 | due sonde in cascata, entrambe scadute sotto carico → `test.skip()` **silenzioso**: la regressione non era sorvegliata | prende un asset dall'API e va dritto alla modale; niente sonde |
| 4 | `brokers/brokers.spec.ts` CRUD | **rowid riciclato** (vedi sotto) | asserisce sul nome che possiede, non sull'ID |
| 5 | `brokers-detail.spec.ts` `ensureBrokerExists` | `waitForTimeout(1000)` poi `count()` → zero sotto carico → crea un broker con **nome fisso** → collisione fra worker | attende `data-busy="false"`; nome reso unico |
| 6 | `portfolio/broker-icons.spec.ts:37` | il pannello posizioni non pubblicava lo stato: sotto carico il report (FIFO a runtime) supera i 10 s e il test guarda uno scheletro | `data-busy` su `positions-panel`, il test lo attende |

**Il reperto che vale oltre questi test — il rowid riciclato.**
I modelli dichiarano `INTEGER PRIMARY KEY` **senza `AUTOINCREMENT`** (zero occorrenze nel repo): in
SQLite quello *è* il rowid, e il rowid più alto **viene riusato** appena la riga è cancellata. Il test
CRUD creava il broker 11, lo cancellava correttamente, e un test vicino si prendeva subito l'11
liberato. L'asserzione «la card 11 non c'è più» falliva **su un altro broker**, mentre il proprio era
sparito davvero: test con ragione, rosso lo stesso.

> **Regola**: un ID identifica una riga *finché la riga vive*. Dopo una delete non identifica più
> niente. Asserisci l'assenza tramite un marcatore che il test possiede (nome con timestamp), mai
> tramite l'ID che il database può restituire a qualcun altro.

**Perché il flag resta più veloce delle dichiarazioni (2,5 vs 3,4).**
Non è che le dichiarazioni vengano ignorate: su un singolo file l'A/B è **identico** (46,5 s vs
47,6 s). La differenza è la **granularità dello scheduler**. Con `fullyParallel: false`, Playwright
assegna un file per worker: in coda alla corsa i worker restano fermi ad aspettare l'ultimo file
lungo. Con `fullyParallel: true` ogni test è unità indipendente e i worker liberi si riempiono da
qualunque file. → **Il residuo 1,4× → 1,9× si incassa nella tappa 11 ribaltando il default della
config**, non aggiungendo altre dichiarazioni.

**Latente, annotato e non toccato**: `tx-commit-all-types.spec.ts:615` ha la stessa esposizione
all'ID riciclato (`tr[data-row-id="tx-{id}"]` dopo la delete), ma il difetto vero è più a monte —
**cancella una transazione che non ha creato**, pescandola fra le prime 10 righe. Sistemarlo bene
significa fargliene cancellare una propria: riscrittura invasiva su un'area già verde a 4 worker.

#### 10.2/10.3 — `assets + fx + utility` e il debito `tx-commit-all-types` ✅ (2026-08-14)

**`tx-commit-all-types.spec.ts` — chiuso il debito.** Tre test su tre prendevano righe altrui:
i due di delete e quello di edit (che cambiava la *description di una transazione di qualcun altro*).
Ora ognuno crea la propria, ne cattura l'ID **dalla risposta di commit** — che nessuno leggeva —
e la ritrova col filtro URL `id_min`/`id_max`, l'unico modo affidabile visto che la paginazione è
client-side e il backend restituisce tutto. L'assenza si asserisce sulla **description posseduta**,
mai sull'ID: l'ID può essere già di un altro (rowid riciclato).

**I rossi della sonda su `assets + fx + utility` (295 passati, 3 rossi, 1 skip):**

| test | causa | correzione |
|---|---|---|
| `files.spec.ts` ×2, anteprima immagine | il modale resta su "Loading…": sotto carico il fetch supera gli 8 s e il test guarda un modale vuoto | `data-busy` su `file-preview-shell`, helper `waitForPreviewReady` |
| `asset-event-delete.spec.ts` | `waitForTimeout(500)` dopo il click sul tab → 0 eventi letti; e il primo test **consuma** un evento Apple che il secondo legge | attende `aria-selected` + `data-busy` della pagina; blocco dichiarato **serial** (fixture finita e condivisa) — *dichiarazione poi rimossa alla 11.4, vedi sotto* |

**Un altro test che non girava — `asset-modal.spec.ts` NR Bug K.** Non ha mai eseguito niente, per
**due** motivi indipendenti, entrambi nascosti da `test.skip`:
1. chiamava `GET /api/v1/assets?page_size=200`, rotta che non esiste (è `/assets/query`) → 422 → skip;
2. anche superandolo, rendeva "dirty" il provider scrivendo uno spazio e cancellandolo, ma
   `providerDirty` è un `$derived` che **confronta valori** (`AssetModal.svelte:358`), non un flag:
   ripristinare la stringa lo riporta a false e Save resta disabilitato.
Dichiarato `test.fixme` con la spiegazione: un rosso visibile vale più di un verde finto.

**E un bug che perdeva dati.** `tx-bulk-suggest-ux.spec.ts` leggeva `results[].tx_id` dalla risposta
di commit — campo inesistente, il vero nome è `ids`. Il risultato erano due `undefined`, quindi il
`cleanup` non cancellava niente: **ogni esecuzione lasciava due transazioni** nel database condiviso.
Corretto, insieme ai suoi tre skip silenziosi (due righe pescate dalla prima pagina → ora se le crea).

### Tappa 11 — Cablaggio e regole

- **11.1 ✅** `--workers` arriva a Playwright. Era già una variabile d'ambiente, ma il runner non la
  scriveva mai: `./dev.py test front-transaction --workers 4` diceva 4 al backend e 1 al browser.
  Ora `_apply_parallel` scrive `_common._E2E_WORKERS` (stesso schema di `_COVERAGE_PY`) e
  `_run_playwright` lo inietta come `E2E_WORKERS` nell'ambiente figlio, senza sovrascrivere una
  variabile già posta dalla shell. Stampa `🧵 Playwright workers: N`, così il numero è nel log.
- **11.2 ✅ — non c'era niente da fare, e questo cambia la 10.4.** `E2E_FORCE_PARALLEL=1` **è già**
  `fullyParallel: true` (`playwright.config.ts:40,55`): non «ignora le dichiarazioni», le rende
  irrilevanti. Conseguenza pratica: **ogni sonda forzata verde è già la prova che serve per
  ribaltare il default**. Scrivere 45 `test.describe.configure({mode:'parallel'})` per poi
  cancellarli alla 11.5 sarebbe puro moto. → **la 10.4 si fonde nella 11.5**: si ribalta il default,
  e restano solo le dichiarazioni `mode:'serial'`, che diventano il **catalogo delle eccezioni**.
- **11.3 ✅** `e2e.md` (sezione *«Parallelismo: guadagnato, non assunto»* — ora riscritta al
  modello opt‑out: le quattro famiglie di rosso, la quinta, il paragrafo sulla pulizia, e le tre
  eccezioni seriali). `runner_architecture.md`: sottosezione *«--workers reaches Playwright too»*
  con i due conteggi di worker distinti, più il riquadro che spiega perché **il consolidamento
  ora serve due volte** — non solo per l'avvio, ma perché un'invocazione può distribuire solo i
  test che ha ricevuto. Invertite anche le tre regole scritte: `frontend-testing.instructions.md`,
  `testing-frontend/SKILL.md`, `test-author.agent.md`.
- **11.4 ✅** Rimisura finale a macchina fredda: **17m00s, 632 test E2E + 695 vitest, zero rossi**.
- **11.5 ✅** *(assorbe la 10.4)* `fullyParallel: true` è il default spedito.

#### 11.4 — la misura dell'intero frontend, e i due test che aveva ancora da dire

La prima corsa di `all-frontend` a 4 worker: **17m03s**, con un solo rosso; la seconda, dopo le
correzioni, **17m00s** — stesso tempo, e il tempo è quindi **stabile**, non fortunato. Per confronto,
prima di questo piano la sola `front-transaction` ne durava 17,6 attraverso il runner.
**L'intero frontend oggi costa quanto costava una categoria.**

I due rossi della prima corsa sono entrambi della famiglia «il test assume uno stato che non
possiede», e nessuno dei due era visibile a categoria singola:

| test | causa | correzione |
|---|---|---|
| `asset-modal` NR Bug G | fa `PUT base_currency=GBP` dal contesto API, ma il browser tiene il valore **messo in cache al login** (`auth.ts` → `setDirect`). La modale legge la valuta una volta sola all'apertura: se il `GET /settings/user` non è ancora atterrato, cattura EUR | arma l'attesa della risposta con `base_currency === 'GBP'` **prima** di navigare |
| `asset-event-delete` scenario 1 | cancellava uno dei **due** eventi non collegati di Apple: funzionava esattamente due volte. Alla terza la prima riga è un evento collegato, l'API risponde `in_use`, e il rosso non c'entra niente col codice | il test **crea l'evento che cancella** (data fuori dalla finestra 3M usata dal vicino), lo ritrova per `data-row-id`, e asserisce che *quel* `event_id` risulti `deleted` |

> Il secondo caso ha anche **cancellato un'eccezione**. Il blocco era `serial` con motivazione
> «fixture finita e condivisa»: vera, ma curava il sintomo. Un test che consuma dati di fixture è
> un test con una data di scadenza — dichiararlo seriale compra tempo, fargli creare ciò che gli
> serve toglie il problema. Il catalogo delle eccezioni scende a due: `multi-user` e `tx-brim-import`.
> Verificato: 4/4 verdi in parallelo, e `front-asset` intera **85/85 in 2,2 min**.

La **seconda corsa completa** (17m00s) ne ha aggiunto un terzo, che le corse per categoria non
avevano mai mostrato: `risk-analysis` › *asset Risk runs typed scenarios* cercava
`risk-comparison-controls` e non lo trovava entro 12 s.

Non era un timeout da allungare: è la **quinta famiglia in una forma nuova**. Ogni sezione del
pannello rischio è condizionata al catalogo delle capability (`supportsComparison = hasRiskCapability(catalog, 'comparison')`),
quindi una sezione assente significa **due cose diverse** — «non supportata» oppure «catalogo non
ancora atterrato» — e il test non poteva distinguerle. A un worker il catalogo arrivava sempre
prima del click; a quattro no.

La correzione è quella di dottrina, **pubblicare lo stato invece di indovinarlo**: il pannello
espone ora `data-catalog="pending|ready"` (e `data-busy` da `initialLoading`), e i tre helper di
apertura lo attendono. Il test smette di chiedere «la sezione c'è?» e chiede «il catalogo è
arrivato?», che è la domanda vera — e se dopo *quella* la sezione manca, è un rosso legittimo.
Il catalogo delle eccezioni resta a due.

> È lo stesso difetto di `isVisible().catch(()=>false)` visto dal lato del prodotto: non era il
> test a mentire, era il DOM a non dire abbastanza. Un rendering condizionale che dipende da un
> fetch **deve** pubblicare se quel fetch è arrivato, altrimenti chiunque lo osservi sta misurando
> la latenza di rete e chiamandola funzionalità.

#### 11.5 — il ribaltamento, e le due cose che ha rotto per strada

**Il risultato.** Otto categorie su otto verdi attraverso il runner a `--workers 4`:

| categoria | dopo | prima |
|---|---|---|
| `front-transaction` | **5,6 min** | 16,7 (runner) / 17,8 (seriale) |
| `front-utility` | 2,7 min | 164 test |
| `front-asset` | 2,3 min | 85 test, 1 skip |
| `front-fx` | 1,4 min | 3,2 seriale |
| `front-ai-export` | 1,4 min | 34 test |
| `front-portfolio` | 1,1 min | 22 test |
| `front-user` | 0,9 min | 17 test |
| `front-broker` | 0,8 min | 31 test |

**Incompatibilità colta prima di spedirla — l'igiene delle transazioni.**
`e2e/fixtures/playwright.ts` ha una fixture che, al cambio di spec file, cancella *«ogni id creato
da quando ho aperto questo file»*, e in un percorso arriva a `populate_mock_data --force`. La sua
correttezza poggiava tutta su una premessa che il ribaltamento **elimina**: «un worker esegue un
file dall'inizio alla fine, da solo». Con lo scheduling per test, quella frase descrive anche le
righe che un altro worker sta usando in quel momento — e il ripopolamento svuoterebbe il database
sotto tre test in corsa. Disattivata sopra 1 worker, con un avviso stampato una volta per worker.
Empiricamente non serviva più: 216/216 e 298/298 verdi senza.

**Il bug di cablaggio che non si vedeva.** `./dev.py test --workers 4 front-transaction all` girava
**verde in 16,7 min** — cioè non parallelo affatto. Ci sono **due** percorsi che lanciano
Playwright (`_frontend_common._run_playwright` per unità, `_consolidate._run_playwright_batch` per
la categoria consolidata) e la 11.1 ne aveva cablato uno solo. Il sintomo di un cablaggio a metà è
**niente**: corsa verde, tre volte il tempo, nessun messaggio. Estratto
`_common.apply_e2e_workers(env)`, chiamato da entrambi. Rimisura: **216 test in 5,6 min (3,0×)**.

> Vale come regola generale: quando un'opzione viaggia per variabile d'ambiente, il punto di
> iniezione va reso **unico**, altrimenti il secondo percorso non fallisce — tace.

#### Altri due difetti di prodotto trovati dalla concorrenza

- **La scrittura dei metadati BRIM non era atomica.** L'endpoint di parse documenta «nessun dato
  persistito nel database» — vero, e fuorviante: `brim_provider.py` riscrive `last_parse_result`
  nel JSON di metadati del file, con un read‑modify‑write non atomico. Otto test BRIM che
  analizzano lo stesso file lo corrompevano a vicenda. Aggiunto `_write_metadata_atomic()`
  (temp file + `Path.replace`); il blocco resta comunque `serial` finché ogni test non carica il
  proprio file, perché l'ultimo scrittore vince lo stesso.
- **`timeout_keep_alive` di uvicorn a 5 s.** Un `ECONNRESET` isolato su `POST /brokers`: il client
  riusa un socket che il server ha appena chiuso, e una POST non viene ritentata. Portato a 65 s
  in modalità test.

> Il declassamento `success → simulated` della tappa 10 era **troppo largo**: scattava anche sui
> dry‑run, e `TransactionBulkModal.svelte:1146` costruisce `pendingTxIds` proprio dai `success`
> della risposta di `/validate`. L'indicatore ● è sparito per una settimana senza che nessun test
> lo notasse. Ristretto a `commit and issues`, e il blocco di documentazione di `TXItemStatus`
> riscritto: chi vuole sapere «le mie righe esistono?» deve leggere `committed`.

#### Il censimento che non è servito, e i due difetti di prodotto che ha trovato

Prima di dichiarare i blocchi ho contato: **46 spec non‑gallery, nessuna con stato condiviso reale**
(due sospetti, entrambi falsi positivi: un `beforeAll` che prende solo un cookie, e un `let` locale
dentro un helper). Quindi il censimento non ha escluso nessuno — ma la sonda che l'ha accompagnato
ha trovato due difetti che **non sono dei test**.

**1. `POST /transactions/commit` rispondeva 200 su un batch annullato.** Due test NR‑D fallivano
cercando una riga che avevano appena creato. A 1 worker fallivano uguale — quindi non concorrenza.
Una spec usa e getta che stampava la risposta grezza ha mostrato la verità:

```
200 OK   results[].status: "success"   ids: [72], [73]   committed: false
issues: ["Cash balance for EUR goes negative (-360.87) on 2026-06-25 for broker 5"]
```

Il servizio documenta `"success"` come *«applicato **e** batch committato»* e `"simulated"` come
*«applicato in sessione ma annullato»* (`transactions.py:677`), ma il passo 8 non declassava mai.
Il chiamante leggeva `resp.ok()`, vedeva `success`, riceveva perfino gli `ids` — che erano gli id
che le righe **avrebbero avuto** — e credeva di aver creato dei dati che non esistevano.
Corretto in `transaction_service.py`: se `issues or not commit`, ogni `success` diventa `simulated`.
`success_count` si calcola **prima** del declassamento (`/validate` è un dry‑run per definizione:
azzerarlo lo avrebbe reso muto). Entrambi gli helper di commit ora asseriscono `committed`.

> Non è un artefatto di test. È un contratto rotto verso qualunque client: l'unica risposta a
> «i miei dati esistono?» era un campo che nessuno guardava.

**2. Il backend degli e2e girava sotto `--reload`.** `playwright.config.ts` avviava uvicorn senza
`--no-reload`, e il watcher copre la radice del repo. Le mie modifiche **durante** una sonda hanno
riavviato il backend cinque volte, uccidendo 8 test al `login()`. Il runner passa già `--no-reload`
per il suo backend condiviso; il `webServer` di Playwright no. Aggiunto, col sintomo scritto nel
commento (una raffica di timeout di login nei primi test schedulati).

> Regola operativa che resta valida comunque: **non si modifica il repo mentre gira una sonda**.
> Un rosso da contaminazione costa più della corsa che lo produce, perché sembra un rosso vero.

#### La quinta famiglia: `resp.ok()` scambiato per «creato»

Alle quattro famiglie già note (pagina‑1‑come‑esistenza, `waitForTimeout`, ID‑come‑identità‑dopo‑delete,
verifica intermedia mancante) se ne aggiunge una:

| famiglia | la domanda che il test crede di fare | quella che fa davvero |
|---|---|---|
| `resp.ok()` come «creato» | «la riga esiste?» | «il server ha risposto?» |

È la stessa forma di `isVisible().catch(()=>false)`: una sonda che risponde sempre qualcosa, e un
test che prosegue su un'assunzione. Nuovo helper condiviso `e2e/fixtures/paging.ts`
(`findAcrossPages`, `pageUntilVisible`, `maximisePageSize`) per la famiglia gemella — leggere
`count()` subito dopo aver aperto una tabella chiede *«è in prima pagina?»*, non *«esiste?»*.


---

## Reperti da decidere (non bloccanti)

- **Il progetto `mobile` gira solo per `front-ai-export`.** `playwright.config.ts` definisce
  `desktop` e `mobile`, e quasi ogni azione passa `project="desktop"`; le sole quattro spec di
  `ai-export` omettono il parametro e girano quindi su **entrambi**. Non è configurazione morta —
  è copertura mobile che esiste per un ottavo del frontend e per nessun altro.
  → **Deciso**: per ora i test sono desktop‑only *di proposito*, tranne quell'isola. Sappiamo
  esattamente quanta copertura mobile abbiamo, che è il punto.
- **`front-transaction` non ha guadagnato nulla** dalle 18 rimozioni della tappa 4 (17,5 → 17,6):
  le sue sleep sono piccole e dentro helper di pulizia condizionali. Conferma che il guadagno lì
  verrà dal parallelismo, non dalle attese.
- **Processi forkserver orfani** dopo le corse `api`: causa ancora ignota, innocuo finora.

## Rischi

| rischio | perché è credibile | contromisura |
|---|---|---|
| I rossi paralleli sono troppi e illeggibili | il backend ne fece 14 su 603, e 13 avevano **una** causa | la sonda 7.1 è su una categoria media, non su tutto; si legge la causa comune prima di toccare i test |
| Il ring buffer finisce in produzione | sono ~30 righe, ma vanno scritte bene | cap fisso a 100, nessuna chiusura su oggetti grandi, nessun `JSON.stringify` all'inserimento |
| Il rendering progressivo rompe la risoluzione di «All» | dipende davvero dai prezzi | 8.1 la tratta esplicitamente |
| Si converte a mano e si scopre che non serviva | già visto: 18 rimozioni su transaction, zero guadagno | 10.1 parte **dai rossi**, non dal censimento |
