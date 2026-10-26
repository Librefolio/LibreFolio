/**
 * Contract tests for the FX pairs the asset detail page needs and for the issues of its data-quality banner
 * (FE5c). Both functions are the page's former `requiredFxPairs` and `assetDetailIssues` `$derived.by`
 * blocks, moved verbatim; the page state they read became an `input`, which the page passes as an object of
 * getters.
 *
 * Two contracts are pinned:
 * - what they return: the pairs in their order (the asset's own, the comparison peers', the event
 *   currencies'), one per canonical slug, each with its status; and the banner's issues in their order;
 * - which state they read, and when. A `$derived` over them depends on what its getters read, so a key read
 *   under a new condition is a new dependency of the page: the chart data, for one, is read only while the
 *   asset's configured pair has no converted date. These cases pass the input through getters that record
 *   each key read, and assert on which keys, never on how many times.
 *
 * The events are shaped as the price query returns them (`FAAssetEventPointOut`), converted or left in
 * their own currency, as `getComparisonEventFxDependency` reads them.
 */
import {describe, expect, it} from 'vitest';
import type {SignalConfig, SignalProblem, SignalProblemCode} from '$lib/charts/signals';
import {buildAssetDetailIssues, buildRequiredFxPairs, type AssetDetailIssuesInput, type RequiredFxPairInfo, type RequiredFxPairsInput} from './assetDetailFxRequirements';

type PairStatus = RequiredFxPairInfo['status'];

/** The page's `forAsset` of the asset's own events, translated by the page. */
const EVENTS_LABEL = 'for the events of this asset';

const PAGE_ASSET_ID = 1;

/** The asset the page shows: in USD, so its pair against the EUR shown is EUR-USD. */
const PAGE_ASSET: NonNullable<RequiredFxPairsInput['asset']> = {display_name: 'Page Asset', currency: 'USD', icon_url: 'https://icons.test/page.png', asset_type: 'STOCK'};

/** Every asset of the user: the page's own, then the comparison peers. */
const ASSETS: RequiredFxPairsInput['assets'] = [
    {id: PAGE_ASSET_ID, display_name: 'Page Asset', currency: 'USD', icon_url: 'https://icons.test/page.png', asset_type: 'STOCK'},
    {id: 7, display_name: 'Swiss Peer', currency: 'CHF', icon_url: 'https://icons.test/swiss.png', asset_type: 'FUND'},
    {id: 8, display_name: 'Yen Peer', currency: 'JPY', icon_url: null, asset_type: 'ETF'},
    {id: 9, display_name: 'Euro Peer', currency: 'EUR'},
    {id: 10, display_name: 'Peer Without Currency'},
    {id: 11, display_name: 'Dollar Peer', currency: 'USD'},
    {id: 12, display_name: 'Second Swiss Peer', currency: 'CHF'},
];

/** What a comparison load writes back into its config once the peer's prices are in. */
const LOADED: Record<string, unknown> = {_resolvedData: [{date: '2026-02-02', value: 101.5}]};

/** The page showing EUR for its USD asset: prices loaded, no pair configured, no signal and no event. */
function pairsInput(overrides: Partial<RequiredFxPairsInput> = {}): RequiredFxPairsInput {
    return {
        displayCurrency: 'EUR',
        asset: PAGE_ASSET,
        pageAssetId: PAGE_ASSET_ID,
        configuredFxSlugs: [],
        fxFirstConvertedDate: null,
        hasChartData: true,
        hasFxDataGap: false,
        signals: [],
        assets: ASSETS,
        primaryMode: 'price',
        calendarSnapshotIsCurrent: true,
        calendarComparisonFxFailures: new Set<number>(),
        calendarComparisonProblems: new Map<number, SignalProblem>(),
        events: [],
        comparisonEvents: new Map<number, readonly unknown[]>(),
        eventsLabel: EVENTS_LABEL,
        assetFallbackLabel: (assetId) => `Asset #${assetId}`,
        ...overrides,
    };
}

/** A page loaded without error: an active asset, a range inside its data, no pair. */
function issuesInput(overrides: Partial<AssetDetailIssuesInput> = {}): AssetDetailIssuesInput {
    return {asset: {active: true}, rangeStartsBeforeData: false, loading: false, error: null, firstDataDate: '2025-03-03', requiredFxPairs: [], ...overrides};
}

