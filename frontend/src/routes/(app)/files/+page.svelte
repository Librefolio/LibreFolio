<script lang="ts">
    /**
     * Files Page - Manage static uploads and broker reports
     *
     * Two tabs:
     * 1. Static Resources - User uploaded files (/api/v1/uploads)
     * 2. Broker Reports - BRIM files (/api/v1/brokers/import/files)
     *
     * URL Deep-Linking:
     * - ?tab=static|brim - Active tab
     * - ?filename=... - Text filter on filename
     * - ?uploader=... - Uploader filter
     * - ?broker=1,2,3 - Filter by broker IDs (BRIM only)
     * - ?status=uploaded,parsed - Filter by status (BRIM only)
     * - ?size=min-max - Size range filter
     * - ?date=from,to - Date range filter
     */
    import {onMount, onDestroy} from 'svelte';
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {browser} from '$app/environment';
    import {t} from '$lib/i18n';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {generateUUID} from '$lib/utils/core/uuid';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import {formatBytes, setUploadScope, uploadFile} from '$lib/utils/files/upload';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {ensureBrokersLoaded, getEditableBrokers, brokerStoreVersion, type BrokerInfo as StoreBrokerInfo} from '$lib/stores/reference/brokerStore';
    import {ensurePluginIconsLoaded} from '$lib/utils/broker/brokerHelpers';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import {FileEditModal, ImageEditModal} from '$lib/components/ui/media';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {BrokerSearchSelect} from '$lib/components/ui/select';
    import BrokerModal from '$lib/features/brokers/BrokerModal.svelte';
    import {File as FileIcon, FileSpreadsheet, FileText, LayoutGrid, List, Pencil, RefreshCw, Trash2, X} from 'lucide-svelte';
    import FilesTable from '$lib/features/files/FilesTable.svelte';
    import FilePreviewModal from '$lib/features/files/FilePreviewModal.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import SelectionBar from '$lib/components/table/SelectionBar.svelte';
    import {matchesColumnFilter} from '$lib/components/table/dataTableLogic';
    import FileGrid from '$lib/features/files/FileGrid.svelte';
    import TabBar from '$lib/components/ui/tabs/TabBar.svelte';
    import {buildUrlFilters, parseUrlFilters, type UrlFilterConfig} from '$lib/utils/urlFilters';
    import {fetchFilePreview, getFilePreviewError} from '$lib/utils/files/filePreview';
    import type {BrimFile, BrokerInfo, FilePreviewResponse, UploadedFile, UploadScope} from '$lib/types';
    import type {ColumnDef, FilterValue} from '$lib/components/table/types';
    import {uiLocaleStore} from '$lib/stores/app/uiLocale';

    type Tab = 'static' | 'brim';
    type PreviewTarget = {source: 'static'; file: UploadedFile} | {source: 'brim'; file: BrimFile};

    // URL filter configuration - defines which columns can be filtered via URL
    const urlFilterColumns: UrlFilterConfig[] = [
        {urlKey: 'filename', type: 'text'},
        {urlKey: 'uploader', type: 'enum'},
        {urlKey: 'scope', type: 'enum'},
        {urlKey: 'broker', type: 'enum'},
        {urlKey: 'status', type: 'enum'},
        {urlKey: 'size', type: 'size'},
        {urlKey: 'date', type: 'date'},
    ];

    // LocalStorage keys (user-scoped via storage utils)
    const STORAGE_KEY_VIEW_MODE = 'filesPage_viewMode';
    const STORAGE_KEY_ACTIVE_TAB = 'filesPage_activeTab';

    // Load view mode from user-scoped localStorage (default: list/table)
    function loadViewMode(): 'grid' | 'list' {
        const stored = getUserStorage(STORAGE_KEY_VIEW_MODE, 'list');
        return stored === 'grid' ? 'grid' : 'list';
    }

    function saveViewMode(mode: 'grid' | 'list'): void {
        setUserStorage(STORAGE_KEY_VIEW_MODE, mode);
    }

    // Load active tab from user-scoped localStorage (default: static)
    function loadActiveTab(): Tab {
        const stored = getUserStorage(STORAGE_KEY_ACTIVE_TAB, 'static');
        return stored === 'brim' ? 'brim' : 'static';
    }

    function saveActiveTab(tab: Tab): void {
        setUserStorage(STORAGE_KEY_ACTIVE_TAB, tab);
    }

    // Load broker filter from user-scoped localStorage

    let activeTab: Tab = 'static';
    let staticFiles: UploadedFile[] = [];
    let brimFiles: BrimFile[] = [];
    let loading = true;
    let error: string | null = null;
    let showUploader = false;
    let pendingStaticFiles: globalThis.File[] = []; // Track files in static uploader

    // View mode with localStorage persistence (default: list/table)
    let viewMode: 'grid' | 'list' = 'list';

    // Max upload size from global settings (default: 10MB)
    let maxUploadSizeMB: number = 10;

    // Broker state for BRIM multi-user
    let brokers: StoreBrokerInfo[] = [];
    let brokerMap: Map<number, BrokerInfo> = new Map();

    // Broker IDs where user is VIEWER (cannot upload — greyed out in selector)
    $: viewerBrokerIds = new Set(brokers.filter((b) => b.user_role === 'VIEWER').map((b) => b.id));

    // URL filter state
    let initialFilters: Record<string, FilterValue> = {};
    let currentFilters: Record<string, FilterValue> = {};
    let urlInitialized = false; // Prevent URL update on initial load

    // FilesTable refs for column visibility toggle
    let staticTableRef: FilesTable;
    let brimTableRef: FilesTable;
    $: activeTableRef = activeTab === 'static' ? staticTableRef : brimTableRef;

    // Selection state for SelectionBar
    let selectedFileIds: string[] = [];

    // BRIM upload with broker selection
    let showBrimUploader = false;
    let showBrimUploadModal = false; // New modal for broker assignment
    let pendingBrimFiles: globalThis.File[] = [];
    // Map of file index -> broker_id for per-file assignment
    let fileBrokerAssignments: Map<number, number | null> = new Map();

    // Image edit modal state
    let showImageEditModal = false;
    let imageEditFile: globalThis.File | null = null;
    let imageEditFileIndex: number | null = null; // Index in pendingStaticFiles for replacement
    let fileUploaderRef: FileUploader; // Reference to FileUploader for replacing files

    // Grid search & copy — now handled internally by FileGrid component

    // Filter static files for grid search — now handled internally by FileGrid component

    // Clipboard helper — now handled internally by FileGrid component

    // File edit modal state (for non-image files)
    let showFileEditModal = false;
    let fileEditFile: globalThis.File | null = null;
    let fileEditFileIndex: number | null = null;
    let createBrokerOpen = false;

    // Confirm modal for closing uploader with pending files
    let showCloseUploaderConfirm = false;
    let closeUploaderCallback: (() => void) | null = null;

    // File preview modal state
    let showPreviewModal = false;
    let previewLoading = false;
    let previewError: string | null = null;
    let previewData: FilePreviewResponse | null = null;
    let previewTarget: PreviewTarget | null = null;
    let previewRequestToken = 0;

    onMount(async () => {
        // Load localStorage preferences as fallback
        viewMode = loadViewMode();

        // Parse URL params (takes priority over localStorage)
        if (browser) {
            const params = $page.url.searchParams;

            // Tab from URL or localStorage
            const tabParam = params.get('tab');
            if (tabParam === 'static' || tabParam === 'brim') {
                activeTab = tabParam;
            } else {
                activeTab = loadActiveTab();
            }

            // Parse column filters from URL
            const urlFilters = parseUrlFilters(params, urlFilterColumns);
            if (urlFilters.size > 0) {
                initialFilters = Object.fromEntries(urlFilters);
            }
            currentFilters = initialFilters;
        } else {
            activeTab = loadActiveTab();
        }

        // The first load holds the page's Refresh button (Y11), the whole chain.
        await pageBusy.track('files-first-load', async () => {
            await loadGlobalSettings();
            await ensurePluginIconsLoaded();
            await loadBrokers();
            await loadFiles();
        });

        // Mark URL as initialized (allow updates now)
        urlInitialized = true;
    });

    /**
     * Handle filter changes from FilesTable - update URL
     */
    function handleFiltersChange(filters: Record<string, FilterValue>) {
        currentFilters = filters;
        if (!browser || !urlInitialized) return;

        // Build URL params from filters
        const filterMap = new Map(Object.entries(filters));
        const params = buildUrlFilters(filterMap, urlFilterColumns);

        // Always include tab in URL for copy/paste sharing
        params.set('tab', activeTab);

        // Update URL without navigation (preserves focus on input fields)
        const newUrl = `/files?${params.toString()}`;
        history.replaceState(history.state, '', newUrl);
    }

    function getStaticUploaderKey(file: UploadedFile): string {
        const rawUploader = file.uploaded_by_user_id;
        return rawUploader == null ? '__none__' : String(rawUploader);
    }

    const staticGridColumns: ColumnDef<UploadedFile>[] = [
        {
            id: 'filename',
            header: '',
            cell: (row) => row.original_name,
            type: 'text',
            getValue: (row) => row.original_name,
        },
        {
            id: 'uploader',
            header: '',
            cell: (row) => getStaticUploaderKey(row),
            type: 'enum',
            getValue: (row) => getStaticUploaderKey(row),
        },
        {
            id: 'scope',
            header: '',
            cell: (row) => row.scope,
            type: 'enum',
            getValue: (row) => row.scope,
        },
        {
            id: 'size',
            header: '',
            cell: (row) => row.size_bytes,
            type: 'size',
            getValue: (row) => row.size_bytes,
        },
        {
            id: 'date',
            header: '',
            cell: (row) => row.uploaded_at,
            type: 'date',
            getValue: (row) => row.uploaded_at,
        },
    ];

    function applyStaticGridFilters(files: UploadedFile[], filters: Record<string, FilterValue>): UploadedFile[] {
        const activeFilters = Object.entries(filters).filter(([, filter]) => filter != null);
        if (activeFilters.length === 0) return files;

        return files.filter((file) => {
            for (const [columnId, filterValue] of activeFilters) {
                const column = staticGridColumns.find((candidate) => candidate.id === columnId);
                if (!column) continue;
                if (!matchesColumnFilter(column, file, filterValue)) return false;
            }
            return true;
        });
    }

    /**
     * Handle tab change - update URL and reload files
     */
    function setActiveTab(tab: Tab) {
        activeTab = tab;
        saveActiveTab(tab);
        closePreviewModal();
        void reloadFiles('files-tab');

        // Update URL with new tab (keep other filters - user can clear manually)
        if (browser && urlInitialized) {
            const params = new URLSearchParams($page.url.searchParams);
            params.set('tab', tab);

            const newUrl = `/files?${params.toString()}`;
            goto(newUrl, {replaceState: true, noScroll: true});
        }
    }

    async function loadGlobalSettings() {
        // Use globalSettings store (already loaded by app layout)
        // Subscribe reactively or get current value
        const settings = globalSettings.get();
        maxUploadSizeMB = settings.max_file_upload_mb || 10;
    }

    async function loadBrokers() {
        try {
            await ensureBrokersLoaded();
            // brokers/brokerMap are kept in sync via the brokerStoreVersion
            // subscription (see below). Default-select-all runs only on the
            // first hydration when no filter is active.
            const list = getEditableBrokers();
        } catch (e) {
            console.error('Failed to load brokers:', e);
        }
    }

    /** Keep `brokers` + `brokerMap` reactive on the shared store: any cache
     *  mutation (broker edit/delete/create from elsewhere in the app) bumps
     *  $brokerStoreVersion → we rebuild the local snapshots so icon/name
     *  changes propagate without a manual reload. */
    const _brokerStoreUnsub = brokerStoreVersion.subscribe(() => {
        const list = getEditableBrokers();
        brokers = list;
        brokerMap = new Map(list.map((b) => [b.id, {id: b.id, name: b.name, icon_url: b.icon_url ?? null, portal_url: b.portal_url ?? null, default_import_plugin: (b as any).default_import_plugin ?? null}]));
    });
    onDestroy(() => _brokerStoreUnsub());

    /** A reload the page decides on (Refresh, tab, after an upload or a delete): it holds the Refresh button (Y11). */
    function reloadFiles(label: string): Promise<void> {
        return pageBusy.track(label, loadFiles);
    }

    async function loadFiles() {
        loading = true;
        error = null;

        try {
            if (activeTab === 'static') {
                const data = await zodiosApi.list_files_api_v1_uploads_get();
                staticFiles = (data.items || []) as UploadedFile[];
            } else {
                // Fetch ALL accessible files — broker filter is applied client-side
                brimFiles = (await zodiosApi.list_files_api_v1_brokers_import_files_get()) as BrimFile[];
            }
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load files';
        } finally {
            loading = false;
        }
    }

    async function handleUpload(event: CustomEvent<{files: globalThis.File[]}>) {
        const {files} = event.detail;

        try {
            // Upload ALL files directly (user should use Edit button to crop before upload)
            for (const file of files) {
                // A file uploaded here is personal: its owner shares it from the list (decision 36)
                await uploadFile(file, undefined, 'personal');
            }

            // Close uploader and refresh
            showUploader = false;
            pendingStaticFiles = [];
            await reloadFiles('files-reload');
            // No toast: the new rows appear in the list, which is the confirmation.
            notify({name: 'file.uploaded', detail: {count: files.length}});
        } catch (e) {
            error = e instanceof Error ? e.message : 'Upload failed';
            // No toast: `error` is rendered in the page.
            notify({name: 'file.upload.failed', detail: {reason: error}});
        }
    }

    // Queue of images waiting to be edited
    let pendingImageFiles: globalThis.File[] = [];

    // Handle completion of image editing - process next image or finish
    async function handleImageEditComplete(event: CustomEvent<{url: string | null; file: File}>) {
        const {file: croppedFile} = event.detail;

        // Case 1: Edit from button (not during upload flow)
        if (imageEditFileIndex !== null) {
            // Replace the file in the pending list with the cropped version
            fileUploaderRef?.replaceFile(imageEditFileIndex, croppedFile);

            // Close modal and reset state
            showImageEditModal = false;
            imageEditFile = null;
            imageEditFileIndex = null;
            return;
        }

        // Case 2: During upload flow - image was already uploaded by ImageEditModal
        showImageEditModal = false;
        imageEditFile = null;

        // Check if there are more images to process
        if (pendingImageFiles.length > 0) {
            const nextImage = pendingImageFiles.shift()!;
            pendingImageFiles = [...pendingImageFiles]; // trigger reactivity
            imageEditFile = nextImage;
            showImageEditModal = true;
        } else {
            // All images processed, close uploader and refresh
            showUploader = false;
            pendingStaticFiles = [];
            await reloadFiles('files-reload');
        }
    }

    // Handle edit image button click from FileUploader
    function handleEditImage(event: CustomEvent<{file: globalThis.File; index: number}>) {
        const {file, index} = event.detail;
        imageEditFile = file;
        imageEditFileIndex = index;
        showImageEditModal = true;
    }

    // Handle cancel of image editing
    function handleImageEditCancel() {
        showImageEditModal = false;
        imageEditFile = null;
        imageEditFileIndex = null;
        // Clear pending images queue
        pendingImageFiles = [];
    }

    // Handle edit file (non-image) button click from FileUploader
    function handleEditFile(event: CustomEvent<{file: globalThis.File; index: number}>) {
        const {file, index} = event.detail;
        fileEditFile = file;
        fileEditFileIndex = index;
        showFileEditModal = true;
    }

    // Handle completion of file editing (rename)
    function handleFileEditComplete(event: CustomEvent<{url: string | null; file: File}>) {
        const {file: renamedFile} = event.detail;

        if (fileEditFileIndex !== null) {
            if (activeTab === 'brim' && fileEditFileIndex < pendingBrimFiles.length) {
                // BRIM context: replace in pendingBrimFiles
                pendingBrimFiles[fileEditFileIndex] = renamedFile;
                pendingBrimFiles = [...pendingBrimFiles]; // Trigger reactivity
            } else {
                // Static context: replace in FileUploader
                fileUploaderRef?.replaceFile(fileEditFileIndex, renamedFile);
            }
        }

        showFileEditModal = false;
        fileEditFile = null;
        fileEditFileIndex = null;
    }

    // Handle cancel of file editing
    function handleFileEditCancel() {
        showFileEditModal = false;
        fileEditFile = null;
        fileEditFileIndex = null;
    }

    // BRIM Upload handlers
    function handleBrimFileSelect(event: CustomEvent<{files: globalThis.File[]}>) {
        const {files} = event.detail;
        pendingBrimFiles = files;

        // If no files, close the modal
        if (files.length === 0) {
            showBrimUploadModal = false;
            return;
        }

        // Initialize broker assignments - null means not assigned yet
        fileBrokerAssignments = new Map();
        // Brokers where user can upload (not VIEWER)
        const editableBrokers = brokers.filter((b) => !viewerBrokerIds.has(b.id));
        files.forEach((_, index) => {
            // If only one editable broker, auto-assign
            if (editableBrokers.length === 1) {
                fileBrokerAssignments.set(index, editableBrokers[0].id);
            } else {
                fileBrokerAssignments.set(index, null);
            }
        });
        fileBrokerAssignments = new Map(fileBrokerAssignments); // Trigger reactivity

        // Show the upload modal
        showBrimUploadModal = true;
    }

    function assignAllBroker(brokerId: number | null) {
        pendingBrimFiles.forEach((_, index) => {
            fileBrokerAssignments.set(index, brokerId);
        });
        fileBrokerAssignments = new Map(fileBrokerAssignments); // Trigger reactivity
    }

    function assignFileBroker(fileIndex: number, brokerId: number | null) {
        fileBrokerAssignments.set(fileIndex, brokerId);
        fileBrokerAssignments = new Map(fileBrokerAssignments); // Trigger reactivity
    }

    function canConfirmBrimUpload(): boolean {
        // All files must have a broker assigned
        for (const [_, brokerId] of fileBrokerAssignments) {
            if (brokerId === null) return false;
        }
        return pendingBrimFiles.length > 0;
    }

    // Reactive derived: Svelte needs explicit var refs to track reactivity
    $: canConfirmBrim = pendingBrimFiles.length > 0 && [...fileBrokerAssignments.values()].every((v) => v !== null);

    async function confirmBrimUpload() {
        if (!canConfirmBrimUpload()) return;

        try {
            // Collect broker IDs used in upload
            const usedBrokerIds = new Set<number>();
            // Files uploaded together form one report set: they share a batch id.
            const batchId = generateUUID();

            for (let i = 0; i < pendingBrimFiles.length; i++) {
                const file = pendingBrimFiles[i];
                const brokerId = fileBrokerAssignments.get(i);
                if (!brokerId) continue;

                usedBrokerIds.add(brokerId);
                const formData = new FormData();
                formData.append('file', file);
                formData.append('broker_id', String(brokerId));
                formData.append('batch_id', batchId);
                // Use axios directly - Zodios doesn't handle FormData correctly
                await axiosInstance.post(`/api/v1/brokers/import/upload`, formData);
            }

            // Reset state
            closeBrimUploadModal();
            await reloadFiles('files-reload');
        } catch (e) {
            error = e instanceof Error ? e.message : 'Upload failed';
        }
    }

    function closeBrimUploadModal() {
        showBrimUploadModal = false;
        showBrimUploader = false;
        pendingBrimFiles = [];
        fileBrokerAssignments = new Map();
    }

    function cancelBrimUpload() {
        closeBrimUploadModal();
    }

    // Handle static file selection change
    function handleStaticFileChange(event: CustomEvent<{files: globalThis.File[]}>) {
        pendingStaticFiles = event.detail.files;
    }

    // Toggle uploader visibility with confirmation if files are pending
    function toggleStaticUploader() {
        if (showUploader) {
            // Closing - check if there are pending files
            if (pendingStaticFiles.length > 0) {
                showCloseUploaderConfirm = true;
                closeUploaderCallback = () => {
                    showUploader = false;
                    pendingStaticFiles = [];
                    showCloseUploaderConfirm = false;
                    closeUploaderCallback = null;
                };
            } else {
                showUploader = false;
            }
        } else {
            showUploader = true;
        }
    }

    function toggleBrimUploader() {
        if (showBrimUploader || showBrimUploadModal) {
            // Closing - check if there are pending files
            if (pendingBrimFiles.length > 0) {
                // Show confirmation
                showCloseUploaderConfirm = true;
                closeUploaderCallback = () => {
                    cancelBrimUpload();
                    showCloseUploaderConfirm = false;
                    closeUploaderCallback = null;
                };
            } else {
                showBrimUploader = false;
                showBrimUploadModal = false;
            }
        } else {
            showBrimUploader = true;
        }
    }

    function confirmCloseUploader() {
        if (closeUploaderCallback) {
            closeUploaderCallback();
        }
    }

    function cancelCloseUploader() {
        showCloseUploaderConfirm = false;
        closeUploaderCallback = null;
    }

    async function deleteFile(fileId: string, isBrim: boolean = false) {
        try {
            if (isBrim) {
                await zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {params: {file_id: fileId}});
            } else {
                await zodiosApi.delete_file_api_v1_uploads__file_id__delete(undefined, {params: {file_id: fileId}});
            }
            await reloadFiles('files-reload');
            notify({name: 'file.deleted', detail: {fileId, isBrim}});
        } catch (e) {
            error = e instanceof Error ? e.message : 'Delete failed';
            notify({name: 'file.delete.failed', detail: {fileId, isBrim, reason: error}});
        }
    }

    /** The selected files the user may delete; the others (uploaded by someone else) stay, with a notice. */
    function deletableSelection(isBrim: boolean): string[] {
        const files: Array<UploadedFile | BrimFile> = isBrim ? brimFiles : staticFiles;
        const blocked = new Set(files.filter((file) => (file as {can_delete?: boolean}).can_delete === false).map((file) => ('file_id' in file ? file.file_id : file.id)));
        return selectedFileIds.filter((fileId) => !blocked.has(fileId));
    }

    async function handleBulkDeleteFiles() {
        const isBrim = activeTab === 'brim';
        const deletable = deletableSelection(isBrim);
        const kept = selectedFileIds.length - deletable.length;
        if (kept > 0) {
            notify({name: 'file.delete.skipped', detail: {count: kept, isBrim}, toast: {variant: 'warning', message: $t('uploads.deleteSkipped')}});
        }
        if (deletable.length === 0) return;
        try {
            for (const fileId of deletable) {
                if (isBrim) {
                    await zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {params: {file_id: fileId}});
                } else {
                    await zodiosApi.delete_file_api_v1_uploads__file_id__delete(undefined, {params: {file_id: fileId}});
                }
            }
            const deletedCount = deletable.length;
            selectedFileIds = [];
            activeTableRef?.getTableRef()?.clearSelection();
            await reloadFiles('files-reload');
            notify({name: 'file.deleted.bulk', detail: {count: deletedCount, isBrim}});
        } catch (e) {
            error = e instanceof Error ? e.message : 'Delete failed';
            notify({name: 'file.delete.failed', detail: {isBrim, reason: error}});
        }
    }

    // Scope (decision 36): sharing is immediate; making a file personal asks first, since the others lose it
    let scopeConfirmFile: UploadedFile | null = null;

    function requestScopeChange(file: UploadedFile, scope: UploadScope) {
        if (scope === 'personal') {
            scopeConfirmFile = file;
            return;
        }
        void applyScopeChange(file, scope);
    }

    function confirmMakePersonal() {
        const file = scopeConfirmFile;
        scopeConfirmFile = null;
        if (file) void applyScopeChange(file, 'personal');
    }

    async function applyScopeChange(file: UploadedFile, scope: UploadScope) {
        try {
            const updated = await setUploadScope(file.id, scope);
            staticFiles = staticFiles.map((candidate) => (candidate.id === updated.id ? updated : candidate));
            const message = scope === 'common' ? $t('uploads.scope.nowShared', {values: {name: file.original_name}}) : $t('uploads.scope.nowPersonal', {values: {name: file.original_name}});
            notify({name: 'file.scope.changed', detail: {fileId: file.id, scope}, toast: {variant: 'success', message}});
        } catch (e) {
            notify({name: 'file.scope.change.failed', detail: {fileId: file.id, scope, reason: e instanceof Error ? e.message : String(e)}, toast: {variant: 'error', message: $t('uploads.scope.changeFailed')}});
        }
    }

    async function openStaticPreview(file: UploadedFile) {
        previewTarget = {source: 'static', file};
        showPreviewModal = true;
        previewData = null;
        previewError = null;
        await loadPreview();
    }

    async function openBrimPreview(file: BrimFile) {
        previewTarget = {source: 'brim', file};
        showPreviewModal = true;
        previewData = null;
        previewError = null;
        await loadPreview();
    }

    async function loadPreview(sheetName?: string) {
        if (!previewTarget) return;

        const token = ++previewRequestToken;
        previewLoading = true;
        previewError = null;

        try {
            const response = await fetchFilePreview(previewTarget.source === 'static' ? {source: 'static', fileId: previewTarget.file.id} : {source: 'brim', fileId: previewTarget.file.file_id}, sheetName);
            if (token === previewRequestToken) {
                previewData = response;
            }
        } catch (error) {
            if (token === previewRequestToken) {
                previewData = null;
                previewError = getFilePreviewError(error, 'Preview failed');
            }
        } finally {
            if (token === previewRequestToken) {
                previewLoading = false;
            }
        }
    }

    async function handlePreviewSheetChange(sheetName: string) {
        if (!sheetName) return;
        await loadPreview(sheetName);
    }

    function closePreviewModal() {
        previewRequestToken += 1;
        showPreviewModal = false;
        previewLoading = false;
        previewError = null;
        previewData = null;
        previewTarget = null;
    }

    function formatDate(dateStr: string): string {
        return formatDateTime(dateStr);
    }

    // isImage and getFileIcon — now handled internally by FileGrid component

    function setViewMode(mode: 'grid' | 'list') {
        viewMode = mode;
        saveViewMode(mode);
    }
