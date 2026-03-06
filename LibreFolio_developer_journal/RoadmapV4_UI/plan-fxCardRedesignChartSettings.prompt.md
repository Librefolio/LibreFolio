# Plan: FX Card Redesign, Chart Settings, Signal Library & Sync All Fix

**Data creazione**: 5 Marzo 2026
**Status**: 🔄 IN PROGRESS — Steps 1-4,6 completati. Prossimo: Step 5 (FxCard redesign), Step 7 (DataTable), Step 8 (integration)
**Dipendenze**: plan-fxUiRefinementsRound2 Step 8, plan-phase05Fx Steps 3-5
**Contesto**: Feedback utente su card layout, settings ⚙️ non collegato, Sync All non funzionante, overlay/benchmark da implementare come libreria di segnali

---

## Analisi Problemi

### P1 — Sync All non funziona (bug critico)
- `FxSyncModal` chiama `sync_rates` **senza** `currencies`, il backend usa il default hardcoded `"USD,GBP,CHF,JPY"` (riga 145 `fx.py`). Se le coppie configurate non contengono queste valute, 0 lavoro eseguito.
- Dopo il sync, `handleSynced` chiama `handleRefreshAll` che legge dalla `TimeSeriesStore` **senza invalidarla** → nessun dato nuovo.
- La modale ha stile minimale (div con spacing, nessun header/footer strutturato) non coerente con `ConfirmModal`/`ModalBase`.
- L'icona `RotateCcw` con `animate-spin` ruota in senso orario, contraddittorio con il glifo che punta antiorario.

### P2 — Settings ⚙️ non collegato
- Il pulsante nella filter bar esiste ma non ha handler (`onclick` mancante).
- Step 8a del plan-fxUiRefinementsRound2 descrive checkbox per chart aesthetics.
- L'utente vuole settings sia **globali** (dalla filter bar, si applicano a tutte le card) che **locali** (per card singola, nella card stessa e nella detail page).
- I settings locali devono persistere nella sessione: entrando nel detail e tornando alla lista, i settings della card restano. Se si modifica dal detail, torna aggiornato nella card.
- I settings globali sovrascrivono i locali quando applicati.
- **Non salvare nel backend** — solo cache locale (session-level).

### P3 — Card layout da ridisegnare
- Layout attuale: header con coppia + swap + % + rate + delta mescolati, bottoni icon-only nel footer.
- Scelto **layout B**: rate prominente come riga dedicata, predispone per future metriche.
- Il badge "✏️ Manual" appare **SOLO** se il provider è MANUAL (condizionale, non estetico).
- Aggiungere infobox nella pagina lista che spiega che i valori Δ% sono relativi al primo giorno della finestra temporale.

### P4 — Overlay e Benchmark come Signal Library
- L'utente vuole sovrapporre **segnali** ai grafici: dati reali (FX pair) o sintetici, **senza vincoli di numero**.
- **FxPairSignal rilassato**: rimosso `maxInstances = 1` — è possibile sovrapporre più coppie FX sullo stesso grafico. Se i punti si sovrappongono (stessa coppia 2 volte) non è un problema, non è permanente.
- **Chart generico**: il componente grafico accetta una lista di segnali (`RenderedSignal[]`) e li mostra TUTTI, senza sapere quale sia "il primo". Massima genericità per espansioni future (Asset, Dashboard).
- **Architettura a classi**: classe base astratta `ChartSignal`, classi figlie per ogni tipo. Stessa interfaccia per segnali reali (dati dal backend) e sintetici (calcolati client-side). Il frontend gestisce una **lista uniforme** di `ChartSignal[]`.
- Le classi figlie dichiarano i propri parametri come `SignalParamDescriptor[]` — la UI li legge per renderizzare i controlli nell'OrderableList dinamicamente.
- Ogni segnale ha parametri comuni (colore, spessore, tipo linea, **freccia inizio, freccia fine**) + parametri specifici del tipo.
- **Frecce inizio/fine**: predisposte in `SignalStyle` per il detail page (es. indicare direzione di un trend), disabilitate di default.
- Se si settano parametri globali, i locali vengono sovrascritti. Riaprendo la modale si trovano le impostazioni correnti.

### P5 — OrderableList: migrazione DataTableToolbar
- `OrderableList` è già generico con snippet (Svelte 5, drag & drop desktop + frecce mobile).
- `DataTableToolbar` ha **logica drag&drop duplicata** (~60 righe, righe 38-114): stessa identica meccanica (dragStart, dragOver, dragLeave, drop, dragEnd, moveUp, moveDown).
- **Confermato**: DataTableToolbar usa layout **verticale** (lista colonne impilate con `column-option`, GripVertical handle, frecce ChevronUp/Down su mobile), identico a OrderableList. Nessuna variante horizontal necessaria.
- Migrare DataTableToolbar ad usare OrderableList eliminando il codice duplicato.

---

## Architettura Signal Library

### Cartella: `frontend/src/lib/charts/signals/`

```
signals/
├── ChartSignal.ts       # Classe base astratta + tipi condivisi
├── FxPairSignal.ts      # Segnale dati reali (FX pair dal backend)
├── LinearSignal.ts      # Retta con pendenza annua costante
├── CompoundSignal.ts    # Crescita con interesse composto (esponenziale)
├── registry.ts          # Registry: signalType → constructor, factory, serializzazione
└── index.ts             # Barrel export
```

### Classe base `ChartSignal`

