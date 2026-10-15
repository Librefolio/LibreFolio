/**
 * allocationHierarchy.test.ts — Unit tests for `buildAllocationHierarchy()`.
 *
 * The builder answers two questions at once, and this file holds it to both:
 *
 * 1. **What order?** Groups by total, largest first, a tie in the order the entries came in (the
 *    sort is stable: a tie must not repaint the chart for no reason); inside a group the
 *    unspecialised member first, then the others by weight. Two members of one family on opposite
 *    sides of the circle read as an accident.
 * 2. **What colour?** The group's own, by key: GR1 of the designer's round 2 (D-T17), a colour per
 *    key and never per rank, so `ETF` is the same blue in the pie and in the history, first or
 *    fifth, in every portfolio. The builder asks `colorOf` for it. Every member after the first is
 *    a shade of it, `shade(group colour, depth)` (GR4), and a lone member is never shaded: a shade
 *    means something only beside the colour it comes from.
 *
 * Which colour a key has, and how a shade is mixed, are not this module's business:
 * `categoryColor` (`lib/theme/chartCategories`) and `familyShade` (`lib/theme/chartShades`) are
 * pinned by the theme's own tests. So most tests here stub both with functions whose answer spells
 * the question — `colour(ETF)`, `colour(ETF)·2` — and a colour is read as the call that produced
 * it: a wrong key or a wrong depth cannot hide behind two hex values that look alike. Every call is
 * recorded too, because what the builder asks is part of the contract. One block wires the real
 * `categoryColor` and `familyShade` exactly as both allocation charts do, in both themes, so the
 * stubs cannot drift from the functions they stand for.
 *
 * `resolvePrimary` is a **stub** as well. The real `primaryAssetType` lives in
 * `$lib/utils/assetTypes`, which reads the generated Zodios schemas at module load — importing it
 * would drag a gitignored build artifact into a unit test. The module under test takes the
 * function as an option precisely so this file does not have to. The exception is the last block:
 * it imports K's taxonomy for real, checks the stub against K2 on every type the charts can
 * receive, and builds the families the pie draws through `assetTypeFamily` itself.
 *
 * No runes, no DOM: this stays in the default `node` environment.
 *
 * @module components/charts/__tests__/allocationHierarchy.test
 */
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe, expect, it, vi} from 'vitest';

import {categoryColor} from '$lib/theme/chartCategories';
import {familyShade, shadePoles} from '$lib/theme/chartShades';
import {chartRoles} from '$lib/theme/roleColors';

import {buildAllocationHierarchy, type AllocationHierarchyOptions} from '../allocationHierarchy';

// =============================================================================
// Fixtures
// =============================================================================

/**
 * Stub for contract K2 (`primaryAssetType`), reproducing its **real** semantics.
 *
 * Five ETF subtypes and real-estate crowdfunding fold onto the base type they
 * contain. Everything else — known enum member, unknown key, or the synthetic
 * `"Liquidity"` bucket — maps to **itself upper-cased**, never to `OTHER`: the
 * real implementation upper-cases *before* the lookup and returns that normalised
 * value even when the lookup misses, so `"Liquidity"` comes back as `"LIQUIDITY"`.
 * Only `null`, `undefined` and blank fall back to `OTHER`.
 *
 * A copy can drift, so the last block, which imports K for real, checks the stub
 * against it on every type the charts can receive: a green test that misstates its
 * own contract misinforms with more authority than prose.
 */
const SUBTYPE_PARENT: Record<string, string> = {
    ETF_STOCK: 'STOCK',
    ETF_BOND: 'BOND',
    ETF_COMMODITY: 'COMMODITY',
    ETF_REAL_ESTATE: 'REAL_ESTATE',
    ETF_CRYPTO: 'CRYPTO',
    CROWDFUND_REAL_ESTATE: 'REAL_ESTATE',
};

