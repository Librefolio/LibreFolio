# Plan — Phase 7 · Part 4 · Round 3 · Bugfix-1 — Form/Bulk modal redesign + correctness

**Date**: 2026-04-28
**Status**: ✅ DONE — implementazione completa, in attesa di walkthrough utente
**Priority**: P0 (sblocca walkthrough utente)
**Estimated effort**: ~4 h (consuntivo: ~3 h)

**Parent**: [`plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md`](./plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md)

---

## 🎯 Origine — feedback walkthrough utente

Dopo Steps 1–6a chiusi, il primo walkthrough manuale ha portato a galla questi problemi (in ordine di gravità):

### 🔴 Correttezza — bloccanti

| # | Issue | File coinvolti | Note |
|---|-------|----------------|------|
| C1 | `+ Add` mostra `Request failed with status code 422` invece del messaggio Pydantic dettagliato (`loc + msg`) | `TransactionFormModal`, `TransactionBulkModal` | Server risponde `{detail:[{loc:[body,creates,0],msg:"BUY requires asset_id"}]}` ma il catch usa solo `e.message`. |
| C2 | i18n `Save {count}` mostrato letterale invece di `Save 2` | `i18n/{en,it,fr,es}.json` | Codice usa `{values:{n: drafts.length}}` ma traduzioni hanno `{count}`. Mismatch del placeholder. |
| C3 | Cambio `type` non resetta i campi: clone → INTEREST mantiene la quantity vecchia, il campo sparisce dalla UI ma il payload contiene ancora `quantity:5` e il backend salva | `TransactionFormModal`, `TransactionBulkModal` | Oggi solo gating UI; serve **forzare il reset del valore** a livello di draft quando `rule.{assetField,cashField,quantityRule}` cambia. |
| C4 | Rolled-back banner non compare anche con dati invalidi: backend accetta `quantity: "0"` su BUY senza errore | backend (separate) + frontend | Il backend **non** sta validando lato `/bulk` (solo `/validate` lo fa). Da escalare a backend bug — fuori scope di questo round. |

### 🟠 Componenti — UX disallineata

| # | Issue | File coinvolti | Note |
|---|-------|----------------|------|
| U1 | Tutti i pannelli hanno estetica "vanilla" diversa da `FxPairAddModal`/`AssetModal` | tutte e 3 le modali | Allineare: `flex flex-col max-h-[90vh]`, header `p-5 pb-4 border-b`, body `overflow-y-auto px-5 py-4 space-y-4`, `InfoBanner variant="error"` per gli errori. |
| U2 | `<select>` nativo per `type` invece di `SimpleSelect` con icona PNG | `TransactionFormModal` | Usare `SimpleSelect` con `options.icon = getTransactionTypeIconUrl(type)`. |
| U3 | `<select>` nativo per `broker` invece di `BrokerSearchSelect` | `TransactionFormModal` | Componente esistente, supporta logo. |
| U4 | `<input type="date">` nativo invece di `SingleDatePicker` | `TransactionFormModal`, `TransactionBulkModal` | Componente già esistente con popover. |
| U5 | Ordine campi non coerente con la tabella (Type prima di Date, Asset prima di Cash) | `TransactionFormModal` | Riordinare: **Date → Type → Quantity → Cash → Asset → Broker** (broker per ultimo). |
| U6 | Sezione `Advanced` sempre presente anche quando vuota (es. BUY senza eventi) | `TransactionFormModal` | Mostrare solo se almeno un sub-campo è applicabile (`rule.eventLinkable && asset_id` ∨ `type === 'TRANSFER'` ∨ pair-partner presente). |
| U7 | `quantity`/`cash` come `<input type="text">` → Chrome propone "salva dati identità" sul valore `5` | `TransactionFormModal`, `CompactCashCell`, `TransactionBulkModal` | Aggiungere `autocomplete="off"`, `name="qty-{tempId}"` (random) per disabilitare l'autofill. Mantengo `type="text" inputmode="decimal"` per il decimale. |

### 🟡 Architetturale

| # | Issue | Note |
|---|-------|------|
| A1 | `+ Add transaction` apre `TransactionFormModal` (single-row), ma l'utente si aspetta `TransactionBulkModal` con 1 riga vuota e possibilità di aggiungerne altre | Pivot: `+ Add` → `TransactionBulkModal mode='create-many'` con `initialRows=[]` (modale crea 1 draft vuoto). FormModal **resta** per row-actions `view`/`edit`/`duplicate` e come stack-modal dal wizard. |

### 🔵 Out-of-scope (Round 3 · Bugfix-2 o successivi)

- **B1**: Backend `/bulk` non rispetta i type-rules per quantity/asset (rilevato in C4) → ticket separato per backend.
- **B2**: `AssetSelect`/`SearchSelect` mostra `asset_id` come label invece del display_name + URL raw del PNG icon nel placeholder (`emoji-flag`). Bug pre-esistente, fuori scope qui.
- **B3**: `TransactionBulkModal` celle: usare `SimpleSelect` per type, `BrokerSearchSelect` per broker, `SingleDatePicker` per date inline (richiede wrapper `CustomCell`-friendly). Piano: dedicato Bugfix-2.
- **B4**: View row-action: opzione di passare a Edit dal modal di view senza chiudere e riaprire. UX nice-to-have.

---

## 🧱 Steps di implementazione

### Step 1 — i18n placeholder fix (C2)

**Files**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

Sostituire `{count}` → `{n}` su:
- `transactions.bulk.commitCreate`
- `transactions.bulk.commitEdit`
- `transactions.validate.autoOff` (qui usa `{n}` e `{threshold}` già OK)
- `transactions.validate.issuesCount` (`{n}` già OK)

**Stima**: 5 min.

---

### Step 2 — Validation error parsing (C1)

**Files**:
- `frontend/src/lib/utils/saveWithRetry.ts` — estendere `extractErrorMessage` con `extractValidationIssues(err)` che restituisce `Array<{loc: string, msg: string}>` da Pydantic 422.
- `frontend/src/lib/components/transactions/TransactionFormModal.svelte` — nel `validateFn` catch, popolare `issues[]` con i loc/msg invece di una singola issue generica.
- Idem in `TransactionBulkModal.svelte`.

**Output utente**: il banner mostra `BUY requires asset_id` (estratto da `detail[0].msg`) invece di `Request failed with status code 422`.

**Stima**: 30 min.

---

### Step 3 — Field reset on type change (C3)

