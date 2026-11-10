<!--
  ReturnHistogram — the distribution of daily returns, with the VaR cut located in it.

  The second representation that was in the contract and in the generated client
  with zero readers: `return_bins` and `var_bin_edge`.

  ⚠️ WHY A CHART NOW (developer, 05/11/2026). This used to be forty CSS bars, and the
  comment that stood here argued a chart would add a registration and a bundle cost to
  render them. Both reasons were wrong: ECharts is imported whole in this app, nothing is
  registered, and what the bars lacked is exactly what a chart gives — an axis with the
  return thresholds (not only the two ends), a threshold line, and a tooltip that can say
  more than the interval. So the drawing is `ReturnHistogramChart` (`components/charts`),
  from the same data, and this file is the section around it.

  ⚠️ WHAT THE TWO SHADINGS MEAN — and why they are two.
  - `holdsCut` — the single bar the threshold falls inside. It says *where the
    number is*.
  - `belowCut` — every bar lying entirely at or beyond the threshold. It says
    *what mass the number is talking about*.
  The straddling bar is deliberately in neither: it is partly on both sides, and
  colouring it as tail would overstate the tail by up to one bin.

  Without the second shading a VaR is a marker with nothing behind it; without the
  first it is a region with no number. Both are computed in `l1Helpers`, under test.
  The tooltip says the same in words (where the bar lies against the threshold), because
  a colour alone is not a reading.

  ⚠️ A CANVAS SAYS NOTHING TO A TEST, so the section publishes what it drew: the bars'
  container carries `data-bin-count`, and a visually hidden list holds one entry per bin
  (`risk-l1-histogram-bin-<i>`, with `data-count`, `data-holds-cut`, `data-below-cut`)
  and the two ends of the axis. The list is also what a screen reader reads.

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import ReturnHistogramChart from '$lib/components/charts/ReturnHistogramChart.svelte';
    import type {HistogramBin} from '$lib/components/charts/returnHistogramChartHelpers';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {_ as t} from '$lib/i18n';

    import {formatShare} from '../shareFormat';
    import {axisPercent, figurePercent, type ReturnHistogram} from './l1Helpers';

    interface Props {
        histogram: ReturnHistogram | null;
        height?: string;
    }

    let {histogram, height = '140px'}: Props = $props();

    /**
     * The interval a bar covers, as the interval it is: closed on the left, open on the right, and closed on both sides for the last
     * bar, which keeps its upper edge. The separator is the one the figures are written with: a semicolon where the decimal mark is
     * a comma (`[−1,2%; −0,8%)`), a comma where it is a point.
     */
    function interval(bin: HistogramBin, index: number, math: boolean): string {
        const last = histogram !== null && index === histogram.bins.length - 1;
        const decimalComma = axisPercent(1.5).includes(',');
        const lower = axisPercent(bin.lowerBound);
        const upper = axisPercent(bin.upperBound);
        const close = last ? ']' : ')';
        if (!math) return `[${lower}${decimalComma ? '; ' : ', '}${upper}${close}`;
        // LaTeX: «%» is a comment mark and the comma after a digit is spaced as a list, so the figures are escaped as they are.
        const tex = (figure: string) => figure.replace(/%/g, '\\%').replace(/,/g, '{,}');
        return `$[${tex(lower)}${decimalComma ? ';\\,' : '{,}\\,'}${tex(upper)}${close}$`;
    }

    /**
     * What a bar's tooltip says (D-B6a, 31/10/2026; F-5, 05/11/2026; F8, 06/11/2026): a few ordered lines — the interval, how many days
     * fell in it and their share of the observed days (written by the share rule), and, when a threshold was published, where the
     * bar lies against it. The share is a plain ratio of counts, the bar's own over the histogram's total: it is not a financial
     * quantity and nothing else reads it.
     *
     * Derived functions, so a language switch (the `$t` store changing) hands the chart new ones and redraws its tooltip. `math`
     * gives the interval as LaTeX for the chart (KaTeX); the hidden list, which a screen reader and a test read, has it as text.
     */
    const linesOf = $derived.by(() => {
        const observations = histogram?.observations ?? 0;
        const cut = histogram?.cut ?? null;
        const say = $t;
        return (math: boolean) =>
            (bin: HistogramBin, index: number): string[] => {
                const lines = [interval(bin, index, math), say('risk.levels.l1.histogram.binDays', {values: {count: bin.count, share: formatShare(observations > 0 ? bin.count / observations : 0, 1)}})];
                if (cut !== null) {
                    const where = bin.holdsCut ? 'holds' : bin.belowCut ? 'beyond' : 'above';
                    lines.push(say(`risk.levels.l1.histogram.position.${where}`, {values: {value: figurePercent(cut / 100)}}));
                }
                return lines;
            };
    });
    const tooltipLines = $derived(linesOf(true));
    const plainLines = $derived(linesOf(false));

    /** The threshold's label on the chart: a figure, not a position, so a cut of −0.04% keeps its sign (D380). */
    const cutLabel = $derived(histogram?.cut == null ? '' : $t('risk.levels.l1.histogram.cutLine', {values: {value: figurePercent(histogram.cut / 100)}}));
