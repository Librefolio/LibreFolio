<script lang="ts">
    import {t} from '$lib/i18n';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {LoaderCircle} from 'lucide-svelte';
    import type {PacContributionInput, PacMoneyInput} from './editorTypes';

    interface AuthoritativePool {
        currency: string;
        existing_amount: string;
        contribution_amount: string;
        combined_amount: string;
    }

    interface SummaryRow {
        currency: string;
        existing: string[];
        contributions: string[];
        authoritative: AuthoritativePool | null;
    }

    interface Props {
        existing: readonly PacMoneyInput[];
        contributions: readonly PacContributionInput[];
        authoritativePools?: readonly AuthoritativePool[] | null;
        pending?: boolean;
        stale?: boolean;
    }

    let {existing, contributions, authoritativePools = null, pending = false, stale = false}: Props = $props();

    let rows = $derived.by<SummaryRow[]>(() => {
        const currencies = new Set<string>();
        for (const item of existing) if (item.currency) currencies.add(item.currency);
        for (const item of contributions) if (item.currency) currencies.add(item.currency);
        for (const item of authoritativePools ?? []) currencies.add(item.currency);
        return [...currencies].sort().map((currency) => ({
            currency,
            existing: existing.filter((item) => item.currency === currency && item.amount !== null).map((item) => item.amount ?? ''),
            contributions: contributions.filter((item) => item.currency === currency && item.amount !== null).map((item) => item.amount ?? ''),
            authoritative: authoritativePools?.find((pool) => pool.currency === currency) ?? null,
        }));
    });

    function display(value: string): string {
        return formatDecimalForDisplay(value, {maxFrac: 12}) || '0';
    }

    function flag(code: string): string {
        void $currencyStoreVersion;
        const value = getCurrencyInfo(code).flag_emoji;
        return value === '🏳️' ? '' : value;
    }
</script>

<section class="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900/50" data-testid="allocation-funding-summary" aria-busy={pending}>
    <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white">
                {$t('tools.allocation.fundingSummary.title', {default: 'Available funds by currency'})}
            </h3>
            <p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {$t('tools.allocation.fundingSummary.hint', {
                    default: 'Existing cash and new contributions remain separate facts. Combined totals are shown only after backend analysis.',
                })}
            </p>
        </div>
        {#if pending}
            <span class="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400" role="status">
                <LoaderCircle class="animate-spin" size={14} />
                {$t('tools.allocation.fundingSummary.updating', {default: 'Updating…'})}
            </span>
        {/if}
    </div>

    {#if rows.length === 0}
        <p class="mt-3 rounded-lg border border-dashed border-gray-300 px-3 py-3 text-center text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
            {$t('tools.allocation.fundingSummary.empty', {default: 'No cash or contribution entered.'})}
        </p>
    {:else}
        <div class="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {#each rows as row (row.currency)}
                <article class="rounded-lg border border-gray-200 bg-white p-2.5 text-xs dark:border-gray-700 dark:bg-gray-800" data-testid={`allocation-funding-${row.currency}`}>
                    <h4 class="inline-flex items-center gap-1 font-semibold text-gray-900 dark:text-white">
                        {#if flag(row.currency)}<span class="emoji-flag" aria-hidden="true">{flag(row.currency)}</span>{/if}
                        {row.currency}
                    </h4>
                    <dl class="mt-2 space-y-1.5 text-gray-600 dark:text-gray-300">
                        <div class="flex items-start justify-between gap-2">
                            <dt>{$t('tools.allocation.fundingSummary.existing', {default: 'Existing'})}</dt>
                            <dd class="text-right font-mono">{row.existing.length > 0 ? row.existing.map(display).join(' + ') : '0'}</dd>
                        </div>
                        <div class="flex items-start justify-between gap-2">
                            <dt>{$t('tools.allocation.fundingSummary.contributions', {default: 'Contributions'})}</dt>
                            <dd class="text-right font-mono">{row.contributions.length > 0 ? row.contributions.map(display).join(' + ') : '0'}</dd>
                        </div>
                        <div class="flex items-center justify-between gap-2 border-t border-gray-200 pt-1.5 font-semibold text-gray-900 dark:border-gray-700 dark:text-white">
                            <dt>{$t('tools.allocation.fundingSummary.available', {default: 'Available'})}</dt>
                            <dd class="font-mono" data-testid={`allocation-funding-total-${row.currency}`}>
                                {#if row.authoritative && !stale}
                                    {display(row.authoritative.combined_amount)}
                                {:else}
                                    <span class="font-sans font-normal text-gray-400">{$t('tools.allocation.fundingSummary.afterAnalysis', {default: 'after analysis'})}</span>
                                {/if}
                            </dd>
                        </div>
                    </dl>
                </article>
            {/each}
        </div>
    {/if}
</section>
