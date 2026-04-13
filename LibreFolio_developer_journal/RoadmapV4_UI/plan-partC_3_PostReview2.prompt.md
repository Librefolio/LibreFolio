# Plan: Part C.3 — Fix post-review round 2

Dalla review di C.2 emergono 7 problemi + 1 pending da C.2. Il più critico è D2r (navigazione non ricarica la pagina), seguito da ristrutturazione tooltip/label, swap layout prezzo/%, e standardizzazione toast sync.

---

## 1. ✅ D2r-fix — Navigazione `goto()` non ricarica il componente

Il problema: SvelteKit riusa la stessa istanza del componente quando si naviga tra `/assets/1` e `/assets/11` (stesso pattern di route). `onMount` non ri-esegue. Il `data.assetId` cambia (viene dal `+page.ts` load function), ma nessun `$effect` osserva quel cambio per ricaricare i dati.

**Fix:** In `frontend/src/routes/(app)/assets/[id]/+page.svelte`, aggiungere un `$effect` che osserva `data.assetId` e ri-esegue tutta la sequenza di caricamento (`loadAssetInfo`, `loadChartData`, etc.) — stessa logica dell'`onMount` ma triggerata dal cambio di `assetId`. Eventualmente estrarre il corpo dell'`onMount` in un `async function reload()` chiamata sia da `onMount` che dall'`$effect`.

**Implementazione:** Estratto `reloadPage()` da `onMount`. Aggiunto `$effect` su `data.assetId` con tracking via `_prevAssetId` (plain `let`, non `$state`, per evitare warning Svelte). Cast `assetInfo as AssetDetail | null` dopo il `Promise.all` per evitare narrowing TypeScript a `never`.

---

## 2. ✅ D5r-fix — Toast con `{@html}` e icone Lucide