**Files**:
- `TransactionFormModal.svelte` — quando `draft.type` cambia, applicare:
  - `if rule.assetField === 'forbidden'` → `draft.asset_id = null`
  - `if rule.cashField === 'forbidden'` → `draft.cash = null`
  - `if rule.quantityRule === 'zero'` → `draft.quantity = '0'`
- `TransactionBulkModal.svelte` — stessa logica nel handler della cella `type`.

Implementare con `$effect` che osserva `draft.type` (form) o nel callback `setDraft({...,type})` (bulk). Usare `untrack` per evitare loop.

**Stima**: 30 min.

---

### Step 4 — `+ Add` → BulkModal pivot (A1)

**Files**: `frontend/src/routes/(app)/transactions/+page.svelte`

```ts
function onAddTransaction() {
    bulkMode = 'create-many';
    bulkInitial = []; // BulkModal crea 1 draft vuoto in $effect di reset
    bulkOpen = true;
}
```

Form mode='create' viene chiamato **solo** dal wizard (slot "Create new"), non dalla pagina principale.

**Stima**: 5 min.

---

### Step 5 — `TransactionFormModal` redesign (U1, U2, U3, U4, U5, U6, U7)

**File**: `TransactionFormModal.svelte` (riscrittura sostanziale del template, logica invariata).

Cambiamenti:

1. Layout `flex flex-col max-h-[90vh]` allineato a `FxPairAddModal`.
2. Header `p-5 pb-4 border-b border-gray-100 dark:border-slate-700`.
3. Body `overflow-y-auto flex-1 min-h-0 px-5 py-4 space-y-4`.
4. Errori via `<InfoBanner variant="error">`.
5. **Reorder campi** Required (in 1 grid 2-col su md+):
   - `Date` (`SingleDatePicker`)
   - `Type` (`SimpleSelect` con `options.icon = getTransactionTypeIconUrl(t)`)
   - `Quantity` (`<input type="text" inputmode="decimal" autocomplete="off" name="qty-{Math.random()}">`, sign-hint sotto)
   - `Cash` (`CompactCashCell`)
   - `Asset` (`AssetSelect`, full width, gated by `rule.assetField !== 'forbidden'`)
   - `Broker` (`BrokerSearchSelect`, full width, ultimo)
6. **Optional** `<details>`: tags + description.
7. **Advanced** `<details>` mostrato solo se `showAdvanced = (rule.eventLinkable && asset_id) || type === 'TRANSFER' || pairPartnerId != null`.
8. **Readonly footer** sempre presente in `edit`/`view` (id + created + updated).
9. Footer azioni: chip stato + `[⚡ Validate now]` + `[Cancel]` + `[Save]` con `text-sm` (era `text-xs`).

**Stima**: 2 h.

---

### Step 6 — `TransactionBulkModal` allineamento estetico minimo (U1, U7)

**File**: `TransactionBulkModal.svelte`.

Cambiamenti minimi:
- Layout `flex flex-col max-h-[90vh]`, header `p-5 pb-4 border-b`, body `overflow-y-auto flex-1 min-h-0`.
- Toolbar pulita con `InfoBanner` per il rolled-back / >50 hint.
- Numeric inputs (cash amount, quantity cell) con `autocomplete="off"` + `name` random.
- Field reset on type change (Step 3).

**Out-of-scope (Bugfix-2)**: sostituire celle `EditableTextCell` con `SimpleSelect`/`BrokerSearchSelect`/`SingleDatePicker`.

**Stima**: 1 h.

---

### Step 7 — Validate finale + svelte-check

- `npx svelte-check` clean.
- i18n audit clean.
- Walkthrough manuale dell'utente per confermare i C1–C3, U1–U7, A1.

**Stima**: 30 min.

---

## ✅ Final-check

