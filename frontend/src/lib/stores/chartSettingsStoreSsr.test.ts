import {describe, expect, it, vi} from 'vitest';

/**
 * Server-side rendering guard for the chart settings store.
 *
 * Deliberately a separate file from `chartSettingsStore.test.ts`: the two need
 * opposite values of `browser`, and importing the store twice in one file would
 * register a second reset callback under the same key, silently unhooking the
 * first module from account changes. Vitest isolates files, so this is the safe
 * way to hold both.
 *
 * The shared `$app/environment` mock already reports `browser: false`, which is
 * what SvelteKit gives a load running on the server.
 */

const getItem = vi.fn(() => null);
const setItem = vi.fn();

Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    writable: true,
    value: {getItem, setItem, removeItem: vi.fn(), clear: vi.fn()},
});

const {DEFAULT_CHART_SETTINGS, getGlobalSettings, getSettingsForPair, setGlobalSettings, setPairSettings} = await import('./chartSettingsStore.svelte');

describe('chartSettingsStore on the server', () => {
    it('never reads storage and answers with the shipped defaults', () => {
        expect(getGlobalSettings()).toMatchObject({
            colorByBaseline: DEFAULT_CHART_SETTINGS.colorByBaseline,
            areaFill: DEFAULT_CHART_SETTINGS.areaFill,
            gridLines: DEFAULT_CHART_SETTINGS.gridLines,
            staleGradient: DEFAULT_CHART_SETTINGS.staleGradient,
            yAxisMode: 'auto',
            signals: [],
        });
        expect(getSettingsForPair('EUR-USD', 'fx')).toMatchObject({yAxisMode: 'auto', signals: []});
        expect(getItem).not.toHaveBeenCalled();
    });

    it('accepts writes in memory without scheduling a storage write', () => {
        vi.useFakeTimers();
        // The scoped global goes first: saving a scope clears that scope's own
        // per-item overrides, so the asset row has to be written after it.
        setGlobalSettings({...DEFAULT_CHART_SETTINGS, areaFill: false}, 'assets');
        setPairSettings('asset-7', {...DEFAULT_CHART_SETTINGS, gridLines: false});

        // A pending debounce would fire well inside this window.
        vi.advanceTimersByTime(5_000);
        vi.useRealTimers();

        expect(setItem).not.toHaveBeenCalled();
        expect(getSettingsForPair('asset-7').gridLines).toBe(false);
        expect(getGlobalSettings('assets').areaFill).toBe(false);
    });
});
