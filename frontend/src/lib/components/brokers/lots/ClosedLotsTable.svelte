<!--
  ClosedLotsTable — fully realized FIFO lots for broker detail inline panel.
  Uses generic DataTable and forwards navigateToRowId for bubble → row pulse, and
  onRowDoubleClick (double-click/long-press) for the reverse row → bubble pulse.
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

    type ClosedLotSchema = z.infer<typeof schemas.ClosedLotSchema>;

    interface Props {
        lots: ReadonlyArray<ClosedLotSchema>;
        currency: string;
        brokers?: ReadonlyArray<BrokerLike>;
        /** "Row → bubble" — fired on double-click (desktop) or long-press (mobile) of a row. */
        onRowDoubleClick?: (buyTransactionId: number) => void;
    }

    interface DisplayRow {
        rowId: string;
        buyTransactionId: number;
        brokerId: number;
        brokerName: string;
        broker: BrokerLike | null;
        buyDate: string;
        sellDate: string;
        quantity: number | null;
        sellPrice: number | null;
        realizedPnl: number | null;
    }

    let {lots = [], currency, brokers = [], onRowDoubleClick}: Props = $props();

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

    function safeNum(value: string): number | null {
        const parsed = Number.parseFloat(value);
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

    function signedAmountCell(value: number | null) {
        if (value == null) return '—';
        const classes = value > 0 ? 'text-green-600 dark:text-green-400' : value < 0 ? 'text-red-500 dark:text-red-400' : 'text-gray-500 dark:text-gray-400';
        return {
            type: 'html' as const,
            html: `<span class="font-medium tabular-nums ${classes}">${formatCurrencyAmountPlain(value, currency, {showSign: value !== 0})}</span>`,
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
            return {
                // Same buy tx can feed multiple sales; composite key avoids row-id collisions.
                rowId: `${lot.buy_transaction_id}-${lot.sell_transaction_id}`,
                buyTransactionId: lot.buy_transaction_id,
                brokerId: lot.broker_id,
                brokerName: broker?.name ?? `#${lot.broker_id}`,
                broker,
                buyDate: lot.buy_date,
                sellDate: lot.sell_date,
                quantity: safeNum(lot.quantity),
                sellPrice: safeNum(lot.sell_price),
                realizedPnl: safeNum(lot.realized_pnl),
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
            id: 'sell-date',
            header: () => label('brokers.lots.sellDate', 'Sell Date'),
            cell: (row) => ({type: 'date', value: row.sellDate, format: 'date'}),
            type: 'date',
            width: 130,
            minWidth: 120,
            sortable: true,
            filterable: false,
            getValue: (row) => row.sellDate,
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
            width: 130,
            minWidth: 120,
            sortable: true,
            filterable: false,
            getValue: (row) => row.quantity ?? 0,
            cell: (row) => ({
                type: 'html',
                html: `<span class="font-medium tabular-nums text-gray-700 dark:text-gray-200">${formatQuantity(row.quantity)}</span>`,
            }),
        },
        {
            id: 'sell-price',
            header: () => label('brokers.lots.sellPrice', 'Sell Price'),
            type: 'number',
            align: 'right',
            width: 170,
            minWidth: 150,
            sortable: true,
            filterable: false,
            getValue: (row) => row.sellPrice ?? 0,
            cell: (row) => amountCell(row.sellPrice),
        },
        {
            id: 'realized-pnl',
            header: () => label('brokers.lots.realizedPnl', 'Realized P&L'),
            type: 'number',
            align: 'right',
            width: 190,
            minWidth: 170,
            sortable: true,
            filterable: false,
            getValue: (row) => row.realizedPnl ?? 0,
            cell: (row) => signedAmountCell(row.realizedPnl),
        },
    ]);

    let emptyMessage = $derived(label('brokers.lots.noClosedLots', 'No closed lots'));
</script>

<section class="rounded-lg border border-gray-200/80 bg-gray-50/80 dark:border-slate-700 dark:bg-slate-900/30" data-testid="closed-lots-table">
    <div class="flex items-center justify-between gap-3 border-b border-gray-200/80 px-4 py-3 dark:border-slate-700">
        <button class="flex min-w-0 flex-1 items-center justify-between gap-3 rounded-md text-left transition-colors hover:bg-gray-100/80 dark:hover:bg-slate-800/60" onclick={() => (expanded = !expanded)} aria-expanded={expanded} data-testid="closed-lots-toggle" type="button">
            <span class="flex min-w-0 items-center gap-2">
                {#if expanded}
                    <ChevronDown size={16} class="shrink-0 text-gray-500 dark:text-gray-400" />
                {:else}
                    <ChevronRight size={16} class="shrink-0 text-gray-500 dark:text-gray-400" />
                {/if}
                <span class="text-base font-semibold text-gray-900 dark:text-gray-100">
                    {label('brokers.lots.closedLots', 'Closed Lots')}
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
        <div class="closed-lots-table-wrap px-4 py-3" transition:slide={{duration: 200}}>
            <DataTable
                bind:this={tableRef}
                data={rows}
                {columns}
                getRowId={(row) => row.rowId}
                {getRowClass}
                getRowStyle={(row) => brokerStyle(row.brokerId)}
                storageKey="broker-closed-lots-v1"
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
                onRowDoubleClick={(row) => onRowDoubleClick?.(row.buyTransactionId)}
            />
        </div>
    {/if}
</section>

<style>
    @keyframes tinted-lot-highlight-pulse {
        0%,
        100% {
            background: var(--lot-highlight-base) !important;
        }
        50% {
            background: var(--lot-highlight-peak) !important;
        }
    }

    :global {
        .closed-lots-table-wrap tr.lot-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 30%, white);
        }
        .dark .closed-lots-table-wrap tr.lot-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 15%, #0f0f18);
        }
        .closed-lots-table-wrap tr.lot-row-tinted.highlighted > td {
            --lot-highlight-base: #f3e8ff;
            --lot-highlight-peak: #e9d5ff;
            background: var(--lot-highlight-base) !important;
            animation: tinted-lot-highlight-pulse 0.6s ease-in-out 3;
        }
        .dark .closed-lots-table-wrap tr.lot-row-tinted.highlighted > td {
            --lot-highlight-base: rgba(147, 51, 234, 0.25);
            --lot-highlight-peak: rgba(147, 51, 234, 0.4);
            background: var(--lot-highlight-base) !important;
        }
        .closed-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 75%, white);
        }
        .dark .closed-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 22%, #0f0f18);
        }
    }
</style>
