# Plan: FX Card Redesign, Chart Settings, Signal Library & Sync All Fix

**Data creazione**: 5 Marzo 2026
**Status**: 🔄 IN PROGRESS — Steps 1-6 done. Step 4 refined (9 Mar): preview Abs/% toggle, synthetic data 365d, SineSignal added, toggle estetici fix, add-buttons moved above list, per-card settings wired. Step 5 done (Layout B + Svelte 5). Sync icons fixed (RotateCw). Prossimo: Step 7 (DataTable refactor, optional) → Step 8 (Integration & Test)
**Dipendenze**: plan-fxUiRefinementsRound2 Step 8, plan-phase05Fx Steps 3-5, plan-fxSyncApiRedesign (sync API pair-based)
**Espansione**: `plan-signalLibraryExpansion.prompt.md` ← indicatori tecnici (EMA, MACD, RSI, Bollinger), dual-axis, KaTeX tooltip, MkDocs docs
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
├── ChartSignal.ts       # Classe base astratta + tipi condivisi + daysBetween utility
├── FxPairSignal.ts      # Segnale dati reali (FX pair dal backend)
├── LinearSignal.ts      # Retta con pendenza annua costante
├── CompoundSignal.ts    # Crescita con interesse composto (iterativo, performance)
├── SineSignal.ts        # Onda sinusoidale (amplitude, period, offset)
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
    markerStart: MarkerType;                    // marker at first point, null = none
    markerEnd: MarkerType;                      // marker at last point, null = none
}

// MarkerType = 'arrow' | 'circle' | 'diamond' | 'pin' | null

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
        markerStart: null,
        markerEnd: null,
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
   - Marker start: <select> None, Arrow, Circle, Diamond, Pin
   - Marker end: <select> None, Arrow, Circle, Diamond, Pin
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
RenderedSignal[] — uniform format with color, lineWidth, lineType, markerStart, markerEnd
    ↓ passed as prop `overlaySignals` to LineChart / PriceChartCompact / PriceChartFull
LineChart treats ALL signals equally — it doesn't know or care about signal types.
For each RenderedSignal it adds an ECharts line series:
    - z: 1 (below main series)
    - NOT affected by visualMap (seriesIndex: 0 targets only main series)
    - symbol: 'none' (or marker shape at endpoints if markerStart/markerEnd set)
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

### Step 4 — Chart Settings Modal (P2 + P4) ✅ COMPLETED + Iteration
Modal component for configuring aesthetics + signals.

- **`ChartSettingsModal.svelte`**:
  - **Aesthetics section**: 4 toggle switches (matching project SettingToggle pattern)
  - **Signals section**: `OrderableList` of signal items
  - **Dirty check**: Cancel triggers `ConfirmModal` (warning=true, arancione) if changes detected
  - **structuredClone fix**: replaced with `JSON.parse(JSON.stringify(...))` for Svelte 5 proxy compat
  - **aria-label** on all toggle buttons for a11y

- **Connect to filter bar** `+page.svelte`: ⚙️ button → `ChartSettingsModal(mode='global')`
  - On confirm: `setGlobalSettings(newSettings)`

#### 🔄 Signal Card Layout — Pending Decision (3 alternatives)

The current signal card layout uses native HTML selects and text labels.
User feedback: use project selectors, show visual previews, add flags for FX pairs.

**ALTERNATIVE A — "Two-Row Compact"**
Type-params on row 1, style controls on row 2. Minimal vertical footprint.
```
┌─[⠿]───────────────────────────────────────────────────────────[🗑]─┐
│  💱 FX Pair    🇪🇺 EUR/🇬🇧 GBP  ▼                                  │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│  🎨■  W[━━]▼  [─ ─ ─]▼  Start[◇]▼  End[→]▼                      │
└─────────────────────────────────────────────────────────────────────┘
```
- Row 1: signal icon + type label + type-specific params (FxPair: CurrencySearchSelect with flags)
- Row 2: color swatch, width preview (line thickness), style preview (solid/dashed/dotted line),
  marker start/end preview (visual icon of the shape)
