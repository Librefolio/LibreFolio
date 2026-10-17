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
 *
 * The last blocks are workstream X, sub-lot 3. F21: the providers carry a tier and
 * a priority, the streamed results are ordered by them (with every provider at its
 * defaults the order is the arrival order, D-X3), and a premium provider among those
 * a search queried splits the dropdown into a Premium section and a community one
 * that starts closed. P20: every finished search ends with a «Can't find it? Let us
 * know» row whose link goes where the instance's `support_url` says — a mail, a page
 * (the report is copied for it) or a GitHub issue — and carries a report proven by
 * decoding the link; the row stays reachable: a click outside closes the dropdown,
 * a focus brings the finished search back, until the input is cleared. For them
 * more boundaries are mocked: the instance's configuration (`support_url`,
 * `profile`, and whether it has `loaded`: switched per case), the clipboard writer,
 * and `notify()` — the outcome of the copy is asserted on its structured half
 * (name, detail, toast variant); the toast store only to prove that no toast is
 * shown besides notify()'s. Their UI texts are read from the shipped catalogue, and
 * each case first proves its key is there.
 *
 * The next block pins where a report may go (X-R37, N61): only a self-hosted
 * instance whose configuration has loaded falls back to a public GitHub issue; on a
 * managed one, or before the configuration has loaded, a search with no valid
 * support address — an address with a user or a password is none — shows no
 * report row at all, in every state, between the sections too.
 *
 * The last block pins the words of a failed search (X-R31): when the stream and
 * then the REST fallback both fail, the dropdown says the catalogue's
 * `assets.search.failed` in the language in force — never the error's own message,
 * which still goes to `console.error` (spied, and silenced, for that case) — and the
 * time cap keeps its own `assets.search.timeout`.
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
// P20: the instance as the component reads it, set per case before the mount. By default a self-hosted instance whose
// configuration has loaded, with no support address: the one that falls back to a public GitHub issue (N61).
const instance = vi.hoisted(() => ({supportUrl: null as string | null | undefined, profile: 'selfhosted' as 'selfhosted' | 'managed', loaded: true, failed: false}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}},
    instanceConfig: {
        get config() {
            return {profile: instance.profile, accounts: {registration_mode: 'open', registration_locked: false}, support_url: instance.supportUrl};
        },
        get loaded() {
            return instance.loaded;
        },
        get failed() {
            return instance.failed;
        },
        load: vi.fn(() => Promise.resolve()),
    },
}));
vi.mock('$lib/utils/clipboard', () => ({writeTextToClipboard: vi.fn(() => Promise.resolve())}));
// The outcome of a copy is one notify() — name, detail, toast — asserted on its structured half.
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
// The toast is a field of notify(): the store is mocked only to prove that no toast is shown besides.
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {items: [], show: vi.fn(), dismiss: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));

import AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
import {zodiosApi} from '$lib/api';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {notify} from '$lib/stores/app/notify.svelte';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {writeTextToClipboard} from '$lib/utils/clipboard';
import {APP_VERSION} from '$lib/version';
import {GITHUB_NEW_ISSUE_URL, buildSearchReport, reportHref, type ProviderOutcome, type SearchReportContext} from './assetSearchReport';

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

// =========================================================================
// Workstream X, sub-lot 3 — F21 premium/community sections, P20 «Can't find it? Let us know»
// =========================================================================

/**
 * `GET /assets/provider` with the F21 fields: two premium sources (vault before prime) and two community ones
 * (beta before alpha). mockprov — premium here — and a premium source that cannot search never take part.
 */
const RANKED = [
    {code: 'alpha', name: 'Alpha', supports_search: true, tier: 'community', priority: 100},
    {code: 'prime', name: 'Prime', supports_search: true, tier: 'premium', priority: 20},
    {code: 'beta', name: 'Beta', supports_search: true, tier: 'community', priority: 50},
    {code: 'vault', name: 'Vault', supports_search: true, tier: 'premium', priority: 5},
    {code: 'nosearch', name: 'NoSearch', supports_search: false, tier: 'premium', priority: 0},
    {code: 'mockprov', name: 'Mock', supports_search: true, tier: 'premium', priority: 0}, // always filtered out
];
const WITHOUT_VAULT = RANKED.filter((provider) => provider.code !== 'vault');

/** A search result of `provider`, told apart by its `identifier`. */
function hit(provider: string, identifier: string, extra: Record<string, unknown> = {}) {
    return {identifier, identifier_type: 'isin', display_name: `${provider} ${identifier}`, provider_code: provider, currency: 'EUR', asset_type: 'ETF', via_web: false, ...extra};
}

/** The SSE events as `services/assets/search.py` sends them: each one names its provider. */
const answered = (provider: string, results: unknown[]) => ({event: 'provider_results', provider_code: provider, results});
/** A provider that failed. Its message carries a secret: the report names the error by its code, never by its message. */
const failed = (provider: string, errorCode?: string) => ({event: 'provider_error', provider_code: provider, error: `${provider}: upstream refused token tk-SECRET-77`, ...(errorCode === undefined ? {} : {error_code: errorCode})});
const DONE = {event: 'done'};

/** A streamed Response that serves `events`, then keeps the request open until `release()`, then serves `rest`. */
function heldSse(events: unknown[], rest: unknown[]) {
    const encoder = new TextEncoder();
    const encode = (list: unknown[]) => list.map((event) => encoder.encode(`data: ${JSON.stringify(event)}\n`));
    const first = encode(events);
    const later = encode(rest);
    let release!: () => void;
    const released = new Promise<void>((resolve) => (release = resolve));
    let i = 0;
    let j = 0;
    const response = {
        ok: true,
        body: {
            getReader: () => ({
                read: async () => {
                    if (i < first.length) return {done: false, value: first[i++]};
                    await released;
                    return j < later.length ? {done: false, value: later[j++]} : {done: true, value: undefined};
                },
                cancel: vi.fn(),
            }),
        },
    };
    return {response, release};
}

/**
 * A stream cut by the 30 s cap: `events` arrive, then the next read fails as the read of an aborted request does —
 * the component aborts its own fetch at the cap — with an AbortError. The cap itself is not waited for.
 */
