# P2 — Wizard di import: identità degli asset, conteggi e reattività

> **Priorità**: 🟠 Alta
> **Ambito**: `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` (3901 righe),
> `ParseDetailModal.svelte`, `backend/app/schemas/brim.py`, `backend/app/api/v1/brokers.py`
> **Rilievi coperti**: W1–W10
> **Riferimenti**: [`01_tassonomia_findings.md`](01_tassonomia_findings.md) §2–§4

---
Nota a posteriori:

Mentre ragionavo sul test fatto con l'utente beta, ho riflettuto che per ora il sistema di eliminazione dei duplicati per overlapp non è stato verificato che gestisca anche il caso in cui vengano caricati più file di più broker, tipo 3 di CA, 2 di intesta san paolo, 4 di Directa, ciascuno con i suoi overlapp, bisogna far si che la UI crei per ogniuno di essi un pannel diverso e foldabile magari con l'icona del broker per aiutarsi a identificarlo, e solo a parità di broker le transazioni possono essere testate per l'overlapp.

---

## 0. Il filo conduttore

Sette dei dieci rilievi hanno la **stessa forma**: uno stato calcolato **una volta sola** e mai
rivalutato, oppure calcolato sul dato **grezzo** invece che su quello consolidato.

> Con un solo file l'errore è invisibile. Con **tre file insieme** — cioè lo scenario reale del
> beta test — diventa il problema dominante.

Non sono difetti indipendenti da tappare uno a uno: **W2 (identità degli asset) è la radice**,
e W1 ne è una conseguenza diretta. Vanno affrontati in quest'ordine.

---

## Blocco A — Identità degli asset (la radice)

### 🔴 W2 — Gli asset non sono consolidati tra file

> ➡️ **Passato a P3** ([`plan-phase00AssetIdentityAndIdentifiers.prompt.md`](plan-phase00AssetIdentityAndIdentifiers.prompt.md),
> workstream **WS‑C**, nuovo Step 4 «Unifica asset»). È un problema di **identità**, non di
> conteggio, e va risolto *prima* di chiedere all'utente a quale asset del DB corrisponde un
> titolo. W1 e W3 restano in P2 e consumano la mappa d'identità prodotta da P3.

**Evidenza**: `mergeAllTransactions()` `ImportWizardModal.svelte:698-816`.
La chiave di merge **non** è l'ISIN né il nome: ogni coppia `(file, fake_asset_id)` viene
rimappata su un contatore nuovo (`:706` `let nextFakeId = FAKE_ASSET_ID_BASE;`, `:766`
`globalFakeId = nextFakeId--;`) e registrata come voce autonoma in `assetMap` (`:772`).
Nulla confronta mai `extracted_isin` o `extracted_name` tra file.

**Perché lo stesso titolo compare due volte** — è strutturale nei due layout CA:

| Layout | Metodo | Asset prodotto |
|---|---|---|
| Deposito Titoli | `_parse_securities` | **solo nome**, nessun ISIN |
| Movimenti Conto | `_parse_account_movements` | **con ISIN** (da cedole/scadenze) |

Il tester lo aveva diagnosticato con precisione: *"anche se sono lo stesso asset, in alcuni
compare l'isin e in altri no, dipende certamente dal file, bisogna necessariamente accorpare
gli asset prima."*

**Fix**: introdurre una vera passata di deduplica per identità in `mergeAllTransactions()`:

