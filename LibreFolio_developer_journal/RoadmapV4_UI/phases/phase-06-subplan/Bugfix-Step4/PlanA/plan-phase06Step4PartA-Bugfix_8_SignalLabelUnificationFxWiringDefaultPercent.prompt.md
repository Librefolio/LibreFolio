# Bugfix 8 — Signal Label Unification, FX Detail Wiring & Default % ViewMode

Il problema principale è che `AssetComparisonSignal.getLabel()` restituisce `📊 Bitcoin` (stringa con emoji) e questa etichetta si propaga tale quale a MeasurePanel e al tooltip di PriceChartFull, dove servirebbero icone reali. In parallelo, la pagina FX detail ignora completamente i segnali `asset-comparison` nel `overlaySignals` derived e non passa `onsyncasset`/`ondetailasset`/`signalSummaries`/`dateStart` a ChartSignalsSection. Il piano unifica la rappresentazione visiva e colma le lacune funzionali.

## Steps

### ✅ 1. Creare utility `signalLabel.ts` con `SignalLabelInfo` e `signalLabelToHtml()`

**File**: `frontend/src/lib/charts/signalLabel.ts` (nuovo — CREATO)

Definire `SignalLabelInfo { label, iconUrl?, assetType?, color?, isCrown? }`. La funzione `signalLabelToHtml()` genera HTML inline: `<img>` per `iconUrl` o per l'icona PNG tipo-asset (da `getAssetTypeIconUrl`), `👑` se `isCrown`, `●` colorato se `color`. Diventa il punto unico per la rappresentazione visiva di ogni segnale. Usare `getAssetTypeIconUrl` da `assetTypes.ts` per le icone tipo-asset. Aggiungere anche `signalLabelToText()` (versione plain text senza HTML per contesti non-HTML).

### ✅ 2. Arricchire `RenderedSignal` e pulire `AssetComparisonSignal`

**File**: `frontend/src/lib/charts/signals/ChartSignal.ts` — aggiunto `iconUrl?`, `assetType?` a `RenderedSignal`
**File**: `frontend/src/lib/charts/signals/AssetComparisonSignal.ts` — rimosso `📊` emoji da `getLabel()`, aggiunto `iconUrl`/`assetType` in `render()`

Aggiungere campi opzionali `iconUrl?: string` e `assetType?: string` a `RenderedSignal`. In `AssetComparisonSignal.render()`: impostare `iconUrl` e `assetType` da `params._assetIconUrl` / `params._assetType` (iniettati dal parent page, come `_resolvedData`). In `getLabel()` rimuovere l'emoji `📊` — restituire solo il nome pulito.

### ✅ 3. Refactorare `MeasurePanel.svelte`: `pairLabel` → `mainSignalInfo: SignalLabelInfo`

**File**: `frontend/src/lib/components/charts/MeasurePanel.svelte` — refactored

Rinominare prop `pairLabel: string` → `mainSignalInfo: SignalLabelInfo`. In `summaryColumns[0].cell` usare `signalLabelToHtml()` per ogni riga: riga main con `mainSignalInfo` (+ `isCrown=true`), righe overlay con `{ label: signal.label, color: signal.color, iconUrl: signal.iconUrl, assetType: signal.assetType }` ricavato da `RenderedSignal`. Eliminare `MeasureSummaryRow.signal` + `signalColor` e sostituire con `signalInfo: SignalLabelInfo`. Passare `availableAssets` non è più necessario perché le info icona viaggiano dentro `RenderedSignal`.

### ✅ 4. Aggiornare tooltip di `PriceChartFull.svelte`: icone reali al posto di `colorDot`

**File**: `frontend/src/lib/components/charts/PriceChartFull.svelte` — aggiunto `overlaySignalInfoMap`, `mainIconUrl`, `mainAssetType` props + `signalLabelToHtml` nel tooltip formatter

