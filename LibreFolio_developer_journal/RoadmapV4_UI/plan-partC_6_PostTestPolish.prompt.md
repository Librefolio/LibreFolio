# Plan: C.6 — Post-test UX Polish & Sync Unificazione

Correzioni emerse dal testing post-C.5: fix tooltip GBP duplicato, icone provider FX mancanti nei sync modal, result row con bandiere+ArrowLeftRight per FX e icone Lucide per asset, toast FX con bandiere/icone, banner "data available" specifico, mobile banner layout, sync modale per FX detail, FX lineWidth=1, SearchSelect FX compatto.

---

## Step 0 — Fix tabella misure: pallino colore mancante su riga originale

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (~riga 390) e `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (~riga 243)

La riga `main-original` nella tabella delle misure non mostra il pallino colorato perché `mainSignalInfo` ha `isCrown: true` ma **nessun `color`**. La `signalLabelToHtml()` renderizza il dot solo quando `color` è definito. Il tooltip del chart funziona perché usa direttamente `p.color` di ECharts (colore della serie).

Fix: aggiungere `color` a `mainSignalInfo` nelle pagine che lo definiscono:
- **Asset detail:** `color: COLORS.lineLight` (o derivare da dark mode) — importare `COLORS` da `lineChartHelpers`
- **FX detail:** stessa aggiunta

Il dot nella riga crown non viene mostrato (la crown ha precedenza visiva), ma il `main-original` row (che ha `isCrown: false` e `color: mainSignalInfo.color`) lo eredita correttamente.

---

## Step 1 — Fix tooltip: GBP duplicato + testo nero/grigio

**File:** `frontend/src/lib/components/charts/PriceChartFull.svelte` (~riga 848-854)

**Bug GBP duplicato:** I ghost dei segnali comparison (es. `💱 Amundi MSCI World UCITS ETF (🇬🇧 GBP)`) hanno già la valuta nel `label` ma passano anche `currency: 'GBP'` e `currencyFlag: '🇬🇧'` nel `RenderedSignal`. Il tooltip li trova via `overlaySignalInfoMap` e appende nuovamente `(🇬🇧 GBP)` con `currSuffix`. Fix: nel tooltip formatter, riconoscere i ghost (il label inizia con `💱` o il `sigInfo` ha opacity < 1) e saltare il `currSuffix`. L'approccio più robusto: aggiungere `isGhost?: boolean` a `SignalLabelInfo` e settarlo in `buildOverlaySignalInfoMap` leggendo `signal.opacity < 1`. In alternativa più semplice: se `sigInfo.label` contiene già la parentesi con la valuta, non aggiungere il suffix.

**Testo nero/grigio:** Nella `signalLabelToHtml()` (in `frontend/src/lib/charts/signalLabel.ts`), il label text è renderizzato con `vertical-align:middle` ma senza colore esplicito. Il testo eredita il colore dal container tooltip. I ghost overlays hanno la label renderizzata da `signalLabelToHtml(sigInfo)` dove `sigInfo.color` è il colore della linea (usato per il dot), che non influenza il testo. Tuttavia il `currSuffix` ha `opacity:0.7` — questo è grigio. Verificare nel tooltip se tutti i label text usano lo stesso colore base e se il ghost dot (opacity:0.4) non si propaga al testo. Possibile fix: i ghost overlay dovrebbero usare `opacity:0.5` anche per il dot nella `signalLabelToHtml` per distinguerli visivamente (come fa il main ghost alla riga 845).

---

## Step 2 — FX provider icons nei sync modal: ensure cache

**File:** `frontend/src/lib/components/ui/PageSyncModal.svelte` e `frontend/src/lib/components/fx/FxSyncModal.svelte`

Le icone FX provider (ECB, FED, BOE, SNB) vengono da `getCachedFxProviders()` in `currencyGraphStore`, che è populated solo dopo `getCurrencyGraph()`. La pagina FX list la chiama, ma **la pagina asset detail no** — quindi `PageSyncModal` aperto da asset detail non trova le icone.

Fix: aggiungere in entrambi i modali un `$effect` all'apertura che chiama `getCurrencyGraph()` (è idempotente, restituisce il cache se già popolato). Importare `getCurrencyGraph` da `currencyGraphStore`.

```typescript
$effect(() => { if (open) getCurrencyGraph(); });
```

Questo precarica il cache FX providers. Le icone arrivano in modo sincrono dal cache nella `getFxProviderIconUrl()` poiché il graph è già costruito prima che il sync avvenga.

---

## Step 3 — FX result row: bandiere + ArrowLeftRight

**File:** `frontend/src/lib/components/fx/FxSyncModal.svelte` (riga 110) e `frontend/src/lib/components/ui/PageSyncModal.svelte` (riga 221)

Sostituire `<span class="font-medium font-mono">{pr.id.replace('-', '/')}</span>` con:
- Split `pr.id` su `-` → `[base, quote]`
- Import `getCurrencyInfo` e `ArrowLeftRight` da lucide
- Render: `{baseFlag} {BASE} <ArrowLeftRight size={10}/> {quoteFlag} {QUOTE}` (stessa estetica dei banner FX nella pagina asset detail)

---

## Step 4 — Asset result row: icone Lucide DollarSign / CalendarClock

**File:** `frontend/src/lib/components/assets/AssetSyncModal.svelte` (riga 131-136) e `frontend/src/lib/components/ui/PageSyncModal.svelte` (riga 177-181)

Sostituire testo plain con icone Lucide coerenti col data editor e il toast asset:
- `{fetched}↓ {changed}Δ` → `<DollarSign size={13}/> {fetched}↓ {changed}Δ`
- `📅 {events}↓ {events_changed}Δ` → `<CalendarClock size={13}/> {events}↓ {events_changed}Δ`
- Import `DollarSign`, `CalendarClock` da lucide-svelte

---

## Step 5 — Mobile banner: pulsanti in cima a destra

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (~riga 1062-1111)

Attualmente `flex flex-col sm:flex-row` con i bottoni dopo il messaggio. In mobile, i bottoni finiscono sotto. Fix: aggiungere `order-first sm:order-none self-end sm:self-auto` alla div bottoni (riga 1090) così in mobile appaiono per primi (in cima, a destra).

---

## Step 6 — Banner "Data available from" specifico per asset/pair

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (~riga 1046) e `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (~riga 692)

