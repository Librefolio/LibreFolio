# Plan: Bugfix 7 — Event Markers + FX Auto-Sync + Yahoo Sector Mapping + AssetModal Polish

## Contesto

Leggere prima `knowledge_base/00_project_overview.md` e poi `knowledge_base/02_frontend.md`.

Siamo nella **Phase 06 Step 4 Part A** del progetto LibreFolio — asset detail page e polish responsive.
Le sessioni precedenti (Bugfix 1–6) hanno risolto la maggior parte dei problemi. Restano due feature incomplete, il mapping dei settori Yahoo Finance, e alcune rifiniture nella modale asset.

### File chiave da leggere prima di implementare
- `backend/app/utils/sector_fin_utils.py` — enum `FinancialSector` + alias mapping + `normalize_sector()` + `validate_sector()`
- `backend/app/services/asset_source_providers/yahoo_finance.py` — `fetch_asset_metadata()` con settori
- `backend/test_scripts/test_utilities/test_sector_normalization.py` — test per settori
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` — pagina asset detail
- `frontend/src/lib/components/charts/PriceChartFull.svelte` — componente chart
- `frontend/src/lib/components/fx/FxPairAddModal.svelte` — modale creazione coppia FX
- `frontend/src/lib/components/assets/AssetPriceSummary.svelte` — price summary con currency select
- `frontend/src/lib/components/assets/AssetModal.svelte` — modale add/edit asset
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` — sezione provider nella modale
- `frontend/src/lib/i18n/{en,it,fr,es}.json` — traduzioni
- `plan-phase06Step4PartA-Bugfix_6_ClassifTooltipEventMarkers.prompt.md` — piano precedente con specifiche A6

---

## Blocco 1 — Yahoo Finance Sector Mapping (Backend + Test)

### Problema attuale
Yahoo Finance restituisce nomi settore diversi dal nostro enum GICS. Attualmente, settori come "Financial Services", "Communication Services", "Consumer Cyclical", "Consumer Defensive" vengono mappati a "Other" perché non hanno alias nel mapping di `FinancialSector.from_string()`. Questo causa ad esempio che Tesla come azienda finisca in "Other".

### Tabella settori Yahoo Finance
| Yahoo Finance | % (esempio S&P 500) |
|---|---|
| Technology | 28.79% |
| Financial Services | 14.09% |
| Communication Services | 10.02% |
| Consumer Cyclical | 9.94% |
| Healthcare | 9.58% |
| Industrials | 9.26% |
| Energy | 5.54% |
| Consumer Defensive | 5.02% |
| Basic Materials | 3.11% |
| Utilities | 2.40% |
| Real Estate | 2.24% |

### Mapping Yahoo → Nostro Enum

| Yahoo Finance restituisce | Enum esistente target | Alias da aggiungere |
|---|---|---|
| `Technology` | `TECHNOLOGY` ("Technology") | ✅ Già presente |
| `Financial Services` | `FINANCIALS` ("Financials") | `"financial services"` |
| `Communication Services` | `TELECOMMUNICATION` ("Telecommunication") | `"communication services"` |
| `Consumer Cyclical` | `CONSUMER_DISCRETIONARY` ("Consumer Discretionary") | `"consumer cyclical"` |
| `Healthcare` | `HEALTH_CARE` ("Health Care") | ✅ Già presente (alias `"healthcare"`) |
| `Industrials` | `INDUSTRIALS` ("Industrials") | ✅ Già presente |
| `Energy` | `ENERGY` ("Energy") | ✅ Già presente |
| `Consumer Defensive` | `CONSUMER_STAPLES` ("Consumer Staples") | `"consumer defensive"` |
| `Basic Materials` | `BASIC_MATERIALS` ("Basic Materials") | ✅ Già presente |
| `Utilities` | `UTILITIES` ("Utilities") | ✅ Già presente |
| `Real Estate` | `REAL_ESTATE` ("Real Estate") | ✅ Già presente |

### Step 1.1 — Aggiungere alias al mapping in `sector_fin_utils.py`

**File:** `backend/app/utils/sector_fin_utils.py`

Aggiungere 4 righe al `mapping` dict in `FinancialSector.from_string()` (~riga 58):

