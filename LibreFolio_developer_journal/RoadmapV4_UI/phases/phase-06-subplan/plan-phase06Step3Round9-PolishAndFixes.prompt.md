# Plan: Phase 6 Step 3 — Round 9: Polish & Fixes Post F9

Data: 2026-03-31
Post Round 8. Integra i fix emersi dalla prima sessione di testing manuale dell'utente.

---

## §0 — Contesto

Round 8 ha completato F9 (ScheduledInvestmentEditor) e §5 (bulk delete multi-gap).
L'utente ha testato manualmente l'editor e riportato feedback:

| Feedback | Area | Status Round 9 |
|----------|------|----------------|
| DateRangePicker: errori IDE (warning + error) | UI | ✅ DONE |
| DataTableToolbar allineata a destra nel schedule editor | Layout | ✅ DONE |
| Tooltip colonne: uppercase/bold ereditato da `<th>` + testo inline senza newline | UX | ✅ DONE |
| Tooltip periodo: chiarire se end date inclusiva o esclusiva | UX/i18n | ✅ DONE |
| DatePicker: visibile, abbassato a 4xl (sufficiente) | UI | ✅ (user confirmed) |
| Merge funziona bene | Test OK | ✅ (user confirmed) |
| Split funziona bene | Test OK | ✅ (user confirmed) |
| Bulk delete: non gestiva sezioni separate, modale per ogni invio | Logic | ✅ DONE |
| Contiguità con espansione/riduzione funziona | Test OK | ✅ (user confirmed) |
| Delete singola con scelta data fa espandere correttamente | Test OK | ✅ (user confirmed) |
| SimpleSelect day_count: menu sotto il rettangolo azioni (z-index) | z-index | ✅ DONE |
| Late-rate: non si riesce a cliccare il grace period | Click handler | ✅ DONE |

---

## §1 — Fix DateRangePicker IDE Errors ✅ DONE

### Problema
1. Warning: `'y' should probably not be assigned to 'calLeftYear'` (×4)
2. Error: `v as Granularity` TypeScript cast non supportato nel template Svelte
3. Warning: `<div>` non permesso dentro `<button>` (HTML validity)

### Soluzione
1. Rinominato parametro `y` → `newYear` (setLeftYear, setRightYear) e `[y, m]` → `[sy, sm]`/`[ey, em]` (openCalendar)
2. Estratta funzione helper `handleGranularityChange(v: string)` con `as Granularity` nel `<script>`, usata nel template con `onchange={handleGranularityChange}`
3. Cambiati i `<div>` interni al `<button>` in `<span>` con `display: flex` via Tailwind classes

**File**: `DateRangePicker.svelte`

---

## §2 — Toolbar Bulk Allineata a Destra ✅ DONE

### Problema
La toolbar di selezione bulk (counter + merge/delete) appariva subito dopo il titolo a sinistra.

### Soluzione
Spostato il `flex-1` spacer PRIMA della toolbar bulk, così sia la toolbar che il bottone "Add Period" sono allineati a destra. La toolbar usa `border-r` (bordo destro) come separatore visivo dal bottone Add.

**File**: `ScheduledInvestmentEditor.svelte`

---

## §3 — Tooltip Colonne: No Uppercase/Bold + Line Breaks ✅ DONE

### Problema
I tooltip sulle intestazioni delle colonne ereditavano `text-transform: uppercase`, `font-weight: 600` e `letter-spacing: 0.025em` dal `<th>` parent, rendendo il testo aggressivo. In più il testo era su una sola riga.

### Soluzione
1. **Tooltip.svelte**: aggiunto `font-weight: 400`, `text-transform: none`, `letter-spacing: normal` in `.tooltip-fixed`
2. **Tooltip.svelte**: cambiato `white-space: normal` → `white-space: pre-line` per supportare `\n`
3. **i18n (4 lingue)**: riscritti i testi dei tooltip con `\n` per separare concetti su righe diverse
4. **periodHint**: aggiunto chiarimento "Both dates are inclusive (the end date is the last day of the period)"

