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
 *
 * The providers to configure first (workstream X, lot CP11b) are the last block: a
 * `provider_error` whose `error_code` is `NOT_CONFIGURED` — and, on the REST
 * fallback, `providers_not_configured` — gives one `asset-search-not-configured`
 * row per provider (`data-provider`) at the top of the dropdown, each with
 * `asset-search-configure`, which opens `PluginSettingsModal` on that provider; a
 * save there runs the search again; the rows start again with every search. The
 * 👑 legend (`asset-search-crown-legend`) shows when a result's name carries the
 * crown. For that block the mock also answers the two plugin settings aliases; the
 * dialog and its form are the real ones.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        list_providers_api_v1_assets_provider_get: vi.fn(),
        search_assets_via_providers_api_v1_assets_provider_search_get: vi.fn(),
        get_plugin_settings_api_v1_settings_plugins_get: vi.fn(),
        update_plugin_settings_api_v1_settings_plugins_bulk_patch: vi.fn(),
    },
    ApiError: class ApiError extends Error {},
}));
vi.mock('$lib/utils/providerHelpers', () => ({
    ensureAssetProvidersCached: vi.fn(() => Promise.resolve()),
    getAssetProviderIconUrl: vi.fn(() => null),
}));

import AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
import {zodiosApi} from '$lib/api';

const listProviders = vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get);
const restSearch = vi.mocked(zodiosApi.search_assets_via_providers_api_v1_assets_provider_search_get);
const settingsRead = vi.mocked(zodiosApi.get_plugin_settings_api_v1_settings_plugins_get);
const settingsWrite = vi.mocked(zodiosApi.update_plugin_settings_api_v1_settings_plugins_bulk_patch);

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

