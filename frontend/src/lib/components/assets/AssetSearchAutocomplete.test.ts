// @vitest-environment jsdom
/**
 * AssetSearchAutocomplete — component test (Vitest + jsdom).
 *
 * The most machinery of the six: a 300 ms debounce, a provider list fetched on
 * mount, an SSE stream parsed by hand, a REST fallback, and a documented race —
 * a query typed before the provider list has landed must be *held* and run once
 * the providers arrive, not silently dropped. That race is a real bug this file
 * guards against: at load it was invisible because the providers almost always
 * won, and it only surfaced under contention.
 *
 * The observable contract is `data-state` on the results dropdown
 * (`searching|results|empty|error`) and `onselect(result)`. Both are asserted
 * here; the human-facing strings inside each state are translated and are not.
 *
 * Mocked at the boundary:
 *   - `$lib/api` — the provider list and the REST fallback endpoint.
 *   - `global.fetch` — the SSE stream, replayed from canned `data:` chunks so the
 *     three event kinds (`provider_results`, `provider_error`, `done`) and the
 *     abort/timeout path are all reachable without a server.
 *   - `$lib/utils/providerHelpers` — `ensureAssetProvidersCached` (a cache warm we
 *     don't want firing real requests) and `getAssetProviderIconUrl` (returns null
 *     so the row's provider-icon block stays out of the way).
 *
 * NOT tested: icon URLs, the external-link anchor's target, and anything that
 * depends on layout — all either translated, positional, or another component's job.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        list_providers_api_v1_assets_provider_get: vi.fn(),
        search_assets_via_providers_api_v1_assets_provider_search_get: vi.fn(),
    },
}));
vi.mock('$lib/utils/providerHelpers', () => ({
    ensureAssetProvidersCached: vi.fn(() => Promise.resolve()),
    getAssetProviderIconUrl: vi.fn(() => null),
}));

import AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
import {zodiosApi} from '$lib/api';

const listProviders = vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get);
const restSearch = vi.mocked(zodiosApi.search_assets_via_providers_api_v1_assets_provider_search_get);

const PROVIDERS = [
    {code: 'alpha', name: 'Alpha', supports_search: true},
    {code: 'beta', name: 'Beta', supports_search: true},
    {code: 'nosearch', name: 'NoSearch', supports_search: false},
    {code: 'mockprov', name: 'Mock', supports_search: true}, // always filtered out
];

const R1 = {identifier: 'US0378331005', identifier_type: 'isin', display_name: 'Apple Inc', provider_code: 'alpha', currency: 'USD', asset_type: 'STOCK', provider_url: 'https://example/apple', via_web: false};
const R2 = {identifier: 'US5949181045', identifier_type: 'isin', display_name: 'Microsoft', provider_code: 'beta', currency: 'USD', asset_type: 'STOCK', via_web: true};

/** A fake streamed Response replaying the given SSE events, one `data:` line each. */
function sseResponse(events: unknown[], {ok = true}: {ok?: boolean} = {}) {
    const encoder = new TextEncoder();
    const chunks = events.map((e) => encoder.encode(`data: ${JSON.stringify(e)}\n`));
    let i = 0;
    return {
        ok,
        body: ok
            ? {
                  getReader: () => ({
                      read: async () => (i < chunks.length ? {done: false, value: chunks[i++]} : {done: true, value: undefined}),
                      cancel: vi.fn(),
                  }),
              }
            : null,
    };
}

/** Mount and wait until the provider badges have loaded (the normal starting point). */
async function mountReady(props: Record<string, unknown> = {}) {
    const onselect = vi.fn();
    const utils = render(AssetSearchAutocomplete, {onselect, ...props});
    await waitFor(() => expect(screen.queryByTestId('asset-search-provider-alpha')).not.toBeNull());
    return {onselect, ...utils};
}

async function type(value: string) {
    const input = document.querySelector<HTMLInputElement>('[data-search-autocomplete] input')!;
    await fireEvent.input(input, {target: {value}});
    return input;
}

function state(): string | null {
    return screen.queryByTestId('asset-search-results')?.getAttribute('data-state') ?? null;
}

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    listProviders.mockResolvedValue(PROVIDERS as never);
    // Default streamed search: two providers answer, then the stream ends.
    global.fetch = vi.fn(async () => sseResponse([{event: 'provider_results', results: [R1]}, {event: 'provider_results', results: [R2]}, {event: 'done'}])) as never;
});

describe('AssetSearchAutocomplete — providers', () => {
    it('shows a badge for each searchable provider and hides mockprov and non-search ones', async () => {
        await mountReady();
        expect(screen.getByTestId('asset-search-provider-alpha')).toHaveAttribute('data-selected', 'true');
        expect(screen.getByTestId('asset-search-provider-beta')).toHaveAttribute('data-selected', 'true');
        expect(screen.queryByTestId('asset-search-provider-nosearch')).toBeNull();
        expect(screen.queryByTestId('asset-search-provider-mockprov')).toBeNull();
    });
});

