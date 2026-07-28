import type {AiExportCatalogCompatibilityChoice, AiExportCatalogCompatibilityResult} from './catalog/compatibility';
import type {AiExportBackendCatalogEntry, AiExportDetailLevel, AiExportDomain, AiExportRenderMode, AiExportTask, AiExportTaskDefinition} from './catalog/shared';
import type {AiExportPromptStats, AiExportResponseLanguageDisplayName} from './templates/promptRenderer';

export const AI_EXPORT_TOKEN_WARNING_THRESHOLD = 8_000;
export const AI_EXPORT_TOKEN_LARGE_THRESHOLD = 16_000;
export const AI_EXPORT_SNAPSHOT_SELECTION_ID = 'snapshot' as const;
export const AI_EXPORT_TECHNICAL_WINDOW_PRESETS = ['3m', '6m', '1y', 'custom'] as const;
export const AI_EXPORT_TECHNICAL_WINDOW_UNITS = ['days', 'weeks', 'months', 'years'] as const;

export type AiExportAnalysisSelection = AiExportTask | typeof AI_EXPORT_SNAPSHOT_SELECTION_ID;
export type AiExportHiddenAnalysisTasks = readonly AiExportTask[];
export type AiExportTechnicalWindowPreset = (typeof AI_EXPORT_TECHNICAL_WINDOW_PRESETS)[number];
export type AiExportTechnicalWindowUnit = (typeof AI_EXPORT_TECHNICAL_WINDOW_UNITS)[number];

export interface AiExportTechnicalWindowSelection {
    readonly preset: AiExportTechnicalWindowPreset;
    readonly customAmount: number;
    readonly customUnit: AiExportTechnicalWindowUnit;
}

export const AI_EXPORT_DEFAULT_TECHNICAL_WINDOW = {
    preset: '3m',
    customAmount: 3,
    customUnit: 'months',
} as const satisfies AiExportTechnicalWindowSelection;

export const AI_EXPORT_SNAPSHOT_TASK_BY_DOMAIN = {
    portfolio: 'portfolio_description',
    asset: 'asset_snapshot',
    fx: 'fx_trend_review',
    broker: 'broker_review',
} as const satisfies Readonly<Record<AiExportDomain, AiExportTask>>;

export type AiExportTokenSeverity = 'normal' | 'warning' | 'large';

/**
 * UI-only classification of an already-rendered prompt. These thresholds never
 * truncate content or alter task, detail level, request payload, or prompt text.
 */
export function estimateAiExportTokenSeverity(finalEstimatedTokens: number): AiExportTokenSeverity {
    if (finalEstimatedTokens >= AI_EXPORT_TOKEN_LARGE_THRESHOLD) return 'large';
    if (finalEstimatedTokens >= AI_EXPORT_TOKEN_WARNING_THRESHOLD) return 'warning';
    return 'normal';
}

export type AiExportCompatibleChoice = AiExportCatalogCompatibilityChoice & {
    readonly status: 'compatible';
    readonly reasonCode: null;
    readonly backendEntry: AiExportBackendCatalogEntry;
};

export interface AiExportTaskOption {
    readonly definition: AiExportTaskDefinition;
    readonly compatibleDetailLevels: readonly AiExportDetailLevel[];
    readonly disabled: boolean;
}

export interface AiExportAnalysisOption extends AiExportTaskOption {
    readonly selection: AiExportAnalysisSelection;
    readonly syntheticSnapshot: boolean;
}

export interface AiExportDetailOption {
    readonly detailLevel: AiExportDetailLevel;
    readonly choice?: AiExportCompatibleChoice;
    readonly disabled: boolean;
}

export interface AiExportOptionsFingerprintInput {
    readonly task: AiExportTask;
    readonly detailLevel: AiExportDetailLevel;
    readonly renderMode: AiExportRenderMode;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly userNotes?: string;
    readonly webResearch: boolean;
    readonly technicalWindow?: AiExportTechnicalWindowSelection;
}

export interface AiExportOptionsSelection extends AiExportOptionsFingerprintInput {}

export interface AiExportOptionsPanelCallbackMetadata {
    readonly userNotesDraft: string;
}

export interface AiExportPanelSelectionInput {
    readonly domain: AiExportDomain;
    readonly analysis: AiExportAnalysisSelection;
    readonly detailLevel: AiExportDetailLevel;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly userNotes?: string;
    readonly technicalWindow?: AiExportTechnicalWindowSelection;
    readonly taskDefinitions: readonly AiExportTaskDefinition[];
}

export interface AiExportMenuTriggerBehavior {
    readonly nativeDisabled: boolean;
    readonly ariaBusy: boolean;
    readonly canToggle: boolean;
}

