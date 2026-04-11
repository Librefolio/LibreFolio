# Part B — Data Editor Unificato + CSV Import Generico + Test E2E

Riscrittura CsvEditor/DataImportModal eliminando tutto il codice FX-specifico. Il parser è generico a N colonne configurato via prop. La modale FX resta esteticamente identica (direction bar, swap ⇄, currency badges) ma è un wrapper del componente generico. Le 2 nuove modali (prezzi, eventi) sono varianti della stessa struttura con banner e link a docs. Prezzi: `date;currency;close` obbligatori. Test E2E per tutte e 3 le modali.

## Steps

### ✅ B1 — Backend: schema `FAAssetEventPointOut` e CRUD endpoint eventi

In `backend/app/schemas/prices.py`: creare `FAAssetEventPointOut(FAAssetEventPoint)` con `id: int` + `is_auto: bool`. Nuovi schemi di risposta ereditano da classi in `backend/app/schemas/common.py` (`BaseDeleteResult`, `BaseBulkResponse`). In `backend/app/api/v1/assets.py`: nuovo `event_router` con `POST /events` (upsert manuale), `DELETE /events/{id}` (elimina per PK), `GET /events` (query per `asset_id` + date range). Registrare in `asset_router.include_router(event_router)`.

**Done**: `FAAssetEventPointOut`, `FAEventUpsert`, `FAEventUpsertResult`, `FABulkEventUpsertResponse`, `FAEventDeleteResult`, `FAEventQueryItem`, `FAEventQueryResult`, `FAEventQueryResponse`. Service methods `bulk_upsert_events_manual()`, `query_events_bulk()`, `delete_event_by_id()`. `event_router` con POST /events, DELETE /events/{id}, POST /events/query.

### ✅ B2 — Riscrittura `CsvEditor.svelte` → generico N colonne, zero codice FX

Eliminare: `parseHeader` con `>/<`, `allowedCurrencies`, `ondirectiondetect`, `appendRow`, `setHeader`. Nuova prop `columns: CsvColumnDef[]` (array `{key, label, type: 'number'|'string', required}`). L'header CSV è generato come `date;label1;label2;...` dai `columns[].label`. Il parser valida ogni riga in base al numero di colonne: i campi mancanti (colonne omesse o `;;`) diventano `null`, ma i `required` devono essere presenti. `ParsedRow` diventa `{ date: string, values: Record<string, unknown>, lineNumber: number }`. La funzione `parseNumber()` e la status bar restano invariate. Nessun `appendRow`/`setHeader` — API pubblica ridotta a `scrollToLine()` e `setText()`.

**Done**: `CsvColumnDef[]` prop, `ParsedRow` con `values: Record<string, unknown>`, header auto-generato, validazione N-colonne con campi opzionali.

### ✅ B3 — Decomposizione `DataImportModal.svelte` → generico con slot

`DataImportModal.svelte` diventa il contenitore generico: riceve `columns: CsvColumnDef[]`, `title: string`, `helpContent?: Snippet`, `headerSlot?: Snippet` (iniettato tra drop zone e CsvEditor), `onimport: (rows: ParsedRow[]) => void`. Contiene: header con titolo + `?` help toggle + `✕`, drop zone, `{@render headerSlot?.()}`, `CsvEditor` con `columns`, footer con contatore + Cancel/Import. La struttura estetica resta identica alla modale FX attuale.

Tre wrapper specifici:

- **`FxDataImportModal.svelte`**: istanzia `DataImportModal` con `columns=[{key:'rate', label:'${from}>${to}', type:'number', required:true}]`. Nell'`headerSlot` inserisce: currency badges readonly + `→` + swap `⇄` + InfoBanner "Rates interpreted as...". Al `onimport` aggiunge info direction e richiama il callback padre.

- **`PriceDataImportModal.svelte`**: `columns=[{key:'currency', label:'currency', type:'string', required:true}, {key:'close', label:'close', type:'number', required:true}, {key:'open',...required:false}, {key:'high',...}, {key:'low',...}, {key:'volume',...}]`. Nell'`headerSlot`: InfoBanner "Minimum format: date;currency;close — optional columns: open, high, low, volume. Use ;; to skip a column." con link docs (`window.open(docsUrl, '_blank')`).

