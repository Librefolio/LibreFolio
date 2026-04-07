# Plan: Bugfix 4 — Layout Polish, FX Toast Link, GeographyMap i18n, Sync Counts

7 fix da applicare su frontend e backend dopo il completamento dei bugfix 1-3.

---

## Fix 1: Invertire geographic/sector nei grafici classificazione

**File**: `frontend/src/routes/(app)/assets/[id]/+page.svelte` (riga ~972)

Scambiare l'ordine dentro `<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">`: **geographic prima, sector dopo**.

```svelte
                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                {#if geographicDistribution && Object.keys(geographicDistribution).length > 0}
                                    <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                        <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('assetDetail.geoDistribution')}</h5>
                                        <GeographyMap data={geographicDistribution} height="280px"/>
                                    </div>
                                {/if}

                                {#if sectorDistribution && Object.keys(sectorDistribution).length > 0}
                                    <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                        <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('assetDetail.sectorDistribution')}</h5>
                                        <SectorPieChart data={sectorDistribution} height="280px"/>
                                    </div>
                                {/if}
                            </div>
```

---

## Fix 2+3: Bottoni chart → orizzontali a destra + Aesthetics SOPRA il chart

**File**: `frontend/src/routes/(app)/assets/[id]/+page.svelte` e `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

I 3 bottoni (⚙️ Aesthetics, ✏️ Editor, 📏 Measure) vanno posizionati **orizzontali in alto a destra** del chart (come erano prima, stile `absolute top-0 right-0`), e il pannello Aesthetics va renderizzato **sopra** il chart (non sotto). L'ordine dei bottoni è: ⚙️, ✏️, 📏.

**In `assets/[id]/+page.svelte`**, sostituire tutto il blocco `{:else if lineData.length > 0}` (righe ~783-870) con:

```svelte
        {:else if lineData.length > 0}
            <!-- Aesthetics panel (ABOVE chart, shown only when gear is active) -->
            {#if showAesthetics}
                <div data-testid="asset-detail-aesthetics-panel" class="mb-3 pb-3 border-b border-gray-100 dark:border-slate-700">
                    <ChartAestheticsSection
                            colorByBaseline={settings.colorByBaseline}
                            areaFill={settings.areaFill}
                            gridLines={settings.gridLines}
                            staleGradient={settings.staleGradient}
                            yAxisMode={settings.yAxisMode}
                            yAxisMin={settings.yAxisMin}
                            yAxisMax={settings.yAxisMax}
                            onchange={handleAestheticsChange}
                    />
                </div>
            {/if}

            <div class="relative">
                <!-- Right toolbar -->
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <button
                            data-testid="asset-detail-aesthetics-toggle"
                            class="p-1.5 rounded-lg transition-colors {showAesthetics
                            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-300 dark:ring-emerald-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => showAesthetics = !showAesthetics}
                            title={$t('common.aesthetics')}
                    >
                        <Settings size={16}/>
                    </button>
                    <button
                            data-testid="asset-detail-editdata-btn"
                            class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => {
                            if (showDataEditor) {
                                showDataEditor = false;
                                if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; }
                            } else {
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false; showMeasures = false; showSignals = false; showDataEditor = true;
                            }
                        }}
                            title={showDataEditor ? $t('assetDetail.closeEditor') : $t('assetDetail.editData')}
                    >
                        <Pencil size={16}/>
                    </button>
                    <button
                            data-testid="asset-detail-measure-btn"
                            class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={async () => {
                            if (measureMode) { measurePanel?.stopMeasureMode(); }
                            else { showMeasures = true; await tick(); measurePanel?.startMeasureMode(); }
                        }}
                            title={measureMode ? $t('assetDetail.exitMeasure') : $t('assetDetail.addMeasure')}
                    >
                        <Ruler size={16}/>
                    </button>
                </div>

                <PriceChartFull
                        data={lineData}
                        currency={displayCurrency}
                        mainSeriesLabel={assetInfo?.display_name ?? ''}
                        chartHeight="400px"
                        overlaySignals={allOverlaySignals}
                        colorByBaseline={settings.colorByBaseline}
                        areaFill={settings.areaFill}
                        showGridLines={settings.gridLines}
                        showGradient={settings.staleGradient}
                        yAxisMode={settings.yAxisMode}
                        yAxisMin={settings.yAxisMin}
                        yAxisMax={settings.yAxisMax}
                        measureMode={measureMode}
                        onMeasureClick={handleMeasureClick}
                        onMeasureHover={(date, value) => measurePanel?.updatePendingEnd(date, value)}
                        hideToolbar={true}
                        externalViewMode={viewMode}
                        editMode={showDataEditor}
                />
            </div>
