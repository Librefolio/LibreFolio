// @vitest-environment jsdom
/**
 * AssetModal — the enrichers (plan 68, E8a): the «Arricchitori» button beside «Chiedi al Provider», the line that says
 * what «Riconosci» found, the enrichers' window over the asset window, and the list saved with the asset.
 *
 * Pinned (PROF, rounds 18, 21, 28 and 40):
 * - at creation «Riconosci» starts by itself with a whole ISIN in the form (prefilled or typed), asked with the asset's
 *   type, its identifiers and its price provider; without one it asks nothing; in edit mode it never starts;
 * - the button counts the enrichers chosen; the line says found / searching / refused (`data-state`);
 * - what «Riconosci» proposes is the list until the user applies one of their own from the window; after that a new
 *   answer changes nothing;
 * - «Crea Asset» sends the list (`enrichers`, in its order); answers still in flight are dropped (no background work);
 * - an edit sends `enrichers` only when the list changed (absent means unchanged);
 * - the window gets the asset, the list, the answers and the codes still asked, and hands the list back (`onapply`);
 * - E6c: opened with `enrichersOnOpen` (the «Configura» of the «Profilo» tab), the enrichers' window is already on top;
 *   opened without it, it is not, even right after a window opened with it.
 *
 * How it is tested: the real asset window, real i18n; the API a spy per method (as `AssetModal.test.ts`); «Riconosci»'s
 * stream (`recognizeStream`) faked; the enrichers' window stood in by a recorder of its props.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const stream = vi.hoisted(() => ({recognizeEnrichers: vi.fn()}));
vi.mock('./enrichers/recognizeStream', () => stream);

const windowStandIn = vi.hoisted(() => {
    const mounts: Array<Record<string, unknown>> = [];
    function AssetEnrichersModalStandIn(anchor: ChildNode, props: Record<string, unknown>): void {
        const element = document.createElement('div');
        element.setAttribute('data-testid', 'stand-in-enrichers-window');
        anchor.before(element);
        mounts.push(props);
    }
    return {mounts, AssetEnrichersModalStandIn};
});
vi.mock('./enrichers/AssetEnrichersModal.svelte', () => ({default: windowStandIn.AssetEnrichersModalStandIn}));

vi.mock('$lib/api', async () => {
    const {schemas} = await import('$lib/api/generated');
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, schemas, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/utils/providerHelpers', () => ({
    ensureAssetProvidersCached: vi.fn(() => Promise.resolve()),
    getAssetProviderName: vi.fn((c: string) => c),
    getAssetProviderIconUrl: vi.fn(() => null),
    isParametricProvider: vi.fn(() => false),
}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()}}));
vi.mock('$lib/stores/reference/assetStore', () => ({mergeAssets: vi.fn(), invalidateAfterMutation: vi.fn()}));

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {zodiosApi} from '$lib/api';
import AssetModal from './AssetModal.svelte';
import type {RecognizeEvent, RecognizeOutcome, RecognizeRequest} from './enrichers/recognizeStream';

type Call = {request: RecognizeRequest; onEvent: (event: RecognizeEvent) => void; signal: AbortSignal; finish: (outcome: RecognizeOutcome) => void};
let calls: Call[] = [];

const ISIN = 'IE00BK5BQT80';
const JUSTETF = {identifier_type: 'ISIN', identifier: ISIN};
const YAHOO = {identifier_type: 'TICKER', identifier: 'VWCE.DE'};
const ESMA = {identifier_type: 'ISIN', identifier: ISIN};
const PREFILL = {display_name: 'Vanguard FTSE All-World', asset_type: 'ETF', currency: 'EUR', identifier_isin: ISIN};
const found = (code: string, binding: {identifier_type: string; identifier: string}) => ({event: 'enricher_result' as const, code, ...binding, status: 'found', name: `${code} name`, page_url: null, identifiers: {}, conflicts: {}, error: null});
const done = (order: string[]) => ({event: 'done' as const, found_order: order, default_order: order, identifiers: {ISIN}});

const createFn = () => vi.mocked(zodiosApi.create_assets_bulk_api_v1_assets_post as never) as ReturnType<typeof vi.fn>;
const patchFn = () => vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch as never) as ReturnType<typeof vi.fn>;
const button = () => screen.getByTestId('asset-modal-enrichers');
const banner = () => screen.queryByTestId('asset-modal-enrichers-banner');
const lastWindow = () => windowStandIn.mounts.at(-1) as Record<string, unknown> & {onapply: (config: Record<string, unknown>) => void};

async function answer(call: Call, events: RecognizeEvent[], outcome: RecognizeOutcome = {kind: 'done', done: null}) {
    for (const event of events) call.onEvent(event);
    call.finish(outcome);
    await new Promise((resolve) => setTimeout(resolve, 0));
}

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    calls = [];
    windowStandIn.mounts.length = 0;
    stream.recognizeEnrichers.mockReset().mockImplementation((request: RecognizeRequest, options: {onEvent: (event: RecognizeEvent) => void; signal: AbortSignal}) => new Promise<RecognizeOutcome>((finish) => calls.push({request, onEvent: options.onEvent, signal: options.signal, finish})));
    vi.mocked(zodiosApi.list_assets_api_v1_assets_query_get as never as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue([]);
    vi.mocked(zodiosApi.list_currencies_api_v1_utilities_currencies_get).mockResolvedValue({items: [], language: 'en'});
    vi.mocked(zodiosApi.list_enrichers_api_v1_assets_enrichers_get as never as ReturnType<typeof vi.fn>).mockResolvedValue({enrichers: [], default_order: {}});
    vi.mocked(zodiosApi.profile_catalogue_api_v1_assets_profile_catalogue_get as never as ReturnType<typeof vi.fn>).mockResolvedValue({voices: []});
    // At creation a settled list starts the automatic «Chiedi» (E8b2): an answer with nothing in it fills nothing
    vi.mocked(zodiosApi.ask_profile_api_v1_assets_profile_ask_post as never as ReturnType<typeof vi.fn>).mockResolvedValue({voices: {}, outcomes: []});
    vi.stubGlobal(
        'fetch',
        vi.fn<typeof fetch>(async () => new Response(null, {status: 503})),
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe('at creation, «Riconosci» by itself', () => {
    it('starts with a prefilled ISIN, proposes what it found, and the creation sends it in its order', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 42}]} as never);
        render(AssetModal, {open: true, editMode: false, prefillData: PREFILL, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(calls).toHaveLength(1));
        expect(calls[0].request).toEqual({asset_type: 'ETF', identifiers: {ISIN}, price_provider_code: null});
        expect(banner()).toHaveAttribute('data-state', 'running');

        await answer(calls[0], [found('esma', ESMA), found('justetf', JUSTETF), done(['justetf', 'esma'])]);
        await waitFor(() => expect(button()).toHaveAttribute('data-count', '2'));
        expect(banner()).toHaveAttribute('data-state', 'found');

        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(createFn()).toHaveBeenCalled());
        const sent = (createFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0];
        expect(Object.keys(sent.enrichers as object)).toEqual(['justetf', 'esma']);
        expect(sent.enrichers).toEqual({justetf: JUSTETF, esma: ESMA});
    });

    it('never puts in by itself one found by a ticker alone (ENR-1, R2): the creation sends the others', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 44}]} as never);
        render(AssetModal, {open: true, editMode: false, prefillData: PREFILL, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(calls).toHaveLength(1));

        await answer(calls[0], [found('yahoo_finance', YAHOO), found('justetf', JUSTETF), done(['justetf', 'yahoo_finance'])]);
        await waitFor(() => expect(banner()).toHaveAttribute('data-state', 'found'));
        expect(button()).toHaveAttribute('data-count', '1');

        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(createFn()).toHaveBeenCalled());
        const sent = (createFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0];
        expect(sent.enrichers).toEqual({justetf: JUSTETF});
    });

    it('asks nothing without an ISIN, and sends no enrichers', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 43}]} as never);
        render(AssetModal, {open: true, editMode: false, prefillData: {...PREFILL, identifier_isin: null, identifier_ticker: 'VWCE'}, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(button()).toHaveAttribute('data-count', '0'));
        expect(calls).toHaveLength(0);
        expect(banner()).toBeNull();
        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(createFn()).toHaveBeenCalled());
        expect((createFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0]).not.toHaveProperty('enrichers');
    });

    it('says a refusal for too many requests', async () => {
        render(AssetModal, {open: true, editMode: false, prefillData: PREFILL, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(calls).toHaveLength(1));
        await answer(calls[0], [], {kind: 'refused', retryAfter: 30});
        await waitFor(() => expect(banner()).toHaveAttribute('data-state', 'refused'));
    });

    it('keeps the list the user applied from the window, whatever answers later', async () => {
        render(AssetModal, {open: true, editMode: false, prefillData: PREFILL, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(calls).toHaveLength(1));
        await fireEvent.click(button());
        await waitFor(() => expect(windowStandIn.mounts.length).toBeGreaterThan(0));
        expect(lastWindow().asset).toEqual({name: PREFILL.display_name, assetType: 'ETF', identifiers: {ISIN}});
        lastWindow().onapply({yahoo_finance: YAHOO});
        await waitFor(() => expect(button()).toHaveAttribute('data-count', '1'));

        await answer(calls[0], [found('justetf', JUSTETF), found('yahoo_finance', YAHOO), done(['justetf', 'yahoo_finance'])]);
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(button()).toHaveAttribute('data-count', '1');
    });

    it('drops the answers in flight when the window closes', async () => {
        const view = render(AssetModal, {open: true, editMode: false, prefillData: PREFILL, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(calls).toHaveLength(1));
        await view.rerender({open: false, editMode: false, prefillData: PREFILL, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(calls[0].signal.aborted).toBe(true));
    });
});

describe('in edit mode', () => {
    const EDIT = {id: 7, display_name: 'Vanguard FTSE All-World', currency: 'EUR', asset_type: 'ETF', quote_base_quantity: 1, active: true, identifier_isin: ISIN, enrichers: {config: {justetf: JUSTETF}, state: {}}};

    it('never starts «Riconosci», and an untouched save sends no enrichers', async () => {
        patchFn().mockResolvedValue({results: [{success: true, asset_id: 7}], success_count: 1} as never);
        render(AssetModal, {open: true, editMode: true, editData: EDIT, onupdated: vi.fn()});
        await waitFor(() => expect(button()).toHaveAttribute('data-count', '1'));
        expect(calls).toHaveLength(0);
        await fireEvent.input(screen.getByTestId('asset-modal-display-name'), {target: {value: 'Vanguard FTSE All-World UCITS'}});
        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(patchFn()).toHaveBeenCalled());
        expect((patchFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0]).not.toHaveProperty('enrichers');
    });

    it('sends the list the user applied, and hands the window the last reads', async () => {
        patchFn().mockResolvedValue({results: [{success: true, asset_id: 7}], success_count: 1} as never);
        const state = {justetf: {last_read: '2026-11-08', outcome: 'ok'}};
        render(AssetModal, {open: true, editMode: true, editData: {...EDIT, enrichers: {config: {justetf: JUSTETF}, state}}, onupdated: vi.fn()});
        await waitFor(() => expect(button()).toHaveAttribute('data-count', '1'));
        await fireEvent.click(button());
        await waitFor(() => expect(windowStandIn.mounts.length).toBeGreaterThan(0));
        expect(lastWindow().readState).toEqual(state);
        lastWindow().onapply({yahoo_finance: YAHOO, justetf: JUSTETF});
        await waitFor(() => expect(button()).toHaveAttribute('data-count', '2'));
        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(patchFn()).toHaveBeenCalled());
        const sent = (patchFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0];
        expect(Object.keys(sent.enrichers as object)).toEqual(['yahoo_finance', 'justetf']);
    });

    it('opens with the enrichers window on top when asked (the tab\u2019s «Configura», E6c), and only then', async () => {
        const bare = {...EDIT, enrichers: {config: {}, state: {}}};
        const view = render(AssetModal, {open: true, editMode: true, editData: bare, enrichersOnOpen: true, onupdated: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('stand-in-enrichers-window')).toBeInTheDocument());
        expect(zodiosApi.list_enrichers_api_v1_assets_enrichers_get, 'the window gets its catalogue').toHaveBeenCalled();

        // The stand-in leaves its element behind: count the mounts of the window instead
        const mounted = windowStandIn.mounts.length;
        await view.rerender({open: false, editMode: true, editData: bare, enrichersOnOpen: false, onupdated: vi.fn()});
        await view.rerender({open: true, editMode: true, editData: bare, enrichersOnOpen: false, onupdated: vi.fn()});
        await waitFor(() => expect(button()).toHaveAttribute('data-count', '0'));
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(windowStandIn.mounts.length, 'opened without it, no enrichers window').toBe(mounted);
    });
});
