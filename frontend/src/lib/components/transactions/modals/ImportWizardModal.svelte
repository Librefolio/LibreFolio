<!--
  ImportWizardModal.svelte — Phase 07 Part 5 v5 M3

  Wide 4-step wizard for importing broker report files into BulkModal.
  Step 1: Upload files (broker-independent) & assign broker per-file
  Step 2: Select existing broker files to parse (DataTable per broker, per-file plugin)
  Step 3: Parse engine — sequential parse with progress, results DataTable, detail modal
  Step 4: Review & Import — asset resolution + TX selection + handoff to BulkModal
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Upload, Trash2, Eye, ChevronDown, ChevronRight, Check, AlertTriangle, Plus, CheckCircle, FileText, RefreshCw, Search, X} from 'lucide-svelte';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {extractErrorMessage, trySave} from '$lib/utils/trySave';
    import {formatBytes} from '$lib/utils/files/upload';
    import {ensureBrokersLoaded, getEditableBrokers, type BrokerInfo} from '$lib/stores/reference/brokerStore';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {ensureAssetsLoaded, getAllAssets, type AssetInfo} from '$lib/stores/reference/assetStore';
    import {isFakeAssetId} from '$lib/utils/brim/isFakeAssetId';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';

    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import {BrokerSearchSelect} from '$lib/components/ui/select';
    import ImportPluginSelect, {getCachedPlugins} from '$lib/components/ui/select/ImportPluginSelect.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import FilePreviewModal from '$lib/components/files/FilePreviewModal.svelte';
    import ParseDetailModal from '$lib/components/transactions/modals/ParseDetailModal.svelte';
    import {fetchFilePreview, getFilePreviewError} from '$lib/utils/files/filePreview';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';

    import type {TransactionCreateItem, BrimFile, BrimParseResponse, FilePreviewResponse} from '$lib/types';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open: boolean;
        zIndex?: number;
        onClose: () => void;
        onImportBatch: (creates: TransactionCreateItem[]) => void;
    }

    let {open, zIndex = 70, onClose, onImportBatch}: Props = $props();

    // =========================================================================
    // Constants
    // =========================================================================

    const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];
    const STEPS = ['step1Title', 'step2Title', 'step3Title', 'step4Title'] as const;

    // =========================================================================
    // Stepper State
    // =========================================================================

    let currentStep = $state(1);
    let maxReachedStep = $state(1);

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
            if (dropZoneContainerRef && !dropZoneContainerRef.contains(e.target as Node)) {
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
    let parseParsing = $derived(parseResults.some((r) => r.status === 'parsing'));
    let step3CanContinue = $derived(parseDone && parseHasSuccess);
    let usingCachedResults = $state(false);

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

    interface ImportTodo {
        field: string;
        severity: 'blocker' | 'warning';
        reasonCode: string;
        message: string;
    }

    interface MergedTx {
        index: number;
        sourceFileId: string;
        tx: TransactionCreateItem;
        selected: boolean;
        duplicateStatus: 'unique' | 'possible' | 'likely';
        todos: ImportTodo[];
    }

    interface AssetResolution {
        fakeAssetId: number;
        extractedSymbol: string | null;
        extractedIsin: string | null;
        extractedName: string | null;
        candidates: Array<{asset_id: number; symbol?: string | null; isin?: string | null; name: string; match_confidence: string}>;
        resolvedAssetId: number | null;
        txCount: number;
        sourceFiles: string[];
    }

    let mergedTransactions = $state<MergedTx[]>([]);
    let assetResolutions = $state<AssetResolution[]>([]);
    let step4AssetQueries = $state<Record<number, string>>({});
    let allUserAssets = $state<AssetInfo[]>([]);
    let allUserAssetsLoaded = $state(false);
    let createAssetForFakeId = $state<number | null>(null);
    let step4ShowResolveSection = $state(true);

    // Step 4 deriveds
    let step4SelectedCount = $derived(mergedTransactions.filter((t) => t.selected).length);
    let step4TotalCount = $derived(mergedTransactions.length);
    let step4UnresolvedCount = $derived(assetResolutions.filter((r) => r.resolvedAssetId === null).length);
    let step4HasUnresolvedSelected = $derived(
        mergedTransactions.some((t) => {
            if (t.selected && typeof t.tx.asset_id === 'number' && isFakeAssetId(t.tx.asset_id)) {
                const res = assetResolutions.find((r) => r.fakeAssetId === t.tx.asset_id);
                return res?.resolvedAssetId == null;
            }
            return false;
        })
    );
    let step4CanImport = $derived(step4SelectedCount > 0 && !step4HasUnresolvedSelected);
    let step4LikelyDupCount = $derived(mergedTransactions.filter((t) => t.selected && t.duplicateStatus === 'likely').length);

    function mergeAllTransactions() {
        const txArr: MergedTx[] = [];
        const assetMap = new Map<number, AssetResolution>();
        let globalIndex = 0;

        for (const result of parseResults.filter((r) => r.status === 'done' && r.response)) {
            const resp = result.response!;
            // Build todos map by tx_index
            const todosMap = new Map<number, ImportTodo[]>();
            for (const ft of resp.field_todos ?? []) {
                const idx = (ft as any).tx_index as number;
                const list = todosMap.get(idx) ?? [];
                list.push({field: (ft as any).field, severity: (ft as any).severity, reasonCode: (ft as any).reason_code, message: (ft as any).message});
                todosMap.set(idx, list);
            }

            // Build duplicate sets (by tx_row_index)
            const dups = resp.duplicates;
            const likelySet = new Set<number>((dups && !Array.isArray(dups) ? (dups.tx_likely_duplicates ?? []) : []).map((d: any) => d.tx_row_index as number));
            const possibleSet = new Set<number>((dups && !Array.isArray(dups) ? (dups.tx_possible_duplicates ?? []) : []).map((d: any) => d.tx_row_index as number));

            for (const [txIdx, tx] of (resp.transactions ?? []).entries()) {
                let dupStatus: 'unique' | 'possible' | 'likely' = 'unique';
                if (likelySet.has(txIdx)) dupStatus = 'likely';
                else if (possibleSet.has(txIdx)) dupStatus = 'possible';

                txArr.push({
                    index: globalIndex++,
                    sourceFileId: result.fileId,
                    tx: tx as TransactionCreateItem,
                    selected: dupStatus !== 'likely',
                    duplicateStatus: dupStatus,
                    todos: todosMap.get(txIdx) ?? [],
                });

                const assetId = typeof tx.asset_id === 'number' ? tx.asset_id : null;
                if (assetId !== null && isFakeAssetId(assetId) && !assetMap.has(assetId)) {
                    const mapping = (resp.asset_mappings ?? []).find((m: any) => m.fake_asset_id === assetId);
                    if (mapping) {
                        assetMap.set(assetId, {
                            fakeAssetId: assetId,
                            extractedSymbol: (mapping.extracted_symbol as string | null) ?? null,
                            extractedIsin: (mapping.extracted_isin as string | null) ?? null,
                            extractedName: (mapping.extracted_name as string | null) ?? null,
                            candidates: ((mapping.candidates ?? []) as AssetResolution['candidates']),
                            resolvedAssetId: typeof mapping.selected_asset_id === 'number' ? (mapping.selected_asset_id as number) : null,
                            txCount: 0,
                            sourceFiles: [],
                        });
                    }
                }
            }
        }

        // Compute txCount and sourceFiles per asset resolution
        for (const [fakeId, res] of assetMap) {
            const relTx = txArr.filter((t) => t.tx.asset_id === fakeId);
            res.txCount = relTx.length;
            res.sourceFiles = [...new Set(relTx.map((t) => parseResults.find((r) => r.fileId === t.sourceFileId)?.fileName ?? t.sourceFileId))];
        }

        mergedTransactions = txArr;
        assetResolutions = [...assetMap.values()];
        step4AssetQueries = {};
        step4ShowResolveSection = assetMap.size > 0;
    }

    async function loadUserAssets() {
        if (allUserAssetsLoaded) return;
        await ensureAssetsLoaded();
        allUserAssets = getAllAssets();
        allUserAssetsLoaded = true;
    }

    function resolveAsset(fakeAssetId: number, realAssetId: number) {
        assetResolutions = assetResolutions.map((r) => (r.fakeAssetId === fakeAssetId ? {...r, resolvedAssetId: realAssetId} : r));
    }

    function clearResolution(fakeAssetId: number) {
        assetResolutions = assetResolutions.map((r) => (r.fakeAssetId === fakeAssetId ? {...r, resolvedAssetId: null} : r));
    }

    function getFilteredAssets(fakeAssetId: number): AssetInfo[] {
        const q = (step4AssetQueries[fakeAssetId] ?? '').toLowerCase().trim();
        if (!q) return [];
        return allUserAssets.filter((a) => {
            const name = a.display_name?.toLowerCase() ?? '';
            const ticker = a.identifier_ticker?.toLowerCase() ?? '';
            const isin = a.identifier_isin ?? '';
            return name.includes(q) || ticker.includes(q) || isin.toLowerCase().includes(q);
        }).slice(0, 8);
    }

    function buildFinalTxList(): TransactionCreateItem[] {
        return mergedTransactions
            .filter((t) => t.selected)
            .map((t) => {
                const tx = {...t.tx} as any;
                const assetId = typeof tx.asset_id === 'number' ? tx.asset_id : null;
                if (assetId !== null && isFakeAssetId(assetId)) {
                    const res = assetResolutions.find((r) => r.fakeAssetId === assetId);
                    if (res?.resolvedAssetId) tx.asset_id = res.resolvedAssetId;
                }
                return tx as TransactionCreateItem;
            });
    }

    function handleImport() {
        const creates = buildFinalTxList();
        onImportBatch(creates);
    }

    function getAssetDisplayName(assetId: number | null | undefined): string {
        if (assetId == null) return '—';
        if (isFakeAssetId(assetId)) {
            const res = assetResolutions.find((r) => r.fakeAssetId === assetId);
            if (!res) return `#${assetId}`;
            return res.extractedSymbol ?? res.extractedName ?? `#${assetId}`;
        }
        const asset = allUserAssets.find((a) => a.id === assetId);
        return asset?.display_name ?? `#${assetId}`;
    }

    function confidenceBadgeClass(conf: string): string {
        if (conf === 'exact') return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300';
        if (conf === 'high') return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
        if (conf === 'medium') return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
        return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
    }

    // =========================================================================
    // Shared State
    // =========================================================================

    let brokers = $state<BrokerInfo[]>([]);
    let brokersLoading = $state(false);
    let confirmCloseOpen = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    let hasUnsavedWork = $derived(pendingFiles.length > 0 || selectedFiles.length > 0 || parseResults.length > 0 || mergedTransactions.length > 0);
    let selectedBrokerCount = $derived(new Set(selectedFiles.map((f) => f.brokerId)).size);

    // =========================================================================
    // Lifecycle
    // =========================================================================

    $effect(() => {
        if (open) {
            loadBrokers();
        } else {
            resetState();
        }
    });

    function resetState() {
        currentStep = 1;
        maxReachedStep = 1;
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
        step4AssetQueries = {};
        step4ShowResolveSection = true;
        createAssetForFakeId = null;
    }

    // =========================================================================
    // Broker Loading
    // =========================================================================

    async function loadBrokers() {
        brokersLoading = true;
        await ensureBrokersLoaded();
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
    // Navigation
    // =========================================================================

    function goToStep(target: number) {
        if (target >= currentStep) return;
        if (target <= 2) {
            selectedFiles = target === 1 ? [] : selectedFiles;
        }
        if (target <= 3) {
            mergedTransactions = [];
            assetResolutions = [];
        }
        currentStep = target;
    }

    function goNext() {
        if (currentStep === 1) {
            uploadAllPendingFiles().then(() => {
                currentStep = 2;
                if (maxReachedStep < 2) maxReachedStep = 2;
                loadBrokerFiles();
            });
        } else if (currentStep === 2) {
            currentStep = 3;
            if (maxReachedStep < 3) maxReachedStep = 3;
            // Init parse results and auto-start parsing
            initParseResults();
            if (!usingCachedResults) doParseAll();
        } else if (currentStep === 3) {
            currentStep = 4;
            if (maxReachedStep < 4) maxReachedStep = 4;
            mergeAllTransactions();
            loadUserAssets();
        }
    }

    function goBack() {
        if (currentStep === 3 && parseParsing) {
            abortParsing = true;
        }
        if (currentStep > 1) {
            currentStep = currentStep - 1;
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
                        id: crypto.randomUUID(),
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
                        id: crypto.randomUUID(),
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

    async function uploadAllPendingFiles() {
        const toUpload = pendingFiles.filter((f) => f.status === 'pending' && f.brokerId !== null);
        if (toUpload.length === 0) return;

        uploading = true;
        uploadError = null;

        for (const entry of toUpload) {
            pendingFiles = pendingFiles.map((f) => (f.id === entry.id ? {...f, status: 'uploading'} : f));

            const formData = new FormData();
            formData.append('file', entry.file);
            const result = await trySave(() => axiosInstance.post(`/api/v1/brokers/import/upload?broker_id=${entry.brokerId}`, formData), {toast: false, fallback: 'Upload failed', prefix: entry.fileName});

            if (result.status === 'error') {
                pendingFiles = pendingFiles.map((f) => (f.id === entry.id ? {...f, status: 'error', errorMessage: result.message} : f));
            } else {
                const serverFileId = result.data?.data?.file_id ?? crypto.randomUUID();
                pendingFiles = pendingFiles.map((f) => (f.id === entry.id ? {...f, status: 'uploaded', serverFileId} : f));
            }
        }

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
            header: () => $t('importWizard.assignBroker'),
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
                              placeholder: $t('importWizard.assignBroker'),
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
            label: () => $t('importWizard.remove'),
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

            // T7: programmatically select rows in DataTable after render
            requestAnimationFrame(() => {
                for (const [brokerId, brokerFiles] of brokerFilesMap) {
                    const brokerIdx = brokers.findIndex((b) => b.id === brokerId);
                    const tableRef = brokerIdx >= 0 ? tableRefs[brokerIdx] : undefined;
                    if (!tableRef) continue;
                    for (const bf of brokerFiles) {
                        if (step1FileIds.has(bf.file_id)) {
                            tableRef.toggleRowSelectionById(bf.file_id);
                        }
                    }
                }
            });
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
            minWidth: 100,
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
                    },
                } as const;
            },
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 200,
            minWidth: 140,
        },
        {
            id: 'uploaded_at',
            header: () => $t('common.date'),
            cell: (row) => ({type: 'date', value: row.uploaded_at, format: 'date'}) as const,
            type: 'date',
            sortable: true,
            filterable: false,
            width: 110,
            minWidth: 80,
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
            minWidth: 70,
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
        lastParseHash = newHash;
    }

    async function doParseAll() {
        abortParsing = false;
        for (const file of parseResults) {
            if (abortParsing) break;
            if (file.status !== 'pending') continue;

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
        }
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
            width: 200,
            minWidth: 120,
            getValue: (row) => row.fileName,
        },
        {
            id: 'brokerName',
            header: () => 'Broker',
            cell: (row) => {
                const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
                const faviconUrl = row.brokerPortalUrl ? (() => { try { return new URL(row.brokerPortalUrl!).origin + '/favicon.ico'; } catch { return null; } })() : null;
                const imgSrc = row.brokerIconUrl || faviconUrl;
                const icon = imgSrc
                    ? `<img src="${esc(imgSrc)}" class="w-5 h-5 rounded-full object-cover shrink-0" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">${`<span class="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-500 shrink-0" style="display:none">${esc(row.brokerName.charAt(0).toUpperCase())}</span>`}`
                    : `<span class="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-500 shrink-0">${esc(row.brokerName.charAt(0).toUpperCase())}</span>`;
                return {type: 'html', html: `<div class="flex items-center gap-1.5 min-w-0">${icon}<span class="truncate text-xs">${esc(row.brokerName)}</span></div>`} as const;
            },
            type: 'text',
            sortable: true,
            width: 130,
            minWidth: 90,
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
            minWidth: 90,
            getValue: (row) => row.pluginName,
        },
        {
            id: 'status',
            header: () => 'Status',
            cell: (row) => {
                if (row.status === 'parsing') {
                    return {type: 'badge', text: $t('importWizard.fileParsing'), variant: 'info'} as const;
                }
                const variantMap: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
                    pending: 'default',
                    done: 'success',
                    error: 'error',
                };
                const labelMap: Record<string, string> = {
                    pending: $t('importWizard.filePending'),
                    done: $t('importWizard.fileDone'),
                    error: $t('importWizard.fileError'),
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
            minWidth: 80,
        },
        {
            id: 'txCount',
            header: () => '📊',
            headerTooltip: () => $t('importWizard.colTip.txCount'),
            cell: (row) => (row.response?.transactions?.length != null ? row.response.transactions.length : '—'),
            type: 'number',
            width: 50,
            minWidth: 40,
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
            width: 50,
            minWidth: 40,
        },
        {
            id: 'unresolvedCount',
            header: () => '❓',
            headerTooltip: () => $t('importWizard.colTip.unresolvedCount'),
            cell: (row) => {
                if (!row.response?.asset_mappings?.length) return '—';
                const unresolved = row.response.asset_mappings.filter((m) => m.selected_asset_id == null).length;
                if (unresolved === 0) return 0;
                return {type: 'html', html: `<span class="text-amber-600 dark:text-amber-400 font-medium">${unresolved}</span>`} as const;
            },
            type: 'number',
            width: 50,
            minWidth: 40,
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
            width: 50,
            minWidth: 40,
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
            width: 50,
            minWidth: 40,
        },
        {
            id: 'warningCount',
            header: () => '⚠️',
            headerTooltip: () => $t('importWizard.colTip.warningCount'),
            cell: (row) => (row.response?.warnings?.length != null ? row.response.warnings.length : '—'),
            type: 'number',
            width: 50,
            minWidth: 40,
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
            label: () => $t('importWizard.reparse'),
            icon: RefreshCw,
            visible: (row) => row.status === 'done' || row.status === 'error',
            onClick: (row) => reparseSingleFile(row),
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

    async function openPreview(fileId: string) {
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

    function closePreviewModal() {
        previewRequestToken += 1;
        showPreviewModal = false;
        previewLoading = false;
        previewError = null;
        previewData = null;
        previewFileId = null;
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
        {#each STEPS as stepKey, i}
            {@const stepNum = i + 1}
            {@const isCompleted = stepNum < currentStep}
            {@const isCurrent = stepNum === currentStep}
            {@const isFuture = stepNum > currentStep}
            {@const isClickable = stepNum < currentStep}

            {#if i > 0}
                <div class="w-8 sm:w-12 h-0.5 mx-1 {isCompleted || isCurrent ? 'bg-libre-green' : 'bg-gray-200 dark:bg-gray-700'}"></div>
            {/if}

            <button
                type="button"
                class="flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors
                    {isClickable ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700' : 'cursor-default'}
                    {isCurrent ? 'font-semibold' : ''}"
                onclick={() => isClickable && goToStep(stepNum)}
                disabled={isFuture}
                data-testid="import-wizard-step-{stepNum}"
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
                    {$t(`importWizard.${stepKey}`)}
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
        {#if currentStep === 1}
            <div class="space-y-4" data-testid="import-wizard-step1">
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
                            <div class="flex-1 max-w-xs">
                                <BrokerSearchSelect {brokers} value={globalBrokerId} onchange={onGlobalBrokerChange} placeholder={$t('importWizard.assignBroker')} />
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
                                        label: () => $t('importWizard.remove'),
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
                            actionsColumnWidth="50px"
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
        {:else if currentStep === 2}
            <div class="space-y-4" data-testid="import-wizard-step2">
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
                                    <BrokerIcon iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size="sm" />
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
                                            onSelectionChange={(ids) => handleSelectionChange(broker.id, ids)}
                                            onRowDoubleClick={(row) => openPreview(row.file_id)}
                                            enableActions={true}
                                            actionsColumnWidth="60px"
                                            rowActions={[{id: 'preview', icon: Eye, label: $t('importWizard.preview'), onClick: (row) => openPreview(row.file_id)}]}
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
        {:else if currentStep === 3}
            <div class="flex flex-col gap-4 p-4" data-testid="import-wizard-step3">
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

                <!-- Results DataTable -->
                <DataTable
                    data={parseResults}
                    columns={step3Columns}
                    getRowId={(row) => row.fileId}
                    storageKey="import-wizard-parse-results"
                    enableSelection={false}
                    enableActions={true}
                    actionsColumnWidth="60px"
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
                            >{stats.totalTodos}</div>
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
                                onclick={() => { showAggregateDetail = true; }}
                            >
                                <Eye size={16} />
                                <span class="text-xs font-medium">{$t('importWizard.viewAll')}</span>
                            </button>
                            <button
                                type="button"
                                class="flex flex-col items-center justify-center gap-1 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors px-2 py-1.5"
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
            <!-- Step 4: Review & Import -->
            <!-- ============================================================ -->
        {:else if currentStep === 4}
            <div class="flex flex-col gap-4 h-full overflow-y-auto" data-testid="import-wizard-step4">

                <!-- ── Resolve Assets section ─────────────────────────── -->
                {#if assetResolutions.length > 0}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                        <!-- Section header -->
                        <button
                            type="button"
                            class="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-slate-800/50 hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors"
                            onclick={() => (step4ShowResolveSection = !step4ShowResolveSection)}
                        >
                            <div class="flex items-center gap-2">
                                {#if step4ShowResolveSection}<ChevronDown size={16} />{:else}<ChevronRight size={16} />{/if}
                                <span class="font-semibold text-sm">{$t('importWizard.resolveAssets')}</span>
                                {#if step4UnresolvedCount > 0}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                                        {step4UnresolvedCount} {$t('importWizard.unresolvedCount', {values: {n: step4UnresolvedCount}})}
                                    </span>
                                {:else}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                                        <Check size={12} class="mr-1" />{$t('importWizard.allResolved')}
                                    </span>
                                {/if}
                            </div>
                        </button>

                        {#if step4ShowResolveSection}
                            <div class="divide-y divide-gray-100 dark:divide-gray-800">
                                {#each assetResolutions as res (res.fakeAssetId)}
                                    {@const isResolved = res.resolvedAssetId !== null}
                                    {@const resolvedAsset = isResolved ? allUserAssets.find((a) => a.id === res.resolvedAssetId) : null}
                                    <div class="p-4 {isResolved ? 'bg-emerald-50/30 dark:bg-emerald-900/10' : ''}">
                                        <!-- Card header -->
                                        <div class="flex items-start justify-between gap-3 mb-3">
                                            <div>
                                                <div class="flex items-center gap-2">
                                                    <span class="font-mono font-bold text-sm text-gray-900 dark:text-gray-100">
                                                        {res.extractedSymbol ?? res.extractedIsin ?? '?'}
                                                    </span>
                                                    {#if res.extractedName && res.extractedName !== res.extractedSymbol}
                                                        <span class="text-xs text-gray-500 dark:text-gray-400">{res.extractedName}</span>
                                                    {/if}
                                                    {#if res.extractedIsin}
                                                        <span class="font-mono text-xs text-gray-400">{res.extractedIsin}</span>
                                                    {/if}
                                                </div>
                                                <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                                    {res.txCount} TX · {res.sourceFiles.join(', ')}
                                                </div>
                                            </div>
                                            {#if isResolved}
                                                <div class="flex items-center gap-2">
                                                    <span class="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                                                        <Check size={12} class="inline mr-1" />{resolvedAsset?.display_name ?? `#${res.resolvedAssetId}`}
                                                    </span>
                                                    <button type="button" class="text-gray-400 hover:text-red-500 transition-colors" onclick={() => clearResolution(res.fakeAssetId)} title="Clear selection">
                                                        <X size={14} />
                                                    </button>
                                                </div>
                                            {/if}
                                        </div>

                                        {#if !isResolved}
                                            <!-- Zone A: Candidates (radio buttons) -->
                                            {#if res.candidates.length > 0}
                                                <div class="mb-3 space-y-1">
                                                    <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{$t('importWizard.suggested')}</div>
                                                    {#each res.candidates as cand (cand.asset_id)}
                                                        <label class="flex items-center gap-2 p-2 rounded-md cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors">
                                                            <input
                                                                type="radio"
                                                                name="asset-{res.fakeAssetId}"
                                                                class="text-libre-green"
                                                                checked={res.resolvedAssetId === cand.asset_id}
                                                                onchange={() => resolveAsset(res.fakeAssetId, cand.asset_id)}
                                                            />
                                                            <span class="text-sm text-gray-800 dark:text-gray-200 flex-1">{cand.name}</span>
                                                            {#if cand.symbol}<span class="font-mono text-xs text-gray-500">{cand.symbol}</span>{/if}
                                                            <span class="text-xs px-1.5 py-0.5 rounded font-medium {confidenceBadgeClass(cand.match_confidence)}">
                                                                {$t(`importWizard.confidence.${cand.match_confidence}`) || cand.match_confidence}
                                                            </span>
                                                        </label>
                                                    {/each}
                                                </div>
                                                <div class="border-t border-gray-100 dark:border-gray-700 my-2"></div>
                                            {/if}

                                            <!-- Zone B: Search all user assets (client-side) -->
                                            <div class="mb-2">
                                                <div class="relative">
                                                    <Search size={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                                                    <input
                                                        type="text"
                                                        class="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-libre-green/40 focus:border-libre-green outline-none"
                                                        placeholder={$t('importWizard.searchAll')}
                                                        value={step4AssetQueries[res.fakeAssetId] ?? ''}
                                                        oninput={(e) => {
                                                            const q = (e.target as HTMLInputElement).value;
                                                            step4AssetQueries = {...step4AssetQueries, [res.fakeAssetId]: q};
                                                        }}
                                                    />
                                                </div>
                                                {#if (step4AssetQueries[res.fakeAssetId] ?? '').length > 0}
                                                    {@const filtered = getFilteredAssets(res.fakeAssetId)}
                                                    {#if filtered.length > 0}
                                                        <div class="mt-1 border border-gray-200 dark:border-gray-600 rounded-md overflow-hidden shadow-sm">
                                                            {#each filtered as asset (asset.id)}
                                                                <button
                                                                    type="button"
                                                                    class="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-libre-green/10 text-left transition-colors border-b border-gray-100 dark:border-gray-700 last:border-0"
                                                                    onclick={() => {
                                                                        resolveAsset(res.fakeAssetId, asset.id);
                                                                        step4AssetQueries = {...step4AssetQueries, [res.fakeAssetId]: ''};
                                                                    }}
                                                                >
                                                                    <span class="flex-1 text-gray-800 dark:text-gray-200">{asset.display_name}</span>
                                                                    {#if asset.identifier_ticker}<span class="font-mono text-xs text-gray-500">{asset.identifier_ticker}</span>{/if}
                                                                    {#if asset.identifier_isin}<span class="font-mono text-xs text-gray-400">{asset.identifier_isin}</span>{/if}
                                                                </button>
                                                            {/each}
                                                        </div>
                                                    {:else}
                                                        <div class="mt-1 text-xs text-gray-400 px-1">{$t('common.noResults') || 'No results'}</div>
                                                    {/if}
                                                {/if}
                                            </div>

                                            <!-- Zone C: Create new asset -->
                                            <button
                                                type="button"
                                                class="flex items-center gap-1.5 text-xs text-libre-green hover:underline font-medium"
                                                onclick={() => (createAssetForFakeId = res.fakeAssetId)}
                                            >
                                                <Plus size={12} />
                                                {$t('importWizard.createNew')}
                                            </button>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        {/if}
                    </div>
                {/if}

                <!-- ── TX Table ────────────────────────────────────────── -->
                <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                    <!-- Table header row -->
                    <div class="flex items-center justify-between px-4 py-2.5 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-200 dark:border-gray-700">
                        <div class="flex items-center gap-3 text-sm">
                            <span class="font-semibold">{$t('importWizard.transactionsSection') || 'Transactions'}</span>
                            <span class="text-gray-500">{step4SelectedCount} / {step4TotalCount}</span>
                            {#if step4LikelyDupCount > 0}
                                <span class="text-xs text-amber-600 dark:text-amber-400">⚠ {step4LikelyDupCount} {$t('importWizard.likelyDuplicate') || 'likely dup'}</span>
                            {/if}
                        </div>
                        <div class="flex items-center gap-2">
                            <button type="button" class="text-xs text-libre-green hover:underline" onclick={() => (mergedTransactions = mergedTransactions.map((t) => ({...t, selected: true})))}>
                                {$t('importWizard.selectAll') || 'Select all'}
                            </button>
                            <span class="text-gray-300 dark:text-gray-600">|</span>
                            <button type="button" class="text-xs text-gray-500 hover:underline" onclick={() => (mergedTransactions = mergedTransactions.map((t) => ({...t, selected: false})))}>
                                {$t('importWizard.deselectAll') || 'Deselect all'}
                            </button>
                        </div>
                    </div>

                    <!-- Scrollable TX list -->
                    <div class="max-h-[420px] overflow-y-auto">
                        <table class="w-full text-xs">
                            <thead class="sticky top-0 bg-white dark:bg-slate-900 z-10 border-b border-gray-200 dark:border-gray-700">
                                <tr class="text-left text-gray-500 dark:text-gray-400">
                                    <th class="pl-3 pr-1 py-2 w-8"></th>
                                    <th class="px-2 py-2 whitespace-nowrap">{$t('common.date') || 'Date'}</th>
                                    <th class="px-2 py-2">{$t('common.type') || 'Type'}</th>
                                    <th class="px-2 py-2">{$t('common.asset') || 'Asset'}</th>
                                    <th class="px-2 py-2 text-right">{$t('common.quantity') || 'Qty'}</th>
                                    <th class="px-2 py-2 text-right">{$t('common.cash') || 'Cash'}</th>
                                    <th class="px-2 py-2 text-right pr-3">{$t('common.status') || 'Status'}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each mergedTransactions as mt (mt.index)}
                                    {@const assetId = typeof mt.tx.asset_id === 'number' ? mt.tx.asset_id : null}
                                    {@const isUnresolvedAsset = assetId !== null && isFakeAssetId(assetId) && (assetResolutions.find((r) => r.fakeAssetId === assetId)?.resolvedAssetId == null)}
                                    <tr
                                        class="border-b border-gray-100 dark:border-gray-800 transition-colors
                                            {mt.selected ? 'bg-white dark:bg-slate-900' : 'bg-gray-50 dark:bg-slate-800/40 opacity-60'}
                                            {isUnresolvedAsset && mt.selected ? 'bg-amber-50/50 dark:bg-amber-900/10' : ''}
                                            hover:bg-gray-50 dark:hover:bg-slate-800/60"
                                    >
                                        <td class="pl-3 pr-1 py-2">
                                            <input
                                                type="checkbox"
                                                class="rounded text-libre-green"
                                                checked={mt.selected}
                                                onchange={() => {
                                                    mergedTransactions = mergedTransactions.map((t) => (t.index === mt.index ? {...t, selected: !t.selected} : t));
                                                }}
                                            />
                                        </td>
                                        <td class="px-2 py-2 font-mono text-gray-600 dark:text-gray-400 whitespace-nowrap">{mt.tx.date}</td>
                                        <td class="px-2 py-2">
                                            <span class="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                                                {mt.tx.type}
                                            </span>
                                        </td>
                                        <td class="px-2 py-2 max-w-[160px] truncate text-gray-800 dark:text-gray-200">
                                            {#if isUnresolvedAsset}
                                                <span class="text-amber-600 dark:text-amber-400">
                                                    ❓ {getAssetDisplayName(assetId)}
                                                </span>
                                            {:else}
                                                {getAssetDisplayName(assetId)}
                                            {/if}
                                        </td>
                                        <td class="px-2 py-2 text-right font-mono text-gray-600 dark:text-gray-400">
                                            {mt.tx.quantity && mt.tx.quantity !== '0' ? mt.tx.quantity : '—'}
                                        </td>
                                        <td class="px-2 py-2 text-right font-mono text-gray-600 dark:text-gray-400 whitespace-nowrap">
                                            {#if mt.tx.cash && typeof mt.tx.cash === 'object' && !Array.isArray(mt.tx.cash)}
                                                {mt.tx.cash.code} {mt.tx.cash.amount}
                                            {:else}—{/if}
                                        </td>
                                        <td class="px-2 py-2 text-right pr-3">
                                            {#if mt.duplicateStatus === 'likely'}
                                                <span class="text-xs text-amber-600 dark:text-amber-400" title={$t('importWizard.likelyDuplicate') || 'Likely duplicate'}>⚠ dup</span>
                                            {:else if mt.duplicateStatus === 'possible'}
                                                <span class="text-xs text-blue-500 dark:text-blue-400" title={$t('importWizard.possibleDuplicate') || 'Possible duplicate'}>ℹ dup</span>
                                            {:else if isUnresolvedAsset}
                                                <span class="text-xs text-amber-600 dark:text-amber-400">❓</span>
                                            {:else}
                                                <span class="text-xs text-emerald-500">✓</span>
                                            {/if}
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                        {#if mergedTransactions.length === 0}
                            <div class="py-8 text-center text-gray-400 text-sm">{$t('importWizard.noFiles') || 'No transactions'}</div>
                        {/if}
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <!-- ================================================================== -->
    <!-- Footer -->
    <!-- ================================================================== -->
    <div class="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
        {#if currentStep === 1}
            <div class="flex items-center gap-3">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={handleClose}>
                    {$t('importWizard.cancel')}
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
        {:else if currentStep === 2}
            <div class="flex items-center gap-3">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack}>
                    ◀ {$t('importWizard.back')}
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
        {:else if currentStep === 3}
            <div class="flex items-center gap-3">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack}>
                    ◀ {$t('importWizard.back')}
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
                {$t('importWizard.continue')} ▶
            </button>
        {:else}
            <div class="flex items-center gap-3">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack}>
                    ◀ {$t('importWizard.back')}
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
                {:else if step4LikelyDupCount > 0}
                    <span class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={14} />
                        {step4LikelyDupCount} {$t('importWizard.likelyDuplicate') || 'likely duplicates'} {$t('importWizard.likelyDupIncluded') || 'included'}
                    </span>
                {/if}
            </div>
            <button
                type="button"
                class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed"
                onclick={handleImport}
                disabled={!step4CanImport}
                data-testid="import-wizard-import"
            >
                {$t('importWizard.importToEditor', {values: {n: step4SelectedCount}})} ▶
            </button>
        {/if}
    </div>
</ModalBase>

<!-- Unsaved guard -->
<ConfirmModal open={confirmCloseOpen} title={$t('importWizard.discardTitle')} message={$t('importWizard.discardMessage')} confirmText={$t('importWizard.discardConfirm')} warning zIndex={80} onConfirm={confirmDiscard} onCancel={() => (confirmCloseOpen = false)} />

<!-- File preview modal -->
<FilePreviewModal open={showPreviewModal} preview={previewData} loading={previewLoading} error={previewError} onRequestClose={closePreviewModal} onSheetChange={(name) => loadPreview(name)} zIndex={80} />

<!-- Parse detail modal (single file) -->
<ParseDetailModal open={showParseDetail} parseResult={parseDetailResult} zIndex={80} onClose={closeParseDetail} />

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
{#if createAssetForFakeId !== null}
    <AssetModal
        open={true}
        editMode={false}
        zIndex={90}
        oncreated={(assetId) => {
            resolveAsset(createAssetForFakeId!, assetId);
            allUserAssetsLoaded = false;
            loadUserAssets();
            createAssetForFakeId = null;
        }}
        onclose={() => (createAssetForFakeId = null)}
    />
{/if}
