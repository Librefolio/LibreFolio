import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

// Same overrides as chartSettingsStore.test.ts, for the same reasons: the shared `$app/environment` mock reports
// `browser: false`, which makes every storage path of the store a no-op, and no test here may reach the API.
vi.mock('$app/environment', () => ({browser: true}));
const apiTransportCall = vi.hoisted(() => vi.fn());
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => apiTransportCall}),
    axiosInstance: new Proxy({}, {get: () => apiTransportCall}),
}));

import type {SignalConfig, SignalStyle} from '$lib/charts/signals';
import {signalCodeToType} from '$lib/charts/signals/catalogMapper';
import {transitionClientSession} from '$lib/stores/app/clientSession';

import * as chartSettingsStore from './chartSettingsStore.svelte';
import {DEFAULT_CHART_SETTINGS, getGlobalSettings, getSettingsForPair, type AxisScaleSettings, type ChartSettings} from './chartSettingsStore.svelte';

/**
 * Chart settings store — storage version 3 (workstream J, CP-10a; developer's decision 29: ONE Rolling Return,
 * measured in calendar days).
 *
 * The backend removes RISK_ROLLING_RETURN (compounded returns over N observations: param `window`, output
 * `rolling_return`) and publishes ASSET_CALENDAR_ROLLING_RETURN (the price return over N calendar days: param
 * `window_days`, output `calendar_return`). A chart that saved the removed signal must not lose it. The stored
 * settings move from version 2 (and 1) to version 3, and on the way every saved `risk-rolling-return` config, in
 * `globalSettings.signals` and in every `pairOverrides` entry, becomes an `asset-calendar-rolling-return` one: the
 * same number in `params.window_days`, the style of its output carried from `componentStyles.rolling_return` to
 * `componentStyles.calendar_return`. Every other field and every other signal stay as they were.
 *
 * The scale the user set on the removed signal's own secondary axis follows it. A secondary-axis scale is saved
 * under `${axisRole}:${axisKey}` (`secondaryAxisSettingsKey`, chartCoreHelpers.ts): the removed signal drew on the
 * independent `risk_return` axis, the calendar return draws on the independent `calendar_return` one (that half is
 * pinned through the renderer in backendRenderer.test.ts). So `axisScales.secondary['independent:risk_return']`
 * always goes, and its scale lands on `'independent:calendar_return'` unless the calendar return already has a
 * scale of its own there, which wins.
 *
 * Two seams. The migration itself is a pure function, `migratePersistedChartSettings(parsed: unknown)`, read
 * through the module namespace so that this file compiles before CP-10a exports it: until then each case is red on
 * its first assertion. Hydration is the wiring: a payload stored by an earlier version reads back migrated and is
 * rewritten as version 3 at once.
 */

const STORAGE_SUFFIX = 'chartSettingsStore';
const REMOVED_SIGNAL_TYPE = 'risk-rolling-return';
const CALENDAR_SIGNAL_TYPE = 'asset-calendar-rolling-return';
const REMOVED_AXIS_KEY = 'independent:risk_return';
const CALENDAR_AXIS_KEY = 'independent:calendar_return';
const RSI_AXIS_KEY = 'independent:rsi';

interface StoredDocument {
    version: number;
    globalSettings: unknown;
    pairOverrides: Array<[string, unknown]>;
}

type Migrate = (parsed: unknown) => unknown;

