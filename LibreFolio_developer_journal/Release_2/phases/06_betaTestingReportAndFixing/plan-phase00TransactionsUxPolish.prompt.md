# P5 — UX transazioni

> **Priorità**: 🟠 Media
> **Ambito**: `frontend/src/lib/components/ui/display/CompactCashCell.svelte`,
> `ui/feedback/Tooltip.svelte`, `transactions/modals/TransactionFormModal.svelte`,
> `transactions/modals/TransactionBulkModal.svelte`, `routes/(app)/transactions/+page.svelte`
> **Rilievi coperti**: T1–T4
> **Riferimenti**: [`01_tassonomia_findings.md`](01_tassonomia_findings.md) §2, §3

---

## 🔴 T1 — I decimali `,` e `.` vengono cancellati mentre si digita

> *"in aggiungi transazione non prende la , e il . per i decimali, e anzi, se si scrive senza
> avere prima il decimale il parse lo cancella subito"*

È il difetto più fastidioso del gruppo: **rende difficile inserire qualunque importo non intero**,
cioè la maggioranza dei casi reali.

> 🔬 **Probe live 02/09/2026** (server di test :6040, digitazione carattere per carattere,
> chiusura senza salvare) + probe jsdom sul branch `dev_release2`:
>
> | Campo | Digitato | Osservato | Diagnosi |
> |---|---|---|---|
> | **Importo** (`CompactCashCell`) | `3`,`4`,`,`,`7` | `3`→`34`→`34`→`347` | **Virgola cancellata a metà digitazione** — causa radice sotto, ancora viva |
> | **Quantità** | `1`,`2`,`,`,`5` | `10`→`120`→`12,0`→`12,50` | Il campo parte pre-riempito a `"0"` (`emptyDraft.quantity: '0'`, `TransactionFormModal.svelte:264`) → per inserire il separatore serve freccia-sinistra + separatore. La virgola in sé è accettata (raw preservato da `qtyDisplay`) |
>
> Il feedback dell'utente 02/09: *"sugli importi non si comporta male, ma sulla quantità devo
> scrivere un numero e se voglio la virgola devo fare freccia sinistra e poi il punto"*.
> Il probe mostra che **entrambi** i campi hanno un difetto, diverso per campo.

### Il ciclo che causa la cancellazione (campo importo)

```
utente digita "12,"
  │
  ├─▶ CompactCashCell.handleAmountInput (:96-99)   amountStr = "12,"
  ├─▶ emit() (:80-89)                              normalizeDecimalInput → "12."  → onChange
  ├─▶ TransactionFormModal.setCash (:1179-1181)    draft = {...draft, cash: v}   ← NUOVO OGGETTO
  ├─▶ il nuovo riferimento ridiscende come prop `value`
  ├─▶ $effect di sincronia (:71-78)                formatDecimalForDisplay("12.") → "12"
  └─▶ "12" !== "12,"  →  amountStr = "12"          ✗ separatore cancellato
```

**Causa radice**: classico anello di retroazione da componente controllato. L'`onChange` del figlio
attraversa lo `$state` del padre e **ritorna indistinguibile da una modifica esterna**. La guardia
dell'effect (`incomingAmount !== amountStr`) previene il loop infinito, ma non questa singola
sovrascrittura errata.

Ironia utile: la docstring di `formatDecimal.ts:20-22` **avverte esplicitamente** di non
riformattare durante la digitazione (*"don't reformat mid-typing"*). L'anello di retroazione la
invoca a ogni tasto, aggirando l'avvertimento.

### Fix — due interventi (aggiornato 02/09)

**T1-a — importo** (strategia A del piano originario): nell'effect confrontare i valori
**normalizzati**, non le stringhe di display: se `"12."` e `"12"` sono lo stesso numero, non
toccare il buffer locale.

**T1-b — quantità**: `emptyDraft.quantity` da `'0'` a `''` (la validazione richiede già la
quantità, quindi il vuoto resta invalido finché non compilato; il reset a `'0'` per i tipi
`quantityMode: 'forbidden'` a :667-669 resta). Così il campo parte vuoto e la digitazione è
libera — niente più ginnastica col cursore.

> ⚠️ Il componente è condiviso: la fix va verificata su **tutti** i punti d'uso del form
> transazioni (`TransactionFormModal.svelte:1575, 1596, 1652, 1850-1851, 1895-1896`) e sulla bulk
> modal, non solo su "aggiungi transazione".

> 📌 `CompactCashCell` usa deliberatamente `<input type="text" inputmode="decimal">` — scelta
> corretta per la sicurezza locale (virgola/punto). **Non** convertire a `type="number"`:
> reintrodurrebbe i problemi di locale che quella scelta risolve.
>
> Nota storica: questo stesso input ha già causato la rottura silenziosa di 7 spec E2E che lo
> cercavano come `input[type="number"]` (vedi `05_cleanAudit/17_stabilizzazione_suite_completa.md`).
> I test ora usano `input[data-testid$="-amount"]`: mantenere quel selettore.

