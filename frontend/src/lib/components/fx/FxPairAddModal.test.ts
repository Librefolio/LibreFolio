// @vitest-environment jsdom
/**
 * Creation owns configuration; the detached sync owns its eventual feedback.
 * Drive the real modal and route picker through DOM, replacing only API/reference
 * data. Every in-flight request is released by the test, never by a clock.
 *
 * The modal takes no date range: a pair created with a real provider always syncs
 * the provider's full history (`start: 'min'`) up to today on the user's calendar,
 * whichever page opened it. Edit mode and MANUAL-only pairs never sync. "Today" is
 * frozen per test (only `Date` is faked, so testing-library's polling still runs).
 *
 * Edit mode (the pair page's provider editor) writes the pair's whole new
 * configuration in one POST that replaces its routes, `{queries: {replace: true}}`,
 * and deletes nothing first (X-R75); with no route left it posts the MANUAL route.
 * Creation's POST adds a pair and asks no replace. The intermediate pairs a chain
 * asks for are not the edited pair's to replace (X-R79): an edit with legs to
 * create posts them first, alone and without replace, then the pair alone with it.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {ChainStep, ProviderInfo} from '$lib/utils/currency/currencyGraph';

const feedback = vi.hoisted(() => ({
    notices: [] as Array<{variant: string; message: string}>,
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        create_routes_bulk_api_v1_fx_providers_routes_post: vi.fn(),
        delete_routes_bulk_api_v1_fx_providers_routes_delete: vi.fn(),
        list_routes_api_v1_fx_providers_routes_get: vi.fn(),
        sync_rates_api_v1_fx_currencies_sync_post: vi.fn(),
    },
}));
vi.mock('$lib/stores/currencyGraphStore', () => ({
    findConversionPaths: vi.fn(),
    getCachedFxProviders: vi.fn(),
}));
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn().mockResolvedValue(undefined),
    getAllCurrencies: vi.fn(),
    getCurrencyInfo: vi.fn(),
}));
vi.mock('$lib/stores/reference/fxRoutesStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/fxRoutesStore')>()),
    ensureFxRoutesLoaded: vi.fn().mockResolvedValue(undefined),
    getConfiguredPairSlugs: vi.fn(() => new Set<string>()),
    getConfiguredCurrencySet: vi.fn(() => new Set<string>()),
}));
vi.mock('$lib/stores/fxStoreRegistry', () => ({
    getRegisteredPairs: vi.fn(() => []),
    createPairSlug: (base: string, quote: string) => [base, quote].sort().join('-'),
    getFxStore: vi.fn(() => ({invalidateAll: vi.fn()})),
}));
vi.mock('$lib/utils/sync/syncToastHelpers', async (importOriginal) => {
    const original = await importOriginal<typeof import('$lib/utils/sync/syncToastHelpers')>();
    return {...original, buildFxSyncToast: vi.fn(original.buildFxSyncToast)};
});
vi.mock('$lib/stores/app/notify.svelte', async (importOriginal) => {
    const original = await importOriginal<typeof import('$lib/stores/app/notify.svelte')>();
    return {...original, notify: vi.fn(original.notify)};
});
vi.mock('$lib/stores/app/toastStore.svelte', () => {
    const show = vi.fn((variant: string, message: string) => {
        feedback.notices.push({variant, message});
        return 'owned-creation-toast';
    });
    return {
        toasts: {
            show,
            success: (message: string) => show('success', message),
            warning: (message: string) => show('warning', message),
            info: (message: string) => show('info', message),
            error: (message: string) => show('error', message),
        },
    };
});

import FxPairAddModal from './FxPairAddModal.svelte';
import {zodiosApi} from '$lib/api';
import {findConversionPaths, getCachedFxProviders} from '$lib/stores/currencyGraphStore';
import {getAllCurrencies, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {getConfiguredPairSlugs} from '$lib/stores/reference/fxRoutesStore';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
import {notify} from '$lib/stores/app/notify.svelte';
import {_} from '$lib/i18n';

const createRoutes = vi.mocked(zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post);
const deleteRoutes = vi.mocked(zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete);
const listRoutes = vi.mocked(zodiosApi.list_routes_api_v1_fx_providers_routes_get);
const syncRates = vi.mocked(zodiosApi.sync_rates_api_v1_fx_currencies_sync_post);
/** Local noon on the frozen day, so no time zone can move it across midnight. */
const FROZEN_NOW = new Date(2024, 2, 31, 12, 0, 0);
const TODAY = '2024-03-31';
/** What every creation sync asks for: the provider's whole history, up to today. */
const FULL_HISTORY = {start: 'min', end: TODAY};
const DIRECT: ChainStep[] = [{from: 'EUR', to: 'GBP', provider: 'ECB'}];
const CHAIN: ChainStep[] = [
    {from: 'EUR', to: 'USD', provider: 'ECB'},
    {from: 'USD', to: 'GBP', provider: 'FED'},
];
/** The identity the route picker publishes for each route (`data-route-key`), as FxProviderSelect builds it. */
const DIRECT_KEY = 'EUR-GBP:ECB';
const CHAIN_KEY = 'EUR-USD:ECB|USD-GBP:FED';
/** EUR-GBP with no provider: the item creation posts for a manual pair, and edit mode once every route is removed. */
const MANUAL_EUR_GBP = {base: 'EUR', quote: 'GBP', chain_steps: [{from: 'EUR', to: 'GBP', provider: 'MANUAL'}], priority: 999};
const PROVIDERS: ProviderInfo[] = [
    {code: 'ECB', name: 'Fixture ECB', base_currency: 'EUR', base_currencies: ['EUR'], target_currencies: ['GBP', 'USD']},
    {code: 'FED', name: 'Fixture FED', base_currency: 'USD', base_currencies: ['USD'], target_currencies: ['GBP']},
];
const CURRENCIES = [
    {code: 'EUR', flag_emoji: '🇪🇺'},
    {code: 'GBP', flag_emoji: '🇬🇧'},
    {code: 'USD', flag_emoji: '🇺🇸'},
    {code: 'JPY', flag_emoji: '🇯🇵'},
].map((currency) => ({...currency, name: currency.code, symbol: currency.code, country_codes: [], country_names: []}));

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return {promise, resolve, reject};
}

