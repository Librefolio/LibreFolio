<script lang="ts">
    import {untrack} from 'svelte';
    import {Activity, ArrowLeftRight, CalendarClock, CircleHelp, FileText, Landmark, LayoutDashboard, ListOrdered, Newspaper, Scale, TrendingUp, Wallet} from 'lucide-svelte';

    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';

    import type {PreparedAiExport} from './aiExportClipboard';
    import {findCompatibleAiExportSelection, selectionsForDomain, type AiExportCatalogCompatibilityResult} from './catalog/compatibility';
    import type {AiExportDetailLevel, AiExportDomain, AiExportSelectionId, AiExportSelectionKind} from './catalog/shared';
    import {AI_EXPORT_DETAIL_LEVELS, resolveDefaultDetailLevel} from './catalog/shared';
    import {
        AI_EXPORT_PERIOD_PRESETS,
        AI_EXPORT_PERIOD_UNITS,
        aiExportOptionsFingerprint,
        estimateAiExportTokenSeverity,
        normalizeAiExportPeriod,
        normalizeAiExportUserNotes,
        reconcileAiExportOptions,
        formatAiExportByteSize,
        formatAiExportTokenCount,
        type AiExportOptionsPanelLabels,
        type AiExportOptionsSelection,
        type AiExportPeriodPreset,
        type AiExportPeriodUnit,
    } from './aiExportOptions';

    interface Props {
        domain: AiExportDomain;
        compatibility: AiExportCatalogCompatibilityResult;
        initialOptions: AiExportOptionsSelection;
        initialUserNotes?: string;
        responseLanguage: AiExportOptionsSelection['responseLanguage'];
        pending?: PreparedAiExport;
        disabled?: boolean;
        loading?: boolean;
        locale: string;
        labels: AiExportOptionsPanelLabels;
        onprepare: (options: AiExportOptionsSelection) => void;
        oncopyanyway: () => void;
        onusecompact: (options: AiExportOptionsSelection) => void;
        ondraftchange?: (options: AiExportOptionsSelection, userNotesDraft: string) => void;
    }

    let {domain, compatibility, initialOptions, initialUserNotes, responseLanguage, pending, disabled = false, loading = false, locale, labels, onprepare, oncopyanyway, onusecompact, ondraftchange}: Props = $props();

    const componentId = $props.id();
    const selectionKinds = ['dataset', 'analysis'] as const;
    const notesId = `${componentId}-notes`;
    const iconComponents = {
        activity: Activity,
        'arrow-left-right': ArrowLeftRight,
        'calendar-clock': CalendarClock,
        landmark: Landmark,
        'layout-dashboard': LayoutDashboard,
        'list-ordered': ListOrdered,
        newspaper: Newspaper,
        scale: Scale,
        'trending-up': TrendingUp,
        wallet: Wallet,
    } as const;
    const initial = untrack(() => reconcileAiExportOptions(compatibility, domain, initialOptions));
    let selectionKind = $state<AiExportSelectionKind>(initial.selectionKind);
    let selectionId = $state<AiExportSelectionId>(initial.selectionId);
    let detailLevel = $state<AiExportDetailLevel>(initial.detailLevel);
    let periodPreset = $state<AiExportPeriodPreset>(initial.period.preset);
    let customAmount = $state(initial.period.customAmount);
    let customUnit = $state<AiExportPeriodUnit>(initial.period.customUnit);
    let userNotes = $state(untrack(() => initialUserNotes ?? initialOptions.userNotes ?? ''));

    let selections = $derived(selectionsForDomain(compatibility, domain, selectionKind));
    let selectionOptions = $derived<SelectOption[]>(
        selections.map((selection) => ({
            value: selection.id,
            label: labels.selectionLabels[selection.id] ?? selection.id,
            searchText: labels.selectionDescriptions[selection.id] ?? '',
            icon: selection.entry.icon,
        })),
    );
    let selected = $derived(findCompatibleAiExportSelection(compatibility, selectionKind, selectionId));
    let currentOptions = $derived<AiExportOptionsSelection>(
        reconcileAiExportOptions(compatibility, domain, {
            selectionKind,
            selectionId,
            detailLevel,
            period: normalizeAiExportPeriod({preset: periodPreset, customAmount, customUnit}),
            responseLanguage,
            userNotes: selected?.entry.kind === 'analysis' && selected.entry.supports_user_notes ? normalizeAiExportUserNotes(selectionKind, userNotes) : undefined,
        }),
    );
    let controlsDisabled = $derived(disabled || loading);
    let severity = $derived(pending ? estimateAiExportTokenSeverity(pending.stats.finalPrompt.estimatedTokens) : null);
    let warningVisible = $derived(pending !== undefined && severity !== null && severity !== 'normal');

    $effect(() => {
        const domainSelections = selections;
        if (!domainSelections.some((selection) => selection.id === selectionId)) {
            const fallback = domainSelections[0];
            if (fallback) {
                selectionId = fallback.id;
                detailLevel = resolveDefaultDetailLevel(fallback.supportedDetailLevels);
            }
        }
    });

    $effect(() => {
        const option = selected;
        if (option && !option.supportedDetailLevels.includes(detailLevel)) detailLevel = option.supportedDetailLevels[0];
    });

    $effect(() => {
        const draft = currentOptions;
        const notesDraft = userNotes;
        untrack(() => ondraftchange?.(draft, notesDraft));
    });

    function setCategory(kind: AiExportSelectionKind) {
        selectionKind = kind;
        const first = selectionsForDomain(compatibility, domain, kind)[0];
        if (first) {
            selectionId = first.id;
            detailLevel = resolveDefaultDetailLevel(first.supportedDetailLevels);
        }
    }

    function handleSelection(value: string) {
        const match = selections.find((selection) => selection.id === value);
        if (match) selectionId = match.id;
    }

    function isAiExportIconName(value: string): value is keyof typeof iconComponents {
        return value in iconComponents;
    }

    function getSelectionIcon(icon: string | undefined) {
        return icon && isAiExportIconName(icon) ? iconComponents[icon] : FileText;
    }

    function isPeriodPreset(value: string): value is AiExportPeriodPreset {
        return AI_EXPORT_PERIOD_PRESETS.includes(value as AiExportPeriodPreset);
    }

    function isPeriodUnit(value: string): value is AiExportPeriodUnit {
        return AI_EXPORT_PERIOD_UNITS.includes(value as AiExportPeriodUnit);
    }

    function severityClasses(value: 'normal' | 'warning' | 'large'): string {
        if (value === 'large') return 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950/40';
        if (value === 'warning') return 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40';
        return 'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40';
    }

    function submit(event: SubmitEvent) {
        event.preventDefault();
        if (!controlsDisabled && selected) onprepare(currentOptions);
    }
