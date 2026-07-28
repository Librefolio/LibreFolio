import type {AiExportMenuV2Labels} from './AiExportMenuV2.svelte';
import {AiExportContractMismatchError, AiExportNetworkError, AiExportProblemError, AiExportValidationError, type AiExportProblemDetail} from './aiExportClient';
import {AiExportChoiceUnavailableError, AiExportClipboardUnavailableError, type CopyAiExportV2Result} from './aiExportClipboardV2';
import type {AiExportTaskDefinition} from './catalog/shared';
import type {AiExportResponseLanguageDisplayName} from './templates/promptRenderer';

type AiExportTranslationValue = string | number | boolean | null | undefined;

export type AiExportTranslate = (key: string, options?: {values?: Record<string, AiExportTranslationValue>}) => string;

export interface AiExportSuccessMessages {
    readonly copied: string;
    readonly privacyNotice: string;
}

export function aiExportResponseLanguageFromLocale(locale: string | null | undefined): AiExportResponseLanguageDisplayName {
    const languageCode = locale?.trim().toLowerCase().split(/[-_]/, 1)[0];

    switch (languageCode) {
        case 'it':
            return 'Italian';
        case 'fr':
            return 'French';
        case 'es':
            return 'Spanish';
        case 'en':
        default:
            return 'English';
    }
}

export function buildAiExportMenuV2Labels(t: AiExportTranslate, taskDefinitions: readonly AiExportTaskDefinition[], triggerLabel: string, loadingLabel: string): AiExportMenuV2Labels {
    const taskLabels: Record<string, string> = {};
    const taskDescriptions: Record<string, string> = {};

    for (const taskDefinition of taskDefinitions) {
        taskLabels[taskDefinition.id] = t(taskDefinition.labelKey);
        taskDescriptions[taskDefinition.id] = t(taskDefinition.descriptionKey);
    }

    return {
        triggerLabel,
        loadingLabel,
        panelLabel: t('aiExport.v2.panelLabel'),
        options: {
            taskLabel: t('aiExport.v2.task'),
            taskLabels,
            taskDescriptions,
            snapshotLabel: t('aiExport.v2.snapshotLabel'),
            snapshotDescription: t('aiExport.v2.snapshotDescription'),
            detailLevelLabel: t('aiExport.v2.detailLevel'),
            detailLevelHelp: {
                compact: t('aiExport.v2.detailLevelHelp.compact'),
                standard: t('aiExport.v2.detailLevelHelp.standard'),
                full: t('aiExport.v2.detailLevelHelp.full'),
            },
            detailLevelLabels: {
                compact: t('aiExport.v2.details.compact'),
                standard: t('aiExport.v2.details.standard'),
                full: t('aiExport.v2.details.full'),
            },
            technicalWindowLabel: t('aiExport.v2.technicalWindow'),
            technicalWindowHelp: t('aiExport.v2.technicalWindowHelp'),
            technicalWindowPresetLabels: {
                '3m': '3M',
                '6m': '6M',
                '1y': '1Y',
                custom: t('aiExport.v2.technicalWindowCustom'),
            },
            technicalWindowUnitLabels: {
                days: t('datePicker.granularity.days'),
                weeks: t('datePicker.granularity.weeks'),
                months: t('datePicker.granularity.months'),
                years: t('datePicker.granularity.years'),
            },
            technicalWindowUnitShortLabels: {
                days: t('datePicker.granularity.daysShort').toUpperCase(),
                weeks: t('datePicker.granularity.weeksShort').toUpperCase(),
                months: t('datePicker.granularity.monthsShort').toUpperCase(),
                years: t('datePicker.granularity.yearsShort').toUpperCase(),
            },
            documentationLabel: t('common.documentation'),
            userNotesLabel: t('aiExport.v2.userNotes'),
            userNotesPlaceholder: t('aiExport.v2.userNotesPlaceholder'),
            payloadStatsLabel: t('aiExport.v2.payloadStats'),
            backendEstimatedTokensLabel: t('aiExport.v2.backendEstimatedTokens'),
            finalEstimatedTokensLabel: t('aiExport.v2.finalEstimatedTokens'),
            tokenSeverityLabels: {
                normal: t('aiExport.v2.tokenSeverity.normal'),
                warning: t('aiExport.v2.tokenSeverity.warning'),
                large: t('aiExport.v2.tokenSeverity.large'),
            },
            exportLabel: t('aiExport.v2.export'),
            loadingLabel: t('aiExport.v2.preparing'),
        },
    };
}

export function getAiExportSuccessMessages(t: AiExportTranslate, result: Pick<CopyAiExportV2Result, 'detailLevel'>): AiExportSuccessMessages {
    const detail = t(`aiExport.v2.details.${result.detailLevel}`);
    const values = {detail};

    return {
        copied: t('aiExport.v2.copied', {values}),
        privacyNotice: t('aiExport.v2.privacyNotice', {values}),
    };
}

export function getAiExportErrorMessage(t: AiExportTranslate, error: unknown): string {
    if (error instanceof AiExportChoiceUnavailableError) return t('aiExport.v2.catalogUnavailable');
    if (error instanceof AiExportContractMismatchError) return t('aiExport.v2.contractMismatch');
    if (error instanceof AiExportProblemError) return getAiExportProblemErrorMessage(t, error.problem);
    if (error instanceof AiExportValidationError) return t('aiExport.v2.validationFailed');
    if (error instanceof AiExportNetworkError) return t('aiExport.v2.networkFailed');
    if (error instanceof AiExportClipboardUnavailableError) return t('aiExport.v2.clipboardUnavailable');
    return t('aiExport.v2.genericFailed');
}

function getAiExportProblemErrorMessage(t: AiExportTranslate, problem: AiExportProblemDetail): string {
    switch (problem.code) {
        case 'unsupported_profile':
            return t('aiExport.v2.catalogUnavailable');
        case 'profile_contract_mismatch':
            return t('aiExport.v2.contractMismatch');
        case 'task_not_applicable':
            return t('aiExport.v2.taskNotApplicable');
        case 'broker_access_denied':
        case 'entity_not_found':
            return t('aiExport.v2.entityNotFound');
        case 'snapshot_source_failure':
            return t('aiExport.v2.sourceUnavailable');
    }
}
