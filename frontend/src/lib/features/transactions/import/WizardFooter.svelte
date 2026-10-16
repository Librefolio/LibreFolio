<!--
  WizardFooter — the footer of the import wizard: each step's Back, Continue and Import buttons, with what blocks them.

  Cut from ImportWizardModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {AlertTriangle, CheckCircle} from 'lucide-svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import type {AssetGroup} from '$lib/utils/assetGrouping';
    import type {FileSelection, PendingFileEntry, StepId} from './wizardTypes';
    import type {ParseUnit, SelectedFileLike} from '$lib/features/transactions/import/importReportSets';

    interface Props {
        assetGroups: AssetGroup[];
        brokersLoading: boolean;
        candidatesRefreshing: boolean;
        currentStepId: StepId;
        duplicateRecheckRunning: boolean;
        importPreparing: boolean;
        pendingFiles: PendingFileEntry[];
        selectedFiles: FileSelection[];
        step1Continuing: boolean;
        uploading: boolean;
        usingCachedResults: boolean;
        assetGroupOpenProposals: number;
        fixStepPendingCount: number;
        gapFixSelectedTotal: number;
        parseCompletedCount: number;
        parseDone: boolean;
        parseHasErrors: boolean;
        parseHasSuccess: boolean;
        parseParsing: boolean;
        parseTotalCount: number;
        parseUnits: ParseUnit[];
        resolverPartialCount: number;
        setBlockReason: 'partly-selected' | 'ungrouped' | 'incomplete' | null;
        step1CanProceed: boolean;
        step1HasUnassigned: boolean;
        step1ValidCount: number;
        step2CanParse: boolean;
        step3CanContinue: boolean;
        step4CanImport: boolean;
        step4HasUnresolvedSelected: boolean;
        step4SelectedCount: number;
        step4SelectedDuplicateCount: number;
        ungroupedFiles: SelectedFileLike[];
        clearAllPendingFiles: () => void;
        goBack: () => void;
        goNext: () => void;
        handleClose: () => void;
        handleGapFixContinue: () => void;
        handleImport: () => Promise<void>;
    }

    let {
        assetGroups,
        brokersLoading,
        candidatesRefreshing,
        currentStepId,
        duplicateRecheckRunning,
        importPreparing,
        pendingFiles,
        selectedFiles,
        step1Continuing,
        uploading,
        usingCachedResults,
        assetGroupOpenProposals,
        fixStepPendingCount,
        gapFixSelectedTotal,
        parseCompletedCount,
        parseDone,
        parseHasErrors,
        parseHasSuccess,
        parseParsing,
        parseTotalCount,
        parseUnits,
        resolverPartialCount,
        setBlockReason,
        step1CanProceed,
        step1HasUnassigned,
        step1ValidCount,
        step2CanParse,
        step3CanContinue,
        step4CanImport,
        step4HasUnresolvedSelected,
        step4SelectedCount,
        step4SelectedDuplicateCount,
        ungroupedFiles,
        clearAllPendingFiles,
        goBack,
        goNext,
        handleClose,
        handleGapFixContinue,
        handleImport,
    }: Props = $props();
</script>

