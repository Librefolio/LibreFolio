<!--
  ExposureTable — Portfolio positions table using DataTable.

  Open mode: current holdings + period realized/costs merged from positions_contribution.
  Closed mode: fully sold positions from positions_contribution only.
  Sorted by value descending (open) or |period P&L| descending (closed).

  Pattern: Svelte 5 Runes, DataTable, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {onMount} from 'svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getBrokerInfo} from '$lib/stores/reference/brokerStore';
    import {getBrokerIconCandidates, ensurePluginIconsLoaded} from '$lib/utils/broker/brokerHelpers';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    interface Holding {
        asset_id: number;
        asset_name: string;
        asset_ticker?: string | (string | null)[] | null;
        asset_type: string;
        broker_id?: number | (number | null)[] | null;
        broker_name?: string | (string | null)[] | null;
        current_value?: string | (string | null)[] | null;
        nav_weight_percent?: string | (string | null)[] | null;
        gain_loss?: string | (string | null)[] | null;
        gain_loss_percent?: string | (string | null)[] | null;
        price_change_1d?: string | (string | null)[] | null;
    }

    interface Props {
        holdings: Holding[];
        navAmount: number;
        displayCurrency: string;
        positionFilter?: 'open' | 'closed';
        contribution?: PositionsContribution | null;
    }

    type ContributionPosition = NonNullable<PositionsContribution['positions']>[number];

    interface DisplayRow {
        key: string;
        assetId: number;
        assetName: string;
        assetType: string;
        brokerId: number | null;
        brokerName: string;
        currentValue: number | null;
        navWeight: number | null;
        unrealizedPnl: number | null;
        realized: number | null;
        costs: number | null;
        periodPnl: number | null;
        change1d: number | null;
    }

    let {
        holdings = [],
        displayCurrency = 'EUR',
        positionFilter = 'open',
        contribution = null,
    }: Props = $props();

    onMount(async () => {
        await Promise.all([ensureAssetsLoaded(), ensurePluginIconsLoaded()]);
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

    function getRealizedAmount(position: ContributionPosition | null | undefined): number {
        return (safeNum(position?.period_realized_gain_loss) ?? 0) + (safeNum(position?.period_income) ?? 0);
    }

    function getCostsAmount(position: ContributionPosition | null | undefined): number {
        return safeNum(position?.period_fees_taxes) ?? 0;
    }

    function escapeHtml(s: string): string {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function signedAmountCell(value: number | null) {
        if (value == null) return '—';
        const classes = value > 0
            ? 'text-green-600 dark:text-green-400'
            : value < 0
                ? 'text-red-500 dark:text-red-400'
                : 'text-gray-500 dark:text-gray-400';
        return {
            type: 'html' as const,
            html: `<span class="font-medium ${classes}">${formatCurrencyAmountPlain(value, displayCurrency, {showSign: value !== 0})}</span>`,
        };
    }

    function costsAmountCell(value: number | null) {
        if (value == null) return '—';
        if (value === 0) return {type: 'html' as const, html: `<span class="font-medium text-gray-500 dark:text-gray-400">${formatCurrencyAmountPlain(0, displayCurrency)}</span>`};
        const signedValue = -Math.abs(value);
        return {
            type: 'html' as const,
            html: `<span class="font-medium text-red-500 dark:text-red-400">${formatCurrencyAmountPlain(signedValue, displayCurrency, {showSign: true})}</span>`,
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

    let contributionMap = $derived.by(() => {
        const map = new Map<string, ContributionPosition>();
        for (const position of contribution?.positions ?? []) {
            map.set(makePositionKey(position.asset_id, position.broker_id), position);
        }
        return map;
    });

    let rows = $derived.by<DisplayRow[]>(() => {
        if (positionFilter === 'closed') {
            return (contribution?.positions ?? [])
                .filter((position) => position.is_fully_sold)
                .map((position) => ({
                    key: makePositionKey(position.asset_id, position.broker_id),
                    assetId: position.asset_id,
                    assetName: position.asset_name,
                    assetType: position.asset_type,
                    brokerId: position.broker_id,
                    brokerName: position.broker_name,
                    currentValue: null,
                    navWeight: null,
                    unrealizedPnl: null,
                    realized: getRealizedAmount(position),
                    costs: getCostsAmount(position),
                    periodPnl: safeNum(position.period_pnl) ?? 0,
                    change1d: null,
                }))
                .sort((a, b) => Math.abs(b.periodPnl ?? 0) - Math.abs(a.periodPnl ?? 0));
        }

        const contributionLoaded = contribution != null;
        return [...holdings]
            .map((holding) => {
                const brokerId = safeInt(holding.broker_id);
                const position = contributionMap.get(makePositionKey(holding.asset_id, brokerId));
                return {
                    key: makePositionKey(holding.asset_id, brokerId),
                    assetId: holding.asset_id,
                    assetName: holding.asset_name,
                    assetType: holding.asset_type,
                    brokerId,
                    brokerName: safeStr(holding.broker_name) || (brokerId ? getBrokerInfo(brokerId)?.name : null) || '—',
                    currentValue: safeNum(holding.current_value),
                    navWeight: safeNum(holding.nav_weight_percent),
                    unrealizedPnl: safeNum(holding.gain_loss),
                    realized: contributionLoaded ? (position ? getRealizedAmount(position) : 0) : null,
                    costs: contributionLoaded ? (position ? getCostsAmount(position) : 0) : null,
                    periodPnl: contributionLoaded ? (position ? (safeNum(position.period_pnl) ?? 0) : 0) : null,
                    change1d: safeNum(holding.price_change_1d),
                };
            })
            .sort((a, b) => (b.currentValue ?? 0) - (a.currentValue ?? 0));
    });

    let columns = $derived.by<ColumnDef<DisplayRow>[]>(() => {
        const baseColumns: ColumnDef<DisplayRow>[] = [
            {
                id: 'asset',
                header: () => $_('common.asset'),
                type: 'text',
                width: 200,
                sortable: true,
                getValue: (row) => row.assetName,
                cell: (row) => {
                    const info = getAssetInfo(row.assetId);
                    const typeIconSrc = getAssetTypeIconUrl(row.assetType) || '';
                    const name = escapeHtml(row.assetName);
                    const typeIconHtml = typeIconSrc ? `<img src="${escapeHtml(typeIconSrc)}" alt="${escapeHtml(row.assetType)}" class="w-4 h-4 rounded object-contain shrink-0" onerror="this.style.display='none'" />` : '';
                    return {
                        type: 'html',
                        html: `<div class="flex items-center gap-1.5 min-w-0">${typeIconHtml}<span class="truncate font-medium text-gray-700 dark:text-gray-200">${name}</span></div>`,
                    };
                },
            },
            {
                id: 'broker',
                header: () => $_('brokers.title'),
                type: 'text',
                width: 130,
                sortable: true,
                getValue: (row) => row.brokerName,
                cell: (row) => {
                    const broker = row.brokerId ? getBrokerInfo(row.brokerId) : null;
                    const candidates = getBrokerIconCandidates(broker);
                    // Build nested img chain: first tries candidate[0], onerror → tries next
                    let iconHtml = '';
                    if (candidates.length > 0) {
                        // Use first candidate; onerror hides it (remaining candidates handled by CSS)
                        const src = candidates[candidates.length - 1]; // prefer plugin icon (most reliable)
                        iconHtml = `<img src="${escapeHtml(src)}" alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" onerror="this.style.display='none'" />`;
                    }
                    return {
                        type: 'html',
                        html: `<div class="flex items-center gap-1 min-w-0">${iconHtml}<span class="truncate text-gray-500 dark:text-gray-400">${escapeHtml(row.brokerName)}</span></div>`,
                    };
                },
            },
        ];

        if (positionFilter === 'closed') {
            return [
                ...baseColumns,
                {
                    id: 'realized',
                    header: () => $_('dashboard.realized'),
                    type: 'number',
                    width: 120,
                    sortable: true,
                    getValue: (row) => row.realized ?? 0,
                    cell: (row) => signedAmountCell(row.realized),
                },
                {
                    id: 'costs',
                    header: () => $_('dashboard.costs'),
                    type: 'number',
                    width: 120,
                    sortable: true,
                    getValue: (row) => row.costs ?? 0,
                    cell: (row) => costsAmountCell(row.costs),
                },
                {
                    id: 'period-pnl',
                    header: () => $_('dashboard.periodPnl'),
                    type: 'number',
                    width: 120,
                    sortable: true,
                    getValue: (row) => row.periodPnl ?? 0,
                    cell: (row) => signedAmountCell(row.periodPnl),
                },
            ];
        }

        return [
            ...baseColumns,
            {
                id: 'value',
                header: () => $_('common.value'),
                type: 'number',
                width: 120,
                sortable: true,
                getValue: (row) => row.currentValue ?? 0,
                cell: (row) => row.currentValue == null ? '—' : formatCurrencyAmountPlain(row.currentValue, displayCurrency),
            },
            {
                id: 'weight',
                header: () => $_('dashboard.navWeight'),
                type: 'number',
                width: 80,
                sortable: true,
                getValue: (row) => row.navWeight ?? 0,
                cell: (row) => row.navWeight == null ? '—' : `${row.navWeight.toFixed(1)}%`,
            },
            {
                id: 'pnl',
                header: () => $_('dashboard.unrealizedPnl'),
                type: 'number',
                width: 120,
                sortable: true,
                getValue: (row) => row.unrealizedPnl ?? 0,
                cell: (row) => signedAmountCell(row.unrealizedPnl),
            },
            {
                id: 'realized',
                header: () => $_('dashboard.realized'),
                type: 'number',
                width: 120,
                sortable: true,
                getValue: (row) => row.realized ?? 0,
                cell: (row) => signedAmountCell(row.realized),
            },
            {
                id: 'costs',
                header: () => $_('dashboard.costs'),
                type: 'number',
                width: 120,
                sortable: true,
                getValue: (row) => row.costs ?? 0,
                cell: (row) => costsAmountCell(row.costs),
            },
            {
                id: 'change1d',
                header: () => 'Δ 1D',
                type: 'number',
                width: 80,
                sortable: true,
                getValue: (row) => row.change1d ?? 0,
                cell: (row) => percentChangeCell(row.change1d),
            },
        ];
    });

    let tableEmptyMessage = $derived(positionFilter === 'closed' ? $_('dashboard.noPeriodPnl') : $_('dashboard.noPositions'));
</script>

<div data-testid="exposure-table">
    <DataTable
        data={rows}
        {columns}
        getRowId={(row) => row.key}
        storageKey={`dashboard-exposure-${positionFilter}`}
        enableSelection={false}
        selectionMode="none"
        enableActions={false}
        enablePagination={false}
        enableColumnVisibility={false}
        enableColumnFilters={false}
        enableSorting={true}
        enableColumnResize={false}
        enableContextMenu={false}
        tableLayout="auto"
        emptyMessage={tableEmptyMessage}
    />
</div>
