<!--
  AssetTable — Table view for assets list using DataTable.
  Columns: Icon, Name, Type (badge), Currency (flag), Last Price, Δ multi-period, Provider, Active, Actions.
  Dynamic Δ columns based on visiblePeriods prop.
  Svelte 5 runes, dark mode.
  Used by: /assets list page (table/list view)
-->
<script lang="ts">
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {goto} from '$app/navigation';
    import {onMount, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {deltaPeriodLabel} from '$lib/features/assets/assetPriceDerived';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {Merge, Pencil, RefreshCw, RotateCw, Trash2} from 'lucide-svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo, currencyStoreVersion} from '$lib/stores/reference/currencyStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import {assetProviderBadgeHtml, assetProvidersVersion, ensureAssetProvidersCached} from '$lib/utils/providerHelpers';
    import {assetTypeBadgeHtml, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {publishAssetTableOrder, type AssetPanelId} from './assetBrowse';
    import type {LivePriceDirection} from '$lib/services/livePriceService';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';
    import {formatFixed, priceFractionDigits} from '$lib/utils/core/formatFixed';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {SIGN_TEXT} from '$lib/theme/toneClasses';
    import {ASSET_LIST_RISK_COLUMNS, type AssetListRiskColumn, type AssetListRiskFigures} from '$lib/features/risk/assetListRisk';
    import {translateErrorCode} from '$lib/features/risk/levels/levelHelpers';

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
        quote_base_quantity?: number | null;
        lastPrice?: number | null;
        deltas?: Record<string, number | null>;
        /** F15 — transactions using this asset. */
        txCount?: number;
        /** F15 — usage scope: own (tx in your brokers) / others / analysis (unused). */
        txScope?: 'own' | 'others' | 'analysis';
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
        /** U10: the row action «Edit» — the owner opens the asset editor, complete, without leaving the list. */
        onedit?: (asset: AssetRow) => void;
        onsync?: (asset: AssetRow) => void;
        onrefresh?: (asset: AssetRow) => void;
        ondelete?: (asset: AssetRow) => void;
        onmerge?: (asset: AssetRow) => void;
        onselectionchange?: (rows: AssetRow[]) => void;
        /** Registers this table's DataTable with the owner, under the panel id (`browseSegment`); the owner keeps no `bind:this` of its own. Returns the function that takes this very registration away. */
        registerTable?: (panelId: string, table: DataTable<AssetRow>) => () => void;
        /** Changes (by any step) when the owner wants the selection dropped. */
        clearSelectionToken?: number;
        /** F15 round-2 — stacked usage tables share column layout; this callback
         *  lets the parent mirror live resizes onto the sibling instances. */
        onColumnResize?: (columnId: string, width: number) => void;
        /** Distinct storageKey per stacked instance (independent client state). */
        storageKey?: string;
        /** The usage panel this table shows: its row order is published for the detail page's prev/next. */
        browseSegment?: AssetPanelId;
        /**
         * RN-23: each row's risk figures, measured on its own asset over the page's period and currency (`assetListRisk.ts`). Absent: no
         * risk columns; a row not in the map yet shows «…» and sorts last.
         */
        riskFigures?: ReadonlyMap<number, AssetListRiskFigures>;
    }

    let {data = [], loading = false, visiblePeriods = [], livePriceMap = new Map(), dateStart, dateEnd, onedit, onsync, onrefresh, ondelete, onmerge, onselectionchange, registerTable, clearSelectionToken = 0, onColumnResize, storageKey = 'assetsTable', browseSegment, riskFigures}: Props = $props();

    // The owner gets this table's DataTable by callback, not through `bind:this` on a record: that binding was left empty after the
    // panels re-mounted, and the column menu and the width mirror then had no table to act on.
    $effect(() => {
        const table = tableRef;
        const panelId = browseSegment;
        if (!panelId || !table) return;
        // Untracked: the owner's registry is state of its own, which must not become this effect's dependency (it would re-run on every
        // write, and register again forever). Each registration is taken away by itself, so the order in which panels mount and are
        // torn down cannot lose another table.
        const unregister = untrack(() => registerTable?.(panelId, table));
        return () => untrack(() => unregister?.());
    });

    // The owner asks for the selection to be dropped by changing the token: this table clears its own DataTable.
    let seenClearToken = untrack(() => clearSelectionToken);
    $effect(() => {
        const token = clearSelectionToken;
        if (token === seenClearToken) return;
        seenClearToken = token;
        tableRef?.clearSelection();
    });

    ensureCurrenciesLoaded($currentLanguage);
    ensureAssetProvidersCached();

    /** Exposed DataTable ref for ColumnVisibilityToggle */
    let tableRef: DataTable<AssetRow> | undefined = $state(undefined);
    let tableWrapperEl: HTMLDivElement | undefined = $state(undefined);

    // Cells are rendered as raw HTML strings (see the 'name' column below), so `use:` actions
    // can't attach to them directly — scan the wrapper for overflow-marquee candidates instead,
    // re-attaching automatically whenever rows are re-rendered (sort/filter/pagination/refresh).
    onMount(() => {
        if (!tableWrapperEl) return;
        return attachOverflowMarqueeToDescendants(tableWrapperEl);
    });

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
            return `<img src="${escapeHtml(iconSrc)}" alt="" class="w-5 h-5 rounded-full object-cover shrink-0" data-hide-on-error="display" />`;
        }
        return `<div class="w-5 h-5 rounded-full bg-lf-selected flex items-center justify-center shrink-0 text-lf-link"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg></div>`;
    }

    function formatDelta(val: number | null | undefined, suffix: string = ''): string {
        if (val === null || val === undefined) return '—';
        const num = Number(val);
        return suffix === '%' ? formatPercent(num) : `${formatFixed(num, 2, {signed: true})}${suffix}`;
    }

    function deltaColorClass(val: number | null | undefined): string {
        if (val === null || val === undefined) return SIGN_TEXT.market.none;
        return Number(val) >= 0 ? SIGN_TEXT.market.gain : SIGN_TEXT.market.loss;
    }

    function typeBadgeHtml(type: string | null | undefined): string {
        if (!type) return '<span class="text-lf-muted">—</span>';
        // The badge colour follows the *family*, the wrapper; a subtype's dot, like its icon's pastille, says what
        // it contains (designer, round 3). The markup is shared with the asset pie's tooltip — see assetTypeBadgeHtml().
        return assetTypeBadgeHtml(type, $t(`assets.types.${type}`) || type);
    }

    // =========================================================================
    // Columns
    // =========================================================================

    // RN-23 — the risk columns: the max drawdown shown, the others in the column menu. A figure the engine could not give is «—» with
    // its reason (Q20); a row still being measured is «…»; both sort last (a null value), never as a zero.
    const RISK_PERCENT_SIGNED: ReadonlySet<AssetListRiskColumn> = new Set(['maxDrawdown', 'annualReturn', 'worstDay', 'bestDay', 'rally']);
    const RISK_RATIO: ReadonlySet<AssetListRiskColumn> = new Set(['sharpe', 'sortino']);

    function riskFigureText(column: AssetListRiskColumn, value: number): string {
        if (RISK_RATIO.has(column)) return formatFixed(value, 2);
        return formatPercent(value, {scale: 100, signed: RISK_PERCENT_SIGNED.has(column)});
    }

    function riskCell(column: AssetListRiskColumn, row: AssetRow): string {
        const figures = riskFigures?.get(row.id);
        if (!figures) return `<span class="text-lf-muted" data-testid="asset-risk-cell" data-column="${column}" data-state="pending">…</span>`;
        const value = figures.values[column];
        if (value === null) {
            const code = figures.reasons[column] ?? 'unknown';
            const reason = translateErrorCode(code, $t, 'risk.errors.unknown');
            return `<span class="text-lf-muted" title="${escapeHtml(reason)}" data-testid="asset-risk-cell" data-column="${column}" data-state="blank" data-reason="${escapeHtml(code)}">—</span>`;
        }
        return `<span class="font-mono tabular-nums text-lf-primary" data-testid="asset-risk-cell" data-column="${column}" data-state="value" data-value="${value}">${escapeHtml(riskFigureText(column, value))}</span>`;
    }

    function riskColumns(): ColumnDef<AssetRow>[] {
        if (!riskFigures) return [];
        return ASSET_LIST_RISK_COLUMNS.map((column, index) => ({
            id: `risk_${column}`,
            header: () => $t(`assets.table.risk.${column}`),
            headerTooltip: () => $t('assets.table.risk.hint'),
            cell: (row: AssetRow) => ({type: 'html' as const, html: riskCell(column, row)}),
            type: 'number' as const,
            getValue: (row: AssetRow) => riskFigures?.get(row.id)?.values[column] ?? null,
            width: 100,
            minWidth: 70,
            align: 'right' as const,
            filterable: false,
            hiddenByDefault: index > 0,
        }));
    }

    let columns = $derived<ColumnDef<AssetRow>[]>(
        (void $assetProvidersVersion, // trigger re-derive when asset provider icons are cached
        [
            {
                id: 'name',
                header: () => $t('common.name'),
                cell: (row) => {
                    const icon = assetIconHtml(row);
                    const activeDot = row.active ? '<span data-lifecycle="active" class="w-2 h-2 rounded-full bg-lf-success shrink-0"></span>' : '<span data-lifecycle="inactive" class="w-2 h-2 rounded-full bg-lf-danger shrink-0"></span>';
                    return {
                        type: 'html',
                        html: `<div class="flex items-center gap-2 min-w-0">${icon}<span class="min-w-0 flex-1 font-medium text-lf-primary ${overflowScrollTextClass}">${escapeHtml(row.display_name)}</span>${activeDot}</div>`,
                    };
                },
                type: 'text',
                getValue: (row) => row.display_name,
                width: 220,
                minWidth: 150,
            },
            {
                id: 'txCount',
                header: () => $t('assets.table.txCount'),
                headerTooltip: () => $t('assets.table.txCountTooltip'),
                cell: (row) => {
                    /* colour: closest role, to review: own = success tint, others = info tint, none = neutral chip (secondary text for contrast on the neutral fill) */
                    const scopeCls = row.txScope === 'own' ? 'bg-lf-success-soft text-lf-success-on-soft' : row.txScope === 'others' ? 'bg-lf-info-soft text-lf-info-on-soft' : 'bg-lf-neutral text-lf-secondary';
                    return {
                        type: 'html',
                        html: `<span data-scope="${row.txScope ?? 'none'}" class="inline-flex items-center justify-center min-w-8 px-1.5 py-0.5 rounded-md text-[11px] font-mono font-medium ${scopeCls}">${row.txCount ?? 0}</span>`,
                    };
                },
                type: 'number',
                getValue: (row) => row.txCount ?? 0,
                width: 60,
                minWidth: 48,
            },
            {
                id: 'type',
                header: () => $t('common.type'),
                cell: (row) => ({type: 'html', html: typeBadgeHtml(row.asset_type)}),
                type: 'enum',
                // Hand-written on purpose, and guarded by the enum gate test rather than
                // derived from schemas.AssetType.options: `generated.ts` is gitignored and
                // only exists after `./dev.py api sync`, so a derived list would quietly
                // come up short on any checkout where the client has not been regenerated —
                // green test, missing filter values. A literal list works with no client at
                // all, and the gate makes forgetting one a red.
                enumOptions: ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'CROWDFUND', 'HOLD', 'COMMODITY', 'REAL_ESTATE', 'INDEX', 'OTHER', 'ETF_STOCK', 'ETF_BOND', 'ETF_COMMODITY', 'ETF_REAL_ESTATE', 'ETF_CRYPTO', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE'].map((v) => ({
                    value: v,
                    label: $t(`assets.types.${v}`) || v,
                })),
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
                    return {type: 'html', html: `<span class="emoji-flag">${info.flag_emoji}</span> ${escapeHtml(row.currency)}`};
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
                    const colorCls = dir === 'up' ? SIGN_TEXT.market.gain : dir === 'down' ? SIGN_TEXT.market.loss : '';
                    // A market quote is the same figure for every user and reveals
                    // nothing about this one's holdings. No masked amount shares the
                    // row, so nothing can be reconstructed from it here.
                    // C-97c: a price under a cent keeps 4 significant digits instead of reading 0.00.
                    const {min, max} = priceFractionDigits(price);
                    const inner = formatCurrencyAmountHtml(price, row.currency, {minFraction: min, maxFraction: max, sensitivity: 'public'});
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
                // 81 U33: measured at 1440 and 1024 px in the four languages — «60,631.70$🇺🇸USD» needs 160 px; narrower, it ran into Δ 1D.
                width: 170,
                minWidth: 160,
            },
            {
                id: 'delta_1D',
                header: () => `Δ ${deltaPeriodLabel('1D', $t)}`,
                cell: (row) => {
                    const val = row.deltas?.['1D'] ?? null;
                    return {
                        type: 'html',
                        html: `<span class="font-mono ${deltaColorClass(val)}">${formatDelta(val, '%')}</span>`,
                    };
                },
                type: 'number',
                getValue: (row) => row.deltas?.['1D'] ?? 0,
                // 81 U33: «+423,30 %» (French, with its space) needs 92 px; at 80 it ran into the next column.
                width: 100,
                minWidth: 92,
            },
            // Dynamic Δ multi-period columns
            ...visiblePeriods.map((period) => ({
                id: `delta_${period.key}`,
                header: () => `Δ ${deltaPeriodLabel(period.key, $t)}`,
                cell: (row: AssetRow) => {
                    const val = row.deltas?.[period.key] ?? null;
                    return {
                        type: 'html' as const,
                        html: `<span class="font-mono ${deltaColorClass(val)}">${formatDelta(val, '%')}</span>`,
                    };
                },
                type: 'number' as const,
                getValue: (row: AssetRow) => row.deltas?.[period.key] ?? 0,
                width: 100,
                minWidth: 92,
            })),
            ...riskColumns(),
            {
                id: 'provider',
                header: () => $t('common.provider'),
                cell: (row) => ({
                    type: 'html' as const,
                    html: row.provider_code ? assetProviderBadgeHtml(row.provider_code) : '<span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-lf-warning-soft text-lf-warning-on-soft">✏️ Manual</span>',
                }),
                type: 'text',
                getValue: (row) => row.provider_code ?? '',
                width: 240,
                minWidth: 160,
                filterable: false,
            },
            {
                id: 'quoteBaseQuantity',
                header: () => $t('assets.table.quoteBaseQuantity'),
                headerTooltip: () => $t('assets.modal.quoteBaseTooltip'),
                cell: (row) => ({type: 'html', html: `<span class="font-mono tabular-nums">${row.quote_base_quantity ?? 1}</span>`}),
                type: 'number',
                getValue: (row) => row.quote_base_quantity ?? 1,
                width: 100,
                minWidth: 70,
                align: 'right',
                filterable: false,
                hiddenByDefault: true,
            },
        ]),
    );
