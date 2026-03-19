# Plan: Round 7.3 — Fix feedback post Round 7.2.1

**Dipendenze**: [`plan-fxDetailBugRound7-2.prompt.md`](plan-fxDetailBugRound7-2.prompt.md)

Correzioni basate su feedback utente dopo Round 7.2.1. 12 step concreti.
Step 8 usa approccio URL-based per l'inversione valuta (slug riflette la direzione, store seguono coppia canonica).
Step 12 ottimizzazione performance chart con `sampling: 'lttb'` e riduzione series segmentate.

**Stato**: ✅ Completato (18 Mar 2026)

---

## Stato implementazione

| Step | Descrizione | Stato | Note |
|------|-------------|-------|------|
| **1** | Cancel button + Edit Rates header dark mode | ✅ Completato | `dark:text-slate-900`, `dark:bg-amber-900/50` |
| **2** | DateRangePicker popover larghezza fissa | ✅ Completato | `singleColumn`, popover fixed width 560px |
| **3** | DateRangePicker trigger w-fit | ✅ Completato | prop `triggerFit` (default `true`), `w-fit` |
| **4** | SelectionBar componente | 🔲 Rimandato | Troppo ampio per questo round, step autonomo |
| **5** | Chart double-click fix | ✅ Completato | `getZr().on('dblclick')` |
| **6** | MeasurePanel style width | ✅ Completato | `flex-1 max-w-[400px]` wide, `w-full` narrow — condizionale `isNarrow` |
| **7** | MeasurePanel auto-delete DRP | 🔲 Da verificare | Richiede debug manuale del flusso DRP `onchange` |
| **8a** | `+page.ts` URL-based inversion | ✅ Completato | Riscritto con `canonicalSlug`, `inverted`, `urlBase`/`urlQuote` |
| **8b** | `+page.svelte` canonicalSlug + swap | ✅ Completato | `handleSwapDirection`, `ConfirmModal`, tutti store via `canonicalSlug` |
| **8c** | `FxCard.svelte` navigate inverted | ✅ Completato | `handleCardClick` naviga a URL invertito se `inverted` |
| **9** | Confirm modal + dirtyCount binding | ✅ Completato | `dirtyCount` esposto come `$bindable()`, `bind:dirtyCount={editorDirtyCount}` in page |
| **10** | Misure e segnali mantenuti su inversione valuta | ✅ Completato | Singola istanza MeasurePanel con classe condizionale `showMeasures ? "..." : "hidden"` |
| **11** | BrokerImportFilesModal | 🔲 Rimandato | Dipende da step 4 |
| **12A** | `sampling: 'lttb'` | ✅ Completato | Applicato a tutte le series line in 3 file |
| **12B** | Tooltip `staleLookup` Map O(1) | ✅ Completato | `PriceChartFull.svelte`, `LineChart.svelte` |
| **i18n** | Chiavi per swap confirm modal | ✅ Completato | `fxDetail.swapConfirmTitle`, `fxDetail.swapConfirmMessage`, `common.continue` |

---

## Steps

### 1. Cancel button + Edit Rates header — Dark mode colori ✅ COMPLETATO

