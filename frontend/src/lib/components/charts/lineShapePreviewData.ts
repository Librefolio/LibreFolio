/**
 * The made-up chart the welcome tour shows while the user picks the shape of the lines (FB-3): one price that holds its value
 * for a few days at a time, so that segments, steps and the curve look different, and a signal over it, so that the
 * preview shows what the choice does to the lines on top of a price too. Nothing here is a financial quantity: it is a drawing.
 */

import type {RenderedSignal} from '$lib/components/charts/chartSignalContract';
import {SIGNAL_DEFAULT_PALETTE} from '$lib/theme/chartPalettes';
import type {LineDataPoint} from './LineChart.svelte';

const POINTS = 30;
/** The price changes every `HOLD_DAYS` days. */
const HOLD_DAYS = 3;
const FIRST_DAY = Date.UTC(2026, 0, 1);

function dayAt(index: number): string {
    return new Date(FIRST_DAY + index * 86_400_000).toISOString().slice(0, 10);
}

/** The made-up price: a slow wave, held for `HOLD_DAYS` days before it moves. */
export function previewPrice(): LineDataPoint[] {
    return Array.from({length: POINTS}, (_, index) => {
        const held = Math.floor(index / HOLD_DAYS) * HOLD_DAYS;
        return {date: dayAt(index), value: Math.round((100 + 8 * Math.sin(held / 4) + held * 0.35) * 100) / 100};
    });
}

/** A signal over the price: its average over the last three held values. Drawn on the same axis. */
export function previewSignal(price: readonly LineDataPoint[]): RenderedSignal {
    const data = price.map((point, index) => {
        const window = price.slice(Math.max(0, index - 5), index + 1);
        return {date: point.date, value: Math.round((window.reduce((sum, item) => sum + item.value, 0) / window.length) * 100) / 100};
    });
    return {id: 'preview:average', label: 'Average', data, color: SIGNAL_DEFAULT_PALETTE[1], lineWidth: 2, lineType: 'dashed', markerStart: null, markerEnd: null, yAxisIndex: 0, aggregationProfile: 'last_with_range'};
}
