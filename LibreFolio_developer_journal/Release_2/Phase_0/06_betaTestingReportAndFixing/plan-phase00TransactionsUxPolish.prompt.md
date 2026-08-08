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

### Il ciclo che lo causa

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

### Fix — tre strade, in ordine di robustezza

| # | Strategia | Nota |
|---|---|---|
| **A** | Nell'effect confrontare i valori **normalizzati**, non le stringhe di display: se `"12."` e `"12"` sono lo stesso numero, non toccare il buffer locale | ✅ Preferita: minima e mirata alla causa |
| B | Sospendere la sincronia discendente mentre il campo ha il **focus** | Efficace ma cambia il comportamento anche per aggiornamenti esterni legittimi |
| C | Flag "dirty" locale finché l'utente sta scrivendo | Più stato da mantenere |

→ **A**.

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

| ID | Rilievo | Complessità | Stato |
|---|---|---|---|
| T1 🔴 | Decimali cancellati durante la digitazione | Piccola | ⏳ Da iniziare |
| T2 | Tooltip senza ritardo in entrata | Piccola | ⏳ Da iniziare |
| T3 | Duplica non copia la data | Banale | ⏳ Da iniziare |
| T4 | Delete singolo → bulk modal | Piccola/Media | ⏳ Da iniziare |
