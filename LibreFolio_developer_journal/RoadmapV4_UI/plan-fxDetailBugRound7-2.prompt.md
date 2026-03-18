# Plan: Round 7.2 — Fix feedback utente post Round 7.1

**Dipendenze**: [`plan-fxDetailBugRound7-1.prompt.md`](plan-fxDetailBugRound7-1.prompt.md)

Refinements basati su feedback utente dopo Round 7.1.

**Stato**: 🔲 Da implementare

---

## Steps

### 1. FxDataEditorSection Cancel button — Dark mode leggibilità

**File**: `frontend/src/lib/components/fx/FxDataEditorSection.svelte`

**Problema**: Il bottone Cancel ha `bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300` — in dark mode il testo grigio chiaro su sfondo grigio è quasi illeggibile.

**Soluzione**: Cambiare il testo del Cancel in dark mode a un colore più contrastante:
- `dark:text-gray-300` → `dark:text-gray-100` (bianco quasi puro su sfondo scuro)

---

### 2. ColumnVisibilityToggle — Close on scroll (ancoraggio)

**File**: `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte`

**Problema**: Scrollando la pagina il dropdown resta fermo (è `position: fixed` e non segue il trigger).

**Soluzione**: Aggiungere `$effect` con listener `scroll` (capture) che chiude il dropdown quando la pagina scrolla:
```ts
$effect(() => {
    if (!open) return;
    const handleScroll = () => close();
    window.addEventListener('scroll', handleScroll, true);
    return () => window.removeEventListener('scroll', handleScroll, true);
});
```

---

### 3. DateRangePicker nel filtro DataTableColumnFilter — Larghezza piena

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

**Problema**: Con il fix `inline-block` / `inline-flex` per il caso `stacked`, il DateRangePicker usato nei filtri DataTable (con `stacked={true}`) ora si restringe al centro del pannello filtro invece di occupare tutta la larghezza.

**Soluzione**: Il fix `stacked` introdotto in Round 7.1 era troppo aggressivo. Invece di cambiare il comportamento per tutti i casi `stacked`, la soluzione giusta è:
- Riportare il container a `w-full` sempre
- Il trigger button: usare `w-full flex flex-col` per stacked (non `inline-flex`)
- Per il MeasurePanel dove serve il contenimento, il parent (`max-w-[300px]`) già lo vincola

---

### 4. DataEditor — Selezione righe con counter + deselect

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`

**Problema**: La selezione di righe funziona ma non compare mai il contatore di righe selezionate con il bottone per deselezionarle (come in FilesTable). `showToolbar={false}` nasconde la toolbar interna DataTable che contiene il counter.

**Soluzione**: Aggiungere nella toolbar del DataEditor, tra i contatori delle modifiche e l'occhio:
- Un callback `onSelectionChange` che aggiorna uno stato locale `selectedCount`
- Se `selectedCount > 0`: mostrare un badge cliccabile `"N selected ✕"` che chiama `clearSelection` via DataTable ref
- Aggiungere `export function clearSelection()` a DataTable se non esiste

---

### 5. DataEditor / DataTable — Scroll al click punto grafico (chart → table)

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`, `frontend/src/lib/components/fx/FxDataEditorSection.svelte`

**Problema**: Cliccando su un punto del grafico mentre si è in edit mode, la tabella non scrolla al corrispondente dato.

**Soluzione**: 
- FxDataEditorSection: esporre un metodo `scrollToDate(date: string)` che chiama `dataEditorRef.scrollToDate(date)` → che a sua volta chiama `dataTableRef.navigateToRowId(date)`
- DataEditor: il `scrollToDate` esistente deve usare `dataTableRef?.navigateToRowId(date)` (non `querySelector`)
- +page.svelte: nel handler click del grafico (se `showDataEditor` è true), chiamare `fxDataEditorRef.scrollToDate(clickedDate)`

---

### 6. ColumnVisibilityToggle — Allineamento posizione (troppo a sinistra)

**File**: `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte`

**Problema**: Il dropdown si apre traslato a sinistra (`left: 576px` con `rect.right - 220`) lasciando un gap vuoto a destra. La logica `rect.right - 220` è fissa e non si adatta al contenuto `w-max`.

**Soluzione**: Allineare il bordo destro del dropdown al bordo destro del trigger button:
```ts
const left = Math.max(8, rect.right - dropdownEl.offsetWidth);
```
Dato che il dropdown non esiste ancora quando calcoliamo, usare un approccio a 2 fasi:
1. Posizionare inizialmente allineato a destra del trigger
2. Dopo il render, misurare la larghezza effettiva e riposizionare se necessario
Oppure: usare `right` invece di `left`:
```ts
const right = window.innerWidth - rect.right;
dropdownStyle = `position:fixed; right:${right}px; ...`;
```

---

### 7. MeasurePanel header — Schema layout responsive (da confermare)

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

Layout del measure card header in 3 breakpoint:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WIDE (>640px) — tutto su una riga:
┌──────────────────────────────────────────────────────────────┐
│ ▾  📅 From: Jul 21 | To: Mar 23   -5.59%  · 245d  ██─── 👁 🗑│
└──────────────────────────────────────────────────────────────┘
 ↑chevron  ↑DateRangePicker(compact)  ↑stats   ↑style ↑col ↑del

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABLET (~400-640px) — 2 righe:
┌──────────────────────────────────────────────────────┐
│ ▾  📅 From: Jul 21 | To: Mar 23   -5.59%  · 245d    │
│    ██────────────────────────────────────── 👁 🗑     │
└──────────────────────────────────────────────────────┘
 riga1: chevron + date + stats (basis-full wraps)
 riga2: style (flex-1, grows to fill) + col + trash

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MOBILE (<400px) — 2 righe, date stacked:
┌──────────────────────────────────────┐
│ ▾  📅 From: Jul 21  -5.59%  · 245d  │
│       To: Mar 23                     │
│    ██──────────────────── 👁 🗑       │
└──────────────────────────────────────┘
 riga1: chevron + date(stacked) + stats
 riga2: style + col + trash