/**
 * `values` behind getters, as the page passes its state, and the keys read so far: a getter records its key
 * when it is read, so a method records it when it is called.
 */
function recorded<T extends object>(values: T): {input: T; reads: Set<string>} {
    const reads = new Set<string>();
    const input = {} as T;
    for (const [key, value] of Object.entries(values)) {
        Object.defineProperty(input, key, {
            enumerable: true,
            get() {
                reads.add(key);
                return value;
            },
        });
    }
    return {input, reads};
}

function signalConfig(id: string, signalType: string, params: Record<string, unknown>): SignalConfig {
    return {id, signalType, params, style: {}} as unknown as SignalConfig;
}

/** A comparison with the asset `assetId`, with the runtime params its load wrote back, if any. */
function comparisonConfig(assetId: unknown, runtimeParams: Record<string, unknown> = {}): SignalConfig {
    return signalConfig(`cmp-${String(assetId)}`, 'asset-comparison', {assetId, ...runtimeParams});
}

/** A signal problem of `code`; the pairs read nothing else of it. */
function signalProblem(code: SignalProblemCode): SignalProblem {
    return {
        code,
        status: 'unavailable',
        missingPriceFields: [],
        missingEventTypes: [],
        fieldCoverage: {},
        availablePoints: null,
        requestedPoints: null,
        minimumPoints: null,
        warmupUsedPoints: null,
        warmupRequiredPoints: null,
        missingPoints: null,
        maxConsecutiveMissingPoints: null,
        coverageRatio: null,
        coveragePercent: null,
        selectedStartDate: null,
        selectedEndDate: null,
        excludedPoints: null,
        unavailablePoints: null,
        unavailableStart: null,
        unavailableEnd: null,
        resyncStart: null,
        resyncEnd: null,
        message: null,
    };
}

/** A dividend as the price query returns it, worth `value`. */
function dividend(value: {code: string; amount: string}, extra: Record<string, unknown> = {}): Record<string, unknown> {
    return {date: '2026-01-15', type: 'DIVIDEND', value, notes: null, id: 501, is_auto: false, ...extra};
}

/** A dividend in `source` that the backend converted to the EUR shown: it keeps its original value. */
function convertedDividend(source: string): Record<string, unknown> {
    return dividend({code: 'EUR', amount: '0.92'}, {original_value: {code: source, amount: '1.00'}, fx_info: {fx_rate_date: '2026-01-15', fx_days_back: 0}});
}

/** A dividend in `source` that the backend could not convert to the EUR shown: it stays in its own currency. */
function unconvertedDividend(source: string): Record<string, unknown> {
    return dividend({code: source, amount: '1.00'});
}

/** The asset's own pair, EUR-USD, as the page lists it. */
function assetPair(status: PairStatus, firstDate?: string): RequiredFxPairInfo {
    return {slug: 'EUR-USD', label: 'EUR/USD', forAsset: 'Page Asset', forAssetIconUrl: 'https://icons.test/page.png', forAssetType: 'STOCK', status, firstDate};
}

/** A pair the page needs, as the issues read it. */
function requiredPair(slug: string, status: PairStatus, forAsset: string, firstDate?: string): RequiredFxPairInfo {
    return {slug, label: slug.replace('-', '/'), forAsset, status, firstDate};
}

/** Each pair as `slug status`, in order. */
function summary(pairs: readonly RequiredFxPairInfo[]): string[] {
    return pairs.map((pair) => `${pair.slug} ${pair.status}`);
}

function statusOf(pairs: readonly RequiredFxPairInfo[], slug: string): PairStatus | undefined {
    return pairs.find((pair) => pair.slug === slug)?.status;
}

