<!--
  ContributionTable file name kept for compatibility, but component now renders unified
  period-based Performance table for dashboard "Your Positions".

  Stage 3 integration contract:
  - `positions` must contain full backend dataset for selected period (open + closed together).
  - Parent must NOT pre-filter by `is_fully_sold`; native Status column filter handles view split.
  - Table stays period-based only (no holdings snapshot semantics mixed in).
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {ExternalLink, Layers} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';

    type NumericLike = string | (string | null)[] | null;
    type PositionStatus = 'open_at_period_end' | 'closed_by_period_end';

    interface HoldingSnapshot {
        asset_id: number;
        broker_id?: number | (number | null)[] | null;
        gain_loss_change_1d?: NumericLike;
        gain_loss_change_1d_percent?: NumericLike;
    }

    interface Position {
        asset_id: number;
        asset_name: string;
        asset_ticker?: string | (string | null)[] | null;
        asset_type: string;
        broker_id: number;
        broker_name: string;
        period_unrealized_delta?: NumericLike;
        period_realized_gain_loss?: NumericLike;
        period_income?: NumericLike;
        period_fees_taxes?: NumericLike;
        period_pnl?: NumericLike;
        period_pnl_percent?: NumericLike;
        start_value?: NumericLike;
        end_value?: NumericLike;
        is_fully_sold?: boolean;
    }

    interface Props {
        /** Full mixed dataset from backend. Do not pre-filter open/closed in parent. */
        positions: Position[];
        holdings?: HoldingSnapshot[];
        displayCurrency?: string;
        brokers?: ReadonlyArray<BrokerLike>;
        onAnalyze?: (assetId: number) => void;
    }

    let {positions = [], holdings = [], displayCurrency = 'EUR', brokers = [], onAnalyze}: Props = $props();

    let tableWrapperEl: HTMLDivElement | undefined = $state(undefined);

    // Cells are rendered as raw HTML strings (see the 'name' column below), so `use:` actions
    // can't attach to them directly — scan the wrapper for overflow-marquee candidates instead,
    // re-attaching automatically whenever rows are re-rendered (sort/filter/data refresh).
    onMount(() => {
        if (!tableWrapperEl) return;
        return attachOverflowMarqueeToDescendants(tableWrapperEl);
    });

    function safeNum(v: NumericLike | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return isNaN(n) ? null : n;
    }

    function safeInt(v: number | (number | null)[] | null | undefined): number | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    function makeHoldingLookupKey(assetId: number, brokerId: number | null): string {
        return `${assetId}-${brokerId ?? 0}`;
    }

    function statusFromSoldFlag(isFullySold: boolean): PositionStatus {
        return isFullySold ? 'closed_by_period_end' : 'open_at_period_end';
    }

    function label(key: string, fallback: string): string {
        const translated = $_(key) || fallback;
        return translated === key ? fallback : translated;
    }

    function statusLabel(status: PositionStatus): string {
        return status === 'closed_by_period_end' ? label('dashboard.closedByPeriodEnd', 'Closed by period end') : label('dashboard.openAtPeriodEnd', 'Open at period end');
    }

    interface DisplayRow {
        key: string;
        assetName: string;
        assetType: string;
        brokerId: number;
        brokerName: string;
        broker: BrokerLike | null;
        pnl: number | null;
        unrealizedDelta: number | null;
        realizedSales: number | null;
        income: number | null;
        costs: number | null;
        startValue: number | null;
        endValue: number | null;
        gainLossChange1d: number | null;
        gainLossChange1dPercent: number | null;
        status: PositionStatus;
        statusLabel: string;
        isFullySold: boolean;
        assetId?: number;
    }

    let displayRows = $derived.by(() => {
        const brokerMap = new Map(brokers.map((broker) => [broker.id, broker]));
        const holdingsByKey = new Map(
            holdings.map((holding) => [
                makeHoldingLookupKey(holding.asset_id, safeInt(holding.broker_id)),
                {
                    gainLossChange1d: safeNum(holding.gain_loss_change_1d),
                    gainLossChange1dPercent: safeNum(holding.gain_loss_change_1d_percent),
                },
            ]),
        );
        return positions
            .map((p) => {
                const isFullySold = p.is_fully_sold ?? false;
                const status = statusFromSoldFlag(isFullySold);
                const holdingMatch = holdingsByKey.get(makeHoldingLookupKey(p.asset_id, p.broker_id)) ?? null;
                return {
                    key: `pos-${p.broker_id}-${p.asset_id}`,
                    assetName: p.asset_name,
                    assetType: p.asset_type,
                    brokerId: p.broker_id,
                    brokerName: p.broker_name,
                    broker: brokerMap.get(p.broker_id) ?? null,
                    pnl: safeNum(p.period_pnl),
                    unrealizedDelta: safeNum(p.period_unrealized_delta),
                    realizedSales: safeNum(p.period_realized_gain_loss),
                    income: safeNum(p.period_income),
                    costs: safeNum(p.period_fees_taxes),
                    startValue: safeNum(p.start_value),
                    endValue: safeNum(p.end_value),
                    gainLossChange1d: holdingMatch?.gainLossChange1d ?? null,
                    gainLossChange1dPercent: holdingMatch?.gainLossChange1dPercent ?? null,
                    status,
                    statusLabel: statusLabel(status),
                    isFullySold,
                    assetId: p.asset_id,
                };
            })
            .sort((a, b) => Math.abs(b.pnl ?? 0) - Math.abs(a.pnl ?? 0));
    });

    function escapeHtml(s: string): string {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function signedAmountCell(value: number | null) {
        if (value == null) return '—';
        const classes = value > 0 ? 'text-green-600 dark:text-green-400' : value < 0 ? 'text-red-500 dark:text-red-400' : 'text-gray-500 dark:text-gray-400';
        return {
            type: 'html' as const,
            html: `<span class="font-medium tabular-nums ${classes}">${formatCurrencyAmountPlain(value, displayCurrency, {showSign: value !== 0})}</span>`,
        };
    }

    function amountCell(value: number | null) {
        if (value == null) return '—';
        return {
            type: 'html' as const,
            html: `<span class="font-medium tabular-nums text-gray-700 dark:text-gray-200">${formatCurrencyAmountPlain(value, displayCurrency)}</span>`,
        };
    }

    function percentChangeCell(value: number | null) {
        if (value == null) return '—';
        const classes = value >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400';
        return {
            type: 'html' as const,
            html: `<span class="font-medium tabular-nums ${classes}">${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%</span>`,
        };
    }

    function statusCell(row: DisplayRow) {
        const classes = row.isFullySold ? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';
        return {
            type: 'html' as const,
            html: `<span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${classes}">${escapeHtml(row.statusLabel)}</span>`,
        };
    }

    function assetIconSrc(r: DisplayRow): string | null {
        if (!r.assetId) return null;
        const info = getAssetInfo(r.assetId);
        return info?.icon_url || getAssetTypeIconUrl(r.assetType) || null;
    }

    function getRowClass(row: DisplayRow): string {
        return row.isFullySold ? 'italic' : '';
    }

    /** Desktop double-click / mobile long-press → asset detail page. The plain `goto()`
     *  push (not `enter`) keeps the shared dateRangeStore state as-is (only 'enter'
     *  navigations re-seed it from URL params) and lets the asset detail page's existing
     *  `goBack('/assets')` correctly pop back to the dashboard via navigationStore's stack. */
    function goToAssetDetail(row: DisplayRow) {
        if (row.assetId == null) return;
        void goto(`/assets/${row.assetId}`);
    }

    const rowActions: RowAction<DisplayRow>[] = [
        {
            id: 'view-asset',
            icon: ExternalLink,
            label: () => $_('brokers.lots.viewAsset') || 'View Asset',
            onClick: (row) => goToAssetDetail(row),
        },
        {
            id: 'analyze-lots',
            icon: Layers,
            label: () => $_('brokers.lots.analyze') || 'Analyze Lots',
            onClick: (row) => {
                if (row.assetId == null) return;
                onAnalyze?.(row.assetId);
            },
        },
    ];

    let columns = $derived.by<ColumnDef<DisplayRow>[]>(() => {
        const openStatusLabel = label('dashboard.openAtPeriodEnd', 'Open at period end');
        const closedStatusLabel = label('dashboard.closedByPeriodEnd', 'Closed by period end');

        return [
            {
                id: 'asset',
                header: () => label('common.asset', 'Asset'),
                type: 'text',
                width: 250,
                minWidth: 220,
                sortable: true,
                filterable: false,
                getValue: (row) => row.assetName,
                cell: (row) => {
                    const iconSrc = assetIconSrc(row);
                    const name = escapeHtml(row.assetName);
                    const iconHtml = iconSrc
                        ? `<img src="${escapeHtml(iconSrc)}" alt="" class="w-5 h-5 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />`
                        : `<div class="w-5 h-5 rounded-full bg-libre-green/10 flex items-center justify-center shrink-0 text-[10px] text-libre-green font-bold">${escapeHtml((row.assetName ?? '?')[0]?.toUpperCase() ?? '?')}</div>`;
                    return {
                        type: 'html',
                        html: `<div class="flex items-center gap-1.5 min-w-0"><span class="shrink-0">${iconHtml}</span><span class="flex-1 min-w-0 ${overflowScrollTextClass} font-medium text-gray-700 dark:text-gray-200" title="${name}">${name}</span></div>`,
                    };
                },
            },
            {
                id: 'pnl',
                header: () => label('dashboard.periodPnl', 'Period P&L'),
                headerTooltip: () => label('dashboard.periodPnlTooltip', 'Profit and loss generated during selected period.'),
                type: 'number',
                width: 170,
                minWidth: 150,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.pnl ?? 0,
                cell: (row) => signedAmountCell(row.pnl),
            },
            {
                id: 'unrealized-delta',
                header: () => label('dashboard.unrealizedDelta', 'Unrealized Δ'),
                type: 'number',
                width: 170,
                minWidth: 150,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.unrealizedDelta ?? 0,
                cell: (row) => signedAmountCell(row.unrealizedDelta),
            },
            {
                id: 'realized-sales',
                header: () => label('dashboard.realizedSales', 'Realized Sales'),
                type: 'number',
                width: 170,
                minWidth: 150,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.realizedSales ?? 0,
                cell: (row) => signedAmountCell(row.realizedSales),
            },
            {
                id: 'income',
                header: () => label('dashboard.income', 'Income'),
                type: 'number',
                width: 160,
                minWidth: 145,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.income ?? 0,
                cell: (row) => signedAmountCell(row.income),
            },
            {
                id: 'costs',
                header: () => label('dashboard.costs', 'Costs'),
                type: 'number',
                width: 160,
                minWidth: 145,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.costs ?? 0,
                cell: (row) => signedAmountCell(row.costs),
            },
            {
                id: 'start-value',
                header: () => label('dashboard.startValue', 'Start Value'),
                type: 'number',
                width: 170,
                minWidth: 150,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.startValue ?? 0,
                cell: (row) => amountCell(row.startValue),
            },
            {
                id: 'end-value',
                header: () => label('dashboard.endValue', 'End Value'),
                type: 'number',
                width: 170,
                minWidth: 150,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.endValue ?? 0,
                cell: (row) => amountCell(row.endValue),
            },
            {
                id: 'pnl-change-1d',
                header: () => label('dashboard.pnlChange1d', 'Δ P&L vs yesterday'),
                headerTooltip: () => label('dashboard.pnlChange1dTooltip', "Change in unrealized P&L vs yesterday, holding today's quantity constant."),
                type: 'number',
                width: 190,
                minWidth: 170,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.gainLossChange1d ?? 0,
                cell: (row) => signedAmountCell(row.gainLossChange1d),
            },
            {
                id: 'pnl-change-1d-percent',
                header: () => label('dashboard.pnlChange1dPercent', 'Δ P&L %'),
                headerTooltip: () => label('dashboard.pnlChange1dPercentTooltip', "Δ P&L vs yesterday as a percentage of yesterday's unrealized P&L."),
                type: 'number',
                width: 120,
                minWidth: 110,
                sortable: true,
                filterable: false,
                align: 'right',
                getValue: (row) => row.gainLossChange1dPercent ?? 0,
                cell: (row) => percentChangeCell(row.gainLossChange1dPercent != null ? row.gainLossChange1dPercent / 100 : null),
            },
            {
                id: 'status',
                header: () => label('dashboard.status', 'Status'),
                type: 'enum',
                width: 190,
                minWidth: 180,
                sortable: true,
                filterable: true,
                urlKey: 'status',
                enumOptions: [
                    {value: 'open_at_period_end', label: openStatusLabel},
                    {value: 'closed_by_period_end', label: closedStatusLabel},
                ],
                getValue: (row) => row.status,
                cell: (row) => statusCell(row),
            },
            {
                id: 'broker',
                header: () => label('transactions.table.broker', 'Broker'),
                type: 'text',
                width: 170,
                minWidth: 150,
                sortable: true,
                filterable: false,
                getValue: (row) => row.brokerName,
                cell: (row) => {
                    const broker = row.broker;
                    return {
                        type: 'custom',
                        component: BrokerBadge,
                        props: {
                            broker: broker ?? {id: row.brokerId, name: row.brokerName},
                            size: 16,
                            showName: true,
                            tooltip: row.brokerName,
                        },
                    };
                },
            },
        ];
    });
</script>

<div data-testid="contribution-table" bind:this={tableWrapperEl}>
    <DataTable
        data={displayRows}
        {columns}
        getRowId={(row) => row.key}
        storageKey="dashboard-performance"
        enableSelection={false}
        selectionMode="none"
        enableActions={true}
        enablePagination={false}
        enableColumnVisibility={false}
        enableColumnFilters={true}
        enableSorting={true}
        enableColumnResize={true}
        enableContextMenu={true}
        tableLayout="fixed"
        {rowActions}
        {getRowClass}
        emptyMessage={label('dashboard.noPeriodPnl', 'No period P&L data')}
    />
</div>
