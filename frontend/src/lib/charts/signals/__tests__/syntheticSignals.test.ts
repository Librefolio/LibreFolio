import {describe, expect, it} from 'vitest';

import {ChartSignal, type SignalStyle} from '../ChartSignal';
import {CompoundSignal} from '../CompoundSignal';
import {LinearSignal} from '../LinearSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {SineSignal} from '../SineSignal';

/**
 * Synthetic benchmarks and the base-class contract they inherit.
 *
 * `localSignalRegression.test.ts` pins that these three still produce a series
 * of the right length. This file pins the numbers and the decisions around them:
 * how a percentage view is derived, what happens on an empty or flat chart, and
 * what each signal calls itself in the legend.
 */

const style: SignalStyle = {
    color: '#3b82f6',
    lineWidth: 1,
    lineType: 'solid',
    markerStart: null,
    markerEnd: null,
};

/** 2026 is not a leap year, so 2026-01-01 → 2027-01-01 is exactly 365 days. */
const YEAR: LineDataPoint[] = [
    {date: '2026-01-01', value: 100},
    {date: '2027-01-01', value: 100},
];

function values(points: LineDataPoint[]): number[] {
    return points.map((point) => point.value);
}

/**
 * Compare a rendered series against exact expected numbers.
 *
 * The formulas run through `/365` and `Math.pow`, so an exact `toEqual` would be
 * asserting IEEE-754 rounding rather than the benchmark: 100 × (1 + 0.1 × 365/365)
 * lands on 110.00000000000001.
 */
function expectValues(points: LineDataPoint[], expected: number[], precision = 9): void {
    const actual = values(points);
    expect(actual).toHaveLength(expected.length);
    actual.forEach((value, index) => expect(value).toBeCloseTo(expected[index], precision));
}

/**
 * Minimal concrete subclass used to exercise `ChartSignal` itself.
 *
 * The base class is abstract, and its rules — when to convert to a percentage,
 * which reference point to use, what to do on the secondary axis — belong to it,
 * not to any one benchmark. Driving them through a signal whose points are fixed
 * keeps the assertions about the base class instead of about someone's formula.
 */
class FixedSignal extends ChartSignal {
    static override signalType = 'fixed-probe';
    static override displayName = 'Fixed';
    static override icon = '•';
    static override paramDescriptors = [];

    computePoints(): LineDataPoint[] {
        return (this.params.points as LineDataPoint[] | undefined) ?? [];
    }

    getLabel(): string {
        return 'Fixed';
    }
}

class SecondaryAxisSignal extends FixedSignal {
    static override signalType = 'fixed-probe-secondary';
    static override yAxisIndex = 1;
}

describe('ChartSignal base contract', () => {
    const points: LineDataPoint[] = [
        {date: '2026-01-01', value: 110},
        {date: '2026-01-02', value: 121},
    ];

    it('converts to a percentage against the chart baseline, not its own first point', () => {
        // The signal opens 10% above the chart; in percentage view it must keep
        // that head start rather than restart at zero.
        const signal = new FixedSignal('probe', style, {points});
        expect(values(signal.render(YEAR, 'percentage').data)).toEqual([10, 21]);
    });

    it('passes absolute values through untouched', () => {
        const signal = new FixedSignal('probe', style, {points});
        expect(values(signal.render(YEAR, 'absolute').data)).toEqual([110, 121]);
    });

    it('leaves values alone when the chart starts at zero', () => {
        // Dividing by that baseline would produce Infinity for every point.
        const signal = new FixedSignal('probe', style, {points});
        const flat: LineDataPoint[] = [
            {date: '2026-01-01', value: 0},
            {date: '2026-01-02', value: 0},
        ];

        expect(values(signal.render(flat, 'percentage').data)).toEqual([110, 121]);
    });

    it('leaves a secondary-axis signal in its own scale', () => {
        // RSI-style signals are dimensionless; a percentage conversion would be
        // meaningless. No shipped signal sets yAxisIndex today, so the rule is
        // exercised through the extension point that declares it.
        const signal = new SecondaryAxisSignal('probe', style, {points});
        const rendered = signal.render(YEAR, 'percentage');

        expect(rendered.yAxisIndex).toBe(1);
        expect(values(rendered.data)).toEqual([110, 121]);
    });

    it('reports an empty series rather than an empty signal', () => {
        const signal = new FixedSignal('probe', style, {points: []});

        expect(signal.render(YEAR, 'percentage').data).toEqual([]);
        expect(signal.renderMulti(YEAR, 'percentage')).toEqual([]);
    });

    it('carries the style straight into the rendered series', () => {
        const signal = new FixedSignal('probe', {color: '#ec4899', lineWidth: 3, lineType: 'dashed', markerStart: 'pin', markerEnd: 'arrow'}, {points});
        const rendered = signal.render(YEAR, 'absolute');

        expect(rendered).toMatchObject({
            id: 'probe',
            label: 'Fixed',
            color: '#ec4899',
            lineWidth: 3,
            lineType: 'dashed',
            markerStart: 'pin',
            markerEnd: 'arrow',
            yAxisIndex: 0,
            aggregationProfile: 'last_with_range',
        });
    });

    it('serialises every param except the injected chart data', () => {
        // `_resolvedData` is refetched on load; the other underscore params are
        // saved style overrides and must survive a reload.
        const signal = new FixedSignal('probe', style, {
            points: [],
            _resolvedData: [{date: '2026-01-01', value: 1}],
            _signalColor: '#84cc16',
            period: 14,
        });

        expect(signal.toConfig()).toEqual({
            id: 'probe',
            signalType: 'fixed-probe',
            params: {points: [], _signalColor: '#84cc16', period: 14},
            style,
        });
    });

    it('does not let the caller mutate the signal through the objects it passed', () => {
        const params = {points};
        const mutableStyle = {...style};
        const signal = new FixedSignal('probe', mutableStyle, params);

        mutableStyle.color = '#000000';
        params.points = [];

        expect(signal.style.color).toBe('#3b82f6');
        expect(signal.computePoints()).toHaveLength(2);
    });
});