describe('buildRequiredFxPairs: the asset’s own pair first, named by its canonical slug, with its status', () => {
    it('names a pair by its two currencies in alphabetical order joined by a dash, and labels it with a slash', () => {
        expect(buildRequiredFxPairs(pairsInput()).map(({slug, label}) => `${slug} ${label}`)).toEqual(['EUR-USD EUR/USD']);
        expect(buildRequiredFxPairs(pairsInput({asset: {...PAGE_ASSET, currency: 'CHF'}})).map(({slug, label}) => `${slug} ${label}`)).toEqual(['CHF-EUR CHF/EUR']);
    });

    it.each<{label: string; configured: boolean; fxFirstConvertedDate: string | null; hasChartData: boolean; hasFxDataGap: boolean; status: PairStatus}>([
        {label: 'its pair is not configured', configured: false, fxFirstConvertedDate: null, hasChartData: true, hasFxDataGap: false, status: 'missing'},
        {label: 'nothing converts while there are prices', configured: true, fxFirstConvertedDate: null, hasChartData: true, hasFxDataGap: true, status: 'no-data'},
        {label: 'nothing converts and there is no price', configured: true, fxFirstConvertedDate: null, hasChartData: false, hasFxDataGap: false, status: 'ok'},
        {label: 'conversion starts after the first price', configured: true, fxFirstConvertedDate: '2026-01-05', hasChartData: true, hasFxDataGap: true, status: 'partial-gap'},
        {label: 'conversion starts with the first price', configured: true, fxFirstConvertedDate: '2026-01-05', hasChartData: true, hasFxDataGap: false, status: 'ok'},
    ])('is $status, with its first converted date, when $label', ({configured, fxFirstConvertedDate, hasChartData, hasFxDataGap, status}) => {
        const input = pairsInput({configuredFxSlugs: configured ? ['EUR-USD'] : [], fxFirstConvertedDate, hasChartData, hasFxDataGap});

        expect(buildRequiredFxPairs(input)).toEqual([assetPair(status, fxFirstConvertedDate ?? undefined)]);
    });

    it('lists no pair for the asset while it is not loaded, or when it is in the shown currency', () => {
        expect(buildRequiredFxPairs(pairsInput({asset: null, configuredFxSlugs: ['EUR-USD']}))).toEqual([]);
        expect(buildRequiredFxPairs(pairsInput({asset: {...PAGE_ASSET, currency: 'EUR'}, configuredFxSlugs: ['EUR-USD']}))).toEqual([]);
    });
});

describe('buildRequiredFxPairs: then a pair per comparison peer in another currency, in the order of the configs, one per slug', () => {
    it('lists the peers’ pairs after the asset’s, in the order of their configs, each named after its peer', () => {
        const input = pairsInput({configuredFxSlugs: ['CHF-EUR', 'EUR-JPY'], signals: [comparisonConfig(8, LOADED), comparisonConfig(7, LOADED)]});

        expect(buildRequiredFxPairs(input)).toEqual([
            assetPair('missing'),
            {slug: 'EUR-JPY', label: 'EUR/JPY', forAsset: 'Yen Peer', forAssetIconUrl: null, forAssetType: 'ETF', status: 'ok'},
            {slug: 'CHF-EUR', label: 'CHF/EUR', forAsset: 'Swiss Peer', forAssetIconUrl: 'https://icons.test/swiss.png', forAssetType: 'FUND', status: 'ok'},
        ]);
    });

    it.each([
        {label: 'its config is not an asset comparison', config: signalConfig('fx-7', 'fx-pair', {assetId: 7})},
        {label: 'its asset id is 0', config: comparisonConfig(0, LOADED)},
        {label: 'its asset id is not a number', config: comparisonConfig('seven', LOADED)},
        {label: 'its asset id is missing', config: comparisonConfig(undefined, LOADED)},
        {label: 'its asset is unknown', config: comparisonConfig(99, LOADED)},
        {label: 'its asset has no currency', config: comparisonConfig(10, LOADED)},
        {label: 'its asset is in the shown currency', config: comparisonConfig(9, LOADED)},
    ])('lists no pair for a peer when $label', ({config}) => {
        expect(buildRequiredFxPairs(pairsInput({asset: null, configuredFxSlugs: ['CHF-EUR', 'EUR-USD'], signals: [config]}))).toEqual([]);
    });

    it('reads a numeric string asset id as its number', () => {
        expect(summary(buildRequiredFxPairs(pairsInput({asset: null, configuredFxSlugs: ['CHF-EUR'], signals: [comparisonConfig('7', LOADED)]})))).toEqual(['CHF-EUR ok']);
    });

    it('lists no pair for a comparison with the asset the page shows', () => {
        const input = pairsInput({asset: null, configuredFxSlugs: ['EUR-USD'], signals: [comparisonConfig(PAGE_ASSET_ID, LOADED)]});

        expect(buildRequiredFxPairs(input)).toEqual([]);
        // The same config on another asset's page: the asset is then a peer like any other.
        expect(summary(buildRequiredFxPairs({...input, pageAssetId: 2}))).toEqual(['EUR-USD ok']);
    });

    it('lists a currency once, named after the first asset that needs it', () => {
        const input = pairsInput({configuredFxSlugs: ['CHF-EUR', 'EUR-USD'], signals: [comparisonConfig(11, LOADED), comparisonConfig(7, LOADED), comparisonConfig(12, LOADED)]});

        expect(buildRequiredFxPairs(input).map(({slug, forAsset}) => `${slug} ${forAsset}`)).toEqual(['EUR-USD Page Asset', 'CHF-EUR Swiss Peer']);
    });
});

