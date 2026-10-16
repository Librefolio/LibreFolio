<!--
  ReviewStep — the review step of the import wizard: the rows to import, their assets and brokers, and what keeps a row out.

  Cut from ImportWizardModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ChevronDown, ChevronRight, Check, AlertTriangle, RefreshCw, CheckSquare, Square, ListChecks, Wand2, Pencil, Loader2} from 'lucide-svelte';
    import {getIndexColor} from '$lib/utils/colors';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import {duplicateCandidates} from '$lib/features/transactions/import/importResolutionHelpers';
    import type {AssetResolution, MergedTx} from '$lib/features/transactions/import/importTypes';
    import type {BrokerOpeningIssue} from './wizardTypes';
    import type {ColumnDef} from '$lib/components/table/types';

    interface Props {
        assetResolutions: AssetResolution[];
        autoFixingBrokerId: number | null;
        candidatesRefreshing: boolean;
        duplicateRecheckError: string | null;
        duplicateRecheckRunning: boolean;
        importPreparing: boolean;
        inspectAssetLoading: boolean;
        recheckingOpenings: boolean;
        showBeforeHistory: boolean;
        step4ShowResolveSection: boolean;
        step4TableRef: DataTable<MergedTx> | undefined;
        brokerOpeningIssues: BrokerOpeningIssue[];
        step4BeforeHistoryCount: number;
        step4BeforeOpeningCount: number;
        step4Columns: ColumnDef<MergedTx>[];
        step4DeselectDbDup: number;
        step4DeselectPendingDup: number;
        step4HasDeselectReasons: boolean;
        step4MissingAssetCount: number;
        step4Rows: MergedTx[];
        step4SelectedCount: number;
        step4SelectedDuplicateCount: number;
        step4TotalCount: number;
        step4UnresolvedCount: number;
        autoFixBrokerOpening: (issue: BrokerOpeningIssue) => Promise<void>;
        clearResolution: (fakeAssetId: number) => void;
        confidenceBadgeClass: (conf: string) => string;
        openAssetInspector: (assetId: number) => Promise<void>;
        openBrokerOpeningEditById: (brokerId: number) => Promise<void>;
        openMergeFromCard: (res: AssetResolution) => void;
        recheckOpenings: () => Promise<void>;
        resolveAssetManual: (fakeAssetId: number, realAssetId: number, res: AssetResolution) => Promise<void>;
        startCreateAsset: (res: AssetResolution) => void;
        step4DeselectAll: () => void;
        step4SelectAll: () => void;
        step4SelectVisible: () => void;
    }

    let {
        assetResolutions,
        autoFixingBrokerId,
        candidatesRefreshing,
        duplicateRecheckError,
        duplicateRecheckRunning,
        importPreparing,
        inspectAssetLoading,
        recheckingOpenings,
        showBeforeHistory = $bindable(),
        step4ShowResolveSection = $bindable(),
        step4TableRef = $bindable(),
        brokerOpeningIssues,
        step4BeforeHistoryCount,
        step4BeforeOpeningCount,
        step4Columns,
        step4DeselectDbDup,
        step4DeselectPendingDup,
        step4HasDeselectReasons,
        step4MissingAssetCount,
        step4Rows,
        step4SelectedCount,
        step4SelectedDuplicateCount,
        step4TotalCount,
        step4UnresolvedCount,
        autoFixBrokerOpening,
        clearResolution,
        confidenceBadgeClass,
        openAssetInspector,
        openBrokerOpeningEditById,
        openMergeFromCard,
        recheckOpenings,
        resolveAssetManual,
        startCreateAsset,
        step4DeselectAll,
        step4SelectAll,
        step4SelectVisible,
    }: Props = $props();
</script>

<div
    class="flex flex-col gap-4 h-full overflow-y-auto"
    data-testid="import-wizard-step4"
    data-busy={autoFixingBrokerId !== null || recheckingOpenings || candidatesRefreshing || duplicateRecheckRunning || importPreparing || inspectAssetLoading}
    aria-busy={autoFixingBrokerId !== null || recheckingOpenings || candidatesRefreshing || duplicateRecheckRunning || importPreparing || inspectAssetLoading}
    data-selected-count={step4SelectedCount}
    data-total-count={step4TotalCount}