function cutSse(events: unknown[]) {
    const encoder = new TextEncoder();
    const chunks = events.map((event) => encoder.encode(`data: ${JSON.stringify(event)}\n`));
    let i = 0;
    return {
        ok: true,
        body: {
            getReader: () => ({
                read: async () => {
                    if (i < chunks.length) return {done: false, value: chunks[i++]};
                    throw new DOMException('The operation was aborted.', 'AbortError');
                },
                cancel: vi.fn(),
            }),
        },
    };
}

/**
 * The identifiers of the results on screen, in their order. Their indices are checked on the way: row i is
 * `asset-search-result-i`, in document order and with no gap — continuous over the display order.
 */
function shown(): string[] {
    const rows = [...document.querySelectorAll('[data-testid^="asset-search-result-"]')];
    expect(rows.map((row) => row.getAttribute('data-testid'))).toEqual(rows.map((_row, i) => `asset-search-result-${i}`));
    return rows.map((row) => row.getAttribute('data-identifier') ?? '');
}

/** A UI text as the shipped catalogue words it, in the language in force. The key must be there: its value is not the key. */
function catalogue(key: string, values?: Record<string, string | number>): string {
    const text = get(_)(key, values === undefined ? undefined : {values});
    expect(text, `${key} is not in the catalogue`).not.toBe(key);
    return text;
}

const normalize = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();
/** Whether `b` comes after `a` in the document. */
const follows = (a: Element, b: Element): boolean => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
const fetchUrls = (): string[] => (global.fetch as ReturnType<typeof vi.fn>).mock.calls.map((call) => String(call[0]));
/** The providers a streamed search asked for, in the order of its `providers=` parameter. */
const queried = (url: string | undefined): string[] => new URL(url ?? '', 'http://localhost').searchParams.get('providers')?.split(',') ?? [];

/** The report link, once its row is on screen. */
async function reportLink(): Promise<HTMLElement> {
    const row = await waitFor(() => screen.getByTestId('asset-search-report-row'));
    const link = within(row).getByTestId('asset-search-report');
    expect(link.tagName, 'the report is a link').toBe('A');
    return link;
}

/** The report a GitHub link carries — the issue's title and body — decoded from its href. */
function githubReport(link: Element): {subject: string; lines: string[]} {
    const href = link.getAttribute('href') ?? '';
    const url = new URL(href);
    expect(`${url.origin}${url.pathname}`, `not a new issue of the project: ${href}`).toBe(GITHUB_NEW_ISSUE_URL);
    return {subject: url.searchParams.get('title') ?? '', lines: (url.searchParams.get('body') ?? '').split('\n')};
}

/** The provider lines of a report: the `- ` lines right after `Providers:`. */
function providerLines(lines: string[]): string[] {
    const start = lines.indexOf('Providers:');
    expect(start, `no «Providers:» line in:\n${lines.join('\n')}`).toBeGreaterThan(-1);
    const out: string[] = [];
    for (const line of lines.slice(start + 1)) {
        if (!line.startsWith('- ')) break;
        out.push(line);
    }
    return out;
}

/** The line naming what wrote the report: the app's version, the instance's profile, the language in force. */
const appLine = (language: string = get(currentLanguage)): string => `LibreFolio ${APP_VERSION}, selfhosted, language ${language}`;

/** The report the pure functions write for a search of this file's instance. */
function expectedReport(query: string, providers: ProviderOutcome[], context: SearchReportContext | null = null) {
    return buildSearchReport({query, providers, context, appVersion: APP_VERSION, profile: 'selfhosted', language: get(currentLanguage)});
}

/**
 * Clicks a report link. jsdom cannot follow a link to another document — it would only log «Not implemented:
 * navigation» — so the default action is cancelled at the very end of the event's path, on `window`, once every
 * handler of the component has run.
 */
async function clickLink(link: HTMLElement): Promise<void> {
    const stay = (event: Event) => event.preventDefault();
    window.addEventListener('click', stay);
    try {
        await fireEvent.click(link);
    } finally {
        window.removeEventListener('click', stay);
    }
}

// --- F21 sections: the order of the results ---
describe('AssetSearchAutocomplete — the order of the results (F21)', () => {
    it.each([
        {label: 'neither tier nor priority', fields: {}},
        {label: 'community at the default priority', fields: {tier: 'community', priority: 100}},
    ])('ASA-F1: providers with $label: the arrival order, one flat list, no section (D-X3)', async ({fields}) => {
        listProviders.mockResolvedValue([
            {code: 'alpha', name: 'Alpha', supports_search: true, ...fields},
            {code: 'beta', name: 'Beta', supports_search: true, ...fields},
        ] as never);
        global.fetch = vi.fn(async () => sseResponse([answered('beta', [hit('beta', 'B1'), hit('beta', 'B2')]), answered('alpha', [hit('alpha', 'A1')]), DONE])) as never;
        await mountReady();
        await type('fund');
        await waitFor(() => expect(state()).toBe('results'));

        expect(shown()).toEqual(['B1', 'B2', 'A1']);
        expect(screen.queryByTestId('asset-search-premium-section')).toBeNull();
        expect(screen.queryByTestId('asset-search-community-toggle')).toBeNull();
    });

    it('ASA-F2: with priorities and no premium provider, the streamed results come out by priority, lower first; ties keep the arrival order', async () => {
        listProviders.mockResolvedValue([
            {code: 'alpha', name: 'Alpha', supports_search: true, tier: 'community', priority: 50},
            {code: 'beta', name: 'Beta', supports_search: true, tier: 'community', priority: 10},
            {code: 'gamma', name: 'Gamma', supports_search: true, priority: 50},
        ] as never);
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1'), hit('alpha', 'A2')]), answered('gamma', [hit('gamma', 'G1')]), answered('beta', [hit('beta', 'B1')]), DONE])) as never;
        await mountReady();
        await type('fund');
        await waitFor(() => expect(state()).toBe('results'));

        // beta (10) first; alpha and gamma tie at 50, so alpha — the first to answer — before gamma.
        expect(shown()).toEqual(['B1', 'A1', 'A2', 'G1']);
        expect(screen.queryByTestId('asset-search-premium-section'), 'no premium provider: one flat list').toBeNull();
        expect(screen.queryByTestId('asset-search-community-toggle')).toBeNull();
    });

    it('ASA-F3: the WebSearch#n ranks count in the order shown', async () => {
        listProviders.mockResolvedValue([
            {code: 'alpha', name: 'Alpha', supports_search: true, priority: 50},
            {code: 'beta', name: 'Beta', supports_search: true, priority: 10},
        ] as never);
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A-web', {via_web: true}), hit('alpha', 'A-native')]), answered('beta', [hit('beta', 'B-web', {via_web: true})]), DONE])) as never;
        await mountReady();
        await type('fund');
        await waitFor(() => expect(state()).toBe('results'));

        expect(shown()).toEqual(['B-web', 'A-web', 'A-native']);
        expect(screen.getByTestId('asset-search-result-0')).toHaveTextContent('WebSearch#1');
        expect(screen.getByTestId('asset-search-result-1')).toHaveTextContent('WebSearch#2');
        expect(screen.getByTestId('asset-search-result-2')).not.toHaveTextContent('WebSearch#');
    });
});

