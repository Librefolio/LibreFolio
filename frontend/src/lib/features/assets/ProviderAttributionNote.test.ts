// @vitest-environment jsdom
/**
 * ProviderAttributionNote — component test (Vitest + jsdom), project 76, P4.
 *
 * The line a provider's terms ask to show with its prices («Powered by CoinGecko», linked to coingecko.com), drawn
 * once per such provider among the assets of a screen, and not at all when none is there. The providers are named
 * directly (`providerCodes`) or through the assets shown (`assetIds`, read from the asset store). The provider list
 * and the asset store are stubbed: the component reads them through their getters, and follows their version stores.
 *
 * Asserted on test ids, `data-provider`, the link's `href`/`target`/`rel`; the brand text is CoinGecko's own wording,
 * the same in every language, so it is compared as such.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {render, screen, waitFor} from '$test/component';
import {ensureAssetsLoaded} from '$lib/stores/reference/assetStore';

const state = vi.hoisted(() => ({
    attributions: new Map<string, {text: string; url: string}>(),
    assets: new Map<number, {provider_code?: string | null}>(),
}));
const versions = vi.hoisted(() => ({providers: null as unknown, assets: null as unknown}));

vi.mock('$lib/utils/providerHelpers', async () => {
    const {writable: w} = await import('svelte/store');
    versions.providers = w(0);
    return {
        assetProvidersVersion: versions.providers,
        ensureAssetProvidersCached: vi.fn(async () => undefined),
        getAssetProviderAttribution: vi.fn((code: string | null | undefined) => (code ? (state.attributions.get(code) ?? null) : null)),
    };
});
vi.mock('$lib/stores/reference/assetStore', async () => {
    const {writable: w} = await import('svelte/store');
    versions.assets = w(0);
    return {
        assetStoreVersion: versions.assets,
        ensureAssetsLoaded: vi.fn(async () => undefined),
        getAssetInfo: vi.fn((id: number) => state.assets.get(id) ?? null),
    };
});

import ProviderAttributionNote from './ProviderAttributionNote.svelte';

const COINGECKO = {text: 'Powered by CoinGecko', url: 'https://www.coingecko.com/'};
const bump = (store: unknown) => (store as ReturnType<typeof writable<number>>).update((v) => v + 1);

beforeEach(() => {
    vi.mocked(ensureAssetsLoaded).mockClear();
    state.attributions = new Map([['coingecko', COINGECKO]]);
    state.assets = new Map([
        [1, {provider_code: 'yfinance'}],
        [2, {provider_code: 'coingecko'}],
        [3, {provider_code: 'coingecko'}],
        [4, {provider_code: null}],
    ]);
});

describe('ProviderAttributionNote', () => {
    it('draws nothing when no provider on screen asks for a line', () => {
        render(ProviderAttributionNote, {providerCodes: ['yfinance', null], assetIds: [1, 4]});
        expect(screen.queryByTestId('provider-attribution-note')).toBeNull();
    });

    it('draws one linked line for CoinGecko, however many of its assets are on screen', () => {
        render(ProviderAttributionNote, {assetIds: [1, 2, 3]});
        const links = screen.getAllByTestId('provider-attribution-link');
        expect(links).toHaveLength(1);
        expect(links[0]).toHaveAttribute('data-provider', 'coingecko');
        expect(links[0]).toHaveAttribute('href', 'https://www.coingecko.com/');
        expect(links[0]).toHaveAttribute('target', '_blank');
        expect(links[0].getAttribute('rel')).toContain('noopener');
        expect(links[0].textContent?.trim()).toBe('Powered by CoinGecko');
    });

    it('takes a provider code directly (the asset page)', () => {
        render(ProviderAttributionNote, {providerCodes: ['coingecko']});
        expect(screen.getByTestId('provider-attribution-link')).toHaveAttribute('data-provider', 'coingecko');
    });

    it('appears once the provider list arrives after the first draw', async () => {
        state.attributions = new Map();
        render(ProviderAttributionNote, {providerCodes: ['coingecko']});
        expect(screen.queryByTestId('provider-attribution-note')).toBeNull();

        state.attributions = new Map([['coingecko', COINGECKO]]);
        bump(versions.providers);
        expect(await screen.findByTestId('provider-attribution-link')).toHaveAttribute('data-provider', 'coingecko');
    });

    it('appears once the assets arrive after the first draw (the Dashboard)', async () => {
        state.assets = new Map();
        render(ProviderAttributionNote, {assetIds: [2]});
        expect(screen.queryByTestId('provider-attribution-note')).toBeNull();

        state.assets = new Map([[2, {provider_code: 'coingecko'}]]);
        bump(versions.assets);
        expect(await screen.findByTestId('provider-attribution-link')).toHaveAttribute('data-provider', 'coingecko');
    });

    it('loads the asset store when the ids arrive after the first draw (the positions of a saved view)', async () => {
        const view = render(ProviderAttributionNote, {assetIds: []});
        expect(ensureAssetsLoaded).not.toHaveBeenCalled();

        await view.rerender({assetIds: [2]});
        await waitFor(() => expect(ensureAssetsLoaded).toHaveBeenCalled());
        expect(await screen.findByTestId('provider-attribution-link')).toHaveAttribute('data-provider', 'coingecko');
    });
});
