# Plan: C.4 — Multi-FX Comparison: staircase, banner, sync-all & currency labels

**TL;DR**: Quando ci sono comparison asset con valute diverse (Apple USD + Enel EUR, display RON), servono più coppie FX. L'attuale sistema non le gestisce: il grafico mostra "gradini" (staircase), i banner non dicono quale coppia FX fallisce, e non si può fare sync/create delle FX mancanti. Il piano risolve: (1) eliminare lo staircase filtrando i punti non convertiti, (2) aggiungere banner per-pair e controlli FX nelle card dei comparison, (3) trasformare il bottone sync in filter bar in un "sync all" con modale, (4) aggiungere valuta a tutti i label.

---

## ✅ Step 1 — Fix staircase: filtrare i punti non convertiti nei comparison

**Il problema spiegato nel dettaglio:**

Scenario: display currency = RON. Comparison Enel (nativa EUR). Chiedi al backend `query_prices(enel, target_currency=RON)`.

Il backend prova a convertire **ogni punto** EUR→RON. Per le date dove il rate EUR/RON esiste, il punto ritorna convertito:
```
date: 2026-01-15, close: 231.50 (RON), original_close: 46.30 (EUR)  ✅ convertito
```

Per le date dove il rate EUR/RON **non** esiste (perché la coppia ha dati solo dal 2026-01-13 in poi, ad esempio), il punto ritorna **inalterato** nella valuta nativa:
```
date: 2025-04-14, close: 45.80 (EUR), original_close: null           ❌ non convertito
```

Il campo `close` (che il frontend mappa a `value`) contiene quindi un **mix di valute**: alcuni valori in EUR (~46), altri in RON (~230). Sul grafico questo produce una linea che salta da ~46 a ~230 — il "gradino"/staircase.

**Fix**: In `frontend/src/lib/charts/loadComparisonData.ts`, quando `targetCurrency` è stato passato, distinguere i punti convertiti dai non-convertiti. Un punto **non convertito** si riconosce perché ha `original_close == null` E `original_currency == null` (il backend non ha toccato il punto). Per questi punti, impostare `value: null` → il grafico mostra un gap (linea interrotta) dove mancano i rate FX, invece di saltare tra due scale di valuta.

Concretamente, passare `targetCurrency` alla funzione di mapping e aggiungere:
```
value: (targetCurrency && p.original_close == null && p.currency !== targetCurrency) 
       ? null   // punto non convertito → gap
       : Number(p.close ?? 0)
```

---

## ✅ Step 2 — Currency label su TUTTI i segnali in tooltip e misura

Aggiungere `currency?: string` e `currencyFlag?: string` a `RenderedSignal` in `frontend/src/lib/charts/signals/ChartSignal.ts`.

- **AssetComparisonSignal** in `frontend/src/lib/charts/signals/AssetComparisonSignal.ts`: nel `render()`, popolare `currency` e `currencyFlag`. Se la conversione è attiva (ha `originalValue`), `currency = displayCurrency`. Se non è attiva, `currency = nativeCurrency` dell'asset. La nativa arriva dal parent: già presente in `allAssets[].currency`, da passare tramite `cfg.params._assetCurrency`.
- **Tooltip** in `frontend/src/lib/components/charts/PriceChartFull.svelte`: per ogni overlay signal nel loop, se ha `currency`/`currencyFlag`, appendere `(flag currency)` al label. Idem per il main signal (già fatto in C.3 per `displayCurrency`).
- **MeasurePanel** in `frontend/src/lib/components/charts/MeasurePanel.svelte`: stessa logica — leggere `signal.currency`/`signal.currencyFlag` dall'overlay e appendere al label della riga.

---

## ✅ Step 3 — Banner FX dedicato per ogni coppia problematica + controlli nelle card comparison

### 3a. Derivata `requiredFxPairs`

In `frontend/src/routes/(app)/assets/[id]/+page.svelte`: calcolare tutte le coppie FX necessarie, da main + comparison signals. Per ogni comparison signal con valuta nativa diversa da `displayCurrency`, determinare lo slug FX canonico e lo stato (`'ok'` / `'missing'` / `'no-data'`).

### 3b. Banner per-pair

Sostituire l'attuale banner singolo `hasFxDataGap` con un loop su `requiredFxPairs.filter(p => p.status !== 'ok')`. Ogni banner mostra:
- La pair specifica: `💱 EUR/RON — ...`
- Messaggio: "Coppia non configurata" (missing) o "Nessun rate nel periodo" (no-data) o "Rate disponibili dal..." (partial gap)
- Azioni: [➕ Crea pair] se missing, [🔄 Sync] se no-data/partial, [↗ Vai alla pair] se esiste
- Componente riusabile `FxStatusBanner` con props `{slug, status, message, onCreate, onSync, onGoto}`

