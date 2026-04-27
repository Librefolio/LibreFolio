<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {Plus, Upload, Pencil, Copy, Trash2, Zap, RefreshCw} from 'lucide-svelte';

    import {zodiosApi} from '$lib/api';
    import {ensureTxTypesLoaded} from '$lib/stores/txTypeStore';
    import {ensureAssetsLoaded} from '$lib/stores/assetStore';
    import type {BrokerLike} from '$lib/utils/brokerColors';
    import type {FilterValue} from '$lib/components/table/types';
    import TransactionsTable from '$lib/components/transactions/TransactionsTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
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
        notes?: string | null;
    }

    type FilterMap = {
        broker_id?: number;
        asset_id?: number;
        types?: string[];
        date_start?: string;
        date_end?: string;
        tags?: string[];
        currency?: string;
        /** Currency-stack filter encoded as `code:min:max` items (CSV). */
        cash?: Array<{code: string; min?: number; max?: number}>;
        page?: number;
        page_size?: number;
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
        // Currency-stack: `cash=USD:0:1000,EUR::500` (min/max optional → empty token).
        const cashRaw = searchParams.get('cash');
        if (cashRaw) {
            const items: Array<{code: string; min?: number; max?: number}> = [];
            for (const s of cashRaw
                .split(',')
                .map((x) => x.trim())
                .filter(Boolean)) {
                const [code, minS, maxS] = s.split(':');
                if (!code) continue;
                const min = minS != null && minS !== '' ? Number(minS) : undefined;
                const max = maxS != null && maxS !== '' ? Number(maxS) : undefined;
                const it: {code: string; min?: number; max?: number} = {code: code.toUpperCase()};
                if (Number.isFinite(min as number)) it.min = min as number;
                if (Number.isFinite(max as number)) it.max = max as number;
                items.push(it);
            }
            if (items.length > 0) out.cash = items;
        }
        out.page = num('page');
        out.page_size = num('page_size');
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
        if (f.cash?.length) {
            params.set('cash', f.cash.map((it) => `${it.code}:${it.min ?? ''}:${it.max ?? ''}`).join(','));
        }
        if (f.page != null && f.page !== 1) params.set('page', String(f.page));
        if (f.page_size != null && f.page_size !== 50) params.set('page_size', String(f.page_size));
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

    /**
     * Build the `initialFilters` map (keyed by column `urlKey`) for the
     * DataTable header filter UI from the current `filters` state. This is
     * computed once at mount; subsequent UI changes flow back through
     * `handleColumnFiltersChange` instead.
     */
    function filtersToColumnFilters(f: FilterMap): Record<string, FilterValue> {
        const out: Record<string, FilterValue> = {};
        if (f.types?.length) out.types = {type: 'enum', selected: f.types};
        if (f.tags?.length) out.tags = {type: 'multi-enum', selected: f.tags};
        if (f.broker_id != null) out.broker_id = {type: 'enum', selected: [String(f.broker_id)]};
        if (f.asset_id != null) out.asset_id = {type: 'enum', selected: [String(f.asset_id)]};
        if (f.date_start || f.date_end) out.date = {type: 'date', from: f.date_start, to: f.date_end};
        if (f.cash?.length) out.cash = {type: 'currency-stack', items: f.cash.map((i) => ({...i}))};
        return out;
    }

    /**
     * Receive header column filter changes (keyed by `urlKey`) from the
     * DataTable and reduce them into the page-level `filters` state.
     * URL sync happens automatically via the existing `$effect` below.
     *
     * NOTE: `DataTable` emits this on every internal reactivity tick (e.g. when
     * the `columns` prop reference changes due to upstream `$derived`), even
     * if the underlying filter set didn't change. We therefore deep-compare
     * the incoming record against the current `filters` and bail out on
     * no-op emits to avoid an infinite reload loop.
     */
    function handleColumnFiltersChange(record: Record<string, FilterValue>) {
        const next: FilterMap = {...filters};
        // Reset the keys that are header-controlled so removing a filter clears it.
        next.types = undefined;
        next.tags = undefined;
        next.broker_id = undefined;
        next.asset_id = undefined;
        next.date_start = undefined;
        next.date_end = undefined;
        next.cash = undefined;
        for (const [k, v] of Object.entries(record)) {
            if (!v) continue;
            if (k === 'types' && v.type === 'enum') next.types = v.selected.length > 0 ? v.selected : undefined;
            else if (k === 'tags' && v.type === 'multi-enum') next.tags = v.selected.length > 0 ? v.selected : undefined;
            else if (k === 'broker_id' && v.type === 'enum' && v.selected.length === 1) next.broker_id = Number(v.selected[0]);
            else if (k === 'asset_id' && v.type === 'enum') next.asset_id = v.selected.length === 1 ? Number(v.selected[0]) : undefined;
            else if (k === 'date' && v.type === 'date') {
                next.date_start = v.from || undefined;
                next.date_end = v.to || undefined;
            } else if (k === 'cash' && v.type === 'currency-stack') next.cash = v.items.length > 0 ? v.items.map((i) => ({...i})) : undefined;
        }
        // Bail-out: if nothing relevant changed, skip the state update.
        // This breaks the DataTable re-emit loop triggered by upstream
        // $derived columns prop changes.
        const sameTypes = JSON.stringify(filters.types ?? null) === JSON.stringify(next.types ?? null);
        const sameTags = JSON.stringify(filters.tags ?? null) === JSON.stringify(next.tags ?? null);
        const sameBroker = (filters.broker_id ?? null) === (next.broker_id ?? null);
        const sameAsset = (filters.asset_id ?? null) === (next.asset_id ?? null);
        const sameDate = (filters.date_start ?? null) === (next.date_start ?? null) && (filters.date_end ?? null) === (next.date_end ?? null);
        const sameCash = JSON.stringify(filters.cash ?? null) === JSON.stringify(next.cash ?? null);
        if (sameTypes && sameTags && sameBroker && sameAsset && sameDate && sameCash) return;
        // Reset to first page on filter change.
        next.page = 1;
        filters = next;
        // No reload(): filtering is now 100% client-side (W28). Use the
        // explicit Refresh button to re-fetch from the backend.
    }

    // =========================================================================
    // Data loading
    // =========================================================================

    async function loadMainRows(): Promise<TXReadItem[]> {
        // Architectural decision (Round 1.2 / W28): the backend always returns
        // the full set of transactions visible to the current user. Filtering,
        // sorting and pagination happen 100% client-side via DataTable. This
        // keeps the network surface minimal and the URL filter state
        // purely presentational. No limit/offset — we pull everything.
        const res = (await zodiosApi.query_transactions_api_v1_transactions_get({} as never)) as TXReadItem[];
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
            const res = (await zodiosApi.list_brokers_api_v1_brokers_get()) as Array<{id: number; name: string; icon_url?: string | null; portal_url?: string | null; default_import_plugin?: string | null}>;
            brokers = res.map((b) => ({id: b.id, name: b.name, icon_url: b.icon_url ?? null, portal_url: b.portal_url ?? null, default_import_plugin: b.default_import_plugin ?? null}));
        } catch (e) {
            console.warn('Failed to load brokers:', e);
            brokers = [];
        }
    }

    async function loadEventTooltipMap(rows: TXReadItem[]): Promise<void> {
        const ids = [...new Set(rows.map((r) => r.asset_event_id).filter((id): id is number => id != null))];
        if (ids.length === 0) {
            eventTooltipMap = new Map();
            return;
        }
        try {
            const res = await zodiosApi.get_events_by_ids_api_v1_assets_events_get({queries: {ids}});
            const map = new Map<number, AssetEvent>();
            for (const item of res.items ?? []) {
                for (const ev of item.events ?? []) {
                    if (ev.id != null) {
                        map.set(ev.id, {
                            id: ev.id,
                            asset_id: item.asset_id,
                            type: ev.type,
                            date: ev.date,
                            value: typeof ev.value === 'object' ? ev.value.amount : String(ev.value),
                            currency: typeof ev.value === 'object' ? ev.value.code : '',
                            is_auto: ev.is_auto ?? false,
                            notes: (Array.isArray(ev.notes) ? ev.notes.join(', ') : ev.notes) ?? null,
                        });
                    }
                }
            }
            eventTooltipMap = map;
        } catch (e) {
            console.warn('Failed to load event tooltips:', e);
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
        void filters.cash;
        void filters.page;
        void filters.page_size;
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
        const hi = resp.new_from_tx_id ?? resp.new_to_tx_id;
        void reload().then(() => {
            // Pulse the new pair after data is loaded and rendered.
            if (hi != null) {
                queueMicrotask(() => {
                    const el = document.querySelector<HTMLElement>(`[data-row-id="tx-${hi}"]`);
                    if (el) {
                        el.classList.add('tx-row-highlight');
                        el.scrollIntoView({behavior: 'smooth', block: 'center'});
                        setTimeout(() => el.classList.remove('tx-row-highlight'), 1600);
                    }
                });
            }
        });
    }

    let highlightClearTimer: ReturnType<typeof setTimeout> | null = null;

    function handleLinkedPairClick(row: TXReadItem) {
        // Pulse the partner row via direct DOM manipulation.
        // We bypass the reactive prop chain (highlightId → getRowClass → DataTable)
        // because DataTable doesn't re-render rows when a closure's captured value
        // changes (same function reference). Direct DOM is reliable for visual-only
        // animations.
        if (row.related_transaction_id == null) return;
        const partnerId = row.related_transaction_id;
        if (highlightClearTimer != null) clearTimeout(highlightClearTimer);

        const el =
            document.querySelector<HTMLElement>(`[data-row-id="tx-${partnerId}"]`) ??
            document.querySelector<HTMLElement>(`[data-row-id="ghost-${partnerId}"]`);
        if (!el) return;

        // Remove class first, force reflow, then re-add → restarts CSS animation.
        el.classList.remove('tx-row-highlight');
        void el.offsetWidth;
        el.classList.add('tx-row-highlight');
        el.scrollIntoView({behavior: 'smooth', block: 'center'});

        // Auto-clear after the pulse animation finishes (1.4s + margin).
        highlightClearTimer = setTimeout(() => {
            el.classList.remove('tx-row-highlight');
            highlightClearTimer = null;
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

    function handleCloneRow(row: TXReadItem) {
        stagingMode = 'create-many';
        const today = new Date().toISOString().slice(0, 10);
        stagingInitial = [{...row, id: 0, date: today, related_transaction_id: null}];
        stagingOpen = true;
    }

    function handleDeleteRow(row: TXReadItem) {
        // Reuse the bulk-delete pipeline with a single-row selection. This
        // automatically handles the linked-pair extender modal when the row
        // has a partner.
        selectedRows = [row];
        void onBulkDelete();
    }

    function handlePageChange(page: number) {
        filters = {...filters, page};
    }

    function handlePageSizeChange(pageSize: number) {
        filters = {...filters, page_size: pageSize, page: 1};
        // No reload(): client-side pagination only (W28).
    }

    /** Reference to the TransactionsTable component for visibility/selection control. */
    let transactionsTableComponent = $state<TransactionsTable | undefined>(undefined);
</script>

<div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between flex-wrap gap-4">
        <div>
            <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
                {$_('transactions.title')}
                {#if mainRows.length > 0}
                    <span data-testid="tx-count-badge" class="text-xs font-mono px-1.5 py-0.5 rounded-full bg-libre-green/10 text-libre-green dark:bg-libre-green/20 dark:text-emerald-400">{mainRows.length}</span>
                {/if}
            </h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('transactions.subtitle')}</p>
        </div>
        <div class="flex items-center gap-2 ml-auto">
            {#if selectedRows.length > 0}
                <DataTableToolbar
                    selectedCount={selectedRows.length}
                    bulkActions={[
                        {id: 'edit', icon: Pencil, label: () => $_('transactions.actions.edit') || 'Edit', onClick: () => onEditBulk()},
                        {id: 'clone', icon: Copy, label: () => $_('transactions.actions.clone') || 'Clone', onClick: () => onCloneBulk()},
                        ...(canPromote ? [{id: 'promote', icon: Zap, label: () => $_('transactions.actions.promotePair') || 'Promote pair', onClick: () => onPromotePair()}] : []),
                        {id: 'delete', icon: Trash2, label: () => $_('transactions.actions.delete') || 'Delete', variant: 'danger', onClick: () => onBulkDelete()},
                    ]}
                    onClearSelection={() => {
                        transactionsTableComponent?.getTableRef()?.clearSelection();
                        selectedRows = [];
                    }}
                />
            {/if}
            <ColumnVisibilityToggle tableRef={transactionsTableComponent?.getTableRef()} />
            <button
                class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-all disabled:opacity-50"
                data-testid="tx-refresh-button"
                title={$_('transactions.refresh') || 'Refresh from server'}
                aria-label={$_('transactions.refresh') || 'Refresh from server'}
                disabled={loading}
                onclick={() => {
                    // Reset column filters, selection, and URL filter state before reloading.
                    transactionsTableComponent?.resetFilters();
                    transactionsTableComponent?.getTableRef()?.clearSelection();
                    selectedRows = [];
                    filters = {...filters, types: undefined, tags: undefined, broker_id: undefined, asset_id: undefined, date_start: undefined, date_end: undefined, cash: undefined, page: 1};
                    void reload();
                }}
            >
                <RefreshCw size={15} class={loading ? 'animate-spin' : ''} />
            </button>
            <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-all" data-testid="tx-import-button" onclick={onImportFromBroker}>
                <Upload size={15} />
                <span class="hidden sm:inline">{$_('transactions.import')}</span>
            </button>
            <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all" data-testid="tx-add-button" onclick={onAddTransaction}>
                <Plus size={15} />
                <span class="hidden sm:inline">{$_('transactions.addTransaction')}</span>
            </button>
        </div>
    </div>

    {#if loading}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-12 text-center border border-gray-100 dark:border-gray-700" data-testid="tx-loading">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-libre-green/10 rounded-full mb-4">
                <RefreshCw class="text-libre-green animate-spin" size={32} />
            </div>
            <p class="text-gray-500 dark:text-gray-400">{$_('common.loading')}</p>
        </div>
    {:else if error}
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4" data-testid="tx-error">
            <p class="text-red-700 dark:text-red-400 text-sm">{error}</p>
        </div>
    {:else}
        <TransactionsTable
            bind:this={transactionsTableComponent}
            {mainRows}
            {partnerRows}
            {brokers}
            {eventTooltipMap}
            currentPage={filters.page ?? 1}
            pageSize={filters.page_size ?? 50}
            initialFilters={filtersToColumnFilters(filters)}
            onSelectionChange={handleSelectionChange}
            onLinkedPairClick={handleLinkedPairClick}
            onEventBadgeClick={handleEventBadgeClick}
            onEditRow={handleEditRow}
            onCloneRow={handleCloneRow}
            onDeleteRow={handleDeleteRow}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            onFiltersChange={handleColumnFiltersChange}
        />
    {/if}
</div>

<TransactionStagingModal open={stagingOpen} mode={stagingMode} initialRows={stagingInitial} {brokers} onClose={() => (stagingOpen = false)} onCommitted={handleStagingCommitted} />
<BulkDeleteLinkedPairModal open={bulkDeleteOpen} cleanRows={bulkDeleteClean} problemRows={bulkDeleteProblems} onClose={() => (bulkDeleteOpen = false)} onCommitted={handleBulkDeleteCommitted} />
<TransferPromoteModal open={promoteOpen} rowA={promoteRowA} rowB={promoteRowB} {brokers} onClose={() => (promoteOpen = false)} onCommitted={handlePromoteCommitted} />