function migrate(parsed: unknown): unknown {
    const candidate: unknown = Reflect.get(chartSettingsStore, 'migratePersistedChartSettings');
    expect(candidate, 'chartSettingsStore.svelte.ts must export migratePersistedChartSettings(parsed: unknown)').toBeTypeOf('function');
    return (candidate as Migrate)(parsed);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Fixtures — fresh objects on every call, so no case can see another's mutation
// ═══════════════════════════════════════════════════════════════════════════════

function style(color: string, overrides: Partial<SignalStyle> = {}): SignalStyle {
    return {color, lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null, ...overrides};
}

/** A saved config of the removed signal whose output the user restyled: `componentStyles` is keyed by output. */
function removedStyled(id: string, window: number): SignalConfig {
    return {
        id,
        signalType: REMOVED_SIGNAL_TYPE,
        params: {window},
        style: style('#16a34a', {lineType: 'dashed', markerEnd: 'arrow'}),
        componentStyles: {rolling_return: style('#dc2626', {lineWidth: 3, lineType: 'dotted', markerStart: 'circle'})},
    };
}

/** `removedStyled` once migrated: the type, the param key and the output key change, nothing else does. */
function calendarStyled(id: string, windowDays: number): SignalConfig {
    return {
        id,
        signalType: CALENDAR_SIGNAL_TYPE,
        params: {window_days: windowDays},
        style: style('#16a34a', {lineType: 'dashed', markerEnd: 'arrow'}),
        componentStyles: {calendar_return: style('#dc2626', {lineWidth: 3, lineType: 'dotted', markerStart: 'circle'})},
    };
}

/** A saved config of the removed signal as `createSignalConfig` makes it: no `componentStyles` at all. */
function removedPlain(id: string, window: number): SignalConfig {
    return {id, signalType: REMOVED_SIGNAL_TYPE, params: {window}, style: style('#9333ea', {lineWidth: 1, lineType: 'dotted'})};
}

/** `removedPlain` once migrated: it gains no `componentStyles` it never had. */
function calendarPlain(id: string, windowDays: number): SignalConfig {
    return {id, signalType: CALENDAR_SIGNAL_TYPE, params: {window_days: windowDays}, style: style('#9333ea', {lineWidth: 1, lineType: 'dotted'})};
}

function emaSignal(): SignalConfig {
    return {id: 'ema-20', signalType: 'ema', params: {period: 20, offset: 0}, style: style('#3b82f6', {lineWidth: 1, lineType: 'dotted'})};
}

/** A neighbour that looks like the removed signal — a risk window named `window`, an output styled by key — and must not move. */
function volatilitySignal(): SignalConfig {
    return {
        id: 'volatility-30',
        signalType: 'risk-rolling-volatility',
        params: {window: 30},
        style: style('#f59e0b'),
        componentStyles: {rolling_volatility: style('#0ea5e9', {lineWidth: 3})},
    };
}

function rsiSignal(): SignalConfig {
    return {
        id: 'rsi-14',
        signalType: 'rsi',
        params: {period: 14, overbought: 70, oversold: 30},
        style: style('#a855f7'),
        partitionStyles: {'rsi:overbought': style('#ef4444', {lineType: 'dashed'})},
    };
}

function comparisonSignal(): SignalConfig {
    return {id: 'comparison-77', signalType: 'asset-comparison', params: {assetId: '77', _assetDisplayName: 'Comparison label'}, style: style('#2563eb')};
}

function settings(signals: SignalConfig[], overrides: Partial<ChartSettings> = {}): ChartSettings {
    return {...structuredClone(DEFAULT_CHART_SETTINGS), signals, ...overrides};
}

/** Settings of one asset that differ from the defaults everywhere a value can, signals aside. */
function asset7Overrides(): Partial<ChartSettings> {
    return {
        areaFill: false,
        axisScales: {
            absolute: {mode: 'custom', min: -5, max: 42},
            percentage: {mode: 'include0'},
            secondary: {'independent:rsi': {mode: 'custom', min: 0, max: 100}},
        },
        calendarReturnWindow: {kind: 'custom', preset: '1m', customAmount: 2, customUnit: 'years'},
    };
}

/** A version-1 settings record: the legacy single Y axis instead of `axisScales`. */
function legacySettings(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, yAxisMode: 'auto', yAxisMin: null, yAxisMax: null, signals: [], ...overrides};
}

/** Every place a signal can be stored, the removed one in three of them and in both of its shapes. */
function v2Document(): StoredDocument {
    return {
        version: 2,
        globalSettings: settings([emaSignal(), removedStyled('rolling-return-global', 90), volatilitySignal()]),
        pairOverrides: [
            ['__global_assets__', settings([removedPlain('rolling-return-assets', 30)], {gridLines: false})],
            ['asset-7', settings([rsiSignal(), removedStyled('rolling-return-asset-7', 250), comparisonSignal()], asset7Overrides())],
            ['EUR-USD', settings([emaSignal()], {colorByBaseline: false})],
        ],
    };
}

/** What `v2Document()` becomes: version 3, its three removed configs migrated, every other field where it was. */
function v3Document(): StoredDocument {
    return {
        version: 3,
        globalSettings: settings([emaSignal(), calendarStyled('rolling-return-global', 90), volatilitySignal()]),
        pairOverrides: [
            ['__global_assets__', settings([calendarPlain('rolling-return-assets', 30)], {gridLines: false})],
            ['asset-7', settings([rsiSignal(), calendarStyled('rolling-return-asset-7', 250), comparisonSignal()], asset7Overrides())],
            ['EUR-USD', settings([emaSignal()], {colorByBaseline: false})],
        ],
    };
}

