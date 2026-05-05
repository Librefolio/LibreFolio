# Plan A — ContextMenu + Bugfix R7-C1 + R7-H1

**Date**: 2026-05-05
**Status**: ✅ DONE
**Parent**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](./plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md) (Steps 1 + 2 + 3)
**Estimated effort**: ~3.5h

---

## Plan: ContextMenu + 2 bugfix indipendenti

ContextMenu riusabile integrato nel DataTable (right-click / long-press), fix del bug R7-C1 (edit paired crea invece di aggiornare il partner) e fix R7-H1 (type swap non propaga la quantità nella tabella). Tre step senza dipendenze incrociate, raggruppati per evitare 3 cicli plan/execute.

### Steps

1. **Creare [`ContextMenu.svelte`](frontend/src/lib/components/ui/ContextMenu.svelte)** — floating panel posizionato a `{x,y}`, `role="menu"`, dismiss su click-outside/Escape, viewport clamping, separator support, `data-testid`, dark mode. Integrare in [`DataTable.svelte`](frontend/src/lib/components/table/DataTable.svelte): prop `enableContextMenu=true` default ON, `oncontextmenu` su `<tr>` (riga 1121), filtrare `rowActions` con `visible?.(row)`, riusare `handleRowAction()` (riga 680). Nessuna modifica ai consumer (Transactions, FX, Assets, Brokers).

2. **Fix R7-C1 in [`TransactionBulkModal.svelte`](frontend/src/lib/components/transactions/TransactionBulkModal.svelte) `patchDualRowFromForm()`** (riga 1266) — quando non trova un partner hidden esistente (riga 1299), crea un `emptyDraft()` con `status:'new'` perdendo `id`/`original` del partner DB. Fix: prima di creare un nuovo partner, cercare il draft con `_partnerId` matching o `id === related_transaction_id` dell'originale; se trovato (DB row), copiare `id`, `status:'edited'`, `original` nel nuovo draft. Se non trovato (genuinamente nuovo), comportamento attuale.

3. **Fix R7-H1 in [`TransactionBulkModal.svelte`](frontend/src/lib/components/transactions/TransactionBulkModal.svelte) `collectUpdate()`** (riga 595) — la comparazione `signedQty` vs `origSignedQty` applica la regola del tipo CORRENTE (`getTypeRule(d.type)`) anche ai valori originali (riga 600), annullando erroneamente il diff quando il tipo cambia (BUY→SELL: entrambi diventano -10 → diff=0). Fix: calcolare `origSignedQty` con `getTypeRule(orig.type)` (regola del tipo ORIGINALE), così il cambio tipo produce un diff reale (`-10 !== +10`) e `quantity` viene incluso nel payload.

### Further Considerations

1. L'approccio ContextMenu con evento `contextmenu` nativo funziona anche su mobile (long-press)? → Sì, i browser mobile emettono `contextmenu` dopo ~400ms. Se l'utente preferisse un timer custom, si può aggiungere in seguito.
2. Il fix R7-H1 con tipo originale in `collectUpdate()` potrebbe avere side-effect su `cash` sign? → Sì, stessa logica si applica a `buildCash`: anche l'originale deve usare `getTypeRule(orig.type)` per il confronto. Da verificare nella stessa fix.

---

## 🧪 Test Feedback (2026-05-05)

### Step 1 — ContextMenu ✅ CONFERMATO
Right-click su qualsiasi tabella → menù appare con azioni filtrate per la riga. Dismiss su Escape/click-outside funziona. Viewport clamping OK.

### Step 2 — R7-C1 ⚠️ BUG RESIDUO nel FormModal dual validate

**Sintomo**: Modificando la data di un TRANSFER asset, il validate del FormModal invia TUTTI i campi (broker_id, link_uuid, asset_id, type, quantity, tags, description) in `updates`, causando `extra_forbidden` dal backend per i campi non patchabili.

**Root cause trovata**: `TransactionFormModal.svelte` riga 582-584 — la validate dual in mode=edit usa `collectDualCreates()` (progettato per CREATE, produce payload completo) e lo wrappa in `{updates: items.map(i => ({...item, id}))}`. Questo NON fa diff contro l'originale e NON filtra con PATCHABLE_FIELDS.

