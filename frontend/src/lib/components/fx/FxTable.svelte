<!--
  FxTable — Table view for FX pairs list using DataTable.
  Columns: Swap ⇄, Pair (flag+code), Rate, Δ Abs, Δ %, Provider(s), Manual-Only badge, Actions.
  Swap button uses fxCardInversionStore.
  Svelte 5 runes, dark mode.
  Used by: /fx list page (table/list view)
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {ArrowLeftRight, Pencil, Trash2} from 'lucide-svelte';
    import {isCardInverted, setCardInverted} from '$lib/stores/fxCardInversionStore';
    import {getCurrencyInfo, ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';
    import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';

    // =========================================================================
    // Types
    // =========================================================================

    export interface FxRow {
        slug: string;
        base: string;
        quote: string;
        data: FxDataPoint[];
        manualOnly: boolean;
        providers: Array<{providerCode: string; priority: number}>;
    }

    interface Props {
        data: FxRow[];
        loading?: boolean;
        onedit?: (info: {base: string; quote: string; slug: string}) => void;
        ondelete?: (info: {base: string; quote: string; slug: string}) => void;
    }

    let {data = [], loading = false, onedit, ondelete}: Props = $props();

    ensureCurrenciesLoaded($currentLanguage);

    // =========================================================================
    // Helpers
    // =========================================================================

    // We need reactivity for inversion — use a version counter
    let inversionVersion = $state(0);

    function toggleInversion(slug: string) {
        const current = isCardInverted(slug);
        setCardInverted(slug, !current);
        inversionVersion++;
    }

    function getDisplayBase(row: FxRow): string {
        void inversionVersion; // register reactivity
        return isCardInverted(row.slug) ? row.quote : row.base;
    }

    function getDisplayQuote(row: FxRow): string {
        void inversionVersion;
        return isCardInverted(row.slug) ? row.base : row.quote;
    }

    function getRate(row: FxRow): number | null {
        void inversionVersion;
        if (row.data.length === 0) return null;
        const last = row.data[row.data.length - 1];
        return isCardInverted(row.slug) && last.rate !== 0 ? 1 / last.rate : last.rate;
    }

    function getDelta(row: FxRow): {abs: number | null; pct: number | null} {
        void inversionVersion;
        if (row.data.length < 2) return {abs: null, pct: null};
        const first = row.data[0];
        const last = row.data[row.data.length - 1];
        if (first.rate === 0 || last.rate === 0) return {abs: null, pct: null};
        const inv = isCardInverted(row.slug);
        const fv = inv ? 1 / first.rate : first.rate;
        const lv = inv ? 1 / last.rate : last.rate;
        return {
            abs: lv - fv,
            pct: ((lv - fv) / fv) * 100,
        };
    }

    function formatDelta(val: number | null, suffix: string = ''): string {
        if (val === null) return '—';
        const sign = val >= 0 ? '+' : '';
        return `${sign}${val.toFixed(4)}${suffix}`;
    }

    function formatDeltaPct(val: number | null): string {
        if (val === null) return '—';
        const sign = val >= 0 ? '+' : '';
        return `${sign}${val.toFixed(2)}%`;
    }

    function deltaColorClass(val: number | null): string {
        if (val === null) return 'text-gray-400 dark:text-gray-500';
        return val >= 0
            ? 'text-emerald-600 dark:text-emerald-400'
            : 'text-red-500 dark:text-red-400';
    }

    // =========================================================================
    // Columns
    // =========================================================================

    let columns = $derived<ColumnDef<FxRow>[]>([
        {
            id: 'swap',
            header: '⇄',
            cell: () => '', // Rendered via rowAction
            type: 'text',
            sortable: false,
            filterable: false,
            width: 40,
            minWidth: 40,
            maxWidth: 40,
        },
        {
            id: 'pair',
            header: () => $t('fx.filter.filterCurrency'),
            cell: (row) => {
                const db = getDisplayBase(row);
                const dq = getDisplayQuote(row);
                const bFlag = getCurrencyInfo(db).flag_emoji;
                const qFlag = getCurrencyInfo(dq).flag_emoji;
                return {type: 'html', html: `<span class="emoji-flag">${bFlag}</span> <span class="font-semibold">${db}</span> <span class="text-gray-400">→</span> <span class="emoji-flag">${qFlag}</span> <span class="font-semibold">${dq}</span>`};
            },
            type: 'text',
            getValue: (row) => `${getDisplayBase(row)}-${getDisplayQuote(row)}`,
            width: 180,
            minWidth: 140,
        },
        {
            id: 'rate',
            header: 'Rate',
            cell: (row) => {
                const r = getRate(row);
                return r !== null
                    ? {type: 'html', html: `<span class="font-mono font-bold">${r.toFixed(4)}</span>`}
                    : '—';
            },
            type: 'number',
            getValue: (row) => getRate(row) ?? 0,
            width: 110,
            minWidth: 80,
        },
        {
            id: 'deltaAbs',
            header: 'Δ Abs',
            cell: (row) => {
                const d = getDelta(row);
                return {type: 'html', html: `<span class="font-mono ${deltaColorClass(d.abs)}">${formatDelta(d.abs)}</span>`};
            },
            type: 'number',
            getValue: (row) => getDelta(row).abs ?? 0,
            width: 110,
            minWidth: 80,
        },
        {
            id: 'deltaPct',
            header: 'Δ %',
            cell: (row) => {
                const d = getDelta(row);
                return {type: 'html', html: `<span class="font-mono ${deltaColorClass(d.pct)}">${formatDeltaPct(d.pct)}</span>`};
            },
            type: 'number',
            getValue: (row) => getDelta(row).pct ?? 0,
            width: 90,
            minWidth: 70,
        },
        {
            id: 'providers',
            header: () => $t('fx.providers'),
            cell: (row) => {
                const codes = row.providers.map(p => p.providerCode).join(', ');
                return codes || '—';
            },
            type: 'text',
            getValue: (row) => row.providers.map(p => p.providerCode).join(', '),
            width: 140,
            minWidth: 100,
        },
        {
            id: 'manualOnly',
            header: 'Manual',
            cell: (row) => ({
                type: 'html',
                html: row.manualOnly
                    ? '<span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">✏️ Manual</span>'
                    : '',
            }),
            type: 'enum',
            enumOptions: [{value: 'true', label: 'Manual'}, {value: 'false', label: 'Auto'}],
            getValue: (row) => String(row.manualOnly),
            width: 80,
            minWidth: 60,
        },
    ]);
</script>

<DataTable
    {data}
    {columns}
    getRowId={(row) => row.slug}
    storageKey="fxTable"
    onRowClick={(row) => {
        const inv = isCardInverted(row.slug);
        const target = inv ? `${row.quote}-${row.base}` : row.slug;
        goto(`/fx/${target}`);
    }}
    enableSorting={true}
    enableColumnFilters={true}
    enablePagination={true}
    defaultPageSize={25}
    isLoading={loading}
    emptyMessage={$t('fx.empty.noPairsDesc')}
    enableActions={true}
    rowActions={[
        {
            id: 'swap',
            label: () => $t('common.swapDirection'),
            icon: ArrowLeftRight,
            onClick: (row) => toggleInversion(row.slug),
        },
        {
            id: 'edit',
            label: () => $t('common.edit'),
            icon: Pencil,
            onClick: (row) => onedit?.({base: row.base, quote: row.quote, slug: row.slug}),
        },
        {
            id: 'delete',
            label: () => $t('common.delete'),
            icon: Trash2,
            onClick: (row) => ondelete?.({base: row.base, quote: row.quote, slug: row.slug}),
            variant: 'danger',
        },
    ]}
/>