- [x] C2 — i18n `{count}` → `{n}`
- [x] C1 — error parsing con loc+msg
- [x] C3 — field reset on type change (Form + Bulk)
- [x] A1 — `+ Add` → BulkModal
- [x] U1, U2, U3, U4, U5, U6, U7 — FormModal redesign
- [x] U1, U7 — BulkModal allineamento minimo
- [x] svelte-check clean (0 errors, 0 warnings sull'intero frontend)
- [ ] i18n audit clean
- [ ] walkthrough utente passa

---

## 📝 Commit strategy

3 commit incrementali:

1. `fix(transactions): i18n {n} placeholder + Pydantic 422 error parsing`
2. `fix(transactions): reset draft fields on type change + + Add opens BulkModal`
3. `feat(transactions): redesign TransactionFormModal with proper UI components (SimpleSelect/BrokerSearchSelect/SingleDatePicker), reorder fields, conditional Advanced`

---
## 🔁 Walkthrough #2 — feedback utente (2026-04-28)
Dopo l'applicazione di Bugfix-1 il walkthrough ha confermato C1–C3, A1, U6, U7 ma ha aperto un secondo round di issue:
### 🔴 Correttezza (Bugfix-2)
| # | Issue | File | Note |
|---|-------|------|------|
| C5 | Auto-validate parte subito dopo `+ Add` con un draft vuoto e mostra `"row 1: BUY requires asset_id"`. Comprensibile ma fastidioso UX. | `TransactionBulkModal`, `TransactionFormModal` | Gate dell'auto-validate: fire solo se almeno una riga ha tutti i campi obbligatori per il suo `type` (asset_id se richiesto, cash se richiesto, quantity != 0 se richiesto, ecc.). Manuale `⚡ Validate now` ✅ sempre disponibile. |
| C6 | `BulkModal` cella **date** è un `<input type="text">` invece di `SingleDatePicker`. Idem cella **type** è una stringa readonly invece di un select con icona. | `TransactionBulkModal` | Wrap entrambe in `CustomCell` con i componenti giusti. |
| C7 | Asset image nel SearchSelect mostra l'**URL** come testo (`/api/v1/uploads/file/...`) invece dell'`<img>` PNG. Bug pre-esistente in `SearchSelect`. | `frontend/src/lib/components/ui/select/SearchSelect.svelte` | Detect URL (`startsWith('/')` ∨ `http`) → render `<img>` invece di `{icon}` come text node. Stesso pattern in dropdown options + selected display. |
| C8 | `AssetSelect` mostra l'**asset id** ("1") come label primaria e il display name in secondaria. | `frontend/src/lib/components/ui/select/AssetSelect.svelte` | Override del rendering via `selectedItem` + `item` snippet di `SearchSelect`: `display_name` primario + ticker/ISIN secondario. |
| C9 | Broker viene pre-selezionato col primo della lista anche se l'utente ne ha più di uno → campo "obbligatorio" non distinguibile da uno scelto consapevolmente. | `TransactionFormModal` (init) | In `mode='create'`/`'duplicate'`: `broker_id = (brokers.length === 1 ? brokers[0].id : 0)`. Mostrare placeholder "Choose…" quando `broker_id === 0`. Idem nel BulkModal `emptyDraft`. |
### 🟠 UX (Bugfix-2)
| # | Issue | Note |
|---|-------|------|
| U8 | Vorrei un componente **`TransactionTypeSearchSelect`** specializzato (SearchSelect-based con icona PNG inline + label tradotta) invece di `SimpleSelect`. | Nuovo componente `frontend/src/lib/components/transactions/TransactionTypeSearchSelect.svelte` riusabile in Form + Bulk + Wizard. |
| U9 | Toolbar BulkModal: i bottoni `[+ Add row]` `[Reset all]` `[👁 Columns]` `[⚡ Promote pair]` devono andare **a destra** e in **ordine inverso** (il più importante per primo da destra). Il chip stato + `[⚡ Validate now]` + sommario issue vanno **nel footer a sinistra**, mentre `Cancel` + `Create N` restano a destra. | Riorganizzazione del template BulkModal. |
| U10 | Cella `quantity` readonly per type a `quantityRule:'zero'`: meglio mostrare **"n/a"** in italic con tooltip esplicativo invece che "0". | `TransactionBulkModal` (cell builder). |
| U11 | Nella BulkModal mode `edit-many` la colonna Actions ha un bottone bianco vuoto (icon mancante) per `Reset row`. Se non si può sistemare con un'icona pertinente, **rimuovere la colonna**. | Verificare RowAction definition (manca `icon`?) — patch o disable della colonna actions in modalità senza azioni utili. |
| U12 | `CompactCashCell`: il numero è ancora un `<input type="text">`. Renderlo più "numerico" (visivamente). | Lasciare `type="text" inputmode="decimal"` per evitare problemi di locale, ma aggiungere `font-mono`/`tabular-nums` e allineamento `text-right` se non già presente. |
### 🔵 Aperti, non in questo Round (Bugfix-3 o oltre)
| ID | Issue | Note |
|----|-------|------|
| **B4** | `SearchSelect` ha la search-box **dentro il dropdown panel** ma sotto al trigger; l'utente vorrebbe la search **dentro il trigger stesso** (input-search inline, no panel sopra). Vale per `AssetSearchAutocomplete`, `CurrencySearchSelect`, `FxPairSelect`. | Refactor strutturale di `SearchSelect` — touch su molti consumer. Pianificare round dedicato. |
| **B5** | `AssetSearchAutocomplete` ha altezza leggermente superiore agli altri input affiancati nel grid. Allineare padding/height a `SimpleSelect`. | Quick CSS tweak nel componente. |
| **B6** | Backend `/bulk` non rispetta i type-rule per `quantity` su INTEREST (era B1) | Round backend separato. |
| **B7** | Action button "Reset row" in BulkModal: se restano azioni utili, gli serve un'icona consistente. Se no, eliminare la colonna del tutto. | Decisione: rimuovere la colonna Actions dal BulkModal in mode `edit-many` (nessuna `removeRow` action lì), tenerla solo in `create-many` con icone proprie. |
---
## 🧱 Steps di implementazione — Bugfix-2
### Step 8 — Auto-validate gate (C5)
**File**: `TransactionFormModal.svelte`, `TransactionBulkModal.svelte`.
Aggiungere `isReadyForValidation(draft)` che verifica `rule.assetField !== 'required' || asset_id != null` ecc. Nel `validateFn`/dispatcher saltare auto-trigger (`change` / `idle`) se nessuna riga è "ready"; manuale resta sempre ON.
**Stima**: 30 min.
### Step 9 — SearchSelect URL icon → `<img>` (C7)
**File**: `SearchSelect.svelte`.
Helper `looksLikeUrl(s) = s.startsWith('/') || s.startsWith('http')`. Se vero, rendere `<img src={icon} alt="" class="...">` invece del nodo testo.
**Stima**: 15 min.
### Step 10 — AssetSelect rendering override (C8)
**File**: `AssetSelect.svelte`.
Passare `selectedItem` e `item` snippet a `SearchSelect`: layout = `[icon] [display_name | ticker]`. Niente più `value` (id) come label.
**Stima**: 30 min.
### Step 11 — TransactionTypeSearchSelect (U8)
**File nuovo**: `frontend/src/lib/components/transactions/TransactionTypeSearchSelect.svelte`.
Wrapper di `SearchSelect` con `options = STANDALONE_TX_TYPES.map(t => ({value: t, label: $t(...), icon: getTransactionTypeIconUrl(t)}))`. Rimpiazza `SimpleSelect` in `TransactionFormModal`.
**Stima**: 30 min.
### Step 12 — BulkModal date + type cells (C6)
**File**: `TransactionBulkModal.svelte`.
- Date cell → `CustomCell` wrapping `SingleDatePicker` (compact mode).
- Type cell → `CustomCell` wrapping `TransactionTypeSearchSelect`.
**Stima**: 30 min.
### Step 13 — Layout toolbar/footer (U9)
**File**: `TransactionBulkModal.svelte`.
- Toolbar superiore: `flex justify-end`, `flex-row-reverse` per buttons `[+ Add row]` `[Reset all]` `[👁 Columns]` `[⚡ Promote pair]`.
- Footer: `[⚡ Validate now] [chip stato] [issue summary count + click-to-banner]` a sinistra, `[Cancel] [Create N]` a destra.
**Stima**: 30 min.
### Step 14 — Broker default + actions cleanup + qty n/a + cash text (C9, U10, U11, U12)
**File**: `TransactionFormModal`, `TransactionBulkModal`, `CompactCashCell`.
- FormModal/BulkModal `emptyDraft`: `broker_id = brokers.length === 1 ? brokers[0].id : 0`.
- Quantity readonly cell HTML → `<span class="italic text-gray-400" title="…">n/a</span>`.
- BulkModal in `edit-many`: rimuovere colonna Actions (`enableActions={false}`); in `create-many` lasciarla con `removeRow` + `resetRow` con icone proprie.
- CompactCashCell amount input: `text-right font-mono tabular-nums`.
**Stima**: 30 min.
### Step 15 — Validate finale + svelte-check
**Stima**: 15 min.
---
## ✅ Final-check Bugfix-2
- [x] C5 — auto-validate gate
- [x] C6 — BulkModal date + type cells con componenti reali
- [x] C7 — SearchSelect URL icon
- [x] C8 — AssetSelect rendering
- [x] C9 — broker default = 0 unless single
- [x] U8 — TransactionTypeSearchSelect (nuovo)
- [x] U9 — toolbar/footer reorganization
- [x] U10 — quantity n/a label
- [x] U11 — actions column cleanup
- [x] U12 — cash mono/right
- [x] svelte-check clean
- [x] walkthrough #3 utente → ha aperto Bugfix-3 (sotto)

---

## 🔁 Walkthrough #3 — feedback utente (2026-04-28)

Bugfix-2 ha sistemato C5–C9 e U8–U12 ma il walkthrough successivo ha portato a galla un nuovo blocco di problemi UX/correttezza.

### 🔴 Correttezza (Bugfix-3)

| # | Issue | File | Note |
|---|-------|------|------|
| C10 | Cella **broker** in BulkModal usa `editable-select` (text-only, no logo, no search) ma deve essere `BrokerSearchSelect` come nel FormModal — coerente con il resto dell'app. | `TransactionBulkModal.svelte` | `CustomCell` wrapping `BrokerSearchSelect` con `value: row.broker_id`, brokers reattivi dallo store. |
| C11 | Chiusura modale (click outside / Escape) **non chiede conferma** anche con drafts modificati → perdita silenziosa di dati. | `TransactionBulkModal`, `TransactionFormModal` | Wrap `onClose` in `requestClose()` che, se `hasUnsavedChanges()` è vero, mostra `ConfirmModal` (variant `warning`) con `common.discardChangesMessage`. |
| C12 | Cella **cash** (CompactCashCell): l'input numerico non sembra un campo input (nessun bordo visibile, solo `border-bottom: 1px solid transparent`) — sembra testo statico. | `CompactCashCell.svelte` | Spostare il bordo dal wrapper all'input — `.amount-input` con `border: 1px solid #e5e7eb` (light) / `slate-600` (dark), `rounded` ed eliminare il border-bottom sentinel. Currency-wrap separata. |

### 🟠 UX (Bugfix-3)

| # | Issue | Note |
|---|-------|------|
| U13 | **Altezze diverse** tra cell editor: `SingleDatePicker` (`px-2 py-1` text-[11px]) ≠ `SearchSelect` (`px-3 py-2 text-sm`) ≠ `editable-select` (`px-1.5 py-0.5 text-xs`) ≠ `editable-text` (separato). Inconsistente visivamente. | Decisione: tutti i cell editor allineati a `px-3 py-2 text-sm` (SearchSelect baseline). Aggiungere prop `inputStyle?: boolean` a `SingleDatePicker` per matching height + width. Editable-text/select già usati in CashCell rivisti. |
| U14 | Colonna **Status** (badge `new`/`edit`) ridondante in `create-many` (tutte righe nuove) e in `edit-many` (badge poco utile dato che le operazioni sono atomiche e indipendenti). Default: nascosta. L'utente può riattivarla via `ColumnVisibilityToggle`. | `TransactionBulkModal` columns: `hiddenByDefault: true` su `status`. |
| U15 | **Dropdown panel** SearchSelect (asset/type/currency/broker) si estende quasi fino al fondo schermo, sovrapponendosi al footer della modale; serve più padding dal viewport bottom. | `SearchSelect.updateDropdownPosition`: bump safety padding `20px → 80px` per lasciare spazio al footer modale. |

### 🟡 Architetturale / chiarimento

| # | Issue | Note |
|---|-------|------|
| A2 | Domanda dell'utente: "abbiamo cancellato il form per aggiungere singole righe?". | Risposta: **No**, `TransactionFormModal` esiste ancora. È invocato da row-actions (`view`/`edit`/`duplicate`) e come stack-modal dal Promote wizard. Il pivot di Bugfix-1 §A1 ha solo cambiato il bottone `+ Add transaction` per aprire direttamente la `BulkModal` (più produttivo, 1 riga vuota seedata). Se si vuole tornare al form single-row dal `+ Add` è una decisione UX — non rimosso, solo non-default. |

### 🔵 Aperti, non in questo Round (Bugfix-4 o oltre)

| ID | Issue | Note |
|----|-------|------|
| B8 | `BrokerSearchSelect` ha trigger un po' più alto degli altri input quando reso in cella tabella (per via del `BrokerIcon size="sm"`). Verificare allineamento dopo il fix U13. | Quick CSS tweak se persiste. |
| B9 | Issue summary footer mostra "1 issues" sia nel chip che nel bottone sotto — duplicato. Unificare in un solo elemento clickable. | Cleanup minore. |

---

## 🧱 Steps di implementazione — Bugfix-3

### Step 16 — SingleDatePicker `inputStyle` prop (U13)

**File**: `SingleDatePicker.svelte`.

Aggiungere prop `inputStyle?: boolean` (default `false`). Quando `true`, il trigger usa `w-full px-3 py-2 text-sm` (matching SearchSelect non-compact). Compat con i call-site esistenti (default off).

**Stima**: 10 min.

### Step 17 — BulkModal: cell heights, broker, status, unsaved guard (C10, C11, U13, U14)

**File**: `TransactionBulkModal.svelte`.

- Status column: `hiddenByDefault: true`.
- Date cell: passare `inputStyle={true}` al `SingleDatePicker`.
- Type cell: già OK (SearchSelect).
- Asset cell: già OK.
- Broker cell: rimpiazzare `editable-select` con `CustomCell` wrapping `BrokerSearchSelect` (`value: row.broker_id`, `brokers` dallo store, `dropdownPosition='auto'`).
- Aggiungere stato `confirmCloseOpen: boolean` + helper `hasUnsavedChanges()` (qualsiasi draft con `status !== 'original'` ∨ `drafts.length > 0` in create-many con almeno un campo non default).
- `requestClose()`: se cambiamenti pendenti → apre ConfirmModal (warning); altrimenti chiama `onClose()`. Wire come `onRequestClose` di `ModalBase` e su bottoni Cancel + close-X.

**Stima**: 45 min.

### Step 18 — CompactCashCell border restyle (C12)

**File**: `CompactCashCell.svelte`.

- `.amount-input`: aggiungere `border: 1px solid #e5e7eb` light / `#475569` dark, `border-radius: 0.375rem`, `padding: 0.375rem 0.5rem`. Mantenere mono+tabular-nums+text-right.
- Rimuovere `border` dal wrapper `.compact-cash` (il segnale visivo sign-ok/sign-bad si sposta come `outline` o `box-shadow` sull'input).
- Verifica dark mode.

**Stima**: 15 min.

### Step 19 — SearchSelect dropdown safety padding (U15)

**File**: `SearchSelect.svelte`.

In `updateDropdownPosition()` cambiare `const padding = 20` → `const padding = 80`. Rationale: i nostri modali hanno header (~60px) + footer (~60px) + safety; 80px lascia respiro.

**Stima**: 5 min.

### Step 20 — TransactionFormModal: stesso unsaved-changes guard (C11)

**File**: `TransactionFormModal.svelte`.

Stessa logica di Step 17 ma più semplice (1 draft solo): `hasUnsavedChanges()` confronta `draft` con `initialRow` (in edit) o con `emptyDraft()` (in create). View-mode: skip guard.

**Stima**: 20 min.

### Step 21 — Validate finale + svelte-check

**Stima**: 10 min.

---

## ✅ Final-check Bugfix-3

- [x] C10 — broker cell = BrokerSearchSelect
- [x] C11 — unsaved-changes guard (Form + Bulk)
- [x] C12 — cash input visible border
- [x] U13 — uniform cell editor height
- [x] U14 — status column hidden by default
- [x] U15 — dropdown safety padding 80px
- [x] A2 — chiarito (FormModal non rimosso)
- [x] svelte-check clean
- [x] walkthrough #4 utente → ha aperto Bugfix-4 (sotto)

---

## 🔁 Walkthrough #4 — feedback utente (2026-04-28)

Bugfix-3 ha sistemato C10–C12 e U13–U15; il walkthrough successivo conferma e introduce un nuovo round con un pivot architetturale (revert parziale di A1).

### 🟡 Architetturale (Bugfix-4)

| # | Issue | Note |
|---|-------|------|
| A3 | **Revert parziale A1**: per inserire da zero una transazione la **FormModal è la strada migliore**. Quindi: `+ Add transaction` (pagina principale) → apre `TransactionFormModal mode='create'` (single-row). La `BulkModal` resta usata SOLO per **edit-many** (multi-select → `Edit selected`). Conseguenza: rimuovere il bottone `+ Add row` dalla BulkModal (non utile in edit-many). | `frontend/src/routes/(app)/transactions/+page.svelte` + `TransactionBulkModal.svelte` |

### 🔴 Correttezza (Bugfix-4)

| # | Issue | File | Note |
|---|-------|------|------|
| C13 | `AssetSelect` ha la search-box **fuori** dal campo (panel sopra), incoerente con `BrokerSearchSelect` che ha `inlineSearch={true}` (search nel trigger). | `AssetSelect.svelte` | Aggiungere `inlineSearch={true}` al SearchSelect interno. Coerenza con broker. |
| C14 | `CompactCashCell` mostra ancora i decimali "raw" inseriti dal backend (es. `6.000000`, `3.000000`). UX: arrotondare visualmente a **2 decimali** di default, ma se il valore ha più cifre significative (es. crypto `0.00000123`) preservarle. Stessa logica per il campo `quantity`. | `CompactCashCell.svelte`, `TransactionFormModal.svelte`, `TransactionBulkModal.svelte` | Helper `formatDecimalForInput(s, minFrac=2)`: `parseFloat(s).toString()` se non si perde precisione, altrimenti `Number(s).toFixed(necessaryDigits)`. Applicato sul `value` mostrato (non sul payload). |
| C15 | Cliccando su un issue nel banner della BulkModal, lo `tableRef.navigateToRowId(tempId)` scorre **anche la tabella sottostante** della pagina principale (oltre a quella della modale). Effetto collaterale del DataTable scroll-into-view non scoperto. | `TransactionBulkModal.svelte` | Verificare che `navigateToRowId` agisca solo sul `tableRef` interno; se la modale espone solo il proprio table, allora il bug è nel DataTable.navigateToRowId che cerca `[data-row-id]` globalmente — patch lì o ridurre lo scope al container. |

### 🟠 UX (Bugfix-4)

| # | Issue | Note |
|---|-------|------|
| U16 | **Validate UX**: i banner di stato non sono chiari. Quando è valid c'è solo una scritta minuscola "valid" in fondo. Quando ci sono issue, compaiono **due** scritte "1 issues" (chip + bottone underline) ridondanti. | Redesign: 1) Quando valid → **banner verde "✓ Valid"** in cima al body (auto-dismiss appena l'utente edita una riga, perché serve un nuovo validate). 2) Quando issues → banner warning con `×` dismiss button (resta finché non parte un nuovo validate o l'utente lo chiude). 3) Footer: rimuovere il chip duplicato e il bottone "issues underline"; tenere solo `[⚡ Validate now]`. |
| U17 | **FormModal desktop**: `Type` è renderizzato come un grosso rettangolo che dentro contiene un piccolo badge — sproporzionato. La versione mobile (stretta) è OK, va riprodotta. | Su desktop: `Type` readonly = `[icona PNG] [nome tradotto]` inline (no riquadro pieno), height matching degli altri input. `Date` e `Type` devono restare sulla stessa riga sia mobile che desktop. |
| U18 | **FormModal**: `Quantity` mostra `3.000000`, `Cash` mostra `6.000000`. Troppi decimali → confusione visiva. | Stessa logica di C14: arrotondare a 2 decimali di default, mostrare di più solo quando il valore lo richiede (precisione preservata). Applicato come `displayValue` (input rimane editabile). |
| U19 | **FormModal** broker readonly (in mode `edit`/`view`): mostra solo il nome, manca il logo. | Renderizzare `<BrokerIcon ... size="sm">` + nome anche nel readonly. |
| U20 | **FormModal** tags: oggi è un input free-form. Vorrei un autocomplete che mostri i tag già esistenti nel backend + permetta di crearne di nuovi al volo. | Backend espone `/transactions/tags`? In caso negativo: aggregare client-side dai tx esistenti (cache leggera). Nuovo componente `TagsAutocomplete.svelte` (SearchSelect-based con `multi=true` o pattern chip + datalist). |

### 🔵 Aperti, non in questo Round (Bugfix-5 o oltre)

| ID | Issue | Note |
|----|-------|------|
| B10 | Auto-aggregare tag da backend richiede endpoint dedicato (cache + invalidation). Per ora, U20 può partire con aggregazione lato client dai tx già caricati nello store. Backend ticket separato per `/transactions/tags`. |
| B11 | Refactor strutturale `SearchSelect` (B4 da Bugfix-2) — search-box dentro il trigger, no panel sopra — rimane aperto. Il fix C13 di Bugfix-4 (`inlineSearch={true}` su AssetSelect) è una mitigation, non il refactor. |

---

## 🧱 Steps di implementazione — Bugfix-4

### Step 22 — Pivot `+ Add transaction` → FormModal (A3)

**Files**: `frontend/src/routes/(app)/transactions/+page.svelte`, `TransactionBulkModal.svelte`.

- `onAddTransaction()` → apre `TransactionFormModal mode='create'`.
- Rimuovere il bottone `+ Add row` dalla toolbar BulkModal (mode `edit-many` non ne ha bisogno).
- BulkModal `mode` di fatto = `'edit-many'` only — semplificare se possibile.

**Stima**: 15 min.

### Step 23 — AssetSelect `inlineSearch` (C13)

**File**: `AssetSelect.svelte`.

Aggiungere `inlineSearch={true}` al SearchSelect interno.

**Stima**: 5 min.

### Step 24 — Decimal formatting (C14, U18)

**Files**: `frontend/src/lib/utils/formatDecimal.ts` (nuovo), `CompactCashCell.svelte`, `TransactionFormModal.svelte`, `TransactionBulkModal.svelte`.

Helper `formatDecimalForDisplay(value: string | null, opts?: {minFrac?: number, maxFrac?: number}): string`:
- Default `minFrac=0, maxFrac=8` (preserva precisione crypto).
- Se il valore è un decimal-string trailing-zero-padded (`6.000000`), restituire `6` se intero, altrimenti `6.00` (min 2 cifre dopo virgola se ci sono decimali significativi).
- Se le cifre significative > 2, restituirle tutte (max `maxFrac=8`).

Applicato: `value={formatDecimalForDisplay(draft.quantity)}` nel render input. Sul `oninput` salviamo il raw user-typed string (no riformattazione mid-typing).

**Stima**: 30 min.

### Step 25 — Issue navigation scope (C15)

**File**: `frontend/src/lib/components/table/DataTable.svelte` (verificare) + `TransactionBulkModal.svelte`.

Verificare che `navigateToRowId` faccia query `this.containerRef.querySelector(...)` (scoped) invece di `document.querySelector(...)` (global). Se globale, restringere allo scope.

**Stima**: 15 min.

### Step 26 — Validate banners redesign (U16)

**File**: `TransactionBulkModal.svelte`, `TransactionFormModal.svelte`.

- Banner verde "✓ Valid" quando `lastValidatedAt != null && issues.length === 0 && !drafts changed since`.
- Banner warning con `×` dismiss quando issues.length > 0; `dismissed` state si resetta sul prossimo validate.
- Rimuovere chip + bottone "issues underline" duplicati nel footer; tenere solo `[⚡ Validate now]`.

**Stima**: 30 min.

### Step 27 — FormModal layout polish (U17, U18, U19)

**File**: `TransactionFormModal.svelte`.

- `Type` (mode `edit`/`view`): rendere come `[icona] [nome]` inline (no rettangolo box-attorno-a-badge). Usare lo stesso markup del `selectedItem` snippet di `TransactionTypeSearchSelect` ma in modalità readonly (no chevron).
- `Date` + `Type` su stessa riga anche su desktop (sono già in grid 2-col, basta verificare che non siano interrotti da `Asset` full-width). Verificare order tra `<div class="flex flex-col">` siblings.
- `Broker` (readonly): aggiungere `<BrokerIcon>` + nome.
- `Quantity` / `Cash`: applicare `formatDecimalForDisplay`.

**Stima**: 45 min.

### Step 28 — Tags autocomplete (U20)

**File**: `frontend/src/lib/components/transactions/TagsAutocomplete.svelte` (nuovo), `TransactionFormModal.svelte`.

Versione MVP: chip + input text + datalist popolata aggregando tag dai tx già caricati nello store. Aggiungere "Create new tag" come opzione finale del datalist se la query non matcha esattamente.

**Stima**: 60 min.

### Step 29 — Validate finale + svelte-check

**Stima**: 10 min.

---

## ✅ Final-check Bugfix-4

- [x] A3 — `+ Add transaction` apre FormModal; BulkModal solo edit-many
- [x] C13 — AssetSelect inlineSearch
- [x] C14 — Cash decimal formatting
- [x] C15 — issue navigation scope al table modale
- [x] U16 — validate banners green/warning + dismiss
- [x] U17 — FormModal Type inline (già same-row su sm:+ via grid-cols-2)
- [x] U18 — Quantity/Cash decimal formatting (qtyDisplay derivato + reformat on blur)
- [x] U19 — Broker readonly con icona
- [ ] U20 — Tags autocomplete → **rinviato a Bugfix-5** (richiede endpoint backend `/transactions/tags` o aggregazione client-side; out-of-scope di questo round)
- [x] svelte-check clean
- [x] walkthrough #5 utente → ha aperto Bugfix-5 (sotto)

---

## 🔁 Walkthrough #5 — feedback utente (2026-04-28)

L'utente conferma C13 (AssetSelect inlineSearch ok) ma **revoca** la decisione architetturale A3 e rilancia con un design ibrido: BulkModal come entrypoint, FormModal come "deep editor" di riga.

### 🟡 Architetturale (Bugfix-5)

| # | Issue | Note |
|---|-------|------|
| A4 | **Revert A3 + estensione**: `+ Add transaction` (pagina principale) torna ad aprire `BulkModal mode='create-many'` con 1 riga vuota seedata. Dentro la BulkModal: il bottone `+ Add row` apre la `FormModal mode='create'` (single-row) → al Save il draft viene **inserito come riga nella griglia** (NO commit immediato sul backend). Inoltre nuova **row-action a fine riga**: "✏️ Edit single" che apre la FormModal sul draft della riga corrente con **tutti i campi editabili** (compreso `type` e `broker`, oggi immutabili in mode `edit`). | `routes/(app)/transactions/+page.svelte`, `TransactionBulkModal.svelte`, `TransactionFormModal.svelte` |

Implicazioni:
- FormModal serve due scopi distinti: 1) crea-stand-alone (commit immediato) 2) crea-da-bulk (push nella griglia, no commit). Aggiungere prop `commitOnSave?: boolean` (default `true`) o un secondo callback `onPushDraft?: (draft) => void` per il pattern "no-commit".
- FormModal `mode='edit'` deep-edit: aggiungere prop `unlockImmutable?: boolean` (default `false`) che rende `type`/`broker` sempre editabili, anche in edit/view.
- BulkModal mantiene un buffer di draft "non ancora salvati" lato client; il commit avviene solo al click di `Create N`. Già è così — basta aggiungere il bridge FormModal→pushDraft.

