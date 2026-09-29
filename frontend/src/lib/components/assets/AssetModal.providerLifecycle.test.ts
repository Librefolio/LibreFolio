// @vitest-environment jsdom
/**
 * Real AssetModal + ProviderAssignmentSection + providerProbeState orchestration.
 *
 * Only AssetSearchAutocomplete is replaced, in BOTH create and edit mode. Its
 * harness invokes the real lowercase onselect callback; it owns no draft or
 * request lifecycle. A case may swap only the synthetic RESULT it hands over
 * (`searchSelection`; null keeps the harness's own TICKER), never the callback.
 * Comparison/confirmation modals and the session coordinator remain real.
 * Everything asynchronous below is an explicitly planned API call, apart from
 * ready reference caches and the incidental duplicate-name listing.
 *
 * Deferred responses, then Svelte tick/flushSync, are the completion boundaries.
 * No network, clock waits, mirrored controller, detached callbacks or UI events
 * behind an active modal. Request oracles are independent of UI-bound fixtures;
 * captured argument REFERENCES are checked again after edits and at teardown.
 *
 * Deliberate interface gaps: autofill provenance, provider URL, total duration
 * and the chooser's report/stored provenance badge have no semantic testid/state
 * here. Stale comparison/confirmation callbacks cannot safely be clicked once
 * their real dialog has closed. Those are not replaced with CSS/source
 * assertions or calls into detached elements.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick, type Component, type ComponentProps} from 'svelte';
import type {z} from 'zod';
import type {schemas} from '$lib/api/generated';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, transitionClientSession} from '$lib/stores/app/clientSession';
import {userSettings} from '$lib/stores/app/settings';
import {currentLanguage} from '$lib/stores/app/language';
import {currencyStoreVersion, type CurrencyInfo} from '$lib/stores/reference/currencyStore';
import type {CountryInfo} from '$lib/stores/reference/countryStore';
import AssetModal from './AssetModal.svelte';
import type AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';

type ProbeRequest = z.infer<typeof schemas.FAProviderProbeRequest>;
type ProbeResponse = z.infer<typeof schemas.FAProviderProbeResponse>;
type ProviderInfo = z.infer<typeof schemas.FAProviderInfo>;
type PatchItem = z.infer<typeof schemas.FAAssetPatchItem>;
type PatchResponse = z.infer<typeof schemas.FABulkAssetPatchResponse>;
type AssignmentItem = z.infer<typeof schemas.FAProviderAssignmentItem>;
type AssignmentResponse = z.infer<typeof schemas.FABulkAssignResponse>;
type EditData = NonNullable<ComponentProps<typeof AssetModal>['editData']>;
type VerificationStatus = 'not_tested' | 'testing' | 'passed' | 'failed';
type ResultStatus = 'success' | 'error' | 'warning';
type SearchProps = ComponentProps<typeof AssetSearchAutocomplete>;
type SearchSelection = Parameters<NonNullable<SearchProps['onselect']>>[0];

const mocks = vi.hoisted(() => ({
    // Explicit facade: even forbidden mutation/search/reference requests are
    // recorded before throwing, because the product catches several of them.
    api: {
        list_providers_api_v1_assets_provider_get: vi.fn(),
        probe_provider_config_api_v1_assets_provider_probe_post: vi.fn(),
        list_assets_api_v1_assets_query_get: vi.fn(),
        patch_assets_bulk_api_v1_assets_patch: vi.fn(),
        assign_providers_bulk_api_v1_assets_provider_post: vi.fn(),
        create_assets_bulk_api_v1_assets_post: vi.fn(),
        remove_providers_bulk_api_v1_assets_provider_delete: vi.fn(),
        sync_prices_bulk_api_v1_assets_prices_sync_post: vi.fn(),
        search_assets_via_providers_api_v1_assets_provider_search_get: vi.fn(),
        market_data_summary_api_v1_assets__asset_id__market_data_summary_get: vi.fn(),
        wipe_market_data_api_v1_assets__asset_id__market_data_wipe_post: vi.fn(),
        list_routes_api_v1_fx_providers_routes_get: vi.fn(),
        list_currencies_api_v1_utilities_currencies_get: vi.fn(),
        list_countries_api_v1_utilities_countries_get: vi.fn(),
        list_sectors_api_v1_utilities_sectors_get: vi.fn(),
        list_files_api_v1_uploads_get: vi.fn(),
    },
    axios: {request: vi.fn(), get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn()},
    providers: {
        ensureAssetProvidersCached: vi.fn(),
        getAssetProviderName: vi.fn(),
        getAssetProviderIconUrl: vi.fn(),
        isParametricProvider: vi.fn(),
    },
    currencies: {
        ensureCurrenciesLoaded: vi.fn(),
        getAllCurrencies: vi.fn(),
        getCurrencyInfo: vi.fn(),
        isCurrenciesLoaded: vi.fn(),
    },
    countries: {ensureCountriesLoaded: vi.fn(), getAllCountries: vi.fn(), getCountryInfo: vi.fn()},
    sectors: {ensureSectorsLoaded: vi.fn(), getSectorKeys: vi.fn(), getSectorEmoji: vi.fn()},
    assets: {mergeAssets: vi.fn(), invalidateAfterMutation: vi.fn()},
    toasts: {success: vi.fn(), info: vi.fn(), warning: vi.fn(), error: vi.fn()},
}));
// Kept out of `mocks`: beforeEach resets every member of that object as a spy.
const searchSelection = vi.hoisted(() => ({result: null as SearchSelection | null}));

vi.mock('$lib/api', () => ({zodiosApi: mocks.api, axiosInstance: mocks.axios}));
vi.mock('./AssetSearchAutocomplete.svelte', async () => {
    const Harness = (await import('$test/AssetSearchSelectionHarness.svelte')).default;
    // The same harness and the same real onselect; only the RESULT may differ.
    const Selection: Component<SearchProps> = (internals, props) =>
        Harness(internals, {
            get disabled() {
                return props.disabled;
            },
            get onselect() {
                const onselect = props.onselect;
                return onselect && ((result: SearchSelection) => onselect(searchSelection.result ?? result));
            },
        });
    return {default: Selection};
});
vi.mock('$lib/utils/providerHelpers', () => mocks.providers);
vi.mock('$lib/stores/reference/assetStore', () => mocks.assets);
vi.mock('$lib/stores/reference/countryStore', () => mocks.countries);
vi.mock('$lib/stores/reference/sectorStore', () => mocks.sectors);
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: mocks.toasts}));
vi.mock('$lib/stores/reference/currencyStore', async () => {
    const {writable} = await import('svelte/store');
    return {...mocks.currencies, currencyStoreVersion: writable(0)};
});
vi.mock('$lib/stores/app/settings', async () => {
    const {writable} = await import('svelte/store');
    const store = writable<ReturnType<typeof userSettings.get>>(null);
    const settings: Pick<typeof userSettings, 'subscribe' | 'reset'> = {
        subscribe: store.subscribe,
        reset: () => store.set(null),
    };
    return {userSettings: settings};
});
vi.mock('$lib/stores/app/language', async () => {
    const {writable} = await import('svelte/store');
    return {currentLanguage: writable('en')};
});
vi.mock('svelte/transition', async (importOriginal) => {
    const transitions = await importOriginal<typeof import('svelte/transition')>();
    // Visual boundary only: retain real ModalBase, handlers and conditional
    // mounts, but do not make a jsdom assertion depend on fade/scale duration.
    return {...transitions, fade: () => ({duration: 0}), scale: () => ({duration: 0})};
});

const routes = {
    catalog: 'GET /api/v1/assets/provider',
    verification: 'POST /api/v1/assets/provider/probe [current_price,history]',
    metadata: 'POST /api/v1/assets/provider/probe [metadata]',
    patch: 'PATCH /api/v1/assets',
    assign: 'POST /api/v1/assets/provider',
} as const;
type Route = (typeof routes)[keyof typeof routes];

interface RecordedCall {
    path: string;
    args: unknown[];
}

interface PlannedCall {
    label: string;
    route: Route;
    expectedArgs: unknown[];
    actualArgs?: unknown[];
    response: Promise<unknown>;
    release: () => void;
    finish: () => Promise<void>;
    assertUnchanged: () => void;
}

let plannedCalls: PlannedCall[] = [];
let recordedCalls: RecordedCall[] = [];
let unexpectedCalls: RecordedCall[] = [];
let referenceReady: Promise<void>;
let previousSessionId: ReturnType<typeof getClientSessionUserId> = null;
const localStorageDescriptors = new Map<object, PropertyDescriptor | undefined>();

/** Freeze only independent expected data, never the component's props/args. */
function immutable<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const child of Object.values(value)) immutable(child);
        Object.freeze(value);
    }
    return value;
}

async function flushUi() {
    await tick();
    flushSync();
}