type SyncResponse = Awaited<ReturnType<typeof zodiosApi.sync_rates_api_v1_fx_currencies_sync_post>>;
type CreationResponse = Awaited<ReturnType<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>>;

function syncResponse(...pairs: string[]): SyncResponse {
    return {
        results: pairs.map((pair) => ({pair, status: 'ok', points_fetched: 8, points_changed: 3})),
        success_count: pairs.length,
        date_range: FULL_HISTORY,
        total_points_changed: pairs.length * 3,
    };
}

function creationResponse(items: Parameters<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>[0]): CreationResponse {
    return {
        results: items.map((item) => ({
            ...item,
            chain_steps: item.chain_steps.map((step) => ({...step})),
            success: true,
            action: 'created',
            is_chain: item.chain_steps.length > 1,
            providers_used: [...new Set(item.chain_steps.map((step) => step.provider))].sort(),
        })),
        success_count: items.length,
        error_count: 0,
    };
}

function mount(props: Partial<ComponentProps<typeof FxPairAddModal>> = {}) {
    const oncreated = vi.fn();
    const onsynced = vi.fn();
    const onclose = vi.fn();
    const view = render(FxPairAddModal, {open: true, initialBase: 'EUR', initialQuote: 'GBP', oncreated, onsynced, onclose, ...props});
    return {...view, oncreated, onsynced, onclose};
}

async function ready() {
    await waitFor(() => {
        expect(findConversionPaths).toHaveBeenCalled();
        expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
        expect(screen.queryByTestId('fx-route-loading')).toBeNull();
    });
}

async function pickRoute(kind: 'direct' | 'chain') {
    await ready();
    await fireEvent.click(screen.getByTestId('fx-route-picker-toggle'));
    const picker = screen.getByTestId('fx-route-picker');
    if (kind === 'chain') {
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-2step-ECB-FED'));
    } else {
        await fireEvent.click(within(picker).getByTestId('fx-route-direct-ECB'));
    }
}

async function save() {
    const button = screen.getByTestId('fx-add-pair-save');
    expect(button).toBeEnabled();
    await fireEvent.click(button);
}

async function closed() {
    await waitFor(() => expect(screen.queryByTestId('fx-add-pair-modal')).not.toBeInTheDocument());
}

/** The `replace` query a routes POST asked for, from its second argument; `undefined` when it asked none. */
function replaceQuery(config: unknown): unknown {
    return (config as {queries?: {replace?: unknown}} | undefined)?.queries?.replace;
}

/**
 * Every routes POST, as what it carried and whether it replaces the pair's routes (X-R75): edit mode writes the
 * whole new configuration in one POST with `{queries: {replace: true}}`, after a POST of the chain's legs that asks
 * none when it has some to create (X-R79); creation adds a pair, so its POST asks no `replace` at all (no second
 * argument, or one without it). Deep equality on `body` stays an allowlist.
 */
function posts() {
    return createRoutes.mock.calls.map(([body, config]) => ({body, replace: replaceQuery(config)}));
}

/** The route picker's selected routes, by key, in priority order. */
function selectedRouteKeys() {
    return screen.queryAllByTestId('fx-route-selected').map((row) => row.getAttribute('data-route-key'));
}

/** The picker's row of one selected route, found by its key, never by its position. */
function selectedRow(key: string): HTMLElement {
    const row = screen.queryAllByTestId('fx-route-selected').find((candidate) => candidate.getAttribute('data-route-key') === key);
    if (!row) throw new Error(`No selected route ${key}: the picker shows ${JSON.stringify(selectedRouteKeys())}`);
    return row;
}

/**
 * The provider editor on EUR-GBP, whose stored routes are `stored` (priority = position), returned once the picker
 * shows them selected: edit mode loads them with a GET and maps them onto the routes it computed, and a pick made
 * before that would be overwritten by the load.
 */
async function editStored(...stored: ChainStep[][]) {
    // An empty list would be no barrier at all: the picker shows no route before the load as well as after it.
    if (stored.length === 0) throw new Error('editStored needs at least one stored route to wait for');
    listRoutes.mockResolvedValue({
        items: stored.map((chainSteps, index) => ({
            base: 'EUR',
            quote: 'GBP',
            priority: index + 1,
            chain_steps: chainSteps,
            is_chain: chainSteps.length > 1,
            providers_used: [...new Set(chainSteps.map((step) => step.provider))].sort(),
        })),
    });
    const view = mount({editMode: true, editBase: 'EUR', editQuote: 'GBP'});
    await ready();
    const keys = stored.map((chainSteps) => chainSteps.map(({from, to, provider}) => `${from}-${to}:${provider}`).join('|'));
    await waitFor(() => expect(selectedRouteKeys()).toEqual(keys));
    return view;
}

/** Only this file's notifications, not a shared UI/global toast count. */
function onlyNotice() {
    expect(feedback.notices).toHaveLength(1);
    const [notice] = feedback.notices;
    return notice!;
}

