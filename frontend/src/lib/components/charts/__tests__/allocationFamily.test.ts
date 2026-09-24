/**
 * allocationFamily.test.ts — the family an asset type belongs to in the "by type" allocation pie,
 * and the icons its tooltip shows (`charts/allocationFamily.ts`).
 *
 * ## The decision these tests pin
 *
 * On 24/09/2026 the developer reviewed the two-ring donut of D72 (review R12) and chose option B,
 * **by vehicle**: every ETF subtype belongs to the ETF family, and the outer ring says what kind
 * of ETF it is — "ETF generico" + "ETF azionario". Until then the pie grouped by **content**
 * through contract K2 (`primaryAssetType`: `ETF_STOCK` under STOCK). That is now wrong for the
 * pie and still right for the allocation history chart, which keeps K2 — so the last test of the
 * first block checks that K2 did not move with the pie.
 *
 * `allocationFamily` only states which parent the pie uses: the list of subtypes is K's
 * (`ETF_SUBTYPES` / `isEtfSubtype`). The tests therefore iterate K's list, not a copy of it — a
 * seventh subtype must land in the ETF family without anyone touching this file — and anchor it on
 * two members known to be there, so an empty or truncated list cannot turn the loop into a green
 * that checked nothing. No count is asserted: the list is expected to grow.
 *
 * ## `'Liquidity'`, on its own
 *
 * The engine injects the cash bucket into `by_type` as the Title Case `"Liquidity"`, which is not
 * an `AssetType`; the hierarchy keys families upper-cased, so the resolver must answer
 * `'LIQUIDITY'`. The case is pinned explicitly because `allocationFamily` is due to become K's
 * `assetTypeFamily` (confirmed by K on 24/09, same normalisation): the swap is one line, and this
 * is the test that says the cash slice survived it.
 *
 * ## The tooltip icons
 *
 * `allocationTypeIcons` shows the icon of the vehicle and, when it says something more, the icon
 * of the content: `ETF_STOCK` wears the ETF icon with the stock icon small beside it (R16's
 * composite, asked for in the review of R12). When the content would repeat the main icon — the
 * generic ETF, `ETF_MONETARY` (which K2 keeps as itself), a base type, the cash bucket — a second
 * copy of the same picture would be noise, so there is none. Expected icons are K's own
 * `getAssetTypeIconUrl`, so a test says "the ETF icon" rather than a file name; a barrier proves
 * those icons are distinct from each other and from the fallback, so no equality below can hold by
 * coincidence.
 *
 * ## Why the import is dynamic
 *
 * `allocationFamily.ts` imports K's `assetTypes.ts`, which reads the generated Zodios schemas
 * (`$lib/api/generated`, gitignored, written by `./dev.py api sync`) at module load. As in
 * `assetTypeTables.test.ts`, the modules are imported inside the tests, after asserting that the
 * generated file exists: a missing file is reported, never skipped — in a summary line a skipped
 * check and a satisfied one are the same absence of red.
 *
 * No DOM, no store, no server: this stays in the default `node` environment.
 *
 * @module components/charts/__tests__/allocationFamily.test
 */
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

/** `__tests__` → `charts` → `components` → `lib`, then `api/generated.ts`. */
const GENERATED_TS = fileURLToPath(new URL('../../../api/generated.ts', import.meta.url));

/** The module under test and K's exports it is built from. */
async function importModules() {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and allocationFamily.ts with it — cannot be imported. Run `./dev.py api sync`.').toBe(true);
    const [family, assetTypes] = await Promise.all([import('../allocationFamily'), import('$lib/utils/assetTypes')]);
    expect(typeof family.allocationFamily, 'charts/allocationFamily.ts no longer exports allocationFamily').toBe('function');
    expect(typeof family.allocationTypeIcons, 'charts/allocationFamily.ts no longer exports allocationTypeIcons').toBe('function');
    return {
        allocationFamily: family.allocationFamily,
        allocationTypeIcons: family.allocationTypeIcons,
        ASSET_TYPES: [...assetTypes.ASSET_TYPES] as string[],
        ETF_SUBTYPES: assetTypes.ETF_SUBTYPES,
        primaryAssetType: assetTypes.primaryAssetType,
        getAssetTypeIconUrl: assetTypes.getAssetTypeIconUrl,
    };
}

// =============================================================================
// allocationFamily — the vehicle, not the content
// =============================================================================

