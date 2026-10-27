/**
 * The tooltip of a step line reads the day the pointer is on (D-P4, Y5-3).
 *
 * On a time axis ECharts hands the tooltip the data point NEAREST to the pointer, so in the right half of a step it would
 * list the next step's values while the line says another (measured with ECharts 6.0.0: pointer on 9 January, step values
 * 100 until the 11th and 200 after, the tooltip said 200). The component keeps the pointed day
 * (`updateAxisPointer` with `snap: false`) and the tooltip finds the step holding it. The expected values here are the
 * fixture's literals; the control is the same view without a pointed day, which reads `dataIndex` as it always did.
 */
import {describe, expect, it} from 'vitest';
import {uiLocale} from '$lib/stores/app/uiLocale';
import type {AggregatedResolutionData} from './growthChartData';
import {buildGrowthTooltip, type GrowthTooltipView} from './growthChartTooltip';

const THEME = {bg: '#fff', border: '#ccc', textColor: '#111', mutedColor: '#777'};
const eurLabels = {bookAssetLike: 'Assets', bookAssetLikeTooltip: 'Assets', cashContributed: 'Contributed', cashGenerated: 'Generated', nav: 'NAV', capitalBaseline: 'Baseline', capitalBaselineTooltip: 'Baseline'};
const pnlLabels = {total: 'Total P&L', dividend: 'Div', interest: 'Int', costs: 'Costs', deposit: 'Dep', acqNewCapital: 'New', acqReinvested: 'Re', bookValue: 'Book'};

/** Steps starting on the 1st, the 11th and the 21st of January: a flat stretch each. */
const DATES = ['2026-01-01', '2026-01-11', '2026-01-21'];
const NAV = [1010, 1030, 1060];
const PNL = [10, 30, 60];
const TWRR = [1, 3, 6];

const buckets = DATES.map((date) => ({date, bucketStart: date, bucketEnd: date, resolution: 'daily' as const}));
const metric = (values: Array<number | null>) => ({values, points: []});

const ENTRY = {
    resolution: 'daily',
    ladder: false,
    dates: DATES,
    buckets,
    eur: {bookAssetLike: metric([1, 2, 3]), cashContributed: metric([4, 5, 6]), cashGenerated: metric([7, 8, 9]), nav: metric(NAV), capitalBaseline: metric([1000, 1000, 1000]), totalPnl: metric(PNL)},
    pct: {mwrrCum: metric([null, null, null]), twrr: metric(TWRR), roi: metric([0.5, 1.5, 3])},
    pnl: {total: metric(PNL), brokers: [{brokerId: 1, brokerName: 'Broker A', metric: metric([1, 3, 6])}]},
} as unknown as AggregatedResolutionData;

const t = (key: string, options?: {values?: Record<string, string | number>}) => `[${key}${options?.values ? ' ' + JSON.stringify(options.values) : ''}]`;

function view(over: Partial<GrowthTooltipView> = {}): GrowthTooltipView {
    return {entry: ENTRY, viewMode: 'eur', pnlSubmode: 'line', ladderActive: false, candleWidthCaption: () => '1M', eurLabels, pnlLabels, baseCurrency: 'EUR', t: t as GrowthTooltipView['t'], isDark: false, theme: THEME, ...over};
}

/** What the tooltip writes for a money amount, as it writes it. */
const money = (amount: number) => (amount === 0 ? 0 : amount).toLocaleString(uiLocale(), {minimumFractionDigits: 2, maximumFractionDigits: 2});

/** ECharts' own answer: the drawn point nearest to the pointer. */
const nearest = (dataIndex: number) => [{dataIndex, seriesName: 'x', value: ['', 0]}];

