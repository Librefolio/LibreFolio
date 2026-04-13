# Plan: Part D — Bug Fix + Miglioramenti post-validazione Parte C (v2)

Validazione C1-C12 ha rivelato 2 bug e 9 miglioramenti. Questo piano incorpora i feedback: backend restituisce valori originali + convertiti in un solo fetch, dual Y-axis separata solo in abs mode, eventi nel sync toast con backend update, e test aggiornati.

---

## ✅ D1. Fix `sync_pairs_bulk` ritorna `None` (BLOCCANTE)

**File:** `backend/app/services/fx.py` — dopo riga 939

`_process_route()` (l.942) è definita ma mai invocata. La funzione `sync_pairs_bulk` termina senza `return` → `None` → 500.

**Fix applicata (13/04/2026):**
1. Aggiunto `pair_results = await asyncio.gather(*[_process_route(slug) for slug in pairs])`
2. Calcolato `success_count` e `total_changed` dai risultati
3. Assemblato `FXSyncBulkResponse(results, success_count, date_range, total_points_changed)`
4. Aggiunto import `DateRangeModel`

**Verifica:** `./dev.py test api fx` — **20/20 test passati** ✅

---

## ✅ D2. Fix navigazione "Go to" da signal card ricarica pagina

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` e `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

**Fix applicata (13/04/2026):**
Sostituito `goto(url)` con `window.open(url, '_blank')` nei 4 handler (`handleDetailAsset` e `handleDetailPair` in entrambe le pagine). Ora si apre in nuova scheda senza perdere stato.

---

