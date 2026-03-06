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
    /** Overlay signal configurations */
    signals: SignalConfig[];
}

export const DEFAULT_CHART_SETTINGS: ChartSettings = {
    colorByBaseline: true,
    areaFill: true,
    gridLines: true,
    staleGradient: true,
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
 * Returns a copy to prevent accidental mutation.
 */
export function getGlobalSettings(): ChartSettings {
    // Access _version to register reactive dependency
    void _version;
    return deepClone(globalSettings);
}

/**
 * Get effective settings for a specific pair.
 * Returns pair override if it exists, otherwise falls back to global settings.
 */
export function getSettingsForPair(slug: string): ChartSettings {
    // Access _version to register reactive dependency
    void _version;
    const override = pairOverrides.get(slug);
    return override ? deepClone(override) : deepClone(globalSettings);
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
 * IMPORTANT: clears ALL pair overrides — global settings override everything.
 */
export function setGlobalSettings(settings: ChartSettings): void {
    globalSettings = deepClone(settings);
    pairOverrides.clear();
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