```

**In `fx/[pair]/+page.svelte`**, stessa struttura:

```svelte
        {:else if lineData.length > 0}
            <!-- Aesthetics panel (ABOVE chart, shown only when gear is active) -->
            {#if showAesthetics}
                <div data-testid="fx-detail-aesthetics-panel" class="mb-3 pb-3 border-b border-gray-100 dark:border-slate-700">
                    <ChartAestheticsSection
                            colorByBaseline={settings.colorByBaseline}
                            areaFill={settings.areaFill}
                            gridLines={settings.gridLines}
                            staleGradient={settings.staleGradient}
                            yAxisMode={settings.yAxisMode}
                            yAxisMin={settings.yAxisMin}
                            yAxisMax={settings.yAxisMax}
                            onchange={handleAestheticsChange}
                    />
                </div>
            {/if}

            <div class="relative">
                <!-- Right toolbar -->
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <button
                            data-testid="fx-detail-aesthetics-toggle"
                            class="p-1.5 rounded-lg transition-colors {showAesthetics
                            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-300 dark:ring-emerald-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => showAesthetics = !showAesthetics}
                            title={$t('common.aesthetics')}
                    >
                        <Settings size={16}/>
                    </button>
                    <button
                            data-testid="fx-detail-edit-btn"
                            class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => {
                            if (showDataEditor) {
                                showDataEditor = false;
                                pendingPreviewSignal = null;
                                if (savedPanelStates) {
                                    showAesthetics = savedPanelStates.aesthetics;
                                    showMeasures = savedPanelStates.measures;
                                    showSignals = savedPanelStates.signals;
                                    savedPanelStates = null;
                                }
                            } else {
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false;
                                showMeasures = false;
                                showSignals = false;
                                showDataEditor = true;
                            }
                        }}
                            title={showDataEditor ? $t('fxDetail.closeEditor') : $t('fxDetail.editRates')}
                    >
                        <Pencil size={16}/>
                    </button>
                    <button
                            data-testid="fx-detail-measure-btn"
                            class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={async () => {
                            if (measureMode) {
                                measurePanel?.stopMeasureMode();
                            } else {
                                showMeasures = true;
                                await tick();
                                measurePanel?.startMeasureMode();
                            }
                        }}
                            title={measureMode ? $t('fxDetail.exitMeasure') : $t('fxDetail.addMeasure')}
                    >
                        <Ruler size={16}/>
                    </button>
                </div>

                <PriceChartFull
                        data={lineData}
                        currency={displayQuote}
                        mainSeriesLabel={`${baseFlag} ${displayBase} → ${quoteFlag} ${displayQuote}`}
                        chartHeight="400px"
                        overlaySignals={allOverlaySignals}
                        colorByBaseline={settings.colorByBaseline}
                        areaFill={settings.areaFill}
                        showGridLines={settings.gridLines}
                        showGradient={settings.staleGradient}
                        yAxisMode={settings.yAxisMode}
                        yAxisMin={settings.yAxisMin}
                        yAxisMax={settings.yAxisMax}
                        measureMode={measureMode}
                        onMeasureClick={handleMeasureClick}
                        onMeasureHover={(date, value) => measurePanel?.updatePendingEnd(date, value)}
                        hideToolbar={true}
                        externalViewMode={viewMode}
                        editMode={showDataEditor}
                        onPointClick={(date, _value) => fxDataEditorRef?.scrollToDate(date)}
                />
            </div>