- ⠿ = drag handle (desktop), ↑↓ arrows (mobile)
- 🗑 top-right corner
- **Pro**: Very compact, minimal space. Good when many signals.
- **Con**: Two rows per signal = moderate density.

**ALTERNATIVE B — "Inline Ribbon"**
Everything on one row with icon-only controls. Most compact possible.
```
┌─[⠿]─ 💱 EUR/GBP ▼ ─── 🎨■ [━]▼ [- -]▼ ◇▼ →▼ ──────────── [🗑]─┐
└────────────────────────────────────────────────────────────────────┘
```
- Single row: handle, type icon, param selector, color, width, style, markers, delete
- All controls inline, separator between param and style zones
- Width/style/markers show visual icons only (no text labels)
- **Pro**: Ultra-compact, maximizes vertical space for chart preview or adding many signals
- **Con**: Can feel crowded, harder on mobile, less discoverable for new users

**ALTERNATIVE C — "Card with Preview Strip"**
Params top, visual style as a live-preview strip below.
```
┌─[⠿]────────────────────────────────────────────────────────[🗑]───┐
│  💱 FX Pair    🇪🇺 EUR / 🇬🇧 GBP  ▼                               │
│                                                                    │
│  ◇──── ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ────→     [🎨] [⚙ style] │
│  ↑ markerStart    line preview (color+width+type)    markerEnd     │
└────────────────────────────────────────────────────────────────────┘
```
- Top: signal type + params (with project selectors + flags)
- Bottom: live SVG preview strip showing the actual line (color, thickness, dash pattern)
  with marker icons at start/end. Clicking the strip opens a style popover.
- Color picker and style button to the right of the strip.
- **Pro**: Most intuitive — user SEES the result immediately. Low cognitive load.
- **Con**: Tallest layout per signal, complex SVG rendering. But most delightful UX.

**Decision pending** from user review.

#### 📊 Preview Chart in Modal (TODO)
Add a small chart preview at the top of the modal that shows current aesthetics applied
(using the same `PriceChartCompact` component with synthetic demo data).
Live-updates as toggles change. Shows overlay signals in real-time when added.

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
  - **Endpoint markers**: If `signal.markerStart` or `signal.markerEnd` is non-null, add `markPoint`
    entries at start/end coordinates with the specified ECharts symbol type ('arrow', 'circle',
    'diamond', 'pin'). Arrow start marker rotated 180° to point backwards.
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
- **6 Mar iteration**: Removed `maxInstances` completely from `ChartSignal` base class and `FxPairSignal`.
  Removed `canAddSignalType()` function — no limits needed. Replaced `arrowStart`/`arrowEnd` booleans
  with `MarkerType = 'arrow' | 'circle' | 'diamond' | 'pin' | null` enum. `SignalStyle` uses
  `markerStart: MarkerType` and `markerEnd: MarkerType` (null = no marker). Updated `RenderedSignal`,
  `createSignal()` defaults, and all downstream consumers. Charts treat ALL signals uniformly.
