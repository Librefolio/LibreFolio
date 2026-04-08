# Plan: Bugfix 6 — Classification Loading, FX Tooltip, Provider Badge, URL, Event Markers

## Riepilogo delle modifiche applicate

### ✅ Bug risolti in questa sessione

| # | Issue | Fix |
|---|-------|-----|
| 1 | **Classification "Loading..." forever** (Bitcoin, asset senza distribuzioni) | Aggiunto flag `classificationLoaded` — la sezione mostra "No classification data" quando il caricamento è completo ma non ci sono dati, e "Loading..." solo durante il fetch effettivo |
| 2 | **Edit modal non carica distribuzioni** | `buildEditData()` ora include `classification_params` costruiti dai dati `sectorDistribution` / `geographicDistribution` già caricati |
| 3 | **Provider badge mostra key invece del nome** | Sostituito `{assetInfo.provider_code}` con `{getAssetProviderName(assetInfo.provider_code)}` nell'header |
| 4 | **FX warning toast scomodo → Tooltip** | Rimosso toast auto-show + `$effect`. L'icona ⚠️ ora è wrappata in `<Tooltip>` che mostra il messaggio on hover |
| 5 | **User URL posizionato male** | `user_url` ora appare nell'header accanto al nome (link icon). La sezione metadata mostra solo `provider_url` |
| 6 | **Navigazione tra asset: grafici classification non spariscono** | `reloadMetadata()` resetta `classificationLoaded = false` prima di ricaricare, e gestisce il caso `has_metadata = false` settando le distribuzioni a null |

### File modificati
- `frontend/src/routes/(app)/assets/[id]/+page.svelte`

---

## Informazioni richieste

### Breakpoint thresholds — dove editare

