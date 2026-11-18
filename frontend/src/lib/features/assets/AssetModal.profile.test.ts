// @vitest-environment jsdom
/**
 * AssetModal — the profile (plan 68, E8b2): the «Dati del profilo» row, the profile window over the asset window in
 * `keep` mode, the automatic «Chiedi» at creation, and the pending changes saved with the asset.
 *
 * Pinned (plan E8, PROF §14.8):
 * - the row opens the profile window, which gets the asset, the catalogue, «Adesso» (in edit mode, the profile of
 *   today) and the pending changes; what it keeps waits in the asset window and leaves with the save (`profile`);
 * - at creation the automatic «Chiedi» starts once the enrichers are settled («Riconosci» done), never on the proposal
 *   still growing and never in edit mode; its answer fills the empty voices «dalla fonte», counted by the row;
 * - the automatic fills alone ask to discard nothing; a change the user kept does;
 * - a value the window would refuse blocks the save;
 * - a fill whose source left the list is not sent.
 *
 * How it is tested: the real asset window, real i18n; the API a spy per method; «Riconosci»'s stream faked; the
 * profile window stood in by a recorder of its props (its own test is `ProfileEditModal.test.ts`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const stream = vi.hoisted(() => ({recognizeEnrichers: vi.fn()}));
vi.mock('./enrichers/recognizeStream', () => stream);

const profileWindow = vi.hoisted(() => {
    const mounts: Array<Record<string, unknown>> = [];
    function ProfileEditModalStandIn(anchor: ChildNode, props: Record<string, unknown>): void {
        const element = document.createElement('div');
        element.setAttribute('data-testid', 'stand-in-profile-window');
        anchor.before(element);
        mounts.push(props);
    }
    return {mounts, ProfileEditModalStandIn};
});
vi.mock('./profile/ProfileEditModal.svelte', () => ({default: profileWindow.ProfileEditModalStandIn}));

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
import {mergeAssets} from '$lib/stores/reference/assetStore';
import {clearProfileMemory} from './profile/profileStore';
import AssetModal from './AssetModal.svelte';
import type {RecognizeEvent, RecognizeOutcome, RecognizeRequest} from './enrichers/recognizeStream';

type Call = {request: RecognizeRequest; onEvent: (event: RecognizeEvent) => void; finish: (outcome: RecognizeOutcome) => void};
let calls: Call[] = [];

const ISIN = 'IE00BK5BQT80';
const JUSTETF = {identifier_type: 'ISIN', identifier: ISIN};
const PREFILL = {display_name: 'Vanguard FTSE All-World', asset_type: 'ETF', currency: 'EUR', identifier_isin: ISIN};
const CATALOGUE = [
    {key: 'ter', shape: 'percentage', sign: 'non_negative', unit: null, groups: ['key_figures'], key_figure: true, charted: true, volatile: false, choices: [], map_keys: null, topic: 'costs'},
    {key: 'fund_provider', shape: 'text', sign: null, unit: null, groups: ['fund'], key_figure: false, charted: false, volatile: false, choices: [], map_keys: null, topic: 'manager'},
];
const found = (code: string) => ({event: 'enricher_result' as const, code, ...JUSTETF, status: 'found', name: `${code} name`, page_url: null, identifiers: {}, conflicts: {}, error: null});
const done = (order: string[]) => ({event: 'done' as const, found_order: order, default_order: order, identifiers: {ISIN}});

const api = (name: string) => vi.mocked((zodiosApi as unknown as Record<string, ReturnType<typeof vi.fn>>)[name]);
const createFn = () => api('create_assets_bulk_api_v1_assets_post');
const patchFn = () => api('patch_assets_bulk_api_v1_assets_patch');
const askFn = () => api('ask_profile_api_v1_assets_profile_ask_post');
const row = () => screen.getByTestId('asset-modal-profile-row');
const lastWindow = () => profileWindow.mounts.at(-1) as Record<string, unknown> & {onkeep: (pending: Record<string, unknown>) => void};
const form = () => screen.getByTestId('asset-modal-form');

async function settle(call: Call, events: RecognizeEvent[]) {
    for (const event of events) call.onEvent(event);
    call.finish({kind: 'done', done: null});
    await new Promise((resolve) => setTimeout(resolve, 0));
}

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    clearProfileMemory();
    calls = [];
    profileWindow.mounts.length = 0;
    stream.recognizeEnrichers.mockReset().mockImplementation((request: RecognizeRequest, options: {onEvent: (event: RecognizeEvent) => void}) => new Promise<RecognizeOutcome>((finish) => calls.push({request, onEvent: options.onEvent, finish})));
    api('list_assets_api_v1_assets_query_get').mockResolvedValue([]);
    api('list_providers_api_v1_assets_provider_get').mockResolvedValue([]);
    api('list_currencies_api_v1_utilities_currencies_get').mockResolvedValue({items: [], language: 'en'});
    api('list_enrichers_api_v1_assets_enrichers_get').mockResolvedValue({enrichers: [], default_order: {}});
    api('profile_catalogue_api_v1_assets_profile_catalogue_get').mockResolvedValue({voices: CATALOGUE});
    askFn().mockResolvedValue({voices: {fund_provider: {value: 'Vanguard', source: 'justetf'}}, outcomes: [{code: 'justetf', status: 'ok'}]});
    vi.stubGlobal(
        'fetch',
        vi.fn<typeof fetch>(async () => new Response(null, {status: 503})),
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe('at creation', () => {
    it('asks the settled enrichers once, fills the empty voices, and saves them with the asset', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 42}]});
        render(AssetModal, {open: true, editMode: false, prefillData: PREFILL, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(calls).toHaveLength(1));

        // The proposal grows with the first answer: the automatic «Chiedi» waits for «Riconosci» to end
        calls[0].onEvent(found('justetf'));
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(askFn()).not.toHaveBeenCalled();

        await settle(calls[0], [done(['justetf'])]);
        await waitFor(() => expect(askFn()).toHaveBeenCalledOnce());
        expect(askFn().mock.calls[0][0]).toEqual({asset_type: 'ETF', enrichers: {justetf: JUSTETF}});
        await waitFor(() => expect(row()).toHaveAttribute('data-count', '1'));
        // The automatic fills alone ask to discard nothing
        expect(form()).toHaveAttribute('data-dirty', 'false');

        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(createFn()).toHaveBeenCalled());
        const sent = (createFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0];
        expect(sent.profile).toEqual({fund_provider: {from: 'justetf', seen: 'Vanguard'}});
        // The shared asset cache gets the asset, not its enrichers nor its profile
        const cached = (vi.mocked(mergeAssets).mock.calls[0][0] as Array<Record<string, unknown>>)[0];
        expect(cached).not.toHaveProperty('profile');
        expect(cached).not.toHaveProperty('enrichers');
    });

    it('opens the profile window in keep mode, and what it keeps waits, counts as a change and leaves with the save', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 43}]});
        render(AssetModal, {open: true, editMode: false, prefillData: {...PREFILL, identifier_isin: null}, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(row()).toHaveAttribute('data-count', '0'));
        await fireEvent.click(row());
        await waitFor(() => expect(profileWindow.mounts.length).toBeGreaterThan(0));
        expect(lastWindow().mode).toBe('keep');
        expect(lastWindow().assetName).toBe(PREFILL.display_name);
        await waitFor(() => expect((lastWindow().catalogue as unknown[]).length).toBe(2));

        lastWindow().onkeep({ter: {key: 'ter', kind: 'value', value: '0.0019', origin: 'new'}});
        await waitFor(() => expect(row()).toHaveAttribute('data-count', '1'));
        expect(form()).toHaveAttribute('data-dirty', 'true');

        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(createFn()).toHaveBeenCalled());
        expect((createFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0].profile).toEqual({ter: '0.0019'});
    });

    it('cannot save with a value the window would refuse', async () => {
        render(AssetModal, {open: true, editMode: false, prefillData: {...PREFILL, identifier_isin: null}, initialNoProvider: true, oncreated: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('asset-modal-save')).toBeEnabled());
        await fireEvent.click(row());
        await waitFor(() => expect(profileWindow.mounts.length).toBeGreaterThan(0));
        await waitFor(() => expect((lastWindow().catalogue as unknown[]).length).toBe(2));
        lastWindow().onkeep({ter: {key: 'ter', kind: 'value', value: 'abc', origin: 'file'}});
        await waitFor(() => expect(screen.getByTestId('asset-modal-save')).toBeDisabled());
    });
});

describe('in edit mode', () => {
    const EDIT = {id: 7, display_name: 'Vanguard FTSE All-World', currency: 'EUR', asset_type: 'ETF', quote_base_quantity: 1, active: true, identifier_isin: ISIN, enrichers: {config: {justetf: JUSTETF}, state: {}}};
    const TODAY = {as_of: '2026-11-18T10:00:00Z', items: [{asset_id: 7, voices: {ter: [{date: '2026-11-18', through: '2026-11-18', value: '0.0022', source: 'justetf', update_id: 3, opened_on: '2026-11-08', source_date: null}]}, changes: null}]};

    it('never asks by itself; the window gets «Adesso» from the profile of today; an untouched save sends no profile', async () => {
        api('query_profile_api_v1_assets_profile_query_post').mockResolvedValue(TODAY);
        patchFn().mockResolvedValue({results: [{success: true, asset_id: 7}], success_count: 1});
        render(AssetModal, {open: true, editMode: true, editData: EDIT, onupdated: vi.fn()});
        await waitFor(() => expect(row()).toBeInTheDocument());
        expect(askFn()).not.toHaveBeenCalled();
        await fireEvent.click(row());
        await waitFor(() => expect(profileWindow.mounts.length).toBeGreaterThan(0));
        await waitFor(() => expect(lastWindow().current).toEqual({ter: {value: '0.0022', source: 'justetf'}}));
        expect(lastWindow().assetId).toBe(7);

        await fireEvent.input(screen.getByTestId('asset-modal-display-name'), {target: {value: 'Vanguard FTSE All-World UCITS'}});
        await fireEvent.click(screen.getByTestId('asset-modal-save'));
        await waitFor(() => expect(patchFn()).toHaveBeenCalled());
        expect((patchFn().mock.calls[0][0] as Array<Record<string, unknown>>)[0]).not.toHaveProperty('profile');
    });
});
