import {describe, expect, it} from 'vitest';

import {AiExportProblemError} from '../aiExportClient';
import type {AiExportOptionsSelection} from '../aiExportOptions';
import type {AiExportPromptStats} from '../templates/promptRenderer';
import {buildAiExportMenuLabels, getAiExportErrorMessage, getAiExportSuccessMessages} from '../ui';
import {compatibilityFixture} from './runtimeFixtures';

const t = (key: string) => key;

describe('AI Export UI helpers', () => {
    it('builds labels for every real catalog selection', () => {
        const labels = buildAiExportMenuLabels(t, compatibilityFixture(), 'AI Export');

        expect(Object.keys(labels.options.selectionLabels)).toHaveLength(19);
        expect(labels.options.categoryLabels).toEqual({dataset: 'aiExport.exportData', analysis: 'aiExport.requestAnalysis'});
        expect(labels.options.categoryHelp).toEqual({dataset: 'aiExport.exportDataHelp', analysis: 'aiExport.requestAnalysisHelp'});
        expect(labels.options.payloadStatsHelp).toBe('aiExport.payloadStatsHelp');
        expect(labels.options.tokenUnitLabel).toBe('aiExport.tokenUnit');
    });

    it('includes localized final token and byte sizes in the copied message', () => {
        const options: AiExportOptionsSelection = {
            selectionKind: 'analysis',
            selectionId: 'portfolio.pac_planning',
            detailLevel: 'standard',
            period: {preset: '3m', customAmount: 3, customUnit: 'months'},
            responseLanguage: 'Italian',
        };
        const stats: AiExportPromptStats = {
            finalPrompt: {
                characterCountUtf16CodeUnits: 47_700,
                byteCountUtf8: 48_828,
                estimatedTokens: 11_925,
                estimationMethod: 'ceil_utf16_code_units_div_4_v1',
            },
            snapshotBackendStats: {
                dataset_count: 1,
                section_count: 1,
                serialized_characters: 129_704,
                serialized_bytes: 131_072,
                estimated_tokens: 32_426,
                token_estimation_method: 'chars_div_4_v1',
            },
        };
        const translate = (key: string, translationOptions?: {values?: Record<string, string | number | boolean | null | undefined>}) => {
            if (key === 'aiExport.details.standard') return 'Standard';
            if (key === 'aiExport.tokenUnit') return 'token';
            if (key === 'aiExport.copied') return `AI Export copiato:\n• ${translationOptions?.values?.tokens} (💾 ${translationOptions?.values?.bytes})\n• dettaglio: ${translationOptions?.values?.detail}`;
            return key;
        };

        expect(getAiExportSuccessMessages(translate, {options, stats}).copied).toBe('AI Export copiato:\n• 11,93 k token (💾 47,68 KB)\n• dettaglio: Standard');
    });

    it('maps new typed problem codes', () => {
        const error = new AiExportProblemError(
            422,
            {
                code: 'selection_not_applicable',
                message: 'Not applicable',
                domain: 'asset',
                selection_kind: 'analysis',
                selection_id: 'asset.position_review',
                detail_level: 'standard',
                applicability_code: 'requires_position',
                reason_code: 'no_position',
            },
            null,
        );
        expect(getAiExportErrorMessage(t, error)).toBe('aiExport.selectionNotApplicable');
    });
});