export interface AiExportStatsContextFingerprintInput {
    readonly contextKey: string;
    readonly dateStart: string;
    readonly dateEnd: string;
    readonly displayCurrency: string;
    readonly targetCurrency: string;
}

export interface AiExportReconciledTaskDetailSelection {
    readonly task: AiExportTask;
    readonly detailLevel: AiExportDetailLevel;
}

export interface AiExportOptionsPanelLabels {
    readonly taskLabel: string;
    readonly taskLabels: Readonly<Record<string, string>>;
    readonly taskDescriptions: Readonly<Record<string, string>>;
    readonly snapshotLabel: string;
    readonly snapshotDescription: string;
    readonly detailLevelLabel: string;
    readonly detailLevelHelp: Readonly<Record<AiExportDetailLevel, string>>;
    readonly detailLevelLabels: Readonly<Record<AiExportDetailLevel, string>>;
    readonly technicalWindowLabel: string;
    readonly technicalWindowHelp: string;
    readonly technicalWindowPresetLabels: Readonly<Record<AiExportTechnicalWindowPreset, string>>;
    readonly technicalWindowUnitLabels: Readonly<Record<AiExportTechnicalWindowUnit, string>>;
    readonly technicalWindowUnitShortLabels: Readonly<Record<AiExportTechnicalWindowUnit, string>>;
    readonly documentationLabel: string;
    readonly userNotesLabel: string;
    readonly userNotesPlaceholder?: string;
    readonly payloadStatsLabel: string;
    readonly backendEstimatedTokensLabel: string;
    readonly finalEstimatedTokensLabel: string;
    readonly tokenSeverityLabels: Readonly<Record<AiExportTokenSeverity, string>>;
    readonly exportLabel: string;
    readonly loadingLabel: string;
}

export function findAiExportCatalogChoice(compatibility: AiExportCatalogCompatibilityResult, domain: AiExportDomain, task: AiExportTask, detailLevel: AiExportDetailLevel): AiExportCatalogCompatibilityChoice | undefined {
    return compatibility.choices.find((choice) => choice.domain === domain && choice.taskId === task && choice.backendTask === task && choice.detailLevel === detailLevel);
}

export function isAiExportCompatibleChoice(choice: AiExportCatalogCompatibilityChoice | undefined): choice is AiExportCompatibleChoice {
    return choice?.status === 'compatible' && choice.reasonCode === null && choice.backendEntry !== undefined;
}

export function findCompatibleAiExportChoice(compatibility: AiExportCatalogCompatibilityResult, domain: AiExportDomain, task: AiExportTask, detailLevel: AiExportDetailLevel): AiExportCompatibleChoice | undefined {
    const choice = findAiExportCatalogChoice(compatibility, domain, task, detailLevel);
    return isAiExportCompatibleChoice(choice) ? choice : undefined;
}

export function getAiExportTaskOptions(taskDefinitions: readonly AiExportTaskDefinition[], compatibility: AiExportCatalogCompatibilityResult): readonly AiExportTaskOption[] {
    return taskDefinitions.map((definition) => {
        const compatibleDetailLevels = definition.supportedDetailLevels.filter((detailLevel) => findCompatibleAiExportChoice(compatibility, definition.domain, definition.backendTask, detailLevel) !== undefined);

        return {
            definition,
            compatibleDetailLevels,
            disabled: compatibleDetailLevels.length === 0,
        };
    });
}

export function getAiExportSnapshotTask(domain: AiExportDomain): AiExportTask {
    return AI_EXPORT_SNAPSHOT_TASK_BY_DOMAIN[domain];
}

export function isAiExportSnapshotSelection(selection: AiExportAnalysisSelection): selection is typeof AI_EXPORT_SNAPSHOT_SELECTION_ID {
    return selection === AI_EXPORT_SNAPSHOT_SELECTION_ID;
}

export function isAiExportAnalysisSelection(value: string, taskDefinitions: readonly AiExportTaskDefinition[], hiddenAnalysisTasks: AiExportHiddenAnalysisTasks = []): value is AiExportAnalysisSelection {
    return value === AI_EXPORT_SNAPSHOT_SELECTION_ID || taskDefinitions.some((definition) => definition.id === value && !hiddenAnalysisTasks.includes(definition.id));
}

export function getInitialAiExportAnalysisSelection(task: AiExportTask, renderMode: AiExportRenderMode): AiExportAnalysisSelection {
    return renderMode === 'data_only' ? AI_EXPORT_SNAPSHOT_SELECTION_ID : task;
}

export function getAiExportTaskForAnalysisSelection(domain: AiExportDomain, analysis: AiExportAnalysisSelection): AiExportTask {
    return isAiExportSnapshotSelection(analysis) ? getAiExportSnapshotTask(domain) : analysis;
}

