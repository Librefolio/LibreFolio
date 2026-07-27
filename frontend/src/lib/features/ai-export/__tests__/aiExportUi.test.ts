import {ZodError} from 'zod';
import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';

import {AiExportContractMismatchError, AiExportNetworkError, AiExportProblemError, AiExportValidationError, type AiExportProblemDetail} from '../aiExportClient';
import {AiExportChoiceUnavailableError, AiExportClipboardUnavailableError} from '../aiExportClipboardV2';
import {AI_EXPORT_TASK_CATALOG} from '../catalog/compatibility';
import {aiExportResponseLanguageFromLocale, buildAiExportMenuV2Labels, getAiExportErrorMessage, getAiExportSuccessMessages, type AiExportTranslate} from '../ui';

const keyTranslator: AiExportTranslate = (key, options) => {
    const detail = options?.values?.detail;
    return detail === undefined ? key : `${key}:${String(detail)}`;
};

describe('AI Export v2 UI helpers', () => {
    it('maps supported base and regional locales to trusted response language names', () => {
        expect(aiExportResponseLanguageFromLocale('en')).toBe('English');
        expect(aiExportResponseLanguageFromLocale('en-GB')).toBe('English');
        expect(aiExportResponseLanguageFromLocale('it_IT')).toBe('Italian');
        expect(aiExportResponseLanguageFromLocale('fr-CA')).toBe('French');
        expect(aiExportResponseLanguageFromLocale('ES-419')).toBe('Spanish');
        expect(aiExportResponseLanguageFromLocale(' de-DE ')).toBe('English');
        expect(aiExportResponseLanguageFromLocale(null)).toBe('English');
        expect(aiExportResponseLanguageFromLocale(undefined)).toBe('English');
    });

    it('builds complete menu labels from shared controls and task definition keys', () => {
        const labels = buildAiExportMenuV2Labels(keyTranslator, AI_EXPORT_TASK_CATALOG, 'AI Export', 'Building export…');

        expect(labels.triggerLabel).toBe('AI Export');
        expect(labels.loadingLabel).toBe('Building export…');
        expect(labels.panelLabel).toBe('aiExport.v2.panelLabel');
        expect(labels.options).toMatchObject({
            taskLabel: 'aiExport.v2.task',
            detailLevelLabel: 'aiExport.v2.detailLevel',
            detailLevelLabels: {
                compact: 'aiExport.v2.details.compact',
                standard: 'aiExport.v2.details.standard',
                full: 'aiExport.v2.details.full',
            },
            snapshotLabel: 'aiExport.v2.snapshotLabel',
            snapshotDescription: 'aiExport.v2.snapshotDescription',
            detailLevelHelp: {
                compact: 'aiExport.v2.detailLevelHelp.compact',
                standard: 'aiExport.v2.detailLevelHelp.standard',
                full: 'aiExport.v2.detailLevelHelp.full',
            },
            documentationLabel: 'common.documentation',
            userNotesLabel: 'aiExport.v2.userNotes',
            userNotesPlaceholder: 'aiExport.v2.userNotesPlaceholder',
            payloadStatsLabel: 'aiExport.v2.payloadStats',
            backendEstimatedTokensLabel: 'aiExport.v2.backendEstimatedTokens',
            finalEstimatedTokensLabel: 'aiExport.v2.finalEstimatedTokens',
            tokenSeverityLabels: {
                normal: 'aiExport.v2.tokenSeverity.normal',
                warning: 'aiExport.v2.tokenSeverity.warning',
                large: 'aiExport.v2.tokenSeverity.large',
            },
            exportLabel: 'aiExport.v2.export',
            loadingLabel: 'aiExport.v2.preparing',
        });
        expect(Object.keys(labels.options.taskLabels)).toHaveLength(18);
        expect(Object.keys(labels.options.taskDescriptions ?? {})).toHaveLength(18);

        for (const taskDefinition of AI_EXPORT_TASK_CATALOG) {
            expect(labels.options.taskLabels[taskDefinition.id]).toBe(taskDefinition.labelKey);
            expect(labels.options.taskDescriptions?.[taskDefinition.id]).toBe(taskDefinition.descriptionKey);
        }
    });

    it('localizes success feedback with the resolved detail label', () => {
        expect(getAiExportSuccessMessages(keyTranslator, {detailLevel: 'full'})).toEqual({
            copied: 'aiExport.v2.copied:aiExport.v2.details.full',
            privacyNotice: 'aiExport.v2.privacyNotice:aiExport.v2.details.full',
        });
    });

    it('maps client and clipboard errors without exposing internal messages', () => {
        const internalMessage = 'private backend context';
        const cases: ReadonlyArray<readonly [unknown, string]> = [
            [new AiExportChoiceUnavailableError('portfolio', 'pac_planning', 'standard', 'catalog_choice_missing'), 'aiExport.v2.catalogUnavailable'],
            [new AiExportContractMismatchError([{field: internalMessage, expected: 'v2', actual: 'v1'}]), 'aiExport.v2.contractMismatch'],
            [new AiExportValidationError('response', 422, new ZodError([]), new Error(internalMessage)), 'aiExport.v2.validationFailed'],
            [new AiExportNetworkError(internalMessage, 'ERR_NETWORK', new Error(internalMessage)), 'aiExport.v2.networkFailed'],
            [new AiExportClipboardUnavailableError(internalMessage), 'aiExport.v2.clipboardUnavailable'],
            [new Error(internalMessage), 'aiExport.v2.genericFailed'],
        ];

        for (const [error, expected] of cases) {
            const message = getAiExportErrorMessage(keyTranslator, error);
            expect(message).toBe(expected);
            expect(message).not.toContain(internalMessage);
        }
    });

    it('maps every typed backend problem code to safe localized feedback', () => {
        const cases: ReadonlyArray<readonly [AiExportProblemDetail, string]> = [
            [
                parseProblem({
                    code: 'unsupported_profile',
                    message: 'Internal unsupported profile context',
                    domain: 'portfolio',
                    task: 'pac_planning',
                    detail_level: 'full',
                    supported_profiles: ['portfolio.pac_planning.standard'],
                }),
                'aiExport.v2.catalogUnavailable',
            ],
            [
                parseProblem({
                    code: 'profile_contract_mismatch',
                    message: 'Internal contract context',
                    profile_id: 'asset.asset_snapshot.standard',
                    expected_frontend_response_contract_id: 'asset.asset_snapshot',
                    expected_frontend_response_contract_version: 2,
                    actual_frontend_response_contract_id: 'asset.asset_snapshot',
                    actual_frontend_response_contract_version: 1,
                }),
                'aiExport.v2.contractMismatch',
            ],
            [
                parseProblem({
                    code: 'task_not_applicable',
                    message: 'Internal applicability context',
                    domain: 'fx',
                    task: 'fx_exposure_impact',
                    detail_level: 'standard',
                    profile_id: 'fx.fx_exposure_impact.standard',
                    applicability_code: 'linked_fx_exposure_required',
                }),
                'aiExport.v2.taskNotApplicable',
            ],
            [
                parseProblem({
                    code: 'broker_access_denied',
                    message: 'Internal access context',
                    denied_broker_ids: [5],
                }),
                'aiExport.v2.entityNotFound',
            ],
            [
                parseProblem({
                    code: 'entity_not_found',
                    message: 'Internal entity context',
                    entity_reference: {kind: 'asset', asset_id: 999},
                }),
                'aiExport.v2.entityNotFound',
            ],
            [
                parseProblem({
                    code: 'snapshot_source_failure',
                    message: 'Internal source context',
                    source_code: 'portfolio_engine',
                    retryable: true,
                }),
                'aiExport.v2.sourceUnavailable',
            ],
        ];

        for (const [problem, expected] of cases) {
            const message = getAiExportErrorMessage(keyTranslator, new AiExportProblemError(409, problem, new Error(problem.message)));
            expect(message).toBe(expected);
            expect(message).not.toContain(problem.message);
        }
    });
});

function parseProblem(detail: unknown): AiExportProblemDetail {
    return schemas.AiExportProblemResponse.parse({detail}).detail;
}