// --- F21 sections: Premium first, community closed ---
describe('AssetSearchAutocomplete — premium and community sections (F21)', () => {
    it('ASA-F4: a premium provider among those searched: the Premium section first, then the report row, then a closed community section', async () => {
        const badge = catalogue('assets.search.premiumBadge');
        const sectionLabel = catalogue('assets.search.communitySection', {count: 2});
        const warning = catalogue('assets.search.communityWarning');
        listProviders.mockResolvedValue(RANKED as never);
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('prime', [hit('prime', 'P1'), hit('prime', 'P2')]), answered('beta', [hit('beta', 'B1')]), answered('vault', [hit('vault', 'V1')]), DONE])) as never;
        const {onselect} = await mountReady();
        await type('world');
        await waitFor(() => expect(state()).toBe('results'));

        // Premium first, vault (5) before prime (20), in their own section under their badge.
        const premium = screen.getByTestId('asset-search-premium-section');
        expect(normalize(within(premium).getByTestId('asset-search-premium-badge').textContent)).toBe(normalize(badge));
        expect(shown(), 'the community section is closed: its results are not rendered').toEqual(['V1', 'P1', 'P2']);
        for (const i of [0, 1, 2]) expect(premium.contains(screen.getByTestId(`asset-search-result-${i}`)), `result ${i} is in the Premium section`).toBe(true);
        expect(within(premium).queryByTestId('asset-search-premium-empty')).toBeNull();

        // Then the report row, then the community section's button, closed.
        const row = screen.getByTestId('asset-search-report-row');
        const toggle = screen.getByTestId('asset-search-community-toggle');
        expect(premium.contains(row), 'the report row is not part of the Premium section').toBe(false);
        expect(follows(premium, row), 'the report row comes after the Premium section').toBe(true);
        expect(follows(row, toggle), 'the community section comes after the report row').toBe(true);
        expect(toggle.tagName === 'BUTTON' || toggle.getAttribute('role') === 'button', 'the community section opens with a button').toBe(true);
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        expect(toggle).toHaveAttribute('data-count', '2');
        expect(normalize(toggle.textContent)).toBe(normalize(sectionLabel));
        expect(screen.queryByTestId('asset-search-community-warning')).toBeNull();
        // The report: every provider searched, in the order of the toggles.
        expect(providerLines(githubReport(await reportLink()).lines)).toEqual(['- alpha: 1 result', '- prime: 2 results', '- beta: 1 result', '- vault: 1 result']);

        await fireEvent.click(toggle);

        // Open: the warning, then the community results — beta (50) before alpha (100) — their indices going on.
        await waitFor(() => expect(screen.getByTestId('asset-search-community-toggle')).toHaveAttribute('aria-expanded', 'true'));
        const warned = screen.getByTestId('asset-search-community-warning');
        expect(normalize(warned.textContent)).toBe(normalize(warning));
        expect(shown()).toEqual(['V1', 'P1', 'P2', 'B1', 'A1']);
        const firstCommunity = screen.getByTestId('asset-search-result-3');
        expect(follows(screen.getByTestId('asset-search-community-toggle'), warned)).toBe(true);
        expect(follows(warned, firstCommunity), 'the warning stands above the community results').toBe(true);
        expect(screen.getByTestId('asset-search-premium-section').contains(firstCommunity)).toBe(false);
        expect(screen.getByTestId('asset-search-results').contains(warned), 'opening the section keeps the dropdown open').toBe(true);

        // Each row picks its own result: #4 is alpha's A1.
        await fireEvent.click(screen.getByTestId('asset-search-result-4'));
        expect(onselect).toHaveBeenCalledWith(expect.objectContaining({identifier: 'A1', provider_code: 'alpha'}));
    });

    it.each([
        {label: 'answered with no result', premiumAnswer: answered('prime', [])},
        {label: 'failed', premiumAnswer: failed('prime', 'TIMEOUT')},
    ])('ASA-F5: the premium provider $label: the Premium section says it found nothing, the community section counts the rest', async ({premiumAnswer}) => {
        const empty = catalogue('assets.search.premiumEmpty');
        const sectionLabel = catalogue('assets.search.communitySection', {count: 1});
        listProviders.mockResolvedValue(WITHOUT_VAULT as never);
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), premiumAnswer, answered('beta', []), DONE])) as never;
        await mountReady();
        await type('world');
        await waitFor(() => expect(state()).toBe('results'));

        const premium = screen.getByTestId('asset-search-premium-section');
        expect(within(premium).getByTestId('asset-search-premium-badge')).toBeInTheDocument();
        expect(normalize(within(premium).getByTestId('asset-search-premium-empty').textContent)).toBe(normalize(empty));
        expect(shown(), 'nothing premium to show, and the community section is closed').toEqual([]);
        const toggle = screen.getByTestId('asset-search-community-toggle');
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        expect(toggle).toHaveAttribute('data-count', '1');
        expect(normalize(toggle.textContent)).toBe(normalize(sectionLabel));

        await fireEvent.click(toggle);

        await waitFor(() => expect(screen.getByTestId('asset-search-community-toggle')).toHaveAttribute('aria-expanded', 'true'));
        expect(shown(), 'numbered from 0: nothing premium comes before them').toEqual(['A1']);
    });

    it('ASA-F6: no community result: no community section at all', async () => {
        listProviders.mockResolvedValue(RANKED as never);
        global.fetch = vi.fn(async () => sseResponse([answered('prime', [hit('prime', 'P1')]), answered('alpha', []), failed('beta', 'TIMEOUT'), answered('vault', []), DONE])) as never;
        await mountReady();
        await type('world');
        await waitFor(() => expect(state()).toBe('results'));

        expect(screen.getByTestId('asset-search-premium-section')).toBeInTheDocument();
        expect(shown()).toEqual(['P1']);
        expect(screen.getByTestId('asset-search-report-row')).toBeInTheDocument();
        expect(screen.queryByTestId('asset-search-community-toggle')).toBeNull();
        expect(screen.queryByTestId('asset-search-community-warning')).toBeNull();
    });

    it('ASA-F7: the community section stays open for the next search of the same instance, starts closed at every mount, and is never stored', async () => {
        const setItem = vi.spyOn(Storage.prototype, 'setItem');
        try {
            listProviders.mockResolvedValue(WITHOUT_VAULT as never);
            global.fetch = vi.fn(async (url: string) =>
                url.includes('q=world%20etf') ? sseResponse([answered('prime', [hit('prime', 'P2')]), answered('beta', [hit('beta', 'B2')]), answered('alpha', []), DONE]) : sseResponse([answered('prime', [hit('prime', 'P1')]), answered('beta', [hit('beta', 'B1')]), answered('alpha', []), DONE]),
            ) as never;
            const first = await mountReady();
            await type('world');
            await waitFor(() => {
                expect(state()).toBe('results');
                expect(shown()).toEqual(['P1']);
            });
            await fireEvent.click(screen.getByTestId('asset-search-community-toggle'));
            await waitFor(() => expect(shown()).toEqual(['P1', 'B1']));

            // A later search in the same instance: the section is still open.
            await type('world etf');
            await waitFor(() => {
                expect(state()).toBe('results');
                expect(shown()).toEqual(['P2', 'B2']);
            });
            expect(screen.getByTestId('asset-search-community-toggle')).toHaveAttribute('aria-expanded', 'true');

            // A new mount: closed again.
            first.unmount();
            await mountReady();
            await type('world');
            await waitFor(() => {
                expect(state()).toBe('results');
                expect(screen.getByTestId('asset-search-community-toggle')).toHaveAttribute('data-count', '1');
            });
            expect(screen.getByTestId('asset-search-community-toggle')).toHaveAttribute('aria-expanded', 'false');
            expect(shown()).toEqual(['P1']);
            expect(setItem, 'the open state is never written to localStorage or sessionStorage').not.toHaveBeenCalled();
        } finally {
            setItem.mockRestore();
        }
    });

    it('ASA-F8: a premium provider switched off before the search does not split the list: today’s flat list, then the report row', async () => {
        listProviders.mockResolvedValue([
            {code: 'prime', name: 'Prime', supports_search: true, tier: 'premium', priority: 20},
            {code: 'alpha', name: 'Alpha', supports_search: true},
            {code: 'beta', name: 'Beta', supports_search: true},
            {code: 'nosearch', name: 'NoSearch', supports_search: false, tier: 'premium', priority: 0},
            {code: 'mockprov', name: 'Mock', supports_search: true, tier: 'premium', priority: 0},
        ] as never);
        global.fetch = vi.fn(async () => sseResponse([answered('beta', [hit('beta', 'B1')]), answered('alpha', [hit('alpha', 'A1')]), DONE])) as never;
        await mountReady();
        await fireEvent.click(screen.getByTestId('asset-search-provider-prime'));
        expect(screen.getByTestId('asset-search-provider-prime')).toHaveAttribute('data-selected', 'false');

        await type('world');
        await waitFor(() => expect(state()).toBe('results'));

        expect(queried(fetchUrls().at(-1)), 'precondition: alpha and beta only — not prime, nor mockprov, nor nosearch').toEqual(['alpha', 'beta']);
        expect(shown(), 'the arrival order: beta answered first').toEqual(['B1', 'A1']);
        expect(screen.queryByTestId('asset-search-premium-section')).toBeNull();
        expect(screen.queryByTestId('asset-search-community-toggle')).toBeNull();
        expect(screen.queryByTestId('asset-search-community-warning')).toBeNull();
        expect(follows(screen.getByTestId('asset-search-result-1'), screen.getByTestId('asset-search-report-row')), 'the report row closes the list').toBe(true);
    });

    it('ASA-F9: the report row comes after the 👑 legend', async () => {
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'IE00B4L5Y983', {display_name: 'iShares Core MSCI World 👑 EUR'})]), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('world');
        await waitFor(() => expect(state()).toBe('results'));

        expect(follows(screen.getByTestId('asset-search-crown-legend'), screen.getByTestId('asset-search-report-row'))).toBe(true);
    });
});

