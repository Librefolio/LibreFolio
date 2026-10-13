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
 * are the guards of that change. The other languages are the last describe's.
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