```typescript
// frontend/src/lib/charts/signals/ChartSignal.ts

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

// ═══════════════════════════════════════════════════════════════════
// PARAM DESCRIPTORS — Letti dalla UI per renderizzare i controlli
// ═══════════════════════════════════════════════════════════════════

/**
 * Descriptor for a user-editable parameter of a signal.
 * The ChartSettingsModal reads these from each signal class to dynamically
 * render the appropriate input controls in the OrderableList rows.
 */
export interface SignalParamDescriptor {
    /** Unique key (maps to signal.params[key]) */
    key: string;
    /** Label shown in the UI (i18n key or fallback string) */
    label: string;
    /** Input type for rendering:
     *  - 'number': <input type="number"> with min/max/step/suffix
     *  - 'select': <select> with options array (static or dynamic)
     *  - 'string': <input type="text">
     */
    type: 'number' | 'string' | 'select';
    /** Default value for new instances */
    default: unknown;
    // ── For type === 'number' ──
    min?: number;
    max?: number;
    step?: number;
    /** Suffix shown inline after the input (e.g. "%/yr") */
    suffix?: string;
    // ── For type === 'select' ──
    /** Static options list */
    options?: Array<{value: string; label: string}>;
    /** If set, the modal resolves options at runtime using this key.
     *  e.g. 'configuredFxPairs' → modal passes configured pairs as options */
    dynamicOptionsKey?: string;
}

// ═══════════════════════════════════════════════════════════════════
// SIGNAL STYLE — Common rendering params for every signal
// ═══════════════════════════════════════════════════════════════════

export interface SignalStyle {
    color: string;                              // hex, e.g. '#3b82f6'
    lineWidth: number;                          // 1, 2, 3, or 4
    lineType: 'solid' | 'dashed' | 'dotted';
    arrowStart: boolean;                        // show arrow marker at first point
    arrowEnd: boolean;                          // show arrow marker at last point
}

// ═══════════════════════════════════════════════════════════════════
// SIGNAL CONFIG — Serializable state (stored in ChartSettings)
// ═══════════════════════════════════════════════════════════════════

/**
 * Serializable config for a signal instance.
 * Stored in ChartSettings.signals[] and used to recreate class instances.
 * Fields prefixed with '_' in params are transient and excluded by toConfig().
 */
export interface SignalConfig {
    id: string;                                 // UUID
    signalType: string;                         // registry key: 'fx-pair', 'linear', 'compound'
    params: Record<string, unknown>;            // signal-specific editable params
    style: SignalStyle;                         // rendering style
}

/** Default color palette — cycled when adding new signals */
export const DEFAULT_SIGNAL_COLORS = [
    '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
];

// ═══════════════════════════════════════════════════════════════════
// ABSTRACT BASE CLASS
// ═══════════════════════════════════════════════════════════════════

/**
 * Abstract base class for all chart overlay signals.
 *
 * Subclasses MUST define static properties:
 *   - signalType: string              — unique registry key
 *   - displayName: string             — shown in "Add signal" dropdown
 *   - icon: string                    — emoji for the dropdown
 *   - paramDescriptors: SignalParamDescriptor[]  — editable params (UI reads these)
 *   - maxInstances?: number           — max allowed per chart (undefined = unlimited)
 *
 * Subclasses MUST implement:
 *   - computePoints(baseData, viewMode): LineDataPoint[]
 *   - getLabel(): string
 *
 * The base class provides:
 *   - id, style, params storage
 *   - toConfig() serialization (excludes '_'-prefixed transient params)
 *   - Common constructor
 */
export abstract class ChartSignal {
    readonly id: string;
    style: SignalStyle;
    params: Record<string, unknown>;

    // ── Static metadata (read by UI and registry) ───────────────
    static signalType: string;
    static displayName: string;
    static icon: string;
    static paramDescriptors: SignalParamDescriptor[];
    static maxInstances?: number;

    constructor(id: string, style: SignalStyle, params: Record<string, unknown>) {
        this.id = id;
        this.style = {...style};
        this.params = {...params};
    }

    /**
     * Compute overlay data points aligned to the primary chart's date axis.
     *
     * @param baseData  Primary chart data (provides date axis + baseValue reference)
     * @param viewMode  'absolute' or 'percentage' — signals adjust their output
     * @returns         Points aligned to baseData dates
     */
    abstract computePoints(
        baseData: LineDataPoint[],
        viewMode: 'absolute' | 'percentage',
    ): LineDataPoint[];

    /** Human-readable label for ECharts legend and tooltip */
    abstract getLabel(): string;

    /** Serialize to storable config (excludes '_'-prefixed transient fields) */
    toConfig(): SignalConfig {
        const serializableParams = Object.fromEntries(
            Object.entries(this.params).filter(([k]) => !k.startsWith('_'))
        );
        return {
            id: this.id,
            signalType: (this.constructor as typeof ChartSignal).signalType,
            params: serializableParams,
            style: {...this.style},
        };
    }
}
```

### Classe `FxPairSignal` — Segnale da dati reali

