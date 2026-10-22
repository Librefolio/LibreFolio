/**
 * Chart Settings Store — Browser-persisted cache for chart aesthetics and signal configs.
 *
 * Two levels:
 * - **Global settings**: applied to all cards/charts by default
 * - **Pair overrides**: per-pair customizations stored in localStorage and cleared
 *   when matching global settings are saved.
 *
 * NOT persisted to backend — settings live in user-scoped localStorage and survive refresh.
 *
 * @module stores/chartSettingsStore
 */

import {browser} from '$app/environment';
import type {SignalConfig} from '$lib/charts/signals';
import {DEFAULT_CALENDAR_RETURN_WINDOW, largestCalendarReturnPresetFor, sanitizeCalendarReturnWindow, type CalendarReturnWindowSelection} from '$lib/components/charts/calendarReturnWindow';
import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';

// ═══════════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════════

export type AxisScaleMode = 'auto' | 'include0' | 'custom';

export interface AxisScaleSettings {
    mode: AxisScaleMode;
    min?: number;
    max?: number;
}

export interface ChartAxisSettings {
    absolute: AxisScaleSettings;
    percentage: AxisScaleSettings;
    secondary: Record<string, AxisScaleSettings>;
}

/**
 * The view a chart opens in (Y-40): its prices, their change in percent, or the rolling return over the calendar window.
 * The list's top bar and the global settings set it for a scope, a card's button and the detail page for one chart.
 */
export type ChartPrimaryView = 'absolute' | 'percentage' | 'calendar-return';

export const CHART_PRIMARY_VIEWS: readonly ChartPrimaryView[] = ['absolute', 'percentage', 'calendar-return'];

export interface ChartSettings {
    /** Color line by baseline: green above, red below (in % mode) */
    colorByBaseline: boolean;
    /** Show area fill under the main line */
    areaFill: boolean;
    /** Show grid split lines */
    gridLines: boolean;
    /** Show stale-data gradient (per-point opacity for backward-filled data) */
    staleGradient: boolean;
    /** Unit-aware primary axes plus stable semantic secondary-axis settings. */
    axisScales: ChartAxisSettings;
    /** Last Calendar Return window for this asset. Ignored by non-asset charts. */
    calendarReturnWindow: CalendarReturnWindowSelection;
    /**
     * True until the user chooses a window: the window in force is then the largest preset that fits the period on screen
     * (`effectiveCalendarReturnWindow`), not `calendarReturnWindow`.
     */
    calendarReturnWindowAuto: boolean;
    /** The view the chart opens in (Y-40). */
    primaryView: ChartPrimaryView;
    /** Overlay signal configurations */
    signals: SignalConfig[];
}

export const DEFAULT_AXIS_SCALE: AxisScaleSettings = {
    mode: 'auto',
};

export const DEFAULT_PERCENTAGE_AXIS_SCALE: AxisScaleSettings = {
    mode: 'include0',
};

export const DEFAULT_CHART_SETTINGS: ChartSettings = {
    colorByBaseline: true,
    areaFill: true,
    gridLines: true,
    staleGradient: true,
    axisScales: {
        absolute: {...DEFAULT_AXIS_SCALE},
        percentage: {...DEFAULT_PERCENTAGE_AXIS_SCALE},
        secondary: {},
    },
    calendarReturnWindow: {...DEFAULT_CALENDAR_RETURN_WINDOW},
    calendarReturnWindowAuto: true,
    primaryView: 'percentage',
    signals: [],
};

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

/** Deep-clone that works with Svelte 5 $state proxy objects */
function deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
}

const STORAGE_VERSION = 3;
const STORAGE_BASE_KEY = 'chartSettingsStore';
const STORAGE_WRITE_DELAY_MS = 250;

interface PersistedChartSettings {
    version: typeof STORAGE_VERSION;
    globalSettings: ChartSettings;
    pairOverrides: Array<[string, ChartSettings]>;
}