const resolvePrimary = (key: string | null | undefined): string => {
    const raw = (key ?? '').trim().toUpperCase();
    if (!raw) return 'OTHER';
    return SUBTYPE_PARENT[raw] ?? raw;
};

interface Payload {
    id: string;
}

function entry(key: string, weight: number): {key: string; weight: number; item: Payload} {
    return {key, weight, item: {id: `item-${key}`}};
}

/** The stand-in for `colorOf` (`categoryColor` in the charts): a colour that names the key it was asked for. */
const colourOf = (primary: string): string => `colour(${primary})`;

/** The stand-in for `shade` (`familyShade` in the charts): a colour that names the base it was given and the depth. */
const shadeOf = (base: string, depth: number): string => `${base}·${depth}`;

/** The builder's options, with both stand-ins recording every call. */
function stubbed(resolve: (key: string) => string = resolvePrimary) {
    const colorOf = vi.fn(colourOf);
    const shade = vi.fn(shadeOf);
    const opts: AllocationHierarchyOptions = {resolvePrimary: resolve, colorOf, shade};
    return {opts, colorOf, shade};
}

/** The builder on the stand-ins, for the tests about order and grouping alone. */
function build(entries: ReturnType<typeof entry>[], resolve: (key: string) => string = resolvePrimary) {
    return buildAllocationHierarchy(entries, stubbed(resolve).opts);
}

// =============================================================================
// The order of the groups
// =============================================================================

describe('buildAllocationHierarchy — the order of the groups', () => {
    // Deliberately includes a three-way tie at 50: a sort that is not stable would
    // shuffle them, and the chart would repaint for no reason.
    const entries = [entry('STOCK', 100), entry('BOND', 50), entry('CRYPTO', 50), entry('CASH', 50), entry('COMMODITY', 20)];

    it('orders groups by total, largest first, a tie keeping the order the entries came in', () => {
        const actual = build(entries);

        // Positive barrier: a bug returning `[]` would satisfy an element-wise check by iterating zero times.
        expect(actual).toHaveLength(entries.length);
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'BOND', 'CRYPTO', 'CASH', 'COMMODITY']);
        expect(actual.map((r) => r.item)).toEqual(['STOCK', 'BOND', 'CRYPTO', 'CASH', 'COMMODITY'].map((key) => entries.find((e) => e.key === key)!.item));
    });

    it('breaks ties by input order, not by name — reversing the tied inputs reverses the output', () => {
        const reordered = [entry('STOCK', 100), entry('CASH', 50), entry('CRYPTO', 50), entry('BOND', 50), entry('COMMODITY', 20)];
        const actual = build(reordered);

        expect(actual).toHaveLength(5);
        // Had the sort been alphabetical, or unstable-but-canonical, this would
        // still read BOND, CRYPTO, CASH as in the test above.
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'CASH', 'CRYPTO', 'BOND', 'COMMODITY']);
    });

    it('leaves every entry at depth 0, in its own colour, when each one is its own group', () => {
        const {opts, shade} = stubbed();
        const actual = buildAllocationHierarchy(entries, opts);

        expect(actual).toHaveLength(5);
        expect(actual.map((r) => r.depth)).toEqual([0, 0, 0, 0, 0]);
        expect(actual.map((r) => r.groupSize)).toEqual([1, 1, 1, 1, 1]);
        expect(actual.map((r) => r.color)).toEqual(actual.map((r) => colourOf(r.key)));
        expect(shade, 'a group of one was shaded').not.toHaveBeenCalled();
    });

    it('accepts zero weights without reordering into nonsense', () => {
        const actual = build([entry('STOCK', 0), entry('BOND', 0), entry('CASH', 5)]);

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['CASH', 'STOCK', 'BOND']);
    });
});

// =============================================================================
// A subtype sits inside its group
// =============================================================================