```

---

## Fix 4: Tablet-s pulsanti filter bar → impilati verticalmente

**File**: `frontend/src/routes/(app)/assets/[id]/+page.svelte` (riga ~698)

Cambiare la condizione CSS del container bottoni da `flex-row justify-center` a `flex-col items-stretch` per tablet-s:

```svelte
<!-- DA -->
{layout.layoutMode === 'mobile' || layout.layoutMode === 'tablet-s' ? 'flex-row justify-center' : 'grid grid-cols-2'}
<!-- A -->
{layout.layoutMode === 'mobile' || layout.layoutMode === 'tablet-s' ? 'flex-col items-stretch' : 'grid grid-cols-2'}
```

---

## Fix 5: Toast FX con link per aprire add FX pair

**File**: `frontend/src/routes/(app)/assets/[id]/+page.svelte`

Aggiungere un piccolo link `FX →` accanto all'icona ⚠️ che porta alla pagina `/fx` per aggiungere la coppia mancante:

```svelte
                {#if fxConversionMissing}
                    <div class="flex items-center gap-1">
                        <button
                            class="p-1 rounded transition-colors {fxWarningToastVisible
                                ? 'text-amber-300 dark:text-amber-700 cursor-not-allowed opacity-50'
                                : 'text-amber-500 dark:text-amber-400 hover:text-amber-600 dark:hover:text-amber-300 cursor-pointer'}"
                            disabled={fxWarningToastVisible}
                            onclick={showFxWarningToast}
                            title={$t('assetDetail.fxPairMissing', {values: {base: assetInfo.currency, quote: displayCurrency}})}
                        >
                            <AlertTriangle size={16}/>
                        </button>
                        <a href="/fx" class="text-[10px] text-amber-500 dark:text-amber-400 hover:underline" title={$t('assetDetail.addFxPair')}>
                            FX →
                        </a>
                    </div>
                {/if}
```

---

## Fix 6: GeographyMap — traduzione nazioni via backend (Issue 2)

**File**: `frontend/src/lib/components/charts/GeographyMap.svelte`

Il backend ha `GET /api/v1/utilities/countries?language=xx` che restituisce `{iso3, name}` localizzati via Python Babel. Il GeoJSON usa nomi inglesi per le regioni, quindi:
- Continuare a usare nomi inglesi per il rendering della mappa
- Nel **tooltip**, fare reverse lookup nome inglese → ISO A3 → nome localizzato

### 6a — Aggiungere prop `language` e stato per nomi localizzati

```svelte
    interface Props {
        data: Record<string, number>;
        height?: string;
        /** Language code for localized country names (e.g. 'it', 'en') */
        language?: string;
    }

    let {
        data = {},
        height = '320px',
        language = 'en',
    }: Props = $props();

    // ...existing state...
    let localizedNames = $state<Record<string, string>>({});

    // Reverse lookup: English name → ISO A3
    const NAME_TO_ISO_A3: Record<string, string> = {};
    for (const [code, name] of Object.entries(ISO_A3_TO_NAME)) {
        NAME_TO_ISO_A3[name] = code;
    }
```

### 6b — Caricare nomi localizzati dal backend

```typescript
    // Load localized country names from backend
    $effect(() => {
        const lang = language;
        if (lang === 'en') {
            localizedNames = {};  // English names are already in ISO_A3_TO_NAME
            return;
        }
        fetch(`/api/v1/utilities/countries?language=${lang}`)
            .then(r => r.ok ? r.json() : [])
            .then((items: Array<{iso3: string; name: string}>) => {
                const map: Record<string, string> = {};
                for (const item of items) {
                    map[item.iso3] = item.name;
                }
                localizedNames = map;
                // Re-render chart with new names
                renderChart();
            })
            .catch(() => { localizedNames = {}; });
    });
```

### 6c — Usare nomi localizzati nel tooltip

Nel `renderChart()`, aggiornare il tooltip formatter:

```typescript
                formatter: (params: any) => {
                    // Reverse lookup: GeoJSON name → ISO A3 → localized name
                    const iso3 = NAME_TO_ISO_A3[params.name];
                    const displayName = (iso3 && localizedNames[iso3]) || params.name;
                    if (params.value != null && !isNaN(params.value)) {
                        return `${displayName}: ${params.value}%`;
                    }
                    return displayName;
                },
