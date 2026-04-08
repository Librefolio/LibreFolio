# Bugfix 9 — Signal Label Polish, Event Marker Fixes, Goto DateRange & Shared Utils

Raccolta delle regressioni e miglioramenti riportati dall'utente dopo il Bugfix 8. Il Bugfix 8 ha risolto i problemi di fondo (unificazione label, FX wiring, default %), ma ha introdotto alcune micro-regressioni e lascia aperti diversi punti cosmetici e funzionali.

---

## Osservazioni utente e risoluzione pianificata

### ✅ 1. Goto resetta il dateRange a 3M

**Problema**: Cliccando "goto" (ExternalLink) su una signal card (asset-comparison o fx-pair), la pagina di destinazione si apre con il range predefinito 3M. Tornando indietro, il range precedente non è ripristinato.

**Soluzione**: Passare `dateStart` e `dateEnd` come query params nell'URL di goto:
- `handleDetailAsset(id)` → `goto(\`/assets/${id}?start=${dateStart}&end=${dateEnd}\`)`
- `handleDetailPair(slug)` → `goto(\`/fx/${slug}?start=${dateStart}&end=${dateEnd}\`)`

Nelle pagine di destinazione (asset detail e FX detail), nel setup iniziale, leggere `$page.url.searchParams` e usarli come valori iniziali di `dateStart`/`dateEnd` al posto del default 3M. Se assenti, fallback al comportamento attuale.

Per il back-navigation: SvelteKit preserva lo stato della pagina precedente nello stack di navigazione. Il `goBack()` attuale già lo gestisce — verificare che non ci sia un reload forzato che resetta lo stato.

