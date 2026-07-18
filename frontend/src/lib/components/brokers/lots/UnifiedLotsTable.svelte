<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {schemas} from '$lib/api';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef, EnumOption, FooterCellContent, HtmlCell, RowAction} from '$lib/components/table/types';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
    import {getBrokerIconCandidates, getBrokerIconHtmlById} from '$lib/utils/broker/brokerHelpers';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {BarChart3, Copy, ExternalLink, Eye} from 'lucide-svelte';
    import type {z} from 'zod';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type LotCustodySummarySchema = z.infer<typeof schemas.LotCustodySummarySchema>;
    type NumericLike = string | number | (string | number | null)[] | null | undefined;
    type BrokerIdLike = number | (number | null)[] | null | undefined;
    type LotState = 'OPEN' | 'PARTIALLY_CLOSED' | 'CLOSED' | 'DISTRIBUTED' | 'IN_TRANSIT' | 'DEGRADED';
    type PrimaryLotState = 'OPEN' | 'PARTIALLY_CLOSED' | 'CLOSED' | 'DEGRADED';

    interface Props {
        lots: ReadonlyArray<LotSummarySchema>;
        currency: string;
        brokers: ReadonlyArray<BrokerLike>;
        selectedLotIds?: number[];
        onSelectionChange?: (lotIds: number[]) => void;
        onCustodyCellClick?: (lot: LotSummarySchema) => void;
        onViewGanttLot?: (lotId: number) => void;
        onGotoOpeningTransaction?: (lot: LotSummarySchema) => void;
        onRowDoubleClick?: (lotId: number) => void;
    }

    interface DisplayRow {
        rowId: string;
        lotId: number;
        lot: LotSummarySchema;
        openingBrokerId: number;
        openingBrokerName: string;
        openingDate: string;
        direction: 'LONG' | 'SHORT';
        primaryState: PrimaryLotState;
        secondaryStates: LotState[];
        filterStates: LotState[];
        brokerFilterValues: string[];
        custodySlices: ReadonlyArray<LotCustodySummarySchema>;
        custodySearchText: string;
        openingUnitPrice: number | null;
        quantityOpen: number | null;
        quantityOriginal: number | null;
        openingValue: number | null;
        currentValue: number | null;
        assetIncome: number | null;
        totalPnl: number | null;
        totalReturn: number | null;
        relativeReturn: number | null;
    }

    const PRIMARY_STATE_ORDER: PrimaryLotState[] = ['OPEN', 'PARTIALLY_CLOSED', 'CLOSED', 'DEGRADED'];
    const SECONDARY_STATE_ORDER: LotState[] = ['DISTRIBUTED', 'IN_TRANSIT', 'DEGRADED'];
    const STATUS_FILTER_VALUES: LotState[] = ['OPEN', 'PARTIALLY_CLOSED', 'CLOSED', 'DISTRIBUTED', 'IN_TRANSIT', 'DEGRADED'];
    const IN_TRANSIT_FILTER_VALUE = '__IN_TRANSIT__';

    let {lots = [], currency, brokers = [], selectedLotIds = undefined, onSelectionChange, onCustodyCellClick, onViewGanttLot, onGotoOpeningTransaction, onRowDoubleClick}: Props = $props();

    let tableRef: DataTable<DisplayRow> | undefined = $state(undefined);
    let internalSelectedLotIds = $state<number[]>(untrack(() => selectedLotIds ?? []));
    let syncingSelection = $state(false);
    let appliedSelectionRowIds = $state<string[]>([]);

    export function navigateToRowId(rowId: string): void {
        tableRef?.navigateToRowId(rowId);
    }

    function label(key: string, fallback: string): string {
        const translated = $_(key) || fallback;
        return translated === key ? fallback : translated;
    }

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function firstScalar<T>(value: T | (T | null)[] | null | undefined): T | null {
        if (Array.isArray(value)) {
            return (value.find((item) => item != null) as T | undefined) ?? null;
        }
        return value ?? null;
    }

    function safeNum(value: NumericLike): number | null {
        const scalar = firstScalar(value);
        if (scalar == null) return null;
        const parsed = Number.parseFloat(String(scalar));
        return Number.isFinite(parsed) ? parsed : null;
    }

    function safeBrokerId(value: BrokerIdLike): number | null {
        const scalar = firstScalar(value);
        if (scalar == null) return null;
        return typeof scalar === 'number' && Number.isFinite(scalar) ? scalar : null;
    }

    function formatQuantity(value: number | null): string {
        return value == null ? '—' : value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
    }

    function formatPercent(value: number | null): string {
        if (value == null) return '—';
        const sign = value > 0 ? '+' : '';
        return `${sign}${(value * 100).toFixed(2)}%`;
    }

    function stateLabel(state: LotState): string {
        switch (state) {
            case 'OPEN':
                return label('brokers.lots.states.OPEN', 'Open');
            case 'PARTIALLY_CLOSED':
                return label('brokers.lots.states.PARTIALLY_CLOSED', 'Partial');
            case 'CLOSED':
                return label('brokers.lots.states.CLOSED', 'Closed');
            case 'DISTRIBUTED':
                return label('brokers.lots.states.DISTRIBUTED', 'Distributed');
            case 'IN_TRANSIT':
                return label('brokers.lots.states.IN_TRANSIT', 'In transit');
            case 'DEGRADED':
                return label('brokers.lots.states.DEGRADED', 'Degraded');
        }
    }

    function directionLabel(direction: 'LONG' | 'SHORT'): string {
        return direction === 'LONG' ? label('brokers.lots.directionLong', 'LONG') : label('brokers.lots.directionShort', 'SHORT');
    }

    function directionCell(direction: 'LONG' | 'SHORT'): HtmlCell {
        const long = direction === 'LONG';
        const classes = long ? 'border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800/70 dark:bg-emerald-950/40 dark:text-emerald-300' : 'border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800/70 dark:bg-rose-950/40 dark:text-rose-300';
        const arrow = long ? '↗' : '↘';
        return {
            type: 'html',
            html: `<span class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${classes}">${arrow}<span>${escapeHtml(directionLabel(direction))}</span></span>`,
        };
    }

    function primaryState(stateList: readonly string[]): PrimaryLotState {
        if (stateList.includes('PARTIALLY_CLOSED')) return 'PARTIALLY_CLOSED';
        if (stateList.includes('OPEN')) return 'OPEN';
        if (stateList.includes('CLOSED')) return 'CLOSED';
        return 'DEGRADED';
    }

    function secondaryStates(stateList: readonly string[]): LotState[] {
        return SECONDARY_STATE_ORDER.filter((state) => stateList.includes(state));
    }

    function filterStates(stateList: readonly string[]): LotState[] {
        const normalized = [primaryState(stateList), ...secondaryStates(stateList)];
        return Array.from(new Set(normalized));
    }

    function brokerStyle(brokerId: number): string {
        const color = getBrokerColor(brokerId, brokers);
        return `--broker-bg:${color.bg};--broker-text:${color.text};--broker-dark-bg:${color.darkBg};--broker-dark-text:${color.darkText};--broker-vivid:${color.vivid};--broker-vivid-light:${color.vividLight};`;
    }

    function getRowClass(_row: DisplayRow): string {
        return 'lot-row-tinted';
    }

    function getBroker(brokerId: number | null | undefined): BrokerLike | null {
        if (brokerId == null) return null;
        return brokers.find((broker) => broker.id === brokerId) ?? null;
    }

    function getBrokerName(brokerId: number | null | undefined): string {
        if (brokerId == null) return label('brokers.lots.inTransit', 'In transit');
        return getBroker(brokerId)?.name ?? `#${brokerId}`;
    }

    function statusBadgeHtml(state: LotState, secondary: boolean): string {
        const classes =
            state === 'OPEN'
                ? 'border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800/70 dark:bg-emerald-950/40 dark:text-emerald-300'
                : state === 'PARTIALLY_CLOSED'
                  ? 'border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/70 dark:bg-amber-950/40 dark:text-amber-300'
                  : state === 'CLOSED'
                    ? 'border border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                    : state === 'DISTRIBUTED'
                      ? 'border border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800/70 dark:bg-violet-950/40 dark:text-violet-300'
                      : state === 'IN_TRANSIT'
                        ? 'border border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800/70 dark:bg-sky-950/40 dark:text-sky-300'
                        : 'border border-red-200 bg-red-50 text-red-700 dark:border-red-800/70 dark:bg-red-950/40 dark:text-red-300';
        const size = secondary ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs';
        return `<span class="inline-flex items-center rounded-full font-semibold ${size} ${classes}">${escapeHtml(stateLabel(state))}</span>`;
    }

    function statusCell(row: DisplayRow): HtmlCell {
        const secondary = row.secondaryStates.filter((state) => state !== row.primaryState);
        return {
            type: 'html',
            html: `<div class="flex flex-wrap items-center gap-1.5">${statusBadgeHtml(row.primaryState, false)}${secondary.map((state) => statusBadgeHtml(state, true)).join('')}</div>`,
        };
    }

    function quantityCell(row: DisplayRow): HtmlCell | string {
        if (row.primaryState === 'CLOSED') return '—';
        const content = row.primaryState === 'PARTIALLY_CLOSED' ? `${formatQuantity(row.quantityOpen)} / ${formatQuantity(row.quantityOriginal)}` : formatQuantity(row.quantityOpen);
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums text-gray-700 dark:text-gray-200">${escapeHtml(content)}</span>`,
        };
    }

    function quantityValueCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums text-gray-700 dark:text-gray-200">${escapeHtml(formatQuantity(value))}</span>`,
        };
    }

    function currencyCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums text-gray-700 dark:text-gray-200">${escapeHtml(formatCurrencyAmountPlain(value, currency))}</span>`,
        };
    }

    function signedAmountCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        const classes = value > 0 ? 'text-green-600 dark:text-green-400' : value < 0 ? 'text-red-500 dark:text-red-400' : 'text-gray-500 dark:text-gray-400';
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums ${classes}">${escapeHtml(formatCurrencyAmountPlain(value, currency, {showSign: value !== 0}))}</span>`,
        };
    }

    function signedPercentCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        const classes = value > 0 ? 'text-green-600 dark:text-green-400' : value < 0 ? 'text-red-500 dark:text-red-400' : 'text-gray-500 dark:text-gray-400';
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums ${classes}">${escapeHtml(formatPercent(value))}</span>`,
        };
    }

    function buildCustodyTooltip(row: DisplayRow): string {
        if (row.custodySlices.length === 0) return '';
        const lines = row.custodySlices.map((slice) => {
            const brokerId = safeBrokerId(slice.broker_id);
            const name = slice.custody_type === 'IN_TRANSIT' && brokerId == null ? label('brokers.lots.inTransit', 'In transit') : getBrokerName(brokerId);
            return `<div class="flex items-center justify-between gap-3"><span>${escapeHtml(name)}</span><span class="font-medium tabular-nums">${escapeHtml(formatQuantity(safeNum(slice.quantity)))}</span></div>`;
        });
        return `<div class="space-y-1"><div class="font-semibold">${escapeHtml(label('brokers.lots.custody', 'Custody'))}</div>${lines.join('')}</div>`;
    }

    function custodyCell(row: DisplayRow): HtmlCell | string {
        const custody = row.custodySlices;
        if (custody.length === 0) return '—';

        const brokerIds = Array.from(new Set(custody.map((slice) => safeBrokerId(slice.broker_id)).filter((brokerId): brokerId is number => brokerId != null)));
        const hasInTransit = custody.some((slice) => slice.custody_type === 'IN_TRANSIT');
        const tooltip = buildCustodyTooltip(row);

        if (brokerIds.length === 1 && !hasInTransit && custody.length === 1) {
            const brokerId = brokerIds[0];
            const brokerName = getBrokerName(brokerId);
            const brokerIcon = getBrokerIconHtmlById(brokerId, brokers, {
                width: 16,
                height: 16,
                className: 'shrink-0 rounded-full object-cover',
                alt: brokerName,
                style: 'flex-shrink:0;border-radius:9999px;object-fit:cover;',
            });
            return {
                type: 'html',
                html: `<span class="inline-flex max-w-full items-center gap-1.5" data-testid="unified-lots-custody-${row.lotId}"><span class="inline-flex shrink-0 items-center">${brokerIcon}</span><span class="truncate text-sm">${escapeHtml(brokerName)}</span></span>`,
                tooltip: tooltip ? {html: tooltip, position: 'top', maxWidth: '280px'} : undefined,
                onClick: () => onCustodyCellClick?.(row.lot),
            };
        }

        const distributedLabel = brokerIds.length > 1 ? label('brokers.lots.brokersCount', '{count} brokers').replace('{count}', String(brokerIds.length)) : label('brokers.lots.inTransit', 'In transit');
        const transitTag = hasInTransit ? `<span class="rounded-full border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[11px] font-semibold text-sky-700 dark:border-sky-800/70 dark:bg-sky-950/40 dark:text-sky-300">${escapeHtml(label('brokers.lots.inTransitShort', 'Transit'))}</span>` : '';
        return {
            type: 'html',
            html: `<span class="inline-flex max-w-full items-center gap-1.5" data-testid="unified-lots-custody-${row.lotId}"><span class="rounded-full border border-violet-200 bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-700 dark:border-violet-800/70 dark:bg-violet-950/40 dark:text-violet-300">${escapeHtml(distributedLabel)}</span>${transitTag}</span>`,
            tooltip: {html: tooltip, position: 'top', maxWidth: '280px'},
            onClick: () => onCustodyCellClick?.(row.lot),
        };
    }

    function sameIdSet(left: readonly string[], right: readonly string[]): boolean {
        if (left.length !== right.length) return false;
        const rightSet = new Set(right);
        return left.every((value) => rightSet.has(value));
    }

    let rows = $derived.by<DisplayRow[]>(() =>
        lots.map((lot) => {
            const rawStates = lot.states ?? [];
            const states = rawStates.filter((state): state is LotState => STATUS_FILTER_VALUES.includes(state as LotState));
            const currentCustody = lot.current_custody ?? [];
            const openingBrokerName = getBrokerName(lot.opening_broker_id);
            const openingUnitPrice = safeNum(lot.opening_unit_price);
            const quantityOpen = safeNum(lot.open_quantity);
            const quantityOriginal = safeNum(lot.original_quantity);
            const openingValue = safeNum(lot.original_cost);
            const brokerFilterValues = Array.from(
                new Set(
                    (currentCustody.length > 0 ? currentCustody : [{broker_id: lot.opening_broker_id, custody_type: 'BROKER', quantity: lot.open_quantity}]).flatMap((slice) => {
                        const brokerId = safeBrokerId(slice.broker_id);
                        const values: string[] = [];
                        if (brokerId != null) values.push(String(brokerId));
                        if (slice.custody_type === 'IN_TRANSIT') values.push(IN_TRANSIT_FILTER_VALUE);
                        return values;
                    }),
                ),
            );
            const row: DisplayRow = {
                rowId: String(lot.lot_id),
                lotId: lot.lot_id,
                lot,
                openingBrokerId: lot.opening_broker_id,
                openingBrokerName,
                openingDate: lot.opening_date,
                direction: lot.direction,
                primaryState: primaryState(states),
                secondaryStates: secondaryStates(states),
                filterStates: filterStates(states),
                brokerFilterValues,
                custodySlices: currentCustody,
                custodySearchText: currentCustody
                    .map((slice) => {
                        const brokerId = safeBrokerId(slice.broker_id);
                        return slice.custody_type === 'IN_TRANSIT' && brokerId == null ? label('brokers.lots.inTransit', 'In transit') : getBrokerName(brokerId);
                    })
                    .join(' '),
                openingUnitPrice,
                quantityOpen,
                quantityOriginal,
                openingValue,
                currentValue: safeNum(lot.open_value),
                assetIncome: safeNum(lot.asset_income),
                totalPnl: safeNum(lot.total_pnl),
                totalReturn: safeNum(lot.total_return),
                relativeReturn: safeNum(lot.relative_return),
            };
            return row;
        }),
    );

    let visibleRows = $derived(rows);

    let statusEnumOptions = $derived.by<EnumOption[]>(() =>
        STATUS_FILTER_VALUES.map((state) => ({
            value: state,
            label: stateLabel(state),
        })),
    );

    let brokerEnumOptions = $derived.by<EnumOption[]>(() => [
        ...brokers.map((broker) => ({
            value: String(broker.id),
            label: broker.name ?? `#${broker.id}`,
            iconCandidates: getBrokerIconCandidates(broker),
            dotColor: getBrokerColor(broker.id, brokers).bg,
        })),
        {
            value: IN_TRANSIT_FILTER_VALUE,
            label: label('brokers.lots.inTransit', 'In transit'),
        },
    ]);

    let rowActions = $derived.by<RowAction<DisplayRow>[]>(() => [
        {
            id: 'lot-view-details-action',
            icon: Eye,
            label: () => label('brokers.lots.viewLotDetail', 'View lot detail'),
            onClick: (row) => onCustodyCellClick?.(row.lot),
            disabled: () => onCustodyCellClick == null,
        },
        {
            id: 'lot-view-gantt-action',
            icon: BarChart3,
            label: () => label('brokers.lots.viewGanttLot', 'Go to lot in Gantt'),
            onClick: (row) => onViewGanttLot?.(row.lotId),
            disabled: () => onViewGanttLot == null,
        },
        {
            id: 'lot-goto-opening-transaction-action',
            icon: ExternalLink,
            label: () => label('brokers.lots.goToOpeningTransaction', 'Go to opening transaction'),
            onClick: (row) => onGotoOpeningTransaction?.(row.lot),
            disabled: () => onGotoOpeningTransaction == null,
        },
        {
            id: 'lot-copy-id-action',
            icon: Copy,
            label: () => label('brokers.lots.copyLotIdentifier', 'Copy lot identifier'),
            onClick: async (row) => {
                await navigator.clipboard.writeText(String(row.lotId));
                toasts.success(`${label('brokers.lots.lotIdentifierCopied', 'Lot identifier copied')}: ${row.lotId}. ${label('brokers.lots.lotIdentifierHelp', 'Stable technical identifier derived from the opening transaction, used for audit, support and API correlation.')}`);
            },
        },
    ]);

    let hasDifferingStates = $derived.by(() => new Set(rows.map((row) => row.filterStates.join('|'))).size > 1);
    let hasMixedDirections = $derived.by(() => new Set(rows.map((row) => row.direction)).size > 1);
    let hasPositiveAssetIncome = $derived.by(() => rows.some((row) => (row.assetIncome ?? 0) > 0));

    function sumNumeric(footerRows: readonly DisplayRow[], getValue: (row: DisplayRow) => number | null): number | null {
        let total = 0;
        let count = 0;
        for (const row of footerRows) {
            const value = getValue(row);
            if (value == null || !Number.isFinite(value)) continue;
            total += value;
            count += 1;
        }
        return count > 0 ? total : null;
    }

    function weightedAverage(footerRows: readonly DisplayRow[], getValue: (row: DisplayRow) => number | null, getWeight: (row: DisplayRow) => number | null): number | null {
        let numerator = 0;
        let denominator = 0;
        for (const row of footerRows) {
            const value = getValue(row);
            const weight = getWeight(row);
            if (value == null || weight == null || !Number.isFinite(value) || !Number.isFinite(weight) || weight === 0) continue;
            const absWeight = Math.abs(weight);
            numerator += value * absWeight;
            denominator += absWeight;
        }
        return denominator > 0 ? numerator / denominator : null;
    }

    function buildFooterCells(footerRows: DisplayRow[]): Record<string, FooterCellContent> {
        const totalPnl = sumNumeric(footerRows, (row) => row.totalPnl);
        const openingValueSum = sumNumeric(footerRows, (row) => row.openingValue);
        const totalReturn = totalPnl != null && openingValueSum != null && openingValueSum !== 0 ? totalPnl / openingValueSum : null;

        return {
            'opening-date': label('brokers.lots.footerTotals', label('assets.distribution.total', 'Totals')),
            'total-pnl': signedAmountCell(totalPnl),
            'total-return': signedPercentCell(totalReturn),
            'asset-income': currencyCell(sumNumeric(footerRows, (row) => row.assetIncome)),
            'current-value': currencyCell(sumNumeric(footerRows, (row) => row.currentValue)),
            'open-quantity': quantityValueCell(sumNumeric(footerRows, (row) => row.quantityOpen)),
            'opening-price': currencyCell(
                weightedAverage(
                    footerRows,
                    (row) => row.openingUnitPrice,
                    (row) => row.currentValue,
                ),
            ),
            'open-return': signedPercentCell(
                weightedAverage(
                    footerRows,
                    (row) => row.relativeReturn,
                    (row) => row.currentValue,
                ),
            ),
        };
    }

    let columns = $derived.by<ColumnDef<DisplayRow>[]>(() => [
        {
            id: 'opening-date',
            header: () => label('brokers.lots.openingDate', 'Opening Date'),
            cell: (row) => ({type: 'date', value: row.openingDate, format: 'date'}),
            type: 'date',
            width: 140,
            minWidth: 130,
            sortable: true,
            getValue: (row) => row.openingDate,
        },
        {
            id: 'total-pnl',
            header: () => label('brokers.lots.totalPnl', 'Total P&L'),
            cell: (row) => signedAmountCell(row.totalPnl),
            type: 'number',
            align: 'right',
            width: 170,
            minWidth: 150,
            sortable: true,
            filterable: false,
            getValue: (row) => row.totalPnl ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'total-return',
            header: () => label('brokers.lots.totalReturn', 'Total return'),
            cell: (row) => signedPercentCell(row.totalReturn),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 130,
            sortable: true,
            filterable: false,
            getValue: (row) => row.totalReturn ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'asset-income',
            header: () => label('brokers.lots.assetIncome', 'Income'),
            cell: (row) => currencyCell(row.assetIncome),
            type: 'number',
            align: 'right',
            width: 160,
            minWidth: 140,
            sortable: true,
            filterable: false,
            hiddenByDefault: !hasPositiveAssetIncome,
            getValue: (row) => row.assetIncome ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'current-value',
            header: () => label('brokers.lots.currentValue', 'Current Value'),
            cell: (row) => currencyCell(row.currentValue),
            type: 'number',
            align: 'right',
            width: 170,
            minWidth: 150,
            sortable: true,
            filterable: false,
            getValue: (row) => row.currentValue ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'open-quantity',
            header: () => label('brokers.lots.openQuantity', 'Open Quantity'),
            cell: (row) => quantityCell(row),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 130,
            sortable: true,
            filterable: false,
            getValue: (row) => row.quantityOpen ?? 0,
        },
        {
            id: 'custody',
            header: () => label('brokers.lots.custody', 'Custody'),
            cell: (row) => custodyCell(row),
            type: 'multi-enum',
            width: 140,
            minWidth: 96,
            sortable: true,
            enumOptions: brokerEnumOptions,
            getValue: (row) => row.custodySearchText || row.openingBrokerName,
            getMultiValue: (row) => row.brokerFilterValues,
        },
        {
            id: 'status',
            header: () => label('brokers.lots.status', 'Status'),
            cell: (row) => statusCell(row),
            type: 'multi-enum',
            width: 120,
            minWidth: 80,
            sortable: true,
            enumOptions: statusEnumOptions,
            hiddenByDefault: !hasDifferingStates,
            getValue: (row) => PRIMARY_STATE_ORDER.indexOf(row.primaryState),
            getMultiValue: (row) => row.filterStates,
        },
        {
            id: 'opening-price',
            header: () => label('brokers.lots.openingPriceReference', 'Opening price'),
            cell: (row) => currencyCell(row.openingUnitPrice),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 130,
            sortable: true,
            filterable: false,
            hiddenByDefault: true,
            getValue: (row) => row.openingUnitPrice ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'opening-value',
            header: () => label('brokers.lots.openingValue', 'Opening Value'),
            cell: (row) => currencyCell(row.openingValue),
            type: 'number',
            align: 'right',
            width: 170,
            minWidth: 160,
            sortable: true,
            filterable: false,
            hiddenByDefault: true,
            getValue: (row) => row.openingValue ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'original-quantity',
            header: () => label('brokers.lots.originalQuantity', 'Original Quantity'),
            cell: (row) => quantityValueCell(row.quantityOriginal),
            type: 'number',
            align: 'right',
            width: 160,
            minWidth: 150,
            sortable: true,
            filterable: false,
            hiddenByDefault: true,
            getValue: (row) => row.quantityOriginal ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'open-return',
            header: () => label('brokers.lots.openReturn', 'Open Return'),
            cell: (row) => signedPercentCell(row.relativeReturn),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 140,
            sortable: true,
            filterable: false,
            hiddenByDefault: true,
            getValue: (row) => row.relativeReturn ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'direction',
            header: () => label('brokers.lots.direction', 'Direction'),
            cell: (row) => directionCell(row.direction),
            type: 'enum',
            width: 120,
            minWidth: 110,
            sortable: true,
            enumOptions: [
                {value: 'LONG', label: directionLabel('LONG')},
                {value: 'SHORT', label: directionLabel('SHORT')},
            ],
            hiddenByDefault: !hasMixedDirections,
            getValue: (row) => row.direction,
        },
    ]);

    let effectiveSelectedLotIds = $derived(selectedLotIds ?? internalSelectedLotIds);
    let effectiveSelectedRowIds = $derived(effectiveSelectedLotIds.map((lotId) => String(lotId)));
    let emptyMessage = $derived(label('brokers.lots.noUnifiedLots', 'No lots match current filters'));

    function handleTableSelectionChange(selectedIds: string[]): void {
        const lotIds = selectedIds.map((id) => Number.parseInt(id, 10)).filter((id) => Number.isFinite(id));
        appliedSelectionRowIds = [...selectedIds];
        if (!syncingSelection && selectedLotIds === undefined) {
            internalSelectedLotIds = lotIds;
        }
        if (!syncingSelection) {
            onSelectionChange?.(lotIds);
        }
    }

    async function syncTableSelection(nextRowIds: string[]): Promise<void> {
        if (!tableRef) return;
        const validRowIds = nextRowIds.filter((rowId) => visibleRows.some((row) => row.rowId === rowId));
        if (sameIdSet(validRowIds, appliedSelectionRowIds)) {
            return;
        }
        syncingSelection = true;
        tableRef.clearSelection();
        for (const rowId of validRowIds) {
            tableRef.toggleRowSelectionById(rowId);
        }
        appliedSelectionRowIds = [...validRowIds];
        await tick();
        syncingSelection = false;
    }

    $effect(() => {
        void visibleRows;
        if (!tableRef) return;
        void syncTableSelection(effectiveSelectedRowIds);
    });

    $effect(() => {
        if (selectedLotIds !== undefined) return;
        const visibleLotIds = new Set(rows.map((row) => row.lotId));
        const pruned = internalSelectedLotIds.filter((lotId) => visibleLotIds.has(lotId));
        if (pruned.length !== internalSelectedLotIds.length) {
            internalSelectedLotIds = pruned;
            onSelectionChange?.(pruned);
        }
    });
