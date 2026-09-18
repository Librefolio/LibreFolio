// @vitest-environment jsdom
/**
 * AssetTable — component test (Vitest + jsdom).
 *
 * Subjects: the F15 usage badge plus lifecycle filtering, ordering and the
 * inactive table/card treatments. Their colours ARE the features — usage scope
 * and lifecycle are communicated visually at a glance — so here, exceptionally,
 * assertions read the class tokens that deliver those contracts. Behaviour is
 * still located by semantic attributes and deterministic ids, never by position.
 *
 * The store loaders the component kicks off (`ensureCurrenciesLoaded`,
 * `ensureAssetProvidersCached`) are fail-soft by design, so a `$lib/api` mock
 * whose calls resolve to `undefined` leaves the table rendering with empty
 * reference caches — which is exactly the state under test: the badge depends
 * on `txScope`/`txCount` props alone.
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

import {render, screen, setupI18n, waitFor} from '$test/component';
import AssetCard from './AssetCard.svelte';
import AssetTable, {type AssetRow} from './AssetTable.svelte';
import {matchesAssetLifecycle, orderAssetsByLifecycle} from './assetLifecycle';

function row(id: number, txCount: number, txScope: AssetRow['txScope'], active = true): AssetRow {
    return {
        id,
        display_name: `Asset ${id}`,
        currency: 'EUR',
        asset_type: 'STOCK',
        active,
        txCount,
        txScope,
    };
}

/** The one row of the mounted table, by the id this test gave it. */
function rowEl(id: number): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${id}"]`);
    if (!el) throw new Error(`row ${id} not rendered`);
    return el;
}

/** The badge span in the row's txCount cell, or null. */
function badgeIn(rowElement: HTMLElement): HTMLElement | null {
    return rowElement.querySelector<HTMLElement>('td.td-data span.font-mono');
}

beforeAll(async () => {
    await setupI18n();
});

describe('asset lifecycle', () => {
    it.each([
        {
            label: 'active only',
            showActive: true,
            showInactive: false,
            expected: ['active'],
        },
        {
            label: 'inactive only',
            showActive: false,
            showInactive: true,
            expected: ['inactive'],
        },
        {
            label: 'both toggles form a union',
            showActive: true,
            showInactive: true,
            expected: ['active', 'inactive'],
        },
        {
            label: 'neither toggle means no lifecycle filter',
            showActive: false,
            showInactive: false,
            expected: ['active', 'inactive'],
        },
    ])('$label', ({showActive, showInactive, expected}) => {
        const assets = [
            {name: 'active', active: true},
            {name: 'inactive', active: false},
        ];

        expect(assets.filter((asset) => matchesAssetLifecycle(asset.active, showActive, showInactive)).map((asset) => asset.name)).toEqual(expected);
    });

    it('orders active assets first while preserving the prior name order within each group', () => {
        const nameOrdered = [
            {id: 1, name: 'Alpha inactive', active: false},
            {id: 2, name: 'Bravo active', active: true},
            {id: 3, name: 'Charlie active', active: true},
            {id: 4, name: 'Delta inactive', active: false},
        ];

        expect(orderAssetsByLifecycle(nameOrdered).map((asset) => asset.name)).toEqual(['Bravo active', 'Charlie active', 'Alpha inactive', 'Delta inactive']);
        expect(nameOrdered.map((asset) => asset.name)).toEqual(['Alpha inactive', 'Bravo active', 'Charlie active', 'Delta inactive']);
    });

    it('marks only the inactive table row and keeps both lifecycle status dots', async () => {
        render(AssetTable, {
            data: [row(21, 1, 'own'), row(22, 0, 'analysis', false)],
        });

        await waitFor(() => {
            expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(2);
        });

        const active = rowEl(21);
        const inactive = rowEl(22);
        expect(active).not.toHaveClass('asset-row-inactive');
        expect(inactive).toHaveClass('asset-row-inactive');
        expect(active.querySelector('span.w-2.h-2.rounded-full.bg-emerald-500')).not.toBeNull();
        expect(inactive.querySelector('span.w-2.h-2.rounded-full.bg-red-400')).not.toBeNull();
    });

    it('publishes inactive card lifecycle and amber surfaces while the active card stays neutral', () => {
        render(AssetCard, {
            asset: {
                id: 31,
                display_name: 'Active card',
                currency: 'EUR',
                asset_type: 'STOCK',
                provider_code: null,
                active: true,
            },
        });
        render(AssetCard, {
            asset: {
                id: 32,
                display_name: 'Inactive card',
                currency: 'EUR',
                asset_type: 'STOCK',
                provider_code: null,
                active: false,
            },
        });

        const active = screen.getByTestId('asset-card-31');
        const inactive = screen.getByTestId('asset-card-32');
        expect(active).toHaveAttribute('data-lifecycle', 'active');
        expect(active).toHaveClass('bg-white', 'dark:bg-slate-800');
        expect(active).not.toHaveClass('bg-amber-50');
        expect(active).not.toHaveClass('dark:bg-amber-950/30');
        expect(inactive).toHaveAttribute('data-lifecycle', 'inactive');
        expect(inactive).toHaveClass('bg-amber-50', 'dark:bg-amber-950/30');
    });
});

describe('AssetTable — F15 usage badge', () => {
    it('tints the count by scope: own → emerald, others → blue, analysis → gray', async () => {
        render(AssetTable, {
            data: [row(1, 3, 'own'), row(2, 5, 'others'), row(3, 0, 'analysis')],
        });

        // Barrier: all three rows rendered before reading any badge.
        await waitFor(() => {
            expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(3);
        });

        const own = badgeIn(rowEl(1));
        const others = badgeIn(rowEl(2));
        const analysis = badgeIn(rowEl(3));
        expect(own, 'own badge missing').not.toBeNull();
        expect(others, 'others badge missing').not.toBeNull();
        expect(analysis, 'analysis badge missing').not.toBeNull();

        expect(own!.className).toContain('bg-emerald-100');
        expect(others!.className).toContain('bg-blue-100');
        expect(analysis!.className).toContain('bg-gray-100');

        // The number the badge carries is the total tx count, whatever the scope.
        expect(own!.textContent?.trim()).toBe('3');
        expect(others!.textContent?.trim()).toBe('5');
        expect(analysis!.textContent?.trim()).toBe('0');
    });

    it('renders the badge with a zero count when txScope is omitted entirely', async () => {
        // Rows built before the F15 fields existed (or from a partial payload)
        // have neither txCount nor txScope: the cell must still render, gray,
        // rather than crash the column.
        render(AssetTable, {data: [row(9, 0, undefined)]});

        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="9"]')).not.toBeNull());
        const badge = badgeIn(rowEl(9));
        expect(badge).not.toBeNull();
        expect(badge!.className).toContain('bg-gray-100');
        expect(badge!.textContent?.trim()).toBe('0');
    });
});
