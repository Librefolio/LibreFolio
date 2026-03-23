# Plan: Round 7.2.1 — Hotfix feedback utente post Round 7.2

**Dipendenze**: [`plan-fxDetailBugRound7-2.prompt.md`](plan-fxDetailBugRound7-2.prompt.md)

Hotfix basati su feedback utente dopo Round 7.2.

**Stato**: ✅ Completato

---

## Fix implementate

### 1. Cancel button — `dark:text-white`
`dark:text-gray-100` era ancora grigio. Cambiato a `dark:text-white`.

### 1b. Edit Rates header — amber più vivace in dark mode
`dark:bg-amber-900/10` → `dark:bg-amber-900/30` per mantenere il colore giallo come in light mode.

### 3. DateRangePicker popover — responsive mobile
Aggiunto `max-width: ${maxW}px` (dove `maxW = window.innerWidth - 16`) allo style del popover per evitare overflow su schermi piccoli.

### 4. Selection bar in DataEditor — counter + bulk delete esterno
- **DataTable.svelte**: esportata `clearSelection()` come API pubblica
- **DataEditor.svelte**: aggiunto `selectedIds` state via `onSelectionChange`, counter "N selected ×" + bottone 🗑 nel toolbar, tra i counters e l'occhio

### 5. Chart → Editor scroll via double-click
Cambiato da `click` a `dblclick` su `series.line` in PriceChartFull per navigare alla data nel DataEditor.

### 7. MeasurePanel layout — fix style width + collapsed + icon centering
- **Style sempre visibile**: rimosso `{#if isExpanded}` dal wrapper style, ora appare anche quando foldato
- **Style width**: `ml-auto w-[200px] min-w-[100px] shrink` → si espande a 200px, si comprime a 100px, allineato a destra
- **Narrow mode**: aggiunto `items-end` al stats+style flex-col per allineamento a destra
- **Icons centering**: aggiunto `items-center` al wrapper icons + `flex items-center justify-center` al trash

### 9. Auto-delete misura — fix ordine operazioni
Spostato `measures = [...measures]` (trigger reactivity) DOPO il check `getMeasurement`. Se il check fallisce, `removeMeasure` viene chiamato senza che la UI abbia mai mostrato lo stato intermedio.

---

## Issue note per round futuro

### A. Confirm modal su switch valuta in edit mode
Quando l'utente è in edit mode e clicca il bottone inverti valuta, dovrebbe apparire una confirm modal che avvisa che le modifiche non salvate andranno perse. Se confermato, uscire da edit mode.

### B. Mantenimento misure su switch valuta
Quando si inverte la valuta, le misure e i segnali dovrebbero essere mantenuti (stessi intervalli di tempo) e ricalcolati con i nuovi rate, non cancellati.

---

## File modificati

| File | Modifiche |
|------|-----------|
| `FxDataEditorSection.svelte` | Cancel button `dark:text-white` |
| `+page.svelte` (fx/[pair]) | Edit Rates header `dark:bg-amber-900/30` |
| `DateRangePicker.svelte` | Popover `max-width` responsive |
| `DataTable.svelte` | Esportata `clearSelection()` |
| `DataEditor.svelte` | `selectedIds` state, counter + bulk delete nel toolbar |
| `PriceChartFull.svelte` | `click` → `dblclick` su series.line |
| `MeasurePanel.svelte` | Style sempre visibile, `w-[200px]` + `ml-auto`, icons centered, auto-delete fix ordine |