describe('AssetSearchAutocomplete — providers to configure first (CP11b)', () => {
    /** The providers the dropdown asks to configure, top to bottom. */
    function toConfigure(): string[] {
        return screen.queryAllByTestId('asset-search-not-configured').map((row) => row.getAttribute('data-provider') ?? '');
    }

    /** A provider that did not search: a setting it requires has no value. */
    const notConfigured = (code: string) => ({event: 'provider_error', provider_code: code, error_code: 'NOT_CONFIGURED', error: `${code} needs settings`});

    /** Alpha's settings as `GET /settings/plugins` answers them: one user API key, saved once alpha is configured. */
    function alphaSettings(configured: boolean) {
        return {
            plugins: [
                {
                    family: 'asset',
                    plugin_code: 'alpha',
                    plugin_name: 'Alpha',
                    configured,
                    fields: [{key: 'api_key', type: 'string', scope: 'user', secret: true, required: true, label: 'API key', description: '', options: [], is_set: configured, source: configured ? 'db' : 'none', locked: false, editable: true, problem: null, updated_at: null}],
                },
            ],
        };
    }

    const fetchCalls = () => (global.fetch as ReturnType<typeof vi.fn>).mock.calls;

    afterEach(() => {
        settingsRead.mockReset();
        settingsWrite.mockReset();
    });

    it('ASA-C1: a provider that answers NOT_CONFIGURED gets a row at the top of the dropdown, with «Configure»; the other providers’ results still show', async () => {
        global.fetch = vi.fn(async () => sseResponse([notConfigured('alpha'), {event: 'provider_results', results: [R2]}, {event: 'done'}])) as never;
        await mountReady();
        await type('micro');
        await waitFor(() => expect(state()).toBe('results'));

        expect(toConfigure()).toEqual(['alpha']);
        const row = screen.getByTestId('asset-search-not-configured');
        expect(within(row).getByTestId('asset-search-configure')).toBeInTheDocument();
        expect(screen.getByTestId('asset-search-results').contains(row), 'inside the dropdown').toBe(true);
        expect(row.compareDocumentPosition(screen.getByTestId('asset-search-result-0')) & Node.DOCUMENT_POSITION_FOLLOWING, 'above the results').toBeTruthy();
        expect(screen.getByTestId('asset-search-result-0')).toHaveAttribute('data-identifier', R2.identifier);
        expect(screen.queryByTestId('plugin-settings-modal'), 'the dialog opens on a click, not before').toBeNull();
    });

    it('ASA-C2: one row per provider: a second NOT_CONFIGURED of the same provider adds none', async () => {
        global.fetch = vi.fn(async () => sseResponse([notConfigured('alpha'), notConfigured('beta'), notConfigured('alpha'), {event: 'done'}])) as never;
        await mountReady();
        await type('micro');
        await waitFor(() => expect(state()).toBe('empty'));

        expect(toConfigure()).toEqual(['alpha', 'beta']);
    });

    it('ASA-C3: any other provider error gives no row', async () => {
        global.fetch = vi.fn(async () =>
            sseResponse([{event: 'provider_error', provider_code: 'alpha', error_code: 'TIMEOUT'}, {event: 'provider_error', provider_code: 'beta'}, {event: 'provider_error', error_code: 'NOT_CONFIGURED'}, {event: 'provider_error', provider_code: 7, error_code: 'NOT_CONFIGURED'}, {event: 'done'}]),
        ) as never;
        await mountReady();
        await type('micro');
        await waitFor(() => expect(state()).toBe('empty'));

        expect(toConfigure()).toEqual([]);
    });

    it('ASA-C4: the rows start again with every search', async () => {
        let searches = 0;
        global.fetch = vi.fn(async () => (++searches === 1 ? sseResponse([notConfigured('alpha'), {event: 'provider_results', results: [R2]}, {event: 'done'}]) : sseResponse([{event: 'provider_results', results: [R1]}, {event: 'done'}]))) as never;
        await mountReady();
        await type('micro');
        await waitFor(() => expect(toConfigure()).toEqual(['alpha']));

        await type('apple');

        await waitFor(() => expect(screen.getByTestId('asset-search-result-0')).toHaveAttribute('data-identifier', R1.identifier));
        expect(state()).toBe('results');
        expect(toConfigure(), 'alpha answered this search: no row is left from the last one').toEqual([]);
    });

    it('ASA-C5: on the REST fallback, providers_not_configured gives the rows: each provider once, codes only', async () => {
        global.fetch = vi.fn(async () => sseResponse([], {ok: false})) as never;
        restSearch.mockResolvedValue({results: [R1], providers_not_configured: ['beta', 'beta', 7, null, 'alpha']} as never);
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        expect(toConfigure()).toEqual(['beta', 'alpha']);
    });

    it('ASA-C6: a REST answer without providers_not_configured gives no row', async () => {
        global.fetch = vi.fn(async () => sseResponse([], {ok: false})) as never;
        restSearch.mockResolvedValue({results: [R1]} as never);
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        expect(toConfigure()).toEqual([]);
    });

    it('ASA-C7: «Configure» opens the plugin settings of that provider, and a save there runs the search again', async () => {
        let configured = false;
        global.fetch = vi.fn(async () => (configured ? sseResponse([{event: 'provider_results', results: [R1]}, {event: 'done'}]) : sseResponse([notConfigured('alpha'), {event: 'done'}]))) as never;
        settingsRead.mockImplementation(async () => alphaSettings(configured) as never);
        settingsWrite.mockImplementation(async () => {
            configured = true;
            return {results: [{family: 'asset', plugin_code: 'alpha', field_key: 'api_key', scope: 'user', success: true, error_code: null, message: null}], success_count: 1} as never;
        });
        await mountReady();
        await type('apple');
        await waitFor(() => expect(toConfigure()).toEqual(['alpha']));
        await waitFor(() => expect(state()).toBe('empty'));
        const searchesBefore = fetchCalls().length;

        await fireEvent.click(within(screen.getByTestId('asset-search-not-configured')).getByTestId('asset-search-configure'));

        const dialog = await screen.findByTestId('plugin-settings-modal');
        expect(settingsRead).toHaveBeenCalledWith({queries: {family: 'asset', plugin_code: 'alpha'}});
        const form = await within(dialog).findByTestId('plugin-settings-form-alpha');
        expect(form).toHaveAttribute('data-configured', 'false');
        expect(fetchCalls(), 'opening the dialog searches nothing').toHaveLength(searchesBefore);

        await fireEvent.input(within(form).getByTestId('plugin-setting-secret-input'), {target: {value: 'sk-alpha-00000001'}});
        await fireEvent.click(within(form).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(fetchCalls().length).toBeGreaterThan(searchesBefore));
        expect(String(fetchCalls().at(-1)?.[0]), 'the same query, again').toContain('q=apple');
        await waitFor(() => expect(state()).toBe('results'));
        expect(screen.getByTestId('asset-search-result-0')).toHaveAttribute('data-identifier', R1.identifier);
        expect(toConfigure(), 'alpha is configured now').toEqual([]);
        expect(settingsWrite.mock.calls).toStrictEqual([[{items: [{family: 'asset', plugin_code: 'alpha', field_key: 'api_key', scope: 'user', secret_value: 'sk-alpha-00000001'}]}]]);

        await fireEvent.click(within(screen.getByTestId('plugin-settings-modal')).getByTestId('plugin-settings-modal-close'));

        await waitFor(() => expect(screen.queryByTestId('plugin-settings-modal')).toBeNull());
    });

    it.each([
        {label: 'a result’s name carries the crown', results: [R2, {...R1, identifier: 'IE00B4L5Y983', display_name: 'iShares Core MSCI World 👑 EUR'}], legend: true},
        {label: 'no result carries it', results: [R1, R2], legend: false},
    ])('ASA-C8: the 👑 legend shows only when $label', async ({results, legend}) => {
        global.fetch = vi.fn(async () => sseResponse([{event: 'provider_results', results}, {event: 'done'}])) as never;
        await mountReady();
        await type('world');
        await waitFor(() => expect(state()).toBe('results'));

        expect(screen.queryByTestId('asset-search-crown-legend') !== null).toBe(legend);
    });
});