- **9 Mar iteration**: `CompoundSignal.computePoints()` rewritten to use **iterative computation**
  instead of per-point `Math.pow()`. Computes `dailyFactor = (1+rate)^(1/365)` once, then
  multiplies iteratively point-by-point. Also refactored date arithmetic: `daysBetween()` utility
  moved to `ChartSignal` base class as a `protected static` method shared by all subclasses.
  Removed millisecond-based arithmetic from both `LinearSignal` and `CompoundSignal` — now both
  use `ChartSignal.daysBetween(dateA, dateB)` which parses YYYY-MM-DD strings via `Date.UTC`.
  (JS has no built-in day-diff, so one `Date.UTC` + divide is unavoidable, but it's in one place.)
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
  - Endpoint markers: if `signal.markerStart`/`markerEnd` is non-null, adds `markPoint` entries
    with the specified ECharts symbol type ('arrow', 'circle', 'diamond', 'pin') at first/last
    non-null data points (arrow start marker rotated 180° to point backwards)
  - Tooltip rewritten from single-series to multi-series: iterates all `params[]`, shows color dot +
    series name + value for each visible series. Stale warning and % note appended at the end.
  - `$effect` now registers `overlaySignals` as reactive dependency to trigger re-render on change
- **Verified**: `./dev.py front check` → 0 errors, 0 warnings. `./dev.py front build` → success.

### Bugfix Round — 6 Mar 2026 PM
**Critical: `$state is not defined` runtime error (HTTP 500 on /fx page)**

Root cause: `chartSettingsStore.ts` used `$state(0)` rune but had `.ts` extension instead of `.svelte.ts`.
Svelte 5 runes (`$state`, `$derived`, `$effect`) only work in `.svelte` or `.svelte.ts` files. The build
succeeded because Vite's SSR transform processes `.ts` files differently, but at runtime in the browser
the rune was not compiled, resulting in `$state is not defined`.

**Changes:**
- Renamed `chartSettingsStore.ts` → `chartSettingsStore.svelte.ts`
- Updated all imports to use `$lib/stores/chartSettingsStore.svelte` path
  (SvelteKit resolves `.svelte.ts` → `.svelte.js` at compile time)

**Also in this round:**
- **Removed `canAddSignalType()`**: Function no longer needed since all signal types are unlimited
  (no `maxInstances` on any class). Removed from `registry.ts`, `index.ts` barrel, and `ChartSignal.ts`.
- **Removed `maxInstances` from `ChartSignal` base class** and `SignalTypeInfo` interface.
- **Replaced `arrowStart`/`arrowEnd` booleans with `MarkerType` enum**: New `MarkerType = 'arrow' | 'circle' | 'diamond' | 'pin' | null`.
  `SignalStyle` now has `markerStart: MarkerType` and `markerEnd: MarkerType` (null = no marker).
  `RenderedSignal` updated accordingly. `createSignal()` defaults to `null` (no markers).
  `ChartSettingsModal` now shows `<select>` dropdowns instead of checkboxes for marker type.
  `LineChart` uses the marker type string as ECharts symbol name directly.
- **SemiDonutChart**: Already extracted as reusable component in `components/charts/SemiDonutChart.svelte`
  during Phase 4. No action needed.

**Verified**: `./dev.py front check` → 0 errors, 0 warnings. `./dev.py front build` → success.

### Bugfix Round 2 — 6 Mar 2026 (user testing feedback)

**Critical: `structuredClone` crash on Apply button**
Root cause: `structuredClone(signals)` fails because Svelte 5 `$state()` produces Proxy objects
that are not cloneable via `structuredClone`. Error: `DataCloneError: could not be cloned`.
Fix: replaced ALL `structuredClone` with `JSON.parse(JSON.stringify(...))` via `deepClone()` helper
in both `ChartSettingsModal.svelte` and `chartSettingsStore.svelte.ts`.

**Other fixes:**
- **Aesthetics: checkboxes → toggle switches**: Replaced `<input type="checkbox">` with `<button>`
  toggle switches matching the project's `SettingToggle.svelte` design pattern (green pill with
  sliding dot). Added `aria-label` on all 4 toggles for a11y (0 svelte-check warnings).
- **Cancel with dirty check**: Added `isDirty()` function comparing local state vs initial settings.
  If dirty, Cancel shows a `ConfirmModal` (warning=true, arancione, not red) asking "Discard changes?".
  If clean, closes silently.
- **Type annotation**: Added explicit `ChartSettings` type on `onsave` callback in `+page.svelte`.

**Console errors analysis:**
- `content-script.js:104 Failed to get subsystem status` → browser extension, not our code. Ignore.
- `api/v1/fx/currencies/convert 404` → **EXPLAINED**: the convert endpoint returns 404 when no rates
  exist for the requested pair. This happened because the SNB provider was completely broken and produced
  0 rates for ALL currencies (not just CNY). Now fixed with the SNB rewrite. If 404 still appears for
  other pairs, it means the sync hasn't been run yet or the provider doesn't support that currency.
- `A listener indicated an asynchronous response` → browser extension. Ignore.
- `structuredClone DataCloneError` → **FIXED** (see above).

**Verified**: `./dev.py front check` → 0 errors, 0 warnings. `./dev.py front build` → success.