- **`EventDataImportModal.svelte`**: `columns=[{key:'type', label:'type', type:'string', required:true}, {key:'amount', label:'amount', type:'number', required:true}, {key:'currency', label:'currency', type:'string', required:false}, {key:'notes', label:'notes', type:'string', required:false}]`. Nell'`headerSlot`: InfoBanner "Types: DIVIDEND, INTEREST, SPLIT, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT" con link docs.

**Done**: `DataImportModal` generico con `headerSlot`/`helpContent` Snippet. `FxDataImportModal`, `PriceDataImportModal`, `EventDataImportModal` wrapper. Bug fix: swap direction aggiorna header CSV automaticamente.

### ✅ B4 — `DataEditor.svelte` + `DataEditorTypes.ts`: `rowId`, enum/string, readonly

In `DataEditorTypes.ts`: aggiungere `rowId: string` a `DataRow`, `readonly?: boolean` a `DataRow`, `'enum'` a `ColumnDef.type`, `enumOptions?: {value: string, label: string, emoji?: string}[]` a `ColumnDef`. In `DataEditor.svelte`: `getRowId` usa `r.rowId`; tutti i lookup interni `r.date` → `r.rowId`; rendering colonne aggiunge `col.type === 'string'` → `editable-text` e `col.type === 'enum'` → `editable-select`; righe `readonly` disabilitano edit ma permettono delete. Nuovo prop opzionale `importModalComponent?: Snippet` per iniettare la modale specifica (il bottone "Import CSV" renderizza lo snippet). Rimuovere `displayBase`/`displayQuote` da DataEditor (spostati nel wrapper).

**Done**: `rowId` in DataRow, `readonly` per righe auto, tipi `'enum'`/`'string'` nelle colonne, `importModal` snippet prop, rimossi `displayBase`/`displayQuote`.

### ✅ B5 — `AssetDataEditorSection.svelte`: orchestratore a 2 tab

Due tab (Prices / Events), ciascuno con la propria istanza `DataEditor`. Prezzi: colonne `currency` (CurrencySearchSelect compact, required, editabile), `close` (number, required), `open/high/low/volume` (number, optional). `rowId = date`. Eventi: colonne `currency` (CurrencySearchSelect compact, optional), `type` (enum con emoji: `💰 DIVIDEND`, `📈 INTEREST`, `✂️ SPLIT`, `📊 PRICE_ADJUSTMENT`, `🏁 MATURITY`), `amount` (number, required), `notes` (string, optional). `rowId = String(event.id)` o `crypto.randomUUID()`. Righe auto (`is_auto`) → `readonly: true`, eliminabili. Salvataggio: bottone Save invia entrambi i tab se almeno uno ha dirty count > 0 (endpoint separati). Al successo → refresh dati (niente preview persistente). Save/Cancel bar unica in basso. Integrato in `frontend/src/routes/(app)/assets/[id]/+page.svelte` al posto del placeholder 🚧.

**Done**:
- `AssetDataEditorSection.svelte` creato (~490 righe) con 2 tab, save/cancel unificato, preview signal viola
- Tipo `'currency'` aggiunto a `ColumnDef.type` in `DataEditorTypes.ts`, renderizza `CurrencySearchSelect` compact nel `DataEditor.svelte`
- Ordine colonne: `date;currency;...` coerente in entrambi i tab e nei CSV import modals
- Integrato nella pagina dettaglio asset, sostituendo il placeholder Construction 🚧
- `pendingPreviewSignal` incluso in `allOverlaySignals` per preview grafico
- i18n: chiavi `pricesTab`/`eventsTab` in EN/IT/FR/ES, rimossa `editDataComingSoon`
- Docs URL corretti: `EventDataImportModal` → `/user/assets/detail/events/`, `PriceDataImportModal` → `/user/assets/detail/prices/`
- Badge `✏️ Manual` aggiunto in: asset detail header, AssetCard, AssetTable (quando no provider)
- Toggle stale rows nel DataEditor: pulsante Eye/EyeOff con contatore, filtra righe backward-fill
- Double-click chart → editor scroll: `onDblClick` e `onEventDblClick` in `PriceChartFull`, con smart tab switching in `scrollToDate(date, tab?)`
- Valori numerici readonly formattati a max 4 decimali
- Fix FX no-data banner: stringa hardcoded inglese sostituita con `get(t)('fxDetail.noData')`

