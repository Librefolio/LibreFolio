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
     * - ?broker=1,2,3 - Filter by broker IDs (BRIM only)
     * - ?status=uploaded,parsed - Filter by status (BRIM only)
     * - ?size=min-max - Size range filter
     * - ?date=from,to - Date range filter
     */
    import {onMount} from 'svelte';
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {browser} from '$app/environment';
    import {t} from '$lib/i18n';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {uploadFile, formatBytes} from '$lib/utils/upload';
    import {globalSettings} from '$lib/stores/globalSettings';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import {ImageEditModal, FileEditModal} from '$lib/components/ui/media';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {BrokerSearchSelect} from '$lib/components/ui/select';
    import {File as FileIcon, FileSpreadsheet, FileText, LayoutGrid, List, Pencil, Search, Trash2, X} from 'lucide-svelte';
    import FilesTable from '$lib/components/files/FilesTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import SelectionBar from '$lib/components/table/SelectionBar.svelte';
    import FileGrid from '$lib/components/files/FileGrid.svelte';
    import {buildUrlFilters, parseUrlFilters, type UrlFilterConfig} from '$lib/utils/urlFilters';
    import type {BrimFile, Broker, BrokerInfo, UploadedFile} from '$lib/types';
    import type {FilterValue} from '$lib/components/table/types';

    type Tab = 'static' | 'brim';

    // URL filter configuration - defines which columns can be filtered via URL
    const urlFilterColumns: UrlFilterConfig[] = [
        {urlKey: 'filename', type: 'text'},
        {urlKey: 'broker', type: 'enum'},
        {urlKey: 'status', type: 'enum'},
        {urlKey: 'size', type: 'size'},
        {urlKey: 'date', type: 'date'},
    ];


    // LocalStorage keys
    const STORAGE_KEY_VIEW_MODE = 'filesPage_viewMode';
    const STORAGE_KEY_ACTIVE_TAB = 'filesPage_activeTab';
    const STORAGE_KEY_BROKER_FILTER = 'filesPage_brokerFilter';

    // Load view mode from localStorage (default: list/table)
    function loadViewMode(): 'grid' | 'list' {
        if (typeof window === 'undefined') return 'list';
        try {
            const stored = localStorage.getItem(STORAGE_KEY_VIEW_MODE);
            return stored === 'grid' ? 'grid' : 'list';
        } catch {
            return 'list';
        }
    }

    function saveViewMode(mode: 'grid' | 'list'): void {
        if (typeof window === 'undefined') return;
        try {
            localStorage.setItem(STORAGE_KEY_VIEW_MODE, mode);
        } catch {
            // Ignore storage errors
        }
    }

    // Load active tab from localStorage (default: static)
    function loadActiveTab(): Tab {
        if (typeof window === 'undefined') return 'static';
        try {
            const stored = localStorage.getItem(STORAGE_KEY_ACTIVE_TAB);
            return stored === 'brim' ? 'brim' : 'static';
        } catch {
            return 'static';
        }
    }

    function saveActiveTab(tab: Tab): void {
        if (typeof window === 'undefined') return;
        try {
            localStorage.setItem(STORAGE_KEY_ACTIVE_TAB, tab);
        } catch {
            // Ignore storage errors
        }
    }

    // Load broker filter from localStorage
    function loadBrokerFilter(): Set<number> {
        if (typeof window === 'undefined') return new Set();
        try {
            const stored = localStorage.getItem(STORAGE_KEY_BROKER_FILTER);
            if (stored) {
                return new Set(JSON.parse(stored) as number[]);
            }
        } catch {
            // Ignore
        }
        return new Set();
    }

    function saveBrokerFilter(filter: Set<number>): void {
        if (typeof window === 'undefined') return;
        try {
            localStorage.setItem(STORAGE_KEY_BROKER_FILTER, JSON.stringify(Array.from(filter)));
        } catch {
            // Ignore
        }
    }

    let activeTab: Tab = 'static';
    let staticFiles: UploadedFile[] = [];
    let brimFiles: BrimFile[] = [];
    let loading = true;
    let error: string | null = null;
    let showUploader = false;
    let pendingStaticFiles: globalThis.File[] = [];  // Track files in static uploader

    // View mode with localStorage persistence (default: list/table)
    let viewMode: 'grid' | 'list' = 'list';

    // Max upload size from global settings (default: 10MB)
    let maxUploadSizeMB: number = 10;

    // Broker state for BRIM multi-user
    let brokers: Broker[] = [];
    let brokerMap: Map<number, BrokerInfo> = new Map();
    let selectedBrokerIds: Set<number> = new Set();

    // Broker IDs where user is VIEWER (cannot upload — greyed out in selector)
    $: viewerBrokerIds = new Set(
        brokers.filter(b => (b as any).user_role === 'VIEWER').map(b => b.id)
    );

    // URL filter state
    let initialFilters: Record<string, FilterValue> = {};
    let urlInitialized = false;  // Prevent URL update on initial load

    // FilesTable refs for column visibility toggle
    let staticTableRef: FilesTable;
    let brimTableRef: FilesTable;
    $: activeTableRef = activeTab === 'static' ? staticTableRef : brimTableRef;

    // Selection state for SelectionBar
    let selectedFileIds: string[] = [];

    // BRIM upload with broker selection
    let showBrimUploader = false;
    let showBrimUploadModal = false;  // New modal for broker assignment
    let pendingBrimFiles: globalThis.File[] = [];
    // Map of file index -> broker_id for per-file assignment
    let fileBrokerAssignments: Map<number, number | null> = new Map();

    // Image edit modal state
    let showImageEditModal = false;
    let imageEditFile: globalThis.File | null = null;
    let imageEditFileIndex: number | null = null;  // Index in pendingStaticFiles for replacement
    let fileUploaderRef: FileUploader;  // Reference to FileUploader for replacing files

    // Grid search & copy — now handled internally by FileGrid component

    // Filter static files for grid search — now handled internally by FileGrid component

    // Clipboard helper — now handled internally by FileGrid component

    // File edit modal state (for non-image files)
    let showFileEditModal = false;
    let fileEditFile: globalThis.File | null = null;
    let fileEditFileIndex: number | null = null;

    // Confirm modal for closing uploader with pending files
    let showCloseUploaderConfirm = false;
    let closeUploaderCallback: (() => void) | null = null;

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
        } else {
            activeTab = loadActiveTab();
        }

        selectedBrokerIds = loadBrokerFilter();
        await loadGlobalSettings();
        await loadBrokers();
        await loadFiles();

        // Mark URL as initialized (allow updates now)
        urlInitialized = true;
    });

    /**
     * Handle filter changes from FilesTable - update URL
     */
    function handleFiltersChange(filters: Record<string, FilterValue>) {
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

    /**
     * Handle tab change - update URL and reload files
     */
    function setActiveTab(tab: Tab) {
        activeTab = tab;
        saveActiveTab(tab);
        loadFiles();

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
            brokers = await zodiosApi.list_brokers_api_v1_brokers_get() as Broker[];
            brokerMap = new Map(brokers.map(b => [b.id, {id: b.id, name: b.name}]));
            // If no filter selected, select all brokers by default
            if (selectedBrokerIds.size === 0 && brokers.length > 0) {
                selectedBrokerIds = new Set(brokers.map(b => b.id));
                saveBrokerFilter(selectedBrokerIds);
            }
        } catch (e) {
            console.error('Failed to load brokers:', e);
        }
    }

    async function loadFiles() {
        loading = true;
        error = null;

        try {
            if (activeTab === 'static') {
                const data = await zodiosApi.list_files_api_v1_uploads_get();
                staticFiles = (data.items || []) as UploadedFile[];
            } else {
                // For BRIM, filter by selected broker IDs
                const brokerIds = Array.from(selectedBrokerIds);
                brimFiles = await zodiosApi.list_files_api_v1_brokers_import_files_get({
                    queries: brokerIds.length > 0 ? {broker_ids: brokerIds} : undefined
                }) as BrimFile[];
            }
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load files';
        } finally {
            loading = false;
        }
    }

    function toggleBrokerFilter(brokerId: number) {
        if (selectedBrokerIds.has(brokerId)) {
            selectedBrokerIds.delete(brokerId);
        } else {
            selectedBrokerIds.add(brokerId);
        }
        selectedBrokerIds = new Set(selectedBrokerIds); // Trigger reactivity
        saveBrokerFilter(selectedBrokerIds);
        loadFiles(); // Reload with new filter
    }

    function selectAllBrokers() {
        selectedBrokerIds = new Set(brokers.map(b => b.id));
        saveBrokerFilter(selectedBrokerIds);
        loadFiles();
    }

    function clearBrokerFilter() {
        selectedBrokerIds = new Set();
        saveBrokerFilter(selectedBrokerIds);
        loadFiles();
    }

    async function handleUpload(event: CustomEvent<{ files: globalThis.File[] }>) {
        const {files} = event.detail;

        try {
            // Upload ALL files directly (user should use Edit button to crop before upload)
            for (const file of files) {
                await uploadFile(file);
            }

            // Close uploader and refresh
            showUploader = false;
            pendingStaticFiles = [];
            await loadFiles();
        } catch (e) {
            error = e instanceof Error ? e.message : 'Upload failed';
        }
    }

    // Queue of images waiting to be edited
    let pendingImageFiles: globalThis.File[] = [];

    // Handle completion of image editing - process next image or finish
    async function handleImageEditComplete(event: CustomEvent<{url: string | null; file: File}>) {
        const { file: croppedFile } = event.detail;

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
            await loadFiles();
        }
    }

    // Handle edit image button click from FileUploader
    function handleEditImage(event: CustomEvent<{ file: globalThis.File; index: number }>) {
        const { file, index } = event.detail;
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
    function handleEditFile(event: CustomEvent<{ file: globalThis.File; index: number }>) {
        const { file, index } = event.detail;
        fileEditFile = file;
        fileEditFileIndex = index;
        showFileEditModal = true;
    }

    // Handle completion of file editing (rename)
    function handleFileEditComplete(event: CustomEvent<{url: string | null; file: File}>) {
        const { file: renamedFile } = event.detail;

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
    function handleBrimFileSelect(event: CustomEvent<{ files: globalThis.File[] }>) {
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
        const editableBrokers = brokers.filter(b => !viewerBrokerIds.has(b.id));
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
    $: canConfirmBrim = pendingBrimFiles.length > 0 && [...fileBrokerAssignments.values()].every(v => v !== null);

    async function confirmBrimUpload() {
        if (!canConfirmBrimUpload()) return;

        try {
            // Collect broker IDs used in upload
            const usedBrokerIds = new Set<number>();

            for (let i = 0; i < pendingBrimFiles.length; i++) {
                const file = pendingBrimFiles[i];
                const brokerId = fileBrokerAssignments.get(i);
                if (!brokerId) continue;

                usedBrokerIds.add(brokerId);
                const formData = new FormData();
                formData.append('file', file);
                // Use axios directly - Zodios doesn't handle FormData correctly
                await axiosInstance.post(`/api/v1/brokers/import/upload?broker_id=${brokerId}`, formData);
            }

            // Add used broker IDs to selected filter so uploaded files are visible
            usedBrokerIds.forEach(id => selectedBrokerIds.add(id));
            selectedBrokerIds = new Set(selectedBrokerIds); // Trigger reactivity
            saveBrokerFilter(selectedBrokerIds);

            // Reset state
            closeBrimUploadModal();
            await loadFiles();
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
    function handleStaticFileChange(event: CustomEvent<{ files: globalThis.File[] }>) {
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
            await loadFiles();
        } catch (e) {
            error = e instanceof Error ? e.message : 'Delete failed';
        }
    }

    async function handleBulkDeleteFiles() {
        const isBrim = activeTab === 'brim';
        try {
            for (const fileId of selectedFileIds) {
                if (isBrim) {
                    await zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {params: {file_id: fileId}});
                } else {
                    await zodiosApi.delete_file_api_v1_uploads__file_id__delete(undefined, {params: {file_id: fileId}});
                }
            }
            selectedFileIds = [];
            activeTableRef?.getTableRef()?.clearSelection();
            await loadFiles();
        } catch (e) {
            error = e instanceof Error ? e.message : 'Delete failed';
        }
    }


    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // isImage and getFileIcon — now handled internally by FileGrid component

    function setViewMode(mode: 'grid' | 'list') {
        viewMode = mode;
        saveViewMode(mode);
    }
</script>

<svelte:head>
    <title>{$t('uploads.title')} - LibreFolio</title>
</svelte:head>

<div class="files-page" data-testid="files-page">
    <header class="page-header">
        <h1>{$t('uploads.title')}</h1>

        <div class="header-actions">
            <!-- View mode toggle (only for static tab) -->
            {#if activeTab === 'static' && staticFiles.length > 0}
                <div class="view-toggle" data-testid="view-mode-toggle">
                    <button
                            class="view-btn"
                            class:active={viewMode === 'grid'}
                            on:click={() => setViewMode('grid')}
                            title="Grid view"
                            data-testid="view-mode-grid"
                    >
                        <LayoutGrid size={18}/>
                    </button>
                    <button
                            class="view-btn"
                            class:active={viewMode === 'list'}
                            on:click={() => setViewMode('list')}
                            title="List view"
                            data-testid="view-mode-list"
                    >
                        <List size={18}/>
                    </button>
                </div>
            {/if}

            {#if activeTab === 'static'}
                <button
                        class="btn {showUploader ? 'btn-secondary' : 'btn-primary'}"
                        data-testid="upload-button"
                        on:click={toggleStaticUploader}
                >
                    {showUploader ? $t('common.close') : $t('uploads.upload')}
                </button>
            {:else if activeTab === 'brim' && brokers.length > 0}
                <button
                        class="btn {showBrimUploader ? 'btn-secondary' : 'btn-primary'}"
                        data-testid="upload-button"
                        on:click={toggleBrimUploader}
                >
                    {showBrimUploader ? $t('common.close') : $t('uploads.upload')}
                </button>
            {/if}
        </div>
    </header>

    <!-- Tabs -->
    <div class="flex items-center gap-2">
        <div class="tabs flex-1" role="tablist">
            <button
                    aria-selected={activeTab === 'static'}
                    class="tab"
                    class:active={activeTab === 'static'}
                    data-testid="files-tab-static"
                    on:click={() => setActiveTab('static')}
                    role="tab"
            >
                {$t('uploads.staticResources')}
            </button>
            <button
                    aria-selected={activeTab === 'brim'}
                    class="tab"
                    class:active={activeTab === 'brim'}
                    data-testid="files-tab-brim"
                    on:click={() => setActiveTab('brim')}
                    role="tab"
            >
                {$t('uploads.brokerReports')}
            </button>
        </div>
        {#if viewMode === 'list'}
            <SelectionBar
                selectedCount={selectedFileIds.length}
                actions={[{
                    id: 'delete',
                    icon: Trash2,
                    label: $t('common.delete') || 'Delete',
                    variant: 'danger',
                    onClick: handleBulkDeleteFiles,
                }]}
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
            <FileUploader
                    bind:this={fileUploaderRef}
                    on:upload={handleUpload}
                    on:change={handleStaticFileChange}
                    on:editImage={handleEditImage}
                    on:editFile={handleEditFile}
                    on:error={(e: CustomEvent<{ message: string }>) => error = e.detail.message}
                    multiple={true}
                    maxSizeMB={maxUploadSizeMB}
            />
        </div>
    {/if}

    <!-- Upload area (BRIM) - just the file selector -->
    {#if showBrimUploader && activeTab === 'brim' && !showBrimUploadModal}
        <div class="upload-area brim-upload-area">
            <FileUploader
                    on:change={handleBrimFileSelect}
                    on:editFile={handleEditFile}
                    on:error={(e: CustomEvent<{ message: string }>) => error = e.detail.message}
                    multiple={true}
                    maxSizeMB={maxUploadSizeMB}
                    accept=".csv,.xlsx,.xls"
            />
        </div>
    {/if}

    <!-- Error message -->
    <InfoBanner variant="error" message={error} dismissible ondismiss={() => error = null} />

    <!-- Content -->
    <div class="content">
        {#if loading}
            <div class="loading">{$t('common.loading')}</div>
        {:else if activeTab === 'static'}
            <!-- Static Files -->
            {#if staticFiles.length === 0}
                <div class="empty-state">
                    <FileIcon size={48}/>
                    <p>{$t('uploads.noFiles')}</p>
                </div>
            {:else if viewMode === 'grid'}
                <FileGrid
                    files={staticFiles}
                    mode="browse"
                    cardSize="full"
                    showSearch={true}
                    showActions={true}
                    on:delete={(e) => deleteFile(e.detail.id, false)}
                />
            {:else}
                <!-- List View with New DataTable -->
                <FilesTable
                        bind:this={staticTableRef}
                        files={staticFiles}
                        type="static"
                        onDelete={(id) => deleteFile(id, false)}
                        {initialFilters}
                        onFiltersChange={handleFiltersChange}
                        onSelectionChange={(ids) => selectedFileIds = ids}
                />
            {/if}
        {:else}
            <!-- BRIM Files -->
            {#if brimFiles.length === 0}
                <div class="empty-state" data-testid="brim-empty-state">
                    <FileText size={48}/>
                    <p>{$t('uploads.noFiles')}</p>
                </div>
            {:else}
                <!-- BRIM Table with New DataTable -->
                <FilesTable
                        bind:this={brimTableRef}
                        files={brimFiles}
                        type="brim"
                        onDelete={(id) => deleteFile(id, true)}
                        brokers={brokerMap}
                        {initialFilters}
                        onFiltersChange={handleFiltersChange}
                        onSelectionChange={(ids) => selectedFileIds = ids}
                />
            {/if}
        {/if}
    </div>
</div>

<!-- BRIM Upload Modal with per-file broker assignment -->
<ModalBase
    open={showBrimUploadModal}
    zIndex={50}
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
    contentClass="upload-modal"
    maxWidth="600px"
>
            <div class="modal-header">
                <h3>{$t('uploads.assignBrokers') || 'Assign Brokers'}</h3>
                <button class="modal-close" on:click={() => {
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
                }}>
                    <X size={20}/>
                </button>
            </div>

            <div class="modal-body upload-modal-body">
                <!-- Assign All section -->
                <div class="assign-all-section">
                    <span class="assign-all-label">{$t('uploads.assignAll') || 'Assign all to'}:</span>
                    <BrokerSearchSelect
                            brokers={brokers}
                            value={null}
                            placeholder={$t('uploads.chooseBroker') || '-- Choose broker --'}
                            dropdownPosition="bottom"
                            disabledIds={viewerBrokerIds}
                            onchange={(brokerId) => {
                            if (brokerId != null) {
                                assignAllBroker(brokerId);
                            }
                        }}
                    />
                </div>

                <!-- File list with individual broker selection -->
                <div class="files-list">
                    <p class="files-count">
                        {pendingBrimFiles.length} {pendingBrimFiles.length === 1 ? $t('uploads.file') || 'file' : $t('uploads.files') || 'files'} {$t('common.selected') || 'selected'}
                    </p>

                    {#each pendingBrimFiles as file, index}
                        <div class="file-row">
                            <div class="file-info">
                                <FileSpreadsheet size={18} class="file-icon"/>
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
                                    <Pencil size={12}/>
                                </button>
                                <span class="file-size">({formatBytes(file.size)})</span>
                            </div>
                            <BrokerSearchSelect
                                    brokers={brokers}
                                    value={fileBrokerAssignments.get(index) ?? null}
                                    placeholder={$t('uploads.selectBroker') || '-- Select --'}
                                    disabledIds={viewerBrokerIds}
                                    onchange={(brokerId) => assignFileBroker(index, brokerId)}
                            />
                        </div>
                    {/each}
                </div>
            </div>

            <div class="modal-footer">
                <button class="btn btn-secondary" on:click={cancelBrimUpload}>
                    {$t('common.cancel')}
                </button>
                <button
                        class="btn btn-primary"
                        class:btn-disabled={!canConfirmBrim}
                        on:click={confirmBrimUpload}
                        disabled={!canConfirmBrim}
                >
                    {$t('uploads.upload')} ({pendingBrimFiles.length})
                </button>
            </div>
</ModalBase>

<!-- Confirm close uploader modal -->
<ModalBase
    open={showCloseUploaderConfirm}
    zIndex={60}
    maxWidth="sm"
    onRequestClose={cancelCloseUploader}
>
            <div class="modal-header">
                <h3>{$t('common.confirm')}</h3>
                <button class="modal-close" on:click={cancelCloseUploader}>
                    <X size={20}/>
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
    open={showImageEditModal}
    file={imageEditFile}
    preset="custom"
    uploadOnComplete={imageEditFileIndex === null}
    on:complete={handleImageEditComplete}
    on:cancel={handleImageEditCancel}
    on:error={(e: CustomEvent<{message: string}>) => {
        error = e.detail.message;
    }}
/>

<!-- File Edit Modal (non-image files) -->
<FileEditModal
    open={showFileEditModal}
    file={fileEditFile}
    uploadOnComplete={fileEditFileIndex === null}
    on:complete={handleFileEditComplete}
    on:cancel={handleFileEditCancel}
    on:error={(e) => {
        error = e.detail.message;
    }}
/>

<style>
    .files-page {
        padding: 1.5rem;
        max-width: 1200px;
        margin: 0 auto;
        min-width: 0;
        overflow: hidden;
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
        color: #1f2937;
        margin: 0;
    }

    :global(.dark) .page-header h1 {
        color: #f3f4f6;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .view-toggle {
        display: flex;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        overflow: hidden;
    }

    :global(.dark) .view-toggle {
        border-color: #4b5563;
    }

    .view-btn {
        padding: 0.5rem;
        background: white;
        border: none;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    :global(.dark) .view-btn {
        background: #374151;
        color: #9ca3af;
    }

    .view-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .view-btn:hover {
        background: #4b5563;
        color: #f3f4f6;
    }

    .view-btn.active {
        background: #1a4031;
        color: white;
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
        background-color: #1a4031;
        border: 1px solid #1a4031;
        color: white;
    }

    .btn-primary:hover {
        background-color: #143326;
    }

    .tabs {
        display: flex;
        gap: 0;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid #e5e7eb;
    }

    :global(.dark) .tabs {
        border-bottom-color: #4b5563;
    }

    .tab {
        padding: 0.75rem 1.5rem;
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 0.875rem;
        font-weight: 500;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    :global(.dark) .tab {
        color: #9ca3af;
    }

    .tab:hover {
        color: #1a4031;
    }

    :global(.dark) .tab:hover {
        color: #10b981;
    }

    .tab.active {
        color: #1a4031;
        border-bottom-color: #1a4031;
    }

    :global(.dark) .tab.active {
        color: #10b981;
        border-bottom-color: #10b981;
    }

    .upload-area {
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: #f9fafb;
        border-radius: 0.5rem;
    }

    :global(.dark) .upload-area {
        background: #374151;
    }


    .loading {
        text-align: center;
        padding: 3rem;
        color: #6b7280;
    }

    :global(.dark) .loading {
        color: #9ca3af;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        color: #9ca3af;
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
        border-bottom: 1px solid #e5e7eb;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #374151;
    }

    .modal-header h3 {
        margin: 0;
        font-size: 1.125rem;
        font-weight: 600;
        color: #1f2937;
    }

    :global(.dark) .modal-header h3 {
        color: #f3f4f6;
    }

    .modal-close {
        background: none;
        border: none;
        cursor: pointer;
        color: #6b7280;
        padding: 0.25rem;
        border-radius: 0.25rem;
    }

    .modal-close:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .modal-close:hover {
        background: #374151;
        color: #f3f4f6;
    }

    .modal-body {
        padding: 1.25rem;
    }

    .modal-body p {
        margin: 0;
        color: #4b5563;
    }

    :global(.dark) .modal-body p {
        color: #9ca3af;
    }

    .pending-count {
        margin-top: 0.5rem !important;
        font-weight: 500;
        color: #1f2937 !important;
    }

    :global(.dark) .pending-count {
        color: #f3f4f6 !important;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid #e5e7eb;
    }

    :global(.dark) .modal-footer {
        border-top-color: #374151;
    }

    .btn-secondary {
        background: #f3f4f6;
        border: 1px solid #d1d5db;
        color: #374151;
    }

    :global(.dark) .btn-secondary {
        background: #374151;
        border-color: #4b5563;
        color: #e5e7eb;
    }

    .btn-secondary:hover {
        background: #e5e7eb;
    }

    :global(.dark) .btn-secondary:hover {
        background: #4b5563;
    }

    .btn-danger {
        background: #dc2626;
        border: 1px solid #dc2626;
        color: white;
    }

    .btn-danger:hover {
        background: #b91c1c;
    }

    .btn-disabled {
        background: #9ca3af !important;
        border-color: #9ca3af !important;
        cursor: not-allowed;
        opacity: 0.7;
    }

    .btn-disabled:hover {
        background: #9ca3af !important;
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
        background: #f8fafc;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }

    :global(.dark) .assign-all-section {
        background: #1e293b;
    }

    .assign-all-label {
        font-weight: 500;
        color: #374151;
        white-space: nowrap;
        flex: 1;
    }

    :global(.dark) .assign-all-label {
        color: #e5e7eb;
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
        color: #6b7280;
        margin: 0 0 0.5rem 0;
    }

    :global(.dark) .files-count {
        color: #9ca3af;
    }

    .file-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.625rem 0.75rem;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        position: relative;
    }

    :global(.dark) .file-row {
        background: #1f2937;
        border-color: #374151;
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
        color: #6b7280;
    }

    :global(.dark) .file-info :global(svg) {
        color: #9ca3af;
    }

    .brim-edit-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.25rem;
        border: none;
        background: transparent;
        color: #9ca3af;
        cursor: pointer;
        border-radius: 0.25rem;
        flex-shrink: 0;
    }
    .brim-edit-btn:hover {
        color: #1a4031;
        background: rgba(26, 64, 49, 0.1);
    }
    :global(.dark) .brim-edit-btn:hover {
        color: #a7f3d0;
        background: rgba(167, 243, 208, 0.1);
    }

    .file-row .file-name {
        font-size: 0.875rem;
        color: #374151;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
        min-width: 0;
    }

    :global(.dark) .file-row .file-name {
        color: #e5e7eb;
    }

    .file-size {
        font-size: 0.75rem;
        color: #9ca3af;
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