describe('buildAllocationHierarchy — a subtype sits inside its group', () => {
    it('places ETF_STOCK immediately after STOCK: groups rank by their total, not by their heaviest member', () => {
        const actual = build([entry('BOND', 90), entry('ETF_STOCK', 40), entry('CASH', 80), entry('STOCK', 60)]);

        expect(actual).toHaveLength(4);
        // STOCK+ETF_STOCK = 100 > BOND = 90 > CASH = 80. ETF_STOCK (40) is individually
        // the lightest entry and still lands second — that is the whole point of grouping.
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK', 'BOND', 'CASH']);
        expect(actual.map((r) => r.primary)).toEqual(['STOCK', 'STOCK', 'BOND', 'CASH']);
        expect(actual.map((r) => r.depth)).toEqual([0, 1, 0, 0]);
        // The pure member wears the group's own colour verbatim; the subtype the first shade of it.
        expect(actual.map((r) => r.color)).toEqual([colourOf('STOCK'), shadeOf(colourOf('STOCK'), 1), colourOf('BOND'), colourOf('CASH')]);
    });

    it('keeps the pure member first even when the subtype outweighs it', () => {
        const actual = build([entry('ETF_STOCK', 900), entry('STOCK', 1)]);

        expect(actual).toHaveLength(2);
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK']);
        expect(actual.map((r) => r.depth)).toEqual([0, 1]);
        expect(actual.map((r) => r.color)).toEqual([colourOf('STOCK'), shadeOf(colourOf('STOCK'), 1)]);
    });

    it('orders several subtypes of one group by weight after the pure member, one depth each', () => {
        const resolveWithExtra = (key: string) => (key === 'STOCK_OPTION' ? 'STOCK' : resolvePrimary(key));
        const actual = build([entry('ETF_STOCK', 30), entry('STOCK', 10), entry('STOCK_OPTION', 50)], resolveWithExtra);

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'STOCK_OPTION', 'ETF_STOCK']);
        expect(actual.map((r) => r.depth)).toEqual([0, 1, 2]);
        expect(actual.map((r) => r.color)).toEqual([colourOf('STOCK'), shadeOf(colourOf('STOCK'), 1), shadeOf(colourOf('STOCK'), 2)]);
    });
});

// =============================================================================
// GR1 — a colour per key, never per rank
// =============================================================================

describe('buildAllocationHierarchy — a colour per key, never per rank (GR1)', () => {
    it('gives a group the colour colorOf gives its key, wherever the group ranks', () => {
        const leading = build([entry('ETF', 50), entry('BOND', 30), entry('STOCK', 20)]);
        const trailing = build([entry('STOCK', 60), entry('BOND', 30), entry('ETF', 10)]);

        // Barrier: ETF and STOCK really trade places between the two portfolios, so a colour handed
        // out by rank would differ below.
        expect(leading.map((r) => r.key)).toEqual(['ETF', 'BOND', 'STOCK']);
        expect(trailing.map((r) => r.key)).toEqual(['STOCK', 'BOND', 'ETF']);

        const colourIn = (rows: typeof leading, key: string) => rows.find((r) => r.key === key)?.color;
        for (const key of ['ETF', 'BOND', 'STOCK']) {
            expect({leading: colourIn(leading, key), trailing: colourIn(trailing, key)}, key).toEqual({leading: colourOf(key), trailing: colourOf(key)});
        }
    });

    it('asks colorOf by group key — upper-cased, as the group is keyed — and never by a member key', () => {
        const {opts, colorOf} = stubbed();
        const actual = buildAllocationHierarchy([entry('Liquidity', 40), entry('ETF_STOCK', 25), entry('STOCK', 35), entry('BOND', 10)], opts);

        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK', 'Liquidity', 'BOND']);
        // The engine's Title Case bucket is asked for under its group key, the subtype never: it
        // wears its group's colour, shaded.
        expect(new Set(colorOf.mock.calls.map(([key]) => key))).toEqual(new Set(['STOCK', 'LIQUIDITY', 'BOND']));
        expect(actual.map((r) => r.color)).toEqual([colourOf('STOCK'), shadeOf(colourOf('STOCK'), 1), colourOf('LIQUIDITY'), colourOf('BOND')]);
    });

    it('gives every group its own key’s colour however many groups there are: no palette runs out, nothing repeats', () => {
        // Twenty groups: more than the fourteen slots the palettes of the rank-based rule held.
        const entries = Array.from({length: 20}, (_, index) => entry(`GROUP_${index}`, 100 - index));
        const actual = build(entries);

        expect(actual).toHaveLength(20);
        expect(actual.map((r) => r.color)).toEqual(entries.map((e) => colourOf(e.key)));
    });
});

