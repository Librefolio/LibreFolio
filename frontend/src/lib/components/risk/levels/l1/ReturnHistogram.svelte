<!--
  ReturnHistogram — the distribution of daily returns, with the VaR cut located in it.

  The second representation that was in the contract and in the generated client
  with zero readers: `return_bins` and `var_bin_edge`.

  ⚠️ WHY CSS BARS AND NOT A CHART LIBRARY.
  A histogram of pre-binned counts needs no axis engine, no tooltip layer and no
  resize observer: the server has already done the binning, so the whole drawing
  is "width from the bounds, height from the count". Reaching for ECharts here
  would add a catalogue registration and a bundle cost to render forty divs.

  ⚠️ WHAT THE TWO SHADINGS MEAN — and why they are two.
  - `holdsCut` — the single bar the threshold falls inside. It says *where the
    number is*.
  - `belowCut` — every bar lying entirely at or beyond the threshold. It says
    *what mass the number is talking about*.
  The straddling bar is deliberately in neither: it is partly on both sides, and
  colouring it as tail would overstate the tail by up to one bin.

  Without the second shading a VaR is a marker with nothing behind it; without the
  first it is a region with no number. Both are computed in `l1Helpers`, under test.

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {_ as t} from '$lib/i18n';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    import type {ReturnHistogram} from './l1Helpers';

    interface Props {
        histogram: ReturnHistogram | null;
        height?: string;
    }

    let {histogram, height = '120px'}: Props = $props();

    /**
     * A percent-unit value with the typographic minus this panel uses throughout.
     *
     * `formatPercent` emits an ASCII hyphen, so the magnitude is formatted and the
     * sign prefixed here rather than letting two different minus characters appear
     * a few pixels apart.
     */
    function axisPercent(value: number): string {
        return `${value < 0 ? '−' : ''}${formatPercent(Math.abs(value), {signed: false, digits: 1})}`;
    }

    function barClass(bin: {holdsCut: boolean; belowCut: boolean}): string {
        if (bin.holdsCut) return 'bg-amber-500 dark:bg-amber-400';
        if (bin.belowCut) return 'bg-red-400/80 dark:bg-red-500/80';
        return 'bg-gray-300 dark:bg-slate-600';
    }
</script>

<section class="space-y-1" data-testid="risk-l1-histogram">
    <div class="flex items-center gap-1">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('risk.levels.l1.histogram.title')}</h4>
        <DocsLink path="financial-theory/technical-analysis/risk-metrics/value-at-risk/" label={$t('risk.levels.l1.histogram.title')} testId="risk-l1-histogram-docs" />
    </div>

    {#if !histogram}
        <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l1-histogram-empty">{$t('risk.levels.l1.histogram.empty')}</p>
    {:else}
        <div class="flex items-end gap-px" style="height: {height};" data-testid="risk-l1-histogram-bars" data-bin-count={histogram.bins.length}>
            {#each histogram.bins as bin, index (index)}
                <!-- Width from the real bounds, not from a constant: the schema
                     guarantees only that lower bounds ascend, so a non-uniform
                     grid must draw correctly rather than draw evenly. -->
                <div
                    class="flex h-full items-end"
                    style="flex: {bin.upperBound - bin.lowerBound} 1 0%;"
                    data-testid="risk-l1-histogram-bin-{index}"
                    data-holds-cut={bin.holdsCut}
                    data-below-cut={bin.belowCut}
                    data-count={bin.count}
                    title="{axisPercent(bin.lowerBound)} … {axisPercent(bin.upperBound)}"
                >
                    <!-- A bar with observations never rounds away to nothing: an
                         invisible bar and an empty bin must not look the same. -->
                    <div class="w-full rounded-t-sm {barClass(bin)}" style="height: {bin.count > 0 ? Math.max(bin.share * 100, 2) : 0}%;"></div>
                </div>
            {/each}
        </div>

        <div class="flex justify-between text-[10px] text-gray-400 tabular-nums dark:text-gray-500">
            <span>{axisPercent(histogram.bins[0].lowerBound)}</span>
            <span>{axisPercent(histogram.bins[histogram.bins.length - 1].upperBound)}</span>
        </div>

        <p class="text-xs text-gray-500 dark:text-gray-400">
            <span data-testid="risk-l1-histogram-observations">{$t('risk.levels.l1.histogram.observations', {values: {count: histogram.observations}})}</span>
            <!-- `=== null`, never a falsy test: a threshold of exactly zero sits at
                 break-even and is a real answer, not a missing one. -->
            {#if histogram.cut === null}
                <span class="ml-1" data-testid="risk-l1-histogram-nocut">— {$t('risk.levels.l1.histogram.noCut')}</span>
            {:else}
                <span class="ml-1 font-medium text-amber-600 dark:text-amber-400" data-testid="risk-l1-histogram-cut">— {$t('risk.levels.l1.histogram.cut', {values: {value: axisPercent(histogram.cut)}})}</span>
            {/if}
        </p>
    {/if}
</section>