```

### 6d — Passare `language` dal parent

In `assets/[id]/+page.svelte` (riga ~983):

```svelte
<GeographyMap data={geographicDistribution} height="280px" language={$currentLanguage}/>
```

`$currentLanguage` è già un `Readable<string>` importato a riga 40 (`currentLanguage`).

---

## Fix 7: Backend — conteggi sync asset (points_changed sempre = points_fetched)

**File**: `backend/app/services/asset_source.py`

### Root cause

`bulk_upsert_prices` usa strategia DELETE+INSERT (riga 1088): tutte le date vengono cancellate e reinserite. Quindi `inserted_count` è SEMPRE uguale al numero totale di prezzi, anche se identici a quelli già nel DB. `updated_count` è sempre 0 (riga 1139).

Il servizio FX ha la stessa problematica risolta con `_count_actual_changes` (fx.py riga 742) che confronta i valori prima di fare l'upsert.

### Fix

Aggiungere `_count_actual_price_changes` come metodo statico di `AssetSourceManager`, e chiamarlo PRIMA dell'upsert nella funzione `_persist_single`.

**7a — Aggiungere il metodo (prima di `_persist_single`, intorno a riga 1860)**:

```python
    @staticmethod
    async def _count_actual_price_changes(
        session: "AsyncSession",
        asset_id: int,
        price_items: list,  # list[FAPricePoint]
    ) -> tuple[int, int]:
        """
        Compare fetched prices with existing DB prices.
        Returns (new_count, changed_count) — truly new inserts and actual value changes.
        """
        if not price_items:
            return 0, 0

        dates = [p.date for p in price_items]

        # Load existing prices for these dates
        stmt = select(PriceHistory.date, PriceHistory.close).where(
            and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(dates))
        )
        result = await session.execute(stmt)
        existing: dict = {row[0]: row[1] for row in result.all()}

        new_count = 0
        changed_count = 0
        for p in price_items:
            old_close = existing.get(p.date)
            if old_close is None:
                new_count += 1
            elif float(old_close) != float(p.close):
                changed_count += 1

        return new_count, changed_count
```

**7b — Usarlo in `_persist_single` (righe ~1919-1927)**:

Sostituire il blocco try/except che chiama `bulk_upsert_prices`:

```python
            try:
                async with AsyncSession(engine, expire_on_commit=False) as persist_session:
                    # Count actual changes BEFORE upserting (compare with DB)
                    try:
                        new_count, changed_count = await AssetSourceManager._count_actual_price_changes(
                            persist_session, asset_id, price_items
                        )
                    except Exception:
                        new_count, changed_count = fetched_count, 0  # Fallback

                    try:
                        upsert_res = await AssetSourceManager.bulk_upsert_prices(
                            [upsert_obj], persist_session
                            )
                        inserted_count = new_count
                        updated_count = changed_count
                    except Exception as e:
                        errors.append(f"DB upsert failed: {str(e)}")
```

Questo fa sì che alla seconda sync, `points_changed` = `new_count + changed_count` = 0 se i dati sono identici.

---

## Riepilogo file da modificare

| File | Fix |
|------|-----|
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | #1 swap grafici, #2/#3 toolbar destra + aesthetics sopra, #4 tablet-s colonna, #5 link FX, #6 language prop |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | #2/#3 toolbar destra + aesthetics sopra |
| `frontend/src/lib/components/charts/GeographyMap.svelte` | #6 prop language, load nomi backend, tooltip localizzato |
| `backend/app/services/asset_source.py` | #7 `_count_actual_price_changes` + usarla nel sync |

## Ordine di esecuzione

1. Fix 1 — swap grafici (1 riga)
2. Fix 4 — tablet-s pulsanti (1 riga)
3. Fix 5 — link FX nel warning (5 righe)
4. Fix 2+3 — toolbar destra + aesthetics sopra (entrambe le pagine, ~80 righe ciascuna)
5. Fix 6 — GeographyMap i18n (~30 righe + 1 riga nel parent)
6. Fix 7 — backend sync counts (~30 righe)

