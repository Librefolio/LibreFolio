<!--
  ImportWizardModal.svelte — Phase 07 Part 5 v5 M1v2 Round 2

  Wide 4-step wizard for importing broker report files into BulkModal.
  Step 1: Upload files (broker-independent) & assign broker per-file
  Step 2: Select existing broker files to parse (DataTable per broker, per-file plugin)
  Step 3: Parse (M2 placeholder)
  Step 4: Review & Import (M3 placeholder)
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Upload, Trash2, Eye, ChevronDown, ChevronRight, Check, AlertTriangle, Plus, CheckCircle} from 'lucide-svelte';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {extractErrorMessage, trySave} from '$lib/utils/trySave';
    import {formatBytes} from '$lib/utils/files/upload';
    import {ensureBrokersLoaded, getEditableBrokers, type BrokerInfo} from '$lib/stores/reference/brokerStore';
    import {toasts} from '$lib/stores/app/toastStore.svelte';

    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import {BrokerSearchSelect} from '$lib/components/ui/select';
    import ImportPluginSelect from '$lib/components/ui/select/ImportPluginSelect.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import FilePreviewModal from '$lib/components/files/FilePreviewModal.svelte';
    import {fetchFilePreview, getFilePreviewError} from '$lib/utils/files/filePreview';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';

    import type {TransactionCreateItem, BrimFile, FilePreviewResponse} from '$lib/types';

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
    // Shared State
    // =========================================================================

    let brokers = $state<BrokerInfo[]>([]);
    let brokersLoading = $state(false);
    let confirmCloseOpen = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    let hasUnsavedWork = $derived(pendingFiles.length > 0 || selectedFiles.length > 0);
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
        } else if (currentStep === 3) {
            currentStep = 4;
            if (maxReachedStep < 4) maxReachedStep = 4;
        }
    }

    function goBack() {
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
            cell: (row) => row.filename,
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
                return {
                    type: 'custom',
                    component: ImportPluginSelect,
                    props: {
                        value: sel.pluginCode,
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
                                            initialFilters={{status: {type: 'enum', selected: ['uploaded']}}}
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
            <!-- Step 3: Parse (M2 placeholder) -->
            <!-- ============================================================ -->
        {:else if currentStep === 3}
            <div class="py-12 text-center text-gray-400 dark:text-gray-500" data-testid="import-wizard-step3">
                <p class="text-lg font-medium">{$t('importWizard.step3Title')}</p>
                <p class="text-sm mt-2">Coming in Milestone 2</p>
            </div>

            <!-- ============================================================ -->
            <!-- Step 4: Review (M3 placeholder) -->
            <!-- ============================================================ -->
        {:else if currentStep === 4}
            <div class="py-12 text-center text-gray-400 dark:text-gray-500" data-testid="import-wizard-step4">
                <p class="text-lg font-medium">{$t('importWizard.step4Title')}</p>
                <p class="text-sm mt-2">Coming in Milestone 3</p>
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
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack}>
                ◀ {$t('importWizard.back')}
            </button>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed" onclick={goNext} disabled data-testid="import-wizard-continue">
                {$t('importWizard.continue')} ▶
            </button>
        {:else}
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={goBack}>
                ◀ {$t('importWizard.back')}
            </button>
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed" disabled data-testid="import-wizard-import">
                {$t('importWizard.review')} ▶
            </button>
        {/if}
    </div>
</ModalBase>

<!-- Unsaved guard -->
<ConfirmModal open={confirmCloseOpen} title={$t('importWizard.discardTitle')} message={$t('importWizard.discardMessage')} confirmText={$t('importWizard.discardConfirm')} warning zIndex={80} onConfirm={confirmDiscard} onCancel={() => (confirmCloseOpen = false)} />

<!-- File preview modal -->
<FilePreviewModal open={showPreviewModal} preview={previewData} loading={previewLoading} error={previewError} onRequestClose={closePreviewModal} onSheetChange={(name) => loadPreview(name)} zIndex={80} />
