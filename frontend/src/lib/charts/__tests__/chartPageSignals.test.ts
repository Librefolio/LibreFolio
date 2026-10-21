/**
 * Contract tests for the signal helpers the chart detail pages share (FE5c, piece 2; Y-42).
 *
 * The three bodies moved out of the asset detail page verbatim; these tests pin what the page
 * relies on, so the move is proven and later edits are guarded:
 * - the backend signal results are parsed all or nothing, by the real signal result schema;
 * - the data fingerprint follows what the signal data depends on (id, type, params) and nothing
 *   else: not the order, not the style, not the runtime params a comparison load writes back;
 * - the comparison peers are the distinct valid asset ids of the asset-comparison configs.
 *
 * Lot Y-42 moves the two detail pages from their own «signalFromConfig → inject → renderMulti» loop to the one
 * renderer, `lib/charts/chartSignalRendering.ts`, which the lists and the settings preview already use (Y-39a). The
 * pages hand it their data through `detailPageSignalSources(…)`, and three more parts pin that move:
 * - the `detailPageSignalSources` contract, as pure units: the FX pairs come from the store's points, straight
 *   (`fxPointToLineDataPoint(point, false)`), asked lazily and per slug; a comparison's target is the series a load wrote
 *   into the matching config (`params._resolvedData`), named by the assets the page knows; the page's own asset passes
 *   through; nothing is read from a store and nothing is written into the configs;
 * - the parity, through the module: `renderLocalSignals(…, detailPageSignalSources(…))` draws what the detail pages
 *   drew with their own loops — a comparison named after its target, with its icon and type, or by the catalogue's
 *   fallback for an asset the page does not know; never the page's own asset, nor a comparison with no data; the FX
 *   conversion ghost; an FX pair straight, or turned by its own `_inverted`, on the days of the chart, and none for an
 *   empty store — in both view modes where the view matters;
 * - the adoption, read from the two pages' sources (the way `chartCoreHelpers.test.ts` reads the list pages): each
 *   imports `renderLocalSignals` and `renderBackendResults` from the module as values, calls them, and calls
 *   `detailPageSignalSources(`; the FX page keeps no `fxPointToLineDataPoint` of its own and imports the module's.
 *   The gate `signalRendering.gate.test.ts` is the other half: no page calls `signalFromConfig(` any more.
 *
 * A comparison's fallback name is a catalogue message (`ChartSignal.text`), which throws before svelte-i18n is
 * initialised: the file boots it once, in English, and compares a fallback with the catalogue's own text for its key,
 * never with a literal. The names the parity cases give to assets («Synthetic peer») are data they inject.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {get} from 'svelte/store';
import {setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import {fxPointToLineDataPoint, renderLocalSignals, type FxRatePoint} from '$lib/charts/chartSignalRendering';
import {getLocalSignalDefinitions, type RenderedSignal, type SignalConfig, type SignalDefinition, type SignalStyle} from '$lib/charts/signals';
import {backendSignalSchemas} from '$lib/charts/signals/backendTypes';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {displayFxRate} from '$lib/stores/fxStoreRegistry';
import {comparisonAssetIds, detailPageSignalSources, parseBackendSignalResults, signalDataContextFingerprint, type DetailPageAsset, type DetailPageSignalSourcesInput} from '../chartPageSignals';
import {COMPARISON_ASSET_RUNTIME_PARAM_KEYS} from '../loadComparisonData';

/**
 * svelte-i18n throws when it formats a message before it is initialised, and a comparison's fallback name is a
 * formatted message: boot it once for the whole file, in English, the app's fallback.
 */
beforeAll(async () => {
    await setupI18n('en');
});

function signalConfig(id: string, signalType: string, params: Record<string, unknown> = {}, style: Record<string, unknown> = {}): SignalConfig {
    return {id, signalType, params, style} as unknown as SignalConfig;
}

function comparisonConfig(id: string, assetId: unknown, params: Record<string, unknown> = {}): SignalConfig {
    return signalConfig(id, 'asset-comparison', {assetId, ...params});
}

/** A minimal result the signal result schema accepts. */
function signalResult(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {instance_id: 'sma-20', signal_code: 'SMA', status: 'ok', ...overrides};
}

/** Every runtime param a comparison load writes back into its config, each with a value. */
function comparisonRuntimeParams(): Record<string, unknown> {
    return Object.fromEntries(COMPARISON_ASSET_RUNTIME_PARAM_KEYS.map((key) => [key, `runtime value of ${key}`]));
}

describe('parseBackendSignalResults: a non-array is no result; each item is parsed by the signal result schema, and one invalid item throws', () => {
    it.each([
        {label: 'undefined', value: undefined},
        {label: 'null', value: null},
        {label: 'a string', value: 'signals'},
        {label: 'a number', value: 3},
        {label: 'a single result object', value: signalResult()},
    ])('gives no results for $label', ({value}) => {
        expect(parseBackendSignalResults(value)).toEqual([]);
    });

    it('gives no results for an empty array', () => {
        expect(parseBackendSignalResults([])).toEqual([]);
    });

    it('returns each item as the schema parses it, in order', () => {
        const items = [signalResult({instance_id: 'sma-20', note_from_backend: 'a key the schema does not know'}), signalResult({instance_id: 'cci-14', signal_code: 'CCI', status: 'failed', error: {code: 'compute_error', message: 'CCI computation failed'}})];

        const results = parseBackendSignalResults(items);

        expect(results.map((result) => result.instance_id)).toEqual(['sma-20', 'cci-14']);
        expect(results).toEqual(items.map((item) => backendSignalSchemas.result.parse(item)));
        // The schema's output, not the raw item: an unknown key is dropped, a default is filled in.
        expect(results.find((result) => result.instance_id === 'sma-20')).not.toHaveProperty('note_from_backend');
        expect(results.find((result) => result.instance_id === 'cci-14')?.error).toEqual({code: 'compute_error', message: 'CCI computation failed', retryable: false});
    });

    it('throws when one item is invalid, even after valid ones', () => {
        const valid = signalResult();

        expect(parseBackendSignalResults([valid])).toHaveLength(1);
        expect(() => parseBackendSignalResults([valid, signalResult({status: 'not-a-status'})])).toThrow();
        expect(() => parseBackendSignalResults([valid, {signal_code: 'SMA', status: 'ok'}])).toThrow();
        expect(() => parseBackendSignalResults([valid, null])).toThrow();
    });
});

