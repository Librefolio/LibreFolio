<!--
  TransactionBulkModal.svelte — Unified bulk editor for transactions.

  Built on top of `DataTable.svelte` with editable cells. Supports a mixed bag
  of new drafts + existing rows + rows marked for deletion, validated+committed
  together via the unified backend pipeline.

  Mode-less: each row's role is inferred from its data:
  - initialRow.id > 0 → existing DB row (edit/delete)
  - initialRow.id ≤ 0 or absent → new draft (create)

  Row states:
  - 'new'      → brand new draft, committed as CREATE
  - 'original' → existing row loaded but unmodified (skipped on commit)
  - 'edited'   → existing row with changes, committed as UPDATE
  - 'delete'   → existing row marked for deletion, committed as DELETE

  Features:
  - Checkbox selection with bulk actions (delete selected)
  - Date sorting (asc/desc)
  - Row actions: edit, clone, remove, mark/unmark delete
  - Nested TransactionFormModal for structured single-row editing
  - Paired rows (TRANSFER/FX_CONVERSION) with special rendering (future)

  Validation: 100% server-side via POST /transactions/validate. Auto-validate
  is debounced (1 s) + idle-fire (60 s) when N ≤ 50; above that threshold only
  the manual `⚡ Validate now` button works (toolbar shows ⓘ hint).

  Commit: POST /transactions/commit with creates + updates + deletes. On
  `committed=false` the modal stays open with a persistent banner.
