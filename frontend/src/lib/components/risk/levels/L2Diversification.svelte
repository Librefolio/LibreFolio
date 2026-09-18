<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {buildDivergenceRows, uncoveredWeight} from './levelHelpers';

    /**
     * L2 — "am I diversified like I think I am?"
     *
     * The cheapest valuable picture in the whole subsystem: `weight` and
     * `percentage_contribution` both already travel in the payload, and `weight`
     * is currently thrown away. Risk contribution on its own does not answer the
     * question — the answer is the *gap* between what a holding weighs and how
     * much risk it produces.
     *
     * The bars are two-sided because a contribution can be negative: an asset
     * that reduces portfolio risk. Neither a pie nor a treemap can draw that,
     * which is why neither is allowed here.
     */
    interface Props {
        contributionResult: RiskAnalyticResult | null;
        /** Display names by asset id; an id with no name falls back to `#id`. */
        assetNames?: Record<number, string>;
        loading?: boolean;
        /** Rows shown before the "show all" control; the rest stay one click away. */
        visibleRows?: number;
    }

    let {contributionResult, assetNames = {}, loading = false, visibleRows = 8}: Props = $props();

    let rows = $derived(buildDivergenceRows(contributionResult));
    /**
     * The share of NAV these rows do not describe.
     *
     * Read with `!== null`, never `?? 0`: the field carries a schema default, so
     * the generated type offers `undefined` even though the server always sends
     * it, and the fallback that type invites — zero — reads as "nothing
     * uncovered". That is precisely the reassurance this line exists to withhold.
     */
    let uncovered = $derived(uncoveredWeight(contributionResult));
    let expanded = $state(false);
    let shown = $derived(expanded ? rows : rows.slice(0, visibleRows));

    /** The widest magnitude on show, so both columns share one scale. */
    let scale = $derived(Math.max(0.01, ...rows.map((row) => Math.max(Math.abs(row.weight), Math.abs(row.contribution)))));

    function name(assetId: number): string {
        return assetNames[assetId] ?? `#${assetId}`;
    }

    function percent(fraction: number): string {
        return `${(fraction * 100).toFixed(1)}%`;
    }

    function signedPercent(fraction: number): string {
        return `${fraction >= 0 ? '+' : '−'}${(Math.abs(fraction) * 100).toFixed(1)}pp`;
    }

    /** Width of a bar as a share of the shared scale. */
    function width(value: number): string {
        return `${Math.min(100, (Math.abs(value) / scale) * 100)}%`;
    }
</script>

<div class="space-y-3" data-testid="risk-l2">
    {#if loading && rows.length === 0}
        <div class="space-y-2" data-testid="risk-l2-loading">
            {#each [0, 1, 2] as placeholder (placeholder)}
                <div class="h-8 animate-pulse rounded bg-gray-100 dark:bg-slate-700"></div>
            {/each}
        </div>
    {:else if rows.length === 0}
        <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-l2-empty">{$t('risk.states.unavailable')}</p>
    {:else}
        {#if uncovered !== null}
            <!-- `weight` is a fraction of NAV, so on a portfolio holding anything
                 unpriceable these bars sum to well under one — 0,408 on the test
                 data — beneath a heading that asks about the whole portfolio.
                 Stating the residual is what keeps the list from answering a
                 narrower question than the one it appears to answer. -->
            <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l2-uncovered" data-uncovered={uncovered}>
                {$t('risk.metrics.cashWeight')}: {percent(uncovered)}
            </p>
        {/if}
        <div class="flex justify-end gap-4 text-xs text-gray-500 dark:text-gray-400">
            <span data-testid="risk-l2-legend-weight">{$t('risk.levels.l2.weight')}</span>
            <span data-testid="risk-l2-legend-contribution">{$t('risk.levels.l2.contribution')}</span>
        </div>
        <ul class="space-y-2" data-testid="risk-l2-rows">
            {#each shown as row (row.assetId)}
                <li class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3" data-testid="risk-l2-row-{row.assetId}">
                    <div class="min-w-0 space-y-1">
                        <span class="block truncate text-sm text-gray-700 dark:text-gray-200">{name(row.assetId)}</span>
                        <div class="h-1.5 rounded bg-gray-200 dark:bg-slate-700">
                            <div class="h-1.5 rounded bg-gray-400 dark:bg-slate-500" style="width: {width(row.weight)}" data-testid="risk-l2-bar-weight-{row.assetId}"></div>
                        </div>
                        <div class="h-1.5 rounded bg-gray-200 dark:bg-slate-700">
                            <div class="h-1.5 rounded {row.contribution < 0 ? 'bg-emerald-500' : 'bg-red-500'}" style="width: {width(row.contribution)}" data-testid="risk-l2-bar-contribution-{row.assetId}" data-sign={row.contribution < 0 ? 'negative' : 'positive'}></div>
                        </div>
                    </div>
                    <div class="shrink-0 text-right tabular-nums">
                        <div class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l2-weight-{row.assetId}">{percent(row.weight)}</div>
                        <div class="text-xs text-gray-700 dark:text-gray-200" data-testid="risk-l2-contribution-{row.assetId}">{percent(row.contribution)}</div>
                        <div class="text-xs font-semibold {row.divergence > 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}" data-testid="risk-l2-divergence-{row.assetId}">
                            {signedPercent(row.divergence)}
                        </div>
                    </div>
                </li>
            {/each}
        </ul>
        {#if rows.length > visibleRows}
            <button type="button" class="text-xs text-libre-green hover:underline" onclick={() => (expanded = !expanded)} data-testid="risk-l2-toggle-all">
                {expanded ? $t('risk.levels.l2.showLess') : $t('risk.levels.l2.showAll')}
            </button>
        {/if}
    {/if}
</div>
