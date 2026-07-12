<!--
  OpenLotsTable — residual FIFO lots still held for broker detail inline panel.
  Uses generic DataTable and forwards navigateToRowId for bubble → row pulse.
-->
<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {slide} from 'svelte/transition';
    import {_} from '$lib/i18n';
    import {schemas} from '$lib/api';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {ChevronDown, ChevronRight} from 'lucide-svelte';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import type {z} from 'zod';

    type OpenLotSchema = z.infer<typeof schemas.OpenLotSchema>;
    type NumericLike = string | (string | null)[] | null | undefined;

    interface Props {
        lots: ReadonlyArray<OpenLotSchema>;
        currency: string;
        brokers?: ReadonlyArray<BrokerLike>;
    }

    interface DisplayRow {
        rowId: string;
        brokerId: number;
        brokerName: string;
        broker: BrokerLike | null;
        buyDate: string;
        buyPrice: number | null;
        originalQuantity: number | null;
        remainingQuantity: number | null;
        residualCostBasis: number | null;
        currentValue: number | null;
        unrealizedPnl: number | null;
        unrealizedPnlPercent: number | null;
    }

    let {lots = [], currency, brokers = []}: Props = $props();

    let tableRef: DataTable<DisplayRow> | undefined = $state(undefined);
    let expanded = $state(untrack(() => lots.length > 0));

    export function navigateToRowId(rowId: string): void {
        if (!expanded) {
            expanded = true;
            void tick().then(() => tableRef?.navigateToRowId(rowId));
            return;
        }
        tableRef?.navigateToRowId(rowId);
    }

    $effect(() => {
        expanded = lots.length > 0;
    });

    function label(key: string, fallback: string): string {
        const translated = $_(key) || fallback;
        return translated === key ? fallback : translated;
    }

    function safeNum(value: NumericLike): number | null {
        const scalar = Array.isArray(value) ? (value[0] ?? null) : value;
        if (scalar == null) return null;
        const parsed = Number.parseFloat(scalar);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function formatQuantity(value: number | null): string {
        return value == null ? '—' : value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
    }

    function amountCell(value: number | null) {
        if (value == null) return '—';
        return {
            type: 'html' as const,
            html: `<span class="font-medium tabular-nums text-gray-700 dark:text-gray-200">${formatCurrencyAmountPlain(value, currency)}</span>`,
        };
    }

    function signedAmountWithPercentCell(value: number | null, percent: number | null) {
        if (value == null) return '—';
        const classes = value > 0 ? 'text-green-600 dark:text-green-400' : value < 0 ? 'text-red-500 dark:text-red-400' : 'text-gray-500 dark:text-gray-400';
        const percentHtml = percent == null ? '' : `<span class="text-xs ${classes}">${percent >= 0 ? '+' : ''}${(percent * 100).toFixed(2)}%</span>`;
        return {
            type: 'html' as const,
            html: `<div class="flex flex-col items-end"><span class="font-medium tabular-nums ${classes}">${formatCurrencyAmountPlain(value, currency, {showSign: value !== 0})}</span>${percentHtml}</div>`,
        };
    }

    function brokerStyle(brokerId: number): string {
        const c = getBrokerColor(brokerId, brokers);
        return `--broker-bg:${c.bg};--broker-text:${c.text};--broker-dark-bg:${c.darkBg};--broker-dark-text:${c.darkText};--broker-vivid:${c.vivid};--broker-vivid-light:${c.vividLight};`;
    }

    function getRowClass(_row: DisplayRow): string {
        return 'lot-row-tinted';
    }

    let rows = $derived.by<DisplayRow[]>(() =>
        lots.map((lot) => {
            const broker = brokers.find((item) => item.id === lot.broker_id) ?? null;
            const buyPrice = safeNum(lot.buy_price);
            const originalQuantity = safeNum(lot.original_quantity);
            const remainingQuantity = safeNum(lot.remaining_quantity);
            const unrealizedPnl = safeNum(lot.unrealized_pnl);
            const residualCostBasis = buyPrice != null && remainingQuantity != null ? buyPrice * remainingQuantity : null;
            const currentValue = residualCostBasis != null && unrealizedPnl != null ? residualCostBasis + unrealizedPnl : null;
            const unrealizedPnlPercent = residualCostBasis != null && residualCostBasis !== 0 && unrealizedPnl != null ? unrealizedPnl / residualCostBasis : null;

            return {
                rowId: String(lot.buy_transaction_id),
                brokerId: lot.broker_id,
                brokerName: broker?.name ?? `#${lot.broker_id}`,
                broker,
                buyDate: lot.buy_date,
                buyPrice,
                originalQuantity,
                remainingQuantity,
                residualCostBasis,
                currentValue,
                unrealizedPnl,
                unrealizedPnlPercent,
            };
        }),
    );

    let columns = $derived.by<ColumnDef<DisplayRow>[]>(() => [
        {
            id: 'buy-date',
            header: () => label('brokers.lots.buyDate', 'Buy Date'),
            cell: (row) => ({type: 'date', value: row.buyDate, format: 'date'}),
            type: 'date',
            width: 130,
            minWidth: 120,
            sortable: true,
            filterable: false,
            getValue: (row) => row.buyDate,
        },
        {
            id: 'broker',
            header: () => $_('brokers.title') || 'Broker',
            type: 'text',
            width: 130,
            minWidth: 120,
            maxWidth: 220,
            resizable: true,
            sortable: true,
            getValue: (row) => row.brokerName,
            cell: (row) => ({
                type: 'custom',
                component: BrokerBadge,
                props: {
                    broker: row.broker ?? {id: row.brokerId, name: row.brokerName},
                    size: 16,
                    showName: true,
                    tooltip: row.brokerName,
                },
            }),
        },
        {
            id: 'quantity',
            header: () => label('common.quantity', 'Quantity'),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 140,
            sortable: true,
            filterable: false,
            getValue: (row) => row.remainingQuantity ?? 0,
            cell: (row) => ({
                type: 'html',
                html: `<span class="font-medium tabular-nums text-gray-700 dark:text-gray-200">${formatQuantity(row.remainingQuantity)} / ${formatQuantity(row.originalQuantity)}</span>`,
            }),
        },
        {
            id: 'buy-price',
            header: () => label('dashboard.price', 'Price'),
            type: 'number',
            align: 'right',
            width: 170,
            minWidth: 150,
            sortable: true,
            filterable: false,
            getValue: (row) => row.buyPrice ?? 0,
            cell: (row) => amountCell(row.buyPrice),
        },
        {
            id: 'current-value',
            header: () => label('brokers.lots.currentValue', 'Current Value'),
            type: 'number',
            align: 'right',
            width: 190,
            minWidth: 170,
            sortable: true,
            filterable: false,
            getValue: (row) => row.currentValue ?? 0,
            cell: (row) => amountCell(row.currentValue),
        },
        {
            id: 'unrealized-pnl',
            header: () => label('dashboard.unrealizedPnl', 'Unrealized P&L'),
            headerTooltip: () => label('dashboard.unrealizedPnlPercentTooltip', 'Unrealized P&L as a percentage of the residual cost basis (Unrealized P&L / cost basis).'),
            type: 'number',
            align: 'right',
            width: 210,
            minWidth: 190,
            sortable: true,
            filterable: false,
            getValue: (row) => row.unrealizedPnl ?? 0,
            cell: (row) => signedAmountWithPercentCell(row.unrealizedPnl, row.unrealizedPnlPercent),
        },
    ]);

    let emptyMessage = $derived(label('brokers.lots.noOpenLots', 'No open lots'));
</script>

<section class="rounded-lg border border-gray-200/80 bg-gray-50/80 dark:border-slate-700 dark:bg-slate-900/30" data-testid="open-lots-table">
    <div class="flex items-center justify-between gap-3 border-b border-gray-200/80 px-4 py-3 dark:border-slate-700">
        <button class="flex min-w-0 flex-1 items-center justify-between gap-3 rounded-md text-left transition-colors hover:bg-gray-100/80 dark:hover:bg-slate-800/60" onclick={() => (expanded = !expanded)} aria-expanded={expanded} data-testid="open-lots-toggle" type="button">
            <span class="flex min-w-0 items-center gap-2">
                {#if expanded}
                    <ChevronDown size={16} class="shrink-0 text-gray-500 dark:text-gray-400" />
                {:else}
                    <ChevronRight size={16} class="shrink-0 text-gray-500 dark:text-gray-400" />
                {/if}
                <span class="text-base font-semibold text-gray-900 dark:text-gray-100">
                    {label('brokers.lots.openLots', 'Open Lots')}
                </span>
            </span>
            <span class="inline-flex min-w-7 items-center justify-center rounded-full bg-gray-200 px-2 py-0.5 text-xs font-semibold tabular-nums text-gray-700 dark:bg-slate-700 dark:text-gray-200">
                {lots.length}
            </span>
        </button>
        <div class="shrink-0">
            <ColumnVisibilityToggle {tableRef} />
        </div>
    </div>

    {#if expanded}
        <div class="open-lots-table-wrap px-4 py-3" transition:slide={{duration: 200}}>
            <DataTable
                bind:this={tableRef}
                data={rows}
                {columns}
                getRowId={(row) => row.rowId}
                {getRowClass}
                getRowStyle={(row) => brokerStyle(row.brokerId)}
                storageKey="broker-open-lots-v1"
                enableSelection={false}
                selectionMode="none"
                enableActions={false}
                enablePagination={false}
                enableColumnVisibility={false}
                enableColumnFilters={false}
                enableSorting={true}
                enableColumnResize={true}
                enableContextMenu={false}
                tableLayout="fixed"
                {emptyMessage}
            />
        </div>
    {/if}
</section>

<style>
    :global {
        .open-lots-table-wrap tr.lot-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 30%, white);
        }
        .dark .open-lots-table-wrap tr.lot-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 15%, #0f0f18);
        }
        .open-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 75%, white);
        }
        .dark .open-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 22%, #0f0f18);
        }
    }
</style>
