import {afterEach, describe, expect, it, vi} from 'vitest';

import {AiExportContractMismatchError, type AiExportBackendExportStats, type AiExportSnapshotRequest, type AiExportSnapshotResponse} from '../aiExportClient';
import {AiExportChoiceUnavailableError, copyAiExportV2, prepareAiExportV2, writePreparedAiExportV2, type AiExportV2PromptRenderer, type AiExportV2SnapshotFetcher, type CopyAiExportV2Input} from '../aiExportClipboardV2';
import type {AiExportCatalogCompatibilityChoice, AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {AI_EXPORT_LOCAL_CHOICES} from '../catalog/compatibility';
import type {AiExportDetailLevel, AiExportDomain, AiExportTask} from '../catalog/shared';
import {AI_EXPORT_TOKEN_LARGE_THRESHOLD, aiExportOptionsFingerprint} from '../aiExportOptions';
import {AiExportPromptRenderError, type RenderedAiExportPrompt} from '../templates/promptRenderer';

const EXPORT_STATS: AiExportBackendExportStats = {
    canonical_json: {
        positions: 2,
        technical_assets: 1,
        series_points: 7,
        events: 3,
        serialized_characters: 1200,
    },
    token_estimate: {
        method: 'chars_div_4_v1',
        estimated_tokens: 300,
    },
};

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('AI Export v2 clipboard orchestration', () => {
    it('builds canonical requests and returns snapshots for all four request contexts', async () => {
        const scenarios: Array<{
            input: CopyAiExportV2Input;
            expectedRequest: AiExportSnapshotRequest;
        }> = [
            {
                input: {
                    context: {
                        domain: 'portfolio',
                        dateRange: {start: '2026-01-01'},
                        targetCurrency: ' eur ',
                        brokerIds: [9, 3],
                    },
                    task: 'portfolio_description',
                    detailLevel: 'standard',
                    renderMode: 'full_prompt',
                    responseLanguage: 'English',
                },
                expectedRequest: {
                    domain: 'portfolio',
                    task: 'portfolio_description',
                    detail_level: 'standard',
                    date_range: {start: '2026-01-01', end: '2026-01-01'},
                    target_currency: 'EUR',
                    broker_ids: [3, 9],
                },
            },
            {
                input: {
                    context: {
                        domain: 'asset',
                        dateRange: {start: '2026-02-01', end: '2026-06-30'},
                        targetCurrency: ' usd ',
                        assetId: 42,
                        brokerIds: [2, 1],
                    },
                    task: 'asset_snapshot',
                    detailLevel: 'compact',
                    renderMode: 'data_only',
                    responseLanguage: 'Italian',
                },
                expectedRequest: {
                    domain: 'asset',
                    task: 'asset_snapshot',
                    detail_level: 'compact',
                    date_range: {start: '2026-02-01', end: '2026-06-30'},
                    target_currency: 'USD',
                    asset_id: 42,
                    broker_ids: [1, 2],
                },
            },
            {
                input: {
                    context: {
                        domain: 'fx',
                        dateRange: {start: '2026-03-01', end: null},
                        targetCurrency: ' eur ',
                        baseCurrency: ' usd ',
                        quoteCurrency: ' gbp ',
                    },
                    task: 'fx_trend_review',
                    detailLevel: 'full',
                    renderMode: 'full_prompt',
                    responseLanguage: 'French',
                },
                expectedRequest: {
                    domain: 'fx',
                    task: 'fx_trend_review',
                    detail_level: 'full',
                    date_range: {start: '2026-03-01', end: '2026-03-01'},
                    target_currency: 'EUR',
                    base_currency: 'USD',
                    quote_currency: 'GBP',
                    broker_ids: undefined,
                },
            },
            {
                input: {
                    context: {
                        domain: 'broker',
                        dateRange: {start: '2026-04-01', end: '2026-05-31'},
                        targetCurrency: ' chf ',
                        brokerId: 7,
                    },
                    task: 'broker_review',
                    detailLevel: 'standard',
                    renderMode: 'full_prompt',
                    responseLanguage: 'Spanish',
                },
                expectedRequest: {
                    domain: 'broker',
                    task: 'broker_review',
                    detail_level: 'standard',
                    date_range: {start: '2026-04-01', end: '2026-05-31'},
                    target_currency: 'CHF',
                    broker_id: 7,
                },
            },
        ];
        const compatibility = buildCompatibility(scenarios.map(({input}) => buildChoice(input.context.domain, input.task, input.detailLevel, 'compatible')));

        for (const scenario of scenarios) {
            const snapshot = buildSnapshot(scenario.expectedRequest);
            const fetchSnapshot = vi.fn<AiExportV2SnapshotFetcher>(async () => snapshot);
            const rendered = buildRenderedPrompt(`prompt:${scenario.input.context.domain}`, snapshot);
            const renderPrompt = vi.fn<AiExportV2PromptRenderer>(() => rendered);
            const writeClipboard = vi.fn(async () => undefined);

            const result = await copyAiExportV2({...scenario.input, compatibility}, {fetchSnapshot, renderPrompt, writeClipboard});

            expect(fetchSnapshot).toHaveBeenCalledOnce();
            expect(fetchSnapshot.mock.calls[0][0]).toEqual(scenario.expectedRequest);
            expect(writeClipboard).toHaveBeenCalledOnce();
            expect(writeClipboard).toHaveBeenCalledWith(rendered.prompt);
            expect(result.snapshot).toBe(snapshot);
            expect(result.renderedPrompt).toBe(rendered);
            expect(result.prompt).toBe(rendered.prompt);
            expect(result.backendStats).toBe(EXPORT_STATS);
            expect(result.finalStats).toBe(rendered.stats.finalPrompt);
            expect(result.task).toBe(scenario.input.task);
            expect(result.detailLevel).toBe(scenario.input.detailLevel);
            expect(result.renderMode).toBe(scenario.input.renderMode);
            expect(result.optionsFingerprint).toBe(
                aiExportOptionsFingerprint({
                    task: scenario.input.task,
                    detailLevel: scenario.input.detailLevel,
                    renderMode: scenario.input.renderMode,
                    responseLanguage: scenario.input.responseLanguage,
                    userNotes: scenario.input.userNotes,
                    webResearch: scenario.input.renderMode === 'full_prompt' && scenario.input.webResearch === true,
                }),
            );
        }
    });

    it('reuses supplied compatibility and loads it only when absent', async () => {
        const input = buildBaseInput();
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const dependencies = {
            loadCatalogCompatibility: vi.fn(async () => compatibility),
            fetchSnapshot: vi.fn<AiExportV2SnapshotFetcher>(async () => snapshot),
            renderPrompt: vi.fn<AiExportV2PromptRenderer>(() => buildRenderedPrompt('loaded', snapshot)),
            writeClipboard: vi.fn(async () => undefined),
        };

        await copyAiExportV2({...input, compatibility}, dependencies);
        expect(dependencies.loadCatalogCompatibility).not.toHaveBeenCalled();

        await copyAiExportV2(input, dependencies);
        expect(dependencies.loadCatalogCompatibility).toHaveBeenCalledOnce();
    });

    it('prepares without writing and writes the exact prompt only when explicitly requested', async () => {
        const input = buildBaseInput();
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const rendered = buildRenderedPrompt('prepared exact prompt', snapshot);
        const writer = vi.fn(async () => undefined);

        const result = await prepareAiExportV2(
            {...input, compatibility},
            {
                fetchSnapshot: async () => snapshot,
                renderPrompt: () => rendered,
            },
        );

        expect(writer).not.toHaveBeenCalled();
        await writePreparedAiExportV2(result, writer);
        expect(writer).toHaveBeenCalledOnce();
        expect(writer).toHaveBeenCalledWith(rendered.prompt);
    });

    it('starts modern clipboard.write before snapshot resolution and resolves its Blob to the exact final text', async () => {
        const input = buildBaseInput();
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const rendered = buildRenderedPrompt('modern clipboard exact prompt', snapshot);
        let resolveSnapshot: ((value: AiExportSnapshotResponse) => void) | undefined;
        let snapshotResolved = false;
        const fetchSnapshot = vi.fn<AiExportV2SnapshotFetcher>(
            () =>
                new Promise((resolve) => {
                    resolveSnapshot = (value) => {
                        snapshotResolved = true;
                        resolve(value);
                    };
                }),
        );
        let clipboardData: Record<string, Promise<Blob>> | undefined;
        class TestClipboardItem {
            constructor(data: Record<string, Promise<Blob>>) {
                clipboardData = data;
            }
        }
        const write = vi.fn(async () => {
            expect(snapshotResolved).toBe(false);
        });
        vi.stubGlobal('ClipboardItem', TestClipboardItem);
        vi.stubGlobal('navigator', {clipboard: {write}});

        const copyPromise = copyAiExportV2(
            {...input, compatibility},
            {
                fetchSnapshot,
                renderPrompt: () => rendered,
            },
        );

        expect(fetchSnapshot).toHaveBeenCalledOnce();
        expect(write).toHaveBeenCalledOnce();
        expect(snapshotResolved).toBe(false);
        expect(clipboardData?.['text/plain']).toBeInstanceOf(Promise);

        resolveSnapshot?.(snapshot);
        const result = await copyPromise;
        const blob = await clipboardData?.['text/plain'];

        expect(result.prompt).toBe(rendered.prompt);
        expect(blob).toBeInstanceOf(Blob);
        expect(blob?.type).toBe('text/plain');
        expect(await blob?.text()).toBe(rendered.prompt);
    });

    it('prepares once and writes the exact prompt via writeText when modern clipboard APIs are unavailable', async () => {
        const input = buildBaseInput();
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const rendered = buildRenderedPrompt('generic clipboard fallback prompt', snapshot);
        const fetchSnapshot = vi.fn<AiExportV2SnapshotFetcher>(async () => snapshot);
        const renderPrompt = vi.fn<AiExportV2PromptRenderer>(() => rendered);
        const writeText = vi.fn(async () => undefined);
        vi.stubGlobal('ClipboardItem', undefined);
        vi.stubGlobal('navigator', {clipboard: {writeText}});

        const result = await copyAiExportV2({...input, compatibility}, {fetchSnapshot, renderPrompt});

        expect(fetchSnapshot).toHaveBeenCalledOnce();
        expect(renderPrompt).toHaveBeenCalledOnce();
        expect(writeText).toHaveBeenCalledOnce();
        expect(writeText).toHaveBeenCalledWith(rendered.prompt);
        expect(result.prompt).toBe(rendered.prompt);
    });

    it('fails with a typed clipboard error after preparing when no transport is available', async () => {
        const input = buildBaseInput();
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const fetchSnapshot = vi.fn<AiExportV2SnapshotFetcher>(async () => snapshot);
        const renderPrompt = vi.fn<AiExportV2PromptRenderer>(() => buildRenderedPrompt('unavailable clipboard prompt', snapshot));
        vi.stubGlobal('ClipboardItem', undefined);
        vi.stubGlobal('navigator', {});
        vi.stubGlobal('document', undefined);

        await expect(copyAiExportV2({...input, compatibility}, {fetchSnapshot, renderPrompt})).rejects.toMatchObject({
            name: 'AiExportClipboardUnavailableError',
            kind: 'clipboard_unavailable',
        });
        expect(fetchSnapshot).toHaveBeenCalledOnce();
        expect(renderPrompt).toHaveBeenCalledOnce();
    });

    it('passes user notes and supported full-prompt web research to the renderer', async () => {
        const input = {
            ...buildBaseInput(),
            userNotes: 'Compare fees; preserve this exact note.',
            webResearch: true,
        };
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const renderPrompt = vi.fn<AiExportV2PromptRenderer>(() => buildRenderedPrompt('notes', snapshot));

        await copyAiExportV2(
            {...input, compatibility},
            {
                fetchSnapshot: async () => snapshot,
                renderPrompt,
                writeClipboard: async () => undefined,
            },
        );

        expect(renderPrompt).toHaveBeenCalledOnce();
        expect(renderPrompt.mock.calls[0][0]).toMatchObject({
            userNotes: input.userNotes,
            webResearch: true,
            renderMode: input.renderMode,
            responseLanguage: input.responseLanguage,
        });
    });

    it('forces notes and web research off for data-only preparation and fingerprints the effective options', async () => {
        const input = {
            ...buildBaseInput(),
            renderMode: 'data_only' as const,
            userNotes: 'Hidden Snapshot note',
            webResearch: true,
        };
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const renderPrompt = vi.fn<AiExportV2PromptRenderer>(() => buildRenderedPrompt('data only', snapshot));

        const result = await prepareAiExportV2(
            {...input, compatibility},
            {
                fetchSnapshot: async () => snapshot,
                renderPrompt,
            },
        );

        expect(renderPrompt.mock.calls[0][0].userNotes).toBeUndefined();
        expect(renderPrompt.mock.calls[0][0].webResearch).toBe(false);
        expect(result.optionsFingerprint).toBe(
            aiExportOptionsFingerprint({
                task: input.task,
                detailLevel: input.detailLevel,
                renderMode: input.renderMode,
                responseLanguage: input.responseLanguage,
                userNotes: undefined,
                webResearch: false,
            }),
        );
    });

    it('fails closed with a typed unavailable error and never enters another export path', async () => {
        const input = buildBaseInput();
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'disabled')]);
        const fetchSnapshot = vi.fn<AiExportV2SnapshotFetcher>();
        const renderPrompt = vi.fn<AiExportV2PromptRenderer>();
        const writeClipboard = vi.fn();

        await expect(copyAiExportV2({...input, compatibility}, {fetchSnapshot, renderPrompt, writeClipboard})).rejects.toMatchObject({
            name: 'AiExportChoiceUnavailableError',
            kind: 'choice_unavailable',
            reason: 'catalog_choice_incompatible',
            domain: 'portfolio',
            task: 'pac_planning',
            detailLevel: 'standard',
        } satisfies Partial<AiExportChoiceUnavailableError>);
        expect(fetchSnapshot).not.toHaveBeenCalled();
        expect(renderPrompt).not.toHaveBeenCalled();
        expect(writeClipboard).not.toHaveBeenCalled();
    });

    it('propagates catalog, client contract, render, and clipboard failures', async () => {
        const input = buildBaseInput();
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'standard', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const catalogError = new Error('catalog failed');
        await expect(
            prepareAiExportV2(input, {
                loadCatalogCompatibility: async () => {
                    throw catalogError;
                },
            }),
        ).rejects.toBe(catalogError);

        const contractError = new AiExportContractMismatchError([{field: 'response.domain', expected: 'portfolio', actual: 'asset'}]);
        await expect(
            prepareAiExportV2(
                {...input, compatibility},
                {
                    fetchSnapshot: async () => {
                        throw contractError;
                    },
                },
            ),
        ).rejects.toBe(contractError);

        const renderError = new AiExportPromptRenderError('incompatible_contract', 'render failed');
        const writerAfterRenderFailure = vi.fn();
        await expect(
            copyAiExportV2(
                {...input, compatibility},
                {
                    fetchSnapshot: async () => snapshot,
                    renderPrompt: () => {
                        throw renderError;
                    },
                    writeClipboard: writerAfterRenderFailure,
                },
            ),
        ).rejects.toBe(renderError);
        expect(writerAfterRenderFailure).not.toHaveBeenCalled();

        const order: string[] = [];
        const clipboardError = new Error('clipboard failed');
        await expect(
            copyAiExportV2(
                {...input, compatibility},
                {
                    fetchSnapshot: async () => {
                        order.push('snapshot');
                        return snapshot;
                    },
                    renderPrompt: () => {
                        order.push('render');
                        return buildRenderedPrompt('clipboard', snapshot);
                    },
                    writeClipboard: async () => {
                        order.push('clipboard');
                        throw clipboardError;
                    },
                },
            ),
        ).rejects.toBe(clipboardError);
        expect(order).toEqual(['snapshot', 'render', 'clipboard']);
    });

    it('keeps the default input type correlated by domain and task', () => {
        const invalidInput = {
            context: {
                domain: 'portfolio',
                dateRange: {start: '2026-01-01', end: '2026-06-30'},
                targetCurrency: 'EUR',
            },
            task: 'asset_snapshot',
            detailLevel: 'standard',
            renderMode: 'full_prompt',
            responseLanguage: 'English',
        } as const;

        // @ts-expect-error Portfolio context cannot use an asset-only task.
        acceptCopyAiExportV2Input(invalidInput);
        expect(invalidInput.task).toBe('asset_snapshot');
    });

    it('copies a large full-detail prompt exactly once without truncating or changing detail', async () => {
        const prompt = 'x'.repeat(AI_EXPORT_TOKEN_LARGE_THRESHOLD * 4 + 17);
        const input = {
            ...buildBaseInput(),
            detailLevel: 'full' as const,
        };
        const compatibility = buildCompatibility([buildChoice('portfolio', 'pac_planning', 'full', 'compatible')]);
        const snapshot = buildSnapshot({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'full',
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
            broker_ids: undefined,
        });
        const rendered = buildRenderedPrompt(prompt, snapshot);
        const writeClipboard = vi.fn(async () => undefined);

        const result = await copyAiExportV2(
            {...input, compatibility},
            {
                fetchSnapshot: async () => snapshot,
                renderPrompt: () => rendered,
                writeClipboard,
            },
        );

        expect(writeClipboard).toHaveBeenCalledOnce();
        expect(writeClipboard).toHaveBeenCalledWith(prompt);
        expect(result.prompt).toHaveLength(prompt.length);
        expect(result.detailLevel).toBe('full');
        expect(result.finalStats.estimatedTokens).toBe(Math.ceil(prompt.length / 4));
    });
});

