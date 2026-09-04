/**
 * Tests for the import-asset grouping layer.
 *
 * The two scenarios that motivated it are pinned explicitly: the Crédit Agricole pair of layouts
 * (one carries the ISIN, the other only a name) and the Italian retail bond issued under a
 * non-tradeable CUM code. The rest guards the override model, whose whole job is to survive the
 * wizard recomputing everything from scratch.
 */

import {describe, expect, it} from 'vitest';
import {
    clusterSignature,
    electPrimary,
    summariseLinks,
    groupExtractedAssets,
    groupIdentifiers,
    groupSignature,
    hasElection,
    hasOpenProposals,
    isPrimary,
    memberKey,
    movePartition,
    orderedIdentifiers,
    partitionOf,
    representativeMap,
    representativeOf,
    splitPartition,
    type ExtractedAsset,
} from '../assetGrouping';

let nextId = -900000;
function asset(partial: Partial<ExtractedAsset> & {fileId: string}): ExtractedAsset {
    return {
        fakeAssetId: nextId--,
        fileName: `${partial.fileId}.csv`,
        name: null,
        isin: null,
        symbol: null,
        ...partial,
    };
}

describe('memberKey', () => {
    it('separates the same instrument read from two files', () => {
        const a = asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu'});
        const b = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu'});
        expect(memberKey(a)).not.toBe(memberKey(b));
    });

    it('is stable against casing and padding, so a re-parse maps onto the same key', () => {
        const a = asset({fileId: 'f1', isin: ' it0005634792 ', name: 'btp piu'});
        const b = asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP PIU'});
        expect(memberKey(a)).toBe(memberKey(b));
    });

    it('does not depend on the fake id, which is reallocated on every merge', () => {
        const a = asset({fileId: 'f1', isin: 'IT0005634792'});
        expect(memberKey({...a, fakeAssetId: -1})).toBe(memberKey({...a, fakeAssetId: -999}));
    });
});