```typescript
// frontend/src/lib/charts/signals/FxPairSignal.ts

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

/**
 * Overlay signal sourced from a real FX pair (data fetched from backend).
 *
 * The parent component pre-fetches data from the TimeSeriesStore and injects
 * it via params._resolvedData before calling computePoints().
 * The '_' prefix ensures _resolvedData is excluded from toConfig() serialization.
 *
 * No maxInstances limit — user can overlay multiple FX pairs on the same chart.
 * If the same pair is added twice, points overlap (not harmful, not permanent).
 */
export class FxPairSignal extends ChartSignal {
    static signalType = 'fx-pair';
    static displayName = 'FX Pair';                   // i18n: 'signals.fxPair'
    static icon = '💱';
    // maxInstances = undefined → unlimited (relaxed per user request)

    static paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'pairSlug',
            label: 'Currency Pair',                    // i18n: 'signals.params.currencyPair'
            type: 'select',
            default: '',
            dynamicOptionsKey: 'configuredFxPairs',    // resolved at runtime by the modal
        },
    ];

    computePoints(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
        // _resolvedData is injected by the parent before calling computePoints
        const resolvedData = this.params._resolvedData as LineDataPoint[] | undefined;
        if (!resolvedData?.length || !baseData.length) return [];

        // Build date→value lookup, then align to base chart's date axis
        const lookup = new Map(resolvedData.map(d => [d.date, d.value]));
        const points: LineDataPoint[] = [];
        for (const bd of baseData) {
            const val = lookup.get(bd.date);
            if (val !== undefined) points.push({date: bd.date, value: val});
        }

        if (viewMode === 'percentage' && points.length > 0) {
            const base = points[0].value;
            if (base !== 0) {
                return points.map(p => ({...p, value: ((p.value - base) / base) * 100}));
            }
        }
        return points;
    }

    getLabel(): string {
        const slug = String(this.params.pairSlug || '');
        return slug ? slug.replace('-', '/') : 'FX Pair';
    }
}
```

### Classe `LinearSignal` — Retta con pendenza annua costante

```typescript
// frontend/src/lib/charts/signals/LinearSignal.ts

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

/**
 * Synthetic signal: straight line with constant annual slope.
 *
 * Formula (absolute): y = y0 × (1 + rate × t)
 * Formula (percentage): pct = rate × t × 100
 *
 * where: t = daysSinceStart / 365, rate = annualRate / 100
 * Unlimited instances per chart.
 */
export class LinearSignal extends ChartSignal {
    static signalType = 'linear';
    static displayName = 'Linear Growth';             // i18n: 'signals.linear'
    static icon = '📈';
    // maxInstances = undefined → unlimited

    static paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'annualRate',
            label: 'Annual Rate',                      // i18n: 'signals.params.annualRate'
            type: 'number',
            default: 2,
            min: -100,
            max: 1000,
            step: 0.5,
            suffix: '%/yr',
        },
    ];

    computePoints(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
        if (!baseData.length) return [];

        const rate = Number(this.params.annualRate ?? 2) / 100;
        const baseValue = baseData[0].value;
        const startMs = new Date(baseData[0].date).getTime();

        return baseData.map(d => {
            const t = (new Date(d.date).getTime() - startMs) / 86_400_000 / 365;
            return {
                date: d.date,
                value: viewMode === 'percentage'
                    ? rate * t * 100
                    : baseValue * (1 + rate * t),
            };
        });
    }

    getLabel(): string {
        return `Linear ${this.params.annualRate ?? 2}%/yr`;
    }
}
```

### Classe `CompoundSignal` — Crescita con interesse composto

```typescript
// frontend/src/lib/charts/signals/CompoundSignal.ts

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

/**
 * Synthetic signal: compound growth (exponential / interest composto).
 *
 * Formula (absolute): y = y0 × (1 + rate)^t
 * Formula (percentage): pct = ((1 + rate)^t − 1) × 100
 *
 * where: t = daysSinceStart / 365, rate = annualRate / 100
 * Unlimited instances per chart.
 */
export class CompoundSignal extends ChartSignal {
    static signalType = 'compound';
    static displayName = 'Compound Growth';           // i18n: 'signals.compound'
    static icon = '📊';
    // maxInstances = undefined → unlimited

    static paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'annualRate',
            label: 'Annual Rate',                      // i18n: 'signals.params.annualRate'
            type: 'number',
            default: 8,
            min: -100,
            max: 1000,
            step: 0.5,
            suffix: '%/yr',
        },
    ];

    computePoints(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
        if (!baseData.length) return [];

        const rate = Number(this.params.annualRate ?? 8) / 100;
        const baseValue = baseData[0].value;
        const startMs = new Date(baseData[0].date).getTime();

        return baseData.map(d => {
            const t = (new Date(d.date).getTime() - startMs) / 86_400_000 / 365;
            return {
                date: d.date,
                value: viewMode === 'percentage'
                    ? (Math.pow(1 + rate, t) - 1) * 100
                    : baseValue * Math.pow(1 + rate, t),
            };
        });
    }

    getLabel(): string {
        return `Compound ${this.params.annualRate ?? 8}%/yr`;
    }
}
```

### Signal Registry