function acceptCopyAiExportV2Input(_input: CopyAiExportV2Input): void {}

function buildBaseInput(): CopyAiExportV2Input {
    return {
        context: {
            domain: 'portfolio',
            dateRange: {start: '2026-01-01', end: '2026-06-30'},
            targetCurrency: 'EUR',
        },
        task: 'pac_planning',
        detailLevel: 'standard',
        renderMode: 'full_prompt',
        responseLanguage: 'English',
    };
}

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

function buildChoice(domain: AiExportDomain, task: AiExportTask, detailLevel: AiExportDetailLevel, status: 'compatible' | 'disabled'): AiExportCatalogCompatibilityChoice {
    const localChoice = AI_EXPORT_LOCAL_CHOICES.find((choice) => choice.domain === domain && choice.backendTask === task && choice.detailLevel === detailLevel);
    if (!localChoice) throw new Error(`Missing local choice for ${domain}.${task}.${detailLevel}`);

    return {
        ...localChoice,
        status,
        reasonCode: status === 'compatible' ? null : 'profile_id_mismatch',
        backendEntry: {
            domain,
            task,
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

function buildSnapshot(request: AiExportSnapshotRequest): AiExportSnapshotResponse {
    return {
        domain: request.domain,
        task: request.task,
        detail_level: request.detail_level,
        export_stats: EXPORT_STATS,
    } as AiExportSnapshotResponse;
}

function buildRenderedPrompt(prompt: string, snapshot: AiExportSnapshotResponse): RenderedAiExportPrompt {
    return {
        prompt,
        stats: {
            finalPrompt: {
                characterCountUtf16CodeUnits: prompt.length,
                estimatedTokens: Math.ceil(prompt.length / 4),
                estimationMethod: 'ceil_utf16_code_units_div_4_v1',
            },
            snapshotBackendStats: snapshot.export_stats,
        },
    };
}
