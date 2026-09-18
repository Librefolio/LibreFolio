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
    import type {RiskCorrelationOutput} from '$lib/risk/riskTypes';
    import {buildLookup, topPairs, type CorrelationPair} from './correlationHelpers';

    interface Props {
        output: RiskCorrelationOutput;
        assetLabels?: ReadonlyMap<number, string>;
        limit?: number;
    }

    let {output, assetLabels = new Map(), limit = 5}: Props = $props();

    let pairs = $derived(topPairs(output.asset_ids, buildLookup(output.cells), limit));

    function nameOf(assetId: number): string {
        return assetLabels.get(assetId) ?? `#${assetId}`;
    }

    /** Red for redundancy, blue for offset — the same axis as the heatmap's scale, so the two views cannot contradict each other. */
    function toneClass(pair: CorrelationPair): string {
        if (pair.value < 0) return 'text-blue-700 dark:text-blue-300';
        if (pair.band === 'high') return 'text-red-700 dark:text-red-300';
        return 'text-slate-700 dark:text-slate-300';
    }
</script>

<div class="space-y-4" data-testid="risk-correlation-pairs">
    <section data-testid="risk-correlation-pairs-correlated">
        <h4 class="text-sm font-semibold text-slate-800 dark:text-slate-100">{$t('risk.assetSet.pairs.correlatedTitle')}</h4>
        <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{$t('risk.assetSet.pairs.correlatedHint')}</p>
        {#if pairs.correlated.length === 0}
            <p class="mt-2 text-xs text-slate-500 dark:text-slate-400" data-testid="risk-correlation-pairs-correlated-empty">{$t('risk.assetSet.pairs.noneCorrelated')}</p>
        {:else}
            <ul class="mt-2 space-y-1">
                {#each pairs.correlated as pair (`${pair.rowAssetId}-${pair.columnAssetId}`)}
                    <li class="flex items-baseline justify-between gap-3 rounded px-2 py-1 text-sm odd:bg-slate-50 dark:odd:bg-slate-800/40" data-testid="risk-correlation-pair-{pair.rowAssetId}-{pair.columnAssetId}">
                        <span class="min-w-0 truncate text-slate-700 dark:text-slate-200">
                            {nameOf(pair.rowAssetId)} <span class="text-slate-400">↔</span>
                            {nameOf(pair.columnAssetId)}
                        </span>
                        <span class="flex shrink-0 items-baseline gap-2">
                            {#if pair.nearIdentical}
                                <span class="rounded bg-red-100 px-1.5 py-0.5 text-[11px] font-medium text-red-800 dark:bg-red-900/40 dark:text-red-200" data-testid="risk-correlation-pair-near-identical-{pair.rowAssetId}-{pair.columnAssetId}">
                                    {$t('risk.assetSet.nearIdentical')}
                                </span>
                            {/if}
                            <span class="font-mono tabular-nums {toneClass(pair)}">{pair.value.toFixed(2)}</span>
                        </span>
                    </li>
                {/each}
            </ul>
        {/if}
    </section>

    <section data-testid="risk-correlation-pairs-offsetting">
        <h4 class="text-sm font-semibold text-slate-800 dark:text-slate-100">{$t('risk.assetSet.pairs.offsettingTitle')}</h4>
        <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{$t('risk.assetSet.pairs.offsettingHint')}</p>
        {#if pairs.offsetting.length === 0}
            <p class="mt-2 text-xs text-slate-500 dark:text-slate-400" data-testid="risk-correlation-pairs-offsetting-empty">{$t('risk.assetSet.pairs.noneOffsetting')}</p>
        {:else}
            <ul class="mt-2 space-y-1">
                {#each pairs.offsetting as pair (`${pair.rowAssetId}-${pair.columnAssetId}`)}
                    <li class="flex items-baseline justify-between gap-3 rounded px-2 py-1 text-sm odd:bg-slate-50 dark:odd:bg-slate-800/40" data-testid="risk-correlation-pair-{pair.rowAssetId}-{pair.columnAssetId}">
                        <span class="min-w-0 truncate text-slate-700 dark:text-slate-200">
                            {nameOf(pair.rowAssetId)} <span class="text-slate-400">↔</span>
                            {nameOf(pair.columnAssetId)}
                        </span>
                        <span class="shrink-0 font-mono tabular-nums {toneClass(pair)}">{pair.value.toFixed(2)}</span>
                    </li>
                {/each}
            </ul>
        {/if}
    </section>
</div>