function expectLinkedPair(message: string, slug: string) {
    const html = document.createElement('div');
    html.innerHTML = message;
    const links = within(html)
        .getAllByTestId('toast-fx-link')
        .filter((candidate) => candidate.getAttribute('href') === `/fx/${slug}`);
    expect(links).toHaveLength(1);
    const [link] = links;
    expect(link).toHaveAttribute('href', `/fx/${slug}`);
    const [base, quote] = slug.split('-');
    expect(link!.textContent).toBe(`${base} / ${quote}`);
    const baseFlag = CURRENCIES.find((currency) => currency.code === base)!.flag_emoji;
    const quoteFlag = CURRENCIES.find((currency) => currency.code === quote)!.flag_emoji;
    const plain = html.textContent!;
    expect(plain.indexOf(baseFlag)).toBeGreaterThanOrEqual(0);
    expect(plain.indexOf(baseFlag)).toBeLessThan(plain.indexOf(`${base} / ${quote}`));
    expect(plain.indexOf(quoteFlag)).toBeGreaterThan(plain.indexOf(`${base} / ${quote}`));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    // Only `Date`: testing-library's waitFor and Svelte's scheduling keep real timers.
    vi.useFakeTimers({toFake: ['Date']});
    vi.setSystemTime(FROZEN_NOW);
    feedback.notices.length = 0;
    transitionClientSession('fx-creation-component-owner');
    createRoutes.mockReset().mockImplementation(async (items) => creationResponse(items));
    deleteRoutes.mockReset().mockResolvedValue({
        results: [{success: true, deleted_count: 1, base: 'EUR', quote: 'GBP'}],
        success_count: 1,
        total_deleted: 1,
    });
    listRoutes.mockReset().mockResolvedValue({items: []});
    syncRates.mockReset().mockResolvedValue(syncResponse('EUR-GBP'));
    // Deliberate UI-only metadata: the POST must pick the three wire fields,
    // not spread whatever the route picker happens to return.
    vi.mocked(findConversionPaths).mockResolvedValue([DIRECT, CHAIN].map((route) => route.map((step) => ({...step, fixtureDisplayLabel: 'not-a-wire-field'}))));
    vi.mocked(getCachedFxProviders).mockReturnValue(PROVIDERS);
    vi.mocked(getAllCurrencies).mockReturnValue(CURRENCIES);
    vi.mocked(getCurrencyInfo).mockImplementation((code) => {
        const currency = CURRENCIES.find((item) => item.code === code);
        if (!currency) throw new Error(`Unexpected currency in owned fixture: ${code}`);
        return currency;
    });
    vi.mocked(getConfiguredPairSlugs).mockReturnValue(new Set());
});

afterEach(() => {
    vi.useRealTimers();
});

describe('FxPairAddModal — tour preview', () => {
    it('keeps the pair selector anchor explanatory while removing save and every mutation path', async () => {
        const {oncreated, onsynced, onclose} = mount({tourPreview: true});

        expect(await screen.findByTestId('fx-tour-pair-selectors')).toBeVisible();
        await waitFor(() => expect(findConversionPaths).toHaveBeenCalled());
        expect(screen.queryByTestId('fx-add-pair-save')).toBeNull();
        expect(createRoutes).not.toHaveBeenCalled();
        expect(deleteRoutes).not.toHaveBeenCalled();
        expect(syncRates).not.toHaveBeenCalled();
        expect(oncreated).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(onclose).not.toHaveBeenCalled();
        expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
    });
});