```python
# Yahoo Finance aliases
"financial services": cls.FINANCIALS,
"communication services": cls.TELECOMMUNICATION,
"consumer cyclical": cls.CONSUMER_DISCRETIONARY,
"consumer defensive": cls.CONSUMER_STAPLES,
```

Non servono nuovi valori enum, nessuna migrazione DB. Il dato salvato nel DB sarà il valore normalizzato (es. "Financials" anziché "Financial Services") perché `FASectorArea.validate_distribution()` chiama `normalize_sector()`.

### Step 1.2 — Aggiornare test in `test_sector_normalization.py`

**File:** `backend/test_scripts/test_utilities/test_sector_normalization.py`

Nella classe `TestFinancialSectorFromString.test_aliases`, aggiungere i 4 alias Yahoo Finance come casi `@pytest.mark.parametrize`:
```python
("Financial Services", FinancialSector.FINANCIALS),
("Communication Services", FinancialSector.TELECOMMUNICATION),
("Consumer Cyclical", FinancialSector.CONSUMER_DISCRETIONARY),
("Consumer Defensive", FinancialSector.CONSUMER_STAPLES),
```

I test `test_expected_sectors_exist`, `test_list_all_excludes_other`, e `test_list_all_with_other_includes_all` restano invariati — nessun nuovo enum value, solo alias.

### Step 1.3 — Nessuna modifica necessaria a `yahoo_finance.py`

Il codice di `fetch_asset_metadata()` (~riga 489-502) salva il settore raw in `FASectorArea(distribution={sector: 1.0})`. Il validatore Pydantic `FASectorArea.validate_distribution()` chiama `normalize_sector()` che ora con i nuovi alias normalizza automaticamente. Il warning log (`validate_sector(sector)`) sparirà da solo per i settori ora riconosciuti.

---

## Blocco 2 — A6: Event Markers sul grafico

### Obiettivo
Visualizzare eventi (dividendi, interessi, split, aggiustamenti prezzo, maturity) come marcatori scatter sul grafico prezzi, sia per l'asset principale che per gli asset in comparazione.

### Prerequisiti già soddisfatti
- Il backend restituisce `events` via `POST /assets/prices/query` con `include_events: true`
- La variabile `events` è già caricata nella pagina asset detail
- `comparisonEvents` map è già popolata per asset in overlay

### Step 2.1 — Definire `EventMarker` type + colori in `PriceChartFull.svelte`

**File:** `frontend/src/lib/components/charts/PriceChartFull.svelte`

Aggiungere dopo le import (zona Props):

```typescript
export interface EventMarker {
    date: string;
    type: string;        // DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT, MATURITY_SETTLEMENT
    value?: number;
    currency?: string;
    notes?: string;
    assetLabel?: string; // solo per comparison events
    signalColor?: string; // colore del segnale overlay per comparison events
}

const EVENT_COLORS: Record<string, string> = {
    INTEREST: '#10b981',           // emerald-500
    DIVIDEND: '#3b82f6',           // blue-500
    PRICE_ADJUSTMENT: '#f59e0b',   // amber-500
    MATURITY_SETTLEMENT: '#ef4444', // red-500
    SPLIT: '#8b5cf6',             // violet-500
};

const EVENT_SYMBOLS: Record<string, string> = {
    INTEREST: 'diamond',
    DIVIDEND: 'triangle',
    PRICE_ADJUSTMENT: 'rect',
    MATURITY_SETTLEMENT: 'roundRect',
    SPLIT: 'arrow',
};
```

### Step 2.2 — Aggiungere prop `eventMarkers` a Props

```typescript
interface Props {
    // ...existing props...
    /** Event markers to display as scatter points on the chart */
    eventMarkers?: EventMarker[];
}
```

Default: `eventMarkers = []` nel destructuring.

### Step 2.3 — Generare scatter series in `renderChart()`

In `renderChart()`, dopo la sezione "Overlay signals" e prima della "Baseline reference line" (~riga 416):

1. Costruire una mappa `dates → index` per lookup O(1): `const dateIndexMap = new Map(dates.map((d, i) => [d, i]));`
2. Raggruppare `eventMarkers` per `type`.
3. Per ogni gruppo, creare una serie scatter ECharts:

```javascript
if (eventMarkers && eventMarkers.length > 0) {
    const dateIndexMap = new Map(dates.map((d, i) => [d, i]));
    const grouped = new Map<string, EventMarker[]>();
    for (const m of eventMarkers) {
        const list = grouped.get(m.type) ?? [];
        list.push(m);
        grouped.set(m.type, list);
    }

    for (const [type, markers] of grouped) {
        const scatterData = markers.map(m => {
            const idx = dateIndexMap.get(m.date);
            if (idx === undefined) return null;
            return {
                value: [m.date, displayData[idx]?.value ?? 0],
                marker: m,
            };
        }).filter(Boolean);

        if (scatterData.length === 0) continue;

        series.push({
            type: 'scatter',
            name: `Events: ${type}`,
            data: scatterData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            symbol: EVENT_SYMBOLS[type] ?? 'diamond',
            symbolSize: 10,
            itemStyle: {
                color: EVENT_COLORS[type] ?? '#6b7280',
            },
            emphasis: {
                scale: 1.5,
            },
            tooltip: {
                trigger: 'item',
                formatter: (params: any) => {
                    const m = params.data?.marker as EventMarker;
                    if (!m) return '';
                    let html = `<strong>${m.date}</strong>`;
                    html += `<br/>📊 ${m.type}`;
                    if (m.value !== undefined) {
                        html += `<br/>💰 ${m.value.toFixed(4)} ${m.currency ?? ''}`;
                    }
                    if (m.notes) {
                        html += `<br/>📝 ${m.notes}`;
                    }
                    if (m.assetLabel) {
                        html += `<br/>🔗 ${m.assetLabel}`;
                    }
                    return html;
                },
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: { color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12 },
            },
            z: 20,
        });
    }
}
```

**Nota architetturale**: Il tooltip globale usa `trigger: 'axis'` e le scatter series non vengono incluse automaticamente. La soluzione è un `tooltip` a livello di serie scatter con `trigger: 'item'` (tooltip indipendente per i marker). Questo evita conflitti con il tooltip globale.

### Step 2.4 — Aggiungere `eventMarkers` all'$effect di renderChart

Nella lista di dep dell'$effect (~riga 124-138), aggiungere `void eventMarkers;` per re-renderizzare quando cambiano gli eventi.

### Step 2.5 — Costruire `eventMarkers` derived nella pagina `+page.svelte`

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte`

Aggiungere nella sezione "Derived" (dopo `allOverlaySignals`, ~riga 234):

```typescript
let eventMarkers = $derived.by(() => {
    const markers: EventMarker[] = [];
    // Main asset events
    for (const ev of events) {
        markers.push({
            date: ev.date,
            type: ev.type,
            value: ev.value ? Number(ev.value.amount) : undefined,
            currency: ev.value?.code,
            notes: ev.notes,
        });
    }
    // Comparison asset events
    for (const [assetId, assetEvents] of comparisonEvents) {
        const cfg = signals.find(s => s.signalType === 'asset-comparison' && Number(s.params.assetId) === assetId);
        const asset = allAssets.find(a => a.id === assetId);
        for (const ev of assetEvents) {
            markers.push({
                date: ev.date,
                type: ev.type,
                value: ev.value ? Number(ev.value.amount) : undefined,
                notes: ev.notes,
                assetLabel: asset?.display_name ?? `Asset #${assetId}`,
                signalColor: cfg?.params.color,
            });
        }
    }
    return markers;
});
```

Passare la prop al componente PriceChartFull (~riga 803):
```svelte
<PriceChartFull
    ...existing props...
    {eventMarkers}