// =============================================================================
// GR4 — a shade only beside the colour it comes from
// =============================================================================

describe('buildAllocationHierarchy — shades (GR4)', () => {
    it('calls shade with (the group colour, the depth) for every member after the first, and for nothing else', () => {
        // The family K2 makes of REAL_ESTATE, input order and weight order disagreeing, beside two
        // groups of one.
        const {opts, shade} = stubbed();
        const actual = buildAllocationHierarchy([entry('ETF_REAL_ESTATE', 10), entry('BOND', 40), entry('REAL_ESTATE', 20), entry('CROWDFUND_REAL_ESTATE', 30), entry('STOCK', 15)], opts);

        expect(actual.map((r) => `${r.key}@${r.depth}`)).toEqual(['REAL_ESTATE@0', 'CROWDFUND_REAL_ESTATE@1', 'ETF_REAL_ESTATE@2', 'BOND@0', 'STOCK@0']);
        expect(shade.mock.calls).toEqual([
            [colourOf('REAL_ESTATE'), 1],
            [colourOf('REAL_ESTATE'), 2],
        ]);
        expect(actual.map((r) => r.color)).toEqual([colourOf('REAL_ESTATE'), shadeOf(colourOf('REAL_ESTATE'), 1), shadeOf(colourOf('REAL_ESTATE'), 2), colourOf('BOND'), colourOf('STOCK')]);
    });

    it('never shades a group of one — a lone subtype included', () => {
        const {opts, shade} = stubbed();
        const actual = buildAllocationHierarchy([entry('ETF_STOCK', 30), entry('BOND', 20), entry('Liquidity', 5)], opts);

        expect(actual).toHaveLength(3);
        const lone = actual.find((r) => r.key === 'ETF_STOCK');
        expect(lone, 'ETF_STOCK must survive the grouping').toBeDefined();
        expect({primary: lone!.primary, depth: lone!.depth, groupSize: lone!.groupSize, color: lone!.color}).toEqual({primary: 'STOCK', depth: 0, groupSize: 1, color: colourOf('STOCK')});
        expect(shade, 'a group of one was shaded').not.toHaveBeenCalled();
    });

    it('without its pure member, the heaviest subtype takes depth 0 and the group colour, the next a shade each', () => {
        // What the hierarchy hands both charts. The pie's outer ring shades by rank among the
        // subtypes instead (`allocationRings.test.ts`); the history draws one area per family.
        const {opts, shade} = stubbed((key) => (key === 'STOCK_OPTION' ? 'STOCK' : resolvePrimary(key)));
        const actual = buildAllocationHierarchy([entry('ETF_STOCK', 30), entry('STOCK_OPTION', 50), entry('BOND', 10)], opts);

        expect(actual.map((r) => `${r.key}@${r.depth}`)).toEqual(['STOCK_OPTION@0', 'ETF_STOCK@1', 'BOND@0']);
        expect(actual.map((r) => r.color)).toEqual([colourOf('STOCK'), shadeOf(colourOf('STOCK'), 1), colourOf('BOND')]);
        expect(shade.mock.calls).toEqual([[colourOf('STOCK'), 1]]);
    });
});

// =============================================================================
// Grouping semantics
// =============================================================================

