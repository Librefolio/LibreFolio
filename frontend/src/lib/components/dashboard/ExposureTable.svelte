<!--
  ExposureTable — Holdings snapshot table for open positions at the selected end date.

  Shows open holdings only (snapshot at date_to).
  Columns: Asset, Value, Weight, Unrealized P&L, P&L %, Quantity, Price, PMC, Broker.
  Sorted by value descending.

  Pattern: Svelte 5 Runes, DataTable, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import type {ColumnDef} from '$lib/components/table/types';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    interface Holding {
        asset_id: number;
        asset_name: string;
        asset_ticker?: string | (string | null)[] | null;
        asset_type: string;
        broker_id?: number | (number | null)[] | null;
        broker_name?: string | (string | null)[] | null;
        quantity?: string | (string | null)[] | null;
        wac_per_unit?: string | (string | null)[] | null;
        current_price?: string | (string | null)[] | null;
        current_value?: string | (string | null)[] | null;
        nav_weight_percent?: string | (string | null)[] | null;
        gain_loss?: string | (string | null)[] | null;
        gain_loss_percent?: string | (string | null)[] | null;
    }

    interface Props {
        holdings: Holding[];
        navAmount: number;
        displayCurrency: string;
        brokers?: ReadonlyArray<BrokerLike>;
    }

    interface DisplayRow {
        key: string;
        assetId: number;
        assetName: string;
        assetType: string;
        brokerId: number | null;
        brokerName: string;
        broker: BrokerLike | null;
        currentValue: number | null;
        navWeight: number | null;
        unrealizedPnl: number | null;
        unrealizedPnlPercent: number | null;
        quantity: number | null;
        price: number | null;
        wacPerUnit: number | null;
    }

    let {holdings = [], navAmount = 0, displayCurrency = 'EUR', brokers = [], ..._legacyProps}: Props & Record<string, unknown> = $props();
    void _legacyProps;

    onMount(async () => {
        await ensureAssetsLoaded();
    });

    function safeNum(v: string | (string | null)[] | null | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return isNaN(n) ? null : n;
    }

    function safeInt(v: number | (number | null)[] | null | undefined): number | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    function safeStr(v: string | (string | null)[] | null | undefined): string | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    function makePositionKey(assetId: number, brokerId: number | null): string {
        return `${assetId}-${brokerId ?? 0}`;
    }

    function escapeHtml(s: string): string {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function signedAmountCell(value: number | null) {
        if (value == null) return '—';
        const classes = value > 0 ? 'text-green-600 dark:text-green-400' : value < 0 ? 'text-red-500 dark:text-red-400' : 'text-gray-500 dark:text-gray-400';
        return {
            type: 'html' as const,
            html: `<span class="font-medium ${classes}">${formatCurrencyAmountPlain(value, displayCurrency, {showSign: value !== 0})}</span>`,
        };
    }

    function percentChangeCell(value: number | null) {
        if (value == null) return '—';
        const pct = (value * 100).toFixed(2);
        const classes = value >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400';
        return {
            type: 'html' as const,
            html: `<span class="font-medium ${classes}">${value >= 0 ? '+' : ''}${pct}%</span>`,
        };
    }

    function formatQuantity(value: number | null): string {
        return value == null ? '—' : value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
    }

    let rows = $derived.by<DisplayRow[]>(() => {
        const brokerMap = new Map(brokers.map((broker) => [broker.id, broker]));

        return [...holdings]
            .map((holding) => {
                const brokerId = safeInt(holding.broker_id);
                const broker = brokerId == null ? null : (brokerMap.get(brokerId) ?? null);
                const currentValue = safeNum(holding.current_value);
                return {
                    key: makePositionKey(holding.asset_id, brokerId),
                    assetId: holding.asset_id,
                    assetName: holding.asset_name,
                    assetType: holding.asset_type,
                    brokerId,
                    brokerName: safeStr(holding.broker_name) || broker?.name || '—',
                    broker,
                    currentValue,
                    navWeight: safeNum(holding.nav_weight_percent) ?? (currentValue != null && navAmount > 0 ? (currentValue / navAmount) * 100 : null),
                    unrealizedPnl: safeNum(holding.gain_loss),
                    unrealizedPnlPercent: safeNum(holding.gain_loss_percent),
                    quantity: safeNum(holding.quantity),
                    price: safeNum(holding.current_price),
                    wacPerUnit: safeNum(holding.wac_per_unit),
                };
            })
            .filter((row) => row.quantity == null || row.quantity !== 0)
            .sort((a, b) => (b.currentValue ?? 0) - (a.currentValue ?? 0));
    });

    let columns = $derived.by<ColumnDef<DisplayRow>[]>(() => {
        const assetColumn: ColumnDef<DisplayRow> = {
            id: 'asset',
            header: () => $_('common.asset'),
            type: 'text',
            width: 240,
            minWidth: 220,
            maxWidth: 420,
            resizable: true,
            sortable: true,
            getValue: (row) => row.assetName,
            cell: (row) => {
                const info = getAssetInfo(row.assetId);
                const typeIconSrc = info?.icon_url || getAssetTypeIconUrl(row.assetType) || '';
                const name = escapeHtml(row.assetName);
                const typeIconHtml = typeIconSrc ? `<img src="${escapeHtml(typeIconSrc)}" alt="${escapeHtml(row.assetType)}" class="w-4 h-4 rounded object-contain shrink-0" onerror="this.style.display='none'" />` : '';
                return {
                    type: 'html',
                    html: `<div class="flex items-center gap-1.5 min-w-0">${typeIconHtml}<span class="truncate font-medium text-gray-700 dark:text-gray-200">${name}</span></div>`,
                };
            },
        };

        const brokerColumn: ColumnDef<DisplayRow> = {
            id: 'broker',
            header: () => $_('brokers.title') || 'Broker',
            type: 'text',
            width: 130,
            minWidth: 120,
            maxWidth: 220,
            resizable: true,
            sortable: true,
            getValue: (row) => row.brokerName,
            cell: (row) => {
                const broker = row.broker;
                if (!broker && row.brokerId == null) return '—';
                return {
                    type: 'custom',
                    component: BrokerBadge,
                    props: {
                        broker: broker ?? {id: row.brokerId ?? 0, name: row.brokerName},
                        size: 16,
                        showName: true,
                        tooltip: row.brokerName,
                    },
                };
            },
        };

        return [
            assetColumn,
            {
                id: 'value',
                header: () => $_('common.value'),
                type: 'number',
                align: 'right',
                width: 180,
                minWidth: 160,
                maxWidth: 280,
                resizable: true,
                sortable: true,
                getValue: (row) => row.currentValue ?? 0,
                cell: (row) => (row.currentValue == null ? '—' : formatCurrencyAmountPlain(row.currentValue, displayCurrency)),
            },
            {
                id: 'weight',
                header: () => $_('dashboard.navWeight') || 'Weight',
                type: 'number',
                align: 'right',
                width: 100,
                minWidth: 90,
                maxWidth: 160,
                resizable: true,
                sortable: true,
                getValue: (row) => row.navWeight ?? 0,
                cell: (row) => (row.navWeight == null ? '—' : `${row.navWeight.toFixed(1)}%`),
            },
            {
                id: 'pnl',
                header: () => $_('dashboard.unrealizedPnl'),
                type: 'number',
                align: 'right',
                width: 180,
                minWidth: 160,
                maxWidth: 280,
                resizable: true,
                sortable: true,
                getValue: (row) => row.unrealizedPnl ?? 0,
                cell: (row) => signedAmountCell(row.unrealizedPnl),
            },
            {
                id: 'pnl-percent',
                header: () => $_('dashboard.unrealizedPnlPercent') || 'P&L %',
                headerTooltip: () => $_('dashboard.unrealizedPnlPercentTooltip') || 'Unrealized P&L as a percentage of the residual cost basis (Unrealized P&L / cost basis).',
                type: 'number',
                align: 'right',
                width: 110,
                minWidth: 100,
                maxWidth: 180,
                resizable: true,
                sortable: true,
                getValue: (row) => row.unrealizedPnlPercent ?? 0,
                cell: (row) => percentChangeCell(row.unrealizedPnlPercent),
            },
            {
                id: 'quantity',
                header: () => $_('dashboard.quantity') || 'Quantity',
                type: 'number',
                align: 'right',
                width: 120,
                minWidth: 100,
                maxWidth: 200,
                resizable: true,
                sortable: true,
                getValue: (row) => row.quantity ?? 0,
                cell: (row) => `${formatQuantity(row.quantity)} 📈`,
            },
            {
                id: 'price',
                header: () => $_('dashboard.price') || 'Price',
                type: 'number',
                align: 'right',
                width: 180,
                minWidth: 160,
                maxWidth: 280,
                resizable: true,
                sortable: true,
                getValue: (row) => row.price ?? 0,
                cell: (row) => (row.price == null ? '—' : formatCurrencyAmountPlain(row.price, displayCurrency)),
            },
            {
                id: 'pmc',
                header: () => $_('dashboard.pmc') || 'PMC',
                headerTooltip: () => $_('dashboard.pmcTooltip') || 'Average cost per unit of the currently open position.',
                type: 'number',
                align: 'right',
                width: 180,
                minWidth: 160,
                maxWidth: 280,
                resizable: true,
                sortable: true,
                getValue: (row) => row.wacPerUnit ?? 0,
                cell: (row) => (row.wacPerUnit == null ? '—' : formatCurrencyAmountPlain(row.wacPerUnit, displayCurrency)),
            },
            brokerColumn,
        ];
    });

    let tableEmptyMessage = $derived($_('dashboard.noPositions') || 'No holdings at the selected date');

    function goToAssetDetail(row: DisplayRow) {
        void goto(`/assets/${row.assetId}`);
    }
</script>

<div data-testid="exposure-table">
    <DataTable
        data={rows}
        {columns}
        getRowId={(row) => row.key}
        storageKey="dashboard-holdings-v3"
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
        emptyMessage={tableEmptyMessage}
        onRowDoubleClick={goToAssetDetail}
    />
</div>
