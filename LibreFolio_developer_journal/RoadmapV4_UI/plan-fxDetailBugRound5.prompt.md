# Plan: Fix Bug Round 5 — FX Detail Page & DataTable

**Dipendenze**: [`plan-fxDetailBugRound4.prompt.md`](plan-fxDetailBugRound4.prompt.md) (Rounds 1–4 completati)

Risoluzione di 10 issue: rotazione sync, allineamento filter bar, MeasurePanel sorting/filtri, z-index filter popover DataTable, stale indicator DataEditor, colori cella, oninput immediato, colonna nascosta di default, paginazione smart, data nuova riga.

---

## Steps

### 1. ✅ Fix rotazione pulsante Sync

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

- Import cambiato da `RotateCcw` → `RotateCw`
- Template cambiato `<RotateCcw` → `<RotateCw`
- **Motivo**: `animate-spin` ruota in senso orario, `RotateCcw` (antiorario) causava conflitto visivo

### 2. ✅ Allineamento filter bar a sinistra (F2)

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

- Container filter bar: `items-center` → `items-start` per layout `tablet` e `wide`
- Inner filters block: `items-center` → `items-start` per layout non-mobile
- Mantenuto `items-center` solo per `mobile` (centrato su schermi piccoli)

### 3. ✅ MeasurePanel: fix sorting segnale + filtri numeri (S4)

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

- Colonna `signal`: `sortable: true` → `sortable: false` (bandiere e cerchi colorati non hanno un ordine naturale)
- Colonne numeriche (`valueStart`, `valueEnd`, `deltaAbs`, `deltaPct`, `annualizedPct`): `filterable: false` → `filterable: true`
- L'icona 👁 (column visibility) e il 🗑 (trash) erano già funzionanti nel toolbar DataTable — nessuna modifica necessaria

### 4. ✅ Fix z-index filter popover DataTable (S8)

**File**: `frontend/src/lib/components/table/DataTableColumnFilter.svelte`, `DataTable.svelte`

- Aggiunta prop `anchorElement?: HTMLElement | null` a `DataTableColumnFilter`
- Quando `anchorElement` presente: posizionamento `position: fixed` con coordinate calcolate da `getBoundingClientRect()`
- z-index alzato a `9999` per evitare conflitti con qualsiasi container
- Listener `scroll` su `.table-wrapper` → chiude il popover al scroll
- Listener `resize` su `window` → ricalcola posizione
- Prevenzione overflow destro: `left` clamped a `window.innerWidth - popW - 8`
- `DataTable.svelte`: `filterBtnRefs` state per tracciare i bottoni filtro, passato come `anchorElement` al componente

### 5. ✅ Proprietà `hiddenByDefault` per colonne DataTable

**File**: `frontend/src/lib/components/table/types.ts`, `DataTable.svelte`

- Aggiunta `hiddenByDefault?: boolean` a `ColumnDef<T>`
- `defaultColumnVisibility` derivato ora usa `!c.hiddenByDefault` invece di `true`
- Retrocompatibile: se non specificato, la colonna è visibile (comportamento precedente)

### 6. ✅ Colonna Status nascosta di default nel DataEditor

**File**: `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`

- Aggiunto `hiddenByDefault: true` alla colonna `'status'`
- L'utente può riattivarla dal menu column visibility 👁 nella toolbar DataTable

### 7. ✅ oninput immediato per celle editable-number (S5)

**File**: `frontend/src/lib/components/table/DataTable.svelte`

- Aggiunto handler `oninput` alla cella `editable-number` che chiama `cellContent.onchange(...)` immediatamente
- `onblur` mantenuto per finalizzazione
- **Risultato**: l'effetto estetico (sfondo riga per status 'edited') si applica subito appena l'utente digita

### 8. ✅ Stale days indicator nel DataEditor (S5)

**File**: `DataEditorTypes.ts`, `DataEditor.svelte`, `FxDataEditorSection.svelte`

- `DataRow`: aggiunto campo opzionale `staleDays?: number`
- `FxDataEditorSection.chartDataToRows()`: mappa `dp.backwardFillInfo?.daysBack ?? 0` → `staleDays`
- Colonna date: se `staleDays > 0`, mostra `⚠️ Xd` accanto alla data con colore amber
- `rowBgClass`: aggiunto caso `row-stale` per righe con `staleDays > 0` e status `original`
- CSS: `row-stale` con sfondo giallo `rgba(245, 158, 11, 0.06)` (light) / `0.08` (dark)
- Larghezza colonna date aumentata da `160` → `180` per accomodare indicatore stale

### 9. ✅ Paginazione smart: page size e auto-hide (S5)

**File**: `DataEditor.svelte`, `DataTable.svelte`

- `DataEditor`: `defaultPageSize` cambiato da `50` → `10`, `pageSizeOptions` da `[25, 50, 100, 0]` → `[10, 25, 50, 100, 0]`
- `DataTable`: paginazione nascosta quando `totalItems ≤ Math.min(...pageSizeOptions.filter(x > 0))` (regola generale, vale per tutte le tabelle)

