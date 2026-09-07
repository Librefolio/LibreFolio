// @vitest-environment jsdom
/**
 * AssetSyncModal — component test (Vitest + jsdom).
 *
 * Same shape as FxSyncModal, one decision heavier: the modal is handed a list of
 * assets and has to work out which of them are syncable at all. Only an asset with
 * a `provider_code` becomes a target, and the ones left out have to disappear from
 * the count as well as from the request — a filter with two visible consequences,
 * neither of which is reachable from an E2E without seeding assets that differ
 * precisely in that field.
 *
 * The other half is the same translation as FX, over a different wire shape:
 * `asset_id` is a number and becomes the row key as a string, price counters and
 * corporate-event counters travel side by side, and every optional field has to
 * survive being absent. `$lib/api` is mocked because that shape is the subject.
 *
 * The `assets` prop is also the display source: a row shows the name from the
 * lookup, or a placeholder when the backend answers about an id the caller never
 * mentioned. Both arms are exercised.
 *
 * Asserted on `data-testid`/`data-*` and on strings this file injected — never on
 * a translated label.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        sync_prices_bulk_api_v1_assets_prices_sync_post: vi.fn(),
        // The open-effect warms the provider icon cache through this endpoint;
        // it is not the subject, but it must not reject into nothing. Exactly one
        // provider carries an icon, so both halves of the badge — image and code
        // text — are reachable from the same file.
        list_providers_api_v1_assets_provider_get: vi.fn().mockResolvedValue([{code: 'stooq', name: 'Stooq', icon_url: '/icons/providers/stooq.png'}]),
    },
}));

import AssetSyncModal from './AssetSyncModal.svelte';
import {zodiosApi} from '$lib/api';

const syncPrices = vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post);

type WireResult = Record<string, unknown>;

function respondWith(...results: WireResult[]) {
    syncPrices.mockResolvedValue({results} as never);
}

/** An asset the modal is allowed to sync unless `provider_code` is cleared. */
function asset(id: number, over: Record<string, unknown> = {}) {
    return {id, display_name: `Asset ${id}`, provider_code: 'yfinance', ...over};
}

function mount(props: Record<string, unknown> = {}) {
    const onsynced = vi.fn();
    const onclose = vi.fn();
    return {onsynced, onclose, ...render(AssetSyncModal, {open: true, dateStart: '2024-03-01', dateEnd: '2024-03-31', assets: [asset(1)], onsynced, onclose, ...props})};
}

function rowOf(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`[data-testid="sync-result-row"][data-row-id="${id}"]`);
    if (!el) throw new Error(`no result row for ${id}; present: ${rowIds().join(', ') || '(none)'}`);
    return el;
}

function rowIds(): string[] {
    return [...document.querySelectorAll<HTMLElement>('[data-testid="sync-result-row"]')].map((r) => r.getAttribute('data-row-id') ?? '');
}

function num(el: Element | null, attr: string): number {
    return Number(el?.getAttribute(attr));
}

function summary() {
    const el = screen.getByTestId('sync-modal-results');
    return {success: num(el, 'data-success'), total: num(el, 'data-total'), failed: num(el, 'data-failed'), fetched: num(el, 'data-fetched'), changed: num(el, 'data-changed')};
}

/** The standalone error banner — not the summary, which is also `error` at 0/N. */
function errorBanner(): HTMLElement | null {
    return [...document.querySelectorAll<HTMLElement>('[data-testid="info-banner-error"]')].find((el) => !el.closest('[data-testid="sync-modal-results"]')) ?? null;
}

async function startSync() {
    await fireEvent.click(screen.getByTestId('sync-modal-start'));
}

async function settled() {
    await waitFor(() => expect(screen.getByTestId('sync-modal-body')).toHaveAttribute('data-busy', 'false'));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    syncPrices.mockReset();
});

// =========================================================================
// Which assets are syncable
// =========================================================================

