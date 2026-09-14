<script lang="ts">
    import {_} from '$lib/i18n';
    import type {ToolOutput} from '$lib/features/tools/contracts';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {Info} from 'lucide-svelte';

    type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;
    type ReportingFact = PacOutput['totals']['initial_invested_reporting'];
    type RowRatioFact = PacOutput['rows'][number]['current_weight_percent'] | PacOutput['rows'][number]['deviation_pp'];
    type TotalRatioFact = PacOutput['totals']['max_abs_gap_pp'] | PacOutput['totals']['squared_gap_pp2'];
    type RatioFact = RowRatioFact | TotalRatioFact;

    interface Props {
        result: PacOutput;
        stale: boolean;
    }

    let {result, stale}: Props = $props();
    let exactView = $state(false);

    function displayDecimal(value: string, maxFrac = 8): string {
        return exactView ? value : formatDecimalForDisplay(value, {maxFrac});
    }

    function currencyFlag(code: string): string {
        void $currencyStoreVersion;
        const flag = getCurrencyInfo(code).flag_emoji;
        return flag === '🏳️' ? '' : flag;
    }

    function displayRatioFact(fact: RatioFact): string {
        if (fact.availability === 'unavailable') return `— (${fact.reason_codes.join(', ')})`;
        return exactView ? `${fact.value.numerator} / ${fact.value.denominator}` : displayDecimal(fact.value.approximation, 6);
    }

    function barWidth(fact: RowRatioFact): number {
        if (fact.availability === 'unavailable') return 0;
        const parsed = Number(fact.value.approximation);
        if (!Number.isFinite(parsed)) return 0;
        return Math.max(0, Math.min(100, parsed));
    }

    function targetWidth(value: string): number {
        const parsed = Number(value);
        if (!Number.isFinite(parsed)) return 0;
        return Math.max(0, Math.min(100, parsed));
    }
</script>

