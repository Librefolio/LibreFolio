import type {AiExportMenuLabels} from './AiExportMenu.svelte';
import {AiExportContractMismatchError, AiExportNetworkError, AiExportProblemError, AiExportValidationError, type AiExportProblemDetail} from './aiExportClient';
import {AiExportChoiceUnavailableError, AiExportClipboardUnavailableError, type PreparedAiExport} from './aiExportClipboard';
import {formatAiExportByteSize, formatAiExportTokenCount} from './aiExportOptions';
import type {AiExportCatalogCompatibilityResult} from './catalog/compatibility';
import type {AiExportResponseLanguageDisplayName} from './templates/promptRenderer';

type AiExportTranslationValue = string | number | boolean | null | undefined;
export type AiExportTranslate = (key: string, options?: {values?: Record<string, AiExportTranslationValue>}) => string;

export interface AiExportSuccessMessages {
    readonly copied: string;
    readonly privacyNotice: string;
}

export function aiExportResponseLanguageFromLocale(locale: string | null | undefined): AiExportResponseLanguageDisplayName {
    const code = locale?.trim().toLowerCase().split(/[-_]/, 1)[0];
    if (code === 'it') return 'Italian';
    if (code === 'fr') return 'French';
    if (code === 'es') return 'Spanish';
    return 'English';
}

export function buildAiExportMenuLabels(t: AiExportTranslate, compatibility: AiExportCatalogCompatibilityResult, triggerLabel: string): AiExportMenuLabels {
    const selectionLabels: Record<string, string> = {};
    const selectionDescriptions: Record<string, string> = {};
    for (const selection of compatibility.selections) {
        selectionLabels[selection.id] = t(selection.entry.display_i18n_key);
        selectionDescriptions[selection.id] = t(selection.entry.description_i18n_key);
    }
    return {
        triggerLabel,
        panelLabel: t('aiExport.panelLabel'),
        options: {
            categoryLabel: t('aiExport.category'),
            categoryLabels: {
                dataset: t('aiExport.exportData'),
                analysis: t('aiExport.requestAnalysis'),
            },
            selectionLabel: t('aiExport.selection'),
            selectionLabels,
            selectionDescriptions,
            detailLevelLabel: t('aiExport.detailLevel'),
            detailLevelHelp: {
                compact: t('aiExport.detailLevelHelp.compact'),
                standard: t('aiExport.detailLevelHelp.standard'),
                full: t('aiExport.detailLevelHelp.full'),
            },
            detailLevelLabels: {
                compact: t('aiExport.details.compact'),
                standard: t('aiExport.details.standard'),
                full: t('aiExport.details.full'),
            },
            periodLabel: t('aiExport.period'),
            periodHelp: t('aiExport.periodHelp'),
            periodPresetLabels: {
                '3m': '3M',
                '6m': '6M',
                '1y': '1Y',
                custom: t('aiExport.periodCustom'),
            },
            periodUnitLabels: {
                days: t('datePicker.granularity.days'),
                weeks: t('datePicker.granularity.weeks'),
                months: t('datePicker.granularity.months'),
                years: t('datePicker.granularity.years'),
            },
            periodUnitShortLabels: {
                days: t('datePicker.granularity.daysShort').toUpperCase(),
                weeks: t('datePicker.granularity.weeksShort').toUpperCase(),
                months: t('datePicker.granularity.monthsShort').toUpperCase(),
                years: t('datePicker.granularity.yearsShort').toUpperCase(),
            },
            userNotesLabel: t('aiExport.userNotes'),
            userNotesPlaceholder: t('aiExport.userNotesPlaceholder'),
            payloadStatsLabel: t('aiExport.payloadStats'),
            backendEstimatedTokensLabel: t('aiExport.backendEstimatedTokens'),
            finalEstimatedTokensLabel: t('aiExport.finalEstimatedTokens'),
            tokenUnitLabel: t('aiExport.tokenUnit'),
            tokenSeverityLabels: {
                normal: t('aiExport.tokenSeverity.normal'),
                warning: t('aiExport.tokenSeverity.warning'),
                large: t('aiExport.tokenSeverity.large'),
            },
            prepareLabel: t('aiExport.copy'),
            preparingLabel: t('aiExport.preparing'),
            copyAnywayLabel: t('aiExport.copyAnyway'),
            useCompactLabel: t('aiExport.useCompact'),
        },
    };
}

export function getAiExportSuccessMessages(t: AiExportTranslate, result: Pick<PreparedAiExport, 'options' | 'stats'>): AiExportSuccessMessages {
    const detail = t(`aiExport.details.${result.options.detailLevel}`);
    const locale = {
        English: 'en',
        Italian: 'it',
        French: 'fr',
        Spanish: 'es',
    }[result.options.responseLanguage];
    const tokens = formatAiExportTokenCount(result.stats.finalPrompt.estimatedTokens, locale, t('aiExport.tokenUnit'));
    const bytes = formatAiExportByteSize(result.stats.finalPrompt.byteCountUtf8, locale);
    return {
        copied: t('aiExport.copied', {values: {detail, tokens, bytes}}),
        privacyNotice: t('aiExport.privacyNotice', {values: {detail}}),
    };
}

function problemMessage(t: AiExportTranslate, problem: AiExportProblemDetail): string {
    if (problem.code === 'version_mismatch') return t('aiExport.contractMismatch');
    if (problem.code === 'unsupported_selection') return t('aiExport.catalogUnavailable');
    if (problem.code === 'selection_not_applicable') return t('aiExport.selectionNotApplicable');
    if (problem.code === 'broker_access_denied' || problem.code === 'entity_not_found') return t('aiExport.entityNotFound');
    return t('aiExport.sourceUnavailable');
}

export function getAiExportErrorMessage(t: AiExportTranslate, error: unknown): string {
    if (error instanceof AiExportChoiceUnavailableError) return t('aiExport.catalogUnavailable');
    if (error instanceof AiExportContractMismatchError) return t('aiExport.contractMismatch');
    if (error instanceof AiExportProblemError) return problemMessage(t, error.problem);
    if (error instanceof AiExportValidationError) return t('aiExport.validationFailed');
    if (error instanceof AiExportNetworkError) return t('aiExport.networkFailed');
    if (error instanceof AiExportClipboardUnavailableError) return t('aiExport.clipboardUnavailable');
    return t('aiExport.genericFailed');
}
