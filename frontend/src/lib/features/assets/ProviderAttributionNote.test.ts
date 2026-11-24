// @vitest-environment jsdom
/**
 * ProviderAttributionNote — component test (Vitest + jsdom), project 76, P4 and TL42.
 *
 * The line a provider's terms ask for («Powered by CoinGecko», linked to coingecko.com), drawn on the provider's own
 * card in Settings › Plugins — the screens that show its prices carry none (TL42) — and not at all for a provider that
 * asks none. The provider list is stubbed: the component reads it through its getter, and follows its version store.
 *
 * Asserted on test ids, `data-provider`, the link's `href`/`target`/`rel`; the brand text is CoinGecko's own wording,
 * the same in every language, so it is compared as such.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {render, screen} from '$test/component';

const state = vi.hoisted(() => ({attributions: new Map<string, {text: string; url: string}>()}));
const versions = vi.hoisted(() => ({providers: null as unknown}));

vi.mock('$lib/utils/providerHelpers', async () => {
    const {writable: w} = await import('svelte/store');
    versions.providers = w(0);
    return {
        assetProvidersVersion: versions.providers,
        ensureAssetProvidersCached: vi.fn(async () => undefined),
        getAssetProviderAttribution: vi.fn((code: string | null | undefined) => (code ? (state.attributions.get(code) ?? null) : null)),
    };
});

import ProviderAttributionNote from './ProviderAttributionNote.svelte';

const COINGECKO = {text: 'Powered by CoinGecko', url: 'https://www.coingecko.com/'};
const bump = (store: unknown) => (store as ReturnType<typeof writable<number>>).update((v) => v + 1);

beforeEach(() => {
    state.attributions = new Map([['coingecko', COINGECKO]]);
});

describe('ProviderAttributionNote', () => {
    it('draws nothing for a provider that asks for no line', () => {
        render(ProviderAttributionNote, {providerCodes: ['yfinance', null]});
        expect(screen.queryByTestId('provider-attribution-note')).toBeNull();
    });

    it('draws one linked line for CoinGecko, however many times it is named', () => {
        render(ProviderAttributionNote, {providerCodes: ['coingecko', 'yfinance', 'coingecko']});
        const links = screen.getAllByTestId('provider-attribution-link');
        expect(links).toHaveLength(1);
        expect(links[0]).toHaveAttribute('data-provider', 'coingecko');
        expect(links[0]).toHaveAttribute('href', 'https://www.coingecko.com/');
        expect(links[0]).toHaveAttribute('target', '_blank');
        expect(links[0].getAttribute('rel')).toContain('noopener');
        expect(links[0].textContent?.trim()).toBe('Powered by CoinGecko');
    });

    it('appears once the provider list arrives after the first draw', async () => {
        state.attributions = new Map();
        render(ProviderAttributionNote, {providerCodes: ['coingecko']});
        expect(screen.queryByTestId('provider-attribution-note')).toBeNull();

        state.attributions = new Map([['coingecko', COINGECKO]]);
        bump(versions.providers);
        expect(await screen.findByTestId('provider-attribution-link')).toHaveAttribute('data-provider', 'coingecko');
    });
});
