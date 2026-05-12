<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {Plus, Upload, Pencil, Copy, Trash2, RefreshCw, Link2, Unlink} from 'lucide-svelte';

    import {zodiosApi} from '$lib/api';
    import {ensureTxTypesLoaded} from '$lib/stores/txTypeStore';
    import {ensureAssetsLoaded} from '$lib/stores/assetStore';
    import {ensureBrokersLoaded, getAllBrokers, brokerStoreVersion} from '$lib/stores/brokerStore';
    import {ensurePluginIconsLoaded} from '$lib/utils/brokerHelpers';
    import {ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';
    import {findPromoteMatch} from '$lib/stores/transactionTypeStore';
    import type {BrokerLike} from '$lib/utils/brokerColors';
    import type {FilterValue} from '$lib/components/table/types';
    import TransactionsTable from '$lib/components/transactions/TransactionsTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import TransactionFormModal from '$lib/components/transactions/TransactionFormModal.svelte';
    import TransactionBulkModal from '$lib/components/transactions/TransactionBulkModal.svelte';
    import TransactionDeleteModal from '$lib/components/transactions/TransactionDeleteModal.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import PromoteMergeModal from '$lib/components/transactions/PromoteMergeModal.svelte';
    import {getBrokerInfo, getPairedAccessLevel, canEditBroker, canEditPaired} from '$lib/stores/brokerStore';
    import {getAssetInfo, getAllAssets} from '$lib/stores/assetStore';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactionTypeStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {getBrokerIconUrlById} from '$lib/utils/brokerHelpers';
    import {getRoleSvgHtml} from '$lib/utils/brokerRoleHelpers';
    import {getBrokerRole} from '$lib/stores/brokerStore';
    import {resolveIssueMessage, type ResolverContext} from '$lib/utils/resolveValidationMessage';
    import {txStoreSetAll, txStoreGet, txStoreCanEdit} from '$lib/stores/txStore.svelte';
    import type {TXReadItem, AssetEvent} from '$lib/components/transactions/types';

    // =========================================================================
    // Types (local, derived from generated.ts shapes)
    // =========================================================================

    type FilterMap = {
        broker_id?: number;
        broker_ids?: number[];
        asset_id?: number;
        asset_ids?: number[];
        types?: string[];
        date_start?: string;
        date_end?: string;
        tags?: string[];
        currency?: string;
        /** Currency-stack filter encoded as `code:min:max` items (CSV). */
        cash?: Array<{code: string; min?: number; max?: number}>;
        /** ID range filter — min/max for the #N column. */
        id_min?: number;
        id_max?: number;
        /** Quantity range filter — min/max. */
        qty_min?: number;
        qty_max?: number;
        page?: number;
        page_size?: number;
    };

    // =========================================================================
    // State
    // =========================================================================

    let mainRows = $state<TXReadItem[]>([]);
    let partnerRows = $state<TXReadItem[]>([]);
    /** Brokers are sourced from the global `brokerStore` cache; this derived
     *  re-evaluates whenever the store version bumps (load/merge/invalidate),
     *  so icon/name edits propagate without a manual reload. */
    let brokers = $derived.by<BrokerLike[]>(() => {
        void $brokerStoreVersion;
        return getAllBrokers() as BrokerLike[];
    });
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
        // Multi-select: comma-separated IDs
        const brokerIdsRaw = csv('broker_ids');
        if (brokerIdsRaw) out.broker_ids = brokerIdsRaw.map(Number).filter(Number.isFinite);
        const assetIdsRaw = csv('asset_ids');
        if (assetIdsRaw) out.asset_ids = assetIdsRaw.map(Number).filter(Number.isFinite);
        out.types = csv('types');
        out.date_start = searchParams.get('date_start') || undefined;
        out.date_end = searchParams.get('date_end') || undefined;
        out.tags = csv('tags');
        out.currency = searchParams.get('currency') || undefined;
        out.id_min = num('id_min');
        out.id_max = num('id_max');
        out.qty_min = num('qty_min');
        out.qty_max = num('qty_max');
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
        if (f.broker_ids?.length) params.set('broker_ids', f.broker_ids.join(','));
        if (f.asset_id != null) params.set('asset_id', String(f.asset_id));
        if (f.asset_ids?.length) params.set('asset_ids', f.asset_ids.join(','));
        if (f.types?.length) params.set('types', f.types.join(','));
        if (f.date_start) params.set('date_start', f.date_start);
        if (f.date_end) params.set('date_end', f.date_end);
        if (f.tags?.length) params.set('tags', f.tags.join(','));
        if (f.currency) params.set('currency', f.currency);
        if (f.id_min != null) params.set('id_min', String(f.id_min));
        if (f.id_max != null) params.set('id_max', String(f.id_max));
        if (f.qty_min != null) params.set('qty_min', String(f.qty_min));
        if (f.qty_max != null) params.set('qty_max', String(f.qty_max));
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
        else if (f.broker_ids?.length) out.broker_id = {type: 'enum', selected: f.broker_ids.map(String)};
        if (f.asset_id != null) out.asset_id = {type: 'enum', selected: [String(f.asset_id)]};
        else if (f.asset_ids?.length) out.asset_id = {type: 'enum', selected: f.asset_ids.map(String)};
        if (f.date_start || f.date_end) out.date = {type: 'date', from: f.date_start, to: f.date_end};
        if (f.cash?.length) out.cash = {type: 'currency-stack', items: f.cash.map((i) => ({...i}))};
        if (f.id_min != null || f.id_max != null) out.id = {type: 'number', min: f.id_min, max: f.id_max};
        if (f.qty_min != null || f.qty_max != null) out.qty = {type: 'number', min: f.qty_min, max: f.qty_max};
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
        // Skip filter resets during initialization — DataTable emits an empty
        // record on first render before `initialFilters` is applied.
        if (!urlInitialized) return;
        const next: FilterMap = {...filters};
        // Reset the keys that are header-controlled so removing a filter clears it.
        next.types = undefined;
        next.tags = undefined;
        next.broker_id = undefined;
        next.broker_ids = undefined;
        next.asset_id = undefined;
        next.asset_ids = undefined;
        next.date_start = undefined;
        next.date_end = undefined;
        next.cash = undefined;
        next.id_min = undefined;
        next.id_max = undefined;
        next.qty_min = undefined;
        next.qty_max = undefined;
        for (const [k, v] of Object.entries(record)) {
            if (!v) continue;
            if (k === 'types' && v.type === 'enum') next.types = v.selected.length > 0 ? v.selected : undefined;
            else if (k === 'tags' && v.type === 'multi-enum') next.tags = v.selected.length > 0 ? v.selected : undefined;
            else if (k === 'broker_id' && v.type === 'enum') {
                if (v.selected.length === 1) {
                    next.broker_id = Number(v.selected[0]);
                    next.broker_ids = undefined;
                } else if (v.selected.length > 1) {
                    next.broker_id = undefined;
                    next.broker_ids = v.selected.map(Number);
                }
            } else if (k === 'asset_id' && v.type === 'enum') {
                if (v.selected.length === 1) {
                    next.asset_id = Number(v.selected[0]);
                    next.asset_ids = undefined;
                } else if (v.selected.length > 1) {
                    next.asset_id = undefined;
                    next.asset_ids = v.selected.map(Number);
                }
            } else if (k === 'date' && v.type === 'date') {
                next.date_start = v.from || undefined;
                next.date_end = v.to || undefined;
            } else if (k === 'cash' && v.type === 'currency-stack') next.cash = v.items.length > 0 ? v.items.map((i) => ({...i})) : undefined;
            else if (k === 'id' && v.type === 'number') {
                next.id_min = v.min;
                next.id_max = v.max;
            } else if (k === 'qty' && v.type === 'number') {
                next.qty_min = v.min;
                next.qty_max = v.max;
            }
        }
        // Bail-out: if nothing relevant changed, skip the state update.
        // This breaks the DataTable re-emit loop triggered by upstream
        // $derived columns prop changes.
        const sameTypes = JSON.stringify(filters.types ?? null) === JSON.stringify(next.types ?? null);
        const sameTags = JSON.stringify(filters.tags ?? null) === JSON.stringify(next.tags ?? null);
        const sameBroker = (filters.broker_id ?? null) === (next.broker_id ?? null) && JSON.stringify(filters.broker_ids ?? null) === JSON.stringify(next.broker_ids ?? null);
        const sameAsset = (filters.asset_id ?? null) === (next.asset_id ?? null) && JSON.stringify(filters.asset_ids ?? null) === JSON.stringify(next.asset_ids ?? null);
        const sameDate = (filters.date_start ?? null) === (next.date_start ?? null) && (filters.date_end ?? null) === (next.date_end ?? null);
        const sameCash = JSON.stringify(filters.cash ?? null) === JSON.stringify(next.cash ?? null);
        const sameId = (filters.id_min ?? null) === (next.id_min ?? null) && (filters.id_max ?? null) === (next.id_max ?? null);
        const sameQty = (filters.qty_min ?? null) === (next.qty_min ?? null) && (filters.qty_max ?? null) === (next.qty_max ?? null);
        if (sameTypes && sameTags && sameBroker && sameAsset && sameDate && sameCash && sameId && sameQty) return;
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

    // NOTE: On /transactions, loadMainRows() returns ALL user-visible transactions
    // (no server-side filtering), so partners are almost always already in mainRows.
    // This function exists for reuse on pages that DO filter server-side (e.g. broker
    // detail page showing only that broker's transactions) — there, a paired partner
    // on a different broker would be missing from the main set and needs fetching.
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
        // Sourced from the shared brokerStore cache. `ensureBrokersLoaded` is
        // a no-op after the first successful load (until invalidated); the
        // local `brokers` is a $derived snapshot reactive on $brokerStoreVersion.
        await ensureBrokersLoaded();
        // Pre-load plugin icon cache so getBrokerIconUrl can resolve
        // brokers that only have default_import_plugin (no icon_url/portal_url).
        await ensurePluginIconsLoaded();
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

    async function reload(opts?: {soft?: boolean}): Promise<void> {
        if (!opts?.soft) loading = true;
        error = null;
        try {
            // Stage 1: main filtered rows.
            const main = await loadMainRows();
            mainRows = main;

            // Stage 2: partners + tooltip + asset hydration in parallel.
            const [partner] = await Promise.all([loadPartnerRows(main), loadEventTooltipMap(main), ensureAssetsLoaded()]);
            partnerRows = partner;

            // Populate txStore (single source of truth for modals).
            txStoreSetAll(main, partner);
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
        // Hydrate currency cache so cell builders that call
        // `formatCurrencyAmountPlain/Html` (event tooltip, cash cell, link
        // tooltip) render with the proper "$ 🇺🇸 USD" format instead of the
        // bare-code fallback. `$currencyStoreVersion` is referenced inside
        // the cell builders so they re-render once data arrives.
        await Promise.all([ensureTxTypesLoaded(), loadBrokers(), ensureCurrenciesLoaded($currentLanguage)]);
        await reload();
        urlInitialized = true;
    });

    $effect(() => {
        // Touch tracked fields so Svelte runs this effect on any filter change.
        void filters.broker_id;
        void filters.broker_ids;
        void filters.asset_id;
        void filters.asset_ids;
        void filters.types;
        void filters.date_start;
        void filters.date_end;
        void filters.tags;
        void filters.currency;
        void filters.cash;
        void filters.id_min;
        void filters.id_max;
        void filters.qty_min;
        void filters.qty_max;
        void filters.page;
        void filters.page_size;
        syncUrl();
    });

    function onAddTransaction() {
        bulkIntent = {action: 'create'};
        bulkOpen = true;
    }
    function onImportFromBroker() {
        // TODO Step 10: open BrokerImportFilesModal
        console.warn('TODO Step 10: open BrokerImportFilesModal');
    }

    // =========================================================================
    // Table interactions (Steps 5–10)
    // =========================================================================

    let selectedRows = $state<TXReadItem[]>([]);

    // Form modal (single tx: create / edit / duplicate / view).
    let formOpen = $state(false);
    let formMode = $state<'create' | 'edit' | 'duplicate' | 'view'>('create');
    let formInitial = $state<TXReadItem | null>(null);

    // Bulk modal (unified batch editor on DataTable).
    let bulkOpen = $state(false);
    /** Declarative intent for BulkModal — replaces bulkInitial/autoOpenForm/initialStatus. */
    let bulkIntent = $state<import('$lib/components/transactions/TransactionBulkModal.svelte').WorkspaceIntent | undefined>(undefined);

    // B1-17: Selection-based promote (replaces PromotePairWizardModal).
    let promoteConfirmOpen = $state(false);
    let promoteTarget = $state<{targetType: string; targetLabel: string; idA: number; idB: number} | null>(null);
    let promoting = $state(false);
    let promoteMergeOpen = $state(false);
    let promoteMergeData = $state<{txA: any; txB: any; targetTypeLabel: string} | null>(null);

    // Split state
    let splitConfirmOpen = $state(false);
    let splitConfirmTx = $state<TXReadItem | null>(null);
    let splitting = $state(false);

    function handleSelectionChange(rows: TXReadItem[]) {
        selectedRows = rows;
    }

    /** Filter out rows on viewer-only brokers. Returns editable + skipped. */
    function filterEditableRows(rows: TXReadItem[]): {editable: TXReadItem[]; skipped: TXReadItem[]} {
        const editable: TXReadItem[] = [];
        const skipped: TXReadItem[] = [];
        for (const r of rows) {
            (txStoreCanEdit(r.id) ? editable : skipped).push(r);
        }
        return {editable, skipped};
    }

    /** Show toast warning for skipped viewer-only rows. Returns false if all skipped. */
    function guardViewerOnly(rows: TXReadItem[]): TXReadItem[] | null {
        const {editable, skipped} = filterEditableRows(rows);
        if (skipped.length > 0 && editable.length > 0) {
            toasts.warning($_('transactions.bulk.skippedViewerOnly', {values: {n: skipped.length}}) || `${skipped.length} transactions excluded: Editor access required`);
        }
        if (editable.length === 0) {
            toasts.error($_('transactions.bulk.allViewerOnly') || 'No editable transactions in selection');
            return null;
        }
        return editable;
    }

    function onEditBulk() {
        if (selectedRows.length === 0) return;
        const rows = guardViewerOnly(selectedRows);
        if (!rows) return;
        bulkIntent = {action: 'edit', txIds: rows.map((r) => r.id)};
        bulkOpen = true;
    }
    function onCloneBulk() {
        if (selectedRows.length === 0) return;
        bulkIntent = {action: 'clone', txIds: selectedRows.map((r) => r.id)};
        bulkOpen = true;
    }
    function handleFormCommitted() {
        formOpen = false;
        void reload({soft: true});
    }
    function handleBulkCommitted(resp: unknown) {
        bulkOpen = false;
        // B4-fix: show toast with operation summary
        const r = resp as {results?: Array<{operation: string; status: string}>};
        if (r?.results) {
            const created = r.results.filter((x) => x.operation === 'create' && x.status === 'success').length;
            const updated = r.results.filter((x) => x.operation === 'update' && x.status === 'success').length;
            const deleted = r.results.filter((x) => x.operation === 'delete' && x.status === 'success').length;
            const parts: string[] = [];
            if (created) parts.push(`${created} ${$_('transactions.toast.created') || 'created'}`);
            if (updated) parts.push(`${updated} ${$_('transactions.toast.updated') || 'updated'}`);
            if (deleted) parts.push(`${deleted} ${$_('transactions.toast.deleted') || 'deleted'}`);
            if (parts.length > 0) {
                toasts.success(`✅ ${parts.join(', ')}`);
            }
        }
        void reload({soft: true});
    }

    // =========================================================================
    // Bulk delete → reuse BulkModal with initialStatus: 'delete' (B23 Step 1-2)
    // =========================================================================

    async function onBulkDelete() {
        if (selectedRows.length === 0) return;
        const editableRows = guardViewerOnly(selectedRows);
        if (!editableRows) return;
        bulkIntent = {action: 'delete', txIds: editableRows.map((r) => r.id)};
        bulkOpen = true;
    }

    // =========================================================================
    // Promote pair wizard (Step 9 — Round 4 rewrite)
    // =========================================================================

    /**
     * True when the current selection is a compatible DEPOSIT+WITHDRAWAL pair
     * with no existing link. Used to seed the wizard slots with the selected
     * rows; otherwise the wizard opens empty and the user picks from
     * "Saved transactions" / "Create new".
     */
    // B1-17: Selection-based promote — uses server-driven promote_from metadata.
    let promoteMatch = $derived.by(() => {
        if (selectedRows.length !== 2) return null;
        const [a, b] = selectedRows;
        // Both must be unpaired DB rows
        if (a.related_transaction_id != null || b.related_transaction_id != null) return null;
        return findPromoteMatch(a.type, b.type, $_);
    });

    function onPromotePair() {
        if (selectedRows.length !== 2 || !promoteMatch) return;
        const a = selectedRows[0];
        const b = selectedRows[1];
        promoteTarget = {
            targetType: promoteMatch.targetType,
            targetLabel: promoteMatch.targetLabel,
            idA: a.id,
            idB: b.id,
        };
        // Check if fields diverge → MergeModal, else direct ConfirmModal
        const descA = a.description ?? '',
            descB = b.description ?? '';
        const tagsA = a.tags ?? [],
            tagsB = b.tags ?? [];
        const dateA = a.date,
            dateB = b.date;
        const cbA = a.cost_basis_override ?? '',
            cbB = b.cost_basis_override ?? '';
        const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB) || dateA !== dateB || cbA !== cbB;
        if (diverges) {
            promoteMergeData = {
                txA: {label: `#${a.id}`, description: descA, tags: tagsA, date: dateA, cost_basis_override: cbA},
                txB: {label: `#${b.id}`, description: descB, tags: tagsB, date: dateB, cost_basis_override: cbB},
                targetTypeLabel: promoteMatch.targetLabel,
            };
            promoteMergeOpen = true;
        } else {
            promoteConfirmOpen = true;
        }
    }

    async function confirmPromote() {
        if (!promoteTarget) return;
        // Direct commit (no merge needed — fields identical)
        await onPromoteMergeConfirm({});
    }

    async function onPromoteMergeConfirm(resolved: Record<string, unknown>) {
        if (!promoteTarget) return;
        promoting = true;
        try {
            const payload: Record<string, unknown> = {
                promotes: [{id_a: promoteTarget.idA, id_b: promoteTarget.idB, ...(Object.keys(resolved).length > 0 ? {resolved_fields: resolved} : {})}],
            };
            const resp = (await zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never)) as {committed?: boolean; issues?: unknown[]};
            if (resp?.committed) {
                promoteMergeOpen = false;
                promoteConfirmOpen = false;
                promoteTarget = null;
                promoteMergeData = null;
                selectedRows = [];
                await reload({soft: true});
            } else {
                console.error('[promote] commit failed:', resp?.issues);
            }
        } catch (e) {
            console.error('[promote]', e);
        } finally {
            promoting = false;
        }
    }

    function handleSplitRow(row: TXReadItem) {
        splitConfirmTx = row;
        splitConfirmOpen = true;
    }

    async function confirmSplit() {
        if (!splitConfirmTx) return;
        splitting = true;
        try {
            const resp = (await zodiosApi.commit_transactions_api_v1_transactions_commit_post({splits: [{id: splitConfirmTx.id}]} as never)) as {committed?: boolean; issues?: unknown[]};
            if (resp?.committed) {
                toasts.success($_('transactions.split.success') || 'Pair unlinked successfully');
                splitConfirmOpen = false;
                splitConfirmTx = null;
                selectedRows = [];
                await reload({soft: true});
            } else {
                console.error('[split] commit failed:', resp?.issues);
            }
        } catch (e) {
            console.error('[split]', e);
        } finally {
            splitting = false;
        }
    }

    let highlightClearTimer: ReturnType<typeof setTimeout> | null = null;

    function pulseElement(el: HTMLElement) {
        if (highlightClearTimer != null) clearTimeout(highlightClearTimer);
        el.classList.remove('tx-row-highlight');
        void el.offsetWidth; // force reflow → restart animation
        el.classList.add('tx-row-highlight');
        el.scrollIntoView({behavior: 'smooth', block: 'center'});
        highlightClearTimer = setTimeout(() => {
            el.classList.remove('tx-row-highlight');
            highlightClearTimer = null;
        }, 1600);
    }

    function findPartnerElement(partnerId: number): HTMLElement | null {
        return document.querySelector<HTMLElement>(`[data-row-id="tx-${partnerId}"]`) ?? document.querySelector<HTMLElement>(`[data-row-id="ghost-${partnerId}"]`);
    }

    async function handleLinkedPairClick(row: TXReadItem) {
        if (row.related_transaction_id == null) return;
        const partnerId = row.related_transaction_id;

        // Try current page first (fast path).
        let el = findPartnerElement(partnerId);
        if (el) {
            pulseElement(el);
            return;
        }

        // Partner on a different page — navigate there, then pulse.
        await transactionsTableComponent?.navigateToPartner(partnerId);

        el = findPartnerElement(partnerId);
        if (el) {
            pulseElement(el);
        }
    }

    function handleEditRow(row: TXReadItem) {
        bulkIntent = {action: 'edit', txIds: [row.id]};
        bulkOpen = true;
    }

    function handleCloneRow(row: TXReadItem) {
        bulkIntent = {action: 'clone', txIds: [row.id]};
        bulkOpen = true;
    }

    function handleViewRow(row: TXReadItem) {
        formMode = 'view';
        formInitial = row;
        formOpen = true;
    }

    /** Bug3-fix: determine if the view→edit switch should be allowed. */
    let formCanEdit = $derived.by(() => {
        const row = formInitial;
        if (!row) return true;
        if (row.related_transaction_id == null) return canEditBroker(row.broker_id);
        // Paired — check both brokers
        const partnerBid = row.partner_broker_id;
        if (partnerBid == null) return false; // partner unknown → can't edit
        return canEditPaired(row.broker_id, partnerBid);
    });

    // =========================================================================
    // Single-row delete (TransactionDeleteModal)
    // =========================================================================

    let deleteModalOpen = $state(false);
    let deleteModalTx = $state<TXReadItem | null>(null);
    let deleteModalPartner = $state<TXReadItem | null>(null);
    let deleteModalPartnerInaccessible = $state(false);
    let deleteModalPartnerBrokerName = $state('');
    let deleteModalErrors = $state<string[]>([]);
    let deleteModalErrorVariant = $state<'warning' | 'error'>('error');
    let deleteModalValidating = $state(false);
    let deleteModalValidated = $state(false);

    function handleDeleteRow(row: TXReadItem) {
        const partnerId = row.related_transaction_id;
        if (partnerId == null) {
            // Standalone → Layout A
            deleteModalTx = row;
            deleteModalPartner = null;
            deleteModalPartnerInaccessible = false;
            deleteModalPartnerBrokerName = '';
            deleteModalErrors = [];
            deleteModalOpen = true;
            return;
        }
        // Paired — try to find partner
        const partner = txStoreGet(partnerId) ?? null;
        if (!partner) {
            // Partner not found → Layout C (inaccessible)
            deleteModalTx = row;
            deleteModalPartner = null;
            deleteModalPartnerInaccessible = true;
            // Try to get broker name from link info (we can't know the broker_id)
            deleteModalPartnerBrokerName = '?';
            deleteModalOpen = true;
            return;
        }
        // Check paired access level
        const level = getPairedAccessLevel(row.broker_id, partner.broker_id);
        if (level === 'full') {
            // Layout B — paired full access
            deleteModalTx = row;
            deleteModalPartner = partner;
            deleteModalPartnerInaccessible = false;
            deleteModalPartnerBrokerName = '';
            deleteModalOpen = true;
        } else {
            // Layout C — blocked
            deleteModalTx = row;
            deleteModalPartner = partner;
            deleteModalPartnerInaccessible = true;
            const bi = getBrokerInfo(partner.broker_id);
            deleteModalPartnerBrokerName = bi?.name ?? `#${partner.broker_id}`;
            deleteModalOpen = true;
        }
    }

    /** Build resolver context for resolveIssueMessage (same shape as BulkModal). */
    function buildResolverCtx(): ResolverContext {
        const brkrs = getAllBrokers();
        return {
            brokers: brkrs as unknown as Array<{id: number; name: string}>,
            assets: getAllAssets() as unknown as Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}>,
            getBrokerIconUrl: (brokerId: number) => getBrokerIconUrlById(brokerId, brkrs as any[]),
        };
    }

    /** Build an HTML-rich broker label: icon + name + role SVG. */
    function brokerHtml(brokerId: number): string {
        const info = getBrokerInfo(brokerId);
        const name = info?.name ?? `#${brokerId}`;
        const brkrs = getAllBrokers();
        const iconUrl = getBrokerIconUrlById(brokerId, brkrs as any[]);
        const iconTag = iconUrl ? `<img src="${iconUrl}" alt="" width="14" height="14" style="display:inline;vertical-align:middle;margin-right:2px;border-radius:2px" onerror="this.style.display='none'">` : '';
        const role = getBrokerRole(brokerId);
        const roleSvg = role ? getRoleSvgHtml(role) : '';
        return `${iconTag}<strong>${name}</strong>${roleSvg ? ' ' + roleSvg : ''}`;
    }

    /** Build an HTML-rich type label: type icon + translated name. */
    function typeHtml(type: string): string {
        const iconUrl = getTransactionTypeIconUrl(type);
        const name = $_(`transactions.types.${type}`) || type;
        const iconTag = iconUrl ? `<img src="${iconUrl}" alt="" width="14" height="14" style="display:inline;vertical-align:middle;margin-right:2px" onerror="this.style.display='none'">` : '';
        return `${iconTag}${name}`;
    }

    async function confirmDeleteModal() {
        if (!deleteModalTx) return;
        deleteModalErrors = [];
        try {
            const ids = [deleteModalTx.id];
            if (deleteModalPartner && !deleteModalPartnerInaccessible) {
                ids.push(deleteModalPartner.id);
            }
            const resp = (await zodiosApi.commit_transactions_api_v1_transactions_commit_post({deletes: ids} as never)) as {committed?: boolean; issues?: Array<{error: string; code?: string; params?: Record<string, any>}>};
            if (resp?.committed) {
                // Build rich HTML toast from cached TX data
                const tx = deleteModalTx;
                const typeLabel = typeHtml(tx.type);
                const assetName = tx.asset_id ? (getAssetInfo(tx.asset_id)?.display_name ?? '') : '';
                const dateStr = tx.date;
                const brokerLabel = brokerHtml(tx.broker_id);
                const onLabel = $_('transactions.deleteModal.toastOnBroker') || 'on';
                if (deleteModalPartner) {
                    const partnerBrokerLabel = brokerHtml(deleteModalPartner.broker_id);
                    const heading = $_('transactions.deleteModal.toastDeletedPaired') || 'Pair deleted:';
                    toasts.success(
                        `<div style="display:flex;flex-direction:column;gap:2px">` +
                            `<span style="font-weight:600">${heading}</span>` +
                            `<span>${typeLabel} ${assetName}</span>` +
                            `<span style="font-size:0.8em;opacity:0.85">${brokerLabel} → ${partnerBrokerLabel}</span>` +
                            `<span style="font-size:0.75em;opacity:0.7">${dateStr}</span>` +
                            `</div>`,
                    );
                } else {
                    const heading = $_('transactions.deleteModal.toastDeletedStandalone') || 'Transaction deleted:';
                    toasts.success(
                        `<div style="display:flex;flex-direction:column;gap:2px">` +
                            `<span style="font-weight:600">${heading}</span>` +
                            `<span>${typeLabel} ${assetName ? assetName + ' ' : ''}${onLabel} ${brokerLabel}</span>` +
                            `<span style="font-size:0.75em;opacity:0.7">${dateStr}</span>` +
                            `</div>`,
                    );
                }
                deleteModalOpen = false;
                deleteModalTx = null;
                deleteModalPartner = null;
                selectedRows = [];
                void reload({soft: true});
            } else {
                // committed: false — resolve errors with resolveIssueMessage
                const ctx = buildResolverCtx();
                deleteModalErrors = (resp?.issues ?? []).map((i) => resolveIssueMessage(i, $_, ctx));
                deleteModalErrorVariant = 'error';
            }
        } catch (e) {
            console.error('[DeleteModal] failed:', e);
            deleteModalErrors = [e instanceof Error ? e.message : String(e)];
            deleteModalErrorVariant = 'error';
        }
    }

    async function validateDeleteModal() {
        if (!deleteModalTx) return;
        deleteModalValidating = true;
        deleteModalValidated = false;
        deleteModalErrors = [];
        try {
            const ids = [deleteModalTx.id];
            if (deleteModalPartner && !deleteModalPartnerInaccessible) {
                ids.push(deleteModalPartner.id);
            }
            const resp = (await zodiosApi.validate_transactions_api_v1_transactions_validate_post({deletes: ids} as never)) as {committed?: boolean; issues?: Array<{error: string; code?: string; params?: Record<string, any>}>};
            if (!resp?.issues || resp.issues.length === 0) {
                deleteModalValidated = true;
            } else {
                const ctx = buildResolverCtx();
                deleteModalErrors = (resp?.issues ?? []).map((i) => resolveIssueMessage(i, $_, ctx));
                deleteModalErrorVariant = 'warning';
            }
        } catch (e) {
            deleteModalErrors = [e instanceof Error ? e.message : String(e)];
        } finally {
            deleteModalValidating = false;
        }
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

    /** Bugfix-5 §U20: aggregated tag list for autocomplete in the form
     *  modals — sourced from the already-loaded transactions (main + partner
     *  rows) so no extra backend endpoint is required. */
    let availableTags = $derived.by<string[]>(() => {
        const seen = new Set<string>();
        for (const r of mainRows) for (const tg of r.tags ?? []) if (tg) seen.add(tg);
        for (const r of partnerRows) for (const tg of r.tags ?? []) if (tg) seen.add(tg);
        return [...seen].sort((a, b) => a.localeCompare(b));
    });
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
                        ...(promoteMatch ? [{id: 'promote', icon: Link2, label: () => `🔗 ${$_('transactions.actions.promotePair') || 'Link as pair'}`, onClick: () => onPromotePair()}] : []),
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
            onEditRow={handleEditRow}
            onCloneRow={handleCloneRow}
            onDeleteRow={handleDeleteRow}
            onViewRow={handleViewRow}
            onSplitRow={handleSplitRow}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            onFiltersChange={handleColumnFiltersChange}
        />
    {/if}
</div>

<TransactionFormModal
    open={formOpen}
    mode={formMode}
    initialRow={formInitial}
    {availableTags}
    canEdit={formCanEdit}
    onClose={() => (formOpen = false)}
    onCommitted={handleFormCommitted}
    onSwitchToEdit={() => {
        formOpen = false;
        if (formInitial) handleEditRow(formInitial);
    }}
/>
<TransactionBulkModal
    open={bulkOpen}
    intent={bulkIntent}
    {availableTags}
    onClose={() => {
        bulkOpen = false;
        bulkIntent = undefined;
    }}
    onCommitted={handleBulkCommitted}
/>
<TransactionDeleteModal
    open={deleteModalOpen}
    transaction={deleteModalTx}
    partner={deleteModalPartner}
    partnerInaccessible={deleteModalPartnerInaccessible}
    partnerBrokerName={deleteModalPartnerBrokerName}
    errors={deleteModalErrors}
    errorVariant={deleteModalErrorVariant}
    validating={deleteModalValidating}
    validated={deleteModalValidated}
    onConfirm={confirmDeleteModal}
    onValidate={validateDeleteModal}
    onCancel={() => {
        deleteModalOpen = false;
        deleteModalTx = null;
        deleteModalPartner = null;
        deleteModalErrors = [];
        deleteModalValidated = false;
        deleteModalErrorVariant = 'error';
    }}
/>
<ConfirmModal
    open={promoteConfirmOpen}
    title={`🔗 ${$_('transactions.actions.promotePair') || 'Link as pair'}`}
    message={promoteTarget ? `${selectedRows[0]?.type ?? ''} + ${selectedRows[1]?.type ?? ''} → ${promoteTarget.targetLabel}` : ''}
    confirmText={promoting ? $_('common.saving') || 'Saving...' : `🔗 ${$_('transactions.actions.promotePair') || 'Link'}`}
    cancelText={$_('common.cancel')}
    onConfirm={confirmPromote}
    onCancel={() => {
        promoteConfirmOpen = false;
        promoteTarget = null;
    }}
/>
<PromoteMergeModal
    open={promoteMergeOpen}
    txA={promoteMergeData?.txA}
    txB={promoteMergeData?.txB}
    targetTypeLabel={promoteMergeData?.targetTypeLabel ?? ''}
    onConfirm={onPromoteMergeConfirm}
    onCancel={() => {
        promoteMergeOpen = false;
        promoteMergeData = null;
    }}
/>
<ConfirmModal
    open={splitConfirmOpen}
    title={`✂️ ${$_('transactions.split.confirmTitle') || 'Unlink this pair?'}`}
    message={$_('transactions.split.confirmMessage') || 'The 2 transactions will become independent rows.'}
    confirmText={splitting ? $_('common.saving') || 'Saving...' : `✂️ ${$_('transactions.split.confirmTitle') || 'Split'}`}
    cancelText={$_('common.cancel')}
    warning
    onConfirm={confirmSplit}
    onCancel={() => {
        splitConfirmOpen = false;
        splitConfirmTx = null;
    }}
/>
