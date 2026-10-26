// @vitest-environment jsdom
/**
 * PriceChartCompact — the aggregation badge of a card's chart (lot Y5-F3).
 *
 * The detail page shows `ResolutionBadge` (`chart-resolution-badge`) over its chart when it draws weekly or monthly points;
 * a card drew nothing, though the backend samples a card's series (`max_points`) and `LineChart` aggregates what it is given
 * for the width of its plot. The contract, after the cure:
 * - `PriceChartCompact` takes an optional `sampledResolution` (`daily` | `weekly` | `monthly`): the step the backend already
 *   applied to `data`. `LineChart` takes an optional callback, `onresolution(resolution)`, which it calls in compact mode
 *   with the static resolution it chose for the data it was given; `PriceChartCompact` hands it one.
 * - The card shows the badge with the COARSEST of `sampledResolution` and the last resolution `LineChart` reported
 *   (daily < weekly < monthly), and nothing when that is daily. The badge publishes the step it says as `data-resolution`
 *   (no case reads its translated text).
 *
 * How it is tested: the real `PriceChartCompact` and `ResolutionBadge`, real i18n; `LineChart` stood in by a recorder of the
 * props it is handed (the `FxCard.primaryView.test.ts` pattern), so a case can call the `onresolution` it received, as the
 * chart does when it has chosen.
 *
 * Red today: no `sampledResolution`, no `onresolution` handed to the chart, no badge on a card.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next to
 * `FxCard.test.ts`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const charts = vi.hoisted(() => {
    const mounts: Array<{element: HTMLElement; live: Record<string, unknown>}> = [];
    function LineChartStandIn(anchor: ChildNode, props: Record<string, unknown>): void {
        const element = document.createElement('div');
        element.setAttribute('data-testid', 'compact-line-chart');
        anchor.before(element);
        mounts.push({element, live: props});
    }
    return {mounts, LineChartStandIn};
});

vi.mock('$lib/components/charts/LineChart.svelte', () => ({default: charts.LineChartStandIn}));

import {tick, type ComponentProps} from 'svelte';
import {render, screen, setupI18n} from '$test/component';
import type {LineDataPoint} from './LineChart.svelte';
import PriceChartCompact from './PriceChartCompact.svelte';

type Resolution = 'daily' | 'weekly' | 'monthly';

const DATA: LineDataPoint[] = [
    {date: '2026-03-02', value: 100},
    {date: '2026-03-03', value: 110},
    {date: '2026-03-04', value: 105},
];

function mount(props: Record<string, unknown> = {}) {
    render(PriceChartCompact, {data: DATA, ...props} as unknown as ComponentProps<typeof PriceChartCompact>);
}

/** What the one chart of the card was handed. */
function chart(): Record<string, unknown> {
    expect(charts.mounts, 'the card mounts one chart').toHaveLength(1);
    return charts.mounts[0].live;
}

/** The chart reports the resolution it chose, as `LineChart` does in compact mode. */
async function chartReports(resolution: Resolution): Promise<void> {
    const onresolution = chart().onresolution;
    expect(typeof onresolution, 'PriceChartCompact hands its chart an onresolution callback').toBe('function');
    (onresolution as (resolution: Resolution) => void)(resolution);
    await tick();
}

const badge = () => screen.queryByTestId('chart-resolution-badge');

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    charts.mounts.length = 0;
});

describe('PriceChartCompact — the aggregation badge (Y5-F3)', () => {
    it('shows no badge by default', () => {
        mount();

        expect(badge()).toBeNull();
    });

    it('shows the badge for a series the backend sampled weekly', () => {
        mount({sampledResolution: 'weekly'});

        expect(badge(), 'a weekly sampled series is told on the card').not.toBeNull();
        expect(badge()).toHaveAttribute('data-resolution', 'weekly');
    });

    it('shows the badge for a series the backend sampled monthly', () => {
        mount({sampledResolution: 'monthly'});

        expect(badge()).toHaveAttribute('data-resolution', 'monthly');
    });

    it('shows no badge for a daily series that the chart did not report', () => {
        mount({sampledResolution: 'daily'});

        expect(badge()).toBeNull();
    });

    it('shows the badge when only the chart aggregates: it reports weekly over a daily series', async () => {
        mount({sampledResolution: 'daily'});

        await chartReports('weekly');

        expect(badge(), 'what the chart aggregates for the plot is told too').not.toBeNull();
        expect(badge()).toHaveAttribute('data-resolution', 'weekly');
    });

    it('shows the coarser of the two: the chart reports monthly over a weekly sampled series', async () => {
        mount({sampledResolution: 'weekly'});

        await chartReports('monthly');

        expect(badge()).toHaveAttribute('data-resolution', 'monthly');
    });

    it('shows the coarser of the two: the chart reports weekly over a monthly sampled series', async () => {
        mount({sampledResolution: 'monthly'});

        await chartReports('weekly');

        expect(badge()).toHaveAttribute('data-resolution', 'monthly');
    });

    it('shows no badge when the chart reports daily alone', async () => {
        mount();

        await chartReports('daily');

        expect(badge()).toBeNull();
    });

    it('follows the last report: weekly, then daily again, takes the badge away', async () => {
        mount();

        await chartReports('weekly');
        expect(badge()).toHaveAttribute('data-resolution', 'weekly');

        await chartReports('daily');
        expect(badge(), 'the chart changed its mind: the card does not keep the old step').toBeNull();
    });

    it('guard: the sampled step still shows when the chart then reports a finer one', async () => {
        mount({sampledResolution: 'monthly'});

        await chartReports('daily');

        expect(badge()).toHaveAttribute('data-resolution', 'monthly');
    });
});
