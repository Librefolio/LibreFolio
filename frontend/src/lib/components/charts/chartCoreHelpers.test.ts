import {describe, expect, it} from 'vitest';

import type {RenderedSignal} from '$lib/charts/signals';
import {assignOverlaySignalAxes, buildSecondaryYAxes, computeRightMargin} from './chartCoreHelpers';
import {buildSignalReferencePrimitives} from './lineChartHelpers';

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
        ...overrides,
    };
}

describe('canonical overlay axis and reference helpers', () => {
    it('shares indexes by canonical axis key and allocates multiple independent axes', () => {
        const assigned = assignOverlaySignalAxes([
            signal({id: 'price', axisKey: 'price', axisRole: 'price'}),
            signal({id: 'rsi', axisKey: 'rsi', axisRole: 'independent', axisMinimum: 0, axisMaximum: 100}),
            signal({id: 'stoch-k', axisKey: 'stoch-rsi', axisRole: 'independent'}),
            signal({id: 'stoch-d', axisKey: 'stoch-rsi', axisRole: 'independent'}),
        ]);

        expect(assigned.map((item) => item.yAxisIndex)).toEqual([0, 1, 2, 2]);

        const layout = buildSecondaryYAxes(assigned, false);
        expect(layout.axes).toHaveLength(2);
        expect(layout.nextAxisIndex).toBe(3);
        expect(layout.axes[0]).toMatchObject({
            min: 0,
            max: 100,
        });
        expect(layout.extraAxesCount).toBe(2);
        expect(computeRightMargin(3)).toBe(170);
    });

    it('preserves legacy explicit RSI/MACD indexes', () => {
        const assigned = assignOverlaySignalAxes([signal({id: 'legacy-rsi', yAxisIndex: 1}), signal({id: 'legacy-macd', yAxisIndex: 2})]);
        expect(assigned.map((item) => item.yAxisIndex)).toEqual([1, 2]);
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
});