describe('AssetSyncModal — target selection', () => {
    it('keeps only the assets that have a provider assigned', async () => {
        respondWith();
        mount({assets: [asset(1), asset(2, {provider_code: null}), asset(3, {provider_code: undefined}), asset(4)]});

        expect(screen.getByTestId('asset-sync-modal')).toBeInTheDocument();
        // 1 and 4 are syncable; 2 and 3 have nowhere to fetch from.
        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(2);
        expect(num(screen.getByTestId('sync-modal-count'), 'data-section-count')).toBe(1);
    });

    it('has nothing to start when no asset has a provider', async () => {
        respondWith();
        mount({assets: [asset(1, {provider_code: null}), asset(2, {provider_code: ''})]});

        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(0);
        expect(screen.getByTestId('sync-modal-start')).toBeDisabled();
    });

    it('sends one item per syncable asset, with numeric ids and the shared date range', async () => {
        respondWith({asset_id: 1, status: 'ok'});
        mount({assets: [asset(1), asset(2, {provider_code: null}), asset(7)], dateStart: '2022-01-01', dateEnd: '2022-12-31'});

        await startSync();
        await settled();

        // parseInt on the way out: the id is a string inside the modal and a number
        // on the wire. Asset 2 never appears.
        expect(syncPrices).toHaveBeenCalledWith(
            [
                {asset_id: 1, date_range: {start: '2022-01-01', end: '2022-12-31'}},
                {asset_id: 7, date_range: {start: '2022-01-01', end: '2022-12-31'}},
            ],
            {timeout: 120_000},
        );
    });
});

// =========================================================================
// The response that arrives
// =========================================================================

