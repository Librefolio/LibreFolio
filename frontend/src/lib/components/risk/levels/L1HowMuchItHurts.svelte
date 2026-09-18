<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {formatCurrencyAmount} from '../riskAnalysisHelpers';
    import {buildCurrentDrawdown, buildHurtRows} from './levelHelpers';

    /**
     * L1 — "how much can it hurt?"
     *
     * The old panel's defect was never that it showed a VaR. It was that it put a
     * one-day loss next to a multi-year drawdown without ever declaring the
     * change of scale, so the reader summed them in their head. The cure is a
     * single section with one explicit, increasing scale.
     *
     * Nothing in here is estimated: every figure is something the sample did.
     */
    interface Props {
        historicalResults: RiskAnalyticResult[];
        /**
         * Scope value, used to put money next to every percentage.
         *
         * Optional, and when absent the money column simply does not appear. No
         * risk analytic carries an amount, so a figure here would have to be
         * invented, and an invented euro reads exactly like a measured one.
         */
        scopeValue?: number | null;
        currency: string;
        loading?: boolean;
    }

    let {historicalResults, scopeValue = null, currency, loading = false}: Props = $props();

    let rows = $derived(buildHurtRows(historicalResults));
    let current = $derived(buildCurrentDrawdown(historicalResults));
    let showMoney = $derived(typeof scopeValue === 'number' && Number.isFinite(scopeValue) && scopeValue > 0);

    /** A loss fraction as a signed percentage, because a loss is a fall. */
    function lossPercent(fraction: number): string {
        return `−${(fraction * 100).toFixed(1)}%`;
    }

    /** A gain fraction as a signed percentage. */
    function gainPercent(fraction: number): string {
        return `+${(fraction * 100).toFixed(1)}%`;
    }

    /** The money a loss fraction costs at the current scope value. */
    function lossMoney(fraction: number): string {
        if (!showMoney || scopeValue == null) return '';
        return `−${formatCurrencyAmount(String(scopeValue * fraction), currency)}`;
    }

    /** Documentation is per row, never one generic link for the section. */
    const DOC_PATHS: Record<string, string> = {
        day: 'user/analysis/risk.md#value-at-risk',
        month: 'user/analysis/risk.md#value-at-risk',
        worst: 'user/analysis/risk.md#drawdown',
    };
</script>

<div class="space-y-3" data-testid="risk-l1">
    {#if loading && rows.length === 0}
        <div class="space-y-2" data-testid="risk-l1-loading">
            {#each [0, 1, 2] as placeholder (placeholder)}
                <div class="h-10 animate-pulse rounded bg-gray-100 dark:bg-slate-700"></div>
            {/each}
        </div>
    {:else if rows.length === 0}
        <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-l1-empty">{$t('risk.states.unavailable')}</p>
    {:else}
        <ul class="divide-y divide-gray-100 dark:divide-slate-700" data-testid="risk-l1-scale">
            {#each rows as row (row.id)}
                <li class="flex items-baseline justify-between gap-4 py-2" data-testid="risk-l1-row-{row.id}">
                    <div class="flex min-w-0 items-center gap-1">
                        <span class="truncate text-sm text-gray-700 dark:text-gray-200">{$t(`risk.levels.l1.rows.${row.id}`)}</span>
                        <DocsLink path={DOC_PATHS[row.id]} label={$t(`risk.levels.l1.rows.${row.id}`)} testId="risk-l1-doc-{row.id}" />
                    </div>
                    <div class="flex shrink-0 items-baseline gap-3 tabular-nums">
                        <span class="text-sm font-semibold text-red-600 dark:text-red-400" data-testid="risk-l1-loss-{row.id}">{lossPercent(row.loss)}</span>
                        {#if showMoney}
                            <span class="text-sm text-gray-600 dark:text-gray-300" data-testid="risk-l1-money-{row.id}">{lossMoney(row.loss)}</span>
                        {/if}
                    </div>
                </li>
                {#if row.durationDays != null || row.requiredRecovery != null}
                    <li class="pb-2 text-right text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l1-detail-{row.id}">
                        {#if row.durationDays != null}
                            <span data-testid="risk-l1-duration-{row.id}">{$t('risk.levels.l1.durationDays', {values: {days: row.durationDays}})}</span>
                        {/if}
                        {#if row.requiredRecovery != null}
                            <!-- The number that teaches the asymmetry: a −50% fall
                                 needs a +100% rise, not a +50% one. -->
                            <span class="ml-2" data-testid="risk-l1-recovery-{row.id}">{$t('risk.levels.l1.requiredRecovery', {values: {percent: gainPercent(row.requiredRecovery)}})}</span>
                        {/if}
                    </li>
                {/if}
            {/each}
        </ul>

        {#if current}
            <div class="rounded-lg bg-gray-50 px-3 py-2 dark:bg-slate-900/40" data-testid="risk-l1-current">
                <div class="flex items-baseline justify-between gap-4">
                    <span class="text-sm text-gray-700 dark:text-gray-200">{$t('risk.levels.l1.currentDrawdown')}</span>
                    <div class="flex shrink-0 items-baseline gap-3 tabular-nums">
                        <span class="text-sm font-semibold text-amber-600 dark:text-amber-400" data-testid="risk-l1-current-loss">{lossPercent(current.loss)}</span>
                        {#if showMoney}
                            <span class="text-sm text-gray-600 dark:text-gray-300" data-testid="risk-l1-current-money">{lossMoney(current.loss)}</span>
                        {/if}
                    </div>
                </div>
                <p class="mt-0.5 text-right text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l1-current-detail">
                    {#if current.peakDate}
                        <span>{$t('risk.levels.l1.sincePeak', {values: {date: current.peakDate}})}</span>
                    {/if}
                    {#if current.requiredRecovery != null}
                        <span class="ml-2">{$t('risk.levels.l1.requiredRecovery', {values: {percent: gainPercent(current.requiredRecovery)}})}</span>
                    {/if}
                </p>
            </div>
        {/if}
    {/if}
</div>