### 🚧 B6 — Test E2E + fix link docs + test backend

- ✅ **Fix `HelpMenu.svelte`**: link FAQ e Documentation già corretti con `target="_blank" rel="noopener noreferrer"`.
- ✅ **Nuovo `e2e/assets/asset-data-editor.spec.ts`**: 23 test (apertura editor, tab switching, CSV import valid/invalid per prices e events, save/cancel, dirty tracking, close, stale toggle, import → tabella).
- ✅ **`test_runner.py`**: aggiunta funzione `front_asset_data_editor()`, registrata nel `TEST_REGISTRY`, `"front-asset"` aggiunto in tutte le tuple categorie frontend.
- ✅ **`fx-csv-import.spec.ts`**: 20 test (inclusi test 15-20 per `<`/`>` syntax, swap direction, badge update).
- ✅ **Backend test `test_assets_events.py`**: 8 test CRUD eventi (upsert, query, delete, upsert replace, empty range, non-existent asset, multiple types same date).
- ✅ **Test CSV validi/invalidi**: test 14-23 in `asset-data-editor.spec.ts` coprono: dati prezzo validi, formato esteso, errori (close mancante, data invalida, close non-numerico), import → tabella, eventi validi, campi required mancanti, import eventi → tabella, stale toggle, skip colonne con `;;`, tutti e 5 i tipi di evento.

#### 🐛 Bug fix: tutti i 23 test skipped (11/04/2026)

**Problema**: `goToFirstAssetDetail` navigava al primo asset card nella lista, che poteva essere un asset senza price data (es. Real Estate Loan, Gold Spot, NVIDIA senza sync). Senza dati prezzo → nessun `<canvas>` → `test.skip()` → tutti 23 test saltati ma la suite passava con exit code 0.

**Fix**: sostituito `goToFirstAssetDetail` con `goToAssetWithPrices` che:
1. Usa `navigateToAssetByName(page, 'Apple')` da `assets-helpers.ts`
2. Apple Inc. è sempre presente nei mock data con 30 giorni di price history (populate_mock_data.py linee 1076+)
3. Eliminato il codice duplicato (search + click card) — usa l'helper condiviso

#### 🐛 Bug fix: performance — chunk JS da 4.5s (11/04/2026)

**Problema**: nonostante il catch-all sia `def` (sync, thread pool), alcuni chunk JS come `9.XGTAAALt.js` e `B93Iqmu4.js` impiegavano ancora 4.5s. Il problema: SvelteKit genera import relativi nei chunk, quindi da `/assets/123` un `import("./ChunkName.js")` risolve a `/assets/123/ChunkName.js` che va nel catch-all (non nel mount `/_app`).

**Fix**: aggiunto nel catch-all un fallback per chunk con path relativo:
- Se l'ultimo segmento del path sembra un file hashed (es. `BV3j34CM.js`), prova a servirlo da `_app/immutable/chunks/`, `_app/immutable/entry/`, `_app/immutable/nodes/`
- La mount `StaticFiles` su `/_app` serve i percorsi assoluti (header `<link>`, `<script>`)
- Il catch-all serve i percorsi relativi (dynamic import da chunk)

### ✅ B7 — Polish e fix post-review utente

1. ✅ **Asset manual: mostrare data editor invece di "set one up via Edit"** — Quando un asset non ha provider (`isManualOnly`), nella sezione no-data del grafico, aggiungere un pulsante per aprire il data editor (invece di solo il modal edit asset). L'utente deve poter inserire dati a mano senza configurare un provider.

2. ✅ **Stale toggle: levetta orizzontale + Tooltip** — Il toggle stale nel DataEditor deve essere una levetta (switch) orizzontale invece di un bottone. Al hover sull'icona, mostrare un `Tooltip.svelte` che spiega cosa fa: "Hide backward-filled rows (⚠️ stale). These are gap-fill points copied from the nearest real data point." Mantenere posizione e contatore.
   - ✅ **Fix i18n**: il tooltip è tradotto con chiave `dataEditor.staleTooltip` (EN/IT/FR/ES). Il testo "Stale: Xd" nell'infobox del grafico (PriceChartFull tooltip formatter) è tradotto tramite prop `staleLabel` passata dalle pagine chiamanti con `$t('chart.tooltip.stale')` (chiave già esistente).