## D3. Banner "FX data gap" su Asset Detail

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte`

Quando si converte valuta e la coppia FX sottostante ha dati che iniziano dopo la tail dell'asset, mostrare un banner di avviso.

**Steps:**
1. Dopo `loadChartData()`, dai dati restituiti (che ora contengono `original_close` per i punti convertiti — vedi D10), identificare la prima data dove la conversione è effettiva vs dove non lo è
2. `fxRangeStartsBeforeData` derived: true se il range visibile inizia prima del primo punto FX convertito
3. Banner sky-blue con icona `💱`, testo: _"FX rates available from {date} — earlier dates show unconverted prices"_
4. 1 chiave i18n (`assetDetail.fxDataAvailableFrom`) in 4 lingue

---

## D4. Bottone FX Sync in `AssetPriceSummary`

**File:** `frontend/src/lib/components/assets/AssetPriceSummary.svelte`

**Steps:**
1. Aggiungere prop `onsyncfx?: () => void` e `fxSyncing?: boolean`
2. Accanto al link FX pair (l.125-131), bottone `<RotateCw>` con spin durante sync
3. Nel parent, passare `onsyncfx={() => handleSyncPair(fxPairSlug)}` e `fxSyncing`
4. Visibile solo quando `showFxPairLink` è true (coppia FX configurata)

---

## ✅ D5. Sync toast con info Event Points + backend update

### ✅ D5a. Backend — eventi nel sync result

**Done (13/04/2026):**
1. Aggiunti `events_fetched: int = Field(0)` e `events_changed: int = Field(0)` a `FARefreshResult`
2. In `_persist_single()`, conteggio eventi separato da prezzi, variabili inizializzate prima del try block
3. `_upsert_asset_events()` già restituiva `int` (conteggio) — ora il valore viene catturato in `events_changed_count`
4. `./dev.py api sync` → client TypeScript rigenerato
5. **23/23 test asset_source passati**

### ✅ D5b. Frontend — toast con 2 righe

**Done (13/04/2026):**
Toast aggiornato: `💰 N↓ MΔ  📅 X↓ YΔ` — seconda parte visibile solo se `events_fetched > 0`. Import `goto` rimosso (non più usato).

---

## D6. "Original Value" in `CurrencySearchSelect`

**File:** `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte`

**Steps:**
1. Aggiungere prop `originalCurrency?: string`
2. Quando `originalCurrency` è fornito e `value !== originalCurrency`, inserire come prima opzione: `{value: originalCurrency, label: $t('assetDetail.originalValue') + ' (' + originalCurrency + ')', icon: '🔙'}`
3. Click → `value = originalCurrency`, dropdown si chiude, chart torna ai prezzi nativi
4. 1 chiave i18n (`assetDetail.originalValue`) in 4 lingue: EN "Original Value", IT "Valore Originale", FR "Valeur Originale", ES "Valor Original"
5. Nel parent `AssetPriceSummary`, passare `originalCurrency={assetCurrency}`

---

## D7. Data Editor i18n (colonne + bottoni)

**File:** `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` l.64-86

Le `label` nelle `priceColumns` ('Currency', 'Close', 'Open', etc.) e `eventColumns` ('Type', 'Amount', 'Notes') + le `eventTypeOptions` ('DIVIDEND', etc.) sono tutte hardcoded in inglese.

**Steps:**
1. Sostituire tutte le `label` con `$t('dataEditor.col.close')`, `$t('dataEditor.col.currency')`, etc.
2. Le label `eventTypeOptions` → `$t('assetDetail.eventType.DIVIDEND')`, etc.
3. Tradurre anche i `placeholder` visibili
4. ~15 chiavi i18n in 4 lingue via `./dev.py i18n add`
5. Verificare che `DataEditor.svelte` legga le label dinamicamente (riceve `ColumnDef[]` come prop → probabile OK)

---

## D8. Info valuta originale nella signal card di comparazione

**File:** `frontend/src/lib/components/charts/ChartSignalsSection.svelte` — area `configuredAssets` (l.537-605)

**Steps:**
1. Recuperare `findAssetInfo(assetIdStr)` per ottenere la valuta nativa dell'asset confrontato
2. Badge piccolo con valuta: `AAPL (USD)` accanto al nome nella card
3. Se conversione fallisce: messaggio esplicito nel warning con info sulle valute coinvolte

---

## D9. Spostare "Add Measure" nel panel header

**File:** `frontend/src/lib/components/charts/MeasurePanel.svelte` l.361-377

**Steps:**
1. Rimuovere il bottone dal body di MeasurePanel
2. `addMeasureFromChartData()` già esposto come `export function` — OK
3. Nel parent (pagina detail o `ChartSignalsSection`), aggiungere il bottone `+` nel header dell'accordion misure, allineato a destra con `flex justify-between`
4. Sempre visibile, anche con pannello chiuso

---

## D10. Dual Y-axis: valori originali in filigrana (MAJOR)

### ✅ D10a. Backend — `original_*` fields in FAPricePoint (single fetch)

**Done (13/04/2026):**
1. Aggiunti a `FAPricePoint`: `original_close`, `original_open`, `original_high`, `original_low` (tutti `Optional[Decimal]`)
2. Inclusi nel `@field_validator` per parsing Decimal
3. In `get_prices_bulk()`, i valori nativi vengono salvati nei campi `original_*` PRIMA di sovrascrivere con i valori convertiti
4. `./dev.py api sync` → client TypeScript rigenerato
5. Test aggiornati: verifiche `original_close` nel test di conversione + verifica `None` nel test senza conversione. **5/5 passati.**

### D10b. Frontend — ghost series + dual Y-axis

**File:** `frontend/src/lib/components/charts/PriceChartFull.svelte`, `frontend/src/lib/components/charts/LineChart.svelte` (interfaccia `LineDataPoint`)

**Come funziona il grafico (dal codice analizzato):**
- `data` → array di `LineDataPoint` (con `value`, `staleDays`, `fxStaleDays`, `originalCurrency`)
- `displayData` = in abs mode restituisce `data` tal quale; in % mode normalizza a `((v - p0) / p0) * 100`
- `overlaySignals` = `RenderedSignal[]` con `yAxisIndex` (0=main, 1=RSI, 2=MACD)
- Y-axes: `yAxis[0]` = main, `yAxis[1]` = RSI (nascosto se nessun segnale), `yAxis[2]` = MACD
- In % mode, comparisons usano il proprio p0 (`AssetComparisonSignal.render()` l.66) → tutte le curve partono da 0%

**Implementazione:**

1. Estendere `LineDataPoint` con `originalValue?: number` (mappato da `original_close`)
2. Nel parent `assets/[id]/+page.svelte`, popolare `originalValue` dal backend quando `target_currency` è attivo
3. In `PriceChartFull`, quando `displayData` contiene punti con `originalValue`:
   - **Abs mode:** Creare un nuovo `yAxis[3]` (quarta Y-axis), posizione `right`, nascosto (`show: false`, nessuna label), scala auto indipendente dal main. Aggiungere una serie ghost: stessi colori del main ma `opacity: 0.5`, `yAxisIndex: 3`, label = `{assetName} ({originalCurrency})`
   - **% mode:** La serie ghost usa `yAxisIndex: 0` (stessa Y principale) perché entrambe sono normalizzate a % rispetto al proprio p0 → partono da 0% e mostrano il delta relativo. La ghost mostra il rendimento % dell'asset in valuta originale vs il rendimento % in valuta convertita
4. Tooltip: mostrare entrambi i valori se ghost presente

### D10c. Segnali overlay con ghost originale

**File:** `frontend/src/lib/charts/signals/AssetComparisonSignal.ts`, `frontend/src/lib/charts/signals/FxPairSignal.ts`

Per i segnali comparison/FX pair:
1. Quando `targetCurrency` è diversa dalla valuta nativa, i dati del segnale includono sia convertiti che originali (dal backend tramite D10a)
2. Il segnale produce 2 `RenderedSignal` da `renderMulti()`: uno convertito (opaco) e uno ghost (opacity 0.5, label con valuta originale)
3. In abs mode: il ghost ha `yAxisIndex` dedicato (new axis nascosta). In % mode: `yAxisIndex: 0` (condiviso)
4. Label: `AAPL (EUR)` per il convertito, `AAPL (USD)` ghost

---

## D11. Misure dual-currency

**File:** `frontend/src/lib/components/charts/MeasurePanel.svelte`

Dipende da D10.

**Steps:**
1. Ricevere `originalData` (i valori nativi corrispondenti) come prop
2. Per ogni misura, calcolare risultati sia sui dati convertiti che originali
3. Nella card: riga 1 = display currency, riga 2 = original currency (con codice valuta appendato)
4. Riga 2 visibile solo quando conversione è attiva

---

## D12. C14b-d pendenti: Test coverage backend

| Step | Descrizione | Stima |
|------|-------------|-------|
| C14b | Test coverage `finance_utils`, `geo_utils`, `decimal_utils`, `cache_utils` | 30 min |
| C14c | Test coverage `global_settings_service`, `fx.py`, `static_uploads` | 30 min |
| C14d | Registrazione test in dev.py + verifica coverage | 5 min |

---

## Ordine di esecuzione

| # | Task | Tipo | Stima | Priorità |
|---|------|------|-------|----------|
| 1 | **D1** — Fix `sync_pairs_bulk` | 🐛 Bug | 5 min | 🔴 Bloccante |
| 2 | **D2** — Fix "Go to" navigation | 🐛 Bug | 5 min | 🔴 Alta |
| 3 | **D10a** — Backend: `original_*` fields in FAPricePoint | 🚀 Backend | 20 min | 🟠 Alta |
| 4 | **D5** — Backend: events count in sync + toast | 🚀 Backend+FE | 25 min | 🟡 Media |
| 5 | **D7** — Data Editor i18n | 🌐 i18n | 15 min | 🟡 Media |
| 6 | **D6** — "Original Value" in currency select | 🎨 UX | 10 min | 🟡 Media |
| 7 | **D4** — FX Sync button in AssetPriceSummary | 🎨 UX | 10 min | 🟡 Media |
| 8 | **D3** — Banner FX data gap | 🎨 UX | 15 min | 🟡 Media |
| 9 | **D8** — Info valuta nella card comparison | 🎨 UX | 10 min | 🟡 Media |
| 10 | **D10b** — Frontend: ghost series + dual Y-axis | 🚀 Feature | 40 min | 🟠 Alta |
| 11 | **D10c** — Ghost per overlay signals | 🚀 Feature | 25 min | 🟡 Media |
| 12 | **D9** — Spostare Add Measure in header | 🎨 UX | 10 min | 🟢 Bassa |
| 13 | **D11** — Misure dual-currency | 🚀 Feature | 20 min | 🟢 Bassa |
| 14 | **D12** — C14b-d test coverage | 🧪 Test | 65 min | 🟢 Bassa |

**Stima totale:** ~4h 35min

