# Plan: Asset Detail Page — Phase 6 Step 4 (v3 Finale)

**Scopo:** Completare la parità funzionale AssetCard/FxCard nella lista, poi creare la pagina dettaglio `/assets/[id]` con chart interattivo, analisi tecnica, editing manuale prezzi+eventi unificato, currency conversion backend-side, e metadata. Le configurazioni provider restano nella modale AssetModal.

Il piano è in **4 Parti (0, A, B, C)**, ciascuna con macro-task indipendenti.

---

## Parte 0 — Parità Asset List ↔ FX List (Card Settings, Abs/%, Segnali)

**Obiettivo:** portare AssetCard e la pagina lista asset allo stesso livello funzionale di FxCard e della lista FX. Prerequisito per la propagazione settings verso la detail page.

### 0.1. AssetCard — nuove props e pulsanti (allineamento a FxCard)

- In `AssetCard.svelte`, aggiungere props:
  - `chartSettings?: ChartSettings` — per estetica mini chart
  - `renderSignals?: (chartData: LineDataPoint[], viewMode) => RenderedSignal[]` — per segnali overlay
  - `onsettings?: (asset: AssetData) => void` — callback per gear button
- Rinominare `deltaDisplayMode` → `globalViewMode` (coerenza con FxCard)
- Aggiungere stato `localViewModeOverride` con reset quando `globalViewMode` cambia (stesso pattern FxCard righe 76-88)
  - `cardViewMode = $derived(localViewModeOverride ?? globalViewMode)`
- Aggiungere pulsante **% toggle** nell'header della card (accanto al type badge, stesso stile FxCard riga 199-207)
- Aggiungere pulsante **⚙ Settings** nel footer a sinistra (prima di sync, stesso pattern FxCard riga 265-271)
- Passare a `PriceChartCompact`:
  - `viewMode={cardViewMode}` (non più hardcoded `'absolute'`)
  - `areaFill={chartSettings?.areaFill ?? true}`
  - `colorByBaseline={chartSettings?.colorByBaseline}`
  - `showGridLines={chartSettings?.gridLines}`
  - `showGradient={chartSettings?.staleGradient ?? true}`
  - `overlaySignals={overlaySignals}` (calcolati via `renderSignals`)
- Calcolare `overlaySignals` come `$derived` (stesso pattern FxCard righe 138-141)
- Il testo delta deve anch'esso usare `cardViewMode` (abs mostra deltaAbs, % mostra deltaPercent)

### 0.2. Assets List Page — wiring settings + signals nelle card

- In `+page.svelte`, nella sezione Grid View, passare ad ogni AssetCard:
  - `chartSettings={getSettingsForPair(\`asset-${asset.id}\`)}`
  - `renderSignals={buildAssetSignals}` — funzione analoga a quella FX che istanzia i segnali dalla config
  - `onsettings={(a) => { settingsTargetId = String(a.id); settingsModalOpen = true; }}`
  - `globalViewMode={globalViewMode}` (rinominare da `deltaDisplayMode`)
- Creare helper `buildAssetSignals(chartData, viewMode)` che itera `settings.signals`, chiama `signalFromConfig` + `renderMulti` (stesso pattern della FX list page)
- Verificare che `ChartSettingsModal` funzioni già per per-card override (il wiring `settingsTargetId` + `handleSettingsSave` esiste già ✅, ma verificare che il modale riceva i segnali corretti)

### 0.3. Abs/% toggle coerenza grid ↔ table

- Attualmente il toggle Abs/% nella matrice 2×2 è visibile solo in grid mode (table mode mostra `ColumnVisibilityToggle`). Valutare se in table mode il toggle Abs/% debba stare altrove o se l'attuale comportamento è accettabile (la tabella mostra già le colonne Δ% per-periodo). **Decisione: mantenere as-is** — la tabella mostra i Δ% multi-periodo, il toggle è solo per le card.

---

## Parte A — Page Detail: Skeleton, Chart, Analisi, Azioni

**Obiettivo:** pagina `/assets/[id]` navigabile con chart funzionante, segnali, misure, matrice 2×2 (Edit/Abs%/Sync/Refresh), e auto-sync dopo edit da modale.

### A1. +page.ts + Load Function

- Creare `+page.ts`: parsing `params.id` (intero), redirect a `/assets` se non valido
- Ritorna `{ assetId: number }`

### A2. Page scaffold + Header

- Riscrivere `+page.svelte` da placeholder a pagina completa
- `onMount` carica in parallelo:
  - Asset info (da `GET /assets/query` o `GET /assets/all`) → `FAinfoResponse`
  - Provider assignment (da `GET /assets/provider/assignments?asset_ids={id}`) → `FAProviderAssignmentReadItem`
  - Chart data + eventi (da `POST /assets/prices/query` con `include_events: true`)