describe('FxPairAddModal — configuration before background sync', () => {
    it('keeps creation pending until the POST commits and ignores a second save activation', async () => {
        const posted = deferred<Awaited<ReturnType<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>>>();
        const pending = deferred<SyncResponse>();
        createRoutes.mockReturnValue(posted.promise);
        syncRates.mockReturnValue(pending.promise);
        const {oncreated, onsynced} = mount();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            const button = screen.getByTestId('fx-add-pair-save');
            expect(button).toBeDisabled();
            await fireEvent.click(button);
            expect(oncreated).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
            expect(feedback.notices).toEqual([]);

            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            await closed();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]]);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP'], ...FULL_HISTORY}]);
            expect(oncreated).toHaveBeenCalledTimes(1);
            pending.resolve(syncResponse('EUR-GBP'));
            await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
            expect(oncreated).toHaveBeenCalledTimes(1);
        } finally {
            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            pending.resolve(syncResponse('EUR-GBP'));
            await Promise.all([posted.promise, pending.promise]);
        }
    });

    it.each(['direct', 'chain'] as const)('closes after %s creation, before one sync resolves, and reports creation only once', async (kind) => {
        const pending = deferred<SyncResponse>();
        syncRates.mockReturnValue(pending.promise);
        const {oncreated, onsynced, onclose} = mount();
        try {
            await pickRoute(kind);
            if (kind === 'chain') {
                await fireEvent.click(screen.getByTestId('fx-add-pair-intermediates'));
                expect(screen.getByTestId('fx-add-pair-intermediates')).toBeChecked();
            }
            await save();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            await closed();

            const expectedPairs = kind === 'chain' ? ['EUR-GBP', 'EUR-USD', 'GBP-USD'] : ['EUR-GBP'];
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: expectedPairs, ...FULL_HISTORY}]);
            expect(createRoutes).toHaveBeenCalledTimes(1);
            // Deep equality is an allowlist: presentation-only ChainStep data,
            // dates, session IDs and callback options cannot leak into the POST.
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
                kind === 'chain'
                    ? [
                          {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 1},
                          {base: 'EUR', quote: 'USD', chain_steps: [CHAIN[0]], priority: 1},
                          {base: 'GBP', quote: 'USD', chain_steps: [CHAIN[1]], priority: 1},
                      ]
                    : [{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}],
            ]);
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(oncreated).toHaveBeenCalledWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: true, autoSyncStarted: true});
            expect(onclose).toHaveBeenCalledTimes(1);
            expect(onsynced).not.toHaveBeenCalled();
            expect(feedback.notices).toEqual([]);

            // Reverse response order deliberately: the primary pair is not row 0.
            pending.resolve(syncResponse(...[...expectedPairs].reverse()));
            await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(syncRates).toHaveBeenCalledTimes(1);
            expect(onlyNotice().variant).toBe('success');
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
            expect(buildFxSyncToast).toHaveBeenCalledWith(expect.objectContaining({pair: 'EUR-GBP', status: 'ok'}), 'EUR-GBP', expect.any(Function), undefined, expect.any(Function), {outerFlags: true, linkToDetail: true});
        } finally {
            pending.resolve(syncResponse('EUR-GBP', 'EUR-USD', 'GBP-USD'));
            await pending.promise;
        }
    });

    it('does not re-create or sync existing intermediates', async () => {
        vi.mocked(getConfiguredPairSlugs).mockReturnValue(new Set(['EUR-USD']));
        const {onsynced} = mount();
        await pickRoute('chain');
        await fireEvent.click(screen.getByTestId('fx-add-pair-intermediates'));
        syncRates.mockResolvedValue(syncResponse('GBP-USD', 'EUR-GBP'));
        await save();
        await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
        expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
            [
                {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 1},
                {base: 'GBP', quote: 'USD', chain_steps: [CHAIN[1]], priority: 1},
            ],
        ]);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP', 'GBP-USD'], ...FULL_HISTORY}]);
    });

    it('a creation with a real provider always syncs its full history — no date range is needed or taken', async () => {
        const {oncreated, onsynced} = mount();
        await pickRoute('direct');
        await save();
        await closed();
        await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP'], ...FULL_HISTORY}]);
        expect(oncreated).toHaveBeenCalledExactlyOnceWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: true, autoSyncStarted: true});
        await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
        expect(onsynced).toHaveBeenCalledWith(expect.objectContaining({slug: 'EUR-GBP', pairs: ['EUR-GBP'], ...FULL_HISTORY, outcome: 'ok'}));
        expect(onlyNotice().variant).toBe('success');
        expectLinkedPair(onlyNotice().message, 'EUR-GBP');
    });

    it('shows one linked creation toast without sync for a MANUAL-only pair', async () => {
        const {oncreated, onsynced} = mount();
        await ready();
        await save();
        await closed();
        expect(oncreated).toHaveBeenCalledTimes(1);
        expect(oncreated).toHaveBeenCalledWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: false, autoSyncStarted: false});
        expect(syncRates).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(buildFxSyncToast).not.toHaveBeenCalled();
        expect(onlyNotice().variant).toBe('success');
        expectLinkedPair(onlyNotice().message, 'EUR-GBP');
        expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: [{from: 'EUR', to: 'GBP', provider: 'MANUAL'}], priority: 999}]]);
    });

    it('editing a provider does not start creation-time sync or creation feedback', async () => {
        const {oncreated, onsynced} = mount({editMode: true, editBase: 'EUR', editQuote: 'GBP'});
        await pickRoute('direct');
        await save();
        await closed();
        // X-R75: the edit is one POST that replaces the pair's routes; nothing is deleted before it.
        expect(deleteRoutes).not.toHaveBeenCalled();
        expect(posts()).toEqual([{body: [{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}], replace: true}]);
        expect(oncreated).toHaveBeenCalledTimes(1);
        expect(syncRates).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(feedback.notices).toEqual([]);
    });

    it.each([409, 500])('keeps the owned draft after configuration HTTP %s and never starts sync', async (status) => {
        createRoutes.mockRejectedValue({response: {status, data: {detail: 'owned-configuration-rejected'}}});
        const {oncreated, onsynced, onclose} = mount();
        await pickRoute('direct');
        await save();
        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeVisible());
        expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
        expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
        expect(screen.getByTestId('fx-route-selected')).toHaveAttribute('data-route-key', 'EUR-GBP:ECB');
        expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]]);
        expect(syncRates).not.toHaveBeenCalled();
        expect(oncreated).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(onclose).not.toHaveBeenCalled();
        expect(feedback.notices).toEqual([]);
    });

    it('an old sync may finish after reopening without changing the new pair or callbacks', async () => {
        const pending = deferred<SyncResponse>();
        syncRates.mockReturnValue(pending.promise);
        const {rerender, oncreated, onsynced} = mount();
        const newSynced = vi.fn();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            await closed();
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            await rerender({open: true, initialBase: 'JPY', initialQuote: 'USD', onsynced: newSynced});
            await ready();
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();

            pending.resolve(syncResponse('EUR-GBP'));
            await waitFor(() => expect(feedback.notices).toHaveLength(1));
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
            expect(newSynced).not.toHaveBeenCalled();
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(onsynced).toHaveBeenCalledTimes(1);

            await save();
            await closed();
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}], [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}]]);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP'], ...FULL_HISTORY}]);
        } finally {
            pending.resolve(syncResponse('EUR-GBP'));
            await pending.promise;
        }
    });

    it('unmounting just the modal does not cancel sync or the still-live host completion', async () => {
        const pending = deferred<SyncResponse>();
        syncRates.mockReturnValue(pending.promise);
        const {unmount, oncreated, onsynced} = mount();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            await closed();
            unmount();
            expect(onsynced).not.toHaveBeenCalled();
            pending.resolve(syncResponse('EUR-GBP'));
            await waitFor(() => expect(feedback.notices).toHaveLength(1));
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(onsynced).toHaveBeenCalledTimes(1);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP'], ...FULL_HISTORY}]);
            expect(onlyNotice().variant).toBe('success');
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
        } finally {
            pending.resolve(syncResponse('EUR-GBP'));
            await pending.promise;
        }
    });

    it('a changed account cannot close or notify a newly opened draft when the old POST completes', async () => {
        const posted = deferred<Awaited<ReturnType<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>>>();
        createRoutes.mockReturnValue(posted.promise);
        const old = mount();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            old.unmount();
            transitionClientSession('new-fx-creation-owner');
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD'});
            await ready();
            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            await posted.promise;
            // Fire a new owned action after the old response, then wait for its
            // success. This is a positive barrier for all negative assertions.
            createRoutes.mockImplementation(async (items) => creationResponse(items));
            await save();
            await closed();
            expect(fresh.oncreated).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: 'JPY-USD', autoSyncStarted: false}));
            expect(old.oncreated).not.toHaveBeenCalled();
            expect(old.onclose).not.toHaveBeenCalled();
            expect(old.onsynced).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}], [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}]]);
            expectLinkedPair(onlyNotice().message, 'JPY-USD');
        } finally {
            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            await posted.promise;
        }
    });

    it('a committed CREATE still syncs its captured chain after same-account modal replacement', async () => {
        const posted = deferred<Awaited<ReturnType<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>>>();
        const pending = deferred<SyncResponse>();
        const items = [
            {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 1},
            {base: 'EUR', quote: 'USD', chain_steps: [CHAIN[0]!], priority: 1},
            {base: 'GBP', quote: 'USD', chain_steps: [CHAIN[1]!], priority: 1},
        ];
        createRoutes.mockReturnValue(posted.promise);
        syncRates.mockReturnValue(pending.promise);
        const old = mount();
        try {
            await pickRoute('chain');
            await fireEvent.click(screen.getByTestId('fx-add-pair-intermediates'));
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            expect(syncRates).not.toHaveBeenCalled();
            old.unmount();
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD'});
            await ready();

            posted.resolve(creationResponse(items));
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([items]);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP', 'EUR-USD', 'GBP-USD'], ...FULL_HISTORY}]);
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(fresh.oncreated).not.toHaveBeenCalled();
            expect(fresh.onclose).not.toHaveBeenCalled();
            pending.resolve(syncResponse('GBP-USD', 'EUR-USD', 'EUR-GBP'));
            await waitFor(() => expect(feedback.notices).toHaveLength(1));
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
            expect(onlyNotice().variant).toBe('success');
            expect(old.onsynced).toHaveBeenCalledTimes(1);
            expect(fresh.onsynced).not.toHaveBeenCalled();

            // The replacement draft must still create its own manual pair, not
            // reuse any currency, route or callback from the old request.
            createRoutes.mockImplementation(async (body) => creationResponse(body));
            await save();
            await closed();
            expect(fresh.oncreated).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: 'JPY-USD', autoSyncStarted: false}));
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([items, [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}]]);
            expect(syncRates).toHaveBeenCalledTimes(1);
        } finally {
            posted.resolve(creationResponse(items));
            pending.resolve(syncResponse('EUR-GBP', 'EUR-USD', 'GBP-USD'));
            await Promise.all([posted.promise, pending.promise]);
        }
    });

    it.each(['create', 'edit'] as const)('reports a failed %s POST globally if the original form is already gone', async (mode) => {
        const editing = mode === 'edit';
        const pending = deferred<never>();
        createRoutes.mockReturnValue(pending.promise);
        const old = mount(editing ? {editMode: true, editBase: 'EUR', editQuote: 'GBP'} : {});
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            // X-R75: in edit mode too the pending write is the one POST; nothing was deleted before it.
            expect(deleteRoutes).not.toHaveBeenCalled();
            old.unmount();
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD'});
            await ready();
            pending.reject({response: {status: 503, data: {detail: 'owned-detached-configuration-failure'}}});

            await waitFor(() => {
                expect(notify).toHaveBeenCalledWith(
                    expect.objectContaining({
                        name: 'fx.pair.configuration-failed',
                        detail: expect.objectContaining({slug: 'EUR-GBP', editMode: editing}),
                        toast: expect.objectContaining({variant: 'error'}),
                    }),
                );
            });
            expect(onlyNotice().variant).toBe('error');
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(screen.queryByTestId('info-banner-error')).not.toBeInTheDocument();
            expect(fresh.oncreated).not.toHaveBeenCalled();
            expect(fresh.onclose).not.toHaveBeenCalled();
            expect(fresh.onsynced).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
            // The edit's POST replaces the pair's routes; the creation's adds a pair and asks no replace.
            expect(posts()).toEqual([{body: [{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}], replace: editing ? true : undefined}]);
            expect(deleteRoutes).not.toHaveBeenCalled();
        } finally {
            pending.reject(new Error('release-owned-failed-configuration'));
            await pending.promise.catch(() => undefined);
        }
    });

    it.each([false, true])('finishes a pending edit POST without adopting a new draft (account changed: %s)', async (changeAccount) => {
        const posted = deferred<CreationResponse>();
        const edited = [{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}];
        // Only the edit's POST is held; the replacement draft's own save is answered at once.
        createRoutes.mockReturnValueOnce(posted.promise);
        const old = mount({editMode: true, editBase: 'EUR', editQuote: 'GBP'});
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            // X-R75: the edit's one write is this POST, which replaces the pair's routes; nothing was deleted before it.
            expect(deleteRoutes).not.toHaveBeenCalled();
            expect(posts()).toEqual([{body: edited, replace: true}]);
            old.unmount();
            if (changeAccount) transitionClientSession('replacement-edit-account');
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD'});
            await ready();
            posted.resolve(creationResponse(edited));
            if (!changeAccount) {
                await waitFor(() => expect(notify).toHaveBeenCalledWith(expect.objectContaining({name: 'fx.pair.updated', detail: expect.objectContaining({slug: 'EUR-GBP'})})));
                expect(feedback.notices).toEqual([]);
            }
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(fresh.oncreated).not.toHaveBeenCalled();
            expect(fresh.onclose).not.toHaveBeenCalled();
            // A new owned successful save also establishes a completion barrier
            // for the negative account case: the old POST cannot finish as it.
            await save();
            await closed();
            const manual = [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}];
            expect(posts()).toEqual([
                {body: edited, replace: true},
                {body: manual, replace: undefined},
            ]);
            expect(deleteRoutes).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
            expect(old.oncreated).not.toHaveBeenCalled();
            expect(old.onclose).not.toHaveBeenCalled();
            expect(fresh.oncreated).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: 'JPY-USD', autoSyncStarted: false}));
            expectLinkedPair(onlyNotice().message, 'JPY-USD');
            if (changeAccount) {
                expect(vi.mocked(notify).mock.calls.some(([event]) => event.name === 'fx.pair.updated')).toBe(false);
            }
        } finally {
            posted.resolve(creationResponse(edited));
            await posted.promise;
        }
    });
});

