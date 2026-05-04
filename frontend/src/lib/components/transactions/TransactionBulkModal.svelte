<!--
  TransactionBulkModal.svelte — Unified bulk editor for transactions.

  Built on top of `DataTable.svelte` with editable cells. Supports a mixed bag
  of new drafts + existing rows + rows marked for deletion, validated+committed
  together via the unified backend pipeline.

  Modes (backward compat — internally everything is a mixed batch):
  - 'create-many' → drafts seeded from `initialRows` (id stripped) or one blank row.
  - 'edit-many'   → drafts pre-filled from `initialRows`.

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
    import {X, Plus, Pencil, Copy, Trash2, Check} from 'lucide-svelte';

    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';

    import type {ColumnDef, CellContent} from '$lib/components/table/types';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded, getAssetInfo, getAllAssets} from '$lib/stores/assetStore';
    import {ensureBrokersLoaded, getAllBrokers, brokerStoreVersion, type BrokerInfo} from '$lib/stores/brokerStore';
    import {ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {type TransactionTypeCode, getTypeRule, isDraftReadyForValidation, ensureTypesLoaded} from '$lib/stores/transactionTypeStore';
    import {createValidateScheduler} from '$lib/utils/useValidateScheduler.svelte';
    import {saveWithRetry, extractErrorMessage, extractValidationIssues} from '$lib/utils/saveWithRetry';
    import {resolveIssueMessage, type ResolverContext} from '$lib/utils/resolveValidationMessage';
    import {generateUUID} from '$lib/utils/uuid';
    import {formatCurrencyAmountHtml} from '$lib/utils/currencyFormat';
    import TransactionFormModal from './TransactionFormModal.svelte';

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
        code?: string | null;
        params?: Record<string, any> | null;
        field?: string | null;
        /** Pydantic loc path (e.g. "body.creates.0.broker_id"). */
        loc?: string;
    }

    type Mode = 'create-many' | 'edit-many';

    interface DraftRow {
        tempId: string; // stable id used by DataTable.getRowId + navigateToRowId
        status: 'new' | 'edited' | 'original' | 'delete';
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
        // B1-13: partner data for paired types (Da:/A: display)
        partnerBrokerId?: number;
        partnerCash?: {code: string; amount: string} | null;
        partnerDate?: string;
        /** DB id of the hidden partner row (for edit-many paired rendering). */
        _partnerId?: number;
        /** True for the "to" half of a merged pair — filtered out from DataTable display. */
        _hidden?: boolean;
    }

    interface Props {
        open: boolean;
        mode: Mode;
        initialRows?: TXReadItem[];
        /** Bugfix-5 §U20: tag suggestions sourced from the parent's loaded
         *  transactions. The bulk modal augments this list with any tag that
         *  appears in its in-flight drafts (so newly-typed tags are
         *  immediately available across rows). */
        availableTags?: string[];
        /** When set, auto-opens the FormModal on mount:
         *  'edit' → opens the first draft for editing
         *  'create' → opens a new row form */
        autoOpenForm?: 'create' | 'edit' | null;
        onClose: () => void;
        onCommitted?: (resp: unknown) => void;
    }

    let {open, mode, initialRows = [], availableTags = [], autoOpenForm = null, onClose, onCommitted}: Props = $props();

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
        return {
            tempId: generateUUID(),
            status: isCreate ? 'new' : 'original',
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

    // Reset on open — compute `next` locally first, then assign once (avoids
    // [[problems/svelte5-effect-read-write-loop]]).
    $effect(() => {
        if (!open) return;
        const m = mode;
        const rows = initialRows;
        untrack(() => {
            issues = [];
            formError = null;
            commitFailed = false;
            confirmCloseOpen = false;
            // Bugfix-2: in create-many with no initial rows, start with an
            // EMPTY grid — the user adds rows via the nested FormModal.
            const next: DraftRow[] = rows.length > 0 ? rows.map((r) => fromTx(r, m)) : [];

            // B1-13: In edit-many, detect paired rows and merge them into
            // a single visible row with partner data for Da:/A: rendering.
            if (m === 'edit-many') {
                mergePairedRows(next, rows);
            }

            drafts = next;
            initialDraftsKey = serializeDrafts(next);

            // Determine whether to auto-open the FormModal
            const autoForm = autoOpenForm;
            if (autoForm === 'edit' && next.length > 0) {
                // Auto-open FormModal on the first row (edit single / clone single)
                queueMicrotask(() => openEditRowForm(next[0]));
            } else if (autoForm === 'create' && next.length > 0) {
                // Clone: row is 'new' so openEditRowForm uses create mode
                queueMicrotask(() => openEditRowForm(next[0]));
            } else if (m === 'create-many' && rows.length === 0) {
                // Auto-open for brand-new empty grid
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
                if (r.quantityMode === 'forbidden') merged.quantity = '0';
                if (!r.eventLinkable) merged.asset_event_id = null;
                if (merged.type !== 'TRANSFER') merged.cost_basis_override = '';
            }
            if (merged.status === 'original') merged.status = 'edited';
            return merged;
        });
    }

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
            related_transaction_id: (d._partnerId ?? (d.partnerBrokerId != null ? -1 : null)),
            tags: d.tags,
            description: d.description,
            cost_basis_override: d.cost_basis_override || null,
            asset_event_id: d.asset_event_id,
            created_at: d.created_at,
            updated_at: d.updated_at,
        };
    }

    /** C1-fix: find the hidden partner draft for a visible paired draft row. */
    function findPartnerDraft(d: DraftRow): DraftRow | undefined {
        if (!d.link_uuid) return undefined;
        return drafts.find((p) => p._hidden && p.link_uuid === d.link_uuid && p.tempId !== d.tempId);
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
            if (merged.status === 'original') merged.status = 'edited';
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

    /** Detect paired rows in the initialRows and merge them: the "from" side
     *  keeps partner display data, the "to" side is flagged `_hidden`. */
    function mergePairedRows(draftArr: DraftRow[], sourceRows: TXReadItem[]) {
        // Map DB id → draft index
        const idToIdx = new Map<number, number>();
        draftArr.forEach((d, i) => { if (d.id != null) idToIdx.set(d.id, i); });
        // Map DB id → source TXReadItem for partner lookup
        const idToSource = new Map<number, TXReadItem>();
        sourceRows.forEach((r) => idToSource.set(r.id, r));

        const processed = new Set<number>(); // indices already merged

        for (let i = 0; i < draftArr.length; i++) {
            if (processed.has(i)) continue;
            const d = draftArr[i];
            const rule = getTypeRule(d.type);
            if (!rule.requiresPair) continue;

            // Find partner via original.related_transaction_id
            const partnerId = d.original?.related_transaction_id;
            if (partnerId == null) continue;
            const pIdx = idToIdx.get(partnerId);
            if (pIdx == null || pIdx === i || processed.has(pIdx)) continue;

            const partner = draftArr[pIdx];
            // Determine from/to: "from" side has negative cash or negative qty
            const cashAmt = Number(d.original?.cash?.amount ?? 0);
            const partnerCashAmt = Number(partner.original?.cash?.amount ?? 0);
            let fromIdx = i, toIdx = pIdx;
            if (cashAmt > 0 && partnerCashAmt <= 0) {
                fromIdx = pIdx;
                toIdx = i;
            } else if (cashAmt === 0 && partnerCashAmt === 0) {
                // For TRANSFER: check quantity sign
                const qtyAmt = Number(d.original?.quantity ?? 0);
                if (qtyAmt > 0) {
                    fromIdx = pIdx;
                    toIdx = i;
                }
            }

            const fromDraft = draftArr[fromIdx];
            const toDraft = draftArr[toIdx];
            // Set partner data on the visible "from" row
            fromDraft.partnerBrokerId = toDraft.broker_id;
            fromDraft.partnerCash = toDraft.cash;
            fromDraft.partnerDate = toDraft.date;
            fromDraft._partnerId = toDraft.id;
            // Hide the "to" half
            toDraft._hidden = true;
            processed.add(fromIdx);
            processed.add(toIdx);
        }
    }

    function removeRow(tempId: string) {
        // C3-fix: for paired 'new' rows, also remove the hidden partner.
        const target = drafts.find((d) => d.tempId === tempId);
        if (target && target.link_uuid && target.status === 'new') {
            drafts = drafts.filter((d) => {
                if (d.tempId === tempId) return false;
                // Remove hidden partner with same link_uuid
                if (d._hidden && d.link_uuid === target.link_uuid) return false;
                return true;
            });
        } else {
            drafts = drafts.filter((d) => d.tempId !== tempId);
        }
    }

    /** R6-B.4: Mark an existing row for deletion (toggle). */
    function markDelete(tempId: string) {
        drafts = drafts.map((d) => {
            if (d.tempId !== tempId) return d;
            if (d.status === 'delete') {
                // Unmark: revert to 'edited' (user already touched it) or 'original'
                return {...d, status: d.original ? 'edited' : 'new'};
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

    // -----------------------------------------------------------------
    // Shared helpers for collectCreate / collectUpdate
    // -----------------------------------------------------------------

    interface SignResult {
        signedQty: string;
        buildCash: (c: {code: string; amount: string} | null | undefined) => {code: string; amount: string} | null;
    }

    /** Apply sign-flip rules for quantity and cash based on the type rule. */
    function applySignRules(d: DraftRow, rule: ReturnType<typeof getTypeRule>): SignResult {
        const negQty = rule.quantityRule === 'negative';
        const negCash = rule.cashSign === 'negative';
        const signedQty = negQty ? String(-Math.abs(Number(d.quantity))) : d.quantity;
        const buildCash = (c: {code: string; amount: string} | null | undefined) => {
            if (!c) return null;
            if (negCash) return {code: c.code, amount: String(-Math.abs(Number(c.amount)))};
            return {code: c.code, amount: c.amount};
        };
        return {signedQty, buildCash};
    }

    type FieldDef = [
        key: string,
        currentValue: unknown,
        originalValue: unknown,
        comparator?: (a: unknown, b: unknown) => boolean,
        outputTransform?: (v: unknown) => unknown,
    ];

    /** Compare each field pair and collect changed keys into a partial record. */
    function diffFields(fields: FieldDef[]): Record<string, unknown> {
        const changes: Record<string, unknown> = {};
        for (const [key, cur, orig, comparator, transform] of fields) {
            const equal = comparator ? comparator(cur, orig) : cur === orig;
            if (!equal) {
                changes[key] = transform ? transform(cur) : cur;
            }
        }
        return changes;
    }

    function collectCreate(d: DraftRow): Record<string, unknown> {
        const rule = getTypeRule(d.type);
        const {signedQty, buildCash} = applySignRules(d, rule);
        const out: Record<string, unknown> = {
            broker_id: d.broker_id,
            type: d.type,
            date: d.date,
            quantity: signedQty,
        };
        if (d.asset_id != null && rule.assetField !== 'forbidden') out.asset_id = d.asset_id;
        if (d.cash && rule.cashField !== 'forbidden') out.cash = buildCash(d.cash);
        if (d.tags.length > 0) out.tags = d.tags;
        if (d.description.trim()) out.description = d.description.trim();
        if (d.asset_event_id != null && rule.eventLinkable) out.asset_event_id = d.asset_event_id;
        if (d.cost_basis_override.trim()) out.cost_basis_override = d.cost_basis_override.trim();
        if (d.link_uuid && rule.requiresPair) out.link_uuid = d.link_uuid;
        return out;
    }

    function collectUpdate(d: DraftRow): Record<string, unknown> | null {
        if (!d.original || d.id == null) return null;
        const rule = getTypeRule(d.type);
        const {signedQty, buildCash} = applySignRules(d, rule);
        const orig = d.original;
        const {signedQty: origSignedQty, buildCash: origBuildCash} = applySignRules(fromTx(orig, 'edit-many'), rule);
        void origBuildCash; // unused — buildCash is used for both sides

        const jsonEq = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
        const nullishEq = (a: unknown, b: unknown) => (a || null) === (b || null);

        const fields: FieldDef[] = [
            // H6 sign-flip: type can change via swap groups
            ['type', d.type, orig.type],
            ['date', d.date, orig.date],
            ['broker_id', d.broker_id, orig.broker_id],
            ['asset_id', d.asset_id ?? null, orig.asset_id ?? null],
            ['quantity', signedQty, origSignedQty],
            ['cash', buildCash(d.cash), buildCash(orig.cash), jsonEq],
            ['tags', d.tags, orig.tags ?? [], jsonEq],
            ['description', d.description || null, orig.description ?? null, nullishEq],
            ['cost_basis_override', d.cost_basis_override || null, orig.cost_basis_override ?? null, nullishEq],
            ['asset_event_id', d.asset_event_id, orig.asset_event_id ?? null, undefined, (v) => (v as number | null) ?? 0],
        ];

        const changes = diffFields(fields);
        return {id: d.id, ...changes};
    }

    // =========================================================================
    // Validate scheduler
    // =========================================================================

    const scheduler = createValidateScheduler({
        enabled: () => drafts.length > 0 && drafts.length <= AUTO_VALIDATE_THRESHOLD && drafts.some((d) => d.status !== 'delete' && isDraftReadyForValidation(d)),
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
                if (d.status === 'new') creates.push(collectCreate(d));
                else if (d.status === 'edited') {
                    const upd = collectUpdate(d);
                    if (upd && Object.keys(upd).length > 1) updates.push(upd);
                } else if (d.status === 'delete' && d.id != null) {
                    deletes.push(d.id);
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
        assets: getAllAssets() as unknown as Array<{id: number; display_name: string}>,
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
                if (d.status === 'new') {
                    creates.push(collectCreate(d));
                } else if (d.status === 'edited') {
                    const upd = collectUpdate(d);
                    if (upd && Object.keys(upd).length > 1) updates.push(upd);
                } else if (d.status === 'delete' && d.id != null) {
                    deletes.push(d.id);
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

            const result = await saveWithRetry(
                () => zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never),
                {fallback: $t('transactions.bulk.saveFailed'), toast: false},
            );
            if (result.status === 'error') {
                formError = result.message;
                return;
            }
            const resp = result.data as {committed?: boolean; issues?: ValidationIssue[]};
            if (!resp.committed) {
                issues = resp.issues ?? [];
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

    const editMode = $derived(mode === 'edit-many');

    // =========================================================================
    // DRY helpers for readonly cell rendering
    // =========================================================================

    /** Render a Da:/A: dual-line cell for paired rows. */
    function renderDualHtml(fromText: string, toText: string): string {
        return `<div class="flex flex-col gap-0.5 text-xs leading-tight min-h-[2.5rem] justify-center"><span><span class="inline-block w-12 text-gray-400 dark:text-gray-500 font-medium">${$t('transactions.form.from')}:</span> ${fromText}</span><hr class="border-gray-200 dark:border-gray-600 my-0.5"/><span><span class="inline-block w-12 text-gray-400 dark:text-gray-500 font-medium">${$t('transactions.form.to')}:</span> ${toText}</span></div>`;
    }

    /** Readonly type badge with icon. */
    function renderTypeHtml(type: string): string {
        const label = $t(`transactions.types.${type}`) || type;
        const slug = type.toLowerCase().replace(/_/g, '-');
        const isPair = getTypeRule(type).requiresPair;
        const prefix = isPair ? '↔ ' : '';
        return `<span class="inline-flex items-center gap-1 text-xs"><img src="/icons/transactions/${slug}.png" alt="" class="w-4 h-4 object-contain shrink-0" onerror="this.style.display='none'"/>${prefix}${label}</span>`;
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
        const iconUrl = info?.icon_url;
        const iconHtml = iconUrl
            ? `<img src="${iconUrl}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />`
            : '';
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
            try { iconSrc = new URL(b.portal_url).origin + '/favicon.ico'; } catch {}
        }
        const iconHtml = iconSrc
            ? `<img src="${iconSrc}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />`
            : '';
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
                cell: (row): CellContent => ({
                    type: 'html',
                    html: row.status === 'new' ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">new</span>' : row.status === 'edited' ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">edit</span>' : row.status === 'delete' ? '<span class="px-1.5 py-0.5 text-[10px] rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">🔴 del</span>' : '<span class="text-gray-300 dark:text-gray-600">·</span>',
                }),
            },
            {
                id: 'id',
                header: 'ID',
                type: 'text',
                width: 70,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => ({type: 'html', html: row.id != null ? `#${row.id}` : '—'}),
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
                width: 140,
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
                width: 85,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    if (getTypeRule(row.type).quantityMode === 'forbidden') {
                        return {type: 'html', html: '<span class="text-gray-400 italic">n/a</span>'};
                    }
                    const qty = row.quantity ?? '0';
                    // H2-fix: paired rows with non-zero qty → show Da:/A: with absolute values
                    const rule = getTypeRule(row.type);
                    if (rule.requiresPair && row.partnerBrokerId != null && Number(qty) !== 0) {
                        const absQty = String(Math.abs(Number(qty)));
                        return {type: 'html', html: renderDualHtml(absQty, absQty)};
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
                width: 140,
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
                cell: (row): CellContent => ({type: 'html', html: row.description ? `<span class="text-xs text-gray-600 dark:text-gray-300 truncate block">${row.description}</span>` : '<span class="text-gray-400">—</span>'}),
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

    let rowActions = $derived([
        {
            id: 'edit-single',
            icon: Pencil,
            label: () => $t('transactions.bulk.editSingle') || 'Edit row',
            onClick: (row: DraftRow) => openEditRowForm(row),
            visible: (row: DraftRow) => row.status !== 'delete',
        },
        {
            id: 'clone',
            icon: Copy,
            label: () => $t('transactions.bulk.cloneRow') || 'Clone row',
            onClick: (row: DraftRow) => cloneRow(row.tempId),
            visible: (row: DraftRow) => row.status !== 'delete',
        },
        {
            id: 'mark-delete',
            icon: Trash2,
            label: (row: DraftRow) => row.status === 'delete'
                ? ($t('transactions.bulk.unmarkDelete') || 'Restore')
                : ($t('transactions.bulk.markDelete') || 'Mark for deletion'),
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
            id: 'reset',
            icon: () => '↺',
            label: () => $t('transactions.bulk.resetRow'),
            onClick: (row: DraftRow) => resetRow(row.tempId),
            visible: (row: DraftRow) => !!row.original && row.status !== 'delete',
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

    // B1-13: filter out hidden partner rows for display
    let visibleDrafts = $derived(drafts.filter((d) => !d._hidden));

    let newCount = $derived(visibleDrafts.filter((d) => d.status === 'new').length);
    let editedCount = $derived(visibleDrafts.filter((d) => d.status === 'edited').length);
    let deleteCount = $derived(visibleDrafts.filter((d) => d.status === 'delete').length);
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
        formOpen = true;
    }
    function openEditRowForm(row: DraftRow) {
        // When editing a 'new' draft, open in create mode so type stays editable;
        // formEditingTempId is still set so handleFormPushed patches (not adds).
        formMode = row.status === 'new' ? 'create' : 'edit';
        formInitial = draftToTxLike(row);
        formEditingTempId = row.tempId;
        // C1-fix: for paired drafts, inject partner data so FormModal can
        // populate the dual form without fetching from the API.
        const partner = findPartnerDraft(row);
        formPartnerRow = partner ? draftToTxLike(partner) : null;
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

    /** Add a paired draft row: visible "from" draft + hidden "to" draft. */
    function addDualRowFromForm(payload: Record<string, unknown>) {
        const items = payload._items as Record<string, unknown>[];
        if (!items || items.length < 2) { addRowFromForm(payload); return; }
        const linkUuid = (items[0].link_uuid as string) ?? generateUUID();

        // "From" side — visible row
        const fromDraft = emptyDraft();
        applyFormPayload(fromDraft, items[0]);
        fromDraft.link_uuid = linkUuid;
        fromDraft.partnerBrokerId = (items[1].broker_id as number) ?? 0;
        fromDraft.partnerCash = (items[1].cash as DraftRow['partnerCash']) ?? null;
        fromDraft.partnerDate = (items[1].date as string) ?? fromDraft.date;

        // "To" side — hidden partner
        const toDraft = emptyDraft();
        applyFormPayload(toDraft, items[1]);
        toDraft.link_uuid = linkUuid;
        toDraft._hidden = true;

        drafts = [...drafts, fromDraft, toDraft];
    }

    /** Patch a paired draft row: update both visible and hidden partner. */
    function patchDualRowFromForm(tempId: string, payload: Record<string, unknown>) {
        const items = payload._items as Record<string, unknown>[];
        if (!items || items.length < 2) { patchRowFromForm(tempId, payload); return; }
        const linkUuid = (items[0].link_uuid as string) ?? generateUUID();

        drafts = drafts.map((d) => {
            if (d.tempId === tempId) {
                // Update the visible "from" row
                const merged = {...d};
                applyFormPayload(merged, items[0]);
                merged.link_uuid = linkUuid;
                merged.partnerBrokerId = (items[1].broker_id as number) ?? 0;
                merged.partnerCash = (items[1].cash as DraftRow['partnerCash']) ?? null;
                merged.partnerDate = (items[1].date as string) ?? merged.date;
                if (merged.status === 'original') merged.status = 'edited';
                return merged;
            }
            return d;
        });

        // Find or create the hidden partner draft
        const existingPartner = drafts.find(
            (d) => d._hidden && d.link_uuid === linkUuid && d.tempId !== tempId
        );
        if (existingPartner) {
            drafts = drafts.map((d) => {
                if (d.tempId !== existingPartner.tempId) return d;
                const merged = {...d};
                applyFormPayload(merged, items[1]);
                merged.link_uuid = linkUuid;
                if (merged.status === 'original') merged.status = 'edited';
                return merged;
            });
        } else {
            // Create a new hidden partner draft
            const toDraft = emptyDraft();
            applyFormPayload(toDraft, items[1]);
            toDraft.link_uuid = linkUuid;
            toDraft._hidden = true;
            drafts = [...drafts, toDraft];
        }
    }

    // Cast to `never` is required because DataTable<T> is generic and Svelte 5
    // template attribute type-checking can't refine through the bind:this ref.
    // Doing this in script keeps the template free of `as` casts (parser-friendly).
    let tableRefForToggle = $derived(tableRef as never);
    let rowActionsForTable = $derived(rowActions as never);

    /** R6-B.4: Red tint for rows marked for deletion. */
    function getRowClass(row: DraftRow): string {
        if (row.status === 'delete') return 'bg-red-50/60 dark:bg-red-950/20 line-through opacity-60';
        // B1-13: visual indicator for paired rows
        if (getTypeRule(row.type).requiresPair && row.partnerBrokerId != null) return 'border-l-2 border-l-indigo-400 dark:border-l-indigo-500';
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
</script>

<ModalBase {open} maxWidth="none" onRequestClose={requestClose} testId="tx-bulk-modal" allowOverflow={true} contentClass="max-w-[95vw] w-[95vw]">
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="tx-bulk-modal-root">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-bulk-title">
                📋 {$t('transactions.bulk.title', {values: {total: visibleDrafts.length}})}
                {#if actionCount > 0}
                    <span class="text-sm font-normal text-gray-500 dark:text-gray-400">
                        ({#if newCount > 0}<span class="text-emerald-600 dark:text-emerald-400">{newCount} {$t('transactions.bulk.stateNew')}</span>{/if}{#if newCount > 0 && (editedCount > 0 || deleteCount > 0)} · {/if}{#if editedCount > 0}<span class="text-amber-600 dark:text-amber-400">{editedCount} {$t('transactions.bulk.stateEdit')}</span>{/if}{#if editedCount > 0 && deleteCount > 0} · {/if}{#if deleteCount > 0}<span class="text-red-600 dark:text-red-400">{deleteCount} {$t('transactions.bulk.stateDel')}</span>{/if})
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
                <InfoBanner variant="error" dismissible ondismiss={() => (formError = null)}>
                    <p class="font-semibold mb-1" data-testid="tx-bulk-error">⛔ {$t('transactions.bulk.rolledBackTitle')}</p>
                    <p>{formError}</p>
                </InfoBanner>
            {:else if commitFailed && issues.length > 0}
                <InfoBanner variant="error" dismissible ondismiss={() => (commitFailed = false)}>
                    <p class="font-semibold mb-1" data-testid="tx-bulk-error">⛔ {$t('transactions.bulk.rolledBackTitle')}</p>
                    {#if fieldIssues.length > 0}
                        <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.issuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-bulk-issues">
                            {#each fieldIssues as issue}
                                <li>
                                    <button type="button" class="underline hover:opacity-80" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue">
                                        {$t('transactions.bulk.rowN', {values: {n: issue.index + 1}})}: {resolveIssueMessage(issue, $t, resolverCtx)}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm">
                            {#each balanceIssues as issue}
                                {@const resolvedRow = findRowForBalanceIssue(issue)}
                                <li>
                                    {#if resolvedRow >= 0}
                                        <button type="button" class="underline hover:opacity-80" onclick={() => { const d = drafts[resolvedRow]; if (d) tableRef?.navigateToRowId(d.tempId); }}>
                                            {$t('transactions.bulk.rowN', {values: {n: resolvedRow + 1}})}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                        </button>
                                    {:else}
                                        {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                    {/if}
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </InfoBanner>
            {/if}
            {#if showIssuesBanner && !formError && !commitFailed}
                <InfoBanner variant="warning" dismissible ondismiss={() => (issuesDismissed = true)}>
                    {#if fieldIssues.length > 0}
                        <p class="font-semibold text-sm mb-1.5" data-testid="tx-bulk-issues-header">{$t('transactions.validate.issuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-bulk-issues">
                            {#each fieldIssues as issue}
                                <li>
                                    <button type="button" class="underline hover:opacity-80" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue">
                                        {$t('transactions.bulk.rowN', {values: {n: issue.index + 1}})}: {resolveIssueMessage(issue, $t, resolverCtx)}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm {fieldIssues.length > 0 ? 'mt-2' : ''} mb-1.5">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm">
                            {#each balanceIssues as issue}
                                {@const resolvedRow = findRowForBalanceIssue(issue)}
                                <li>
                                    {#if resolvedRow >= 0}
                                        <button type="button" class="underline hover:opacity-80" onclick={() => { const d = drafts[resolvedRow]; if (d) tableRef?.navigateToRowId(d.tempId); }}>
                                            {$t('transactions.bulk.rowN', {values: {n: resolvedRow + 1}})}: {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                        </button>
                                    {:else}
                                        {@html resolveIssueMessage(issue, $t, resolverCtx)}
                                    {/if}
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </InfoBanner>
            {/if}
            {#if visibleDrafts.length > AUTO_VALIDATE_THRESHOLD}
                <InfoBanner variant="info">
                    <p data-testid="tx-bulk-auto-off">ⓘ {$t('transactions.validate.autoOff', {values: {n: visibleDrafts.length, threshold: AUTO_VALIDATE_THRESHOLD}})}</p>
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
            <div class="ml-auto flex flex-row-reverse items-center gap-2 flex-wrap">
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={openAddRowForm} data-testid="tx-bulk-add-row">
                    <Plus size={12} /> {$t('transactions.bulk.addRow') || 'Add row'}
                </button>
                {#if mode === 'edit-many'}
                    <button type="button" class="px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={resetAll} data-testid="tx-bulk-reset-all">{$t('transactions.bulk.resetAll')}</button>
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
                stickyActions={false}
                {getRowClass}
                onRowDoubleClick={(row) => openEditRowForm(row)}
            />
        </div>

        <!-- Footer (Bugfix-4 §U16: validate-now on the left, no duplicate chip
             /issue-count — the green/warning banners above are the single
             source of truth for validate state). -->
        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t border-gray-100 dark:border-slate-700 shrink-0 text-xs">
            <div class="flex items-center gap-2 flex-wrap">
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={() => scheduler.trigger('manual')} data-testid="tx-bulk-validate-now">
                    ⚡ {$t('transactions.validate.now')}
                </button>
                {#if scheduler.state.isValidating}
                    <span class="text-[11px] text-gray-500 dark:text-gray-400" data-testid="tx-bulk-validating">{$t('transactions.validate.validating')}</span>
                {:else if isFreshlyValid && !formError && !commitFailed}
                    <span class="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1" data-testid="tx-bulk-valid">
                        <Check size={14} /> {$t('transactions.validate.ok')}
                    </span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600" onclick={requestClose} data-testid="tx-bulk-cancel">{$t('common.cancel')}</button>
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={commitDisabled} onclick={commit} data-testid="tx-bulk-commit">
                    💾 {commitLabel}
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
    onClose={() => {
        formOpen = false;
        formEditingTempId = null;
        formPartnerRow = null;
    }}
    onPushDraft={handleFormPushed}
/>