**Fix necessario**: Creare `collectDualUpdates()` nel FormModal che:
1. Per ciascuna metà (from/to), confronti i campi correnti con `initialRow` / `partnerRow`
2. Includa solo i campi cambiati, filtrati per PATCHABLE_FIELDS
3. Aggiunga `id` da `initialRow.id` / `partnerRow.id`
Oppure: per la validate del FormModal embedded, saltare la validate dual e delegare alla BulkModal (che ha già il fix corretto). La validate del FormModal in mode=edit standalone deve invece usare il proprio collectDualUpdates.

**Nota**: Il fix R7-C1 nel BulkModal (`patchDualRowFromForm` else branch) è corretto ma non viene raggiunto in questo scenario perché `existingPartner` VIENE trovato (link_uuid matcha). Il problema è interamente nel FormModal validate path.

### Step 3 — R7-H1 ✅ CONFERMATO (BulkModal) / ⚠️ FormModal validate mostra diff vuoto

**BulkModal**: Il fix `origRule = getTypeRule(orig.type)` funziona. Dopo BUY→SELL, il payload contiene `{"type":"SELL","quantity":"-5","cash":...}` e il commit va a buon fine.

**FormModal validate preview**: In mode=edit, il FormModal prima di "Applica" fa una validate standalone. Il suo `collectUpdate()` (riga 724) usa `autoNegateQty` (basato sul tipo CORRENTE), applicandolo anche all'originale → diff annullato → `{"updates":[{"id":17}]}` (vuoto). Questo è un bug cosmetico nel preview — il salvataggio effettivo passa dalla BulkModal che usa il fix corretto.

**Fix necessario nel FormModal**: riga 728-729 — calcolare `origQty` con la regola del tipo originale (`initialRow.type`), non del tipo corrente. Stesso pattern del fix BulkModal:
```ts
const origRule = getTypeRule(initialRow.type as TransactionTypeCode);
const origAutoNegate = origRule.quantityRule === 'negative';
const origQty = origAutoNegate ? String(-Math.abs(Number(initialRow.quantity))) : initialRow.quantity;
```

**Nota aggiuntiva utente**: Per errori di bilancio asset negativo, usare 📈 se positivo e 📉 se negativo (al posto del generico). Numeri interi senza `.00`.

---

## 🧪 Test Feedback Round 2 (2026-05-05)

### Step 2 — R7-C1 ⚠️ Diff spurio qty/description nel FormModal

**Sintomo**: Modificata solo la data "Da", ma nel payload compare anche `quantity: "-0.1"` e `description: "Transfer BTC to IB"`. Causa: `collectDualUpdates().diffItem()` usava `JSON.stringify` generico — le quantità hanno formati diversi (`"-0.1"` form vs `"-0.100000"` DB) e description `null` vs stringa vuota.

**Fix applicato**: Campo-aware comparison in `fieldEq()`:
- `quantity`: `Number(a) === Number(b)` (ignora format stringa)
- `cash`: confronto numerico su amount + strict su code
- `description/cost_basis_override`: normalizza `null/undefined/""` → `""`
- `tags`: sorted array comparison
- Default: `JSON.stringify`

**Risultato**: Dopo fix, solo il campo effettivamente cambiato appare nel diff.

**Nota utente su layout BulkModal**:
- Colonna broker troppo a destra (w-12 troppo largo per label "A:")
- Icona tipo non grande come nella tabella principale
- Nomi transazioni doppie dovrebbero andare a capo
- ID della coppia mostra solo `#24`, dovrebbe mostrare `#24 ↔ #25` o layout Da:/A:

→ Questi sono fix di layout addizionali, da tracciare separatamente.

### Step 3 — R7-H1 ✅ CONFERMATO — swap BUY→SELL e SELL→BUY funzionano

**Payload**: `{"updates":[{"id":10,"type":"SELL","quantity":"-5","cash":{"code":"USD","amount":"909"}}]}` — corretto, i campi flippati nel segno compaiono nel diff.

**Banner balance migliorato**:
- ✅ Emoji 📉 per negativo, 📈 per positivo (posizione: numero prima, emoji dopo)
- ✅ Numeri interi senza `.00` (→ `minimumFractionDigits: 0`)
- ✅ `<strong>` su brokerName in tutte le lingue
- ✅ Icone asset (via `icon_url` / `asset_type` fallback) e broker (via `getBrokerIconUrl`) nei messaggi di errore