| Pagina | File | Riga | Soglie attuali |
|--------|------|------|----------------|
| **Asset Detail** | `frontend/src/routes/(app)/assets/[id]/+page.svelte` | ~127 | `{wide: 730, tablet: 550, tabletS: 400, labelHide: 500}` |
| **Asset List** | `frontend/src/routes/(app)/assets/+page.svelte` | ~152 | `{wide: 1240, tablet: 920, tabletS: 500, labelHide: 460}` |
| **FX List** | `frontend/src/routes/(app)/fx/+page.svelte` | ~102 | `{wide: 1030, tablet: 700, tabletS: 530, labelHide: 460}` |
| **FX Detail** | `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | (cerca `createResponsiveLayout`) | simile |

Il comportamento è definito in `frontend/src/lib/utils/responsiveLayout.svelte.ts`:
- `wide` → layout a riga piena, prezzo + filtri affiancati
- `tablet` → layout a colonna, filtri sovrapposti
- `tablet-s` (tabletS) → pulsanti si impilano verticalmente
- `mobile` → tutto verticale centrato
- `labelHide` → sotto questa soglia i label dei pulsanti spariscono, restano solo le icone

Per fare fine-tuning: modifica i numeri in px nella chiamata `createResponsiveLayout({...})`.

---

## Piano successivo: A6 — Event Markers

### Obiettivo
Visualizzare eventi (dividendi, interessi, split, aggiustamenti prezzo, maturity) come marcatori scatter sul grafico prezzi, sia per l'asset principale che per gli asset in comparazione.

### Prerequisiti
- Il backend già restituisce `events` da `POST /assets/prices/query` con `include_events: true`
- Il campo `events` è già caricato nella pagina asset detail (`events` state variable, caricato in `loadChartData()`)
- Gli eventi di comparazione sono caricati in `comparisonEvents` map

### Step da implementare

#### A6.1 — Definire `EventMarker` type + colori

**File:** `frontend/src/lib/components/charts/PriceChartFull.svelte`

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

#### A6.2 — Prop `eventMarkers` su PriceChartFull

Aggiungere al `Props`:
```typescript
eventMarkers?: EventMarker[];
```

Default: `[]`

#### A6.3 — Scatter series in `renderChart()`

Per ogni tipo evento presente nei markers:
1. Raggruppare i markers per `type`
2. Per ogni marker, trovare il punto `lineData` con data più vicina → usare quel valore Y
3. Creare una scatter series ECharts:

```javascript
const scatterSeries = Object.entries(groupedByType).map(([type, markers]) => ({
    type: 'scatter',
    name: `Events: ${type}`,
    data: markers.map(m => {
        const closestPoint = findClosestDataPoint(lineData, m.date);
        return {
            value: [m.date, closestPoint?.value ?? 0],
            marker: m,
        };
    }),
    symbol: EVENT_SYMBOLS[type] ?? 'diamond',
    symbolSize: (_, params) => params.data.marker.signalColor ? 8 : 10,
    itemStyle: {
        color: EVENT_COLORS[type] ?? '#6b7280',
        borderColor: (params) => params.data.marker.signalColor ?? EVENT_COLORS[type],
        borderWidth: (params) => params.data.marker.signalColor ? 2 : 0,
    },
    z: 20,
}));
```

#### A6.4 — Tooltip formatter per event markers

Aggiornare il tooltip formatter per gestire scatter series:
```
📊 DIVIDEND
💰 0.82 USD
📝 Quarterly dividend
```
Per comparison events: aggiungere label dell'asset con colore.

#### A6.5 — Passare gli eventi dalla page al chart

In `+page.svelte`, costruire `eventMarkers` combinando:
1. `events` dell'asset principale
2. `comparisonEvents` degli asset in overlay

```typescript
let eventMarkers = $derived.by(() => {
    const markers: EventMarker[] = [];
    // Main asset events
    for (const ev of events) {
        markers.push({
            date: ev.date,
            type: ev.type,
            value: ev.value ? Number(ev.value) : undefined,
            currency: assetInfo?.currency,
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
                value: ev.value ? Number(ev.value) : undefined,
                notes: ev.notes,
                assetLabel: asset?.display_name ?? `Asset #${assetId}`,
                signalColor: cfg?.params.color,
            });
        }
    }
    return markers;
});
```

#### A6.6 — i18n per tipi evento

Aggiungere chiavi:
```json
{
  "assetDetail": {
    "events": "Events",
    "eventType": {
      "DIVIDEND": "Dividend",
      "INTEREST": "Interest",
      "PRICE_ADJUSTMENT": "Price Adjustment",
      "MATURITY_SETTLEMENT": "Maturity Settlement",
      "SPLIT": "Split"
    }
  }
}
```

#### A6.7 — Legenda opzionale

Nella legenda ECharts, le scatter series degli eventi appaiono come voci separate. L'utente può nasconderle cliccando nella legenda.

### Test di verifica
- [ ] Asset con dividendi (es. Apple) → mostra triangoli blu sulle date dei dividendi
- [ ] Loan con interessi → mostra diamanti verdi
- [ ] Asset senza eventi → nessun marker (nessuna scatter series)
- [ ] Hover su marker → tooltip mostra tipo, valore, currency
- [ ] Comparison asset con eventi → marker con bordo colorato
- [ ] Toggle legenda → nasconde/mostra marker per tipo

---

## Altre migliorie rimandate al prossimo ciclo

### FX+ button: auto-sync dopo creazione coppia
Al salvataggio dalla modale FX, se almeno 1 provider è configurato:
1. Sincronizzare la coppia nel date range attualmente impostato sulla pagina asset
2. Fare refresh dell'asset
3. La prima valuta (base = valuta asset) dovrebbe essere readonly nella modale
4. Se la seconda valuta cambia, aggiornare la conversione alla chiusura della modale

### Considerazioni sul flusso FxPairAddModal
- Prop `readonlyBase?: boolean` per bloccare la valuta base
- `oncreated` callback deve ricevere il slug della coppia creata per poter poi triggerare sync

