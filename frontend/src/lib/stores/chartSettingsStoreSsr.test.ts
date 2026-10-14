import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const apiTransportCall = vi.hoisted(() => vi.fn());
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => apiTransportCall}),
    axiosInstance: new Proxy({}, {get: () => apiTransportCall}),
}));

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
let fetchMock = vi.fn();

Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    writable: true,
    value: {getItem, setItem, removeItem: vi.fn(), clear: vi.fn()},
});

const {DEFAULT_CHART_SETTINGS, getGlobalSettings, getSettingsForPair, setGlobalSettings, setPairSettings} = await import('./chartSettingsStore.svelte');

beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    apiTransportCall.mockReset();
});

afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
});

describe('chartSettingsStore on the server', () => {
    it('never reads storage and answers with the shipped defaults', () => {
        expect(getGlobalSettings()).toMatchObject({
            colorByBaseline: DEFAULT_CHART_SETTINGS.colorByBaseline,
            areaFill: DEFAULT_CHART_SETTINGS.areaFill,
            gridLines: DEFAULT_CHART_SETTINGS.gridLines,
            staleGradient: DEFAULT_CHART_SETTINGS.staleGradient,
            axisScales: {
                absolute: {mode: 'auto'},
                percentage: {mode: 'include0'},
                secondary: {},
            },
            calendarReturnWindow: DEFAULT_CHART_SETTINGS.calendarReturnWindow,
            signals: [],
        });
        expect(getSettingsForPair('EUR-USD', 'fx')).toMatchObject({
            axisScales: {
                absolute: {mode: 'auto'},
                percentage: {mode: 'include0'},
                secondary: {},
            },
            calendarReturnWindow: DEFAULT_CHART_SETTINGS.calendarReturnWindow,
            signals: [],
        });
        expect(getItem).not.toHaveBeenCalled();
        expect(fetchMock).not.toHaveBeenCalled();
        expect(apiTransportCall).not.toHaveBeenCalled();
    });

    it('accepts v2 writes in memory without scheduling storage or backend work', () => {
        vi.useFakeTimers();
        // The scoped global goes first: saving a scope clears that scope's own
        // per-item overrides, so the asset row has to be written after it.
        setGlobalSettings(
            {
                ...DEFAULT_CHART_SETTINGS,
                areaFill: false,
                axisScales: {
                    absolute: {mode: 'auto'},
                    percentage: {mode: 'custom', min: -25, max: 75},
                    secondary: {},
                },
            },
            'assets',
        );
        setPairSettings('asset-7', {
            ...DEFAULT_CHART_SETTINGS,
            gridLines: false,
            calendarReturnWindow: {
                kind: 'custom',
                preset: '1m',
                customAmount: 6,
                customUnit: 'months',
            },
        });

        // A pending debounce would fire well inside this window.
        vi.advanceTimersByTime(5_000);

        expect(setItem).not.toHaveBeenCalled();
        expect(fetchMock).not.toHaveBeenCalled();
        expect(apiTransportCall).not.toHaveBeenCalled();
        expect(getSettingsForPair('asset-7').gridLines).toBe(false);
        expect(getSettingsForPair('asset-7').calendarReturnWindow).toEqual({
            kind: 'custom',
            preset: '1m',
            customAmount: 6,
            customUnit: 'months',
        });
        expect(getGlobalSettings('assets').areaFill).toBe(false);
        expect(getGlobalSettings('assets').axisScales.percentage).toEqual({mode: 'custom', min: -25, max: 75});
    });
});