**File**: `frontend/src/lib/components/fx/FxDataEditorSection.svelte`, `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

**Problema**: Il bottone Cancel ha `dark:bg-slate-600 dark:text-white` — lo sfondo chiaro in dark mode va bene, ma il testo bianco su sfondo chiaro non è leggibile. L'header "Edit Rates" con `dark:bg-amber-900/30` risulta ancora grigio anziché ambra.

**Soluzione**:
- **Cancel button**: cambiare a `dark:text-slate-900` (testo scuro su sfondo chiaro in dark mode).
- **Edit Rates header**: aumentare `dark:bg-amber-900/30` → `dark:bg-amber-900/50` per rendere il giallo più visibile in dark mode. Il testo `dark:text-amber-400` resta.

---

### 2. DateRangePicker popover — Larghezza fissa + traslazione + colonna su mobile ✅ COMPLETATO

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

**Problema**: Il popover usa `max-w-[600px]` + `max-width` JS ma si espande fino al bordo destro dello schermo. In modalità colonna (mobile) è troppo largo.

**Soluzione**: Riscrivere `updatePopoverPosition()` con logica a 3 step:
1. Calcolare larghezza fissa `popW = 560px` (due calendari affiancati).
2. Se `popW` entra nel viewport: posizionarlo con `left` e `width: 560px`.
3. Se non entra: traslarlo a sinistra (`left = 8px`).
4. Se ancora non entra (viewport < ~300px): layout a singola colonna, `width = min(280px, viewport-16px)`. Aggiungere prop o media-query per passare a `flex-col` anche sopra `sm`.
5. Il trigger (bottone From/To) deve restare `w-full` ma il popover **non** eredita la larghezza del trigger.

---

### 3. DateRangePicker trigger — Larghezza contenuto vs w-full ✅ COMPLETATO

**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

**Problema**: Il trigger si espande sempre a `w-full`. In MeasurePanel il parent `max-w-[300px]` lo vincola, ma fuori da lì si allunga a tutta pagina.

**Soluzione**: Cambiare il trigger da `w-full` a `w-fit` (si adatta al contenuto delle date) e mantenere `w-full` solo quando il parent lo richiede esplicitamente. In alternativa, aggiungere una prop `triggerFit?: boolean` che quando `true` usa `w-fit` sul container e sul bottone.

---

### 4. SelectionBar — Nuovo componente esterno (come ColumnVisibilityToggle) 🔲 RIMANDATO

**File**: nuovo `frontend/src/lib/components/table/SelectionBar.svelte`, `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`, `frontend/src/routes/(app)/files/+page.svelte`, `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte`

**Problema**: Il selection counter + bulk actions è inline nel DataEditor ma non è un componente riutilizzabile. In Files il selection counter è dentro la DataTableToolbar (che ora è stata semplificata). L'utente vuole un componente esterno posizionabile liberamente, come `ColumnVisibilityToggle`.

**Soluzione**: Creare `SelectionBar.svelte`:
- Props: `selectedCount: number`, `onClearSelection: () => void`, `bulkActions: BulkActionInfo[]`
- Template: `[N selected ×] [🗑] [📥]` — stessi stili della toolbar già implementata nel DataEditor
- Usabile ovunque:
  - **DataEditor**: nel toolbar, tra counters e 👁 (migrare l'inline attuale al nuovo componente)
  - **Files page (`+page.svelte`)**: accanto a `ColumnVisibilityToggle` nella riga dei tab
  - **BrokerImportFilesModal**: nell'header della modale, accanto al `ColumnVisibilityToggle` (che attualmente manca e va aggiunto anche quello)
- Rimuovere la `DataTableToolbar.svelte` interna (ora vuota) o mantenerla come shell per backward compat.

---

### 5. Chart double-click → table scroll (fix) ✅ COMPLETATO

**File**: `frontend/src/lib/components/charts/PriceChartFull.svelte`

**Problema**: Il handler `dblclick` su `series.line` (riga 196) viene registrato una sola volta alla init del chart (`if (!chartInstance)`). In quel momento `editMode=false` e la closure cattura quel valore. Inoltre ECharts non supporta `dblclick` su series allo stesso modo del `click`.

**Soluzione**: Usare il global handler su `getZr().on('dblclick')` (canvas-level double-click, non series-specific) per edit mode, nello stesso pattern del global click handler per measure mode (riga 204). Leggere le variabili `editMode` e `onPointClick` dalla closure aggiornata (visto che Svelte 5 le aggiorna reactivamente):

```ts
// Global dblclick handler for edit mode — catches double-clicks anywhere on the chart area
chartInstance.getZr().on('dblclick', (params: any) => {
    if (!editMode || !onPointClick || !chartInstance) return;
    const pointInPixel = [params.offsetX, params.offsetY];
    if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
        const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
        if (pointInGrid) {
            const dateIdx = Math.round(pointInGrid[0]);
            if (dateIdx >= 0 && dateIdx < displayData.length) {
                const point = displayData[dateIdx];
                handlePointClick(point.date, point.value);
            }
        }
    }
});
```

Rimuovere il vecchio handler `chartInstance.on('dblclick', 'series.line', ...)`.

---

### 6. MeasurePanel style width — Espansione in wide + contenimento in narrow ⚠️ PARZIALE

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`

