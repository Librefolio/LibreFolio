# Plan: Parte 0 — Parità Asset List ↔ FX List + Bugfix + AssetComparisonSignal

**Fase:** Phase 6 Step 4, Parte 0
**Prerequisito per:** Parte A (detail page), Parte B (data editor), Parte C (currency conversion)

**Scopo:** Portare AssetCard e la pagina lista asset allo stesso livello funzionale di FxCard e della lista FX (settings, Abs/%, segnali), creare un nuovo segnale `AssetComparisonSignal` disponibile ovunque (FX+Asset), e risolvere bug critici emersi durante i test.

---

## 0.1 — AssetCard: nuove props e pulsanti (allineamento a FxCard)

**File:** `frontend/src/lib/components/assets/AssetCard.svelte`
**Riferimento:** `frontend/src/lib/components/fx/FxCard.svelte` (righe 24-64 Props, 76-88 localViewModeOverride, 128-141 overlaySignals, 199-207 pulsante %, 265-271 pulsante ⚙)

### Modifiche:

1. **Aggiungere import** (allineamento a FxCard riga 11, 17-18):
   - `Percent, Settings` da `lucide-svelte` (aggiungerli a quelli già importati riga 11)
   - `type ChartSettings` da `$lib/stores/chartSettingsStore.svelte`
   - `type RenderedSignal` da `$lib/charts/signals`

2. **Estendere `interface Props`** (attualmente righe 32-52):
   - Aggiungere `chartSettings?: ChartSettings` (= FxCard riga 35)
   - Aggiungere `renderSignals?: (chartData: LineDataPoint[], viewMode: 'absolute' | 'percentage') => RenderedSignal[]` (= FxCard riga 42)
   - Aggiungere `onsettings?: (asset: AssetData) => void` (analogo a FxCard riga 47 ma con `AssetData` invece di `{slug}`)
   - **Rinominare** `deltaDisplayMode` → `globalViewMode` (coerenza con FxCard riga 33), tipo `'absolute' | 'percentage'`, default `'percentage'`

3. **Destrutturare le nuove props** (righe 54-66): aggiungere `chartSettings`, `renderSignals`, `onsettings`, rinominare `deltaDisplayMode` → `globalViewMode`

4. **Aggiungere stato `localViewModeOverride`** (pattern identico FxCard righe 76-88):
   ```
   let localViewModeOverride = $state<'absolute' | 'percentage' | null>(null);
   let cardViewMode = $derived(localViewModeOverride ?? globalViewMode);
   // Reset local override when global changes
   let prevGlobal: string | undefined;
   $effect(() => {
       if (prevGlobal !== undefined && globalViewMode !== prevGlobal) {
           localViewModeOverride = null;
       }
       prevGlobal = globalViewMode;
   });
   ```

5. **Aggiungere `absoluteData` derivato** (necessario per i segnali, come FxCard righe 129-135). Per AssetCard è più semplice perché non c'è inversione — `absoluteData` = `chartData` (passato come prop). Per coerenza col pattern:
   ```
   let absoluteData = $derived(chartData);
   ```

6. **Aggiungere `overlaySignals` derivato** (= FxCard righe 138-141):
   ```
   let overlaySignals = $derived.by((): RenderedSignal[] => {
       if (!renderSignals || absoluteData.length === 0) return [];
       return renderSignals(absoluteData, cardViewMode);
   });
   ```

7. **Aggiornare la riga delta** (template, attualmente righe 152-160):
   - Sostituire la condizione `deltaDisplayMode === 'absolute'` → `cardViewMode === 'absolute'` (perché ora la card ha il suo toggle locale)