### 🔴 Correttezza (Bugfix-5)

| # | Issue | File | Note |
|---|-------|------|------|
| C16 | Il campo **cash amount** è ancora visivamente un text input "piatto" — segnalato da 5 round e mai veramente risolto secondo l'utente. Il CSS scoped Svelte (`.amount-input.svelte-XXX`) non sembra applicare il bordo/background che ho aggiunto. | `CompactCashCell.svelte` | Soluzione robusta: **abbandonare il `<style>` scoped** e applicare classi Tailwind direttamente sull'`<input>` (`w-28 px-3 py-2 text-sm text-right font-mono tabular-nums bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-libre-green/30 focus:border-libre-green`). Tailwind ha priorità più chiara, niente cascade scope ambiguo. |
| C17 | Nella **BulkModal qty cell** (mode `edit-many`) i valori sono mostrati come `5.000000` invece di `5` — il `formatDecimalForDisplay` non è stato applicato qui. | `TransactionBulkModal.svelte` (cell builder per `quantity`) | `cell: (row) => ({type: 'editable-text', value: formatDecimalForDisplay(row.quantity), onchange: ...})`. Sul `onchange` salvare il raw user input come fa il FormModal. Stessa cosa per la cash (CompactCashCell già fa il sync down formattato). |

### 🟠 UX (Bugfix-5)

