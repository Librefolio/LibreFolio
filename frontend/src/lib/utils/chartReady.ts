/**
 * The one signal ECharts does not give us: "the drawing is finished".
 *
 * ECharts emits `finished` once a render pass — including its animations — has
 * completed, but nothing in the DOM says so. Without that, anybody who needs to
 * know whether a chart is showing real data or a half-drawn frame has to guess,
 * and guessing means sleeping. That is where ~15 of the suite's `waitForTimeout`
 * calls come from.
 *
 * It matters beyond the tests: a chart caught mid-animation *looks* like a
 * finished chart with different numbers. Publishing the state makes the
 * difference observable instead of assumed.
 *
 * Two attributes land on the container:
 *   - `data-chart-ready` — `'false'` from init, `'true'` after the first render;
 *   - `data-chart-renders` — how many render passes have completed, so a
 *     *re*-render (new range, new series) can be awaited without a stale `true`
 *     letting the reader through too early.
 *
 * The container also keeps the chart instance as `__lfChart`, for a spec that needs what the chart really drew and where (the series it
 * holds, the pixel of a day); the app never reads it.
 */
import {notify} from '$lib/stores/app/notify.svelte';

type MinimalChart = {
    on: (event: string, handler: () => void) => void;
};

export function attachChartReady(instance: MinimalChart, container: HTMLElement | null | undefined, name: string): void {
    if (!container) return;

    // The instance, for a spec that needs the series a chart actually drew (`e2e/fixtures/timeAxisTooltip.ts`); never read by the app
    (container as unknown as Record<string, unknown>).__lfChart = instance;
    container.dataset.chartReady = 'false';
    container.dataset.chartRenders = '0';

    instance.on('finished', () => {
        const renders = Number(container.dataset.chartRenders ?? '0') + 1;
        container.dataset.chartRenders = String(renders);
        container.dataset.chartReady = 'true';
        notify({name: 'chart.rendered', detail: {chart: name, renders}});
    });
}