8. **Aggiungere pulsante `%` toggle** nell'header, Row 1 (righe 126-142). Inserirlo nella `div` con `items-center gap-1.5 shrink-0` (riga 132), **prima** del type badge, stesso stile FxCard righe 199-207:
   ```svelte
   <button
       class="p-1 rounded-md transition-colors {cardViewMode === 'percentage'
           ? 'bg-libre-green/10 text-libre-green dark:bg-libre-green/20 dark:text-green-400'
           : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-gray-300'}"
       onclick={(e) => { stop(e); localViewModeOverride = cardViewMode === 'absolute' ? 'percentage' : 'absolute'; }}
       title={cardViewMode === 'absolute' ? $t('chart.showPercentage') : $t('chart.showAbsolute')}
   >
       <Percent size={14}/>
   </button>
   ```

9. **Aggiungere pulsante `⚙ Settings`** nel footer (righe 190-207). Inserirlo **a sinistra** prima del pulsante Sync (come FxCard righe 265-271):
   ```svelte
   <button
       class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
       onclick={(e) => { stop(e); onsettings?.(asset); }}
       title={$t('chartSettings.title')}
   >
       <Settings size={15}/>
   </button>
   ```

10. **Aggiornare `PriceChartCompact`** (righe 171-177). Sostituire le props hardcoded con quelle derivate da `chartSettings` (= FxCard righe 241-249):
    ```svelte
    <PriceChartCompact
        data={chartData}
        height="80px"
        viewMode={cardViewMode}
        areaFill={chartSettings?.areaFill ?? true}
        colorByBaseline={chartSettings?.colorByBaseline}
        showGridLines={chartSettings?.gridLines}
        showGradient={chartSettings?.staleGradient ?? true}
        overlaySignals={overlaySignals}
    />
    ```

---

## 0.2 — Assets List Page: wiring settings + signals nelle card (RIVISTO)

**File:** `frontend/src/routes/(app)/assets/+page.svelte`
**Riferimento:** `frontend/src/routes/(app)/fx/+page.svelte` (righe 26-28 imports signals, 337-353 settings handlers, 359-393 getRenderedSignals, 855-869 FxCard props)

**Correzione critica rispetto al piano macro:** la funzione `getRenderedSignals` nella pagina Asset **DEVE** supportare anche `FxPairSignal` (non solo segnali sintetici). L'utente vuole poter sovrapporre cambi FX sui grafici asset e viceversa.

### Modifiche:

1. **Aggiungere import per signals** (in cima, dopo riga 36):
   - `import { type RenderedSignal, signalFromConfig } from '$lib/charts/signals';`
   - `import type { LineDataPoint } from '$lib/components/charts/LineChart.svelte';`
   - `import { getSettingsVersion } from '$lib/stores/chartSettingsStore.svelte';` (aggiungere a riga 33 che già importa `getSettingsForPair` ecc.)
   - `import { getFxStore } from '$lib/stores/fxStoreRegistry';`

2. **Creare la funzione `getRenderedSignals`** (completa, supporta FxPairSignal + AssetComparisonSignal + segnali sintetici):
   ```typescript
   function getRenderedSignals(
       assetId: number,
       absoluteData: LineDataPoint[],
       vm: 'absolute' | 'percentage'
   ): RenderedSignal[] {
       void getSettingsVersion();
       const settings = getSettingsForPair(`asset-${assetId}`);
       if (!settings.signals.length) return [];
       const rendered: RenderedSignal[] = [];
       for (const cfg of settings.signals) {
           const instance = signalFromConfig(cfg);
           if (!instance) continue;

           // Resolve FxPairSignal data from FX stores
           if (cfg.signalType === 'fx-pair') {
               const pairSlug = String(cfg.params.pairSlug || '');
               if (!pairSlug) continue;
               try {
                   const store = getFxStore(pairSlug);
                   const storeData = store.getAllSorted();
                   if (storeData.length === 0) continue;
                   instance.params._resolvedData = storeData.map(d => ({
                       date: d.date,
                       value: d.rate,
                   }));
               } catch { continue; }
           }

           // Resolve AssetComparisonSignal data from local assets array
           if (cfg.signalType === 'asset-comparison') {
               const targetId = Number(cfg.params.assetId);
               if (!targetId || targetId === assetId) continue;
               const targetAsset = assets.find(a => a.id === targetId);
               if (!targetAsset?.chartData?.length) continue;
               instance.params._resolvedData = targetAsset.chartData;
               instance.params._assetDisplayName = targetAsset.display_name;
           }

           const results = instance.renderMulti(absoluteData, vm);
           for (const result of results) {
               if (result.data.length > 0) rendered.push(result);
           }
       }
       return rendered;
   }
   ```

