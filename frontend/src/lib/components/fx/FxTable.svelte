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
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/currencyStore';
    import {fxProviderBadgeHtml} from '$lib/utils/providerHelpers';
    import {currentLanguage} from '$lib/stores/language';
    import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import {fxProvidersVersion} from '$lib/stores/currencyGraphStore';

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
        /** Date range start (passed to detail page on row click) */
        dateStart?: string;
        /** Date range end (passed to detail page on row click) */
        dateEnd?: string;
        onsync?: (info: {base: string; quote: string; slug: string}) => void;
        onrefresh?: (info: {base: string; quote: string; slug: string}) => void;
        ondelete?: (info: {base: string; quote: string; slug: string}) => void;
        onselectionchange?: (rows: FxRow[]) => void;
    }

    let {data = [], loading = false, visiblePeriods = [], dateStart, dateEnd, onsync, onrefresh, ondelete, onselectionchange}: Props = $props();

    ensureCurrenciesLoaded($currentLanguage);

    /** Exposed DataTable ref for ColumnVisibilityToggle */
    let tableRef: DataTable<FxRow> | undefined = $state(undefined);

    export function getTableRef() {
        return tableRef;
    }

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

    /** Bulk-toggle inversion for multiple slugs (called by parent for bulk actions). */
    export function bulkToggleInversion(slugs: string[]) {
        for (const slug of slugs) {
            const current = isCardInverted(slug);
            setCardInverted(slug, !current);
        }
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
        return val >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400';
    }

    // Provider chain rendering — constants & helpers from $lib/utils/fxSync

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
                parts.push(fxProviderBadgeHtml(step.provider));
                parts.push(`<span class="text-gray-400 text-[8px]">⇆</span>`);
                parts.push(`<span class="emoji-flag text-[10px]">${toFlag}</span>`);
            }
            return `<div class="flex items-center gap-0.5 flex-wrap">${parts.join('')}</div>`;
        }
        // Single provider, no steps detail
        return fxProviderBadgeHtml(prov.providerCode);
    }

    // =========================================================================
    // Columns
    // =========================================================================

    let columns = $derived<ColumnDef<FxRow>[]>(
        (void $fxProvidersVersion, // trigger re-derive when FX provider icons are cached
        [
            {
                id: 'pair',
                header: () => $t('fx.filter.filterCurrency'),
                cell: (row) => {
                    const db = getDisplayBase(row);
                    const dq = getDisplayQuote(row);
                    const bFlag = getCurrencyInfo(db).flag_emoji;
                    const qFlag = getCurrencyInfo(dq).flag_emoji;
                    const manualBadge = row.manualOnly ? ' <span class="inline-flex items-center px-1 py-0.5 text-[9px] font-medium rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 ml-1">✏️</span>' : '';
                    return {
                        type: 'html',
                        html: `<span class="emoji-flag">${bFlag}</span> <span class="font-semibold">${db}</span> <span class="text-gray-400">→</span> <span class="emoji-flag">${qFlag}</span> <span class="font-semibold">${dq}</span>${manualBadge}`,
                    };
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
                    return r !== null ? {type: 'html', html: `<span class="font-mono font-bold">${r.toFixed(4)}</span>`} : '—';
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
            ...visiblePeriods.map((p) => ({
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
                getValue: (row) => row.providers.map((p) => p.providerCode).join(', '),
                width: 160,
                minWidth: 100,
                hiddenByDefault: true,
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
    emptyMessage={$t('fx.empty.noPairsDesc')}
    enableActions={true}
    enableColumnFilters={true}
    enablePagination={true}
    enableSorting={true}
    getRowId={(row) => row.slug}
    isLoading={loading}
    onRowClick={(row) => {
        const inv = isCardInverted(row.slug);
        const target = inv ? `${row.quote}-${row.base}` : row.slug;
        const params = dateStart && dateEnd ? `?start=${dateStart}&end=${dateEnd}` : '';
        goto(`/fx/${target}${params}`);
    }}
    onSelectionChange={(ids) => onselectionchange?.(data.filter((row) => ids.includes(row.slug)))}
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
                try {
                    await onsync?.({base: row.base, quote: row.quote, slug: row.slug});
                } finally {
                    syncingRowIds = new Set([...syncingRowIds].filter((id) => id !== row.slug));
                }
            },
            disabled: (row) => row.manualOnly,
            iconClass: (row) => (syncingRowIds.has(row.slug) ? 'animate-spin' : ''),
        },
        {
            id: 'refresh',
            label: () => $t('common.refresh'),
            icon: RefreshCw,
            onClick: async (row) => {
                refreshingRowIds = new Set([...refreshingRowIds, row.slug]);
                try {
                    await onrefresh?.({base: row.base, quote: row.quote, slug: row.slug});
                } finally {
                    refreshingRowIds = new Set([...refreshingRowIds].filter((id) => id !== row.slug));
                }
            },
            iconClass: (row) => (refreshingRowIds.has(row.slug) ? 'animate-spin' : ''),
        },
        {
            id: 'delete',
            label: () => $t('common.delete'),
            icon: Trash2,
            onClick: (row) => ondelete?.({base: row.base, quote: row.quote, slug: row.slug}),
            variant: 'danger',
        },
    ]}
    storageKey="fxTable"
/>
