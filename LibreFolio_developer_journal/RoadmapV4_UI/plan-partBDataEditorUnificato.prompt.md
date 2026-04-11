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

### B5 — `AssetDataEditorSection.svelte`: orchestratore a 2 tab

Due tab (Prices / Events), ciascuno con la propria istanza `DataEditor`. Prezzi: colonne `currency` (string, required, editabile), `close` (number, required), `open/high/low/volume` (number, optional). `rowId = date`. Eventi: colonne `type` (enum con emoji: `💰 DIVIDEND`, `📈 INTEREST`, `✂️ SPLIT`, `📊 PRICE_ADJUSTMENT`, `🏁 MATURITY`), `amount` (number, required), `currency` (string, optional), `notes` (string, optional). `rowId = String(event.id)` o `crypto.randomUUID()`. Righe auto (`is_auto`) → `readonly: true`, eliminabili. Emoji tipo: hover → `Tooltip` con descrizione sintetica, click → `window.open(docsUrl, '_blank')` a pagina eventi docs. Salvataggio: bottone Save invia entrambi i tab se almeno uno ha dirty count > 0 (endpoint separati). Al successo → refresh dati (niente preview persistente). Save/Cancel bar unica in basso. Integra in `frontend/src/routes/(app)/assets/[id]/+page.svelte` al posto del placeholder 🚧.

### ✅ B6 — Test E2E + fix link docs + test backend

- **Fix `HelpMenu.svelte`** righe 48 e 57: aggiungere `target="_blank" rel="noopener noreferrer"` ai link FAQ e Documentation.

- **Estendere `fx-data-editor.spec.ts`**: test apertura modale CSV import (`click "Import CSV"` → modale visibile), swap ⇄ funziona, paste CSV valido → contatore valid rows, click Import → righe aggiunte alla tabella, chiusura con dati dirty mostra confirm discard.

- **Nuovo `e2e/assets/asset-data-editor.spec.ts`**: test apertura editor dati, 2 tab visibili, switch tab, apertura modale CSV import prezzi (header corretto `date;currency;close`), paste CSV prezzi valido, import, apertura modale CSV import eventi, paste CSV eventi valido, import. Test salvataggio (save con dirty → API call → refresh dati).

- **Backend test: `test_assets_events.py` (8 test)**:
  1. Bulk upsert manual events
  2. Query events with id + is_auto
  3. Delete event by ID + verify deletion
  4. Delete non-existent event returns success=False
  5. Upsert same date+type replaces manual event
  6. Query empty date range returns 0 events
  7. Upsert for non-existent asset returns count=0
  8. Multiple event types on same date coexist

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