**File coinvolti**:
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` — leggere query params in init
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — leggere query params in init
- Entrambe le pagine: `handleDetailAsset`/`handleDetailPair` → aggiungere query params

---

### ✅ 2. Triangolo warning assente quando dati = 0

**Problema**: Se un asset/forex non ha **nessun** dato, il triangolo di warning non compare. Attualmente la condizione è `summary?.firstDate && dateStart && summary.firstDate > dateStart`. Quando `firstDate` è null (0 punti), la condizione è falsa.

**Soluzione**: Estendere la condizione in `ChartSignalsSection.svelte`:
```typescript
const dataStartsLate = summary?.firstDate && dateStart && summary.firstDate > dateStart;
const hasNoData = summary && summary.pointCount === 0;
```
Mostrare il triangolo con tooltip diversificato:
- `hasNoData` → "No data available. Try syncing this asset/pair."
- `dataStartsLate` → testo attuale ("Data starts after chart range...")

Aggiungere chiave i18n `chartSettings.noDataAvailable` in 4 lingue.

**File coinvolti**:
- `frontend/src/lib/components/charts/ChartSignalsSection.svelte`
- `frontend/src/lib/i18n/{en,it,fr,es}.json`

---

### ✅ 3. Puntino colore sparito nella tabella misure (MeasurePanel)

**Problema**: Il refactoring di `MeasurePanel` ha sostituito `signalColor` con `signalInfo: SignalLabelInfo`. La funzione `signalLabelToHtml()` mostra l'icona OPPURE il colore (chain di priorità). L'utente vuole **entrambi**: icona + puntino colore.

**Soluzione**: Aggiornare `signalLabelToHtml()` in `signalLabel.ts`:
- Se sia `iconUrl`/`assetType` SIA `color` sono presenti, mostrare **entrambi**: prima il dot colorato, poi l'icona, poi il label.
- L'attuale logica "mutually exclusive" va cambiata in "additive" per il colore.

**File coinvolti**:
- `frontend/src/lib/charts/signalLabel.ts` — rendere `color` additivo (non mutuamente esclusivo con icon)

---

### ✅ 4. Regressione label FX in MeasurePanel — mancano le bandiere

**Problema**: In FX detail, `mainSignalInfo` è stato cambiato a `{ label: displayBase+'/'+displayQuote, isCrown: true }`. Ma prima mostrava le bandiere emoji: `👑 🇪🇺 EUR → 🇺🇸 USD`.

**Soluzione**: Includere le flag emoji nel label:
```typescript
let mainSignalInfo: SignalLabelInfo = $derived({
    label: `${baseFlag} ${displayBase} → ${quoteFlag} ${displayQuote}`,
    isCrown: true,
});
```

**File coinvolti**:
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — aggiornare `mainSignalInfo` derived

---

### ✅ 5. Manca il colore della linea nel tooltip del grafico

**Problema**: Stessa logica del punto 3 — `signalLabelToHtml()` mostra icona OPPURE colore. Nel tooltip, l'icona dell'asset compare ma il colore della sua linea no. L'utente vuole entrambi.

**Soluzione**: Stesso fix del punto 3 — la modifica a `signalLabelToHtml()` risolve sia MeasurePanel che tooltip.

---

### ✅ 6. INDEX mostra "other" in AssetIcon nella pagina detail

**Problema**: Dopo la rimozione di `INDEX` da `PNG_MAP`, `getAssetTypeIconUrl('INDEX')` restituisce `other.png`. In `AssetIcon.svelte`, la catena di fallback è: `icon_url` → `pngSrc` (da `getAssetTypeIconUrl`) → `BarChart3`. Per INDEX senza `icon_url`, mostra `other.png` (perché esiste) invece di `BarChart3`.

Nel dropdown di `ChartSignalsSection` il codice usa `ASSET_TYPE_ICON_MAP` (che non ha INDEX) → `BarChart3` SVG. Questo è il comportamento desiderato dall'utente.

**Soluzione**: In `AssetIcon.svelte`, aggiungere caso speciale per INDEX:
```typescript
let pngSrc = $derived(assetType && assetType !== 'INDEX' ? getAssetTypeIconUrl(assetType) : null);
```
Oppure: non rimuovere INDEX da `PNG_MAP` ma creare un'icona `index.png` che sia il render del BarChart3 SVG in PNG. Ma è più semplice il primo approccio.

In questo modo INDEX → `pngSrc = null` → `showPng = false` → `BarChart3` SVG.

**File coinvolti**:
- `frontend/src/lib/components/assets/AssetIcon.svelte` — skip PNG per INDEX

---

### ✅ 7. FX detail: eventi degli asset di confronto non visibili

**Problema**: La pagina FX detail non ha la computed `chartEventMarkers` che raccoglie gli eventi di confronto. La prop `eventMarkers` non è nemmeno passata a `<PriceChartFull>`.

**Soluzione**: Aggiungere `chartEventMarkers` derived in FX detail (come in asset detail), passarlo a `<PriceChartFull>`. Nota: la pagina FX non ha eventi propri (le FX pair non hanno eventi), ma i segnali asset-comparison sì — i loro eventi vanno mostrati sul grafico.

**File coinvolti**:
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — aggiungere `chartEventMarkers` derived + passare prop

---

### ✅ 8. Eventi dell'asset principale devono usare il colore del main, non il blu fisso

**Problema**: In `PriceChartFull.svelte`, gli eventi del main asset usano `EVENT_COLORS[m.type]` (es. DIVIDEND = blu). L'utente vuole che usino il colore della linea principale del grafico.

**Soluzione**: Aggiungere una prop opzionale `mainEventColor?: string` a `PriceChartFull`. Se fornita, usarla per gli eventi del main asset (dove `!m.assetLabel`). Il parent la passa come il colore della linea principale (che dipende dal tema: `isDark ? COLORS.lineDark : COLORS.lineLight`).

In alternativa, usare direttamente `baseColor` (già computato in renderChart) per gli eventi senza `assetLabel`. Questo è più semplice e non richiede prop aggiuntive.

**File coinvolti**:
- `frontend/src/lib/components/charts/PriceChartFull.svelte` — usare `baseColor` per eventi main

---

### ✅ 9. Marker eventi: differenziare per tipo (già previsto ma verificare)

**Problema**: L'utente dice "tutti gli eventi hanno sempre il triangolo". Il codice ha `EVENT_SYMBOLS` con forme diverse per tipo, ma potrebbe non funzionare correttamente.

**Soluzione**: Verificare che `EVENT_SYMBOLS` sia applicato correttamente nel loop scatter di `PriceChartFull.svelte`. Attualmente il `symbol` è impostato per-serie (tutti i marker di un tipo hanno la stessa forma). Controllare che il grouping per tipo funzioni — se due tipi finiscono nella stessa serie, la forma sarà quella del primo. Il grouping attuale è per `groupKey = assetLabel::type` per comparison e `type` per main — dovrebbe funzionare. Debug visivo necessario.

**File coinvolti**:
- `frontend/src/lib/components/charts/PriceChartFull.svelte` — debug/verifica EVENT_SYMBOLS

---

### ✅ 10. Marker eventi di confronto: Y alla posizione sbagliata

**Problema**: I marker degli eventi di asset di confronto usano `displayData[idx]?.value` come Y, che è il valore dell'asset **principale**. Dovrebbero essere posizionati alla Y del **proprio** segnale di confronto.

**Soluzione**: Per eventi con `assetLabel`, cercare il valore Y nella serie overlay corrispondente, non in `displayData`. Questo richiede che il renderer degli eventi abbia accesso ai dati overlay. Approcci possibili:

a) Passare una mappa `overlayDataByLabel: Map<string, Map<string, number>>` (label → date → value) a `renderChart()` e usarla per i marker comparison.

b) In alternativa, arricchire `EventMarker` con un campo opzionale `yValue?: number` pre-calcolato dal parent.

L'approccio (a) è più robusto — il renderer ha i dati overlay da `overlaySignals`, basta costruire la lookup map nel loop dove li processa.

**File coinvolti**:
- `frontend/src/lib/components/charts/PriceChartFull.svelte` — lookup Y da overlay data per comparison events

---

### ✅ 11. Estrarre util condivisa `loadComparisonData.ts`

**Problema**: `loadComparisonAssetsData()` è duplicato quasi identico in asset detail e FX detail.

**Soluzione**: Estrarre in `frontend/src/lib/charts/loadComparisonData.ts`:
```typescript
export async function loadComparisonAssetsData(
    compSignals: SignalConfig[],
    dateRange: { start: string; end: string },
    allAssets: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}>,
    excludeAssetId?: number, // asset detail exclues self
): Promise<{ comparisonEvents: Map<number, any[]> }>
```
Entrambe le pagine importano e usano questa funzione, eliminando la duplicazione.

**File coinvolti**:
- `frontend/src/lib/charts/loadComparisonData.ts` (nuovo)
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` — import + uso
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — import + uso