```typescript
// frontend/src/lib/charts/signals/registry.ts

import type {SignalParamDescriptor} from './ChartSignal';
import {ChartSignal, type SignalConfig, type SignalStyle, DEFAULT_SIGNAL_COLORS} from './ChartSignal';
import {FxPairSignal} from './FxPairSignal';
import {LinearSignal} from './LinearSignal';
import {CompoundSignal} from './CompoundSignal';

// ═══════════════════════════════════════════════════════════════════
// REGISTRY MAP: signalType → constructor
// ═══════════════════════════════════════════════════════════════════

const SIGNAL_REGISTRY = new Map<string, typeof ChartSignal>([
    [FxPairSignal.signalType,   FxPairSignal   as unknown as typeof ChartSignal],
    [LinearSignal.signalType,   LinearSignal   as unknown as typeof ChartSignal],
    [CompoundSignal.signalType, CompoundSignal as unknown as typeof ChartSignal],
]);

// ═══════════════════════════════════════════════════════════════════
// PUBLIC API
// ═══════════════════════════════════════════════════════════════════

export interface SignalTypeInfo {
    type: string;
    displayName: string;
    icon: string;
    maxInstances?: number;
    paramDescriptors: SignalParamDescriptor[];
}

/** All registered signal types (for "Add signal" dropdown) */
export function getRegisteredSignalTypes(): SignalTypeInfo[] {
    return [...SIGNAL_REGISTRY.values()].map(Cls => ({
        type: Cls.signalType,
        displayName: Cls.displayName,
        icon: Cls.icon,
        maxInstances: Cls.maxInstances,
        paramDescriptors: Cls.paramDescriptors,
    }));
}

/** Create a NEW signal instance with default params and next color from palette */
export function createSignal(signalType: string, existingCount: number): ChartSignal | null {
    const Cls = SIGNAL_REGISTRY.get(signalType);
    if (!Cls) return null;

    const id = crypto.randomUUID();
    const style: SignalStyle = {
        color: DEFAULT_SIGNAL_COLORS[existingCount % DEFAULT_SIGNAL_COLORS.length],
        lineWidth: 2,
        lineType: 'dashed',
        arrowStart: false,
        arrowEnd: false,
    };

    const params: Record<string, unknown> = {};
    for (const desc of Cls.paramDescriptors) {
        params[desc.key] = desc.default;
    }

    return new (Cls as any)(id, style, params);
}

/** Recreate a signal instance from serialized config */
export function signalFromConfig(config: SignalConfig): ChartSignal | null {
    const Cls = SIGNAL_REGISTRY.get(config.signalType);
    if (!Cls) return null;
    return new (Cls as any)(config.id, config.style, config.params);
}

/** Check if adding another signal of this type is allowed */
export function canAddSignalType(signalType: string, currentSignals: SignalConfig[]): boolean {
    const Cls = SIGNAL_REGISTRY.get(signalType);
    if (!Cls || Cls.maxInstances === undefined) return true;
    return currentSignals.filter(s => s.signalType === signalType).length < Cls.maxInstances;
}
```

### How the UI reads parameters from classes

The `OrderableList` in `ChartSettingsModal` renders each signal item by:

```
1. Get type info: getRegisteredSignalTypes().find(t => t.type === config.signalType)
2. For each descriptor in typeInfo.paramDescriptors:
   - type === 'number'
     → <input type="number" min={desc.min} max={desc.max} step={desc.step}>
     → suffix (e.g. "%/yr") shown inline right of input
   - type === 'select'
     → if desc.dynamicOptionsKey → modal resolves options at runtime
       (e.g. 'configuredFxPairs' → configured pairs passed as prop)
     → else desc.options (static)
     → <select>
   - type === 'string' → <input type="text">
3. ALWAYS render (below type-specific params, on one row):
   - Color: <input type="color">
   - Width: <select> 1,2,3,4
   - Line type: <select> solid, dashed, dotted
   - Arrow start: <checkbox> (default off)
   - Arrow end: <checkbox> (default off)
4. 🗑 button to remove
```

---

## Architettura Chart Settings Store

### Tipo `ChartSettings`

```typescript
// frontend/src/lib/stores/chartSettingsStore.ts

import type {SignalConfig} from '$lib/charts/signals/ChartSignal';

export interface ChartSettings {
    colorByBaseline: boolean;       // default true
    areaFill: boolean;              // default true
    gridLines: boolean;             // default true
    staleGradient: boolean;         // default true
    signals: SignalConfig[];        // default [] — serialized signal configurations
}

export const DEFAULT_CHART_SETTINGS: ChartSettings = {
    colorByBaseline: true,
    areaFill: true,
    gridLines: true,
    staleGradient: true,
    signals: [],
};
```

### Store API

```typescript
// Module-level state (session-lifetime, lost on browser refresh)
let globalSettings: ChartSettings = structuredClone(DEFAULT_CHART_SETTINGS);
let pairOverrides = new Map<string, ChartSettings>();

// ── Read ──
export function getGlobalSettings(): ChartSettings;
export function getSettingsForPair(slug: string): ChartSettings;
    // → pairOverrides.get(slug) ?? structuredClone(globalSettings)

// ── Write ──
export function setGlobalSettings(s: ChartSettings): void;
    // → globalSettings = s
    // → pairOverrides.clear()  ← OVERWRITES ALL LOCAL SETTINGS

export function setPairSettings(slug: string, s: ChartSettings): void;
    // → pairOverrides.set(slug, s)

export function clearPairSettings(slug: string): void;
    // → pairOverrides.delete(slug) → card falls back to global
```

### Settings data flow

```
[Filter Bar ⚙️] → opens ChartSettingsModal (global)
    → save → setGlobalSettings() → overwrites global + clears all overrides
    → all cards re-render with new settings

[FxCard ⚙️ local] → opens ChartSettingsModal (pair-specific)
    → save → setPairSettings(slug, ...) → only this card
    → navigating to detail, the detail reads the same override

[Detail page] → reads getSettingsForPair(slug)
    → if modified → setPairSettings(slug, ...)
    → returning to list, the card sees the updated override
```

### Data flow: from SignalConfig to ECharts rendering

```
ChartSettings.signals (SignalConfig[])
    ↓ signalFromConfig() — registry deserializes
ChartSignal[] (live instances)
    ↓ for FxPairSignal: parent pre-fetches data, injects params._resolvedData
    ↓ signal.computePoints(baseData, viewMode)
LineDataPoint[] per signal
    ↓ signal.render(baseData, viewMode) — wraps into RenderedSignal
RenderedSignal[] — uniform format with color, lineWidth, lineType, arrowStart, arrowEnd
    ↓ passed as prop `overlaySignals` to LineChart / PriceChartCompact / PriceChartFull
LineChart treats ALL signals equally — it doesn't know or care about signal types.
For each RenderedSignal it adds an ECharts line series:
    - z: 1 (below main series)
    - NOT affected by visualMap (seriesIndex: 0 targets only main series)
    - symbol: 'none' (or 'arrow' at endpoints if arrowStart/arrowEnd)
    - Tooltip shows signal label
```