</script>

<section class="rounded-lg border border-gray-200/80 bg-gray-50/80 dark:border-slate-700 dark:bg-slate-900/30" data-testid="unified-lots-table">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200/80 px-4 py-3 dark:border-slate-700">
        <div class="flex min-w-0 items-center gap-3">
            <div>
                <div class="text-base font-semibold text-gray-900 dark:text-gray-100">{label('brokers.lots.unifiedLots', 'Lots')}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{label('brokers.lots.unifiedLotsHint', 'Unified FIFO lots view with multi-selection and custody drill-down.')}</div>
            </div>
            <span class="inline-flex min-w-7 items-center justify-center rounded-full bg-gray-200 px-2 py-0.5 text-xs font-semibold tabular-nums text-gray-700 dark:bg-slate-700 dark:text-gray-200">
                {lots.length}
            </span>
        </div>
        <div class="flex flex-wrap items-center gap-2">
            <ColumnVisibilityToggle {tableRef} />
        </div>
    </div>

    <div class="unified-lots-table-wrap px-4 py-3">
        <DataTable
            bind:this={tableRef}
            data={visibleRows}
            {columns}
            getRowId={(row) => row.rowId}
            getRowDisplayName={(row) => `${directionLabel(row.direction)} · ${row.openingDate}`}
            {getRowClass}
            getRowStyle={(row) => brokerStyle(row.openingBrokerId)}
            storageKey="broker-unified-lots-v3"
            initialSelectedIds={effectiveSelectedRowIds}
            enableSelection={true}
            selectionMode="multi"
            enableActions={true}
            actionsLabel={label('brokers.lots.actions', 'Actions')}
            actionsColumnWidth="72px"
            enablePagination={true}
            enableColumnVisibility={false}
            enableColumnFilters={true}
            enableSorting={true}
            enableColumnResize={true}
            enableContextMenu={true}
            {rowActions}
            tableLayout="fixed"
            defaultPageSize={25}
            {emptyMessage}
            footerCells={buildFooterCells}
            onSelectionChange={handleTableSelectionChange}
            onRowClick={(row) => tableRef?.toggleRowSelectionById(row.rowId)}
            onRowDoubleClick={(row) => onRowDoubleClick?.(row.lotId)}
        />
    </div>
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
        .unified-lots-table-wrap tr.lot-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 26%, white);
        }
        .dark .unified-lots-table-wrap tr.lot-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 14%, #0f0f18);
        }
        .unified-lots-table-wrap tr.lot-row-tinted.highlighted > td {
            --lot-highlight-base: #f3e8ff;
            --lot-highlight-peak: #e9d5ff;
            background: var(--lot-highlight-base) !important;
            animation: tinted-lot-highlight-pulse 0.6s ease-in-out 3;
        }
        .dark .unified-lots-table-wrap tr.lot-row-tinted.highlighted > td {
            --lot-highlight-base: rgba(147, 51, 234, 0.25);
            --lot-highlight-peak: rgba(147, 51, 234, 0.4);
            background: var(--lot-highlight-base) !important;
        }
        .unified-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 68%, white);
        }
        .dark .unified-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 22%, #0f0f18);
        }
    }
</style>