### 10. ✅ Data nuova riga: 1 giorno dopo l'ultimo (S5)

**File**: `DataEditor.svelte`

- `handleAddRow()`: calcola la data come `ultimo giorno nel dataset + 1`, invece di `new Date()` (oggi)
- Fallback a oggi se il dataset è vuoto
- Loop di skip: se la data calcolata esiste già, incrementa di 1 giorno fino a trovare una data libera

### 11. ✅ Colori sfondo celle allineati ai badge (S5)

**File**: `DataEditor.svelte`

- Opacità CSS aumentata: `0.05` → `0.08` (light), `0.1` → `0.12` (dark) per `row-edited`, `row-deleted`, `row-appended`
- Aggiunto `row-stale` (giallo) con opacità graduale

---

## Ordine di esecuzione effettivo

| Fase | Steps | Note |
|------|-------|------|
| Tipi condivisi | 5 (types.ts), 8a (DataEditorTypes.ts) | Prerequisiti per i componenti |
| DataTable core | 7, 4, 9 (DataTable auto-hide) | Retrocompatibili |
| Filter popover | 4 (DataTableColumnFilter.svelte) | Fixed positioning |
| DataEditor | 6, 8, 9, 10, 11 | Tutti i miglioramenti editor |
| FxDataEditorSection | 8b (staleDays passthrough) | Semplice mapping |
| MeasurePanel | 3 | Quick fix sorting/filtri |
| Pagina FX | 1, 2 | Quick fix finali |

---

## Decisioni confermate

| Domanda | Decisione |
|---------|-----------|
| Direzione spin sync? | `RotateCw` + `animate-spin` (entrambi orari → coerente) |
| Filter bar alignment? | `items-start` per tablet/wide, `items-center` solo mobile |
| Signal sorting in MeasurePanel? | Rimosso — bandiere e cerchi colorati non sortabili sensatamente |
| Filter popover z-index? | `position: fixed` con `getBoundingClientRect()`, z-index 9999, chiusura su scroll |
| Status column visibilità? | `hiddenByDefault: true` — riattivatibile dall'utente |
| oninput debounce? | No debounce — per DataEditor con poche righe visibili il costo è accettabile |
| Data nuova riga? | Ultimo giorno + 1, skip date esistenti, fallback a oggi se vuoto |
| Stale indicator? | ⚠️ emoji + contatore giorni, sfondo giallo gradient nella riga |

---

## Feature rimandati (prossima iterazione)

### Import CSV e Add Row — gestione date fuori selezione

Come deciso: rimandato. Nota per la prossima iterazione:
- **Date fuori range**: se l'utente aggiunge/importa date fuori dal range selezionato nel DateRangePicker, il grafico non le mostra → serve un feedback ("X righe fuori dal range attuale")
- **Righe new con data corretta**: ora la data è calcolata come ultimo giorno + 1, ma la data deve essere anche **editabile** dall'utente
- **Date duplicate**: non deve essere possibile scegliere date già presenti → validazione inline
- **Merge strategia**: se si importa una data già esistente, cosa succede? (attualmente: sovrascrittura con status 'edited')

### Aesthetics inline nel filter bar (F2 avanzato)

L'utente ha proposto di spostare la personalizzazione segnale/estetica inline nel filter bar sulla destra quando c'è spazio (wide mode). Implementazione proposta:
- Estrarre le opzioni principali di `ChartAestheticsSection` (colorByBaseline, areaFill, gridLines, staleGradient) come toggle compatti
- In wide mode: mostrarli come mini-toolbar a destra del rate/delta, prima dei pulsanti azione
- In tablet/mobile: mantenere il pannello foldable separato
- **Complessità**: media — richiede estrazione di un sotto-componente compatto

---

## File modificati

| File | Modifiche |
|------|-----------|
| `frontend/src/lib/components/table/types.ts` | `hiddenByDefault` aggiunto a `ColumnDef` |
| `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts` | `staleDays` aggiunto a `DataRow` |
| `frontend/src/lib/components/table/DataTable.svelte` | `defaultColumnVisibility` usa `hiddenByDefault`, `oninput` per editable-number, pagination auto-hide, `filterBtnRefs` |
| `frontend/src/lib/components/table/DataTableColumnFilter.svelte` | `anchorElement` prop, `position: fixed`, z-index 9999, scroll/resize listeners |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | Stale indicator, `hiddenByDefault` status, page sizes 10+, `handleAddRow` data fix, colori CSS |
| `frontend/src/lib/components/fx/FxDataEditorSection.svelte` | `staleDays` passthrough da `backwardFillInfo` |
| `frontend/src/lib/components/charts/MeasurePanel.svelte` | Signal `sortable: false`, numeri `filterable: true` |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | `RotateCw`, filter bar `items-start` |