describe('buildRequiredFxPairs: a configured peer pair follows the calendar view while its snapshot is current, else the peer’s loaded comparison', () => {
    /** The status of the Swiss peer's pair, CHF-EUR, configured, on a page with `overrides`. */
    function swissPairStatus(overrides: Partial<RequiredFxPairsInput>): PairStatus | undefined {
        return statusOf(buildRequiredFxPairs(pairsInput({configuredFxSlugs: ['CHF-EUR'], ...overrides})), 'CHF-EUR');
    }

    it.each<{label: string; runtime: Record<string, unknown>; failures: number[]; problems: Array<[number, SignalProblemCode]>; status: PairStatus}>([
        {label: 'nothing failed, even without loaded prices', runtime: {}, failures: [], problems: [], status: 'ok'},
        {label: 'its conversion failed', runtime: LOADED, failures: [7], problems: [], status: 'no-data'},
        {label: 'its problem is fx_conversion_unavailable', runtime: LOADED, failures: [], problems: [[7, 'fx_conversion_unavailable']], status: 'no-data'},
        {label: 'its problem is another one', runtime: LOADED, failures: [], problems: [[7, 'missing_input_fields']], status: 'ok'},
        {label: 'only another peer failed', runtime: LOADED, failures: [8], problems: [[8, 'fx_conversion_unavailable']], status: 'ok'},
        {label: 'its loaded comparison failed to convert, which this view does not read', runtime: {...LOADED, _conversionFailed: true}, failures: [], problems: [], status: 'ok'},
    ])('is $status in the calendar view with a current snapshot when $label', ({runtime, failures, problems, status}) => {
        const calendarComparisonProblems = new Map(problems.map(([assetId, code]): [number, SignalProblem] => [assetId, signalProblem(code)]));

        expect(swissPairStatus({primaryMode: 'calendar-return', calendarSnapshotIsCurrent: true, signals: [comparisonConfig(7, runtime)], calendarComparisonFxFailures: new Set(failures), calendarComparisonProblems})).toBe(status);
    });

    it.each<{label: string; primaryMode: string; calendarSnapshotIsCurrent: boolean; runtime: Record<string, unknown>; failures: number[]; status: PairStatus}>([
        {label: 'in the price view, its prices loaded', primaryMode: 'price', calendarSnapshotIsCurrent: true, runtime: LOADED, failures: [], status: 'ok'},
        {label: 'in the price view, its conversion failed', primaryMode: 'price', calendarSnapshotIsCurrent: true, runtime: {...LOADED, _conversionFailed: true}, failures: [], status: 'no-data'},
        {label: 'in the price view, no prices loaded', primaryMode: 'price', calendarSnapshotIsCurrent: true, runtime: {}, failures: [], status: 'no-data'},
        {label: 'in the price view, despite a calendar failure it does not read', primaryMode: 'price', calendarSnapshotIsCurrent: true, runtime: LOADED, failures: [7], status: 'ok'},
        {label: 'in a calendar view with a stale snapshot, despite a calendar failure', primaryMode: 'calendar-return', calendarSnapshotIsCurrent: false, runtime: LOADED, failures: [7], status: 'ok'},
        {label: 'in a calendar view with a stale snapshot, no prices loaded', primaryMode: 'calendar-return', calendarSnapshotIsCurrent: false, runtime: {}, failures: [], status: 'no-data'},
        {label: 'in a calendar view with a stale snapshot, its conversion failed', primaryMode: 'calendar-return', calendarSnapshotIsCurrent: false, runtime: {...LOADED, _conversionFailed: true}, failures: [], status: 'no-data'},
    ])('is $status $label', ({primaryMode, calendarSnapshotIsCurrent, runtime, failures, status}) => {
        expect(swissPairStatus({primaryMode, calendarSnapshotIsCurrent, signals: [comparisonConfig(7, runtime)], calendarComparisonFxFailures: new Set(failures)})).toBe(status);
    });

    it.each(['price', 'calendar-return'])('is missing in the %s view while the pair is not configured, whatever the conversion', (primaryMode) => {
        const input = pairsInput({primaryMode, configuredFxSlugs: [], signals: [comparisonConfig(7, LOADED)], calendarComparisonFxFailures: new Set([7])});

        expect(statusOf(buildRequiredFxPairs(input), 'CHF-EUR')).toBe('missing');
    });
});