</script>

<div bind:this={tableWrapperEl}>
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
        getRowClass={(row) => (row.active ? '' : 'asset-row-inactive')}
        onSelectionChange={(ids) => onselectionchange?.(data.filter((row) => ids.includes(String(row.id))))}
        rowActions={[
            {
                id: 'edit',
                label: () => $t('common.edit'),
                icon: Pencil,
                onClick: (row) => onedit?.(row),
                testid: 'asset-table-edit-action',
            },
            {
                id: 'sync',
                label: () => $t('common.sync'),
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
                // Without a provider there is nothing to sync: not offered; an inactive Asset says why it is off (77 SEL-M, Q-SEL-17)
                visible: (row) => !!row.provider_code,
                blocked: (row) => (row.active === false ? {hint: () => $t('assetDetail.syncDisabledInactive'), reason: 'inactive'} : null),
                iconClass: (row) => (syncingRowIds.has(String(row.id)) ? 'animate-spin' : ''),
                testid: 'asset-table-sync-action',
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
                id: 'merge',
                label: () => $t('assets.merge.action'),
                icon: Merge,
                onClick: (row) => onmerge?.(row),
            },
            {
                id: 'delete',
                label: () => $t('common.delete'),
                icon: Trash2,
                onClick: (row) => ondelete?.(row),
                variant: 'danger',
            },
        ]}
        {storageKey}
        {onColumnResize}
        onRowOrderChange={browseSegment ? (rowIds) => publishAssetTableOrder(browseSegment, rowIds.map(Number)) : undefined}
    />
</div>

<style>
    /* An inactive asset's row: the warning tint, a step stronger under the pointer — the roles follow the theme. Set as the
       row's tint of DataTable (`--dt-row-tint`), never as its background: so the fixed columns show the same colour,
       opaque. */
    :global(tr.asset-row-inactive:not(.selected):not(.highlighted)) {
        --dt-row-tint: var(--lf-warning-soft) !important;
    }

    :global(tr.asset-row-inactive:not(.selected):not(.highlighted):hover) {
        --dt-row-tint: color-mix(in oklab, var(--lf-warning-line) 50%, transparent) !important;
    }
</style>
