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
import {get} from 'svelte/store';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

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

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import {getUserStorageKey} from '$lib/utils/storage';
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

/**
 * The tooltips of the hidden columns «Start Value» and «End Value» (discussion #49, promised to a user on 17/10).
 *
 * The two columns are hidden by default and had no tooltip, so nobody could tell what a «0» in them meant. The contract: each
 * has a header tooltip, from the catalogue (`dashboard.startValueTooltip`, `dashboard.endValueTooltip`), that says — as the
 * answer given in the discussion does — that it is the position's value at the start (end) of the period, as the Value column
 * of the Portfolio, 0 when the position was not there (was closed), and, for the start, that it is the base of the period's
 * percentages. The text is read from the catalogue, in the interface language (never typed here, so the file passes in any
 * language); the cases pin that the columns have a tooltip, that it is the catalogue's, and that the columns stay hidden by default.
 *
 * Red today: the two columns have no header tooltip.
 */
describe('ContributionTable — the tooltips of Start Value and End Value (#49)', () => {
    // The jsdom here has no storage: a plain one in memory, as the table reads and writes its saved overrides through it.
    let stored = new Map<string, string>();
    beforeEach(() => {
        stored = new Map();
        vi.stubGlobal('localStorage', {getItem: (key: string) => stored.get(key) ?? null, setItem: (key: string, value: string) => void stored.set(key, value), removeItem: (key: string) => void stored.delete(key), clear: () => stored.clear()});
    });
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    /** Show the two hidden columns as a user does, through the table's saved overrides, before it mounts. */
    function showHiddenValueColumns() {
        stored.set(getUserStorageKey('dataTable_dashboard-performance-v2_columnVisibilityOverrides'), JSON.stringify({'start-value': true, 'end-value': true}));
    }

    it('keeps both columns hidden by default', async () => {
        render(ContributionTable, {positions: [position(11, 1)]});
        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(1));

        expect(screen.queryByTestId('dt-sort-start-value')).toBeNull();
        expect(screen.queryByTestId('dt-sort-end-value')).toBeNull();
    });

    it.each([
        {column: 'start-value', key: 'dashboard.startValueTooltip'},
        {column: 'end-value', key: 'dashboard.endValueTooltip'},
    ])('shows the catalogue’s $key on the $column header', async ({column, key}) => {
        showHiddenValueColumns();
        render(ContributionTable, {positions: [position(11, 1)]});
        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(1));

        // A column with a tooltip and no documentation link wears it on its sort button (`DataTableColumnHeader`): a click opens it.
        const header = await screen.findByTestId(`dt-sort-${column}`);
        expect(header, `precondition: the ${column} column is shown through the saved overrides`).toBeInTheDocument();
        await fireEvent.click(header);

        const expected = get(_)(key);
        expect(expected, `the catalogue holds ${key}`).not.toBe(key);
        expect(await screen.findByRole('tooltip')).toHaveTextContent(expected);
    });
});