3. ✅ **Double-click chart → evento: highlight viola** — Quando si fa double-click su un punto del grafico che corrisponde a un event marker, e l'editor è aperto, il tab Events deve attivarsi e la riga dell'evento deve risaltare (background viola temporaneo o scroll + flash animation), uguale al comportamento del tab Prices. Attualmente il tab si cambia ma la riga non si evidenzia.
   - ✅ **Fix mobile**: il long-press (800ms) su mobile ora invoca `onDblClick`/`onEventDblClick` (stessa logica del dblclick desktop), oltre a `handlePointClick` per edit mode.

4. ✅ **Tooltip grafico mobile: posizionamento centrato** — L'infobox/tooltip del grafico ECharts su mobile tende a uscire dal bordo dello schermo (destra/sinistra) e sta sotto il pollice. Configurare il tooltip ECharts per: posizionamento centrato sopra il punto, con margine dal bordo superiore; clamp ai bordi dello schermo (non va oltre il viewport); distanza sufficiente dal dito.
   - ✅ **Fix**: rimosso fallback sotto il dito (`y = point[1] + 30`). Il tooltip resta SEMPRE sopra, con `confine: false` e clamp Y al bordo superiore del viewport (`-chartRect.top`). Il tooltip può uscire dal chart ma mai dal viewport.

5. ✅ **Financial Theory MkDocs pages** — Create 6 pagine sotto `mkdocs_src/docs/financial-theory/`:
   - `asset-events.en.md` — Overview di tutti i 5 tipi evento con tabella comparativa, events vs transactions, fonti (provider/manual)
   - `asset-events/dividend.en.md` — Definizione, lifecycle (declaration/ex/record/payment dates), impatto su prezzo, dividend yield, formula total return
   - `asset-events/interest.en.md` — Definizione, schedule, dirty/clean price, current yield, YTM, formula prezzo Scheduled Investment
   - `asset-events/split.en.md` — Forward/reverse split, rapporti, impatto prezzo, motivazioni, adjusted prices
   - `asset-events/price-adjustment.en.md` — Write-down, haircut, mark-to-market, quando usare, formula Scheduled Investment
   - `asset-events/maturity-settlement.en.md` — Definizione, pull-to-par, zero-coupon, post-maturity, formula Scheduled Investment
   - Aggiunto sotto-menù `Asset Events` in `mkdocs.yml` con traduzioni IT/FR/ES
   - Aggiornato `financial-theory/index.en.md` con link
   - Aggiornato `user/assets/detail/data-editor.en.md` con docs completi (tab Prices/Events, CSV format, stale toggle, chart↔editor navigation)
   - Aggiornato `user/assets/detail/events.en.md` con link 📖 a ciascun tipo evento
   - Solo EN per ora — traduzione IT/FR/ES via pipeline AI successivamente

6. ✅ **Emoji tooltip evento nella tabella** — Nella colonna `type` del DataEditor eventi:
   - Righe **readonly** (auto): l'emoji ha `title="..."` con tooltip descrittivo (es. "Cash distribution from equity/ETF. Price drops on ex-date."), il nome del tipo è un `<a>` con link alla pagina docs corrispondente (apre in nuovo tab)
   - Righe **editabili**: select standard con emoji nel label (invariato)
   - Aggiunto `tooltip?: string` e `docsPath?: string` a `enumOptions` in `DataEditorTypes.ts`
   - `AssetDataEditorSection.svelte`: tooltip e docsPath configurati per ogni tipo evento

7. ✅ **FX banner traduzione non reattiva** — Fix: pattern `_i18n:` + `$derived.by` per risoluzione reattiva.

8. ✅ **Asset banner "no data for range" mancante** — Fix: stesso pattern del FX page.

### 🔜 B8 — Riorganizzazione Financial Theory docs: 4 sotto-alberi tematici