**Complessità**: Piccola · Solo frontend

---

## 🟠 T2 — Il tooltip compare immediatamente

> *"il tooltip custom non deve comparire subito, dopo qualche secondo che il mouse è fermo o con
> un click, ovunque"*

### Evidenza

`Tooltip.svelte:5` lo dichiara come comportamento voluto: *"0ms delay on hover; stays open indefinitely"*.
Esistono solo ritardi **in uscita** (`:76-77`: `PINNED_LEAVE_GRACE_MS = 30000`,
`HOVER_LEAVE_BRIDGE_MS = 150`); nessun ritardo **in entrata**. `handlePointerEnter()` (`:116-120`)
chiama `show()` in modo sincrono. Le props (`:33-42`) non prevedono alcun `delay`.

### Perché è un punto solo

Il componente è **unico**: 38 file lo importano, 85 usi totali. Nonostante il *"ovunque"* della
richiesta, **la fix è centrale** — un solo componente da modificare, nessuna revisione a tappeto.

### Fix

Aggiungere `showDelayMs` (default proposto **400–600 ms**): timer in `handlePointerEnter`,
annullato in `handlePointerLeave`. I punti d'uso non cambiano; chi ha bisogno di un tooltip
istantaneo può passare `showDelayMs={0}`.

> Verificare che il ritardo **non** si applichi all'apertura per click né alla navigazione da
> tastiera/focus: lì l'intenzione dell'utente è già esplicita e un ritardo sarebbe solo latenza.

**Complessità**: Piccola · Solo frontend

---

## ✨ T3 — "Duplica transazione" non copia la data

> *"Il pulsante duplica transazione non duplica anche la data, la mette ad oggi, so che avevamo
> pensato fosse corretto fare così, ma la realtà sta dimostrando che è meglio di no."*

### È una scelta deliberata, non un difetto

```
// TransactionFormModal.svelte:8  (docstring)
- 'duplicate' → pre-filled, id stripped, link_uuid regenerated, date=today, commits as 'create'
```

```js
// :424
draft = fromTx(row, {regenerateLink: row.related_transaction_id != null, resetDate: true});
// :297
date: opts.resetDate ? todayIso() : tx.date,
```

Le modalità *edit* e *view* chiamano `fromTx(row)` senza opzioni e **preservano** la data: solo
*duplicate* la azzera.

### Perché l'uso reale contraddice il progetto

Il presupposto era "duplico per registrare un'operazione simile **oggi**". L'uso emerso in beta è
opposto: **duplicare per correggere una transazione storica mal classificata** — esattamente quello
che il tester ha fatto per recuperare gli acquisti persi da P1/B1. In quello scenario azzerare la
data distrugge il dato più importante.

### Fix

Rimuovere `resetDate: true` a `:424` e aggiornare la docstring a `:8`.

> ⚠️ **Cambio di requisito, non correzione di bug**: la docstring va aggiornata insieme al codice,
> altrimenti resta a documentare un comportamento che non esiste più. Verificare che nessun test
> E2E asserisca la data odierna dopo una duplicazione.

**Complessità**: Banale (un booleano + documentazione)

---

## ✨ T4 — Eliminazione singola → usare la bulk modal

> *"il pulsante per eliminare 1 sola transazione che fa comparire la modale di delete unica, in
> realtà è alquanto scomoda, meglio fare che cliccando delete si apre la bulk modal transaction
> con la riga marcata come da eliminare."*

### L'infrastruttura c'è già

```ts
// TransactionBulkModal.svelte:76
export type WorkspaceIntent =
  | {action:'create'} | {action:'import'}
  | {action:'edit'; txIds:number[]} | {action:'delete'; txIds:number[]} | {action:'clone'; txIds:number[]};
```

Con `action:'delete'` la modale apre le righe **già marcate** (`:346-347`, `:403-404`), e questo
intent è **già usato oggi** per l'eliminazione multipla (`+page.svelte:319`).

Soprattutto: *edit* e *clone* a riga singola passano **già** dalla bulk modal
(`+page.svelte:625`, `:630`). **Solo `delete` è rimasto l'eccezione** — l'incoerenza è già nel
codice, la richiesta del tester non fa che allinearla.

### Fix

In `handleDeleteRow(row)` (`+page.svelte:673-712`) sostituire `deleteModalOpen = true` con:

```js
bulkIntent = {action: 'delete', txIds: [row.id]};
```

riusando il `<TransactionBulkModal>` già montato a `:968`.

> ⚠️ **Prima di rimuovere `TransactionDeleteModal.svelte`** (331 righe) verificare la parità sulla
> gestione delle transazioni **appaiate** con controparte non accessibile (i "Layout A/B/C" di
> `handleDeleteRow`, `:673-712`) rispetto a `hasPairedDelete` (`:1978`) / `getPartnerOp` della bulk
> modal. Se la parità non è piena, **rimandare la rimozione** e limitarsi al re-instradamento.
>
> 🗑️ **Requisito utente (02/09)**: se la parità passa, la rimozione è **parte del task** —
> eliminare `TransactionDeleteModal.svelte` **e i suoi test** (unit + E2E che la coprono),
> aggiornando di conseguenza la suite. Niente codice morto lasciato "per sicurezza".

