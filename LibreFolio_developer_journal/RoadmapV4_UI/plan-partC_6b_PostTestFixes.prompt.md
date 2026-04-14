# Plan: C.6b — Fix post-test C.6

Post-test di C.6: fix banner icona mancante, refresh overlay dopo sync-all, toast FX 3 righe, revert mobile banner buttons, goto FX con timeframe, icone asset nelle sync modali, nota weekend, ridisegno ghost signals (opacity 0.8 chart, riga intera sbiadita in tooltip/tabella).

---

## Step 1 — Ghost signals: opacity 0.8, lineWidth 1, tooltip/tabella riga intera sbiadita ✅

**1a.** In `PriceChartFull.svelte` (~riga 490): ghost del main → `opacity: 0.8` (da 0.4).

**1b.** In `AssetComparisonSignal.ts` (~riga 160): ghost comparison → `opacity: 0.8` (da 0.4).

**1c.** In `PriceChartFull.svelte` tooltip (~riga 843-879): per main ghost e overlay ghost (`sigInfo.isGhost`), wrappare l'intera riga HTML (label+value+delta) in `<span style="opacity:0.7">` — effetto uniforme su testo, bandiere e dot.

**1d.** In `signalLabel.ts` (~riga 63): rimuovere `dotOpacity = info.isGhost ? 'opacity:0.4;' : ''`. Il dot è sempre pieno — la trasparenza è gestita dal wrapper padre.

**1e.** In `MeasurePanel.svelte` `buildSummaryRows()`: aggiungere `isGhost?: boolean` a `MeasureSummaryRow`, settarlo per le righe ghost. In `summaryColumns`, la cell render applica `opacity:0.7` all'HTML dell'intera riga quando `isGhost`.

---

## Step 2 — Fix banner "Data available" — icona asset con fallback `asset_type` ✅

In `+page.svelte` (asset detail) riga 1052: aggiungere `{:else if assetInfo.asset_type}` con PNG fallback da `getAssetTypeIconUrl()`, importandolo da `assetTypes`.

---

## Step 3 — Fix refresh overlay dopo sync-all ✅

In `+page.svelte` (asset detail) `handleRefresh()` riga 760: aggiungere loop su signal `fx-pair` per invalidare/re-fetch gli FX overlay stores (stessa logica del FX detail page riga 511-531 con `invalidateRange` + `convert_currency_bulk`).

---

## Step 4 — Toast FX su 3 righe ✅

In `syncToastHelpers.ts`: formato ok → `Synced:\n{pairLabel}\n{dataLine} {providerHtml}` (idem partial/failed).

---

## Step 5 — Revert mobile banner buttons ✅

In `+page.svelte` (asset detail) riga 1096: rimuovere `order-first sm:order-none self-end sm:self-auto`, tornare a solo `sm:ml-auto`.

---

## Step 6 — Goto FX con timeframe ✅

In `+page.svelte` (asset detail) riga 1105: `href="/fx/{pair.slug}?start={dateStart}&end={dateEnd}"`.

---

## Step 7 — Icone asset nel PageSyncModal ✅

In `PageSyncModal.svelte`: aggiungere `asset_type` a `AssetSyncItem`, usarlo come fallback icon nella result row. Aggiornare `syncAllAssets` nelle pagine asset detail e FX detail per passare `asset_type`.

---

## Step 8 — Nota weekend nel banner data gap ✅

In `+page.svelte` (asset detail): se `dateStart` cade di sabato/domenica, aggiungere hint i18n (*selected start date falls on a weekend — try adjusting*).

---

## Considerazioni

- **Ghost opacity unificata a 0.8:** sul grafico il ghost sarà chiaramente visibile ma distinguibile dal parent (lineWidth 1 vs 2, opacity 0.8 vs 1.0). Nel tooltip e nella tabella misure l'intera riga è al 70% di opacità (uniforme su dot, bandiere, testo).

---

## Collegamento ai piani precedenti

- Piano precedente: [C.6 — Post-test UX Polish](plan-partC_6_PostTestPolish.prompt.md)
- Piano origine: [C.5 — UX Refinement](plan-partC_5_UxRefinement.prompt.md)

---

## ➡️ Seguito: C.7 — Core-level Cache + Thread Isolation per Asset Providers

Layer centralizzato di cache e isolamento thread in `asset_source.py` per tutti i provider: cache smart range per history, TTL per current/metadata, cache a due livelli per search, ed esecuzione di ogni provider in thread dedicato.
Vedi → [plan-partC_7_AssetProviderCoreCache.prompt.md](plan-partC_7_AssetProviderCoreCache.prompt.md)