function installLocalStorageFixture(): void {
    // Own the Storage implementation, not the runner's optional global alias.
    // Neither installing nor restoring it evaluates an environment getter.
    const backing = new Map<string, string>();
    const storage: Storage = {
        get length() {
            return backing.size;
        },
        clear() {
            backing.clear();
        },
        getItem(key: string) {
            return backing.get(String(key)) ?? null;
        },
        key(index: number) {
            return [...backing.keys()][index] ?? null;
        },
        removeItem(key: string) {
            backing.delete(String(key));
        },
        setItem(key: string, value: string) {
            backing.set(String(key), String(value));
        },
    };

    const targets = new Set<object>([globalThis, window]);
    // Capture both descriptors before changing either: jsdom may expose aliases.
    for (const target of targets) {
        localStorageDescriptors.set(target, Object.getOwnPropertyDescriptor(target, 'localStorage'));
    }
    for (const target of targets) {
        Object.defineProperty(target, 'localStorage', {value: storage, configurable: true, writable: true});
    }
}

function restoreLocalStorageFixture(): void {
    // Always iterable, even if beforeEach aborted before installation completed.
    for (const [target, descriptor] of localStorageDescriptors) {
        if (descriptor) Object.defineProperty(target, 'localStorage', descriptor);
        else Reflect.deleteProperty(target, 'localStorage');
    }
    localStorageDescriptors.clear();
}

function unexpected(path: string, args: unknown[]): never {
    unexpectedCalls.push({path, args});
    throw new Error(`Unplanned AssetModal request: ${path}`);
}

function checkArguments(path: string, actual: unknown[], expected: unknown[]) {
    try {
        expect(actual, path).toStrictEqual(expected);
    } catch (error) {
        // An assertion thrown inside a caught API call must remain observable.
        unexpectedCalls.push({path, args: actual});
        throw error;
    }
}

function consume(route: Route, args: unknown[]): Promise<unknown> {
    recordedCalls.push({path: route, args});
    const call = plannedCalls.find((candidate) => candidate.route === route && candidate.actualArgs === undefined);
    if (!call) return unexpected(route, args);
    call.actualArgs = args; // Deliberately NOT a JSON snapshot.
    checkArguments(`${route}: ${call.label}`, args, call.expectedArgs);
    return call.response;
}

function plan<T>(label: string, route: Route, expectedArgs: unknown[], value: T): PlannedCall {
    let resolve!: (value: T) => void;
    let released = false;
    const response = new Promise<T>((done) => {
        resolve = done;
    });
    const call: PlannedCall = {
        label,
        route,
        expectedArgs: immutable(expectedArgs),
        response,
        release() {
            if (!released) {
                released = true;
                resolve(value);
            }
        },
        async finish() {
            call.assertUnchanged();
            call.release();
            await response;
            await flushUi();
        },
        assertUnchanged() {
            expect(call.actualArgs, `${label}: expected request was consumed`).toBeDefined();
            expect(call.actualArgs, `${label}: captured request must stay immutable`).toStrictEqual(call.expectedArgs);
        },
    };
    plannedCalls.push(call);
    return call;
}

function assertTraffic() {
    expect(unexpectedCalls, 'caught API errors must not conceal unexpected traffic').toEqual([]);
    expect(
        plannedCalls.filter((call) => call.actualArgs === undefined).map((call) => call.label),
        'unconsumed expected calls',
    ).toEqual([]);
    expect(recordedCalls).toHaveLength(plannedCalls.length);
    for (const call of plannedCalls) call.assertUnchanged();
    // Duplicate-name debounce is incidental, not a completion boundary. Its
    // arguments are still checked; neither its timing nor its count is a claim.
    for (const args of mocks.api.list_assets_api_v1_assets_query_get.mock.calls) {
        expect(args).toStrictEqual([{queries: {}}]);
    }
}

function providerCatalog(): ProviderInfo[] {
    return [
        {
            code: 'lifecycle_atlas',
            name: 'Fictional Atlas',
            description: 'Offline lifecycle fixture, not a real provider.',
            kind: 'online_scraper',
            supports_search: true,
            supports_meaningful_volume: false,
            accepted_identifier_types: ['TICKER', 'ISIN'],
            icon_url: null,
            provider_help_url: 'https://atlas.provider.invalid/help',
            params_schema: [{key: 'note', type: 'string', required: false, label: 'Note', description: 'Synthetic provider note'}],
        },
        {
            code: 'lifecycle_beacon',
            name: 'Fictional Beacon',
            description: 'Second offline provider with the same optional text parameter.',
            kind: 'online_scraper',
            supports_search: true,
            supports_meaningful_volume: false,
            accepted_identifier_types: ['TICKER', 'ISIN'],
            icon_url: null,
            provider_help_url: 'https://beacon.provider.invalid/help',
            params_schema: [{key: 'note', type: 'string', required: false, label: 'Note', description: 'Synthetic provider note'}],
        },
    ];
}

function expectCatalog(label: string) {
    return plan(label, routes.catalog, [], providerCatalog());
}

function editFixture(overrides: Partial<EditData> = {}): EditData {
    return {
        id: 8101,
        display_name: 'Owned Atlas security',
        currency: 'USD',
        asset_type: 'STOCK',
        provider_code: 'lifecycle_atlas',
        provider_identifier: 'SYN-ATLAS',
        provider_identifier_type: 'TICKER',
        provider_params: {note: 'owned note'},
        ...overrides,
    };
}

/** Independent oracle: never assembled by reading editData or harness props. */
function probeRequest(operations: ProbeRequest['operations'], params: ProbeRequest['provider_params'] = {note: 'owned note'}): ProbeRequest {
    return {
        provider_code: 'lifecycle_atlas',
        identifier: 'SYN-ATLAS',
        identifier_type: 'TICKER',
        provider_params: params,
        operations: [...operations],
    };
}

function probeResponse(value = '42.50'): ProbeResponse {
    return {
        provider_code: 'lifecycle_atlas',
        identifier: 'SYN-ATLAS',
        provider_url: 'https://atlas.provider.invalid/probed/SYN-ATLAS',
        total_execution_time_ms: 8,
        current_price: {success: true, value, currency: 'USD', as_of_date: '2025-02-18', execution_time_ms: 3},
        history: {
            success: true,
            points_count: 2,
            date_range: '2025-02-17 → 2025-02-18',
            sample_prices: [
                {date: '2025-02-17', close: '40.00'},
                {date: '2025-02-18', close: value},
            ],
            execution_time_ms: 5,
        },
    };
}

function metadataResponse(name: string, description: string): ProbeResponse {
    return {
        provider_code: 'lifecycle_atlas',
        identifier: 'SYN-ATLAS',
        total_execution_time_ms: 4,
        metadata: {
            success: true,
            execution_time_ms: 4,
            patch_data: {
                display_name: name,
                asset_type: 'STOCK',
                currency: 'USD',
                classification_params: {short_description: description},
            },
        },
    };
}

function expectProbe(label: string, response: ProbeResponse = probeResponse(), params: ProbeRequest['provider_params'] = {note: 'owned note'}) {
    return plan(label, routes.verification, [probeRequest(['current_price', 'history'], params)], response);
}

function expectMetadata(label: string, name: string, description: string, params: ProbeRequest['provider_params'] = {note: 'owned note'}) {
    return plan(label, routes.metadata, [probeRequest(['metadata'], params)], metadataResponse(name, description));
}

function expectReady() {
    expect(screen.getByTestId('asset-modal')).toBeVisible();
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true');
    expect(screen.getByTestId('asset-modal-display-name')).toBeVisible();
    expect(screen.getByTestId('asset-modal-description')).toBeVisible();
}

function expectBusy(busy: boolean) {
    const form = screen.getByTestId('asset-modal-form');
    expect(form).toHaveAttribute('data-busy', String(busy));
    expect(form).toHaveAttribute('aria-busy', String(busy));
}

function expectStatus(status: VerificationStatus) {
    expect(screen.getByTestId('asset-modal-provider-status')).toHaveAttribute('data-status', status);
    const button = screen.getByTestId('provider-test-config');
    expect(button).toBeVisible();
    expect(button).toHaveAttribute('data-status', status);
    if (status === 'testing') expect(button).toBeDisabled();
}

function expectResults(statuses: ResultStatus[], price?: string) {
    const rows = within(screen.getByTestId('asset-modal')).getAllByTestId('provider-test-result');
    // This collection belongs to precisely the two operations in our response.
    expect(rows).toHaveLength(statuses.length);
    for (const row of rows) expect(row).toBeVisible();
    expect(rows.map((row) => row.getAttribute('data-status')).sort()).toEqual([...statuses].sort());
    // Identify history by the response-owned range, not its translated label
    // or position. An unordered error/success pair alone could hide swapped
    // operation statuses in the real child.
    const historyRows = rows.filter((row) => row.textContent?.includes('2025-02-17 → 2025-02-18'));
    expect(historyRows).toHaveLength(1);
    for (const row of historyRows) expect(row).toHaveAttribute('data-status', 'success');
    if (price !== undefined) {
        const priceRow = rows.find((row) => row.textContent?.includes(price));
        expect(priceRow, `owned current-price value ${price}`).toBeDefined();
        expect(priceRow).toHaveAttribute('data-status', 'success');
    }
}