function signalsOf(value: unknown): unknown {
    return (value as {signals?: unknown}).signals;
}

function overrideSignals(document: StoredDocument, key: string): unknown {
    return signalsOf(document.pairOverrides.find(([candidate]) => candidate === key)?.[1]);
}

/** The scale a user set on the removed signal's own axis: custom, so no default can pass for it. */
function removedAxisScale(): AxisScaleSettings {
    return {mode: 'custom', min: -20, max: 35};
}

/** A scale the calendar return's axis already has of its own, distinct from the removed one. */
function calendarAxisScale(): AxisScaleSettings {
    return {mode: 'custom', min: -8, max: 12};
}

/** A neighbouring secondary axis, which the migration must not touch. */
function rsiAxisScale(): AxisScaleSettings {
    return {mode: 'custom', min: 0, max: 100};
}

/** Settings with these secondary-axis scales, and primary axes that differ from the defaults so that a reset shows. */
function withSecondary(secondary: Record<string, AxisScaleSettings>, signals: SignalConfig[] = []): ChartSettings {
    return settings(signals, {axisScales: {absolute: {mode: 'custom', min: -5, max: 42}, percentage: {mode: 'auto'}, secondary}});
}

function secondaryOf(value: unknown): Record<string, unknown> {
    return (value as {axisScales?: {secondary?: Record<string, unknown>}}).axisScales?.secondary ?? {};
}

// ═══════════════════════════════════════════════════════════════════════════════
// The pure migration
// ═══════════════════════════════════════════════════════════════════════════════

describe('migratePersistedChartSettings — storage version 3', () => {
    it('names both signal types after their backend codes', () => {
        // Premise: a stored config carries the catalog type, derived from the backend signal code.
        expect(signalCodeToType('RISK_ROLLING_RETURN')).toBe(REMOVED_SIGNAL_TYPE);
        expect(signalCodeToType('ASSET_CALENDAR_ROLLING_RETURN')).toBe(CALENDAR_SIGNAL_TYPE);
    });

    it('turns every saved observation Rolling Return of a v2 document into the calendar one, and moves nothing else', () => {
        const stored = v2Document();
        const before = structuredClone(stored);

        const migrated = migrate(stored);

        expect(migrated).toEqual(v3Document());
        // Pure: the parsed document it was handed is left as it was.
        expect(stored).toEqual(before);
    });

    it('carries the same number of days and the restyled output to the new keys', () => {
        const migrated = migrate({version: 2, globalSettings: settings([removedStyled('rolling-return-solo', 365)]), pairOverrides: []}) as StoredDocument;
        const [config] = signalsOf(migrated.globalSettings) as SignalConfig[];

        expect(config.signalType).toBe(CALENDAR_SIGNAL_TYPE);
        expect(config.params).toEqual({window_days: 365});
        expect(config.componentStyles).toEqual({calendar_return: removedStyled('rolling-return-solo', 365).componentStyles?.rolling_return});
    });

    it('migrates a v1 document to version 3 as well', () => {
        // How the legacy single Y axis of version 1 reaches `axisScales` is pinned through hydration in
        // chartSettingsStore.test.ts; here only the version and the signals.
        const stored = {
            version: 1,
            globalSettings: legacySettings({yAxisMode: 'custom', yAxisMin: -5, yAxisMax: 42, signals: [removedStyled('rolling-return-v1', 60), emaSignal()]}),
            pairOverrides: [['asset-9', legacySettings({signals: [removedPlain('rolling-return-v1-asset-9', 7)]})]],
        };

        const migrated = migrate(stored) as StoredDocument;

        expect(migrated.version).toBe(3);
        expect(signalsOf(migrated.globalSettings)).toEqual([calendarStyled('rolling-return-v1', 60), emaSignal()]);
        expect(migrated.pairOverrides.map(([key, value]) => [key, signalsOf(value)])).toEqual([['asset-9', [calendarPlain('rolling-return-v1-asset-9', 7)]]]);
    });

    it('passes a version-3 document through unchanged, so migrating twice changes nothing', () => {
        expect(migrate(v3Document())).toEqual(v3Document());
        expect(migrate(migrate(v2Document()))).toEqual(v3Document());
    });

    it('changes only the version of a v2 document that never saved the removed signal', () => {
        const stored: StoredDocument = {
            version: 2,
            globalSettings: settings([emaSignal(), volatilitySignal()]),
            pairOverrides: [
                ['asset-7', settings([rsiSignal(), comparisonSignal()], asset7Overrides())],
                ['EUR-USD', settings([], {staleGradient: false})],
            ],
        };

        expect(migrate(structuredClone(stored))).toEqual({...stored, version: 3});
    });
});

