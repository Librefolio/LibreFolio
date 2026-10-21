/**
 * chartSignalRendering — the one renderer of a chart's saved signals (lot Y-39a, «parity between the card and the preview»).
 *
 * ## Why
 *
 * Until Y-39a the loop «definition → `signalFromConfig` → inject the FX pair or the comparison data → `renderMulti`, then
 * the backend results» is written five times: the asset list's and the FX list's `getRenderedSignals` (the cards), the
 * settings preview's `renderLocalPreview` (`ChartSettingsModal`), and the two detail pages — another workstream's files,
 * which adopt the module later (Y-42). Card and preview were born as one component and drifted apart:
 *   - the card names a comparison after its target, the preview calls it «Asset #id»;
 *   - the card skips a comparison with its own asset, the preview draws it (decision: skip in both);
 *   - the card hands an FX pair the pair's straight rates and lets the signal's own `_inverted` turn them, the FX-list
 *     preview hands it rates already turned by each pair's own card (decision: as the card);
 *   - the converter «FX store point → chart point» is written three times.
 * Y-39a moves the loop into `lib/charts/chartSignalRendering.ts`: a pure module — no Svelte state, no store read inside,
 * the caller passes its data sources — that the cards and the preview call with the same sources, keeping the best of
 * the copies. The parity comes by construction.
 *
 * ## The contract, as the cases below pin it
 *
 * 1. `fxPointToLineDataPoint(point, inverted)`: `value` is `displayFxRate(rate, inverted) ?? 0`, `missing` says that rate
 *    is null, `staleDays` is the point's backward-fill days (0 without), `date` is kept — the FX list's converter.
 * 2. `renderLocalSignal(config, baseData, viewMode, sources)`: the signal `signalFromConfig(config)` rebuilds, none → `[]`.
 *    - `fx-pair`: no slug, or no data from `sources.fxPairData(slug)` → `[]`; else that data, straight: the signal's own
 *      `_inverted` turns it.
 *    - `asset-comparison`: `Number(assetId)` 0 or NaN, or the chart's own `sources.selfAssetId` → `[]`;
 *      `sources.comparisonTarget(id)` null or without data → `[]`; else its data, and its display name, icon, type and
 *      base point, each only when given.
 *    - then `renderMulti(baseData, viewMode)`, the results with data only; the config is never written into.
 * 3. `renderLocalSignals(configs, definitionsByType, …)`: `renderLocalSignal` over the configs, in their order, skipping
 *    those with no definition and those whose definition is backend-owned.
 * 4. `renderBackendResults(configs, results, definitionsByType, baseData, viewMode, translate?)`: in the results' order,
 *    each backend item with a result, drawn by `renderBackendSignalResult` with the CURRENT config of its id (else the
 *    item's own config) and that config's backend definition; anything else is skipped.
 *
 * Two readings this file settles, where the contract's words leave room:
 *   - «each only when given»: what the target does not give is not written, so a name, an icon or a type the saved config
 *     already carries (the runtime params a detail page writes back, `COMPARISON_ASSET_RUNTIME_PARAM_KEYS`) stays; what
 *     the target gives wins over it. With neither, the signal's own catalogue fallback names it.
 *   - «its definition» is the definition of the config the item is drawn with — the current one when there is one.
 *
 * ## Red until the cure
 *
 * The module does not exist yet. It is loaded by a computed specifier (`exported()`), so each case fails on its own —
 * «cannot be loaded — red until Y-39a creates it» — instead of the whole file at import, and everything a case builds
 * before loading it runs today: a red here is the missing module, not a broken fixture. The contract's types are written
 * out below for the same reason: the type check does not wait for the module.
 *
 * The names a signal gives itself before the page names it come from the catalogue (`ChartSignal.text`), which throws
 * before svelte-i18n is initialised: the file boots it once, in English, and compares a fallback with the catalogue's own
 * text for its key, never with a literal. «Synthetic peer» and the other names below are data the cases inject.
 *
 * Registered (to be) in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`), beside
 * `chartPageSignals.test.ts`.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

import {setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import {getRegisteredSignalTypes, type RenderedSignal, type SignalConfig, type SignalDefinition, type SignalStyle} from '$lib/charts/signals';
import {renderBackendSignalResult} from '$lib/charts/signals/backendRenderer';
import {backendSignalSchemas, type BackendSignalResult} from '$lib/charts/signals/backendTypes';
import type {SignalInstanceResult} from '$lib/charts/signals/resultMapper';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {displayFxRate} from '$lib/stores/fxStoreRegistry';
import {extractDaysBack} from '$lib/utils/assetPriceDerived';

// ---------------------------------------------------------------------------
// The contract's types, written out: the module does not exist yet
// ---------------------------------------------------------------------------

type ViewMode = 'absolute' | 'percentage';

/** An FX store point, as `fxPointToLineDataPoint` reads it (`FxDataPoint` of `$lib/stores/fxStoreRegistry`). */
interface FxStorePoint {
    date: string;
    rate: number | null;
    backwardFillInfo?: {actualRateDate?: string; daysBack: number} | null;
}

