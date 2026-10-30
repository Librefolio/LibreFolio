// @vitest-environment jsdom
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import ChartAestheticsSection from './ChartAestheticsSection.svelte';

/** Y2 FB-3: the line shape is a parameter of the chart's settings where the page keeps one shape per chart (the asset and FX details). */

beforeAll(async () => {
    await setupI18n();
});

describe('ChartAestheticsSection — line shape row (Y2 FB-3)', () => {
    it('is not shown on a page that keeps no shape per chart', () => {
        render(ChartAestheticsSection, {});
        expect(screen.queryByTestId('chart-aesthetic-line-shape-row')).toBeNull();
    });

    it('shows the shape in force and tells the page which one the user picks', async () => {
        const onlineshapechange = vi.fn();
        render(ChartAestheticsSection, {lineShape: 'steps', onlineshapechange});
        expect(screen.getByTestId('chart-aesthetic-line-shape')).toHaveAttribute('data-value', 'steps');
        await fireEvent.click(screen.getByTestId('chart-aesthetic-line-shape-spline'));
        expect(onlineshapechange).toHaveBeenCalledExactlyOnceWith('spline');
    });
});
