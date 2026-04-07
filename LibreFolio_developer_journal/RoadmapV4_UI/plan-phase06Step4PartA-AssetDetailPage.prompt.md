# Plan: Parte A — Asset Detail Page (Skeleton, Chart, Analisi, Azioni)

## Progresso implementazione

| Step | Descrizione | Status |
|------|-------------|--------|
| A1 | `+page.ts` — param validation + redirect | ✅ Completato |
| A2 | Scaffold `+page.svelte` — state, onMount, derived, API calls | ✅ Completato |
| A3 | Header — back button, AssetIcon, badges, identifiers | ✅ Completato |
| A4 | Filter bar responsive + matrice 2×2 + CurrencySearchSelect | ✅ Completato |
| A5 | Chart + pannelli foldable + Data Editor placeholder | ✅ Completato |
| A6 | Event markers su PriceChartFull (scatter series ECharts) | ⏳ Da fare |
| A7 | Auto-sync + Refresh dopo Edit da modale | ✅ Completato |
| A8 | Sezione Metadata (accordion foldable, readonly) | ✅ Completato |
| A9 | `populate_asset_events()` in mock data | ✅ Completato |
| A10 | i18n — chiavi `assetDetail.*` (28 chiavi) | ✅ Completato |
| — | Cleanup: tipi locali → import da `$lib/types/asset` | ✅ Completato |

### Note fuori pista
- `@const` in Svelte template non è ammesso come figlio diretto di `{#if}` a livello di blocco — spostato a `$derived` nel script
- `availableAssets` per `ChartSignalsSection` usa il formato `{id, display_name, ...}` (non `{value, name}`)
- **Tipi duplicati eliminati**: le interfacce locali `AssetInfo` e `ProviderAssignment` in `+page.svelte` sono state sostituite con import da `$lib/types/asset.ts` (derivati da `z.infer<typeof schemas.FAinfoResponse>` e `z.infer<typeof schemas.FAProviderAssignmentReadItem>`). Il cast `(providerAssignment as ProviderAssignment | null)` è stato rimosso perché ora il tipo è corretto nativamente.
- Aggiunto `export type ProviderAssignment` in `$lib/types/asset.ts`
- Eliminata chiave `chartSettings.tooltips.currencyPair` → da rimuovere con `./dev.py i18n remove`
- **i18n formato corretto**: `./dev.py i18n add KEY --en "..." --it "..." --fr "..." --es "..."` (non posizionale)

---

## Risposte ai dubbi dell'utente

1. **Filter bar breakpoints:** Usare le stesse soglie di FX detail (`wide: 730, tablet: 550`) ma via `createResponsiveLayout` (non ResizeObserver inline come in FX detail). Aggiungere il 4° breakpoint `tablet-s` per coerenza col pattern condiviso. Le soglie verranno affinate una volta visto il risultato.

2. **Eventi backend — già implementati?** Il backend ha **già** il supporto per leggere eventi: `POST /assets/prices/query` con `include_events: true` restituisce `FAAssetEventPoint[]` dalla tabella `asset_events`. Gli eventi vengono scritti dai provider durante il sync (es. scheduled_investment genera INTEREST/MATURITY_SETTLEMENT, yfinance genera DIVIDEND). **Non esiste** però un endpoint REST per CRUD eventi manuali — quello è pianificato in Parte B (`POST /assets/events`, `DELETE /assets/events`). Quindi per la Parte A possiamo solo **visualizzare** gli eventi auto-generati dai provider + quelli inseriti manualmente nel populate.