### SNB Provider Rewrite — 6 Mar 2026 (backend bug fix)

**Root cause of CHF→CNY sync failure**: The SNB provider (`backend/app/services/fx_providers/snb.py`)
was completely broken since inception. Multiple critical bugs:

1. **CSV parser used `,` separator** — SNB uses `;` (semicolon-separated)
2. **Expected daily dates `YYYY-MM-DD`** — SNB only provides monthly data `YYYY-MM`
3. **Expected simple 2-column CSV** — actual format has 4 columns with metadata header
4. **Hardcoded currency map** — no `CNY` in multi-unit currencies list
5. **Per-currency HTTP requests** — inefficient, could use single request for all currencies
6. **Dataset labeled "daily"** — actually monthly averages (no daily dataset exists)

**Complete rewrite using JSON API:**
- **Dynamic currency map**: fetched from `/api/cube/devkum/dimensions/en` (lazy-loaded, cached for process lifetime).
  Walks nested dimension items recursively, extracts D1 id → ISO code + multiplier mapping.
  Now supports 25 currencies (was 10 hardcoded) without any code changes when SNB adds new currencies.
- **JSON data endpoint**: uses `/api/cube/devkum/data/json/en` with `dimSel=D0(M0),D1(EUR1,CNY100,...)`
  filter to request only M0 (monthly average) for only the needed currencies. Much more robust than CSV parsing.
- **Single HTTP request** for all currencies (was one per currency).
- **Date assigned to 1st of month** (`YYYY-MM` → `date(year, month, 1)`) for compatibility with daily rate storage.
- **Rate normalization**: D1 id contains multiplier (e.g. `CNY100` → divide by 100). No more separate
  `multi_unit_currencies` property needed — managed internally via dimension map.
- **Debug test suite**: `pipenv run python -m backend.app.services.fx_providers.snb [dimensions|json|parser|supported|datasets|all]`

**Also analyzed: convert endpoint 404 in frontend**
The 404 on `POST /api/v1/fx/currencies/convert` when clicking sync on CHF→CNY card is **caused by**
the SNB sync producing 0 rates → no data in DB → convert endpoint returns 404 because there are no
rates to convert with. With the SNB fix, sync will now produce monthly data points and the convert
will work.

**Note**: SNB only provides monthly averages. For a CHF→CNY pair, data will have 1 point per month
(assigned to 1st), not daily. This means the line chart will show fewer data points compared to
ECB-sourced pairs. The backward-fill logic in the convert endpoint will interpolate for dates between
monthly points.

**Verified**: `pipenv run python -m backend.app.services.fx_providers.snb parser` → ✅ CNY: 5 rates parsed.

---

## Pending Feedback Items (Step 4 iteration)


### ✅ 📐 Signal Card Layout — DECIDED: Layout C v2 ("Card with Preview Strip")
Implemented 6 Mar 2026, refined same day.
- **Math params** on top row (type-specific: pair selector, annual rate, etc.)
- **Visual style strip** on bottom row:
  - Color picker at start (leftmost)
  - Marker start: clickable cycle button (null→arrow→circle→diamond→pin→null), colored with signal color, no dropdown
  - SVG line preview (full width): shows actual color + width + dash pattern. Click opens popover.
  - Marker end: same clickable cycle, colored
  - Line style popover: tiny overlay with SVG buttons for type (solid/dashed/dotted) and width (1-4px), all shown as visual SVG previews
  - Click-outside closes popover (invisible backdrop pattern)

### ✅ 🌍 i18n of ChartSettingsModal — COMPLETED 6 Mar 2026
All hardcoded strings replaced with `$t()` calls. Added 25+ new i18n keys under `chartSettings.*`:
- Title, warning, aesthetics, overlay signals, empty state
- Style labels (color, width, lineType, markerStart, markerEnd)
- Line types (solid, dashed, dotted), markers (none, arrow, circle, diamond, pin)
- Apply, cancel, discard changes confirmation