describe('allocationFamily — the pie groups by vehicle (R12, option B)', () => {
    it('puts every ETF subtype K lists into the ETF family', async () => {
        const {allocationFamily, ETF_SUBTYPES} = await importModules();

        // Anti-vacuous: K's list was read, and it holds the developer's subtype and the one K2 keeps
        // as itself — the subtype a content resolver would leave outside the family.
        expect(ETF_SUBTYPES).toEqual(expect.arrayContaining(['ETF_STOCK', 'ETF_MONETARY']));

        const strays = ETF_SUBTYPES.filter((type) => allocationFamily(type) !== 'ETF').map((type) => `${type} → ${allocationFamily(type)}`);
        expect(strays, 'ETF subtypes outside the ETF family: the pie would draw them as families of their own, apart from the ETF they are').toEqual([]);
    });

    it("keeps the generic 'ETF' as the ETF family itself", async () => {
        const {allocationFamily} = await importModules();

        expect(allocationFamily('ETF')).toBe('ETF');
    });

    it('maps every other asset type to itself', async () => {
        const {allocationFamily, ASSET_TYPES, ETF_SUBTYPES} = await importModules();
        const others = ASSET_TYPES.filter((type) => !ETF_SUBTYPES.includes(type));

        // Anti-vacuous: the enum was read and the subtypes came out of it. REAL_ESTATE is here on
        // purpose — it has an underscore, and it is what ETF_REAL_ESTATE contains: a rule keyed on
        // either would move it.
        expect(others).toEqual(expect.arrayContaining(['STOCK', 'ETF', 'BOND', 'CROWDFUND', 'REAL_ESTATE', 'OTHER']));

        const moved = others.filter((type) => allocationFamily(type) !== type).map((type) => `${type} → ${allocationFamily(type)}`);
        expect(moved, 'asset types the pie would fold into another family').toEqual([]);
    });

    it("answers 'LIQUIDITY' for the engine's Title Case cash bucket 'Liquidity'", async () => {
        const {allocationFamily} = await importModules();

        expect(allocationFamily('Liquidity')).toBe('LIQUIDITY');
    });

    it("folds '', whitespace, null and undefined to 'OTHER'", async () => {
        const {allocationFamily} = await importModules();
        const blanks: Array<string | null | undefined> = ['', '  ', null, undefined];

        const misfolded = blanks.filter((input) => allocationFamily(input) !== 'OTHER').map((input) => `${JSON.stringify(input) ?? 'undefined'} → ${JSON.stringify(allocationFamily(input))}`);
        expect(misfolded, 'blank types must fall into OTHER: an empty family key matches no label, no icon and no palette slot').toEqual([]);
    });

    it("contrast control: K2 still groups by content — primaryAssetType('ETF_STOCK') is 'STOCK'", async () => {
        const {allocationFamily, primaryAssetType} = await importModules();

        // The pie changed its own resolver, not K2: the allocation history chart still reads an
        // equity ETF as equity. The same input, two answers — which is the whole decision.
        expect(primaryAssetType('ETF_STOCK')).toBe('STOCK');
        expect(allocationFamily('ETF_STOCK')).toBe('ETF');
    });
});

// =============================================================================
// allocationTypeIcons — the vehicle's icon, and the content's when it adds something
// =============================================================================

describe('allocationTypeIcons — the tooltip names the vehicle, and the content when it differs', () => {
    /** K's icons for the types these tests name. Fails unless they can tell the types apart. */
    function distinctIcons(getAssetTypeIconUrl: (type: string | null | undefined) => string) {
        const icons = {etf: getAssetTypeIconUrl('ETF'), stock: getAssetTypeIconUrl('STOCK'), bond: getAssetTypeIconUrl('BOND'), fallback: getAssetTypeIconUrl('NOT_AN_ASSET_TYPE')};
        // Barrier: four different pictures. With a degenerate map every `content === main` would hold
        // by construction, and every "single icon" below would be true for the wrong reason.
        expect(new Set(Object.values(icons)).size, `icons not distinct: ${JSON.stringify(icons)}`).toBe(4);
        return icons;
    }

    it('gives ETF_STOCK the ETF icon, with the stock icon as its content', async () => {
        const {allocationTypeIcons, getAssetTypeIconUrl} = await importModules();
        const {etf, stock} = distinctIcons(getAssetTypeIconUrl);

        expect(allocationTypeIcons('ETF_STOCK')).toEqual({main: etf, content: stock});
    });

    it('gives ETF_BOND the ETF icon, with the bond icon as its content', async () => {
        const {allocationTypeIcons, getAssetTypeIconUrl} = await importModules();
        const {etf, bond} = distinctIcons(getAssetTypeIconUrl);

        expect(allocationTypeIcons('ETF_BOND')).toEqual({main: etf, content: bond});
    });

    it.each(['ETF', 'ETF_MONETARY', 'STOCK', 'Liquidity'])('shows %s with a single icon: its content would repeat it', async (type) => {
        const {allocationTypeIcons, getAssetTypeIconUrl} = await importModules();
        distinctIcons(getAssetTypeIconUrl);

        expect(allocationTypeIcons(type)).toEqual({main: getAssetTypeIconUrl(type), content: null});
    });
});