3. **Creare `handleCardSettings`** (analogo a FX riga 337-340):
   ```typescript
   function handleCardSettings(asset: { id: number }) {
       settingsTargetId = String(asset.id);
       settingsModalOpen = true;
   }
   ```
   Nota: `handleGlobalSettings` (riga 555) e `handleSettingsSave` (riga 560) **esistono già** e sono corretti. Non vanno toccati.

4. **Rinominare `deltaDisplayMode` → `globalViewMode`** nella prop passata ad `AssetCard`. Attualmente riga 904 dice `deltaDisplayMode={globalViewMode}`, ma dopo il rename nella card la prop diventa `globalViewMode={globalViewMode}`.

5. **Aggiungere le nuove props ad ogni `AssetCard`** nel Grid View (righe 891-912):
   ```svelte
   <AssetCard
       asset={...}
       lastPrice={asset.lastPrice}
       deltaPercent={asset.deltaPercent}
       deltaAbs={asset.deltaAbs}
       globalViewMode={globalViewMode}
       chartSettings={getSettingsForPair(`asset-${asset.id}`)}
       renderSignals={(chartData, vm) => getRenderedSignals(asset.id, chartData, vm)}
       chartData={asset.chartData}
       loading={asset.loadingPrices}
       syncing={syncingAssetIds.has(asset.id)}
       onsync={handleSyncAsset}
       onrefresh={handleRefreshAsset}
       ondelete={handleDeleteAsset}
       onsettings={handleCardSettings}
   />
   ```

6. **Aggiornare `ChartSettingsModal`** (riga 930-936). Passare le props mancanti per preview e signal resolution:
   ```svelte
   <ChartSettingsModal
       bind:open={settingsModalOpen}
       mode={settingsTargetId ? 'pair' : 'global'}
       onclose={() => { settingsModalOpen = false; settingsTargetId = null; }}
       onsave={handleSettingsSave}
       settings={settingsForModal}
       pairData={settingsTargetId
           ? assets.find(a => a.id === Number(settingsTargetId))?.chartData
           : undefined}
       availablePairs={fxPairSlugs}
       availableAssets={assets.map(a => ({ id: a.id, display_name: a.display_name }))}
   />
   ```
   Dove `fxPairSlugs` è caricato on-demand (o vuoto se i dati FX non sono disponibili).

7. **Estendere `getRenderedSignals` nella pagina FX** (`fx/+page.svelte`) per supportare `AssetComparisonSignal`:
   - Nel blocco `getRenderedSignals` (riga 359-393), aggiungere dopo il blocco `fx-pair`:
   ```typescript
   if (cfg.signalType === 'asset-comparison') {
       const targetId = Number(cfg.params.assetId);
       if (!targetId) continue;
       // Load asset price data on-demand (or skip if not available)
       // For now: graceful skip — full resolution requires async loading
       // which will be implemented in Parte A when the detail page exists
       continue;
   }
   ```
   - Nella pagina FX, i dati Asset non sono pre-caricati. L'approccio iniziale è: skip graceful con tooltip "dati asset non disponibili in questa vista". La risoluzione completa (caricamento on-demand) verrà in Parte A.

---

## 0.3 — Abs/% toggle coerenza grid ↔ table

**Decisione: nessuna modifica.** La matrice 2×2 della pagina lista (righe 797-817) mostra già `ColumnVisibilityToggle` in table mode e `Abs/%` in grid mode. La tabella `AssetTable` mostra le colonne Δ% multi-periodo, quindi il toggle Abs/% per le card non ha senso in table view. Confermato: as-is (stesso pattern della FX page, righe 759-779).