// --- P20 report ---
describe('AssetSearchAutocomplete — «Can’t find it? Let us know» (P20)', () => {
    afterEach(() => {
        instance.supportUrl = null;
        // A one-shot answer a failed case did not consume must not reach the next one.
        vi.mocked(writeTextToClipboard).mockReset();
        vi.mocked(notify).mockReset();
        restSearch.mockReset();
    });

    /** What the component told through notify(), in order: the structured half of each notification. */
    const notified = () => vi.mocked(notify).mock.calls.map(([options]) => options);

    /** The toast is a field of notify(): none is shown besides — one notification, never two. */
    function expectNoToastBesides(): void {
        for (const direct of [toasts.show, toasts.success, toasts.warning, toasts.error, toasts.info]) expect(direct, 'a toast shown besides notify()’s').not.toHaveBeenCalled();
    }

    it('ASA-R1: the report row waits for the search to end — absent before it and while it runs, there once it is over', async () => {
        const held = heldSse([answered('alpha', [hit('alpha', 'A1')])], [answered('beta', [hit('beta', 'B1')]), DONE]);
        global.fetch = vi.fn(async () => held.response) as never;
        try {
            await mountReady();
            expect(screen.queryByTestId('asset-search-report-row'), 'no search yet').toBeNull();

            await type('apple');
            await waitFor(() => expect(screen.getByTestId('asset-search-result-0')).toHaveAttribute('data-identifier', 'A1'));
            expect(state(), 'alpha answered, beta has not: the search is still running').toBe('searching');
            expect(screen.queryByTestId('asset-search-report-row'), 'no report while the search runs').toBeNull();

            held.release();

            await waitFor(() => expect(state()).toBe('results'));
            expect(screen.getByTestId('asset-search-report-row')).toBeInTheDocument();
        } finally {
            held.release();
        }
    });

    it('ASA-R2: no support address: a new GitHub issue in a new tab, prefilled with the search and its outcome; the click copies nothing', async () => {
        const question = catalogue('assets.search.reportQuestion');
        const action = catalogue('assets.search.reportAction');
        const via = catalogue('assets.search.reportVia.github');
        global.fetch = vi.fn(async () => sseResponse([answered('beta', [hit('beta', 'B1')]), answered('alpha', [hit('alpha', 'A1')]), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        const row = screen.getByTestId('asset-search-report-row');
        expect(screen.getByTestId('asset-search-results').contains(row), 'the row is part of the dropdown').toBe(true);
        expect(follows(screen.getByTestId('asset-search-result-1'), row), 'after the results').toBe(true);
        expect(normalize(row.textContent)).toContain(normalize(question));
        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'github');
        expect(normalize(link.textContent)).toBe(normalize(action));
        expect(link).toHaveAttribute('title', via);
        expect(link).toHaveAttribute('target', '_blank');
        expect((link.getAttribute('rel') ?? '').split(/\s+/)).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));

        const {subject, lines} = githubReport(link);
        expect(subject).toBe('LibreFolio: asset not found — apple');
        expect(lines[0]).toBe('I searched LibreFolio for an asset and could not find it.');
        expect(lines).toContain('Search: apple');
        expect(providerLines(lines), 'in the order of the provider toggles, not of the answers').toEqual(['- alpha: 1 result', '- beta: 1 result']);
        const formLines = lines.filter((line) => line.startsWith('In the form:'));
        expect(formLines, 'no reportContext, no form line').toEqual([]);
        expect(lines).toContain(appLine());
        expect(link.getAttribute('href'), 'never the address of the instance').not.toContain(window.location.host);

        await clickLink(link);
        expect(writeTextToClipboard, 'the issue carries the report: nothing to copy').not.toHaveBeenCalled();
        expect(notify, 'nothing copied, nothing to announce').not.toHaveBeenCalled();

        // The whole link, as the pure functions write it for this search.
        const report = expectedReport('apple', [
            {code: 'alpha', status: 'results', count: 1},
            {code: 'beta', status: 'results', count: 1},
        ]);
        expect(link.getAttribute('href')).toBe(reportHref({kind: 'github', url: GITHUB_NEW_ISSUE_URL}, report));
    });

    it('ASA-R3: the outcome of each provider the search queried, in the order of the toggles: results counted, errors by their code — never their message', async () => {
        listProviders.mockResolvedValue(['alpha', 'beta', 'gamma', 'delta', 'epsilon'].map((code) => ({code, name: code.toUpperCase(), supports_search: true})) as never);
        // The answers come in the reverse order of the toggles; epsilon is switched off first: not queried, not listed.
        global.fetch = vi.fn(async () => sseResponse([failed('delta'), {...failed('gamma', 'RATE_LIMITED'), retry_after: 30}, answered('beta', []), answered('alpha', [hit('alpha', 'A1')]), DONE])) as never;
        await mountReady();
        await fireEvent.click(screen.getByTestId('asset-search-provider-epsilon'));
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));
        expect(queried(fetchUrls().at(-1)), 'precondition: epsilon was not queried').toEqual(['alpha', 'beta', 'gamma', 'delta']);

        const {lines} = githubReport(await reportLink());
        expect(providerLines(lines)).toEqual(['- alpha: 1 result', '- beta: 0 results', '- gamma: error RATE_LIMITED', '- delta: error']);
        expect(lines.join('\n'), 'a provider’s error message stays out of the report').not.toContain('tk-SECRET-77');
    });

    it('ASA-R4: on the REST fallback, the outcome comes from providers_queried, providers_not_configured and providers_with_errors', async () => {
        listProviders.mockResolvedValue(['alpha', 'beta', 'gamma', 'delta'].map((code) => ({code, name: code.toUpperCase(), supports_search: true})) as never);
        global.fetch = vi.fn(async () => sseResponse([], {ok: false})) as never;
        restSearch.mockResolvedValueOnce({
            query: 'apple',
            total_results: 2,
            results: [hit('alpha', 'A1'), hit('alpha', 'A2')],
            providers_queried: ['delta', 'gamma', 'beta', 'alpha'],
            providers_with_errors: ['gamma', 'beta'],
            providers_not_configured: ['beta'],
        } as never);
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));
        expect(restSearch).toHaveBeenCalledTimes(1);

        const {lines} = githubReport(await reportLink());
        expect(providerLines(lines)).toEqual(['- alpha: 2 results', '- beta: error NOT_CONFIGURED', '- gamma: error', '- delta: 0 results']);
    });

    it.each([
        {
            label: 'before any provider answered',
            search: async () => {
                throw new DOMException('The operation was aborted.', 'AbortError');
            },
            outcome: ['- alpha: no answer', '- beta: no answer'],
        },
        {label: 'after alpha answered', search: async () => cutSse([answered('alpha', [hit('alpha', 'A1')])]), outcome: ['- alpha: 1 result', '- beta: no answer']},
    ])('ASA-R5: the search reaches its time cap $label: the report row is under the message, and a provider that never answered says so', async ({search, outcome}) => {
        global.fetch = vi.fn(search) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('error'));
        expect(restSearch, 'the time cap, not the REST fallback').not.toHaveBeenCalled();

        const {lines} = githubReport(await reportLink());
        expect(lines).toContain('Search: apple');
        expect(providerLines(lines)).toEqual(outcome);
    });

    it('ASA-R6: the stream and the REST fallback both fail: the report row is under the error', async () => {
        global.fetch = vi.fn(async () => {
            throw new Error('network down');
        }) as never;
        restSearch.mockRejectedValueOnce(new Error('rest down'));
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('error'));

        const {subject, lines} = githubReport(await reportLink());
        expect(subject).toBe('LibreFolio: asset not found — apple');
        expect(lines).toContain('Search: apple');
    });

    it('ASA-R7: nothing found: the report row is under «no results»', async () => {
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('zzz');
        await waitFor(() => expect(state()).toBe('empty'));

        const link = await reportLink();
        expect(screen.getByTestId('asset-search-results').contains(link), 'the row is part of the dropdown').toBe(true);
        const {lines} = githubReport(link);
        expect(lines).toContain('Search: zzz');
        expect(providerLines(lines)).toEqual(['- alpha: 0 results', '- beta: 0 results']);
    });

    it('ASA-R8: a mailto: support address: a mail to it, subject and body prefilled, line breaks CRLF; no new tab, nothing copied', async () => {
        instance.supportUrl = 'mailto:support@example.org';
        const via = catalogue('assets.search.reportVia.mailto');
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'mailto');
        expect(link).toHaveAttribute('title', via);
        expect(link, 'a mail opens no tab').not.toHaveAttribute('target');
        const href = link.getAttribute('href') ?? '';
        const parts = /^mailto:support@example\.org\?subject=([^&]*)&body=([^&]*)$/.exec(href);
        expect(parts, `not mailto:<address>?subject=…&body=…: ${href}`).not.toBeNull();
        expect(decodeURIComponent(parts![1])).toBe('LibreFolio: asset not found — apple');
        const body = decodeURIComponent(parts![2]);
        expect(body.replace(/\r\n/g, ''), 'every line break is CRLF').not.toContain('\n');
        const lines = body.split('\r\n');
        expect(lines).toContain('Search: apple');
        expect(providerLines(lines)).toEqual(['- alpha: 1 result', '- beta: 0 results']);
        expect(lines).toContain(appLine());

        await clickLink(link);
        expect(writeTextToClipboard, 'a mail carries its body: nothing to copy').not.toHaveBeenCalled();
        expect(notify, 'nothing copied, nothing to announce').not.toHaveBeenCalled();

        const report = expectedReport('apple', [
            {code: 'alpha', status: 'results', count: 1},
            {code: 'beta', status: 'results', count: 0},
        ]);
        expect(href).toBe(reportHref({kind: 'mailto', address: 'support@example.org'}, report));
    });

    it('ASA-R9: an http(s) support page opens in a new tab; the click copies the report for it and, once the copy is done, notify() says so; the dropdown stays open', async () => {
        const page = 'https://help.example.org/assets?from=librefolio';
        instance.supportUrl = page;
        const via = catalogue('assets.search.reportVia.page');
        const copied = catalogue('assets.search.reportCopied');
        const context: SearchReportContext = {currency: 'EUR', assetType: 'ETF', identifiers: [{type: 'ISIN', value: 'IE00BK5BQT80'}]};
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), failed('beta', 'NOT_CONFIGURED'), DONE])) as never;
        await mountReady({reportContext: context});
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'page');
        expect(link).toHaveAttribute('href', page);
        expect(link).toHaveAttribute('title', via);
        expect(link).toHaveAttribute('target', '_blank');
        expect((link.getAttribute('rel') ?? '').split(/\s+/)).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
        expect(writeTextToClipboard, 'nothing is copied before the click').not.toHaveBeenCalled();

        // The copy is held: what the component says must wait for its outcome.
        let finishCopy!: () => void;
        vi.mocked(writeTextToClipboard).mockReturnValueOnce(new Promise<void>((resolve) => (finishCopy = resolve)));
        try {
            await clickLink(link);

            // The write starts within the click — the page opens in the same gesture.
            expect(writeTextToClipboard).toHaveBeenCalledTimes(1);
            const [text] = vi.mocked(writeTextToClipboard).mock.calls[0];
            const lines = text.split('\n');
            expect(lines[0]).toBe('I searched LibreFolio for an asset and could not find it.');
            expect(lines).toContain('Search: apple');
            expect(providerLines(lines)).toEqual(['- alpha: 1 result', '- beta: error NOT_CONFIGURED']);
            expect(lines).toContain('In the form: currency EUR, type ETF, ISIN IE00BK5BQT80');
            expect(lines).toContain(appLine());
            expect(notify, 'nothing is said while the copy is under way').not.toHaveBeenCalled();

            finishCopy();

            // Once it is done: one notification, its structured half — the toast's words are the catalogue's key, wired.
            await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
            const [event] = notified();
            expect(event.name).toBe('assets.search.report.copied');
            expect(event.detail).toStrictEqual({channel: 'page'});
            expect(event.toast?.variant).toBe('success');
            expect(event.toast?.message, 'the toast is worded by assets.search.reportCopied').toBe(copied);
            expectNoToastBesides();
            expect(screen.getByTestId('asset-search-results').contains(link), 'the link is inside the dropdown, and the dropdown stays open').toBe(true);

            const report = expectedReport(
                'apple',
                [
                    {code: 'alpha', status: 'results', count: 1},
                    {code: 'beta', status: 'error', errorCode: 'NOT_CONFIGURED'},
                ],
                context,
            );
            expect(text).toBe(report.body);
        } finally {
            finishCopy();
        }
    });

    it('ASA-R10: the copy fails: notify() warns that the report was not copied — one notification, never a success', async () => {
        instance.supportUrl = 'https://help.example.org/assets';
        const copyFailed = catalogue('assets.search.reportCopyFailed');
        vi.mocked(writeTextToClipboard).mockRejectedValueOnce(new Error('Clipboard copy was rejected.'));
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('empty'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'page');
        await clickLink(link);

        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        expect(writeTextToClipboard).toHaveBeenCalledTimes(1);
        const [event] = notified();
        expect(event.name).toBe('assets.search.report.copyFailed');
        expect(event.detail).toStrictEqual({channel: 'page'});
        expect(event.toast?.variant).toBe('warning');
        expect(event.toast?.message, 'the toast is worded by assets.search.reportCopyFailed').toBe(copyFailed);
        expectNoToastBesides();
    });

    it('ASA-R11: a support address that is neither an http(s) page nor a mailto: — javascript:alert(1) — sends the report to GitHub; no such href anywhere in the dropdown', async () => {
        instance.supportUrl = 'javascript:alert(1)';
        const via = catalogue('assets.search.reportVia.github');
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'github');
        expect(link).toHaveAttribute('title', via);
        expect(githubReport(link).lines).toContain('Search: apple');
        const hrefs = [...document.querySelectorAll('[data-search-autocomplete] [href]')].map((element) => element.getAttribute('href') ?? '');
        expect(hrefs.filter((href) => /^\s*javascript:/i.test(href))).toEqual([]);
    });

    it('ASA-R12: the form the caller passes (reportContext) is in the report, its blank identifiers left out', async () => {
        const context: SearchReportContext = {
            currency: 'CHF',
            assetType: 'BOND',
            identifiers: [
                {type: 'ISIN', value: 'CH0012032048'},
                {type: 'TICKER', value: '   '},
                {type: 'OTHER', value: ' swiss-conf-2031 '},
            ],
        };
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])) as never;
        await mountReady({reportContext: context});
        await type('confederation 2031');
        await waitFor(() => expect(state()).toBe('empty'));

        const {lines} = githubReport(await reportLink());
        expect(lines).toContain('Search: confederation 2031');
        expect(lines.filter((line) => line.startsWith('In the form:'))).toEqual(['In the form: currency CHF, type BOND, ISIN CH0012032048, OTHER swiss-conf-2031']);
    });

    it('ASA-R13: the report is the last search’s: its query and the outcome of its providers', async () => {
        global.fetch = vi.fn(async (url: string) => (url.includes('q=micro') ? sseResponse([answered('alpha', []), failed('beta', 'RATE_LIMITED'), DONE]) : sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('beta', [hit('beta', 'B1')]), DONE]))) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));
        expect(githubReport(await reportLink()).lines).toContain('Search: apple');

        await type('micro');
        await waitFor(() => expect(state()).toBe('empty'));

        const {subject, lines} = githubReport(await reportLink());
        expect(subject).toBe('LibreFolio: asset not found — micro');
        expect(lines).toContain('Search: micro');
        expect(lines).not.toContain('Search: apple');
        expect(providerLines(lines)).toEqual(['- alpha: 0 results', '- beta: error RATE_LIMITED']);
    });

    it('ASA-R14: with the UI in Italian the report is still written in English; its labels follow the UI, its language line says it', async () => {
        await setupI18n('it');
        currentLanguage.set('it');
        try {
            const question = catalogue('assets.search.reportQuestion');
            const action = catalogue('assets.search.reportAction');
            global.fetch = vi.fn(async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])) as never;
            await mountReady();
            await type('zzz');
            await waitFor(() => expect(state()).toBe('empty'));

            const link = await reportLink();
            expect(normalize(screen.getByTestId('asset-search-report-row').textContent)).toContain(normalize(question));
            expect(normalize(link.textContent)).toBe(normalize(action));
            const {subject, lines} = githubReport(link);
            expect(subject).toBe('LibreFolio: asset not found — zzz');
            expect(lines[0]).toBe('I searched LibreFolio for an asset and could not find it.');
            expect(lines.at(-1)).toBe("Anything else that helps (the exchange, a link to the asset's page):");
            expect(lines).toContain(appLine('it'));
        } finally {
            currentLanguage.set('en');
            await setupI18n('en');
        }
    });

    it.each([
        {label: 'found nothing', finished: 'empty', search: async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])},
        {
            label: 'failed',
            finished: 'error',
            search: async () => {
                throw new DOMException('The operation was aborted.', 'AbortError');
            },
        },
    ])('ASA-R15: the search $label, the dropdown closed by a click outside: a focus brings it back with the report row, until the input is cleared', async ({finished, search}) => {
        global.fetch = vi.fn(search) as never;
        await mountReady();
        const input = await type('zzz');
        await waitFor(() => expect(state()).toBe(finished));
        expect(within(screen.getByTestId('asset-search-results')).getByTestId('asset-search-report-row'), 'precondition: the finished search offers the report').toBeInTheDocument();
        const searches = fetchUrls().length;

        // A click elsewhere closes the dropdown, and the report row with it.
        await fireEvent.click(document.body);
        await waitFor(() => expect(screen.queryByTestId('asset-search-results')).toBeNull());
        expect(screen.queryByTestId('asset-search-report-row')).toBeNull();

        // (a) Back in the box: the finished search is shown again, its report row too — shown, not searched again.
        await fireEvent.focusIn(input);
        await waitFor(() => expect(state()).toBe(finished));
        const link = await reportLink();
        expect(screen.getByTestId('asset-search-results').contains(link), 'the row is back inside the dropdown').toBe(true);
        expect(githubReport(link).lines, 'the report of that same search').toContain('Search: zzz');
        expect(fetchUrls(), 'the focus shows the last search: it does not search again').toHaveLength(searches);

        // (b) The input cleared, the last search is forgotten: the same focus that reopened it now opens nothing.
        await type('');
        expect(screen.queryByTestId('asset-search-results')).toBeNull();
        await fireEvent.focusIn(input);
        expect(screen.queryByTestId('asset-search-results'), 'no search to show: no dropdown').toBeNull();
        expect(screen.queryByTestId('asset-search-report-row'), 'no report of a search that is gone').toBeNull();
        expect(fetchUrls()).toHaveLength(searches);
    });
});