describe('LinearSignal', () => {
    it('adds the full annual rate over exactly one year', () => {
        const signal = new LinearSignal('linear', style, {annualRate: 10, offset: 0});
        expectValues(signal.computePoints(YEAR), [100, 110]);
    });

    it('scales the rate linearly with elapsed days', () => {
        // A quarter of a year at 10%/yr is 2.5%: the defining property of a
        // straight line, and what separates it from CompoundSignal.
        const quarter: LineDataPoint[] = [
            {date: '2026-01-01', value: 200},
            {date: '2026-04-02', value: 200}, // 91 days
        ];
        const signal = new LinearSignal('linear', style, {annualRate: 10, offset: 0});

        expect(values(signal.computePoints(quarter))[1]).toBeCloseTo(200 * (1 + (0.1 * 91) / 365), 10);
    });

    it('lifts the whole line by the offset', () => {
        const signal = new LinearSignal('linear', style, {annualRate: 10, offset: 5});
        expectValues(signal.computePoints(YEAR), [105, 115]);
    });

    it('keeps the offset visible in percentage view', () => {
        // The base class normalises against the chart, so a benchmark that opens
        // 5% high still opens at +5% while the chart itself starts at 0%.
        const signal = new LinearSignal('linear', style, {annualRate: 10, offset: 5});
        expectValues(signal.render(YEAR, 'percentage').data, [5, 15]);
    });

    it('falls back to its declared defaults when params are missing', () => {
        const signal = new LinearSignal('linear', style, {});
        expectValues(signal.computePoints(YEAR), [100, 102]);
    });

    it('accepts a negative rate as a declining benchmark', () => {
        const signal = new LinearSignal('linear', style, {annualRate: -20, offset: 0});
        expectValues(signal.computePoints(YEAR), [100, 80]);
    });

    it('produces nothing for an empty chart', () => {
        expect(new LinearSignal('linear', style, {annualRate: 10}).computePoints([])).toEqual([]);
    });

    it('names itself by rate, and appends the offset only when set', () => {
        expect(new LinearSignal('linear', style, {annualRate: 10, offset: 0}).getLabel()).toBe('Linear 10%/yr');
        expect(new LinearSignal('linear', style, {annualRate: 10, offset: 5}).getLabel()).toBe('Linear 10%/yr +5%');
        expect(new LinearSignal('linear', style, {}).getLabel()).toBe('Linear 2%/yr');
    });

    it('lets a negative offset carry its own sign', () => {
        // Users reported `Linear 10%/yr +-5%`: the `+` was hard-coded while the
        // control accepts offsets down to -100, so a benchmark below the start —
        // a legitimate thing to draw — was labelled with two signs.
        expect(new LinearSignal('linear', style, {annualRate: 10, offset: -5}).getLabel()).toBe('Linear 10%/yr -5%');
        expect(new LinearSignal('linear', style, {annualRate: 10, offset: -100}).getLabel()).toBe('Linear 10%/yr -100%');
    });
});

