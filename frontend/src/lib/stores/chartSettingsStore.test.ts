import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

// The shared `$app/environment` mock reports `browser: false`, which makes every
// storage path in this store a no-op. Nothing below would run against it.
vi.mock('$app/environment', () => ({browser: true}));
const apiTransportCall = vi.hoisted(() => vi.fn());
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => apiTransportCall}),
    axiosInstance: new Proxy({}, {get: () => apiTransportCall}),
}));

import {transitionClientSession} from '$lib/stores/app/clientSession';
import type {SignalConfig} from '$lib/charts/signals';

import {DEFAULT_CHART_SETTINGS, getGlobalSettings, getSettingsForPair, getSettingsVersion, setGlobalSettings, setPairSettings, type ChartSettings} from './chartSettingsStore.svelte';

/**
 * Chart settings store — hydration, sanitising, scope rules and persistence.
 *
 * The store keeps its state at module level and re-reads localStorage only when
 * the resolved account changes, so each test claims a brand-new user id: that is
 * the store's own re-hydration trigger, not a back door.
 */

const STORAGE_SUFFIX = 'chartSettingsStore';
const WRITE_DELAY_MS = 250;

let backing = new Map<string, string>();
let getItem = vi.fn((key: string) => backing.get(key) ?? null);
let setItem = vi.fn((key: string, value: string) => void backing.set(key, value));
let fetchMock = vi.fn();

let userSeq = 0;

function storageKeyFor(userId: string): string {
    return `lf_${userId}_${STORAGE_SUFFIX}`;
}

/** Claim a fresh account, which is what forces the store to re-read storage. */
function freshUser(): string {
    const userId = `chart-settings-u${++userSeq}`;
    transitionClientSession(userId);
    return userId;
}

/** Write a raw payload under a user's key *before* that user becomes current. */
function seed(userId: string, payload: unknown): void {
    backing.set(storageKeyFor(userId), typeof payload === 'string' ? payload : JSON.stringify(payload));
}

function persistedFor(userId: string): {version: number; globalSettings: ChartSettings; pairOverrides: Array<[string, ChartSettings]>} | null {
    const raw = backing.get(storageKeyFor(userId));
    return raw === undefined ? null : JSON.parse(raw);
}

/** Flush the store's debounced write. */
function flushWrite(): void {
    vi.advanceTimersByTime(WRITE_DELAY_MS);
}

function settings(overrides: Partial<ChartSettings> = {}): ChartSettings {
    return {
        ...DEFAULT_CHART_SETTINGS,
        axisScales: {
            absolute: {...DEFAULT_CHART_SETTINGS.axisScales.absolute},
            percentage: {...DEFAULT_CHART_SETTINGS.axisScales.percentage},
            secondary: {...DEFAULT_CHART_SETTINGS.axisScales.secondary},
        },
        calendarReturnWindow: {...DEFAULT_CHART_SETTINGS.calendarReturnWindow},
        signals: [...DEFAULT_CHART_SETTINGS.signals],
        ...overrides,
    };
}

function legacySettings(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        colorByBaseline: true,
        areaFill: true,
        gridLines: true,
        staleGradient: true,
        yAxisMode: 'auto',
        yAxisMin: null,
        yAxisMax: null,
        signals: [],
        ...overrides,
    };
}

function comparisonSignal(id: string, params: Record<string, unknown>): SignalConfig {
    return {
        id,
        signalType: 'asset-comparison',
        params,
        style: {
            color: '#2563eb',
            lineWidth: 2,
            lineType: 'solid',
            markerStart: null,
            markerEnd: null,
        },
    };
}

beforeEach(() => {
    backing = new Map();
    getItem = vi.fn((key: string) => backing.get(key) ?? null);
    setItem = vi.fn((key: string, value: string) => void backing.set(key, value));
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        writable: true,
        value: {
            getItem: (key: string) => getItem(key),
            setItem: (key: string, value: string) => setItem(key, value),
            removeItem: (key: string) => void backing.delete(key),
            clear: () => backing.clear(),
        },
    });
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    apiTransportCall.mockReset();
    vi.useFakeTimers();
});

afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
});

