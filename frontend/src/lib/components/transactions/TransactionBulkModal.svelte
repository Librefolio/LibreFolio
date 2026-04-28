<!--
  TransactionBulkModal.svelte — Bulk create/edit editor for transactions.

  Built on top of `DataTable.svelte` with editable cells. Replaces the
  hand-rolled `<table>` of the legacy `TransactionStagingModal` and reuses the
  full DataTable ecosystem (column visibility eye-toggle, custom cells,
  navigateToRowId for issue-banner deep-links, etc).

  Modes:
  - 'create-many' → drafts seeded from `initialRows` (id stripped, link_uuid
                    regenerated for pairs) or one blank row.
  - 'edit-many'   → drafts pre-filled from `initialRows`, type+broker locked.

  Validation: 100% server-side via POST /transactions/validate. Auto-validate
  is debounced (1 s) + idle-fire (60 s) when N ≤ 50; above that threshold only
  the manual `⚡ Validate now` button works (toolbar shows ⓘ hint).

  Commit: POST /transactions/bulk (create) or PATCH (edit). On `rolled_back=true`
  the modal stays open with a persistent banner; clicking an issue scrolls to
  the offending row via `tableRef.navigateToRowId(tempId)`.

  Pair types (TRANSFER, FX_CONVERSION) are NOT selectable here — they live in
  the Promote wizard. The toolbar exposes a `⚡ Promote pair` shortcut.