interface ComparisonTarget {
    data: LineDataPoint[];
    displayName?: string | null;
    iconUrl?: string | null;
    assetType?: string | null;
    basePoint?: LineDataPoint | null;
}

interface SignalDataSources {
    fxPairData: (pairSlug: string) => LineDataPoint[] | null;
    comparisonTarget: (assetId: number) => ComparisonTarget | null;
    selfAssetId?: number | null;
}

/** `lib/charts/chartSignalRendering.ts`, as Y-39a specifies it. */
interface ChartSignalRendering {
    fxPointToLineDataPoint(point: FxStorePoint, inverted: boolean): LineDataPoint;
    renderLocalSignal(config: SignalConfig, baseData: LineDataPoint[], viewMode: ViewMode, sources: SignalDataSources): RenderedSignal[];
    renderLocalSignals(configs: readonly SignalConfig[], definitionsByType: ReadonlyMap<string, SignalDefinition>, baseData: LineDataPoint[], viewMode: ViewMode, sources: SignalDataSources): RenderedSignal[];
    renderBackendResults(configs: readonly SignalConfig[], results: readonly SignalInstanceResult[], definitionsByType: ReadonlyMap<string, SignalDefinition>, baseData: LineDataPoint[], viewMode: ViewMode, translate?: (key: string) => string): RenderedSignal[];
}

const MODULE_FILE = 'src/lib/charts/chartSignalRendering.ts';
/** Computed, so that a missing module fails the case that loads it, not the whole file at import. */
const MODULE_SPECIFIER = '../chartSignalRendering';

