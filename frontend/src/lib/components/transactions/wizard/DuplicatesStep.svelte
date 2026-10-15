<!--
  DuplicatesStep — the duplicates step of the import wizard: the groups of rows that may be one transaction, and the file priority that settles them.

  Cut from ImportWizardModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Search, ChevronDown, ChevronRight, RefreshCw} from 'lucide-svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import type {DuplicateGroup, DuplicateTier, MergedTx} from '$lib/utils/transactions/importTypes';
    import type {ColumnDef} from '$lib/components/table/types';

    interface Props {
        duplicateFilePriorityIds: string[];
        duplicateGroups: DuplicateGroup[];
        duplicatePriorityWidth: number;
        duplicateRecheckError: string | null;
        duplicateResolverCollapsed: boolean;
        expandedDuplicateGroupKeys: Set<string>;
        expandedDuplicateTiers: Set<DuplicateTier>;
        resolverPartialCount: number;
        resolverTierPanels: {tier: DuplicateTier; groups: DuplicateGroup[]}[];
        duplicateSimilarityLabel: (tier: DuplicateTier) => string;
        duplicateTierBadgeClass: (tier: DuplicateTier) => string;
        getDuplicateGroupTitle: (group: DuplicateGroup) => string;
        getSourceFileName: (fileId: string) => string;
        marqueeDescendants: (node: HTMLElement) => {destroy: () => void};
        openLotCompare: (group: DuplicateGroup) => void;
        reapplyResolverGroups: () => void;
        recalcResolverDefaults: () => void;
        resetDuplicateResolverChoice: (group: DuplicateGroup) => void;
        resolverGroupMembers: (group: DuplicateGroup) => MergedTx[];
        resolverHasManualChoice: (group: DuplicateGroup) => boolean;
        resolverMemberColumns: (group: DuplicateGroup) => ColumnDef<MergedTx>[];
        startPriorityResize: (ev: PointerEvent) => void;
        toggleDuplicateGroup: (groupKey: string) => void;
        toggleDuplicateTier: (tier: DuplicateTier) => void;
    }

    let {
        duplicateFilePriorityIds = $bindable(),
        duplicateGroups,
        duplicatePriorityWidth,
        duplicateRecheckError,
        duplicateResolverCollapsed = $bindable(),
        expandedDuplicateGroupKeys,
        expandedDuplicateTiers,
        resolverPartialCount,
        resolverTierPanels,
        duplicateSimilarityLabel,
        duplicateTierBadgeClass,
        getDuplicateGroupTitle,
        getSourceFileName,
        marqueeDescendants,
        openLotCompare,
        reapplyResolverGroups,
        recalcResolverDefaults,
        resetDuplicateResolverChoice,
        resolverGroupMembers,
        resolverHasManualChoice,
        resolverMemberColumns,
        startPriorityResize,
        toggleDuplicateGroup,
        toggleDuplicateTier,
    }: Props = $props();
</script>

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
                            <button type="button" class="flex w-full items-center gap-2 bg-gray-50 px-3 py-2 text-left hover:bg-gray-100 dark:bg-slate-800/70 dark:hover:bg-slate-800" onclick={() => toggleDuplicateTier(panel.tier)} data-testid="import-wizard-resolver-tier-toggle-{panel.tier}">
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
