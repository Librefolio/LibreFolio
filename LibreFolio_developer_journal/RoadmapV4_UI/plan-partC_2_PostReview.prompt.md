# Plan: Part C.2 — Fix post-review (v4)

Review di D1-D12 ha rivelato: 1 comportamento sbagliato (D2), 1 formato toast (D5), 1 cosmetico (D8), 1 bug live-price label + banner esteso (D3r), e un cluster ghost/dual-currency (D10r). Rispetto alla v3: il ghost mostra i **valori originali grezzi** senza scaling proporzionale (l'utente valuterà visivamente); il banner FX gap usa `original_close` null/presente per determinare la copertura.

---

## ✅ 1. D2r — Revertire `window.open()` a `goto()` con navigation stack

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (l.728-729, l.767-768), `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (l.636-637, l.660-661)

In tutti e 4 gli handler (`handleDetailAsset`, `handleDetailPair`): sostituire `window.open(url, '_blank')` con `goto(url)`. Ri-aggiungere `import {goto} from '$app/navigation'` dove rimosso. Il `navigationStore` traccia già la depth via `trackNavigation()` nell'app layout → `goBack()` funziona automaticamente.

**Fix applicata (13/04/2026):** Sostituito `window.open(url, '_blank')` con `goto(url)` in tutti e 4 gli handler. Re-aggiunto `import {goto} from '$app/navigation'` in asset page (FX page lo aveva già).

---

## ✅ 2. D5r — Toast sync multiline con `\n`

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (l.660-665, `handleSync()`)

Inserire `\n` tra riga prezzi e riga eventi nel messaggio toast. Il `whitespace-pre-line` già presente in `frontend/src/lib/components/ui/ToastContainer.svelte` (l.41) lo supporta nativamente. Mantenere le emoji `💰`/`📅` per ora. Risultato atteso:

```
Sincronizza prezzi:
💰 62↓ 1Δ
📅 1↓ 1Δ
```

**Fix applicata (13/04/2026):** Aggiunto `\n` tra titolo e prima riga, e tra riga prezzi e riga eventi. Emoji `💰`/`📅` mantenute.

---

## ✅ 3. D8r — Badge comparison con flag emoji

**File:** `frontend/src/lib/components/charts/ChartSignalsSection.svelte` (l.605-611)

`getCurrencyInfo` è già importato (l.21). Nel badge (l.608-609): cambiare `{currencyInfo.currency}` in `{getCurrencyInfo(currencyInfo.currency).flag_emoji} {currencyInfo.currency}` → mostra es. `🇺🇸 USD` anziché solo `USD`.

**Fix applicata (13/04/2026):** Aggiunto `getCurrencyInfo(currencyInfo.currency).flag_emoji` prima del codice valuta nel badge.

---

## ✅ 4. D3r — Banner FX data gap esteso + fix label valuta live price

Due fix in due file:

### ✅ 4a. Fix label valuta live price

**File:** `frontend/src/lib/components/assets/AssetPriceSummary.svelte` (l.84)

Quando `livePriceConversionFailed = true`, il prezzo mostrato è nativo ma il label dice `displayCurrency`. Fix: `{livePriceConversionFailed ? assetCurrency : displayCurrency}`.

**Fix applicata (13/04/2026):** Condizionale `{livePriceConversionFailed ? assetCurrency : displayCurrency}`.

### ✅ 4b. Banner FX gap esteso

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (l.193-197)

Espandere la logica `hasFxDataGap`. Attualmente è `true` solo se il primo punto chart ha `original_close == null` ma punti successivi ce l'hanno. Deve diventare `true` anche quando:
- La conversione è attiva (`displayCurrency !== assetCurrency && !fxConversionMissing`) ma **nessun punto** in `chartData` ha `original_close` (= 0 rate in DB, oppure tutti i rate sono successivi alla finestra).
- Oppure il primo punto con `original_close` è successivo a `dateStart` (= il primo rate in DB è dopo l'inizio della finestra selezionata).

La chiave è: se il backend per una data non torna nessun FX rate (nemmeno stale con backward fill), `original_close` è `null`. Se torna uno stale, `original_close` ha un valore (con `fx_days_back > 0`). Quindi basta verificare la presenza/assenza di `original_close` nel `chartData`.

Aggiungere chiave i18n `assetDetail.fxPairNoRates` in 4 lingue per il caso "0 rate totali" (banner arancione, distinto dal banner sky-blue "gap parziale").

**Fix applicata (13/04/2026):**
1. `hasFxDataGap` espanso: copre gap parziale + 0 rate + rate dopo finestra
2. Template con 2 banner distinti: sky-blue (gap parziale con data inizio), amber (0 rate con slug coppia)
3. Chiave i18n `assetDetail.fxPairNoRates` in 4 lingue

---

## ✅ 5. D10r — Rearchitettura ghost series (main chart)

**File:** `frontend/src/lib/components/charts/PriceChartFull.svelte`

### 5a. Eliminare yAxis[3]

Rimuovere l'asse nascosto (l.768-775). `ghostYAxisIndex = 0` sempre (eliminare il ternario l.637).

### 5b. Abs mode — valori originali grezzi

Nessun calcolo `k`. Semplicemente `ghostSeriesData = data.map(d => d.originalValue ?? null)` (invariato da attuale l.653). Entrambe le curve vivono su `yAxisIndex: 0` — la differenza di livello tra le due curve è l'impatto FX in valore assoluto. Custom Y min/max e zoom si applicano automaticamente.

### 5c. % mode — normalizzare al proprio p0

`((origVal - origP0) / origP0) * 100` (invariato da l.647-650). Entrambi partono da 0%. Aggiungere `void displayData;` nel `$effect` di rendering (l.182-199) per garantire re-render su switch abs↔%.

### 5d. Ghost label con 💱 + bandiera + valuta

A l.641, cambiare `ghostLabel` in `💱 ${mainSeriesLabel} (${flag} ${origCur})` dove `flag` viene passato dal parent come prop (es. `getCurrencyInfo(origCur).flag_emoji` calcolato nel parent page e passato tramite una nuova prop `originalCurrencyFlag?: string`). Es: `💱 Apple Inc. (🇺🇸 USD)`.

### 5e. Ghost inserito dopo main, prima degli overlay

Nella costruzione dell'array `series` (l.656), inserire la ghost series subito dopo `mainSeriesList` (output di `buildMainSeries`) e prima del loop sugli `overlaySignals`. Questo corregge l'ordine nel tooltip (ghost subito sotto il main, non in fondo).

### 5f. Tooltip — ghost escluso ma valore originale reale mostrato

Invariato (l.829, l.894-901). Il ghost è escluso dal loop principale, il valore originale reale appare accanto a "💱 Converted from…" in fondo al tooltip del main.

**Fix applicata (13/04/2026):**
1. yAxis[3] eliminato
2. Ghost sempre su yAxisIndex 0 (abs: valori grezzi, %: normalizzato a p0)
3. `void displayData` aggiunto al $effect per re-render su switch abs↔%
4. Ghost label: `💱 {nome} ({bandiera} {valuta})`
5. Ghost inserito subito dopo mainSeriesList, prima degli overlay
6. `originalCurrencyFlag` aggiunto a LineDataPoint e mappato nel parent

---

## ✅ 6. D10r-comp — Comparison: non scartare dati nativi quando conversione fallisce

**File:** `frontend/src/lib/charts/loadComparisonData.ts` (l.57-65)

### 6a. Non scartare prezzi nativi

Attualmente quando `hasConversionError = true`, `prices = []` (l.58-59) — scarta tutti i dati anche se il backend ha restituito prezzi in valuta nativa. Fix: passare i prezzi nativi comunque (senza `original_close` perché la conversione non è avvenuta). Aggiungere flag `_conversionFailed = true` (già fatto l.72) e `_nativeCurrency` per tracking.

### 6b. Ghost anche in abs mode per comparison

In `frontend/src/lib/charts/signals/AssetComparisonSignal.ts` → `renderMulti()` (l.98-146): produrre ghost anche in **abs mode** (non solo % mode). Abs: ghost = valori originali grezzi, label `💱 {nome} ({bandiera} {valuta})`. % mode: normalizzare al proprio p0, invariato.

### 6c. Triangle warning post-sync

In `frontend/src/routes/(app)/assets/[id]/+page.svelte` `handleSyncAsset()` (l.708-726), fare `overlayDataVersion++` DOPO `maybeLoadComparison()` per forzare il ricalcolo di `signalSummaries` → se ora ci sono punti, il triangolo ⚠️ scompare.

**Fix applicata (13/04/2026):**
1. `loadComparisonData.ts`: prezzi nativi passati sempre (non scartati su conversionError)
2. `AssetComparisonSignal.renderMulti()`: ghost prodotto in abs E % mode con label 💱
3. `originalCurrencyFlag` aggiunto ai dati di comparazione
4. `handleSyncAsset()`: `overlayDataVersion++` dopo `maybeLoadComparison()` per aggiornare triangle

---

## ✅ 7. D10r-measure — MeasurePanel: 💱 + bandiera + colore

**File:** `frontend/src/lib/components/charts/MeasurePanel.svelte` (l.353-368)

### 7a. Label riga `main-original`

A l.359, cambiare da `${mainSignalInfo.label} (${originalCurrencyCode})` a `💱 ${mainSignalInfo.label} (${flag} ${originalCurrencyCode})` dove `flag = getCurrencyInfo(originalCurrencyCode).flag_emoji`. Importare `getCurrencyInfo`.

### 7b. Colore segnale

`signalInfo.color`: usare il colore del main signal per coerenza visiva.

### 7c. Overlay ghost non esclusi

Per gli overlay ghost (quelli con `opacity < 1` prodotti da `renderMulti`): non escluderli (rimuovere il `continue` a l.373), ma mostrarli con la stessa convenzione `💱` + bandiera + valuta + pallino colore del parent signal.

**Fix applicata (13/04/2026):**
1. Label `main-original`: `💱 {nome} ({bandiera} {valuta})` con colore main signal
2. Ghost overlay (opacity < 1) non più esclusi — mostrati con label 💱 e colore parent
3. Import `getCurrencyInfo` aggiunto

---

## 8. D13 — Code cleanup review

Step finale dopo tutti i fix. Scope:
- Import inutilizzati (es. `EVENT_COLORS` usato o no in PriceChartFull).
- Funzioni esportate mai chiamate.
- Chiavi i18n orfane.
- Dead CSS / componenti Svelte inutilizzati.
- Coverage test gap.
- Documentare i findings.

---

## Considerazioni

1. **Ghost senza scaling in abs mode**: le due curve (convertita e originale) vivranno su scale diverse sullo stesso asse (es. Apple EUR ~220 vs Apple USD ~240). La differenza di livello visualizza l'impatto FX. Dopo la review visiva, l'utente deciderà se introdurre lo scaling proporzionale `k` per farle partire dallo stesso punto.
2. **Prop `originalCurrencyFlag`**: PriceChartFull opera con HTML puro (ECharts). Per usare la bandiera nel ghost label, il parent page calcola `getCurrencyInfo(origCur).flag_emoji` e lo passa come stringa. Alternativa: passare il codice valuta e fare il lookup dentro PriceChartFull (ma richiede import aggiuntivo in un componente chart-only).
3. **D3r backend check**: Non serve nessun campo aggiuntivo dal backend. `original_close` nel `chartData` è sufficiente: presente (anche con `fx_days_back > 0`) = FX rate trovato (anche stale); assente = nessun FX rate per quella data (il primo punto in DB è successivo).

---

## ➡️ Seguito: Part C.3 — Post-Review round 2

La review di C.2 ha rivelato: D2r non ricarica il componente su `goto()`, toast ancora con emoji invece di icone Lucide, label valuta mancante quando FX pair non configurata, layout prezzo/% invertito, e tooltip/measure con label ghost da ristrutturare.
Vedi → [plan-partC_3_PostReview2.prompt.md](plan-partC_3_PostReview2.prompt.md)