// --- X-R37 / N61: where a report may go ---
describe('AssetSearchAutocomplete — a report needs a channel (X-R37, N61)', () => {
    afterEach(() => {
        Object.assign(instance, {supportUrl: null, profile: 'selfhosted', loaded: true, failed: false});
    });

    /** Every address anywhere in the component, hidden or not. */
    const hrefs = (): string[] => [...document.querySelectorAll('[data-search-autocomplete] [href]')].map((element) => element.getAttribute('href') ?? '');

    it.each([
        {label: 'results', finished: 'results', rows: ['A1'], search: async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('beta', []), DONE])},
        {label: 'no result', finished: 'empty', rows: [], search: async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])},
        {
            label: 'an error (the time cap)',
            finished: 'error',
            rows: [],
            search: async () => {
                throw new DOMException('The operation was aborted.', 'AbortError');
            },
        },
    ])('ASA-S1: a managed instance with no support address: a search over with $label shows no report row — a public issue would publish it', async ({finished, rows, search}) => {
        instance.profile = 'managed';
        global.fetch = vi.fn(search) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe(finished));

        // The search is over and drawn: on a self-hosted instance its report row is there by now (ASA-R2, R5, R7).
        expect(shown()).toEqual(rows);
        expect(screen.queryByTestId('asset-search-report-row')).toBeNull();
        expect(screen.queryByTestId('asset-search-report')).toBeNull();
        const github = hrefs().filter((href) => href.includes('github.com'));
        expect(github, 'no way to a GitHub issue anywhere').toEqual([]);
    });

    it('ASA-S2: a managed instance with a mailto: support address: the row is there, a mail to that address, and its report says managed', async () => {
        instance.profile = 'managed';
        instance.supportUrl = 'mailto:support@example.org';
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('empty'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'mailto');
        const href = link.getAttribute('href') ?? '';
        const parts = /^mailto:support@example\.org\?subject=([^&]*)&body=([^&]*)$/.exec(href);
        expect(parts, `not mailto:support@example.org?subject=…&body=…: ${href}`).not.toBeNull();
        const lines = decodeURIComponent(parts![2]).split('\r\n');
        expect(lines).toContain('Search: apple');
        expect(lines).toContain(`LibreFolio ${APP_VERSION}, managed, language ${get(currentLanguage)}`);
    });

    it('ASA-S3: a managed instance with a valid support page: the row is there, a link to that page', async () => {
        instance.profile = 'managed';
        instance.supportUrl = 'https://help.example.org/assets';
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'page');
        expect(link).toHaveAttribute('href', 'https://help.example.org/assets');
    });

    it('ASA-S4: a managed instance whose support page carries a user and a password: that address counts as none — no row, and it is never linked', async () => {
        instance.profile = 'managed';
        instance.supportUrl = 'https://user:pass@help.example.org';
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        expect(shown()).toEqual(['A1']);
        expect(screen.queryByTestId('asset-search-report-row')).toBeNull();
        expect(hrefs().filter((href) => href.includes('help.example.org') || href.includes('github.com'))).toEqual([]);
    });

    it.each([
        {label: 'its request failed', failed: true},
        {label: 'it has not answered yet', failed: false},
    ])('ASA-S5: the instance configuration not loaded — $label — and no support address: no row, though its defaults say selfhosted', async ({failed}) => {
        // What the real store holds before an answer: the defaults, a self-hosted instance. Only `loaded` tells.
        instance.loaded = false;
        instance.failed = failed;
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('empty'));

        expect(screen.queryByTestId('asset-search-report-row')).toBeNull();
        expect(hrefs().filter((href) => href.includes('github.com'))).toEqual([]);
    });

    it('ASA-S6: a self-hosted instance whose support page carries a user and a password: refused as no address, so the GitHub issue — never that page', async () => {
        instance.supportUrl = 'https://user:pass@help.example.org';
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('results'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'github');
        expect(githubReport(link).lines).toContain('Search: apple');
        expect(hrefs().filter((href) => href.includes('help.example.org'))).toEqual([]);
    });

    it('ASA-S7: grouped, with no channel: the community section’s button follows the Premium section directly — no row between, nor anywhere', async () => {
        instance.profile = 'managed';
        listProviders.mockResolvedValue(RANKED as never);
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', [hit('alpha', 'A1')]), answered('prime', [hit('prime', 'P1')]), answered('beta', []), answered('vault', []), DONE])) as never;
        await mountReady();
        await type('world');
        await waitFor(() => expect(state()).toBe('results'));

        const premium = screen.getByTestId('asset-search-premium-section');
        const toggle = screen.getByTestId('asset-search-community-toggle');
        expect(shown()).toEqual(['P1']);
        expect(premium.nextElementSibling, 'the button comes right after the Premium section').toBe(toggle);
        expect(screen.queryByTestId('asset-search-report-row')).toBeNull();

        await fireEvent.click(toggle);

        await waitFor(() => expect(screen.getByTestId('asset-search-community-toggle')).toHaveAttribute('aria-expanded', 'true'));
        expect(shown()).toEqual(['P1', 'A1']);
        expect(screen.queryByTestId('asset-search-report-row'), 'nor under the community results').toBeNull();
        expect(hrefs().filter((href) => href.includes('github.com'))).toEqual([]);
    });

    it('ASA-S8: a support page written without its slashes (https:help.example.org/assets) is linked by its absolute address, never as a path of the instance', async () => {
        instance.supportUrl = 'https:help.example.org/assets';
        global.fetch = vi.fn(async () => sseResponse([answered('alpha', []), answered('beta', []), DONE])) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('empty'));

        const link = await reportLink();
        expect(link).toHaveAttribute('data-channel', 'page');
        expect(link).toHaveAttribute('href', 'https://help.example.org/assets');
    });
});