>
    {#if duplicateRecheckError}
        <div data-testid="import-wizard-duplicate-recheck-error">
            <InfoBanner variant="error" message={$t('importWizard.duplicateRecheckFailed', {values: {error: duplicateRecheckError}})} />
        </div>
    {/if}
    <!-- ── Resolve Assets section ─────────────────────────── -->
    {#if assetResolutions.length > 0}
        <div class="border border-lf-subtle rounded-lg overflow-hidden" data-testid="import-wizard-resolve-section">
            <!-- Section header -->
            <button type="button" class="w-full flex items-center justify-between px-4 py-3 bg-lf-panel hover:bg-lf-neutral transition-colors" onclick={() => (step4ShowResolveSection = !step4ShowResolveSection)} data-testid="import-wizard-resolve-toggle">
                <div class="flex items-center gap-2">
                    {#if step4ShowResolveSection}<ChevronDown size={16} />{:else}<ChevronRight size={16} />{/if}
                    <span class="font-semibold text-sm">{$t('importWizard.resolveAssets')}</span>
                    {#if step4UnresolvedCount > 0}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-lf-warning-soft text-lf-warning-on-soft" data-testid="import-wizard-unresolved-count">
                            {$t('importWizard.unresolvedCount', {values: {n: step4UnresolvedCount}})}
                        </span>
                    {:else}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-lf-success-soft text-lf-success-on-soft">
                            <Check size={12} class="mr-1" />{$t('importWizard.allResolved')}
                        </span>
                    {/if}
                </div>
            </button>

            {#if step4MissingAssetCount > 0}
                <div class="px-3 pt-3" data-testid="import-wizard-manual-asset-help">
                    <InfoBanner variant="info">
                        <p class="font-semibold mb-1">{$t('importWizard.manualAssets.title')}</p>
                        <p>{$t('importWizard.manualAssets.body')}</p>
                    </InfoBanner>
                </div>
            {/if}

            {#if step4ShowResolveSection}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 p-3">
                    {#each assetResolutions as res (res.fakeAssetId)}
                        {@const isResolved = res.resolvedAssetId !== null}
                        <div class="border rounded-lg p-3 {isResolved ? 'border-lf-success-line bg-lf-success-soft/30' : 'border-lf-subtle'}">
                            <!-- Card header — name + badges on same flex-wrap row, TX count right -->
                            <div class="flex items-start justify-between gap-2 mb-1">
                                <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1 flex-1 min-w-0">
                                    <span class="font-semibold text-sm text-lf-primary truncate max-w-full">
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
                                <span class="shrink-0 text-xs font-medium text-lf-muted bg-lf-panel px-1.5 py-0.5 rounded whitespace-nowrap">
                                    {res.txCount} TX
                                </span>
                            </div>
                            <div class="text-xs text-lf-muted mb-3 truncate">{res.sourceFiles.join(', ')}</div>

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
                                <div class="mt-1.5 flex items-center gap-2 rounded border border-lf-warning-line bg-lf-warning-soft px-2 py-1.5" data-testid="import-wizard-duplicate-hint-{res.fakeAssetId}">
                                    <AlertTriangle size={13} class="shrink-0 text-lf-warning" />
                                    <span class="min-w-0 flex-1 text-[11px] text-lf-secondary">{$t('importWizard.duplicateAssetHint')}</span>
                                    <button type="button" class="shrink-0 rounded bg-lf-warning px-2 py-0.5 text-[11px] font-medium text-lf-on-status hover:bg-lf-warning-hover" onclick={() => openMergeFromCard(res)} data-testid="import-wizard-merge-assets-{res.fakeAssetId}">
                                        {$t('importWizard.duplicateAssetMerge')}
                                    </button>
                                </div>
                            {/if}
                            {#if res.resolvedAssetId !== null}
                                <button
                                    type="button"
                                    class="ml-auto mt-1.5 flex w-fit items-center gap-1 text-xs text-lf-muted hover:text-lf-link disabled:opacity-50"
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
                <div class="flex flex-col gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3">
                    <div class="flex min-w-0 flex-1 items-start gap-2 sm:items-center">
                        <AlertTriangle size={16} class="mt-0.5 shrink-0 text-lf-warning sm:mt-0" />
                        <div class="min-w-0">
                            <BrokerBadge broker={issue.broker} size={18} showName={true} />
                            <p class="mt-0.5 text-xs text-lf-secondary">
                                {$t('importWizard.brokerOpeningMsg', {values: {count: issue.count, openedAt: issue.openedAt, minDate: issue.minTxDate}})}
                            </p>
                        </div>
                    </div>
                    <div class="flex shrink-0 items-center gap-2">
                        <button
                            type="button"
                            class="flex items-center gap-1 rounded bg-lf-action px-2 py-1 text-xs font-medium text-lf-on-action hover:opacity-90 disabled:opacity-50"
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
                        <button type="button" class="flex items-center gap-1 rounded border border-lf-input px-2 py-1 text-xs hover:bg-lf-hover" onclick={() => void openBrokerOpeningEditById(issue.brokerId)} data-testid="broker-opening-edit-{issue.brokerId}">
                            <Pencil size={12} /><span>{$t('importWizard.status.editBrokerDate')}</span>
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    {/if}

    <!-- ── TX Table (DataTable) ───────────────────────────── -->
    <div class="border border-lf-subtle rounded-lg overflow-hidden">
        <!-- Toolbar row -->
        <div class="flex items-center justify-between px-4 py-2.5 bg-lf-panel border-b border-lf-subtle">
            <div class="flex items-center gap-3 text-sm">
                <span class="font-semibold">{$t('transactions.title')}</span>
                <span class="text-lf-muted">{step4SelectedCount} / {step4TotalCount}</span>
                {#if step4SelectedDuplicateCount > 0}
                    <Tooltip text={$t('importWizard.duplicatesSelectedTip')} position="top" maxWidth="320px" wrapperClass="inline-flex">
                        <span class="cursor-help text-xs text-lf-warning underline decoration-dotted">⚠ {$t('importWizard.duplicatesSelected', {values: {n: step4SelectedDuplicateCount}})}</span>
                    </Tooltip>
                {/if}
                {#if step4BeforeOpeningCount > 0}
                    <span class="text-xs text-lf-muted">⛔ {step4BeforeOpeningCount} {$t('importWizard.beforeOpeningCount')}</span>
                {/if}
                {#if step4BeforeHistoryCount > 0}
                    <span class="text-xs text-lf-muted" data-testid="import-wizard-before-history-count" data-count={step4BeforeHistoryCount}>⏮ {$t('importWizard.reportSet.beforeHistoryCount', {values: {n: step4BeforeHistoryCount}})}</span>
                    <button type="button" class="text-xs text-lf-link hover:underline" onclick={() => (showBeforeHistory = !showBeforeHistory)} aria-pressed={showBeforeHistory} data-testid="import-wizard-before-history-toggle">
                        {showBeforeHistory ? $t('importWizard.reportSet.hideBeforeHistory') : $t('importWizard.reportSet.showBeforeHistory')}
                    </button>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                {#if step4BeforeOpeningCount > 0}
                    <button type="button" class="text-xs text-lf-link hover:underline flex items-center gap-1 disabled:opacity-50" onclick={() => void recheckOpenings()} disabled={recheckingOpenings} data-testid="import-wizard-recheck-openings" title={$t('importWizard.recheckOpeningsTip')}>
                        <RefreshCw size={12} class={recheckingOpenings ? 'animate-spin' : ''} /><span class="hidden sm:inline">{$t('importWizard.recheckOpenings')}</span>
                    </button>
                    <span class="text-lf-muted">|</span>
                {/if}
                <button type="button" class="text-xs text-lf-link hover:underline flex items-center gap-1" onclick={step4SelectAll} data-testid="import-wizard-select-all">
                    <CheckSquare size={12} /><span class="hidden sm:inline">{$t('common.selectAll')}</span>
                </button>
                <span class="text-lf-muted">|</span>
                <button type="button" class="text-xs text-lf-link hover:underline flex items-center gap-1" onclick={step4SelectVisible} data-testid="import-wizard-select-visible" title={$t('importWizard.selectVisibleTip')}>
                    <ListChecks size={12} /><span class="hidden sm:inline">{$t('importWizard.selectVisible')}</span>
                </button>
                <span class="text-lf-muted">|</span>
                <button type="button" class="text-xs text-lf-muted hover:underline flex items-center gap-1" onclick={step4DeselectAll} data-testid="import-wizard-deselect-all">
                    <Square size={12} /><span class="hidden sm:inline">{$t('common.deselectAll')}</span>
                </button>
                <span class="text-lf-muted">|</span>
                <ColumnVisibilityToggle tableRef={step4TableRef} />
            </div>
        </div>

        {#if step4HasDeselectReasons}
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-lf-warning-line bg-lf-warning-soft px-4 py-2 text-xs text-lf-warning-on-soft" data-testid="import-wizard-deselect-banner">
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
            getRowClass={(mt) => `${!mt.selected ? 'opacity-50' : ''} ${mt.isDupKeeper ? 'bg-lf-success-soft/60' : ''}`.trim()}
            emptyMessage={$t('importWizard.noFiles')}
        />
    </div>
</div>