### ✅ FxSyncModal Padding Fix — COMPLETED 6 Mar 2026
Added `px-6 py-4` to header, body, and footer sections (was missing horizontal padding).
Matches `ChartSettingsModal` pattern. No longer "tutto attaccato".

### ✅ `dev.py i18n search` CLI Rewrite — COMPLETED 6 Mar 2026
**Bug**: Old search matched per-language then only showed matched languages (others as "—").
This gave confusing results where searching a Spanish word showed "—" for EN/IT/FR.

**Fix**: Complete rewrite using `flatten_dict` for all languages, union of all keys.
- **Always shows ALL languages** for every matching key
- New flags: `--keys` (search only key names), `--values` (search only values), `--lang` (restrict to specific languages)
- Default (no flags): search both keys and values across all languages
- Shows search mode in output header: `(in keys + values[all])`, `(in keys)`, `(in values[it,es])`, etc.
- Also noted typo: `bxrokers.sharing.lastOwnerWarning` should be `brokers.sharing.lastOwnerWarning` (not fixed, just flagged)

### 🔍 Sync Feedback to Frontend — Analysis (pending implementation)

### ✅ Step 5 — FxCard Redesign (Layout B) — 9 Mar 2026
**Changes made:**
- **Full Svelte 5 runes migration**: Replaced `createEventDispatcher` + `export let` with `interface Props` +
  `$props()` + callback props (`onedit`, `ondelete`, `onrefresh`, `onsync`, `onsettings`).
- **Layout B** implemented:
  - **Row 1**: Pair with flags (🇪🇺 EUR → 🇬🇧 GBP) + swap [⇄] + toggle [%] + Manual badge (right-aligned)
  - **Row 2**: Prominent rate (text-xl font-bold) + delta with ▲/▼ arrows on same baseline
  - **Mini chart**: PriceChartCompact with new props: `chartSettings` passthrough (areaFill, colorByBaseline,
    gridLines), `overlaySignals` for signal rendering
  - **Footer split**: Left side (⚙️ Settings, ⟳ Sync, ↻ Refresh) | Right side (✏️ Edit, 🗑 Delete)
- **New props**: `chartSettings?: ChartSettings`, `overlaySignals?: RenderedSignal[]`, `onsettings?` callback
- **Parent page updated**: `/fx/+page.svelte` handlers converted from `CustomEvent` to direct callback signatures
- **daysBetween refactored**: Utility moved to `ChartSignal` base class as `protected static daysBetween()`,
  shared by `LinearSignal` and `CompoundSignal`. No more millisecond arithmetic duplication.
- **Verified**: `./dev.py front check` → 0 errors, 0 warnings. `./dev.py front build` → success.

### 🔍 Sync Feedback to Frontend — Analysis (pending implementation)
**Problem**: When sync completes, the frontend doesn't know which pairs had 0 data (e.g., SNB→CNY before fix).
The user wants non-invasive feedback about sync outcomes per-pair.

**Current API response** (`FXSyncResponse`):
```json
{"synced": 244, "date_range": {...}, "currencies": ["CAD", "GBP", "JPY", "USD"]}
```
- `synced` = total changed rates
- `currencies` = currencies that had at least 1 change

**Problem**: If SNB fetches CNY but all values already exist (0 changed), CNY won't appear in `currencies`.
But if SNB returns 0 rates because the currency has no data, same result. The frontend can't distinguish.

**Proposed solution** (TODO — not yet implemented):
1. **Backend**: Extend `FXSyncResponse` with per-provider detail:
   ```python
   provider_results: list[ProviderSyncResult]  # each has: provider, fetched, changed, skipped_currencies
   ```
   This lets the frontend show: "ECB: 4 currencies ✓ | SNB: CNY — no data available"

2. **Frontend**: In `FxSyncModal`, after sync, show collapsible detail per provider.
   For the per-card sync button, show a brief toast/badge if sync returned 0 rates for that pair.

3. **Non-invasive approach**: Only show warnings (amber banner) for currencies with 0 fetched rates,
   not for currencies with 0 changed (which is normal when data is already up-to-date).

**Impact**: Requires backend schema change + API response enrichment + frontend UI. Medium effort.
Defer to next iteration unless specifically requested.

