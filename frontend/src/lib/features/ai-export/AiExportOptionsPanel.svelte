<script lang="ts">
    import {untrack} from 'svelte';
    import {Activity, ArrowLeftRight, Briefcase, CalendarClock, Camera, ChartColumn, ChartNoAxesCombined, CircleHelp, Clock, Coins, FileText, Landmark, Layers, PieChart, PiggyBank, Receipt, Scale, TrendingUp} from 'lucide-svelte';

    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';

    import type {AiExportPromptStats, AiExportResponseLanguageDisplayName} from './templates/promptRenderer';
    import type {AiExportDetailLevel, AiExportDomain, AiExportRenderMode, AiExportTask, AiExportTaskDefinition, AiExportTaskIconName} from './catalog/shared';
    import type {AiExportCatalogCompatibilityResult} from './catalog/compatibility';
    import {
        AI_EXPORT_SNAPSHOT_SELECTION_ID,
        AI_EXPORT_DEFAULT_TECHNICAL_WINDOW,
        AI_EXPORT_TECHNICAL_WINDOW_PRESETS,
        AI_EXPORT_TECHNICAL_WINDOW_UNITS,
        aiExportOptionsFingerprint,
        estimateAiExportTokenSeverity,
        findCompatibleAiExportChoice,
        getAiExportAnalysisOptions,
        getAiExportDetailOptions,
        getAiExportTaskForAnalysisSelection,
        getInitialAiExportAnalysisSelection,
        getMatchingAiExportStats,
        isAiExportAnalysisSelection,
        isAiExportSnapshotSelection,
        normalizeAiExportPanelOptions,
        normalizeAiExportTechnicalWindow,
        reconcileAiExportAnalysisAndDetail,
        type AiExportAnalysisSelection,
        type AiExportHiddenAnalysisTasks,
        type AiExportOptionsPanelCallbackMetadata,
        type AiExportOptionsPanelLabels,
        type AiExportOptionsSelection,
        type AiExportTokenSeverity,
        type AiExportTechnicalWindowPreset,
        type AiExportTechnicalWindowSelection,
        type AiExportTechnicalWindowUnit,
    } from './aiExportOptions';

    const AI_EXPORT_ICON_COMPONENTS = {
        Activity,
        ArrowLeftRight,
        Briefcase,
        CalendarClock,
        Camera,
        ChartColumn,
        ChartNoAxesCombined,
        Clock,
        Coins,
        FileText,
        Landmark,
        Layers,
        PieChart,
        PiggyBank,
        Receipt,
        Scale,
        TrendingUp,
    } satisfies Record<AiExportTaskIconName, typeof Camera>;

    const AI_EXPORT_DOCS_PATHS = {
        portfolio: 'user/ai-export/portfolio/',
        broker: 'user/ai-export/broker/',
        asset: 'user/ai-export/asset/',
        fx: 'user/ai-export/fx/',
    } as const satisfies Readonly<Record<AiExportDomain, string>>;

    interface AiExportAnalysisPresentation {
        readonly selection: AiExportAnalysisSelection;
        readonly label: string;
        readonly description: string;
        readonly icon: AiExportTaskIconName;
    }

    interface Props {
        domainTaskDefinitions: readonly AiExportTaskDefinition[];
        compatibility: AiExportCatalogCompatibilityResult;
        initialTask: AiExportTask;
        initialDetailLevel: AiExportDetailLevel;
        initialRenderMode: AiExportRenderMode;
        initialTechnicalWindow?: AiExportTechnicalWindowSelection;
        responseLanguage: AiExportResponseLanguageDisplayName;
        initialUserNotes?: string;
        hiddenAnalysisTasks?: AiExportHiddenAnalysisTasks;
        lastStats?: AiExportPromptStats;
        lastStatsFingerprint?: string;
        disabled?: boolean;
        loading?: boolean;
        labels: AiExportOptionsPanelLabels;
        onexport: (options: AiExportOptionsSelection, metadata: AiExportOptionsPanelCallbackMetadata) => void;
        ondraftchange?: (options: AiExportOptionsSelection, metadata: AiExportOptionsPanelCallbackMetadata) => void;
    }

    let {
        domainTaskDefinitions,
        compatibility,
        initialTask,
        initialDetailLevel,
        initialRenderMode,
        initialTechnicalWindow = AI_EXPORT_DEFAULT_TECHNICAL_WINDOW,
        responseLanguage,
        initialUserNotes = '',
        hiddenAnalysisTasks = [],
        lastStats,
        lastStatsFingerprint,
        disabled = false,
        loading = false,
        labels,
        onexport,
        ondraftchange,
    }: Props = $props();

    const componentId = $props.id();
    const userNotesId = `${componentId}-notes`;
    const domain = untrack(() => {
        const firstDefinition = domainTaskDefinitions[0];
        if (!firstDefinition) throw new Error('AI Export options panel requires at least one task definition');
        return firstDefinition.domain;
    });
    const initialAnalysis = untrack(() => getInitialAiExportAnalysisSelection(initialTask, initialRenderMode));
    const initialReconciled = untrack(() => reconcileAiExportAnalysisAndDetail(domainTaskDefinitions, compatibility, domain, initialAnalysis, initialDetailLevel, hiddenAnalysisTasks));

    let selectedAnalysis = $state<AiExportAnalysisSelection>(initialReconciled.analysis);
    let selectedDetailLevel = $state<AiExportDetailLevel>(initialReconciled.detailLevel);
    let userNotes = $state(untrack(() => initialUserNotes));
    const normalizedInitialTechnicalWindow = untrack(() => normalizeAiExportTechnicalWindow(initialTechnicalWindow));
    let technicalWindowPreset = $state<AiExportTechnicalWindowPreset>(normalizedInitialTechnicalWindow.preset);
    let customTechnicalWindowAmount = $state(normalizedInitialTechnicalWindow.customAmount);
    let customTechnicalWindowUnit = $state<AiExportTechnicalWindowUnit>(normalizedInitialTechnicalWindow.customUnit);

    let analysisOptions = $derived(getAiExportAnalysisOptions(domainTaskDefinitions, compatibility, domain, hiddenAnalysisTasks));
    let analysisSelectOptions = $derived<SelectOption[]>(
        analysisOptions.map((option) => ({
            value: option.selection,
            label: isAiExportSnapshotSelection(option.selection) ? labels.snapshotLabel : (labels.taskLabels[option.definition.id] ?? option.definition.id),
            searchText: isAiExportSnapshotSelection(option.selection) ? labels.snapshotDescription : (labels.taskDescriptions[option.definition.id] ?? ''),
            disabled: option.disabled,
        })),
    );
    let technicalWindowUnitOptions = $derived<SelectOption[]>(
        AI_EXPORT_TECHNICAL_WINDOW_UNITS.map((unit) => ({
            value: unit,
            label: labels.technicalWindowUnitShortLabels[unit],
            searchText: labels.technicalWindowUnitLabels[unit],
        })),
    );
    let selectedTask = $derived(getAiExportTaskForAnalysisSelection(domain, selectedAnalysis));
    let selectedDefinition = $derived(domainTaskDefinitions.find((definition) => definition.domain === domain && definition.backendTask === selectedTask));
    let detailOptions = $derived(getAiExportDetailOptions(selectedDefinition, compatibility));
    let selectedChoice = $derived(selectedDefinition ? findCompatibleAiExportChoice(compatibility, selectedDefinition.domain, selectedDefinition.backendTask, selectedDetailLevel) : undefined);
    let snapshotSelected = $derived(isAiExportSnapshotSelection(selectedAnalysis));
    let controlsDisabled = $derived(disabled || loading);
    let technicalWindow = $derived(
        normalizeAiExportTechnicalWindow({
            preset: technicalWindowPreset,
            customAmount: customTechnicalWindowAmount,
            customUnit: customTechnicalWindowUnit,
        }),
    );
    let currentOptions = $derived<AiExportOptionsSelection>(
        normalizeAiExportPanelOptions({
            domain,
            analysis: selectedAnalysis,
            detailLevel: selectedDetailLevel,
            responseLanguage,
            userNotes,
            technicalWindow,
            taskDefinitions: domainTaskDefinitions,
        }),
    );
    let selectionCompatible = $derived(selectedChoice !== undefined && selectedDefinition !== undefined && selectedDefinition.renderModes.includes(currentOptions.renderMode));
    let exportDisabled = $derived(controlsDisabled || !selectionCompatible);
    let currentOptionsFingerprint = $derived(aiExportOptionsFingerprint(currentOptions));
    let currentStats = $derived(getMatchingAiExportStats(lastStats, lastStatsFingerprint, currentOptionsFingerprint));
    let tokenSeverity = $derived<AiExportTokenSeverity | null>(currentStats ? estimateAiExportTokenSeverity(currentStats.finalPrompt.estimatedTokens) : null);

    $effect(() => {
        const reconciled = reconcileAiExportAnalysisAndDetail(domainTaskDefinitions, compatibility, domain, selectedAnalysis, selectedDetailLevel, hiddenAnalysisTasks);
        if (reconciled.analysis !== selectedAnalysis) selectedAnalysis = reconciled.analysis;
        if (reconciled.detailLevel !== selectedDetailLevel) selectedDetailLevel = reconciled.detailLevel;
    });

    $effect(() => {
        const options = currentOptions;
        const metadata = {userNotesDraft: userNotes} satisfies AiExportOptionsPanelCallbackMetadata;
        untrack(() => ondraftchange?.(options, metadata));
    });

    function getAnalysisPresentation(value: string): AiExportAnalysisPresentation | undefined {
        if (!isAiExportAnalysisSelection(value, domainTaskDefinitions, hiddenAnalysisTasks)) return undefined;
        const option = analysisOptions.find((candidate) => candidate.selection === value);
        if (!option) return undefined;

        if (option.syntheticSnapshot) {
            return {
                selection: AI_EXPORT_SNAPSHOT_SELECTION_ID,
                label: labels.snapshotLabel,
                description: labels.snapshotDescription,
                icon: 'Camera',
            };
        }

        return {
            selection: option.selection,
            label: labels.taskLabels[option.definition.id] ?? option.definition.id,
            description: labels.taskDescriptions[option.definition.id] ?? '',
            icon: option.definition.icon,
        };
    }

    function handleAnalysisChange(value: string) {
        if (!isAiExportAnalysisSelection(value, domainTaskDefinitions, hiddenAnalysisTasks)) return;
        selectedAnalysis = value;
    }

    function isTechnicalWindowPreset(value: string): value is AiExportTechnicalWindowPreset {
        return AI_EXPORT_TECHNICAL_WINDOW_PRESETS.includes(value as AiExportTechnicalWindowPreset);
    }

    function isTechnicalWindowUnit(value: string): value is AiExportTechnicalWindowUnit {
        return AI_EXPORT_TECHNICAL_WINDOW_UNITS.includes(value as AiExportTechnicalWindowUnit);
    }

    function handleSubmit(event: SubmitEvent) {
        event.preventDefault();
        if (exportDisabled || !selectedDefinition) return;
        onexport(currentOptions, {userNotesDraft: userNotes});
    }

    function severityClasses(severity: AiExportTokenSeverity): string {
        if (severity === 'large') return 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950/40';
        if (severity === 'warning') return 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40';
        return 'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40';
    }