describe('buildRequiredFxPairs: then a pair per event currency, the asset’s events before the peers’; a pair already listed only gets worse', () => {
    it('lists the events’ pairs last, the asset’s first, each named after whose events need it', () => {
        const input = pairsInput({
            configuredFxSlugs: ['CHF-EUR', 'EUR-GBP', 'EUR-JPY', 'EUR-SEK', 'EUR-USD'],
            fxFirstConvertedDate: '2026-01-05',
            signals: [comparisonConfig(8, LOADED), comparisonConfig(7, LOADED)],
            events: [convertedDividend('GBP')],
            comparisonEvents: new Map([
                [7, [unconvertedDividend('SEK')]],
                [42, [convertedDividend('NOK')]],
            ]),
        });

        const pairs = buildRequiredFxPairs(input);

        expect(summary(pairs)).toEqual(['EUR-USD ok', 'EUR-JPY ok', 'CHF-EUR ok', 'EUR-GBP ok', 'EUR-SEK no-data', 'EUR-NOK missing']);
        expect(pairs.slice(3)).toEqual([
            {slug: 'EUR-GBP', label: 'EUR/GBP', forAsset: EVENTS_LABEL, forAssetIconUrl: undefined, forAssetType: undefined, status: 'ok'},
            {slug: 'EUR-SEK', label: 'EUR/SEK', forAsset: 'Swiss Peer', forAssetIconUrl: 'https://icons.test/swiss.png', forAssetType: 'FUND', status: 'no-data'},
            {slug: 'EUR-NOK', label: 'EUR/NOK', forAsset: 'Asset #42', forAssetIconUrl: undefined, forAssetType: undefined, status: 'missing'},
        ]);
    });

    it.each([
        {label: 'converted, its pair configured', event: convertedDividend('GBP'), configured: ['EUR-GBP'], status: 'ok'},
        {label: 'not converted, its pair configured', event: unconvertedDividend('GBP'), configured: ['EUR-GBP'], status: 'no-data'},
        {label: 'converted, its pair not configured', event: convertedDividend('GBP'), configured: [], status: 'missing'},
        {label: 'not converted, its pair not configured', event: unconvertedDividend('GBP'), configured: [], status: 'missing'},
    ])('lists the pair of an event $label as $status', ({event, configured, status}) => {
        const input = pairsInput({asset: null, configuredFxSlugs: configured, events: [event]});

        expect(buildRequiredFxPairs(input)).toEqual([{slug: 'EUR-GBP', label: 'EUR/GBP', forAsset: EVENTS_LABEL, status}]);
    });

    it('needs no pair for an event already in the shown currency, nor for an entry that is not an event', () => {
        const input = pairsInput({asset: null, events: [dividend({code: 'EUR', amount: '1.00'}), null, 'DIVIDEND'], comparisonEvents: new Map([[7, [dividend({code: 'EUR', amount: '2.00'})]]])});

        expect(buildRequiredFxPairs(input)).toEqual([]);
    });

    it('lists an event currency once, its status getting worse and never better, whatever the order of the events', () => {
        const worse = pairsInput({asset: null, configuredFxSlugs: ['EUR-GBP'], events: [convertedDividend('GBP'), unconvertedDividend('GBP')]});
        const notBetter = pairsInput({asset: null, configuredFxSlugs: ['EUR-GBP'], events: [unconvertedDividend('GBP'), convertedDividend('GBP')]});

        expect(summary(buildRequiredFxPairs(worse))).toEqual(['EUR-GBP no-data']);
        expect(summary(buildRequiredFxPairs(notBetter))).toEqual(['EUR-GBP no-data']);
    });

    it('keeps the name of a pair an event joins', () => {
        const input = pairsInput({configuredFxSlugs: ['EUR-USD'], fxFirstConvertedDate: '2026-01-05', events: [unconvertedDividend('USD')]});

        expect(buildRequiredFxPairs(input)).toEqual([assetPair('no-data', '2026-01-05')]);
    });

    it.each<{label: string; overrides: Partial<RequiredFxPairsInput>; slug: string; status: PairStatus}>([
        {label: 'an ok pair becomes no-data with an unconverted event', overrides: {fxFirstConvertedDate: '2026-01-05', events: [unconvertedDividend('USD')]}, slug: 'EUR-USD', status: 'no-data'},
        {label: 'an ok pair stays ok with a converted event', overrides: {fxFirstConvertedDate: '2026-01-05', events: [convertedDividend('USD')]}, slug: 'EUR-USD', status: 'ok'},
        {label: 'a partial-gap pair stays partial-gap with an unconverted event', overrides: {fxFirstConvertedDate: '2026-01-05', hasFxDataGap: true, events: [unconvertedDividend('USD')]}, slug: 'EUR-USD', status: 'partial-gap'},
        {label: 'a missing pair stays missing with a converted event', overrides: {configuredFxSlugs: [], events: [convertedDividend('USD')]}, slug: 'EUR-USD', status: 'missing'},
        {label: 'a no-data peer pair stays no-data with a converted event', overrides: {signals: [comparisonConfig(7)], comparisonEvents: new Map([[7, [convertedDividend('CHF')]]])}, slug: 'CHF-EUR', status: 'no-data'},
    ])('keeps one entry per slug: $label', ({overrides, slug, status}) => {
        const pairs = buildRequiredFxPairs(pairsInput({configuredFxSlugs: ['CHF-EUR', 'EUR-USD'], ...overrides}));

        expect(pairs.filter((pair) => pair.slug === slug)).toHaveLength(1);
        expect(statusOf(pairs, slug)).toBe(status);
    });
});

