// @vitest-environment jsdom
/**
 * ContributionTable — component test (Vitest + jsdom).
 *
 * Subject: the same F9 analyzed-row highlight as ExposureTable, on the
 * performance (contribution) twin of the dashboard tables. A sold row renders
 * italic through the same `getRowClass`, so the two classes must compose, not
 * overwrite each other.
 *
 * Rows are addressed by `data-row-id` (`pos-{brokerId}-{assetId}`), never by
 * position.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {render, setupI18n, waitFor} from '$test/component';
import ContributionTable from './ContributionTable.svelte';

function position(asset_id: number, broker_id: number, opts: {is_fully_sold?: boolean} = {}) {
    return {
        asset_id,
        asset_name: `Asset ${asset_id}`,
        asset_type: 'STOCK',
        broker_id,
        broker_name: `Broker ${broker_id}`,
        period_pnl: '100',
        start_value: '1000',
        end_value: '1100',
        is_fully_sold: opts.is_fully_sold ?? false,
    };
}

function rowEl(assetId: number, brokerId: number): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="pos-${brokerId}-${assetId}"]`);
    if (!el) throw new Error(`row pos-${brokerId}-${assetId} not rendered`);
    return el;
}

beforeAll(async () => {
    await setupI18n();
});

describe('ContributionTable — analyzedAssetId row highlight (F9)', () => {
    it('marks only the analyzed asset row with row-analyzed', async () => {
        render(ContributionTable, {
            positions: [position(11, 1), position(22, 1), position(33, 2)],
            analyzedAssetId: 33,
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(3));

        expect(rowEl(33, 2).className).toContain('row-analyzed');
        expect(rowEl(11, 1).className).not.toContain('row-analyzed');
        expect(rowEl(22, 1).className).not.toContain('row-analyzed');
    });

    it('composes with the italic of a fully-sold row instead of overwriting it', async () => {
        render(ContributionTable, {
            positions: [position(11, 1, {is_fully_sold: true})],
            analyzedAssetId: 11,
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(1));

        const cls = rowEl(11, 1).className;
        expect(cls).toContain('row-analyzed');
        expect(cls).toContain('italic');
    });
});
