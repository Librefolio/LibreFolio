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

## ✅ D3. Banner "FX data gap" su Asset Detail

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte`

**Done (13/04/2026):**
1. Aggiunto `fxFirstConvertedDate` derived: trova prima data con `original_close` presente
2. Aggiunto `hasFxDataGap` derived: true se primo punto chart non ha conversione ma punti successivi sì
3. Banner sky-blue con icona `💱`, testo i18n `assetDetail.fxDataAvailableFrom`
4. Chiave i18n in 4 lingue (EN/IT/FR/ES)

---

## ✅ D4. Bottone FX Sync in `AssetPriceSummary`

**File:** `frontend/src/lib/components/assets/AssetPriceSummary.svelte` + parent page

**Done (13/04/2026):**
1. Aggiunte prop `onsyncfx?: () => void` e `fxSyncing?: boolean`
2. Aggiunto import `RotateCw` e bottone sync con spin animation accanto al link FX pair
3. Visibile solo quando `showFxPairLink` e `onsyncfx` sono truthy
4. Nel parent: aggiunto stato `fxSyncing`, wrappato `handleSyncPair` con `fxSyncing = true/false`
5. Dopo FX sync, richiamato `loadChartData()` per aggiornare la conversione
6. Passato `onsyncfx` e `fxSyncing` nel template

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

## ✅ D6. "Original Value" in `CurrencySearchSelect`

**File:** `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte` + `AssetPriceSummary.svelte`

**Done (13/04/2026):**
1. Aggiunta prop `originalCurrency?: string`
2. Quando `originalCurrency` è fornito e `value !== originalCurrency`, inserita come prima opzione: icon `🔙`, label con `$_('assetDetail.originalValue') + ' (' + originalCurrency + ')'`
3. Chiave i18n `assetDetail.originalValue` in 4 lingue: EN "Original Value", IT "Valore Originale", FR "Valeur Originale", ES "Valor Original"
4. Nel parent `AssetPriceSummary`, passato `originalCurrency={assetCurrency}`

---

## ✅ D7. Data Editor i18n (colonne + bottoni)

**File:** `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` + 4 JSON i18n

**Done (13/04/2026):**
1. Convertiti `priceColumns`, `eventTypeOptions`, `eventColumns` da `const` a `$derived` per reattività al cambio lingua
2. Tutte le `label` sostituite con `$t('dataEditor.col.*')` (9 chiavi: currency, close, open, high, low, volume, type, amount, notes)
3. Le label `eventTypeOptions` ora usano `$t('assetDetail.eventType.DIVIDEND')` etc. (erano hardcoded come `'DIVIDEND'`)
4. Bottoni Save/Cancel tradotti: `$t('dataEditor.save', {values: {count}})`, `$t('dataEditor.saving')`, `$t('dataEditor.cancel')`
5. 12 nuove chiavi i18n in 4 lingue (EN/IT/FR/ES)

---

## ✅ D8. Info valuta originale nella signal card di comparazione

**File:** `frontend/src/lib/components/charts/ChartSignalsSection.svelte` + parent page

**Done (13/04/2026):**
1. Aggiunto `currency?: string` al tipo `availableAssets` (ChartSignalsSection + parent page)
2. Nel parent, incluso `currency: a.currency` nel mapping da API response
3. Badge `<span>` con codice valuta (font-mono, bg grigio) accanto ai bottoni sync/detail nella card comparison
4. Visibile solo quando `findAssetInfo(assetIdStr)?.currency` è truthy

---

## ✅ D9. Spostare "Add Measure" nel panel header

**File:** `frontend/src/lib/components/charts/MeasurePanel.svelte` + pagine detail

**Done (13/04/2026):**
1. Rimosso bottone "Add Measure" dal body di MeasurePanel, rimosso import `Plus`
2. In entrambe le pagine detail (asset + FX): trasformato accordion header da singolo `<button>` a `<div>` con `flex justify-between`
3. Bottone `+` a destra nell'header: sempre visibile, `e.stopPropagation()` per non triggere il toggle, auto-apre il pannello prima di aggiungere la misura
4. Stile coerente: violet-50 bg, arrotondato, disabilitato se `lineData.length < 2`

---

## D10. Dual Y-axis: valori originali in filigrana (MAJOR)

### ✅ D10a. Backend — `original_*` fields in FAPricePoint (single fetch)

**Done (13/04/2026):**
1. Aggiunti a `FAPricePoint`: `original_close`, `original_open`, `original_high`, `original_low` (tutti `Optional[Decimal]`)
2. Inclusi nel `@field_validator` per parsing Decimal
3. In `get_prices_bulk()`, i valori nativi vengono salvati nei campi `original_*` PRIMA di sovrascrivere con i valori convertiti
4. `./dev.py api sync` → client TypeScript rigenerato
5. Test aggiornati: verifiche `original_close` nel test di conversione + verifica `None` nel test senza conversione. **5/5 passati.**

### ✅ D10b. Frontend — ghost series + dual Y-axis

**File:** `frontend/src/lib/components/charts/PriceChartFull.svelte`, `LineChart.svelte`, `assets/[id]/+page.svelte`

**Done (13/04/2026):**
1. Esteso `LineDataPoint` con `originalValue?: number`
2. Nel parent, mappato `original_close` → `originalValue` in `lineData`
3. In `PriceChartFull.renderChart()`:
   - Rilevamento `hasOriginalValues` dalla data
   - **Abs mode**: ghost su yAxis[3] (nascosta, scala indipendente). Serie dashed con opacity 0.4
   - **% mode**: ghost su yAxis[0] (condivisa), valori normalizzati al proprio p0 originale
   - Ghost label = `{mainSeriesLabel} ({originalCurrency})`
4. yAxis[3] aggiunta: nascosta, scale=true, nessuna label/tick
5. Tooltip: valore originale mostrato accanto a "Converted from {currency}" label
6. Ghost series esclusa dal tooltip loop principale (mostrata via "💱" label)

### ✅ D10c. Segnali overlay con ghost originale

**File:** `frontend/src/lib/charts/signals/AssetComparisonSignal.ts`, `frontend/src/lib/charts/signals/ChartSignal.ts`, `frontend/src/lib/charts/loadComparisonData.ts`, `PriceChartFull.svelte`

**Done (13/04/2026):**
1. Aggiunto `opacity?: number` a `RenderedSignal` interface
2. PriceChartFull: applica `opacity` da RenderedSignal a `lineStyle` e `itemStyle`, z=0 per ghost
3. `loadComparisonData.ts`: include `originalValue` e `originalCurrency` nella resolved data
4. `AssetComparisonSignal.renderMulti()`: override che produce ghost signal in % mode quando original values presenti
   - Ghost label: `{assetName} ({originalCurrency})`
   - Ghost: opacity 0.4, dashed, lineWidth 1, yAxisIndex 0
   - Solo in % mode (in abs mode le scale assolute di valute diverse non si allineano)
5. Ghost excluded dal tooltip loop in PriceChartFull

---

## ✅ D11. Misure dual-currency

**File:** `frontend/src/lib/components/charts/MeasurePanel.svelte`

**Done (13/04/2026):**
1. Aggiunto `originalChartData` derived: filtra `chartData` per punti con `originalValue`, costruisce array di `LineDataPoint` con valori nativi
2. Aggiunto `originalCurrencyCode` derived dal primo punto con `originalCurrency`
3. In `buildSummaryRows()`: quando conversion attiva, aggiunta riga extra `main-original` con misurazioni sui dati originali
   - Label: `{mainSignalInfo.label} ({originalCurrencyCode})`
   - Usa `getMeasurementForSignal(originalChartData)` per calcolare delta/% sui valori nativi
4. Ghost overlay signals (opacity < 1) esclusi dalle righe summary per evitare duplicati

---

## ✅ D12. C14b-d pendenti: Test coverage backend

**Done (13/04/2026):**

| Step | Descrizione | Status |
|------|-------------|--------|
| C14b | Test `cache_utils.py`: 17 test (NamedCache set/get/delete/clear, TTL expiration, registry, stats, list_caches) | ✅ |
| C14b | Test `decimal_utils`, `geo_utils`, `sector_fin_utils`, `currency_utils` | ✅ (pre-esistenti, 6/6 passati) |
| C14d | Registrazione `cache-utils` in dev.py test runner + verifica | ✅ 7/7 `./dev.py test utils all` |

---

## Ordine di esecuzione

| # | Task | Tipo | Stima | Priorità |
|---|------|------|-------|----------|
| 1 | **D1** — Fix `sync_pairs_bulk` | 🐛 Bug | 5 min | ✅ Done |
| 2 | **D2** — Fix "Go to" navigation | 🐛 Bug | 5 min | ✅ Done |
| 3 | **D10a** — Backend: `original_*` fields in FAPricePoint | 🚀 Backend | 20 min | ✅ Done |
| 4 | **D5** — Backend: events count in sync + toast | 🚀 Backend+FE | 25 min | ✅ Done |
| 5 | **D7** — Data Editor i18n | 🌐 i18n | 15 min | ✅ Done |
| 6 | **D6** — "Original Value" in currency select | 🎨 UX | 10 min | ✅ Done |
| 7 | **D4** — FX Sync button in AssetPriceSummary | 🎨 UX | 10 min | ✅ Done |
| 8 | **D3** — Banner FX data gap | 🎨 UX | 15 min | ✅ Done |
| 9 | **D8** — Info valuta nella card comparison | 🎨 UX | 10 min | ✅ Done |
| 10 | **D10b** — Frontend: ghost series + dual Y-axis | 🚀 Feature | 40 min | ✅ Done |
| 11 | **D10c** — Ghost per overlay signals | 🚀 Feature | 25 min | ✅ Done |
| 12 | **D9** — Spostare Add Measure in header | 🎨 UX | 10 min | ✅ Done |
| 13 | **D11** — Misure dual-currency | 🚀 Feature | 20 min | ✅ Done |
| 14 | **D12** — C14b-d test coverage | 🧪 Test | 65 min | ✅ Done |

**Tutti i 14 task completati.** ✅

---

## ➡️ Seguito: Part C.2 — Post-Review

La review manuale di D1-D12 ha rivelato 1 comportamento sbagliato (D2), 1 formato toast (D5), 1 cosmetico (D8), 1 bug live-price label + banner esteso (D3r), e un cluster ghost/dual-currency (D10r).
Vedi → [plan-partC_2_PostReview.prompt.md](plan-partC_2_PostReview.prompt.md)