**File**: `Tooltip.svelte`, `en.json`, `it.json`, `fr.json`, `es.json`

---

## §4 — Bulk Delete Multi-Gap ✅ DONE

### Problema
La bulk delete trattava la selezione come blocco contiguo, aprendo una sola modale per l'intero range. Con selezioni non contigue servivano N spartiacque separati.

### Soluzione
1. **`groupContiguousIndices()`**: raggruppa gli indici selezionati in blocchi contigui
2. **Classificazione HEAD/MIDDLE/TAIL**: HEAD e TAIL si auto-espandono senza modale, solo i MIDDLE richiedono boundary date
3. **BoundaryDateModal multi-gap**: nuovo prop `gaps: GapInfo[]` + `onconfirmMulti: (dates: string[]) => void`. La modale mostra N sezioni con DatePicker indipendenti, una per gap, con un solo bottone "Confirm Delete"
4. **Confirm unico**: tutti gli spartiacque vengono applicati atomicamente in `confirmBulkDeleteMulti()`

**File**: `BoundaryDateModal.svelte`, `ScheduledInvestmentEditor.svelte`

---

## §5 — SimpleSelect z-index vs Sticky Actions Column ✅ DONE

### Problema
Il dropdown del SimpleSelect per Day Count veniva disegnato sotto il rettangolo delle azioni riga (sticky column).

### Root cause
`.cell-editable-select-wrapper` aveva `position: relative; z-index: 1;` → creava un stacking context a z-index 1, inferiore al `z-index: 5` della colonna azioni sticky. Anche se il dropdown aveva `z-index: 9999`, era confinato nel stacking context del wrapper.

### Soluzione
Rimosso `z-index` dal `.cell-editable-select-wrapper` e dal suo `:global(.relative)` child. Senza stacking context nel wrapper, il dropdown fixed con z-index 9999 compete direttamente con il td-actions (z-index 5) nel contesto del `<tr>`, e vince.

**File**: `DataTable.svelte`

---

## §6 — Late-Rate Grace Period Non Cliccabile ✅ DONE

### Problema
L'utente non riusciva a cliccare il grace period della riga late interest.

### Root cause
Nella column def `period`, la prop `disabled` per il CellDateRange era:
```
disabled: disabled || readonly || (row.isLate && true)
```
Questo rendeva la CellDateRange SEMPRE disabilitata per la riga late, impedendo al popover del grace period di aprirsi.

### Soluzione
Rimosso `(row.isLate && true)` dalla condizione disabled. Il flag `isLateInterest` nel CellDateRange gestisce già la UI diversa (mostra popover grace anziché date range picker).

**File**: `ScheduledInvestmentEditor.svelte`

---

## Residui da Round 8 (CHIUSI)

| # | Item | Status | Note |
|---|------|--------|------|
| §7 | Identifier label dinamico per provider | ✅ DONE | Già implementato: `identifierLabel`, `identifierPlaceholder`, `isAutoGenerated` |
| F5 | Layout B Two-Panel + wrap | ❌ CANCELLED | Rimosso intenzionalmente dall'utente |

---

## Validation Checklist (Round 9)

- [x] DateRangePicker: zero errori IDE
- [x] Toolbar bulk: allineata a destra con Add Period
- [x] Tooltip: testo normale (no uppercase/bold), multi-riga con `\n`
- [x] Tooltip periodo: specifica "end date inclusive"
- [x] Bulk delete multi-gap: modale unica con N sezioni
- [x] SimpleSelect day_count: dropdown sopra la colonna azioni
- [x] Late interest: grace period cliccabile
- [x] BoundaryDateModal: backward compatible (single gap mode funziona)
- [x] i18n: testi tooltip aggiornati in EN/IT/FR/ES
- [x] §7: Identifier label dinamico — ✅ già implementato
- [x] F5: Layout B Two-Panel — ❌ CANCELLED (rimosso dall'utente)

