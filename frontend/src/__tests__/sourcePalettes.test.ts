/**
 * sourcePalettes — the reader the allocation tests take their palettes through.
 *
 * Its error paths are the whole point of it, so each is pinned here on a small
 * inline source rather than on a real component: a test that only ever read the
 * real files could not tell "the reader works" from "the files happen to be
 * well formed". The real reads live in the three files that use them
 * (`colors.test.ts`, `allocationHierarchy.test.ts`, `allocationRings.test.ts`).
 */
import {describe, expect, it} from 'vitest';

import {paletteDefects, parseSourcePalette, PALETTE_SLOTS} from './sourcePalettes';

const ORIGIN = 'Synthetic.svelte';

describe('parseSourcePalette — what it reads', () => {
    it('returns the entries of the named constant, in order and as written', () => {
        const source = `<script lang="ts">\n    const PALETTE_LIGHT = ['#1a4031', '#2563EB', "#7c3aed"];\n    const PALETTE_DARK = ['#4ade80'];\n</script>`;

        expect(parseSourcePalette(source, 'PALETTE_LIGHT')).toEqual(['#1a4031', '#2563EB', '#7c3aed']);
        expect(parseSourcePalette(source, 'PALETTE_DARK')).toEqual(['#4ade80']);
    });

    it('reads a declaration a formatter wrapped, typed, with a trailing comma', () => {
        const source = `const PALETTE_DARK: readonly string[] = [\n    '#4ade80',\n    '#60a5fa',\n] as const;`;

        expect(parseSourcePalette(source, 'PALETTE_DARK')).toEqual(['#4ade80', '#60a5fa']);
    });

    it('finds the constant by its name, not by a name that merely contains it', () => {
        const source = `const PALETTE_LIGHT_OLD = ['#000000'];\nconst MY_PALETTE_LIGHT = ['#111111'];\nconst PALETTE_LIGHT = ['#ffffff'];`;

        expect(parseSourcePalette(source, 'PALETTE_LIGHT')).toEqual(['#ffffff']);
    });
});

describe('parseSourcePalette — what it refuses, loudly', () => {
    it('throws, naming the file and the constant, when the constant is missing', () => {
        // The shape of a rename: the palette is still there, under another name.
        const source = `const LIGHT_SLICE_PALETTE = ['#1a4031', '#2563eb'];`;

        expect(() => parseSourcePalette(source, 'PALETTE_LIGHT', ORIGIN)).toThrow('Synthetic.svelte: no `const PALETTE_LIGHT` declaration');
    });

    it('throws when the constant is declared twice', () => {
        const source = `const PALETTE_LIGHT = ['#1a4031'];\nfunction legacy() {\n    const PALETTE_LIGHT = ['#2563eb'];\n}`;

        expect(() => parseSourcePalette(source, 'PALETTE_LIGHT', ORIGIN)).toThrow('Synthetic.svelte: `const PALETTE_LIGHT` is declared 2 times');
    });

    it.each(["'#abc'", "'red'", 'BRAND_GREEN', "'#1a40311'", "'#gggggg'", "'#1a4031' + ''", '`#1a4031`'])('throws on an entry that is not a #rrggbb literal: %s', (entry) => {
        const source = `const PALETTE_LIGHT = ['#1a4031', ${entry}];`;

        expect(() => parseSourcePalette(source, 'PALETTE_LIGHT', ORIGIN)).toThrow(`Synthetic.svelte: \`PALETTE_LIGHT\` holds ${entry} — only '#rrggbb' literals are read.`);
    });

    it('throws when the constant is not a literal array', () => {
        const source = `const PALETTE_LIGHT = buildPalette();`;

        expect(() => parseSourcePalette(source, 'PALETTE_LIGHT', ORIGIN)).toThrow('Synthetic.svelte: `const PALETTE_LIGHT` is not initialised with a literal array');
    });

    it('throws on an array with no colour in it, rather than handing back an empty palette', () => {
        expect(() => parseSourcePalette(`const PALETTE_LIGHT = [];`, 'PALETTE_LIGHT', ORIGIN)).toThrow('Synthetic.svelte: `PALETTE_LIGHT` holds no colour.');
    });
});

describe('paletteDefects — the guard every palette read goes through', () => {
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