### 3c. Controlli FX nella card del comparison signal

In `frontend/src/lib/components/charts/ChartSignalsSection.svelte`: nella riga di ogni comparison signal, accanto al badge valuta esistente (`🇪🇺 EUR`), aggiungere:
- Se la coppia FX per quel comparison verso `displayCurrency` manca: icona ⚠ + bottone [➕ Crea]
- Se esiste ma ha errore di conversione (`_conversionFailed`): icona ⚠ + bottone [🔄 Sync]
- Se esiste e funziona: bottone [↗ Vai alla pair FX]

Serve passare a ChartSignalsSection nuove prop: `displayCurrency`, `allConfiguredFxSlugs`, `onCreateFxPair(slug)`, `onSyncFxPair(slug)`.

---

## ✅ Step 4 — Sync-All dalla filter bar: modale con 2 sezioni (Asset + FX)

Trasformare il bottone sync nella filter bar da "sync solo l'asset corrente" a **"sync everything on page"**:

### 4a. Raccogliere tutti i target

- **Assets**: main asset + tutti i comparison asset attivi (dai signal configs). Solo quelli con provider.
- **FX pairs**: main FX pair (se conversione attiva) + tutte le FX pair necessarie ai comparison. Solo quelle configurate.

### 4b. Due chiamate bulk in parallelo

- `sync_prices_bulk([main_asset, comp_1, comp_2, ...])` — endpoint già bulk
- `sync_rates({pairs: [USD-RON, EUR-RON, ...], start, end})` — endpoint già bulk

### 4c. Modale a 2 sezioni

Creare un nuovo componente `PageSyncModal` (o riusare/comporre `AssetSyncModal` + `FxSyncModal`) che mostra:
- **Sezione 1 — Assets**: lista di risultati come `AssetSyncModal` (icona, nome, punti, provider, retry)
- **Sezione 2 — FX Pairs**: lista di risultati come `FxSyncModal` (slug, punti, provider, retry)

Entrambe le sezioni dentro la stessa `ModalBase`. Al termine di entrambe le sync, fare `handleRefresh()` + `maybeLoadComparison()` per aggiornare tutto.

I sotto-componenti per le righe dei risultati sono gli snippet `resultRow` già definiti in `AssetSyncModal` e `FxSyncModal` — estrarre come componenti standalone per riusarli nella modale composita.

---

## ✅ Step 5 — Creare FX pair per comparison dal banner/card

Se una coppia FX per un comparison non esiste, il bottone [➕] apre `FxPairAddModal` con `base`/`quote` pre-compilati (componente già esistente, usato per la coppia principale). Dopo la creazione:
1. Aggiornare `allConfiguredFxSlugs` (ri-fetch)
2. Ricaricare i dati del comparison (`maybeLoadComparison()`)
3. Aggiornare i banner

---

## Considerazioni

1. **Gap vs interpolazione nel staircase**: Il gap (linea interrotta) è la scelta più onesta: mostra chiaramente dove mancano i rate FX. L'utente vede il buco e può fare sync della pair. Interpolare o lasciare i punti nativi sarebbe fuorviante.

2. **Segnali tecnici**: Confermato — EMA, MACD, RSI, Bollinger, ecc. operano sui dati del segnale principale (già nella valuta target). Non serve aggiungere currency label ai segnali tecnici.

3. **Banner dedicato per pair**: Confermato come approccio. Componente `FxStatusBanner` riusabile.

4. **Controllo utente**: Confermato — nessun auto-sync. L'utente decide quando creare/sincronizzare.

5. **Ordine di implementazione consigliato**: Step 1 (staircase) → Step 2 (currency labels) → Step 3 (banner + card controls) → Step 4 (sync-all modal) → Step 5 (create pair). Step 1 e 2 sono indipendenti e possono essere paralleli.

---

## ➡️ Seguito: Part C.5 — Rifinitura UX post-review completa

La review completa di C.4 ha rivelato: errore Svelte (`}}`), necessità di SearchSelect per comparison, stili linea differenziati per categoria, banner FX con bandiere/icone Lucide, SyncModal da riarchitettare su sezioni, fix pannello misure e allineamento tabella.
Vedi → [plan-partC_5_UxRefinement.prompt.md](plan-partC_5_UxRefinement.prompt.md)