describe('buildAllocationHierarchy — grouping', () => {
    it('groups REAL_ESTATE with ETF_REAL_ESTATE, and never produces "REAL"', () => {
        const actual = build([entry('ETF_REAL_ESTATE', 30), entry('REAL_ESTATE', 70), entry('BOND', 20)]);

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['REAL_ESTATE', 'ETF_REAL_ESTATE', 'BOND']);

        // Positive form first: the primary is the *whole* underscored key.
        expect(actual[0].primary).toBe('REAL_ESTATE');
        expect(actual[1].primary).toBe('REAL_ESTATE');
        expect(actual[0].groupSize).toBe(2);
        expect(actual[1].groupSize).toBe(2);

        // Then the guard against a future `key.split('_')[0]`, which would
        // bucket these under "REAL" — and quietly sweep in any other
        // REAL_-prefixed type.
        expect(actual.map((r) => r.primary)).not.toContain('REAL');
    });

    it('maps an unknown key to itself, forming its own group — never to OTHER', () => {
        const actual = build([entry('WIDGETS', 50), entry('STOCK', 80), entry('ETF_STOCK', 10)]);

        expect(actual).toHaveLength(3);

        const widgets = actual.find((r) => r.key === 'WIDGETS');
        expect(widgets, 'WIDGETS must survive the grouping').toBeDefined();
        expect(widgets!.primary).toBe('WIDGETS');
        expect(widgets!.groupSize).toBe(1);
        expect(widgets!.depth).toBe(0);
        expect(widgets!.primaryTotal).toBe(50);
        expect(widgets!.color).toBe(colourOf('WIDGETS'));

        expect(actual.map((r) => r.primary)).not.toContain('OTHER');
    });

    it('groups the synthetic "Liquidity" bucket on its own, in its own colour, unshaded', () => {
        // `portfolio_engine.py` emits this Title Case key alongside the SCREAMING_CASE enum
        // members. It must be a first-class group, not a subtype of anything and not a shaded
        // straggler.
        const actual = build([entry('Liquidity', 40), entry('STOCK', 90), entry('ETF_STOCK', 20)]);

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK', 'Liquidity']);

        const liquidity = actual[2];
        expect(liquidity.key).toBe('Liquidity'); // original casing preserved
        expect(liquidity.primary).toBe('LIQUIDITY'); // group key is upper-cased
        expect(liquidity.groupSize).toBe(1);
        expect(liquidity.depth).toBe(0);
        expect(liquidity.color).toBe(colourOf('LIQUIDITY')); // its key's own, not a shade
        expect(liquidity.primaryTotal).toBe(40);
    });

    it('case-folds "Liquidity" and "LIQUIDITY" into one bucket, with neither demoted for its casing', () => {
        // Pinning the *documented* behaviour: `sameKey()` is deliberately case-insensitive, and
        // the group key is upper-cased, so a Title Case key is recognised as its group's pure
        // member instead of being pushed behind a differently-cased sibling. The two do not become
        // rival groups, and neither is dropped.
        const actual = build([entry('LIQUIDITY', 15), entry('Liquidity', 40)]);

        expect(actual).toHaveLength(2);
        expect(new Set(actual.map((r) => r.primary))).toEqual(new Set(['LIQUIDITY']));
        expect(actual.map((r) => r.groupSize)).toEqual([2, 2]);
        expect(actual.map((r) => r.primaryTotal)).toEqual([55, 55]);
        // Both are "pure" by sameKey(), so the tie-break is weight — casing never decides the order.
        expect(actual.map((r) => r.key)).toEqual(['Liquidity', 'LIQUIDITY']);
        expect(actual.map((r) => r.depth)).toEqual([0, 1]);
        expect(actual.map((r) => r.color)).toEqual([colourOf('LIQUIDITY'), shadeOf(colourOf('LIQUIDITY'), 1)]);
    });
});

// =============================================================================
// groupSize / primaryTotal
// =============================================================================