{#snippet reportingValue(fact: ReportingFact)}
    {#if fact.availability === 'unavailable'}
        — ({fact.reason_codes.join(', ')})
    {:else}
        <span class="inline-flex items-center gap-1">
            {#if currencyFlag(fact.value.currency)}<span class="emoji-flag" aria-hidden="true">{currencyFlag(fact.value.currency)}</span>{/if}
            <span>{fact.value.currency}</span>
            <span class="font-mono">{displayDecimal(fact.value.amount)}</span>
        </span>
    {/if}
{/snippet}

<section class="space-y-4 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800" data-testid="pac-result" data-state={result.availability} data-stale={stale ? 'true' : 'false'} data-view={exactView ? 'exact' : 'formatted'} data-density="compact">
    <header class="flex flex-wrap items-start justify-between gap-3">
        <div>
            <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">
                {#if result.availability === 'ready'}
                    {$_('tools.pacAllocator.state.ready')}
                {:else if result.availability === 'needs_input'}
                    {$_('tools.pacAllocator.state.needsInput')}
                {:else if result.availability === 'invalid'}
                    {$_('tools.pacAllocator.state.invalid')}
                {:else}
                    {$_('tools.pacAllocator.state.unsupported')}
                {/if}
            </h2>
            <p class="mt-1 text-xs text-gray-600 dark:text-gray-400">{$_('tools.pacAllocator.resultMeaning')}</p>
            {#if stale}
                <p class="mt-2 text-sm font-medium text-amber-700 dark:text-amber-300" data-testid="pac-result-stale">{$_('tools.pacAllocator.stale.result')}</p>
            {/if}
        </div>
        <div class="inline-flex rounded-lg border border-gray-300 p-1 dark:border-gray-600" data-testid="pac-display-mode">
            <button
                type="button"
                onclick={() => (exactView = true)}
                aria-pressed={exactView}
                class="min-h-8 rounded px-2 py-1 text-xs font-medium aria-pressed:bg-libre-green aria-pressed:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70"
                data-testid="pac-view-exact">{$_('tools.pacAllocator.exactView')}</button
            >
            <button
                type="button"
                onclick={() => (exactView = false)}
                aria-pressed={!exactView}
                class="min-h-8 rounded px-2 py-1 text-xs font-medium aria-pressed:bg-libre-green aria-pressed:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70"
                data-testid="pac-view-formatted">{$_('tools.pacAllocator.formattedView')}</button
            >
        </div>
    </header>

    <div class="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-900/60 dark:bg-blue-950/20 dark:text-blue-200" data-testid="pac-denominator-note">
        <Info class="mt-0.5 shrink-0" size={15} />
        <p>
            {$_('tools.pacAllocator.denominatorHint', {
                default: 'Current weights and gaps use invested Asset value only. Existing cash and new contributions stay separate and do not change these P1 percentages.',
            })}
        </p>
    </div>

    <dl class="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4" data-testid="pac-totals">
        <div class="rounded-lg bg-gray-50 p-2.5 dark:bg-gray-900/50">
            <dt class="text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.totals.invested')}</dt>
            <dd class="mt-1 break-words text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-invested">{@render reportingValue(result.totals.initial_invested_reporting)}</dd>
        </div>
        <div class="rounded-lg bg-gray-50 p-2.5 dark:bg-gray-900/50">
            <dt class="text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.totals.existingCash')}</dt>
            <dd class="mt-1 break-words text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-existing-cash">{@render reportingValue(result.totals.existing_cash_reporting)}</dd>
        </div>
        <div class="rounded-lg bg-gray-50 p-2.5 dark:bg-gray-900/50">
            <dt class="text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.totals.contributions')}</dt>
            <dd class="mt-1 break-words text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-contributions">{@render reportingValue(result.totals.contributions_reporting)}</dd>
        </div>
        <div class="rounded-lg bg-gray-50 p-2.5 dark:bg-gray-900/50">
            <dt class="text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.totals.combinedCash')}</dt>
            <dd class="mt-1 break-words text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-combined-cash">{@render reportingValue(result.totals.cash_plus_contributions_reporting)}</dd>
        </div>
    </dl>

    <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table class="min-w-full divide-y divide-gray-200 text-left text-sm dark:divide-gray-700" data-testid="pac-result-rows">
            <thead class="bg-gray-50 text-xs text-gray-600 dark:bg-gray-900/50 dark:text-gray-400">
                <tr>
                    <th class="px-3 py-2 font-medium">{$_('tools.pacAllocator.result.row')}</th>
                    <th class="px-3 py-2 font-medium">{$_('tools.pacAllocator.rows.initialQuantity')}</th>
                    <th class="px-3 py-2 font-medium">{$_('tools.pacAllocator.result.value')}</th>
                    <th class="min-w-36 px-3 py-2 font-medium">{$_('tools.pacAllocator.result.weight')}</th>
                    <th class="min-w-36 px-3 py-2 font-medium">{$_('tools.pacAllocator.result.target')}</th>
                    <th class="px-3 py-2 font-medium">{$_('tools.pacAllocator.result.gap')}</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 text-gray-800 dark:divide-gray-700 dark:text-gray-200">
                {#each result.rows as row}
                    <tr data-testid="pac-result-row">
                        <td class="max-w-48 break-words px-3 py-2">{row.name || row.row_key}</td>
                        <td class="whitespace-nowrap px-3 py-2 font-mono">{row.quantity.availability === 'available' ? displayDecimal(row.quantity.value) : '—'}</td>
                        <td class="whitespace-nowrap px-3 py-2">{@render reportingValue(row.initial_value_reporting)}</td>
                        <td class="px-3 py-2 font-mono">
                            <span>{displayRatioFact(row.current_weight_percent)}</span>
                            <span class="mt-1 block h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                                <span class="block h-full rounded-full bg-blue-500" style={`width:${barWidth(row.current_weight_percent)}%`}></span>
                            </span>
                        </td>
                        <td class="px-3 py-2 font-mono">
                            {#if row.target_percent.availability === 'available'}
                                <span>{displayDecimal(row.target_percent.value)}%</span>
                                <span class="mt-1 block h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                                    <span class="block h-full rounded-full bg-libre-green" style={`width:${targetWidth(row.target_percent.value)}%`}></span>
                                </span>
                            {:else}
                                —
                            {/if}
                        </td>
                        <td class="whitespace-nowrap px-3 py-2 font-mono">{displayRatioFact(row.deviation_pp)}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    <dl class="grid grid-cols-1 gap-3 sm:grid-cols-2" data-testid="pac-distance-summary">
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
            <dt class="text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.totals.maxGap')}</dt>
            <dd class="mt-1 break-words font-mono text-sm" data-testid="pac-max-gap">{displayRatioFact(result.totals.max_abs_gap_pp)}</dd>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
            <dt class="text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.totals.squaredGap')}</dt>
            <dd class="mt-1 break-words font-mono text-sm" data-testid="pac-squared-gap">{displayRatioFact(result.totals.squared_gap_pp2)}</dd>
        </div>
    </dl>

    <section data-testid="pac-cash-pools">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$_('tools.pacAllocator.cashPools')}</h3>
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {$_('tools.pacAllocator.cashPoolsHint', {
                default: 'Native balances remain separate by currency. This report does not exchange, transfer, or merge cash.',
            })}
        </p>
        {#if result.cash_pools.availability === 'available'}
            <ul class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {#each result.cash_pools.value as pool}
                    <li class="rounded-lg bg-gray-50 p-2.5 text-sm dark:bg-gray-900/50" data-testid="pac-cash-pool">
                        <p class="inline-flex items-center gap-1 font-semibold">
                            {#if currencyFlag(pool.currency)}<span class="emoji-flag" aria-hidden="true">{currencyFlag(pool.currency)}</span>{/if}
                            {pool.currency}
                        </p>
                        <p class="mt-1 font-mono">{$_('tools.pacAllocator.totals.existingCash')}: {displayDecimal(pool.existing_amount)}</p>
                        <p class="font-mono">{$_('tools.pacAllocator.totals.contributions')}: {displayDecimal(pool.contribution_amount)}</p>
                        <p class="font-mono">{$_('tools.pacAllocator.totals.combinedCash')}: {displayDecimal(pool.combined_amount)}</p>
                    </li>
                {/each}
            </ul>
        {:else}
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">— ({result.cash_pools.reason_codes.join(', ')})</p>
        {/if}
    </section>

    {#if result.issues.length > 0}
        <section data-testid="pac-issues">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$_('tools.pacAllocator.issues')}</h3>
            <ul class="mt-3 space-y-2">
                {#each result.issues as issue}
                    <li class="rounded-lg border border-gray-200 p-3 text-sm dark:border-gray-700" data-testid="pac-issue" data-kind={issue.kind}>
                        <p class="font-medium"><span class="font-mono">{issue.code}</span> · {issue.kind}</p>
                        <p class="mt-1 break-words font-mono text-xs text-gray-600 dark:text-gray-400">{issue.path.join(' · ')}</p>
                    </li>
                {/each}
            </ul>
        </section>
    {/if}

    {#if result.availability === 'ready'}
        <details class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="pac-normalized-details">
            <summary class="cursor-pointer font-medium">{$_('tools.pacAllocator.normalizedInput')}</summary>
            <pre class="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(result.normalized, null, 2)}</pre>
        </details>
    {/if}
</section>