describe('chartSettingsStore — hydration', () => {
    it('reads the payload stored under the current account', () => {
        const user = `chart-settings-u${userSeq + 1}`;
        seed(user, {
            version: 2,
            globalSettings: settings({
                areaFill: false,
                axisScales: {
                    absolute: {mode: 'custom', min: -5, max: 42},
                    percentage: {mode: 'include0'},
                    secondary: {},
                },
            }),
            pairOverrides: [['EUR-USD', settings({gridLines: false})]],
        });
        expect(freshUser()).toBe(user);

        const global = getGlobalSettings();
        expect(global.areaFill).toBe(false);
        expect(global.axisScales.absolute).toEqual({mode: 'custom', min: -5, max: 42});
        expect(global.axisScales.percentage).toEqual({mode: 'include0'});
        expect(getSettingsForPair('EUR-USD').gridLines).toBe(false);
    });

    it('migrates each v1 legacy Y-axis setting into both primary axis modes', () => {
        const user = `chart-settings-u${userSeq + 1}`;
        seed(user, {
            version: 1,
            globalSettings: legacySettings({areaFill: false, yAxisMode: 'custom', yAxisMin: -5, yAxisMax: 42}),
            pairOverrides: [['EUR-USD', legacySettings({gridLines: false, yAxisMode: 'include0'})]],
        });
        expect(freshUser()).toBe(user);

        expect(getGlobalSettings().axisScales).toEqual({
            absolute: {mode: 'custom', min: -5, max: 42},
            percentage: {mode: 'custom', min: -5, max: 42},
            secondary: {},
        });
        expect(getSettingsForPair('EUR-USD').axisScales).toEqual({
            absolute: {mode: 'include0'},
            percentage: {mode: 'include0'},
            secondary: {},
        });
    });

    it('migrates and immediately rewrites a v1 runtime-bearing payload under only the active account key', () => {
        const user = `chart-settings-u${userSeq + 1}`;
        const untouchedUser = `chart-settings-u${userSeq + 2}`;
        const durableSignal = comparisonSignal('legacy-v1-comparison', {
            assetId: '77',
            _assetDisplayName: 'Durable comparison label',
            lookback: 63,
        });
        const storedSignal = {
            ...durableSignal,
            params: {
                ...durableSignal.params,
                _resolvedData: [{date: '2026-01-02', value: 14.5, source: 'legacy-runtime'}],
            },
        };
        seed(user, {
            version: 1,
            globalSettings: legacySettings({
                areaFill: false,
                yAxisMode: 'custom',
                yAxisMin: -5,
                yAxisMax: 42,
                signals: [storedSignal],
            }),
            pairOverrides: [
                ['__global_assets__', legacySettings({gridLines: false, yAxisMode: 'include0', signals: [storedSignal]})],
                ['asset-7', legacySettings({colorByBaseline: false, yAxisMode: 'custom', yAxisMin: 0, yAxisMax: 100, signals: [storedSignal]})],
            ],
        });
        seed(untouchedUser, {
            version: 2,
            globalSettings: settings({staleGradient: false}),
            pairOverrides: [],
        });
        const untouchedRaw = backing.get(storageKeyFor(untouchedUser));

        expect(freshUser()).toBe(user);
        expect(setItem).toHaveBeenCalledTimes(1);
        expect(setItem.mock.calls[0]?.[0]).toBe(storageKeyFor(user));

        const migratedGlobal = getGlobalSettings();
        expect(migratedGlobal).toMatchObject({
            areaFill: false,
            axisScales: {
                absolute: {mode: 'custom', min: -5, max: 42},
                percentage: {mode: 'custom', min: -5, max: 42},
                secondary: {},
            },
        });
        expect(migratedGlobal.signals).toEqual([durableSignal]);

        const migratedAssetScope = getGlobalSettings('assets');
        expect(migratedAssetScope).toMatchObject({
            gridLines: false,
            axisScales: {
                absolute: {mode: 'include0'},
                percentage: {mode: 'include0'},
                secondary: {},
            },
        });
        expect(migratedAssetScope.signals).toEqual([durableSignal]);

        const migratedAsset = getSettingsForPair('asset-7', 'assets');
        expect(migratedAsset).toMatchObject({
            colorByBaseline: false,
            axisScales: {
                absolute: {mode: 'custom', min: 0, max: 100},
                percentage: {mode: 'custom', min: 0, max: 100},
                secondary: {},
            },
        });
        expect(migratedAsset.signals).toEqual([durableSignal]);
        expect(getSettingsForPair('asset-unconfigured', 'assets').gridLines).toBe(false);

        const rewrittenRaw = backing.get(storageKeyFor(user));
        expect(rewrittenRaw).toBeDefined();
        expect(rewrittenRaw).not.toContain('"_resolvedData"');
        expect(rewrittenRaw).not.toContain('legacy-runtime');
        const rewritten = persistedFor(user);
        expect(rewritten?.version).toBe(2);
        expect(rewritten?.globalSettings.signals).toEqual([durableSignal]);
        const rewrittenOverrides = new Map(rewritten?.pairOverrides);
        expect(rewrittenOverrides.get('__global_assets__')?.signals).toEqual([durableSignal]);
        expect(rewrittenOverrides.get('asset-7')?.signals).toEqual([durableSignal]);
        expect(backing.get(storageKeyFor(untouchedUser))).toBe(untouchedRaw);
        expect(setItem).toHaveBeenCalledTimes(1);
        expect(setItem).toHaveBeenCalledWith(storageKeyFor(user), expect.any(String));

        // Hydration itself performs the rewrite; no later settings write or
        // debounce flush is needed to remove the legacy runtime cache.
        flushWrite();
        expect(setItem).toHaveBeenCalledTimes(1);
    });

    it('immediately scrubs runtime data from an otherwise-current v2 payload', () => {
        const user = `chart-settings-u${userSeq + 1}`;
        const durableSignal = comparisonSignal('legacy-v2-comparison', {
            assetId: '88',
            _assetDisplayName: 'Current-version comparison label',
            enabled: true,
        });
        const storedSignal = {
            ...durableSignal,
            params: {
                ...durableSignal.params,
                _resolvedData: [{date: '2026-02-03', value: 22.25, source: 'v2-runtime'}],
            },
        };
        seed(user, {
            version: 2,
            globalSettings: settings({signals: [storedSignal]}),
            pairOverrides: [['EUR-USD', settings({areaFill: false, signals: [storedSignal]})]],
        });

        expect(freshUser()).toBe(user);
        expect(setItem).toHaveBeenCalledTimes(1);
        expect(setItem.mock.calls[0]?.[0]).toBe(storageKeyFor(user));

        expect(getGlobalSettings().signals).toEqual([durableSignal]);
        const hydratedPair = getSettingsForPair('EUR-USD', 'fx');
        expect(hydratedPair.areaFill).toBe(false);
        expect(hydratedPair.signals).toEqual([durableSignal]);
        const rewrittenRaw = backing.get(storageKeyFor(user));
        expect(rewrittenRaw).toBeDefined();
        expect(rewrittenRaw).not.toContain('"_resolvedData"');
        expect(rewrittenRaw).not.toContain('v2-runtime');
        const rewritten = persistedFor(user);
        expect(rewritten?.version).toBe(2);
        expect(rewritten?.globalSettings.signals).toEqual([durableSignal]);
        expect(new Map(rewritten?.pairOverrides).get('EUR-USD')?.signals).toEqual([durableSignal]);
        expect(setItem).toHaveBeenCalledTimes(1);
        expect(setItem).toHaveBeenCalledWith(storageKeyFor(user), expect.any(String));

        flushWrite();
        expect(setItem).toHaveBeenCalledTimes(1);
    });

    it('keeps one account out of another account\u2019s settings', () => {
        const first = `chart-settings-u${userSeq + 1}`;
        seed(first, {version: 2, globalSettings: settings({colorByBaseline: false}), pairOverrides: [['EUR-USD', settings({areaFill: false})]]});
        freshUser();
        expect(getGlobalSettings().colorByBaseline).toBe(false);

        // A second account has nothing stored: it must see the shipped defaults,
        // not what the previous account left in module state.
        freshUser();
        expect(getGlobalSettings().colorByBaseline).toBe(true);
        expect(getSettingsForPair('EUR-USD').areaFill).toBe(true);
    });

    it('returns to a previous account\u2019s stored settings when it becomes current again', () => {
        const first = freshUser();
        setPairSettings('EUR-USD', settings({gridLines: false}));
        flushWrite();

        freshUser();
        expect(getSettingsForPair('EUR-USD').gridLines).toBe(true);

        transitionClientSession(first);
        expect(getSettingsForPair('EUR-USD').gridLines).toBe(false);
    });

    it('falls back to defaults for a payload written by another storage version', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 3, globalSettings: settings({areaFill: false}), pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().areaFill).toBe(true);
    });

    it('falls back to defaults for unreadable or wrongly shaped payloads', () => {
        seed(`chart-settings-u${userSeq + 1}`, '{not json');
        freshUser();
        expect(getGlobalSettings().areaFill).toBe(true);

        // Valid JSON, but an array is not a settings record.
        seed(`chart-settings-u${userSeq + 1}`, '[{"version":1}]');
        freshUser();
        expect(getGlobalSettings().areaFill).toBe(true);
    });

    it('survives a browser that refuses to read storage at all', () => {
        // Safari private browsing throws on access rather than returning null.
        getItem.mockImplementation(() => {
            throw new DOMException('SecurityError');
        });
        freshUser();

        expect(getGlobalSettings()).toMatchObject({
            colorByBaseline: true,
            areaFill: true,
            gridLines: true,
            staleGradient: true,
            axisScales: {
                absolute: {mode: 'auto'},
                percentage: {mode: 'include0'},
                secondary: {},
            },
            signals: [],
        });
    });

    it('reads storage once per account instead of on every call', () => {
        freshUser();
        getItem.mockClear();

        getGlobalSettings();
        getGlobalSettings('assets');
        getSettingsForPair('EUR-USD');

        expect(getItem).not.toHaveBeenCalled();
    });
});