describe('buildAllocationHierarchy — group metadata', () => {
    it('reports the summed group weight and member count on every row', () => {
        const actual = build([entry('STOCK', 60), entry('ETF_STOCK', 40), entry('BOND', 70), entry('ETF_BOND', 5), entry('CASH', 30)]);

        expect(actual).toHaveLength(5);
        // Group totals: STOCK 100 > BOND 75 > CASH 30.
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK', 'BOND', 'ETF_BOND', 'CASH']);
        expect(actual.map((r) => r.primaryTotal)).toEqual([100, 100, 75, 75, 30]);
        expect(actual.map((r) => r.groupSize)).toEqual([2, 2, 2, 2, 1]);

        // A singleton reports 1 and its own weight.
        const cash = actual[4];
        expect(cash.key).toBe('CASH');
        expect(cash.groupSize).toBe(1);
        expect(cash.primaryTotal).toBe(30);
    });

    it('carries the caller payload through untouched', () => {
        const stock = entry('STOCK', 10);
        const etf = entry('ETF_STOCK', 5);
        const actual = build([stock, etf]);

        expect(actual).toHaveLength(2);
        expect(actual[0].item).toBe(stock.item);
        expect(actual[1].item).toBe(etf.item);
    });
});

// =============================================================================
// Degenerate inputs
// =============================================================================

describe('buildAllocationHierarchy — degenerate inputs', () => {
    it('returns [] for empty entries, and asks for no colour', () => {
        const {opts, colorOf, shade} = stubbed();

        expect(buildAllocationHierarchy([], opts)).toEqual([]);
        expect(colorOf).not.toHaveBeenCalled();
        expect(shade).not.toHaveBeenCalled();
    });
});

// =============================================================================
// Wired to the real colours, as both allocation charts wire them
// =============================================================================

/** `__tests__` → `charts` → `components` → `lib`, then `api/generated.ts`. */
const GENERATED_TS = fileURLToPath(new URL('../../../api/generated.ts', import.meta.url));

/** The two themes, as the charts read them off the `dark` class of <html>. */
const THEMES = [
    {theme: 'light', dark: false},
    {theme: 'dark', dark: true},
] as const;