export function getAiExportAnalysisOptions(taskDefinitions: readonly AiExportTaskDefinition[], compatibility: AiExportCatalogCompatibilityResult, domain: AiExportDomain, hiddenAnalysisTasks: AiExportHiddenAnalysisTasks = []): readonly AiExportAnalysisOption[] {
    const taskOptions = getAiExportTaskOptions(taskDefinitions, compatibility);
    const snapshotTask = getAiExportSnapshotTask(domain);
    const snapshotTaskOption = taskOptions.find((option) => option.definition.domain === domain && option.definition.backendTask === snapshotTask);
    const snapshotOptions: readonly AiExportAnalysisOption[] = snapshotTaskOption
        ? [
              {
                  ...snapshotTaskOption,
                  selection: AI_EXPORT_SNAPSHOT_SELECTION_ID,
                  syntheticSnapshot: true,
              },
          ]
        : [];

    return [
        ...snapshotOptions,
        ...taskOptions
            .filter((option) => option.definition.domain === domain && !hiddenAnalysisTasks.includes(option.definition.id))
            .map(
                (option): AiExportAnalysisOption => ({
                    ...option,
                    selection: option.definition.id,
                    syntheticSnapshot: false,
                }),
            ),
    ];
}

export function getAiExportDetailOptions(taskDefinition: AiExportTaskDefinition | undefined, compatibility: AiExportCatalogCompatibilityResult): readonly AiExportDetailOption[] {
    if (!taskDefinition) return [];

    return taskDefinition.supportedDetailLevels.map((detailLevel) => {
        const choice = findCompatibleAiExportChoice(compatibility, taskDefinition.domain, taskDefinition.backendTask, detailLevel);
        return {
            detailLevel,
            choice,
            disabled: choice === undefined,
        };
    });
}

export function reconcileAiExportTaskAndDetail(
    taskDefinitions: readonly AiExportTaskDefinition[],
    compatibility: AiExportCatalogCompatibilityResult,
    currentTask: AiExportTask,
    currentDetailLevel: AiExportDetailLevel,
    hiddenAnalysisTasks: AiExportHiddenAnalysisTasks = [],
): AiExportReconciledTaskDetailSelection {
    const taskOptions = getAiExportTaskOptions(taskDefinitions, compatibility).filter((option) => !hiddenAnalysisTasks.includes(option.definition.id));
    const currentTaskOption = taskOptions.find((option) => option.definition.id === currentTask);
    const taskOption = currentTaskOption && !currentTaskOption.disabled ? currentTaskOption : (taskOptions.find((option) => !option.disabled) ?? currentTaskOption ?? taskOptions[0]);

    if (!taskOption) {
        return {
            task: currentTask,
            detailLevel: currentDetailLevel,
        };
    }

    const detailOptions = getAiExportDetailOptions(taskOption.definition, compatibility);
    const currentDetailOption = detailOptions.find((option) => option.detailLevel === currentDetailLevel);
    const detailOption = currentDetailOption && !currentDetailOption.disabled ? currentDetailOption : (detailOptions.find((option) => option.detailLevel === taskOption.definition.defaultDetailLevel && !option.disabled) ?? detailOptions.find((option) => !option.disabled));

    return {
        task: taskOption.definition.id,
        detailLevel: detailOption?.detailLevel ?? currentDetailLevel,
    };
}

export function reconcileAiExportAnalysisAndDetail(
    taskDefinitions: readonly AiExportTaskDefinition[],
    compatibility: AiExportCatalogCompatibilityResult,
    domain: AiExportDomain,
    currentAnalysis: AiExportAnalysisSelection,
    currentDetailLevel: AiExportDetailLevel,
    hiddenAnalysisTasks: AiExportHiddenAnalysisTasks = [],
): AiExportReconciledTaskDetailSelection & {readonly analysis: AiExportAnalysisSelection} {
    const analysisOptions = getAiExportAnalysisOptions(taskDefinitions, compatibility, domain, hiddenAnalysisTasks);
    const currentOption = analysisOptions.find((option) => option.selection === currentAnalysis);
    const selectedOption =
        currentOption && !currentOption.disabled
            ? currentOption
            : (analysisOptions.find((option) => !option.syntheticSnapshot && !option.disabled) ?? analysisOptions.find((option) => !option.disabled) ?? currentOption ?? analysisOptions.find((option) => !option.syntheticSnapshot) ?? analysisOptions[0]);

    if (!selectedOption) {
        return {
            task: getAiExportTaskForAnalysisSelection(domain, currentAnalysis),
            detailLevel: currentDetailLevel,
            analysis: currentAnalysis,
        };
    }

    const detailOptions = getAiExportDetailOptions(selectedOption.definition, compatibility);
    const currentDetailOption = detailOptions.find((option) => option.detailLevel === currentDetailLevel);
    const detailOption =
        currentDetailOption && !currentDetailOption.disabled
            ? currentDetailOption
            : (detailOptions.find((option) => option.detailLevel === selectedOption.definition.defaultDetailLevel && !option.disabled) ?? detailOptions.find((option) => !option.disabled) ?? currentDetailOption ?? detailOptions[0]);

    return {
        task: selectedOption.definition.id,
        detailLevel: detailOption?.detailLevel ?? currentDetailLevel,
        analysis: selectedOption.selection,
    };
}