- Header: back button ←, AssetIcon, `display_name`, badge tipo, flag+currency, identificatore principale, badge provider. **NO delete**, **NO edit inline** (stanno nella matrice 2×2)

### A3. Filter Bar + Matrice 2×2 Actions

- Stessa struttura FX detail e lista asset:
  - **Sinistra:** DateRangePicker (default 3M) + price summary (last price, Δ%, Δabs)
  - **Destra:** matrice 2×2:
    - `[Abs | %]` segmented toggle → controlla viewMode del chart
    - `[✏ Edit]` → riapre AssetModal in editMode → al save: auto-sync + refresh
    - `[⟳ Sync]` → `POST /assets/prices/sync` (label "Recalculate" se scheduled_investment; disabled se no provider)
    - `[↻ Refresh]` → re-query prezzi dal DB
- `ResizeObserver` con `createResponsiveLayout`

### A4. Chart + Pannelli Foldable

- `PriceChartFull` con dati da query, conversione `FAPricePoint[]` → `LineDataPoint[]`
- Chart settings da store: `getSettingsForPair(\`asset-${id}\`)`
- `ChartAestheticsSection` foldable (sopra chart)
- `MeasurePanel` foldable (sotto chart)
- `ChartSignalsSection` foldable (sotto measures)
- Empty state adattivo (no provider / scheduled_investment / no data)
- Pulsanti overlay: 📐 Measure e ✏ Edit data (toggle pannello editor)

### A5. Event Markers sul Chart

- Nuova prop `eventMarkers` su `PriceChartFull`:
  - `Array<{date: string, type: string, value: number, label?: string}>`
- Implementati come **scatter series** con `symbol: 'diamond'`, posizionati a **Y = 90%** dell'altezza chart (asse Y invisibile normalizzato 0-100, i marker stanno a 90). Fine-tunable successivamente.
- Colori per tipo: 🟢 INTEREST, 🟡 PRICE_ADJUSTMENT, 🔴 MATURITY_SETTLEMENT, 🔵 DIVIDEND
- Tooltip: tipo evento con badge colorato, valore formattato con currency, notes

### A6. Auto-sync + Refresh dopo Edit da modale

- Quando `AssetModal` emette `onupdated`:
  - Ri-carica asset info
  - `POST /assets/prices/sync` (sync dal provider)
  - Re-query prezzi (refresh chart)
  - Toast con risultato sync

### A7. Sezione Metadata (accordion foldable, readonly)

- In fondo alla pagina: identifiers, classification, sector, geographic, short description
- Dati da `FAinfoResponse` + `FAAssetMetadataResponse` (caricati in A2)
- Readonly — editing via AssetModal

---

## Parte B — Data Editor Unificato (Prezzi + Eventi) + Backend Eventi + CSV Import

**Obiettivo:** pannello edit (toggle via ✏ sul chart) con due tabelle — Prezzi OHLCV e Eventi — save unificato, CSV import generalizzato per entrambe.

### B1. Backend — Endpoint CRUD Eventi manuali

- Attualmente mancante: `_upsert_asset_events` esiste come metodo interno ma nessun endpoint REST pubblico
- Creare `POST /assets/events` — upsert eventi manuali bulk (input: `[{asset_id, events: FAAssetEventPoint[]}]`), chiama `_upsert_asset_events(provider_assignment_id=None)`
- Creare `DELETE /assets/events` — delete eventi manuali per `(asset_id, date, type)` con filtro `provider_assignment_id IS NULL`
- Estendere `FAAssetEventPoint` (o `FAPriceQueryResult`) per includere `is_auto_generated: bool` nella risposta query (derivato da `provider_assignment_id IS NOT NULL`)
- `./dev.py api sync` per rigenerare Zodios

### B2. DataEditor — estensione tipi cella (enum, string editable)

- In `DataEditorTypes.ts`: aggiungere `'enum'` a `ColumnDef.type`, campo `enumOptions?: Array<{value: string, label: string}>`
- In `DataEditor.svelte`: quando `col.type === 'enum'` e `col.editable`, renderizzare `SimpleSelect` inline nella cella
- Aggiungere supporto `type: 'string'` editable (input text inline per campo notes)

### B3. AssetDataEditorSection.svelte — orchestratore 2 tabelle

- Creare `AssetDataEditorSection.svelte`
- **Tab "Prices":** DataEditor con colonne OHLCV (date required, open/high/low optional, close required, volume optional)
  - Conversione `FAPricePoint[]` ↔ `DataRow[]`, dirty tracking → preview signal arancione, `scrollToDate()`
  - **Nascosta** per scheduled_investment (prezzi calcolati, non editabili)