describe('chartSettingsStore — sanitising a stored payload', () => {
    it('replaces every non-boolean flag with its shipped default', () => {
        seed(`chart-settings-u${userSeq + 1}`, {
            version: 2,
            globalSettings: {colorByBaseline: 'yes', areaFill: 1, gridLines: null, staleGradient: undefined, signals: []},
            pairOverrides: [],
        });
        freshUser();

        expect(getGlobalSettings()).toMatchObject({colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true});
    });

    it('keeps a stored false rather than treating it as missing', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 2, globalSettings: {colorByBaseline: false, areaFill: false, gridLines: false, staleGradient: false, signals: []}, pairOverrides: []});
        freshUser();

        expect(getGlobalSettings()).toMatchObject({colorByBaseline: false, areaFill: false, gridLines: false, staleGradient: false});
    });

    it('accepts only the two named legacy Y-axis modes and defaults the rest to auto', () => {
        const modes: Array<[unknown, string]> = [
            ['include0', 'include0'],
            ['custom', 'custom'],
            ['logarithmic', 'auto'],
            [null, 'auto'],
            [undefined, 'auto'],
        ];

        for (const [stored, expected] of modes) {
            seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: legacySettings({yAxisMode: stored}), pairOverrides: []});
            freshUser();
            expect(getGlobalSettings().axisScales.absolute.mode).toBe(expected);
            expect(getGlobalSettings().axisScales.percentage.mode).toBe(expected);
        }
    });

    it('drops legacy Y-axis bounds that are not finite numbers', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: legacySettings({yAxisMode: 'custom', yAxisMin: '12', yAxisMax: null}), pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().axisScales.absolute).toEqual({mode: 'custom'});
        expect(getGlobalSettings().axisScales.percentage).toEqual({mode: 'custom'});
    });

    it('keeps a zero legacy bound, which is falsy but perfectly valid', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: legacySettings({yAxisMode: 'custom', yAxisMin: 0, yAxisMax: 0}), pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().axisScales.absolute).toEqual({mode: 'custom', min: 0, max: 0});
        expect(getGlobalSettings().axisScales.percentage).toEqual({mode: 'custom', min: 0, max: 0});
    });

    it('sanitises semantic secondary-axis entries without one malformed entry poisoning its neighbours', () => {
        seed(`chart-settings-u${userSeq + 1}`, {
            version: 2,
            globalSettings: {
                ...settings(),
                axisScales: {
                    absolute: {mode: 'auto'},
                    percentage: {mode: 'include0'},
                    secondary: {
                        'independent:rsi': {mode: 'custom', min: 100, max: 0},
                        'volume:turnover': {mode: 'include0', min: -20, max: 80},
                        'independent:malformed': 'not-an-axis-setting',
                        '   ': {mode: 'custom', min: 1, max: 2},
                    },
                },
            },
            pairOverrides: [],
        });
        freshUser();

        expect(getGlobalSettings().axisScales.secondary).toEqual({
            'independent:rsi': {mode: 'custom', min: 0, max: 100},
            'volume:turnover': {mode: 'include0'},
            'independent:malformed': {mode: 'auto'},
        });
    });

    it('replaces a non-array signal list with an empty one', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 2, globalSettings: {...DEFAULT_CHART_SETTINGS, signals: {id: 'not-a-list'}}, pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().signals).toEqual([]);
    });

    it('carries a stored signal list through untouched', () => {
        const signal = {id: 'ema-1', signalType: 'ema', params: {period: 20}, style: {color: '#3b82f6', lineWidth: 1, lineType: 'dotted', markerStart: null, markerEnd: null}};
        seed(`chart-settings-u${userSeq + 1}`, {version: 2, globalSettings: {...DEFAULT_CHART_SETTINGS, signals: [signal]}, pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().signals).toEqual([signal]);
    });

    it('replaces a globalSettings that is not a record with the full defaults', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 2, globalSettings: 'corrupted', pairOverrides: []});
        freshUser();

        expect(getGlobalSettings()).toEqual(DEFAULT_CHART_SETTINGS);
    });

    it('skips malformed override entries and keeps the well-formed ones', () => {
        seed(`chart-settings-u${userSeq + 1}`, {
            version: 2,
            globalSettings: settings(),
            pairOverrides: [
                'EUR-USD', // not a tuple
                ['GBP-USD'], // wrong arity
                [7, settings({areaFill: false})], // non-string key
                ['USD-JPY', settings({areaFill: false})], // the only good one
            ],
        });
        freshUser();

        expect(getSettingsForPair('USD-JPY').areaFill).toBe(false);
        expect(getSettingsForPair('GBP-USD').areaFill).toBe(true);
        expect(getSettingsForPair('EUR-USD').areaFill).toBe(true);
    });

    it('ignores a pairOverrides field that is not a list', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 2, globalSettings: settings({gridLines: false}), pairOverrides: {'EUR-USD': settings()}});
        freshUser();

        expect(getGlobalSettings().gridLines).toBe(false);
        expect(getSettingsForPair('EUR-USD').gridLines).toBe(false);
    });
});

