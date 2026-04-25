<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {Plus, Upload} from 'lucide-svelte';

    import {zodiosApi} from '$lib/api';
    import {ensureTxTypesLoaded} from '$lib/stores/txTypeStore';
    import {ensureAssetsLoaded} from '$lib/stores/assetStore';
    import type {BrokerLike} from '$lib/utils/brokerColors';
    import TransactionsTable from '$lib/components/transactions/TransactionsTable.svelte';
    import TransactionStagingModal from '$lib/components/transactions/TransactionStagingModal.svelte';
    import BulkDeleteLinkedPairModal, {type ProblemPair} from '$lib/components/transactions/BulkDeleteLinkedPairModal.svelte';
    import TransferPromoteModal from '$lib/components/transactions/TransferPromoteModal.svelte';

    // =========================================================================
    // Types (local, derived from generated.ts shapes)
    // =========================================================================

    interface TXReadItem {
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

    interface AssetEvent {
        id: number;
        asset_id: number;
        type: string;
        date: string;
        value: string;
        currency: string;
        is_auto: boolean;
    }

    type FilterMap = {
        broker_id?: number;
        asset_id?: number;
        types?: string[];
        date_start?: string;
        date_end?: string;
        tags?: string[];
        currency?: string;
        page?: number;
        page_size?: number;
        highlight_id?: number;
    };

    // =========================================================================
    // State
    // =========================================================================

    let mainRows = $state<TXReadItem[]>([]);
    let partnerRows = $state<TXReadItem[]>([]);
    let brokers = $state<BrokerLike[]>([]);
    let eventTooltipMap = $state<Map<number, AssetEvent>>(new Map());

    let loading = $state(true);
    let error = $state<string | null>(null);

    let filters = $state<FilterMap>({});
    let urlInitialized = $state(false);

    // =========================================================================
    // URL ↔ filters
    // =========================================================================

    function parseFiltersFromUrl(searchParams: URLSearchParams): FilterMap {
        const out: FilterMap = {};
        const num = (k: string) => {
            const v = searchParams.get(k);
            if (v == null || v === '') return undefined;
            const n = Number(v);
            return Number.isFinite(n) ? n : undefined;
        };
        const csv = (k: string) => {
            const v = searchParams.get(k);
            return v ? v.split(',').filter(Boolean) : undefined;
        };

        out.broker_id = num('broker_id');
        out.asset_id = num('asset_id');
        out.types = csv('types');
        out.date_start = searchParams.get('date_start') || undefined;
        out.date_end = searchParams.get('date_end') || undefined;
        out.tags = csv('tags');
        out.currency = searchParams.get('currency') || undefined;
        out.page = num('page');
        out.page_size = num('page_size');
        out.highlight_id = num('highlight_id');
        return out;
    }

    function buildFiltersUrl(f: FilterMap): string {
        const params = new URLSearchParams();
        if (f.broker_id != null) params.set('broker_id', String(f.broker_id));
        if (f.asset_id != null) params.set('asset_id', String(f.asset_id));
        if (f.types?.length) params.set('types', f.types.join(','));
        if (f.date_start) params.set('date_start', f.date_start);
        if (f.date_end) params.set('date_end', f.date_end);
        if (f.tags?.length) params.set('tags', f.tags.join(','));
        if (f.currency) params.set('currency', f.currency);
        if (f.page != null && f.page !== 1) params.set('page', String(f.page));
        if (f.page_size != null && f.page_size !== 50) params.set('page_size', String(f.page_size));
        if (f.highlight_id != null) params.set('highlight_id', String(f.highlight_id));
        const qs = params.toString();
        return qs ? `/transactions?${qs}` : '/transactions';
    }

    function syncUrl() {
        if (!browser || !urlInitialized) return;
        const next = buildFiltersUrl(filters);
        if (next !== `${$page.url.pathname}${$page.url.search}`) {
            goto(next, {replaceState: true, noScroll: true, keepFocus: true});
        }
    }

    // =========================================================================
    // Data loading
    // =========================================================================

    async function loadMainRows(): Promise<TXReadItem[]> {
        const queries: Record<string, unknown> = {
            limit: filters.page_size ?? 100,
            offset: filters.page && filters.page_size ? (filters.page - 1) * filters.page_size : 0,
        };
        if (filters.broker_id != null) queries.broker_id = filters.broker_id;
        if (filters.asset_id != null) queries.asset_id = filters.asset_id;
        if (filters.types?.length) queries.types = filters.types;
        if (filters.date_start) queries.date_start = filters.date_start;
        if (filters.date_end) queries.date_end = filters.date_end;
        if (filters.tags?.length) queries.tags = filters.tags;
        if (filters.currency) queries.currency = filters.currency;

        const res = (await zodiosApi.query_transactions_api_v1_transactions_get({queries} as never)) as TXReadItem[];
        return res ?? [];
    }

    async function loadPartnerRows(main: TXReadItem[]): Promise<TXReadItem[]> {
        const mainIds = new Set(main.map((r) => r.id));
        const missing = new Set<number>();
        for (const r of main) {
            const partner = r.related_transaction_id;
            if (partner != null && !mainIds.has(partner)) missing.add(partner);
        }
        if (missing.size === 0) return [];
        try {
            const res = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {ids: [...missing]}} as never)) as TXReadItem[];
            return res ?? [];
        } catch (e) {
            console.warn('Failed to load partner rows:', e);
            return [];
        }
    }

    async function loadBrokers(): Promise<void> {
        try {
            const res = (await zodiosApi.list_brokers_api_v1_brokers_get()) as Array<{id: number; name: string}>;
            brokers = res.map((b) => ({id: b.id, name: b.name}));
        } catch (e) {
            console.warn('Failed to load brokers:', e);
            brokers = [];
        }
    }

    async function loadEventTooltipMap(rows: TXReadItem[]): Promise<void> {
        const ids = new Set<number>();
        for (const r of rows) {
            if (r.asset_event_id != null) ids.add(r.asset_event_id);
        }
        if (ids.size === 0) {
            eventTooltipMap = new Map();
            return;
        }
        try {
            const res = (await zodiosApi.query_events_bulk_api_v1_assets_events_query_post({ids: [...ids]} as never)) as AssetEvent[] | unknown;
            const items = (res as AssetEvent[]) ?? [];
            const m = new Map<number, AssetEvent>();
            for (const ev of items) m.set(ev.id, ev);
            eventTooltipMap = m;
        } catch (e) {
            console.warn('Failed to load event tooltip map:', e);
            eventTooltipMap = new Map();
        }
    }

    async function reload(): Promise<void> {
        loading = true;
        error = null;
        try {
            // Stage 1: main filtered rows.
            const main = await loadMainRows();
            mainRows = main;

            // Stage 2: partners + tooltip + asset hydration in parallel.
            const [partner] = await Promise.all([loadPartnerRows(main), loadEventTooltipMap(main), ensureAssetsLoaded()]);
            partnerRows = partner;
        } catch (e) {
            error = e instanceof Error ? e.message : String(e);
        } finally {
            loading = false;
        }
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        if (browser) {
            filters = parseFiltersFromUrl($page.url.searchParams);
        }
        await Promise.all([ensureTxTypesLoaded(), loadBrokers()]);
        await reload();
        urlInitialized = true;
    });

    $effect(() => {
        // Touch tracked fields so Svelte runs this effect on any filter change.
        void filters.broker_id;
        void filters.asset_id;
        void filters.types;
        void filters.date_start;
        void filters.date_end;
        void filters.tags;
        void filters.currency;
        void filters.page;
        void filters.page_size;
        void filters.highlight_id;
        syncUrl();
    });

    function onAddTransaction() {
        stagingMode = 'create-many';
        stagingInitial = [];
        stagingOpen = true;
    }
    function onImportFromBroker() {
        // TODO Step 10: open BrokerImportFilesModal
        console.warn('TODO Step 10: open BrokerImportFilesModal');
    }

    // =========================================================================
    // Table interactions (Steps 5–10)
    // =========================================================================

    let selectedRows = $state<TXReadItem[]>([]);

    // Staging modal state.
    let stagingOpen = $state(false);
    let stagingMode = $state<'create-many' | 'edit-many'>('create-many');
    let stagingInitial = $state<TXReadItem[]>([]);

    function handleSelectionChange(rows: TXReadItem[]) {
        selectedRows = rows;
    }

    function onEditBulk() {
        if (selectedRows.length === 0) return;
        stagingMode = 'edit-many';
        stagingInitial = [...selectedRows];
        stagingOpen = true;
    }
    function onCloneBulk() {
        if (selectedRows.length === 0) return;
        stagingMode = 'create-many';
        const today = new Date().toISOString().slice(0, 10);
        stagingInitial = selectedRows.map((r) => ({
            ...r,
            id: 0, // ignored on create-many path (id stripped before commit)
            date: today,
            related_transaction_id: null,
        }));
        stagingOpen = true;
    }
    function handleStagingCommitted() {
        stagingOpen = false;
        void reload();
    }

    // =========================================================================
    // Bulk delete (Step 8)
    // =========================================================================

    let bulkDeleteOpen = $state(false);
    let bulkDeleteClean = $state<TXReadItem[]>([]);
    let bulkDeleteProblems = $state<ProblemPair[]>([]);

    async function onBulkDelete() {
        if (selectedRows.length === 0) return;
        const selectedIds = new Set(selectedRows.map((r) => r.id));
        const clean: TXReadItem[] = [];
        const problems: ProblemPair[] = [];
        const missingPartnerIds = new Set<number>();

        // Index of in-memory rows for partner resolution.
        const inMemory = new Map<number, TXReadItem>();
        for (const r of mainRows) inMemory.set(r.id, r);
        for (const r of partnerRows) inMemory.set(r.id, r);

        for (const r of selectedRows) {
            const partnerId = r.related_transaction_id;
            if (partnerId == null) {
                clean.push(r);
                continue;
            }
            if (selectedIds.has(partnerId)) {
                // Both halves are selected — no extender prompt needed; treat as clean.
                clean.push(r);
                continue;
            }
            const cached = inMemory.get(partnerId);
            if (cached) {
                problems.push({selected: r, partner: cached});
            } else {
                missingPartnerIds.add(partnerId);
            }
        }

        // Resolve missing partners with a single batched fetch.
        if (missingPartnerIds.size > 0) {
            try {
                const fetched = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {ids: [...missingPartnerIds]}} as never)) as TXReadItem[];
                const byId = new Map(fetched.map((r) => [r.id, r]));
                for (const r of selectedRows) {
                    const partnerId = r.related_transaction_id;
                    if (partnerId == null || selectedIds.has(partnerId)) continue;
                    if (inMemory.has(partnerId)) continue;
                    const partner = byId.get(partnerId);
                    if (partner) problems.push({selected: r, partner});
                    else clean.push(r); // Server hides the partner — let backend reject if needed.
                }
            } catch (e) {
                console.warn('Failed to resolve partner IDs for bulk delete:', e);
            }
        }

        bulkDeleteClean = clean;
        bulkDeleteProblems = problems;

        // No conflicts → skip the extender modal and confirm inline (a plain
        // ConfirmModal would be ideal, but for the MVP we open the same modal
        // with empty `problemRows` which renders a clean confirm summary).
        bulkDeleteOpen = true;
    }

    function handleBulkDeleteCommitted() {
        bulkDeleteOpen = false;
        selectedRows = [];
        void reload();
    }

    // =========================================================================
    // Promote pair (Step 9)
    // =========================================================================

    let promoteOpen = $state(false);
    let promoteRowA = $state<TXReadItem | null>(null);
    let promoteRowB = $state<TXReadItem | null>(null);

    /** True when exactly 2 rows are selected matching DEPOSIT+WITHDRAWAL with no link. */
    let canPromote = $derived.by(() => {
        if (selectedRows.length !== 2) return false;
        const types = new Set(selectedRows.map((r) => r.type));
        if (!types.has('DEPOSIT') || !types.has('WITHDRAWAL')) return false;
        return selectedRows.every((r) => r.related_transaction_id == null);
    });

    function onPromotePair() {
        if (!canPromote) return;
        promoteRowA = selectedRows[0];
        promoteRowB = selectedRows[1];
        promoteOpen = true;
    }

    function handlePromoteCommitted(resp: {new_from_tx_id?: number | null; new_to_tx_id?: number | null}) {
        promoteOpen = false;
        selectedRows = [];
        // Highlight the new pair after the list reloads.
        const hi = resp.new_from_tx_id ?? resp.new_to_tx_id;
        if (hi != null) filters = {...filters, highlight_id: hi};
        void reload();
    }

    function handleLinkedPairClick(row: TXReadItem) {
        // GoTo: scroll/pulse on the partner row.
        // The TransactionsTable already renders pairs adjacent, so we just need
        // to set the highlight_id filter and let the table react via its
        // `highlightId` prop. We also auto-clear it after the pulse animation
        // finishes so the URL doesn't carry stale highlight state.
        if (row.related_transaction_id == null) return;
        const partnerId = row.related_transaction_id;
        filters = {...filters, highlight_id: partnerId};
        // Scroll the partner row into view if rendered.
        queueMicrotask(() => {
            const el = document.querySelector<HTMLElement>(`[data-row-id="tx-${partnerId}"]`);
            if (el) el.scrollIntoView({behavior: 'smooth', block: 'center'});
        });
        // Auto-clear highlight after the pulse animation (1.4s).
        window.setTimeout(() => {
            filters = {...filters, highlight_id: undefined};
        }, 1600);
    }

    function handleEventBadgeClick(_row: TXReadItem) {
        // TODO Step 6: open popover with link to /assets/{asset_id}#events
    }

    function handleEditRow(row: TXReadItem) {
        stagingMode = 'edit-many';
        stagingInitial = [row];
        stagingOpen = true;
    }

    function handlePageChange(page: number) {
        filters = {...filters, page};
    }