-->
<script lang="ts">
    import {onDestroy, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {X, Zap} from 'lucide-svelte';

    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import BrokerSearchSelect from '$lib/components/ui/select/BrokerSearchSelect.svelte';
    import CompactCashCell from '$lib/components/ui/CompactCashCell.svelte';
    import SingleDatePicker from '$lib/components/ui/SingleDatePicker.svelte';
    import TransactionTypeSearchSelect from './TransactionTypeSearchSelect.svelte';

    import type {ColumnDef, CellContent} from '$lib/components/table/types';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/assetStore';
    import {ensureBrokersLoaded, getAllBrokers, brokerStoreVersion, type BrokerInfo} from '$lib/stores/brokerStore';
    import {ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {type TransactionTypeCode} from '$lib/utils/transactionTypes';
    import {STANDALONE_TX_TYPES, getTypeRule, isDraftReadyForValidation} from '$lib/utils/transactionTypeRules';
    import {createValidateScheduler} from '$lib/utils/useValidateScheduler.svelte';
    import {saveWithRetry, extractErrorMessage, extractValidationIssues} from '$lib/utils/saveWithRetry';
    import {generateUUID} from '$lib/utils/uuid';

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
        created_at?: string;
        updated_at?: string;
    }

    interface ValidationIssue {
        operation: 'create' | 'update' | 'delete';
        index: number;
        ref_id?: number | null;
        error: string;
    }

    type Mode = 'create-many' | 'edit-many';

    interface DraftRow {
        tempId: string; // stable id used by DataTable.getRowId + navigateToRowId
        status: 'new' | 'edited' | 'original';
        id?: number; // present in edit-many
        original?: TXReadItem;
        broker_id: number;
        asset_id: number | null;
        type: TransactionTypeCode;
        date: string;
        quantity: string;
        cash: {code: string; amount: string} | null;
        tags: string[];
        description: string;
        asset_event_id: number | null;
        cost_basis_override: string;
        link_uuid: string | null;
        created_at?: string;
        updated_at?: string;
    }

    interface Props {
        open: boolean;
        mode: Mode;
        initialRows?: TXReadItem[];
        onClose: () => void;
        onCommitted?: (resp: unknown) => void;
        /** Open the Promote wizard (passed by parent page; modal stays open). */
        onOpenPromoteWizard?: () => void;
    }

    let {open, mode, initialRows = [], onClose, onCommitted, onOpenPromoteWizard}: Props = $props();

    const AUTO_VALIDATE_THRESHOLD = 50;

    // =========================================================================
    // Helpers
    // =========================================================================

    function todayIso(): string {
        return new Date().toISOString().slice(0, 10);
    }

    function emptyDraft(): DraftRow {
        const brokers = getAllBrokers();
        // Bugfix-2 §C9: only auto-pick if exactly one broker exists.
        const defaultBroker = brokers.length === 1 ? brokers[0].id : 0;
        return {
            tempId: generateUUID(),
            status: 'new',
            broker_id: defaultBroker,
            asset_id: null,
            type: 'BUY',
            date: todayIso(),
            quantity: '0',
            cash: null,
            tags: [],
            description: '',
            asset_event_id: null,
            cost_basis_override: '',
            link_uuid: null,
        };
    }

    function fromTx(tx: TXReadItem, m: Mode): DraftRow {
        const isCreate = m === 'create-many';
        return {
            tempId: generateUUID(),
            status: isCreate ? 'new' : 'original',
            id: isCreate ? undefined : tx.id,
            original: isCreate ? undefined : tx,
            broker_id: tx.broker_id,
            asset_id: tx.asset_id ?? null,
            type: tx.type as TransactionTypeCode,
            date: isCreate ? todayIso() : tx.date,
            quantity: tx.quantity,
            cash: tx.cash ? {code: tx.cash.code, amount: tx.cash.amount} : null,
            tags: [...(tx.tags ?? [])],
            description: tx.description ?? '',
            asset_event_id: tx.asset_event_id ?? null,
            cost_basis_override: tx.cost_basis_override ?? '',
            // Regenerate link_uuid for pairs being cloned (create-many) — though
            // pair types are not editable here, BRIM/duplicate flows may seed them.
            link_uuid: isCreate && tx.related_transaction_id != null ? generateUUID() : null,
            created_at: tx.created_at,
            updated_at: tx.updated_at,
        };
    }

    // =========================================================================
    // State
    // =========================================================================

    let drafts = $state<DraftRow[]>([]);
    let issues = $state<ValidationIssue[]>([]);
    let formError = $state<string | null>(null);
    let committing = $state(false);
    let tableRef = $state<DataTable<DraftRow> | undefined>(undefined);
    /** Snapshot of `drafts` at modal-open time, used to detect unsaved changes
     *  for the close-confirmation guard (Bugfix-3 §C11). */
    let initialDraftsKey = $state('');
    let confirmCloseOpen = $state(false);

    // Reset on open — compute `next` locally first, then assign once (avoids
    // [[problems/svelte5-effect-read-write-loop]]).
    $effect(() => {
        if (!open) return;
        const m = mode;
        const rows = initialRows;
        untrack(() => {
            issues = [];
            formError = null;
            confirmCloseOpen = false;
            const next: DraftRow[] = rows.length > 0 ? rows.map((r) => fromTx(r, m)) : m === 'create-many' ? [emptyDraft()] : [];
            drafts = next;
            initialDraftsKey = serializeDrafts(next);
        });
        void (async () => {
            await Promise.all([ensureBrokersLoaded(), ensureCurrenciesLoaded($currentLanguage), ensureAssetsLoaded()]);
        })();
    });

    /** Stable, comparison-friendly serialization of the drafts array (drops
     *  the volatile `tempId` so newly seeded rows compare equal to the
     *  original snapshot). */
    function serializeDrafts(rows: DraftRow[]): string {
        return JSON.stringify(
            rows.map((d) => {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const {tempId: _tempId, original: _original, status: _status, ...rest} = d;
                return rest;
            }),
        );
    }

    function hasUnsavedChanges(): boolean {
        return serializeDrafts(drafts) !== initialDraftsKey;
    }

    function requestClose() {
        if (committing) return;
        if (hasUnsavedChanges()) {
            confirmCloseOpen = true;
            return;
        }
        onClose();
    }

    function confirmDiscardAndClose() {
        confirmCloseOpen = false;
        onClose();
    }

    let brokers = $derived.by<BrokerInfo[]>(() => {
        void $brokerStoreVersion;
        return getAllBrokers();
    });

    // =========================================================================
    // Mutators (always emit a new array reference for reactivity)
    // =========================================================================

    function patchDraft(tempId: string, patch: Partial<DraftRow>) {
        drafts = drafts.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d, ...patch};
            // Type-rule enforcement: if `type` changed, clear values that
            // are now forbidden (Bugfix-1 §C3) so the backend doesn't receive
            // stale data hidden by the UI.
            if (patch.type && patch.type !== d.type) {
                const r = getTypeRule(merged.type);
                if (r.assetField === 'forbidden') merged.asset_id = null;
                if (r.cashField === 'forbidden') merged.cash = null;
                if (r.quantityRule === 'zero') merged.quantity = '0';
                if (!r.eventLinkable) merged.asset_event_id = null;
                if (merged.type !== 'TRANSFER') merged.cost_basis_override = '';
            }
            if (merged.status === 'original') merged.status = 'edited';
            return merged;
        });
    }

    function addRow() {
        // Bugfix-4 §A3: kept for future create-many flows but currently unused
        // (toolbar entry removed). Reference via `void` to keep tree-shaking
        // from complaining about an exported helper.
        drafts = [...drafts, emptyDraft()];
    }
    void addRow;

    function removeRow(tempId: string) {
        drafts = drafts.filter((d) => d.tempId !== tempId);
    }

    function resetRow(tempId: string) {
        drafts = drafts.map((d) => {
            if (d.tempId !== tempId || !d.original) return d;
            return fromTx(d.original, mode);
        });
    }

    function resetAll() {
        if (mode !== 'edit-many') return;
        drafts = drafts.map((d) => (d.original ? fromTx(d.original, mode) : d));
    }

    // =========================================================================
    // Sanitizers
    // =========================================================================

    function collectCreate(d: DraftRow): Record<string, unknown> {
        const rule = getTypeRule(d.type);
        const out: Record<string, unknown> = {
            broker_id: d.broker_id,
            type: d.type,
            date: d.date,
            quantity: d.quantity,
        };
        if (d.asset_id != null && rule.assetField !== 'forbidden') out.asset_id = d.asset_id;
        if (d.cash && rule.cashField !== 'forbidden') out.cash = d.cash;
        if (d.tags.length > 0) out.tags = d.tags;
        if (d.description.trim()) out.description = d.description.trim();
        if (d.asset_event_id != null && rule.eventLinkable) out.asset_event_id = d.asset_event_id;
        if (d.cost_basis_override.trim()) out.cost_basis_override = d.cost_basis_override.trim();
        if (d.link_uuid && rule.requiresPair) out.link_uuid = d.link_uuid;
        return out;
    }

    function collectUpdate(d: DraftRow): Record<string, unknown> | null {
        if (!d.original || d.id == null) return null;
        const out: Record<string, unknown> = {id: d.id};
        const orig = d.original;
        if (d.date !== orig.date) out.date = d.date;
        if (d.quantity !== orig.quantity) out.quantity = d.quantity;
        if (JSON.stringify(d.cash ?? null) !== JSON.stringify(orig.cash ?? null)) out.cash = d.cash ?? null;
        if (JSON.stringify(d.tags) !== JSON.stringify(orig.tags ?? [])) out.tags = d.tags;
        if ((d.description || null) !== (orig.description ?? null)) out.description = d.description || null;
        if ((d.cost_basis_override || null) !== (orig.cost_basis_override ?? null)) out.cost_basis_override = d.cost_basis_override || null;
        const origEvent = orig.asset_event_id ?? null;
        if (origEvent !== d.asset_event_id) out.asset_event_id = d.asset_event_id ?? 0;
        return out;
    }

    function collectAllUpdates(): Record<string, unknown>[] {
        const out: Record<string, unknown>[] = [];
        for (const d of drafts) {
            if (d.status !== 'edited') continue;
            const upd = collectUpdate(d);
            if (upd && Object.keys(upd).length > 1) out.push(upd);
        }
        return out;
    }

    // =========================================================================
    // Validate scheduler
    // =========================================================================

    const scheduler = createValidateScheduler({
        enabled: () => drafts.length > 0 && drafts.length <= AUTO_VALIDATE_THRESHOLD && drafts.some(isDraftReadyForValidation),
        validateFn: async () => {
            if (drafts.length === 0) {
                issues = [];
                lastValidatedDraftKey = lastDraftKey;
                issuesDismissed = false;
                return {issuesCount: 0};
            }
            const payload = mode === 'edit-many' ? {updates: collectAllUpdates()} : {creates: drafts.map(collectCreate)};
            // Snapshot the key at the moment we *send* the payload — so when
            // the response comes back we know whether the drafts have drifted.
            const sentKey = lastDraftKey;
            try {
                const res = (await zodiosApi.validate_transactions_api_v1_transactions_validate_post(payload as never)) as {issues?: ValidationIssue[]};
                issues = res?.issues ?? [];
                lastValidatedDraftKey = sentKey;
                issuesDismissed = false;
                return {issuesCount: issues.length};
            } catch (e) {
                // Pydantic 422 → expand into per-row issues so the banner is actionable.
                const extracted = extractValidationIssues(e);
                if (extracted.length > 0) {
                    issues = extracted.map((iss) => {
                        // Try to recover the row index from loc: body.{creates|updates}.<idx>.<field?>
                        const parts = iss.loc.split('.');
                        let idx = 0;
                        for (let i = 0; i < parts.length; i++) {
                            if (/^\d+$/.test(parts[i])) {
                                idx = Number(parts[i]);
                                break;
                            }
                        }
                        return {operation: mode === 'edit-many' ? 'update' : 'create', index: idx, error: iss.msg};
                    });
                } else {
                    issues = [{operation: mode === 'edit-many' ? 'update' : 'create', index: 0, error: extractErrorMessage(e, $t('transactions.bulk.saveFailed'))}];
                }
                lastValidatedDraftKey = sentKey;
                issuesDismissed = false;
                return {issuesCount: issues.length};
            }
        },
    });

    onDestroy(() => scheduler.dispose());

    let lastDraftKey = $state('');
    /** Bugfix-4 §U16: track which draft state we last validated, so the UI
     *  can show a "fresh" valid banner only when no edits happened since. */
    let lastValidatedDraftKey = $state('');
    /** User-dismissed flag for the issues banner; reset on every new validate. */
    let issuesDismissed = $state(false);

    let isFreshlyValid = $derived(scheduler.state.lastValidatedAt != null && issues.length === 0 && lastValidatedDraftKey === lastDraftKey && lastDraftKey !== '');
    let showIssuesBanner = $derived(issues.length > 0 && !issuesDismissed);

    $effect(() => {
        if (!open) return;
        const key = JSON.stringify(drafts);
        if (key === lastDraftKey) return;
        lastDraftKey = key;
        scheduler.trigger('change');
    });

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        if (committing) return;
        committing = true;
        formError = null;
        try {
            if (mode === 'edit-many') {
                const items = collectAllUpdates();
                if (items.length === 0) {
                    onClose();
                    return;
                }
                const result = await saveWithRetry(() => zodiosApi.update_transactions_bulk_api_v1_transactions_bulk_patch(items as never), {fallback: $t('transactions.bulk.saveFailed'), toast: false});
                if (result.status === 'error') {
                    formError = result.message;
                    return;
                }
                const resp = result.data as {rolled_back?: boolean; errors?: string[]};
                if (resp.rolled_back) {
                    formError = (resp.errors?.[0] ?? $t('transactions.bulk.rolledBack')) as string;
                    // Re-run validate to surface per-row issues that match.
                    scheduler.trigger('manual');
                    return;
                }
                onCommitted?.(resp);
                onClose();
            } else {
                const items = drafts.map(collectCreate);
                const result = await saveWithRetry(() => zodiosApi.create_transactions_bulk_api_v1_transactions_bulk_post(items as never), {fallback: $t('transactions.bulk.saveFailed'), toast: false});
                if (result.status === 'error') {
                    formError = result.message;
                    return;
                }
                const resp = result.data as {rolled_back?: boolean; errors?: string[]};
                if (resp.rolled_back) {
                    formError = (resp.errors?.[0] ?? $t('transactions.bulk.rolledBack')) as string;
                    scheduler.trigger('manual');
                    return;
                }
                onCommitted?.(resp);
                onClose();
            }
        } finally {
            committing = false;
        }
    }

    // =========================================================================
    // Columns
    // =========================================================================

    // TYPE_OPTIONS removed in Bugfix-2 §C6 — type column now uses
    // TransactionTypeSearchSelect (PNG icons + i18n labels).

    // Bugfix-3 §C10: BrokerSearchSelect expects `{id, name, icon_url, ...}`
    // items. The brokerStore's BrokerInfo is structurally compatible but TS
    // can't widen via the prop attribute, so we cast in script (parser-friendly).
    let brokersForCellSelect = $derived(brokers as unknown as Array<{id: number; name: string; icon_url?: string | null; portal_url?: string | null; default_import_plugin?: string | null}>);

    const editMode = $derived(mode === 'edit-many');

    let columns = $derived.by<ColumnDef<DraftRow>[]>(() => {
        const isEdit = editMode;
        return [
            {
                id: 'status',
                header: () => $t('transactions.bulk.status'),
                type: 'text',
                width: 70,
                sortable: false,
                filterable: false,
                // Bugfix-3 §U14: hidden by default — operations are atomic and
                // independent so the new/edit badge is rarely actionable.
                hiddenByDefault: true,
                cell: (row): CellContent => ({
                    type: 'html',
                    html: row.status === 'new' ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">new</span>' : row.status === 'edited' ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">edit</span>' : '<span class="text-gray-300 dark:text-gray-600">·</span>',
                }),
            },
            {
                id: 'id',
                header: 'ID',
                type: 'text',
                width: 70,
                sortable: false,
                filterable: false,
                hiddenByDefault: !isEdit,
                cell: (row): CellContent => ({type: 'html', html: row.id != null ? `#${row.id}` : '—'}),
            },
            {
                id: 'date',
                header: () => $t('transactions.table.date'),
                type: 'custom',
                width: 160,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => ({
                    type: 'custom',
                    component: SingleDatePicker,
                    props: {
                        value: row.date,
                        label: '',
                        // Bugfix-3 §U13: render the date trigger as an input-style
                        // control matching SearchSelect height (px-3 py-2 text-sm).
                        inputStyle: true,
                        onchange: (d: string) => patchDraft(row.tempId, {date: d}),
                    },
                }),
            },
            {
                id: 'type',
                header: () => $t('transactions.table.type'),
                type: 'custom',
                width: 170,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    if (isEdit) {
                        // Edit-many: type is immutable per business rule. Render the badge readonly.
                        const label = $t(`transactions.types.${row.type}`) || row.type;
                        return {type: 'html', html: `<span class="inline-flex items-center gap-1 text-xs"><img src="/icons/transactions/${row.type.toLowerCase().replace('_', '-')}.png" alt="" class="w-4 h-4 object-contain shrink-0" onerror="this.style.display='none'"/>${label}</span>`};
                    }
                    return {
                        type: 'custom',
                        component: TransactionTypeSearchSelect,
                        props: {
                            value: row.type,
                            compact: true,
                            onchange: (v: TransactionTypeCode) => patchDraft(row.tempId, {type: v}),
                            testid: `tx-bulk-type-${row.tempId}`,
                        },
                    };
                },
            },
            {
                id: 'asset',
                header: () => $t('transactions.table.asset'),
                type: 'custom',
                width: 200,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => ({
                    type: 'custom',
                    component: AssetSelect,
                    props: {
                        value: row.asset_id,
                        compact: true,
                        disabled: getTypeRule(row.type).assetField === 'forbidden',
                        onchange: (v: number | null) => patchDraft(row.tempId, {asset_id: v}),
                        testid: `tx-bulk-asset-${row.tempId}`,
                    },
                }),
            },
            {
                id: 'quantity',
                header: () => $t('transactions.table.quantity'),
                type: 'number',
                width: 110,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    // Type-rule gating (Bugfix-1 §C3 + Bugfix-2 §U10): when
                    // quantity must be 0 (DEPOSIT/WITHDRAWAL/DIVIDEND/INTEREST
                    // /FEE/TAX/ADJUSTMENT…), render a readonly `n/a` italic
                    // placeholder so the user can clearly see the field is
                    // not applicable to the current type.
                    if (getTypeRule(row.type).quantityRule === 'zero') {
                        return {type: 'html', html: '<span class="text-gray-400 italic" title="Not applicable: quantity must be 0 for this transaction type">n/a</span>'};
                    }
                    return {
                        type: 'editable-text',
                        value: row.quantity,
                        onchange: (v) => patchDraft(row.tempId, {quantity: v}),
                    };
                },
            },
            {
                id: 'cash',
                header: () => $t('transactions.table.cash'),
                type: 'custom',
                width: 220,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => ({
                    type: 'custom',
                    component: CompactCashCell,
                    props: {
                        value: row.cash,
                        signHint: getTypeRule(row.type).cashSign,
                        disabled: getTypeRule(row.type).cashField === 'forbidden',
                        defaultCode: (row.asset_id != null && getAssetInfo(row.asset_id)?.currency) || 'EUR',
                        onChange: (v: {amount: string; code: string} | null) => patchDraft(row.tempId, {cash: v}),
                        testid: `tx-bulk-cash-${row.tempId}`,
                    },
                }),
            },
            {
                id: 'broker',
                header: () => $t('transactions.table.broker'),
                type: 'custom',
                width: 200,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    if (isEdit) {
                        const b = brokers.find((x) => x.id === row.broker_id);
                        return {type: 'html', html: b?.name ?? '—'};
                    }
                    // Bugfix-3 §C10: BrokerSearchSelect (search + logo) instead
                    // of a plain editable-select to stay consistent with the
                    // rest of the app (FormModal, wizard, BRIM editor).
                    return {
                        type: 'custom',
                        component: BrokerSearchSelect,
                        props: {
                            brokers: brokersForCellSelect,
                            value: row.broker_id || null,
                            placeholder: $t('uploads.selectBroker'),
                            onchange: (id: number | null) => patchDraft(row.tempId, {broker_id: id ?? 0}),
                        },
                    };
                },
            },
            {
                id: 'description',
                header: () => $t('transactions.form.description'),
                type: 'text',
                width: 200,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({
                    type: 'editable-text',
                    value: row.description,
                    maxLength: 500,
                    onchange: (v) => patchDraft(row.tempId, {description: v}),
                }),
            },
            {
                id: 'cost_basis_override',
                header: () => $t('transactions.form.costBasis'),
                type: 'text',
                width: 130,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({
                    type: 'editable-text',
                    value: row.cost_basis_override,
                    placeholder: 'auto',
                    onchange: (v) => patchDraft(row.tempId, {cost_basis_override: v}),
                }),
            },
            {
                id: 'asset_event_id',
                header: () => $t('transactions.form.assetEvent'),
                type: 'number',
                width: 110,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({
                    type: 'editable-number',
                    value: row.asset_event_id,
                    placeholder: 'event id',
                    onchange: (v) => patchDraft(row.tempId, {asset_event_id: v}),
                }),
            },
            {
                id: 'link_uuid',
                header: () => $t('transactions.form.linkUuid'),
                type: 'text',
                width: 140,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({type: 'html', html: row.link_uuid ? `<code class="text-[10px] font-mono text-gray-400">${row.link_uuid.slice(0, 8)}…</code>` : '—'}),
            },
            {
                id: 'created_at',
                header: () => $t('common.created'),
                type: 'date',
                width: 160,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({type: 'html', html: row.created_at ?? '—'}),
            },
            {
                id: 'updated_at',
                header: () => $t('common.updated'),
                type: 'date',
                width: 160,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({type: 'html', html: row.updated_at ?? '—'}),
            },
        ] satisfies ColumnDef<DraftRow>[];
    });

    // =========================================================================
    // Row actions (remove / reset)
    // =========================================================================

    let rowActions = $derived(
        editMode
            ? [
                  {
                      id: 'reset',
                      icon: () => '↺',
                      label: () => $t('transactions.bulk.resetRow'),
                      onClick: (row: DraftRow) => resetRow(row.tempId),
                      visible: (row: DraftRow) => !!row.original,
                  },
              ]
            : [
                  {
                      id: 'remove',
                      icon: X,
                      label: () => $t('transactions.bulk.removeRow'),
                      onClick: (row: DraftRow) => removeRow(row.tempId),
                      variant: 'danger' as const,
                  },
              ],
    );

    // =========================================================================
    // Issue → row navigation
    // =========================================================================

    function jumpToIssue(issue: ValidationIssue) {
        const draft = drafts[issue.index];
        if (!draft) return;
        tableRef?.navigateToRowId(draft.tempId);
    }

    // =========================================================================
    // Toolbar chips
    // =========================================================================

    // Bugfix-4 §U16: validate chip removed — banners are the single source
    // of truth. Footer keeps only an inline "Validating…" indicator.


    let editedCount = $derived(drafts.filter((d) => d.status === 'edited' || d.status === 'new').length);
    let commitDisabled = $derived(committing || drafts.length === 0 || (mode === 'edit-many' && editedCount === 0));
    let commitLabel = $derived(committing ? $t('common.saving') : mode === 'create-many' ? $t('transactions.bulk.commitCreate', {values: {n: drafts.length}}) : $t('transactions.bulk.commitEdit', {values: {n: editedCount}}));

    // Cast to `never` is required because DataTable<T> is generic and Svelte 5
    // template attribute type-checking can't refine through the bind:this ref.
    // Doing this in script keeps the template free of `as` casts (parser-friendly).
    let tableRefForToggle = $derived(tableRef as never);
    let rowActionsForTable = $derived(rowActions as never);
