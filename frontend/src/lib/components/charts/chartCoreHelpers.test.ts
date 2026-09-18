import {readFileSync} from 'node:fs';
import * as echarts from 'echarts';
import {describe, expect, it, vi} from 'vitest';

import type {RenderedSignal} from '$lib/charts/signals';
import {INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, assignOverlaySignalAxes, buildOverlaySignalSeries, buildSecondaryYAxes, collectConfigurableSecondaryAxes, computeRightMargin, secondaryAxisSettingsKey} from './chartCoreHelpers';
import type {ConfigurableAxisDescriptor} from './chartCoreHelpers';
import {exchangeRateAxisLabel, percentageAxisLabel, priceAxisLabel, secondaryAxisLabel, type AxisLabelTranslator} from './axisLabelHelpers';
import {CHART_SET_OPTION_OPTS} from './echartsAnimationConfig';
import {buildSignalReferencePrimitives} from './lineChartHelpers';
import {buildResponsiveXAxisPolicy, formatCompactXAxisDate} from './responsiveXAxis';
import {buildOhlcQuad} from './candlestickChartHelpers';
import {buildBucketInfos, buildZoomWindowForRange, computeBucketCounts, logicalRangeFromBuckets} from '../brokers/lots/lotComparisonChartHelpers';
import {clampGrowthLogicalRange, type GrowthLogicalRange} from '../dashboard/growthChartRange';
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
    });

    const SHORT_X_AXIS_DATES = ['2026-01-01', '2026-01-02'] as const;
    const JANUARY_X_AXIS_DATES = Array.from({length: 31}, (_, index) => `2026-01-${String(index + 1).padStart(2, '0')}`);
    const GROWTH_TIME_AXIS_DATES = ['2025-09-01', '2026-09-01'] as const;

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

        it('leaves a caller-specific desktop axis exactly unchanged and emits no responsive-only keys', () => {
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
            const applied = {
                ...baseline,
                ...(policy.compact ? {splitNumber: policy.splitNumber} : {}),
                axisLabel: {
                    ...baseline.axisLabel,
                    ...(policy.axisLabel ?? {}),
                },
            };

            expect(policy).toEqual({
                compact: false,
                maxLabels: GROWTH_TIME_AXIS_DATES.length,
            });
            expect(policy).not.toHaveProperty('splitNumber');
            expect(policy).not.toHaveProperty('axisLabel');
            expect(applied).toEqual(baseline);
            expect(applied).not.toHaveProperty('splitNumber');
            expect(applied.axisLabel).not.toHaveProperty('hideOverlap');
            expect(applied.axisLabel).not.toHaveProperty('showMinLabel');
            expect(applied.axisLabel).not.toHaveProperty('showMaxLabel');
            expect(applied.axisLabel).not.toHaveProperty('rotate');
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
            const value = '2026-02-03';
            const localDate = new Date(2026, 1, 3);
            const english = formatCompactXAxisDate('en-US', value, 30);
            const italian = formatCompactXAxisDate('it-IT', value, 30);

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
                const expectedCompactFirst = new Intl.DateTimeFormat('en-US', {month: 'short', year: '2-digit'}).format(firstDate);
                const expectedCompactLast = new Intl.DateTimeFormat('en-US', {month: 'short', year: '2-digit'}).format(lastDate);
                const compactAxisLabel = responsiveAxisLabel(compact);

                expect(compact.compact).toBe(true);
                expect(compactAxisLabel.formatter(values[0])).toBe(expectedCompactFirst);
                expect(compactAxisLabel.formatter(values[1])).toBe(expectedCompactLast);
                expect(compactAxisLabel.formatter(values[1])).not.toBe(compactAxisLabel.formatter(values[0]));

                expect(desktop).toEqual({
                    compact: false,
                    maxLabels: values.length,
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
            const expectedCompact = new Intl.DateTimeFormat('it-IT', {month: 'short', year: '2-digit'}).format(localDate);
            const expectedDesktop = new Intl.DateTimeFormat('it-IT', {year: 'numeric', month: 'short', day: 'numeric'}).format(localDate);
            const desktopBaseline = {
                color: '#475569',
                fontSize: 14,
                formatter: (axisValue: number | string) => new Intl.DateTimeFormat('it-IT', {year: 'numeric', month: 'short', day: 'numeric'}).format(new Date(`${axisValue}T00:00:00`)),
            };
            const compactPolicyAxisLabel = responsiveAxisLabel(compact);
            const compactAxisLabel = {...desktopBaseline, ...compactPolicyAxisLabel};
            const restoredDesktopAxisLabel = {...desktopBaseline, ...(desktop.axisLabel ?? {})};

            expect(compact.compact).toBe(true);
            expect(desktop.compact).toBe(false);
            expect(compactPolicyAxisLabel.formatter(value)).toBe(expectedCompact);
            expect(compactAxisLabel.formatter(value)).toBe(expectedCompact);
            expect(restoredDesktopAxisLabel.formatter(value)).toBe(expectedDesktop);
            expect(expectedDesktop).not.toBe(expectedCompact);
            expect(desktop).not.toHaveProperty('axisLabel');
            expect(restoredDesktopAxisLabel).toEqual(desktopBaseline);
        });

        it('lets a lot-chart desktop formatter remain caller-owned without changing compact labels', () => {
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
            const compactAxisLabel = {...baseline, ...compactPolicyAxisLabel};
            const desktopAxisLabel = {...baseline, ...(desktop.axisLabel ?? {})};

            expect(compactPolicyAxisLabel.formatter(value)).toBe(new Intl.DateTimeFormat('en-US', {month: 'short', year: '2-digit'}).format(new Date(2026, 0, 1)));
            expect(compactAxisLabel.formatter).not.toBe(desktopFormatter);
            expect(desktopAxisLabel).toEqual(baseline);
            expect(desktopAxisLabel.formatter(value)).toBe(`lot:${value}`);
            expect(desktopFormatter).toHaveBeenCalledOnce();
        });
    });

    const RESPONSIVE_X_AXIS_CHARTS = [
        ['LineChart', new URL('./LineChart.svelte', import.meta.url)],
        ['CandlestickChart', new URL('./CandlestickChart.svelte', import.meta.url)],
        ['PriceChartFull', new URL('./PriceChartFull.svelte', import.meta.url)],
        ['GrowthChart', new URL('../dashboard/GrowthChart.svelte', import.meta.url)],
        ['AllocationHistoryChart', new URL('../dashboard/AllocationHistoryChart.svelte', import.meta.url)],
        ['LotGanttChart', new URL('../brokers/lots/LotGanttChart.svelte', import.meta.url)],
        ['LotComparisonChart', new URL('../brokers/lots/LotComparisonChart.svelte', import.meta.url)],
        ['LotWacPriceChart', new URL('../brokers/lots/LotWacPriceChart.svelte', import.meta.url)],
    ] as const;

    const LOT_RESPONSIVE_X_AXIS_CHARTS = [
        ['LotGanttChart', new URL('../brokers/lots/LotGanttChart.svelte', import.meta.url)],
        ['LotComparisonChart', new URL('../brokers/lots/LotComparisonChart.svelte', import.meta.url)],
        ['LotWacPriceChart', new URL('../brokers/lots/LotWacPriceChart.svelte', import.meta.url)],
    ] as const;

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
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const rangeReaderStart = source.indexOf('function getLogicalRangeFromChart()');
                const rangeReaderEnd = source.indexOf('\n    function buildZoomWindow(', rangeReaderStart);
                expect(rangeReaderStart).toBeGreaterThan(-1);
                expect(rangeReaderEnd).toBeGreaterThan(rangeReaderStart);
                if (rangeReaderStart < 0 || rangeReaderEnd <= rangeReaderStart) {
                    throw new Error('GrowthChart logical-range reader contract not found');
                }
                const rangeReader = source.slice(rangeReaderStart, rangeReaderEnd);
                expect(rangeReader).toContain('if (!activeChartData || activeChartData.resolution !== currentResolution) return null;');
                expect(rangeReader).not.toContain('getResolutionData(');

                const initialDates = Array.from({length: 9}, (_, index) => `2026-01-${String(index + 1).padStart(2, '0')}`);
                const replacementDates = ['2026-03-10', '2026-03-12', '2026-03-14', '2026-03-16', '2026-03-18'] as const;
                let dates: readonly string[] = initialDates;
                let currentResolution: ChartResolution = 'daily';
                let activeChartData: {resolution: ChartResolution; buckets: ReturnType<typeof buildBucketInfos>} | null = {
                    resolution: currentResolution,
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

                const logicalRangeFromActiveChart = (): GrowthLogicalRange | null => {
                    const entry = activeChartData;
                    if (!entry || entry.resolution !== currentResolution) return null;
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
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
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
                const activeRangeRead = historyEffect.indexOf('const preservedRange = getLogicalRangeFromChart();');
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
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
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
                expect(renderChart).toMatch(/if \(resolutionResetPending\) \{\s*const counts = computeBucketCounts\(logicalRange\.startDate, logicalRange\.endDate\);\s*currentResolution = chooseInitialResolution\(counts, chartInstance\.getWidth\(\)\);\s*resolutionResetPending = false;\s*\}/);

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
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
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
                const zoomWindow = renderChart.indexOf('const zoomWindow = buildZoomWindow(currentResolution, logicalRange.startDate, logicalRange.endDate);', ensure);
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
                    expect(desktopPolicy).toEqual({
                        compact: false,
                        maxLabels: dates.length,
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
                                axisLabel: {
                                    color: '#475569',
                                    fontSize: 14,
                                    rotate: 0,
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
                    expect(rebuiltAxisLabel?.formatter).toBeUndefined();
                    expect(rebuiltAxisLabel?.interval).toBeUndefined();
                    expect(rebuiltAxisLabel?.showMinLabel).toBe(false);
                    expect(rebuiltAxisLabel?.showMaxLabel).toBe(false);
                } finally {
                    chart.dispose();
                }
            });
        });

        it.each(RESPONSIVE_X_AXIS_CHARTS)('%s imports and applies the shared policy to initial and resized options', (_name, path) => {
            const source = readFileSync(path, 'utf8');

            expect(source).toMatch(/import\s+\{\s*buildResponsiveXAxisPolicy\s*\}\s+from\s+['"][^'"]*responsiveXAxis['"]/);
            expect(source).toMatch(/\bbuildResponsiveXAxisPolicy\s*\(/);
            expect(source).toMatch(/if \(policy\.axisLabel\) \{[\s\S]*?setOption\(\{xAxis:\s*\{[\s\S]*?axisLabel:\s*policy\.axisLabel/);
            expect(source).toContain('...(xAxisPolicy.axisLabel ?? {})');
        });

        it('routes every GrowthChart compact-to-desktop data update through a full x-axis replacement with the current zoom window', () => {
            const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
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
            expect(updateChartData).toMatch(
                /const isCandlesSubmode = viewMode === 'pnl' && pnlSubmode === 'candles';\s*const xAxisPolicy = buildResponsiveXAxisPolicy\(\{\s*width: chartContainer\?\.clientWidth \?\? 0,\s*values: entry\.dates,\s*locale: \$locale \?\? undefined,\s*axisType: isCandlesSubmode \? 'category' : 'time',\s*\}\);/,
            );
            expect(updateChartData).toMatch(/const wasCompact = responsiveXAxisCompact;[\s\S]*?if \(wasCompact && !xAxisPolicy\.compact\) \{\s*applyFullOption\(isDark, buildFullSeries\(isDark, seriesData\), zoomWindow\);\s*return;\s*\}\s*responsiveXAxisCompact = xAxisPolicy\.compact;/);
            expect(updateChartData).toContain("dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],");
            // Candles submode's category axis needs `data` refreshed on every partial
            // update (resolution switch changes bucket dates) — the time-axis branch
            // only needs a label/splitNumber refresh, gated behind `compact`.
            expect(updateChartData).toContain('xAxis: isCandlesSubmode ? {data: entry.dates, ...(xAxisPolicy.compact ? {axisLabel: xAxisPolicy.axisLabel} : {})} : xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber, axisLabel: xAxisPolicy.axisLabel}');
            expect(updateChartData).toMatch(/chartInstance\.setOption\([\s\S]*?CHART_SERIES_UPDATE_OPTS,\s*\);/);
            expect(source).toContain("const CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']};");
            expect(source).toContain("const CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis']};");
            expect(source).not.toContain('const entry = activeChartData?.resolution === currentResolution ? activeChartData : getResolutionData(currentResolution);');
            expect(source).toContain('if (!activeChartData || activeChartData.resolution !== currentResolution) return null;');
            expect(fullOption).toContain("dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],");
            // G1b-candles-fix: xAxis is now a submode-conditional ternary (category for
            // candles — a `time` xAxis silently fails to paint any candlestick body/wick,
            // a known upstream ECharts limitation — time for everything else), not a
            // single unconditional object.
            expect(fullOption).toContain('xAxis: isCandlesSubmode');
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
                expect(desktopPolicy).toEqual({
                    compact: false,
                    maxLabels: replacementDates.length,
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
                            axisLabel: {
                                color: '#475569',
                                fontSize: 14,
                                rotate: 0,
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
                expect(rebuiltXAxisLabel?.formatter).toBeUndefined();
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
            const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
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
            expect(renderChart).toContain('const zoomWindow = buildZoomWindow(currentResolution, logicalRange.startDate, logicalRange.endDate);');
            // G1b: needsFullInit now keys on (viewMode, pnlSubmode) via renderedModeKey, not
            // viewMode alone — a pnlSubmode change (line -> candles) changes the series TYPE
            // (line -> candlestick) while viewMode stays 'pnl', which the partial-update path
            // cannot express, so it must also force a full rebuild.
            expect(renderChart).toContain("const renderedModeKey = viewMode === 'pnl' ? `pnl:${pnlSubmode}` : viewMode;");
            expect(renderChart).toContain('const needsFullInit = forceFullXAxisRebuild || lastRenderedMode !== renderedModeKey || lastRenderedDark !== isDark;');
            expect(renderChart).toMatch(/if \(needsFullInit\) \{\s*applyFullOption\(isDark, buildFullSeries\(isDark, seriesData\), zoomWindow\);\s*\} else \{\s*updateChartData\(activeData, isDark, zoomWindow, false, logicalRange\.startDate\);\s*\}/);
            expect(source).toContain("const CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']};");
            expect(source).toContain("const CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis']};");
            expect(fullOption).toContain("dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],");
            expect(fullOption).toContain('xAxis: isCandlesSubmode');
            expect(fullOption).toContain('...(xAxisPolicy.axisLabel ?? {}),');
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

            const capture = renderChart.slice(captureStart, replacement);
            const restoration = renderChart.slice(restoreGuard, renderChart.indexOf('updateArrowRotations(chartInstance);', restoreGuard));
            expect(renderChart).toContain('dataZoom: buildDataZoom(actualShowVolume ? [0, 1] : [0]),');
            expect(capture).toContain('const currentZoom = currentOption.dataZoom?.[0];');
            expect(capture).toContain("if (typeof currentZoom?.start === 'number' && typeof currentZoom.end === 'number')");
            expect(capture).toContain('start: currentZoom.start');
            expect(capture).toContain('end: currentZoom.end');
            expect(restoration).toContain('chartInstance.dispatchAction({');
            expect(restoration).toContain("type: 'dataZoom'");
            expect(restoration).toContain('start: savedZoom.start');
            expect(restoration).toContain('end: savedZoom.end');
        });

        it.each(LOT_RESPONSIVE_X_AXIS_CHARTS)('%s keeps its desktop formatter caller-owned and applies responsive labels only in compact mode', (_name, path) => {
            const source = readFileSync(path, 'utf8');
            const resizeAxisUpdate = source.match(/const policy = buildLotXAxisPolicy\(\);[\s\S]*?if \(policy\.axisLabel\) \{[\s\S]*?setOption\(\{xAxis:\s*\{splitNumber:\s*policy\.splitNumber,\s*axisLabel:\s*policy\.axisLabel\}\},\s*\{lazyUpdate:\s*true\}\);/)?.[0];

            expect(source).toContain('formatter: (value: number) => formatAxisDate($currentLanguage, value, multiYearAxis)');
            expect(source).toContain('...(xAxisPolicy.axisLabel ?? {})');
            expect(source).not.toContain('desktopFormatter:');
            expect(resizeAxisUpdate).toBeDefined();
            if (!resizeAxisUpdate) throw new Error(`${_name} responsive resize axis update not found`);
            expect(resizeAxisUpdate).toContain('axisLabel: policy.axisLabel');
        });

        it('keeps PerformanceChart outside the date-axis policy', () => {
            const source = readFileSync(new URL('../dashboard/PerformanceChart.svelte', import.meta.url), 'utf8');

            expect(source).not.toContain('responsiveXAxis');
            expect(source).not.toContain('buildResponsiveXAxisPolicy');
        });
    });

    describe('GrowthChart P&L mode (G1a/G1b/G1c) series-shape and axis regressions', () => {
        // -------------------------------------------------------------------
        // Fixture builders, mirroring GrowthChart.svelte's own namedPoint/
        // toSeriesPoint shapes: SeriesPoint = {name, value: [date, value|null],
        // bucketStart, bucketEnd, resolution}; CandleSeriesPoint adds
        // open/high/low/close on top (see the component-local type declarations
        // just above buildChartUpdateSeries in GrowthChart.svelte).
        // -------------------------------------------------------------------
        interface FixtureSeriesPoint {
            name: string;
            value: [string, number | null];
            bucketStart: string;
            bucketEnd: string;
            resolution: 'daily';
        }

        interface FixtureCandlePoint extends FixtureSeriesPoint {
            open: number | null;
            high: number | null;
            low: number | null;
            close: number | null;
        }

        function seriesPoint(date: string, value: number | null, bucketEnd: string = date): FixtureSeriesPoint {
            return {name: date, value: [date, value], bucketStart: date, bucketEnd, resolution: 'daily'};
        }

        function candlePoint(date: string, ohlc: {open: number; high: number; low: number; close: number} | null): FixtureCandlePoint {
            return {...seriesPoint(date, ohlc?.close ?? null), open: ohlc?.open ?? null, high: ohlc?.high ?? null, low: ohlc?.low ?? null, close: ohlc?.close ?? null};
        }

        function candlePointRaw(date: string, open: number | null, close: number | null, low: number | null, high: number | null): FixtureCandlePoint {
            return {...seriesPoint(date, close), open, close, low, high};
        }

        // -------------------------------------------------------------------
        // Faithful reimplementations of GrowthChart.svelte's component-local
        // helpers. They are not exported (closures inside the component's
        // <script>), so — following this file's own established pattern for
        // testing GrowthChart-local logic (see "GrowthChart stateful reset and
        // rebuild regressions" above, which reimplements getLogicalRangeFromChart
        // / resetResolutionState the same way) — each is (a) copied here
        // verbatim for real execution, and (b) pinned against the actual source
        // text by the source-contract test immediately below, so an edit to the
        // real function forces this reimplementation to be revisited too.
        // -------------------------------------------------------------------
        function toCandlestickPointImpl(point: FixtureCandlePoint): number[] | null {
            if (point.open == null || point.close == null || point.low == null || point.high == null) return null;
            return buildOhlcQuad(point.open, point.close, point.low, point.high, false, 1);
        }

        function toPositionalValueImpl(point: FixtureSeriesPoint): number | null {
            return point.value[1];
        }

        function clipToSignImpl(point: FixtureSeriesPoint, keepPositive: boolean): FixtureSeriesPoint {
            const v = point.value[1];
            if (v == null || v >= 0 === keepPositive) return point;
            return {...point, value: [point.value[0], null]};
        }

        function findReferenceTotalPnlImpl(points: FixtureSeriesPoint[], referenceDate: string | null): number | null {
            if (points.length === 0) return null;
            const point = (referenceDate != null && points.find((p) => p.bucketEnd >= referenceDate)) || points[0];
            return point.value[1];
        }

        it('mirrors the exact literal bodies of toCandlestickPoint / toPositionalValue / clipToSign / findReferenceTotalPnl in GrowthChart.svelte (ties every reimplementation above to the real source)', () => {
            const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
            const start = source.indexOf('function toCandlestickPoint(point: CandleSeriesPoint): number[] | null {');
            const end = source.indexOf('\n    function buildChartUpdateSeries(', start);
            expect(start).toBeGreaterThan(-1);
            expect(end).toBeGreaterThan(start);
            if (start < 0 || end <= start) throw new Error('GrowthChart P&L local-helper contract not found');

            const block = source.slice(start, end);
            // toCandlestickPoint
            expect(block).toContain('if (point.open == null || point.close == null || point.low == null || point.high == null) return null;');
            expect(block).toContain('return buildOhlcQuad(point.open, point.close, point.low, point.high, false, 1);');
            // toPositionalValue
            expect(block).toContain('function toPositionalValue(point: SeriesPoint): number | null {');
            expect(block).toContain('return point.value[1];');
            // clipToSign
            expect(block).toContain('function clipToSign(point: SeriesPoint, keepPositive: boolean): SeriesPoint {');
            expect(block).toContain('const v = point.value[1];');
            expect(block).toContain('if (v == null || v >= 0 === keepPositive) return point;');
            expect(block).toContain('return {...point, value: [point.value[0], null]};');
            // findReferenceTotalPnl
            expect(block).toContain('function findReferenceTotalPnl(entry: AggregatedResolutionData, referenceDate: string | null): number | null {');
            expect(block).toContain('const points = entry.pnl.total.points;');
            expect(block).toContain('if (points.length === 0) return null;');
            expect(block).toContain('const point = (referenceDate != null && points.find((p) => p.bucketEnd >= referenceDate)) || points[0];');
        });

        describe('toCandlestickPoint', () => {
            it('returns the [open, close, low, high] quad, via the real buildOhlcQuad, in absolute mode (base=1) regardless of any outer view mode', () => {
                const point = candlePoint('2026-01-05', {open: 100, close: 110, low: 95, high: 115});
                expect(toCandlestickPointImpl(point)).toEqual([100, 110, 95, 115]);
                expect(toCandlestickPointImpl(point)).toEqual(buildOhlcQuad(100, 110, 95, 115, false, 1));
            });

            const missingLegScenarios: Array<[string, number | null, number | null, number | null, number | null]> = [
                ['open', null, 1, 1, 1],
                ['close', 1, null, 1, 1],
                ['low', 1, 1, null, 1],
                ['high', 1, 1, 1, null],
            ];

            it.each(missingLegScenarios)('returns null (a genuine gap, never a synthesized flat bar) when only %s is missing', (_field, open, close, low, high) => {
                expect(toCandlestickPointImpl(candlePointRaw('2026-01-05', open, close, low, high))).toBeNull();
            });

            it('returns a quad when all four legs are present, even when one leg is exactly zero (zero is not "missing")', () => {
                expect(toCandlestickPointImpl(candlePointRaw('2026-01-05', 0, 5, 0, 10))).toEqual([0, 5, 0, 10]);
            });
        });

        describe('toPositionalValue', () => {
            it('extracts the bare numeric value, discarding the date half of the [date, value] tuple', () => {
                expect(toPositionalValueImpl(seriesPoint('2026-01-01', 123.45))).toBe(123.45);
            });

            it('preserves null (a gap) rather than coercing it to 0 or dropping the point', () => {
                expect(toPositionalValueImpl(seriesPoint('2026-01-01', null))).toBeNull();
            });

            it('is a pure 1:1 positional map — mapping it over an array never changes length or order', () => {
                const dates = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04'];
                const values: Array<number | null> = [10, null, -5, 0];
                const points = dates.map((d, i) => seriesPoint(d, values[i]));
                expect(points.map(toPositionalValueImpl)).toEqual(values);
            });
        });

        describe('clipToSign', () => {
            it('keeps a positive value unchanged (same object reference) when keepPositive is true', () => {
                const point = seriesPoint('2026-01-01', 50);
                expect(clipToSignImpl(point, true)).toBe(point);
            });

            it('keeps a negative value unchanged (same object reference) when keepPositive is false', () => {
                const point = seriesPoint('2026-01-01', -50);
                expect(clipToSignImpl(point, false)).toBe(point);
            });

            it('treats an exact zero as positive: kept when keepPositive is true, nulled when keepPositive is false', () => {
                const point = seriesPoint('2026-01-01', 0);
                expect(clipToSignImpl(point, true)).toBe(point);
                expect(clipToSignImpl(point, false).value[1]).toBeNull();
            });

            it('nulls only the value (not the date/name/bucket metadata) when the sign does not match', () => {
                const point = seriesPoint('2026-01-01', -50, '2026-01-02');
                const clipped = clipToSignImpl(point, true);
                expect(clipped).not.toBe(point);
                expect(clipped.value).toEqual(['2026-01-01', null]);
                expect(clipped.name).toBe(point.name);
                expect(clipped.bucketStart).toBe(point.bucketStart);
                expect(clipped.bucketEnd).toBe(point.bucketEnd);
            });

            it('preserves a null point unchanged (same reference) for BOTH keepPositive branches — a missing day is a gap in both series, never fabricated', () => {
                const point = seriesPoint('2026-01-01', null);
                expect(clipToSignImpl(point, true)).toBe(point);
                expect(clipToSignImpl(point, false)).toBe(point);
            });
        });

        describe('findReferenceTotalPnl', () => {
            const dates = ['2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26'];
            const values = [100, 150, 90, 200];
            const points = dates.map((d, i) => seriesPoint(d, values[i], d));

            it('returns null for an empty series (nothing to draw a reference against)', () => {
                expect(findReferenceTotalPnlImpl([], '2026-01-12')).toBeNull();
            });

            it('falls back to the first point when referenceDate is null', () => {
                expect(findReferenceTotalPnlImpl(points, null)).toBe(100);
            });

            it('picks the first bucket whose bucketEnd reaches a referenceDate that falls strictly between two buckets', () => {
                // 01-08 sits between bucket 1 (ends 01-05) and bucket 2 (ends 01-12): the
                // first bucket that "closes over" it is bucket 2 (150), not bucket 1.
                expect(findReferenceTotalPnlImpl(points, '2026-01-08')).toBe(150);
            });

            it('matches on an exact bucketEnd', () => {
                expect(findReferenceTotalPnlImpl(points, '2026-01-19')).toBe(90);
            });

            it('falls back to the first point when referenceDate is after every bucket', () => {
                expect(findReferenceTotalPnlImpl(points, '2099-01-01')).toBe(100);
            });

            it('can itself return null when the located bucket has no P&L value that day (a genuine gap is a valid reference, never guessed)', () => {
                const withGap = [seriesPoint('2026-01-05', null), seriesPoint('2026-01-12', 50)];
                expect(findReferenceTotalPnlImpl(withGap, '2026-01-05')).toBeNull();
            });
        });

        describe('resize watcher keeps the splitNumber/axisLabel update unconditional across submodes', () => {
            it('computes isCandlesSubmode and forwards it to buildResponsiveXAxisPolicy, but does not fork the actual setOption call on it (splitNumber is undefined-by-construction for category — see the policy test above)', () => {
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const resizeStart = source.indexOf('const resizeWatcher = createResizeWatcher(() => {');
                const resizeEnd = source.indexOf('\n    let darkModeObserver', resizeStart);
                expect(resizeStart).toBeGreaterThan(-1);
                expect(resizeEnd).toBeGreaterThan(resizeStart);
                if (resizeStart < 0 || resizeEnd <= resizeStart) throw new Error('GrowthChart resize watcher contract not found');

                const resizeCallback = source.slice(resizeStart, resizeEnd);
                expect(resizeCallback).toContain("const isCandlesSubmode = viewMode === 'pnl' && pnlSubmode === 'candles';");
                expect(resizeCallback).toContain("axisType: isCandlesSubmode ? 'category' : 'time',");
                // The actual xAxis update stays a SINGLE unconditional object — unlike
                // updateChartData's category branch, it never refreshes `data`: a resize
                // never changes which dates are on screen, only the pixel budget for labels.
                expect(resizeCallback).toContain('chartInstance.setOption({xAxis: {splitNumber: policy.splitNumber, axisLabel: policy.axisLabel}}, {lazyUpdate: true});');
                expect(resizeCallback).not.toContain('data: activeChartData.dates');
                expect(resizeCallback).not.toContain('data: entry.dates');
                // Exactly ONE isCandlesSubmode ternary in this block (the axisType line
                // above) — if a future edit also forked the setOption call, this count
                // would become 2 and this assertion would catch it.
                const isCandlesSubmodeTernaryCount = (resizeCallback.match(/isCandlesSubmode\s*\?/g) ?? []).length;
                expect(isCandlesSubmodeTernaryCount).toBe(1);
            });
        });

        describe('applyFullOption completes the category-vs-time xAxis ternary on both branches', () => {
            it('sets category type/data/boundaryGap and time type/splitNumber, sharing the axisLabel merge / axisLine / splitLine exactly once per branch', () => {
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const fullOptionStart = source.indexOf('function applyFullOption(');
                const fullOptionEnd = source.indexOf('\n</script>', fullOptionStart);
                expect(fullOptionStart).toBeGreaterThan(-1);
                expect(fullOptionEnd).toBeGreaterThan(fullOptionStart);
                if (fullOptionStart < 0 || fullOptionEnd <= fullOptionStart) throw new Error('GrowthChart applyFullOption contract not found');

                const fullOption = source.slice(fullOptionStart, fullOptionEnd);
                const xAxisStart = fullOption.indexOf('xAxis: isCandlesSubmode');
                const xAxisEnd = fullOption.indexOf('yAxis: {', xAxisStart);
                expect(xAxisStart).toBeGreaterThan(-1);
                expect(xAxisEnd).toBeGreaterThan(xAxisStart);
                if (xAxisStart < 0 || xAxisEnd <= xAxisStart) throw new Error('GrowthChart applyFullOption xAxis ternary not found');

                const xAxisBlock = fullOption.slice(xAxisStart, xAxisEnd);
                // Category branch (candles submode).
                expect(xAxisBlock).toContain("type: 'category',");
                expect(xAxisBlock).toContain('data: activeChartData?.dates ?? dates,');
                expect(xAxisBlock).toContain('boundaryGap: true,');
                // Time branch (every other mode/submode) — not just spot-checked, but
                // proven present alongside the category branch above, in the same slice.
                expect(xAxisBlock).toContain("type: 'time',");
                expect(xAxisBlock).toContain('...(xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber} : {}),');

                // Shared theming appears exactly twice (once per branch) — catches a
                // future edit that updates one branch and forgets its sibling.
                const axisLabelMergeCount = (xAxisBlock.match(/\.\.\.\(xAxisPolicy\.axisLabel \?\? \{\}\),/g) ?? []).length;
                const axisLineCount = (xAxisBlock.match(/axisLine: \{lineStyle: \{color: gridColor\}\},/g) ?? []).length;
                const splitLineCount = (xAxisBlock.match(/splitLine: \{show: false\},/g) ?? []).length;
                expect(axisLabelMergeCount).toBe(2);
                expect(axisLineCount).toBe(2);
                expect(splitLineCount).toBe(2);
            });
        });

        describe('candles-submode positional alignment: candlestick quad and broker overlay line up 1:1 with dates', () => {
            it('mirrors getResolutionData: dates, pnl.total, pnl.candle and every pnl.brokers[].metric are all built from the exact same buckets array (never a second, independently computed one)', () => {
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const start = source.indexOf('function getResolutionData(resolution: ChartResolution): AggregatedResolutionData {');
                const end = source.indexOf('\n    function computeBucketCounts(', start);
                expect(start).toBeGreaterThan(-1);
                expect(end).toBeGreaterThan(start);
                if (start < 0 || end <= start) throw new Error('GrowthChart getResolutionData contract not found');

                const block = source.slice(start, end);
                expect(block).toContain('const buckets = buildBucketInfos(resolution);');
                expect(block).toContain('dates: buckets.map((bucket) => bucket.date),');
                expect(block).toContain('total: aggregateMetric(eurStackedData.totalPnl, resolution, buckets),');
                expect(block).toContain('metric: aggregateMetric(broker.values, resolution, buckets),');
                expect(block).toContain('candle: aggregateCandleMetric(pnlCandleByDate, resolution, buckets),');
                // `buckets` is constructed exactly once per resolution-cache-miss — every
                // series above threads that SAME reference, never a fresh computation.
                const buildBucketInfosCallCount = (block.match(/buildBucketInfos\(/g) ?? []).length;
                expect(buildBucketInfosCallCount).toBe(1);
            });

            it('mirrors the buildChartUpdateSeries candles-submode mapping calls exactly: toCandlestickPoint for the total slot, toPositionalValue for every broker slot', () => {
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const functionStart = source.indexOf('function buildChartUpdateSeries(');
                const start = source.indexOf("if (viewMode === 'pnl' && pnlSubmode === 'candles') {", functionStart);
                const end = source.indexOf("if (viewMode === 'pnl' && pnlSubmode === 'income') {", start);
                expect(functionStart).toBeGreaterThan(-1);
                expect(start).toBeGreaterThan(functionStart);
                expect(end).toBeGreaterThan(start);
                if (functionStart < 0 || start <= functionStart || end <= start) throw new Error('GrowthChart candles-submode series contract not found');

                const block = source.slice(start, end);
                expect(block).toContain('entry.pnl.candle.points.map(toCandlestickPoint)');
                expect(block).toContain('broker.metric.points.map(toPositionalValue)');
            });

            it('keeps candlestick quads and broker overlay values 1:1 by array position with dates — a gap at one position never shifts a later one', () => {
                const dates = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'];
                // Distinct sentinel OHLC/values per position so any transposition/shift is
                // caught. The candle is missing (a genuine gap) at position 2; the broker
                // value is missing at position 1 — deliberately DIFFERENT positions, to
                // prove the two series are independently, not jointly, null-preserving.
                const candles: Array<{open: number; high: number; low: number; close: number} | null> = [{open: 10, close: 11, low: 9, high: 12}, {open: 20, close: 22, low: 19, high: 23}, null, {open: 40, close: 38, low: 37, high: 41}, {open: 50, close: 55, low: 49, high: 56}];
                const brokerValues: Array<number | null> = [100, null, 300, 400, 500];

                const candlePoints = dates.map((d, i) => candlePoint(d, candles[i]));
                const brokerPoints = dates.map((d, i) => seriesPoint(d, brokerValues[i]));

                const candleSeries = candlePoints.map(toCandlestickPointImpl);
                const brokerSeries = brokerPoints.map(toPositionalValueImpl);

                expect(candleSeries).toHaveLength(dates.length);
                expect(brokerSeries).toHaveLength(dates.length);

                dates.forEach((_date, i) => {
                    const ohlc = candles[i];
                    if (ohlc == null) {
                        expect(candleSeries[i]).toBeNull();
                    } else {
                        expect(candleSeries[i]).toEqual(buildOhlcQuad(ohlc.open, ohlc.close, ohlc.low, ohlc.high, false, 1));
                    }
                    expect(brokerSeries[i]).toBe(brokerValues[i]);
                });

                // The two gaps are genuinely independent, at different positions — if
                // either mapping ever filtered instead of preserving position (the exact
                // off-by-one risk this fix calls out), the two arrays would desync both
                // from `dates` and from each other.
                expect(candleSeries[2]).toBeNull();
                expect(candleSeries[1]).not.toBeNull();
                expect(brokerSeries[1]).toBeNull();
                expect(brokerSeries[2]).not.toBeNull();
                expect(candleSeries).toHaveLength(brokerSeries.length);
            });
        });

        describe('line-submode fixed 3-slot P&L split (positive / negative / reference)', () => {
            it('mirrors the exact buildChartUpdateSeries / buildFullSeries series-shape contract: 3 fixed slots (line submode) or 1 fixed slot (candles submode) before the variable broker spread', () => {
                const source = readFileSync(new URL('../dashboard/GrowthChart.svelte', import.meta.url), 'utf8');
                const updateStart = source.indexOf('function buildChartUpdateSeries(');
                const updateEnd = source.indexOf('\n    function buildFullSeries(', updateStart);
                const fullStart = source.indexOf('function buildFullSeries(', updateEnd);
                const fullEnd = source.indexOf('\n    function updateChartData(', fullStart);
                expect(updateStart).toBeGreaterThan(-1);
                expect(updateEnd).toBeGreaterThan(updateStart);
                expect(fullStart).toBeGreaterThan(updateEnd);
                expect(fullEnd).toBeGreaterThan(fullStart);
                if (updateStart < 0 || updateEnd <= updateStart || fullStart <= updateEnd || fullEnd <= fullStart) {
                    throw new Error('GrowthChart buildChartUpdateSeries/buildFullSeries contract not found');
                }

                const updateSeries = source.slice(updateStart, updateEnd);
                const fullSeries = source.slice(fullStart, fullEnd);

                // buildChartUpdateSeries: line submode is exactly [positive, negative,
                // reference, ...brokers] — 3 fixed named slots, then the variable spread.
                expect(updateSeries).toContain('const referenceValue = findReferenceTotalPnl(entry, referenceDate);');
                expect(updateSeries).toContain('const referencePoints: SeriesPoint[] = entry.pnl.total.points.map((p) => ({...p, value: [p.value[0], referenceValue]}));');
                expect(updateSeries).toContain('{name: pnlLabels.total, data: entry.pnl.total.points.map((p) => clipToSign(p, true))},');
                expect(updateSeries).toContain('{name: pnlLabels.total, data: entry.pnl.total.points.map((p) => clipToSign(p, false))},');
                expect(updateSeries).toContain("{name: '__pnlReference__', data: referencePoints},");
                expect(updateSeries).toContain('...entry.pnl.brokers.map((broker) => ({name: broker.brokerName, data: broker.metric.points})),');

                // buildChartUpdateSeries: candles submode is exactly [candle, ...brokers] —
                // a single fixed slot, then the variable spread.
                expect(updateSeries).toContain('{name: pnlLabels.total, data: entry.pnl.candle.points.map(toCandlestickPoint) as unknown as SeriesPoint[]},');
                expect(updateSeries).toContain('...entry.pnl.brokers.map((broker) => ({name: broker.brokerName, data: broker.metric.points.map(toPositionalValue) as unknown as SeriesPoint[]}))];');

                // buildFullSeries: line submode consumes seriesData[0]/[1]/[2] for
                // positive/negative/reference, then slices from index 3 for brokers —
                // matching the 3 fixed slots above exactly (not slice(1) or slice(2)).
                expect(fullSeries).toMatch(/data: seriesData\[0\]\.data,\s*smooth: false,\s*connectNulls: false,/);
                expect(fullSeries).toMatch(/data: seriesData\[1\]\.data,\s*smooth: false,\s*connectNulls: false,/);
                expect(fullSeries).toContain('data: seriesData[2].data,');
                expect(fullSeries).toContain('const brokerSeries: echarts.SeriesOption[] = seriesData.slice(3).map((s, index) => ({');
                expect(fullSeries).toContain('return [positiveSeries, negativeSeries, referenceSeries, ...brokerSeries];');

                // buildFullSeries: candles submode consumes seriesData[0] for the
                // candlestick, then slices from index 1 for brokers — matching the single
                // fixed candle slot above exactly (not slice(2) or higher).
                expect(fullSeries).toContain('const brokerSeries: echarts.SeriesOption[] = seriesData.slice(1).map((s, index) => ({');
                expect(fullSeries).toContain('return [candleSeries, ...brokerSeries];');
            });

            const signCrossingScenarios: Array<[string, Array<number | null>]> = [
                ['all positive', [10, 20, 30]],
                ['all negative', [-10, -20, -30]],
                ['odd number of sign crossings', [5, -5, 5, -5, 5]],
                ['even number of sign crossings', [5, -5, 5, -5]],
                ['many crossings interleaved with gaps', [10, null, -10, 0, -5, null, 20, -20, 0]],
                ['a single point', [42]],
            ];

            it.each(signCrossingScenarios)('keeps exactly 3 fixed-length series (positive/negative/reference) for %s — the slot count never varies with the number of sign crossings', (_label, values) => {
                const dates = values.map((_v, i) => `2026-01-${String(i + 1).padStart(2, '0')}`);
                const points = dates.map((d, i) => seriesPoint(d, values[i]));

                const positive = points.map((p) => clipToSignImpl(p, true));
                const negative = points.map((p) => clipToSignImpl(p, false));
                const referenceValue = findReferenceTotalPnlImpl(points, null);
                const referencePoints = points.map((p) => ({...p, value: [p.value[0], referenceValue] as [string, number | null]}));

                // FIXED length: each of the 3 series has one entry per source point —
                // exactly what keeps updateChartData's partial by-index series merge
                // valid across zoom/pan (see clipToSign's own docstring in GrowthChart.svelte).
                expect(positive).toHaveLength(values.length);
                expect(negative).toHaveLength(values.length);
                expect(referencePoints).toHaveLength(values.length);

                // Completeness + mutual exclusivity per point: a non-null value survives in
                // EXACTLY one of positive/negative; a null value is preserved as null in
                // BOTH (a genuine gap, never fabricated into a zero).
                values.forEach((v, i) => {
                    if (v == null) {
                        expect(positive[i].value[1]).toBeNull();
                        expect(negative[i].value[1]).toBeNull();
                    } else if (v >= 0) {
                        expect(positive[i].value[1]).toBe(v);
                        expect(negative[i].value[1]).toBeNull();
                    } else {
                        expect(positive[i].value[1]).toBeNull();
                        expect(negative[i].value[1]).toBe(v);
                    }
                });

                // The reference line is flat: the SAME single value at every position,
                // regardless of how many points/sign-crossings are in the series.
                const distinctReferenceValues = new Set(referencePoints.map((p) => p.value[1]));
                expect(distinctReferenceValues.size).toBe(1);
                expect(referencePoints[0].value[1]).toBe(referenceValue);
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
