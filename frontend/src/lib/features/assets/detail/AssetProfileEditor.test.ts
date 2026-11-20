// @vitest-environment jsdom
/**
 * AssetProfileEditor (plan 68, E9b2): «Modifica i dati» of the «Profilo» tab opens the profile window in `save` mode over
 * the asset page.
 *
 * Pinned:
 * - closed, it reads nothing and mounts nothing;
 * - opened, it reads the catalogue, the profile of today («Adesso») and the enrichers' names, then mounts the window in
 *   `save` mode with the asset, its name, the catalogue, «Adesso» and the names (RN-25b: `sourceNames` reaches the
 *   window);
 * - «Salva Tutto» done: the profile memory of the asset is forgotten, the window closes, the page is told (it reads the
 *   tab again); «Annulla» closes and tells nothing.
 *
 * How it is tested: the API a spy per method; the profile window stood in by a recorder of its props (its own test is
 * `ProfileEditModal.test.ts`).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

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
vi.mock('$lib/features/assets/profile/ProfileEditModal.svelte', () => ({default: profileWindow.ProfileEditModalStandIn}));

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
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()}}));

import {render, screen, setupI18n, waitFor} from '$test/component';
import {zodiosApi} from '$lib/api';
import {clearProfileMemory} from '$lib/features/assets/profile/profileStore';
import AssetProfileEditor from './AssetProfileEditor.svelte';

const api = (name: string) => vi.mocked((zodiosApi as unknown as Record<string, ReturnType<typeof vi.fn>>)[name]);
const queryFn = () => api('query_profile_api_v1_assets_profile_query_post');
const lastWindow = () => profileWindow.mounts.at(-1) as Record<string, unknown> & {onsaved: (pending: Record<string, unknown>) => void; oncancel: () => void};

const CATALOGUE = [{key: 'ter', shape: 'percentage', sign: 'non_negative', unit: null, groups: ['key_figures'], key_figure: true, charted: true, volatile: false, choices: [], map_keys: null, topic: 'costs'}];
const TODAY = {as_of: '2026-11-18T10:00:00Z', items: [{asset_id: 9, voices: {ter: [{date: '2026-11-18', through: '2026-11-18', value: '0.0022', source: 'justetf', update_id: 3, opened_on: '2026-11-08', source_date: null}]}, changes: null}]};
const ENRICHERS = {enrichers: [{code: 'justetf', name: 'justETF'}], default_order: {}};

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    clearProfileMemory();
    profileWindow.mounts.length = 0;
    api('profile_catalogue_api_v1_assets_profile_catalogue_get').mockResolvedValue({voices: CATALOGUE});
    queryFn().mockResolvedValue(TODAY);
    api('list_enrichers_api_v1_assets_enrichers_get').mockResolvedValue(ENRICHERS);
});

describe('AssetProfileEditor', () => {
    it('reads nothing and mounts nothing while closed', async () => {
        render(AssetProfileEditor, {open: false, assetId: 9, assetName: 'Vanguard FTSE All-World'});
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(queryFn()).not.toHaveBeenCalled();
        expect(screen.queryByTestId('stand-in-profile-window')).toBeNull();
    });

    it('opens the window in save mode with the catalogue, «Adesso» and the enrichers’ names', async () => {
        render(AssetProfileEditor, {open: true, assetId: 9, assetName: 'Vanguard FTSE All-World'});
        await waitFor(() => expect(profileWindow.mounts.length).toBeGreaterThan(0));
        expect(lastWindow().mode).toBe('save');
        expect(lastWindow().assetId).toBe(9);
        expect(lastWindow().assetName).toBe('Vanguard FTSE All-World');
        expect(lastWindow().catalogue).toEqual(CATALOGUE);
        expect(lastWindow().current).toEqual({ter: {value: '0.0022', source: 'justetf'}});
        expect(lastWindow().sourceNames).toEqual({justetf: 'justETF'});
    });

    it('after «Salva Tutto» forgets the asset’s profile, closes and tells the page; «Annulla» tells nothing', async () => {
        const onsaved = vi.fn();
        const view = render(AssetProfileEditor, {open: true, assetId: 9, assetName: 'Vanguard FTSE All-World', onsaved});
        await waitFor(() => expect(profileWindow.mounts.length).toBeGreaterThan(0));
        expect(queryFn()).toHaveBeenCalledTimes(1);

        lastWindow().onsaved({ter: {key: 'ter', kind: 'value', value: '0.0019', origin: 'new'}});
        await waitFor(() => expect(onsaved).toHaveBeenCalledOnce());

        // Closed and forgotten: opening again mounts a new window, on a new read of the profile of today. (The stand-in
        // leaves its element behind when unmounted, so the closing is read from the new mount, not from the DOM.)
        const mountsBefore = profileWindow.mounts.length;
        await view.rerender({open: true, assetId: 9, assetName: 'Vanguard FTSE All-World', onsaved});
        await waitFor(() => expect(queryFn()).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(profileWindow.mounts.length).toBe(mountsBefore + 1));
        lastWindow().oncancel();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(onsaved).toHaveBeenCalledOnce();
    });
});
