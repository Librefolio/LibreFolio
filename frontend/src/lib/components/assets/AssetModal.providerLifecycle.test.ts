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
 * ready reference caches, the incidental duplicate-name listing, and the
 * incidental read of the provider's plugin settings (workstream X, CP11b): the
 * panel reads them for every provider it shows, and is answered «no settings»,
 * so it offers no «Configure» and these cases stay about the probe.
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
 *
 * One module function is replaced too (workstream X, X-R49): `wipeRefusalMessage`
 * of `./currencyChangeErrors` answers what a case makes it answer, null by
 * default, so a refused save is read against the module's answer and never a
 * translation; the module's own wording is `currencyChangeErrors.test.ts`'s. A
 * planned request may also be refused (`planRejection`): the product's call
 * rejects once released, while `finish` and the teardown wait on a response that
 * only settles. The catalogue lists the parametric provider too, as the real
 * plugin declares it, so a scheduled asset is edited through the real
 * ScheduledInvestmentEditor.
 *
 * The provider's removal is a planned route too (workstream X, X-R62, written
 * by H): «No provider» saved, `DELETE /assets/provider` is answered — or
 * refused through `planRejection` — like any other planned request.
 *
 * X5-1 (workstream X, C-65a + W-B2 + X-R69): changing the provider or its parameters, and removing the provider, follow
 * ONE rule. Before the asset PATCH, `saveEdit` asks the server's dry run (`POST /assets/provider/impact`, a planned route
 * like the others) what the change would delete; a non-empty answer opens ONE dialog by kind (`asset-scheduled-regen-
 * confirm`, `asset-parametric-switch-confirm`, `asset-provider-remove-confirm`) whose confirm re-enters the save and
 * whose cancel sends nothing; an empty or refused dry run, or one that failed, lets the save go on as a plain save. The
 * market-data summary the switch dialog used to count with is no longer read (its facade method stays unplanned, so a
 * call to it fails the test), and a new asset or an unchanged provider asks nothing. `PROVIDER_REMOVAL_LINKED_TRANSACTIONS`
 * no longer exists: the removal disconnects the linked transactions, and its 409s are the split refusal (said inline,
 * as the assignment's) and the conflict.
 *
 * «Ask provider» refused for too many probes (workstream X, X-R66) — red until
 * X-R66: the metadata probe refused with 429 PROBE_RATE_LIMITED is toasted as
 * the catalogue's PROBE_RATE_LIMITED, with the time the pause ends, instead of
 * the generic «an error occurred»; any other failure keeps that generic toast.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {flushSync, tick, type Component, type ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import type {z} from 'zod';
import type {schemas} from '$lib/api/generated';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {_} from '$lib/i18n';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, transitionClientSession} from '$lib/stores/app/clientSession';
import {userSettings} from '$lib/stores/app/settings';
import {currentLanguage} from '$lib/stores/app/language';
import {currencyStoreVersion, type CurrencyInfo} from '$lib/stores/reference/currencyStore';
import type {CountryInfo} from '$lib/stores/reference/countryStore';
import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
import {formatDay} from '$lib/utils/core/formatAxisDate';
import AssetModal from './AssetModal.svelte';
import type AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
import {formatResumeTime, resumesToday} from './resolveProviderError';

type ProbeRequest = z.infer<typeof schemas.FAProviderProbeRequest>;
type ProbeResponse = z.infer<typeof schemas.FAProviderProbeResponse>;
type ProviderInfo = z.infer<typeof schemas.FAProviderInfo>;
type PatchItem = z.infer<typeof schemas.FAAssetPatchItem>;
type PatchResponse = z.infer<typeof schemas.FABulkAssetPatchResponse>;
type AssignmentItem = z.infer<typeof schemas.FAProviderAssignmentItem>;
type AssignmentResponse = z.infer<typeof schemas.FABulkAssignResponse>;
type RemovalResponse = z.infer<typeof schemas.FABulkRemoveResponse>;
type ImpactResponse = z.infer<typeof schemas.FAProviderImpactResponse>;
type ImpactResult = z.infer<typeof schemas.FAProviderImpactResult>;
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
        // X5-1: the dry run of the assignment and of the removal.
        provider_change_impact_api_v1_assets_provider_impact_post: vi.fn(),
        sync_prices_bulk_api_v1_assets_prices_sync_post: vi.fn(),
        search_assets_via_providers_api_v1_assets_provider_search_get: vi.fn(),
        market_data_summary_api_v1_assets__asset_id__market_data_summary_get: vi.fn(),
        wipe_market_data_api_v1_assets__asset_id__market_data_wipe_post: vi.fn(),
        list_routes_api_v1_fx_providers_routes_get: vi.fn(),
        list_currencies_api_v1_utilities_currencies_get: vi.fn(),
        list_countries_api_v1_utilities_countries_get: vi.fn(),
        list_sectors_api_v1_utilities_sectors_get: vi.fn(),
        list_files_api_v1_uploads_get: vi.fn(),
        get_plugin_settings_api_v1_settings_plugins_get: vi.fn(),
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
    // X-R49: the sentence of a refused plan. Reset with the rest, then null (an error the module does not word).
    refusals: {wipeRefusalMessage: vi.fn()},
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
// X-R49: only `wipeRefusalMessage` is replaced; the module's other exports stay real.
vi.mock('./currencyChangeErrors', async (importOriginal) => ({...(await importOriginal<Record<string, unknown>>()), wipeRefusalMessage: mocks.refusals.wipeRefusalMessage}));
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
    remove: 'DELETE /api/v1/assets/provider',
    /** X5-1: what the change would delete, counted and nothing written. */
    impact: 'POST /api/v1/assets/provider/impact',
    /** The price sync a confirmed provider change starts when the save is done. */
    sync: 'POST /api/v1/assets/prices/sync',
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
    /** What the product's call is handed when it is not `response`: a refusal (`planRejection`). */
    answer?: Promise<unknown>;
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
    return call.answer ?? call.response;
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

/**
 * A planned request the server refuses (X-R49): once released, the product's call rejects with `error`, as a zodios
 * call rejects with the axios error. `response` settles with that refusal and never rejects, so `finish` and the
 * teardown wait on it as on any other call. Its handler is attached here, before the product's await: when `finish`
 * resumes, the product has already met the refusal, and the flush that follows renders what it made of it.
 */
function planRejection(label: string, route: Route, expectedArgs: unknown[], error: unknown): PlannedCall {
    let refuse!: (reason: unknown) => void;
    let released = false;
    const answer = new Promise<never>((_resolve, reject) => {
        refuse = reject;
    });
    const response = answer.then(
        () => undefined,
        () => undefined,
    );
    const call: PlannedCall = {
        label,
        route,
        expectedArgs: immutable(expectedArgs),
        answer,
        response,
        release() {
            if (!released) {
                released = true;
                refuse(error);
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

// ---------------------------------------------------------------------------
// X5-1 — the dry run and the one dialog it opens.
// ---------------------------------------------------------------------------

/** The figures every dry run below answers with: distinct, so that a dialog saying them is read against the answer. */
const IMPACT_FIGURES = ['41', '17', '23'] as const;

/**
 * Release the dry run's answer and let the save it was holding reach whatever it does next (a dialog, or its first
 * write): the answer travels through the loader's promise and the save's await before Svelte renders, so one flush after
 * the release is not a promise that the continuation ran. Microtask turns only, no clock.
 */
async function answerDryRun(call: PlannedCall) {
    await call.finish();
    for (let turn = 0; turn < 3; turn++) await flushUi();
}

/** One result of the dry run for an asset: by default a params change that deletes prices, events and links. */
function impactResult(assetId: number, overrides: Partial<ImpactResult> = {}): ImpactResult {
    return {asset_id: assetId, action: 'assign', reason: 'params_changed', prices_deleted: 41, events_deleted: 17, transactions_unlinked: 23, blocking_splits: [], ...overrides};
}

/** A dry run with nothing to lose: the server's own `none`. */
function nothingLost(assetId: number, action: 'assign' | 'remove' = 'assign'): ImpactResult {
    return impactResult(assetId, {action, reason: 'none', prices_deleted: 0, events_deleted: 0, transactions_unlinked: 0});
}

/** The dry run as a planned request: its body is the contract (assignments and removals), its answer the results. */
function planImpact(label: string, body: {assignments: AssignmentItem[]; removals: number[]}, ...results: ImpactResult[]): PlannedCall {
    const response: ImpactResponse = {results};
    return plan(label, routes.impact, [body], response);
}

type DialogKind = 'regenerate' | 'switch' | 'remove';
/** The testId of each dialog, as the contract (and the E2E suite) names them. */
const DIALOG_IDS: Record<DialogKind, string> = {
    regenerate: 'asset-scheduled-regen-confirm',
    switch: 'asset-parametric-switch-confirm',
    remove: 'asset-provider-remove-confirm',
};

/** The open dialog of a kind: the dialog around its header, whose buttons are the generic ones. */
function impactDialog(kind: DialogKind): HTMLElement {
    const dialog = screen.getByTestId(DIALOG_IDS[kind]).closest<HTMLElement>('[role="dialog"]');
    if (!dialog) throw new Error(`The ${kind} dialog is not inside a dialog of its own.`);
    return dialog;
}

/** No dialog of the dry run on screen: the save goes on as a plain save. */
function expectNoImpactDialog() {
    for (const [kind, testId] of Object.entries(DIALOG_IDS)) expect(screen.queryByTestId(testId), `no ${kind} dialog`).toBeNull();
}

/**
 * The dialog of `kind` is the only one open, worded by the catalogue keys of its kind (the whole-literal
 * `assets.modal.providerImpact.<kind>{Title,Confirm}`) and its message carries the figures the dry run answered,
 * with no placeholder left raw. Nothing has been sent but the dry run.
 */
function expectImpactDialog(kind: DialogKind, figures: readonly string[] = IMPACT_FIGURES) {
    for (const other of Object.keys(DIALOG_IDS) as DialogKind[]) {
        if (other !== kind) expect(screen.queryByTestId(DIALOG_IDS[other]), `only the ${kind} dialog, not the ${other} one`).toBeNull();
    }
    const dialog = impactDialog(kind);
    expect(dialog).toBeVisible();
    const title = get(_)(`assets.modal.providerImpact.${kind}Title`);
    const confirm = get(_)(`assets.modal.providerImpact.${kind}Confirm`);
    expect(title, `premise: the catalogue has the ${kind} title`).not.toBe(`assets.modal.providerImpact.${kind}Title`);
    expect(within(dialog).getByRole('heading').textContent?.trim(), `the ${kind} title`).toBe(title);
    expect(within(dialog).getByTestId('confirm-modal-confirm').textContent?.trim(), `the ${kind} confirm`).toBe(confirm);
    const message = within(dialog).getByTestId('confirm-modal-message').textContent ?? '';
    for (const figure of figures) expect(message, `the message says ${figure}, from the dry run`).toContain(figure);
    expect(message, 'no placeholder left raw').not.toMatch(/[{}]/);
    expect(mocks.api.patch_assets_bulk_api_v1_assets_patch, 'nothing is sent while the question is open').not.toHaveBeenCalled();
    expect(mocks.api.assign_providers_bulk_api_v1_assets_provider_post).not.toHaveBeenCalled();
    expect(mocks.api.remove_providers_bulk_api_v1_assets_provider_delete).not.toHaveBeenCalled();
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
    // The provider's plugin settings read is incidental too, and checked the same way.
    for (const args of mocks.api.get_plugin_settings_api_v1_settings_plugins_get.mock.calls) {
        expect(args).toStrictEqual(expectedSettingsRead(args));
    }
}

/**
 * The provider's plugin settings read (workstream X, CP11b) as the panel must ask it: the asset family and a provider
 * of the catalogue, nothing else. Built from what was asked, so that a provider of the catalogue matches exactly and
 * any other name fails on one no provider carries.
 */
function expectedSettingsRead(args: unknown[]): unknown[] {
    const code = (args[0] as {queries?: {plugin_code?: unknown}} | undefined)?.queries?.plugin_code;
    const known = providerCatalog().some((provider) => provider.code === code);
    return [{queries: {family: 'asset', plugin_code: known ? code : '(a provider of the catalogue)'}}];
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
        scheduledProvider(),
    ];
}

/** The parametric provider's code (X-R49): the series is generated from its params, the real plugin's own code. */
const SCHEDULED = 'scheduled_investment';

/**
 * The parametric provider as the real plugin declares itself: its series generated from its params, its identifier
 * generated (AUTO_GENERATED is its only type), and its params the schedule editor's, through the `_ui_component`
 * meta-field. Offline like the rest of the catalogue: nothing here reaches a network.
 */
function scheduledProvider(): ProviderInfo {
    return {
        code: SCHEDULED,
        name: 'Fictional schedule',
        description: 'Offline parametric fixture: the series is generated from the stored schedule.',
        kind: 'parametric_generation',
        supports_search: false,
        supports_meaningful_volume: false,
        accepted_identifier_types: ['AUTO_GENERATED'],
        icon_url: null,
        provider_help_url: null,
        params_schema: [{key: '_ui_component', type: 'ui_component', required: false, description: 'Custom editor: ScheduledInvestmentEditor', default: SCHEDULED}],
    };
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
    // Identify each row by the operation it publishes (`data-operation`, the backend's own operation names, the
    // ones the request sends), never by its translated text or its position. An unordered error/success pair
    // alone could hide swapped operation statuses in the real child: here each status is read on its own row.
    expect(rows.map((row) => row.getAttribute('data-operation')).sort(), 'the rows are not exactly the response’s operations, one current_price and one history').toEqual(['current_price', 'history']);
    const rowOf = (operation: 'current_price' | 'history') => rows.find((row) => row.getAttribute('data-operation') === operation);
    expect(statuses, 'premise: the response’s history always succeeds').toContain('success');
    const currentPriceStatus = [...statuses];
    currentPriceStatus.splice(currentPriceStatus.indexOf('success'), 1);
    expect(rowOf('history'), 'the history row').toHaveAttribute('data-status', 'success');
    expect(rowOf('current_price'), 'the current-price row').toHaveAttribute('data-status', currentPriceStatus[0]);
    if (price !== undefined) {
        expect(rowOf('current_price')?.textContent, `owned current-price value ${price}`).toContain(price);
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
    mocks.api.remove_providers_bulk_api_v1_assets_provider_delete.mockImplementation((...args: unknown[]) => consume(routes.remove, args));
    mocks.api.provider_change_impact_api_v1_assets_provider_impact_post.mockImplementation((...args: unknown[]) => consume(routes.impact, args));
    mocks.api.sync_prices_bulk_api_v1_assets_prices_sync_post.mockImplementation((...args: unknown[]) => consume(routes.sync, args));
    mocks.api.list_assets_api_v1_assets_query_get.mockImplementation((...args: unknown[]) => {
        checkArguments('incidental duplicate-name listing', args, [{queries: {}}]);
        return Promise.resolve([]);
    });
    // The provider's plugin settings (workstream X, CP11b): read for every provider the panel shows, answered «no
    // settings». Routed here, so that the facade records the call instead of failing it as «not a function».
    mocks.api.get_plugin_settings_api_v1_settings_plugins_get.mockImplementation((...args: unknown[]) => {
        checkArguments('incidental provider settings read', args, expectedSettingsRead(args));
        return Promise.resolve({plugins: []});
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
    // X-R49: an error the module does not word, unless a case says otherwise.
    mocks.refusals.wipeRefusalMessage.mockReturnValue(null);
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

// ---------------------------------------------------------------------------
// K17 — a provider that only knows the family of the stored type.
//
// Borsa Italiana answers ETF for every fund of ETFplus. Against an asset stored
// as ETF_STOCK that is no disagreement: the provider names the family the
// subtype already belongs to, and knows nothing finer. Offered as a difference,
// the row is ticked by default and Apply rewrites ETF_STOCK to ETF — a downgrade
// nobody asked for. The developer's rule: a proposal of the parent type counts
// as valid anyway, so no row is offered and the stored subtype stays. A sibling
// subtype or a refinement is real information, and is still offered.
//
// The type the form holds is read off the closed type select, whose trigger
// shows the picture of the selected type: an attribute, never a translated label.
// ---------------------------------------------------------------------------

const TYPE_READ_DESCRIPTION = 'Type metadata accepted';

/** A stored asset of `assetType` whose classification the provider repeats verbatim: nothing is missing, so "all match" is reachable. */
function typeEditFixture(assetType: string): EditData {
    return editFixture({asset_type: assetType, classification_params: {sector_area: {distribution: {Technology: 1}}, geographic_area: {distribution: {USA: 1}}}});
}

/**
 * Metadata agreeing with `typeEditFixture` on everything but the type — and the name, when one
 * is given. Its description fills the empty field: the positive barrier before any absence claim.
 */
function typeMetadata(assetType: string, displayName = 'Owned Atlas security'): ProbeResponse {
    return {
        provider_code: 'lifecycle_atlas',
        identifier: 'SYN-ATLAS',
        total_execution_time_ms: 4,
        metadata: {
            success: true,
            execution_time_ms: 4,
            patch_data: {
                display_name: displayName,
                asset_type: assetType,
                currency: 'USD',
                classification_params: {
                    short_description: TYPE_READ_DESCRIPTION,
                    sector_area: {distribution: {Technology: '1'}},
                    geographic_area: {distribution: {USA: '1'}},
                },
            },
        },
    };
}

/** A manual Ask provider landing `response`; ends once this very response was accepted. */
async function askProviderForType(response: ProbeResponse) {
    const metadata = plan('K17 type metadata', routes.metadata, [probeRequest(['metadata'])], response);
    expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
    await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
    expectBusy(true);
    await metadata.finish();
    expectBusy(false);
    // The description is compared after the type, in the same pass: once it has landed, the type has been decided too.
    expect(screen.getByTestId('asset-modal-description')).toHaveValue(TYPE_READ_DESCRIPTION);
}

/** The picture of the type the form holds: the closed type select shows the selected type's, and only it. */
function selectedTypePicture(): string | null {
    const images = screen.getByTestId('asset-modal-type-button').querySelectorAll('img');
    expect(images, 'the closed type select shows exactly one picture, the one of the selected type').toHaveLength(1);
    return images[0].getAttribute('src');
}

/** The fields the comparison on screen asks about. */
function comparisonFields(): string[] {
    const modal = screen.getByTestId('comparison-modal');
    expect(modal).toBeVisible();
    return within(modal)
        .getAllByTestId('comparison-card')
        .map((card) => card.getAttribute('data-field') ?? '');
}

describe('AssetModal keeps a stored subtype the provider only knows by its family (K17)', () => {
    it.each([
        {label: 'nothing else differs', providerName: 'Owned Atlas security', after: [] as string[]},
        {label: 'the name differs too', providerName: 'Provider family-only title', after: ['display_name']},
    ])('offers no type row for ETF against a stored ETF_STOCK, and keeps the subtype ($label)', async ({providerName, after}) => {
        expect(getAssetTypeIconUrl('ETF_STOCK'), 'ETF_STOCK and ETF share a picture: the type select could not tell the stored subtype from its family').not.toBe(getAssetTypeIconUrl('ETF'));
        await renderEdit(typeEditFixture('ETF_STOCK'));
        expect(selectedTypePicture()).toBe(getAssetTypeIconUrl('ETF_STOCK'));

        await askProviderForType(typeMetadata('ETF', providerName));
        // K17: today the family-only ETF arrives as a ticked difference, and Apply downgrades ETF_STOCK to ETF.
        expect(screen.queryByTestId('comparison-checkbox-asset_type'), 'the provider proposed ETF, the family of the stored ETF_STOCK. By the K17 rule that is agreement, not a difference: offered as a row it is ticked by default, and Apply downgrades the stored subtype to its family').toBeNull();
        if (after.length === 0) {
            // Nothing left to ask: no dialog, and the "all match" claim proves the comparison ran to its end.
            expect(screen.queryByTestId('comparison-modal')).toBeNull();
            expect(mocks.toasts.success).toHaveBeenCalledTimes(1);
        } else {
            expect(comparisonFields()).toEqual(after);
            await fireEvent.click(screen.getByTestId('comparison-apply'));
            await flushUi();
            expect(screen.queryByTestId('comparison-modal')).toBeNull();
            expect(screen.getByTestId('asset-modal-display-name')).toHaveValue(providerName);
        }
        expect(selectedTypePicture(), 'the stored ETF_STOCK must survive a provider that only knows its family').toBe(getAssetTypeIconUrl('ETF_STOCK'));
        assertTraffic();
    });

    it.each([
        {label: 'a sibling subtype', stored: 'ETF_STOCK', proposed: 'ETF_BOND'},
        {label: 'a refinement of the stored family', stored: 'ETF', proposed: 'ETF_STOCK'},
    ])('still offers $label as a ticked type row, and Apply takes it ($stored → $proposed)', async ({stored, proposed}) => {
        expect(getAssetTypeIconUrl(stored), `${stored} and ${proposed} share a picture: the type select could not tell them apart`).not.toBe(getAssetTypeIconUrl(proposed));
        await renderEdit(typeEditFixture(stored));
        expect(selectedTypePicture()).toBe(getAssetTypeIconUrl(stored));

        await askProviderForType(typeMetadata(proposed));
        expect(comparisonFields()).toEqual(['asset_type']);
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-total-count', '1');
        expect(screen.getByTestId('comparison-checkbox-asset_type')).toBeChecked();
        await fireEvent.click(screen.getByTestId('comparison-apply'));
        await flushUi();
        expect(screen.queryByTestId('comparison-modal')).toBeNull();
        // The reading the family-only case relies on, proven live: the select follows a type the comparison wrote.
        expect(selectedTypePicture()).toBe(getAssetTypeIconUrl(proposed));
        assertTraffic();
    });
});

// ---------------------------------------------------------------------------
// X-R49 — the assignment refuses to delete a split of the plan.
//
// A parametric provider generates the series, events included, from its params:
// changing them (or leaving the provider) regenerates the plan, and the server
// deletes the old one first. Since X-R49 the assignment (POST /assets/provider)
// refuses, writing nothing, when a SPLIT of that plan carries linked incoming
// adjustments without a purchase cost — gone, those units would count as bought
// at an unknown price: 409, `detail.error_code` =
// PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST, the splits in its params. The
// save reaches the assignment by two roads, and today neither says what happened:
//   - the regenerate question (`asset-scheduled-regen-confirm`; since X5-1 the
//     server's dry run opens it, whatever kind the modal knows the provider
//     by): its confirm re-invokes saveEdit outside trySave, and its catch toasts
//     the generic «an error occurred»;
//   - the plain save, through trySave, when the dry run opens no dialog (here it
//     reports a blocking split, so the real call will be refused): its onError
//     reads every 409 as «duplicate name».
// The cure, in saveEdit's step 2: a refusal `wipeRefusalMessage` words becomes
// the form's banner (`asset-modal-form-error`), pendingSaveAssetId is reset, and
// the save stops there — no toast, no sync, the modal open, no onupdated. Any
// other failure is thrown on, as today.
//
// The asset is a scheduled_investment edited through the real
// ScheduledInvestmentEditor: its initial value is the param that changes. The
// module answers a marker for the very refusal the assignment threw, so the
// banner is read against what the module wrote, never against a translation.
//
// Red before the cure: on the regenerate road no banner (the generic toast
// instead) and the module never asked; on the plain road the banner says
// «duplicate name». The guards are green before and after it: on each road, a
// failure the module does not word keeps today's handling.
// ---------------------------------------------------------------------------

const SCHEDULED_ASSET_ID = 8201;
const PLAN_REFUSAL_CODE = 'PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST';
/** What the stubbed `wipeRefusalMessage` answers for the refusal: a marker, so the banner is read against the module's answer. */
const REFUSAL_SENTENCE = '⟨wipeRefusalMessage: the refused plan, worded⟩';

/** The schedule as the editor writes it, so that its own serialisation gives it back unchanged; only the initial value varies. */
function scheduledParams(amount: string): Record<string, unknown> {
    return {
        initial_value: {code: 'EUR', amount},
        interest_type: 'SIMPLE',
        day_count: 'ACT/365',
        schedule: [{start_date: '2025-01-01', end_date: '2025-12-31', annual_rate: '0.0500', maturation_frequency: 'MONTHLY', generate_interest: false}],
        late_interest: null,
        asset_events: [],
    };
}

/** A stored scheduled asset: a loan priced by the parametric provider, its identifier generated (none is stored). */
function scheduledFixture(): EditData {
    return {
        id: SCHEDULED_ASSET_ID,
        display_name: 'Owned scheduled loan',
        currency: 'EUR',
        asset_type: 'CROWDFUND',
        provider_code: SCHEDULED,
        provider_identifier_type: 'AUTO_GENERATED',
        provider_params: scheduledParams('10000'),
    };
}

/** Independent oracle of the save's PATCH: the stored fields as they are — the edit is the plan's alone. */
function scheduledPatch(): PatchItem[] {
    return [
        {
            asset_id: SCHEDULED_ASSET_ID,
            display_name: 'Owned scheduled loan',
            currency: 'EUR',
            asset_type: 'CROWDFUND',
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
}

function scheduledPatchAccepted(): PatchResponse {
    return {results: [{asset_id: SCHEDULED_ASSET_ID, success: true, message: 'Synthetic patch accepted'}], success_count: 1, errors: []};
}

/** Independent oracle of the assignment: the provider with the schedule the editor wrote, its initial value now 12000. */
function scheduledAssignment(): AssignmentItem[] {
    return [{asset_id: SCHEDULED_ASSET_ID, provider_code: SCHEDULED, identifier: '', identifier_type: 'AUTO_GENERATED', provider_params: scheduledParams('12000')}];
}

/** An HTTP failure as a zodios (axios) call rejects with it: the axios error, its answer's `detail` as sent. */
function apiError(status: number, detail: unknown): Error & {response: {status: number; data: {detail: unknown}}} {
    return Object.assign(new Error(`Request failed with status code ${status}`), {response: {status, data: {detail}}});
}

/** The assignment's X-R49 refusal: 409, a structured detail, the server's English (totals only), the splits in its params. */
function splitOfPlanRefusal() {
    return apiError(409, {
        error_code: PLAN_REFUSAL_CODE,
        message: 'Provider not assigned: 1 split of the plan has 2 linked adjustments without a purchase cost',
        params: {asset_id: SCHEDULED_ASSET_ID, item_index: 0, splits: [{event_id: 31, date: '2026-02-10', transaction_ids: [5], hidden_transactions_count: 1}]},
    });
}

/** A 409 the module does not word: a conflict, but not a split of the plan. */
function otherConflict() {
    return apiError(409, {error_code: 'SYNTHETIC_OTHER_CONFLICT', message: 'Synthetic conflict that is not a split of the plan', params: {}});
}

/** Make the module word `refusal` — that very error, and nothing else — as `sentence`. */
function wordRefusal(refusal: unknown, sentence = REFUSAL_SENTENCE) {
    mocks.refusals.wipeRefusalMessage.mockImplementation((err: unknown) => (err === refusal ? sentence : null));
}

/** Change the stored plan through the real editor: its initial value, 10000 → 12000. Ends on a changed, untested provider. */
async function changeScheduledInitialValue() {
    // Premise: the editor read the stored schedule — its one period is there, and valid.
    expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-valid', 'true');
    const field = screen.getByTestId('schedule-initial-value');
    expect(field).toBeVisible();
    expect(field).toBeEnabled();
    expect(field).toHaveValue(10000);
    await fireEvent.input(field, {target: {value: '12000'}});
    await flushUi();
    expect(screen.getByTestId('schedule-initial-value')).toHaveValue(12000);
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
    expectStatus('not_tested');
}

/** Save the changed, untested provider, and answer its «save without testing?»: the sole confirmation on screen. */
async function saveUntestedProvider() {
    expect(screen.getByTestId('asset-modal-save')).toBeEnabled();
    await fireEvent.click(screen.getByTestId('asset-modal-save'));
    await flushUi();
    expect(screen.queryByTestId('asset-scheduled-regen-confirm'), 'the untested provider is asked about first').toBeNull();
    // getByTestId also rejects an ambiguous second generic confirmation.
    expect(screen.getByTestId('confirm-modal-message')).toBeVisible();
    await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
    await referenceReady; // The real saveEdit awaits the ready provider cache.
    await flushUi();
}

/** The dry run of the scheduled asset's plan change, as the save must ask it: the assignment alone, no removal. */
function scheduledImpactBody() {
    return {assignments: scheduledAssignment(), removals: []};
}

/**
 * The regenerate road (X5-1: the dry run, then the dialog): the plan of a parametric asset changed and saved, «save
 * without testing?» answered, the dry run answered with a loss, and the regenerate dialog confirmed. The PATCH is
 * accepted and the assignment fails with `error`. Ends with that failure handled and every request answered.
 *
 * `isParametricProvider` stays false throughout (the beforeEach default): the dialog follows the server's dry run, not
 * the kind the modal knows the provider by.
 */
async function regenerateAndFail(error: unknown) {
    const view = await renderEdit(scheduledFixture());
    await changeScheduledInitialValue();
    const impact = planImpact('regenerate dry run', scheduledImpactBody(), impactResult(SCHEDULED_ASSET_ID));
    await saveUntestedProvider();
    // The dry run goes first and alone: nothing is written before the user has been told what is lost.
    impact.assertUnchanged();
    expect(mocks.api.patch_assets_bulk_api_v1_assets_patch).not.toHaveBeenCalled();
    expectBusy(true);
    await answerDryRun(impact);
    // Its params changed and the dry run says something is lost: the save waits on the regenerate question.
    expectImpactDialog('regenerate');
    const patch = plan('regenerate PATCH', routes.patch, [scheduledPatch()], scheduledPatchAccepted());
    const assignment = planRejection('regenerate assignment', routes.assign, [scheduledAssignment()], error);
    await fireEvent.click(within(impactDialog('regenerate')).getByTestId('confirm-modal-confirm'));
    await referenceReady; // The confirmation re-invokes saveEdit, which awaits the ready provider cache again.
    await flushUi();
    expect(screen.queryByTestId(DIALOG_IDS.regenerate)).toBeNull();
    patch.assertUnchanged();
    expect(assignment.actualArgs).toBeUndefined();
    await patch.finish();
    assignment.assertUnchanged();
    await assignment.finish();
    await flushUi();
    return view;
}

/**
 * The plain road: the changed plan saved through trySave with no dialog, because the dry run lets the save go on —
 * `dryRun` is its result: nothing to lose, or a split that will refuse the real call. The PATCH is accepted and the
 * assignment fails with `error`. Ends with that failure handled and every request answered.
 */
async function saveStraightAndFail(error: unknown, dryRun: ImpactResult = nothingLost(SCHEDULED_ASSET_ID)) {
    const view = await renderEdit(scheduledFixture());
    await changeScheduledInitialValue();
    const impact = planImpact('plain-save dry run', scheduledImpactBody(), dryRun);
    const patch = plan('plain-save PATCH', routes.patch, [scheduledPatch()], scheduledPatchAccepted());
    const assignment = planRejection('plain-save assignment', routes.assign, [scheduledAssignment()], error);
    await saveUntestedProvider();
    impact.assertUnchanged();
    expect(patch.actualArgs, 'the PATCH waits for the dry run').toBeUndefined();
    expectBusy(true);
    await answerDryRun(impact);
    expectNoImpactDialog();
    await flushUi();
    patch.assertUnchanged();
    await patch.finish();
    assignment.assertUnchanged();
    await assignment.finish();
    await flushUi();
    return view;
}

/** Where a stopped save leaves the user: the modal open on their draft, nothing reported done, nothing synced. */
function expectSaveStopped(view: Awaited<ReturnType<typeof renderEdit>>) {
    expect(screen.getByTestId('asset-modal')).toBeVisible();
    expectBusy(false);
    expect(screen.getByTestId('schedule-initial-value'), 'the draft is still the user’s').toHaveValue(12000);
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
    expect(view.onupdated).not.toHaveBeenCalled();
    expect(view.onclose).not.toHaveBeenCalled();
    expect(view.oncreated).not.toHaveBeenCalled();
    expect(mocks.toasts.success).not.toHaveBeenCalled();
    expect(mocks.api.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
}

/** The next save asks the dry run and the regenerate question again — pendingSaveAssetId was reset — and sends nothing; it is then cancelled. */
async function expectRegenerateAskedAgain() {
    const again = planImpact('asked again: regenerate dry run', scheduledImpactBody(), impactResult(SCHEDULED_ASSET_ID));
    await saveUntestedProvider();
    again.assertUnchanged();
    await answerDryRun(again);
    expect(impactDialog('regenerate'), 'pendingSaveAssetId reset: the next save asks again instead of sending').toBeVisible();
    expect(mocks.api.patch_assets_bulk_api_v1_assets_patch).toHaveBeenCalledTimes(1);
    expect(mocks.api.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledTimes(1);
    await fireEvent.click(within(impactDialog('regenerate')).getByTestId('confirm-modal-cancel'));
    await flushUi();
    expect(screen.queryByTestId(DIALOG_IDS.regenerate)).toBeNull();
    expect(screen.getByTestId('asset-modal')).toBeVisible();
}

describe('AssetModal: a provider change refused for a split of the plan (X-R49)', () => {
    let consoleError: MockInstance<typeof console.error>;

    beforeEach(() => {
        // Both roads log the failure they catch: the guards read that log, the other cases only silence it.
        consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    it('regenerate road: the refusal is the banner the module wrote — no toast, no sync, the modal open — and the next save asks again', async () => {
        const refusal = splitOfPlanRefusal();
        wordRefusal(refusal);
        const view = await regenerateAndFail(refusal);

        // Today: no banner, and the confirmation's catch toasts the generic «an error occurred».
        const banner = screen.queryByTestId('asset-modal-form-error');
        expect(banner, 'the refusal must reach the form, as its banner').not.toBeNull();
        expect(banner).toBeVisible();
        expect(banner).toHaveAttribute('data-form-error');
        expect(banner?.textContent?.trim(), "the banner is the module's sentence for that refusal, as it wrote it").toBe(REFUSAL_SENTENCE);
        expect(mocks.toasts.error, 'one sentence, in the banner: not also «an error occurred»').not.toHaveBeenCalled();
        expect(mocks.toasts.warning).not.toHaveBeenCalled();
        expect(mocks.toasts.info).not.toHaveBeenCalled();
        expectSaveStopped(view);

        await expectRegenerateAskedAgain();
        assertTraffic();
    });

    it('regenerate road: the module is asked about the very error the assignment threw, with the interface translator and its day label', async () => {
        const refusal = splitOfPlanRefusal();
        wordRefusal(refusal);
        await regenerateAndFail(refusal);

        expect(mocks.refusals.wipeRefusalMessage, 'asked once, when the assignment failed').toHaveBeenCalledTimes(1);
        const [err, translate, dateLabel] = mocks.refusals.wipeRefusalMessage.mock.calls[0];
        expect(err, 'the error as the assignment rejected with it').toBe(refusal);
        const key = 'assets.modal.saveFailed';
        expect(get(_)(key), `premise: the catalogue has ${key}`).not.toBe(key);
        expect(translate(key), 'the translator of the interface: a key reads as the catalogue writes it').toBe(get(_)(key));
        expect(dateLabel, 'a day label is handed over').toBeTypeOf('function');
        expect(formatDay('2026-02-10'), 'premise: the interface does not write a day in its ISO form').not.toBe('2026-02-10');
        expect(dateLabel('2026-02-10'), 'the day written as the interface writes one (formatDay)').toBe(formatDay('2026-02-10'));
        assertTraffic();
    });

    it.each<[string, () => unknown]>([
        ['a 409 the module does not word', otherConflict],
        ['a request that got no answer', () => new Error('Network Error')],
    ])('guard — regenerate road, %s: as today, the generic error toast, the very error logged, no banner, and the next save asks again', async (_label, failure) => {
        const error = failure();
        const view = await regenerateAndFail(error);

        const generic = get(_)('common.errorOccurred');
        expect(generic, 'premise: the catalogue has common.errorOccurred').not.toBe('common.errorOccurred');
        expect(mocks.toasts.error, 'one error toast').toHaveBeenCalledTimes(1);
        expect(mocks.toasts.error, "the confirmation's own generic sentence").toHaveBeenCalledWith(generic);
        expect(consoleError, "the confirmation's catch still receives the very error: thrown on, as before").toHaveBeenCalledWith(expect.any(String), error);
        expect(screen.queryByTestId('asset-modal-form-error'), 'no banner: the module did not word it').toBeNull();
        expectSaveStopped(view);

        await expectRegenerateAskedAgain();
        assertTraffic();
    });

    it('plain road (the dry run reports a blocking split, so no dialog): the refusal is the banner the module wrote, not «duplicate name»', async () => {
        const refusal = splitOfPlanRefusal();
        wordRefusal(refusal);
        const blocking = impactResult(SCHEDULED_ASSET_ID, {blocking_splits: [{event_id: 31, date: '2026-02-10', transaction_ids: [5], hidden_transactions_count: 1}]});
        const view = await saveStraightAndFail(refusal, blocking);

        const banner = screen.getByTestId('asset-modal-form-error');
        expect(banner).toBeVisible();
        // Today trySave's onError reads every 409 as a duplicate name.
        expect(banner.textContent?.trim(), "the banner is the module's sentence for that refusal, not «duplicate name»").toBe(REFUSAL_SENTENCE);
        expect(mocks.toasts.error).not.toHaveBeenCalled();
        expect(mocks.toasts.warning).not.toHaveBeenCalled();
        expect(mocks.toasts.info).not.toHaveBeenCalled();
        expectSaveStopped(view);
        assertTraffic();
    });

    it('guard — plain road, a 409 the module does not word: as today, the banner reads it as «duplicate name»', async () => {
        const view = await saveStraightAndFail(otherConflict());

        const duplicateName = get(_)('assets.modal.duplicateName');
        expect(duplicateName, 'premise: the catalogue has assets.modal.duplicateName').not.toBe('assets.modal.duplicateName');
        expect(screen.getByTestId('asset-modal-form-error').textContent?.trim(), "trySave's reading of a 409, kept: the error is thrown on, as before").toBe(duplicateName);
        expect(mocks.toasts.error, 'inline, as today: no toast').not.toHaveBeenCalled();
        expectSaveStopped(view);
        assertTraffic();
    });
});

// ---------------------------------------------------------------------------
// X-R62, rewritten by X5-1 — removing the provider.
//
// «No provider» removes the asset's provider (DELETE /assets/provider), and the
// server deletes the events that provider generated with it. X-R62 made the
// removal refuse while transactions were linked to those events
// (PROVIDER_REMOVAL_LINKED_TRANSACTIONS). X5-1 (developer decision) turned that
// refusal into the rule of every provider change: the dry run (POST
// /assets/provider/impact) counts what is lost, ONE dialog
// (`asset-provider-remove-confirm`) tells it — prices, provider events and the
// transactions that lose the link and are kept — and on confirm the removal
// proceeds and disconnects them. The code PROVIDER_REMOVAL_LINKED_TRANSACTIONS no
// longer exists. The removal's 409s are the split refusal
// (PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST, said inline as the assignment's
// is) and PROVIDER_REMOVAL_CONFLICT, a link made between the check and the delete.
//
// The asset is the Atlas one of `editFixture`, its provider unticked through the
// real header switch (`asset-modal-no-provider`). Two roads, by the dry run's
// answer: a loss opens the dialog and the confirm re-enters saveEdit (outside
// trySave, as the regenerate confirm does); nothing to lose, a blocking split or
// a failed dry run opens nothing and the save runs through trySave. The module
// answers a marker for the very refusal the removal threw, so the banner is read
// against what the module wrote, never against a translation.
//
// Red before the cure: the dry run is never asked and no dialog opens. The
// guards that keep today's handling of a failure the module does not word are
// green on the plain road only once that road asks its dry run too.
// ---------------------------------------------------------------------------

/** The Atlas asset of `editFixture`, whose provider the save removes. */
const ATLAS_ASSET_ID = 8101;
/** What the stubbed `wipeRefusalMessage` answers for each refusal of the removal: markers, so the banner is read against the module's answer. */
const SPLIT_SENTENCE = '⟨wipeRefusalMessage: the removal refused for a split with adjustments without a cost, worded⟩';
const CONFLICT_SENTENCE = '⟨wipeRefusalMessage: the removal that met a new link, worded⟩';
/** The detail of a 500 on the removal: a sentence trySave shows as it is. */
const REMOVAL_FAILURE_DETAIL = 'Synthetic failure of the provider removal';

/** Independent oracle of the save's PATCH: the stored fields as they are — the edit is the provider's removal alone. */
function atlasPatch(): PatchItem[] {
    return [
        {
            asset_id: ATLAS_ASSET_ID,
            display_name: 'Owned Atlas security',
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
}

function atlasPatchAccepted(): PatchResponse {
    return {results: [{asset_id: ATLAS_ASSET_ID, success: true, message: 'Synthetic patch accepted'}], success_count: 1, errors: []};
}

/** Independent oracle of the removal as the save sends it: no body, the asset in the query. */
function removalArgs(): unknown[] {
    return [undefined, {queries: {asset_ids: [ATLAS_ASSET_ID]}}];
}

function removalAccepted(): RemovalResponse {
    return {results: [{asset_id: ATLAS_ASSET_ID, success: true, deleted_count: 1, message: 'Synthetic removal accepted'}], success_count: 1, errors: []};
}

/** The removal's split refusal: 409, the same code and params as the assignment's (X-R49), the splits listed. */
function splitOnRemovalRefusal() {
    return apiError(409, {
        error_code: 'PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST',
        message: 'Provider not removed: 1 split of the plan has 2 linked adjustments without a purchase cost',
        params: {asset_id: ATLAS_ASSET_ID, item_index: 0, splits: [{event_id: 41, date: '2026-03-02', transaction_ids: [7, 9], hidden_transactions_count: 1}]},
    });
}

/** The removal's other refusal (X-R62): a link appeared between the check and the delete; its params are empty. */
function removalConflict() {
    return apiError(409, {error_code: 'PROVIDER_REMOVAL_CONFLICT', message: 'Provider not removed: a link to its events appeared meanwhile', params: {}});
}

/** A failure of the removal that is no refusal: a 500 whose detail is a sentence. */
function removalServerError() {
    return apiError(500, REMOVAL_FAILURE_DETAIL);
}

/** Untick the asset's provider through the real header switch. Ends on a dirty draft with no provider, its assignment form folded away. */
async function chooseNoProvider() {
    const noProvider = screen.getByTestId('asset-modal-no-provider');
    expect(noProvider).toBeVisible();
    expect(noProvider).toBeEnabled();
    expect(noProvider).not.toBeChecked();
    await fireEvent.click(noProvider);
    await flushUi();
    expect(screen.getByTestId('asset-modal-no-provider')).toBeChecked();
    expect(screen.getByTestId('asset-modal-provider-header')).toHaveAttribute('data-expanded', 'false');
    expect(screen.queryByTestId('provider-test-config'), 'no provider left to test').toBeNull();
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
}

/** The dry run of the Atlas removal, as the save must ask it: the asset alone in the removals, no assignment. */
function removalImpactBody() {
    return {assignments: [], removals: [ATLAS_ASSET_ID]};
}

/** The dry run's answer for the Atlas removal: by default a loss of prices, events and links. */
function removalDryRun(overrides: Partial<ImpactResult> = {}): ImpactResult {
    return impactResult(ATLAS_ASSET_ID, {action: 'remove', reason: 'provider_removed', ...overrides});
}

/** How a case plans the dry run: an answer, or a function that plans it its own way (a refusal). */
type DryRun = ImpactResult | ((body: ReturnType<typeof removalImpactBody>) => PlannedCall);

/**
 * The removal road: the Atlas asset's provider unticked and the asset saved. The dry run is asked first and alone; with
 * `outcome` 'dialog' it opens the removal dialog and the save goes on after its confirm (outside trySave), with 'plain'
 * it opens nothing and the save runs through trySave. The PATCH is accepted and the removal is answered by the call
 * `planRemoval` plans on the expected arguments. Ends with that answer handled and every request answered.
 */
async function saveWithoutProvider(planRemoval: (expectedArgs: unknown[]) => PlannedCall, dryRun: DryRun = removalDryRun(), outcome: 'dialog' | 'plain' = 'dialog') {
    const view = await renderEdit();
    await chooseNoProvider();
    const body = removalImpactBody();
    const impact = typeof dryRun === 'function' ? dryRun(body) : planImpact('removal dry run', body, dryRun);
    const patch = plan('removal-road PATCH', routes.patch, [atlasPatch()], atlasPatchAccepted());
    const removal = planRemoval(removalArgs());
    expect(screen.getByTestId('asset-modal-save')).toBeEnabled();
    await fireEvent.click(screen.getByTestId('asset-modal-save'));
    await referenceReady; // The real saveEdit awaits the ready provider cache.
    await flushUi();
    expect(screen.queryByTestId('confirm-modal-message'), 'no provider left to test: the save asks nothing before the dry run').toBeNull();
    impact.assertUnchanged();
    expect(patch.actualArgs, 'the PATCH waits for the dry run').toBeUndefined();
    expect(removal.actualArgs).toBeUndefined();
    expectBusy(true);
    await answerDryRun(impact);
    if (outcome === 'dialog') {
        // The message carries the figures this answer holds (a removal deletes no price: its figures are its own).
        expectImpactDialog('remove', typeof dryRun === 'function' ? IMPACT_FIGURES : [dryRun.prices_deleted, dryRun.events_deleted, dryRun.transactions_unlinked].filter((figure) => figure > 0).map(String));
        await fireEvent.click(within(impactDialog('remove')).getByTestId('confirm-modal-confirm'));
        await referenceReady; // The confirmation re-invokes saveEdit, which awaits the ready provider cache again.
        await flushUi();
        expect(screen.queryByTestId(DIALOG_IDS.remove)).toBeNull();
    } else {
        expectNoImpactDialog();
        await flushUi();
    }
    patch.assertUnchanged();
    expect(removal.actualArgs, 'the removal waits for the PATCH').toBeUndefined();
    await patch.finish();
    removal.assertUnchanged();
    await removal.finish();
    await flushUi();
    return view;
}

/** Where a stopped removal leaves the user: the modal open on their draft — still without a provider — nothing reported done, nothing synced. */
function expectRemovalStopped(view: Awaited<ReturnType<typeof renderEdit>>) {
    expect(screen.getByTestId('asset-modal')).toBeVisible();
    expectBusy(false);
    expect(screen.getByTestId('asset-modal-no-provider'), 'the draft is still the user’s: no provider').toBeChecked();
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
    expect(screen.getByTestId('asset-modal-save'), 'the save can be tried again, once the transactions are unlinked').toBeEnabled();
    expect(view.onupdated).not.toHaveBeenCalled();
    expect(view.onclose).not.toHaveBeenCalled();
    expect(view.oncreated).not.toHaveBeenCalled();
    expect(mocks.toasts.success).not.toHaveBeenCalled();
    expect(mocks.api.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
}

/** The sole removal question on screen after a save of the unticked provider: the dry run asked, answered, the dialog open. */
async function askRemoval(dryRun: ImpactResult = removalDryRun(), label = 'removal dry run') {
    const impact = planImpact(label, removalImpactBody(), dryRun);
    await fireEvent.click(screen.getByTestId('asset-modal-save'));
    await referenceReady; // The real saveEdit awaits the ready provider cache.
    await flushUi();
    impact.assertUnchanged();
    await answerDryRun(impact);
    expectImpactDialog('remove');
}

/** One success, the way a finished save ends: the modal closed, onupdated once, one success toast, nothing synced. */
function expectRemovalSaved(view: Awaited<ReturnType<typeof renderEdit>>) {
    expect(screen.queryByTestId('asset-modal')).toBeNull();
    expect(view.onupdated).toHaveBeenCalledTimes(1);
    expect(view.onupdated).toHaveBeenCalledWith();
    expect(view.onclose).not.toHaveBeenCalled();
    expect(view.oncreated).not.toHaveBeenCalled();
    expect(mocks.toasts.success).toHaveBeenCalledTimes(1);
    expect(mocks.toasts.error).not.toHaveBeenCalled();
    expect(mocks.toasts.warning).not.toHaveBeenCalled();
    expect(mocks.refusals.wipeRefusalMessage, 'nothing refused, nothing to word').not.toHaveBeenCalled();
    expect(mocks.api.sync_prices_bulk_api_v1_assets_prices_sync_post, 'no provider left to sync').not.toHaveBeenCalled();
}

describe('AssetModal: removing the provider asks the dry run, then one dialog (X5-1, replaces X-R62)', () => {
    let consoleError: MockInstance<typeof console.error>;

    beforeEach(() => {
        // trySave and the confirmations log the failure they handle: the guards read that log, the other cases only silence it.
        consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    it('a loss opens the removal dialog, the dry run having been asked alone; confirm sends the PATCH, then the removal, and the asset is saved', async () => {
        const view = await saveWithoutProvider((expectedArgs) => plan('accepted removal', routes.remove, expectedArgs, removalAccepted()));

        expectRemovalSaved(view);
        assertTraffic();
    });

    it('a removal with linked transactions is no longer refused: the dialog says it, and confirm goes through', async () => {
        // The case X-R62 refused: events with linked transactions (23 lose the link, they are kept). Only the dialog stands between the user and the delete.
        const view = await saveWithoutProvider((expectedArgs) => plan('accepted removal', routes.remove, expectedArgs, removalAccepted()), removalDryRun({prices_deleted: 0, events_deleted: 2, transactions_unlinked: 23}));

        expectRemovalSaved(view);
        expect(consoleError).not.toHaveBeenCalled();
        assertTraffic();
    });

    it('cancel: nothing is sent, the draft is still the user’s, and the next save asks the dry run and the question again', async () => {
        const view = await renderEdit();
        await chooseNoProvider();
        await askRemoval();
        await fireEvent.click(within(impactDialog('remove')).getByTestId('confirm-modal-cancel'));
        await flushUi();

        expect(screen.queryByTestId(DIALOG_IDS.remove)).toBeNull();
        expect(mocks.api.patch_assets_bulk_api_v1_assets_patch).not.toHaveBeenCalled();
        expect(mocks.api.remove_providers_bulk_api_v1_assets_provider_delete).not.toHaveBeenCalled();
        expectRemovalStopped(view);

        // pendingSaveAssetId was cleared: a second save asks again instead of sending.
        await askRemoval(removalDryRun(), 'removal dry run, asked again');
        await fireEvent.click(within(impactDialog('remove')).getByTestId('confirm-modal-cancel'));
        await flushUi();
        expect(screen.queryByTestId(DIALOG_IDS.remove)).toBeNull();
        expect(mocks.api.patch_assets_bulk_api_v1_assets_patch).not.toHaveBeenCalled();
        assertTraffic();
    });

    it.each([
        ['reason none', removalDryRun({reason: 'none', prices_deleted: 0, events_deleted: 0, transactions_unlinked: 0})],
        ['nothing to delete', removalDryRun({prices_deleted: 0, events_deleted: 0, transactions_unlinked: 0})],
    ])('%s: no dialog, the save goes on as a plain save through trySave', async (_label, dryRun) => {
        const view = await saveWithoutProvider((expectedArgs) => plan('accepted removal', routes.remove, expectedArgs, removalAccepted()), dryRun, 'plain');

        expectRemovalSaved(view);
        assertTraffic();
    });

    it('a dry run that failed: no dialog, a console warning, and the save goes on — the server judges', async () => {
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const view = await saveWithoutProvider(
            (expectedArgs) => plan('accepted removal', routes.remove, expectedArgs, removalAccepted()),
            (body) => planRejection('failed removal dry run', routes.impact, [body], apiError(500, 'Synthetic failure of the dry run')),
            'plain',
        );

        expectRemovalSaved(view);
        expect(warn, 'the failure of the dry run is warned, never thrown').toHaveBeenCalled();
        assertTraffic();
    });

    it.each<[string, () => unknown, string]>([
        ['PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST', splitOnRemovalRefusal, SPLIT_SENTENCE],
        ['PROVIDER_REMOVAL_CONFLICT', removalConflict, CONFLICT_SENTENCE],
    ])('%s: the refusal is the banner the module wrote, not «duplicate name» — no toast, no sync, the modal open on the draft', async (code, refused, sentence) => {
        const refusal = refused();
        wordRefusal(refusal, sentence);
        // The split refusal is announced by the dry run (a blocking split: no dialog); the conflict is not (a loss: the dialog, then the conflict).
        const split = code === 'PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST';
        const dryRun = split ? removalDryRun({blocking_splits: [{event_id: 41, date: '2026-03-02', transaction_ids: [7, 9], hidden_transactions_count: 1}]}) : removalDryRun();
        const view = await saveWithoutProvider((expectedArgs) => planRejection('refused removal', routes.remove, expectedArgs, refusal), dryRun, split ? 'plain' : 'dialog');

        const banner = screen.getByTestId('asset-modal-form-error');
        expect(banner).toBeVisible();
        expect(banner).toHaveAttribute('data-form-error');
        expect(banner.textContent?.trim(), "the banner is the module's sentence for that refusal, not «duplicate name»").toBe(sentence);
        expect(mocks.toasts.error).not.toHaveBeenCalled();
        expect(mocks.toasts.warning).not.toHaveBeenCalled();
        expect(mocks.toasts.info).not.toHaveBeenCalled();
        expectRemovalStopped(view);
        assertTraffic();
    });

    it('the module is asked about the very error the removal threw, with the interface translator and its day label', async () => {
        const refusal = splitOnRemovalRefusal();
        wordRefusal(refusal, SPLIT_SENTENCE);
        const blocking = removalDryRun({blocking_splits: [{event_id: 41, date: '2026-03-02', transaction_ids: [7, 9], hidden_transactions_count: 1}]});
        await saveWithoutProvider((expectedArgs) => planRejection('refused removal', routes.remove, expectedArgs, refusal), blocking, 'plain');

        expect(mocks.refusals.wipeRefusalMessage, 'asked once, when the removal failed').toHaveBeenCalledTimes(1);
        const [err, translate, dateLabel] = mocks.refusals.wipeRefusalMessage.mock.calls[0];
        expect(err, 'the error as the removal rejected with it').toBe(refusal);
        const key = 'assets.modal.saveFailed';
        expect(get(_)(key), `premise: the catalogue has ${key}`).not.toBe(key);
        expect(translate(key), 'the translator of the interface: a key reads as the catalogue writes it').toBe(get(_)(key));
        expect(dateLabel, 'a day label is handed over').toBeTypeOf('function');
        expect(formatDay('2026-03-02'), 'premise: the interface does not write a day in its ISO form').not.toBe('2026-03-02');
        expect(dateLabel('2026-03-02'), 'the day written as the interface writes one (formatDay)').toBe(formatDay('2026-03-02'));
        assertTraffic();
    });

    it('guard — a 500 with no dialog: as today, thrown on to trySave, whose reading of it, the server detail, is the banner; the save stops', async () => {
        const failure = removalServerError();
        const view = await saveWithoutProvider((expectedArgs) => planRejection('failed removal', routes.remove, expectedArgs, failure), nothingLost(ATLAS_ASSET_ID, 'remove'), 'plain');

        expect(screen.getByTestId('asset-modal-form-error').textContent?.trim(), "trySave's reading of a detail it can show, kept: the error is thrown on, as before").toBe(REMOVAL_FAILURE_DETAIL);
        expect(consoleError.mock.calls.flat(), 'the very error reached trySave').toContain(failure);
        expect(mocks.toasts.error, 'inline, as today: no toast').not.toHaveBeenCalled();
        expectRemovalStopped(view);
        assertTraffic();
    });

    it('guard — a 409 the module does not word, with no dialog: as today, the banner reads it as «duplicate name»', async () => {
        const failure = otherConflict();
        const view = await saveWithoutProvider((expectedArgs) => planRejection('failed removal', routes.remove, expectedArgs, failure), nothingLost(ATLAS_ASSET_ID, 'remove'), 'plain');

        const duplicateName = get(_)('assets.modal.duplicateName');
        expect(duplicateName, 'premise: the catalogue has assets.modal.duplicateName').not.toBe('assets.modal.duplicateName');
        expect(screen.getByTestId('asset-modal-form-error').textContent?.trim(), "trySave's reading of a 409, kept: the error is thrown on, as before").toBe(duplicateName);
        expect(consoleError.mock.calls.flat(), 'the very error reached trySave').toContain(failure);
        expect(mocks.toasts.error, 'inline, as today: no toast').not.toHaveBeenCalled();
        expectRemovalStopped(view);
        assertTraffic();
    });

    it('guard — a 500 after the dialog: as the confirmations do, the generic error toast and the very error logged; the next save asks again', async () => {
        const failure = removalServerError();
        const view = await saveWithoutProvider((expectedArgs) => planRejection('failed removal', routes.remove, expectedArgs, failure));

        expect(mocks.toasts.error, "the confirmation's own generic sentence").toHaveBeenCalledWith(get(_)('common.errorOccurred'));
        expect(consoleError, "the confirmation's catch still receives the very error").toHaveBeenCalledWith(expect.any(String), failure);
        expect(mocks.toasts.error).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('asset-modal-form-error'), 'no banner: the module did not word it').toBeNull();
        expectRemovalStopped(view);

        // The first pass sent its PATCH and its removal: the question of the next one is judged from a clean record of it.
        mocks.api.patch_assets_bulk_api_v1_assets_patch.mockClear();
        mocks.api.remove_providers_bulk_api_v1_assets_provider_delete.mockClear();
        await askRemoval(removalDryRun(), 'removal dry run, asked again');
        await fireEvent.click(within(impactDialog('remove')).getByTestId('confirm-modal-cancel'));
        await flushUi();
        assertTraffic();
    });
});

// ---------------------------------------------------------------------------
// X5-1 — the change of provider or parameters: the dry run, then one dialog.
//
// The Atlas asset of `editFixture` (an online provider, not a parametric one:
// the dialog follows the server's answer, not the kind the modal knows). The
// parameters change («regenerate»), or the provider is swapped («switch»);
// the save asks `POST /assets/provider/impact` first, with the assignment alone,
// and a loss opens the dialog of its kind. Confirm: PATCH, assignment, price
// sync. Cancel: nothing more is sent. No loss, a blocking split or a failed dry
// run: no dialog, a plain save. A new asset and an unchanged provider ask nothing.
// ---------------------------------------------------------------------------

/** The assignment the Atlas save sends when only the note changes. */
function atlasAssignment(note: string): AssignmentItem[] {
    return [{asset_id: ATLAS_ASSET_ID, provider_code: 'lifecycle_atlas', identifier: 'SYN-ATLAS', identifier_type: 'TICKER', provider_params: {note}}];
}

/** The assignment the Atlas save sends once the provider is swapped for the Beacon one (the test types these values). */
function beaconAssignment(): AssignmentItem[] {
    return [{asset_id: ATLAS_ASSET_ID, provider_code: 'lifecycle_beacon', identifier: 'US0000000001', identifier_type: 'ISIN', provider_params: {note: 'beacon note'}}];
}

function assignAccepted(): AssignmentResponse {
    return {results: [{asset_id: ATLAS_ASSET_ID, success: true, message: 'Synthetic assignment accepted'}], success_count: 1, errors: []};
}

/** The day the sync after a provider change ends on: the clock is pinned, so the oracle is not the product's own expression. */
const SYNC_DAY = '2026-06-10';

function atlasSync(): unknown[] {
    return [[{asset_id: ATLAS_ASSET_ID, date_range: {start: 'resume', end: SYNC_DAY}}]];
}

/** Change the note of the stored Atlas provider through the real field. Ends on a changed, untested provider. */
async function changeAtlasNote(note = 'changed note') {
    await input('param-note', note);
    expectStatus('not_tested');
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
}

/** Swap the Atlas provider for the Beacon one through the real fields. Ends on a changed, untested provider. */
async function swapAtlasForBeacon() {
    await fireEvent.click(screen.getByTestId('provider-code-select-button'));
    await fireEvent.click(screen.getByTestId('provider-option-lifecycle_beacon'));
    await flushUi();
    expect(screen.queryByTestId('provider-option-lifecycle_beacon'), 'the list closed on the choice').toBeNull();
    await input('provider-identifier', 'US0000000001');
    await input('param-note', 'beacon note');
    await fireEvent.click(screen.getByTestId('provider-id-type-select-button'));
    await fireEvent.click(screen.getByTestId('provider-id-type-option-ISIN'));
    await flushUi();
    expect(screen.getByTestId('provider-id-type-select-button')).toHaveAttribute('aria-expanded', 'false');
    expectStatus('not_tested');
    expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
}

/** Confirm the open dialog of `kind` and let the re-entered save reach its first request. */
async function confirmImpact(kind: DialogKind) {
    await fireEvent.click(within(impactDialog(kind)).getByTestId('confirm-modal-confirm'));
    await referenceReady; // The confirmation re-invokes saveEdit, which awaits the ready provider cache again.
    await flushUi();
    expect(screen.queryByTestId(DIALOG_IDS[kind])).toBeNull();
}

/** The saved edit, as the user sees it: the modal closed, `onupdated` once, one success toast, nothing else. */
function expectUpdated(view: Awaited<ReturnType<typeof renderEdit>>) {
    expect(screen.queryByTestId('asset-modal')).toBeNull();
    expect(view.onupdated).toHaveBeenCalledTimes(1);
    expect(view.onclose).not.toHaveBeenCalled();
    expect(view.oncreated).not.toHaveBeenCalled();
    expect(mocks.toasts.success).toHaveBeenCalledTimes(1);
    expect(mocks.toasts.error).not.toHaveBeenCalled();
    expect(mocks.toasts.warning).not.toHaveBeenCalled();
}

describe('AssetModal: a provider change asks the dry run, then one dialog by kind (X5-1)', () => {
    beforeEach(() => {
        // The sync after a provider change ends today: pin the clock (Date only) so that its day is an oracle.
        vi.useFakeTimers({toFake: ['Date']});
        vi.setSystemTime(new Date(Date.UTC(2026, 5, 10, 12, 0, 0)));
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('new parameters: the dry run first and alone, then the regenerate dialog by the answer’s figures; confirm → PATCH → assignment → sync, saved', async () => {
        const view = await renderEdit();
        await changeAtlasNote();
        const impact = planImpact('regenerate dry run', {assignments: atlasAssignment('changed note'), removals: []}, impactResult(ATLAS_ASSET_ID));
        await saveUntestedProvider();
        impact.assertUnchanged();
        expect(mocks.api.patch_assets_bulk_api_v1_assets_patch, 'the dry run goes first').not.toHaveBeenCalled();
        await answerDryRun(impact);
        expectImpactDialog('regenerate');

        const patch = plan('regenerate PATCH', routes.patch, [atlasPatch()], atlasPatchAccepted());
        const assignment = plan('regenerate assignment', routes.assign, [atlasAssignment('changed note')], assignAccepted());
        const sync = plan('regenerate sync', routes.sync, atlasSync(), {results: [], success_count: 0});
        await confirmImpact('regenerate');
        patch.assertUnchanged();
        await patch.finish();
        assignment.assertUnchanged();
        await assignment.finish();
        sync.assertUnchanged();
        await sync.finish();

        expectUpdated(view);
        expect(mocks.api.market_data_summary_api_v1_assets__asset_id__market_data_summary_get, 'the market-data summary is no longer read').not.toHaveBeenCalled();
        assertTraffic();
    });

    it('another provider: the dry run names the swap, the switch dialog says the provider left and the one that comes; confirm → PATCH → assignment → sync', async () => {
        const view = await renderEdit();
        await swapAtlasForBeacon();
        const impact = planImpact('switch dry run', {assignments: beaconAssignment(), removals: []}, impactResult(ATLAS_ASSET_ID, {reason: 'provider_changed'}));
        await saveUntestedProvider();
        impact.assertUnchanged();
        await answerDryRun(impact);
        // The provider names come from the catalogue lookup the modal already has (here, the code itself).
        expectImpactDialog('switch', [...IMPACT_FIGURES, 'lifecycle_atlas', 'lifecycle_beacon']);

        const patch = plan('switch PATCH', routes.patch, [atlasPatch()], atlasPatchAccepted());
        const assignment = plan('switch assignment', routes.assign, [beaconAssignment()], assignAccepted());
        const sync = plan('switch sync', routes.sync, atlasSync(), {results: [], success_count: 0});
        await confirmImpact('switch');
        await patch.finish();
        await assignment.finish();
        await sync.finish();

        expectUpdated(view);
        expect(mocks.api.market_data_summary_api_v1_assets__asset_id__market_data_summary_get, 'the market-data summary is no longer read').not.toHaveBeenCalled();
        assertTraffic();
    });

    it('cancel: the dialog closes, nothing is sent after the dry run, the draft stays, and the next save asks again', async () => {
        const view = await renderEdit();
        await changeAtlasNote();
        const first = planImpact('cancelled dry run', {assignments: atlasAssignment('changed note'), removals: []}, impactResult(ATLAS_ASSET_ID));
        await saveUntestedProvider();
        first.assertUnchanged();
        await answerDryRun(first);
        expectImpactDialog('regenerate');
        await fireEvent.click(within(impactDialog('regenerate')).getByTestId('confirm-modal-cancel'));
        await flushUi();

        expect(screen.queryByTestId(DIALOG_IDS.regenerate)).toBeNull();
        expect(screen.getByTestId('asset-modal')).toBeVisible();
        expect(screen.getByTestId('param-note')).toHaveValue('changed note');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
        expect(mocks.api.patch_assets_bulk_api_v1_assets_patch).not.toHaveBeenCalled();
        expect(mocks.api.assign_providers_bulk_api_v1_assets_provider_post).not.toHaveBeenCalled();
        expect(view.onupdated).not.toHaveBeenCalled();

        // pendingSaveAssetId was cleared: a second save asks the dry run again instead of sending.
        const again = planImpact('asked again', {assignments: atlasAssignment('changed note'), removals: []}, impactResult(ATLAS_ASSET_ID));
        await saveUntestedProvider();
        again.assertUnchanged();
        await answerDryRun(again);
        expectImpactDialog('regenerate');
        await fireEvent.click(within(impactDialog('regenerate')).getByTestId('confirm-modal-cancel'));
        await flushUi();
        expect(mocks.api.patch_assets_bulk_api_v1_assets_patch).not.toHaveBeenCalled();
        assertTraffic();
    });

    it.each<[string, ImpactResult | ((body: {assignments: AssignmentItem[]; removals: number[]}) => PlannedCall)]>([
        ['reason none (a change between market providers keeps the history)', impactResult(ATLAS_ASSET_ID, {reason: 'none', prices_deleted: 0, events_deleted: 0, transactions_unlinked: 0})],
        ['a reason, but nothing to delete', impactResult(ATLAS_ASSET_ID, {prices_deleted: 0, events_deleted: 0, transactions_unlinked: 0})],
        ['a dry run that failed (the server judges the real call)', (body) => planRejection('failed dry run', routes.impact, [body], apiError(500, 'Synthetic failure of the dry run'))],
    ])('%s: no dialog, the save goes on as a plain save — PATCH, assignment, sync', async (_label, dryRun) => {
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const view = await renderEdit();
        await changeAtlasNote();
        const body = {assignments: atlasAssignment('changed note'), removals: []};
        const impact = typeof dryRun === 'function' ? dryRun(body) : planImpact('plain dry run', body, dryRun);
        const patch = plan('plain PATCH', routes.patch, [atlasPatch()], atlasPatchAccepted());
        const assignment = plan('plain assignment', routes.assign, [atlasAssignment('changed note')], assignAccepted());
        const sync = plan('plain sync', routes.sync, atlasSync(), {results: [], success_count: 0});
        await saveUntestedProvider();
        impact.assertUnchanged();
        await answerDryRun(impact);
        expectNoImpactDialog();
        await patch.finish();
        await assignment.finish();
        await sync.finish();

        expectUpdated(view);
        if (typeof dryRun === 'function') expect(warn, 'the failure is warned, never thrown').toHaveBeenCalled();
        assertTraffic();
    });

    it('an unchanged provider asks no dry run: a rename saves with the PATCH and the unchanged assignment, no dialog, no sync', async () => {
        const view = await renderEdit();
        await input('asset-modal-display-name', 'Renamed Atlas security');
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true');
        const patch = plan('rename PATCH', routes.patch, [[{...atlasPatch()[0], display_name: 'Renamed Atlas security'}]], atlasPatchAccepted());
        const assignment = plan('unchanged assignment', routes.assign, [atlasAssignment('owned note')], assignAccepted());
        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await referenceReady;
        await flushUi();
        expectNoImpactDialog();
        await patch.finish();
        await assignment.finish();

        expectUpdated(view);
        expect(mocks.api.provider_change_impact_api_v1_assets_provider_impact_post, 'no dry run when the provider did not change').not.toHaveBeenCalled();
        expect(mocks.api.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
        assertTraffic();
    });
});

// ---------------------------------------------------------------------------
// X-R66 — «Ask provider» refused for too many probes.
//
// The probe endpoint allows LIBREFOLIO_PROBE_RATE_LIMIT probes a minute per
// user. Past it, it answers 429, `detail.error_code` = PROBE_RATE_LIMITED with
// `retry_after` (whole seconds) and the server's English, and the same seconds
// in `Retry-After`. «Ask provider» is a probe of ['metadata']
// (fetchAndCompareMetadata), and today any failure of it is the generic toast
// «an error occurred»: the user is told neither that the probes are paused nor
// until when. The cure: the error toast is `probeRateLimitMessage(e, $t)` — the
// catalogue's PROBE_RATE_LIMITED, «until HH:MM» in local time — and, for any
// other failure, «an error occurred» as today.
//
// The clock is pinned from the click (Date only), so the moment the pause ends
// is the same for the modal and for the expectation; the sentence is read
// through the catalogue (`$_`), never as a literal.
//
// Red before the cure: the toast is «an error occurred». The guards are green
// before and after it: a failure that is not the probe's refusal keeps it.
// ---------------------------------------------------------------------------

/** «Now» when the refusal lands: 10 June 2026, 14:30:20 local time — a month with no daylight-saving change. */
const RATE_LIMIT_NOW = new Date(2026, 5, 10, 14, 30, 20);
/** The refusal's wait, in whole seconds as the server counts them: the pause ends at 14:31:02, written 14:32. */
const RATE_LIMIT_WAIT = 42;
const PROBE_RATE_LIMITED_KEY = 'providerErrors.PROBE_RATE_LIMITED';

/** The probe's X-R66 refusal as the generated client rejects with it: 429, the structured detail with the server's English, and `Retry-After` with the same seconds. */
function probeRateLimited() {
    const refusal = apiError(429, {error_code: 'PROBE_RATE_LIMITED', retry_after: RATE_LIMIT_WAIT, message: 'Too many provider probes: try again later'});
    return Object.assign(refusal, {response: {...refusal.response, headers: {'retry-after': String(RATE_LIMIT_WAIT)}}});
}

/** A 429 the probe's limiter did not send: another code, its own English. */
function otherTooManyRequests() {
    return apiError(429, {error_code: 'SYNTHETIC_OTHER_LIMIT', message: 'Synthetic limit of another kind', params: {}});
}

/**
 * A manual «Ask provider» on the Atlas asset of `editFixture`, its metadata probe refused with `failure`, the clock
 * pinned at RATE_LIMIT_NOW from the click. Ends with that failure handled — the form free again, nothing to compare —
 * and every request answered.
 */
async function askProviderRefused(failure: unknown) {
    await renderEdit();
    const metadata = planRejection('refused Ask provider', routes.metadata, [probeRequest(['metadata'])], failure);
    vi.useFakeTimers({toFake: ['Date']});
    vi.setSystemTime(RATE_LIMIT_NOW);
    expect(screen.getByTestId('asset-modal-ask-provider')).toBeEnabled();
    await fireEvent.click(screen.getByTestId('asset-modal-ask-provider'));
    expectBusy(true);
    await metadata.finish();
    expectBusy(false);
    expect(screen.getByTestId('asset-modal-ask-provider'), 'free again, for a later try').toBeEnabled();
    expect(screen.queryByTestId('comparison-modal'), 'nothing to compare').toBeNull();
}

describe('AssetModal: «Ask provider» refused for too many probes (X-R66)', () => {
    let consoleError: MockInstance<typeof console.error>;

    beforeEach(() => {
        // fetchAndCompareMetadata logs the failure it catches: the guards read that log, the other case only silences it.
        consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('the error toast is the catalogue’s PROBE_RATE_LIMITED, with the time the pause ends — not «an error occurred»', async () => {
        await askProviderRefused(probeRateLimited());

        expect(resumesToday(RATE_LIMIT_WAIT, RATE_LIMIT_NOW), 'premise: the pause ends today').toBe(true);
        const time = formatResumeTime(RATE_LIMIT_WAIT, RATE_LIMIT_NOW);
        const sentence = get(_)(PROBE_RATE_LIMITED_KEY, {values: {time}});
        expect(mocks.toasts.error, 'one error toast').toHaveBeenCalledTimes(1);
        const [shown] = mocks.toasts.error.mock.calls[0];
        expect(shown, 'not the generic «an error occurred»: the probes are paused, and the toast says until when').not.toBe(get(_)('common.errorOccurred'));
        expect(shown, 'the catalogue’s PROBE_RATE_LIMITED, with the time the pause ends').toBe(sentence);
        expect(shown, 'the time the pause ends, rounded up to the minute').toContain(time);
        expect(get(_)(PROBE_RATE_LIMITED_KEY), `premise: the catalogue has ${PROBE_RATE_LIMITED_KEY}`).not.toBe(PROBE_RATE_LIMITED_KEY);
        expect(mocks.toasts.success).not.toHaveBeenCalled();
        expect(mocks.toasts.info).not.toHaveBeenCalled();
        expect(mocks.toasts.warning).not.toHaveBeenCalled();
        assertTraffic();
    });

    it.each<[string, () => unknown]>([
        ['a 429 the probe’s limiter did not send, another code', otherTooManyRequests],
        ['a request that got no answer', () => new Error('Network Error')],
    ])('guard — %s: as today, the generic «an error occurred», the very error logged', async (_label, failure) => {
        const error = failure();
        await askProviderRefused(error);

        const generic = get(_)('common.errorOccurred');
        expect(generic, 'premise: the catalogue has common.errorOccurred').not.toBe('common.errorOccurred');
        expect(mocks.toasts.error, 'one error toast').toHaveBeenCalledTimes(1);
        expect(mocks.toasts.error, 'the generic sentence, as today').toHaveBeenCalledWith(generic);
        expect(consoleError, 'the catch still receives the very error').toHaveBeenCalledWith(expect.any(String), error);
        expect(mocks.toasts.success).not.toHaveBeenCalled();
        expect(mocks.toasts.info).not.toHaveBeenCalled();
        assertTraffic();
    });
});