**Complessità**: Piccola/Media · Solo frontend

---

## Ordine di esecuzione

```
T1  🔴  [blocca l'inserimento manuale — prima di tutto]
T3      [banale, quick win]
T2      [componente unico, fix centrale]
T4      [ultimo: richiede la verifica di parità sulle transazioni appaiate]
```

---

## Verifica

```bash
./dev.py front check
./dev.py test frontend --filter transactions
```

**Test E2E da aggiungere:**

| # | Scenario | Asserzione |
|---|---|---|
| 1 | Digitare `1234,56` in un campo cash | il valore finale è `1234.56`, il separatore **sopravvive** a ogni tasto |
| 2 | Digitare `12,` e fermarsi | il campo mostra ancora il separatore |
| 3 | Duplicare una transazione storica | la data è **quella originale** |
| 4 | Delete su una riga singola | si apre la **bulk modal** con la riga marcata |
| 5 | Hover su un tooltip | non compare prima del ritardo configurato |

> Il test 1 è quello che mancava: nessuna spec digitava un importo **decimale carattere per
> carattere**, quindi il difetto non poteva emergere.

---

## Stato

> 🔄 **Riallineato il 08/08/2026**, dopo i giri di beta testing su Crédit Agricole. Verificato
> sul codice.
>
> 🔬 **Riverificato il 02/09/2026** con probe live sul server di test :6040 e probe jsdom sul
> branch: T1 è **due difetti distinti** (importo + quantità), entrambi riprodotti — vedi tabella
> nel blocco T1. T2/T3/T4 confermati aperti riga per riga.

| ID | Rilievo | Complessità | Stato |
|---|---|---|---|
| T1 🔴 | Decimali cancellati durante la digitazione | Piccola | ✅ **Fatto 02/09** — T1-a: l'`$effect` di `CompactCashCell` confronta ora i valori **normalizzati** (il ritorno della propria emissione `"12,"→"12."` non sovrascrive più il buffer); T1-b: `emptyDraft.quantity` da `'0'` a `''` (campo quantità parte vuoto) |
| T2 | Tooltip senza ritardo in entrata | Piccola | ✅ **Fatto 02/09** — `Tooltip.svelte` prop `showDelayMs` (default 500ms): hover apre dopo il ritardo, uscita prima del ritardo annulla, click/tap/tastiera istantanei (`showDelayMs={0}` ripristina l'istantaneo) |
| T3 | Duplica non copia la data | Banale | ✅ **Fatto 02/09** — NOTA da collaudo: il reset a oggi viveva nei path **clone** della bulk modal (quelli realmente raggiungibili), non nel `mode='duplicate'` del FormModal (percorso morto, vedi nota sotto). Rimosso in tutti e tre: `resolveInitialRows` (clone da lista), `cloneRow` (dentro il workspace), `createOpFromClone`. Il ramo FormModal resta comunque corretto dopo la pulizia di `resetDate` |
| T4 | Delete singolo → bulk modal | Piccola/Media | ✅ **Fatto 02/09** — `handleDeleteRow` instrada su `bulkIntent {action:'delete'}`; la bulk auto-include il partner e la guardia backend `pairDeleteIncomplete` (ora localizzata ×4) copre il partner non accessibile. **Rimossi** `TransactionDeleteModal.svelte`, export barrel, helper morti in `+page.svelte` e le chiavi `transactions.deleteModal.*` (salvato `splitHint` → `transactions.bulk.splitHint`); test E2E aggiornati da test-author |

### Nota su ciò che è già arrivato per altra via

Durante il beta testing sono stati introdotti, fuori da questo piano ma nella stessa area:
stepping universale con accelerazione su tutti gli input numerici (`actions/numericArrows.ts`),
date scrivibili a mano nei due picker, e i vincoli di validità sui campi numerici. Non chiudono
T1–T4, ma ne cambiano il contorno: le fix vanno provate **con** le frecce attive.

> ⚠️ **Fuori pista (02/09, collaudo)**: il primo fix T3 colpì `TransactionFormModal.fromTx({resetDate})`, ma test-author ha scoperto che `mode='duplicate'` non è raggiungibile da nessuna azione UI — il "duplica" dell'utente passa da `TransactionBulkModal` intent `clone`. Il reset a oggi viveva in TRE punti della bulk (`resolveInitialRows`, `cloneRow`, `createOpFromClone`); rimosso ovunque dopo il collaudo utente che ha beccato il primo fix come inefficace. **Decisione di prodotto aperta**: la modalità `duplicate` del FormModal è codice morto di fatto — ricollegarla o rimuoverla.
