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

    it('badges the row Global while the shape follows the global choice, and only then', async () => {
        const {rerender} = render(ChartAestheticsSection, {lineShape: 'segments', lineShapeFollowsGlobal: true, onlineshapechange: vi.fn()});
        expect(screen.getByTestId('chart-aesthetic-line-shape-badge-global')).toHaveAttribute('data-source', 'global');

        await rerender({lineShape: 'segments', lineShapeFollowsGlobal: false, onlineshapechange: vi.fn()});
        expect(screen.queryByTestId('chart-aesthetic-line-shape-badge-global')).toBeNull();
    });

    it('shows no badge by default', () => {
        render(ChartAestheticsSection, {lineShape: 'steps', onlineshapechange: vi.fn()});
        expect(screen.queryByTestId('chart-aesthetic-line-shape-badge-global')).toBeNull();
    });
});
