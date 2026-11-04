<!--
  UploadStep — the first step of the import wizard: drop the files and assign each a broker.

  Cut from ImportWizardModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Trash2, AlertTriangle, Plus} from 'lucide-svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {BrokerSearchSelect} from '$lib/components/ui/select';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import type {BrokerInfo} from '$lib/stores/reference/brokerStore';
    import type {PendingFileEntry, Step1SetWarning} from './wizardTypes';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';

    interface Props {
        brokers: BrokerInfo[];
        brokersLoading: boolean;
        createBrokerContext: 'global' | string | null;
        createBrokerOpen: boolean;
        dropZoneContainerRef: HTMLDivElement | undefined;
        dropZoneExpanded: boolean;
        fileUploaderRef: FileUploader | undefined;
        globalBrokerId: number | null;
        pendingFiles: PendingFileEntry[];
        step1SelectedIds: string[];
        step1SetWarnings: Step1SetWarning[];
        step1TableRef: DataTable<PendingFileEntry> | undefined;
        uploadError: string | null;
        uploading: boolean;
        pendingFileActions: RowAction<PendingFileEntry>[];
        pendingFileColumns: ColumnDef<PendingFileEntry>[];
        formatSetDay: (iso: string | null | undefined) => string;
        handleFilesChanged: (event: CustomEvent<{files: globalThis.File[]}>) => void;
        onGlobalBrokerChange: (brokerId: number | null) => void;
        removePendingFilesByIds: (ids: string[]) => void;
    }

    let {
        brokers,
        brokersLoading,
        createBrokerContext = $bindable(),
        createBrokerOpen = $bindable(),
        dropZoneContainerRef = $bindable(),
        dropZoneExpanded = $bindable(),
        fileUploaderRef = $bindable(),
        globalBrokerId,
        pendingFiles,
        step1SelectedIds = $bindable(),
        step1SetWarnings,
        step1TableRef = $bindable(),
        uploadError = $bindable(),
        uploading,
        pendingFileActions,
        pendingFileColumns,
        formatSetDay,
        handleFilesChanged,
        onGlobalBrokerChange,
        removePendingFilesByIds,
    }: Props = $props();
</script>

<div class="space-y-4" data-testid="import-wizard-step1" data-busy={brokersLoading || uploading}>
    <!-- Info hint -->
    <p class="text-xs text-lf-muted italic">{$t('importWizard.step1Optional')}</p>

    <!-- Upload error banner -->
    {#if uploadError}
        <InfoBanner variant="error" message={uploadError} dismissible ondismiss={() => (uploadError = null)} />
    {/if}

    <!-- A report set this upload left incomplete: the missing export dropped here joins the same set -->
    {#each step1SetWarnings as warning (warning.key)}
        <div class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="import-wizard-step1-set-warning" data-plugin-code={warning.pluginCode} data-role={warning.roleCode}>
            <AlertTriangle size={16} class="mt-0.5 shrink-0" />
            <div class="space-y-1">
                <p>{$t('importWizard.reportSet.step1Missing', {values: {plugin: warning.pluginName, role: warning.roleLabel, ext: warning.extensions}})}</p>
                {#if warning.start && warning.end}
                    <p>{$t('importWizard.reportSet.missingPeriod', {values: {start: formatSetDay(warning.start), end: formatSetDay(warning.end)}})}</p>
                {/if}
                <p class="text-xs">
                    {$t('importWizard.reportSet.step1MissingHint')}
                    {#if warning.docsUrl}
                        <a class="ml-1 text-lf-link hover:underline" href={warning.docsUrl} target="_blank" rel="noopener noreferrer">{$t('importWizard.reportSet.howToExport')}</a>
                    {/if}
                </p>
            </div>
        </div>
    {/each}

    <!-- T2: Collapsible drop zone -->
    {#if dropZoneExpanded}
        <div bind:this={dropZoneContainerRef}>
            <FileUploader bind:this={fileUploaderRef} on:change={handleFilesChanged} on:error={(e) => (uploadError = e.detail.message)} multiple={true} accept=".csv,.xlsx,.xls" hideActions={true} />
        </div>
    {:else}
        <button
            type="button"
            class="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg border border-dashed border-lf-input text-sm text-lf-muted hover:border-lf-focus hover:text-lf-link transition-colors"
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
            <div class="flex items-center gap-3 p-3 bg-lf-panel rounded-lg">
                <span class="text-sm font-medium text-lf-secondary whitespace-nowrap">{$t('importWizard.globalBroker')}:</span>
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