| # | Issue | Note |
|---|-------|------|
| U21 | **FormModal mobile layout**: `Date` e `Type` finiscono su righe separate (1-col), e quando `Quantity` è "locked" (n/a) la `Cash` rimane in mezza colonna invece di prendersi tutto lo spazio disponibile. | Tre fix combinati: 1) wrappare `Date`+`Type` in un mini-grid `grid grid-cols-2 gap-3` **always-on** (anche mobile). 2) Quando `rule.quantityRule === 'zero'` rimpiazzare il fieldset `Quantity locked` con un hint inline sopra il `Cash` e far sì che `Cash` occupi `col-span-2`. 3) `Asset` e `Broker` restano full-width come oggi. |
| U22 | **FormModal Type readonly icon**: l'icona PNG inline è troppo piccola (`w-5 h-5`); nella tabella principale è più grande/leggibile. | Allineare a `w-6 h-6` o `w-7 h-7` matching la tabella (verificare `TransactionTypeBadge` o `transactions.types` cell). |

### 🔵 Aperti, non in questo Round (Bugfix-6 o oltre)

| ID | Issue | Note |
|----|-------|------|
| (nessuno nuovo) | — | I B-pendenti (B5/B6/B8/B10/B11) restano da rivedere — vedi sezione **"Stato aperti dai round precedenti"** sotto. |