describe('AssetSyncModal — mapping the response into rows', () => {
    it('keys rows by the stringified asset id and sums both counters', async () => {
        respondWith({asset_id: 1, status: 'ok', points_fetched: 30, points_changed: 12, provider_used: 'yfinance', elapsed_ms: 800}, {asset_id: 2, status: 'ok', points_fetched: 5, points_changed: 1});
        const {onsynced} = mount({assets: [asset(1), asset(2)]});

        await startSync();
        await settled();

        expect(rowIds().sort()).toEqual(['1', '2']);
        // The display name comes from the `assets` prop, which this test supplied.
        expect(rowOf('1')).toHaveTextContent('Asset 1');
        expect(within(rowOf('1')).getByTitle('yfinance')).toHaveTextContent('yfinance');
        expect(summary()).toMatchObject({success: 2, total: 2, fetched: 35, changed: 13});
        expect(onsynced).toHaveBeenCalledTimes(1);
    });

    it('turns absent counters into zeros and omits the decorations they drive', async () => {
        respondWith({asset_id: 1, status: 'ok'});
        mount({assets: [asset(1)]});

        await startSync();
        await settled();

        expect(summary()).toMatchObject({fetched: 0, changed: 0, success: 1, total: 1});
        expect(rowOf('1')).toHaveTextContent('0↓ 0Δ');
        // No provider, no elapsed time, and no corporate-event group.
        expect(rowOf('1').querySelector('[title="yfinance"]')).toBeNull();
    });

    it('carries the corporate-event counters through into the row', async () => {
        respondWith({asset_id: 1, status: 'ok', points_fetched: 10, points_changed: 2, events_fetched: 4, events_changed: 1}, {asset_id: 2, status: 'ok', points_fetched: 10, points_changed: 2, events_fetched: 0});
        mount({assets: [asset(1), asset(2)]});

        await startSync();
        await settled();

        // `4↓ 1Δ` is the events group; asset 2 fetched none, so it has one group only.
        expect(rowOf('1')).toHaveTextContent('4↓ 1Δ');
        expect(rowOf('2')).not.toHaveTextContent('4↓');
    });

    it('names a row it has no asset for by its id', async () => {
        // The backend answered about an asset the caller never listed — the lookup
        // misses and the row still has to identify itself.
        respondWith({asset_id: 99, status: 'ok', points_fetched: 1, points_changed: 1});
        mount({assets: [asset(1)]});

        await startSync();
        await settled();

        expect(rowOf('99')).toHaveTextContent('Asset #99');
    });

    it('renders the asset icon when the caller supplied one', async () => {
        respondWith({asset_id: 1, status: 'ok'});
        mount({assets: [asset(1, {icon_url: '/icons/acme.png'})]});

        await startSync();
        await settled();

        expect(rowOf('1').querySelector('img')).toHaveAttribute('src', '/icons/acme.png');
    });

    it('draws the provider badge as its icon when the cache knows one, and as its code when it does not', async () => {
        respondWith({asset_id: 1, status: 'ok', provider_used: 'stooq'}, {asset_id: 2, status: 'ok', provider_used: 'yfinance'});
        mount({assets: [asset(1), asset(2)]});

        await startSync();
        await settled();

        // 'stooq' is the one provider the mocked catalogue gives an icon to.
        const known = within(rowOf('1')).getByTitle('stooq');
        expect(known.querySelector('img')).toHaveAttribute('src', '/icons/providers/stooq.png');
        // 'yfinance' is absent from it, so the badge degrades to the bare code.
        const unknown = within(rowOf('2')).getByTitle('yfinance');
        expect(unknown.querySelector('img')).toBeNull();
        expect(unknown).toHaveTextContent('yfinance');
    });

    /**
     * The one wiring test for this modal. What the row *does* with a result —
     * which statuses afford a retry, how the visible error is picked out of the
     * list, the copy gestures, the skipped note — belongs to
     * SyncResultRow.test.ts, in one place, because the four hand-written copies
     * of that row drifted apart precisely by being read one at a time. What is
     * this modal's own is that it hands the shared row its results at all, and
     * that what the row says is what the tally counts.
     */
    it('renders the shared result row, and counts what the rows say', async () => {
        respondWith({asset_id: 1, status: 'failed', errors: ['symbol not found']}, {asset_id: 2, status: 'skipped', message: 'already up to date'});
        mount({assets: [asset(1), asset(2)]});

        await startSync();
        await settled();

        expect(within(rowOf('1')).getByTestId('sync-row-error')).toHaveTextContent('symbol not found');
        expect(within(rowOf('2')).getByTestId('sync-row-skipped')).toHaveTextContent('already up to date');
        // Skipped is not a failure: nothing to retry on that row, and it counts
        // as neither a success nor a failure.
        expect(within(rowOf('2')).queryByTestId('sync-retry-row')).toBeNull();
        expect(summary()).toMatchObject({success: 0, total: 2, failed: 1});
    });

    it('retries a single asset with only that id', async () => {
        syncPrices.mockResolvedValueOnce({
            results: [
                {asset_id: 1, status: 'failed', errors: ['rate limited']},
                {asset_id: 2, status: 'ok', points_fetched: 4, points_changed: 4},
            ],
        } as never);
        syncPrices.mockResolvedValueOnce({results: [{asset_id: 1, status: 'ok', points_fetched: 11, points_changed: 11}]} as never);
        mount({assets: [asset(1), asset(2)]});

        await startSync();
        await settled();
        expect(rowOf('1')).toHaveAttribute('data-status', 'failed');

        await fireEvent.click(within(rowOf('1')).getByTestId('sync-retry-row'));
        await waitFor(() => expect(rowOf('1')).toHaveAttribute('data-status', 'ok'));

        expect(syncPrices).toHaveBeenNthCalledWith(2, [{asset_id: 1, date_range: {start: '2024-03-01', end: '2024-03-31'}}], {timeout: 120_000});
        expect(summary()).toMatchObject({success: 2, total: 2, failed: 0});
    });

    it('turns a rejected call into one failed row per requested asset', async () => {
        syncPrices.mockRejectedValue(new Error('Network Error'));
        mount({assets: [asset(1), asset(2)]});

        await startSync();
        await settled();

        expect(rowIds().sort()).toEqual(['1', '2']);
        expect(rowOf('1')).toHaveAttribute('data-status', 'failed');
        expect(errorBanner()).toHaveTextContent('Network Error');
        // The error is repeated per row, so each one says why it failed.
        expect(rowOf('2')).toHaveTextContent('Network Error');
    });
});
