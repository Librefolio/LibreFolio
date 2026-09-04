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
import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';

// ═══════════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface ChartSettings {
    /** Color line by baseline: green above, red below (in % mode) */
    colorByBaseline: boolean;
    /** Show area fill under the main line */
    areaFill: boolean;
    /** Show grid split lines */
    gridLines: boolean;
    /** Show stale-data gradient (per-point opacity for backward-filled data) */
    staleGradient: boolean;
    /** Y-axis mode: 'auto' fits to data range, 'include0' always shows 0, 'custom' uses yAxisMin/Max */
    yAxisMode: 'auto' | 'include0' | 'custom';
    /** Custom Y-axis minimum (only used when yAxisMode === 'custom') */
    yAxisMin?: number;
    /** Custom Y-axis maximum (only used when yAxisMode === 'custom') */
    yAxisMax?: number;
    /** Overlay signal configurations */
    signals: SignalConfig[];
}

export const DEFAULT_CHART_SETTINGS: ChartSettings = {
    colorByBaseline: true,
    areaFill: true,
    gridLines: true,
    staleGradient: true,
    yAxisMode: 'auto',
    yAxisMin: undefined,
    yAxisMax: undefined,
    signals: [],
};

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

/** Deep-clone that works with Svelte 5 $state proxy objects */
function deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
}

const STORAGE_VERSION = 1;
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

function sanitizeSettings(value: unknown): ChartSettings {
    if (!isRecord(value)) return deepClone(DEFAULT_CHART_SETTINGS);

    const yAxisMode = value.yAxisMode === 'include0' || value.yAxisMode === 'custom' ? value.yAxisMode : 'auto';
    const yAxisMin = typeof value.yAxisMin === 'number' && Number.isFinite(value.yAxisMin) ? value.yAxisMin : undefined;
    const yAxisMax = typeof value.yAxisMax === 'number' && Number.isFinite(value.yAxisMax) ? value.yAxisMax : undefined;

    return {
        colorByBaseline: typeof value.colorByBaseline === 'boolean' ? value.colorByBaseline : DEFAULT_CHART_SETTINGS.colorByBaseline,
        areaFill: typeof value.areaFill === 'boolean' ? value.areaFill : DEFAULT_CHART_SETTINGS.areaFill,
        gridLines: typeof value.gridLines === 'boolean' ? value.gridLines : DEFAULT_CHART_SETTINGS.gridLines,
        staleGradient: typeof value.staleGradient === 'boolean' ? value.staleGradient : DEFAULT_CHART_SETTINGS.staleGradient,
        yAxisMode,
        yAxisMin,
        yAxisMax,
        signals: Array.isArray(value.signals) ? deepClone(value.signals) : [],
    };
}

function parsePersistedSettings(raw: string | null): PersistedChartSettings | null {
    if (!raw) return null;
    try {
        const parsed: unknown = JSON.parse(raw);
        if (!isRecord(parsed) || parsed.version !== STORAGE_VERSION) return null;

        const overrides = new Map<string, ChartSettings>();
        if (Array.isArray(parsed.pairOverrides)) {
            for (const entry of parsed.pairOverrides) {
                if (!Array.isArray(entry) || entry.length !== 2 || typeof entry[0] !== 'string') continue;
                overrides.set(entry[0], sanitizeSettings(entry[1]));
            }
        }

        return {
            version: STORAGE_VERSION,
            globalSettings: sanitizeSettings(parsed.globalSettings),
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
}

function persistNow(): void {
    if (!browser) return;

    const storageKey = getStorageKey();
    const payload: PersistedChartSettings = {
        version: STORAGE_VERSION,
        globalSettings: deepClone(globalSettings),
        pairOverrides: [...pairOverrides.entries()].map(([key, settings]) => [key, deepClone(settings)] as [string, ChartSettings]),
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
    if (scope) {
        pairOverrides.set(`__global_${scope}__`, deepClone(settings));
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
        globalSettings = deepClone(settings);
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
    pairOverrides.set(slug, deepClone(settings));
    bump();
    schedulePersist();
}

registerClientSessionReset('chartSettingsStore', () => {
    hydratedStorageKey = null;
    loadFromStorage();
    bump();
});