**Asset detail:** Calcolare `dataGapItems: {name, iconUrl?, assetType?, firstDate}[]` che include il main asset + ogni comparison asset il cui primo dato > `dateStart`. Loop su ciascuno nel banner con icona + nome. Se un solo item, si mostra come singolo banner. Se multipli, si mostrano N banner separati.

**FX detail:** Aggiungere il nome del pair (bandiere + base/quote) al banner generico. Se ci sono anche overlay pair, mostrare per ciascuno il nome specifico. Aggiornare chiave i18n `assetDetail.dataAvailableFrom` per accettare parametro `{name}` opzionale.

---

## Step 7 — Toast FX con bandiere + icone provider HTML

**File:** `frontend/src/lib/utils/syncToastHelpers.ts` — `buildFxSyncToast()`

Il toast attualmente mostra `AUD/GBP synced 62↓ 0Δ (ECB + ECB)`. Migliorare:
- Slug: usare bandiere emoji (`getCurrencyInfo(base).flag_emoji`) + `↔` al posto di `/`
- Provider: usare `fxProviderBadgeHtml()` (genera `<img>` HTML o testo fallback) al posto di `formatProviderText`
- Il toast supporta `{@html}` — HTML inline funziona
- Pre-caricare `getCurrencyGraph()` all'init della pagina FX/asset per avere le icone ready

Aggiornare le 4 chiavi i18n `fx.sync.toastOk/Partial/Skipped/Failed` per rimuovere `({provider})` e renderlo via HTML badge separato.

**File:** `frontend/src/routes/(app)/fx/+page.svelte` (riga 597-648) — `handleSyncPair()`: sostituire il toast inline con `buildFxSyncToast()` (come già fatto in FX detail page).

---