---

## Ordine di implementazione suggerito

1. ✅ **Step A**: Fix `signalLabelToHtml()` — colore additivo (risolve punti 3 e 5)
2. ✅ **Step B**: Fix FX `mainSignalInfo` con bandiere (punto 4)
3. ✅ **Step C**: Fix `AssetIcon` per INDEX (punto 6)
4. ✅ **Step D**: Fix warning triangle per dati=0 (punto 2)
5. ✅ **Step E**: Goto con dateRange in query params (punto 1)
6. ✅ **Step F**: FX detail `chartEventMarkers` (punto 7)
7. ✅ **Step G**: Main events color + Y position + marker diff (punti 8, 9, 10)
8. ✅ **Step H**: Estrarre `loadComparisonData.ts` (punto 11)

---

## Post-review — Fix aggiuntivi (Bugfix 9b)

### ✅ 12. Disallineamento dot/corona nella tabella misure

**Problema**: Il puntino colore `●` (8px + 4px margin) occupa meno spazio orizzontale della corona `👑` (~1em + 2px margin), causando disallineamento delle colonne nella DataTable.

**Soluzione**: Entrambi gli elementi (corona e dot) ora usano container `display:inline-block; width:1em` a larghezza fissa. Il dot è centrato nel container con `inline-flex + justify-content:center`.

**File**: `frontend/src/lib/charts/signalLabel.ts`

### ✅ 13. Loop infinito API calls — `$effect` tracking async reads

**Problema**: L'`$effect` che triggera `loadComparisonData(compSignals)` tracciava anche le letture reattive sincrone dentro la funzione async (`comparisonEvents`, `dateStart`, `dateEnd`, `allAssets`). Quando `loadComparisonData` aggiorna `comparisonEvents`, l'`$effect` si ri-attivava → loop infinito di `POST /api/v1/assets/prices/query`.

**Causa root**: In Svelte 5, `$effect` traccia TUTTE le letture reattive sincrone, incluse quelle nelle funzioni chiamate dal body dell'effect. `loadComparisonData` leggeva `comparisonEvents` (passata come arg a `loadComparisonAssetsData`) e poi la sovrascriveva → loop.

**Soluzione**: Wrappare la chiamata async in `untrack()`:
```typescript
$effect(() => {
    const compSignals = signals.filter(s => s.signalType === 'asset-comparison');
    if (compSignals.length > 0 && lineData.length > 0) {
        untrack(() => loadComparisonData(compSignals));
    }
});
```

**File**:
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` — import `untrack`, wrap call
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — import `untrack`, wrap call

### Note: FX event markers (punto 7)

I marker eventi FX erano implementati correttamente ma non visibili a causa del loop infinito (punto 13) che impediva il completamento di `loadComparisonData`. Con il fix `untrack`, gli eventi dei comparison assets dovrebbero ora renderizzarsi correttamente anche nella pagina FX detail.
