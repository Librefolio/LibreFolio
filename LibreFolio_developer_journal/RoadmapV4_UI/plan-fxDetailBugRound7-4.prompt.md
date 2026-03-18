# Plan: Round 7.4 — Fix feedback post Round 7.3

**Dipendenze**: [`plan-fxDetailBugRound7-3.prompt.md`](plan-fxDetailBugRound7-3.prompt.md)

Correzioni basate su feedback utente dopo Round 7.3. 3 step concreti + step rimandati dal Round 7.3.

**Stato**: ✅ Completato (18 Mar 2026)

---

## Stato implementazione

| Step | Descrizione | Stato | Note |
|------|-------------|-------|------|
| **1** | FxCard navigazione invertita (bug logico) | ✅ Completato | Fix: `${displayBase}-${displayQuote}` (era invertito) |
| **1b** | FxCard inversione persistente su back-navigation | ✅ Completato | `fxCardInversionStore.ts` module-level Map, card legge/scrive su toggle |
| **2** | DataTable highlight viola su navigateToRowId | ✅ Completato | `highlightedRowId` state, CSS `.highlighted` viola, reset su click/keydown |
| **3** | Chart long-press per mobile (1s) | ✅ Completato | Touch handlers con timer 800ms, threshold 10px, vibrate feedback |
| **4** | SelectionBar componente | ✅ Completato | Nuovo `SelectionBar.svelte` Tailwind standalone + fix DataTable `showToolbar` prop |
| **7** | MeasurePanel auto-delete DRP | ✅ Completato | Auto-filter misure invalide nel `$effect` su `chartData` |
| **11** | BrokerImportFilesModal | ✅ Completato | `ColumnVisibilityToggle` + `SelectionBar` nell'header, `onSelectionChange` in FilesTable |

---

## Steps

### 1. FxCard — Navigazione URL invertita (bug logico)

**File**: `frontend/src/lib/components/fx/FxCard.svelte`

**Problema**: `handleCardClick()` usa `${displayQuote}-${displayBase}` quando `inverted=true`. Ma:
- `displayBase = inverted ? quote : base` → quando inverted, = quote (es. "USD")
- `displayQuote = inverted ? base : quote` → quando inverted, = base (es. "EUR")
- `${displayQuote}-${displayBase}` = `${base}-${quote}` = "EUR-USD" = canonico → SBAGLIATO!

**Fix**: Invertire l'ordine → `${displayBase}-${displayQuote}` = "USD-EUR" (URL invertito, corretto).

```ts
function handleCardClick() {
    const target = inverted ? `${displayBase}-${displayQuote}` : slug;
    goto(`/fx/${target}`);
}
```

---

### 2. DataTable — Highlight viola riga su navigateToRowId

**File**: `frontend/src/lib/components/table/DataTable.svelte`

**Problema**: Quando il double-click sul chart attiva `scrollToDate → navigateToRowId`, la riga target viene scrollata in vista ma non è visivamente distinguibile dalle altre.

**Soluzione**: Aggiungere uno stato `highlightedRowId` che applica uno sfondo viola alla riga target. L'highlight si resetta al primo interaction dell'utente (click, keydown, scroll nella tabella).

#### Implementazione:

1. Aggiungere stato `highlightedRowId`:
   ```ts
   let highlightedRowId = $state<string | null>(null);
   ```

2. In `navigateToRowId`, settare l'highlight:
   ```ts
   highlightedRowId = rowId;
   ```

3. Nel template `<tr>`, aggiungere la classe `highlighted`:
   ```svelte
   <tr class="... {getRowId(row) === highlightedRowId ? 'highlighted' : ''} ...">
   ```

4. Aggiungere stile CSS per `.highlighted`:
   ```css
   tbody :global(tr.highlighted) {
       background: #f3e8ff !important; /* purple-100 */
   }
   :global(.dark) tbody :global(tr.highlighted) {
       background: #581c87 !important; /* purple-900 */
   }
   tbody :global(tr.highlighted) td {
       border-bottom-color: #e9d5ff; /* purple-200 */
   }
   :global(.dark) tbody :global(tr.highlighted) td {
       border-bottom-color: #7e22ce; /* purple-700 */
   }
   ```

5. Aggiungere listener per reset su interaction:
   - Sul contenitore `.datatable`, aggiungere `onclick` e `onkeydown` che resettano `highlightedRowId = null` (solo se non è già null, per evitare re-render inutili).
   - Lo scroll non serve — l'utente clicca/tipea per interagire.

---

### 3. PriceChartFull — Long-press per mobile (1 secondo)

**File**: `frontend/src/lib/components/charts/PriceChartFull.svelte`

**Problema**: Il double-click non funziona su mobile/touchscreen. Serve un'alternativa: tenere premuto per ~1 secondo.

**Soluzione**: Aggiungere handler `touchstart`/`touchmove`/`touchend` sul container del chart.

#### Implementazione:

1. Registrare `touchstart` sull'elemento Zr (via ECharts `getZr()`) o direttamente sul container div.

2. Logica:
   - `touchstart` (single finger): memorizza posizione e avvia timer 1s
   - `touchmove`: se il dito si sposta >10px, cancella il timer (era un pan/scroll)
   - `touchend`/`touchcancel`: cancella il timer
   - Quando il timer scatta (1s): calcola il punto del chart più vicino e chiama `handlePointClick`
   - Il browser vibra brevemente (`navigator.vibrate?.(50)`) come feedback tattile

3. Il long-press funziona sia in edit mode sia in measure mode (come il dblclick/click).

---

## Step rimandati (da Round 7.3)

### 4. SelectionBar componente
Componente riusabile per selezione righe con azioni batch. Troppo ampio per questo round.

### 7. MeasurePanel auto-delete DRP
Il DateRangePicker del MeasurePanel non cancella automaticamente le misure fuori range. Richiede debug manuale del flusso `onchange`.

### 11. BrokerImportFilesModal
Refactoring del modal di import file broker. Dipende da step 4.

---

## File modificati

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/fx/FxCard.svelte` | Fix ordine variabili in URL invertito + persistenza inversione via store |
| `frontend/src/lib/stores/fxCardInversionStore.ts` | **Nuovo** — Module-level Map per persistere lo stato inversione card |
| `frontend/src/lib/components/table/DataTable.svelte` | `highlightedRowId` state, CSS `.highlighted` viola, reset su interazione, fix `showToolbar` prop |
| `frontend/src/lib/components/charts/PriceChartFull.svelte` | Long-press touch handler (800ms) per mobile |
| `frontend/src/lib/components/charts/MeasurePanel.svelte` | Auto-delete misure fuori range nel `$effect` su `chartData` |
| `frontend/src/lib/components/table/SelectionBar.svelte` | **Nuovo** — Componente standalone selection counter + bulk actions (Tailwind) |
| `frontend/src/lib/components/table/index.ts` | Export `SelectionBar` |
| `frontend/src/lib/components/files/FilesTable.svelte` | Aggiunta prop `onSelectionChange` + metodo `clearSelection()` |
| `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` | `ColumnVisibilityToggle` + `SelectionBar` nell'header, `bind:this` su FilesTable |