async function input(testId: string, value: string) {
    const field = screen.getByTestId(testId);
    expect(field).toBeVisible();
    expect(field).toBeEnabled();
    await fireEvent.input(field, {target: {value}});
    await flushUi();
    expect(screen.getByTestId(testId)).toHaveValue(value);
}

async function setProviderExpanded(expanded: boolean) {
    const header = screen.getByTestId('asset-modal-provider-header');
    expect(header).toBeVisible();
    if (header.getAttribute('data-expanded') !== String(expanded)) await fireEvent.click(header);
    await flushUi();
    expect(header).toHaveAttribute('data-expanded', String(expanded));
}

async function startManualReads() {
    expect(screen.getByTestId('provider-test-config')).toBeEnabled();
    expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
    await fireEvent.click(screen.getByTestId('provider-test-config'));
    await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
    await flushUi();
    expectStatus('testing');
    expectBusy(true);
    expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();
}

async function renderEdit(data: EditData = editFixture()) {
    const catalog = expectCatalog('opening provider catalog');
    const onclose = vi.fn();
    const oncreated = vi.fn();
    const onupdated = vi.fn();
    const view = render(AssetModal, {open: true, editMode: true, editData: data, onclose, oncreated, onupdated});
    await flushUi();
    await catalog.finish();
    await referenceReady;
    await flushUi();
    expectReady();
    expect(screen.getByTestId('asset-search-offline-select')).toBeVisible();
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');
    expect(screen.getByTestId('asset-modal-more-info')).toHaveAttribute('data-expanded', 'false');
    expectStatus('not_tested');
    return {...view, onclose, oncreated, onupdated};
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    plannedCalls = [];
    recordedCalls = [];
    unexpectedCalls = [];
    searchSelection.result = null;
    referenceReady = Promise.resolve();
    previousSessionId = getClientSessionUserId();
    installLocalStorageFixture();

    for (const group of Object.values(mocks)) {
        for (const mock of Object.values(group)) mock.mockReset();
    }
    for (const [name, mock] of Object.entries(mocks.api)) {
        mock.mockImplementation((...args: unknown[]) => unexpected(name, args));
    }
    for (const [name, mock] of Object.entries(mocks.axios)) {
        mock.mockImplementation((...args: unknown[]) => unexpected(`axios.${name}`, args));
    }
    // ModalBase restores scroll on close; jsdom has no scrolling/layout engine.
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    vi.stubGlobal(
        'fetch',
        vi.fn((resource: RequestInfo | URL, init?: RequestInit) => {
            const path = typeof resource === 'string' ? resource : resource instanceof URL ? resource.href : resource.url;
            return unexpected(`fetch ${path}`, [resource, init]);
        }),
    );

    mocks.api.list_providers_api_v1_assets_provider_get.mockImplementation((...args: unknown[]) => consume(routes.catalog, args));
    mocks.api.probe_provider_config_api_v1_assets_provider_probe_post.mockImplementation((request: ProbeRequest, ...extra: unknown[]) => {
        const args = [request, ...extra];
        const operations = Array.isArray(request?.operations) ? request.operations.join(',') : 'invalid operations';
        if (operations === 'current_price,history') return consume(routes.verification, args);
        if (operations === 'metadata') return consume(routes.metadata, args);
        return unexpected(`POST /api/v1/assets/provider/probe [${operations}]`, args);
    });
    mocks.api.patch_assets_bulk_api_v1_assets_patch.mockImplementation((...args: unknown[]) => consume(routes.patch, args));
    mocks.api.assign_providers_bulk_api_v1_assets_provider_post.mockImplementation((...args: unknown[]) => consume(routes.assign, args));
    mocks.api.list_assets_api_v1_assets_query_get.mockImplementation((...args: unknown[]) => {
        checkArguments('incidental duplicate-name listing', args, [{queries: {}}]);
        return Promise.resolve([]);
    });

    const currencies: CurrencyInfo[] = [
        {code: 'USD', name: 'US dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['United States']},
        {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
    ];
    const country: CountryInfo = {iso3: 'USA', iso2: 'US', name: 'United States', flag_emoji: '🇺🇸'};
    mocks.providers.ensureAssetProvidersCached.mockReturnValue(referenceReady);
    mocks.providers.getAssetProviderName.mockImplementation((code: string) => code);
    mocks.providers.getAssetProviderIconUrl.mockReturnValue(null);
    mocks.providers.isParametricProvider.mockReturnValue(false);
    mocks.currencies.ensureCurrenciesLoaded.mockReturnValue(referenceReady);
    mocks.currencies.getAllCurrencies.mockReturnValue(currencies);
    mocks.currencies.getCurrencyInfo.mockImplementation((code: string) => {
        const currency = currencies.find((entry) => entry.code === code);
        if (!currency) throw new Error(`Unplanned reference currency: ${code}`);
        return currency;
    });
    mocks.currencies.isCurrenciesLoaded.mockReturnValue(true);
    mocks.countries.ensureCountriesLoaded.mockReturnValue(referenceReady);
    mocks.countries.getAllCountries.mockReturnValue([country]);
    mocks.countries.getCountryInfo.mockReturnValue(country);
    mocks.sectors.ensureSectorsLoaded.mockReturnValue(referenceReady);
    mocks.sectors.getSectorKeys.mockReturnValue(['Technology']);
    mocks.sectors.getSectorEmoji.mockReturnValue('🏷️');
    mocks.assets.mergeAssets.mockImplementation(() => {});
    mocks.assets.invalidateAfterMutation.mockImplementation(() => {});
    for (const toast of Object.values(mocks.toasts)) toast.mockImplementation(() => {});
    userSettings.reset();
    currentLanguage.set('en');
    currencyStoreVersion.set(0);
    transitionClientSession('asset-modal-lifecycle-owner');

    // Real DataTable persistence runs against this case's private Storage.
    // Existing environment preferences remain untouched behind their descriptors.
});

afterEach(async () => {
    try {
        // Dispose the REAL owner before releasing anything a failed assertion
        // might have left pending. Cleanup itself must not satisfy a missing call.
        await cleanup();
        flushSync();
        const unconsumed = plannedCalls.filter((call) => call.actualArgs === undefined).map((call) => call.label);
        for (const call of plannedCalls) call.release();
        await Promise.all(plannedCalls.map((call) => call.response));
        await flushUi();
        expect(unconsumed, 'calls unconsumed before teardown releases').toEqual([]);
        assertTraffic();
    } finally {
        try {
            transitionClientSession(previousSessionId);
        } finally {
            try {
                vi.unstubAllGlobals();
                vi.restoreAllMocks();
            } finally {
                restoreLocalStorageFixture();
            }
        }
    }
});

describe('AssetModal import-prefill name initialization', () => {
    it.each([
        {label: 'trimmed provided name wins', prefill: {display_name: '  Synthetic report name  ', identifier_isin: 'US0000000001', identifier_ticker: 'SYN-NAME'}, expected: 'Synthetic report name'},
        {label: 'missing name falls back to ISIN before ticker', prefill: {identifier_isin: '  US0000000001  ', identifier_ticker: 'SYN-TICKER'}, expected: 'US0000000001'},
        {label: 'blank name falls back to ISIN', prefill: {display_name: '  ', identifier_isin: 'US0000000001'}, expected: 'US0000000001'},
        {label: 'blank name and ISIN fall back to ticker', prefill: {display_name: ' ', identifier_isin: '  ', identifier_ticker: '  SYN-TICKER  '}, expected: 'SYN-TICKER'},
        {label: 'missing name and ISIN fall back to ticker', prefill: {identifier_ticker: 'SYN-TICKER'}, expected: 'SYN-TICKER'},
        {label: 'no usable name or identifier stays invalid', prefill: {display_name: ' ', identifier_isin: ' ', identifier_ticker: ' '}, expected: ''},
    ])('$label, without reinitializing edits or a manual revert', async ({prefill, expected}) => {
        render(AssetModal, {open: true, initialNoProvider: true, prefillData: {...prefill, currency: 'EUR'}});
        await referenceReady;
        await flushUi();
        expectReady();
        expectBusy(false);
        const name = screen.getByTestId('asset-modal-display-name');
        expect(name).toHaveValue(expected);
        expect(name).toHaveAttribute('aria-invalid', String(expected === ''));
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');
        if (expected === '') {
            expect(screen.getByTestId('asset-modal-name-required')).toBeVisible();
            expect(screen.getByTestId('asset-modal-save')).toBeDisabled();
        } else {
            expect(screen.queryByTestId('asset-modal-name-required')).toBeNull();
            expect(screen.getByTestId('asset-modal-save')).toBeEnabled();
        }

        await input('asset-modal-display-name', 'User-owned replacement');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
        await input('asset-modal-display-name', expected);
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');

        // A derived identifier fallback would wrongly undo this deliberate clear.
        await input('asset-modal-display-name', '');
        await input('asset-modal-description', 'Manual description after clearing');
        expect(name).toHaveValue('');
        expect(name).toHaveAttribute('aria-invalid', 'true');
        expect(name).toHaveAttribute('aria-describedby', 'asset-name-required');
        expect(screen.getByTestId('asset-modal-name-required')).toBeVisible();
        expect(screen.getByTestId('asset-modal-save')).toBeDisabled();

        await input('asset-modal-display-name', 'Final user choice');
        expect(name).toHaveAttribute('aria-invalid', 'false');
        expect(screen.queryByTestId('asset-modal-name-required')).toBeNull();
        expect(screen.getByTestId('asset-modal-save')).toBeEnabled();
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('Manual description after clearing');
        assertTraffic();
    });
});

describe('AssetModal provider lifecycle', () => {
    it.each([false, true])('ignores reordered equal distributions but offers a genuine weight change (changed=%s)', async (changed) => {
        await renderEdit(
            editFixture({
                classification_params: {
                    sector_area: {distribution: {Technology: 0.4, Health: 0.6}},
                    geographic_area: {distribution: {USA: 0.7, FRA: 0.3}},
                },
            }),
        );
        const response: ProbeResponse = {
            provider_code: 'lifecycle_atlas',
            identifier: 'SYN-ATLAS',
            total_execution_time_ms: 4,
            metadata: {
                success: true,
                execution_time_ms: 4,
                patch_data: {
                    display_name: 'OWNED ATLAS SECURITY',
                    asset_type: 'STOCK',
                    currency: 'USD',
                    classification_params: {
                        short_description: 'Current metadata accepted',
                        sector_area: {distribution: changed ? {Health: '0.4', Technology: '0.6'} : {Health: '0.6', Technology: '0.4'}},
                        geographic_area: {distribution: {FRA: '0.3', USA: '0.7'}},
                    },
                },
            },
        };
        const metadata = plan('unordered metadata distributions', routes.metadata, [probeRequest(['metadata'])], response);
        await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
        expectBusy(true);
        await metadata.finish();
        expectBusy(false);
        // Prove this very response was accepted before asserting no false dialog.
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('Current metadata accepted');
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('OWNED ATLAS SECURITY');
        if (changed) {
            expect(screen.getByTestId('comparison-modal')).toBeVisible();
            expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-total-count', '1');
            expect(screen.getByTestId('comparison-checkbox-sector_area')).toBeChecked();
            expect(screen.queryByTestId('comparison-checkbox-geographic_area')).toBeNull();
        } else {
            expect(screen.queryByTestId('comparison-modal')).toBeNull();
            expect(mocks.toasts.success).toHaveBeenCalledTimes(1);
        }
        assertTraffic();
    });

    it('shares automatic/manual verification, retains manual details on remount, and clears effective provider changes', async () => {
        render(AssetModal, {open: true});
        await referenceReady;
        await flushUi();
        expectReady();
        expect(screen.getByTestId('asset-search-offline-select')).toBeEnabled();
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();

        const catalog = expectCatalog('selected provider catalog');
        const automatic = expectProbe('automatic selection probe', probeResponse('41.25'), {note: 'search note', currency: 'USD'});
        const metadata = expectMetadata('automatic selection metadata', 'OFFLINE ATLAS SECURITY', 'Automatic metadata accepted', {note: 'search note', currency: 'USD'});
        await fireEvent.click(screen.getByTestId('asset-search-offline-select'));
        await flushUi();
        // Both requests must already contain the complete selected config while
        // the child is still waiting for its provider schema.
        automatic.assertUnchanged();
        metadata.assertUnchanged();
        await catalog.finish();
        expectStatus('testing');
        expectBusy(true);
        expect(screen.getByTestId('asset-modal-more-info')).toHaveAttribute('data-expanded', 'true');
        expect(screen.getByTestId('asset-modal-provider-header')).toHaveAttribute('data-expanded', 'true');
        expect(screen.getByTestId('provider-identifier')).toHaveValue('SYN-ATLAS');
        expect(screen.getByTestId('param-note')).toHaveValue('search note');
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();
        automatic.assertUnchanged();
        metadata.assertUnchanged();

        // Metadata is independent: its completion clears busy, not verification.
        await metadata.finish();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('OFFLINE ATLAS SECURITY');
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('Automatic metadata accepted');
        expectBusy(false);
        expectStatus('testing');
        await automatic.finish();
        expectStatus('passed');
        expect(screen.getByTestId('provider-test-config')).toBeEnabled();
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        const manual = expectProbe('manual probe after automatic result', probeResponse('53.75'), {note: 'search note', currency: 'USD'});
        await fireEvent.click(screen.getByTestId('provider-test-config'));
        expectStatus('testing');
        await manual.finish();
        expectStatus('passed');
        expectResults(['success', 'success'], '53.75');

        await setProviderExpanded(false);
        expect(screen.getByTestId('asset-modal-provider-status')).toHaveAttribute('data-status', 'passed');
        expect(screen.queryByTestId('provider-test-config')).toBeNull();
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        const remountedCatalog = expectCatalog('remounted child catalog');
        await setProviderExpanded(true);
        await remountedCatalog.finish();
        expectStatus('passed');
        expectResults(['success', 'success'], '53.75');
        manual.assertUnchanged();

        await fireEvent.click(screen.getByTestId('provider-code-select-button'));
        expect(screen.getByTestId('provider-option-lifecycle_beacon')).toBeVisible();
        await fireEvent.click(screen.getByTestId('provider-option-lifecycle_beacon'));
        await flushUi();
        expect(screen.getByTestId('provider-code-select-button')).toHaveTextContent('Fictional Beacon');
        expect(screen.getByTestId('provider-identifier')).toHaveValue('');
        expect(screen.getByTestId('param-note')).toHaveValue('');
        expectStatus('not_tested');
        expect(screen.getByTestId('provider-test-config')).toBeDisabled();
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();
        expect(screen.queryByTestId('provider-test-result')).toBeNull();

        // Genuine bound edits, AFTER the requests: no UI-bound expected object
        // can mutate in parallel with the captured payload and hide a regression.
        await input('provider-identifier', 'US0000000001');
        await input('param-note', 'replacement note');
        await fireEvent.click(screen.getByTestId('provider-id-type-select-button'));
        expect(screen.getByTestId('provider-id-type-option-ISIN')).toBeVisible();
        await fireEvent.click(screen.getByTestId('provider-id-type-option-ISIN'));
        await flushUi();
        expect(screen.getByTestId('provider-id-type-select-button')).toHaveAttribute('aria-expanded', 'false');
        expectStatus('not_tested');
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        automatic.assertUnchanged();
        metadata.assertUnchanged();
        manual.assertUnchanged();

        // A new real request proves the type edit took effect and ALL old params
        // were removed, including the search-added currency with no input here.
        const replacementRequest: ProbeRequest = {
            provider_code: 'lifecycle_beacon',
            identifier: 'US0000000001',
            identifier_type: 'ISIN',
            provider_params: {note: 'replacement note'},
            operations: ['current_price', 'history'],
        };
        const replacementResponse: ProbeResponse = {
            ...probeResponse('57.25'),
            provider_code: 'lifecycle_beacon',
            identifier: 'US0000000001',
            provider_url: 'https://beacon.provider.invalid/security/US0000000001',
        };
        const replacement = plan('replacement provider verification', routes.verification, [replacementRequest], replacementResponse);
        expect(screen.getByTestId('provider-test-config')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('provider-test-config'));
        expectStatus('testing');
        await replacement.finish();
        expectStatus('passed');
        expectResults(['success', 'success'], '57.25');
        assertTraffic();
    });

    it.each([
        {code: 'FETCH_ERROR', status: 'failed', row: 'error'},
        {code: 'NO_DATA', status: 'passed', row: 'warning'},
        {code: 'NOT_IMPLEMENTED', status: 'passed', row: 'warning'},
    ] as const)('renders $code with successful history through the shared manual owner', async ({code, status, row}) => {
        await renderEdit();
        const response: ProbeResponse = {
            ...probeResponse(),
            current_price: {
                success: false,
                error: 'Synthetic current-price outcome',
                error_code: code,
                error_details: {identifier: 'SYN-ATLAS'},
                execution_time_ms: 3,
            },
        };
        const probe = expectProbe(`manual ${code}`, response);
        expect(screen.getByTestId('provider-test-config')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('provider-test-config'));
        expectStatus('testing');
        expectBusy(false); // Probe testing is not metadata/saving busy.
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        await probe.finish();
        expectStatus(status);
        expect(screen.getByTestId('provider-test-config')).toBeEnabled();
        expectResults([row, 'success']);
        assertTraffic();
    });

    it.each([
        {field: 'display_name', revert: false},
        {field: 'display_name', revert: true},
        {field: 'short_description', revert: false},
        {field: 'short_description', revert: true},
    ] as const)('offers a diff for manually edited $field (revert=$revert) without autofilling it', async ({field, revert}) => {
        await renderEdit();
        const editingName = field === 'display_name';
        const touchedId = editingName ? 'asset-modal-display-name' : 'asset-modal-description';
        const untouchedId = editingName ? 'asset-modal-description' : 'asset-modal-display-name';
        const initialValue = editingName ? 'Owned Atlas security' : '';
        const manualValue = editingName ? 'User-selected name' : 'User-written description';
        // Case-only metadata would normally normalize a matching value. A manual
        // edit made in flight must suppress even that overwrite. Reverting an
        // emptied description exercises the otherwise-automatic empty-field fill.
        const providerName = editingName && !revert ? 'USER-SELECTED NAME' : 'OWNED ATLAS SECURITY';
        const providerDescription = editingName ? 'Untouched description enriched' : revert ? 'Provider description after manual clearing' : 'USER-WRITTEN DESCRIPTION';
        const metadata = expectMetadata('field-level metadata intent', providerName, providerDescription);
        expect(screen.getByTestId(touchedId)).toHaveValue(initialValue);
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
        expectBusy(true);
        metadata.assertUnchanged();

        await input(touchedId, manualValue);
        if (revert) await input(touchedId, initialValue);
        await metadata.finish();

        // Positive acceptance barrier: the OTHER field really changed. For an
        // untouched name this is a case-only enrichment, not a legitimate diff.
        expect(screen.getByTestId(untouchedId)).toHaveValue(editingName ? providerDescription : providerName);
        expectBusy(false);
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        const retainedValue = revert ? initialValue : manualValue;
        const offeredValue = editingName ? providerName : providerDescription;
        expect(screen.getByTestId(touchedId)).toHaveValue(retainedValue);
        // The request is still current, but this field has newer manual intent:
        // offer the provider value through the REAL comparison, never autofill.
        expect(screen.getByTestId('comparison-modal')).toBeVisible();
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-total-count', '1');
        expect(screen.getByTestId(`comparison-checkbox-${field}`)).toBeChecked();
        expect(screen.getByTestId(`comparison-provider-${field}`)).toHaveTextContent(offeredValue);
        if (retainedValue !== '') {
            expect(screen.getByTestId(`comparison-current-${field}`)).toHaveTextContent(retainedValue);
        }
        expect(screen.getByTestId('comparison-apply')).toBeEnabled();
        metadata.assertUnchanged();

        // Only explicit consent may now change the field, including after ABA.
        await fireEvent.click(screen.getByTestId('comparison-apply'));
        await flushUi();
        expect(screen.getByTestId(touchedId)).toHaveValue(offeredValue);
        expect(screen.getByTestId(untouchedId)).toHaveValue(editingName ? providerDescription : providerName);
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        assertTraffic();
    });

    it.each(['cancel', 'open prop'] as const)('invalidates both pending reads on %s close and protects a reopened identical configuration', async (closeVia) => {
        const view = await renderEdit();
        const oldProbe = expectProbe('closed draft verification', probeResponse('91.75'));
        const oldMetadata = expectMetadata('closed draft metadata', 'Closed draft title', 'Closed draft description');
        await startManualReads();
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');
        expect(screen.getByTestId('asset-modal-cancel')).toBeEnabled();

        if (closeVia === 'cancel') {
            await fireEvent.click(screen.getByTestId('asset-modal-cancel'));
            expect(view.onclose).toHaveBeenCalledTimes(1);
            expect(view.onclose).toHaveBeenCalledWith();
        } else {
            await view.rerender({open: false});
            expect(view.onclose).not.toHaveBeenCalled();
        }
        await flushUi();
        expect(screen.queryByTestId('asset-modal')).toBeNull();
        expect(screen.queryByTestId('asset-modal-discard-confirm')).toBeNull();
        expect(screen.queryByTestId('confirm-modal-message')).toBeNull();

        // Explicit false also updates the external prop after a bindable close.
        await view.rerender({open: false});
        const reopenedCatalog = expectCatalog('reopened child catalog');
        await view.rerender({open: true, editData: editFixture()});
        await flushUi();
        await reopenedCatalog.finish();
        expectReady();
        expectStatus('not_tested');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');
        const freshProbe = expectProbe('reopened draft verification', probeResponse('64.25'));
        const freshMetadata = expectMetadata('reopened draft metadata', 'OWNED ATLAS SECURITY', 'Reopened draft enrichment');
        await startManualReads();
        freshProbe.assertUnchanged();
        freshMetadata.assertUnchanged();

        // Old success AND old metadata finally run while the new pair is pending.
        await oldProbe.finish();
        await oldMetadata.finish();
        expectStatus('testing');
        expectBusy(true);
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('Owned Atlas security');
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('');
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        await freshProbe.finish();
        expectStatus('passed');
        expectResults(['success', 'success'], '64.25');
        expectBusy(true);
        await freshMetadata.finish();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('OWNED ATLAS SECURITY');
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('Reopened draft enrichment');
        expectBusy(false);
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        expect(view.onupdated).not.toHaveBeenCalled();
        expect(view.oncreated).not.toHaveBeenCalled();
        assertTraffic();
    });

    it('rejects old-session reads before any configuration reset, then accepts real current-session work', async () => {
        await renderEdit();
        const oldProbe = expectProbe('old-session verification', probeResponse('92.75'));
        const oldMetadata = expectMetadata('old-session metadata', 'Old session title', 'Old session description');
        await startManualReads();
        const oldGeneration = getClientSessionGeneration();
        expect(isClientSessionCurrent(oldGeneration)).toBe(true);
        expect(getClientSessionUserId()).toBe('asset-modal-lifecycle-owner');

        transitionClientSession('asset-modal-lifecycle-next-owner');
        expect(getClientSessionUserId()).toBe('asset-modal-lifecycle-next-owner');
        expect(getClientSessionGeneration()).toBeGreaterThan(oldGeneration);
        expect(isClientSessionCurrent(oldGeneration)).toBe(false);
        // Resolve BEFORE editing props/config or disposing. Otherwise those
        // independent guards could conceal a broken session-generation check.
        await oldProbe.finish();
        await oldMetadata.finish();
        expectReady();
        expect(screen.getByTestId('provider-identifier')).toHaveValue('SYN-ATLAS');
        expect(screen.getByTestId('param-note')).toHaveValue('owned note');
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('Owned Atlas security');
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('');
        const parentStatus = screen.getByTestId('asset-modal-provider-status').getAttribute('data-status');
        const childStatus = screen.getByTestId('provider-test-config').getAttribute('data-status');
        expect(['not_tested', 'testing']).toContain(parentStatus);
        expect(childStatus).toBe(parentStatus);
        // Deliberately no assertion prescribing persistent pending vs proactive
        // reset at identity transition; only stale acceptance is forbidden.
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        await input('param-note', 'current session note');
        expectStatus('not_tested');
        expectBusy(false);
        oldProbe.assertUnchanged();
        oldMetadata.assertUnchanged();
        const freshProbe = expectProbe('current-session verification', probeResponse('68.25'), {note: 'current session note'});
        const freshMetadata = expectMetadata('current-session metadata', 'OWNED ATLAS SECURITY', 'Current session enrichment', {note: 'current session note'});
        await startManualReads();
        await freshProbe.finish();
        expectStatus('passed');
        expectResults(['success', 'success'], '68.25');
        expectBusy(true);
        await freshMetadata.finish();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('OWNED ATLAS SECURITY');
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('Current session enrichment');
        expectBusy(false);
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        assertTraffic();
    });

    it.each(['pending', 'passed'] as const)('saves with %s verification and pending metadata without accepting late reads or syncing an unchanged provider', async (verification) => {
        const view = await renderEdit();
        await input('asset-modal-display-name', 'Saved owned security');
        const probe = expectProbe('verification around save', probeResponse(verification === 'passed' ? '19.25' : '87.75'));
        const metadata = expectMetadata('metadata invalidated by save', 'Stale saving title', 'Stale saving description');
        await startManualReads();
        if (verification === 'passed') {
            await probe.finish();
            expectStatus('passed');
            expectResults(['success', 'success'], '19.25');
        }
        expectBusy(true);
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();

        const expectedPatch: PatchItem[] = [
            {
                asset_id: 8101,
                display_name: 'Saved owned security',
                currency: 'USD',
                asset_type: 'STOCK',
                icon_url: null,
                quote_base_quantity: 1,
                active: true,
                is_benchmark: false,
                user_url: null,
                // Untouched classification is omitted, not sent as a clear.
                identifier_isin: null,
                identifier_ticker: null,
                identifier_cusip: null,
                identifier_sedol: null,
                identifier_figi: null,
                identifier_uuid: null,
                identifier_other: null,
            },
        ];
        const patchResult: PatchResponse = {results: [{asset_id: 8101, success: true, message: 'Synthetic patch accepted'}], success_count: 1, errors: []};
        const patch = plan('save PATCH', routes.patch, [expectedPatch], patchResult);
        const expectedAssignment: AssignmentItem[] = [
            {
                asset_id: 8101,
                provider_code: 'lifecycle_atlas',
                identifier: 'SYN-ATLAS',
                identifier_type: 'TICKER',
                provider_params: {note: 'owned note'},
            },
        ];
        const assignmentResult: AssignmentResponse = {results: [{asset_id: 8101, success: true, message: 'Synthetic assignment accepted'}], success_count: 1, errors: []};
        const assignment = plan('save assignment', routes.assign, [expectedAssignment], assignmentResult);

        expect(screen.getByTestId('asset-modal-save')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await referenceReady; // The real saveEdit awaits the ready provider cache.
        await flushUi();
        patch.assertUnchanged();
        expect(assignment.actualArgs).toBeUndefined();
        expectStatus(verification === 'passed' ? 'passed' : 'not_tested');
        expectBusy(true);
        expect(screen.getByTestId('asset-modal-form')).toBeDisabled();
        expect(screen.getByTestId('asset-modal-save')).toBeDisabled();
        expect(screen.getByTestId('asset-modal-cancel')).toBeDisabled();
        expect(screen.getByTestId('provider-test-config')).toBeDisabled();
        // Unchanged provider: even a pending test must not interpose this gate.
        expect(screen.queryByTestId('confirm-modal-message')).toBeNull();
        expect(view.onupdated).not.toHaveBeenCalled();

        if (verification === 'pending') await probe.finish();
        await metadata.finish();
        expectStatus(verification === 'passed' ? 'passed' : 'not_tested');
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('Saved owned security');
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('');
        expectBusy(true);
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        if (verification === 'passed') expectResults(['success', 'success'], '19.25');
        else expect(screen.queryByTestId('provider-test-result')).toBeNull();
        expect(mocks.toasts.info).not.toHaveBeenCalled();
        expect(mocks.toasts.success).not.toHaveBeenCalled();
        patch.assertUnchanged();

        await patch.finish();
        assignment.assertUnchanged();
        expectBusy(true);
        expect(view.onupdated).not.toHaveBeenCalled();
        expect(mocks.assets.mergeAssets).toHaveBeenCalledTimes(1);
        expect(mocks.assets.mergeAssets).toHaveBeenCalledWith([
            {
                id: 8101,
                asset_id: 8101,
                display_name: 'Saved owned security',
                currency: 'USD',
                asset_type: 'STOCK',
                icon_url: null,
                quote_base_quantity: 1,
                active: true,
                is_benchmark: false,
                user_url: null,
                identifier_isin: null,
                identifier_ticker: null,
                identifier_cusip: null,
                identifier_sedol: null,
                identifier_figi: null,
                identifier_uuid: null,
                identifier_other: null,
            },
        ]);
        await assignment.finish();
        expect(view.onupdated).toHaveBeenCalledTimes(1);
        expect(view.onupdated).toHaveBeenCalledWith();
        expect(view.oncreated).not.toHaveBeenCalled();
        expect(view.onclose).not.toHaveBeenCalled();
        expect(mocks.api.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
        expect(mocks.toasts.success).toHaveBeenCalledTimes(1);
        expect(mocks.toasts.warning).not.toHaveBeenCalled();
        expect(mocks.toasts.error).not.toHaveBeenCalled();
        expect(screen.queryByTestId('asset-modal')).toBeNull();
        assertTraffic();
    });

    it('closes a real valid comparison on public draft switch and accepts only a new draft choice', async () => {
        const view = await renderEdit(editFixture({classification_params: {short_description: 'Stored description'}}));
        const oldMetadata = expectMetadata('valid old-draft conflict', 'Provider comparison title', 'Stored description');
        await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
        await oldMetadata.finish();
        expect(screen.getByTestId('comparison-modal')).toBeVisible();
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-total-count', '1');
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-selected-count', '1');
        expect(screen.getByTestId('comparison-checkbox-display_name')).toBeChecked();
        expect(screen.getByTestId('comparison-current-display_name')).toHaveTextContent('Owned Atlas security');
        expect(screen.getByTestId('comparison-provider-display_name')).toHaveTextContent('Provider comparison title');
        expect(screen.getByTestId('comparison-apply')).toBeEnabled();

        // Public props are the opening-context contract. No event is dispatched
        // behind this overlay, and its old Apply element is never retained.
        await view.rerender({editData: editFixture({id: 8102, display_name: 'Replacement draft security'})});
        await flushUi();
        expectReady();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('Replacement draft security');
        expect(screen.getByTestId('asset-modal-description')).toHaveValue('');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');
        expectStatus('not_tested');
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        expect(screen.queryByTestId('comparison-checkbox-display_name')).toBeNull();

        const freshMetadata = expectMetadata('replacement-draft conflict', 'Replacement provider choice', '');
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
        await freshMetadata.finish();
        expect(screen.getByTestId('comparison-modal')).toBeVisible();
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-total-count', '1');
        expect(screen.getByTestId('comparison-current-display_name')).toHaveTextContent('Replacement draft security');
        expect(screen.getByTestId('comparison-provider-display_name')).toHaveTextContent('Replacement provider choice');
        expect(screen.getByTestId('comparison-checkbox-display_name')).toBeChecked();
        await fireEvent.click(screen.getByTestId('comparison-apply'));
        await flushUi();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('Replacement provider choice');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        expect(view.onupdated).not.toHaveBeenCalled();
        expect(view.oncreated).not.toHaveBeenCalled();
        assertTraffic();
    });

    it('closes the sole real save-without-test confirmation on a public draft switch', async () => {
        const view = await renderEdit();
        await input('param-note', 'changed provider note');
        expectStatus('not_tested');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
        expect(screen.getByTestId('asset-modal-save')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await flushUi();
        // getByTestId also rejects an ambiguous second generic confirmation.
        expect(screen.getByTestId('confirm-modal-message')).toBeVisible();
        expect(screen.getByTestId('confirm-modal-confirm')).toBeEnabled();
        expect(screen.getByTestId('confirm-modal-cancel')).toBeVisible();
        expect(mocks.api.patch_assets_bulk_api_v1_assets_patch).not.toHaveBeenCalled();
        expect(mocks.api.assign_providers_bulk_api_v1_assets_provider_post).not.toHaveBeenCalled();

        await view.rerender({editData: editFixture({id: 8103, display_name: 'Another owned draft'})});
        await flushUi();
        expectReady();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('Another owned draft');
        expect(screen.getByTestId('param-note')).toHaveValue('owned note');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');
        expectStatus('not_tested');
        expect(screen.getByTestId('asset-modal-save')).toBeEnabled();
        expect(screen.queryByTestId('confirm-modal-message')).toBeNull();
        expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull();
        expect(view.onupdated).not.toHaveBeenCalled();
        expect(view.oncreated).not.toHaveBeenCalled();
        assertTraffic();
    });
});

// ---------------------------------------------------------------------------
// R18 — a search selection asks each identifier question once.
//
// Picking a result that quotes a different ISIN opens the chooser at once AND
// starts the metadata read that feeds the comparison. Whichever lands first, that
// selection's comparison waits for every prompt of the selection, and never
// re-asks a code the chooser already put on the table. A later manual read is
// not the selection's and stays unchanged.
// ---------------------------------------------------------------------------

const REPORT_ISIN = 'IT0000000001';
const PROVIDER_ISIN = 'IT0000000002';
const THIRD_ISIN = 'IT0000000003';
const STORED_ISIN = 'IT0000000004';
const REPORT_NAME = 'Report synthetic bond';
const SELECTION_NAME = 'Offline quoted security';
const PROVIDER_TITLE = 'Provider metadata title';
const ACCEPTED_DESCRIPTION = 'Selection metadata accepted';

type MetadataPatch = Record<string, unknown>;

interface ReportPrefill {
    display_name: string;
    identifier_isin: string;
    currency: string;
}

interface SelectionCase {
    label: string;
    patch: MetadataPatch;
    distributions: boolean;
    after: string[];
}

/** A fresh result per selection: it is the component's callback argument, never frozen. */
function isinSelection(): SearchSelection {
    return {
        identifier: PROVIDER_ISIN,
        identifier_type: 'ISIN',
        display_name: SELECTION_NAME,
        provider_code: 'lifecycle_atlas',
        currency: 'USD',
        asset_type: 'STOCK',
        provider_params: {note: 'search note'},
        provider_url: `https://atlas.provider.invalid/security/${PROVIDER_ISIN}`,
    };
}

/** Independent oracle for both reads the ISIN selection starts; the modal adds the currency. */
function isinRequest(operations: ProbeRequest['operations']): ProbeRequest {
    return {
        provider_code: 'lifecycle_atlas',
        identifier: PROVIDER_ISIN,
        identifier_type: 'ISIN',
        provider_params: {note: 'search note', currency: 'USD'},
        operations: [...operations],
    };
}

/**
 * Metadata agreeing with the selection except for `patch`. Its description fills
 * the empty field on acceptance: the positive barrier before any absence claim.
 * With `distributions` nothing is missing, so the "all match" branch is reachable
 * and a missing success toast is evidence rather than a vacuous pass.
 */
function isinMetadata(patch: MetadataPatch, distributions: boolean): ProbeResponse {
    return {
        provider_code: 'lifecycle_atlas',
        identifier: PROVIDER_ISIN,
        total_execution_time_ms: 4,
        metadata: {
            success: true,
            execution_time_ms: 4,
            patch_data: {
                display_name: SELECTION_NAME,
                asset_type: 'STOCK',
                currency: 'USD',
                classification_params: {
                    short_description: ACCEPTED_DESCRIPTION,
                    ...(distributions ? {sector_area: {distribution: {Technology: '1'}}, geographic_area: {distribution: {USA: '1'}}} : {}),
                },
                ...patch,
            },
        },
    };
}

/** The import wizard's create context: report codes prefilled, no provider yet, reuse prompt enabled. */
async function renderReportCreate(prefill: ReportPrefill = {display_name: REPORT_NAME, identifier_isin: REPORT_ISIN, currency: 'EUR'}) {
    const onReuseExisting = vi.fn();
    const view = render(AssetModal, {open: true, initialNoProvider: true, prefillData: {...prefill}, onReuseExisting});
    await referenceReady;
    await flushUi();
    expectReady();
    expectBusy(false);
    expect(screen.getByTestId('asset-modal-display-name')).toHaveValue(prefill.display_name);
    expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();
    return {...view, onReuseExisting};
}

/** Edit mode: the stored ISIN column differs from the quoted code the asset is priced by. */
async function renderStoredIsinEdit() {
    const catalog = expectCatalog('stored-ISIN edit catalog');
    const view = render(AssetModal, {open: true, editMode: true, editData: editFixture({identifier_isin: STORED_ISIN, provider_identifier: PROVIDER_ISIN, provider_identifier_type: 'ISIN'})});
    await flushUi();
    await catalog.finish();
    await referenceReady;
    await flushUi();
    expectReady();
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');
    // A stored identifier row opens this section by itself.
    expect(screen.getByTestId('asset-modal-more-info')).toHaveAttribute('data-expanded', 'true');
    expectStatus('not_tested');
    return view;
}

/**
 * Pick the quoted ISIN through the real onselect. The automatic verification is
 * incidental here and finished first, so the metadata read is the one open boundary.
 */
async function selectProviderIsin(patch: MetadataPatch, {catalog = true, distributions = false} = {}): Promise<PlannedCall> {
    searchSelection.result = isinSelection();
    const schema = catalog ? expectCatalog('ISIN selection catalog') : null;
    const verification = plan('ISIN selection verification', routes.verification, [isinRequest(['current_price', 'history'])], {...probeResponse('41.25'), identifier: PROVIDER_ISIN, provider_url: `https://atlas.provider.invalid/probed/${PROVIDER_ISIN}`});
    const metadata = plan('ISIN selection metadata', routes.metadata, [isinRequest(['metadata'])], isinMetadata(patch, distributions));
    expect(screen.getByTestId('asset-search-offline-select')).toBeEnabled();
    await fireEvent.click(screen.getByTestId('asset-search-offline-select'));
    await flushUi();
    // Both reads leave at selection time, before any prompt can be answered.
    verification.assertUnchanged();
    metadata.assertUnchanged();
    if (schema) await schema.finish();
    await verification.finish();
    expectStatus('passed');
    expectBusy(true);
    return metadata;
}

/** The selection's chooser: precisely its two codes, `primary` elected. */
function expectIsinChooser(current: string, primary: string) {
    expect(screen.getByTestId('asset-modal-identifier-primary')).toBeVisible();
    const chooser = screen.getByTestId('asset-modal-primary-chooser');
    expect(within(chooser).getAllByRole('radio')).toHaveLength(2);
    expect(within(chooser).getByTestId(`asset-modal-primary-chooser-option-${primary}`)).toHaveAttribute('aria-checked', 'true');
    const other = primary === PROVIDER_ISIN ? current : PROVIDER_ISIN;
    expect(within(chooser).getByTestId(`asset-modal-primary-chooser-option-${other}`)).not.toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('asset-modal-primary-confirm')).toBeEnabled();
}

/** Answer the chooser, electing `primary` first when given; ends with the chooser closed. */
async function confirmChooser(primary?: string) {
    if (primary !== undefined) {
        await fireEvent.click(screen.getByTestId(`asset-modal-primary-chooser-option-${primary}`));
        await flushUi();
        expect(screen.getByTestId(`asset-modal-primary-chooser-option-${primary}`)).toHaveAttribute('aria-checked', 'true');
    }
    await fireEvent.click(screen.getByTestId('asset-modal-primary-confirm'));
    await flushUi();
    expect(screen.queryByTestId('asset-modal-identifier-primary')).toBeNull();
}

/** Ask to leave the chooser; ends with the sole generic discard confirmation over it. */
async function requestChooserDiscard() {
    await fireEvent.click(screen.getByTestId('asset-modal-primary-cancel'));
    await flushUi();
    // getByTestId also rejects an ambiguous second generic confirmation.
    expect(screen.getByTestId('confirm-modal-message')).toBeVisible();
    expect(screen.getByTestId('confirm-modal-confirm')).toBeEnabled();
    expect(screen.getByTestId('asset-modal-identifier-primary')).toBeVisible();
}

/** This very response was accepted — its description landed — and yet no comparison is shown. */
function expectAcceptedWithoutComparison() {
    expectBusy(false);
    expect(screen.getByTestId('asset-modal-description')).toHaveValue(ACCEPTED_DESCRIPTION);
    expect(screen.queryByTestId('comparison-modal'), 'a selection comparison must wait while a prompt of that selection is open').toBeNull();
}

/** The comparison on screen asks exactly `fields`; with none, there is no comparison at all. */
function expectComparison(fields: readonly string[]) {
    if (fields.length === 0) {
        expect(screen.queryByTestId('comparison-modal'), 'nothing is left to ask once the chooser answered').toBeNull();
        return;
    }
    const modal = screen.getByTestId('comparison-modal');
    expect(modal).toBeVisible();
    // Every card comes from this case's synthetic response: the set is the claim.
    const cards = within(modal).getAllByTestId('comparison-card');
    expect(
        cards.map((card) => card.getAttribute('data-field')),
        'rows left once the chooser answered its own question',
    ).toEqual([...fields]);
    expect(within(modal).getByTestId('comparison-body')).toHaveAttribute('data-total-count', String(fields.length));
    expect(within(modal).getByTestId('comparison-apply')).toBeEnabled();
}

/** Accepting the name proves the released comparison is live, not the shell of a stale read. */
async function applyProviderTitle() {
    expect(screen.getByTestId('comparison-current-display_name')).toHaveTextContent(SELECTION_NAME);
    expect(screen.getByTestId('comparison-provider-display_name')).toHaveTextContent(PROVIDER_TITLE);
    await fireEvent.click(screen.getByTestId('comparison-apply'));
    await flushUi();
    expect(screen.queryByTestId('comparison-modal')).toBeNull();
    expect(screen.getByTestId('asset-modal-display-name')).toHaveValue(PROVIDER_TITLE);
}

/** Nothing left to ask: no dialog, and no "all match" claim (nothing was missing either). */
function expectSilentDrop() {
    expect(screen.queryByTestId('comparison-modal')).toBeNull();
    expect(mocks.toasts.info).not.toHaveBeenCalled();
    expect(mocks.toasts.success).not.toHaveBeenCalled();
}

describe('AssetModal search selection asks each identifier question once (R18)', () => {
    it.each<SelectionCase>([
        {label: 'a name difference remains', patch: {identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE}, distributions: false, after: ['display_name']},
        {label: 'only the chooser ISIN differs', patch: {identifier_isin: PROVIDER_ISIN}, distributions: true, after: []},
        {label: 'a third ISIN is another question', patch: {identifier_isin: THIRD_ISIN}, distributions: false, after: ['identifier_isin']},
    ])('holds a comparison that lands behind the open ISIN chooser, then asks only what is left ($label)', async ({patch, distributions, after}) => {
        await renderReportCreate();
        const metadata = await selectProviderIsin(patch, {distributions});
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        await metadata.finish();
        // R18: today the comparison opens over the chooser and asks the same ISIN again.
        expectAcceptedWithoutComparison();
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);

        await confirmChooser(); // the provider's quoted code is the default primary
        expectComparison(after);
        if (after.length === 0) expectSilentDrop();
        else if (after.includes('identifier_isin')) expect(screen.getByTestId(`comparison-chooser-identifier_isin-option-${THIRD_ISIN}`)).toBeVisible();
        else await applyProviderTitle();
        assertTraffic();
    });

    it.each<SelectionCase & {landsUnder: 'chooser' | 'discard confirmation'}>([
        {label: 'lands under the chooser; a name difference remains', landsUnder: 'chooser', patch: {identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE}, distributions: false, after: ['display_name']},
        {label: 'lands under the discard confirmation; only the discarded ISIN differs', landsUnder: 'discard confirmation', patch: {identifier_isin: PROVIDER_ISIN}, distributions: true, after: []},
    ])('keeps the comparison waiting through the discard confirmation and never re-asks the discarded code ($label)', async ({landsUnder, patch, distributions, after}) => {
        await renderReportCreate();
        const metadata = await selectProviderIsin(patch, {distributions});
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
        if (landsUnder === 'chooser') {
            await metadata.finish();
            // R18: today the comparison opens over the chooser.
            expectAcceptedWithoutComparison();
        }
        await requestChooserDiscard();
        if (landsUnder === 'discard confirmation') {
            await metadata.finish();
            // R18: today the comparison opens while the chooser and its discard confirmation are up.
            expectAcceptedWithoutComparison();
            expect(screen.getByTestId('confirm-modal-message')).toBeVisible();
        }
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        // Backing out of the discard is not an answer: the chooser is still asking.
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await flushUi();
        expect(screen.queryByTestId('confirm-modal-message')).toBeNull();
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        await requestChooserDiscard();
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await flushUi();
        expect(screen.queryByTestId('confirm-modal-message')).toBeNull();
        expect(screen.queryByTestId('asset-modal-identifier-primary')).toBeNull();
        expectComparison(after);
        if (after.length === 0) expectSilentDrop();
        else await applyProviderTitle();
        assertTraffic();
    });

    it.each<SelectionCase>([
        {label: 'a name difference remains', patch: {identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE}, distributions: false, after: ['display_name']},
        {label: 'only the answered ISIN differs', patch: {identifier_isin: PROVIDER_ISIN}, distributions: true, after: []},
    ])('does not re-ask the ISIN when the read lands after the report code was kept as primary ($label)', async ({patch, distributions, after}) => {
        await renderReportCreate();
        const metadata = await selectProviderIsin(patch, {distributions});
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
        await confirmChooser(REPORT_ISIN);
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        expectBusy(true); // answered while the metadata read is still in flight

        await metadata.finish();
        expectBusy(false);
        expect(screen.getByTestId('asset-modal-description')).toHaveValue(ACCEPTED_DESCRIPTION);
        // R18, second half: current (report) ≠ provider, so the answered row comes back today.
        expectComparison(after);
        if (after.length === 0) expectSilentDrop();
        else await applyProviderTitle();
        assertTraffic();
    });

    it('holds the comparison behind the chooser for a stored ISIN in edit mode, then asks only the name', async () => {
        await renderStoredIsinEdit();
        const metadata = await selectProviderIsin({identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE}, {catalog: false});
        expectIsinChooser(STORED_ISIN, PROVIDER_ISIN);

        await metadata.finish();
        expectAcceptedWithoutComparison();
        expectIsinChooser(STORED_ISIN, PROVIDER_ISIN);

        await confirmChooser();
        expectComparison(['display_name']);
        await applyProviderTitle();
        assertTraffic();
    });

    it('leaves a later manual Ask provider unchanged: it offers the identifier row again', async () => {
        await renderReportCreate();
        // This read proposes no identifier at all, so the case passes before and after the fix.
        const selection = await selectProviderIsin({display_name: PROVIDER_TITLE});
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
        await confirmChooser(REPORT_ISIN);
        await selection.finish();
        expectBusy(false);
        expectComparison(['display_name']);
        await fireEvent.click(screen.getByTestId('comparison-cancel'));
        await flushUi();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue(SELECTION_NAME);

        const manual = plan('manual Ask provider after the answered selection', routes.metadata, [isinRequest(['metadata'])], isinMetadata({identifier_isin: PROVIDER_ISIN}, false));
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
        expectBusy(true);
        await manual.finish();
        expectBusy(false);
        // Not the selection's read: the chooser's answer must not prune it.
        expectComparison(['identifier_isin']);
        const chooser = screen.getByTestId('comparison-chooser-identifier_isin');
        for (const value of [PROVIDER_ISIN, REPORT_ISIN]) {
            expect(within(chooser).getByTestId(`comparison-chooser-identifier_isin-option-${value}`)).toBeVisible();
        }
        assertTraffic();
    });

    it('drops a held comparison when a public draft switch replaces the provider context', async () => {
        const view = await renderStoredIsinEdit();
        const metadata = await selectProviderIsin({identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE}, {catalog: false});
        await metadata.finish();
        expectAcceptedWithoutComparison();
        expectIsinChooser(STORED_ISIN, PROVIDER_ISIN);

        // Public props are the opening-context contract: nothing is clicked behind the chooser.
        await view.rerender({editData: editFixture({id: 8102, display_name: 'Replacement draft security'})});
        await flushUi();
        expectReady();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue('Replacement draft security');
        expectStatus('not_tested');
        expect(screen.queryByTestId('asset-modal-identifier-primary')).toBeNull();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        // A fresh read on the new draft opens only its own question: nothing held leaks in.
        const fresh = expectMetadata('replacement-draft metadata', 'Replacement provider choice', '');
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
        await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
        await fresh.finish();
        expectComparison(['display_name']);
        expect(screen.getByTestId('comparison-current-display_name')).toHaveTextContent('Replacement draft security');
        expect(screen.getByTestId('comparison-provider-display_name')).toHaveTextContent('Replacement provider choice');
        assertTraffic();
    });

    it('drops a held comparison whose session ended before the chooser was answered', async () => {
        await renderReportCreate();
        // Same read as the first case, where a name row survives the answer: only staleness can drop it here.
        const metadata = await selectProviderIsin({identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE});
        await metadata.finish();
        expectAcceptedWithoutComparison();

        const generation = getClientSessionGeneration();
        transitionClientSession('asset-modal-lifecycle-next-owner');
        expect(isClientSessionCurrent(generation)).toBe(false);
        await flushUi();
        // Nothing closes the chooser on an identity change, so answering it is a real action.
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
        await confirmChooser();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        expectReady();
        assertTraffic();
    });

    it('drops a held comparison when the modal closes, and reopens on a clean draft', async () => {
        const view = await renderReportCreate();
        const metadata = await selectProviderIsin({identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE});
        await metadata.finish();
        expectAcceptedWithoutComparison();
        expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);

        await view.rerender({open: false});
        await flushUi();
        expect(screen.queryByTestId('asset-modal')).toBeNull();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();

        // Reopening re-renders the body once with the previous draft's provider state
        // (expanded, provider chosen) before the open effect resets it, so the section
        // mounts for an instant and reads its catalog. That wasted read predates R18 and
        // is real traffic: planned here so assertTraffic stays strict. If the transient
        // mount is ever removed, this plan goes unconsumed and must be dropped with it.
        const reopenCatalog = expectCatalog('reopen transient catalog');
        await view.rerender({open: true});
        await flushUi();
        await reopenCatalog.finish();
        expectReady();
        expect(screen.getByTestId('asset-modal-display-name')).toHaveValue(REPORT_NAME);
        // Clean draft: the reset folded the provider section away again and no provider is set.
        expect(screen.getByTestId('asset-modal-provider-header')).toHaveAttribute('data-expanded', 'false');
        expect(screen.getByTestId('asset-modal-ask-provider')).toBeDisabled();
        expect(screen.queryByTestId('asset-modal-identifier-primary')).toBeNull();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        assertTraffic();
    });

    it.each([false, true])('holds the selection comparison behind the reuse prompt too (ISIN chooser also open: %s)', async (withChooser) => {
        const view = await renderReportCreate({display_name: REPORT_NAME, identifier_isin: withChooser ? REPORT_ISIN : PROVIDER_ISIN, currency: 'EUR'});
        // An existing asset already carries the provider's name: that raises the reuse prompt.
        // The incidental duplicate-name check reads the same listing; it stays incidental.
        mocks.api.list_assets_api_v1_assets_query_get.mockImplementation((...args: unknown[]) => {
            checkArguments('reuse-candidate listing', args, [{queries: {}}]);
            return Promise.resolve([{id: 7001, display_name: SELECTION_NAME}]);
        });
        const metadata = await selectProviderIsin({identifier_isin: PROVIDER_ISIN, display_name: PROVIDER_TITLE});
        expect(screen.getByTestId('reuse-existing-title')).toBeVisible();
        if (withChooser) expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
        else expect(screen.queryByTestId('asset-modal-identifier-primary')).toBeNull();

        await metadata.finish();
        // R18: today the comparison opens over the reuse prompt as well.
        expectAcceptedWithoutComparison();
        expect(screen.getByTestId('reuse-existing-title')).toBeVisible();

        // Same layer, later in the DOM than the chooser: the reuse prompt is the one on top.
        await fireEvent.click(screen.getByTestId('reuse-existing-cancel'));
        await flushUi();
        expect(screen.queryByTestId('reuse-existing-title')).toBeNull();
        if (withChooser) {
            expectIsinChooser(REPORT_ISIN, PROVIDER_ISIN);
            expect(screen.queryByTestId('comparison-modal')).toBeNull();
            await confirmChooser();
        }
        expectComparison(['display_name']);
        await applyProviderTitle();
        expect(view.onReuseExisting).not.toHaveBeenCalled();
        assertTraffic();
    });
});