</script>

<div class="files-page" aria-busy={loading} data-busy={loading ? 'true' : 'false'} data-testid="files-page">
    <header class="page-header">
        <h1>{$t('uploads.title')}</h1>

        <div class="header-actions">
            <!-- View mode toggle (only for static tab) -->
            {#if activeTab === 'static' && staticFiles.length > 0}
                <div class="view-toggle" data-testid="view-mode-toggle">
                    <button class="view-btn" class:active={viewMode === 'grid'} on:click={() => setViewMode('grid')} title="Grid view" data-testid="view-mode-grid" aria-pressed={viewMode === 'grid'}>
                        <LayoutGrid size={18} />
                    </button>
                    <button class="view-btn" class:active={viewMode === 'list'} on:click={() => setViewMode('list')} title="List view" data-testid="view-mode-list" aria-pressed={viewMode === 'list'}>
                        <List size={18} />
                    </button>
                </div>
            {/if}

            {#if activeTab === 'static'}
                <button class="btn {showUploader ? 'btn-secondary' : 'btn-primary'}" data-testid="upload-button" on:click={toggleStaticUploader}>
                    {showUploader ? $t('common.close') : $t('uploads.upload')}
                </button>
            {:else if activeTab === 'brim' && brokers.length > 0}
                <button class="btn {showBrimUploader ? 'btn-secondary' : 'btn-primary'}" data-testid="upload-button" on:click={toggleBrimUploader}>
                    {showBrimUploader ? $t('common.close') : $t('uploads.upload')}
                </button>
            {/if}
            <button class="btn btn-secondary" data-testid="files-refresh-button" data-busy={pageBusy.busy ? 'true' : 'false'} title={$t('common.refresh')} disabled={pageBusy.busy} on:click={() => reloadFiles('files-refresh')}>
                <RefreshCw size={16} class={pageBusy.busy ? 'animate-spin' : ''} />
            </button>
        </div>
    </header>

    <!-- Tabs -->
    <div class="mb-6 flex items-center gap-2">
        <TabBar
            tabs={[
                {id: 'static', label: $t('uploads.staticResources'), testId: 'files-tab-static'},
                {id: 'brim', label: $t('uploads.brokerReports'), testId: 'files-tab-brim'},
            ]}
            bind:activeTab
            onchange={(tabId) => setActiveTab(tabId as Tab)}
            class="flex-1"
        />
        {#if viewMode === 'list'}
            <SelectionBar
                selectedCount={selectedFileIds.length}
                actions={[
                    {
                        id: 'delete',
                        icon: Trash2,
                        label: $t('common.delete') || 'Delete',
                        variant: 'danger',
                        onClick: handleBulkDeleteFiles,
                    },
                ]}
                onClearSelection={() => {
                    selectedFileIds = [];
                    activeTableRef?.getTableRef()?.clearSelection();
                }}
            />
            <ColumnVisibilityToggle tableRef={activeTableRef?.getTableRef()} />
        {/if}
    </div>

    <!-- Upload area (static only) -->
    {#if showUploader && activeTab === 'static'}
        <div class="upload-area">
            <FileUploader bind:this={fileUploaderRef} on:upload={handleUpload} on:change={handleStaticFileChange} on:editImage={handleEditImage} on:editFile={handleEditFile} on:error={(e: CustomEvent<{message: string}>) => (error = e.detail.message)} multiple={true} maxSizeMB={maxUploadSizeMB} />
        </div>
    {/if}

    <!-- Upload area (BRIM) - just the file selector -->
    {#if showBrimUploader && activeTab === 'brim' && !showBrimUploadModal}
        <div class="upload-area brim-upload-area">
            <FileUploader on:change={handleBrimFileSelect} on:editFile={handleEditFile} on:error={(e: CustomEvent<{message: string}>) => (error = e.detail.message)} multiple={true} maxSizeMB={maxUploadSizeMB} accept=".csv,.xlsx,.xls" />
        </div>
    {/if}

    <!-- Error message -->
    <InfoBanner dismissible message={error} ondismiss={() => (error = null)} variant="error" />

    <!-- Content -->
    <div class="content">
        {#if loading}
            <div class="loading">{$t('common.loading')}</div>
        {:else if activeTab === 'static'}
            <!-- Static Files -->
            {#if staticFiles.length === 0}
                <div class="empty-state">
                    <FileIcon size={48} />
                    <p>{$t('uploads.noFiles')}</p>
                </div>
            {:else if viewMode === 'grid'}
                <FileGrid
                    files={applyStaticGridFilters(staticFiles, currentFilters)}
                    mode="browse"
                    cardSize="full"
                    showSearch={true}
                    showActions={true}
                    ondelete={(e) => deleteFile(e.id, false)}
                    onpreview={(e) => openStaticPreview(e.file)}
                    onscopechange={(e) => requestScopeChange(e.file, e.scope)}
                />
            {:else}
                <!-- List View with New DataTable -->
                <FilesTable
                    bind:this={staticTableRef}
                    files={staticFiles}
                    type="static"
                    onDelete={(id) => deleteFile(id, false)}
                    onPreview={(file) => openStaticPreview(file as UploadedFile)}
                    initialFilters={currentFilters}
                    onFiltersChange={handleFiltersChange}
                    onSelectionChange={(ids) => (selectedFileIds = ids)}
                    onScopeChange={requestScopeChange}
                />
            {/if}
        {:else}
            <!-- BRIM Files -->
            {#if brimFiles.length === 0}
                <div class="empty-state" data-testid="brim-empty-state">
                    <FileText size={48} />
                    <p>{$t('uploads.noFiles')}</p>
                </div>
            {:else}
                <!-- BRIM Table with New DataTable — broker filter applied client-side -->
                <FilesTable
                    bind:this={brimTableRef}
                    files={brimFiles}
                    type="brim"
                    onDelete={(id) => deleteFile(id, true)}
                    onPreview={(file) => openBrimPreview(file as BrimFile)}
                    brokers={brokerMap}
                    initialFilters={currentFilters}
                    onFiltersChange={handleFiltersChange}
                    onSelectionChange={(ids) => (selectedFileIds = ids)}
                />
            {/if}
        {/if}
    </div>
</div>

<FilePreviewModal open={showPreviewModal} preview={previewData} loading={previewLoading} error={previewError} onRequestClose={closePreviewModal} onSheetChange={handlePreviewSheetChange} />

<!-- BRIM Upload Modal with per-file broker assignment -->
<ModalBase
    contentClass="upload-modal"
    maxWidth="600px"
    testId="brim-assign-modal"
    onRequestClose={() => {
        if (pendingBrimFiles.length > 0) {
            showCloseUploaderConfirm = true;
            closeUploaderCallback = () => {
                cancelBrimUpload();
                showCloseUploaderConfirm = false;
                closeUploaderCallback = null;
            };
        } else {
            closeBrimUploadModal();
        }
    }}
    open={showBrimUploadModal}
    zIndex={50}
>
    <div class="modal-header">
        <h3>{$t('uploads.assignBrokers') || 'Assign Brokers'}</h3>
        <button
            class="modal-close"
            on:click={() => {
                if (pendingBrimFiles.length > 0) {
                    showCloseUploaderConfirm = true;
                    closeUploaderCallback = () => {
                        cancelBrimUpload();
                        showCloseUploaderConfirm = false;
                        closeUploaderCallback = null;
                    };
                } else {
                    closeBrimUploadModal();
                }
            }}
        >
            <X size={20} />
        </button>
    </div>

    <div class="modal-body upload-modal-body">
        <!-- Assign All section -->
        <div class="assign-all-section" data-testid="brim-assign-all">
            <span class="assign-all-label">{$t('uploads.assignAll') || 'Assign all to'}:</span>
            <BrokerSearchSelect
                {brokers}
                disabledIds={viewerBrokerIds}
                dropdownPosition="bottom"
                onchange={(brokerId) => {
                    if (brokerId != null) {
                        assignAllBroker(brokerId);
                    }
                }}
                placeholder={$t('uploads.chooseBroker') || '-- Choose broker --'}
                value={null}
                createLabel={$t('common.createNew')}
                onCreateNew={() => (createBrokerOpen = true)}
            />
        </div>

        <!-- File list with individual broker selection -->
        <div class="files-list">
            <p class="files-count">
                {pendingBrimFiles.length}
                {pendingBrimFiles.length === 1 ? $t('uploads.file') || 'file' : $t('uploads.files') || 'files'}
                {$t('common.selected') || 'selected'}
            </p>

            {#each pendingBrimFiles as file, index}
                <div class="file-row">
                    <div class="file-info">
                        <FileSpreadsheet size={18} class="file-icon" />
                        <span class="file-name" title={file.name}>{file.name}</span>
                        <button
                            type="button"
                            class="brim-edit-btn"
                            title={$t('uploads.rename') || 'Rename'}
                            on:click={() => {
                                fileEditFileIndex = index;
                                fileEditFile = file;
                                showFileEditModal = true;
                            }}
                        >
                            <Pencil size={12} />
                        </button>
                        <span class="file-size">({formatBytes(file.size, $t, $uiLocaleStore)})</span>
                    </div>
                    <BrokerSearchSelect
                        {brokers}
                        value={fileBrokerAssignments.get(index) ?? null}
                        placeholder={$t('uploads.selectBroker') || '-- Select --'}
                        disabledIds={viewerBrokerIds}
                        onchange={(brokerId) => assignFileBroker(index, brokerId)}
                        createLabel={$t('common.createNew')}
                        onCreateNew={() => (createBrokerOpen = true)}
                    />
                </div>
            {/each}
        </div>
    </div>

    <div class="modal-footer">
        <button class="btn btn-secondary" on:click={cancelBrimUpload}>
            {$t('common.cancel')}
        </button>
        <button class="btn btn-primary" class:btn-disabled={!canConfirmBrim} disabled={!canConfirmBrim} on:click={confirmBrimUpload} data-testid="brim-upload-confirm">
            {$t('uploads.upload')} ({pendingBrimFiles.length})
        </button>
    </div>
</ModalBase>

<!-- Confirm making a file personal: the other users lose it, also where it shows as an icon or a photo -->
<ConfirmModal open={scopeConfirmFile !== null} testId="files-scope-confirm" warning title={$t('uploads.scope.makePersonal')} message={$t('uploads.scope.makePersonalConfirm')} confirmText={$t('uploads.scope.makePersonal')} onConfirm={confirmMakePersonal} onCancel={() => (scopeConfirmFile = null)} />

<!-- Confirm close uploader modal -->
<ModalBase maxWidth="sm" onRequestClose={cancelCloseUploader} open={showCloseUploaderConfirm} zIndex={60}>
    <div class="modal-header">
        <h3>{$t('common.confirm')}</h3>
        <button class="modal-close" on:click={cancelCloseUploader}>
            <X size={20} />
        </button>
    </div>
    <div class="modal-body">
        <p>{$t('uploads.confirmCloseWithPendingFiles') || 'You have files selected for upload. Are you sure you want to cancel?'}</p>
        <p class="pending-count">{pendingBrimFiles.length + pendingStaticFiles.length} {$t('uploads.files')}</p>
    </div>
    <div class="modal-footer">
        <button class="btn btn-secondary" on:click={cancelCloseUploader}>
            {$t('common.cancel')}
        </button>
        <button class="btn btn-danger" on:click={confirmCloseUploader}>
            {$t('common.confirm')}
        </button>
    </div>
</ModalBase>

<!-- Image Edit Modal -->
<ImageEditModal
    file={imageEditFile}
    on:cancel={handleImageEditCancel}
    on:complete={handleImageEditComplete}
    on:error={(e: CustomEvent<{message: string}>) => {
        error = e.detail.message;
    }}
    open={showImageEditModal}
    preset="custom"
    uploadOnComplete={imageEditFileIndex === null}
    scope="personal"
/>

<!-- File Edit Modal (non-image files) -->
<FileEditModal
    file={fileEditFile}
    on:cancel={handleFileEditCancel}
    on:complete={handleFileEditComplete}
    on:error={(e) => {
        error = e.detail.message;
    }}
    open={showFileEditModal}
    uploadOnComplete={fileEditFileIndex === null}
    scope="personal"
/>

<BrokerModal isOpen={createBrokerOpen} mode="create" onclose={() => (createBrokerOpen = false)} />

<style>
    .files-page {
        padding: 1.5rem;
        max-width: 1200px;
        margin: 0 auto;
        min-width: 0;
        overflow: hidden;
        color: var(--lf-text-primary);
    }

    .files-page .content {
        min-width: 0;
        overflow: hidden;
    }

    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
    }

    .page-header h1 {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--lf-text-primary);
        margin: 0;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .view-toggle {
        display: flex;
        border: 1px solid var(--lf-border-subtle);
        border-radius: 0.5rem;
        overflow: hidden;
    }

    .view-btn {
        padding: 0.5rem;
        background: var(--lf-surface-card);
        border: none;
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .view-btn:hover {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .view-btn.active {
        background: var(--lf-checked);
        color: var(--lf-on-checked);
    }

    .btn {
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .btn-primary {
        background-color: var(--lf-action);
        border: 1px solid var(--lf-action);
        color: var(--lf-on-action);
    }

    .btn-primary:hover {
        background-color: var(--lf-action-hover);
    }

    .upload-area {
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: var(--lf-surface-panel);
        border-radius: 0.5rem;
    }

    .loading {
        text-align: center;
        padding: 3rem;
        color: var(--lf-text-muted);
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        color: var(--lf-text-muted);
    }

    .empty-state p {
        margin-top: 1rem;
    }

    /* File Grid (Static) — styles now in FileGrid.svelte component */

    /* Modal styles — backdrop/content now handled by ModalBase */

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--lf-border-subtle);
    }

    .modal-header h3 {
        margin: 0;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--lf-text-primary);
    }

    .modal-close {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--lf-text-muted);
        padding: 0.25rem;
        border-radius: 0.25rem;
    }

    .modal-close:hover {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .modal-body {
        padding: 1.25rem;
    }

    .modal-body p {
        margin: 0;
        color: var(--lf-text-secondary);
    }

    .pending-count {
        margin-top: 0.5rem !important;
        font-weight: 500;
        color: var(--lf-text-primary) !important;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid var(--lf-border-subtle);
    }

    .btn-secondary {
        background: var(--lf-surface-panel);
        border: 1px solid var(--lf-border-subtle);
        color: var(--lf-text-secondary);
    }

    .btn-secondary:hover {
        background: var(--lf-surface-neutral);
    }

    .btn-danger {
        background: var(--lf-danger-solid);
        border: 1px solid var(--lf-danger-solid);
        color: var(--lf-on-danger-solid);
    }

    .btn-danger:hover {
        background: var(--lf-danger-hover);
    }

    .btn-disabled {
        background: var(--lf-surface-neutral) !important;
        border-color: var(--lf-surface-neutral) !important;
        cursor: not-allowed;
        opacity: 0.7;
        color: var(--lf-text-muted);
    }

    .btn-disabled:hover {
        background: var(--lf-surface-neutral) !important;
    }

    /* BRIM Upload Modal Styles — class applied via ModalBase contentClass */
    :global(.upload-modal) {
        width: 95%;
        max-height: 80vh;
        min-height: 350px;
        display: flex;
        flex-direction: column;
    }

    .upload-modal-body {
        overflow-y: auto;
        max-height: 60vh;
        min-height: 220px;
    }

    .assign-all-section {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        background: var(--lf-surface-panel);
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }

    .assign-all-label {
        font-weight: 500;
        color: var(--lf-text-secondary);
        white-space: nowrap;
        flex: 1;
    }

    /* BrokerSelect in assign-all-section should match file-row width */
    .assign-all-section :global(.broker-select) {
        min-width: 180px;
        flex-shrink: 0;
    }

    .files-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .files-count {
        font-size: 0.875rem;
        color: var(--lf-text-muted);
        margin: 0 0 0.5rem 0;
    }

    .file-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.625rem 0.75rem;
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-subtle);
        border-radius: 0.5rem;
        position: relative;
    }

    .file-info {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
        flex: 1;
    }

    .file-info :global(svg) {
        flex-shrink: 0;
        color: var(--lf-text-muted);
    }

    .brim-edit-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.25rem;
        border: none;
        background: transparent;
        color: var(--lf-text-muted);
        cursor: pointer;
        border-radius: 0.25rem;
        flex-shrink: 0;
    }

    .brim-edit-btn:hover {
        color: var(--lf-link);
        background: var(--lf-selected);
    }

    .file-row .file-name {
        font-size: 0.875rem;
        color: var(--lf-text-secondary);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
        min-width: 0;
    }

    .file-size {
        font-size: 0.75rem;
        color: var(--lf-text-muted);
        flex-shrink: 0;
    }

    @media (max-width: 480px) {
        .file-row {
            flex-direction: column;
            align-items: stretch;
            gap: 0.5rem;
        }

        .assign-all-section {
            flex-direction: column;
            align-items: stretch;
        }
    }
</style>