describe('CompoundSignal', () => {
    it('doubles over a year at 100%/yr', () => {
        const signal = new CompoundSignal('compound', style, {annualRate: 100, offset: 0});
        const computed = values(signal.computePoints(YEAR));

        expect(computed[0]).toBe(100);
        expect(computed[1]).toBeCloseTo(200, 6);
    });

    it('compounds above the straight line over the same period', () => {
        // 10%/yr compounded for one year is 10% too, so the difference has to be
        // read mid-period: at half a year compound is behind linear.
        const half: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-07-02', value: 100}, // 182 days
        ];
        const compound = values(new CompoundSignal('compound', style, {annualRate: 100, offset: 0}).computePoints(half))[1];
        const linear = values(new LinearSignal('linear', style, {annualRate: 100, offset: 0}).computePoints(half))[1];

        expect(compound).toBeCloseTo(100 * Math.pow(2, 182 / 365), 6);
        expect(compound).toBeLessThan(linear);
    });

    it('gives the same answer whether the year is walked in one step or many', () => {
        // The iterative daily factor is an optimisation over Math.pow per point;
        // it must not drift away from the closed form as points are added.
        const monthly: LineDataPoint[] = ['2026-01-01', '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01', '2026-06-01', '2026-07-01', '2026-08-01', '2026-09-01', '2026-10-01', '2026-11-01', '2026-12-01', '2027-01-01'].map((date) => ({date, value: 100}));
        const signal = new CompoundSignal('compound', style, {annualRate: 100, offset: 0});

        expect(values(signal.computePoints(monthly)).at(-1)).toBeCloseTo(200, 6);
    });

    it('applies the offset to the starting value before compounding', () => {
        const signal = new CompoundSignal('compound', style, {annualRate: 100, offset: 10});
        const computed = values(signal.computePoints(YEAR));

        expect(computed[0]).toBeCloseTo(110, 9);
        expect(computed[1]).toBeCloseTo(220, 6);
    });

    it('falls back to its declared defaults when params are missing', () => {
        const computed = values(new CompoundSignal('compound', style, {}).computePoints(YEAR));
        expect(computed[1]).toBeCloseTo(108, 6);
    });

    it('produces nothing for an empty chart', () => {
        expect(new CompoundSignal('compound', style, {annualRate: 8}).computePoints([])).toEqual([]);
    });

    it('names itself by rate, and appends the offset only when set', () => {
        expect(new CompoundSignal('compound', style, {annualRate: 8, offset: 0}).getLabel()).toBe('Compound 8%/yr');
        expect(new CompoundSignal('compound', style, {annualRate: 8, offset: 3}).getLabel()).toBe('Compound 8%/yr +3%');
        expect(new CompoundSignal('compound', style, {}).getLabel()).toBe('Compound 8%/yr');
    });

    it('lets a negative offset carry its own sign', () => {
        // The twin of the LinearSignal case: same hard-coded `+`, same report.
        expect(new CompoundSignal('compound', style, {annualRate: 8, offset: -3}).getLabel()).toBe('Compound 8%/yr -3%');
    });
});

describe('SineSignal', () => {
    /** One full oscillation across four days: 0, peak, 0, trough. */
    const cycle: LineDataPoint[] = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'].map((date) => ({date, value: 100}));

    it('peaks at a quarter period and troughs at three quarters', () => {
        const signal = new SineSignal('sine', style, {amplitude: 10, period: 4, offset: 0});
        const computed = values(signal.computePoints(cycle));

        expect(computed[0]).toBeCloseTo(100, 6);
        expect(computed[1]).toBeCloseTo(110, 6);
        expect(computed[2]).toBeCloseTo(100, 6);
        expect(computed[3]).toBeCloseTo(90, 6);
        expect(computed[4]).toBeCloseTo(100, 6);
    });

    it('shifts the whole wave by the offset without changing its swing', () => {
        const signal = new SineSignal('sine', style, {amplitude: 10, period: 4, offset: 20});
        const computed = values(signal.computePoints(cycle));

        expect(computed[0]).toBeCloseTo(120, 6);
        expect(computed[1]).toBeCloseTo(130, 6);
        expect(computed[3]).toBeCloseTo(110, 6);
    });

    it('falls back to its declared defaults when params are missing', () => {
        // amplitude 15, period 45: day 0 is on the zero crossing.
        const computed = values(new SineSignal('sine', style, {}).computePoints(cycle));
        expect(computed[0]).toBeCloseTo(100, 6);
        expect(computed[1]).toBeCloseTo(100 * (1 + 0.15 * Math.sin((2 * Math.PI) / 45)), 6);
    });

    it('produces nothing for an empty chart', () => {
        expect(new SineSignal('sine', style, {amplitude: 15}).computePoints([])).toEqual([]);
    });

    it('names itself by amplitude and period', () => {
        expect(new SineSignal('sine', style, {amplitude: 10, period: 4}).getLabel()).toBe('Sine ±10% / 4d');
        expect(new SineSignal('sine', style, {}).getLabel()).toBe('Sine ±15% / 45d');
    });
});