describe('groupExtractedAssets — automatic partition', () => {
    it('confirms a group on an identical ISIN across files', () => {
        const groups = groupExtractedAssets([asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'}), asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP PIU 02/33'})]);
        expect(groups).toHaveLength(1);
        expect(groups[0].state).toBe('confirmed');
        expect(groups[0].members).toHaveLength(2);
    });

    /** The Crédit Agricole case at its easiest: the two layouts spell the name identically. */
    it('confirms a group when the names match exactly and only one side has the ISIN', () => {
        const groups = groupExtractedAssets([asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'}), asset({fileId: 'f2', isin: null, name: 'BTP Piu Sc Fb33'})]);
        expect(groups).toHaveLength(1);
        expect(groups[0].state).toBe('confirmed');
        expect(hasOpenProposals(groups)).toBe(false);
    });

    /** The same case when the layouts abbreviate differently — evidence, but not proof. */
    it('proposes a group when only one side carries an ISIN and the names merely resemble', () => {
        const groups = groupExtractedAssets([asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'}), asset({fileId: 'f2', isin: null, name: 'BTP Piu Scad Fb33'})]);
        expect(groups).toHaveLength(1);
        expect(groups[0].state).toBe('proposed');
        expect(hasOpenProposals(groups)).toBe(true);
    });

    /** The whole reason numeric tokens are treated as identifying. */
    it('never groups two bonds that differ on a maturity', () => {
        const groups = groupExtractedAssets([asset({fileId: 'f1', isin: 'IT0000000001', name: 'BTP 1/3/32'}), asset({fileId: 'f1', isin: 'IT0000000002', name: 'BTP 1/3/35'})]);
        expect(groups).toHaveLength(2);
        expect(groups.every((g) => g.state === 'single')).toBe(true);
        expect(hasOpenProposals(groups)).toBe(false);
    });

    it('leaves unrelated assets alone', () => {
        const groups = groupExtractedAssets([asset({fileId: 'f1', isin: 'IE00B4L5Y983', name: 'iShares Core MSCI World'}), asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'})]);
        expect(groups).toHaveLength(2);
    });

    it('keeps extraction order, so merging one pair does not reshuffle the page', () => {
        const world = asset({fileId: 'f1', isin: 'IE00B4L5Y983', name: 'iShares Core MSCI World'});
        const btp1 = asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
        const btp2 = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
        const groups = groupExtractedAssets([world, btp1, btp2]);
        // The two-member group is second because its earliest member was extracted second —
        // sorting by size would have thrown it in front and moved the ETF under the user's hand.
        expect(groups.map((g) => g.members.length)).toEqual([1, 2]);
        expect(groups[0].members[0].fakeAssetId).toBe(world.fakeAssetId);
    });

    it('orders by extraction even when the fake ids run downwards', () => {
        const first = {...asset({fileId: 'f1', name: 'Alpha'}), fakeAssetId: -10};
        const second = {...asset({fileId: 'f2', name: 'Beta'}), fakeAssetId: -20};
        const groups = groupExtractedAssets([first, second]);
        expect(groups.map((g) => g.members[0].name)).toEqual(['Alpha', 'Beta']);
    });
});

describe('groupExtractedAssets — user override', () => {
    const a = asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
    const b = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
    const c = asset({fileId: 'f1', isin: 'IE00B4L5Y983', name: 'iShares Core MSCI World'});

    it('honours a partition that contradicts the engine', () => {
        const groups = groupExtractedAssets([a, b, c], [[memberKey(a)], [memberKey(b), memberKey(c)]]);
        const sizes = groups.map((g) => g.members.length).sort();
        expect(sizes).toEqual([1, 2]);
    });

    it('marks an overridden group as settled, never as a proposal', () => {
        const groups = groupExtractedAssets([a, c], [[memberKey(a), memberKey(c)]]);
        expect(groups[0].state).toBe('confirmed');
        expect(groups[0].userTouched).toBe(true);
    });

    /** A file added after the user edited the layout must not vanish. */
    it('keeps members the override does not mention, alone', () => {
        const groups = groupExtractedAssets([a, b, c], [[memberKey(a), memberKey(b)]]);
        expect(groups).toHaveLength(2);
        expect(groups.flatMap((g) => g.members)).toHaveLength(3);
    });

    it('drops keys that no longer match any asset', () => {
        const groups = groupExtractedAssets([a], [[memberKey(a), 'GONE'], ['ALSO-GONE']]);
        expect(groups).toHaveLength(1);
        expect(groups[0].members).toHaveLength(1);
    });

    it('treats an explicit confirmation as settling a proposal', () => {
        const weakA = asset({fileId: 'f1', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
        const weakB = asset({fileId: 'f2', isin: null, name: 'BTP Piu Scad Fb33'});
        const signature = clusterSignature([memberKey(weakA), memberKey(weakB)]);
        expect(groupExtractedAssets([weakA, weakB])[0].state).toBe('proposed');
        expect(groupExtractedAssets([weakA, weakB], null, new Set([signature]))[0].state).toBe('confirmed');
    });
});

describe('partition editing', () => {
    const a = asset({fileId: 'f1', name: 'A'});
    const b = asset({fileId: 'f2', name: 'B'});
    const c = asset({fileId: 'f3', name: 'C'});
    const [ka, kb, kc] = [memberKey(a), memberKey(b), memberKey(c)];

    it('reads the current layout back as an override', () => {
        const groups = groupExtractedAssets([a, b, c]);
        expect(partitionOf(groups)).toEqual([[ka], [kb], [kc]]);
    });

    it('merges a chip into the cluster of its target', () => {
        expect(movePartition([[ka], [kb], [kc]], [kc], ka)).toEqual([[ka, kc], [kb]]);
    });

    it('does not leave the moved chip behind in its old cluster', () => {
        expect(movePartition([[ka, kb], [kc]], [kb], kc)).toEqual([[ka], [kc, kb]]);
    });

    it('is a no-op when the chip is already with its target', () => {
        expect(movePartition([[ka, kb]], [kb], ka)).toEqual([[ka, kb]]);
    });

    it('extracts a chip into a cluster of its own', () => {
        expect(movePartition([[ka, kb, kc]], [kb], null)).toEqual([[ka, kc], [kb]]);
    });

    it('breaks a whole cluster apart', () => {
        expect(splitPartition([[ka, kb, kc]], [ka, kb, kc])).toEqual([[ka], [kb], [kc]]);
    });

    it('drops clusters emptied by a move', () => {
        expect(movePartition([[ka], [kb]], [kb], ka)).toEqual([[ka, kb]]);
    });
});

describe('groupIdentifiers', () => {
    /** The BTP CUM case: the group legitimately carries two ISINs and must keep both. */
    it('unions the codes of every member without electing one', () => {
        const cum = asset({fileId: 'f1', isin: 'IT0005612345', name: 'BTP Piu Sc Fb33 CUM'});
        const quoted = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
        expect(groupIdentifiers([cum, quoted]).isins).toEqual(['IT0005612345', 'IT0005634792']);
    });

    it('deduplicates case-insensitively and preserves member order', () => {
        const one = asset({fileId: 'f1', isin: 'it0005634792', symbol: 'btp', name: 'BTP Piu'});
        const two = asset({fileId: 'f2', isin: 'IT0005634792', symbol: 'BTP', name: 'BTP PIU'});
        const ids = groupIdentifiers([one, two]);
        expect(ids.isins).toEqual(['it0005634792']);
        expect(ids.symbols).toEqual(['btp']);
        expect(ids.names).toEqual(['BTP Piu']);
    });

    it('skips blanks instead of emitting empty entries', () => {
        expect(groupIdentifiers([asset({fileId: 'f1', isin: '  ', name: 'X'})]).isins).toEqual([]);
    });
});

describe('representativeOf', () => {
    it('prefers the member that carries an ISIN', () => {
        const noIsin = asset({fileId: 'f1', name: 'BTP Piu Sc Fb33'});
        const withIsin = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu'});
        expect(representativeOf([noIsin, withIsin])).toBe(withIsin);
    });

    it('falls back to a ticker before giving up', () => {
        const bare = asset({fileId: 'f1', name: 'Something'});
        const ticker = asset({fileId: 'f2', symbol: 'VWCE', name: 'Vanguard All-World'});
        expect(representativeOf([bare, ticker])).toBe(ticker);
    });

    it('returns the first member when nobody has an identifier', () => {
        const first = asset({fileId: 'f1', name: 'A'});
        expect(representativeOf([first, asset({fileId: 'f2', name: 'B'})])).toBe(first);
    });
});

describe('representativeMap', () => {
    /**
     * The invariant the whole step exists for. The correction step lists one entry per surviving
     * fake id, so if two members of one security kept distinct representatives the user would be
     * shown the same instrument twice and half their rows would land on the wrong half of it.
     */
    it('sends every member of a group to a single survivor', () => {
        const cum = asset({fileId: 'f1', isin: 'IT0005612345', name: 'BTP Piu Sc Fb33 CUM'});
        const quoted = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
        const other = asset({fileId: 'f1', isin: 'IE00B4L5Y983', name: 'iShares Core MSCI World'});

        const groups = groupExtractedAssets([cum, quoted, other]);
        const map = representativeMap(groups);

        expect(new Set([map.get(cum.fakeAssetId), map.get(quoted.fakeAssetId)]).size).toBe(1);
        expect(new Set(map.values()).size).toBe(groups.length);
    });

    it('is total and maps a representative to itself', () => {
        const lone = asset({fileId: 'f1', isin: 'IE00B4L5Y983', name: 'iShares Core MSCI World'});
        const map = representativeMap(groupExtractedAssets([lone]));
        expect(map.get(lone.fakeAssetId)).toBe(lone.fakeAssetId);
    });

    it("follows the user's partition, not the engine's", () => {
        const a = asset({fileId: 'f1', isin: 'IT0005612345', name: 'BTP Piu Sc Fb33 CUM'});
        const b = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
        const split = groupExtractedAssets([a, b], [[memberKey(a)], [memberKey(b)]]);
        const map = representativeMap(split);
        expect(map.get(a.fakeAssetId)).not.toBe(map.get(b.fakeAssetId));
    });
});

/**
 * Electing the leading code is the step's second job, and the BTP is the case that demands it:
 * the placement ISIN cannot be priced, so leaving the order to chance means the created asset
 * quotes nothing.
 */
describe('primary election', () => {
    const cum = asset({fileId: 'f1', isin: 'IT0005612345', name: 'BTP Piu Sc Fb33 CUM'});
    const quoted = asset({fileId: 'f2', isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
    const members = [cum, quoted];
    const signature = clusterSignature(members.map(memberKey));

    it('leaves the provenance order alone when nobody has ruled', () => {
        expect(orderedIdentifiers(members, undefined).isins).toEqual(['IT0005612345', 'IT0005634792']);
    });

    it('moves the elected ISIN in front so every consumer of [0] gets it', () => {
        const map = electPrimary({}, signature, 'isin', 'IT0005634792');
        expect(orderedIdentifiers(members, map[signature]).isins).toEqual(['IT0005634792', 'IT0005612345']);
    });

    it('keeps the codes it did not elect, they are the asset other identifiers', () => {
        const map = electPrimary({}, signature, 'isin', 'IT0005634792');
        expect(orderedIdentifiers(members, map[signature]).isins).toHaveLength(2);
    });

    it('elects per kind without disturbing the others', () => {
        let map = electPrimary({}, signature, 'isin', 'IT0005634792');
        map = electPrimary(map, signature, 'name', 'BTP Piu Sc Fb33');
        expect(map[signature]).toEqual({isin: 'IT0005634792', name: 'BTP Piu Sc Fb33'});
    });

    it('ignores an election naming a value the group no longer holds', () => {
        const map = electPrimary({}, signature, 'isin', 'XX0000000000');
        expect(orderedIdentifiers(members, map[signature]).isins).toEqual(['IT0005612345', 'IT0005634792']);
    });

    it('survives the fake ids being reallocated, which is why it is keyed by signature', () => {
        const reparsed = members.map((m, i) => ({...m, fakeAssetId: -5000 - i}));
        expect(groupSignature({members: reparsed})).toBe(signature);
    });

    it('recognises the elected value case-insensitively', () => {
        const map = electPrimary({}, signature, 'isin', 'it0005634792');
        expect(isPrimary(map[signature], 'isin', 'IT0005634792')).toBe(true);
        expect(isPrimary(map[signature], 'isin', 'IT0005612345')).toBe(false);
    });

    it('reports whether a kind has been ruled on at all', () => {
        expect(hasElection(undefined, 'isin')).toBe(false);
        expect(hasElection(electPrimary({}, signature, 'isin', 'IT0005634792')[signature], 'isin')).toBe(true);
        expect(hasElection(electPrimary({}, signature, 'isin', 'IT0005634792')[signature], 'symbol')).toBe(false);
    });
});

/**
 * The four Crédit Agricole reports overlap in time, so one bond is extracted four times with the
 * same ISIN: six pairwise links, six identical sentences. The summary is what keeps the one line
 * that differs visible.
 */
describe('link summary', () => {
    it('says a reason once however many pairs carry it', () => {
        const files = ['f1', 'f2', 'f3', 'f4'].map((fileId) => asset({fileId, isin: 'IT0005425753', name: 'BTP 17-11-28 FUT CUM'}));
        const group = groupExtractedAssets(files)[0];
        expect(group.links.length).toBeGreaterThan(1);
        const summary = summariseLinks(group);
        expect(summary).toHaveLength(1);
        expect(summary[0].reason).toBe('isin');
        expect(summary[0].coversAll).toBe(true);
    });

    it('keeps the reason that does not cover everyone, and says who it is about', () => {
        const coded = ['f1', 'f2'].map((fileId) => asset({fileId, isin: 'IT0005425753', name: 'BTP 17-11-28 FUT CUM'}));
        const bare = asset({fileId: 'f3', isin: null, name: 'BTP 17-11-28 FUT CUM'});
        const group = groupExtractedAssets([...coded, bare])[0];
        const summary = summariseLinks(group);

        // The name reaches all three; the ISIN reaches only the two that carry one. Saying so is
        // the whole point: it tells the user the third extraction has no code of its own.
        const byName = summary.find((s) => s.reason === 'name');
        const byIsin = summary.find((s) => s.reason === 'isin');
        expect(byName?.coversAll).toBe(true);
        expect(byIsin?.coversAll).toBe(false);
        expect(byIsin?.members).not.toContain(bare.fakeAssetId);
    });

    it('puts the reason that explains the most in front', () => {
        const coded = ['f1', 'f2'].map((fileId) => asset({fileId, isin: 'IT0005425753', name: 'BTP 17-11-28 FUT CUM'}));
        const bare = asset({fileId: 'f3', isin: null, name: 'BTP 17-11-28 FUT CUM'});
        expect(summariseLinks(groupExtractedAssets([...coded, bare])[0])[0].coversAll).toBe(true);
    });

    it('reports the weakest evidence of a reason, not the flattering one', () => {
        const group = {
            members: [asset({fileId: 'f1'}), asset({fileId: 'f2'})],
            links: [
                {from: 1, to: 2, reason: 'name' as const, strength: 'weak' as const, score: 0.94},
                {from: 1, to: 2, reason: 'name' as const, strength: 'weak' as const, score: 1},
            ],
        };
        expect(summariseLinks(group)[0].score).toBe(0.94);
    });

    it('has nothing to say about a lone asset', () => {
        const group = groupExtractedAssets([asset({fileId: 'f1', isin: 'IE00B4L5Y983'})])[0];
        expect(summariseLinks(group)).toEqual([]);
    });
});

describe('rename', () => {
    const a = asset({fileId: 'f1', isin: 'IT0005425753', name: 'BTP 17-11-28 FUT CUM'});
    const b = asset({fileId: 'f2', isin: 'IT0005425753', name: 'BTP 17/11/28'});
    const signature = clusterSignature([a, b].map(memberKey));

    it('lets a name nobody extracted lead, because that is what renaming is', () => {
        const map = electPrimary({}, signature, 'name', 'BTP Nov 2028');
        expect(orderedIdentifiers([a, b], map[signature]).names[0]).toBe('BTP Nov 2028');
    });

    it('keeps the extracted names behind it, they are still search keys', () => {
        const map = electPrimary({}, signature, 'name', 'BTP Nov 2028');
        expect(orderedIdentifiers([a, b], map[signature]).names).toHaveLength(3);
    });

    it('refuses to invent a code the files never carried', () => {
        const map = electPrimary({}, signature, 'isin', 'XX0000000000');
        expect(orderedIdentifiers([a, b], map[signature]).isins).toEqual(['IT0005425753']);
    });
});