/** One export of the module, loaded when the case needs it. */
async function exported<K extends keyof ChartSignalRendering>(name: K): Promise<ChartSignalRendering[K]> {
    let loaded: Record<string, unknown>;
    try {
        loaded = (await import(/* @vite-ignore */ MODULE_SPECIFIER)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`${MODULE_FILE} cannot be loaded — red until Y-39a creates it: ${String(error)}`);
    }
    expect(typeof loaded[name], `${MODULE_FILE} exports no ${name}()`).toBe('function');
    return loaded[name] as ChartSignalRendering[K];
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/**
 * svelte-i18n throws when it formats a message before it is initialised, and a signal's fallback name is a formatted
 * message: boot it once for the whole file, in English, the app's fallback.
 */
beforeAll(async () => {
    await setupI18n('en');
});

/** A catalogue message with its values, as the interface language words it. */
function catalogue(key: string, values: Record<string, string> = {}): string {
    return get(_)(key, {values});
}

const STYLE: SignalStyle = {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null};

/** The four days the chart draws: the base data of every local signal below. */
const CHART: LineDataPoint[] = [
    {date: '2026-03-02', value: 100},
    {date: '2026-03-03', value: 110},
    {date: '2026-03-04', value: 120},
    {date: '2026-03-05', value: 130},
];
const CHART_DATES = CHART.map((point) => point.date);

/** EUR-GBP as the FX store holds it, straight: a day before the chart, and no rate on 03-05. */
const EUR_GBP: LineDataPoint[] = [
    {date: '2026-02-27', value: 0.4},
    {date: '2026-03-02', value: 0.5},
    {date: '2026-03-03', value: 0.8},
    {date: '2026-03-04', value: 0.625},
];
/** The days of the chart EUR-GBP has a rate for. */
const EUR_GBP_DATES = ['2026-03-02', '2026-03-03', '2026-03-04'];

/** Asset 42, the comparison's target: a day before the chart and one after it, and no price on 03-04. */
const PEER_ID = 42;
const PEER_NAME = 'Synthetic peer';
const PEER: LineDataPoint[] = [
    {date: '2026-02-27', value: 190},
    {date: '2026-03-02', value: 200},
    {date: '2026-03-03', value: 220},
    {date: '2026-03-05', value: 180},
    {date: '2026-03-06', value: 240},
];
/** The days of the chart asset 42 has a price for. */
const PEER_DATES = ['2026-03-02', '2026-03-03', '2026-03-05'];

function signalConfig(id: string, signalType: string, params: Record<string, unknown> = {}, style: SignalStyle = STYLE): SignalConfig {
    return {id, signalType, params, style: {...style}};
}

const fxPair = (params: Record<string, unknown> = {}): SignalConfig => signalConfig('fx-eur-gbp', 'fx-pair', {pairSlug: 'EUR-GBP', ...params});
const comparison = (params: Record<string, unknown> = {}): SignalConfig => signalConfig('cmp-42', 'asset-comparison', {assetId: PEER_ID, ...params});
const linear = (): SignalConfig => signalConfig('lin-1', 'linear', {annualRate: 2, offset: 0});

/** Sources that know the pair EUR-GBP and the asset 42, and nothing else — each a spy. */
function sourcesWith(target: ComparisonTarget | null = {data: PEER, displayName: PEER_NAME}, selfAssetId?: number | null) {
    return {
        fxPairData: vi.fn((pairSlug: string): LineDataPoint[] | null => (pairSlug === 'EUR-GBP' ? EUR_GBP : null)),
        comparisonTarget: vi.fn((assetId: number): ComparisonTarget | null => (assetId === PEER_ID ? target : null)),
        ...(selfAssetId === undefined ? {} : {selfAssetId}),
    } satisfies SignalDataSources;
}

/** To 9 decimals, -0 read as 0: what the cases compare, so that a float's last bit never decides. */
const round = (value: number): number => Number(value.toFixed(9)) + 0;
const datesOf = (signal: RenderedSignal | undefined): string[] => (signal?.data ?? []).map((point) => point.date);
const valuesOf = (signal: RenderedSignal | undefined): number[] => (signal?.data ?? []).map((point) => round(point.value));

/** A config frozen to its leaves: writing into it throws, in the module's strict code. */
function frozen<T>(value: T): T {
    if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
        Object.freeze(value);
        for (const child of Object.values(value)) frozen(child);
    }
    return value;
}

const LOCAL_DEFINITIONS = getRegisteredSignalTypes();

/** A backend indicator with one line output, `sma`, as the catalogue maps it. */
const SMA_DEFINITION: SignalDefinition = {
    type: 'sma',
    displayName: 'SMA',
    icon: 'activity',
    category: 'indicator',
    paramDescriptors: [],
    source: 'backend',
    visualComponents: [
        {
            key: 'sma',
            labelKey: 'signals.sma',
            kind: 'line',
            aggregationProfile: 'last_with_range',
            style: {colorRole: 'primary', lineWidthDelta: 0, opacity: 1, fillOpacity: 0.2},
            fullyPartitioned: false,
        },
    ],
};

/** The definitions by type: every local one, then `extra` — a later one of the same type replaces the earlier. */
function definitionsWith(...extra: SignalDefinition[]): ReadonlyMap<string, SignalDefinition> {
    return new Map([...LOCAL_DEFINITIONS, ...extra].map((definition) => [definition.type, definition]));
}

/** A saved backend result of `sma`, on the chart's days, parsed by the signal result schema as the client parses it. */
function smaResult(instanceId: string, values: readonly number[]): BackendSignalResult {
    return backendSignalSchemas.result.parse({
        instance_id: instanceId,
        signal_code: 'SMA',
        status: 'ok',
        series: [
            {
                key: 'sma',
                label_key: 'signals.sma',
                semantic_id: 'test.sma',
                semantic_description: 'Canonical test output for sma.',
                unit: 'price',
                axis: {key: 'price', role: 'price'},
                view_transform: 'base_percentage',
                kind: 'line',
                points: values.map((value, index) => ({date: CHART[index].date, value})),
            },
        ],
    });
}