- **Tab "Events":** DataEditor con colonne evento (date required, type enum required [INTEREST/PRICE_ADJUSTMENT/MATURITY_SETTLEMENT/DIVIDEND], amount number required, notes string optional)
  - Conversione `FAAssetEventPoint[]` ↔ `DataRow[]`
  - Badge colorato per tipo, badge "auto"/"manual" (auto = readonly/non-deletable)
  - **Sempre visibile** (anche per scheduled_investment — eventi manuali ammessi)
- **Save unificato:** raccoglie dirty rows da entrambe le tabelle → `POST /assets/prices` + `POST /assets/events` + DELETE per righe marcate → toast aggregato → refresh chart
- Barra Save/Cancel in fondo (stessa estetica FxDataEditorSection)

### B4. Generalizzazione DataImportModal + CsvEditor multi-colonna

- **Nuova sintassi CSV:** il formato è `date;col1;col2;...;colN` con header obbligatorio. Colonne da `ColumnDef[]` passato come prop. Solo `date` e le colonne required sono obbligatorie, le altre accettano celle vuote.
  - Prezzi: `date;open;high;low;close;volume` (solo date+close required)
  - Eventi: `date;type;amount;notes` (date+type+amount required)
  - FX: `date;EUR>USD` (retrocompatibile, same as now)
- Il dettaglio architetturale dell'evoluzione di CsvEditor (parsing multi-colonna, validazione per-colonna, rendering) viene **rimandato a un sotto-piano dedicato** dopo la standardizzazione delle API (B1). Si accenna qui la direzione:
  - `DataImportModal` riceve `columns: ColumnDef[]` come prop opzionale
  - `CsvEditor` viene generalizzato per N colonne
  - Wrapper specializzati thin: `FxDataImportModal` (1 colonna rate + direction), `AssetPriceImportModal` (5 colonne OHLCV), `AssetEventImportModal` (3 colonne type+amount+notes)
- **Per ora** (Parte B implementazione) si può usare solo "Add Row" + edit inline, e rimandare il CSV import multi-colonna alla fine di Parte B o come follow-up

---

## Parte C — Currency Conversion Backend + Frontend

**Obiettivo:** dropdown display currency nella detail page, il backend converte via FX, con `AssetBackwardFillInfo` separato per staleness prezzo vs FX.

### C1. Backend — AssetBackwardFillInfo

- In `prices.py`, creare:
  - `AssetBackwardFillInfo(BackwardFillInfo)` con `fx_rate_date` e `fx_days_back`
- Aggiornare `FAPricePoint.backward_fill_info` → `Optional[AssetBackwardFillInfo]`
- Aggiungere `original_currency: Optional[str] = None` a `FAPricePoint`

### C2. Backend — target_currency in query

- Aggiungere `target_currency: Optional[str] = None` a `FAPriceQueryItem`
- In `get_prices_bulk()`: se `target_currency` presente e ≠ `point.currency`:
  - Raggruppare per coppia `(from_currency, target_currency)`
  - `convert_bulk()` FX in batch
  - Sostituire OHLC, popolare `original_currency`, `fx_rate_date`, `fx_days_back`
  - Se coppia FX mancante → prezzo originale + warning in `errors`
- `./dev.py api sync`

### C3. Frontend — Dropdown + Chart Integration

- Nella filter bar: `CurrencySearchSelect` "Display currency" (default = `asset.currency`)
- Passare `target_currency` a `POST /assets/prices/query`
- Gradiente opacità → usa solo `days_back` (prezzo), ignora `fx_days_back`
- Tooltip → riga ⚠ `FX rate: N days old` quando `fx_days_back > 0`
- Label chart: currency display + "converted from XXX" quando `original_currency` presente

### C4. i18n + Polish finale

- ~40-50 chiavi i18n (EN/IT/FR/ES) via `./dev.py i18n add`
- Dark mode coerenza tutte le sezioni
- Responsive wide/tablet/mobile

---

## Dipendenze

```
Parte 0 (parità AssetCard ↔ FxCard)
 └→ Parte A (detail page + chart + analisi)
      ├→ Parte B (editor prezzi+eventi + backend eventi + CSV)
      │    └→ B1 (backend) è prerequisito di B3-B4
      │    └→ B2 (DataEditor enum) è prerequisito di B3
      └→ Parte C (currency conversion) — indipendente da B
           └→ C1-C2 (backend) prerequisito di C3 (frontend)
```

---

## Further Considerations

- **CsvEditor multi-colonna:** la generalizzazione va dettagliata in un sotto-piano dedicato dopo che le API sono stabilizzate (post B1). La direzione è: `DataImportModal` generico con `columns` prop, `CsvEditor` generalizzato, wrapper thin per FX/Asset/Event. Per ora nella Parte B si usa solo Add Row + edit inline.
- **Performance event markers a Y=90%:** lo scatter series a quota fissa sull'asse Y invisibile è semplice da implementare e visivamente chiaro. Se in futuro i marker dovessero sovrapporsi (molti eventi nello stesso range), si può aggiungere jitter verticale o raggruppamento.