### 📊 Preview Chart in Settings Modal (TODO)
Add a small preview chart at the top of the modal showing current aesthetics.
- Global mode: use synthetic sinusoidal data (shows positive/negative segments for baseline color testing)
- Pair mode: use actual pair data from TimeSeriesStore
- Overlay signals rendered on top in real-time as they are added/configured
- Primary signal always in default green color
- Uses same `PriceChartCompact` component
- **Blocking on**: Step 5 (FxCard redesign) for the chart integration pattern

### ✅ Step 4 Iteration — Preview Chart + Settings Polish — 9 Mar 2026
**Issues fixed (from user testing feedback):**

1. **Aesthetics toggles non riflessi nel preview** — `LineChart.$effect` solo toccava `data` e `overlaySignals`
   come dipendenze reattive. Aggiunti `areaFill`, `colorByBaseline`, `showGridLines`, `viewMode`, `compact`,
   `showMiniAxis`, `lineColor`, `darkLineColor` per registrarli e forzare re-render al cambio.

2. **Preview Abs/% toggle** — Aggiunto `previewViewMode` $state con toggle button nell'header della sezione
   Preview. Il preview chart ora può mostrare sia valori assoluti che percentuali.

3. **Dati sintetici estesi a 365 giorni** — Modificato `generateSyntheticData()`: 90→365 giorni, 3 cicli
   completi di sinusoide ±10%. Permette ai segnali LinearSignal e CompoundSignal di mostrare divergenza
   significativa su arco temporale annuale.

4. **SineSignal registrato** — Creato `SineSignal.ts` come segnale sintetico ufficiale (non più sinusoide
   hardcoded). Parametri: `amplitude` (%), `period` (giorni), `offset` (%). Registrato in `registry.ts`.
   Icona: 〰️. La sinusoide demo nel preview resta come dati base, i SineSignal sono overlay aggiuntivi.

5. **"Add signal" buttons spostati sopra la lista** — I pulsanti "+" ora compaiono subito sotto il titolo
   "Overlay Signals", prima della lista segnali. Più intuitivo per l'utente.

6. **FX Pair in preview non più skippato** — Ora skippa solo se `_resolvedData` non è presente (prima
   skippava tutti gli FxPairSignal indiscriminatamente).

7. **Per-card ⚙️ settings** — Cablato handler completo nella pagina FX:
   - `handleCardSettings(slug)` → apre modale in `mode='pair'` con dati coppia
   - `settingsTargetSlug` traccia quale card ha la modale aperta (null = global)
   - `settingsForModal` è un `$derived` che restituisce settings appropriati (pair o global)
   - `handleSettingsSave` salva con `setPairSettings`/`setGlobalSettings` in base al target
   - `getRenderedSignals(slug, data, viewMode)` calcola overlay signals per ogni card
   - FxCard riceve ora `chartSettings` e `overlaySignals` come props

8. **Icona sync corretta** — `RotateCcw` → `RotateCw` (senso orario) per sync, in FxCard e toolbar.
   Refresh mantiene `RefreshCw` (icona circolare). Import puliti.

**Verified**: `./dev.py front check` → 0 errors, 0 warnings. `./dev.py front build` → success.

---

## 🔍 Backend FX Sync Analysis (6 Mar 2026)

### Current API: `GET /api/v1/fx/currencies/sync`
The API accepts individual currencies (CSV: `"EUR,USD,GBP,..."`) not pairs.
In Auto-Configuration mode (no provider param):
1. Loads ALL `fx_currency_pair_sources` from DB
2. Groups by provider → extracts individual currencies per provider
3. Calls `ensure_rates_multi_source()` per provider with flat currency list
4. `ensure_rates_multi_source()` generates **all possible pairs** between currencies (N*(N-1)/2)
   — this creates spurious pairs not configured by user!
5. Response returns individual currencies, not pairs

