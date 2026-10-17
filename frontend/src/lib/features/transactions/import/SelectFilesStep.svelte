<!--
  SelectFilesStep — the second step of the import wizard: pick the files and the report sets to analyse, broker by broker.

  Cut from ImportWizardModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Trash2, Eye, ChevronDown, ChevronRight} from 'lucide-svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import ReportSetCard from '$lib/features/transactions/import/ReportSetCard.svelte';
    import {setSelectionState, type ParseUnit, type ReportSetGroup, type SetPluginInfo} from '$lib/features/transactions/import/importReportSets';
    import type {BrimFile} from '$lib/types';
    import type {BrokerInfo} from '$lib/stores/reference/brokerStore';
    import type {FileSelection, PendingFileEntry, SetPreviewEntry} from './wizardTypes';
    import type {ColumnDef} from '$lib/components/table/types';

    interface Props {
        brokerFilesLoading: boolean;
        brokerFilesMap: Map<number, BrimFile[]>;
        brokers: BrokerInfo[];
        expandedBrokers: Set<number>;
        expandedSets: Set<string>;
        pendingFiles: PendingFileEntry[];
        selectedFiles: FileSelection[];
        setPreviews: Map<string, SetPreviewEntry>;
        setUploadingRole: Map<string, string>;
        tableRefs: (DataTable<BrimFile> | undefined)[];
        uploading: boolean;
        allReportSets: ReportSetGroup[];
        brokerSetGroups: Map<number, {sets: ReportSetGroup[]; singles: BrimFile[]}>;
        parseUnits: ParseUnit[];
        selectedBrokerCount: number;
        selectedFileIdSet: Set<string>;
        selectedSetCount: number;
        setPluginInfos: SetPluginInfo[];
        setPreviewsLoading: boolean;
        fileTableColumns: ColumnDef<BrimFile>[];
        handleColumnResize: (sourceIdx: number, columnId: string, width: number) => void;
        handleSelectionChange: (brokerId: number, selectedIds: string[]) => void;
        isSetAnalysed: (set: ReportSetGroup) => boolean;
        openPreview: (fileId: string, callerZIndex?: number, highlightRows?: number[]) => Promise<void>;
        readFileAlone: (fileId: string, code: string) => void;
        readSetAs: (set: ReportSetGroup, code: string | null) => void;
        removeFileFromSet: (fileId: string) => void;
        requestDeleteFile: (file: BrimFile, brokerId: number) => void;
        toggleBrokerExpand: (brokerId: number) => void;
        toggleSetExpanded: (key: string) => void;
        toggleSetSelection: (set: ReportSetGroup) => void;
        uploadMissingIntoSet: (set: ReportSetGroup, roleCode: string, file: globalThis.File) => Promise<void>;
    }

    let {
        brokerFilesLoading,
        brokerFilesMap,
        brokers,
        expandedBrokers,
        expandedSets,
        pendingFiles,
        selectedFiles,
        setPreviews,
        setUploadingRole,
        tableRefs = $bindable(),
        uploading,
        allReportSets,
        brokerSetGroups,
        parseUnits,
        selectedBrokerCount,
        selectedFileIdSet,
        selectedSetCount,
        setPluginInfos,
        setPreviewsLoading,
        fileTableColumns,
        handleColumnResize,
        handleSelectionChange,
        isSetAnalysed,
        openPreview,
        readFileAlone,
        readSetAs,
        removeFileFromSet,
        requestDeleteFile,
        toggleBrokerExpand,
        toggleSetExpanded,
        toggleSetSelection,
        uploadMissingIntoSet,
    }: Props = $props();
</script>