describe('migratePersistedChartSettings — the saved scale of the Rolling Return axis', () => {
    it('moves the removed signal’s axis scale to the calendar return’s axis, and leaves the other axes where they were', () => {
        const stored: StoredDocument = {
            version: 2,
            globalSettings: withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}, [removedStyled('rolling-return-global', 90), rsiSignal()]),
            pairOverrides: [],
        };

        const migrated = migrate(stored) as StoredDocument;

        expect(migrated.globalSettings).toEqual(withSecondary({[CALENDAR_AXIS_KEY]: removedAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}, [calendarStyled('rolling-return-global', 90), rsiSignal()]));
        expect(Object.keys(secondaryOf(migrated.globalSettings))).not.toContain(REMOVED_AXIS_KEY);
    });

    it('keeps the calendar return’s own scale when both axes were saved, and drops the removed one', () => {
        const stored: StoredDocument = {
            version: 2,
            globalSettings: withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [CALENDAR_AXIS_KEY]: calendarAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}),
            pairOverrides: [],
        };

        const migrated = migrate(stored) as StoredDocument;

        expect(migrated.globalSettings).toEqual(withSecondary({[CALENDAR_AXIS_KEY]: calendarAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}));
        expect(Object.keys(secondaryOf(migrated.globalSettings))).not.toContain(REMOVED_AXIS_KEY);
    });

    it('does the same inside every pair override, and leaves an override without the removed axis as it was', () => {
        const stored: StoredDocument = {
            version: 2,
            globalSettings: withSecondary({[RSI_AXIS_KEY]: rsiAxisScale()}),
            pairOverrides: [
                ['asset-7', withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}, [removedPlain('rolling-return-asset-7', 30)])],
                ['asset-8', withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [CALENDAR_AXIS_KEY]: calendarAxisScale()})],
                ['EUR-USD', withSecondary({[RSI_AXIS_KEY]: rsiAxisScale()})],
            ],
        };

        const migrated = migrate(stored) as StoredDocument;

        expect(migrated).toEqual({
            version: 3,
            globalSettings: withSecondary({[RSI_AXIS_KEY]: rsiAxisScale()}),
            pairOverrides: [
                ['asset-7', withSecondary({[CALENDAR_AXIS_KEY]: removedAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}, [calendarPlain('rolling-return-asset-7', 30)])],
                ['asset-8', withSecondary({[CALENDAR_AXIS_KEY]: calendarAxisScale()})],
                ['EUR-USD', withSecondary({[RSI_AXIS_KEY]: rsiAxisScale()})],
            ],
        });
        for (const [key, value] of migrated.pairOverrides) {
            expect(Object.keys(secondaryOf(value)), `pair override ${key}`).not.toContain(REMOVED_AXIS_KEY);
        }
    });

    it('leaves the parsed document untouched while it moves the axis scales', () => {
        const stored: StoredDocument = {
            version: 2,
            globalSettings: withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}, [removedStyled('rolling-return-global', 90)]),
            pairOverrides: [['asset-7', withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [CALENDAR_AXIS_KEY]: calendarAxisScale()})]],
        };
        const before = structuredClone(stored);

        const migrated = migrate(stored) as StoredDocument;

        // Premise: the migration did move something, so an untouched input is not an idle function's.
        expect(Object.keys(secondaryOf(migrated.globalSettings))).toContain(CALENDAR_AXIS_KEY);
        // Pure: the old key is still in the input it was handed, and no new key was written into it.
        expect(stored).toStrictEqual(before);
        expect(secondaryOf(stored.globalSettings)).toHaveProperty([REMOVED_AXIS_KEY]);
        expect(secondaryOf(stored.globalSettings)).not.toHaveProperty([CALENDAR_AXIS_KEY]);
    });
});

// ═══════════════════════════════════════════════════════════════════════════════
// The wiring — hydration reads an earlier version through the migration
// ═══════════════════════════════════════════════════════════════════════════════

let backing = new Map<string, string>();
let userSeq = 0;

function storageKeyFor(userId: string): string {
    return `lf_${userId}_${STORAGE_SUFFIX}`;
}

/** The id `claim()` will hand out next, so a payload can be seeded under it before it becomes current. */
function nextUserId(): string {
    return `chart-settings-v3-u${userSeq + 1}`;
}