Tre file:
- `frontend/src/lib/components/ui/ToastContainer.svelte` (l.41): cambiare `{toast.message}` in `{@html toast.message}`.
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` `handleSync()`: usare SVG inline di `DollarSign` e `CalendarClock` (stringhe SVG raw, non componenti Svelte — perché il toast è una stringa, non un template). Alternativa: renderizzare piccoli `<svg>` inline nel messaggio HTML.

**Implementazione:** Cambiato `{toast.message}` in `{@html toast.message}` in ToastContainer.svelte. Creato `syncToastHelpers.ts` con SVG inline di DollarSign e CalendarClock.

---

## 3. ✅ D3r-fix — Label valuta quando FX pair non configurata

In `frontend/src/lib/components/assets/AssetPriceSummary.svelte` (l.84): la condizione attuale `livePriceConversionFailed ? assetCurrency : displayCurrency` non copre il caso `fxConversionMissing`. Quando la coppia non è nemmeno configurata, il prezzo mostrato è sempre nativo → mostrare `assetCurrency`. Fix: `{(livePriceConversionFailed || fxConversionMissing) ? assetCurrency : displayCurrency}`.

**Implementazione:** Condizione aggiornata a `{(livePriceConversionFailed || fxConversionMissing) ? assetCurrency : displayCurrency}`.

---

## 4. ✅ Layout swap: prezzo prima, % dopo

In `frontend/src/lib/components/assets/AssetPriceSummary.svelte` (l.70-97) e `frontend/src/lib/components/fx/FxPriceSummary.svelte` (l.30-43): invertire l'ordine dei blocchi. Il prezzo assoluto (font-mono text-lg) viene prima, il delta % (text-xs) dopo.

**Implementazione:** Invertito ordine in entrambi i componenti: prezzo (font-mono text-lg) a sinistra, delta % (text-xs) a destra.

---

## 5. ✅ D10r-tooltip — Ristrutturare tooltip: ghost dopo main, no "Converted from", label con bandiera

In `frontend/src/lib/components/charts/PriceChartFull.svelte` tooltip formatter (l.823-898):

- **Rimuovere** il blocco "Converted from" in fondo (l.890-898) — le info sulla valuta originale sono già nel ghost.
- **NON escludere** il ghost dal loop (rimuovere il `continue` a l.825). Renderizzare il ghost nel loop normale con la sua label `💱 Apple (🇺🇸 USD)`.
- **Dopo il main**, inserire il ghost appena sotto (ECharts itera in ordine di series nell'array → ghost è già subito dopo il main grazie al C.2).
- **Label main**: quando conversione attiva, mostrare `👑Apple Inc. 💱(🇪🇺 EUR)` → aggiungere suffix al main label. Serve passare `displayCurrency` e `displayCurrencyFlag` a PriceChartFull come prop.

**Implementazione:** Ghost nel loop normale, main label con `💱(flag currency)` suffix, blocco "Converted from" rimosso. Aggiunte prop `displayCurrency`/`displayCurrencyFlag` a PriceChartFull.

---

## 6. ✅ D10r-measure — Label invertite: 💱 sul main, non sull'originale

In `frontend/src/lib/components/charts/MeasurePanel.svelte`:
- Riga **main** (l.341-351): quando `originalChartData.length > 0`, aggiungere `💱(🇪🇺 EUR)` al label del main signal → `👑Apple Inc. 💱(🇪🇺 EUR)`.
- Riga **main-original** (l.358-361): togliere `💱` dal prefisso, mostrare solo `Apple Inc. (🇺🇸 USD)`.
- MeasurePanel ha bisogno di sapere il `displayCurrency` + flag → passare come nuova prop o derivare da `chartData`.

**Implementazione:** Main row → `💱(flag currency)` suffix quando conversione attiva. Original row → solo `(flag currency)` senza 💱. Aggiunte prop `displayCurrency`/`displayCurrencyFlag` a MeasurePanel.

---

## 7. ✅ Sync toast helper — Standardizzare i toast per sync asset e FX

Il toast sync è inconsistente tra i vari punti del codice. Creare 2 helper centralizzati:

### 7a. `buildAssetSyncToast(result, tr): { variant, message }`

File: nuovo `frontend/src/lib/utils/syncToastHelpers.ts`

Estrae stats dal response di `sync_prices_bulk` e costruisce il messaggio formattato. Usato da:
- `handleSync()` in asset detail (bottone sync principale) — attualmente usa `💰`/`📅` con `\n`
- `handleSyncAsset()` in asset detail e FX detail (sync da signal card) — attualmente toast generico `common.sync: N↓ MΔ`

Formato uniforme (come `handleSync` attuale, con icone SVG dopo D5r-fix):
```
{tr('assetDetail.syncPrices')}:
<DollarSign/> N↓ MΔ
<CalendarClock/> X↓ YΔ   (solo se events_fetched > 0)
```

### 7b. `buildFxSyncToast(result, slug, tr): { variant, message }`

Stesso file. Estrae stats dal response di `sync_rates`. Usato da:
- `handleSyncPair()` in asset detail — attualmente toast generico `Sync FX EUR/USD ✓` senza stats
- `handleSync()` in FX detail page — attualmente usa i18n keys `fx.sync.toastOk` con stats (questo è il modello)
- `handleSyncPair()` in FX detail page — stessa situazione di asset detail

Formato uniforme (come FX detail page attuale):
```
{tr('fx.sync.toastOk', {pair, fetched, changed, provider})}
```

### 7c. Applicare gli helper nei 5 callsite

1. `assets/[id]/+page.svelte` → `handleSync()`: sostituire logica inline con `buildAssetSyncToast()`
2. `assets/[id]/+page.svelte` → `handleSyncAsset()`: sostituire toast generico con `buildAssetSyncToast()`
3. `assets/[id]/+page.svelte` → `handleSyncPair()`: sostituire toast generico con `buildFxSyncToast()`
4. `fx/[pair]/+page.svelte` → `handleSync()`: sostituire logica inline con `buildFxSyncToast()`
5. `fx/[pair]/+page.svelte` → `handleSyncAsset()`: sostituire toast generico con `buildAssetSyncToast()`

**Implementazione:** Creato `syncToastHelpers.ts` con `buildAssetSyncToast()` e `buildFxSyncToast()`. Applicato nei 5 callsite (3 in asset page, 2 in FX page).

---

## 8. ✅ D13 — Code cleanup review (pending da C.2)

Step finale dopo tutti i fix. Scope:
- ~~Import inutilizzati (es. `EVENT_COLORS` in PriceChartFull, `formatProviderText`/`formatSyncDetail` se rimossi dai callsite).~~ → `EVENT_COLORS` rimosso. `formatProviderText`/`formatSyncDetail` ancora in uso (FX list page, FX detail page, FxSyncModal).
- ~~Funzioni esportate mai chiamate.~~ → `addPoint` e `updatePendingEnd` in MeasurePanel sono falsi positivi (chiamati dai caller via `bind:this`).
- ~~Chiavi i18n orfane.~~ → Rimossa `chart.tooltip.convertedFrom` da EN/IT/FR/ES.
- ~~Dead CSS / componenti Svelte inutilizzati.~~ → Nessuno trovato.
- Rimossa prop `convertedFromLabel` da PriceChartFull + entrambi i caller (asset/FX page).
- Rimossa costante `coinsSvg` inutilizzata da `syncToastHelpers.ts`.
- Coverage test gap → fuori scope (richiede sessione dedicata).

---

## Considerazioni

1. **D2r `$effect` vs `invalidateAll`**: SvelteKit offre `invalidateAll()` per forzare il reload dei dati. Tuttavia, dato che il componente usa `onMount` manuale (non `load` function per i dati), un `$effect` su `data.assetId` che chiama `reload()` è più pulito.
2. **Toast `{@html}`**: Usare `{@html}` implica che qualsiasi toast con HTML venga renderizzato. Per sicurezza, i toasts che usiamo sono tutti costruiti nel codice frontend (nessun input utente), quindi il rischio XSS è nullo.
3. **SVG inline per toast**: I componenti Lucide Svelte non possono essere usati in una stringa. Si possono usare le SVG path raw di Lucide (sono stringhe piccole). Alternativa: creare micro-funzioni `dollarSignSvg()` e `calendarClockSvg()` che tornano l'SVG string pronta per `{@html}`.

---

## ➡️ Seguito: Part C.4 — Multi-FX Comparison

La review di C.3 ha rivelato problemi strutturali con le comparison multi-valuta: staircase da mix di valute nel grafico, banner FX che non specificano quale coppia fallisce, impossibilità di sync/create FX pair per i comparison, e mancanza di valuta nei label dei segnali overlay.
Vedi → [plan-partC_4_MultiFxComparison.prompt.md](plan-partC_4_MultiFxComparison.prompt.md)
