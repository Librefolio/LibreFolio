import {describe, expect, it} from 'vitest';
import type * as echarts from 'echarts';
import {applyLineShape, DEFAULT_LINE_SHAPE, drawsSteps, effectiveLineShape, isLineShape, LINE_SHAPES, lineShapeOptions} from './lineShape';

const line = (extra: Record<string, unknown> = {}) => ({type: 'line', name: 'a', data: [], ...extra}) as echarts.SeriesOption;

describe('lineShape', () => {
    it('segments are the default and the three shapes are the whole list', () => {
        expect(DEFAULT_LINE_SHAPE).toBe('segments');
        expect(LINE_SHAPES).toEqual(['segments', 'steps', 'spline']);
        expect(isLineShape('spline')).toBe(true);
        expect(isLineShape('smooth')).toBe(false);
        expect(isLineShape(undefined)).toBe(false);
    });

    it('each shape sets all the keys, so changing shape overwrites the last one', () => {
        expect(lineShapeOptions('segments')).toEqual({step: false, smooth: false});
        expect(lineShapeOptions('steps')).toEqual({step: 'end', smooth: false});
        expect(lineShapeOptions('spline')).toEqual({step: false, smooth: true, smoothMonotone: 'x'});
    });

    it('draws steps only where the points hold a value', () => {
        expect(effectiveLineShape('steps', true)).toBe('steps');
        expect(effectiveLineShape('steps', false)).toBe('segments');
        expect(effectiveLineShape('spline', false)).toBe('spline');
        expect(drawsSteps('steps', false)).toBe(false);
        expect(drawsSteps('steps')).toBe(true);
    });

    it('applies the shape to lines only and leaves the other series alone', () => {
        const bar = {type: 'bar', data: []} as echarts.SeriesOption;
        const [shaped, untouched] = applyLineShape([line({smooth: true}), bar], 'steps');
        expect(shaped).toMatchObject({step: 'end', smooth: false});
        expect(untouched).toBe(bar);
    });

    it('does not mutate the series it is given', () => {
        const original = line();
        applyLineShape([original], 'spline');
        expect(original).not.toHaveProperty('step');
    });

    it('turns steps into segments for a line of true values and for a bucketed chart', () => {
        const mwrr = line({name: 'mwrr'});
        const [trueLine, steppedLine] = applyLineShape([mwrr, line()], 'steps', {isTrueValues: (entry) => entry.name === 'mwrr'});
        expect(trueLine).toMatchObject({step: false});
        expect(steppedLine).toMatchObject({step: 'end'});
        expect(applyLineShape([line()], 'steps', {holdsValue: false})[0]).toMatchObject({step: false});
    });

    it('a spline stays a spline for a line of true values', () => {
        expect(applyLineShape([line()], 'spline', {isTrueValues: () => true})[0]).toMatchObject({smooth: true, smoothMonotone: 'x'});
    });
});
