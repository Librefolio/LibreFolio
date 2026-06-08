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
    import {currentLanguage} from '$lib/stores/app/language';
    import {X, Plus, Pencil, Copy, Trash2, Check, Undo2, Save, Unlink, Link2, Lightbulb, Upload} from 'lucide-svelte';

    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import TransactionResultBanner from '../shared/TransactionResultBanner.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';

    import type {ColumnDef, CellContent} from '$lib/components/table/types';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded, getAssetInfo, getAllAssets} from '$lib/stores/reference/assetStore';
    import {ensureBrokersLoaded, getAllBrokers, brokerStoreVersion, type BrokerInfo} from '$lib/stores/reference/brokerStore';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {type TransactionTypeCode, getTypeRule, isDraftReadyForValidation, ensureTypesLoaded, isTypesLoaded, getTransactionTypeIconUrl, getCostBasisRule} from '$lib/stores/transactions/transactionTypeStore';
    import {findPromoteMatch, type PromoteContext} from '$lib/stores/transactions/transactionTypeStore';
    import PromoteMergeModal from './PromoteMergeModal.svelte';
    import {createValidateScheduler} from '$lib/utils/transactions/useValidateScheduler.svelte';
    import {commitTransactions, validateTransactions} from '$lib/utils/transactions/txCommitApi';
    import {buildCreatePayload, buildUpdateDiff, buildBatchPayload, diffDualItem, applySignRules, upgradeAutoToDetail, type TxFields, type TxOriginal, type ResolvedOp} from '$lib/utils/transactions/txPayloadHelpers';
    import {resolveIssueMessage, type ResolverContext} from '$lib/utils/transactions/resolveValidationMessage';
    import {generateUUID} from '$lib/utils/core/uuid';
    import {formatCurrencyAmountHtml, formatCurrencyCodeHtml} from '$lib/utils/currency/currencyFormat';
    import {getStringColor} from '$lib/utils/colors';
    import {lookupFxRate, type FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import {computeFxConversionInfo, buildFxTooltipData, buildFxTooltipHtml} from '$lib/utils/currency/fxConversionHelper';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import TransactionFormModal from './TransactionFormModal.svelte';
    import TransactionPickerModal from './TransactionPickerModal.svelte';
    import ImportWizardModal from './ImportWizardModal.svelte';
    import {txStoreGet, txStoreCount} from '$lib/stores/transactions/txStore.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import type {FormModalItems} from '../shared/resolveFormItems';
    import type {TXReadItem, ValidationIssue} from '../types';
    import type {TransactionCreateItem} from '$lib/types';

    // =========================================================================
    // Types
    // =========================================================================

    /** WorkspaceIntent — declarative API for opening the BulkModal.
     *  +page passes only action + txIds; BulkModal resolves data from txStore. */
    export type WorkspaceIntent = {action: 'create'} | {action: 'import'} | {action: 'edit'; txIds: number[]} | {action: 'delete'; txIds: number[]} | {action: 'clone'; txIds: number[]};

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
        cost_basis_override: {code: string; amount: string} | null;
        /** UI-only: tracks whether cost_basis is auto-calculated, manual, or not applicable.
         *  null = field not applicable for this type/side (forbidden).
         *  'auto' = WAC will be calculated automatically.
         *  'manual' = user provided explicit value. */
        cost_basis_mode: 'auto' | 'manual' | null;
    }

    /** Pending operation — one per row in the BulkModal (visible + hidden partners).
     *  Tagged union: 'create' for new rows, 'edit' for existing DB rows.
     *  If `pairedWith` is set, this op is the hidden partner of a paired row.
     *  `link_uuid` is the shared pairing UUID for backend payloads (WAC, commit). */
    type PendingOp = ({op: 'create'} | {op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean}) & {
        tempId: string;
        fields: DraftFields;
        pairedWith?: string;
        link_uuid?: string | null;
        /** W4b: partner on inaccessible broker — read-only sentinel */ inaccessible?: boolean;
        /** Cached WAC result from validate — transient, not sent to backend */ _wacCache?: WacResultEntry | null;
        /** Currency hint for WAC target — null = backend decides */ wacCurrencyHint?: string | null;
    };

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

    // R3-B5: delta-days filter for suggest banner (persisted in sessionStorage)
    let maxDeltaDays = $state(Number(sessionStorage.getItem('lf-suggest-delta-days') ?? '3'));
    $effect(() => {
        sessionStorage.setItem('lf-suggest-delta-days', String(maxDeltaDays));
    });

    /** Compute the absolute difference in days between two ISO date strings. */
    function daysDiff(a: string, b: string): number {
        const da = new Date(a);
        const db = new Date(b);
        return Math.round(Math.abs(da.getTime() - db.getTime()) / 86400000);
    }

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
            cost_basis_override: null,
            cost_basis_mode: null,
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
        const cbo = tx.cost_basis_override
            ? typeof tx.cost_basis_override === 'object' && tx.cost_basis_override !== null
                ? {code: String((tx.cost_basis_override as any).code ?? ''), amount: String((tx.cost_basis_override as any).amount ?? '')}
                : {amount: String(tx.cost_basis_override), code: tx.cash?.code ?? ''}
            : null;
        // Derive cost_basis_mode from backend rules
        // For DB rows: if cost_basis is present → 'manual'; if absent but applicable → still 'manual'
        // (existing rows without cost_basis were saved intentionally or before the feature existed).
        // Only NEW creates get 'auto' (see applyFormPayload fallback).
        const rawQty = Number(tx.quantity);
        const side: 'from' | 'to' | 'self' = tx.related_transaction_id != null ? (rawQty < 0 ? 'from' : 'to') : 'self';
        const cbRule = getCostBasisRule(tx.type, side);
        let cbMode: 'auto' | 'manual' | null = null;
        if (cbRule !== 'forbidden') {
            cbMode = 'manual';
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
            cost_basis_override: cbo,
            cost_basis_mode: cbMode,
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
    /** Visible ops: excludes hidden partner ops (pairedWith set). Used by DataTable. */
    let visibleOps = $derived(ops.filter((o) => !o.pairedWith));
    /** Find the hidden partner op for a given main op's tempId. */
    function getPartnerOp(mainTempId: string): PendingOp | undefined {
        return ops.find((o) => o.pairedWith === mainTempId);
    }
    let issues = $state<ValidationIssue[]>([]);
    /** Maps "operation:index" (from backend) → tempId. Built after each validate. */
    let lastOpsIndexMap = $state<Map<string, string>>(new Map());
    let formError = $state<string | null>(null);
    let commitFailed = $state(false);
    let committing = $state(false);
    /** Anti-bounce: track last commit draft key + timestamp. */
    let lastCommitDraftKey = $state('');
    let lastCommitAt = $state(0);
    const COMMIT_ANTI_BOUNCE_MS = 10000;
    let tableRef = $state<DataTable<PendingOp> | undefined>(undefined);
    /** Accumulated splits for saved paired TXs (sent in batch.splits). originalType is client-only for preview. */
    let pendingSplits = $state<{id_a: number; id_b: number; originalType: string}[]>([]);
    /** Derived set of all split-queued TX IDs for quick lookup. */
    let splitTxIdsSet = $derived(new Set(pendingSplits.flatMap((s) => [s.id_a, s.id_b])));
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

    // =========================================================================
    // WAC results — populated from validate response (Phase C: inline WAC)
    // =========================================================================

    /** Single source of truth: WAC results per auto-op (keyed by tempId).
     *  Contains full details (qualifying_txs) for FormModal display. */
    type WacResultEntry = {
        wac: {code: string; amount: string} | null;
        qualifying_txs: Array<Record<string, any>>;
        missing_pairs: string[];
    };
    let wacResults = $state<Map<string, WacResultEntry>>(new Map());
    /** TX IDs from the last validate response (uncommitted batch) — for pending markers in qualifying tables */
    let pendingTxIds = $state<Set<number>>(new Set());

    // =========================================================================
    // Event cache — populated after validate for rich cell rendering
    // =========================================================================

    type EventCacheEntry = {type: string; date: string; amount: string; code: string; notes: string | null};
    let eventCache = $state<Map<number, EventCacheEntry>>(new Map());

    // =========================================================================
    // Initial rows resolution
    // =========================================================================

    /** Resolve initialRows from intent (if provided) or use legacy initialRows prop. */
    function resolveInitialRows(): {rows: TXReadItem[]; status?: 'delete'; autoForm: string | null} {
        if (intent) {
            if (intent.action === 'create') {
                return {rows: [], autoForm: 'create'};
            }
            if (intent.action === 'import') {
                return {rows: [], autoForm: null};
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
                if (rows.length === 0 && intent?.action !== 'import') {
                    queueMicrotask(() => {
                        formOpen = true;
                        formMode = 'create';
                        formItems = null;
                        formEditingTempId = null;
                    });
                }
                if (intent?.action === 'import') {
                    queueMicrotask(() => {
                        importWizardOpen = true;
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
        } else if (opArr.length === 0 && intent?.action !== 'import') {
            // Auto-open for brand-new empty grid (not import — bridge opens instead)
            queueMicrotask(() => {
                formOpen = true;
                formMode = 'create';
                formItems = null;
                formEditingTempId = null;
            });
        } else if (opArr.length === 0 && intent?.action === 'import') {
            queueMicrotask(() => {
                importWizardOpen = true;
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
        // For paired main, find partner's DB id (if it's an edit op)
        const partnerOp = d.pairedWith ? undefined : getPartnerOp(d.tempId);
        const partnerDbId = partnerOp?.op === 'edit' ? partnerOp.txId : null;
        return {
            id: id ?? 0,
            broker_id: d.fields.broker_id,
            asset_id: d.fields.asset_id,
            type: d.fields.type,
            date: d.fields.date,
            quantity: d.fields.quantity,
            cash: d.fields.cash,
            related_transaction_id: partnerDbId ?? (partnerOp ? 0 : null),
            tags: d.fields.tags,
            description: d.fields.description,
            cost_basis_override: (d.fields.cost_basis_override || null) as any,
            cost_basis_mode: d.fields.cost_basis_mode,
            asset_event_id: d.fields.asset_event_id,
            created_at: orig?.created_at,
            updated_at: orig?.updated_at,
        };
    }

    /** Collapse paired drafts in an array: detect partners via
     *  related_transaction_id, keep the "from" half as visible, make the "to"
     *  half a hidden partner (pairedWith). For solo drafts with a partner in
     *  txStore, create a hidden partner op from the store data. */
    function collapsePairedOps(opArr: PendingOp[]): PendingOp[] {
        const idToIdx = new Map<number, number>();
        opArr.forEach((d, i) => {
            const _id = opTxId(d);
            if (_id != null) idToIdx.set(_id, i);
        });
        const toHide = new Set<number>(); // indices that become hidden partners
        for (let i = 0; i < opArr.length; i++) {
            if (toHide.has(i)) continue;
            const d = opArr[i];
            const partnerId = (d.op === 'edit' ? txStoreGet(d.txId) : undefined)?.related_transaction_id;
            if (partnerId == null) continue;
            const pIdx = idToIdx.get(partnerId);
            if (pIdx == null || pIdx === i || toHide.has(pIdx)) continue;
            // Determine from/to: "from" = negative cash or negative qty (the sender)
            const cashAmt = Number((d.op === 'edit' ? txStoreGet(d.txId) : undefined)?.cash?.amount ?? 0);
            const partnerCashAmt = Number((opArr[pIdx].op === 'edit' ? txStoreGet(opArr[pIdx].txId) : undefined)?.cash?.amount ?? 0);
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
            // Mark "to" as hidden partner of "from"
            opArr[toIdx].pairedWith = opArr[fromIdx].tempId;
            // Generate shared link_uuid for WAC payload
            const sharedUuid = generateUUID();
            opArr[fromIdx].link_uuid = sharedUuid;
            opArr[toIdx].link_uuid = sharedUuid;
            toHide.add(toIdx);
        }
        // For remaining edit drafts with DB partner not in batch, create hidden partner op from txStore
        for (const d of opArr) {
            if (d.pairedWith) continue; // already a partner
            if (d.op !== 'edit') continue;
            const relId = txStoreGet(d.txId)?.related_transaction_id;
            if (relId == null) continue;
            if (idToIdx.has(relId)) continue; // partner already in batch
            const partnerTx = txStoreGet(relId);
            if (!partnerTx) {
                // W4b: partner not in txStore — likely on inaccessible broker
                const mainTx = txStoreGet(d.txId);
                const pBrokerId = mainTx?.partner_broker_id;
                if (pBrokerId) {
                    const sharedUuid = generateUUID();
                    d.link_uuid = sharedUuid;
                    const placeholderOp: PendingOp = {
                        op: 'edit',
                        txId: relId,
                        markedDelete: false,
                        tempId: generateUUID(),
                        fields: {type: mainTx.type, broker_id: pBrokerId, date: mainTx.date} as any,
                        pairedWith: d.tempId,
                        link_uuid: sharedUuid,
                        inaccessible: true,
                    };
                    opArr.push(placeholderOp);
                }
                continue;
            }
            // Create a hidden edit op for the partner
            const sharedUuid = generateUUID();
            d.link_uuid = sharedUuid;
            const partnerOp: PendingOp = {
                op: 'edit',
                txId: relId,
                markedDelete: false,
                tempId: generateUUID(),
                fields: fieldsFromTx(partnerTx),
                pairedWith: d.tempId,
                link_uuid: sharedUuid,
            };
            opArr.push(partnerOp);
        }
        // Pass 3: collapse create ops with shared link_uuid (clone path)
        const linkUuidMap = new Map<string, number>();
        for (let i = 0; i < opArr.length; i++) {
            const op = opArr[i];
            if (op.op !== 'create' || op.pairedWith) continue;
            const uuid = op.link_uuid as string | undefined;
            if (!uuid) continue;
            const prev = linkUuidMap.get(uuid);
            if (prev !== undefined) {
                // Determine from/to: negative cash or qty = sender (from)
                const cashI = Number(op.fields.cash?.amount ?? 0);
                const cashP = Number(opArr[prev].fields.cash?.amount ?? 0);
                const qtyI = Number(op.fields.quantity ?? 0);
                let fromIdx = prev,
                    toIdx = i;
                if (cashI < 0 || (cashI === 0 && cashP === 0 && qtyI < 0)) {
                    fromIdx = i;
                    toIdx = prev;
                }
                opArr[toIdx].pairedWith = opArr[fromIdx].tempId;
                // Derive cost_basis_mode for receiver (to) side using backend rules
                const toQty = Number(opArr[toIdx].fields.quantity ?? 0);
                if (toQty > 0) {
                    const toCbRule = getCostBasisRule(opArr[toIdx].fields.type, 'to');
                    if (toCbRule !== 'forbidden') {
                        opArr[toIdx].fields.cost_basis_mode = 'auto';
                        opArr[toIdx].fields.cost_basis_override = null;
                    }
                }
            } else {
                linkUuidMap.set(uuid, i);
            }
        }
        return opArr;
    }

    /** Collapse two standalone ops into one paired row (main + hidden partner).
     *  Used post-promote (DD-BF2). The "to" op becomes hidden (pairedWith set).
     *  "from" = negative cash or negative qty. */
    function collapseIntoPaired(opA: PendingOp, opB: PendingOp): {main: PendingOp; removeTempId: string} {
        const cashA = Number(opA.fields.cash?.amount ?? 0);
        const cashB = Number(opB.fields.cash?.amount ?? 0);
        const qtyA = Number(opA.fields.quantity ?? 0);
        let from = opA,
            to = opB;
        if (cashA > 0 && cashB <= 0) {
            from = opB;
            to = opA;
        } else if (cashA === 0 && cashB === 0 && qtyA > 0) {
            from = opB;
            to = opA;
        }
        // Mark "to" as hidden partner of "from"
        to.pairedWith = from.tempId;
        return {main: from, removeTempId: ''}; // no removal — to stays in ops but hidden
    }

    /** Apply the form-collected payload to a brand-new draft row. */
    function addRowFromForm(payload: Record<string, unknown>) {
        const next = createOpEmpty();
        applyFormPayload(next.fields, payload);
        if (typeof payload.link_uuid === 'string' && next.op === 'create') (next as any).link_uuid = payload.link_uuid;
        // Persist WAC currency hint
        if (typeof payload._wac_currency_hint === 'string') next.wacCurrencyHint = payload._wac_currency_hint;
        ops = [...ops, next];
    }

    /** Apply the form-collected payload to an existing draft (deep-edit). */
    function patchRowFromForm(tempId: string, payload: Record<string, unknown>) {
        ops = ops.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d, fields: {...d.fields}};
            applyFormPayload(merged.fields, payload);
            // Persist WAC currency hint from FormModal
            if (typeof payload._wac_currency_hint === 'string') {
                merged.wacCurrencyHint = payload._wac_currency_hint;
            } else if (payload._wac_currency_hint === null) {
                merged.wacCurrencyHint = null;
            }
            return merged;
        });
    }

    function applyFormPayload(target: DraftFields, p: Record<string, unknown>) {
        const prevType = target.type; // Capture before overwrite for type-change detection
        if (typeof p.broker_id === 'number') target.broker_id = p.broker_id;
        if (typeof p.type === 'string') target.type = p.type as TransactionTypeCode;
        if (typeof p.date === 'string') target.date = p.date;
        if (typeof p.quantity === 'string') target.quantity = p.quantity;
        target.asset_id = (p.asset_id as number | null | undefined) ?? null;
        target.cash = (p.cash as DraftFields['cash']) ?? null;
        target.tags = Array.isArray(p.tags) ? (p.tags as string[]) : [];
        target.description = typeof p.description === 'string' ? p.description : '';
        target.asset_event_id = (p.asset_event_id as number | null | undefined) ?? null;
        target.cost_basis_override = p.cost_basis_override && typeof p.cost_basis_override === 'object' && 'code' in (p.cost_basis_override as any) ? (p.cost_basis_override as {code: string; amount: string}) : null;

        // Derive cost_basis_mode with backend-driven guardrail
        const typeChanged = target.type !== prevType;
        const qty = Number(target.quantity ?? 0);
        const side: 'from' | 'to' | 'self' = qty < 0 ? 'from' : qty > 0 ? 'to' : 'self';
        const cbRule = getCostBasisRule(target.type, side);

        if (cbRule === 'forbidden' || (cbRule === 'required_qty_pos' && qty <= 0)) {
            // Guardrail: forbidden OR required_qty_pos with non-positive qty → no cost_basis
            target.cost_basis_mode = null;
            target.cost_basis_override = null;
        } else if (typeof p._cost_basis_mode === 'string') {
            // Explicit mode from FormModal — only accept if backend rule allows it
            // (cbRule is already != 'forbidden' here thanks to the guard above)
            const cbAllowed = !(cbRule === 'required_qty_pos' && qty <= 0);
            target.cost_basis_mode = cbAllowed ? (p._cost_basis_mode as 'auto' | 'manual') : null;
        } else if (target.cost_basis_mode === null || typeChanged) {
            // Re-derive: mode was null (fresh from defaultFields) or type actually changed
            const cbAllowed = !(cbRule === 'required_qty_pos' && qty <= 0);
            if (target.cost_basis_override) {
                target.cost_basis_mode = 'manual';
            } else if (cbAllowed) {
                target.cost_basis_mode = 'auto';
            } else {
                target.cost_basis_mode = null;
            }
        }
        // else: target already has 'auto' or 'manual' and no explicit override → preserve
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
            link_uuid: getTypeRule(src.fields.type as TransactionTypeCode)?.requiresPair ? generateUUID() : null,
        };
        // Clone hidden partner if exists
        const srcPartner = getPartnerOp(tempId);
        if (srcPartner) {
            const partnerClone: PendingOp = {
                op: 'create',
                tempId: generateUUID(),
                fields: {...srcPartner.fields, date: todayIso()},
                link_uuid: clone.link_uuid, // share link_uuid
                pairedWith: clone.tempId,
            };
            ops = [...ops, clone, partnerClone];
        } else {
            ops = [...ops, clone];
        }
    }

    function resetRow(tempId: string) {
        ops = ops.map((d) => {
            if (d.tempId !== tempId || d.op !== 'edit') return d;
            const reset = editOpFromTx(d.txId, {addedViaPicker: d.addedViaPicker});
            return reset;
        });
        // Re-collapse pairs from txStore
        ops = collapsePairedOps(ops);
    }

    function resetAll() {
        // BUG-C2: also undo pending splits
        // Remove partner rows added by split, then reset remaining edit rows
        ops = ops.filter((d) => !(d as any).addedBySplit);
        ops = ops.map((d) => {
            if (d.op !== 'edit') return d;
            const reset = editOpFromTx(d.txId, {addedViaPicker: d.addedViaPicker});
            return reset;
        });
        // Re-collapse pairs
        ops = collapsePairedOps(ops);
        pendingSplits = [];
    }

    /** Split a paired row in the BulkModal.
     *  Saved paired → backend split + 2 editable preview rows (DD-R2.1).
     *  New paired (link_uuid shared or pairedWith) → local transformation only. */
    function handleSplitRow(row: PendingOp) {
        const partnerOp = getPartnerOp(row.tempId);

        if (row.op === 'edit' && partnerOp && partnerOp.op === 'edit') {
            // Case A: Saved paired → backend split + preview editable (DD-R2.1)
            const txId = row.txId;
            const partnerId = partnerOp.txId;
            pendingSplits = [...pendingSplits, {id_a: txId, id_b: partnerId, originalType: row.fields.type}];

            // Un-pair: partner becomes visible and independent
            partnerOp.pairedWith = undefined;
            (partnerOp as any).addedBySplit = true;

            // BUG-C1: Insert partner adjacent to main row (not at end)
            const mainIdx = ops.findIndex((o) => o.tempId === row.tempId);
            const partnerIdx = ops.findIndex((o) => o.tempId === partnerOp.tempId);
            if (partnerIdx !== mainIdx + 1) {
                // Move partner right after main
                const newOps = ops.filter((o) => o.tempId !== partnerOp.tempId);
                const insertAt = newOps.findIndex((o) => o.tempId === row.tempId) + 1;
                newOps.splice(insertAt, 0, partnerOp);
                ops = newOps;
            } else {
                ops = [...ops]; // trigger reactivity
            }
            lastSuggestKey = ''; // B9: invalidate suggest
        } else if (row.op === 'create' && partnerOp) {
            // Case B/C: New paired (partner is a hidden create op) → local split
            const splitTypes = SPLIT_TYPE_MAP[row.fields.type];
            if (!splitTypes) return;
            const [fromType, toType] = splitTypes;
            const cashAmt = Number(row.fields.cash?.amount ?? 0);
            const qty = Number(row.fields.quantity ?? 0);
            const isFrom = row.fields.type === 'TRANSFER' ? qty < 0 || qty === 0 : cashAmt < 0 || cashAmt === 0;

            // Main row → standalone type
            row.fields.type = (isFrom ? fromType : toType) as TransactionTypeCode;
            row.link_uuid = null;

            // Partner → standalone type, becomes visible
            partnerOp.fields.type = (isFrom ? toType : fromType) as TransactionTypeCode;
            partnerOp.pairedWith = undefined;
            if (partnerOp.op === 'create') partnerOp.link_uuid = null;

            ops = [...ops]; // trigger reactivity
        } else if (row.op === 'create' && row.link_uuid) {
            // Case B legacy: link_uuid shared between two visible create ops
            const partner = ops.find((o) => o !== row && o.op === 'create' && o.link_uuid === row.link_uuid);
            if (partner) {
                const splitTypes = SPLIT_TYPE_MAP[row.fields.type];
                if (!splitTypes) return;
                const [fromType, toType] = splitTypes;
                const cashAmt = Number(row.fields.cash?.amount ?? 0);
                const qty = Number(row.fields.quantity ?? 0);
                const isFrom = row.fields.type === 'TRANSFER' ? qty < 0 : cashAmt < 0;
                row.fields.type = (isFrom ? fromType : toType) as TransactionTypeCode;
                partner.fields.type = (isFrom ? toType : fromType) as TransactionTypeCode;
                row.link_uuid = null;
                partner.link_uuid = null;
                ops = [...ops];
            }
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
        const resolved = resolveOps({excludeTempId});
        const result = buildBatchPayload({ops: resolved});
        return {
            creates: (result.creates as Record<string, unknown>[]) ?? [],
            updates: (result.updates as Record<string, unknown>[]) ?? [],
            deletes: (result.deletes as number[]) ?? [],
        };
    }

    /**
     * Resolve all PendingOps into ResolvedOp[] for batch payload building.
     * Handles split-queued type stripping and promote-queued row skipping.
     */
    function resolveOps(opts?: {excludeTempId?: string | null; splitTxIds?: Set<number>; promoteTxIds?: Set<number>}): ResolvedOp[] {
        const excludeTempId = opts?.excludeTempId ?? null;
        const splitTxIds = opts?.splitTxIds ?? new Set<number>();
        const promoteTxIds = opts?.promoteTxIds ?? new Set<number>();
        const resolved: ResolvedOp[] = [];

        for (const d of ops) {
            if (d.pairedWith) continue; // hidden partners are handled via their main op
            if (d.tempId === excludeTempId) continue;
            const st = deriveStatus(d);

            // Skip split-queued edit rows ONLY if unchanged
            if (d.op === 'edit' && splitTxIds.has((d as any).txId) && st !== 'edited') continue;
            // Skip promote-queued edit rows entirely
            if (d.op === 'edit' && promoteTxIds.has((d as any).txId)) continue;

            const pOp = getPartnerOp(d.tempId);

            if (st === 'new') {
                let partnerPayload: Record<string, unknown> | null = null;
                if (pOp) {
                    const partnerRule = getTypeRule(pOp.fields.type as TransactionTypeCode);
                    partnerPayload = buildCreatePayload(opToTxFields(pOp), partnerRule);
                }
                resolved.push({intent: 'create', payload: collectCreate(d), partnerPayload});
            } else if (st === 'edited') {
                const upd = collectUpdate(d);
                // For split-queued rows, strip type (split handles type change)
                if (upd && splitTxIds.has((d as any).txId)) delete upd.type;
                const payload = upd && Object.keys(upd).length > 1 ? upd : undefined;
                let partnerPayload: Record<string, unknown> | null = null;
                if (pOp && pOp.op === 'edit') {
                    const partnerOrig = txStoreGet(pOp.txId);
                    if (partnerOrig) {
                        const partnerRule = getTypeRule(pOp.fields.type as TransactionTypeCode);
                        const partnerOrigRule = getTypeRule(partnerOrig.type as TransactionTypeCode);
                        const partnerUpd = buildUpdateDiff(opToTxFields(pOp), partnerOrig as unknown as TxOriginal, partnerRule, partnerOrigRule);
                        if (Object.keys(partnerUpd).length > 1) partnerPayload = partnerUpd;
                    }
                }
                if (payload || partnerPayload) {
                    resolved.push({intent: 'update', payload: payload ?? undefined, partnerPayload});
                }
            } else if (st === 'delete' && d.op === 'edit') {
                resolved.push({
                    intent: 'delete',
                    deleteId: d.txId,
                    partnerDeleteId: pOp?.op === 'edit' ? pOp.txId : null,
                });
            }
        }
        return resolved;
    }

    /** Convert a PendingOp to the shared TxFields interface. */
    function opToTxFields(d: PendingOp): TxFields {
        // In auto mode with currency hint, override becomes the hint sentinel
        const cbo = d.fields.cost_basis_mode === 'auto' && d.wacCurrencyHint ? {code: d.wacCurrencyHint, amount: '0'} : d.fields.cost_basis_override || null;
        return {...d.fields, cost_basis_override: cbo, link_uuid: d.link_uuid ?? null};
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
        // For split-queued rows, type change is handled by split — ignore it in diff
        if (diff && pendingSplits.some((s) => s.id_a === d.txId || s.id_b === d.txId)) {
            delete diff.type;
        }
        if (diff && Object.keys(diff).length > 1) return 'edited';
        // Also check partner changes
        const pOp = getPartnerOp(d.tempId);
        if (pOp && pOp.op === 'edit') {
            const partnerOrig = txStoreGet(pOp.txId);
            if (partnerOrig) {
                const partnerRule = getTypeRule(pOp.fields.type as TransactionTypeCode);
                const partnerOrigRule = getTypeRule(partnerOrig.type as TransactionTypeCode);
                const partnerUpd = buildUpdateDiff(opToTxFields(pOp), partnerOrig as unknown as TxOriginal, partnerRule, partnerOrigRule);
                if (Object.keys(partnerUpd).length > 1) return 'edited';
            }
        }
        return 'original';
    }

    // =========================================================================
    // Validate scheduler
    // =========================================================================

    /** Map a ResolvedOp back to the tempId of the PendingOp that produced it.
     *  Uses the resolved ops array to find the source PendingOp by intent match.
     *  `resolvedIdx` is the index within the `resolved` array. */
    function buildOpsIndexMap(resolved: ResolvedOp[]): Map<string, string> {
        // Replicate buildBatchPayload ordering to map "operation:index" → tempId.
        // The resolved array mirrors ops ordering (pairedWith skipped, same filter).
        const opsMap = new Map<string, string>(); // "create:0" → tempId
        let createIdx = 0;
        let updateIdx = 0;

        // Track which resolved op came from which visible PendingOp.
        // resolveOps iterates ops in order, skipping pairedWith. We do the same.
        const splitTxIds = new Set(pendingSplits.flatMap((s) => [s.id_a, s.id_b]));
        const promoteTxIds = new Set(pendingPromotes.flatMap((p) => [p.id_a, p.id_b].filter(Boolean) as number[]));
        let resolvedI = 0;

        for (const d of ops) {
            if (d.pairedWith) continue;
            const st = deriveStatus(d);
            // Same skip logic as resolveOps
            if (d.op === 'edit' && splitTxIds.has((d as any).txId) && st !== 'edited') continue;
            if (d.op === 'edit' && promoteTxIds.has((d as any).txId)) continue;

            if (resolvedI >= resolved.length) break;
            const rOp = resolved[resolvedI];

            if (st === 'new' && rOp.intent === 'create') {
                opsMap.set(`create:${createIdx}`, d.tempId);
                createIdx++;
                const pOp = getPartnerOp(d.tempId);
                if (rOp.partnerPayload && pOp) {
                    opsMap.set(`create:${createIdx}`, pOp.tempId);
                    createIdx++;
                }
                resolvedI++;
            } else if (st === 'edited' && rOp.intent === 'update') {
                opsMap.set(`update:${updateIdx}`, d.tempId);
                updateIdx++;
                const pOp = getPartnerOp(d.tempId);
                if (rOp.partnerPayload && pOp) {
                    opsMap.set(`update:${updateIdx}`, pOp.tempId);
                    updateIdx++;
                }
                resolvedI++;
            } else if (st === 'delete' && rOp.intent === 'delete') {
                resolvedI++;
            } else {
                // Mismatch — skip this op (original/no-change)
            }
        }
        return opsMap;
    }

    const scheduler = createValidateScheduler({
        enabled: () =>
            ops.length > 0 &&
            ops.length <= AUTO_VALIDATE_THRESHOLD &&
            ops.some((d) => {
                if (deriveStatus(d) === 'delete') return false;
                if (!isDraftReadyForValidation(d.fields as any)) return false;
                // W3-fix: for paired ops, partner must also be ready (unless inaccessible)
                const pOp = getPartnerOp(d.tempId);
                if (pOp && !(pOp as any).inaccessible && !isDraftReadyForValidation(pOp.fields as any)) return false;
                return true;
            }),
        draftKey: () => lastDraftKey,
        validateFn: async () => {
            if (ops.length === 0) {
                issues = [];
                lastValidatedDraftKey = lastDraftKey;
                issuesDismissed = false;
                return {issuesCount: 0};
            }
            const splitTxIds = new Set(pendingSplits.flatMap((s) => [s.id_a, s.id_b]));
            const resolved = resolveOps({splitTxIds});
            const payload = buildBatchPayload({
                ops: resolved,
                splits: pendingSplits.length > 0 ? pendingSplits.map((s) => ({id_a: s.id_a, id_b: s.id_b})) : undefined,
            });
            upgradeAutoToDetail(payload);
            const sentKey = lastDraftKey;
            const result = await validateTransactions(payload, {fallback: $t('transactions.bulk.saveFailed')});
            if (result.networkError) {
                issues = [{operation: 'create', index: 0, error: result.networkError}];
            } else {
                issues = result.issues as unknown as ValidationIssue[];
            }
            lastValidatedDraftKey = sentKey;
            issuesDismissed = false;

            // ── Phase C: extract wac_results from validate response ──
            const rawResp = result.rawResponse as Record<string, unknown> | null;

            // Always update pendingTxIds from results (even without WAC data)
            const rawResults = (rawResp?.results as Array<{ids?: number[]; operation?: string; status?: string}> | null) ?? [];
            const pendingIdOps = new Map<number, string>();
            for (const r of rawResults) {
                if (r.status !== 'success') continue;
                for (const id of r.ids ?? []) pendingIdOps.set(id, r.operation ?? 'create');
            }
            if (pendingIdOps.size > 0) pendingTxIds = new Set(pendingIdOps.keys());

            // Always build the ops index map (needed for issue row mapping + WAC)
            const opsMap = buildOpsIndexMap(resolved);
            lastOpsIndexMap = opsMap;

            const rawWacResults = (rawResp?.wac_results as Array<Record<string, unknown>> | null | undefined) ?? null;
            if (rawWacResults && rawWacResults.length > 0) {
                // Map wac_results to tempIds using the opsMap
                const nextMap = new Map<string, WacResultEntry>();
                for (const wr of rawWacResults) {
                    const op = wr.operation as string | null;
                    const idx = wr.index as number | null;
                    if (op == null || idx == null) continue;
                    const key = `${op}:${idx}`;
                    const tempId = opsMap.get(key);
                    if (!tempId) continue;
                    const wacVal = (wr.wac as {code: string; amount: string} | null) ?? null;
                    // Annotate qualifying_txs entries that belong to this batch (pending)
                    const rawQtxs = (wr.wac_qualifying_txs as Array<Record<string, any>>) ?? [];
                    const qualifyingTxs =
                        pendingIdOps.size > 0
                            ? rawQtxs.map((q) => {
                                  if (q.tx_id == null) return q;
                                  const pendingOp = pendingIdOps.get(q.tx_id);
                                  return pendingOp ? {...q, is_pending: true, pending_op: pendingOp} : q;
                              })
                            : rawQtxs;
                    const cacheEntry: WacResultEntry = {
                        wac: wacVal,
                        qualifying_txs: qualifyingTxs,
                        missing_pairs: (wr.wac_missing_pairs as string[]) ?? [],
                    };
                    nextMap.set(tempId, cacheEntry);
                    // Write WAC value + cache into the op's fields for cell display (with equality guard)
                    const opObj = ops.find((o) => o.tempId === tempId);
                    if (opObj) {
                        const needsValueUpdate = wacVal && opObj.fields.cost_basis_mode === 'auto' && (!opObj.fields.cost_basis_override || opObj.fields.cost_basis_override.code !== wacVal.code || opObj.fields.cost_basis_override.amount !== wacVal.amount);
                        const needsCacheUpdate = true; // always update cache with latest result
                        if (needsValueUpdate || needsCacheUpdate) {
                            const mainTempId = opObj.pairedWith; // sender's tempId (receiver points to sender)
                            ops = ops.map((o) => {
                                if (o.tempId === tempId) {
                                    const updated = {...o, _wacCache: cacheEntry};
                                    if (needsValueUpdate && wacVal) {
                                        updated.fields = {...o.fields, cost_basis_override: {code: wacVal.code, amount: wacVal.amount}};
                                    }
                                    return updated;
                                }
                                if (mainTempId && o.tempId === mainTempId) {
                                    // Sender: new reference to force DataTable cell re-render
                                    return {...o};
                                }
                                return o;
                            });
                        }
                    }
                }
                wacResults = nextMap;
            } else {
                // No WAC results — clear (might have been cleared by backend due to pydantic errors)
                if (wacResults.size > 0) wacResults = new Map();
            }

            // ── Fetch event cache for rich cell rendering ──
            const eventIdsToFetch = [...new Set(ops.map((o) => o.fields.asset_event_id).filter((id): id is number => id != null && !eventCache.has(id)))];
            if (eventIdsToFetch.length > 0) {
                try {
                    const resp = await zodiosApi.get('/api/v1/assets/events', {queries: {ids: eventIdsToFetch}});
                    const nextCache = new Map(eventCache);
                    for (const item of resp.items ?? []) {
                        for (const ev of item.events ?? []) {
                            const val = ev.value as {code: string; amount: string};
                            nextCache.set(ev.id, {type: ev.type, date: ev.date, amount: val.amount, code: val.code, notes: (ev as any).notes ?? null});
                        }
                    }
                    eventCache = nextCache;
                } catch {
                    // Non-blocking: cell falls back to #ID
                }
            }

            return {issuesCount: issues.length};
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
    const BALANCE_CODES = new Set(['balanceAssetNegative', 'balanceCashNegative']);
    let fieldIssues = $derived(issues.filter((i) => !BALANCE_CODES.has(i.code ?? '')));
    let balanceIssues = $derived(issues.filter((i) => BALANCE_CODES.has(i.code ?? '')));
    let hasWacFxIssues = $derived(fieldIssues.some((i) => i.code === 'wacFxUnavailable'));

    /** Sync FX rates for missing pairs referenced in issues, then re-validate. */
    let syncFxLoading = $state(false);
    async function handleSyncFx() {
        const fxIssues = fieldIssues.filter((i) => i.code === 'wacFxUnavailable');
        if (fxIssues.length === 0) return;
        // Collect all unique pairs and date ranges
        const allPairs = [...new Set(fxIssues.flatMap((i) => (i.params?.pairs as string[]) ?? []))];
        if (allPairs.length === 0) return;
        // Gather dates from ops linked to these issues
        const dates: string[] = [];
        for (const issue of fxIssues) {
            const key = `${issue.operation}:${issue.index}`;
            const tempId = lastOpsIndexMap.get(key);
            const op = tempId ? ops.find((o) => o.tempId === tempId) : null;
            if (op?.fields.date) dates.push(op.fields.date);
        }
        const sortedDates = dates.sort();
        const minDate = sortedDates[0] ?? new Date().toISOString().slice(0, 10);
        const maxDate = sortedDates[sortedDates.length - 1] ?? minDate;
        // Expand range ±7 days
        const start = new Date(new Date(minDate).getTime() - 7 * 86400000).toISOString().slice(0, 10);
        const end = new Date(new Date(maxDate).getTime() + 7 * 86400000).toISOString().slice(0, 10);
        // Convert pair format: "EUR/USD" → "EUR-USD"
        const pairs = allPairs.map((p) => p.replace('/', '-'));
        syncFxLoading = true;
        try {
            await zodiosApi.post('/api/v1/fx/currencies/sync', {pairs, start, end});
            toasts.success($t('transactions.wac.syncSuccess') || 'FX rates synced');
            scheduler.trigger('change');
        } catch {
            toasts.error($t('transactions.wac.syncFailed') || 'Failed to sync FX rates');
        } finally {
            syncFxLoading = false;
        }
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
            const splitTxIds = new Set(pendingSplits.flatMap((s) => [s.id_a, s.id_b]));
            const promoteTxIds = new Set(pendingPromotes.flatMap((p) => [p.id_a, p.id_b].filter(Boolean) as number[]));
            const resolved = resolveOps({splitTxIds, promoteTxIds});

            if (resolved.length === 0 && pendingSplits.length === 0 && pendingPromotes.length === 0) {
                onClose();
                return;
            }

            const payload = buildBatchPayload({
                ops: resolved,
                splits: pendingSplits.length > 0 ? pendingSplits.map((s) => ({id_a: s.id_a, id_b: s.id_b})) : undefined,
                promotes: pendingPromotes.length > 0 ? pendingPromotes : undefined,
            });

            const result = await commitTransactions(payload, {fallback: $t('transactions.bulk.saveFailed')});
            if (result.networkError) {
                formError = result.networkError;
                toasts.error($t('transactions.commit.serverError') || 'Save failed — server error');
                return;
            }
            if (!result.committed) {
                issues = result.issues as unknown as ValidationIssue[];
                // Rebuild index map for the commit payload (same resolved ops)
                lastOpsIndexMap = buildOpsIndexMap(resolved);
                issuesDismissed = false;
                commitFailed = true;
                return;
            }
            onCommitted?.(result.rawResponse);
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
                    // B5: split-queued badge takes priority
                    if (row.op === 'edit' && splitTxIdsSet.has((row as any).txId)) {
                        return {type: 'html', html: '<span class="px-1.5 py-0.5 text-[10px] rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">✂️ split</span>'};
                    }
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
                    const pOp = getPartnerOp(row.tempId);
                    if (rule.requiresPair && pOp && pOp.op === 'edit') {
                        return {type: 'html', html: renderDualHtml(`#${opTxId(row)}`, `#${pOp.txId}`)};
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
                    const pOp = getPartnerOp(row.tempId);
                    if (rule.requiresPair && pOp && pOp.fields.date !== row.fields.date) {
                        return {type: 'html', html: renderDualHtml(row.fields.date, pOp.fields.date)};
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
                cell: (row): CellContent => {
                    // B5: show type transition preview for split-queued rows
                    if (row.op === 'edit' && splitTxIdsSet.has((row as any).txId)) {
                        // BUG-C4: use originalType from pendingSplits (fields.type may have been edited)
                        const splitEntry = pendingSplits.find((s) => s.id_a === (row as any).txId || s.id_b === (row as any).txId);
                        const origType = splitEntry?.originalType ?? row.fields.type;
                        const splitTypes = SPLIT_TYPE_MAP[origType];
                        if (splitTypes) {
                            const qty = Number(row.fields.quantity ?? 0);
                            const cashAmt = Number(row.fields.cash?.amount ?? 0);
                            const isSender = origType === 'TRANSFER' ? qty < 0 || qty === 0 : cashAmt < 0 || cashAmt === 0;
                            const targetType = isSender ? splitTypes[0] : splitTypes[1];
                            const origSlug = origType.toLowerCase().replace(/_/g, '-');
                            return {
                                type: 'html',
                                html: `<span class="inline-flex items-center gap-1 text-[11px]"><img src="/icons/transactions/${origSlug}.png" alt="" style="width:1.5rem;height:1.5rem" class="object-contain shrink-0" onerror="this.style.display='none'"/> <span class="text-gray-400">→</span> ${renderTypeHtml(targetType)}</span>`,
                            };
                        }
                        return {type: 'html', html: `<span class="text-[11px]">${renderTypeHtml(row.fields.type)} → <span class="text-purple-600 dark:text-purple-400">✂️ ADJUSTMENT</span></span>`};
                    }
                    return {type: 'html', html: renderTypeHtml(row.fields.type)};
                },
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
                    const pOp = getPartnerOp(row.tempId);
                    if (rule.requiresPair && pOp && Number(qty) !== 0) {
                        const absVal = Math.abs(Number(qty));
                        const fromQty = `-${absVal} 📉`;
                        const toQty = `+${absVal} 📈`;
                        return {type: 'html', html: renderDualHtml(fromQty, toQty)};
                    }
                    // Format with trailing zeros removal
                    const fmtQty = (() => {
                        const n = parseFloat(qty);
                        return isNaN(n) ? qty : n.toString();
                    })();
                    return {type: 'html', html: `<span class="font-mono text-sm">${fmtQty}</span>`};
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
                    // Reconstruct display sign: form stores abs, column shows actual sign
                    let displayCash = row.fields.cash;
                    if (displayCash && rule.cashSign === 'negative') {
                        displayCash = {code: displayCash.code, amount: String(-Math.abs(Number(displayCash.amount)))};
                    }
                    // Paired row → show Da:/A: dual cash lines
                    const pOp = getPartnerOp(row.tempId);
                    if (rule.requiresPair && pOp) {
                        return {type: 'html', html: renderDualHtml(formatCashText(displayCash), formatCashText(pOp.fields.cash))};
                    }
                    return {type: 'html', html: `<span class="text-sm">${formatCashText(displayCash)}</span>`};
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
                    const pOp = getPartnerOp(row.tempId);
                    if (rule.requiresPair && pOp) {
                        if (pOp.inaccessible) {
                            // W4b: partner on inaccessible broker → show lock
                            const lockHtml = `<span class="text-red-500 dark:text-red-400" data-testid="tx-bulk-partner-lock" title="${$t('transactions.bulk.partnerInaccessible')}">🔒</span>`;
                            return {type: 'html', html: renderDualHtml(renderBrokerHtml(row.fields.broker_id), lockHtml)};
                        }
                        if (pOp.fields.broker_id !== row.fields.broker_id) {
                            return {type: 'html', html: renderDualHtml(renderBrokerHtml(row.fields.broker_id), renderBrokerHtml(pOp.fields.broker_id))};
                        }
                    }
                    return {type: 'html', html: renderBrokerHtml(row.fields.broker_id)};
                },
            },
            {
                id: 'cost_basis_override',
                header: () => $t('transactions.form.costBasis'),
                type: 'text',
                width: 160,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    // For paired rows (sender visible), cost_basis lives on the receiver (hidden partner)
                    const partner = getPartnerOp(row.tempId);
                    const source = partner ?? row;
                    const mode = source.fields.cost_basis_mode;
                    const cbo = source.fields.cost_basis_override;

                    // mode null → field not applicable for this type
                    if (mode === null) {
                        return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                    }

                    // mode 'auto'
                    if (mode === 'auto') {
                        if (cbo && cbo.amount) {
                            // Auto-calculated value present
                            return {
                                type: 'html',
                                html: `<span class="text-gray-400 italic" data-testid="tx-bulk-cost-basis-auto">💡 ${formatCurrencyAmountHtml(Number(cbo.amount), cbo.code)}</span>`,
                            };
                        }
                        // Loading/pending
                        return {type: 'html', html: '<span class="text-gray-400 italic" data-testid="tx-bulk-cost-basis-auto">💡 …</span>'};
                    }

                    // mode 'manual'
                    if (cbo && cbo.amount) {
                        return {type: 'html', html: `<span class="font-mono text-xs" data-testid="tx-bulk-cost-basis-manual">${formatCurrencyAmountHtml(Number(cbo.amount), cbo.code)}</span>`};
                    }
                    // User explicitly cleared the value
                    return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                },
            },
            {
                id: 'asset_event_id',
                header: () => $t('transactions.form.assetEvent'),
                type: 'text',
                width: 160,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    if (row.fields.asset_event_id == null) return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                    const ev = eventCache.get(row.fields.asset_event_id);
                    if (!ev) return {type: 'html', html: `<span class="font-mono text-xs">#${row.fields.asset_event_id}</span>`};
                    const emojiMap: Record<string, string> = {DIVIDEND: '💰', INTEREST: '🏦', SPLIT: '✂️', PRICE_ADJUSTMENT: '📊', MATURITY_SETTLEMENT: '📅'};
                    const emoji = emojiMap[ev.type] ?? '📋';
                    const shortDate = new Date(ev.date).toLocaleDateString(undefined, {day: 'numeric', month: 'short'});
                    const fullDate = new Date(ev.date).toLocaleDateString(undefined, {day: 'numeric', month: 'long', year: 'numeric'});
                    const amt = parseFloat(ev.amount);
                    let fmtAmt = '';
                    if (amt !== 0) {
                        const ci = getCurrencyInfo(ev.code);
                        const sym = ci.symbol && ci.symbol !== ev.code ? `${ci.symbol} ` : '';
                        const flag = ci.flag_emoji && ci.flag_emoji !== '🏳️' ? `<span class="emoji-flag">${ci.flag_emoji}</span> ` : '';
                        fmtAmt = `${Number.isInteger(amt) ? amt.toString() : amt.toFixed(2)} ${sym}${flag}${ev.code}`;
                    }
                    // Build rich HTML tooltip
                    const typeLabel = $t(`assetDetail.eventType.${ev.type}`) || ev.type.replace(/_/g, ' ');
                    let tooltipHtml = `<strong>${emoji} ${typeLabel}</strong><br>${fullDate}`;
                    if (amt !== 0) tooltipHtml += `<br>${$t('transactions.bulk.eventTooltipAmount')}: <span style="font-family:monospace">${amt.toFixed(4)} ${ev.code}</span>`;
                    if (ev.notes) tooltipHtml += `<br>📝 ${$t('transactions.bulk.eventTooltipNotes')}: ${ev.notes}`;
                    return {
                        type: 'html',
                        html: `<span class="inline-flex items-center gap-1 text-xs"><span class="text-sm">${emoji}</span><span class="text-gray-600 dark:text-gray-400">${shortDate}</span>${fmtAmt ? `<span class="font-mono text-gray-500">${fmtAmt}</span>` : ''}</span>`,
                        tooltip: {html: tooltipHtml, position: 'top'},
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
                hiddenByDefault: false,
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
                id: 'link_uuid',
                header: () => $t('transactions.form.linkUuid'),
                type: 'text',
                width: 140,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    const pOp = getPartnerOp(row.tempId);
                    if (pOp && pOp.op === 'edit') {
                        const selfId = opTxId(row) ?? '?';
                        return {type: 'html', html: `<code class="text-xs font-mono text-gray-400">#${selfId} <span class="text-base">⇄</span> #${pOp.txId}</code>`};
                    }
                    if (pOp && pOp.op === 'create') return {type: 'html', html: '<code class="text-xs font-mono text-indigo-400">new <span class="text-base">⇄</span> new</code>'};
                    if (row.op === 'create' && row.link_uuid) return {type: 'html', html: `<code class="text-xs font-mono text-gray-400">${row.link_uuid.slice(0, 8)}…</code>`};
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
            disabled: (row: PendingOp) => !!getPartnerOp(row.tempId)?.inaccessible,
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
                // Hide if already split-queued
                if (row.op === 'edit' && splitTxIdsSet.has((row as any).txId)) return false;
                // Has a hidden partner → can split
                if (getPartnerOp(row.tempId)) return true;
                // New paired (any kind: link_uuid shared or dual-form)
                if (row.op === 'create') {
                    const t = row.fields.type;
                    if (t === 'TRANSFER' || t === 'CASH_TRANSFER' || t === 'FX_CONVERSION') return true;
                }
                return false;
            },
        },
        {
            id: 'undo-split',
            icon: Undo2,
            label: () => $t('transactions.bulk.undoSplit') || 'Undo split',
            onClick: (row: PendingOp) => {
                const txId = (row as any).txId as number;
                const splitEntry = pendingSplits.find((s) => s.id_a === txId || s.id_b === txId);
                if (!splitEntry) return;
                const partnerId = splitEntry.id_a === txId ? splitEntry.id_b : splitEntry.id_a;
                // Remove from pendingSplits
                pendingSplits = pendingSplits.filter((s) => s !== splitEntry);
                // Find partner op (was made visible during split) → re-hide it
                const partnerOp = ops.find((o) => o.op === 'edit' && (o as any).txId === partnerId);
                if (partnerOp) {
                    partnerOp.pairedWith = row.tempId;
                    (partnerOp as any).addedBySplit = undefined;
                }
                ops = [...ops]; // reactivity
                lastSuggestKey = ''; // B9: invalidate suggest
            },
            visible: (row: PendingOp) => row.op === 'edit' && splitTxIdsSet.has((row as any).txId),
        },
        {
            id: 'suggest',
            icon: Lightbulb,
            label: () => $t('transactions.bulk.suggestLightbulb') || 'Import suggestion',
            onClick: (row: PendingOp) => {
                // BUG-C7: open suggest picker filtered to this row's importable candidates
                const txId = (row as any).txId as number;
                const entry = importableSuggestions.find((s) => s.txId === txId);
                if (entry && entry.candidates.length > 0) {
                    // Open picker filtered to just this row's candidates
                    suggestPickerOpen = true;
                } else {
                    // Fallback: scroll to banner
                    const banner = document.querySelector('[data-testid="promote-suggest-banner"]');
                    if (banner) {
                        banner.scrollIntoView({behavior: 'smooth', block: 'center'});
                        banner.classList.add('ring-2', 'ring-green-400');
                        setTimeout(() => banner.classList.remove('ring-2', 'ring-green-400'), 1500);
                    }
                }
            },
            visible: (row: PendingOp) => {
                if (getPartnerOp(row.tempId)) return false;
                const txId = (row as any).txId;
                // Show if this row has importable DB candidates OR is in banner suggestions
                return importableSuggestions.some((s) => s.txId === txId) || bannerSuggestions.some((s) => s.tempIdA === row.tempId || s.tempIdB === row.tempId);
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
            visible: (row: PendingOp) => row.op === 'edit' && deriveStatus(row) !== 'delete',
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
        const key = `${issue.operation}:${issue.index}`;
        const tempId = lastOpsIndexMap.get(key);
        if (!tempId) {
            // Fallback: try direct ops index
            const draft = ops[issue.index];
            if (draft) tableRef?.navigateToRowId(draft.tempId);
            return;
        }
        // If this is a partner (hidden), navigate to its main row
        const op = ops.find((o) => o.tempId === tempId);
        const mainTempId = op?.pairedWith ?? tempId;
        tableRef?.navigateToRowId(mainTempId);
    }

    /** Get visual row label for an issue (e.g. "3", "5a", "5b"). */
    function getVisualRowLabel(issue: ValidationIssue): string {
        if (issue.index < 0) {
            // Global issue (balance): use broker name from params
            if (issue.params?.brokerId) {
                const broker = brokers.find((b) => b.id === issue.params!.brokerId);
                return broker ? `🏦 ${broker.name}` : `🏦 #${issue.params.brokerId}`;
            }
            return '⚠️';
        }
        const key = `${issue.operation}:${issue.index}`;
        const tempId = lastOpsIndexMap.get(key);
        if (!tempId) return String(issue.index + 1); // fallback
        const op = ops.find((o) => o.tempId === tempId);
        // Determine main row (for visual position) and suffix
        const isPartner = !!op?.pairedWith;
        const mainTempId = isPartner ? op.pairedWith! : tempId;
        const visIdx = visibleOps.findIndex((o) => o.tempId === mainTempId);
        const rowNum = visIdx >= 0 ? visIdx + 1 : issue.index + 1;
        // Suffix: "a" if main of a pair, "b" if partner
        const hasPair = isPartner || getPartnerOp(tempId) != null;
        const suffix = hasPair ? (isPartner ? 'b' : 'a') : '';
        return `${rowNum}${suffix}`;
    }

    // =========================================================================
    // Toolbar chips
    // =========================================================================

    // Bugfix-4 §U16: validate chip removed — banners are the single source
    // of truth. Footer keeps only an inline "Validating…" indicator.

    let newCount = $derived(visibleOps.filter((d) => deriveStatus(d) === 'new').length);
    let editedCount = $derived(visibleOps.filter((d) => deriveStatus(d) === 'edited').length);
    let deleteCount = $derived(visibleOps.filter((d) => deriveStatus(d) === 'delete').length);
    /** B23: true when at least one paired row is marked for deletion — show split hint. */
    let hasPairedDelete = $derived(visibleOps.some((d) => deriveStatus(d) === 'delete' && getPartnerOp(d.tempId) != null));
    let actionCount = $derived(newCount + editedCount + deleteCount + pendingSplits.length + pendingPromotes.length);
    let commitDisabled = $derived(committing || ops.length === 0 || actionCount === 0);
    let commitLabel = $derived(committing ? $t('common.saving') : $t('transactions.bulk.commitAll'));

    // -------------------------------------------------------------------------
    // Nested FormModal (Bugfix-5 §A4): "+ Add row" + row-action "Edit single".
    // -------------------------------------------------------------------------
    let formOpen = $state(false);
    let formMode = $state<'create' | 'edit'>('create');
    let formItems = $state<FormModalItems | null>(null);
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

    // -------------------------------------------------------------------------
    // ImportWizardModal (Phase 07 Part 5 v5 M1): BRIM Import Wizard → BulkModal bridge.
    // -------------------------------------------------------------------------
    let importWizardOpen = $state(false);

    function onImportBatch(creates: TransactionCreateItem[]) {
        toasts.success($t('importWizard.importedCount', {values: {n: creates.length}}));
        importWizardOpen = false;
    }

    // BUG-C7: Suggest picker — opens PickerModal filtered to importable candidates
    let suggestPickerOpen = $state(false);
    function openSuggestPicker() {
        suggestPickerOpen = true;
    }

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
        suggestPickerOpen = false;
        lastSuggestKey = ''; // BUG-C10: force re-trigger suggest after import
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
        formItems = null;
        formEditingTempId = null;
        formKey++;
        formOpen = true;
    }

    /** B23 Step 4: intercept edit on deleted row — show confirm before restoring. */
    function handleEditRowClick(row: PendingOp) {
        // W4b: block edit if partner is inaccessible
        if (getPartnerOp(row.tempId)?.inaccessible) return;
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
        let mainItem = opToTxLike(row);
        // SP-C Step 2: if split-queued, override type with post-split target
        if (row.op === 'edit' && splitTxIdsSet.has(row.txId) && mainItem) {
            const splitEntry = pendingSplits.find((s) => s.id_a === row.txId || s.id_b === row.txId);
            const origType = splitEntry?.originalType ?? row.fields.type;
            const splitTypes = SPLIT_TYPE_MAP[origType];
            if (splitTypes) {
                const qty = Number(row.fields.quantity ?? 0);
                const cashAmt = Number(row.fields.cash?.amount ?? 0);
                const isSender = origType === 'TRANSFER' ? qty < 0 || qty === 0 : cashAmt < 0 || cashAmt === 0;
                mainItem.type = (isSender ? splitTypes[0] : splitTypes[1]) as string;
            }
        }
        formEditingTempId = row.tempId;
        // Resolve partner from hidden partner op or txStore fallback
        const pOp = getPartnerOp(row.tempId);
        const partnerItem = pOp ? opToTxLike(pOp) : null;
        formItems = partnerItem ? [mainItem, partnerItem] : [mainItem];
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
        // R3-B2: trigger validation after FormModal pushes a draft
        scheduler.trigger('change');
        lastSuggestKey = ''; // B9: invalidate suggest after form push
    }

    /** Add a paired draft row: single visible draft with partner payload stored. */
    function addDualRowFromForm(payload: Record<string, unknown>) {
        const items = payload._items as Record<string, unknown>[];
        if (!items || items.length < 2) {
            addRowFromForm(payload);
            return;
        }

        // Propagate cost_basis_mode to receiver item if present at top level
        if (typeof payload._cost_basis_mode === 'string' && !('_cost_basis_mode' in items[1])) {
            items[1]._cost_basis_mode = payload._cost_basis_mode;
        }

        // "From" side — visible row
        const fromOp = createOpEmpty();
        applyFormPayload(fromOp.fields, items[0]);
        if (typeof items[0].link_uuid === 'string' && fromOp.op === 'create') fromOp.link_uuid = items[0].link_uuid;

        // "To" side — hidden partner op
        const toOp = createOpEmpty();
        applyFormPayload(toOp.fields, items[1]);
        if (typeof items[1].link_uuid === 'string' && toOp.op === 'create') toOp.link_uuid = items[1].link_uuid;
        toOp.pairedWith = fromOp.tempId;
        // Persist WAC currency hint on receiver (the side with WAC calc)
        if (typeof payload._wac_currency_hint === 'string') toOp.wacCurrencyHint = payload._wac_currency_hint;

        ops = [...ops, fromOp, toOp];
    }

    /** Patch a paired draft row: update visible draft + hidden partner. */
    function patchDualRowFromForm(tempId: string, payload: Record<string, unknown>) {
        const items = payload._items as Record<string, unknown>[];
        if (!items || items.length < 2) {
            patchRowFromForm(tempId, payload);
            return;
        }

        // Propagate _cost_basis_mode to partner item so applyFormPayload can derive
        // the correct mode on the receiver (e.g. user toggled Auto→Manual in FormModal)
        if (typeof payload._cost_basis_mode === 'string' && !('_cost_basis_mode' in items[1])) {
            items[1]._cost_basis_mode = payload._cost_basis_mode;
        }

        // Update main op
        ops = ops.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d, fields: {...d.fields}};
            applyFormPayload(merged.fields, items[0]);
            // B6: sync link_uuid
            const sharedUuid = (items[0].link_uuid as string) ?? (items[1].link_uuid as string) ?? d.link_uuid;
            if (sharedUuid) merged.link_uuid = sharedUuid;
            return merged;
        });

        // Update or create partner op
        let pOp = getPartnerOp(tempId);
        if (pOp) {
            ops = ops.map((d) => {
                if (d.tempId !== pOp!.tempId) return d;
                const merged = {...d, fields: {...d.fields}};
                applyFormPayload(merged.fields, items[1]);
                // B6: sync link_uuid on partner
                const sharedUuid = (items[0].link_uuid as string) ?? (items[1].link_uuid as string) ?? d.link_uuid;
                if (sharedUuid) merged.link_uuid = sharedUuid;
                // Persist WAC currency hint on receiver
                if (typeof payload._wac_currency_hint === 'string') merged.wacCurrencyHint = payload._wac_currency_hint;
                else if (payload._wac_currency_hint === null) merged.wacCurrencyHint = null;
                return merged;
            });
        } else {
            // No existing partner (edge case) — create one
            const toOp = createOpEmpty();
            applyFormPayload(toOp.fields, items[1]);
            toOp.pairedWith = tempId;
            const sharedUuid = (items[0].link_uuid as string) ?? (items[1].link_uuid as string);
            if (sharedUuid) toOp.link_uuid = sharedUuid;
            ops = [...ops, toOp];
        }
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

    /** Build PromoteContext from two PendingOps for constraint checking (F4). */
    function buildPromoteCtx(a: PendingOp, b: PendingOp): PromoteContext {
        return {
            brokerA: a.fields.broker_id,
            brokerB: b.fields.broker_id,
            currencyA: a.fields.cash?.code,
            currencyB: b.fields.cash?.code,
            assetA: a.fields.asset_id,
            assetB: b.fields.asset_id,
            qtyA: Number(a.fields.quantity ?? 0),
            qtyB: Number(b.fields.quantity ?? 0),
        };
    }

    /** Selection-based promote detection — 2 standalone rows with matching promote rule. */
    let selectedForPromote = $derived.by(() => {
        if (bulkTableSelectedRows.length !== 2) return null;
        const [a, b] = bulkTableSelectedRows;
        // Both must be standalone (no hidden partner)
        if (getPartnerOp(a.tempId) || getPartnerOp(b.tempId)) return null;
        // Check markedDelete
        if ((a.op === 'edit' && a.markedDelete) || (b.op === 'edit' && b.markedDelete)) return null;
        const match = findPromoteMatch(a.fields.type, b.fields.type, $t, buildPromoteCtx(a, b));
        if (!match) return null;
        return {...match, opA: a, opB: b};
    });

    /** Handle promote of 2 selected rows. */
    function handlePromoteSelected() {
        if (!selectedForPromote) return;
        const {opA, opB, targetLabel} = selectedForPromote;
        // Check if fields diverge (only description + tags — date/cost_basis handled in FormModal)
        const descA = opA.fields.description,
            descB = opB.fields.description;
        const tagsA = opA.fields.tags,
            tagsB = opB.fields.tags;
        const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB);
        if (diverges) {
            const labelA = opA.op === 'edit' ? `#${(opA as any).txId}` : opA.tempId.slice(0, 6);
            const labelB = opB.op === 'edit' ? `#${(opB as any).txId}` : opB.tempId.slice(0, 6);
            promoteMergeData = {
                txA: {label: labelA, description: descA, tags: tagsA, date: opA.fields.date, cost_basis_override: opA.fields.cost_basis_override},
                txB: {label: labelB, description: descB, tags: tagsB, date: opB.fields.date, cost_basis_override: opB.fields.cost_basis_override},
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
        const match = findPromoteMatch(opA.fields.type, opB.fields.type, $t, buildPromoteCtx(opA, opB));
        if (!match) return;

        // Apply resolved fields (from MergeModal) to opA before collapsing
        if (resolved.description != null) opA.fields.description = resolved.description as string;
        if (resolved.tags != null) opA.fields.tags = resolved.tags as string[];
        if (resolved.date != null) opA.fields.date = resolved.date as string;
        if (resolved.cost_basis_override != null) opA.fields.cost_basis_override = resolved.cost_basis_override as any;

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
            opA.fields.type = match.targetType as TransactionTypeCode;
            opB.fields.type = match.targetType as TransactionTypeCode;
        } else if (opA.op === 'create' && opB.op === 'create') {
            // 2 new → local transformation (assign shared link_uuid)
            const sharedUuid = generateUUID();
            opA.link_uuid = sharedUuid;
            opB.link_uuid = sharedUuid;
            opA.fields.type = match.targetType as TransactionTypeCode;
            opB.fields.type = match.targetType as TransactionTypeCode;
        } else {
            // 1 saved + 1 new (mixed)
            const savedOp = opA.op === 'edit' ? opA : opB;
            const newOp = opA.op === 'create' ? opA : opB;
            if (!newOp.link_uuid) newOp.link_uuid = generateUUID();
            pendingPromotes = [
                ...pendingPromotes,
                {
                    id_a: (savedOp as any).txId,
                    link_uuid_b: newOp.link_uuid,
                    ...(Object.keys(resolved).length > 0 ? {resolved_fields: resolved} : {}),
                },
            ];
            savedOp.fields.type = match.targetType as TransactionTypeCode;
            newOp.fields.type = match.targetType as TransactionTypeCode;
        }

        // F5: Collapse into paired row (DD-BF2) — removes opB from grid, sets partner display on opA
        const {removeTempId} = collapseIntoPaired(opA, opB);
        ops = ops.filter((o) => o.tempId !== removeTempId);
        ops = [...ops]; // trigger reactivity
        lastSuggestKey = ''; // B9: invalidate suggest after promote
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
        const editStandalone = ops.filter((o) => o.op === 'edit' && !o.pairedWith && !getPartnerOp(o.tempId) && !(o as any).markedDelete);
        if (editStandalone.length === 0) {
            untrack(() => {
                suggestFromDB = new Map();
            });
            return;
        }
        const inputs = editStandalone.map((o) => {
            const rule = getTypeRule(o.fields.type);
            const {signedQty, signedCash} = applySignRules(o.fields.quantity, o.fields.cash, rule);
            return {
                id: (o as any).txId as number,
                type: o.fields.type,
                broker_id: o.fields.broker_id,
                date: o.fields.date,
                currency: signedCash?.code ?? null,
                asset_id: o.fields.asset_id,
                amount: Number(signedCash?.amount ?? 0) || null,
                quantity: Number(signedQty ?? 0) || null,
            };
        });
        const key = JSON.stringify(inputs);
        untrack(() => {
            if (key === lastSuggestKey) return;
            if (suggestTimer) clearTimeout(suggestTimer);
            suggestTimer = setTimeout(async () => {
                try {
                    const resp = await zodiosApi.promote_suggest_api_v1_transactions_promote_suggest_post(inputs as never, {queries: {tolerance_days: maxDeltaDays}});
                    const raw = (resp as any).results ?? {};
                    const result = new Map(Object.entries(raw).map(([k, v]) => [Number(k), v as Array<{id: number; broker_id: number; date: string; type: string}>]));
                    // BUG-C7 fix: do NOT filter here — bannerSuggestions and importableSuggestions
                    // handle the split between "already in ops" and "importable" in their derived logic.
                    suggestFromDB = result;
                    lastSuggestKey = key;
                } catch (e) {
                    console.warn('[promote-suggest]', e);
                }
            }, 500);
        });
    });

    /** Local promote suggestions: match new standalone ops against each other. */
    let localSuggestions = $derived.by(() => {
        const newStandalone = ops.filter((o) => o.op === 'create' && !o.pairedWith && !getPartnerOp(o.tempId) && !o.link_uuid);
        const results: SuggestEntry[] = [];
        for (let i = 0; i < newStandalone.length; i++) {
            for (let j = i + 1; j < newStandalone.length; j++) {
                const dA = newStandalone[i].fields.date;
                const dB = newStandalone[j].fields.date;
                const delta = daysDiff(dA, dB);
                if (delta > maxDeltaDays) continue;
                const match = findPromoteMatch(newStandalone[i].fields.type, newStandalone[j].fields.type, $t, buildPromoteCtx(newStandalone[i], newStandalone[j]));
                if (match) {
                    results.push({
                        tempIdA: newStandalone[i].tempId,
                        tempIdB: newStandalone[j].tempId,
                        targetType: match.targetType,
                    });
                }
            }
        }
        return results;
    });

    /** Minimal suggest entry — all display data is read live from ops[].
     *  This is future-proof: if fields change in ops, suggestions auto-update. */
    type SuggestEntry = {tempIdA: string; tempIdB: string; targetType: string; isDB?: boolean; dbCandidateId?: number};

    /** Banner suggestions: only pairs where BOTH TX are already in ops[] (local↔local or local↔imported-DB) */
    let bannerSuggestions = $derived.by(() => {
        const combined: SuggestEntry[] = [];
        // Local new+new (both in ops by definition)
        for (const s of localSuggestions) combined.push(s);

        // Local edit+edit: match standalone edit ops against each other (works even after suggestFromDB is refreshed)
        const editStandalone = ops.filter((o) => o.op === 'edit' && !o.pairedWith && !getPartnerOp(o.tempId) && !(o as any).markedDelete);
        const seenPairs = new Set<string>(); // avoid duplicates
        for (let i = 0; i < editStandalone.length; i++) {
            for (let j = i + 1; j < editStandalone.length; j++) {
                const a = editStandalone[i],
                    b = editStandalone[j];
                const dA = a.fields.date,
                    dB = b.fields.date;
                const delta = daysDiff(dA, dB);
                if (delta > maxDeltaDays) continue;
                const match = findPromoteMatch(a.fields.type, b.fields.type, $t, buildPromoteCtx(a, b));
                if (!match) continue;
                const pairKey = `${(a as any).txId}-${(b as any).txId}`;
                if (seenPairs.has(pairKey)) continue;
                seenPairs.add(pairKey);
                combined.push({
                    tempIdA: a.tempId,
                    tempIdB: b.tempId,
                    targetType: match.targetType,
                    isDB: true,
                    dbCandidateId: (b as any).txId,
                });
            }
        }

        return combined;
    });

    /** Importable suggestions: DB candidates NOT yet in ops (for 💡 button) */
    let importableSuggestions = $derived.by(() => {
        const result: Array<{txId: number; tempId: string; candidates: Array<{id: number; type: string; broker_id: number; date: string}>}> = [];
        const opsEditIds = new Set(ops.filter((o) => o.op === 'edit').map((o) => (o as any).txId as number));
        for (const [txId, candidates] of suggestFromDB) {
            const op = ops.find((o) => o.op === 'edit' && (o as any).txId === txId);
            if (!op) continue;
            const importable = candidates.filter((c) => !opsEditIds.has(c.id));
            if (importable.length > 0) {
                result.push({txId, tempId: op.tempId, candidates: importable});
            }
        }
        return result;
    });

    let suggestPickerIncludeIds = $derived(new Set(importableSuggestions.flatMap((s) => s.candidates.map((c) => c.id))));

    // =========================================================================
    // FX Implied Rate — reactive market cache for FX_CONVERSION suggestions
    // =========================================================================

    /** Reactive bridge for async FX market rates. Key: "BASE-QUOTE-DATE" */
    let fxMarketCache = $state<Map<string, FxDataPoint | null>>(new Map());
    let fxFetchGeneration = 0;

    $effect(() => {
        const currentGen = ++fxFetchGeneration;
        const fxEntries = bannerSuggestions.filter((s) => s.targetType === 'FX_CONVERSION');

        for (const entry of fxEntries) {
            const opA = ops.find((o) => o.tempId === entry.tempIdA);
            const opB = ops.find((o) => o.tempId === entry.tempIdB);
            if (!opA?.fields.cash || !opB?.fields.cash) continue;

            const aAmt = Number(opA.fields.cash.amount);
            const [fromOp, toOp] = aAmt < 0 ? [opA, opB] : [opB, opA];
            if (!fromOp.fields.cash || !toOp.fields.cash) continue;
            const base = fromOp.fields.cash.code;
            const quote = toOp.fields.cash.code;
            const date = fromOp.fields.date;
            if (!base || !quote || base === quote || !date) continue;
            const cacheKey = `${base}-${quote}-${date}`;

            if (untrack(() => fxMarketCache.has(cacheKey))) continue;
            fxMarketCache.set(cacheKey, null); // mark pending

            lookupFxRate(base, quote, date).then((result) => {
                if (currentGen !== fxFetchGeneration) return;
                if (!bannerSuggestions.some((s) => s.tempIdA === entry.tempIdA && s.tempIdB === entry.tempIdB)) return;
                fxMarketCache = new Map(fxMarketCache).set(cacheKey, result);
            });
        }
    });

    /** Combined for backward compat with triggerPromoteFromSuggestion */
    let allSuggestions = $derived([...bannerSuggestions]);

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
            const match = findPromoteMatch(opA.fields.type, opB.fields.type, $t, buildPromoteCtx(opA, opB));
            if (!match) return;
            // Check divergence
            const descA = opA.fields.description,
                descB = opB.fields.description;
            const tagsA = opA.fields.tags,
                tagsB = opB.fields.tags;
            const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB);
            if (diverges) {
                const labelA = opA.fields.type;
                const labelB = opB.fields.type;
                promoteMergeData = {
                    txA: {label: labelA, description: descA, tags: tagsA, date: opA.fields.date, cost_basis_override: opA.fields.cost_basis_override},
                    txB: {label: labelB, description: descB, tags: tagsB, date: opB.fields.date, cost_basis_override: opB.fields.cost_basis_override},
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
            const match = findPromoteMatch(opA.fields.type, opB.fields.type, $t, buildPromoteCtx(opA, opB));
            if (!match) return;
            const descA = opA.fields.description,
                descB = opB.fields.description;
            const tagsA = opA.fields.tags,
                tagsB = opB.fields.tags;
            const diverges = descA !== descB || JSON.stringify(tagsA) !== JSON.stringify(tagsB);
            if (diverges) {
                const labelA = `#${(opA as any).txId ?? ''} ${opA.fields.type}`;
                const labelB = `#${(opB as any).txId ?? ''} ${opB.fields.type}`;
                promoteMergeData = {
                    txA: {label: labelA, description: descA, tags: tagsA, date: opA.fields.date, cost_basis_override: opA.fields.cost_basis_override},
                    txB: {label: labelB, description: descB, tags: tagsB, date: opB.fields.date, cost_basis_override: opB.fields.cost_basis_override},
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
                        {/if}{#if deleteCount > 0}<span class="text-red-600 dark:text-red-400">{deleteCount} {$t('transactions.bulk.stateDel')}</span>{/if}{#if pendingSplits.length > 0}
                            · <span class="text-purple-600 dark:text-purple-400" data-testid="split-queued-badge">⚡ {$t('transactions.bulk.splitQueued', {values: {n: pendingSplits.length}})}</span>{/if})
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
                    {#snippet titleAction()}
                        {#if hasWacFxIssues}
                            <button type="button" class="text-xs px-2 py-0.5 rounded bg-red-100 dark:bg-red-800/40 hover:bg-red-200 dark:hover:bg-red-700/50 font-medium whitespace-nowrap" onclick={handleSyncFx} disabled={syncFxLoading} data-testid="tx-bulk-sync-fx-error">
                                {syncFxLoading ? '⏳' : '🔄'} Sync FX
                            </button>
                        {/if}
                    {/snippet}
                    {#if fieldIssues.length > 0}
                        <p class="font-semibold text-sm mt-1 mb-1">{$t('transactions.validate.issuesHeader')}</p>
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues">
                            {#each fieldIssues as issue}
                                <li>
                                    <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue">
                                        {#if issue.index < 0}{getVisualRowLabel(issue)}:
                                        {:else}{$t('transactions.bulk.rowN', {values: {n: getVisualRowLabel(issue)}})}:
                                        {/if}{@html resolveIssueMessage(issue, $t, resolverCtx)}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left">
                            {#each balanceIssues as issue}
                                <li>
                                    {#if issue.index >= 0}
                                        <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)}>
                                            {$t('transactions.bulk.rowN', {values: {n: getVisualRowLabel(issue)}})}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                        </button>
                                    {:else}
                                        {getVisualRowLabel(issue)}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                    {/if}
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </TransactionResultBanner>
            {/if}
            {#if showIssuesBanner && !formError && !commitFailed}
                <TransactionResultBanner variant="warning" title={`⚠️ ${$t('transactions.validate.issuesHeader')}`} dismissible ondismiss={() => (issuesDismissed = true)} testId="tx-bulk-issues-header">
                    {#snippet titleAction()}
                        {#if hasWacFxIssues}
                            <button type="button" class="text-xs px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/50 font-medium whitespace-nowrap" onclick={handleSyncFx} disabled={syncFxLoading} data-testid="tx-bulk-sync-fx">
                                {syncFxLoading ? '⏳' : '🔄'} Sync FX
                            </button>
                        {/if}
                    {/snippet}
                    {#if fieldIssues.length > 0}
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues">
                            {#each fieldIssues as issue}
                                <li>
                                    <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue">
                                        {#if issue.index < 0}{getVisualRowLabel(issue)}:
                                        {:else}{$t('transactions.bulk.rowN', {values: {n: getVisualRowLabel(issue)}})}:
                                        {/if}{@html resolveIssueMessage(issue, $t, resolverCtx)}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm {fieldIssues.length > 0 ? 'mt-2' : ''} mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc pl-4 space-y-0.5 text-sm text-left">
                            {#each balanceIssues as issue}
                                <li>
                                    {#if issue.index >= 0}
                                        <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)}>
                                            {$t('transactions.bulk.rowN', {values: {n: getVisualRowLabel(issue)}})}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                        </button>
                                    {:else}
                                        {getVisualRowLabel(issue)}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
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
            {#if bannerSuggestions.length > 0}
                <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 text-xs" data-testid="promote-suggest-banner">
                    <div class="font-medium text-green-800 dark:text-green-200 mb-1.5">{$t('transactions.promoteSuggest.detected')}</div>
                    <ul class="space-y-1.5">
                        {#each bannerSuggestions.slice(0, 5) as sug, idx}
                            {@const rawA = ops.find((o) => o.tempId === sug.tempIdA)}
                            {@const rawB = ops.find((o) => o.tempId === sug.tempIdB)}
                            <!-- Semantic order: "from" (negative cash) first, "to" (positive) second -->
                            {@const needSwap = rawA && rawB && rawA.fields.cash && rawB.fields.cash && Number(rawA.fields.cash.amount) > 0 && Number(rawB.fields.cash.amount) < 0}
                            {@const opA = needSwap ? rawB : rawA}
                            {@const opB = needSwap ? rawA : rawB}
                            {@const rowIdxA = opA ? ops.indexOf(opA) : -1}
                            {@const rowIdxB = sug.isDB ? ops.findIndex((o) => o.op === 'edit' && (o as any).txId === sug.dbCandidateId) : opB ? ops.indexOf(opB) : -1}
                            {@const typeA = opA?.fields.type ?? ''}
                            {@const typeB = opB?.fields.type ?? ''}
                            {@const deltaDays = opA && opB ? Math.round((new Date(opB.fields.date).getTime() - new Date(opA.fields.date).getTime()) / 86400000) : 0}
                            {@const targetLabel = $t('transactions.types.' + sug.targetType) || sug.targetType}
                            <li class="relative pl-3 flex items-center gap-1.5 flex-wrap" data-testid="promote-suggest-item-{idx}">
                                <span class="absolute left-0 top-1 text-green-800 dark:text-green-200">•</span>
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800/30 border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-700/40 font-medium"
                                    onclick={() => triggerPromoteFromSuggestion(sug)}
                                    data-testid="promote-suggest-link-{idx}"
                                >
                                    <Link2 size={12} />
                                    {$t('transactions.promoteSuggest.merge')}
                                </button>
                                <!-- Row A reference (clickable — "from" / negative side) -->
                                <button
                                    type="button"
                                    class="underline text-gray-700 dark:text-gray-300 hover:text-blue-600"
                                    onclick={() => {
                                        if (opA) tableRef?.navigateToRowId(opA.tempId);
                                    }}
                                >
                                    {rowIdxA >= 0 ? $t('transactions.promoteSuggest.rowRef', {values: {n: rowIdxA + 1}}) : typeA}
                                </button>
                                <img src={getTransactionTypeIconUrl(typeA)} alt="" class="w-4 h-4 inline object-contain" />
                                <span class="text-gray-500">{$t('common.and')}</span>
                                <!-- Row B reference -->
                                {#if sug.isDB}
                                    <button
                                        type="button"
                                        class="underline text-gray-700 dark:text-gray-300 hover:text-blue-600"
                                        onclick={() => {
                                            const op = ops.find((o) => o.op === 'edit' && (o as any).txId === sug.dbCandidateId);
                                            if (op) tableRef?.navigateToRowId(op.tempId);
                                        }}
                                    >
                                        {rowIdxB >= 0 ? $t('transactions.promoteSuggest.rowRef', {values: {n: rowIdxB + 1}}) : `#${sug.dbCandidateId}`}
                                    </button>
                                {:else}
                                    <button
                                        type="button"
                                        class="underline text-gray-700 dark:text-gray-300 hover:text-blue-600"
                                        onclick={() => {
                                            if (opB) tableRef?.navigateToRowId(opB.tempId);
                                        }}
                                    >
                                        {rowIdxB >= 0 ? $t('transactions.promoteSuggest.rowRef', {values: {n: rowIdxB + 1}}) : typeB}
                                    </button>
                                {/if}
                                <img src={getTransactionTypeIconUrl(typeB)} alt="" class="w-4 h-4 inline object-contain" />
                                <span class="text-gray-500">→</span>
                                <span class="font-medium text-green-700 dark:text-green-300">{targetLabel}</span>
                                <img src={getTransactionTypeIconUrl(sug.targetType)} alt="" class="w-4 h-4 inline object-contain" />
                                {#if deltaDays !== 0}
                                    <span class="text-gray-400">(Δ{deltaDays > 0 ? '+' : ''}{deltaDays}d)</span>
                                {/if}
                                {#if sug.targetType === 'FX_CONVERSION' && opA?.fields.cash && opB?.fields.cash}
                                    {@const aAmtFx = Number(opA.fields.cash.amount)}
                                    {@const fromOpFx = aAmtFx < 0 ? opA : opB}
                                    {@const toOpFx = aAmtFx < 0 ? opB : opA}
                                    {#if fromOpFx.fields.cash && toOpFx.fields.cash && fromOpFx.fields.cash.code !== toOpFx.fields.cash.code}
                                        {@const fxInfo = computeFxConversionInfo(Number(fromOpFx.fields.cash.amount), fromOpFx.fields.cash.code, Number(toOpFx.fields.cash.amount), toOpFx.fields.cash.code)}
                                        {#if fxInfo}
                                            {@const cacheKey = `${fxInfo.base}-${fxInfo.quote}-${fromOpFx.fields.date}`}
                                            {@const fxPoint = fxMarketCache.get(cacheKey)}
                                            {@const tooltipData = buildFxTooltipData(fxInfo, fxPoint)}
                                            <span class="text-gray-400 mx-0.5">·</span>
                                            <Tooltip html={buildFxTooltipHtml(tooltipData, $t)} position="bottom">
                                                <span class="inline-flex items-center gap-0.5 text-xs text-violet-600 dark:text-violet-400 cursor-help" data-testid="promote-suggest-fx-info-{idx}">
                                                    {@html formatCurrencyCodeHtml(fxInfo.base)}
                                                    <span>→</span>
                                                    {@html formatCurrencyCodeHtml(fxInfo.quote)}
                                                    <span class="font-mono">@ {fxInfo.impliedRate.toFixed(4)}</span>
                                                    {#if tooltipData.staleDays != null && tooltipData.staleDays > 0}
                                                        <span class="text-amber-500">⚠️</span>
                                                    {/if}
                                                </span>
                                            </Tooltip>
                                        {/if}
                                    {/if}
                                {/if}
                            </li>
                        {/each}
                    </ul>
                    {#if allSuggestions.length > 5}
                        <span class="text-gray-500 text-[11px] mt-1">{$t('transactions.promoteSuggest.bannerMore', {values: {n: allSuggestions.length - 5}})}</span>
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

            <!-- R3-B5: Delta-days filter for promote suggestions -->
            <div class="inline-flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
                <span class="hidden sm:inline">{$t('transactions.promoteSuggest.deltaLabel') || 'Max Δ days'}</span>
                <span class="sm:hidden" title="Max delta days">Δ</span>
                <input type="range" min="0" max="14" step="1" class="w-20 accent-libre-green" bind:value={maxDeltaDays} data-testid="promote-suggest-delta-input" />
                <span class="text-[11px] font-mono w-5 text-center">{maxDeltaDays}</span>
            </div>

            <!-- Inline selection toolbar moved to Right group below -->

            <!-- Right: actions -->
            <div class="ml-auto flex flex-row-reverse items-center gap-2 flex-wrap">
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={openAddRowForm} data-testid="tx-bulk-add-row" title={$t('transactions.bulk.addRow') || 'Add row'}>
                    <Plus size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.addRow') || 'Add row'}</span>
                </button>
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 border border-gray-200 dark:border-gray-600"
                    onclick={() => (importWizardOpen = true)}
                    data-testid="tx-bulk-import"
                    title={$t('importWizard.import') || 'Import'}
                >
                    <Upload size={12} /> <span class="hidden sm:inline">{$t('importWizard.import') || 'Import'}</span>
                </button>
                {#if importableSuggestions.length > 0}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 border border-amber-200 dark:border-amber-700"
                        onclick={openSuggestPicker}
                        data-testid="tx-bulk-suggest-import"
                        title={$t('transactions.bulk.suggestLightbulb') || 'Import suggested pairs'}
                    >
                        <Lightbulb size={14} />
                        <span class="text-[10px] font-medium">{importableSuggestions.reduce((n, s) => n + s.candidates.length, 0)}</span>
                    </button>
                {/if}
                {#if visibleOps.some((d) => d.op === 'edit' && (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete')) || pendingSplits.length > 0}
                    <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={resetAll} data-testid="tx-bulk-reset-all" title={$t('transactions.bulk.resetAll')}>
                        <Undo2 size={12} /> <span class="hidden sm:inline">{$t('transactions.bulk.resetAll')}</span>
                    </button>
                {/if}
                <ColumnVisibilityToggle tableRef={tableRefForToggle} />
                {#if bulkTableSelectedRows.length > 0}
                    <div class="flex items-center gap-2">
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
                actionsColumnWidth="160px"
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
    items={formItems}
    commitOnSave={false}
    unlockImmutable={formMode === 'edit'}
    availableTags={aggregatedTags}
    zIndex={70}
    openKey={formKey}
    getBulkContext={() => getBulkContextExcluding(formEditingTempId)}
    getWacResult={(tempId) => {
        // Direct lookup (standalone ADJUSTMENT)
        const direct = wacResults.get(tempId);
        if (direct) return direct;
        // Partner lookup (paired TRANSFER — WAC is on the receiver/hidden op)
        const partnerOp = getPartnerOp(tempId);
        if (partnerOp) return wacResults.get(partnerOp.tempId) ?? partnerOp._wacCache ?? null;
        // Fallback to own op's cache (e.g. after Map was cleared)
        const selfOp = ops.find((o) => o.tempId === tempId);
        return selfOp?._wacCache ?? null;
    }}
    editingTempId={formEditingTempId}
    pendingTxIds={pendingTxIds.size > 0 ? pendingTxIds : null}
    onClose={() => {
        formOpen = false;
        formEditingTempId = null;
    }}
    onPushDraft={handleFormPushed}
/>

<!-- Plan B Step 9: PickerModal for adding existing DB transactions -->
<TransactionPickerModal open={pickerOpen} excludeIds={pickerExcludeIds} onAdd={handlePickerAdd} onClose={() => (pickerOpen = false)} />

<!-- BUG-C7: Suggest picker — opens PickerModal filtered to importable candidates -->
<TransactionPickerModal open={suggestPickerOpen} excludeIds={pickerExcludeIds} includeIds={suggestPickerIncludeIds} onAdd={handlePickerAdd} onClose={() => (suggestPickerOpen = false)} />

<!-- Plan D2 Step C4: PromoteMergeModal for resolving divergent fields during promote -->
<PromoteMergeModal
    open={promoteMergeOpen}
    txA={promoteMergeData?.txA}
    txB={promoteMergeData?.txB}
    targetTypeLabel={promoteMergeData?.targetTypeLabel ?? ''}
    {availableTags}
    onConfirm={onBulkPromoteMergeConfirm}
    onCancel={() => {
        promoteMergeOpen = false;
        promoteMergeData = null;
    }}
/>

<!-- Phase 07 Part 5 v5 M1: BRIM Import Wizard -->
<ImportWizardModal open={importWizardOpen} zIndex={70} onClose={() => (importWizardOpen = false)} {onImportBatch} />