const SMA_1_RESULT = smaResult('sma-1', [101, 104, 108, 113]);
const SMA_2_RESULT = smaResult('sma-2', [99, 103, 107, 111]);

/** An item of `mapSignalInstanceResults`, as a page keeps it between two requests. */
function resultItem(config: SignalConfig, result: BackendSignalResult | null, source: SignalInstanceResult['source'] = 'backend'): SignalInstanceResult {
    return {config, source, status: result?.status ?? (source === 'local' ? 'local' : 'missing'), result, error: null};
}

/** What `renderBackendSignalResult` draws for one result, with one config: the oracle of rule 4. */
function backendSignals(result: BackendSignalResult, config: SignalConfig, viewMode: ViewMode, translate?: (key: string) => string): RenderedSignal[] {
    return renderBackendSignalResult(result, config, {baseData: CHART, viewMode, definition: SMA_DEFINITION, translate}).signals;
}

// ---------------------------------------------------------------------------
// Rule 1 — the converter
// ---------------------------------------------------------------------------

describe('fxPointToLineDataPoint: an FX store point as a chart point — its value, its gap, its staleness (rule 1)', () => {
    it('keeps the date and the rate, with no gap and no staleness', async () => {
        const fxPointToLineDataPoint = await exported('fxPointToLineDataPoint');

        expect(fxPointToLineDataPoint({date: '2026-03-02', rate: 0.5, backwardFillInfo: null}, false)).toEqual({date: '2026-03-02', value: 0.5, missing: false, staleDays: 0});
    });

    it('inverted, the value is the reciprocal of the rate', async () => {
        const fxPointToLineDataPoint = await exported('fxPointToLineDataPoint');

        expect(fxPointToLineDataPoint({date: '2026-03-02', rate: 0.5, backwardFillInfo: null}, true)).toEqual({date: '2026-03-02', value: 2, missing: false, staleDays: 0});
    });

    it.each([
        {label: 'no rate', rate: null, inverted: false},
        {label: 'no rate, inverted', rate: null, inverted: true},
        {label: 'a rate of 0, which displayFxRate refuses', rate: 0, inverted: false},
        {label: 'a rate of 0, inverted', rate: 0, inverted: true},
    ])('$label is a gap: value 0, missing', async ({rate, inverted}) => {
        const fxPointToLineDataPoint = await exported('fxPointToLineDataPoint');

        expect(fxPointToLineDataPoint({date: '2026-03-04', rate, backwardFillInfo: null}, inverted)).toEqual({date: '2026-03-04', value: 0, missing: true, staleDays: 0});
    });

    it('a backward-filled rate keeps its staleness: staleDays is its days back, 0 without backward-fill info', async () => {
        const fxPointToLineDataPoint = await exported('fxPointToLineDataPoint');

        expect(fxPointToLineDataPoint({date: '2026-03-02', rate: 0.5, backwardFillInfo: {actualRateDate: '2026-02-27', daysBack: 3}}, false)).toEqual({date: '2026-03-02', value: 0.5, missing: false, staleDays: 3});
        expect(fxPointToLineDataPoint({date: '2026-03-02', rate: 0.5}, true), 'a point with no backward-fill info at all').toEqual({date: '2026-03-02', value: 2, missing: false, staleDays: 0});
    });

    it('gives the FX list’s own point in every case: displayFxRate for the value and the gap, extractDaysBack for the staleness', async () => {
        const fxPointToLineDataPoint = await exported('fxPointToLineDataPoint');
        const points: FxStorePoint[] = [
            {date: '2026-03-02', rate: 0.5, backwardFillInfo: null},
            {date: '2026-03-03', rate: 1.25, backwardFillInfo: {actualRateDate: '2026-03-01', daysBack: 2}},
            {date: '2026-03-04', rate: null, backwardFillInfo: {actualRateDate: '2026-02-27', daysBack: 5}},
            {date: '2026-03-05', rate: 0, backwardFillInfo: null},
            {date: '2026-03-06', rate: 0.8},
        ];

        for (const point of points) {
            for (const inverted of [false, true]) {
                const rate = displayFxRate(point.rate, inverted);
                expect(fxPointToLineDataPoint(point, inverted), `${JSON.stringify(point)}, inverted: ${inverted}`).toEqual({date: point.date, value: rate ?? 0, missing: rate === null, staleDays: extractDaysBack(point)});
            }
        }
    });
});

