import {describe, expect, it, vi} from 'vitest';

import {buildAiExportSnapshotRequest, copyAiExport, prepareAiExport, writePreparedAiExport} from '../aiExportClipboard';
import {compatibilityFixture, selectionFixture, snapshotFixture} from './runtimeFixtures';

const options = {
    selectionKind: 'analysis' as const,
    selectionId: 'asset.drawdown_recovery' as const,
    detailLevel: 'standard' as const,
    period: {preset: '3m' as const, customAmount: 3, customUnit: 'months' as const},
    responseLanguage: 'English' as const,
    userNotes: 'Focus',
};

describe('AI Export clipboard orchestration', () => {
    it('builds the new selection/period request contract', () => {
        const selection = selectionFixture('analysis', 'asset.drawdown_recovery');
        const request = buildAiExportSnapshotRequest({domain: 'asset', assetId: 7, snapshotAsOf: '2026-03-31', targetCurrency: 'eur'}, options, selection);

        expect(request).toMatchObject({
            domain: 'asset',
            asset_id: 7,
            period: {start: '2025-12-31', end: '2026-03-31'},
            selection: {kind: 'analysis', id: 'asset.drawdown_recovery'},
        });
    });

    it('prepares once and writes the already-prepared prompt without another request', async () => {
        const selection = selectionFixture('analysis', 'asset.drawdown_recovery');
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

    it('copyAiExport prepares and copies in one call for normal-size payloads', async () => {
        const selection = selectionFixture('analysis', 'asset.drawdown_recovery');
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