describe('the Abs tooltip', () => {
    it('lists the step holding the pointed day, not the drawn point nearest to it', () => {
        // 19 January is two days from the step starting on the 21st and eight from the one starting on the 11th: ECharts says index 2.
        const html = buildGrowthTooltip(nearest(2), view({pointedDay: '2026-01-19'}));
        expect(html).toContain(money(1030));
        expect(html).not.toContain(money(1060));
    });

    it('writes the pointed day in the header, not the day the step starts', () => {
        const html = buildGrowthTooltip(nearest(2), view({pointedDay: '2026-01-19'}));
        expect(html).toContain('2026');
        expect(html).not.toContain('[chart.tooltip.valueAt');
    });

    it('control: without a pointed day it reads the index ECharts gave, as before', () => {
        const html = buildGrowthTooltip(nearest(2), view());
        expect(html).toContain(money(1060));
    });

    it('reads the first step before the first date and the last step after the last', () => {
        expect(buildGrowthTooltip(nearest(0), view({pointedDay: '2025-12-30'}))).toContain(money(1010));
        expect(buildGrowthTooltip(nearest(0), view({pointedDay: '2026-03-01'}))).toContain(money(1060));
    });

    it('reads the step that starts on the pointed day', () => {
        expect(buildGrowthTooltip(nearest(0), view({pointedDay: '2026-01-11'}))).toContain(money(1030));
    });

    it('does not use the pointed day when the chart is not the steps (a coarser resolution)', () => {
        const weekly = {...ENTRY, resolution: 'weekly'} as unknown as AggregatedResolutionData;
        expect(buildGrowthTooltip(nearest(2), view({entry: weekly, pointedDay: '2026-01-19'}))).toContain(money(1060));
    });

    it('does not use the pointed day under the ladder, whose axis is made of buckets', () => {
        const html = buildGrowthTooltip(nearest(2), view({ladderActive: true, viewMode: 'pnl', pnlSubmode: 'line', pointedDay: '2026-01-12'}));
        expect(html).toContain(money(60));
    });
});

describe('the P&L line tooltip', () => {
    it('lists the total and each broker from the step holding the pointed day', () => {
        const html = buildGrowthTooltip(nearest(2), view({viewMode: 'pnl', pnlSubmode: 'line', pointedDay: '2026-01-15'}));
        expect(html).toContain(money(30));
        expect(html).toContain('Broker A');
        expect(html).not.toContain(money(60));
    });
});

describe('the % tooltip', () => {
    const pctRows = [
        {key: 'mwrrCum' as const, name: 'MWRR', colorKey: 'nav' as const},
        {key: 'twrr' as const, name: 'TWRR', colorKey: 'invested' as const},
        {key: 'roi' as const, name: 'ROI', colorKey: 'pctCash' as const},
    ];
    const percent = (value: number) => value.toLocaleString(uiLocale(), {minimumFractionDigits: 2, maximumFractionDigits: 2});

    it('lists TWRR and ROI from the step holding the day, and the MWRR from the true point nearest to it, with its date', () => {
        const html = buildGrowthTooltip(nearest(2), view({viewMode: 'pct', pointedDay: '2026-01-15', pctRows, mwrrAt: () => ({date: '2026-01-11', value: 2.5})}));
        expect(html).toContain('TWRR');
        expect(html).toContain('ROI');
        expect(html).toContain(percent(3));
        expect(html).not.toContain(percent(6));
        expect(html).toContain('MWRR');
        expect(html).toContain(percent(2.5));
        expect(html).toContain('[chart.tooltip.valueAt');
        expect(html).toContain('2026-01-11'.slice(0, 4));
    });

    it('does not name a date when the nearest true point is on the pointed day itself', () => {
        const html = buildGrowthTooltip(nearest(1), view({viewMode: 'pct', pointedDay: '2026-01-11', pctRows, mwrrAt: () => ({date: '2026-01-11', value: 2.5})}));
        expect(html).toContain('MWRR');
        expect(html).not.toContain('[chart.tooltip.valueAt {"date"');
    });

    it('leaves the MWRR out when the line has no point', () => {
        const html = buildGrowthTooltip(nearest(1), view({viewMode: 'pct', pointedDay: '2026-01-15', pctRows, mwrrAt: () => null}));
        expect(html).not.toContain('MWRR');
        expect(html).toContain('TWRR');
    });
});
