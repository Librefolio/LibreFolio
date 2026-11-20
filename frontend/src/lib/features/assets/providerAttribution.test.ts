/**
 * providerAttribution — which attribution lines a screen owes (project 76, P4).
 *
 * A provider's terms may ask the interface to show a line with its prices (CoinGecko: «Powered by CoinGecko», linked to
 * its site). A screen owes one line per such provider among the assets it shows: never one per row, and none when no
 * asset on screen is priced by such a provider. The codes come from the assets (their `provider_code`); a code with no
 * attribution, or not known, owes nothing.
 */
import {describe, expect, it} from 'vitest';
import {attributionsFor, type ProviderAttribution} from './providerAttribution';

const COINGECKO: ProviderAttribution = {text: 'Powered by CoinGecko', url: 'https://www.coingecko.com/'};
const lookup = (code: string): ProviderAttribution | null => (code === 'coingecko' ? COINGECKO : null);

describe('attributionsFor', () => {
    it('owes nothing when no provider on screen asks for a line', () => {
        expect(attributionsFor(['yfinance', 'justetf', null, undefined, ''], lookup)).toEqual([]);
        expect(attributionsFor([], lookup)).toEqual([]);
    });

    it('owes one line per provider, never one per asset', () => {
        expect(attributionsFor(['coingecko', 'yfinance', 'coingecko', 'coingecko'], lookup)).toEqual([{code: 'coingecko', ...COINGECKO}]);
    });

    it('keeps the order in which the providers first appear', () => {
        const two = (code: string): ProviderAttribution | null => (code === 'a' ? {text: 'Powered by A', url: 'https://a.example/'} : code === 'b' ? {text: 'Powered by B', url: 'https://b.example/'} : null);
        expect(attributionsFor(['b', 'x', 'a', 'b'], two).map((line) => line.code)).toEqual(['b', 'a']);
    });
});
