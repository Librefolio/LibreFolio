import {describe, expect, it} from 'vitest';
import {previewPrice, previewSignal} from './lineShapePreviewData';

describe('the welcome page example chart (Y2 FB-3)', () => {
    it('is a price that holds its value for a few days, so the three shapes look different', () => {
        const price = previewPrice();
        const distinct = new Set(price.map((point) => point.value));
        expect(price.length).toBeGreaterThan(distinct.size);
        expect(distinct.size).toBeGreaterThan(5);
        expect(price.map((point) => point.date)).toEqual([...price.map((point) => point.date)].sort());
    });

    it('is the same every time: a drawing, not a random sample', () => {
        expect(previewPrice()).toEqual(previewPrice());
    });

    it('has a signal on the same days as the price, drawn over it', () => {
        const price = previewPrice();
        const signal = previewSignal(price);
        expect(signal.data.map((point) => point.date)).toEqual(price.map((point) => point.date));
        expect(signal.yAxisIndex).toBe(0);
    });
});
