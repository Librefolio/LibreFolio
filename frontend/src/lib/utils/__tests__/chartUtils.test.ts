/**
 * chartUtils.ts — `normalizeToPercentage` and the base a sampled series is measured from (Z-29b, MF n3).
 */
import {describe, expect, it} from 'vitest';

import {normalizeToPercentage} from '../chartUtils';

const series = [
    {date: '2026-01-11', value: 104},
    {date: '2026-01-18', value: 110},
    {date: '2026-01-25', value: 95},
];

describe('normalizeToPercentage', () => {
    it('measures from the first present non-zero value, as ever', () => {
        expect(normalizeToPercentage(series).map((point) => Math.round(point.value * 100) / 100)).toEqual([0, 5.77, -8.65]);
    });

    it('measures from the base it is given when the series hides the day it starts on: a sampled series opens on its first bucket’s end', () => {
        // The fill's first day F was worth 100; the first bucket ends on 104.
        expect(normalizeToPercentage(series, 100).map((point) => Math.round(point.value * 100) / 100)).toEqual([4, 10, -5]);
    });

    it('falls back to the first present value on an unusable base: absent, null, NaN, infinite or zero', () => {
        const own = normalizeToPercentage(series);
        for (const base of [undefined, null, Number.NaN, Number.POSITIVE_INFINITY, 0]) {
            expect(normalizeToPercentage(series, base), String(base)).toEqual(own);
        }
    });

    it('keeps missing points as gaps and leaves an empty series alone', () => {
        const withGap = [{date: '2026-01-11', value: 0, missing: true}, ...series];

        expect(normalizeToPercentage(withGap, 100)[0]).toEqual(withGap[0]);
        expect(normalizeToPercentage([], 100)).toEqual([]);
    });
});
