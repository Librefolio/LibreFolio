<script lang="ts">
    /**
     * CorrelationPairsList — the matrix's answer, in words.
     *
     * A heatmap scales badly in exactly the place it matters. At twenty assets
     * it is 190 squares, the in-cell numbers are already suppressed, and
     * finding the two products that are the same bet means hunting for the
     * darkest square and then tracing two axes to read its names. The question
     * is a *ranking* question — *which pairs are redundant?* — and a ranking is
     * better served by a list.
     *
     * So this sits **beside** the matrix rather than replacing it: the matrix
     * shows the shape of the whole set, the list names the handful of pairs
     * that carry a decision. Taking away the picture the user was already
     * looking at would not be an improvement.
     *
     * Two lists, because they answer two different questions:
     *
     * - **correlated** — what you are holding twice;
     * - **offsetting** — what is actually pulling the other way, which is the
     *   only evidence on this page that diversification is doing anything.
     *
     * The second list is often empty. That emptiness is a finding, and it is
     * stated rather than hidden behind a collapsed section.
     */
    import {_ as t} from '$lib/i18n';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import type {RiskCorrelationOutput} from '$lib/risk/riskTypes';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {buildLookup, pairKey, topPairs, type CorrelationPair} from './correlationHelpers';

    interface Props {
        output: RiskCorrelationOutput;
        assetLabels?: ReadonlyMap<number, string>;
        limit?: number;
        /** `pairKey` of the pair shown in the matrix, if any. */
        selectedKey?: string | null;
        /** A click on a ranking entry: the matrix highlights the cell and opens its tooltip. */
        onselect?: (pair: CorrelationPair) => void;
    }

    let {output, assetLabels = new Map(), limit = 5, selectedKey = null, onselect}: Props = $props();

    let pairs = $derived(topPairs(output.asset_ids, buildLookup(output.cells), limit));

    /** Below this a pair offsets strongly enough to be called opposite, not merely offsetting. */
    const OPPOSITE = -0.7;

    function nameOf(assetId: number): string {
        return assetLabels.get(assetId) ?? `#${assetId}`;
    }

    /**
     * The heatmap's own polarity — blue for a positive pair (`#1d4ed8` at +1), red
     * for an offsetting one (`#b91c1c` at −1) — so the list and the matrix cannot
     * contradict each other. This docstring used to promise exactly that while the
     * list did the opposite (red for redundancy), so the same pair was red here and
     * dark blue in the matrix. The polarity is the heatmap's, not a verdict: flipping
     * it is one line in `CorrelationHeatmap`'s `visualMap`, and it has to move both
     * views together.
     */
    function toneClass(pair: CorrelationPair): string {
        return pair.value < 0 ? 'text-red-700 dark:text-red-300' : 'text-blue-700 dark:text-blue-300';
    }

    /** The short verdict next to the value: the names are on the line below, and the cell in the matrix. */
    function tag(pair: CorrelationPair): string {
        if (pair.value < 0) return $t(pair.value <= OPPOSITE ? 'risk.assetSet.pairs.tagOpposite' : 'risk.assetSet.pairs.tagOffsetting');
        return $t(pair.nearIdentical ? 'risk.assetSet.nearIdentical' : 'risk.assetSet.pairs.tagSimilar');
    }

    function tagClass(pair: CorrelationPair): string {
        return pair.value < 0 ? 'bg-red-50 text-red-800 dark:bg-red-900/40 dark:text-red-200' : 'bg-blue-50 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200';
    }
</script>

{#snippet ranking(entries: CorrelationPair[])}
    <ol class="mt-2 space-y-1">
        {#each entries as pair, index (pairKey(pair.rowAssetId, pair.columnAssetId))}
            {@const key = pairKey(pair.rowAssetId, pair.columnAssetId)}
            <li>
                <button
                    type="button"
                    class="w-full rounded-lg border px-2 py-1.5 text-left transition-colors {selectedKey === key ? 'border-slate-300 bg-slate-100 dark:border-slate-500 dark:bg-slate-700' : 'border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/60'}"
                    aria-pressed={selectedKey === key}
                    onclick={() => onselect?.(pair)}
                    data-testid="risk-correlation-pair-{pair.rowAssetId}-{pair.columnAssetId}"
                >
                    <span class="flex items-center gap-2">
                        <span class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">{index + 1}</span>
                        <span class="w-11 shrink-0 font-mono text-sm font-semibold tabular-nums {toneClass(pair)}">{pair.value.toFixed(2)}</span>
                        <span class="rounded px-1.5 py-0.5 text-[11px] font-medium {tagClass(pair)}" data-testid={pair.nearIdentical ? `risk-correlation-pair-near-identical-${pair.rowAssetId}-${pair.columnAssetId}` : undefined}>
                            {tag(pair)}
                        </span>
                    </span>
                    <!-- The names scroll when they do not fit, as they do across the app's tables
                         (`scrollOnOverflow`). No `title`: a native box that pops up when the mouse
                         rests covered the next entries, and the full pair is in the matrix tooltip. -->
                    <span class="mt-0.5 flex min-w-0 items-baseline gap-1 pl-7 text-xs text-slate-500 dark:text-slate-400">
                        <span use:scrollOnOverflow class="{overflowScrollTextClass} flex-1">{nameOf(pair.rowAssetId)}</span>
                        <span class="shrink-0 text-slate-400">↔</span>
                        <span use:scrollOnOverflow class="{overflowScrollTextClass} flex-1">{nameOf(pair.columnAssetId)}</span>
                    </span>
                </button>
            </li>
        {/each}
    </ol>
{/snippet}

<div class="space-y-4" data-testid="risk-correlation-pairs">
    <section data-testid="risk-correlation-pairs-correlated">
        <h4 class="text-sm font-semibold text-slate-800 dark:text-slate-100">{$t('risk.assetSet.pairs.correlatedTitle')}</h4>
        <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{$t('risk.assetSet.pairs.correlatedHint')}</p>
        {#if pairs.correlated.length === 0}
            <p class="mt-2 text-xs text-slate-500 dark:text-slate-400" data-testid="risk-correlation-pairs-correlated-empty">{$t('risk.assetSet.pairs.noneCorrelated')}</p>
        {:else}
            {@render ranking(pairs.correlated)}
        {/if}
    </section>

    <section data-testid="risk-correlation-pairs-offsetting">
        <h4 class="text-sm font-semibold text-slate-800 dark:text-slate-100">{$t('risk.assetSet.pairs.offsettingTitle')}</h4>
        <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{$t('risk.assetSet.pairs.offsettingHint')}</p>
        {#if pairs.offsetting.length === 0}
            <p class="mt-2 text-xs text-slate-500 dark:text-slate-400" data-testid="risk-correlation-pairs-offsetting-empty">{$t('risk.assetSet.pairs.noneOffsetting')}</p>
        {:else}
            {@render ranking(pairs.offsetting)}
        {/if}
    </section>
</div>