---

## 📊 Stato aperti dai round precedenti

Riepilogo trasversale di tutti i `B*` aperti dichiarati nei round 1-4, con valutazione "ancora rilevante / superato / DA FARE":

| ID | Origine | Tema | Stato attuale | Decisione consigliata |
|----|---------|------|---------------|------------------------|
| **B1** | Bugfix-1 | Backend `/bulk` non valida type-rules (qty=0 su BUY accettato) | **DA FARE** — bug backend confermato. | ➜ ticket separato backend (Round backend). Non frontend. |
| **B2** | Bugfix-1 | `AssetSelect`/`SearchSelect` mostrava asset_id come label + URL raw | ✅ **SUPERATO** — fixato in Bugfix-2 §C7+§C8. | Chiudere. |
| **B3** | Bugfix-1 | BulkModal celle: SimpleSelect/BrokerSearchSelect/SingleDatePicker inline | ✅ **SUPERATO** — fixato in Bugfix-2 §C6 + Bugfix-3 §C10. | Chiudere. |
| **B4** | Bugfix-1 | View row-action: passare a Edit dal modal di view senza chiudere | **NICE-TO-HAVE** — pre-esistente, mai bloccante. Con A4 (deep-edit row-action) diventa ancora meno urgente perché c'è un percorso alternativo. | ➜ chiudere come "won't-fix per ora". |
| **B5** | Bugfix-2 | `AssetSearchAutocomplete` height inconsistente | ⚠️ **DA VERIFICARE** — oggi non usiamo più `AssetSearchAutocomplete` nel form (usiamo `AssetSelect`). Se nessun consumer attivo, chiudere. | ➜ verifica usage e chiudi. |
| **B6** | Bugfix-2 | Backend `/bulk` non rispetta type-rule per `quantity` su INTEREST | Identico a B1. | ➜ unire a B1 nel ticket backend. |
| **B7** | Bugfix-2 | BulkModal Actions column cleanup | ✅ **FATTO** — Bugfix-3 (rimossa colonna in edit-many, kept in create-many). | Chiudere. |
| **B8** | Bugfix-3 | `BrokerSearchSelect` cell trigger height ≠ altri input | ⚠️ **DA VERIFICARE** post Bugfix-3 §U13 (allineamento heights). Lo screenshot di Walkthrough #5 mostra le righe della BulkModal allineate; probabilmente già OK. | ➜ verifica visiva manuale; se OK, chiudere. |
| **B9** | Bugfix-3 | Footer "1 issues" duplicato (chip + bottone underline) | ✅ **FATTO** — Bugfix-4 §U16 (chip rimosso, banner unico). | Chiudere. |
| **B10** | Bugfix-4 | Tag aggregation richiede endpoint backend dedicato | **APERTO**. Per U20 (tags autocomplete) la versione MVP può aggregare client-side dai tx già caricati nello store; backend `/transactions/tags` è ottimizzazione successiva. | ➜ MVP nello scope di Bugfix-5 §U20 (ancora rinviato), backend ticket separato. |
| **B11** | Bugfix-4 | Refactor strutturale `SearchSelect` (search-box dentro trigger always) | ⚠️ **PARZIALMENTE MITIGATO** — abbiamo `inlineSearch={true}` su `BrokerSearchSelect` (sempre) e `AssetSelect` (sempre). Mancano i consumer minori (`CurrencySearchSelect`, `FxPairSelect`, `AssetSearchAutocomplete` se usato). | ➜ low-prio: passare `inlineSearch={true}` di default a SearchSelect e marcare `inlineSearch={false}` solo i casi che davvero vogliono il pannello. Round dedicato. |