// ---------------------------------------------------------------------------
// Rule 2 — one local signal
// ---------------------------------------------------------------------------

describe('renderLocalSignal — an FX pair: the straight rates its source gives, turned by the signal’s own _inverted (rule 2)', () => {
    it('draws the rates sources.fxPairData gives for its slug, straight, on the days the chart draws', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');
        const sources = sourcesWith();

        const signals = renderLocalSignal(fxPair(), CHART, 'absolute', sources);

        expect(sources.fxPairData).toHaveBeenCalledWith('EUR-GBP');
        expect(signals.map((signal) => signal.id)).toEqual(['fx-eur-gbp']);
        expect(datesOf(signals[0])).toEqual(EUR_GBP_DATES);
        expect(valuesOf(signals[0]), 'not the straight rates of EUR-GBP').toEqual([0.5, 0.8, 0.625]);
    });

    it('with the signal’s own _inverted, draws their reciprocals: the module hands the rates over straight and turns them nowhere else', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');

        const signals = renderLocalSignal(fxPair({_inverted: true}), CHART, 'absolute', sourcesWith());

        expect(datesOf(signals[0])).toEqual(EUR_GBP_DATES);
        expect(valuesOf(signals[0]), 'not the reciprocals of 0.5, 0.8 and 0.625').toEqual([2, 1.25, 1.6]);
    });

    it('in the percentage view, measures the pair from its own first rate', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');

        const signals = renderLocalSignal(fxPair(), CHART, 'percentage', sourcesWith());

        expect(valuesOf(signals[0]), '0.5 → 0.8 → 0.625 from 0.5').toEqual([0, 60, 25]);
    });

    it.each([
        {label: 'an empty slug', params: {pairSlug: ''}},
        {label: 'no slug', params: {pairSlug: undefined}},
        {label: 'a pair the source has no data for', params: {pairSlug: 'USD-JPY'}},
    ])('draws nothing for $label', async ({params}) => {
        const renderLocalSignal = await exported('renderLocalSignal');

        expect(renderLocalSignal(fxPair(params), CHART, 'absolute', sourcesWith())).toEqual([]);
    });

    it('draws nothing when the source gives the pair an empty series', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');
        const sources: SignalDataSources = {...sourcesWith(), fxPairData: vi.fn(() => [])};

        expect(renderLocalSignal(fxPair(), CHART, 'absolute', sources)).toEqual([]);
    });
});