---

## Steps

### Step 1 — Fix Sync All (P1) ✅ COMPLETED
**Critical bug fix**, independent from redesign. See "Completed Steps Log" for details.

- **`FxSyncModal.svelte`**:
  - Add prop `currencies: string[]` (all configured currencies)
  - Pass `currencies: currencies.join(',')` to backend
  - Rewrite UI with consistent style: use `ConfirmModal` as reference (header with icon, structured body, styled footer)
  - Fix animation: use `RefreshCw` (rotates correctly) or CSS `[animation-direction:reverse]` on `RotateCcw`
  - i18n texts instead of hardcoded strings
  - After successful sync, show detailed result (rates synced count, which pairs)

- **`+page.svelte`**:
  - Compute `allConfiguredCurrencies` as derived (all unique currencies from pairs)
  - Pass to `FxSyncModal` as prop
  - In `handleSynced`: invalidate **all** `TimeSeriesStore` instances before `fetchAllPairData()`

### Step 2 — Signal Library (P4 infrastructure) ✅ COMPLETED
Created the signal class library.

- **`frontend/src/lib/charts/signals/`** (NEW folder):
  - `ChartSignal.ts` — abstract base + types (`SignalParamDescriptor`, `SignalStyle`, `SignalConfig`)
  - `FxPairSignal.ts` — real data signal, `maxInstances = 1`
  - `LinearSignal.ts` — linear annual slope, param `annualRate` with suffix `%/yr`
  - `CompoundSignal.ts` — compound growth, param `annualRate` with suffix `%/yr`
  - `registry.ts` — map `signalType → constructor`, factory `createSignal()`, `signalFromConfig()`, `canAddSignalType()`
  - `index.ts` — barrel exports

### Step 3 — Chart Settings Store (P2) ✅ COMPLETED
Created session-level settings store.

- **`chartSettingsStore.ts`** (NEW):
  - Types `ChartSettings` with `signals: SignalConfig[]`
  - `DEFAULT_CHART_SETTINGS`
  - API: `getGlobalSettings()`, `getSettingsForPair(slug)`, `setGlobalSettings()`, `setPairSettings()`, `clearPairSettings()`
  - `setGlobalSettings` overwrites global + `pairOverrides.clear()`

### Step 4 — Chart Settings Modal (P2 + P4) ✅ COMPLETED
Modal component for configuring aesthetics + signals.

- **`ChartSettingsModal.svelte`** (NEW):
  - **Aesthetics section**: 4 checkboxes (colorByBaseline, areaFill, gridLines, staleGradient)
  - **Signals section**: `OrderableList` of signal items
    - Each row: type (from registry `getRegisteredSignalTypes()`), params (from `paramDescriptors`), style (color/width/type/arrows)
    - For `FxPairSignal`: `pairSlug` options resolved dynamically from prop `availablePairs`; no instance limit
    - For synthetics: numeric inputs with suffix
    - All signal types: unlimited instances (no maxInstances enforced)
    - "+ Add signal" button at bottom, "🗑" to remove
  - Props: `open`, `settings: ChartSettings`, `mode: 'global' | 'pair'`, `availablePairs: string[]`
  - Callbacks: `onsave(settings: ChartSettings)`, `onclose()`
  - **If mode='global'**: banner "⚠ These settings will override all per-card customizations"

- **Connect to filter bar** `+page.svelte`: ⚙️ button → `ChartSettingsModal(mode='global')`
  - On confirm: `setGlobalSettings(newSettings)`

### Step 5 — Redesign FxCard (P3 + P2)
New layout B with local settings.

- **`FxCard.svelte`**: Rewrite
  - **Svelte 5 conversion**: from `createEventDispatcher`/`export let`/`$:` to `$props`/`$derived`/`$state`/callback props
  - **Layout B**:
    ```
    ┌──────────────────────────────────────┐
    │ 🇪🇺 EUR → 🇬🇧 GBP  [⇄] [%]  ✏️ Manual│  ← row 1: pair + controls + badge (ONLY if MANUAL)
    │ 0.8705  ▼ -0.25%                     │  ← row 2: prominent rate + future metrics
    ├──────────────────────────────────────┤
    │     ~~~~~~ mini chart ~~~~~~          │
    ├──────────────────────────────────────┤
    │    [⚙️][⟳][↻]          [✏️][🗑]      │  ← footer: settings+sync+refresh left, edit+delete right
    └──────────────────────────────────────┘
    ```
  - Local ⚙️ button: opens `ChartSettingsModal(mode='pair')` pre-populated with `getSettingsForPair(slug)`
  - Prop `chartSettings: ChartSettings` from parent (derived from store)
  - Pass aesthetics to `PriceChartCompact` (areaFill, colorByBaseline, gridLines, staleGradient)
  - Pass `overlayData` computed from signals to `PriceChartCompact`

- **Percentage infobox** in `+page.svelte`: info banner visible only when `globalViewMode === 'percentage'`:
  > "Percentage values (Δ%) are relative to the first day of the selected time window"
  - Style: `bg-blue-50 dark:bg-blue-900/20 border-blue-200` with info icon