/**
 * X-R75. The provider editor (the pair page's modal, `editMode`) used to DELETE the whole pair and then POST the
 * routes picked: a refused POST left the pair with no route, and with no route picked the POST was skipped, so the
 * pair was deleted outright where the user guide says it becomes manual. It now writes the pair's whole new
 * configuration in one POST with `{queries: {replace: true}}` — the backend keeps exactly the routes posted for the
 * pair, atomically — and deletes nothing; with no route picked, what it posts is the MANUAL route creation builds.
 * Errors are reported as before, on the form that is still open. Creation is unchanged: its POST asks no replace.
 */
describe('FxPairAddModal — the provider editor replaces the pair’s routes in one POST (X-R75)', () => {
    it('posts the stored route and the one added in one POST that replaces the pair, and deletes nothing', async () => {
        const {oncreated, onsynced} = await editStored(DIRECT);
        await pickRoute('chain');
        await waitFor(() => expect(selectedRouteKeys()).toEqual([DIRECT_KEY, CHAIN_KEY]));
        await save();
        await closed();
        // `replace` drops whatever is not posted: the POST must carry the stored route too, in priority order.
        expect(posts(), 'one POST, every route the pair keeps, replacing its routes').toEqual([
            {
                body: [
                    {base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1},
                    {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 2},
                ],
                replace: true,
            },
        ]);
        expect(deleteRoutes, 'nothing is deleted before the POST').not.toHaveBeenCalled();
        expect(oncreated).toHaveBeenCalledExactlyOnceWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: true, autoSyncStarted: false});
        expect(syncRates).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(feedback.notices).toEqual([]);
    });

    it('with every route removed, posts the MANUAL route in one POST that replaces the pair: the pair is kept, manual', async () => {
        const {oncreated, onsynced} = await editStored(DIRECT);
        await fireEvent.click(within(selectedRow(DIRECT_KEY)).getByTestId('fx-route-remove'));
        await waitFor(() => expect(selectedRouteKeys()).toEqual([]));
        await save();
        await closed();
        expect(posts(), 'one POST that leaves the pair its MANUAL route, replacing the route removed').toEqual([{body: [MANUAL_EUR_GBP], replace: true}]);
        expect(deleteRoutes, 'nothing is deleted: a pair without any route no longer exists').not.toHaveBeenCalled();
        expect(oncreated).toHaveBeenCalledExactlyOnceWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: false, autoSyncStarted: false});
        expect(notify).toHaveBeenCalledWith(expect.objectContaining({name: 'fx.pair.updated', detail: expect.objectContaining({slug: 'EUR-GBP', hasRealProvider: false})}));
        expect(syncRates).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(feedback.notices).toEqual([]);
    });

    it.each([503, 409])('a POST refused with HTTP %s leaves its error on the open editor, the draft as it was, and deletes nothing', async (status) => {
        const detail = status === 409 ? 'owned-edit-conflict-detail' : 'owned-edit-refused';
        createRoutes.mockRejectedValue({response: {status, data: {detail}}});
        const {oncreated, onsynced, onclose} = await editStored(DIRECT);
        await pickRoute('chain');
        await waitFor(() => expect(selectedRouteKeys()).toEqual([DIRECT_KEY, CHAIN_KEY]));
        await save();

        // The error as today: on the form, which is still open, saveable again, on the user's draft.
        const banner = await screen.findByTestId('info-banner-error');
        if (status === 409) {
            // The conflict is the one refusal the user can act on: the catalogue's sentence, never the backend's own.
            const conflict = get(_)('fx.addPair.createConflict');
            expect(conflict, 'the catalogue has a sentence for the conflict').not.toBe('fx.addPair.createConflict');
            expect(banner).toHaveTextContent(conflict);
            expect(banner).not.toHaveTextContent(detail);
        } else {
            expect(banner).toHaveTextContent(detail);
        }
        expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
        await waitFor(() => expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled());
        expect(selectedRouteKeys(), 'the draft is kept').toEqual([DIRECT_KEY, CHAIN_KEY]);

        // A refused POST changed nothing, because nothing was deleted before it.
        expect(deleteRoutes, 'nothing was deleted: the pair keeps the routes it had').not.toHaveBeenCalled();
        expect(posts()).toEqual([
            {
                body: [
                    {base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1},
                    {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 2},
                ],
                replace: true,
            },
        ]);
        expect(oncreated).not.toHaveBeenCalled();
        expect(onclose).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(syncRates).not.toHaveBeenCalled();
        const detachedReports = vi.mocked(notify).mock.calls.filter(([event]) => event.name === 'fx.pair.configuration-failed');
        expect(detachedReports, 'the open form reports the error itself, not a detached notification').toEqual([]);
        expect(feedback.notices).toEqual([]);
    });

    // Guard, green before and after the cure: creation adds a pair, it never replaces one.
    it.each(['a provider route', 'no route'] as const)('creation with %s is one POST that asks no replace', async (kind) => {
        const {oncreated, onsynced} = mount();
        if (kind === 'a provider route') await pickRoute('direct');
        else await ready();
        await save();
        await closed();
        const item = kind === 'a provider route' ? {base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1} : MANUAL_EUR_GBP;
        expect(posts()).toEqual([{body: [item], replace: undefined}]);
        expect(deleteRoutes).not.toHaveBeenCalled();
        expect(oncreated).toHaveBeenCalledTimes(1);
        // A provider creation syncs in the background: let it finish inside this test.
        if (kind === 'a provider route') await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
        else expect(syncRates).not.toHaveBeenCalled();
    });
});