Ristrutturare `mkdocs_src/docs/financial-theory/` da flat list a 4 sotto-alberi tematici. Ogni sotto-pagina attuale viene splittata in file di dettaglio.

**Struttura target:**

```
📚 financial-theory/
├── index.en.md (hub — mappa concettuale con link a tutti i sotto-alberi)
│
├── 🏦 instruments/
│   ├── index.en.md (hub: cosa sono gli strumenti, come differiscono)
│   ├── asset-types/
│   │   ├── index.en.md (tabella riassuntiva di tutti i tipi)
│   │   ├── stocks.en.md
│   │   ├── etfs.en.md
│   │   ├── bonds.en.md
│   │   ├── crypto.en.md
│   │   ├── real-estate.en.md
│   │   └── index-benchmark.en.md
│   ├── transaction-types/
│   │   ├── index.en.md (tabella riassuntiva)
│   │   ├── buy-sell.en.md
│   │   ├── deposit-withdrawal.en.md
│   │   ├── dividend.en.md
│   │   ├── fee.en.md
│   │   ├── interest.en.md
│   │   └── transfer.en.md
│   └── asset-events/  (già esistente — mantenere struttura attuale)
│       ├── index.en.md → asset-events.en.md (rinomina)
│       ├── dividend.en.md ✅
│       ├── interest.en.md ✅
│       ├── split.en.md ✅
│       ├── price-adjustment.en.md ✅
│       └── maturity-settlement.en.md ✅
│
├── 📊 technical-analysis/
│   ├── index.en.md (cos'è l'analisi tecnica, quando usarla)
│   ├── indicators/  (split di technical-indicators.en.md)
│   │   ├── index.en.md (tabella riassuntiva)
│   │   ├── ema.en.md
│   │   ├── macd.en.md
│   │   ├── rsi.en.md
│   │   └── bollinger-bands.en.md
│   └── synthetic-benchmarks/  (split di synthetic-benchmarks.en.md)
│       ├── index.en.md
│       ├── linear.en.md
│       ├── compound.en.md
│       └── sine-wave.en.md
│
├── 📐 fundamentals/
│   ├── index.en.md (concetti base di finanza)
│   ├── day-count.en.md (da day-count.en.md — spostato)
│   ├── returns.en.md (da returns.en.md — spostato)
│   └── taxation.en.md (da taxation.en.md — spostato)
│
└── 📈 portfolio-theory/  (NUOVO)
    ├── index.en.md (cos'è la portfolio theory, panoramica)
    ├── diversification.en.md
    ├── asset-allocation.en.md
    └── risk-metrics/
        ├── index.en.md (tabella comparativa metriche)
        ├── sharpe-ratio.en.md
        ├── sortino-ratio.en.md
        ├── max-drawdown.en.md
        └── volatility.en.md
```

**Piano esecuzione:**

1. Creare la struttura di cartelle
2. Creare gli overview/index per ogni sotto-albero
3. Splittare `asset-types.en.md` in 6 sotto-file (stocks, ETFs, bonds, crypto, real-estate, index)
4. Splittare `transaction-types.en.md` in 6 sotto-file (buy/sell, deposit/withdrawal, dividend, fee, interest, transfer)
5. Splittare `technical-indicators.en.md` in 4 sotto-file (EMA, MACD, RSI, Bollinger)
6. Splittare `synthetic-benchmarks.en.md` in 3 sotto-file (Linear, Compound, Sine Wave)
7. Spostare `day-count`, `returns`, `taxation` sotto `fundamentals/`
8. Creare sezione `portfolio-theory/` con 4 pagine + sotto-albero `risk-metrics/` con 4 pagine
9. Aggiornare `mkdocs.yml` nav con la nuova struttura
10. Aggiornare tutti i cross-link interni
11. `mkdocs build --strict` per validare
12. Traduzione IT/FR/ES via pipeline AI

**Note:**
- Mantenere backward compatibility: i file vecchi possono diventare redirect o essere eliminati se `mkdocs build --strict` non si lamenta
- I file `asset-events/` esistenti (5 sotto-pagine EN) restano invariati, si spostano sotto `instruments/asset-events/`
- Solo EN per ora — traduzione come step finale

### 🔜 B9 — Portfolio Theory: contenuto pagine

