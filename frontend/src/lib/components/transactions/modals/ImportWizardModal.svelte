<!--
  ImportWizardModal.svelte — Phase 07 Part 5 v5 M3

  Wide 4-step wizard for importing broker report files into BulkModal.
  Step 1: Upload files (broker-independent) & assign broker per-file
  Step 2: Select existing broker files to parse (DataTable per broker, per-file plugin)
  Step 3: Parse engine — sequential parse with progress, results DataTable, detail modal
  Step 4: Review & Import — asset resolution + TX selection + handoff to BulkModal
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {Upload, Trash2, Eye, Search, ChevronDown, ChevronRight, Check, AlertTriangle, Info, Plus, CheckCircle, FileText, RefreshCw, CheckSquare, Square, ListChecks, X, Wand2, Pencil, Loader2} from 'lucide-svelte';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {extractErrorMessage, trySave} from '$lib/utils/trySave';
    import {formatBytes} from '$lib/utils/files/upload';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {ensureBrokersLoaded, getEditableBrokers, refreshAllBrokers, getBrokerInfo, type BrokerInfo} from '$lib/stores/reference/brokerStore';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {getAssetInfo, refreshAllAssets, type AssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {isFakeAssetId} from '$lib/utils/brim/isFakeAssetId';
    import {getIndexColor, getStringColor} from '$lib/utils/colors';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';
    import IdentifierPrimaryChooser from '$lib/components/assets/IdentifierPrimaryChooser.svelte';
    import {pendingIdentifier, needsPrimaryChoice, mergeOther, demotedValues} from '$lib/utils/assetIdentifiers';
    import {electPrimary, groupExtractedAssets, groupSignature, orderedIdentifiers, representativeMap, representativeOf, type AssetGroup, type ExtractedAsset, type GroupOverride, type IdentifierKind, type PrimaryMap, type SimilarityLink} from '$lib/utils/assetGrouping';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import {getTransactionTypeIconUrl, getTypeRule, ensureTypesLoaded, TX_TYPES} from '$lib/stores/transactions/transactionTypeStore';

    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {BrokerSearchSelect} from '$lib/components/ui/select';
    import ImportPluginSelect, {getCachedPlugins} from '$lib/components/ui/select/ImportPluginSelect.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import BrokerModal from '$lib/components/brokers/BrokerModal.svelte';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import FilePreviewModal from '$lib/components/files/FilePreviewModal.svelte';
    import ParseDetailModal from '$lib/components/transactions/modals/ParseDetailModal.svelte';
    import {fetchFilePreview, getFilePreviewError} from '$lib/utils/files/filePreview';
    import {generateUUID} from '$lib/utils/core/uuid';
    import {mapWithConcurrency} from '$lib/utils/core/requestConcurrency';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import {scrollOnOverflow, attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import type {ColumnDef, RowAction, EnumOption} from '$lib/components/table/types';
    import type {BrimDuplicateMatch, BrimNotice} from '$lib/types/files';
    import BrimNoticeList from '$lib/components/transactions/import/BrimNoticeList.svelte';
    import FixFlaggedStep, {type FixPatch} from '$lib/components/transactions/import/FixFlaggedStep.svelte';
    import AssetGroupStep from '$lib/components/transactions/import/AssetGroupStep.svelte';
    import AssetMergeModal from '$lib/components/assets/AssetMergeModal.svelte';
    import TransactionCompareModal from '$lib/components/transactions/modals/TransactionCompareModal.svelte';
    import type {CompareColumn, CompareField, CompareCell} from '$lib/components/transactions/modals/TransactionCompareModal.svelte';
    import type {TXReadItem} from '$lib/components/transactions';
    import {txStoreGet} from '$lib/stores/transactions/txStore.svelte';
    import {applySignRules, type ImportTodo} from '$lib/utils/transactions/txPayloadHelpers';
    import {buildDuplicateRecheckPayload} from '$lib/utils/transactions/duplicateRecheckPayload';
    import {isFixStepTodo, rowStaysInFixStep, todosAfterSettle, todosAfterReopen} from '$lib/utils/transactions/fixRowLifecycle';
    import {CONF_ORDER, type DuplicateStatus, type DuplicateTier, type DedupKey, type DuplicateGroup, type MergedTx, type AssetResolution} from '$lib/utils/transactions/importTypes';
    import {buildDedupKey, buildDuplicateGroups, dedupKeysMatch, duplicateStatusAllowsAutoSelect, duplicateStatusIsSelectedWarning, isResolvedAwayDuplicate, pendingDuplicateStatusFor} from '$lib/utils/transactions/importDedup';
    import {buildMergedTransactions, mergeCandidates, uniqueExactCandidateId} from '$lib/utils/transactions/importMerge';
    import {cmpSourceFromTx, cmpSourceFromExisting, compareTypeCellHtml, type CmpSource} from '$lib/utils/transactions/importCompare';
    import {createNamesFor, createOtherFor, duplicateCandidates, resolutionLabel as resolutionLabelPure} from '$lib/utils/transactions/importResolutionHelpers';
    import {brokerIdForTx, beforeOpeningInfo, isBeforeOpening as isBeforeOpeningPure, isRowAssetResolved as isRowAssetResolvedPure} from '$lib/utils/transactions/importRowState';
    import {groupPartitions as groupPartitionsPure, defaultKeeperIndices as defaultKeeperIndicesPure, resolverSelectionFor as resolverSelectionForPure, outlierIndexSet} from '$lib/utils/transactions/importDuplicateResolver';

    import type {TransactionCreateItem, BrimFile, BrimParseResponse, FilePreviewResponse} from '$lib/types';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open: boolean;
        zIndex?: number;
        /** Pre-populates the global broker selector (Step 1) when opened from a
         *  broker-scoped page — still editable, still per-file overridable. */
        defaultBrokerId?: number | null;
        pendingCreateTransactions?: TransactionCreateItem[];
        /** DB transaction ids marked for deletion in the parent bulk editor. DB-duplicate
         *  matches against these ids are dropped, so a re-imported row matching only
         *  to-be-deleted rows is no longer flagged as a duplicate. */
        pendingDeleteTxIds?: number[];
        onClose: () => void;
        onImportBatch: (creates: Array<{tx: TransactionCreateItem; todos: ImportTodo[]}>) => void;
    }

    let {open, zIndex = 70, defaultBrokerId = null, pendingCreateTransactions = [], pendingDeleteTxIds = [], onClose, onImportBatch}: Props = $props();

    // =========================================================================
    // Constants
    // =========================================================================

    const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];

    /**
     * Wizard steps, in canonical order.
     *
     * `fix` and `duplicates` only appear when they have something to do. A wizard that
     * always shows every step, half of them empty, teaches the user to click through
     * without reading — which is exactly the habit that makes a review step useless.
     *
     * Order matters and encodes the invariant that motivated the split: nothing is
     * compared against the database until the data is complete. Understand → unify →
     * correct → compare → review.
     *
     * `assets` sits before `fix` deliberately. The correction step asks the user to attach an
     * asset to a flagged row, and its list is derived from the resolutions: unify afterwards and
     * the same security would appear twice there, indistinguishable, so half the rows would land
     * on half the instrument. Unifying first makes that choice unambiguous and asks it once.
     */
    type StepId = 'upload' | 'select' | 'analyze' | 'assets' | 'fix' | 'duplicates' | 'review';

    const STEP_DEFS: ReadonlyArray<{id: StepId; titleKey: string}> = [
        {id: 'upload', titleKey: 'step1Title'},
        {id: 'select', titleKey: 'step2Title'},
        {id: 'analyze', titleKey: 'step3Title'},
        {id: 'assets', titleKey: 'stepAssetsTitle'},
        {id: 'fix', titleKey: 'stepFixTitle'},
        {id: 'duplicates', titleKey: 'stepDuplicatesTitle'},
        {id: 'review', titleKey: 'step4Title'},
    ];

    const STEP_ORDER: ReadonlyArray<StepId> = STEP_DEFS.map((s) => s.id);

    // =========================================================================
    // Stepper State
    // =========================================================================

    let currentStepId = $state<StepId>('upload');

    // =========================================================================
    // Step 1 State — Upload & Assign Broker
    // =========================================================================

    interface PendingFileEntry {
        id: string;
        file: globalThis.File;
        fileName: string;
        brokerId: number | null;
        status: 'pending' | 'uploading' | 'uploaded' | 'error';
        serverFileId?: string;
        errorMessage?: string;
    }

    let pendingFiles = $state<PendingFileEntry[]>([]);
    let globalBrokerId = $state<number | null>(null);
    let uploading = $state(false);
    let uploadError = $state<string | null>(null);
    let fileUploaderRef: FileUploader | undefined = $state(undefined);
    let dropZoneExpanded = $state(true); // T2: collapsible drop zone
    let dropZoneContainerRef: HTMLDivElement | undefined = $state(undefined);

    // T1/R3: click outside drop zone → collapse if files exist
    $effect(() => {
        if (!dropZoneExpanded || pendingFiles.length === 0) return;
        function handleClickOutside(e: MouseEvent) {
            if (isOutsideClick(e.target, (el) => !dropZoneContainerRef || dropZoneContainerRef.contains(el))) {
                dropZoneExpanded = false;
            }
        }
        // Delay listener to avoid collapsing from the same click that opened it
        const timer = setTimeout(() => document.addEventListener('mousedown', handleClickOutside), 0);
        return () => {
            clearTimeout(timer);
            document.removeEventListener('mousedown', handleClickOutside);
        };
    });

    // Step 1 validation: all files must have broker assigned (or no files = ok to proceed)
    let step1CanProceed = $derived(pendingFiles.length === 0 || pendingFiles.every((f) => f.brokerId !== null && f.status !== 'error'));
    let step1HasUnassigned = $derived(pendingFiles.some((f) => f.brokerId === null && f.status !== 'error'));
    let step1ValidCount = $derived(pendingFiles.filter((f) => f.status !== 'error').length);
    let step1SelectedIds = $state<string[]>([]);
    let step1TableRef: DataTable<PendingFileEntry> | undefined = $state(undefined);

    // =========================================================================
    // Step 2 State — Select Files from Broker Panels (DataTable)
    // =========================================================================

    interface FileSelection {
        fileId: string;
        fileName: string;
        brokerId: number;
        pluginCode: string;
    }

    let selectedFiles = $state<FileSelection[]>([]);
    let brokerFilesMap = $state<Map<number, BrimFile[]>>(new Map());
    let brokerFilesLoading = $state(false);

    // Step 2: delete-report (broker import file) confirmation
    let showDeleteFileConfirm = $state(false);
    let pendingDeleteFile = $state<{fileId: string; brokerId: number; fileName: string} | null>(null);
    let expandedBrokers = $state<Set<number>>(new Set());
    let filePluginOverrides = $state<Map<string, string>>(new Map());

    // T9: Parse validation — all selected files must have a plugin
    let step2CanParse = $derived(selectedFiles.length > 0 && selectedFiles.every((f) => f.pluginCode !== ''));

    // =========================================================================
    // Step 3 State — Parse Engine & Results
    // =========================================================================

    interface ParsedFileResult {
        fileId: string;
        fileName: string;
        brokerId: number;
        brokerName: string;
        brokerIconUrl: string | null;
        brokerPortalUrl: string | null;
        pluginUsed: string;
        pluginName: string;
        status: 'pending' | 'parsing' | 'done' | 'error';
        response: BrimParseResponse | null;
        errorMessage?: string;
    }

    let parseResults = $state<ParsedFileResult[]>([]);
    let abortParsing = $state(false);
    let lastParseHash = $state<string | null>(null);
    let showParseDetail = $state(false);
    let parseDetailResult = $state<ParsedFileResult | null>(null);
    let showAggregateDetail = $state(false);

    // Parse progress deriveds
    let parseCompletedCount = $derived(parseResults.filter((r) => r.status === 'done' || r.status === 'error').length);
    let parseTotalCount = $derived(parseResults.length);
    let parseDone = $derived(parseTotalCount > 0 && parseResults.every((r) => r.status === 'done' || r.status === 'error'));
    let parseHasSuccess = $derived(parseResults.some((r) => r.status === 'done'));
    let parseHasErrors = $derived(parseResults.some((r) => r.status === 'error'));
    let parseFailures = $derived(parseResults.filter((r) => r.status === 'error'));
    let parseParsing = $derived(parseResults.some((r) => r.status === 'parsing'));
    let step3CanContinue = $derived(parseDone && parseHasSuccess);
    let usingCachedResults = $state(false);

    // The outcome of the parse, in one machine-readable word. The visible status is a
    // localized sentence, so without this the only thing an observer can see is that
    // Continue stays disabled — which is equally true while a parse is still running and
    // after one has failed. Those two need telling apart: the first is worth waiting for,
    // the second never resolves.
    let parseState = $derived(parseTotalCount === 0 ? 'idle' : !parseDone ? 'parsing' : parseHasSuccess ? (parseHasErrors ? 'partial' : 'ok') : 'error');

    // Aggregate stats from done results
    let parseAggregateStats = $derived(() => {
        const doneResults = parseResults.filter((r) => r.status === 'done' && r.response);
        const totalTx = doneResults.reduce((sum, r) => sum + (r.response!.transactions?.length ?? 0), 0);
        const doneFileCount = doneResults.length;
        const allMappings = doneResults.flatMap((r) => r.response!.asset_mappings ?? []);
        const uniqueAssetIds = new Set(allMappings.map((m) => m.fake_asset_id));
        const unresolvedCount = allMappings.filter((m) => m.selected_asset_id == null).length;
        const totalWarnings = doneResults.reduce((sum, r) => sum + (r.response!.warnings?.length ?? 0), 0);
        const totalIssues = doneResults.reduce((sum, r) => sum + ((r.response!.validation_issues as unknown[] | undefined)?.length ?? 0), 0);
        const fieldTodos = doneResults.flatMap((r) => (r.response!.field_todos as {severity: string}[] | undefined) ?? []);
        const totalTodos = fieldTodos.length;
        const todoBlockers = fieldTodos.filter((t) => t.severity === 'blocker').length;
        const duplicates = doneResults.reduce((sum, r) => {
            const dup = r.response!.duplicates;
            if (!dup || Array.isArray(dup)) return sum;
            return sum + (dup.tx_likely_duplicates?.length ?? 0);
        }, 0);
        return {totalTx, doneFileCount, uniqueAssets: uniqueAssetIds.size, unresolvedCount, totalWarnings, totalIssues, totalTodos, todoBlockers, likelyDuplicates: duplicates};
    });

    function computeParseHash(): string {
        const sorted = [...selectedFiles].sort((a, b) => a.fileId.localeCompare(b.fileId)).map((f) => `${f.fileId}:${f.pluginCode}`);
        return sorted.join('|');
    }

    // =========================================================================
    // Step 4 State — Review & Import
    // =========================================================================

    // Value-object types (MergedTx, AssetResolution, DedupKey, DuplicateGroup, …) and the
    // dedup tolerances live in `$lib/utils/transactions/importTypes`, so the pure Step-4
    // logic can be extracted and unit-tested. See the import at the top of this script.

    function syncDuplicateFilePriority() {
        const ids = parseResults.filter((r) => r.status === 'done').map((r) => r.fileId);
        const known = new Set(ids);
        duplicateFilePriorityIds = [...duplicateFilePriorityIds.filter((id) => known.has(id)), ...ids.filter((id) => !duplicateFilePriorityIds.includes(id))];
    }

    interface GroupPartition {
        primaryIndex: number;
        memberIndices: number[];
        crossFile: boolean;
    }

    // Duplicate-resolver logic lives in $lib/utils/transactions/importDuplicateResolver.ts; these
    // thin wrappers inject the reactive wizard state (duplicateFilePriorityIds, the manual-choice
    // set, the per-row selections) so all call sites and the markup stay unchanged.
    function groupPartitions(group: DuplicateGroup, txArr: MergedTx[] = mergedTransactions): GroupPartition[] {
        return groupPartitionsPure(group, txArr, duplicateFilePriorityIds);
    }

    function defaultKeeperIndices(group: DuplicateGroup, txArr: MergedTx[] = mergedTransactions): Set<number> {
        return defaultKeeperIndicesPure(group, txArr, duplicateFilePriorityIds);
    }

    function resolverHasManualChoice(group: DuplicateGroup): boolean {
        return duplicateResolverTouchedKeys.has(group.key);
    }

    function resolverSelectionFor(group: DuplicateGroup, rowIndex: number, txArr: MergedTx[] = mergedTransactions): boolean {
        return resolverSelectionForPure(group, rowIndex, txArr, duplicateFilePriorityIds, resolverHasManualChoice(group), duplicateResolverSelections);
    }

    function applyDuplicateResolverChoice(group: DuplicateGroup, rowIndex: number, selected: boolean) {
        const next = {...duplicateResolverSelections};
        for (const idx of group.memberIndices) {
            next[idx] = resolverSelectionFor(group, idx);
        }
        next[rowIndex] = selected;
        duplicateResolverSelections = next;
        duplicateResolverTouchedKeys = new Set(duplicateResolverTouchedKeys).add(group.key);
        reapplyResolverGroups();
    }

    function resetDuplicateResolverChoice(group: DuplicateGroup) {
        const next = {...duplicateResolverSelections};
        for (const idx of group.memberIndices) delete next[idx];
        duplicateResolverSelections = next;
        const touched = new Set(duplicateResolverTouchedKeys);
        touched.delete(group.key);
        duplicateResolverTouchedKeys = touched;
        reapplyResolverGroups();
    }

    /**
     * Re-apply in-batch duplicate resolution to the already-merged rows after a resolver change
     * (checkbox, reset, priority reorder) so step 3 (member table) and step 4 stay live. Mutates
     * MergedTx in place, then reassigns the array to trigger Svelte reactivity.
     */
    function reapplyResolverGroups() {
        if (mergedTransactions.length === 0 || duplicateGroups.length === 0) return;
        applyPendingDuplicateGroups(mergedTransactions, duplicateGroups);
        mergedTransactions = [...mergedTransactions];
    }

    function applyPendingDuplicateGroups(txArr: MergedTx[], groups: DuplicateGroup[]) {
        for (const group of groups) {
            const partitions = groupPartitions(group, txArr);
            const primaryIndices = new Set(partitions.map((p) => p.primaryIndex));
            // Back-reference each secondary to its own partition primary (its exact twin).
            const primaryOf = new Map<number, number>();
            for (const p of partitions) {
                for (const idx of p.memberIndices) primaryOf.set(idx, p.primaryIndex);
            }
            for (const idx of group.memberIndices) {
                const mt = txArr.find((row) => row.index === idx);
                if (!mt) continue;
                const isPrimary = primaryIndices.has(idx);
                mt.selected = resolverSelectionFor(group, idx, txArr);
                mt.dupGroupKey = group.key;
                mt.dupTier = group.tier;
                mt.isDupKeeper = isPrimary;
                if (isPrimary) {
                    // Keep the primary's own vs-existing status; it is not an in-batch duplicate.
                    mt.dupKeeperIndex = undefined;
                    mt.dupKeeperFileName = undefined;
                } else {
                    // Every secondary shares its partition's description+key → exact in-batch duplicate.
                    mt.duplicateStatus = 'pending_duplicate';
                    const keeperIndex = primaryOf.get(idx) ?? idx;
                    mt.dupKeeperIndex = keeperIndex;
                    mt.dupKeeperFileName = getSourceFileName(txArr.find((row) => row.index === keeperIndex)?.sourceFileId ?? '');
                }
            }
        }
    }

    function markPendingBulkDuplicates(txArr: MergedTx[], assetMap: Map<number, AssetResolution>) {
        const pending = pendingCreateTransactions.map((tx) => ({tx, key: buildDedupKey(tx, assetMap)})).filter((entry): entry is {tx: TransactionCreateItem; key: DedupKey} => entry.key !== null);
        for (const mt of txArr) {
            const key = buildDedupKey(mt.tx, assetMap);
            if (!key) continue;
            const match = pending.find((entry) => dedupKeysMatch(key, entry.key));
            if (!match) continue;
            mt.duplicateStatus = pendingDuplicateStatusFor(mt.tx, match.tx);
            mt.selected = mt.duplicateStatus === 'pending_possible_duplicate';
            mt.isDupKeeper = false;
            mt.dupKeeperIndex = undefined;
            mt.dupKeeperFileName = $t('importWizard.resolver.pendingEditor');
            mt.dupPendingMatch = match.tx;
        }
    }

    let mergedTransactions = $state<MergedTx[]>([]);
    let assetResolutions = $state<AssetResolution[]>([]);

    /*
     * Unification state.
     *
     * `assetGroupOverride` holds the user's partition once they have touched the layout. It is a
     * whole partition rather than a delta because the automatic grouping is recomputed from
     * scratch on every re-merge, and a delta against a partition that no longer exists cannot be
     * replayed. Members are addressed by content key, since fake ids are reallocated each time.
     */
    let assetGroups = $state<AssetGroup[]>([]);
    let assetGroupOverride = $state<GroupOverride>(null);
    /** Signatures of proposals the user accepted as they stood, without reshaping anything. */
    let assetGroupConfirmed = $state<Set<string>>(new Set());
    /**
     * Which code leads its kind, per group. Keyed by cluster signature so the choice outlives the
     * fake ids; the elected value is moved to the front of the group's list, which is how it
     * reaches the creation form and the search hints without any of them learning a new concept.
     */
    let assetGroupPrimary = $state<PrimaryMap>({});
    let duplicateGroups = $state<DuplicateGroup[]>([]);
    let duplicateFilePriorityIds = $state<string[]>([]);
    let duplicateResolverTouchedKeys = $state<Set<string>>(new Set());
    let duplicateResolverSelections = $state<Record<number, boolean>>({});
    let expandedDuplicateGroupKeys = $state<Set<string>>(new Set());
    let duplicateResolverCollapsed = $state(false);
    /** The database-collision recap is informational — it opens folded. */
    /** Width of the file-priority column, dragged by the user (desktop only). */
    let duplicatePriorityWidth = $state(280);

    function startPriorityResize(ev: PointerEvent) {
        ev.preventDefault();
        const startX = ev.clientX;
        const startWidth = duplicatePriorityWidth;
        const onMove = (m: PointerEvent) => {
            duplicatePriorityWidth = Math.min(560, Math.max(180, startWidth + (m.clientX - startX)));
        };
        const onUp = () => {
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
        };
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
    }
    /** Tier sub-panels inside the resolver — both start folded (see `resolverTierPanels`). */
    let expandedDuplicateTiers = $state<Set<DuplicateTier>>(new Set());
    /**
     * How the user settled each flagged row in the `fix` step: by correcting it, or by
     * accepting the plugin's fallback. Kept apart from the todos themselves so a re-parse
     * can restore the original verdict, and kept per-row (rather than as a bare "done"
     * set) so the list can show *which* decision was taken.
     */
    let fixDecisions = $state<Record<number, 'corrected' | 'kept'>>({});
    /** The flagged todos as they were before being retired — the row stays readable. */
    let fixTodoSnapshot = $state<Record<number, ImportTodo[]>>({});
    /** The transaction as the plugin read it, so a correction can always be undone. */
    let fixTxSnapshot = $state<Record<number, TransactionCreateItem>>({});
    let fixExpandedIndices = $state<Set<number>>(new Set());
    let duplicateRecheckRunning = $state(false);
    let duplicateRecheckError = $state<string | null>(null);
    /** True once the duplicate report has been recomputed on the corrected transactions. */
    let duplicateRecheckDone = $state(false);
    let createAssetForFakeId = $state<number | null>(null);
    /**
     * Which code leads on an asset about to be created from a unified group.
     *
     * A group that absorbed two files can carry two ISINs — the retail bond's non-tradeable
     * issue code and its quoted one — and picking either by position would be a coin toss with
     * a real cost: only the quoted code can ever return a price. So the question is asked once,
     * before the form opens, and the form then arrives already correct.
     */
    let createPrimaryIsin = $state<string | null>(null);
    let createPrimarySymbol = $state<string | null>(null);
    let createPrimaryPending = $state<'identifier_isin' | 'identifier_ticker' | null>(null);
    let createBrokerOpen = $state(false);
    /** Tracks which context opened the create-broker modal: 'global' or a pendingFile id */
    let createBrokerContext = $state<'global' | string | null>(null);
    let step4ShowResolveSection = $state(true);
    let step4TableRef = $state<DataTable<MergedTx> | undefined>(undefined);
    let brokers = $state<BrokerInfo[]>([]);
    let brokersLoading = $state(false);
    let confirmCloseOpen = $state(false);
    let showWarningConfirm = $state(false);

    interface BrokerModalInitialData {
        name?: string;
        description?: string | null;
        portal_url?: string | null;
        icon_url?: string | null;
        default_import_plugin?: string | null;
        allow_cash_overdraft?: boolean;
        allow_asset_shorting?: boolean;
        is_active?: boolean;
        opened_at?: string | null;
    }

    let editBrokerOpen = $state(false);
    let editBrokerId = $state<number | null>(null);
    let editBrokerInitialData = $state<BrokerModalInitialData>({});

    // N-way compare modal state — side-by-side comparison of lot-duplicate members or parsed-vs-DB rows
    let nwCompareOpen = $state(false);
    let nwCompareTitle = $state('');
    let nwCompareHint = $state<string | undefined>(undefined);
    let nwCompareFields = $state<CompareField[]>([]);
    let nwCompareColumns = $state<CompareColumn[]>([]);
    let nwCompareDefaultKept = $state<string[] | undefined>(undefined);
    let nwCompareResetKept = $state<string[] | undefined>(undefined);
    let nwCompareOnKeep = $state<((keptIds: string[]) => void) | undefined>(undefined);

    /*
     * Add-identifier prompt — raised when the asset the user just picked does not already carry
     * the identifier the report quoted.
     *
     * Two shapes, one modal:
     *  - the asset holds no code of that type → a plain "save it as the primary?" confirmation;
     *  - it holds a different one → `IdentifierPrimaryChooser`, because the right answer is never
     *    to throw one away. An Italian retail bond bought at issue quotes its non-tradeable CUM
     *    code in the report while the asset already holds the quoted one: both must survive, one
     *    leads.
     */
    let identifierPromptOpen = $state(false);
    let identifierPromptAssetId = $state<number | null>(null);
    let identifierPromptFakeAssetId = $state<number | null>(null);
    let identifierPromptField = $state<'identifier_ticker' | 'identifier_isin' | null>(null);
    /** The codes the group offers that the asset does not know. More than one after unification. */
    let identifierPromptValues = $state<string[]>([]);
    let identifierPromptAssetName = $state<string | null>(null);
    let identifierPromptSaving = $state(false);
    /** true = there is an election to hold (a stored code, or several offered) → chooser shown. */
    let identifierPromptIsConflict = $state(false);
    /** Normalised: an empty column reads as `null`, never `''`, or every blank looks like a clash. */
    let identifierPromptExistingValue = $state<string | null>(null);
    /** The asset's current `identifier_other`: the PATCH replaces the list, so it must travel whole. */
    let identifierPromptExistingOther = $state<string[]>([]);
    /** Extra search keys to merge in the same PATCH — the reuse-existing flow feeds these. */
    let identifierPromptExtraOther = $state<string[]>([]);
    /** The value elected as primary (bound to `IdentifierPrimaryChooser`). */
    let identifierPromptPrimary = $state<string | null>(null);
    /** Fields already settled in this chain, so a second pass cannot re-ask the same question. */
    let identifierPromptSettled = $state<string[]>([]);
    /**
     * Cancel means "wrong asset" when the user reached the prompt by picking one from the list,
     * so the row goes back to unresolved. After *creating* an asset there is nothing to undo —
     * it exists, and unbinding it would only orphan it.
     */
    let identifierPromptClearOnCancel = $state(true);

    /**
     * Button labels for the two shapes of the prompt. Kept as plain `$t` calls rather than
     * ternaries inside the markup so the i18n audit can see every key it needs to account for.
     */
    let identifierPromptLabels = $derived(
        identifierPromptIsConflict
            ? {
                  cancel: $t('assets.identifiers.primaryChooser.cancel'),
                  skip: $t('assets.identifiers.primaryChooser.skip'),
                  confirm: $t('assets.identifiers.primaryChooser.confirm'),
              }
            : {
                  cancel: $t('common.cancel'),
                  skip: $t('importWizard.addIdentifier.skip'),
                  confirm: $t('importWizard.addIdentifier.confirm'),
              },
    );

    function getBrokerIdForTx(mt: MergedTx): number | null {
        return brokerIdForTx(mt, parseResults);
    }

    function getBeforeOpeningInfo(mt: MergedTx): {brokerId: number; openedAt: string} | null {
        return beforeOpeningInfo(mt, parseResults, brokers);
    }

    function isBeforeOpening(mt: MergedTx): boolean {
        return isBeforeOpeningPure(mt, parseResults, brokers);
    }

    let beforeOpeningIndices = $derived.by(() => new Set(mergedTransactions.filter(isBeforeOpening).map((t) => t.index)));

    $effect(() => {
        if (!mergedTransactions.some((t) => t.selected && beforeOpeningIndices.has(t.index))) return;
        mergedTransactions = mergedTransactions.map((t) => (beforeOpeningIndices.has(t.index) ? {...t, selected: false} : t));
    });

    /** True unless the row's asset is an unresolved fake mapping (no bound real asset yet). */
    function isRowAssetResolved(t: MergedTx): boolean {
        return isRowAssetResolvedPure(t, assetResolutions);
    }

    // Step 4 deriveds
    let step4Rows = $derived(mergedTransactions.filter((t) => !isResolvedAwayDuplicate(t)));
    let step4SelectedCount = $derived(mergedTransactions.filter((t) => t.selected && !beforeOpeningIndices.has(t.index)).length);
    let step4TotalCount = $derived(step4Rows.filter((t) => !beforeOpeningIndices.has(t.index)).length);
    let step4UnresolvedCount = $derived(assetResolutions.filter((r) => r.resolvedAssetId === null).length);
    let step4HasUnresolvedSelected = $derived(mergedTransactions.some((t) => t.selected && !beforeOpeningIndices.has(t.index) && !isRowAssetResolved(t)));
    let step4CanImport = $derived(step4SelectedCount > 0 && !step4HasUnresolvedSelected);
    let step4SelectedDuplicateCount = $derived(mergedTransactions.filter((t) => t.selected && !beforeOpeningIndices.has(t.index) && duplicateStatusIsSelectedWarning(t.duplicateStatus)).length);
    let step4BeforeOpeningCount = $derived(beforeOpeningIndices.size);
    // Reasons a visible step-4 row is pre-deselected (for the explanatory banner)
    let step4DeselectPendingDup = $derived(step4Rows.filter((t) => !t.selected && !beforeOpeningIndices.has(t.index) && t.duplicateStatus === 'pending_duplicate').length);
    let step4DeselectDbDup = $derived(step4Rows.filter((t) => !t.selected && !beforeOpeningIndices.has(t.index) && t.duplicateStatus === 'likely').length);
    let step4HasDeselectReasons = $derived(step4BeforeOpeningCount > 0 || step4DeselectPendingDup > 0 || step4DeselectDbDup > 0);

    interface BrokerOpeningIssue {
        brokerId: number;
        broker: BrokerInfo | {id: number; name: string};
        openedAt: string;
        minTxDate: string;
        count: number;
    }

    /** Brokers whose opening date is later than one or more of their (before-opening) transactions. */
    let brokerOpeningIssues = $derived.by<BrokerOpeningIssue[]>(() => {
        const byBroker = new Map<number, {openedAt: string; minTxDate: string; count: number}>();
        for (const t of mergedTransactions) {
            if (!beforeOpeningIndices.has(t.index)) continue;
            const info = getBeforeOpeningInfo(t);
            if (!info) continue;
            const d = t.tx.date ? String(t.tx.date).slice(0, 10) : '';
            const cur = byBroker.get(info.brokerId);
            if (!cur) {
                byBroker.set(info.brokerId, {openedAt: String(info.openedAt).slice(0, 10), minTxDate: d, count: 1});
            } else {
                cur.count += 1;
                if (d && (cur.minTxDate === '' || d < cur.minTxDate)) cur.minTxDate = d;
            }
        }
        return [...byBroker.entries()].map(([brokerId, v]) => ({
            brokerId,
            broker: getBrokerInfo(brokerId) ?? brokers.find((b) => b.id === brokerId) ?? {id: brokerId, name: `#${brokerId}`},
            openedAt: v.openedAt,
            minTxDate: v.minTxDate,
            count: v.count,
        }));
    });

    /**
     * Return the asset_id of a lone EXACT-confidence candidate, else null.
     * Used to auto-bind an extracted asset whose ISIN uniquely matches one existing
     * asset even when the backend left selected_asset_id null.
     */
    function mergeAllTransactions() {
        const {txArr, assetMap, fileIdOfFake} = buildMergedTransactions(parseResults, brokers, pendingDeleteTxIds);

        // Unification runs *before* anything else looks at assets: the duplicate report, the
        // correction step and the review all read the resulting list, so a partition applied
        // later would mean asking the user to pick an asset twice.
        applyAssetGrouping(txArr, assetMap, fileIdOfFake);

        syncDuplicateFilePriority();
        rebuildDuplicateGroups(txArr, assetMap);

        // Compute txCount and sourceFiles per asset resolution
        for (const [fakeId, res] of assetMap) {
            const relTx = txArr.filter((t) => t.tx.asset_id === fakeId);
            res.txCount = relTx.length;
            res.sourceFiles = [...new Set(relTx.map((t) => parseResults.find((r) => r.fileId === t.sourceFileId)?.fileName ?? t.sourceFileId))];
        }

        mergedTransactions = txArr;
        assetResolutions = [...assetMap.values()];
        step4ShowResolveSection = assetMap.size > 0;
    }

    /**
     * Fold the per-file extracted assets into one resolution per security, rewriting the
     * transactions of the folded members onto the survivor.
     *
     * Rewriting `tx.asset_id` rather than keeping a parallel lookup is what makes the rest of the
     * wizard correct for free: the duplicate detector finally sees two files' rows as the same
     * instrument, the correction step's picker lists the security once, and the final import
     * needs no translation table.
     */
    function applyAssetGrouping(txArr: MergedTx[], assetMap: Map<number, AssetResolution>, fileIdOfFake: Map<number, string>) {
        const extracted: ExtractedAsset[] = [...assetMap.values()].map((res) => {
            const fileId = fileIdOfFake.get(res.fakeAssetId) ?? '';
            return {
                fakeAssetId: res.fakeAssetId,
                fileId,
                fileName: parseResults.find((r) => r.fileId === fileId)?.fileName ?? fileId,
                name: res.extractedName,
                isin: res.extractedIsin,
                symbol: res.extractedSymbol,
            };
        });

        const groups = groupExtractedAssets(extracted, assetGroupOverride, assetGroupConfirmed);
        assetGroups = groups;
        const survivorOf = representativeMap(groups);

        for (const group of groups) {
            const lead = representativeOf(group.members);
            const leadRes = assetMap.get(lead.fakeAssetId);
            if (!leadRes) continue;
            const primary = assetGroupPrimary[groupSignature(group)];
            const identifiers = orderedIdentifiers(group.members, primary);

            leadRes.groupIsins = identifiers.isins;
            leadRes.groupSymbols = identifiers.symbols;
            leadRes.groupNames = identifiers.names;
            leadRes.groupMembers = group.members;
            leadRes.groupState = group.state;
            leadRes.groupLinks = group.links;
            leadRes.groupPrimaryIsin = primary?.isin !== undefined;
            leadRes.groupPrimarySymbol = primary?.symbol !== undefined;

            for (const member of group.members) {
                if (member.fakeAssetId === lead.fakeAssetId) continue;
                const folded = assetMap.get(member.fakeAssetId);
                if (!folded) continue;
                // A member may have been the only one the backend could match: keep its
                // candidates and its binding rather than losing them with the entry.
                leadRes.candidates = mergeCandidates(leadRes.candidates, folded.candidates);
                leadRes.resolvedAssetId = leadRes.resolvedAssetId ?? folded.resolvedAssetId;
                leadRes.notices = [...leadRes.notices, ...folded.notices];
                assetMap.delete(member.fakeAssetId);
            }
        }

        // Rewriting the bindings through the map rather than per group is what keeps the two
        // representations from drifting: a row can only point at a fake id the map knows.
        for (const mt of txArr) {
            const current = (mt.tx as {asset_id?: number | null}).asset_id;
            if (typeof current !== 'number') continue;
            const survivor = survivorOf.get(current);
            if (survivor !== undefined && survivor !== current) (mt.tx as {asset_id?: number | null}).asset_id = survivor;
        }
    }

    /** Union of two candidate lists, keeping the strongest confidence seen for each asset. */
    /** Turns a per-row duplicate verdict into resolver groups and folds the panel sensibly. */
    function rebuildDuplicateGroups(txArr: MergedTx[], assetMap: Map<number, AssetResolution>) {
        const groups = buildDuplicateGroups(txArr, assetMap);
        duplicateGroups = groups;
        // Nothing partial to arbitrate ⇒ every group is a total overlap, which the resolver
        // already keeps one copy of. The panel stays available but folded, with a badge that
        // says so — showing an open resolver full of decisions that need no decision buries
        // the cases that do.
        duplicateResolverCollapsed = !groups.some((g) => g.tier === 'probable');
        expandedDuplicateTiers = new Set<DuplicateTier>();
        applyPendingDuplicateGroups(txArr, groups);
        markPendingBulkDuplicates(txArr, assetMap);
    }

    /**
     * Recomputes the duplicate verdict against the database using the transactions as they
     * stand now — corrections applied, fake asset ids replaced by the user's choices.
     *
     * The report returned by `/parse` answers the question "does the plugin's raw reading of
     * this file already exist?". After the user fixes a row that the plugin misread, that is
     * no longer the question being asked, so the answer is re-requested rather than reused.
     */
    async function refreshDuplicateReport(): Promise<void> {
        duplicateRecheckError = null;
        if (mergedTransactions.length === 0) {
            duplicateGroups = [];
            return;
        }

        // Duplicate detection is scoped to one broker, and an import can span several.
        const byBroker = new Map<number, MergedTx[]>();
        for (const m of mergedTransactions) {
            const brokerId = parseResults.find((r) => r.fileId === m.sourceFileId)?.brokerId;
            if (typeof brokerId !== 'number') continue;
            const list = byBroker.get(brokerId) ?? [];
            list.push(m);
            byBroker.set(brokerId, list);
        }
        if (byBroker.size === 0) return;

        const resolvedByFakeId = new Map<number, number>();
        for (const res of assetResolutions) {
            if (typeof res.resolvedAssetId === 'number') resolvedByFakeId.set(res.fakeAssetId, res.resolvedAssetId);
        }

        duplicateRecheckRunning = true;
        const verdict = new Map<number, {status: DuplicateStatus; matches: BrimDuplicateMatch[]}>();
        try {
            for (const [brokerId, rows] of byBroker) {
                // A row whose instrument is still unresolved is left out of the question
                // entirely — see `buildDuplicateRecheckPayload` for why.
                const asked = buildDuplicateRecheckPayload(rows, resolvedByFakeId, (t) => getTypeRule(t).assetField);
                if (asked.length === 0) continue;
                const report = await zodiosApi.check_duplicates_api_v1_brokers_import_duplicates_post({
                    broker_id: brokerId,
                    transactions: asked.map(({clone}) => clone) as never,
                });
                const pendingDeleteSet = new Set(pendingDeleteTxIds);
                const record = (entries: unknown[], status: DuplicateStatus) => {
                    for (const raw of entries as Array<{tx_row_index: number; tx_existing_matches?: BrimDuplicateMatch[]}>) {
                        const all = raw.tx_existing_matches ?? [];
                        const surviving = all.filter((mm) => !pendingDeleteSet.has(mm.existing_tx_id));
                        // Every DB match is queued for deletion ⇒ nothing left to collide with.
                        if (all.length > 0 && surviving.length === 0) continue;
                        const row = asked[raw.tx_row_index]?.row;
                        if (row) verdict.set(row.index, {status, matches: surviving});
                    }
                };
                record(report.tx_likely_duplicates ?? [], 'likely');
                record(report.tx_possible_duplicates ?? [], 'possible');
            }
        } catch (e) {
            // A failed re-check must not silently fall back to the stale verdict: say so and
            // keep what we have, so the user can still arbitrate manually.
            duplicateRecheckError = extractErrorMessage(e);
            duplicateRecheckRunning = false;
            return;
        }
        duplicateRecheckRunning = false;

        const assetMap = new Map<number, AssetResolution>(assetResolutions.map((r) => [r.fakeAssetId, r]));
        const txArr = mergedTransactions.map((m) => {
            const v = verdict.get(m.index);
            const status: DuplicateStatus = v?.status ?? 'unique';
            // Recomputed, not carried over: a correction can clear a false duplicate, and the
            // row must then become selectable again. Rows predating the broker's opening date
            // stay out either way.
            const openedAt = brokers.find((b) => b.id === parseResults.find((r) => r.fileId === m.sourceFileId)?.brokerId)?.opened_at ?? null;
            const beforeOpening = openedAt != null && String(m.tx.date ?? '') !== '' && String(m.tx.date ?? '') < openedAt;
            return {
                ...m,
                duplicateStatus: status,
                dupMatches: v?.matches ?? [],
                dupGroupKey: undefined,
                dupTier: undefined,
                dupKeeperIndex: undefined,
                dupKeeperFileName: undefined,
                isDupKeeper: undefined,
                dupPendingMatch: undefined,
                selected: !beforeOpening && duplicateStatusAllowsAutoSelect(status),
            } as MergedTx;
        });

        duplicateResolverTouchedKeys = new Set();
        duplicateResolverSelections = {};
        expandedDuplicateGroupKeys = new Set();
        rebuildDuplicateGroups(txArr, assetMap);
        mergedTransactions = txArr;
        duplicateRecheckDone = true;
    }

    function resolveAsset(fakeAssetId: number, realAssetId: number) {
        assetResolutions = assetResolutions.map((r) => (r.fakeAssetId === fakeAssetId ? {...r, resolvedAssetId: realAssetId} : r));
    }

    function clearResolution(fakeAssetId: number) {
        assetResolutions = assetResolutions.map((r) => (r.fakeAssetId === fakeAssetId ? {...r, resolvedAssetId: null} : r));
    }

    /**
     * Open the creation form for a resolution, electing the leading code first when the group
     * offers more than one and nobody has ruled yet.
     *
     * The unification step is where the choice belongs — the codes are on screen there, next to
     * the files that carried them. This prompt is the fallback for the user who walked past it.
     */
    function startCreateAsset(res: AssetResolution) {
        createPrimaryIsin = null;
        createPrimarySymbol = null;
        createAssetForFakeId = res.fakeAssetId;
        if (res.groupIsins.length > 1 && !res.groupPrimaryIsin) {
            createPrimaryPending = 'identifier_isin';
            identifierPromptPrimary = res.groupIsins[0];
        } else if (res.groupSymbols.length > 1 && !res.groupPrimarySymbol) {
            createPrimaryPending = 'identifier_ticker';
            identifierPromptPrimary = res.groupSymbols[0];
        } else {
            createPrimaryPending = null;
        }
    }

    /** Record the elected code and move on to the ticker if it too is contested. */
    function confirmCreatePrimary() {
        const res = assetResolutions.find((r) => r.fakeAssetId === createAssetForFakeId);
        if (!res) return;
        if (createPrimaryPending === 'identifier_isin') {
            createPrimaryIsin = identifierPromptPrimary;
            if (res.groupSymbols.length > 1 && !res.groupPrimarySymbol) {
                createPrimaryPending = 'identifier_ticker';
                identifierPromptPrimary = res.groupSymbols[0];
                return;
            }
        } else if (createPrimaryPending === 'identifier_ticker') {
            createPrimarySymbol = identifierPromptPrimary;
        }
        createPrimaryPending = null;
    }

    /**
     * Wizard create flow: the user selected a search result whose provider name matches an
     * existing asset and chose to reuse it (instead of creating a duplicate). Bind the fake id
     * to the existing asset and, if requested, merge the import's identity into it.
     *
     * "Search keys" used to mean names only, so the ISIN and the ticker the report carried were
     * dropped on the floor — and the next import of the same file asked the very same question
     * again. They now go through the identifier prompt, which knows the difference between a code
     * the asset is *missing* (it becomes the primary: an asset with no ISIN cannot be quoted) and
     * one that *competes* with a code it already holds (the user elects, nothing is lost).
     */
    async function reuseExistingForCreate(existingAssetId: number, addKeys: boolean) {
        const fakeId = createAssetForFakeId;
        if (fakeId === null) return;
        const res = assetResolutions.find((r) => r.fakeAssetId === fakeId);
        resolveAsset(fakeId, existingAssetId);
        createAssetForFakeId = null;
        if (!addKeys || !res) {
            await refreshCandidates(fakeId);
            return;
        }
        await checkAndPromptIdentifier(fakeId, existingAssetId, res, {clearOnCancel: false, extraOther: createNamesFor(res)});
    }

    /** Asset offered for folding in the merge modal, opened from a resolution card. */
    let mergeSourceAsset = $state<{id: number; display_name: string} | null>(null);
    let mergeForFakeAssetId = $state<number | null>(null);

    function openMergeFromCard(res: AssetResolution) {
        const strong = duplicateCandidates(res);
        // Fold the one the user is *not* keeping: the bound asset is their stated answer.
        const source = strong.find((c) => c.asset_id !== res.resolvedAssetId) ?? strong[1];
        if (!source) return;
        mergeForFakeAssetId = res.fakeAssetId;
        mergeSourceAsset = {id: source.asset_id, display_name: source.name ?? source.isin ?? `#${source.asset_id}`};
    }

    async function onCardMerged(targetId: number) {
        const fakeId = mergeForFakeAssetId;
        mergeSourceAsset = null;
        mergeForFakeAssetId = null;
        if (fakeId === null) return;
        resolveAsset(fakeId, targetId);
        await refreshCandidates(fakeId);
    }

    /**
     * Replace candidates for a specific fakeAssetId with fresh results from the backend.
     * Called after an asset's identifier is updated so confidence reflects current DB state.
     */
    async function refreshCandidates(fakeAssetId: number) {
        const res = assetResolutions.find((r) => r.fakeAssetId === fakeAssetId);
        if (!res) return;
        try {
            // Search on every code the group carries, not just the representative's. A unified
            // bond holds its issue code and its quoted one; querying one of them would quietly
            // narrow the very union the unification step just built.
            const isins = res.groupIsins.length > 0 ? res.groupIsins : [res.extractedIsin ?? ''];
            const symbols = res.groupSymbols.length > 0 ? res.groupSymbols : [res.extractedSymbol ?? ''];
            const queries = Math.max(isins.length, symbols.length);
            let fresh: Awaited<ReturnType<typeof zodiosApi.get_asset_candidates_api_v1_brokers_import_asset_candidates_post>> = [];
            for (let i = 0; i < queries; i++) {
                const batch = await zodiosApi.get_asset_candidates_api_v1_brokers_import_asset_candidates_post({
                    extracted_symbol: symbols[i] || undefined,
                    extracted_isin: isins[i] || undefined,
                    extracted_name: res.extractedName ?? undefined,
                });
                fresh = [...fresh, ...batch];
            }
            // Sort by confidence and replace candidates in state
            const seenAssetIds = new Set<number>();
            const sorted: AssetResolution['candidates'] = [...fresh]
                .sort((a, b) => (CONF_ORDER[a.match_confidence] ?? 9) - (CONF_ORDER[b.match_confidence] ?? 9))
                .filter((c) => {
                    // Sorted first, so the entry kept is the strongest confidence for that asset.
                    if (seenAssetIds.has(c.asset_id)) return false;
                    seenAssetIds.add(c.asset_id);
                    return true;
                })
                .map((c) => ({asset_id: c.asset_id, symbol: (Array.isArray(c.symbol) ? (c.symbol[0] ?? null) : c.symbol) as string | null, isin: (Array.isArray(c.isin) ? (c.isin[0] ?? null) : c.isin) as string | null, name: c.name, match_confidence: c.match_confidence as string}));
            assetResolutions = assetResolutions.map((r) => {
                if (r.fakeAssetId !== fakeAssetId) return r;
                // If still unresolved and a fresh identifier edit produced a lone exact match, auto-bind it.
                const autoBind = r.resolvedAssetId == null ? uniqueExactCandidateId(sorted) : null;
                return {...r, candidates: sorted, resolvedAssetId: r.resolvedAssetId ?? autoBind};
            });
        } catch {
            // Silently ignore — old candidates remain visible
        }
    }

    /**
     * Called when the user manually picks an existing asset via AssetSelect (not a candidate chip).
     * Resolves the asset and, if the selected asset is missing the extracted identifier, opens the
     * "add identifier" prompt.
     */
    async function resolveAssetManual(fakeAssetId: number, realAssetId: number, res: AssetResolution) {
        resolveAsset(fakeAssetId, realAssetId);
        await checkAndPromptIdentifier(fakeAssetId, realAssetId, res);
    }

    /**
     * Check if a resolved asset is missing the extracted identifier and, if so, open the prompt.
     * Shared by resolveAssetManual, the oncreated callback and the reuse-existing flow.
     *
     * `extraOther` are search keys to merge in the same PATCH as the decision; when there is
     * nothing to decide they are still written, silently, because the user already asked for them.
     */
    async function checkAndPromptIdentifier(fakeAssetId: number, realAssetId: number, res: AssetResolution, options: {clearOnCancel?: boolean; extraOther?: string[]; settled?: string[]} = {}) {
        let info = getAssetInfo(realAssetId);
        if (!info) {
            await refreshAllAssets();
            info = getAssetInfo(realAssetId);
            if (!info) return;
        }
        const settled = options.settled ?? [];
        const extraOther = options.extraOther ?? [];
        const currentOther: string[] = Array.isArray(info.identifier_other) ? (info.identifier_other as string[]) : [];
        // The whole group speaks, not just its representative: a unified BTP carries the CUM code
        // and the quoted one, and offering only one of them would silently drop the other.
        // ISIN before ticker: it is the more precise of the two, and one question at a time.
        const isins = res.groupIsins.length > 0 ? res.groupIsins : [res.extractedIsin];
        const symbols = res.groupSymbols.length > 0 ? res.groupSymbols : [res.extractedSymbol];
        const pending = (settled.includes('identifier_isin') ? null : pendingIdentifier(isins, info.identifier_isin, currentOther, 'identifier_isin')) ?? (settled.includes('identifier_ticker') ? null : pendingIdentifier(symbols, info.identifier_ticker, currentOther, 'identifier_ticker'));

        if (!pending) {
            // Nothing to decide — but the search keys still have to land somewhere.
            await mergeSearchKeys(realAssetId, currentOther, extraOther);
            await refreshCandidates(fakeAssetId);
            return;
        }

        identifierPromptAssetId = realAssetId;
        identifierPromptFakeAssetId = fakeAssetId;
        identifierPromptField = pending.field;
        identifierPromptValues = pending.extracted;
        identifierPromptAssetName = info.display_name ?? `#${realAssetId}`;
        identifierPromptIsConflict = needsPrimaryChoice(pending);
        identifierPromptExistingValue = pending.existing;
        identifierPromptExistingOther = currentOther;
        identifierPromptExtraOther = extraOther;
        identifierPromptSettled = settled;
        // Default to what the asset already holds: the stored code is usually the quoted one,
        // and demoting it without being asked is exactly the destructive act being removed here.
        identifierPromptPrimary = pending.existing ?? pending.extracted[0];
        identifierPromptClearOnCancel = options.clearOnCancel ?? true;
        identifierPromptOpen = true;
    }

    /** Merge leftover search keys when the prompt had nothing to ask. The PATCH replaces the list. */
    async function mergeSearchKeys(assetId: number, currentOther: string[], extra: string[]) {
        const merged = mergeOther(currentOther, extra);
        if (merged.length === currentOther.length) return;
        try {
            await zodiosApi.patch_assets_bulk_api_v1_assets_patch([{asset_id: assetId, identifier_other: merged}]);
            toasts.success($t('importWizard.reuseExisting.success'));
            await refreshAllAssets();
        } catch {
            toasts.error($t('importWizard.reuseExisting.error'));
        }
    }

    /**
     * Confirm the prompt: a single PATCH writes the elected primary and the full alternate list.
     *
     * Nothing is dropped. Whatever the user did not elect lands in `identifier_other`, where it no
     * longer quotes but still *recognises* — which is what makes a dual-ISIN bond resolvable from
     * either code on any future import. Then the store is refreshed (so the new code is visible to
     * AssetSelect and to the second pass) and the candidates are re-queried, so confidence comes
     * from the database rather than from an assumption.
     */
    async function confirmAddIdentifier() {
        const assetId = identifierPromptAssetId;
        const field = identifierPromptField;
        const extracted = identifierPromptValues;
        const fakeId = identifierPromptFakeAssetId;
        if (assetId === null || !field || extracted.length === 0 || fakeId === null) return;

        const primary = identifierPromptPrimary ?? extracted[0];
        const demoted = demotedValues(primary, [identifierPromptExistingValue, ...extracted]);
        const other = mergeOther(identifierPromptExistingOther, [...demoted, ...identifierPromptExtraOther]);

        const res = assetResolutions.find((r) => r.fakeAssetId === fakeId);
        const settled = [...identifierPromptSettled, field];
        const clearOnCancel = identifierPromptClearOnCancel;
        identifierPromptSaving = true;
        try {
            await zodiosApi.patch_assets_bulk_api_v1_assets_patch([{asset_id: assetId, [field]: primary, identifier_other: other}]);
            toasts.success($t('importWizard.addIdentifier.success'));
            await refreshAllAssets();
            identifierPromptSaving = false;
            identifierPromptOpen = false;
            // A report can quote both an ISIN and a ticker; this pass settled one of the two.
            if (res) await checkAndPromptIdentifier(fakeId, assetId, res, {clearOnCancel, settled});
            else await refreshCandidates(fakeId);
        } catch {
            toasts.error($t('importWizard.addIdentifier.error'));
            identifierPromptSaving = false;
            identifierPromptOpen = false;
        }
    }

    /**
     * Cancel. Reaching the prompt by picking an asset from the list means cancelling is "wrong
     * asset", so the row goes back to unresolved instead of silently keeping a binding the user
     * just backed out of.
     */
    function cancelAddIdentifier() {
        const fakeId = identifierPromptFakeAssetId;
        const clear = identifierPromptClearOnCancel;
        identifierPromptOpen = false;
        if (clear && fakeId !== null) clearResolution(fakeId);
    }

    /**
     * Keep the binding, decline the identifier — but still write the search keys. The user asked
     * for those when they chose to reuse the asset, and declining one question is not declining
     * both. Cancel is the gesture that discards everything.
     */
    async function skipAddIdentifier() {
        const fakeId = identifierPromptFakeAssetId;
        const assetId = identifierPromptAssetId;
        const currentOther = identifierPromptExistingOther;
        const extra = identifierPromptExtraOther;
        identifierPromptOpen = false;
        if (assetId !== null && extra.length > 0) await mergeSearchKeys(assetId, currentOther, extra);
        if (fakeId !== null) await refreshCandidates(fakeId);
    }

    function buildFinalTxList(): Array<{tx: TransactionCreateItem; todos: ImportTodo[]}> {
        return mergedTransactions
            .filter((t) => t.selected && !beforeOpeningIndices.has(t.index))
            .map((t) => {
                const tx = {...t.tx} as any;
                const assetId = typeof tx.asset_id === 'number' ? tx.asset_id : null;
                if (assetId !== null && isFakeAssetId(assetId)) {
                    const res = assetResolutions.find((r) => r.fakeAssetId === assetId);
                    if (res?.resolvedAssetId) tx.asset_id = res.resolvedAssetId;
                }
                return {tx: tx as TransactionCreateItem, todos: t.todos};
            });
    }

    function handleImport() {
        const creates = buildFinalTxList();
        onImportBatch(creates);
    }

    /**
     * The one name a unified group answers to, everywhere it is shown.
     *
     * Order matters and is not arbitrary: the archive's own name wins once the group is bound,
     * because that is the name the user will see forever after; then the name elected (or typed)
     * on the unification step; only last the raw extraction of whichever file happened to be
     * first. Labelling by the raw extraction is what made the corrections step look like it was
     * still offering the pre-unification assets.
     */
    function resolutionLabel(res: AssetResolution): string {
        // Pure label logic lives in importResolutionHelpers; inject the store's display-name lookup.
        return resolutionLabelPure(res, (id) => getAssetInfo(id)?.display_name);
    }

    function getAssetDisplayName(assetId: number | null | undefined): string {
        if (assetId == null) return '—';
        if (isFakeAssetId(assetId)) {
            const res = assetResolutions.find((r) => r.fakeAssetId === assetId);
            return res ? resolutionLabel(res) : `#${assetId}`;
        }
        return getAssetInfo(assetId)?.display_name ?? `#${assetId}`;
    }

    function getSourceFileName(fileId: string): string {
        return parseResults.find((r) => r.fileId === fileId)?.fileName ?? fileId;
    }

    function getDuplicateGroupTitle(group: DuplicateGroup): string {
        const first = mergedTransactions.find((mt) => mt.index === group.memberIndices[0]);
        if (!first) return group.key;
        const description = String(first.tx.description ?? '').trim();
        if (description) return description;
        return getAssetDisplayName(typeof first.tx.asset_id === 'number' ? first.tx.asset_id : null);
    }

    /**
     * Badge colour by overlap tier — semantics are *safety*, not severity:
     *  - `sure`     = total overlap → green: keeping one copy is the safe, obvious call.
     *  - `probable` = partial overlap → orange: the rows only partly match, so the
     *                 automatic choice may be wrong and deserves a look.
     */
    function duplicateTierBadgeClass(tier: DuplicateTier): string {
        return tier === 'sure' ? 'bg-emerald-100 text-emerald-800 ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-700' : 'bg-orange-100 text-orange-800 ring-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:ring-orange-700';
    }

    function toggleDuplicateGroup(groupKey: string) {
        const next = new Set(expandedDuplicateGroupKeys);
        if (next.has(groupKey)) next.delete(groupKey);
        else next.add(groupKey);
        expandedDuplicateGroupKeys = next;
    }

    /**
     * Svelte action: attach the auto-scrolling marquee to overflowing text cells (file name,
     * description) rendered as raw HTML inside a member DataTable — mirrors the asset-name
     * marquee used across the main tables. The container's MutationObserver re-attaches on
     * every DataTable re-render (sort, resolver recompute).
     */
    function marqueeDescendants(node: HTMLElement) {
        const dispose = attachOverflowMarqueeToDescendants(node);
        return {destroy: dispose};
    }

    /** Discrete overlap-similarity label for a group header (Totale / Parziale). */
    function duplicateSimilarityLabel(tier: DuplicateTier): string {
        return tier === 'sure' ? $t('importWizard.resolver.similarityTotal') : $t('importWizard.resolver.similarityPartial');
    }

    function toggleDuplicateTier(tier: DuplicateTier) {
        const next = new Set(expandedDuplicateTiers);
        if (next.has(tier)) next.delete(tier);
        else next.add(tier);
        expandedDuplicateTiers = next;
    }

    /**
     * Drop every manual resolver choice so keepers recompute from the current file priority.
     * Step-3 member checkboxes read `resolverSelectionFor` live; step-4 recomputes on entry.
     */
    function recalcResolverDefaults() {
        duplicateResolverTouchedKeys = new Set();
        duplicateResolverSelections = {};
        reapplyResolverGroups();
    }

    /** Members of a duplicate group as MergedTx rows, in group order. */
    function resolverGroupMembers(group: DuplicateGroup): MergedTx[] {
        return group.memberIndices.map((idx) => mergedTransactions.find((mt) => mt.index === idx)).filter((mt): mt is MergedTx => mt !== undefined);
    }

    /**
     * Transaction-style columns for the in-group member table (DataTable), mirroring the main
     * transactions page (type icon, cash formatting) plus a keeper checkbox and a File column.
     * A function (not a derived) so the keeper column can close over the specific group.
     */
    function resolverMemberColumns(group: DuplicateGroup): ColumnDef<MergedTx>[] {
        const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const cmpMembers = resolverGroupMembers(group);
        const descOutliers = outlierIndexSet(cmpMembers, (mt) =>
            String(mt.tx.description ?? '')
                .trim()
                .toLowerCase()
                .replace(/\s+/g, ''),
        );
        const cashOutliers = outlierIndexSet(cmpMembers, (mt) => {
            const cash = mt.tx.cash;
            if (cash && typeof cash === 'object' && !Array.isArray(cash)) {
                const c = cash as {code: string; amount: string};
                return `${Number(c.amount).toFixed(2)}|${c.code}`;
            }
            return '';
        });
        const diffCls = ' rounded bg-amber-100/70 px-1 dark:bg-amber-900/40';
        return [
            {
                id: 'keep',
                header: () => $t('importWizard.resolver.keepColumn'),
                displayName: () => $t('importWizard.resolver.keepColumn'),
                type: 'custom',
                sortable: false,
                filterable: false,
                width: 84,
                minWidth: 64,
                align: 'center' as const,
                pinned: 'left' as const,
                cell: (mt) => ({
                    type: 'editable-checkbox',
                    value: resolverSelectionFor(group, mt.index),
                    onchange: (v: boolean) => applyDuplicateResolverChoice(group, mt.index, v),
                    testId: `import-wizard-resolver-keep-${mt.index}`,
                }),
            },
            {
                id: 'role',
                header: '',
                type: 'custom',
                sortable: false,
                filterable: false,
                width: 104,
                minWidth: 80,
                cell: (mt) => {
                    if (defaultKeeperIndices(group).has(mt.index)) {
                        return {type: 'html', html: `<span class="inline-block rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">${$t('importWizard.resolver.defaultKeeper')}</span>`};
                    }
                    return {type: 'html', html: `<span class="inline-block rounded-full bg-orange-100 px-1.5 py-0.5 text-[10px] font-medium text-orange-700 dark:bg-orange-900/30 dark:text-orange-300">${$t('importWizard.resolver.duplicateBadge')}</span>`};
                },
            },
            {
                id: 'date',
                header: () => $t('common.date'),
                type: 'date',
                sortable: true,
                filterable: false,
                width: 116,
                minWidth: 96,
                getValue: (mt) => String(mt.tx.date ?? ''),
                cell: (mt) => ({type: 'date', value: mt.tx.date ?? '', format: 'date'}),
            },
            {
                id: 'type',
                header: () => $t('common.type'),
                type: 'text',
                sortable: true,
                filterable: false,
                width: 140,
                minWidth: 100,
                getValue: (mt) => String(mt.tx.type ?? ''),
                cell: (mt) => {
                    const type = String(mt.tx.type ?? '');
                    const slug = type.toLowerCase().replace(/_/g, '-');
                    const label = $t(`transactions.types.${type}`) || type;
                    const isPair = getTypeRule(type).requiresPair;
                    const arrow = isPair ? '<span class="shrink-0 mr-0.5">↔</span>' : '';
                    return {
                        type: 'html',
                        html: `<span class="inline-flex items-center gap-1.5 text-xs leading-snug"><img src="/icons/transactions/${slug}.png" alt="" style="width:1.5rem;height:1.5rem" class="object-contain shrink-0" onerror="this.style.display='none'"/>${arrow}<span>${esc(label)}</span></span>`,
                    };
                },
            },
            {
                id: 'cash',
                header: () => $t('common.cash'),
                type: 'text',
                sortable: true,
                filterable: false,
                width: 150,
                minWidth: 120,
                align: 'right' as const,
                getValue: (mt) => {
                    const cash = mt.tx.cash;
                    return cash && typeof cash === 'object' && !Array.isArray(cash) ? Number((cash as {amount: string}).amount) : 0;
                },
                cell: (mt) => {
                    const cash = mt.tx.cash;
                    const hl = cashOutliers.has(mt.index) ? diffCls : '';
                    if (cash && typeof cash === 'object' && !Array.isArray(cash)) {
                        const c = cash as {code: string; amount: string};
                        return {type: 'html', html: `<span class="inline-block${hl}">${formatCurrencyAmountHtml(Number(c.amount), c.code, {showSign: true})}</span>`};
                    }
                    return {type: 'html', html: `<span class="text-gray-400${hl}">—</span>`};
                },
            },
            {
                id: 'sourceFileId',
                header: () => $t('importWizard.sourceFile'),
                displayName: () => $t('importWizard.sourceFile'),
                type: 'text',
                sortable: true,
                filterable: false,
                width: 170,
                minWidth: 130,
                getValue: (mt) => getSourceFileName(mt.sourceFileId),
                cell: (mt) => ({type: 'html', html: `<span class="${overflowScrollTextClass} text-xs text-gray-600 dark:text-gray-300" title="${esc(getSourceFileName(mt.sourceFileId))}">${esc(getSourceFileName(mt.sourceFileId))}</span>`}),
            },
            {
                id: 'description',
                header: () => $t('common.description'),
                type: 'text',
                sortable: false,
                filterable: false,
                minWidth: 200,
                getValue: (mt) => String(mt.tx.description ?? ''),
                cell: (mt) => {
                    const raw = String(mt.tx.description ?? '').trim();
                    const hl = descOutliers.has(mt.index) ? diffCls : '';
                    return {type: 'html', html: `<span class="${overflowScrollTextClass} text-xs text-gray-800 dark:text-gray-100${hl}" title="${esc(raw)}">${esc(raw || '—')}</span>`};
                },
            },
        ];
    }

    function confidenceBadgeClass(conf: string): string {
        if (conf === 'exact') return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300';
        if (conf === 'high') return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
        if (conf === 'medium') return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
        return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
    }

    // ── N-way compare: shared source/cell/column builders ───────────────────

    /** Build the per-field comparison cells (display + normalized cmp token) for one column. */
    function buildCompareCells(src: CmpSource): Record<string, CompareCell> {
        const amountCell: CompareCell = src.cashAmount != null ? {display: formatCurrencyAmountHtml(src.cashAmount, src.cashCode ?? '', {showSign: true}), cmp: `${src.cashAmount.toFixed(2)}|${src.cashCode ?? ''}`, html: true} : {display: '—', cmp: ''};
        const assetName = getAssetDisplayName(src.assetId);
        return {
            date: {display: src.date || '—', cmp: src.date},
            type: src.type ? {display: compareTypeCellHtml(src.type, $t(`transactions.types.${src.type}`) || src.type), cmp: src.type, html: true} : {display: '—', cmp: ''},
            amount: amountCell,
            broker: src.brokerId != null ? {display: getBrokerName(src.brokerId), cmp: String(src.brokerId)} : {display: '—', cmp: ''},
            asset: {display: assetName, cmp: `${src.assetId ?? ''}|${assetName.toLowerCase()}`},
            // Compared whitespace-insensitively, like the duplicate matcher: a description
            // re-wrapped by the bank is the same text and must not be flagged as a difference.
            description: {display: src.description.trim() || '—', cmp: src.description.toLowerCase().replace(/\s+/g, '')},
        };
    }

    function compareFieldDefs(): CompareField[] {
        return [
            {key: 'date', label: $t('common.date')},
            {key: 'type', label: $t('common.type')},
            // Left-aligned like every other field: the columns are transactions, not a
            // ledger, so nothing lines up under an amount to be read against it.
            {key: 'amount', label: $t('common.amount')},
            {key: 'broker', label: $t('common.broker')},
            {key: 'asset', label: $t('common.asset')},
            {key: 'description', label: $t('common.description')},
            {key: 'file', label: $t('importWizard.sourceFile')},
        ];
    }

    /** A non-diffing provenance cell (the file column never counts as a "difference"). */
    function fileCell(label: string): CompareCell {
        return {display: label, cmp: ''};
    }

    function columnFromMergedTx(mt: MergedTx): CompareColumn {
        const fileName = getSourceFileName(mt.sourceFileId);
        return {
            id: String(mt.index),
            title: fileName,
            selectable: true,
            cells: {...buildCompareCells(cmpSourceFromTx(mt.tx, getBrokerIdForTx(mt))), file: fileCell(fileName)},
        };
    }

    /** Compare all members of an in-batch duplicate group (opened from step 3 or a step-4 badge). */
    function openLotCompare(group: DuplicateGroup) {
        const members = resolverGroupMembers(group);
        if (members.length < 2) return;
        nwCompareFields = compareFieldDefs();
        nwCompareColumns = members.map(columnFromMergedTx);
        nwCompareDefaultKept = members.filter((mt) => resolverSelectionFor(group, mt.index)).map((mt) => String(mt.index));
        nwCompareResetKept = [...defaultKeeperIndices(group)].map((i) => String(i));
        nwCompareOnKeep = (keptIds: string[]) => applyLotCompareKeep(group, keptIds);
        nwCompareTitle = `🔍 ${$t('importWizard.compareModal.title', {values: {n: members.length}})}`;
        nwCompareHint = $t('importWizard.compareModal.hint');
        nwCompareOpen = true;
    }

    /** Apply a "keep which" choice from the compare modal back to the resolver selection. */
    function applyLotCompareKeep(group: DuplicateGroup, keptIds: string[]) {
        const keep = new Set(keptIds);
        const next = {...duplicateResolverSelections};
        for (const idx of group.memberIndices) {
            next[idx] = keep.has(String(idx));
        }
        duplicateResolverSelections = next;
        duplicateResolverTouchedKeys = new Set(duplicateResolverTouchedKeys).add(group.key);
        reapplyResolverGroups();
    }

    /** Compare a bulk-modal pending duplicate against the matched unsaved transaction. */
    function openPendingCompare(mt: MergedTx) {
        const match = mt.dupPendingMatch;
        if (!match) return;
        const pendingLabel = $t('importWizard.resolver.pendingEditor');
        const fileName = getSourceFileName(mt.sourceFileId);
        nwCompareFields = compareFieldDefs();
        nwCompareColumns = [
            {id: String(mt.index), title: fileName, selectable: false, cells: {...buildCompareCells(cmpSourceFromTx(mt.tx, getBrokerIdForTx(mt))), file: fileCell(fileName)}},
            {id: 'pending', title: pendingLabel, selectable: false, cells: {...buildCompareCells(cmpSourceFromTx(match)), file: fileCell(pendingLabel)}},
        ];
        nwCompareDefaultKept = undefined;
        nwCompareResetKept = undefined;
        nwCompareOnKeep = undefined;
        nwCompareTitle = `🔍 ${$t('importWizard.compareModal.title', {values: {n: 2}})}`;
        nwCompareHint = $t('importWizard.compareModal.hint');
        nwCompareOpen = true;
    }

    /**
     * Compare a parsed row against the existing transaction already in the database
     * (⚠ likely / ℹ possible). Fetches the existing tx from the store or API.
     */
    async function openDbCompare(mt: MergedTx) {
        if (!mt.dupMatches.length) return;
        const existingId = mt.dupMatches[0].existing_tx_id;
        let existing: TXReadItem | undefined = txStoreGet(existingId);
        if (!existing) {
            try {
                const results = (await zodiosApi.query_transactions_api_v1_transactions_get({
                    queries: {ids: [existingId], limit: 1},
                })) as unknown as TXReadItem[];
                existing = results[0] ?? undefined;
            } catch {
                toasts.error(`Could not load transaction #${existingId}`);
                return;
            }
        }
        if (!existing) {
            toasts.error(`Transaction #${existingId} not found`);
            return;
        }
        const fileName = getSourceFileName(mt.sourceFileId);
        const dbLabel = $t('importWizard.compareModal.dbColumn', {values: {id: String(existingId)}});
        nwCompareFields = compareFieldDefs();
        nwCompareColumns = [
            {id: String(mt.index), title: fileName, selectable: false, cells: {...buildCompareCells(cmpSourceFromTx(mt.tx, getBrokerIdForTx(mt))), file: fileCell(fileName)}},
            {id: `db-${existingId}`, title: dbLabel, selectable: false, cells: {...buildCompareCells(cmpSourceFromExisting(existing)), file: fileCell('—')}},
        ];
        nwCompareDefaultKept = undefined;
        nwCompareResetKept = undefined;
        nwCompareOnKeep = undefined;
        nwCompareTitle = `🔍 ${$t('importWizard.compareModal.title', {values: {n: 2}})}`;
        nwCompareHint = $t('importWizard.compareModal.hint');
        nwCompareOpen = true;
    }

    /** Dispatch a step-4 status-badge click to the right comparison view. */
    function openBadgeCompare(mt: MergedTx) {
        if (mt.dupGroupKey != null) {
            const group = duplicateGroups.find((g) => g.key === mt.dupGroupKey);
            if (group) {
                openLotCompare(group);
                return;
            }
        }
        if (mt.dupPendingMatch) {
            openPendingCompare(mt);
            return;
        }
        void openDbCompare(mt);
    }

    async function openBrokerOpeningEdit(mt: MergedTx) {
        const brokerId = getBrokerIdForTx(mt);
        if (brokerId === null) return;
        await openBrokerOpeningEditById(brokerId);
    }

    async function openBrokerOpeningEditById(brokerId: number) {
        let broker = getBrokerInfo(brokerId) ?? brokers.find((b) => b.id === brokerId) ?? null;
        if (!broker) {
            await refreshAllBrokers();
            brokers = getEditableBrokers();
            broker = getBrokerInfo(brokerId) ?? brokers.find((b) => b.id === brokerId) ?? null;
        }
        if (!broker) return;

        editBrokerId = brokerId;
        editBrokerInitialData = {
            name: broker.name,
            description: broker.description ?? null,
            portal_url: broker.portal_url ?? null,
            icon_url: broker.icon_url ?? null,
            default_import_plugin: broker.default_import_plugin ?? null,
            allow_cash_overdraft: broker.allow_cash_overdraft,
            allow_asset_shorting: broker.allow_asset_shorting,
            is_active: broker.is_active,
            opened_at: broker.opened_at ?? null,
        };
        editBrokerOpen = true;
    }

    async function refreshEditableBrokers() {
        await refreshAllBrokers();
        brokers = getEditableBrokers();
    }

    /**
     * Re-evaluate the opening-date gate after a broker's opening date was edited.
     * Refreshes the broker list (so `beforeOpeningIndices` recomputes) and re-selects rows
     * that just became importable (no longer before-opening and not a likely duplicate).
     */
    let recheckingOpenings = $state(false);

    async function recheckOpenings() {
        recheckingOpenings = true;
        try {
            await refreshEditableBrokers();
            mergedTransactions = mergedTransactions.map((t) => (!isBeforeOpening(t) && isRowAssetResolved(t) && !t.selected && duplicateStatusAllowsAutoSelect(t.duplicateStatus) ? {...t, selected: true} : t));
        } finally {
            recheckingOpenings = false;
        }
    }

    let autoFixingBrokerId = $state<number | null>(null);

    /**
     * Auto-fix a broker's opening-date gate: set `opened_at` to the broker's
     * earliest transaction date, then recheck so its rows become importable.
     */
    async function autoFixBrokerOpening(issue: BrokerOpeningIssue) {
        if (!issue.minTxDate || autoFixingBrokerId !== null) return;
        autoFixingBrokerId = issue.brokerId;
        try {
            const result = await trySave(() => zodiosApi.update_broker_api_v1_brokers__broker_id__patch({opened_at: issue.minTxDate}, {params: {broker_id: issue.brokerId}}), {fallback: $t('importWizard.autoFixFailed')});
            if (result.status === 'success') await recheckOpenings();
        } finally {
            autoFixingBrokerId = null;
        }
    }

    /**
     * Normalize a transaction's `tags` into a clean `string[]`.
     * The generated `TXCreateItem.tags` type is a Zodios union
     * (`string[] | (string[] | null)[] | null`); at runtime BRIM plugins always
     * emit a flat list of strings, so we keep only the string entries.
     */
    function txTagsToArray(tags: TransactionCreateItem['tags']): string[] {
        if (Array.isArray(tags)) return tags.filter((t): t is string => typeof t === 'string');
        return [];
    }

    let step4Columns = $derived.by<ColumnDef<MergedTx>[]>(() => {
        const doneFilesCount = parseResults.filter((r) => r.status === 'done').length;
        const columns: ColumnDef<MergedTx>[] = [
            {
                id: 'status',
                header: () => $t('common.status'),
                displayName: () => $t('common.status'),
                headerHtml: () => `<span class="hidden sm:inline">${$t('common.status')}</span>`,
                type: 'enum',
                sortable: true,
                filterable: true,
                width: 170,
                minWidth: 130,
                align: 'center' as const,
                pinned: 'left' as const,
                sortFn: (a: MergedTx, b: MergedTx) => {
                    const order = {before_opening: 0, unresolved: 1, pending_duplicate: 2, pending_possible_duplicate: 3, likely: 4, possible: 5, unique: 6};
                    const aKey = (() => {
                        if (beforeOpeningIndices.has(a.index)) return 'before_opening';
                        const id = typeof a.tx.asset_id === 'number' ? a.tx.asset_id : null;
                        if (id !== null && isFakeAssetId(id) && !assetResolutions.find((r) => r.fakeAssetId === id)?.resolvedAssetId) return 'unresolved';
                        return a.duplicateStatus;
                    })();
                    const bKey = (() => {
                        if (beforeOpeningIndices.has(b.index)) return 'before_opening';
                        const id = typeof b.tx.asset_id === 'number' ? b.tx.asset_id : null;
                        if (id !== null && isFakeAssetId(id) && !assetResolutions.find((r) => r.fakeAssetId === id)?.resolvedAssetId) return 'unresolved';
                        return b.duplicateStatus;
                    })();
                    return (order[aKey as keyof typeof order] ?? 3) - (order[bKey as keyof typeof order] ?? 3);
                },
                getValue: (mt) => {
                    if (beforeOpeningIndices.has(mt.index)) return 'before_opening';
                    const assetId = typeof mt.tx.asset_id === 'number' ? mt.tx.asset_id : null;
                    if (assetId !== null && isFakeAssetId(assetId) && !assetResolutions.find((r) => r.fakeAssetId === assetId)?.resolvedAssetId) return 'unresolved';
                    return mt.duplicateStatus as string;
                },
                enumOptions: [
                    {value: 'unique', label: $t('importWizard.status.unique')},
                    {value: 'possible', label: $t('importWizard.status.possibleDup')},
                    {value: 'likely', label: $t('importWizard.status.likelyDup')},
                    {value: 'pending_duplicate', label: $t('importWizard.status.pendingDuplicate')},
                    {value: 'pending_possible_duplicate', label: $t('importWizard.status.possiblePendingDuplicate')},
                    {value: 'unresolved', label: $t('importWizard.status.unresolved')},
                    {value: 'before_opening', label: $t('importWizard.status.beforeOpening')},
                ],
                cell: (mt) => {
                    if (beforeOpeningIndices.has(mt.index)) {
                        return {
                            type: 'html',
                            html: `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200 cursor-pointer"><span>⛔</span><span class="hidden sm:inline">${$t('importWizard.status.beforeOpening')}</span><span class="text-gray-500 dark:text-gray-300">· ${$t('importWizard.status.editBrokerDate')}</span></span>`,
                            tooltip: {text: $t('importWizard.status.tooltip.beforeOpening'), position: 'top', maxWidth: '280px'},
                            onClick: () => openBrokerOpeningEdit(mt),
                            testId: `import-wizard-edit-broker-opening-${mt.index}`,
                        };
                    }
                    const assetId = typeof mt.tx.asset_id === 'number' ? mt.tx.asset_id : null;
                    const isUnresolved = assetId !== null && isFakeAssetId(assetId) && assetResolutions.find((r) => r.fakeAssetId === assetId)?.resolvedAssetId == null;
                    if (isUnresolved) {
                        return {
                            type: 'html',
                            html: `<span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"><span class="sm:hidden">✗</span><span class="hidden sm:inline">${$t('importWizard.status.unresolved')}</span></span>`,
                            tooltip: {
                                html: `<strong>${$t('importWizard.status.tooltip.unresolvedReason')}</strong> ${$t('importWizard.status.tooltip.unresolvedAction')}`,
                                position: 'top',
                                maxWidth: '280px',
                            },
                        };
                    }
                    const dupLabels = {date: $t('common.date'), type: $t('common.type'), amount: $t('common.amount'), desc: $t('common.description')};
                    if (mt.duplicateStatus === 'likely') {
                        return {
                            type: 'html',
                            html: `<span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 cursor-pointer"><span class="sm:hidden">⚠</span><span class="hidden sm:inline">${$t('importWizard.status.likelyDup')}</span></span>`,
                            tooltip: {text: $t('importWizard.compareModal.openHint'), position: 'top', maxWidth: '260px'},
                            onClick: () => openBadgeCompare(mt),
                            testId: `import-wizard-compare-${mt.index}`,
                        };
                    }
                    if (mt.duplicateStatus === 'pending_duplicate') {
                        return {
                            type: 'html',
                            html: `<span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap bg-orange-100 text-orange-800 ring-1 ring-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:ring-orange-700 cursor-pointer"><span class="sm:hidden">⧉</span><span class="hidden sm:inline">${$t('importWizard.status.pendingDuplicate')}</span></span>`,
                            tooltip: {text: $t('importWizard.status.tooltip.pendingDuplicate'), position: 'top', maxWidth: '300px'},
                            onClick: () => openBadgeCompare(mt),
                            testId: `import-wizard-compare-${mt.index}`,
                        };
                    }
                    if (mt.duplicateStatus === 'pending_possible_duplicate') {
                        return {
                            type: 'html',
                            html: `<span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap bg-yellow-100 text-yellow-800 ring-1 ring-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:ring-yellow-700 cursor-pointer"><span class="sm:hidden">≈</span><span class="hidden sm:inline">${$t('importWizard.status.possiblePendingDuplicate')}</span></span>`,
                            tooltip: {text: $t('importWizard.status.tooltip.possiblePendingDuplicate'), position: 'top', maxWidth: '300px'},
                            onClick: () => openBadgeCompare(mt),
                            testId: `import-wizard-compare-${mt.index}`,
                        };
                    }
                    if (mt.duplicateStatus === 'possible') {
                        return {
                            type: 'html',
                            html: `<span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 cursor-pointer"><span class="sm:hidden">ℹ</span><span class="hidden sm:inline">${$t('importWizard.status.possibleDup')}</span></span>`,
                            tooltip: {text: $t('importWizard.compareModal.openHint'), position: 'top', maxWidth: '260px'},
                            onClick: () => openBadgeCompare(mt),
                            testId: `import-wizard-compare-${mt.index}`,
                        };
                    }
                    return {
                        type: 'html',
                        html: `<span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"><span class="sm:hidden">✓</span><span class="hidden sm:inline">${$t('importWizard.status.unique')}</span></span>`,
                    };
                },
            },
            {
                id: 'selected',
                header: '',
                type: 'custom',
                sortable: false,
                filterable: false,
                width: 44,
                minWidth: 44,
                cell: (mt) => {
                    const beforeOpening = beforeOpeningIndices.has(mt.index);
                    return {
                        type: 'editable-checkbox',
                        value: beforeOpening ? false : mt.selected,
                        disabled: beforeOpening,
                        onchange: (v: boolean) => {
                            if (beforeOpening) return;
                            mergedTransactions = mergedTransactions.map((t) => (t.index === mt.index ? {...t, selected: v} : t));
                        },
                    };
                },
            },
            {
                id: 'date',
                header: () => $t('common.date'),
                type: 'date',
                sortable: true,
                filterable: true,
                width: 120,
                minWidth: 100,
                cell: (mt) => ({type: 'date', value: mt.tx.date ?? '', format: 'date'}),
            },
            {
                id: 'type',
                header: () => $t('common.type'),
                type: 'enum',
                sortable: true,
                filterable: true,
                width: 140,
                minWidth: 100,
                getValue: (mt) => String(mt.tx.type ?? ''),
                enumOptions: TX_TYPES.filter((tt) => mergedTransactions.some((mt) => String(mt.tx.type ?? '') === tt)).map((tt) => ({
                    value: tt,
                    label: $t(`transactions.types.${tt}`) || tt,
                    iconUrl: getTransactionTypeIconUrl(tt),
                })),
                cell: (mt) => {
                    const type = String(mt.tx.type ?? '');
                    const slug = type.toLowerCase().replace(/_/g, '-');
                    const label = $t(`transactions.types.${type}`) || type;
                    const isPair = getTypeRule(type).requiresPair;
                    const arrow = isPair ? '<span class="shrink-0 mr-0.5">↔</span>' : '';
                    return {
                        type: 'html',
                        html: `<span class="inline-flex items-center gap-1.5 text-xs leading-snug">\
<img src="/icons/transactions/${slug}.png" alt="" style="width:1.5rem;height:1.5rem" class="object-contain shrink-0" onerror="this.style.display='none'"/>\
${arrow}<span>${label}</span></span>`,
                    };
                },
            },
            {
                id: 'asset',
                header: () => $t('common.asset'),
                type: 'enum',
                sortable: true,
                filterable: true,
                width: 200,
                minWidth: 150,
                getValue: (mt) => {
                    const assetId = typeof mt.tx.asset_id === 'number' ? mt.tx.asset_id : null;
                    if (assetId === null) return '__null__';
                    if (isFakeAssetId(assetId)) {
                        const res = assetResolutions.find((r) => r.fakeAssetId === assetId);
                        // Group under the resolved real asset once assigned; keep distinct per
                        // extracted instrument while still unresolved.
                        if (res?.resolvedAssetId) return String(res.resolvedAssetId);
                        return String(assetId);
                    }
                    return String(assetId);
                },
                enumOptions: (() => {
                    const opts = new Map<string, EnumOption>();
                    let hasNull = false;
                    for (const mt of mergedTransactions) {
                        const assetId = typeof mt.tx.asset_id === 'number' ? mt.tx.asset_id : null;
                        if (assetId === null) {
                            hasNull = true;
                            continue;
                        }
                        if (isFakeAssetId(assetId)) {
                            const res = assetResolutions.find((r) => r.fakeAssetId === assetId);
                            if (res?.resolvedAssetId) {
                                const key = String(res.resolvedAssetId);
                                if (!opts.has(key)) {
                                    const rInfo = getAssetInfo(res.resolvedAssetId);
                                    const rIcon = rInfo?.icon_url ?? (rInfo?.asset_type ? getAssetTypeIconUrl(rInfo.asset_type) : undefined);
                                    opts.set(key, {value: key, label: rInfo?.display_name ?? `#${res.resolvedAssetId}`, iconUrl: rIcon ?? undefined});
                                }
                                continue;
                            }
                            const key = String(assetId);
                            if (!opts.has(key)) {
                                opts.set(key, {value: key, label: getAssetDisplayName(assetId), dotColor: '#dc2626'});
                            }
                            continue;
                        }
                        const key = String(assetId);
                        if (!opts.has(key)) {
                            const info = getAssetInfo(assetId);
                            const iconUrl = info?.icon_url ?? (info?.asset_type ? getAssetTypeIconUrl(info.asset_type) : undefined);
                            opts.set(key, {value: key, label: info?.display_name ?? `#${assetId}`, iconUrl: iconUrl ?? undefined});
                        }
                    }
                    const list = [...opts.values()].sort((a, b) => a.label.localeCompare(b.label));
                    if (hasNull) list.unshift({value: '__null__', label: $t('transactions.noAsset')});
                    return list;
                })(),
                cell: (mt) => {
                    const assetId = typeof mt.tx.asset_id === 'number' ? mt.tx.asset_id : null;
                    if (assetId === null) return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                    if (isFakeAssetId(assetId)) {
                        const res = assetResolutions.find((r) => r.fakeAssetId === assetId);
                        if (res?.resolvedAssetId) {
                            const rInfo = getAssetInfo(res.resolvedAssetId);
                            const rName = rInfo?.display_name ?? `#${res.resolvedAssetId}`;
                            const rIcon = rInfo?.icon_url ?? (rInfo?.asset_type ? getAssetTypeIconUrl(rInfo.asset_type) : null);
                            const rIconHtml = rIcon ? `<img src="${rIcon}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />` : '';
                            const origName = getAssetDisplayName(assetId);
                            return {type: 'html', html: `<span class="inline-flex items-center gap-1.5 truncate text-emerald-600 dark:text-emerald-400" title="${origName} → ${rName}">${rIconHtml}<span class="truncate">${rName}</span></span>`};
                        }
                        const name = getAssetDisplayName(assetId);
                        return {type: 'html', html: `<span class="text-red-600 dark:text-red-400 inline-flex items-center gap-1">✗ <span class="truncate">${name}</span></span>`};
                    }
                    const info = getAssetInfo(assetId);
                    const name = info?.display_name ?? `#${assetId}`;
                    const iconUrl = info?.icon_url ?? (info?.asset_type ? getAssetTypeIconUrl(info.asset_type) : null);
                    const iconHtml = iconUrl ? `<img src="${iconUrl}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />` : '';
                    return {type: 'html', html: `<span class="inline-flex items-center gap-1.5 truncate">${iconHtml}<span class="truncate">${name}</span></span>`};
                },
            },
            {
                id: 'broker',
                header: () => $t('common.broker'),
                type: 'enum',
                sortable: true,
                filterable: true,
                width: 160,
                minWidth: 110,
                getValue: (mt) => {
                    const brokerId = getBrokerIdForTx(mt);
                    return brokerId === null ? '__none__' : String(brokerId);
                },
                enumOptions: (() => {
                    const opts = new Map<string, EnumOption>();
                    for (const mt of mergedTransactions) {
                        const brokerId = getBrokerIdForTx(mt);
                        if (brokerId === null) continue;
                        const key = String(brokerId);
                        if (!opts.has(key)) {
                            const b = brokers.find((x) => x.id === brokerId) ?? getBrokerInfo(brokerId);
                            opts.set(key, {value: key, label: b?.name ?? `#${brokerId}`, iconUrl: b?.icon_url ?? undefined});
                        }
                    }
                    return [...opts.values()].sort((a, b) => a.label.localeCompare(b.label));
                })(),
                cell: (mt) => {
                    const brokerId = getBrokerIdForTx(mt);
                    if (brokerId === null) return {type: 'html', html: '<span class="text-gray-400 italic">—</span>'};
                    const b = brokers.find((x) => x.id === brokerId) ?? getBrokerInfo(brokerId);
                    const name = b?.name ?? `#${brokerId}`;
                    const iconUrl = b?.icon_url ?? null;
                    const iconHtml = iconUrl ? `<img src="${iconUrl}" alt="" class="w-4 h-4 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />` : '';
                    // For rows blocked by the broker's opening date, surface a discoverable
                    // "edit opening date" affordance directly in the destination-broker column.
                    if (beforeOpeningIndices.has(mt.index)) {
                        return {
                            type: 'html',
                            html: `<span class="inline-flex items-center gap-1 cursor-pointer text-gray-700 dark:text-gray-200 hover:text-libre-green" title="${$t('importWizard.status.editBrokerDate')}">${iconHtml}<span class="truncate">${name}</span><span class="shrink-0">✏️</span></span>`,
                            onClick: () => openBrokerOpeningEdit(mt),
                            testId: `import-wizard-broker-edit-${mt.index}`,
                        };
                    }
                    return {
                        type: 'custom',
                        component: BrokerBadge,
                        props: {broker: b ?? {id: brokerId, name}, size: 18, showName: true, tooltip: name},
                    } as const;
                },
            },
            {
                id: 'quantity',
                header: () => $t('common.quantity'),
                type: 'number',
                sortable: true,
                filterable: false,
                width: 90,
                minWidth: 70,
                getValue: (mt) => Number(mt.tx.quantity ?? 0),
                cell: (mt) => {
                    const q = mt.tx.quantity;
                    if (!q || q === '0') return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                    const n = parseFloat(q);
                    const formatted = isNaN(n) ? q : parseFloat(n.toFixed(8)).toString();
                    return {type: 'html', html: `<span class="font-mono text-sm">${formatted}</span>`};
                },
            },
            {
                id: 'cash',
                header: () => $t('common.cash'),
                type: 'currency-stack',
                sortable: true,
                filterable: true,
                width: 220,
                minWidth: 160,
                align: 'right' as const,
                currencyOptions: [
                    ...new Set(
                        mergedTransactions
                            .map((mt) => mt.tx.cash)
                            .filter((c): c is {code: string; amount: string} => !!c && typeof c === 'object' && !Array.isArray(c))
                            .map((c) => c.code),
                    ),
                ].sort(),
                getValue: (mt) => {
                    const cash = mt.tx.cash;
                    return cash && typeof cash === 'object' && !Array.isArray(cash) ? Number((cash as {amount: string}).amount) : 0;
                },
                getCurrencyValue: (mt) => {
                    const cash = mt.tx.cash;
                    if (cash && typeof cash === 'object' && !Array.isArray(cash)) {
                        const c = cash as {code: string; amount: string};
                        return {code: c.code, amount: Number(c.amount)};
                    }
                    return null;
                },
                cell: (mt) => {
                    const cash = mt.tx.cash;
                    if (cash && typeof cash === 'object' && !Array.isArray(cash)) {
                        const c = cash as {code: string; amount: string};
                        return {type: 'html', html: formatCurrencyAmountHtml(Number(c.amount), c.code, {showSign: true})};
                    }
                    return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                },
            },
            {
                id: 'tags',
                header: () => $t('common.tags'),
                type: 'multi-enum',
                sortable: true,
                filterable: true,
                width: 160,
                minWidth: 100,
                enumOptions: (() => {
                    const tagSet = new Set<string>();
                    for (const mt of mergedTransactions) {
                        for (const tag of txTagsToArray(mt.tx.tags)) tagSet.add(tag);
                    }
                    return [...tagSet].sort().map((tag) => ({value: tag, label: tag, dotColor: getStringColor(tag).bg}));
                })(),
                getValue: (mt) => txTagsToArray(mt.tx.tags).join(','),
                getMultiValue: (mt) => txTagsToArray(mt.tx.tags),
                cell: (mt) => {
                    const tags = txTagsToArray(mt.tx.tags);
                    if (tags.length === 0) return {type: 'html', html: '<span class="text-gray-400">—</span>'};
                    const html = tags
                        .map((tag) => {
                            const escaped = tag.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                            const c = getStringColor(tag);
                            return `<span class="inline-block px-1.5 py-0.5 text-[10px] rounded mr-0.5 mb-0.5" style="background:${c.bg};color:${c.text}">${escaped}</span>`;
                        })
                        .join('');
                    return {type: 'html', html: `<span class="flex flex-wrap gap-0.5" data-testid="import-wizard-tags-${mt.index}">${html}</span>`};
                },
            },
        ];

        // Show source file column only when multiple files were parsed (avoids noise for single-file imports)
        if (doneFilesCount > 1) {
            const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
            columns.push({
                id: 'sourceFileId',
                header: () => $t('importWizard.sourceFile'),
                displayName: () => $t('importWizard.sourceFile'),
                type: 'text',
                sortable: true,
                filterable: true,
                width: 200,
                minWidth: 160,
                getValue: (mt) => parseResults.find((r) => r.fileId === mt.sourceFileId)?.fileName ?? mt.sourceFileId,
                cell: (mt) => {
                    const name = parseResults.find((r) => r.fileId === mt.sourceFileId)?.fileName ?? mt.sourceFileId;
                    return {type: 'html', html: `<span class="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[180px] block" title="${esc(name)}">${esc(name)}</span>`} as const;
                },
            });
        }

        return columns;
    });

    function step4SelectAll() {
        // Do not re-select in-batch duplicates that were resolved away (non-keeper group members):
        // selecting them would surface hidden duplicates. Keepers and non-group rows are selected.
        mergedTransactions = mergedTransactions.map((t) => ({...t, selected: !beforeOpeningIndices.has(t.index) && !(t.dupGroupKey != null && t.isDupKeeper === false)}));
    }
    function step4DeselectAll() {
        mergedTransactions = mergedTransactions.map((t) => ({...t, selected: false}));
    }
    /**
     * Select every selectable row on the current DataTable page (respecting active filters,
     * sort, and pagination) without touching selections on other pages. Skips before-opening
     * rows and resolved-away in-batch duplicate members, mirroring step4SelectAll's selectability.
     */
    function step4SelectVisible() {
        const ids = new Set(step4TableRef?.getPageRowIds() ?? []);
        if (ids.size === 0) return;
        mergedTransactions = mergedTransactions.map((t) => {
            if (!ids.has(String(t.index))) return t;
            if (beforeOpeningIndices.has(t.index)) return t;
            if (t.dupGroupKey != null && t.isDupKeeper === false) return t;
            return {...t, selected: true};
        });
    }

    // =========================================================================
    // Shared State
    // =========================================================================

    // =========================================================================
    // Derived
    // =========================================================================

    let hasUnsavedWork = $derived(pendingFiles.length > 0 || selectedFiles.length > 0 || parseResults.length > 0 || mergedTransactions.length > 0);
    let selectedBrokerCount = $derived(new Set(selectedFiles.map((f) => f.brokerId)).size);
    let step3Warnings = $derived(parseResults.flatMap((r) => r.response?.warnings ?? []));
    /**
     * Notices grouped by *severity first, file second*.
     *
     * Severity is the axis the reader acts on: an `info` explains a deliberate plugin
     * decision, a `warning` asks for attention. Grouping by file alone mixed the two,
     * so a single warning buried among informational notes looked identical to them.
     * Warnings are emitted first so the section that needs action is on top.
     */
    let step3NoticeSections = $derived(
        (['warning', 'info'] as const)
            .map((severity) => ({
                severity,
                files: parseResults
                    .filter((r) => r.status === 'done' && (r.response?.warnings?.length ?? 0) > 0)
                    .map((r) => ({
                        fileName: r.fileName,
                        fileId: r.fileId,
                        warnings: (r.response!.warnings as BrimNotice[]).filter((w) => (w.severity === 'info' ? 'info' : 'warning') === severity),
                    }))
                    .filter((f) => f.warnings.length > 0),
            }))
            .filter((s) => s.files.length > 0),
    );
    let step3HasWarningSeverity = $derived(step3Warnings.some((w) => w.severity !== 'info'));

    /**
     * Duplicate groups split by overlap tier, partial first.
     *
     * `probable` (partial overlap) is the only tier that really needs a human: the rows
     * only partly match, so the automatic keeper may be the wrong one. `sure` (total
     * overlap) is mechanical — keep one copy — and is folded away behind its own panel
     * so it stops competing for attention.
     */
    let resolverTierPanels = $derived((['probable', 'sure'] as const).map((tier) => ({tier: tier as DuplicateTier, groups: duplicateGroups.filter((g) => g.tier === tier)})).filter((p) => p.groups.length > 0));
    let resolverPartialCount = $derived(duplicateGroups.filter((g) => g.tier === 'probable').length);

    // =========================================================================
    // Lifecycle
    // =========================================================================

    $effect(() => {
        if (open) {
            loadBrokers();
            globalBrokerId = defaultBrokerId ?? null;
        } else {
            resetState();
        }
    });

    function resetState() {
        currentStepId = 'upload';
        pendingFiles = [];
        globalBrokerId = null;
        uploading = false;
        uploadError = null;
        dropZoneExpanded = true;
        selectedFiles = [];
        brokerFilesMap = new Map();
        brokerFilesLoading = false;
        expandedBrokers = new Set();
        filePluginOverrides = new Map();
        confirmCloseOpen = false;
        step1SelectedIds = [];
        // Step 3 reset
        parseResults = [];
        abortParsing = false;
        lastParseHash = null;
        usingCachedResults = false;
        showParseDetail = false;
        parseDetailResult = null;
        showAggregateDetail = false;
        // Step 4 reset
        mergedTransactions = [];
        assetResolutions = [];
        assetGroups = [];
        // Only a full reset drops the user's unification: member keys are content-based, so a
        // re-parse of the same files replays their decisions instead of asking again.
        assetGroupOverride = null;
        assetGroupConfirmed = new Set();
        assetGroupPrimary = {};
        duplicateGroups = [];
        duplicateFilePriorityIds = [];
        duplicateResolverTouchedKeys = new Set();
        duplicateResolverSelections = {};
        expandedDuplicateGroupKeys = new Set();
        fixDecisions = {};
        fixTodoSnapshot = {};
        fixTxSnapshot = {};
        fixExpandedIndices = new Set();
        fixCreateAssetIndex = null;
        fixCreateAssetQuery = '';
        fixCreatedAssets = {};
        duplicateRecheckRunning = false;
        duplicateRecheckDone = false;
        duplicateRecheckError = null;
        step4ShowResolveSection = true;
        createAssetForFakeId = null;
        createPrimaryPending = null;
        createPrimaryIsin = null;
        createPrimarySymbol = null;
        editBrokerOpen = false;
        editBrokerId = null;
        editBrokerInitialData = {};
    }

    // =========================================================================
    // Broker Loading
    // =========================================================================

    async function loadBrokers() {
        brokersLoading = true;
        await Promise.all([ensureBrokersLoaded(), ensureTypesLoaded()]);
        brokers = getEditableBrokers();
        brokersLoading = false;
    }

    // =========================================================================
    // Close / Unsaved Guard
    // =========================================================================

    function handleClose() {
        if (hasUnsavedWork) {
            confirmCloseOpen = true;
        } else {
            onClose();
        }
    }

    function confirmDiscard() {
        confirmCloseOpen = false;
        resetState();
        onClose();
    }

    // =========================================================================
    // Navigation — step machine
    // =========================================================================

    /**
     * Rows the plugin could not fully understand: it booked them somehow, but said so.
     * They must be settled before the database comparison, because a purchase misread as
     * a cash withdrawal gets compared against cash withdrawals — the wrong question,
     * asked confidently.
     *
     * A settled row stays in the list, badged with the decision and still editable: the
     * blockers it carried are retired from the transaction (so the bulk editor no longer
     * refuses to save), which is why the todos shown here come from `fixTodoSnapshot`.
     */
    let fixStepRows = $derived(
        mergedTransactions
            .filter((m) => rowStaysInFixStep(m.todos, fixDecisions[m.index]))
            // Only the todos this step can actually act on are handed over: showing a row a
            // cost-basis complaint it cannot fix here would be noise at best.
            .map((m) => ({
                index: m.index,
                tx: m.tx as unknown as Record<string, unknown>,
                todos: fixTodoSnapshot[m.index] ?? m.todos.filter(isFixStepTodo),
                decision: fixDecisions[m.index] ?? null,
            })),
    );

    let fixStepPendingCount = $derived(fixStepRows.filter((r) => r.decision === null).length);

    /**
     * The instruments the analysis already recognised. A flagged row's asset is nearly
     * always one of them — the file named it on another line — so offering the whole
     * database first would mean asking the user to find what the import already found.
     */
    let fixAnalysisAssets = $derived(
        assetResolutions.map((r) => ({
            id: r.fakeAssetId,
            label: resolutionLabel(r),
            // A unified entry shows every code it absorbed: two files, two ISINs, one instrument
            // — and the user must be able to recognise it as the one they just unified.
            detail: [...r.groupSymbols, ...r.groupIsins].join(' · ') || [r.extractedSymbol, r.extractedIsin].filter(Boolean).join(' · '),
            // Already bound to an archived asset: the picker must not list it twice.
            archiveId: r.resolvedAssetId,
        })),
    );

    /** Transactions per member, so the unification step can weigh each group. */
    let assetGroupTxCounts = $derived.by(() => {
        const counts: Record<number, number> = {};
        for (const mt of mergedTransactions) {
            const id = (mt.tx as {asset_id?: number | null}).asset_id;
            if (typeof id === 'number') counts[id] = (counts[id] ?? 0) + 1;
        }
        return counts;
    });

    /** Groups already bound to a real asset, so the step can offer the inspect pencil. */
    let assetGroupResolvedIds = $derived.by(() => {
        const ids: Record<number, number> = {};
        for (const res of assetResolutions) if (res.resolvedAssetId !== null) ids[res.fakeAssetId] = res.resolvedAssetId;
        return ids;
    });

    /**
     * The archive's name for each bound group, so the unification step shows the same label the
     * user will see everywhere else instead of whichever spelling one file happened to use.
     */
    let assetGroupResolvedNames = $derived.by(() => {
        const names: Record<number, string> = {};
        for (const res of assetResolutions) if (res.resolvedAssetId !== null) names[res.fakeAssetId] = resolutionLabel(res);
        return names;
    });

    /**
     * Store the user's partition and rebuild everything downstream from it.
     *
     * Re-merging is the right answer rather than patching the existing list in place: the fold
     * rewrites transaction bindings, candidate unions and duplicate groups, and reproducing that
     * by hand for one moved chip is how the two representations drift apart.
     */
    function applyGroupPartition(partition: string[][]) {
        assetGroupOverride = partition;
        mergeAllTransactions();
    }

    /** Accept a proposal as it stands — no reshaping, so the automatic partition still applies. */
    function confirmGroupProposal(signature: string) {
        assetGroupConfirmed = new Set([...assetGroupConfirmed, signature]);
        mergeAllTransactions();
    }

    /** Promote one code to lead its kind for a group. */
    function electGroupPrimary(signature: string, kind: IdentifierKind, value: string) {
        assetGroupPrimary = electPrimary(assetGroupPrimary, signature, kind, value);
        mergeAllTransactions();
    }

    /**
     * Throw away every decision taken on this step and go back to what the engine proposes.
     *
     * The escape hatch matters because the partition is stored whole: once the user has touched
     * anything the engine stops shaping the layout, so a few wrong drags leave a mess that no
     * single undo can clear.
     */
    function resetGrouping() {
        assetGroupOverride = null;
        assetGroupConfirmed = new Set();
        assetGroupPrimary = {};
        mergeAllTransactions();
    }

    /** True once anything on the unification step has been decided by hand. */
    let assetGroupingTouched = $derived(assetGroupOverride !== null || assetGroupConfirmed.size > 0 || Object.keys(assetGroupPrimary).length > 0);

    /** Groups the engine is not confident enough to settle on its own. */
    let assetGroupOpenProposals = $derived(assetGroups.filter((g) => g.state === 'proposed').length);

    /*
     * Collisions with the database are deliberately NOT listed here. They carry no
     * decision — the re-check recomputes them after the corrections and they land
     * straight in the review table as pre-deselected rows with a ⚠ status. Showing
     * a second, read-only copy of them would only add noise to a step whose whole
     * job is arbitrating overlaps *between the files being imported*.
     */

    function toggleFixRow(index: number) {
        const next = new Set(fixExpandedIndices);
        if (next.has(index)) next.delete(index);
        else next.add(index);
        fixExpandedIndices = next;
    }

    /**
     * Writes the user's correction onto the merged transaction and retires its blocker
     * todos. The parse response itself is left untouched: it stays the plugin's objective
     * reading of the file, and a re-parse must be able to restore it.
     */
    /**
     * Index namespace for the legs the user carves out of a source row. A leg is not in the
     * file, so it has no row of its own to be numbered by; keeping it far above the parse
     * counter makes its index stable across re-applies (one leg per parent, replaced in
     * place) and impossible to confuse with a row the plugin actually read.
     */
    const SPLIT_LEG_INDEX_BASE = 1_000_000;

    /** Every index a given source row's legs can occupy, in order. */
    function legIndices(index: number): number[] {
        return Array.from({length: MAX_SPLIT_LEGS}, (_, k) => SPLIT_LEG_INDEX_BASE * (k + 1) + index);
    }
    const MAX_SPLIT_LEGS = 6;

    function applyFixToRow(index: number, patch: FixPatch) {
        snapshotFixTodos(index);
        let legs: MergedTx[] = [];
        mergedTransactions = mergedTransactions.map((m) => {
            if (m.index !== index) return m;
            const tx = {...m.tx} as TransactionCreateItem;
            if (patch.type) (tx as {type?: string}).type = patch.type;
            if (patch.asset_id !== undefined) (tx as {asset_id?: number | null}).asset_id = patch.asset_id;
            if (patch.quantity !== undefined && patch.quantity !== '') (tx as {quantity?: string}).quantity = String(patch.quantity);
            // Retyping a row changes what its numbers are allowed to mean: a deposit becoming
            // a sale needs a negative quantity, a withdrawal becoming a purchase a negative
            // amount. The user states magnitudes — the sign is the type's business, exactly as
            // in the transaction form — and getting it wrong here fails the whole duplicate
            // re-check with a validation error and falls back to a stale verdict.
            const rule = getTypeRule(String((tx as {type?: string}).type ?? ''));
            const signed = applySignRules(String((tx as {quantity?: string}).quantity ?? '0'), (tx as {cash?: {code: string; amount: string} | null}).cash ?? null, rule);
            (tx as {quantity?: string}).quantity = signed.signedQty;
            (tx as {cash?: {code: string; amount: string} | null}).cash = signed.signedCash;
            if (patch.split) {
                // The bank moved one amount and that amount is the one thing in the row we
                // know to be right, so the legs are written as a share of it: what the user
                // named, and the rest. Their sum is the original by construction — there is
                // no arithmetic here that could drift away from the statement.
                //
                // The trade keeps the row's direction; a charge is always money leaving, on
                // a purchase as much as on a sale, where it was withheld from the proceeds.
                const cash = (tx as {cash?: {code: string; amount: string} | null}).cash ?? null;
                const code = cash?.code ?? 'EUR';
                const sign = Number(cash?.amount ?? '0') < 0 ? '-' : '';
                (tx as {cash?: {code: string; amount: string} | null}).cash = {code, amount: `${sign}${patch.split.main}`};
                legs = patch.split.legs.slice(0, MAX_SPLIT_LEGS).map((leg, k) => ({
                    ...m,
                    index: SPLIT_LEG_INDEX_BASE * (k + 1) + m.index,
                    tx: {
                        ...(tx as TransactionCreateItem),
                        type: leg.type,
                        quantity: '0',
                        cash: {code, amount: `-${leg.amount}`},
                        description: leg.description,
                        tags: [...(((tx as {tags?: string[]}).tags ?? []) as string[]), 'split_leg'],
                        cost_basis_override: null,
                    } as TransactionCreateItem,
                    todos: [],
                    duplicateStatus: 'unique' as DuplicateStatus,
                    dupMatches: [],
                }));
            }
            return {...m, tx, todos: todosAfterSettle(m.todos)};
        });
        // Re-applying with different charges replaces the legs instead of stacking new ones.
        const stale = new Set(legIndices(index));
        mergedTransactions = mergedTransactions.filter((m) => !stale.has(m.index));
        if (legs.length > 0) {
            const at = mergedTransactions.findIndex((m) => m.index === index);
            mergedTransactions = [...mergedTransactions.slice(0, at + 1), ...legs, ...mergedTransactions.slice(at + 1)];
        }
        markFixResolved(index, 'corrected');
    }

    /** The user judged the plugin's fallback good enough — record the decision, keep the row. */
    function acceptPluginFallback(index: number) {
        // "Keep as read" is a statement about the plugin's reading, so a correction already
        // applied — and the legs it created — has to be undone first. Without this the row
        // kept the corrected transaction under a badge that denies it was ever corrected.
        // A row that was never applied has no snapshot, and the reset is a no-op.
        resetFixRow(index);
        snapshotFixTodos(index);
        mergedTransactions = mergedTransactions.map((m) => (m.index === index ? {...m, todos: todosAfterSettle(m.todos)} : m));
        markFixResolved(index, 'kept');
    }

    /**
     * The user touched a field on a row they had already settled: the decision lapses, the row
     * goes back to the colour and the wording it had when it was flagged. The transaction is
     * deliberately left alone — the draft they are editing was read off it, so restoring it
     * would move the values under their hands.
     */
    function reopenFixRow(index: number) {
        if (fixDecisions[index] === undefined) return;
        fixDecisions = Object.fromEntries(Object.entries(fixDecisions).filter(([k]) => Number(k) !== index));
        // Settling a row retires its todos, so from that moment the row stayed in the step
        // only because it carried a decision. Withdrawing the decision without giving the
        // todos back left it matching neither half of the filter and the row vanished from
        // under the user mid-edit, recoverable only by reloading. The transaction itself is
        // deliberately untouched: the draft being edited was read off it.
        const todos = fixTodoSnapshot[index];
        if (!todos) return;
        mergedTransactions = mergedTransactions.map((m) => (m.index === index ? {...m, todos: todosAfterReopen(m.todos, todos)} : m));
    }

    /** "Everything the plugin proposed is fine" — settles every row still waiting. */
    function acceptAllPluginFallbacks(indices?: number[]) {
        const scope = indices ? new Set(indices) : null;
        for (const row of fixStepRows.filter((r) => r.decision === null && (scope === null || scope.has(r.index)))) acceptPluginFallback(row.index);
    }

    /**
     * Row index whose asset is being created, and the ids created so far. The instrument
     * of a flagged row can be in neither the analysis list nor the database — the file
     * only ever named it in the free-text description of this one line — so the step
     * needs a way out that does not send the user off to another screen.
     */
    let fixCreateAssetIndex = $state<number | null>(null);
    /** What the user had typed in the picker when they gave up looking — usually the name. */
    let fixCreateAssetQuery = $state('');
    let fixCreatedAssets = $state<Record<number, number>>({});

    /** Bare ISIN detector: 2 country letters, 9 alphanumerics, 1 check digit. */
    const ISIN_RE = /\b([A-Z]{2}[A-Z0-9]{9}\d)\b/;

    /**
     * Asset opened for inspection from the resolution step. Picking the right instrument
     * from a list of names is guesswork when two of them read alike — the currency, the
     * identifiers and the provider decide it, and they are only visible in the asset form.
     */
    let inspectAssetData = $state<Record<string, unknown> | null>(null);
    let inspectAssetLoading = $state(false);

    async function openAssetInspector(assetId: number) {
        if (inspectAssetLoading) return;
        inspectAssetLoading = true;
        try {
            // `/assets/all` hides inactive instruments, and an expired security created from
            // this very wizard is usually filed as inactive on purpose — asking for it there
            // returns nothing and the inspector silently refuses to open.
            const assets = (await zodiosApi.list_assets_api_v1_assets_query_get({queries: {}})) as Array<Record<string, unknown>>;
            const asset = assets.find((a) => a.id === assetId);
            if (!asset) return;
            const assignments = (await zodiosApi.get_provider_assignments_api_v1_assets_provider_assignments_get({queries: {asset_ids: [assetId]}})) as Array<Record<string, unknown>>;
            const assignment = assignments[0] ?? null;
            inspectAssetData = {
                ...asset,
                provider_code: assignment?.provider_code ?? null,
                provider_identifier: assignment?.identifier ?? '',
                provider_identifier_type: assignment?.identifier_type ?? '',
                provider_params: assignment?.provider_params ?? null,
                provider_user_url: asset.user_url ?? '',
                provider_url: assignment?.provider_url ?? null,
            };
        } finally {
            inspectAssetLoading = false;
        }
    }

    function fixRowDescription(index: number): string {
        const row = mergedTransactions.find((m) => m.index === index);
        const desc = row?.tx?.description;
        return typeof desc === 'string' ? desc.trim() : '';
    }

    /**
     * Search seeds taken from the description. The plugin could not read an instrument out
     * of it, so nothing here is claimed to be the name — these are candidates the user
     * filters, which is why the whole description is offered alongside its parts.
     */
    function fixCreateHints(index: number): string[] {
        const desc = fixRowDescription(index);
        if (desc === '') return [];
        const isin = desc.match(ISIN_RE)?.[1];
        const words = desc
            .split(/[\s:;,/|]+/)
            .map((w) => w.trim())
            .filter((w) => w.length >= 3 && w.length <= 24 && /[A-Za-z]/.test(w) && !/^\d+$/.test(w));
        return [...new Set([...(isin ? [isin] : []), desc, ...words])];
    }

    /**
     * Keeps the flagged todos alive for display after they have been retired from the
     * transaction: the row stays visible and editable, so its reason must stay readable.
     */
    function snapshotFixTodos(index: number) {
        const row = mergedTransactions.find((m) => m.index === index);
        if (!row) return;
        if (!fixTxSnapshot[index]) fixTxSnapshot = {...fixTxSnapshot, [index]: {...row.tx}};
        if (fixTodoSnapshot[index]) return;
        const todos = row.todos.filter(isFixStepTodo);
        if (todos.length > 0) fixTodoSnapshot = {...fixTodoSnapshot, [index]: todos};
    }

    /**
     * Puts a settled row back exactly as the plugin read it. Correcting a row rewrites the
     * transaction and retires its todos, so without the snapshots there would be no way
     * back from a wrong answer other than re-uploading the file.
     */
    function resetFixRow(index: number) {
        const original = fixTxSnapshot[index];
        const todos = fixTodoSnapshot[index];
        const staleLegs = new Set(legIndices(index));
        mergedTransactions = mergedTransactions
            // A leg only exists because of a correction, so undoing the correction removes it.
            .filter((m) => !staleLegs.has(m.index))
            .map((m) => {
                if (m.index !== index) return m;
                return {
                    ...m,
                    tx: original ? ({...original} as TransactionCreateItem) : m.tx,
                    todos: todosAfterReopen(m.todos, todos),
                };
            });
        fixDecisions = Object.fromEntries(Object.entries(fixDecisions).filter(([k]) => Number(k) !== index));
        fixCreatedAssets = Object.fromEntries(Object.entries(fixCreatedAssets).filter(([k]) => Number(k) !== index));
    }

    function resetAllFixRows(indices?: number[]) {
        const scope = indices ? new Set(indices) : null;
        for (const row of fixStepRows.filter((r) => r.decision !== null && (scope === null || scope.has(r.index)))) resetFixRow(row.index);
    }

    function markFixResolved(index: number, decision: 'corrected' | 'kept') {
        fixDecisions = {...fixDecisions, [index]: decision};
        const open = new Set(fixExpandedIndices);
        open.delete(index);
        fixExpandedIndices = open;
    }

    function stepIsActive(id: StepId): boolean {
        // Nothing to unify means nothing to ask: a single-file import where every security is
        // distinct never sees this step. It opens when two extractions were merged, or when the
        // engine found a resemblance it is not confident enough to act on alone.
        if (id === 'assets') return assetGroups.some((g) => g.members.length > 1 || g.state === 'proposed');
        if (id === 'fix') return fixStepRows.length > 0;
        // Database collisions do NOT open this step: there is nothing to arbitrate about
        // them here — they simply arrive at the review deselected. The step exists for the
        // one decision only the user can make: which copy to keep when the same movement
        // appears in two of the files being imported.
        if (id === 'duplicates') return duplicateGroups.length > 0;
        return true;
    }

    /**
     * The step currently shown always stays in the bar even if its reason to exist just
     * disappeared — fixing the last flagged row must not make the step vanish from under
     * the user mid-click.
     */
    let visibleSteps = $derived(STEP_DEFS.filter((s) => s.id === currentStepId || stepIsActive(s.id)));

    let currentStepIndex = $derived(
        Math.max(
            0,
            visibleSteps.findIndex((s) => s.id === currentStepId),
        ),
    );

    function isStepBeforeCurrent(id: StepId): boolean {
        const idx = visibleSteps.findIndex((s) => s.id === id);
        return idx >= 0 && idx < currentStepIndex;
    }

    function resetDownstreamState() {
        mergedTransactions = [];
        assetResolutions = [];
        assetGroups = [];
        duplicateGroups = [];
        duplicateFilePriorityIds = [];
        duplicateResolverTouchedKeys = new Set();
        duplicateResolverSelections = {};
        expandedDuplicateGroupKeys = new Set();
        fixDecisions = {};
        fixTodoSnapshot = {};
        fixExpandedIndices = new Set();
        fixCreateAssetIndex = null;
        fixCreateAssetQuery = '';
        fixCreatedAssets = {};
        duplicateRecheckDone = false;
        duplicateRecheckError = null;
    }

    function goToStep(target: StepId) {
        if (!isStepBeforeCurrent(target)) return;
        if (target === 'upload') selectedFiles = [];
        if (target === 'upload' || target === 'select') resetDownstreamState();
        currentStepId = target;
    }

    /**
     * Walks forward from `from` and lands on the first step that has something to do.
     * The duplicate report is refreshed just before its step is evaluated: it must be
     * computed on the corrected transactions, otherwise the step would either be skipped
     * on a stale "nothing to arbitrate" or shown with the plugin's original verdict.
     */
    async function enterNextActiveStep(from: StepId) {
        for (let i = STEP_ORDER.indexOf(from) + 1; i < STEP_ORDER.length; i++) {
            const id = STEP_ORDER[i];
            if (id === 'duplicates') await refreshDuplicateReport();
            if (stepIsActive(id)) {
                currentStepId = id;
                return;
            }
        }
        currentStepId = 'review';
    }

    function goNext() {
        if (currentStepId === 'upload') {
            uploadAllPendingFiles().then(() => {
                currentStepId = 'select';
                loadBrokerFiles();
            });
        } else if (currentStepId === 'select') {
            currentStepId = 'analyze';
            // Init parse results and auto-start parsing
            initParseResults();
            if (!usingCachedResults) doParseAll();
            else mergeAllTransactions();
        } else if (currentStepId === 'analyze') {
            if (step3Warnings.length > 0 && !showWarningConfirm) {
                showWarningConfirm = true;
                return;
            }
            showWarningConfirm = false;
            mergeAllTransactions();
            enterNextActiveStep('analyze');
        } else if (currentStepId === 'assets') {
            enterNextActiveStep('assets');
        } else if (currentStepId === 'fix') {
            enterNextActiveStep('fix');
        } else if (currentStepId === 'duplicates') {
            currentStepId = 'review';
        }
    }

    function goBack() {
        if (currentStepId === 'analyze' && parseParsing) {
            abortParsing = true;
        }
        if (currentStepIndex > 0) {
            currentStepId = visibleSteps[currentStepIndex - 1].id;
        }
    }

    // =========================================================================
    // Step 1: File handling (files stored locally, uploaded on Next)
    // =========================================================================

    function validateExtension(filename: string): boolean {
        const ext = '.' + (filename.split('.').pop()?.toLowerCase() ?? '');
        return ALLOWED_EXTENSIONS.includes(ext);
    }

    function handleFilesChanged(event: CustomEvent<{files: globalThis.File[]}>) {
        const files = event.detail?.files;
        if (!files?.length) return;

        const existingNames = new Set(pendingFiles.map((f) => f.fileName));
        for (const file of files) {
            if (existingNames.has(file.name)) continue;

            if (!validateExtension(file.name)) {
                const ext = '.' + (file.name.split('.').pop() ?? '');
                pendingFiles = [
                    ...pendingFiles,
                    {
                        id: generateUUID(),
                        file,
                        fileName: file.name,
                        brokerId: globalBrokerId,
                        status: 'error',
                        errorMessage: $t('importWizard.extensionError', {values: {ext}}),
                    },
                ];
            } else {
                pendingFiles = [
                    ...pendingFiles,
                    {
                        id: generateUUID(),
                        file,
                        fileName: file.name,
                        brokerId: globalBrokerId,
                        status: 'pending',
                    },
                ];
            }
        }

        fileUploaderRef?.clearFiles();
        // T2: collapse drop zone after adding files
        dropZoneExpanded = false;
    }

    // Uploads run in parallel, bounded: the browser will not open unlimited connections and
    // the rest of the app still needs some. Each file writes its own row by id, so completion
    // order is irrelevant — see requestConcurrency.ts.
    async function uploadAllPendingFiles() {
        const toUpload = pendingFiles.filter((f) => f.status === 'pending' && f.brokerId !== null);
        if (toUpload.length === 0) return;

        uploading = true;
        uploadError = null;

        await mapWithConcurrency(toUpload, async (entry) => {
            pendingFiles = pendingFiles.map((f) => (f.id === entry.id ? {...f, status: 'uploading'} : f));

            const formData = new FormData();
            formData.append('file', entry.file);
            formData.append('broker_id', String(entry.brokerId));
            if (entry.fileName !== entry.file.name) {
                formData.append('custom_filename', entry.fileName);
            }
            const result = await trySave(() => axiosInstance.post(`/api/v1/brokers/import/upload`, formData), {toast: false, fallback: 'Upload failed', prefix: entry.fileName});

            if (result.status === 'error') {
                pendingFiles = pendingFiles.map((f) => (f.id === entry.id ? {...f, status: 'error', errorMessage: result.message} : f));
            } else {
                const serverFileId = result.data?.data?.file_id ?? generateUUID();
                pendingFiles = pendingFiles.map((f) => (f.id === entry.id ? {...f, status: 'uploaded', serverFileId} : f));
            }
        });

        uploading = false;
    }

    function clearAllPendingFiles() {
        pendingFiles = [];
        dropZoneExpanded = true;
    }

    function onGlobalBrokerChange(brokerId: number | null) {
        globalBrokerId = brokerId;
        if (brokerId) {
            pendingFiles = pendingFiles.map((f) => (f.brokerId === null ? {...f, brokerId} : f));
        }
    }

    function onFileBrokerChange(fileId: string, brokerId: number | null) {
        pendingFiles = pendingFiles.map((f) => (f.id === fileId ? {...f, brokerId} : f));
    }

    function renamePendingFile(fileId: string, newName: string) {
        if (!newName.trim()) return;
        pendingFiles = pendingFiles.map((f) => (f.id === fileId ? {...f, fileName: newName} : f));
    }

    function removePendingFileById(fileId: string) {
        pendingFiles = pendingFiles.filter((f) => f.id !== fileId);
        if (pendingFiles.length === 0) dropZoneExpanded = true;
    }

    function removePendingFilesByIds(ids: string[]) {
        const idSet = new Set(ids);
        pendingFiles = pendingFiles.filter((f) => !idSet.has(f.id));
        if (pendingFiles.length === 0) dropZoneExpanded = true;
    }

    // =========================================================================
    // Step 1: DataTable columns + actions
    // =========================================================================

    const pendingFileColumns: ColumnDef<PendingFileEntry>[] = [
        {
            id: 'fileName',
            header: () => $t('common.name'),
            cell: (row) => ({
                type: 'editable-text',
                value: row.fileName,
                placeholder: 'filename.csv',
                onchange: (newValue: string) => renamePendingFile(row.id, newValue),
            }),
            type: 'text',
            sortable: false,
            filterable: false,
            width: 250,
            minWidth: 120,
        },
        {
            id: 'size',
            header: () => 'Size',
            cell: (row) => formatBytes(row.file.size),
            type: 'text',
            sortable: false,
            filterable: false,
            width: 80,
            minWidth: 60,
        },
        {
            id: 'broker',
            header: () => $t('common.broker'),
            cell: (row) =>
                row.status === 'error'
                    ? '—'
                    : ({
                          type: 'custom',
                          component: BrokerSearchSelect,
                          props: {
                              brokers,
                              value: row.brokerId,
                              onchange: (v: number | null) => onFileBrokerChange(row.id, v),
                              placeholder: $t('common.broker'),
                              createLabel: $t('common.createNew'),
                              onCreateNew: () => {
                                  createBrokerContext = row.id;
                                  createBrokerOpen = true;
                              },
                          },
                      } as const),
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 220,
            minWidth: 160,
        },
        {
            id: 'status',
            header: () => 'Status',
            cell: (row) => {
                if (row.status === 'error') return {type: 'badge', text: row.errorMessage ?? 'Error', variant: 'error'} as const;
                if (row.status === 'uploading') return {type: 'badge', text: $t('common.loading'), variant: 'warning'} as const;
                if (row.status === 'uploaded') return {type: 'badge', text: $t('importWizard.fileStatus.uploaded'), variant: 'success'} as const;
                return {type: 'badge', text: $t('importWizard.ready'), variant: 'default'} as const;
            },
            type: 'text',
            sortable: false,
            filterable: false,
            width: 100,
            minWidth: 70,
        },
    ];

    const pendingFileActions: RowAction<PendingFileEntry>[] = [
        {
            id: 'delete',
            icon: Trash2,
            label: () => $t('common.remove'),
            onClick: (row) => removePendingFileById(row.id),
            variant: 'danger',
        },
    ];

    // =========================================================================
    // Step 2: Load Broker Files
    // =========================================================================

    async function loadBrokerFiles() {
        brokerFilesLoading = true;
        const allBrokerIds = brokers.map((b) => b.id);
        try {
            const res = await zodiosApi.list_files_api_v1_brokers_import_files_get({
                queries: {broker_ids: allBrokerIds},
            });
            const files = res as BrimFile[];
            const map = new Map<number, BrimFile[]>();
            for (const f of files) {
                const rawBid = f.target_broker_id;
                const bid = typeof rawBid === 'number' ? rawBid : null;
                if (bid == null) continue;
                if (!map.has(bid)) map.set(bid, []);
                map.get(bid)!.push(f);
            }
            brokerFilesMap = map;

            // Auto-expand brokers with files
            expandedBrokers = new Set(allBrokerIds.filter((id) => (map.get(id)?.length ?? 0) > 0));

            // T7: Pre-select files uploaded in Step 1 + auto-pick plugin
            const step1FileIds = new Set(pendingFiles.filter((f) => f.status === 'uploaded' && f.serverFileId).map((f) => f.serverFileId!));
            for (const [brokerId, brokerFiles] of brokerFilesMap) {
                for (const bf of brokerFiles) {
                    if (step1FileIds.has(bf.file_id) && !selectedFiles.some((s) => s.fileId === bf.file_id)) {
                        const pluginCode = pickBestPlugin(bf, brokerId);
                        selectedFiles = [...selectedFiles, {fileId: bf.file_id, fileName: bf.filename, brokerId, pluginCode}];
                    }
                }
            }
        } catch (e) {
            console.error('Failed to load broker files:', e);
        } finally {
            brokerFilesLoading = false;
        }
    }

    // T6: Smart plugin auto-selection
    function pickBestPlugin(file: BrimFile, brokerId: number): string {
        const broker = brokers.find((b) => b.id === brokerId);
        const defaultPlugin = broker?.default_import_plugin ?? '';
        const compatible = (file.compatible_plugins as string[] | undefined) ?? [];

        if (compatible.length === 0) return defaultPlugin;

        // If broker default is in compatible list, use it
        if (defaultPlugin && compatible.includes(defaultPlugin)) return defaultPlugin;

        // Use highest priority (first in sorted list), skip if it's the only one and it's generic
        if (compatible.length === 1) return compatible[0];

        // Multiple: first is highest priority (sorted by backend)
        return compatible[0];
    }

    function toggleBrokerExpand(brokerId: number) {
        const next = new Set(expandedBrokers);
        if (next.has(brokerId)) next.delete(brokerId);
        else next.add(brokerId);
        expandedBrokers = next;
    }

    function handleSelectionChange(brokerId: number, selectedIds: string[]) {
        // Remove deselected files from this broker
        selectedFiles = selectedFiles.filter((f) => f.brokerId !== brokerId || selectedIds.includes(f.fileId));

        // Add newly selected files with auto-picked plugin
        const existing = new Set(selectedFiles.map((f) => f.fileId));
        const brokerFiles = brokerFilesMap.get(brokerId) ?? [];
        for (const id of selectedIds) {
            if (!existing.has(id)) {
                const bf = brokerFiles.find((f) => f.file_id === id);
                if (bf) {
                    const pluginCode = filePluginOverrides.get(id) ?? pickBestPlugin(bf, brokerId);
                    selectedFiles = [...selectedFiles, {fileId: id, fileName: bf.filename, brokerId, pluginCode}];
                }
            }
        }
    }

    function updateFilePlugin(fileId: string, pluginCode: string) {
        filePluginOverrides = new Map(filePluginOverrides).set(fileId, pluginCode);
        selectedFiles = selectedFiles.map((f) => (f.fileId === fileId ? {...f, pluginCode} : f));
    }

    function getFileStatus(file: BrimFile): string {
        if (file.parse_is_stale) return 'stale';
        if (file.status === 'parsed') return 'parsed';
        if (file.status === 'failed') return 'error';
        return 'uploaded';
    }

    /** Ask for confirmation before deleting a broker import file (report) from Step 2. */
    function requestDeleteFile(file: BrimFile, brokerId: number) {
        pendingDeleteFile = {fileId: file.file_id, brokerId, fileName: file.filename};
        showDeleteFileConfirm = true;
    }

    /** Delete the pending report server-side, then drop it from local selection + broker map. */
    async function confirmDeleteFile() {
        const target = pendingDeleteFile;
        if (!target) return;
        try {
            await zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {
                params: {file_id: target.fileId},
            });
            selectedFiles = selectedFiles.filter((f) => f.fileId !== target.fileId);
            const map = new Map(brokerFilesMap);
            map.set(
                target.brokerId,
                (map.get(target.brokerId) ?? []).filter((f) => f.file_id !== target.fileId),
            );
            brokerFilesMap = map;
        } catch (e) {
            console.error('Delete report failed:', e);
            toasts.error($t('files.deleteFailed'));
        } finally {
            showDeleteFileConfirm = false;
            pendingDeleteFile = null;
        }
    }

    function cancelDeleteFile() {
        showDeleteFileConfirm = false;
        pendingDeleteFile = null;
    }

    // =========================================================================
    // Step 2: DataTable columns (shared across all broker tables)
    // =========================================================================

    // T5: per-file plugin column added
    const fileTableColumns: ColumnDef<BrimFile>[] = [
        {
            id: 'filename',
            header: () => $t('common.name'),
            cell: (row) => ({type: 'icon-text', icon: FileText, text: row.filename}) as const,
            type: 'text',
            sortable: true,
            filterable: true,
            width: 200,
            minWidth: 200,
        },
        {
            id: 'plugin',
            header: () => $t('importWizard.pluginLabel'),
            cell: (row) => {
                const sel = selectedFiles.find((s) => s.fileId === row.file_id);
                if (!sel) return '—';
                const compatible = (row.compatible_plugins as string[] | undefined) ?? [];
                return {
                    type: 'custom',
                    component: ImportPluginSelect,
                    props: {
                        value: sel.pluginCode,
                        compatiblePlugins: compatible.length > 0 ? compatible : undefined,
                        onchange: (v: string) => updateFilePlugin(row.file_id, v),
                        placeholder: $t('importWizard.selectPlugin'),
                        compact: true,
                    },
                } as const;
            },
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 200,
            minWidth: 180,
        },
        {
            id: 'uploaded_at',
            header: () => $t('common.date'),
            cell: (row) => ({type: 'date', value: row.uploaded_at, format: 'date'}) as const,
            type: 'date',
            sortable: true,
            filterable: false,
            width: 110,
            minWidth: 110,
        },
        {
            id: 'status',
            header: () => 'Status',
            cell: (row) => {
                const status = getFileStatus(row);
                const variant = status === 'parsed' ? 'success' : status === 'stale' ? 'warning' : status === 'error' ? 'error' : 'default';
                return {type: 'badge', text: $t(`importWizard.fileStatus.${status}`), variant} as const;
            },
            type: 'enum',
            enumOptions: [
                {value: 'uploaded', label: $t('importWizard.fileStatus.uploaded')},
                {value: 'parsed', label: $t('importWizard.fileStatus.parsed')},
                {value: 'stale', label: $t('importWizard.fileStatus.stale')},
                {value: 'error', label: $t('importWizard.fileStatus.error')},
            ],
            getValue: (row) => getFileStatus(row),
            sortable: false,
            filterable: true,
            width: 90,
            minWidth: 90,
        },
        {
            id: 'size',
            header: () => 'Size',
            cell: (row) => ({type: 'size', bytes: row.size_bytes}) as const,
            type: 'size',
            sortable: true,
            filterable: false,
            width: 80,
            minWidth: 60,
            hiddenByDefault: true,
        },
    ];

    // Per-broker DataTable refs for shared ColumnVisibilityToggle + resize sync
    let tableRefs: (DataTable<BrimFile> | undefined)[] = $state([]);

    /** Sync column resize across all broker tables */
    function handleColumnResize(sourceIdx: number, columnId: string, width: number) {
        for (let i = 0; i < tableRefs.length; i++) {
            if (i !== sourceIdx) tableRefs[i]?.setColumnWidth(columnId, width);
        }
    }

    // =========================================================================
    // Step 3: Parse Engine
    // =========================================================================

    function getBrokerName(brokerId: number): string {
        return brokers.find((b) => b.id === brokerId)?.name ?? `Broker #${brokerId}`;
    }

    function getPluginName(pluginCode: string): string {
        const cached = getCachedPlugins();
        if (cached) {
            const plugin = cached.find((p: {code: string; name: string}) => p.code === pluginCode);
            if (plugin) return plugin.name;
        }
        return pluginCode;
    }

    function initParseResults() {
        const newHash = computeParseHash();

        // Cache hit: same files+plugins as last parse, all terminal → skip
        if (lastParseHash === newHash && parseResults.length > 0 && parseDone) {
            usingCachedResults = true;
            return;
        }

        usingCachedResults = false;
        mergedTransactions = [];
        assetResolutions = [];
        assetGroups = [];
        duplicateGroups = [];
        duplicateFilePriorityIds = [];
        duplicateResolverTouchedKeys = new Set();
        duplicateResolverSelections = {};
        expandedDuplicateGroupKeys = new Set();

        // Build fresh ParsedFileResult[] from selectedFiles
        const results: ParsedFileResult[] = [];
        for (const file of selectedFiles) {
            const pluginName = getPluginName(file.pluginCode);
            const broker = brokers.find((b) => b.id === file.brokerId);
            results.push({
                fileId: file.fileId,
                fileName: file.fileName,
                brokerId: file.brokerId,
                brokerName: getBrokerName(file.brokerId),
                brokerIconUrl: broker?.icon_url ?? null,
                brokerPortalUrl: broker?.portal_url ?? null,
                pluginUsed: file.pluginCode,
                pluginName,
                status: 'pending',
                response: null,
            });
        }
        parseResults = results;
        syncDuplicateFilePriority();
        lastParseHash = newHash;
    }

    // Parses run in parallel too. The server off-loads each parse to its own process, so the
    // concurrency is real and not just queued behind one event loop (brim_parse_pool.py).
    // `parseResults` is mutated in place by reference, so order is untouched; the abort flag
    // stops new parses without pretending to unsend the ones already in flight.
    async function doParseAll() {
        abortParsing = false;
        const pending = parseResults.filter((f) => f.status === 'pending');

        await mapWithConcurrency(
            pending,
            async (file) => {
                file.status = 'parsing';
                parseResults = [...parseResults];

                try {
                    const res = await zodiosApi.parse_file_api_v1_brokers_import_files__file_id__parse_post({plugin_code: file.pluginUsed, broker_id: file.brokerId}, {params: {file_id: file.fileId}});
                    file.response = res as BrimParseResponse;
                    file.status = 'done';
                } catch (e) {
                    file.status = 'error';
                    file.errorMessage = extractErrorMessage(e);
                }

                parseResults = [...parseResults];
            },
            {shouldStop: () => abortParsing},
        );

        if (!abortParsing && parseHasSuccess) mergeAllTransactions();
    }

    function handleReparse() {
        usingCachedResults = false;
        parseResults = parseResults.map((r) => ({...r, status: 'pending' as const, response: null, errorMessage: undefined}));
        lastParseHash = computeParseHash();
        doParseAll();
    }

    function openParseDetail(result: ParsedFileResult) {
        parseDetailResult = result;
        showParseDetail = true;
    }

    function closeParseDetail() {
        showParseDetail = false;
        parseDetailResult = null;
    }

    // Step 3 DataTable columns
    const step3Columns: ColumnDef<ParsedFileResult>[] = [
        {
            id: 'fileName',
            header: () => $t('common.name'),
            cell: (row) => ({type: 'icon-text', icon: FileText, text: row.fileName}) as const,
            type: 'text',
            sortable: true,
            width: 250,
            minWidth: 200,
            getValue: (row) => row.fileName,
        },
        {
            id: 'brokerName',
            header: () => 'Broker',
            cell: (row) =>
                ({
                    type: 'custom',
                    component: BrokerBadge,
                    props: {
                        broker: getBrokerInfo(row.brokerId) ?? {id: row.brokerId, name: row.brokerName},
                        size: 20,
                        showName: true,
                        tooltip: row.brokerName,
                    },
                }) as const,
            type: 'text',
            sortable: true,
            width: 130,
            minWidth: 130,
            getValue: (row) => row.brokerName,
        },
        {
            id: 'pluginName',
            header: () => 'Plugin',
            cell: (row) => {
                const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
                const plugin = (getCachedPlugins() ?? []).find((p) => p.code === row.pluginUsed);
                const iconUrl = (plugin as {icon_url?: string | null} | undefined)?.icon_url;
                const name = row.pluginName || row.pluginUsed;
                const icon = iconUrl
                    ? `<img src="${esc(iconUrl)}" class="w-5 h-5 rounded-full object-cover shrink-0" alt="">`
                    : `<span class="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-500 shrink-0">${esc(name.charAt(0).toUpperCase())}</span>`;
                return {type: 'html', html: `<div class="flex items-center gap-1.5 min-w-0">${icon}<span class="truncate text-xs">${esc(name)}</span></div>`} as const;
            },
            type: 'text',
            sortable: true,
            width: 130,
            minWidth: 130,
            getValue: (row) => row.pluginName,
        },
        {
            id: 'status',
            header: () => 'Status',
            cell: (row) => {
                if (row.status === 'parsing') {
                    return {type: 'badge', text: $t('importWizard.fileParsing'), variant: 'info'} as const;
                }
                // Failed rows carry the reason in a tooltip: a bare "Error" badge tells
                // the user nothing about what went wrong.
                if (row.status === 'error') {
                    const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                    return {
                        type: 'html',
                        html: `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300">${esc($t('common.error'))}</span>`,
                        tooltip: {text: row.errorMessage ?? $t('common.error'), position: 'top', maxWidth: '28rem'},
                    } as const;
                }
                const variantMap: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
                    pending: 'default',
                    done: 'success',
                    error: 'error',
                };
                const labelMap: Record<string, string> = {
                    pending: $t('importWizard.filePending'),
                    done: $t('importWizard.fileDone'),
                    error: $t('common.error'),
                };
                return {type: 'badge', text: labelMap[row.status] ?? row.status, variant: variantMap[row.status] ?? 'default'} as const;
            },
            type: 'enum',
            enumOptions: [
                {value: 'pending', label: 'Pending'},
                {value: 'parsing', label: 'Parsing'},
                {value: 'done', label: 'Done'},
                {value: 'error', label: 'Error'},
            ],
            getValue: (row) => row.status,
            sortable: false,
            width: 100,
            minWidth: 100,
        },
        {
            id: 'txCount',
            header: () => '📊',
            headerTooltip: () => $t('importWizard.colTip.txCount'),
            cell: (row) => (row.response?.transactions?.length != null ? row.response.transactions.length : '—'),
            type: 'number',
            width: 40,
            minWidth: 32,
        },
        {
            id: 'assetCount',
            header: () => '🏦',
            headerTooltip: () => $t('importWizard.colTip.assetCount'),
            cell: (row) => {
                if (!row.response?.asset_mappings?.length) return '—';
                return row.response.asset_mappings.length;
            },
            type: 'number',
            width: 40,
            minWidth: 32,
        },
        {
            id: 'unresolvedCount',
            header: () => '✗',
            headerTooltip: () => $t('importWizard.colTip.unresolvedCount'),
            cell: (row) => {
                if (!row.response?.asset_mappings?.length) return '—';
                const unresolved = row.response.asset_mappings.filter((m) => m.selected_asset_id == null).length;
                if (unresolved === 0) return 0;
                return {type: 'html', html: `<span class="text-red-600 dark:text-red-400 font-medium">${unresolved}</span>`} as const;
            },
            type: 'number',
            width: 40,
            minWidth: 32,
        },
        {
            id: 'issueCount',
            header: () => '🔴',
            headerTooltip: () => $t('importWizard.colTip.issueCount'),
            cell: (row) => {
                const count = (row.response?.validation_issues as unknown[] | undefined)?.length ?? 0;
                if (row.status !== 'done') return '—';
                if (count === 0) return 0;
                return {type: 'html', html: `<span class="text-amber-600 dark:text-amber-400 font-medium">${count}</span>`} as const;
            },
            type: 'number',
            width: 40,
            minWidth: 32,
        },
        {
            id: 'todoCount',
            header: () => '🔧',
            headerTooltip: () => $t('importWizard.colTip.todoCount'),
            cell: (row) => {
                if (row.status !== 'done') return '—';
                const todos = (row.response?.field_todos as {severity: string}[] | undefined) ?? [];
                if (todos.length === 0) return 0;
                const hasBlocker = todos.some((t) => t.severity === 'blocker');
                const color = hasBlocker ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400';
                return {type: 'html', html: `<span class="${color} font-medium">${todos.length}</span>`} as const;
            },
            type: 'number',
            width: 40,
            minWidth: 32,
        },
        {
            id: 'warningCount',
            header: () => '⚠️',
            headerTooltip: () => $t('importWizard.colTip.warningCount'),
            cell: (row) => (row.response?.warnings?.length != null ? row.response.warnings.length : '—'),
            type: 'number',
            width: 40,
            minWidth: 32,
        },
    ];

    const step3RowActions: RowAction<ParsedFileResult>[] = [
        {
            id: 'viewDetail',
            label: () => $t('importWizard.viewDetail'),
            icon: Eye,
            disabled: (row) => row.status !== 'done',
            onClick: (row) => openParseDetail(row),
        },
        {
            id: 'reparse',
            label: () => $t('importWizard.reparseSingle'),
            icon: RefreshCw,
            visible: (row) => row.status === 'done' || row.status === 'error',
            onClick: (row) => reparseSingleFile(row),
        },
        {
            id: 'preview',
            label: () => $t('importWizard.previewFile'),
            icon: FileText,
            visible: (row) => row.status === 'done',
            onClick: (row) => openPreview(row.fileId),
        },
    ];

    async function reparseSingleFile(result: ParsedFileResult) {
        result.status = 'pending';
        result.response = null;
        result.errorMessage = undefined;
        parseResults = [...parseResults];

        // Parse just this one file
        result.status = 'parsing';
        parseResults = [...parseResults];
        try {
            const res = await zodiosApi.parse_file_api_v1_brokers_import_files__file_id__parse_post({plugin_code: result.pluginUsed, broker_id: result.brokerId}, {params: {file_id: result.fileId}});
            result.response = res as BrimParseResponse;
            result.status = 'done';
        } catch (e) {
            result.status = 'error';
            result.errorMessage = extractErrorMessage(e);
        }
        parseResults = [...parseResults];
        mergeAllTransactions();
    }

    // =========================================================================
    // File Preview
    // =========================================================================

    let showPreviewModal = $state(false);
    let previewLoading = $state(false);
    let previewError = $state<string | null>(null);
    let previewData = $state<FilePreviewResponse | null>(null);
    let previewFileId = $state<string | null>(null);
    let previewRequestToken = 0;
    /** z-index for FilePreviewModal — set dynamically based on the caller's z-index. */
    let previewZIndex = $state(untrack(() => zIndex + 20));
    /** 1-based lines to tint, when the preview is opened from specific rows. */
    let previewHighlightRows = $state<number[]>([]);

    async function openPreview(fileId: string, callerZIndex?: number, highlightRows?: number[]) {
        previewZIndex = (callerZIndex ?? zIndex) + 20;
        previewHighlightRows = highlightRows ?? [];
        previewFileId = fileId;
        showPreviewModal = true;
        previewData = null;
        previewError = null;
        await loadPreview();
    }

    async function loadPreview(sheetName?: string) {
        if (!previewFileId) return;
        const token = ++previewRequestToken;
        previewLoading = true;
        previewError = null;
        try {
            const response = await fetchFilePreview({source: 'brim', fileId: previewFileId}, sheetName);
            if (token === previewRequestToken) previewData = response;
        } catch (error) {
            if (token === previewRequestToken) {
                previewData = null;
                previewError = getFilePreviewError(error, 'Preview failed');
            }
        } finally {
            if (token === previewRequestToken) previewLoading = false;
        }
    }

    /**
     * Opens the file a flagged row came from, scrolled to that row. A charge line often
     * cannot be judged on its own — what it was charged on is written on a neighbouring
     * row — and the one-row evidence table has no neighbours to show.
     */
    async function openSourceRow(index: number, rowNumbers: number[]) {
        const fileId = mergedTransactions.find((m) => m.index === index)?.sourceFileId;
        if (!fileId) return;
        await openPreview(fileId, undefined, rowNumbers);
    }

    function closePreviewModal() {
        previewRequestToken += 1;
        showPreviewModal = false;
        previewLoading = false;
        previewError = null;
        previewData = null;
        previewFileId = null;
        previewHighlightRows = [];
    }
