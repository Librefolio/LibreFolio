<script lang="ts">
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import type {ToolOutput} from '$lib/features/tools/contracts';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {Calculator, Info} from 'lucide-svelte';
    import AllocationDiagnostics from './AllocationDiagnostics.svelte';

    interface AllocationRow {
        instrument_key: string;
        name: string | null;
        target_percent: {
            availability: 'available' | 'unavailable';
            value: string | null;
            reason_codes: string[];
        };
        ideal_allocation_reporting: {
            availability: 'available' | 'unavailable';
            value: {amount: string; currency: string} | null;
            reason_codes: string[];
        };
    }

    interface Props {
        output: ToolOutput<'pac_allocator', '1.0.0'> | null;
        stale?: boolean;
    }

    let {output, stale = false}: Props = $props();

    function factText(fact: AllocationRow['target_percent']): string {
        return fact.availability === 'available' && fact.value !== null ? formatDecimalForDisplay(fact.value, {maxFrac: 12}) : '—';
    }

    function moneyText(fact: AllocationRow['ideal_allocation_reporting']): string {
        if (fact.availability !== 'available' || fact.value === null) return '—';
        return `${formatDecimalForDisplay(fact.value.amount, {maxFrac: 12})} ${fact.value.currency}`;
    }

    let columns = $derived<ColumnDef<AllocationRow>[]>([
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
            id: 'target',
            header: () => $t('tools.pacAllocator.rows.target'),
            type: 'text',
            sortable: false,
            filterable: false,
            width: 130,
            cell: (row) => `${factText(row.target_percent)}%`,
        },
        {
            id: 'allocation',
            header: () => $t('tools.pacAllocator.results.idealAllocation', {default: 'Theoretical allocation'}),
            type: 'text',
            sortable: false,
            filterable: false,
            minWidth: 190,
            cell: (row) => moneyText(row.ideal_allocation_reporting),
        },
    ]);

    let allocations = $derived((output?.allocations ?? []) as AllocationRow[]);
</script>

<section class="space-y-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="pac-result-panel">
    <div class="flex items-start gap-2">
        <Calculator class="mt-0.5 shrink-0 text-libre-green dark:text-green-300" size={18} />
        <div>
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                {$t('tools.pacAllocator.results.title', {default: '4. PAC analysis'})}
            </h2>
            <p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">
                {$t('tools.pacAllocator.results.hint', {
                    default: 'P1 splits the available liquidity by target percentage. It does not calculate units, orders, feasibility or an optimum.',
                })}
            </p>
        </div>
    </div>

    {#if output === null}
        <div class="rounded-lg border border-dashed border-gray-300 px-4 py-8 text-center text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
            {$t('tools.pacAllocator.results.empty', {default: 'Run the analysis to calculate the theoretical monetary allocation.'})}
        </div>
    {:else}
        <AllocationDiagnostics availability={output.availability} issues={output.issues} />

        {#if stale}
            <div class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" data-testid="pac-result-stale">
                {$t('tools.allocation.results.stale', {default: 'Inputs changed after this result. Run the analysis again before using it.'})}
            </div>
        {/if}

        <div class="grid gap-2 sm:grid-cols-3">
            <article class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 dark:border-gray-700 dark:bg-gray-900/50">
                <p class="text-[11px] text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.results.existingCash', {default: 'Existing cash'})}</p>
                <p class="mt-1 font-mono text-sm font-semibold text-gray-900 dark:text-white">{moneyText(output.totals.existing_cash_reporting)}</p>
            </article>
            <article class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 dark:border-gray-700 dark:bg-gray-900/50">
                <p class="text-[11px] text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.results.contributions', {default: 'New contributions'})}</p>
                <p class="mt-1 font-mono text-sm font-semibold text-gray-900 dark:text-white">{moneyText(output.totals.contributions_reporting)}</p>
            </article>
            <article class="rounded-lg border border-blue-200 bg-blue-50 p-2.5 dark:border-blue-900 dark:bg-blue-950/30">
                <p class="text-[11px] text-blue-700 dark:text-blue-300">{$t('tools.pacAllocator.results.budget', {default: 'Investable budget'})}</p>
                <p class="mt-1 font-mono text-sm font-semibold text-blue-950 dark:text-blue-100">{moneyText(output.totals.investable_budget_reporting)}</p>
            </article>
        </div>

        {#if allocations.length > 0}
            <DataTable
                data={allocations}
                {columns}
                getRowId={(row) => row.instrument_key}
                storageKey="tool-pac-allocator-result-v1"
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
                {$t('tools.pacAllocator.results.boundary', {
                    default: 'These are theoretical money amounts. No price, quantity, Broker route, FX transfer or order has been selected.',
                })}
            </p>
        </div>
    {/if}
</section>
