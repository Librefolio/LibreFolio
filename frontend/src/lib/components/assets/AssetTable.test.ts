// @vitest-environment jsdom
/**
 * AssetTable — component test (Vitest + jsdom).
 *
 * Subject: the F15 usage badge in the `txCount` column. The badge's colour IS
 * the feature — it is how the table tells "used by your brokers" (emerald)
 * from "used only by other users" (blue) from "never used / under analysis"
 * (gray) at a glance — so here, exceptionally, the assertion reads the class
 * token, because the class is the contract the fix delivers (this is the
 * badge-palette exception the F15 task sanctions; behaviour is still located
 * by row id and column, never by position).
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
import AssetTable, {type AssetRow} from './AssetTable.svelte';

function row(id: number, txCount: number, txScope: AssetRow['txScope']): AssetRow {
    return {
        id,
        display_name: `Asset ${id}`,
        currency: 'EUR',
        asset_type: 'STOCK',
        active: true,
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
