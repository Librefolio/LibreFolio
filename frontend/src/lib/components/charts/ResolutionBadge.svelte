<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {ChartResolution} from '$lib/components/charts/timeSeriesAggregation';

    interface Props {
        resolution: ChartResolution;
    }

    let {resolution}: Props = $props();

    const LABEL_KEY: Record<'weekly' | 'monthly', string> = {
        weekly: 'chart.resolution.weekly',
        monthly: 'chart.resolution.monthly',
    };
</script>

{#if resolution !== 'daily'}
    <span class="inline-flex items-center rounded-full border border-lf-subtle/70 bg-lf-card/90 px-2 py-1 text-[11px] font-medium text-lf-secondary shadow-sm" data-testid="chart-resolution-badge">
        {$t(LABEL_KEY[resolution])}
    </span>
{/if}