/** Claim a fresh account: that is what makes the store read storage again, not a back door. */
function claim(userId: string): void {
    userSeq += 1;
    expect(userId).toBe(`chart-settings-v3-u${userSeq}`);
    transitionClientSession(userId);
}

function seed(userId: string, payload: unknown): void {
    backing.set(storageKeyFor(userId), JSON.stringify(payload));
}

function persistedFor(userId: string): StoredDocument | null {
    const raw = backing.get(storageKeyFor(userId));
    return raw === undefined ? null : (JSON.parse(raw) as StoredDocument);
}

describe('chartSettingsStore — hydrating earlier storage versions as version 3', () => {
    beforeEach(() => {
        backing = new Map();
        Object.defineProperty(globalThis, 'localStorage', {
            configurable: true,
            writable: true,
            value: {
                getItem: (key: string) => backing.get(key) ?? null,
                setItem: (key: string, value: string) => void backing.set(key, value),
                removeItem: (key: string) => void backing.delete(key),
                clear: () => backing.clear(),
            },
        });
        vi.stubGlobal('fetch', vi.fn());
        apiTransportCall.mockReset();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    it('reads a stored v2 payload back with the calendar return in place of the removed one, and rewrites it as v3', () => {
        const user = nextUserId();
        seed(user, v2Document());
        claim(user);
        const expected = v3Document();

        expect(getGlobalSettings().signals).toEqual(signalsOf(expected.globalSettings));
        expect(getGlobalSettings('assets').signals).toEqual(overrideSignals(expected, '__global_assets__'));
        expect(getSettingsForPair('asset-7', 'assets').signals).toEqual(overrideSignals(expected, 'asset-7'));
        expect(getSettingsForPair('EUR-USD', 'fx').signals).toEqual([emaSignal()]);

        const raw = backing.get(storageKeyFor(user));
        expect(persistedFor(user)?.version).toBe(3);
        expect(raw).not.toContain(`"${REMOVED_SIGNAL_TYPE}"`);
        expect(raw).not.toContain('"rolling_return"');
    });

    it('reads a stored v1 payload with the removed signal as v3 too', () => {
        const user = nextUserId();
        seed(user, {
            version: 1,
            globalSettings: legacySettings({signals: [removedPlain('rolling-return-v1', 14)]}),
            pairOverrides: [['asset-9', legacySettings({areaFill: false, signals: [emaSignal(), removedStyled('rolling-return-v1-asset-9', 120)]})]],
        });
        claim(user);

        expect(getGlobalSettings().signals).toEqual([calendarPlain('rolling-return-v1', 14)]);
        expect(getSettingsForPair('asset-9', 'assets').signals).toEqual([emaSignal(), calendarStyled('rolling-return-v1-asset-9', 120)]);
        expect(persistedFor(user)?.version).toBe(3);
    });

    it('reads a stored v3 payload as it is', () => {
        const user = nextUserId();
        seed(user, v3Document());
        claim(user);
        const expected = v3Document();

        expect(getGlobalSettings().signals).toEqual(signalsOf(expected.globalSettings));
        expect(getSettingsForPair('asset-7', 'assets')).toMatchObject({areaFill: false, signals: overrideSignals(expected, 'asset-7')});
    });

    it('reads a stored v2 payload with the removed signal’s axis scale back under the calendar return’s axis, and rewrites it as v3', () => {
        const user = nextUserId();
        seed(user, {
            version: 2,
            globalSettings: withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()}, [removedStyled('rolling-return-global', 90)]),
            pairOverrides: [['asset-7', withSecondary({[REMOVED_AXIS_KEY]: removedAxisScale(), [CALENDAR_AXIS_KEY]: calendarAxisScale()})]],
        });
        claim(user);

        expect(getGlobalSettings().axisScales).toEqual({
            absolute: {mode: 'custom', min: -5, max: 42},
            percentage: {mode: 'auto'},
            secondary: {[CALENDAR_AXIS_KEY]: removedAxisScale(), [RSI_AXIS_KEY]: rsiAxisScale()},
        });
        expect(getGlobalSettings().signals).toEqual([calendarStyled('rolling-return-global', 90)]);
        expect(getSettingsForPair('asset-7', 'assets').axisScales.secondary).toEqual({[CALENDAR_AXIS_KEY]: calendarAxisScale()});

        expect(persistedFor(user)?.version).toBe(3);
        expect(backing.get(storageKeyFor(user))).not.toContain(`"${REMOVED_AXIS_KEY}"`);
    });
});