**Problema**: La barra stile ha `w-[200px] min-w-[100px]` ma si comprime subito al minimo. In wide mode dovrebbe espandersi molto di più (fino a 400px). In narrow mode la barra si compenetra con l'occhio.

**Soluzione**:
- **Wide mode**: cambiare da `w-[200px] min-w-[100px]` a `flex-1 min-w-[100px] max-w-[400px]`. La barra cresce per riempire lo spazio disponibile, si comprime fino a 100px.
- **Narrow mode**: usare `w-full` (occupa tutta la riga sotto stats), con `max-w-[calc(100%-40px)]` o simile per evitare la compenetrazione con l'occhio. Oppure il wrapper stats+style in narrow diventa `flex-col items-stretch` e il wrapper icone ha larghezza fissa, quindi il `flex-1` del stats+style wrapper esclude naturalmente lo spazio delle icone.

**Stato implementazione**: Wide mode fatto (`flex-1 min-w-[100px] max-w-[400px]`). Narrow mode: manca `w-full` — attualmente usa stessa classe per entrambi i mode. Da completare: aggiungere condizionale `isNarrow ? 'w-full' : 'flex-1 min-w-[100px] max-w-[400px]'`.

---

### 7. MeasurePanel auto-delete — `updateMeasureDates` non viene chiamato dal DRP 🔲 DA VERIFICARE

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`, `frontend/src/lib/components/ui/DateRangePicker.svelte`

**Problema**: Il breakpoint dell'utente su `updateMeasureDates` non viene mai raggiunto quando si cambiano date dal DateRangePicker. Il DRP è passato con `start={String(measure.params.startDate)}` e `end={String(measure.params.endDate)}` (one-way binding) e `onchange` callback.

**Soluzione**: Verificare il flow `handleDayClick()` → `confirmRange()` → `onchange?.()` nel DRP. Il problema potrebbe essere:
- Il DRP aspetta 2 click (primo click = pending, secondo click = confirm) ma l'utente potrebbe fare un solo click
- Il DRP non emette `onchange` se start/end non cambiano effettivamente
- Il `confirmRange()` potrebbe non essere chiamato alla chiusura del calendario

Debug: aggiungere log in `confirmRange()` / `handleDayClick()` per verificare il flusso. Se il problema è che `onchange` non viene emesso, fixare la logica.

---

### 8. Inversione valuta — URL-based (slug nell'URL riflette la direzione)

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.ts`, `frontend/src/routes/(app)/fx/[pair]/+page.svelte`, `frontend/src/lib/components/fx/FxCard.svelte`

**Problema**: Lo stato `inverted` è locale (`$state(false)`) e si perde alla navigazione. Link e redirect non portano l'informazione sulla direzione. L'utente vuole che l'URL rifletta la coppia visualizzata (es. `/fx/USD-EUR` per la vista invertita).

**Soluzione — l'inversione vive nell'URL, gli store seguono la coppia canonica**:

#### 8a. `+page.ts` — Rimuovere redirect canonico, esporre `canonicalSlug` + `inverted`