/>
```

Aggiungere l'import del tipo `EventMarker` da PriceChartFull.

### Step 2.6 — i18n per tipi evento (4 lingue)

Aggiungere sotto `assetDetail` nelle 4 lingue:

**en.json:**
```json
"eventType": {
    "DIVIDEND": "Dividend",
    "INTEREST": "Interest",
    "PRICE_ADJUSTMENT": "Price Adjustment",
    "MATURITY_SETTLEMENT": "Maturity",
    "SPLIT": "Split"
}
```

**it.json:**
```json
"eventType": {
    "DIVIDEND": "Dividendo",
    "INTEREST": "Interesse",
    "PRICE_ADJUSTMENT": "Aggiustamento Prezzo",
    "MATURITY_SETTLEMENT": "Scadenza",
    "SPLIT": "Split"
}
```

**fr.json:**
```json
"eventType": {
    "DIVIDEND": "Dividende",
    "INTEREST": "Intérêt",
    "PRICE_ADJUSTMENT": "Ajustement de prix",
    "MATURITY_SETTLEMENT": "Échéance",
    "SPLIT": "Division"
}
```

**es.json:**
```json
"eventType": {
    "DIVIDEND": "Dividendo",
    "INTEREST": "Interés",
    "PRICE_ADJUSTMENT": "Ajuste de precio",
    "MATURITY_SETTLEMENT": "Vencimiento",
    "SPLIT": "División"
}
```

### Step 2.7 — Legenda opzionale

Le scatter series degli eventi appaiono automaticamente nella legenda ECharts come voci separate ("Events: DIVIDEND", ecc.). L'utente può nasconderle cliccando nella legenda. Per usare i nomi localizzati, passare il nome tradotto come `name` della serie (usando il `$t` nel contesto della pagina e passandolo come prop, oppure mantenendo le chiavi inglesi nella legenda e localizzando solo nel tooltip).

---

## Blocco 3 — FX Auto-Sync dopo creazione coppia dalla modale asset detail

### Problema attuale
Quando dalla pagina asset detail si clicca "Aggiungi coppia FX" (pulsante FX+), si apre `FxPairAddModal`. Dopo la creazione:
1. Non viene aggiornata la `displayCurrency` dell'asset detail con la quote della coppia creata
2. La prima valuta (= valuta dell'asset) dovrebbe essere readonly nella modale
3. Il grafico non si aggiorna con i dati convertiti

### Step 3.1 — `FxPairAddModal`: prop `readonlyBase`

**File:** `frontend/src/lib/components/fx/FxPairAddModal.svelte`

1. Aggiungere prop opzionale `readonlyBase?: boolean` (default `false`) all'interfaccia `Props`.
2. Nel destructuring, aggiungere `readonlyBase = false`.
3. Nella condizione `disabled` del `CurrencySearchSelect` della base (~riga 359):
   - Cambiare da `disabled={editMode}` a `disabled={editMode || readonlyBase}`
4. Aggiungere lo stesso per `excludedCurrencies` della base: `excludedCurrencies={editMode || readonlyBase ? new Set() : excludedForBase}`

### Step 3.2 — `oncreated` callback esteso con `slug`

**File:** `frontend/src/lib/components/fx/FxPairAddModal.svelte`

1. Aggiornare il tipo callback nell'interfaccia Props (~riga 50):
```typescript
oncreated?: (detail: { base: string; quote: string; hasRealProvider: boolean; slug: string }) => void;
```
2. Nel `handleSave()`, calcolare slug e passarlo (~riga 282):
```typescript
const slug = `${base}-${quote}`;
oncreated?.({ base, quote, hasRealProvider, slug });
```

### Step 3.3 — Auto-sync dalla pagina asset detail

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte`

Aggiornare l'invocazione di `FxPairAddModal` (~riga 1011-1020):

```svelte
<FxPairAddModal
    bind:open={showFxPairAddModal}
    readonlyBase={true}
    initialBase={assetInfo.currency}
    initialQuote={displayCurrency !== assetInfo.currency ? displayCurrency : ''}
    dateStart={dateStart}
    dateEnd={dateEnd}
    oncreated={async ({ base, quote, hasRealProvider, slug }) => {
        showFxPairAddModal = false;
        await loadFxPairSlugs();
        // Update display currency to the quote of the created pair
        const newQuote = assetInfo!.currency === base ? quote : base;
        if (newQuote !== assetInfo!.currency) {
            displayCurrency = newQuote;
        }
        if (hasRealProvider) {
            toasts.success($t('assetDetail.fxPairCreatedSynced'));
        }
        await handleRefresh();
    }}
    onclose={() => showFxPairAddModal = false}
/>
```

Aggiungere chiave i18n `assetDetail.fxPairCreatedSynced` nelle 4 lingue:
- EN: "FX pair created and synced"
- IT: "Coppia FX creata e sincronizzata"
- FR: "Paire FX créée et synchronisée"
- ES: "Par FX creado y sincronizado"

**Nota**: Il sync è già gestito internamente dalla modale (`handleSave` fa auto-sync se `dateStart`/`dateEnd` sono passati e `hasRealProvider`). Il callback NON deve rifarlo.

---

## Blocco 4 — AssetModal Polish