describe('chartSettingsStore — read fallbacks', () => {
    it('defaults a fresh percentage axis to Include0 while the absolute axis stays Auto', () => {
        freshUser();

        expect(getGlobalSettings().axisScales).toEqual({
            absolute: {mode: 'auto'},
            percentage: {mode: 'include0'},
            secondary: {},
        });
        expect(getSettingsForPair('asset-unconfigured', 'assets').axisScales.percentage).toEqual({mode: 'include0'});
    });

    it('prefers the pair override, then the scoped global, then the base global', () => {
        freshUser();
        setGlobalSettings(settings({areaFill: false, gridLines: false, staleGradient: false}));
        setGlobalSettings(settings({areaFill: true, gridLines: false, staleGradient: false}), 'assets');
        setPairSettings('asset-7', settings({areaFill: true, gridLines: true, staleGradient: false}));

        expect(getSettingsForPair('asset-7', 'assets').gridLines).toBe(true);
        expect(getSettingsForPair('asset-9', 'assets')).toMatchObject({areaFill: true, gridLines: false});
        expect(getSettingsForPair('asset-9')).toMatchObject({areaFill: false, gridLines: false});
    });

    it('isolates axis settings across accounts, base globals, scoped globals, and pairs', () => {
        const firstUser = freshUser();
        setGlobalSettings(
            settings({
                axisScales: {
                    absolute: {mode: 'custom', min: 10, max: 20},
                    percentage: {mode: 'include0'},
                    secondary: {},
                },
            }),
        );
        setGlobalSettings(
            settings({
                axisScales: {
                    absolute: {mode: 'auto'},
                    percentage: {mode: 'custom', min: -5, max: 5},
                    secondary: {},
                },
            }),
            'assets',
        );
        setPairSettings(
            'asset-7',
            settings({
                axisScales: {
                    absolute: {mode: 'include0'},
                    percentage: {mode: 'auto'},
                    secondary: {'independent:rsi': {mode: 'custom', min: 20, max: 80}},
                },
            }),
        );
        flushWrite();

        expect(getGlobalSettings().axisScales.absolute).toEqual({mode: 'custom', min: 10, max: 20});
        expect(getGlobalSettings('assets').axisScales.percentage).toEqual({mode: 'custom', min: -5, max: 5});
        expect(getSettingsForPair('asset-7', 'assets').axisScales.secondary).toEqual({'independent:rsi': {mode: 'custom', min: 20, max: 80}});
        expect(getSettingsForPair('asset-9', 'assets').axisScales.percentage).toEqual({mode: 'custom', min: -5, max: 5});
        expect(getSettingsForPair('EUR-USD', 'fx').axisScales.absolute).toEqual({mode: 'custom', min: 10, max: 20});

        const secondUser = freshUser();
        expect(getGlobalSettings().axisScales).toEqual(DEFAULT_CHART_SETTINGS.axisScales);
        expect(getSettingsForPair('asset-7', 'assets').axisScales).toEqual(DEFAULT_CHART_SETTINGS.axisScales);

        transitionClientSession(firstUser);
        expect(getSettingsForPair('asset-7', 'assets').axisScales.secondary).toEqual({'independent:rsi': {mode: 'custom', min: 20, max: 80}});
        expect(new Set(setItem.mock.calls.map(([key]) => key))).toEqual(new Set([storageKeyFor(firstUser)]));
        expect(backing.has(storageKeyFor(secondUser))).toBe(false);
        expect(fetchMock).not.toHaveBeenCalled();
        expect(apiTransportCall).not.toHaveBeenCalled();
    });

    it('serves the base global when the requested scope has no override', () => {
        freshUser();
        setGlobalSettings(settings({staleGradient: false}));

        expect(getGlobalSettings('fx').staleGradient).toBe(false);
        expect(getGlobalSettings().staleGradient).toBe(false);
    });

    it('serves the scoped global once the scope has one', () => {
        freshUser();
        setGlobalSettings(settings({staleGradient: false}));
        setGlobalSettings(settings({staleGradient: true}), 'fx');

        expect(getGlobalSettings('fx').staleGradient).toBe(true);
        expect(getGlobalSettings('assets').staleGradient).toBe(false);
        expect(getGlobalSettings().staleGradient).toBe(false);
    });

    it('hands out copies, so a caller cannot edit the store by accident', () => {
        freshUser();
        setPairSettings('EUR-USD', settings({signals: [{id: 's1', signalType: 'ema', params: {}, style: {color: '#3b82f6', lineWidth: 1, lineType: 'solid', markerStart: null, markerEnd: null}}]}));

        const copy = getSettingsForPair('EUR-USD');
        copy.gridLines = false;
        const copiedSignal = copy.signals.find((signal) => signal.id === 's1');
        expect(copiedSignal).toBeDefined();
        copiedSignal!.params.period = 99;

        expect(getSettingsForPair('EUR-USD').gridLines).toBe(true);
        expect(getSettingsForPair('EUR-USD').signals.find((signal) => signal.id === 's1')?.params).toEqual({});
    });

    it('does not alias the object handed in to setPairSettings', () => {
        freshUser();
        const mutable = settings({gridLines: true});
        setPairSettings('EUR-USD', mutable);
        mutable.gridLines = false;

        expect(getSettingsForPair('EUR-USD').gridLines).toBe(true);
    });
});

