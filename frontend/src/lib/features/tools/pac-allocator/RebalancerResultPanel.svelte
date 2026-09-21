<script lang="ts">
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import type {ToolOutput} from '$lib/features/tools/contracts';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {Info, Scale} from 'lucide-svelte';
    import AllocationDiagnostics from './AllocationDiagnostics.svelte';

    type RebalancerOutput = ToolOutput<'portfolio_rebalancer', '1.0.0'>;
    type RebalanceRow = RebalancerOutput['instruments'][number];

    interface Props {
        output: RebalancerOutput | null;
        stale?: boolean;
    }

    let {output, stale = false}: Props = $props();

    function scalar(fact: {availability: string; value: string | null}): string {
        return fact.availability === 'available' && fact.value !== null ? formatDecimalForDisplay(fact.value, {maxFrac: 12}) : '—';
    }

    function ratio(fact: {availability: string; value: {approximation: string} | null}): string {
        return fact.availability === 'available' && fact.value !== null ? formatDecimalForDisplay(fact.value.approximation, {maxFrac: 4}) : '—';
    }

    function money(fact: {availability: string; value: {amount: string; currency: string} | null}): string {
        if (fact.availability !== 'available' || fact.value === null) return '—';
        return `${formatDecimalForDisplay(fact.value.amount, {maxFrac: 12})} ${fact.value.currency}`;
    }

    let columns = $derived<ColumnDef<RebalanceRow>[]>([
        {
            id: 'asset',
            header: () => $t('common.asset'),
            type: 'text',
            sortable: true,
            filterable: false,
            minWidth: 180,
            cell: (row) => row.name || row.instrument_key,
        },
        {
            id: 'contexts',
            header: () => $t('tools.portfolioRebalancer.results.custodyContexts', {default: 'Custodies'}),
            type: 'number',
            sortable: true,
            filterable: false,
            width: 100,
            cell: (row) => row.custody_context_count,
        },
        {
            id: 'currentValue',
            header: () => $t('tools.portfolioRebalancer.results.currentValue', {default: 'Current value'}),
            type: 'text',
            sortable: false,
            filterable: false,
            minWidth: 150,
            cell: (row) => money(row.current_value_reporting),
        },
        {
            id: 'currentWeight',
            header: () => $t('tools.portfolioRebalancer.results.currentWeight', {default: 'Current %'}),
            type: 'text',
            sortable: false,
            filterable: false,
            width: 120,
            cell: (row) => `${ratio(row.current_weight_percent)}%`,
        },
        {
            id: 'target',
            header: () => $t('tools.pacAllocator.rows.target'),
            type: 'text',
            sortable: false,
            filterable: false,
            width: 110,
            cell: (row) => `${scalar(row.target_percent)}%`,
        },
        {
            id: 'targetValue',
            header: () => $t('tools.portfolioRebalancer.results.targetValue', {default: 'Target value'}),
            type: 'text',
            sortable: false,
            filterable: false,
            minWidth: 150,
            cell: (row) => money(row.target_value_reporting),
        },
        {
            id: 'gap',
            header: () => $t('tools.portfolioRebalancer.results.valueGap', {default: 'Value gap'}),
            type: 'text',
            sortable: false,
            filterable: false,
            minWidth: 150,
            cell: (row) => money(row.value_gap_to_target_reporting),
        },
    ]);

    let rows = $derived(output?.instruments ?? []);
    let zeroInvested = $derived(output?.totals.max_abs_gap_pp.reason_codes.includes('zero_invested_value') ?? false);
</script>

<section class="space-y-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="rebalancer-result-panel">
    <div class="flex items-start gap-2">
        <Scale class="mt-0.5 shrink-0 text-blue-700 dark:text-blue-300" size={18} />
        <div>
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                {$t('tools.portfolioRebalancer.results.title', {default: '3. Allocation gaps'})}
            </h2>
            <p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">
                {$t('tools.portfolioRebalancer.results.hint', {
                    default: 'P1 compares current invested value with the final target. It does not propose trades or prove feasibility.',
                })}
            </p>
        </div>
    </div>

    {#if output === null}
        <div class="rounded-lg border border-dashed border-gray-300 px-4 py-8 text-center text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
            {$t('tools.portfolioRebalancer.results.empty', {default: 'Run the analysis to compare current and target allocation.'})}
        </div>
    {:else}
        <AllocationDiagnostics availability={output.availability} issues={output.issues} />

        {#if zeroInvested}
            <div class="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs leading-5 text-blue-900 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-100" data-testid="rebalancer-zero-invested">
                {$t('tools.portfolioRebalancer.results.zeroInvested', {
                    default: 'Current invested value is zero, so current weights and percentage-point gaps are unavailable.',
                })}
            </div>
        {/if}

        {#if stale}
            <div class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" data-testid="rebalancer-result-stale">
                {$t('tools.allocation.results.stale', {default: 'Inputs changed after this result. Run the analysis again before using it.'})}
            </div>
        {/if}

        <div class="grid gap-2 sm:grid-cols-2">
            <article class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 dark:border-gray-700 dark:bg-gray-900/50">
                <p class="text-[11px] text-gray-500 dark:text-gray-400">{$t('tools.portfolioRebalancer.results.investedTotal', {default: 'Current invested value'})}</p>
                <p class="mt-1 font-mono text-sm font-semibold text-gray-900 dark:text-white">{money(output.totals.current_invested_reporting)}</p>
            </article>
            <article class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 dark:border-gray-700 dark:bg-gray-900/50">
                <p class="text-[11px] text-gray-500 dark:text-gray-400">{$t('tools.portfolioRebalancer.results.availableCash', {default: 'Cash and new contributions (context only)'})}</p>
                <p class="mt-1 font-mono text-sm font-semibold text-gray-900 dark:text-white">{money(output.totals.cash_plus_contributions_reporting)}</p>
            </article>
        </div>

        {#if rows.length > 0}
            <DataTable
                data={rows}
                {columns}
                getRowId={(row) => row.instrument_key}
                storageKey="tool-portfolio-rebalancer-result-v1"
                enableSelection={false}
                enableActions={false}
                enableSorting={true}
                enableColumnFilters={false}
                enableColumnResize={true}
                enablePagination={false}
                enableColumnVisibility={true}
                stickyHeader={false}
                enableContextMenu={false}
                tableLayout="auto"
            />
        {/if}

        <div class="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs leading-5 text-blue-900 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-100">
            <Info class="mt-0.5 shrink-0" size={14} />
            <p>
                {$t('tools.portfolioRebalancer.results.boundary', {
                    default: 'A positive or negative gap is descriptive, not a buy or sell instruction. No order, Broker route, FX transfer or tax action is generated.',
                })}
            </p>
        </div>
    {/if}
</section>