</script>

<section class="space-y-1" data-testid="risk-l1-histogram">
    <div class="flex items-center gap-1">
        <h4 class="text-sm font-medium text-lf-secondary">{$t('risk.levels.l1.histogram.title')}</h4>
        <DocsLink path="financial-theory/technical-analysis/risk-metrics/value-at-risk/" label={$t('risk.levels.l1.histogram.title')} testId="risk-l1-histogram-docs" />
    </div>

    {#if !histogram}
        <p class="text-xs text-lf-muted" data-testid="risk-l1-histogram-empty">{$t('risk.levels.l1.histogram.empty')}</p>
    {:else}
        <div data-testid="risk-l1-histogram-bars" data-bin-count={histogram.bins.length}>
            <ReturnHistogramChart bins={histogram.bins} cut={histogram.cut} formatAxis={axisPercent} {cutLabel} {tooltipLines} {height} testId="risk-l1-histogram-chart" />
            <!-- What the canvas drew, as text: for a screen reader, and for a test that cannot read pixels. -->
            <ul class="sr-only" data-testid="risk-l1-histogram-bins">
                {#each histogram.bins as bin, index (index)}
                    <li data-testid="risk-l1-histogram-bin-{index}" data-holds-cut={bin.holdsCut} data-below-cut={bin.belowCut} data-count={bin.count}>{plainLines(bin, index).join('. ')}</li>
                {/each}
            </ul>
            <p class="sr-only">
                <span data-testid="risk-l1-histogram-axis-min">{axisPercent(histogram.bins[0].lowerBound)}</span>
                <span data-testid="risk-l1-histogram-axis-max">{axisPercent(histogram.bins[histogram.bins.length - 1].upperBound)}</span>
            </p>
        </div>

        <p class="text-xs text-lf-muted">
            <span data-testid="risk-l1-histogram-observations">{$t('risk.levels.l1.histogram.observations', {values: {count: histogram.observations}})}</span>
            <!-- `=== null`, never a falsy test: a threshold of exactly zero sits at
                 break-even and is a real answer, not a missing one. -->
            {#if histogram.cut === null}
                <span class="ml-1" data-testid="risk-l1-histogram-nocut">— {$t('risk.levels.l1.histogram.noCut')}</span>
            {:else}
                <!-- A figure, not a position: a threshold of −0.04% keeps its sign (D380). -->
                <span class="ml-1 font-medium text-lf-warning" data-testid="risk-l1-histogram-cut">— {$t('risk.levels.l1.histogram.cut', {values: {value: figurePercent(histogram.cut / 100)}})}</span>
            {/if}
        </p>
    {/if}
</section>
