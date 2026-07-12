/**
 * RsiSignal.test.ts — Unit tests for RsiSignal.renderMulti() zone-segment merging.
 *
 * @module charts/signals/__tests__/RsiSignal.test
 */
import {describe, expect, it} from 'vitest';

import {RsiSignal} from '../RsiSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

function makeSignal(overrides: Record<string, unknown> = {}): RsiSignal {
    return new RsiSignal('rsi-test', {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null}, {period: 14, overbought: 70, oversold: 30, ...overrides});
}

/** Build a synthetic daily price series oscillating to force RSI in/out of zones repeatedly. */
function buildOscillatingPrices(cycles: number, up: number, down: number): LineDataPoint[] {
    const points: LineDataPoint[] = [];
    let value = 100;
    let idx = 0;
    for (let c = 0; c < cycles; c++) {
        for (let i = 0; i < up; i++) {
            value += 5;
            points.push({date: `2000-01-${String((idx % 28) + 1).padStart(2, '0')}`, value});
            idx++;
        }
        for (let i = 0; i < down; i++) {
            value -= 5;
            points.push({date: `2000-01-${String((idx % 28) + 1).padStart(2, '0')}`, value});
            idx++;
        }
    }
    return points;
}

describe('RsiSignal.renderMulti', () => {
    it('produces a small number of segments for a mild, mostly-neutral series', () => {
        const signal = makeSignal();
        const prices = buildOscillatingPrices(3, 5, 5);
        const result = signal.renderMulti(prices, 'absolute');
        expect(result.length).toBeGreaterThan(0);
        expect(result.length).toBeLessThan(20);
    });

    it('caps the segment count for a pathologically choppy series (perf guard)', () => {
        // Many short up/down cycles push RSI in and out of overbought/oversold
        // repeatedly, simulating decades of volatile daily prices with many
        // threshold crossings — without the merge cap, buildOverlaySignalSeries()
        // would turn each crossing into its own full-length ECharts series.
        const signal = makeSignal();
        const prices = buildOscillatingPrices(400, 2, 2);
        const result = signal.renderMulti(prices, 'absolute');
        expect(result.length).toBeLessThanOrEqual(100);
    });

    it('still returns a rendered signal with valid data for a very short series', () => {
        const signal = makeSignal();
        const prices: LineDataPoint[] = [
            {date: '2000-01-01', value: 100},
            {date: '2000-01-02', value: 105},
        ];
        const result = signal.renderMulti(prices, 'absolute');
        expect(result.length).toBeGreaterThan(0);
        expect(result[0].data.length).toBeGreaterThan(0);
    });
});