### Step 4.1 — Spostare `user_url` dalla sezione Provider alla sezione Asset Details

#### In `ProviderAssignmentSection.svelte`:
1. Rimuovere il blocco HTML "User URL" (~riga 724-750): label, input, link esterno.
2. Rimuovere la prop `userUrl` dall'interfaccia `Props` (~riga 87) e dal destructuring (~riga 109).
3. Rimuovere `userUrl` dall'oggetto `emitChange()` (~riga 236).

#### In `AssetModal.svelte`:
1. Rimuovere il `bind:userUrl={providerUserUrl}` dal componente `ProviderAssignmentSection` (~riga 1176).
2. Aggiungere il campo `providerUserUrl` nella sezione "Asset Details", subito dopo il campo "Display Name" e prima del grid Type+Currency (~riga 946):

```svelte
<!-- User URL (custom link) -->
<div>
    <label for="asset-user-url" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
        {$t('assets.provider.userUrl')}
    </label>
    <div class="flex gap-1.5">
        <input
            id="asset-user-url"
            type="text"
            bind:value={providerUserUrl}
            placeholder="https://..."
            class="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                   bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                   placeholder-gray-400 dark:placeholder-gray-500
                   focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green"
        />
        {#if providerUserUrl}
            <a href={providerUserUrl} target="_blank" rel="noopener noreferrer"
               class="shrink-0 flex items-center px-2 py-2 text-gray-400 hover:text-libre-green transition-colors">
                <ExternalLink size={14}/>
            </a>
        {/if}
    </div>
</div>
```

3. Aggiungere `ExternalLink` alle import di lucide-svelte se non già presente.

**Nota**: La variabile `providerUserUrl` rimane in `AssetModal` — cambia solo la posizione del rendering. Il salvataggio in `saveEdit()` (~riga 802: `user_url: providerUserUrl || null`) resta invariato.

### Step 4.2 — Currency in modalità compact

**File:** `frontend/src/lib/components/assets/AssetModal.svelte`

Nella sezione "Asset Details" (~riga 979), aggiungere `compact={true}` al `CurrencySearchSelect`:

```svelte
<CurrencySearchSelect
    value={currency}
    onchange={(v) => { if (v) currency = v; }}
    maxVisibleItems={6}
    compact={true}
/>
```

---

## Ordine di implementazione suggerito

1. **Blocco 1** (Yahoo Sector Mapping) — backend puro, indipendente, testabile subito
2. **Blocco 4** (AssetModal Polish) — frontend puro, indipendente, piccolo
3. **Blocco 2** (Event Markers) — feature più grande, richiede chart + page + i18n
4. **Blocco 3** (FX Auto-Sync) — dipende dalla modale FxPairAddModal

---

## Test di verifica finale

### Yahoo Sector Mapping
- [ ] `./dev.py test unit sector` — tutti i test passano, inclusi i nuovi alias
- [ ] Tesla (TSLA) su Yahoo Finance → settore "Consumer Cyclical" → normalizzato a "Consumer Discretionary" nel DB
- [ ] Apple (AAPL) → settore "Technology" → rimane "Technology" (nessun cambio)
- [ ] Verifica che `validate_sector("Financial Services")` restituisca `True`

### Event Markers
- [ ] Asset con dividendi → mostra marcatori triangolari blu sulle date dei dividendi
- [ ] Asset senza eventi → nessun marker visibile (nessuna scatter series)
- [ ] Hover su marker → tooltip con tipo localizzato, valore, currency
- [ ] Comparison asset con eventi → marker con bordo colorato del segnale
- [ ] Toggle legenda → nasconde/mostra marker per tipo

### FX Auto-Sync
- [ ] Da asset detail, click FX+ → modale si apre con base = valuta asset (readonly)
- [ ] Creo coppia con provider reale → sync automatico + toast feedback
- [ ] Dopo chiusura modale, il grafico mostra i dati convertiti nella nuova valuta
- [ ] Se cambio la seconda valuta nella modale, `displayCurrency` si aggiorna

### AssetModal Polish
- [ ] Il campo "URL utente" è nella sezione "Asset Details", accanto al nome
- [ ] Il campo "URL utente" NON è più nella sezione "Provider Assignment"
- [ ] La currency nella modale è in modalità compact (più piccola, coerente)
- [ ] Il salvataggio funziona correttamente con user_url nella nuova posizione