```

Il punto chiave è che la linea style (SignalStyleEditor) deve:
- **Wide**: avere width naturale (min-w-[80px]) e stare nella stessa riga
- **Tablet/mobile**: occupare tutto lo spazio disponibile nella riga 2 (`flex-1`)

L'attuale `basis-full sm:basis-auto` sulla riga 1 è corretto. Il problema è che il gruppo riga 2 ha `ml-auto` che lo tiene a destra — quando fa wrap deve diventare `w-full` per occupare tutta la riga.

**Soluzione**: Struttura container con `flex-wrap` e 2 gruppi:
- Gruppo 1 (dates): `flex items-center gap-2 flex-1 min-w-[200px]`
- Gruppo 2 (style+controls): `flex items-center gap-1.5 flex-1 min-w-[120px]`
  - SignalStyleEditor wrapper: `flex-1 min-w-[50px] max-w-[200px]`

---

### 8. Tooltip headerTooltip — Formato frazione LaTeX

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

**Problema**: La formula `$(1 + \Delta\%)^{365/d} - 1$` mostra `365/d` in riga, non come una vera frazione, e il testo è piccolo.

**Soluzione**: Usare `\frac{365}{d}` per una vera frazione LaTeX e aggiungere `\large` per ingrandire:
```
$\large (1 + \Delta\%)^{\frac{365}{d}} - 1$
```

---

### 9. MeasurePanel — Auto-delete misura su range invalido (fix #15)

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

**Problema**: `updateMeasureDates` controlla se ci sono dati generici nel range, ma la card della misura rimane visibile anche se `getMeasurement` torna `null` (perché le date esatte start/end non hanno un data point). La card mostra l'header ma senza tabella.

**Soluzione**: Dopo l'update delle date, verificare se `getMeasurement` torna `null` — se sì, rimuovere la misura:
```ts
m.params.startDate = s;
m.params.endDate = e;
measures = [...measures];
// Auto-delete if new range produces no valid measurement
const check = m.getMeasurement(chartData);
if (!check) {
    removeMeasure(id);
    return;
}
emitRendered();
```

---

### 10. DateRangePicker stacked — Ripristino width vincolata

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

**Problema**: Il DateRangePicker nella MeasurePanel (con `compact=true`, senza `stacked`) si allarga a tutta la larghezza della pagina. Il fix `inline-block` della Round 7.1 doveva risolvere solo il caso stacked nel filtro, ma ha rotto il caso non-stacked.

**Soluzione**: Combinato con step 3 — riportare sempre `w-full` sul container, ma aggiungere la classe `max-w-fit` solo quando `compact` è true (senza stacked), così il DateRangePicker non si allarga oltre il suo contenuto naturale in contesti come il MeasurePanel header.

Concretamente: il container `<div class="relative drp-trigger ...">` dovrebbe avere:
- Default: `w-full` (come prima)
- Se `compact && !stacked`: aggiungere anche `max-w-fit` per limitare la crescita

---

## Decisioni confermate

| # | Feedback | Decisione |
|---|----------|-----------|
| 1 | Bottone Cancel dark mode | `dark:text-gray-100` per testo più contrastante |
| 2 | Scroll chiude ColumnVisibilityToggle | Listener `scroll` capture come DateRangePicker/SingleDatePicker |
| 3 | DateRangePicker filtro troppo stretto | Riportare `w-full` sempre, il compact per MeasurePanel usa `max-w-fit` |
| 4 | Selezione righe senza counter | Aggiungere counter + deselect nella toolbar DataEditor |
| 5 | Click grafico → scroll tabella | Esporre `scrollToDate` su FxDataEditorSection, collegare al click chart |
| 6 | ColumnVisibility dropdown traslato | Usare `right` per allineare bordo destro |
| 7 | MeasurePanel layout responsive | 2 gruppi con `flex-wrap`, style `flex-1 min-w-[50px] max-w-[200px]` |
| 8 | Formula in vera frazione | `\frac{365}{d}` + `\large` in LaTeX |
| 9 | Auto-delete misura range invalido | Check `getMeasurement` dopo update, remove se null |
| 10 | DateRangePicker allarga troppo | `max-w-fit` su compact non-stacked |

---

## File modificati

| File | Modifiche |
|------|-----------|
| `FxDataEditorSection.svelte` | Cancel button dark text, esporre `scrollToDate` |
| `ColumnVisibilityToggle.svelte` | Close on scroll, posizione allineata a destra |
| `DateRangePicker.svelte` | Ripristino `w-full`, `max-w-fit` per compact |
| `DataEditor.svelte` | Counter selezione + deselect, `scrollToDate` via DataTable |
| `MeasurePanel.svelte` | Header 2 gruppi responsive, formula LaTeX, auto-delete |
| `DataTable.svelte` | `clearSelection` public API (se necessario) |
| `+page.svelte` (fx/[pair]) | Collegamento click chart → scrollToDate |

