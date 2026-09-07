// @vitest-environment jsdom
/**
 * FxSyncModal — component test (Vitest + jsdom).
 *
 * FxSyncModal is a translator. It owns no sync logic: it builds one `SyncSection`
 * out of the `pairs` prop and hands SyncModalBase a `doSyncFn` that calls one
 * endpoint and reshapes the answer into `SyncResult[]`. Both halves of that
 * translation are what this file pins down — the request that leaves (which pairs,
 * which dates, which axios options) and the row that arrives (which fields survive,
 * which absent ones become 0 or []).
 *
 * The boundary is therefore `$lib/api`: mocking it is not a way of avoiding the
 * network, it is the point. Whether the HTTP call works is an E2E question and is
 * answered there with MOCKFX; whether a response with no `points_fetched` produces
 * a row that says 0 instead of NaN can only be asked here, because no provider can
 * be made to answer that way on demand.
 *
 * `getCurrencyGraph` is stubbed for a different reason: the open-effect fires it to
 * warm the FX provider icon cache, it awaits two endpoints, and in jsdom that is an
 * unhandled rejection with nothing to do with the subject.
 *
 * Asserted on `data-testid`/`data-*` and on values this file injected. Never on a
 * label: the pair rows carry translated tooltips and the footer button changes
 * wording with `isTimeout`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        sync_rates_api_v1_fx_currencies_sync_post: vi.fn(),
    },
}));
// The modal warms the FX provider cache on open; that call is not the subject.
// The cache itself is: exactly one provider is given an icon, so both halves of
// the badge — image and code text — are reachable from this file.
vi.mock('$lib/stores/currencyGraphStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/currencyGraphStore')>()),
    getCurrencyGraph: vi.fn().mockResolvedValue(undefined),
    getCachedFxProviders: vi.fn(() => [{code: 'ecb', name: 'ECB', icon_url: '/icons/fx/ecb.png'}]),
}));

import FxSyncModal from './FxSyncModal.svelte';
import {zodiosApi} from '$lib/api';

const syncRates = vi.mocked(zodiosApi.sync_rates_api_v1_fx_currencies_sync_post);

/** One entry of the endpoint's `results` array, straight from the wire shape. */
type WireResult = Record<string, unknown>;

function respondWith(...results: WireResult[]) {
    syncRates.mockResolvedValue({results} as never);
}

function mount(props: Record<string, unknown> = {}) {
    const onsynced = vi.fn();
    const onclose = vi.fn();
    return {onsynced, onclose, ...render(FxSyncModal, {open: true, dateStart: '2024-03-01', dateEnd: '2024-03-31', pairs: ['EUR-USD'], onsynced, onclose, ...props})};
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

/** Results land through the endpoint promise and an effect flush. */
async function settled() {
    await waitFor(() => expect(screen.getByTestId('sync-modal-body')).toHaveAttribute('data-busy', 'false'));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    syncRates.mockReset();
});

// =========================================================================
// The request that leaves
// =========================================================================

describe('FxSyncModal — the section it builds', () => {
    it('puts every pair into a single section', async () => {
        respondWith();
        mount({pairs: ['EUR-USD', 'EUR-GBP', 'USD-JPY']});

        expect(screen.getByTestId('fx-sync-modal')).toBeInTheDocument();
        expect(num(screen.getByTestId('sync-modal-count'), 'data-section-count')).toBe(1);
        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(3);
    });

    it('has nothing to start when there are no pairs', async () => {
        respondWith();
        mount({pairs: []});

        // The single section is empty, so it is not active and the modal is inert.
        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(0);
        expect(screen.getByTestId('sync-modal-start')).toBeDisabled();
    });

    it('sends the pairs and the date range, with a timeout the user cannot influence', async () => {
        respondWith({pair: 'EUR-USD', status: 'ok'});
        mount({pairs: ['EUR-USD', 'EUR-GBP'], dateStart: '2023-01-01', dateEnd: '2023-06-30'});

        // Raise the modal's own timeout field before starting: it moves the
        // countdown and nothing else — see the report.
        await fireEvent.input(screen.getByTestId('sync-modal-timeout'), {target: {value: '300'}});
        await startSync();
        await settled();

        expect(syncRates).toHaveBeenCalledWith({pairs: ['EUR-USD', 'EUR-GBP'], start: '2023-01-01', end: '2023-06-30'}, {timeout: 120_000});
    });
});