-->
<script lang="ts">
    import {onDestroy, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {X, Plus, Pencil, Copy, Trash2, Check, Undo2, Save} from 'lucide-svelte';

    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import TransactionResultBanner from './TransactionResultBanner.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';

    import type {ColumnDef, CellContent} from '$lib/components/table/types';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded, getAssetInfo, getAllAssets} from '$lib/stores/assetStore';
    import {ensureBrokersLoaded, getAllBrokers, brokerStoreVersion, type BrokerInfo} from '$lib/stores/brokerStore';
    import {ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {type TransactionTypeCode, getTypeRule, isDraftReadyForValidation, ensureTypesLoaded, isTypesLoaded} from '$lib/stores/transactionTypeStore';
    import {createValidateScheduler} from '$lib/utils/useValidateScheduler.svelte';
    import {saveWithRetry, extractErrorMessage, extractValidationIssues} from '$lib/utils/saveWithRetry';
    import {buildCreatePayload, buildUpdateDiff, diffDualItem, type TxFields, type TxOriginal} from '$lib/utils/txPayloadHelpers';
    import {resolveIssueMessage, type ResolverContext} from '$lib/utils/resolveValidationMessage';
    import {generateUUID} from '$lib/utils/uuid';
    import {formatCurrencyAmountHtml} from '$lib/utils/currencyFormat';
    import {getStringColor} from '$lib/utils/colors';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import TransactionFormModal from './TransactionFormModal.svelte';
    import TransactionPickerModal from './TransactionPickerModal.svelte';
    import {txStoreGet, txStoreCount} from '$lib/stores/txStore.svelte';
    import type {TXReadItem, ValidationIssue} from './types';

    // =========================================================================
    // Types
    // =========================================================================

    /** WorkspaceIntent — declarative API for opening the BulkModal.
     *  +page passes only action + txIds; BulkModal resolves data from txStore. */
    export type WorkspaceIntent =
        | {action: 'create'}
        | {action: 'edit'; txIds: number[]}
        | {action: 'delete'; txIds: number[]}
        | {action: 'clone'; txIds: number[]};

    interface DraftRow {
        tempId: string; // stable id used by DataTable.getRowId + navigateToRowId
        status: 'new' | 'edited' | 'original' | 'delete';
        id?: number; // present for existing DB rows
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
        // B1-13: partner data for paired types (Da:/A: display)
        partnerBrokerId?: number;
        partnerCash?: {code: string; amount: string} | null;
        partnerDate?: string;
        /** DB id of the linked partner row (for paired rendering + commit). */
        _partnerId?: number;
        /** Full partner payload from FormModal's collectDualCreates().
         *  For new pairs: a complete CREATE payload with link_uuid.
         *  For existing pairs being edited: a CREATE-style payload to diff against txStore. */
        _partnerFormPayload?: Record<string, unknown>;
        /** True for rows added via PickerModal (can be removed without DB delete). */
        _addedViaPicker?: boolean;
    }

    interface Props {
        open: boolean;
        /** Legacy: provide rows directly. Prefer `intent` instead. */
        initialRows?: TXReadItem[];
        /** Declarative API: action + txIds. BulkModal resolves from txStore. */
        intent?: WorkspaceIntent;
        /** Bugfix-5 §U20: tag suggestions sourced from the parent's loaded
         *  transactions. The bulk modal augments this list with any tag that
         *  appears in its in-flight drafts (so newly-typed tags are
         *  immediately available across rows). */
        availableTags?: string[];
        /** When set, auto-opens the FormModal on mount:
         *  'edit' → opens the first draft for editing
         *  'create' → opens a new row form */
        autoOpenForm?: 'create' | 'edit' | null;
        /** B23: when 'delete', all rows start with status='delete' (bulk delete flow). */
        initialStatus?: 'delete';
        onClose: () => void;
        onCommitted?: (resp: unknown) => void;
    }

    let {open, initialRows = [], intent, availableTags = [], autoOpenForm = null, initialStatus, onClose, onCommitted}: Props = $props();

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

    function fromTx(tx: TXReadItem, overrideStatus?: 'delete'): DraftRow {
        const isCreate = !(tx.id > 0);
        const txRule = getTypeRule(tx.type);
        // Auto-sign: show positive values for auto-negated types
        let qty = tx.quantity;
        if (txRule.quantityRule === 'negative' && Number(qty) < 0) {
            qty = String(Math.abs(Number(qty)));
        }
        let cash = tx.cash ? {code: tx.cash.code, amount: tx.cash.amount} : null;
        if (cash && txRule.cashSign === 'negative' && Number(cash.amount) < 0) {
            cash = {code: cash.code, amount: String(Math.abs(Number(cash.amount)))};
        }
        const status = isCreate ? 'new' : overrideStatus === 'delete' ? 'delete' : 'original';
        return {
            tempId: generateUUID(),
            status,
            id: isCreate ? undefined : tx.id,
            original: isCreate ? undefined : tx,
            broker_id: tx.broker_id,
            asset_id: tx.asset_id ?? null,
            type: tx.type as TransactionTypeCode,
            date: isCreate ? todayIso() : tx.date,
            quantity: qty,
            cash,
            tags: [...(tx.tags ?? [])],
            description: tx.description ?? '',
            asset_event_id: tx.asset_event_id ?? null,
            cost_basis_override: tx.cost_basis_override ?? '',
            // Regenerate link_uuid for pairs being cloned (create-many) — though
            // pair types are not editable here, BRIM/duplicate flows may seed them.
            // If resolveInitialRows already set a shared link_uuid (clone paired), preserve it.
            link_uuid: (tx as any).link_uuid ?? (isCreate && tx.related_transaction_id != null ? generateUUID() : null),
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
    let commitFailed = $state(false);
    let committing = $state(false);
    /** Anti-bounce: track last commit draft key + timestamp. */
    let lastCommitDraftKey = $state('');
    let lastCommitAt = $state(0);
    const COMMIT_ANTI_BOUNCE_MS = 10000;
    let tableRef = $state<DataTable<DraftRow> | undefined>(undefined);
    /** Snapshot of `drafts` at modal-open time, used to detect unsaved changes
     *  for the close-confirmation guard (Bugfix-3 §C11). */
    let initialDraftsKey = $state('');
    let confirmCloseOpen = $state(false);
    /** B23 Step 4: confirm edit on a row marked for deletion. */
    let confirmEditDeleteOpen = $state(false);
    let confirmEditDeleteRow = $state<DraftRow | null>(null);

    /** Resolve initialRows from intent (if provided) or use legacy initialRows prop. */
    function resolveInitialRows(): {rows: TXReadItem[]; status?: 'delete'; autoForm: string | null} {
        if (intent) {
            if (intent.action === 'create') {
                return {rows: [], autoForm: 'create'};
            }
            const txIds = intent.txIds;
            const resolved: TXReadItem[] = [];
            const seen = new Set<number>();
            for (const id of txIds) {
                const tx = txStoreGet(id);
                if (!tx || seen.has(id)) continue;
                seen.add(id);
                resolved.push(tx);
                // Auto-include partner for edit/delete
                if (intent.action !== 'clone' && tx.related_transaction_id != null && !seen.has(tx.related_transaction_id)) {
                    const partner = txStoreGet(tx.related_transaction_id);
                    if (partner) {
                        resolved.push(partner);
                        seen.add(partner.id);
                    }
                }
            }
            if (intent.action === 'delete') {
                return {rows: resolved, status: 'delete', autoForm: null};
            }
            if (intent.action === 'clone') {
                // B2-fix: auto-include partner for paired clone
                for (const id of txIds) {
                    const tx = txStoreGet(id);
                    if (tx?.related_transaction_id != null && !seen.has(tx.related_transaction_id)) {
                        const partner = txStoreGet(tx.related_transaction_id);
                        if (partner) {
                            resolved.push(partner);
                            seen.add(partner.id);
                        }
                    }
                }
                const today = new Date().toISOString().slice(0, 10);
                // Generate shared link_uuid for paired clones
                const sharedLinkUuid = resolved.length === 2 && resolved[0].type === resolved[1].type
                    ? generateUUID() : null;
                const cloned = resolved.map((r) => {
                    const c = {...r, id: 0, date: today, related_transaction_id: null} as TXReadItem;
                    // Bug6-fix: reset quantity when the type requires qty=0 (e.g. INTEREST)
                    const rule = getTypeRule(r.type);
                    if (rule.quantityRule === 'zero') c.quantity = '0';
                    if (sharedLinkUuid) (c as any).link_uuid = sharedLinkUuid;
                    return c;
                });
                return {rows: cloned, autoForm: cloned.length === 1 ? 'create' : null};
            }
            // edit — auto-open FormModal only for single-row intent (user selected 1 row)
            return {rows: resolved, autoForm: txIds.length === 1 ? 'edit' : null};
        }
        // Legacy: use initialRows prop
        return {rows: initialRows, status: initialStatus, autoForm: autoOpenForm};
    }

    // Reset on open — compute `next` locally first, then assign once (avoids
    // [[problems/svelte5-effect-read-write-loop]]).
    $effect(() => {
        if (!open) return;
        const {rows, status: initSt, autoForm} = resolveInitialRows();
        untrack(() => {
            issues = [];
            formError = null;
            commitFailed = false;
            confirmCloseOpen = false;
            // When no initial rows → empty grid; user adds rows via nested FormModal.
            let next: DraftRow[] = rows.length > 0 ? rows.map((r) => fromTx(r, initSt)) : [];

            // Collapse paired rows: keep only the "from" half with partner
            // metadata populated. No dependency on isTypesLoaded — pair detection
            // uses related_transaction_id (not getTypeRule().requiresPair).
            next = collapsePairedDrafts(next);

            drafts = next;
            initialDraftsKey = serializeDrafts(next);

            // Schedule auto-open if types already loaded; otherwise defer.
            if (isTypesLoaded()) {
                scheduleAutoOpen(autoForm, next);
            } else if (rows.length === 0) {
                queueMicrotask(() => {
                    formOpen = true;
                    formMode = 'create';
                    formInitial = null;
                    formPartnerRow = null;
                    formEditingTempId = null;
                });
            }
        });
        void (async () => {
            await Promise.all([ensureBrokersLoaded(), ensureCurrenciesLoaded($currentLanguage), ensureAssetsLoaded(), ensureTypesLoaded()]);
            untrack(() => {
                if (!formOpen) {
                    scheduleAutoOpen(autoForm, drafts);
                }
            });
        })();
    });

    /** Schedule auto-open of the nested FormModal based on the mode. */
    function scheduleAutoOpen(autoForm: string | null, draftArr: DraftRow[]) {
        if (autoForm === 'edit' && draftArr.length > 0) {
            queueMicrotask(() => openEditRowForm(draftArr[0]));
        } else if (autoForm === 'create' && draftArr.length > 0) {
            // Clone: row is 'new' so openEditRowForm uses create mode
            queueMicrotask(() => openEditRowForm(draftArr[0]));
        } else if (draftArr.length === 0) {
            // Auto-open for brand-new empty grid
            queueMicrotask(() => {
                formOpen = true;
                formMode = 'create';
                formInitial = null;
                formPartnerRow = null;
                formEditingTempId = null;
            });
        }
    }

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

    function addRow() {
        // Bugfix-5 §A4: kept as a programmatic helper. The toolbar entrypoint
        // now opens TransactionFormModal (commitOnSave=false) and pushes the
        // resulting draft into the grid via `addRowFromForm`.
        drafts = [...drafts, emptyDraft()];
    }
    void addRow;

    /** Convert a DraftRow to a TXReadItem-shaped object so it can be fed back to
     *  TransactionFormModal as `initialRow`. We reuse the BulkModal's in-flight
     *  draft state, NOT a server-persisted row, so id/timestamps are synthetic. */
    function draftToTxLike(d: DraftRow): TXReadItem {
        return {
            id: d.id ?? 0,
            broker_id: d.broker_id,
            asset_id: d.asset_id,
            type: d.type,
            date: d.date,
            quantity: d.quantity,
            cash: d.cash,
            // C1-fix: if this is a paired row, expose the partner id so FormModal
            // opens in dual mode. For 'new' drafts _partnerId is undefined, so we
            // use a sentinel -1 to signal "pair present, fetch locally".
            related_transaction_id: d._partnerId ?? (d.partnerBrokerId != null ? -1 : null),
            tags: d.tags,
            description: d.description,
            cost_basis_override: d.cost_basis_override || null,
            asset_event_id: d.asset_event_id,
            created_at: d.created_at,
            updated_at: d.updated_at,
        };
    }

    /** Populate partner display metadata on a draft from txStore. */
    function populatePartnerDisplay(d: DraftRow): void {
        const pid = d.original?.related_transaction_id ?? d._partnerId;
        if (pid == null) return;
        const partner = txStoreGet(pid);
        if (!partner) return;
        d._partnerId = partner.id;
        d.partnerBrokerId = partner.broker_id;
        d.partnerCash = partner.cash ?? null;
        d.partnerDate = partner.date;
    }

    /** Collapse paired drafts in an array: detect partners via
     *  related_transaction_id, keep the "from" half, set partner metadata,
     *  remove the "to" half. For solo drafts with a partner in txStore,
     *  populate partner display data from the store. */
    function collapsePairedDrafts(draftArr: DraftRow[]): DraftRow[] {
        const idToIdx = new Map<number, number>();
        draftArr.forEach((d, i) => {
            if (d.id != null) idToIdx.set(d.id, i);
        });
        const toRemove = new Set<number>();
        for (let i = 0; i < draftArr.length; i++) {
            if (toRemove.has(i)) continue;
            const d = draftArr[i];
            const partnerId = d.original?.related_transaction_id;
            if (partnerId == null) continue;
            const pIdx = idToIdx.get(partnerId);
            if (pIdx == null || pIdx === i || toRemove.has(pIdx)) continue;
            const partner = draftArr[pIdx];
            // Determine from/to: "from" = negative cash (giver)
            const cashAmt = Number(d.original?.cash?.amount ?? 0);
            const partnerCashAmt = Number(partner.original?.cash?.amount ?? 0);
            let fromIdx = i,
                toIdx = pIdx;
            if (cashAmt > 0 && partnerCashAmt <= 0) {
                fromIdx = pIdx;
                toIdx = i;
            } else if (cashAmt === 0 && partnerCashAmt === 0) {
                if (Number(d.original?.quantity ?? 0) > 0) {
                    fromIdx = pIdx;
                    toIdx = i;
                }
            }
            const fromDraft = draftArr[fromIdx];
            const toDraft = draftArr[toIdx];
            fromDraft._partnerId = toDraft.id;
            fromDraft.partnerBrokerId = toDraft.broker_id;
            fromDraft.partnerCash = toDraft.cash;
            fromDraft.partnerDate = toDraft.date;
            toRemove.add(toIdx);
        }
        const result = draftArr.filter((_, i) => !toRemove.has(i));
        // For remaining drafts with partner not in batch, populate from txStore
        for (const d of result) {
            if (d.original?.related_transaction_id != null && d._partnerId == null) {
                populatePartnerDisplay(d);
            }
        }
        return result;
    }

    /** Apply the form-collected payload to a brand-new draft row. */
    function addRowFromForm(payload: Record<string, unknown>) {
        const next = emptyDraft();
        applyFormPayload(next, payload);
        drafts = [...drafts, next];
    }

    /** Apply the form-collected payload to an existing draft (deep-edit). */
    function patchRowFromForm(tempId: string, payload: Record<string, unknown>) {
        drafts = drafts.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d};
            applyFormPayload(merged, payload);
            // Status 'edited' is derived automatically by deriveStatus() — no manual marking needed.
            return merged;
        });
    }

    function applyFormPayload(target: DraftRow, p: Record<string, unknown>) {
        if (typeof p.broker_id === 'number') target.broker_id = p.broker_id;
        if (typeof p.type === 'string') target.type = p.type as TransactionTypeCode;
        if (typeof p.date === 'string') target.date = p.date;
        if (typeof p.quantity === 'string') target.quantity = p.quantity;
        target.asset_id = (p.asset_id as number | null | undefined) ?? null;
        target.cash = (p.cash as DraftRow['cash']) ?? null;
        target.tags = Array.isArray(p.tags) ? (p.tags as string[]) : [];
        target.description = typeof p.description === 'string' ? p.description : '';
        target.asset_event_id = (p.asset_event_id as number | null | undefined) ?? null;
        target.cost_basis_override = typeof p.cost_basis_override === 'string' ? p.cost_basis_override : '';
        if (typeof p.link_uuid === 'string') target.link_uuid = p.link_uuid;
        // B1-13: partner data from dual FormModal push
        if (typeof p._partnerBrokerId === 'number') target.partnerBrokerId = p._partnerBrokerId;
        if (p._partnerCash !== undefined) target.partnerCash = (p._partnerCash as DraftRow['partnerCash']) ?? null;
        if (typeof p._partnerDate === 'string') target.partnerDate = p._partnerDate;
    }

    // =========================================================================
    // B1-13: Pair Merging (edit-many)
    // =========================================================================

    function removeRow(tempId: string) {
        drafts = drafts.filter((d) => d.tempId !== tempId);
    }

    /** R6-B.4: Mark an existing row for deletion (toggle). */
    function markDelete(tempId: string) {
        drafts = drafts.map((d) => {
            if (d.tempId !== tempId) return d;
            if (d.status === 'delete') {
                // Unmark: revert to 'original' — deriveStatus() will compute 'edited' if fields changed
                return {...d, status: d.original ? 'original' : 'new'};
            }
            return {...d, status: 'delete'};
        });
    }

    /** R6-B.4: Clone a draft row as a new row. */
    function cloneRow(tempId: string) {
        const src = drafts.find((d) => d.tempId === tempId);
        if (!src) return;
        const clone: DraftRow = {
            ...src,
            tempId: generateUUID(),
            status: 'new',
            id: undefined,
            original: undefined,
            link_uuid: src.link_uuid ? generateUUID() : null,
            date: todayIso(),
        };
        drafts = [...drafts, clone];
    }

    function resetRow(tempId: string) {
        const target = drafts.find((d) => d.tempId === tempId);
        if (!target || !target.original) return;
        drafts = drafts.map((d) => {
            if (d.tempId !== tempId) return d;
            const reset = fromTx(d.original!);
            if (d._addedViaPicker) reset._addedViaPicker = true;
            // Re-populate partner display from txStore
            populatePartnerDisplay(reset);
            // Discard any partner edits
            reset._partnerFormPayload = undefined;
            return reset;
        });
    }

    function resetAll() {
        drafts = drafts.map((d) => {
            if (!d.original) return d;
            const reset = fromTx(d.original);
            if (d._addedViaPicker) reset._addedViaPicker = true;
            populatePartnerDisplay(reset);
            reset._partnerFormPayload = undefined;
            return reset;
        });
    }

    // =========================================================================
    // Sanitizers
    // =========================================================================

    // -----------------------------------------------------------------
    // Shared helpers for collectCreate / collectUpdate
    // -----------------------------------------------------------------

    function collectCreate(d: DraftRow): Record<string, unknown> {
        const rule = getTypeRule(d.type);
        return buildCreatePayload(draftToTxFields(d), rule);
    }

    function collectUpdate(d: DraftRow): Record<string, unknown> | null {
        if (!d.original || d.id == null) return null;
        const rule = getTypeRule(d.type);
        const origRule = getTypeRule(d.original.type as TransactionTypeCode);
        return buildUpdateDiff(draftToTxFields(d), d.original as unknown as TxOriginal, rule, origRule);
    }

    /**
     * Build the bulk payload excluding one specific draft (by tempId).
     * Used by FormModal for context-aware validation: the form sends the
     * entire bulk + its own row to /validate, so the balance walk sees
     * all in-flight changes.
     */
    function getBulkContextExcluding(excludeTempId: string | null): {creates: Record<string, unknown>[]; updates: Record<string, unknown>[]; deletes: number[]} {
        const creates: Record<string, unknown>[] = [];
        const updates: Record<string, unknown>[] = [];
        const deletes: number[] = [];
        for (const d of drafts) {
            if (d.tempId === excludeTempId) continue;
            const st = deriveStatus(d);
            if (st === 'new') {
                creates.push(collectCreate(d));
                if (d._partnerFormPayload) creates.push(d._partnerFormPayload);
            } else if (st === 'edited') {
                const upd = collectUpdate(d);
                if (upd && Object.keys(upd).length > 1) updates.push(upd);
                if (d._partnerFormPayload && d._partnerId != null) {
                    const partnerOrig = txStoreGet(d._partnerId);
                    if (partnerOrig) {
                        const partnerUpd = diffDualItem(d._partnerFormPayload, partnerOrig as unknown as TxOriginal);
                        if (Object.keys(partnerUpd).length > 1) updates.push(partnerUpd);
                    }
                }
            } else if (st === 'delete' && d.id != null) {
                deletes.push(d.id);
                if (d._partnerId != null) deletes.push(d._partnerId);
            }
        }
        return {creates, updates, deletes};
    }

    /** Convert a DraftRow to the shared TxFields interface. */
    function draftToTxFields(d: DraftRow): TxFields {
        return {
            type: d.type,
            broker_id: d.broker_id,
            date: d.date,
            quantity: d.quantity,
            asset_id: d.asset_id,
            cash: d.cash,
            tags: d.tags,
            description: d.description,
            cost_basis_override: d.cost_basis_override,
            asset_event_id: d.asset_event_id,
            link_uuid: d.link_uuid,
        };
    }

    /** Derive the effective display status of a draft row.
     *  'new' and 'delete' are explicit. 'edited' is derived from diff vs original.
     *  This eliminates "edited falso" bugs — status is always truthful. */
    function deriveStatus(d: DraftRow): 'new' | 'edited' | 'original' | 'delete' {
        if (d.status === 'new') return 'new';
        if (d.status === 'delete') return 'delete';
        // For existing rows: check whether fields differ from original
        if (!d.original) return 'original';
        const diff = collectUpdate(d);
        if (diff && Object.keys(diff).length > 1) return 'edited';
        // Also check partner changes
        if (d._partnerFormPayload && d._partnerId != null) {
            const partnerOrig = txStoreGet(d._partnerId);
            if (partnerOrig) {
                const partnerUpd = diffDualItem(d._partnerFormPayload, partnerOrig as unknown as TxOriginal);
                if (Object.keys(partnerUpd).length > 1) return 'edited';
            }
        }
        return 'original';
    }

    // =========================================================================
    // Validate scheduler
    // =========================================================================

    const scheduler = createValidateScheduler({
        enabled: () => drafts.length > 0 && drafts.length <= AUTO_VALIDATE_THRESHOLD && drafts.some((d) => deriveStatus(d) !== 'delete' && isDraftReadyForValidation(d)),
        draftKey: () => lastDraftKey,
        validateFn: async () => {
            if (drafts.length === 0) {
                issues = [];
                lastValidatedDraftKey = lastDraftKey;
                issuesDismissed = false;
                return {issuesCount: 0};
            }
            // R6-B.4: build mixed payload matching commit logic
            const creates: Record<string, unknown>[] = [];
            const updates: Record<string, unknown>[] = [];
            const deletes: number[] = [];
            for (const d of drafts) {
                const st = deriveStatus(d);
                if (st === 'new') {
                    creates.push(collectCreate(d));
                    if (d._partnerFormPayload) creates.push(d._partnerFormPayload);
                } else if (st === 'edited') {
                    const upd = collectUpdate(d);
                    if (upd && Object.keys(upd).length > 1) updates.push(upd);
                    // Partner update from dual-form edits
                    if (d._partnerFormPayload && d._partnerId != null) {
                        const partnerOrig = txStoreGet(d._partnerId);
                        if (partnerOrig) {
                            const partnerUpd = diffDualItem(d._partnerFormPayload, partnerOrig as unknown as TxOriginal);
                            if (Object.keys(partnerUpd).length > 1) updates.push(partnerUpd);
                        }
                    }
                } else if (st === 'delete' && d.id != null) {
                    deletes.push(d.id);
                    if (d._partnerId != null) deletes.push(d._partnerId);
                }
            }
            const payload: Record<string, unknown> = {};
            if (creates.length > 0) payload.creates = creates;
            if (updates.length > 0) payload.updates = updates;
            if (deletes.length > 0) payload.deletes = deletes;
            // Snapshot the key at the moment we *send* the payload — so when
            // the response comes back we know whether the drafts have drifted.
            const sentKey = lastDraftKey;
            try {
                const res = (await zodiosApi.validate_transactions_api_v1_transactions_validate_post(payload as never)) as {committed?: boolean; issues?: ValidationIssue[]};
                issues = res?.issues ?? [];
                lastValidatedDraftKey = sentKey;
                issuesDismissed = false;
                return {issuesCount: issues.length};
            } catch (e) {
                // 422 safety net — should rarely fire now that /validate uses List[dict].
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
                        return {operation: 'create' as const, index: idx, error: iss.msg, code: iss.code, params: iss.params, loc: iss.loc} as ValidationIssue;
                    });
                } else {
                    issues = [{operation: 'create', index: 0, error: extractErrorMessage(e, $t('transactions.bulk.saveFailed'))}];
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
    let fieldIssues = $derived(issues.filter((i) => i.index >= 0));
    let balanceIssues = $derived(issues.filter((i) => i.index < 0));

    /**
     * For balance issues (index=-1), try to find the draft row that caused
     * the violation by matching brokerId + assetId/currency from issue params.
     * Returns the 0-based index of the last matching draft, or -1 if unresolvable.
     */
    function findRowForBalanceIssue(issue: ValidationIssue): number {
        const p = issue.params;
        if (!p) return -1;
        const brokerId = Number(p.brokerId);
        if (!brokerId) return -1;

        if (issue.code === 'balanceAssetNegative') {
            const assetId = Number(p.assetId);
            for (let i = drafts.length - 1; i >= 0; i--) {
                if (drafts[i].broker_id === brokerId && drafts[i].asset_id === assetId) return i;
            }
        } else if (issue.code === 'balanceCashNegative') {
            const currency = p.currency as string;
            for (let i = drafts.length - 1; i >= 0; i--) {
                if (drafts[i].broker_id === brokerId && drafts[i].cash?.code === currency) return i;
            }
        }
        return -1;
    }

    /** Context for resolving validation issue codes into translated messages. */
    let resolverCtx: ResolverContext = $derived({
        brokers: brokers as unknown as Array<{id: number; name: string}>,
        assets: getAllAssets() as unknown as Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}>,
        getBrokerIconUrl: (brokerId: number) => {
            const b = brokers.find((br) => br.id === brokerId);
            if (!b) return null;
            if (b.icon_url?.trim()) return b.icon_url;
            if (b.portal_url?.trim()) {
                try {
                    return new URL(b.portal_url).origin + '/favicon.ico';
                } catch {
                    /* skip */
                }
            }
            return null;
        },
    });

    $effect(() => {
        if (!open) return;
        const key = JSON.stringify(drafts);
        if (key === lastDraftKey) return;
        lastDraftKey = key;
        commitFailed = false;
        scheduler.trigger('change');
    });

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        if (committing) return;
        committing = true;
        formError = null;
        commitFailed = false;
        // Anti-bounce: if drafts unchanged and < 10s since last commit attempt, skip.
        const currentKey = lastDraftKey;
        if (currentKey === lastCommitDraftKey && Date.now() - lastCommitAt < COMMIT_ANTI_BOUNCE_MS) {
            committing = false;
            return;
        }
        try {
            // R6-B.4: unified mixed batch — creates + updates + deletes in one call.
            const creates: Record<string, unknown>[] = [];
            const updates: Record<string, unknown>[] = [];
            const deletes: number[] = [];

            for (const d of drafts) {
                const st = deriveStatus(d);
                if (st === 'new') {
                    creates.push(collectCreate(d));
                    if (d._partnerFormPayload) creates.push(d._partnerFormPayload);
                } else if (st === 'edited') {
                    const upd = collectUpdate(d);
                    if (upd && Object.keys(upd).length > 1) updates.push(upd);
                    // Partner update from dual-form edits
                    if (d._partnerFormPayload && d._partnerId != null) {
                        const partnerOrig = txStoreGet(d._partnerId);
                        if (partnerOrig) {
                            const partnerUpd = diffDualItem(d._partnerFormPayload, partnerOrig as unknown as TxOriginal);
                            if (Object.keys(partnerUpd).length > 1) updates.push(partnerUpd);
                        }
                    }
                } else if (st === 'delete' && d.id != null) {
                    deletes.push(d.id);
                    if (d._partnerId != null) deletes.push(d._partnerId);
                }
                // 'original' rows are unchanged — skip
            }

            if (creates.length === 0 && updates.length === 0 && deletes.length === 0) {
                onClose();
                return;
            }

            const payload: Record<string, unknown> = {};
            if (creates.length > 0) payload.creates = creates;
            if (updates.length > 0) payload.updates = updates;
            if (deletes.length > 0) payload.deletes = deletes;

            const result = await saveWithRetry(() => zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never), {fallback: $t('transactions.bulk.saveFailed'), toast: false});
            if (result.status === 'error') {
                formError = result.message;
                return;
            }
            const resp = result.data as {committed?: boolean; issues?: ValidationIssue[]};
            if (!resp.committed) {
                const rawIssues = resp.issues ?? [];
                // Step 17 (M10): extra_forbidden errors are FE bugs — log and hide from user
                const internalErrors = rawIssues.filter((i) => i.code === 'extra_forbidden');
                if (internalErrors.length > 0) {
                    console.error('[BulkModal] Internal extra_forbidden errors (FE bug):', internalErrors);
                }
                const userIssues = rawIssues.filter((i) => i.code !== 'extra_forbidden');
                if (userIssues.length === 0 && internalErrors.length > 0) {
                    // All errors were internal — show generic message
                    issues = [{operation: 'update', index: 0, error: 'An internal error occurred. Please try again.'}];
                } else {
                    issues = userIssues;
                }
                issuesDismissed = false;
                commitFailed = true;
                return;
            }
            onCommitted?.(resp);
            onClose();
        } finally {
            committing = false;
            lastCommitDraftKey = currentKey;
            lastCommitAt = Date.now();
        }
    }

    // =========================================================================
    // Columns
    // =========================================================================

    // TYPE_OPTIONS removed in Bugfix-2 §C6 — type column now uses
    // TransactionTypeSearchSelect (PNG icons + i18n labels).

    // =========================================================================
    // DRY helpers for readonly cell rendering
    // =========================================================================

    /** Render a Da:/A: dual-line cell for paired rows.
     *  Uses ch-based min-width so the shorter label (e.g. "A:") is padded
     *  to match the longer one (e.g. "From:"), keeping content aligned. */
    function renderDualHtml(fromText: string, toText: string): string {
        const fromLabel = $t('transactions.form.from');
        const toLabel = $t('transactions.form.to');
        // Pad to the longer label + colon + 1ch spacing
        const maxCh = Math.max(fromLabel.length, toLabel.length) + 2;
        const labelCls = `inline-block text-gray-400 dark:text-gray-500 font-medium`;
        const labelStyle = `min-width:${maxCh}ch`;
        return `<div class="flex flex-col gap-0.5 text-xs leading-tight min-h-[2.5rem] justify-center"><span><span class="${labelCls}" style="${labelStyle}">${fromLabel}:</span> ${fromText}</span><hr class="border-gray-200 dark:border-gray-600 my-0.5"/><span><span class="${labelCls}" style="${labelStyle}">${toLabel}:</span> ${toText}</span></div>`;
    }

    /** Readonly type badge with icon. */
    function renderTypeHtml(type: string): string {
        const label = $t(`transactions.types.${type}`) || type;
        const slug = type.toLowerCase().replace(/_/g, '-');
        const isPair = getTypeRule(type).requiresPair;
        const arrow = isPair ? '<span class="shrink-0">↔</span>' : '';
        return `<span class="inline-flex items-center gap-1.5 text-xs leading-snug" style="white-space:normal"><img src="/icons/transactions/${slug}.png" alt="" style="width:1.75rem;height:1.75rem" class="object-contain shrink-0" onerror="this.style.display='none'"/>${arrow}<span>${label}</span></span>`;
    }

    /** Format a cash value as "±amount CODE". */
    function formatCashText(cash: {code: string; amount: string} | null | undefined): string {
        if (!cash) return '—';
        const amt = Number(cash.amount);
        if (isNaN(amt)) return `${cash.amount} ${cash.code}`;
        return formatCurrencyAmountHtml(amt, cash.code, {showSign: true});
    }

    /** Broker name lookup. */
    function brokerName(brokerId: number): string {
        return brokers.find((b) => b.id === brokerId)?.name ?? '—';
    }

    /** Asset display name lookup. */
    function assetName(assetId: number | null | undefined): string {
        if (assetId == null) return '—';
        const info = getAssetInfo(assetId);
        return info?.display_name ?? `#${assetId}`;
    }

    /** H1-fix: Asset name with icon for readonly cells. */
    function renderAssetHtml(assetId: number | null | undefined): string {
        if (assetId == null) return '<span class="text-gray-400 italic">—</span>';
        const info = getAssetInfo(assetId);
        const name = info?.display_name ?? `#${assetId}`;
        // Bug11-fix: use asset type icon as fallback when icon_url is null
        const iconUrl = info?.icon_url ?? (info?.asset_type ? getAssetTypeIconUrl(info.asset_type) : null);
        const iconHtml = iconUrl ? `<img src="${iconUrl}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />` : '';
        return `<span class="inline-flex items-center gap-1.5 text-sm truncate">${iconHtml}${name}</span>`;
    }

    /** H1-fix: Broker name with favicon icon for readonly cells. */
    function renderBrokerHtml(brokerId: number): string {
        const b = brokers.find((br) => br.id === brokerId);
        const name = b?.name ?? '—';
        let iconSrc = '';
        if (b?.icon_url) {
            iconSrc = b.icon_url;
        } else if (b?.portal_url) {
            try {
                iconSrc = new URL(b.portal_url).origin + '/favicon.ico';
            } catch {}
        }
        const iconHtml = iconSrc ? `<img src="${iconSrc}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />` : '';
        return `<span class="inline-flex items-center gap-1.5 text-sm truncate">${iconHtml}${name}</span>`;
    }

    let columns = $derived.by<ColumnDef<DraftRow>[]>(() => {
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
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    const st = deriveStatus(row);
                    return {
                        type: 'html',
                        html:
                            st === 'new'
                                ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">new</span>'
                                : st === 'edited'
                                  ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">edit</span>'
                                  : st === 'delete'
                                    ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">🔴 del</span>'
                                    : '<span class="text-gray-300 dark:text-gray-600">·</span>',
                    };
                },
            },
            {
                id: 'id',
                header: 'ID',
                type: 'text',
                width: 90,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    if (row.id == null) return {type: 'html', html: '—'};
                    const rule = getTypeRule(row.type);
                    if (rule.requiresPair && row._partnerId != null) {
                        return {type: 'html', html: renderDualHtml(`#${row.id}`, `#${row._partnerId}`)};
                    }
                    return {type: 'html', html: `#${row.id}`};
                },
            },
            {
                id: 'date',
                header: () => $t('transactions.table.date'),
                type: 'text',
                width: 140,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    const rule = getTypeRule(row.type);
                    // Paired rows with different dates → Da:/A:
                    if (rule.requiresPair && row.partnerDate && row.partnerDate !== row.date) {
                        return {type: 'html', html: renderDualHtml(row.date, row.partnerDate)};
                    }
                    return {type: 'html', html: `<span class="font-mono text-sm text-gray-700 dark:text-gray-200">${row.date}</span>`};
                },
            },
            {
                id: 'type',
                header: () => $t('transactions.table.type'),
                type: 'text',
                width: 155,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => ({type: 'html', html: renderTypeHtml(row.type)}),
            },
            {
                id: 'asset',
                header: () => $t('transactions.table.asset'),
                type: 'text',
                width: 180,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    if (getTypeRule(row.type).assetField === 'forbidden') {
                        return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                    }
                    return {type: 'html', html: renderAssetHtml(row.asset_id)};
                },
            },
            {
                id: 'quantity',
                header: () => $t('transactions.table.quantity'),
                type: 'text',
                width: 110,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    if (getTypeRule(row.type).quantityMode === 'forbidden') {
                        return {type: 'html', html: '<span class="text-gray-400 italic">n/a</span>'};
                    }
                    const qty = row.quantity ?? '0';
                    // H2-fix: paired rows with non-zero qty → show Da:/A: with signed values + emoji
                    const rule = getTypeRule(row.type);
                    if (rule.requiresPair && row.partnerBrokerId != null && Number(qty) !== 0) {
                        const absVal = Math.abs(Number(qty));
                        const fromQty = `-${absVal} 📉`;
                        const toQty = `+${absVal} 📈`;
                        return {type: 'html', html: renderDualHtml(fromQty, toQty)};
                    }
                    return {type: 'html', html: `<span class="font-mono text-sm">${qty}</span>`};
                },
            },
            {
                id: 'cash',
                header: () => $t('transactions.table.cash'),
                type: 'text',
                width: 160,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    const rule = getTypeRule(row.type);
                    if (rule.cashField === 'forbidden') {
                        return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                    }
                    // Paired row → show Da:/A: dual cash lines
                    if (rule.requiresPair && row.partnerCash !== undefined && row.partnerBrokerId != null) {
                        return {type: 'html', html: renderDualHtml(formatCashText(row.cash), formatCashText(row.partnerCash))};
                    }
                    return {type: 'html', html: `<span class="text-sm">${formatCashText(row.cash)}</span>`};
                },
            },
            {
                id: 'broker',
                header: () => $t('transactions.table.broker'),
                type: 'text',
                width: 190,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    const rule = getTypeRule(row.type);
                    // Paired row with different brokers → Da:/A:
                    if (rule.requiresPair && row.partnerBrokerId != null && row.partnerBrokerId !== row.broker_id) {
                        return {type: 'html', html: renderDualHtml(renderBrokerHtml(row.broker_id), renderBrokerHtml(row.partnerBrokerId))};
                    }
                    return {type: 'html', html: renderBrokerHtml(row.broker_id)};
                },
            },
            {
                id: 'description',
                header: () => $t('transactions.form.description'),
                type: 'text',
                width: 200,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    if (!row.description) return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                    const escaped = row.description.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    return {
                        type: 'html',
                        html: `<span class="text-xs text-gray-600 dark:text-gray-300 truncate block leading-tight">${escaped}</span>`,
                        tooltip: {text: row.description, position: 'top', maxWidth: '400px'},
                    };
                },
            },
            {
                id: 'tags',
                header: () => $t('transactions.table.tags'),
                type: 'text',
                width: 180,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => {
                    if (row.tags.length === 0) return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                    const html = row.tags
                        .map((tag) => {
                            const escaped = tag.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                            const c = getStringColor(tag);
                            return `<span class="inline-block px-1.5 py-0.5 text-[10px] rounded mr-0.5 mb-0.5" style="background:${c.bg};color:${c.text}">${escaped}</span>`;
                        })
                        .join('');
                    return {type: 'html', html: `<span class="flex flex-wrap gap-0.5" data-testid="tx-bulk-tags">${html}</span>`};
                },
            },
            {
                id: 'cost_basis_override',
                header: () => $t('transactions.form.costBasis'),
                type: 'text',
                width: 160,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({type: 'html', html: row.cost_basis_override ? `<span class="font-mono text-xs">${row.cost_basis_override}</span>` : '<span class="text-gray-400 italic">auto</span>'}),
            },
            {
                id: 'asset_event_id',
                header: () => $t('transactions.form.assetEvent'),
                type: 'text',
                width: 110,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({type: 'html', html: row.asset_event_id != null ? `<span class="font-mono text-xs">#${row.asset_event_id}</span>` : '<span class="text-gray-400">—</span>'}),
            },
            {
                id: 'link_uuid',
                header: () => $t('transactions.form.linkUuid'),
                type: 'text',
                width: 140,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => {
                    if (row._partnerId != null) return {type: 'html', html: `<code class="text-[10px] font-mono text-gray-400">↔ #${row._partnerId}</code>`};
                    if (row._partnerFormPayload != null) return {type: 'html', html: '<code class="text-[10px] font-mono text-indigo-400">↔ new</code>'};
                    if (row.link_uuid) return {type: 'html', html: `<code class="text-[10px] font-mono text-gray-400">${row.link_uuid.slice(0, 8)}…</code>`};
                    return {type: 'html', html: '—'};
                },
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

    let rowActions = $derived([
        {
            id: 'edit-single',
            icon: Pencil,
            label: () => $t('transactions.bulk.editSingle') || 'Edit row',
            onClick: (row: DraftRow) => handleEditRowClick(row),
        },
        {
            id: 'clone',
            icon: Copy,
            label: () => $t('transactions.bulk.cloneRow') || 'Clone row',
            onClick: (row: DraftRow) => cloneRow(row.tempId),
        },
        {
            id: 'mark-delete',
            icon: Trash2,
            label: (row: DraftRow) => (deriveStatus(row) === 'delete' ? $t('transactions.bulk.unmarkDelete') || 'Restore' : $t('transactions.bulk.markDelete') || 'Mark for deletion'),
            onClick: (row: DraftRow) => {
                if (row.id != null) {
                    // Existing row: toggle delete state
                    markDelete(row.tempId);
                } else {
                    // New draft: just remove from batch
                    removeRow(row.tempId);
                }
            },
            variant: 'danger' as const,
        },
        {
            id: 'remove-from-batch',
            icon: X,
            label: () => $t('transactions.bulk.removeFromBatch') || 'Remove from batch',
            onClick: (row: DraftRow) => removeRow(row.tempId),
            visible: (row: DraftRow) => !!row._addedViaPicker && deriveStatus(row) !== 'new',
        },
        {
            id: 'reset',
            icon: Undo2,
            label: () => $t('transactions.bulk.resetRow'),
            onClick: (row: DraftRow) => resetRow(row.tempId),
            visible: (row: DraftRow) => !!row.original && (deriveStatus(row) === 'edited' || deriveStatus(row) === 'delete'),
        },
    ]);

    // =========================================================================
    // Issue → row navigation
    // =========================================================================

    function jumpToIssue(issue: ValidationIssue) {
        if (issue.index < 0) return; // broker-level error, no specific row
        const draft = drafts[issue.index];
        if (!draft) return;
        tableRef?.navigateToRowId(draft.tempId);
    }

    // =========================================================================
    // Toolbar chips
    // =========================================================================

    // Bugfix-4 §U16: validate chip removed — banners are the single source
    // of truth. Footer keeps only an inline "Validating…" indicator.

    // All drafts are visible (no more _hidden partner rows)
    let visibleDrafts = $derived(drafts);

    let newCount = $derived(visibleDrafts.filter((d) => deriveStatus(d) === 'new').length);
    let editedCount = $derived(visibleDrafts.filter((d) => deriveStatus(d) === 'edited').length);
    let deleteCount = $derived(visibleDrafts.filter((d) => deriveStatus(d) === 'delete').length);
    /** B23: true when at least one paired row is marked for deletion — show split hint. */
    let hasPairedDelete = $derived(visibleDrafts.some((d) => deriveStatus(d) === 'delete' && d._partnerId != null));
    let actionCount = $derived(newCount + editedCount + deleteCount);
    let commitDisabled = $derived(committing || drafts.length === 0 || actionCount === 0);
    let commitLabel = $derived(committing ? $t('common.saving') : $t('transactions.bulk.commitAll'));

    // -------------------------------------------------------------------------
    // Nested FormModal (Bugfix-5 §A4): "+ Add row" + row-action "Edit single".
    // -------------------------------------------------------------------------
    let formOpen = $state(false);
    let formMode = $state<'create' | 'edit'>('create');
    let formInitial = $state<TXReadItem | null>(null);
    /** C1-fix: injected partner row for paired drafts (avoids API fetch). */
    let formPartnerRow = $state<TXReadItem | null>(null);
    /** Set to a tempId when the FormModal is editing an existing draft row.
     *  When null, a successful Save = push as a brand-new row. */
    let formEditingTempId = $state<string | null>(null);
    /** Bug15-fix: monotonic counter incremented on every open to guarantee
     *  the FormModal's $effect re-fires even when `open` stays `true`. */
    let formKey = $state(0);

    // PickerModal (Plan B Step 9): "Search & add" existing DB transactions.
    let pickerOpen = $state(false);
    let pickerExcludeIds = $derived(new Set(drafts.filter((d) => d.id != null).map((d) => d.id!)));
    // PickerModal reads from txStore directly (Plan C Step 2)

    function openPicker() {
        pickerOpen = true;
    }
    function handlePickerAdd(rows: TXReadItem[]) {
        const existing = new Set(drafts.filter((d) => d.id != null).map((d) => d.id!));
        const newDrafts: DraftRow[] = [];
        for (const r of rows) {
            if (existing.has(r.id)) continue;
            existing.add(r.id);
            const d = emptyDraft();
            d.id = r.id;
            d.status = 'original';
            d.original = r;
            d._addedViaPicker = true;
            d.broker_id = r.broker_id;
            d.asset_id = r.asset_id ?? null;
            d.type = r.type as TransactionTypeCode;
            d.date = r.date;
            d.quantity = r.quantity;
            d.cash = r.cash ?? null;
            d.tags = r.tags ?? [];
            d.description = r.description ?? '';
            d.asset_event_id = r.asset_event_id ?? null;
            d.cost_basis_override = r.cost_basis_override ?? '';
            d.created_at = r.created_at;
            d.updated_at = r.updated_at;
            newDrafts.push(d);
        }
        // Collapse paired rows so only the "from" half is visible
        const collapsed = collapsePairedDrafts(newDrafts);
        drafts = [...drafts, ...collapsed];
        pickerOpen = false;
    }

    /** Aggregated tag suggestions: union of tags currently in any draft +
     *  any tag in the initialRows snapshot + the parent-supplied
     *  `availableTags` (sourced from the loaded transactions table). Drives
     *  the autocomplete in the nested FormModal's tag field (Bugfix-5 §U20
     *  client-side MVP). */
    let aggregatedTags = $derived.by<string[]>(() => {
        const seen = new Set<string>(availableTags);
        for (const d of drafts) for (const tg of d.tags ?? []) if (tg) seen.add(tg);
        for (const r of initialRows) for (const tg of r.tags ?? []) if (tg) seen.add(tg);
        return [...seen].sort((a, b) => a.localeCompare(b));
    });

    function openAddRowForm() {
        formMode = 'create';
        formInitial = null;
        formPartnerRow = null;
        formEditingTempId = null;
        formKey++;
        formOpen = true;
    }

    /** B23 Step 4: intercept edit on deleted row — show confirm before restoring. */
    function handleEditRowClick(row: DraftRow) {
        if (deriveStatus(row) === 'delete') {
            confirmEditDeleteRow = row;
            confirmEditDeleteOpen = true;
            return;
        }
        openEditRowForm(row);
    }

    /** B23 Step 4: user confirmed restore-and-edit on a deleted row. */
    function confirmRestoreAndEdit() {
        if (!confirmEditDeleteRow) return;
        const target = drafts.find((d) => d.tempId === confirmEditDeleteRow!.tempId);
        if (target) {
            target.status = 'original';
            drafts = [...drafts];
        }
        const row = confirmEditDeleteRow;
        confirmEditDeleteOpen = false;
        confirmEditDeleteRow = null;
        openEditRowForm(row);
    }

    function openEditRowForm(row: DraftRow) {
        // When editing a 'new' draft, open in create mode so type stays editable;
        // formEditingTempId is still set so handleFormPushed patches (not adds).
        formMode = deriveStatus(row) === 'new' ? 'create' : 'edit';
        formInitial = draftToTxLike(row);
        formEditingTempId = row.tempId;
        // For paired drafts, get the partner from txStore (existing rows)
        // or synthesize from _partnerFormPayload (new pairs).
        let partnerTxLike: TXReadItem | null = null;
        if (row._partnerId != null) {
            const p = txStoreGet(row._partnerId);
            if (p) partnerTxLike = p;
        }
        formPartnerRow = partnerTxLike;
        formKey++;
        formOpen = true;
    }
    function handleFormPushed(payload: Record<string, unknown>) {
        const isDual = payload._dual === true;
        if (formEditingTempId != null) {
            // Patching an existing draft row
            if (isDual) {
                patchDualRowFromForm(formEditingTempId, payload);
            } else {
                patchRowFromForm(formEditingTempId, payload);
            }
        } else {
            // Adding a new draft row
            if (isDual) {
                addDualRowFromForm(payload);
            } else {
                addRowFromForm(payload);
            }
        }
        formOpen = false;
        formEditingTempId = null;
    }

    /** Add a paired draft row: single visible draft with partner payload stored. */
    function addDualRowFromForm(payload: Record<string, unknown>) {
        const items = payload._items as Record<string, unknown>[];
        if (!items || items.length < 2) {
            addRowFromForm(payload);
            return;
        }

        // "From" side — visible row
        const fromDraft = emptyDraft();
        applyFormPayload(fromDraft, items[0]);
        fromDraft.partnerBrokerId = (items[1].broker_id as number) ?? 0;
        fromDraft.partnerCash = (items[1].cash as DraftRow['partnerCash']) ?? null;
        fromDraft.partnerDate = (items[1].date as string) ?? fromDraft.date;
        // Store the full partner create payload for commit
        fromDraft._partnerFormPayload = items[1];

        drafts = [...drafts, fromDraft];
    }

    /** Patch a paired draft row: update visible draft + store partner payload. */
    function patchDualRowFromForm(tempId: string, payload: Record<string, unknown>) {
        const items = payload._items as Record<string, unknown>[];
        if (!items || items.length < 2) {
            patchRowFromForm(tempId, payload);
            return;
        }

        drafts = drafts.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d};
            applyFormPayload(merged, items[0]);
            // Update partner display data
            merged.partnerBrokerId = (items[1].broker_id as number) ?? 0;
            merged.partnerCash = (items[1].cash as DraftRow['partnerCash']) ?? null;
            merged.partnerDate = (items[1].date as string) ?? merged.date;
            // Store the full partner payload for commit diffing
            merged._partnerFormPayload = items[1];
            // Status 'edited' is derived automatically by deriveStatus() — no manual marking needed.
            return merged;
        });
    }

    // Cast to `never` is required because DataTable<T> is generic and Svelte 5
    // template attribute type-checking can't refine through the bind:this ref.
    // Doing this in script keeps the template free of `as` casts (parser-friendly).
    let tableRefForToggle = $derived(tableRef as never);
    let rowActionsForTable = $derived(rowActions as never);

    /** Row background tint by status for immediate visual recognition.
     *  Color is purely status-based — paired nature is visible from Da:/A: rendering. */
    function getRowClass(row: DraftRow): string {
        const st = deriveStatus(row);
        if (st === 'delete') return 'row-deleted';
        if (st === 'new') return 'row-appended';
        if (st === 'edited') return 'row-edited';
        return '';
    }

    /** R6-B.4: Bulk actions for selected rows. */
    let bulkDeleteSelected = $derived({
        id: 'delete-selected',
        icon: Trash2,
        label: () => $t('transactions.bulk.deleteSelected') || 'Delete selected',
        variant: 'danger' as const,
        onClick: (rows: DraftRow[]) => {
            for (const r of rows) {
                if (r.id != null) {
                    markDelete(r.tempId);
                } else {
                    removeRow(r.tempId);
                }
            }
        },
    });
    let bulkActionsForTable = $derived([bulkDeleteSelected] as never);

    /** Rows currently selected in the bulk DataTable (for inline toolbar). */
    let bulkTableSelectedRows = $state<DraftRow[]>([]);

    function handleBulkTableSelectionChange(selectedIds: string[]) {
        const idSet = new Set(selectedIds);
        bulkTableSelectedRows = drafts.filter((d) => idSet.has(d.tempId));
    }

    function executeBulkDeleteOnSelected() {
        for (const r of bulkTableSelectedRows) {
            if (r.id != null) {
                markDelete(r.tempId);
            } else {
                removeRow(r.tempId);
            }
        }
        tableRef?.clearSelection();
        bulkTableSelectedRows = [];
    }