---

## 0.4 — NUOVO: `AssetComparisonSignal` (nuovo tipo di segnale)

**Scopo:** Permettere di sovrapporre il prezzo di un asset come segnale su qualsiasi grafico (FX o Asset). Complementare a `FxPairSignal` che permette di sovrapporre un cambio FX.

### File da creare:

**`frontend/src/lib/charts/signals/AssetComparisonSignal.ts`**

Architettura (modello: `FxPairSignal.ts`):
- `signalType`: `'asset-comparison'`
- `displayName`: `'Asset'`
- `icon`: `'📊'`
- `category`: `'comparison'`
- `paramDescriptors`: un unico `'select'` param con `dynamicOptionsKey: 'configuredAssets'`
  ```typescript
  static override paramDescriptors: SignalParamDescriptor[] = [
      {
          key: 'assetId',
          label: 'Asset',
          type: 'select',
          default: '',
          dynamicOptionsKey: 'configuredAssets',
          tooltip: 'chartSettings.tooltips.assetComparison',
      },
  ];
  ```
- `computePoints`: legge `this.params._resolvedData` (iniettato dal parent, identico al pattern FxPairSignal), allinea alle date del chart base
- `render`: override come FxPairSignal — in `% mode`, normalizza al PROPRIO primo valore (non al p0 del chart base), perché le scale sono diverse
- `getLabel`: mostra `display_name` dell'asset (letto da `this.params._assetDisplayName` iniettato dal parent, o fallback all'ID)

### File da modificare:

1. **`frontend/src/lib/charts/signals/registry.ts`** (riga 33-42):
   - Importare `AssetComparisonSignal`
   - Aggiungere al `SIGNAL_REGISTRY`:
   ```typescript
   [AssetComparisonSignal.signalType, AssetComparisonSignal as unknown as SignalConstructor],
   ```

2. **`frontend/src/lib/charts/signals/index.ts`**:
   - Aggiungere export: `export { AssetComparisonSignal } from './AssetComparisonSignal';`

3. **`frontend/src/lib/components/charts/ChartSignalsSection.svelte`**:
   - Aggiungere prop `availableAssets?: Array<{id: number, display_name: string}>`
   - Estendere `resolveDynamicOptions` (riga 187-195):
   ```typescript
   if (dynamicKey === 'configuredAssets') {
       return (availableAssets ?? []).map(a => ({
           value: String(a.id),
           label: a.display_name,
       }));
   }
   ```
   - Nel template (dopo il blocco `{#if desc.dynamicOptionsKey === 'configuredFxPairs'}`, riga 364), aggiungere:
   ```svelte
   {:else if desc.dynamicOptionsKey === 'configuredAssets'}
       <div class="w-48">
           <SimpleSelect
               value={getParamString(signal, desc.key)}
               options={resolveDynamicOptions('configuredAssets')}
               placeholder="— Select asset"
               onchange={(v) => updateSignalParam(signal.id, desc.key, v)}
           />
       </div>
   ```

4. **`frontend/src/lib/components/charts/ChartSettingsModal.svelte`**:
   - Aggiungere props `availableAssets?: Array<{id: number, display_name: string}>` e `assetsDataMap?: Record<string, LineDataPoint[]>`
   - Passare `availableAssets` a `ChartSignalsSection`
   - Nel preview rendering, risolvere `_resolvedData` per `asset-comparison` signals (come già fa per `fx-pair`)

---

## 0.5 — NUOVO: BrokerIcon `effect_update_depth_exceeded` + icon non reattiva a pluginCode — Bugfix critico

**File:** `frontend/src/lib/components/brokers/BrokerIcon.svelte`

### Bug 1 — Infinite loop su fresh DB

Navigando a `/brokers` dopo aver creato un broker su DB vuoto, l'app si blocca con errore `effect_update_depth_exceeded` dalla catena `BrokerIcon.svelte:134`.

### Bug 2 — Selezione plugin in BrokerForm non aggiorna l'icona