### Step 6 — Overlay rendering in LineChart (P4) ✅ COMPLETED
Implement generic signal rendering in ECharts. The chart component doesn't care about
signal types — it receives a list of `RenderedSignal[]` and renders them all equally.

- **`LineChart.svelte`**:
  - New prop `overlaySignals: RenderedSignal[]` (from `$lib/charts/signals`)
  - In `renderChart()`: for each signal, push to `series[]`:
    ```javascript
    {
        type: 'line',
        name: signal.label,
        data: signal.data.map(d => useTupleFormat ? [dateIndex, d.value] : d.value),
        lineStyle: {color: signal.color, width: signal.lineWidth, type: signal.lineType},
        itemStyle: {color: signal.color},
        symbol: 'none',
        z: 1,  // below main series
        // If arrowStart/arrowEnd: markPoint at first/last data point with arrow symbol
        markPoint: buildArrowMarks(signal),
    }
    ```
  - **Arrow markers**: If `signal.arrowStart` or `signal.arrowEnd`, add `markPoint` entries
    with ECharts `symbol: 'arrow'` at start/end coordinates. Useful for detail page trend direction.
  - `visualMap.seriesIndex: 0` to target only main series
  - Tooltip updated to show all overlay series labels

- **`PriceChartCompact.svelte`**: Add prop `overlaySignals` (passthrough)
- **`PriceChartFull.svelte`**: Add prop `overlaySignals` (passthrough)

### Step 7 — Refactor OrderableList in DataTableToolbar (P5)
Remove duplicated code.

- **`DataTableToolbar.svelte`**: Remove lines 38-114 (drag&drop state + handlers)
- Use `OrderableList` with snippet: `[Eye/EyeOff icon] [col name]`
- GripVertical handle and mobile arrows handled automatically by OrderableList
- `onReorder` callback → extract id order → call `onReorderColumns`

### Step 8 — Integration & Test
- Connect everything in FX list and detail pages
- Verify settings session-persistence: card → detail → card
- Verify global override clears all pair settings
- Verify Sync All with real pairs
- Verify FxPairSignal pre-fetches data from TimeSeriesStore
- `./dev.py front check && ./dev.py front build`

---

## Execution Order

| # | Step | Complexity | Priority | Dependencies |
|---|------|------------|----------|--------------|
| 1 | Fix Sync All | Medium | ✅ Done | None |
| 2 | Signal Library | Medium | ✅ Done (updated 6 Mar) | None |
| 3 | Chart Settings Store | Low | ✅ Done | Step 2 (uses SignalConfig) |
| 4 | Chart Settings Modal | High | ✅ Done | Step 2 + 3 |
| 5 | Redesign FxCard | High | 🟡 High | Step 3 + 4 |
| 6 | Overlay rendering LineChart | Medium | ✅ Done | Step 2 (uses computePoints) |
| 7 | Refactor DataTableToolbar | Low | 🟢 Low | None |
| 8 | Integration & Test | Medium | 🟡 High | Step 1-6 |

```
Step 1 (Sync All fix)           ← independent, urgent
Step 7 (DataTable refactor)     ← independent, low priority

Step 2 (Signal Library)
    ↓
Step 3 (Settings Store) ──→ Step 6 (Overlay rendering)
    ↓
Step 4 (Settings Modal)
    ↓
Step 5 (FxCard redesign)
    ↓
Step 8 (Integration & Test)
```

---

## Technical Notes

### Signal Library extensibility
- To add a new signal type: create a subclass, register in `SIGNAL_REGISTRY`. The UI adapts automatically by reading `paramDescriptors`.
- For Phase 6 (Asset): add `AssetSignal` fetching asset data from backend, with `dynamicOptionsKey: 'configuredAssets'`.
- Default benchmarks: FX global defaults to `signals: []`. Asset defaults can include `CompoundSignal` with `annualRate: 8`.

### FxPairSignal: pre-fetch data (no instance limit)
- **No maxInstances limit**: user can overlay multiple FX pairs on the same chart. If the same pair is added twice, points overlap harmlessly (data is not permanent).
- The parent component (FxCard or detail page) pre-fetches the FX pair overlay data from `TimeSeriesStore` before calling `computePoints()`.
- Data injected in `signal.params._resolvedData` (`_` prefix = transient field, excluded from `toConfig()` serialization).
- If data unavailable (fetch in progress), signal is not rendered (graceful skip).

### DataTableToolbar → OrderableList
- **Confirmed**: vertical layout (stacked `column-option` items with GripVertical + ChevronUp/Down), identical to OrderableList. No horizontal variant needed.
- Direct migration: wrap columns in OrderableList with children snippet for rendering.

### Adding a new synthetic signal type in the future
1. Create `frontend/src/lib/charts/signals/NewSignal.ts` extending `ChartSignal`
2. Define `static signalType`, `displayName`, `icon`, `paramDescriptors`
3. Implement `computePoints()` and `getLabel()`
4. Register in `registry.ts` → `SIGNAL_REGISTRY.set(...)`
5. Done — UI automatically renders params and "Add signal" dropdown includes it

### Future: Unify main data loading with Signal pattern

Currently, the chart data pipeline is:
```
Page/Card → fetches data → passes LineDataPoint[] as `data` prop to LineChart
PriceChartFull does % conversion in `displayData` derived
```

The Signal Library introduces `overlayData` as additional series. But the **main data** still
flows as a raw `data: LineDataPoint[]` prop, separate from signals.

**Phase 6+ Migration Plan**: Replace direct `data` prop with a `PrimaryDataSignal` that
wraps the main series using the same interface. This enables:
- Uniform rendering: one signal array for everything (main + overlays)
- Main series is just `signals[0]` with `isPrimary: true`
- PriceChartFull's `displayData`/`displayPending` conversion becomes `computePoints(data, viewMode)`
- Percentage mode logic moves from PriceChartFull into the signal's `computePoints()`

