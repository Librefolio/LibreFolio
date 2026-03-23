<!--
  AssetTable — Table view for assets list using DataTable.
  Columns: Icon, Name, Type (badge), Currency (flag), Last Price, Δ Abs, Δ %, Provider, Active, Actions.
  Svelte 5 runes, dark mode.
  Used by: /assets list page (table/list view)
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {Pencil, Trash2} from 'lucide-svelte';
    import {getCurrencyInfo, ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';

    // =========================================================================
    // Types
    // =========================================================================

    export interface AssetRow {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        has_provider: boolean;
        active: boolean;
        lastPrice?: number | null;
        deltaAbs?: number | null;
        deltaPercent?: number | null;
    }

    interface Props {
        data: AssetRow[];
        loading?: boolean;
        onedit?: (asset: AssetRow) => void;
        ondelete?: (asset: AssetRow) => void;
    }

    let {data = [], loading = false, onedit, ondelete}: Props = $props();

    ensureCurrenciesLoaded($currentLanguage);

    // =========================================================================
    // Helpers
    // =========================================================================

    function formatDelta(val: number | null | undefined, suffix: string = ''): string {
        if (val === null || val === undefined) return '—';
        const sign = val >= 0 ? '+' : '';
        return `${sign}${val.toFixed(2)}${suffix}`;
    }

    function deltaColorClass(val: number | null | undefined): string {
        if (val === null || val === undefined) return 'text-gray-400 dark:text-gray-500';
        return val >= 0
            ? 'text-emerald-600 dark:text-emerald-400'
            : 'text-red-500 dark:text-red-400';
    }

    function typeBadgeHtml(type: string | null | undefined): string {
        if (!type) return '<span class="text-gray-400">—</span>';
        const colors: Record<string, string> = {
            STOCK: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
            ETF: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
            BOND: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
            CRYPTO: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
            FUND: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400',
            HOLD: 'bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-400',
            CROWDFUND_LOAN: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
        };
        const cls = colors[type] ?? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400';
        return `<span class="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded ${cls}">${type}</span>`;
    }

    // =========================================================================
    // Columns
    // =========================================================================

    let columns = $derived<ColumnDef<AssetRow>[]>([
        {
            id: 'name',
            header: () => $t('assets.table.name'),
            cell: (row) => ({type: 'html', html: `<div class="flex items-center gap-2"><span class="font-medium text-gray-800 dark:text-gray-100">${row.display_name}</span></div>`}),
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
            enumOptions: ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND_LOAN', 'OTHER'].map(v => ({value: v, label: v})),
            getValue: (row) => row.asset_type ?? '',
            width: 110,
            minWidth: 80,
        },
        {
            id: 'currency',
            header: () => $t('assets.table.currency'),
            cell: (row) => {
                const info = getCurrencyInfo(row.currency);
                return {type: 'html', html: `<span class="emoji-flag">${info.flag_emoji}</span> ${row.currency}`};
            },
            type: 'text',
            getValue: (row) => row.currency,
            width: 90,
            minWidth: 70,
        },
        {
            id: 'lastPrice',
            header: () => $t('assets.table.lastPrice'),
            cell: (row) => row.lastPrice !== null && row.lastPrice !== undefined
                ? {type: 'html', html: `<span class="font-mono">${row.lastPrice.toFixed(2)}</span>`}
                : '—',
            type: 'number',
            getValue: (row) => row.lastPrice ?? 0,
            width: 110,
            minWidth: 80,
        },
        {
            id: 'deltaAbs',
            header: 'Δ Abs',
            cell: (row) => ({
                type: 'html' as const,
                html: `<span class="font-mono ${deltaColorClass(row.deltaAbs)}">${formatDelta(row.deltaAbs)}</span>`,
            }),
            type: 'number',
            getValue: (row) => row.deltaAbs ?? 0,
            width: 100,
            minWidth: 70,
        },
        {
            id: 'deltaPct',
            header: 'Δ %',
            cell: (row) => ({
                type: 'html' as const,
                html: `<span class="font-mono ${deltaColorClass(row.deltaPercent)}">${formatDelta(row.deltaPercent, '%')}</span>`,
            }),
            type: 'number',
            getValue: (row) => row.deltaPercent ?? 0,
            width: 90,
            minWidth: 70,
        },
        {
            id: 'provider',
            header: () => $t('assets.table.provider'),
            cell: (row) => ({
                type: 'html' as const,
                html: row.has_provider
                    ? '<span class="text-emerald-600 dark:text-emerald-400">✅</span>'
                    : '<span class="text-gray-400 dark:text-gray-500">❌</span>',
            }),
            type: 'enum',
            enumOptions: [{value: 'true', label: '✅ Yes'}, {value: 'false', label: '❌ No'}],
            getValue: (row) => String(row.has_provider),
            width: 80,
            minWidth: 60,
        },
        {
            id: 'active',
            header: () => $t('assets.table.active'),
            cell: (row) => ({
                type: 'html' as const,
                html: row.active
                    ? '<span class="text-emerald-600 dark:text-emerald-400">●</span>'
                    : '<span class="text-red-400 dark:text-red-500">●</span>',
            }),
            type: 'enum',
            enumOptions: [{value: 'true', label: 'Active'}, {value: 'false', label: 'Inactive'}],
            getValue: (row) => String(row.active),
            width: 70,
            minWidth: 50,
        },
    ]);
</script>

<DataTable
    {data}
    {columns}
    getRowId={(row) => String(row.id)}
    storageKey="assetsTable"
    onRowClick={(row) => goto(`/assets/${row.id}`)}
    enableSorting={true}
    enableColumnFilters={true}
    enablePagination={true}
    defaultPageSize={25}
    isLoading={loading}
    emptyMessage={$t('assets.empty.noAssets')}
    enableActions={true}
    rowActions={[
        {
            id: 'edit',
            label: () => $t('common.edit'),
            icon: Pencil,
            onClick: (row) => onedit?.(row),
        },
        {
            id: 'delete',
            label: () => $t('common.delete'),
            icon: Trash2,
            onClick: (row) => ondelete?.(row),
            variant: 'danger',
        },
    ]}
/>