describe('AssetSearchAutocomplete — streamed search', () => {
    it('debounced typing runs a stream and reaches the results state', async () => {
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));
        expect(screen.getByTestId('asset-search-result-0')).toHaveAttribute('data-identifier', 'US0378331005');
        expect(screen.getByTestId('asset-search-result-1')).toHaveAttribute('data-identifier', 'US5949181045');
    });

    it('hands the picked result to onselect', async () => {
        const {onselect} = await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        await fireEvent.click(screen.getByTestId('asset-search-result-0'));
        expect(onselect).toHaveBeenCalledTimes(1);
        expect(onselect).toHaveBeenCalledWith(expect.objectContaining({identifier: 'US0378331005', display_name: 'Apple Inc', provider_code: 'alpha'}));
    });

    it('reaches the empty state when the providers return nothing', async () => {
        global.fetch = vi.fn(async () => sseResponse([{event: 'provider_results', results: []}, {event: 'done'}])) as never;
        await mountReady();
        await type('zzz');
        await waitFor(() => expect(state()).toBe('empty'));
    });

    it('treats a provider_error like a completed provider with no rows', async () => {
        global.fetch = vi.fn(async () => sseResponse([{event: 'provider_error', provider: 'alpha'}, {event: 'done'}])) as never;
        await mountReady();
        await type('zzz');
        await waitFor(() => expect(state()).toBe('empty'));
    });

    it('clears the dropdown when the query is emptied', async () => {
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        await type('');
        expect(screen.queryByTestId('asset-search-results')).toBeNull();
    });
});

describe('AssetSearchAutocomplete — fallbacks and errors', () => {
    it('falls back to the REST endpoint when the stream is unavailable', async () => {
        global.fetch = vi.fn(async () => sseResponse([], {ok: false})) as never;
        restSearch.mockResolvedValue({results: [R1]} as never);

        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));
        expect(restSearch).toHaveBeenCalled();
        expect(screen.getByTestId('asset-search-result-0')).toHaveAttribute('data-identifier', 'US0378331005');
    });

    it('shows the error state when both the stream and the REST fallback fail', async () => {
        global.fetch = vi.fn(async () => {
            throw new Error('network down');
        }) as never;
        restSearch.mockRejectedValue(new Error('rest down'));

        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('error'));
    });

    it('shows the error state on an aborted/timed-out stream without hitting REST', async () => {
        global.fetch = vi.fn(async () => {
            throw new DOMException('aborted', 'AbortError');
        }) as never;

        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('error'));
        // The abort path deliberately does NOT fall back to REST (it would hang too).
        expect(restSearch).not.toHaveBeenCalled();
    });
});

describe('AssetSearchAutocomplete — provider toggle', () => {
    it('deselecting a provider re-runs the search without it', async () => {
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));
        const callsBefore = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length;

        await fireEvent.click(screen.getByTestId('asset-search-provider-beta'));
        expect(screen.getByTestId('asset-search-provider-beta')).toHaveAttribute('data-selected', 'false');

        await waitFor(() => expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(callsBefore));
        const lastUrl = String((global.fetch as ReturnType<typeof vi.fn>).mock.calls.at(-1)?.[0]);
        expect(lastUrl).toContain('providers=alpha');
        expect(lastUrl).not.toContain('beta');
    });
});

describe('AssetSearchAutocomplete — the pending-query race', () => {
    it('holds a query typed before providers load and runs it once they arrive', async () => {
        // Providers are gated: nothing resolves until we let them.
        let releaseProviders!: (v: unknown) => void;
        listProviders.mockReturnValueOnce(new Promise((res) => (releaseProviders = res)) as never);

        const onselect = vi.fn();
        render(AssetSearchAutocomplete, {onselect});

        // Type while the provider list is still in flight — the debounce fires but
        // there is nothing to search against yet, so the box goes to "searching".
        await type('apple');
        await waitFor(() => expect(state()).toBe('searching'));

        // Providers land: the held query must now run on its own.
        releaseProviders(PROVIDERS);
        await waitFor(() => expect(state()).toBe('results'));
        expect(screen.getByTestId('asset-search-result-0')).toHaveAttribute('data-identifier', 'US0378331005');
    });

    it('auto-searches an initialQuery once the providers are ready', async () => {
        await mountReady({initialQuery: 'apple'});
        await waitFor(() => expect(state()).toBe('results'));
        expect(global.fetch).toHaveBeenCalled();
    });
});
