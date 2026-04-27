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
    import {Pencil, Copy, Trash2} from 'lucide-svelte';

    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTablePagination from '$lib/components/table/DataTablePagination.svelte';
    import type {ColumnDef, FilterValue, RowAction} from '$lib/components/table/types';

    import {assetStoreVersion, ensureAssetsLoaded, getAssetInfo} from '$lib/stores/assetStore';
    import {ensureCurrenciesLoaded, currencyStoreVersion} from '$lib/stores/currencyStore';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/brokerColors';
    import {getBrokerIconUrl, getBrokerIconUrlById} from '$lib/utils/brokerHelpers';
    import {getStringBadgeStyle, getStringColor} from '$lib/utils/colors';
    import {formatCurrencyAmountHtml} from '$lib/utils/currencyFormat';
    import {getTransactionTypeIconUrl, getTxTypeDocUrl, TX_TYPES} from '$lib/utils/transactionTypes';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {getEventTypeEmoji} from '$lib/utils/eventTypes';

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
        onPageChange?: (page: number) => void;
        onPageSizeChange?: (pageSize: number) => void;
        /** Bidirectional URL filter sync. When provided, header column filters
         *  are emitted (keyed by `urlKey` or column id). The parent serializes
         *  to URL query params and passes them back via `initialFilters`. */
        onFiltersChange?: (filters: Record<string, FilterValue>) => void;
        initialFilters?: Record<string, FilterValue>;
    }

    let {
        mainRows = [],
        partnerRows = [],
        brokers = [],
        eventTooltipMap = new Map(),
        currentPage = 1,
        pageSize = 50,
        onSelectionChange,
        onLinkedPairClick,
        onEventBadgeClick,
        onEditRow,
        onCloneRow,
        onDeleteRow,
        onPageChange,
        onPageSizeChange,
        onFiltersChange,
        initialFilters,
    }: Props = $props();

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
     * Build display rows with always-pair-adjacent semantics.
     *
     * Iterate `mainRows` in their natural order. For each row:
     *  - If it has a partner that hasn't been rendered yet → emit giver,
     *    then receiver. Receiver may be a ghost (if not in mainIds).
     *  - If the row is itself a receiver of a partner already rendered → skip.
     */
    let displayRows = $derived.by<DisplayRow[]>(() => {
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
    // Pair-never-split paginator
    // =========================================================================

    /**
     * Slice `filteredDisplayRows` into pages, ensuring pairs never cross a page boundary.
     * Effective page size may be `pageSize ± 1` to preserve adjacency.
     */
    let pages = $derived.by<DisplayRow[][]>(() => {
        const rows = filteredDisplayRows;
        const result: DisplayRow[][] = [];
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
    let visibleRows = $derived(pages[safePage - 1] ?? []);

    // =========================================================================
    // Helpers
    // =========================================================================

    function brokerName(brokerId: number): string {
        return brokers.find((b) => b.id === brokerId)?.name ?? `#${brokerId}`;
    }

    function brokerStyle(brokerId: number): string {
        const c = getBrokerColor(brokerId, brokers);
        // Inject CSS custom properties used by the row tint, broker badge and
        // (legacy) color band. Row tint uses --broker-bg with low alpha.
        return `--broker-bg:${c.bg};--broker-text:${c.text};--broker-dark-bg:${c.darkBg};--broker-dark-text:${c.darkText};`;
    }

    function formatQty(q: string): string {
        const n = Number(q);
        if (!Number.isFinite(n) || n === 0) return '0';
        const formatted = n.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
        const emoji = n > 0 ? ' 📈' : ' 📉';
        return `${n > 0 ? '+' : ''}${formatted}${emoji}`;
    }

    function formatCash(cash: TXReadItem['cash']): string {
        if (!cash || cash.amount === '0') return '—';
        const n = Number(cash.amount);
        if (!Number.isFinite(n)) return cash.amount;
        const sign = n > 0 ? '+' : '';
        const abs = Math.abs(n).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        return `${sign}${n < 0 ? '-' : ''}${abs} ${cash.code}`;
    }

    function eventTooltipText(eventId: number): string {
        const ev = eventTooltipMap.get(eventId);
        if (!ev) return $t('transactions.linkedEvent') || 'Linked event';
        const emoji = getEventTypeEmoji(ev.type);
        const amount = Number(ev.value);
        // Strip HTML tags from formatCurrencyAmountHtml for plain-text tooltip
        const currHtml = Number.isFinite(amount) ? formatCurrencyAmountHtml(amount, ev.currency) : `${ev.value} ${ev.currency}`;
        const currText = currHtml.replace(/<[^>]*>/g, '');
        const parts = [`${emoji} ${ev.type}`, ev.date, currText];
        if (ev.notes) parts.push(`"${ev.notes}"`);
        if (ev.is_auto) parts.push('⚙ auto');
        return parts.join(' · ');
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

        if (type === 'TRANSFER') {
            if (d.isReceiver) {
                return `📥 ${$t('transactions.linkTooltip.transferIn') || `Receiving from ${partnerBroker}`}`.replace('{broker}', partnerBroker);
            }
            return `📤 ${$t('transactions.linkTooltip.transferOut') || `Sending to ${partnerBroker}`}`.replace('{broker}', partnerBroker);
        }
        if (type === 'FX_CONVERSION') {
            const toCurr = partner?.cash?.code ?? '?';
            if (d.isReceiver) {
                return `💱 ${$t('transactions.linkTooltip.fxReceive') || `Converted from ${toCurr}`}`.replace('{currency}', toCurr);
            }
            return `💱 ${$t('transactions.linkTooltip.fxSend') || `Converting to ${toCurr}`}`.replace('{currency}', toCurr);
        }
        // Generic fallback
        return `🔗 ${$t('transactions.linkTooltip.generic') || 'Linked pair'} — ${thisBroker} ↔ ${partnerBroker}`;
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
        const set = new Set(ids);
        // Map back to TXReadItem from displayRows (giver/receiver/ghost).
        const out: TXReadItem[] = [];
        for (const d of displayRows) {
            if (set.has(getRowId(d))) out.push(d.tx);
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
                    type: 'html',
                    html: `<a href="${escapeHtml(docUrl)}" target="_blank" rel="noopener noreferrer" class="tx-type-icon-link" data-testid="tx-type-icon-${d.tx.id}" aria-label="${escapeHtml(label)}"><img src="${escapeHtml(url)}" alt="${escapeHtml(label)}" class="tx-type-icon" /></a>`,
                    tooltip: {text: label, position: 'top'},
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
                    html: `<span class="tx-cash-cell" data-testid="tx-cash-cell-${d.tx.id}" title="${escapeHtml(formatCash(d.tx.cash))}">${inner}</span>`,
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
                const hasEvent = d.tx.asset_event_id != null;
                const hasLink = d.tx.related_transaction_id != null;
                if (!hasEvent && !hasLink) return '';
                const parts: string[] = [];
                if (hasEvent) {
                    const tip = eventTooltipText(d.tx.asset_event_id!);
                    parts.push(`<button type="button" class="tx-event-dot" data-tx-event="${d.tx.id}" data-testid="tx-event-dot-${d.tx.id}" aria-label="${escapeHtml(tip)}" title="${escapeHtml(tip)}"></button>`);
                }
                if (hasLink) {
                    // Direction arrow: giver ⬇, receiver ⬆
                    const arrow = d.pairAnchorId != null ? (d.isReceiver ? '<span class="tx-pair-arrow">⬆</span>' : '<span class="tx-pair-arrow">⬇</span>') : '';
                    const linkTip = linkedPairTooltip(d);
                    parts.push(`${arrow}<button type="button" class="tx-link-icon" data-tx-link="${d.tx.id}" data-testid="tx-link-icon-${d.tx.id}" aria-label="${escapeHtml(linkTip)}" title="${escapeHtml(linkTip)}">🔗</button>`);
                }
                const tooltipText = hasEvent ? eventTooltipText(d.tx.asset_event_id!) : linkedPairTooltip(d);
                return {
                    type: 'html',
                    html: `<div class="tx-links-cell">${parts.join('')}</div>`,
                    tooltip: parts.length === 1 ? {text: tooltipText, position: 'top'} : undefined,
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
                return {
                    type: 'html',
                    html: `<span class="tx-broker-cell" data-testid="tx-broker-cell-${d.tx.broker_id}" title="${escapeHtml(name)}">${iconHtml}<span class="tx-broker-name">${escapeHtml(name)}</span></span>`,
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
        {columns}
        {getRowId}
        storageKey="transactions-list"
        enableSelection={true}
        selectionMode="multi"
        enableActions={true}
        {rowActions}
        enablePagination={false}
        enableColumnVisibility={true}
        enableColumnFilters={true}
        enableSorting={true}
        stickyActions={false}
        emptyMessage={$t('transactions.empty') || 'No transactions yet'}
        {getRowClass}
        {getRowStyle}
        {isRowSelectable}
        onFiltersChange={handleFiltersChangeInternal}
        {initialFilters}
        onSelectionChange={handleSelectionChange}
        getRowDisplayName={(d) => `#${d.tx.id} ${d.tx.type}`}
    />

    {#if filteredDisplayRows.length > 0}
        <DataTablePagination pageIndex={safePage - 1} {pageSize} totalItems={filteredDisplayRows.length} pageSizeOptions={[10, 25, 50, 100, 0]} onPageChange={(idx) => onPageChange?.(idx + 1)} onPageSizeChange={(s) => onPageSizeChange?.(s)} />
    {/if}
</div>

<style>
    /* All selectors target HTML injected by DataTable's HtmlCell / row APIs;
       they are not statically visible to Svelte, hence the single :global block. */
    :global {
        /* Whole-row tint: broker color recognition.
           ── TUNE THESE VALUES to adjust row saturation ──
           Mixed with white (light) / #1e1e2e (dark) instead of transparent.
           Dark uses --broker-bg (high lightness) at low % to get visible tint.
           Light: base 60% / hover 75%.  Dark: base 18% / hover 25%. */
        .tx-table-wrap tr.tx-row-tinted > td {
            background: color-mix(in srgb, var(--broker-bg, transparent) 60%, white);
        }
        .dark .tx-table-wrap tr.tx-row-tinted > td {
            background: color-mix(in srgb, var(--broker-bg, transparent) 18%, #1e1e2e);
        }
        .tx-table-wrap tr.tx-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-bg, transparent) 75%, white);
        }
        .dark .tx-table-wrap tr.tx-row-tinted:hover > td {
            background: color-mix(in srgb, var(--broker-bg, transparent) 25%, #1e1e2e);
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
        .tx-table-wrap .tx-cash-amount {
            font-variant-numeric: tabular-nums;
            font-weight: 500;
            color: #1e293b;
        }
        .dark .tx-table-wrap .tx-cash-amount {
            color: #e2e8f0;
        }
        .tx-table-wrap .tx-cash-symbol {
            font-size: 0.75rem;
            color: #64748b;
        }
        .dark .tx-table-wrap .tx-cash-symbol {
            color: #94a3b8;
        }
        .tx-table-wrap .tx-cash-cell .emoji-flag {
            font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;
            line-height: 1;
        }
        .tx-table-wrap .tx-cash-code {
            font-weight: 500;
            color: #475569;
        }
        .dark .tx-table-wrap .tx-cash-code {
            color: #cbd5e1;
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