describe('chartSettingsStore — scope rules on save', () => {
    it('clears only the asset overrides when the assets scope is saved', () => {
        freshUser();
        // The fx scoped global is written first on purpose: saving a scope also
        // clears that scope's per-item overrides, so seeding it afterwards would
        // wipe the EUR-USD row this test is about to check survived.
        setGlobalSettings(settings({areaFill: false}), 'fx');
        setPairSettings('asset-7', settings({gridLines: false}));
        setPairSettings('EUR-USD', settings({gridLines: false}));

        setGlobalSettings(settings({staleGradient: false}), 'assets');

        expect(getSettingsForPair('asset-7', 'assets').gridLines).toBe(true);
        expect(getSettingsForPair('EUR-USD', 'fx').gridLines).toBe(false);
        expect(getGlobalSettings('fx').areaFill).toBe(false);
        expect(getGlobalSettings('assets').staleGradient).toBe(false);
    });

    it('clears only the pair overrides when the fx scope is saved', () => {
        freshUser();
        setGlobalSettings(settings({areaFill: false}), 'assets');
        setPairSettings('asset-7', settings({gridLines: false}));
        setPairSettings('EUR-USD', settings({gridLines: false}));

        setGlobalSettings(settings({staleGradient: false}), 'fx');

        expect(getSettingsForPair('EUR-USD', 'fx').gridLines).toBe(true);
        expect(getSettingsForPair('asset-7', 'assets').gridLines).toBe(false);
        expect(getGlobalSettings('assets').areaFill).toBe(false);
    });

    it('leaves the base global untouched when a scope is saved', () => {
        freshUser();
        setGlobalSettings(settings({colorByBaseline: false}));
        setGlobalSettings(settings({colorByBaseline: true}), 'assets');

        expect(getGlobalSettings().colorByBaseline).toBe(false);
    });

    it('wipes every override, scoped globals included, when saving without a scope', () => {
        freshUser();
        setPairSettings('asset-7', settings({gridLines: false}));
        setPairSettings('EUR-USD', settings({gridLines: false}));
        setGlobalSettings(settings({areaFill: false}), 'assets');
        setGlobalSettings(settings({areaFill: false}), 'fx');

        setGlobalSettings(settings({staleGradient: false}));

        expect(getSettingsForPair('asset-7', 'assets')).toMatchObject({gridLines: true, areaFill: true, staleGradient: false});
        expect(getSettingsForPair('EUR-USD', 'fx')).toMatchObject({gridLines: true, areaFill: true, staleGradient: false});
        expect(getGlobalSettings('assets').areaFill).toBe(true);
    });

    it('protects the reserved double-underscore namespace from scope clearing', () => {
        freshUser();
        setPairSettings('__scratch__', settings({gridLines: false}));
        setGlobalSettings(settings(), 'fx');

        expect(getSettingsForPair('__scratch__').gridLines).toBe(false);
    });

    it('advances the reactive version on every write', () => {
        freshUser();
        const start = getSettingsVersion();

        setPairSettings('EUR-USD', settings());
        const afterPair = getSettingsVersion();
        setGlobalSettings(settings(), 'fx');
        const afterScoped = getSettingsVersion();
        setGlobalSettings(settings());

        expect(afterPair).toBeGreaterThan(start);
        expect(afterScoped).toBeGreaterThan(afterPair);
        expect(getSettingsVersion()).toBeGreaterThan(afterScoped);
    });
});