export function isAiExportWebResearchAvailable(taskDefinition: AiExportTaskDefinition | undefined, renderMode: AiExportRenderMode): boolean {
    return renderMode === 'full_prompt' && taskDefinition?.supportsWebResearch === true;
}

export function normalizeAiExportWebResearch(taskDefinition: AiExportTaskDefinition | undefined, renderMode: AiExportRenderMode, webResearch: boolean | undefined): boolean {
    return isAiExportWebResearchAvailable(taskDefinition, renderMode) && webResearch === true;
}

export function normalizeAiExportUserNotes(renderMode: AiExportRenderMode, userNotes: string | undefined): string | undefined {
    return renderMode === 'full_prompt' ? userNotes : undefined;
}

export function normalizeAiExportTechnicalWindow(selection: AiExportTechnicalWindowSelection | undefined): AiExportTechnicalWindowSelection {
    const preset = selection && AI_EXPORT_TECHNICAL_WINDOW_PRESETS.includes(selection.preset) ? selection.preset : AI_EXPORT_DEFAULT_TECHNICAL_WINDOW.preset;
    const customUnit = selection && AI_EXPORT_TECHNICAL_WINDOW_UNITS.includes(selection.customUnit) ? selection.customUnit : AI_EXPORT_DEFAULT_TECHNICAL_WINDOW.customUnit;
    const customAmount = selection && Number.isFinite(selection.customAmount) ? Math.max(1, Math.floor(selection.customAmount)) : AI_EXPORT_DEFAULT_TECHNICAL_WINDOW.customAmount;
    return {preset, customAmount, customUnit};
}

export function getAiExportMenuTriggerBehavior(disabled: boolean, loading: boolean): AiExportMenuTriggerBehavior {
    return {
        nativeDisabled: disabled,
        ariaBusy: loading,
        canToggle: !disabled && !loading,
    };
}

export function aiExportOptionsFingerprint(options: AiExportOptionsFingerprintInput): string {
    const technicalWindow = normalizeAiExportTechnicalWindow(options.technicalWindow);
    return JSON.stringify([
        'ai-export-options-v2',
        options.task,
        options.detailLevel,
        options.renderMode,
        options.responseLanguage,
        normalizeAiExportUserNotes(options.renderMode, options.userNotes) ?? null,
        options.webResearch,
        technicalWindow.preset,
        technicalWindow.preset === 'custom' ? technicalWindow.customAmount : null,
        technicalWindow.preset === 'custom' ? technicalWindow.customUnit : null,
    ]);
}

export function normalizeAiExportPanelOptions(input: AiExportPanelSelectionInput): AiExportOptionsSelection {
    const snapshot = isAiExportSnapshotSelection(input.analysis);
    const task = getAiExportTaskForAnalysisSelection(input.domain, input.analysis);
    const taskDefinition = input.taskDefinitions.find((definition) => definition.domain === input.domain && definition.backendTask === task);
    const userNotes = !snapshot && taskDefinition?.supportsUserNotes === true && input.userNotes?.trim() ? input.userNotes : undefined;

    return {
        task,
        detailLevel: input.detailLevel,
        renderMode: snapshot ? 'data_only' : 'full_prompt',
        responseLanguage: input.responseLanguage,
        userNotes,
        webResearch: false,
        technicalWindow: normalizeAiExportTechnicalWindow(input.technicalWindow),
    };
}

export function aiExportStatsContextFingerprint(context: AiExportStatsContextFingerprintInput): string {
    return JSON.stringify(['ai-export-stats-context-v1', context.contextKey, context.dateStart, context.dateEnd, context.displayCurrency, context.targetCurrency]);
}

export function isAiExportStatsRequestCurrent(requestGeneration: number, requestContextFingerprint: string, currentGeneration: number, currentContextFingerprint: string): boolean {
    return requestGeneration === currentGeneration && requestContextFingerprint === currentContextFingerprint;
}

export function getMatchingAiExportStats(lastStats: AiExportPromptStats | undefined, lastStatsFingerprint: string | undefined, currentFingerprint: string): AiExportPromptStats | undefined {
    return lastStatsFingerprint === currentFingerprint ? lastStats : undefined;
}