// --- X-R31: a failed search speaks the language of the UI ---
describe('AssetSearchAutocomplete — a failed search says so in the UI’s language (X-R31)', () => {
    afterEach(() => {
        // A one-shot answer a failed case did not consume must not reach the next one.
        restSearch.mockReset();
    });

    it('ASA-T1: the stream and the REST fallback both fail: the dropdown says assets.search.failed, never the error’s own message, and the error still goes to console.error', async () => {
        // The component logs the failure: spied to prove it still does, and silenced so the run stays readable.
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        try {
            const boom = new Error('boom 42');
            global.fetch = vi.fn(async () => {
                throw new Error('network down');
            }) as never;
            restSearch.mockRejectedValueOnce(boom);
            await mountReady();
            await type('apple');
            await waitFor(() => expect(state()).toBe('error'));
            expect(restSearch, 'precondition: the stream failed, so the search fell back to REST — which failed too').toHaveBeenCalledTimes(1);

            const shownText = normalize(screen.getByTestId('asset-search-results').textContent);
            expect(shownText, 'the error’s own message must never reach the user').not.toContain('boom 42');
            expect(shownText, 'the catalogue’s assets.search.failed, in the language in force').toContain(normalize(catalogue('assets.search.failed')));
            expect(consoleError.mock.calls.flat(), 'the error itself still goes to console.error').toContain(boom);
        } finally {
            consoleError.mockRestore();
        }
    });

    it('ASA-T2: guard — a search cut by the time cap still says assets.search.timeout, without asking REST', async () => {
        const timeout = catalogue('assets.search.timeout');
        global.fetch = vi.fn(async () => {
            throw new DOMException('The operation was aborted.', 'AbortError');
        }) as never;
        await mountReady();
        await type('apple');
        await waitFor(() => expect(state()).toBe('error'));
        expect(restSearch, 'the time cap does not fall back to REST').not.toHaveBeenCalled();

        expect(normalize(screen.getByTestId('asset-search-results').textContent)).toContain(normalize(timeout));
    });
});