</script>

<ModalBase {open} {zIndex} maxWidth="6xl" onRequestClose={handleClose} testId="import-wizard-modal" closeOnBackdropClick={true}>
    <!-- ================================================================== -->
    <!-- Header -->
    <!-- ================================================================== -->
    <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{$t('importWizard.title')}</h2>
        <button type="button" class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 dark:text-gray-500" onclick={handleClose} data-testid="import-wizard-close">
            <span class="sr-only">Close</span>
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
    </div>

    <!-- ================================================================== -->
    <!-- Stepper Bar -->
    <!-- ================================================================== -->
    <div class="flex items-center justify-center gap-0 px-6 py-3 border-b border-gray-100 dark:border-gray-800" data-testid="import-wizard-stepper">
        {#each visibleSteps as step, i}
            {@const stepNum = i + 1}
            {@const isCompleted = i < currentStepIndex}
            {@const isCurrent = i === currentStepIndex}
            {@const isFuture = i > currentStepIndex}
            {@const isClickable = i < currentStepIndex}

            {#if i > 0}
                <div class="w-8 sm:w-12 h-0.5 mx-1 {isCompleted || isCurrent ? 'bg-libre-green' : 'bg-gray-200 dark:bg-gray-700'}"></div>
            {/if}

            <button
                type="button"
                class="flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors
                    {isClickable ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700' : 'cursor-default'}
                    {isCurrent ? 'font-semibold' : ''}"
                onclick={() => isClickable && goToStep(step.id)}
                disabled={isFuture}
                aria-current={isCurrent ? 'step' : undefined}
                data-testid="import-wizard-step-{stepNum}"
                data-step-id={step.id}
            >
                <span
                    class="flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
                        {isCompleted ? 'bg-libre-green text-white' : ''}
                        {isCurrent ? 'bg-libre-green text-white' : ''}
                        {isFuture ? 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400' : ''}"
                >
                    {#if isCompleted}
                        <Check size={14} />
                    {:else}
                        {stepNum}
                    {/if}
                </span>
                <span class="hidden sm:inline text-xs {isFuture ? 'text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-200'}">
                    {$t(`importWizard.${step.titleKey}`)}
                </span>
            </button>
        {/each}
    </div>

    <!-- ================================================================== -->
    <!-- Content -->
    <!-- ================================================================== -->
    <div class="p-5 space-y-4 max-h-[65vh] overflow-y-auto">
        <!-- ============================================================ -->
        <!-- Step 1: Upload & Assign Broker -->
        <!-- ============================================================ -->
        {#if currentStepId === 'upload'}
            <div class="space-y-4" data-testid="import-wizard-step1" data-busy={brokersLoading || uploading}>
                <!-- Info hint -->
                <p class="text-xs text-gray-500 dark:text-gray-400 italic">{$t('importWizard.step1Optional')}</p>

                <!-- Upload error banner -->
                {#if uploadError}
                    <InfoBanner variant="error" message={uploadError} dismissible ondismiss={() => (uploadError = null)} />
                {/if}

                <!-- T2: Collapsible drop zone -->
                {#if dropZoneExpanded}
                    <div bind:this={dropZoneContainerRef}>
                        <FileUploader bind:this={fileUploaderRef} on:change={handleFilesChanged} on:error={(e) => (uploadError = e.detail.message)} multiple={true} accept=".csv,.xlsx,.xls" hideActions={true} />
                    </div>
                {:else}
                    <button
                        type="button"
                        class="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 text-sm text-gray-500 dark:text-gray-400 hover:border-libre-green hover:text-libre-green dark:hover:text-libre-green transition-colors"
                        onclick={() => (dropZoneExpanded = true)}
                        data-testid="import-wizard-upload-more"
                    >
                        <Plus size={16} />
                        {$t('importWizard.uploadMore')}
                    </button>
                {/if}

                <!-- Pending files DataTable -->
                {#if pendingFiles.length > 0}
                    <div class="space-y-3">
                        <!-- "Assign all" global broker -->
                        <div class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-slate-800 rounded-lg">
                            <span class="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">{$t('importWizard.globalBroker')}:</span>
                            <div class="flex-1 max-w-xs" data-testid="import-wizard-step1-broker-select">
                                <BrokerSearchSelect
                                    {brokers}
                                    value={globalBrokerId}
                                    onchange={onGlobalBrokerChange}
                                    placeholder={$t('common.broker')}
                                    createLabel={$t('common.createNew')}
                                    onCreateNew={() => {
                                        createBrokerContext = 'global';
                                        createBrokerOpen = true;
                                    }}
                                />
                            </div>
                        </div>

                        <!-- Toolbar for bulk actions on selected files -->
                        {#if step1SelectedIds.length > 0}
                            <DataTableToolbar
                                selectedCount={step1SelectedIds.length}
                                bulkActions={[
                                    {
                                        id: 'bulk-delete',
                                        icon: Trash2,
                                        label: () => $t('common.remove'),
                                        variant: 'danger',
                                        onClick: () => {
                                            removePendingFilesByIds(step1SelectedIds);
                                            step1SelectedIds = [];
                                            step1TableRef?.clearSelection();
                                        },
                                    },
                                ]}
                                onClearSelection={() => {
                                    step1SelectedIds = [];
                                    step1TableRef?.clearSelection();
                                }}
                            />
                        {/if}

                        <!-- Files DataTable with selection -->
                        <DataTable
                            bind:this={step1TableRef}
                            data={pendingFiles}
                            columns={pendingFileColumns}
                            getRowId={(row) => row.id}
                            storageKey="import-wizard-pending"
                            enableSelection={true}
                            selectionMode="multi"
                            onSelectionChange={(ids) => (step1SelectedIds = ids)}
                            enableActions={true}
                            actionsColumnWidth="64px"
                            rowActions={pendingFileActions}
                            enableSorting={false}
                            enableColumnFilters={false}
                            enableColumnResize={false}
                            enablePagination={false}
                            enableColumnVisibility={false}
                            defaultPageSize={100}
                            tableLayout="auto"
                            stickyActions={false}
                            enableContextMenu={true}
                        />
                    </div>
                {/if}
            </div>

            <!-- ============================================================ -->
            <!-- Step 2: Select Files from Broker Panels (DataTable) -->
            <!-- ============================================================ -->
        {:else if currentStepId === 'select'}
            <div class="space-y-4" data-testid="import-wizard-step2" data-busy={brokerFilesLoading || uploading}>
                {#if brokerFilesLoading}
                    <div class="py-8 text-center">
                        <LoadingSpinner size="md" />
                    </div>
                {:else}
                    <!-- Header: selected count + column visibility -->
                    <div class="flex items-center justify-between flex-wrap gap-2">
                        <span class="text-sm font-medium text-gray-700 dark:text-gray-200">
                            {$t('importWizard.selectedCount', {values: {n: selectedFiles.length, b: selectedBrokerCount}})}
                        </span>
                        <div class="flex items-center gap-2">
                            <ColumnVisibilityToggle tableRef={tableRefs[0]} additionalTableRefs={tableRefs.slice(1)} />
                        </div>
                    </div>

                    <!-- Pre-selected hint -->
                    {#if pendingFiles.some((f) => f.status === 'uploaded')}
                        <p class="text-xs text-libre-green italic">{$t('importWizard.preSelectedHint')}</p>
                    {/if}

                    <!-- Broker panels with DataTable -->
                    {#each brokers as broker, brokerIdx}
                        {@const brokerFiles = brokerFilesMap.get(broker.id) ?? []}
                        {#if brokerFiles.length > 0}
                            <div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                                <!-- Broker header (collapsible) -->
                                <button type="button" class="w-full flex items-center gap-2 px-3 py-2.5 bg-gray-50 dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-750 text-left" onclick={() => toggleBrokerExpand(broker.id)}>
                                    {#if expandedBrokers.has(broker.id)}
                                        <ChevronDown size={14} class="text-gray-400" />
                                    {:else}
                                        <ChevronRight size={14} class="text-gray-400" />
                                    {/if}
                                    <BrokerIcon brokerId={broker.id} iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size="sm" />
                                    <span class="font-medium text-sm text-gray-800 dark:text-gray-200">{broker.name}</span>
                                    {#if selectedFiles.filter((f) => f.brokerId === broker.id).length > 0}
                                        <span class="text-xs font-medium text-libre-green ml-1">({selectedFiles.filter((f) => f.brokerId === broker.id).length})</span>
                                    {/if}
                                    <span class="text-xs text-gray-400 ml-auto">{brokerFiles.length} file(s)</span>
                                </button>

                                <!-- DataTable per broker -->
                                {#if expandedBrokers.has(broker.id)}
                                    <div class="border-t border-gray-200 dark:border-gray-700">
                                        <DataTable
                                            bind:this={tableRefs[brokerIdx]}
                                            data={brokerFiles}
                                            columns={fileTableColumns}
                                            getRowId={(row) => row.file_id}
                                            storageKey={`import-wizard-files-${broker.id}`}
                                            enableSelection={true}
                                            selectionMode="multi"
                                            initialSelectedIds={selectedFiles.filter((f) => f.brokerId === broker.id).map((f) => f.fileId)}
                                            onSelectionChange={(ids) => handleSelectionChange(broker.id, ids)}
                                            onRowDoubleClick={(row) => openPreview(row.file_id)}
                                            enableActions={true}
                                            actionsColumnWidth="64px"
                                            rowActions={[
                                                {id: 'preview', icon: Eye, label: $t('common.preview'), onClick: (row) => openPreview(row.file_id)},
                                                {id: 'delete', icon: Trash2, label: $t('common.delete'), variant: 'danger', onClick: (row) => requestDeleteFile(row, broker.id)},
                                            ]}
                                            enableSorting={true}
                                            enableColumnFilters={true}
                                            enableColumnResize={true}
                                            enablePagination={false}
                                            enableColumnVisibility={false}
                                            defaultPageSize={100}
                                            tableLayout="auto"
                                            stickyActions={false}
                                            enableContextMenu={true}
                                            initialFilters={undefined}
                                            onColumnResize={(colId, w) => handleColumnResize(brokerIdx, colId, w)}
                                        />
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    {/each}

                    <!-- No files at all -->
                    {#if brokers.every((b) => (brokerFilesMap.get(b.id) ?? []).length === 0)}
                        <div class="py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                            <p>{$t('importWizard.noFiles')}</p>
                            <p class="text-xs mt-1">{$t('importWizard.noFilesHint')}</p>
                        </div>
                    {/if}
                {/if}
            </div>

            <!-- ============================================================ -->
            <!-- Step 3: Parse Engine -->
            <!-- ============================================================ -->
        {:else if currentStepId === 'analyze'}
            <div class="flex flex-col gap-4 p-4" data-testid="import-wizard-step3" data-parse-state={parseState}>
                <!-- Progress bar -->
                <div class="space-y-1">
                    <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                        {#if usingCachedResults}
                            <span class="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                                <CheckCircle size={14} />
                                {$t('importWizard.cachedResults')}
                            </span>
                        {:else if parseDone}
                            <span>{$t('importWizard.parseComplete')}</span>
                        {:else}
                            <span>{$t('importWizard.parsingProgress', {values: {done: parseCompletedCount, total: parseTotalCount}})}</span>
                        {/if}
                        <span>{parseCompletedCount}/{parseTotalCount}</span>
                    </div>
                    <div class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all duration-300 ease-out" class:bg-libre-green={!parseHasErrors} class:bg-amber-500={parseHasErrors} style="width: {parseTotalCount > 0 ? (parseCompletedCount / parseTotalCount) * 100 : 0}%"></div>
                    </div>
                </div>

                <!-- Parse failures: show WHY, not just "Error".
                     Without this the only signal is a red badge, which is useless for
                     diagnosing e.g. a stale client bundle rejecting a new response shape. -->
                {#if parseFailures.length > 0}
                    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-xs" data-testid="import-wizard-parse-errors">
                        <div class="font-medium text-red-800 dark:text-red-200 mb-1.5">
                            {$t('importWizard.parseErrorsTitle', {values: {n: parseFailures.length}})}
                        </div>
                        <ul class="space-y-1">
                            {#each parseFailures as failure}
                                <li class="text-red-700 dark:text-red-300">
                                    <span class="font-medium">{failure.fileName}</span>
                                    <span class="opacity-80"> — {failure.errorMessage ?? $t('common.error')}</span>
                                </li>
                            {/each}
                        </ul>
                    </div>
                {/if}

                <!-- Results DataTable -->
                <DataTable
                    data={parseResults}
                    columns={step3Columns}
                    getRowId={(row) => row.fileId}
                    storageKey="import-wizard-parse-results"
                    enableSelection={false}
                    enableActions={true}
                    actionsColumnWidth="64px"
                    rowActions={step3RowActions}
                    onRowDoubleClick={(row) => {
                        if (row.status === 'done') openParseDetail(row);
                    }}
                    enableSorting={true}
                    enableColumnFilters={false}
                    enablePagination={false}
                    enableColumnVisibility={false}
                    defaultPageSize={100}
                    tableLayout="auto"
                    stickyActions={false}
                    enableContextMenu={true}
                />

                <!-- Aggregate summary -->
                {#if parseHasSuccess}
                    {@const stats = parseAggregateStats()}
                    <div class="grid grid-cols-2 md:grid-cols-8 gap-3 p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                        <div class="text-center">
                            <div class="text-lg font-semibold text-gray-900 dark:text-white">{stats.totalTx}</div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.txCount', {values: {n: stats.totalTx, k: stats.doneFileCount}})}</div>
                        </div>
                        <div class="text-center">
                            <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                {stats.uniqueAssets}
                                {#if stats.unresolvedCount > 0}
                                    <span class="text-amber-500 text-sm">({stats.unresolvedCount}?)</span>
                                {/if}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.assetsCount', {values: {n: stats.uniqueAssets, m: stats.unresolvedCount}})}</div>
                        </div>
                        <div class="text-center">
                            <div class="text-lg font-semibold" class:text-amber-500={stats.totalIssues > 0} class:text-gray-900={stats.totalIssues === 0} class:dark:text-white={stats.totalIssues === 0}>{stats.totalIssues}</div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.validationIssueCount', {values: {n: stats.totalIssues}})}</div>
                        </div>
                        <div class="text-center">
                            <div
                                class="text-lg font-semibold"
                                class:text-red-600={stats.todoBlockers > 0}
                                class:dark:text-red-400={stats.todoBlockers > 0}
                                class:text-amber-500={stats.todoBlockers === 0 && stats.totalTodos > 0}
                                class:text-gray-900={stats.totalTodos === 0}
                                class:dark:text-white={stats.totalTodos === 0}
                            >
                                {stats.totalTodos}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.fieldTodoCount', {values: {n: stats.totalTodos}})}</div>
                        </div>
                        <div class="text-center">
                            <div class="text-lg font-semibold" class:text-amber-500={stats.totalWarnings > 0} class:text-gray-900={stats.totalWarnings === 0} class:dark:text-white={stats.totalWarnings === 0}>{stats.totalWarnings}</div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.warningsCount', {values: {n: stats.totalWarnings}})}</div>
                        </div>
                        <div class="text-center">
                            <div class="text-lg font-semibold" class:text-amber-500={stats.likelyDuplicates > 0} class:text-gray-900={stats.likelyDuplicates === 0} class:dark:text-white={stats.likelyDuplicates === 0}>{stats.likelyDuplicates}</div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.likelyDuplicates', {values: {n: stats.likelyDuplicates}})}</div>
                        </div>
                        <!-- View All action cell -->
                        {#if parseDone || usingCachedResults}
                            <button
                                type="button"
                                class="flex flex-col items-center justify-center gap-1 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 text-blue-600 dark:text-blue-400 transition-colors px-2 py-1.5"
                                data-testid="import-wizard-view-all"
                                onclick={() => {
                                    showAggregateDetail = true;
                                }}
                            >
                                <Eye size={16} />
                                <span class="text-xs font-medium">{$t('importWizard.viewAll')}</span>
                            </button>
                            <button
                                type="button"
                                class="flex flex-col items-center justify-center gap-1 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors px-2 py-1.5"
                                data-testid="import-wizard-reparse"
                                onclick={handleReparse}
                            >
                                <RefreshCw size={16} />
                                <span class="text-xs font-medium">{$t('importWizard.reparse')}</span>
                            </button>
                        {/if}
                    </div>
                {/if}
            </div>

            <!-- ============================================================ -->
            <!-- Step ASSETS: how many distinct securities are really here -->
            <!-- ============================================================ -->
        {:else if currentStepId === 'assets'}
            <div class="space-y-4" data-testid="import-wizard-step-assets">
                <AssetGroupStep
                    groups={assetGroups}
                    txCounts={assetGroupTxCounts}
                    resolvedIds={assetGroupResolvedIds}
                    resolvedNames={assetGroupResolvedNames}
                    primaries={assetGroupPrimary}
                    touched={assetGroupingTouched}
                    onpartition={applyGroupPartition}
                    onconfirm={confirmGroupProposal}
                    onprimary={electGroupPrimary}
                    onreset={resetGrouping}
                    oninspect={openAssetInspector}
                />
            </div>

            <!-- ============================================================ -->
            <!-- Step FIX: correct the rows the plugin flagged -->
            <!-- ============================================================ -->
        {:else if currentStepId === 'fix'}
            <div class="space-y-4" data-testid="import-wizard-step-fix">
                <FixFlaggedStep
                    rows={fixStepRows}
                    analysisAssets={fixAnalysisAssets}
                    expanded={fixExpandedIndices}
                    createdAssets={fixCreatedAssets}
                    ontoggle={toggleFixRow}
                    onapply={applyFixToRow}
                    onaccept={acceptPluginFallback}
                    onacceptall={acceptAllPluginFallbacks}
                    onreset={resetFixRow}
                    onresetall={resetAllFixRows}
                    onreopen={reopenFixRow}
                    oncreateasset={(index, query) => {
                        fixCreateAssetQuery = query;
                        fixCreateAssetIndex = index;
                    }}
                    ongotosource={openSourceRow}
                />
            </div>

            <!-- ============================================================ -->
            <!-- Step DUPLICATES: arbitrate against the database -->
            <!-- ============================================================ -->
        {:else if currentStepId === 'duplicates'}
            <div class="space-y-4" data-testid="import-wizard-step-duplicates">
                <InfoBanner variant="info" message={$t('importWizard.duplicatesStepIntro')} />
                {#if duplicateRecheckError}
                    <InfoBanner variant="error" message={$t('importWizard.duplicateRecheckFailed', {values: {error: duplicateRecheckError}})} />
                {/if}

                {#if duplicateGroups.length > 0}
                    <section class="rounded-lg border border-gray-200 bg-gray-50/60 dark:border-slate-700 dark:bg-slate-800/40" data-testid="import-wizard-duplicate-resolver">
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 border-gray-200 px-3 py-2 text-left dark:border-slate-700"
                            class:border-b={!duplicateResolverCollapsed}
                            onclick={() => (duplicateResolverCollapsed = !duplicateResolverCollapsed)}
                            data-testid="import-wizard-duplicate-resolver-toggle"
                        >
                            {#if duplicateResolverCollapsed}
                                <ChevronRight size={16} class="shrink-0 text-gray-400" />
                            {:else}
                                <ChevronDown size={16} class="shrink-0 text-gray-400" />
                            {/if}
                            <div class="min-w-0 flex-1">
                                <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100">{$t('importWizard.resolver.title')}</h3>
                                <p class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.resolver.subtitle', {values: {n: duplicateGroups.length}})}</p>
                            </div>
                            <span
                                class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 {resolverPartialCount > 0
                                    ? 'bg-orange-100 text-orange-800 ring-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:ring-orange-700'
                                    : 'bg-emerald-100 text-emerald-800 ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-700'}"
                                data-testid="import-wizard-resolver-status"
                            >
                                {resolverPartialCount > 0 ? $t('importWizard.resolver.statusToVerify', {values: {n: resolverPartialCount}}) : $t('importWizard.resolver.statusAllAuto')}
                            </span>
                        </button>

                        <div class="min-w-0 gap-3 p-3 lg:grid-cols-[var(--priority-w)_minmax(0,1fr)] {duplicateResolverCollapsed ? 'hidden' : 'grid'}" style="--priority-w: {duplicatePriorityWidth}px">
                            <div class="relative min-w-0 space-y-2 rounded-lg border border-gray-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900/60" data-testid="import-wizard-file-priority">
                                <div class="text-xs font-semibold tracking-wide text-gray-500 uppercase dark:text-gray-400">{$t('importWizard.resolver.filePriority')}</div>
                                <p class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.resolver.priorityPanelHint')}</p>
                                <OrderableList
                                    items={duplicateFilePriorityIds}
                                    keyFn={(id) => id}
                                    onReorder={(ids) => {
                                        duplicateFilePriorityIds = ids;
                                        reapplyResolverGroups();
                                    }}
                                    compact
                                >
                                    {#snippet children({item, index})}
                                        <div class="flex min-w-0 items-center gap-2" data-testid="import-wizard-priority-file-{item}">
                                            <span class="w-5 shrink-0 text-xs font-semibold text-gray-400">{index + 1}</span>
                                            <span use:scrollOnOverflow class="{overflowScrollTextClass} flex-1 text-xs text-gray-700 dark:text-gray-200" title={getSourceFileName(item)}>{getSourceFileName(item)}</span>
                                        </div>
                                    {/snippet}
                                </OrderableList>
                                <div class="flex justify-end">
                                    <button
                                        type="button"
                                        class="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:bg-slate-800 dark:text-gray-200 dark:hover:bg-slate-700"
                                        onclick={recalcResolverDefaults}
                                        data-testid="import-wizard-resolver-recalc"
                                    >
                                        <RefreshCw size={13} />
                                        {$t('importWizard.resolver.recalcDefaults')}
                                    </button>
                                </div>
                                <!-- Drag handle: file names are long and unpredictable, so the split
                                     between the priority list and the groups is the user's to make. -->
                                <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                                <div role="separator" aria-orientation="vertical" class="absolute top-0 -right-2 hidden h-full w-2 cursor-col-resize touch-none lg:block" onpointerdown={startPriorityResize} data-testid="import-wizard-priority-resize">
                                    <span class="absolute top-1/2 left-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded bg-gray-300 dark:bg-slate-600"></span>
                                </div>
                            </div>

                            <div class="min-w-0 space-y-2">
                                {#each resolverTierPanels as panel (panel.tier)}
                                    {@const tierOpen = expandedDuplicateTiers.has(panel.tier)}
                                    <section class="min-w-0 overflow-hidden rounded-lg border border-gray-200 dark:border-slate-700" data-testid="import-wizard-resolver-tier-{panel.tier}">
                                        <button
                                            type="button"
                                            class="flex w-full items-center gap-2 bg-gray-50 px-3 py-2 text-left hover:bg-gray-100 dark:bg-slate-800/70 dark:hover:bg-slate-800"
                                            onclick={() => toggleDuplicateTier(panel.tier)}
                                            data-testid="import-wizard-resolver-tier-toggle-{panel.tier}"
                                        >
                                            {#if tierOpen}
                                                <ChevronDown size={14} class="shrink-0 text-gray-400" />
                                            {:else}
                                                <ChevronRight size={14} class="shrink-0 text-gray-400" />
                                            {/if}
                                            <span class="min-w-0 flex-1 text-sm font-medium text-gray-800 dark:text-gray-100">
                                                {panel.tier === 'sure' ? $t('importWizard.resolver.tierTotalTitle') : $t('importWizard.resolver.tierPartialTitle')}
                                            </span>
                                            <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 {duplicateTierBadgeClass(panel.tier)}">
                                                {$t('importWizard.resolver.groupCount', {values: {n: panel.groups.length}})}
                                            </span>
                                        </button>
                                        {#if tierOpen}
                                            <div class="min-w-0 space-y-2 border-t border-gray-100 p-2 dark:border-slate-700/60">
                                                {#each panel.groups as group (group.key)}
                                                    <div class="min-w-0 overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-900/60" data-testid="import-wizard-duplicate-group">
                                                        <button type="button" class="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-slate-800/60" onclick={() => toggleDuplicateGroup(group.key)}>
                                                            {#if expandedDuplicateGroupKeys.has(group.key)}
                                                                <ChevronDown size={14} class="shrink-0 text-gray-400" />
                                                            {:else}
                                                                <ChevronRight size={14} class="shrink-0 text-gray-400" />
                                                            {/if}
                                                            <span use:scrollOnOverflow class="{overflowScrollTextClass} flex-1 text-sm font-medium text-gray-800 dark:text-gray-100">{getDuplicateGroupTitle(group)}</span>
                                                            <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-slate-700 dark:text-gray-300">{$t('importWizard.resolver.memberCount', {values: {n: group.memberIndices.length}})}</span>
                                                            <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 {duplicateTierBadgeClass(group.tier)}" title={$t('importWizard.resolver.similarityTooltip')}>{duplicateSimilarityLabel(group.tier)}</span>
                                                        </button>

                                                        {#if expandedDuplicateGroupKeys.has(group.key)}
                                                            <div class="min-w-0 border-t border-gray-100 p-3 dark:border-slate-700/60">
                                                                <div class="mb-2 flex items-center justify-between gap-2">
                                                                    <p class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.resolver.groupHelp')}</p>
                                                                    <div class="flex shrink-0 items-center gap-3">
                                                                        <button type="button" class="inline-flex items-center gap-1 text-xs text-libre-green hover:underline" onclick={() => openLotCompare(group)} data-testid="import-wizard-resolver-compare-{group.key}">
                                                                            <Search size={13} />
                                                                            {$t('importWizard.compareModal.openAction')}
                                                                        </button>
                                                                        {#if resolverHasManualChoice(group)}
                                                                            <button type="button" class="text-xs text-libre-green hover:underline" onclick={() => resetDuplicateResolverChoice(group)} data-testid="import-wizard-resolver-reset">
                                                                                {$t('importWizard.resolver.resetDefault')}
                                                                            </button>
                                                                        {/if}
                                                                    </div>
                                                                </div>
                                                                <div use:marqueeDescendants class="min-w-0" data-testid="import-wizard-resolver-member-table-{group.key}">
                                                                    <DataTable
                                                                        data={resolverGroupMembers(group)}
                                                                        columns={resolverMemberColumns(group)}
                                                                        getRowId={(mt) => String(mt.index)}
                                                                        storageKey="import-wizard-resolver-members"
                                                                        enableSelection={false}
                                                                        enableActions={false}
                                                                        enablePagination={false}
                                                                        enableSorting={false}
                                                                        enableColumnFilters={false}
                                                                        enableColumnVisibility={false}
                                                                        enableColumnResize={false}
                                                                        enableContextMenu={false}
                                                                        stickyHeader={false}
                                                                        tableLayout="fixed"
                                                                    />
                                                                </div>
                                                            </div>
                                                        {/if}
                                                    </div>
                                                {/each}
                                            </div>
                                        {/if}
                                    </section>
                                {/each}
                            </div>
                        </div>
                    </section>
                {/if}
            </div>

            <!-- ============================================================ -->
            <!-- Step 4: Review & Import -->
            <!-- ============================================================ -->
        {:else if currentStepId === 'review'}
            <div class="flex flex-col gap-4 h-full overflow-y-auto" data-testid="import-wizard-step4" data-busy={autoFixingBrokerId !== null || recheckingOpenings} data-selected-count={step4SelectedCount} data-total-count={step4TotalCount}>
                <!-- ── Resolve Assets section ─────────────────────────── -->
                {#if assetResolutions.length > 0}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden" data-testid="import-wizard-resolve-section">
                        <!-- Section header -->
                        <button
                            type="button"
                            class="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-slate-800/50 hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors"
                            onclick={() => (step4ShowResolveSection = !step4ShowResolveSection)}
                            data-testid="import-wizard-resolve-toggle"
                        >
                            <div class="flex items-center gap-2">
                                {#if step4ShowResolveSection}<ChevronDown size={16} />{:else}<ChevronRight size={16} />{/if}
                                <span class="font-semibold text-sm">{$t('importWizard.resolveAssets')}</span>
                                {#if step4UnresolvedCount > 0}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                                        {step4UnresolvedCount}
                                        {$t('importWizard.unresolvedCount', {values: {n: step4UnresolvedCount}})}
                                    </span>
                                {:else}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                                        <Check size={12} class="mr-1" />{$t('importWizard.allResolved')}
                                    </span>
                                {/if}
                            </div>
                        </button>

                        {#if step4ShowResolveSection}
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 p-3">
                                {#each assetResolutions as res (res.fakeAssetId)}
                                    {@const isResolved = res.resolvedAssetId !== null}
                                    <div class="border rounded-lg p-3 {isResolved ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50/30 dark:bg-emerald-900/10' : 'border-gray-200 dark:border-gray-700'}">
                                        <!-- Card header — name + badges on same flex-wrap row, TX count right -->
                                        <div class="flex items-start justify-between gap-2 mb-1">
                                            <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1 flex-1 min-w-0">
                                                <span class="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate max-w-full">
                                                    {res.extractedName ?? res.extractedSymbol ?? '?'}
                                                </span>
                                                {#if res.extractedSymbol}
                                                    {@const tc = getIndexColor(0, 200)}
                                                    <span class="font-mono text-xs px-1.5 py-0.5 rounded-full shrink-0" style="background-color:{tc.bg};color:{tc.text}">
                                                        Ticker: {res.extractedSymbol}
                                                    </span>
                                                {/if}
                                                {#if res.extractedIsin}
                                                    {@const ic = getIndexColor(1, 200)}
                                                    <span class="font-mono text-xs px-1.5 py-0.5 rounded-full shrink-0" style="background-color:{ic.bg};color:{ic.text}">
                                                        ISIN: {res.extractedIsin}
                                                    </span>
                                                {/if}
                                            </div>
                                            <span class="shrink-0 text-xs font-medium text-gray-500 bg-gray-100 dark:bg-slate-700 px-1.5 py-0.5 rounded whitespace-nowrap">
                                                {res.txCount} TX
                                            </span>
                                        </div>
                                        <div class="text-xs text-gray-400 mb-3 truncate">{res.sourceFiles.join(', ')}</div>

                                        <!-- AssetSelect: candidates pinned at top via suggestedIds prop -->
                                        <AssetSelect
                                            value={res.resolvedAssetId}
                                            placeholder={$t('importWizard.searchAll')}
                                            compact={true}
                                            createLabel={$t('importWizard.createNew')}
                                            onCreateNew={() => startCreateAsset(res)}
                                            suggestedIds={res.candidates.map((c) => ({
                                                id: c.asset_id,
                                                badge: $t(`importWizard.confidence.${c.match_confidence.toLowerCase()}`) || c.match_confidence,
                                                badgeClass: confidenceBadgeClass(c.match_confidence.toLowerCase()),
                                                badgeTooltip: $t(`importWizard.confidenceTip.${c.match_confidence.toLowerCase()}`) || c.match_confidence,
                                            }))}
                                            onchange={(id) => {
                                                if (id !== null) resolveAssetManual(res.fakeAssetId, id, res);
                                                else clearResolution(res.fakeAssetId);
                                            }}
                                        />
                                        {#if duplicateCandidates(res).length >= 2}
                                            <div class="mt-1.5 flex items-center gap-2 rounded border border-amber-300 bg-amber-50 px-2 py-1.5 dark:border-amber-700/60 dark:bg-amber-900/20" data-testid="import-wizard-duplicate-hint-{res.fakeAssetId}">
                                                <AlertTriangle size={13} class="shrink-0 text-amber-500" />
                                                <span class="min-w-0 flex-1 text-[11px] text-gray-600 dark:text-gray-300">{$t('importWizard.duplicateAssetHint')}</span>
                                                <button type="button" class="shrink-0 rounded bg-amber-600 px-2 py-0.5 text-[11px] font-medium text-white hover:bg-amber-700" onclick={() => openMergeFromCard(res)} data-testid="import-wizard-merge-assets-{res.fakeAssetId}">
                                                    {$t('importWizard.duplicateAssetMerge')}
                                                </button>
                                            </div>
                                        {/if}
                                        {#if res.resolvedAssetId !== null}
                                            <button
                                                type="button"
                                                class="ml-auto mt-1.5 flex w-fit items-center gap-1 text-xs text-gray-500 hover:text-libre-green disabled:opacity-50 dark:text-gray-400"
                                                onclick={() => void openAssetInspector(res.resolvedAssetId!)}
                                                disabled={inspectAssetLoading}
                                                title={$t('importWizard.inspectAssetHint')}
                                                data-testid="import-wizard-inspect-asset-{res.fakeAssetId}"
                                            >
                                                <Pencil size={12} />
                                                {$t('importWizard.inspectAsset')}
                                            </button>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        {/if}
                    </div>
                {/if}

                {#if brokerOpeningIssues.length > 0}
                    <div class="space-y-2 mb-3" data-testid="import-wizard-broker-opening-issues">
                        {#each brokerOpeningIssues as issue (issue.brokerId)}
                            <div class="flex flex-col gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 dark:border-amber-700/60 dark:bg-amber-900/20 sm:flex-row sm:items-center sm:gap-3">
                                <div class="flex min-w-0 flex-1 items-start gap-2 sm:items-center">
                                    <AlertTriangle size={16} class="mt-0.5 shrink-0 text-amber-500 sm:mt-0" />
                                    <div class="min-w-0">
                                        <BrokerBadge broker={issue.broker} size={18} showName={true} />
                                        <p class="mt-0.5 text-xs text-gray-600 dark:text-gray-300">
                                            {$t('importWizard.brokerOpeningMsg', {values: {count: issue.count, openedAt: issue.openedAt, minDate: issue.minTxDate}})}
                                        </p>
                                    </div>
                                </div>
                                <div class="flex shrink-0 items-center gap-2">
                                    <button
                                        type="button"
                                        class="flex items-center gap-1 rounded bg-libre-green px-2 py-1 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
                                        onclick={() => void autoFixBrokerOpening(issue)}
                                        disabled={autoFixingBrokerId !== null || !issue.minTxDate}
                                        data-testid="broker-opening-autofix-{issue.brokerId}"
                                        title={$t('importWizard.autoFixOpeningTip')}
                                    >
                                        {#if autoFixingBrokerId === issue.brokerId}
                                            <Loader2 size={12} class="animate-spin" />
                                        {:else}
                                            <Wand2 size={12} />
                                        {/if}
                                        <span>{$t('importWizard.autoFixOpening', {values: {date: issue.minTxDate}})}</span>
                                    </button>
                                    <button
                                        type="button"
                                        class="flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 dark:border-slate-600 dark:hover:bg-slate-700"
                                        onclick={() => void openBrokerOpeningEditById(issue.brokerId)}
                                        data-testid="broker-opening-edit-{issue.brokerId}"
                                    >
                                        <Pencil size={12} /><span>{$t('importWizard.status.editBrokerDate')}</span>
                                    </button>
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}

                <!-- ── TX Table (DataTable) ───────────────────────────── -->
                <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                    <!-- Toolbar row -->
                    <div class="flex items-center justify-between px-4 py-2.5 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-200 dark:border-gray-700">
                        <div class="flex items-center gap-3 text-sm">
                            <span class="font-semibold">{$t('transactions.title')}</span>
                            <span class="text-gray-500">{step4SelectedCount} / {step4TotalCount}</span>
                            {#if step4SelectedDuplicateCount > 0}
                                <Tooltip text={$t('importWizard.duplicatesSelectedTip')} position="top" maxWidth="320px" wrapperClass="inline-flex">
                                    <span class="cursor-help text-xs text-amber-600 underline decoration-dotted dark:text-amber-400">⚠ {$t('importWizard.duplicatesSelected', {values: {n: step4SelectedDuplicateCount}})}</span>
                                </Tooltip>
                            {/if}
                            {#if step4BeforeOpeningCount > 0}
                                <span class="text-xs text-gray-500 dark:text-gray-400">⛔ {step4BeforeOpeningCount} {$t('importWizard.beforeOpeningCount')}</span>
                            {/if}
                        </div>
                        <div class="flex items-center gap-2">
                            {#if step4BeforeOpeningCount > 0}
                                <button
                                    type="button"
                                    class="text-xs text-libre-green hover:underline flex items-center gap-1 disabled:opacity-50"
                                    onclick={() => void recheckOpenings()}
                                    disabled={recheckingOpenings}
                                    data-testid="import-wizard-recheck-openings"
                                    title={$t('importWizard.recheckOpeningsTip')}
                                >
                                    <RefreshCw size={12} class={recheckingOpenings ? 'animate-spin' : ''} /><span class="hidden sm:inline">{$t('importWizard.recheckOpenings')}</span>
                                </button>
                                <span class="text-gray-300 dark:text-gray-600">|</span>
                            {/if}
                            <button type="button" class="text-xs text-libre-green hover:underline flex items-center gap-1" onclick={step4SelectAll} data-testid="import-wizard-select-all">
                                <CheckSquare size={12} /><span class="hidden sm:inline">{$t('common.selectAll')}</span>
                            </button>
                            <span class="text-gray-300 dark:text-gray-600">|</span>
                            <button type="button" class="text-xs text-libre-green hover:underline flex items-center gap-1" onclick={step4SelectVisible} data-testid="import-wizard-select-visible" title={$t('importWizard.selectVisibleTip')}>
                                <ListChecks size={12} /><span class="hidden sm:inline">{$t('importWizard.selectVisible')}</span>
                            </button>
                            <span class="text-gray-300 dark:text-gray-600">|</span>
                            <button type="button" class="text-xs text-gray-500 hover:underline flex items-center gap-1" onclick={step4DeselectAll} data-testid="import-wizard-deselect-all">
                                <Square size={12} /><span class="hidden sm:inline">{$t('common.deselectAll')}</span>
                            </button>
                            <span class="text-gray-300 dark:text-gray-600">|</span>
                            <ColumnVisibilityToggle tableRef={step4TableRef} />
                        </div>
                    </div>

                    {#if step4HasDeselectReasons}
                        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-200" data-testid="import-wizard-deselect-banner">
                            <span class="font-medium">{$t('importWizard.deselectReasons.title')}</span>
                            {#if step4BeforeOpeningCount > 0}
                                <span class="inline-flex items-center gap-1">⛔ {$t('importWizard.deselectReasons.beforeOpening', {values: {n: step4BeforeOpeningCount}})}</span>
                            {/if}
                            {#if step4DeselectPendingDup > 0}
                                <span class="inline-flex items-center gap-1">⧉ {$t('importWizard.deselectReasons.pendingDuplicate', {values: {n: step4DeselectPendingDup}})}</span>
                            {/if}
                            {#if step4DeselectDbDup > 0}
                                <span class="inline-flex items-center gap-1">⚠ {$t('importWizard.deselectReasons.dbDuplicate', {values: {n: step4DeselectDbDup}})}</span>
                            {/if}
                        </div>
                    {/if}

                    <DataTable
                        bind:this={step4TableRef}
                        data={step4Rows}
                        columns={step4Columns}
                        getRowId={(mt) => String(mt.index)}
                        storageKey="import-wizard-step4"
                        enableSelection={false}
                        enableActions={false}
                        enablePagination={true}
                        defaultPageSize={25}
                        pageSizeOptions={[10, 25, 50, 100, 0]}
                        enableSorting={true}
                        enableColumnFilters={true}
                        enableColumnResize={true}
                        enableColumnVisibility={true}
                        tableLayout="auto"
                        getRowClass={(mt) => `${!mt.selected ? 'opacity-50' : ''} ${mt.isDupKeeper ? 'bg-emerald-50/60 dark:bg-emerald-900/10' : ''}`.trim()}
                        emptyMessage={$t('importWizard.noFiles')}
                    />
                </div>
            </div>
        {/if}
    </div>

    <!-- ================================================================== -->
    <!-- Footer -->
    <!-- ================================================================== -->
    <div class="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
        {#if currentStepId === 'upload'}
            <div class="flex items-center gap-1">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={handleClose}>
                    {$t('common.cancel')}
                </button>
                {#if pendingFiles.length > 0 && step1HasUnassigned}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.brokerRequired')}
                    </span>
                {:else if pendingFiles.length > 0 && step1ValidCount > 0}
                    <span class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <CheckCircle size={14} />
                        {$t('importWizard.allConfigured')}
                    </span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                {#if pendingFiles.length > 0}
                    <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={clearAllPendingFiles} data-testid="import-wizard-clear">
                        {$t('common.clear') || 'Clear'}
                    </button>
                {/if}
                <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed" onclick={goNext} disabled={!step1CanProceed || uploading} data-testid="import-wizard-next">
                    {#if uploading}
                        <LoadingSpinner size="sm" />
                    {:else if step1ValidCount > 0}
                        {$t('importWizard.next')} ({step1ValidCount}) ▶
                    {:else}
                        {$t('importWizard.next')} ▶
                    {/if}
                </button>
            </div>
        {:else if currentStepId === 'select'}
            <div class="flex items-center gap-1">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack} data-testid="import-wizard-back">
                    ◀ {$t('common.back')}
                </button>
                {#if selectedFiles.length > 0 && !step2CanParse}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.pluginRequired')}
                    </span>
                {:else if step2CanParse}
                    <span class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <CheckCircle size={14} />
                        {$t('importWizard.allConfigured')}
                    </span>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed" onclick={goNext} disabled={!step2CanParse} data-testid="import-wizard-parse">
                {$t('importWizard.parse', {values: {n: selectedFiles.length}})} ▶
            </button>
        {:else if currentStepId === 'analyze'}
            <div class="flex items-center gap-1">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack} data-testid="import-wizard-back">
                    ◀ {$t('common.back')}
                </button>
                {#if parseParsing}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <LoadingSpinner size="sm" />
                        {$t('importWizard.parsingProgress', {values: {done: parseCompletedCount, total: parseTotalCount}})}
                    </span>
                {:else if parseDone && parseHasErrors && !parseHasSuccess}
                    <span class="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.parseCompleteWithErrors')}
                    </span>
                {:else if parseDone && parseHasErrors}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.parseCompleteWithErrors')}
                    </span>
                {:else if parseDone && parseHasSuccess}
                    <span class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <CheckCircle size={14} />
                        {$t('importWizard.parseComplete')}
                    </span>
                {:else if usingCachedResults}
                    <span class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <CheckCircle size={14} />
                        {$t('importWizard.cachedResults')}
                    </span>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed" onclick={goNext} disabled={!step3CanContinue} data-testid="import-wizard-continue">
                {$t('common.continue')} ▶
            </button>
            <!--
              The unification step had no footer branch of its own and fell through to the review
              one, which judges *transactions*: it announced "select at least one transaction" on a
              step that has none and disabled the only way forward.
            -->
        {:else if currentStepId === 'assets'}
            <div class="flex items-center gap-1">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack} data-testid="import-wizard-back">
                    ◀ {$t('common.back')}
                </button>
                {#if assetGroupOpenProposals > 0}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.assetUnify.openProposals', {values: {n: assetGroupOpenProposals}})}
                    </span>
                {:else}
                    <span class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <CheckCircle size={14} />
                        {$t('importWizard.assetUnify.allSettled', {values: {n: assetGroups.length}})}
                    </span>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={goNext} data-testid="import-wizard-assets-continue">
                {$t('common.continue')} ▶
            </button>
        {:else if currentStepId === 'fix'}
            <div class="flex items-center gap-1">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack} data-testid="import-wizard-back">
                    ◀ {$t('common.back')}
                </button>
                {#if fixStepPendingCount > 0}
                    <span class="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.fixStep.pending', {values: {n: fixStepPendingCount}})}
                    </span>
                {:else}
                    <span class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <CheckCircle size={14} />
                        {$t('importWizard.fixStep.allDone')}
                    </span>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed" onclick={goNext} disabled={fixStepPendingCount > 0 || duplicateRecheckRunning} data-testid="import-wizard-fix-continue">
                {#if duplicateRecheckRunning}
                    <LoadingSpinner size="sm" />
                {:else}
                    {$t('common.continue')} ▶
                {/if}
            </button>
        {:else if currentStepId === 'duplicates'}
            <div class="flex items-center gap-1">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack} data-testid="import-wizard-back">
                    ◀ {$t('common.back')}
                </button>
                {#if resolverPartialCount > 0}
                    <span class="flex items-center gap-1 text-xs text-orange-600 dark:text-orange-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.resolver.statusToVerify', {values: {n: resolverPartialCount}})}
                    </span>
                {:else}
                    <span class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <CheckCircle size={14} />
                        {$t('importWizard.resolver.statusAllAuto')}
                    </span>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={goNext} data-testid="import-wizard-duplicates-continue">
                {$t('common.continue')} ▶
            </button>
        {:else}
            <div class="flex items-center gap-1">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack} data-testid="import-wizard-back">
                    ◀ {$t('common.back')}
                </button>
                {#if step4HasUnresolvedSelected}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.importDisabledUnresolved') || 'Resolve all assets to import'}
                    </span>
                {:else if step4SelectedCount === 0}
                    <span class="flex items-center gap-1 text-xs text-gray-400">
                        {$t('importWizard.importDisabledEmpty') || 'Select at least one transaction'}
                    </span>
                {:else if step4SelectedDuplicateCount > 0}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={14} />
                        {$t('importWizard.duplicatesSelected', {values: {n: step4SelectedDuplicateCount}})}
                    </span>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed" onclick={handleImport} disabled={!step4CanImport} data-testid="import-wizard-import">
                {$t('importWizard.importToEditor', {values: {n: step4SelectedCount}})} ▶
            </button>
        {/if}
    </div>
</ModalBase>

<!-- Unsaved guard -->
<ConfirmModal open={confirmCloseOpen} title={$t('common.discardImport')} message={$t('common.discardChangesMessage')} confirmText={$t('common.discard')} warning zIndex={80} onConfirm={confirmDiscard} onCancel={() => (confirmCloseOpen = false)} />

<!-- Step 2: delete-report (broker import file) confirmation -->
<ConfirmModal
    open={showDeleteFileConfirm}
    title={$t('common.confirmDelete')}
    message={$t('uploads.deleteConfirm')}
    items={pendingDeleteFile ? [pendingDeleteFile.fileName] : undefined}
    itemsLabel={$t('uploads.filesToDelete')}
    confirmText={$t('common.delete')}
    danger
    zIndex={85}
    onConfirm={confirmDeleteFile}
    onCancel={cancelDeleteFile}
/>

<!-- Step 3 → 4: parser notice acknowledgement (custom modal with accordion).
     Shown for both `info` and `warning` notices: an `info` is a deliberate plugin
     decision the user should see before the data lands, not noise to skip. -->
<ModalBase open={showWarningConfirm} maxWidth="4xl" zIndex={85} onRequestClose={() => (showWarningConfirm = false)}>
    <!-- Header -->
    <div class="flex items-center gap-3 p-4 border-b border-gray-200 dark:border-gray-700">
        <div class="p-2 {step3HasWarningSeverity ? 'bg-amber-100 dark:bg-amber-900/30' : 'bg-sky-100 dark:bg-sky-900/30'} rounded-full shrink-0">
            {#if step3HasWarningSeverity}
                <AlertTriangle size={18} class="text-amber-600 dark:text-amber-400" />
            {:else}
                <Info size={18} class="text-sky-600 dark:text-sky-400" />
            {/if}
        </div>
        <div class="flex-1 min-w-0">
            <h2 class="text-base font-semibold text-gray-900 dark:text-white">{step3HasWarningSeverity ? $t('importWizard.warningConfirmTitle') : $t('importWizard.noticeConfirmTitle')}</h2>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {step3HasWarningSeverity ? $t('importWizard.warningConfirmMessage', {values: {n: step3Warnings.length}}) : $t('importWizard.noticeConfirmMessage', {values: {n: step3Warnings.length}})}
            </p>
        </div>
        <button type="button" class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 shrink-0" onclick={() => (showWarningConfirm = false)}>
            <X size={16} />
        </button>
    </div>
    <!-- Body: one block per severity, accordion by file inside -->
    <div class="p-4 space-y-4 max-h-[55vh] overflow-y-auto">
        {#each step3NoticeSections as section}
            <div class="space-y-2">
                {#if step3NoticeSections.length > 1}
                    <h3 class="flex items-center gap-1.5 text-xs font-semibold {section.severity === 'info' ? 'text-sky-700 dark:text-sky-300' : 'text-amber-700 dark:text-amber-300'}">
                        {#if section.severity === 'info'}
                            <Info size={13} class="shrink-0" />
                        {:else}
                            <AlertTriangle size={13} class="shrink-0" />
                        {/if}
                        {section.severity === 'info' ? $t('importWizard.noticeSectionInfo') : $t('importWizard.noticeSectionWarning')}
                    </h3>
                {/if}
                {#each section.files as group}
                    <details open class="border {section.severity === 'info' ? 'border-sky-200 dark:border-sky-800' : 'border-amber-200 dark:border-amber-800'} rounded-lg overflow-hidden">
                        <summary
                            class="flex items-center justify-between px-3 py-2 cursor-pointer {section.severity === 'info'
                                ? 'bg-sky-50 dark:bg-sky-900/20 hover:bg-sky-100 dark:hover:bg-sky-900/30'
                                : 'bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 dark:hover:bg-amber-900/30'} transition-colors list-none"
                        >
                            <!-- No file-preview button here: every notice below carries its own
                                 "open at row N" jump, which lands on the rows that matter. -->
                            <span class="text-xs font-medium {section.severity === 'info' ? 'text-sky-800 dark:text-sky-200' : 'text-amber-800 dark:text-amber-200'} truncate flex-1 mr-2">
                                {group.fileName} <span class="opacity-70">({group.warnings.length})</span>
                            </span>
                        </summary>
                        <div class="px-4 py-2 bg-white dark:bg-slate-800">
                            <BrimNoticeList notices={group.warnings} dense collapsibleEvidence onGotoRow={(lines) => openPreview(group.fileId, 85, lines)} />
                        </div>
                    </details>
                {/each}
            </div>
        {/each}
    </div>
    <!-- Footer -->
    <div class="flex justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
        <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors" onclick={() => (showWarningConfirm = false)}>
            {$t('common.cancel')}
        </button>
        <button type="button" class="px-4 py-2 text-sm rounded-lg {step3HasWarningSeverity ? 'bg-amber-500 hover:bg-amber-600' : 'bg-sky-500 hover:bg-sky-600'} text-white transition-colors" onclick={goNext} data-testid="import-wizard-warning-confirm">
            {$t('importWizard.warningConfirmOk')}
        </button>
    </div>
</ModalBase>

<!-- File preview modal -->
<FilePreviewModal
    open={showPreviewModal}
    preview={previewData}
    loading={previewLoading}
    error={previewError}
    onRequestClose={closePreviewModal}
    onSheetChange={(name) => {
        // The line numbers belong to the sheet they came from; on another sheet they point
        // at unrelated rows, which is worse than pointing at nothing.
        previewHighlightRows = [];
        loadPreview(name);
    }}
    highlightRows={previewHighlightRows}
    zIndex={previewZIndex}
/>

<!-- Parse detail modal (single file) -->
<ParseDetailModal open={showParseDetail} parseResult={parseDetailResult} zIndex={80} onClose={closeParseDetail} onPreview={parseDetailResult ? () => openPreview(parseDetailResult!.fileId, 80) : undefined} />

<!-- Parse detail modal (aggregate) -->
<ParseDetailModal
    open={showAggregateDetail}
    parseResult={null}
    allResults={parseResults}
    zIndex={80}
    onClose={() => {
        showAggregateDetail = false;
    }}
/>

<!-- Asset creation modal (Step 4 Zone C) -->
{#if createAssetForFakeId !== null && createPrimaryPending === null}
    {@const _createRes = assetResolutions.find((r) => r.fakeAssetId === createAssetForFakeId)}
    {@const _createIsin = createPrimaryIsin ?? _createRes?.groupIsins[0] ?? _createRes?.extractedIsin ?? null}
    {@const _createSymbol = createPrimarySymbol ?? _createRes?.groupSymbols[0] ?? _createRes?.extractedSymbol ?? null}
    {@const _createNames = createNamesFor(_createRes)}
    <!-- The name elected (or typed) on the unification step, or the raw extraction if nobody ruled. -->
    {@const _createName = _createRes?.groupNames[0] || _createRes?.extractedName || ''}
    {@const _createOther = createOtherFor(_createRes, _createIsin, _createSymbol)}
    {@const _createDesc = _createRes ? [$t('importWizard.createAsset.identifiedNames'), ..._createNames.map((n) => `• ${n}`), _createSymbol ? `Ticker: ${_createSymbol}` : '', _createIsin ? `ISIN: ${_createIsin}` : ''].filter((l) => l !== '').join('\n') : ''}
    <AssetModal
        open={true}
        editMode={false}
        prefillData={_createRes
            ? {
                  display_name: _createName,
                  identifier_ticker: _createSymbol ?? undefined,
                  identifier_isin: _createIsin ?? undefined,
                  identifier_other: _createOther.length > 0 ? _createOther : undefined,
                  classification_params: _createDesc ? {short_description: _createDesc} : undefined,
              }
            : null}
        initialSearchBadges={_createRes ? [...(_createSymbol ? [{label: `Ticker: ${_createSymbol}`, value: _createSymbol}] : []), ...(_createIsin ? [{label: `ISIN: ${_createIsin}`, value: _createIsin}] : []), ...(_createName ? [{label: _createName, value: _createName}] : [])] : []}
        searchHints={_createRes ? [...(_createIsin ? [_createIsin] : []), ...(_createSymbol ? [_createSymbol] : []), ..._createNames] : []}
        initialSearchQuery=""
        zIndex={90}
        initialNoProvider={true}
        importNotices={_createRes ? _createRes.notices : []}
        onReuseExisting={reuseExistingForCreate}
        oncreated={(assetId) => {
            const fakeId = createAssetForFakeId!;
            const res = assetResolutions.find((r) => r.fakeAssetId === fakeId);
            resolveAsset(fakeId, assetId);
            createAssetForFakeId = null;
            if (res) {
                // The asset was just created, so cancelling the prompt must not unbind it.
                void checkAndPromptIdentifier(fakeId, assetId, res, {clearOnCancel: false});
            }
        }}
        onclose={() => (createAssetForFakeId = null)}
    />
{/if}

<!--
  Which code leads, asked before the creation form opens.

  A unified group can bring two ISINs for one bond; the form has a single primary field, so the
  choice has to be made somewhere. Making it here means the form arrives already correct instead
  of being corrected afterwards.
-->
{#if createAssetForFakeId !== null && createPrimaryPending !== null}
    {@const _primaryRes = assetResolutions.find((r) => r.fakeAssetId === createAssetForFakeId)}
    <ModalBase open={true} maxWidth="lg" onRequestClose={() => (createAssetForFakeId = null)} zIndex={zIndex + 30}>
        <div class="p-6">
            <IdentifierPrimaryChooser
                choices={(createPrimaryPending === 'identifier_isin' ? (_primaryRes?.groupIsins ?? []) : (_primaryRes?.groupSymbols ?? [])).map((v) => ({value: v, origin: 'report' as const}))}
                assetName={_primaryRes?.extractedName ?? ''}
                typeLabel={createPrimaryPending === 'identifier_ticker' ? 'Ticker' : 'ISIN'}
                isIsin={createPrimaryPending === 'identifier_isin'}
                bind:primary={identifierPromptPrimary}
                testid="create-primary-chooser"
            />
            <div class="mt-5 flex justify-end gap-2">
                <button type="button" class="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700" onclick={() => (createAssetForFakeId = null)} data-testid="create-primary-cancel">
                    {$t('assets.identifiers.primaryChooser.cancel')}
                </button>
                <button type="button" class="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700" onclick={confirmCreatePrimary} data-testid="create-primary-confirm">
                    {$t('assets.identifiers.primaryChooser.confirm')}
                </button>
            </div>
        </div>
    </ModalBase>
{/if}

<!-- Duplicate assets, merged from the resolution card where the two are visible side by side -->
{#if mergeSourceAsset !== null}
    <AssetMergeModal open={true} sourceAsset={mergeSourceAsset} zIndex={zIndex + 30} onmerged={(targetId) => void onCardMerged(targetId)} onclose={() => ((mergeSourceAsset = null), (mergeForFakeAssetId = null))} />
{/if}

<!-- Asset inspection from the resolution step — the picked instrument, in full -->
{#if inspectAssetData !== null}
    <AssetModal
        open={true}
        editMode={true}
        editData={inspectAssetData as never}
        zIndex={90}
        onupdated={() => {
            inspectAssetData = null;
            void refreshAllAssets();
        }}
        onclose={() => (inspectAssetData = null)}
    />
{/if}

<!-- Asset creation from the correction step — seeded with the row's own description -->
{#if fixCreateAssetIndex !== null}
    {@const _fixDesc = fixRowDescription(fixCreateAssetIndex)}
    {@const _fixHints = fixCreateHints(fixCreateAssetIndex)}
    {@const _fixIsin = _fixDesc.match(ISIN_RE)?.[1]}
    <AssetModal
        open={true}
        editMode={false}
        prefillData={{
            display_name: fixCreateAssetQuery,
            identifier_isin: _fixIsin ?? undefined,
            classification_params: _fixDesc ? {short_description: _fixDesc} : undefined,
        }}
        initialSearchBadges={_fixHints.slice(0, 8).map((h) => ({label: h, value: h}))}
        searchHints={_fixHints}
        initialSearchQuery={fixCreateAssetQuery}
        zIndex={zIndex + 30}
        initialNoProvider={true}
        onReuseExisting={(existingAssetId) => {
            fixCreatedAssets = {...fixCreatedAssets, [fixCreateAssetIndex!]: existingAssetId};
            fixCreateAssetIndex = null;
        }}
        reuseAllowKeyMerge={false}
        oncreated={(assetId) => {
            fixCreatedAssets = {...fixCreatedAssets, [fixCreateAssetIndex!]: assetId};
            fixCreateAssetIndex = null;
            void refreshAllAssets();
        }}
        onclose={() => (fixCreateAssetIndex = null)}
    />
{/if}

<!-- N-way duplicate compare modal — side-by-side field×transaction grid -->
<TransactionCompareModal
    open={nwCompareOpen}
    title={nwCompareTitle}
    hint={nwCompareHint}
    fields={nwCompareFields}
    columns={nwCompareColumns}
    defaultKept={nwCompareDefaultKept}
    resetKept={nwCompareResetKept}
    onKeep={nwCompareOnKeep
        ? (choice) => {
              nwCompareOnKeep?.(choice);
              nwCompareOpen = false;
          }
        : undefined}
    zIndex={zIndex + 25}
    onClose={() => (nwCompareOpen = false)}
/>

<!--
  Identifier prompt. Two shapes: a plain confirmation when the asset holds no code of that type,
  the primary chooser when it already holds a different one — because the answer to two ISINs for
  one bond is never to throw one away.
-->
<ModalBase open={identifierPromptOpen} maxWidth="lg" onRequestClose={cancelAddIdentifier} zIndex={zIndex + 30}>
    <div class="p-6">
        {#if identifierPromptIsConflict}
            <IdentifierPrimaryChooser
                choices={[...(identifierPromptExistingValue ? [{value: identifierPromptExistingValue, origin: 'stored' as const}] : []), ...identifierPromptValues.map((v) => ({value: v, origin: 'report' as const}))]}
                assetName={identifierPromptAssetName ?? ''}
                typeLabel={identifierPromptField === 'identifier_ticker' ? 'Ticker' : 'ISIN'}
                isIsin={identifierPromptField === 'identifier_isin'}
                bind:primary={identifierPromptPrimary}
                testid="identifier-prompt-chooser"
            />
        {:else}
            <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100 mb-3">
                {$t('importWizard.addIdentifier.title')}
            </h2>
            <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed" data-testid="identifier-prompt-body">
                {@html $t('importWizard.addIdentifier.body', {
                    values: {
                        asset: `<strong>${identifierPromptAssetName ?? ''}</strong>`,
                        value: `<strong>${identifierPromptValues[0] ?? ''}</strong>`,
                        type: identifierPromptField === 'identifier_ticker' ? 'Ticker' : 'ISIN',
                    },
                })}
            </p>
        {/if}

        {#if identifierPromptExtraOther.length > 0}
            <p class="mt-3 text-xs text-gray-500 dark:text-gray-400" data-testid="identifier-prompt-extra-keys">
                {$t('importWizard.addIdentifier.alsoKeys', {values: {keys: identifierPromptExtraOther.join(', ')}})}
            </p>
        {/if}

        <div class="flex justify-end gap-2 flex-nowrap mt-5">
            <button type="button" class="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors whitespace-nowrap" onclick={cancelAddIdentifier} data-testid="identifier-prompt-cancel">
                {identifierPromptLabels.cancel}
            </button>
            <button type="button" class="px-3 py-1.5 text-sm rounded-lg border border-libre-green/40 text-libre-green hover:bg-libre-green/10 transition-colors whitespace-nowrap" onclick={skipAddIdentifier} data-testid="identifier-prompt-skip">
                {identifierPromptLabels.skip}
            </button>
            <button type="button" disabled={identifierPromptSaving} class="px-3 py-1.5 text-sm rounded-lg bg-libre-green hover:bg-libre-green/90 text-white disabled:opacity-50 transition-colors whitespace-nowrap" onclick={confirmAddIdentifier} data-testid="identifier-prompt-confirm">
                {identifierPromptSaving ? '…' : identifierPromptLabels.confirm}
            </button>
        </div>
    </div>
</ModalBase>

<BrokerModal
    isOpen={createBrokerOpen}
    mode="create"
    zIndex={zIndex + 10}
    oncreated={(d) => {
        if (createBrokerContext === 'global') {
            onGlobalBrokerChange(d.id);
        } else if (createBrokerContext) {
            pendingFiles = pendingFiles.map((f) => (f.id === createBrokerContext ? {...f, brokerId: d.id} : f));
        }
        // Force full refetch so user_role is included (mergeBrokers alone lacks role data).
        refreshAllBrokers().then(() => {
            brokers = getEditableBrokers();
        });
        createBrokerOpen = false;
        createBrokerContext = null;
    }}
    onclose={() => {
        createBrokerOpen = false;
        createBrokerContext = null;
    }}
/>

<BrokerModal
    isOpen={editBrokerOpen}
    mode="edit"
    brokerId={editBrokerId}
    initialData={editBrokerInitialData}
    zIndex={zIndex + 20}
    onupdated={() => {
        void recheckOpenings();
    }}
    onclose={() => {
        editBrokerOpen = false;
        editBrokerId = null;
        editBrokerInitialData = {};
    }}
/>
