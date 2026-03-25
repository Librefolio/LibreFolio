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
    import {ArrowLeftRight, RefreshCw, RotateCw, Trash2} from 'lucide-svelte';
    import {isCardInverted, setCardInverted} from '$lib/stores/fxCardInversionStore';
    import {getCurrencyInfo, ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {getCachedProviders} from '$lib/stores/currencyGraphStore';
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
        providers: Array<{providerCode: string; priority: number; chainSteps?: Array<{from: string; to: string; provider: string}>}>;
        deltas?: Record<string, number | null>;
    }

    interface Props {
        data: FxRow[];
        loading?: boolean;
        visiblePeriods?: ReadonlyArray<{key: string; days: number}>;
        onsync?: (info: {base: string; quote: string; slug: string}) => void;
        onrefresh?: (info: {base: string; quote: string; slug: string}) => void;
        ondelete?: (info: {base: string; quote: string; slug: string}) => void;
        onselectionchange?: (rows: FxRow[]) => void;
    }

    let {data = [], loading = false, visiblePeriods = [], onsync, onrefresh, ondelete, onselectionchange}: Props = $props();

    ensureCurrenciesLoaded($currentLanguage);

    /** Exposed DataTable ref for ColumnVisibilityToggle */
    let tableRef: DataTable<FxRow> | undefined = $state(undefined);
    export function getTableRef() { return tableRef; }

    /** Track rows currently being refreshed/synced for spin animation */
    let refreshingRowIds = $state(new Set<string>());
    let syncingRowIds = $state(new Set<string>());

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

    // Provider chain rendering helpers
    const PROVIDER_COLORS: Record<string, string> = {
        ECB: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
        FRANKFURTER: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
        FIXED_RATE: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
        MANUAL: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    };
    const DEFAULT_PROVIDER_COLOR = 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400';

    /** Build provider icon or 2-char initials fallback */
    function providerIconHtml(providerCode: string): string {
        const providers = getCachedProviders();
        const info = providers.find(p => p.code === providerCode);
        const cls = PROVIDER_COLORS[providerCode] ?? DEFAULT_PROVIDER_COLOR;
        if (info?.icon_url) {
            // Icon-only: show just the icon with tooltip for the code
            return `<span class="inline-flex items-center px-1 py-0.5 rounded ${cls}" title="${providerCode}"><img src="${info.icon_url}" alt="${providerCode}" class="w-3.5 h-3.5 rounded-sm object-contain" onerror="this.parentElement.textContent='${providerCode.slice(0,2)}'" /></span>`;
        }
        // Fallback: text code with colored background
        return `<span class="inline-flex items-center px-1 py-0.5 text-[9px] font-medium rounded ${cls}">${providerCode}</span>`;
    }

    function providerChainHtml(row: FxRow): string {
        const prov = row.providers[0]; // Primary provider (highest priority)
        if (!prov) return '—';
        const steps = prov.chainSteps;
        if (steps && steps.length > 0) {
            // Chain route: flag FROM → [icon PROVIDER] → flag TO for each step
            const parts: string[] = [];
            for (let i = 0; i < steps.length; i++) {
                const step = steps[i];
                const fromFlag = getCurrencyInfo(step.from).flag_emoji;
                const toFlag = getCurrencyInfo(step.to).flag_emoji;
                if (i === 0) {
                    parts.push(`<span class="emoji-flag text-[10px]">${fromFlag}</span>`);
                }
                parts.push(`<span class="text-gray-400 text-[8px]">⇆</span>`);
                parts.push(providerIconHtml(step.provider));
                parts.push(`<span class="text-gray-400 text-[8px]">⇆</span>`);
                parts.push(`<span class="emoji-flag text-[10px]">${toFlag}</span>`);
            }
            return `<div class="flex items-center gap-0.5 flex-wrap">${parts.join('')}</div>`;
        }
        // Single provider, no steps detail
        return providerIconHtml(prov.providerCode);
    }

    // =========================================================================
    // Columns
    // =========================================================================

    let columns = $derived<ColumnDef<FxRow>[]>([
        {
            id: 'pair',
            header: () => $t('fx.filter.filterCurrency'),
            cell: (row) => {
                const db = getDisplayBase(row);
                const dq = getDisplayQuote(row);
                const bFlag = getCurrencyInfo(db).flag_emoji;
                const qFlag = getCurrencyInfo(dq).flag_emoji;
                const manualBadge = row.manualOnly
                    ? ' <span class="inline-flex items-center px-1 py-0.5 text-[9px] font-medium rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 ml-1">✏️</span>'
                    : '';
                return {type: 'html', html: `<span class="emoji-flag">${bFlag}</span> <span class="font-semibold">${db}</span> <span class="text-gray-400">→</span> <span class="emoji-flag">${qFlag}</span> <span class="font-semibold">${dq}</span>${manualBadge}`};
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
        // Dynamic delta period columns
        ...visiblePeriods.map(p => ({
            id: `delta_${p.key}`,
            header: `Δ ${p.key}`,
            cell: (row: FxRow) => {
                const val = row.deltas?.[p.key] ?? null;
                return {type: 'html' as const, html: `<span class="font-mono ${deltaColorClass(val)}">${formatDeltaPct(val)}</span>`};
            },
            type: 'number' as const,
            getValue: (row: FxRow) => row.deltas?.[p.key] ?? 0,
            width: 90,
            minWidth: 70,
        })),
        {
            id: 'providers',
            header: () => $t('fx.providers'),
            cell: (row) => ({type: 'html', html: providerChainHtml(row)}),
            type: 'text',
            getValue: (row) => row.providers.map(p => p.providerCode).join(', '),
            width: 160,
            minWidth: 100,
            hiddenByDefault: true,
            filterable: false,
        },
    ]);
</script>

<DataTable
    bind:this={tableRef}
    {data}
    {columns}
    getRowId={(row) => row.slug}
    storageKey="fxTable"
    onSelectionChange={(ids) => onselectionchange?.(data.filter(row => ids.includes(row.slug)))}
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
            id: 'sync',
            label: () => $t('common.sync'),
            icon: RotateCw,
            onClick: async (row) => {
                syncingRowIds = new Set([...syncingRowIds, row.slug]);
                try { await onsync?.({base: row.base, quote: row.quote, slug: row.slug}); }
                finally { syncingRowIds = new Set([...syncingRowIds].filter(id => id !== row.slug)); }
            },
            disabled: (row) => row.manualOnly,
            iconClass: (row) => syncingRowIds.has(row.slug) ? 'animate-spin' : '',
        },
        {
            id: 'refresh',
            label: () => $t('common.refresh'),
            icon: RefreshCw,
            onClick: async (row) => {
                refreshingRowIds = new Set([...refreshingRowIds, row.slug]);
                try { await onrefresh?.({base: row.base, quote: row.quote, slug: row.slug}); }
                finally { refreshingRowIds = new Set([...refreshingRowIds].filter(id => id !== row.slug)); }
            },
            iconClass: (row) => refreshingRowIds.has(row.slug) ? 'animate-spin' : '',
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


