<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {translateOr} from '$lib/utils/core/translateOr';
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
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import {safeDecimal, safeNumber} from '$lib/types';
    import {formatPercent as sharedFormatPercent} from '$lib/utils/core/formatPercent';
    import {filterStates, findBroker, formatLotQuantityCell, formatLotQuantityMasked, primaryState, ratioOrNull, sameIdSet, secondaryStates, sumCompleteOrNull, sumNumeric, weightedAverageCompleteOrNull} from './unifiedLotsTableHelpers';
    import {isUnknownOrNonZero} from './lotChartShared';
    import {compareRowsByColumn, formatCellDate} from '$lib/components/table/dataTableLogic';
    import type {SortState} from '$lib/components/table/types';
    import {arrangeRows, groupRewardLots, groupSelection, lotRowsOf, lotsAfterTableSelection, tableRowIdsFor} from './rewardLotGroups';
    import {SIGN_TEXT} from '$lib/theme/toneClasses';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type LotCustodySummarySchema = z.infer<typeof schemas.LotCustodySummarySchema>;
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
        /** The matching method on screen (project 69): the hint names it. */
        matchingMethod?: string;
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
        annualizedReturn: number | null;
        allocatedFees: number | null;
        allocatedTaxes: number | null;
        netTotalPnl: number | null;
        netTotalReturn: number | null;
        netMetricsStatus: 'AVAILABLE' | 'UNAVAILABLE';
        relativeReturn: number | null;
        /** STK-2c: the group row of a broker's reward lots (its own id, its lots' sums), or a lot shown under one. */
        groupHead?: {size: number; firstDate: string; lastDate: string};
        groupChildOf?: string;
    }

    const PRIMARY_STATE_ORDER: PrimaryLotState[] = ['OPEN', 'PARTIALLY_CLOSED', 'CLOSED', 'DEGRADED'];
    const STATUS_FILTER_VALUES: LotState[] = ['OPEN', 'PARTIALLY_CLOSED', 'CLOSED', 'DISTRIBUTED', 'IN_TRANSIT', 'DEGRADED'];
    const IN_TRANSIT_FILTER_VALUE = '__IN_TRANSIT__';

    let {lots = [], currency, brokers = [], selectedLotIds = undefined, onSelectionChange, onCustodyCellClick, onViewGanttLot, onGotoOpeningTransaction, onRowDoubleClick, matchingMethod = 'FIFO'}: Props = $props();

    let tableRef: DataTable<DisplayRow> | undefined = $state(undefined);
    let internalSelectedLotIds = $state<number[]>(untrack(() => selectedLotIds ?? []));
    let syncingSelection = $state(false);
    let appliedSelectionRowIds = $state<string[]>([]);

    export function navigateToRowId(rowId: string): void {
        // A lot inside a closed reward group has no row until the group opens (STK-2c)
        const group = [...rewardGroups.entries()].find(([, members]) => members.some((row) => row.rowId === rowId))?.[0];
        if (group && !expandedGroups.has(group)) {
            expandedGroups = new Set([...expandedGroups, group]);
            void tick().then(() => tableRef?.navigateToRowId(rowId));
            return;
        }
        tableRef?.navigateToRowId(rowId);
    }

    function label(key: string, fallback: string): string {
        const translated = $_(key) || fallback;
        return translated === key ? fallback : translated;
    }

    /** These come from the API as fractions, hence scale 100. */
    const formatPercent = (value: number | null): string => sharedFormatPercent(value, {scale: 100});

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
        /* colour: closest role, to review: LONG/SHORT is a direction, not a state; success and danger tints are the nearest (not gain/loss, rule 7) */
        const classes = long ? 'border border-lf-success-line bg-lf-success-soft text-lf-success-on-soft' : 'border border-lf-danger-line bg-lf-danger-soft text-lf-danger-on-soft';
        const arrow = long ? '↗' : '↘';
        return {
            type: 'html',
            html: `<span class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${classes}">${arrow}<span>${escapeHtml(directionLabel(direction))}</span></span>`,
        };
    }

    function brokerStyle(brokerId: number): string {
        const color = getBrokerColor(brokerId, brokers);
        return `--broker-bg:${color.bg};--broker-text:${color.text};--broker-dark-bg:${color.darkBg};--broker-dark-text:${color.darkText};--broker-vivid:${color.vivid};--broker-vivid-light:${color.vividLight};`;
    }

    function getRowClass(row: DisplayRow): string {
        if (row.groupHead) return 'reward-group-row';
        return row.groupChildOf ? 'lot-row-tinted reward-group-child' : 'lot-row-tinted';
    }

    /** The first cell of a group row (STK-2c): the open/close chevron, the rewards dot, «N rewards» and the dates. */
    function groupHeadCell(row: DisplayRow): HtmlCell {
        const head = row.groupHead!;
        const open = expandedGroups.has(row.rowId);
        const title = translateOr((key) => $_(key, {values: {n: head.size}}), 'brokers.lots.rewardGroup.title', `${head.size} rewards`);
        const toggle = label(open ? 'brokers.lots.rewardGroup.close' : 'brokers.lots.rewardGroup.open', open ? 'Hide the reward lots' : 'Show the reward lots');
        const day = (value: string): string => formatCellDate(value, 'date', {today: $_('date.today') || 'Today', yesterday: $_('date.yesterday') || 'Yesterday'});
        const dates = head.firstDate === head.lastDate ? day(head.firstDate) : `${day(head.firstDate)} → ${day(head.lastDate)}`;
        return {
            type: 'html',
            html: `<span class="inline-flex items-start gap-1.5" data-testid="reward-group-head" data-group-id="${escapeHtml(row.rowId)}" data-state="${open ? 'open' : 'closed'}" aria-expanded="${open}" title="${escapeHtml(toggle)}"><span class="w-3 text-lf-secondary" aria-hidden="true">${open ? '▾' : '▸'}</span><span class="reward-group-dot mt-1.5 inline-block size-2 shrink-0 rounded-full" aria-hidden="true"></span><span class="flex flex-col"><span class="font-semibold text-lf-primary">${escapeHtml(title)}</span><span class="text-xs text-lf-muted tabular-nums">${escapeHtml(dates)}</span></span></span>`,
            onClick: () => toggleGroup(row.rowId),
        };
    }

    const getBroker = (brokerId: number | null | undefined): BrokerLike | null => findBroker(brokerId, brokers);

    function getBrokerName(brokerId: number | null | undefined): string {
        if (brokerId == null) return label('brokers.lots.inTransit', 'In transit');
        return getBroker(brokerId)?.name ?? `#${brokerId}`;
    }

    function statusBadgeHtml(state: LotState, secondary: boolean): string {
        /* colour: closest role, to review: lot states on success, warning, neutral, info and danger tints; DISTRIBUTED stays violet (categorical) */
        const classes =
            state === 'OPEN'
                ? 'border border-lf-success-line bg-lf-success-soft text-lf-success-on-soft'
                : state === 'PARTIALLY_CLOSED'
                  ? 'border border-lf-warning-line bg-lf-warning-soft text-lf-warning-on-soft'
                  : state === 'CLOSED'
                    ? 'border border-lf-subtle bg-lf-neutral text-lf-secondary'
                    : state === 'DISTRIBUTED'
                      ? 'border border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800/70 dark:bg-violet-950/40 dark:text-violet-300'
                      : state === 'IN_TRANSIT'
                        ? 'border border-lf-info-line bg-lf-info-soft text-lf-info-on-soft'
                        : 'border border-lf-danger-line bg-lf-danger-soft text-lf-danger-on-soft';
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
        const content = formatLotQuantityCell(row.quantityOpen, row.quantityOriginal, row.primaryState === 'PARTIALLY_CLOSED');
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums text-lf-secondary">${escapeHtml(content)}</span>`,
        };
    }

    function quantityValueCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums text-lf-secondary">${escapeHtml(formatLotQuantityMasked(value))}</span>`,
        };
    }

    function currencyCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums text-lf-secondary">${escapeHtml(formatCurrencyAmountPlain(value, currency))}</span>`,
        };
    }

    /**
     * A price per unit. Public: the product owner ruled that a price is not patrimony and that
     * a purchase price is admissible (2026-09-22). It used to be masked with the other amounts
     * while the open quantity beside it was visible, since quantity × price rebuilds the value;
     * the quantity is masked now (D5′), so the price has nothing left to reveal.
     */
    function unitPriceCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums text-lf-secondary">${escapeHtml(formatCurrencyAmountPlain(value, currency, {sensitivity: 'public'}))}</span>`,
        };
    }

    function signedAmountCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        const classes = value > 0 ? SIGN_TEXT.portfolio.gain : value < 0 ? SIGN_TEXT.portfolio.loss : SIGN_TEXT.portfolio.zero;
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums ${classes}">${escapeHtml(formatCurrencyAmountPlain(value, currency, {showSign: value !== 0}))}</span>`,
        };
    }

    function signedPercentCell(value: number | null): HtmlCell | string {
        if (value == null) return '—';
        const classes = value > 0 ? SIGN_TEXT.portfolio.gain : value < 0 ? SIGN_TEXT.portfolio.loss : SIGN_TEXT.portfolio.zero;
        return {
            type: 'html',
            html: `<span class="font-medium tabular-nums ${classes}">${escapeHtml(formatPercent(value))}</span>`,
        };
    }

    function netUnavailableCell(): HtmlCell {
        const tip = escapeHtml(label('brokers.lots.netMetricsUnavailable', 'Net metrics unavailable: degraded economic pool'));
        return {
            type: 'html',
            html: `<span class="tabular-nums text-lf-muted" title="${tip}">—</span>`,
        };
    }

    function netAmountCell(row: DisplayRow): HtmlCell | string {
        return row.netMetricsStatus === 'UNAVAILABLE' ? netUnavailableCell() : signedAmountCell(row.netTotalPnl);
    }

    function netReturnCell(row: DisplayRow): HtmlCell | string {
        return row.netMetricsStatus === 'UNAVAILABLE' ? netUnavailableCell() : signedPercentCell(row.netTotalReturn);
    }

    function buildCustodyTooltip(row: DisplayRow): string {
        if (row.custodySlices.length === 0) return '';
        const lines = row.custodySlices.map((slice) => {
            const brokerId = safeNumber(slice.broker_id);
            const name = slice.custody_type === 'IN_TRANSIT' && brokerId == null ? label('brokers.lots.inTransit', 'In transit') : getBrokerName(brokerId);
            return `<div class="flex items-center justify-between gap-3"><span>${escapeHtml(name)}</span><span class="font-medium tabular-nums">${escapeHtml(formatLotQuantityMasked(safeDecimal(slice.quantity)))}</span></div>`;
        });
        return `<div class="space-y-1"><div class="font-semibold">${escapeHtml(label('brokers.lots.custody', 'Custody'))}</div>${lines.join('')}</div>`;
    }

    function custodyCell(row: DisplayRow): HtmlCell | string {
        const custody = row.custodySlices;
        if (custody.length === 0) return '—';

        const brokerIds = Array.from(new Set(custody.map((slice) => safeNumber(slice.broker_id)).filter((brokerId): brokerId is number => brokerId != null)));
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
        /* colour: closest role, to review: the transit badge, sky blue as in the status badge, on the info tint */
        const transitBadge = hasInTransit ? `<span class="rounded-full border border-lf-info-line bg-lf-info-soft px-1.5 py-0.5 text-[11px] font-semibold text-lf-info-on-soft">${escapeHtml(label('brokers.lots.inTransitShort', 'Transit'))}</span>` : '';
        return {
            type: 'html',
            html: `<span class="inline-flex max-w-full items-center gap-1.5" data-testid="unified-lots-custody-${row.lotId}"><span class="rounded-full border border-violet-200 bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-700 dark:border-violet-800/70 dark:bg-violet-950/40 dark:text-violet-300">${escapeHtml(distributedLabel)}</span>${transitBadge}</span>`,
            tooltip: {html: tooltip, position: 'top', maxWidth: '280px'},
            onClick: () => onCustodyCellClick?.(row.lot),
        };
    }

    let rows = $derived.by<DisplayRow[]>(() =>
        lots.map((lot) => {
            const rawStates = lot.states ?? [];
            const states = rawStates.filter((state): state is LotState => STATUS_FILTER_VALUES.includes(state as LotState));
            const currentCustody = lot.current_custody ?? [];
            const openingBrokerName = getBrokerName(lot.opening_broker_id);
            const openingUnitPrice = safeDecimal(lot.opening_unit_price);
            const quantityOpen = safeDecimal(lot.open_quantity);
            const quantityOriginal = safeDecimal(lot.original_quantity);
            const openingValue = safeDecimal(lot.original_cost);
            const brokerFilterValues = Array.from(
                new Set(
                    (currentCustody.length > 0 ? currentCustody : [{broker_id: lot.opening_broker_id, custody_type: 'BROKER', quantity: lot.open_quantity}]).flatMap((slice) => {
                        const brokerId = safeNumber(slice.broker_id);
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
                        const brokerId = safeNumber(slice.broker_id);
                        return slice.custody_type === 'IN_TRANSIT' && brokerId == null ? label('brokers.lots.inTransit', 'In transit') : getBrokerName(brokerId);
                    })
                    .join(' '),
                openingUnitPrice,
                quantityOpen,
                quantityOriginal,
                openingValue,
                currentValue: safeDecimal(lot.open_value),
                assetIncome: safeDecimal(lot.asset_income),
                totalPnl: safeDecimal(lot.total_pnl),
                totalReturn: safeDecimal(lot.total_return),
                annualizedReturn: safeDecimal(lot.annualized_return),
                allocatedFees: safeDecimal(lot.allocated_fees),
                allocatedTaxes: safeDecimal(lot.allocated_taxes),
                netTotalPnl: safeDecimal(lot.net_total_pnl),
                netTotalReturn: safeDecimal(lot.net_total_return),
                netMetricsStatus: lot.net_metrics_status === 'UNAVAILABLE' ? 'UNAVAILABLE' : 'AVAILABLE',
                relativeReturn: safeDecimal(lot.relative_return),
            };
            return row;
        }),
    );

    // STK-2c: the reward lots of one broker as one row, open or closed (rewardLotGroups.ts). Without groups the table
    // is exactly what it was: the rows as given, sorted by the table itself.
    let rewardGroups = $derived(groupRewardLots(rows, (row) => row.lot.opening_kind === 'REWARD'));
    let expandedGroups = $state<Set<string>>(new Set());
    let sortState = $state<SortState | null>(null);

    function toggleGroup(groupId: string): void {
        const next = new Set(expandedGroups);
        if (next.has(groupId)) next.delete(groupId);
        else next.add(groupId);
        expandedGroups = next;
    }

    /** A group's row: its lots' column sums and the return of those sums (D-MF6(b), as the totals row); no unit price. */
    function groupHeadRow(groupId: string, members: readonly DisplayRow[]): DisplayRow {
        const first = members[0];
        const states = Array.from(new Set(members.flatMap((row) => row.filterStates)));
        const primaries = new Set(members.map((row) => row.primaryState));
        const totalPnl = sumCompleteOrNull(members, (row) => row.totalPnl);
        const openingValue = sumCompleteOrNull(members, (row) => row.openingValue);
        const netTotalPnl = sumCompleteOrNull(members, (row) => row.netTotalPnl);
        return {
            ...first,
            rowId: groupId,
            lotId: -1,
            openingDate: first.openingDate,
            primaryState: primaries.size === 1 ? first.primaryState : 'PARTIALLY_CLOSED',
            secondaryStates: secondaryStates(states),
            filterStates: states,
            brokerFilterValues: Array.from(new Set(members.flatMap((row) => row.brokerFilterValues))),
            custodySlices: [],
            custodySearchText: '',
            openingUnitPrice: null,
            quantityOpen: sumNumeric(members, (row) => row.quantityOpen),
            quantityOriginal: sumNumeric(members, (row) => row.quantityOriginal),
            openingValue,
            currentValue: sumCompleteOrNull(members, (row) => row.currentValue),
            assetIncome: sumCompleteOrNull(members, (row) => row.assetIncome),
            totalPnl,
            totalReturn: ratioOrNull(totalPnl, openingValue),
            annualizedReturn: null,
            allocatedFees: sumCompleteOrNull(members, (row) => row.allocatedFees),
            allocatedTaxes: sumCompleteOrNull(members, (row) => row.allocatedTaxes),
            netTotalPnl,
            netTotalReturn: ratioOrNull(netTotalPnl, openingValue),
            netMetricsStatus: members.some((row) => row.netMetricsStatus === 'UNAVAILABLE') ? 'UNAVAILABLE' : 'AVAILABLE',
            relativeReturn: null,
            groupHead: {size: members.length, firstDate: first.openingDate, lastDate: members[members.length - 1].openingDate},
        };
    }

    /** The top-level rows in the lots' own order: each group's head where its first lot was, its other lots left out. */
    function topLevelRows(): DisplayRow[] {
        const heads = new Map(groupHeads.map((head) => [head.rowId, head]));
        const groupOf = new Map([...rewardGroups.entries()].flatMap(([groupId, members]) => members.map((row) => [row.lotId, groupId] as const)));
        const placed = new Set<string>();
        const top: DisplayRow[] = [];
        for (const row of rows) {
            const groupId = groupOf.get(row.lotId);
            if (groupId == null) top.push(row);
            else if (!placed.has(groupId)) {
                placed.add(groupId);
                top.push(heads.get(groupId)!);
            }
        }
        return top;
    }

    let groupHeads = $derived([...rewardGroups.entries()].map(([groupId, members]) => groupHeadRow(groupId, members)));
    let childRows = $derived(new Map([...rewardGroups.entries()].map(([groupId, members]) => [groupId, members.map((row) => ({...row, groupChildOf: groupId}))])));
    let sortComparator = $derived.by<((a: DisplayRow, b: DisplayRow) => number) | undefined>(() => {
        const state = sortState;
        const column = state ? baseColumns.find((candidate) => candidate.id === state.columnId) : undefined;
        return state && column ? (a, b) => compareRowsByColumn(column, a, b, state.direction) : undefined;
    });
    let visibleRows = $derived(rewardGroups.size === 0 ? rows : arrangeRows(topLevelRows(), childRows, expandedGroups, sortComparator));

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
            // A page that cannot open it does not offer it (77 SEL-M, Q-SEL-12)
            visible: (row) => onCustodyCellClick != null && !row.groupHead,
        },
        {
            id: 'lot-view-gantt-action',
            icon: BarChart3,
            label: () => label('brokers.lots.viewGanttLot', 'Go to lot in Gantt'),
            onClick: (row) => onViewGanttLot?.(row.lotId),
            visible: (row) => onViewGanttLot != null && !row.groupHead,
        },
        {
            id: 'lot-goto-opening-transaction-action',
            icon: ExternalLink,
            label: () => label('brokers.lots.goToOpeningTransaction', 'Go to opening transaction'),
            onClick: (row) => onGotoOpeningTransaction?.(row.lot),
            visible: (row) => onGotoOpeningTransaction != null && !row.groupHead,
        },
        {
            id: 'lot-copy-id-action',
            icon: Copy,
            visible: (row) => !row.groupHead,
            label: () => label('brokers.lots.copyLotIdentifier', 'Copy lot identifier'),
            onClick: async (row) => {
                try {
                    await writeTextToClipboard(String(row.lotId));
                } catch {
                    toasts.error($_('support.clipboardUnavailable'));
                    return;
                }
                toasts.success(`${label('brokers.lots.lotIdentifierCopied', 'Lot identifier copied')}: ${row.lotId}. ${label('brokers.lots.lotIdentifierHelp', 'Stable technical identifier derived from the opening transaction, used for audit, support and API correlation.')}`);
            },
        },
    ]);

    let hasDifferingStates = $derived.by(() => new Set(rows.map((row) => row.filterStates.join('|'))).size > 1);
    let hasMixedDirections = $derived.by(() => new Set(rows.map((row) => row.direction)).size > 1);
    // A column stays visible when one of its values is unknown (null, shown as «—»): hiding it would read as zero.
    let hasPositiveAssetIncome = $derived.by(() => rows.some((row) => row.assetIncome == null || row.assetIncome > 0));
    let hasNetCosts = $derived.by(() => rows.some((row) => isUnknownOrNonZero(row.allocatedFees) || isUnknownOrNonZero(row.allocatedTaxes)));

    function buildFooterCells(footerRows: DisplayRow[]): Record<string, FooterCellContent> {
        // Amounts that can be unknown total only when every row is known; a partial sum would read as complete.
        const totalPnl = sumCompleteOrNull(footerRows, (row) => row.totalPnl);
        const openingValueSum = sumCompleteOrNull(footerRows, (row) => row.openingValue);
        const totalReturn = ratioOrNull(totalPnl, openingValueSum);
        const netTotalPnl = sumCompleteOrNull(footerRows, (row) => row.netTotalPnl);
        const netTotalReturn = ratioOrNull(netTotalPnl, openingValueSum);

        return {
            'opening-date': label('brokers.lots.footerTotals', label('assets.distribution.total', 'Totals')),
            'total-pnl': signedAmountCell(totalPnl),
            'total-return': signedPercentCell(totalReturn),
            'asset-income': currencyCell(sumCompleteOrNull(footerRows, (row) => row.assetIncome)),
            'allocated-fees': currencyCell(sumCompleteOrNull(footerRows, (row) => row.allocatedFees)),
            'allocated-taxes': currencyCell(sumCompleteOrNull(footerRows, (row) => row.allocatedTaxes)),
            'net-total-pnl': signedAmountCell(netTotalPnl),
            'net-total-return': signedPercentCell(netTotalReturn),
            'current-value': currencyCell(sumCompleteOrNull(footerRows, (row) => row.currentValue)),
            'open-quantity': quantityValueCell(sumNumeric(footerRows, (row) => row.quantityOpen)),
            'opening-price': unitPriceCell(
                weightedAverageCompleteOrNull(
                    footerRows,
                    (row) => row.openingUnitPrice,
                    (row) => row.currentValue,
                ),
            ),
            'open-return': signedPercentCell(
                weightedAverageCompleteOrNull(
                    footerRows,
                    (row) => row.relativeReturn,
                    (row) => row.currentValue,
                ),
            ),
        };
    }

    let baseColumns = $derived.by<ColumnDef<DisplayRow>[]>(() => [
        {
            id: 'opening-date',
            header: () => label('brokers.lots.openingDate', 'Opening Date'),
            cell: (row) => (row.groupHead ? groupHeadCell(row) : {type: 'date', value: row.openingDate, format: 'date'}),
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
            id: 'annualized-return',
            header: () => label('brokers.lots.annualizedReturn', 'Annualized'),
            headerTooltip: () => label('brokers.lots.annualizedReturnTooltip', 'Total return annualized (CAGR) over the lot holding window, for comparison across lots held for different durations.'),
            cell: (row) => signedPercentCell(row.annualizedReturn),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 130,
            sortable: true,
            filterable: false,
            getValue: (row) => row.annualizedReturn ?? Number.NEGATIVE_INFINITY,
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
            id: 'allocated-fees',
            header: () => label('brokers.lots.allocatedFees', 'Fees'),
            cell: (row) => currencyCell(row.allocatedFees),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 130,
            sortable: true,
            filterable: false,
            hiddenByDefault: !hasNetCosts,
            getValue: (row) => row.allocatedFees ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'allocated-taxes',
            header: () => label('brokers.lots.allocatedTaxes', 'Taxes'),
            cell: (row) => currencyCell(row.allocatedTaxes),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 130,
            sortable: true,
            filterable: false,
            hiddenByDefault: !hasNetCosts,
            getValue: (row) => row.allocatedTaxes ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'net-total-pnl',
            header: () => label('brokers.lots.netTotalPnl', 'Net P&L'),
            cell: (row) => netAmountCell(row),
            type: 'number',
            align: 'right',
            width: 170,
            minWidth: 150,
            sortable: true,
            filterable: false,
            hiddenByDefault: !hasNetCosts,
            getValue: (row) => row.netTotalPnl ?? Number.NEGATIVE_INFINITY,
        },
        {
            id: 'net-total-return',
            header: () => label('brokers.lots.netTotalReturn', 'Net return'),
            cell: (row) => netReturnCell(row),
            type: 'number',
            align: 'right',
            width: 150,
            minWidth: 130,
            sortable: true,
            filterable: false,
            hiddenByDefault: !hasNetCosts,
            getValue: (row) => row.netTotalReturn ?? Number.NEGATIVE_INFINITY,
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
            cell: (row) => unitPriceCell(row.openingUnitPrice),
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

    // With groups the rows reach the table already in order: its own sort keeps them (stable), the header still shows it.
    let columns = $derived(rewardGroups.size === 0 ? baseColumns : baseColumns.map((column) => (column.sortable === false ? column : {...column, sortFn: () => 0})));

    let effectiveSelectedLotIds = $derived(selectedLotIds ?? internalSelectedLotIds);
    // STK-2c: the selection is the set of lot ids; the table's rows show it (a group row when all its lots are selected)
    let effectiveSelectedRowIds = $derived(tableRowIdsFor(effectiveSelectedLotIds, visibleRows, rewardGroups));
    let emptyMessage = $derived(label('brokers.lots.noUnifiedLots', 'No lots match current filters'));

    function handleTableSelectionChange(selectedIds: string[]): void {
        // A group row checked or unchecked takes all its lots; the lots no row shows (a closed group's) keep their state
        const lotIds = lotsAfterTableSelection(effectiveSelectedLotIds, appliedSelectionRowIds, selectedIds, rewardGroups);
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

<section class="rounded-lg border border-lf-subtle/80 bg-lf-panel/80 text-lf-primary" data-testid="unified-lots-table">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-lf-subtle/80 px-4 py-3">
        <div class="flex min-w-0 items-center gap-3">
            <div>
                <div class="text-base font-semibold text-lf-primary">{label('brokers.lots.unifiedLots', 'Lots')}</div>
                <div class="text-xs text-lf-muted">{translateOr((key) => $_(key, {values: {method: matchingMethod}}), 'brokers.lots.unifiedLotsHint', `Unified lots view (${matchingMethod}) with multi-selection and custody drill-down.`)}</div>
            </div>
            <span class="inline-flex min-w-7 items-center justify-center rounded-full bg-lf-neutral px-2 py-0.5 text-xs font-semibold tabular-nums text-lf-secondary">
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
            footerCells={(footerRows: DisplayRow[]) => buildFooterCells(lotRowsOf(footerRows, rewardGroups))}
            getRowSelectionState={(row: DisplayRow) => (row.groupHead && groupSelection(rewardGroups.get(row.rowId) ?? [], new Set(effectiveSelectedLotIds)) === 'partial' ? 'partial' : null)}
            opensPage={(row: DisplayRow) => !row.groupChildOf}
            onSortChange={(state) => (sortState = state)}
            onSelectionChange={handleTableSelectionChange}
            onRowClick={(row) => (row.groupHead ? toggleGroup(row.rowId) : tableRef?.toggleRowSelectionById(row.rowId))}
            onRowDoubleClick={(row) => {
                if (!row.groupHead) onRowDoubleClick?.(row.lotId);
            }}
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
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 26%, var(--lf-surface-card));
        }
        .dark .unified-lots-table-wrap tr.lot-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 14%, var(--lf-surface-card));
        }
        .unified-lots-table-wrap tr.lot-row-tinted.highlighted > td {
            /* A highlighted row is the selection tint (palette, `--lf-selected`); the pulse peaks on a deeper one. */
            --lot-highlight-base: var(--lf-selected);
            --lot-highlight-peak: color-mix(in oklab, var(--lf-checked) 20%, transparent);
            background: var(--lot-highlight-base) !important;
            animation: tinted-lot-highlight-pulse 0.6s ease-in-out 3;
        }
        /* On the selection tint the muted text falls under 4.5:1 (design system, rule 5; TC-15). */
        .unified-lots-table-wrap tr.lot-row-tinted.highlighted > td .text-lf-muted {
            color: var(--lf-text-secondary);
        }
        /* STK-2c: the reward lots group — the rewards colour of the charts (--lf-cat-index), as in the approved mockup */
        .unified-lots-table-wrap tr.reward-group-row > td {
            background: var(--lf-cat-index-soft);
            cursor: pointer;
        }
        .unified-lots-table-wrap tr.reward-group-row > td:first-child {
            box-shadow: inset 3px 0 0 var(--lf-cat-index);
        }
        .unified-lots-table-wrap tr.reward-group-child > td:first-child {
            box-shadow: inset 3px 0 0 color-mix(in srgb, var(--lf-cat-index) 45%, transparent);
        }
        .unified-lots-table-wrap tr.reward-group-child > td:nth-child(2) {
            padding-left: 2rem;
        }
        .unified-lots-table-wrap .reward-group-dot {
            background: var(--lf-cat-index);
        }
        .unified-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 68%, var(--lf-surface-card));
        }
        .dark .unified-lots-table-wrap tr.lot-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 22%, var(--lf-surface-card));
        }
    }
</style>