describe('signalDataContextFingerprint: the id, type and params of each config, blind to config order, params order, style and comparison runtime params', () => {
    it('is the JSON of each config id, type and params, sorted by id', () => {
        const fingerprint = signalDataContextFingerprint([signalConfig('sig-b', 'ema', {period: 12, source: 'close'}, {color: '#ff0000'}), comparisonConfig('sig-a', 7)]);

        expect(JSON.parse(fingerprint)).toEqual([
            {id: 'sig-a', signalType: 'asset-comparison', params: {assetId: 7}},
            {id: 'sig-b', signalType: 'ema', params: {period: 12, source: 'close'}},
        ]);
    });

    it('ignores the order of the configs and of their params, and leaves the given configs in their order', () => {
        const configs = [signalConfig('sig-b', 'ema', {period: 12, source: 'close'}), signalConfig('sig-a', 'sma', {source: 'open', period: 20})];
        const reordered = [signalConfig('sig-a', 'sma', {period: 20, source: 'open'}), signalConfig('sig-b', 'ema', {source: 'close', period: 12})];

        expect(signalDataContextFingerprint(configs)).toBe(signalDataContextFingerprint(reordered));
        expect(configs.map((config) => config.id)).toEqual(['sig-b', 'sig-a']);
    });

    it('ignores the style of a config', () => {
        const styled = signalConfig('sig-a', 'sma', {period: 20}, {color: '#ff0000', lineWidth: 1});
        const restyled = signalConfig('sig-a', 'sma', {period: 20}, {color: '#00ff00', lineWidth: 3});

        expect(signalDataContextFingerprint([restyled])).toBe(signalDataContextFingerprint([styled]));
    });

    it('ignores every runtime param a comparison load writes back', () => {
        const bare = comparisonConfig('sig-a', 7, {mode: 'percent'});
        const loaded = comparisonConfig('sig-a', 7, {mode: 'percent', ...comparisonRuntimeParams()});

        expect(signalDataContextFingerprint([loaded])).toBe(signalDataContextFingerprint([bare]));
    });

    it.each([
        {label: 'a param value', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-a', 'sma', {period: 21})},
        {label: 'an added param', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-a', 'sma', {period: 20, source: 'close'})},
        {label: 'the signal type', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-a', 'ema', {period: 20})},
        {label: 'the id', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-b', 'sma', {period: 20})},
        {label: 'the comparison peer', base: comparisonConfig('sig-a', 7), changed: comparisonConfig('sig-a', 8)},
    ])('changes with $label', ({base, changed}) => {
        expect(signalDataContextFingerprint([changed])).not.toBe(signalDataContextFingerprint([base]));
    });
});

describe('comparisonAssetIds: the distinct positive safe-integer peers of the asset-comparison configs, ascending, without the excluded asset', () => {
    it('reads only asset-comparison configs', () => {
        const configs = [comparisonConfig('cmp-7', 7), signalConfig('fx-1', 'fx-pair', {assetId: 5}), signalConfig('sma-1', 'sma', {assetId: 6, period: 20})];

        expect(comparisonAssetIds(configs)).toEqual([7]);
    });

    it('returns each peer once, in ascending numeric order', () => {
        const configs = [comparisonConfig('cmp-a', 10), comparisonConfig('cmp-b', 9), comparisonConfig('cmp-c', 2), comparisonConfig('cmp-d', 9)];

        expect(comparisonAssetIds(configs)).toEqual([2, 9, 10]);
    });

    it.each([
        {label: 'zero', assetId: 0},
        {label: 'a negative id', assetId: -4},
        {label: 'a fractional id', assetId: 2.5},
        {label: 'NaN', assetId: Number.NaN},
        {label: 'an infinite id', assetId: Number.POSITIVE_INFINITY},
        {label: 'an id beyond the safe integers', assetId: Number.MAX_SAFE_INTEGER + 1},
        {label: 'a string that is not a number', assetId: 'seven'},
        {label: 'null', assetId: null},
        {label: 'a missing id', assetId: undefined},
    ])('drops $label', ({assetId}) => {
        expect(comparisonAssetIds([comparisonConfig('cmp-bad', assetId), comparisonConfig('cmp-ok', 4)])).toEqual([4]);
    });

    it('reads a numeric string as its number, and keeps the largest safe integer', () => {
        const configs = [comparisonConfig('cmp-a', '7'), comparisonConfig('cmp-b', 7), comparisonConfig('cmp-c', Number.MAX_SAFE_INTEGER)];

        expect(comparisonAssetIds(configs)).toEqual([7, Number.MAX_SAFE_INTEGER]);
    });

    it('leaves out the excluded asset, and only it', () => {
        const configs = [comparisonConfig('cmp-a', 3), comparisonConfig('cmp-b', '7'), comparisonConfig('cmp-c', 8)];

        expect(comparisonAssetIds(configs, 7)).toEqual([3, 8]);
        expect(comparisonAssetIds(configs, 99)).toEqual([3, 7, 8]);
        expect(comparisonAssetIds(configs)).toEqual([3, 7, 8]);
    });

    it('gives no peers without configs', () => {
        expect(comparisonAssetIds([])).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// Y-42 — what the detail pages hand the one renderer
// ---------------------------------------------------------------------------

type ViewMode = Parameters<typeof renderLocalSignals>[3];

/** A catalogue message with its values, as the interface language words it. */
function catalogue(key: string, values: Record<string, string> = {}): string {
    return get(_)(key, {values});
}

const STYLE: SignalStyle = {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null};

/** The four days the detail chart draws: the base data of every signal below. */
const CHART: LineDataPoint[] = [
    {date: '2026-03-02', value: 100},
    {date: '2026-03-03', value: 110},
    {date: '2026-03-04', value: 120},
    {date: '2026-03-05', value: 130},
];

/** EUR-GBP as the FX store holds it, straight: a day before the chart, a backward-filled rate, and a point with no rate on 03-05. */
const EUR_GBP_STORE: readonly FxRatePoint[] = [
    {date: '2026-02-27', rate: 0.4, backwardFillInfo: null},
    {date: '2026-03-02', rate: 0.5, backwardFillInfo: null},
    {date: '2026-03-03', rate: 0.8, backwardFillInfo: {actualRateDate: '2026-03-02', daysBack: 1}},
    {date: '2026-03-04', rate: 0.625, backwardFillInfo: null},
    {date: '2026-03-05', rate: null, backwardFillInfo: null},
];
/** The days of the chart the pair draws on: the store has a usable rate for them, and none on 03-05. */
const FX_DAYS = ['2026-03-02', '2026-03-03', '2026-03-04'];

/** The asset the comparisons target, and the asset the detail page itself draws. */
const PEER_ID = 42;
const PEER_NAME = 'Synthetic peer';
const OWN_ID = 7;
const OWN_NAME = 'The page asset';

/** The assets the page knows: what names a comparison. */
const ASSETS: readonly DetailPageAsset[] = [
    {id: PEER_ID, display_name: PEER_NAME, icon_url: '/icons/peer.png', asset_type: 'ETF'},
    {id: OWN_ID, display_name: OWN_NAME, icon_url: null, asset_type: null},
];

/**
 * Asset 42's series as a comparison load writes it into its config: a day before the chart and one after it, and no
 * price on 03-04. A fresh copy each time, so a case that freezes it freezes its own.
 */
const peerSeries = (): LineDataPoint[] => [
    {date: '2026-02-27', value: 190},
    {date: '2026-03-02', value: 200},
    {date: '2026-03-03', value: 220},
    {date: '2026-03-05', value: 180},
    {date: '2026-03-06', value: 240},
];
/** The days of the chart asset 42 has a price for. */
const PEER_DATES = ['2026-03-02', '2026-03-03', '2026-03-05'];

/** Asset 42's series after an FX conversion: the converted value, and the original one the ghost line draws (190 to 240 at 0.9). */
const convertedPeerSeries = (): LineDataPoint[] =>
    [
        {date: '2026-02-27', value: 171, originalValue: 190},
        {date: '2026-03-02', value: 180, originalValue: 200},
        {date: '2026-03-03', value: 198, originalValue: 220},
        {date: '2026-03-05', value: 162, originalValue: 180},
        {date: '2026-03-06', value: 216, originalValue: 240},
    ].map((point) => ({...point, originalCurrency: 'USD', originalCurrencyFlag: 'flag-usd'}));

/** A config with a complete style: what a chart draws. */
function drawnConfig(id: string, signalType: string, params: Record<string, unknown> = {}): SignalConfig {
    return {id, signalType, params, style: {...STYLE}};
}

/**
 * A comparison config as a detail page holds it after a comparison load: the target's series written into its params
 * (`_resolvedData`). `series: null` is a config no load has reached.
 */
function loadedComparison(assetId: unknown = PEER_ID, params: Record<string, unknown> = {}, series: LineDataPoint[] | null = peerSeries()): SignalConfig {
    return drawnConfig(`cmp-${String(assetId)}`, 'asset-comparison', {assetId, ...(series ? {_resolvedData: series} : {}), ...params});
}

const fxPairConfig = (params: Record<string, unknown> = {}): SignalConfig => drawnConfig('fx-eur-gbp', 'fx-pair', {pairSlug: 'EUR-GBP', ...params});
const linearConfig = (): SignalConfig => drawnConfig('lin-1', 'linear', {annualRate: 2, offset: 0});

/** The definitions a detail page draws its local signals by: the registry's local ones, by type. */
const DETAIL_DEFINITIONS: ReadonlyMap<string, SignalDefinition> = new Map(getLocalSignalDefinitions().map((definition) => [definition.type, definition]));

/** What a detail page hands the module: its configs, the assets it knows, and the FX store, which holds EUR-GBP and nothing else. */
function pageInput(configs: readonly SignalConfig[], overrides: Partial<DetailPageSignalSourcesInput> = {}): DetailPageSignalSourcesInput {
    return {configs, assets: ASSETS, fxPairPoints: (pairSlug) => (pairSlug === 'EUR-GBP' ? EUR_GBP_STORE : []), ...overrides};
}

/** The signals the module draws on the detail chart for `configs`, with the sources a detail page builds. */
function drawn(configs: readonly SignalConfig[], viewMode: ViewMode, overrides: Partial<DetailPageSignalSourcesInput> = {}): RenderedSignal[] {
    return renderLocalSignals(configs, DETAIL_DEFINITIONS, CHART, viewMode, detailPageSignalSources(pageInput(configs, overrides)));
}

/** To 9 decimals, -0 read as 0: what the cases compare, so that a float's last bit never decides. */
const round = (value: number): number => Number(value.toFixed(9)) + 0;
const idsOf = (signals: readonly RenderedSignal[]): string[] => signals.map((signal) => signal.id);
const datesOf = (signal: RenderedSignal | undefined): string[] => (signal?.data ?? []).map((point) => point.date);
const valuesOf = (signal: RenderedSignal | undefined): number[] => (signal?.data ?? []).map((point) => round(point.value));

/** A value frozen to its leaves: writing into it throws, in strict code. */
function frozen<T>(value: T): T {
    if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
        Object.freeze(value);
        for (const child of Object.values(value)) frozen(child);
    }
    return value;
}

/**
 * What the FX detail page drew for the pair: each store rate shown as `displayFxRate(rate, false)`, on the days of the
 * chart that have one, then turned by the signal's own `_inverted`. Built from the store points alone, not from the module.
 */
function fxPageValues(inverted: boolean): number[] {
    const rates = new Map(EUR_GBP_STORE.map((point) => [point.date, displayFxRate(point.rate, false)]));
    return CHART.flatMap(({date}) => {
        const rate = rates.get(date);
        return rate ? [round(inverted ? 1 / rate : rate)] : [];
    });
}

// ---------------------------------------------------------------------------
// The contract
// ---------------------------------------------------------------------------

describe('detailPageSignalSources.fxPairData: the store’s points of a pair, straight, as chart points (Y-42)', () => {
    it('converts each store point as the chart shows a pair straight: the rate, a gap where no rate is usable, the days a backward-filled rate is stale', () => {
        const points: FxRatePoint[] = [
            {date: '2026-03-02', rate: 0.5, backwardFillInfo: null},
            {date: '2026-03-03', rate: 0.8, backwardFillInfo: {actualRateDate: '2026-02-27', daysBack: 3}},
            {date: '2026-03-04', rate: null, backwardFillInfo: null},
            {date: '2026-03-05', rate: 0},
        ];
        const sources = detailPageSignalSources(pageInput([], {fxPairPoints: () => points}));

        const data = sources.fxPairData('EUR-GBP');

        expect(data, 'not the straight rates, in the module’s own point shape').toEqual([
            {date: '2026-03-02', value: 0.5, missing: false, staleDays: 0},
            {date: '2026-03-03', value: 0.8, missing: false, staleDays: 3},
            {date: '2026-03-04', value: 0, missing: true, staleDays: 0},
            {date: '2026-03-05', value: 0, missing: true, staleDays: 0},
        ]);
        expect(data, 'not fxPointToLineDataPoint(point, false) of each point').toEqual(points.map((point) => fxPointToLineDataPoint(point, false)));
    });

    it('hands the rates over straight, whatever the pair is shown as: turning them is the signal’s own _inverted, nowhere else', () => {
        const sources = detailPageSignalSources(pageInput([fxPairConfig({_inverted: true})]));

        expect(sources.fxPairData('EUR-GBP')?.map((point) => round(point.value))).toEqual(EUR_GBP_STORE.map((point) => round(point.rate ?? 0)));
    });

    it('gives an empty array, not null, for a pair the store holds no points of', () => {
        const sources = detailPageSignalSources(pageInput([]));

        expect(sources.fxPairData('USD-JPY')).toEqual([]);
    });

    it('asks the store only when asked, and only for the slug asked', () => {
        const fxPairPoints = vi.fn((pairSlug: string): readonly FxRatePoint[] => (pairSlug === 'EUR-GBP' ? EUR_GBP_STORE : []));

        const sources = detailPageSignalSources(pageInput([fxPairConfig(), loadedComparison()], {fxPairPoints}));
        expect(fxPairPoints, 'building the sources already reads the store').not.toHaveBeenCalled();

        expect(sources.fxPairData('EUR-GBP')).toHaveLength(EUR_GBP_STORE.length);
        expect(fxPairPoints.mock.calls.map(([pairSlug]) => pairSlug)).toEqual(['EUR-GBP']);

        expect(sources.fxPairData('USD-JPY')).toEqual([]);
        expect(fxPairPoints.mock.calls.map(([pairSlug]) => pairSlug)).toEqual(['EUR-GBP', 'USD-JPY']);
    });
});

describe('detailPageSignalSources.comparisonTarget: the series a comparison load wrote into the matching config, named by the assets the page knows (Y-42)', () => {
    it('is the _resolvedData of the config of that asset, with the name, icon and type of the asset — and no base point: a detail page draws daily data', () => {
        const series = peerSeries();
        const sources = detailPageSignalSources(pageInput([loadedComparison(PEER_ID, {}, series)]));

        const target = sources.comparisonTarget(PEER_ID);

        expect(target?.data, 'the very array the load wrote, not a copy').toBe(series);
        expect(target).toEqual({data: series, displayName: PEER_NAME, iconUrl: '/icons/peer.png', assetType: 'ETF'});
        expect(target?.basePoint ?? null).toBeNull();
    });

    it('reads the saved asset id as a number: a numeric string matches the same asset', () => {
        const series = peerSeries();
        const sources = detailPageSignalSources(pageInput([loadedComparison(String(PEER_ID), {}, series)]));

        expect(sources.comparisonTarget(PEER_ID)?.data).toBe(series);
    });

    it('finds each asset’s own series among several comparisons', () => {
        const peer = peerSeries();
        const own = [{date: '2026-03-02', value: 50}];
        const sources = detailPageSignalSources(pageInput([loadedComparison(PEER_ID, {}, peer), loadedComparison(OWN_ID, {}, own)]));

        expect(sources.comparisonTarget(OWN_ID)).toEqual({data: own, displayName: OWN_NAME, iconUrl: null, assetType: null});
        expect(sources.comparisonTarget(PEER_ID)?.data).toBe(peer);
    });

    it('takes the first config of that asset that has data: one a load has not reached is passed over', () => {
        const later = peerSeries();
        const sources = detailPageSignalSources(
            pageInput([
                {...loadedComparison(PEER_ID, {}, null), id: 'cmp-a'},
                {...loadedComparison(PEER_ID, {_resolvedData: []}), id: 'cmp-b'},
                {...loadedComparison(PEER_ID, {}, later), id: 'cmp-c'},
                {...loadedComparison(PEER_ID, {}, [{date: '2026-03-02', value: 1}]), id: 'cmp-d'},
            ]),
        );

        expect(sources.comparisonTarget(PEER_ID)?.data).toBe(later);
    });

    it.each([
        {label: 'no _resolvedData: no load has reached the config', config: () => loadedComparison(PEER_ID, {}, null)},
        {label: 'an empty _resolvedData', config: () => loadedComparison(PEER_ID, {_resolvedData: []})},
        {label: 'a _resolvedData that is not an array', config: () => loadedComparison(PEER_ID, {_resolvedData: {date: '2026-03-02', value: 200}})},
    ])('is null for a config with $label', ({config}) => {
        expect(detailPageSignalSources(pageInput([config()])).comparisonTarget(PEER_ID)).toBeNull();
    });

    it.each([
        {label: 'an asset no config compares', assetId: 43},
        {label: 'an asset id of 0', assetId: 0},
    ])('is null for $label', ({assetId}) => {
        expect(detailPageSignalSources(pageInput([loadedComparison(PEER_ID)])).comparisonTarget(assetId)).toBeNull();
    });

    it.each([
        {label: 'an FX pair', signalType: 'fx-pair'},
        {label: 'a linear benchmark', signalType: 'linear'},
        {label: 'a backend indicator', signalType: 'sma'},
    ])('is null when the only config of the asset is $label, whatever its params hold', ({signalType}) => {
        const config = drawnConfig('other-1', signalType, {assetId: PEER_ID, _resolvedData: peerSeries()});

        expect(detailPageSignalSources(pageInput([config])).comparisonTarget(PEER_ID)).toBeNull();
    });

    it('names an asset the page does not know with nulls, and keeps its series: the signal’s own catalogue fallback names it', () => {
        const series = peerSeries();
        const sources = detailPageSignalSources(pageInput([loadedComparison(PEER_ID, {}, series)], {assets: []}));

        expect(sources.comparisonTarget(PEER_ID)).toEqual({data: series, displayName: null, iconUrl: null, assetType: null});
    });

    it('gives null for an icon or a type the known asset does not have', () => {
        const series = peerSeries();
        const assets: DetailPageAsset[] = [{id: PEER_ID, display_name: PEER_NAME}];

        expect(detailPageSignalSources(pageInput([loadedComparison(PEER_ID, {}, series)], {assets})).comparisonTarget(PEER_ID)).toEqual({data: series, displayName: PEER_NAME, iconUrl: null, assetType: null});
    });
});

describe('detailPageSignalSources.selfAssetId: the asset the page draws, passed through (Y-42)', () => {
    it.each([
        {label: 'the asset the page draws', selfAssetId: OWN_ID, expected: OWN_ID},
        {label: 'no asset (null)', selfAssetId: null, expected: null},
        {label: 'no asset (absent)', selfAssetId: undefined, expected: null},
    ])('is $expected for $label', ({selfAssetId, expected}) => {
        const sources = detailPageSignalSources(pageInput([], selfAssetId === undefined ? {} : {selfAssetId}));

        expect(sources.selfAssetId).toBe(expected);
    });
});

describe('detailPageSignalSources: pure — it reads the configs, the assets and the store, and writes into none of them (Y-42)', () => {
    it('leaves the configs, the assets and the store’s points as they were, however the sources are used', () => {
        const configs = frozen([loadedComparison(), loadedComparison(OWN_ID), fxPairConfig({_inverted: true}), linearConfig()]);
        const assets = frozen(ASSETS.map((asset) => ({...asset})));
        const points = frozen(EUR_GBP_STORE.map((point) => ({...point})));
        const before: unknown = JSON.parse(JSON.stringify({configs, assets, points}));

        const sources = detailPageSignalSources({configs, assets, fxPairPoints: () => points, selfAssetId: OWN_ID});
        expect(() => {
            sources.fxPairData('EUR-GBP');
            sources.comparisonTarget(PEER_ID);
            sources.comparisonTarget(OWN_ID);
            sources.comparisonTarget(999);
            renderLocalSignals(configs, DETAIL_DEFINITIONS, CHART, 'percentage', sources);
        }, 'it writes into what it was given (frozen here, so a write throws)').not.toThrow();

        expect({configs, assets, points}).toEqual(before);
    });
});

// ---------------------------------------------------------------------------
// The parity: what the detail pages drew with their own loops, drawn through the module
// ---------------------------------------------------------------------------

describe('through the module, the detail pages draw their saved signals as their own loops did (Y-42 parity)', () => {
    describe('a comparison', () => {
        it.each([
            {viewMode: 'absolute', values: [200, 220, 180]},
            {viewMode: 'percentage', values: [0, 10, -10]},
        ] as const)('is named after its target, with its icon and type, and drawn on the days the chart draws ($viewMode view)', ({viewMode, values}) => {
            const signals = drawn([loadedComparison()], viewMode);

            expect(idsOf(signals)).toEqual(['cmp-42']);
            expect(signals[0]?.label, 'the comparison is not named after its target').toBe(PEER_NAME);
            expect({iconUrl: signals[0]?.iconUrl, assetType: signals[0]?.assetType}).toEqual({iconUrl: '/icons/peer.png', assetType: 'ETF'});
            expect(datesOf(signals[0])).toEqual(PEER_DATES);
            expect(valuesOf(signals[0]), viewMode === 'percentage' ? 'measured from its own first price' : 'its own prices').toEqual(values);
        });

        it('gives each comparison the series of its own asset, in the order of the configs', () => {
            const own = [
                {date: '2026-03-02', value: 50},
                {date: '2026-03-03', value: 55},
            ];

            const signals = drawn([loadedComparison(PEER_ID), loadedComparison(OWN_ID, {}, own)], 'absolute');

            expect(signals.map((signal) => [signal.id, signal.label])).toEqual([
                ['cmp-42', PEER_NAME],
                ['cmp-7', OWN_NAME],
            ]);
            expect(signals.map(valuesOf)).toEqual([
                [200, 220, 180],
                [50, 55],
            ]);
        });

        it('on an asset the page does not know is named by the catalogue’s fallback, with the series the load wrote and no icon or type', () => {
            const signals = drawn([loadedComparison(43)], 'absolute');

            expect(idsOf(signals)).toEqual(['cmp-43']);
            expect(signals[0]?.label).toBe(catalogue('chartSettings.signals.assetFallback', {id: '43'}));
            expect({iconUrl: signals[0]?.iconUrl, assetType: signals[0]?.assetType}).toEqual({iconUrl: null, assetType: null});
            expect(valuesOf(signals[0])).toEqual([200, 220, 180]);
        });

        it.each([
            {label: 'its id saved as a number', assetId: OWN_ID},
            {label: 'its id saved as a numeric string', assetId: String(OWN_ID)},
        ])('is never drawn with the page’s own asset ($label)', ({assetId}) => {
            expect(drawn([loadedComparison(assetId)], 'absolute', {selfAssetId: OWN_ID})).toEqual([]);
        });

        it('is drawn with that same asset on a page that draws no asset, the FX detail page', () => {
            const signals = drawn([loadedComparison(OWN_ID)], 'absolute');

            expect(signals.map((signal) => signal.label)).toEqual([OWN_NAME]);
        });

        it.each([
            {label: 'no _resolvedData: no load has reached it', config: () => loadedComparison(PEER_ID, {}, null)},
            {label: 'an empty _resolvedData: its target has no prices', config: () => loadedComparison(PEER_ID, {_resolvedData: []})},
        ])('is not drawn with $label, and the comparison beside it still is', ({config}) => {
            const signals = drawn([config(), loadedComparison(OWN_ID)], 'absolute');

            expect(idsOf(signals)).toEqual(['cmp-7']);
        });

        it.each([
            {viewMode: 'absolute', main: [180, 198, 162], ghost: [200, 220, 180]},
            {viewMode: 'percentage', main: [0, 10, -10], ghost: [0, 10, -10]},
        ] as const)('converted by FX keeps its ghost line, the unconverted prices, dashed beside it ($viewMode view)', ({viewMode, main, ghost}) => {
            const config = loadedComparison(PEER_ID, {_assetCurrency: 'USD', _targetCurrency: 'EUR'}, convertedPeerSeries());

            const signals = drawn([config], viewMode);

            expect(idsOf(signals), 'the converted line, then its ghost').toEqual(['cmp-42', 'cmp-42__ghost']);
            expect(valuesOf(signals[0])).toEqual(main);
            expect(signals[0]?.currency, 'the converted line is in the target currency, a runtime param the config carries').toBe('EUR');
            expect(valuesOf(signals[1])).toEqual(ghost);
            expect(datesOf(signals[1])).toEqual(PEER_DATES);
            expect(signals[1]).toMatchObject({lineType: 'dashed', currency: 'USD'});
        });

        it('with no converted price draws no ghost line', () => {
            expect(idsOf(drawn([loadedComparison()], 'absolute')).filter((id) => id.endsWith('__ghost'))).toEqual([]);
        });
    });

    describe('an FX pair', () => {
        it('is drawn straight, on the days of the chart that have a usable rate, as the FX page drew it: displayFxRate(rate, false)', () => {
            const signals = drawn([fxPairConfig()], 'absolute');

            expect(idsOf(signals)).toEqual(['fx-eur-gbp']);
            expect(datesOf(signals[0]), 'a day with no rate is not drawn').toEqual(FX_DAYS);
            expect(valuesOf(signals[0])).toEqual(fxPageValues(false));
            expect(valuesOf(signals[0]), 'control: the store’s rates, straight').toEqual([0.5, 0.8, 0.625]);
        });

        it('is turned by its own _inverted, and only by it', () => {
            const signals = drawn([fxPairConfig({_inverted: true})], 'absolute');

            expect(datesOf(signals[0])).toEqual(FX_DAYS);
            expect(valuesOf(signals[0])).toEqual(fxPageValues(true));
            expect(valuesOf(signals[0]), 'control: the reciprocals of the store’s rates').toEqual([2, 1.25, 1.6]);
        });

        it.each([
            {label: 'straight', params: {}, values: [0, 60, 25]},
            {label: 'inverted', params: {_inverted: true}, values: [0, -37.5, -20]},
        ])('in the percentage view is measured from its own first rate, $label', ({params, values}) => {
            const signals = drawn([fxPairConfig(params)], 'percentage');

            expect(valuesOf(signals[0])).toEqual(values);
        });

        it('asks the FX store for the pair the config names, and for no other', () => {
            const fxPairPoints = vi.fn((pairSlug: string): readonly FxRatePoint[] => (pairSlug === 'EUR-GBP' ? EUR_GBP_STORE : []));

            drawn([fxPairConfig(), loadedComparison(), linearConfig()], 'absolute', {fxPairPoints});

            expect([...new Set(fxPairPoints.mock.calls.map(([pairSlug]) => pairSlug))]).toEqual(['EUR-GBP']);
        });

        it('is not drawn when the store holds no points of its pair, and the signals beside it still are', () => {
            const signals = drawn([fxPairConfig(), loadedComparison()], 'absolute', {fxPairPoints: () => []});

            expect(idsOf(signals)).toEqual(['cmp-42']);
        });

        it('is not drawn without a pair, and the signals beside it still are', () => {
            const signals = drawn([fxPairConfig({pairSlug: ''}), linearConfig()], 'absolute');

            expect(idsOf(signals)).toEqual(['lin-1']);
        });
    });

    it('draws the local configs in their order, and leaves a backend one or one of no known definition to the backend results', () => {
        const configs = [fxPairConfig(), drawnConfig('sma-1', 'sma', {window: 2}), loadedComparison(), drawnConfig('mystery-1', 'mystery-signal'), linearConfig()];

        expect(idsOf(drawn(configs, 'absolute'))).toEqual(['fx-eur-gbp', 'cmp-42', 'lin-1']);
    });
});

// ---------------------------------------------------------------------------
// The adoption: read from the sources of the two detail pages
// ---------------------------------------------------------------------------

/**
 * The two detail pages: reading their sources is how adoption is proven, since mounting a page loads a dozen endpoints
 * and stores before it draws. A form here is a floor, not a proof: the signals they draw are pinned by the cases above
 * and by the gate `signalRendering.gate.test.ts` (no page calls `signalFromConfig(`); what a page shows by its E2E.
 */
const DETAIL_PAGES = [
    ['asset detail', new URL('../../../routes/(app)/assets/[id]/+page.svelte', import.meta.url)],
    ['FX detail', new URL('../../../routes/(app)/fx/[pair]/+page.svelte', import.meta.url)],
] as const;

/** Where the pages get the one renderer, as an import names it. */
const MODULE_IMPORT = /import\s+(type\s+)?([^;'"]*?)\s*\bfrom\s*['"]\$lib\/charts\/chartSignalRendering['"]/g;

/** A source with its comments blanked, the way the gate blanks them: a name in a comment is no code. `//` after `:` stays (`https://`). */
function withoutComments(source: string): string {
    const blank = (text: string, pattern: RegExp): string => text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
    return blank(blank(blank(source, /<!--[\s\S]*?-->/g), /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);
}

/**
 * The names a source imports from the module as values: `import {a, b as c, type D}` gives a and b, `import type {…}`
 * none, a namespace none — a page imports what it calls, by name.
 */
function valueImportsOf(code: string): string[] {
    return [...code.matchAll(MODULE_IMPORT)]
        .filter(([, typeOnly]) => !typeOnly)
        .flatMap(([, , clause]) =>
            (clause.match(/\{([^}]*)\}/)?.[1] ?? '')
                .split(',')
                .map((specifier) => specifier.trim())
                .filter((specifier) => specifier !== '' && !/^type\s/.test(specifier))
                .map((specifier) => specifier.split(/\s+as\s+/)[0]),
        );
}

/**
 * Whether `code` calls `name(` as itself: not a longer name, not a method of something (`other.name(`), but a spread of
 * its result is a call (`...name(`): a single `.` before the name is member access, three are a spread.
 */
const callsFunction = (code: string, name: string): boolean => new RegExp(`(?<![\\w$])(?<!(?<!\\.)\\.)${name}\\s*\\(`).test(code);

/** What keeps a detail page from drawing its signals through the module: the renderer functions not imported as values or not called, and the sources not built. */
function adoptionProblems(source: string): string[] {
    const code = withoutComments(source);
    const imported = valueImportsOf(code);
    const problems: string[] = [];
    for (const name of ['renderLocalSignals', 'renderBackendResults']) {
        if (!imported.includes(name)) problems.push(`${name} is not imported as a value from $lib/charts/chartSignalRendering`);
        else if (!callsFunction(code, name)) problems.push(`${name} is imported but never called`);
    }
    if (!callsFunction(code, 'detailPageSignalSources')) problems.push('detailPageSignalSources( is never called: the page does not hand the module its data sources');
    return problems;
}

/** What keeps the FX detail page on its own point converter: a declaration of its own, or no import of the module’s. */
function converterProblems(source: string): string[] {
    const code = withoutComments(source);
    const problems: string[] = [];
    if (/\bfunction\s+fxPointToLineDataPoint\s*\(|\b(?:const|let|var)\s+fxPointToLineDataPoint\b/.test(code)) problems.push('declares its own fxPointToLineDataPoint');
    if (!valueImportsOf(code).includes('fxPointToLineDataPoint')) problems.push('does not import fxPointToLineDataPoint from $lib/charts/chartSignalRendering');
    return problems;
}

/** The finding list as the failure message gives it: the rule, how many, then each one. */
const listed = (page: string, what: string, problems: readonly string[]): string => ['', `The ${page} page ${what} (Y-42). ${problems.length} finding(s):`, '', ...problems, ''].join('\n  ');

describe('the detail pages draw their saved signals through lib/charts/chartSignalRendering.ts (Y-42 adoption)', () => {
    it.each(DETAIL_PAGES)('the %s page imports renderLocalSignals and renderBackendResults as values, calls them, and calls detailPageSignalSources(', (page, path) => {
        const problems = adoptionProblems(readFileSync(path, 'utf8'));

        expect(problems, listed(page, 'still draws its signals with a loop of its own: build its data sources with detailPageSignalSources(…) and draw through renderLocalSignals and renderBackendResults', problems)).toEqual([]);
    });

    it('the FX detail page keeps no fxPointToLineDataPoint of its own, and imports the module’s', () => {
        const [page, path] = DETAIL_PAGES[1];
        const problems = converterProblems(readFileSync(path, 'utf8'));

        expect(problems, listed(page, 'converts the FX store points with a converter of its own: import fxPointToLineDataPoint from the module', problems)).toEqual([]);
    });

    describe('the forms read what they claim (controls)', () => {
        const ADOPTED = [
            "import {renderLocalSignals, renderBackendResults, type SignalDataSources} from '$lib/charts/chartSignalRendering';",
            "import {detailPageSignalSources} from '$lib/charts/chartPageSignals';",
            'const sources = detailPageSignalSources({configs, assets, fxPairPoints});',
            'const local = renderLocalSignals(signals, definitions, lineData, viewMode, sources);',
            'const backend = renderBackendResults(signals, results, definitions, lineData, viewMode, translate);',
        ].join('\n');

        it('pass a page that imports, calls and builds', () => {
            expect(adoptionProblems(ADOPTED)).toEqual([]);
            // A call whose result is spread is a call: `...renderLocalSignals(` has a `.` before the name, three of them.
            expect(adoptionProblems(ADOPTED.replace('const local = renderLocalSignals(signals, definitions, lineData, viewMode, sources);', 'const all = [...renderLocalSignals(signals, definitions, lineData, viewMode, sources), ...extra];'))).toEqual([]);
            expect(adoptionProblems(ADOPTED.replace('const backend = renderBackendResults(signals, results, definitions, lineData, viewMode, translate);', 'const all = [...renderBackendResults(signals, results, definitions, lineData, viewMode, translate)];'))).toEqual([]);
            expect(adoptionProblems(ADOPTED.replace('{renderLocalSignals, renderBackendResults, type SignalDataSources}', '{\n    type SignalDataSources,\n    renderLocalSignals,\n    renderBackendResults,\n}'))).toEqual([]);
        });

        it('fail a type-only import, an import never called, a call only in a comment, and a page that builds no sources', () => {
            const typeOnly = ADOPTED.replace('import {renderLocalSignals, renderBackendResults, type SignalDataSources}', 'import type {renderLocalSignals, renderBackendResults}');
            expect(adoptionProblems(typeOnly).map((problem) => problem.split(' ')[0])).toEqual(['renderLocalSignals', 'renderBackendResults']);

            expect(adoptionProblems(ADOPTED.replace('const local = renderLocalSignals(signals, definitions, lineData, viewMode, sources);', ''))).toEqual(['renderLocalSignals is imported but never called']);
            expect(adoptionProblems(ADOPTED.replace('const backend = renderBackendResults(signals, results, definitions, lineData, viewMode, translate);', '// const backend = renderBackendResults(signals);'))).toEqual(['renderBackendResults is imported but never called']);
            // A method of something else is no call of the function: a single `.` before the name.
            expect(adoptionProblems(ADOPTED.replace('const local = renderLocalSignals(signals, definitions, lineData, viewMode, sources);', 'const local = other.renderLocalSignals(signals);'))).toEqual(['renderLocalSignals is imported but never called']);
            expect(adoptionProblems(ADOPTED.replace('const backend = renderBackendResults(signals, results, definitions, lineData, viewMode, translate);', 'const backend = other.renderBackendResults(signals);'))).toEqual(['renderBackendResults is imported but never called']);
            expect(adoptionProblems(ADOPTED.replace('const sources = detailPageSignalSources({configs, assets, fxPairPoints});', '/* const sources = detailPageSignalSources({}); */\nconst sources = other.detailPageSignalSources({});'))).toHaveLength(1);
        });

        it('see a converter of its own in either form, and an import of the module’s in a clause of several names', () => {
            const imported = "import {fxPointToLineDataPoint, renderLocalSignals} from '$lib/charts/chartSignalRendering';";

            expect(converterProblems(imported)).toEqual([]);
            expect(converterProblems(`${imported}\nfunction fxPointToLineDataPoint(point, inverted) {}`)).toEqual(['declares its own fxPointToLineDataPoint']);
            expect(converterProblems(`${imported}\nconst fxPointToLineDataPoint = (point) => point;`)).toEqual(['declares its own fxPointToLineDataPoint']);
            expect(converterProblems(`${imported}\n// function fxPointToLineDataPoint(point) {}`)).toEqual([]);
            expect(converterProblems("import {renderLocalSignals} from '$lib/charts/chartSignalRendering';\nfunction fxPointToLineDataPoint(point) {}")).toHaveLength(2);
        });
    });
});