describe('buildRequiredFxPairs: reads the page state under the conditions of the former $derived, so the page depends on the same state', () => {
    it('gives no pair and reads nothing but the shown currency when none is shown', () => {
        const values = pairsInput({displayCurrency: '', configuredFxSlugs: ['EUR-USD'], signals: [comparisonConfig(7, LOADED)], events: [unconvertedDividend('GBP')], comparisonEvents: new Map([[42, [convertedDividend('NOK')]]])});
        const {input, reads} = recorded(values);

        expect(buildRequiredFxPairs(input)).toEqual([]);
        expect([...reads]).toEqual(['displayCurrency']);
    });

    it('reads the chart data while the asset’s configured pair has no converted date', () => {
        const {input, reads} = recorded(pairsInput({configuredFxSlugs: ['EUR-USD'], fxFirstConvertedDate: null}));

        expect(summary(buildRequiredFxPairs(input))).toEqual(['EUR-USD no-data']);
        expect(reads.has('hasChartData')).toBe(true);
    });

    it.each<{label: string; overrides: Partial<RequiredFxPairsInput>}>([
        {label: 'the asset’s pair has a converted date', overrides: {configuredFxSlugs: ['EUR-USD'], fxFirstConvertedDate: '2026-01-05'}},
        {label: 'the asset’s pair is not configured', overrides: {configuredFxSlugs: [], fxFirstConvertedDate: null}},
        {label: 'the asset is in the shown currency', overrides: {asset: {...PAGE_ASSET, currency: 'EUR'}, configuredFxSlugs: ['EUR-USD']}},
        {label: 'the asset is not loaded', overrides: {asset: null, configuredFxSlugs: ['EUR-USD']}},
    ])('does not read the chart data when $label', ({overrides}) => {
        const {input, reads} = recorded(pairsInput(overrides));

        buildRequiredFxPairs(input);

        expect(reads.has('hasChartData')).toBe(false);
    });

    it('reads whether the calendar snapshot is current for a configured peer pair in the calendar view', () => {
        const {input, reads} = recorded(pairsInput({primaryMode: 'calendar-return', configuredFxSlugs: ['CHF-EUR'], signals: [comparisonConfig(7)]}));

        expect(statusOf(buildRequiredFxPairs(input), 'CHF-EUR')).toBe('ok');
        expect(reads.has('calendarSnapshotIsCurrent')).toBe(true);
    });

    it.each<{label: string; overrides: Partial<RequiredFxPairsInput>}>([
        {label: 'in the price view', overrides: {primaryMode: 'price', configuredFxSlugs: ['CHF-EUR'], signals: [comparisonConfig(7, LOADED)]}},
        {label: 'for a peer pair that is not configured', overrides: {primaryMode: 'calendar-return', configuredFxSlugs: [], signals: [comparisonConfig(7)]}},
        {label: 'for the asset’s own pair, without a peer', overrides: {primaryMode: 'calendar-return', configuredFxSlugs: ['EUR-USD'], signals: []}},
        {label: 'for a peer in the shown currency', overrides: {primaryMode: 'calendar-return', configuredFxSlugs: ['EUR-USD'], signals: [comparisonConfig(9)]}},
        {label: 'for a peer that shares the asset’s pair', overrides: {primaryMode: 'calendar-return', configuredFxSlugs: ['EUR-USD'], signals: [comparisonConfig(11)]}},
    ])('does not read whether the calendar snapshot is current $label', ({overrides}) => {
        const {input, reads} = recorded(pairsInput(overrides));

        buildRequiredFxPairs(input);

        expect(reads.has('calendarSnapshotIsCurrent')).toBe(false);
    });

    it('asks for the fallback name of a peer with events that is not among the assets, and of it only', () => {
        const askedFor = new Set<number>();
        const values = pairsInput({
            configuredFxSlugs: ['EUR-GBP', 'EUR-NOK'],
            comparisonEvents: new Map([
                [8, [convertedDividend('GBP')]],
                [42, [convertedDividend('NOK')]],
            ]),
            assetFallbackLabel: (assetId) => {
                askedFor.add(assetId);
                return `Asset #${assetId}`;
            },
        });
        const {input, reads} = recorded(values);

        const pairs = buildRequiredFxPairs(input);

        expect(reads.has('assetFallbackLabel')).toBe(true);
        expect(askedFor).toEqual(new Set([42]));
        expect(pairs.find((pair) => pair.slug === 'EUR-NOK')?.forAsset).toBe('Asset #42');
    });

    it.each<{label: string; comparisonEvents: ReadonlyMap<number, readonly unknown[]>}>([
        {label: 'every peer with events is among the assets', comparisonEvents: new Map([[8, [convertedDividend('GBP')]]])},
        {label: 'no peer has events', comparisonEvents: new Map()},
    ])('never asks for a fallback name when $label', ({comparisonEvents}) => {
        const {input, reads} = recorded(pairsInput({configuredFxSlugs: ['EUR-GBP'], comparisonEvents}));

        buildRequiredFxPairs(input);

        expect(reads.has('assetFallbackLabel')).toBe(false);
    });
});