function getStorageKey(): string {
    return `lf_${getClientSessionUserId() ?? 'anon'}_${STORAGE_BASE_KEY}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSignalConfig(value: unknown): value is SignalConfig {
    return isRecord(value) && typeof value.id === 'string' && typeof value.signalType === 'string' && isRecord(value.params) && isRecord(value.style);
}

function finiteNumber(value: unknown): number | undefined {
    return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

export function normalizeAxisScaleSettings(value: unknown, fallback: AxisScaleSettings): AxisScaleSettings {
    if (!isRecord(value)) return {...fallback};
    const mode: AxisScaleMode = value.mode === 'include0' || value.mode === 'custom' ? value.mode : 'auto';
    const min = finiteNumber(value.min);
    const max = finiteNumber(value.max);
    if (mode !== 'custom') return {mode};
    if (min !== undefined && max !== undefined && min > max) {
        return {mode, min: max, max: min};
    }
    return {mode, min, max};
}

function legacyAxisScale(value: Record<string, unknown>): AxisScaleSettings {
    return normalizeAxisScaleSettings(
        {
            mode: value.yAxisMode,
            min: value.yAxisMin,
            max: value.yAxisMax,
        },
        DEFAULT_AXIS_SCALE,
    );
}

function sanitizeAxisSettings(value: Record<string, unknown>): ChartAxisSettings {
    const legacy = legacyAxisScale(value);
    if (!isRecord(value.axisScales)) {
        const hasLegacyAxis = 'yAxisMode' in value || 'yAxisMin' in value || 'yAxisMax' in value;
        return {
            absolute: hasLegacyAxis ? {...legacy} : {...DEFAULT_AXIS_SCALE},
            percentage: hasLegacyAxis ? {...legacy} : {...DEFAULT_PERCENTAGE_AXIS_SCALE},
            secondary: {},
        };
    }

    const secondary: Record<string, AxisScaleSettings> = {};
    if (isRecord(value.axisScales.secondary)) {
        for (const [key, scale] of Object.entries(value.axisScales.secondary)) {
            if (!key.trim()) continue;
            secondary[key] = normalizeAxisScaleSettings(scale, DEFAULT_AXIS_SCALE);
        }
    }
    return {
        absolute: normalizeAxisScaleSettings(value.axisScales.absolute, DEFAULT_AXIS_SCALE),
        percentage: normalizeAxisScaleSettings(value.axisScales.percentage, DEFAULT_PERCENTAGE_AXIS_SCALE),
        secondary,
    };
}

function isPrimaryView(value: unknown): value is ChartPrimaryView {
    return CHART_PRIMARY_VIEWS.includes(value as ChartPrimaryView);
}

function sameWindow(left: CalendarReturnWindowSelection, right: CalendarReturnWindowSelection): boolean {
    return left.kind === right.kind && left.preset === right.preset && left.customAmount === right.customAmount && left.customUnit === right.customUnit;
}

/** The view a scope opens in until it is set (Y-40): the FX list on absolute rates, as before; every other chart in percent. */
function scopeDefaultView(scope?: string): ChartPrimaryView {
    return scope === 'fx' ? 'absolute' : DEFAULT_CHART_SETTINGS.primaryView;
}

/** The scope a stored key belongs to: a scope's own settings, an asset's, else an FX pair's. */
function scopeOfKey(key: string): string | undefined {
    if (key.startsWith('__global_')) return key.slice('__global_'.length, -2);
    if (key.startsWith('__')) return undefined;
    return key.startsWith('asset-') ? 'assets' : 'fx';
}

/** Settings the store falls back on for a scope that has none of its own: the base ones, opening on the scope's view. */
function forScope(settings: ChartSettings, scope?: string): ChartSettings {
    return scope === 'fx' ? {...settings, primaryView: scopeDefaultView(scope)} : settings;
}

function sanitizeSettings(value: unknown, defaultView: ChartPrimaryView = DEFAULT_CHART_SETTINGS.primaryView): ChartSettings {
    if (!isRecord(value)) return {...deepClone(DEFAULT_CHART_SETTINGS), primaryView: defaultView};
    const calendarReturnWindow = sanitizeCalendarReturnWindow(value.calendarReturnWindow);

    return {
        colorByBaseline: typeof value.colorByBaseline === 'boolean' ? value.colorByBaseline : DEFAULT_CHART_SETTINGS.colorByBaseline,
        areaFill: typeof value.areaFill === 'boolean' ? value.areaFill : DEFAULT_CHART_SETTINGS.areaFill,
        gridLines: typeof value.gridLines === 'boolean' ? value.gridLines : DEFAULT_CHART_SETTINGS.gridLines,
        staleGradient: typeof value.staleGradient === 'boolean' ? value.staleGradient : DEFAULT_CHART_SETTINGS.staleGradient,
        axisScales: sanitizeAxisSettings(value),
        calendarReturnWindow,
        // Stored before Y-40: a window other than the shipped default was chosen by the user.
        calendarReturnWindowAuto: typeof value.calendarReturnWindowAuto === 'boolean' ? value.calendarReturnWindowAuto : sameWindow(calendarReturnWindow, DEFAULT_CALENDAR_RETURN_WINDOW),
        primaryView: isPrimaryView(value.primaryView) ? value.primaryView : defaultView,
        signals: normalizeSignalConfigs(value.signals),
    };
}

function normalizeSignalConfigs(value: unknown): SignalConfig[] {
    if (!Array.isArray(value)) return [];
    return value.flatMap((item) => {
        if (!isSignalConfig(item)) return [];
        return [deepClone(item)];
    });
}

function sanitizeStoredSettings(value: unknown, defaultView?: ChartPrimaryView): ChartSettings {
    const sanitized = sanitizeSettings(value, defaultView);
    sanitized.signals = sanitized.signals.map((signal) => {
        const {_resolvedData: _discarded, ...serializableParams} = signal.params;
        return {
            ...signal,
            params: serializableParams,
        };
    });
    return sanitized;
}

// Version 3 (decision 29): the Rolling Return over N observations (RISK_ROLLING_RETURN) left the catalogue; a saved
// one becomes the calendar Rolling Return (ASSET_CALENDAR_ROLLING_RETURN) over the same number of days.
const REMOVED_ROLLING_RETURN_TYPE = 'risk-rolling-return';
const CALENDAR_ROLLING_RETURN_TYPE = 'asset-calendar-rolling-return';
const REMOVED_ROLLING_RETURN_AXIS = 'independent:risk_return';
const CALENDAR_ROLLING_RETURN_AXIS = 'independent:calendar_return';

function migrateRollingReturnSignal(signal: unknown): unknown {
    if (!isRecord(signal) || signal.signalType !== REMOVED_ROLLING_RETURN_TYPE) return signal;
    const migrated: Record<string, unknown> = {...signal, signalType: CALENDAR_ROLLING_RETURN_TYPE};
    if (isRecord(signal.params) && 'window' in signal.params) {
        const {window: observations, ...params} = signal.params;
        migrated.params = {...params, window_days: observations};
    }
    if (isRecord(signal.componentStyles) && 'rolling_return' in signal.componentStyles) {
        const {rolling_return: outputStyle, ...componentStyles} = signal.componentStyles;
        migrated.componentStyles = {...componentStyles, calendar_return: outputStyle};
    }
    return migrated;
}

function migrateRollingReturnSettings(settings: unknown): unknown {
    if (!isRecord(settings)) return settings;
    const migrated: Record<string, unknown> = {...settings};
    if (Array.isArray(settings.signals)) migrated.signals = settings.signals.map(migrateRollingReturnSignal);
    const scales = settings.axisScales;
    if (isRecord(scales) && isRecord(scales.secondary) && REMOVED_ROLLING_RETURN_AXIS in scales.secondary) {
        const {[REMOVED_ROLLING_RETURN_AXIS]: scale, ...secondary} = scales.secondary;
        migrated.axisScales = {...scales, secondary: CALENDAR_ROLLING_RETURN_AXIS in secondary ? secondary : {...secondary, [CALENDAR_ROLLING_RETURN_AXIS]: scale}};
    }
    return migrated;
}

/**
 * Bring stored settings of an earlier version (1 or 2) to the current one, without touching the parsed input.
 * Version 3 turns every saved observation Rolling Return into the calendar one; anything else passes as it is.
 */
export function migratePersistedChartSettings(parsed: unknown): unknown {
    if (!isRecord(parsed) || (parsed.version !== 1 && parsed.version !== 2)) return parsed;
    return {
        ...parsed,
        version: STORAGE_VERSION,
        globalSettings: migrateRollingReturnSettings(parsed.globalSettings),
        pairOverrides: Array.isArray(parsed.pairOverrides) ? parsed.pairOverrides.map((entry) => (Array.isArray(entry) && entry.length === 2 ? [entry[0], migrateRollingReturnSettings(entry[1])] : entry)) : parsed.pairOverrides,
    };
}

function parsePersistedSettings(raw: string | null): PersistedChartSettings | null {
    if (!raw) return null;
    try {
        const parsed: unknown = migratePersistedChartSettings(JSON.parse(raw));
        if (!isRecord(parsed) || parsed.version !== STORAGE_VERSION) return null;

        const overrides = new Map<string, ChartSettings>();
        if (Array.isArray(parsed.pairOverrides)) {
            for (const entry of parsed.pairOverrides) {
                if (!Array.isArray(entry) || entry.length !== 2 || typeof entry[0] !== 'string') continue;
                overrides.set(entry[0], sanitizeStoredSettings(entry[1], scopeDefaultView(scopeOfKey(entry[0]))));
            }
        }

        return {
            version: STORAGE_VERSION,
            globalSettings: sanitizeStoredSettings(parsed.globalSettings),
            pairOverrides: [...overrides.entries()],
        };
    } catch {
        return null;
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Module-level state (hydrated from localStorage on client)
// ═══════════════════════════════════════════════════════════════════════════════

let globalSettings: ChartSettings = deepClone(DEFAULT_CHART_SETTINGS);
let pairOverrides = new Map<string, ChartSettings>();
let hydratedStorageKey: string | null = null;
let saveTimer: ReturnType<typeof setTimeout> | null = null;

// Reactive version counter — Svelte 5 components can use this to trigger re-renders
let _version = $state(0);

function bump() {
    _version++;
}

function loadFromStorage(): void {
    if (!browser) return;

    const storageKey = getStorageKey();
    if (hydratedStorageKey === storageKey) return;

    let raw: string | null = null;
    try {
        raw = localStorage.getItem(storageKey);
    } catch {
        raw = null;
    }

    const persisted = parsePersistedSettings(raw);
    globalSettings = persisted ? deepClone(persisted.globalSettings) : deepClone(DEFAULT_CHART_SETTINGS);
    pairOverrides = new Map(persisted?.pairOverrides ?? []);
    hydratedStorageKey = storageKey;
    if (persisted) {
        const sanitizedRaw = JSON.stringify(persisted);
        if (raw !== sanitizedRaw) {
            try {
                localStorage.setItem(storageKey, sanitizedRaw);
            } catch {
                // Keep the sanitized in-memory state when storage is unavailable.
            }
        }
    }
}

function persistNow(): void {
    if (!browser) return;

    const storageKey = getStorageKey();
    const payload: PersistedChartSettings = {
        version: STORAGE_VERSION,
        globalSettings: sanitizeStoredSettings(globalSettings),
        pairOverrides: [...pairOverrides.entries()].map(([key, settings]) => [key, sanitizeStoredSettings(settings)] as [string, ChartSettings]),
    };

    try {
        localStorage.setItem(storageKey, JSON.stringify(payload));
        hydratedStorageKey = storageKey;
    } catch {
        // Ignore storage errors (private browsing, quota exceeded).
    }
}

let pagehideBound = false;

/** A write the debounce still holds is done when the page goes away for good: a reload, a close, a navigation away (Y-40). */
function flushOnPagehide(): void {
    if (pagehideBound || typeof window === 'undefined') return;
    pagehideBound = true;
    window.addEventListener('pagehide', () => {
        if (!saveTimer) return;
        clearTimeout(saveTimer);
        saveTimer = null;
        persistNow();
    });
}

function schedulePersist(): void {
    if (!browser) return;
    flushOnPagehide();
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
        saveTimer = null;
        persistNow();
    }, STORAGE_WRITE_DELAY_MS);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Read API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get current global chart settings.
 * If scope is provided, returns scoped global settings (e.g., 'assets' or 'fx').
 * Falls back to the base global settings if no scoped override exists.
 * Returns a copy to prevent accidental mutation.
 */
export function getGlobalSettings(scope?: string): ChartSettings {
    loadFromStorage();
    // Access _version to register reactive dependency
    void _version;
    if (scope) {
        const scoped = pairOverrides.get(`__global_${scope}__`);
        if (scoped) return deepClone(scoped);
    }
    return forScope(deepClone(globalSettings), scope);
}

/**
 * Get effective settings for a specific pair.
 * Returns pair override if it exists, otherwise falls back to scoped global (if scope provided),
 * then base global settings.
 */
export function getSettingsForPair(slug: string, scope?: string): ChartSettings {
    loadFromStorage();
    // Access _version to register reactive dependency
    void _version;
    const override = pairOverrides.get(slug);
    if (override) return deepClone(override);
    if (scope) {
        const scoped = pairOverrides.get(`__global_${scope}__`);
        if (scoped) return deepClone(scoped);
    }
    return forScope(deepClone(globalSettings), scope);
}

/**
 * Get the reactive version counter (for Svelte 5 reactivity).
 * Use in derived/effect to track changes.
 */
export function getSettingsVersion(): number {
    return _version;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Write API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Save global settings.
 * If scope is provided (e.g., 'assets' or 'fx'), saves as a scoped global
 * and only clears pair overrides within that scope.
 * Without scope: clears ALL pair overrides (backward compatible).
 */
export function setGlobalSettings(settings: ChartSettings, scope?: string): void {
    loadFromStorage();
    const sanitized = withWindowChoice(sanitizeSettings(settings), scope ? (pairOverrides.get(scopeKey(scope)) ?? globalSettings) : globalSettings);
    if (scope) {
        pairOverrides.set(scopeKey(scope), deepClone(sanitized));
        // Clear per-item overrides for this scope only
        for (const key of [...pairOverrides.keys()]) {
            if (key.startsWith('__global_')) continue; // Don't clear scoped globals
            if (scope === 'assets' && key.startsWith('asset-')) {
                pairOverrides.delete(key);
            } else if (scope === 'fx' && !key.startsWith('asset-') && !key.startsWith('__')) {
                pairOverrides.delete(key);
            }
        }
    } else {
        globalSettings = deepClone(sanitized);
        pairOverrides.clear();
    }
    bump();
    schedulePersist();
}

/**
 * Save per-pair settings override.
 * Does NOT affect other pairs or global settings.
 */
export function setPairSettings(slug: string, settings: ChartSettings): void {
    loadFromStorage();
    pairOverrides.set(slug, deepClone(withWindowChoice(sanitizeSettings(settings), pairOverrides.get(slug) ?? globalSettings)));
    bump();
    schedulePersist();
}

function scopeKey(scope: string): string {
    return `__global_${scope}__`;
}

/** Whether `key` is the override of one chart of `scope` (the same partition `setGlobalSettings` clears). */
function inScope(key: string, scope: string): boolean {
    if (key.startsWith('__')) return false;
    return scope === 'assets' ? key.startsWith('asset-') : scope === 'fx' ? !key.startsWith('asset-') : false;
}

/** A saved window other than the one stored before is a window the user chose, whoever saves it (Y-40). */
function withWindowChoice(next: ChartSettings, previous: ChartSettings): ChartSettings {
    return sameWindow(next.calendarReturnWindow, previous.calendarReturnWindow) ? next : {...next, calendarReturnWindowAuto: false};
}

/**
 * The view of a whole scope (Y-40, V-3 a): the list's top bar and its global settings. Every chart of the scope is reset to
 * it, keeping everything else it saved; the other scope is not touched.
 */
export function setScopePrimaryView(view: ChartPrimaryView, scope: string): void {
    loadFromStorage();
    if (!isPrimaryView(view)) return;
    const key = scopeKey(scope);
    pairOverrides.set(key, {...deepClone(pairOverrides.get(key) ?? globalSettings), primaryView: view});
    for (const [slug, settings] of pairOverrides) {
        if (inScope(slug, scope)) pairOverrides.set(slug, {...settings, primaryView: view});
    }
    bump();
    schedulePersist();
}

/**
 * The view of one chart (Y-40, V-1 a and V-2 a): a card's button. An override it creates starts from the scope's settings.
 *
 * It rebuilds the override from the store's own copy: what a page wrote into the settings it holds — a comparison's
 * `_resolvedData` in its signal configs — is not in it. A page that holds such settings saves its view with them instead:
 * `setPairSettings(slug, {...settings, primaryView, signals})`, as the asset detail page does.
 */
export function setItemPrimaryView(slug: string, view: ChartPrimaryView, scope?: string): void {
    loadFromStorage();
    if (!isPrimaryView(view)) return;
    const current = pairOverrides.get(slug) ?? (scope ? pairOverrides.get(scopeKey(scope)) : undefined) ?? globalSettings;
    pairOverrides.set(slug, {...deepClone(current), primaryView: view});
    bump();
    schedulePersist();
}

/** The view a card's button turns to (Y-40, the developer's order): percent → rolling return → absolute → percent. */
export function nextCardPrimaryView(view: ChartPrimaryView): ChartPrimaryView {
    return view === 'percentage' ? 'calendar-return' : view === 'calendar-return' ? 'absolute' : 'percentage';
}

/**
 * How the asset detail page opens a view (Y-40): the rolling return is its `calendar-return` mode, the two others its price
 * mode in that view. The rolling return keeps the detail's percent view underneath, as today.
 */
export function detailModesForPrimaryView(view: ChartPrimaryView): {primaryMode: 'price' | 'calendar-return'; viewMode: 'absolute' | 'percentage'} {
    if (view === 'calendar-return') return {primaryMode: 'calendar-return', viewMode: 'percentage'};
    return {primaryMode: 'price', viewMode: view};
}

/** The view the detail page saves when its user changes mode or view (Y-40, V-2 a). */
export function primaryViewForDetailModes(primaryMode: 'price' | 'calendar-return', viewMode: 'absolute' | 'percentage'): ChartPrimaryView {
    return primaryMode === 'calendar-return' ? 'calendar-return' : viewMode;
}

/**
 * The rolling-return window in force for `rangeDays` on screen: the one the user chose, else the largest preset of the
 * selector that fits the period (the developer's decision for the first start, 20/10).
 */
export function effectiveCalendarReturnWindow(settings: Pick<ChartSettings, 'calendarReturnWindow' | 'calendarReturnWindowAuto'>, rangeDays: number): CalendarReturnWindowSelection {
    if (!settings.calendarReturnWindowAuto) return {...settings.calendarReturnWindow};
    return {...settings.calendarReturnWindow, kind: 'preset', preset: largestCalendarReturnPresetFor(rangeDays)};
}

registerClientSessionReset('chartSettingsStore', () => {
    hydratedStorageKey = null;
    loadFromStorage();
    bump();
});