In `BrokerForm.svelte` (riga 275-280), `BrokerIcon` riceve `pluginCode={defaultImportPlugin}`. Inizialmente `defaultImportPlugin` è `''`. L'`onMount` di BrokerIcon carica la lista plugin ma il check `if (pluginCode)` (riga 135) fallisce perché `pluginCode` è ancora vuoto. Quando l'utente seleziona un plugin dal dropdown, `pluginCode` cambia ma `onMount` non viene rieseguito — `pluginIconUrl` resta null e l'icona mostra sempre il fallback Briefcase.

### Analisi root cause (condivisa)

Il componente usa una state machine imperativa (`currentAttempt` + due `$effect` + funzioni ricorsive `moveToNextFallback`) per gestire la catena di fallback `icon_url → portal favicon → plugin icon → Briefcase`. I due `$effect` (righe 153-158 e 161-170) scrivono a variabili `$state` condivise (`currentAttempt`, `currentUrl`, `imageKey`, `imageLoaded`) e le leggono transitivamente via `computeUrl()` e `moveToNextFallback()`, creando dipendenze reattive non intenzionali. Inoltre `onMount` carica i plugin una sola volta — non reagisce a cambi di `pluginCode`.

### Fix: riscrittura a `$derived` + plugin loading reattivo

Sostituire la state machine imperativa con un approccio puramente dichiarativo:

1. `pluginIconUrl = $state<string | null>(null)` — caricato reattivamente (non più in onMount)
2. **Sostituire `onMount`** con un `$effect` che osserva `pluginCode`:
   ```typescript
   $effect(() => {
       const code = pluginCode;
       if (!code) {
           pluginIconUrl = null;
           return;
       }
       loadPluginIcon(code);
   });

   async function loadPluginIcon(code: string) {
       try {
           const plugins = await zodiosApi.list_plugins_api_v1_brokers_import_plugins_get();
           const plugin = plugins.find(p => p.code === code);
           pluginIconUrl = plugin?.icon_url ?? null;
       } catch {
           pluginIconUrl = null;
       }
   }
   ```
   Questo risolve Bug 2: ogni volta che `pluginCode` cambia (es. l'utente seleziona un plugin nel form), l'icona si aggiorna.
3. `candidateUrls = $derived(...)` — array ordinato di URL candidate, derivato da props + `pluginIconUrl`:
   ```typescript
   let candidateUrls = $derived.by(() => {
       const urls: string[] = [];
       if (iconUrl?.trim()) urls.push(iconUrl);
       if (portalUrl?.trim()) {
           try { urls.push(new URL(portalUrl).origin + '/favicon.ico'); } catch {}
       }
       if (pluginIconUrl) urls.push(pluginIconUrl);
       return urls;
   });
   ```
4. `failedUrls = $state(new Set<string>())` — aggiornato solo da `handleError()`
5. `currentDisplayUrl = $derived(candidateUrls.find(u => !failedUrls.has(u)) ?? null)` — prima URL non-fallita
6. **Eliminare** entrambi i vecchi `$effect`, `moveToNextFallback()`, `resetAttempt()`, `currentAttempt`, `imageKey`, `onMount`

Reset su cambio props: quando `mainPropsKey` (derivato da `iconUrl|portalUrl|pluginCode`) cambia, `candidateUrls` si aggiorna automaticamente. `failedUrls` deve essere resettato — usare un `$effect` minimale:
```typescript
let prevPropsKey = '';
$effect(() => {
    const key = mainPropsKey;
    if (key !== prevPropsKey) {
        prevPropsKey = key;
        failedUrls = new Set();
    }
});
```

Questo elimina completamente le dipendenze effect↔effect, rende il plugin loading reattivo, ed è Svelte 5 idiomatico.

### Perché i test non lo intercettavano

- Nessun test unitario per `BrokerIcon.svelte` (confermato: zero file `BrokerIcon*.test*`)
- I test E2E creano broker ma non verificano il rendering dell'icona in isolamento
- Bug 1 si manifesta solo quando tutte le URL fallback sono null (fresh DB) + flush cycle timing di produzione
- Bug 2 non si manifesta se il broker ha già un plugin assegnato al momento del mount (solo in create mode)

### Test da creare

- **Vitest component test** (`BrokerIcon.test.ts`):
  - Test 1: montare con `iconUrl=null, portalUrl=null, pluginCode='test_plugin'`, mockare la API plugins con delay. Verificare che dopo mount il componente mostra il fallback Briefcase senza errori. Verificare che se `pluginIconUrl` ha un valore, l'img viene renderizzato.
  - Test 2: montare con `pluginCode=''`, poi cambiare `pluginCode` a `'broker_etoro'`. Verificare che l'icona si aggiorna (da Briefcase a img del plugin).
- **E2E test** (Playwright): su DB vuoto, creare broker con plugin, navigare a `/brokers`, verificare che la pagina non si blocca (broker card visibile entro timeout) e nessun errore console `effect_update_depth_exceeded`.

---

## 0.6 — NUOVO: BrokerForm — Usare `SingleDatePicker` per `opened_at`

**File:** `frontend/src/lib/components/brokers/BrokerForm.svelte`

### Bug

Riga 302-307: il campo "Opened At" usa `<input type="date">` (date picker nativo del browser) anziché il componente `SingleDatePicker` custom del progetto (`frontend/src/lib/components/ui/SingleDatePicker.svelte`).

### Fix

Sostituire `<input type="date" bind:value={openedAt}>` con:
```svelte
<SingleDatePicker
    value={openedAt}
    onchange={(d) => { openedAt = d; }}
    label={$_('brokers.openedAt')}
/>
```

Importare `SingleDatePicker` nel file. Rimuovere il `<label>` wrapper poiché SingleDatePicker ha il suo. Verificare dark mode e responsive.

---

## 0.7 — NUOVO: DistributionEditor — `SectorSearchSelect` + `CountrySearchSelect` inline

**File principali:**
- `frontend/src/lib/components/ui/input/DistributionEditor.svelte`
- `frontend/src/lib/components/ui/select/SectorSearchSelect.svelte` (**nuovo**)

### Bug UX

La colonna key nel `DistributionEditor` usa una `editable-select` plain (riga 275-281) sia per i settori (12 voci) che per i paesi (195+ voci). Per i paesi è impraticabile senza ricerca; per i settori è funzionale ma inconsistente. Entrambi devono avere ricerca.

### Contesto

- Esiste già `CountrySearchSelect.svelte` — ricerca per ISO3/ISO2/nome localizzato, flag emoji, include "Other" come opzione catch-all.
- NON esiste `SectorSearchSelect.svelte` — i settori usano `getSectorKeysList()` da `assetTypes.ts` (con fallback locale) + i18n via `sectorI18nKey()`.
- I settori vengono dal backend (`GET /utilities/sectors` con `include_other: true`) tramite `sectorStore.ts`.

### Piano: creare `SectorSearchSelect` e usare entrambi nel DistributionEditor

**1. Creare `SectorSearchSelect.svelte`** — modellato su `CountrySearchSelect`:

File: `frontend/src/lib/components/ui/select/SectorSearchSelect.svelte`

- **Stesso pattern** di CountrySearchSelect: wrappa `SearchSelect`, carica dati dal proprio store, costruisce `SelectOption[]`
- Prop interface analoga: `value`, `excludedSectors?: Set<string>`, `placeholder`, `disabled`, `onchange`
- Caricamento settori: `$effect` che chiama `ensureSectorsLoaded()` poi `getSectorKeysList()` per ottenere la lista (include "Other" dal backend)
- Opzioni: `getSectorKeysList().map(k => ({ value: k, label: $t(\`sectors.${sectorI18nKey(k)}\`) || k }))` — localizzate via i18n
- "Other" è già incluso nella lista dal backend (`include_other: true` in `sectorStore.ts` riga 39)
- Snippet `item` e `selectedItem`: nome settore localizzato (niente icona/emoji per i settori, solo testo)

**2. Esportare dal barrel** — aggiungere a `frontend/src/lib/components/ui/select/index.ts`:
```typescript
export {default as SectorSearchSelect} from './SectorSearchSelect.svelte';
```

**3. Aggiornare `DistributionEditor.svelte`** — colonna `key`:

- Importare `CountrySearchSelect` e `SectorSearchSelect`
- Nella definizione della colonna `key` (riga 267-286), quando `!isReadonly && !disabled`:
  - Se `kind === 'geographic'`: il cell content renderizza `CountrySearchSelect` inline con `value={row.key}`, `excludedCountries={usedKeys minus row.key}`, `onchange={(v) => updateKey(row.id, v)}`
  - Se `kind === 'sector'`: il cell content renderizza `SectorSearchSelect` inline con `value={row.key}`, `excludedSectors={usedKeys minus row.key}`, `onchange={(v) => updateKey(row.id, v)}`
- Approccio: usare il tipo di cella `'editable-component'` (snippet-based) del DataTable per renderizzare il componente search dentro la cella. Alternativa: restituire un cell content di tipo `custom` con snippet che rende il componente.

**Nota "Other":** Entrambi i selettori devono mostrare "Other" come opzione in fondo alla lista:
- `CountrySearchSelect`: già presente (riga 150: `{value: 'Other', label: '🏳️ Other — ${$t('common.other')}'}`)
- `SectorSearchSelect`: incluso nella lista dal backend (`include_other: true`), etichetta localizzata `$t('sectors.Other')` o fallback "Other"

---

## 0.8 — NUOVO: DataTable — Filtro "Show selected only" nell'header della colonna selezione

**File:** `frontend/src/lib/components/table/DataTable.svelte`

### Feature

Aggiungere al DataTable un toggle per mostrare solo le righe attualmente selezionate. Il toggle appare come icona filtro (🔍 `Filter`) **nell'header della colonna di selezione** (la colonna checkbox, righe 840-851), coerente con gli imbuti filtro delle colonne dati (righe 904-914).

### Implementazione

1. **Stato:** aggiungere `showSelectedOnly = $state(false)` nel DataTable

2. **Filtro nella pipeline:** nel calcolo di `filteredData`, se `showSelectedOnly` è true, filtrare per `selectedIds.has(getRowId(row))`. Questo filtro si applica DOPO i filtri colonna e PRIMA della paginazione.

3. **Toggle nell'header della colonna selezione** (righe 840-851):
   - Accanto (o sotto) al checkbox "select all", aggiungere un pulsante filtro con icona `Filter` (lucide-svelte), stessa estetica del filter button delle colonne dati:
     ```svelte
     <button
         type="button"
         class="filter-btn"
         class:active={showSelectedOnly}
         onclick={() => { showSelectedOnly = !showSelectedOnly; }}
         title="Show selected only"
     >
         <Filter size={12}/>
     </button>
     ```
   - Quando attivo: stile evidenziato (verde, come `class:active` sui filtri colonna)

4. **Auto-deactivazione:** quando `selectedIds` diventa vuoto (l'utente deseleziona tutto), il toggle si disattiva automaticamente e la tabella torna a mostrare tutte le righe:
   ```typescript
   $effect(() => {
       if (selectedIds.size === 0 && showSelectedOnly) {
           showSelectedOnly = false;
       }
   });
   ```

5. **Deselezionare righe:** L'utente deve poter continuare a deselezionare righe anche quando il filtro è attivo:
   - Click sulla checkbox di una riga → deseleziona → la riga scompare dalla vista (perché non più selezionata)
   - Click "Clear selection" nella `DataTableToolbar` → svuota la selezione → il filtro si auto-disattiva (punto 4) → tutte le righe tornano visibili
   - Il "select all" checkbox nell'header (quando il filtro è attivo) opera solo sulle righe VISIBILI (cioè quelle selezionate), permettendo deselezionamento bulk

---

## Riepilogo file da modificare (Parte 0 completa)

| Step | File | Tipo |
|------|------|------|
| 0.1 | `frontend/src/lib/components/assets/AssetCard.svelte` | Modifica (props, pulsanti, chart) |
| 0.2 | `frontend/src/routes/(app)/assets/+page.svelte` | Modifica (wiring, `getRenderedSignals` completo) |
| 0.2 | `frontend/src/routes/(app)/fx/+page.svelte` | Modifica (estendere `getRenderedSignals` per `asset-comparison`) |
| 0.4 | `frontend/src/lib/charts/signals/AssetComparisonSignal.ts` | **Nuovo file** |
| 0.4 | `frontend/src/lib/charts/signals/registry.ts` | Modifica (registro) |
| 0.4 | `frontend/src/lib/charts/signals/index.ts` | Modifica (export) |
| 0.4 | `frontend/src/lib/components/charts/ChartSignalsSection.svelte` | Modifica (dynamic options per assets) |
| 0.4 | `frontend/src/lib/components/charts/ChartSettingsModal.svelte` | Modifica (nuove props assets) |
| 0.5 | `frontend/src/lib/components/brokers/BrokerIcon.svelte` | **Riscrittura** (da state machine a `$derived` + plugin loading reattivo) |
| 0.5 | `frontend/src/lib/components/brokers/BrokerIcon.test.ts` | **Nuovo file** (vitest) |
| 0.5 | `frontend/e2e/broker-icon.spec.ts` | **Nuovo file** (playwright) |
| 0.6 | `frontend/src/lib/components/brokers/BrokerForm.svelte` | Modifica (SingleDatePicker) |
| 0.7 | `frontend/src/lib/components/ui/select/SectorSearchSelect.svelte` | **Nuovo file** |
| 0.7 | `frontend/src/lib/components/ui/select/index.ts` | Modifica (export SectorSearchSelect) |
| 0.7 | `frontend/src/lib/components/ui/input/DistributionEditor.svelte` | Modifica (CountrySearchSelect + SectorSearchSelect inline) |
| 0.8 | `frontend/src/lib/components/table/DataTable.svelte` | Modifica (show selected filter in selection column header) |

---

## Dipendenze interne Parte 0

```
0.4 (AssetComparisonSignal) ─┐
0.1 (AssetCard props)     ───┼→ 0.2 (List page wiring — serve sia 0.1 che 0.4)
                              │
0.5 (BrokerIcon fix)      ───┤  indipendente (risolve Bug 1 infinite loop + Bug 2 plugin icon reattività)
0.6 (BrokerForm date)     ───┤  indipendente
0.7 (DistributionEditor)  ───┤  indipendente (SectorSearchSelect nuovo + CountrySearchSelect esistente)
0.8 (DataTable filter)    ───┘  indipendente
```

---

## Further Considerations

1. **Caricamento dati FX per segnali nelle pagine Asset:** La pagina Asset attualmente non carica dati FX. Per risolvere `FxPairSignal._resolvedData`, serve importare `getFxStore` e leggere dai cache FX già popolati (se l'utente ha visitato la pagina FX). Graceful fallback: segnale non renderizzato se dati FX non disponibili, con tooltip "visita la pagina FX per popolare i dati".

2. **Caricamento dati Asset per segnali nelle pagine FX:** La pagina FX non ha dati Asset. Approccio iniziale: skip graceful. La risoluzione completa (caricamento on-demand via `POST /assets/prices/query`) verrà implementata in Parte A quando la detail page esiste e l'infrastruttura di caricamento è consolidata.

3. **BrokerCard Svelte 4 legacy:** `BrokerCard.svelte` usa ancora `createEventDispatcher` e `on:click` (Svelte 4). La convention del progetto è "Edit > Rewrite" e "No backward compatibility". Il refactor a Svelte 5 è fuori scope per Step 4 — va segnalato come tech debt.

