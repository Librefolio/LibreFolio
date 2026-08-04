import {describe, expect, it, vi} from 'vitest';

import {buildAiExportSnapshotRequest, copyAiExport, prepareAiExport, writePreparedAiExport} from '../aiExportClipboard';
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
        expect(prepared.prompt).not.toContain('## User Notes');
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
});