Aggiungere prop opzionale `overlaySignalInfoMap?: Map<string, SignalLabelInfo>` (costruita dal parent). Nel `tooltip.formatter` (~riga 658-662), sostituire `colorDot + p.seriesName` con `signalLabelToHtml(map.get(p.seriesName))` per le righe overlay. Per la serie main, costruire `SignalLabelInfo` dal `mainSeriesLabel` + eventuali icone ricevute come nuovi prop (`mainIconUrl?`, `mainAssetType?`). Per le righe evento (scatter tooltip) mantenere l'attuale format. Il parent (detail pages) costruisce la mappa iterando `overlaySignals`.

### ✅ 5. Aggiornare `assets/[id]/+page.svelte`: wirare nuove props

**File**: `frontend/src/routes/(app)/assets/[id]/+page.svelte`
- ✅ `viewMode` default → `'percentage'`
- ✅ `mainSignalInfo` derived costruito con `isCrown: true`
- ✅ `overlaySignalInfoMap` derived
- ✅ `_assetIconUrl` e `_assetType` iniettati in `loadComparisonAssetsData()`
- ✅ `overlaySignalInfoMap`, `mainIconUrl`, `mainAssetType` passati a `<PriceChartFull>`
- ✅ `mainSignalInfo` passato a `<MeasurePanel>` al posto di `pairLabel`

### ✅ 6. Completare `fx/[pair]/+page.svelte`: supporto asset-comparison e tutte le callback mancanti

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`
- ✅ `viewMode` default → `'percentage'`
- ✅ `overlaySignals` derived: aggiunto blocco `asset-comparison` con `_resolvedData`, `_assetDisplayName`, `_assetIconUrl`, `_assetType`
- ✅ `loadComparisonAssetsData()` aggiunta
- ✅ `$effect` per triggerare `loadComparisonAssetsData`
- ✅ `handleSyncAsset()` e `handleDetailAsset()` aggiunti
- ✅ `signalSummaries` computed aggiunto
- ✅ `mainSignalInfo` e `overlaySignalInfoMap` derivati aggiunti
- ✅ `onsyncasset`, `ondetailasset`, `signalSummaries`, `dateStart` passati a `<ChartSignalsSection>`
- ✅ `mainSignalInfo` passato a `<MeasurePanel>` (rimosso `pairLabel`)
- ✅ `overlaySignalInfoMap` passato a `<PriceChartFull>`

### ✅ 7. Aggiungere `Tooltip` sui badge di riepilogo in `ChartSignalsSection.svelte` e rimuovere icona INDEX

- ✅ Badge wrappati con `<Tooltip>` + chiave i18n
- ✅ `EVENT_BADGE_KEY` map per lookup pulito
- ✅ Chiavi i18n aggiunte in EN/IT/FR/ES: `badgePoints`, `badgeDividend`, `badgeInterest`, `badgePriceAdjustment`, `badgeMaturitySettlement`, `badgeSplit`
- ✅ `INDEX` rimosso da `PNG_MAP` in `assetTypes.ts`
- ✅ `index.png` eliminato da `static/icons/asset-types/`

## Validation

- ✅ `svelte-check`: **0 errors, 0 warnings**

## Further Considerations

1. **Estrazione util condivisa `loadAssetComparisonData()`**: Sia asset detail che FX detail eseguono la stessa logica `query_prices_bulk` + inject `_resolvedData`. Si potrebbe estrarre in un util `lib/charts/loadComparisonData.ts` condiviso. Raccomandazione: estrarlo subito per evitare divergenza.

2. **`RenderedSignal.iconUrl/assetType` vs mappa esterna**: Per il tooltip di PriceChartFull servono le info icona per nome serie. Arricchire `RenderedSignal` copre MeasurePanel, ma PriceChartFull raggruppa per `seriesName` che è `label`. Propongo di usare entrambi: `RenderedSignal` arricchito per MeasurePanel, `overlaySignalInfoMap` per PriceChartFull (costruita dal parent). Così nessun componente deve fare lookup su `availableAssets`.

3. **Tooltip formatter performance**: `signalLabelToHtml()` genera `<img>` tags con URL statici — nessun fetch aggiuntivo, le immagini sono già caricate in pagina. Nessun impatto performance.
