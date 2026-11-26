import {afterEach, describe, expect, it, vi} from 'vitest';

import {AiExportClipboardUnavailableError, buildAiExportSnapshotRequest, copyAiExport, defaultAiExportClipboardWriter, prepareAiExport, writePreparedAiExport} from '../aiExportClipboard';
import {aiExportOptionsFingerprint} from '../aiExportOptions';
import {compatibilityFixture, selectionFixture, snapshotFixture} from './runtimeFixtures';

const options = {
    selectionKind: 'analysis' as const,
    selectionId: 'asset.market_analysis' as const,
    detailLevel: 'standard' as const,
    period: {preset: '3m' as const, customAmount: 3, customUnit: 'months' as const},
    responseLanguage: 'English' as const,
    userNotes: 'Focus',
};

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('AI Export clipboard orchestration', () => {
    it('builds the new selection/period request contract', () => {
        const selection = selectionFixture('analysis', 'asset.market_analysis');
        const request = buildAiExportSnapshotRequest({domain: 'asset', assetId: 7, snapshotAsOf: '2026-03-31', targetCurrency: 'eur'}, options, selection);

        expect(request).toMatchObject({
            domain: 'asset',
            asset_id: 7,
            period: {start: '2025-12-31', end: '2026-03-31'},
            selection: {kind: 'analysis', id: 'asset.market_analysis'},
        });
    });

    it('prepares once and writes the already-prepared prompt without another request', async () => {
        const selection = selectionFixture('analysis', 'asset.market_analysis');
        const transport = vi.fn(async (request) => snapshotFixture(selection, request.detail_level, request.period));
        const prepared = await prepareAiExport(
            {
                context: {domain: 'asset', assetId: 7, snapshotAsOf: '2026-03-31', targetCurrency: 'EUR'},
                options,
                compatibility: compatibilityFixture(),
            },
            {transport},
        );
        const writer = vi.fn();
        await writePreparedAiExport(prepared, writer);

        expect(transport).toHaveBeenCalledTimes(1);
        expect(writer).toHaveBeenCalledWith(prepared.prompt);
    });

    it('strips hidden Analysis notes from Dataset requests, prompts, and fingerprints', async () => {
        const hiddenNote = 'ANALYSIS_ONLY_NOTE';
        const selection = selectionFixture('dataset', 'portfolio.overview_and_history');
        const datasetOptions = {
            selectionKind: 'dataset' as const,
            selectionId: 'portfolio.overview_and_history' as const,
            detailLevel: 'standard' as const,
            period: {preset: '3m' as const, customAmount: 3, customUnit: 'months' as const},
            responseLanguage: 'English' as const,
            userNotes: hiddenNote,
        };
        const transport = vi.fn(async (request) => snapshotFixture(selection, request.detail_level, request.period));
        const prepared = await prepareAiExport(
            {
                context: {domain: 'portfolio', snapshotAsOf: '2026-03-31', targetCurrency: 'EUR'},
                options: datasetOptions,
                compatibility: compatibilityFixture(),
            },
            {transport},
        );

        expect(transport.mock.calls[0][0]).not.toHaveProperty('userNotes');
        expect(prepared.options.userNotes).toBeUndefined();
        expect(prepared.prompt).not.toContain(hiddenNote);
        expect(prepared.optionsFingerprint).toBe(aiExportOptionsFingerprint({...datasetOptions, userNotes: undefined}));
    });

    it('copyAiExport prepares and copies in one call for normal-size payloads', async () => {
        const selection = selectionFixture('analysis', 'asset.market_analysis');
        const writer = vi.fn();
        const result = await copyAiExport(
            {
                context: {domain: 'asset', assetId: 7, snapshotAsOf: '2026-03-31', targetCurrency: 'EUR'},
                options,
                compatibility: compatibilityFixture(),
            },
            {transport: async (request) => snapshotFixture(selection, request.detail_level, request.period), writer},
        );

        expect(result.prompt).not.toBe('');
        expect(writer).toHaveBeenCalledOnce();
    });

    it('tells the steps as they begin, the request before the rendering', async () => {
        const selection = selectionFixture('analysis', 'asset.market_analysis');
        const order: string[] = [];
        await prepareAiExport(
            {context: {domain: 'asset', assetId: 7, snapshotAsOf: '2026-03-31', targetCurrency: 'EUR'}, options, compatibility: compatibilityFixture()},
            {
                transport: async (request) => {
                    order.push('transport');
                    return snapshotFixture(selection, request.detail_level, request.period);
                },
                onstep: (step) => order.push(step),
            },
        );
        // The copy is the caller's step: preparing reports the request and the rendering, nothing else
        expect(order).toEqual(['request', 'transport', 'render']);
    });

    /** The refusals of the default writer: the shared one, on a page with no working transport. */
    async function refusal(hasFocus: boolean): Promise<AiExportClipboardUnavailableError> {
        const denied = Object.assign(new Error('Permission denied'), {name: 'NotAllowedError'});
        const writeText = vi.fn().mockRejectedValue(denied);
        vi.stubGlobal('navigator', {clipboard: {writeText}});
        vi.stubGlobal('window', {isSecureContext: true});
        vi.stubGlobal('document', {hasFocus: () => hasFocus, activeElement: null, body: {appendChild: () => {}}, createElement: () => ({style: {}, focus: () => {}, select: () => {}, setSelectionRange: () => {}, remove: () => {}})});
        vi.stubGlobal('HTMLElement', class {});
        const error = await defaultAiExportClipboardWriter('prompt').catch((caught: unknown) => caught);
        expect(error).toBeInstanceOf(AiExportClipboardUnavailableError);
        expect(writeText).toHaveBeenCalledWith('prompt');
        expect(error).toMatchObject({name: 'AiExportClipboardUnavailableError', kind: 'clipboard_unavailable', cause: denied});
        return error as AiExportClipboardUnavailableError;
    }

    it('surfaces a refusal as a typed unavailable error, for a permission', async () => {
        expect((await refusal(true)).reason).toBe('refused');
    });

    it('says when the window simply was not the active one', async () => {
        expect((await refusal(false)).reason).toBe('not_focused');
    });
});
