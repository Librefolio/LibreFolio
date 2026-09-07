/**
 * assetSimilarity.test.ts — Unit tests for the token-aware asset unification engine.
 *
 * The cases that matter are the two opposite failure modes:
 * - **false negative**: the BTP "CUM" pair and the with/without-ISIN pair must be proposed;
 * - **false positive**: two bonds differing only by maturity must NEVER be proposed.
 *
 * @module utils/__tests__/assetSimilarity.test
 */
import {describe, expect, it} from 'vitest';

import {buildAssetGroups, compareAssetNames, compareAssets, normalizeAssetName, tokenizeAssetName, type SimilarityInput} from '../assetSimilarity';

describe('normalizeAssetName', () => {
    it('strips accents, case and punctuation', () => {
        expect(normalizeAssetName('Société Générale S.p.A.')).toBe('SOCIETE GENERALE S P A');
    });

    it('keeps numeric groups glued together', () => {
        expect(normalizeAssetName('BTP 1/3/32')).toBe('BTP 1-3-32');
        expect(normalizeAssetName('BTP 25.02.2033')).toBe('BTP 25-02-2033');
    });

    it('preserves percent signs on coupon rates', () => {
        expect(normalizeAssetName('BTP 1,65%')).toBe('BTP 1-65%');
    });

    it('returns an empty string for nullish input', () => {
        expect(normalizeAssetName(null)).toBe('');
        expect(normalizeAssetName(undefined)).toBe('');
    });
});

describe('tokenizeAssetName', () => {
    it('drops legal-form noise but keeps numeric tokens', () => {
        expect(tokenizeAssetName(normalizeAssetName('Enel SpA 1/3/32'))).toEqual(['ENEL', '1-3-32']);
    });
});

describe('compareAssetNames', () => {
    it('flags a numeric mismatch between two maturities', () => {
        const cmp = compareAssetNames('BTP 1/3/32', 'BTP 1/3/35');
        expect(cmp.numericMismatch).toBe(true);
    });

    it('does not flag a numeric mismatch when the numbers agree', () => {
        const cmp = compareAssetNames('BTP Piu 1/3/32 CUM', 'BTP Piu 1/3/32');
        expect(cmp.numericMismatch).toBe(false);
        expect(cmp.onlyMinorTokenDiff).toBe(true);
    });

    it('treats a missing coupon as a numeric mismatch', () => {
        const cmp = compareAssetNames('BTP Valore 3,35%', 'BTP Valore');
        expect(cmp.numericMismatch).toBe(true);
    });

    it('scores 0 when either side is empty', () => {
        expect(compareAssetNames('', 'BTP').score).toBe(0);
        expect(compareAssetNames(null, null).score).toBe(0);
    });

    // The neutrality of a suffix is judged by shape, not by a dictionary of known markers:
    // a couple of short alphabetic tokens on an otherwise identical name.
    it('accepts an unlisted short suffix, not just the ones somebody thought of', () => {
        expect(compareAssetNames('Btp Piu Fb33', 'Btp Piu Fb33 Ptf').onlyMinorTokenDiff).toBe(true);
    });

    it('rejects a long distinguishing token', () => {
        // "World" vs "Emerging" is a different index, not a different share class.
        expect(compareAssetNames('Amundi MSCI World', 'Amundi MSCI Emerging').onlyMinorTokenDiff).toBe(false);
    });

    it('rejects more than a couple of differing tokens', () => {
        expect(compareAssetNames('Btp Piu Fb33 Cum', 'Btp Piu Fb33 Ex Acc Hdg').onlyMinorTokenDiff).toBe(false);
    });

    it('never calls a numeric difference minor', () => {
        // Guard held on its own: the flag is exported, so it cannot lean on the caller's checks.
        expect(compareAssetNames('Btp Ag30', 'Btp St27').onlyMinorTokenDiff).toBe(false);
    });
});

describe('compareAssets — strong signals', () => {
    it('links two entries sharing an ISIN', () => {
        const link = compareAssets({key: 1, isin: 'IT0005634792', name: 'Btp Piu'}, {key: 2, isin: 'it0005634792', name: 'BTP PIU SCAD FB33'});
        expect(link?.reason).toBe('isin');
        expect(link?.strength).toBe('strong');
    });

    it('links two entries sharing a ticker', () => {
        const link = compareAssets({key: 1, symbol: 'VWCE', name: 'Vanguard All World'}, {key: 2, symbol: 'vwce', name: 'VG FTSE AW ACC'});
        expect(link?.reason).toBe('ticker');
        expect(link?.strength).toBe('strong');
    });

    it('links two entries with an identical normalized name', () => {
        const link = compareAssets({key: 1, name: 'Enel S.p.A.'}, {key: 2, name: 'ENEL SPA'});
        expect(link?.reason).toBe('name');
        expect(link?.strength).toBe('strong');
    });

    it('does not treat identical names as strong when the ISINs contradict', () => {
        const link = compareAssets({key: 1, name: 'Enel SpA', isin: 'IT0003128367'}, {key: 2, name: 'ENEL SPA', isin: 'IT0009999999'});
        expect(link?.strength).not.toBe('strong');
    });
});