---

## 🧪 Test Feedback Round 3 (2026-05-05) — FX_CONVERSION Partner crea invece di aggiornare

### Problema FormModal dual edit FX_CONVERSION
**Sintomo**: Modificata solo la data "Da" di un FX_CONVERSION. Il FormModal produce `{"updates":[]}` (vuoto). Nella BulkModal il partner diventa `creates` con tutti i campi, causando errore.

**Root cause**: Il FormModal `collectDualUpdates()` e il BulkModal `collectUpdate()` usano implementazioni completamente diverse della stessa logica di diff. Questo ha causato 3 bug consecutivi (R7-C1, R7-H1, diff spurio qty/description).

### Analisi duplicazioni Form vs Bulk

| Funzione | BulkModal | FormModal | Divergenza |
|----------|-----------|-----------|------------|
| `collectCreate` | `applySignRules()` | inline `autoNegateQty/Cash` | Logica identica, impl diversa |
| `collectUpdate` | `diffFields()` + `applySignRules()` + `PATCHABLE_FIELDS` | inline campo-per-campo | **Causa dei bug R7-H1** |
| `collectDualUpdates` | N/A | `collectDualCreates()` + `fieldEq()` + `PATCHABLE` | Logica diff diversa da BulkModal |
| `PATCHABLE_FIELDS` | riga 590 | riga 890 | **Duplicato letterale** |
| `fieldEq` / `diffFields` | `jsonEq`/`nullishEq` in `diffFields` | `fieldEq` con normalizzazione numerica | **Logica diversa** |

### Fix pianificato: Helper condiviso `txPayloadHelpers.ts`

Creare `frontend/src/lib/utils/txPayloadHelpers.ts` con:
1. `PATCHABLE_FIELDS` — unica copia
2. `applySignRules(qty, cash, typeRule)` — sign-flip pura, senza dipendenza da `DraftRow`
3. `buildCreatePayload(fields, typeRule)` — costruisce TXCreateItem
4. `buildUpdateDiff(current, original, currentRule, originalRule)` — diff con normalizzazione numerica, filtra per PATCHABLE_FIELDS
5. `fieldEq(key, a, b)` — confronto tipo-aware normalizzato (numeri, cash, tags, stringhe)

Sia `TransactionFormModal` che `TransactionBulkModal` importano e invocano le stesse funzioni. Zero duplicazione di logica di diffing.

### Layout fix deferred (non bloccanti)
- [x] BulkModal: colonna broker troppo a destra (w-12 → `min-width:Nch` dinamico basato su lunghezza label i18n)
- [x] BulkModal: icona tipo stessa dimensione della tabella principale (w-4 h-4 → w-5 h-5, matching `1.75rem` della TransactionsTable)
- [x] BulkModal: nomi transazioni doppie vanno a capo (`break-words` + `leading-snug` + `white-space:normal` inline)
- [x] BulkModal: ID coppia mostra solo `#24` → dual Da:/A: layout con `#24` / `#25`
- [x] BulkModal: colonna broker più larga (140 → 190px), colonna type (140 → 155px), colonna ID (70 → 90px), colonna qty (85 → 110px)
- [x] BulkModal: quantità dual con segno e icona direzionale (`-qty 📤` / `+qty 📥`) + colore rosso/verde
- [x] Filtri/sort reset dopo save da BulkModal → soft reload preserva stato DataTable

---

## 🧪 Test Feedback Round 5 (2026-05-05)

### Problema 1 — FormModal `collectDualUpdates` include partner vuoto
**Sintomo**: Cambiata solo la data "Da" di un TRANSFER. Il payload FormModal invia `{"updates":[{"id":24,"date":"2026-04-23"},{"id":25}]}` — il 2° elemento `{"id":25}` è vuoto (nessun campo cambiato) ma viene incluso.

**Root cause**: `collectDualUpdates()` ritorna sempre 2 item (da `diffDualItem`), anche quando il diff è vuoto (solo `{id}`). Il backend riceve un update no-op.

