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
    import type {DuplicateGroup, DuplicateTier, MergedTx} from '$lib/features/transactions/import/importTypes';
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
        <section class="rounded-lg border border-lf-subtle bg-lf-panel/60" data-testid="import-wizard-duplicate-resolver">
            <button type="button" class="flex w-full items-center gap-2 border-lf-subtle px-3 py-2 text-left" class:border-b={!duplicateResolverCollapsed} onclick={() => (duplicateResolverCollapsed = !duplicateResolverCollapsed)} data-testid="import-wizard-duplicate-resolver-toggle">
                {#if duplicateResolverCollapsed}
                    <ChevronRight size={16} class="shrink-0 text-lf-muted" />
                {:else}
                    <ChevronDown size={16} class="shrink-0 text-lf-muted" />
                {/if}
                <div class="min-w-0 flex-1">
                    <h3 class="text-sm font-semibold text-lf-primary">{$t('importWizard.resolver.title')}</h3>
                    <p class="text-xs text-lf-muted">{$t('importWizard.resolver.subtitle', {values: {n: duplicateGroups.length}})}</p>
                </div>
                <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 {resolverPartialCount > 0 ? 'bg-lf-warning-soft text-lf-warning-on-soft ring-lf-warning-line' : 'bg-lf-success-soft text-lf-success-on-soft ring-lf-success-line'}" data-testid="import-wizard-resolver-status">
                    {resolverPartialCount > 0 ? $t('importWizard.resolver.statusToVerify', {values: {n: resolverPartialCount}}) : $t('importWizard.resolver.statusAllAuto')}
                </span>
            </button>

            <div class="min-w-0 gap-3 p-3 lg:grid-cols-[var(--priority-w)_minmax(0,1fr)] {duplicateResolverCollapsed ? 'hidden' : 'grid'}" style="--priority-w: {duplicatePriorityWidth}px">
                <div class="relative min-w-0 space-y-2 rounded-lg border border-lf-subtle bg-lf-card p-2" data-testid="import-wizard-file-priority">
                    <div class="text-xs font-semibold tracking-wide text-lf-muted uppercase">{$t('importWizard.resolver.filePriority')}</div>
                    <p class="text-xs text-lf-muted">{$t('importWizard.resolver.priorityPanelHint')}</p>
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
                                <span class="w-5 shrink-0 text-xs font-semibold text-lf-muted">{index + 1}</span>
                                <span use:scrollOnOverflow class="{overflowScrollTextClass} flex-1 text-xs text-lf-secondary" title={getSourceFileName(item)}>{getSourceFileName(item)}</span>
                            </div>
                        {/snippet}
                    </OrderableList>
                    <div class="flex justify-end">
                        <button type="button" class="inline-flex items-center gap-1 rounded-md border border-lf-input bg-lf-card px-2 py-1 text-xs font-medium text-lf-secondary hover:bg-lf-hover" onclick={recalcResolverDefaults} data-testid="import-wizard-resolver-recalc">
                            <RefreshCw size={13} />
                            {$t('importWizard.resolver.recalcDefaults')}
                        </button>
                    </div>
                    <!-- Drag handle: file names are long and unpredictable, so the split
                         between the priority list and the groups is the user's to make. -->
                    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                    <div role="separator" aria-orientation="vertical" class="absolute top-0 -right-2 hidden h-full w-2 cursor-col-resize touch-none lg:block" onpointerdown={startPriorityResize} data-testid="import-wizard-priority-resize">
                        <span class="absolute top-1/2 left-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded bg-lf-input"></span>
                    </div>
                </div>

                <div class="min-w-0 space-y-2">
                    {#each resolverTierPanels as panel (panel.tier)}
                        {@const tierOpen = expandedDuplicateTiers.has(panel.tier)}
                        <section class="min-w-0 overflow-hidden rounded-lg border border-lf-subtle" data-testid="import-wizard-resolver-tier-{panel.tier}">
                            <button type="button" class="flex w-full items-center gap-2 bg-lf-panel px-3 py-2 text-left hover:bg-lf-neutral" onclick={() => toggleDuplicateTier(panel.tier)} data-testid="import-wizard-resolver-tier-toggle-{panel.tier}">
                                {#if tierOpen}
                                    <ChevronDown size={14} class="shrink-0 text-lf-muted" />
                                {:else}
                                    <ChevronRight size={14} class="shrink-0 text-lf-muted" />
                                {/if}
                                <span class="min-w-0 flex-1 text-sm font-medium text-lf-primary">
                                    {panel.tier === 'sure' ? $t('importWizard.resolver.tierTotalTitle') : $t('importWizard.resolver.tierPartialTitle')}
                                </span>
                                <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 {duplicateTierBadgeClass(panel.tier)}">
                                    {$t('importWizard.resolver.groupCount', {values: {n: panel.groups.length}})}
                                </span>
                            </button>
                            {#if tierOpen}
                                <div class="min-w-0 space-y-2 border-t border-lf-subtle p-2">
                                    {#each panel.groups as group (group.key)}
                                        <div class="min-w-0 overflow-hidden rounded-lg border border-lf-subtle bg-lf-card" data-testid="import-wizard-duplicate-group">
                                            <button type="button" class="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-lf-hover" onclick={() => toggleDuplicateGroup(group.key)}>
                                                {#if expandedDuplicateGroupKeys.has(group.key)}
                                                    <ChevronDown size={14} class="shrink-0 text-lf-muted" />
                                                {:else}
                                                    <ChevronRight size={14} class="shrink-0 text-lf-muted" />
                                                {/if}
                                                <span use:scrollOnOverflow class="{overflowScrollTextClass} flex-1 text-sm font-medium text-lf-primary">{getDuplicateGroupTitle(group)}</span>
                                                <span class="shrink-0 rounded-full bg-lf-panel px-2 py-0.5 text-xs text-lf-secondary">{$t('importWizard.resolver.memberCount', {values: {n: group.memberIndices.length}})}</span>
                                                <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 {duplicateTierBadgeClass(group.tier)}" title={$t('importWizard.resolver.similarityTooltip')}>{duplicateSimilarityLabel(group.tier)}</span>
                                            </button>

                                            {#if expandedDuplicateGroupKeys.has(group.key)}
                                                <div class="min-w-0 border-t border-lf-subtle p-3">
                                                    <div class="mb-2 flex items-center justify-between gap-2">
                                                        <p class="text-xs text-lf-muted">{$t('importWizard.resolver.groupHelp')}</p>
                                                        <div class="flex shrink-0 items-center gap-3">
                                                            <button type="button" class="inline-flex items-center gap-1 text-xs text-lf-link hover:underline" onclick={() => openLotCompare(group)} data-testid="import-wizard-resolver-compare-{group.key}">
                                                                <Search size={13} />
                                                                {$t('importWizard.compareModal.openAction')}
                                                            </button>
                                                            {#if resolverHasManualChoice(group)}
                                                                <button type="button" class="text-xs text-lf-link hover:underline" onclick={() => resetDuplicateResolverChoice(group)} data-testid="import-wizard-resolver-reset">
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