</script>

<div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between flex-wrap gap-4">
        <div>
            <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200">{$_('transactions.title')}</h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('transactions.subtitle')}</p>
        </div>
        <div class="flex items-center space-x-2">
            <button class="flex items-center space-x-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-all" data-testid="tx-import-button" onclick={onImportFromBroker}>
                <Upload size={18} />
                <span>{$_('transactions.import')}</span>
            </button>
            <button class="flex items-center space-x-2 px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all" data-testid="tx-add-button" onclick={onAddTransaction}>
                <Plus size={18} />
                <span>{$_('transactions.addTransaction')}</span>
            </button>
        </div>
    </div>

    {#if loading}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-8 text-center border border-gray-100 dark:border-gray-700" data-testid="tx-loading">
            <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('common.loading')}…</p>
        </div>
    {:else if error}
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4" data-testid="tx-error">
            <p class="text-red-700 dark:text-red-400 text-sm">{error}</p>
        </div>
    {:else}
        <TransactionsTable
            {mainRows}
            {partnerRows}
            {brokers}
            {eventTooltipMap}
            currentPage={filters.page ?? 1}
            pageSize={filters.page_size ?? 50}
            highlightId={filters.highlight_id ?? null}
            onSelectionChange={handleSelectionChange}
            onLinkedPairClick={handleLinkedPairClick}
            onEventBadgeClick={handleEventBadgeClick}
            onEditRow={handleEditRow}
            onPageChange={handlePageChange}
        />
        {#if selectedRows.length > 0}
            <div class="flex items-center justify-between gap-3 p-3 rounded-lg bg-libre-green/10 dark:bg-libre-green/20 border border-libre-green/30" data-testid="tx-selection-bar">
                <span class="text-xs text-gray-700 dark:text-gray-200" data-testid="tx-selection-count">
                    {selectedRows.length} selected
                </span>
                <div class="flex items-center gap-2">
                    <button class="px-3 py-1.5 text-xs rounded bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600" onclick={onEditBulk} data-testid="tx-bulk-edit"> ✎ Edit bulk </button>
                    <button class="px-3 py-1.5 text-xs rounded bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600" onclick={onCloneBulk} data-testid="tx-bulk-clone"> 📋 Clone </button>
                    {#if canPromote}
                        <button class="px-3 py-1.5 text-xs rounded bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-900/50" onclick={onPromotePair} data-testid="tx-bulk-promote">
                            ⚡ Promote pair
                        </button>
                    {/if}
                    <button class="px-3 py-1.5 text-xs rounded bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-300 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/50" onclick={onBulkDelete} data-testid="tx-bulk-delete"> 🗑 Delete </button>
                </div>
            </div>
        {/if}
    {/if}
</div>

<TransactionStagingModal open={stagingOpen} mode={stagingMode} initialRows={stagingInitial} {brokers} onClose={() => (stagingOpen = false)} onCommitted={handleStagingCommitted} />
<BulkDeleteLinkedPairModal open={bulkDeleteOpen} cleanRows={bulkDeleteClean} problemRows={bulkDeleteProblems} onClose={() => (bulkDeleteOpen = false)} onCommitted={handleBulkDeleteCommitted} />
<TransferPromoteModal open={promoteOpen} rowA={promoteRowA} rowB={promoteRowB} {brokers} onClose={() => (promoteOpen = false)} onCommitted={handlePromoteCommitted} />