describe('buildAssetDetailIssues: the archived asset, then the range before the data, then one issue per pair that is not ok', () => {
    it('lists the issues in that order, each with its code, severity, message key, affected pair and asset, and call to action', () => {
        const input = issuesInput({
            asset: {active: false},
            rangeStartsBeforeData: true,
            firstDataDate: '2025-03-03',
            requiredFxPairs: [requiredPair('EUR-USD', 'missing', 'Page Asset'), requiredPair('EUR-JPY', 'ok', 'Yen Peer'), requiredPair('CHF-EUR', 'no-data', 'Swiss Peer'), requiredPair('EUR-GBP', 'partial-gap', EVENTS_LABEL, '2025-06-02')],
        });

        expect(buildAssetDetailIssues(input)).toEqual([
            {domain: 'asset', code: 'ASSET_ARCHIVED', severity: 'warning', message_i18n_key: 'dataQuality.archivedAsset'},
            {domain: 'asset', code: 'RANGE_BEFORE_FIRST_DATA', severity: 'info', message_i18n_key: 'dataQuality.rangeBeforeData', message_params: {date: '2025-03-03'}},
            {domain: 'forex', code: 'FX_PAIR_MISSING', severity: 'warning', group_key: 'EUR-USD', message_i18n_key: 'dataQuality.fxPairMissing', affected_fx_pairs: ['EUR-USD'], affected_asset_names: ['Page Asset'], cta_action: 'add_fx_pair', cta_target: 'EUR-USD'},
            {domain: 'forex', code: 'FX_PAIR_NO_DATA', severity: 'warning', group_key: 'CHF-EUR', message_i18n_key: 'dataQuality.fxPairNoData', affected_fx_pairs: ['CHF-EUR'], affected_asset_names: ['Swiss Peer'], cta_action: 'navigate_fx', cta_target: 'CHF-EUR'},
            {
                domain: 'forex',
                code: 'FX_PAIR_PARTIAL_GAP',
                severity: 'info',
                group_key: 'EUR-GBP',
                message_i18n_key: 'dataQuality.fxPairPartialGap',
                message_params: {date: '2025-06-02'},
                affected_fx_pairs: ['EUR-GBP'],
                affected_asset_names: [EVENTS_LABEL],
                cta_action: 'navigate_fx',
                cta_target: 'EUR-GBP',
            },
        ]);
    });

    it('dates a gap with an empty date when its first converted date is unknown', () => {
        const issues = buildAssetDetailIssues(issuesInput({requiredFxPairs: [requiredPair('EUR-GBP', 'partial-gap', 'Page Asset')]}));

        expect(issues).toMatchObject([{code: 'FX_PAIR_PARTIAL_GAP', message_params: {date: ''}}]);
    });

    it('raises nothing for an active asset, a range inside its data and pairs that are all ok', () => {
        expect(buildAssetDetailIssues(issuesInput({requiredFxPairs: [requiredPair('EUR-USD', 'ok', 'Page Asset'), requiredPair('CHF-EUR', 'ok', 'Swiss Peer')]}))).toEqual([]);
    });

    it.each([true, null, undefined])('does not call an asset archived when its active flag is %s', (active) => {
        expect(buildAssetDetailIssues(issuesInput({asset: {active}}))).toEqual([]);
    });

    it.each<{label: string; overrides: Partial<AssetDetailIssuesInput>}>([
        {label: 'while loading', overrides: {loading: true}},
        {label: 'with an error', overrides: {error: 'Failed to load prices'}},
    ])('raises only the archived issue $label: no range, no pair', ({overrides}) => {
        const input = issuesInput({asset: {active: false}, rangeStartsBeforeData: true, requiredFxPairs: [requiredPair('EUR-USD', 'missing', 'Page Asset')], ...overrides});

        expect(buildAssetDetailIssues(input).map((issue) => issue.code)).toEqual(['ASSET_ARCHIVED']);
    });

    it('raises no range issue while the asset is not loaded, but still the pairs’ issues', () => {
        const input = issuesInput({asset: null, rangeStartsBeforeData: true, requiredFxPairs: [requiredPair('CHF-EUR', 'missing', 'Swiss Peer')]});

        expect(buildAssetDetailIssues(input).map((issue) => issue.code)).toEqual(['FX_PAIR_MISSING']);
    });
});

