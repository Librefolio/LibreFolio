/**
 * providerInputTypes — the label of a provider's input type (project 76, P3).
 *
 * The codes TICKER, ISIN and URL read the same in every language and stay as they are; a code with an underscore
 * reads with a space. PROVIDER_ID, a provider's own code (CoinGecko's «bitcoin»), has a translated label and a
 * translated example.
 */
import {describe, expect, it} from 'vitest';
import {providerInputTypeLabel, providerInputTypePlaceholder} from './providerInputTypes';

const tr = (key: string) => `[[${key}]]`;

describe('providerInputTypeLabel', () => {
    it('translates PROVIDER_ID', () => {
        expect(providerInputTypeLabel('PROVIDER_ID', tr)).toBe('[[assets.provider.inputType.PROVIDER_ID]]');
    });

    it('keeps the other codes, an underscore read as a space', () => {
        expect(['TICKER', 'ISIN', 'URL', 'AUTO_GENERATED'].map((type) => providerInputTypeLabel(type, tr))).toEqual(['TICKER', 'ISIN', 'URL', 'AUTO GENERATED']);
    });
});

describe('providerInputTypePlaceholder', () => {
    it('gives each type its example, PROVIDER_ID translated', () => {
        expect(providerInputTypePlaceholder('PROVIDER_ID', tr)).toBe('[[assets.provider.inputTypePlaceholder.PROVIDER_ID]]');
        expect(providerInputTypePlaceholder('ISIN', tr)).toBe('IE00B4L5Y983');
        expect(providerInputTypePlaceholder('URL', tr)).toBe('https://example.com/price');
        expect(providerInputTypePlaceholder('TICKER', tr)).toBe('AAPL, MSFT…');
        expect(providerInputTypePlaceholder('', tr)).toBe('AAPL, IE00B4L5Y983, https://...');
    });
});
