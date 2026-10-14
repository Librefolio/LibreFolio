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
import {DEFAULT_CALENDAR_RETURN_WINDOW, sanitizeCalendarReturnWindow, type CalendarReturnWindowSelection} from '$lib/components/charts/calendarReturnWindow';
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
    signals: [],
};

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

/** Deep-clone that works with Svelte 5 $state proxy objects */
function deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
}

const STORAGE_VERSION = 2;
const STORAGE_BASE_KEY = 'chartSettingsStore';
const STORAGE_WRITE_DELAY_MS = 250;

interface PersistedChartSettings {
    version: 1 | typeof STORAGE_VERSION;
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

function sanitizeSettings(value: unknown): ChartSettings {
    if (!isRecord(value)) return deepClone(DEFAULT_CHART_SETTINGS);

    return {
        colorByBaseline: typeof value.colorByBaseline === 'boolean' ? value.colorByBaseline : DEFAULT_CHART_SETTINGS.colorByBaseline,
        areaFill: typeof value.areaFill === 'boolean' ? value.areaFill : DEFAULT_CHART_SETTINGS.areaFill,
        gridLines: typeof value.gridLines === 'boolean' ? value.gridLines : DEFAULT_CHART_SETTINGS.gridLines,
        staleGradient: typeof value.staleGradient === 'boolean' ? value.staleGradient : DEFAULT_CHART_SETTINGS.staleGradient,
        axisScales: sanitizeAxisSettings(value),
        calendarReturnWindow: sanitizeCalendarReturnWindow(value.calendarReturnWindow),
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

function sanitizeStoredSettings(value: unknown): ChartSettings {
    const sanitized = sanitizeSettings(value);
    sanitized.signals = sanitized.signals.map((signal) => {
        const {_resolvedData: _discarded, ...serializableParams} = signal.params;
        return {
            ...signal,
            params: serializableParams,
        };
    });
    return sanitized;
}

function parsePersistedSettings(raw: string | null): PersistedChartSettings | null {
    if (!raw) return null;
    try {
        const parsed: unknown = JSON.parse(raw);
        if (!isRecord(parsed) || (parsed.version !== 1 && parsed.version !== STORAGE_VERSION)) return null;

        const overrides = new Map<string, ChartSettings>();
        if (Array.isArray(parsed.pairOverrides)) {
            for (const entry of parsed.pairOverrides) {
                if (!Array.isArray(entry) || entry.length !== 2 || typeof entry[0] !== 'string') continue;
                overrides.set(entry[0], sanitizeStoredSettings(entry[1]));
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

function schedulePersist(): void {
    if (!browser) return;
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
    return deepClone(globalSettings);
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
    return deepClone(globalSettings);
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
    const sanitized = sanitizeSettings(settings);
    if (scope) {
        pairOverrides.set(`__global_${scope}__`, deepClone(sanitized));
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
    pairOverrides.set(slug, deepClone(sanitizeSettings(settings)));
    bump();
    schedulePersist();
}

registerClientSessionReset('chartSettingsStore', () => {
    hydratedStorageKey = null;
    loadFromStorage();
    bump();
});