describe('buildAssetDetailIssues: reads the first data date and the pairs only when it uses them', () => {
    it('reads the first data date when it raises the range issue', () => {
        const {input, reads} = recorded(issuesInput({rangeStartsBeforeData: true}));

        expect(buildAssetDetailIssues(input).map((issue) => issue.code)).toEqual(['RANGE_BEFORE_FIRST_DATA']);
        expect(reads.has('firstDataDate')).toBe(true);
    });

    it.each<{label: string; overrides: Partial<AssetDetailIssuesInput>}>([
        {label: 'the range starts inside the data', overrides: {rangeStartsBeforeData: false}},
        {label: 'the page is loading', overrides: {rangeStartsBeforeData: true, loading: true}},
        {label: 'the page has an error', overrides: {rangeStartsBeforeData: true, error: 'Failed to load prices'}},
        {label: 'the asset is not loaded', overrides: {rangeStartsBeforeData: true, asset: null}},
    ])('does not read the first data date when $label', ({overrides}) => {
        const {input, reads} = recorded(issuesInput(overrides));

        buildAssetDetailIssues(input);

        expect(reads.has('firstDataDate')).toBe(false);
    });

    it('reads the pairs once loaded without an error', () => {
        const {input, reads} = recorded(issuesInput({requiredFxPairs: [requiredPair('EUR-USD', 'missing', 'Page Asset')]}));

        expect(buildAssetDetailIssues(input).map((issue) => issue.code)).toEqual(['FX_PAIR_MISSING']);
        expect(reads.has('requiredFxPairs')).toBe(true);
    });

    it.each<{label: string; overrides: Partial<AssetDetailIssuesInput>}>([
        {label: 'while loading', overrides: {loading: true}},
        {label: 'with an error', overrides: {error: 'Failed to load prices'}},
    ])('does not read the pairs $label', ({overrides}) => {
        const {input, reads} = recorded(issuesInput({requiredFxPairs: [requiredPair('EUR-USD', 'missing', 'Page Asset')], ...overrides}));

        buildAssetDetailIssues(input);

        expect(reads.has('requiredFxPairs')).toBe(false);
    });
});