describe('renderLocalSignal — a comparison: its target’s data, name, icon, type and base point; never the chart’s own asset (rule 2)', () => {
    it('draws the target’s data on the days the chart draws, named after the target', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');
        const sources = sourcesWith();

        const signals = renderLocalSignal(comparison(), CHART, 'absolute', sources);

        expect(sources.comparisonTarget).toHaveBeenCalledWith(PEER_ID);
        expect(signals.map((signal) => signal.id)).toEqual(['cmp-42']);
        expect(signals[0].label, 'the comparison is not named after its target').toBe(PEER_NAME);
        expect(datesOf(signals[0])).toEqual(PEER_DATES);
        expect(valuesOf(signals[0])).toEqual([200, 220, 180]);
    });

    it('reads the saved asset id as a number: a numeric string asks for the same target', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');
        const sources = sourcesWith();

        const signals = renderLocalSignal(comparison({assetId: '42'}), CHART, 'absolute', sources);

        expect(sources.comparisonTarget).toHaveBeenCalledWith(PEER_ID);
        expect(signals.map((signal) => signal.label)).toEqual([PEER_NAME]);
    });

    it.each([
        {label: 'no display name', target: {data: PEER}},
        {label: 'a null display name', target: {data: PEER, displayName: null}},
    ])('with $label, keeps the signal’s own catalogue fallback for asset 42', async ({target}) => {
        const renderLocalSignal = await exported('renderLocalSignal');

        const signals = renderLocalSignal(comparison(), CHART, 'absolute', sourcesWith(target));

        expect(signals.map((signal) => signal.label)).toEqual([catalogue('chartSettings.signals.assetFallback', {id: '42'})]);
    });

    it('hands the target’s icon and type to the drawn signal', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');

        const signals = renderLocalSignal(comparison(), CHART, 'absolute', sourcesWith({data: PEER, displayName: PEER_NAME, iconUrl: '/icons/peer.png', assetType: 'ETF'}));

        expect(signals.map((signal) => ({iconUrl: signal.iconUrl, assetType: signal.assetType}))).toEqual([{iconUrl: '/icons/peer.png', assetType: 'ETF'}]);
    });

    it('writes only what the target gives: a name, an icon and a type the saved config carries stay when the target has none, and give way to the target’s own', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');
        const saved = comparison({_assetDisplayName: 'Name saved with the config', _assetIconUrl: '/icons/saved.png', _assetType: 'STOCK'});

        const bare = renderLocalSignal(saved, CHART, 'absolute', sourcesWith({data: PEER}));
        const named = renderLocalSignal(saved, CHART, 'absolute', sourcesWith({data: PEER, displayName: PEER_NAME, iconUrl: '/icons/peer.png', assetType: 'ETF'}));

        expect(
            bare.map((signal) => ({label: signal.label, iconUrl: signal.iconUrl, assetType: signal.assetType})),
            'a target with no name, icon or type wrote over the saved ones',
        ).toEqual([{label: 'Name saved with the config', iconUrl: '/icons/saved.png', assetType: 'STOCK'}]);
        expect(
            named.map((signal) => ({label: signal.label, iconUrl: signal.iconUrl, assetType: signal.assetType})),
            'the target’s own name, icon and type do not win',
        ).toEqual([{label: PEER_NAME, iconUrl: '/icons/peer.png', assetType: 'ETF'}]);
    });

    it('measures the percentage line from the target’s base point when one is given (Z-29d-0), from its own first point otherwise', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');

        const fromBase = renderLocalSignal(comparison(), CHART, 'percentage', sourcesWith({data: PEER, displayName: PEER_NAME, basePoint: {date: '2026-02-27', value: 160}}));
        const fromFirst = renderLocalSignal(comparison(), CHART, 'percentage', sourcesWith());

        expect(valuesOf(fromBase[0]), '200, 220 and 180 measured from the base point, 160').toEqual([25, 37.5, 12.5]);
        expect(valuesOf(fromFirst[0]), '200, 220 and 180 measured from the first, 200').toEqual([0, 10, -10]);
    });

    it.each([
        {label: 'its id saved as a number', assetId: 42},
        {label: 'its id saved as a numeric string', assetId: '42'},
    ])('never draws a comparison with the chart’s own asset ($label)', async ({assetId}) => {
        const renderLocalSignal = await exported('renderLocalSignal');

        expect(renderLocalSignal(comparison({assetId}), CHART, 'absolute', sourcesWith(undefined, PEER_ID))).toEqual([]);
    });

    it.each([
        {label: 'another asset', selfAssetId: 7},
        {label: 'no asset (null)', selfAssetId: null},
        {label: 'no asset (absent)', selfAssetId: undefined},
    ])('draws the comparison on a chart whose own asset is $label', async ({selfAssetId}) => {
        const renderLocalSignal = await exported('renderLocalSignal');

        expect(renderLocalSignal(comparison(), CHART, 'absolute', sourcesWith(undefined, selfAssetId)).map((signal) => signal.label)).toEqual([PEER_NAME]);
    });

    it.each([
        {label: 'an asset id of 0', params: {assetId: 0}},
        {label: 'an empty asset id', params: {assetId: ''}},
        {label: 'an asset id that is not a number', params: {assetId: 'peer'}},
        {label: 'no asset id', params: {assetId: undefined}},
        {label: 'a target the source does not know', params: {assetId: 43}},
    ])('draws nothing for $label', async ({params}) => {
        const renderLocalSignal = await exported('renderLocalSignal');

        expect(renderLocalSignal(comparison(params), CHART, 'absolute', sourcesWith())).toEqual([]);
    });

    it.each([
        {label: 'no data', target: {data: [], displayName: PEER_NAME}},
        {
            label: 'no price on a day the chart draws',
            target: {
                data: [
                    {date: '2026-02-27', value: 190},
                    {date: '2026-03-06', value: 240},
                ],
                displayName: PEER_NAME,
            },
        },
    ])('draws nothing for a target with $label', async ({target}) => {
        const renderLocalSignal = await exported('renderLocalSignal');

        expect(renderLocalSignal(comparison(), CHART, 'absolute', sourcesWith(target))).toEqual([]);
    });
});