**Fix applicato**: Filtro `.filter(item => Object.keys(item).length > 1)` su `collectDualUpdates()` — include solo item con campi effettivamente cambiati.

### Problema 2 — FormModal view mode senza bottone Edit
**Sintomo**: In mode `view` il titolo mostra 👁 ma non c'è modo di passare a `edit` senza chiudere e riaprire.

**Fix applicato**: Aggiunta prop `onSwitchToEdit` alla FormModal. In view mode, bottone ✏️ (Pencil icon) nel header. Il parent `+page.svelte` lo wira con `formMode = 'edit'`.

### Problema 3 — BulkModal tipo: icona piccola e testo non a capo
**Sintomo**: Nonostante il fix precedente (`w-5 h-5` + `break-words`), il testo non andava a capo perché il `<td>` del DataTable ha `white-space: nowrap` globale.

**Fix applicato**: Aggiunto `style="white-space:normal"` inline al wrapper span della cella tipo, per overridare il `nowrap` del `<td>`.

### Problema 4 — BulkModal quantità dual senza segno/icona
**Sintomo**: La quantità duale mostrava solo il valore assoluto (es. "0.1" / "0.1") senza indicare quale fosse l'uscita e quale l'entrata.

**Fix applicato**: Da: mostra `-qty 📤` in rosso, A: mostra `+qty 📥` in verde. Colonna allargata (85 → 110px).

### Problema 5 — Broker ancora stretto
**Fix**: Colonna broker allargata ulteriormente (170 → 190px).

---

## 🧪 Test Feedback Round 5 (2026-05-05)

### 1. FormModal `collectDualUpdates` filtro ✅ CONFERMATO

### 2. View → Edit apre solo FormModal, non BulkModal ⚠️ → FIX
**Sintomo**: Premendo ✏️ in view mode, la FormModal passava a mode `edit` con commit diretto. L'utente si aspettava il flusso completo (BulkModal + FormModal) come da toolbar Edit.

**Fix applicato**: `onSwitchToEdit` ora chiude la FormModal standalone e invoca `handleEditRow(formInitial)` → apre BulkModal in `edit-many` con autoOpenForm.

### 3. Icona tipo ancora piccola + struttura non corretta ⚠️ → FIX
**Sintomo**: `w-5 h-5` = 20px, la tabella principale usa `1.75rem` = 28px. Inoltre la freccia `↔` era concatenata al testo label, non in un blocco separato.

**Fix applicato**: Icona con `style="width:1.75rem;height:1.75rem"` inline (matching CSS della TransactionsTable). Struttura a 3 blocchi: `<img>` + `<span>↔</span>` + `<span>label</span>` — la label va a capo indipendentemente.

### 4. Quantità dual: niente colori, icone 📉/📈 ⚠️ → FIX
**Sintomo**: Erano state usate icone 📤/📥 con colori rosso/verde. L'utente vuole 📉 (uscita) e 📈 (entrata), senza colori addizionali.

**Fix applicato**: Da: `-qty 📉`, A: `+qty 📈`, testo senza classi colore.

### 5. Broker largo ✅ CONFERMATO (190px)

---

## 🧪 Test Feedback Round 6 (2026-05-05) — Filter/Sort reset fix

### Problema — Filtri e sort reset dopo save da BulkModal/FormModal/Delete
**Sintomo**: Dopo aver salvato dalla BulkModal, i filtri della colonna e l'ordinamento nella tabella principale venivano resettati.

**Root cause**: `reload()` settava `loading = true` → il template `{#if loading}` distruggeva `TransactionsTable` → ricreata da zero con stato interno (filtri, sort, selezione) perso.

**Fix applicato**: Aggiunto parametro `opts?: {soft?: boolean}` a `reload()`. In soft mode (`reload({soft: true})`), non setta `loading = true` → il componente non viene rimontato → stato interno preservato. Usato `soft: true` in:
- `handleFormCommitted()`
- `handleBulkCommitted()`
- `handleBulkDeleteCommitted()`
- `confirmSimpleDelete()`

Il bottone ↺ (refresh manuale) continua a fare hard reload con reset filtri esplicito, come prima.

### ✅ CONFERMATO — filtri e sort preservati dopo save da BulkModal/FormModal/Delete

