import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

// The shared `$app/environment` mock reports `browser: false`, which makes every
// storage path in this store a no-op. Nothing below would run against it.
vi.mock('$app/environment', () => ({browser: true}));

import {transitionClientSession} from '$lib/stores/app/clientSession';

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
    return {...DEFAULT_CHART_SETTINGS, ...overrides};
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
    vi.useFakeTimers();
});

afterEach(() => {
    vi.useRealTimers();
});

describe('chartSettingsStore — hydration', () => {
    it('reads the payload stored under the current account', () => {
        const user = `chart-settings-u${userSeq + 1}`;
        seed(user, {
            version: 1,
            globalSettings: settings({areaFill: false, yAxisMode: 'custom', yAxisMin: -5, yAxisMax: 42}),
            pairOverrides: [['EUR-USD', settings({gridLines: false})]],
        });
        expect(freshUser()).toBe(user);

        const global = getGlobalSettings();
        expect(global.areaFill).toBe(false);
        expect(global.yAxisMode).toBe('custom');
        expect(global.yAxisMin).toBe(-5);
        expect(global.yAxisMax).toBe(42);
        expect(getSettingsForPair('EUR-USD').gridLines).toBe(false);
    });

    it('keeps one account out of another account\u2019s settings', () => {
        const first = `chart-settings-u${userSeq + 1}`;
        seed(first, {version: 1, globalSettings: settings({colorByBaseline: false}), pairOverrides: [['EUR-USD', settings({areaFill: false})]]});
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
        seed(`chart-settings-u${userSeq + 1}`, {version: 2, globalSettings: settings({areaFill: false}), pairOverrides: []});
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

        expect(getGlobalSettings()).toMatchObject({colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, yAxisMode: 'auto', signals: []});
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
            version: 1,
            globalSettings: {colorByBaseline: 'yes', areaFill: 1, gridLines: null, staleGradient: undefined, signals: []},
            pairOverrides: [],
        });
        freshUser();

        expect(getGlobalSettings()).toMatchObject({colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true});
    });

    it('keeps a stored false rather than treating it as missing', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: {colorByBaseline: false, areaFill: false, gridLines: false, staleGradient: false, signals: []}, pairOverrides: []});
        freshUser();

        expect(getGlobalSettings()).toMatchObject({colorByBaseline: false, areaFill: false, gridLines: false, staleGradient: false});
    });

    it('accepts only the two named y-axis modes and defaults the rest to auto', () => {
        const modes: Array<[unknown, string]> = [
            ['include0', 'include0'],
            ['custom', 'custom'],
            ['logarithmic', 'auto'],
            [null, 'auto'],
            [undefined, 'auto'],
        ];

        for (const [stored, expected] of modes) {
            seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: {...DEFAULT_CHART_SETTINGS, yAxisMode: stored}, pairOverrides: []});
            freshUser();
            expect(getGlobalSettings().yAxisMode).toBe(expected);
        }
    });

    it('drops y-axis bounds that are not finite numbers', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: {...DEFAULT_CHART_SETTINGS, yAxisMode: 'custom', yAxisMin: '12', yAxisMax: null}, pairOverrides: []});
        freshUser();

        const global = getGlobalSettings();
        expect(global.yAxisMode).toBe('custom');
        expect(global.yAxisMin).toBeUndefined();
        expect(global.yAxisMax).toBeUndefined();
    });

    it('keeps a zero bound, which is falsy but perfectly valid', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: {...DEFAULT_CHART_SETTINGS, yAxisMode: 'custom', yAxisMin: 0, yAxisMax: 0}, pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().yAxisMin).toBe(0);
        expect(getGlobalSettings().yAxisMax).toBe(0);
    });

    it('replaces a non-array signal list with an empty one', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: {...DEFAULT_CHART_SETTINGS, signals: {id: 'not-a-list'}}, pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().signals).toEqual([]);
    });

    it('carries a stored signal list through untouched', () => {
        const signal = {id: 'ema-1', signalType: 'ema', params: {period: 20}, style: {color: '#3b82f6', lineWidth: 1, lineType: 'dotted', markerStart: null, markerEnd: null}};
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: {...DEFAULT_CHART_SETTINGS, signals: [signal]}, pairOverrides: []});
        freshUser();

        expect(getGlobalSettings().signals).toEqual([signal]);
    });

    it('replaces a globalSettings that is not a record with the full defaults', () => {
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: 'corrupted', pairOverrides: []});
        freshUser();

        expect(getGlobalSettings()).toMatchObject({colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, yAxisMode: 'auto', signals: []});
    });

    it('skips malformed override entries and keeps the well-formed ones', () => {
        seed(`chart-settings-u${userSeq + 1}`, {
            version: 1,
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
        seed(`chart-settings-u${userSeq + 1}`, {version: 1, globalSettings: settings({gridLines: false}), pairOverrides: {'EUR-USD': settings()}});
        freshUser();

        expect(getGlobalSettings().gridLines).toBe(false);
        expect(getSettingsForPair('EUR-USD').gridLines).toBe(false);
    });
});

describe('chartSettingsStore — read fallbacks', () => {
    it('prefers the pair override, then the scoped global, then the base global', () => {
        freshUser();
        setGlobalSettings(settings({areaFill: false, gridLines: false, staleGradient: false}));
        setGlobalSettings(settings({areaFill: true, gridLines: false, staleGradient: false}), 'assets');
        setPairSettings('asset-7', settings({areaFill: true, gridLines: true, staleGradient: false}));

        expect(getSettingsForPair('asset-7', 'assets').gridLines).toBe(true);
        expect(getSettingsForPair('asset-9', 'assets')).toMatchObject({areaFill: true, gridLines: false});
        expect(getSettingsForPair('asset-9')).toMatchObject({areaFill: false, gridLines: false});
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
        copy.signals[0].params.period = 99;

        expect(getSettingsForPair('EUR-USD').gridLines).toBe(true);
        expect(getSettingsForPair('EUR-USD').signals[0].params).toEqual({});
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
        expect(payload?.version).toBe(1);
        expect(payload?.globalSettings).toMatchObject({colorByBaseline: false});
        expect(Object.fromEntries(payload!.pairOverrides)).toMatchObject({
            __global_assets__: expect.objectContaining({gridLines: false}),
        });
        expect(setItem.mock.calls[0][0]).toBe(storageKeyFor(user));
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