**New class** (to be added in Phase 6):
```typescript
// frontend/src/lib/charts/signals/PrimaryDataSignal.ts

export class PrimaryDataSignal extends ChartSignal {
    static signalType = 'primary';
    static displayName = 'Primary Data';
    static icon = '📊';
    static maxInstances = 1;
    static paramDescriptors: SignalParamDescriptor[] = [];   // no user-editable params

    /** The primary signal uses the baseData directly as its own points */
    computePoints(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
        if (viewMode === 'absolute' || baseData.length === 0) return baseData;
        const base = baseData[0].value;
        if (base === 0) return baseData;
        return baseData.map(d => ({
            ...d,
            value: ((d.value - base) / base) * 100,
        }));
    }

    getLabel(): string { return 'Primary'; }
}
```

**Migration steps** (Phase 6, not now):
1. Add `PrimaryDataSignal` to the signal library + registry
2. In `PriceChartFull`: compute main series via `PrimaryDataSignal.computePoints()` instead of inline `displayData` derived
3. In `LineChart`: accept `signals: RenderedSignal[]` alongside (or replacing) `data` prop
4. `RenderedSignal = { data: LineDataPoint[]; style: SignalStyle; label: string; isPrimary: boolean }`
5. Render all series from the unified signals array; `isPrimary` controls which gets visualMap, tooltips, etc.
6. `PriceChartCompact`: same migration, pass signals instead of raw data

**Why not now**: The current `data` prop works fine. The migration adds complexity that only
pays off when Asset charts (Phase 6) and Dashboard (Phase 8) reuse the same components.
At that point, having a unified signal pipeline avoids duplicating % conversion, stale gradient,
and overlay logic across FX, Asset, and Dashboard chart components.

---

## Completed Steps Log

### Step 1 — Fix Sync All ✅ (5 Mar 2026)
**Changes made:**
- **`FxSyncModal.svelte`**: Full rewrite to Svelte 5 runes. Added `currencies: string[]` prop
  (passed from parent). Backend now receives correct currencies instead of hardcoded
  `"USD,GBP,CHF,JPY"`. New styled UI consistent with ConfirmModal (header with icon,
  structured body showing date range + currency count, footer with proper buttons).
  Fixed spin animation using `RefreshCw` (rotates correctly vs `RotateCcw` counterclockwise glyph).
  i18n-ready with fallbacks.
- **`+page.svelte`**: Passes `currencies={configuredCurrencies}` to FxSyncModal. Uses Svelte 5
  callback props (`onsynced`/`onclose`) instead of Svelte 4 `on:synced`/`on:close`. `handleSynced`
  no longer closes modal immediately — lets user see results, modal is closed manually.
  Invalidates all FxStores and refreshes data in background after sync.
- **i18n**: Added 5 keys (`fx.sync.title`, `fx.sync.description`, `fx.sync.currenciesCount`,
  `fx.sync.synced`, `fx.sync.syncing`, `fx.sync.start`) in all 4 languages (EN/IT/FR/ES).
- **Verified**: `./dev.py front check` → 0 errors, `./dev.py front build` → success.

### Step 2 — Signal Library ✅ (5 Mar 2026, updated 6 Mar 2026)
**Changes made:**
- Created `frontend/src/lib/charts/signals/` folder with 6 files:
  - `ChartSignal.ts` — Abstract base class with `SignalParamDescriptor`, `SignalStyle`, `SignalConfig`,
    `RenderedSignal` types. Base class provides `toConfig()` serialization (excludes `_`-prefixed transient
    fields) and `render()` convenience method.
  - `FxPairSignal.ts` — Real data signal from backend FX pairs. Pre-fetched data injected via
    `params._resolvedData`. **No maxInstances limit** (relaxed per user feedback — duplicates overlay harmlessly).
  - `LinearSignal.ts` — Synthetic: straight line y = y0×(1+rate×t). Param: `annualRate` with suffix `%/yr`.
  - `CompoundSignal.ts` — Synthetic: exponential y = y0×(1+rate)^t. Param: `annualRate` with suffix `%/yr`.
  - `registry.ts` — `SIGNAL_REGISTRY` map + factory functions: `createSignal()`, `signalFromConfig()`,
    `canAddSignalType()`, `getRegisteredSignalTypes()`.
  - `index.ts` — Barrel exports for all classes, types, and functions.
- All subclasses use `static override` for proper TypeScript inheritance.
- **6 Mar iteration**: Removed `maxInstances = 1` from `FxPairSignal`. Added `arrowStart`/`arrowEnd`
  boolean fields to `SignalStyle` (default false). Updated `RenderedSignal` to include arrows.
  Updated `createSignal()` default style to include `arrowStart: false, arrowEnd: false`.
  Charts will treat ALL signals uniformly — no "first" signal concept.
- **Verified**: `./dev.py front check` → 0 errors, 0 warnings.

### Step 3 — Chart Settings Store ✅ (5 Mar 2026)
**Changes made:**
- Created `frontend/src/lib/stores/chartSettingsStore.ts`:
  - `ChartSettings` interface: `colorByBaseline`, `areaFill`, `gridLines`, `staleGradient`, `signals[]`
  - `DEFAULT_CHART_SETTINGS` constant
  - Module-level state with `_version` Svelte 5 `$state()` counter for reactivity
  - Read API: `getGlobalSettings()`, `getSettingsForPair(slug)`, `hasPairOverride(slug)`, `getSettingsVersion()`
  - Write API: `setGlobalSettings()` (clears all pair overrides), `setPairSettings()`, `clearPairSettings()`, `resetAllSettings()`
  - All read functions access `_version` to register reactive dependencies
