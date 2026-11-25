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
    import {todayIso} from '$lib/utils/dateOnly';
    import {onDestroy, tick, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {X, Plus, Pencil, Copy, Trash2, Check, Undo2, Save, Unlink, Link2, Lightbulb, Upload, ChevronDown, ChevronRight} from 'lucide-svelte';

    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import BrimEvidenceTable from '$lib/features/transactions/import/BrimEvidenceTable.svelte';
    import {initialCostBasisMode, remainingTodos, withoutPossibleSplit, possibleSplitEntries as buildSplitEntries, rewardFillCandidates, applyRewardFill, type PossibleSplitEntry, type RewardFillAnswer, type RewardFillCounts} from './bulkTodos';
    import {fetchRewardValues} from '$lib/features/transactions/form/rewardValue';
    import {isPreFloorDateTodo, preFloorEntries as buildPreFloorEntries} from '$lib/features/transactions/preFloorDate';
    import EventCreateMiniModal from '../events/EventCreateMiniModal.svelte';
    import {resolveBrimTodoMessage} from '$lib/features/transactions/resolveBrimNotice';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import TransactionResultBanner from './TransactionResultBanner.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';

    import type {BulkAction, ColumnDef, CellContent} from '$lib/components/table/types';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded, getAssetInfo, getAllAssets} from '$lib/stores/reference/assetStore';
    import {ensureBrokersLoaded, getAccessibleBrokers, getEditableBrokers, brokerStoreVersion, type BrokerInfo} from '$lib/stores/reference/brokerStore';
    import {getBrokerIconHtmlById} from '$lib/utils/broker/brokerHelpers';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {type TransactionTypeCode, getTypeRule, isDraftReadyForValidation, ensureTypesLoaded, isTypesLoaded, getTransactionTypeIconUrl, getCostBasisRule} from '$lib/features/transactions/transactionTypeStore';
    import {findPromoteMatch, type PromoteContext} from '$lib/features/transactions/transactionTypeStore';
    import PromoteMergeModal from './PromoteMergeModal.svelte';
    import PromoteAllModal, {type PromoteAllStrategy} from './PromoteAllModal.svelte';
    import {createValidateScheduler} from '$lib/features/transactions/useValidateScheduler.svelte';
    import {commitTransactions, validateTransactions} from '$lib/features/transactions/txCommitApi';
    import {buildCreatePayload, buildUpdateDiff, buildBatchPayload, diffDualItem, applySign, applySignRules, exactDecimalSign, magnitudeForRule, upgradeAutoToDetail, type TxFields, type TxOriginal, type ImportTodo} from '$lib/features/transactions/txPayloadHelpers';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {
        buildBulkOperationIndex,
        buildBulkRowLabels,
        createBulkDateComparator,
        firstAutoCostRefusalRowId,
        isBulkBalanceIssue,
        resolveBulkIssueRows,
        serializeOps,
        settleBulkIssueSnapshot,
        type BulkBatchResult,
        type BulkIssueRow,
        type BulkIssueSnapshotEntry,
        type BulkOperationIndex,
        type IdentifiedBulkOp,
    } from '$lib/features/transactions/bulk/bulkDisplay';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {autoCostCellState} from '$lib/features/transactions/bulk/costCellState';
    import {unitPriceCellHtml} from '$lib/features/transactions/unitPriceCell';
    import {cashAmountsCancel, promoteNotesDiverge, promotePairOrder, resolvePromoteAllFields, TX_DESCRIPTION_MAX_LENGTH} from '$lib/features/transactions/bulk/promoteHelpers';
    import {assetQuantitiesCancel, importableSuggestions as importableFromResults, mixedPromotePairs, newRowSuggestId} from '$lib/features/transactions/bulk/promoteSuggest';
    import {resolveIssueMessage, type ResolverContext} from '$lib/features/transactions/resolveValidationMessage';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {generateUUID} from '$lib/utils/core/uuid';
    import {formatCurrencyAmountHtml, formatCurrencyCodeHtml} from '$lib/utils/currency/currencyFormat';
    import {getStringColor} from '$lib/utils/colors';
    import {getUserStorage} from '$lib/utils/storage';
    import {lookupFxRate, type FxDataPoint} from '$lib/features/fx/fxStoreRegistry';
    import {computeFxConversionInfo, buildFxTooltipData, buildFxTooltipHtml} from '$lib/features/fx/fxConversionHelper';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import TransactionFormModal from '../form/TransactionFormModal.svelte';
    import TransactionPickerModal from './TransactionPickerModal.svelte';
    import ImportWizardModal from '../import/ImportWizardModal.svelte';
    import {txStoreGet, txStoreCount, txStoreAddExtras} from '$lib/features/transactions/txStore.svelte';
    import {
        adoptCharges,
        applyChargeDrafts,
        chargeDraftsFor,
        chargeParentFields,
        foldBulkCharges,
        isUnderParent,
        isPairLeg,
        parentNeedsRef,
        remapChargeOf,
        rowAnchor,
        applyDeleteChoice,
        linkedChargesOf,
        planBulkDelete,
        withoutRows,
        bulkLinkSelection,
        unlinkableCharges,
        unlinkSelectedCharges,
        linkInBulk,
        rowsWithLinkedCharges,
        unlinkCharge,
        type BulkDeletePlan,
        type ChargesUnread,
        cloneChargeLink,
        cloneChargesUnder,
        wireClonedRows,
        bulkChargeCandidates,
        type BulkChargeProbe,
        newGroupOf,
        syncNewGroup,
    } from './bulkCharges';
    import {SPLIT_TYPE_MAP, splitHalfType, postSplitType, splitTypeToSend} from './splitTypes';
    import {txRowRef} from '../chargeLinkRules';
    import {canEditBroker} from '$lib/stores/reference/brokerStore';
    import TxChargesActionModal from '../TxChargesActionModal.svelte';
    import type {ChargeDraft} from '../form/txCharges';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {guideAnchor, guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {TRANSACTION_BULK_STEP_IDS, type TransactionBulkStepId} from '$lib/features/onboarding/onboardingGuideCatalog';
    import {resolveFormItemsFromOps, type FormModalItems} from '../resolveFormItems';
    import type {TXReadItem, ValidationIssue} from '../types';
    import type {DraftFields, PendingOp, PromoteSelection, SuggestEntry, WacResultEntry} from './txBulkTypes';
    import TxBulkBanners from './TxBulkBanners.svelte';
    import TxBulkToolbar from './TxBulkToolbar.svelte';
    import type {TransactionCreateItem} from '$lib/types';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import {uiLocale} from '$lib/stores/app/uiLocale';

    // =========================================================================
    // Types
    // =========================================================================

    /** WorkspaceIntent — declarative API for opening the BulkModal.
     *  +page passes only action + txIds; BulkModal resolves data from txStore. A delete after the panel V1 (66 F6) names
     *  the charges to unlink (`unlinkIds`) and the charges chosen with their parent (`chargeIds`, 66 F7-d). */
    export type WorkspaceIntent = {action: 'create'} | {action: 'import'} | {action: 'edit'; txIds: number[]} | {action: 'delete'; txIds: number[]; unlinkIds?: number[]; chargeIds?: number[]} | {action: 'clone'; txIds: number[]};

    interface Props {
        open: boolean;
        intent?: WorkspaceIntent;
        availableTags?: string[];
        /** Pre-populates the broker field for new rows (create) and the global broker
         *  selector (import) — e.g. when opened from a broker-scoped page. The field
         *  stays visible/editable; this only changes its initial value, it never skips
         *  a step or restricts the linked-transaction picker (which always searches
         *  across all brokers, unaffected by this prop). */
        defaultBrokerId?: number;
        onClose: () => void;
        onCommitted?: (resp: unknown) => void;
    }

    let {open, intent, availableTags = [], defaultBrokerId, onClose, onCommitted}: Props = $props();

    const AUTO_VALIDATE_THRESHOLD = 50;

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

    /** Default DraftFields for a brand-new transaction. */
    function defaultFields(): DraftFields {
        const brokers = getEditableBrokers();
        // defaultBrokerId (e.g. opened from a broker-scoped page) wins over the
        // single-broker heuristic; both are just an initial value, still editable.
        const defaultBroker = defaultBrokerId ?? (brokers.length === 1 ? brokers[0].id : 0);
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

    /** Monotonic creation stamp for new rows. Their tempId is a random UUID, so it cannot order them. */
    let createdSeqCounter = 0;
    function nextCreatedSeq(): number {
        return createdSeqCounter++;
    }

    /** Create an empty 'create' PendingOp. */
    function createOpEmpty(): PendingOp {
        return {op: 'create', tempId: generateUUID(), createdSeq: nextCreatedSeq(), fields: defaultFields(), link_uuid: null};
    }

    /** A quantity's digits as the grid shows them, trailing zeros dropped, never in exponent notation (C-97b): through
     *  Number a satoshi read `1e-8`, in the cell and in the payload. Never cut: a value past the budget stays whole, and
     *  the Save says why. */
    function quantityText(value: string): string {
        return formatDecimalForDisplay(value, {maxFrac: value.length});
    }

    /** Extract display-ready DraftFields from a TXReadItem (auto-sign applied). */
    function fieldsFromTx(tx: TXReadItem): DraftFields {
        const rule = getTypeRule(tx.type);
        // The editor's convention (W-B65): a value whose rule demands a negative is held as its magnitude, exactly; never
        // through Number, which turned a satoshi into `1e-8` (C-97b) and an amount read back with noise into another one.
        const qty = magnitudeForRule(tx.quantity, rule.quantityRule);
        const cash = tx.cash ? {code: tx.cash.code, amount: magnitudeForRule(tx.cash.amount, rule.cashSign)} : null;
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
        // A cost only where units come in: an ADJUSTMENT taking units out has no value (N78-1).
        if (cbRule !== 'forbidden' && !(cbRule === 'required_qty_pos' && rawQty <= 0)) {
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
    function editOpFromTx(txId: number, opts?: {markedDelete?: boolean; addedViaPicker?: boolean; loadedWithParent?: boolean}): PendingOp {
        const tx = txStoreGet(txId)!;
        const op: PendingOp = {op: 'edit', tempId: generateUUID(), createdSeq: nextCreatedSeq(), txId, fields: fieldsFromTx(tx), markedDelete: opts?.markedDelete ?? false, addedViaPicker: opts?.addedViaPicker};
        // 66 F7-c1: set only when true, so a row that was not read with its parent keys as it always did (close guard).
        if (opts?.loadedWithParent) op.loadedWithParent = true;
        return op;
    }

    /** Create 'create' PendingOp by cloning from a TXReadItem. */
    function createOpFromClone(tx: TXReadItem, linkUuid?: string | null): PendingOp {
        const fields = fieldsFromTx(tx);
        // T3: keep the source date — clone is the correction workflow, not "same op today".
        const rule = getTypeRule(tx.type);
        if (rule.quantityRule === 'zero') fields.quantity = '0';
        return {op: 'create', tempId: generateUUID(), createdSeq: nextCreatedSeq(), fields, link_uuid: linkUuid ?? null};
    }

    /** Get DB id from PendingOp (undefined for creates). */
    function opTxId(op: PendingOp): number | undefined {
        return op.op === 'edit' ? op.txId : undefined;
    }

    // =========================================================================
    // State
    // =========================================================================

    let ops = $state<PendingOp[]>([]);
    let dateSortDirection = $state<'asc' | 'desc'>('asc');
    let compareBulkDates = $derived(createBulkDateComparator(ops));
    /** Sort display groups only. The ledger and payload retain their original order. */
    let visibleOps = $derived(ops.filter((o) => !o.pairedWith).sort((a, b) => (dateSortDirection === 'asc' ? 1 : -1) * compareBulkDates(a, b)));
    let visualRowLabels = $derived(buildBulkRowLabels(ops, visibleOps));
    /** 66 F7-c1 (BK2): the parents whose group of linked charges is open, by `tempId`. A group opens by the chip, or by
     *  itself (a parent «del», charges brought with their parent, a charge created or linked in its parent's Form); it
     *  never closes by itself. Remapped when a reset regenerates a parent's `tempId`. */
    let expandedParents = $state<Set<string>>(new Set());
    /** 66 F7-c1 (§14.2): the saved parents (by `txId`) whose charges are being read: «Save all» waits, «del» on them
     *  waits. */
    let chargesInFlight = $state<Set<number>>(new Set());
    /** 66 F7-c1 (§14.2): the saved parents (by `txId`) whose charges could not be read: «del» on them is off, with a
     *  reason. */
    let chargesReadFailed = $state<Set<number>>(new Set());
    /** 66 F7-c1: the operations that sit under their parent (`isUnderParent`): indented rows, drawn only in an open
     *  group. They stay in `visibleOps`, so the labels see them (the title counts `topRows`). */
    let indentedIds = $derived(new Set(ops.filter((o) => o.chargeOf !== undefined && isUnderParent(o, ops)).map((o) => o.tempId)));
    /** 66 F7-c1: the top-level rows, in the date order of `visibleOps`. */
    let topRows = $derived(visibleOps.filter((o) => !indentedIds.has(o.tempId)));
    /** 66 F7-c1: the rows of the grid — the top-level rows, each open parent followed by its charges. One order, ours:
     *  the date column only says which direction (`dateSortDirection`). */
    let gridRows = $derived(foldBulkCharges(topRows, ops, expandedParents));
    /** 66 F7-c1: the charges under each parent, in the order of the operations (the chip counts them). */
    let chargesUnder = $derived.by(() => {
        const under = new Map<string, PendingOp[]>();
        for (const op of ops) if (op.chargeOf !== undefined && indentedIds.has(op.tempId)) under.set(op.chargeOf, [...(under.get(op.chargeOf) ?? []), op]);
        return under;
    });
    /** 66 F7-b: whether any row is owned by another one (`chargeOf`); spares the scan of `parentNeedsRef` otherwise. */
    let hasChargeLinks = $derived(ops.some((o) => o.chargeOf !== undefined));
    /** Find the hidden partner op for a given main op's tempId. */
    function getPartnerOp(mainTempId: string): PendingOp | undefined {
        return ops.find((o) => o.pairedWith === mainTempId);
    }
    let issues = $state<ValidationIssue[]>([]);
    /** API-array indices map to stable op IDs, never to display/file row numbers. */
    let lastOpsIndexMap = $state<BulkOperationIndex>(new Map());
    let lastIssueRows = $state<BulkIssueRow[]>([]);
    let lastBalanceRows = $state<BulkIssueRow[]>([]);
    let lastIssueDraftKey = $state('');
    let lastDraftKey = $state('');
    let activeIssue = $state<ValidationIssue | null>(null);
    let activeIssueRows = $derived(activeIssue && lastIssueDraftKey === lastDraftKey ? getIssueRows(activeIssue) : []);
    let highlightedIssueIds = $derived(new Set(activeIssueRows.map((row) => issueRowAnchor(row))));
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
    /** The question the rows ask promote-suggest right now ('' when none): an answer to an older one is dropped. */
    let suggestAskedKey = '';

    /** Snapshot of `ops` at modal-open time, used to detect unsaved changes
     *  for the close-confirmation guard (Bugfix-3 §C11). */
    let initialOpsKey = $state('');
    let confirmCloseOpen = $state(false);
    /** B23 Step 4: confirm edit on a row marked for deletion. */
    let confirmEditDeleteOpen = $state(false);
    let confirmEditDeleteRow = $state<PendingOp | null>(null);
    /** Gate: confirm Save when auto-derived "fields to verify" (warning todos) are still un-acknowledged. */
    let confirmWarningsOpen = $state(false);
    /** Save gate for dates before 1900 (D-P4, W5-10): one confirmation for all the rows. */
    let confirmPreFloorOpen = $state(false);
    /**
     * Save gate for merge suggestions nobody looked at: the saved counterparts behind the lightbulb
     * and the banner of complementary rows. Opening the lightbulb, or touching the banner, once is
     * enough; «Save anyway» counts as a look too.
     */
    let suggestPickerSeen = $state(false);
    let promoteBannerSeen = $state(false);
    let confirmSuggestionsOpen = $state(false);
    /** «Merge all» of the banner: one answer for every suggested pair. */
    let promoteAllOpen = $state(false);

    // =========================================================================
    // WAC results — populated from validate response (Phase C: inline WAC)
    // =========================================================================

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
    function resolveInitialRows(): {rows: TXReadItem[]; status?: 'delete'; autoForm: string | null; cloneSources?: TXReadItem[]} {
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
                // T3 (02/09): the original date is PRESERVED on clone — duplication is
                // how users fix a misclassified historical row, and resetting to
                // today destroyed exactly the field they needed to keep.
                // A pair of the ledger is cloned as a pair: one fresh link_uuid for each pair whose two halves are
                // both selected. A single row gets none, whatever the type of the rows beside it.
                const selectedIds = new Set(resolved.map((r) => r.id));
                const cloneLinks = new Map<number, string>();
                for (const r of resolved) {
                    const partnerId = r.related_transaction_id;
                    if (partnerId == null || !selectedIds.has(partnerId) || cloneLinks.has(r.id)) continue;
                    const link = generateUUID();
                    cloneLinks.set(r.id, link);
                    cloneLinks.set(partnerId, link);
                }
                const cloned = resolved.map((r) => {
                    const c = {...r, id: 0, related_transaction_id: null} as TXReadItem;
                    // Bug6-fix: reset quantity when the type requires qty=0 (e.g. INTEREST)
                    const rule = getTypeRule(r.type);
                    if (rule.quantityRule === 'zero') c.quantity = '0';
                    const link = cloneLinks.get(r.id);
                    if (link) (c as any).link_uuid = link;
                    return c;
                });
                // 66 TL-3: the originals, aligned with their clones, so the charges' structure is carried over.
                return {rows: cloned, autoForm: cloned.length === 1 ? 'create' : null, cloneSources: resolved};
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
        // The rows come from the intent; the store is read untracked. Tracked, a row added to the store while the editor
        // is open (66 F7-c1: the charges the Bulk reads, `txStoreAddExtras`) re-ran this whole effect, which rebuilds the
        // rows from the intent: every unsaved edit was lost.
        void intent;
        const {rows, status: initSt, autoForm, cloneSources} = untrack(() => resolveInitialRows());
        // 66 TL-3: «Clona» on a parent with linked charges reads them first (`GET ?parent_ids`), then builds the rows.
        const cloneParents = untrack(() => (cloneSources ?? []).filter((source) => (source.charges_count ?? 0) > 0).map((source) => source.id));
        const cloneGeneration = ++cloneChargesGeneration;
        // K-2: the nested form or wizard opens automatically once per open. Set when it is scheduled before the load
        // ends; the load's end then opens nothing the user may have closed meanwhile.
        let autoOpenScheduled = false;
        untrack(() => {
            issues = [];
            lastOpsIndexMap = new Map();
            lastIssueRows = [];
            lastBalanceRows = [];
            lastIssueDraftKey = '';
            activeIssue = null;
            formError = null;
            commitFailed = false;
            confirmCloseOpen = false;
            formChargeEdits = true;
            ++chargesReadRequest; // a charges read still in flight belongs to the previous open
            restartChargesLoad(); // 66 F7-c1: and so does an entry load
            expandedParents = new Set();
            pendingSplits = [];
            pendingPromotes = [];
            promoteMergeOpen = false;
            promoteMergeData = null;
            promoteAllOpen = false;
            suggestPickerSeen = false;
            promoteBannerSeen = false;
            confirmSuggestionsOpen = false;
            suggestFromDB = new Map();
            lastSuggestKey = '';
            if (suggestTimer) {
                clearTimeout(suggestTimer);
                suggestTimer = null;
            }
            // When no initial rows → empty grid; user adds rows via nested FormModal.
            // Collapse paired rows: keep only the "from" half with partner
            // metadata populated. No dependency on isTypesLoaded — pair detection
            // uses related_transaction_id (not getTypeRule().requiresPair).
            let next: PendingOp[] = rows.length > 0 ? buildInitialOps(rows, initSt, cloneSources ? {sources: cloneSources, read: []} : undefined) : [];

            // B4-fix: Build ops eagerly but only assign after types are loaded,
            // because getTypeRule() returns FALLBACK_RULE (requiresPair=false)
            // until _ruleMap is populated → paired rows render as singles.
            if (isTypesLoaded() && cloneParents.length === 0) {
                // Fast path: types already cached → assign + auto-open immediately.
                ops = next;
                setBaseline(next);
                enterOps(next);
                scheduleAutoOpen(autoForm, next);
                autoOpenScheduled = true;
            } else {
                // Slow path: keep ops empty so DataTable doesn't render
                // with FALLBACK_RULE. Ops will be assigned after Promise.all.
                ops = [];
                // The snapshot of what is on screen: no rows. Without initial rows it is never taken again, and an
                // empty key would make an untouched editor ask to discard.
                setBaseline([]);
                if (rows.length === 0 && intent?.action !== 'import') {
                    autoOpenScheduled = true;
                    queueMicrotask(() => {
                        formOpen = true;
                        formMode = 'create';
                        formItems = null;
                        formEditingTempId = null;
                    });
                }
                if (intent?.action === 'import') {
                    autoOpenScheduled = true;
                    queueMicrotask(() => {
                        importWizardOpen = true;
                    });
                }
            }
        });
        void (async () => {
            // K-4: the language read untracked. Tracked, a language change re-ran this whole effect, which rebuilds the
            // rows from the intent: every unsaved edit was lost.
            await Promise.all([ensureBrokersLoaded(), ensureCurrenciesLoaded(untrack(() => $currentLanguage)), ensureAssetsLoaded(), ensureTypesLoaded()]);
            const cloneRead = cloneParents.length > 0 ? await readCloneCharges(cloneParents) : [];
            // An answer for an editor closed or reopened meanwhile changes nothing.
            if (cloneGeneration !== cloneChargesGeneration || !untrack(() => open)) return;
            untrack(() => {
                // B4-fix: if ops was deferred (slow path), rebuild + assign now.
                if (ops.length === 0 && rows.length > 0) {
                    const next2 = buildInitialOps(rows, initSt, cloneSources ? {sources: cloneSources, read: cloneRead} : undefined);
                    ops = next2;
                    setBaseline(next2);
                    enterOps(next2);
                    if (cloneRead === null) notifyCloneChargesUnread(cloneParents);
                }
                if (!autoOpenScheduled && !formOpen) {
                    scheduleAutoOpen(autoForm, ops);
                }
            });
        })();
    });

    /**
     * The operations of the rows an intent opens on: saved rows as edits (marked for deletion by a delete intent), clones
     * as creates, the pairs collapsed, the charges adopted by their parent (66 F7-b). «Keep the charges» (66 F6, V1:
     * `unlinkIds`) brings each charge kept as a row of its own, owned by its parent and unlinked (`parentUnlink`): the
     * batch sends `parent_transaction_id: 0` beside the parent's deletion. A charge also marked for deletion is a delete.
     * The charges of the page's choice (`chargeIds`, 66 F7-d: «Delete all» or «Keep») are the parent's choice
     * (`byParentChoice`), so «Restore» on the parent takes them back; a charge the user selected is not among them.
     */
    function buildInitialOps(rows: TXReadItem[], initSt: 'delete' | undefined, clone?: {sources: TXReadItem[]; read: TXReadItem[] | null}): PendingOp[] {
        let next: PendingOp[] = initSt === 'delete' ? rows.filter((r) => r.id > 0).map((r) => editOpFromTx(r.id, {markedDelete: true})) : rows.map((r) => (r.id > 0 ? editOpFromTx(r.id) : createOpFromClone(r, (r as any).link_uuid)));
        if (clone) {
            // 66 TL-3: each cloned charge under its parent's clone (or linked to its saved parent), and the charges read
            // of each cloned parent as copies under its clone. Their groups start open: the user brought them.
            const wired = wireClonedRows(clone.sources, next, clone.read, (charge) => createOpFromClone(charge));
            next = wired.ops;
            if (wired.expanded.length > 0) expandedParents = new Set([...expandedParents, ...wired.expanded]);
        }
        const unlinkIds = new Set(intent?.action === 'delete' ? (intent.unlinkIds ?? []) : []);
        if (unlinkIds.size > 0) {
            const present = new Set(next.map((op) => opTxId(op)).filter((id): id is number => id != null));
            for (const id of unlinkIds) {
                if (present.has(id) || !txStoreGet(id)) continue;
                present.add(id);
                next.push(editOpFromTx(id));
            }
        }
        next = adoptCharges(collapsePairedOps(next), txStoreGet);
        // An intent from before `chargeIds`: the charges unlinked are the parent's choice.
        const chosenIds = new Set(intent?.action === 'delete' ? (intent.chargeIds ?? intent.unlinkIds ?? []) : []);
        if (unlinkIds.size === 0 && chosenIds.size === 0) return next;
        return next.map((op) => {
            if (op.op !== 'edit') return op;
            const unlinked = unlinkIds.has(op.txId) && !op.markedDelete;
            const chosen = chosenIds.has(op.txId) && (unlinked || op.markedDelete);
            if (!unlinked && !chosen) return op;
            // The parent of an intent's charge is its saved one: `unlinkCharge` cuts that link (`parentUnlink`).
            return {...(unlinked ? unlinkCharge(op, next, txStoreGet) : op), ...(chosen ? {byParentChoice: true as const} : {})};
        });
    }

    /** 66 TL-3: bumped on every open, so the charges read for a clone answer only the open that asked for them. */
    let cloneChargesGeneration = 0;

    /** 66 TL-3: the linked charges of the parents a «Clona» copies, read in batches of `CHARGES_READ_BATCH`; `null` when a
     *  read failed (the parents are then copied alone, and a toast says so). */
    async function readCloneCharges(parentIds: number[]): Promise<TXReadItem[] | null> {
        const found: TXReadItem[] = [];
        try {
            for (let at = 0; at < parentIds.length; at += CHARGES_READ_BATCH) {
                const batch = parentIds.slice(at, at + CHARGES_READ_BATCH);
                const answer = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {parent_ids: batch}} as never)) as unknown;
                if (!Array.isArray(answer)) return null;
                found.push(...(answer as TXReadItem[]).filter((charge) => charge.parent_transaction_id != null && batch.includes(charge.parent_transaction_id)));
            }
        } catch {
            // The API client writes the failure to the console (H-60); the toast tells the user.
            return null;
        }
        return found;
    }

    /** 66 TL-3: the charges of these parents could not be read: each parent was copied alone. */
    function notifyCloneChargesUnread(parentIds: readonly number[]) {
        notify({name: 'tx.bulk.clone.charges-read-failed', detail: {parentIds: [...parentIds]}, toast: {variant: 'warning', message: $t('transactions.bulk.cloneChargesReadFailed', {values: {ids: shortIdList(parentIds)}})}});
    }

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

    /** The close guard's baseline: the rows as the editor opened on them, plus the charges the Bulk read itself since
     *  (66 F7-c1, `addLoadedCharges`). A plain snapshot: the live rows are mutated in place in a few places. */
    let baselineOps: PendingOp[] = [];
    function setBaseline(rows: PendingOp[]) {
        baselineOps = $state.snapshot(rows) as PendingOp[];
        initialOpsKey = serializeOps(baselineOps);
    }

    /**
     * 66 F7-c1: rows that entered the editor with the intent. A parent that came with its charges opens its group (§14.7:
     * the user brought them; a parent «del» too), and the charges of every saved parent not all held are read.
     */
    function enterOps(rows: readonly PendingOp[]) {
        const parents = rows.filter((o) => o.chargeOf !== undefined && isUnderParent(o, rows)).map((o) => o.chargeOf!);
        if (parents.length > 0) expandedParents = new Set([...expandedParents, ...parents]);
        loadMissingCharges(rows);
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

    /** Display lookups (names, icons, issue messages): every broker the user can see, read-only ones
     *  included, so a pair landing on a VIEWER broker names it. New rows default to an editable broker. */
    let brokers = $derived.by<BrokerInfo[]>(() => {
        void $brokerStoreVersion;
        return getAccessibleBrokers();
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

    /** 66 C22d: the type a half of a queued split will have (`postSplitType`, the one computation). */
    function postSplitTypeForForm(d: PendingOp): string {
        return postSplitType(d, pendingSplits);
    }

    /** Convert a PendingOp to a TXReadItem-shaped object so it can be fed back to
     *  TransactionFormModal as `initialRow`. We reuse the BulkModal's in-flight
     *  draft state, NOT a server-persisted row, so id/timestamps are synthetic. */
    function opToTxLike(d: PendingOp): TXReadItem {
        const id = opTxId(d);
        const orig = id != null ? txStoreGet(id) : undefined;
        // For paired main, find partner's DB id (if it's an edit op)
        const partnerOp = d.pairedWith ? undefined : getPartnerOp(d.tempId);
        const partnerDbId = partnerOp?.op === 'edit' ? partnerOp.txId : null;
        const fields = followedFields(d);
        return {
            id: id ?? 0,
            broker_id: fields.broker_id,
            asset_id: fields.asset_id,
            type: d.fields.type,
            date: fields.date,
            quantity: d.fields.quantity,
            cash: d.fields.cash,
            related_transaction_id: partnerDbId ?? (partnerOp ? 0 : null),
            // 66 F7-b: the charge's parent as the Bulk holds it now, and the parent's saved count (the Form's section).
            parent_transaction_id: effectiveParentId(d, orig),
            charges_count: orig?.charges_count,
            tags: d.fields.tags,
            description: d.fields.description,
            cost_basis_override: (d.fields.cost_basis_override || null) as any,
            cost_basis_mode: d.fields.cost_basis_mode,
            asset_event_id: d.fields.asset_event_id,
            created_at: orig?.created_at,
            updated_at: orig?.updated_at,
        };
    }

    /** 66 F7-b: the parent of a charge as the Bulk holds it — none once unlinked, the owner's saved id (a new owner has
     *  none yet), the saved parent picked in the charge's form, else the saved link. */
    function effectiveParentId(d: PendingOp, orig: TXReadItem | undefined): number | null {
        if (d.parentUnlink) return null;
        if (d.chargeOf !== undefined) {
            const owner = ops.find((o) => o.tempId === d.chargeOf);
            if (owner) return owner.op === 'edit' ? owner.txId : null;
        }
        if (d.parentLinkId !== undefined) return d.parentLinkId;
        return orig?.parent_transaction_id ?? null;
    }

    /** 66 F7-b (§11.4): a create born in its parent's form takes the parent's broker, asset and date until it is opened
     *  on its own. Read wherever the row is sent or shown to the Form, so the three payloads and the Form agree. */
    function followedFields(d: PendingOp, opArr: readonly PendingOp[] = ops): DraftFields {
        if (d.op !== 'create' || !d.followsParent || d.chargeOf === undefined) return d.fields;
        const owner = opArr.find((o) => o.tempId === d.chargeOf);
        if (!owner) return d.fields;
        return {...d.fields, broker_id: owner.fields.broker_id, asset_id: owner.fields.asset_id, date: owner.fields.date};
    }

    function opToTxLikeForForm(d: PendingOp): TXReadItem {
        const item = opToTxLike(d);
        item.type = postSplitTypeForForm(d);
        return item;
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
            // K-3b: a W4b placeholder (the half on a broker the user cannot read) has no row in the store, so the direction
            // test below would read its cash as 0 and hide a readable receiver behind it: after a reset the pair left the
            // grid. As in the first build (pass 2), the placeholder is always the hidden partner of the readable half.
            if (opArr[pIdx].inaccessible) {
                const sharedUuid = generateUUID();
                d.link_uuid = sharedUuid;
                opArr[pIdx].link_uuid = sharedUuid;
                opArr[pIdx].pairedWith = d.tempId;
                toHide.add(pIdx);
                continue;
            }
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
                        createdSeq: nextCreatedSeq(),
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
                createdSeq: nextCreatedSeq(),
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

    /** Apply the form-collected payload to a brand-new draft row; returns its tempId. */
    function addRowFromForm(payload: Record<string, unknown>): string {
        const next = createOpEmpty();
        applyFormPayload(next.fields, payload);
        if (typeof payload.link_uuid === 'string' && next.op === 'create') (next as any).link_uuid = payload.link_uuid;
        // Persist WAC currency hint
        if (typeof payload._wac_currency_hint === 'string') next.wacCurrencyHint = payload._wac_currency_hint;
        ops = [...ops, next];
        return next.tempId;
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
                // Null and absent both mean «the backend decides»; absent, as a row starts, so the close guard's key
                // (`serializeOps`, which keeps a null key and drops an absent one) reads no change (W-B65).
                delete merged.wacCurrencyHint;
            }
            // Auto-clear todos whose field has now been filled
            if (merged.todos?.length) {
                merged.todos = remainingTodos(merged.todos, merged.fields);
                if (merged.todos.length === 0) delete merged.todos;
            }
            return merged;
        });
        ops = syncFollowers(ops);
    }

    /** 66 F7-b: the creates that follow their parent (`followsParent`) show its broker, asset and date in the grid too
     *  (the payload reads them through `followedFields` whatever this says). Unchanged rows keep their reference. */
    function syncFollowers(opArr: PendingOp[]): PendingOp[] {
        if (!opArr.some((o) => o.followsParent)) return opArr;
        return opArr.map((d) => {
            const fields = followedFields(d, opArr);
            return fields === d.fields || (fields.broker_id === d.fields.broker_id && fields.asset_id === d.fields.asset_id && fields.date === d.fields.date) ? d : {...d, fields};
        });
    }

    /** Whether a row of these fields takes a cost-basis mode: the guardrail of `applyFormPayload` below, on the exact sign
     *  of the quantity as the payload reads it (`diffDualItem`). */
    function costBasisModeAllowed(fields: DraftFields): boolean {
        const sign = exactDecimalSign(fields.quantity ?? '0') ?? 0;
        const side: 'from' | 'to' | 'self' = sign < 0 ? 'from' : sign > 0 ? 'to' : 'self';
        const cbRule = getCostBasisRule(fields.type, side);
        return cbRule !== 'forbidden' && !(cbRule === 'required_qty_pos' && sign <= 0);
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
        // A type whose cost basis is a stated value (`costBasisAuto` false: a REWARD, project 79) never takes Auto
        if (target.cost_basis_mode === 'auto' && !getTypeRule(target.type).costBasisAuto) target.cost_basis_mode = 'manual';

        // Back to the editor's convention, last, so the derivation above reads the Form's payload as it always has
        // (W-B65): the Form pushes signed values, the editor holds a negative-rule value as its magnitude (`fieldsFromTx`),
        // and an untouched «Apply» must land where the row started — its cell, its status and the close guard's key.
        const heldRule = getTypeRule(target.type);
        target.quantity = magnitudeForRule(target.quantity, heldRule.quantityRule);
        if (target.cash) target.cash = {code: target.cash.code, amount: magnitudeForRule(target.cash.amount, heldRule.cashSign)};
    }

    // =========================================================================
    // Pair operations + row lifecycle
    // =========================================================================

    function removeRow(tempId: string) {
        // A pair is one row on screen and two ops: its hidden half leaves the batch with it.
        const removed = new Set(ops.filter((d) => d.tempId === tempId || d.pairedWith === tempId).map((d) => d.tempId));
        // 66 F7-c1 (§14.2): the charges the Bulk read itself for this parent leave with it while nobody changed them.
        const takenAlong = new Set(ops.filter((d) => d.loadedWithParent && d.chargeOf !== undefined && removed.has(d.chargeOf) && deriveStatus(d) === 'original').map((d) => d.tempId));
        // 66 F7-b (§11.2): no `chargeOf` left dangling. The parent's new charges born in its form (`followsParent`, F7-d)
        // leave with it; every other charge stays, owned by nobody (an unlink typed on them stays theirs): `withoutRows`.
        ops = withoutRows(
            ops.filter((d) => !takenAlong.has(d.tempId)),
            removed,
        );
    }

    /** 66 F7-c1/F7-c2: whether the charges of this saved row are being read, or could not be read. */
    function chargesUnread(row: PendingOp): ChargesUnread {
        if (row.op !== 'edit') return null;
        if (chargesInFlight.has(row.txId)) return 'loading';
        if (chargesReadFailed.has(row.txId) && parentChargesMissing(row)) return 'failed';
        return null;
    }

    /** 66 F7-c1 (§14.2): why «del» on this saved parent is off — its charges are being read, or could not be — or
     *  `null` when it is not. */
    function chargesUnreadReason(row: PendingOp): string | null {
        const state = chargesUnread(row);
        if (state === 'loading') return $t('transactions.form.charges.loading');
        if (state === 'failed') return $t('transactions.chargesDelete.loadFailed');
        return null;
    }

    /** 66 F7-c2: the panel V1 open inside the Bulk — the plan it decides, and what it shows. */
    let deletePanel = $state<{plan: BulkDeletePlan; parents: TXReadItem[]; charges: TXReadItem[]; parentRefs: string[]; chargeRefs: string[]; fromSelection: boolean} | null>(null);

    /** 66 F7-d (§22.1): how a text names a row of the Bulk — `#123` saved, its label («row 3») new, «new» without one.
     *  The labels do not depend on the grid's filters (`visualRowLabels`). */
    function bulkRowRef(op: PendingOp): string {
        const id = opTxId(op) ?? null;
        return txRowRef(id, id === null ? (visualRowLabels.get(op.tempId) ?? null) : null, $t);
    }

    /**
     * 66 TL-2: the Bulk's rows the charges picker of the open Form may offer, read on the Bulk's state by the selection's
     * «Link» rule (`bulkChargeCandidates`; the parent is the row the Form edits, or none while it creates it). Each is a
     * mirror as the panels show it, free: a saved one keeps its id, a new one gets a negative one and its key
     * (`_bulkKey`), and both their name (`_rowRef`). The parent picker reads the database only, as before.
     */
    function formBulkCandidates(mode: 'charges' | 'parent', probe: BulkChargeProbe): {rows: TXReadItem[]; exclude: number[]} | null {
        if (mode !== 'charges') return null;
        const parent = formEditingTempId !== null ? (ops.find((d) => d.tempId === formEditingTempId) ?? null) : null;
        const {candidates, excluded} = bulkChargeCandidates(parent, probe, ops, txStoreGet, {roleOf: (type) => getTypeRule(type).chargeRole, canEdit: (brokerId) => canEditBroker(brokerId)}, (op) => postSplitType(op, pendingSplits));
        let synthetic = 0;
        const rows = candidates.map((op): TXReadItem => {
            const id = op.op === 'edit' ? op.txId : -++synthetic;
            return {...panelItem(op), id, parent_transaction_id: null, related_transaction_id: null, _rowRef: bulkRowRef(op), ...(op.op === 'create' ? {_bulkKey: `op-${op.tempId}`} : {})} as TXReadItem;
        });
        return {rows, exclude: excluded};
    }

    /** A row as the panel shows it: the editor's values, signed as the ledger holds them. */
    function panelItem(op: PendingOp, parentTxId?: number): TXReadItem {
        // 66 C22d: a half of a queued split is shown with the type the split gives it (`postSplitType`).
        const item = opToTxLikeForForm(op);
        const {signedQty, signedCash} = applySignRules(item.quantity, item.cash, getTypeRule(item.type));
        return {...item, quantity: signedQty, cash: signedCash, ...(parentTxId !== undefined ? {parent_transaction_id: parentTxId} : {})};
    }

    /**
     * 66 F7-c2 (§17, §18, §19): «Delete» (one row) and «Delete selected» go through one plan (`planBulkDelete`). A parent
     * going «del» with linked charges asks first, in the panel V1, once for every such parent; nothing is marked before
     * the choice. A parent whose charges are being read is waited for; a reset, «Reset all» or the Bulk closed meanwhile
     * cancels the wait. A parent whose read failed is skipped, with a warning; the other rows proceed.
     */
    /** 66 F7-d (§20.3, §21.1): the rows of the delete requests waiting for a read, by `tempId`. A new request leaves them
     *  out and proceeds with the others; each request releases its own rows when it ends, a cut wait included. */
    const deleteHeld = new Set<string>();

    async function requestDelete(tempIds: readonly string[], fromSelection: boolean) {
        const mine = [...new Set(tempIds)].filter((id) => !deleteHeld.has(id));
        // Every row already waits in another request: that one decides, this one changes nothing.
        if (mine.length === 0) return;
        for (const id of mine) deleteHeld.add(id);
        try {
            await planAndAskDelete(mine, fromSelection);
        } finally {
            for (const id of mine) deleteHeld.delete(id);
        }
    }

    async function planAndAskDelete(tempIds: readonly string[], fromSelection: boolean) {
        const generation = chargesLoadGeneration;
        let plan = planBulkDelete(ops, tempIds, chargesUnread);
        while (plan.waiting.length > 0) {
            const reads = plan.waiting.map((id) => ops.find((d) => d.tempId === id)).map((d) => (d?.op === 'edit' ? chargesReads.get(d.txId) : undefined));
            await Promise.all(reads.map((read) => read ?? Promise.resolve(false)));
            await tick();
            if (generation !== chargesLoadGeneration || !open) return;
            // The rows taken at the click, resolved again (§19.7): a row gone meanwhile is simply not there.
            const next = planBulkDelete(ops, tempIds, chargesUnread);
            if (next.waiting.length > 0 && reads.every((read) => read === undefined)) return;
            plan = next;
        }
        if (plan.skipped.length > 0) {
            notify({
                name: 'tx.bulk.delete.skipped-unread',
                detail: {rowIds: plan.skipped},
                toast: {variant: 'warning', message: $t('transactions.bulk.deleteSkippedUnread', {values: {n: plan.skipped.length}})},
            });
        }
        if (plan.needsChoice.length === 0) {
            applyDelete(plan, 'keep', fromSelection);
            return;
        }
        const parents = plan.needsChoice.map((id) => ops.find((d) => d.tempId === id)).filter((d): d is PendingOp => d?.op === 'edit');
        const own = new Set([...plan.toggles.map((t) => t.tempId), ...plan.removals]);
        const charges = parents.flatMap((p) =>
            linkedChargesOf(p, ops)
                .filter((c) => !own.has(c.tempId))
                .map((c) => ({op: c, parentTxId: p.op === 'edit' ? p.txId : undefined})),
        );
        deletePanel = {
            plan,
            parents: parents.map((p) => panelItem(p)),
            charges: charges.map(({op, parentTxId}) => panelItem(op, parentTxId)),
            parentRefs: parents.map((p) => bulkRowRef(p)),
            chargeRefs: charges.map(({op}) => bulkRowRef(op)),
            fromSelection,
        };
    }

    /** The plan and the choice onto the rows: the groups of the parents gone «del» open, and a selection that asked is
     *  emptied (§19.5). */
    function applyDelete(plan: BulkDeletePlan, choice: 'keep' | 'all', fromSelection: boolean) {
        const deleted = [...plan.needsChoice, ...plan.toggles.filter((t) => t.deleted).map((t) => t.tempId)];
        ops = applyDeleteChoice(ops, plan, choice, txStoreGet);
        // 66 C21 (§5.2): a charge back from «del» stays «unlink» when its parent cannot hold it (a leg of a pair, «del»).
        keepUnlinkedFromUnfitParents(new Set(plan.toggles.filter((t) => !t.deleted).map((t) => t.tempId)));
        // 66 F7-c1 (§14.7): a parent marked «del» opens its group, so its charges' state is on screen.
        const opened = deleted.filter((id) => !expandedParents.has(id) && ops.some((d) => d.chargeOf === id));
        if (opened.length > 0) expandedParents = new Set([...expandedParents, ...opened]);
        if (fromSelection) {
            tableRef?.clearSelection();
            bulkTableSelectedRows = [];
        }
    }

    function chooseDelete(choice: 'keep' | 'all') {
        const panel = deletePanel;
        deletePanel = null;
        if (panel) applyDelete(panel.plan, choice, panel.fromSelection);
    }

    /** «Cancel» or Esc on the panel: nothing changes, the selection is kept (§18.5). */
    function cancelDelete() {
        deletePanel = null;
    }

    /** «Delete» on one row, through the same plan as «Delete selected». */
    function markDelete(tempId: string) {
        const target = ops.find((d) => d.tempId === tempId);
        if (!target || target.op !== 'edit') return; // can't mark-delete a create — just remove it
        // 66 F7-c1 (§14.2): «del» on a parent waits for its charges to be read (the menu says why).
        if (!target.markedDelete && chargesUnreadReason(target) !== null) return;
        void requestDelete([tempId], false);
    }

    /**
     * Mark a saved row for deletion, or restore it, without asking: a restore (a row reset, «Restore and edit»), or a
     * deletion whose choice is known. 66 F7-c2: a parent «del» no longer unlinks its charges by itself; restoring it
     * takes back only what a delete choice set on them (`byParentChoice`); a charge restored under a parent still «del»
     * is unlinked (`applyDeleteChoice`).
     */
    function setRowDeleted(tempId: string, deleted: boolean, choice: 'keep' | 'all' = 'keep') {
        const target = ops.find((d) => d.tempId === tempId);
        if (!target || target.op !== 'edit' || target.markedDelete === deleted) return;
        applyDelete(
            planBulkDelete(ops, [tempId], () => null),
            choice,
            false,
        );
    }

    /**
     * Clone a row as a new row. 66 TL-3: a parent brings a copy of each charge still linked under it (neither «del» nor
     * «scollega»), owned by its copy, whose group opens; a saved parent whose charges are not all read yet is read first,
     * and copied alone if that read fails (a toast says so). A charge's copy is born linked to the same parent, when the
     * «Link» rule allows it (`cloneChargeLink`), free otherwise, with a toast saying why. Every copy keeps its original's date.
     */
    async function cloneRow(tempId: string) {
        let src = ops.find((d) => d.tempId === tempId);
        if (!src) return;
        if (src.op === 'edit' && parentChargesMissing(src)) {
            const read = await ensureParentCharges(tempId);
            src = ops.find((d) => d.tempId === tempId);
            if (!src) return;
            if (!read) notifyCloneChargesUnread([(src as PendingOp & {txId: number}).txId]);
        }
        const copyOf = (row: PendingOp): PendingOp => ({op: 'create', tempId: generateUUID(), createdSeq: nextCreatedSeq(), fields: structuredClone($state.snapshot(followedFields(row))) as DraftFields, link_uuid: null});
        // T3: the source row's date is preserved (correction workflow) — not reset to today.
        const clone: PendingOp = {...copyOf(src), link_uuid: getTypeRule(src.fields.type as TransactionTypeCode)?.requiresPair ? generateUUID() : null};
        const added: PendingOp[] = [clone];
        // Clone hidden partner if exists
        const srcPartner = getPartnerOp(tempId);
        if (srcPartner) {
            added.push({...copyOf(srcPartner), link_uuid: clone.link_uuid, pairedWith: clone.tempId});
        }
        if (src.fields.type === 'FEE' || src.fields.type === 'TAX') {
            const link = cloneChargeLink(src, clone.fields, ops, txStoreGet, {roleOf: (type) => getTypeRule(type).chargeRole, canEdit: (brokerId) => canEditBroker(brokerId)}, (op) => postSplitType(op, pendingSplits));
            if (link.kind === 'owner') {
                clone.chargeOf = link.chargeOf;
                openGroup(link.chargeOf);
            } else if (link.kind === 'saved') {
                clone.parentLinkId = link.parentLinkId;
            } else if (link.reason !== null) {
                notify({name: 'tx.bulk.clone.charge-free', detail: {reason: link.reason, tempId: clone.tempId}, toast: {variant: 'warning', message: $t('transactions.bulk.cloneChargeFree', {values: {reason: link.reason}})}});
            }
        } else if (!srcPartner) {
            const charges = cloneChargesUnder(src, clone.tempId, ops, copyOf);
            added.push(...charges);
            if (charges.length > 0) openGroup(clone.tempId);
        }
        ops = [...ops, ...added];
    }

    /** 66 C22 (§5.1): reset rows back to what is saved. A merge still waiting for the save (`pendingPromotes`) that
     *  touches one of them is undone first, both halves, so «Save all» never sends a merge the grid no longer shows, and
     *  the order of the rows does not change the outcome (a charge reset before its parent's merge is undone would
     *  otherwise stay «unlink»). 66 C22b: a split still waiting for the save (`pendingSplits`) that touches one of them is
     *  undone the same way, both halves reset, so the grid's joined pair is never split by the save. */
    function resetRows(tempIds: readonly string[]) {
        const rows = [...new Set(tempIds)];
        const undone: string[] = [];
        const rowTxIds = new Set(rows.map((tempId) => ops.find((d) => d.tempId === tempId)).flatMap((d) => (d?.op === 'edit' ? [d.txId] : [])));
        const splitsUndone = pendingSplits.filter((s) => rowTxIds.has(s.id_a) || rowTxIds.has(s.id_b));
        if (splitsUndone.length > 0) {
            pendingSplits = pendingSplits.filter((s) => !splitsUndone.includes(s));
            const halves = new Set(splitsUndone.flatMap((s) => [s.id_a, s.id_b]));
            for (const d of ops) if (d.op === 'edit' && halves.has(d.txId)) undone.push(d.tempId);
            lastSuggestKey = ''; // B9: invalidate suggest
        }
        for (const tempId of rows) {
            const row = ops.find((d) => d.tempId === tempId);
            // The partner is taken before the undo: afterwards neither half names the other.
            const partner = row ? (row.pairedWith !== undefined ? ops.find((d) => d.tempId === row.pairedWith) : getPartnerOp(row.tempId)) : undefined;
            if (row && partner && undoPendingPromote(row, partner)) undone.push(partner.tempId);
        }
        for (const tempId of new Set([...rows, ...undone])) resetOne(tempId);
    }

    function resetRow(tempId: string) {
        resetRows([tempId]);
    }

    /** Reset one row (and the hidden half of its saved pair) to what is saved. */
    function resetOne(tempId: string) {
        // A saved pair is one row on screen: its hidden half is reset with it, in place, or an edit made through the
        // pair's form would stay on it. A W4b placeholder has nothing to reset: its half is not in the store.
        const partnerTempId = getPartnerOp(tempId)?.tempId;
        // 66 F7-b: a parent reset from «del» is restored, so its charges come back from «del» and «scollega» as with
        // «Restore»; an edited parent keeps what its charges hold.
        const wasDeleted = ops.some((d) => d.tempId === tempId && d.op === 'edit' && d.markedDelete);
        if (wasDeleted) setRowDeleted(tempId, false);
        const renamed = new Map<string, string>();
        let next = ops.map((d) => {
            if ((d.tempId !== tempId && d.tempId !== partnerTempId) || d.op !== 'edit' || d.inaccessible) return d;
            const reset = editOpFromTx(d.txId, {addedViaPicker: d.addedViaPicker, loadedWithParent: d.loadedWithParent});
            renamed.set(d.tempId, reset.tempId);
            return reset;
        });
        // 66 F7-b (§11.2): the charges follow their parent's new tempId.
        for (const [from, to] of renamed) next = remapChargeOf(next, from, to);
        remapExpanded(renamed);
        // Re-collapse pairs from txStore, then the charges
        ops = syncFollowers(adoptCharges(collapsePairedOps(next), txStoreGet));
        const entered = new Set(renamed.values());
        keepUnlinkedFromUnfitParents(entered);
        // 66 F7-c1 (§14.2): the row enters again: its charges are read if they are not all held (a new generation). The
        // reads in flight are asked again; a parent whose read failed and that was not reset keeps «del» off.
        const failedBefore = chargesReadFailed;
        const waiting = restartChargesLoad();
        const resetTxIds = new Set(ops.filter((d) => entered.has(d.tempId)).map((d) => opTxId(d)));
        chargesReadFailed = new Set([...failedBefore].filter((id) => !resetTxIds.has(id)));
        loadMissingCharges(
            ops.filter((d) => entered.has(d.tempId)),
            waiting,
        );
    }

    /** 66 C21 (§5.2): a reset or restored charge whose parent cannot hold it — «del», or a leg of a pair, saved or pending — stays
     *  «unlink»; the reset brings back its other values only. A pair is named in a toast (the «Link» reason `paired`).
     *  66 C22b: so does a charge of a reset row that the reset made a leg again — a half of a split undone by the reset,
     *  whose charge was linked while the split was queued. 66 C22c: the link is undone by `unlinkCharge` — a saved link is
     *  cut («unlink»), a link made only here is dropped (the charge back as before it). «Undo split» calls it on the two
     *  halves too, with its own event name. */
    function keepUnlinkedFromUnfitParents(resetTempIds: ReadonlySet<string>, eventName = 'tx.bulk.reset.charge.kept-unlinked') {
        const ownerOfReset = (d: PendingOp): PendingOp | undefined => (d.chargeOf !== undefined && !d.parentUnlink && (resetTempIds.has(d.tempId) || resetTempIds.has(d.chargeOf)) ? ops.find((o) => o.tempId === d.chargeOf && o !== d) : undefined);
        const unfit = (owner: PendingOp | undefined): boolean => !!owner && (isPairLeg(owner, ops) || (owner.op === 'edit' && owner.markedDelete === true));
        const parent = ops.map(ownerOfReset).find((owner): owner is PendingOp => !!owner && isPairLeg(owner, ops));
        const before = ops;
        ops = ops.map((d) => (unfit(ownerOfReset(d)) ? unlinkCharge(d, before, txStoreGet) : d));
        if (parent) {
            notify({
                name: eventName,
                detail: {parentTempId: parent.tempId},
                toast: {variant: 'warning', message: $t('transactions.chargesLink.reason.paired', {values: {type: $t(`transactions.types.${parent.fields.type}`) || parent.fields.type, ref: bulkRowRef(parent)}})},
            });
        }
    }

    /** 66 F7-c1: open the group of this parent (never closed by itself). */
    function openGroup(parentTempId: string) {
        if (!expandedParents.has(parentTempId)) expandedParents = new Set([...expandedParents, parentTempId]);
    }

    /** 66 F7-c1: the chip opens and closes the group of this parent. */
    function toggleGroup(parentTempId: string) {
        const next = new Set(expandedParents);
        if (!next.delete(parentTempId)) next.add(parentTempId);
        expandedParents = next;
    }

    /** 66 F7-c1: a reset regenerated these parents' `tempId`s: their groups stay as they were. */
    function remapExpanded(renamed: ReadonlyMap<string, string>) {
        if (![...renamed.keys()].some((from) => expandedParents.has(from))) return;
        expandedParents = new Set([...expandedParents].map((id) => renamed.get(id) ?? id));
    }

    function resetAll() {
        // 66 C22 (§1.5): every merge still waiting for the save is undone first, before the reset renames the rows: a
        // reset brings back what is saved, and a queued merge is not (it stayed queued, unseen, and «Save all» sent it).
        for (const hidden of ops.filter((d) => d.pairedWith !== undefined)) {
            const visible = ops.find((d) => d.tempId === hidden.pairedWith);
            if (visible) undoPendingPromote(visible, hidden);
        }
        // BUG-C2: also undo pending splits
        // Remove partner rows added by split, then reset remaining edit rows
        ops = ops.filter((d) => !(d as any).addedBySplit);
        // K-3: a W4b placeholder has nothing to reset, its half is not in the store (as in `resetRow`).
        const renamed = new Map<string, string>();
        let next = ops.map((d) => {
            if (d.op !== 'edit' || d.inaccessible) return d;
            const reset = editOpFromTx(d.txId, {addedViaPicker: d.addedViaPicker, loadedWithParent: d.loadedWithParent});
            renamed.set(d.tempId, reset.tempId);
            return reset;
        });
        // 66 F7-b (§11.2): the charges follow their parent's new tempId (the saved ones are adopted again below).
        for (const [from, to] of renamed) next = remapChargeOf(next, from, to);
        remapExpanded(renamed);
        // Re-collapse pairs, then the charges
        ops = syncFollowers(adoptCharges(collapsePairedOps(next), txStoreGet));
        pendingSplits = [];
        pendingPromotes = [];
        // 66 F7-c1 (§15.8): «Reset all» reads again the charges of every saved parent that lacks some.
        restartChargesLoad();
        loadMissingCharges(ops);
    }

    /** Split a paired row in the BulkModal.
     *  Saved paired → backend split + 2 editable preview rows (DD-R2.1).
     *  New paired (link_uuid shared or pairedWith) → local transformation only. */
    /** «Split pair» on a merge still waiting for the save (`pendingPromotes`: two saved rows, or a saved and a new one):
     *  undo it, whichever row the pair shows (J-67). Each row gets its own type back — a saved row's from the store, a
     *  new row's `promoteFromType` — with its amount in the editor's convention (a withdrawal as its magnitude, as
     *  `fieldsFromTx` reads it); the new row loses the promote's link; both rows are visible; the merge leaves the
     *  queue, so the save sends neither it nor a split. False for any other pair: one saved as such (Case A), two new
     *  rows merged locally (Case B/C). */
    function undoPendingPromote(a: PendingOp, b: PendingOp): boolean {
        const saved = [a, b].filter((op) => op.op === 'edit').map((op) => (op as any).txId as number);
        const created = [a, b].find((op) => op.op === 'create');
        const index = pendingPromotes.findIndex((promote) =>
            saved.length === 2 ? (promote.id_a === saved[0] && promote.id_b === saved[1]) || (promote.id_a === saved[1] && promote.id_b === saved[0]) : saved.length === 1 && !!created?.link_uuid && promote.id_a === saved[0] && promote.link_uuid_b === created.link_uuid,
        );
        if (index < 0) return false;
        pendingPromotes = pendingPromotes.filter((_, at) => at !== index);
        for (const op of [a, b]) {
            const sourceType = op.op === 'edit' ? txStoreGet((op as any).txId)?.type : op.promoteFromType;
            if (sourceType) {
                const rule = getTypeRule(sourceType);
                op.fields.type = sourceType as TransactionTypeCode;
                op.fields.quantity = magnitudeForRule(op.fields.quantity, rule.quantityRule);
                if (op.fields.cash) op.fields.cash = {code: op.fields.cash.code, amount: magnitudeForRule(op.fields.cash.amount, rule.cashSign)};
            }
            op.promoteFromType = null;
            if (op.op === 'create') op.link_uuid = null;
            op.pairedWith = undefined;
        }
        ops = [...ops];
        lastSuggestKey = ''; // B9: invalidate suggest
        return true;
    }

    function handleSplitRow(row: PendingOp) {
        const partnerOp = getPartnerOp(row.tempId);
        if (partnerOp && undoPendingPromote(row, partnerOp)) return;

        // Splitting undoes the pairing, so any pre-promote type kept for the wire is
        // now stale — left behind it would silently override the standalone type each
        // branch below assigns, and the row would be committed as what it used to be.
        row.promoteFromType = null;
        if (partnerOp) partnerOp.promoteFromType = null;

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
            const rowType = splitHalfType(row.fields.type, row.fields);
            if (!splitTypes || !rowType) return;
            const [fromType, toType] = splitTypes;
            const isFrom = rowType === fromType;

            // Main row → standalone type
            row.fields.type = rowType as TransactionTypeCode;
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
                partner.promoteFromType = null;
                const splitTypes = SPLIT_TYPE_MAP[row.fields.type];
                const rowType = splitHalfType(row.fields.type, row.fields);
                if (!splitTypes || !rowType) return;
                const [fromType, toType] = splitTypes;
                const isFrom = rowType === fromType;
                row.fields.type = rowType as TransactionTypeCode;
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
        // The rule must follow the type actually being sent, not the one on screen:
        // for a mixed promote those differ, and a rule for the wrong type strips or
        // keeps the wrong fields.
        const fields = opToTxFields(d);
        const payload = buildCreatePayload(fields, getTypeRule(fields.type as TransactionTypeCode));
        // `buildCreatePayload` only forwards link_uuid for types whose rule requires a
        // pair, which a pre-promote type by definition does not. Here the uuid is not
        // a pairing marker at all: it is the handle the promote resolves as
        // `link_uuid_b`, so it has to ride along independently of the type's own rule.
        if (d.promoteFromType && d.link_uuid) payload.link_uuid = d.link_uuid;
        // 66 F7-b: a new parent named by a charge carries its tempId as `ref` (36 characters, the schema's limit); a
        // charge names its parent by `parent_ref` or by `parent_transaction_id` (`chargeParentFields`).
        if (hasChargeLinks && parentNeedsRef(d, ops)) payload.ref = d.tempId;
        const link = chargeParentFields(d, ops, txStoreGet);
        if (link) Object.assign(payload, link);
        return payload;
    }

    function collectUpdate(d: PendingOp): Record<string, unknown> | null {
        if (d.op !== 'edit') return null;
        const orig = txStoreGet(d.txId);
        if (!orig) return null;
        const rule = getTypeRule(d.fields.type);
        const origRule = getTypeRule(orig.type as TransactionTypeCode);
        const diff = buildUpdateDiff(opToTxFields(d), orig as unknown as TxOriginal, rule, origRule);
        // 66 F7-b (§11.3): a change of parent is a change of the row: an unlink or a new link alone makes it `edited`.
        const link = chargeParentFields(d, ops, txStoreGet);
        return link ? {...diff, ...link} : diff;
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
    function resolveOps(opts?: {excludeTempId?: string | null; splitTxIds?: Set<number>; promoteTxIds?: Set<number>}): IdentifiedBulkOp[] {
        const excludeTempId = opts?.excludeTempId ?? null;
        const splitTxIds = opts?.splitTxIds ?? new Set<number>();
        const promoteTxIds = opts?.promoteTxIds ?? new Set<number>();
        const resolved: IdentifiedBulkOp[] = [];

        for (const d of ops) {
            if (d.pairedWith) continue; // hidden partners are handled via their main op
            if (d.tempId === excludeTempId) continue;
            // 66 F7-b (§4): the parent open in the Form takes its charges out of the context with it, or they would
            // count twice (and name a parent the context does not hold).
            if (excludeTempId !== null && d.chargeOf === excludeTempId) continue;
            const st = deriveStatus(d);

            // Skip split-queued edit rows ONLY if unchanged
            if (d.op === 'edit' && splitTxIds.has((d as any).txId) && st !== 'edited') continue;
            // Skip promote-queued edit rows: the promote itself carries them.
            //
            // But not their hidden partner. In a *mixed* promote (one saved row +
            // one new one) the promote sends `link_uuid_b`, and the backend resolves
            // that uuid only against the creates it receives in the same batch. If
            // the new row happens to be the hidden partner of this edit, the two
            // `continue`s cancel each other out — this one skips the main, line 960
            // skips the partner — and the create is never sent at all. The commit
            // then fails with "Cannot resolve TX B reference", pointing at a row the
            // user filled in and can see on screen.
            if (d.op === 'edit' && promoteTxIds.has((d as any).txId)) {
                const hidden = getPartnerOp(d.tempId);
                if (hidden && hidden.op === 'create') {
                    resolved.push({intent: 'create', tempId: hidden.tempId, payload: collectCreate(hidden), partnerPayload: null});
                }
                continue;
            }

            const pOp = getPartnerOp(d.tempId);

            if (st === 'new') {
                let partnerPayload: Record<string, unknown> | null = null;
                // Only a *new* partner is created alongside. A saved partner (the
                // other half of a mixed promote) already exists in the database:
                // emitting a create payload for it would insert a duplicate of a
                // row the user was merely linking.
                if (pOp && pOp.op === 'create') {
                    partnerPayload = collectCreate(pOp);
                }
                resolved.push({intent: 'create', tempId: d.tempId, partnerTempId: pOp?.tempId, payload: collectCreate(d), partnerPayload});
            } else if (st === 'edited') {
                const upd = collectUpdate(d);
                // A split half: the split gives it its type, so the update names one only when the user swapped it
                // (66 C22e, `splitTypeToSend`); otherwise the type stays out.
                if (upd && splitTxIds.has((d as any).txId)) {
                    const handType = splitTypeToSend(d, pendingSplits, txStoreGet((d as any).txId) ?? null);
                    if (handType) upd.type = handType;
                    else delete upd.type;
                }
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
                    resolved.push({intent: 'update', tempId: d.tempId, partnerTempId: pOp?.tempId, payload: payload ?? undefined, partnerPayload});
                }
            } else if (st === 'delete' && d.op === 'edit') {
                resolved.push({
                    intent: 'delete',
                    tempId: d.tempId,
                    partnerTempId: pOp?.tempId,
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
        // A mixed promote is applied server-side from the two *source* types, so the
        // wire keeps the pre-promote value while the grid shows the promoted one.
        const type = d.promoteFromType ?? d.fields.type;
        return {...followedFields(d), type, cost_basis_override: cbo, link_uuid: d.link_uuid ?? null};
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

    function buildOpsIndexMap(resolved: IdentifiedBulkOp[]): BulkOperationIndex {
        return buildBulkOperationIndex(resolved, {
            splits: pendingSplits.map((split) => ops.filter((op) => op.op === 'edit' && (op.txId === split.id_a || op.txId === split.id_b)).map((op) => op.tempId)),
            promotes: pendingPromotes.map((promote) => ops.filter((op) => (op.op === 'edit' && (op.txId === promote.id_a || op.txId === promote.id_b)) || (op.op === 'create' && !!op.link_uuid && (op.link_uuid === promote.link_uuid_a || op.link_uuid === promote.link_uuid_b))).map((op) => op.tempId)),
        });
    }

    function toIssueRow(op: PendingOp, fields: Pick<TxFields, 'type' | 'broker_id' | 'date' | 'quantity' | 'asset_id' | 'cash'>): BulkIssueRow {
        const {signedQty, signedCash} = applySignRules(fields.quantity, fields.cash, getTypeRule(fields.type));
        return {
            tempId: op.tempId,
            pairedWith: op.pairedWith,
            txId: opTxId(op),
            inaccessible: op.inaccessible,
            fields: {type: fields.type, broker_id: fields.broker_id, date: fields.date, asset_id: fields.asset_id ?? null, quantity: signedQty, cash: signedCash},
        };
    }

    /** Capture the state actually sent. Failed operations fall back to their saved row;
     *  successful deletes disappear from balance groups, but retain field-issue links. */
    function captureIssueSnapshot(resolved: IdentifiedBulkOp[], indexMap: BulkOperationIndex): BulkIssueSnapshotEntry[] {
        const payloads = new Map<string, Record<string, unknown>>();
        const deleted = new Set<string>();
        for (const op of resolved) {
            if (op.payload) payloads.set(op.tempId, op.payload);
            if (op.partnerPayload && op.partnerTempId) payloads.set(op.partnerTempId, op.partnerPayload);
            if (op.deleteId != null) deleted.add(op.tempId);
            if (op.partnerDeleteId != null && op.partnerTempId) deleted.add(op.partnerTempId);
        }
        const keysById = new Map<string, string[]>();
        for (const [key, ids] of indexMap) {
            for (const id of ids) keysById.set(id, [...(keysById.get(id) ?? []), key]);
        }
        return ops.map((op) => {
            const original = op.op === 'edit' ? txStoreGet(op.txId) : undefined;
            const draft = toIssueRow(op, opToTxFields(op));
            const before = original ? toIssueRow(op, original) : null;
            const operationKeys = keysById.get(op.tempId) ?? [];
            const atomic = operationKeys.some((key) => key.startsWith('split:') || key.startsWith('promote:'));
            const fields = {...(original ?? opToTxFields(op)), ...payloads.get(op.tempId)};
            const ordinaryAfter = deleted.has(op.tempId) ? null : toIssueRow(op, fields);
            let atomicFallback = before;
            if (before && operationKeys.some((key) => key.startsWith('split:'))) {
                const type = splitHalfType(before.fields.type, before.fields);
                if (type) atomicFallback = toIssueRow(op, {...before.fields, type: type as TransactionTypeCode});
            }
            return {before, after: atomic ? toIssueRow(op, op.fields) : ordinaryAfter, ordinaryAfter, atomicFallback, draft, operationKeys};
        });
    }

    function applyIssueSnapshot(snapshot: BulkIssueSnapshotEntry[], indexMap: BulkOperationIndex, rawResponse: unknown, sentKey: string) {
        lastOpsIndexMap = indexMap;
        lastIssueRows = snapshot.map((entry) => entry.draft);
        const results = (rawResponse as {results?: BulkBatchResult[]} | null)?.results ?? [];
        lastBalanceRows = settleBulkIssueSnapshot(snapshot, results);
        lastIssueDraftKey = sentKey;
        activeIssue = null;
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
        validateFn: async (reason) => {
            if (ops.length === 0) {
                issues = [];
                lastValidatedDraftKey = lastDraftKey;
                issuesDismissed = false;
                return {issuesCount: 0};
            }
            const splitTxIds = new Set(pendingSplits.flatMap((s) => [s.id_a, s.id_b]));
            // Resolve the same CUD and atomic commands as commit: indices and balance
            // groups must describe the ledger that Save will actually submit.
            const promoteTxIds = new Set(pendingPromotes.flatMap((p) => [p.id_a, p.id_b].filter(Boolean) as number[]));
            const resolved = resolveOps({splitTxIds, promoteTxIds});
            const payload = buildBatchPayload({
                ops: resolved,
                splits: pendingSplits.length > 0 ? pendingSplits.map((s) => ({id_a: s.id_a, id_b: s.id_b})) : undefined,
                promotes: pendingPromotes.length > 0 ? pendingPromotes : undefined,
            });
            upgradeAutoToDetail(payload);
            const sentKey = lastDraftKey;
            const opsMap = buildOpsIndexMap(resolved);
            const issueSnapshot = captureIssueSnapshot(resolved, opsMap);
            const result = await validateTransactions(payload, {fallback: $t('transactions.bulk.saveFailed')});
            // A response that lands after the draft moved on describes a state
            // that no longer exists: applying it overwrites fresher numbers
            // (a WAC cell falling back to its "…" placeholder is the visible
            // symptom). The change that moved the key already armed a newer
            // run, so dropping this one loses nothing.
            if (lastDraftKey !== sentKey) return {issuesCount: issues.length};
            if (result.networkError) {
                issues = [{operation: 'create', index: -1, error: result.networkError}];
            } else {
                issues = result.issues as unknown as ValidationIssue[];
            }
            lastValidatedDraftKey = sentKey;
            issuesDismissed = false;
            applyIssueSnapshot(issueSnapshot, opsMap, result.rawResponse, sentKey);
            // Q-J57-4: an explicit validation (⚡, the import hand-over) leads to the first row refused for an Auto cost;
            // the background ones never move the grid under the user's hands.
            if (reason === 'manual') jumpToFirstAutoCostRefusal();

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

            const rawWacResults = (rawResp?.wac_results as Array<Record<string, unknown>> | null | undefined) ?? null;
            if (rawWacResults && rawWacResults.length > 0) {
                // Map wac_results to tempIds using the opsMap
                const nextMap = new Map<string, WacResultEntry>();
                for (const wr of rawWacResults) {
                    const op = wr.operation as string | null;
                    const idx = wr.index as number | null;
                    if (op == null || idx == null) continue;
                    const key = `${op}:${idx}`;
                    const tempId = opsMap.get(key)?.[0];
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
        if (onboardingGuide.active?.flow === 'transaction_bulk_guide') {
            onboardingGuide.dismissHost({restartAtFirst: true});
        }
        onboardingGuide.clearQueued('transaction_bulk_guide');
    });

    /** Bugfix-4 §U16: track which draft state we last validated, so the UI
     *  can show a "fresh" valid banner only when no edits happened since. */
    let lastValidatedDraftKey = $state('');
    /** User-dismissed flag for the issues banner; reset on every new validate. */
    let issuesDismissed = $state(false);

    let isFreshlyValid = $derived(scheduler.state.lastValidatedAt != null && issues.length === 0 && lastValidatedDraftKey === lastDraftKey && lastDraftKey !== '');
    let showIssuesBanner = $derived(issues.length > 0 && !issuesDismissed);
    let fieldIssues = $derived(issues.filter((i) => !isBulkBalanceIssue(i)));
    let balanceIssues = $derived(issues.filter(isBulkBalanceIssue));
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
            const tempId = lastOpsIndexMap.get(key)?.[0];
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
        getBrokerIconHtml: (brokerId: number) =>
            getBrokerIconHtmlById(brokerId, brokers as any[], {
                width: 16,
                height: 16,
                style: 'display:inline-block;vertical-align:middle;margin-right:2px;border-radius:2px',
            }),
    });

    $effect(() => {
        if (!open) return;
        const key = JSON.stringify(ops);
        if (key === lastDraftKey) return;
        lastDraftKey = key;
        commitFailed = false;
        activeIssue = null;
        scheduler.trigger('change');
    });

    // =========================================================================
    // Commit
    // =========================================================================

    /**
     * Save-gate: if there are auto-derived "fields to verify" (warning todos) that the user
     * hasn't acknowledged yet, force a confirmation step listing them before committing.
     * Blockers are already gated by `commitDisabled`; this covers non-blocking warnings so the
     * user is prompted to look (e.g. matured-bond nominal quantities) instead of silently saving.
     */
    function requestCommit() {
        if (unseenSuggestionCount > 0) {
            confirmSuggestionsOpen = true;
            return;
        }
        requestCommitPastSuggestions();
    }

    /** The rest of the save gate, once the suggestions are seen or waived: the fields to verify, then the commit. */
    function requestCommitPastSuggestions() {
        if (todoWarningRowCountAll > 0) {
            confirmWarningsOpen = true;
            return;
        }
        requestCommitPastWarnings();
    }

    /** The last gate: dates before 1900 (D-P4, W5-10), asked once for all the rows; then the commit. */
    function requestCommitPastWarnings() {
        if (preFloorEntries.length > 0) {
            confirmPreFloorOpen = true;
            return;
        }
        void commit();
    }

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

            const opsMap = buildOpsIndexMap(resolved);
            const issueSnapshot = captureIssueSnapshot(resolved, opsMap);
            const result = await commitTransactions(payload, {fallback: $t('transactions.bulk.saveFailed')});
            if (result.networkError) {
                formError = result.networkError;
                toasts.error($t('transactions.commit.serverError') || 'Save failed — server error');
                return;
            }
            if (!result.committed) {
                issues = result.issues as unknown as ValidationIssue[];
                applyIssueSnapshot(issueSnapshot, opsMap, result.rawResponse, currentKey);
                issuesDismissed = false;
                commitFailed = true;
                jumpToFirstAutoCostRefusal();
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
        const fromLabel = $t('common.from');
        const toLabel = $t('common.to');
        // Pad to the longer label + colon + 1ch spacing
        const maxCh = Math.max(fromLabel.length, toLabel.length) + 2;
        const labelCls = `inline-block text-lf-muted font-medium`;
        const labelStyle = `min-width:${maxCh}ch`;
        return `<div class="flex flex-col gap-0.5 text-xs leading-tight min-h-[2.5rem] justify-center"><span><span class="${labelCls}" style="${labelStyle}">${fromLabel}:</span> ${fromText}</span><hr class="border-lf-subtle my-0.5"/><span><span class="${labelCls}" style="${labelStyle}">${toLabel}:</span> ${toText}</span></div>`;
    }

    /** Readonly type badge with icon. */
    function renderTypeHtml(type: string): string {
        const label = $t(`transactions.types.${type}`) || type;
        const slug = type.toLowerCase().replace(/_/g, '-');
        const isPair = getTypeRule(type).requiresPair;
        const arrow = isPair ? '<span class="shrink-0">↔</span>' : '';
        return `<span class="inline-flex items-center gap-1.5 text-xs leading-snug" style="white-space:normal"><img src="/icons/transactions/${slug}.png" alt="" style="width:1.75rem;height:1.75rem" class="object-contain shrink-0" data-hide-on-error="display"/>${arrow}<span>${label}</span></span>`;
    }

    /**
     * 66 F7-c1 (§13.4, §14.8): the chip of a parent's linked charges in its Type cell, the markup and label of the
     * transactions table's chip (`TxTypeIconCell`, F5): «N charges» with a chevron, N = the charges under it. A click
     * (caught in capture, `captureChargeChip`) opens and closes the group and does nothing else. `data-charges-modified`
     * marks a group with a charge that is not unchanged; the parent's own status stays its own. None when N = 0.
     */
    function chargesChipHtml(row: PendingOp): string {
        const charges = chargesUnder.get(row.tempId) ?? [];
        if (charges.length === 0) return '';
        const expanded = expandedParents.has(row.tempId);
        const modified = charges.some((c) => deriveStatus(c) !== 'original');
        const label = $t('transactions.table.chargesN', {values: {n: charges.length}}) || `${charges.length} charges`;
        const chevron = expanded ? '<path d="m6 9 6 6 6-6"/>' : '<path d="m9 18 6-6-6-6"/>';
        const toggleText = escapeHtml($t('transactions.linkTooltip.chargesToggle') || 'Show or hide its charges');
        return `<button type="button" class="ml-1 inline-flex items-center gap-0.5 whitespace-nowrap rounded-full border border-lf-input bg-lf-card px-2 text-[11px] font-medium leading-5 text-lf-link hover:bg-lf-hover" data-tx-bulk-charges-toggle="${escapeHtml(row.tempId)}" data-testid="tx-bulk-charges-toggle-${escapeHtml(row.tempId)}" aria-expanded="${expanded}" data-expanded="${expanded}" data-charges-count="${charges.length}"${modified ? ' data-charges-modified="true"' : ''} title="${toggleText}"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${chevron}</svg>${modified ? '<span class="text-lf-warning" aria-hidden="true">•</span>' : ''}${escapeHtml(label)}</button>`;
    }

    /**
     * 66 F7-c1 (§13.5, §15.2): the state of a linked charge, beside its own status: `linked`, `unlink` or `del`. On every
     * row under its parent, and on a charge unlinked from a parent that stays (a top-level row); nothing on other rows.
     */
    /** 66 F7-c1: the state of a linked charge (`linked` / `unlink` / `del`), or null for a row that is not one. */
    function chargeState(row: PendingOp): 'linked' | 'unlink' | 'del' | null {
        // 66 C21: a charge «del» of a row merged here is top-level (no parent is a leg of a pair) and keeps its state.
        if (!indentedIds.has(row.tempId) && !(row.chargeOf !== undefined && (row.parentUnlink || (row.op === 'edit' && row.markedDelete)))) return null;
        return row.op === 'edit' && row.markedDelete ? 'del' : row.parentUnlink ? 'unlink' : 'linked';
    }

    /** Format a cash value as "±amount CODE". */
    function formatCashText(cash: {code: string; amount: string} | null | undefined): string {
        if (!cash) return '—';
        const amt = Number(cash.amount);
        if (isNaN(amt)) return `${cash.amount} ${cash.code}`;
        return formatCurrencyAmountHtml(amt, cash.code, {showSign: true});
    }

    /** H1-fix: Asset name with icon for readonly cells. */
    function renderAssetHtml(assetId: number | null | undefined): string {
        if (assetId == null) return '<span class="text-lf-muted italic">—</span>';
        const info = getAssetInfo(assetId);
        const name = info?.display_name ?? `#${assetId}`;
        // Bug11-fix: use asset type icon as fallback when icon_url is null
        const iconUrl = info?.icon_url ?? (info?.asset_type ? getAssetTypeIconUrl(info.asset_type) : null);
        const iconHtml = iconUrl ? `<img src="${escapeHtml(iconUrl)}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" data-hide-on-error="display" />` : '';
        return `<span class="inline-flex items-center gap-1.5 text-sm truncate">${iconHtml}${escapeHtml(name)}</span>`;
    }

    /** H1-fix: Broker name with favicon icon for readonly cells. */
    function renderBrokerHtml(brokerId: number): string {
        const name = brokers.find((br) => br.id === brokerId)?.name ?? '—';
        const iconHtml = getBrokerIconHtmlById(brokerId, brokers as any[], {
            width: 16,
            height: 16,
            className: 'w-4 h-4 rounded-full object-contain shrink-0',
        });
        return `<span class="inline-flex items-center gap-1.5 text-sm truncate">${iconHtml}${escapeHtml(name)}</span>`;
    }

    let columns = $derived.by<ColumnDef<PendingOp>[]>(() => {
        return [
            {
                id: 'workspace_row',
                header: () => $t('common.rowN', {values: {n: ''}}).trim(),
                displayName: () => $t('common.rowN', {values: {n: ''}}).trim(),
                headerTooltip: () => $t('transactions.bulk.workspaceRowHint'),
                type: 'text',
                width: 70,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    const partner = getPartnerOp(row.tempId);
                    const label = visualRowLabels.get(row.tempId) ?? '—';
                    // 66 F7-c1: a charge under its parent draws `↳` (its label, `<parent>·k`, names it in the banners).
                    if (row.chargeOf !== undefined && indentedIds.has(row.tempId)) {
                        return {type: 'html', html: `<div data-testid="tx-bulk-row-label" data-row-id="${row.tempId}" data-charge-of="${escapeHtml(row.chargeOf)}" data-issue-highlighted="${highlightedIssueIds.has(row.tempId)}" class="pl-3 text-lf-muted" title="${escapeHtml(label)}">↳</div>`};
                    }
                    const content = partner ? renderDualHtml(label, visualRowLabels.get(partner.tempId) ?? '—') : label;
                    return {type: 'html', html: `<div data-testid="tx-bulk-row-label" data-row-id="${row.tempId}" data-issue-highlighted="${highlightedIssueIds.has(row.tempId)}">${content}</div>`};
                },
            },
            {
                id: 'status',
                header: () => $t('common.status'),
                type: 'text',
                // 66 F7-c1: 84, not 70 — the charge chip «Desenlazar» (ES, the longest) fits whole.
                width: 84,
                sortable: false,
                filterable: false,
                // Bugfix-3 §U14: hidden by default — operations are atomic and
                // independent so the new/edit badge is rarely actionable.
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    const st = deriveStatus(row);
                    // B5: split-queued badge takes priority
                    if (row.op === 'edit' && splitTxIdsSet.has((row as any).txId)) {
                        return {type: 'html', html: '<span data-testid="tx-bulk-row-status" data-status="split" class="px-1.5 py-0.5 text-[10px] rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">✂️ split</span>'};
                    }
                    // 66 F7-c1 (consultant, v5): one chip in the Status cell. A charge «del» shows the row's «🔴 del»; a charge
                    // «unlink» shows «Unlink» in place of «edit», drawn as a chip on the tinted row; a linked charge keeps the
                    // row's status, with 🔗 beside it. The charge's state rides on a wrapper that draws nothing.
                    const charge = chargeState(row);
                    const statusHtml =
                        charge === 'unlink'
                            ? `<span data-testid="tx-bulk-row-status" data-status="${st}" class="px-1.5 py-0.5 text-[10px] rounded border border-lf-info-line bg-lf-info-soft text-lf-info-on-soft">${escapeHtml($t('transactions.form.charges.unlink'))}</span>`
                            : st === 'new'
                              ? '<span data-testid="tx-bulk-row-status" data-status="new" class="px-1.5 py-0.5 text-[10px] rounded bg-lf-success-soft text-lf-success-on-soft">new</span>'
                              : st === 'edited'
                                ? '<span data-testid="tx-bulk-row-status" data-status="edited" class="px-1.5 py-0.5 text-[10px] rounded bg-lf-warning-soft text-lf-warning-on-soft">edit</span>'
                                : st === 'delete'
                                  ? '<span data-testid="tx-bulk-row-status" data-status="delete" class="px-1.5 py-0.5 text-[10px] rounded bg-lf-danger-soft text-lf-danger-on-soft">🔴 del</span>'
                                  : '<span data-testid="tx-bulk-row-status" data-status="original" class="text-lf-muted">·</span>';
                    if (!charge) return {type: 'html', html: statusHtml};
                    const link = charge === 'linked' ? `<span class="text-lf-muted" title="${escapeHtml($t('transactions.form.charges.title'))}">🔗</span>` : '';
                    return {type: 'html', html: `<span data-testid="tx-bulk-charge-state" data-state="${charge}" class="inline-flex items-center gap-1 whitespace-nowrap">${statusHtml}${link}</span>`};
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
                header: () => $t('common.date'),
                type: 'text',
                width: 140,
                sortable: true,
                filterable: false,
                getValue: (row) => row.fields.date,
                // 66 F7-c1 (§14.5): one order, ours — `gridRows` is already sorted by date in the header's direction,
                // each open parent followed by its charges. The table's sort is stable, so a constant keeps that order
                // in both directions; the header only sets `dateSortDirection` (`onSortChange`).
                sortFn: () => 0,
                headerTooltip: () => bulkDisplayText('transactions.bulk.dateSortHint', 'Date is primary. Pairs stay together, ordered by earliest leg date, then latest leg date and stable row ID.'),
                cell: (row): CellContent => {
                    // Paired rows with different dates → Da:/A:
                    const pOp = getPartnerOp(row.tempId);
                    const content = pOp && pOp.fields.date !== row.fields.date ? renderDualHtml(row.fields.date, pOp.fields.date) : `<span class="font-mono text-sm text-lf-secondary">${escapeHtml(row.fields.date)}</span>`;
                    return {type: 'html', html: `<div data-testid="tx-bulk-date" data-row-id="${row.tempId}" data-date="${escapeHtml(row.fields.date)}" data-partner-date="${escapeHtml(pOp?.fields.date ?? '')}">${content}</div>`};
                },
            },
            {
                id: 'type',
                header: () => $t('common.type'),
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
                        if (SPLIT_TYPE_MAP[origType]) {
                            // 66 C22d: the type the split gives this half (`postSplitType`, the one computation), or the
                            // user's own; its charges chip under it, as on any parent.
                            const targetType = postSplitType(row, pendingSplits);
                            const origSlug = origType.toLowerCase().replace(/_/g, '-');
                            const transition = `<span class="inline-flex items-center gap-1 text-[11px]"><img src="/icons/transactions/${origSlug}.png" alt="" style="width:1.5rem;height:1.5rem" class="object-contain shrink-0" data-hide-on-error="display"/> <span class="text-lf-muted">→</span> ${renderTypeHtml(targetType)}</span>`;
                            const splitChip = chargesChipHtml(row);
                            return {type: 'html', html: splitChip ? `<div class="flex flex-col items-start gap-1" style="white-space:normal">${transition}${splitChip}</div>` : transition};
                        }
                        return {type: 'html', html: `<span class="text-[11px]">${renderTypeHtml(row.fields.type)} → <span class="text-purple-600 dark:text-purple-400">✂️ ADJUSTMENT</span></span>`};
                    }
                    const chip = chargesChipHtml(row);
                    // 66 F7-c1: the chip goes under the type, inside the cell (side by side it overflows the column).
                    if (chip) return {type: 'html', html: `<div class="flex flex-col items-start gap-1" style="white-space:normal">${renderTypeHtml(row.fields.type)}${chip}</div>`};
                    return {type: 'html', html: renderTypeHtml(row.fields.type)};
                },
            },
            {
                id: 'asset',
                header: () => $t('common.asset'),
                type: 'text',
                width: 180,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    if (getTypeRule(row.fields.type).assetField === 'forbidden') {
                        return {type: 'html', html: '<span class="text-lf-muted italic">—</span>'};
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
                        return {type: 'html', html: '<span class="text-lf-muted italic">n/a</span>'};
                    }
                    const qty = row.fields.quantity ?? '0';
                    // H2-fix: paired rows with non-zero qty → show Da:/A: with signed values + emoji
                    const rule = getTypeRule(row.fields.type);
                    const pOp = getPartnerOp(row.tempId);
                    if (rule.requiresPair && pOp && Number(qty) !== 0) {
                        const absVal = escapeHtml(quantityText(applySign(String(qty), 'positive')));
                        const fromQty = `-${absVal} 📉`;
                        const toQty = `+${absVal} 📈`;
                        return {type: 'html', html: renderDualHtml(fromQty, toQty)};
                    }
                    // Trailing zeros removed, the digits as written (C-97b)
                    const fmtQty = quantityText(String(qty));
                    return {type: 'html', html: `<span class="font-mono text-sm">${escapeHtml(fmtQty)}</span>`};
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
                        return {type: 'html', html: '<span class="text-lf-muted italic">—</span>'};
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
                // W2-6: read-only, calculated from the row's own quantity and cash by the helper the transactions table uses.
                id: 'unit_price',
                header: () => $t('transactions.table.unitPrice'),
                type: 'text',
                width: 120,
                sortable: false,
                filterable: false,
                cell: (row): CellContent => {
                    // Cash is stored as a magnitude here: the helper reads magnitudes, so the display sign does not matter.
                    return {type: 'html', html: unitPriceCellHtml(row.fields, {testId: 'tx-bulk-unit-price', isPairLeg: getPartnerOp(row.tempId) != null})};
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
                            const lockHtml = `<span class="text-lf-danger" data-testid="tx-bulk-partner-lock" title="${$t('transactions.bulk.partnerInaccessible')}">🔒</span>`;
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
                        return {type: 'html', html: '<span class="text-lf-muted italic">—</span>'};
                    }

                    // Read-only mirror of WacPreviewSection's Total/Per-unit toggle (same
                    // 'wacPreviewUnitMode' localStorage key) so this cell stays consistent with
                    // whatever the row's own FormModal last showed. `cbo.amount` is always
                    // per-unit at rest — only the display here gets multiplied.
                    const unitModeStored = getUserStorage('wacPreviewUnitMode', 'unit');
                    const qtyAbs = Math.abs(Number(source.fields.quantity ?? '0'));
                    const showAsTotal = unitModeStored === 'total' && qtyAbs > 0;
                    const displayAmount = (amount: number) => (showAsTotal ? amount * qtyAbs : amount);
                    const modeSuffix = `<span class="text-[9px] text-lf-muted ml-1">${showAsTotal ? ($t('transactions.wacPreview.unitModeTotal') ?? 'Total') : ($t('transactions.wacPreview.unitModePerUnit') ?? 'Per unit')}</span>`;

                    // mode 'auto'
                    if (mode === 'auto') {
                        // `…` means the value is still being computed, `—` that it was computed and there is nothing to
                        // propose (a BUY has no cost basis to match, a SELL may find no lot); the lightbulb stays in both
                        // because the cell is still in automatic mode. `validateRuns === 0` belongs with «unknown»: before
                        // the first run nobody has asked yet, so an em-dash would be a verdict the app has not reached.
                        // A cost of 0 is read the same way (W6-2): while the validation is not settled it may be only the
                        // currency hint Auto sends, not a computed value.
                        const unknown = scheduler.state.isPending || scheduler.state.isValidating || scheduler.state.validateRuns === 0;
                        const state = autoCostCellState(cbo?.amount, !unknown);
                        if (cbo && state === 'ready') {
                            return {
                                type: 'html',
                                html: `<span class="text-lf-muted italic" data-testid="tx-bulk-cost-basis-auto" data-state="ready">💡 ${formatCurrencyAmountHtml(displayAmount(Number(cbo.amount)), cbo.code)}${modeSuffix}</span>`,
                            };
                        }
                        return {
                            type: 'html',
                            html: `<span class="text-lf-muted italic" data-testid="tx-bulk-cost-basis-auto" data-state="${state}">💡 ${state === 'pending' ? '…' : '—'}</span>`,
                        };
                    }

                    // mode 'manual'
                    if (cbo && cbo.amount) {
                        return {type: 'html', html: `<span class="font-mono text-xs" data-testid="tx-bulk-cost-basis-manual">${formatCurrencyAmountHtml(displayAmount(Number(cbo.amount)), cbo.code)}${modeSuffix}</span>`};
                    }
                    // User explicitly cleared the value
                    return {type: 'html', html: '<span class="text-lf-muted italic">—</span>'};
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
                    if (row.fields.asset_event_id == null) return {type: 'html', html: '<span class="text-lf-muted">—</span>'};
                    const ev = eventCache.get(row.fields.asset_event_id);
                    if (!ev) return {type: 'html', html: `<span class="font-mono text-xs">#${row.fields.asset_event_id}</span>`};
                    const emojiMap: Record<string, string> = {DIVIDEND: '💰', INTEREST: '🏦', SPLIT: '✂️', PRICE_ADJUSTMENT: '📊', MATURITY_SETTLEMENT: '📅'};
                    const emoji = emojiMap[ev.type] ?? '📋';
                    const shortDate = new Date(ev.date).toLocaleDateString(uiLocale(), {day: 'numeric', month: 'short'});
                    const fullDate = new Date(ev.date).toLocaleDateString(uiLocale(), {day: 'numeric', month: 'long', year: 'numeric'});
                    const amt = parseFloat(ev.amount);
                    let fmtAmt = '';
                    if (amt !== 0) {
                        const ci = getCurrencyInfo(ev.code);
                        const sym = ci.symbol && ci.symbol !== ev.code ? `${ci.symbol} ` : '';
                        const flag = ci.flag_emoji && ci.flag_emoji !== '🏳️' ? `<span class="emoji-flag">${ci.flag_emoji}</span> ` : '';
                        fmtAmt = `${formatFixed(amt, Number.isInteger(amt) ? 0 : 2)} ${sym}${flag}${ev.code}`;
                    }
                    // Build rich HTML tooltip
                    const typeLabel = $t(`assetDetail.eventType.${ev.type}`) || ev.type.replace(/_/g, ' ');
                    let tooltipHtml = `<strong>${emoji} ${typeLabel}</strong><br>${fullDate}`;
                    if (amt !== 0) tooltipHtml += `<br>${$t('transactions.bulk.eventTooltipAmount')}: <span style="font-family:monospace">${formatFixed(amt, 4)} ${ev.code}</span>`;
                    if (ev.notes) tooltipHtml += `<br>📝 ${$t('common.notes')}: ${escapeHtml(ev.notes)}`;
                    return {
                        type: 'html',
                        html: `<span class="inline-flex items-center gap-1 text-xs"><span class="text-sm">${emoji}</span><span class="text-lf-secondary">${shortDate}</span>${fmtAmt ? `<span class="font-mono text-lf-muted">${fmtAmt}</span>` : ''}</span>`,
                        tooltip: {html: tooltipHtml, position: 'top'},
                    };
                },
            },
            {
                id: 'description',
                header: () => $t('common.description'),
                type: 'text',
                width: 200,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    if (!row.fields.description) return {type: 'html', html: '<span class="text-lf-muted">—</span>'};
                    const escaped = escapeHtml(row.fields.description);
                    return {
                        type: 'html',
                        html: `<span class="text-xs text-lf-secondary truncate block leading-tight">${escaped}</span>`,
                        tooltip: {text: row.fields.description, position: 'top', maxWidth: '400px'},
                    };
                },
            },
            {
                id: 'tags',
                header: () => $t('common.tags'),
                type: 'text',
                width: 180,
                sortable: false,
                filterable: false,
                hiddenByDefault: false,
                cell: (row): CellContent => {
                    if (row.fields.tags.length === 0) return {type: 'html', html: '<span class="text-lf-muted">—</span>'};
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
                        return {type: 'html', html: `<code class="text-xs font-mono text-lf-muted">#${selfId} <span class="text-base">⇄</span> #${pOp.txId}</code>`};
                    }
                    if (pOp && pOp.op === 'create') return {type: 'html', html: '<code class="text-xs font-mono text-indigo-400">new <span class="text-base">⇄</span> new</code>'};
                    if (row.op === 'create' && row.link_uuid) return {type: 'html', html: `<code class="text-xs font-mono text-lf-muted">${row.link_uuid.slice(0, 8)}…</code>`};
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
            // A pair whose partner sits on a broker the user cannot read is not edited from here: off, saying why (77 SEL-M)
            blocked: (row: PendingOp) => (getPartnerOp(row.tempId)?.inaccessible ? {hint: () => $t('transactions.bulk.editPartnerInaccessible'), reason: 'partner-inaccessible'} : null),
            // 66 F7-c1: an indented row keeps «Edit row» — on touch and from the keyboard it is the double-click's twin.
        },
        {
            id: 'clone',
            icon: Copy,
            label: () => $t('transactions.bulk.cloneRow') || 'Clone row',
            // 66 TL-3: offered on a charge under its parent again (the FEE consultant); its copy sits under the same parent.
            onClick: (row: PendingOp) => void cloneRow(row.tempId),
        },
        {
            id: 'split',
            icon: Unlink,
            label: () => $t('transactions.actions.split') || 'Split pair',
            onClick: (row: PendingOp) => handleSplitRow(row),
            visible: (row: PendingOp) => {
                if (indentedIds.has(row.tempId)) return false;
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
                // 66 C22c: a charge linked to a half while the split was queued would now hang under a leg (rule 8): its
                // link is undone as by a reset, with the same `paired` toast.
                keepUnlinkedFromUnfitParents(new Set([row.tempId, ...(partnerOp ? [partnerOp.tempId] : [])]), 'tx.bulk.undo-split.charge.kept-unlinked');
                lastSuggestKey = ''; // B9: invalidate suggest
            },
            visible: (row: PendingOp) => !indentedIds.has(row.tempId) && row.op === 'edit' && splitTxIdsSet.has((row as any).txId),
        },
        {
            id: 'suggest',
            icon: Lightbulb,
            label: () => $t('transactions.bulk.suggestLightbulb') || 'Import suggestion',
            onClick: (row: PendingOp) => {
                // BUG-C7: open suggest picker filtered to this row's importable candidates
                const entry = importableSuggestions.find((s) => s.tempId === row.tempId);
                if (entry && entry.candidates.length > 0) {
                    // Open picker filtered to just this row's candidates
                    openSuggestPicker();
                } else {
                    // Fallback: scroll to banner
                    const banner = document.querySelector('[data-testid="promote-suggest-banner"]');
                    if (banner) {
                        banner.scrollIntoView({behavior: 'smooth', block: 'center'});
                        banner.classList.add('ring-2', 'ring-lf-success');
                        setTimeout(() => banner.classList.remove('ring-2', 'ring-lf-success'), 1500);
                    }
                }
            },
            visible: (row: PendingOp) => {
                if (indentedIds.has(row.tempId) || getPartnerOp(row.tempId)) return false;
                // Show if this row (saved or new) has importable DB candidates OR is in banner suggestions
                return importableSuggestions.some((s) => s.tempId === row.tempId) || bannerSuggestions.some((s) => s.tempIdA === row.tempId || s.tempIdB === row.tempId);
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
            // 66 F7-c1 (§14.2): «del» on a parent waits for its charges to be read, and stays off when they could not be.
            // The reason is reachable at the touch and from the keyboard (77 SEL-M), its code the state of the read.
            blocked: (row: PendingOp) => {
                if (row.op !== 'edit' || row.markedDelete) return null;
                const unread = chargesUnread(row);
                const hint = chargesUnreadReason(row);
                return unread === null || hint === null ? null : {hint, reason: unread === 'loading' ? 'charges-loading' : 'charges-failed'};
            },
            variant: 'danger' as const,
        },
        {
            id: 'remove-from-batch',
            icon: X,
            label: () => $t('transactions.bulk.removeFromBatch') || 'Remove from batch',
            onClick: (row: PendingOp) => removeRow(row.tempId),
            visible: (row: PendingOp) => !indentedIds.has(row.tempId) && row.op === 'edit' && deriveStatus(row) !== 'delete',
        },
        {
            id: 'reset',
            icon: Undo2,
            label: () => $t('transactions.bulk.resetRow'),
            onClick: (row: PendingOp) => resetRow(row.tempId),
            // 66 F7-c1: also on an untouched parent whose charges could not be read: the reset reads them again (the toast says so).
            visible: (row: PendingOp) => !indentedIds.has(row.tempId) && row.op === 'edit' && (deriveStatus(row) === 'edited' || deriveStatus(row) === 'delete' || (chargesReadFailed.has(row.txId) && parentChargesMissing(row))),
        },
    ]);

    // =========================================================================
    // Issue → row navigation
    // =========================================================================

    function bulkDisplayText(key: string, fallback: string, values?: Record<string, string | number>): string {
        const translated = $t(key, {values});
        return translated === key ? fallback : translated;
    }

    function getIssueRows(issue: ValidationIssue): BulkIssueRow[] {
        const rows = resolveBulkIssueRows(issue, isBulkBalanceIssue(issue) ? lastBalanceRows : lastIssueRows, lastOpsIndexMap);
        const positions = new Map([...visualRowLabels.keys()].map((id, index) => [id, index]));
        return rows.filter((row) => positions.has(row.tempId)).sort((a, b) => positions.get(a.tempId)! - positions.get(b.tempId)!);
    }

    function issueRowsLabel(issue: ValidationIssue): string {
        const rows = getIssueRows(issue)
            .map((row) => visualRowLabels.get(row.tempId)!)
            .join(', ');
        return bulkDisplayText('transactions.bulk.workspaceRows', `Workspace rows: ${rows}`, {rows});
    }

    /** 66 F7-c1: the row on screen that stands for an issue's row (`rowAnchor`): a charge in a closed group → its parent. */
    function issueRowAnchor(row: {tempId: string; pairedWith?: string}): string {
        const op = ops.find((o) => o.tempId === row.tempId);
        return op ? rowAnchor(op, ops, expandedParents) : (row.pairedWith ?? row.tempId);
    }

    /** 66 F7-c1 (§13.8): the groups to open so these rows are drawn: a charge under a closed parent opens its group. */
    async function openGroupsOf(tempIds: readonly string[]) {
        const parents = tempIds.map((id) => ops.find((o) => o.tempId === id)).filter((o): o is PendingOp => !!o && o.chargeOf !== undefined && indentedIds.has(o.tempId) && !expandedParents.has(o.chargeOf));
        if (parents.length === 0) return;
        expandedParents = new Set([...expandedParents, ...parents.map((o) => o.chargeOf!)]);
        await tick();
    }

    /** Page the grid to the row of a todo and highlight it, as a validation issue does.
     *  `rowId` is the visible row: a hidden partner's todo leads to its paired row; a charge's todo opens its group. */
    async function jumpToTodoRow(rowId: string) {
        await openGroupsOf([rowId]);
        if (!tableRef?.getSortedRowIds().includes(rowId)) {
            notify({
                name: 'tx.bulk.todo.row-hidden',
                detail: {rowIds: [rowId]},
                toast: {variant: 'warning', message: $t('transactions.bulk.issueRowsHidden')},
            });
            return;
        }
        tableRef.navigateToRowId(rowId);
    }

    /** Q-J57-4: page the grid to the first row refused for an Auto cost (`firstAutoCostRefusalRowId`), as a click on its
     *  issue would; nothing when the issues no longer describe the draft or no row is refused for an Auto cost. */
    function jumpToFirstAutoCostRefusal() {
        if (lastIssueDraftKey !== lastDraftKey) return;
        const rowId = firstAutoCostRefusalRowId(issues, getIssueRows);
        if (rowId) void jumpToTodoRow(rowId);
    }

    async function jumpToIssue(issue: ValidationIssue) {
        if (lastIssueDraftKey !== lastDraftKey) return;
        const rows = getIssueRows(issue);
        if (rows.length === 0) return;
        // 66 F7-c1 (§13.8): an issue on a charge of a closed group opens the group, then goes to the charge.
        await openGroupsOf(rows.map((row) => row.tempId));
        const affectedIds = new Set(rows.map((row) => issueRowAnchor(row)));
        activeIssue = isBulkBalanceIssue(issue) ? issue : null;
        const firstVisibleId = tableRef?.getSortedRowIds().find((id) => affectedIds.has(id));
        if (!firstVisibleId) {
            notify({
                name: 'tx.bulk.issue.rows-hidden',
                detail: {code: issue.code, rowIds: [...affectedIds]},
                toast: {variant: 'warning', message: $t('transactions.bulk.issueRowsHidden')},
            });
            return;
        }
        tableRef?.navigateToRowId(firstVisibleId);
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
        return (
            getIssueRows(issue)
                .map((row) => visualRowLabels.get(row.tempId))
                .join(', ') || '—'
        );
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
    let hasTodoBlockers = $derived(ops.some((op) => op.todos?.some((t) => t.severity === 'blocker')));
    /** Blocker todos with their row position, so the banner can name the offending rows.
     *  Without this the user only sees a red row and a disabled Save, never the reason. */
    let todoBlockerEntries = $derived(ops.flatMap((op) => (op.todos ?? []).filter((t) => t.severity === 'blocker').map((todo) => ({rowId: op.pairedWith ?? op.tempId, rowNumber: visualRowLabels.get(op.tempId) ?? '—', date: op.fields.date, todo}))));
    /** Warning todos with their row, so the banner can lead to each of them (D4). */
    /** The warning todos of a row that belong to the «fields to verify»: the one for a date before 1900 has its own banner and its own save gate (D-P4, W5-10). */
    const warningTodos = <T extends {field: string; severity?: string; reasonCode?: string}>(todos: T[] | undefined): T[] => (todos ?? []).filter((todo) => todo.severity === 'warning' && !isPreFloorDateTodo(todo));
    let todoWarningEntries = $derived(ops.flatMap((op) => withoutPossibleSplit(warningTodos(op.todos)).map((todo) => ({rowId: op.pairedWith ?? op.tempId, rowNumber: visualRowLabels.get(op.tempId) ?? '—', todo}))));
    let todoWarningsExpanded = $state(false);
    // Folded by default: with evidence tables attached, an expanded banner can be taller
    // than the viewport and push the grid — the thing the user has to fix — off-screen.
    let todoBlockersExpanded = $state(false);
    let todoWarningRowCountAll = $derived(ops.filter((op) => warningTodos(op.todos).length > 0).length);
    let todoWarningRowCount = $derived(ops.filter((op) => withoutPossibleSplit(warningTodos(op.todos)).length > 0).length);
    let possibleSplitEntries = $derived(buildSplitEntries(ops, (tempId) => visualRowLabels.get(tempId) ?? '—'));
    /** The rows dated before 1900 (D-P4, W5-10): a warning per row in the banner, one confirmation at save. */
    let preFloorEntries = $derived(buildPreFloorEntries(ops, (tempId) => visualRowLabels.get(tempId) ?? '—'));
    let splitCreateEntry = $state<PossibleSplitEntry | null>(null);
    function linkSplitEvent(tempId: string, eventId: number) {
        ops = ops.map((d) => {
            if (d.tempId !== tempId) return d;
            const merged = {...d, fields: {...d.fields, asset_event_id: eventId}};
            if (merged.todos?.length) {
                merged.todos = remainingTodos(merged.todos, merged.fields);
                if (merged.todos.length === 0) delete merged.todos;
            }
            return merged;
        });
    }
    // «Fill from price history» (project 79, STK-4b): the rows with an open `reward_value` todo get the asset's close of
    // that very day, per unit, from the backend's one reader; the outcome is a count shown in the blockers banner.
    let rewardFillPending = $derived(rewardFillCandidates(ops).length);
    let rewardFillRunning = $state(false);
    let rewardFillResult = $state<(RewardFillCounts & {failed: boolean}) | null>(null);
    async function fillRewardsFromHistory() {
        const candidates = rewardFillCandidates(ops);
        if (candidates.length === 0 || rewardFillRunning) return;
        rewardFillRunning = true;
        try {
            const asked = candidates.filter((candidate) => candidate.assetId != null);
            const answers = asked.length > 0 ? await fetchRewardValues(asked.map((candidate) => ({assetId: candidate.assetId as number, date: candidate.date}))) : [];
            if (answers === null) {
                rewardFillResult = {filled: 0, noPrice: 0, noHistory: 0, failed: true};
                return;
            }
            const fill: RewardFillAnswer[] = candidates.map((candidate) => {
                if (candidate.assetId == null) return {tempId: candidate.tempId, status: 'NO_HISTORY', value: null};
                const answer = answers[asked.indexOf(candidate)];
                return {tempId: candidate.tempId, status: answer?.status ?? 'NO_PRICE_THAT_DAY', value: answer?.suggestion ? {code: answer.suggestion.code, amount: answer.suggestion.amount} : null};
            });
            const result = applyRewardFill(ops, fill);
            ops = result.ops;
            rewardFillResult = {...result.counts, failed: false};
            notify({name: 'tx.bulk.rewards.filled', detail: {...result.counts}});
        } finally {
            rewardFillRunning = false;
        }
    }
    let splitCreateAsset = $derived(splitCreateEntry?.assetId != null ? getAssetInfo(splitCreateEntry.assetId) : null);
    /** Human-readable list of the auto-derived fields still awaiting verification (for the Save-gate dialog). */
    let todoWarningItems = $derived(ops.flatMap((op) => warningTodos(op.todos).map((todo) => resolveBrimTodoMessage(todo, $t) || todo.field)));
    // 66 F7-c1 (§14.2): while the charges of a parent are being read, the batch is not complete: «Save all» waits.
    let commitDisabled = $derived(committing || ops.length === 0 || actionCount === 0 || hasTodoBlockers || chargesInFlight.size > 0);
    let commitLabel = $derived(committing ? $t('common.saving') : $t('common.saveAll'));

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
    /** 66 F7-b: the Form's charges section is editable (`allowChargeEdits`): the Bulk saves what it hands back. Off only
     *  when the charges of the parent it opens on could not be read: the section is then read-only. */
    let formChargeEdits = $state(true);
    /** 66 F7-d: the saved row the Form highlights — the one the user came from with «Open». */
    let formHighlightTxId = $state<number | null>(null);
    /** Guards the charges' read before a parent's Form: an answer for an older open is dropped. */
    let chargesReadRequest = 0;

    // PickerModal (Plan B Step 9): "Search & add" existing DB transactions.
    let pickerOpen = $state(false);
    let pickerExcludeIds = $derived(new Set(ops.filter((d) => opTxId(d) != null).map((d) => opTxId(d)!)));
    // PickerModal reads from txStore directly (Plan C Step 2)

    // -------------------------------------------------------------------------
    // ImportWizardModal (Phase 07 Part 5 v5 M1→M4): BRIM Import Wizard → BulkModal bridge.
    // -------------------------------------------------------------------------
    let importWizardOpen = $state(false);
    let guideBulkObservedOpen = false;
    let nestedGuideHostObserved = false;
    let bulkGuideAttemptedForOpen = new Set<TransactionBulkStepId>();
    let bulkValidationObserved = false;
    let bulkSelectionObserved = false;
    let bulkSaveObserved = false;
    let importGuideBulkReady = $state(false);
    let importGuideBulkProgress = $state<{current: number; total: number} | undefined>(undefined);
    let pendingCreateTransactions = $derived.by<TransactionCreateItem[]>(() =>
        ops.flatMap((op) => {
            if (op.op !== 'create') return [];
            return [buildCreatePayload(opToTxFields(op), getTypeRule(op.fields.type as TransactionTypeCode)) as TransactionCreateItem];
        }),
    );
    /** DB transaction ids the user has marked for deletion in the bulk editor. Passed to the
     *  import wizard so DB-duplicate detection drops matches against to-be-deleted rows — a
     *  re-imported row is not flagged as a duplicate of a transaction that is about to go. */
    let pendingDeleteTxIds = $derived.by<number[]>(() => ops.flatMap((op) => (op.op === 'edit' && op.markedDelete ? [op.txId] : [])));

    /** Convert a TXCreateItem (from BRIM parse) to a PendingOp 'create' row.
     *  Signs are converted to display values (BulkModal convention: positive display,
     *  sign applied on commit/validate via getTypeRule().quantityRule + cashSign). */
    function txCreateItemToPendingOp(tx: TransactionCreateItem): PendingOp {
        const rule = getTypeRule(tx.type);

        // Quantity: convert storage sign → display sign
        let qty = String(tx.quantity ?? '0');
        if (rule.quantityRule === 'negative' && exactDecimalSign(qty) === -1) qty = quantityText(applySign(String(qty), 'positive'));

        // Cash: convert storage sign → display sign
        let cash: {code: string; amount: string} | null = null;
        const rawCash = tx.cash && !Array.isArray(tx.cash) ? tx.cash : null;
        if (rawCash) {
            // B-47: the editor's convention (W-B65), as in `fieldsFromTx`: exact, never through Number.
            cash = {code: String(rawCash.code), amount: magnitudeForRule(String(rawCash.amount), rule.cashSign)};
        }

        // cost_basis_override
        const rawCbo = tx.cost_basis_override && !Array.isArray(tx.cost_basis_override) ? tx.cost_basis_override : null;
        const cbo = rawCbo ? {code: String((rawCbo as any).code ?? ''), amount: String((rawCbo as any).amount ?? '')} : null;

        // cost_basis_mode
        const rawCbm = tx.cost_basis_mode && !Array.isArray(tx.cost_basis_mode) ? tx.cost_basis_mode : null;
        const cbMode = (rawCbm as 'auto' | 'auto-detail' | 'manual' | null | undefined) ?? null;
        // BulkModal only uses 'auto' | 'manual' | null
        const cbDisplay: 'auto' | 'manual' | null = cbMode === 'auto-detail' ? 'auto' : (cbMode ?? null);

        // asset_id: only accept plain number (no arrays, no null for typed ops)
        const assetId = typeof tx.asset_id === 'number' ? tx.asset_id : null;

        // link_uuid
        const linkUuid = tx.link_uuid && !Array.isArray(tx.link_uuid) ? String(tx.link_uuid) : null;

        return {
            op: 'create',
            tempId: generateUUID(),
            createdSeq: nextCreatedSeq(),
            link_uuid: linkUuid,
            fields: {
                broker_id: tx.broker_id,
                asset_id: assetId,
                type: tx.type as TransactionTypeCode,
                date: tx.date,
                quantity: qty,
                cash,
                tags: Array.isArray(tx.tags) ? (tx.tags as string[]).filter((t): t is string => typeof t === 'string') : [],
                description: String(tx.description ?? ''),
                asset_event_id: typeof tx.asset_event_id === 'number' ? tx.asset_event_id : null,
                cost_basis_override: cbo,
                cost_basis_mode: cbDisplay,
            },
        };
    }

    /** Link paired ops by shared link_uuid: second op becomes hidden partner. */
    function linkPairedImportOps(newOps: PendingOp[]): PendingOp[] {
        const byUuid = new Map<string, PendingOp[]>();
        for (const op of newOps) {
            if (op.link_uuid) {
                const list = byUuid.get(op.link_uuid) ?? [];
                list.push(op);
                byUuid.set(op.link_uuid, list);
            }
        }
        for (const pair of byUuid.values()) {
            if (pair.length === 2) {
                pair[1].pairedWith = pair[0].tempId;
            }
        }
        return newOps;
    }

    /**
     * 66 P1b: the names of ONE hand-over become the Bulk's links. A row carrying `ref` is a parent, a row naming it in
     * `parent_ref` its charge (`chargeOf`), when the Bulk's own rule accepts the group (`bulkLinkSelection` → `ok`, the
     * same answer «Link» gets); otherwise the charges stay free. A name carried by two rows links nothing. No
     * `followsParent`: an imported charge keeps its values. The groups start closed (an import brings its charges
     * closed); the names are not kept, so two hand-overs never cross. `newOps[i]` is the op of `creates[i]`.
     */
    function linkImportedCharges(all: PendingOp[], creates: ReadonlyArray<{tx: TransactionCreateItem}>, newOps: readonly PendingOp[]): PendingOp[] {
        const named = (value: unknown): string | null => (typeof value === 'string' && value !== '' ? value : null);
        const parentByName = new Map<string, PendingOp | null>();
        const chargesByName = new Map<string, PendingOp[]>();
        creates.forEach((item, i) => {
            const names = item.tx as {ref?: string | null; parent_ref?: string | null};
            const ref = named(names.ref);
            if (ref) parentByName.set(ref, parentByName.has(ref) ? null : newOps[i]);
            const parentRef = named(names.parent_ref);
            if (parentRef) chargesByName.set(parentRef, [...(chargesByName.get(parentRef) ?? []), newOps[i]]);
        });
        let result = all;
        for (const [name, charges] of chargesByName) {
            const parent = parentByName.get(name);
            const own = charges.filter((c) => c !== parent);
            if (!parent || own.length === 0) continue;
            const current = (op: PendingOp) => result.find((d) => d.tempId === op.tempId) ?? op;
            // Charge by charge, as the backend judges a link (66 P1b §6.1): one charge that breaks a rule (another
            // asset) stays free and never takes the link away from its siblings.
            const valid = own.filter((charge) => {
                const state = bulkLinkSelection([current(parent), current(charge)], result, txStoreGet, {roleOf: (type) => getTypeRule(type).chargeRole, canEdit: (brokerId) => canEditBroker(brokerId)}, (op) => postSplitType(op, pendingSplits));
                // The parent must be the row that carried the name: the rule picks the parent by type.
                return state.kind === 'ok' && state.parent.tempId === parent.tempId;
            });
            if (valid.length === 0) continue;
            result = linkInBulk(result, current(parent), valid.map(current));
        }
        return result;
    }

    async function onImportBatch(creates: Array<{tx: TransactionCreateItem; todos: ImportTodo[]}>, guideProgress?: {current: number; total: number}) {
        const newOps = creates.map((item) => {
            const op = txCreateItemToPendingOp(item.tx);
            if (item.todos.length > 0) op.todos = item.todos;
            // Q-J57-5 (a) and Q-J57-1 (c): a row the plugin left without a cost mode starts in Auto where its type takes a
            // cost, so the hand-over's validation costs it or refuses it and leads to it; a cost the plugin wrote, or a
            // blocking cost todo, starts it in Manual.
            op.fields.cost_basis_mode = initialCostBasisMode({mode: op.fields.cost_basis_mode, cost: op.fields.cost_basis_override, costAllowed: costBasisModeAllowed(op.fields), autoAllowed: getTypeRule(op.fields.type).costBasisAuto}, item.todos);
            return op;
        });
        const linked = linkPairedImportOps(newOps);
        ops = linkImportedCharges([...ops, ...linked], creates, newOps);
        importGuideBulkReady = true;
        importGuideBulkProgress = guideProgress;
        importWizardOpen = false;
        toasts.success($t('importWizard.importedCount', {values: {n: creates.length}}));
        // Every hand-over is validated once, whatever its size (D5): above the auto threshold the
        // editor would otherwise say nothing until "Validate now". Later edits follow the usual rules.
        // The validation checks the state its draft key names, and the key effect names the new rows only once this
        // call has returned: wait for it, or the verdict comes back «stale» and is dropped — nothing shown above the
        // threshold, and no lead to a refused row (Q-J57-4). The manual trigger cancels the run the effect queued.
        await tick();
        scheduler.trigger('manual');
    }

    // BUG-C7: Suggest picker — opens PickerModal filtered to importable candidates
    let suggestPickerOpen = $state(false);
    function openSuggestPicker() {
        suggestPickerOpen = true;
        suggestPickerSeen = true;
    }

    function openPicker() {
        pickerOpen = true;
    }
    /**
     * Saved rows (in the store) join the Bulk as unchanged edits, the way the picker brings them: the pairs collapsed, a
     * parent adopting its charges already here and a charge joining its parent (66 F7-b, §11.6), the group of a charge the
     * user brought opened (F7-c1, §14.7), the charges of a saved parent read (§14.2). Returns the operations added.
     */
    function addSavedRows(txIds: readonly number[]): PendingOp[] {
        const existing = new Set(ops.filter((d) => opTxId(d) != null).map((d) => opTxId(d)!));
        const newOps: PendingOp[] = [];
        for (const id of txIds) {
            if (existing.has(id) || !txStoreGet(id)) continue;
            existing.add(id);
            newOps.push(editOpFromTx(id, {addedViaPicker: true}));
        }
        if (newOps.length === 0) return [];
        const collapsed = collapsePairedOps(newOps);
        const ownedBefore = new Set(ops.filter((d) => d.chargeOf !== undefined).map((d) => d.tempId));
        ops = adoptCharges([...ops, ...collapsed], txStoreGet);
        const brought = ops.filter((d) => d.chargeOf !== undefined && !ownedBefore.has(d.tempId) && !d.loadedWithParent && isUnderParent(d, ops)).map((d) => d.chargeOf!);
        if (brought.length > 0) expandedParents = new Set([...expandedParents, ...brought]);
        loadMissingCharges(collapsed);
        return collapsed;
    }

    function handlePickerAdd(rows: TXReadItem[]) {
        addSavedRows(rows.map((r) => r.id));
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
        ++chargesReadRequest;
        formChargeEdits = true;
        formHighlightTxId = null;
        formMode = 'create';
        formItems = null;
        formEditingTempId = null;
        formKey++;
        formOpen = true;
    }

    /** The highlight the «restore and edit» question carries to the Form it opens (66 F7-d, «Open»). */
    let confirmEditDeleteHighlight: number | null = null;

    /** B23 Step 4: intercept edit on deleted row — show confirm before restoring. `highlightTxId`: the row the Form
     *  highlights (66 F7-d, the row «Open» came from). */
    function handleEditRowClick(row: PendingOp, highlightTxId: number | null = null) {
        // W4b: block edit if partner is inaccessible
        if (getPartnerOp(row.tempId)?.inaccessible) return;
        if (deriveStatus(row) === 'delete') {
            confirmEditDeleteRow = row;
            confirmEditDeleteHighlight = highlightTxId;
            confirmEditDeleteOpen = true;
            return;
        }
        openEditRowForm(row, highlightTxId);
    }

    /** B23 Step 4: user confirmed restore-and-edit on a deleted row. */
    function confirmRestoreAndEdit() {
        if (!confirmEditDeleteRow) return;
        const target = ops.find((d) => d.tempId === confirmEditDeleteRow!.tempId);
        if (target) setRowDeleted(target.tempId, false);
        const row = confirmEditDeleteRow;
        const highlight = confirmEditDeleteHighlight;
        confirmEditDeleteOpen = false;
        confirmEditDeleteRow = null;
        confirmEditDeleteHighlight = null;
        openEditRowForm(row, highlight);
    }

    /**
     * 66 F7-d (§20.4, §21.4, §22.4): «Open» in the Form, on a parent or a charge with an id. The Form moves to that row
     * by the double-click's entry (`handleEditRowClick`: a row «del» asks «restore and edit»), highlighting the row the
     * user came from.
     *   - present: the row with that `txId` (a hidden partner: the visible row of its pair); under a closed group, the
     *     group opens, so the row is on screen when the Form closes;
     *   - absent: read from the store, else from the server (then added to the store), and added as the picker adds
     *     (`addSavedRows`). It is navigation, not a change: it joins the close guard's baseline;
     *   - a failed read: an error toast; a late answer (the Bulk closed, the Form closed or moved): nothing.
     */
    async function handleFormOpenTransaction(id: number) {
        const fromTempId = formEditingTempId;
        const fromOp = fromTempId !== null ? ops.find((d) => d.tempId === fromTempId) : undefined;
        const fromTxId = fromOp ? (opTxId(fromOp) ?? null) : null;
        const request = chargesReadRequest;
        const stale = () => !open || !formOpen || formEditingTempId !== fromTempId || request !== chargesReadRequest;
        if (!findSavedRow(id)) {
            let row: TXReadItem | null = txStoreGet(id) ?? null;
            if (!row) {
                try {
                    const answer = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {ids: [id]}} as never)) as unknown;
                    row = Array.isArray(answer) ? ((answer as TXReadItem[]).find((r) => r.id === id) ?? null) : null;
                } catch {
                    row = null;
                }
                if (stale()) return;
                if (!row) {
                    notify({name: 'tx.form.open.failed', detail: {id}, toast: {variant: 'error', message: $t('transactions.form.openFailed')}});
                    return;
                }
                txStoreAddExtras([row]);
            }
            if (stale()) return;
            joinBaseline(addSavedRows([id]));
        }
        const target = findSavedRow(id);
        if (!target) return;
        if (target.chargeOf !== undefined && isUnderParent(target, ops)) openGroup(target.chargeOf);
        handleEditRowClick(target, fromTxId);
    }

    /** The row on screen of the saved transaction `txId`: its own, or the visible half of its pair. */
    function findSavedRow(txId: number): PendingOp | undefined {
        const op = ops.find((d) => d.op === 'edit' && d.txId === txId && !d.inaccessible);
        if (!op?.pairedWith) return op;
        return ops.find((d) => d.tempId === op.pairedWith);
    }

    /** 66 F7-d (§22.4): rows added by navigation join the close guard's baseline, adopted as in the rows, so an editor
     *  nobody changed is still unchanged. */
    function joinBaseline(added: readonly PendingOp[]) {
        if (added.length === 0) return;
        const addedIds = new Set(added.map((d) => d.tempId));
        const current = ops.filter((d) => addedIds.has(d.tempId) || (d.pairedWith !== undefined && addedIds.has(d.pairedWith)));
        baselineOps = adoptCharges([...baselineOps, ...($state.snapshot(current) as PendingOp[])], txStoreGet);
        initialOpsKey = serializeOps(baselineOps);
    }

    // -------------------------------------------------------------------------
    // 66 F7-c1 (§14.2): the linked charges of a saved parent, read when it enters the Bulk
    // -------------------------------------------------------------------------

    /** How many parents one read asks for (`GET /transactions?parent_ids=…`): the query string stays short. */
    const CHARGES_READ_BATCH = 100;
    /** Bumped on every open, reset and «Reset all»: an answer of an older generation changes nothing. */
    let chargesLoadGeneration = 0;
    /** The read in flight for each parent (by `txId`), so the Form of a parent waits for it instead of asking again. */
    const chargesReads = new Map<number, Promise<boolean>>();

    /** Whether the Bulk lacks some saved charge of this saved parent: fewer owned rows saved under it than its count. */
    function parentChargesMissing(row: PendingOp): boolean {
        if (row.op !== 'edit' || row.pairedWith || row.inaccessible) return false;
        const count = txStoreGet(row.txId)?.charges_count ?? 0;
        if (count <= 0 || getTypeRule(row.fields.type).chargeRole !== 'parent') return false;
        const held = ops.filter((d) => d.op === 'edit' && d.chargeOf === row.tempId && txStoreGet(d.txId)?.parent_transaction_id === row.txId).length;
        return held < count;
    }

    /** A new generation: every read in flight is dropped. Returns the parents (by `txId`) that were waiting, so the
     *  caller can ask for them again. */
    function restartChargesLoad(): Set<number> {
        const waiting = new Set(chargesInFlight);
        chargesLoadGeneration++;
        chargesReads.clear();
        chargesInFlight = new Set();
        chargesReadFailed = new Set();
        return waiting;
    }

    /** Read the charges of the saved parents among `rows` that the Bulk does not hold all of (and is not reading). */
    function loadMissingCharges(rows: readonly PendingOp[], extraTxIds: ReadonlySet<number> = new Set()) {
        const wanted = new Set<number>();
        for (const row of rows) {
            const current = ops.find((d) => d.tempId === row.tempId) ?? (row.op === 'edit' ? ops.find((d) => d.op === 'edit' && d.txId === row.txId && !d.pairedWith) : undefined);
            if (current?.op === 'edit' && parentChargesMissing(current)) wanted.add(current.txId);
        }
        for (const txId of extraTxIds) {
            const current = ops.find((d) => d.op === 'edit' && d.txId === txId && !d.pairedWith);
            if (current && parentChargesMissing(current)) wanted.add(txId);
        }
        const ids = [...wanted].filter((id) => !chargesInFlight.has(id));
        for (let at = 0; at < ids.length; at += CHARGES_READ_BATCH) void readParentCharges(ids.slice(at, at + CHARGES_READ_BATCH));
    }

    /** One read of the charges of these saved parents. True when they landed; false when the read failed or its answer
     *  belongs to an older generation (dropped). A failure raises an error toast and leaves «del» off on them. */
    function readParentCharges(parentIds: number[]): Promise<boolean> {
        const generation = chargesLoadGeneration;
        chargesInFlight = new Set([...chargesInFlight, ...parentIds]);
        const failedBefore = chargesReadFailed;
        if (parentIds.some((id) => failedBefore.has(id))) chargesReadFailed = new Set([...failedBefore].filter((id) => !parentIds.includes(id)));
        const read = (async (): Promise<boolean> => {
            let rows: TXReadItem[] | null = null;
            try {
                const answer = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {parent_ids: parentIds}} as never)) as unknown;
                if (Array.isArray(answer)) rows = (answer as TXReadItem[]).filter((charge) => charge.parent_transaction_id != null && parentIds.includes(charge.parent_transaction_id));
            } catch {
                rows = null;
            }
            // An answer for an editor closed, reopened or reset meanwhile changes nothing.
            if (generation !== chargesLoadGeneration || !open) return false;
            chargesInFlight = new Set([...chargesInFlight].filter((id) => !parentIds.includes(id)));
            for (const id of parentIds) chargesReads.delete(id);
            if (rows === null) {
                chargesReadFailed = new Set([...chargesReadFailed, ...parentIds]);
                notify({name: 'tx.bulk.charges.read-failed', detail: {parentIds}, toast: {variant: 'error', message: $t('transactions.bulk.chargesReadFailed', {values: {ids: shortIdList(parentIds)}})}});
                return false;
            }
            addLoadedCharges(rows);
            return true;
        })();
        for (const id of parentIds) chargesReads.set(id, read);
        return read;
    }

    /** 66 F7-c1: a toast names at most three parents (`#1, #2, #3 +4`): a read may cover up to 100. */
    function shortIdList(ids: readonly number[]): string {
        const shown = ids
            .slice(0, 3)
            .map((id) => `#${id}`)
            .join(', ');
        return ids.length > 3 ? `${shown} +${ids.length - 3}` : shown;
    }

    /**
     * The charges read join as unchanged edit rows (`loadedWithParent`), adopted by their parent; under a parent already
     * «del» they are unlinked (§15.1, the F7-b interim), and the group opens. The close guard's baseline takes them too
     * (§14.2), when it holds their parent: an editor nobody changed is still unchanged.
     */
    function addLoadedCharges(rows: TXReadItem[]) {
        txStoreAddExtras(rows);
        const present = new Set(ops.map((d) => opTxId(d)).filter((id): id is number => id != null));
        const fresh = rows.filter((charge, at) => !present.has(charge.id) && rows.findIndex((other) => other.id === charge.id) === at && txStoreGet(charge.id));
        if (fresh.length === 0) return;
        const added = fresh.map((charge) => editOpFromTx(charge.id, {loadedWithParent: true}));
        ops = withLoadedCharges(ops, added);
        const opened = ops.filter((d) => d.loadedWithParent && d.chargeOf !== undefined && added.some((a) => a.tempId === d.tempId) && ops.some((p) => p.tempId === d.chargeOf && p.op === 'edit' && p.markedDelete)).map((d) => d.chargeOf!);
        if (opened.length > 0) expandedParents = new Set([...expandedParents, ...opened]);
        const baseHeld = new Set(baselineOps.map((d) => opTxId(d)).filter((id): id is number => id != null));
        const forBaseline = added.filter((op) => {
            const parentId = txStoreGet(op.op === 'edit' ? op.txId : 0)?.parent_transaction_id;
            return op.op === 'edit' && !baseHeld.has(op.txId) && parentId != null && baseHeld.has(parentId);
        });
        if (forBaseline.length > 0) {
            baselineOps = withLoadedCharges(baselineOps, $state.snapshot(forBaseline) as PendingOp[]);
            initialOpsKey = serializeOps(baselineOps);
        }
    }

    /** `rows` with these charges read added, adopted by their parent, unlinked under a parent already «del» (§15.1). */
    function withLoadedCharges(rows: PendingOp[], added: PendingOp[]): PendingOp[] {
        const addedIds = new Set(added.map((op) => op.tempId));
        const next = adoptCharges([...rows, ...added], txStoreGet);
        return next.map((op) => {
            if (!addedIds.has(op.tempId) || op.chargeOf === undefined) return op;
            const owner = next.find((p) => p.tempId === op.chargeOf);
            return owner?.op === 'edit' && owner.markedDelete ? {...unlinkCharge(op, next, txStoreGet), byParentChoice: true} : op;
        });
    }

    /**
     * 66 F7-b (§10, §11.6): before the Form of a saved parent opens, the Bulk holds every charge of it, so the Form never
     * reads them on its own. The entry load normally has them already; a read still in flight is awaited, otherwise
     * (a read that failed) the charges are read again. True when the charges are in the Bulk, false when the read failed.
     */
    async function ensureParentCharges(tempId: string): Promise<boolean> {
        const row = ops.find((d) => d.tempId === tempId);
        if (!row || row.op !== 'edit' || !parentChargesMissing(row)) return true;
        return (await (chargesReads.get(row.txId) ?? readParentCharges([row.txId]))) || !parentChargesMissingByTxId(row.txId);
    }

    /** Whether the parent saved as `txId`, as the Bulk holds it now, still lacks some of its charges. */
    function parentChargesMissingByTxId(txId: number): boolean {
        const current = ops.find((d) => d.op === 'edit' && d.txId === txId && !d.pairedWith);
        return current ? parentChargesMissing(current) : false;
    }

    function openEditRowForm(row: PendingOp, highlightTxId: number | null = null) {
        const request = ++chargesReadRequest;
        const current = ops.find((d) => d.tempId === row.tempId);
        if (!current || !parentChargesMissing(current)) {
            showRowForm(row.tempId, true, highlightTxId);
            return;
        }
        void ensureParentCharges(row.tempId).then((ok) => {
            if (request !== chargesReadRequest || !open) return;
            showRowForm(row.tempId, ok, highlightTxId);
        });
    }

    function showRowForm(tempId: string, chargesEditable: boolean, highlightTxId: number | null = null) {
        const row = ops.find((d) => d.tempId === tempId);
        if (!row) return;
        formHighlightTxId = highlightTxId;
        // When editing a 'new' draft, open in create mode so type stays editable;
        // formEditingTempId is still set so handleFormPushed patches (not adds).
        formMode = deriveStatus(row) === 'new' ? 'create' : 'edit';
        formEditingTempId = row.tempId;
        // Project post-split type before validatePair: handleSplitRow already
        // un-paired split tails, so the mismatch must stop txStore fallback from
        // re-pairing them as the original transfer.
        const items = resolveFormItemsFromOps(row, ops, opToTxLikeForForm, txStoreGet);
        // 66 F7-b (§11.6): the parent's charges always handed over, `[]` too, so the Form in the Bulk never reads them.
        formItems = items && items.length === 1 ? [{...items[0], _charges: chargeDraftsFor(row, ops, txStoreGet)} as TXReadItem] : items;
        formChargeEdits = chargesEditable;
        formKey++;
        formOpen = true;
    }

    /** 66 F7-b: what the Form hands back about the linked charges, onto the operations (`bulkCharges.ts`). */
    function applyChargePayload(tempId: string, payload: Record<string, unknown>, openedOnItself: boolean) {
        let target = ops.find((d) => d.tempId === tempId);
        if (!target) return;
        // §11.4: a create that followed its parent, opened and applied on its own, keeps the values it now shows.
        if (openedOnItself && target.followsParent) {
            const next = {...target};
            delete next.followsParent;
            ops = ops.map((d) => (d.tempId === tempId ? next : d));
            target = next;
        }
        if (Array.isArray(payload._charges)) {
            const deps = {
                get: txStoreGet,
                editOpFromTx: (id: number) => (txStoreGet(id) ? editOpFromTx(id) : null),
                newChargeOp: (draft: ChargeDraft, parent: PendingOp): PendingOp => ({
                    op: 'create',
                    tempId: generateUUID(),
                    createdSeq: nextCreatedSeq(),
                    fields: {
                        broker_id: parent.fields.broker_id,
                        asset_id: parent.fields.asset_id,
                        type: draft.type,
                        date: parent.fields.date,
                        quantity: '0',
                        cash: draft.cash ? {code: draft.cash.code, amount: draft.cash.amount} : null,
                        tags: [],
                        description: draft.description,
                        asset_event_id: null,
                        cost_basis_override: null,
                        cost_basis_mode: null,
                    },
                    link_uuid: null,
                }),
            };
            const parentTempId = target.tempId;
            const underBefore = new Set(chargesUnder.get(parentTempId)?.map((o) => o.tempId) ?? []);
            ops = adoptCharges(applyChargeDrafts(target, ops, payload._charges as ChargeDraft[], deps), txStoreGet);
            // 66 F7-c1 (§14.7, §15.6): a charge created or linked in the parent's Form opens the group (the user brought
            // it); a value changed on a charge already under it does not (§15.7).
            if (ops.some((o) => o.chargeOf === parentTempId && !underBefore.has(o.tempId) && isUnderParent(o, ops))) openGroup(parentTempId);
        }
        if (payload._parent_unlink === true) {
            // §11.7: the charge keeps its owner (`chargeOf`); only the link goes. 66 C22c: a link made only here is dropped
            // instead (`unlinkCharge`), the charge back as before it.
            const before = ops;
            ops = ops.map((d) => (d.tempId === tempId ? unlinkCharge(d, before, txStoreGet) : d));
        }
        if (typeof payload._parent_link === 'number') {
            const parentId = payload._parent_link;
            const owner = ops.find((d) => d.op === 'edit' && d.txId === parentId);
            // 66 C22 (path 3): the Form's picker reads the database, where a row merged in this Bulk is not a pair yet; a leg
            // is no parent (rule 8), so the link is refused and the charge keeps its own state. Its other values apply.
            if (owner && isPairLeg(owner, ops)) {
                notify({
                    name: 'tx.bulk.charge.link.refused.paired',
                    detail: {chargeTempId: tempId, parentTempId: owner.tempId, parentTxId: parentId},
                    toast: {variant: 'warning', message: $t('transactions.chargesLink.reason.paired', {values: {type: $t(`transactions.types.${owner.fields.type}`) || owner.fields.type, ref: bulkRowRef(owner)}})},
                });
                return;
            }
            ops = ops.map((d) => {
                if (d.tempId !== tempId) return d;
                const next = {...d};
                delete next.parentUnlink;
                if (owner) {
                    delete next.parentLinkId;
                    next.chargeOf = owner.tempId;
                    // 66 F7-c1: linked from its own Form to a parent of the Bulk, the charge goes under it: the group
                    // opens, or the row the user just applied would vanish from the grid.
                    openGroup(owner.tempId);
                } else {
                    delete next.chargeOf;
                    next.parentLinkId = parentId;
                }
                return next;
            });
        }
    }

    function handleFormPushed(payload: Record<string, unknown>) {
        const isDual = payload._dual === true;
        let pushedTempId: string | null = formEditingTempId;
        // 66 TL-3b: the row's broker and asset as shown before this «Apply», to tell what changed (`syncNewGroup`).
        const editedBefore = formEditingTempId != null && !isDual ? ops.find((d) => d.tempId === formEditingTempId) : undefined;
        const before = editedBefore ? followedFields(editedBefore) : undefined;
        if (formEditingTempId != null) {
            // Patching an existing draft row
            if (isDual) {
                patchDualRowFromForm(formEditingTempId, payload);
            } else {
                // §11.4: a create that followed its parent, applied in its own form, keeps what that form gives it. The flag
                // goes before the patch, or `syncFollowers` would write the parent's broker, asset and date back over it.
                if (editedBefore?.followsParent) {
                    const own = {...editedBefore};
                    delete own.followsParent;
                    ops = ops.map((d) => (d.tempId === own.tempId ? own : d));
                }
                patchRowFromForm(formEditingTempId, payload);
            }
        } else {
            // Adding a new draft row
            if (isDual) {
                addDualRowFromForm(payload);
            } else {
                pushedTempId = addRowFromForm(payload);
            }
        }
        if (!isDual && pushedTempId != null) applyChargePayload(pushedTempId, payload, formEditingTempId != null);
        // 66 TL-3b (P-30): in an all-new group, the broker or asset changed on one row moves onto the others, both ways.
        if (before && pushedTempId != null) ops = syncNewGroup(ops, pushedTempId, {broker_id: before.broker_id, asset_id: before.asset_id}, {effective: (d) => followedFields(d), assetAllowed: (type) => getTypeRule(type as TransactionTypeCode).assetField !== 'forbidden'});
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
            // Auto-clear todos whose field has now been filled
            if (merged.todos?.length) {
                merged.todos = remainingTodos(merged.todos, merged.fields);
                if (merged.todos.length === 0) delete merged.todos;
            }
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
                else if (payload._wac_currency_hint === null) delete merged.wacCurrencyHint; // absent, as a row starts (W-B65)
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
        const highlight = highlightedIssueIds.has(row.tempId) ? 'highlighted ' : '';
        if (row.todos?.some((t) => t.severity === 'blocker')) return `${highlight}row-todo-blocker`;
        const st = deriveStatus(row);
        if (st === 'delete') return `${highlight}row-deleted`;
        if (st === 'new') return `${highlight}row-appended`;
        if (st === 'edited') return `${highlight}row-edited`;
        return highlight;
    }

    /** A row the selection's «Reset» acts on: changed or marked for deletion, or half of a split or a merge still waiting
     *  for the save — `resetRows` undoes those too, and a row in a pending split can read «original» (77 SEL-E). */
    function hasPendingChange(row: PendingOp): boolean {
        const status = deriveStatus(row);
        if (status === 'edited' || status === 'delete') return true;
        if (row.op === 'edit' && pendingSplits.some((s) => s.id_a === row.txId || s.id_b === row.txId)) return true;
        if (row.op === 'edit') return pendingPromotes.some((p) => p.id_a === row.txId || p.id_b === row.txId);
        return !!row.link_uuid && pendingPromotes.some((p) => p.link_uuid_a === row.link_uuid || p.link_uuid_b === row.link_uuid);
    }

    /** The body that scrolls, which holds the table and its selection panel. */
    let bulkBodyEl: HTMLElement | undefined = $state();

    // The Bulk guide's «selection» step points at the selection bar (77 SEL-E). The table's panel draws it, at the top of
    // the table or, once scrolled away, in the balloon at the bottom — another element: the anchor follows whichever is on
    // screen while rows are ticked.
    $effect(() => {
        const body = bulkBodyEl;
        if (!body || bulkTableSelectedRows.length === 0) return;
        let current: HTMLElement | null = null;
        let unregister: (() => void) | null = null;
        const follow = () => {
            const bar = body.querySelector<HTMLElement>('[data-testid="selection-toolbar"]');
            if (bar === current) return;
            unregister?.();
            current = bar;
            unregister = bar ? guideAnchors.register('transaction.bulk.selection', bar) : null;
        };
        // The registry is reactive: registering inside the effect would make the effect depend on it
        untrack(follow);
        const observer = new MutationObserver(follow);
        observer.observe(body, {childList: true, subtree: true});
        return () => {
            observer.disconnect();
            unregister?.();
        };
    });

    /**
     * The selection's actions on the table's panel (77 SEL-E): the bar at the top of the table, the balloon when it scrolls
     * away, each with the number of rows it takes. Hidden where it makes no sense, off with its reason where it is blocked.
     * The test ids stay the Bulk's own.
     */
    let bulkActionsForTable = $derived.by((): BulkAction<PendingOp>[] => [
        {
            id: 'reset-selected',
            testid: 'tx-bulk-reset-selected',
            icon: Undo2,
            label: () => $t('transactions.bulk.resetSelected') || 'Reset selected',
            appliesTo: (row) => hasPendingChange(row),
            // Offered, as before, only when a ticked row is changed or marked for deletion (66 C22b: no reset on a row that
            // reads `original`); then it takes every row the reset undoes something on, and counts them
            pointless: (rows) => !rows.some((row) => ['edited', 'delete'].includes(deriveStatus(row))),
            onClick: (rows) => resetRows(rows.map((row) => row.tempId)),
        },
        {
            id: 'link-charges',
            testid: 'tx-bulk-link-charges',
            icon: Link2,
            label: () => $t('transactions.chargesLink.action') || 'Link the charges',
            shortLabel: () => $t('transactions.chargesLink.actionShort') || 'Link',
            pointless: () => bulkLinkState.kind === 'hidden',
            blocked: () => (bulkLinkState.kind === 'disabled' ? {hint: () => bulkLinkHint, reason: bulkLinkState.reason} : null),
            onClick: () => openLinkPanel(),
        },
        {
            // 66 TL-4 (P-2 = C): the ticked charges still linked under their parent, unlinked as «Scollega» in their Form
            // does; no panel (nothing is saved before «Save all»; «Reset» links back a saved charge); the selection empties.
            id: 'unlink-charges',
            testid: 'tx-bulk-unlink-charges',
            icon: Unlink,
            label: () => $t('transactions.bulk.unlinkSelected') || 'Unlink the charges',
            shortLabel: () => $t('transactions.form.charges.unlink') || 'Unlink',
            appliesTo: (row) => unlinkableCharges([row], ops).length > 0,
            pointless: (rows) => unlinkableCharges(rows, ops).length === 0,
            onClick: (rows) => unlinkSelectedRows(rows.map((row) => row.tempId)),
        },
        {
            id: 'delete-selected',
            testid: 'tx-bulk-delete-selected',
            icon: Trash2,
            label: () => $t('transactions.bulk.deleteSelected') || 'Delete selected',
            shortLabel: () => $t('common.delete') || 'Delete',
            variant: 'danger',
            onClick: (rows) =>
                void requestDelete(
                    rows.map((row) => row.tempId),
                    true,
                ),
        },
        {
            id: 'promote-pair',
            testid: 'promote-toolbar-confirm',
            icon: Link2,
            label: () => (selectedForPromote.kind === 'hidden' ? $t('transactions.actions.promotePair') : `${$t('transactions.actions.promotePair')}: ${selectedForPromote.targetLabel}`),
            shortLabel: () => (selectedForPromote.kind === 'hidden' ? $t('transactions.actions.promotePair') : selectedForPromote.targetLabel),
            minSelection: 2,
            pointless: () => selectedForPromote.kind === 'hidden',
            blocked: () => (selectedForPromote.kind === 'disabled' ? {hint: () => promoteHint, reason: selectedForPromote.reason} : null),
            onClick: () => handlePromoteSelected(),
        },
    ]);

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
            eventA: a.fields.asset_event_id ?? null,
            eventB: b.fields.asset_event_id ?? null,
        };
    }

    // cashAmountsCancel is imported from '$lib/features/transactions/bulk/promoteHelpers'
    // (extracted for unit-testability — see promoteHelpers.ts). It takes `getTypeRule`
    // because a cash amount cannot be compared without knowing the sign its type implies:
    // pool rows arrive signed, DB rows arrive normalised to a magnitude by fieldsFromTx.

    /** 66 C21: the rows that still hold linked charges (under them, or saved and not read yet): rule 6 refuses to promote
     *  them, so no offer takes them, on either side. A charge «unlink»ed or «del» does not count. */
    let chargeHolders = $derived(rowsWithLinkedCharges(ops, txStoreGet));
    function hasLinkedCharges(op: PendingOp): boolean {
        return chargeHolders.has(op.tempId);
    }

    /** Selection-based promote detection — 2 standalone rows with matching promote rule. 66 C22: a pair that only the
     *  linked charges of a leg forbid (rule 6) is offered off, with the reason; any other failure keeps it absent. */
    let selectedForPromote = $derived.by((): PromoteSelection => {
        const hidden: PromoteSelection = {kind: 'hidden'};
        if (bulkTableSelectedRows.length !== 2) return hidden;
        const [a, b] = bulkTableSelectedRows;
        // Both must be standalone (no hidden partner)
        if (getPartnerOp(a.tempId) || getPartnerOp(b.tempId)) return hidden;
        // Check markedDelete
        if ((a.op === 'edit' && a.markedDelete) || (b.op === 'edit' && b.markedDelete)) return hidden;
        const match = findPromoteMatch(a.fields.type, b.fields.type, $t, buildPromoteCtx(a, b));
        if (!match) return hidden;
        // For CASH_TRANSFER: require exact cash cancel (same currency, opposite sign).
        // For TRANSFER: the same asset by exactly opposite quantities, compared as decimals like
        // the banner and the backend do (findPromoteMatch compares JavaScript numbers).
        // For FX_CONVERSION: amounts are in different currencies — no cancel check.
        if (match.targetType === 'CASH_TRANSFER' && !cashAmountsCancel(a, b, getTypeRule)) return hidden;
        if (match.targetType === 'TRANSFER' && !assetQuantitiesCancel(a, b, getTypeRule)) return hidden;
        // 66 C22: the one place the off state is born (to drop it, return `hidden` here).
        const holder = [a, b].find(hasLinkedCharges);
        if (holder) return {kind: 'disabled', reason: 'hasCharges', holder, targetLabel: match.targetLabel};
        return {...match, kind: 'ok', opA: a, opB: b};
    });

    /** 66 C22: why the merge button is off — the leg that still holds linked charges. */
    let promoteHint = $derived(selectedForPromote.kind === 'disabled' ? $t('transactions.promote.chargesBlock', {values: {type: $t(`transactions.types.${selectedForPromote.holder.fields.type}`) || selectedForPromote.holder.fields.type, ref: bulkRowRef(selectedForPromote.holder)}}) : '');

    /** Handle promote of 2 selected rows. */
    function handlePromoteSelected() {
        if (selectedForPromote.kind !== 'ok') return;
        const {opA, opB, targetLabel} = selectedForPromote;
        // Check if fields diverge (only description + tags — date/cost_basis handled in FormModal)
        const descA = opA.fields.description,
            descB = opB.fields.description;
        const tagsA = opA.fields.tags,
            tagsB = opB.fields.tags;
        const diverges = promoteNotesDiverge(opA.fields, opB.fields);
        if (diverges) {
            const labelA = opA.op === 'edit' ? `#${(opA as any).txId}` : opA.tempId.slice(0, 6);
            const labelB = opB.op === 'edit' ? `#${(opB as any).txId}` : opB.tempId.slice(0, 6);
            promoteMergeData = {
                txA: {label: labelA, description: descA, tags: tagsA, date: opA.fields.date},
                txB: {label: labelB, description: descB, tags: tagsB, date: opB.fields.date},
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
        // 66 C21: a defence — the offers already leave such rows out; a charge can still land while the merge dialog is open.
        const holder = [opA, opB].find(hasLinkedCharges);
        if (holder) {
            notify({
                name: 'tx.bulk.promote.refused.charges',
                detail: {tempId: holder.tempId, txId: opTxId(holder) ?? null},
                toast: {variant: 'error', message: $t('transactions.promote.chargesBlock', {values: {type: $t(`transactions.types.${holder.fields.type}`) || holder.fields.type, ref: bulkRowRef(holder)}})},
            });
            return;
        }

        // Apply resolved fields (from MergeModal) to *both* ops before collapsing.
        //
        // Not just opA, for two reasons. The create+create branch below is purely
        // local — it assigns a shared link_uuid and sends no `resolved_fields`, so
        // nothing else would ever reach opB and the commit is rejected with
        // `pairDescriptionMismatch`, quoting a description the user never chose.
        // And `collapseIntoPaired` picks the displayed row by cash sign, so opB can
        // become the *visible* one: resolving into opA alone can hide the chosen
        // value as well as fail on it.
        //
        // For the edit+edit and mixed branches the backend applies `resolved_fields`
        // to both sides anyway, so writing them here is idempotent — and it keeps
        // the grid showing what will actually be persisted.
        for (const op of [opA, opB]) {
            if (resolved.description != null) op.fields.description = resolved.description as string;
            if (resolved.tags != null) op.fields.tags = resolved.tags as string[];
            if (resolved.date != null) op.fields.date = resolved.date as string;
            if (resolved.cost_basis_override != null) op.fields.cost_basis_override = resolved.cost_basis_override as any;
        }

        // The editor shows a magnitude and lets the type carry the sign (fieldsFromTx, txCreateItemToPendingOp, the
        // form). The target type is free-sign (CASH_TRANSFER, FX_CONVERSION), so in every branch the sign moves into the
        // amount before the type changes, or the pair is shown, ordered and split as if the withdrawal were a deposit
        // (J-67). The save is unchanged: a promoted saved row is not sent as an update, and a new row's create signs by
        // its source type (`promoteFromType`), on which applySign is idempotent.
        for (const op of [opA, opB]) {
            const {signedQty, signedCash} = applySignRules(op.fields.quantity, op.fields.cash, getTypeRule(op.fields.type));
            op.fields.quantity = signedQty;
            op.fields.cash = signedCash;
        }

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
            for (const op of [opA, opB]) {
                op.link_uuid = sharedUuid;
                op.fields.type = match.targetType as TransactionTypeCode;
            }
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
            // The backend derives the target from the two *source* types, so the new
            // row has to reach it un-promoted; the grid still shows the target below.
            newOp.promoteFromType = newOp.fields.type as TransactionTypeCode;
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

    /** The id a row is asked under in promote-suggest: its transaction id when saved, a negative id when new. */
    function suggestKeyOf(op: PendingOp): number {
        return op.op === 'edit' ? ((op as any).txId as number) : newRowSuggestId(op.createdSeq);
    }

    /**
     * The rows the database search is asked about: standalone saved rows not marked for deletion, and
     * new rows not linked to anything that can be compared (type, broker, date, and an amount or a
     * quantity: without them the backend skips the "opposite amounts" check and every deposit or
     * withdrawal of the window would come back). A new row's other side may already be saved — the
     * overnight account imported a month after the broker account.
     */
    function isSuggestable(op: PendingOp): boolean {
        if (op.pairedWith || getPartnerOp(op.tempId)) return false;
        if (hasLinkedCharges(op)) return false; // 66 C21
        if (op.op === 'edit') return !(op as any).markedDelete;
        const measured = Number(op.fields.cash?.amount ?? 0) !== 0 || Number(op.fields.quantity ?? 0) !== 0;
        return !op.link_uuid && !!op.fields.type && Number(op.fields.broker_id) > 0 && !!op.fields.date && measured;
    }

    /** Reactive effect: when ops change, debounce-call promote-suggest API for
     *  standalone rows, saved and new. */
    $effect(() => {
        if (!open) return;
        const asked = ops.filter(isSuggestable);
        if (asked.length === 0) {
            untrack(() => {
                suggestAskedKey = '';
                if (suggestTimer) {
                    clearTimeout(suggestTimer);
                    suggestTimer = null;
                }
                suggestFromDB = new Map();
            });
            return;
        }
        const inputs = asked.map((o) => {
            const rule = getTypeRule(o.fields.type);
            const {signedQty, signedCash} = applySignRules(o.fields.quantity, o.fields.cash, rule);
            return {
                id: suggestKeyOf(o),
                type: o.fields.type,
                broker_id: o.fields.broker_id,
                date: o.fields.date,
                currency: signedCash?.code ?? null,
                asset_id: o.fields.asset_id,
                amount: Number(signedCash?.amount ?? 0) || null,
                quantity: Number(signedQty ?? 0) || null,
                asset_event_id: o.fields.asset_event_id ?? null,
            };
        });
        // The window is part of the search: moving the Max Δ days slider asks again.
        const toleranceDays = maxDeltaDays;
        const key = JSON.stringify({inputs, toleranceDays});
        untrack(() => {
            suggestAskedKey = key;
            if (key === lastSuggestKey) return;
            if (suggestTimer) clearTimeout(suggestTimer);
            suggestTimer = setTimeout(async () => {
                try {
                    const resp = await zodiosApi.promote_suggest_api_v1_transactions_promote_suggest_post(inputs as never, {queries: {tolerance_days: toleranceDays}});
                    // The rows changed while the request was out (a promote, an edit): this answer is stale.
                    if (key !== suggestAskedKey) return;
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

    $effect(() => {
        if (!importWizardOpen) return;
        importGuideBulkReady = false;
        importGuideBulkProgress = undefined;
    });

    $effect(() => {
        const isOpen = open;
        if (isOpen && onboardingGuide.active?.flow === 'import_guide' && onboardingGuide.active.stepId === 'import.bulk') {
            guideBulkObservedOpen = true;
            return;
        }
        if (!isOpen && guideBulkObservedOpen && onboardingGuide.active?.flow === 'import_guide' && onboardingGuide.active.stepId === 'import.bulk') {
            onboardingGuide.dismissHost({restartAtFirst: true});
        }
        if (!isOpen) guideBulkObservedOpen = false;
    });

    $effect(() => {
        const isOpen = open;
        const nestedOpen = formOpen || importWizardOpen || pickerOpen || suggestPickerOpen || promoteMergeOpen;
        const validationReady = scheduler.state.validateRuns > 0 && !scheduler.state.isPending && !scheduler.state.isValidating;
        const selectionReady = bulkTableSelectedRows.length > 0;
        const saveReady = visibleOps.length > 0 && !commitDisabled;
        if (!isOpen) {
            if (onboardingGuide.active?.flow === 'transaction_bulk_guide') {
                onboardingGuide.dismissHost({restartAtFirst: true});
            }
            onboardingGuide.clearQueued('transaction_bulk_guide');
            nestedGuideHostObserved = false;
            bulkGuideAttemptedForOpen = new Set();
            bulkValidationObserved = false;
            bulkSelectionObserved = false;
            bulkSaveObserved = false;
            importGuideBulkReady = false;
            importGuideBulkProgress = undefined;
            return;
        }
        if (validationReady) bulkValidationObserved = true;
        if (selectionReady) bulkSelectionObserved = true;
        if (saveReady) bulkSaveObserved = true;
        if (nestedOpen) {
            nestedGuideHostObserved = true;
            return;
        }
        const bridgeIntent = intent?.action === 'create' || intent?.action === 'import';
        const overviewReady = !bridgeIntent || nestedGuideHostObserved;
        if (!onboardingGuide.active && importGuideBulkReady) {
            const started = onboardingGuide.startImportAt('import.bulk', importGuideBulkProgress);
            importGuideBulkReady = false;
            importGuideBulkProgress = undefined;
            if (started) return;
        }
        const availability: Record<TransactionBulkStepId, boolean> = {
            'transaction.bulk.workspace': overviewReady,
            'transaction.bulk.validation': bulkValidationObserved && validationReady,
            'transaction.bulk.selection': bulkSelectionObserved && selectionReady,
            'transaction.bulk.save': bulkSaveObserved && saveReady,
        };
        for (const stepId of TRANSACTION_BULK_STEP_IDS) {
            if (availability[stepId] && !bulkGuideAttemptedForOpen.has(stepId)) {
                onboardingGuide.queueContextual('transaction_bulk_guide', stepId);
            } else if (!availability[stepId] && !(onboardingGuide.active?.flow === 'transaction_bulk_guide' && onboardingGuide.active.stepId === stepId)) {
                onboardingGuide.clearQueued('transaction_bulk_guide', stepId);
            }
        }
        const activeFlow = onboardingGuide.active?.flow;
        const activeStep = onboardingGuide.active?.stepId;
        if (activeFlow === 'transaction_bulk_guide' && activeStep === 'transaction.bulk.selection' && !selectionReady) {
            onboardingGuide.dismissHost({restartAtFirst: true});
            bulkGuideAttemptedForOpen.delete('transaction.bulk.selection');
            return;
        }
        if (activeFlow === 'transaction_bulk_guide' && activeStep === 'transaction.bulk.save' && !saveReady) {
            onboardingGuide.dismissHost({restartAtFirst: true});
            bulkGuideAttemptedForOpen.delete('transaction.bulk.save');
            return;
        }
        if (onboardingGuide.active) return;
        for (const stepId of TRANSACTION_BULK_STEP_IDS) {
            if (!availability[stepId] || !onboardingGuide.queuedGuides.some((queued) => queued.flow === 'transaction_bulk_guide' && queued.stepId === stepId)) continue;
            onboardingGuide.maybeStartQueued('transaction_bulk_guide', stepId);
            bulkGuideAttemptedForOpen.add(stepId);
            break;
        }
    });

    /** Local promote suggestions: match new standalone ops against each other. */
    let localSuggestions = $derived.by(() => {
        const newStandalone = ops.filter((o) => o.op === 'create' && !o.pairedWith && !getPartnerOp(o.tempId) && !o.link_uuid && !hasLinkedCharges(o));
        const results: SuggestEntry[] = [];
        for (let i = 0; i < newStandalone.length; i++) {
            for (let j = i + 1; j < newStandalone.length; j++) {
                const dA = newStandalone[i].fields.date;
                const dB = newStandalone[j].fields.date;
                const delta = daysDiff(dA, dB);
                if (delta > maxDeltaDays) continue;
                const match = findPromoteMatch(newStandalone[i].fields.type, newStandalone[j].fields.type, $t, buildPromoteCtx(newStandalone[i], newStandalone[j]));
                if (match && (match.targetType !== 'CASH_TRANSFER' || cashAmountsCancel(newStandalone[i], newStandalone[j], getTypeRule)) && (match.targetType !== 'TRANSFER' || assetQuantitiesCancel(newStandalone[i], newStandalone[j], getTypeRule))) {
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

    /** Banner suggestions: only pairs where BOTH TX are already in ops[] (local↔local or local↔imported-DB) */
    let bannerSuggestions = $derived.by(() => {
        const combined: SuggestEntry[] = [];
        // Local new+new (both in ops by definition)
        for (const s of localSuggestions) combined.push(s);

        // Local edit+edit: match standalone edit ops against each other (works even after suggestFromDB is refreshed)
        const editStandalone = ops.filter((o) => o.op === 'edit' && !o.pairedWith && !getPartnerOp(o.tempId) && !(o as any).markedDelete && !hasLinkedCharges(o));
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
                // CASH_TRANSFER: amounts must cancel. TRANSFER: same asset, quantities must cancel. FX_CONVERSION: different currencies, no cancel check.
                if (match.targetType === 'CASH_TRANSFER' && !cashAmountsCancel(a, b, getTypeRule)) continue;
                if (match.targetType === 'TRANSFER' && !assetQuantitiesCancel(a, b, getTypeRule)) continue;
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

        // New + saved: a side imported now whose other side was saved earlier, both in the editor.
        // The mixed branch of executePromote links the saved id to the new row's link_uuid.
        const newStandalone = ops.filter((o) => o.op === 'create' && !o.pairedWith && !getPartnerOp(o.tempId) && !o.link_uuid && !hasLinkedCharges(o));
        const mixed = mixedPromotePairs(newStandalone, editStandalone, {
            keyOf: (o) => o.tempId,
            daysBetween: (a, b) => daysDiff(a.fields.date, b.fields.date),
            maxDeltaDays,
            match: (a, b) => {
                const match = findPromoteMatch(a.fields.type, b.fields.type, $t, buildPromoteCtx(a, b));
                if (!match) return null;
                if (match.targetType === 'CASH_TRANSFER' && !cashAmountsCancel(a, b, getTypeRule)) return null;
                if (match.targetType === 'TRANSFER' && !assetQuantitiesCancel(a, b, getTypeRule)) return null;
                return match.targetType;
            },
        });
        for (const pair of mixed) combined.push({tempIdA: pair.newTempId, tempIdB: pair.savedTempId, targetType: pair.targetType});

        return combined;
    });

    /** The pairs «Merge all» merges: the banner's, in its order, without a pair that shares a row with an earlier one. */
    let mergeAllPairs = $derived.by(() => {
        const used = new Set<string>();
        return bannerSuggestions.filter((sug) => {
            if (used.has(sug.tempIdA) || used.has(sug.tempIdB)) return false;
            used.add(sug.tempIdA);
            used.add(sug.tempIdB);
            return true;
        });
    });

    /**
     * Importable suggestions: DB candidates NOT yet in ops, for saved and new rows (for 💡 button).
     * Only rows that would still be asked count: a row merged meanwhile has no counterpart to import.
     */
    let importableSuggestions = $derived.by(() => {
        const opsEditIds = new Set(ops.filter((o) => o.op === 'edit').map((o) => (o as any).txId as number));
        const tempIdByKey = new Map(ops.filter(isSuggestable).map((o) => [suggestKeyOf(o), o.tempId]));
        return importableFromResults(
            suggestFromDB,
            (key) => tempIdByKey.get(key),
            opsEditIds,
            (id) => txStoreGet(id) != null,
        );
    });

    let suggestPickerIncludeIds = $derived(new Set(importableSuggestions.flatMap((s) => s.candidates.map((c) => c.id))));

    /** Suggestions the save gate asks about: the lightbulb's candidates until it is opened, the banner's pairs until it is touched. */
    let unseenSuggestionCount = $derived((suggestPickerSeen ? 0 : importableSuggestions.reduce((n, s) => n + s.candidates.length, 0)) + (promoteBannerSeen ? 0 : bannerSuggestions.length));

    /** «Show the suggestions» of the save gate: the lightbulb's picker if it was never opened, the banner otherwise. */
    function reviewSuggestions() {
        confirmSuggestionsOpen = false;
        if (!suggestPickerSeen && importableSuggestions.length > 0) {
            openSuggestPicker();
            return;
        }
        promoteBannerSeen = true;
        document.querySelector('[data-testid="promote-suggest-banner"]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
    }

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

            const {from: fromOp, to: toOp} = promotePairOrder(opA, opB, getTypeRule);
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

    /** The two rows of a suggestion; a saved counterpart joins the grid first when it is not there yet. Null when a row is gone. */
    function suggestionOps(sug: (typeof allSuggestions)[number]): {opA: PendingOp; opB: PendingOp} | null {
        const opA = ops.find((o) => o.tempId === sug.tempIdA);
        if (!opA) return null;
        if (!sug.isDB) {
            const opB = ops.find((o) => o.tempId === sug.tempIdB);
            return opB ? {opA, opB} : null;
        }
        if (!sug.dbCandidateId) return null;
        // DB suggestion: edit → DB candidate. Check if DB candidate is already in ops
        let opB = ops.find((o) => o.op === 'edit' && (o as any).txId === sug.dbCandidateId);
        if (!opB) {
            // Add DB candidate to ops via picker
            const tx = txStoreGet(sug.dbCandidateId);
            if (!tx) return null; // TX not in store — can't proceed
            opB = editOpFromTx(sug.dbCandidateId, {addedViaPicker: true});
            ops = [...ops, opB];
            // 66 F7-c1 (§14.2): a saved parent entering from a suggestion has its charges read, as from the picker.
            loadMissingCharges([opB]);
        }
        return {opA, opB};
    }

    /** Trigger promote from a suggestion line (auto-select both ops + invoke handler). */
    function triggerPromoteFromSuggestion(sug: (typeof allSuggestions)[number]) {
        // The banner's own order (`promotePairOrder`, read as the banner and «Merge all» read it, before `suggestionOps`
        // may add a saved candidate): the dialog lists first the row the banner lists first, so its first text is the
        // one «Merge all → All left» keeps (J-66). Only what the dialog shows follows it; the promote keeps opA and opB.
        const rawA = ops.find((o) => o.tempId === sug.tempIdA);
        const rawB = ops.find((o) => o.tempId === sug.tempIdB);
        const swapped = !!(rawA && rawB) && promotePairOrder(rawA, rawB, getTypeRule).swapped;
        const pair = suggestionOps(sug);
        if (!pair) return;
        const {opA, opB} = pair;
        // Directly execute promote (no need to simulate DataTable selection)
        const match = findPromoteMatch(opA.fields.type, opB.fields.type, $t, buildPromoteCtx(opA, opB));
        if (!match) return;
        // Check divergence
        const descA = opA.fields.description,
            descB = opB.fields.description;
        const tagsA = opA.fields.tags,
            tagsB = opB.fields.tags;
        const diverges = promoteNotesDiverge(opA.fields, opB.fields);
        if (diverges) {
            const [first, second] = swapped ? [opB, opA] : [opA, opB];
            const labelOf = (op: PendingOp) => (sug.isDB ? `#${(op as any).txId ?? ''} ${op.fields.type}` : op.fields.type);
            promoteMergeData = {
                txA: {label: labelOf(first), description: first.fields.description, tags: first.fields.tags, date: first.fields.date},
                txB: {label: labelOf(second), description: second.fields.description, tags: second.fields.tags, date: second.fields.date},
                targetTypeLabel: match.targetLabel,
                opA,
                opB,
            };
            promoteMergeOpen = true;
        } else {
            executePromote(opA, opB, {});
        }
    }

    /** A row already merged with another: a second suggestion on it must not promote it again. */
    function isPaired(op: PendingOp): boolean {
        return !!op.pairedWith || !!getPartnerOp(op.tempId);
    }

    /**
     * «Merge all» of the banner: every suggested pair at once. Where the two rows of a pair differ in
     * description or tags, one answer settles all of them: the left row's (the one the banner lists
     * first), the right row's, or both combined — PromoteMergeModal's default. A pair whose combined notes would pass
     * the description's limit is left unpromoted, for the merge dialog, and a notice counts them (W-B70).
     */
    function mergeAllSuggestions(strategy: PromoteAllStrategy) {
        promoteAllOpen = false;
        let leftForManualMerge = 0;
        for (const sug of [...mergeAllPairs]) {
            const rawA = ops.find((o) => o.tempId === sug.tempIdA);
            if (!rawA || isPaired(rawA)) continue;
            const rawB = ops.find((o) => o.tempId === sug.tempIdB);
            if (rawB && isPaired(rawB)) continue;
            // The banner's own order (`promotePairOrder`): the paying row first, the one «left» names.
            const swapped = !!rawB && promotePairOrder(rawA, rawB, getTypeRule).swapped;
            const pair = suggestionOps(sug);
            if (!pair || isPaired(pair.opB)) continue;
            const {opA, opB} = pair;
            if (!findPromoteMatch(opA.fields.type, opB.fields.type, $t, buildPromoteCtx(opA, opB))) continue;
            const [left, right] = swapped ? [opB, opA] : [opA, opB];
            const resolved = resolvePromoteAllFields(strategy, left.fields, right.fields);
            if (resolved === null) {
                leftForManualMerge += 1;
                continue;
            }
            executePromote(opA, opB, resolved);
        }
        if (leftForManualMerge > 0) {
            notify({
                name: 'tx.bulk.promote-all.left-for-manual-merge',
                detail: {pairs: leftForManualMerge},
                toast: {variant: 'warning', message: $t('transactions.promote.mergeAllLeftTooLong', {values: {count: leftForManualMerge, max: TX_DESCRIPTION_MAX_LENGTH}})},
            });
        }
    }

    /** 66 F7-c1: a charge under its parent never opens a page (`DataTable`'s `opensPage`, `paginateFlat`). */
    function opensGridPage(row: PendingOp): boolean {
        return !indentedIds.has(row.tempId);
    }

    /** 66 TL-4 (P-2 = C, was F7-c1 §13.5): every drawn row has its checkbox, a charge under its parent too — ticking the
     *  parent never ticks its charges, nor the reverse. Only the half a merge hides (`pairedWith`) is never selectable. */
    function isGridRowSelectable(row: PendingOp): boolean {
        return row.pairedWith === undefined;
    }

    // 66 C21: the half a merge hides (`pairedWith`) leaves the selection: «Reset selected» would reset it alone and break
    // the pair still waiting for the save. 66 TL-4: a selected row that goes under its parent (a «Restore», a link in the
    // parent's Form) keeps its tick (it was F7-c1 §14.6).
    let hiddenPairHalves = $derived(new Set(ops.filter((op) => op.pairedWith !== undefined).map((op) => op.tempId)));
    $effect(() => {
        const hidden = hiddenPairHalves;
        untrack(() => {
            for (const row of bulkTableSelectedRows) if (hidden.has(row.tempId)) tableRef?.toggleRowSelectionById(row.tempId);
        });
    });

    /**
     * 66 F7-c1: clicks the grid's HTML cells cannot handle themselves, caught in the capture phase before the row's own
     * handlers: the chip of a parent toggles its group and nothing else (no selection, no menu, no Form). A double-click
     * on an indented row reaches the table's own handler (66 TL-4: the row is selectable), so the Form opens once.
     */
    function captureChargeChip(node: HTMLElement) {
        const onClick = (ev: MouseEvent) => {
            const chip = (ev.target as HTMLElement | null)?.closest?.('[data-tx-bulk-charges-toggle]') as HTMLElement | null;
            if (!chip) return;
            ev.preventDefault();
            ev.stopPropagation();
            const parentTempId = chip.getAttribute('data-tx-bulk-charges-toggle');
            if (parentTempId) toggleGroup(parentTempId);
        };
        const onDblClick = (ev: MouseEvent) => {
            const target = ev.target as HTMLElement | null;
            if (target?.closest?.('[data-tx-bulk-charges-toggle]')) {
                ev.preventDefault();
                ev.stopPropagation();
            }
        };
        node.addEventListener('click', onClick, true);
        node.addEventListener('dblclick', onDblClick, true);
        return {
            destroy() {
                node.removeEventListener('click', onClick, true);
                node.removeEventListener('dblclick', onDblClick, true);
            },
        };
    }

    function handleBulkTableSelectionChange(selectedIds: string[]) {
        const idSet = new Set(selectedIds);
        bulkTableSelectedRows = ops.filter((d) => idSet.has(d.tempId));
    }

    // -------------------------------------------------------------------------
    // 66 F7-d (§20.5, §21.2, §22): U3, «Link» on the selection — one parent and its charges, saved with «Save all»
    // -------------------------------------------------------------------------

    /** What «Link» does with the selection, on the rows as they are now (`bulkLinkSelection`). */
    let bulkLinkState = $derived.by(() => {
        const selected = bulkTableSelectedRows.map((row) => ops.find((op) => op.tempId === row.tempId)).filter((op): op is PendingOp => op !== undefined);
        return bulkLinkSelection(selected, ops, txStoreGet, {roleOf: (type) => getTypeRule(type).chargeRole, canEdit: (brokerId) => canEditBroker(brokerId)}, (op) => postSplitType(op, pendingSplits));
    });
    /** Why «Link» is off, naming the row by its reference (`bulkRowRef`). */
    let bulkLinkHint = $derived(bulkLinkState.kind === 'disabled' ? $t(`transactions.chargesLink.reason.${bulkLinkState.reason}`, {values: {type: $t(`transactions.types.${bulkLinkState.params.type}`) || bulkLinkState.params.type, ref: bulkRowRef(bulkLinkState.params.op)}}) : '');
    /** The open panel of «Link»: the parent and the charges by `tempId`, and what the panel shows. */
    let linkPanel = $state<{parentId: string; chargeIds: string[]; parent: TXReadItem; charges: TXReadItem[]; parentRef: string; chargeRefs: string[]} | null>(null);

    function openLinkPanel() {
        const state = bulkLinkState;
        if (state.kind !== 'ok') return;
        linkPanel = {
            parentId: state.parent.tempId,
            chargeIds: state.charges.map((c) => c.tempId),
            parent: panelItem(state.parent),
            charges: state.charges.map((c) => panelItem(c)),
            parentRef: bulkRowRef(state.parent),
            chargeRefs: state.charges.map((c) => bulkRowRef(c)),
        };
    }

    /** The confirmation: the charges go under the parent (`linkInBulk`), its group opens, the selection empties. */
    function confirmLinkPanel() {
        const panel = linkPanel;
        linkPanel = null;
        if (!panel) return;
        const parent = ops.find((op) => op.tempId === panel.parentId);
        const charges = panel.chargeIds.map((id) => ops.find((op) => op.tempId === id)).filter((op): op is PendingOp => op !== undefined);
        if (!parent || charges.length === 0) return;
        ops = linkInBulk(ops, parent, charges);
        openGroup(parent.tempId);
        tableRef?.clearSelection();
        bulkTableSelectedRows = [];
    }

    /** 66 TL-4: «Scollega» on the selection (`unlinkSelectedCharges`); the selection empties, as after «Link». */
    function unlinkSelectedRows(tempIds: string[]) {
        ops = unlinkSelectedCharges(ops, tempIds, txStoreGet);
        tableRef?.clearSelection();
        bulkTableSelectedRows = [];
    }

    /** «Delete selected» (66 F7-c2): the rows taken at the click; the selection empties once the choice is made. */
</script>

<ModalBase {open} maxWidth="none" onRequestClose={requestClose} testId="tx-bulk-modal" allowOverflow={true} contentClass="max-w-[95vw] w-[95vw]">
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="tx-bulk-modal-root" data-busy={scheduler.state.isPending || scheduler.state.isValidating || committing} data-validate-runs={scheduler.state.validateRuns}>
        <!-- Header -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-lf-subtle shrink-0">
            <h2 class="text-lg font-semibold text-lf-primary" data-testid="tx-bulk-title" use:guideAnchor={'transaction.bulk.workspace'}>
                📋 {$t('transactions.bulk.title', {values: {total: topRows.length}})}
                {#if actionCount > 0}
                    <span class="text-sm font-normal text-lf-muted">
                        ({#if newCount > 0}<span class="text-lf-success">{newCount} {$t('transactions.bulk.stateNew')}</span>{/if}{#if newCount > 0 && (editedCount > 0 || deleteCount > 0)}
                            ·
                        {/if}{#if editedCount > 0}<span class="text-lf-warning">{editedCount} {$t('transactions.bulk.stateEdit')}</span>{/if}{#if editedCount > 0 && deleteCount > 0}
                            ·
                        {/if}{#if deleteCount > 0}<span class="text-lf-danger">{deleteCount} {$t('transactions.bulk.stateDel')}</span>{/if}{#if pendingSplits.length > 0}
                            · <span class="text-purple-600 dark:text-purple-400" data-testid="split-queued-badge">⚡ {$t('transactions.bulk.splitQueued', {values: {n: pendingSplits.length}})}</span>{/if})
                    </span>
                {/if}
            </h2>
            <button class="p-2 text-lf-muted hover:text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors" onclick={requestClose} data-testid="tx-bulk-close" aria-label="Close">
                <X size={20} />
            </button>
        </div>

        <!-- Banners -->
        <TxBulkBanners
            bind:commitFailed
            bind:formError
            {fxMarketCache}
            {issues}
            bind:issuesDismissed
            {lastDraftKey}
            {lastIssueDraftKey}
            {ops}
            bind:promoteAllOpen
            bind:promoteBannerSeen
            {syncFxLoading}
            {tableRef}
            bind:todoBlockersExpanded
            bind:todoWarningsExpanded
            {allSuggestions}
            {balanceIssues}
            {bannerSuggestions}
            {fieldIssues}
            {hasPairedDelete}
            {hasWacFxIssues}
            {mergeAllPairs}
            {resolverCtx}
            {showIssuesBanner}
            {todoBlockerEntries}
            {todoWarningEntries}
            {todoWarningRowCount}
            {visibleOps}
            {AUTO_VALIDATE_THRESHOLD}
            {bulkDisplayText}
            {getIssueRows}
            {getVisualRowLabel}
            {handleSyncFx}
            {issueRowsLabel}
            {jumpToIssue}
            {jumpToTodoRow}
            {triggerPromoteFromSuggestion}
            {possibleSplitEntries}
            {preFloorEntries}
            onSplitCreate={(entry) => (splitCreateEntry = entry)}
            onSplitLink={linkSplitEvent}
            {rewardFillPending}
            {rewardFillRunning}
            {rewardFillResult}
            onRewardFill={fillRewardsFromHistory}
        />

        <!-- Toolbar (Bugfix-2 §U9: action buttons right-aligned, most important first
             from the right via flex-row-reverse).
             Bugfix-5 §A4: `+ Add row` re-introduced — opens a nested
             TransactionFormModal that pushes its draft into the grid (no
             commit) so the user gets the structured single-row UX while
             staying in the bulk batch. -->
        <TxBulkToolbar bind:importWizardOpen bind:maxDeltaDays {pendingSplits} {importableSuggestions} {tableRefForToggle} {visibleOps} {deriveStatus} {openAddRowForm} {openPicker} {openSuggestPicker} {resetAll} />

        <!-- DataTable body -->
        <div class="flex-1 min-h-0 overflow-y-auto px-3 py-2" data-testid="tx-bulk-body" bind:this={bulkBodyEl} use:captureChargeChip>
            <DataTable
                bind:this={tableRef}
                data={gridRows}
                selectionData={visibleOps}
                opensPage={opensGridPage}
                isRowSelectable={isGridRowSelectable}
                {columns}
                getRowId={(d) => d.tempId}
                storageKey="tx-bulk-modal"
                enableSelection={true}
                enableColumnFilters={false}
                enablePagination={true}
                alwaysShowPagination={true}
                defaultPageSize={25}
                pageSizeOptions={[5, 10, 25, 50, 0]}
                enableSorting={true}
                onSortChange={(sort) => (dateSortDirection = sort?.direction ?? 'asc')}
                enableColumnVisibility={true}
                enableActions={true}
                actionsColumnWidth="64px"
                rowActions={rowActionsForTable}
                bulkActions={bulkActionsForTable}
                selectionPanel={true}
                onSelectionChange={handleBulkTableSelectionChange}
                stickyActions={false}
                {getRowClass}
                onRowDoubleClick={(row) => handleEditRowClick(row)}
            />
        </div>

        <!-- Footer (Bugfix-4 §U16: validate-now on the left, no duplicate chip
             /issue-count — the green/warning banners above are the single
             source of truth for validate state). -->
        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t border-lf-subtle shrink-0 text-xs">
            <div class="flex items-center gap-2 flex-wrap" use:guideAnchor={'transaction.bulk.validation'}>
                <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={() => scheduler.trigger('manual')} data-testid="tx-bulk-validate-now" title={$t('transactions.validate.now')}>
                    ⚡ <span class="hidden sm:inline">{$t('transactions.validate.now')}</span>
                </button>
                {#if scheduler.state.isValidating || scheduler.state.isPending}
                    <span class="text-[11px] text-lf-muted" data-testid="tx-bulk-validating">{$t('transactions.validate.validating')}</span>
                {:else if isFreshlyValid && !formError && !commitFailed}
                    <span class="text-lf-success text-xs flex items-center gap-1" data-testid="tx-bulk-valid">
                        <Check size={14} />
                        {$t('transactions.validate.ok')}
                    </span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary bg-lf-panel hover:bg-lf-neutral inline-flex items-center gap-1.5" onclick={requestClose} data-testid="tx-bulk-cancel" title={$t('common.cancel')}
                    ><X size={15} /> <span class="hidden sm:inline">{$t('common.cancel')}</span></button
                >
                <button
                    type="button"
                    class="px-4 py-2 text-sm rounded-lg text-lf-on-action bg-lf-action hover:bg-lf-action-hover disabled:opacity-50 inline-flex items-center gap-1.5"
                    disabled={commitDisabled}
                    onclick={requestCommit}
                    use:guideAnchor={['import.bulk.save-all', 'transaction.bulk.save']}
                    data-testid="tx-bulk-commit"
                    title={hasTodoBlockers ? $t('importWizard.todoBlockerCommitHint') : commitLabel}
                >
                    <Save size={15} /> <span class="hidden sm:inline">{commitLabel}</span>
                </button>
            </div>
        </div>
    </div>
</ModalBase>

<!-- Save-gate: force the user to review auto-derived "fields to verify" (warning todos)
     before committing. Non-destructive — "Save anyway" proceeds, "Review" returns to the grid. -->
<ConfirmModal
    open={confirmWarningsOpen}
    title={$t('importWizard.todoWarningConfirmTitle')}
    message={$t('importWizard.todoWarningConfirmMessage', {values: {n: todoWarningRowCountAll}})}
    items={todoWarningItems}
    itemsLabel={$t('importWizard.todoWarningConfirmItemsLabel', {values: {n: todoWarningItems.length}})}
    confirmText={$t('importWizard.todoWarningConfirmProceed')}
    cancelText={$t('importWizard.todoWarningConfirmReview')}
    warning
    onConfirm={() => {
        confirmWarningsOpen = false;
        requestCommitPastWarnings();
    }}
    onCancel={() => (confirmWarningsOpen = false)}
    zIndex={70}
/>

<!-- Save gate: rows dated before 1900 (D-P4). One question for all of them; «Review» returns to the grid. -->
<ConfirmModal
    open={confirmPreFloorOpen}
    title={$t('transactions.bulk.preFloorDate.confirmTitle')}
    message={$t('transactions.bulk.preFloorDate.confirmMessage', {values: {n: preFloorEntries.length}})}
    items={preFloorEntries.map((entry) => $t('transactions.bulk.preFloorDate.row', {values: {row: entry.rowNumber, date: entry.date}}))}
    confirmText={$t('transactions.bulk.preFloorDate.confirmProceed')}
    cancelText={$t('importWizard.todoWarningConfirmReview')}
    warning
    onConfirm={() => {
        confirmPreFloorOpen = false;
        void commit();
    }}
    onCancel={() => (confirmPreFloorOpen = false)}
    zIndex={70}
/>

<!-- Save gate: merge suggestions nobody looked at (the lightbulb never opened, the banner never
     touched). «Save anyway» goes on to the fields to verify; the other answer shows them. -->
<ConfirmModal
    open={confirmSuggestionsOpen}
    title={$t('transactions.bulk.unseenSuggestionsTitle')}
    message={$t('transactions.bulk.unseenSuggestionsMessage', {values: {n: unseenSuggestionCount}})}
    confirmText={$t('importWizard.todoWarningConfirmProceed')}
    cancelText={$t('transactions.bulk.unseenSuggestionsReview')}
    warning
    testId="tx-bulk-unseen-suggestions"
    onConfirm={() => {
        confirmSuggestionsOpen = false;
        suggestPickerSeen = true;
        promoteBannerSeen = true;
        requestCommitPastSuggestions();
    }}
    onCancel={reviewSuggestions}
    zIndex={70}
/>

<!-- «Merge all» of the banner: one answer for every suggested pair. -->
<PromoteAllModal open={promoteAllOpen} count={mergeAllPairs.length} onConfirm={mergeAllSuggestions} onCancel={() => (promoteAllOpen = false)} />

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
    open={open && formOpen}
    mode={formMode}
    items={formItems}
    {defaultBrokerId}
    commitOnSave={false}
    unlockImmutable={formMode === 'edit'}
    availableTags={aggregatedTags}
    zIndex={70}
    openKey={formKey}
    getBulkContext={() => getBulkContextExcluding(formEditingTempId)}
    allowChargeEdits={formChargeEdits}
    bulkCandidates={formBulkCandidates}
    groupSync={formEditingTempId != null && newGroupOf(ops, formEditingTempId) !== null}
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
    onOpenTransaction={(id) => void handleFormOpenTransaction(id)}
    highlightTxId={formHighlightTxId}
    pendingTxIds={pendingTxIds.size > 0 ? pendingTxIds : null}
    onClose={() => {
        formOpen = false;
        formEditingTempId = null;
    }}
    onPushDraft={handleFormPushed}
/>

<!-- Plan B Step 9: PickerModal for adding existing DB transactions -->
<!-- 66 F7-c2: the panel V1 inside the Bulk — what to do with the linked charges of the parents being deleted. -->
<TxChargesActionModal
    open={deletePanel != null}
    mode="deleteParent"
    parents={deletePanel?.parents ?? []}
    charges={deletePanel?.charges ?? []}
    parentRefs={deletePanel?.parentRefs}
    chargeRefs={deletePanel?.chargeRefs}
    counts={deletePanel?.plan.counts}
    onChoose={chooseDelete}
    onCancel={cancelDelete}
    zIndex={70}
/>

<!-- 66 F7-d: «Link» inside the Bulk (U3) — the parent and its charges, linked on «Save all». -->
<TxChargesActionModal
    open={linkPanel != null}
    mode="link"
    parents={linkPanel ? [linkPanel.parent] : []}
    charges={linkPanel?.charges ?? []}
    parentRefs={linkPanel ? [linkPanel.parentRef] : undefined}
    chargeRefs={linkPanel?.chargeRefs}
    onConfirm={confirmLinkPanel}
    onCancel={() => (linkPanel = null)}
    zIndex={70}
/>

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
<EventCreateMiniModal
    open={splitCreateEntry !== null}
    assetId={splitCreateEntry?.assetId ?? 0}
    assetName={splitCreateAsset?.display_name ?? splitCreateEntry?.ticker ?? ''}
    assetCurrency={splitCreateAsset?.currency ?? 'USD'}
    defaultDate={splitCreateEntry?.date ?? ''}
    suggestedAmount={splitCreateEntry?.suggestedRatio ?? ''}
    defaultEventType="ADJUSTMENT"
    zIndex={80}
    oncreated={(eventId) => {
        if (splitCreateEntry) linkSplitEvent(splitCreateEntry.tempId, eventId);
    }}
    onclose={() => (splitCreateEntry = null)}
/>
<ImportWizardModal open={importWizardOpen} zIndex={70} {defaultBrokerId} {pendingCreateTransactions} {pendingDeleteTxIds} onClose={() => (importWizardOpen = false)} {onImportBatch} />