describe('renderLocalSignal — any other local signal: the chart’s data alone (rule 2)', () => {
    it('a linear benchmark draws on every day of the chart, and asks no source', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');
        const sources = sourcesWith();

        const signals = renderLocalSignal(linear(), CHART, 'absolute', sources);

        expect(signals.map((signal) => signal.id)).toEqual(['lin-1']);
        expect(datesOf(signals[0])).toEqual(CHART_DATES);
        expect(sources.fxPairData).not.toHaveBeenCalled();
        expect(sources.comparisonTarget).not.toHaveBeenCalled();
    });

    it('a type the local registry does not know draws nothing', async () => {
        const renderLocalSignal = await exported('renderLocalSignal');

        expect(renderLocalSignal(signalConfig('sma-1', 'sma', {window: 2}), CHART, 'absolute', sourcesWith())).toEqual([]);
    });
});

describe('renderLocalSignal — never writes into the config it draws (rule 2)', () => {
    it.each([
        {label: 'an FX pair', build: () => fxPair({_inverted: true})},
        {label: 'a comparison', build: () => comparison({assetId: '42'})},
        {label: 'a linear benchmark', build: linear},
    ])('leaves the config of $label, its params and its style as they were', async ({build}) => {
        const renderLocalSignal = await exported('renderLocalSignal');
        const config = frozen(build());
        const before: unknown = JSON.parse(JSON.stringify(config));
        const target: ComparisonTarget = {data: PEER, displayName: PEER_NAME, iconUrl: '/icons/peer.png', assetType: 'ETF', basePoint: {date: '2026-02-27', value: 160}};

        let signals: RenderedSignal[] = [];
        expect(() => {
            signals = renderLocalSignal(config, CHART, 'percentage', sourcesWith(target));
        }, 'it writes into the config (frozen here, so a write throws)').not.toThrow();

        expect(signals.length, 'control: the signal is drawn').toBeGreaterThan(0);
        expect(config).toEqual(before);
    });
});

// ---------------------------------------------------------------------------
// Rule 3 — the local configs of a chart
// ---------------------------------------------------------------------------

