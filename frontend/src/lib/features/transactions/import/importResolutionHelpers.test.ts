import {describe, it, expect} from 'vitest';
import type {AssetResolution} from './importTypes';
import {createNamesFor, createOtherFor, duplicateCandidates, resolutionLabel} from './importResolutionHelpers';

type Candidate = AssetResolution['candidates'][number];
const cand = (asset_id: number, name: string, match_confidence = 'exact'): Candidate => ({asset_id, name, match_confidence});

/** A resolution with sane empty defaults; override only the fields a test cares about. */
const res = (over: Partial<AssetResolution> = {}): AssetResolution => ({
    fakeAssetId: 2147483647,
    extractedSymbol: null,
    extractedIsin: null,
    extractedName: null,
    candidates: [],
    resolvedAssetId: null,
    txCount: 0,
    sourceFiles: [],
    notices: [],
    groupIsins: [],
    groupSymbols: [],
    groupNames: [],
    groupMembers: [],
    groupState: 'single',
    groupLinks: [],
    groupPrimaryIsin: false,
    groupPrimarySymbol: false,
    ...over,
});

describe('createNamesFor', () => {
    it('returns an empty list for an undefined resolution', () => {
        expect(createNamesFor(undefined)).toEqual([]);
    });

    it('collects group names first, then extracted name, then candidate names — deduplicated', () => {
        const out = createNamesFor(
            res({
                groupNames: ['Alpha Fund', 'Alpha Renamed'],
                extractedName: 'Alpha Raw',
                candidates: [cand(1, 'Alpha Cand'), cand(2, 'Alpha Fund')], // 'Alpha Fund' duplicates a group name
            }),
        );
        expect(out).toEqual(['Alpha Fund', 'Alpha Renamed', 'Alpha Raw', 'Alpha Cand']);
    });

    it('drops blank and whitespace-only names', () => {
        // '' fails the truthiness guard; '   ' is truthy but trims to empty.
        const out = createNamesFor(res({groupNames: ['', '   ', 'Real'], extractedName: '   ', candidates: [cand(1, '')]}));
        expect(out).toEqual(['Real']);
    });

    it('tolerates a nullish candidates list', () => {
        const out = createNamesFor(res({groupNames: ['Only'], candidates: null as unknown as Candidate[]}));
        expect(out).toEqual(['Only']);
    });
});

describe('createOtherFor', () => {
    it('returns an empty list for an undefined resolution', () => {
        expect(createOtherFor(undefined, null, null)).toEqual([]);
    });

    it('keeps every code when no primary is elected (null primaries normalise to empty)', () => {
        const out = createOtherFor(res({groupNames: ['Name'], groupIsins: ['US123', 'US999'], groupSymbols: ['AAA']}), null, null);
        expect(out).toEqual(['Name', 'US123', 'US999', 'AAA']);
    });

    it('excludes the elected primary ISIN and symbol case-insensitively, keeping the rest', () => {
        const out = createOtherFor(
            res({groupNames: ['Name'], groupIsins: ['us123', 'US999'], groupSymbols: ['aaa', 'BBB']}),
            'US123', // matches 'us123' regardless of case
            'AAA', // matches 'aaa'
        );
        expect(out).toEqual(['Name', 'US999', 'BBB']);
    });

    it('deduplicates names against codes', () => {
        const out = createOtherFor(res({groupNames: ['SHARED'], groupIsins: ['SHARED']}), null, null);
        expect(out).toEqual(['SHARED']);
    });
});

describe('duplicateCandidates', () => {
    it('returns nothing when fewer than two strong candidates exist', () => {
        expect(duplicateCandidates(res({candidates: []}))).toEqual([]);
        expect(duplicateCandidates(res({candidates: [cand(1, 'One', 'exact')]}))).toEqual([]);
    });

    it('returns exact/high candidates once at least two exist, case-insensitively', () => {
        const strong = duplicateCandidates(
            res({
                candidates: [cand(1, 'A', 'EXACT'), cand(2, 'B', 'High'), cand(3, 'C', 'low'), cand(4, 'D', 'medium')],
            }),
        );
        expect(strong.map((c) => c.asset_id)).toEqual([1, 2]);
    });

    it('ignores weak-only candidate sets even when many', () => {
        expect(duplicateCandidates(res({candidates: [cand(1, 'A', 'low'), cand(2, 'B', 'medium')]}))).toEqual([]);
    });
});

describe('resolutionLabel', () => {
    const noDb = () => undefined;

    it('returns the DB display name when the fake id is bound to a real asset', () => {
        const label = resolutionLabel(res({resolvedAssetId: 42, groupNames: ['Group']}), (id) => (id === 42 ? 'DB Name' : undefined));
        expect(label).toBe('DB Name');
    });

    it('falls back to the matched candidate name when the store has no display name yet', () => {
        const label = resolutionLabel(res({resolvedAssetId: 7, candidates: [cand(7, 'Candidate Name')], groupNames: ['Group']}), noDb);
        expect(label).toBe('Candidate Name');
    });

    it('ignores a whitespace-only DB name and continues to the fallback chain', () => {
        const label = resolutionLabel(res({resolvedAssetId: 7, groupNames: ['Group']}), () => '   ');
        expect(label).toBe('Group');
    });

    it('uses the fallback chain when unresolved: group name, then extraction, then fake id', () => {
        expect(resolutionLabel(res({groupNames: ['G'], extractedName: 'E'}), noDb)).toBe('G');
        expect(resolutionLabel(res({extractedName: 'E', extractedSymbol: 'S'}), noDb)).toBe('E');
        expect(resolutionLabel(res({extractedSymbol: 'S', extractedIsin: 'I'}), noDb)).toBe('S');
        expect(resolutionLabel(res({extractedIsin: 'I'}), noDb)).toBe('I');
        expect(resolutionLabel(res({fakeAssetId: 999}), noDb)).toBe('#999');
    });

    it('falls through to the chain when resolved but neither store nor candidates name the asset', () => {
        // resolvedAssetId set, but no candidate matches its id and the store returns undefined.
        const label = resolutionLabel(res({resolvedAssetId: 5, candidates: [cand(6, 'Other')], extractedSymbol: 'SYM'}), noDb);
        expect(label).toBe('SYM');
    });
});