## Step 8 — FX pair SearchSelect compatto con bandiere

**File:** `frontend/src/lib/components/charts/ChartSignalsSection.svelte` (~riga 494-518)

Attualmente il SearchSelect per FX pair genera label lunghe su 2 righe come il currency selector. Rendere compatto:
- Fornire snippet `item` e `selectedItem` inline con layout 1 riga: `{baseFlag} {BASE} ↔ {quoteFlag} {QUOTE}` in `text-xs gap-1`
- Il container `w-48` può restare, ma il contenuto deve essere su una riga sola
- Le bandiere sono già calcolate nel `options.map()`— fornire snippet che le renderizza compatte anziché affidarsi alla label text

---

## Step 9 — FX pair default lineWidth = 1

**File:** `frontend/src/lib/charts/signals/registry.ts` (~riga 131)

Attualmente `comparison` category (fx-pair + asset-comparison) ha `defaultWidth = 2`. L'utente vuole fx-pair a 1. Differenziare: se `Cls.signalType === 'fx-pair'` → `lineWidth: 1`, altrimenti comparison → `lineWidth: 2`.

---

## Step 10 — FX detail page: sync modale multi-section

**File:** `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

Il pulsante sync (riga 776) fa sync inline con toast. Sostituire con `PageSyncModal`:
- Importare `PageSyncModal`
- Aggiungere stato `showPageSyncModal`, derivare `syncAllFxPairs` (pair principale + FX overlay signals) e `syncAllAssets` (asset comparison signals, da `allAssets`)
- Pulsante sync: `onclick={() => showPageSyncModal = true}`
- `PageSyncModal` con 2 sezioni (assets + FX) se ci sono comparison asset, altrimenti 1 sezione (FX)
- `onsynced` → `handleRefresh()` + `maybeLoadComparison()`

---

## Ordine di implementazione consigliato

| # | Step | Tipo | Stima |
|---|------|------|-------|
| 0 | **Step 0** — Fix pallino colore riga originale misure | 🐛 Bug | 5 min |
| 1 | **Step 1** — Fix tooltip GBP duplicato + colori | 🐛 Bug | 15 min |
| 2 | **Step 2** — Ensure FX provider cache in modali | 🐛 Fix | 5 min |
| 3 | **Step 3** — FX result row bandiere+ArrowLeftRight | 🎨 UX | 15 min |
| 4 | **Step 4** — Asset result row icone Lucide | 🎨 UX | 10 min |
| 5 | **Step 5** — Mobile banner pulsanti in cima | 🐛 Fix | 5 min |
| 6 | **Step 9** — FX pair lineWidth=1 | 🎨 UX | 5 min |
| 7 | **Step 8** — FX SearchSelect compatto | 🎨 UX | 15 min |
| 8 | **Step 6** — Banner "data available" specifico | 🎨 UX | 20 min |
| 9 | **Step 7** — Toast FX con bandiere+icone | 🎨 UX | 20 min |
| 10 | **Step 10** — FX detail sync modale | 🏗️ Feature | 25 min |

---

## Considerazioni

1. **`getCurrencyGraph()` in asset detail:** Va chiamato anche dalla pagina asset detail (`onMount`) per pre-caricare il cache FX providers, non solo al momento dell'apertura del modal. Così le icone sono ready anche per i banner, le card FX, etc.

2. **Toast HTML lazy load:** Confermato approccio lazy — il pre-fetch di `getCurrencyGraph()` all'init della pagina assicura che le icone siano disponibili prima che l'utente esegua il sync. Il toast viene generato dopo la risposta API, quindi il cache è già popolato.

3. **PageSyncModal naming:** Mantenuto il nome `PageSyncModal.svelte`. Tutti i sync multipli (asset detail, FX detail, e in futuro dashboard) useranno questo componente per centralizzare logica e estetica.

---

## Piano successivo

→ [C.6b — Fix post-test C.6](plan-partC_6b_PostTestFixes.prompt.md)
→ [C.7 — Core-level Cache + Thread Isolation](plan-partC_7_AssetProviderCoreCache.prompt.md)

