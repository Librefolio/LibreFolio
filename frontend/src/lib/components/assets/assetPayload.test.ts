/**
 * assetPayload — pure unit tests for the shared save-path builders.
 */
import {describe, expect, it} from 'vitest';
import {normalizeQuoteBaseQuantity, buildClassificationParams, buildClassificationPatch, normalizeDistribution, sameDistribution} from './assetPayload';
import type {ClassificationParams} from './assetPayload';

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

// Root cause E2: a full-block replace silently dropped untouched
// classification_params subfields on the wire. buildClassificationPatch is the
// frontend half of that fix — it must diff previous vs. current per subfield
// (omit unchanged, null only what actually cleared) so the backend's own
// per-field shallow merge (see backend/app/services/asset_source.py
// patch_assets_bulk) receives exactly the intended keys.
describe('buildClassificationPatch', () => {
    const full: ClassificationParams = {
        short_description: 'a bond',
        sector_area: {distribution: {Tech: 0.4, Health: 0.6}},
        geographic_area: {distribution: {US: 1}},
    };

    it('omits the patch when nothing was ever set (unknown initial state)', () => {
        expect(buildClassificationPatch(undefined, undefined)).toBeUndefined();
    });

    it('omits the patch when current is identical to previous', () => {
        const current: ClassificationParams = {
            short_description: 'a bond',
            sector_area: {distribution: {Tech: 0.4, Health: 0.6}},
            geographic_area: {distribution: {US: 1}},
        };
        expect(buildClassificationPatch(full, current)).toBeUndefined();
    });

    it('treats equal weights under a different key order as no change', () => {
        const current: ClassificationParams = {
            short_description: 'a bond',
            sector_area: {distribution: {Health: 0.6, Tech: 0.4}}, // same pairs, keys reordered
            geographic_area: {distribution: {US: 1}},
        };
        expect(buildClassificationPatch(full, current)).toBeUndefined();
    });

    it('sends a whole-block null when the last remaining field is cleared', () => {
        // previous carries every subfield; current is undefined, i.e. the editor
        // ends up with nothing left at all — this must collapse to a single
        // top-level null, not an object of three null subfields.
        expect(buildClassificationPatch(full, undefined)).toBeNull();
    });

    it('nulls only the cleared subfield, leaving siblings out of the patch entirely', () => {
        // sector_area is dropped, short_description/geographic_area are unchanged
        // and current is still a real object (not undefined) — so this must NOT
        // hit the whole-block-null branch, and must not mention the untouched
        // siblings at all (omission, not a redundant same-value key).
        const current: ClassificationParams = {
            short_description: 'a bond',
            geographic_area: {distribution: {US: 1}},
        };
        const patch = buildClassificationPatch(full, current);
        expect(patch).toEqual({sector_area: null});
        expect(patch).not.toHaveProperty('short_description');
        expect(patch).not.toHaveProperty('geographic_area');
    });

    it('patches only short_description when only the description changed', () => {
        const current: ClassificationParams = {
            short_description: 'an updated bond',
            sector_area: {distribution: {Tech: 0.4, Health: 0.6}},
            geographic_area: {distribution: {US: 1}},
        };
        const patch = buildClassificationPatch(full, current);
        expect(patch).toEqual({short_description: 'an updated bond'});
        expect(patch).not.toHaveProperty('sector_area');
        expect(patch).not.toHaveProperty('geographic_area');
    });
});

describe('sameDistribution', () => {
    it('compares own key/value pairs independently of insertion order without mutating either input', () => {
        const left = Object.freeze({Technology: 0.4, Health: 0.6});
        const right = Object.freeze({Health: 0.6, Technology: 0.4});
        expect(sameDistribution(left, right)).toBe(true);
        expect(sameDistribution(right, left)).toBe(true);
        expect(Object.keys(left)).toEqual(['Technology', 'Health']);
        expect(Object.keys(right)).toEqual(['Health', 'Technology']);
    });

    it('treats omitted distributions as empty, but distinguishes missing keys from zero weights', () => {
        expect(sameDistribution()).toBe(true);
        expect(sameDistribution(undefined, {})).toBe(true);
        expect(sameDistribution({}, {Technology: 0})).toBe(false);
        expect(sameDistribution({Technology: 0}, {})).toBe(false);
    });

    it('rejects changed weights and changed keys even when cardinality and totals match', () => {
        expect(sameDistribution({Technology: 0.4, Health: 0.6}, {Technology: 0.6, Health: 0.4})).toBe(false);
        expect(sameDistribution({Technology: 1}, {Health: 1})).toBe(false);
        expect(sameDistribution({toString: 1}, {Technology: 1})).toBe(false);
    });
});

describe('normalizeDistribution', () => {
    it('accepts numeric strings and numbers, coercing both to number', () => {
        expect(normalizeDistribution({Tech: '0.4', Health: 0.6})).toEqual({Tech: 0.4, Health: 0.6});
    });

    it.each([
        ['non-numeric string', 'abc'],
        ['NaN', NaN],
        ['positive Infinity', Infinity],
        ['negative Infinity', -Infinity],
        ['blank/whitespace string', '   '],
    ])('throws on a non-finite weight (%s)', (_label, value) => {
        expect(() => normalizeDistribution({Tech: value as string | number})).toThrow('Invalid distribution weight.');
    });
});