describe('compareAssets — the BTP CUM case', () => {
    it('proposes a merge when two ISINs differ but only a CUM suffix separates the names', () => {
        const link = compareAssets({key: 1, isin: 'IT0005634792', name: "Btp Piu' Sc Fb33 CUM"}, {key: 2, isin: 'IT0005634800', name: "Btp Piu' Sc Fb33"});
        expect(link).not.toBeNull();
        expect(link?.reason).toBe('nameSuffix');
        expect(link?.strength).toBe('weak');
    });

    it('proposes a merge when one layout carries no ISIN at all', () => {
        const link = compareAssets({key: 1, isin: 'IT0005634792', name: 'Btp Valore Mz30 2,15%'}, {key: 2, isin: null, name: 'Btp Valore Mz30 2,15%'});
        expect(link?.strength).toBe('strong');
    });

    it('proposes a weak link for a near-miss name when one side lacks an ISIN', () => {
        const link = compareAssets({key: 1, isin: 'IT0005634792', name: 'Btp Valore Mz30 2,15% Serie'}, {key: 2, isin: null, name: 'Btp Valore Mz30 2,15%'});
        expect(link?.reason).toBe('nameNoIsin');
        expect(link?.strength).toBe('weak');
    });
});

describe('compareAssets — the false-positive guard', () => {
    it('never links two bonds differing by maturity', () => {
        expect(compareAssets({key: 1, isin: 'IT0000000001', name: 'BTP 1/3/32'}, {key: 2, isin: 'IT0000000002', name: 'BTP 1/3/35'})).toBeNull();
    });

    it('never links two bonds differing by coupon', () => {
        expect(compareAssets({key: 1, name: 'BTP Valore 3,35%'}, {key: 2, name: 'BTP Valore 2,15%'})).toBeNull();
    });

    it('never links two bonds differing by maturity even without ISINs', () => {
        expect(compareAssets({key: 1, name: 'BTP Piu Sc Fb33'}, {key: 2, name: 'BTP Piu Sc Fb35'})).toBeNull();
    });

    it('does not link unrelated names', () => {
        expect(compareAssets({key: 1, name: 'Enel SpA'}, {key: 2, name: 'Vanguard All World'})).toBeNull();
    });
});

describe('buildAssetGroups', () => {
    it('marks a same-ISIN pair as confirmed', () => {
        const items: SimilarityInput[] = [
            {key: 1, fileId: 'f1', isin: 'IT0005634792', name: 'Btp Piu'},
            {key: 2, fileId: 'f2', isin: 'IT0005634792', name: 'BTP PIU SCAD'},
        ];
        const groups = buildAssetGroups(items);
        expect(groups).toHaveLength(1);
        expect(groups[0].state).toBe('confirmed');
        expect(groups[0].members).toEqual([1, 2]);
    });

    it('marks a CUM pair as proposed, not confirmed', () => {
        const items: SimilarityInput[] = [
            {key: 1, fileId: 'f1', isin: 'IT0005634792', name: "Btp Piu' Sc Fb33 CUM"},
            {key: 2, fileId: 'f2', isin: 'IT0005634800', name: "Btp Piu' Sc Fb33"},
        ];
        const groups = buildAssetGroups(items);
        expect(groups).toHaveLength(1);
        expect(groups[0].state).toBe('proposed');
        expect(groups[0].links[0].reason).toBe('nameSuffix');
    });

    it('keeps two different maturities in separate single groups', () => {
        const items: SimilarityInput[] = [
            {key: 1, name: 'BTP 1/3/32', isin: 'IT0000000001'},
            {key: 2, name: 'BTP 1/3/35', isin: 'IT0000000002'},
        ];
        const groups = buildAssetGroups(items);
        expect(groups).toHaveLength(2);
        expect(groups.every((g) => g.state === 'single')).toBe(true);
    });

    it('returns every item exactly once', () => {
        const items: SimilarityInput[] = [
            {key: 1, isin: 'IT0005634792', name: 'Btp Piu Sc Fb33 CUM'},
            {key: 2, isin: 'IT0005634800', name: 'Btp Piu Sc Fb33'},
            {key: 3, name: 'BTP 1/3/35', isin: 'IT0000000002'},
            {key: 4, symbol: 'VWCE', name: 'Vanguard All World'},
            {key: 5, symbol: 'VWCE', name: 'VG FTSE AW'},
        ];
        const groups = buildAssetGroups(items);
        const seen = groups.flatMap((g) => g.members).sort();
        expect(seen).toEqual([1, 2, 3, 4, 5]);
    });

    it('sorts proposed groups before confirmed ones and singles last', () => {
        const items: SimilarityInput[] = [
            {key: 1, name: 'Lonely Asset'},
            {key: 2, symbol: 'VWCE', name: 'Vanguard All World'},
            {key: 3, symbol: 'VWCE', name: 'VG FTSE AW'},
            {key: 4, isin: 'IT0005634792', name: 'Btp Piu Sc Fb33 CUM'},
            {key: 5, isin: 'IT0005634800', name: 'Btp Piu Sc Fb33'},
        ];
        const groups = buildAssetGroups(items);
        expect(groups.map((g) => g.state)).toEqual(['proposed', 'confirmed', 'single']);
    });

    it('transitively merges a three-way chain', () => {
        const items: SimilarityInput[] = [
            {key: 1, isin: 'IT0005634792', name: 'Btp Valore Mz30 2,15%'},
            {key: 2, isin: 'IT0005634792', name: 'BTP VALORE MZ30 2,15%'},
            {key: 3, isin: null, name: 'Btp Valore Mz30 2,15%'},
        ];
        const groups = buildAssetGroups(items);
        expect(groups).toHaveLength(1);
        expect(groups[0].members).toEqual([1, 2, 3]);
    });

    it('handles an empty input', () => {
        expect(buildAssetGroups([])).toEqual([]);
    });
});