describe('chartSettingsStore — persistence', () => {
    it('defers the write and collapses a burst into a single one', () => {
        const user = freshUser();
        setItem.mockClear();

        setPairSettings('EUR-USD', settings({gridLines: false}));
        setPairSettings('EUR-USD', settings({gridLines: true}));
        setPairSettings('EUR-USD', settings({areaFill: false}));
        expect(setItem).not.toHaveBeenCalled();

        flushWrite();
        expect(setItem).toHaveBeenCalledTimes(1);
        expect(persistedFor(user)?.pairOverrides).toEqual([['EUR-USD', expect.objectContaining({areaFill: false, gridLines: true})]]);
    });

    it('writes the version and both levels under the account key', () => {
        const user = freshUser();
        setGlobalSettings(settings({colorByBaseline: false}));
        setPairSettings('asset-7', settings({areaFill: false}));
        setGlobalSettings(settings({gridLines: false}), 'assets');
        flushWrite();

        const payload = persistedFor(user);
        expect(payload?.version).toBe(2);
        expect(payload?.globalSettings).toMatchObject({colorByBaseline: false});
        expect(Object.fromEntries(payload!.pairOverrides)).toMatchObject({
            __global_assets__: expect.objectContaining({gridLines: false}),
        });
        expect(setItem).toHaveBeenCalledWith(storageKeyFor(user), expect.any(String));
    });

    it('scrubs comparison runtime data from storage without mutating live pair settings', () => {
        const user = freshUser();
        const persistentParams = {
            assetId: '77',
            _assetDisplayName: 'Persistence Asset',
            lookback: 63,
            enabled: true,
            nested: {
                thresholds: [0.1, 0.25, 0.5],
                presentation: {
                    mode: 'relative',
                    labels: ['short', 'medium', 'long'],
                },
                windows: [
                    {kind: 'rolling', amount: 12},
                    {kind: 'calendar', amount: 3},
                ],
            },
        };
        const runtimePayloadMarker = 'runtime-only-resolved-cache';
        const largeResolvedData = Array.from({length: 256}, (_, index) => ({
            date: `resolved-${index}`,
            value: index / 10,
            diagnostics: {
                samples: Array.from({length: 6}, (_, sample) => ({
                    sample,
                    value: index + sample / 10,
                })),
                source: {
                    provider: runtimePayloadMarker,
                    path: ['asset', index, 'close'],
                },
            },
            metadata: {
                asset: {id: 77, symbol: 'PERSIST'},
                requestedRange: {start: '2020-01-01', end: '2026-01-01'},
                aggregations: {
                    daily: {count: 2_192, complete: true},
                    monthly: {count: 72, complete: true},
                },
            },
        }));
        const transientSignal: SignalConfig = {
            id: 'persistence-sanitizer',
            signalType: 'asset-comparison',
            params: {
                ...persistentParams,
                _resolvedData: largeResolvedData,
            },
            style: {
                color: '#123456',
                lineWidth: 4,
                lineType: 'dashed',
                markerStart: 'diamond',
                markerEnd: 'pin',
            },
            componentStyles: {
                return: {
                    color: '#abcdef',
                    lineWidth: 3,
                    lineType: 'dotted',
                    markerStart: 'circle',
                    markerEnd: null,
                },
                baseline: {
                    color: '#fedcba',
                    lineWidth: 2,
                    lineType: 'solid',
                    markerStart: null,
                    markerEnd: 'arrow',
                },
            },
            partitionStyles: {
                positive: {
                    color: '#16a34a',
                    lineWidth: 2,
                    lineType: 'solid',
                    markerStart: null,
                    markerEnd: null,
                },
                negative: {
                    color: '#dc2626',
                    lineWidth: 1,
                    lineType: 'dashed',
                    markerStart: 'rect',
                    markerEnd: null,
                },
            },
        };
        const updatedPercentageAxis = {
            mode: 'custom',
            min: -25,
            max: 75,
        } satisfies ChartSettings['axisScales']['percentage'];
        const updatedComparisonStyle: SignalConfig['style'] = {
            ...transientSignal.style,
            color: '#654321',
            lineWidth: 5,
        };
        const expectedStoredSignal: SignalConfig = {
            ...transientSignal,
            params: persistentParams,
        };
        const expectedEditedStoredSignal: SignalConfig = {
            ...expectedStoredSignal,
            style: updatedComparisonStyle,
        };

        setPairSettings('EUR-USD', settings({signals: [transientSignal]}));
        setGlobalSettings(settings({signals: [transientSignal]}), 'assets');

        // Reproduce an unrelated settings-modal save after comparison data was
        // resolved: axis/chart style changes must not evict the live series.
        const editedPair = getSettingsForPair('EUR-USD', 'fx');
        editedPair.axisScales.percentage = updatedPercentageAxis;
        editedPair.areaFill = false;
        editedPair.signals = editedPair.signals.map((signal) =>
            signal.id === transientSignal.id
                ? {
                      ...signal,
                      style: updatedComparisonStyle,
                  }
                : signal,
        );
        setPairSettings('EUR-USD', editedPair);
        flushWrite();

        const livePair = getSettingsForPair('EUR-USD', 'fx');
        const liveComparison = livePair.signals.find((signal) => signal.id === transientSignal.id);
        expect(livePair.axisScales.percentage).toEqual(updatedPercentageAxis);
        expect(livePair.areaFill).toBe(false);
        expect(liveComparison).toBeDefined();
        expect(liveComparison?.style).toEqual(updatedComparisonStyle);
        expect(liveComparison?.params._resolvedData).toEqual(largeResolvedData);

        const liveAssetScope = getSettingsForPair('asset-unconfigured', 'assets');
        const scopedComparison = liveAssetScope.signals.find((signal) => signal.id === transientSignal.id);
        expect(scopedComparison?.params._resolvedData).toEqual(largeResolvedData);
        expect(getSettingsForPair('GBP-USD', 'fx').signals).toEqual([]);

        const raw = backing.get(storageKeyFor(user));
        expect(raw).toBeDefined();
        expect(raw).not.toContain('"_resolvedData"');
        expect(raw).not.toContain(runtimePayloadMarker);
        expect(raw).toContain('"_assetDisplayName"');

        const payload = persistedFor(user);
        expect(payload).not.toBeNull();
        const persistedOverrides = new Map(payload!.pairOverrides);
        const persistedPair = persistedOverrides.get('EUR-USD');
        expect(persistedPair?.axisScales.percentage).toEqual(updatedPercentageAxis);
        expect(persistedPair?.areaFill).toBe(false);
        expect(persistedPair?.signals).toEqual([expectedEditedStoredSignal]);
        expect(persistedOverrides.get('__global_assets__')?.signals).toEqual([expectedStoredSignal]);
        expect(payload!.globalSettings.signals).toEqual([]);

        const otherUser = freshUser();
        expect(backing.has(storageKeyFor(otherUser))).toBe(false);
        expect(getSettingsForPair('EUR-USD', 'fx').signals).toEqual([]);
        expect(getSettingsForPair('asset-unconfigured', 'assets').signals).toEqual([]);
        expect(new Set(setItem.mock.calls.map(([key]) => key))).toEqual(new Set([storageKeyFor(user)]));

        // Returning to the first account re-hydrates the deliberately scrubbed
        // payload; only that boundary removes the transient comparison series.
        transitionClientSession(user);
        expect(getSettingsForPair('EUR-USD', 'fx')).toMatchObject({
            areaFill: false,
            axisScales: {percentage: updatedPercentageAxis},
            signals: [expectedEditedStoredSignal],
        });
        expect(getSettingsForPair('asset-unconfigured', 'assets').signals).toEqual([expectedStoredSignal]);
        expect(getSettingsForPair('GBP-USD', 'fx').signals).toEqual([]);
        expect(fetchMock).not.toHaveBeenCalled();
        expect(apiTransportCall).not.toHaveBeenCalled();
    });

    it('persists Calendar Return windows independently per account and asset without backend calls', () => {
        const firstUser = freshUser();
        setPairSettings(
            'asset-7',
            settings({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 2,
                    customUnit: 'months',
                },
            }),
        );
        setPairSettings(
            'asset-8',
            settings({
                calendarReturnWindow: {
                    kind: 'preset',
                    preset: '1y',
                    customAmount: 3,
                    customUnit: 'years',
                },
            }),
        );
        flushWrite();

        expect(getGlobalSettings('assets').calendarReturnWindow).toEqual(DEFAULT_CHART_SETTINGS.calendarReturnWindow);

        const secondUser = freshUser();
        setPairSettings(
            'asset-7',
            settings({
                calendarReturnWindow: {
                    kind: 'preset',
                    preset: '1w',
                    customAmount: 3,
                    customUnit: 'years',
                },
            }),
        );
        flushWrite();

        expect(getSettingsForPair('asset-7', 'assets').calendarReturnWindow).toEqual({
            kind: 'preset',
            preset: '1w',
            customAmount: 3,
            customUnit: 'years',
        });
        expect(getSettingsForPair('asset-8', 'assets').calendarReturnWindow).toEqual(DEFAULT_CHART_SETTINGS.calendarReturnWindow);

        transitionClientSession(firstUser);
        expect(getSettingsForPair('asset-7', 'assets').calendarReturnWindow).toEqual({
            kind: 'custom',
            preset: '1m',
            customAmount: 2,
            customUnit: 'months',
        });
        expect(getSettingsForPair('asset-8', 'assets').calendarReturnWindow).toEqual({
            kind: 'preset',
            preset: '1y',
            customAmount: 3,
            customUnit: 'years',
        });

        transitionClientSession(secondUser);
        expect(getSettingsForPair('asset-7', 'assets').calendarReturnWindow.preset).toBe('1w');
        expect(new Set(setItem.mock.calls.map(([key]) => key))).toEqual(new Set([storageKeyFor(firstUser), storageKeyFor(secondUser)]));
        expect(fetchMock).not.toHaveBeenCalled();
        expect(apiTransportCall).not.toHaveBeenCalled();
    });

    it('keeps working in memory when the browser refuses the write', () => {
        freshUser();
        setItem.mockImplementation(() => {
            throw new DOMException('QuotaExceededError');
        });

        setPairSettings('EUR-USD', settings({gridLines: false}));
        expect(() => flushWrite()).not.toThrow();
        expect(getSettingsForPair('EUR-USD').gridLines).toBe(false);
    });

    it('does not write anything when nothing was changed', () => {
        freshUser();
        setItem.mockClear();

        getGlobalSettings();
        getSettingsForPair('EUR-USD');
        flushWrite();

        expect(setItem).not.toHaveBeenCalled();
    });
});
