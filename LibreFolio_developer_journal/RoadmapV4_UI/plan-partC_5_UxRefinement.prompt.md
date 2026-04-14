# Plan: C.5 — Rifinitura UX post-review completa (v3)

Rifinitura complessiva dell'asset detail page: fix errore Svelte, SearchSelect per comparison/FX, stili linea per categoria, banner con bandiere + icone Lucide, SyncModal completamente riarchitettato su sezioni, fix pannello misure, fix allineamento/icone tabella misure.

---

## Step 1 — Fix errore Svelte riga 1594 + bug logico `fxPairCreateSlug`

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte`

Estrarre il callback `oncreated` inline come funzione named `handleFxPairCreated({base, quote, hasRealProvider})`. Salvare `fxPairCreateSlug` in variabile locale (`const wasForComparison = !!fxPairCreateSlug`) **prima** di azzerarlo, usare quella per il guard. Spostare `PageSyncAllModal` dentro il blocco `{#if assetInfo}`.

**Bug attuale:** a riga 1578 `fxPairCreateSlug = ''` lo azzera, poi a riga 1581 `if (!fxPairCreateSlug)` è sempre true — il guard è inutile. La logica corretta: solo quando si crea la FX pair per l'asset principale (non per un comparison) si aggiorna `displayCurrency`.

**Errore Svelte:** `}}` a riga 1594 è ambiguo — il parser Svelte lo interpreta come chiusura di un blocco template anziché come fine del callback + fine del tag. Estrarre come funzione named risolve.

---

## Step 2 — SearchSelect per asset comparison e FX pair

**File:** `frontend/src/lib/components/charts/ChartSignalsSection.svelte`

Sostituire `SimpleSelect` con `SearchSelect` (già supporta snippet `item`/`selectedItem` come `Snippet<[SelectOption]>`) per il dropdown asset comparison (~riga 560). Riusare gli snippet `menuItem`/`selectedItem` già presenti con icone e label. Per il dropdown FX pair usare `SearchSelect` con ricerca standard. Nessuna virtualizzazione — `maxVisibleItems=8` limita il DOM.

`SearchSelect` filtra già su `value`, `label`, `searchText` e `icon` — sufficiente per entrambi i casi d'uso.

---

## Step 3 — Banner "Data available from" — specificare l'asset

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte`

Calcolare `dataGapAssets: {name, iconUrl, assetType, firstDate}[]` che include main + comparison asset il cui `firstDate > dateStart`. Sostituire il singolo banner con un loop che mostra icona e nome asset per ciascun gap:

```
📊 [icon] Apple Inc. — Data available from 2024-04-15 — earlier dates have no data
📊 [icon] Amundi MSCI World — Data available from 2025-01-10 — earlier dates have no data
```

---

## Step 4 — Stili linea differenziati per categoria

**File:** `frontend/src/lib/charts/signals/registry.ts` (`createSignal()`)

Attualmente: `lineType: Cls.signalType === 'macd' ? 'solid' : 'dashed'` per tutti. Differenziare:

| Categoria | `lineType` | `lineWidth` | Esempi |
|-----------|-----------|-------------|--------|
| `'indicator'` (tecnici) | `'dotted'` | `1` | EMA, RSI, Bollinger |
| `'benchmark'` (sintetici) | `'dashed'` | `1` | linear, compound, sine |
| `'comparison'` (asset/FX) | `'solid'` | `2` | asset-comparison, fx-pair |
| MACD (eccezione) | `'solid'` | `1` | macd (invariato) |

**File:** `frontend/src/lib/charts/signals/MeasureSignal.ts` (`getDefaultStyle()`)

Cambiare: `lineWidth: 1`, `lineType: 'dotted'`. Freccia invariata (pin + arrow).

---

## Step 5 — Banner FX con bandiere, icone Lucide e `ArrowLeftRight`

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (riga 1028-1070)

### 5a. Estetica banner

- `💱` → `<Coins size={14}/>` (stessa icona del burger menu FX Rates)
- Slug `SEK/USD` → `{flag1} SEK <ArrowLeftRight size={10}/> {flag2} USD` (stessa estetica di `FxPairAddModal`)
- `({pair.forAsset})` → preceduto dall'icona dell'asset (`icon_url` o fallback `asset_type` PNG)
- Estendere `RequiredFxPairInfo` con `forAssetIconUrl?: string | null`, `forAssetType?: string | null`

### 5b. Bottoni banner

- Goto FX: `<Coins size={13}/>` (non `↗`)
- Add FX: `<Coins size={13}/>` (non `➕`)
- Sync FX: `<RotateCw size={13}/>` con `animate-spin` durante sync
- Ordine: Coins (goto/add) prima, RotateCw dopo (come in `AssetPriceSummary`)

### 5c. Mobile layout

- Desktop: bottoni inline a destra con `ml-auto` (invariato)
- Mobile: bottoni in cima allineati a destra. Cambiare layout da `flex-wrap` a `flex-col sm:flex-row` con bottoni posizionati in cima

### 5d. Toast FX sync con stessa estetica

In `frontend/src/lib/utils/syncToastHelpers.ts` (`buildFxSyncToast`): usare SVG inline di `ArrowLeftRight` e bandiere nella riga del pair slug, coerente coi banner.

---

## Step 6 — Rearchitettura SyncModal: `SyncModalBase` con sezioni

Riscrivere completamente l'architettura sync modal con **sezioni** — breaking change voluto. La modale contiene tutta la logica di sync; il padre passa solo la lista di asset/FX e riceve `onsynced()` per fare refresh.

### 6a. Nuova interfaccia `SyncSection`

**File:** `frontend/src/lib/utils/syncHelpers.ts`

```typescript
export interface SyncSection {
    /** Section identifier (e.g. 'assets', 'fx') */
    id: string;
    /** Section title (e.g. '📊 Assets', '💱 FX Pairs') */
    title: string;
    /** Callback to perform the actual sync — returns results */
    doSyncFn: (targetIds: string[]) => Promise<SyncResult[]>;
    /** All target IDs to sync in this section */
    targetIds: string[];
    /** Snippet for rendering each result row */
    resultRow: Snippet<[SyncResult, boolean]>;
    /** Count label for summary (e.g. 'assets', 'pairs') */
    countLabel: string;
}
```

### 6b. `SyncModalBase` rewrite

**File:** `frontend/src/lib/components/ui/SyncModalBase.svelte`

Props diventano:
```typescript
interface Props {
    open: boolean;
    dateStart: string;
    dateEnd: string;
    title: string;
    description: string;
    testId: string;
    headerIcon?: typeof RefreshCw;
    headerIconBg?: string;
    headerIconColor?: string;
    /** Sync sections — each rendered as a titled group with its own results */
    sections: SyncSection[];
    onsynced: () => void;
    onclose: () => void;
}
```

- `itemCount` = somma `targetIds.length` di tutte le sezioni (derivata)
- Sezioni con `targetIds.length === 0` non renderizzate
- Sync: `Promise.all(sections.map(s => doSync(s)))` — parallelo, countdown unificato
- Risultati: `Map<sectionId, SyncResult[]>`
- Retry per singolo item: identifica la sezione dal `result.id` → chiama `section.doSyncFn([id])`
- Retry-all-failed: filtra i failed per sezione → `Promise.all`
- Summary aggregato in fondo: `{successCount}/{total} · N↓ MΔ`
- **Esportare** `handleRetrySingle(sectionId, itemId)` per uso da snippet

### 6c. `AssetSyncModal` — aggiornare

**File:** `frontend/src/lib/components/assets/AssetSyncModal.svelte`

Diventa wrapper che costruisce 1 `SyncSection` con `id: 'assets'`, `title`, `doSyncFn`, `targetIds`, snippet `resultRow` (lo snippet esistente). Passa array di 1 sezione a `SyncModalBase`.

Aggiungere al result row: se `events_fetched > 0`, mostrare sotto il conteggio prezzi anche `📅 {events_fetched}↓ {events_changed}Δ`.

### 6d. `FxSyncModal` — aggiornare

**File:** `frontend/src/lib/components/fx/FxSyncModal.svelte`

Stesso pattern: 1 `SyncSection` con `id: 'fx'`. Snippet result row invariato (mantiene icone provider chain con `parseProviderChain` + `getFxProviderIconUrl`).

### 6e. `PageSyncAllModal.svelte` — creare

**File:** `frontend/src/lib/components/ui/PageSyncAllModal.svelte`

Passa 2 sezioni (Asset + FX) a `SyncModalBase`. Il padre passa:
- `assets: AssetSyncItem[]` — lista asset con id, display_name, icon_url, provider_code
- `fxPairs: string[]` — lista slug FX pair da sincronizzare

La modale costruisce le 2 sezioni internamente con i rispettivi `doSyncFn` (endpoint asset sync + endpoint FX sync). Snippet result row riusa la stessa logica di `AssetSyncModal` e `FxSyncModal`.

Eliminare `PageSyncModal.svelte` (il vecchio componente che reinventava la ruota).

### 6f. Aggiornare i 3 callsite

1. **Asset list** `assets/+page.svelte` → `AssetSyncModal` — invariato API (la nuova `SyncModalBase` è sotto il cofano)
2. **FX list** `fx/+page.svelte` → `FxSyncModal` — invariato API
3. **Asset detail** `assets/[id]/+page.svelte` → `PageSyncAllModal` — sostituisce `PageSyncModal`

In tutti i casi il padre:
- Passa la lista di item da sincronizzare
- Riceve `onsynced()` → fa i refresh del caso (reload chart, reload metadata, etc.)
- La modale gestisce internamente sync, timeout, retry, countdown, progress, summary

---

## Step 7 — Fix pannello Misure

**File:** `frontend/src/routes/(app)/assets/[id]/+page.svelte` (riga 1404-1430)

### 7a. Click area

L'intera riga header deve essere cliccabile per aprire/chiudere il pannello. Wrappare in un `<div>` (o `<button>`) con `onclick={() => showMeasures = !showMeasures}`. Il bottone "+" annidato ha `e.stopPropagation()` per non triggare il toggle.

### 7b. Ordine elementi

Riordinare: `Ruler icon + "Misure" label` → (gap flessibile) → bottone "+" → `ChevronDown` alla fine.

### 7c. Label bottone "+"

Aggiungere label testuale: `<span class="hidden sm:inline">{$t('measure.addMeasure')}</span>` accanto al `+`. Visibile solo su `sm:` e superiori.

---

## Step 8 — Fix tabella misure: icona/colore mancanti sulla riga originale

**File:** `frontend/src/lib/components/charts/MeasurePanel.svelte` (riga 382-395)

La riga `main-original` non riceve `iconUrl` né `assetType` nella `signalInfo`. Aggiungere:

```typescript
signalInfo: {
    label: `${mainSignalInfo.label ?? 'Main'} (${origFlag} ${originalCurrencyCode})`,
    isCrown: false,
    color: mainSignalInfo.color,
    iconUrl: mainSignalInfo.iconUrl,      // ← AGGIUNGERE
    assetType: mainSignalInfo.assetType,  // ← AGGIUNGERE
},
```

---

## Step 9 — Fix allineamento original value nell'infobox

**File:** `frontend/src/lib/components/assets/AssetPriceSummary.svelte`

Unificare spacing/allineamento tra riga prezzo e riga currency selector. Il problema è che il container prezzo (`flex items-center gap-3`) e il container valuta (`flex items-center gap-2`) hanno gap diversi e il `CurrencySearchSelect` non si allinea visivamente.

Fix: verificare e allineare `gap`, `items-center`/`items-baseline`, e larghezza fissa del `CurrencySearchSelect` container (`w-28 sm:w-32`).

---

## Ordine di implementazione consigliato

| # | Step | Tipo | Stima | Dipendenze |
|---|------|------|-------|-----------|
| 1 | **Step 1** — Fix compile error | 🐛 Bug | 5 min | Bloccante |
| 2 | **Step 6** — SyncModal arch | 🏗️ Refactor | 60 min | Indipendente |
| 3 | **Step 2** — SearchSelect | 🎨 UX | 20 min | Indipendente |
| 4 | **Step 4** — Stili linea | 🎨 UX | 10 min | Indipendente |
| 5 | **Step 5** — Banner FX | 🎨 UX | 30 min | Indipendente |
| 6 | **Step 3** — Data gap banner | 🎨 UX | 15 min | Indipendente |
| 7 | **Step 7** — Fix misure panel | 🐛 Bug | 15 min | Indipendente |
| 8 | **Step 8** — Fix misure icona | 🐛 Bug | 5 min | Indipendente |
| 9 | **Step 9** — Fix allineamento | 🐛 Bug | 10 min | Indipendente |

---

## Considerazioni

1. **Search FX pair multi-term**: per ora la ricerca standard di `SearchSelect` è sufficiente. Se in futuro servisse "ogni spazio = contain separato", aggiungere prop `multiTermSearch?: boolean` al componente.

2. **`SyncModalBase` sezioni — design pulito e scalabile**: la modale contiene tutta la logica di sync. Il padre passa la lista di asset/FX e riceve `onsynced()` per i refresh. Questo permette riuso ovunque (asset list, FX list, asset detail, futuro dashboard) senza duplicazione. Breaking change sulle vecchie prop — corretto perché siamo in pre-beta.

---

➡️ Seguito: [Part C.6 — Post-test UX Polish & Sync Unificazione](plan-partC_6_PostTestPolish.prompt.md)