</script>

<ModalBase {open} maxWidth="none" onRequestClose={requestClose} testId="tx-bulk-modal" allowOverflow={true} contentClass="max-w-[95vw] w-[95vw]">
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="tx-bulk-modal-root">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-bulk-title">
                📋 {$t('transactions.bulk.title', {values: {total: visibleDrafts.length}})}
                {#if actionCount > 0}
                    <span class="text-sm font-normal text-gray-500 dark:text-gray-400">
                        ({#if newCount > 0}<span class="text-emerald-600 dark:text-emerald-400">{newCount} {$t('transactions.bulk.stateNew')}</span>{/if}{#if newCount > 0 && (editedCount > 0 || deleteCount > 0)}
                            ·
                        {/if}{#if editedCount > 0}<span class="text-amber-600 dark:text-amber-400">{editedCount} {$t('transactions.bulk.stateEdit')}</span>{/if}{#if editedCount > 0 && deleteCount > 0}
                            ·
                        {/if}{#if deleteCount > 0}<span class="text-red-600 dark:text-red-400">{deleteCount} {$t('transactions.bulk.stateDel')}</span>{/if})
                    </span>
                {/if}
            </h2>
            <button class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" onclick={requestClose} data-testid="tx-bulk-close" aria-label="Close">
                <X size={20} />
            </button>
        </div>

        <!-- Banners -->
        <div class="px-5 pt-3 space-y-2 shrink-0">
            {#if formError}
                <TransactionResultBanner variant="error" title={`⛔ ${$t('transactions.bulk.rolledBackTitle')}`} subtitle={formError} dismissible ondismiss={() => (formError = null)} testId="tx-bulk-error" />
            {:else if commitFailed && issues.length > 0}
                <TransactionResultBanner variant="error" title={`⛔ ${$t('transactions.bulk.rolledBackTitle')}`} dismissible ondismiss={() => (commitFailed = false)} testId="tx-bulk-error">
                    {#if fieldIssues.length > 0}
                        <p class="font-semibold text-sm mt-1 mb-1">{$t('transactions.validate.issuesHeader')}</p>
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues">
                            {#each fieldIssues as issue}
                                <li>
                                    <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue">
                                        {$t('transactions.bulk.rowN', {values: {n: issue.index + 1}})}: {resolveIssueMessage(issue, $t, resolverCtx)}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left">
                            {#each balanceIssues as issue}
                                {@const resolvedRow = findRowForBalanceIssue(issue)}
                                <li>
                                    {#if resolvedRow >= 0}
                                        <button
                                            type="button"
                                            class="underline hover:opacity-80 text-left"
                                            onclick={() => {
                                                const d = drafts[resolvedRow];
                                                if (d) tableRef?.navigateToRowId(d.tempId);
                                            }}
                                        >
                                            {$t('transactions.bulk.rowN', {values: {n: resolvedRow + 1}})}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                        </button>
                                    {:else}
                                        {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                    {/if}
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </TransactionResultBanner>
            {/if}
            {#if showIssuesBanner && !formError && !commitFailed}
                <TransactionResultBanner variant="warning" title={`⚠️ ${$t('transactions.validate.issuesHeader')}`} dismissible ondismiss={() => (issuesDismissed = true)} testId="tx-bulk-issues-header">
                    {#if fieldIssues.length > 0}
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues">
                            {#each fieldIssues as issue}
                                <li>
                                    <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue">
                                        {$t('transactions.bulk.rowN', {values: {n: issue.index + 1}})}: {resolveIssueMessage(issue, $t, resolverCtx)}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm {fieldIssues.length > 0 ? 'mt-2' : ''} mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left">
                            {#each balanceIssues as issue}
                                {@const resolvedRow = findRowForBalanceIssue(issue)}
                                <li>
                                    {#if resolvedRow >= 0}
                                        <button
                                            type="button"
                                            class="underline hover:opacity-80 text-left"
                                            onclick={() => {
                                                const d = drafts[resolvedRow];
                                                if (d) tableRef?.navigateToRowId(d.tempId);
                                            }}
                                        >
                                            {$t('transactions.bulk.rowN', {values: {n: resolvedRow + 1}})}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                        </button>
                                    {:else}
                                        {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                    {/if}
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </TransactionResultBanner>
            {/if}
            {#if visibleDrafts.length > AUTO_VALIDATE_THRESHOLD}
                <InfoBanner variant="info">
                    <p data-testid="tx-bulk-auto-off">ⓘ {$t('transactions.validate.autoOff', {values: {n: visibleDrafts.length, threshold: AUTO_VALIDATE_THRESHOLD}})}</p>
                </InfoBanner>
            {/if}
            {#if hasPairedDelete}
                <InfoBanner variant="info">
                    <p data-testid="tx-bulk-split-hint">ℹ️ {$t('transactions.deleteModal.splitHint')}</p>
                </InfoBanner>
            {/if}
        </div>

        <!-- Toolbar (Bugfix-2 §U9: action buttons right-aligned, most important first
             from the right via flex-row-reverse).
             Bugfix-5 §A4: `+ Add row` re-introduced — opens a nested
             TransactionFormModal that pushes its draft into the grid (no
             commit) so the user gets the structured single-row UX while
             staying in the bulk batch. -->
        <div class="flex items-center gap-2 px-5 py-3 border-b border-gray-100 dark:border-slate-800 text-xs shrink-0">
            <!-- Left: search & add -->
            {#if txStoreCount() > 0}
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600"
                    onclick={openPicker}
                    data-testid="tx-bulk-picker"
                    title={$t('transactions.picker.searchAdd') || 'Search & add'}
                >
                    🔍 <span class="hidden sm:inline">{$t('transactions.picker.searchAdd') || 'Search & add'}</span>
                </button>
            {/if}

            <!-- Inline selection toolbar (when rows selected in DataTable) -->
            {#if bulkTableSelectedRows.length > 0}
                <div class="flex items-center gap-2 ml-2">
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2 py-1 rounded text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-[11px]"
                        onclick={() => {
                            tableRef?.clearSelection();
                            bulkTableSelectedRows = [];
                        }}
                    >
                        <span class="font-medium">{bulkTableSelectedRows.length}</span> <span class="hidden sm:inline">{$t('common.selected') || 'selected'}</span> <span class="opacity-60 ml-0.5">×</span>
                    </button>
                    {#if bulkTableSelectedRows.some((d) => (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete') && d.original)}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1 px-2 py-1 rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 text-[11px]"
                            onclick={() => {
                                for (const r of bulkTableSelectedRows) resetRow(r.tempId);
                            }}
                            title={$t('transactions.bulk.resetSelected') || 'Reset selected'}
                            data-testid="tx-bulk-reset-selected"
                        >
                            <Undo2 size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.resetSelected') || 'Reset'}</span>
                        </button>
                    {/if}
                    <button type="button" class="inline-flex items-center gap-1 px-2 py-1 rounded text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 text-[11px]" onclick={executeBulkDeleteOnSelected} title={$t('transactions.bulk.deleteSelected') || 'Delete selected'}>
                        <Trash2 size={12} /> <span class="hidden sm:inline">{$t('common.delete') || 'Delete'}</span>
                    </button>
                </div>
            {/if}

            <!-- Right: actions -->
            <div class="ml-auto flex flex-row-reverse items-center gap-2 flex-wrap">
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={openAddRowForm} data-testid="tx-bulk-add-row" title={$t('transactions.bulk.addRow') || 'Add row'}>
                    <Plus size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.addRow') || 'Add row'}</span>
                </button>
                {#if visibleDrafts.some((d) => (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete') && d.original)}
                    <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={resetAll} data-testid="tx-bulk-reset-all" title={$t('transactions.bulk.resetAll')}>
                        <Undo2 size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.resetAll')}</span>
                    </button>
                {/if}
                <ColumnVisibilityToggle tableRef={tableRefForToggle} />
            </div>
        </div>

        <!-- DataTable body -->
        <div class="flex-1 min-h-0 overflow-y-auto px-3 py-2" data-testid="tx-bulk-body">
            <DataTable
                bind:this={tableRef}
                data={visibleDrafts}
                {columns}
                getRowId={(d) => d.tempId}
                storageKey="tx-bulk-modal"
                enableSelection={true}
                enableColumnFilters={false}
                enablePagination={false}
                enableSorting={false}
                enableColumnVisibility={true}
                enableActions={true}
                rowActions={rowActionsForTable}
                bulkActions={bulkActionsForTable}
                onSelectionChange={handleBulkTableSelectionChange}
                stickyActions={false}
                {getRowClass}
                onRowDoubleClick={(row) => handleEditRowClick(row)}
            />
        </div>

        <!-- Footer (Bugfix-4 §U16: validate-now on the left, no duplicate chip
             /issue-count — the green/warning banners above are the single
             source of truth for validate state). -->
        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t border-gray-100 dark:border-slate-700 shrink-0 text-xs">
            <div class="flex items-center gap-2 flex-wrap">
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={() => scheduler.trigger('manual')} data-testid="tx-bulk-validate-now" title={$t('transactions.validate.now')}>
                    ⚡ <span class="hidden sm:inline">{$t('transactions.validate.now')}</span>
                </button>
                {#if scheduler.state.isValidating}
                    <span class="text-[11px] text-gray-500 dark:text-gray-400" data-testid="tx-bulk-validating">{$t('transactions.validate.validating')}</span>
                {:else if isFreshlyValid && !formError && !commitFailed}
                    <span class="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1" data-testid="tx-bulk-valid">
                        <Check size={14} />
                        {$t('transactions.validate.ok')}
                    </span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 inline-flex items-center gap-1.5" onclick={requestClose} data-testid="tx-bulk-cancel" title={$t('common.cancel')}
                    ><X size={15} /> <span class="hidden sm:inline">{$t('common.cancel')}</span></button
                >
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50 inline-flex items-center gap-1.5" disabled={commitDisabled} onclick={commit} data-testid="tx-bulk-commit" title={commitLabel}>
                    <Save size={15} /> <span class="hidden sm:inline">{commitLabel}</span>
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

<!-- B23 Step 4: confirm restore-and-edit on a row marked for deletion. -->
<ConfirmModal
    open={confirmEditDeleteOpen}
    title={$t('transactions.bulk.confirmEditDelete') || 'Transaction marked for deletion'}
    message={$t('transactions.bulk.confirmEditDeleteMessage') || 'This transaction is marked for deletion. Do you want to restore it and edit it instead?'}
    confirmText={$t('transactions.bulk.restoreAndEdit') || 'Restore & Edit'}
    cancelText={$t('common.cancel')}
    warning
    onConfirm={confirmRestoreAndEdit}
    onCancel={() => {
        confirmEditDeleteOpen = false;
        confirmEditDeleteRow = null;
    }}
    zIndex={70}
/>

<!-- Bugfix-5 §A4: nested single-row form. `commitOnSave={false}` makes the
     Save button push the collected draft back to the bulk grid instead of
     committing to the backend; `unlockImmutable={true}` lets the user change
     `type` and `broker` even when editing an existing draft (deep-edit). -->
<TransactionFormModal
    open={formOpen}
    mode={formMode}
    initialRow={formInitial}
    injectedPartnerRow={formPartnerRow}
    commitOnSave={false}
    unlockImmutable={formMode === 'edit'}
    availableTags={aggregatedTags}
    zIndex={70}
    openKey={formKey}
    getBulkContext={() => getBulkContextExcluding(formEditingTempId)}
    onClose={() => {
        formOpen = false;
        formEditingTempId = null;
        formPartnerRow = null;
    }}
    onPushDraft={handleFormPushed}
/>

<!-- Plan B Step 9: PickerModal for adding existing DB transactions -->
<TransactionPickerModal open={pickerOpen} excludeIds={pickerExcludeIds} onAdd={handlePickerAdd} onClose={() => (pickerOpen = false)} />