<div class="flex items-center justify-between p-4 border-t border-lf-subtle">
    {#if currentStepId === 'upload'}
        <div class="flex items-center gap-1">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={handleClose}>
                {$t('common.cancel')}
            </button>
            {#if pendingFiles.length > 0 && step1HasUnassigned}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <AlertTriangle size={14} />
                    {$t('importWizard.brokerRequired')}
                </span>
            {:else if pendingFiles.length > 0 && step1ValidCount > 0}
                <span class="flex items-center gap-1 text-xs text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.allConfigured')}
                </span>
            {/if}
        </div>
        <div class="flex items-center gap-2">
            {#if pendingFiles.length > 0}
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={clearAllPendingFiles} data-testid="import-wizard-clear">
                    {$t('common.clear') || 'Clear'}
                </button>
            {/if}
            <button
                type="button"
                class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed"
                onclick={goNext}
                disabled={!step1CanProceed || uploading || step1Continuing || brokersLoading}
                data-testid="import-wizard-next"
                use:guideAnchor={'import.action.upload'}
            >
                {#if uploading || step1Continuing || brokersLoading}
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
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={goBack} data-testid="import-wizard-back">
                ◀ {$t('common.back')}
            </button>
            {#if setBlockReason !== null}
                <span class="flex items-center gap-1 text-xs text-lf-warning" data-testid="import-wizard-set-blocks" data-reason={setBlockReason} data-file-ids={setBlockReason === 'ungrouped' ? ungroupedFiles.map((file) => file.fileId).join(',') : undefined}>
                    <AlertTriangle size={14} />
                    {#if setBlockReason === 'partly-selected'}
                        {$t('importWizard.reportSet.partlySelectedBlocks')}
                    {:else if setBlockReason === 'ungrouped'}
                        {$t('importWizard.reportSet.ungroupedBlocks', {values: {files: ungroupedFiles.map((file) => file.fileName).join(', ')}})}
                    {:else}
                        {$t('importWizard.reportSet.incompleteBlocks')}
                    {/if}
                </span>
            {:else if selectedFiles.length > 0 && !step2CanParse}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <AlertTriangle size={14} />
                    {$t('importWizard.pluginRequired')}
                </span>
            {:else if step2CanParse}
                <span class="flex items-center gap-1 text-xs text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.allConfigured')}
                </span>
            {/if}
        </div>
        <button type="button" class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed" onclick={goNext} disabled={!step2CanParse} data-testid="import-wizard-parse" use:guideAnchor={'import.action.select'}>
            {$t('importWizard.parse', {values: {n: parseUnits.length}})} ▶
        </button>
    {:else if currentStepId === 'analyze'}
        <div class="flex items-center gap-1">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={goBack} data-testid="import-wizard-back">
                ◀ {$t('common.back')}
            </button>
            {#if parseParsing}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <LoadingSpinner size="sm" />
                    {$t('importWizard.parsingProgress', {values: {done: parseCompletedCount, total: parseTotalCount}})}
                </span>
            {:else if parseDone && parseHasErrors && !parseHasSuccess}
                <span class="flex items-center gap-1 text-xs text-lf-danger">
                    <AlertTriangle size={14} />
                    {$t('importWizard.parseCompleteWithErrors')}
                </span>
            {:else if parseDone && parseHasErrors}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <AlertTriangle size={14} />
                    {$t('importWizard.parseCompleteWithErrors')}
                </span>
            {:else if parseDone && parseHasSuccess}
                <span class="flex items-center gap-1 text-xs text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.parseComplete')}
                </span>
            {:else if usingCachedResults}
                <span class="flex items-center gap-1 text-xs text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.cachedResults')}
                </span>
            {/if}
        </div>
        <button
            type="button"
            class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed"
            onclick={goNext}
            disabled={!step3CanContinue || candidatesRefreshing || duplicateRecheckRunning}
            data-testid="import-wizard-continue"
            use:guideAnchor={'import.action.analyze'}
        >
            {$t('common.continue')} ▶
        </button>
        <!--
          The unification step had no footer branch of its own and fell through to the review
          one, which judges *transactions*: it announced "select at least one transaction" on a
          step that has none and disabled the only way forward.
        -->
    {:else if currentStepId === 'assets'}
        <div class="flex items-center gap-1">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={goBack} data-testid="import-wizard-back">
                ◀ {$t('common.back')}
            </button>
            {#if assetGroupOpenProposals > 0}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <AlertTriangle size={14} />
                    {$t('importWizard.assetUnify.openProposals', {values: {n: assetGroupOpenProposals}})}
                </span>
            {:else}
                <span class="flex items-center gap-1 text-xs text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.assetUnify.allSettled', {values: {n: assetGroups.length}})}
                </span>
            {/if}
        </div>
        <button
            type="button"
            class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50"
            onclick={goNext}
            disabled={assetGroupOpenProposals > 0 || candidatesRefreshing || duplicateRecheckRunning}
            data-testid="import-wizard-assets-continue"
            use:guideAnchor={'import.action.assets'}
        >
            {$t('common.continue')} ▶
        </button>
    {:else if currentStepId === 'fix'}
        <div class="flex items-center gap-1">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={goBack} data-testid="import-wizard-back">
                ◀ {$t('common.back')}
            </button>
            {#if fixStepPendingCount > 0}
                <span class="flex items-center gap-1 text-xs text-lf-danger">
                    <AlertTriangle size={14} />
                    {$t('importWizard.fixStep.pending', {values: {n: fixStepPendingCount}})}
                </span>
            {:else}
                <span class="flex items-center gap-1 text-xs text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.fixStep.allDone')}
                </span>
            {/if}
        </div>
        <button
            type="button"
            class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed"
            onclick={goNext}
            disabled={fixStepPendingCount > 0 || duplicateRecheckRunning || candidatesRefreshing}
            data-testid="import-wizard-fix-continue"
            use:guideAnchor={'import.action.fix'}
        >
            {#if duplicateRecheckRunning}
                <LoadingSpinner size="sm" />
            {:else}
                {$t('common.continue')} ▶
            {/if}
        </button>
    {:else if currentStepId === 'duplicates'}
        <div class="flex items-center gap-1">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={goBack} data-testid="import-wizard-back">
                ◀ {$t('common.back')}
            </button>
            {#if resolverPartialCount > 0}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <AlertTriangle size={14} />
                    {$t('importWizard.resolver.statusToVerify', {values: {n: resolverPartialCount}})}
                </span>
            {:else}
                <span class="flex items-center gap-1 text-xs text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.resolver.statusAllAuto')}
                </span>
            {/if}
        </div>
        <button
            type="button"
            class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50"
            onclick={goNext}
            disabled={candidatesRefreshing || duplicateRecheckRunning}
            data-testid="import-wizard-duplicates-continue"
            use:guideAnchor={'import.action.duplicates'}
        >
            {$t('common.continue')} ▶
        </button>
    {:else if currentStepId === 'gapFix'}
        <div class="flex items-center gap-2">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={goBack} data-testid="import-wizard-back">
                ◀ {$t('common.back')}
            </button>
            <span class="text-xs text-lf-secondary" data-testid="import-wizard-gapfix-count" data-count={gapFixSelectedTotal}>
                {$t('importWizard.reportSet.gapFix.selectedCount', {values: {n: gapFixSelectedTotal}})}
            </span>
        </div>
        <button type="button" class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50" onclick={handleGapFixContinue} disabled={importPreparing} data-testid="import-wizard-gapfix-continue" use:guideAnchor={'import.action.gapFix'}>
            {$t('common.continue')} ▶
        </button>
    {:else}
        <div class="flex items-center gap-1">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={goBack} data-testid="import-wizard-back">
                ◀ {$t('common.back')}
            </button>
            {#if step4HasUnresolvedSelected}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <AlertTriangle size={14} />
                    {$t('importWizard.importDisabledUnresolved') || 'Resolve all assets to import'}
                </span>
            {:else if step4SelectedCount === 0}
                <span class="flex items-center gap-1 text-xs text-lf-muted">
                    {$t('importWizard.importDisabledEmpty') || 'Select at least one transaction'}
                </span>
            {:else if step4SelectedDuplicateCount > 0}
                <span class="flex items-center gap-1 text-xs text-lf-warning">
                    <AlertTriangle size={14} />
                    {$t('importWizard.duplicatesSelected', {values: {n: step4SelectedDuplicateCount}})}
                </span>
            {/if}
        </div>
        <button type="button" class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed" onclick={handleImport} disabled={!step4CanImport} data-testid="import-wizard-import" use:guideAnchor={'import.action.review'}>
            {$t('importWizard.importToEditor', {values: {n: step4SelectedCount}})} ▶
        </button>
    {/if}
</div>
