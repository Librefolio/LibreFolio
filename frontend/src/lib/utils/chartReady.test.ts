// @vitest-environment jsdom
/**
 * `attachChartReady` publishes when a chart has drawn, and hands its instance to the container (Y2-I63): a spec that puts the pointer on a known
 * day reads the series the chart drew and the pixel of a day from `__lfChart`, because ECharts is not reachable from the page any other way.
 */
import {describe, expect, it} from 'vitest';
import {attachChartReady} from './chartReady';

function chart() {
    const handlers: Array<() => void> = [];
    return {instance: {on: (_event: string, handler: () => void) => handlers.push(handler)}, finish: () => handlers.forEach((handler) => handler())};
}

describe('attachChartReady', () => {
    it('says the chart is not ready until it has drawn, and counts every pass', () => {
        const container = document.createElement('div');
        const {instance, finish} = chart();
        attachChartReady(instance, container, 'test');
        expect(container.dataset.chartReady).toBe('false');
        expect(container.dataset.chartRenders).toBe('0');
        finish();
        finish();
        expect(container.dataset.chartReady).toBe('true');
        expect(container.dataset.chartRenders).toBe('2');
    });

    it('hands the instance to the container, for a spec that reads what the chart drew', () => {
        const container = document.createElement('div');
        const {instance} = chart();
        attachChartReady(instance, container, 'test');
        expect((container as unknown as {__lfChart?: unknown}).__lfChart).toBe(instance);
    });

    it('does nothing without a container', () => {
        const {instance} = chart();
        expect(() => attachChartReady(instance, null, 'test')).not.toThrow();
    });
});
