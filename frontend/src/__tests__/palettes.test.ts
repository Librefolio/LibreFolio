/**
 * palettes — the guard the category colour tables are held to (`paletteDefects`), and the two tables held to it.
 *
 * The allocation charts no longer draw 14-slot palettes by rank: since the designer's round 2 (GR1, D-T17) every asset
 * type and every sector keeps one colour, read through `categoryColor` (`$lib/theme/chartCategories`). The guard is
 * kept, and pointed at those tables.
 *
 * - **The guard first, on synthetic palettes.** Each defect it reports is pinned on a small palette made up here rather
 *   than on a real one: a test that only ever ran it on the real tables could not tell "the guard works" from "the
 *   tables happen to be well formed".
 * - **Then the tables, per kind and theme.** Read as the charts read them — `categoryColor` for each key of
 *   `CATEGORY_KEYS` (`categoryPalette`) — each is as many `#rrggbb` colours as it has keys (`categorySlots`), none
 *   repeating another; and the two buckets the engine draws beside either table, the cash and the unclassified, repeat
 *   none of its colours. That the reading goes through the one read point, not a copy, is shown by the Designer Lab's
 *   hook (C3) reaching it.
 *
 * How far apart the colours are, and the designer's values themselves, are `chartCategories.test.ts`'s.
 *
 * Node env: no DOM, no runes. Registered with the allocation unit tests (`front_portfolio_allocation_unit`,
 * `scripts/test_runner/_frontend_portfolio.py`, action `allocation-unit`).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

import {CATEGORY_BUCKETS, CATEGORY_KEYS, categoryColor, type CategoryKind} from '$lib/theme/chartCategories';

import {categoryPalette, categorySlots, paletteDefects} from './palettes';

describe('paletteDefects — the guard every palette under test goes through', () => {
    /** How many slots the synthetic palettes are asked for: any number, as long as the palettes below follow it. */
    const SLOTS = 6;
    /** `SLOTS` distinct colours, with letters in them so the case of a repeat can differ. */
    const whole = Array.from({length: SLOTS}, (_, index) => `#abcd${index.toString(16).padStart(2, '0')}`);

    it('finds nothing wrong with as many distinct #rrggbb colours as the slots asked for', () => {
        expect(paletteDefects(whole, SLOTS)).toEqual([]);
    });

    it('names the slot that repeats another, whatever the letter case', () => {
        const repeated = [whole[0], whole[0].toUpperCase(), ...whole.slice(2)];
        expect(repeated[1], 'guard: the repeat must differ in case, or the case rule is not exercised').not.toBe(repeated[0]);

        expect(paletteDefects(repeated, SLOTS)).toEqual([`slot 1 repeats slot 0 (${whole[0].toUpperCase()})`]);
    });

    it('says how many entries a palette has when it is not the slots asked for, one short or one over', () => {
        expect(paletteDefects(whole.slice(0, -1), SLOTS)).toEqual([`has ${SLOTS - 1} entries, not ${SLOTS}`]);
        expect(paletteDefects([...whole, '#abcdef'], SLOTS)).toEqual([`has ${SLOTS + 1} entries, not ${SLOTS}`]);
    });

    it('names an entry that is not #rrggbb: a name, the short form, the form with alpha', () => {
        const slot = SLOTS - 1;
        for (const entry of ['red', '#abc', '#abcdef80']) {
            expect(paletteDefects([...whole.slice(0, -1), entry], SLOTS), entry).toEqual([`slot ${slot} (${entry}) is not #rrggbb`]);
        }
    });
});

/** The two tables in the two themes. */
const TABLES: ReadonlyArray<readonly [string, CategoryKind, boolean]> = [
    ['the asset types, light', 'type', false],
    ['the asset types, dark', 'type', true],
    ['the sectors, light', 'sector', false],
    ['the sectors, dark', 'sector', true],
];

describe('the category tables — read through categoryColor, as the charts read them', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('reads tables that exist: keys certainly present in each, so no check below passes on an empty table', () => {
        expect(CATEGORY_KEYS.type, 'the asset-type families').toEqual(expect.arrayContaining(['STOCK', 'ETF', 'OTHER']));
        expect(CATEGORY_KEYS.sector, 'the sectors').toEqual(expect.arrayContaining(['Technology', 'Health Care', 'Other']));
        expect(CATEGORY_BUCKETS, 'the buckets the engine adds').toEqual(['Liquidity', 'Unknown']);
    });

    it.each(TABLES)('%s: as many distinct #rrggbb colours as the table has keys', (_name, kind, dark) => {
        const palette = categoryPalette(kind, dark);
        expect(categorySlots(kind), 'one slot per key').toBe(CATEGORY_KEYS[kind].length);

        expect(paletteDefects(palette, categorySlots(kind)), 'two categories of one table would share a colour, or a key reads no #rrggbb').toEqual([]);
    });

    it.each(TABLES)('%s: the cash and the unclassified, drawn beside the table, repeat none of its colours', (_name, kind, dark) => {
        const drawn = [...categoryPalette(kind, dark), ...CATEGORY_BUCKETS.map((bucket) => categoryColor(kind, bucket, dark))];

        expect(paletteDefects(drawn, categorySlots(kind) + CATEGORY_BUCKETS.length), 'a bucket takes the colour of a category, or the two buckets share one').toEqual([]);
    });

    it('reads every slot through categoryColor itself: the Designer Lab hook (C3) reaches the palette', () => {
        const index = CATEGORY_KEYS.type.indexOf('ETF');
        expect(index, 'barrier: ETF is a key of the type table').toBeGreaterThanOrEqual(0);
        const edited = '#010203';
        expect(categoryPalette('type', false)[index], 'barrier: the edit is not the table value already').not.toBe(edited);

        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        vi.stubGlobal('__lfDesignerLab', {categoryColor: (kind: CategoryKind, key: string) => (kind === 'type' && key === 'ETF' ? edited : null)});

        const palette = categoryPalette('type', false);
        expect(palette[index], 'the palette does not read ETF through categoryColor: a copy of the table would not follow the Lab').toBe(edited);
        expect(
            palette.filter((colour, slot) => slot !== index && colour === edited),
            'the hook answered for ETF only: no other slot may take its colour',
        ).toEqual([]);
    });
});