</script>

<form class="flex flex-col gap-4 p-4" onsubmit={submit} data-testid="ai-export-options-panel">
    <fieldset class="flex flex-col gap-2">
        <legend class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.categoryLabel}</legend>
        <div class="grid grid-cols-2 gap-1 rounded-lg bg-gray-100 p-1 dark:bg-slate-900">
            {#each selectionKinds as kind}
                <button
                    type="button"
                    disabled={controlsDisabled}
                    aria-pressed={selectionKind === kind}
                    class="rounded-md px-2 py-1.5 text-xs font-medium transition-colors {selectionKind === kind ? 'bg-white text-purple-700 shadow-sm dark:bg-slate-700 dark:text-purple-300' : 'text-gray-600 dark:text-gray-300'}"
                    onclick={() => setCategory(kind)}
                    data-testid={`ai-export-category-${kind}`}
                >
                    {labels.categoryLabels[kind]}
                </button>
            {/each}
        </div>
        <p class="text-[11px] leading-4 text-gray-500 dark:text-gray-400" data-testid="ai-export-category-help">{labels.categoryHelp[selectionKind]}</p>
    </fieldset>

    <div class="flex flex-col gap-1.5">
        <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.selectionLabel}</span>
        <SimpleSelect
            value={selectionId}
            options={selectionOptions}
            disabled={controlsDisabled}
            dropdownPosition="auto"
            testId="ai-export-selection"
            ariaLabel={labels.selectionLabel}
            optionTestId={(option) => `ai-export-selection-option-${option.value}`}
            onchange={handleSelection}
            matchTriggerWidth
        >
            {#snippet selectedItem(option)}
                {@const SelectionIcon = getSelectionIcon(option.icon)}
                <span class="flex min-w-0 flex-1 items-center gap-2.5">
                    <SelectionIcon class="shrink-0 text-purple-600 dark:text-purple-300" size={18} aria-hidden="true" data-testid="ai-export-selection-selected-icon" />
                    <span class="min-w-0 flex-1">
                        <span class="block truncate font-medium">{option.label}</span>
                        <span class="block truncate text-[11px] text-gray-500 dark:text-gray-400">{option.searchText}</span>
                    </span>
                </span>
            {/snippet}
            {#snippet item(option)}
                {@const SelectionIcon = getSelectionIcon(option.icon)}
                <span class="flex min-w-0 items-start gap-2.5 whitespace-normal">
                    <SelectionIcon class="mt-0.5 shrink-0 text-purple-600 dark:text-purple-300" size={18} aria-hidden="true" data-testid={`ai-export-selection-option-${option.value}-icon`} />
                    <span class="min-w-0 flex-1">
                        <span class="block font-medium">{option.label}</span>
                        <span class="block whitespace-normal break-words text-xs leading-4 text-gray-500 dark:text-gray-400" data-testid={`ai-export-selection-option-${option.value}-description`}>{option.searchText}</span>
                    </span>
                </span>
            {/snippet}
        </SimpleSelect>
    </div>

    <fieldset class="flex flex-col gap-2">
        <legend class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.detailLevelLabel}</legend>
        <div class="grid grid-cols-3 gap-1 rounded-lg bg-gray-100 p-1 dark:bg-slate-900">
            {#each AI_EXPORT_DETAIL_LEVELS as detail}
                <div class="relative">
                    <button
                        type="button"
                        disabled={controlsDisabled || !selected?.supportedDetailLevels.includes(detail)}
                        aria-pressed={detailLevel === detail}
                        class="w-full rounded-md py-1.5 pr-6 pl-2 text-xs font-medium {detailLevel === detail ? 'bg-white text-purple-700 shadow-sm dark:bg-slate-700 dark:text-purple-300' : 'text-gray-600 dark:text-gray-300'}"
                        onclick={() => (detailLevel = detail)}
                        data-testid={`ai-export-detail-${detail}`}
                    >
                        {labels.detailLevelLabels[detail]}
                    </button>
                    <span class="absolute top-1/2 right-1 -translate-y-1/2">
                        <Tooltip text={labels.detailLevelHelp[detail]} position="right" maxWidth="320px" interactiveChild>
                            <button type="button" aria-label={`${labels.detailLevelLabels[detail]}: ${labels.detailLevelHelp[detail]}`} class="rounded-sm p-0.5 text-gray-400" data-testid={`ai-export-detail-help-${detail}`}>
                                <CircleHelp size={13} aria-hidden="true" />
                            </button>
                        </Tooltip>
                    </span>
                </div>
            {/each}
        </div>
    </fieldset>

    <fieldset class="flex flex-col gap-2">
        <div class="flex items-center gap-1.5">
            <legend class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.periodLabel}</legend>
            <Tooltip text={labels.periodHelp} position="right" maxWidth="320px" interactiveChild>
                <button type="button" aria-label={`${labels.periodLabel}: ${labels.periodHelp}`} class="rounded-sm p-0.5 text-gray-400" data-testid="ai-export-period-help"><CircleHelp size={13} /></button>
            </Tooltip>
        </div>
        <div class="flex min-w-0 items-center gap-1 rounded-lg bg-gray-100 p-1 dark:bg-slate-900">
            {#each AI_EXPORT_PERIOD_PRESETS.filter((preset) => preset !== 'custom') as preset}
                <button
                    type="button"
                    disabled={controlsDisabled}
                    aria-pressed={periodPreset === preset}
                    class="min-w-0 flex-1 rounded-md px-1 py-1.5 text-xs font-medium {periodPreset === preset ? 'bg-white text-purple-700 shadow-sm dark:bg-slate-700 dark:text-purple-300' : 'text-gray-600 dark:text-gray-300'}"
                    onclick={() => isPeriodPreset(preset) && (periodPreset = preset)}
                    data-testid={`ai-export-period-${preset}`}>{labels.periodPresetLabels[preset]}</button
                >
            {/each}
            {#if periodPreset === 'custom'}
                <div class="inline-flex shrink-0 items-center gap-0.5 rounded-md border border-purple-400/40 bg-purple-500/10 px-1.5 py-0.5" data-testid="ai-export-period-custom">
                    <input type="number" min="1" max="999" step="1" bind:value={customAmount} disabled={controlsDisabled} class="w-8 appearance-none bg-transparent text-center text-xs outline-none" data-testid="ai-export-period-custom-amount" />
                    <SimpleSelect
                        value={customUnit}
                        options={AI_EXPORT_PERIOD_UNITS.map((unit) => ({value: unit, label: labels.periodUnitShortLabels[unit], searchText: labels.periodUnitLabels[unit]}))}
                        disabled={controlsDisabled}
                        onchange={(value) => isPeriodUnit(value) && (customUnit = value)}
                        compact
                        showChevron={false}
                        testId="ai-export-period-custom-unit"
                        ariaLabel={labels.periodPresetLabels.custom}
                    />
                </div>
            {:else}
                <button type="button" disabled={controlsDisabled} class="min-w-0 flex-1 rounded-md px-1 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300" onclick={() => (periodPreset = 'custom')} data-testid="ai-export-period-custom">{labels.periodPresetLabels.custom}</button>
            {/if}
        </div>
    </fieldset>

    {#if selectionKind === 'analysis' && selected?.entry.kind === 'analysis' && selected.entry.supports_user_notes}
        <div class="flex flex-col gap-1.5">
            <label for={notesId} class="text-xs font-semibold text-gray-700 dark:text-gray-200">{labels.userNotesLabel}</label>
            <textarea id={notesId} bind:value={userNotes} disabled={controlsDisabled} placeholder={labels.userNotesPlaceholder} rows="3" class="w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900" data-testid="ai-export-user-notes"
            ></textarea>
        </div>
    {/if}

    {#if pending && severity}
        <section class="rounded-lg border border-gray-200 p-3 dark:border-slate-700" aria-live="polite" data-testid="ai-export-payload-stats">
            <h3 class="text-xs font-semibold">{labels.payloadStatsLabel}</h3>
            <p class="mt-1 text-[11px] leading-4 text-gray-500 dark:text-gray-400">{labels.payloadStatsHelp}</p>
            <p class="mt-2 text-sm font-semibold" data-testid="ai-export-final-size">
                {formatAiExportTokenCount(pending.stats.finalPrompt.estimatedTokens, locale, labels.tokenUnitLabel)}
                <span class="whitespace-nowrap">(<span aria-hidden="true">💾</span> {formatAiExportByteSize(pending.stats.finalPrompt.byteCountUtf8, locale)})</span>
            </p>
            <p class="mt-2 rounded-md px-2 py-1 text-xs font-medium {severityClasses(severity)}" data-testid="ai-export-token-severity">{labels.tokenSeverityLabels[severity]}</p>
            {#if warningVisible}
                <div class="mt-2 flex gap-2">
                    {#if currentOptions.detailLevel !== 'compact'}
                        <button type="button" class="flex-1 rounded-md border px-2 py-1.5 text-xs font-semibold" onclick={() => onusecompact({...currentOptions, detailLevel: 'compact'})} data-testid="ai-export-use-compact">{labels.useCompactLabel}</button>
                    {/if}
                    <button type="button" class="flex-1 rounded-md bg-purple-600 px-2 py-1.5 text-xs font-semibold text-white" onclick={oncopyanyway} data-testid="ai-export-copy-anyway">{labels.copyAnywayLabel}</button>
                </div>
            {/if}
        </section>
    {/if}

    <button type="submit" disabled={controlsDisabled || !selected} class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" data-testid="ai-export-copy-button">
        {loading ? labels.preparingLabel : labels.prepareLabel}
    </button>
</form>