</script>

<ModalBase {open} maxWidth="none" onRequestClose={requestClose} testId="tx-bulk-modal" allowOverflow={true} contentClass="max-w-[95vw] w-[95vw]">
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="tx-bulk-modal-root">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-bulk-title">
                {#if mode === 'create-many'}
                    ➕ {$t('transactions.bulk.titleCreate')} <span class="text-sm font-normal text-gray-500 dark:text-gray-400">· {drafts.length}</span>
                {:else}
                    ✎ {$t('transactions.bulk.titleEdit')} <span class="text-sm font-normal text-gray-500 dark:text-gray-400">· {editedCount}/{drafts.length}</span>
                {/if}
            </h2>
            <button class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" onclick={requestClose} data-testid="tx-bulk-close" aria-label="Close">
                <X size={20} />
            </button>
        </div>

        <!-- Banners -->
        <div class="px-5 pt-3 space-y-2 shrink-0">
            {#if formError}
                <InfoBanner variant="error">
                    <p class="font-semibold mb-1" data-testid="tx-bulk-error">⛔ {$t('transactions.bulk.rolledBackTitle')}</p>
                    <p>{formError}</p>
                </InfoBanner>
            {/if}
            {#if isFreshlyValid && !formError}
                <!-- Bugfix-4 §U16: green "all valid" banner; auto-dismisses on
                     the next edit (because lastValidatedDraftKey ≠ lastDraftKey). -->
                <InfoBanner variant="success">
                    <p data-testid="tx-bulk-valid">✓ {$t('transactions.validate.ok')}</p>
                </InfoBanner>
            {/if}
            {#if showIssuesBanner && !formError}
                <InfoBanner variant="warning" dismissible ondismiss={() => (issuesDismissed = true)}>
                    <ul class="space-y-0.5" data-testid="tx-bulk-issues">
                        {#each issues as issue}
                            <li>
                                <button type="button" class="underline hover:opacity-80" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue">
                                    {$t('transactions.bulk.rowN', {values: {n: issue.index + 1}})}: {issue.error}
                                </button>
                            </li>
                        {/each}
                    </ul>
                </InfoBanner>
            {/if}
            {#if drafts.length > AUTO_VALIDATE_THRESHOLD}
                <InfoBanner variant="info">
                    <p data-testid="tx-bulk-auto-off">ⓘ {$t('transactions.validate.autoOff', {values: {n: drafts.length, threshold: AUTO_VALIDATE_THRESHOLD}})}</p>
                </InfoBanner>
            {/if}
        </div>

        <!-- Toolbar (Bugfix-2 §U9: action buttons right-aligned, most important first
             from the right via flex-row-reverse).
             Bugfix-4 §A3: `+ Add row` removed — single-row create now goes
             through TransactionFormModal. BulkModal toolbar serves edit-many
             multi-select flows only. -->
        <div class="flex items-center gap-2 px-5 py-3 border-b border-gray-100 dark:border-slate-800 text-xs shrink-0">
            <div class="ml-auto flex flex-row-reverse items-center gap-2 flex-wrap">
                {#if mode === 'edit-many'}
                    <button type="button" class="px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={resetAll} data-testid="tx-bulk-reset-all">{$t('transactions.bulk.resetAll')}</button>
                {/if}
                <ColumnVisibilityToggle tableRef={tableRefForToggle} />
                {#if onOpenPromoteWizard}
                    <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20" onclick={onOpenPromoteWizard} data-testid="tx-bulk-promote">
                        ⚡ {$t('transactions.bulk.promotePair')}
                    </button>
                {/if}
            </div>
        </div>

        <!-- DataTable body -->
        <div class="flex-1 min-h-0 overflow-y-auto px-3 py-2" data-testid="tx-bulk-body">
            <DataTable
                bind:this={tableRef}
                data={drafts}
                {columns}
                getRowId={(d) => d.tempId}
                storageKey="tx-bulk-modal"
                enableSelection={false}
                enableColumnFilters={false}
                enablePagination={false}
                enableSorting={false}
                enableColumnVisibility={true}
                enableActions={mode === 'create-many'}
                rowActions={rowActionsForTable}
                stickyActions={false}
            />
        </div>

        <!-- Footer (Bugfix-4 §U16: validate-now on the left, no duplicate chip
             /issue-count — the green/warning banners above are the single
             source of truth for validate state). -->
        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t border-gray-100 dark:border-slate-700 shrink-0 text-xs">
            <div class="flex items-center gap-2 flex-wrap">
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={() => scheduler.trigger('manual')} data-testid="tx-bulk-validate-now">
                    <Zap size={12} /> {$t('transactions.validate.now')}
                </button>
                {#if scheduler.state.isValidating}
                    <span class="text-[11px] text-gray-500 dark:text-gray-400" data-testid="tx-bulk-validating">{$t('transactions.validate.validating')}</span>
                {/if}
                {#if mode === 'edit-many'}
                    <span class="text-[11px] text-gray-500 dark:text-gray-400">{$t('transactions.bulk.editHint')}</span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600" onclick={requestClose} data-testid="tx-bulk-cancel">{$t('common.cancel')}</button>
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={commitDisabled} onclick={commit} data-testid="tx-bulk-commit">
                    {commitLabel}
                </button>
            </div>
        </div>
    </div>
</ModalBase>

<!-- Bugfix-3 §C11: confirm dialog when closing with unsaved changes. -->
<ConfirmModal
    open={confirmCloseOpen}
    title={$t('common.discardChanges') || 'Discard changes?'}
    message={$t('common.discardChangesMessage')}
    confirmText={$t('common.discard') || $t('common.confirm')}
    cancelText={$t('common.cancel')}
    warning
    onConfirm={confirmDiscardAndClose}
    onCancel={() => (confirmCloseOpen = false)}
    zIndex={70}
/>