// =========================================================================
// The response that arrives
// =========================================================================

describe('FxSyncModal — mapping the response into rows', () => {
    it('keys each row by the pair and carries the counters into the tally', async () => {
        respondWith({pair: 'EUR-USD', status: 'ok', points_fetched: 21, points_changed: 4, provider_used: 'frankfurter', elapsed_ms: 1350}, {pair: 'EUR-GBP', status: 'ok', points_fetched: 9, points_changed: 0});
        const {onsynced} = mount({pairs: ['EUR-USD', 'EUR-GBP']});

        await startSync();
        await settled();

        expect(rowIds().sort()).toEqual(['EUR-GBP', 'EUR-USD']);
        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'ok');
        expect(summary()).toMatchObject({success: 2, total: 2, failed: 0, fetched: 30, changed: 4});
        // The provider badge falls back to the code when no icon is cached.
        expect(within(rowOf('EUR-USD')).getByTitle('frankfurter')).toHaveTextContent('frankfurter');
        expect(onsynced).toHaveBeenCalledTimes(1);
    });

    it('turns absent counters into zeros instead of undefined', async () => {
        // A result with only pair+status is valid on the wire; every optional field
        // must acquire a defined value on the way in.
        respondWith({pair: 'EUR-USD', status: 'ok'});
        mount();

        await startSync();
        await settled();

        expect(summary()).toMatchObject({fetched: 0, changed: 0, success: 1, total: 1});
        // No provider, no elapsed time: neither trailing decoration is rendered.
        expect(rowOf('EUR-USD').querySelector('[title]')).toBeNull();
        expect(rowOf('EUR-USD')).toHaveTextContent('0↓ 0Δ');
    });

    it('splits a provider chain into one badge per leg', async () => {
        respondWith({pair: 'RON-JPY', status: 'ok', points_fetched: 5, points_changed: 5, provider_used: 'CHAIN:ecb+frankfurter'});
        mount({pairs: ['RON-JPY']});

        await startSync();
        await settled();

        // `parseProviderChain` strips the CHAIN: prefix and splits on '+'; each leg
        // gets its own badge, titled with the provider code this test injected.
        const row = rowOf('RON-JPY');
        expect(within(row).getByTitle('ecb')).toBeInTheDocument();
        expect(within(row).getByTitle('frankfurter')).toBeInTheDocument();
    });

    it('draws each leg as its icon when the cache knows it, and as its code when it does not', async () => {
        respondWith({pair: 'RON-JPY', status: 'ok', points_fetched: 5, points_changed: 5, provider_used: 'CHAIN:ecb+frankfurter'});
        mount({pairs: ['RON-JPY']});

        await startSync();
        await settled();

        // 'ecb' is the one provider the mocked cache gives an icon to.
        const known = within(rowOf('RON-JPY')).getByTitle('ecb');
        expect(known.querySelector('img')).toHaveAttribute('src', '/icons/fx/ecb.png');
        // 'frankfurter' is absent from it, so the badge degrades to the bare code.
        const unknown = within(rowOf('RON-JPY')).getByTitle('frankfurter');
        expect(unknown.querySelector('img')).toBeNull();
        expect(unknown).toHaveTextContent('frankfurter');
    });

    /**
     * The props only this modal chooses. Whether the row *renders* a tooltip, or
     * what it does without a glyph, is SyncResultRow.test.ts's business; what is
     * FX's own is that it asks for the per-leg breakdown, and asks for no
     * currency glyph in front of counters that count rates rather than money.
     */
    it('hands the row a per-leg breakdown and no currency glyph', async () => {
        respondWith({pair: 'EUR-USD', status: 'ok', points_fetched: 12, points_changed: 9, provider_used: 'ecb'});
        mount({pairs: ['EUR-USD']});

        await startSync();
        await settled();

        const row = rowOf('EUR-USD');
        expect(row).toHaveTextContent('12↓ 9Δ');

        // The status icon comes first in the row, and here it is the tooltip's
        // trigger. The listener sits on the wrapper, the icon's parent, because
        // mouseenter does not bubble.
        const icon = row.querySelector('svg') as SVGElement;
        await fireEvent.mouseEnter(icon.parentElement as HTMLElement);
        // Portaled out of the modal's stacking context, so it is read globally.
        // Asserted on the counters, which this test injected; the rest of the
        // detail line is translated and is not asserted on.
        expect(await screen.findByTestId('tooltip-content')).toHaveTextContent('12↓ 9Δ');
    });

    /**
     * The one wiring test: this modal really renders the shared row, and the
     * control the row offers really reaches this modal's endpoint with this
     * modal's payload. The row's own repertoire lives in SyncResultRow.test.ts.
     */
    it('offers a per-row retry on a partial result and asks only for that pair', async () => {
        syncRates.mockResolvedValueOnce({
            results: [
                {pair: 'EUR-USD', status: 'partial', points_fetched: 3, points_changed: 3},
                {pair: 'EUR-GBP', status: 'ok', points_fetched: 8, points_changed: 8},
            ],
        } as never);
        syncRates.mockResolvedValueOnce({results: [{pair: 'EUR-USD', status: 'ok', points_fetched: 12, points_changed: 9}]} as never);
        mount({pairs: ['EUR-USD', 'EUR-GBP']});

        await startSync();
        await settled();
        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'partial');

        await fireEvent.click(within(rowOf('EUR-USD')).getByTestId('sync-retry-row'));
        await waitFor(() => expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'ok'));

        expect(syncRates).toHaveBeenNthCalledWith(2, {pairs: ['EUR-USD'], start: '2024-03-01', end: '2024-03-31'}, {timeout: 120_000});
        expect(summary()).toMatchObject({success: 2, total: 2, failed: 0});
    });

    it('turns a rejected call into one failed row per requested pair', async () => {
        syncRates.mockRejectedValue({response: {data: {detail: 'fx service unavailable'}}});
        mount({pairs: ['EUR-USD', 'EUR-GBP']});

        await startSync();
        await settled();

        expect(rowIds().sort()).toEqual(['EUR-GBP', 'EUR-USD']);
        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'failed');
        expect(errorBanner()).toHaveTextContent('fx service unavailable');
    });
});

