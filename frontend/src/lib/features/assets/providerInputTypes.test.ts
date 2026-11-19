/**
 * providerInputTypes — the label of a provider's input type (project 76, P3).
 *
 * The codes TICKER, ISIN and URL read the same in every language and stay as they are; a code with an underscore
 * reads with a space. COINGECKO_ID, CoinGecko's own code for a coin («bitcoin»; N-ID, 19/11), has a translated label and a
 * translated example.
 */
import {describe, expect, it} from 'vitest';
import {providerInputTypeLabel, providerInputTypePlaceholder} from './providerInputTypes';

const tr = (key: string) => `[[${key}]]`;

describe('providerInputTypeLabel', () => {
    it('translates COINGECKO_ID', () => {
        expect(providerInputTypeLabel('COINGECKO_ID', tr)).toBe('[[assets.provider.inputType.COINGECKO_ID]]');
    });

    it('keeps the other codes, an underscore read as a space', () => {
        expect(['TICKER', 'ISIN', 'URL', 'AUTO_GENERATED'].map((type) => providerInputTypeLabel(type, tr))).toEqual(['TICKER', 'ISIN', 'URL', 'AUTO GENERATED']);
    });
});

describe('providerInputTypePlaceholder', () => {
    it('gives each type its example, COINGECKO_ID translated', () => {
        expect(providerInputTypePlaceholder('COINGECKO_ID', tr)).toBe('[[assets.provider.inputTypePlaceholder.COINGECKO_ID]]');
        expect(providerInputTypePlaceholder('ISIN', tr)).toBe('IE00B4L5Y983');
        expect(providerInputTypePlaceholder('URL', tr)).toBe('https://example.com/price');
        expect(providerInputTypePlaceholder('TICKER', tr)).toBe('AAPL, MSFT…');
        expect(providerInputTypePlaceholder('', tr)).toBe('AAPL, IE00B4L5Y983, https://...');
    });
});
