import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';

import {setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {AssetComparisonSignal} from '../AssetComparisonSignal';
import type {SignalStyle} from '../ChartSignal';
import {FxPairSignal} from '../FxPairSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

/**
 * Comparison signals — the two overlays whose data is fetched by the page and
 * injected as `params._resolvedData` before rendering.
 *
 * Both override `render()` to normalise against their *own* first point instead
 * of the chart's, because an overlay on a different scale (AAPL at 180 over a
 * chart at 1.09) is only comparable once both curves start at zero. That
 * override, the date alignment underneath it, and the FX ghost series are what
 * this file pins.
 *
 * The currency store is empty in a unit run, so `getCurrencyInfo` returns its
 * documented fallback: the code as its own name and 🏳️ as the flag.
 *
 * What a comparison signal calls itself before the page has named it comes from
 * the catalogue (T-FB): «Asset #7», «Asset» and «FX Pair» are
 * `chartSettings.signals.assetFallback` around the id, `common.asset` and
 * `chartSettings.signals.fxPair`, read through `ChartSignal.text`. Formatting a
 * message throws before svelte-i18n is initialised, so the file boots it once,
 * in English, the app's fallback: the English names the cases pin as literals
 * are the guards of that change. The other languages are the T-FB describe's.
 *
 * The page may also inject the base of the percentage view (Z-29d-0):
 * `params._basePoint`, the target's point on the day the comparison starts,
 * which a sampled chart does not draw — the line, and the FX ghost through its
 * `originalValue`, measure from it, an unusable one changes nothing, it is never
 * drawn, and `toConfig()` leaves it out like `_resolvedData`; the Z-29d-0
 * describe pins it.
 */

/**
 * svelte-i18n throws when it formats a message before it is initialised, and the
 * fallback names are formatted messages: boot it once for the whole file, in
 * English. The cases that speak another language switch the interface language
 * themselves and put English back.
 */
beforeAll(async () => {
    await setupI18n('en');
});

const style: SignalStyle = {
    color: '#3b82f6',
    lineWidth: 2,
    lineType: 'solid',
    markerStart: null,
    markerEnd: null,
};

const FALLBACK_FLAG = '🏳️';

/** Four trading days the chart knows about. */
const chart: LineDataPoint[] = [
    {date: '2026-03-02', value: 1000},
    {date: '2026-03-03', value: 1010},
    {date: '2026-03-04', value: 1020},
    {date: '2026-03-05', value: 1030},
];

function values(points: LineDataPoint[]): number[] {
    return points.map((point) => point.value);
}

function dates(points: LineDataPoint[]): string[] {
    return points.map((point) => point.date);
}

describe('AssetComparisonSignal — aligning injected data', () => {
    it('keeps only the dates the chart itself plots', () => {
        // The overlay asset trades on a day the chart does not, and misses one the
        // chart has: the result follows the chart's axis, never its own.
        const signal = new AssetComparisonSignal('a1', style, {
            assetId: '7',
            _resolvedData: [
                {date: '2026-03-02', value: 200},
                {date: '2026-03-03', value: 210},
                {date: '2026-03-04-bis', value: 215},
                {date: '2026-03-05', value: 230},
            ],
        });

        expect(dates(signal.computePoints(chart))).toEqual(['2026-03-02', '2026-03-03', '2026-03-05']);
        expect(values(signal.computePoints(chart))).toEqual([200, 210, 230]);
    });

    it('drops zero values instead of plotting a collapse to the axis', () => {
        const signal = new AssetComparisonSignal('a1', style, {
            assetId: '7',
            _resolvedData: [
                {date: '2026-03-02', value: 200},
                {date: '2026-03-03', value: 0},
                {date: '2026-03-04', value: 220},
            ],
        });

        expect(dates(signal.computePoints(chart))).toEqual(['2026-03-02', '2026-03-04']);
    });

    it('produces nothing when either side has no data', () => {
        const withData = new AssetComparisonSignal('a1', style, {assetId: '7', _resolvedData: [{date: '2026-03-02', value: 200}]});
        const withoutData = new AssetComparisonSignal('a1', style, {assetId: '7'});

        expect(withData.computePoints([])).toEqual([]);
        expect(withoutData.computePoints(chart)).toEqual([]);
        expect(new AssetComparisonSignal('a1', style, {assetId: '7', _resolvedData: []}).computePoints(chart)).toEqual([]);
        expect(withoutData.renderMulti(chart, 'absolute')).toEqual([]);
    });
});

describe('AssetComparisonSignal — percentage view', () => {
    const signal = new AssetComparisonSignal('a1', style, {
        assetId: '7',
        _resolvedData: [
            {date: '2026-03-02', value: 200},
            {date: '2026-03-03', value: 220},
            {date: '2026-03-04', value: 180},
        ],
    });

    it('restarts at zero on its own first point, not on the chart baseline', () => {
        // The chart opens at 1000. Normalising against that would put this
        // overlay at -80%; against its own 200 it reads +10% and -10%.
        expect(values(signal.render(chart, 'percentage').data)).toEqual([0, 10, -10]);
    });

    it('leaves absolute view in the asset\u2019s own units', () => {
        expect(values(signal.render(chart, 'absolute').data)).toEqual([200, 220, 180]);
    });
});

describe('AssetComparisonSignal — currency of the plotted values', () => {
    const base = {assetId: '7', _assetCurrency: 'USD'};

    it('reports the asset\u2019s own currency when no conversion happened', () => {
        const signal = new AssetComparisonSignal('a1', style, {...base, _resolvedData: [{date: '2026-03-02', value: 200}]});
        const rendered = signal.render(chart, 'absolute');

        expect(rendered.currency).toBe('USD');
        expect(rendered.currencyFlag).toBe(FALLBACK_FLAG);
    });

    it('reports the target currency once values carry an original', () => {
        const signal = new AssetComparisonSignal('a1', style, {
            ...base,
            _targetCurrency: 'EUR',
            _resolvedData: [{date: '2026-03-02', value: 184, originalValue: 200, originalCurrency: 'USD'}],
        });

        expect(signal.render(chart, 'absolute').currency).toBe('EUR');
    });

    it('stays on the native currency when a conversion target was never resolved', () => {
        const signal = new AssetComparisonSignal('a1', style, {
            ...base,
            _resolvedData: [{date: '2026-03-02', value: 184, originalValue: 200}],
        });

        expect(signal.render(chart, 'absolute').currency).toBe('USD');
    });

    it('emits no flag at all when the currency is unknown', () => {
        const signal = new AssetComparisonSignal('a1', style, {assetId: '7', _resolvedData: [{date: '2026-03-02', value: 200}]});
        const rendered = signal.render(chart, 'absolute');

        expect(rendered.currency).toBe('');
        expect(rendered.currencyFlag).toBe('');
    });

    it('passes the asset icon and type through, and nulls them when absent', () => {
        const withMeta = new AssetComparisonSignal('a1', style, {...base, _assetIconUrl: '/icons/7.png', _assetType: 'ETF', _resolvedData: [{date: '2026-03-02', value: 200}]});
        const withoutMeta = new AssetComparisonSignal('a1', style, {...base, _resolvedData: [{date: '2026-03-02', value: 200}]});

        expect(withMeta.render(chart, 'absolute')).toMatchObject({iconUrl: '/icons/7.png', assetType: 'ETF'});
        expect(withoutMeta.render(chart, 'absolute')).toMatchObject({iconUrl: null, assetType: null});
    });
});

describe('AssetComparisonSignal — the unconverted ghost series', () => {
    const converted: LineDataPoint[] = [
        {date: '2026-03-02', value: 184, originalValue: 200, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸'},
        {date: '2026-03-03', value: 202, originalValue: 220, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸'},
    ];

    it('renders only the converted line when no original values were carried', () => {
        const signal = new AssetComparisonSignal('a1', style, {assetId: '7', _assetDisplayName: 'Acme', _resolvedData: [{date: '2026-03-02', value: 200}]});

        expect(signal.renderMulti(chart, 'absolute')).toHaveLength(1);
    });

    it('adds a dashed, half-weight ghost beside the converted line', () => {
        const signal = new AssetComparisonSignal('a1', style, {assetId: '7', _assetDisplayName: 'Acme', _targetCurrency: 'EUR', _resolvedData: converted});
        const [main, ghost] = signal.renderMulti(chart, 'absolute');

        expect(main.id).toBe('a1');
        expect(ghost).toMatchObject({
            id: 'a1__ghost',
            lineWidth: 1,
            lineType: 'dashed',
            color: style.color,
            opacity: 0.8,
            currency: 'USD',
            currencyFlag: '🇺🇸',
        });
        expect(values(ghost.data)).toEqual([200, 220]);
    });

    it('names the ghost after the asset, the source flag and the source currency', () => {
        const signal = new AssetComparisonSignal('a1', style, {assetId: '7', _assetDisplayName: 'Acme', _targetCurrency: 'EUR', _resolvedData: converted});

        expect(signal.renderMulti(chart, 'absolute')[1].label).toBe('💱 Acme (🇺🇸 USD)');
    });

    it('drops the flag from the ghost label when the parent did not resolve one', () => {
        const signal = new AssetComparisonSignal('a1', style, {
            assetId: '7',
            _assetDisplayName: 'Acme',
            _targetCurrency: 'EUR',
            _resolvedData: converted.map(({originalCurrencyFlag: _flag, ...point}) => point),
        });

        expect(signal.renderMulti(chart, 'absolute')[1].label).toBe('💱 Acme (USD)');
    });

    it('normalises the ghost against its own opening price in percentage view', () => {
        // Converted and unconverted must both start at 0% or the FX effect reads
        // as a jump at the left edge instead of as a widening gap.
        const signal = new AssetComparisonSignal('a1', style, {assetId: '7', _targetCurrency: 'EUR', _resolvedData: converted});
        const [main, ghost] = signal.renderMulti(chart, 'percentage');

        expect(values(main.data)).toEqual([0, expect.closeTo(9.7826, 4)]);
        expect(values(ghost.data)).toEqual([0, 10]);
    });

    it('aligns the ghost to the chart axis and skips zero originals', () => {
        const signal = new AssetComparisonSignal('a1', style, {
            assetId: '7',
            _targetCurrency: 'EUR',
            _resolvedData: [
                {date: '2026-03-02', value: 184, originalValue: 200, originalCurrency: 'USD'},
                {date: '2026-03-03', value: 202, originalValue: 0, originalCurrency: 'USD'},
                {date: '2026-03-04', value: 210, originalCurrency: 'USD'},
                {date: '2026-03-05', value: 220, originalValue: 240, originalCurrency: 'USD'},
            ],
        });
        const [, ghost] = signal.renderMulti(chart, 'absolute');

        expect(dates(ghost.data)).toEqual(['2026-03-02', '2026-03-05']);
    });
});

describe('AssetComparisonSignal — legend label', () => {
    it('prefers the display name resolved by the page', () => {
        expect(new AssetComparisonSignal('a1', style, {assetId: '7', _assetDisplayName: 'Acme Corp'}).getLabel()).toBe('Acme Corp');
    });

    it('falls back to the numeric id while the name is still loading', () => {
        expect(new AssetComparisonSignal('a1', style, {assetId: '7'}).getLabel()).toBe('Asset #7');
    });

    it('falls back to a bare word when nothing has been chosen yet', () => {
        expect(new AssetComparisonSignal('a1', style, {assetId: ''}).getLabel()).toBe('Asset');
        expect(new AssetComparisonSignal('a1', style, {}).getLabel()).toBe('Asset');
    });
});

describe('FxPairSignal', () => {
    const rates: LineDataPoint[] = [
        {date: '2026-03-02', value: 1.1},
        {date: '2026-03-03', value: 1.2},
        {date: '2026-03-05', value: 0.9},
    ];

    it('aligns rates to the chart axis and skips zero quotes', () => {
        const signal = new FxPairSignal('fx1', style, {
            pairSlug: 'EUR-USD',
            _resolvedData: [...rates, {date: '2026-03-04', value: 0}],
        });

        expect(dates(signal.computePoints(chart))).toEqual(['2026-03-02', '2026-03-03', '2026-03-05']);
    });

    it('produces nothing when either side has no data', () => {
        expect(new FxPairSignal('fx1', style, {pairSlug: 'EUR-USD'}).computePoints(chart)).toEqual([]);
        expect(new FxPairSignal('fx1', style, {pairSlug: 'EUR-USD', _resolvedData: rates}).computePoints([])).toEqual([]);
    });

    it('reciprocates every quote when the pair is shown inverted', () => {
        const signal = new FxPairSignal('fx1', style, {pairSlug: 'EUR-USD', _inverted: true, _resolvedData: rates});
        const computed = values(signal.computePoints(chart));

        expect(computed[0]).toBeCloseTo(1 / 1.1, 12);
        expect(computed[1]).toBeCloseTo(1 / 1.2, 12);
        expect(computed[2]).toBeCloseTo(1 / 0.9, 12);
    });

    it('restarts at zero on its own first quote in percentage view', () => {
        const signal = new FxPairSignal('fx1', style, {pairSlug: 'EUR-USD', _resolvedData: rates});
        const computed = values(signal.render(chart, 'percentage').data);

        expect(computed[0]).toBe(0);
        expect(computed[1]).toBeCloseTo(9.0909, 4);
        expect(computed[2]).toBeCloseTo(-18.1818, 4);
    });

    it('labels the pair with both flags in quote order', () => {
        const signal = new FxPairSignal('fx1', style, {pairSlug: 'EUR-USD'});
        expect(signal.getLabel()).toBe(`${FALLBACK_FLAG} EUR → ${FALLBACK_FLAG} USD`);
    });

    it('swaps base and quote in the label when inverted', () => {
        const signal = new FxPairSignal('fx1', style, {pairSlug: 'EUR-USD', _inverted: true});
        expect(signal.getLabel()).toBe(`${FALLBACK_FLAG} USD → ${FALLBACK_FLAG} EUR`);
    });

    it('falls back to a bare word before a pair is chosen', () => {
        expect(new FxPairSignal('fx1', style, {pairSlug: ''}).getLabel()).toBe('FX Pair');
        expect(new FxPairSignal('fx1', style, {}).getLabel()).toBe('FX Pair');
    });
});

describe('The comparison signals’ fallback names in the interface language (T-FB)', () => {
    /*
     * Before the page has named it, an asset comparison calls itself by its id — «Asset #7» — or, with no asset
     * chosen yet, «Asset»; an FX pair with no pair chosen calls itself «FX Pair». Today those are English written
     * in the classes, whatever the interface language, and they reach the chart: the legend and the tooltip read
     * `render()`'s label, which is `getLabel()`.
     *
     * The contract. `AssetComparisonSignal` with no `_assetDisplayName` and an `assetId` is
     * `chartSettings.signals.assetFallback` around `{id}`; with no `assetId` either, `common.asset`.
     * `FxPairSignal` with an empty slug is `chartSettings.signals.fxPair`. All three through `ChartSignal.text`,
     * the tracked translator.
     *
     * Every expectation is the catalogue's own text (`$_`), never a typed translation. `common.asset` reads
     * «Asset» in Italian as in English, so only French tells the bare word from the literal; the numbered name
     * and the FX pair are told apart in both.
     *
     * Red today: in Italian and French every fallback reads as it does in English.
     */
    const LANGUAGES = ['it', 'fr'] as const;
    type UiLanguage = 'en' | (typeof LANGUAGES)[number];

    /** Switch the interface language in place, as the language selector does. */
    async function speak(lang: UiLanguage): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    afterEach(async () => {
        // The language is module-level state shared by every case of the file.
        await speak('en');
    });

    /** A catalogue message with its values, as the interface language words it. */
    function catalogue(key: string, values: Record<string, string> = {}): string {
        return get(_)(key, {values});
    }

    /** The fallback names the two signals give themselves — and hand the chart — before the page has named them. */
    function fallbackNames(): Record<string, string> {
        const numbered = new AssetComparisonSignal('a1', style, {assetId: '7', _resolvedData: [{date: '2026-03-02', value: 200}]});
        return {
            numbered: numbered.getLabel(),
            numberedOnTheChart: numbered.render(chart, 'absolute').label,
            bare: new AssetComparisonSignal('a1', style, {}).getLabel(),
            fxPair: new FxPairSignal('fx1', style, {pairSlug: ''}).getLabel(),
        };
    }

    /** The same names as the catalogue words them in the interface language. */
    function cataloguedNames(): Record<string, string> {
        const numbered = catalogue('chartSettings.signals.assetFallback', {id: '7'});
        return {
            numbered,
            numberedOnTheChart: numbered,
            bare: catalogue('common.asset'),
            fxPair: catalogue('chartSettings.signals.fxPair'),
        };
    }

    it.each(LANGUAGES)('%s interface: «Asset #7», «Asset» and «FX Pair» are the catalogue’s — assetFallback around the id, common.asset, chartSettings.signals.fxPair — and the chart gets the same', async (lang) => {
        await speak(lang);
        expect(catalogue('chartSettings.signals.assetFallback', {id: '7'}), `premise: the ${lang} catalogue names an asset by its id another way than English`).not.toBe(get(_)('chartSettings.signals.assetFallback', {values: {id: '7'}, locale: 'en'}));

        expect(fallbackNames(), `the fallback names are not in the ${lang} interface's words: the classes write «Asset #», «Asset» and «FX Pair» in English`).toEqual(cataloguedNames());
    });

    it('English interface: the English catalogue words the fallbacks exactly as the classes always did (guard)', async () => {
        await speak('en');

        expect(fallbackNames(), 'the English fallback names moved').toEqual(cataloguedNames());
    });
});

describe('AssetComparisonSignal — an injected base point (Z-29d-0)', () => {
    /*
     * What it protects. Backend lot Z-29a samples the asset list's cards: a card draws one point per bucket, never
     * the day its range starts. A comparison aligned on those dates begins at the first bucket's point — or later,
     * where the target's sample is dated otherwise — and, normalised there as it is today, its percentage reads
     * another number than the same comparison on a daily chart. Its base must be the target's point on the day the
     * comparison starts, the point a daily chart draws first: MF's note n3, «the percentage base reads
     * `sample_bounds.first`, not `prices[0]`». The page injects that point as `params._basePoint`, beside
     * `_resolvedData`.
     *
     * The contract. `_basePoint` is optional, a `LineDataPoint`. In the percentage view the line is measured from
     * `_basePoint.value` — pct = (v − base) / base × 100 — no longer from its own first aligned value; the FX ghost
     * from `_basePoint.originalValue` when the point carries one, from its own first aligned original otherwise.
     * An unusable point changes nothing: absent, not an object, `missing: true`, or a `value` that is not a finite
     * number or is 0. The point is usable only if its `value` is, so an unusable one leaves the ghost as today too,
     * however good its `originalValue`; a usable one moves the ghost only if its `originalValue` passes the same
     * number rule. The point is never drawn: the dates stay the aligned dates, and the absolute view does not move.
     * `toConfig()` leaves it out, as it does `_resolvedData` — the moment's data, not a preference — and still saves
     * the `_` style overrides such as `_signalColor`. Without `_basePoint` everything is as today: the describes
     * above pin that.
     *
     * How it is read. Through what the class hands the chart and the settings: `render()`, `renderMulti()`,
     * `toConfig()`. The reds expect the arithmetic, to nine decimals. A guard that says «as today» compares with an
     * identical instance without `_basePoint` — today's class is its oracle — never with typed numbers. Where the
     * line will move after the cure and the ghost must not — or where the line guard already pins the line — only
     * the ghost is read.
     *
     * Red today: the class never reads the point. The line and the ghost restart at 0 % on their own first aligned
     * value, and `toConfig()` saves the point with the preferences.
     */
    type Rendered = ReturnType<AssetComparisonSignal['render']>;

    /** The chart's drawn days, 2026-03-02 … 2026-03-05. */
    const DRAWN_DAYS = dates(chart);

    /** The target on the chart's four days: 110 … 140. */
    const target: LineDataPoint[] = [
        {date: '2026-03-02', value: 110},
        {date: '2026-03-03', value: 120},
        {date: '2026-03-04', value: 130},
        {date: '2026-03-05', value: 140},
    ];

    /** The target's point on the day the comparison starts: 2026-03-01, the day before the chart's first drawn one. */
    const basePoint: LineDataPoint = {date: '2026-03-01', value: 100};

    /** The same target converted from USD at 0.5: its originals, 220 … 280, are the ghost's. */
    const convertedTarget: LineDataPoint[] = target.map((point) => ({...point, originalValue: point.value * 2, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸'}));

    /** The converted base point: 100 converted, 200 original. */
    const convertedBasePoint: LineDataPoint = {...basePoint, originalValue: 200, originalCurrency: 'USD'};

    /** Asset 7 compared on `data`, as the page injects it, with `extra` params on top — `_basePoint`, or nothing. */
    function comparison(data: LineDataPoint[], extra: Record<string, unknown> = {}): AssetComparisonSignal {
        return new AssetComparisonSignal('a1', style, {assetId: '7', _assetDisplayName: 'Acme', _targetCurrency: 'EUR', _resolvedData: data, ...extra});
    }

    /** The unconverted ghost among the series `renderMulti()` hands the chart. */
    function ghostOf(series: Rendered[]): Rendered | undefined {
        return series.find((entry) => entry.id.endsWith('__ghost'));
    }

    /** Expected percentages to nine decimals: the arithmetic is exact, its last bit need not be. */
    function approx(percentages: number[]): unknown[] {
        return percentages.map((percentage) => expect.closeTo(percentage, 9));
    }

    /** A rendering expected exactly, but its values to nine decimals: an equivalent formula may round the last bit another way. */
    function toNineDecimals(series: Rendered[]): Rendered[] {
        return series.map((entry) => ({...entry, data: entry.data.map((point) => ({...point, value: expect.closeTo(point.value, 9)}))}));
    }

    it('the percentage line is measured from the injected base point, not from its own first aligned value', () => {
        // Today: `_basePoint` is never read — the line restarts at 0 % on 03-02's 110: [0, 9.09…, 18.18…, 27.27…].
        const line = comparison(target, {_basePoint: basePoint}).render(chart, 'percentage');

        expect(dates(line.data), 'premise: the line is drawn on the chart’s four days').toEqual(DRAWN_DAYS);
        expect(values(line.data), 'the comparison restarts at 0 % on its first drawn point (110 on 03-02) instead of measuring from the target’s price on the day the comparison starts (100 on 03-01)').toEqual(approx([10, 20, 30, 40]));
    });

    it('the percentage line is still measured from the base point when the target’s first aligned point comes after the chart’s first day (03-03)', () => {
        // Today: the line restarts at 0 % on 03-03's 120, its own first aligned value: [0, 8.33…, 16.66…].
        const late = target.filter((point) => point.date !== '2026-03-02'); // started later, or its sample there is dated otherwise
        const line = comparison(late, {_basePoint: basePoint}).render(chart, 'percentage');

        expect(dates(line.data), 'premise: the line is drawn from 03-03 on').toEqual(['2026-03-03', '2026-03-04', '2026-03-05']);
        expect(values(line.data), 'a comparison whose first aligned point comes late restarts at 0 % there (120 on 03-03) instead of measuring from the target’s price on the day the comparison starts (100)').toEqual(approx([20, 30, 40]));
    });

    it('GUARD: a base point on the first aligned day itself gives today’s percentage line and ghost — the two definitions agree', () => {
        // Green today and after: when the comparison starts on a drawn day, its first aligned point is the base point.
        const today = comparison(convertedTarget).renderMulti(chart, 'percentage');
        const onTheFirstDay = comparison(convertedTarget, {_basePoint: {date: '2026-03-02', value: 110, originalValue: 220}}).renderMulti(chart, 'percentage');

        expect(ghostOf(today), 'premise: today the converted target draws a ghost').toBeDefined();
        expect(onTheFirstDay, 'a base point equal to the first aligned point moved the percentage view').toEqual(toNineDecimals(today));
    });

    it.each<[string, unknown]>([
        ['a value of 0', {date: '2026-03-01', value: 0}],
        ['a NaN value', {date: '2026-03-01', value: NaN}],
        ['an infinite value', {date: '2026-03-01', value: Infinity}],
        ['a value that is the string "100"', {date: '2026-03-01', value: '100'}],
        ['a point marked missing', {date: '2026-03-01', value: 100, missing: true}],
        ['a point with no value at all', {date: '2026-03-01'}],
        ['a bare number, 100', 100],
        ['null', null],
    ])('GUARD: an unusable base point — %s — is ignored: the percentage line is exactly today’s', (_case, unusable) => {
        // Green today and after: today every base point is ignored; after the cure an unusable one still is.
        const today = comparison(target).render(chart, 'percentage');

        expect(dates(today.data), 'premise: today the line is drawn on the chart’s four days').toEqual(DRAWN_DAYS);
        expect(comparison(target, {_basePoint: unusable}).render(chart, 'percentage'), 'an unusable base point moved the percentage line').toEqual(today);
    });

    it('the percentage ghost is measured from the base point’s original value, not from its own first aligned original', () => {
        // Today: the ghost restarts at 0 % on its own first aligned original, 03-02's 220: [0, 9.09…, 18.18…, 27.27…].
        const ghost = ghostOf(comparison(convertedTarget, {_basePoint: convertedBasePoint}).renderMulti(chart, 'percentage'));

        expect(ghost, 'premise: the converted target draws a ghost').toBeDefined();
        expect(dates(ghost?.data ?? []), 'premise: the ghost is drawn on the chart’s four days').toEqual(DRAWN_DAYS);
        expect(values(ghost?.data ?? []), 'the unconverted ghost restarts at 0 % on its own first original (220 on 03-02) instead of measuring from the base point’s original (200 on 03-01)').toEqual(approx([10, 20, 30, 40]));
    });

    it.each<[string, unknown]>([
        ['a base point without originalValue', {date: '2026-03-01', value: 100}],
        ['an originalValue of 0', {date: '2026-03-01', value: 100, originalValue: 0}],
        ['a NaN originalValue', {date: '2026-03-01', value: 100, originalValue: NaN}],
        ['an infinite originalValue', {date: '2026-03-01', value: 100, originalValue: Infinity}],
        ['an originalValue that is the string "200"', {date: '2026-03-01', value: 100, originalValue: '200'}],
        ['a bare number for a base point', 100],
        ['a null base point', null],
    ])('GUARD: %s leaves the percentage ghost exactly as today — on its own first aligned original', (_case, base) => {
        // Green today and after: with no usable original to measure from, the ghost keeps today's base; only the ghost is read, the line may move.
        const today = ghostOf(comparison(convertedTarget).renderMulti(chart, 'percentage'));

        expect(today, 'premise: today the converted target draws a ghost').toBeDefined();
        expect(ghostOf(comparison(convertedTarget, {_basePoint: base}).renderMulti(chart, 'percentage')), 'the ghost moved on a base point with no usable original value').toEqual(today);
    });

    it.each<[string, unknown]>([
        ['a value of 0', {date: '2026-03-01', value: 0, originalValue: 200}],
        ['a NaN value', {date: '2026-03-01', value: NaN, originalValue: 200}],
        ['an infinite value', {date: '2026-03-01', value: Infinity, originalValue: 200}],
        ['a value that is the string "100"', {date: '2026-03-01', value: '100', originalValue: 200}],
        ['a point marked missing', {date: '2026-03-01', value: 100, missing: true, originalValue: 200}],
    ])('GUARD: an unusable base point — %s — is ignored whole: the percentage ghost is exactly today’s even though its original value, 200, is usable', (_case, base) => {
        // Green today and after: today every base point is ignored; after the cure one whose value is unusable still is, whole — its
        // good original, 200, included: the ghost keeps its own first aligned original. Only the ghost is read; the line guard above pins the line.
        const today = ghostOf(comparison(convertedTarget).renderMulti(chart, 'percentage'));

        expect(today, 'premise: today the converted target draws a ghost').toBeDefined();
        expect(ghostOf(comparison(convertedTarget, {_basePoint: base}).renderMulti(chart, 'percentage')), 'an unusable base point still moved the ghost through its original value').toEqual(today);
    });

    it.each<[string, LineDataPoint[], LineDataPoint, string[]]>([
        ['dated before the chart’s first drawn day', convertedTarget, convertedBasePoint, DRAWN_DAYS],
        ['dated on a drawn day where the target has no point', convertedTarget.filter((point) => point.date !== '2026-03-02'), {date: '2026-03-02', value: 100, originalValue: 200}, ['2026-03-03', '2026-03-04', '2026-03-05']],
    ])('GUARD: a base point %s is never drawn — the line and the ghost keep the aligned dates', (_case, data, base, aligned) => {
        // Green today and after: the point is a base, not a point of the line — today it is not read at all.
        const series = comparison(data, {_basePoint: base}).renderMulti(chart, 'percentage');
        const line = series.find((entry) => entry.id === 'a1');

        expect({line: dates(line?.data ?? []), ghost: dates(ghostOf(series)?.data ?? [])}, 'the base point is drawn as an extra point').toEqual({line: aligned, ghost: aligned});
    });

    it('GUARD: the absolute view does not move — the line and the ghost stay the target’s own values', () => {
        // Green today and after: the base point is a percentage base only.
        const today = comparison(convertedTarget).renderMulti(chart, 'absolute');

        expect(ghostOf(today), 'premise: today the converted target draws a ghost').toBeDefined();
        expect(comparison(convertedTarget, {_basePoint: convertedBasePoint}).renderMulti(chart, 'absolute'), 'the base point moved the absolute view').toEqual(today);
    });

    it('toConfig() leaves the injected base point out of the saved settings, as it does `_resolvedData`', () => {
        // Today: toConfig() drops `_resolvedData` only, so `_basePoint` is saved with the preferences.
        const config = comparison(target, {_basePoint: basePoint}).toConfig();

        expect(config.params, 'toConfig() saves the moment’s base point with the chart settings, as if it were a preference').not.toHaveProperty('_basePoint');
    });

    it('GUARD: toConfig() still drops `_resolvedData` and still saves the asset and a `_` style override', () => {
        // Green today and after: leaving `_basePoint` out must not widen to every `_` param — `_signalColor` is a saved style preference.
        const config = comparison(target, {_basePoint: basePoint, _signalColor: '#123456'}).toConfig();

        expect(config.params, 'toConfig() saves the moment’s resolved series').not.toHaveProperty('_resolvedData');
        expect(config.params, 'toConfig() lost the asset or a saved `_` style override').toMatchObject({assetId: '7', _signalColor: '#123456'});
    });
});
