// @vitest-environment jsdom
/**
 * ExposureTable — component test (Vitest + jsdom).
 *
 * Subject: the F9 analyzed-row highlight. While the lot-analysis panel is open
 * for an asset, the dashboard passes `analyzedAssetId` down and the matching
 * row keeps a steady emerald tint (`tr.row-analyzed`, styled in DataTable's
 * stylesheet) so the user can see which row they are analyzing. The class is
 * the contract here — it is the only handle the persistent tint has.
 *
 * Rows are addressed by `data-row-id` (`makePositionKey(assetId, brokerId)`),
 * never by position: the table sorts by value descending.
 *
 * `assetStore.ensureAssetsLoaded()` fires on mount and fails soft against the
 * mocked `$lib/api` — the row-class decision depends only on props.
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
import ExposureTable from './ExposureTable.svelte';

function holding(asset_id: number, broker_id: number) {
    return {
        asset_id,
        asset_name: `Asset ${asset_id}`,
        asset_type: 'STOCK',
        broker_id,
        broker_name: `Broker ${broker_id}`,
        quantity: '10',
        current_value: String(asset_id * 1000), // distinct values → deterministic sort
    };
}

/** The row for (assetId, brokerId): makePositionKey's "assetId-brokerId". */
function rowEl(assetId: number, brokerId: number): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${assetId}-${brokerId}"]`);
    if (!el) throw new Error(`row ${assetId}-${brokerId} not rendered`);
    return el;
}

beforeAll(async () => {
    await setupI18n();
});

describe('ExposureTable — analyzedAssetId row highlight (F9)', () => {
    it('marks only the analyzed asset row with row-analyzed', async () => {
        render(ExposureTable, {
            holdings: [holding(11, 1), holding(22, 1), holding(33, 2)],
            navAmount: 6000,
            displayCurrency: 'EUR',
            analyzedAssetId: 22,
        });

        // Barrier: all three rows rendered before reading any class.
        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(3));

        expect(rowEl(22, 1).className).toContain('row-analyzed');
        expect(rowEl(11, 1).className).not.toContain('row-analyzed');
        expect(rowEl(33, 2).className).not.toContain('row-analyzed');
    });

    it('marks nothing when no analysis is open (analyzedAssetId null/absent)', async () => {
        render(ExposureTable, {
            holdings: [holding(11, 1), holding(22, 1)],
            navAmount: 3000,
            displayCurrency: 'EUR',
            analyzedAssetId: null,
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(2));

        expect(document.querySelector('tbody tr.row-analyzed')).toBeNull();
    });

    it('moves the tint when the analyzed asset changes', async () => {
        const {rerender} = render(ExposureTable, {
            holdings: [holding(11, 1), holding(22, 1)],
            navAmount: 3000,
            displayCurrency: 'EUR',
            analyzedAssetId: 11,
        });

        await waitFor(() => expect(rowEl(11, 1).className).toContain('row-analyzed'));

        await rerender({
            holdings: [holding(11, 1), holding(22, 1)],
            navAmount: 3000,
            displayCurrency: 'EUR',
            analyzedAssetId: 22,
        });

        await waitFor(() => expect(rowEl(22, 1).className).toContain('row-analyzed'));
        expect(rowEl(11, 1).className).not.toContain('row-analyzed');
    });
});