```ts
export async function load({params}: {params: {pair: string}}) {
    const slug = params.pair;
    const parts = slug.split('-');
    if (parts.length !== 2 || parts[0].length !== 3 || parts[1].length !== 3) {
        throw redirect(302, '/fx');
    }
    const urlBase = parts[0].toUpperCase();
    const urlQuote = parts[1].toUpperCase();
    // Canonical = always alphabetical (matching backend + store keys)
    const canonicalBase = urlBase < urlQuote ? urlBase : urlQuote;
    const canonicalQuote = urlBase < urlQuote ? urlQuote : urlBase;
    const canonicalSlug = `${canonicalBase}-${canonicalQuote}`;
    const inverted = urlBase > urlQuote; // true when URL order ≠ canonical
    return {
        urlBase, urlQuote,
        canonicalBase, canonicalQuote, canonicalSlug,
        inverted,
    };
}
```

**Non c'è più il redirect** `if (base > quote) → redirect`. Qualsiasi ordine delle 2 valute è un URL valido.

#### 8b. `+page.svelte` — Derivare `inverted` da `data`, store via `canonicalSlug`

- **Rimuovere** `let inverted = $state(false)` → diventa `let inverted = $derived(data.inverted)`
- **Tutti gli accessi a store** usano `data.canonicalSlug` al posto di `data.slug`:
  - `getFxStore(data.canonicalSlug)` in `loadChartData()`, `handleRefresh()`
  - `getSettingsForPair(data.canonicalSlug)` per il `$derived settings`
  - `setPairSettings(data.canonicalSlug, ...)` in `handleAestheticsChange`, `handleSignalsChange`
  - `handleSync`: `pairs: [data.canonicalSlug]`
- **`displayBase` / `displayQuote`**: ora semplicemente `data.urlBase` e `data.urlQuote`
- **API calls** (convert, providers, sync) usano sempre `data.canonicalBase` e `data.canonicalQuote` (ordine alfabetico per il backend)
- **Il bottone ⇄ (swap direction)**: cambia da `inverted = !inverted` a:
  ```ts
  goto(`/fx/${displayQuote}-${displayBase}`, {replaceState: true})
  ```
  `replaceState: true` evita che forward/back del browser cicli tra le due direzioni.
- **`handleDetailPair(slug)`**: resta invariato — naviga sempre al canonical (che è ciò che passa `ChartSignalsSection`)

#### 8c. `FxCard.svelte` — Navigare alla versione invertita

- `handleCardClick()` cambia da `goto(\`/fx/${slug}\`)` a:
  ```ts
  function handleCardClick() {
      // If inverted, navigate to the inverted URL — detail page reads direction from URL
      const target = inverted ? `${displayQuote}-${displayBase}` : slug;
      goto(`/fx/${target}`);
  }
  ```
  Così, se l'utente ha invertito la card nella lista e ci clicca, il dettaglio si apre con la stessa direzione.

#### 8d. Principio fondamentale — store seguono la coppia canonica

| Cosa | Key |
|------|-----|
| `fxStoreRegistry` (`getFxStore`) | `canonicalSlug` (es. `EUR-USD`) |
| `chartSettingsStore` (`getSettingsForPair`, `setPairSettings`) | `canonicalSlug` |
| `signals` (in `ChartSettings`) | Dentro lo store per `canonicalSlug` |
| `lineData` / `chartData` | Calcolati dal rate canonico, invertiti (`1/rate`) se `inverted` |
| Measures (`MeasurePanel`) | Stato locale nel componente — sopravvive all'inversione perché il componente non si smonta (stessa route, solo `data` prop cambia via SvelteKit shallow navigation) |

#### 8e. SvelteKit shallow navigation — Stessa route, param diverso

Quando si fa `goto('/fx/USD-EUR')` dalla pagina `/fx/EUR-USD`, SvelteKit:
1. Ri-esegue il `load()` di `+page.ts` con il nuovo `params.pair`
2. Il componente `+page.svelte` **non si smonta** — riceve un nuovo `data` via `$props()`
3. Tutti i `$derived` si ricalcolano automaticamente
4. Lo stato locale (`$state`) persiste (misure, panel states, ecc.)