- **Verified**: `./dev.py front check` → 0 errors, 0 warnings.

### Step 4 — Chart Settings Modal ✅ (6 Mar 2026)
**Changes made:**
- Created `frontend/src/lib/components/charts/ChartSettingsModal.svelte` (Svelte 5 runes):
  - **Aesthetics section**: 4 checkbox toggles in 2×2 grid (colorByBaseline, areaFill, gridLines, staleGradient)
    with labels inside `<label>` wrapping for proper a11y associations.
  - **Signals section**: `OrderableList` of `SignalConfig[]` items. Each row dynamically renders:
    - Signal type icon + name + remove button
    - Type-specific params from `paramDescriptors[]` (number with suffix, select with dynamic options, text)
    - Style controls: color picker, lineWidth select (1-4), lineType select (solid/dashed/dotted),
      arrowStart checkbox, arrowEnd checkbox
  - "+ Add signal" buttons: one per registered signal type from registry.
  - Props: `open` ($bindable), `settings`, `mode`, `availablePairs`, `onsave`, `onclose`
  - Global mode banner: "⚠ These settings will override all per-card customizations"
  - ModalBase wrapper with max-width `xl`, proper header/footer
  - Helper functions `getParamNumber`/`getParamString` to avoid TypeScript `as` casts in templates
  - Uses `selected` attribute on `<option>` tags instead of `value` bind on `<select>` (Svelte 5 compatibility)
- **Connected to FX list page** (`+page.svelte`):
  - Imported `ChartSettingsModal`, `getGlobalSettings`, `setGlobalSettings`
  - Added `settingsModalOpen` state
  - Settings ⚙️ button `onclick` opens modal in `mode='global'`
  - Modal passes `availablePairs` from configured pairs
  - On save: `setGlobalSettings(s)` overwrites global + clears all pair overrides
- **Verified**: `./dev.py front check` → 0 errors, 0 warnings. `./dev.py front build` → success.

### Step 6 — Overlay rendering in LineChart ✅ (6 Mar 2026)
**Changes made:**
- **`LineChart.svelte`**:
  - Added `overlaySignals: RenderedSignal[]` prop (imported from `$lib/charts/signals`)
  - New overlay rendering loop after pending edits: for each signal, builds date-aligned series
    data with `connectNulls: true`, renders as ECharts line series with `z: 1` (below main)
  - Arrow markers: if `signal.arrowStart`/`arrowEnd`, adds `markPoint` entries with `symbol: 'arrow'`
    at first/last non-null data points (start arrow rotated 180° to point left)
  - Tooltip rewritten from single-series to multi-series: iterates all `params[]`, shows color dot +
    series name + value for each visible series. Stale warning and % note appended at the end.
  - `$effect` now registers `overlaySignals` as reactive dependency to trigger re-render on change
- **Verified**: `./dev.py front check` → 0 errors, 0 warnings. `./dev.py front build` → success.

---

## Files Involved

| File | Action |
|------|--------|
| `frontend/src/lib/charts/signals/ChartSignal.ts` | ✅ DONE — Base class + types + arrow markers |
| `frontend/src/lib/charts/signals/FxPairSignal.ts` | ✅ DONE — Real data signal (no maxInstances) |
| `frontend/src/lib/charts/signals/LinearSignal.ts` | ✅ DONE — Linear slope |
| `frontend/src/lib/charts/signals/CompoundSignal.ts` | ✅ DONE — Compound growth |
| `frontend/src/lib/charts/signals/registry.ts` | ✅ DONE — Registry + factory (arrows in defaults) |
| `frontend/src/lib/charts/signals/index.ts` | ✅ DONE — Barrel export |
| `frontend/src/lib/stores/chartSettingsStore.ts` | ✅ DONE — Session-level store |
| `frontend/src/lib/components/charts/ChartSettingsModal.svelte` | ✅ DONE — Settings configurator (aesthetics + signals) |
| `frontend/src/lib/components/fx/FxSyncModal.svelte` | ✅ DONE — Fix currencies + Svelte 5 + style |
| `frontend/src/lib/components/fx/FxCard.svelte` | REWRITE — Layout B + Svelte 5 |
| `frontend/src/lib/components/charts/LineChart.svelte` | ✅ DONE — overlaySignals prop + multi-series tooltip + arrows |
| `frontend/src/lib/components/charts/PriceChartCompact.svelte` | MODIFY — passthrough `overlaySignals` + aesthetics |
| `frontend/src/lib/components/charts/PriceChartFull.svelte` | MODIFY — passthrough `overlaySignals` + aesthetics |
| `frontend/src/routes/(app)/fx/+page.svelte` | ✅ PARTIAL — sync fix + settings modal done, card integration pending |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | MODIFY — local settings, overlay |
| `frontend/src/lib/components/table/DataTableToolbar.svelte` | REFACTOR — Use OrderableList |

---

## References to previous plans

- **plan-fxUiRefinementsRound2** Step 8 (Settings ⚙️, Overlay, Benchmark) → **fully absorbed** into this plan (Steps 2-6)
- **plan-phase05Fx** Step 3 (FxCard) → layout evolution in Step 5
- **plan-phase05Fx** §Test Futuri (provider reorder) → not covered here, remains noted in master plan
- **plan-fxUiFeedbackRound3** F13+F14 (localization) → completed, localized names used in cards

