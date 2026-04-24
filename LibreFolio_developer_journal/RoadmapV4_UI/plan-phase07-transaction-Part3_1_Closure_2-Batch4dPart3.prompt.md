# Batch 4.d-part3 + I-bis residui (#5 + #19) — UX drift + CSV resilience + doc

> 📄 **Sub-plan di** [`plan-phase07-transaction-Part3_1_Closure_2.prompt.md`](./plan-phase07-transaction-Part3_1_Closure_2.prompt.md) §"Priorità Batch 4 post-retest" (#R6-6/#R6-7/#R6-8) + §"Coda I-bis pendente" (#5, #19).
> **Prerequisito**: Batch 4 già committato (4.a+4.b+4.c+4.d-part1+4.d-part2 + #R6-1..#R6-5).
> **Defer**: I-bis #24 (auto-refresh post-sync) → sub-plan dedicato (BE schema + FE chart merge, cross-cutting).

**Data**: 2026-04-24 — **Stima totale**: ~2h15.

---

## Scope

**Inclusi**

1. **#R6-6** — `BrokerImportFilesModal`: toast success su upload + delete (adotta pattern uniforme dell'app evoluta).
2. **#R6-7** — `BrokerImportFilesModal`: `ConfirmModal` destructive prima del bulk delete.
3. **#R6-8** — `BrokerSharingModal`: save success → `toast.success` + `onClose()`, rimuovere `successMessage` banner inline.
4. **I-bis #5** — `CsvEditor`: auto-detect separator + tolerant header (round-trip export→import).
5. **I-bis #19** — doc cross-link formale a Phase 8/9 per `Asset.active` semantic (0 codice).

**Escluso**

- I-bis #24 (auto-refresh mirato post-sync): richiede schema BE + rigen client + chart store refactor → sub-plan separato.

---

## Ordine di esecuzione (basso → medio rischio)

| # | Item | Effort | Rischio |
|---|------|-------:|:-------:|
| 1 | #19 doc cross-link | 5 min | nullo |
| 2 | #R6-8 BrokerSharing success→toast+close | 15 min | basso |
| 3 | #R6-7 BrokerImport ConfirmModal bulk delete | 20 min | basso |
| 4 | #R6-6 BrokerImport toasts upload/delete | 20 min | basso |
| 5 | I-bis #5 CsvEditor resilience | ~1h | medio |
| 6 | i18n audit + lint + front check | 15 min | — |

---

## 1. I-bis #19 — doc cross-link  (5 min)

**Dove**: parent plan `plan-phase07-transaction-Part3_1_Closure_2.prompt.md` §"I-bis #19".

**Azione**: sostituire lo stato ⏳ PENDING con ✅ DONE (doc only) — il contenuto tecnico è già consolidato in `phases/phase-08-scheduler.md`. Aggiungere 1 paragrafo di chiusura che chiarisce "nessun codice in Phase 7; regole operative in Phase 8/9".

**File**: solo il plan markdown. Zero codice.

---

## 2. #R6-8 — BrokerSharingModal success→toast+close  (15 min)

**Dove**: `frontend/src/lib/components/brokers/BrokerSharingModal.svelte` riga 302 `handleSave()`.

**Cambio**:

```diff
  if (result.status === 'success') {
-   successMessage = $_('brokers.sharing.saved');
    originalAccesses = JSON.parse(JSON.stringify(accesses));
    onChanged?.();
-   setTimeout(() => { successMessage = null; }, 3000);
+   toast.success($_('brokers.sharing.saved'));
+   onClose();
  } else {
    error = result.message;
  }
```

**Side-cleanup**: rimuovere `let successMessage` (riga 59), rimuovere il blocco `{#if successMessage}...InfoBanner variant="success"{/if}` (righe 463–467).

**Import**: aggiungere `import {toast} from '$lib/stores/toast';` (verificare path — probabilmente `$lib/stores/toast` o `$lib/utils/toast`).

**i18n**: zero nuove chiavi (`brokers.sharing.saved` già esiste).

**Test manuale**:
- [ ] Modifica share % → Save → toast success + modale chiude.
- [ ] Save con errore (backend offline) → modale resta aperta + banner rosso inline (invariato).

---

## 3. #R6-7 — BrokerImportFilesModal ConfirmModal bulk delete  (20 min)

**Dove**: `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` riga 215 `SelectionBar actions[delete].onClick`.

**Cambio**:

1. Nuovi state:
   ```ts
   let confirmBulkDeleteOpen = $state(false);
   let pendingBulkDeleteIds = $state<string[]>([]);
   ```

2. `SelectionBar.actions[delete].onClick` → apre il confirm invece di eseguire:
   ```ts
   onClick: () => {
     pendingBulkDeleteIds = [...selectedFileIds];
     confirmBulkDeleteOpen = true;
   }
   ```

3. Nuovo `<ConfirmModal>` destructive in fondo al markup (dopo il close-confirm):
   ```svelte
   <ConfirmModal
     open={confirmBulkDeleteOpen}
     danger
     title={$_('uploads.confirmBulkDelete.title')}
     message={$_('uploads.confirmBulkDelete.message', {values: {count: pendingBulkDeleteIds.length}})}
     confirmText={$_('common.delete')}
     onCancel={() => { confirmBulkDeleteOpen = false; pendingBulkDeleteIds = []; }}
     onConfirm={async () => {
       confirmBulkDeleteOpen = false;
       const ids = pendingBulkDeleteIds;
       pendingBulkDeleteIds = [];
       await handleDeleteMultiple(ids);
       filesTableRef?.clearSelection();
     }}
   />
   ```

4. Opzionale: se `FilesTable` chiama `onDeleteMultiple` di suo iniziativa (es. menu interno), vale la pena aprire la stessa ConfirmModal — controllare in lettura. Se già passa per `SelectionBar`, un solo gate basta.

**i18n NUOVE × 4**:
- `uploads.confirmBulkDelete.title`
- `uploads.confirmBulkDelete.message` (`"Delete {count} file(s)?"`)

---

## 4. #R6-6 — BrokerImportFilesModal toasts upload/delete  (20 min)

**Dove**: `BrokerImportFilesModal.svelte` — `handleUpload`, `handleDelete`, `handleDeleteMultiple`.

**Cambio**: flip `toast: false` → `toast: true` in `saveWithRetry` per gli errori + aggiungere toast success al termine di ogni operazione completata.

```ts
// handleUpload (after loop completes successfully)
showUploader = false;
pendingFiles = [];
await loadFiles();
uploading = false;
toast.success($_('uploads.uploadBatchSucceeded', {values: {count: uploadFiles.length}}));
```

```ts
// handleDelete (single success)
if (result.status === 'error') { error = result.message; return; }
await loadFiles();
toast.success($_('uploads.deleteSucceeded'));
```

```ts
// handleDeleteMultiple (bulk success/partial)
await loadFiles();
if (failedCount > 0) {
  error = failedCount === 1 ? lastMessage : $_('uploads.deleteFailedSome', {values: {count: failedCount}});
} else {
  toast.success($_('uploads.deleteBatchSucceeded', {values: {count: fileIds.length}}));
}
```

**Policy errori**: manteniamo l'inline banner rosso come primary feedback (utente può rileggerlo) **+** toast error per quick peripheral vision — quindi `toast: true` negli `saveWithRetry` (invece di `false` come ora). L'errore compare sia come toast che come banner — il banner è dismissible.

**Decisione**: stare con `toast: false` per coerenza di UX con la modale (l'errore è inline, persistente, leggibile) e usare toast **solo per success**. Più consistente.

Scelgo la policy **success-only toast**: errori inline banner (come oggi), success via toast.

**i18n NUOVE × 4**:
- `uploads.uploadBatchSucceeded` (`"{count} file(s) uploaded"`)
- `uploads.deleteSucceeded` (`"File deleted"`)
- `uploads.deleteBatchSucceeded` (`"{count} file(s) deleted"`)

---

## 5. I-bis #5 — CsvEditor resilience  (~1h)

**Dove**: `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte`.

**Obiettivo**: round-trip export→import del CSV generato da `/backup/asset/{id}/prices?format=csv` (oggi fallisce per "too many columns" e per separator `,` invece di `;`).

### 5a. Auto-detect separator

Aggiungere `$derived detectedSeparator` che analizza la prima riga non vuota:

```ts
function detectSeparator(rawLines: string[]): ';' | ',' {
  for (const line of rawLines) {
    const t = line.trim();
    if (!t) continue;
    const semis = (t.match(/;/g) ?? []).length;
    const commas = (t.match(/,/g) ?? []).length;
    // Heuristic: the separator with higher count wins;
    // fallback to ';' (current default) in case of tie.
    return commas > semis ? ',' : ';';
  }
  return ';';
}

let detectedSeparator = $derived(detectSeparator(lines));
```

**Caveat**: i numeri con decimale `,` possono gonfiare il count `,`. Mitigazione: contare solo occorrenze di separatori consecutivi o con spazio adiacente — oppure escludere match `\d,\d` (numerico interno). Approccio robusto: contare `,` / `;` in sequenze `X<sep>Y` dove il separatore è al bordo parola.

Implementazione pragmatica (buona per header):
```ts
function countSep(line: string, sep: ';' | ','): number {
  // conta solo separatori non preceduti/seguiti da cifra (esclude decimali "0,6")
  const re = new RegExp(`(?<=[^\\d]|^)\\${sep}(?=[^\\d]|$)|(?<=\\d)\\${sep}(?=\\D|$)|(?<=\\D)\\${sep}(?=\\d|$)`, 'g');
  return (line.match(re) ?? []).length;
}
```

Più semplice e sufficiente per il round-trip: usare la **riga header** (la prima non vuota). Se contiene `date` seguito da separator, quello è il separator:

```ts
function detectSeparator(rawLines: string[]): ';' | ',' {
  for (const line of rawLines) {
    const t = line.trim().toLowerCase();
    if (!t) continue;
    // Header line starts with "date"
    if (t.startsWith('date;')) return ';';
    if (t.startsWith('date,')) return ',';
    // Fallback: whichever is more frequent
    return t.includes(';') ? ';' : ',';
  }
  return ';';
}
```

Questo è **deterministico per CSV validi** (export sempre inizia con `date`) e robusto.

### 5b. Tolerant header matching

Attualmente `isHeaderLine` confronta stringhe letterali (`date;close` vs header corrente). Cambiare in **mappa per nome colonna**:

```ts
interface HeaderMap {
  valid: boolean;
  // index of 'date' column in the CSV header
  dateIdx: number;
  // map from CsvColumnDef.key → column index in CSV (or -1 if missing)
  colIndices: Record<string, number>;
  // missing required columns (including 'date')
  missingRequired: string[];
  // extra columns present in CSV but not in `columns` prop → ignored silently
  extraColumns: string[];
}

function parseHeaderLine(line: string, sep: ';' | ','): HeaderMap {
  const parts = line.split(sep).map((p) => p.trim().toLowerCase());
  const dateIdx = parts.indexOf('date');
  const colIndices: Record<string, number> = {};
  const missingRequired: string[] = [];
  const extraColumns: string[] = [];

  if (dateIdx < 0) missingRequired.push('date');

  for (const col of columns) {
    const idx = parts.indexOf(col.label.toLowerCase());
    colIndices[col.key] = idx;
    if (idx < 0 && col.required) missingRequired.push(col.label);
  }

  // Extra columns: anything in `parts` that isn't 'date' or a known column label
  const known = new Set(['date', ...columns.map((c) => c.label.toLowerCase())]);
  for (const p of parts) {
    if (p && !known.has(p)) extraColumns.push(p);
  }

  return {
    valid: missingRequired.length === 0,
    dateIdx,
    colIndices,
    missingRequired,
    extraColumns,
  };
}
```

### 5c. Row parsing adattato

Nel blocco `validations = $derived.by(...)`:
- Usare `detectedSeparator` invece di `;` hardcoded in `trimmed.split(';')`.
- Usare `headerMap.dateIdx` e `headerMap.colIndices` per accedere ai valori anziché position-based 0,1,2.
- **Rimuovere** il check `parts.length > totalCols` (ora le colonne extra sono ignorate).
- Se `headerMap.colIndices[col.key] === -1`: significa colonna opzionale mancante → `values[col.key] = null` (già gestito dal ramo `!rawVal`).

### 5d. Header error message

Nel caso `!headerValid`, mostrare le `missingRequired` nel tooltip:
```ts
error: $t('csvImport.headerMissingColumns', {
  values: {cols: headerMap.missingRequired.join(', ')}
})
```

### 5e. UI hint

Nel `<div class="status bar">` aggiungere un badge quando `detectedSeparator === ','`:
```svelte
{#if detectedSeparator === ','}
  <span class="text-amber-500 text-[10px]">• comma-separated</span>
{/if}
```

E nel `kbd` del separator hint, mostrare dinamicamente il detected:
```svelte
<kbd>{detectedSeparator}</kbd>
```

### i18n NUOVE × 4

- `csvImport.headerMissingColumns` (`"Missing required columns: {cols}"`)
- `csvImport.commaSeparated` (`"Comma-separated"`) — badge opzionale

### Test manuale

- [ ] Paste CSV con header `date;currency;close` → verde (immutato).
- [ ] Paste CSV con header `date;close;currency;open;high;low;volume` (ordine diverso, +4 colonne) → verde, colonne extra ignorate.
- [ ] Paste CSV con header `date,open,high,low,close,volume,currency,source_plugin_key,fetched_at` (export format) → verde, comma detected.
- [ ] Paste CSV con header `date;currency` (manca `close` required) → rosso, errore "Missing required columns: close".
- [ ] Paste CSV con decimali `,` e separator `;` — es. `2024-01-15;USD;145,50` → verde (parseNumber già gestisce).
- [ ] Import completo di un file esportato via `/backup/asset/{id}/prices?format=csv` → tutte le righe valide, import procede.

---

## 6. Validazione finale

```bash
./dev.py format
./dev.py lint
./dev.py front check
./dev.py i18n audit
```

---

## Commit strategy

1 commit unico:
```
feat(phase07): Batch 4.d-part3 + I-bis #5 + #19 — UX drift + CSV resilience

• #R6-6 BrokerImportFiles success toasts (upload/delete/bulk delete)
• #R6-7 BrokerImportFiles ConfirmModal destructive before bulk delete
• #R6-8 BrokerSharing success → toast + close (remove inline banner)
• I-bis #5 CsvEditor — separator auto-detect + tolerant header (round-trip)
• I-bis #19 doc cross-link to Phase 8/9 for Asset.active semantic

i18n — 6 new keys × 4 locales:
  uploads.uploadBatchSucceeded
  uploads.deleteSucceeded
  uploads.deleteBatchSucceeded
  uploads.confirmBulkDelete.title
  uploads.confirmBulkDelete.message
  csvImport.headerMissingColumns
```

**Deferred**: I-bis #24 (auto-refresh mirato post-sync) → dedicated sub-plan
with BE schema change + FE chart incremental merge.

