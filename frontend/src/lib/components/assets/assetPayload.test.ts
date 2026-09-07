/**
 * assetPayload — pure unit tests for the shared save-path builders.
 */
import {describe, expect, it} from 'vitest';
import {normalizeQuoteBaseQuantity, buildClassificationParams} from './assetPayload';

describe('normalizeQuoteBaseQuantity', () => {
    it('passes a positive quantity through unchanged', () => {
        expect(normalizeQuoteBaseQuantity(1)).toBe(1);
        expect(normalizeQuoteBaseQuantity(100)).toBe(100);
    });

    it('floors a non-positive or falsy quantity to 1', () => {
        expect(normalizeQuoteBaseQuantity(0)).toBe(1);
        expect(normalizeQuoteBaseQuantity(-5)).toBe(1);
        expect(normalizeQuoteBaseQuantity(NaN)).toBe(1);
    });
});

describe('buildClassificationParams', () => {
    it('returns undefined when nothing is set', () => {
        expect(buildClassificationParams('', {}, {})).toBeUndefined();
    });

    it('includes only the short_description when only it is set', () => {
        expect(buildClassificationParams('a bond', {}, {})).toEqual({short_description: 'a bond'});
    });

    it('wraps sector and geographic distributions under a distribution key', () => {
        const out = buildClassificationParams('', {Tech: 0.6, Health: 0.4}, {US: 1});
        expect(out).toEqual({
            sector_area: {distribution: {Tech: 0.6, Health: 0.4}},
            geographic_area: {distribution: {US: 1}},
        });
    });

    it('omits an empty distribution but keeps a non-empty sibling', () => {
        const out = buildClassificationParams('', {Tech: 1}, {});
        expect(out).toEqual({sector_area: {distribution: {Tech: 1}}});
        expect(out).not.toHaveProperty('geographic_area');
    });

    it('assembles all three parts together', () => {
        const out = buildClassificationParams('desc', {S: 1}, {G: 1});
        expect(out).toEqual({
            short_description: 'desc',
            sector_area: {distribution: {S: 1}},
            geographic_area: {distribution: {G: 1}},
        });
    });
});
