<!--
  TransactionsTable.svelte — read-view of /transactions list.

  Step 5 of plan-phase07-transaction-Part4.prompt.md.

  Responsibilities:
  - Always-pair-adjacent rendering: linked TX (TRANSFER, FX_CONVERSION) are always
    rendered as adjacent rows; giver (out, qty<0 or cash<0) above, receiver (in)
    below. When the partner is filtered out of `mainRows`, it is shown as a
    "ghost row" with violet tint (taken from `partnerRows`).
  - Pair-never-split paginator: pairs are kept on the same page; if a pair would
    cross a page boundary it is pushed entirely to the next page.
  - Columns: color-band (broker), date, type-badge, asset, qty, cash, broker,
    tags, link-icon, event-icon. Selection + actions managed by DataTable.
  - GoTo / row actions are emitted via callbacks; this component does not
    perform navigation or open modals on its own.

  Pattern: Svelte 5 runes, dark mode, `data-testid` everywhere.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Calendar1, Hash, Link2 as LinkIcon, Pencil, Sparkles} from 'lucide-svelte';

    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';

    import TransactionTypeBadge from './TransactionTypeBadge.svelte';

    import {assetStoreVersion, getAssetInfo} from '$lib/stores/assetStore';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/brokerColors';

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
        /** Highlighted row id (CSS pulse). Cleared after the animation runs. */
        highlightId?: number | null;
        onSelectionChange?: (rows: TXReadItem[]) => void;
        onLinkedPairClick?: (row: TXReadItem) => void;
        onEventBadgeClick?: (row: TXReadItem) => void;
        onEditRow?: (row: TXReadItem) => void;
        onPageChange?: (page: number) => void;
    }

    let {mainRows = [], partnerRows = [], brokers = [], eventTooltipMap = new Map(), currentPage = 1, pageSize = 50, highlightId = null, onSelectionChange, onLinkedPairClick, onEventBadgeClick, onEditRow, onPageChange}: Props = $props();

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
    // Pair-never-split paginator
    // =========================================================================

    /**
     * Slice `displayRows` into pages, ensuring pairs never cross a page boundary.
     * Effective page size may be `pageSize ± 1` to preserve adjacency.
     */
    let pages = $derived.by<DisplayRow[][]>(() => {
        const result: DisplayRow[][] = [];
        let buf: DisplayRow[] = [];
        for (let i = 0; i < displayRows.length; i++) {
            const row = displayRows[i];
            const isPair = row.pairAnchorId != null;
            // Look-ahead: if adding this row would exceed pageSize and the row is
            // a giver of a pair (next row is its receiver), push the buffer first.
            const nextIsPartner = isPair && i + 1 < displayRows.length && displayRows[i + 1].pairAnchorId === row.pairAnchorId && !row.isReceiver;
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
        return `--broker-bg:${c.bg};--broker-text:${c.text};--broker-dark-bg:${c.darkBg};--broker-dark-text:${c.darkText};`;
    }

    function formatQty(q: string, isReceiver: boolean): string {
        const n = Number(q);
        if (!Number.isFinite(n) || n === 0) return '0';
        const formatted = n.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
        return (isReceiver ? '↳ ' : '') + (n > 0 ? `+${formatted}` : formatted);
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
        return `${ev.type} · ${ev.date} · ${ev.value} ${ev.currency}${ev.is_auto ? ' · auto' : ''}`;
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
        const cls: string[] = [];
        if (d.isGhost) cls.push('tx-row-ghost');
        if (d.isReceiver) cls.push('tx-row-receiver');
        if (highlightId != null && d.tx.id === highlightId) cls.push('tx-row-highlight');
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

    let columns = $derived<ColumnDef<DisplayRow>[]>([
        {
            id: 'colorBand',
            header: '',
            type: 'custom',
            sortable: false,
            filterable: false,
            resizable: false,
            width: 12,
            cell: () => ({
                type: 'html',
                html: `<span class="tx-color-band" data-testid="tx-color-band"></span>`,
            }),
        },
        {
            id: 'date',
            header: () => $t('transactions.table.date'),
            type: 'date',
            width: 110,
            getValue: (d) => d.tx.date,
            cell: (d) => ({type: 'date', value: d.tx.date}),
        },
        {
            id: 'type',
            header: () => $t('transactions.table.type'),
            type: 'enum',
            width: 130,
            getValue: (d) => d.tx.type,
            cell: (d) => ({
                type: 'custom',
                component: TransactionTypeBadge,
                props: {type: d.tx.type},
            }),
        },
        {
            id: 'asset',
            header: () => $t('transactions.table.asset'),
            type: 'text',
            width: 220,
            getValue: (d) => {
                void $assetStoreVersion;
                return d.tx.asset_id ? (getAssetInfo(d.tx.asset_id)?.display_name ?? '') : '';
            },
            cell: (d) => {
                void $assetStoreVersion;
                if (!d.tx.asset_id) return '—';
                const info = getAssetInfo(d.tx.asset_id);
                return info?.display_name ?? `#${d.tx.asset_id}`;
            },
        },
        {
            id: 'quantity',
            header: () => $t('transactions.table.quantity'),
            type: 'number',
            width: 110,
            getValue: (d) => Number(d.tx.quantity),
            cell: (d) => formatQty(d.tx.quantity, d.isReceiver),
        },
        {
            id: 'cash',
            header: () => $t('transactions.table.cash'),
            type: 'text',
            width: 150,
            getValue: (d) => (d.tx.cash ? Number(d.tx.cash.amount) : 0),
            cell: (d) => formatCash(d.tx.cash),
        },
        {
            id: 'broker',
            header: () => $t('transactions.table.broker'),
            type: 'enum',
            width: 140,
            getValue: (d) => brokerName(d.tx.broker_id),
            cell: (d) => ({
                type: 'html',
                html: `<span class="tx-broker-badge" data-testid="tx-broker-badge-${d.tx.broker_id}">${brokerName(d.tx.broker_id)}</span>`,
            }),
        },
        {
            id: 'tags',
            header: () => $t('transactions.table.tags'),
            type: 'text',
            width: 140,
            getValue: (d) => (d.tx.tags ?? []).join(','),
            cell: (d) => (d.tx.tags?.length ? d.tx.tags.join(', ') : '—'),
        },
        {
            id: 'links',
            header: '',
            type: 'custom',
            sortable: false,
            filterable: false,
            resizable: false,
            width: 80,
            cell: (d) => {
                const parts: string[] = [];
                if (d.tx.related_transaction_id != null) {
                    parts.push(`<button type="button" class="tx-link-icon" data-tx-link="${d.tx.id}" data-testid="tx-link-icon-${d.tx.id}" title="${$t('transactions.gotoLinkedPair') || 'Go to linked pair'}">🔗</button>`);
                }
                if (d.tx.asset_event_id != null) {
                    const tip = eventTooltipText(d.tx.asset_event_id);
                    parts.push(`<button type="button" class="tx-event-badge" data-tx-event="${d.tx.id}" data-testid="tx-event-badge-${d.tx.id}" title="${tip}">●evt</button>`);
                }
                if (d.isGhost) {
                    parts.push(`<span class="tx-ghost-chip" data-testid="tx-ghost-chip-${d.tx.id}" title="${$t('transactions.ghost.tooltip') || 'Linked partner shown for context'}">ghost</span>`);
                }
                return {type: 'html', html: parts.join(' ')};
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
    ]);

    /**
     * Click delegation for the inline `tx-link-icon` / `tx-event-badge` buttons
     * rendered as HtmlCell. We listen on the table's container.
     */
    function handleTableClick(ev: MouseEvent) {
        const target = ev.target as HTMLElement | null;
        if (!target) return;
        const linkBtn = target.closest('[data-tx-link]') as HTMLElement | null;
        if (linkBtn) {
            const id = Number(linkBtn.getAttribute('data-tx-link'));
            const tx = displayRows.find((d) => d.tx.id === id)?.tx;
            if (tx) onLinkedPairClick?.(tx);
            ev.stopPropagation();
            return;
        }
        const eventBtn = target.closest('[data-tx-event]') as HTMLElement | null;
        if (eventBtn) {
            const id = Number(eventBtn.getAttribute('data-tx-event'));
            const tx = displayRows.find((d) => d.tx.id === id)?.tx;
            if (tx) onEventBadgeClick?.(tx);
            ev.stopPropagation();
        }
    }

    // =========================================================================
    // Sentinel (mark unused vars to avoid lint warnings while we wire the
    // remaining steps; consumed in handleSelectionChange / icons).
    // =========================================================================

    void Calendar1;
    void Hash;
    void LinkIcon;
    void Sparkles;
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="tx-table-wrap" data-testid="tx-table" onclick={handleTableClick}>
    <DataTable
        data={visibleRows}
        {columns}
        {getRowId}
        storageKey="transactions-list"
        enableSelection={true}
        selectionMode="multi"
        enableActions={true}
        {rowActions}
        enablePagination={false}
        enableColumnFilters={true}
        enableSorting={true}
        emptyMessage={$t('transactions.empty') || 'No transactions yet'}
        {getRowClass}
        {getRowStyle}
        {isRowSelectable}
        onSelectionChange={handleSelectionChange}
        getRowDisplayName={(d) => `#${d.tx.id} ${d.tx.type}`}
    />

    {#if totalPages > 1}
        <div class="flex items-center justify-end gap-2 mt-3 text-sm text-gray-600 dark:text-gray-400" data-testid="tx-paginator">
            <button class="px-3 py-1 rounded-md border border-gray-200 dark:border-gray-700 disabled:opacity-40" disabled={safePage <= 1} onclick={() => onPageChange?.(safePage - 1)} data-testid="tx-page-prev">◂</button>
            <span data-testid="tx-page-indicator">{safePage} / {totalPages}</span>
            <button class="px-3 py-1 rounded-md border border-gray-200 dark:border-gray-700 disabled:opacity-40" disabled={safePage >= totalPages} onclick={() => onPageChange?.(safePage + 1)} data-testid="tx-page-next">▸</button>
        </div>
    {/if}
</div>

<style>
    /* All selectors target HTML injected by DataTable's HtmlCell / row APIs;
       they are not statically visible to Svelte, hence the single :global block. */
    :global {
        .tx-table-wrap .tx-color-band {
            display: block;
            width: 4px;
            height: 1.75rem;
            border-radius: 2px;
            background: var(--broker-bg, #d1d5db);
        }
        .tx-table-wrap .tx-broker-badge {
            display: inline-block;
            padding: 0.05rem 0.45rem;
            border-radius: 0.375rem;
            font-size: 0.7rem;
            font-weight: 500;
            background: var(--broker-bg, #f3f4f6);
            color: var(--broker-text, #374151);
        }
        .dark .tx-table-wrap .tx-broker-badge {
            background: var(--broker-dark-bg, #374151);
            color: var(--broker-dark-text, #d1d5db);
        }
        .tx-table-wrap tr.tx-row-ghost {
            background-color: rgb(245 243 255 / 0.6);
        }
        .dark .tx-table-wrap tr.tx-row-ghost {
            background-color: rgb(76 29 149 / 0.15);
        }
        .tx-table-wrap tr.tx-row-highlight {
            animation: txPulse 1.4s ease-in-out 1;
        }
        @keyframes txPulse {
            0% {
                box-shadow: inset 0 0 0 0 rgb(99 102 241 / 0);
            }
            40% {
                box-shadow: inset 0 0 0 9999px rgb(99 102 241 / 0.18);
            }
            100% {
                box-shadow: inset 0 0 0 0 rgb(99 102 241 / 0);
            }
        }
        .tx-table-wrap .tx-link-icon,
        .tx-table-wrap .tx-event-badge {
            cursor: pointer;
            font-size: 0.875rem;
            margin-right: 0.25rem;
            background: transparent;
            border: 0;
            padding: 0;
        }
        .tx-table-wrap .tx-event-badge {
            color: rgb(124 58 237);
            font-weight: 600;
            font-size: 0.7rem;
        }
        .tx-table-wrap .tx-ghost-chip {
            display: inline-block;
            padding: 0.05rem 0.4rem;
            border-radius: 0.375rem;
            font-size: 0.65rem;
            background: rgb(237 233 254);
            color: rgb(91 33 182);
        }
        .dark .tx-table-wrap .tx-ghost-chip {
            background: rgb(76 29 149 / 0.4);
            color: rgb(196 181 253);
        }
    }
</style>