Scrivere il contenuto delle 8 pagine sotto `portfolio-theory/`:

1. **index.en.md** — Cos'è la Modern Portfolio Theory (Markowitz), efficient frontier, risk-return tradeoff
2. **diversification.en.md** — Correlazione, riduzione varianza, systematic vs idiosyncratic risk, formule
3. **asset-allocation.en.md** — Strategic vs tactical, glide path, target-date, rebalancing
4. **risk-metrics/index.en.md** — Tabella comparativa: nome, formula, quando usarla, pro/contro
5. **risk-metrics/sharpe-ratio.en.md** — Formula, interpretazione, limiti (non distingue upside/downside volatility), esempio numerico
6. **risk-metrics/sortino-ratio.en.md** — Formula con downside deviation, confronto con Sharpe, quando preferirlo
7. **risk-metrics/max-drawdown.en.md** — Definizione (peak-to-trough), durata recovery, esempio grafico, formula
8. **risk-metrics/volatility.en.md** — Standard deviation, annualizzazione, realized vs implied, rolling window

## Further Considerations

### Formato CSV prezzi — minimo

```
┌─────────────────────────────────────────────────┐
│  📥 Import Prices CSV                     ? ✕   │
├─────────────────────────────────────────────────┤
│  [  Drop .csv/.txt file or click to browse  ]   │
│                                                  │
│  ℹ Minimum: date;currency;close                  │
│    Extended: date;currency;close;open;high;low;  │
│    volume. Use ;; to skip a column.        📖    │
│                                                  │
│  H │ date;currency;close                         │
│  ✓ │ 2024-01-15;USD;145.50                       │
│  ✓ │ 2024-01-16;USD;146.10                       │
│                                                  │
│  2 valid rows              [ Cancel ] [Import 2] │
└─────────────────────────────────────────────────┘
```

Formato esteso (colonne opzionali con `;;` per skip):

```
H │ date;currency;close;open;high;low;volume
✓ │ 2024-01-15;USD;145.50;144.00;146.20;143.80;
✓ │ 2024-01-16;USD;146.10;;;;1200000
✓ │ 2024-01-17;EUR;147.00
```

### Formato CSV eventi

```
┌─────────────────────────────────────────────────┐
│  📥 Import Events CSV                     ? ✕   │
├─────────────────────────────────────────────────┤
│  [  Drop .csv/.txt file or click to browse  ]   │
│                                                  │
│  ℹ Format: date;type;amount;currency;notes       │
│    Types: DIVIDEND, INTEREST, SPLIT,             │
│    PRICE_ADJUSTMENT, MATURITY_SETTLEMENT   📖    │
│                                                  │
│  H │ date;type;amount;currency;notes              │
│  ✓ │ 2024-03-15;DIVIDEND;1.25;USD;Q1 payout      │
│  ✓ │ 2024-06-01;SPLIT;2;;2:1 split               │
│  ✓ │ 2024-09-15;DIVIDEND;1.30;USD;               │
│                                                  │
│  3 valid rows              [ Cancel ] [Import 3] │
└─────────────────────────────────────────────────┘
```

### Tooltip emoji tipi evento nella tabella DataEditor

Esempio rendering nella colonna `type`:

`💰` (hover → Tooltip "Cash distribution from equity/ETF. Affects ex-date price.") + click → apre docs in nuovo tab. Accanto all'emoji: testo `DIVIDEND` (o select editabile per righe manuali). Serve una pagina MkDocs dedicata agli asset events o si punta a `/mkdocs/user/assets/events/`. Se non esiste, crearla come step preliminare.

### Modale FX — struttura estetica invariata

La modale FX rimane esteticamente identica all'attuale:

- Header: "Import CSV Data" + `?` help + `✕`
- Drop zone per .csv/.txt
- Direction bar: CurrencySearchSelect (disabled) → CurrencySearchSelect (disabled) con swap `⇄` + InfoBanner
- CsvEditor con header `date;FROM>TO` e validazione 2 colonne
- Footer: contatore valid rows + Cancel + Import

L'unico cambiamento è architetturale: `FxDataImportModal` wrappa `DataImportModal` generico, iniettando la direction bar nell'`headerSlot`.
