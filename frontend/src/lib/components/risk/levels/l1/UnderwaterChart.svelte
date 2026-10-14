<!--
  UnderwaterChart — how far below its last peak the portfolio sat, day by day.

  The curve nobody had drawn: `underwater_series` has been in the contract and in
  the generated client for the whole of this campaign with **zero readers**.

  ⚠️ THREE PROPS ARE SET HERE AND NONE OF THEM IS COSMETIC.

  - `yAxisMode='include0'` — with the default `'auto'` ECharts fits the axis to
    the data range, and a portfolio that never regained its peak inside the window
    would be drawn without a zero line at all. Zero *is* the peak: losing it loses
    the only reference the chart exists to give.
  - `viewMode='percentage'` + values pre-multiplied by 100 — percentage mode
    relabels the axis and moves the baseline to zero, but converts nothing
    (`LineChart.svelte:373` plots `d.value` verbatim). The scaling is done in
    `buildUnderwater`, and the two must stay together: either alone draws a chart
    that is wrong by a factor of a hundred while looking perfectly plausible.
  - `colorByBaseline={false}` — every underwater value is ≤ 0, so the default
    `true` paints the entire curve red and the green branch never appears. That
    is not a bug, but it spends a colour on a fact the reader already has. All
    three existing percentage callers in this codebase pass `false`; this follows
    them rather than inventing a fourth convention.

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import LineChart from '$lib/components/charts/LineChart.svelte';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {_ as t} from '$lib/i18n';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    import type {UnderwaterPoint} from './l1Helpers';

    interface Props {
        points: UnderwaterPoint[];
        /**
         * Ulcer index as a decimal ratio, shown as this chart's caption.
         *
         * It is placed here rather than on a card of its own deliberately: on its
         * own it is a dimensionless number with no reading, and the curve above it
         * is literally the thing it summarises — the root-mean-square depth of
         * exactly this shape.
         */
        ulcerIndex: number | null;
        height?: string;
    }

    let {points, ulcerIndex, height = '220px'}: Props = $props();

    const ulcerCaption = $derived(ulcerIndex === null ? null : $t('risk.levels.l1.tails.ulcerIndex', {values: {value: formatPercent(ulcerIndex, {scale: 100, signed: false, digits: 2})}}));
</script>

<section class="space-y-1" data-testid="risk-l1-underwater">
    <div class="flex items-center gap-1">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('risk.levels.l1.underwater.title')}</h4>
        <DocsLink path="financial-theory/technical-analysis/risk-metrics/current-drawdown/" label={$t('risk.levels.l1.underwater.title')} testId="risk-l1-underwater-docs" />
    </div>

    {#if points.length === 0}
        <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l1-underwater-empty">{$t('risk.levels.l1.underwater.empty')}</p>
    {:else}
        <div data-testid="risk-l1-underwater-chart" data-point-count={points.length}>
            <LineChart data={points} currency="%" viewMode="percentage" yAxisMode="include0" colorByBaseline={false} showGradient={false} {height} />
        </div>
        {#if ulcerCaption}
            <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l1-ulcer">
                <span class="tabular-nums font-medium text-gray-700 dark:text-gray-300">{ulcerCaption}</span>
                <span class="ml-1">— {$t('risk.levels.l1.tails.ulcerIndexHint')}</span>
                <DocsLink path="financial-theory/technical-analysis/risk-metrics/ulcer-index/" label={$t('risk.levels.l1.tails.ulcerIndexHint')} testId="risk-l1-ulcer-docs" />
            </p>
        {/if}
    {/if}
</section>