Questo garantisce che le misure e i segnali sopravvivano all'inversione senza nessuna logica speciale.

---

### 9. Confirm modal su switch valuta in edit mode ⚠️ PARZIALE

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`, `frontend/src/lib/components/fx/FxDataEditorSection.svelte`

**Problema**: Quando l'utente è in edit mode (Edit Rates aperto con modifiche non salvate) e clicca il bottone inverti valuta (⇄), le modifiche vengono perse silenziosamente perché i `rows` del DataEditor sono calcolati dai `chartData` che cambiano con l'inversione.

**Soluzione**: Intercettare il click su ⇄ quando `showDataEditor === true`:
1. Il bottone ⇄ chiama un handler `handleSwapDirection()` che:
   - Se `!showDataEditor`: fa `goto(\`/fx/${displayQuote}-${displayBase}\`, {replaceState: true})` direttamente.
   - Se `showDataEditor && dirtyCount === 0`: stessa navigazione diretta.
   - Se `showDataEditor && dirtyCount > 0`: mostra un `ConfirmModal` con messaggio "Le modifiche non salvate andranno perse. Continuare?".
2. Se l'utente conferma: uscire da edit mode (`showDataEditor = false`, reset panel states, `pendingPreviewSignal = null`), poi `goto(...)`.
3. Se l'utente annulla: non fare nulla.

**Nota su `dirtyCount`**: Serve passare il `dirtyCount` dalla `FxDataEditorSection` al parent. La soluzione è esporre una prop `bind:dirtyCount` (un `$state` che viene aggiornato internamente dal DataEditor ogni volta che cambia la lista di dirty rows).

**Stato implementazione**:
- ✅ `showSwapConfirm` stato + `handleSwapDirection()` funzione + `doSwap()` nella page
- ✅ `ConfirmModal` nel template con props corrette (`open`, `onConfirm`, `onCancel`, `confirmText`, `warning`)
- ✅ `editorDirtyCount` stato dichiarato nella page (riga 106)
- ❌ `FxDataEditorSection`: `dirtyCount` è un `$derived` locale ma **NON** esposto come prop `$bindable()`
- ❌ Template page: manca `bind:dirtyCount={editorDirtyCount}` sulla `<FxDataEditorSection>`
- ❌ i18n: mancano chiavi `fxDetail.swapConfirmTitle`, `fxDetail.swapConfirmMessage`, `common.continue`

---

### 10. Misure e segnali mantenuti su inversione valuta ⚠️ PARZIALE

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte`, `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

**Problema**: L'utente si aspetta che le misure e i segnali siano mantenuti (stessi intervalli temporali) e ricalcolati quando si inverte la valuta. Le frecce (arrows) restano calcolate con i rate vecchi.

**Analisi con approccio URL-based**:

Con l'inversione via URL (step 8), `goto('/fx/USD-EUR')` da `/fx/EUR-USD`:
- SvelteKit **non smonta** il componente (stessa route, solo param diverso)
- `data.inverted` cambia → `lineData` si ricalcola (`1/rate`)
- `MeasurePanel` riceve `chartData={lineData}` aggiornato → `$effect` ricalcola tutto
- `overlaySignals` (signals) si ricalcolano automaticamente perché `lineData` cambia
- Le misure sono `$state` locale al MeasurePanel → persistono tra i cambi di `data`

Quindi:
- ✅ I **valori** nella tabella si aggiornano automaticamente (start, end, delta, %)
- ✅ Le **linee measure** sul grafico si ri-rendono via `emitRendered()`
- ⚠️ Verificare che le **frecce** (arrows) delle measure si aggiornino. Le frecce sono calcolate in `MeasureSignal.render()` che usa `chartData` (passato come parametro). Se il render produce nuovi dati con le frecce, il chart le ridisegna.

**Soluzione**: Probabilmente già funziona automaticamente grazie alla reattività. La fix consiste nel:
1. **Verificare** che le frecce si aggiornino correttamente facendo un test manuale: creare una misura, invertire la valuta, verificare che le frecce puntino nella direzione corretta.
2. Se le frecce NON si aggiornano: il problema è che `PriceChartFull` potrebbe cachare l'orientamento delle frecce. In quel caso, forzare un re-render delle frecce quando `overlaySignals` cambia (via `updateArrowRotations()`).
3. Se tutto funziona: nessuna modifica necessaria — documentare che il comportamento è corretto.

---

### 11. BrokerImportFilesModal — Aggiungere 👁 ColumnVisibilityToggle + SelectionBar 🔲 RIMANDATO

**File**: `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte`, `frontend/src/lib/components/files/FilesTable.svelte`

**Problema**: Il BrokerImportFilesModal usa `FilesTable` che ha `showToolbar={false}`. La `DataTableToolbar` interna (ora semplificata) mostra il selection counter solo quando ci sono bulk actions. Ma manca l'icona 👁 per la visibilità colonne, che in Files page è esterna. Nella modale broker non c'è spazio dedicato per questi controlli.

**Soluzione**:
1. **FilesTable**: esporre il ref della DataTable interna via una prop `bind:this` o un metodo `getTableRef()` (verificare se esiste già — dal context: `activeTableRef?.getTableRef()` in files `+page.svelte`).
2. **BrokerImportFilesModal**: nell'header della modale (accanto a "Manage all files" e "×"), aggiungere:
   - `ColumnVisibilityToggle tableRef={filesTableRef?.getTableRef()}`
   - `SelectionBar` (dallo step 4) con i `selectedIds` e bulk actions di FilesTable
3. Serve tracking `selectedIds` via `onSelectionChange` su FilesTable → passare al parent (modale).

**Nota**: Lo step 4 (SelectionBar) deve essere implementato prima di questo step.

---

### 12. Chart performance — Rallentamento con dataset grandi (≥5 anni)

**File**: `frontend/src/lib/components/charts/lineChartHelpers.ts`, `frontend/src/lib/components/charts/PriceChartFull.svelte`, `frontend/src/lib/components/charts/LineChart.svelte`

**Problema**: Caricando 5 anni di dati (~1825 punti giornalieri) il grafico va a rilento. L'esempio ECharts "Large Scale Area Chart" gestisce 2 milioni di punti fluidamente.

**Analisi comparativa con l'esempio ECharts**:

| Aspetto | Esempio ECharts (veloce) | LibreFolio (lento) | Impatto |
|---------|--------------------------|---------------------|---------|
| **`sampling`** | `sampling: 'lttb'` | ❌ Assente | 🔴 CRITICO |
| **Numero series** | 1 sola series | N series (1 per segmento colore/opacità) | 🔴 ALTO |
| **Formato dati** | `data: number[]` (array piatto) | `data: (number\|null)[]` per segmento (padding null) | 🟠 MEDIO |
| **Area fill** | 1 LinearGradient semplice | N LinearGradient (1 per segmento, sia linea che area) | 🟠 MEDIO |
| **Tooltip** | Default ECharts | Custom formatter con `data.find(d => d.date === date)` — O(n) per hover | 🟡 BASSO |
| **Re-render** | `setOption()` una volta | `renderChart()` ricostruisce tutto in `$effect` su ~10 dependency | 🟡 BASSO |
| **`symbol`** | `symbol: 'none'` | `symbol: 'none'` ✅ | ✅ OK |
| **`animation`** | default (true) | `animation: false` ✅ | ✅ OK |

#### Causa #1 — Manca `sampling: 'lttb'` (critica)

ECharts supporta `sampling: 'lttb'` (Largest Triangle Three Buckets), un algoritmo di downsampling che riduce i punti disegnati al numero di pixel disponibili. Con un grafico largo 1000px, solo ~1000 punti vengono renderizzati indipendentemente dal dataset.

**LibreFolio non usa `sampling` su nessuna series.** Questo è il singolo cambiamento con l'impatto più grande.

**Problema con la segmentazione attuale**: `sampling` richiede una **singola series con dati contigui**. L'architettura attuale in `buildMainSeries()` crea N series con array padded-null (una per segmento colore/opacità). ECharts non può applicare `sampling` a dati frammentati con null.

#### Causa #2 — N series segmentate (alto impatto)

`buildMainSeries()` (riga 118-281 di `lineChartHelpers.ts`) splitta il dataset in segmenti per:
- **Baseline coloring**: verde (sopra baseline) / rosso (sotto baseline)
- **Stale gradient**: fresh (opacity 1.0) / stale (opacity < 1.0)

Ogni segmento diventa una **series separata** con un array `new Array(n).fill(null)` dove solo il range [start, end] ha valori. Con 1825 punti e ~10 transizioni colore, si ottengono ~10 series, ciascuna con un array 1825-long quasi tutto `null`.

**Effetto**: ECharts deve iterare N×1825 valori, creare N gradienti, fare N render pass. Il costo cresce linearmente con il numero di segmenti × punti.

#### Causa #3 — Allocazione oggetti nel tooltip (basso ma cumulativo)

Riga 459 di `PriceChartFull.svelte`:
```ts
const dataPoint = data.find(d => d.date === date); // O(n) ad ogni hover
```
Con 1825 punti non è drammatico, ma viene chiamato ad ogni mousemove sul tooltip. Può causare micro-jank durante il hover.

**Soluzione**:

##### Fix A — Aggiungere `sampling: 'lttb'` (priorità 1) ✅ APPLICATO

Aggiungere `sampling: 'lttb'` a TUTTE le series line (main + overlay signal):

```ts
// In buildMainSeries(), per ogni series:
s.sampling = 'lttb';

// In PriceChartFull.svelte, per ogni overlay signal series:
overlaySeries.sampling = 'lttb';

// In LineChart.svelte, stessa cosa
```

⚠️ **Conflitto con segmentazione**: `sampling` non funziona bene con series null-padded perché LTTB non sa gestire i buchi. Due opzioni:

**Opzione 1 (pragmatica)**: Aggiungere `sampling: 'lttb'` comunque. ECharts lo applica parzialmente — i segmenti contigui vengono downsamplati, i null ignorati. Il miglioramento non è del 100% ma è comunque significativo, specialmente per i segmenti lunghi.

**Opzione 2 (strutturale, più impattante)**: Riscrivere `buildMainSeries` per usare **`visualMap`** di ECharts invece di N series separate:
```ts
// Una sola series con tutti i dati contigui
series: [{
    type: 'line',
    data: values, // array piatto senza null
    sampling: 'lttb',
    symbol: 'none',
}],
// Coloring gestito da visualMap
visualMap: [{
    show: false,
    type: 'piecewise',
    dimension: 1, // colora in base al valore Y
    pieces: [
        {min: baseline, color: greenColor},
        {max: baseline, color: redColor},
    ],
    seriesIndex: 0,
}],
```
Questo elimina la segmentazione mantenendo il coloring. Ma richiede riscrivere anche la logica del stale gradient (più complessa con visualMap) — valutare se il trade-off vale.

**Raccomandazione**: Partire con **Opzione 1** (aggiungere `sampling` alle series attuali). Se il miglioramento è sufficiente, non serve la riscrittura strutturale. Se non basta, passare a Opzione 2 come step separato.

##### Fix B — Ottimizzare tooltip con Map lookup (priorità 2) ✅ APPLICATO

Sostituire `data.find()` con un `Map` pre-calcolato:
```ts
// Pre-calcolato una volta (fuori dal formatter)
const staleLookup = new Map(data.filter(d => d.staleDays && d.staleDays > 0).map(d => [d.date, d.staleDays]));

// Nel formatter:
const staleDays = staleLookup.get(date);
if (staleDays) {
    html += `<br/><span style="...">⚠ Stale: ${staleDays}d</span>`;
}
```
Da O(n) a O(1) per ogni hover.

##### Fix C — Ridurre re-render non necessari (priorità 3)

L'`$effect` a riga 123-136 traccia ~10 dependency e chiama `renderChart()` (che ricostruisce TUTTO) per qualsiasi cambiamento. Valutare se alcune proprietà (es. `areaFill`, `showGridLines`) possono essere aggiornate con `setOption()` parziale anziché full rebuild.

---

## Rimanenze da completare

### Da fare subito (prossimo agente)

1. **Step 8c**: `FxCard.svelte` — `handleCardClick()` → navigare a URL invertito se `inverted`
2. **Step 9**: `FxDataEditorSection.svelte` — esporre `dirtyCount` come `$bindable()` prop; `+page.svelte` — aggiungere `bind:dirtyCount={editorDirtyCount}`
3. **Step 10**: `+page.svelte` — fix MeasurePanel con singola istanza (pattern `{#if}...{:else}...{/if}` sul wrapper, componente fuori dall'if)
4. **Step 6**: `MeasurePanel.svelte` — aggiungere condizionale `isNarrow` per `w-full` in narrow mode
5. **i18n**: aggiungere chiavi `fxDetail.swapConfirmTitle`, `fxDetail.swapConfirmMessage`, `common.continue` (4 lingue)
6. **Verifica compilazione**: `./dev.py front check` deve dare 0 errori

### Rimandati a round successivo

- **Step 4**: SelectionBar componente (round 7.4)
- **Step 7**: Debug DRP onchange (verifica manuale)
- **Step 11**: BrokerImportFilesModal (dipende da step 4)
- **Step 12 Fix C**: Ridurre re-render non necessari

---

## File modificati

| File | Modifiche |
|------|-----------|
| `FxDataEditorSection.svelte` | Cancel button `dark:text-slate-900`, esporre `bind:dirtyCount` |
| `+page.ts` (fx/[pair]) | **Riscritto**: rimuovere redirect canonico, esporre `canonicalSlug` + `inverted` + `urlBase`/`urlQuote` |
| `+page.svelte` (fx/[pair]) | Header `dark:bg-amber-900/50`, `inverted` da `$derived(data.inverted)`, tutti store via `canonicalSlug`, swap via `goto()` con `replaceState`, confirm modal su invert in edit mode, MeasurePanel always-mounted |
| `FxCard.svelte` | Navigazione a `/fx/${displayQuote}-${displayBase}` se invertita |
| `DateRangePicker.svelte` | Popover larghezza fissa + traslazione, trigger `w-fit` / prop `triggerFit` |
| `SelectionBar.svelte` | **Rimandato** — round 7.4 |
| `DataEditor.svelte` | **Rimandato** — round 7.4 |
| `+page.svelte` (files) | **Rimandato** — round 7.4 |
| `BrokerImportFilesModal.svelte` | **Rimandato** — round 7.4 |
| `MeasurePanel.svelte` | Style `flex-1 max-w-[400px]`, fix narrow `w-full` |
| `FilesTable.svelte` | **Rimandato** — round 7.4 |
| `lineChartHelpers.ts` | Aggiungere `sampling: 'lttb'` a tutte le series in `buildMainSeries()` |
| `PriceChartFull.svelte` | Fix dblclick: usare `getZr().on('dblclick')`, aggiungere `sampling: 'lttb'` a overlay signal series, tooltip `Map` lookup |
| `LineChart.svelte` | Aggiungere `sampling: 'lttb'` a overlay signal series, tooltip `Map` lookup |