3. **Eventi degli asset in comparazione:** Sì, anche gli event markers degli asset in overlay verranno mostrati. Il loro marker avrà un quadratino di sfondo nel colore del segnale che li importa (colore dall'`AssetComparisonSignal`).

4. **A6 (era A7 nel piano macro) — "ricarica provider":** No, non si ricarica il provider assignment. Si intendeva: (a) ri-carica `FAinfoResponse` (info asset aggiornate), (b) ri-carica `providerAssignment` (potrebbe essere cambiato nell'edit), (c) ri-carica `metadata`, (d) POST sync prezzi, (e) re-query prezzi e eventi per aggiornare il chart.

5. **Chiavi i18n inutilizzate:** Le chiavi dall'audit vanno riutilizzate dove possibile. In particolare: `assets.identifiers.autoFilled` e `assets.identifiers.conflictWarning` nella sezione metadata; `assets.provider.lastFetch` e `assets.provider.neverFetched` nel badge provider; `assets.schedule.*` e `assets.probe.*` non servono nella detail page (restano in AssetModal). `chartSettings.tooltips.currencyPair` → eliminata (sostituita da `tooltips.fxPair`).

6. **Data Editor:** Presente ma disabilitato (pulsante ✏ visibile, pannello con messaggio "Coming in Part B").

7. **CurrencySearchSelect (display currency):** Posizionato nella filter bar a sinistra, dopo il price summary. Per ora solo cosmetico (cambia label, non converte i dati). La conversione backend è Parte C.

---

## Riferimenti chiave

| Concetto | File | Note |
|---|---|---|
| FX detail (reference implementation) | `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (1044 righe) | Pattern completo: header, filter bar, chart, foldable panels, editor, signals |
| FX detail +page.ts | `frontend/src/routes/(app)/fx/[pair]/+page.ts` (30 righe) | Param validation + redirect pattern |
| Asset detail placeholder (da riscrivere) | `frontend/src/routes/(app)/assets/[id]/+page.svelte` (43 righe) | Attualmente solo placeholder Construction |
| Asset list page (signal resolution pattern) | `frontend/src/routes/(app)/assets/+page.svelte` (righe 640-681) | `buildAssetSignals()` con FxPair + AssetComparison resolution |
| Responsive layout helper | `frontend/src/lib/utils/responsiveLayout.svelte.ts` (69 righe) | `createResponsiveLayout({wide, tablet, tabletS, labelHide})` |
| Chart settings store (scoped) | `frontend/src/lib/stores/chartSettingsStore.svelte.ts` | `getSettingsForPair(\`asset-${id}\`, 'assets')` |
| PriceChartFull | `frontend/src/lib/components/charts/PriceChartFull.svelte` (615 righe) | Props: data, overlaySignals, eventMarkers (da aggiungere) |
| AssetComparisonSignal | `frontend/src/lib/charts/signals/AssetComparisonSignal.ts` (97 righe) | `_resolvedData` injection pattern |
| AssetModal | `frontend/src/lib/components/assets/AssetModal.svelte` (1293 righe) | Props: `open`, `editMode`, `editData`, `onupdated` |
| Provider helpers | `frontend/src/lib/utils/providerHelpers.ts` | `assetProviderBadgeHtml()`, `formatProviderText()` |
| Backend FAinfoResponse | `backend/app/schemas/assets.py:817` | id, display_name, currency, icon_url, asset_type, active, provider_code, has_metadata, identifier_* |
| Backend FAProviderAssignmentReadItem | `backend/app/schemas/provider.py:178` | provider_code, identifier, identifier_type, last_fetch_at, user_url |
| Backend FAAssetMetadataResponse | `backend/app/schemas/assets.py:601` | classification_params (short_description, geographic_area, sector_area) |
| Backend FAAssetEventPoint | `backend/app/schemas/prices.py:226` | date, type, value (Currency), notes |
| Backend FAPriceQueryItem | `backend/app/schemas/prices.py:250` | asset_id, date_range, include_events |
| Backend AssetEventType enum | `backend/app/db/models.py:180` | DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT, MATURITY_SETTLEMENT |
| Populate mock data | `backend/test_scripts/test_db/populate_mock_data.py` (1566 righe) | Nessun `populate_asset_events()` — da aggiungere |
| CurrencySearchSelect | `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte` (203 righe) | value bindable, allowedCurrencies, compact |

---

## Steps

### A1. Creare `+page.ts`

**File:** `frontend/src/routes/(app)/assets/[id]/+page.ts` (nuovo)

- `parseInt(params.id)` → redirect a `/assets` se `isNaN` o ≤ 0
- Ritorna `{ assetId: number }`
- `prerender = false`, `csr = true`

```typescript
import { redirect } from '@sveltejs/kit';

export const prerender = false;
export const csr = true;

export async function load({ params }: { params: { id: string } }) {
    const assetId = parseInt(params.id, 10);
    if (isNaN(assetId) || assetId <= 0) {
        throw redirect(302, '/assets');
    }
    return { assetId };
}
```

---

### A2. Scaffold `+page.svelte` — State + onMount + Derived

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (riscrittura completa)

**Props:**
```typescript
interface Props {
    data: { assetId: number };
}
let { data }: Props = $props();
```

**State:**
- `assetInfo: FAinfoResponse | null` — info asset
- `providerAssignment: FAProviderAssignmentReadItem | null` — provider config
- `metadata: FAAssetMetadataResponse | null` — classification metadata
- `chartData: FAPricePoint[]` — dati prezzi raw
- `events: FAAssetEventPoint[]` — eventi asset (main)
- `comparisonEvents: Map<number, FAAssetEventPoint[]>` — eventi asset in comparazione
- `loading`, `error: string | null`, `syncing`
- `dateStart`, `dateEnd`, `activePreset` — date range (default 3M)
- `viewMode: ViewMode` — `'absolute'` | `'percentage'`
- `displayCurrency: string` — inizializzato a `assetInfo.currency` (per CurrencySearchSelect, cosmetico per ora)
- Foldable: `showAesthetics`, `showMeasures`, `showSignals`, `showDataEditor`
- `layoutMode` via `createResponsiveLayout`
- `measureMode`, `measureSignals`, `measurePanel`
- `pendingPreviewSignal` (per data editor futuro)
- `overlayDataVersion` (trigger recomputation)
- `editModalOpen`, `editModalData` — per AssetModal
- `allConfiguredFxSlugs: string[]` — per FxPair signal dropdown
- `allAssets: Array<{id, display_name, icon_url, asset_type}>` — per AssetComparison dropdown

**onMount — parallel loading:**
```typescript
onMount(async () => {
    await Promise.all([
        ensureCurrenciesLoaded(get(currentLanguage)),
        loadAssetInfo(),
        loadProviderAssignment(),
        loadChartData(),      // POST /assets/prices/query con include_events: true
        loadMetadata(),
        loadFxPairSlugs(),    // per overlay dropdown
        loadAssetList(),      // per comparison dropdown
    ]);
});
```

**API calls:**
1. `loadAssetInfo()` — `GET /assets/all` → filtra per `data.assetId` → `assetInfo`. Poi `displayCurrency = assetInfo.currency`
2. `loadProviderAssignment()` — `zodiosApi.list_provider_assignments_..._get({ asset_ids: String(data.assetId) })` → `providerAssignment`
3. `loadChartData()` — `zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post([{ asset_id: data.assetId, date_range: { start: dateStart, end: dateEnd }, include_events: true }])` → `chartData = result.prices`, `events = result.events`
4. `loadMetadata()` — `GET /assets/metadata?asset_ids={id}` → `metadata`
5. `loadFxPairSlugs()` — `zodiosApi.list_routes_api_v1_fx_providers_routes_get()` → extract unique slugs → `allConfiguredFxSlugs`
6. `loadAssetList()` — `zodiosApi.list_assets_api_v1_assets_all_get()` → map to `{id, display_name, icon_url, asset_type}` → `allAssets`

**Key derived:**
```typescript
let lineData: LineDataPoint[] = $derived(chartData.map(p => ({
    date: p.date,
    value: Number(p.close),
    staleDays: p.backward_fill_info?.days_back ?? 0,
})));

let settings = $derived(getSettingsForPair(`asset-${data.assetId}`, 'assets'));
let signals = $derived<SignalConfig[]>([...settings.signals]);

let isScheduledInvestment = $derived(
    providerAssignment?.provider_code === 'scheduled_investment'
);
let isManualOnly = $derived(!providerAssignment);

let lastPrice = $derived.by(() => { /* last chartData point → close */ });
let deltaPercent = $derived.by(() => { /* ((last-first)/first)*100 */ });
let deltaAbs = $derived.by(() => { /* last - first */ });

let overlaySignals: RenderedSignal[] = $derived.by(() => {
    // Same pattern as assets/+page.svelte L640-681
    // Resolve FxPairSignal from FxStores
    // Resolve AssetComparisonSignal from allAssets data + loadComparisonData
});

let allOverlaySignals = $derived([
    ...overlaySignals,
    ...measureSignals,
    ...(pendingPreviewSignal ? [pendingPreviewSignal] : []),
]);

// Event markers: main asset + comparison assets
let eventMarkers = $derived.by(() => {
    const markers = [];
    // Main asset events
    for (const evt of events) {
        markers.push({
            date: evt.date,
            type: evt.type,
            value: Number(evt.value.amount),
            currency: evt.value.code,
            notes: evt.notes ?? undefined,
        });
    }
    // Comparison asset events (with signalColor)
    for (const cfg of signals) {
        if (cfg.signalType !== 'asset-comparison') continue;
        const targetId = Number(cfg.params.assetId);
        const targetEvents = comparisonEvents.get(targetId);
        if (!targetEvents?.length) continue;
        const instance = signalFromConfig(cfg);
        const color = instance?.style.color ?? '#888';
        const targetAsset = allAssets.find(a => a.id === targetId);
        for (const evt of targetEvents) {
            markers.push({
                date: evt.date,
                type: evt.type,
                value: Number(evt.value.amount),
                currency: evt.value.code,
                notes: evt.notes ?? undefined,
                assetLabel: targetAsset?.display_name ?? `Asset #${targetId}`,
                signalColor: color,
            });
        }
    }
    return markers;
});
```

---

### A3. Header

Layout (flexbox, gap-3):
```
[← Back] [AssetIcon] [display_name] [badge TYPE] [🇺🇸 USD] [AAPL] [badge yfinance]
```

- Back button: `goto('/assets')` con titolo `$t('assetDetail.backToList')`
- `AssetIcon`: component esistente con `src={assetInfo.icon_url}` e fallback tipo
- `display_name` in `h2.text-xl.font-bold`
- Badge tipo: pill con icona da `ASSET_TYPE_ICON_MAP` + label localizzata
- Flag emoji + currency code (da `getCurrencyInfo`)
- Identificatore principale: `identifier_ticker ?? identifier_isin ?? identifier_cusip ?? ...` in mono font
- Badge provider: icona + nome da `providerHelpers.assetProviderBadgeHtml()` (o inline se preferisci non usare innerHTML)

---

### A4. Filter Bar responsive + Matrice 2×2 + CurrencySearchSelect

**Responsive layout:**
```typescript
const layout = createResponsiveLayout({
    wide: 730,     // stesse soglie FX detail
    tablet: 550,
    tabletS: 400,
    labelHide: 500,
});
$effect(() => {
    const el = filterBarRef;
    if (!el) return;
    layout.attach(el);
    return () => layout.detach();
});
```

**Layout wide (≥730px):**
```
[ DateRangePicker | CurrencySelect | price-summary ─── actions-2×2 ]
```

**Layout tablet (550-729px):**
```
[ DateRangePicker  CurrencySelect ]  [ actions-2×2 ]
[ price-summary                   ]  [             ]
```

**Layout mobile (<400px):**
```
[ DateRangePicker       ]
[ CurrencySelect        ]
[ price-summary         ]
[ actions-row           ]
```

**CurrencySearchSelect:**
```svelte
<CurrencySearchSelect
    bind:value={displayCurrency}
    compact={true}
    placeholder={$t('assetDetail.displayCurrency')}