</script>

<form class="flex flex-col gap-4 p-4" onsubmit={handleSubmit} data-testid="ai-export-v2-options-panel">
    <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-3">
            <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.taskLabel}</span>
            <DocsLink path={AI_EXPORT_DOCS_PATHS[domain]} label={labels.documentationLabel} icon="book" size={16} testId="ai-export-v2-docs-link" />
        </div>
        <SimpleSelect value={selectedAnalysis} options={analysisSelectOptions} disabled={controlsDisabled} dropdownPosition="auto" testId="ai-export-v2-task-select" ariaLabel={labels.taskLabel} optionTestId={(option) => `ai-export-v2-task-option-${option.value}`} onchange={handleAnalysisChange}>
            {#snippet selectedItem(option)}
                {@const presentation = getAnalysisPresentation(option.value)}
                {#if presentation}
                    {@const TaskIcon = AI_EXPORT_ICON_COMPONENTS[presentation.icon]}
                    <div class="flex min-w-0 flex-1 items-center gap-2.5" data-testid="ai-export-v2-task-selected">
                        <TaskIcon class="shrink-0 text-purple-600 dark:text-purple-300" size={18} aria-hidden="true" data-testid="ai-export-v2-task-selected-icon" />
                        <span class="min-w-0 flex-1">
                            <span class="block truncate font-medium text-gray-900 dark:text-gray-100" data-testid="ai-export-v2-task-selected-name">{presentation.label}</span>
                            <span class="block truncate text-[11px] leading-4 text-gray-500 dark:text-gray-400" data-testid="ai-export-v2-task-selected-description">{presentation.description}</span>
                        </span>
                    </div>
                {/if}
            {/snippet}
            {#snippet item(option)}
                {@const presentation = getAnalysisPresentation(option.value)}
                {#if presentation}
                    {@const TaskIcon = AI_EXPORT_ICON_COMPONENTS[presentation.icon]}
                    <div class="flex w-full min-w-0 max-w-[calc(100vw-4rem)] items-start gap-2.5 sm:max-w-sm">
                        <TaskIcon class="mt-0.5 shrink-0 text-purple-600 dark:text-purple-300" size={18} aria-hidden="true" data-testid={`ai-export-v2-task-option-${presentation.selection}-icon`} />
                        <span class="min-w-0 flex-1 whitespace-normal">
                            <span class="block font-medium text-gray-900 dark:text-gray-100">{presentation.label}</span>
                            <span class="mt-0.5 block text-xs leading-snug text-gray-500 dark:text-gray-400">{presentation.description}</span>
                        </span>
                    </div>
                {/if}
            {/snippet}
        </SimpleSelect>
    </div>

    <fieldset class="flex flex-col gap-2">
        <legend class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.detailLevelLabel}</legend>
        <div class="grid grid-cols-3 gap-1 rounded-lg bg-gray-100 p-1 dark:bg-slate-900">
            {#each detailOptions as detailOption (detailOption.detailLevel)}
                <div class="relative min-w-0">
                    <button
                        type="button"
                        disabled={controlsDisabled || detailOption.disabled}
                        aria-pressed={selectedDetailLevel === detailOption.detailLevel}
                        class="w-full rounded-md py-1.5 pr-6 pl-2 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 {selectedDetailLevel === detailOption.detailLevel
                            ? 'bg-white text-purple-700 shadow-sm dark:bg-slate-700 dark:text-purple-300'
                            : 'text-gray-600 hover:bg-white/70 dark:text-gray-300 dark:hover:bg-slate-700/70'}"
                        onclick={() => (selectedDetailLevel = detailOption.detailLevel)}
                        data-testid={`ai-export-v2-detail-${detailOption.detailLevel}`}
                    >
                        {labels.detailLevelLabels[detailOption.detailLevel]}
                    </button>
                    <span class="absolute top-1/2 right-1 z-10 -translate-y-1/2">
                        <Tooltip text={labels.detailLevelHelp[detailOption.detailLevel]} position="right" maxWidth="320px" interactiveChild>
                            <button
                                type="button"
                                aria-label={`${labels.detailLevelLabels[detailOption.detailLevel]}: ${labels.detailLevelHelp[detailOption.detailLevel]}`}
                                class="inline-flex rounded-sm p-0.5 text-gray-400 transition-colors hover:text-purple-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 dark:text-gray-500 dark:hover:text-purple-300"
                                data-testid={`ai-export-v2-detail-help-${detailOption.detailLevel}`}
                            >
                                <CircleHelp size={13} aria-hidden="true" />
                            </button>
                        </Tooltip>
                    </span>
                </div>
            {/each}
        </div>
    </fieldset>

    <fieldset class="flex flex-col gap-2">
        <legend class="sr-only">{labels.technicalWindowLabel}</legend>
        <div class="flex items-center gap-1.5">
            <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.technicalWindowLabel}</span>
            <Tooltip text={labels.technicalWindowHelp} position="right" maxWidth="320px" interactiveChild>
                <button
                    type="button"
                    aria-label={`${labels.technicalWindowLabel}: ${labels.technicalWindowHelp}`}
                    class="inline-flex rounded-sm p-0.5 text-gray-400 transition-colors hover:text-purple-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 dark:text-gray-500 dark:hover:text-purple-300"
                    data-testid="ai-export-v2-technical-window-help"
                >
                    <CircleHelp size={13} aria-hidden="true" />
                </button>
            </Tooltip>
        </div>
        <div class="flex min-w-0 items-center gap-1 rounded-lg bg-gray-100 p-1 dark:bg-slate-900">
            {#each AI_EXPORT_TECHNICAL_WINDOW_PRESETS.filter((preset) => preset !== 'custom') as preset}
                <button
                    type="button"
                    disabled={controlsDisabled}
                    aria-pressed={technicalWindowPreset === preset}
                    class="min-w-0 flex-1 rounded-md px-1 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 {technicalWindowPreset === preset
                        ? 'bg-white text-purple-700 shadow-sm dark:bg-slate-700 dark:text-purple-300'
                        : 'text-gray-600 hover:bg-white/70 dark:text-gray-300 dark:hover:bg-slate-700/70'}"
                    onclick={() => {
                        if (isTechnicalWindowPreset(preset)) technicalWindowPreset = preset;
                    }}
                    data-testid={`ai-export-v2-technical-window-${preset}`}
                >
                    {labels.technicalWindowPresetLabels[preset]}
                </button>
            {/each}

            {#if technicalWindowPreset === 'custom'}
                <div class="inline-flex shrink-0 items-center gap-0.5 rounded-md border border-purple-400/40 bg-purple-500/10 px-1.5 py-0.5 dark:bg-purple-500/20" role="group" data-testid="ai-export-v2-technical-window-custom">
                    <input
                        type="number"
                        min="1"
                        max="999"
                        step="1"
                        bind:value={customTechnicalWindowAmount}
                        disabled={controlsDisabled}
                        aria-label={labels.technicalWindowPresetLabels.custom}
                        class="w-8 appearance-none border-none bg-transparent px-0.5 py-0.5 text-center text-xs text-purple-700 outline-none focus:ring-0 disabled:cursor-not-allowed disabled:opacity-50 dark:text-purple-300 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                        data-testid="ai-export-v2-technical-window-custom-amount"
                    />
                    <SimpleSelect
                        value={customTechnicalWindowUnit}
                        options={technicalWindowUnitOptions}
                        disabled={controlsDisabled}
                        onchange={(value) => {
                            if (isTechnicalWindowUnit(value)) customTechnicalWindowUnit = value;
                        }}
                        class="inline-block w-auto"
                        dropdownPosition="auto"
                        compact
                        showChevron={false}
                        testId="ai-export-v2-technical-window-custom-unit"
                        ariaLabel={labels.technicalWindowPresetLabels.custom}
                        optionTestId={(option) => `ai-export-v2-technical-window-custom-unit-option-${option.value}`}
                    />
                </div>
            {:else}
                <button
                    type="button"
                    disabled={controlsDisabled}
                    aria-pressed="false"
                    class="min-w-0 flex-1 rounded-md px-1 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-white/70 disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-300 dark:hover:bg-slate-700/70"
                    onclick={() => (technicalWindowPreset = 'custom')}
                    data-testid="ai-export-v2-technical-window-custom"
                >
                    {labels.technicalWindowPresetLabels.custom}
                </button>
            {/if}
        </div>
    </fieldset>

    {#if !snapshotSelected}
        {#if selectedDefinition?.supportsUserNotes}
            <div class="flex flex-col gap-1.5">
                <label for={userNotesId} class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.userNotesLabel}</label>
                <textarea
                    id={userNotesId}
                    bind:value={userNotes}
                    disabled={controlsDisabled}
                    placeholder={labels.userNotesPlaceholder}
                    rows="3"
                    class="w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-gray-100"
                    data-testid="ai-export-v2-user-notes"
                ></textarea>
            </div>
        {/if}
    {/if}

    {#if currentStats && tokenSeverity}
        <section class="rounded-lg border border-gray-200 p-3 dark:border-slate-700" aria-live="polite" data-testid="ai-export-v2-payload-stats">
            <h3 class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.payloadStatsLabel}</h3>
            <dl class="mt-2 grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
                <dt>{labels.backendEstimatedTokensLabel}</dt>
                <dd data-testid="ai-export-v2-backend-token-count">{currentStats.snapshotBackendStats.token_estimate.estimated_tokens}</dd>
                <dt>{labels.finalEstimatedTokensLabel}</dt>
                <dd data-testid="ai-export-v2-final-token-count">{currentStats.finalPrompt.estimatedTokens}</dd>
            </dl>
            <p class="mt-2 rounded-md px-2 py-1 text-xs font-medium {severityClasses(tokenSeverity)}" role="status" data-testid="ai-export-v2-token-severity">
                {labels.tokenSeverityLabels[tokenSeverity]}
            </p>
        </section>
    {/if}

    <button
        type="submit"
        disabled={exportDisabled}
        class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-slate-800"
        data-testid="ai-export-v2-export-button"
    >
        {loading ? labels.loadingLabel : labels.exportLabel}
    </button>
</form>