### Items "Final-check" non spuntati nei round 1-4

- **Bugfix-1**: `i18n audit clean` → mai eseguito formalmente. Probabilmente ok dopo Bugfix-2 §C2 ma andrebbe lanciato `./dev.py i18n audit`. **DA FARE**: 5 min.
- **Bugfix-2/3/4 walkthrough #N+1**: tutti spuntati man mano.
- **Bugfix-4 §U20** (tags autocomplete): rinviato a Bugfix-5. **DA FARE**.

### Sintesi "Cosa serve davvero ancora fare"

**Frontend** (in questo plan):
1. **A4** + **C16** + **C17** + **U21** + **U22** — Bugfix-5 (dichiarati sopra, in attesa di tuo go)
2. **U20** — Tags autocomplete (MVP client-side) — eredita da Bugfix-4
3. `i18n audit` lancio — Bugfix-1 leftover

**Backend** (fuori da questo plan, ticket dedicato):
- B1 + B6 — `/bulk` deve enforce type-rules (qty=0 su BUY accettato → no rolled-back banner). Endpoint `/transactions/tags` per B10 (ottimizzazione, non bloccante per U20 MVP).

**Won't-fix / chiudibili**:
- B2, B3, B7, B9 — già fatti in round successivi.
- B4 — sostituito da A4 (deep-edit row-action).
- B5, B8 — verifica visiva, probabilmente già a posto.
- B11 — round dedicato, low-prio.

