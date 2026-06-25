<!--
  AssetTable — Table view for assets list using DataTable.
  Columns: Icon, Name, Type (badge), Currency (flag), Last Price, Δ multi-period, Provider, Active, Actions.
  Dynamic Δ columns based on visiblePeriods prop.
  Svelte 5 runes, dark mode.
  Used by: /assets list page (table/list view)
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {RefreshCw, RotateCw, Trash2} from 'lucide-svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo, currencyStoreVersion} from '$lib/stores/reference/currencyStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import {assetProviderBadgeHtml, assetProvidersVersion, ensureAssetProvidersCached} from '$lib/utils/providerHelpers';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import type {LivePriceDirection} from '$lib/services/livePriceService';

    // =========================================================================
    // Types
    // =========================================================================

    export interface AssetRow {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        provider_code?: string | null;
        active: boolean;
        lastPrice?: number | null;
        deltaAbs?: number | null;
        deltaPercent?: number | null;
        deltas?: Record<string, number | null>;
    }

    interface Props {
        data: AssetRow[];
        loading?: boolean;
        visiblePeriods?: ReadonlyArray<{key: string; days: number}>;
        /** Live price data (asset_id → {value, direction}) for flash effect */
        livePriceMap?: Map<number, {value: number; direction: LivePriceDirection}>;
        /** Date range start (passed to detail page on row click) */
        dateStart?: string;
        /** Date range end (passed to detail page on row click) */
        dateEnd?: string;
        onsync?: (asset: AssetRow) => void;
        onrefresh?: (asset: AssetRow) => void;
        ondelete?: (asset: AssetRow) => void;
        onselectionchange?: (rows: AssetRow[]) => void;
    }

    let {data = [], loading = false, visiblePeriods = [], livePriceMap = new Map(), dateStart, dateEnd, onsync, onrefresh, ondelete, onselectionchange}: Props = $props();

    ensureCurrenciesLoaded($currentLanguage);
    ensureAssetProvidersCached();

    /** Exposed DataTable ref for ColumnVisibilityToggle */
    let tableRef: DataTable<AssetRow> | undefined = $state(undefined);

    export function getTableRef() {
        return tableRef;
    }

    /** Track rows currently being refreshed/synced for spin animation */
    let refreshingRowIds = $state(new Set<string>());
    let syncingRowIds = $state(new Set<string>());

    // =========================================================================
    // Helpers
    // =========================================================================

    function assetIconHtml(row: AssetRow): string {
        const iconSrc = row.icon_url || (row.asset_type ? getAssetTypeIconUrl(row.asset_type) : null);
        if (iconSrc) {
            return `<img src="${iconSrc}" alt="" class="w-5 h-5 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />`;
        }
        return `<div class="w-5 h-5 rounded-full bg-libre-green/10 flex items-center justify-center shrink-0 text-libre-green"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg></div>`;
    }

    function formatDelta(val: number | null | undefined, suffix: string = ''): string {
        if (val === null || val === undefined) return '—';
        const num = Number(val);
        const sign = num >= 0 ? '+' : '';
        return `${sign}${num.toFixed(2)}${suffix}`;
    }

    function deltaColorClass(val: number | null | undefined): string {
        if (val === null || val === undefined) return 'text-gray-400 dark:text-gray-500';
        return Number(val) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400';
    }

    function typeBadgeHtml(type: string | null | undefined): string {
        if (!type) return '<span class="text-gray-400">—</span>';
        const imgSrc = getAssetTypeIconUrl(type);
        const colors: Record<string, string> = {
            STOCK: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
            ETF: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
            BOND: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
            CRYPTO: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
            FUND: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400',
            HOLD: 'bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-400',
            CROWDFUND_LOAN: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
            INDEX: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
        };
        const cls = colors[type] ?? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400';
        const label = $t(`assets.types.${type}`) || type;
        return `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded ${cls}"><img src="${imgSrc}" alt="" class="w-3.5 h-3.5 object-contain" onerror="this.style.display='none'" />${label}</span>`;
    }

    // =========================================================================
    // Columns
    // =========================================================================

    let columns = $derived<ColumnDef<AssetRow>[]>(
        (void $assetProvidersVersion, // trigger re-derive when asset provider icons are cached
        [
            {
                id: 'name',
                header: () => $t('assets.table.name'),
                cell: (row) => {
                    const icon = assetIconHtml(row);
                    const activeDot = row.active ? '<span class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>' : '<span class="w-2 h-2 rounded-full bg-red-400 shrink-0"></span>';
                    return {
                        type: 'html',
                        html: `<div class="flex items-center gap-2">${icon}<span class="font-medium text-gray-800 dark:text-gray-100">${row.display_name}</span>${activeDot}</div>`,
                    };
                },
                type: 'text',
                getValue: (row) => row.display_name,
                width: 220,
                minWidth: 150,
            },
            {
                id: 'type',
                header: () => $t('common.type'),
                cell: (row) => ({type: 'html', html: typeBadgeHtml(row.asset_type)}),
                type: 'enum',
                enumOptions: ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND_LOAN', 'OTHER'].map((v) => ({value: v, label: $t(`assets.types.${v}`) || v})),
                getValue: (row) => row.asset_type ?? '',
                filterable: false,
                width: 70,
                minWidth: 40,
            },
            {
                id: 'currency',
                header: () => $t('common.currency'),
                cell: (row) => {
                    const info = getCurrencyInfo(row.currency);
                    return {type: 'html', html: `<span class="emoji-flag">${info.flag_emoji}</span> ${row.currency}`};
                },
                type: 'text',
                getValue: (row) => row.currency,
                filterable: false,
                width: 90,
                minWidth: 70,
            },
            {
                id: 'lastPrice',
                header: () => $t('assets.table.lastPrice'),
                cell: (row) => {
                    void $currencyStoreVersion;
                    const live = livePriceMap.get(row.id);
                    const price = live?.value ?? row.lastPrice;
                    if (price == null) return '—';
                    const dir = live?.direction ?? 'neutral';
                    const colorCls = dir === 'up' ? 'text-emerald-600 dark:text-emerald-400' : dir === 'down' ? 'text-red-500 dark:text-red-400' : '';
                    const inner = formatCurrencyAmountHtml(price, row.currency);
                    return {
                        type: 'html',
                        html: `<span class="font-mono transition-colors duration-300 ${colorCls}">${inner}</span>`,
                    };
                },
                type: 'currency-stack',
                getCurrencyValue: (row) => {
                    const live = livePriceMap.get(row.id);
                    const price = live?.value ?? row.lastPrice;
                    return price != null ? {code: row.currency, amount: price} : null;
                },
                getValue: (row) => livePriceMap.get(row.id)?.value ?? row.lastPrice ?? 0,
                width: 150,
                minWidth: 100,
            },
            // Dynamic Δ multi-period columns
            ...visiblePeriods.map((period) => ({
                id: `delta_${period.key}`,
                header: `Δ ${period.key}`,
                cell: (row: AssetRow) => {
                    const val = row.deltas?.[period.key] ?? null;
                    return {
                        type: 'html' as const,
                        html: `<span class="font-mono ${deltaColorClass(val)}">${formatDelta(val, '%')}</span>`,
                    };
                },
                type: 'number' as const,
                getValue: (row: AssetRow) => row.deltas?.[period.key] ?? 0,
                width: 80,
                minWidth: 60,
            })),
            {
                id: 'provider',
                header: () => $t('assets.table.provider'),
                cell: (row) => ({
                    type: 'html' as const,
                    html: row.provider_code ? assetProviderBadgeHtml(row.provider_code) : '<span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">✏️ Manual</span>',
                }),
                type: 'text',
                getValue: (row) => row.provider_code ?? '',
                width: 240,
                minWidth: 160,
                filterable: false,
            },
        ]),
    );