<div class="space-y-4" data-testid="import-wizard-step2" data-busy={brokerFilesLoading || uploading || setPreviewsLoading || setUploadingRole.size > 0}>
    {#if brokerFilesLoading}
        <div class="py-8 text-center">
            <LoadingSpinner size="md" />
        </div>
    {:else}
        <!-- Header: selected count + column visibility -->
        <div class="flex items-center justify-between flex-wrap gap-2">
            <span class="text-sm font-medium text-lf-secondary">
                {#if allReportSets.length > 0}
                    {$t('importWizard.reportSet.selectedCount', {values: {sets: selectedSetCount, n: parseUnits.length - selectedSetCount, b: selectedBrokerCount}})}
                {:else}
                    {$t('importWizard.selectedCount', {values: {n: selectedFiles.length, b: selectedBrokerCount}})}
                {/if}
            </span>
            <div class="flex items-center gap-2">
                <ColumnVisibilityToggle tableRef={tableRefs.find((table) => table != null)} additionalTableRefs={tableRefs.filter((table) => table != null).slice(1)} />
            </div>
        </div>

        <!-- Pre-selected hint -->
        {#if pendingFiles.some((f) => f.status === 'uploaded')}
            <p class="text-xs text-lf-link italic">{$t('importWizard.preSelectedHint')}</p>
        {/if}

        <!-- Broker panels with DataTable -->
        {#each brokers as broker, brokerIdx}
            {@const brokerFiles = brokerFilesMap.get(broker.id) ?? []}
            {@const brokerGroups = brokerSetGroups.get(broker.id) ?? {sets: [], singles: brokerFiles}}
            {#if brokerFiles.length > 0}
                <div class="rounded-lg border border-lf-subtle overflow-hidden" data-testid={`import-wizard-broker-files-${broker.id}`}>
                    <!-- Broker header (collapsible) -->
                    <button type="button" class="w-full flex items-center gap-2 px-3 py-2.5 bg-lf-panel hover:bg-lf-neutral text-left" onclick={() => toggleBrokerExpand(broker.id)} aria-expanded={expandedBrokers.has(broker.id)} data-testid={`import-wizard-broker-toggle-${broker.id}`}>
                        {#if expandedBrokers.has(broker.id)}
                            <ChevronDown size={14} class="text-lf-muted" />
                        {:else}
                            <ChevronRight size={14} class="text-lf-muted" />
                        {/if}
                        <BrokerIcon brokerId={broker.id} iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size="sm" />
                        <span class="font-medium text-sm text-lf-primary">{broker.name}</span>
                        {#if selectedFiles.filter((f) => f.brokerId === broker.id).length > 0}
                            <span class="text-xs font-medium text-lf-link ml-1">({selectedFiles.filter((f) => f.brokerId === broker.id).length})</span>
                        {/if}
                        <span class="text-xs text-lf-muted ml-auto">
                            {#if brokerGroups.sets.length > 0}{$t('importWizard.reportSet.setCount', {values: {n: brokerGroups.sets.length}})} ·{/if}
                            {brokerGroups.singles.length + brokerGroups.sets.reduce((total, set) => total + set.files.length, 0)} file(s)
                        </span>
                    </button>

                    <!-- Report sets, one card each; the single files stay in the table -->
                    {#if expandedBrokers.has(broker.id) && brokerGroups.sets.length > 0}
                        <div class="space-y-2 border-t border-lf-subtle p-2" data-testid={`import-wizard-broker-sets-${broker.id}`}>
                            {#each brokerGroups.sets as set (set.key)}
                                <ReportSetCard
                                    {set}
                                    plugin={setPluginInfos.find((p) => p.code === set.pluginCode) ?? null}
                                    previewState={setPreviews.get(set.key)}
                                    selection={setSelectionState(set, selectedFileIdSet)}
                                    expanded={expandedSets.has(set.key)}
                                    analysed={isSetAnalysed(set)}
                                    uploadingRole={setUploadingRole.get(set.key) ?? null}
                                    onToggleSelected={() => toggleSetSelection(set)}
                                    onToggleExpanded={() => toggleSetExpanded(set.key)}
                                    onUploadMissing={(roleCode, file) => void uploadMissingIntoSet(set, roleCode, file)}
                                    onPreviewFile={(fileId) => openPreview(fileId)}
                                    onDeleteFile={(file) => requestDeleteFile(file as BrimFile, broker.id)}
                                    plugins={setPluginInfos}
                                    brokerDefaultPlugin={broker.default_import_plugin ?? null}
                                    onReadAs={(code) => readSetAs(set, code)}
                                    onReadAlone={(fileId, code) => readFileAlone(fileId, code)}
                                    onRemoveFromSet={(fileId) => removeFileFromSet(fileId)}
                                />
                            {/each}
                        </div>
                    {/if}

                    <!-- DataTable per broker: the single files -->
                    {#if expandedBrokers.has(broker.id) && brokerGroups.singles.length > 0}
                        <div class="border-t border-lf-subtle">
                            {#if brokerGroups.sets.length > 0}
                                <p class="px-3 pt-2 text-xs font-medium text-lf-secondary" data-testid={`import-wizard-other-files-${broker.id}`}>{$t('importWizard.reportSet.otherFiles')}</p>
                            {/if}
                            <!-- The table reads the selection only when it mounts (initialSelectedIds), so it is
                                 remounted whenever a file joins or leaves it: a file that arrives from a set keeps
                                 its tick, and the next click on another row cannot drop it (step H). -->
                            {#key brokerGroups.singles.map((file) => file.file_id).join(',')}
                                <DataTable
                                    bind:this={tableRefs[brokerIdx]}
                                    data={brokerGroups.singles}
                                    columns={fileTableColumns}
                                    getRowId={(row) => row.file_id}
                                    storageKey={`import-wizard-files-${broker.id}`}
                                    enableSelection={true}
                                    selectionMode="multi"
                                    initialSelectedIds={selectedFiles.filter((f) => f.brokerId === broker.id && brokerGroups.singles.some((single) => single.file_id === f.fileId)).map((f) => f.fileId)}
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
                                    enablePagination={brokerGroups.singles.length > 5}
                                    alwaysShowPagination={brokerGroups.singles.length > 5}
                                    enableColumnVisibility={false}
                                    defaultPageSize={5}
                                    pageSizeOptions={[5, 10, 25, 50, 100, 0]}
                                    tableLayout="auto"
                                    stickyActions={false}
                                    enableContextMenu={true}
                                    initialFilters={undefined}
                                    onColumnResize={(colId, w) => handleColumnResize(brokerIdx, colId, w)}
                                />
                            {/key}
                        </div>
                    {/if}
                </div>
            {/if}
        {/each}

        <!-- No files at all -->
        {#if brokers.every((b) => (brokerFilesMap.get(b.id) ?? []).length === 0)}
            <div class="py-8 text-center text-sm text-lf-muted">
                <p>{$t('importWizard.noFiles')}</p>
                <p class="text-xs mt-1">{$t('importWizard.noFilesHint')}</p>
            </div>
        {/if}
    {/if}
</div>