/>
```
- Per ora **cosmetico**: `displayCurrency` viene mostrato nel label del chart e nel summary. Nessuna conversione API.
- In Parte C: `displayCurrency` verrà passato come `target_currency` alla query prezzi.

**Matrice 2×2 actions** (stessa struttura esatta di FX detail righe 689-739):
- `[Abs | %]` segmented toggle
- `[✏ Edit]` → `editModalOpen = true; editModalData = buildEditData(assetInfo, providerAssignment, metadata);`
- `[⟳ Sync]` / `[Recalculate]`:
  - Label: `isScheduledInvestment ? $t('assetDetail.recalculate') : $t('common.sync')`
  - Disabled: `syncing || isManualOnly`
  - Action: `handleSync()` → `zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([{ asset_id: data.assetId, start_date: dateStart, end_date: dateEnd }])`
- `[↻ Refresh]` → `handleRefresh()` → re-query prezzi + eventi

---

### A5. Chart + Pannelli Foldable + Data Editor placeholder

**Chart area:**
```svelte
<PriceChartFull
    data={lineData}
    currency={displayCurrency}
    mainSeriesLabel={assetInfo?.display_name ?? ''}
    chartHeight="400px"
    overlaySignals={allOverlaySignals}
    eventMarkers={eventMarkers}
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
```

**Overlay buttons** (top-right chart, identico FX detail righe 787-835):
- 📐 Measure toggle
- ✏ Edit data toggle

**Foldable panels (top → bottom):**

1. **ChartAestheticsSection** (sopra chart) — identico FX detail
2. **Data Editor placeholder** (sotto chart):
   ```svelte
   {#if showDataEditor}
       <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-800">
           <div class="flex items-center justify-between px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-yellow-900/30 rounded-t-xl">
               <span class="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
                   <Pencil size={15}/>
                   {$t('assetDetail.editData')}
               </span>
               <button onclick={() => showDataEditor = false}>✕</button>
           </div>
           <div class="px-4 py-8 text-center">
               <Construction class="text-amber-400 mx-auto mb-2" size={32}/>
               <p class="text-sm text-gray-500">{$t('assetDetail.editDataComingSoon')}</p>
           </div>
       </div>
   {/if}
   ```
3. **MeasurePanel** (sotto editor) — identico FX detail
4. **ChartSignalsSection** (sotto measures):
   ```svelte
   <ChartSignalsSection
       signals={[...signals]}
       availablePairs={allConfiguredFxSlugs}
       availableAssets={allAssets.filter(a => a.id !== data.assetId).map(a => ({
           value: String(a.id), name: a.display_name, icon_url: a.icon_url, asset_type: a.asset_type
       }))}
       mainPairSlug={`asset-${data.assetId}`}
       onchange={handleSignalsChange}
   />
   ```

**Empty states:**
- No provider + no data: "No provider configured — set one up via Edit" + button → open AssetModal
- Has provider, no data: "No price data yet — try Sync" + Sync button
- Scheduled investment, no schedule: "Configure interest schedule in Edit" + button → open AssetModal

---

### A6. Event Markers sul Chart

**Modifica a `PriceChartFull.svelte`:**

Aggiungere prop:
```typescript
interface Props {
    // ...existing props...
    /** Event markers (dividends, interest, splits, etc.) */
    eventMarkers?: EventMarker[];
}

interface EventMarker {
    date: string;
    type: string;           // AssetEventType: DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT, MATURITY_SETTLEMENT
    value: number;
    currency: string;
    notes?: string;
    assetLabel?: string;    // presente solo per eventi di asset in comparazione
    signalColor?: string;   // colore del segnale overlay (per eventi comparison)
}
```

**Implementazione ECharts:**
- Per ogni `eventMarkers` entry, creare un punto nella scatter series corrispondente al tipo.
- **Y positioning:** cercare il `lineData` point con data più vicina all'evento, usare quel valore Y. Fallback: media dei valori Y min/max.
- **Raggruppamento:** una scatter series per tipo evento (colore uniforme per tipo).
- **Rendering:**
  ```javascript
  // Per ogni tipo evento presente:
  {
      type: 'scatter',
      name: `Events: ${eventType}`,
      data: markersOfType.map(m => [m.date, yValueAtDate]),
      symbol: 'diamond',
      symbolSize: m.signalColor ? 10 : 12,  // più piccolo per comparison
      itemStyle: {
          color: EVENT_COLORS[m.type],
          borderColor: m.signalColor ?? EVENT_COLORS[m.type],
          borderWidth: m.signalColor ? 2 : 0,
      },
      z: 20,  // sopra la linea principale
  }
  ```
- **Colori per tipo (costanti):**
  ```typescript
  const EVENT_COLORS: Record<string, string> = {
      INTEREST: '#10b981',            // emerald-500
      DIVIDEND: '#3b82f6',            // blue-500
      PRICE_ADJUSTMENT: '#f59e0b',    // amber-500
      MATURITY_SETTLEMENT: '#ef4444', // red-500
      SPLIT: '#8b5cf6',              // violet-500
  };
  ```
- **Tooltip formatter:** badge colorato con tipo, valore formattato `{amount} {currency}`, notes se presente, `assetLabel` se comparison event.

---

### A7. Auto-sync + Refresh dopo Edit da modale

```typescript
async function handleAssetUpdated() {
    editModalOpen = false;
    // 1. Reload asset info (name, currency, type may have changed)
    await loadAssetInfo();
    // 2. Reload provider assignment (may have been added/changed/removed)
    await loadProviderAssignment();
    // 3. Reload metadata (classification may have changed)
    await loadMetadata();
    // 4. Sync prices if provider exists
    if (providerAssignment) {
        await handleSync();  // includes toast + refresh
    } else {
        // No provider — just refresh from DB
        await handleRefresh();
    }
}
```

```svelte
<AssetModal
    bind:open={editModalOpen}
    editMode={true}
    editData={editModalData}
    onupdated={handleAssetUpdated}
    onclose={() => editModalOpen = false}
/>
```

---

### A8. Sezione Metadata (accordion foldable, readonly)

Pannello foldable in fondo alla pagina, **collassato di default**.

```svelte
<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
    <button class="w-full flex items-center justify-between px-4 py-2.5 ..."
            onclick={() => showMetadata = !showMetadata}>
        <span class="flex items-center gap-2">
            <Info size={15}/> {$t('assetDetail.metadata')}
        </span>
        <ChevronDown class="transition-transform {showMetadata ? 'rotate-180' : ''}" size={15}/>
    </button>
    {#if showMetadata}
        <div class="px-4 pb-4 border-t ... space-y-4">
            <!-- Identifiers grid -->
            <!-- Short description -->
            <!-- Sector distribution (tag pills with %) -->
            <!-- Geographic distribution (flag + country + %) -->
            <!-- "Edit via modal" link -->
        </div>
    {/if}
</div>
```

**Contenuto:**
- **Identifiers:** griglia 2 colonne `[tipo | valore]` per ogni `identifier_*` non-null di `assetInfo`
- **Short description:** testo da `metadata.classification_params.short_description`
- **Sector distribution:** tag pills con percentuali (es. "💻 Technology 45%", "🏦 Financials 30%"), da `classification_params.sector_area.distribution`
- **Geographic distribution:** tag pills con flag emoji + codice paese + % (es. "🇺🇸 USA 60%"), da `classification_params.geographic_area.distribution`
- **"Edit" link:** bottone che apre AssetModal in editMode

Riutilizzare chiavi i18n esistenti:
- `assets.provider.lastFetch` / `assets.provider.neverFetched` — per badge provider nel header
- `assets.identifiers.autoFilled` — label per identificatori auto-compilati dal provider

---

### A9. `populate_asset_events()` in mock data

**File:** `backend/test_scripts/test_db/populate_mock_data.py`

Creare funzione `populate_asset_events(session)`:

```python
def populate_asset_events(session: Session):
    """Create asset events for testing event markers on charts."""
    print("\n📅 Creating Asset Events...")
    print("-" * 60)

    today = date.today()

    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    vwce = session.exec(select(Asset).where(Asset.display_name == "Vanguard FTSE All-World UCITS ETF")).first()
    loan1 = session.exec(select(Asset).where(Asset.display_name == "Real Estate Loan - Milano Centro")).first()
    loan2 = session.exec(select(Asset).where(Asset.display_name == "Real Estate Loan - Roma Parioli")).first()

    events_data = []

    # Apple — quarterly dividends
    if apple:
        for days_ago, amount in [(90, "0.24"), (180, "0.24"), (270, "0.25")]:
            events_data.append(AssetEvent(
                asset_id=apple.id,
                date=today - timedelta(days=days_ago),
                type=AssetEventType.DIVIDEND,
                value=Decimal(amount),
                currency="USD",
                notes=f"Quarterly dividend",
            ))

    # VWCE — semi-annual dividends
    if vwce:
        for days_ago, amount in [(120, "0.52"), (300, "0.48")]:
            events_data.append(AssetEvent(
                asset_id=vwce.id,
                date=today - timedelta(days=days_ago),
                type=AssetEventType.DIVIDEND,
                value=Decimal(amount),
                currency="EUR",
                notes="Distribution",
            ))

    # Loan Milano — interest payments + haircut
    if loan1:
        for days_ago, amount in [(30, "25.00"), (60, "25.00"), (90, "25.00"), (120, "25.50")]:
            events_data.append(AssetEvent(
                asset_id=loan1.id,
                date=today - timedelta(days=days_ago),
                type=AssetEventType.INTEREST,
                value=Decimal(amount),
                currency="EUR",
                notes="Monthly interest",
            ))
        events_data.append(AssetEvent(
            asset_id=loan1.id,
            date=today - timedelta(days=45),
            type=AssetEventType.PRICE_ADJUSTMENT,
            value=Decimal("-200.00"),
            currency="EUR",
            notes="Haircut Q3 — collateral revaluation",
        ))

    # Loan Roma — maturity settlement
    if loan2:
        events_data.append(AssetEvent(
            asset_id=loan2.id,
            date=today - timedelta(days=15),
            type=AssetEventType.MATURITY_SETTLEMENT,
            value=Decimal("10000.00"),
            currency="EUR",
            notes="Final capital return at maturity",
        ))

    for evt in events_data:
        session.add(evt)
        print(f"  ✅ Asset #{evt.asset_id} — {evt.type} {evt.value} {evt.currency} ({evt.date})")

    session.commit()
    print(f"\n  📊 Total: {len(events_data)} events created")
```

**Chiamata in `main()`:** dopo `populate_price_history(session)`, prima di `populate_fx_rates(session)`:
```python
populate_price_history(session)
populate_asset_events(session)   # ← NEW
populate_fx_rates(session)
```

---

### A10. i18n — Nuove chiavi `assetDetail.*`

Chiavi da creare via `./dev.py i18n add`:

```
assetDetail.backToList          = "Back to Assets"
assetDetail.loadingPrices       = "Loading prices..."
assetDetail.noData              = "No price data available for this range."
assetDetail.noDataManual        = "No provider configured — set one up via Edit"
assetDetail.noDataScheduled     = "Configure interest schedule via Edit to generate prices"
assetDetail.syncPrices          = "Sync Prices"
assetDetail.recalculate         = "Recalculate"
assetDetail.syncDisabledManual  = "Sync disabled — no provider configured"
assetDetail.measures            = "Measures"
assetDetail.signals             = "Signals"
assetDetail.editData            = "Edit Prices & Events"
assetDetail.editDataComingSoon  = "Data editing will be available in a future update"
assetDetail.closeEditor         = "Close editor"
assetDetail.exitMeasure         = "Exit measure mode"
assetDetail.addMeasure          = "Add measurement"
assetDetail.metadata            = "Metadata & Classification"
assetDetail.identifiers         = "Identifiers"
assetDetail.classification      = "Classification"
assetDetail.sectorDistribution  = "Sector Distribution"
assetDetail.geoDistribution     = "Geographic Distribution"
assetDetail.editViaModal        = "Edit in asset modal"
assetDetail.displayCurrency     = "Display currency"
assetDetail.syncSuccess         = "Prices synced: {fetched}↓ {changed}Δ"
assetDetail.syncFailed          = "Sync failed"
assetDetail.syncPartial         = "Partial sync: {fetched}↓ {changed}Δ"
assetDetail.noIdentifiers       = "No identifiers configured"
assetDetail.noClassification    = "No classification data"
assetDetail.eventMarkers        = "Event Markers"
```

Riutilizzare chiavi esistenti:
- `common.sync`, `common.refresh`, `common.aesthetics`, `common.close`, `common.cancel`
- `measure.active`
- `assets.schedule.eventType.*` (INTEREST, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT)
- `assets.provider.lastFetch`, `assets.provider.neverFetched`

Eliminare chiave unused:
- `chartSettings.tooltips.currencyPair` (sostituita da `chartSettings.tooltips.fxPair`)

---

## Ordine di implementazione consigliato

```
A1 (+page.ts)
 └→ A2 (scaffold + state + onMount)
     └→ A3 (header)
     └→ A4 (filter bar + actions + CurrencySearchSelect)
     └→ A5 (chart + foldable panels + editor placeholder)
         └→ A9 (populate_asset_events — per testare subito)
         └→ A6 (event markers su PriceChartFull)
     └→ A7 (auto-sync dopo edit)
     └→ A8 (metadata section)
A10 (i18n — in parallelo ad ogni step, man mano che servono)
```

---

## Dipendenze da altre Parti

- **Parte B** (Data Editor): A5 predispone il placeholder. Una volta implementato B, si sostituisce il placeholder con `AssetDataEditorSection`.
- **Parte C** (Currency Conversion): A4 predispone il `CurrencySearchSelect` con `displayCurrency`. Una volta implementato C, si aggiunge `target_currency` alla query prezzi e la conversione diventa reale.

---

## Checklist di Validazione — Parte A

### Pre-requisiti
- [x] DB test popolato: `./dev.py test db populate --force`
- [x] Server avviato: `./dev.py server --test`
- [x] Frontend dev: `./dev.py front dev`

### A1 — `+page.ts` (Param Validation)
- [x] Navigare a `/assets/abc` → redirect a `/assets`
- [x] Navigare a `/assets/-1` → redirect a `/assets`
- [x] Navigare a `/assets/0` → redirect a `/assets`
- [x] Navigare a `/assets/1` → carica la pagina

### A2 — Scaffold (State + API calls)
- [x] La pagina carica senza errori nella console
- [x] `assetInfo` viene popolato (nome e currency visibili)
nell'header c'è anche il provider usato, ma solo come nome, vorrei anche qui icona e nome, in oltre nell'header sarebbe utile aver il link all'url esterno messo dall'utente, se assete fallback su quello del provider, se assente, non mostrare il bottone
- [x] `chartData` viene caricato (chart visibile con dati mock)
- [x] `providerAssignment` caricato per asset con provider
- [x] `allConfiguredFxSlugs` caricato (verificare in Signals → FxPair dropdown)
- [x] `allAssets` caricato (verificare in Signals → AssetComparison dropdown)

### A3 — Header
- [x] Back button `←` torna a `/assets`
- [ ] `AssetIcon` mostra icona o fallback tipo
il fall back si mostra ma se vado su edit e clicco l'icona non si apre l'image picker, ed in oltre non riesco a chiudere più la modale, devo fare f5
- [x] Nome asset in `h2` bold
- [x] Badge tipo (es. "STOCK", "ETF", "LOAN") con icona tipo
- [x] Flag emoji + codice currency (es. 🇺🇸 USD)
si ma farei si che in modalità mobile tutta la riga andasse sotto al nome assieme, non che va a capo come ora che è flex
- [x] Identificatore principale visibile (ticker > ISIN > CUSIP > ...)
l'indentificatore penso sia inutile, meglio mettere il link alla pagina esterna se cè
- [x] Badge provider visibile (es. "yfinance") se presente
come scritto sopra, vorrei anche l'icona assieme al nome
- [x] Asset senza provider: nessun badge provider mostrato
L'url utente deve essere tra le opzioni base dell'add asset, non nel panel dei provider, così che si possa inserire anche nei provider manuali. Di conseguenza, anche a db, l'user_url non è un campo dentro il provider, ma una colonna tra gli asset.

### A4 — Filter Bar + Actions 2×2
- [x] DateRangePicker funzionante, default 3M
- [x] Cambiare range → chart si aggiorna
- [x] CurrencySearchSelect visibile, default = currency asset
si ma lo invertieri con il Price summary, e sopra il bottone aggiungerei una label che faccia capire che serve per convertire la valuta degli asset presenti nel diagramma, e bisogna prevedere che se un asset selezionato ha una valuta non convertibile, compaia un warning che dica che manca la conversione e che si può risolvere aggiungendo quella tratta, aprendo la modale dell'add forex pair e la scelta del provider.
- [x] Price summary: ultimo prezzo, Δ%, Δabs visibili
- [x] Segmented toggle `Abs | %` cambia `viewMode` del chart
- [x] Bottone Edit `✏` → apre AssetModal
ma come detto, poi non si chiude più, e se si deseleziona un "no provider" non succede comunque nulla
- [x] Bottone Sync `⟳`:
  - [-] Label "Recalculate" per scheduled_investment
  no, compare sincronizza ed è anche in readonly, non calcola i punti e se ci entro dentro dice pure "Nessun provider configurato — configura tramite Modifica"
  - [x] Label "Sync" per altri provider
  - [x] Disabilitato se no provider (`opacity-50 cursor-not-allowed`)
  - [x] Tooltip "Sync disabled" se no provider
  - [x] Animazione spin durante sync
- [-] Bottone Refresh `↻` → ri-carica dati, spin durante loading
un pacchetto di query parte, però non gira, e mi pare che non lo facesse neanche in asset, fx e fx/detail, aggiungi a tutti la rotazione oraria se manca
- [x] **Responsive** — ridimensionare finestra:
  - [x] Wide (≥730px): tutto in una riga
  - [x] Tablet (550-729px): filtri e azioni su 2 righe
  - [x] Mobile (<400px): tutto verticale centrato
Le soglie sono da aggiustare ma facciamolo quando troviamo il layout definitivo

### A5 — Chart + Pannelli Foldable
- [x] **Chart visibile** con dati prezzo, linea e area
- [x] **Chart settings** funzionanti (colorByBaseline, areaFill, gridLines, staleGradient, yAxis)
- [x] **Pannello Aesthetics** (sopra chart):
  - [x] Toggle apre/chiude con chevron animato
  - [x] Modifiche estetiche si applicano al chart
- [x] **Pulsante 📐 Measure** (overlay chart):
  - [x] Click attiva measure mode
  - [x] Pannello Measures si apre automaticamente
  - [x] Click su chart aggiunge punto di misura
  - [x] Re-click disattiva measure mode
- [x] **Pulsante ✏ Edit Data** (overlay chart):
  - [x] Click apre pannello Data Editor placeholder
  - [x] Salva/ripristina stato pannelli precedenti
  - [x] Re-click chiude editor e ripristina pannelli
- [x] **Data Editor placeholder**:
  - [x] Icona Construction + messaggio "coming in future update"
  - [x] Pulsante ✕ chiude il pannello
- [x] **Pannello Measures** (sotto chart):
  - [x] Toggle apre/chiude
  - [x] Badge "active" visibile durante measure mode
  - [x] MeasurePanel funzionante (aggiungi/rimuovi misure)
- [x] **Pannello Signals** (sotto measures):
  - [x] Toggle apre/chiude
  - [x] ChartSignalsSection con dropdown per FxPair e AssetComparison
  - [x] Aggiungere un segnale EMA → visibile sul chart
  - [x] Aggiungere FxPair signal → carica dati e mostra overlay
  - [x] Aggiungere AssetComparison → carica dati e mostra overlay
- [x] **Empty states**:
  - [x] Asset senza provider e senza dati → "No provider configured — set one up via Edit" + bottone Edit
  - [x] Scheduled investment senza dati → "Configure interest schedule via Edit" + bottone Edit
  - [x] Asset con provider ma senza dati → "No price data" + bottone Sync

### A6 — Event Markers (⏳ DA FARE)
- [ ] Prop `eventMarkers` su PriceChartFull
- [ ] Scatter series su chart con diamanti colorati per tipo
- [ ] Colori: 🟢 INTEREST, 🔵 DIVIDEND, 🟡 PRICE_ADJUSTMENT, 🔴 MATURITY_SETTLEMENT, 🟣 SPLIT
- [ ] Tooltip: tipo, valore, currency, notes
- [ ] Marker per comparison assets con bordo nel colore del segnale
- [ ] **Test con mock data**: Apple (dividendi), Loan Milano (interest + haircut), Loan Roma (maturity)

### A7 — Auto-sync dopo Edit
- [ ] Aprire AssetModal via bottone Edit → modificare qualcosa → Save
- [ ] Dopo save: asset info si aggiorna (nome, currency, etc.)
- [ ] Se ha provider: sync automatico + toast con risultato
- [ ] Se no provider: solo refresh dal DB
- [ ] Modal si chiude dopo update
come detto sopra, si apre ma poi non si riesce a fare nulla, si blocca dall'edit in poi
questo è l'errore in console:
errors.js:228 Uncaught Error: https://svelte.dev/e/effect_update_depth_exceeded
    at effect_update_depth_exceeded (errors.js:228:9)
    at infinite_loop_guard (batch.js:629:3)
    at flush_effects (batch.js:601:5)
    at Batch.flush (batch.js:315:4)
    at Array.<anonymous> (batch.js:485:12)
    at run_all (utils.js:45:8)
    at run_micro_tasks (task.js:10:2)
    at task.js:28:31
effect_update_depth_exceeded @ errors.js:228
infinite_loop_guard @ batch.js:629
flush_effects @ batch.js:601
flush @ batch.js:315
(anonymous) @ batch.js:485
run_all @ utils.js:45
run_micro_tasks @ task.js:10
(anonymous) @ task.js:28
errors.js:228 Uncaught Error: https://svelte.dev/e/effect_update_depth_exceeded
    at effect_update_depth_exceeded (errors.js:228:9)
    at infinite_loop_guard (batch.js:629:3)
    at flush_effects (batch.js:601:5)
    at Batch.flush (batch.js:315:4)
    at Array.<anonymous> (batch.js:485:12)
    at run_all (utils.js:45:8)
    at run_micro_tasks (task.js:10:2)
    at task.js:28:31
effect_update_depth_exceeded @ errors.js:228
infinite_loop_guard @ batch.js:629
flush_effects @ batch.js:601
flush @ batch.js:315
(anonymous) @ batch.js:485
run_all @ utils.js:45
run_micro_tasks @ task.js:10
(anonymous) @ task.js:28
debug.ts:45 [API] GET /api/v1/assets/provider
debug.ts:45 [API] GET /api/v1/assets/provider
debug.ts:45 [API] GET /api/v1/utilities/sectors
debug.ts:45 [API] GET /api/v1/utilities/countries
debug.ts:45 [API] GET /api/v1/assets/provider
errors.js:228 Uncaught (in promise) Error: https://svelte.dev/e/effect_update_depth_exceeded
    at effect_update_depth_exceeded (errors.js:228:9)
    at infinite_loop_guard (batch.js:629:3)
    at flush_effects (batch.js:601:5)
    at Batch.flush (batch.js:315:4)
    at Array.<anonymous> (batch.js:485:12)
    at run_all (utils.js:45:8)
    at run_micro_tasks (task.js:10:2)
    at flush_tasks (task.js:40:3)
    at flushSync (batch.js:541:4)
    at tick (runtime.js:497:2)
effect_update_depth_exceeded @ errors.js:228
infinite_loop_guard @ batch.js:629
flush_effects @ batch.js:601
flush @ batch.js:315
(anonymous) @ batch.js:485
run_all @ utils.js:45
run_micro_tasks @ task.js:10
flush_tasks @ task.js:40
flushSync @ batch.js:541
tick @ runtime.js:497
await in tick
(anonymous) @ ModalBase.svelte:65
untrack @ runtime.js:740
(anonymous) @ effects.js:315
update_reaction @ runtime.js:260
update_effect @ runtime.js:453
#traverse_effect_tree @ batch.js:245
process @ batch.js:165
flush_effects @ batch.js:604
flush @ batch.js:315
(anonymous) @ batch.js:485
run_all @ utils.js:45
run_micro_tasks @ task.js:10
(anonymous) @ task.js:28
debug.ts:45 [API] GET /api/v1/assets/query


### A8 — Metadata Section
- [x] Sezione collassata di default
- [x] Click espande con animazione chevron
- [x] **Identifiers**: griglia con tipo+valore per ogni identifier non-null
- [x] Se nessun identifier → "No identifiers configured"
- [x] **Classification**: "Classification data available — view full details via Edit modal" se `has_metadata`
- [x] Se no metadata → "No classification data"
- [x] **Provider info**: nome, identifier, identifier_type, lastFetch o "never fetched"
- [x] **Link "Edit in asset modal"** → apre AssetModal
Lavorerei un attimo sull'estetica, trasformerei il diagramma di distribuzione dei settori in un grafico a torta, mentre quello con le aree geografice in un planisfero con le nazioni presenti colorate con vari livelli di intensità di colore. Entrembi questi diagrammi li farei come funzioni helper perchè serviranno anche nella dashboard. Anche qui vorrei icona e nome del provider, e gli identifier li metterei nascosti in basso, non sono tanto importanti, in alto metterei url utente e url provider.

### A9 — Mock Data Events
- [x] Dopo `./dev.py test db populate`: verificare che eventi esistano nel DB
- [x] Apple: 3 dividendi trimestrali USD
- [x] VWCE: 2 distribuzioni semestrali EUR
- [x] Loan Milano: 4 interessi mensili + 1 haircut
- [x] Loan Roma: 1 maturity settlement
si ma servirebbero anche degli asset con scheduled_investment come provider e anche con css_scraber

### A10 — i18n (28 chiavi)
- [x] `./dev.py i18n tree assetDetail` mostra 28 chiavi
- [x] Cambiare lingua (IT, FR, ES) → tutte le label nella pagina tradotte
- [x] Nessun testo hardcoded in inglese nel template (eccetto "Abs", "%" nei toggle)
- [x] Chiave `chartSettings.tooltips.currencyPair` eliminata (se non ancora fatto: `./dev.py i18n remove chartSettings.tooltips.currencyPair`)

### Controlli Generali
- [x] **Dark mode**: tutti i pannelli, header, filter bar, empty states leggibili in dark
- [x] **No errori console** durante navigazione e interazione
- [x] **`svelte-check` pulito**: `./dev.py front check` senza errori rilevanti
- [x] **Tipi corretti**: nessuna interfaccia locale duplicata — tutti i tipi da `$lib/types/asset` e `generated.ts`
- [x] **Nessun `as any` evitabile**: verificare che i cast `as any` siano solo per API response parsing (Zodios)