1. Raggruppare per **ISIN quando presente**, altrimenti per **nome normalizzato**.
2. Una voce **con ISIN assorbe** una voce omonima senza ISIN (l'informazione più ricca vince).
3. Ripuntare **tutte** le transazioni che referenziavano il `fake_id` assorbito.
4. Normalizzazione dei nomi coerente con quella di P1/Step 1 (troncamenti dell'export).

> ⚠️ Tocca `buildDuplicateGroups` e `assetResolutions`: va fatto **prima** di W1, che ne dipende.
> ⚠️ **Ambiguità = nessuna fusione**: due nomi simili con ISIN diversi restano separati.
> Fondere per errore due titoli distinti è un danno peggiore di mostrarne due da unire a mano.

**Complessità**: Media/Alta · Solo frontend · Nessun cambio di schema

---

### 🟠 W1 — Conteggio asset non deduplicato: `14 (37)`

**Evidenza**: `parseAggregateStats` `:199-216`, reso a `:3279`.
`uniqueAssetIds = new Set(allMappings.map(m => m.fake_asset_id))` (`:204`) **sembra** deduplicare,
ma i `fake_asset_id` **collidono tra file** (ogni parse riparte da `FAKE_ASSET_ID_BASE`): il `Set`
deduplica collisioni accidentali di ID, non titoli reali. Il secondo numero (`:205`) è un
`.filter().length` piatto — la somma con duplicati che il tester ha ricostruito da sé:
*"stavo importando 3 file e la somma degli asset fa proprio 37, bisogna fare un set e non contare i duplicati"*.

**Fix**: ricalcolare **entrambi** i numeri dalla mappa d'identità di W2, mai dai `parseResults` grezzi.

**Fix di copy** (richiesta esplicita): separare le due grandezze invece di `14 (37)` →
`14 asset unici · 37 da risolvere`, con etichette esplicite.

**Complessità**: Media *(banale una volta fatto W2)* · Solo frontend

---

## Blocco B — Reattività dello stato

### 🟠 W7 — Dopo l'assegnazione, le transazioni non si auto-selezionano

**Evidenza**: `:793` — `selected: !beforeOpening && duplicateStatusAllowsAutoSelect(dupStatus)`,
impostato **una sola volta** al merge, mai rivalutato quando l'asset viene assegnato dopo.

**La logica corretta esiste già**, in `recheckOpenings()` `:1466-1469`:

```js
mergedTransactions = mergedTransactions.map((t) =>
  !isBeforeOpening(t) && isRowAssetResolved(t) && !t.selected && duplicateStatusAllowsAutoSelect(t.duplicateStatus)
    ? {...t, selected: true} : t);
```

…ma è invocata **solo** dal ricalcolo della data di apertura del broker: mai da `resolveAsset`
(`:819`), `resolveAssetManual` (`:896`), `clearResolution` (`:823`) o dalla callback `oncreated`.

**Fix**: estrarre quel blocco in una funzione riusabile e invocarla da tutti i punti di
risoluzione. Preferibile: rendere l'idoneità un `$derived` di `assetResolutions` (runes Svelte 5),
così il difetto non può ripresentarsi in un nuovo punto d'ingresso.

**Complessità**: Piccola · Solo frontend

---

### 🟠 W3 — Il riepilogo non sottrae le transazioni rimosse

**Evidenza**: `parseAggregateStats` `:199-216` è `$derived` **solo** da `parseResults` (le risposte
di parse immutabili). La risoluzione dei duplicati scrive su `duplicateResolverSelections` /
`mergedTransactions` (`:453-472`): **due alberi di stato disgiunti**, mai collegati. Il riquadro
di step 3 (`:3266`) mostra quindi sempre i totali pre-risoluzione.

**Fix**: derivare i conteggi da `mergedTransactions` (stato consolidato) invece che da
`parseResults` (stato grezzo). Stessa direzione di W1/W2: **il riepilogo deve descrivere ciò che
verrà importato, non ciò che è stato letto**.

**Complessità**: Piccola/Media · Solo frontend

---

### 🟢 W6 — "Annulla" non riporta l'asset a neutro

> ⚠️ **Assorbito da P3** ([`plan-phase00AssetIdentityAndIdentifiers.prompt.md`](plan-phase00AssetIdentityAndIdentifiers.prompt.md),
> punto **B‑02**). P3 riscrive integralmente il blocco `identifierPrompt*` di
> `ImportWizardModal.svelte` che contiene questo bug: eseguirlo qui in parallelo significherebbe
> lavorare sulle stesse righe. In P2 **resta solo come verifica** a valle di P3.

**Evidenza**:
1. `resolveAssetManual` `:896-899` chiama `resolveAsset(...)` **prima** di aprire la modale →
   `assetResolutions[...].resolvedAssetId` è già impostato.
2. `checkAndPromptIdentifier` `:905-934` apre la modale.
3. Il tasto Annulla `:3833-3839` fa **solo** `identifierPromptOpen = false`.

L'assegnazione fatta al passo 1 non viene mai annullata: la modale chiede il permesso per
qualcosa che ha già fatto.

**Fix**: chiamare `clearResolution(identifierPromptFakeAssetId)` — la funzione esiste già a
`:823-825` proprio per questo.

**Complessità**: Banale · Solo frontend

---

## Blocco C — Comunicazione all'utente

### 🟢 W4 — Tipi transazione in inglese nel riepilogo analisi

**Evidenza**: `ParseDetailModal.svelte:181` → `<span>{type}</span>`, enum backend grezzo senza
`$t()`. Il titolo della modale risolve a `importWizard.summary` ("Riepilogo analisi"), che è
esattamente il punto segnalato.

La chiave i18n **esiste ed è usata correttamente altrove** (`TransactionTypeBadge.svelte`,
`transactions.types.*`): è un singolo punto sfuggito, non una lacuna di traduzione.

**Fix**: `$t('transactions.types.' + type)`.
**Complessità**: Banale

---

### 🟢 W5 — `N TX` poco chiaro in italiano

*"in italiano scrivere nello step 4 della revisione N TX non fa capire che TX è transazione,
magari possiamo mettere un emoji con una riga"*

**Fix**: sostituire l'abbreviazione con la parola per esteso (o un'icona + numero) nelle 4 lingue.
`TX` è gergo da sviluppatore, non da utente finale.

**Complessità**: Banale · Solo copy/i18n

---

### 🟠 W8 — Livello **INFO** nei messaggi di import

*"aggiungere un livello info all'import, il warning non è sufficiente"*

**Evidenza**: `brim.py:429` e `:455` → `warnings: List[str]`, testo libero senza severità.
Il pattern esiste già nello stesso file: `BRIMFieldTodo.severity: Literal["blocker","warning"]` (`:399`).

**Fix**: `warnings: List[str]` → `List[BRIMWarning] {message, severity, rows?}`.

> ⚠️ **Cambio di contratto API** — richiede:
> 1. nuovo schema in `backend/app/schemas/brim.py`;
> 2. aggiornamento di **tutti** i provider che scrivono in `warnings`;
> 3. `./dev.py api sync` per rigenerare il client TypeScript;
> 4. rendering per severità in `ParseDetailModal.svelte` e nel riepilogo.
>
> **Non** è una migrazione DB: è un DTO di preview, non dato persistito.

**Sinergia**: il campo `rows` opzionale copre anche **B7** (P1/Step 6) in modo strutturato,
invece di annegare i numeri di riga nel testo. Coordinare i due piani.

**Complessità**: Media · Backend + frontend + contratto API

---

## Blocco D — Prestazioni

### 🟠 W9 — Upload e parsing sequenziali

**Evidenza**: `uploadAllPendingFiles()` `:2129-2158` e `doParseAll()` `:2560-2581` sono cicli
`for` con un `await` per file. Nessun `Promise.all`/`allSettled`.

**Fix**: `Promise.allSettled` con tracciamento di stato per file (la struttura già traccia
`status` per voce, quindi è predisposta).

> Usare `allSettled`, **non** `all`: il fallimento di un file non deve annullare gli altri.

**Complessità**: Piccola · Solo frontend

---

### 🟠 W10 — Parse sincrono dentro `async def` → blocca l'event loop

**Evidenza**: `brokers.py:721` dichiara `async def parse_file(...)`, ma chiama
`brim_provider.parse_file(...)` — un `def` puro (`brim_provider.py:1022`) — **direttamente**.
Nessun `asyncio.to_thread` in tutto `brim_provider.py`.

È parsing XLSX CPU-bound eseguito senza cedere il controllo: **blocca l'intero event loop** per
tutta la durata. Viola la regola di progetto sull'I/O asincrono — che lo stesso file rispetta
altrove (`brokers.py:384`: `await asyncio.to_thread(_delete_brim_files_for_brokers, ...)`).

**Fix**: `parse_output = await asyncio.to_thread(brim_provider.parse_file, ...)`.

> ❗ **W10 va fatto prima di W9.** Parallelizzare il frontend su un backend che blocca l'event
> loop non produce alcun guadagno e peggiora la latenza percepita di tutta l'applicazione durante
> l'import.

**Complessità**: Piccola · Solo backend

---

## Ordine di esecuzione

```
W10 (event loop) ──▶ W9 (parallelo)          [prestazioni — indipendente]

W2 (identità) 🔴 ──▶ W1 (conteggi) ──▶ W3 (riepilogo consolidato)
                 └──▶ W7 (auto-selezione)

W6, W4, W5  [indipendenti, banali — quick win immediati]

W8 (schema warning)  ──▶ coordinare con P1/Step 6
```

---

## Verifica

```bash
./dev.py front check
./dev.py test frontend --filter import
./dev.py api sync          # obbligatorio dopo W8
```

**Test E2E da aggiungere** — lo scenario reale del beta test non è coperto:

| # | Scenario | Asserzione |
|---|---|---|
| 1 | Import di **3 file insieme**, stesso titolo con e senza ISIN | una sola card nello step 4 |
| 2 | Conteggio asset | il numero unici corrisponde alle card mostrate |
| 3 | Assegnazione di un asset | le transazioni collegate si selezionano subito |
| 4 | Annulla sulla modale identificativo | l'asset torna neutro |
| 5 | Risoluzione duplicati | il riepilogo si aggiorna |

> Il fixture di test deve usare **due file con layout diversi**: è la condizione che genera W2,
> e con un file solo il difetto non è riproducibile.

---

## Stato

| ID | Rilievo | Complessità | Stato |
|---|---|---|---|
| W2 🔴 | Consolidamento asset cross-file | Media/Alta | ➡️ Passato a P3 (WS‑C, Step 4 «Unifica asset») |
| W1 | Conteggi non deduplicati | Media | ⏳ Da iniziare |
| W3 | Riepilogo non sottrae le rimozioni | Piccola/Media | ⏳ Da iniziare |
| W4 | Tipi transazione in inglese | Banale | ⏳ Da iniziare |
| W5 | `N TX` poco chiaro | Banale | ⏳ Da iniziare |
| W6 | Annulla non resetta l'asset | Banale | ➡️ Assorbito da P3 (B‑02) — qui resta solo la verifica |
| W7 | Auto-selezione dopo assegnazione | Piccola | ⏳ Da iniziare |
| W8 | Livello INFO nei warning | Media | ⏳ Da iniziare |
| W9 | Upload/parse in parallelo | Piccola | ⏳ Da iniziare |
| W10 | `asyncio.to_thread` sul parse | Piccola | ⏳ Da iniziare |