</script>

<DataTable
    bind:this={tableRef}
    {columns}
    {data}
    defaultPageSize={25}
    emptyMessage={$t('assets.empty.noAssets')}
    enableActions={true}
    enableColumnFilters={true}
    enablePagination={true}
    enableSorting={true}
    getRowId={(row) => String(row.id)}
    isLoading={loading}
    onRowClick={(row) => goto(`/assets/${row.id}${dateStart && dateEnd ? `?start=${dateStart}&end=${dateEnd}` : ''}`)}
    getRowHref={(row) => `/assets/${row.id}${dateStart && dateEnd ? `?start=${dateStart}&end=${dateEnd}` : ''}`}
    onSelectionChange={(ids) => onselectionchange?.(data.filter((row) => ids.includes(String(row.id))))}
    rowActions={[
        {
            id: 'sync',
            label: 'Sync',
            icon: RotateCw,
            onClick: async (row) => {
                const rid = String(row.id);
                syncingRowIds = new Set([...syncingRowIds, rid]);
                try {
                    await onsync?.(row);
                } finally {
                    syncingRowIds = new Set([...syncingRowIds].filter((id) => id !== rid));
                }
            },
            disabled: (row) => !row.provider_code,
            iconClass: (row) => (syncingRowIds.has(String(row.id)) ? 'animate-spin' : ''),
        },
        {
            id: 'refresh',
            label: () => $t('common.refresh'),
            icon: RefreshCw,
            onClick: async (row) => {
                const rid = String(row.id);
                refreshingRowIds = new Set([...refreshingRowIds, rid]);
                try {
                    await onrefresh?.(row);
                } finally {
                    refreshingRowIds = new Set([...refreshingRowIds].filter((id) => id !== rid));
                }
            },
            iconClass: (row) => (refreshingRowIds.has(String(row.id)) ? 'animate-spin' : ''),
        },
        {
            id: 'delete',
            label: () => $t('common.delete'),
            icon: Trash2,
            onClick: (row) => ondelete?.(row),
            variant: 'danger',
        },
    ]}
    storageKey="assetsTable"
/>