describe('renderLocalSignals — the local configs of a chart, in their order (rule 3)', () => {
    it('draws each local config in order — skipping a backend one and one with no definition — as renderLocalSignal draws it', async () => {
        const renderLocalSignals = await exported('renderLocalSignals');
        const renderLocalSignal = await exported('renderLocalSignal');
        const configs = [comparison(), signalConfig('sma-1', 'sma', {window: 2}), linear(), signalConfig('mystery-1', 'mystery-signal'), fxPair()];

        const signals = renderLocalSignals(configs, definitionsWith(SMA_DEFINITION), CHART, 'absolute', sourcesWith());

        expect(signals.map((signal) => signal.id)).toEqual(['cmp-42', 'lin-1', 'fx-eur-gbp']);
        expect(signals, 'not the concatenation of renderLocalSignal').toEqual([comparison(), linear(), fxPair()].flatMap((config) => renderLocalSignal(config, CHART, 'absolute', sourcesWith())));
    });

    it('skips a config whose definition is backend-owned, even of a type the local registry could draw', async () => {
        const renderLocalSignals = await exported('renderLocalSignals');
        const localLinear = LOCAL_DEFINITIONS.find((definition) => definition.type === 'linear');
        if (!localLinear) throw new Error('premise: the local registry defines `linear`');

        const signals = renderLocalSignals([linear(), fxPair()], definitionsWith({...localLinear, source: 'backend'}), CHART, 'absolute', sourcesWith());

        expect(signals.map((signal) => signal.id)).toEqual(['fx-eur-gbp']);
    });

    it('a local definition the registry cannot rebuild draws nothing, and the next config still draws', async () => {
        const renderLocalSignals = await exported('renderLocalSignals');
        const phantom: SignalDefinition = {type: 'phantom', displayName: 'Phantom', icon: '?', category: 'benchmark', paramDescriptors: [], source: 'local'};

        const signals = renderLocalSignals([signalConfig('phantom-1', 'phantom'), linear()], definitionsWith(phantom), CHART, 'absolute', sourcesWith());

        expect(signals.map((signal) => signal.id)).toEqual(['lin-1']);
    });

    it('draws nothing for no configs', async () => {
        const renderLocalSignals = await exported('renderLocalSignals');

        expect(renderLocalSignals([], definitionsWith(SMA_DEFINITION), CHART, 'absolute', sourcesWith())).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// Rule 4 — the saved backend results
// ---------------------------------------------------------------------------

describe('renderBackendResults — the saved backend results, drawn with the current config (rule 4)', () => {
    const requested = signalConfig('sma-1', 'sma', {window: 2}, {...STYLE, color: '#111111'});
    const current = signalConfig('sma-1', 'sma', {window: 2}, {...STYLE, color: '#ff0000'});

    it('draws a result with the current config of its id: a colour changed since the request wins over the one saved with the result', async () => {
        const renderBackendResults = await exported('renderBackendResults');

        const signals = renderBackendResults([current], [resultItem(requested, SMA_1_RESULT)], definitionsWith(SMA_DEFINITION), CHART, 'absolute');

        expect(signals.length, 'control: the result is drawn').toBeGreaterThan(0);
        expect(
            signals.map((signal) => signal.color),
            'drawn in the colour of the request, not in the one of the settings now',
        ).toEqual(signals.map(() => '#ff0000'));
        expect(signals).toEqual(backendSignals(SMA_1_RESULT, current, 'absolute'));
    });

    it('draws a result with its own config when the current configs no longer hold its id', async () => {
        const renderBackendResults = await exported('renderBackendResults');

        const signals = renderBackendResults([signalConfig('other-1', 'sma')], [resultItem(requested, SMA_1_RESULT)], definitionsWith(SMA_DEFINITION), CHART, 'absolute');

        expect(signals.length, 'control: the result is drawn').toBeGreaterThan(0);
        expect(signals).toEqual(backendSignals(SMA_1_RESULT, requested, 'absolute'));
    });

    it('keeps the order of the results, and skips every item it cannot draw', async () => {
        const renderBackendResults = await exported('renderBackendResults');
        const sma2 = signalConfig('sma-2', 'sma', {window: 3}, {...STYLE, color: '#00aa00'});
        const items = [
            resultItem(linear(), null, 'local'), // a local signal: renderLocalSignals draws it
            resultItem(signalConfig('sma-3', 'sma'), null), // a backend item with no result
            resultItem(signalConfig('ghost-1', 'ghost-indicator'), SMA_1_RESULT), // no definition for its type
            resultItem(signalConfig('lin-2', 'linear'), SMA_1_RESULT), // a definition that is not backend-owned
            resultItem(signalConfig('gone-1', 'sma'), SMA_1_RESULT, 'unavailable'), // not a backend item
            resultItem(sma2, SMA_2_RESULT),
            resultItem(current, SMA_1_RESULT),
        ];

        const signals = renderBackendResults([current, sma2], items, definitionsWith(SMA_DEFINITION), CHART, 'absolute');

        expect(signals).toEqual([...backendSignals(SMA_2_RESULT, sma2, 'absolute'), ...backendSignals(SMA_1_RESULT, current, 'absolute')]);
    });

    it('looks the definition up by the config it draws with: a current config of a type with no backend definition is skipped', async () => {
        const renderBackendResults = await exported('renderBackendResults');
        const retyped = signalConfig('sma-1', 'linear', {annualRate: 2, offset: 0});

        expect(renderBackendResults([retyped], [resultItem(requested, SMA_1_RESULT)], definitionsWith(SMA_DEFINITION), CHART, 'absolute')).toEqual([]);
    });

    it('hands the view mode and translate to the backend renderer', async () => {
        const renderBackendResults = await exported('renderBackendResults');
        const translate = (key: string): string => (key === 'signals.sma' ? 'Label injected by the case' : key);

        const signals = renderBackendResults([current], [resultItem(current, SMA_1_RESULT)], definitionsWith(SMA_DEFINITION), CHART, 'percentage', translate);

        expect(signals).toEqual(backendSignals(SMA_1_RESULT, current, 'percentage', translate));
        expect(signals.map((signal) => signal.label)).toEqual(signals.map(() => 'Label injected by the case'));
        expect(valuesOf(signals[0]), '101, 104, 108 and 113 rebased on the chart’s first value, 100').toEqual([1, 4, 8, 13]);
    });
});
