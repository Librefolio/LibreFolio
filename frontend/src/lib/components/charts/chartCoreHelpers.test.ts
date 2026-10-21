import {readFileSync} from 'node:fs';
import * as echarts from 'echarts';
import {afterEach, describe, expect, expectTypeOf, it, vi} from 'vitest';

// The Y-axis labels follow the interface locale (M-18, last block): the UI language regionalised by
// `navigator.language`. Node's tag follows the host's ICU locale, so it is pinned to en-US — jsdom's
// own — before any import, as the CP1 formatter tests do.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import type {RenderedSignal} from '$lib/charts/signals';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {CHART_GAIN_LOSS, chartNeutrals, GROWTH_SERIES} from '$lib/theme/chartTheme';
import {themed} from '$lib/theme/themePair';
import {formatFixed} from '$lib/utils/core/formatFixed';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, assignOverlaySignalAxes, buildOverlaySignalSeries, buildPriceYAxis, buildSecondaryYAxes, collectConfigurableSecondaryAxes, computeRightMargin, getChartColors, secondaryAxisSettingsKey} from './chartCoreHelpers';
import type {ConfigurableAxisDescriptor} from './chartCoreHelpers';
import {exchangeRateAxisLabel, percentageAxisLabel, priceAxisLabel, secondaryAxisLabel, type AxisLabelTranslator} from './axisLabelHelpers';
import {CHART_SET_OPTION_OPTS} from './echartsAnimationConfig';
import {buildSignalReferencePrimitives} from './lineChartHelpers';
import {axisLabelFont, axisLabelMeasure, buildResponsiveXAxisPolicy, categoryAxisLabelPatch, timeAxisGridRight, type AxisLabelMeasure, type ResponsiveXAxisFormatter} from './responsiveXAxis';
// 47-1: the module itself too, so an export still to come is read as a property (a missing one fails its own cases only).
import * as responsiveXAxis from './responsiveXAxis';
import {buildOhlcQuad} from './candlestickChartHelpers';
import {buildTooltipDivider, type TooltipTheme} from './echartsTooltipHelpers';
import {buildBucketInfos, buildZoomWindowForRange, computeBucketCounts, logicalRangeFromBuckets} from '../../features/brokers/lots/lotComparisonChartHelpers';
import {clampGrowthLogicalRange, type GrowthLogicalRange} from '../../features/dashboard/growthChartRange';
import {
    aggregateFlowMetric,
    aggregateMetric,
    alignFlowToDates,
    buildLadderData,
    buildResolutionData,
    type AggregatedMetric,
    type AggregatedResolutionData,
    type AggregationInputs,
    type BucketInfo,
    type CandleSeriesPoint,
    type DailyCandle,
    type SeriesPoint,
} from '../../features/dashboard/growthChartData';
import {
    ECHARTS_EMPTY_VALUE,
    PARTIAL_BUCKET_OPACITY,
    PNL_REFERENCE_SERIES_NAME,
    brokerColor,
    buildGrowthFullSeries,
    buildGrowthUpdateSeries,
    clipToSign,
    findReferenceTotalPnl,
    splitBySign,
    toCandlestickPoint,
    type EurLabels,
    type GrowthSeriesContext,
    type PnlLabels,
    type PnlSubmode,
} from '../../features/dashboard/growthChartSeries';
import {buildGrowthTooltip, type GrowthTooltipView} from '../../features/dashboard/growthChartTooltip';
import {chooseInitialResolution, type ChartResolution} from './timeSeriesAggregation';

function signal(overrides: Partial<RenderedSignal>): RenderedSignal {
    return {
        id: 'signal',
        label: 'Signal',
        data: [{date: '2026-07-23', value: 1}],
        color: '#3b82f6',
        lineWidth: 1,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
        aggregationProfile: 'last_with_range',
        ...overrides,
    };
}

function axisNamed(layout: ReturnType<typeof buildSecondaryYAxes>, name: string): ReturnType<typeof buildSecondaryYAxes>['axes'][number] {
    const axis = layout.axes.find((candidate) => candidate.name === name);
    expect(axis).toBeDefined();
    return axis;
}

function importedTranslationStoreReference(source: string): string {
    const importSpecifiers = source.match(/import\s+\{([^}]*)\}\s+from\s+['"]\$lib\/i18n['"]/)?.[1];
    if (!importSpecifiers) throw new Error('Svelte translation store import not found');

    const translationSpecifier = importSpecifiers
        .split(',')
        .map((specifier) => specifier.trim())
        .find((specifier) => /^_(?:\s+as\s+[A-Za-z_$][\w$]*)?$/.test(specifier));
    if (!translationSpecifier) throw new Error('Svelte translation store binding not found');

    const localIdentifier = translationSpecifier.match(/^_\s+as\s+([A-Za-z_$][\w$]*)$/)?.[1] ?? '_';
    return `$${localIdentifier}`;
}

function translationCallPattern(storeReference: string, key: string): RegExp {
    const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`${escapeRegExp(storeReference)}\\(\\s*(['"])${escapeRegExp(key)}\\1\\s*\\)`);
}

function responsiveAxisLabel(policy: ReturnType<typeof buildResponsiveXAxisPolicy>): NonNullable<ReturnType<typeof buildResponsiveXAxisPolicy>['axisLabel']> {
    expect(policy.axisLabel).toBeDefined();
    if (!policy.axisLabel) throw new Error('Expected compact responsive axis labels');
    return policy.axisLabel;
}

describe('canonical overlay axis and reference helpers', () => {
    it('shares indexes by canonical axis key and allocates multiple independent axes', () => {
        const assigned = assignOverlaySignalAxes([
            signal({id: 'price', axisKey: 'price', axisRole: 'price'}),
            signal({id: 'rsi', axisKey: 'rsi', axisRole: 'independent', axisMinimum: 0, axisMaximum: 100, axisLabel: 'RSI'}),
            signal({id: 'stoch-k', axisKey: 'stoch-rsi', axisRole: 'independent', axisLabel: 'Stochastic RSI'}),
            signal({id: 'stoch-d', axisKey: 'stoch-rsi', axisRole: 'independent', axisLabel: 'Stochastic RSI'}),
        ]);

        expect(Object.fromEntries(assigned.map((item) => [item.id, item.yAxisIndex]))).toEqual({
            price: 0,
            rsi: 1,
            'stoch-k': 2,
            'stoch-d': 2,
        });

        const layout = buildSecondaryYAxes(assigned, false);
        expect(layout.axes).toHaveLength(2);
        expect(layout.nextAxisIndex).toBe(3);
        const rsiAxis = axisNamed(layout, 'RSI');
        expect(rsiAxis.min).toBe(1);
        expect(rsiAxis.max).toBe(1);
        expect(rsiAxis.scale).toBe(true);
        expect(layout.extraAxesCount).toBe(2);
        expect(computeRightMargin(3)).toBe(170);
    });

    it('preserves legacy explicit RSI/MACD indexes', () => {
        const assigned = assignOverlaySignalAxes([signal({id: 'legacy-rsi', yAxisIndex: 1, axisLabel: 'Legacy RSI'}), signal({id: 'legacy-macd', yAxisIndex: 2, axisLabel: 'Legacy MACD'})]);
        expect(Object.fromEntries(assigned.map((item) => [item.id, item.yAxisIndex]))).toEqual({
            'legacy-rsi': 1,
            'legacy-macd': 2,
        });

        const legacyMacd = assigned.find((item) => item.id === 'legacy-macd');
        expect(legacyMacd).toBeDefined();
        expect(secondaryAxisSettingsKey(legacyMacd!)).toBe('legacy:2');

        const layout = buildSecondaryYAxes(assigned, false, 0, true, {
            'legacy:2': {mode: 'custom', min: 25, max: -10},
        });
        expect(axisNamed(layout, 'Legacy MACD')).toMatchObject({
            min: -10,
            max: 25,
            scale: true,
        });
    });

    interface AxisLabelFallbackCase {
        name: string;
        expectedKey: string;
        expectedParams: Record<string, string>;
        expectedFallback: string;
        resolve: (translate: AxisLabelTranslator) => string;
    }

    const AXIS_LABEL_FALLBACK_CASES: AxisLabelFallbackCase[] = [
        {
            name: 'price',
            expectedKey: 'chartSettings.axes.price',
            expectedParams: {currency: 'USD'},
            expectedFallback: 'Price axis (USD)',
            resolve: (translate) => priceAxisLabel(translate, 'USD'),
        },
        {
            name: 'percentage',
            expectedKey: 'chartSettings.axes.percentage',
            expectedParams: {},
            expectedFallback: 'Percentage axis',
            resolve: percentageAxisLabel,
        },
        {
            name: 'exchange pair',
            expectedKey: 'chartSettings.axes.exchangeRate',
            expectedParams: {pair: 'EUR/USD'},
            expectedFallback: 'Exchange-rate axis (EUR/USD)',
            resolve: (translate) => exchangeRateAxisLabel(translate, 'EUR/USD'),
        },
        {
            name: 'volume',
            expectedKey: 'chartSettings.axes.volume',
            expectedParams: {},
            expectedFallback: 'Volume axis',
            resolve: (translate) =>
                secondaryAxisLabel(translate, {
                    key: 'independent:turnover',
                    label: 'Turnover',
                    unit: 'volume',
                }),
        },
        {
            name: 'RSI',
            expectedKey: 'chartSettings.axes.signal',
            expectedParams: {name: 'RSI'},
            expectedFallback: 'RSI axis',
            resolve: (translate) => secondaryAxisLabel(translate, {key: 'independent:rsi', label: 'RSI'}),
        },
        {
            name: 'MACD',
            expectedKey: 'chartSettings.axes.signal',
            expectedParams: {name: 'MACD'},
            expectedFallback: 'MACD axis',
            resolve: (translate) => secondaryAxisLabel(translate, {key: 'independent:macd', label: 'MACD'}),
        },
        {
            name: 'generic signal',
            expectedKey: 'chartSettings.axes.signal',
            expectedParams: {name: 'Momentum'},
            expectedFallback: 'Momentum axis',
            resolve: (translate) => secondaryAxisLabel(translate, {key: 'independent:custom', label: 'Momentum'} satisfies ConfigurableAxisDescriptor),
        },
    ];

    describe('axis label helpers', () => {
        it.each(AXIS_LABEL_FALLBACK_CASES)('$name requests the exact translation contract and falls back when the key is unresolved', ({expectedKey, expectedParams, expectedFallback, resolve}) => {
            const translate = vi.fn((key: string, params?: Record<string, string>) => {
                expect(key).toBe(expectedKey);
                expect(params).toEqual(expectedParams);
                return key;
            });

            expect(resolve(translate)).toBe(expectedFallback);
            expect(translate).toHaveBeenCalledTimes(1);
        });
    });

    describe('axis label adoption contract', () => {
        it('routes every settings preview row through semantic axis label helpers', () => {
            const source = readFileSync(new URL('./ChartSettingsModal.svelte', import.meta.url), 'utf8');
            const previewRowsContract = source.match(/let previewPrimaryLabel = \$derived\.by\([\s\S]*?let previewAxisRows = \$derived\(\[[\s\S]*?\]\);/)?.[0];

            expect(source).toMatch(/import\s+\{\s*exchangeRateAxisLabel,\s*percentageAxisLabel,\s*priceAxisLabel,\s*secondaryAxisLabel\s*\}\s+from\s+['"]\.\/axisLabelHelpers['"]/);
            expect(previewRowsContract).toBeDefined();
            if (!previewRowsContract) throw new Error('ChartSettingsModal preview axis rows contract not found');

            expect(previewRowsContract).toContain('percentageAxisLabel(translate)');
            expect(previewRowsContract).toContain('exchangeRateAxisLabel(translate, context)');
            expect(previewRowsContract).toContain('priceAxisLabel(translate, context)');
            expect(previewRowsContract).toContain('label: previewPrimaryLabel');
            expect(previewRowsContract).toContain('label: secondaryAxisLabel(');
            expect(previewRowsContract).not.toMatch(/label:\s*['"]%['"]/);
            expect(previewRowsContract).not.toMatch(/label:\s*['"]Abs['"]/);
            expect(previewRowsContract).not.toMatch(/label:\s*axis\.label\b/);
        });

        it('has the asset list pass its currency context and imported translation-store Preview fallback', () => {
            const source = readFileSync(new URL('../../../routes/(app)/assets/+page.svelte', import.meta.url), 'utf8');
            const modal = source.match(/<ChartSettingsModal\b[\s\S]*?\/>/)?.[0];
            const translationStore = importedTranslationStoreReference(source);

            expect(modal).toBeDefined();
            if (!modal) throw new Error('asset list ChartSettingsModal invocation not found');

            expect(modal).toContain('axisDomain="asset"');
            expect(modal).toContain('axisContext={settingsTargetId ?');
            expect(modal).toContain('assets.find((asset) => asset.id === Number(settingsTargetId))?.currency');
            expect(modal).toMatch(translationCallPattern(translationStore, 'common.preview'));
        });

        it('has the FX list pass an inversion-aware settings axis context and imported translation-store Preview fallback', () => {
            const source = readFileSync(new URL('../../../routes/(app)/fx/+page.svelte', import.meta.url), 'utf8');
            const modal = source.match(/<ChartSettingsModal\b[\s\S]*?\/>/)?.[0];
            const settingsAxisContext = source.match(/let settingsAxisContext = \$derived\.by\(\(\) => \{[\s\S]*?\n\s*\}\);/)?.[0];
            const translationStore = importedTranslationStoreReference(source);

            expect(modal).toBeDefined();
            if (!modal) throw new Error('FX list ChartSettingsModal invocation not found');
            expect(settingsAxisContext).toBeDefined();
            if (!settingsAxisContext) throw new Error('FX list settingsAxisContext contract not found');

            expect(modal).toContain('axisDomain="fx"');
            expect(modal).toContain('axisContext={settingsAxisContext}');
            expect(modal).not.toMatch(/axisContext=\{settingsTargetSlug\s*\?/);
            expect(settingsAxisContext).toMatch(translationCallPattern(translationStore, 'common.preview'));
            expect(settingsAxisContext).toContain('const pair = pairs.find((item) => item.config.slug === settingsTargetSlug);');
            expect(settingsAxisContext).toContain("if (!pair) return settingsTargetSlug.replace('-', '/');");
            expect(settingsAxisContext).toMatch(/return\s+isCardInverted\(settingsTargetSlug\)\s*\?\s*`\$\{pair\.config\.quote\}\/\$\{pair\.config\.base\}`\s*:\s*`\$\{pair\.config\.base\}\/\$\{pair\.config\.quote\}`;/);
            expect(source).toMatch(/import\s+\{\s*isCardInverted\s*\}\s+from\s+['"]\$lib\/stores\/fx\/fxCardInversionStore['"]/);
        });

        /**
         * Y-39a, «parity between the card and the preview»: each list page draws its cards' saved signals through
         * `$lib/charts/chartSignalRendering`, and hands its settings modal the same sources, `signalSources`. The two maps
         * the preview read until then went away with the modal props of the same names: `pairsDataMap` (each pair turned by
         * its own card, where the card turns it by the signal's own `_inverted`) and `assetsDataMap` (no target name, so the
         * preview called a comparison «Asset #id»). A prop counts as passed in both forms Svelte takes, `name=` and the
         * shorthand `{name}`.
         */
        const SIGNAL_SOURCE_LIST_PAGES = [
            ['asset list', new URL('../../../routes/(app)/assets/+page.svelte', import.meta.url)],
            ['FX list', new URL('../../../routes/(app)/fx/+page.svelte', import.meta.url)],
        ] as const;

        /** Whether a component invocation passes `prop`: as `prop=…`, or as the shorthand `{prop}`. */
        const passesProp = (invocation: string, prop: string): boolean => new RegExp(`\\s(?:${prop}\\s*=(?!=)|\\{\\s*${prop}\\s*\\})`).test(invocation);

        it.each(SIGNAL_SOURCE_LIST_PAGES)('Y-39a: the %s hands ChartSettingsModal signalSources, and neither pairsDataMap nor assetsDataMap', (page, path) => {
            const source = readFileSync(path, 'utf8');
            const modal = source.match(/<ChartSettingsModal\b[\s\S]*?\/>/)?.[0];

            expect(modal).toBeDefined();
            if (!modal) throw new Error(`${page} ChartSettingsModal invocation not found`);
            // Controls: the invocation is read whole — a `/>` inside an attribute's expression would cut it short, and a
            // cut one would pass none of the props below — and the helper sees a prop every invocation passes.
            expect(modal.split('{').length, `${page}: the ChartSettingsModal invocation is not read whole`).toBe(modal.split('}').length);
            expect(passesProp(modal, 'settings'), `${page}: control — the invocation passes its settings`).toBe(true);

            expect(
                {signalSources: passesProp(modal, 'signalSources'), pairsDataMap: passesProp(modal, 'pairsDataMap'), assetsDataMap: passesProp(modal, 'assetsDataMap')},
                `${page}: the settings preview does not get the cards' signalSources in place of the two data maps, so it cannot draw the FX pairs and the comparisons as the cards do`,
            ).toEqual({signalSources: true, pairsDataMap: false, assetsDataMap: false});
        });

        it.each(SIGNAL_SOURCE_LIST_PAGES)('Y-39a: the %s imports $lib/charts/chartSignalRendering, the renderer its cards and its settings preview share', (page, path) => {
            const source = readFileSync(path, 'utf8');
            const clauses = [...source.matchAll(/import\s+(type\s+)?([^;'"]*?)\s*\bfrom\s*['"]\$lib\/charts\/chartSignalRendering['"]/g)].filter(([, typeOnly]) => !typeOnly).map(([, , clause]) => clause.trim());
            // A value binding: a namespace, or a specifier that is not `type …` — a type alone renders nothing.
            const valueImports = clauses.filter(
                (clause) =>
                    /^\*\s*as\s+[\w$]+$/.test(clause) ||
                    clause
                        .replace(/^\{|\}$/g, '')
                        .split(',')
                        .map((specifier) => specifier.trim())
                        .some((specifier) => specifier !== '' && !/^type\s/.test(specifier)),
            );

            expect(valueImports, `${page}: draws its saved signals without $lib/charts/chartSignalRendering`).not.toEqual([]);
        });
    });

    const SHORT_X_AXIS_DATES = ['2026-01-01', '2026-01-02'] as const;
    const JANUARY_X_AXIS_DATES = Array.from({length: 31}, (_, index) => `2026-01-${String(index + 1).padStart(2, '0')}`);
    const GROWTH_TIME_AXIS_DATES = ['2025-09-01', '2026-09-01'] as const;
    /**
     * The edge alignment a compact policy gives a CATEGORY axis, and only its last label (R-2, lot 51): a centred anchor
     * pushes that label half out of the chart, while the first one spills at most into the y-axis label column on its left,
     * inside the chart, and is never cut.
     */
    const COMPACT_CATEGORY_END_ALIGNMENT = {alignMaxLabel: 'right'} as const;

    describe('responsive X-axis policy', () => {
        it('budgets the 315px Growth-like time axis separately from a category axis', () => {
            const timePolicy = buildResponsiveXAxisPolicy({
                width: 315,
                values: GROWTH_TIME_AXIS_DATES,
                locale: 'en-US',
                axisType: 'time',
            });
            const categoryPolicy = buildResponsiveXAxisPolicy({
                width: 315,
                values: GROWTH_TIME_AXIS_DATES,
                locale: 'en-US',
                axisType: 'category',
            });
            const growthXAxis = {
                type: 'time' as const,
                boundaryGap: true,
                splitNumber: timePolicy.splitNumber,
                axisLabel: timePolicy.axisLabel,
            };

            expect(timePolicy).toMatchObject({
                compact: true,
                maxLabels: 5,
                splitNumber: 5,
                axisLabel: {
                    hideOverlap: true,
                    showMinLabel: true,
                    showMaxLabel: true,
                    rotate: 0,
                },
            });
            expect(categoryPolicy).toMatchObject({
                compact: true,
                maxLabels: 4,
                axisLabel: {
                    hideOverlap: true,
                    showMinLabel: true,
                    showMaxLabel: true,
                    rotate: 0,
                },
            });
            expect(timePolicy).not.toHaveProperty('boundaryGap');
            expect(growthXAxis).toMatchObject({
                boundaryGap: true,
                splitNumber: 5,
                axisLabel: {
                    hideOverlap: true,
                    showMinLabel: true,
                    showMaxLabel: true,
                    rotate: 0,
                },
            });
        });

        it('replaces only the label formatter on a caller-specific desktop axis and emits no responsive-only keys', () => {
            const desktopFormatter = vi.fn((value: number | string) => `growth:${value}`);
            const baseline = {
                type: 'time' as const,
                boundaryGap: true,
                axisLabel: {
                    color: '#475569',
                    fontSize: 14,
                    formatter: desktopFormatter,
                },
                axisLine: {lineStyle: {color: '#f1f5f9'}},
                splitLine: {show: false},
            };
            const policy = buildResponsiveXAxisPolicy({
                width: 1000,
                values: GROWTH_TIME_AXIS_DATES,
                locale: 'en-US',
                axisType: 'time',
            });
            // Why (re-pin, plan 47 C3): a desktop policy carries a localized formatter too, so a
            // wide chart stops showing ECharts' English defaults. The charts merge it as below: the
            // caller's keys, then the policy's formatter, then the compact-only keys (none here).
            const applied = {
                ...baseline,
                ...(policy.compact ? {splitNumber: policy.splitNumber} : {}),
                axisLabel: {
                    ...baseline.axisLabel,
                    formatter: policy.formatter,
                    ...(policy.axisLabel ?? {}),
                },
            };

            expect(policy).toEqual({
                compact: false,
                maxLabels: GROWTH_TIME_AXIS_DATES.length,
                formatter: expect.any(Function),
            });
            expect(policy).not.toHaveProperty('splitNumber');
            expect(policy).not.toHaveProperty('axisLabel');
            expect(applied).toEqual({...baseline, axisLabel: {...baseline.axisLabel, formatter: policy.formatter}});
            expect(applied.axisLabel.formatter).toBe(policy.formatter);
            expect(applied.axisLabel.formatter).not.toBe(desktopFormatter);
            // 1 September 2025, a month tick: the month alone, localized.
            expect(applied.axisLabel.formatter(new Date(2025, 8, 1).getTime())).toBe(new Intl.DateTimeFormat('en-US', {month: 'short'}).format(new Date(2025, 8, 1)));
            expect(desktopFormatter).not.toHaveBeenCalled();
            expect(applied).not.toHaveProperty('splitNumber');
            expect(applied.axisLabel).not.toHaveProperty('hideOverlap');
            expect(applied.axisLabel).not.toHaveProperty('showMinLabel');
            expect(applied.axisLabel).not.toHaveProperty('showMaxLabel');
            expect(applied.axisLabel).not.toHaveProperty('rotate');
            // R-2: the edge alignment is compact-only. A wide axis does not force its end labels, so its last drawn label may sit mid-axis.
            expect(applied.axisLabel).not.toHaveProperty('alignMinLabel');
            expect(applied.axisLabel).not.toHaveProperty('alignMaxLabel');
        });

        it.each([315, 337])('keeps the 48px time budget and one-year Growth-like SSR tick gaps within 50px at width %i', (width) => {
            const start = Date.UTC(2025, 8, 1);
            const end = Date.UTC(2026, 8, 1);
            const policy = buildResponsiveXAxisPolicy({
                width,
                values: GROWTH_TIME_AXIS_DATES,
                locale: 'en-US',
                axisType: 'time',
            });
            const growthDataZoom = {
                type: 'inside' as const,
                ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG,
                start: 0,
                end: 100,
            };
            const growthXAxis = {
                type: 'time' as const,
                boundaryGap: true,
                splitNumber: policy.splitNumber,
                axisLabel: {
                    color: '#475569',
                    fontSize: 14,
                    ...policy.axisLabel,
                },
                axisLine: {lineStyle: {color: '#f1f5f9'}},
                splitLine: {show: false},
            };
            const chart = echarts.init(null, undefined, {
                renderer: 'svg',
                ssr: true,
                width,
                height: 240,
            });

            try {
                chart.setOption({
                    useUTC: true,
                    animation: false,
                    grid: {left: '3%', right: '4%', bottom: '30px', top: '10px', containLabel: true},
                    dataZoom: [growthDataZoom],
                    xAxis: growthXAxis,
                    yAxis: {type: 'value'},
                    series: [
                        {
                            type: 'line',
                            data: [
                                [start, 100],
                                [end, 112],
                            ],
                        },
                    ],
                });

                const dataZoomBeforeResponsiveUpdate = JSON.parse(JSON.stringify(chart.getOption().dataZoom));
                chart.setOption(
                    {
                        xAxis: {
                            splitNumber: policy.splitNumber,
                            axisLabel: policy.axisLabel,
                        },
                    },
                    {lazyUpdate: false},
                );
                const svg = chart.renderToSVGString();
                type RenderedTimeAxisReader = {
                    getModel(): {
                        getComponent(
                            componentType: 'xAxis',
                            index: 0,
                        ): {
                            axis: {
                                scale: {
                                    getTicks(): Array<{value: number}>;
                                };
                            };
                        };
                    };
                };
                const xAxisModel = (chart as unknown as RenderedTimeAxisReader).getModel().getComponent('xAxis', 0);
                const endpointPixels = [start, end].map((value) => Number(chart.convertToPixel({xAxisIndex: 0}, value))).sort((left, right) => left - right);
                const endpointValues = new Set([start, end]);
                const visibleCandidates = xAxisModel.axis.scale
                    .getTicks()
                    .map(({value}) => ({
                        value,
                        pixel: Number(chart.convertToPixel({xAxisIndex: 0}, value)),
                    }))
                    .filter(({value, pixel}) => value >= start && value <= end && Number.isFinite(pixel) && pixel >= endpointPixels[0] - 0.5 && pixel <= endpointPixels[1] + 0.5)
                    .sort((left, right) => Number(endpointValues.has(right.value)) - Number(endpointValues.has(left.value)) || left.pixel - right.pixel);
                const nonCoincidentCandidates = visibleCandidates.filter((candidate, index, candidates) => candidates.findIndex((other) => Math.abs(other.pixel - candidate.pixel) < 1) === index).sort((left, right) => left.pixel - right.pixel);
                const positiveGaps = nonCoincidentCandidates
                    .slice(1)
                    .map((candidate, index) => candidate.pixel - nonCoincidentCandidates[index].pixel)
                    .filter((gap) => gap > 0);

                expect(svg).toMatch(/^<svg\b/);
                expect(policy.compact).toBe(true);
                expect(policy.maxLabels).toBe(Math.floor((width - 64) / 48));
                expect(policy.splitNumber).toBe(5);
                expect(policy.axisLabel).toMatchObject({
                    hideOverlap: true,
                    showMinLabel: true,
                    showMaxLabel: true,
                    rotate: 0,
                });
                expect(nonCoincidentCandidates).toHaveLength(7);
                expect(nonCoincidentCandidates.at(0)).toMatchObject({
                    value: start,
                    pixel: endpointPixels[0],
                });
                expect(nonCoincidentCandidates.at(-1)).toMatchObject({
                    value: end,
                    pixel: endpointPixels[1],
                });
                expect(positiveGaps).toHaveLength(6);
                expect(positiveGaps.every((gap) => gap <= 50)).toBe(true);
                expect(Math.max(...positiveGaps)).toBeLessThanOrEqual(50);
                expect(chart.getOption().dataZoom).toEqual(dataZoomBeforeResponsiveUpdate);
            } finally {
                chart.dispose();
            }
        });

        it('switches at 480 usable pixels after horizontal padding', () => {
            const below = buildResponsiveXAxisPolicy({width: 543, values: SHORT_X_AXIS_DATES, axisType: 'category'});
            const atThreshold = buildResponsiveXAxisPolicy({width: 544, values: SHORT_X_AXIS_DATES, axisType: 'category'});

            expect(below.compact).toBe(true);
            expect(atThreshold.compact).toBe(false);
        });

        it('enters compact mode when point density drops below 24 pixels', () => {
            const dense = buildResponsiveXAxisPolicy({width: 800, values: JANUARY_X_AXIS_DATES, axisType: 'category'});
            const atOrAboveBudget = buildResponsiveXAxisPolicy({width: 800, values: JANUARY_X_AXIS_DATES.slice(0, 30), axisType: 'category'});

            expect(dense.compact).toBe(true);
            expect(atOrAboveBudget.compact).toBe(false);
        });

        it('derives the category stride from the compact label budget', () => {
            const policy = buildResponsiveXAxisPolicy({
                width: 344,
                values: JANUARY_X_AXIS_DATES.slice(0, 10),
                axisType: 'category',
            });

            expect(policy.compact).toBe(true);
            expect(policy.maxLabels).toBe(5);
            expect(responsiveAxisLabel(policy).interval).toBe(2);
        });

        it('never sets splitNumber for a category-axis policy, compact or not — the GrowthChart resize watcher relies on exactly this to stay unforked when the P&L candles submode switches the axis to category (splitNumber is a time/value/log-axis-only concept)', () => {
            const compactCategory = buildResponsiveXAxisPolicy({width: 320, values: JANUARY_X_AXIS_DATES, axisType: 'category'});
            const desktopCategory = buildResponsiveXAxisPolicy({width: 1000, values: JANUARY_X_AXIS_DATES, axisType: 'category'});

            expect(compactCategory.compact).toBe(true);
            expect(desktopCategory.compact).toBe(false);
            expect(compactCategory).not.toHaveProperty('splitNumber');
            expect(desktopCategory).not.toHaveProperty('splitNumber');
            expect(compactCategory.splitNumber).toBeUndefined();
        });

        it.each([
            ['compact category', 320, 'category'],
            ['compact time', 320, 'time'],
        ] as const)('preserves both endpoint labels and rotation 0 for %s', (_name, width, axisType) => {
            const policy = buildResponsiveXAxisPolicy({width, values: SHORT_X_AXIS_DATES, axisType});
            const axisLabel = responsiveAxisLabel(policy);

            expect(axisLabel.showMinLabel).toBe(true);
            expect(axisLabel.showMaxLabel).toBe(true);
            expect(axisLabel.hideOverlap).toBe(true);
            expect(axisLabel.rotate).toBe(0);
        });

        it.each([
            ['minimum compact budget', 176, JANUARY_X_AXIS_DATES, 2],
            ['mobile compact budget', 344, JANUARY_X_AXIS_DATES, 5],
        ] as const)('sets the time-axis split budget for %s', (_name, width, values, expectedSplitNumber) => {
            const policy = buildResponsiveXAxisPolicy({width, values, axisType: 'time'});

            expect(policy.splitNumber).toBe(expectedSplitNumber);
        });

        it('formats compact dates through the requested locale', () => {
            // Through the policy, the only way a chart reaches the formatter. The value is the
            // middle day, neither end of the data nor the 1st of a month: a plain day tick.
            const values = ['2026-02-01', '2026-02-03', '2026-02-05'] as const;
            const value = values[1];
            const localDate = new Date(2026, 1, 3);
            const english = responsiveAxisLabel(buildResponsiveXAxisPolicy({width: 320, values, locale: 'en-US', axisType: 'time'})).formatter(value);
            const italian = responsiveAxisLabel(buildResponsiveXAxisPolicy({width: 320, values, locale: 'it-IT', axisType: 'time'})).formatter(value);

            expect(english).toBe(new Intl.DateTimeFormat('en-US', {day: 'numeric', month: 'short'}).format(localDate));
            expect(italian).toBe(new Intl.DateTimeFormat('it-IT', {day: 'numeric', month: 'short'}).format(localDate));
            expect(italian).not.toBe(english);
        });

        it.each([
            ['365-day common-year span', ['2025-03-30', '2026-03-30'], 365],
            ['366-day leap-year span', ['2023-03-27', '2024-03-27'], 366],
        ] as const)('keeps year-bearing, distinct endpoints for a %s across the Europe/Rome DST boundary', (_name, values, expectedSpanDays) => {
            const previousTimeZone = process.env.TZ;
            process.env.TZ = 'Europe/Rome';
            try {
                const [firstYear, firstMonth, firstDay] = values[0].split('-').map(Number);
                const [lastYear, lastMonth, lastDay] = values[1].split('-').map(Number);
                const firstDate = new Date(firstYear, firstMonth - 1, firstDay);
                const lastDate = new Date(lastYear, lastMonth - 1, lastDay);
                expect((Date.UTC(lastYear, lastMonth - 1, lastDay) - Date.UTC(firstYear, firstMonth - 1, firstDay)) / 86_400_000).toBe(expectedSpanDays);
                expect(Math.abs(lastDate.getTime() - firstDate.getTime()) / 86_400_000).not.toBe(expectedSpanDays);

                const compact = buildResponsiveXAxisPolicy({width: 320, values, locale: 'en-US', axisType: 'time'});
                const desktop = buildResponsiveXAxisPolicy({width: 1000, values, locale: 'en-US', axisType: 'time'});
                // Both values are ends of the data, in two different years: each is named by its day, with the year (plan 47, C1).
                const expectedCompactFirst = new Intl.DateTimeFormat('en-US', {day: 'numeric', month: 'short', year: '2-digit'}).format(firstDate);
                const expectedCompactLast = new Intl.DateTimeFormat('en-US', {day: 'numeric', month: 'short', year: '2-digit'}).format(lastDate);
                const compactAxisLabel = responsiveAxisLabel(compact);

                expect(compact.compact).toBe(true);
                expect(compactAxisLabel.formatter(values[0])).toBe(expectedCompactFirst);
                expect(compactAxisLabel.formatter(values[1])).toBe(expectedCompactLast);
                expect(compactAxisLabel.formatter(values[1])).not.toBe(compactAxisLabel.formatter(values[0]));

                // Why (re-pin, plan 47 C3): a desktop policy carries its own localized formatter, still without any compact-only key.
                expect(desktop).toEqual({
                    compact: false,
                    maxLabels: values.length,
                    formatter: expect.any(Function),
                });
                expect(desktop).not.toHaveProperty('axisLabel');
            } finally {
                if (previousTimeZone === undefined) delete process.env.TZ;
                else process.env.TZ = previousTimeZone;
            }
        });

        it('replaces the compact formatter when a multi-year time axis returns to desktop', () => {
            const values = ['2024-01-01', '2026-01-01'] as const;
            const value = values[0];
            const localDate = new Date(2024, 0, 1);
            const compact = buildResponsiveXAxisPolicy({width: 320, values, locale: 'it-IT', axisType: 'time'});
            const desktop = buildResponsiveXAxisPolicy({width: 1000, values, locale: 'it-IT', axisType: 'time'});
            // The first end of data that crosses a year: its day, with the year (plan 47, C1).
            const expectedCompact = new Intl.DateTimeFormat('it-IT', {day: 'numeric', month: 'short', year: '2-digit'}).format(localDate);
            // Why (re-pin, plan 47 C3): the desktop label now comes from the policy, which has no
            // end-of-data rule: 1 January is named by its year, as any 1 January tick.
            const expectedDesktop = new Intl.DateTimeFormat('it-IT', {year: 'numeric'}).format(localDate);
            const desktopBaseline = {
                color: '#475569',
                fontSize: 14,
                formatter: (axisValue: number | string) => new Intl.DateTimeFormat('it-IT', {year: 'numeric', month: 'short', day: 'numeric'}).format(new Date(`${axisValue}T00:00:00`)),
            };
            const compactPolicyAxisLabel = responsiveAxisLabel(compact);
            // The charts' merge order: the caller's keys, the policy's formatter, then the compact-only keys.
            const compactAxisLabel = {...desktopBaseline, formatter: compact.formatter, ...(compact.axisLabel ?? {})};
            const restoredDesktopAxisLabel = {...desktopBaseline, formatter: desktop.formatter, ...(desktop.axisLabel ?? {})};

            expect(compact.compact).toBe(true);
            expect(desktop.compact).toBe(false);
            expect(typeof desktop.formatter, 'a desktop policy carries its own label formatter (plan 47, C3)').toBe('function');
            expect(compactPolicyAxisLabel.formatter(value)).toBe(expectedCompact);
            expect(compactAxisLabel.formatter(value)).toBe(expectedCompact);
            expect(restoredDesktopAxisLabel.formatter).toBe(desktop.formatter);
            expect(restoredDesktopAxisLabel.formatter(value)).toBe(expectedDesktop);
            expect(expectedDesktop).not.toBe(expectedCompact);
            expect(desktop).not.toHaveProperty('axisLabel');
            expect(restoredDesktopAxisLabel).toEqual({...desktopBaseline, formatter: desktop.formatter});
        });

        it('takes a lot-chart desktop formatter from the policy instead of the caller, without changing compact labels', () => {
            const values = ['2024-01-01', '2026-01-01'] as const;
            const value = values[1];
            const desktopFormatter = vi.fn((axisValue: number | string) => `lot:${axisValue}`);
            const baseline = {
                color: '#475569',
                fontSize: 14,
                formatter: desktopFormatter,
            };
            const compact = buildResponsiveXAxisPolicy({width: 320, values, locale: 'en-US', axisType: 'time'});
            const desktop = buildResponsiveXAxisPolicy({width: 1000, values, locale: 'en-US', axisType: 'time'});
            const compactPolicyAxisLabel = responsiveAxisLabel(compact);
            // Why (re-pin, plan 47 C3): the lot charts no longer keep a desktop formatter of their
            // own; both modes take it from the policy, merged after the caller's keys and before
            // the compact-only ones.
            const compactAxisLabel = {...baseline, formatter: compact.formatter, ...(compact.axisLabel ?? {})};
            const desktopAxisLabel = {...baseline, formatter: desktop.formatter, ...(desktop.axisLabel ?? {})};

            expect(compact.compact).toBe(true);
            expect(desktop.compact).toBe(false);
            expect(typeof desktop.formatter, 'a desktop policy carries its own label formatter (plan 47, C3)').toBe('function');
            // The last end of data that crosses a year: its day, with the year (plan 47, C1).
            expect(compactPolicyAxisLabel.formatter(value)).toBe(new Intl.DateTimeFormat('en-US', {day: 'numeric', month: 'short', year: '2-digit'}).format(new Date(2026, 0, 1)));
            expect(compactAxisLabel.formatter).not.toBe(desktopFormatter);
            expect(compactAxisLabel.formatter(value)).toBe(new Intl.DateTimeFormat('en-US', {day: 'numeric', month: 'short', year: '2-digit'}).format(new Date(2026, 0, 1)));
            // Desktop: no end-of-data rule, so 1 January is named by its year.
            expect(desktopAxisLabel).toEqual({...baseline, formatter: desktop.formatter});
            expect(desktopAxisLabel.formatter(value)).toBe(new Intl.DateTimeFormat('en-US', {year: 'numeric'}).format(new Date(2026, 0, 1)));
            expect(desktopFormatter).not.toHaveBeenCalled();
        });

        // ── Plan 47 (C1): a compact date label names its day, so two neighbours never repeat a month ──
        //
        // WHY: the compact formatter chose ONE format for the whole axis from the span of the data
        // (over 90 days: the month alone). ECharts ticks a three-month daily axis every week, so the
        // developer's screenshot of the Growth chart (Abs, about 800 px) read "lug lug ago ago ago ago
        // set set …". The approved rules name each label by what it is: an end of the data, a year, a
        // month boundary among days, a month, a day. Every expected string comes from Intl in the same
        // locale, never from a literal: the ICU data moves between Node versions.

        const COMPACT_FORMATS: Record<'dm' | 'dmy' | 'm' | 'my' | 'y', Intl.DateTimeFormatOptions> = {
            dm: {day: 'numeric', month: 'short'},
            dmy: {day: 'numeric', month: 'short', year: '2-digit'},
            m: {month: 'short'},
            my: {month: 'short', year: '2-digit'},
            y: {year: 'numeric'},
        };

        /** `isoDate` ('YYYY-MM-DD', a local calendar day) as the approved rules write it in `format`. */
        function compactLabel(locale: string, format: keyof typeof COMPACT_FORMATS, isoDate: string): string {
            const [year, month, day] = isoDate.split('-').map(Number);
            return new Intl.DateTimeFormat(locale, COMPACT_FORMATS[format]).format(new Date(year, month - 1, day));
        }

        /** Every calendar day from `first` to `last`, both included, that `keep` accepts. Stepped in UTC, so a DST change neither drops nor doubles a day. */
        function isoDays(first: string, last: string, keep: (isoDate: string) => boolean = () => true): string[] {
            const days: string[] = [];
            for (let ms = Date.parse(`${first}T00:00:00Z`); ms <= Date.parse(`${last}T00:00:00Z`); ms += 86_400_000) {
                const isoDate = new Date(ms).toISOString().slice(0, 10);
                if (keep(isoDate)) days.push(isoDate);
            }
            return days;
        }

        /** Monday to Friday: the days a category axis of market prices carries. */
        const isWeekday = (isoDate: string) => ![0, 6].includes(new Date(`${isoDate}T00:00:00Z`).getUTCDay());

        /** Runs `run` in Europe/Rome, where local midnight and the DST changes are those of the developer's machine, and restores the zone whatever happens. */
        function withRomeTimeZone<T>(run: () => T): T {
            const previousTimeZone = process.env.TZ;
            process.env.TZ = 'Europe/Rome';
            try {
                return run();
            } finally {
                if (previousTimeZone === undefined) delete process.env.TZ;
                else process.env.TZ = previousTimeZone;
            }
        }

        /** The compact formatter as ECharts calls it: `(tick value, index, {level})` on a time axis, `(category value, index)` on a category axis. */
        type CompactFormatter = (value: number | string, index?: number, extra?: {level?: number}) => string;

        function compactFormatter(policy: ReturnType<typeof buildResponsiveXAxisPolicy>): CompactFormatter {
            expect(policy.compact, 'a compact policy').toBe(true);
            return responsiveAxisLabel(policy).formatter;
        }

        /** The stride of a compact category axis: label `i` is a regular one when `i % step === 0`. No interval means every label is. */
        function regularStep(policy: ReturnType<typeof buildResponsiveXAxisPolicy>): number {
            const interval = responsiveAxisLabel(policy).interval ?? 0;
            if (interval === 'auto') throw new Error('A compact category policy sets a numeric interval');
            return interval + 1;
        }

        /** Every pair of neighbouring labels that read the same, as `a | a`: the defect, named in the diff. */
        function consecutiveDuplicates(labels: readonly string[]): string[] {
            return labels.slice(1).flatMap((label, index) => (label === labels[index] ? [`${labels[index]} | ${label}`] : []));
        }

        /** Where zrender placed a `<text>`: its own `x`/`y` (0 when omitted) through its `transform`, a `translate(…)` or a `matrix(…)`. */
        function svgTextPosition(attributes: string): {x: number; y: number} {
            const attribute = (name: string) => Number(new RegExp(`\\b${name}="([^"]*)"`).exec(attributes)?.[1] ?? 0);
            const localX = attribute('x');
            const localY = attribute('y');
            const transform = /\btransform="(translate|matrix)\(([^)]*)\)"/.exec(attributes);
            if (!transform) return {x: localX, y: localY};
            const parts = transform[2]
                .trim()
                .split(/[\s,]+/)
                .map(Number);
            const [a, b, c, d, e, f] = transform[1] === 'translate' ? [1, 0, 0, 1, parts[0], parts[1] ?? 0] : parts;
            return {x: a * localX + c * localY + e, y: b * localX + d * localY + f};
        }

        const decodeSvgText = (text: string) =>
            text
                .replace(/&lt;/g, '<')
                .replace(/&gt;/g, '>')
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/&amp;/g, '&');

        /**
         * The CSS font a `<text>` was laid out with. zrender writes either one `font:` shorthand or, when the label style
         * names its parts (ECharts' does), `font-size`/`font-family`/… declarations: rebuilt here in zrender's own
         * `makeFont` order (style, weight, size, family), so measuring the text matches its layout.
         */
        function svgTextFont(attributes: string): string | null {
            const style = /\bstyle="([^"]*)"/.exec(attributes)?.[1] ?? '';
            const declarations = new Map([...style.matchAll(/([a-z-]+)\s*:\s*([^;]+)/g)].map(([, property, value]): [string, string] => [property, value.trim()]));
            const shorthand = declarations.get('font');
            if (shorthand) return shorthand;
            const size = declarations.get('font-size');
            if (!size) return null;
            return [declarations.get('font-style'), declarations.get('font-weight'), size, declarations.get('font-family') ?? 'sans-serif'].filter(Boolean).join(' ');
        }

        /**
         * A drawn x-axis label: its text, where zrender placed it, the `text-anchor` its alignment became (left → start,
         * center → middle, right → end) and the CSS font it was laid out with, as the `<text>` style carries it.
         */
        interface RenderedXAxisLabel {
            text: string;
            anchor: string | null;
            font: string | null;
            x: number;
            y: number;
        }

        /**
         * The x-axis labels a real ECharts draws for `option`, left to right: every `<text>` of the
         * server-side SVG below the plot, empty ones dropped. A label `hideOverlap` hides is not
         * emitted at all, so the list is what a user reads. WHY no `useUTC`: no production chart
         * sets it, so ticks fall on local midnights, as on screen.
         */
        function renderedXAxisLabelElements(option: echarts.EChartsCoreOption, width: number, height: number): RenderedXAxisLabel[] {
            type GridRectReader = {getModel(): {getComponent(componentType: 'grid', index: 0): {coordinateSystem?: {getRect(): {y: number; height: number}}} | undefined}};
            const chart = echarts.init(null, undefined, {renderer: 'svg', ssr: true, width, height});
            try {
                chart.setOption(option);
                const svg = chart.renderToSVGString();
                const plot = (chart as unknown as GridRectReader).getModel().getComponent('grid', 0)?.coordinateSystem?.getRect();
                if (!plot) throw new Error('The rendered chart has no laid-out grid');
                const plotBottom = plot.y + plot.height;
                return [...svg.matchAll(/<text\b([^>]*)>([^<]*)<\/text>/g)]
                    .map(([, attributes, text]) => ({
                        text: decodeSvgText(text).trim(),
                        anchor: /\btext-anchor="([^"]*)"/.exec(attributes)?.[1] ?? null,
                        font: svgTextFont(attributes),
                        ...svgTextPosition(attributes),
                    }))
                    .filter(({text, y}) => text !== '' && y > plotBottom)
                    .sort((left, right) => left.x - right.x);
            } finally {
                chart.dispose();
            }
        }

        /** The texts of {@link renderedXAxisLabelElements}, left to right. */
        function renderedXAxisLabels(option: echarts.EChartsCoreOption, width: number, height: number): string[] {
            return renderedXAxisLabelElements(option, width, height).map(({text}) => text);
        }

        it('names the day on every compact time label of the Jul→Oct Growth screenshot, so no two neighbours repeat a month (plan 47, C1)', () => {
            withRomeTimeZone(() => {
                const dates = isoDays('2026-07-14', '2026-10-21');
                const policy = buildResponsiveXAxisPolicy({width: 800, values: dates, locale: 'it-IT', axisType: 'time'});
                const labels = renderedXAxisLabels(
                    {
                        animation: false,
                        xAxis: {type: 'time', splitNumber: policy.splitNumber, axisLabel: {fontSize: 14, rotate: 0, ...policy.axisLabel}},
                        yAxis: {type: 'value', scale: true, axisLabel: {show: false}},
                        series: [{type: 'line', data: dates.map((date, index) => [date, 100 + index])}],
                    },
                    800,
                    300,
                );
                const rendered = `rendered: ${labels.join(' | ')}`;

                // Preconditions: the screenshot's density makes the policy compact, and the axis is labelled.
                expect(policy.compact).toBe(true);
                expect(labels.length, rendered).toBeGreaterThanOrEqual(8);

                expect.soft(consecutiveDuplicates(labels), rendered).toEqual([]);
                expect
                    .soft(
                        labels.filter((label) => !/\d/.test(label)),
                        `${rendered} — every label names a day`,
                    )
                    .toEqual([]);
                expect.soft(labels, rendered).toEqual(expect.arrayContaining(['2026-08-01', '2026-09-01', '2026-10-01'].map((date) => compactLabel('it-IT', 'dm', date))));
                expect.soft([labels[0], labels.at(-1)], `${rendered} — the two ends of the data`).toEqual([compactLabel('it-IT', 'dm', '2026-07-14'), compactLabel('it-IT', 'dm', '2026-10-21')]);
            });
        });

        it('formats a compact time tick by what it is: an end of the data, a month boundary among days, a month, a day, or no midnight at all (plan 47, C1)', () => {
            withRomeTimeZone(() => {
                const dates = isoDays('2026-07-14', '2026-10-21');
                const formatter = compactFormatter(buildResponsiveXAxisPolicy({width: 800, values: dates, locale: 'it-IT', axisType: 'time'}));
                const label = (format: keyof typeof COMPACT_FORMATS, isoDate: string) => compactLabel('it-IT', format, isoDate);

                expect({
                    firstDataDay: formatter(new Date(2026, 6, 14).getTime(), 0, {level: 0}),
                    lastDataDay: formatter(new Date(2026, 9, 21).getTime(), 0, {level: 0}),
                    monthBoundaryAmongDays: formatter(new Date(2026, 7, 1).getTime(), 0, {level: 1}),
                    monthTick: formatter(new Date(2026, 7, 1).getTime(), 0, {level: 0}),
                    monthTickWithoutExtra: formatter(new Date(2026, 7, 1).getTime()),
                    dayTick: formatter(new Date(2026, 7, 15).getTime(), 0, {level: 0}),
                    notAMidnight: formatter(new Date(2026, 7, 15, 12).getTime()),
                    unparseable: formatter('not a date'),
                }).toEqual({
                    firstDataDay: label('dm', '2026-07-14'),
                    lastDataDay: label('dm', '2026-10-21'),
                    monthBoundaryAmongDays: label('dm', '2026-08-01'),
                    monthTick: label('m', '2026-08-01'),
                    monthTickWithoutExtra: label('m', '2026-08-01'),
                    dayTick: label('dm', '2026-08-15'),
                    notAMidnight: '',
                    unparseable: 'not a date',
                });
            });
        });

        it('gives the two ends of a compact time axis that crosses a year their year, and names 1 January by its year (plan 47, C1)', () => {
            withRomeTimeZone(() => {
                const dates = isoDays('2025-11-03', '2026-02-20');
                const formatter = compactFormatter(buildResponsiveXAxisPolicy({width: 800, values: dates, locale: 'it-IT', axisType: 'time'}));

                expect({
                    first: formatter(new Date(2025, 10, 3).getTime(), 0, {level: 0}),
                    last: formatter(new Date(2026, 1, 20).getTime(), 0, {level: 0}),
                    newYear: formatter(new Date(2026, 0, 1).getTime(), 0, {level: 2}),
                }).toEqual({
                    first: compactLabel('it-IT', 'dmy', '2025-11-03'),
                    last: compactLabel('it-IT', 'dmy', '2026-02-20'),
                    newYear: compactLabel('it-IT', 'y', '2026-01-01'),
                });
            });
        });

        it('names the last day of a lot-like range that ends mid-afternoon once, at its end, and leaves every tick that is not a midnight blank (plan 47, C1)', () => {
            withRomeTimeZone(() => {
                // Built inside the zone: a local midnight depends on it.
                const first = new Date(2026, 9, 18).getTime();
                const last = new Date(2026, 9, 21, 15, 30).getTime();
                const formatter = compactFormatter(buildResponsiveXAxisPolicy({width: 400, values: [first, last], locale: 'it-IT', axisType: 'time'}));

                expect({
                    first: formatter(first),
                    last: formatter(last),
                    lastDayMidnight: formatter(new Date(2026, 9, 21).getTime()),
                    dayBeforeLast: formatter(new Date(2026, 9, 20).getTime()),
                    dayBeforeLastNoon: formatter(new Date(2026, 9, 20, 12).getTime()),
                }).toEqual({
                    first: compactLabel('it-IT', 'dm', '2026-10-18'),
                    last: compactLabel('it-IT', 'dm', '2026-10-21'),
                    lastDayMidnight: '',
                    dayBeforeLast: compactLabel('it-IT', 'dm', '2026-10-20'),
                    dayBeforeLastNoon: '',
                });
            });
        });

        it('names the day on the labels of a compact category axis whose stride is shorter than a month, in the formatter and on the rendered axis (plan 47, C1)', () => {
            const dates = isoDays('2026-04-01', '2026-09-30', isWeekday);
            const policy = buildResponsiveXAxisPolicy({width: 800, values: dates, locale: 'it-IT', axisType: 'category'});
            const formatter = compactFormatter(policy);
            const step = regularStep(policy);
            const regularLabels = dates.flatMap((date, index) => (index % step === 0 ? [formatter(date, index)] : []));
            const rendered = renderedXAxisLabels(
                {
                    animation: false,
                    xAxis: {type: 'category', data: dates, boundaryGap: true, axisLabel: {fontSize: 14, ...policy.axisLabel}},
                    yAxis: {type: 'value', scale: true, axisLabel: {show: false}},
                    series: [{type: 'line', data: dates.map((_date, index) => 100 + index)}],
                },
                800,
                300,
            );

            // Preconditions: a stride, so only every `step`-th label is drawn, and an axis that draws them.
            expect(policy.axisLabel).toMatchObject({interval: expect.any(Number)});
            expect(rendered.length, `rendered: ${rendered.join(' | ')}`).toBeGreaterThanOrEqual(8);

            expect.soft(consecutiveDuplicates(regularLabels), `regular: ${regularLabels.join(' | ')}`).toEqual([]);
            expect
                .soft(
                    regularLabels.filter((label) => !/\d/.test(label)),
                    `regular: ${regularLabels.join(' | ')} — every label names a day`,
                )
                .toEqual([]);
            expect.soft(consecutiveDuplicates(rendered), `rendered: ${rendered.join(' | ')}`).toEqual([]);
        });

        it('names the months of a compact category axis whose labels all fall in different months, with the year at both ends and where the year changes (plan 47, C1)', () => {
            const dates = isoDays('2025-10-01', '2026-09-30', isWeekday);
            const policy = buildResponsiveXAxisPolicy({width: 400, values: dates, locale: 'it-IT', axisType: 'category'});
            const formatter = compactFormatter(policy);
            const step = regularStep(policy);
            const lastIndex = dates.length - 1;
            const regular = dates.flatMap((date, index) => (index % step === 0 ? [{index, date, label: formatter(date, index)}] : []));
            const regularText = `regular: ${regular.map(({label}) => label).join(' | ')}`;
            /** A regular label that must carry a year: the first, the last, and one whose regular neighbour on the left is in another year. */
            const bearsYear = (position: number) => position === 0 || regular[position].index === lastIndex || regular[position].date.slice(0, 4) !== regular[position - 1].date.slice(0, 4);
            const firstOf2026 = regular.find(({date}) => date.startsWith('2026'));
            if (!firstOf2026) throw new Error('No regular label falls in 2026');

            // Precondition: month mode. Every two neighbouring regular labels fall in different months, so a month can name each.
            expect(policy.axisLabel).toMatchObject({interval: expect.any(Number)});
            expect(regular.slice(1).filter(({date}, position) => date.slice(0, 7) === regular[position].date.slice(0, 7))).toEqual([]);

            expect.soft(consecutiveDuplicates(regular.map(({label}) => label)), regularText).toEqual([]);
            expect
                .soft(
                    regular.filter((_entry, position) => !bearsYear(position) && /\d/.test(regular[position].label)).map(({label}) => label),
                    `${regularText} — a month alone, away from the ends and the year change`,
                )
                .toEqual([]);
            expect
                .soft(
                    {
                        first: formatter(dates[0], 0),
                        firstOf2026: firstOf2026.label,
                        last: formatter(dates[lastIndex], lastIndex),
                    },
                    regularText,
                )
                .toEqual({
                    first: compactLabel('it-IT', 'my', dates[0]),
                    firstOf2026: compactLabel('it-IT', 'my', firstOf2026.date),
                    // The last index is a regular label (a month) or an extra one ECharts adds at the end (a day).
                    last: compactLabel('it-IT', lastIndex % step === 0 ? 'my' : 'dmy', dates[lastIndex]),
                });
        });

        it('names a value outside the data of a compact category axis by its day, with the year on an axis that crosses one, and returns an unparseable value as it is (plan 47, C1)', () => {
            const dates = isoDays('2025-10-01', '2026-09-30', isWeekday);
            const formatter = compactFormatter(buildResponsiveXAxisPolicy({width: 400, values: dates, locale: 'it-IT', axisType: 'category'}));
            const sunday = '2026-03-15';

            // Precondition: a Sunday, so not one of the axis's weekdays.
            expect(dates).not.toContain(sunday);

            expect({outside: formatter(sunday), unparseable: formatter('not a date')}).toEqual({
                outside: compactLabel('it-IT', 'dmy', sunday),
                unparseable: 'not a date',
            });
        });

        // ── Plan 47 (C3): the non-compact path names its labels too, in the user's language ──
        //
        // WHY: a policy that was not compact returned `{compact: false, maxLabels}` and nothing else,
        // so a wide axis fell back to ECharts' own labels: English on a time axis ("Aug", "8"), the
        // raw ISO date on a category axis ("2026-03-04"), while the three lot charts kept a formatter
        // of their own that repeated the day on intraday ticks. The policy now carries a localized
        // `formatter` in both modes and every chart applies it. A time label follows the compact
        // rules without the end-of-data ones; a category label carries everything it needs, because
        // ECharts picks which labels it draws. Expected strings come from Intl, never from literals.

        /** The label formatter a policy carries in both modes since plan 47 (C3), after the preconditions that make a red explicit. */
        function policyFormatter(policy: ReturnType<typeof buildResponsiveXAxisPolicy>, compact: boolean): ResponsiveXAxisFormatter {
            expect(policy.compact, compact ? 'a compact policy' : 'a non-compact policy').toBe(compact);
            expect(typeof policy.formatter, 'the policy carries its own label formatter in both modes (plan 47, C3)').toBe('function');
            return policy.formatter;
        }

        /** The third argument ECharts passes to a time-axis formatter: the tick's level, under `time` and as the deprecated `level`. */
        const tickLevel = (level: number) => ({time: {level}, level});

        it('formats a non-compact time tick by what it is, with no end-of-data rule: a day, a month, a month boundary among days, or no midnight at all (plan 47, C3)', () => {
            withRomeTimeZone(() => {
                const dates = isoDays('2026-07-14', '2026-08-20');
                const formatter = policyFormatter(buildResponsiveXAxisPolicy({width: 1200, values: dates, locale: 'it-IT', axisType: 'time'}), false);
                const label = (format: keyof typeof COMPACT_FORMATS, isoDate: string) => compactLabel('it-IT', format, isoDate);
                const augustFirst = new Date(2026, 7, 1).getTime();

                expect({
                    firstDataDay: formatter(new Date(2026, 6, 14).getTime(), 0, tickLevel(0)),
                    lastDataDay: formatter(new Date(2026, 7, 20).getTime(), 0, tickLevel(0)),
                    dayTick: formatter(new Date(2026, 6, 22).getTime(), 0, tickLevel(0)),
                    monthTick: formatter(augustFirst, 0, tickLevel(0)),
                    monthTickWithoutExtra: formatter(augustFirst),
                    monthBoundaryAmongDays: formatter(augustFirst, 0, tickLevel(1)),
                    monthBoundaryDeprecatedLevelOnly: formatter(augustFirst, 0, {level: 1}),
                    monthBoundaryTimeLevelOnly: formatter(augustFirst, 0, {time: {level: 1}}),
                    notAMidnight: formatter(new Date(2026, 7, 15, 12).getTime()),
                    unparseable: formatter('not a date'),
                }).toEqual({
                    firstDataDay: label('dm', '2026-07-14'),
                    lastDataDay: label('dm', '2026-08-20'),
                    dayTick: label('dm', '2026-07-22'),
                    monthTick: label('m', '2026-08-01'),
                    monthTickWithoutExtra: label('m', '2026-08-01'),
                    monthBoundaryAmongDays: label('dm', '2026-08-01'),
                    monthBoundaryDeprecatedLevelOnly: label('dm', '2026-08-01'),
                    monthBoundaryTimeLevelOnly: label('dm', '2026-08-01'),
                    notAMidnight: '',
                    unparseable: 'not a date',
                });
            });
        });

        it('names the two ends of a non-compact time axis that crosses a year like any other day, where the compact axis adds the year, and names 1 January by its year (plan 47, C3)', () => {
            withRomeTimeZone(() => {
                const dates = isoDays('2025-12-20', '2026-01-10');
                const first = new Date(2025, 11, 20).getTime();
                const last = new Date(2026, 0, 10).getTime();
                const newYear = new Date(2026, 0, 1).getTime();
                const desktop = policyFormatter(buildResponsiveXAxisPolicy({width: 1000, values: dates, locale: 'it-IT', axisType: 'time'}), false);
                const compact = compactFormatter(buildResponsiveXAxisPolicy({width: 320, values: dates, locale: 'it-IT', axisType: 'time'}));

                expect({
                    first: desktop(first, 0, tickLevel(0)),
                    last: desktop(last, 0, tickLevel(0)),
                    firstAsData: desktop(dates[0]),
                    lastAsData: desktop(dates[dates.length - 1]),
                    newYear: desktop(newYear, 0, tickLevel(2)),
                    newYearWithoutExtra: desktop(newYear),
                }).toEqual({
                    first: compactLabel('it-IT', 'dm', '2025-12-20'),
                    last: compactLabel('it-IT', 'dm', '2026-01-10'),
                    firstAsData: compactLabel('it-IT', 'dm', '2025-12-20'),
                    lastAsData: compactLabel('it-IT', 'dm', '2026-01-10'),
                    newYear: compactLabel('it-IT', 'y', '2026-01-01'),
                    newYearWithoutExtra: compactLabel('it-IT', 'y', '2026-01-01'),
                });
                // The contrast: the compact axis keeps its end-of-data rule (plan 47, C1).
                expect({first: compact(first, 0, {level: 0}), last: compact(last, 0, {level: 0})}).toEqual({
                    first: compactLabel('it-IT', 'dmy', '2025-12-20'),
                    last: compactLabel('it-IT', 'dmy', '2026-01-10'),
                });
            });
        });

        it('names the last-day midnight of a lot-like non-compact range by its day, where the compact axis leaves it blank, and leaves the intraday ends of the data blank (plan 47, C3)', () => {
            withRomeTimeZone(() => {
                // Built inside the zone: a local midnight depends on it.
                const first = new Date(2026, 9, 20, 9).getTime();
                const last = new Date(2026, 9, 21, 15, 30).getTime();
                const lastDayMidnight = new Date(2026, 9, 21).getTime();
                const desktop = policyFormatter(buildResponsiveXAxisPolicy({width: 1000, values: [first, last], locale: 'it-IT', axisType: 'time'}), false);
                const compact = compactFormatter(buildResponsiveXAxisPolicy({width: 320, values: [first, last], locale: 'it-IT', axisType: 'time'}));

                expect({
                    lastDayMidnight: desktop(lastDayMidnight, 0, tickLevel(0)),
                    first: desktop(first),
                    last: desktop(last),
                }).toEqual({
                    lastDayMidnight: compactLabel('it-IT', 'dm', '2026-10-21'),
                    first: '',
                    last: '',
                });
                // The compact axis keeps its guard (plan 47, C1): there, that midnight would repeat the day its last end already names.
                expect(compact(lastDayMidnight)).toBe('');
            });
        });

        it('formats non-compact time labels through the requested locale (plan 47, C3)', () => {
            withRomeTimeZone(() => {
                const dates = isoDays('2026-07-14', '2026-08-20');
                const english = policyFormatter(buildResponsiveXAxisPolicy({width: 1200, values: dates, locale: 'en-US', axisType: 'time'}), false);
                const italian = policyFormatter(buildResponsiveXAxisPolicy({width: 1200, values: dates, locale: 'it-IT', axisType: 'time'}), false);
                const day = new Date(2026, 6, 22).getTime();
                const month = new Date(2026, 7, 1).getTime();

                expect({englishDay: english(day), italianDay: italian(day), englishMonth: english(month), italianMonth: italian(month)}).toEqual({
                    englishDay: compactLabel('en-US', 'dm', '2026-07-22'),
                    italianDay: compactLabel('it-IT', 'dm', '2026-07-22'),
                    englishMonth: compactLabel('en-US', 'm', '2026-08-01'),
                    italianMonth: compactLabel('it-IT', 'm', '2026-08-01'),
                });
                expect(italian(day)).not.toBe(english(day));
                expect(italian(month)).not.toBe(english(month));
            });
        });

        it.each([
            ['spring-forward', '2026-03-23', '2026-04-03', '2026-03-29', '2026-03-30', '2026-04-01'],
            ['fall-back', '2026-10-19', '2026-11-03', '2026-10-25', '2026-10-26', '2026-11-01'],
        ] as const)('names the local midnights of a non-compact time axis across the %s Europe/Rome DST change, and only them (plan 47, C3)', (_name, firstDate, lastDate, changeDate, dayAfterChange, monthStart) => {
            withRomeTimeZone(() => {
                const formatter = policyFormatter(buildResponsiveXAxisPolicy({width: 1200, values: isoDays(firstDate, lastDate), locale: 'it-IT', axisType: 'time'}), false);
                /** `isoDate` at `hour`, local time. Built inside the zone: a local midnight depends on it. */
                const localTime = (isoDate: string, hour = 0) => {
                    const [year, month, day] = isoDate.split('-').map(Number);
                    return new Date(year, month - 1, day, hour).getTime();
                };

                expect({
                    changeDay: formatter(localTime(changeDate), 0, tickLevel(0)),
                    dayAfterChange: formatter(localTime(dayAfterChange), 0, tickLevel(0)),
                    changeDayAtThree: formatter(localTime(changeDate, 3)),
                    monthStart: formatter(localTime(monthStart), 0, tickLevel(0)),
                }).toEqual({
                    changeDay: compactLabel('it-IT', 'dm', changeDate),
                    dayAfterChange: compactLabel('it-IT', 'dm', dayAfterChange),
                    changeDayAtThree: '',
                    monthStart: compactLabel('it-IT', 'm', monthStart),
                });
            });
        });

        it('names every label of a non-compact daily category axis by its day, the 1st of a month included, and adds the year to every label when the data cross one (plan 47, C3)', () => {
            const withinYear = isoDays('2026-03-20', '2026-04-10');
            const acrossYears = isoDays('2025-12-20', '2026-01-10');
            const withinYearFormatter = policyFormatter(buildResponsiveXAxisPolicy({width: 1000, values: withinYear, locale: 'it-IT', axisType: 'category'}), false);
            const acrossYearsFormatter = policyFormatter(buildResponsiveXAxisPolicy({width: 1000, values: acrossYears, locale: 'it-IT', axisType: 'category'}), false);

            // Preconditions: a 1st of a month among the days, and a 1 January among the days that cross a year.
            expect(withinYear).toContain('2026-04-01');
            expect(acrossYears).toContain('2026-01-01');

            expect(withinYear.map((date, index) => withinYearFormatter(date, index))).toEqual(withinYear.map((date) => compactLabel('it-IT', 'dm', date)));
            expect(acrossYears.map((date, index) => acrossYearsFormatter(date, index))).toEqual(acrossYears.map((date) => compactLabel('it-IT', 'dmy', date)));
        });

        it('names every label of a non-compact monthly category axis by its month, and adds the year to every label when the data cross one (plan 47, C3)', () => {
            const firstHalf = ['2026-01-01', '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01', '2026-06-01'];
            // One value a month, mid-month: the rule is about calendar months, not about the 1st.
            const acrossYears = ['2025-10-15', '2025-11-15', '2025-12-15', '2026-01-15', '2026-02-15', '2026-03-15'];
            const firstHalfFormatter = policyFormatter(buildResponsiveXAxisPolicy({width: 800, values: firstHalf, locale: 'it-IT', axisType: 'category'}), false);
            const acrossYearsFormatter = policyFormatter(buildResponsiveXAxisPolicy({width: 800, values: acrossYears, locale: 'it-IT', axisType: 'category'}), false);

            expect(firstHalf.map((date, index) => firstHalfFormatter(date, index))).toEqual(firstHalf.map((date) => compactLabel('it-IT', 'm', date)));
            expect(acrossYears.map((date, index) => acrossYearsFormatter(date, index))).toEqual(acrossYears.map((date) => compactLabel('it-IT', 'my', date)));
        });

        it('keeps the day on every label of a non-compact category axis that is not one value a month: weekly, irregular, a single value, or data with an unparseable value (plan 47, C3)', () => {
            const mondays = isoDays('2026-03-02', '2026-05-18', (isoDate) => new Date(`${isoDate}T00:00:00Z`).getUTCDay() === 1);
            // Two values share March, so these are not monthly data, though most neighbours fall in different months.
            const irregular = ['2026-01-15', '2026-02-15', '2026-03-01', '2026-03-31', '2026-04-15'];
            const single = ['2026-04-01'];
            const withUnparseable = ['2026-01-01', 'n/a', '2026-03-01'];
            const formatterFor = (values: readonly string[], width: number) => policyFormatter(buildResponsiveXAxisPolicy({width, values, locale: 'it-IT', axisType: 'category'}), false);
            const labelsOf = (values: readonly string[], width: number) => {
                const formatter = formatterFor(values, width);
                return values.map((value, index) => formatter(value, index));
            };

            // Precondition: weekly values, so neighbours share a month.
            expect(mondays.slice(0, 2)).toEqual(['2026-03-02', '2026-03-09']);

            expect({
                weekly: labelsOf(mondays, 1000),
                irregular: labelsOf(irregular, 800),
                single: labelsOf(single, 800),
                withUnparseable: labelsOf(withUnparseable, 800),
            }).toEqual({
                weekly: mondays.map((date) => compactLabel('it-IT', 'dm', date)),
                irregular: irregular.map((date) => compactLabel('it-IT', 'dm', date)),
                single: [compactLabel('it-IT', 'dm', '2026-04-01')],
                withUnparseable: [compactLabel('it-IT', 'dm', '2026-01-01'), 'n/a', compactLabel('it-IT', 'dm', '2026-03-01')],
            });
        });

        it('names a value outside the data of a non-compact category axis by the rule of its data, and returns an unparseable value as it is (plan 47, C3)', () => {
            const formatterFor = (values: readonly string[], width: number) => policyFormatter(buildResponsiveXAxisPolicy({width, values, locale: 'it-IT', axisType: 'category'}), false);
            const daily = formatterFor(isoDays('2026-03-20', '2026-04-10'), 1000);
            const dailyAcrossYears = formatterFor(isoDays('2025-12-20', '2026-01-10'), 1000);
            const monthly = formatterFor(['2026-01-01', '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01', '2026-06-01'], 800);
            const monthlyAcrossYears = formatterFor(['2025-10-15', '2025-11-15', '2025-12-15', '2026-01-15', '2026-02-15', '2026-03-15'], 800);

            // Each value lies past the end of its data.
            expect({
                daily: daily('2026-04-12'),
                dailyAcrossYears: dailyAcrossYears('2026-01-11'),
                monthly: monthly('2026-07-01'),
                monthlyAcrossYears: monthlyAcrossYears('2026-04-15'),
                unparseable: daily('not a date'),
            }).toEqual({
                daily: compactLabel('it-IT', 'dm', '2026-04-12'),
                dailyAcrossYears: compactLabel('it-IT', 'dmy', '2026-01-11'),
                monthly: compactLabel('it-IT', 'm', '2026-07-01'),
                monthlyAcrossYears: compactLabel('it-IT', 'my', '2026-04-15'),
                unparseable: 'not a date',
            });
        });

        it('formats non-compact category labels through the requested locale (plan 47, C3)', () => {
            const daily = isoDays('2026-03-20', '2026-04-10');
            const monthly = ['2026-01-01', '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01', '2026-06-01'];
            const formatterFor = (values: readonly string[], locale: string) => policyFormatter(buildResponsiveXAxisPolicy({width: 1000, values, locale, axisType: 'category'}), false);

            const labels = {
                englishDay: formatterFor(daily, 'en-US')('2026-03-24'),
                italianDay: formatterFor(daily, 'it-IT')('2026-03-24'),
                englishMonth: formatterFor(monthly, 'en-US')('2026-06-01'),
                italianMonth: formatterFor(monthly, 'it-IT')('2026-06-01'),
            };

            expect(labels).toEqual({
                englishDay: compactLabel('en-US', 'dm', '2026-03-24'),
                italianDay: compactLabel('it-IT', 'dm', '2026-03-24'),
                englishMonth: compactLabel('en-US', 'm', '2026-06-01'),
                italianMonth: compactLabel('it-IT', 'm', '2026-06-01'),
            });
            expect(labels.italianDay).not.toBe(labels.englishDay);
            expect(labels.italianMonth).not.toBe(labels.englishMonth);
        });

        it.each(['time', 'category'] as const)('gives a compact %s policy one label formatter, the same at its top level and in its axisLabel (plan 47, C3)', (axisType) => {
            const policy = buildResponsiveXAxisPolicy({width: 320, values: JANUARY_X_AXIS_DATES, locale: 'en-US', axisType});
            const formatter = policyFormatter(policy, true);

            expect(policy).toEqual({
                compact: true,
                maxLabels: expect.any(Number),
                ...(axisType === 'time' ? {splitNumber: expect.any(Number)} : {}),
                formatter: expect.any(Function),
                axisLabel: {
                    hideOverlap: true,
                    showMinLabel: true,
                    showMaxLabel: true,
                    rotate: 0,
                    formatter: expect.any(Function),
                    // R-2 (lot 51): only a category axis ends its last label at its tick; a time axis keeps the centred anchor.
                    ...(axisType === 'category' ? {interval: expect.any(Number), ...COMPACT_CATEGORY_END_ALIGNMENT} : {}),
                },
            });
            expect(responsiveAxisLabel(policy).formatter).toBe(formatter);
        });

        it('renders localized day labels on a wide time axis across a month boundary, with no neighbour repeated (plan 47, C3)', () => {
            withRomeTimeZone(() => {
                const dates = isoDays('2026-07-20', '2026-08-18');
                const policy = buildResponsiveXAxisPolicy({width: 1200, values: dates, locale: 'it-IT', axisType: 'time'});
                // Preconditions first: without a formatter the axis would draw ECharts' own English labels.
                policyFormatter(policy, false);
                const labels = renderedXAxisLabels(
                    {
                        animation: false,
                        xAxis: {type: 'time', axisLabel: {fontSize: 14, rotate: 0, formatter: policy.formatter, ...(policy.axisLabel ?? {})}},
                        yAxis: {type: 'value', scale: true, axisLabel: {show: false}},
                        series: [{type: 'line', data: dates.map((date, index) => [date, 100 + index])}],
                    },
                    1200,
                    300,
                );
                const rendered = `rendered: ${labels.join(' | ')}`;
                const dayLabels = new Set(dates.map((date) => compactLabel('it-IT', 'dm', date)));
                const localizedLabels = new Set([...dayLabels, ...dates.flatMap((date) => [compactLabel('it-IT', 'm', date), compactLabel('it-IT', 'y', date)])]);

                // Precondition: the axis is labelled.
                expect(labels.length, rendered).toBeGreaterThanOrEqual(2);

                expect
                    .soft(
                        labels.filter((label) => !localizedLabels.has(label)),
                        `${rendered} — every label is a localized day, month or year of the data`,
                    )
                    .toEqual([]);
                expect
                    .soft(
                        labels.some((label) => dayLabels.has(label)),
                        `${rendered} — the days are named`,
                    )
                    .toBe(true);
                expect.soft(consecutiveDuplicates(labels), rendered).toEqual([]);
            });
        });

        it('renders the year at each 1 January and localized months in between on a wide multi-year monthly time axis (plan 47, C3)', () => {
            withRomeTimeZone(() => {
                const dates = Array.from({length: 36}, (_value, index) => `${2024 + Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}-01`);
                const policy = buildResponsiveXAxisPolicy({width: 1200, values: dates, locale: 'it-IT', axisType: 'time'});
                // Preconditions first: without a formatter the axis would draw ECharts' own English labels.
                policyFormatter(policy, false);
                const labels = renderedXAxisLabels(
                    {
                        animation: false,
                        xAxis: {type: 'time', axisLabel: {fontSize: 14, rotate: 0, formatter: policy.formatter, ...(policy.axisLabel ?? {})}},
                        yAxis: {type: 'value', scale: true, axisLabel: {show: false}},
                        series: [{type: 'line', data: dates.map((date, index) => [date, 100 + index])}],
                    },
                    1200,
                    300,
                );
                const rendered = `rendered: ${labels.join(' | ')}`;
                const yearLabels = new Set(dates.map((date) => compactLabel('it-IT', 'y', date)));
                // January is named by its year, so its month name is not an expected label.
                const monthLabels = new Set(dates.filter((date) => date.slice(5, 7) !== '01').map((date) => compactLabel('it-IT', 'm', date)));

                // Precondition: the axis is labelled.
                expect(labels.length, rendered).toBeGreaterThanOrEqual(2);

                expect.soft(labels, `${rendered} — each 1 January inside the data is named by its year`).toEqual(expect.arrayContaining([compactLabel('it-IT', 'y', '2025-01-01'), compactLabel('it-IT', 'y', '2026-01-01')]));
                expect
                    .soft(
                        labels.filter((label) => !yearLabels.has(label) && !monthLabels.has(label)),
                        `${rendered} — a localized year or month`,
                    )
                    .toEqual([]);
                expect
                    .soft(
                        labels.some((label) => monthLabels.has(label)),
                        `${rendered} — the months between the years are named`,
                    )
                    .toBe(true);
                expect.soft(consecutiveDuplicates(labels), rendered).toEqual([]);
            });
        });

        it('renders localized day labels with their year, never raw ISO dates, on a wide category axis of daily dates across a year (plan 47, C3)', () => {
            const dates = isoDays('2025-12-15', '2026-01-08');
            const policy = buildResponsiveXAxisPolicy({width: 1200, values: dates, locale: 'it-IT', axisType: 'category'});
            // Preconditions first: without a formatter the axis would draw the raw ISO dates.
            policyFormatter(policy, false);
            const labels = renderedXAxisLabels(
                {
                    animation: false,
                    xAxis: {type: 'category', data: dates, boundaryGap: true, axisLabel: {fontSize: 14, formatter: policy.formatter, ...(policy.axisLabel ?? {})}},
                    yAxis: {type: 'value', scale: true, axisLabel: {show: false}},
                    series: [{type: 'line', data: dates.map((_date, index) => 100 + index)}],
                },
                1200,
                300,
            );
            const rendered = `rendered: ${labels.join(' | ')}`;
            const dayYearLabels = new Set(dates.map((date) => compactLabel('it-IT', 'dmy', date)));

            // Precondition: the axis is labelled.
            expect(labels.length, rendered).toBeGreaterThanOrEqual(2);

            expect
                .soft(
                    labels.filter((label) => /^\d{4}-\d{2}-\d{2}$/.test(label)),
                    `${rendered} — no raw ISO date`,
                )
                .toEqual([]);
            expect
                .soft(
                    labels.filter((label) => !dayYearLabels.has(label)),
                    `${rendered} — every label is a localized day of the data, with its year`,
                )
                .toEqual([]);
            expect.soft(consecutiveDuplicates(labels), rendered).toEqual([]);
        });

        it('aligns the last compact category label to the right of its tick, so it does not stick out of the chart (R-2)', () => {
            const policy = buildResponsiveXAxisPolicy({width: 360, values: JANUARY_X_AXIS_DATES, locale: 'en-US', axisType: 'category'});

            // Precondition: a phone width makes the policy compact, the mode that forces both end labels on.
            expect(policy.compact).toBe(true);
            expect(policy.axisLabel).toMatchObject({showMinLabel: true, showMaxLabel: true, ...COMPACT_CATEGORY_END_ALIGNMENT});
            // The first label spills at most into the y-axis label column, inside the chart: aligning it would only hide more labels.
            expect(policy.axisLabel).not.toHaveProperty('alignMinLabel');
        });

        it('keeps the edge alignment off a compact time policy, whose month and year ticks outrank its end labels (R-2 guard)', () => {
            const policy = buildResponsiveXAxisPolicy({width: 360, values: JANUARY_X_AXIS_DATES, locale: 'en-US', axisType: 'time'});

            // Precondition: compact, with the last label forced on.
            expect(policy.compact).toBe(true);
            expect(policy.axisLabel).toMatchObject({showMaxLabel: true});
            // A time label is ranked by its tick level (z2 = 10 + level) before `hideOverlap`, and the forced end label only
            // hides its immediate neighbour: pulled inwards, it would collide with a month or year tick and be the one hidden.
            expect(policy.axisLabel).not.toHaveProperty('alignMinLabel');
            expect(policy.axisLabel).not.toHaveProperty('alignMaxLabel');
        });

        it.each(['time', 'category'] as const)('keeps the edge alignment off a wide %s policy, whose last drawn label may sit mid-axis (R-2)', (axisType) => {
            const policy = buildResponsiveXAxisPolicy({width: 1000, values: JANUARY_X_AXIS_DATES, locale: 'en-US', axisType});

            expect(policy.compact).toBe(false);
            expect(policy.axisLabel ?? {}).not.toHaveProperty('alignMinLabel');
            expect(policy.axisLabel ?? {}).not.toHaveProperty('alignMaxLabel');
        });

        // Category only: its labels share one priority, so the forced last label always survives `hideOverlap`. On a time
        // axis a month tick outranks the end label, so the policy leaves a time axis centred (the R-2 guard above).
        it('keeps the first compact category label centred and ends the last at its tick on a 360px phone, both inside the chart (R-2)', () => {
            // 90 daily points: the last label reads "Oct 13", which a centred anchor pushes half out of the chart ("Oct 1").
            const width = 360;
            const dates = isoDays('2026-07-16', '2026-10-13');
            const policy = buildResponsiveXAxisPolicy({width, values: dates, locale: 'en-US', axisType: 'category'});
            const labels = renderedXAxisLabelElements(
                {
                    animation: false,
                    // LineChart's full-size grid: `containLabel` reserves the x labels' height and the y labels' width, but not
                    // what the last x label spills past the 12px right margin.
                    grid: {top: 20, right: computeRightMargin(0), bottom: 25, left: 10, containLabel: true},
                    // As LineChart applies the policy: its formatter, then the compact-only keys.
                    xAxis: {type: 'category', data: dates, axisLabel: {fontSize: 11, formatter: policy.formatter, ...policy.axisLabel}},
                    // Its y labels too: they move the plot, and so the first x label, inwards. Numbers, so no end label can match one.
                    yAxis: {type: 'value', scale: true},
                    series: [{type: 'line', data: dates.map((_date, index) => 100 + index)}],
                },
                width,
                240,
            );
            const rendered = `rendered: ${labels.map(({text, anchor}) => `${text} [${anchor}]`).join(' | ')}`;
            // Found by text, not by position: the first and the last date of the data, as the policy names them.
            const firstText = policy.formatter(dates[0]);
            const lastText = policy.formatter(dates[dates.length - 1]);
            const first = labels.filter(({text}) => text === firstText);
            const last = labels.filter(({text}) => text === lastText);
            // A label's horizontal extent: its anchor point, its anchor and the width ECharts' own measurer gives its font.
            const extent = ({text, anchor, font, x}: RenderedXAxisLabel) => {
                if (!font) throw new Error(`${rendered} — "${text}" carries no font to measure it with`);
                const textWidth = echarts.format.getTextRect(text, font).width;
                const left = anchor === 'end' ? x - textWidth : anchor === 'middle' ? x - textWidth / 2 : x;
                const right = left + textWidth;
                return {left, right, described: `"${text}" anchored ${anchor} at x=${x.toFixed(1)}, ${textWidth.toFixed(1)}px in "${font}": ${left.toFixed(1)}→${right.toFixed(1)}`};
            };

            // Preconditions: compact, two distinct end labels, each drawn exactly once.
            expect(policy.compact).toBe(true);
            expect(firstText).not.toBe(lastText);
            expect(first, `${rendered} — the first date "${firstText}" is drawn once`).toHaveLength(1);
            expect(last, `${rendered} — the last date "${lastText}" is drawn once`).toHaveLength(1);
            const firstExtent = extent(first[0]);
            const lastExtent = extent(last[0]);

            expect.soft(first[0].anchor, `${rendered} — the first label stays centred on its tick`).toBe('middle');
            expect.soft(last[0].anchor, `${rendered} — the last label ends at its tick`).toBe('end');
            expect.soft(firstExtent.left, `${firstExtent.described} — the first label starts inside the chart`).toBeGreaterThanOrEqual(0);
            expect.soft(lastExtent.right, `${lastExtent.described} — the last label ends inside the ${width}px chart`).toBeLessThanOrEqual(width);
        });

        describe('the visible window of a zoomed category axis (47-1)', () => {
            // 47-1: in compact mode the category label `interval` is computed on ALL the values, and no chart recomputes it
            // when the user zooms, so a window of 33 daily points out of 365 keeps the 365-point interval — one label every
            // 34 points — and shows only its two forced edge labels. The fix: `visibleCount`, when given, replaces
            // `values.length` in the compact decision (`usableWidth / pointCount < 24`) and in the label interval, while the
            // formatter still names every value of `values`, built with that interval; `visiblePointCountFromZoom` reads the
            // window off a dataZoom event. All at 800 px: 736 usable after the default 64 px padding, a budget of 12 labels
            // (56 px each). Expected texts come from Intl, never from literals.

            /** The 365 days of 2025: daily points, and a year crossed by none of them. */
            const YEAR = isoDays('2025-01-01', '2025-12-31');

            /** The decision a compact category policy makes, in one object, so a red names all of it at once. */
            const decisionOf = (policy: ReturnType<typeof buildResponsiveXAxisPolicy>) => ({compact: policy.compact, maxLabels: policy.maxLabels, interval: policy.axisLabel?.interval});

            it('sizes the labels on every value without visibleCount: 365 points at 800px are compact, 12 labels, one every 34 points (guard)', () => {
                // Why: the call every chart makes today must not move. ceil(364 / 11) − 1 = 33.
                expect(YEAR).toHaveLength(365);
                expect(decisionOf(buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category'}))).toEqual({compact: true, maxLabels: 12, interval: 33});
            });

            it('sizes the compact interval on the visible window: 33 of 365 points at 800px are labelled one every 3 points (interval 2)', () => {
                // Why: the reported defect. 736 / 33 ≈ 22 px a point, under 24, so still compact, but the 12 labels now spread
                // over the 33 points shown: ceil(32 / 11) − 1 = 2, where the whole axis would give 33.
                const policy = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 33});

                expect(decisionOf(policy)).toEqual({compact: true, maxLabels: 12, interval: 2});
            });

            it('leaves compact mode when the visible window is wide enough: 20 of 365 points at 800px get no compact axisLabel', () => {
                // Why: 736 / 20 = 36.8 px a point, over 24, and 736 px is over 480, so ECharts may place the labels itself.
                const policy = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 20});

                expect({compact: policy.compact, axisLabel: policy.axisLabel}).toEqual({compact: false, axisLabel: undefined});
                expect(typeof policy.formatter, 'a non-compact policy still carries its label formatter (plan 47, C3)').toBe('function');
            });

            it('names every value of the axis with the window’s interval: on a 3-point stride no label is a bare month', () => {
                // Why: the formatter decides month-or-day from the stride. On a 34-point stride every two neighbouring labels
                // fall in different months, so the regular ones read as bare months ("Jan", "Feb"); on the window's 3-point
                // stride they share a month, so every label of the year keeps its day. Only the mismatches are listed.
                const policy = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 33});
                const formatter = compactFormatter(policy);
                const notADay = YEAR.flatMap((date, index) => {
                    const label = formatter(date, index);
                    return label === compactLabel('en-US', 'dm', date) ? [] : [`${date} → ${label}`];
                });

                expect(notADay, 'labels that do not name their day').toEqual([]);
                expect(policy.formatter, 'one formatter, the same at the top level and in the axisLabel').toBe(formatter);
            });

            describe('visiblePointCountFromZoom — how many points a dataZoom event shows', () => {
                /** The helper, read off the module namespace: a named import of an export that does not exist yet would take every case of this file down with it. */
                function visibleCount(event: unknown, pointCount: number): number | null {
                    expect(typeof responsiveXAxis.visiblePointCountFromZoom, 'responsiveXAxis exports visiblePointCountFromZoom').toBe('function');
                    return responsiveXAxis.visiblePointCountFromZoom(event, pointCount);
                }

                // A window in data indices counts both ends; one in percent covers every index it touches,
                // floor(start / 100 × (n − 1)) to ceil(end / 100 × (n − 1)); the result is clamped to [1, n].
                it.each([
                    {name: 'batch, percent 50..100 of 365', event: {batch: [{start: 50, end: 100}]}, pointCount: 365, expected: 183},
                    {name: 'percent 0..100 of 365', event: {start: 0, end: 100}, pointCount: 365, expected: 365},
                    {name: 'indices 10..42', event: {startValue: 10, endValue: 42}, pointCount: 365, expected: 33},
                    {name: 'batch, indices before percent', event: {batch: [{start: 0, end: 100, startValue: 10, endValue: 42}]}, pointCount: 365, expected: 33},
                    {name: 'percent past the end, clamped', event: {start: 0, end: 150}, pointCount: 365, expected: 365},
                    {name: 'reversed indices, clamped', event: {startValue: 42, endValue: 10}, pointCount: 365, expected: 1},
                    {name: 'no window', event: {}, pointCount: 365, expected: null},
                    {name: 'no point on the axis', event: {start: 0, end: 50}, pointCount: 0, expected: null},
                ])('$name → $expected', ({event, pointCount, expected}) => {
                    expect(visibleCount(event, pointCount)).toBe(expected);
                });
            });

            describe('categoryAxisLabelPatch — the x-axis labels a zoom or a resize merges', () => {
                // 47-1: a zoom or a resize re-spaces the labels with `setOption({xAxis: {axisLabel: patch}})`, a merge, and ECharts
                // keeps every stored key a merge does not name. So the patch always names `interval` (the window's step, or 'auto'
                // when it needs none), and a window that leaves compact mode also names the keys the compact policy overrides, at
                // the values that let ECharts place the labels itself.

                it('carries a compact window’s axisLabel whole, its step included: 34 of 365 points at 800px merge interval 2', () => {
                    // Why: 736 / 34 ≈ 21.6 px a point, under 24, so compact; ceil(33 / 11) − 1 = 2.
                    const policy = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 34});
                    const axisLabel = responsiveAxisLabel(policy);
                    const patch = categoryAxisLabelPatch(policy);

                    expect(decisionOf(policy), 'precondition').toEqual({compact: true, maxLabels: 12, interval: 2});
                    expect(patch, 'every key of the policy’s axisLabel, at its value').toMatchObject(axisLabel);
                    expect(patch.formatter, 'the policy’s own formatter, not a copy').toBe(axisLabel.formatter);
                    expect(patch.interval, 'the window’s step').toBe(2);
                });

                it('names the step even when a compact window needs none: 4 of 365 points at 300px merge interval auto (the stale-step guard)', () => {
                    // Why: a phone zoomed in to 4 days. 236 usable px are under 480, so compact, and the budget of 4 labels (56 px
                    // each) covers the 4 points, so the policy sets no step. A merge that named none would keep the step of the
                    // window before; 'auto' hands the spacing back to ECharts.
                    const policy = buildResponsiveXAxisPolicy({width: 300, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 4});
                    const axisLabel = responsiveAxisLabel(policy);
                    const patch = categoryAxisLabelPatch(policy);

                    expect(decisionOf(policy), 'precondition').toEqual({compact: true, maxLabels: 4, interval: undefined});
                    expect(Object.keys(axisLabel), 'precondition: the policy names no step at all').not.toContain('interval');
                    expect(patch.interval, 'the step, named all the same').toBe('auto');
                    expect(patch, 'the rest is the policy’s axisLabel').toMatchObject(axisLabel);
                });

                it('hands a wide window’s labels back to ECharts: 20 of 365 points at 800px merge interval auto, the formatter and the defaults compact mode overrides', () => {
                    // Why: 736 / 20 = 36.8 px a point, so not compact, and the policy has no axisLabel to carry. The patch keeps its
                    // formatter (plan 47, C3) and resets what the compact policy overrides: the step to 'auto', overlap hiding off,
                    // and null, which ECharts reads as its own default, for the forced edge labels and the aligned last one. The
                    // compact `rotate: 0` is ECharts' default already.
                    const policy = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 20});

                    expect({compact: policy.compact, axisLabel: policy.axisLabel}, 'precondition').toEqual({compact: false, axisLabel: undefined});
                    expect(categoryAxisLabelPatch(policy)).toStrictEqual({interval: 'auto', formatter: policy.formatter, hideOverlap: false, showMinLabel: null, showMaxLabel: null, alignMaxLabel: null});
                });

                /** Asserts the x axis' axisLabel, as `getOption()` returns it, holds each key of `expected` at its value: one comparison, so a red names them all, and an absent key reads `undefined` where a stored null reads `null`. */
                function expectStoredXAxisLabel(chart: echarts.ECharts, expected: Record<string, unknown>, message: string): void {
                    const stored = (chart.getOption() as {xAxis?: Array<{axisLabel?: Record<string, unknown>}>}).xAxis?.[0]?.axisLabel;
                    if (!stored) throw new Error('getOption() holds no xAxis[0].axisLabel');
                    expect(Object.fromEntries(Object.keys(expected).map((key) => [key, stored[key]])), message).toEqual(expected);
                }

                /**
                 * A server-side ECharts with the year on a category axis, labelled as a chart labels it on its first draw: by the
                 * policy of the whole axis, one label every 34 points (interval 33). Handed to `run`, then disposed.
                 */
                function withWholeYearAxis(run: (chart: echarts.ECharts) => void): void {
                    const policy = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category'});
                    const chart = echarts.init(null, undefined, {
                        renderer: 'svg',
                        ssr: true,
                        width: 800,
                        height: 240,
                    });

                    try {
                        chart.setOption({
                            animation: false,
                            xAxis: {type: 'category', data: YEAR, axisLabel: {fontSize: 11, formatter: policy.formatter, ...policy.axisLabel}},
                            yAxis: {type: 'value'},
                            series: [{type: 'line', data: YEAR.map((_, index) => index)}],
                        });
                        expectStoredXAxisLabel(chart, {interval: 33, formatter: policy.formatter}, 'precondition: the step of the whole axis is stored');
                        run(chart);
                    } finally {
                        chart.dispose();
                    }
                }

                it('re-spaces the step a real ECharts stores: 33, then 2 for 34 of 365 points, then auto with the defaults back for 20 (SSR)', () => {
                    // Why: the charts' merge, replayed. They pass {lazyUpdate: true}, which defers the redraw only: `setOption` merges
                    // into the model before it reads the flag, so getOption() returns the same axisLabel. Merged eagerly here, so that
                    // the render below lays out the merged labels.
                    const zoomed = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 34});
                    const wide = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 20});

                    withWholeYearAxis((chart) => {
                        chart.setOption({xAxis: {axisLabel: categoryAxisLabelPatch(zoomed)}});
                        expectStoredXAxisLabel(chart, {interval: 2, formatter: zoomed.formatter}, 'after the patch of 34 of 365 points');

                        chart.setOption({xAxis: {axisLabel: categoryAxisLabelPatch(wide)}});
                        // A merged null is stored as null, not dropped: the key is there, at ECharts' own default.
                        expectStoredXAxisLabel(chart, {interval: 'auto', formatter: wide.formatter, hideOverlap: false, showMinLabel: null, showMaxLabel: null, alignMaxLabel: null}, 'after the patch of 20 of 365 points');
                        expect(chart.renderToSVGString(), 'the merged labels lay out').toMatch(/^<svg\b/);
                    });
                });

                it('keeps the stored step through a merge that names none: the wide patch without its interval leaves 33 (negative control, SSR)', () => {
                    // Why: the ECharts rule the patch answers. The merge replaces every key it names (the formatter, overlap hiding)
                    // and keeps the one it does not, so a window merged without a step would show the step of the window before.
                    const wide = buildResponsiveXAxisPolicy({width: 800, values: YEAR, locale: 'en-US', axisType: 'category', visibleCount: 20});
                    const withoutInterval = Object.fromEntries(Object.entries(categoryAxisLabelPatch(wide)).filter(([key]) => key !== 'interval'));

                    withWholeYearAxis((chart) => {
                        chart.setOption({xAxis: {axisLabel: withoutInterval}});
                        expectStoredXAxisLabel(chart, {interval: 33, formatter: wide.formatter, hideOverlap: false}, 'the keys merged are replaced, the step not named stays');
                    });
                });
            });
        });

        describe('timeAxisGridRight — the right inset for the last time label (plan 52, C1)', () => {
            // Plan 52, C1: `grid.containLabel` reserves the x labels' height, never the half-width a centred label overhangs
            // past the plot's right edge. A time axis ends exactly on the last day of the data (or of the zoom) and ECharts
            // labels that edge, so on a phone the last label was cut: «Oct 2» for «Oct 20». The fix widens `grid.right` to
            // half the widest label the axis can draw plus 2 px when that beats the base inset. Expected texts come from Intl,
            // from the real policy formatter or from what real ECharts draws, never from the helper's own enumeration.

            /** A measure answering `widthOf(text)` that records every text it is asked: what the helper measures IS its candidate set. */
            function recordingMeasure(widthOf: AxisLabelMeasure = () => 10): {measure: AxisLabelMeasure; texts: string[]} {
                const texts: string[] = [];
                const measure: AxisLabelMeasure = (text) => {
                    texts.push(text);
                    return widthOf(text);
                };
                return {measure, texts};
            }

            /** `isoDate` ('YYYY-MM-DD') as the local midnight the policy parses it to. */
            function localDay(isoDate: string): Date {
                const [year, month, day] = isoDate.split('-').map(Number);
                return new Date(year, month - 1, day);
            }

            /** Every local midnight from the day before `first` to the day after `last`: the ticks a time axis on those days can label. Stepped by calendar day, so a DST change neither drops nor doubles one. */
            function midnightsAround(first: string, last: string): Date[] {
                const start = localDay(first);
                const end = localDay(last);
                const stop = new Date(end.getFullYear(), end.getMonth(), end.getDate() + 1).getTime();
                const days: Date[] = [];
                for (let day = new Date(start.getFullYear(), start.getMonth(), start.getDate() - 1); day.getTime() <= stop; day = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1)) days.push(day);
                return days;
            }

            it('keeps the base when it already holds half the widest label: 40px labels on a 1280px chart stay on 4% (A1)', () => {
                // Why: desktop must not move. 4% of 1280 is 51.2px, more than the 22px inset, and the base comes back as given.
                const {measure} = recordingMeasure(() => 40);
                expect(timeAxisGridRight({width: 1280, values: isoDays('2026-07-16', '2026-10-20'), locale: 'en-US', base: '4%', measure})).toBe('4%');
            });

            it('returns the inset in px when it beats the base: 41px labels on a 360px phone need 23px, more than 4% (A2)', () => {
                // Why: ceil(41 / 2) + 2 = 23 > 14.4px, and a number is what ECharts reads as px.
                const {measure} = recordingMeasure(() => 41);
                expect(timeAxisGridRight({width: 360, values: isoDays('2026-07-16', '2026-10-20'), locale: 'en-US', base: '4%', measure})).toBe(23);
            });

            it('keeps a px base that already holds the inset: 30px labels need 17px, the 18px base stays (A3)', () => {
                // Why: a number base is px, compared as is and returned untouched when it wins (LotComparisonChart's 18).
                const {measure} = recordingMeasure(() => 30);
                expect(timeAxisGridRight({width: 360, values: isoDays('2025-12-20', '2026-01-10'), locale: 'en-US', base: 18, measure})).toBe(18);
            });

            it('widens a px base the inset beats: 34px labels need 19px, one more than the 18px base (A3)', () => {
                // Why: ceil(34 / 2) + 2 = 19 > 18, the pixel the last label lacked.
                const {measure} = recordingMeasure(() => 34);
                expect(timeAxisGridRight({width: 360, values: isoDays('2025-12-20', '2026-01-10'), locale: 'en-US', base: 18, measure})).toBe(19);
            });

            it.each([
                ['no values', [] as string[]],
                ['an endpoint that does not parse', ['not-a-date']],
            ])('returns the base and measures nothing for %s (A4)', (_case, values) => {
                // Why: no date, no label to fit, and every measure is a text layout: none is spent.
                const {measure, texts} = recordingMeasure(() => 99);
                expect(timeAxisGridRight({width: 360, values, locale: 'en-US', base: '4%', measure})).toBe('4%');
                expect(texts).toEqual([]);
            });

            it('sizes the inset on the widest text alone: one 61px label among 10px ones gives 33px (A5)', () => {
                // Why: the last date's label is the one cut on a phone; the inset follows the widest text, never an average or the first.
                const lastLabel = compactLabel('en-US', 'dm', '2026-10-20');
                const {measure} = recordingMeasure((text) => (text === lastLabel ? 61 : 10));
                expect(timeAxisGridRight({width: 360, values: isoDays('2026-07-16', '2026-10-20'), locale: 'en-US', base: '4%', measure})).toBe(33);
            });

            it('measures each candidate text once per call, and at least one (A6)', () => {
                // Why: every measure lays the text out; a repeat is pure cost, and an empty list means nothing was fitted.
                const {measure, texts} = recordingMeasure();
                timeAxisGridRight({width: 360, values: isoDays('2026-07-16', '2026-10-20'), locale: 'en-US', base: '4%', measure});
                expect(texts.length, 'texts measured').toBeGreaterThan(0);
                expect(
                    texts.filter((text, index) => texts.indexOf(text) !== index),
                    'texts measured more than once',
                ).toEqual([]);
            });

            it('measures the labels in the locale it is given: the Spanish day of the last date in es-ES, not the English one (A7)', () => {
                // Why: the widths must be those of the labels the policy draws, and those follow the interface locale (M-18).
                const spanish = compactLabel('es-ES', 'dm', '2026-10-20');
                const english = compactLabel('en-US', 'dm', '2026-10-20');
                const {measure, texts} = recordingMeasure();
                timeAxisGridRight({width: 360, values: isoDays('2026-07-16', '2026-10-20'), locale: 'es-ES', base: '4%', measure});
                expect(spanish, 'precondition: the two locales write the day apart').not.toBe(english);
                expect(texts).toContain(spanish);
                expect(texts).not.toContain(english);
            });

            it('covers a range over 366 days: the year labels, 29 February and both endpoints with their 2-digit year (A8)', () => {
                // Why: a long axis can tick any day of any year, the leap day included, and each January 1 as its year, while its
                // compact ends carry the year.
                const {measure, texts} = recordingMeasure();
                timeAxisGridRight({width: 360, values: isoDays('2023-11-20', '2026-02-10'), locale: 'en-US', base: '4%', measure});
                expect(texts).toEqual(
                    expect.arrayContaining([
                        compactLabel('en-US', 'y', '2024-01-01'),
                        compactLabel('en-US', 'y', '2025-01-01'),
                        compactLabel('en-US', 'y', '2026-01-01'),
                        compactLabel('en-US', 'dm', '2024-02-29'),
                        compactLabel('en-US', 'dmy', '2023-11-20'),
                        compactLabel('en-US', 'dmy', '2026-02-10'),
                    ]),
                );
            });

            it('fits one value with its neighbours: the day before, the day and the day after (A9)', () => {
                // Why: ECharts widens a one-point time extent by a day on each side, so both neighbours can be labelled ticks.
                const {measure, texts} = recordingMeasure();
                timeAxisGridRight({width: 360, values: ['2026-03-15'], locale: 'en-US', base: '4%', measure});
                expect(texts).toEqual(expect.arrayContaining(['2026-03-14', '2026-03-15', '2026-03-16'].map((isoDate) => compactLabel('en-US', 'dm', isoDate))));
            });

            it.each([
                ['inside one month', isoDays('2026-07-03', '2026-07-24')],
                ['across a month', isoDays('2026-09-20', '2026-10-10')],
                ['from Dec 20 to Jan 10', isoDays('2025-12-20', '2026-01-10')],
                ['over 366 days, given by its two endpoints', ['2023-11-20', '2026-02-10']],
                ['on one value', ['2026-03-15']],
            ])('measures every text the real policy formatter writes on a midnight of the axis, compact and wide, %s (A10)', (_case, values) => {
                // Why: the inset holds only if no label the axis can draw escapes the measure. The oracle is the policy's own
                // formatter at 360px (compact) and 1280px (wide), levels 0 and 1, never a copy of the helper's enumeration. The
                // multi-year range is given by its endpoints: daily, its density would make the 1280px policy compact too.
                const {measure, texts} = recordingMeasure();
                timeAxisGridRight({width: 360, values, locale: 'en-US', base: '4%', measure});
                const formatters = [policyFormatter(buildResponsiveXAxisPolicy({width: 360, values, locale: 'en-US', axisType: 'time'}), true), policyFormatter(buildResponsiveXAxisPolicy({width: 1280, values, locale: 'en-US', axisType: 'time'}), false)];
                const drawable = [...new Set(formatters.flatMap((formatter) => midnightsAround(values[0], values[values.length - 1]).flatMap((day) => [0, 1].map((level) => formatter(day.getTime(), 0, tickLevel(level))))))].filter((text) => text !== '');

                expect(drawable.length, 'precondition: the formatter names the midnights of the axis').toBeGreaterThan(0);
                expect(
                    drawable.filter((text) => !texts.includes(text)),
                    `measured: ${texts.join(' | ')}`,
                ).toEqual([]);
            });

            it('reads the label family from the chart model: 14px LF Test Sans (B1)', () => {
                // Why: the measure must lay text out in the font ECharts draws the labels with, the theme's family when it names one.
                const chart = {getModel: () => ({get: (path: unknown) => ((Array.isArray(path) ? path.join('.') : path) === 'textStyle.fontFamily' ? 'LF Test Sans' : undefined)})};
                expect(axisLabelFont(chart as unknown as Parameters<typeof axisLabelFont>[0], 14)).toBe('14px LF Test Sans');
            });

            it.each([
                ['no chart', null],
                ['a chart with no model', {}],
                ['a model not built yet', {getModel: () => undefined}],
                ['an empty family', {getModel: () => ({get: () => ''})}],
                ['a family that is not a string', {getModel: () => ({get: () => 42})}],
            ])('falls back to the ECharts default family off Windows for %s: 14px sans-serif (B2)', (_case, chart) => {
                // Why: before the first setOption, or under a theme that names no family, ECharts draws its labels in its own default.
                expect(axisLabelFont(chart as unknown as Parameters<typeof axisLabelFont>[0], 14)).toBe('14px sans-serif');
            });

            it('falls back to Microsoft YaHei on Windows, as ECharts does: 12px Microsoft YaHei (B3)', () => {
                // Why: ECharts picks its default family from navigator.platform; a measure in another family would size another text.
                // Restored by re-stubbing, never by unstubAllGlobals, which would drop the file's hoisted en-US navigator.
                const previous = globalThis.navigator;
                vi.stubGlobal('navigator', {...previous, platform: 'Win32'});
                try {
                    expect(axisLabelFont(null, 12)).toBe('12px Microsoft YaHei');
                } finally {
                    vi.stubGlobal('navigator', previous);
                }
            });

            it('measures a label with the ECharts text measurer in the resolved font (B4)', () => {
                // Why: the inset must come from the layout ECharts draws the label with, not from a guess per character.
                const width = axisLabelMeasure(null, 14)('Oct 20');
                expect(width).toBe(echarts.format.getTextRect('Oct 20', '14px sans-serif').width);
                expect(width).toBeGreaterThan(0);
            });

            describe('on a real ECharts time axis rendered server-side (C)', () => {
                // As the R-2 case reads a category axis: every label ECharts draws under the plot, its anchor, and its width in
                // its own font. Each case runs twice: with the base inset (it must cut a label today) and with the fix's.

                /** One chart of a C case: its option at a given `grid.right`, and what the fix is called with. */
                interface CutCase {
                    name: string;
                    width: number;
                    height: number;
                    base: number | string;
                    fontSize: number;
                    values: string[];
                    option: (right: number | string) => echarts.EChartsCoreOption;
                }

                /** GrowthChart (and AllocationHistoryChart) as it draws a time axis: the policy on the full data, its compact keys, 14px labels, an optional inside zoom between two local midnights. */
                function growthCase(width: number, dates: string[], zoom?: readonly [string, string]): CutCase {
                    const policy = buildResponsiveXAxisPolicy({width, values: dates, locale: 'en-US', axisType: 'time'});
                    return {
                        name: `Growth ${dates[0]} → ${dates[dates.length - 1]}${zoom ? ` zoomed ${zoom[0]} → ${zoom[1]}` : ''} at ${width}px`,
                        width,
                        height: 240,
                        base: '4%',
                        fontSize: 14,
                        values: dates,
                        option: (right) => ({
                            animation: false,
                            grid: {top: 20, right, bottom: 25, left: 10, containLabel: true},
                            xAxis: {type: 'time', ...(policy.compact ? {splitNumber: policy.splitNumber} : {}), axisLabel: {fontSize: 14, rotate: 0, formatter: policy.formatter, ...policy.axisLabel}},
                            yAxis: {type: 'value', scale: true},
                            series: [{type: 'line', data: dates.map((date, index) => [date, 100 + index])}],
                            ...(zoom ? {dataZoom: [{type: 'inside', startValue: localDay(zoom[0]).getTime(), endValue: localDay(zoom[1]).getTime()}]} : {}),
                        }),
                    };
                }

                /** LotComparisonChart's time axis: ECharts' default 12px labels (the chart sets no size), an 18px base, the policy on the date range with its 42px padding, weekly points plus the last day, 320px tall under its legend band. */
                function lotsCase(width: number, first: string, last: string): CutCase {
                    const days = isoDays(first, last);
                    const points = days.filter((_day, index) => index % 7 === 0 || index === days.length - 1);
                    const policy = buildResponsiveXAxisPolicy({width, values: [first, last], locale: 'en-US', axisType: 'time', horizontalPadding: 42});
                    return {
                        name: `Lots ${first} → ${last} at ${width}px`,
                        width,
                        height: 320,
                        base: 18,
                        fontSize: 12,
                        values: [first, last],
                        option: (right) => ({
                            animation: false,
                            grid: {top: 62, right, bottom: 34, left: 10, containLabel: true},
                            xAxis: {type: 'time', min: first, max: last, ...(policy.compact ? {splitNumber: policy.splitNumber} : {}), axisTick: {show: false}, axisLabel: {hideOverlap: true, formatter: policy.formatter, ...policy.axisLabel}},
                            yAxis: {type: 'value', scale: true},
                            series: [{type: 'line', data: points.map((date, index) => [date, 1000 + index * 3])}],
                        }),
                    };
                }

                /** Every label ECharts draws under the plot of `testCase` at `right`, with where it ends: the R-2 extent, from its anchor and its width in its own font. */
                function drawnLabels({option, width, height}: CutCase, right: number | string): Array<{text: string; end: number; described: string}> {
                    return renderedXAxisLabelElements(option(right), width, height).map(({text, anchor, font, x}) => {
                        if (!font) throw new Error(`"${text}" carries no font to measure it with`);
                        const textWidth = echarts.format.getTextRect(text, font).width;
                        const left = anchor === 'end' ? x - textWidth : anchor === 'middle' ? x - textWidth / 2 : x;
                        const end = left + textWidth;
                        return {text, end, described: `"${text}" anchored ${anchor} at x=${x.toFixed(1)}, ${textWidth.toFixed(1)}px in "${font}", ends at ${end.toFixed(1)}`};
                    });
                }

                const WIDTHS = [320, 360, 390, 440];
                const JUL_TO_OCT_13 = isoDays('2026-07-16', '2026-10-13');
                const CASES: CutCase[] = [
                    ...WIDTHS.map((width) => growthCase(width, isoDays('2026-07-16', '2026-10-20'))),
                    ...WIDTHS.map((width) => growthCase(width, isoDays('2025-12-20', '2026-01-10'))),
                    ...WIDTHS.map((width) => growthCase(width, JUL_TO_OCT_13, ['2026-08-03', '2026-09-28'])),
                    ...WIDTHS.map((width) => growthCase(width, JUL_TO_OCT_13, ['2026-07-25', '2026-08-28'])),
                    ...WIDTHS.map((width) => lotsCase(width, '2025-12-20', '2026-01-10')),
                ];

                it.each(CASES)('$name: the base inset lets a drawn label end past the chart (precondition)', (testCase) => {
                    // Why: the fix below proves something only where today cuts a label; a failing precondition is reported, never tuned away.
                    const drawn = drawnLabels(testCase, testCase.base);
                    expect(
                        drawn.filter(({end}) => end > testCase.width).map(({described}) => described),
                        `drawn: ${drawn.map(({described}) => described).join(' | ')}`,
                    ).not.toEqual([]);
                });

                it.each(CASES)('$name: every drawn label ends inside the chart, whole, once grid.right holds the inset (fix)', (testCase) => {
                    // Why: the user-visible defect. The label ECharts draws at the right edge must end inside the chart, the text
                    // cut today must still be drawn and whole, and every drawn text must be one the inset measured.
                    const {width, base, fontSize, values} = testCase;
                    const cutToday = drawnLabels(testCase, base)
                        .filter(({end}) => end > width)
                        .map(({text}) => text);
                    const {measure, texts} = recordingMeasure(axisLabelMeasure(null, fontSize));
                    const right = timeAxisGridRight({width, values, locale: 'en-US', base, measure});
                    const drawn = drawnLabels(testCase, right);
                    const rendered = `grid.right=${String(right)}; drawn: ${drawn.map(({described}) => described).join(' | ')}`;

                    expect(cutToday, 'precondition: the base inset cuts a label').not.toEqual([]);
                    expect
                        .soft(
                            drawn.filter(({end}) => end > width).map(({described}) => described),
                            `${rendered} — labels past the ${width}px edge`,
                        )
                        .toEqual([]);
                    expect
                        .soft(
                            cutToday.filter((text) => !drawn.some((label) => label.text === text && label.end <= width)),
                            `${rendered} — labels cut today and not drawn whole`,
                        )
                        .toEqual([]);
                    expect
                        .soft(
                            drawn.map(({text}) => text).filter((text) => !texts.includes(text)),
                            `${rendered} — drawn labels the inset never measured`,
                        )
                        .toEqual([]);
                });
            });
        });
    });

    const RESPONSIVE_X_AXIS_CHARTS = [
        ['LineChart', new URL('./LineChart.svelte', import.meta.url)],
        ['CandlestickChart', new URL('./CandlestickChart.svelte', import.meta.url)],
        ['PriceChartFull', new URL('./PriceChartFull.svelte', import.meta.url)],
        ['GrowthChart', new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url)],
        ['AllocationHistoryChart', new URL('../../features/dashboard/AllocationHistoryChart.svelte', import.meta.url)],
        ['LotGanttChart', new URL('../../features/brokers/lots/LotGanttChart.svelte', import.meta.url)],
        ['LotComparisonChart', new URL('../../features/brokers/lots/LotComparisonChart.svelte', import.meta.url)],
        ['LotWacPriceChart', new URL('../../features/brokers/lots/LotWacPriceChart.svelte', import.meta.url)],
    ] as const;

    const LOT_RESPONSIVE_X_AXIS_CHARTS = [
        ['LotGanttChart', new URL('../../features/brokers/lots/LotGanttChart.svelte', import.meta.url)],
        ['LotComparisonChart', new URL('../../features/brokers/lots/LotComparisonChart.svelte', import.meta.url)],
        ['LotWacPriceChart', new URL('../../features/brokers/lots/LotWacPriceChart.svelte', import.meta.url)],
    ] as const;

    /** The zoomable category charts (47-1): their labels follow the zoomed window, and their resize merges `categoryAxisLabelPatch(policy)`. */
    const ZOOM_RELABEL_CHARTS = new Set<(typeof RESPONSIVE_X_AXIS_CHARTS)[number][0]>(['LineChart', 'CandlestickChart', 'PriceChartFull']);

    describe('responsive X-axis adoption contract', () => {
        describe('Growth logical range preservation', () => {
            const narrowedDates = ['2026-01-10', '2026-01-20'] as const;

            it('retains a prior non-full range when the new history contains both boundaries', () => {
                const priorRange = {
                    startDate: '2026-01-10',
                    endDate: '2026-01-24',
                } satisfies GrowthLogicalRange;
                const newDates = ['2026-01-01', priorRange.startDate, priorRange.endDate, '2026-01-31'] as const;

                expect(clampGrowthLogicalRange(priorRange, newDates)).toEqual(priorRange);
            });

            it('clamps only the left boundary when the new history excludes it', () => {
                expect(
                    clampGrowthLogicalRange(
                        {
                            startDate: '2026-01-01',
                            endDate: '2026-01-18',
                        },
                        narrowedDates,
                    ),
                ).toEqual({
                    startDate: narrowedDates[0],
                    endDate: '2026-01-18',
                });
            });

            it('clamps only the right boundary when the new history excludes it', () => {
                expect(
                    clampGrowthLogicalRange(
                        {
                            startDate: '2026-01-12',
                            endDate: '2026-01-31',
                        },
                        narrowedDates,
                    ),
                ).toEqual({
                    startDate: '2026-01-12',
                    endDate: narrowedDates[1],
                });
            });

            it('clamps both boundaries when the new history excludes both', () => {
                expect(
                    clampGrowthLogicalRange(
                        {
                            startDate: '2026-01-01',
                            endDate: '2026-01-31',
                        },
                        narrowedDates,
                    ),
                ).toEqual({
                    startDate: narrowedDates[0],
                    endDate: narrowedDates[1],
                });
            });

            it('keeps a missing prior range null and maps the full date-domain fallback to the next zoom window', () => {
                const newDates = ['2026-01-10', '2026-01-15', '2026-01-20'] as const;
                const preservedRange = clampGrowthLogicalRange(null, newDates);
                const fallbackRange: GrowthLogicalRange = preservedRange ?? {
                    startDate: newDates[0],
                    endDate: newDates.at(-1)!,
                };
                const buildZoomWindow = vi.fn((resolution: 'daily', startDate: string, endDate: string) => buildZoomWindowForRange(newDates, resolution, startDate, endDate));

                expect(preservedRange).toBeNull();
                expect(fallbackRange).toEqual({
                    startDate: newDates[0],
                    endDate: newDates.at(-1),
                });
                expect(buildZoomWindow('daily', fallbackRange.startDate, fallbackRange.endDate)).toEqual({
                    start: 0,
                    end: 100,
                });
                expect(buildZoomWindow).toHaveBeenCalledWith('daily', newDates[0], newDates.at(-1));
            });
        });

        describe('GrowthChart stateful reset and rebuild regressions', () => {
            type StoredGrowthOption = {
                dataZoom?: Array<{start?: number; end?: number}>;
                xAxis?: Array<{
                    axisLabel?: {
                        formatter?: (value: number | string) => string;
                        interval?: number | string;
                        showMinLabel?: boolean | null;
                        showMaxLabel?: boolean | null;
                    };
                }>;
            };

            const fullUpdateOptions = {
                ...CHART_SET_OPTION_OPTS,
                replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis'],
            };

            function storedGrowthZoom(chart: ReturnType<typeof echarts.init>): {start: number; end: number} {
                const zoom = (chart.getOption() as StoredGrowthOption).dataZoom?.at(0);
                if (typeof zoom?.start !== 'number' || typeof zoom.end !== 'number') {
                    throw new Error('Expected a numeric Growth dataZoom range');
                }
                return {start: zoom.start, end: zoom.end};
            }

            it('falls back to the new full domain after empty history invalidates stale ECharts zoom percentages', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const rangeReaderStart = source.indexOf('function getLogicalRangeFromChart()');
                // Why (re-pin, FE6a): buildZoomWindow, which followed the reader, moved to growthChartData.ts with the
                // derived data. The reader stayed, so the slice now ends at the declaration that follows it.
                const rangeReaderEnd = source.indexOf('\n    let lastLadderPlanKey: string | null = null;', rangeReaderStart);
                expect(rangeReaderStart).toBeGreaterThan(-1);
                expect(rangeReaderEnd).toBeGreaterThan(rangeReaderStart);
                if (rangeReaderStart < 0 || rangeReaderEnd <= rangeReaderStart) {
                    throw new Error('GrowthChart logical-range reader contract not found');
                }
                const rangeReader = source.slice(rangeReaderStart, rangeReaderEnd);
                // Why (re-pin, S7): the reader now binds `entry = activeChartData` and exempts a
                // ladder entry from the resolution check (a ladder entry carries its own buckets,
                // whatever the cascade's resolution says). The pins keep the invariant: a missing,
                // stale or empty active entry yields null, so the render falls back to the full
                // domain instead of reading stale ECharts zoom percentages against new history.
                expect(rangeReader).toContain('const entry = activeChartData;');
                expect(rangeReader).toContain('if (!entry || (!entry.ladder && entry.resolution !== currentResolution)) return null;');
                expect(rangeReader).toContain('if (entry.buckets.length === 0) return null;');
                expect(rangeReader).not.toContain('getResolutionData(');

                const initialDates = Array.from({length: 9}, (_, index) => `2026-01-${String(index + 1).padStart(2, '0')}`);
                const replacementDates = ['2026-03-10', '2026-03-12', '2026-03-14', '2026-03-16', '2026-03-18'] as const;
                let dates: readonly string[] = initialDates;
                let currentResolution: ChartResolution = 'daily';
                let activeChartData: {resolution: ChartResolution; ladder: boolean; buckets: ReturnType<typeof buildBucketInfos>} | null = {
                    resolution: currentResolution,
                    ladder: false,
                    buckets: buildBucketInfos(initialDates, currentResolution),
                };
                let visibleStartDate: string | null = initialDates[0];
                let visibleEndDate: string | null = initialDates.at(-1)!;
                let resolutionResetPending = false;
                const chart = echarts.init(null, undefined, {
                    renderer: 'svg',
                    ssr: true,
                    width: 640,
                    height: 240,
                });

                // Why (re-pin, S7): this copy follows the reader pinned above, ladder-aware guard and
                // empty-bucket guard included, so the test does not exercise a reader that no longer
                // exists. The entry here is a cascade one (`ladder: false`): the reader reads its window
                // in time, which on these evenly spaced dates reduces to the widening floor/ceil that
                // logicalRangeFromBuckets implements.
                const logicalRangeFromActiveChart = (): GrowthLogicalRange | null => {
                    const entry = activeChartData;
                    if (!entry || (!entry.ladder && entry.resolution !== currentResolution)) return null;
                    if (entry.buckets.length === 0) return null;
                    const zoom = storedGrowthZoom(chart);
                    return logicalRangeFromBuckets(entry.buckets, zoom.start, zoom.end);
                };
                const ensureLogicalRange = (): GrowthLogicalRange | null => {
                    if (dates.length === 0) return null;
                    visibleStartDate ??= dates[0];
                    visibleEndDate ??= dates.at(-1)!;
                    return {startDate: visibleStartDate, endDate: visibleEndDate};
                };
                const resetResolutionState = (preservedRange: GrowthLogicalRange | null) => {
                    activeChartData = null;
                    currentResolution = 'daily';
                    resolutionResetPending = true;
                    const nextRange = clampGrowthLogicalRange(preservedRange, dates);
                    visibleStartDate = nextRange?.startDate ?? null;
                    visibleEndDate = nextRange?.endDate ?? null;
                };
                const transitionHistory = (nextDates: readonly string[]): GrowthLogicalRange | null => {
                    dates = nextDates;
                    const preservedRange = logicalRangeFromActiveChart();
                    resetResolutionState(preservedRange);
                    return preservedRange;
                };

                try {
                    chart.setOption(
                        {
                            useUTC: true,
                            animation: false,
                            dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: 25, end: 75}],
                            xAxis: {type: 'time'},
                            yAxis: {type: 'value'},
                            series: [
                                {
                                    name: 'growth',
                                    type: 'line',
                                    data: initialDates.map((date, index) => [date, index]),
                                },
                            ],
                        },
                        fullUpdateOptions,
                    );

                    const staleZoom = storedGrowthZoom(chart);
                    const initialLiveRange = logicalRangeFromActiveChart();
                    expect(initialLiveRange).toEqual({
                        startDate: initialDates[2],
                        endDate: initialDates[6],
                    });

                    expect(transitionHistory([])).toEqual(initialLiveRange);
                    expect({visibleStartDate, visibleEndDate}).toEqual({
                        visibleStartDate: null,
                        visibleEndDate: null,
                    });
                    expect(activeChartData).toBeNull();
                    expect(resolutionResetPending).toBe(true);
                    expect(storedGrowthZoom(chart)).toEqual(staleZoom);

                    const restoredForReplacement = transitionHistory(replacementDates);
                    const explicitFullDomain = {
                        startDate: replacementDates[0],
                        endDate: replacementDates.at(-1)!,
                    };
                    const staleRangeOnReplacement = logicalRangeFromBuckets(buildBucketInfos(replacementDates, currentResolution), staleZoom.start, staleZoom.end);
                    expect(restoredForReplacement).toBeNull();
                    expect({visibleStartDate, visibleEndDate}).toEqual({
                        visibleStartDate: null,
                        visibleEndDate: null,
                    });
                    expect(storedGrowthZoom(chart)).toEqual(staleZoom);

                    const logicalRangeForReplacement = ensureLogicalRange();
                    expect(logicalRangeForReplacement).toEqual(explicitFullDomain);
                    expect(logicalRangeForReplacement).not.toEqual(staleRangeOnReplacement);
                    expect({visibleStartDate, visibleEndDate}).toEqual({
                        visibleStartDate: explicitFullDomain.startDate,
                        visibleEndDate: explicitFullDomain.endDate,
                    });
                    if (!logicalRangeForReplacement) throw new Error('Expected the replacement Growth history to initialize its full domain');

                    const rebuiltZoom = buildZoomWindowForRange(replacementDates, currentResolution, logicalRangeForReplacement.startDate, logicalRangeForReplacement.endDate);
                    expect(rebuiltZoom).toEqual({start: 0, end: 100});
                    expect(rebuiltZoom).not.toEqual(staleZoom);

                    chart.setOption(
                        {
                            useUTC: true,
                            animation: false,
                            dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, ...rebuiltZoom}],
                            xAxis: {type: 'time'},
                            yAxis: {type: 'value'},
                            series: [
                                {
                                    name: 'growth',
                                    type: 'line',
                                    data: replacementDates.map((date, index) => [date, index]),
                                },
                            ],
                        },
                        fullUpdateOptions,
                    );

                    expect(chart.renderToSVGString()).toMatch(/^<svg\b/);
                    expect(storedGrowthZoom(chart)).toEqual(rebuiltZoom);
                } finally {
                    chart.dispose();
                }
            });

            it('does not reuse history A bounds when history B arrives before the deferred Growth render', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const historyChangeStart = source.indexOf('if (history !== lastHistoryRef) {');
                const effectStart = source.lastIndexOf('$effect(() => {', historyChangeStart);
                const effectEnd = source.indexOf('\n    // =========================================================================\n    // Helpers', historyChangeStart);
                expect(historyChangeStart).toBeGreaterThan(-1);
                expect(effectStart).toBeGreaterThan(-1);
                expect(effectEnd).toBeGreaterThan(historyChangeStart);
                if (historyChangeStart < 0 || effectStart < 0 || effectEnd <= historyChangeStart) {
                    throw new Error('GrowthChart history-change effect contract not found');
                }

                const historyEffect = source.slice(effectStart, effectEnd);
                // Why (re-pin, S10): since round 2 (master plan §6.0.17) the reset tells new data
                // for the same period (live zoom kept) from a new period (zoom dropped), so the read
                // is gated: `periodChanged ? null : getLogicalRangeFromChart()`. The pin guards the
                // invariant, not the gate's spelling: the preserved range is the LIVE chart read or
                // null, never a remembered A bound. The gate only adds a null path, so the ungated
                // simulation below stays a sound model (history B already reads null there).
                const activeRangeRead = historyEffect.search(/const preservedRange = \w+ \? null : getLogicalRangeFromChart\(\);/);
                const directReset = historyEffect.indexOf('resetResolutionState(preservedRange);', activeRangeRead);
                const deferredRender = historyEffect.indexOf('tick().then(() => {', directReset);
                const render = historyEffect.indexOf('renderChart();', deferredRender);
                expect(activeRangeRead).toBeGreaterThan(-1);
                expect(directReset).toBeGreaterThan(activeRangeRead);
                expect(deferredRender).toBeGreaterThan(directReset);
                expect(render).toBeGreaterThan(deferredRender);
                expect(historyEffect).not.toContain('ensureLogicalRange');
                expect(historyEffect).not.toMatch(/getLogicalRangeFromChart\(\)\s*\?\?/);

                const historyADates = Array.from({length: 9}, (_, index) => `2026-01-${String(index + 1).padStart(2, '0')}`);
                const historyAReference = [...historyADates];
                const historyBDates = ['2026-04-10', '2026-04-12', '2026-04-14', '2026-04-16', '2026-04-18'] as const;
                let dates: readonly string[] = historyADates;
                let currentResolution: ChartResolution = 'daily';
                let activeChartData: {resolution: ChartResolution; buckets: ReturnType<typeof buildBucketInfos>} | null = {
                    resolution: currentResolution,
                    buckets: buildBucketInfos(historyADates, currentResolution),
                };
                let visibleStartDate: string | null = historyADates[0];
                let visibleEndDate: string | null = historyADates.at(-1)!;
                const deferredRenders: Array<() => void> = [];
                const renderedRanges: GrowthLogicalRange[] = [];
                const renderedZooms: Array<{start: number; end: number}> = [];
                const chart = echarts.init(null, undefined, {
                    renderer: 'svg',
                    ssr: true,
                    width: 640,
                    height: 240,
                });

                const logicalRangeFromActiveChart = (): GrowthLogicalRange | null => {
                    const entry = activeChartData;
                    if (!entry || entry.resolution !== currentResolution) return null;
                    const zoom = storedGrowthZoom(chart);
                    return logicalRangeFromBuckets(entry.buckets, zoom.start, zoom.end);
                };
                const ensureLogicalRange = vi.fn((): GrowthLogicalRange | null => {
                    if (dates.length === 0) return null;
                    visibleStartDate ??= dates[0];
                    visibleEndDate ??= dates.at(-1)!;
                    return {startDate: visibleStartDate, endDate: visibleEndDate};
                });
                const resetResolutionState = vi.fn((preservedRange: GrowthLogicalRange | null) => {
                    activeChartData = null;
                    currentResolution = 'daily';
                    const nextRange = clampGrowthLogicalRange(preservedRange, dates);
                    visibleStartDate = nextRange?.startDate ?? null;
                    visibleEndDate = nextRange?.endDate ?? null;
                });
                const buildZoomWindow = vi.fn((resolution: ChartResolution, startDate: string, endDate: string) => buildZoomWindowForRange(dates, resolution, startDate, endDate));
                const renderChart = vi.fn(() => {
                    const liveRange = logicalRangeFromActiveChart();
                    if (liveRange) {
                        visibleStartDate = liveRange.startDate;
                        visibleEndDate = liveRange.endDate;
                    }
                    const logicalRange = ensureLogicalRange();
                    if (!logicalRange) return;

                    const zoomWindow = buildZoomWindow(currentResolution, logicalRange.startDate, logicalRange.endDate);
                    activeChartData = {
                        resolution: currentResolution,
                        buckets: buildBucketInfos(dates, currentResolution),
                    };
                    renderedRanges.push(logicalRange);
                    renderedZooms.push(zoomWindow);
                    chart.setOption(
                        {
                            useUTC: true,
                            animation: false,
                            dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, ...zoomWindow}],
                            xAxis: {type: 'time'},
                            yAxis: {type: 'value'},
                            series: [
                                {
                                    name: 'growth',
                                    type: 'line',
                                    data: dates.map((date, index) => [date, index]),
                                },
                            ],
                        },
                        fullUpdateOptions,
                    );
                });
                const scheduleDeferredRender = vi.fn(() => {
                    deferredRenders.push(renderChart);
                });
                const transitionHistory = (nextDates: readonly string[]): GrowthLogicalRange | null => {
                    dates = nextDates;
                    const preservedRange = logicalRangeFromActiveChart();
                    resetResolutionState(preservedRange);
                    scheduleDeferredRender();
                    return preservedRange;
                };

                try {
                    chart.setOption(
                        {
                            useUTC: true,
                            animation: false,
                            dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: 25, end: 75}],
                            xAxis: {type: 'time'},
                            yAxis: {type: 'value'},
                            series: [
                                {
                                    name: 'growth',
                                    type: 'line',
                                    data: historyADates.map((date, index) => [date, index]),
                                },
                            ],
                        },
                        fullUpdateOptions,
                    );

                    const partialARange = logicalRangeFromActiveChart();
                    expect(partialARange).toEqual({
                        startDate: historyADates[2],
                        endDate: historyADates[6],
                    });
                    if (!partialARange) throw new Error('Expected history A to expose a partial active Growth range');

                    expect(transitionHistory(historyAReference)).toEqual(partialARange);
                    expect({visibleStartDate, visibleEndDate}).toEqual({
                        visibleStartDate: partialARange.startDate,
                        visibleEndDate: partialARange.endDate,
                    });
                    expect(activeChartData).toBeNull();
                    expect(ensureLogicalRange).not.toHaveBeenCalled();

                    expect(transitionHistory(historyBDates)).toBeNull();
                    expect(resetResolutionState).toHaveBeenNthCalledWith(1, partialARange);
                    expect(resetResolutionState).toHaveBeenNthCalledWith(2, null);
                    expect({visibleStartDate, visibleEndDate}).toEqual({
                        visibleStartDate: null,
                        visibleEndDate: null,
                    });
                    expect(activeChartData).toBeNull();
                    expect(ensureLogicalRange).not.toHaveBeenCalled();
                    expect(deferredRenders).toHaveLength(2);

                    const staleAClampedIntoB = clampGrowthLogicalRange(partialARange, historyBDates);
                    expect(staleAClampedIntoB).toEqual({
                        startDate: historyBDates[0],
                        endDate: historyBDates[0],
                    });
                    if (!staleAClampedIntoB) throw new Error('Expected retained history A bounds to clamp into history B');
                    const staleAFallbackZoom = buildZoomWindowForRange(historyBDates, currentResolution, staleAClampedIntoB.startDate, staleAClampedIntoB.endDate);
                    expect(staleAFallbackZoom).toEqual({start: 0, end: 0});

                    for (const runDeferredRender of deferredRenders) runDeferredRender();

                    const fullBDomain = {
                        startDate: historyBDates[0],
                        endDate: historyBDates.at(-1)!,
                    } satisfies GrowthLogicalRange;
                    const firstBRange = renderedRanges.at(0);
                    const firstBZoom = renderedZooms.at(0);
                    expect(firstBRange).toEqual(fullBDomain);
                    expect(firstBZoom).toEqual({start: 0, end: 100});
                    expect(firstBZoom).not.toEqual(staleAFallbackZoom);
                    expect(renderChart).toHaveBeenCalledTimes(2);
                    expect(ensureLogicalRange).toHaveBeenCalledTimes(2);
                    expect(buildZoomWindow).toHaveBeenNthCalledWith(1, 'daily', fullBDomain.startDate, fullBDomain.endDate);

                    const storedBZoom = storedGrowthZoom(chart);
                    const mappedBRange = logicalRangeFromBuckets(buildBucketInfos(historyBDates, 'daily'), storedBZoom.start, storedBZoom.end);
                    expect(chart.renderToSVGString()).toMatch(/^<svg\b/);
                    expect(storedBZoom).toEqual({start: 0, end: 100});
                    expect(mappedBRange).toEqual(fullBDomain);
                    if (!firstBRange || !mappedBRange) throw new Error('Expected history B to render and map its full Growth domain');

                    const historyADateSet = new Set(historyADates);
                    const bRangeAndMappingDates = [firstBRange.startDate, firstBRange.endDate, mappedBRange.startDate, mappedBRange.endDate];
                    const zoomBoundaryDates = buildZoomWindow.mock.calls.flatMap(([, startDate, endDate]) => [startDate, endDate]);
                    expect(bRangeAndMappingDates.some((date) => historyADateSet.has(date))).toBe(false);
                    expect(zoomBoundaryDates.some((date) => historyADateSet.has(date))).toBe(false);
                } finally {
                    chart.dispose();
                }
            });

            it('chooses the first post-reset resolution from the clamped restored range instead of the full history domain', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const resetStart = source.indexOf('function resetResolutionState(');
                const resetEnd = source.indexOf('\n    function ensureLogicalRange()', resetStart);
                const renderStart = source.indexOf('function renderChart(forceFullXAxisRebuild = false)');
                const renderEnd = source.indexOf('\n    function applyFullOption(', renderStart);
                expect(resetStart).toBeGreaterThan(-1);
                expect(resetEnd).toBeGreaterThan(resetStart);
                expect(renderStart).toBeGreaterThan(-1);
                expect(renderEnd).toBeGreaterThan(renderStart);
                if (resetStart < 0 || resetEnd <= resetStart || renderStart < 0 || renderEnd <= renderStart) {
                    throw new Error('GrowthChart resolution-reset contract not found');
                }

                const resetState = source.slice(resetStart, resetEnd);
                const renderChart = source.slice(renderStart, renderEnd);
                expect(resetState).toContain('resolutionResetPending = true;');
                expect(source).toMatch(/if \(history !== lastHistoryRef\) \{[\s\S]*?resetResolutionState\(preservedRange\);[\s\S]*?\}/);
                expect(renderChart).toMatch(
                    /if \(resolutionResetPending\) \{\s*const counts = computeBucketCounts\(logicalRange\.startDate, logicalRange\.endDate\);\s*currentResolution = chooseInitialResolution\(counts, chartInstance\.getWidth\(\), resolutionGrammar\);\s*resolutionResetPending = false;\s*\}/,
                );

                const historyDates = Array.from({length: 3_000}, (_, index) => new Date(Date.UTC(2020, 0, index + 1)).toISOString().slice(0, 10));
                const preservedRange = {
                    startDate: '2019-12-01',
                    endDate: historyDates[499],
                } satisfies GrowthLogicalRange;
                const plotWidth = 300;
                const state: {
                    currentResolution: ChartResolution;
                    resolutionResetPending: boolean;
                    visibleStartDate: string | null;
                    visibleEndDate: string | null;
                } = {
                    currentResolution: 'monthly',
                    resolutionResetPending: false,
                    visibleStartDate: null,
                    visibleEndDate: null,
                };

                const resetHistory = (range: GrowthLogicalRange | null) => {
                    const restored = clampGrowthLogicalRange(range, historyDates);
                    state.currentResolution = 'daily';
                    state.resolutionResetPending = true;
                    state.visibleStartDate = restored?.startDate ?? null;
                    state.visibleEndDate = restored?.endDate ?? null;
                    return restored;
                };

                const restoredRange = resetHistory(preservedRange);
                expect(restoredRange).toEqual({
                    startDate: historyDates[0],
                    endDate: historyDates[499],
                });
                expect(state.resolutionResetPending).toBe(true);
                if (!restoredRange) throw new Error('Expected the partial Growth range to clamp into the replacement history');

                const restoredCounts = computeBucketCounts(historyDates, restoredRange.startDate, restoredRange.endDate);
                const fullDomainCounts = computeBucketCounts(historyDates, historyDates[0], historyDates.at(-1)!);
                const restoredResolution = chooseInitialResolution(restoredCounts, plotWidth);
                const fullDomainResolution = chooseInitialResolution(fullDomainCounts, plotWidth);
                expect(restoredCounts.dailyCount).toBe(500);
                expect(fullDomainCounts.dailyCount).toBe(historyDates.length);
                expect(restoredResolution).not.toBe('daily');
                expect(fullDomainResolution).not.toBe(restoredResolution);

                if (state.resolutionResetPending) {
                    const counts = computeBucketCounts(historyDates, restoredRange.startDate, restoredRange.endDate);
                    state.currentResolution = chooseInitialResolution(counts, plotWidth);
                    state.resolutionResetPending = false;
                }

                expect(state.currentResolution).toBe(restoredResolution);
                expect(state.currentResolution).not.toBe(fullDomainResolution);
                expect(state.resolutionResetPending).toBe(false);
            });

            it('uses the latest live zoom for an immediate full rebuild and clears compact-only x-axis state', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const renderStart = source.indexOf('function renderChart(forceFullXAxisRebuild = false)');
                const renderEnd = source.indexOf('\n    function applyFullOption(', renderStart);
                expect(renderStart).toBeGreaterThan(-1);
                expect(renderEnd).toBeGreaterThan(renderStart);
                if (renderStart < 0 || renderEnd <= renderStart) {
                    throw new Error('GrowthChart synchronous live-range capture contract not found');
                }

                const renderChart = source.slice(renderStart, renderEnd);
                const capture = renderChart.indexOf('const liveRange = getLogicalRangeFromChart();');
                const storeStart = renderChart.indexOf('visibleStartDate = liveRange.startDate;', capture);
                const storeEnd = renderChart.indexOf('visibleEndDate = liveRange.endDate;', storeStart);
                const ensure = renderChart.indexOf('const logicalRange = ensureLogicalRange();', storeEnd);
                // Why (re-pin, S10): the candle-width ladder (Candles, Income) owns its bucket
                // width and keeps the whole history on the axis, so it no longer goes through
                // buildZoomWindow and the statement became a ladder/cascade ternary. The pin keeps
                // only the off-ladder operand this test simulates: the zoom handed to the full
                // rebuild is rebuilt from the live logical range, whatever the ladder side says.
                // Why (re-pin, S7): the ladder goes through buildZoomWindow again, on its own
                // entry: renderChart takes `activeData = getActiveAggregation()` (ladder or
                // cascade) and places the window on that entry's buckets, so the ternary above
                // is gone and the statement is one call. The invariant is unchanged: the zoom
                // handed to the immediate full rebuild is rebuilt from the live logical range,
                // captured and ensured just before it.
                const zoomWindow = renderChart.search(/const zoomWindow = buildZoomWindow\(activeData, logicalRange\.startDate, logicalRange\.endDate\);/);
                const fullRebuild = renderChart.indexOf('applyFullOption(isDark, buildFullSeries(isDark, seriesData), zoomWindow);', zoomWindow);
                expect(capture).toBeGreaterThan(-1);
                expect(storeStart).toBeGreaterThan(capture);
                expect(storeEnd).toBeGreaterThan(storeStart);
                expect(ensure).toBeGreaterThan(storeEnd);
                expect(zoomWindow).toBeGreaterThan(ensure);
                expect(fullRebuild).toBeGreaterThan(zoomWindow);

                const dates = Array.from({length: 41}, (_, index) => new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10));
                const compactPolicy = buildResponsiveXAxisPolicy({
                    width: 800,
                    values: dates,
                    locale: 'en-US',
                    axisType: 'time',
                });
                const desktopPolicy = buildResponsiveXAxisPolicy({
                    width: 1_200,
                    values: dates,
                    locale: 'en-US',
                    axisType: 'time',
                });
                const compactAxisLabel = responsiveAxisLabel(compactPolicy);
                const liveZoom = {start: 55, end: 85};
                const staleStoredRange: GrowthLogicalRange = {
                    startDate: dates[5],
                    endDate: dates[12],
                };
                let visibleStartDate = staleStoredRange.startDate;
                let visibleEndDate = staleStoredRange.endDate;
                const chart = echarts.init(null, undefined, {
                    renderer: 'svg',
                    ssr: true,
                    width: 1_200,
                    height: 240,
                });

                try {
                    expect(compactPolicy.compact).toBe(true);
                    // Why (re-pin, plan 47 C3): a desktop policy carries its own localized formatter.
                    expect(desktopPolicy).toEqual({
                        compact: false,
                        maxLabels: dates.length,
                        formatter: expect.any(Function),
                    });

                    chart.setOption(
                        {
                            useUTC: true,
                            animation: false,
                            dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, ...liveZoom}],
                            xAxis: {
                                type: 'time',
                                splitNumber: compactPolicy.splitNumber,
                                axisLabel: {
                                    color: '#475569',
                                    fontSize: 14,
                                    ...compactAxisLabel,
                                    interval: 3,
                                },
                                axisLine: {lineStyle: {color: '#f1f5f9'}},
                                splitLine: {show: false},
                            },
                            yAxis: {type: 'value'},
                            series: [
                                {
                                    name: 'growth',
                                    type: 'line',
                                    data: dates.map((date, index) => [date, index]),
                                },
                            ],
                        },
                        fullUpdateOptions,
                    );

                    const compactOption = chart.getOption() as StoredGrowthOption;
                    expect(compactOption.xAxis?.at(0)?.axisLabel).toMatchObject({
                        formatter: compactAxisLabel.formatter,
                        interval: 3,
                        showMinLabel: true,
                        showMaxLabel: true,
                    });

                    const currentZoom = storedGrowthZoom(chart);
                    const liveRange = logicalRangeFromBuckets(buildBucketInfos(dates, 'daily'), currentZoom.start, currentZoom.end);
                    expect(liveRange).not.toBeNull();
                    if (!liveRange) throw new Error('Expected the live Growth zoom to map to a logical range');
                    expect({startDate: visibleStartDate, endDate: visibleEndDate}).toEqual(staleStoredRange);
                    expect(liveRange).not.toEqual(staleStoredRange);

                    visibleStartDate = liveRange.startDate;
                    visibleEndDate = liveRange.endDate;
                    const logicalRange = {startDate: visibleStartDate, endDate: visibleEndDate};
                    expect(logicalRange).toEqual(liveRange);
                    const rebuiltZoom = buildZoomWindowForRange(dates, 'daily', logicalRange.startDate, logicalRange.endDate);
                    const staleStoredZoom = buildZoomWindowForRange(dates, 'daily', staleStoredRange.startDate, staleStoredRange.endDate);
                    expect(rebuiltZoom.start).toBeCloseTo(liveZoom.start);
                    expect(rebuiltZoom.end).toBeCloseTo(liveZoom.end);
                    expect(rebuiltZoom).not.toEqual(staleStoredZoom);

                    chart.setOption(
                        {
                            useUTC: true,
                            animation: false,
                            dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, ...rebuiltZoom}],
                            xAxis: {
                                type: 'time',
                                // GrowthChart's full time branch: the policy's formatter, then its compact-only keys (none on desktop).
                                axisLabel: {
                                    color: '#475569',
                                    fontSize: 14,
                                    rotate: 0,
                                    formatter: desktopPolicy.formatter,
                                    ...(desktopPolicy.axisLabel ?? {}),
                                },
                                axisLine: {lineStyle: {color: '#f1f5f9'}},
                                splitLine: {show: false},
                            },
                            yAxis: {type: 'value'},
                            series: [
                                {
                                    name: 'growth',
                                    type: 'line',
                                    data: dates.map((date, index) => [date, index]),
                                },
                            ],
                        },
                        fullUpdateOptions,
                    );

                    const rebuiltOption = chart.getOption() as StoredGrowthOption;
                    const rebuiltAxisLabel = rebuiltOption.xAxis?.at(0)?.axisLabel;
                    expect(chart.renderToSVGString()).toMatch(/^<svg\b/);
                    expect(storedGrowthZoom(chart)).toEqual(rebuiltZoom);
                    expect(storedGrowthZoom(chart)).not.toEqual(staleStoredZoom);
                    // Why (re-pin, plan 47 C3): the compact formatter is replaced by the desktop policy's own, not dropped.
                    expect(rebuiltAxisLabel?.formatter).toBe(desktopPolicy.formatter);
                    expect(rebuiltAxisLabel?.interval).toBeUndefined();
                    expect(rebuiltAxisLabel?.showMinLabel).toBe(false);
                    expect(rebuiltAxisLabel?.showMaxLabel).toBe(false);
                } finally {
                    chart.dispose();
                }
            });
        });

        it.each(RESPONSIVE_X_AXIS_CHARTS)('%s imports and applies the shared policy to initial and resized options', (name, path) => {
            const source = readFileSync(path, 'utf8');

            // Why (re-pin, plan 52 C1): the import now carries the inset helpers too (`timeAxisGridRight`, `axisLabelMeasure`), so the pin asks for the policy among the names, not alone.
            expect(source).toMatch(/import\s+\{[^}]*\bbuildResponsiveXAxisPolicy\b[^}]*\}\s+from\s+['"][^'"]*responsiveXAxis['"]/);
            expect(source).toMatch(/\bbuildResponsiveXAxisPolicy\s*\(/);
            // Why (re-pin, Y8 47-1): the three zoomable category charts merge `categoryAxisLabelPatch(policy)` on resize: it always sets
            // `interval` (the window's step, or 'auto'), so a step left by a previous window or width cannot survive the merge.
            if (ZOOM_RELABEL_CHARTS.has(name)) {
                expect(source).toMatch(/import\s+\{[^}]*\bcategoryAxisLabelPatch\b[^}]*\}\s+from\s+['"][^'"]*responsiveXAxis['"]/);
                expect(source).toMatch(/if \(policy\.axisLabel\) \{[^}]*?\.setOption\(\{xAxis:\s*\{\s*axisLabel:\s*categoryAxisLabelPatch\(policy\)\s*\}\s*\}/);
                expect(source, `${name}: no x-axis merge takes the bare policy.axisLabel`).not.toMatch(/axisLabel:\s*policy\.axisLabel\b/);
            } else {
                expect(source).toMatch(/if \(policy\.axisLabel\) \{[\s\S]*?setOption\(\{xAxis:\s*\{[\s\S]*?axisLabel:\s*policy\.axisLabel/);
            }
            // Why (re-pin, S7): GrowthChart's ladder (P&L Candles and Income) owns its category
            // x axis, so applyFullOption builds the shared policy for the time axis only
            // (`ladderActive ? null : buildResponsiveXAxisPolicy(…)`) and merges it through `?.`.
            // The optional merge is pinned together with that declaration, so its one reason is
            // pinned too: the policy is null only under the ladder, and the time axis still
            // applies it. The other seven charts keep the strict, non-optional merge.
            if (name === 'GrowthChart') {
                expect(source).toMatch(/const xAxisPolicy = ladderActive\s*\?\s*null\s*:\s*buildResponsiveXAxisPolicy\(\{/);
                expect(source).toContain('...(xAxisPolicy?.axisLabel ?? {})');
                // Why (re-pin, plan 47 C3): the policy's formatter labels the axis in both modes,
                // set right before the compact-only keys so a compact policy still overrides it.
                expect(source).toMatch(/formatter: xAxisPolicy\?\.formatter,\s*\.\.\.\(xAxisPolicy\?\.axisLabel \?\? \{\}\)/);
            } else {
                expect(source).toContain('...(xAxisPolicy.axisLabel ?? {})');
                expect(source).toMatch(/formatter: xAxisPolicy\.formatter,\s*\.\.\.\(xAxisPolicy\.axisLabel \?\? \{\}\)/);
            }
        });

        /** `code` without its comments: a comment that names a call is not the call. Cut at `//`, so it assumes no string holds one. Shared by 47-1 and Y-25. */
        function withoutComments(code: string): string {
            return code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
        }

        /**
         * The code of `function fn(…) {…}` in `source`, comments removed. The body is the first block after the name, braces
         * balanced by `blockAfter` (further down this describe), which holds while the signature carries no brace: none of the
         * functions read here takes or returns an object type. Throws, naming the chart, when the declaration is missing.
         * Shared by 47-1 and Y-25.
         */
        function functionCode(source: string, chart: string, fn: string): string {
            const body = blockAfter(source, `function ${fn}(`, '{');
            if (body === undefined) throw new Error(`${chart}: function ${fn}() not found`);
            return withoutComments(body);
        }

        describe('the zoomable category charts re-space their labels on the zoomed window (47-1)', () => {
            // 47-1: the compact label `interval` was computed on every point and no dataZoom path recomputed it, so a chart zoomed in
            // on a phone kept the step of its whole axis and showed only its two forced edge labels. These pins hold each link of the
            // fix, chart by chart, so none can be dropped in silence. LineChart.test.ts drives LineChart's path end to end; the policy
            // and the window reader are unit-tested in «responsive X-axis policy».

            /** The two charts that read the window off the dataZoom event itself, behind a debounce of their own. */
            const EVENT_RELABEL_CHARTS = [
                ['LineChart', new URL('./LineChart.svelte', import.meta.url)],
                ['CandlestickChart', new URL('./CandlestickChart.svelte', import.meta.url)],
            ] as const;

            /** A `getOption(` call: it deep-clones the whole option, so the zoom functions read the event or the logical range instead. */
            const GET_OPTION_CALL = /\bgetOption\s*\(/;

            /** `import {…, name, …} from '…responsiveXAxis'`, whatever the other names and their order. */
            function importsFromResponsiveXAxis(name: string): RegExp {
                return new RegExp(`import\\s+\\{[^}]*\\b${name}\\b[^}]*\\}\\s+from\\s+['"][^'"]*responsiveXAxis['"]`);
            }

            /** The chart's `on('dataZoom', (…) => {…})` handler: the name of its parameter ('' when it takes none) and its code. */
            function dataZoomHandler(source: string, chart: string): {param: string; code: string} {
                const head = source.match(/\.on\(\s*['"]dataZoom['"]\s*,\s*\(\s*(\w*)[^)]*\)\s*=>\s*\{/);
                const body = head ? blockAfter(source, head[0].slice(0, -1), '{') : undefined;
                if (!head || body === undefined) throw new Error(`${chart}: no on('dataZoom', (…) => {…}) handler found`);
                return {param: head[1], code: withoutComments(body)};
            }

            /** The first of `steps` not found in `code` after the one before it; null when they all come, in that order. */
            function firstStepOutOfOrder(code: string, steps: ReadonlyArray<readonly [string, RegExp]>): string | null {
                let from = 0;
                for (const [step, pattern] of steps) {
                    const match = pattern.exec(code.slice(from));
                    if (!match) return step;
                    from += match.index + match[0].length;
                }
                return null;
            }

            it.each(EVENT_RELABEL_CHARTS)('%s re-spaces its labels on the window a zoom leaves visible, once the gesture pauses', (name, path) => {
                const source = readFileSync(path, 'utf8');
                const handler = dataZoomHandler(source, name);
                const schedule = functionCode(source, name, 'scheduleZoomedAxisLabels');
                const count = functionCode(source, name, 'zoomedCategoryCount');
                const apply = functionCode(source, name, 'applyZoomedAxisLabels');
                const cleanup = functionCode(source, name, 'cleanup');
                const scheduleParam = source.match(/function scheduleZoomedAxisLabels\(\s*(\w+)/)?.[1];
                if (!scheduleParam) throw new Error(`${name}: scheduleZoomedAxisLabels() takes no event`);

                for (const helper of ['visiblePointCountFromZoom', 'ZOOM_LABEL_SETTLE_MS']) {
                    expect(source, `${name}: imports ${helper} from responsiveXAxis`).toMatch(importsFromResponsiveXAxis(helper));
                }
                // The handler passes its own event on: the window is read from it.
                expect(handler.param, `${name}: the dataZoom handler takes its event`).not.toBe('');
                expect(handler.code, `${name}: the dataZoom handler hands its event to scheduleZoomedAxisLabels`).toMatch(new RegExp(`\\bscheduleZoomedAxisLabels\\(\\s*${handler.param}\\s*\\)`));
                // The debounce keeps the event where the count reads it, and relabels once the gesture has paused.
                expect(schedule, `${name}: scheduleZoomedAxisLabels keeps the event`).toMatch(new RegExp(`\\blastZoomEvent\\s*=\\s*${scheduleParam}\\b`));
                expect(count, `${name}: zoomedCategoryCount reads the kept event`).toMatch(/\bvisiblePointCountFromZoom\(\s*lastZoomEvent\s*,/);
                expect(schedule, `${name}: every tick cancels the pending relabel before arming the next`).toMatch(/\bclear(?:Timer|Timeout)\(\s*zoomLabelTimer\s*\)[\s\S]*?\bzoomLabelTimer\s*=\s*setTimeout\(/);
                expect(schedule, `${name}: the relabel runs once no tick has come for ZOOM_LABEL_SETTLE_MS`).toMatch(/\bzoomLabelTimer\s*=\s*setTimeout\(\s*\(\)\s*=>\s*\{[^}]*\bapplyZoomedAxisLabels\(\);[^}]*\},\s*ZOOM_LABEL_SETTLE_MS\s*\)/);
                // The relabel sizes the policy on the visible count and merges it through the patch that resets the step.
                expect(apply, `${name}: applyZoomedAxisLabels counts the visible window`).toMatch(/\bvisibleCount\s*[=:]\s*zoomedCategoryCount\(\)/);
                expect(apply, `${name}: applyZoomedAxisLabels sizes the policy on it`).toMatch(/buildResponsiveXAxisPolicy\(\{[^}]*\bvisibleCount\b[^}]*\}\)/);
                expect(apply, `${name}: applyZoomedAxisLabels merges categoryAxisLabelPatch(policy)`).toMatch(/\.setOption\(\{xAxis:\s*\{\s*axisLabel:\s*categoryAxisLabelPatch\(policy\)\s*\}\s*\}/);
                // A resize keeps the window's spacing. Its policy is the one an `if (policy.axisLabel)` branch follows.
                expect(source, `${name}: the resize policy counts the visible window`).toMatch(/buildResponsiveXAxisPolicy\(\{[^}]*\bvisibleCount:\s*zoomedCategoryCount\(\)[^}]*\}\);[^}]*?if \(policy\.axisLabel\) \{/);
                expect(cleanup, `${name}: cleanup() cancels a pending relabel`).toMatch(/\bclear(?:Timer|Timeout)\(\s*zoomLabelTimer\s*\)/);
                // The window comes from the event, never from the chart. renderChart() is not checked: it reads the zoom it restores.
                for (const [fn, code] of [
                    ['zoomedCategoryCount', count],
                    ['scheduleZoomedAxisLabels', schedule],
                    ['applyZoomedAxisLabels', apply],
                ] as const) {
                    expect(code, `${name}: ${fn} reads no getOption()`).not.toMatch(GET_OPTION_CALL);
                }
            });

            it.each(EVENT_RELABEL_CHARTS)('%s sizes the labels of a full re-render on the zoom it is about to restore', (name, path) => {
                // A full re-render (a refresh, a theme or an overlay change) replaces the option, then restores the zoom. Sized on
                // every point, its labels showed the whole axis's step until the restored zoom's event re-spaced them 120 ms later.
                const source = readFileSync(path, 'utf8');
                const render = functionCode(source, name, 'renderChart');
                const countedWhen = render.match(/const restoredZoomCount = ([^;?]+?)\s*\?\s*visiblePointCountFromZoom\(\s*savedZoom\s*,\s*dates\.length\s*\)\s*:\s*null;/)?.[1];
                const restoredWhen = render.match(/if \(([^)]+)\) \{\s*chartInstance\.dispatchAction\(\{\s*type:\s*'dataZoom',\s*start:\s*savedZoom\.start,\s*end:\s*savedZoom\.end\b/)?.[1];
                if (countedWhen === undefined) throw new Error(`${name}: renderChart() counts no saved zoom (const restoredZoomCount = … ? visiblePointCountFromZoom(savedZoom, dates.length) : null;)`);
                if (restoredWhen === undefined) throw new Error(`${name}: renderChart() restores no saved zoom (if (…) { chartInstance.dispatchAction({type: 'dataZoom', start: savedZoom.start, end: savedZoom.end…`);

                expect(
                    firstStepOutOfOrder(render, [
                        ['reads the zoom on screen into savedZoom', /\blet savedZoom\b[\s\S]*?\bsavedZoom = \{/],
                        ['counts the window it will restore', /\bconst restoredZoomCount = /],
                        ['sizes the labels on that count', /\bconst xAxisPolicy = buildResponsiveXAxisPolicy\(\{(?=[^}]*\bvalues:\s*dates\b)(?=[^}]*\bvisibleCount:\s*restoredZoomCount\b)/],
                        ['replaces the option', /\bchartInstance\.setOption\(\s*option\s*,\s*true\s*\);/],
                        ['then restores the zoom', /\bchartInstance\.dispatchAction\(\{\s*type:\s*'dataZoom'/],
                    ]),
                    `${name}: renderChart() — the first step missing, or out of order`,
                ).toBeNull();
                // The window counted is the window restored (LineChart restores none while compact).
                expect(countedWhen.replace(/\s+/g, ' ').trim(), `${name}: restoredZoomCount is counted under the condition the zoom is restored under`).toBe(restoredWhen.replace(/\s+/g, ' ').trim());
            });

            it('PriceChartFull re-spaces its labels on the settled window through its resolution debounce, and renders them on the zoom it draws', () => {
                // No debounce of its own: the dataZoom handler already arms the 200 ms resolution recompute, which reads the settled
                // logical range once. A new resolution redraws, sized on the zoom it draws; a kept one redraws nothing, so the labels
                // are re-spaced right there.
                const name = 'PriceChartFull';
                const source = readFileSync(new URL('./PriceChartFull.svelte', import.meta.url), 'utf8');
                const handler = dataZoomHandler(source, name);
                const recompute = functionCode(source, name, 'scheduleResolutionRecompute');
                const count = functionCode(source, name, 'visibleCategoryCount');
                const apply = functionCode(source, name, 'applyZoomedAxisLabels');
                const render = functionCode(source, name, 'renderChart');
                const keptResolution = blockAfter(recompute, 'if (nextResolution !== resolution)', '} else {');
                if (keptResolution === undefined) throw new Error(`${name}: scheduleResolutionRecompute() has no branch for a kept resolution (if (nextResolution !== resolution) {…} else {…})`);

                expect(source, `${name}: imports visiblePointCountFromZoom from responsiveXAxis`).toMatch(importsFromResponsiveXAxis('visiblePointCountFromZoom'));
                expect(handler.code, `${name}: the dataZoom handler arms the resolution debounce`).toMatch(/\bscheduleResolutionRecompute\(\)/);
                expect(keptResolution, `${name}: a kept resolution re-spaces the labels on the settled window`).toMatch(/\bapplyZoomedAxisLabels\(\)/);
                expect(count, `${name}: visibleCategoryCount takes the window off the logical range`).toMatch(/\bcomputeZoomWindow\([^;]*\blogicalRange\s*\)/);
                expect(count, `${name}: visibleCategoryCount counts that window`).toMatch(/\bvisiblePointCountFromZoom\(/);
                expect(apply, `${name}: applyZoomedAxisLabels sizes the policy on the visible count`).toMatch(/buildResponsiveXAxisPolicy\(\{[^}]*\bvisibleCount:\s*visibleCategoryCount\(\)[^}]*\}\)/);
                expect(apply, `${name}: applyZoomedAxisLabels merges categoryAxisLabelPatch(policy)`).toMatch(/\.setOption\(\{xAxis:\s*\{\s*axisLabel:\s*categoryAxisLabelPatch\(policy\)\s*\}\s*\}/);
                expect(render, `${name}: the render sizes the labels on the zoom window it draws`).toMatch(/\bconst xAxisPolicy = buildResponsiveXAxisPolicy\(\{[^}]*\bvisibleCount:\s*visiblePointCountFromZoom\(\s*zoomWindow\s*,\s*dates\.length\s*\)/);
                expect(render, `${name}: the render draws that zoom window`).toMatch(/\bdataZoom:\s*\[\{[^}]*\bstart:\s*zoomWindow\.start,\s*end:\s*zoomWindow\.end\b/);
                expect(source, `${name}: the resize policy counts the visible window`).toMatch(/buildResponsiveXAxisPolicy\(\{[^}]*\bvisibleCount:\s*visibleCategoryCount\(\)[^}]*\}\);[^}]*?if \(policy\.axisLabel\) \{/);
                // The window comes from the logical range, never from the chart. renderChart() and the debounce body are not checked:
                // the debounce reads the settled range once through getOption(), by design.
                for (const [fn, code] of [
                    ['visibleCategoryCount', count],
                    ['applyZoomedAxisLabels', apply],
                ] as const) {
                    expect(code, `${name}: ${fn} reads no getOption()`).not.toMatch(GET_OPTION_CALL);
                }
            });
        });

        describe('the arrows are re-aimed once a resize settles, and only on a chart that has some (Y-25)', () => {
            // Y-25: what is left of updateArrowRotations()'s cost after Y-8 — each call reads getOption(), a deep copy of the whole
            // option, and writes every series back. (b) The ResizeObserver paths re-aimed the arrows on every callback: LineChart's
            // and CandlestickChart's re-arm their settle instead (scheduleZoomedAxisLabels(lastZoomEvent), whose timer re-aims, Y-8),
            // PriceChartFull's leaves them to the resolution debounce it already arms (its kept-resolution branch re-aims, Y-8).
            // (d) Each full render notes whether its option has an arrow, so a chart without one is not read for them:
            // noteArrowMarkers(chartInstance, option) right after chartInstance.setOption(option, true). These pins hold the wiring,
            // chart by chart; LineChart.test.ts and PriceChartFull.test.ts drive the behaviour, lineChartHelpers.test.ts the helper.

            /** The three charts that draw arrow markers and re-aim them. */
            const ARROW_CHARTS = [
                ['LineChart', new URL('./LineChart.svelte', import.meta.url)],
                ['CandlestickChart', new URL('./CandlestickChart.svelte', import.meta.url)],
                ['PriceChartFull', new URL('./PriceChartFull.svelte', import.meta.url)],
            ] as const;

            /** An `updateArrowRotations(` call: a getOption() copy, and every series written back. */
            const ARROW_REAIM = /\bupdateArrowRotations\s*\(/;

            /** The settle re-armed on the window last zoomed to. */
            const REARMED_SETTLE = /\bscheduleZoomedAxisLabels\(\s*lastZoomEvent\s*\)/;

            /** The settle's timer re-aims the arrows, once no tick has come for its delay (Y-8). */
            const SETTLE_REAIMS = /\bzoomLabelTimer\s*=\s*setTimeout\(\s*\(\)\s*=>\s*\{[^}]*\bupdateArrowRotations\(\s*chartInstance\s*\)/;

            /** The full render: the one `setOption` that replaces the option, series and all. */
            const FULL_RENDER = /^\.setOption\(\s*option\s*,\s*true\s*\)$/;

            /** The ResizeObserver callback a chart creates in `renderChart()`, comments removed. */
            function resizeCallback(source: string, chart: string): string {
                const callback = blockAfter(source, 'resizeObserver = new ResizeObserver(', '=> {');
                if (callback === undefined) throw new Error(`${chart}: the ResizeObserver callback not found (resizeObserver = new ResizeObserver(() => {…}))`);
                return withoutComments(callback);
            }

            /** The call that starts at `at` — `.setOption(` — up to its balanced closing parenthesis. */
            function callText(code: string, at: number): string {
                const open = code.indexOf('(', at);
                for (let index = open, depth = 0; index >= 0 && index < code.length; index++) {
                    if (code[index] === '(') depth++;
                    else if (code[index] === ')' && --depth === 0) return code.slice(at, index + 1);
                }
                return code.slice(at);
            }

            it('LineChart: resizeChartOnly() — the ResizeObserver’s work — re-arms the settle instead of re-aiming the arrows at once', () => {
                const name = 'LineChart';
                const source = readFileSync(new URL('./LineChart.svelte', import.meta.url), 'utf8');
                const callback = resizeCallback(source, name);
                const resize = functionCode(source, name, 'resizeChartOnly');
                const compact = functionCode(source, name, 'handleCompactResize');
                const schedule = functionCode(source, name, 'scheduleZoomedAxisLabels');

                // Positive controls: the scans read the code they are about, and the settle they point to re-aims.
                expect(callback, `${name}: the ResizeObserver callback hands a full-size chart’s resize to resizeChartOnly()`).toMatch(/\bresizeChartOnly\(\)/);
                expect(compact, `${name}: a compact chart that keeps its resolution goes through resizeChartOnly() too`).toMatch(/\bresizeChartOnly\(\)/);
                expect(resize, `${name}: resizeChartOnly() resizes the chart`).toMatch(/\bchartInstance\??\.resize\(\)/);
                expect(schedule, `${name}: the settle’s timer re-aims the arrows (Y-8)`).toMatch(SETTLE_REAIMS);

                expect(
                    {callbackReaims: ARROW_REAIM.test(callback), compactReaims: ARROW_REAIM.test(compact), resizeReaims: ARROW_REAIM.test(resize), resizeRearmsSettle: REARMED_SETTLE.test(resize)},
                    `Y-25: ${name}’s resizeChartOnly() re-aims the arrows at once — a getOption() copy, and every series written back, on each ResizeObserver callback — instead of re-arming the settle with scheduleZoomedAxisLabels(lastZoomEvent)`,
                ).toEqual({callbackReaims: false, compactReaims: false, resizeReaims: false, resizeRearmsSettle: true});
            });

            it('CandlestickChart: the ResizeObserver callback re-arms the settle instead of re-aiming the arrows at once', () => {
                const name = 'CandlestickChart';
                const source = readFileSync(new URL('./CandlestickChart.svelte', import.meta.url), 'utf8');
                const callback = resizeCallback(source, name);
                const schedule = functionCode(source, name, 'scheduleZoomedAxisLabels');

                expect(callback, `${name}: the ResizeObserver callback resizes the chart`).toMatch(/\bchartInstance\??\.resize\(\)/);
                expect(schedule, `${name}: the settle’s timer re-aims the arrows (Y-8)`).toMatch(SETTLE_REAIMS);

                expect(
                    {reaims: ARROW_REAIM.test(callback), rearmsSettle: REARMED_SETTLE.test(callback)},
                    `Y-25: ${name}’s ResizeObserver callback re-aims the arrows at once — a getOption() copy, and every series written back, on each callback — instead of re-arming the settle with scheduleZoomedAxisLabels(lastZoomEvent)`,
                ).toEqual({reaims: false, rearmsSettle: true});
            });

            it('PriceChartFull: the ResizeObserver callback leaves the arrows to the resolution debounce it arms, whose kept-resolution branch re-aims them', () => {
                const name = 'PriceChartFull';
                const source = readFileSync(new URL('./PriceChartFull.svelte', import.meta.url), 'utf8');
                const callback = resizeCallback(source, name);
                const recompute = functionCode(source, name, 'scheduleResolutionRecompute');
                const keptResolution = blockAfter(recompute, 'if (nextResolution !== resolution)', '} else {');
                if (keptResolution === undefined) throw new Error(`${name}: scheduleResolutionRecompute() has no branch for a kept resolution (if (nextResolution !== resolution) {…} else {…})`);

                expect(callback, `${name}: the ResizeObserver callback resizes the chart`).toMatch(/\bchartInstance\??\.resize\(\)/);
                expect(callback, `${name}: the ResizeObserver callback arms the resolution debounce`).toMatch(/\bscheduleResolutionRecompute\(\)/);
                expect(keptResolution, `${name}: the debounce’s kept-resolution branch re-aims the arrows (Y-8)`).toMatch(/\bupdateArrowRotations\(\s*chartInstance\s*\)/);

                expect(ARROW_REAIM.test(callback), `Y-25: ${name}’s ResizeObserver callback re-aims the arrows at once — a getOption() copy, and every series written back, on each callback — though the resolution debounce it arms re-aims them once the resize settles`).toBe(false);
            });

            it.each(ARROW_CHARTS)('%s notes, right after its full render, whether its option has an arrow (noteArrowMarkers)', (name, path) => {
                const source = readFileSync(path, 'utf8');
                const render = functionCode(source, name, 'renderChart');
                const fullRenders = sitesOf(render, /\bchartInstance\.setOption\(\s*option\s*,\s*true\s*\)/g);
                // Positive control: «right after the full render» is also true of no full render at all.
                expect(fullRenders.length, `${name}: the full render — chartInstance.setOption(option, true) — in renderChart()`).toBe(1);

                expect(
                    {imported: /import\s+\{[^}]*\bnoteArrowMarkers\b[^}]*\}\s+from\s+['"]\.\/lineChartHelpers['"]/.test(source), rightAfterTheFullRender: lineAfterCall(render, fullRenders[0])},
                    `Y-25: ${name} does not import noteArrowMarkers from ./lineChartHelpers and call noteArrowMarkers(chartInstance, option); right after chartInstance.setOption(option, true); — no statement between`,
                ).toEqual({imported: true, rightAfterTheFullRender: expect.stringMatching(/^noteArrowMarkers\(\s*chartInstance\s*,\s*option\s*\);/)});
            });

            it.each(ARROW_CHARTS)('%s sets its series only in its full render, so the arrows noted there stay the chart’s until the next one (guard)', (name, path) => {
                // The premise of noteArrowMarkers: it is taken at the full render, so a setOption that brought series anywhere else
                // could give the chart an arrow the note does not know of — skipped, and never aimed.
                const code = withoutComments(readFileSync(path, 'utf8'));
                const calls = sitesOf(code, /\.setOption\(/g).map((at) => callText(code, at));
                // Positive control: the scan sees the calls it is about.
                expect(
                    calls.filter((call) => FULL_RENDER.test(call)),
                    `${name}: the full render among its setOption calls`,
                ).toHaveLength(1);

                expect(
                    calls.filter((call) => !FULL_RENDER.test(call) && /\bseries\b/.test(call)),
                    `${name}: a setOption besides the full render carries series — the arrows noted at the full render may no longer be the chart’s: note them there too`,
                ).toEqual([]);
            });
        });

        it('routes every GrowthChart compact-to-desktop data update through a full x-axis replacement with the current zoom window', () => {
            const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
            const updateStart = source.indexOf('function updateChartData(');
            const updateEnd = source.indexOf('\n    function syncResolutionToViewport()', updateStart);
            const fullOptionStart = source.indexOf('function applyFullOption(', updateEnd);
            const fullOptionEnd = source.indexOf('\n</script>', fullOptionStart);
            const dataUpdateCalls = source.match(/^\s+updateChartData\([^;]+;/gm)?.map((call) => call.trim()) ?? [];

            expect(updateStart).toBeGreaterThan(-1);
            expect(updateEnd).toBeGreaterThan(updateStart);
            expect(fullOptionStart).toBeGreaterThan(updateEnd);
            expect(fullOptionEnd).toBeGreaterThan(fullOptionStart);
            expect(dataUpdateCalls).toEqual(['updateChartData(entry, isDark, zoomWindow, true, logicalRange.startDate);', 'updateChartData(activeData, isDark, zoomWindow, false, logicalRange.startDate);']);
            if (updateStart < 0 || updateEnd <= updateStart || fullOptionStart <= updateEnd || fullOptionEnd <= fullOptionStart) {
                throw new Error('GrowthChart data-update compact-to-desktop contract not found');
            }

            const updateChartData = source.slice(updateStart, updateEnd);
            const fullOption = source.slice(fullOptionStart, fullOptionEnd);
            // Why (re-pin, S7): the ladder (Candles, Income) owns its x axis, so updateChartData
            // forks on `entry.ladder` and builds the shared responsive policy on the time branch
            // only (`axisType: 'time'`); `isCandlesSubmode` and its category policy are gone. The
            // policy is still computed from the entry's dates at the container width.
            // Why (re-pin, M-18): every figure, dates included, is written in the interface locale, so the policy takes `uiLocale()` instead of svelte-i18n's `$locale ?? undefined`.
            expect(updateChartData).toMatch(/if \(entry\.ladder\) \{[\s\S]*?\} else \{\s*const xAxisPolicy = buildResponsiveXAxisPolicy\(\{\s*width: chartContainer\?\.clientWidth \?\? 0,\s*values: entry\.dates,\s*locale: uiLocale\(\),\s*axisType: 'time',\s*\}\);/);
            // Why (re-pin, S7): the time branch now tests `responsiveXAxisCompact` directly
            // instead of a `wasCompact` copy. The check still runs before the flag is
            // overwritten, so a compact-to-desktop update still goes through applyFullOption
            // with the current zoom window and returns before the partial setOption.
            expect(updateChartData).toMatch(/if \(responsiveXAxisCompact && !xAxisPolicy\.compact\) \{\s*applyFullOption\(isDark, buildFullSeries\(isDark, seriesData\), zoomWindow\);\s*return;\s*\}\s*responsiveXAxisCompact = xAxisPolicy\.compact;/);
            expect(updateChartData).toContain("dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],");
            // The ladder's category axis (Candles, Income) needs `data` refreshed on every
            // partial update (a rung change replaces the bucket dates) — the time-axis branch
            // only needs a label refresh, with splitNumber and the compact-only label keys
            // gated behind `compact`.
            // Why (re-pin, S7): the inline submode ternary is gone. Each branch assigns `xAxis`
            // (the ladder: its dates with the axis planned for this window), and that one value
            // rides the series update. The pins keep the claim above on both branches and
            // prove the computed axis is the one sent.
            // Why (re-pin, plan 47 C3): the desktop side of the time branch no longer sends an
            // empty axis. Its formatter is built from the entry's dates, so a data update sends
            // the fresh one; splitNumber and the compact-only label keys stay compact-only.
            expect(updateChartData).toContain('xAxis = {data: entry.dates, ...ladderAxisOption(plan)};');
            expect(updateChartData).toContain('xAxis = xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber, axisLabel: xAxisPolicy.axisLabel} : {axisLabel: {formatter: xAxisPolicy.formatter}};');
            expect(updateChartData).toMatch(/\bxAxis,\s*series,\s*\},\s*CHART_SERIES_UPDATE_OPTS,\s*\);/);
            expect(updateChartData).toMatch(/chartInstance\.setOption\([\s\S]*?CHART_SERIES_UPDATE_OPTS,\s*\);/);
            expect(source).toContain("const CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']};");
            expect(source).toContain("const CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis']};");
            expect(source).not.toContain('const entry = activeChartData?.resolution === currentResolution ? activeChartData : getResolutionData(currentResolution);');
            // Why (re-pin, S7): the logical-range reader's guard now names `entry`
            // (= activeChartData) and exempts a ladder entry, which carries its own buckets. A
            // stale cascade entry still yields null rather than a silently rebuilt one (the
            // negative above).
            expect(source).toContain('if (!entry || (!entry.ladder && entry.resolution !== currentResolution)) return null;');
            expect(fullOption).toContain("dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],");
            // G1b-candles-fix: xAxis is now a submode-conditional ternary (category for
            // candles — a `time` xAxis silently fails to paint any candlestick body/wick,
            // a known upstream ECharts limitation — time for everything else), not a
            // single unconditional object.
            // Why (re-pin, S7): the ternary now keys on the ladder plan (`ladderAxis`), not on
            // the candles submode: the ladder (Candles and Income) draws on the category axis,
            // every other view on time. The pins below still prove the category branch carries
            // its own type and dates.
            expect(fullOption).toMatch(/xAxis: ladderAxis\s*\?\s*\{/);
            expect(fullOption).toContain("type: 'category',");
            expect(fullOption).toContain('data: activeChartData?.dates ?? dates,');
            expect(fullOption).toContain('chartInstance.setOption(option, CHART_FULL_UPDATE_OPTS);');
        });

        it('clamps and preserves Growth zoom while clearing compact x-axis state on a data-driven compact-to-desktop full rebuild', () => {
            const width = 800;
            const originalDates = Array.from({length: 41}, (_, index) => new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10));
            const replacementDates = [originalDates[14], originalDates[19], originalDates[24], originalDates[29], originalDates[34]];
            const compactPolicy = buildResponsiveXAxisPolicy({
                width,
                values: originalDates,
                locale: 'en-US',
                axisType: 'time',
            });
            const desktopPolicy = buildResponsiveXAxisPolicy({
                width,
                values: replacementDates,
                locale: 'en-US',
                axisType: 'time',
            });
            const compactAxisLabel = responsiveAxisLabel(compactPolicy);
            const compactOnlyInterval = 3;
            const fullUpdateOptions = {
                ...CHART_SET_OPTION_OPTS,
                replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis'],
            };
            const chart = echarts.init(null, undefined, {
                renderer: 'svg',
                ssr: true,
                width,
                height: 240,
            });

            type StoredGrowthOption = {
                dataZoom?: Array<{start?: number; end?: number}>;
                xAxis?: Array<{
                    axisLabel?: {
                        formatter?: (value: number | string) => string;
                        interval?: number | string;
                        showMinLabel?: boolean | null;
                        showMaxLabel?: boolean | null;
                    };
                }>;
            };

            try {
                expect(compactPolicy.compact).toBe(true);
                // Why (re-pin, plan 47 C3): a desktop policy carries its own localized formatter.
                expect(desktopPolicy).toEqual({
                    compact: false,
                    maxLabels: replacementDates.length,
                    formatter: expect.any(Function),
                });

                chart.setOption(
                    {
                        useUTC: true,
                        animation: false,
                        dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: 25, end: 75}],
                        xAxis: {
                            type: 'time',
                            splitNumber: compactPolicy.splitNumber,
                            axisLabel: {
                                color: '#475569',
                                fontSize: 14,
                                ...compactAxisLabel,
                                interval: compactOnlyInterval,
                            },
                            axisLine: {lineStyle: {color: '#f1f5f9'}},
                            splitLine: {show: false},
                        },
                        yAxis: {type: 'value'},
                        series: [
                            {
                                name: 'growth',
                                type: 'line',
                                data: originalDates.map((date, index) => [date, index]),
                            },
                        ],
                    },
                    fullUpdateOptions,
                );

                const zoomedOption = chart.getOption() as StoredGrowthOption;
                expect(zoomedOption.dataZoom).toHaveLength(1);
                expect(zoomedOption.xAxis).toHaveLength(1);
                const currentZoom = zoomedOption.dataZoom?.at(0);
                const compactXAxisLabel = zoomedOption.xAxis?.at(0)?.axisLabel;
                expect(currentZoom).toMatchObject({start: 25, end: 75});
                expect(compactXAxisLabel?.formatter).toBe(compactAxisLabel.formatter);
                expect(compactXAxisLabel?.interval).toBe(compactOnlyInterval);
                expect(compactXAxisLabel).toMatchObject({
                    showMinLabel: true,
                    showMaxLabel: true,
                });
                if (typeof currentZoom?.start !== 'number' || typeof currentZoom.end !== 'number') {
                    throw new Error('Expected a current Growth dataZoom range');
                }

                const currentLogicalRange = logicalRangeFromBuckets(buildBucketInfos(originalDates, 'daily'), currentZoom.start, currentZoom.end);
                expect(currentLogicalRange).not.toBeNull();
                if (!currentLogicalRange) throw new Error('Expected the old active Growth data to produce a logical range');

                const preservedLogicalRange = clampGrowthLogicalRange(currentLogicalRange, replacementDates);
                expect(preservedLogicalRange).toEqual({
                    startDate: replacementDates[0],
                    endDate: currentLogicalRange.endDate,
                });
                if (!preservedLogicalRange) throw new Error('Expected the Growth logical range to survive the history change');

                const buildZoomWindow = vi.fn((resolution: 'daily', startDate: string, endDate: string) => buildZoomWindowForRange(replacementDates, resolution, startDate, endDate));
                const rebuiltZoom = buildZoomWindow('daily', preservedLogicalRange.startDate, preservedLogicalRange.endDate);
                expect(buildZoomWindow).toHaveBeenCalledWith('daily', replacementDates[0], currentLogicalRange.endDate);
                expect(rebuiltZoom).toEqual({
                    start: 0,
                    end: 75,
                });

                chart.setOption(
                    {
                        useUTC: true,
                        animation: false,
                        dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, ...rebuiltZoom}],
                        xAxis: {
                            type: 'time',
                            // GrowthChart's full time branch: the policy's formatter, then its compact-only keys (none on desktop).
                            axisLabel: {
                                color: '#475569',
                                fontSize: 14,
                                rotate: 0,
                                formatter: desktopPolicy.formatter,
                                ...(desktopPolicy.axisLabel ?? {}),
                            },
                            axisLine: {lineStyle: {color: '#f1f5f9'}},
                            splitLine: {show: false},
                        },
                        yAxis: {type: 'value'},
                        series: [
                            {
                                name: 'growth',
                                type: 'line',
                                data: replacementDates.map((date, index) => [date, index]),
                            },
                        ],
                    },
                    fullUpdateOptions,
                );

                const rebuiltOption = chart.getOption() as StoredGrowthOption;
                expect(rebuiltOption.dataZoom).toHaveLength(1);
                expect(rebuiltOption.xAxis).toHaveLength(1);
                const storedRebuiltZoom = rebuiltOption.dataZoom?.at(0);
                const rebuiltXAxisLabel = rebuiltOption.xAxis?.at(0)?.axisLabel;

                expect(chart.renderToSVGString()).toMatch(/^<svg\b/);
                // Why (re-pin, plan 47 C3): the compact formatter is replaced by the desktop policy's own, not dropped.
                expect(rebuiltXAxisLabel?.formatter).toBe(desktopPolicy.formatter);
                expect(rebuiltXAxisLabel?.interval).toBeUndefined();
                expect(rebuiltXAxisLabel?.showMinLabel).toBe(false);
                expect(rebuiltXAxisLabel?.showMaxLabel).toBe(false);
                expect(storedRebuiltZoom).toMatchObject(rebuiltZoom);
                expect(storedRebuiltZoom).not.toMatchObject({start: 0, end: 100});
            } finally {
                chart.dispose();
            }
        });

        it('forces GrowthChart compact-to-desktop resize through the full x-axis path with the current zoom window', () => {
            const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
            const resizeStart = source.indexOf('const resizeWatcher = createResizeWatcher(() => {');
            const resizeEnd = source.indexOf('\n    let darkModeObserver', resizeStart);
            const renderStart = source.indexOf('function renderChart(forceFullXAxisRebuild = false)');
            const renderEnd = source.indexOf('\n    function applyFullOption(', renderStart);
            const fullOptionStart = source.indexOf('function applyFullOption(', renderEnd);
            const fullOptionEnd = source.indexOf('\n</script>', fullOptionStart);

            expect(resizeStart).toBeGreaterThan(-1);
            expect(resizeEnd).toBeGreaterThan(resizeStart);
            expect(renderStart).toBeGreaterThan(-1);
            expect(renderEnd).toBeGreaterThan(renderStart);
            expect(fullOptionStart).toBeGreaterThan(renderEnd);
            expect(fullOptionEnd).toBeGreaterThan(fullOptionStart);
            if (resizeStart < 0 || resizeEnd <= resizeStart || renderStart < 0 || renderEnd <= renderStart || fullOptionStart <= renderEnd || fullOptionEnd <= fullOptionStart) {
                throw new Error('GrowthChart compact-to-desktop full-render contract not found');
            }

            const resizeCallback = source.slice(resizeStart, resizeEnd);
            const renderChart = source.slice(renderStart, renderEnd);
            const fullOption = source.slice(fullOptionStart, fullOptionEnd);

            expect(resizeCallback).toMatch(/const wasCompact = responsiveXAxisCompact;\s*responsiveXAxisCompact = policy\.compact;[\s\S]*?if \(policy\.axisLabel\) \{[\s\S]*?\} else if \(wasCompact\) \{\s*renderChart\(true\);\s*\}/);
            // Why (re-pin, S10): two product changes, neither to the resize path itself. The
            // candle-width ladder keeps the whole history, so `const zoomWindow` became a
            // ladder/cascade ternary, and the privacy mask joined the full-rebuild triggers
            // (ECharts caches axis labels). The pins keep what this test is about: off the
            // ladder the zoom is rebuilt from the live logical range, and `renderChart(true)`
            // always takes the full path because forceFullXAxisRebuild is a disjunct of
            // needsFullInit. The triggers are checked as a set, so a new one is not a failure.
            // Why (re-pin, S7): the ladder goes through buildZoomWindow again, on its own entry
            // (`activeData = getActiveAggregation()`), so the ternary above is gone. The zoom the
            // forced full path receives is still rebuilt from the live logical range.
            expect(renderChart).toMatch(/const zoomWindow = buildZoomWindow\(activeData, logicalRange\.startDate, logicalRange\.endDate\);/);
            // G1b: needsFullInit now keys on (viewMode, pnlSubmode) via renderedModeKey, not
            // viewMode alone — a pnlSubmode change (line -> candles) changes the series TYPE
            // (line -> candlestick) while viewMode stays 'pnl', which the partial-update path
            // cannot express, so it must also force a full rebuild.
            expect(renderChart).toContain("const renderedModeKey = viewMode === 'pnl' ? `pnl:${pnlSubmode}` : viewMode;");
            const fullInitTriggers = renderChart.match(/const needsFullInit = ([^;]+);/)?.[1].split(' || ') ?? [];
            expect(fullInitTriggers).toEqual(expect.arrayContaining(['forceFullXAxisRebuild', 'lastRenderedMode !== renderedModeKey', 'lastRenderedDark !== isDark']));
            expect(renderChart).toMatch(/if \(needsFullInit\) \{\s*applyFullOption\(isDark, buildFullSeries\(isDark, seriesData\), zoomWindow\);\s*\} else \{\s*updateChartData\(activeData, isDark, zoomWindow, false, logicalRange\.startDate\);\s*\}/);
            expect(source).toContain("const CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']};");
            expect(source).toContain("const CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis']};");
            expect(fullOption).toContain("dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],");
            // Why (re-pin, S7): the full option's xAxis ternary now keys on the ladder plan
            // (`ladderAxis`), and the shared policy is null under the ladder, so the time branch
            // merges it through `?.`. Leaving compact mode is a time-axis event (the resize
            // watcher skips the ladder), and its full path still replaces the whole xAxis,
            // labels merged from the desktop policy.
            // Why (re-pin, plan 47 C3): the desktop policy now brings its own formatter, so the
            // replaced xAxis drops the compact labels for the policy's desktop ones.
            expect(fullOption).toMatch(/xAxis: ladderAxis\s*\?\s*\{/);
            expect(fullOption).toContain('formatter: xAxisPolicy?.formatter,');
            expect(fullOption).toContain('...(xAxisPolicy?.axisLabel ?? {}),');
            expect(fullOption).toContain('chartInstance.setOption(option, CHART_FULL_UPDATE_OPTS);');
        });

        it('captures and restores CandlestickChart zoom around its full option replacement', () => {
            const source = readFileSync(new URL('./CandlestickChart.svelte', import.meta.url), 'utf8');
            const renderStart = source.indexOf('function renderChart()');
            const renderEnd = source.indexOf('\n</script>', renderStart);

            expect(renderStart).toBeGreaterThan(-1);
            expect(renderEnd).toBeGreaterThan(renderStart);
            if (renderStart < 0 || renderEnd <= renderStart) {
                throw new Error('CandlestickChart render contract not found');
            }

            const renderChart = source.slice(renderStart, renderEnd);
            const captureStart = renderChart.indexOf('let savedZoom: {start: number; end: number} | null = null;');
            const captureGuard = renderChart.indexOf('if (chartOptionSet && chartInstance) {', captureStart);
            const getOption = renderChart.indexOf('const currentOption = chartInstance.getOption()', captureGuard);
            const replacement = renderChart.indexOf('chartInstance.setOption(option, true);', getOption);
            const restoreGuard = renderChart.indexOf('if (savedZoom) {', replacement);
            const restoreAction = renderChart.indexOf("type: 'dataZoom'", restoreGuard);

            expect(captureStart).toBeGreaterThan(-1);
            expect(captureGuard).toBeGreaterThan(captureStart);
            expect(getOption).toBeGreaterThan(captureGuard);
            expect(replacement).toBeGreaterThan(getOption);
            expect(restoreGuard).toBeGreaterThan(replacement);
            expect(restoreAction).toBeGreaterThan(restoreGuard);

            const capture = blockAfter(renderChart.slice(captureGuard), 'if (chartOptionSet && chartInstance)', '{');
            // Why (re-pin, Y8 47-1): the capture moved above the x-axis policy, which sizes the labels on the zoom it restores, so a
            // slice up to `replacement` spanned the whole option build. The capture is now the body of its guard, braces balanced.
            if (capture === undefined) throw new Error('CandlestickChart saved-zoom capture guard not closed');
            const restoration = renderChart.slice(restoreGuard, renderChart.indexOf('updateArrowRotations(chartInstance);', restoreGuard));
            expect(renderChart).toContain('dataZoom: buildDataZoom(actualShowVolume ? [0, 1] : [0]),');
            expect(capture).toContain('const currentOption = chartInstance.getOption()');
            expect(capture).toContain('const currentZoom = currentOption.dataZoom?.[0];');
            expect(capture).toContain("if (typeof currentZoom?.start === 'number' && typeof currentZoom.end === 'number')");
            expect(capture).toContain('start: currentZoom.start');
            expect(capture).toContain('end: currentZoom.end');
            expect(restoration).toContain('chartInstance.dispatchAction({');
            expect(restoration).toContain("type: 'dataZoom'");
            expect(restoration).toContain('start: savedZoom.start');
            expect(restoration).toContain('end: savedZoom.end');
        });

        it.each(LOT_RESPONSIVE_X_AXIS_CHARTS)('%s takes its labels from the shared policy in both modes and patches only compact labels on resize', (_name, path) => {
            const source = readFileSync(path, 'utf8');
            const resizeAxisUpdate = source.match(/const policy = buildLotXAxisPolicy\(\);[\s\S]*?if \(policy\.axisLabel\) \{[\s\S]*?setOption\(\{xAxis:\s*\{splitNumber:\s*policy\.splitNumber,\s*axisLabel:\s*policy\.axisLabel\}\},\s*\{lazyUpdate:\s*true\}\);/)?.[0];

            // Why (re-pin, plan 47 C3): the caller-owned desktop formatter (`formatAxisDate` with
            // `multiYearAxis`) repeated the day on intraday ticks. The policy's formatter labels
            // the axis in both modes; overlapping desktop labels are still hidden.
            expect(source).toContain('formatter: xAxisPolicy.formatter,');
            expect(source).not.toContain('multiYearAxis');
            expect(source).toContain('hideOverlap: true');
            expect(source).toContain('...(xAxisPolicy.axisLabel ?? {})');
            expect(source).not.toContain('desktopFormatter:');
            expect(resizeAxisUpdate).toBeDefined();
            if (!resizeAxisUpdate) throw new Error(`${_name} responsive resize axis update not found`);
            expect(resizeAxisUpdate).toContain('axisLabel: policy.axisLabel');
        });

        /**
         * The lots charts' `axisBuilder` crash: `TypeError: Cannot read properties of undefined (reading
         * 'axisBuilder')` from ECharts' `CartesianAxisView.render`. Each resize callback below merges a
         * lazy `setOption({xAxis: {splitNumber, axisLabel}}, {lazyUpdate: true})` while the usable width
         * is compact. Merged into an instance that `renderChart()` has just `init()`-ed, or `clear()`-ed
         * because there is nothing to draw, it leaves a model with one x-axis and no grid, and ECharts'
         * next frame throws. The fix is the house guard of LineChart, CandlestickChart and PriceChartFull:
         * a flag that is up only while the instance holds a full option. Every init and clear lowers it,
         * the full setOption raises it, and the resize callback writes the axis only while it is up. The
         * compact bookkeeping stays unconditional, so the next full option starts from the right policy.
         *
         * brokers-detail.spec.ts ("Lots charts axisBuilder guard") reproduces the Gantt and comparison
         * crashes in a browser. No UI path reaches the WAC chart's cleared state today (`showChart` false
         * needs a mode with no points, and the component then falls back to absolute), so for the WAC
         * chart this contract is the only pin.
         */
        const LOT_X_AXIS_PATCH_GUARDS = [
            {
                chart: 'LotGanttChart',
                path: new URL('../../features/brokers/lots/LotGanttChart.svelte', import.meta.url),
                watcher: 'const axisResizeWatcher = createResizeWatcher(',
                // Only the sticky axis instance is patched on resize; the lanes instance never is.
                instance: 'axisInstance',
                flag: 'axisOptionSet',
                // The lazy patch and the compact→wide rebuild (`buildAxisOption(isDark), true`).
                resizeWrites: 2,
                // The `!chartContainer` branch and the `!chartHasData` branch.
                minClears: 2,
                // The axis instance is also disposed when its container is remounted.
                lowersOnDispose: true,
                fullSetOption: /axisInstance\??\.setOption\(buildAxisOption\(isDark\), CHART_SET_OPTION_OPTS\)/g,
            },
            {
                chart: 'LotComparisonChart',
                path: new URL('../../features/brokers/lots/LotComparisonChart.svelte', import.meta.url),
                watcher: 'const resizeWatcher = createResizeWatcher(',
                instance: 'chartInstance',
                flag: 'chartOptionSet',
                // Only the lazy patch: compact→wide goes through renderChart(), which keeps its own books.
                resizeWrites: 1,
                minClears: 1,
                lowersOnDispose: false,
                fullSetOption: /chartInstance\.setOption\(option, /g,
            },
            {
                chart: 'LotWacPriceChart',
                path: new URL('../../features/brokers/lots/LotWacPriceChart.svelte', import.meta.url),
                watcher: 'const resizeWatcher = createResizeWatcher(',
                instance: 'chartInstance',
                flag: 'chartOptionSet',
                resizeWrites: 1,
                minClears: 1,
                lowersOnDispose: false,
                fullSetOption: /chartInstance\.setOption\(option, /g,
            },
        ] as const;

        /** The body of the block that `opener` (ending in `{`) opens first after `anchor`, braces balanced. */
        function blockAfter(source: string, anchor: string, opener: string): string | undefined {
            const at = source.indexOf(anchor);
            const open = at < 0 ? -1 : source.indexOf(opener, at + anchor.length);
            if (open < 0) return undefined;
            const bodyStart = open + opener.length;
            let depth = 1;
            for (let i = bodyStart; i < source.length; i++) {
                if (source[i] === '{') depth++;
                else if (source[i] === '}' && --depth === 0) return source.slice(bodyStart, i);
            }
            return undefined;
        }

        /** Where every match of `pattern` (a global regex) starts in `text`. */
        function sitesOf(text: string, pattern: RegExp): number[] {
            return [...text.matchAll(pattern)].map((match) => match.index ?? -1);
        }

        /**
         * The first line of code after the call that starts at `callAt`: past its balanced parentheses
         * and `;`, with blank space and line comments skipped, then an optional `skip` statement.
         */
        function lineAfterCall(body: string, callAt: number, skip?: RegExp): string {
            let end = body.indexOf('(', callAt);
            for (let depth = 0; end >= 0 && end < body.length; end++) {
                if (body[end] === '(') depth++;
                else if (body[end] === ')' && --depth === 0) break;
            }
            const gap = /^(?:\s+|\/\/[^\n]*)+/;
            let rest = body
                .slice(end + 1)
                .replace(/^;/, '')
                .replace(gap, '');
            if (skip) rest = rest.replace(skip, '').replace(gap, '');
            return rest.split('\n')[0].trim();
        }

        it.each(LOT_X_AXIS_PATCH_GUARDS)('$chart writes its x-axis on resize only while $flag says the instance holds a full option', ({chart, watcher, path, instance, flag, resizeWrites}) => {
            const source = readFileSync(path, 'utf8');
            const callback = blockAfter(source, watcher, '=> {');
            if (!callback) throw new Error(`${chart}: resize callback not found (${watcher})`);

            const write = `${instance}\\??\\.setOption\\(`;
            // The brief's one-liner `if (flag) instance.setOption(…)` and the house block form both qualify.
            const guardedWrite = `if \\(${flag}\\) \\{?\\s*${write}`;
            // Positive control first: the scan still sees the writes it is about.
            expect(sitesOf(callback, new RegExp(write, 'g')).length, `${chart}: setOption calls in the resize callback`).toBe(resizeWrites);
            expect(sitesOf(callback, new RegExp(guardedWrite, 'g')).length, `${chart}: resize-callback setOption calls behind if (${flag})`).toBe(resizeWrites);

            const lazyPatchInCompactBranch = new RegExp(`if \\(policy\\.axisLabel\\) \\{\\s*${guardedWrite}\\{xAxis:\\s*\\{splitNumber:\\s*policy\\.splitNumber,\\s*axisLabel:\\s*policy\\.axisLabel\\}\\},\\s*\\{lazyUpdate:\\s*true\\}\\);`);
            expect(lazyPatchInCompactBranch.test(callback), `${chart}: the guarded lazy patch sits inside the existing if (policy.axisLabel) branch`).toBe(true);
            expect(/responsiveXAxisCompact = policy\.compact;\s*if \(policy\.axisLabel\) \{/.test(callback), `${chart}: the compact bookkeeping stays unconditional, outside the guard`).toBe(true);
        });

        it.each(LOT_X_AXIS_PATCH_GUARDS)('$chart lowers $flag on every init and clear in renderChart() and raises it after the full setOption', ({chart, path, instance, flag, minClears, lowersOnDispose, fullSetOption}) => {
            const source = readFileSync(path, 'utf8');
            const renderChart = blockAfter(source, 'function renderChart(', ') {');
            if (!renderChart) throw new Error(`${chart}: renderChart() not found`);

            const inits = sitesOf(renderChart, new RegExp(`${instance} = echarts\\.init\\(`, 'g'));
            const clears = sitesOf(renderChart, new RegExp(`${instance}\\??\\.clear\\(\\)`, 'g'));
            const disposes = lowersOnDispose ? sitesOf(renderChart, new RegExp(`${instance}\\??\\.dispose\\(\\)`, 'g')) : [];
            const fullSets = sitesOf(renderChart, fullSetOption);
            // Positive controls: "every site is followed by …" is also true of no site at all.
            expect(inits.length, `${chart}: ${instance} init sites in renderChart()`).toBeGreaterThanOrEqual(1);
            expect(clears.length, `${chart}: ${instance} clear sites in renderChart()`).toBeGreaterThanOrEqual(minClears);
            if (lowersOnDispose) expect(disposes.length, `${chart}: ${instance} dispose sites in renderChart()`).toBeGreaterThanOrEqual(1);
            expect(fullSets.length, `${chart}: the full ${instance} setOption in renderChart()`).toBe(1);

            expect(source.includes(`let ${flag} = false;`), `${chart}: declares let ${flag} = false; (no option until renderChart() sets one)`).toBe(true);
            const lowered = new RegExp(`^${flag} = false;`);
            for (const at of [...inits, ...clears]) {
                expect(lineAfterCall(renderChart, at), `${chart}: ${flag} = false; right after ${renderChart.slice(at, renderChart.indexOf('(', at))}(…)`).toMatch(lowered);
            }
            for (const at of disposes) {
                expect(lineAfterCall(renderChart, at, new RegExp(`^${instance} = undefined;`)), `${chart}: ${flag} = false; right after ${instance}.dispose()`).toMatch(lowered);
            }
            for (const at of fullSets) {
                expect(lineAfterCall(renderChart, at), `${chart}: ${flag} = true; right after the full setOption`).toMatch(new RegExp(`^${flag} = true;`));
            }
        });

        it('keeps PerformanceChart outside the date-axis policy', () => {
            const source = readFileSync(new URL('../../features/dashboard/PerformanceChart.svelte', import.meta.url), 'utf8');

            expect(source).not.toContain('responsiveXAxis');
            expect(source).not.toContain('buildResponsiveXAxisPolicy');
        });

        describe('the time-axis charts size grid.right with timeAxisGridRight (plan 52, C1)', () => {
            // Plan 52, C1: GrowthChart, AllocationHistoryChart and LotComparisonChart widen `grid.right` so the last time
            // label is drawn whole. These pins hold the wiring the jsdom harnesses cannot reach: the measure each chart hands
            // the helper, the grid it lays out, its resize callback and GrowthChart's data-update path.

            /** The three charts the defect touched, with the base inset and the label size each one draws its time axis with. */
            const INSET_CHARTS = [
                {chart: 'GrowthChart', path: new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), base: "'4%'", fontSize: 14},
                {chart: 'AllocationHistoryChart', path: new URL('../../features/dashboard/AllocationHistoryChart.svelte', import.meta.url), base: "'4%'", fontSize: 14},
                {chart: 'LotComparisonChart', path: new URL('../../features/brokers/lots/LotComparisonChart.svelte', import.meta.url), base: '18', fontSize: 12},
            ] as const;

            /** The argument text of every `timeAxisGridRight(…)` call in `source`, parentheses balanced: one entry per call site. */
            function gridRightCallArgs(source: string): string[] {
                return sitesOf(source, /\btimeAxisGridRight\(/g).map((at) => {
                    const open = source.indexOf('(', at);
                    let depth = 0;
                    for (let i = open; i < source.length; i++) {
                        if (source[i] === '(') depth++;
                        else if (source[i] === ')' && --depth === 0) return source.slice(open + 1, i);
                    }
                    throw new Error(`An unbalanced timeAxisGridRight( call at ${at}`);
                });
            }

            /** `let appliedGridRight = '4%';`, typed or not: the inset the instance holds, compared by the resize callback. */
            const APPLIED_GRID_RIGHT_DECLARATION = /let appliedGridRight(?::\s*(?:number \| string|string \| number))? = '4%';/;

            it.each(INSET_CHARTS)('$chart imports the inset helpers and hands every timeAxisGridRight call its base and a $fontSize px measure (E2)', ({chart, path, base, fontSize}) => {
                // Why: the inset fits the labels only if it measures them in the size the axis draws them at, against the chart own base.
                const source = readFileSync(path, 'utf8');
                const importedNames =
                    /import\s+\{([^}]*)\}\s+from\s+['"][^'"]*responsiveXAxis['"]/
                        .exec(source)?.[1]
                        .split(',')
                        .map((name) => name.trim()) ?? [];
                const calls = gridRightCallArgs(source);

                expect(importedNames, `${chart}: the names of its responsiveXAxis import`).toEqual(expect.arrayContaining(['timeAxisGridRight', 'axisLabelMeasure']));
                expect(calls.length, `${chart}: timeAxisGridRight( call sites`).toBeGreaterThan(0);
                for (const args of calls) {
                    expect(args, `${chart}: the base of timeAxisGridRight(${args})`).toMatch(new RegExp(`\\bbase:\\s*${base}\\s*[,}]`));
                    expect(args, `${chart}: the measure of timeAxisGridRight(${args})`).toContain(`measure: axisLabelMeasure(chartInstance, ${fontSize})`);
                }
            });

            it.each([
                {
                    chart: 'GrowthChart',
                    path: new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url),
                    // The applyFullOption slice of the existing GrowthChart pins: from the function to the end of the script.
                    body: (source: string) => {
                        const start = source.indexOf('function applyFullOption(');
                        const end = source.indexOf('\n</script>', start);
                        return start < 0 || end <= start ? undefined : source.slice(start, end);
                    },
                },
                {
                    chart: 'AllocationHistoryChart',
                    path: new URL('../../features/dashboard/AllocationHistoryChart.svelte', import.meta.url),
                    body: (source: string) => blockAfter(source, 'function buildChartOption(', '): echarts.EChartsOption {'),
                },
            ])('$chart lays its full option out on the computed gridRight and records it as the applied inset (E2)', ({chart, path, body}) => {
                // Why: the grid must carry the computed inset, not the literal 4%, and the resize guard compares against the inset the full option applied.
                const source = readFileSync(path, 'utf8');
                const fullOption = body(source);
                if (!fullOption) throw new Error(`${chart}: the full-option builder not found`);

                expect(source, `${chart}: declares the applied inset`).toMatch(APPLIED_GRID_RIGHT_DECLARATION);
                expect(fullOption, `${chart}: the inset is computed and recorded`).toMatch(/const gridRight = (?:xAxisPolicy\s*\?\s*)?timeAxisGridRight\(\{[^;]*;\s*appliedGridRight = gridRight;/);
                expect(fullOption, `${chart}: grid.right is the computed inset`).toMatch(/\bgrid:\s*\{[^{}]*\bright:\s*gridRight\b/);
                expect(fullOption, `${chart}: grid.right is no longer the 4% literal`).not.toMatch(/\bgrid:\s*\{[^{}]*\bright:\s*'4%'/);
            });

            it('LotComparisonChart computes its grid right in buildOption in place of the 18 px literal (E2)', () => {
                // Why: the lots chart has no other grid write, so the inset must be computed where the option is built.
                const source = readFileSync(new URL('../../features/brokers/lots/LotComparisonChart.svelte', import.meta.url), 'utf8');
                const buildOption = blockAfter(source, 'function buildOption(', '{');
                if (!buildOption) throw new Error('LotComparisonChart: buildOption() not found');

                expect(buildOption).toMatch(/\bgrid:\s*\{[^{}]*?\bright:\s*timeAxisGridRight\(\{/);
                expect(buildOption).not.toMatch(/\bgrid:\s*\{[^{}]*?\bright:\s*18\b/);
            });

            it('GrowthChart re-lays its grid on resize only off the ladder and only when the inset changes, eagerly, then re-reads the plot (E3)', () => {
                // Why: a resize moves the px a 4% base stands for; syncPlotGeometry() reads the grid this write lays out, so it cannot be lazy.
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const resizeStart = source.indexOf('const resizeWatcher = createResizeWatcher(() => {');
                const resizeEnd = source.indexOf('\n    let darkModeObserver', resizeStart);
                if (resizeStart < 0 || resizeEnd <= resizeStart) throw new Error('GrowthChart resize watcher contract not found');
                const resizeCallback = source.slice(resizeStart, resizeEnd);
                const offLadder = blockAfter(resizeCallback, 'if (chartInstance && chartContainer && activeChartData && !ladderActive)', '{');
                if (!offLadder) throw new Error('GrowthChart: the off-ladder block of the resize watcher not found');

                expect(source).toMatch(APPLIED_GRID_RIGHT_DECLARATION);
                expect(offLadder).toContain('timeAxisGridRight(');
                expect(offLadder).toMatch(/if \(gridRight !== appliedGridRight\) \{(?:\s|\/\/[^\n]*)*appliedGridRight = gridRight;(?:\s|\/\/[^\n]*)*chartInstance\.setOption\(\{grid: \{right: gridRight\}\}\);(?:\s|\/\/[^\n]*)*syncPlotGeometry\(\);/);
                expect(resizeCallback).not.toMatch(/setOption\(\{grid:[^;]*lazyUpdate/);
                // The existing guard stays the only ladderActive reference: the inset does not fork the block on the submode.
                expect((resizeCallback.match(/\bladderActive\b/g) ?? []).length).toBe(1);
            });

            it('AllocationHistoryChart re-lays its grid on resize only when the inset changes, lazily (E4)', () => {
                // Why: the same width-dependent inset; this chart reads no plot geometry back, so its lazy axis write is enough.
                const source = readFileSync(new URL('../../features/dashboard/AllocationHistoryChart.svelte', import.meta.url), 'utf8');
                const callback = blockAfter(source, 'resizeObserver = new ResizeObserver(', '=> {');
                if (!callback) throw new Error('AllocationHistoryChart: the ResizeObserver callback not found');

                expect(source).toMatch(APPLIED_GRID_RIGHT_DECLARATION);
                expect(callback).toContain('timeAxisGridRight(');
                expect(callback).toMatch(/if \(gridRight !== appliedGridRight\) \{(?:\s|\/\/[^\n]*)*appliedGridRight = gridRight;(?:\s|\/\/[^\n]*)*chartInstance\.setOption\(\{grid: \{right: gridRight\}\}, \{lazyUpdate: true\}\);/);
            });

            it('LotComparisonChart leaves the inset out of its resize callback: a px base does not depend on the width (E5)', () => {
                // Why: with base 18 the inset follows the labels alone, so the resize keeps the single axis write LOT_X_AXIS_PATCH_GUARDS counts.
                const source = readFileSync(new URL('../../features/brokers/lots/LotComparisonChart.svelte', import.meta.url), 'utf8');
                const callback = blockAfter(source, 'const resizeWatcher = createResizeWatcher(', '=> {');
                if (!callback) throw new Error('LotComparisonChart: resize callback not found');

                expect(callback, 'positive control: the slice is the callback that re-plans the axis').toContain('buildLotXAxisPolicy(');
                expect(callback).not.toContain('timeAxisGridRight');
            });

            it('GrowthChart sends the inset with every time-axis data update and none from the ladder (E6)', () => {
                // Why: a data update brings new dates, hence new labels; the ladder category axis keeps the 4% the full option gave it.
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const updateStart = source.indexOf('function updateChartData(');
                const updateEnd = source.indexOf('\n    function syncResolutionToViewport()', updateStart);
                if (updateStart < 0 || updateEnd <= updateStart) throw new Error('GrowthChart updateChartData contract not found');
                const updateChartData = source.slice(updateStart, updateEnd);
                const ladderBranch = /if \(entry\.ladder\) \{([\s\S]*?)\} else \{\s*const xAxisPolicy = buildResponsiveXAxisPolicy\(/.exec(updateChartData)?.[1];

                expect(updateChartData).toContain('let gridRight: number | string | undefined;');
                expect(updateChartData).toMatch(/xAxis = xAxisPolicy\.compact \? [^;]+;\s*gridRight = timeAxisGridRight\(\{[^;]*\);\s*appliedGridRight = gridRight;/);
                expect(updateChartData).toMatch(/\.\.\.\(gridRight === undefined \? \{\} : \{grid: \{right: gridRight\}\}\),\s*xAxis,/);
                expect(ladderBranch, 'positive control: the ladder branch of updateChartData').toBeDefined();
                expect(ladderBranch).not.toContain('gridRight');
            });
        });
    });

    describe('GrowthChart P&L mode (G1a/G1b/G1c) series-shape and axis regressions', () => {
        // -------------------------------------------------------------------
        // Why (FE6a): GrowthChart's derived data, series and tooltip moved out of the
        // component into three pure modules (growthChartData.ts, growthChartSeries.ts,
        // growthChartTooltip.ts), verbatim except for their parameters. Every helper this
        // block used to copy for execution — and pin to the component's text, because a
        // closure inside <script> could not be imported — is now imported and run as it
        // ships; the contracts those pins guarded are asserted on what the real builders
        // return. Source pins remain only for code that stayed in GrowthChart.svelte.
        //
        // Fixture builders, in the shapes of growthChartData.ts: SeriesPoint = {name,
        // value: [date, value|null], bucketStart, bucketEnd, resolution}; CandleSeriesPoint
        // adds open/high/low/close on top.
        // -------------------------------------------------------------------
        function seriesPoint(date: string, value: number | null, bucketEnd: string = date): SeriesPoint {
            return {name: date, value: [date, value], bucketStart: date, bucketEnd, resolution: 'daily'};
        }

        function candlePoint(date: string, ohlc: {open: number; high: number; low: number; close: number} | null): CandleSeriesPoint {
            return {...seriesPoint(date, ohlc?.close ?? null), open: ohlc?.open ?? null, high: ohlc?.high ?? null, low: ohlc?.low ?? null, close: ohlc?.close ?? null};
        }

        function candlePointRaw(date: string, open: number | null, close: number | null, low: number | null, high: number | null): CandleSeriesPoint {
            return {...seriesPoint(date, close), open, close, low, high};
        }

        /** `count` consecutive ISO days from `first`. */
        function isoDays(first: string, count: number): string[] {
            const start = Date.parse(`${first}T00:00:00Z`);
            return Array.from({length: count}, (_, index) => new Date(start + index * 86_400_000).toISOString().slice(0, 10));
        }

        type GrowthInputsFixture = Partial<Omit<AggregationInputs, 'dates' | 'eurStackedData'>> & {totalPnl?: Array<number | null>};

        /**
         * The aggregation inputs as GrowthChart's `aggregationInputs` hands them to the builders of
         * growthChartData.ts: every series aligned to `dates`. A series the case does not name is
         * empty — null for a level, 0 for a flow — so each case states only what it is about.
         */
        function growthInputs(dates: string[], {totalPnl, ...overrides}: GrowthInputsFixture = {}): AggregationInputs {
            const levels = (): Array<number | null> => dates.map(() => null);
            const flows = (): number[] => dates.map(() => 0);
            return {
                dates,
                eurStackedData: {bookAssetLike: levels(), cashContributed: levels(), cashGenerated: levels(), nav: levels(), capitalBaseline: levels(), totalPnl: totalPnl ?? levels()},
                pctValuesRaw: {mwrrCum: levels(), twrr: levels(), roi: levels()},
                pnlBrokerSeriesRaw: [],
                pnlCandleByDate: new Map<string, DailyCandle>(),
                dividendValues: flows(),
                interestValues: flows(),
                costValues: flows(),
                depositValues: flows(),
                acqFromNewCapitalValues: flows(),
                acqFromReinvestedValues: flows(),
                ...overrides,
            };
        }

        /** Each label is its own slot's name, so a swapped slot shows in the names. The product passes translations. */
        const PNL_LABELS: PnlLabels = {total: 'total', dividend: 'dividend', interest: 'interest', costs: 'costs', deposit: 'deposit', acqNewCapital: 'acqNewCapital', acqReinvested: 'acqReinvested', bookValue: 'bookValue'};
        const EUR_LABELS: EurLabels = {bookAssetLike: 'bookAssetLike', bookAssetLikeTooltip: 'bookAssetLikeTooltip', cashContributed: 'cashContributed', cashGenerated: 'cashGenerated', nav: 'nav', capitalBaseline: 'capitalBaseline', capitalBaselineTooltip: 'capitalBaselineTooltip'};

        /** The P&L view on screen, as GrowthChart's `seriesContext()` builds it for the series builders. */
        function pnlContext(pnlSubmode: PnlSubmode, aggregationInputs: AggregationInputs): GrowthSeriesContext {
            return {viewMode: 'pnl', pnlSubmode, eurLabels: EUR_LABELS, pnlLabels: PNL_LABELS, pctSeries: [], aggregationInputs};
        }

        /** The keys of an ECharts series option read here. `echarts.SeriesOption` is a union of every series type, so a drawn series is read through this one view of it. */
        interface DrawnSeries {
            name?: string;
            type?: string;
            stack?: string;
            data?: unknown;
            smooth?: boolean;
            connectNulls?: boolean;
            silent?: boolean;
            lineStyle?: {color?: string; type?: string; width?: number};
            itemStyle?: {color?: string; color0?: string; borderColor?: string; borderColor0?: string};
            areaStyle?: {color?: string};
            tooltip?: {show?: boolean};
        }

        function drawn(series: ReturnType<typeof buildGrowthFullSeries>): DrawnSeries[] {
            return series as unknown as DrawnSeries[];
        }

        // ECharts' documented empty-value sentinel, ECHARTS_EMPTY_VALUE (growthChartSeries.ts). A
        // candlestick gap MUST be this string and never `null`: on a category base axis,
        // whiskerBoxCommon's getInitialData clones items with `isArray(item) ? … : isArray(item.value)`,
        // so a null item dereferences `null.value` and throws inside SeriesModel.init — before
        // GlobalModel finishes building, leaving no _seriesIndices and silently no-oping every later
        // setOption. Verified against this exact echarts build by the SSR smoke test at the end of the
        // candles block, not inferred.
        describe('toCandlestickPoint', () => {
            it('returns the [open, close, low, high] quad, via the real buildOhlcQuad, in absolute mode (base=1) regardless of any outer view mode', () => {
                const point = candlePoint('2026-01-05', {open: 100, close: 110, low: 95, high: 115});
                expect(toCandlestickPoint(point)).toEqual([100, 110, 95, 115]);
                expect(toCandlestickPoint(point)).toEqual(buildOhlcQuad(100, 110, 95, 115, false, 1));
                // Why (FE6a): the widened return type is part of the contract — `number[] | null` would let a
                // null flow back in without a type error. It was pinned as source text while the function
                // was a closure of the component; exported, it is checked as a type (svelte-check reads this
                // file; at run time expectTypeOf asserts nothing).
                expectTypeOf(toCandlestickPoint).toEqualTypeOf<(point: CandleSeriesPoint) => number[] | string>();
            });

            const missingLegScenarios: Array<[string, number | null, number | null, number | null, number | null]> = [
                ['open', null, 1, 1, 1],
                ['close', 1, null, 1, 1],
                ['low', 1, 1, null, 1],
                ['high', 1, 1, 1, null],
            ];

            it.each(missingLegScenarios)("returns ECharts' empty-value sentinel '-' (a gap that still OCCUPIES its category slot, never null and never a synthesized flat bar) when only %s is missing", (_field, open, close, low, high) => {
                // Not null: that crashes SeriesModel.init on a category axis (see
                // ECHARTS_EMPTY_VALUE above). Not omitted either: a category axis aligns
                // by POSITION, so dropping the item would shift every later candle by one
                // slot and silently desync the whole series from its dates.
                expect(toCandlestickPoint(candlePointRaw('2026-01-05', open, close, low, high))).toBe('-');
            });

            it('returns a quad when all four legs are present, even when one leg is exactly zero (zero is not "missing")', () => {
                expect(toCandlestickPoint(candlePointRaw('2026-01-05', 0, 5, 0, 10))).toEqual([0, 5, 0, 10]);
            });
        });

        describe('clipToSign', () => {
            it('keeps a positive value unchanged (same object reference) when keepPositive is true', () => {
                const point = seriesPoint('2026-01-01', 50);
                expect(clipToSign(point, true)).toBe(point);
            });

            it('keeps a negative value unchanged (same object reference) when keepPositive is false', () => {
                const point = seriesPoint('2026-01-01', -50);
                expect(clipToSign(point, false)).toBe(point);
            });

            it('treats an exact zero as positive: kept when keepPositive is true, nulled when keepPositive is false', () => {
                const point = seriesPoint('2026-01-01', 0);
                expect(clipToSign(point, true)).toBe(point);
                expect(clipToSign(point, false).value[1]).toBeNull();
            });

            it('nulls only the value (not the date/name/bucket metadata) when the sign does not match', () => {
                const point = seriesPoint('2026-01-01', -50, '2026-01-02');
                const clipped = clipToSign(point, true);
                expect(clipped).not.toBe(point);
                expect(clipped.value).toEqual(['2026-01-01', null]);
                expect(clipped.name).toBe(point.name);
                expect(clipped.bucketStart).toBe(point.bucketStart);
                expect(clipped.bucketEnd).toBe(point.bucketEnd);
            });

            it('preserves a null point unchanged (same reference) for BOTH keepPositive branches — a missing day is a gap in both series, never fabricated', () => {
                const point = seriesPoint('2026-01-01', null);
                expect(clipToSign(point, true)).toBe(point);
                expect(clipToSign(point, false)).toBe(point);
            });
        });

        describe('findReferenceTotalPnl', () => {
            const dates = ['2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26'];
            const values = [100, 150, 90, 200];
            // Why (FE6a): the real function reads the entry on screen and the daily inputs, so each case
            // hands it both: the inputs, and the daily entry the builders make of them.
            const inputs = growthInputs(dates, {totalPnl: values});
            const entry = buildResolutionData(inputs, 'daily');

            it('returns null for an empty series (nothing to draw a reference against)', () => {
                const empty = growthInputs([]);
                expect(findReferenceTotalPnl(buildResolutionData(empty, 'daily'), '2026-01-12', empty)).toBeNull();
            });

            it('falls back to the first point when referenceDate is null', () => {
                expect(findReferenceTotalPnl(entry, null, inputs)).toBe(100);
            });

            it('anchors a referenceDate that falls between two days on the last day BEFORE it, never on the next one', () => {
                // Why (re-pin, S10): the product reads the DAILY series and never a later day (e7773a143), so 01-08 anchors on 01-05 (100), not on 01-12 (150).
                expect(findReferenceTotalPnl(entry, '2026-01-08', inputs)).toBe(100);
            });

            it('matches on an exact day', () => {
                // Why (re-pin, S10): the product reads the DAILY series and never a later day (e7773a143), so an exact date is matched on its own day, not on a bucket end.
                expect(findReferenceTotalPnl(entry, '2026-01-19', inputs)).toBe(90);
            });

            it('anchors a referenceDate after every day on the LAST day, not on the first', () => {
                // Why (re-pin, S10): the product reads the DAILY series and never a later day (e7773a143), so a date after every day anchors on the last one, 01-26 (200), not on the first (100).
                expect(findReferenceTotalPnl(entry, '2099-01-01', inputs)).toBe(200);
            });

            it('can itself return null when the located day has no P&L value that day (a genuine gap is a valid reference, never guessed)', () => {
                // Why (re-pin, S10): the product reads the DAILY series and never a later day (e7773a143), so a day with no P&L yields null, never the next day's 50.
                const withGap = growthInputs(['2026-01-05', '2026-01-12'], {totalPnl: [null, 50]});
                expect(findReferenceTotalPnl(buildResolutionData(withGap, 'daily'), '2026-01-05', withGap)).toBeNull();
            });

            it("reads the DAILY series, never the aggregated buckets: under a weekly entry a mid-week day anchors on its own value, not on its week's close", () => {
                // Why (FE6a): the source pin that kept the first-bucket-end lookup out
                // (`p.bucketEnd >= referenceDate`, ~600 instead of 0 under a monthly bucket) left with the
                // copy it policed. This is the same rule as behaviour: the week of 01-07 closes at 106 on
                // 01-11, the day itself held 102.
                const days = isoDays('2026-01-05', 8);
                const weeklyInputs = growthInputs(days, {totalPnl: [100, 101, 102, 103, 104, 105, 106, 107]});
                const weekly = buildResolutionData(weeklyInputs, 'weekly');

                // Positive control: the entry is coarser than the days, so the two readings differ.
                expect(weekly.pnl.total.values).toEqual([106, 107]);
                expect(findReferenceTotalPnl(weekly, '2026-01-07', weeklyInputs)).toBe(102);
            });
        });

        describe('resize watcher keeps the splitNumber/axisLabel update unconditional off the ladder', () => {
            it('keeps the ladder out of buildResponsiveXAxisPolicy (time axis only), but does not fork the actual setOption call on the submode', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const resizeStart = source.indexOf('const resizeWatcher = createResizeWatcher(() => {');
                const resizeEnd = source.indexOf('\n    let darkModeObserver', resizeStart);
                expect(resizeStart).toBeGreaterThan(-1);
                expect(resizeEnd).toBeGreaterThan(resizeStart);
                if (resizeStart < 0 || resizeEnd <= resizeStart) throw new Error('GrowthChart resize watcher contract not found');

                const resizeCallback = source.slice(resizeStart, resizeEnd);
                // Why (re-pin, S7): the ladder (Candles, Income) owns its x axis and re-plans it
                // through the resolution sync, so the watcher no longer computes
                // isCandlesSubmode: it skips the responsive policy under the ladder and builds
                // it for the time axis only. The invariant stands: the policy never reaches the
                // ladder's category axis, and the setOption call below is not forked on the
                // submode.
                expect(resizeCallback).toContain('if (chartInstance && chartContainer && activeChartData && !ladderActive) {');
                expect(resizeCallback).toContain("axisType: 'time',");
                // The actual xAxis update stays a SINGLE unconditional object — unlike
                // updateChartData's category branch, it never refreshes `data`: a resize
                // never changes which dates are on screen, only the pixel budget for labels.
                expect(resizeCallback).toContain('chartInstance.setOption({xAxis: {splitNumber: policy.splitNumber, axisLabel: policy.axisLabel}}, {lazyUpdate: true});');
                expect(resizeCallback).not.toContain('data: activeChartData.dates');
                expect(resizeCallback).not.toContain('data: entry.dates');
                // Exactly ONE ladderActive reference in this block (the guard above) — if a
                // future edit also forked the setOption call on it, this count would become 2
                // and this assertion would catch it.
                // Why (re-pin, S7): isCandlesSubmode is gone, so a submode fork would now key
                // on `ladderActive`; that is the name counted.
                const ladderActiveCount = (resizeCallback.match(/\bladderActive\b/g) ?? []).length;
                expect(ladderActiveCount).toBe(1);
            });
        });

        describe('applyFullOption completes the category-vs-time xAxis ternary on both branches', () => {
            it('sets category type/data/boundaryGap and time type/splitNumber, merging one axisLabel source per branch, sharing the axisLine and declaring splitLine exactly once per branch', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const fullOptionStart = source.indexOf('function applyFullOption(');
                const fullOptionEnd = source.indexOf('\n</script>', fullOptionStart);
                expect(fullOptionStart).toBeGreaterThan(-1);
                expect(fullOptionEnd).toBeGreaterThan(fullOptionStart);
                if (fullOptionStart < 0 || fullOptionEnd <= fullOptionStart) throw new Error('GrowthChart applyFullOption contract not found');

                const fullOption = source.slice(fullOptionStart, fullOptionEnd);
                // Why (re-pin, S7): the ternary now keys on the ladder plan (`ladderAxis`), not on
                // the candles submode; it is still the one xAxis literal, category then time.
                const xAxisStart = fullOption.search(/xAxis: ladderAxis\s*\?/);
                const xAxisEnd = fullOption.indexOf('yAxis: {', xAxisStart);
                expect(xAxisStart).toBeGreaterThan(-1);
                expect(xAxisEnd).toBeGreaterThan(xAxisStart);
                if (xAxisStart < 0 || xAxisEnd <= xAxisStart) throw new Error('GrowthChart applyFullOption xAxis ternary not found');

                const xAxisBlock = fullOption.slice(xAxisStart, xAxisEnd);
                // Category branch (the ladder: Candles and Income).
                expect(xAxisBlock).toContain("type: 'category',");
                expect(xAxisBlock).toContain('data: activeChartData?.dates ?? dates,');
                expect(xAxisBlock).toContain('boundaryGap: true,');
                // Time branch (every other mode/submode) — not just spot-checked, but
                // proven present alongside the category branch above, in the same slice.
                expect(xAxisBlock).toContain("type: 'time',");
                // Why (re-pin, S7): the shared policy is null under the ladder, so the time branch
                // reads it through `?.`; its compact splitNumber is still spread on that branch.
                expect(xAxisBlock).toContain('...(xAxisPolicy?.compact ? {splitNumber: xAxisPolicy.splitNumber} : {}),');

                // Each branch merges its own label source exactly once, and the shared axisLine
                // appears exactly twice (once per branch) — catches a future edit that updates
                // one branch and forgets its sibling.
                // Why (re-pin, S7): the axisLabel merge is no longer shared. The time branch
                // merges the responsive policy, the category branch the ladder plan's labels.
                // Counting each source once keeps both branches complete, and a policy merge
                // leaking onto the ladder's axis (a count of 2) still turns this red.
                const policyLabelMergeCount = (xAxisBlock.match(/\.\.\.\(xAxisPolicy\??\.axisLabel \?\? \{\}\)/g) ?? []).length;
                const ladderLabelMergeCount = (xAxisBlock.match(/\.\.\.ladderAxis\.axisLabel\b/g) ?? []).length;
                const axisLineCount = (xAxisBlock.match(/axisLine: \{lineStyle: \{color: gridColor\}\},/g) ?? []).length;
                // Why (re-pin, S10): splitLine is no longer shared theming. It now draws the
                // bucket separators: always on the category branch, and on the time branch only
                // under the ladder. So the value differs between branches, and S7 will reshape it
                // (splitLine.interval). What survives is that each branch declares the KEY once:
                // a second `splitLine` in the same literal silently wins, and the product comment
                // records that this already happened. The pin counts the key, not its value.
                // Why (re-pin, S7): the category branch (the ladder: Candles and Income) now takes
                // its separators from the ladder plan (`interval: ladderAxis.splitLine.interval`);
                // the time branch draws none (`splitLine: {show: false}`), so the S10 lines above
                // describe the pre-S7 state. The pin is unchanged: one `splitLine` KEY per branch.
                const splitLineCount = (xAxisBlock.match(/^[ \t]+splitLine:/gm) ?? []).length;
                expect(policyLabelMergeCount).toBe(1);
                expect(ladderLabelMergeCount).toBe(1);
                expect(axisLineCount).toBe(2);
                expect(splitLineCount).toBe(2);
            });
        });

        describe('candles-submode positional alignment: candlestick quads line up 1:1 with dates', () => {
            it("builds dates, pnl.total, pnl.candle and every pnl.brokers[].metric on the entry's own buckets, 1:1 by position — in the density cascade and in the ladder alike", () => {
                // Why (FE6a): getResolutionData's body moved to growthChartData.ts as buildResolutionData (the
                // component keeps only its memo), beside the ladder's buildLadderData. The source pin that
                // counted ONE buildBucketInfos call is replaced by the property that single call protected:
                // every series of an entry stands on that entry's buckets, position by position. The
                // fixture is sparse where a second, independent bucketing would disagree: no candle in the
                // second week, and a broker that joins the scope on the 11th day.
                const dates = isoDays('2026-01-05', 24); // Mon 01-05 … Wed 01-28: three whole ISO weeks and a running one
                const totalPnl = dates.map((_, index) => 100 + index);
                const brokerA = dates.map((_, index) => 10 + index);
                const brokerB = dates.map((_, index) => (index < 10 ? null : 20 + index));
                const candles = new Map<string, DailyCandle>(dates.flatMap((date, index): Array<[string, DailyCandle]> => (index >= 7 && index <= 13 ? [] : [[date, {open: 50 + index, high: 60 + index, low: 40 + index, close: 55 + index}]])));
                const inputs = growthInputs(dates, {
                    totalPnl,
                    pnlCandleByDate: candles,
                    pnlBrokerSeriesRaw: [
                        {brokerId: 1, brokerName: 'Broker A', values: brokerA},
                        {brokerId: 2, brokerName: 'Broker B', values: brokerB},
                    ],
                });
                const today = '2026-01-28';
                const entries: Array<[string, AggregatedResolutionData, number]> = [
                    ['cascade daily', buildResolutionData(inputs, 'daily'), 24],
                    ['cascade weekly', buildResolutionData(inputs, 'weekly'), 4],
                    ['ladder 1D', buildLadderData(inputs, '1D', today), 24],
                    ['ladder 1W', buildLadderData(inputs, '1W', today), 4],
                ];
                const positions = (points: SeriesPoint[]) => points.map((point) => point.value[0]);
                const onDay = (series: Array<number | null>) => (date: string) => series[dates.indexOf(date)];

                for (const [label, entry, bucketCount] of entries) {
                    // Positive control: the entry has the buckets it should, so 1:1 is not 0:0.
                    expect(entry.buckets, label).toHaveLength(bucketCount);
                    const closings = entry.buckets.map((bucket) => bucket.date);

                    expect(entry.dates, label).toEqual(closings);
                    expect(positions(entry.pnl.total.points), label).toEqual(closings);
                    expect(entry.pnl.total.values, label).toEqual(closings.map(onDay(totalPnl)));
                    expect(positions(entry.pnl.candle.points), label).toEqual(closings);
                    // The candle-less week keeps its slot as a gap; it never shifts a later candle.
                    expect(
                        entry.pnl.candle.points.map((point) => point.close),
                        label,
                    ).toEqual(closings.map((date) => candles.get(date)?.close ?? null));
                    expect(
                        entry.pnl.brokers.map((broker) => broker.brokerName),
                        label,
                    ).toEqual(['Broker A', 'Broker B']);
                    entry.pnl.brokers.forEach((broker, index) => {
                        expect(positions(broker.metric.points), `${label}: ${broker.brokerName}`).toEqual(closings);
                        expect(broker.metric.values, `${label}: ${broker.brokerName}`).toEqual(closings.map(onDay([brokerA, brokerB][index])));
                    });
                }
            });

            it('keeps candlestick quads 1:1 by array position with dates — a gap at one position never shifts a later one', () => {
                // Why (re-pin, S10, D21a): the per-broker overlay was removed from the candles submode
                // (developer review 2026-09-21: total candle only; last caller of toPositionalValue gone
                // in e7773a143), so only the candle's positional contract is left to prove.
                const dates = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'];
                // Distinct sentinel OHLC per position so any transposition/shift is caught. The
                // candle is missing (a genuine gap) at position 2.
                const candles: Array<{open: number; high: number; low: number; close: number} | null> = [{open: 10, close: 11, low: 9, high: 12}, {open: 20, close: 22, low: 19, high: 23}, null, {open: 40, close: 38, low: 37, high: 41}, {open: 50, close: 55, low: 49, high: 56}];

                const candlePoints = dates.map((d, i) => candlePoint(d, candles[i]));

                const candleSeries = candlePoints.map(toCandlestickPoint);

                expect(candleSeries).toHaveLength(dates.length);

                dates.forEach((_date, i) => {
                    const ohlc = candles[i];
                    if (ohlc == null) {
                        expect(candleSeries[i]).toBe(ECHARTS_EMPTY_VALUE);
                    } else {
                        expect(candleSeries[i]).toEqual(buildOhlcQuad(ohlc.open, ohlc.close, ohlc.low, ohlc.high, false, 1));
                    }
                });

                // The gap stays at its own position — if the mapping ever filtered instead of
                // preserving position (the exact off-by-one risk this fix calls out), every
                // candle after it would desync from `dates`.
                expect(candleSeries[2]).toBe(ECHARTS_EMPTY_VALUE);
                expect(candleSeries[1]).not.toBe(ECHARTS_EMPTY_VALUE);
            });

            // Why (FE6a): the candles half of the old buildChartUpdateSeries/buildFullSeries source pin
            // (`return [candleSeries];`, the `candles` map through toCandlestickPoint), now asserted on what
            // buildGrowthUpdateSeries and buildGrowthFullSeries return. The fixture sits on the 1W ladder,
            // where the candles are drawn: a week cut at its start (partial, with candles), a whole one,
            // and one cut at its end without a candle (partial AND a gap) — every branch of the mapping.
            // Two brokers ride along, so "no broker spread" is a claim about data that is there.
            const candleDates = isoDays('2026-01-07', 15); // Wed 01-07 … Wed 01-21
            const candleInputs = growthInputs(candleDates, {
                pnlCandleByDate: new Map<string, DailyCandle>(candleDates.slice(0, 12).map((date, index): [string, DailyCandle] => [date, {open: 100 + index, high: 110 + index, low: 90 + index, close: 105 + index}])),
                pnlBrokerSeriesRaw: [
                    {brokerId: 1, brokerName: 'Broker A', values: candleDates.map(() => 1)},
                    {brokerId: 2, brokerName: 'Broker B', values: candleDates.map(() => 2)},
                ],
            });
            const candleEntry = buildLadderData(candleInputs, '1W', '2026-02-15');

            it('builds the candles submode as the total candle ALONE — no broker spread — each quad on its own bucket, faded on a partial bucket, the bare sentinel on a gap', () => {
                // Positive controls: the fixture holds every case the mapping distinguishes.
                expect(candleEntry.buckets.map((bucket) => Boolean(bucket.partial))).toEqual([true, false, true]);
                expect(candleEntry.pnl.brokers).toHaveLength(2);
                const quads = candleEntry.pnl.candle.points.map(toCandlestickPoint);
                expect(quads.map((quad) => quad === ECHARTS_EMPTY_VALUE)).toEqual([false, false, true]);

                const update = buildGrowthUpdateSeries(pnlContext('candles', candleInputs), candleEntry);

                expect(update).toHaveLength(1);
                expect(update[0].name).toBe(PNL_LABELS.total);
                // A partial bucket's quad travels as `{value, itemStyle}`, the item form ECharts reads through
                // `isArray(item.value)`; a whole bucket's quad is bare; a gap stays the bare sentinel even on
                // a partial bucket, where wrapping it would hand ECharts an item with no quad inside.
                expect(update[0].data).toEqual([{value: quads[0], itemStyle: {opacity: PARTIAL_BUCKET_OPACITY}}, quads[1], ECHARTS_EMPTY_VALUE]);
            });

            it('draws the candles slot as the one candlestick, from seriesData[0], green up and red down in both themes', () => {
                const context = pnlContext('candles', candleInputs);
                const update = buildGrowthUpdateSeries(context, candleEntry);

                for (const isDark of [false, true]) {
                    const gain = themed(CHART_GAIN_LOSS.portfolio.gain, isDark);
                    const loss = themed(CHART_GAIN_LOSS.portfolio.loss, isDark);
                    const full = drawn(buildGrowthFullSeries(context, isDark, update));

                    expect(full).toHaveLength(1);
                    expect(full[0]).toMatchObject({name: PNL_LABELS.total, type: 'candlestick', itemStyle: {color: gain, color0: loss, borderColor: gain, borderColor0: loss}});
                    expect(full[0].data).toBe(update[0].data);
                }
            });

            // ---------------------------------------------------------------
            // Real-ECharts regression guard for the shipped crash.
            //
            // Every assertion above this point inspects VALUES and SOURCE TEXT, and all
            // of them stayed green while the chart was crashing in the browser — because
            // the defect only manifests when real ECharts initialises a candlestick
            // series on a category base axis. That is the gap that let this reach a
            // developer, so these tests drive the real library instead.
            //
            // Headless via SSR mode (`init(null, null, {renderer: 'svg', ssr: true})`):
            // no DOM, no browser, ~10ms. The canvas renderer cannot be used here — its
            // painter dereferences the (null) root — which is why `renderer: 'svg'` is
            // load-bearing and not incidental.
            // ---------------------------------------------------------------
            describe('real ECharts: a candlestick gap on a category axis must not kill the chart instance', () => {
                // Why (re-pin, S10, D21a): the per-broker overlay was removed from the candles submode
                // (developer review 2026-09-21: total candle only), so the guard drives ECharts with the
                // candlestick alone — and the CONTROL below still proves that a null gap kills it.
                /** The candles submode's real shape: the total candlestick alone over a category
                 *  base axis, exactly as buildGrowthFullSeries emits it (one series, proven by
                 *  «draws the candles slot as the one candlestick» above). */
                function candlesSubmodeOption(candleData: Array<number[] | string | null>) {
                    return {
                        xAxis: {type: 'category' as const, data: ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05']},
                        yAxis: {type: 'value' as const},
                        series: [{name: 'Total P&L', type: 'candlestick' as const, data: candleData}],
                    };
                }

                function withSsrChart<T>(run: (chart: ReturnType<typeof echarts.init>) => T): T {
                    const chart = echarts.init(null, null, {renderer: 'svg', ssr: true, width: 400, height: 300});
                    try {
                        return run(chart);
                    } finally {
                        chart.dispose();
                    }
                }

                // The gap values actually produced by the product's own helper, so this
                // guard is wired to the real mapping rather than to a hand-written '-'.
                const dates = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'];
                const ohlcByPosition: Array<{open: number; high: number; low: number; close: number} | null> = [{open: 10, close: 11, low: 9, high: 12}, null, {open: 30, close: 28, low: 27, high: 31}, null, {open: 50, close: 55, low: 49, high: 56}];
                const realCandleData = dates.map((d, i) => toCandlestickPoint(candlePoint(d, ohlcByPosition[i])));

                it("drives ECharts with the sentinel the real toCandlestickPoint returns — the exported ECHARTS_EMPTY_VALUE, ECharts' documented '-'", () => {
                    // Why (FE6a): this guard used to feed a reimplementation, and the link to the product
                    // was a regex reading `const ECHARTS_EMPTY_VALUE = '-'` out of GrowthChart.svelte.
                    // toCandlestickPoint and the constant are exports of growthChartSeries.ts now, so the
                    // fixture above IS the product's mapping: a regression to `return null` reaches the
                    // CONTROL and the guards below directly. What closes the loop is that each gap this
                    // block hands ECharts is the product's constant, and the constant is ECharts' own.
                    expect(ECHARTS_EMPTY_VALUE).toBe('-');
                    expect(realCandleData.map((value) => value === ECHARTS_EMPTY_VALUE)).toEqual([false, true, false, true, false]);
                    expect(realCandleData).not.toContain(null);
                });

                it('CONTROL: a null gap genuinely throws inside SeriesModel.init AND leaves the instance dead — without this, the guard below could pass for the wrong reason', () => {
                    // This is the shipped defect, reproduced end to end. If a future
                    // ECharts upgrade makes null tolerable, THIS test goes red first and
                    // tells us the guard below has stopped guarding anything.
                    const withNullGap = realCandleData.map((value) => (value === ECHARTS_EMPTY_VALUE ? null : value));

                    withSsrChart((chart) => {
                        expect(() => chart.setOption(candlesSubmodeOption(withNullGap))).toThrow(/Cannot read properties of null/);

                        // The throw is only the first symptom. The real damage is that it
                        // happened before GlobalModel finished building, so the instance is
                        // left with NO registered series — which is why every later
                        // setOption silently no-oped while the previous submode's canvas
                        // stayed on screen and looked like a freeze.
                        expect(chart.getOption().series).toEqual([]);
                    });
                });

                it("initialises cleanly with the helper's '-' sentinel, and the instance is left fully alive", () => {
                    withSsrChart((chart) => {
                        expect(() => chart.setOption(candlesSubmodeOption(realCandleData))).not.toThrow();

                        // The exact inverse of the control's `series === []`: the candlestick
                        // registered and addressable BY INDEX, which is the lookup
                        // (getSeriesByIndex) that produced ~22 console errors on mouse-move.
                        // Why (re-pin, S10, D21a): one series, not two — the fixture above now has the
                        // candles submode's real shape, the total candle without a broker overlay.
                        const registered = chart.getOption().series as Array<{name?: string}>;
                        expect(registered).toHaveLength(1);
                        expect(registered.map((s) => s.name)).toEqual(['Total P&L']);
                        expect(chart.convertToPixel({seriesIndex: 0}, [0, 2])).toBeDefined();
                        expect(chart.renderToSVGString().length).toBeGreaterThan(0);
                    });
                });

                it('stays alive across a SECOND setOption — the symptom the developer saw was a dead model repainting nothing', () => {
                    withSsrChart((chart) => {
                        chart.setOption(candlesSubmodeOption(realCandleData));
                        // A zoom/pan or submode switch issues further setOption calls; on a
                        // half-built model these are the ones that silently do nothing.
                        expect(() => chart.setOption({series: [{name: 'Total P&L', type: 'candlestick', data: realCandleData}]})).not.toThrow();
                        expect(chart.getOption().series).not.toEqual([]);
                        expect(chart.renderToSVGString().length).toBeGreaterThan(0);
                    });
                });

                it('keeps the gap OCCUPYING its slot: a category axis aligns by position, so 5 dates must still yield 5 items', () => {
                    // Omitting the gap instead of sentinelling it would render without
                    // throwing — and silently shift every later candle one day earlier.
                    expect(realCandleData).toHaveLength(dates.length);
                    expect(realCandleData.filter((v) => v === ECHARTS_EMPTY_VALUE)).toHaveLength(2);

                    withSsrChart((chart) => {
                        chart.setOption(candlesSubmodeOption(realCandleData));
                        const registered = chart.getOption().series as Array<{data?: unknown[]}>;
                        expect(registered[0].data).toHaveLength(dates.length);
                    });
                });

                it('excludes the reference-series sentinel from the legend while keeping the two Total P&L halves as ONE entry', () => {
                    // The other half of this fix: with no explicit legend.data, ECharts
                    // derives entries from every series name and leaked '__pnlReference__'
                    // into the UI. Dedupe is equally load-bearing — the positive/negative
                    // halves deliberately share one name and must toggle together.
                    // Why (FE6a): the sentinel is the product's export now, not a local copy of its value;
                    // the legend expression below is the component's, pinned in the line-submode block.
                    const series = [
                        {name: 'Total P&L', type: 'line' as const, data: [1, 2, 3]},
                        {name: 'Total P&L', type: 'line' as const, data: [null, null, null]},
                        {name: PNL_REFERENCE_SERIES_NAME, type: 'line' as const, data: [2, 2, 2]},
                        {name: 'Broker A', type: 'line' as const, data: [5, 6, 7]},
                    ];
                    const legendData = [...new Set(series.map((s) => s.name).filter((n): n is string => typeof n === 'string' && n !== PNL_REFERENCE_SERIES_NAME))];

                    expect(legendData).toEqual(['Total P&L', 'Broker A']);

                    withSsrChart((chart) => {
                        chart.setOption({
                            xAxis: {type: 'category' as const, data: ['a', 'b', 'c']},
                            yAxis: {type: 'value' as const},
                            legend: {data: legendData},
                            series,
                        });
                        const renderedLegend = chart.getOption().legend as Array<{data?: unknown[]}>;
                        expect(renderedLegend[0].data).toEqual(['Total P&L', 'Broker A']);
                        expect(chart.renderToSVGString()).not.toContain(PNL_REFERENCE_SERIES_NAME);
                    });
                });
            });
        });

        describe('line-submode fixed 3-slot P&L split (positive / negative / reference)', () => {
            // Why (FE6a): the old buildChartUpdateSeries/buildFullSeries source pin is now asserted on what
            // buildGrowthUpdateSeries and buildGrowthFullSeries return (their candles half lives in the
            // candles block above). Five days of a Total P&L that crosses zero twice, two brokers under it.
            const lineDates = isoDays('2026-01-05', 5);
            const lineInputs = growthInputs(lineDates, {
                totalPnl: [30, -10, -20, 15, 25],
                pnlBrokerSeriesRaw: [
                    {brokerId: 1, brokerName: 'Broker A', values: [10, -5, -10, 5, 10]},
                    {brokerId: 2, brokerName: 'Broker B', values: [20, -5, -10, 10, 15]},
                ],
            });
            const lineEntry = buildResolutionData(lineInputs, 'daily');

            it('builds the Line submode as 3 fixed slots — positive half, negative half, the flat reference — then the variable broker spread, in that order', () => {
                const update = buildGrowthUpdateSeries(pnlContext('line', lineInputs), lineEntry, '2026-01-06');

                expect(update.map((series) => series.name)).toEqual([PNL_LABELS.total, PNL_LABELS.total, PNL_REFERENCE_SERIES_NAME, 'Broker A', 'Broker B']);
                // The two halves come from ONE splitBySign call: the zero crossings it interpolates are in
                // them (so each half outgrows the source), which two plain clipToSign maps could not do.
                const {positive, negative} = splitBySign(lineEntry.pnl.total.points);
                expect(update[0].data).toEqual(positive);
                expect(update[1].data).toEqual(negative);
                expect(update[0].data.length).toBeGreaterThan(lineEntry.pnl.total.points.length);
                // The reference is flat at the Total P&L of the reference day (01-06: −10), on the total's
                // own positions — one point per source day, no crossing among them.
                expect(update[2].data.map((point) => point.value)).toEqual(lineEntry.pnl.total.points.map((point) => [point.value[0], -10]));
                // Each broker slot carries its own aggregated line.
                expect(update[3].data).toBe(lineEntry.pnl.brokers[0].metric.points);
                expect(update[4].data).toBe(lineEntry.pnl.brokers[1].metric.points);

                // The spread is the only variable part: without brokers, the three fixed slots stand alone.
                const totalOnly = growthInputs(lineDates, {totalPnl: [30, -10, -20, 15, 25]});
                expect(buildGrowthUpdateSeries(pnlContext('line', totalOnly), buildResolutionData(totalOnly, 'daily'), '2026-01-06').map((series) => series.name)).toEqual([PNL_LABELS.total, PNL_LABELS.total, PNL_REFERENCE_SERIES_NAME]);
            });

            it('draws each Line slot from the seriesData at its own index — green and red halves, the dashed silent reference, a dashed palette line per broker — in both themes', () => {
                const context = pnlContext('line', lineInputs);
                const update = buildGrowthUpdateSeries(context, lineEntry, '2026-01-06');

                for (const isDark of [false, true]) {
                    const gain = themed(CHART_GAIN_LOSS.portfolio.gain, isDark);
                    const loss = themed(CHART_GAIN_LOSS.portfolio.loss, isDark);
                    const full = drawn(buildGrowthFullSeries(context, isDark, update));

                    expect(full.map((series) => series.name)).toEqual(update.map((series) => series.name));
                    // Slot N draws seriesData[N]: brokers from index 3, matching the 3 fixed slots exactly
                    // (not slice(1) or slice(2)) — not off by one, not transposed.
                    full.forEach((series, index) => expect(series.data).toBe(update[index].data));
                    expect(full[0]).toMatchObject({type: 'line', smooth: false, connectNulls: false, lineStyle: {color: gain}, itemStyle: {color: gain}, areaStyle: {color: gain}});
                    expect(full[1]).toMatchObject({type: 'line', smooth: false, connectNulls: false, lineStyle: {color: loss}, itemStyle: {color: loss}, areaStyle: {color: loss}});
                    expect(full[2]).toMatchObject({name: PNL_REFERENCE_SERIES_NAME, type: 'line', lineStyle: {color: chartNeutrals(isDark).growth.pnlReference, type: 'dashed'}, tooltip: {show: false}, silent: true});
                    expect(full.slice(3).map((series) => series.lineStyle)).toEqual([0, 1].map((index) => ({color: brokerColor(index, isDark), width: 1.5, type: 'dashed'})));
                }
            });

            it('names the reference slot with ONE shared constant at every site — both builders, and the legend exclusion of GrowthChart.svelte, by import', () => {
                // The reference series' name is a shared module-level constant, not an inline literal:
                // three sites must agree on it (both construction sites AND applyFullOption's legend
                // exclusion), and a magic string repeated three times is how the sentinel leaked into the
                // legend in the first place. Why (FE6a): the constant and the two builders moved to
                // growthChartSeries.ts (the slot tests above use them); the legend stayed in the
                // component, which must reach the sentinel through the same import and never by value.
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');

                expect(PNL_REFERENCE_SERIES_NAME).toBe('__pnlReference__');
                expect(source).toMatch(/import \{[^}]*\bPNL_REFERENCE_SERIES_NAME\b[^}]*\} from '\.\/growthChartSeries';/);
                expect(source).toContain("data: [...new Set(series.map((s) => s.name).filter((n): n is string => typeof n === 'string' && n !== PNL_REFERENCE_SERIES_NAME))],");
                expect(source).not.toContain("'__pnlReference__'");
            });

            // Why (re-pin, S10, D21b): e7773a143 splits the Total P&L with splitBySign, which
            // inserts the interpolated zero crossing into both halves (the developer's report: the
            // area vanished at a sign change). The old claim — each half as long as the source —
            // described two plain clipToSign maps and is false for the product. What stays fixed
            // is the series COUNT (pinned in the slot test above); the points inside the halves
            // are not.
            // D22 (developer, 2026-09-25): two rows added for the zero guard and the interpolation
            // weight, and the reference-line assertions removed: the test built that line itself,
            // so they could not fail. Its flatness is pinned by the slot-test literals and its
            // value by describe('findReferenceTotalPnl').
            //
            // Third column: the instants at which each row must gain a crossing, in order, written
            // by hand rather than computed with the rule under test. The dates are UTC midnights
            // (index i is day i + 1), so a crossing between equal magnitudes sits at noon. Only two
            // neighbours that are both non-null, non-zero and of opposite sign get one, so a pair
            // touching a gap or a zero gets none (in the gapped row only 20 → −20 qualifies).
            // [5, 0, −5] is there for the zero guard: every other zero sits next to a negative value
            // or a gap, which the sign test or the gap guard already skips (0 > 0 is false), whereas
            // 5 → 0 passes the sign test and, without the guard, would get t = 1 — a crossing at the
            // zero's own instant. [30, −10] is there for the interpolation weight, which no
            // equal-magnitude row can tell apart: both ends give noon there, but 30 → −10 reaches
            // zero three quarters of the way, at 18:00, and the wrong-end weight would give 06:00.
            const signCrossingScenarios: Array<[string, Array<number | null>, string[]]> = [
                ['all positive', [10, 20, 30], []],
                ['all negative', [-10, -20, -30], []],
                ['even number of sign crossings', [5, -5, 5, -5, 5], ['2026-01-01T12:00:00.000Z', '2026-01-02T12:00:00.000Z', '2026-01-03T12:00:00.000Z', '2026-01-04T12:00:00.000Z']],
                ['odd number of sign crossings', [5, -5, 5, -5], ['2026-01-01T12:00:00.000Z', '2026-01-02T12:00:00.000Z', '2026-01-03T12:00:00.000Z']],
                ['many crossings interleaved with gaps', [10, null, -10, 0, -5, null, 20, -20, 0], ['2026-01-07T12:00:00.000Z']],
                ['a zero between a positive and a negative value', [5, 0, -5], []],
                ['a single point', [42], []],
                ['a crossing between unequal magnitudes', [30, -10], ['2026-01-01T18:00:00.000Z']],
            ];

            it.each(signCrossingScenarios)('splits %s into ONE positive and ONE negative half: every source point in exactly one half (a gap null in both), the zero crossing inserted into BOTH between opposite-sign neighbours, nothing invented at a gap or a zero', (_label, values, crossings) => {
                const dates = values.map((_v, i) => `2026-01-${String(i + 1).padStart(2, '0')}`);
                const points = dates.map((d, i) => seriesPoint(d, values[i]));

                // Why (FE6a): the real splitBySign (growthChartSeries.ts), no longer a copy of it.
                const {positive, negative} = splitBySign(points);

                // One point more per crossing, the same number in both halves.
                expect(positive).toHaveLength(values.length + crossings.length);
                expect(negative).toHaveLength(positive.length);

                // A crossing is recognisable without the rule under test: every source date is a
                // bare day, and a crossing carries an instant that is none of them.
                const sourceDates = new Set(dates);
                const isCrossing = (p: SeriesPoint) => !sourceDates.has(p.value[0]);

                // The crossings are exactly the third column's hand-written instants, in order.
                expect(positive.filter(isCrossing).map((p) => p.value[0])).toEqual(crossings);

                const positiveSource = positive.filter((p) => !isCrossing(p));
                const negativeSource = negative.filter((p) => !isCrossing(p));

                // With the crossings taken out, each half is the plain clipToSign map, in order...
                expect(positiveSource).toEqual(points.map((p) => clipToSign(p, true)));
                expect(negativeSource).toEqual(points.map((p) => clipToSign(p, false)));

                // ...so a non-null value survives in EXACTLY one half, and a null value stays null
                // in BOTH (a genuine gap, never fabricated into a zero).
                values.forEach((v, i) => {
                    if (v == null) {
                        expect(positiveSource[i].value[1]).toBeNull();
                        expect(negativeSource[i].value[1]).toBeNull();
                    } else if (v >= 0) {
                        expect(positiveSource[i].value[1]).toBe(v);
                        expect(negativeSource[i].value[1]).toBeNull();
                    } else {
                        expect(positiveSource[i].value[1]).toBeNull();
                        expect(negativeSource[i].value[1]).toBe(v);
                    }
                });

                // Each crossing: value 0; the same point at the same index in both halves; right
                // after its left neighbour and right before its right one (never at either end,
                // never two in a row); only between two non-null, non-zero values of opposite
                // sign; strictly between their dates. Its exact instant is the third column's,
                // asserted above.
                const sourceSlots = positive.flatMap((p, k) => (isCrossing(p) ? [] : [k]));
                positive.forEach((p, k) => {
                    if (!isCrossing(p)) return;
                    const left = sourceSlots.indexOf(k - 1);
                    expect(left).toBeGreaterThanOrEqual(0);
                    expect(sourceSlots[left + 1]).toBe(k + 1);

                    expect(p.value[1]).toBe(0);
                    expect(negative[k]).toEqual(p);
                    expect(Math.sign(values[left] ?? 0) * Math.sign(values[left + 1] ?? 0)).toBe(-1);

                    const leftMs = new Date(dates[left]).getTime();
                    const rightMs = new Date(dates[left + 1]).getTime();
                    const crossingMs = new Date(p.value[0]).getTime();
                    expect(crossingMs).toBeGreaterThan(leftMs);
                    expect(crossingMs).toBeLessThan(rightMs);
                });
            });
        });

        // ===================================================================
        // Income submode (G1c dividend/interest + batch 2 costs/deposit/acquisition)
        // ===================================================================
        //
        // Why (FE6a): this block pinned the pure source *shape* (which slot holds what, which
        // stack it joins) by reading GrowthChart.svelte, and ran faithful copies of the
        // component-local *logic* (the sparse alignments, aggregateFlowMetric, the tooltip's
        // conditional section) tied back to the source text by contract tests. All of it moved
        // to growthChartData.ts, growthChartSeries.ts and growthChartTooltip.ts as exports, so
        // the shape is asserted on what the real builders return and the logic runs as it
        // ships. What stayed in the component — the six alignments' wiring — keeps its pin.

        // Why (re-pin, S8): R11 names both acquisition slots after the purchase value
        // (pnlLabels.bookValue, the KPI card's key), so slots 4-5 now share one label. The
        // block still pins the fixed 6-slot order, new capital before reinvested, the path
        // each slot reads and the stack it joins.
        describe('income-submode fixed 6-slot order (dividend / interest / costs / deposit / bookValue: new capital, then reinvested)', () => {
            interface IncomeSlot {
                label: string;
                /** The AggregatedResolutionData path the slot's data comes from. */
                metric: (entry: AggregatedResolutionData) => AggregatedMetric;
                stack: 'income' | 'acquisition' | undefined;
                /** The GROWTH_SERIES key of its colour. */
                colour: keyof typeof GROWTH_SERIES;
            }

            // The single source of truth this whole describe block defends: slot index ->
            // (label, the AggregatedResolutionData path its data comes from, its stack group, its colour).
            const EXPECTED_SLOTS: IncomeSlot[] = [
                {label: PNL_LABELS.dividend, metric: (entry) => entry.pnl.income.dividend, stack: 'income', colour: 'dividend'},
                {label: PNL_LABELS.interest, metric: (entry) => entry.pnl.income.interest, stack: 'income', colour: 'interest'},
                // Why (re-pin, S7): costs moved into the income stack (item 6). They are signed
                // negative and a same-sign stack splits by sign, so they hang below dividends and
                // interest in the same column. The expectation still pins, slot by slot, the label
                // order the full builder reads seriesData[0..5] in and the stack each slot joins.
                {label: PNL_LABELS.costs, metric: (entry) => entry.pnl.costs, stack: 'income', colour: 'costs'},
                {label: PNL_LABELS.deposit, metric: (entry) => entry.pnl.deposits, stack: undefined, colour: 'deposit'},
                // Why (re-pin, S8): R11 (D2 = A) gives both acquisition halves the shared
                // purchase-value name, pnlLabels.bookValue, so the legend shows it once. The
                // slots still pin new capital at 4 and reinvested at 5, each on its own data
                // path, both in the 'acquisition' stack: a swap still turns both tests red.
                // D26 paints new capital in the KPI blue of the Abs purchase-cost series
                // (bookAssetLike, the sage cashContributed before S8) and reinvested in the Abs
                // returns colour (cashGenerated).
                {label: PNL_LABELS.bookValue, metric: (entry) => entry.pnl.acquisition.fromNewCapital, stack: 'acquisition', colour: 'bookAssetLike'},
                {label: PNL_LABELS.bookValue, metric: (entry) => entry.pnl.acquisition.fromReinvested, stack: 'acquisition', colour: 'cashGenerated'},
            ];

            // Two weeks on the 1W ladder, where Income is drawn: the first cut at its start (partial,
            // faded), the second whole. Every dimension carries its own amounts — ×1 … ×6 the day
            // number, costs negative — so a slot reading a sibling's path cannot pass for its own; two
            // brokers ride along, so "no broker spread" is a claim about data that is there.
            const incomeDates = isoDays('2026-01-07', 12); // Wed 01-07 … Sun 01-18
            const flow = (factor: number) => incomeDates.map((_, index) => factor * (index + 1));
            const incomeInputs = growthInputs(incomeDates, {
                dividendValues: flow(1),
                interestValues: flow(2),
                costValues: flow(-3),
                depositValues: flow(4),
                acqFromNewCapitalValues: flow(5),
                acqFromReinvestedValues: flow(6),
                pnlBrokerSeriesRaw: [
                    {brokerId: 1, brokerName: 'Broker A', values: incomeDates.map(() => 1)},
                    {brokerId: 2, brokerName: 'Broker B', values: incomeDates.map(() => 2)},
                ],
            });
            const incomeEntry = buildLadderData(incomeInputs, '1W', '2026-02-15');
            const incomeContext = pnlContext('income', incomeInputs);

            it('emits exactly the 6 expected slots, in order, each reading its own AggregatedResolutionData path', () => {
                // Positive controls: the six paths differ in every bucket, and the first bucket is partial.
                expect(new Set(EXPECTED_SLOTS.map((slot) => slot.metric(incomeEntry).values.join('|'))).size).toBe(6);
                expect(incomeEntry.buckets.map((bucket) => Boolean(bucket.partial))).toEqual([true, false]);

                const update = buildGrowthUpdateSeries(incomeContext, incomeEntry);

                expect(update.map((series) => series.name)).toEqual(EXPECTED_SLOTS.map((slot) => slot.label));
                update.forEach((series, index) => {
                    // Its own path's sums, bucket by bucket, on its own positions...
                    expect(series.data.map((point) => point.value)).toEqual(EXPECTED_SLOTS[index].metric(incomeEntry).points.map((point) => point.value));
                    // Why (re-pin, S7): ...and the partial first bucket faded on every income column
                    // alike (item 4), the whole one left as it is.
                    expect(series.data.map((point) => point.itemStyle)).toEqual([{opacity: PARTIAL_BUCKET_OPACITY}, undefined]);
                });
            });

            it('buildGrowthFullSeries consumes seriesData[0..5] in exactly the same label order — a swap here would silently draw two bars with each other data', () => {
                const update = buildGrowthUpdateSeries(incomeContext, incomeEntry);
                const full = drawn(buildGrowthFullSeries(incomeContext, false, update));

                expect(full).toHaveLength(6);
                // (a) same labels, same order as buildGrowthUpdateSeries emits them, and
                // (b) slot N is drawn from seriesData[N] — not off-by-one, not transposed.
                expect(full.map((series) => series.name)).toEqual(EXPECTED_SLOTS.map((slot) => slot.label));
                full.forEach((series, index) => expect(series.data).toBe(update[index].data));
                expect(full.map((series) => series.type)).toEqual(EXPECTED_SLOTS.map(() => 'bar'));
                expect(full.map((series) => series.stack)).toEqual(EXPECTED_SLOTS.map((slot) => slot.stack));
            });

            it('never spreads broker overlays into the income submode — the slot count is fixed at 6, unlike line', () => {
                // Why (re-pin, S10, D21a): candles no longer spreads broker overlays either (total candle only, developer review 2026-09-21), so line is the only submode left to contrast with.
                // Positive control: the entry does carry two brokers.
                expect(incomeEntry.pnl.brokers.map((broker) => broker.brokerName)).toEqual(['Broker A', 'Broker B']);

                const update = buildGrowthUpdateSeries(incomeContext, incomeEntry);
                expect(update.map((series) => series.name)).toEqual(EXPECTED_SLOTS.map((slot) => slot.label));
                // The full builder draws six bars even when handed more data than that: it never
                // slices a spread out of seriesData.
                const withStray = [...update, {name: 'Broker A', data: incomeEntry.pnl.brokers[0].metric.points}];
                expect(drawn(buildGrowthFullSeries(incomeContext, false, withStray)).map((series) => series.name)).toEqual(EXPECTED_SLOTS.map((slot) => slot.label));
                // The contrast: the same entry under the line submode gains one slot per broker.
                expect(buildGrowthUpdateSeries(pnlContext('line', incomeInputs), incomeEntry)).toHaveLength(3 + 2);
            });

            it('paints the two acquisition zones in the Abs view colours: new capital in the KPI blue of the purchase cost, reinvested in the returns colour', () => {
                // Why (re-pin, S7/S8): the pin is one colour per zone, tied to the seriesData index it
                // paints, so a swap or an invented colour turns it red — now read off the drawn series,
                // in both themes, with every other slot's colour checked as well.
                const update = buildGrowthUpdateSeries(incomeContext, incomeEntry);

                for (const isDark of [false, true]) {
                    const theme = isDark ? 'dark' : 'light';
                    const colours = drawn(buildGrowthFullSeries(incomeContext, isDark, update)).map((series) => series.itemStyle?.color);

                    expect(colours[4]).toBe(GROWTH_SERIES.bookAssetLike[theme]);
                    expect(colours[5]).toBe(GROWTH_SERIES.cashGenerated[theme]);
                    expect(colours).not.toContain(GROWTH_SERIES.cashContributed[theme]);
                    expect(colours).toEqual(EXPECTED_SLOTS.map((slot) => GROWTH_SERIES[slot.colour][theme]));
                }
            });

            it('sums all six aggregated dimensions per bucket — in the density cascade and in the ladder alike — never end-of-period', () => {
                // If one of these went through aggregateMetric (end-of-period) instead, a
                // weekly/monthly bar would silently show only the last day of the bucket.
                // Why (FE6a): buildResolutionData (aggregateFlowMetric) and buildLadderData
                // (ladderFlowMetric) are exports now, so the six calls are proven by their result
                // instead of their text. Each week closes on a day holding less than its sum (1 of 46,
                // 2 of 9), so an end-of-period reading cannot pass for one.
                const days = isoDays('2026-01-05', 14); // two ISO weeks, Mon 01-05 … Sun 01-18
                const pattern = [0, 40, 0, 0, 5, 0, 1, 0, 0, 7, 0, 0, 0, 2];
                const factors = [1, 2, -3, 4, 5, 6];
                const scaled = (factor: number) => pattern.map((value) => factor * value);
                const inputs = growthInputs(days, {dividendValues: scaled(1), interestValues: scaled(2), costValues: scaled(-3), depositValues: scaled(4), acqFromNewCapitalValues: scaled(5), acqFromReinvestedValues: scaled(6)});
                const sums = (entry: AggregatedResolutionData) => EXPECTED_SLOTS.map((slot) => slot.metric(entry).values);

                for (const entry of [buildResolutionData(inputs, 'weekly'), buildLadderData(inputs, '1W', '2026-01-18')]) {
                    expect(sums(entry)).toEqual(factors.map((factor) => [46 * factor, 9 * factor]));
                }
                for (const entry of [buildResolutionData(inputs, 'monthly'), buildLadderData(inputs, '1M', '2026-01-18')]) {
                    expect(sums(entry)).toEqual(factors.map((factor) => [55 * factor]));
                }
            });
        });

        // -------------------------------------------------------------------
        // The Income submode's own data pipeline: sparse API series -> `dates`-aligned
        // values -> aggregateFlowMetric -> aggregateSumSeries. Predates batch 2 (it is
        // how dividend/interest have always reached the chart) and had no coverage
        // anywhere; batch 2's four new dimensions reuse it unchanged, so it is now
        // load-bearing for six series instead of two.
        //
        // Why (FE6a): the six `$derived` bodies are one export now, alignFlowToDates, and
        // aggregateFlowMetric is exported beside it (growthChartData.ts). The copies that
        // stood here are gone: every case below runs the real function.
        // -------------------------------------------------------------------
        describe('income-submode data pipeline: sparse series alignment and flow aggregation', () => {
            /** A sparse API point reduced to what alignment reads: its day and its amount. */
            interface FlowPoint {
                date: string;
                amount: number;
            }

            /** The real alignment, with the plainest amount accessor; the component passes one per Currency field. */
            const align = (dates: string[], points: FlowPoint[]) => alignFlowToDates(dates, points, (point: FlowPoint) => point.amount);

            const week = ['2026-01-05', '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09'];
            const dailyBuckets: BucketInfo[] = week.map((d) => ({date: d, bucketStart: d, bucketEnd: d, resolution: 'daily'}));
            // 2026-01-05..09 is one ISO week; aggregateSumSeries renders it at its last source date,
            // so the bucket list for weekly resolution is that single date.
            const weekBucket: BucketInfo = {date: '2026-01-09', bucketStart: '2026-01-05', bucketEnd: '2026-01-11', resolution: 'weekly'};

            it('a date absent from the sparse series becomes 0, never a gap — flows are zero, not unknown', () => {
                // The opposite of the candles submode, where an absent date is a genuine
                // null gap. "No dividend was paid on the 7th" is a known zero.
                expect(
                    align(week, [
                        {date: '2026-01-06', amount: 40},
                        {date: '2026-01-09', amount: 5},
                    ]),
                ).toEqual([0, 40, 0, 0, 5]);
            });

            it('an entirely absent series (prop undefined) aligns to all zeros of the right length', () => {
                expect(align(week, [])).toEqual([0, 0, 0, 0, 0]);
            });

            it('a point whose date is not in `dates` is dropped rather than shifting the alignment', () => {
                // A sparse API series can legitimately carry a date outside the chart's
                // current window; positional alignment must survive it.
                expect(
                    align(week, [
                        {date: '2025-12-31', amount: 999},
                        {date: '2026-01-07', amount: 3},
                    ]),
                ).toEqual([0, 0, 3, 0, 0]);
            });

            it('negative amounts survive alignment unchanged — costs are signed', () => {
                expect(align(week, [{date: '2026-01-05', amount: -12}])).toEqual([-12, 0, 0, 0, 0]);
            });

            it('aggregateFlowMetric at daily resolution is a pass-through, one point per bucket', () => {
                const values = [0, 40, 0, 0, 5];
                const result = aggregateFlowMetric(values, 'daily', dailyBuckets, week);

                expect(result.values).toEqual(values);
                expect(result.values).not.toBe(values); // copied, not aliased
                expect(result.points.map((p) => p.value)).toEqual(week.map((d, i) => [d, values[i]]));
            });

            it('aggregateFlowMetric SUMS a weekly bucket instead of taking its last day', () => {
                const result = aggregateFlowMetric([0, 40, 0, 0, 5], 'weekly', [weekBucket], week);

                expect(result.values).toEqual([45]); // 40 + 5, NOT 5
                expect(result.points[0].bucketStart).toBe('2026-01-05');
                expect(result.points[0].bucketEnd).toBe('2026-01-11');
            });

            it('aggregateFlowMetric fills a bucket with no aggregated match with 0, not null', () => {
                // aggregateMetric (the cumulative sibling) uses `?? null` here; the flow
                // variant uses `?? 0`. Mixing them up would put a null into a bar series.
                const weeklyBuckets: BucketInfo[] = [weekBucket, {date: '2026-01-16', bucketStart: '2026-01-12', bucketEnd: '2026-01-18', resolution: 'weekly'}];
                const result = aggregateFlowMetric([1, 1, 1, 1, 1], 'weekly', weeklyBuckets, week);

                expect(result.values).toEqual([5, 0]);
                expect(result.points[1].value[1]).toBe(0);
                expect(result.points[1].value[1]).not.toBeNull();
            });

            it('aggregateFlowMetric reads a day missing from its values as 0, never as a gap, at every resolution', () => {
                // Why (FE6a): the `values[index] ?? 0` of both paths, pinned as text while the function
                // was the component's, now as behaviour: a values array shorter than its days.
                expect(aggregateFlowMetric([7], 'daily', dailyBuckets.slice(0, 2), week.slice(0, 2)).points.map((p) => p.value[1])).toEqual([7, 0]);
                expect(aggregateFlowMetric([7], 'weekly', [weekBucket], week).values).toEqual([7]);
            });

            it('aggregateFlowMetric sums where its end-of-period sibling aggregateMetric reads the last day — the same week, two answers', () => {
                // Why (FE6a): the distinguishing line vs aggregateMetric (aggregateSumSeries, never
                // aggregateLineSeries) was pinned as text; this is the difference it makes.
                const values = [0, 40, 0, 0, 5];

                expect(aggregateFlowMetric(values, 'weekly', [weekBucket], week).values).toEqual([45]);
                expect(aggregateMetric(values, 'weekly', [weekBucket], week).values).toEqual([5]);
            });

            it("aggregateMetric keeps the last value a weekly bucket holds when the line stops mid-week, drawn on the bucket's own date — not a gap", () => {
                // Why (Y-2): a broker line that leaves the scope on Wednesday: values Mon–Wed, null Thu–Fri.
                // aggregateLineSeries dates the week on its last point with a value (Wed), the bucket stands on
                // the last day the history holds (Fri), and the lookup by bucket.date found nothing: a gap, where
                // the ladder's ladderLast keeps 30. The point stays on Friday, with every other series of the entry.
                const result = aggregateMetric([10, 20, 30, null, null], 'weekly', [weekBucket], week);

                expect(result.values).toEqual([30]);
                expect(result.points).toEqual([{name: '2026-01-09', value: ['2026-01-09', 30], bucketStart: '2026-01-05', bucketEnd: '2026-01-11', resolution: 'weekly'}]);
            });

            it('aggregateMetric leaves a week where the line has no value a gap — the last value of the week it left is never carried into the next', () => {
                // Why (Y-2): the other half. The value is the last one inside the SAME calendar week (bucketEnd),
                // so a week where the line has none stays a real gap: the 30 of the week it left is never carried
                // into the next one, as a lookup of the last value on or before bucket.date would do.
                const nextWeek = ['2026-01-12', '2026-01-13', '2026-01-14', '2026-01-15', '2026-01-16'];
                const nextWeekBucket: BucketInfo = {date: '2026-01-16', bucketStart: '2026-01-12', bucketEnd: '2026-01-18', resolution: 'weekly'};
                const result = aggregateMetric([10, 20, 30, null, null, ...nextWeek.map(() => null)], 'weekly', [weekBucket, nextWeekBucket], [...week, ...nextWeek]);

                expect(result.values).toEqual([30, null]);
                expect(result.points.map((point) => point.value)).toEqual([
                    ['2026-01-09', 30],
                    ['2026-01-16', null],
                ]);
            });

            it("aggregateMetric keeps the last value a monthly bucket holds when the line stops before the history's last day of the month", () => {
                // Why (Y-2): the same lookup serves the months. The bucket is the product's: buildResolutionData
                // builds it with growthChartData's buildBucketInfos (the one imported at the top is the lot chart's).
                // The history stops on the 28th, so the point stands on 01-28 and the month ends on 01-31 — neither
                // is the 20th, the line's last value.
                const days = isoDays('2026-01-01', 28); // Thu 01-01 … Wed 01-28: January, still running
                const reachesThe28th = days.map((_, index) => 100 + index);
                const leavesOnThe20th = days.map((_, index) => (index < 20 ? 100 + index : null));
                const {buckets} = buildResolutionData(growthInputs(days), 'monthly');
                // The precondition the case is about: one month, standing on a day after the line's last value.
                expect(buckets).toEqual([{date: '2026-01-28', bucketStart: '2026-01-01', bucketEnd: '2026-01-31', resolution: 'monthly'}]);
                // Positive control: a line that reaches the 28th reads it, so the bucket itself is sound.
                expect(aggregateMetric(reachesThe28th, 'monthly', buckets, days).values).toEqual([127]);

                const result = aggregateMetric(leavesOnThe20th, 'monthly', buckets, days);

                expect(result.values).toEqual([119]); // 01-20's value
                expect(result.points).toEqual([{name: '2026-01-28', value: ['2026-01-28', 119], bucketStart: '2026-01-01', bucketEnd: '2026-01-31', resolution: 'monthly'}]);
            });

            it('wires each of the six sparse $derived alignments in GrowthChart.svelte to its own prop and Currency field, through the one alignFlowToDates', () => {
                // Why (re-pin, FE6a): the six identical "absent date -> 0" bodies became one export,
                // alignFlowToDates, run for real above. What stayed in the component is the wiring —
                // which prop each dimension aligns and which Currency field it reads — pinned here.
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');

                const alignments: Array<[string, string, string]> = [
                    ['dividendValues', 'incomeHistory', 'p.dividend.amount'],
                    ['interestValues', 'incomeHistory', 'p.interest.amount'],
                    ['costValues', 'costHistory', 'p.cost.amount'],
                    ['depositValues', 'depositHistory', 'p.deposit.amount'],
                    ['acqFromNewCapitalValues', 'acquisitionFunding', 'p.from_new_capital.amount'],
                    ['acqFromReinvestedValues', 'acquisitionFunding', 'p.from_reinvested.amount'],
                ];
                for (const [name, prop, field] of alignments) {
                    expect(source).toContain(`const ${name} = $derived(alignFlowToDates(dates, ${prop}?.points ?? [], (p) => Number(${field})));`);
                }
                // ...and no seventh, hand-written copy of the body is left in the component.
                expect(source).not.toContain('byDate.get(d) ?? 0');
            });
        });

        describe('income-submode tooltip: the batch-2 section is conditional, the income block never is', () => {
            // Why (FE6a): the tooltip's income branch is buildGrowthTooltip's (growthChartTooltip.ts), so
            // the faithful copy that stood here, and the contract test that tied it to the component's
            // text, are gone: every case hovers the REAL tooltip. The six values reach it the way they
            // do on screen — a one-day 1D ladder entry built by buildLadderData — and its translator
            // returns the key, so nothing here reads a translation. A row is read back as its label,
            // its colour and the amount it prints.
            const THEME: TooltipTheme = {bg: '#tooltip-bg', border: '#tooltip-border', textColor: '#tooltip-text', mutedColor: '#tooltip-muted'};
            const DIVIDER = buildTooltipDivider(THEME.border);
            /** The income total's label: its key, through the stub translator. */
            const TOTAL = '<b>assets.distribution.total</b>';
            const DAY = '2026-01-07';

            interface IncomeTooltipValues {
                divVal: number;
                intVal: number;
                costVal: number;
                depositVal: number;
                acqNewVal: number;
                acqReinvestedVal: number;
            }

            /** The tooltip of the Income view hovered on a day holding these six values. */
            function incomeTooltip(values: IncomeTooltipValues, isDark = false, reshape: (entry: AggregatedResolutionData) => AggregatedResolutionData = (entry) => entry): string {
                // Precondition of every amount read below: the rows are printed in en-US.
                expect(uiLocale()).toBe('en-US');
                const inputs = growthInputs([DAY], {
                    dividendValues: [values.divVal],
                    interestValues: [values.intVal],
                    costValues: [values.costVal],
                    depositValues: [values.depositVal],
                    acqFromNewCapitalValues: [values.acqNewVal],
                    acqFromReinvestedValues: [values.acqReinvestedVal],
                });
                const view: GrowthTooltipView = {
                    entry: reshape(buildLadderData(inputs, '1D', DAY)),
                    viewMode: 'pnl',
                    pnlSubmode: 'income',
                    ladderActive: true,
                    candleWidthCaption: () => '1D',
                    eurLabels: EUR_LABELS,
                    pnlLabels: PNL_LABELS,
                    baseCurrency: 'EUR',
                    t: (key) => key,
                    isDark,
                    theme: THEME,
                };
                return buildGrowthTooltip([{dataIndex: 0}], view);
            }

            interface TooltipRow {
                label: string;
                colour: string;
                amount: number;
            }

            /** A signed amount row of the tooltip: `<div … color:C"><span>LABEL</span><b style="color:S">AMOUNT</b></div>`. */
            const ROW = /<div style="display:flex;justify-content:space-between;gap:16px;color:([^"]*)"><span>(.*?)<\/span><b style="color:[^"]*">([^<]*)<\/b><\/div>/g;

            /** `EUR +1,000.00` → 1000: the base currency, then the en-US digits. */
            function printedAmount(text: string): number {
                expect(text.startsWith('EUR ')).toBe(true);
                return Number(text.slice('EUR '.length).replaceAll(',', ''));
            }

            function rowsOf(html: string): TooltipRow[] {
                return [...html.matchAll(ROW)].map((match) => ({colour: match[1], label: match[2], amount: printedAmount(match[3])}));
            }

            function rowNamed(html: string, label: string): TooltipRow {
                const row = rowsOf(html).find((candidate) => candidate.label === label);
                expect(row, `tooltip row ${label}`).toBeDefined();
                if (!row) throw new Error(`Tooltip row ${label} not found`);
                return row;
            }

            const zeroDay: IncomeTooltipValues = {divVal: 0, intVal: 0, costVal: 0, depositVal: 0, acqNewVal: 0, acqReinvestedVal: 0};
            const allActive: IncomeTooltipValues = {divVal: 10, intVal: 2, costVal: -5, depositVal: 1000, acqNewVal: 300, acqReinvestedVal: 100};
            const rowLabels = (html: string) => rowsOf(html).map((row) => row.label);
            const dividerCount = (html: string) => html.split(DIVIDER).length - 1;

            it('an all-zero day renders ONLY dividend/interest/total — no divider, no empty trailing rows', () => {
                const html = incomeTooltip(zeroDay);

                expect(rowLabels(html)).toEqual(['dividend', 'interest', TOTAL]);
                expect(dividerCount(html)).toBe(1);
            });

            it('a day with income but no batch-2 activity still renders only the original block', () => {
                const html = incomeTooltip({...zeroDay, divVal: 42, intVal: 8});

                expect(rowLabels(html)).toEqual(['dividend', 'interest', TOTAL]);
                expect(dividerCount(html)).toBe(1);
                expect(rowNamed(html, TOTAL).amount).toBe(50);
            });

            const singleDimensionScenarios: Array<[string, Partial<IncomeTooltipValues>, string[]]> = [
                ['only costs', {costVal: -12}, ['costs']],
                ['only deposit', {depositVal: 500}, ['deposit']],
                // Why (re-pin, S8): R11 prints the purchase value above the two indented halves,
                // so either acquisition half now opens three rows. The scenarios still prove that
                // only the non-zero dimensions open the section, and the halves come as a pair.
                ['only fresh-capital acquisition', {acqNewVal: 400}, ['<b>bookValue</b>', '↳ acqNewCapital', '↳ acqReinvested']],
                ['only reinvested acquisition', {acqReinvestedVal: 200}, ['<b>bookValue</b>', '↳ acqNewCapital', '↳ acqReinvested']],
            ];

            it.each(singleDimensionScenarios)('opens the second section for %s, and only for the dimensions that are actually non-zero', (_label, overrides, expectedExtraRows) => {
                const html = incomeTooltip({...zeroDay, ...overrides});

                expect(rowLabels(html)).toEqual(['dividend', 'interest', TOTAL, ...expectedExtraRows]);
                expect(dividerCount(html)).toBe(2);
            });

            it('renders BOTH acquisition legs whenever either is non-zero — the split is a pair, and a 0 leg is information', () => {
                // A BUY funded entirely from reinvested returns means the acqNewCapital
                // row's value is exactly 0.
                // Hiding that row would make the day look like it had no fresh-capital
                // question at all, rather than answering it with a zero.
                const html = incomeTooltip({...zeroDay, acqNewVal: 0, acqReinvestedVal: 200});

                // Why (re-pin, S8): R11 indents the halves under the purchase value, so the zero
                // half is now the `↳ acqNewCapital` row and the purchase value prints the sum
                // (0 + 200). The pin still proves the zero leg is printed, not hidden.
                expect(rowLabels(html)).toContain('↳ acqNewCapital');
                expect(rowNamed(html, '↳ acqNewCapital').amount).toBe(0);
                expect(rowNamed(html, '<b>bookValue</b>').amount).toBe(200);
            });

            it('renders every batch-2 row when all four dimensions are active, in a fixed order', () => {
                const html = incomeTooltip(allActive);

                // Why (re-pin, S8): R11 replaces the two acquisition rows with the purchase value
                // followed by its two indented halves. The pin still proves one fixed order for
                // every batch-2 row and a single divider before them.
                expect(rowLabels(html)).toEqual(['dividend', 'interest', TOTAL, 'costs', 'deposit', '<b>bookValue</b>', '↳ acqNewCapital', '↳ acqReinvested']);
                expect(dividerCount(html)).toBe(2);
            });

            it('folds NOTHING from the batch-2 dimensions into the income total — they are different economic concepts', () => {
                const html = incomeTooltip(allActive);

                expect(rowNamed(html, TOTAL).amount).toBe(12);
                // Why (re-pin, S8): R11 gives the purchase value its own total (300 + 100). The
                // income total above still folds in none of the batch-2 dimensions.
                expect(rowNamed(html, '<b>bookValue</b>').amount).toBe(400);
            });

            it('paints each income row in its own colour — both totals in the text colour, the acquisition halves in their D26 zone colours — and prints each amount from its own path', () => {
                // Why (FE6a): the colour of each signedRow and the path of each value were pinned as
                // the branch's source text; here they are read off the real tooltip, in both themes.
                // Why (re-pin, S8): R11 swaps the two acquisition rows for the purchase value (bold
                // label, new + reinvested, text colour) and its two `↳ ` halves, painted in the D26
                // zone colours (KPI blue, returns): the old two-row form, in the sage of the
                // contributed capital, must be gone.
                for (const isDark of [false, true]) {
                    const theme = isDark ? 'dark' : 'light';
                    const rows = rowsOf(incomeTooltip(allActive, isDark));

                    expect(rows.map(({label, colour}) => [label, colour])).toEqual([
                        ['dividend', GROWTH_SERIES.dividend[theme]],
                        ['interest', GROWTH_SERIES.interest[theme]],
                        [TOTAL, THEME.textColor],
                        ['costs', GROWTH_SERIES.costs[theme]],
                        ['deposit', GROWTH_SERIES.deposit[theme]],
                        ['<b>bookValue</b>', THEME.textColor],
                        ['↳ acqNewCapital', GROWTH_SERIES.bookAssetLike[theme]],
                        ['↳ acqReinvested', GROWTH_SERIES.cashGenerated[theme]],
                    ]);
                    // Six distinct values, so a row reading a sibling's path prints a wrong amount.
                    expect(rows.map(({amount}) => amount)).toEqual([10, 2, 12, -5, 1000, 400, 300, 100]);
                    expect(rows.map(({colour}) => colour)).not.toContain(GROWTH_SERIES.cashContributed[theme]);
                }
            });

            it('defaults each of the six values to 0 when the hovered entry holds none — an empty day reads as the all-zero day, never as a gap', () => {
                // Each of the six values defaults to 0 when the aggregated entry is absent —
                // which is what makes "all zero" the honest reading of an empty day. Why (FE6a):
                // pinned as `?? 0` source text while the branch was the component's; here an entry
                // whose six series hold no value at the hovered index, with every input non-zero.
                const none: AggregatedMetric = {values: [], points: []};
                const html = incomeTooltip(allActive, false, (entry) => ({
                    ...entry,
                    pnl: {...entry.pnl, income: {dividend: none, interest: none}, costs: none, deposits: none, acquisition: {fromNewCapital: none, fromReinvested: none}},
                }));

                expect(rowsOf(html).map(({label, amount}) => [label, amount])).toEqual([
                    ['dividend', 0],
                    ['interest', 0],
                    [TOTAL, 0],
                ]);
                expect(dividerCount(html)).toBe(1);
            });

            it('reuses existing i18n keys for costs and deposit — batch 2 adds ZERO new keys for those two', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const storeReference = importedTranslationStoreReference(source);

                expect(source).toMatch(translationCallPattern(storeReference, 'dashboard.feesAndTaxes'));
                expect(source).toMatch(translationCallPattern(storeReference, 'transactions.types.DEPOSIT'));
            });
        });

        // ===================================================================
        // GrowthChart i18n contract
        // ===================================================================
        //
        // Why this block exists. Five keys were added to all four locale files, committed,
        // and then never consumed: the component kept rendering hardcoded English, so
        // IT/FR/ES users saw English while svelte-check, Vitest and the production build
        // all stayed green. Nothing in the suite could have caught it, because nothing
        // asserted the relationship between a key and its call site.
        //
        // The failure mode this guards is NOT "a test goes red" — it is the opposite: a
        // typo'd key makes $_() render the raw key string as visible UI text, and an
        // un-wired key makes one locale silently fall back to English. Both ship green.

        describe('GrowthChart i18n contract', () => {
            const LOCALES = ['en', 'it', 'fr', 'es'] as const;

            function growthChartSource(): string {
                return readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
            }

            function localeBundle(locale: (typeof LOCALES)[number]): Record<string, unknown> {
                return JSON.parse(readFileSync(new URL(`../../i18n/${locale}.json`, import.meta.url), 'utf8'));
            }

            function resolveKey(bundle: Record<string, unknown>, key: string): unknown {
                return key.split('.').reduce<unknown>((node, part) => (node && typeof node === 'object' && part in (node as object) ? (node as Record<string, unknown>)[part] : undefined), bundle);
            }

            /** Every key GrowthChart passes to $_(), including interpolated
             *  `$_('key', {values: …})` calls — the narrow `$_('key')` form misses those
             *  three and would let a future interpolated key slip through unchecked. */
            function referencedKeys(source: string): string[] {
                return [...new Set([...source.matchAll(/\$_\(\s*'([^']+)'/g)].map((match) => match[1]))].sort();
            }

            /**
             * Why (FE6a): GrowthChart's derived data, series and tooltip moved to these three modules. They
             * have no `$_` of their own — the component hands its `$_` to the tooltip as `t` — so their keys
             * are swept as `t('…')` calls, by the same two rules as the component's. `\b` keeps calls such
             * as `format(` or `split(` out of the count.
             */
            const GROWTH_CHART_MODULES = ['growthChartData.ts', 'growthChartSeries.ts', 'growthChartTooltip.ts'] as const;
            const TRANSLATE_CALL = /\bt\(/g;
            const TRANSLATE_LITERAL_CALL = /\bt\(\s*'([^']+)'/g;

            function moduleSource(file: (typeof GROWTH_CHART_MODULES)[number]): string {
                return readFileSync(new URL(`../../features/dashboard/${file}`, import.meta.url), 'utf8');
            }

            /** Every key a module passes to its translator `t`, interpolated calls included. */
            function moduleKeys(): string[] {
                return [...new Set(GROWTH_CHART_MODULES.flatMap((file) => [...moduleSource(file).matchAll(TRANSLATE_LITERAL_CALL)].map((match) => match[1])))].sort();
            }

            it('passes a static string literal to every single $_() call of the component and t() call of its data, series and tooltip modules — the sweep below is only exhaustive if none is dynamic', () => {
                const source = growthChartSource();
                const totalCalls = source.match(/\$_\(/g) ?? [];
                const literalCalls = source.match(/\$_\(\s*'[^']+'/g) ?? [];

                expect(literalCalls).toHaveLength(totalCalls.length);

                let moduleLiteralCalls = 0;
                for (const file of GROWTH_CHART_MODULES) {
                    const text = moduleSource(file);
                    const calls = text.match(TRANSLATE_CALL) ?? [];
                    const literals = [...text.matchAll(TRANSLATE_LITERAL_CALL)];
                    expect(literals, file).toHaveLength(calls.length);
                    moduleLiteralCalls += literals.length;
                }
                // Positive control: the module sweep sees the tooltip's calls. A pattern that matched
                // nothing would make every count above agree, at zero.
                expect(moduleLiteralCalls).toBeGreaterThan(0);
            });

            it('resolves EVERY key the component and its data, series and tooltip modules reference in all four locales — the guard against a typo rendering a raw key as UI text', () => {
                const componentKeys = referencedKeys(growthChartSource());
                const fromModules = moduleKeys();
                expect(componentKeys.length).toBeGreaterThan(0);
                // Positive control: keys that left the component with the tooltip are in the sweep — the
                // partial-bucket line, the candle rows, the income total.
                expect(fromModules).toEqual(expect.arrayContaining(['chart.tooltip.partialBucket', 'dataEditor.col.open', 'assets.distribution.total']));
                const keys = [...new Set([...componentKeys, ...fromModules])].sort();

                const bundles = Object.fromEntries(LOCALES.map((locale) => [locale, localeBundle(locale)]));
                const missing = keys.flatMap((key) => LOCALES.filter((locale) => resolveKey(bundles[locale], key) == null).map((locale) => `${key} @ ${locale}`));

                expect(missing).toEqual([]);
            });

            // The keys batch 2's i18n pass wired, each asserted by NAME rather than by its
            // English text, so a retranslation never turns this red. The long caption key
            // left in round 4 (R9): the caption now uses the short register.
            const WIRED_KEYS = ['dashboard.pnlSubmodeLine', 'dashboard.pnlSubmodeCandles', 'dashboard.pnlSubmodeIncome', 'dashboard.pnlCandlesHypotheticalShort', 'dashboard.pnlAcqNewCapital', 'dashboard.pnlAcqReinvested'] as const;

            it.each(WIRED_KEYS)('consumes %s through $_() — a key that exists but is never wired is exactly the bug that shipped', (key) => {
                const source = growthChartSource();
                const storeReference = importedTranslationStoreReference(source);

                expect(source).toMatch(translationCallPattern(storeReference, key));
            });

            it.each(WIRED_KEYS)('%s is a real translation in every locale, not an English copy left as a placeholder', (key) => {
                const values = LOCALES.map((locale) => resolveKey(localeBundle(locale), key));

                for (const value of values) {
                    expect(typeof value).toBe('string');
                    expect(value).not.toBe('');
                }
                const [en, ...translated] = values;
                expect(translated.some((value) => value !== en)).toBe(true);
            });

            it('never reintroduces hardcoded English for any of the seven — the next person adding a submode cannot quietly repeat this', () => {
                // Why (FE6a): the tooltip rows and the series names moved to the three modules, so the ban
                // covers them as well as the component.
                const sources = [growthChartSource(), ...GROWTH_CHART_MODULES.map(moduleSource)];
                const bannedLiterals = ['Line', 'Candles', 'Income', 'Synthetic — cross-asset high/low are hypothetical and non-simultaneous', 'Synthetic — cross-asset high/low are hypothetical and non-simultaneous, not a real intraday series.', 'New capital', 'Reinvested'];

                for (const source of sources) {
                    for (const literal of bannedLiterals) {
                        // Quoted-literal form, e.g. acqNewCapital: 'New capital'. Bare
                        // substrings are NOT checked: `Line`/`Candles`/`Income`/`Reinvested`
                        // occur dozens of times inside legitimate identifiers
                        // (aggregateLineSeries, pnlSubmodeCandles, incomeHistory,
                        // acqFromReinvestedValues), so a substring ban would be unmaintainable
                        // noise rather than a signal.
                        expect(source).not.toContain(`'${literal}'`);
                        // Svelte text-node form, e.g. >Line< between button tags.
                        expect(source).not.toMatch(new RegExp(`>\\s*${literal.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*<`));
                    }
                    expect(source).not.toContain('TODO(coordinator i18n batch)');
                }
            });

            it('binds each submode button to its OWN key — testid and label cannot drift apart', () => {
                const source = growthChartSource();
                const pairs = [
                    ['growth-pnl-submode-line', 'dashboard.pnlSubmodeLine'],
                    ['growth-pnl-submode-candles', 'dashboard.pnlSubmodeCandles'],
                    ['growth-pnl-submode-income', 'dashboard.pnlSubmodeIncome'],
                ] as const;

                for (const [testid, key] of pairs) {
                    // Sliced by index, not by a `<button[^>]*…>` regex: these buttons carry
                    // `onclick={() => (pnlSubmode = 'line')}`, and the `=>` arrow ends a
                    // `[^>]*` run early, so the regex form silently matches nothing.
                    const anchor = source.indexOf(`data-testid="${testid}"`);
                    expect(anchor, `testid ${testid} not found`).toBeGreaterThan(-1);
                    const open = source.lastIndexOf('<button', anchor);
                    const close = source.indexOf('</button>', anchor);
                    expect(open).toBeGreaterThan(-1);
                    expect(close).toBeGreaterThan(anchor);
                    if (open < 0 || close <= anchor) throw new Error(`GrowthChart ${testid} button not found`);

                    const button = source.slice(open, close);
                    expect(button).toContain(`$_('${key}')`);
                    // ...and only its own key: no other submode's label may appear inside it.
                    for (const [, otherKey] of pairs.filter(([otherTestid]) => otherTestid !== testid)) {
                        expect(button).not.toContain(`$_('${otherKey}')`);
                    }
                }
            });
        });

        describe('P&L candle-width ladder markup', () => {
            it('renders one button per available rung of the eight-rung CANDLE_WIDTH_ORDER, with testid, selectCandleWidth handler and aria-pressed bound to the same width, and no zoom-window selector left', () => {
                const source = readFileSync(new URL('../../features/dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                // Why (re-pin, S10): round 3 removed the 1W/1M/1Y/All visible-range selector
                // (selectZoomWindow). The control in that place is now the candle-width ladder: it
                // picks how many days one body covers and keeps the whole history on the axis.
                // The pins: the eight rungs in order; ONE button per rung through the `#each`,
                // with testid, handler and aria-pressed all bound to the same loop variable; and
                // no trace of the old selector, so it cannot come back unnoticed.
                const order = source.match(/const CANDLE_WIDTH_ORDER: CandleWidth\[\] = \[([^\]]*)\];/)?.[1] ?? '';
                expect([...order.matchAll(/'(\w+)'/g)].map((m) => m[1])).toEqual(['1D', '3D', '1W', '2W', '1M', '3M', '6M', '1Y']);

                const eachStart = source.indexOf('{#each availableCandleWidths as width (width)}');
                const eachEnd = source.indexOf('{/each}', eachStart);
                expect(eachStart).toBeGreaterThan(-1);
                expect(eachEnd).toBeGreaterThan(eachStart);
                if (eachStart < 0 || eachEnd <= eachStart) throw new Error('GrowthChart candle-width ladder #each not found');

                const rung = source.slice(eachStart, eachEnd);
                expect(rung.match(/<button\b/g) ?? []).toHaveLength(1);
                expect(rung).toContain('onclick={() => selectCandleWidth(width)}');
                expect(rung).toContain('aria-pressed={candleWidth === width}');
                expect(rung).toContain('data-testid="growth-candle-width-{width.toLowerCase()}"');

                expect(source).not.toContain('growth-zoom-window-');
                expect(source).not.toContain('selectZoomWindow');
            });
        });
    });

    describe('card chart settings adoption contract', () => {
        it('forwards primary mode and bounds plus secondary profiles through PriceChartCompact', () => {
            const source = readFileSync(new URL('./PriceChartCompact.svelte', import.meta.url), 'utf8');
            const lineChart = source.match(/<LineChart\b[\s\S]*?\/>/)?.[0];

            expect(lineChart).toBeDefined();
            if (!lineChart) throw new Error('PriceChartCompact LineChart invocation not found');
            expect(lineChart).toContain('yAxisMode={axisScale?.mode}');
            expect(lineChart).toContain('yAxisMin={axisScale?.min}');
            expect(lineChart).toContain('yAxisMax={axisScale?.max}');
            expect(lineChart).toContain('{secondaryAxisScales}');
        });

        it.each([
            ['AssetCard', new URL('../assets/AssetCard.svelte', import.meta.url)],
            ['FxCard', new URL('../fx/FxCard.svelte', import.meta.url)],
        ] as const)('%s selects the active primary profile and passes secondary profiles', (_name, path) => {
            const source = readFileSync(path, 'utf8');
            const compactChart = source.match(/<PriceChartCompact\b[\s\S]*?\/>/)?.[0];

            expect(compactChart).toBeDefined();
            if (!compactChart) throw new Error(`${_name} PriceChartCompact invocation not found`);
            expect(compactChart).toContain('axisScale={chartSettings?.axisScales[cardViewMode]}');
            expect(compactChart).toContain('secondaryAxisScales={chartSettings?.axisScales.secondary}');
            expect(compactChart).toContain('viewMode={cardViewMode}');
        });
    });

    it('builds stable semantic descriptors independent of ECharts axis order', () => {
        const rsi = signal({
            id: 'rsi',
            label: 'Relative strength',
            axisKey: 'rsi',
            axisRole: 'independent',
            axisLabel: 'RSI',
            axisMinimum: 0,
            axisMaximum: 100,
            unit: 'index',
        });
        const turnover = signal({
            id: 'turnover',
            label: 'Turnover',
            axisKey: 'turnover',
            axisRole: 'volume',
            axisLabel: 'Volume',
            axisMinimum: 10,
            axisMaximum: 1_000,
            unit: 'volume',
        });

        const descriptorsByKey = (signals: RenderedSignal[]) => Object.fromEntries(collectConfigurableSecondaryAxes(signals).map((descriptor) => [descriptor.key, descriptor]));
        const forward = descriptorsByKey([rsi, turnover]);
        const reversed = descriptorsByKey([turnover, rsi]);

        expect(forward).toEqual({
            'independent:rsi': {
                key: 'independent:rsi',
                label: 'RSI',
                unit: 'index',
                defaultMin: 0,
                defaultMax: 100,
            },
            'volume:turnover': {
                key: 'volume:turnover',
                label: 'Volume',
                unit: 'volume',
                defaultMin: 10,
                defaultMax: 1_000,
            },
        });
        expect(reversed).toEqual(forward);
    });

    it('distinguishes Auto from Include0 for RSI data 20–80 without forcing plugin 0–100', () => {
        const assigned = assignOverlaySignalAxes([
            signal({
                id: 'rsi-closed-semantics',
                axisKey: 'rsi',
                axisRole: 'independent',
                axisLabel: 'RSI 20–80',
                axisMinimum: 0,
                axisMaximum: 100,
                data: [
                    {date: '2026-07-22', value: 20},
                    {date: '2026-07-23', value: 80},
                ],
            }),
        ]);

        const autoLayout = buildSecondaryYAxes(assigned, false, 0, true, {
            'independent:rsi': {mode: 'auto'},
        });
        const include0Layout = buildSecondaryYAxes(assigned, false, 0, true, {
            'independent:rsi': {mode: 'include0'},
        });
        const autoAxis = axisNamed(autoLayout, 'RSI 20–80');
        const include0Axis = axisNamed(include0Layout, 'RSI 20–80');

        expect(autoAxis.min).toBe(20);
        expect(autoAxis.max).toBe(80);
        expect(autoAxis.scale).toBe(true);
        expect(include0Axis.min).toBe(0);
        expect(include0Axis.max).toBe(80);
        expect(include0Axis.scale).toBe(false);
    });

    it('aggregates Auto and Include0 extents across every series sharing a semantic axis', () => {
        const axisKey = 'stoch-rsi';
        const axisLabel = 'Shared Stochastic RSI';
        const assigned = assignOverlaySignalAxes([
            signal({
                id: 'stoch-k-visible-extents',
                axisKey,
                axisRole: 'independent',
                axisLabel,
                data: [
                    {date: '2026-07-22', value: 20},
                    {date: '2026-07-23', value: 60},
                ],
            }),
            signal({
                id: 'stoch-d-visible-extents',
                axisKey,
                axisRole: 'independent',
                axisLabel,
                data: [
                    {date: '2026-07-22', value: 30},
                    {date: '2026-07-23', value: 80},
                ],
            }),
        ]);
        const stochK = assigned.find((candidate) => candidate.id === 'stoch-k-visible-extents');
        const stochD = assigned.find((candidate) => candidate.id === 'stoch-d-visible-extents');

        expect(stochK).toBeDefined();
        expect(stochD).toBeDefined();
        expect(secondaryAxisSettingsKey(stochK!)).toBe('independent:stoch-rsi');
        expect(secondaryAxisSettingsKey(stochD!)).toBe('independent:stoch-rsi');
        expect(stochK!.yAxisIndex).toBe(stochD!.yAxisIndex);
        expect(stochK!.yAxisIndex).toBeGreaterThan(0);

        const autoAxis = axisNamed(
            buildSecondaryYAxes(assigned, false, 0, true, {
                'independent:stoch-rsi': {mode: 'auto'},
            }),
            axisLabel,
        );
        const include0Axis = axisNamed(
            buildSecondaryYAxes(assigned, false, 0, true, {
                'independent:stoch-rsi': {mode: 'include0'},
            }),
            axisLabel,
        );

        expect(autoAxis.min).toBe(20);
        expect(autoAxis.max).toBe(80);
        expect(autoAxis.scale).toBe(true);
        expect(include0Axis.min).toBe(0);
        expect(include0Axis.max).toBe(80);
        expect(include0Axis.scale).toBe(false);
    });

    it('ignores plugin bounds for Include0 on either side of zero', () => {
        const assigned = assignOverlaySignalAxes([
            signal({
                id: 'positive',
                axisKey: 'positive',
                axisRole: 'independent',
                axisLabel: 'Positive',
                axisMinimum: 25,
                axisMaximum: 75,
                data: [
                    {date: '2026-07-22', value: 20},
                    {date: '2026-07-23', value: 80},
                ],
            }),
            signal({
                id: 'negative',
                axisKey: 'negative',
                axisRole: 'independent',
                axisLabel: 'Negative',
                axisMinimum: -75,
                axisMaximum: -25,
                data: [
                    {date: '2026-07-22', value: -80},
                    {date: '2026-07-23', value: -20},
                ],
            }),
        ]);

        const layout = buildSecondaryYAxes(assigned, false, 0, true, {
            'independent:positive': {mode: 'include0'},
            'independent:negative': {mode: 'include0'},
        });

        const positiveAxis = axisNamed(layout, 'Positive');
        const negativeAxis = axisNamed(layout, 'Negative');
        expect(positiveAxis.min).toBe(0);
        expect(positiveAxis.max).toBe(80);
        expect(positiveAxis.scale).toBe(false);
        expect(negativeAxis.min).toBe(-80);
        expect(negativeAxis.max).toBe(0);
        expect(negativeAxis.scale).toBe(false);
    });

    it('keeps explicit Custom bounds and swaps only reversed Custom values', () => {
        const assigned = assignOverlaySignalAxes([
            signal({
                id: 'custom-explicit',
                axisKey: 'custom-explicit',
                axisRole: 'independent',
                axisLabel: 'Custom Explicit',
                axisMinimum: 0,
                axisMaximum: 100,
            }),
            signal({
                id: 'custom-reversed',
                axisKey: 'custom-reversed',
                axisRole: 'independent',
                axisLabel: 'Custom Reversed',
                axisMinimum: 0,
                axisMaximum: 100,
            }),
        ]);

        const layout = buildSecondaryYAxes(assigned, false, 0, true, {
            'independent:custom-explicit': {mode: 'custom', min: -5, max: 15},
            'independent:custom-reversed': {mode: 'custom', min: 90, max: 10},
        });

        expect(axisNamed(layout, 'Custom Explicit')).toMatchObject({
            min: -5,
            max: 15,
            scale: true,
        });
        expect(axisNamed(layout, 'Custom Reversed')).toMatchObject({
            min: 10,
            max: 90,
            scale: true,
        });
    });

    it('builds ECharts markLine and markArea primitives', () => {
        const primitives = buildSignalReferencePrimitives(
            signal({
                referenceLevels: [
                    {
                        key: 'threshold',
                        label: 'Threshold',
                        semantic: 'threshold',
                        value: 70,
                    },
                ],
                valueRegions: [
                    {
                        key: 'high',
                        label: 'High',
                        semantic: 'high',
                        lower: 70,
                        includeLower: true,
                        includeUpper: false,
                    },
                ],
            }),
            false,
        );

        expect(primitives.markLine).toMatchObject({
            data: [{name: 'Threshold', yAxis: 70}],
        });
        expect(primitives.markArea).toMatchObject({
            data: [[{name: 'High', yAxis: 70}, {yAxis: 'max'}]],
        });
    });

    it('maps missing overlay points to null and honors an explicit connectNulls opt-out', () => {
        const label = 'Explicit gap overlay';
        const series = buildOverlaySignalSeries(
            [
                signal({
                    id: 'explicit-gap',
                    label,
                    connectNulls: false,
                    data: [
                        {date: '2026-07-21', value: 10},
                        {date: '2026-07-22', value: 999, missing: true},
                        {date: '2026-07-23', value: 30},
                    ],
                }),
            ],
            ['2026-07-21', '2026-07-22', '2026-07-23'],
            false,
        ).find((candidate) => candidate.name === label);

        expect(series).toBeDefined();
        expect(series).toMatchObject({
            name: label,
            data: [10, null, 30],
            connectNulls: false,
        });
    });

    it('defaults legacy overlays that omit connectNulls to joining gaps', () => {
        const label = 'Legacy gap overlay';
        const series = buildOverlaySignalSeries(
            [
                signal({
                    id: 'legacy-gap',
                    label,
                    data: [
                        {date: '2026-07-21', value: 10},
                        {date: '2026-07-22', value: 999, missing: true},
                        {date: '2026-07-23', value: 30},
                    ],
                }),
            ],
            ['2026-07-21', '2026-07-22', '2026-07-23'],
            false,
        ).find((candidate) => candidate.name === label);

        expect(series).toBeDefined();
        expect(series).toMatchObject({
            name: label,
            data: [10, null, 30],
            connectNulls: true,
        });
    });

    it('renders AREA signals as zero-origin line fills', () => {
        const series = buildOverlaySignalSeries(
            [
                signal({
                    seriesType: 'area',
                    fillOpacity: 0.2,
                    data: [{date: '2026-07-23', value: -12}],
                }),
            ],
            ['2026-07-23'],
            false,
        ).find((candidate) => candidate.name === 'Signal');

        expect(series).toMatchObject({
            type: 'line',
            areaStyle: {origin: 0},
        });
        expect(series?.areaStyle.color).toContain('0.2');
    });
});

/**
 * M-18 CP2: the Y-axis labels in the interface language.
 *
 * `buildPriceYAxis` — the price axis of PriceChartFull and CandlestickChart — and `buildSecondaryYAxes` —
 * RSI, MACD and every other independent axis — write their ticks with `toFixed`, which goes through no
 * locale: a French reader gets `12.3%` and `0.1234` beside amounts written `1 234,56`. Every figure is
 * written in the interface language (the developer's decision M-18, 2026-10-12), through the formatters of
 * CP1, whose locale defaults to `uiLocale()`:
 *
 *     price axis, percentage view    formatPercent(v, {digits: 1, signed: false})
 *     price axis, |v| ≥ 1000         formatFixed(v / 1000, 1) + 'k'
 *     price axis, |v| ≥ 1            formatFixed(v, 2)
 *     price axis, |v| < 1            formatFixed(v, 4, {trim: true})
 *     secondary axes, |v| ≥ 100      formatFixed(v, 0)
 *     secondary axes, |v| ≥ 1        formatFixed(v, 2)
 *     secondary axes, |v| < 1        formatFixed(v, 4, {trim: true})
 *
 * The digits stay `toFixed`'s; only the notation moves. English on an en-US browser keeps today's text
 * below 1,000 (the guard) and gains its thousands separator from 1,000: the new contract, pinned where a
 * case reaches it.
 *
 * Expectations. Localized strings come from `formatPercent`/`formatFixed` given an explicit locale, never
 * typed; English is typed where it is today's exact text, or the grouped text of the new contract. Each
 * French case also checks that French differs from English, so a runtime without French ICU data cannot
 * make the comparison vacuous.
 *
 * Language. Switched as LanguageSelector does — `currentLanguage.set` — before the axis is built; the
 * `afterEach` puts English back, because the language is module state shared by the whole file.
 */
describe('Y-axis labels in the interface language (M-18)', () => {
    type AxisLabelFormatter = (value: number) => string;

    const COLORS = getChartColors(false);
    const FR = {locale: 'fr'} as const;

    /** The tick formatter of the price axis, in its percentage view or in its absolute one. */
    function priceAxisLabel(isPercentage: boolean): AxisLabelFormatter {
        return buildPriceYAxis({mode: 'auto', isPercentage}, COLORS).axisLabel.formatter;
    }

    /** The tick formatter of an independent axis: the RSI's. */
    function secondaryAxisLabel(): AxisLabelFormatter {
        const layout = buildSecondaryYAxes(assignOverlaySignalAxes([signal({id: 'rsi', axisKey: 'rsi', axisRole: 'independent', axisLabel: 'RSI'})]), false);
        return axisNamed(layout, 'RSI').axisLabel.formatter;
    }

    /** What `format` writes for each value, keyed by the value, so one diff names every tick that moved. */
    function ticks(format: AxisLabelFormatter, values: readonly number[]): Record<string, string> {
        return Object.fromEntries(values.map((value) => [String(value), format(value)]));
    }

    /** `value` as JSON with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
    function spelled(value: unknown): string {
        return JSON.stringify(value).replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
    }

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: 'en' | 'fr'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    /** The percentage view: a share, a loss, zero. */
    const PERCENT_TICKS = [12.34, -5.27, 0];
    /** The absolute view, every branch at least once: thousands, units, fractions, zero. */
    const PRICE_TICKS = [2_500, -2_500, 12.3456, 1, -45.678, 0.1234, 0.5, 0];
    /** An independent axis, every branch at least once: hundreds, units, fractions, zero. */
    const SECONDARY_TICKS = [123.4, 12.3456, -45.678, 0.1234, 0.5, 0];

    it('English UI on an en-US browser (guard): below 1,000 every label is today’s exact text', async () => {
        await uiLanguage('en');

        expect(ticks(priceAxisLabel(true), PERCENT_TICKS)).toEqual({'12.34': '12.3%', '-5.27': '-5.3%', '0': '0.0%'});
        expect(ticks(priceAxisLabel(false), PRICE_TICKS)).toEqual({'2500': '2.5k', '-2500': '-2.5k', '12.3456': '12.35', '1': '1.00', '-45.678': '-45.68', '0.1234': '0.1234', '0.5': '0.5', '0': '0'});
        expect(ticks(secondaryAxisLabel(), SECONDARY_TICKS)).toEqual({'123.4': '123', '12.3456': '12.35', '-45.678': '-45.68', '0.1234': '0.1234', '0.5': '0.5', '0': '0'});
    });

    it('English UI on an en-US browser: from 1,000 a label is grouped — the new contract', async () => {
        await uiLanguage('en');
        const grouped = {
            percent: formatPercent(1234.5, {digits: 1, signed: false, locale: 'en-US'}),
            thousands: `${formatFixed(1234.567, 1, {locale: 'en-US'})}k`,
            secondary: formatFixed(1234.56, 0, {locale: 'en-US'}),
        };
        // Control: the grouped text, which today's `toFixed` (`1234.5%`, `1234.6k`, `1235`) is not.
        expect(grouped).toEqual({percent: '1,234.5%', thousands: '1,234.6k', secondary: '1,235'});

        expect({percent: priceAxisLabel(true)(1234.5), thousands: priceAxisLabel(false)(1_234_567), secondary: secondaryAxisLabel()(1234.56)}).toEqual(grouped);
    });

    it('French UI: the percentage view of the price axis writes French percentages', async () => {
        await uiLanguage('fr');
        const expected = {
            '12.34': formatPercent(12.34, {digits: 1, signed: false, ...FR}),
            '-5.27': formatPercent(-5.27, {digits: 1, signed: false, ...FR}),
            '0': formatPercent(0, {digits: 1, signed: false, ...FR}),
            '1234.5': formatPercent(1234.5, {digits: 1, signed: false, ...FR}),
        };
        // Control: this runtime carries French data, so the French text is not the English one.
        expect(expected['12.34'], 'French differs from English').not.toBe('12.3%');

        expect(ticks(priceAxisLabel(true), [...PERCENT_TICKS, 1234.5]), spelled(expected)).toEqual(expected);
    });

    it('French UI: the absolute view of the price axis — thousands as k, units with two decimals, fractions with up to four — in French notation', async () => {
        await uiLanguage('fr');
        const expected = {
            '2500': `${formatFixed(2.5, 1, FR)}k`,
            '-2500': `${formatFixed(-2.5, 1, FR)}k`,
            '1234567': `${formatFixed(1234.567, 1, FR)}k`,
            '12.3456': formatFixed(12.3456, 2, FR),
            '1': formatFixed(1, 2, FR),
            '-45.678': formatFixed(-45.678, 2, FR),
            '0.1234': formatFixed(0.1234, 4, {trim: true, ...FR}),
            '0.5': formatFixed(0.5, 4, {trim: true, ...FR}),
            '0': formatFixed(0, 4, {trim: true, ...FR}),
        };
        expect(expected['12.3456'], 'French differs from English').not.toBe('12.35');

        expect(ticks(priceAxisLabel(false), [...PRICE_TICKS, 1_234_567]), spelled(expected)).toEqual(expected);
    });

    it('French UI: the secondary axes (RSI, MACD, …) in French notation', async () => {
        await uiLanguage('fr');
        const expected = {
            '1234.56': formatFixed(1234.56, 0, FR),
            '123.4': formatFixed(123.4, 0, FR),
            '12.3456': formatFixed(12.3456, 2, FR),
            '-45.678': formatFixed(-45.678, 2, FR),
            '0.1234': formatFixed(0.1234, 4, {trim: true, ...FR}),
            '0.5': formatFixed(0.5, 4, {trim: true, ...FR}),
            '0': formatFixed(0, 4, {trim: true, ...FR}),
        };
        expect(expected['0.1234'], 'French differs from English').not.toBe('0.1234');

        expect(ticks(secondaryAxisLabel(), [1234.56, ...SECONDARY_TICKS]), spelled(expected)).toEqual(expected);
    });
});

/**
 * Plan 52, C3b, Z2's premise: on a `time` axis, ECharts maps a dataZoom percent linearly in TIME over the data's x
 * extent, not over the data indexes. GrowthChart's cascade keeps its window as such a percent; once the running bucket
 * stands on its last day with data, its buckets are no longer evenly spaced, and the window must then be read and
 * written in time. Real ECharts, SSR, as the axis cases above.
 */
describe('ECharts time-axis dataZoom: a percent is a position in time (plan 52, C3b)', () => {
    it('an inside dataZoom at 50–100 % over unevenly spaced days opens halfway in time between the first and the last x, not halfway in index', () => {
        // WHY: whether a percent counts time or indexes is ECharts' call, not ours, so the build the app ships is asked.
        const DAY_MS = 86_400_000;
        const first = Date.UTC(2024, 0, 7);
        // Days 0, 7, 14 and 17: two week steps, then a three-day one, as a running week leaves the last interval.
        const xs = [0, 7, 14, 17].map((day) => first + day * DAY_MS);
        const x0 = xs[0];
        const xN = xs[xs.length - 1];
        const byTime = [x0 + 0.5 * (xN - x0), xN];
        // Control: read as an index, 50 % is index 1.5 of 0..3, halfway between the 2nd and the 3rd x, another instant.
        const byIndex = xs[1] + 0.5 * (xs[2] - xs[1]);
        expect(Math.abs(byIndex - byTime[0]), 'control: the two readings are a day or more apart on these days').toBeGreaterThanOrEqual(DAY_MS);

        /** The slice of ECharts' model this case reads: the window the time axis' scale is set to. WHY a type: `getModel()` is not in ECharts' public typings. */
        type TimeScaleReader = {
            getModel(): {
                getComponent(
                    componentType: 'xAxis',
                    index: 0,
                ): {
                    axis: {
                        scale: {
                            getExtent(): [number, number];
                        };
                    };
                };
            };
        };
        const chart = echarts.init(null, undefined, {
            renderer: 'svg',
            ssr: true,
            width: 640,
            height: 240,
        });
        try {
            chart.setOption({
                useUTC: true,
                animation: false,
                xAxis: {type: 'time'},
                yAxis: {type: 'value'},
                // The shape `buildDataZoom` builds, at 50–100 %.
                dataZoom: [{type: 'inside', xAxisIndex: [0], filterMode: 'filter', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: 50, end: 100}],
                series: [{type: 'line', data: xs.map((x, index) => [x, index + 1])}],
            });
            // The scale's extent is the window the axis draws (ECharts 6 exposes it on the model's axis).
            const [start, end] = (chart as unknown as TimeScaleReader).getModel().getComponent('xAxis', 0).axis.scale.getExtent();
            expect(Math.abs(start - byTime[0]), `window start ${start}: halfway in time is ${byTime[0]}, halfway in index ${byIndex}`).toBeLessThan(1);
            expect(Math.abs(end - byTime[1]), `window end ${end}: the last x is ${byTime[1]}`).toBeLessThan(1);
            // Cross-check: the dataZoom component reports the same window as values.
            const zoom = (chart.getOption() as {dataZoom?: Array<{startValue?: unknown; endValue?: unknown}>}).dataZoom?.[0];
            expect([Math.abs(Number(zoom?.startValue) - byTime[0]) < 1, Math.abs(Number(zoom?.endValue) - byTime[1]) < 1], `dataZoom values ${zoom?.startValue}..${zoom?.endValue}`).toEqual([true, true]);
        } finally {
            chart.dispose();
        }
    });
});