describe('buildAllocationHierarchy — wired to the real colours (categoryColor, familyShade)', () => {
    /**
     * `assetTypes.ts` reads the generated client at module load, so the import is dynamic, local to
     * this block, and follows a check that the file exists: a missing client is reported with the
     * command that fixes it, never skipped.
     */
    async function importTaxonomy() {
        expect(existsSync(GENERATED_TS), "src/lib/api/generated.ts is absent, so assetTypes.ts cannot be imported and K's families cannot be built. Run `./dev.py api sync`.").toBe(true);
        const assetTypes = await import('$lib/utils/assetTypes');
        return {primaryAssetType: assetTypes.primaryAssetType, assetTypeFamily: assetTypes.assetTypeFamily, ASSET_TYPES: [...assetTypes.ASSET_TYPES] as string[]};
    }

    /** The members of `family` under `resolve`, read off the enum: its pure member first, then the others in enum order. */
    function membersOf(types: readonly string[], resolve: (key: string) => string, family: string): string[] {
        const members = types.filter((type) => resolve(type) === family);
        return [...members.filter((type) => type === family), ...members.filter((type) => type !== family)];
    }

    it('checks the K2 stub of the tests above against primaryAssetType, on every type the charts can receive', async () => {
        const {primaryAssetType, ASSET_TYPES} = await importTaxonomy();

        // `by_type` carries the enum values and the synthetic cash bucket, in the engine's spelling.
        const domain = [...ASSET_TYPES, 'Liquidity'];
        // Anti-vacuous: the enum was read, with the subtypes that move and the one K2 keeps as itself.
        expect(domain).toEqual(expect.arrayContaining(['STOCK', 'ETF_STOCK', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE', 'Liquidity']));

        const disagreements = domain.filter((type) => resolvePrimary(type) !== primaryAssetType(type)).map((type) => `${type}: stub ${resolvePrimary(type)}, primaryAssetType ${primaryAssetType(type)}`);
        expect(disagreements, 'the K2 stub of this file no longer mirrors primaryAssetType: the builder tests above would check a grouping no chart draws').toEqual([]);
    });

    it.each(THEMES)('$theme theme: by vehicle, each family in categoryColor of its key and each member after the first a familyShade of it by depth — the ETF family seven colours apart, the cash bucket in the Liquidity colour, no two families alike', async ({dark}) => {
        const {assetTypeFamily, ASSET_TYPES} = await importTaxonomy();
        const etf = membersOf(ASSET_TYPES, assetTypeFamily, 'ETF');
        // Anti-vacuous: K files its subtypes under ETF, with the generic ETF leading, and more of
        // them than one pole holds — so shades on both sides of the family colour are drawn.
        expect(etf[0]).toBe('ETF');
        expect(etf.length, 'the ETF family by vehicle holds four members or fewer: both poles of GR4 are no longer reached').toBeGreaterThan(4);

        // The family heaviest, its members by descending weight so the depth follows K's order;
        // then a plain family, the engine's cash bucket, and a family of two by vehicle.
        const entries = [...etf.map((key, rank) => entry(key, 10 * (etf.length - rank))), entry('BOND', 25), entry('Liquidity', 7), entry('CROWDFUND', 3), entry('CROWDFUND_REAL_ESTATE', 2)];
        // As the pie wires it: the card the chart sits on is the dark theme's near pole. Read through the bridge,
        // which in a node run (no document, no reader) answers the stand-in of the theme.
        const poles = shadePoles(dark, chartRoles(dark).color('--lf-surface-card'));
        const actual = buildAllocationHierarchy(entries, {
            resolvePrimary: assetTypeFamily,
            colorOf: (primary) => categoryColor('type', primary, dark),
            shade: (base, rank) => familyShade(base, rank, poles),
        });

        // Barrier: the rows are the ones meant, each family whole and in place.
        expect(actual.map((r) => r.primary)).toEqual([...etf.map(() => 'ETF'), 'BOND', 'LIQUIDITY', 'CROWDFUND', 'CROWDFUND']);
        expect(actual.map((r) => r.key)).toEqual([...etf, 'BOND', 'Liquidity', 'CROWDFUND', 'CROWDFUND_REAL_ESTATE']);

        expect(
            actual.map((r) => r.color),
            'a family not in its key’s colour, or a member not shaded from it by its depth',
        ).toEqual(actual.map((r) => (r.depth === 0 ? categoryColor('type', r.primary, dark) : familyShade(categoryColor('type', r.primary, dark), r.depth, poles))));

        // The engine spells the bucket in Title Case; the group key is upper-cased, and the lookup ignores case.
        expect(actual.find((r) => r.key === 'Liquidity')?.color).toBe(categoryColor('type', 'Liquidity', dark));
        // `#rrggbb` throughout: the history's area fill appends its alpha to it (`withHexAlpha(color, '88')`).
        expect(actual.filter((r) => !/^#[0-9a-f]{6}$/i.test(r.color)).map((r) => `${r.key}: ${r.color}`)).toEqual([]);

        const etfColours = actual.filter((r) => r.primary === 'ETF').map((r) => r.color.toLowerCase());
        expect(new Set(etfColours).size, `members of the ETF family sharing a colour: ${etfColours.join(', ')}`).toBe(etf.length);
        const familyColours = actual.filter((r) => r.depth === 0).map((r) => `${r.primary} ${r.color.toLowerCase()}`);
        expect(new Set(familyColours.map((line) => line.split(' ')[1])).size, `families sharing a colour: ${familyColours.join(', ')}`).toBe(familyColours.length);
    });
});
