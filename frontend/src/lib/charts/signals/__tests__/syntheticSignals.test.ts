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

    it('still converts to a percentage against a negative chart baseline', () => {
        // p0 !== 0 is the only guard in render(); a negative baseline (a
        // leveraged or short-style series that opens below zero) must divide
        // the same way a positive one does, sign and all.
        const signal = new FixedSignal('probe', style, {points});
        const negativeBase: LineDataPoint[] = [
            {date: '2026-01-01', value: -100},
            {date: '2026-01-02', value: -100},
        ];
        // pct = ((value - p0) / p0) * 100 = ((110 - -100) / -100) * 100 = -210
        expectValues(signal.render(negativeBase, 'percentage').data, [-210, -221]);
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

    it('only reads the date of every point after the first — the values are irrelevant', () => {
        // computePoints derives every point from baseData[0].value plus the
        // ELAPSED DAYS of each subsequent point's date. Whatever price the base
        // series actually had on those later dates must not leak in.
        const withRealPrices: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-04-02', value: 9999}, // 91 days — wildly different "price"
            {date: '2026-07-01', value: -5}, // even a negative one
        ];
        const withRepeatedPrices: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-04-02', value: 100},
            {date: '2026-07-01', value: 100},
        ];
        const signal = new LinearSignal('linear', style, {annualRate: 10, offset: 0});
        expect(values(signal.computePoints(withRealPrices))).toEqual(values(signal.computePoints(withRepeatedPrices)));
    });

    it('scales correctly across an irregular calendar with a leap day in the span', () => {
        // 2028 is a leap year: Jan 1 → Mar 1 is 31 + 29 = 60 days, and the gaps
        // between points are themselves irregular (30 then 29), not a fixed step.
        const leapSpan: LineDataPoint[] = [
            {date: '2028-01-01', value: 100},
            {date: '2028-01-31', value: 100}, // +30 days
            {date: '2028-03-01', value: 100}, // +29 more = 60 total
        ];
        const signal = new LinearSignal('linear', style, {annualRate: 36.5, offset: 0}); // rate/365 = 0.001 %/day
        const computed = values(signal.computePoints(leapSpan));

        expect(computed[0]).toBeCloseTo(100, 9);
        expect(computed[1]).toBeCloseTo(100 * (1 + 0.001 * 30), 9);
        expect(computed[2]).toBeCloseTo(100 * (1 + 0.001 * 60), 9);
    });

    it('reaches exactly zero at the minimum allowed rate after a full year', () => {
        // annualRate's declared min is -100 (a 100% decline): at t=1 the line
        // must land on exactly zero, not merely "close to" it — 1 + (-1) * 1 = 0.
        const signal = new LinearSignal('linear', style, {annualRate: -100, offset: 0});
        expect(values(signal.computePoints(YEAR))[1]).toBeCloseTo(0, 9);
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

    it('matches the closed form even when the steps between points are irregular', () => {
        // The existing "one step or many" test uses near-monthly steps; this
        // walks genuinely uneven gaps (10, 200, 60, 95 days — summing to a full
        // year) to prove the iterative daily-factor accumulation doesn't drift
        // away from Math.pow(1+rate, totalDays/365) when the steps are lumpy.
        const irregular: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-11', value: 100}, // +10
            {date: '2026-07-30', value: 100}, // +200
            {date: '2026-09-28', value: 100}, // +60
            {date: '2027-01-01', value: 100}, // +95 = 365 total
        ];
        const signal = new CompoundSignal('compound', style, {annualRate: 37, offset: 0});
        const computed = values(signal.computePoints(irregular));

        expect(computed.at(-1)).toBeCloseTo(100 * Math.pow(1.37, 1), 6);
        // And every intermediate point must match the closed form for ITS OWN
        // elapsed days from the start, not just the final one.
        expect(computed[2]).toBeCloseTo(100 * Math.pow(1.37, 210 / 365), 6);
    });

    it('only reads the date of every point after the first — the values are irrelevant', () => {
        const withRealPrices: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-04-02', value: 9999},
            {date: '2026-07-01', value: -5},
        ];
        const withRepeatedPrices: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-04-02', value: 100},
            {date: '2026-07-01', value: 100},
        ];
        const signal = new CompoundSignal('compound', style, {annualRate: 25, offset: 0});
        expect(values(signal.computePoints(withRealPrices))).toEqual(values(signal.computePoints(withRepeatedPrices)));
    });

    it('collapses to exactly zero at the minimum allowed rate, and stays flat at zero rate', () => {
        // annualRate's min is -100%: dailyFactor = (1 + -1)^(1/365) = 0, so the
        // very first non-start point already lands on exactly zero — not
        // asymptotically close, because 0 raised to any positive power is 0.
        const wipeout = new CompoundSignal('compound', style, {annualRate: -100, offset: 0});
        expect(values(wipeout.computePoints(YEAR))[1]).toBe(0);

        // annualRate = 0: dailyFactor = 1^(1/365) = 1, so the line is exactly
        // flat regardless of how many days elapse.
        const flat = new CompoundSignal('compound', style, {annualRate: 0, offset: 0});
        expect(values(flat.computePoints(YEAR))).toEqual([100, 100]);
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

    it('only reads the date of every point after the first — the values are irrelevant', () => {
        const withRealPrices: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-02', value: 42},
            {date: '2026-01-03', value: -7},
        ];
        const withRepeatedPrices: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-02', value: 100},
            {date: '2026-01-03', value: 100},
        ];
        const signal = new SineSignal('sine', style, {amplitude: 10, period: 4, offset: 0});
        expect(values(signal.computePoints(withRealPrices))).toEqual(values(signal.computePoints(withRepeatedPrices)));
    });

    it('holds its phase correctly across an irregular calendar with uneven gaps', () => {
        // period=4: days [0, 1, 6, 8] map to sin phases at day 0 (0), day 1
        // (quarter → peak), day 6 (== day 2 mod 4 → back to the zero crossing,
        // descending), day 8 (== day 0 mod 4 → zero crossing again). The gaps
        // between points (1, 5, 2 days) are deliberately irregular.
        const irregular: LineDataPoint[] = [
            {date: '2026-01-01', value: 100}, // day 0
            {date: '2026-01-02', value: 100}, // day 1  (+1)
            {date: '2026-01-07', value: 100}, // day 6  (+5)
            {date: '2026-01-09', value: 100}, // day 8  (+2)
        ];
        const signal = new SineSignal('sine', style, {amplitude: 10, period: 4, offset: 0});
        const computed = values(signal.computePoints(irregular));

        expect(computed[0]).toBeCloseTo(100, 6);
        expect(computed[1]).toBeCloseTo(110, 6);
        expect(computed[2]).toBeCloseTo(100 * (1 + 0.1 * Math.sin((2 * Math.PI * 6) / 4)), 9);
        expect(computed[3]).toBeCloseTo(100, 6);
    });

    it('reaches its extremes at the amplitude bounds declared by the control', () => {
        // amplitude's declared range is [0.1, 200]. At the quarter-period peak
        // the swing must scale exactly with amplitude at both ends.
        const tiny = new SineSignal('sine', style, {amplitude: 0.1, period: 4, offset: 0});
        expect(values(tiny.computePoints(cycle))[1]).toBeCloseTo(100 * 1.001, 9);

        const huge = new SineSignal('sine', style, {amplitude: 200, period: 4, offset: 0});
        expect(values(huge.computePoints(cycle))[1]).toBeCloseTo(100 * 3, 9);
        // A 200% amplitude swings symmetrically below zero at the trough too.
        expect(values(huge.computePoints(cycle))[3]).toBeCloseTo(100 * -1, 9);
    });

    it('aliases to a flat line at the minimum allowed period when sampled daily', () => {
        // period's declared min is 2 days. Sampled at daily granularity, every
        // integer day lands exactly on sin(π × day) = 0 — a zero crossing —
        // so the "wave" at this boundary is indistinguishable from a flat
        // line at the offset. Not a bug in the formula, but a real aliasing
        // trap at the edge of the declared range that a user could hit.
        const signal = new SineSignal('sine', style, {amplitude: 10, period: 2, offset: 0});
        const computed = values(signal.computePoints(cycle));
        computed.forEach((value) => expect(value).toBeCloseTo(100, 6));
    });

    it('names itself by amplitude and period', () => {
        expect(new SineSignal('sine', style, {amplitude: 10, period: 4}).getLabel()).toBe('Sine ±10% / 4d');
        expect(new SineSignal('sine', style, {}).getLabel()).toBe('Sine ±15% / 45d');
    });
});