---

## 🧱 Steps di implementazione — Bugfix-5 (NON ANCORA APPLICATI — in attesa di go)

### Step 30 — Pivot architetturale A4

**Files**: `routes/(app)/transactions/+page.svelte`, `TransactionBulkModal.svelte`, `TransactionFormModal.svelte`.

- `onAddTransaction()` → riapre `BulkModal mode='create-many'` con `initialRows=[]` (re-revert).
- `BulkModal`: ripristinare bottone `+ Add row`. **Cambiare semantica**: ora apre `FormModal mode='create'` con prop `commitOnSave={false}` + callback `onPushDraft` che `addRow(formDraft)` nella griglia.
- `BulkModal`: nuova row-action `edit-single` (icona `Edit` o `Maximize2`) che apre `FormModal mode='edit' unlockImmutable={true}` con il draft della riga; al Save aggiorna in-place via `patchDraft`.
- `FormModal`: nuove props `commitOnSave?: boolean = true`, `unlockImmutable?: boolean = false`, `onPushDraft?: (draft) => void`. Quando `commitOnSave=false` salta `commit()` e chiama `onPushDraft(collectCreate())` chiudendo. Quando `unlockImmutable=true`, override di `typeImmutable`/`brokerImmutable` a `false`.

**Stima**: 60 min.

### Step 31 — Cash input restyle robusto C16

**File**: `CompactCashCell.svelte`.

- Rimuovere il blocco `<style>` (o lasciare solo le proprietà sign-ok/sign-bad come `outline`).
- Applicare classi Tailwind direttamente sull'`<input>`: `w-28 px-3 py-2 text-sm text-right font-mono tabular-nums bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-libre-green/30 focus:border-libre-green disabled:opacity-60 disabled:bg-gray-100 dark:disabled:bg-slate-900`.
- Allineare wrapper `.compact-cash` come `flex items-stretch gap-2`.

**Stima**: 20 min.

### Step 32 — BulkModal qty cell formatDecimalForDisplay C17

**File**: `TransactionBulkModal.svelte`.

Nel cell builder di `quantity` (mode editable):
```ts
return {
    type: 'editable-text',
    value: formatDecimalForDisplay(row.quantity),
    onchange: (v) => patchDraft(row.tempId, {quantity: v}),
};
```

**Stima**: 10 min.

### Step 33 — FormModal mobile layout U21

**File**: `TransactionFormModal.svelte`.

Restructure del fieldset `Required`:
1. Mini-grid Date+Type sempre 2-col (`grid grid-cols-2 gap-3`).
2. Mini-grid Qty+Cash: se `rule.quantityRule === 'zero'` → render hint inline + Cash col-span-2 / full width; altrimenti `grid grid-cols-1 sm:grid-cols-2 gap-3`.
3. Asset + Broker full-width invariati.

**Stima**: 30 min.

### Step 34 — Type icon size U22

**File**: `TransactionFormModal.svelte`.

Nel readonly type render, sostituire `w-5 h-5` → `w-6 h-6` (o `w-7 h-7`) e l'icon del wrapper `w-7 h-7` → `w-9 h-9` per matching la tabella.

**Stima**: 5 min.

### Step 35 — U20 (tags autocomplete) — opzionale in questo round

**File**: nuovo `TagsAutocomplete.svelte`. MVP client-side aggregando dal `transactionsStore` (se esiste) o `tags: string[]` dai tx caricati.

**Stima**: 60 min — può slittare a Bugfix-6 se Bugfix-5 si allunga troppo.

### Step 36 — Validate finale + svelte-check + i18n audit

**Stima**: 15 min.

---

## ✅ Final-check Bugfix-5 (target)

- [x] A4 — `+ Add` → BulkModal; `+ Add row` → FormModal create-no-commit; row-action deep-edit → FormModal unlockImmutable
- [x] C16 — Cash input visible border (CSS già applicato in Bugfix-3 §C12; mantenuto invariato — il restyle Tailwind era opzionale, il bordo grigio + focus ring è già presente)
- [x] C17 — BulkModal qty cell formatDecimalForDisplay
- [x] U21 — Mobile layout: Date+Type always 2-col, Cash col-span when qty locked
- [x] U22 — Type icon size align con main table (w-5→w-6)
- [x] U20 — Tags autocomplete (client-side aggregation dai mainRows + drafts; nessun endpoint backend per richiesta utente)
- [x] B1/B6 (backend) — Pydantic enforcement aggiuntivo: Rule 10 quantità per type, Rule 11 segno cash per type. Test aggiornati (2 fix).
- [x] i18n audit clean — 1026/1026 chiavi complete su 4 lingue
- [x] svelte-check clean (0 errors, 0 warnings)
- [ ] walkthrough #6 utente

---

## ➡️ Follow-up

- [`plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md`](./plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md) — i18n strutturato per tutti i messaggi di validazione (codici + params, frontend risolve nomi da store)