### Problems Identified:
- **Spurious pairs**: If ECB gets [CAD,EUR,GBP,JPY,USD], it generates 10 pairs when only 4 are configured
- **Wasted fetch**: Provider APIs may return data for unwanted pairs
- **Confusing response**: `currencies_synced: ["CAD","GBP","JPY","USD"]` — user doesn't know which pairs
- **API design**: `currencies` param should be `pairs` (e.g. `"EUR-GBP,EUR-USD"`)

### Planned Fix (breaking change — no backward compat needed):
- Change API param from `currencies` to `pairs` (CSV of `BASE-QUOTE` slugs)
- Pass explicit pairs to `ensure_rates_multi_source()` instead of flat currencies
- Response should return pair slugs, not individual currencies
- Frontend already passes pair slugs since this session's refactor

### 📝 Documentation TODO:
When writing MkDocs documentation for FX (Phase 5 docs step):
- Document the pair-based sync API (new design)
- Document provider fallback mechanism (priority-based)
- Document MANUAL provider sentinel behavior
- Document FX data flow: frontend → API → provider → normalize → DB
- Update API examples in docs
- The existing docstrings in `fx.py` and `fx_providers/*.py` are outdated

---

## Files Involved

| File | Action |
|------|--------|
| `frontend/src/lib/charts/signals/ChartSignal.ts` | ✅ DONE — Base class + types + arrow markers |
| `frontend/src/lib/charts/signals/FxPairSignal.ts` | ✅ DONE — Real data signal (no maxInstances) |
| `frontend/src/lib/charts/signals/LinearSignal.ts` | ✅ DONE — Linear slope |
| `frontend/src/lib/charts/signals/CompoundSignal.ts` | ✅ DONE — Compound growth |
| `frontend/src/lib/charts/signals/SineSignal.ts` | ✅ DONE — Sine wave (amplitude, period, offset) |
| `frontend/src/lib/charts/signals/registry.ts` | ✅ DONE — Registry + factory (4 types) |
| `frontend/src/lib/charts/signals/index.ts` | ✅ DONE — Barrel export |
| `frontend/src/lib/stores/chartSettingsStore.svelte.ts` | ✅ DONE — Session-level store (renamed from .ts → .svelte.ts for $state) |
| `frontend/src/lib/components/charts/ChartSettingsModal.svelte` | ✅ DONE — Settings + i18n (25 keys) + Layout C v3 (marker popovers, SVG line popover upward, square caps) |
| `frontend/src/lib/components/fx/FxSyncModal.svelte` | ✅ DONE — Pair-based (not currency-based), Svelte 5, padding fix |
| `frontend/src/lib/components/fx/FxCard.svelte` | ✅ DONE — Layout B + Svelte 5 + RotateCw sync icon |
| `frontend/src/lib/components/charts/LineChart.svelte` | ✅ DONE — overlaySignals + multi-series tooltip + reactive aesthetic props |
| `frontend/src/lib/components/charts/PriceChartCompact.svelte` | ✅ DONE — passthrough overlaySignals + aesthetics |
| `frontend/src/lib/components/charts/PriceChartFull.svelte` | MODIFY — passthrough `overlaySignals` + aesthetics |
| `frontend/src/routes/(app)/fx/+page.svelte` | ✅ PARTIAL — pair-based sync + settings modal done, card integration pending |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | MODIFY — local settings, overlay |
| `frontend/src/lib/components/table/DataTableToolbar.svelte` | REFACTOR — Use OrderableList |
| `backend/app/services/fx_providers/snb.py` | ✅ DONE — Complete rewrite: JSON API, dynamic dimensions, 25 currencies |
| `backend/app/api/v1/fx.py` | TODO — Refactor sync API to pair-based |
| `backend/app/services/fx.py` | TODO — Refactor `ensure_rates_multi_source` to accept pairs |

---

## References to previous plans

- **plan-fxUiRefinementsRound2** Step 8 (Settings ⚙️, Overlay, Benchmark) → **fully absorbed** into this plan (Steps 2-6)
- **plan-phase05Fx** Step 3 (FxCard) → layout evolution in Step 5
- **plan-phase05Fx** §Test Futuri (provider reorder) → not covered here, remains noted in master plan
- **plan-fxUiFeedbackRound3** F13+F14 (localization) → completed, localized names used in cards

