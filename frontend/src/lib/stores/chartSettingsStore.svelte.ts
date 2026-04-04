/**
 * Chart Settings Store — Session-level cache for chart aesthetics and signal configs.
 *
 * Two levels:
 * - **Global settings**: applied to all cards/charts by default
 * - **Pair overrides**: per-pair customizations that persist during session navigation
 *   (card → detail → card) but are cleared when global settings are saved.
 *
 * NOT persisted to backend — session-lifetime only (lost on browser refresh).
 *
 * @module stores/chartSettingsStore
 */

import type {SignalConfig} from '$lib/charts/signals';

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

// ═══════════════════════════════════════════════════════════════════════════════
// Module-level state (session-lifetime)
// ═══════════════════════════════════════════════════════════════════════════════

let globalSettings: ChartSettings = deepClone(DEFAULT_CHART_SETTINGS);
let pairOverrides = new Map<string, ChartSettings>();

// Reactive version counter — Svelte 5 components can use this to trigger re-renders
let _version = $state(0);

function bump() {
    _version++;
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
 * Check if a pair has custom (overridden) settings.
 */
export function hasPairOverride(slug: string): boolean {
    void _version;
    return pairOverrides.has(slug);
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
}

/**
 * Save per-pair settings override.
 * Does NOT affect other pairs or global settings.
 */
export function setPairSettings(slug: string, settings: ChartSettings): void {
    pairOverrides.set(slug, deepClone(settings));
    bump();
}

/**
 * Remove per-pair override — pair falls back to global settings.
 */
export function clearPairSettings(slug: string): void {
    pairOverrides.delete(slug);
    bump();
}

/**
 * Reset everything to defaults (for testing or "reset all" button).
 */
export function resetAllSettings(): void {
    globalSettings = deepClone(DEFAULT_CHART_SETTINGS);
    pairOverrides.clear();
    bump();
}