/**
 * X-R79. The backend applies `replace` to every pair a request names (`create_routes_bulk`), and X-R75's one edit POST
 * also carried the chain's intermediate pairs when «Also create intermediate pairs» is ticked: a leg another tab had
 * configured meanwhile kept only the route posted for it. The editor now posts the legs it has to create first, alone
 * and as a plain upsert (no `replace`), and only once they are answered the pair alone, replacing its routes; a refused
 * POST of the legs ends the save there, with nothing replaced and the error on the open editor. The upsert still writes
 * priority 1 of such a leg (the backend upserts by pair and priority): what X-R79 keeps is the leg's other routes.
 * With no leg to create the edit stays X-R75's one replacing POST: box unticked (X-R75's first test), no chain route
 * («editing a provider does not start creation-time sync…», X-R75's MANUAL test), every leg configured already (below).
 * Creation is unchanged: one POST, the pair and its legs together, asking no replace (below).
 */
describe('FxPairAddModal — the editor posts the intermediate pairs first, without replace, then the pair alone with it (X-R79)', () => {
    /** What the replacing POST carries: EUR-GBP keeps its stored DIRECT route and gains CHAIN, in priority order. */
    const EDITED = [
        {base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1},
        {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 2},
    ];
    /** CHAIN's legs as the box creates a pair not configured yet: its one step, at priority 1, wire fields only. */
    const LEG_EUR_USD = {base: 'EUR', quote: 'USD', chain_steps: [CHAIN[0]!], priority: 1};
    const LEG_GBP_USD = {base: 'GBP', quote: 'USD', chain_steps: [CHAIN[1]!], priority: 1};
    const BOTH_LEGS = [LEG_EUR_USD, LEG_GBP_USD];

    /** The two POSTs of an edit that creates `legs`: the legs alone, a plain upsert, then the pair alone, replacing its routes. */
    function legsThenPair(legs: unknown[]) {
        return [
            {body: legs, replace: undefined},
            {body: EDITED, replace: true},
        ];
    }

    /** Tick «Also create intermediate pairs», which the modal shows once a chain route is selected. */
    async function tickIntermediates() {
        const box = await screen.findByTestId('fx-add-pair-intermediates');
        await fireEvent.click(box);
        expect(box).toBeChecked();
    }

    /** The provider editor on EUR-GBP (stored: DIRECT), with CHAIN added through the picker and the box ticked. */
    async function editAddingChainWithLegs() {
        const view = await editStored(DIRECT);
        await pickRoute('chain');
        await waitFor(() => expect(selectedRouteKeys()).toEqual([DIRECT_KEY, CHAIN_KEY]));
        await tickIntermediates();
        return view;
    }

    /**
     * A refusal reported as X-R75 reports it: on the editor, still open and saveable again on the user's draft. A 409
     * never shows the backend's own text; `conflictSentence` also asks for the catalogue's sentence in its place.
     */
    async function expectErrorOnOpenEditor(status: number, detail: string, {conflictSentence}: {conflictSentence: boolean}) {
        const banner = await screen.findByTestId('info-banner-error');
        if (status === 409) {
            expect(banner, 'a conflict never shows the backend’s own text').not.toHaveTextContent(detail);
            if (conflictSentence) {
                const conflict = get(_)('fx.addPair.createConflict');
                expect(conflict, 'the catalogue has a sentence for the conflict').not.toBe('fx.addPair.createConflict');
                expect(banner).toHaveTextContent(conflict);
            }
        } else {
            expect(banner).toHaveTextContent(detail);
        }
        expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
        await waitFor(() => expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled());
        expect(selectedRouteKeys(), 'the draft is kept').toEqual([DIRECT_KEY, CHAIN_KEY]);
    }

    /** What a refused save leaves: nothing deleted, no completion, no sync, no feedback but the editor's own banner. */
    function expectNothingFinished({oncreated, onsynced, onclose}: Pick<ReturnType<typeof mount>, 'oncreated' | 'onsynced' | 'onclose'>) {
        expect(deleteRoutes).not.toHaveBeenCalled();
        expect(oncreated).not.toHaveBeenCalled();
        expect(onclose).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(syncRates).not.toHaveBeenCalled();
        const detachedReports = vi.mocked(notify).mock.calls.filter(([event]) => event.name === 'fx.pair.configuration-failed');
        expect(detachedReports, 'the open form reports the error itself, not a detached notification').toEqual([]);
        expect(feedback.notices).toEqual([]);
    }

    it.each([
        ['both legs (EUR-USD, GBP-USD)', ['EUR-GBP'], BOTH_LEGS],
        ['the one leg not configured yet (GBP-USD)', ['EUR-GBP', 'EUR-USD'], [LEG_GBP_USD]],
    ])('posts %s first, alone and without replace, then, once answered, the pair alone, replacing its routes', async (_what, configured, legs) => {
        // The pair under edit is configured by definition, and never one of its own legs.
        vi.mocked(getConfiguredPairSlugs).mockReturnValue(new Set(configured));
        const legsPosted = deferred<CreationResponse>();
        // Only the first POST is held; the one that follows it is answered at once.
        createRoutes.mockReturnValueOnce(legsPosted.promise);
        const {oncreated, onsynced} = await editAddingChainWithLegs();
        try {
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            expect(posts(), 'first the legs alone, a plain upsert: `replace` would drop the routes another tab gave them').toEqual([{body: legs, replace: undefined}]);
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(oncreated).not.toHaveBeenCalled();

            legsPosted.resolve(creationResponse(legs));
            await closed();
            expect(posts(), 'then, once the legs are answered, the pair alone, replacing its routes').toEqual(legsThenPair(legs));
            expect(deleteRoutes).not.toHaveBeenCalled();
            expect(oncreated).toHaveBeenCalledExactlyOnceWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: true, autoSyncStarted: false});
            expect(
                vi.mocked(notify).mock.calls.filter(([event]) => event.name === 'fx.pair.updated'),
                'one save, one update',
            ).toHaveLength(1);
            expect(syncRates).not.toHaveBeenCalled();
            expect(onsynced).not.toHaveBeenCalled();
            expect(feedback.notices).toEqual([]);
        } finally {
            legsPosted.resolve(creationResponse(legs));
            await legsPosted.promise;
        }
    });

    it.each([503, 409])('a refused POST of the legs (HTTP %s) ends the save there: no replacing POST, the error on the open editor, the draft as it was', async (status) => {
        const detail = status === 409 ? 'owned-legs-conflict-detail' : 'owned-legs-refused';
        // Only the first POST is refused: a replacing POST sent after it would be answered, and close the editor.
        createRoutes.mockRejectedValueOnce({response: {status, data: {detail}}});
        const view = await editAddingChainWithLegs();
        await save();

        // The refused legs saved nothing, so the catalogue's conflict sentence holds here, as in X-R75.
        await expectErrorOnOpenEditor(status, detail, {conflictSentence: true});
        expect(screen.getByTestId('fx-add-pair-intermediates'), 'the box stays ticked: a retry asks for the legs again').toBeChecked();
        // The save is over (saveable again): what it posted is all it posts.
        expect(posts(), 'the legs alone; nothing replaced after their refusal').toEqual([{body: BOTH_LEGS, replace: undefined}]);
        expectNothingFinished(view);
    });

    it.each([503, 409])('the legs answered, a refused replacing POST of the pair (HTTP %s) leaves its error on the open editor', async (status) => {
        const detail = status === 409 ? 'owned-pair-conflict-detail' : 'owned-pair-refused';
        // The first POST (the legs) is answered, the second (the pair, replacing its routes) refused.
        createRoutes.mockImplementationOnce(async (items) => creationResponse(items));
        createRoutes.mockRejectedValueOnce({response: {status, data: {detail}}});
        const view = await editAddingChainWithLegs();
        await save();

        // The refusal comes from the second POST: wait for both; a timeout's diff shows what was posted instead.
        await waitFor(() => expect(posts()).toEqual(legsThenPair(BOTH_LEGS)));
        // A conflict's sentence is not pinned here: the catalogue's says nothing was saved, and the legs were.
        await expectErrorOnOpenEditor(status, detail, {conflictSentence: false});
        expect(posts(), 'nothing is posted after the refusal').toEqual(legsThenPair(BOTH_LEGS));
        expectNothingFinished(view);
    });

    // Guard, green before and after the cure: no leg left to create, so the edit is X-R75's one replacing POST.
    it('with the box ticked but every leg configured already, the edit stays one POST that replaces the pair alone', async () => {
        vi.mocked(getConfiguredPairSlugs).mockReturnValue(new Set(['EUR-GBP', 'EUR-USD', 'GBP-USD']));
        const {oncreated, onsynced} = await editAddingChainWithLegs();
        await save();
        await closed();
        expect(posts()).toEqual([{body: EDITED, replace: true}]);
        expect(deleteRoutes).not.toHaveBeenCalled();
        expect(oncreated).toHaveBeenCalledExactlyOnceWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: true, autoSyncStarted: false});
        expect(syncRates).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
    });

    // Guard, green before and after the cure. «closes after chain creation…» pins this body, but not its `replace`.
    it('creation with the box ticked stays one POST, the pair and its legs together, that asks no replace', async () => {
        syncRates.mockResolvedValue(syncResponse('EUR-GBP', 'EUR-USD', 'GBP-USD'));
        const {oncreated, onsynced} = mount();
        await pickRoute('chain');
        await tickIntermediates();
        await save();
        await closed();
        expect(posts()).toEqual([{body: [{base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 1}, ...BOTH_LEGS], replace: undefined}]);
        expect(deleteRoutes).not.toHaveBeenCalled();
        expect(oncreated).toHaveBeenCalledTimes(1);
        // A provider creation syncs the pair and its legs in the background: let it finish inside this test.
        await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
    });
});
