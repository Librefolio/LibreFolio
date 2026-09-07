import {describe, expect, it, vi} from 'vitest';

import {AiExportContractMismatchError, AiExportUnknownError, AiExportValidationError, canonicalizeAiExportSnapshotRequest, fetchAiExportSnapshot, normalizeAiExportClientError, type AiExportSnapshotRequestInput} from '../aiExportClient';
import {AI_EXPORT_CATALOG_VERSION, AI_EXPORT_SELECTION_VERSION} from '../catalog/shared';
import {selectionFixture, snapshotFixture} from './runtimeFixtures';

function requestFixture(): AiExportSnapshotRequestInput {
    return {
        domain: 'asset',
        selection: {
            kind: 'analysis',
            id: 'asset.market_analysis',
            version: AI_EXPORT_SELECTION_VERSION,
            instruction_template_id: 'asset.market_analysis.instructions',
            instruction_template_version: AI_EXPORT_SELECTION_VERSION,
            response_contract_id: 'asset.market_analysis.response',
            response_contract_version: AI_EXPORT_SELECTION_VERSION,
        },
        detail_level: 'standard',
        period: {start: '2026-01-01', end: '2026-03-31'},
        target_currency: ' eur ',
        expected_catalog_version: AI_EXPORT_CATALOG_VERSION,
        asset_id: 7,
        broker_ids: [3, 1],
    };
}

describe('AI Export client', () => {
    it('canonicalizes currencies and broker scope without changing selection identity', () => {
        expect(canonicalizeAiExportSnapshotRequest(requestFixture())).toMatchObject({
            target_currency: 'EUR',
            broker_ids: [1, 3],
            selection: {
                kind: 'analysis',
                id: 'asset.market_analysis',
            },
        });
    });

    it('validates request, response, and catalog handshake', async () => {
        const selection = selectionFixture('analysis', 'asset.market_analysis');
        const expected = snapshotFixture(selection);
        const requests: AiExportSnapshotRequestInput[] = [];
        const transport = vi.fn(async (request: AiExportSnapshotRequestInput) => {
            requests.push(request);
            return expected;
        });

        const response = await fetchAiExportSnapshot(requestFixture(), selection, transport);

        expect(response.selection.id).toBe('asset.market_analysis');
        expect(transport).toHaveBeenCalledOnce();
        expect(requests[0]?.target_currency).toBe('EUR');
    });

    it('fails closed when local choice and request differ', async () => {
        const wrongSelection = selectionFixture('analysis', 'asset.position_review');

        await expect(fetchAiExportSnapshot(requestFixture(), wrongSelection, async () => snapshotFixture(wrongSelection))).rejects.toBeInstanceOf(AiExportContractMismatchError);
    });

    it('rejects malformed responses before prompt rendering', async () => {
        const selection = selectionFixture('analysis', 'asset.market_analysis');

        await expect(fetchAiExportSnapshot(requestFixture(), selection, async () => ({domain: 'asset'}))).rejects.toBeInstanceOf(AiExportValidationError);
    });

    it('normalizes unknown transport errors', () => {
        expect(normalizeAiExportClientError(new Error('boom'))).toBeInstanceOf(AiExportUnknownError);
    });
});