// =========================================================================
// Pinned behaviour — see the report
// =========================================================================

describe('FxSyncModal — pinned behaviour', () => {
    /**
     * `(r.results ?? [])` on a body with no `results` yields an empty list, and an
     * empty list no longer means "never mind": SyncModalBase turns every id it
     * asked about and got no word on into a failed row. The wrapper's job here is
     * only not to throw on the missing key.
     */
    it('turns a body with no results array into a failed row per requested pair', async () => {
        syncRates.mockResolvedValue({} as never);
        const {onsynced} = mount({pairs: ['EUR-USD', 'EUR-GBP']});

        await startSync();
        await settled();

        expect(rowIds().sort()).toEqual(['EUR-GBP', 'EUR-USD']);
        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'failed');
        expect(rowOf('EUR-GBP')).toHaveAttribute('data-status', 'failed');
        // Reported per row, not as a global error: the call itself did succeed.
        expect(errorBanner()).toBeNull();
        expect(summary()).toMatchObject({success: 0, total: 2, failed: 2});
        // Each row keeps its own way out.
        expect(within(rowOf('EUR-USD')).getByTestId('sync-retry-row')).toBeInTheDocument();
        // The parent is told the run finished anyway — the user's decision: it
        // reloads regardless, and a failed row is still news.
        expect(onsynced).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('sync-modal-start')).toBeEnabled();
    });

    /**
     * ⚠ `status` is copied from the wire with no validation. A value outside the
     * four known ones renders with the failed icon but counts as neither a success
     * nor a failure, so the summary reads "0/1" with no retry offered anywhere.
     */
    it('renders an unknown status as a row nobody can act on', async () => {
        respondWith({pair: 'EUR-USD', status: 'throttled', points_fetched: 0, points_changed: 0});
        mount({pairs: ['EUR-USD']});

        await startSync();
        await settled();

        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'throttled');
        expect(summary()).toMatchObject({success: 0, total: 1, failed: 0});
        // No per-row retry (not a failure) and no footer control (no failures at all).
        expect(within(rowOf('EUR-USD')).queryByTestId('sync-retry-row')).toBeNull();
        expect(screen.queryByTestId('sync-modal-start')).toBeNull();
    });
});
