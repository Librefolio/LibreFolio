import {describe, expect, it} from 'vitest';

import type {AiExportCatalogCompatibilityChoice, AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {AI_EXPORT_LOCAL_CHOICES} from '../catalog/compatibility';
import {ASSET_AI_EXPORT_TASKS} from '../catalog/assetTasks';
import {BROKER_AI_EXPORT_TASKS} from '../catalog/brokerTasks';
import {FX_AI_EXPORT_TASKS} from '../catalog/fxTasks';
import {PORTFOLIO_AI_EXPORT_TASKS} from '../catalog/portfolioTasks';
import type {AiExportDetailLevel, AiExportDomain, AiExportTask, AiExportTaskDefinition} from '../catalog/shared';
import {
    AI_EXPORT_SNAPSHOT_SELECTION_ID,
    AI_EXPORT_SNAPSHOT_TASK_BY_DOMAIN,
    AI_EXPORT_TOKEN_LARGE_THRESHOLD,
    AI_EXPORT_TOKEN_WARNING_THRESHOLD,
    aiExportOptionsFingerprint,
    aiExportStatsContextFingerprint,
    estimateAiExportTokenSeverity,
    findCompatibleAiExportChoice,
    getAiExportAnalysisOptions,
    getAiExportDetailOptions,
    getAiExportMenuTriggerBehavior,
    getInitialAiExportAnalysisSelection,
    getAiExportTaskOptions,
    getMatchingAiExportStats,
    isAiExportStatsRequestCurrent,
    isAiExportWebResearchAvailable,
    normalizeAiExportPanelOptions,
    normalizeAiExportUserNotes,
    normalizeAiExportWebResearch,
    reconcileAiExportAnalysisAndDetail,
    reconcileAiExportTaskAndDetail,
    type AiExportOptionsFingerprintInput,
} from '../aiExportOptions';
import type {AiExportPromptStats} from '../templates/promptRenderer';

describe('AI Export v2 option helpers', () => {
    it('keeps local catalog order, hides backend-only entries, and disables tasks without a compatible detail', () => {
        const pac = PORTFOLIO_AI_EXPORT_TASKS[0];
        const rebalancing = PORTFOLIO_AI_EXPORT_TASKS[1];
        const compatibility = buildCompatibility([buildChoice(pac, 'standard', 'compatible'), buildChoice(rebalancing, 'standard', 'disabled')]);
        const options = getAiExportTaskOptions([pac, rebalancing], {
            ...compatibility,
            backendOnlyEntries: [
                {
                    key: 'asset:pac_planning:standard',
                    status: 'disabled',
                    reasonCode: 'local_definition_missing',
                    entry: {
                        domain: 'asset',
                        task: 'pac_planning',
                        detail_level: 'standard',
                        profile_id: 'portfolio.backend_only.standard',
                        profile_version: 1,
                        frontend_response_contract_id: 'portfolio.backend_only',
                        frontend_response_contract_version: 1,
                        applicability_code: 'always',
                        supports_user_notes: false,
                        supports_web_research: false,
                    },
                },
            ],
        });

        expect(options.map((option) => option.definition.id)).toEqual(['pac_planning', 'rebalancing']);
        expect(options.map((option) => option.disabled)).toEqual([false, true]);
        expect(options[0].compatibleDetailLevels).toEqual(['standard']);
        expect(options).toHaveLength(2);
    });

    it('prepends one synthetic Snapshot choice and maps it to each domain data task', () => {
        const scenarios: readonly [AiExportDomain, readonly AiExportTaskDefinition[], AiExportTask][] = [
            ['portfolio', PORTFOLIO_AI_EXPORT_TASKS, 'portfolio_description'],
            ['asset', ASSET_AI_EXPORT_TASKS, 'asset_snapshot'],
            ['fx', FX_AI_EXPORT_TASKS, 'fx_trend_review'],
            ['broker', BROKER_AI_EXPORT_TASKS, 'broker_review'],
        ];

        for (const [domain, definitions, mappedTask] of scenarios) {
            const mappedDefinition = definitions.find((definition) => definition.backendTask === mappedTask);
            if (!mappedDefinition) throw new Error(`Missing ${domain} Snapshot mapping task`);
            const compatibility = buildCompatibility([buildChoice(mappedDefinition, 'standard', 'compatible')]);
            const options = getAiExportAnalysisOptions(definitions, compatibility, domain);

            expect(AI_EXPORT_SNAPSHOT_TASK_BY_DOMAIN[domain]).toBe(mappedTask);
            expect(options[0]).toMatchObject({
                selection: AI_EXPORT_SNAPSHOT_SELECTION_ID,
                syntheticSnapshot: true,
                definition: mappedDefinition,
                disabled: false,
            });
            expect(options.some((option) => option.selection === mappedTask && !option.syntheticSnapshot)).toBe(true);
        }
    });

    it('filters hidden analyses without removing their synthetic Snapshot backing task', () => {
        const assetCompatibility = buildCompatibility(ASSET_AI_EXPORT_TASKS.flatMap((definition) => definition.supportedDetailLevels.map((detailLevel) => buildChoice(definition, detailLevel, 'compatible'))));
        const assetOptions = getAiExportAnalysisOptions(ASSET_AI_EXPORT_TASKS, assetCompatibility, 'asset', ['asset_snapshot', 'asset_pac_timing_context']);

        expect(assetOptions.map((option) => option.selection)).toEqual([AI_EXPORT_SNAPSHOT_SELECTION_ID, 'asset_trend_analysis', 'position_review', 'drawdown_recovery']);
        expect(assetOptions[0]).toMatchObject({
            selection: AI_EXPORT_SNAPSHOT_SELECTION_ID,
            syntheticSnapshot: true,
            definition: ASSET_AI_EXPORT_TASKS[0],
        });

        const fxCompatibility = buildCompatibility(FX_AI_EXPORT_TASKS.flatMap((definition) => definition.supportedDetailLevels.map((detailLevel) => buildChoice(definition, detailLevel, 'compatible'))));
        expect(getAiExportAnalysisOptions(FX_AI_EXPORT_TASKS, fxCompatibility, 'fx', ['fx_exposure_impact']).map((option) => option.selection)).toEqual([AI_EXPORT_SNAPSHOT_SELECTION_ID, 'fx_trend_review', 'fx_conversion_timing_context']);
    });

    it('reopens data-only options as Snapshot and full prompts as their real analysis', () => {
        expect(getInitialAiExportAnalysisSelection('pac_planning', 'data_only')).toBe(AI_EXPORT_SNAPSHOT_SELECTION_ID);
        expect(getInitialAiExportAnalysisSelection('pac_planning', 'full_prompt')).toBe('pac_planning');
    });

    it('normalizes Snapshot and analysis choices to effective panel exports', () => {
        expect(
            normalizeAiExportPanelOptions({
                domain: 'portfolio',
                analysis: AI_EXPORT_SNAPSHOT_SELECTION_ID,
                detailLevel: 'compact',
                responseLanguage: 'Italian',
                userNotes: 'Hidden Snapshot note',
                taskDefinitions: PORTFOLIO_AI_EXPORT_TASKS,
            }),
        ).toEqual({
            task: 'portfolio_description',
            detailLevel: 'compact',
            renderMode: 'data_only',
            responseLanguage: 'Italian',
            userNotes: undefined,
            webResearch: false,
        });

        expect(
            normalizeAiExportPanelOptions({
                domain: 'portfolio',
                analysis: 'pac_planning',
                detailLevel: 'full',
                responseLanguage: 'English',
                userNotes: 'Keep fees visible.',
                taskDefinitions: PORTFOLIO_AI_EXPORT_TASKS,
            }),
        ).toEqual({
            task: 'pac_planning',
            detailLevel: 'full',
            renderMode: 'full_prompt',
            responseLanguage: 'English',
            userNotes: 'Keep fees visible.',
            webResearch: false,
        });

        expect(
            normalizeAiExportPanelOptions({
                domain: 'portfolio',
                analysis: 'technical_breadth',
                detailLevel: 'standard',
                responseLanguage: 'English',
                userNotes: 'Unsupported note',
                taskDefinitions: PORTFOLIO_AI_EXPORT_TASKS,
            }).userNotes,
        ).toBeUndefined();
    });

    it('normalizes user notes away from every data-only export and fingerprint', () => {
        expect(normalizeAiExportUserNotes('data_only', 'Hidden Snapshot note')).toBeUndefined();
        expect(normalizeAiExportUserNotes('full_prompt', 'Analysis note')).toBe('Analysis note');

        const dataOnly = {
            task: 'portfolio_description' as const,
            detailLevel: 'standard' as const,
            renderMode: 'data_only' as const,
            responseLanguage: 'English' as const,
            webResearch: false,
        };
        expect(aiExportOptionsFingerprint({...dataOnly, userNotes: 'Hidden Snapshot note'})).toBe(aiExportOptionsFingerprint({...dataOnly, userNotes: undefined}));
    });

    it('filters detail compatibility by exact domain, task, and detail tuple', () => {
        const task = PORTFOLIO_AI_EXPORT_TASKS[0];
        const compatibility = buildCompatibility([buildChoice(task, 'compact', 'disabled'), buildChoice(task, 'standard', 'compatible'), buildChoice(task, 'full', 'disabled')]);

        const details = getAiExportDetailOptions(task, compatibility);

        expect(details.map(({detailLevel, disabled}) => ({detailLevel, disabled}))).toEqual([
            {detailLevel: 'compact', disabled: true},
            {detailLevel: 'standard', disabled: false},
            {detailLevel: 'full', disabled: true},
        ]);
        expect(findCompatibleAiExportChoice(compatibility, 'portfolio', 'pac_planning', 'standard')?.detailLevel).toBe('standard');
        expect(findCompatibleAiExportChoice(compatibility, 'portfolio', 'pac_planning', 'full')).toBeUndefined();
    });

    it('classifies final token estimates at UI-only thresholds', () => {
        expect(estimateAiExportTokenSeverity(AI_EXPORT_TOKEN_WARNING_THRESHOLD - 1)).toBe('normal');
        expect(estimateAiExportTokenSeverity(AI_EXPORT_TOKEN_WARNING_THRESHOLD)).toBe('warning');
        expect(estimateAiExportTokenSeverity(AI_EXPORT_TOKEN_LARGE_THRESHOLD - 1)).toBe('warning');
        expect(estimateAiExportTokenSeverity(AI_EXPORT_TOKEN_LARGE_THRESHOLD)).toBe('large');
    });

    it('reconciles unavailable tasks and details without changing an already-compatible detail', () => {
        const pac = PORTFOLIO_AI_EXPORT_TASKS[0];
        const rebalancing = PORTFOLIO_AI_EXPORT_TASKS[1];

        const defaultDetailCompatibility = buildCompatibility([buildChoice(pac, 'compact', 'disabled'), buildChoice(pac, 'standard', 'compatible'), buildChoice(pac, 'full', 'compatible')]);
        expect(reconcileAiExportTaskAndDetail([pac], defaultDetailCompatibility, pac.id, 'compact')).toEqual({
            task: pac.id,
            detailLevel: 'standard',
        });
        expect(reconcileAiExportTaskAndDetail([pac], defaultDetailCompatibility, pac.id, 'full')).toEqual({
            task: pac.id,
            detailLevel: 'full',
        });

        const firstDetailCompatibility = buildCompatibility([buildChoice(pac, 'compact', 'compatible'), buildChoice(pac, 'standard', 'disabled'), buildChoice(pac, 'full', 'compatible')]);
        expect(reconcileAiExportTaskAndDetail([pac], firstDetailCompatibility, pac.id, 'standard')).toEqual({
            task: pac.id,
            detailLevel: 'compact',
        });

        const fallbackTaskCompatibility = buildCompatibility([buildChoice(pac, 'standard', 'disabled'), buildChoice(rebalancing, 'full', 'compatible')]);
        expect(reconcileAiExportTaskAndDetail([pac, rebalancing], fallbackTaskCompatibility, pac.id, 'compact')).toEqual({
            task: rebalancing.id,
            detailLevel: 'full',
        });
    });

    it('migrates hidden analyses to the first compatible visible analysis and preserves Snapshot', () => {
        const assetCompatibility = buildCompatibility(ASSET_AI_EXPORT_TASKS.flatMap((definition) => definition.supportedDetailLevels.map((detailLevel) => buildChoice(definition, detailLevel, 'compatible'))));
        const hiddenAssetTasks = ['asset_snapshot', 'asset_pac_timing_context'] as const;

        expect(reconcileAiExportAnalysisAndDetail(ASSET_AI_EXPORT_TASKS, assetCompatibility, 'asset', 'asset_pac_timing_context', 'full', hiddenAssetTasks)).toEqual({
            task: 'asset_trend_analysis',
            detailLevel: 'full',
            analysis: 'asset_trend_analysis',
        });
        expect(reconcileAiExportAnalysisAndDetail(ASSET_AI_EXPORT_TASKS, assetCompatibility, 'asset', AI_EXPORT_SNAPSHOT_SELECTION_ID, 'compact', hiddenAssetTasks)).toEqual({
            task: 'asset_snapshot',
            detailLevel: 'compact',
            analysis: AI_EXPORT_SNAPSHOT_SELECTION_ID,
        });

        const fxCompatibility = buildCompatibility(FX_AI_EXPORT_TASKS.flatMap((definition) => definition.supportedDetailLevels.map((detailLevel) => buildChoice(definition, detailLevel, 'compatible'))));
        expect(reconcileAiExportAnalysisAndDetail(FX_AI_EXPORT_TASKS, fxCompatibility, 'fx', 'fx_exposure_impact', 'standard', ['fx_exposure_impact'])).toEqual({
            task: 'fx_trend_review',
            detailLevel: 'standard',
            analysis: 'fx_trend_review',
        });
    });

    it('keeps the current disabled selection when no compatible task or detail exists', () => {
        const pac = PORTFOLIO_AI_EXPORT_TASKS[0];
        const compatibility = buildCompatibility([buildChoice(pac, 'standard', 'disabled')]);

        expect(reconcileAiExportTaskAndDetail([pac], compatibility, pac.id, 'full')).toEqual({
            task: pac.id,
            detailLevel: 'full',
        });
    });

    it('allows web research only for supported full-prompt tasks', () => {
        const supported = PORTFOLIO_AI_EXPORT_TASKS[0];
        const unsupported = PORTFOLIO_AI_EXPORT_TASKS[2];

        expect(isAiExportWebResearchAvailable(supported, 'full_prompt')).toBe(true);
        expect(isAiExportWebResearchAvailable(supported, 'data_only')).toBe(false);
        expect(isAiExportWebResearchAvailable(unsupported, 'full_prompt')).toBe(false);
        expect(normalizeAiExportWebResearch(supported, 'full_prompt', true)).toBe(true);
        expect(normalizeAiExportWebResearch(supported, 'data_only', true)).toBe(false);
        expect(normalizeAiExportWebResearch(unsupported, 'full_prompt', true)).toBe(false);
    });

    it('keeps the trigger focusable but non-toggleable while an export is loading', () => {
        expect(getAiExportMenuTriggerBehavior(false, false)).toEqual({
            nativeDisabled: false,
            ariaBusy: false,
            canToggle: true,
        });
        expect(getAiExportMenuTriggerBehavior(false, true)).toEqual({
            nativeDisabled: false,
            ariaBusy: true,
            canToggle: false,
        });
        expect(getAiExportMenuTriggerBehavior(true, false)).toEqual({
            nativeDisabled: true,
            ariaBusy: false,
            canToggle: false,
        });
    });

    it('fingerprints stats context and rejects stale generations even after context returns', () => {
        const context = {
            contextKey: 'asset:7',
            dateStart: '2025-01-01',
            dateEnd: '2025-12-31',
            displayCurrency: 'EUR',
            targetCurrency: 'EUR',
        };
        const fingerprint = aiExportStatsContextFingerprint(context);

        expect(aiExportStatsContextFingerprint({...context})).toBe(fingerprint);
        expect(aiExportStatsContextFingerprint({...context, contextKey: 'asset:8'})).not.toBe(fingerprint);
        expect(aiExportStatsContextFingerprint({...context, dateStart: '2025-02-01'})).not.toBe(fingerprint);
        expect(aiExportStatsContextFingerprint({...context, dateEnd: '2026-01-01'})).not.toBe(fingerprint);
        expect(aiExportStatsContextFingerprint({...context, displayCurrency: 'USD'})).not.toBe(fingerprint);
        expect(aiExportStatsContextFingerprint({...context, targetCurrency: 'USD'})).not.toBe(fingerprint);
        expect(isAiExportStatsRequestCurrent(3, fingerprint, 3, fingerprint)).toBe(true);
        expect(isAiExportStatsRequestCurrent(3, fingerprint, 4, fingerprint)).toBe(false);
        expect(isAiExportStatsRequestCurrent(3, fingerprint, 3, aiExportStatsContextFingerprint({...context, dateEnd: '2026-01-01'}))).toBe(false);
    });

    it('fingerprints every option stably and hides stats for stale fingerprints', () => {
        const options: AiExportOptionsFingerprintInput = {
            task: 'pac_planning',
            detailLevel: 'standard',
            renderMode: 'full_prompt',
            responseLanguage: 'English',
            userNotes: 'Keep fees visible.',
            webResearch: true,
        };
        const fingerprint = aiExportOptionsFingerprint(options);
        const variants: readonly AiExportOptionsFingerprintInput[] = [
            {...options, task: 'rebalancing'},
            {...options, detailLevel: 'full'},
            {...options, renderMode: 'data_only'},
            {...options, responseLanguage: 'Italian'},
            {...options, userNotes: 'Different note.'},
            {...options, webResearch: false},
        ];
        const stats: AiExportPromptStats = {
            finalPrompt: {
                characterCountUtf16CodeUnits: 400,
                estimatedTokens: 100,
                estimationMethod: 'ceil_utf16_code_units_div_4_v1',
            },
            snapshotBackendStats: {
                canonical_json: {
                    positions: 1,
                    technical_assets: 0,
                    series_points: 0,
                    events: 0,
                    serialized_characters: 200,
                },
                token_estimate: {
                    method: 'chars_div_4_v1',
                    estimated_tokens: 50,
                },
            },
        };

        expect(aiExportOptionsFingerprint({...options})).toBe(fingerprint);
        expect(new Set(variants.map(aiExportOptionsFingerprint))).not.toContain(fingerprint);
        expect(getMatchingAiExportStats(stats, fingerprint, fingerprint)).toBe(stats);
        expect(getMatchingAiExportStats(stats, aiExportOptionsFingerprint(variants[0]), fingerprint)).toBeUndefined();
        expect(getMatchingAiExportStats(stats, undefined, fingerprint)).toBeUndefined();
    });
});

function buildCompatibility(choices: readonly AiExportCatalogCompatibilityChoice[]): AiExportCatalogCompatibilityResult {
    const selectableChoices = choices.filter((choice) => choice.status === 'compatible');
    return {
        status: choices.every((choice) => choice.status === 'compatible') ? 'compatible' : 'disabled',
        choices,
        selectableChoices,
        backendOnlyEntries: [],
        reasonCodes: choices.some((choice) => choice.status === 'disabled') ? ['profile_id_mismatch'] : [],
    };
}

function buildChoice(taskDefinition: AiExportTaskDefinition, detailLevel: AiExportDetailLevel, status: 'compatible' | 'disabled'): AiExportCatalogCompatibilityChoice {
    const localChoice = AI_EXPORT_LOCAL_CHOICES.find((choice) => choice.domain === taskDefinition.domain && choice.backendTask === taskDefinition.backendTask && choice.detailLevel === detailLevel);
    if (!localChoice) throw new Error('Missing local AI Export choice');

    return {
        ...localChoice,
        status,
        reasonCode: status === 'compatible' ? null : 'profile_id_mismatch',
        backendEntry: {
            domain: localChoice.domain,
            task: localChoice.backendTask,
            detail_level: detailLevel,
            profile_id: localChoice.profileId,
            profile_version: localChoice.profileVersion,
            frontend_response_contract_id: localChoice.frontendResponseContractId,
            frontend_response_contract_version: localChoice.frontendResponseContractVersion,
            applicability_code: 'always',
            supports_user_notes: localChoice.supportsUserNotes,
            supports_web_research: localChoice.supportsWebResearch,
        },
    };
}
