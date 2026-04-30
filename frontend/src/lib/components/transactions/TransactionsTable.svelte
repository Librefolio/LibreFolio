<!--
  TransactionsTable.svelte — read-view of /transactions list.

  Step 5 of plan-phase07-transaction-Part4.prompt.md.

  Responsibilities:
  - Always-pair-adjacent rendering: linked TX (TRANSFER, FX_CONVERSION) are always
    rendered as adjacent rows; giver (out, qty<0 or cash<0) above, receiver (in)
    below. When the partner is filtered out of `mainRows`, it is shown as a
    "ghost row" with reduced opacity (taken from `partnerRows`). Broker tint is
    uniform across all rows (ghost or not). Direction arrows (⬇/⬆) appear in
    the Links column for each half of a pair.
  - Pair-never-split paginator: pairs are kept on the same page; if a pair would
    cross a page boundary it is pushed entirely to the next page.
  - Columns: date, type-icon, quantity (📈/📉), cash, links (event dot + pair
    arrows + 🔗), asset, broker, tags. Selection + actions managed by DataTable.
  - GoTo / row actions are emitted via callbacks; this component does not
    perform navigation or open modals on its own.

  Pattern: Svelte 5 runes, dark mode, `data-testid` everywhere.
-->
<script lang="ts">
    import {_ as t, locale} from '$lib/i18n';
    import {Eye, Pencil, Copy, Trash2} from 'lucide-svelte';

    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTablePagination from '$lib/components/table/DataTablePagination.svelte';
    import type {ColumnDef, FilterValue, RowAction, SortState} from '$lib/components/table/types';

    import {assetStoreVersion, ensureAssetsLoaded, getAssetInfo} from '$lib/stores/assetStore';
    import {ensureCurrenciesLoaded, currencyStoreVersion} from '$lib/stores/currencyStore';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/brokerColors';
    import {getBrokerIconUrl, getBrokerIconUrlById} from '$lib/utils/brokerHelpers';
    import {getStringBadgeStyle, getStringColor} from '$lib/utils/colors';
    import {formatCurrencyAmountHtml, formatCurrencyAmountPlain} from '$lib/utils/currencyFormat';
    import {getTransactionTypeIconUrl, getTxTypeDocUrl, TX_TYPES, getEventTypeEmoji} from '$lib/stores/transactionTypeStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import TxTooltipCell from './cells/TxTooltipCell.svelte';
    import TxLinksCell from './cells/TxLinksCell.svelte';
    import TxTypeIconCell from './cells/TxTypeIconCell.svelte';

    // Sentinel keep-imports (used in reactive expressions but not statically referenced).
    void $currencyStoreVersion;

    // Hydrate stores used by the cell renderers.
    void ensureAssetsLoaded();
    ensureCurrenciesLoaded($locale ?? 'en');

    // =========================================================================
    // Types
    // =========================================================================

    export interface TXReadItem {
        id: number;
        broker_id: number;
        asset_id?: number | null;
        type: string;
        date: string;
        quantity: string;
        cash?: {code: string; amount: string} | null;
        related_transaction_id?: number | null;
        tags?: string[] | null;
        description?: string | null;
        cost_basis_override?: string | null;
        asset_event_id?: number | null;
        created_at: string;
        updated_at: string;
    }

    export interface AssetEvent {
        id: number;
        asset_id: number;
        type: string;
        date: string;
        value: string;
        currency: string;
        is_auto: boolean;
        notes?: string | null;
    }

    /**
     * Display row = TXReadItem + decoration metadata for adjacency rendering.
     */
    export interface DisplayRow {
        tx: TXReadItem;
        /** True when partner is rendered for context (not in main filter set). */
        isGhost: boolean;
        /** True when this row is the receiver half of a linked pair. */
        isReceiver: boolean;
        /** Pair anchor id (giver tx id). null when not part of a pair. */
        pairAnchorId: number | null;
    }

    interface Props {
        mainRows: TXReadItem[];
        partnerRows: TXReadItem[];
        brokers: BrokerLike[];
        eventTooltipMap: Map<number, AssetEvent>;
        /** 1-based current page (default 1). */
        currentPage?: number;
        /** Target page size — pairs may push effective size to N±1. Default 50. */
        pageSize?: number;
        onSelectionChange?: (rows: TXReadItem[]) => void;
        onLinkedPairClick?: (row: TXReadItem) => void;
        onEventBadgeClick?: (row: TXReadItem) => void;
        onEditRow?: (row: TXReadItem) => void;
        onCloneRow?: (row: TXReadItem) => void;
        onDeleteRow?: (row: TXReadItem) => void;
        onViewRow?: (row: TXReadItem) => void;
        onPageChange?: (page: number) => void;
        onPageSizeChange?: (pageSize: number) => void;
        /** Bidirectional URL filter sync. When provided, header column filters
         *  are emitted (keyed by `urlKey` or column id). The parent serializes
         *  to URL query params and passes them back via `initialFilters`. */
        onFiltersChange?: (filters: Record<string, FilterValue>) => void;
        initialFilters?: Record<string, FilterValue>;
    }

    let {mainRows = [], partnerRows = [], brokers = [], eventTooltipMap = new Map(), currentPage = 1, pageSize = 50, onSelectionChange, onLinkedPairClick, onEventBadgeClick, onEditRow, onCloneRow, onDeleteRow, onViewRow, onPageChange, onPageSizeChange, onFiltersChange, initialFilters}: Props = $props();

    /** Exposed DataTable ref for ColumnVisibilityToggle / external selection control. */
    let tableRef: DataTable<DisplayRow> | undefined = $state(undefined);

    /** Track active column filters so we can pre-filter displayRows before
     *  the pair-never-split paginator. Initialized from `initialFilters`. */
    // svelte-ignore state_referenced_locally
    let activeColumnFilters = $state<Record<string, FilterValue>>(initialFilters ? {...initialFilters} : {});

    /** Intercept filter changes: update local state and forward to parent. */
    function handleFiltersChangeInternal(record: Record<string, FilterValue>) {
        activeColumnFilters = {...record};
        onFiltersChange?.(record);
    }

    /** Mirror of DataTable's internal `sortState`, exposed via `onSortChange`.
     *  Used together with `activeColumnFilters` to decide whether linked-pair
     *  rows must be kept adjacent (pair-grouping ON) or treated as ordinary
     *  independent rows (pair-grouping OFF). */
    let activeSort = $state<SortState | null>(null);

    /** Mirror of DataTable's "show selected only" toggle. Used to adjust the
     *  external paginator totalItems in grouped mode. */
    let showSelectedOnlyActive = $state(false);

    /** Set of currently selected row IDs (DataTable string keys). Kept in sync
     *  via `onSelectionChange` so the external paginator can filter by selection
     *  when `showSelectedOnly` is active. */
    let selectedIdSet = $state<Set<string>>(new Set());

    /** True when the user has neither active filters nor active sort:
     *  the natural "browse" mode where giver+receiver pairs stay glued
     *  together and ghost partners are surfaced. As soon as a filter or
     *  sort is applied, pairs become regular rows so they participate in
     *  the user's ordering/filtering on equal footing. */
    let isGrouped = $derived(Object.keys(activeColumnFilters).length === 0 && activeSort == null);

    export function getTableRef() {
        return tableRef;
    }

    /** Total number of transactions in the current dataset (excluding ghost partners). */
    export function getTotalCount(): number {
        return mainRows.length;
    }

    /** Clear all column filters (called by parent on refresh). */
    export function resetFilters(): void {
        activeColumnFilters = {};
        tableRef?.clearFilters();
    }

    /**
     * Navigate to the page containing a linked partner row, wait for the DOM
     * to update, then return. The caller is responsible for pulsing the row.
     *
     * - **Flat mode**: delegates to DataTable's `navigateToRowId` which
     *   handles internal pagination + scroll.
     * - **Grouped mode**: finds the page containing the partner in the
     *   pair-never-split paginator and emits `onPageChange`.
     */
    export async function navigateToPartner(partnerId: number): Promise<void> {
        const rowId = `tx-${partnerId}`;
        const ghostId = `ghost-${partnerId}`;

        if (!isGrouped) {
            // Flat mode — DataTable handles pagination internally.
            tableRef?.navigateToRowId(rowId);
        } else {
            // Grouped mode — find the page containing the partner.
            const pageIdx = pages.findIndex((p) => p.some((d) => getRowId(d) === rowId || getRowId(d) === ghostId));
            if (pageIdx >= 0 && pageIdx !== safePage - 1) {
                onPageChange?.(pageIdx + 1);
            }
        }

        // Wait for DOM update after page change.
        const {tick} = await import('svelte');
        await tick();
        await new Promise((r) => requestAnimationFrame(r));
    }

    // =========================================================================
    // Always-pair-adjacent algorithm
    // =========================================================================

    /** Determine which row of a pair is the giver (rendered above receiver). */
    function isGiver(tx: TXReadItem): boolean {
        // TRANSFER: qty<0 = giver. FX_CONVERSION / DEPOSIT-WITHDRAWAL: cash<0 = giver.
        const q = Number(tx.quantity);
        if (Number.isFinite(q) && q !== 0) return q < 0;
        const c = tx.cash ? Number(tx.cash.amount) : 0;
        return c < 0;
    }

    /** Build the partner lookup: id → tx (from main + ghost partner rows). */
    let partnerLookup = $derived.by(() => {
        const m = new Map<number, TXReadItem>();
        for (const r of mainRows) m.set(r.id, r);
        for (const r of partnerRows) m.set(r.id, r);
        return m;
    });

    /**
     * Build display rows.
     *
     * **Grouped mode** (no filter + no sort, `isGrouped === true`): always
     * pair-adjacent semantics — for each main row with a partner, emit
     * giver+receiver in order; missing partners surface as ghost rows. This
     * is the "browse" experience: linked TX stay glued together.
     *
     * **Flat mode** (any filter or sort active, `isGrouped === false`): each
     * `mainRows` entry becomes an independent row. Ghost partners are not
     * synthesized — if the partner doesn't match the active filters the
     * server didn't return it, so it stays out (consistent with the rest of
     * the table). The ⬆/⬇ arrow is still rendered when the row has a
     * partner, so direction is recognizable even out of context — the
     * tooltip resolves any ambiguity at distance.
     */
    let displayRows = $derived.by<DisplayRow[]>(() => {
        if (!isGrouped) {
            // Flat mode: keep `isReceiver` so the ⬆/⬇ arrow still renders
            // for linked rows (computed from quantity sign / role helper).
            const out: DisplayRow[] = [];
            for (const r of mainRows) {
                const hasPartner = r.related_transaction_id != null;
                out.push({
                    tx: r,
                    isGhost: false,
                    isReceiver: hasPartner ? !isGiver(r) : false,
                    // Use the partner-id as anchor so the arrow renders; the
                    // pair-never-split paginator is bypassed in flat mode.
                    pairAnchorId: hasPartner ? (r.related_transaction_id ?? null) : null,
                });
            }
            return out;
        }

        // Grouped mode — original always-pair-adjacent algorithm.
        const mainIds = new Set(mainRows.map((r) => r.id));
        const rendered = new Set<number>();
        const out: DisplayRow[] = [];

        for (const r of mainRows) {
            if (rendered.has(r.id)) continue;
            const partnerId = r.related_transaction_id ?? null;
            if (partnerId == null || !partnerLookup.has(partnerId)) {
                // Stand-alone row.
                out.push({tx: r, isGhost: false, isReceiver: false, pairAnchorId: null});
                rendered.add(r.id);
                continue;
            }
            const partner = partnerLookup.get(partnerId)!;
            const partnerIsGhost = !mainIds.has(partner.id);

            // Determine giver / receiver order.
            const rIsGiver = isGiver(r);
            const partnerIsGiverFlag = isGiver(partner);
            // If both report the same role (data quirk) prefer the one with neg qty
            // as giver; fallback: keep `r` as giver.
            const giver: TXReadItem = rIsGiver || !partnerIsGiverFlag ? r : partner;
            const receiver: TXReadItem = giver.id === r.id ? partner : r;
            const giverIsGhost = !mainIds.has(giver.id);
            const receiverIsGhost = !mainIds.has(receiver.id);

            out.push({tx: giver, isGhost: giverIsGhost, isReceiver: false, pairAnchorId: giver.id});
            out.push({tx: receiver, isGhost: receiverIsGhost, isReceiver: true, pairAnchorId: giver.id});
            rendered.add(giver.id);
            rendered.add(receiver.id);

            // Mark partner ghost-id as rendered too (defensive — ghost rows are
            // never in mainRows so they wouldn't be revisited anyway).
            if (partnerIsGhost) rendered.add(partner.id);
        }
        return out;
    });

    // =========================================================================
    // Pre-filter displayRows by active column filters (so pagination reflects
    // the filtered count, not the full dataset). DataTable also applies
    // filters internally — but since data is already filtered, it's a no-op.
    // =========================================================================

    /** Apply active column filters to displayRows. */
    let filteredDisplayRows = $derived.by<DisplayRow[]>(() => {
        const filters = activeColumnFilters;
        const entries = Object.entries(filters).filter(([, v]) => v != null);
        if (entries.length === 0) return displayRows;

        return displayRows.filter((d) => {
            for (const [urlKeyOrId, fv] of entries) {
                if (!fv) continue;
                const col = columns.find((c) => (c.urlKey ?? c.id) === urlKeyOrId || c.id === urlKeyOrId);
                if (!col) continue;
                const getValue = col.getValue ?? col.cell;
                const rawValue = getValue(d);

                if (fv.type === 'enum') {
                    if (!fv.selected.includes(String(rawValue))) return false;
                } else if (fv.type === 'multi-enum') {
                    if (fv.selected.length > 0) {
                        const rowVals = col.getMultiValue ? col.getMultiValue(d) : String(rawValue ?? '').split(',');
                        if (!fv.selected.some((sel) => rowVals.includes(sel))) return false;
                    }
                } else if (fv.type === 'date') {
                    const dateStr = typeof rawValue === 'object' && rawValue !== null && 'type' in rawValue && (rawValue as unknown as {type: string}).type === 'date' ? String((rawValue as unknown as {value: string}).value) : String(rawValue);
                    const date = new Date(dateStr);
                    if (fv.from && date < new Date(fv.from)) return false;
                    if (fv.to && date > new Date(fv.to)) return false;
                } else if (fv.type === 'currency-stack') {
                    if (fv.items.length > 0) {
                        const cv = col.getCurrencyValue ? col.getCurrencyValue(d) : null;
                        if (!cv) return false;
                        if (!fv.items.some((it) => it.code === cv.code && (it.min === undefined || cv.amount >= it.min) && (it.max === undefined || cv.amount <= it.max))) return false;
                    }
                }
            }
            return true;
        });
    });

    // =========================================================================
    // Paginator
    // =========================================================================

    /**
     * Slice `filteredDisplayRows` into pages.
     *  - Grouped mode (`isGrouped`): pair-never-split — pairs never cross a
     *    page boundary; effective page size may be `pageSize ± 1` to preserve
     *    adjacency.
     *  - Flat mode: standard fixed-size pagination — every row is independent
     *    and ordering wins over pair coupling. `pageSize === 0` ⇒ single page.
     */
    let pages = $derived.by<DisplayRow[][]>(() => {
        const rows = filteredDisplayRows;
        const result: DisplayRow[][] = [];
        if (!isGrouped) {
            if (pageSize <= 0) return rows.length > 0 ? [rows] : [[]];
            for (let i = 0; i < rows.length; i += pageSize) {
                result.push(rows.slice(i, i + pageSize));
            }
            if (result.length === 0) result.push([]);
            return result;
        }
        // Grouped mode — pair-never-split paginator.
        let buf: DisplayRow[] = [];
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const isPair = row.pairAnchorId != null;
            const nextIsPartner = isPair && i + 1 < rows.length && rows[i + 1].pairAnchorId === row.pairAnchorId && !row.isReceiver;
            const wouldExceed = buf.length >= pageSize;
            const wouldSplitPair = nextIsPartner && buf.length + 1 > pageSize;
            if ((wouldExceed && !row.isReceiver) || wouldSplitPair) {
                result.push(buf);
                buf = [];
            }
            buf.push(row);
        }
        if (buf.length > 0) result.push(buf);
        if (result.length === 0) result.push([]);
        return result;
    });

    let totalPages = $derived(pages.length);
    let safePage = $derived(Math.min(Math.max(1, currentPage), totalPages));
    /** In grouped mode: page slice from custom paginator (pre-filtered).
     *  In flat mode: ALL displayRows — DataTable handles sort+filter+pagination internally. */
    let visibleRows = $derived(isGrouped ? (pages[safePage - 1] ?? []) : displayRows);

    /** Total items for the external paginator in grouped mode.
     *  When "show selected only" is active inside DataTable, filter the count
     *  to match only selected rows — otherwise the paginator shows a stale total. */
    let externalPaginatorTotal = $derived.by(() => {
        if (!showSelectedOnlyActive || selectedIdSet.size === 0) return filteredDisplayRows.length;
        return filteredDisplayRows.filter((d) => selectedIdSet.has(getRowId(d))).length;
    });

    // =========================================================================
    // Helpers
    // =========================================================================

    function brokerName(brokerId: number): string {
        return brokers.find((b) => b.id === brokerId)?.name ?? `#${brokerId}`;
    }

    function brokerStyle(brokerId: number): string {
        const c = getBrokerColor(brokerId, brokers);
        // Inject CSS custom properties for row tint, broker badge, and dot.
        // --broker-vivid is hsl(hue, 75%, 50%) for dark-mode row tints.
        // --broker-vivid-light is hsl(hue, 60%, 80%) for light-mode row tints.
        return `--broker-bg:${c.bg};--broker-text:${c.text};--broker-dark-bg:${c.darkBg};--broker-dark-text:${c.darkText};--broker-vivid:${c.vivid};--broker-vivid-light:${c.vividLight};`;
    }

    function formatQty(q: string): string {
        const n = Number(q);
        if (!Number.isFinite(n) || n === 0) return '0';
        const formatted = n.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
        const emoji = n > 0 ? ' 📈' : ' 📉';
        return `${n > 0 ? '+' : ''}${formatted}${emoji}`;
    }

    function eventTooltipText(eventId: number): string {
        const ev = eventTooltipMap.get(eventId);
        if (!ev) return $t('transactions.linkedEvent') || 'Linked event';
        const emoji = getEventTypeEmoji(ev.type);
        const typeName = $t(`assetDetail.eventType.${ev.type}`) || ev.type;
        const amount = Number(ev.value);
        const currText = Number.isFinite(amount) ? formatCurrencyAmountPlain(amount, ev.currency) : `${ev.value} ${ev.currency}`;
        // Line 1: emoji + translated type name + date
        const line1 = `${emoji} ${typeName} · ${ev.date}`;
        // Line 2: formatted amount
        const line2 = currText + (ev.is_auto ? '  ⚙ auto' : '');
        // Line 3+: notes (if any)
        const lines = [line1, line2];
        if (ev.notes) lines.push(ev.notes);
        return lines.join('\n');
    }

    /**
     * Build a context-specific tooltip for the 🔗 link icon based on TX type
     * and role (giver/receiver). Explains what this linked pair means.
     */
    function linkedPairTooltip(d: DisplayRow): string {
        const type = d.tx.type;
        const partner = d.tx.related_transaction_id != null ? partnerLookup.get(d.tx.related_transaction_id) : null;
        const partnerBroker = partner ? brokerName(partner.broker_id) : '?';
        const thisBroker = brokerName(d.tx.broker_id);
        const currency = d.tx.cash?.code ?? '?';

        /** Format a cash amount as plain text for tooltips. */
        const fmtCash = (code: string, amount: string | undefined): string => {
            const n = Number(amount ?? 0);
            if (!Number.isFinite(n)) return `${amount} ${code}`;
            return formatCurrencyAmountPlain(Math.abs(n), code);
        };

        if (type === 'TRANSFER') {
            if (d.isReceiver) {
                return `📥 ${$t('transactions.linkTooltip.transferIn') || `Received from ${partnerBroker}`}`.replace('{broker}', partnerBroker);
            }
            return `📤 ${$t('transactions.linkTooltip.transferOut') || `Sent to ${partnerBroker}`}`.replace('{broker}', partnerBroker);
        }
        if (type === 'FX_CONVERSION') {
            const thisAmount = fmtCash(currency, d.tx.cash?.amount);
            const partnerCurr = partner?.cash?.code ?? '?';
            const partnerAmount = fmtCash(partnerCurr, partner?.cash?.amount);
            // Show both sides: "Converting 1,000.00 € EUR → 1,090.00 $ USD"
            if (d.isReceiver) {
                return `💱 ${$t('transactions.linkTooltip.fxReceive') || `Converted from ${partnerAmount}`}`.replace('{amount}', `${partnerAmount} → ${thisAmount}`);
            }
            return `💱 ${$t('transactions.linkTooltip.fxSend') || `Converting to ${partnerAmount}`}`.replace('{amount}', `${thisAmount} → ${partnerAmount}`);
        }
        // Cash transfers between brokers (DEPOSIT↔WITHDRAWAL, or same-type linked)
        if (type === 'DEPOSIT' && partner) {
            return `🏦 ${$t('transactions.linkTooltip.depositFrom') || `Cash in from ${partnerBroker}`}`.replace('{broker}', partnerBroker).replace('{currency}', currency);
        }
        if (type === 'WITHDRAWAL' && partner) {
            return `🏦 ${$t('transactions.linkTooltip.withdrawalTo') || `Cash out to ${partnerBroker}`}`.replace('{broker}', partnerBroker).replace('{currency}', currency);
        }
        // Generic fallback — cash transfer / linked pair
        return `🏦 ${$t('transactions.linkTooltip.generic') || 'Cash transfer'} — ${thisBroker} ↔ ${partnerBroker}`;
    }

    // =========================================================================
    // DataTable wiring
    // =========================================================================

    function getRowId(d: DisplayRow): string {
        // Ghost rows share id-space with main rows; prefix to keep them unique
        // in DataTable selection state.
        return d.isGhost ? `ghost-${d.tx.id}` : `tx-${d.tx.id}`;
    }

    function getRowClass(d: DisplayRow): string {
        const cls: string[] = ['tx-row-tinted'];
        if (d.isGhost) cls.push('tx-row-ghost');
        if (d.isReceiver) cls.push('tx-row-receiver');
        return cls.join(' ');
    }

    function getRowStyle(d: DisplayRow): string {
        return brokerStyle(d.tx.broker_id);
    }

    function isRowSelectable(d: DisplayRow): boolean {
        // Ghost rows are selectable (legitimate operations on the partner).
        return !!d;
    }

    function handleSelectionChange(ids: string[]) {
        selectedIdSet = new Set(ids);
        // Map back to TXReadItem from displayRows (giver/receiver/ghost).
        const out: TXReadItem[] = [];
        for (const d of displayRows) {
            if (selectedIdSet.has(getRowId(d))) out.push(d.tx);
        }
        onSelectionChange?.(out);
    }

    /** Escape a string for safe inclusion in an HTML attribute / text node. */
    function escapeHtml(s: string): string {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    let columns = $derived<ColumnDef<DisplayRow>[]>([
        {
            id: 'date',
            header: () => $t('transactions.table.date'),
            type: 'date',
            width: 110,
            urlKey: 'date',
            getValue: (d) => d.tx.date,
            cell: (d) => ({type: 'date', value: d.tx.date}),
        },
        {
            id: 'typeIcon',
            header: () => $t('transactions.table.type'),
            type: 'enum',
            width: 90,
            sortable: true,
            filterable: true,
            urlKey: 'types',
            enumOptions: TX_TYPES.filter((tt) => mainRows.some((r) => r.type === tt)).map((tt) => ({value: tt, label: $t(`transactions.types.${tt}`) || tt, iconUrl: getTransactionTypeIconUrl(tt)})),
            getValue: (d) => d.tx.type,
            cell: (d) => {
                const label = $t(`transactions.types.${d.tx.type}`) || d.tx.type;
                const url = getTransactionTypeIconUrl(d.tx.type);
                const docUrl = getTxTypeDocUrl(d.tx.type, $locale ?? 'en');
                return {
                    type: 'custom',
                    component: TxTypeIconCell,
                    props: {iconUrl: url, label, docUrl, txId: d.tx.id},
                };
            },
        },
        {
            id: 'quantity',
            header: () => $t('transactions.table.quantity'),
            type: 'number',
            width: 110,
            getValue: (d) => Number(d.tx.quantity),
            cell: (d) => formatQty(d.tx.quantity),
        },
        {
            id: 'cash',
            header: () => $t('transactions.table.cash'),
            type: 'currency-stack',
            width: 160,
            urlKey: 'cash',
            currencyOptions: [...new Set(mainRows.filter((r) => r.cash).map((r) => r.cash!.code))].sort(),
            getValue: (d) => (d.tx.cash ? Number(d.tx.cash.amount) : 0),
            getCurrencyValue: (d) => (d.tx.cash ? {code: d.tx.cash.code, amount: Number(d.tx.cash.amount)} : null),
            cell: (d) => {
                void $currencyStoreVersion;
                if (!d.tx.cash) return '—';
                const code = d.tx.cash.code;
                const n = Number(d.tx.cash.amount);
                const inner = formatCurrencyAmountHtml(n, code, {showSign: true});
                return {
                    type: 'html',
                    html: `<span class="tx-cash-cell" data-testid="tx-cash-cell-${d.tx.id}">${inner}</span>`,
                };
            },
        },
        {
            id: 'links',
            header: () => $t('transactions.table.links') || 'Links',
            type: 'custom',
            sortable: false,
            filterable: false,
            resizable: false,
            width: 80,
            cell: (d) => {
                // `void`s here keep the cell reactive on async store loads
                // (eventTooltipText/linkedPairTooltip read currency info).
                void $currencyStoreVersion;
                void $assetStoreVersion;
                const hasEvent = d.tx.asset_event_id != null;
                const hasLink = d.tx.related_transaction_id != null;
                if (!hasEvent && !hasLink) return '';
                let eventHtml = '';
                let eventTooltip = '';
                let linkHtml = '';
                let linkTooltip = '';
                if (hasEvent) {
                    eventTooltip = eventTooltipText(d.tx.asset_event_id!);
                    eventHtml = `<button type="button" class="tx-event-dot" data-tx-event="${d.tx.id}" data-testid="tx-event-dot-${d.tx.id}" aria-label="${escapeHtml(eventTooltip)}"></button>`;
                }
                if (hasLink) {
                    // Direction arrow: giver ⬇, receiver ⬆
                    const arrow = d.pairAnchorId != null ? (d.isReceiver ? '<span class="tx-pair-arrow">⬆</span>' : '<span class="tx-pair-arrow">⬇</span>') : '';
                    linkTooltip = linkedPairTooltip(d);
                    linkHtml = `${arrow}<button type="button" class="tx-link-icon" data-tx-link="${d.tx.id}" data-testid="tx-link-icon-${d.tx.id}" aria-label="${escapeHtml(linkTooltip)}">🔗</button>`;
                }
                // CustomCell with TxLinksCell — two real Tooltip instances
                // (one per icon), each with its own text. Native `title=""`
                // is no longer used.
                return {
                    type: 'custom',
                    component: TxLinksCell,
                    props: {eventHtml, eventTooltip, linkHtml, linkTooltip},
                };
            },
        },
        {
            id: 'asset',
            header: () => $t('transactions.table.asset'),
            type: 'enum',
            width: 220,
            urlKey: 'asset_id',
            enumOptions: (() => {
                void $assetStoreVersion;
                const assetIds = new Set<number | null>();
                for (const r of mainRows) assetIds.add(r.asset_id ?? null);
                const opts: {value: string; label: string; iconUrl?: string}[] = [];
                if (assetIds.has(null)) {
                    opts.push({value: '__null__', label: $t('transactions.noAsset') || '(No asset)'});
                }
                for (const aid of assetIds) {
                    if (aid == null) continue;
                    const info = getAssetInfo(aid);
                    const name = info?.display_name ?? `#${aid}`;
                    const iconSrc = info?.icon_url ?? (info?.asset_type ? getAssetTypeIconUrl(info.asset_type) : undefined);
                    opts.push({value: String(aid), label: name, iconUrl: iconSrc ?? undefined});
                }
                return opts.sort((a, b) => {
                    if (a.value === '__null__') return -1;
                    if (b.value === '__null__') return 1;
                    return a.label.localeCompare(b.label);
                });
            })(),
            getValue: (d) => (d.tx.asset_id ? String(d.tx.asset_id) : '__null__'),
            cell: (d) => {
                void $assetStoreVersion;
                if (!d.tx.asset_id) return '—';
                const info = getAssetInfo(d.tx.asset_id);
                const name = info?.display_name ?? `#${d.tx.asset_id}`;
                // Fallback chain: icon_url → asset-type PNG → plain text
                const iconSrc = info?.icon_url ?? (info?.asset_type ? getAssetTypeIconUrl(info.asset_type) : null);
                if (iconSrc) {
                    return {type: 'image', src: iconSrc, alt: name, text: name, size: 20, circle: false};
                }
                return name;
            },
        },
        {
            id: 'broker',
            header: () => $t('transactions.table.broker'),
            type: 'enum',
            width: 160,
            urlKey: 'broker_id',
            enumOptions: brokers.map((b) => {
                const iconUrl = getBrokerIconUrl(b);
                const color = getBrokerColor(b.id, brokers);
                return {value: String(b.id), label: b.name ?? `#${b.id}`, iconUrl: iconUrl ?? undefined, dotColor: iconUrl ? undefined : color.bg};
            }),
            getValue: (d) => String(d.tx.broker_id),
            cell: (d) => {
                const name = brokerName(d.tx.broker_id);
                const iconSrc = getBrokerIconUrlById(d.tx.broker_id, brokers);
                const iconHtml = iconSrc ? `<img src="${escapeHtml(iconSrc)}" alt="" class="tx-broker-icon" onerror="this.style.display='none';this.nextElementSibling.style.display='inline-block'" /><span class="tx-broker-dot" style="display:none"></span>` : `<span class="tx-broker-dot"></span>`;
                // CustomCell — broker name shown via real Tooltip (no native HTML title).
                return {
                    type: 'custom',
                    component: TxTooltipCell,
                    props: {
                        html: `<span class="tx-broker-cell" data-testid="tx-broker-cell-${d.tx.broker_id}">${iconHtml}<span class="tx-broker-name">${escapeHtml(name)}</span></span>`,
                        tooltip: name,
                    },
                };
            },
        },
        {
            id: 'tags',
            header: () => $t('transactions.table.tags'),
            type: 'multi-enum',
            width: 200,
            urlKey: 'tags',
            enumOptions: (() => {
                const tagSet = new Set<string>();
                for (const r of mainRows) {
                    if (r.tags) for (const tag of r.tags) tagSet.add(tag);
                }
                return [...tagSet].sort().map((tag) => ({value: tag, label: tag, dotColor: getStringColor(tag).bg}));
            })(),
            getValue: (d) => (d.tx.tags ?? []).join(','),
            getMultiValue: (d) => d.tx.tags ?? [],
            cell: (d) => {
                const tags = d.tx.tags ?? [];
                if (tags.length === 0) return '—';
                const html = tags.map((tag) => `<span class="tx-tag-badge" style="${getStringBadgeStyle(tag)}">${escapeHtml(tag)}</span>`).join('');
                return {type: 'html', html: `<span class="tx-tag-list" data-testid="tx-tag-list-${d.tx.id}">${html}</span>`};
            },
        },
    ]);

    let rowActions = $derived<RowAction<DisplayRow>[]>([
        {
            id: 'view',
            icon: Eye,
            label: () => $t('transactions.actions.view') || 'View',
            onClick: (d) => onViewRow?.(d.tx),
        },
        {
            id: 'edit',
            icon: Pencil,
            label: () => $t('transactions.actions.edit') || 'Edit',
            onClick: (d) => onEditRow?.(d.tx),
        },
        {
            id: 'clone',
            icon: Copy,
            label: () => $t('transactions.actions.clone') || 'Clone',
            onClick: (d) => onCloneRow?.(d.tx),
        },
        {
            id: 'delete',
            icon: Trash2,
            label: () => $t('transactions.actions.delete') || 'Delete',
            variant: 'danger',
            onClick: (d) => onDeleteRow?.(d.tx),
        },
    ]);

    /**
     * Click delegation for inline buttons rendered by HtmlCell:
     * - `data-tx-event` → open event popover (Round 2)
     * - `data-tx-link`  → go to linked pair (scroll + pulse)
     * Type-icon navigation is now handled via native <a> tags (no delegation needed).
     */

    function handleTableClick(ev: MouseEvent) {
        const target = ev.target as HTMLElement | null;
        if (!target) return;
        const eventBtn = target.closest('[data-tx-event]') as HTMLElement | null;
        if (eventBtn) {
            ev.preventDefault();
            ev.stopPropagation();
            const id = Number(eventBtn.getAttribute('data-tx-event'));
            const tx = displayRows.find((d) => d.tx.id === id)?.tx;
            if (tx) onEventBadgeClick?.(tx);
            return;
        }
        const linkBtn = target.closest('[data-tx-link]') as HTMLElement | null;
        if (linkBtn) {
            ev.preventDefault();
            ev.stopPropagation();
            const id = Number(linkBtn.getAttribute('data-tx-link'));
            const tx = displayRows.find((d) => d.tx.id === id)?.tx;
            if (tx) onLinkedPairClick?.(tx);
            return;
        }
    }

    /** Svelte action: attach click handler in capture phase so we intercept
     *  clicks on injected HTML buttons before DataTable's <tr onclick>. */
    function captureClick(node: HTMLElement) {
        node.addEventListener('click', handleTableClick, true);
        return {
            destroy() {
                node.removeEventListener('click', handleTableClick, true);
            },
        };
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="tx-table-wrap" data-testid="tx-table" use:captureClick>
    <DataTable
        bind:this={tableRef}
        data={visibleRows}
        fullData={displayRows}
        {columns}
        {getRowId}
        storageKey="transactions-list"
        enableSelection={true}
        selectionMode="multi"
        enableActions={true}
        {rowActions}
        enablePagination={!isGrouped}
        enableColumnVisibility={true}
        enableColumnFilters={true}
        enableSorting={true}
        stickyActions={false}
        emptyMessage={$t('transactions.empty') || 'No transactions yet'}
        {getRowClass}
        {getRowStyle}
        {isRowSelectable}
        onFiltersChange={handleFiltersChangeInternal}
        onSortChange={(s) => (activeSort = s)}
        onShowSelectedOnlyChange={(v) => (showSelectedOnlyActive = v)}
        {initialFilters}
        onSelectionChange={handleSelectionChange}
        getRowDisplayName={(d) => `#${d.tx.id} ${d.tx.type}`}
    />

    {#if isGrouped && externalPaginatorTotal > 0}
        <DataTablePagination pageIndex={safePage - 1} {pageSize} totalItems={externalPaginatorTotal} pageSizeOptions={[10, 25, 50, 100, 0]} onPageChange={(idx) => onPageChange?.(idx + 1)} onPageSizeChange={(s) => onPageSizeChange?.(s)} />
    {/if}
</div>

<style>
    /* All selectors target HTML injected by DataTable's HtmlCell / row APIs;
       they are not statically visible to Svelte, hence the single :global block. */
    :global {
        /* Whole-row tint: broker color recognition.
           ── TUNE THESE VALUES to adjust row saturation ──
           Light: --broker-vivid-light (hsl hue, 60%, 80%) mixed with white.
           Dark: --broker-vivid (hsl hue, 75%, 50%) mixed with near-black. */
        .tx-table-wrap tr.tx-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 60%, white);
        }
        .dark .tx-table-wrap tr.tx-row-tinted > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 15%, #0f0f18);
        }
        .tx-table-wrap tr.tx-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid-light, transparent) 75%, white);
        }
        .dark .tx-table-wrap tr.tx-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-vivid, transparent) 22%, #0f0f18);
        }
        /* Broker cell: icon/dot + name with proper truncation when narrow. */
        .tx-table-wrap .tx-broker-cell {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            max-width: 100%;
            min-width: 0;
        }
        .tx-table-wrap .tx-broker-icon {
            width: 1rem;
            height: 1rem;
            border-radius: 3px;
            object-fit: contain;
            flex-shrink: 0;
        }
        .tx-table-wrap .tx-broker-dot {
            display: inline-block;
            width: 0.625rem;
            height: 0.625rem;
            border-radius: 9999px;
            background: var(--broker-bg, #94a3b8);
            flex-shrink: 0;
            box-shadow: 0 0 0 1px rgb(0 0 0 / 0.06);
        }
        .dark .tx-table-wrap .tx-broker-dot {
            background: var(--broker-dark-bg, #475569);
            box-shadow: 0 0 0 1px rgb(255 255 255 / 0.08);
        }
        .tx-table-wrap .tx-broker-name {
            font-size: 0.8125rem;
            color: inherit;
            min-width: 0;
            flex: 1 1 auto;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        /* Type-icon column: clickable button (opens mkdocs doc page). */
        .tx-table-wrap .tx-type-icon-link {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            margin: 0;
            background: transparent;
            border: 0;
            border-radius: 4px;
            cursor: pointer;
            line-height: 1;
            text-decoration: none;
            transition:
                transform 0.12s ease,
                background-color 0.12s ease;
        }
        .tx-table-wrap .tx-type-icon-link:hover {
            background: rgb(0 0 0 / 0.05);
            transform: translateY(-1px);
        }
        .dark .tx-table-wrap .tx-type-icon-link:hover {
            background: rgb(255 255 255 / 0.08);
        }
        .tx-table-wrap .tx-type-icon {
            width: 1.75rem;
            height: 1.75rem;
            object-fit: contain;
            pointer-events: none;
        }
        /* Cash cell: amount + symbol + flag emoji + ISO3 code. */
        .tx-table-wrap .tx-cash-cell {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.8125rem;
        }
        .tx-table-wrap .currency-amount {
            font-variant-numeric: tabular-nums;
            font-weight: 600;
            color: #1e293b;
        }
        .dark .tx-table-wrap .currency-amount {
            color: #e2e8f0;
        }
        .tx-table-wrap .currency-symbol {
            font-size: 0.75rem;
            color: #475569;
        }
        .dark .tx-table-wrap .currency-symbol {
            color: #cbd5e1;
        }
        .tx-table-wrap .tx-cash-cell .emoji-flag {
            font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;
            line-height: 1;
        }
        .tx-table-wrap .currency-code {
            font-weight: 500;
            color: #475569;
        }
        .dark .tx-table-wrap .currency-code {
            color: #e2e8f0;
        }
        /* Links column: event dot + chain icon side by side. */
        .tx-table-wrap .tx-links-cell {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0.375rem;
            width: 100%;
        }
        .tx-table-wrap .tx-event-dot {
            display: inline-block;
            width: 0.625rem;
            height: 0.625rem;
            border-radius: 9999px;
            background: rgb(139 92 246);
            border: 0;
            cursor: pointer;
            box-shadow: 0 0 0 2px rgb(139 92 246 / 0.18);
            transition: transform 0.12s ease;
        }
        .tx-table-wrap .tx-event-dot:hover {
            transform: scale(1.25);
        }
        .dark .tx-table-wrap .tx-event-dot {
            background: rgb(196 181 253);
            box-shadow: 0 0 0 2px rgb(196 181 253 / 0.22);
        }
        /* Link chain icon: clickable button for linked pair navigation. */
        .tx-table-wrap .tx-link-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.25rem;
            height: 1.25rem;
            padding: 0;
            margin: 0;
            background: transparent;
            border: 0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            line-height: 1;
            transition: transform 0.12s ease;
        }
        .tx-table-wrap .tx-link-icon:hover {
            transform: scale(1.2);
        }
        /* Tag badges: colored chips, one per tag, deterministic palette. */
        .tx-table-wrap .tx-tag-list {
            display: inline-flex;
            flex-wrap: wrap;
            gap: 0.25rem;
            align-items: center;
        }
        .tx-table-wrap .tx-tag-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.05rem 0.45rem;
            border-radius: 9999px;
            font-size: 0.6875rem;
            font-weight: 500;
            line-height: 1.4;
            background: var(--badge-bg, #e2e8f0);
            color: var(--badge-text, #334155);
            box-shadow: 0 0 0 1px color-mix(in srgb, var(--badge-text, #334155) 18%, transparent);
        }
        .dark .tx-table-wrap .tx-tag-badge {
            background: var(--badge-dark-bg, #334155);
            color: var(--badge-dark-text, #e2e8f0);
            box-shadow: 0 0 0 1px color-mix(in srgb, var(--badge-dark-text, #e2e8f0) 22%, transparent);
        }
        /* Pair direction arrows: ⬇ (giver) / ⬆ (receiver) in Links column. */
        .tx-table-wrap .tx-pair-arrow {
            font-size: 0.75rem;
            line-height: 1;
            opacity: 0.55;
            pointer-events: none;
        }
        /* Ghost rows: subtle opacity to distinguish context-only partner rows
           while keeping the broker tint uniform with other rows. */
        .tx-table-wrap tr.tx-row-ghost > td {
            opacity: 0.7;
        }
        /* Pulse highlight: applied via direct DOM classList.add('tx-row-highlight').
           Targets <td> because <tr> box-shadow is unreliable across browsers. */
        .tx-table-wrap tr.tx-row-highlight > td {
            animation: txPulse 1.4s ease-in-out 1;
        }
        @keyframes txPulse {
            0% {
                box-shadow: inset 0 0 0 0 rgb(99 102 241 / 0);
            }
            40% {
                box-shadow: inset 0 0 0 9999px rgb(99 102 241 / 0.25);
            }
            100% {
                box-shadow: inset 0 0 0 0 rgb(99 102 241 / 0);
            }
        }
    }
</style>
