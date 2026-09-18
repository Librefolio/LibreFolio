<script lang="ts">
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {getIndexColor} from '$lib/utils/colors';
    import {normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import {Copy} from 'lucide-svelte';
    import AllocationTargetBarCell from './AllocationTargetBarCell.svelte';
    import AllocationTargetInputCell from './AllocationTargetInputCell.svelte';
    import type {AllocationTargetDraft} from './editorTypes';

    interface Props {
        targets: AllocationTargetDraft[];
        service: 'pac' | 'rebalancer';
        disabled?: boolean;
        canCopyCurrent?: boolean;
        oncopycurrent?: () => void;
        onchange: () => void;
    }

    let {targets, service, disabled = false, canCopyCurrent = false, oncopycurrent = () => {}, onchange}: Props = $props();

    interface ExactTotal {
        total: string;
        remaining: string;
        valid: boolean;
        excess: boolean;
    }

    function decimalParts(value: string): {digits: bigint; places: number} | null {
        const normalized = normalizeDecimalInput(value);
        if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) return null;
        const [whole = '0', fraction = ''] = normalized.split('.');
        return {
            digits: BigInt(`${whole || '0'}${fraction}` || '0'),
            places: fraction.length,
        };
    }

    function formatScaled(value: bigint, places: number): string {
        const negative = value < 0n;
        const digits = (negative ? -value : value).toString().padStart(places + 1, '0');
        const whole = places === 0 ? digits : digits.slice(0, -places);
        const fraction = places === 0 ? '' : digits.slice(-places).replace(/0+$/, '');
        return `${negative ? '-' : ''}${whole}${fraction ? `.${fraction}` : ''}`;
    }

    function exactTotal(values: readonly string[]): ExactTotal {
        const parsed = values.map(decimalParts);
        if (parsed.some((value) => value === null)) {
            return {total: '—', remaining: '—', valid: false, excess: false};
        }
        const parts = parsed.filter((value): value is NonNullable<typeof value> => value !== null);
        const places = Math.max(0, ...parts.map((value) => value.places));
        const scale = 10n ** BigInt(places);
        const total = parts.reduce((sum, value) => sum + value.digits * 10n ** BigInt(places - value.places), 0n);
        const hundred = 100n * scale;
        return {
            total: formatScaled(total, places),
            remaining: formatScaled(hundred - total, places),
            valid: total === hundred && values.length > 0,
            excess: total > hundred,
        };
    }

    let total = $derived(exactTotal(targets.map((target) => target.target_percent)));

    let columns = $derived<ColumnDef<AllocationTargetDraft>[]>([
        {
            id: 'instrument',
            header: () => $t('common.asset'),
            type: 'text',
            sortable: false,
            filterable: false,
            resizable: false,
            minWidth: 180,
            cell: (target) => target.name || target.instrument_key,
        },
        {
            id: 'target',
            header: () => $t('tools.pacAllocator.rows.target'),
            type: 'custom',
            sortable: false,
            filterable: false,
            resizable: false,
            width: 180,
            cell: (target) => ({
                type: 'custom',
                component: AllocationTargetInputCell,
                props: {
                    value: target.target_percent,
                    disabled,
                    testid: `allocation-target-${target.instrument_key}`,
                    onchange: (value: string) => {
                        target.target_percent = value;
                        onchange();
                    },
                },
            }),
        },
        {
            id: 'bar',
            header: () => $t('tools.allocation.target.visual', {default: 'Distribution'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            resizable: false,
            minWidth: 180,
            cell: (target) => ({
                type: 'custom',
                component: AllocationTargetBarCell,
                props: {
                    value: target.target_percent,
                    index: targets.indexOf(target),
                },
            }),
        },
    ]);
</script>

<section class="space-y-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="allocation-target-editor" data-service={service}>
    <div class="flex flex-wrap items-start justify-between gap-2">
        <div>
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                {#if service === 'pac'}
                    {$t('tools.pacAllocator.targetEditor.title', {default: '3. Liquidity distribution'})}
                {:else}
                    {$t('tools.portfolioRebalancer.targetEditor.title', {default: '2. Final target allocation'})}
                {/if}
            </h2>
            <p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">
                {#if service === 'pac'}
                    {$t('tools.pacAllocator.targetEditor.hint', {default: 'Set how the investable liquidity should be split. These percentages do not describe the current portfolio.'})}
                {:else}
                    {$t('tools.portfolioRebalancer.targetEditor.hint', {default: 'Set the desired final allocation of the invested portfolio. Cash remains separate context.'})}
                {/if}
            </p>
        </div>
        {#if service === 'rebalancer' && canCopyCurrent}
            <button
                class="inline-flex min-h-8 shrink-0 items-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200"
                type="button"
                onclick={oncopycurrent}
                {disabled}
                data-testid="rebalancer-copy-current-distribution"
            >
                <Copy size={13} />
                {$t('tools.portfolioRebalancer.targetEditor.copyCurrent', {default: 'Use current distribution'})}
            </button>
        {/if}
    </div>

    {#if targets.length === 0}
        <div class="rounded-lg border border-dashed border-gray-300 px-4 py-6 text-center text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400" data-testid="allocation-target-empty">
            {$t('tools.allocation.target.selectAssetsFirst', {default: 'Select at least one Asset before setting targets.'})}
        </div>
    {:else}
        <DataTable
            data={targets}
            {columns}
            getRowId={(target) => target.instrument_key}
            storageKey={`tool-${service}-target-v1`}
            enableSelection={false}
            enableActions={false}
            enableSorting={false}
            enableColumnFilters={false}
            enableColumnResize={false}
            enablePagination={false}
            enableColumnVisibility={false}
            stickyHeader={false}
            enableContextMenu={false}
            tableLayout="auto"
        />

        <div class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 dark:border-gray-700 dark:bg-gray-900/50">
            <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
                <span class="font-medium text-gray-700 dark:text-gray-200">
                    {$t('tools.allocation.target.total', {default: 'Total'})}
                    <strong class="ml-1 font-mono">{total.total}%</strong>
                </span>
                <span class={total.valid ? 'font-medium text-libre-green dark:text-green-300' : total.excess ? 'font-medium text-red-700 dark:text-red-300' : 'font-medium text-amber-700 dark:text-amber-300'} data-testid="allocation-target-remaining">
                    {$t('tools.allocation.target.remaining', {default: 'Remaining'})}
                    <strong class="ml-1 font-mono">{total.remaining}%</strong>
                </span>
            </div>
            <div class="mt-2 flex h-3 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700" data-testid="allocation-target-overview">
                {#each targets as target, index (target.instrument_key)}
                    {@const width = Math.max(0, Math.min(100, Number(normalizeDecimalInput(target.target_percent)) || 0))}
                    {@const color = getIndexColor(index, 205).vivid}
                    <span class="h-full transition-[width]" style={`width:${width}%;background:${color}`} title={`${target.name}: ${target.target_percent || '0'}%`}></span>
                {/each}
            </div>
        </div>
    {/if}
</section>
