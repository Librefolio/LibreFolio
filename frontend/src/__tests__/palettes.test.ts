/**
 * palettes — the guard the allocation tests hold their palettes to (`paletteDefects`).
 *
 * Each defect it reports is pinned here on a small synthetic palette rather than on a real one: a test that only ever
 * ran it on the real palettes could not tell "the guard works" from "the palettes happen to be well formed". The real
 * palettes go through it in the three files that measure them (`colors.test.ts`, `allocationHierarchy.test.ts`,
 * `allocationRings.test.ts`).
 */
import {describe, expect, it} from 'vitest';

import {paletteDefects, PALETTE_SLOTS} from './palettes';

describe('paletteDefects — the guard every palette under test goes through', () => {
    /** Fourteen distinct colours, with letters in them so the case of a repeat can differ. */
    const whole = Array.from({length: PALETTE_SLOTS}, (_, index) => `#abcd${index.toString(16).padStart(2, '0')}`);

    it('finds nothing wrong with fourteen distinct #rrggbb colours', () => {
        expect(paletteDefects(whole)).toEqual([]);
    });

    it('names the slot that repeats another, whatever the letter case', () => {
        const repeated = [whole[0], whole[0].toUpperCase(), ...whole.slice(2)];
        expect(repeated[1], 'guard: the repeat must differ in case, or the case rule is not exercised').not.toBe(repeated[0]);

        expect(paletteDefects(repeated)).toEqual([`slot 1 repeats slot 0 (${whole[0].toUpperCase()})`]);
    });

    it('says how many entries a palette has when it is not fourteen', () => {
        expect(paletteDefects(whole.slice(0, -1))).toEqual([`has ${PALETTE_SLOTS - 1} entries, not ${PALETTE_SLOTS}`]);
    });

    it('names an entry that is not #rrggbb', () => {
        expect(paletteDefects([...whole.slice(0, -1), 'red'])).toEqual([`slot ${PALETTE_SLOTS - 1} (red) is not #rrggbb`]);
    });
});
