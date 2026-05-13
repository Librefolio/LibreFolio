<!--
  TransactionBulkModal.svelte — Unified bulk editor for transactions.

  Built on top of `DataTable.svelte`. Each visible row is a `PendingOp`:
  - op='create' → new draft, committed as CREATE
  - op='edit' + markedDelete=false → DB row (skipped if unchanged, UPDATE if edited)
  - op='edit' + markedDelete=true → DB row marked for deletion, committed as DELETE

  Status is DERIVED by `deriveStatus()` — never set manually:
  - 'new' = op='create'
  - 'original' = op='edit', fields unchanged vs txStore
  - 'edited' = op='edit', fields differ from txStore
  - 'delete' = op='edit' + markedDelete

  Originals are NEVER copied — `txStoreGet(op.txId)` is the single source of truth.

  Validation: 100% server-side via POST /transactions/validate. Auto-validate
  is debounced (1 s) + idle-fire (60 s) when N ≤ 50; above that threshold only
  the manual `⚡ Validate now` button works (toolbar shows ⓘ hint).

  Commit: POST /transactions/commit with creates + updates + deletes. On
  `committed=false` the modal stays open with a persistent banner.

  Architecture: Plan C3 — PendingOp refactor (2026-05-11).
-->
<script lang="ts">
    import {onDestroy, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {X, Plus, Pencil, Copy, Trash2, Check, Undo2, Save, Unlink, Link2} from 'lucide-svelte';

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
    import {findPromoteMatch} from '$lib/stores/transactionTypeStore';
    import PromoteMergeModal from './PromoteMergeModal.svelte';
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
    export type WorkspaceIntent = {action: 'create'} | {action: 'edit'; txIds: number[]} | {action: 'delete'; txIds: number[]} | {action: 'clone'; txIds: number[]};

    /** Fields displayed & editable in the grid — pure data, no metadata. */
    interface DraftFields {
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
    }

    /** Partner display data for paired rendering (Da:/A: columns). */
    interface PartnerDisplay {
        partnerId?: number;
        partnerBrokerId?: number;
        partnerCash?: {code: string; amount: string} | null;
        partnerDate?: string;
        /** Full partner payload from FormModal (TxFields for type-safe diffing). */
        partnerPayload?: TxFields | null;
    }

    /** Pending operation — one per visible row in the BulkModal grid.
     *  Tagged union: 'create' for new rows, 'edit' for existing DB rows. */
    type PendingOp = ({op: 'create'; link_uuid: string | null} | {op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean}) & {tempId: string; fields: DraftFields} & PartnerDisplay;

    interface Props {
        open: boolean;
        intent?: WorkspaceIntent;
        availableTags?: string[];
        onClose: () => void;
        onCommitted?: (resp: unknown) => void;
    }

    let {open, intent, availableTags = [], onClose, onCommitted}: Props = $props();

    const AUTO_VALIDATE_THRESHOLD = 50;

    /** Client-side mirror of backend SPLIT_TYPE_MAP. */
    const SPLIT_TYPE_MAP: Record<string, [string, string]> = {
        TRANSFER: ['ADJUSTMENT', 'ADJUSTMENT'],
        CASH_TRANSFER: ['WITHDRAWAL', 'DEPOSIT'],
        FX_CONVERSION: ['WITHDRAWAL', 'DEPOSIT'],
    };

    // =========================================================================
    // Helpers
    // =========================================================================

    function todayIso(): string {
        return new Date().toISOString().slice(0, 10);
    }

    /** Default DraftFields for a brand-new transaction. */
    function defaultFields(): DraftFields {
        const brokers = getAllBrokers();
        const defaultBroker = brokers.length === 1 ? brokers[0].id : 0;
        return {
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
        };
    }

    /** Create an empty 'create' PendingOp. */
    function createOpEmpty(): PendingOp {
        return {op: 'create', tempId: generateUUID(), fields: defaultFields(), link_uuid: null};
    }

    /** Extract display-ready DraftFields from a TXReadItem (auto-sign applied). */
    function fieldsFromTx(tx: TXReadItem): DraftFields {
        const rule = getTypeRule(tx.type);
        let qty = tx.quantity;
        if (rule.quantityRule === 'negative' && Number(qty) < 0) qty = String(Math.abs(Number(qty)));
        let cash = tx.cash ? {code: tx.cash.code, amount: tx.cash.amount} : null;
        if (cash && rule.cashSign === 'negative' && Number(cash.amount) < 0) {
            cash = {code: cash.code, amount: String(Math.abs(Number(cash.amount)))};
        }
        return {
            broker_id: tx.broker_id,
            asset_id: tx.asset_id ?? null,
            type: tx.type as TransactionTypeCode,
            date: tx.date,
            quantity: qty,
            cash,
            tags: [...(tx.tags ?? [])],
            description: tx.description ?? '',
            asset_event_id: tx.asset_event_id ?? null,
            cost_basis_override: tx.cost_basis_override ?? '',
        };
    }

    /** Create 'edit' PendingOp from DB transaction (reads txStore, zero copies). */
    function editOpFromTx(txId: number, opts?: {markedDelete?: boolean; addedViaPicker?: boolean}): PendingOp {
        const tx = txStoreGet(txId)!;
        return {op: 'edit', tempId: generateUUID(), txId, fields: fieldsFromTx(tx), markedDelete: opts?.markedDelete ?? false, addedViaPicker: opts?.addedViaPicker};
    }

    /** Create 'create' PendingOp by cloning from a TXReadItem. */
    function createOpFromClone(tx: TXReadItem, linkUuid?: string | null): PendingOp {
        const fields = fieldsFromTx(tx);
        fields.date = todayIso();
        const rule = getTypeRule(tx.type);
        if (rule.quantityRule === 'zero') fields.quantity = '0';
        return {op: 'create', tempId: generateUUID(), fields, link_uuid: linkUuid ?? null};
    }

    /** Get DB id from PendingOp (undefined for creates). */
    function opTxId(op: PendingOp): number | undefined {
        return op.op === 'edit' ? op.txId : undefined;
    }

    // =========================================================================
    // State
    // =========================================================================

    let ops = $state<PendingOp[]>([]);
    let issues = $state<ValidationIssue[]>([]);
    let formError = $state<string | null>(null);
    let commitFailed = $state(false);
    let committing = $state(false);
    /** Anti-bounce: track last commit draft key + timestamp. */
    let lastCommitDraftKey = $state('');
    let lastCommitAt = $state(0);
    const COMMIT_ANTI_BOUNCE_MS = 10000;
    let tableRef = $state<DataTable<PendingOp> | undefined>(undefined);
    /** Accumulated splits for saved paired TXs (sent in batch.splits). */
    let pendingSplits = $state<{id: number}[]>([]);
    /** Accumulated promotes for saved TXs (sent in batch.promotes). */
    let pendingPromotes = $state<{id_a?: number; id_b?: number; link_uuid_a?: string; link_uuid_b?: string; resolved_fields?: Record<string, unknown>}[]>([]);
    /** Promote merge modal state. */
    let promoteMergeOpen = $state(false);
    let promoteMergeData = $state<{txA: any; txB: any; targetTypeLabel: string; opA: PendingOp; opB: PendingOp} | null>(null);

    // =========================================================================
    // C6 — Promote Suggest (DB + local candidates)
    // =========================================================================
    let suggestFromDB = $state<Map<number, Array<{id: number; broker_id: number; date: string; type: string}>>>(new Map());
    let suggestTimer: ReturnType<typeof setTimeout> | null = null;
    /** Last JSON key sent to promote-suggest — avoids redundant calls. */
    let lastSuggestKey = '';

    /** Snapshot of `ops` at modal-open time, used to detect unsaved changes
     *  for the close-confirmation guard (Bugfix-3 §C11). */
    let initialOpsKey = $state('');
    let confirmCloseOpen = $state(false);
    /** B23 Step 4: confirm edit on a row marked for deletion. */
    let confirmEditDeleteOpen = $state(false);
    let confirmEditDeleteRow = $state<PendingOp | null>(null);

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
                const sharedLinkUuid = resolved.length === 2 && resolved[0].type === resolved[1].type ? generateUUID() : null;
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
        throw new Error('BulkModal: intent prop is required');
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
            pendingSplits = [];
            pendingPromotes = [];
            promoteMergeOpen = false;
            promoteMergeData = null;
            suggestFromDB = new Map();
            lastSuggestKey = '';
            if (suggestTimer) {
                clearTimeout(suggestTimer);
                suggestTimer = null;
            }
            // When no initial rows → empty grid; user adds rows via nested FormModal.
            let next: PendingOp[] = [];
            if (rows.length > 0) {
                if (initSt === 'delete') {
                    next = rows.filter((r) => r.id > 0).map((r) => editOpFromTx(r.id, {markedDelete: true}));
                } else {
                    next = rows.map((r) => (r.id > 0 ? editOpFromTx(r.id) : createOpFromClone(r, (r as any).link_uuid)));
                }
            }

            // Collapse paired rows: keep only the "from" half with partner
            // metadata populated. No dependency on isTypesLoaded — pair detection
            // uses related_transaction_id (not getTypeRule().requiresPair).
            next = collapsePairedOps(next);

            // B4-fix: Build ops eagerly but only assign after types are loaded,
            // because getTypeRule() returns FALLBACK_RULE (requiresPair=false)
            // until _ruleMap is populated → paired rows render as singles.
            if (isTypesLoaded()) {
                // Fast path: types already cached → assign + auto-open immediately.
                ops = next;
                initialOpsKey = serializeOps(next);
                scheduleAutoOpen(autoForm, next);
            } else {
                // Slow path: keep ops empty so DataTable doesn't render
                // with FALLBACK_RULE. Ops will be assigned after Promise.all.
                ops = [];
                initialOpsKey = '';
                if (rows.length === 0) {
                    queueMicrotask(() => {
                        formOpen = true;
                        formMode = 'create';
                        formInitial = null;
                        formPartnerRow = null;
                        formEditingTempId = null;
                    });
                }
            }
        });
        void (async () => {
            await Promise.all([ensureBrokersLoaded(), ensureCurrenciesLoaded($currentLanguage), ensureAssetsLoaded(), ensureTypesLoaded()]);
            untrack(() => {
                // B4-fix: if ops was deferred (slow path), rebuild + assign now.
                if (ops.length === 0 && rows.length > 0) {
                    let next2: PendingOp[] = [];
                    if (initSt === 'delete') {
                        next2 = rows.filter((r) => r.id > 0).map((r) => editOpFromTx(r.id, {markedDelete: true}));
                    } else {
                        next2 = rows.map((r) => (r.id > 0 ? editOpFromTx(r.id) : createOpFromClone(r, (r as any).link_uuid)));
                    }
                    next2 = collapsePairedOps(next2);
                    ops = next2;
                    initialOpsKey = serializeOps(next2);
                }
                if (!formOpen) {
                    scheduleAutoOpen(autoForm, ops);
                }
            });
        })();
    });

    /** Schedule auto-open of the nested FormModal based on the mode. */
    function scheduleAutoOpen(autoForm: string | null, opArr: PendingOp[]) {
        if (autoForm === 'edit' && opArr.length > 0) {
            queueMicrotask(() => openEditRowForm(opArr[0]));
        } else if (autoForm === 'create' && opArr.length > 0) {
            // Clone: row is 'new' so openEditRowForm uses create mode
            queueMicrotask(() => openEditRowForm(opArr[0]));
        } else if (opArr.length === 0) {
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
    function serializeOps(rows: PendingOp[]): string {
        return JSON.stringify(
            rows.map((d) => {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const {tempId: _tempId, ...rest} = d;
                return rest;
            }),
        );
    }

    function hasUnsavedChanges(): boolean {
        return serializeOps(ops) !== initialOpsKey;
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
        ops = [...ops, createOpEmpty()];
    }
    void addRow;

    /** Convert a PendingOp to a TXReadItem-shaped object so it can be fed back to
     *  TransactionFormModal as `initialRow`. We reuse the BulkModal's in-flight
     *  draft state, NOT a server-persisted row, so id/timestamps are synthetic. */
    function opToTxLike(d: PendingOp): TXReadItem {
        const id = opTxId(d);
        const orig = id != null ? txStoreGet(id) : undefined;
        return {
            id: id ?? 0,
            broker_id: d.fields.broker_id,
            asset_id: d.fields.asset_id,
            type: d.fields.type,
            date: d.fields.date,
            quantity: d.fields.quantity,
            cash: d.fields.cash,
            // C1-fix: if this is a paired row, expose the partner id so FormModal
            // opens in dual mode. For 'new' drafts _partnerId is undefined, so we
            // use a sentinel -1 to signal "pair present, fetch locally".
            related_transaction_id: d.partnerId ?? (d.partnerBrokerId != null ? -1 : null),
            tags: d.fields.tags,
            description: d.fields.description,
            cost_basis_override: d.fields.cost_basis_override || null,
            asset_event_id: d.fields.asset_event_id,
            created_at: orig?.created_at,
            updated_at: orig?.updated_at,
        };
    }

    /** Populate partner display metadata on a draft from txStore. */
    function populatePartnerDisplay(d: PendingOp): void {
        const origTx = d.op === 'edit' ? txStoreGet(d.txId) : undefined;
        const pid = origTx?.related_transaction_id ?? d.partnerId;
        if (pid == null) return;
        const partner = txStoreGet(pid);
        if (!partner) return;
        d.partnerId = partner.id;
        d.partnerBrokerId = partner.broker_id;
        d.partnerCash = partner.cash ?? null;
        d.partnerDate = partner.date;
    }

    /** Collapse paired drafts in an array: detect partners via
     *  related_transaction_id, keep the "from" half, set partner metadata,
     *  remove the "to" half. For solo drafts with a partner in txStore,
     *  populate partner display data from the store. */
    function collapsePairedOps(opArr: PendingOp[]): PendingOp[] {
        const idToIdx = new Map<number, number>();
        opArr.forEach((d, i) => {
            {
                const _id = opTxId(d);
                if (_id != null) idToIdx.set(_id, i);
            }
        });
        const toRemove = new Set<number>();
        for (let i = 0; i < opArr.length; i++) {
            if (toRemove.has(i)) continue;
            const d = opArr[i];
            const partnerId = (d.op === 'edit' ? txStoreGet(d.txId) : undefined)?.related_transaction_id;
            if (partnerId == null) continue;
            const pIdx = idToIdx.get(partnerId);
            if (pIdx == null || pIdx === i || toRemove.has(pIdx)) continue;
            const partner = opArr[pIdx];
            // Determine from/to: "from" = negative cash (giver)
            const cashAmt = Number((d.op === 'edit' ? txStoreGet(d.txId) : undefined)?.cash?.amount ?? 0);
            const partnerCashAmt = Number((partner.op === 'edit' ? txStoreGet(partner.txId) : undefined)?.cash?.amount ?? 0);
            let fromIdx = i,
                toIdx = pIdx;
            if (cashAmt > 0 && partnerCashAmt <= 0) {
                fromIdx = pIdx;
                toIdx = i;
            } else if (cashAmt === 0 && partnerCashAmt === 0) {
                if (Number((d.op === 'edit' ? txStoreGet(d.txId) : undefined)?.quantity ?? 0) > 0) {
                    fromIdx = pIdx;
                    toIdx = i;
                }
            }
            const fromDraft = opArr[fromIdx];
            const toDraft = opArr[toIdx];
            fromDraft.partnerId = opTxId(toDraft);
            fromDraft.partnerBrokerId = toDraft.fields.broker_id;
            fromDraft.partnerCash = toDraft.fields.cash;
            fromDraft.partnerDate = toDraft.fields.date;
            toRemove.add(toIdx);
        }
        const result = opArr.filter((_, i) => !toRemove.has(i));
        // For remaining drafts with partner not in batch, populate from txStore
        for (const d of result) {
            if ((d.op === 'edit' ? txStoreGet(d.txId) : undefined)?.related_transaction_id != null && d.partnerId == null) {
                populatePartnerDisplay(d);
            }
        }
        return result;
    }

    /** Apply the form-collected payload to a brand-new draft row. */
    function addRowFromForm(payload: Record<string, unknown>) {
        const next = createOpEmpty();
        applyFormPayload(next.fields, payload);
        if (typeof payload.link_uuid === 'string' && next.op === 'create') (next as any).link_uuid = payload.link_uuid;
        ops = [...ops, next];
    }

    /** Apply the form-collected payload to an existing draft (deep-edit). */
    function patchRowFromForm(tempId: string, payload: Record<string, unknown>) {
        ops = ops.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d, fields: {...d.fields}};
            applyFormPayload(merged.fields, payload);
            return merged;
        });
    }

    function applyFormPayload(target: DraftFields, p: Record<string, unknown>) {
        if (typeof p.broker_id === 'number') target.broker_id = p.broker_id;
        if (typeof p.type === 'string') target.type = p.type as TransactionTypeCode;
        if (typeof p.date === 'string') target.date = p.date;
        if (typeof p.quantity === 'string') target.quantity = p.quantity;
        target.asset_id = (p.asset_id as number | null | undefined) ?? null;
        target.cash = (p.cash as DraftFields['cash']) ?? null;
        target.tags = Array.isArray(p.tags) ? (p.tags as string[]) : [];
        target.description = typeof p.description === 'string' ? p.description : '';
        target.asset_event_id = (p.asset_event_id as number | null | undefined) ?? null;
        target.cost_basis_override = typeof p.cost_basis_override === 'string' ? p.cost_basis_override : '';
    }

    // =========================================================================
    // Pair operations + row lifecycle
    // =========================================================================

    function removeRow(tempId: string) {
        ops = ops.filter((d) => d.tempId !== tempId);
    }

    /** Mark an existing row for deletion (toggle). */
    function markDelete(tempId: string) {
        ops = ops.map((d) => {
            if (d.tempId !== tempId) return d;
            if (d.op !== 'edit') return d; // can't mark-delete a create — just remove it
            return {...d, markedDelete: !(d as any).markedDelete};
        });
    }

    /** Clone a row as a new row. */
    function cloneRow(tempId: string) {
        const src = ops.find((d) => d.tempId === tempId);
        if (!src) return;
        const clone: PendingOp = {
            op: 'create',
            tempId: generateUUID(),
            fields: {...src.fields, date: todayIso()},
            link_uuid: src.op === 'create' && src.link_uuid ? generateUUID() : null,
            partnerBrokerId: src.partnerBrokerId,
            partnerCash: src.partnerCash,
            partnerDate: src.partnerDate,
        };
        ops = [...ops, clone];
    }

    function resetRow(tempId: string) {
        ops = ops.map((d) => {
            if (d.tempId !== tempId || d.op !== 'edit') return d;
            const reset = editOpFromTx(d.txId, {addedViaPicker: d.addedViaPicker});
            populatePartnerDisplay(reset);
            return reset;
        });
    }

    function resetAll() {
        ops = ops.map((d) => {
            if (d.op !== 'edit') return d;
            const reset = editOpFromTx(d.txId, {addedViaPicker: d.addedViaPicker});
            populatePartnerDisplay(reset);
            return reset;
        });
    }

    /** Split a paired row in the BulkModal.
     *  Saved paired → accumulate in pendingSplits for batch commit.
     *  New paired (link_uuid shared) → local transformation only. */
    function handleSplitRow(row: PendingOp) {
        if (row.op === 'edit' && row.partnerId != null) {
            // Case A: Saved paired → backend split
            const splitTypes = SPLIT_TYPE_MAP[row.fields.type];
            if (!splitTypes) return;
            pendingSplits = [...pendingSplits, {id: (row as any).txId}];
            const [fromType, toType] = splitTypes;
            // Determine from/to by sign
            const cashAmt = Number(row.fields.cash?.amount ?? 0);
            const qty = Number(row.fields.quantity ?? 0);
            const isFrom = row.fields.type === 'TRANSFER' ? qty < 0 : cashAmt < 0;
            row.fields.type = (isFrom ? fromType : toType) as TransactionTypeCode;
            // Clear partner display
            row.partnerId = undefined;
            row.partnerBrokerId = undefined;
            row.partnerCash = undefined;
            row.partnerDate = undefined;
            row.partnerPayload = undefined;
            ops = [...ops];
        } else if (row.op === 'create' && row.link_uuid) {
            // Case B: New paired (link_uuid shared) → local transformation
            const partner = ops.find((o) => o !== row && o.op === 'create' && (o as any).link_uuid === row.link_uuid);
            if (!partner) return;
            const splitTypes = SPLIT_TYPE_MAP[row.fields.type];
            if (!splitTypes) return;
            const [fromType, toType] = splitTypes;
            // Determine from/to by sign
            const cashAmt = Number(row.fields.cash?.amount ?? 0);
            const qty = Number(row.fields.quantity ?? 0);
            const isFrom = row.fields.type === 'TRANSFER' ? qty < 0 : cashAmt < 0;
            row.fields.type = (isFrom ? fromType : toType) as TransactionTypeCode;
            partner.fields.type = (isFrom ? toType : fromType) as TransactionTypeCode;
            (row as any).link_uuid = null;
            (partner as any).link_uuid = null;
            // Clear partner display on both
            for (const o of [row, partner]) {
                o.partnerId = undefined;
                o.partnerBrokerId = undefined;
                o.partnerCash = undefined;
                o.partnerDate = undefined;
                o.partnerPayload = undefined;
            }
            ops = [...ops];
        }
    }

    // =========================================================================
    // Sanitizers
    // =========================================================================

    // -----------------------------------------------------------------
    // Shared helpers for collectCreate / collectUpdate
    // -----------------------------------------------------------------

    function collectCreate(d: PendingOp): Record<string, unknown> {
        const rule = getTypeRule(d.fields.type);
        return buildCreatePayload(opToTxFields(d), rule);
    }

    function collectUpdate(d: PendingOp): Record<string, unknown> | null {
        if (d.op !== 'edit') return null;
        const orig = txStoreGet(d.txId);
        if (!orig) return null;
        const rule = getTypeRule(d.fields.type);
        const origRule = getTypeRule(orig.type as TransactionTypeCode);
        return buildUpdateDiff(opToTxFields(d), orig as unknown as TxOriginal, rule, origRule);
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
        for (const d of ops) {
            if (d.tempId === excludeTempId) continue;
            const st = deriveStatus(d);
            if (st === 'new') {
                creates.push(collectCreate(d));
                if (d.partnerPayload) creates.push(d.partnerPayload as unknown as Record<string, unknown>);
            } else if (st === 'edited') {
                const upd = collectUpdate(d);
                if (upd && Object.keys(upd).length > 1) updates.push(upd);
                if (d.partnerPayload && d.partnerId != null) {
                    const partnerOrig = txStoreGet(d.partnerId);
                    if (partnerOrig) {
                        const partnerUpd = diffDualItem(d.partnerPayload as unknown as Record<string, unknown>, partnerOrig as unknown as TxOriginal);
                        if (Object.keys(partnerUpd).length > 1) updates.push(partnerUpd);
                    }
                }
            } else if (st === 'delete' && d.op === 'edit') {
                deletes.push((d as any).txId);
                if (d.partnerId != null) deletes.push(d.partnerId);
            }
        }
        return {creates, updates, deletes};
    }

    /** Convert a PendingOp to the shared TxFields interface. */
    function opToTxFields(d: PendingOp): TxFields {
        return {...d.fields, link_uuid: d.op === 'create' ? d.link_uuid : null};
    }

    /** Derive the effective display status of a draft row.
     *  'new' and 'delete' are explicit. 'edited' is derived from diff vs original.
     *  This eliminates "edited falso" bugs — status is always truthful. */
    function deriveStatus(d: PendingOp): 'new' | 'edited' | 'original' | 'delete' {
        if (d.op === 'create') return 'new';
        if (d.op === 'edit' && d.markedDelete) return 'delete';
        // For existing rows: check whether fields differ from txStore original
        if (d.op !== 'edit') return 'original';
        const diff = collectUpdate(d);
        if (diff && Object.keys(diff).length > 1) return 'edited';
        // Also check partner changes
        if (d.partnerPayload && d.partnerId != null) {
            const partnerOrig = txStoreGet(d.partnerId);
            if (partnerOrig) {
                const partnerUpd = diffDualItem(d.partnerPayload as unknown as Record<string, unknown>, partnerOrig as unknown as TxOriginal);
                if (Object.keys(partnerUpd).length > 1) return 'edited';
            }
        }
        return 'original';
    }

    // =========================================================================
    // Validate scheduler
    // =========================================================================

    const scheduler = createValidateScheduler({
        enabled: () => ops.length > 0 && ops.length <= AUTO_VALIDATE_THRESHOLD && ops.some((d) => deriveStatus(d) !== 'delete' && isDraftReadyForValidation(d.fields as any)),
        draftKey: () => lastDraftKey,
        validateFn: async () => {
            if (ops.length === 0) {
                issues = [];
                lastValidatedDraftKey = lastDraftKey;
                issuesDismissed = false;
                return {issuesCount: 0};
            }
            // R6-B.4: build mixed payload matching commit logic
            const creates: Record<string, unknown>[] = [];
            const updates: Record<string, unknown>[] = [];
            const deletes: number[] = [];
            for (const d of ops) {
                const st = deriveStatus(d);
                if (st === 'new') {
                    creates.push(collectCreate(d));
                    if (d.partnerPayload) creates.push(d.partnerPayload as unknown as Record<string, unknown>);
                } else if (st === 'edited') {
                    const upd = collectUpdate(d);
                    if (upd && Object.keys(upd).length > 1) updates.push(upd);
                    // Partner update from dual-form edits
                    if (d.partnerPayload && d.partnerId != null) {
                        const partnerOrig = txStoreGet(d.partnerId);
                        if (partnerOrig) {
                            const partnerUpd = diffDualItem(d.partnerPayload as unknown as Record<string, unknown>, partnerOrig as unknown as TxOriginal);
                            if (Object.keys(partnerUpd).length > 1) updates.push(partnerUpd);
                        }
                    }
                } else if (st === 'delete' && d.op === 'edit') {
                    deletes.push((d as any).txId);
                    if (d.partnerId != null) deletes.push(d.partnerId);
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

    onDestroy(() => {
        scheduler.dispose();
        if (suggestTimer) clearTimeout(suggestTimer);
    });

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
            for (let i = ops.length - 1; i >= 0; i--) {
                if (ops[i].fields.broker_id === brokerId && ops[i].fields.asset_id === assetId) return i;
            }
        } else if (issue.code === 'balanceCashNegative') {
            const currency = p.currency as string;
            for (let i = ops.length - 1; i >= 0; i--) {
                if (ops[i].fields.broker_id === brokerId && ops[i].fields.cash?.code === currency) return i;
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
        const key = JSON.stringify(ops);
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

            for (const d of ops) {
                const st = deriveStatus(d);
                if (st === 'new') {
                    creates.push(collectCreate(d));
                    if (d.partnerPayload) creates.push(d.partnerPayload as unknown as Record<string, unknown>);
                } else if (st === 'edited') {
                    const upd = collectUpdate(d);
                    if (upd && Object.keys(upd).length > 1) updates.push(upd);
                    // Partner update from dual-form edits
                    if (d.partnerPayload && d.partnerId != null) {
                        const partnerOrig = txStoreGet(d.partnerId);
                        if (partnerOrig) {
                            const partnerUpd = diffDualItem(d.partnerPayload as unknown as Record<string, unknown>, partnerOrig as unknown as TxOriginal);
                            if (Object.keys(partnerUpd).length > 1) updates.push(partnerUpd);
                        }
                    }
                } else if (st === 'delete' && d.op === 'edit') {
                    deletes.push((d as any).txId);
                    if (d.partnerId != null) deletes.push(d.partnerId);
                }
                // 'original' rows are unchanged — skip
            }

            if (creates.length === 0 && updates.length === 0 && deletes.length === 0 && pendingSplits.length === 0 && pendingPromotes.length === 0) {
                onClose();
                return;
            }

            const payload: Record<string, unknown> = {};
            if (creates.length > 0) payload.creates = creates;
            if (updates.length > 0) payload.updates = updates;
            if (deletes.length > 0) payload.deletes = deletes;
            if (pendingSplits.length > 0) payload.splits = pendingSplits;
            if (pendingPromotes.length > 0) payload.promotes = pendingPromotes;

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
            pendingSplits = [];
            pendingPromotes = [];
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
    // DRY helpers for cell rendering
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

    let columns = $derived.by<ColumnDef<PendingOp>[]>(() => {
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
                    if (opTxId(row) == null) return {type: 'html', html: '—'};
                    const rule = getTypeRule(row.fields.type);
                    if (rule.requiresPair && row.partnerId != null) {
                        return {type: 'html', html: renderDualHtml(`#${opTxId(row)}`, `#${row.partnerId}`)};
                    }
                    return {type: 'html', html: `#${opTxId(row)}`};
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
                    const rule = getTypeRule(row.fields.type);
                    // Paired rows with different dates → Da:/A:
                    if (rule.requiresPair && row.partnerDate && row.partnerDate !== row.fields.date) {
                        return {type: 'html', html: renderDualHtml(row.fields.date, row.partnerDate)};
                    }
                    return {type: 'html', html: `<span class="font-mono text-sm text-gray-700 dark:text-gray-200">${row.fields.date}</span>`};
                },
            },
            {
                id: 'type',
                header: () => $t('transactions.table.type'),
                type: 'text',
                width: 155,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => ({type: 'html', html: renderTypeHtml(row.fields.type)}),
            },
            {
                id: 'asset',
                header: () => $t('transactions.table.asset'),
                type: 'text',
                width: 180,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    if (getTypeRule(row.fields.type).assetField === 'forbidden') {
                        return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                    }
                    return {type: 'html', html: renderAssetHtml(row.fields.asset_id)};
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
                    if (getTypeRule(row.fields.type).quantityMode === 'forbidden') {
                        return {type: 'html', html: '<span class="text-gray-400 italic">n/a</span>'};
                    }
                    const qty = row.fields.quantity ?? '0';
                    // H2-fix: paired rows with non-zero qty → show Da:/A: with signed values + emoji
                    const rule = getTypeRule(row.fields.type);
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
                    const rule = getTypeRule(row.fields.type);
                    if (rule.cashField === 'forbidden') {
                        return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                    }
                    // Paired row → show Da:/A: dual cash lines
                    if (rule.requiresPair && row.partnerCash !== undefined && row.partnerBrokerId != null) {
                        return {type: 'html', html: renderDualHtml(formatCashText(row.fields.cash), formatCashText(row.partnerCash))};
                    }
                    return {type: 'html', html: `<span class="text-sm">${formatCashText(row.fields.cash)}</span>`};
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
                    const rule = getTypeRule(row.fields.type);
                    // Paired row with different brokers → Da:/A:
                    if (rule.requiresPair && row.partnerBrokerId != null && row.partnerBrokerId !== row.fields.broker_id) {
                        return {type: 'html', html: renderDualHtml(renderBrokerHtml(row.fields.broker_id), renderBrokerHtml(row.partnerBrokerId))};
                    }
                    return {type: 'html', html: renderBrokerHtml(row.fields.broker_id)};
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
                    if (!row.fields.description) return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                    const escaped = row.fields.description.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    return {
                        type: 'html',
                        html: `<span class="text-xs text-gray-600 dark:text-gray-300 truncate block leading-tight">${escaped}</span>`,
                        tooltip: {text: row.fields.description, position: 'top', maxWidth: '400px'},
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
                    if (row.fields.tags.length === 0) return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                    const html = row.fields.tags
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
                cell: (row): CellContent => ({type: 'html', html: row.fields.cost_basis_override ? `<span class="font-mono text-xs">${row.fields.cost_basis_override}</span>` : '<span class="text-gray-400 italic">auto</span>'}),
            },
            {
                id: 'asset_event_id',
                header: () => $t('transactions.form.assetEvent'),
                type: 'text',
                width: 110,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({type: 'html', html: row.fields.asset_event_id != null ? `<span class="font-mono text-xs">#${row.fields.asset_event_id}</span>` : '<span class="text-gray-400">—</span>'}),
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
                    if (row.partnerId != null) return {type: 'html', html: `<code class="text-[10px] font-mono text-gray-400">↔ #${row.partnerId}</code>`};
                    if (row.partnerPayload != null) return {type: 'html', html: '<code class="text-[10px] font-mono text-indigo-400">↔ new</code>'};
                    if (row.op === 'create' && row.link_uuid) return {type: 'html', html: `<code class="text-[10px] font-mono text-gray-400">${row.op === 'create' ? row.link_uuid?.slice(0, 8) : ''}…</code>`};
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
                cell: (row): CellContent => ({type: 'html', html: (row.op === 'edit' ? txStoreGet(row.txId)?.created_at : undefined) ?? '—'}),
            },
            {
                id: 'updated_at',
                header: () => $t('common.updated'),
                type: 'date',
                width: 160,
                sortable: false,
                filterable: false,
                hiddenByDefault: true,
                cell: (row): CellContent => ({type: 'html', html: (row.op === 'edit' ? txStoreGet(row.txId)?.updated_at : undefined) ?? '—'}),
            },
        ] satisfies ColumnDef<PendingOp>[];
    });

    // =========================================================================
    // Row actions (remove / reset)
    // =========================================================================

    let rowActions = $derived([
        {
            id: 'edit-single',
            icon: Pencil,
            label: () => $t('transactions.bulk.editSingle') || 'Edit row',
            onClick: (row: PendingOp) => handleEditRowClick(row),
        },
        {
            id: 'clone',
            icon: Copy,
            label: () => $t('transactions.bulk.cloneRow') || 'Clone row',
            onClick: (row: PendingOp) => cloneRow(row.tempId),
        },
        {
            id: 'split',
            icon: Unlink,
            label: () => $t('transactions.actions.split') || 'Split pair',
            onClick: (row: PendingOp) => handleSplitRow(row),
            visible: (row: PendingOp) => {
                // Saved paired → backend split
                if (row.op === 'edit' && row.partnerId != null) return true;
                // New paired (link_uuid shared) → local split
                if (row.op === 'create' && row.link_uuid != null) {
                    return ops.some((o) => o !== row && o.op === 'create' && (o as any).link_uuid === row.link_uuid);
                }
                return false;
            },
        },
        {
            id: 'mark-delete',
            icon: Trash2,
            label: (row: PendingOp) => (deriveStatus(row) === 'delete' ? $t('transactions.bulk.unmarkDelete') || 'Restore' : $t('transactions.bulk.markDelete') || 'Mark for deletion'),
            onClick: (row: PendingOp) => {
                if (row.op === 'edit') {
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
            onClick: (row: PendingOp) => removeRow(row.tempId),
            visible: (row: PendingOp) => row.op === 'edit' && row.addedViaPicker && deriveStatus(row) !== 'new',
        },
        {
            id: 'reset',
            icon: Undo2,
            label: () => $t('transactions.bulk.resetRow'),
            onClick: (row: PendingOp) => resetRow(row.tempId),
            visible: (row: PendingOp) => row.op === 'edit' && (deriveStatus(row) === 'edited' || deriveStatus(row) === 'delete'),
        },
    ]);

    // =========================================================================
    // Issue → row navigation
    // =========================================================================

    function jumpToIssue(issue: ValidationIssue) {
        if (issue.index < 0) return; // broker-level error, no specific row
        const draft = ops[issue.index];
        if (!draft) return;
        tableRef?.navigateToRowId(draft.tempId);
    }

    // =========================================================================
    // Toolbar chips
    // =========================================================================

    // Bugfix-4 §U16: validate chip removed — banners are the single source
    // of truth. Footer keeps only an inline "Validating…" indicator.

    // All ops are visible (no more _hidden partner rows)
    let visibleOps = $derived(ops);

    let newCount = $derived(visibleOps.filter((d) => deriveStatus(d) === 'new').length);
    let editedCount = $derived(visibleOps.filter((d) => deriveStatus(d) === 'edited').length);
    let deleteCount = $derived(visibleOps.filter((d) => deriveStatus(d) === 'delete').length);
    /** B23: true when at least one paired row is marked for deletion — show split hint. */
    let hasPairedDelete = $derived(visibleOps.some((d) => deriveStatus(d) === 'delete' && d.partnerId != null));
    let actionCount = $derived(newCount + editedCount + deleteCount + pendingSplits.length + pendingPromotes.length);
    let commitDisabled = $derived(committing || ops.length === 0 || actionCount === 0);
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
    let pickerExcludeIds = $derived(new Set(ops.filter((d) => opTxId(d) != null).map((d) => opTxId(d)!)));
    // PickerModal reads from txStore directly (Plan C Step 2)

    function openPicker() {
        pickerOpen = true;
    }
    function handlePickerAdd(rows: TXReadItem[]) {
        const existing = new Set(ops.filter((d) => opTxId(d) != null).map((d) => opTxId(d)!));
        const newOps: PendingOp[] = [];
        for (const r of rows) {
            if (existing.has(r.id)) continue;
            existing.add(r.id);
            newOps.push(editOpFromTx(r.id, {addedViaPicker: true}));
        }
        const collapsed = collapsePairedOps(newOps);
        ops = [...ops, ...collapsed];
        pickerOpen = false;
    }

    /** Aggregated tag suggestions: union of tags in current ops +
     *  `availableTags` (sourced from the loaded transactions table). Drives
     *  the autocomplete in the nested FormModal's tag field (Bugfix-5 §U20
     *  client-side MVP). */
    let aggregatedTags = $derived.by<string[]>(() => {
        const seen = new Set<string>(availableTags);
        for (const d of ops) for (const tg of d.fields.tags ?? []) if (tg) seen.add(tg);
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
    function handleEditRowClick(row: PendingOp) {
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
        const target = ops.find((d) => d.tempId === confirmEditDeleteRow!.tempId);
        if (target) {
            if (target.op === 'edit') (target as any).markedDelete = false;
            ops = [...ops];
        }
        const row = confirmEditDeleteRow;
        confirmEditDeleteOpen = false;
        confirmEditDeleteRow = null;
        openEditRowForm(row);
    }

    function openEditRowForm(row: PendingOp) {
        // When editing a 'new' draft, open in create mode so type stays editable;
        // formEditingTempId is still set so handleFormPushed patches (not adds).
        formMode = deriveStatus(row) === 'new' ? 'create' : 'edit';
        formInitial = opToTxLike(row);
        formEditingTempId = row.tempId;
        // For paired drafts, get the partner from txStore (existing rows)
        // or synthesize from partnerPayload (new pairs).
        let partnerTxLike: TXReadItem | null = null;
        if (row.partnerId != null) {
            const p = txStoreGet(row.partnerId);
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
        const fromOp = createOpEmpty();
        applyFormPayload(fromOp.fields, items[0]);
        if (typeof items[0].link_uuid === 'string' && fromOp.op === 'create') (fromOp as any).link_uuid = items[0].link_uuid;
        fromOp.partnerBrokerId = (items[1].broker_id as number) ?? 0;
        fromOp.partnerCash = (items[1].cash as DraftFields['cash']) ?? null;
        fromOp.partnerDate = (items[1].date as string) ?? fromOp.fields.date;
        fromOp.partnerPayload = items[1] as unknown as TxFields;

        ops = [...ops, fromOp];
    }

    /** Patch a paired draft row: update visible draft + store partner payload. */
    function patchDualRowFromForm(tempId: string, payload: Record<string, unknown>) {
        const items = payload._items as Record<string, unknown>[];
        if (!items || items.length < 2) {
            patchRowFromForm(tempId, payload);
            return;
        }

        ops = ops.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d, fields: {...d.fields}};
            applyFormPayload(merged.fields, items[0]);
            merged.partnerBrokerId = (items[1].broker_id as number) ?? 0;
            merged.partnerCash = (items[1].cash as DraftFields['cash']) ?? null;
            merged.partnerDate = (items[1].date as string) ?? merged.fields.date;
            merged.partnerPayload = items[1] as unknown as TxFields;
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
    function getRowClass(row: PendingOp): string {
        const st = deriveStatus(row);
        if (st === 'delete') return 'row-deleted';
        if (st === 'new') return 'row-appended';
        if (st === 'edited') return 'row-edited';
        return '';
    }

    /** Bulk actions for selected rows. */
    let bulkDeleteSelected = $derived({
        id: 'delete-selected',
        icon: Trash2,
        label: () => $t('transactions.bulk.deleteSelected') || 'Delete selected',
        variant: 'danger' as const,
        onClick: (rows: PendingOp[]) => {
            for (const r of rows) {
                if (r.op === 'edit') {
                    markDelete(r.tempId);
                } else {
                    removeRow(r.tempId);
                }
            }
        },
    });
    let bulkActionsForTable = $derived([bulkDeleteSelected] as never);

    /** Rows currently selected in the bulk DataTable (for inline toolbar). */
    let bulkTableSelectedRows = $state<PendingOp[]>([]);

    /** Selection-based promote detection — 2 standalone rows with matching promote rule. */
    let selectedForPromote = $derived.by(() => {
        if (bulkTableSelectedRows.length !== 2) return null;
        const [a, b] = bulkTableSelectedRows;
        // Both must be standalone (no partnerId, no partnerPayload)
        if (a.partnerId != null || b.partnerId != null) return null;
        if (a.partnerPayload != null || b.partnerPayload != null) return null;
        // Check markedDelete
        if ((a.op === 'edit' && a.markedDelete) || (b.op === 'edit' && b.markedDelete)) return null;
        const match = findPromoteMatch(a.fields.type, b.fields.type, $t);
        if (!match) return null;
        return {...match, opA: a, opB: b};
    });

    /** Handle promote of 2 selected rows. */
    function handlePromoteSelected() {
        if (!selectedForPromote) return;
        const {opA, opB, targetLabel} = selectedForPromote;
        // Check if fields diverge
        const descA = opA.fields.description,
            descB = opB.fields.description;
        const tagsA = opA.fields.tags,
            tagsB = opB.fields.tags;
        const dateA = opA.fields.date,
            dateB = opB.fields.date;
        const cbA = opA.fields.cost_basis_override,
            cbB = opB.fields.cost_basis_override;
        const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB) || dateA !== dateB || cbA !== cbB;
        if (diverges) {
            const labelA = opA.op === 'edit' ? `#${(opA as any).txId}` : opA.tempId.slice(0, 6);
            const labelB = opB.op === 'edit' ? `#${(opB as any).txId}` : opB.tempId.slice(0, 6);
            promoteMergeData = {
                txA: {label: labelA, description: descA, tags: tagsA, date: dateA, cost_basis_override: cbA},
                txB: {label: labelB, description: descB, tags: tagsB, date: dateB, cost_basis_override: cbB},
                targetTypeLabel: targetLabel,
                opA,
                opB,
            };
            promoteMergeOpen = true;
            return;
        }
        executePromote(opA, opB, {});
    }

    /** Execute a promote between two ops. */
    function executePromote(opA: PendingOp, opB: PendingOp, resolved: Record<string, unknown>) {
        const match = findPromoteMatch(opA.fields.type, opB.fields.type, $t);
        if (!match) return;
        if (opA.op === 'edit' && opB.op === 'edit') {
            // 2 saved → batch promotes
            pendingPromotes = [
                ...pendingPromotes,
                {
                    id_a: (opA as any).txId,
                    id_b: (opB as any).txId,
                    ...(Object.keys(resolved).length > 0 ? {resolved_fields: resolved} : {}),
                },
            ];
            // Update display: set partner metadata
            opA.fields.type = match.targetType as TransactionTypeCode;
            opB.fields.type = match.targetType as TransactionTypeCode;
            opA.partnerId = (opB as any).txId;
            opA.partnerBrokerId = opB.fields.broker_id;
            opA.partnerCash = opB.fields.cash;
            opA.partnerDate = opB.fields.date;
        } else if (opA.op === 'create' && opB.op === 'create') {
            // 2 new → local transformation (assign shared link_uuid)
            const sharedUuid = generateUUID();
            (opA as any).link_uuid = sharedUuid;
            (opB as any).link_uuid = sharedUuid;
            opA.fields.type = match.targetType as TransactionTypeCode;
            opB.fields.type = match.targetType as TransactionTypeCode;
            opA.partnerBrokerId = opB.fields.broker_id;
            opA.partnerCash = opB.fields.cash;
            opA.partnerDate = opB.fields.date;
        } else {
            // 1 saved + 1 new (mixed)
            const savedOp = opA.op === 'edit' ? opA : opB;
            const newOp = opA.op === 'create' ? opA : opB;
            if (!(newOp as any).link_uuid && newOp.op === 'create') (newOp as any).link_uuid = generateUUID();
            pendingPromotes = [
                ...pendingPromotes,
                {
                    id_a: (savedOp as any).txId,
                    link_uuid_b: (newOp as any).link_uuid,
                    ...(Object.keys(resolved).length > 0 ? {resolved_fields: resolved} : {}),
                },
            ];
            savedOp.fields.type = match.targetType as TransactionTypeCode;
            newOp.fields.type = match.targetType as TransactionTypeCode;
            savedOp.partnerBrokerId = newOp.fields.broker_id;
            savedOp.partnerCash = newOp.fields.cash;
            savedOp.partnerDate = newOp.fields.date;
        }
        ops = [...ops];
    }

    /** Promote merge modal confirm handler. */
    function onBulkPromoteMergeConfirm(resolved: Record<string, unknown>) {
        if (!promoteMergeData) return;
        executePromote(promoteMergeData.opA, promoteMergeData.opB, resolved);
        promoteMergeOpen = false;
        promoteMergeData = null;
    }

    // =========================================================================
    // C6 — Promote Suggest: DB candidates ($effect + debounce) + local candidates ($derived)
    // =========================================================================

    /** Reactive effect: when ops change, debounce-call promote-suggest API for
     *  standalone edit ops (saved rows without partner). */
    $effect(() => {
        if (!open) return;
        const editStandalone = ops.filter((o) => o.op === 'edit' && !o.partnerId && !(o as any).markedDelete && !o.partnerPayload);
        if (editStandalone.length === 0) {
            untrack(() => {
                suggestFromDB = new Map();
            });
            return;
        }
        const inputs = editStandalone.map((o) => ({
            id: (o as any).txId as number,
            type: o.fields.type,
            broker_id: o.fields.broker_id,
            date: o.fields.date,
            currency: o.fields.cash?.code ?? null,
            asset_id: o.fields.asset_id,
        }));
        const key = JSON.stringify(inputs);
        untrack(() => {
            if (key === lastSuggestKey) return;
            if (suggestTimer) clearTimeout(suggestTimer);
            suggestTimer = setTimeout(async () => {
                try {
                    const resp = await zodiosApi.promote_suggest_api_v1_transactions_promote_suggest_post(inputs as never, {queries: {tolerance_days: 7}});
                    const raw = (resp as any).results ?? {};
                    suggestFromDB = new Map(Object.entries(raw).map(([k, v]) => [Number(k), v as Array<{id: number; broker_id: number; date: string; type: string}>]));
                    lastSuggestKey = key;
                } catch (e) {
                    console.warn('[promote-suggest]', e);
                }
            }, 500);
        });
    });

    /** Local promote suggestions: match new standalone ops against each other. */
    let localSuggestions = $derived.by(() => {
        const newStandalone = ops.filter((o) => o.op === 'create' && !(o as any).link_uuid && !o.partnerId && !o.partnerPayload);
        const results: Array<{tempIdA: string; tempIdB: string; labelA: string; labelB: string; targetLabel: string}> = [];
        for (let i = 0; i < newStandalone.length; i++) {
            for (let j = i + 1; j < newStandalone.length; j++) {
                const match = findPromoteMatch(newStandalone[i].fields.type, newStandalone[j].fields.type, $t);
                if (match) {
                    results.push({
                        tempIdA: newStandalone[i].tempId,
                        tempIdB: newStandalone[j].tempId,
                        labelA: `${newStandalone[i].fields.type}`,
                        labelB: `${newStandalone[j].fields.type}`,
                        targetLabel: match.targetLabel,
                    });
                }
            }
        }
        return results;
    });

    /** Combined promote suggestions (local new+new + DB edit→candidate). */
    let allSuggestions = $derived.by(() => {
        const combined: Array<{tempIdA: string; tempIdB: string; labelA: string; labelB: string; targetLabel: string; isDB?: boolean; dbCandidateId?: number}> = [];
        for (const s of localSuggestions) combined.push(s);
        for (const [txId, candidates] of suggestFromDB) {
            const op = ops.find((o) => o.op === 'edit' && (o as any).txId === txId);
            if (!op || !candidates.length) continue;
            const best = candidates[0];
            const match = findPromoteMatch(op.fields.type, best.type, $t);
            if (!match) continue;
            combined.push({
                tempIdA: op.tempId,
                tempIdB: `db-${best.id}`,
                labelA: `#${txId} ${op.fields.type}`,
                labelB: `DB #${best.id} ${best.type}`,
                targetLabel: match.targetLabel,
                isDB: true,
                dbCandidateId: best.id,
            });
        }
        return combined;
    });

    /** Scroll to a row in the DataTable by tempId. */
    function scrollToSuggestRow(tempIdOrDbRef: string) {
        if (tempIdOrDbRef.startsWith('db-')) return; // DB row not in batch — cannot scroll
        tableRef?.navigateToRowId(tempIdOrDbRef);
    }

    /** Trigger promote from a suggestion line (auto-select both ops + invoke handler). */
    function triggerPromoteFromSuggestion(sug: (typeof allSuggestions)[number]) {
        if (!sug.isDB) {
            // Local new+new: find both ops by tempId, select them, then promote
            const opA = ops.find((o) => o.tempId === sug.tempIdA);
            const opB = ops.find((o) => o.tempId === sug.tempIdB);
            if (!opA || !opB) return;
            // Directly execute promote (no need to simulate DataTable selection)
            const match = findPromoteMatch(opA.fields.type, opB.fields.type, $t);
            if (!match) return;
            // Check divergence
            const descA = opA.fields.description,
                descB = opB.fields.description;
            const tagsA = opA.fields.tags,
                tagsB = opB.fields.tags;
            const dateA = opA.fields.date,
                dateB = opB.fields.date;
            const cbA = opA.fields.cost_basis_override,
                cbB = opB.fields.cost_basis_override;
            const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB) || dateA !== dateB || cbA !== cbB;
            if (diverges) {
                promoteMergeData = {
                    txA: {label: sug.labelA, description: descA, tags: tagsA, date: dateA, cost_basis_override: cbA},
                    txB: {label: sug.labelB, description: descB, tags: tagsB, date: dateB, cost_basis_override: cbB},
                    targetTypeLabel: match.targetLabel,
                    opA,
                    opB,
                };
                promoteMergeOpen = true;
            } else {
                executePromote(opA, opB, {});
            }
        } else {
            // DB suggestion: edit → DB candidate
            const opA = ops.find((o) => o.tempId === sug.tempIdA);
            if (!opA || !sug.dbCandidateId) return;
            // Check if DB candidate is already in ops
            let opB = ops.find((o) => o.op === 'edit' && (o as any).txId === sug.dbCandidateId);
            if (!opB) {
                // Add DB candidate to ops via picker
                const tx = txStoreGet(sug.dbCandidateId);
                if (!tx) return; // TX not in store — can't proceed
                opB = editOpFromTx(sug.dbCandidateId, {addedViaPicker: true});
                ops = [...ops, opB];
            }
            const match = findPromoteMatch(opA.fields.type, opB.fields.type, $t);
            if (!match) return;
            const descA = opA.fields.description,
                descB = opB.fields.description;
            const tagsA = opA.fields.tags,
                tagsB = opB.fields.tags;
            const dateA = opA.fields.date,
                dateB = opB.fields.date;
            const cbA = opA.fields.cost_basis_override,
                cbB = opB.fields.cost_basis_override;
            const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB) || dateA !== dateB || cbA !== cbB;
            if (diverges) {
                promoteMergeData = {
                    txA: {label: sug.labelA, description: descA, tags: tagsA, date: dateA, cost_basis_override: cbA},
                    txB: {label: sug.labelB, description: descB, tags: tagsB, date: dateB, cost_basis_override: cbB},
                    targetTypeLabel: match.targetLabel,
                    opA,
                    opB,
                };
                promoteMergeOpen = true;
            } else {
                executePromote(opA, opB, {});
            }
        }
    }

    function handleBulkTableSelectionChange(selectedIds: string[]) {
        const idSet = new Set(selectedIds);
        bulkTableSelectedRows = ops.filter((d) => idSet.has(d.tempId));
    }

    function executeBulkDeleteOnSelected() {
        for (const r of bulkTableSelectedRows) {
            if (r.op === 'edit') {
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
                📋 {$t('transactions.bulk.title', {values: {total: visibleOps.length}})}
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
                                                const d = ops[resolvedRow];
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
                                                const d = ops[resolvedRow];
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
            {#if visibleOps.length > AUTO_VALIDATE_THRESHOLD}
                <InfoBanner variant="info">
                    <p data-testid="tx-bulk-auto-off">ⓘ {$t('transactions.validate.autoOff', {values: {n: visibleOps.length, threshold: AUTO_VALIDATE_THRESHOLD}})}</p>
                </InfoBanner>
            {/if}
            {#if hasPairedDelete}
                <InfoBanner variant="info">
                    <p data-testid="tx-bulk-split-hint">ℹ️ {$t('transactions.deleteModal.splitHint')}</p>
                </InfoBanner>
            {/if}
            {#if allSuggestions.length > 0}
                <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-2 text-xs space-y-0.5" data-testid="promote-suggest-banner">
                    {#each allSuggestions.slice(0, 5) as sug, idx}
                        <div class="flex items-center gap-1 flex-wrap" data-testid="promote-suggest-item-{idx}">
                            <span>💡</span>
                            <button type="button" class="underline text-green-700 dark:text-green-300" onclick={() => scrollToSuggestRow(sug.tempIdA)}>{sug.labelA}</button>
                            <span>&amp;</span>
                            <button type="button" class="underline text-green-700 dark:text-green-300" onclick={() => scrollToSuggestRow(sug.tempIdB)}>{sug.labelB}</button>
                            <span>→ {sug.targetLabel}</span>
                            <button type="button" class="text-green-600 font-bold hover:text-green-800 dark:text-green-400 dark:hover:text-green-200" onclick={() => triggerPromoteFromSuggestion(sug)} data-testid="promote-suggest-link-{idx}">🔗</button>
                        </div>
                    {/each}
                    {#if allSuggestions.length > 5}
                        <span class="text-gray-500 text-[11px]">{$t('transactions.promoteSuggest.bannerMore', {values: {n: allSuggestions.length - 5}})}</span>
                    {/if}
                </div>
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
                    {#if bulkTableSelectedRows.some((d) => d.op === 'edit' && (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete'))}
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
                    {#if selectedForPromote}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1 px-2 py-1 rounded text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-[11px]"
                            onclick={handlePromoteSelected}
                            data-testid="promote-toolbar-confirm"
                            title={$t('transactions.actions.promotePair')}
                        >
                            <Link2 size={12} /> <span class="hidden sm:inline">🔗 {selectedForPromote.targetLabel}</span>
                        </button>
                    {/if}
                </div>
            {/if}

            <!-- Right: actions -->
            <div class="ml-auto flex flex-row-reverse items-center gap-2 flex-wrap">
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={openAddRowForm} data-testid="tx-bulk-add-row" title={$t('transactions.bulk.addRow') || 'Add row'}>
                    <Plus size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.addRow') || 'Add row'}</span>
                </button>
                {#if visibleOps.some((d) => d.op === 'edit' && (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete'))}
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
                data={visibleOps}
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

<!-- Plan D2 Step C4: PromoteMergeModal for resolving divergent fields during promote -->
<PromoteMergeModal
    open={promoteMergeOpen}
    txA={promoteMergeData?.txA}
    txB={promoteMergeData?.txB}
    targetTypeLabel={promoteMergeData?.targetTypeLabel ?? ''}
    onConfirm={onBulkPromoteMergeConfirm}
    onCancel={() => {
        promoteMergeOpen = false;
        promoteMergeData = null;
    }}
/>
